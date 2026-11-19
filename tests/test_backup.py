from pathlib import Path
import os
import re
import time

from soloblog import backup
from conftest import save_post


def _wide_image(name):
    """An upload wide enough to get smaller copies."""
    from PIL import Image
    from soloblog import config
    os.makedirs(config.UPLOADS_DIR, exist_ok=True)
    Image.new("RGB", (1200, 800), (30, 120, 200)).save(os.path.join(config.UPLOADS_DIR, name), "WEBP")
    return name


def _upload(admin):
    data = backup.build_backup_zip({"posts"})
    return admin.post("/admin/backup/inspect", files={"backup_zip": ("site.zip", data, "application/zip")})


def test_an_uploaded_backup_is_looked_at_then_restored(admin):
    save_post(admin, title="In the backup")
    r = _upload(admin)
    # what's inside, to choose from - nothing restored yet
    assert r.status_code == 200 and 'action="/admin/backup/restore-confirm"' in r.text
    assert os.path.exists(backup.STAGED_RESTORE_PATH)
    r = admin.post("/admin/backup/restore-confirm", data={"posts": "1"})
    assert r.status_code == 303 and "Restored" in r.headers["location"]
    # restored: the copy waiting on the server is gone
    assert not os.path.exists(backup.STAGED_RESTORE_PATH)


def test_discard_deletes_the_upload(admin, client):
    _upload(admin)
    page = admin.get("/admin/settings?tab=backup").text
    # not restored yet: it's shown, not left on the disk unseen
    assert "hasn&#x27;t been restored" in page or "hasn't been restored" in page
    assert 'formaction="/admin/backup/discard"' in page and "data-confirm" in page
    # only the admin can discard it
    assert client.post("/admin/backup/discard").status_code in (302, 303, 401, 403)
    assert os.path.exists(backup.STAGED_RESTORE_PATH)
    r = admin.post("/admin/backup/discard")
    assert r.status_code == 303 and "Discarded" in r.headers["location"]
    assert not os.path.exists(backup.STAGED_RESTORE_PATH)
    assert "Upload a backup to see" in admin.get("/admin/settings?tab=backup").text


def test_a_waiting_upload_can_be_picked_up_again(admin):
    _upload(admin)
    r = admin.post("/admin/backup/pending")
    assert r.status_code == 200 and 'action="/admin/backup/restore-confirm"' in r.text
    backup.discard_staged()
    r = admin.post("/admin/backup/pending")
    assert r.status_code == 303 and "expired" in r.headers["location"]


def test_an_upload_left_for_a_day_goes(admin):
    _upload(admin)
    old = time.time() - backup.STAGED_MAX_AGE - 60
    os.utime(backup.STAGED_RESTORE_PATH, (old, old))
    # any Settings page clears it, not just Backup and import
    admin.get("/admin/settings?tab=name")
    assert not os.path.exists(backup.STAGED_RESTORE_PATH)
    # and a restore can't be finished from it
    _upload(admin)
    os.utime(backup.STAGED_RESTORE_PATH, (old, old))
    r = admin.post("/admin/backup/restore-confirm", data={"posts": "1"})
    assert "expired" in r.headers["location"] and not os.path.exists(backup.STAGED_RESTORE_PATH)


def test_sizes_read_like_a_person_would_say_them():
    assert backup.size_label(0) == "0 KB"
    assert backup.size_label(300) == "1 KB"
    assert backup.size_label(820 * 1024) == "820 KB"
    assert backup.size_label(int(4.25 * 1024 ** 2)) == "4.2 MB"
    assert backup.size_label(48 * 1024 ** 2) == "48 MB"
    assert backup.size_label(int(1.2 * 1024 ** 3)) == "1.2 GB"


