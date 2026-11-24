import re
import hashlib
from datetime import datetime, UTC

from soloblog import storage

EMPTY = hashlib.sha256(b"").hexdigest()
AK, SK = "AKIAIOSFODNN7EXAMPLE", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
WHEN = datetime(2013, 5, 24, tzinfo=UTC)


def _signature(headers):
    return headers["Authorization"].rsplit("Signature=", 1)[1]


def test_sigv4_get_object_example():
    # AWS's own worked example: "Signature Calculations for the
    # Authorization Header", GET Object
    h = storage.sign("GET", "https://examplebucket.s3.amazonaws.com/test.txt", {"Range": "bytes=0-9"},
                     EMPTY, AK, SK, "us-east-1", now=WHEN)
    assert _signature(h) == "f0e8bdb87c964420e857bd35b5d6ed310bd44f0170aba48dd91039c6036bdb41"
    assert "SignedHeaders=host;range;x-amz-content-sha256;x-amz-date" in h["Authorization"]


def test_sigv4_list_objects_example():
    h = storage.sign("GET", "https://examplebucket.s3.amazonaws.com/?max-keys=2&prefix=J", {},
                     EMPTY, AK, SK, "us-east-1", now=WHEN)
    assert _signature(h) == "34b48302e7b5fa45bde8084f4b7868a86f0a534bc59db6670ed5711ef69dc6f7"


# ---- against a real S3 API (moto's local server), not a mock of our own

import os
import socket
import tempfile
import time

import pytest

from soloblog import config


@pytest.fixture
def bucket(monkeypatch):
    moto_server = pytest.importorskip("moto.server")
    with socket.socket() as sk:
        sk.bind(("127.0.0.1", 0))
        port = sk.getsockname()[1]
    server = moto_server.ThreadedMotoServer(ip_address="127.0.0.1", port=port, verbose=False)
    server.start()
    for name, value in {"S3_BUCKET": "soloblog-test", "S3_ENDPOINT": f"http://127.0.0.1:{port}",
                        "S3_REGION": "us-east-1", "S3_ACCESS_KEY_ID": "test", "S3_SECRET_ACCESS_KEY": "test",
                        "S3_PREFIX": "blog", "S3_AUTO_BACKUP": False}.items():
        monkeypatch.setattr(config, name, value)
    status, _ = storage._request("PUT")  # create the bucket
    assert status == 200
    yield
    server.stop()


def test_round_trip(bucket):
    storage.put("uploads/a b.webp", b"hello")
    assert storage.get("uploads/a b.webp") == b"hello"
    assert storage.get("uploads/missing.webp") is None
    assert [k["key"] for k in storage.list_keys("uploads/")] == ["uploads/a b.webp"]
    storage.delete("uploads/a b.webp")
    assert storage.list_keys("uploads/") == []
    assert storage.check() == ""


def test_bad_credentials_are_reported(bucket, monkeypatch):
    monkeypatch.setattr(config, "S3_ENDPOINT", "http://127.0.0.1:9")  # nothing listening
    assert "can't reach" in storage.check()


def test_an_endpoint_without_https_is_taken_as_shown(monkeypatch):
    # Backblaze shows "s3.us-west-004.backblazeb2.com", with no https://
    monkeypatch.setattr(config, "S3_ENDPOINT", "s3.us-west-004.backblazeb2.com")
    assert storage.endpoint() == "https://s3.us-west-004.backblazeb2.com"
    monkeypatch.setattr(config, "S3_ENDPOINT", "http://127.0.0.1:9000")
    assert storage.endpoint() == "http://127.0.0.1:9000"


@pytest.mark.parametrize("junk", ["https://", "ftp://example.com", "://nothing", "https://exa mple.com/x"])
def test_an_endpoint_that_isnt_an_address_is_said_not_crashed(bucket, monkeypatch, admin, junk):
    # the Backup and import page shows why, as for a wrong key - never a server error
    monkeypatch.setattr(config, "S3_ENDPOINT", junk)
    assert storage.check()
    assert admin.get("/admin/settings?tab=backup").status_code == 200


def _png():
    from PIL import Image
    import io
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), "red").save(buf, "PNG")
    return buf.getvalue()


