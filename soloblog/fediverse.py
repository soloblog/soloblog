import logging
import base64
import hashlib
import json
import queue
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, UTC
from soloblog.tz import utcnow
from email.utils import format_datetime, parsedate_to_datetime
from html import escape
from urllib.parse import urlsplit

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from soloblog import config
from soloblog import netguard
from soloblog import settings
from soloblog.db import get_db

log = logging.getLogger(__name__)

# ActivityPub - the protocol Mastodon, Pixelfed, Misskey, Threads and
# the rest of the fediverse speak. With it on (Settings > Site >
# Fediverse), the blog is an account people can follow - @blog@your.site
# - and each new post appears in their timelines. Replies come back as
# comments waiting for approval; favourites and boosts are counted.
#
# The pieces: WebFinger (so @blog@your.site can be found), the actor
# (the account itself, with its public key), an outbox of recent posts,
# a followers collection, and an inbox that other servers POST to. Every
# request in either direction is signed with HTTP Signatures (the draft
# Mastodon uses); an unsigned or badly signed inbox delivery is dropped.

AS_PUBLIC = "https://www.w3.org/ns/activitystreams#Public"
CONTEXT = ["https://www.w3.org/ns/activitystreams", "https://w3id.org/security/v1"]
JSON_TYPES = ("application/activity+json", "application/ld+json")
CONTENT_TYPE = "application/activity+json"
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{1,30}$")
MAX_INBOX_BYTES = 1024 * 1024
ACTOR_TTL = 24 * 3600


def host() -> str:
    return urlsplit(config.BASE_URL).hostname or ""


def reachable() -> str:
    """"" if other servers can reach this blog, else why not - the
    fediverse needs a public https address in BASE_URL."""
    parts = urlsplit(config.BASE_URL)
    if parts.scheme != "https":
        return "BASE_URL has to be an https:// address"
    if parts.hostname in ("localhost", "127.0.0.1") or (parts.hostname or "").endswith(".local"):
        return "BASE_URL has to be your public address, not localhost"
    return ""


def enabled(s=None) -> bool:
    s = s or settings.get_all()
    return s.get("activitypub_enabled") == "1" and not reachable()


def username(s=None) -> str:
    s = s or settings.get_all()
    name = s.get("activitypub_username") or "blog"
    return name if USERNAME_RE.match(name) else "blog"


def handle(s=None) -> str:
    return f"@{username(s)}@{host()}"


def actor_id() -> str:
    return f"{config.BASE_URL}/ap/actor"


def wants_json(accept: str) -> bool:
    accept = (accept or "").lower()
    return "application/activity+json" in accept or (
        "application/ld+json" in accept and "activitystreams" in accept)


# ---- keys

def _keys():
    """The blog's RSA key pair, made the first time it's needed and kept
    in settings (so it's in backups, and survives a new disk)."""
    s = settings.get_all()
    pem = s.get("activitypub_private_key")
    if not pem:
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                serialization.NoEncryption()).decode()
        public = key.public_key().public_bytes(serialization.Encoding.PEM,
                                               serialization.PublicFormat.SubjectPublicKeyInfo).decode()
        settings.set_many({"activitypub_private_key": pem, "activitypub_public_key": public})
    return serialization.load_pem_private_key(pem.encode(), password=None)


def public_key_pem() -> str:
    _keys()
    return settings.get("activitypub_public_key")


# ---- documents

def webfinger(resource: str, s=None):
    s = s or settings.get_all()
    wanted = {f"acct:{username(s)}@{host()}".lower(), actor_id().lower(), f"{config.BASE_URL}/".lower()}
    if resource.lower() not in wanted:
        return None
    return {
        "subject": f"acct:{username(s)}@{host()}",
        "aliases": [actor_id(), f"{config.BASE_URL}/"],
        "links": [
            {"rel": "self", "type": CONTENT_TYPE, "href": actor_id()},
            {"rel": "http://webfinger.net/rel/profile-page", "type": "text/html", "href": f"{config.BASE_URL}/"},
        ],
    }


