import functools
from html import unescape
import logging
import hashlib
import http.client
import hmac
import os
import queue
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, UTC
from soloblog.tz import utcnow

from soloblog import config
from soloblog import netguard

log = logging.getLogger(__name__)

# Optional off-site storage in any S3-compatible bucket - Amazon S3,
# Cloudflare R2, Backblaze B2, MinIO, Wasabi... Configured only through
# environment variables (see config.py): the whole point is that the
# database itself can be rebuilt from the bucket, so the bucket's keys
# can't live in that database.
#
# What goes where in the bucket (under S3_PREFIX, if set):
#   uploads/<file>          every image, mirrored as it changes
#   uploads/_trash/<file>   trashed images
#                           (both encrypted when BACKUP_PASSPHRASE is set)
#   backups/<timestamp>.zip posts + comments/settings, after changes
#                           (.zip.enc when BACKUP_PASSPHRASE is set)
#
# The client is a small AWS Signature V4 signer on the standard library,
# path-style URLs - every provider above supports that - rather than
# boto3 and the tens of megabytes it brings along.


def enabled() -> bool:
    return bool(config.S3_BUCKET and config.S3_ACCESS_KEY_ID and config.S3_SECRET_ACCESS_KEY)


def endpoint() -> str:
    # Backblaze and others show the endpoint without https:// - taken as it's shown
    given = config.S3_ENDPOINT.strip()
    if given and "://" not in given:
        given = f"https://{given}"
    return given or f"https://s3.{config.S3_REGION}.amazonaws.com"


class StorageError(Exception):
    pass


# ---- AWS Signature Version 4