def test_images_are_mirrored(bucket, client):
    from soloblog import images
    url = images.save_upload(_png())
    name = url.rsplit("/", 1)[1]
    storage.wait_for_mirroring()  # mirroring runs in the background
    assert storage.get(f"uploads/{name}") is not None
    images.move_to_trash(name)
    storage.wait_for_mirroring()
    assert storage.get(f"uploads/{name}") is None and storage.get(f"uploads/_trash/{name}") is not None
    images.restore_from_trash(name)
    storage.wait_for_mirroring()
    assert storage.get(f"uploads/{name}") is not None

    # a disk that lost the file gets it back from the bucket on request
    os.remove(os.path.join(config.UPLOADS_DIR, name))
    r = client.get(url)
    assert r.status_code == 200 and os.path.exists(os.path.join(config.UPLOADS_DIR, name))


def test_backups_are_pruned(bucket, monkeypatch):
    from soloblog import settings
    settings.set_many({"backup_keep": "2"})
    for _ in range(3):
        storage.backup_now()
        time.sleep(1.05)  # backup names are per second
    assert len(storage.list_backups()) == 2
    settings.set_many({"backup_keep": "30"})


def test_change_triggers_debounced_backup(bucket, monkeypatch, admin):
    monkeypatch.setattr(config, "S3_AUTO_BACKUP", True)
    monkeypatch.setattr(config, "S3_BACKUP_DELAY", 0.3)
    before = len(storage.list_backups())
    admin.post("/admin/settings/name", headers={"hx-request": "true"},
               data={"site_title": "My Blog", "comments_enabled": "1", "timezone": "UTC"})
    admin.post("/admin/settings/name", headers={"hx-request": "true"},
               data={"site_title": "My Blog", "comments_enabled": "1", "timezone": "UTC"})
    time.sleep(1.5)
    assert len(storage.list_backups()) == before + 1  # two changes, one backup


def test_backups_once_a_day(bucket, monkeypatch, admin):
    from datetime import timedelta
    from soloblog import settings
    from soloblog.tz import utcnow
    monkeypatch.setattr(config, "S3_AUTO_BACKUP", True)
    monkeypatch.setattr(config, "S3_BACKUP_DELAY", 0.3)
    assert "How often" in admin.get("/admin/backup/cloud").text
    assert "Saved" in admin.post("/admin/backup/every", data={"backup_every": "day"}).text
    assert "Choose one" in admin.post("/admin/backup/every", data={"backup_every": "hourly"}).text
    assert settings.get("backup_every") == "day"

    def nothing_waiting():
        with storage._lock:
            if storage._state["timer"]:
                storage._state["timer"].cancel()
            storage._state["timer"] = storage._state["first_change"] = None
    try:
        nothing_waiting()  # saving the setting was a change too
        # the last one an hour ago: a change waits for the rest of the day
        settings.set_many({"backup_last_at": (utcnow() - timedelta(hours=1)).isoformat()})
        before = len(storage.list_backups())
        storage.note_change()
        timer = storage._state["timer"]
        assert timer and 22 * 3600 < timer.interval < 23 * 3600
        storage.note_change()  # more changes: still the one backup, not moved on
        assert storage._state["timer"] is timer
        # shutting down makes it now, so nothing's lost
        storage.flush()
        assert len(storage.list_backups()) == before + 1 and storage._state["timer"] is None
        # nothing changed since: nothing waiting
        assert storage._state["timer"] is None
        # a day since the last one: the next change backs up straight away
        settings.set_many({"backup_last_at": (utcnow() - timedelta(days=2)).isoformat()})
        storage.note_change()
        assert storage._state["timer"].interval == 0.3
        # changed to once a week: what's waiting is timed again
        settings.set_many({"backup_last_at": utcnow().isoformat(), "backup_every": "week"})
        storage.reschedule()
        assert storage._state["timer"].interval > 6 * 24 * 3600
    finally:
        nothing_waiting()
        settings.set_many({"backup_every": "changes"})


def test_restore_on_an_empty_disk(bucket, monkeypatch, admin):
    from conftest import save_post
    from soloblog import images
    save_post(admin, title="Survives a restart")
    name = images.save_upload(_png()).rsplit("/", 1)[1]
    storage.backup_now()

    fresh = tempfile.mkdtemp()
    monkeypatch.setattr(config, "DB_PATH", os.path.join(fresh, "blog.db"))
    monkeypatch.setattr(config, "POSTS_DIR", os.path.join(fresh, "posts"))
    monkeypatch.setattr(config, "UPLOADS_DIR", os.path.join(fresh, "uploads"))
    assert storage.restore_on_boot()
    assert os.path.exists(os.path.join(fresh, "blog.db"))
    assert os.path.exists(os.path.join(fresh, "posts", "survives-a-restart.md"))
    assert os.path.exists(os.path.join(fresh, "uploads", name))
    # and never over a disk that already has a database
    assert not storage.restore_on_boot()