def _absolute(url: str) -> str:
    return config.BASE_URL + url if url and url.startswith("/") else url


def _image(url: str):
    if not url:
        return None
    import mimetypes
    return {"type": "Image", "url": _absolute(url), "mediaType": mimetypes.guess_type(url)[0] or "image/jpeg"}


def actor(s=None) -> dict:
    s = s or settings.get_all()
    about = s.get("author_bio") or s.get("tagline") or s.get("meta_description") or ""
    doc = {
        "@context": CONTEXT,
        "id": actor_id(),
        "type": "Person",
        "preferredUsername": username(s),
        "name": s["site_title"],
        "summary": f"<p>{escape(about)}</p>" if about else "",
        "url": f"{config.BASE_URL}/",
        "inbox": f"{config.BASE_URL}/ap/inbox",
        "outbox": f"{config.BASE_URL}/ap/outbox",
        "followers": f"{config.BASE_URL}/ap/followers",
        "following": f"{config.BASE_URL}/ap/following",
        "endpoints": {"sharedInbox": f"{config.BASE_URL}/ap/inbox"},
        "manuallyApprovesFollowers": False,
        "discoverable": True,
        "indexable": s.get("search_noindex") != "1",
        "published": "2020-01-01T00:00:00Z",
        "publicKey": {"id": f"{actor_id()}#main-key", "owner": actor_id(), "publicKeyPem": public_key_pem()},
        "attachment": [{"type": "PropertyValue", "name": "Website",
                        "value": f'<a href="{config.BASE_URL}/" rel="me">{escape(host())}</a>'}],
    }
    icon = _image(s.get("author_avatar_url") or s.get("app_icon_url") or "")
    if icon:
        doc["icon"] = icon
    header = _image(s.get("banner_image_url") or "")
    if header:
        doc["image"] = header
    return doc


def _stamp(value: str) -> str:
    value = (value or "")[:19].rstrip("Z")
    if len(value) == 10:
        value += "T00:00:00"
    return value + "Z"


def post_object(row, s=None) -> dict:
    """A post as an ActivityPub Article - the post's own URL is its id."""
    from soloblog import posts
    from soloblog.feeds import _absolute as absolute_html
    from soloblog.render import render_post
    from soloblog.ui import tag_url
    s = s or settings.get_all()
    url = f"{config.BASE_URL}/post/{row['slug']}"
    html, _ = render_post(posts.public_part(posts.load_post_body(row["slug"]), row["visibility"]))
    if posts.is_gated(row):
        html += posts.members_note(row)
    if posts.is_protected(row):
        from soloblog import i18n
        html = (f'<p>{i18n.t("This post is protected with a password.")} '
                f'<a href="{config.BASE_URL + posts.url_for(row)}">{i18n.t("Open it")}</a></p>')
    tags = posts.split_tags(row["tags"])
    obj = {
        "@context": CONTEXT[0],
        "id": url,
        "type": "Article",
        "name": row["title"],
        "content": absolute_html(html),
        "url": url,
        "attributedTo": actor_id(),
        "published": _stamp(row["created_at"]),
        "updated": _stamp(row["updated_at"] or row["created_at"]),
        "to": [AS_PUBLIC],
        "cc": [f"{config.BASE_URL}/ap/followers"],
        "tag": [{"type": "Hashtag", "href": config.BASE_URL + tag_url(t), "name": "#" + re.sub(r"\W", "", t)}
                for t in tags if re.sub(r"\W", "", t)],
        "replies": f"{url}#comments",
    }
    if row["summary"]:
        # not "summary" - Mastodon shows that as a content warning
        obj["preview"] = {"type": "Note", "content": f"<p>{escape(row['summary'])}</p>"}
    if row["cover_image"]:
        obj["image"] = _image(row["cover_image"])
        obj["attachment"] = [_image(row["cover_image"])]
    return obj