def test_disk_space_accounts_for_every_file(admin, client):
    from soloblog import config
    from soloblog import images
    # the kinds of file the app makes: posts, a trashed one, an image and
    # its smaller copy, an upload waiting to be restored
    slug = save_post(admin, title="Disk space post")
    admin.post("/admin/delete", data={"slug": save_post(admin, title="Disk space trashed")})
    name = _wide_image("disk-space.webp")
    assert images.sized(name, min(images.SIZES)) != os.path.join(config.UPLOADS_DIR, name)
    _upload(admin)
    usage = backup.disk_usage()
    keys = {key for key, _, _ in usage["parts"]}
    assert {"posts", "posts_trash", "images", "sizes", "database", "pending"} <= keys
    # nothing the app makes is left unexplained
    assert usage["other"] == {}, usage["other"]
    assert usage["total"] == sum(n for _, _, n in usage["parts"])
    page = admin.get("/admin/health").text
    assert 'data-panel="backup-disk"' in page and "Posts and pages" in page and "free of" in page
    # the lock a running copy holds is Soloblog's own, never an "other file"
    open(os.path.join(config.DATA_DIR, ".running"), "a").close()
    assert ".running" not in backup.disk_usage()["other"]
    # something that isn't Soloblog's shows, by name
    stray = os.path.join(config.DATA_DIR, "stray.bin")
    with open(stray, "wb") as f:
        f.write(b"x" * 2048)
    try:
        assert "stray.bin" in backup.disk_usage()["other"]
        assert "Other files" in admin.get("/admin/health").text
    finally:
        os.remove(stray)
        backup.discard_staged()
    assert slug


def test_the_smaller_copies_can_be_cleared(admin, client):
    from soloblog import config
    from soloblog import images
    name = _wide_image("clear-sizes.webp")
    small = images.sized(name, min(images.SIZES))
    sizes_dir = os.path.join(config.UPLOADS_DIR, "_sizes")
    assert os.path.isdir(sizes_dir)
    assert client.post("/admin/disk/clear-sizes").status_code in (302, 303, 401, 403)
    assert os.path.isdir(sizes_dir)
    r = admin.post("/admin/disk/clear-sizes")
    assert r.status_code == 303 and "Cleared" in r.headers["location"]
    assert not os.path.exists(sizes_dir)
    # made again the next time it's asked for
    assert os.path.exists(images.sized(name, min(images.SIZES)))
    assert small


def test_a_restore_brings_back_everything_but_the_keys(admin, client):
    """A server that died, restored from a downloaded zip: members,
    subscribers, messages, reactions and the rest come back - every table
    but the few backup.NOT_RESTORED names."""
    from soloblog import apikeys, contact, members, newsletter, reactions, settings, webhooks
    from soloblog.db import get_db
    from conftest import PASSWORD
    slug = save_post(admin, title="Backed up with its people")
    paid = members.add("paid-in-backup@example.com", "Ana", "paid")
    newsletter.subscribe_confirmed("reader-in-backup@example.com")
    contact.add("Kai", "kai@example.com", "A message in the backup")
    reactions.add(slug, "heart")
    webhooks.add("https://hooks.example.com/in-backup", ["post.published"])
    key = apikeys.create("Revoked after the backup", "read")
    os.makedirs(os.path.join(backup.config.UPLOADS_DIR, "_originals"), exist_ok=True)
    with open(os.path.join(backup.config.UPLOADS_DIR, "_originals", "edited.webp"), "wb") as f:
        f.write(b"the untouched original")
    db = get_db()
    tables = sorted(t for ts in backup.TABLES.values() for t in ts)
    before = {t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}  # noqa: S608 - fixed table names
    data = backup.build_backup_zip()

    # the disaster: people gone, a key revoked, a member signed in
    db.execute("DELETE FROM members")
    db.execute("DELETE FROM subscribers")
    db.execute("DELETE FROM contact_messages")
    db.execute("DELETE FROM post_reactions")
    db.commit()
    apikeys.revoke_key(key)
    os.remove(os.path.join(backup.config.UPLOADS_DIR, "_originals", "edited.webp"))
    stranger = members.add("joined-after@example.com", "Later")
    members.new_session(stranger["id"])

    counts = backup.import_backup_zip(data)
    after = {t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}  # noqa: S608 - fixed table names
    assert after == before, {t: (before[t], after[t]) for t in tables if before[t] != after[t]}
    assert counts["members"] and counts["subscribers"] and counts["contact_messages"]
    assert members.get(paid["id"])["status"] == "paid"
    assert db.execute("SELECT 1 FROM subscribers WHERE email=?",
                      ("reader-in-backup@example.com",)).fetchone()
    # the revoked key stays revoked, the password stays the one you have now,
    # and nobody stays signed in as a member id that may be someone else's
    assert apikeys.check(key) is None
    assert admin.post("/login", data={"password": PASSWORD}).status_code in (200, 303)
    assert not db.execute("SELECT 1 FROM member_sessions").fetchone()
    assert Path(os.path.join(backup.config.UPLOADS_DIR, "_originals", "edited.webp")).read_bytes() == \
        b"the untouched original"
    assert settings.get("site_title") is not None