def test_seal_round_trip_and_wrong_passphrase():
    sealed = storage.seal(b"zip bytes", "correct horse")
    assert sealed.startswith(storage.MAGIC) and b"zip bytes" not in sealed
    assert storage.unseal(sealed, "correct horse") == b"zip bytes"
    for wrong in ("battery staple", ""):
        with pytest.raises(storage.StorageError):
            storage.unseal(sealed, wrong)
    tampered = sealed[:-1] + bytes([sealed[-1] ^ 1])
    with pytest.raises(storage.StorageError):
        storage.unseal(tampered, "correct horse")


def test_encrypted_backup_restores_on_an_empty_disk(bucket, monkeypatch, admin):
    from conftest import save_post
    monkeypatch.setattr(config, "BACKUP_PASSPHRASE", "correct horse")
    save_post(admin, title="Encrypted and back")
    key = storage.backup_now()
    assert key.endswith(".zip.enc") and storage.list_backups()[0]["key"] == key
    assert storage.get(key).startswith(storage.MAGIC)

    fresh = tempfile.mkdtemp()
    monkeypatch.setattr(config, "DB_PATH", os.path.join(fresh, "blog.db"))
    monkeypatch.setattr(config, "POSTS_DIR", os.path.join(fresh, "posts"))
    monkeypatch.setattr(config, "UPLOADS_DIR", os.path.join(fresh, "uploads"))
    assert storage.restore_on_boot()
    assert os.path.exists(os.path.join(fresh, "posts", "encrypted-and-back.md"))


def test_images_in_the_bucket_are_encrypted_with_the_passphrase(bucket, monkeypatch, client):
    from soloblog import images, settings
    plain_url = images.save_upload(_png())
    plain = plain_url.rsplit("/", 1)[1]
    storage.wait_for_mirroring()
    original = storage.get(f"uploads/{plain}")
    assert not original.startswith(storage.MAGIC)
    settings.set_many({"bucket_images_sealed": ""})

    monkeypatch.setattr(config, "BACKUP_PASSPHRASE", "correct horse")
    try:
        # a new image goes in sealed: the storage company sees nothing of it
        url = images.save_upload(_png())
        name = url.rsplit("/", 1)[1]
        storage.wait_for_mirroring()
        sealed = storage.get(f"uploads/{name}")
        assert sealed.startswith(storage.MAGIC) and b"PNG" not in sealed and b"WEBP" not in sealed
        with open(os.path.join(config.UPLOADS_DIR, name), "rb") as f:
            assert storage.unseal(sealed, "correct horse") == f.read()
        # trashing it keeps it sealed
        images.move_to_trash(name)
        storage.wait_for_mirroring()
        assert storage.get(f"uploads/_trash/{name}").startswith(storage.MAGIC)
        images.restore_from_trash(name)
        storage.wait_for_mirroring()
        # a disk that lost it gets it back, opened
        os.remove(os.path.join(config.UPLOADS_DIR, name))
        assert client.get(url).status_code == 200
        with open(os.path.join(config.UPLOADS_DIR, name), "rb") as f:
            assert storage.unseal(sealed, "correct horse") == f.read()
        # one copied before the passphrase was set still opens...
        os.remove(os.path.join(config.UPLOADS_DIR, plain))
        assert client.get(plain_url).status_code == 200
        # ...and is sealed too, once: on the next start, or Sync images
        assert storage.reseal_images() >= 2
        assert storage.get(f"uploads/{plain}").startswith(storage.MAGIC)
        assert storage.reseal_images() == 0
        # Sync images brings sealed ones down opened
        os.remove(os.path.join(config.UPLOADS_DIR, plain))
        assert storage.sync_uploads()["downloaded"] >= 1
        with open(os.path.join(config.UPLOADS_DIR, plain), "rb") as f:
            assert f.read() == original
        # the wrong passphrase: the image isn't fetched, and nothing breaks
        os.remove(os.path.join(config.UPLOADS_DIR, plain))
        monkeypatch.setattr(config, "BACKUP_PASSPHRASE", "battery staple")
        assert not storage.fetch_upload(plain)
        # the passphrase removed: copied again, plain
        monkeypatch.setattr(config, "BACKUP_PASSPHRASE", "")
        assert storage.reseal_images() >= 1
        assert not storage.get(f"uploads/{name}").startswith(storage.MAGIC)
    finally:
        settings.set_many({"bucket_images_sealed": ""})