def note_object(comment, reply_to, s=None) -> dict:
    """The author's reply to a fediverse comment, as a Note addressed
    back to whoever wrote it."""
    url = f"{config.BASE_URL}/ap/note/{comment['id']}"
    mention = reply_to.get("author_url") or reply_to["source_url"]
    name = reply_to["author_name"]
    return {
        "@context": CONTEXT[0],
        "id": url,
        "type": "Note",
        "url": f"{config.BASE_URL}/post/{comment['post_slug']}#comment-{comment['id']}",
        "attributedTo": actor_id(),
        "inReplyTo": reply_to["source_url"],
        "published": _stamp(comment["created_at"]),
        "to": [reply_to["actor"]],
        "cc": [AS_PUBLIC, f"{config.BASE_URL}/ap/followers"],
        "content": (f'<p><span class="h-card"><a href="{escape(mention)}" class="u-url mention">'
                    f'{escape(name)}</a></span> {escape(comment["body"])}</p>'),
        "tag": [{"type": "Mention", "href": reply_to["actor"], "name": name}],
    }


def activity(kind: str, obj, extra_id: str = "") -> dict:
    oid = obj["id"] if isinstance(obj, dict) else obj
    return {
        "@context": CONTEXT[0],
        "id": f"{oid}#{kind.lower()}{extra_id}",
        "type": kind,
        "actor": actor_id(),
        "published": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "to": obj.get("to", [AS_PUBLIC]) if isinstance(obj, dict) else [AS_PUBLIC],
        "cc": obj.get("cc", []) if isinstance(obj, dict) else [f"{config.BASE_URL}/ap/followers"],
        "object": obj,
    }


def outbox(s=None) -> dict:
    from soloblog import posts
    s = s or settings.get_all()
    rows = [r for r in posts.list_roll_all()][:20]
    return {
        "@context": CONTEXT[0], "id": f"{config.BASE_URL}/ap/outbox", "type": "OrderedCollection",
        "totalItems": posts.count_roll(),
        "orderedItems": [activity("Create", post_object(r, s)) for r in rows],
    }


def followers_collection() -> dict:
    # a count, not the list - who follows the blog isn't anyone else's business
    return {"@context": CONTEXT[0], "id": f"{config.BASE_URL}/ap/followers", "type": "OrderedCollection",
            "totalItems": follower_count(), "orderedItems": []}


def following_collection() -> dict:
    return {"@context": CONTEXT[0], "id": f"{config.BASE_URL}/ap/following", "type": "OrderedCollection",
            "totalItems": 0, "orderedItems": []}


def nodeinfo(s=None) -> dict:
    from soloblog import posts
    s = s or settings.get_all()
    return {
        "version": "2.0",
        "software": {"name": "soloblog", "version": config.VERSION.split("-")[0]},
        "protocols": ["activitypub"],
        "services": {"inbound": [], "outbound": ["rss2.0", "atom1.0"]},
        "openRegistrations": False,
        "usage": {"users": {"total": 1, "activeMonth": 1, "activeHalfyear": 1}, "localPosts": posts.count_roll()},
        "metadata": {"nodeName": s["site_title"]},
    }


# ---- HTTP Signatures

def _digest(body: bytes) -> str:
    return "SHA-256=" + base64.b64encode(hashlib.sha256(body).digest()).decode()


def signed_headers(method: str, url: str, body: bytes = None) -> dict:
    parts = urlsplit(url)
    target = parts.path + (f"?{parts.query}" if parts.query else "")
    headers = {"host": parts.netloc, "date": format_datetime(datetime.now(UTC), usegmt=True)}
    names = ["(request-target)", "host", "date"]
    if body is not None:
        headers["digest"] = _digest(body)
        headers["content-type"] = CONTENT_TYPE
        names += ["digest", "content-type"]
    lines = [f"(request-target): {method.lower()} {target}"] + [f"{n}: {headers[n]}" for n in names[1:]]
    signature = _keys().sign("\n".join(lines).encode(), padding.PKCS1v15(), hashes.SHA256())
    headers["signature"] = (f'keyId="{actor_id()}#main-key",algorithm="rsa-sha256",headers="{" ".join(names)}",'
                            f'signature="{base64.b64encode(signature).decode()}"')
    return headers