def _hmac(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()


def _uri_encode(s: str, safe: str = "-_.~") -> str:
    return urllib.parse.quote(s, safe=safe)


def sign(method: str, url: str, headers: dict, payload_hash: str, access_key: str, secret_key: str,
         region: str, now: datetime = None) -> dict:
    """Returns headers with x-amz-date, x-amz-content-sha256 and
    Authorization added - every header passed in is signed."""
    now = now or datetime.now(UTC)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date = amz_date[:8]
    parts = urllib.parse.urlsplit(url)
    headers = {**headers, "host": parts.netloc, "x-amz-date": amz_date, "x-amz-content-sha256": payload_hash}
    canonical_headers = {k.lower().strip(): " ".join(str(v).split()) for k, v in headers.items()}
    signed = ";".join(sorted(canonical_headers))
    query = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    canonical_query = "&".join(f"{_uri_encode(k)}={_uri_encode(v)}" for k, v in sorted(query))
    canonical = "\n".join([
        method,
        parts.path or "/",  # already encoded by _url()
        canonical_query,
        "".join(f"{k}:{canonical_headers[k]}\n" for k in sorted(canonical_headers)),
        signed,
        payload_hash,
    ])
    scope = f"{date}/{region}/s3/aws4_request"
    to_sign = "\n".join(["AWS4-HMAC-SHA256", amz_date, scope, hashlib.sha256(canonical.encode()).hexdigest()])
    key = _hmac(_hmac(_hmac(_hmac(f"AWS4{secret_key}".encode(), date), region), "s3"), "aws4_request")
    signature = hmac.new(key, to_sign.encode(), hashlib.sha256).hexdigest()
    headers["Authorization"] = (f"AWS4-HMAC-SHA256 Credential={access_key}/{scope}, "
                                f"SignedHeaders={signed}, Signature={signature}")
    return headers


# ---- the handful of S3 calls Soloblog needs

def _key(key: str) -> str:
    prefix = config.S3_PREFIX.strip("/")
    return f"{prefix}/{key}" if prefix else key


def _url(key: str = "", query: dict = None) -> str:
    url = f"{endpoint().rstrip('/')}/{_uri_encode(config.S3_BUCKET)}"
    if key:
        url += "/" + _uri_encode(_key(key), safe="-_.~/")
    if query:
        url += "?" + urllib.parse.urlencode(query, quote_via=urllib.parse.quote)
    return url


def _request(method: str, key: str = "", body: bytes = b"", query: dict = None, headers: dict = None,
             timeout: int = 30):
    url = _url(key, query)
    payload_hash = hashlib.sha256(body).hexdigest()
    signed = sign(method, url, headers or {}, payload_hash, config.S3_ACCESS_KEY_ID,
                  config.S3_SECRET_ACCESS_KEY, config.S3_REGION)
    signed.pop("host")  # urllib sets it itself
    signed["User-Agent"] = "Soloblog"  # some firewalls turn away Python's default name
    try:
        req = urllib.request.Request(url, data=body if method in ("PUT", "POST") else None, method=method,  # noqa: S310 - opened through netguard
                                     headers=signed)
    except ValueError as e:
        # an endpoint that isn't an address at all: said where it's set, not a crash
        raise StorageError(f"can't reach the bucket: {e}") from e
    try:
        with netguard.open_url(req, timeout=timeout, private_ok=True) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except (urllib.error.URLError, OSError, http.client.HTTPException, netguard.Blocked) as e:
        # not reachable, or not an address that can be (a space, not http or https)
        raise StorageError(f"can't reach the bucket: {e}") from e


# What the bucket's refusals mean, in the words Backup and import and
# Site health show - and which setting to look at - for the codes people
# meet setting up (S3's own, which R2 and Backblaze B2 use too)
REFUSALS = {
    "InvalidAccessKeyId": "The bucket doesn't know the key in S3_ACCESS_KEY_ID - check it, and that the key "
                          "still exists",
    "SignatureDoesNotMatch": "The secret doesn't match the key - check S3_SECRET_ACCESS_KEY",
    "NoSuchBucket": "There's no bucket by that name - check S3_BUCKET",
    "AccessDenied": "The key isn't allowed to use this bucket - check its access, and any file name prefix "
                    "matches S3_PREFIX",
    "AuthorizationHeaderMalformed": "The region doesn't match the bucket - check S3_REGION and S3_ENDPOINT",
    "InvalidRegion": "The region doesn't match the bucket - check S3_REGION and S3_ENDPOINT",
}


def _refused(what: str, status: int, body: bytes) -> "StorageError":
    """A refusal as plain words: what it means where it's known, else the
    bucket's own message - never its raw XML."""
    found = {tag: m.group(1).decode("utf-8", "replace").strip()
             for tag in ("Code", "Message") if (m := re.search(rb"<%s>(.*?)</%s>" % (tag.encode(), tag.encode()),
                                                              body or b"", re.S))}
    said = REFUSALS.get(found.get("Code", "")) or unescape(found.get("Message") or found.get("Code") or "")
    return StorageError(f"{what} failed ({status})" + (f": {said}" if said else ""))


def put(key: str, data: bytes, content_type: str = "application/octet-stream"):
    status, body = _request("PUT", key, data, headers={"content-type": content_type})
    if status >= 300:
        raise _refused("Upload", status, body)


def get(key: str):
    """The object's bytes, or None if it doesn't exist."""
    status, body = _request("GET", key)
    if status == 404:
        return None
    if status >= 300:
        raise _refused("Download", status, body)
    return body


def delete(key: str):
    status, body = _request("DELETE", key)
    if status >= 300 and status != 404:
        raise _refused("Delete", status, body)


def list_keys(prefix: str) -> list:
    """[{"key", "size", "modified", "etag"}] under prefix, keys relative to
    S3_PREFIX - every page of the listing, not just the first 1000."""
    out, token = [], None
    full_prefix = _key(prefix)
    strip = len(_key(""))
    while True:
        query = {"list-type": "2", "prefix": full_prefix}
        if token:
            query["continuation-token"] = token
        status, body = _request("GET", query=query)
        if status >= 300:
            raise _refused("Listing", status, body)
        root = ET.fromstring(body)  # noqa: S314 - the admin's own storage server; ElementTree reads no outside entities
        ns = root.tag[:root.tag.index("}") + 1] if root.tag.startswith("{") else ""
        for item in root.iter(f"{ns}Contents"):
            out.append({
                "key": item.findtext(f"{ns}Key")[strip:],
                "size": int(item.findtext(f"{ns}Size") or 0),
                "modified": item.findtext(f"{ns}LastModified") or "",
                # an MD5 of what was uploaded in one go - what an image is compared by
                "etag": (item.findtext(f"{ns}ETag") or "").strip('"').lower(),
            })
        if root.findtext(f"{ns}IsTruncated") != "true":
            return out
        token = root.findtext(f"{ns}NextContinuationToken")


def check() -> str:
    """"" if the bucket answers to these credentials, else why not -
    shown in Backup and import so a typo'd key is obvious straight away."""
    if not enabled():
        return "Not configured"
    try:
        list_keys("backups/")
        return ""
    except StorageError as e:
        return str(e)


# ---- images: every change mirrored, missing files fetched back

# Mirroring runs on one background thread, in the order the changes
# happened: an upload no longer waits on the bucket before the page
# answers, and an upload, trash and restore of one image still reach the
# bucket in that order.
_mirror_queue = queue.Queue()
_mirror_thread = None
_mirror_lock = threading.Lock()


def _mirror_worker():
    while True:
        action, args = _mirror_queue.get()
        try:
            action(*args)
        except Exception:
            log.exception("copying to the bucket failed")
            if action is _put_image:
                _set_unsynced(unsynced() | {args[0]})
        finally:
            _mirror_queue.task_done()


def _mirror(action, *args):
    """Mirroring never blocks or breaks the local change it follows - a
    bucket that's briefly unreachable just gets logged; "Sync images"
    in Backup and import catches it up later."""
    global _mirror_thread
    if not enabled():
        return
    with _mirror_lock:
        if _mirror_thread is None:
            _mirror_thread = threading.Thread(target=_mirror_worker, name="bucket-mirror", daemon=True)
            _mirror_thread.start()
    _mirror_queue.put((action, args))


def wait_for_mirroring():
    """Blocks until every queued image change has reached the bucket."""
    _mirror_queue.join()


def mirror_upload(filename: str, trash: bool = False):
    if not enabled():
        return
    folder = os.path.join(config.uploads_dir(), "_trash") if trash else config.uploads_dir()
    key = f"uploads/_trash/{filename}" if trash else f"uploads/{filename}"
    # read now - by the time the worker gets to it, the file may already
    # have moved on (into trash, say), which is a later queued change
    try:
        with open(os.path.join(folder, filename), "rb") as f:
            data = f.read()
    except OSError as e:
        log.warning("couldn't read %s to copy it to the bucket: %s", filename, e)
        return
    _mirror(_put_image, key, data)


def _put_image(key: str, data: bytes):
    import mimetypes
    content_type = "application/octet-stream" if config.BACKUP_PASSPHRASE else \
        mimetypes.guess_type(key)[0] or "application/octet-stream"
    put(key, _to_bucket(data), content_type)
    if key in (missing := unsynced()):
        _set_unsynced(missing - {key})


def mirror_move(filename: str, to_trash: bool):
    """An image moved into (or out of) trash locally - same move in the bucket."""
    mirror_upload(filename, trash=to_trash)
    _mirror(delete, f"uploads/{filename}" if to_trash else f"uploads/_trash/{filename}")


def mirror_delete(filename: str, trash: bool = False):
    _mirror(delete, f"uploads/_trash/{filename}" if trash else f"uploads/{filename}")


def fetch_upload(filename: str) -> bool:
    """Copies a missing image back from the bucket into the local
    uploads folder - how a host without a persistent disk refills it."""
    if not enabled():
        return False
    try:
        data = get(f"uploads/{filename}")
        if data is None:
            return False
        data = _from_bucket(data)
    except StorageError as e:
        log.warning("couldn't fetch %s from the bucket: %s", filename, e)
        return False
    os.makedirs(config.uploads_dir(), exist_ok=True)
    with open(os.path.join(config.uploads_dir(), filename), "wb") as f:
        f.write(data)
    return True


def _same(data: bytes, remote: dict) -> bool:
    """Whether the bucket's copy is this image already - by its MD5
    (the listing's ETag); locked, by its size, as a locked copy differs
    every time it's made but is always the same size bigger."""
    if config.BACKUP_PASSPHRASE:
        return remote["size"] == len(MAGIC) + 16 + 12 + len(data) + 16
    return remote["etag"] == hashlib.md5(data, usedforsecurity=False).hexdigest()


def sync_uploads(way: str = "both") -> dict:
    """Images between this disk and the bucket. "up": every image here
    the bucket hasn't got as it is here copied to it; "down": every image
    in the bucket this disk hasn't got as it is there copied here. "both":
    only what's missing on each side, each way (a new server refilling
    itself). The same image is never copied again - a bucket that keeps
    every version (Backblaze, unless told not to) would keep it twice -
    and nothing is deleted on either side."""
    counts = {"uploaded": 0, "downloaded": 0, "same": 0}
    for folder, prefix in ((config.uploads_dir(), "uploads/"),
                           (os.path.join(config.uploads_dir(), "_trash"), "uploads/_trash/")):
        os.makedirs(folder, exist_ok=True)
        remote = {k["key"][len(prefix):]: k for k in list_keys(prefix) if "/" not in k["key"][len(prefix):]}
        local = {f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))}
        if way in ("up", "both"):
            for fn in sorted(local):
                if way == "both" and fn in remote:
                    continue
                with open(os.path.join(folder, fn), "rb") as f:
                    data = f.read()
                if fn in remote and _same(data, remote[fn]):
                    counts["same"] += 1
                    continue
                _put_image(prefix + fn, data)
                counts["uploaded"] += 1
        if way in ("down", "both"):
            for fn in sorted(remote):
                path = os.path.join(folder, fn)
                if fn in local:
                    if way == "both":
                        continue
                    with open(path, "rb") as f:
                        if _same(f.read(), remote[fn]):
                            counts["same"] += 1
                            continue
                data = get(prefix + fn)
                if data is None:
                    continue
                try:
                    data = _from_bucket(data)
                except StorageError as e:  # one image the passphrase can't open needn't stop the rest
                    log.warning("couldn't open %s from the bucket: %s", fn, e)
                    continue
                with open(path, "wb") as f:
                    f.write(data)
                counts["downloaded"] += 1
    if way in ("up", "both"):
        # everything here has reached the bucket now
        _set_unsynced(set())
    return counts