def test_a_failed_automatic_backup_is_remembered_until_one_works(bucket, monkeypatch):
    # kept in settings, so a restart doesn't hide it from Site health
    from soloblog import settings
    working = config.S3_ENDPOINT
    monkeypatch.setattr(config, "S3_ENDPOINT", "http://127.0.0.1:9")  # nothing listening
    storage._state["last_result"] = ""
    storage._run_scheduled()
    assert "can't reach" in settings.get("backup_last_error")
    storage._state["last_result"] = ""  # as after a restart
    assert "can't reach" in storage.last_status()["error"]
    monkeypatch.setattr(config, "S3_ENDPOINT", working)
    storage.backup_now()
    assert settings.get("backup_last_error") == "" and storage.last_status()["error"] == ""


def test_a_refusal_is_said_in_plain_words():
    # what the bucket says, as words that name the setting to check - never its raw XML
    xml = (b'<?xml version="1.0" encoding="UTF-8"?>\n<Error>\n <Code>InvalidAccessKeyId</Code>\n'
           b' <Message>The key &apos;000abc&apos; is not valid</Message>\n</Error>\n')
    said = str(storage._refused("Listing", 403, xml))
    assert said.startswith("Listing failed (403): ") and "S3_ACCESS_KEY_ID" in said and "<" not in said
    for code, setting in (("SignatureDoesNotMatch", "S3_SECRET_ACCESS_KEY"), ("NoSuchBucket", "S3_BUCKET"),
                          ("AuthorizationHeaderMalformed", "S3_REGION")):
        assert setting in str(storage._refused("Upload", 403, f"<Error><Code>{code}</Code></Error>".encode()))
    # one it doesn't know keeps the bucket's own words, unescaped
    other = str(storage._refused("Upload", 500, b"<Error><Code>Busy</Code><Message>Try &apos;later&apos;</Message></Error>"))
    assert other == "Upload failed (500): Try 'later'"
    assert str(storage._refused("Upload", 502, b"")) == "Upload failed (502)"


def test_the_newest_backups_show_and_the_rest_fold(monkeypatch, admin):
    # the newest few with Restore as a row icon; the rest under Older backups, all restorable
    from datetime import timedelta
    fake = [{"key": f"backups/soloblog-{i}.zip", "size": 168_000, "modified": (WHEN - timedelta(hours=i)).isoformat()}
            for i in range(7)]
    monkeypatch.setattr(storage, "enabled", lambda: True)
    monkeypatch.setattr(storage, "check", lambda: "")
    monkeypatch.setattr(storage, "list_backups", lambda: fake)
    html = admin.get("/admin/backup/cloud").text
    shown, folded = html.split("Older backups (4)")
    assert shown.count('name="key" value="backups/soloblog-') == 3 and "Latest" in shown
    assert folded.count('name="key" value="backups/soloblog-') == 4
    # an icon named Restore, not a word button
    assert 'aria-label="Restore"' in shown and 'class="ml-1">Restore<' not in shown
    # the older ones scroll up and down in their box, never sideways
    assert "overflow-y-auto overflow-x-hidden" in folded


def test_restoring_a_bucket_backup_says_which_and_comes_into_view(monkeypatch, admin):
    # the Restore card fills up the page from Cloud storage's list - it says
    # which backup it's from, and is marked to be brought into view
    from soloblog import backup
    data = backup.build_backup_zip({"posts", "settings"})
    monkeypatch.setattr(storage, "enabled", lambda: True)
    monkeypatch.setattr(storage, "check", lambda: "")
    monkeypatch.setattr(storage, "list_backups", lambda: [])
    monkeypatch.setattr(storage, "get_backup", lambda key, raw=False: data)
    html = admin.post("/admin/backup/from-bucket", data={"key": "backups/soloblog-20261119-162700.zip"}).text
    restore = re.search(r'<details[^>]*data-panel="backup-restore"[^>]*>', html).group(0)
    assert "data-arrive" in restore
    assert re.search(r"From your backup of [^<]*2026", html)
    backup.discard_staged()