def signed_get(url: str) -> dict:
    """A signed GET of an ActivityPub document (servers in "secure mode"
    only answer those)."""
    headers = {**signed_headers("GET", url), "accept": CONTENT_TYPE, "user-agent": f"Soloblog/{config.VERSION}"}
    req = urllib.request.Request(url, headers=headers)  # noqa: S310 - opened through netguard
    with netguard.open_url(req, timeout=10) as resp:
        return json.loads(resp.read(MAX_INBOX_BYTES))


def signed_post(url: str, doc: dict) -> int:
    body = json.dumps(doc).encode()
    headers = {**signed_headers("POST", url, body), "user-agent": f"Soloblog/{config.VERSION}"}
    req = urllib.request.Request(url, data=body, method="POST", headers=headers)  # noqa: S310 - opened through netguard
    try:
        with netguard.open_url(req, timeout=15) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code


def fetch_actor(url: str, refresh: bool = False) -> dict:
    """Someone else's actor document, cached a day. Raises on failure."""
    url = url.split("#")[0]
    db = get_db()
    row = db.execute("SELECT data, fetched_at FROM ap_actors WHERE id=?", (url,)).fetchone()
    if row and not refresh:
        age = time.time() - datetime.fromisoformat(row["fetched_at"]).timestamp()
        if age < ACTOR_TTL:
            return json.loads(row["data"])
    doc = signed_get(url)
    if doc.get("type") in ("Key", "CryptographicKey") and doc.get("owner"):
        return fetch_actor(doc["owner"], refresh)
    # an actor lives where it says: a profile fetched from one server
    # claiming to be someone on another would sign as them with its own key
    if urllib.parse.urlsplit(str(doc.get("id") or "")).netloc.lower() != urllib.parse.urlsplit(url).netloc.lower():
        raise ValueError("the actor isn't on the server it came from")
    db.execute("INSERT INTO ap_actors (id, data, fetched_at) VALUES (?, ?, ?) ON CONFLICT(id) DO UPDATE SET "
               "data=excluded.data, fetched_at=excluded.fetched_at",
               (url, json.dumps(doc), utcnow().isoformat(timespec="seconds")))
    db.commit()
    return doc


def _parse_signature(value: str) -> dict:
    return dict(re.findall(r'(\w+)="([^"]*)"', value or ""))


def verify(method: str, path: str, headers: dict, body: bytes) -> dict:
    """The actor who signed this request, or raises ValueError."""
    sig = _parse_signature(headers.get("signature", ""))
    if not sig.get("keyId") or not sig.get("signature"):
        raise ValueError("unsigned")
    names = (sig.get("headers") or "date").lower().split()
    if body and "digest" not in names:
        raise ValueError("the body isn't covered by the signature")
    # where it was sent and when, signed too - else a signature made for
    # another server's inbox, or long ago, could be sent again here
    if "(request-target)" not in names or "date" not in names:
        raise ValueError("the signature doesn't cover where it was sent, or when")
    if "digest" in names and headers.get("digest", "").split(",")[0].strip() != _digest(body):
        # some servers send several digests; ours is SHA-256
        digests = [d.strip() for d in headers.get("digest", "").split(",")]
        if _digest(body) not in digests:
            raise ValueError("digest mismatch")
    if headers.get("date"):
        try:
            skew = abs(time.time() - parsedate_to_datetime(headers["date"]).timestamp())
        except (TypeError, ValueError):
            skew = 0
        if skew > 12 * 3600:
            raise ValueError("stale date")
    lines = []
    for name in names:
        if name == "(request-target)":
            lines.append(f"(request-target): {method.lower()} {path}")
        elif name in headers:
            lines.append(f"{name}: {headers[name]}")
        else:
            raise ValueError(f"missing signed header {name}")
    message, signature = "\n".join(lines).encode(), base64.b64decode(sig["signature"])
    for refresh in (False, True):  # a key that changed gets one fresh look
        who = fetch_actor(sig["keyId"], refresh=refresh)
        pem = (who.get("publicKey") or {}).get("publicKeyPem", "")
        try:
            serialization.load_pem_public_key(pem.encode()).verify(signature, message, padding.PKCS1v15(),
                                                                   hashes.SHA256())
            return who
        except (InvalidSignature, ValueError):
            continue
    raise ValueError("bad signature")