# ---- images that didn't reach the bucket: remembered (across restarts)
# until they do, so Backup and import and Site health can say so - a
# copy that fails while the bucket can't be reached is never retried

def unsynced() -> set:
    from soloblog import settings
    return {k for k in (settings.get("images_not_in_bucket") or "").split("\n") if k}


def _set_unsynced(keys: set):
    from soloblog import settings
    value = "\n".join(sorted(keys)[:1000])
    if (settings.get("images_not_in_bucket") or "") != value:
        settings.set_many({"images_not_in_bucket": value})


# ---- backups: posts + comments/settings, a zip per change burst

# images aren't in these - they're already in the bucket one by one
BACKUP_CATEGORIES = ["posts", "settings", "comments", "members", "subscribers", "stats"]
BACKUP_PREFIX = "backups/"
_state = {"timer": None, "first_change": None, "last_result": "", "last_at": ""}
_lock = threading.Lock()


# An encrypted backup: MAGIC, a 16-byte salt, a 12-byte nonce, then the
# zip under AES-256-GCM with a key scrypt makes from BACKUP_PASSPHRASE.
# GCM also proves the file wasn't changed - a wrong passphrase or a
# tampered file fails the same way.
MAGIC = b"SOLOBLOG-ENC1"


@functools.lru_cache(maxsize=8)
def _backup_key(passphrase: str, salt: bytes) -> bytes:
    return hashlib.scrypt(passphrase.encode(), salt=salt, n=2 ** 15, r=8, p=1, maxmem=2 ** 26, dklen=32)