def _write_upload(name, data):
    os.makedirs(config.uploads_dir(), exist_ok=True)
    with open(os.path.join(config.uploads_dir(), name), "wb") as f:
        f.write(data)


def test_sync_images_goes_the_way_asked_and_deletes_nothing(bucket, admin):
    _write_upload("same-name.png", b"this site's")
    _write_upload("only-here.png", b"here")
    storage.put("uploads/same-name.png", b"the bucket's")
    storage.put("uploads/only-there.png", b"there")
    # this site to the bucket: its copies replace the bucket's; the bucket's own stays
    r = admin.post("/admin/backup/sync?way=up")
    assert re.search(r"Copied \d+ images to your bucket", r.headers["location"].replace("%20", " "))
    assert storage.get("uploads/same-name.png") == b"this site's"
    assert storage.get("uploads/only-there.png") == b"there"
    # the bucket to this site: its copies replace these; this site's own stays
    storage.put("uploads/same-name.png", b"the bucket's again")
    admin.post("/admin/backup/sync?way=down")
    with open(os.path.join(config.uploads_dir(), "same-name.png"), "rb") as f:
        assert f.read() == b"the bucket's again"
    assert os.path.isfile(os.path.join(config.uploads_dir(), "only-here.png"))
    assert os.path.isfile(os.path.join(config.uploads_dir(), "only-there.png"))
    for name in ("same-name.png", "only-here.png", "only-there.png"):
        os.remove(os.path.join(config.uploads_dir(), name))


def test_an_image_that_didnt_reach_the_bucket_is_said_until_it_does(bucket, monkeypatch, admin):
    from soloblog import health, settings
    settings.set_many({"images_not_in_bucket": ""})
    working = config.S3_ENDPOINT
    monkeypatch.setattr(config, "S3_ENDPOINT", "http://127.0.0.1:9")  # nothing listening
    storage._mirror(storage._put_image, "uploads/lost.png", b"x")
    storage.wait_for_mirroring()
    assert storage.unsynced() == {"uploads/lost.png"}
    assert health.bucket_images_check()["title"] == "1 image hasn't reached your bucket"
    monkeypatch.setattr(config, "S3_ENDPOINT", working)
    monkeypatch.setattr(storage, "check", lambda: "")
    assert "1 image hasn&#x27;t reached your bucket" in admin.get("/admin/backup/cloud").text \
        or "1 image hasn't reached your bucket" in admin.get("/admin/backup/cloud").text
    # once it's copied, it's no longer said
    storage._put_image("uploads/lost.png", b"x")
    assert storage.unsynced() == set() and health.bucket_images_check() is None


def test_a_bucket_restore_brings_images_back_when_ticked(bucket, admin):
    from soloblog import backup
    storage.put("uploads/from-bucket.png", b"bucket copy")
    data = backup.build_backup_zip({"posts", "settings"})
    storage.put("backups/soloblog-20261119-162700.zip", data)
    html = admin.post("/admin/backup/from-bucket", data={"key": "backups/soloblog-20261119-162700.zip"}).text
    assert 'name="images_from_bucket"' in html and "the latest copy of each, from your bucket" in html
    r = admin.post("/admin/backup/restore-confirm", data={"settings": "1", "images_from_bucket": "1"})
    said = r.headers["location"].replace("%20", " ")
    assert "image" in said and "(s)" not in said
    with open(os.path.join(config.uploads_dir(), "from-bucket.png"), "rb") as f:
        assert f.read() == b"bucket copy"
    os.remove(os.path.join(config.uploads_dir(), "from-bucket.png"))