# ---- followers

def follower_count() -> int:
    return get_db().execute("SELECT COUNT(*) FROM ap_followers").fetchone()[0]


def list_followers(limit: int = 200) -> list:
    return get_db().execute("SELECT * FROM ap_followers ORDER BY followed_at DESC LIMIT ?", (limit,)).fetchall()


def _handle_of(doc: dict) -> str:
    name = doc.get("preferredUsername") or ""
    return f"@{name}@{urlsplit(doc.get('id', '')).hostname}" if name else doc.get("id", "")


def inboxes() -> set:
    """Where a post goes: each server's shared inbox once, else each
    follower's own."""
    return {r["shared_inbox"] or r["inbox"] for r in get_db().execute("SELECT inbox, shared_inbox FROM ap_followers")}


# ---- the inbox

def _object_id(obj):
    return obj.get("id") if isinstance(obj, dict) else obj


def _local_slug(url: str):
    """The slug of one of our posts from its URL (or a comment/note on it)."""
    from soloblog import posts
    if not url or not url.startswith(config.BASE_URL + "/post/"):
        return None
    slug = url[len(config.BASE_URL + "/post/"):].split("#")[0].split("?")[0].strip("/")
    row = posts.get_post(slug)
    return slug if row and posts.is_live(row) else None


def _reply_target(obj) -> str:
    """The post a reply belongs to - directly, or through one of our
    own replies (/ap/note/<id>) or a comment we've already stored."""
    target = obj.get("inReplyTo") or ""
    if isinstance(target, dict):
        target = target.get("id", "")
    slug = _local_slug(target)
    if slug:
        return slug
    m = re.match(re.escape(config.BASE_URL) + r"/ap/note/(\d+)$", target)
    db = get_db()
    if m:
        row = db.execute("SELECT post_slug FROM comments WHERE id=?", (int(m.group(1)),)).fetchone()
        return row["post_slug"] if row else None
    row = db.execute("SELECT post_slug FROM comments WHERE source_url=?", (target,)).fetchone()
    return row["post_slug"] if row else None


def _plain(html: str) -> str:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html or "", "html.parser")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for p in soup.find_all("p"):
        p.append("\n\n")
    return re.sub(r"\n{3,}", "\n\n", soup.get_text()).strip()