def seal(data: bytes, passphrase: str, salt: bytes = None) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    salt, nonce = salt or os.urandom(16), os.urandom(12)
    return MAGIC + salt + nonce + AESGCM(_backup_key(passphrase, salt)).encrypt(nonce, data, MAGIC)


def unseal(data: bytes, passphrase: str) -> bytes:
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    if not data.startswith(MAGIC):
        raise StorageError("not an encrypted Soloblog backup")
    if not passphrase:
        raise StorageError("this backup is encrypted - set BACKUP_PASSPHRASE to restore it")
    head = len(MAGIC)
    salt, nonce, body = data[head:head + 16], data[head + 16:head + 28], data[head + 28:]
    try:
        return AESGCM(_backup_key(passphrase, salt)).decrypt(nonce, body, MAGIC)
    except InvalidTag:
        raise StorageError("wrong BACKUP_PASSPHRASE, or the backup is damaged") from None


# Images are sealed the same way, with one salt for the site's images, so
# the slow scrypt key is made once rather than for every image. A fresh
# nonce each time still makes every sealed image different.
def _image_salt() -> bytes:
    return hashlib.sha256(f"soloblog-images:{config.S3_BUCKET}:{config.S3_PREFIX}".encode()).digest()[:16]


def _to_bucket(data: bytes) -> bytes:
    return seal(data, config.BACKUP_PASSPHRASE, _image_salt()) if config.BACKUP_PASSPHRASE else data