def test_every_table_is_restored_or_named(admin):
    """Every table belongs to one backup category, or NOT_RESTORED says
    why it isn't restored - so a new feature's table can't be forgotten."""
    from soloblog.db import get_db
    names = backup._tables(get_db())
    owned = [t for ts in backup.TABLES.values() for t in ts]
    assert len(owned) == len(set(owned)), "a table in two categories"
    assert not set(owned) & set(backup.NOT_RESTORED)
    assert names <= set(owned) | set(backup.NOT_RESTORED), names - set(owned) - set(backup.NOT_RESTORED)
    assert set(backup.NOT_RESTORED) <= names | {"posts_fts"}, set(backup.NOT_RESTORED) - names
    assert set(backup.TABLES) <= set(backup.CATEGORIES) and set(backup.CATEGORY_LABELS) == set(backup.CATEGORIES)


def test_a_backup_without_members_has_none_of_them(admin, monkeypatch):
    """Unticked means not in the file at all - not even in the database's
    free space, where deleted rows linger until it's rewritten."""
    import io
    import sqlite3
    import zipfile
    from soloblog import members
    # some SQLite builds wipe deleted rows themselves; Debian's (the Docker
    # image) doesn't - as there, so it's VACUUM that has to do it
    connect = sqlite3.connect

    def leaves_deleted_rows(*args, **kwargs):
        conn = connect(*args, **kwargs)
        conn.execute("PRAGMA secure_delete=OFF")
        return conn
    monkeypatch.setattr(backup.sqlite3, "connect", leaves_deleted_rows)
    members.add("left-out-member@example.com", "Hidden")
    # enough to fill whole pages - a deleted page keeps its bytes until VACUUM
    for n in range(300):
        members.add(f"crowd-{n}@example.com", "A crowd of members to fill the database's pages")
    full = backup.build_backup_zip()
    assert b"left-out-member@example.com" in zipfile.ZipFile(io.BytesIO(full)).read("blog.db")
    data = backup.build_backup_zip({"settings", "comments"})
    blog_db = zipfile.ZipFile(io.BytesIO(data)).read("blog.db")
    assert b"left-out-member@example.com" not in blog_db and b"crowd-150@example.com" not in blog_db
    found = backup.inspect_zip(data)
    assert found["settings"]["present"] and not found["members"]["present"] and not found["posts"]["present"]
    # and the download link builds the same from its boxes
    r = admin.get("/admin/backup/download?settings=1")
    assert r.status_code == 200 and b"left-out-member@example.com" not in zipfile.ZipFile(io.BytesIO(r.content)).read("blog.db")