def handle_activity(act: dict, signer: dict):
    """One verified inbox delivery."""
    kind = act.get("type")
    who = act.get("actor")
    if isinstance(who, dict):
        who = who.get("id")
    if who != signer.get("id"):
        return  # someone forwarding another actor's activity - not trusted here
    obj = act.get("object")
    db = get_db()
    now = utcnow().isoformat(timespec="seconds")

    if kind == "Follow" and _object_id(obj) == actor_id():
        endpoints = signer.get("endpoints") or {}
        db.execute("INSERT INTO ap_followers (actor, inbox, shared_inbox, handle, followed_at) VALUES (?, ?, ?, ?, ?) "
                   "ON CONFLICT(actor) DO UPDATE SET inbox=excluded.inbox, shared_inbox=excluded.shared_inbox, "
                   "handle=excluded.handle",
                   (signer["id"], signer.get("inbox", ""), endpoints.get("sharedInbox", ""), _handle_of(signer), now))
        db.commit()
        accept = {"@context": CONTEXT[0], "id": f"{actor_id()}#accept-{hashlib.sha1(str(act.get('id')).encode(), usedforsecurity=False).hexdigest()[:12]}",
                  "type": "Accept", "actor": actor_id(), "object": act}
        deliver(accept, {signer.get("inbox")})
    elif kind == "Undo" and isinstance(obj, dict):
        if obj.get("type") == "Follow":
            db.execute("DELETE FROM ap_followers WHERE actor=?", (signer["id"],))
        elif obj.get("type") in ("Like", "Announce"):
            db.execute("DELETE FROM ap_interactions WHERE activity_id=? AND actor=?", (obj.get("id"), signer["id"]))
        db.commit()
    elif kind in ("Like", "Announce"):
        slug = _local_slug(_object_id(obj))
        if slug and act.get("id"):
            db.execute("INSERT OR IGNORE INTO ap_interactions (activity_id, kind, actor, post_slug, created_at) "
                       "VALUES (?, ?, ?, ?, ?)", (act["id"], "like" if kind == "Like" else "boost", signer["id"], slug, now))
            db.commit()
    elif kind in ("Create", "Update") and isinstance(obj, dict) and obj.get("type") in ("Note", "Article"):
        slug = _reply_target(obj)
        if not slug or not obj.get("id"):
            return
        body = _plain(obj.get("content", ""))[:2000]
        existing = db.execute("SELECT id FROM comments WHERE source_url=?", (obj["id"],)).fetchone()
        if existing:
            db.execute("UPDATE comments SET body=? WHERE id=?", (body, existing["id"]))
        else:
            parent = None
            target = obj.get("inReplyTo") or ""
            m = re.match(re.escape(config.BASE_URL) + r"/ap/note/(\d+)$", target if isinstance(target, str) else "")
            if m:
                parent = int(m.group(1))
            else:
                row = db.execute("SELECT id FROM comments WHERE source_url=?", (target,)).fetchone()
                parent = row["id"] if row else None
            from soloblog.render import web_url
            icon = signer.get("icon")
            icon = web_url(icon.get("url", "")) if isinstance(icon, dict) else ""
            db.execute(
                "INSERT INTO comments (post_slug, author_name, email, body, approved, confirmed_at, parent_id, "
                "created_at, source, source_url, author_url, author_photo) VALUES (?, ?, '', ?, 0, ?, ?, ?, "
                "'activitypub', ?, ?, ?)",
                (slug, (signer.get("name") or _handle_of(signer))[:80], body, now, parent, now, obj["id"],
                 web_url(signer.get("url")) or web_url(signer["id"]), icon))
            from soloblog import notify
            notify.comment_waiting(slug, (signer.get("name") or _handle_of(signer))[:80], re.sub(r"<[^>]+>", " ", body))
        db.commit()
    elif kind == "Delete":
        oid = _object_id(obj)
        if oid == signer["id"]:
            db.execute("DELETE FROM ap_followers WHERE actor=?", (oid,))
            db.execute("DELETE FROM ap_interactions WHERE actor=?", (oid,))
        else:
            db.execute("DELETE FROM comments WHERE source_url=? AND source='activitypub'", (oid,))
        db.commit()


_inbox_queue = queue.Queue()
_inbox_worker = None
_worker_lock = threading.Lock()


def receive(method: str, path: str, headers: dict, body: bytes):
    """Queues an inbox delivery - the sender gets its 202 straight away,
    and the signature check and the work happen on a background thread."""
    global _inbox_worker
    with _worker_lock:
        if _inbox_worker is None:
            _inbox_worker = threading.Thread(target=_inbox_loop, name="ap-inbox", daemon=True)
            _inbox_worker.start()
    _inbox_queue.put((method, path, headers, body))


def _inbox_loop():
    while True:
        method, path, headers, body = _inbox_queue.get()
        try:
            act = json.loads(body)
            if act.get("type") == "Delete" and act.get("actor") == _object_id(act.get("object")):
                # an account being deleted: its key is gone too, so only
                # act if we know the account already
                known = get_db().execute("SELECT 1 FROM ap_followers WHERE actor=?", (act.get("actor"),)).fetchone()
                if known:
                    try:
                        handle_activity(act, verify(method, path, headers, body))
                    except Exception as e:
                        # usually the key went with the account, so it can't
                        # be checked - routine, so not a warning
                        log.info("couldn't act on the deletion of %s: %s", act.get("actor"), e)
                continue
            handle_activity(act, verify(method, path, headers, body))
        except Exception as e:
            log.warning("an incoming fediverse message failed: %s", e)
        finally:
            _inbox_queue.task_done()