@pytest.mark.parametrize("passphrase", ["", "a passphrase"])
def test_sync_images_never_copies_the_same_image_again(bucket, monkeypatch, passphrase):
    # a bucket that keeps every version (Backblaze, unless told not to)
    # would keep a second copy of each one
    monkeypatch.setattr(config, "BACKUP_PASSPHRASE", passphrase)
    _write_upload("twice.png", b"the same picture")
    storage.sync_uploads("up")
    puts = []
    real_put = storage.put
    monkeypatch.setattr(storage, "put", lambda key, *a, **kw: (puts.append(key), real_put(key, *a, **kw)))
    counts = storage.sync_uploads("up")
    assert "uploads/twice.png" not in puts and counts["same"] >= 1
    gets = []
    real_get = storage.get
    monkeypatch.setattr(storage, "get", lambda key: (gets.append(key), real_get(key))[1])
    storage.sync_uploads("down")
    assert "uploads/twice.png" not in gets
    # a changed one is copied
    _write_upload("twice.png", b"a cropped picture, longer")
    storage.sync_uploads("up")
    assert "uploads/twice.png" in puts
    os.remove(os.path.join(config.uploads_dir(), "twice.png"))


def test_the_sync_message_says_what_was_already_there():
    from soloblog.routes.backup_routes import _synced
    assert _synced(0, 82, "to") == "Nothing to copy - 82 images already the same on both sides"
    assert _synced(3, 79, "to") == "Copied 3 images to your bucket - 79 were the same already"
    assert _synced(1, 0, "from") == "Copied 1 image from your bucket"


def test_the_backup_page_doesnt_wait_for_the_bucket(monkeypatch, admin):
    # the bucket answers in a second or two: the page comes first, and the
    # Cloud storage card fills itself in from /admin/backup/cloud
    calls = []
    monkeypatch.setattr(storage, "enabled", lambda: True)
    monkeypatch.setattr(storage, "check", lambda: calls.append("check") or "")
    monkeypatch.setattr(storage, "list_backups", lambda: calls.append("list") or [])
    html = admin.get("/admin/settings?tab=backup").text
    assert calls == [] and 'hx-get="/admin/backup/cloud"' in html and "Checking your bucket" in html
    part = admin.get("/admin/backup/cloud").text
    assert "check" in calls and "Back up now" in part and 'id="cloud-status"' in part


def test_a_bucket_backup_from_before_the_passphrase_changed_still_restores(bucket, monkeypatch, admin):
    from soloblog import backup
    sealed = storage.seal(backup.build_backup_zip({"posts", "settings"}), "the old one")
    storage.put("backups/soloblog-20261119-162700.zip.enc", sealed)
    monkeypatch.setattr(config, "BACKUP_PASSPHRASE", "the new one")
    html = admin.post("/admin/backup/from-bucket", data={"key": "backups/soloblog-20261119-162700.zip.enc"}).text
    assert 'name="passphrase"' in html and re.search(r"From your backup of [^<]*2026", html)
    assert re.search(r'<details[^>]*data-panel="backup-restore"[^>]*data-arrive', html) \
        or re.search(r'<details[^>]*data-arrive[^>]*data-panel="backup-restore"', html)
    html = admin.post("/admin/backup/unlock", data={"passphrase": "the old one", "source": "your backup",
                                                    "from_bucket": "1"}).text
    # still offers the bucket's images, as any bucket backup does
    assert 'name="images_from_bucket"' in html
    backup.discard_staged()


# ---- a start that can't bring the site back: held, never a blank site
# backed up over the real one

def _empty_disk(monkeypatch):
    fresh = tempfile.mkdtemp()
    for name, sub in (("DB_PATH", "blog.db"), ("POSTS_DIR", "posts"), ("UPLOADS_DIR", "uploads")):
        monkeypatch.setattr(config, name, os.path.join(fresh, sub))
    return fresh