def test_restoring_one_category_leaves_the_rest(admin):
    from soloblog import contact, members
    from soloblog.db import get_db
    contact.add("Kai", "kai@example.com", "Kept by the backup")
    data = backup.build_backup_zip()
    get_db().execute("DELETE FROM contact_messages")
    get_db().commit()
    joined = members.add("joined-since@example.com", "Since")
    counts = backup.import_backup_zip(data, {"comments"})
    assert counts["contact_messages"] and "members" not in counts
    assert get_db().execute("SELECT 1 FROM contact_messages WHERE body='Kept by the backup'").fetchone()
    assert members.get(joined["id"])  # members weren't chosen, so the newer one stays


def test_cloud_backups_include_what_is_ticked(admin):
    from soloblog import settings, storage
    before = settings.get("backup_include")
    try:
        assert storage.backup_categories() == set(storage.BACKUP_CATEGORIES)
        r = admin.post("/admin/backup/include", data={"posts": "1", "settings": "1"}, headers={"HX-Request": "true"})
        assert "Saved" in r.text and storage.backup_categories() == {"posts", "settings"}
        assert "at least one" in admin.post("/admin/backup/include", data={}, headers={"HX-Request": "true"}).text
        # everything ticked is stored blank, so a category added later is in too
        admin.post("/admin/backup/include", data={c: "1" for c in storage.BACKUP_CATEGORIES})
        assert settings.get("backup_include") == ""
    finally:
        settings.set_many({"backup_include": before or ""})


def test_a_backup_from_another_version(admin):
    """Older: a table it doesn't have is left alone. Newer: a column this
    version doesn't know is skipped. Either way the rest restores."""
    import io
    import sqlite3
    import tempfile
    import zipfile
    from soloblog.db import get_db
    get_db().execute("INSERT INTO contact_messages (name, email, body, created_at) "
                     "VALUES ('Old', 'o@example.com', 'still here', '2026-01-01')")
    get_db().commit()
    path = os.path.join(tempfile.mkdtemp(), "blog.db")
    old = sqlite3.connect(path)
    old.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT, from_the_future TEXT)")
    old.execute("INSERT INTO settings VALUES ('site_title', 'From another version', 'x')")
    old.commit()
    old.close()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.write(path, "blog.db")
    title = get_db().execute("SELECT value FROM settings WHERE key='site_title'").fetchone()
    try:
        counts = backup.import_backup_zip(buf.getvalue(), {"db"})
        assert counts["settings"] == 1 and "contact_messages" not in counts
        assert get_db().execute("SELECT 1 FROM contact_messages WHERE body='still here'").fetchone()
    finally:
        from soloblog import settings
        settings.set_many({"site_title": title[0] if title else ""})


def test_trash_goes_with_its_own_kind(admin):
    """As trashed comments do with comments: no separate trash boxes."""
    import io
    import zipfile
    from soloblog import config
    os.makedirs(os.path.join(config.POSTS_DIR, "_trash"), exist_ok=True)
    with open(os.path.join(config.POSTS_DIR, "_trash", "binned.md"), "w") as f:
        f.write("---\ntitle: Binned\n---\nGone")
    names = zipfile.ZipFile(io.BytesIO(backup.build_backup_zip({"posts"}))).namelist()
    assert "posts/_trash/binned.md" in names
    assert backup.inspect_zip(backup.build_backup_zip({"posts"}))["posts"]["trashed"] >= 1
    assert "posts/_trash/binned.md" not in zipfile.ZipFile(io.BytesIO(backup.build_backup_zip({"settings"}))).namelist()
    # an older bookmark's trashed_posts=1 still means the posts
    assert backup._expand({"trashed_posts"}) == {"posts"}
    os.remove(os.path.join(config.POSTS_DIR, "_trash", "binned.md"))