# ---- delivery

_out_queue = queue.Queue()
_out_worker = None


def deliver(doc: dict, targets):
    """Sends doc to each inbox in targets, in the background. A server
    that's down gets one more try a few minutes later."""
    global _out_worker
    targets = {t for t in targets if t}
    if not targets:
        return
    with _worker_lock:
        if _out_worker is None:
            _out_worker = threading.Thread(target=_out_loop, name="ap-deliver", daemon=True)
            _out_worker.start()
    for inbox in targets:
        _out_queue.put((inbox, doc, 0))


def _out_loop():
    while True:
        inbox, doc, attempt = _out_queue.get()
        try:
            status = signed_post(inbox, doc)
            if status >= 500 and attempt == 0:
                log.info("delivery to %s answered HTTP %s - trying again in five minutes", inbox, status)
                # bound now: by the time it fires, the loop has moved on to other deliveries
                threading.Timer(300, lambda inbox=inbox, doc=doc: _out_queue.put((inbox, doc, 1))).start()
            elif status >= 300:
                # info, not a warning: a follower's server that's gone or
                # has blocked this one is routine, and nothing the admin can fix
                log.info("delivery to %s refused: HTTP %s", inbox, status)
        except Exception as e:
            log.warning("delivery to %s failed: %s", inbox, e)
        finally:
            _out_queue.task_done()


def wait():
    _inbox_queue.join()
    _out_queue.join()


def publish(row, update: bool = False):
    """A new (or edited) post, to every follower."""
    obj = post_object(row)
    deliver(activity("Update" if update else "Create", obj,
                     f"-{int(time.time())}" if update else ""), inboxes())


def retract(slug: str):
    """A post that's gone (trashed) - followers' servers remove it."""
    url = f"{config.BASE_URL}/post/{slug}"
    tomb = {"id": url, "type": "Tombstone", "to": [AS_PUBLIC], "cc": [f"{config.BASE_URL}/ap/followers"]}
    deliver(activity("Delete", tomb, f"-{int(time.time())}"), inboxes())


def reply(comment_id: int):
    """The author's reply to a comment that came from the fediverse goes
    back there, so the conversation carries on where it started."""
    from soloblog import comments
    if not enabled():
        return
    mine = comments.get(comment_id)
    parent = comments.get(mine["parent_id"]) if mine and mine["parent_id"] else None
    if not parent or parent["source"] != "activitypub":
        return
    db = get_db()
    row = db.execute("SELECT data FROM ap_actors WHERE json_extract(data, '$.url') = ? OR id = ?",
                     (parent["author_url"], parent["author_url"])).fetchone()
    author = json.loads(row["data"]) if row else None
    if not author:
        return
    reply_to = {"source_url": parent["source_url"], "author_url": parent["author_url"],
                "author_name": _handle_of(author), "actor": author["id"]}
    note = note_object(mine, reply_to)
    deliver(activity("Create", note), {author.get("inbox")} | inboxes())


def note_for(comment_id: int):
    """GET /ap/note/<id> - only the author's own replies are notes."""
    from soloblog import comments
    mine = comments.get(comment_id)
    if not mine or not mine["is_author"] or mine["trashed_at"]:
        return None
    parent = comments.get(mine["parent_id"]) if mine["parent_id"] else None
    if not parent or parent["source"] != "activitypub":
        return None
    reply_to = {"source_url": parent["source_url"], "author_url": parent["author_url"],
                "author_name": parent["author_name"], "actor": parent["author_url"]}
    return note_object(mine, reply_to)


def interactions(slug: str) -> dict:
    rows = get_db().execute("SELECT kind, COUNT(*) AS n FROM ap_interactions WHERE post_slug=? GROUP BY kind",
                            (slug,)).fetchall()
    return {r["kind"]: r["n"] for r in rows}