@pytest.mark.parametrize("why", ["locked", "unreachable", "damaged", "removed"])
def test_a_start_that_cant_restore_holds_the_site(bucket, monkeypatch, admin, why):
    from soloblog import backup
    monkeypatch.setattr(config, "BACKUP_PASSPHRASE", "the old one")
    if why == "damaged":
        storage.put("backups/soloblog-29991231-235959.zip", b"not a zip at all")
    else:
        storage.backup_now()
    real = {name: getattr(config, name) for name in ("DB_PATH", "POSTS_DIR", "UPLOADS_DIR")}
    monkeypatch.setattr(config, "BACKUP_PASSPHRASE", {"removed": ""}.get(why, "the new one"))
    working = config.S3_ENDPOINT
    if why == "unreachable":
        monkeypatch.setattr(config, "S3_ENDPOINT", "http://127.0.0.1:9")  # nothing listening
    fresh = _empty_disk(monkeypatch)
    try:
        assert not storage.restore_on_boot()  # and no crash, even on a file that isn't a zip
        assert storage.held["why"] == {"removed": "locked"}.get(why, why)
        assert not os.path.exists(os.path.join(fresh, "blog.db"))
        # nothing goes to the bucket while it's held
        with pytest.raises(storage.StorageError):
            storage.backup_now()
        monkeypatch.setattr(config, "S3_AUTO_BACKUP", True)
        if storage._state["timer"]:  # one an earlier test left
            storage._state["timer"].cancel()
            storage._state["timer"] = None
        storage.note_change()
        assert storage._state["timer"] is None
        storage._mirror(storage.delete, "backups/anything")
        assert storage._mirror_queue.empty()
    finally:
        storage.release_hold()
        for name, value in real.items():
            monkeypatch.setattr(config, name, value)
        if why == "damaged":  # the test bucket outlives the test
            monkeypatch.setattr(config, "S3_ENDPOINT", working)
            storage.delete("backups/soloblog-29991231-235959.zip")
    backup.discard_staged()


def test_a_restore_cut_short_runs_again_rather_than_leaving_no_posts(monkeypatch):
    import io
    import zipfile
    fresh = _empty_disk(monkeypatch)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("posts/a.md", "---\ntitle: A\n---\nA")
        zf.writestr("blog.db", b"this isn't a database")
    with pytest.raises(storage.StorageError):
        storage.unpack_backup(buf.getvalue())
    assert not os.path.exists(os.path.join(fresh, "blog.db"))
    assert not os.path.exists(os.path.join(fresh, "blog.db.restoring"))


def test_setup_brings_a_held_site_back_with_the_old_passphrase(bucket, monkeypatch, admin, client):
    # a host without a disk, its passphrase changed: the restart can't open
    # the newest backup, so setup asks for the old one and restores it all
    from conftest import save_post
    from soloblog import auth, images, posts
    from soloblog.db import get_db
    monkeypatch.setattr(config, "BACKUP_PASSPHRASE", "the old one")
    save_post(admin, title="Brought back whole")
    name = images.save_upload(_png()).rsplit("/", 1)[1]
    storage.wait_for_mirroring()
    key = storage.backup_now()
    monkeypatch.setattr(config, "BACKUP_PASSPHRASE", "the new one")
    real = {n: getattr(config, n) for n in ("DB_PATH", "POSTS_DIR", "UPLOADS_DIR")}
    _empty_disk(monkeypatch)
    storage.restore_on_boot()
    for n, value in real.items():
        monkeypatch.setattr(config, n, value)
    assert storage.held["why"] == "locked"
    # this disk, as a blank start would have it
    row = get_db().execute("SELECT * FROM admin WHERE id=1").fetchone()
    get_db().execute("DELETE FROM admin")
    get_db().commit()
    os.remove(os.path.join(config.posts_dir(), "brought-back-whole.md"))
    os.remove(os.path.join(config.uploads_dir(), name))
    try:
        page = client.get("/setup").text
        assert "Restore your site" in page and 'name="passphrase"' in page and f'value="{key}"' in page
        assert 'action="/setup/restore"' in page and 'href="/setup?new=1"' in page
        token = auth.setup_token()
        tries = [({"token": "not it", "key": key, "passphrase": "the old one"}, "setup token isn"),
                 ({"token": token, "key": key, "passphrase": "the new one"}, "Wrong passphrase, try again"),
                 ({"token": token, "key": key, "passphrase": "x" * 5000}, "Wrong passphrase, try again"),
                 ({"token": token, "key": key, "passphrase": ""}, "Type the passphrase"),
                 ({"token": token, "key": "backups/../../etc/passwd", "passphrase": "the old one"},
                  "couldn&#x27;t be opened")]
        for data, said in tries:
            r = client.post("/setup/restore", data=data)
            assert r.status_code == 200 and (said in r.text or said.replace("&#x27;", "'") in r.text), data
            assert not auth.admin_exists() and storage.held
        # a fresh start is there too, and says the backups stay
        assert "each new backup replaces the oldest" in client.get("/setup?new=1").text
        r = client.post("/setup/restore", data={"token": token, "key": key, "passphrase": "the old one"})
        assert r.status_code == 303 and r.headers["location"] == "/login?back=1"
        assert "Your site is back" in client.get("/login?back=1").text
        assert auth.admin_exists() and not storage.held
        assert posts.get_post("brought-back-whole")
        # its image is back, and locked again the new way in the bucket
        assert os.path.isfile(os.path.join(config.uploads_dir(), name))
        assert storage._from_bucket(storage.get(f"uploads/{name}"))
        # and a backup the new way already, so the next start opens it
        newest = storage.list_backups()[0]["key"]
        assert storage.get_backup(newest)  # opens with the new passphrase
    finally:
        storage.release_hold()
        if not auth.admin_exists():
            get_db().execute("INSERT INTO admin VALUES (?, ?, ?, ?, ?, ?)", tuple(row))
            get_db().commit()