def _from_bucket(data: bytes) -> bytes:
    # an image copied before the passphrase was set is still plain
    return unseal(data, config.BACKUP_PASSPHRASE) if data.startswith(MAGIC) else data


def _images_sealed_with() -> str:
    """Which passphrase the bucket's images should be under - a short
    fingerprint of its key, never the passphrase; blank for none."""
    if not config.BACKUP_PASSPHRASE:
        return ""
    return hashlib.sha256(_backup_key(config.BACKUP_PASSPHRASE, _image_salt())).hexdigest()[:16]


def reseal_images() -> int:
    """After BACKUP_PASSPHRASE is set, changed or removed: every image
    copied again, sealed the way it is now. Returns how many - none when
    nothing changed since last time."""
    from soloblog import settings
    want = _images_sealed_with()
    if (settings.get("bucket_images_sealed") or "") == want:
        return 0
    n = 0
    for folder, prefix in ((config.uploads_dir(), "uploads/"),
                           (os.path.join(config.uploads_dir(), "_trash"), "uploads/_trash/")):
        if not os.path.isdir(folder):
            continue
        for fn in os.listdir(folder):
            if os.path.isfile(os.path.join(folder, fn)):
                with open(os.path.join(folder, fn), "rb") as f:
                    _put_image(prefix + fn, f.read())
                n += 1
    settings.set_many({"bucket_images_sealed": want})
    return n


def get_backup(key: str):
    """A backup's zip, decrypted if it was stored encrypted. None if
    it's gone."""
    data = get(key)
    if data is not None and key.endswith(".enc"):
        data = unseal(data, config.BACKUP_PASSPHRASE)
    return data


def backup_now() -> str:
    """Writes a backup zip to the bucket and prunes old ones. Returns
    the new object's key."""
    from soloblog import backup
    key = f"{BACKUP_PREFIX}soloblog-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}.zip"
    data = backup.build_backup_zip(backup_categories())
    if config.BACKUP_PASSPHRASE:
        put(key + ".enc", seal(data, config.BACKUP_PASSPHRASE))
        key += ".enc"
    else:
        put(key, data, "application/zip")
    backups = list_backups()
    for old in backups[keep_count():]:
        delete(old["key"])
    _state["last_result"], _state["last_at"] = "", datetime.now(UTC).isoformat()
    # kept across restarts, for Site health
    from soloblog import settings
    settings.set_many({"backup_last_at": utcnow().isoformat(), "backup_last_error": ""})
    return key


BACKUP_KEEP_CHOICES = (7, 14, 30, 60, 90, 180, 365)
# Settings > Backup > How often: seconds between backups (0: after changes)
BACKUP_EVERY = {"changes": 0, "day": 24 * 3600, "week": 7 * 24 * 3600}


def every() -> int:
    from soloblog import settings
    return BACKUP_EVERY.get(settings.get("backup_every"), 0)


def _since_last() -> float | None:
    from soloblog import settings
    try:
        return (utcnow() - datetime.fromisoformat(settings.get("backup_last_at"))).total_seconds()
    except (TypeError, ValueError):
        return None


def backup_categories() -> set:
    """What the automatic backups include - Settings > Backup and import >
    Cloud storage. Everything (but images) unless some were unticked."""
    from soloblog import settings
    chosen = {c for c in (settings.get("backup_include") or "").split(",") if c in BACKUP_CATEGORIES}
    return chosen or set(BACKUP_CATEGORIES)


def keep_count() -> int:
    """How many backups to keep - Settings > Backup and import > Cloud storage."""
    from soloblog import settings
    try:
        return max(1, int(settings.get("backup_keep")))
    except (TypeError, ValueError):
        return config.S3_BACKUP_KEEP


def list_backups() -> list:
    """Newest first."""
    items = [k for k in list_keys(BACKUP_PREFIX) if k["key"].endswith((".zip", ".zip.enc"))]
    return sorted(items, key=lambda k: k["key"], reverse=True)