def test_a_backup_cant_write_outside_its_folders(admin, tmp_path):
    """A zip's names are someone else's choice - ../, absolute paths and
    nested folders are skipped, never followed."""
    import io
    import zipfile
    from soloblog import config
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name in ("posts/../../escaped.md", "../escaped.md", "/tmp/escaped.md", "posts/a/b.md",
                     "uploads/../../escaped.webp", "uploads/_trash/../../escaped.webp", "posts/_trash/../x.md"):
            zf.writestr(name, "---\ntitle: Out\n---\nnope")
        zf.writestr("posts/inside.md", "---\ntitle: Inside\n---\nfine")
    counts = backup.import_backup_zip(buf.getvalue(), {"posts", "images"})
    assert counts["posts"] == 1 and counts["images"] == 0 and counts["trashed_posts"] == 0
    for where in (config.DATA_DIR, os.path.dirname(config.DATA_DIR), "/tmp"):
        assert not os.path.exists(os.path.join(where, "escaped.md")) and not os.path.exists(os.path.join(where, "escaped.webp"))
    os.remove(os.path.join(config.POSTS_DIR, "inside.md"))
    from soloblog.db import get_db
    get_db().execute("DELETE FROM posts WHERE slug='inside'")
    get_db().commit()


def test_disk_space_names_the_media_it_holds(admin):
    from soloblog import config
    os.makedirs(config.UPLOADS_DIR, exist_ok=True)
    with open(os.path.join(config.UPLOADS_DIR, "clip-0001.mp4"), "wb") as f:
        f.write(b"\x00\x00\x00\x18ftypmp42")
    try:
        page = admin.get("/admin/health").text
        assert ">Media<" in page and "1 video" in page and "Your media library:" in page
    finally:
        os.remove(os.path.join(config.UPLOADS_DIR, "clip-0001.mp4"))



def test_disk_space_counts_posts_and_says_what_the_logs_are(admin):
    """Posts and pages has its counts, like Media; the detailed log says
    what it is and that it's safe to clear; the login secret is named as
    what's there (the setup token's file is gone by the time anyone sees)."""
    from soloblog import health
    save_post(admin, title="Counted on the disk")
    os.makedirs(health.DETAIL_DIR, exist_ok=True)
    with open(os.path.join(health.DETAIL_DIR, "2026-01-01.log"), "a", encoding="utf-8") as f:
        f.write("a line\n")
    page = admin.get("/admin/health").text
    assert re.search(r"Your writing, as files: \d+ posts?", page)
    assert "Four weeks of everything your site did" in page and "safe to clear" in page
    assert "setup token" not in page.lower().split("disk space", 1)[-1]


def test_a_backup_from_before_layouts_went_restores_and_every_page_renders(admin, client):
    """Files with a layout: line (any name, even one that never was) restore as
    ordinary pages: the line is an unknown key, it does nothing, raises
    nothing and isn't written back."""
    import io
    import zipfile
    from soloblog import posts
    pages = {"old-recipe": "recipe", "old-landing": "landing", "old-photo": "photo", "old-nonsense": "nonsense"}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for slug, layout in pages.items():
            zf.writestr(f"posts/{slug}.md", f"---\ntitle: {slug}\ndate: 2026-01-01\nauthor: A\ntags: ''\nsummary: ''\n"
                                           f"cover_image: ''\npublished: true\npinned: false\nlayout: {layout}\n---\n"
                                           f"## Part\n\nWords for {slug}.\n")
    try:
        backup.import_backup_zip(buf.getvalue(), {"posts"})
        for slug in pages:
            r = client.get(f"/post/{slug}")
            assert r.status_code == 200 and f"Words for {slug}." in r.text, slug
            assert "layout" not in r.text.split("<article", 1)[1], slug
        # saved again, the line is gone from the file
        posts.write("old-recipe", title="old-recipe")
        assert "layout" not in Path(posts._path("old-recipe")).read_text(encoding="utf-8")
    finally:
        for slug in pages:
            posts.delete_post(slug)


def test_the_restore_screen_counts_in_words():
    # "1 revision", "110 revisions" - never "revision(s)"
    from soloblog import backup
    assert backup.counted("post_revisions", 1) == "1 revision"
    assert backup.counted("settings", 207) == "207 settings"
    assert all("(s)" not in one + many for one, many in backup.COUNTED.values())