def test_a_fresh_start_over_held_backups_is_the_owners_choice(bucket, monkeypatch, admin, client):
    from soloblog import auth
    from soloblog.db import get_db
    # nothing restores over a site that has its admin
    storage.held["why"] = "locked"
    assert client.post("/setup/restore", data={"token": auth.setup_token()}).status_code == 303
    row = get_db().execute("SELECT * FROM admin WHERE id=1").fetchone()
    get_db().execute("DELETE FROM admin")
    get_db().commit()
    try:
        # its errors keep the fresh-start form, not the restore one
        r = client.post("/setup", data={"token": "not it", "password": "x", "confirm": "x", "new": "1"})
        assert "Set up your site" in r.text and "Restore your site" not in r.text
        assert storage.held  # only setting up a new site lets it go
    finally:
        storage.release_hold()
        get_db().execute("INSERT INTO admin VALUES (?, ?, ?, ?, ?, ?)", tuple(row))
        get_db().commit()


def test_restoring_a_locked_bucket_backup_opens_its_images_with_the_passphrase_typed(bucket, monkeypatch, admin):
    from soloblog import backup, images
    monkeypatch.setattr(config, "BACKUP_PASSPHRASE", "the old one")
    name = images.save_upload(_png()).rsplit("/", 1)[1]
    storage.wait_for_mirroring()
    key = storage.backup_now()
    monkeypatch.setattr(config, "BACKUP_PASSPHRASE", "the new one")
    os.remove(os.path.join(config.uploads_dir(), name))
    admin.post("/admin/backup/from-bucket", data={"key": key})
    admin.post("/admin/backup/unlock", data={"passphrase": "the old one", "from_bucket": "1"})
    admin.post("/admin/backup/restore-confirm", data={"images_from_bucket": "1"})
    assert os.path.isfile(os.path.join(config.uploads_dir(), name))
    assert storage._from_bucket(storage.get(f"uploads/{name}"))  # locked the new way now
    assert backup.typed_passphrase() == ""  # gone with the backup


def test_a_restart_after_a_held_start_is_still_held_then_restores(bucket, monkeypatch, admin):
    # a disk that's kept: the held start left a blank database, which the
    # next start mustn't take for the site
    from soloblog.db import run_migrations, get_db, _local
    monkeypatch.setattr(config, "BACKUP_PASSPHRASE", "the old one")
    from conftest import save_post
    save_post(admin, title="Back after two starts")
    storage.backup_now()
    real = {n: getattr(config, n) for n in ("DB_PATH", "POSTS_DIR", "UPLOADS_DIR")}
    monkeypatch.setattr(config, "BACKUP_PASSPHRASE", "the new one")
    fresh = _empty_disk(monkeypatch)
    conn = getattr(_local, "conn", None)
    try:
        storage.restore_on_boot()
        assert storage.held["why"] == "locked"
        del _local.conn
        run_migrations()  # the blank database a held start makes
        get_db().close()
        del _local.conn
        assert os.path.exists(os.path.join(fresh, "blog.db"))
        storage.restore_on_boot()  # restarted, still the wrong passphrase
        assert storage.held["why"] == "locked"
        monkeypatch.setattr(config, "BACKUP_PASSPHRASE", "the old one")  # put back on the host
        assert storage.restore_on_boot() and not storage.held
        assert os.path.exists(os.path.join(fresh, "posts", "back-after-two-starts.md"))
        assert storage._has_admin(os.path.join(fresh, "blog.db"))
        assert not os.path.exists(storage._held_path())
    finally:
        storage.release_hold()
        if conn is not None:
            _local.conn = conn
        for n, value in real.items():
            monkeypatch.setattr(config, n, value)