def last_status() -> dict:
    # a failure is kept across restarts (backup_last_error) - a restart
    # must not hide that backups aren't reaching the bucket
    from soloblog import settings
    return {"at": _state["last_at"], "error": _state["last_result"] or settings.get("backup_last_error") or "",
            "pending": _state["timer"] is not None}


def _run_scheduled():
    with _lock:
        _state["timer"] = None
        _state["first_change"] = None
    try:
        backup_now()
    except Exception as e:  # a background thread - never let it die silently
        _state["last_result"] = str(e)
        log.warning("automatic backup failed: %s", e)
        from soloblog import settings
        settings.set_many({"backup_last_error": str(e)[:500]})


def note_change():
    """Called after anything that changes data. Backs up once things go
    quiet for BACKUP_DELAY seconds - a burst of saves makes one backup,
    not twenty - but never waits longer than BACKUP_MAX_WAIT overall, so
    steady activity still gets backed up. Once a day or a week instead:
    a day or a week after the last backup, and only if something changed -
    or at shutdown, by flush(), so a host without its own disk loses nothing."""
    if not enabled() or not config.S3_AUTO_BACKUP:
        return
    gap = every()
    with _lock:
        if gap:
            if _state["timer"]:
                return  # one's already waiting
            since = _since_last()
            delay = config.S3_BACKUP_DELAY if since is None else max(config.S3_BACKUP_DELAY, gap - since)
            timer = threading.Timer(delay, _run_scheduled)
            timer.daemon = True
            _state["timer"] = timer
            timer.start()
            return
        now = time.monotonic()
        first = _state["first_change"] or now
        _state["first_change"] = first
        if _state["timer"]:
            _state["timer"].cancel()
        delay = max(0.0, min(config.S3_BACKUP_DELAY, first + config.S3_BACKUP_MAX_WAIT - now))
        timer = threading.Timer(delay, _run_scheduled)
        timer.daemon = True
        _state["timer"] = timer
        timer.start()


def reschedule():
    """How often changed: a backup that's waiting is timed again for it."""
    with _lock:
        timer = _state["timer"]
        if not timer:
            return
        timer.cancel()
        _state["timer"] = _state["first_change"] = None
    note_change()


def flush():
    """A pending automatic backup, run now - at shutdown, so a host that
    throws its disk away on restart doesn't lose the last few minutes."""
    with _lock:
        timer = _state["timer"]
    if timer:
        timer.cancel()
        _run_scheduled()
    wait_for_mirroring()


class ChangeTracker:
    """ASGI middleware: any successful request that isn't a plain read
    counts as a change worth backing up."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] in ("GET", "HEAD", "OPTIONS"):
            return await self.app(scope, receive, send)

        async def watch(message):
            if message["type"] == "http.response.start" and message["status"] < 400:
                note_change()
            await send(message)
        return await self.app(scope, receive, watch)


# ---- starting on an empty disk

def restore_on_boot():
    """Runs before migrations. If this disk has no database yet but the
    bucket has backups, the newest one is unpacked - database (admin
    login included) and posts - and the images come back from the
    bucket. What makes a host without a persistent disk usable: every
    restart picks up where the last backup left off."""
    if not enabled() or not config.S3_RESTORE_ON_BOOT or os.path.exists(config.db_path()):
        return False
    try:
        backups = list_backups()
        if not backups:
            return False
        data = get_backup(backups[0]["key"])
    except StorageError as e:
        log.warning("couldn't restore on boot: %s", e)
        return False
    import io
    import zipfile
    from soloblog.backup import _safe_member
    os.makedirs(os.path.join(config.posts_dir(), "_trash"), exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for info in zf.infolist():
            if info.filename == "blog.db":
                dest = config.db_path()
            elif (base := _safe_member(info.filename, "posts/_trash/")) and base.endswith(".md"):
                dest = os.path.join(config.posts_dir(), "_trash", base)
            elif (base := _safe_member(info.filename, "posts/")) and base.endswith(".md"):
                dest = os.path.join(config.posts_dir(), base)
            else:
                continue
            with zf.open(info) as src, open(dest, "wb") as dst:
                dst.write(src.read())
    try:
        counts = sync_uploads()
    except StorageError as e:
        log.warning("images will load on demand instead: %s", e)
        counts = {"downloaded": 0}
    log.info("restored %s and %s image(s) from the bucket", backups[0]['key'], counts['downloaded'])
    return True
