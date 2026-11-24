import contextlib
import io
import os
import re
import shutil
import sqlite3
import tempfile
import time
import zipfile
from datetime import datetime
from urllib.parse import quote

from soloblog import cache
from soloblog import config
from soloblog import posts
from soloblog.db import get_db

# every category a backup can be built from or restored to - the single
# list both the download checkboxes and the restore checkboxes are built
# from, so the two flows can't quietly drift apart on what "everything"
# means
# trash goes with its own kind, as trashed comments do with comments
CATEGORIES = ["posts", "images", "settings", "comments", "members", "subscribers", "stats"]

CATEGORY_LABELS = {
    "posts": "Posts and pages",
    "images": "Images",
    "settings": "Settings",
    "comments": "Comments and messages",
    "members": "Members",
    "subscribers": "Subscribers and followers",
    "stats": "Stats and reactions",
}

# each category's part of the database: restored with it, and taken out of
# a backup made without it. Every table is in one of these or NOT_RESTORED
# (tests/test_backup.py), so a new feature's table can't be forgotten.
TABLES = {
    "posts": ("post_revisions", "published_log", "webmentions_sent"),
    "images": ("image_meta",),
    "settings": ("settings", "webhooks"),
    "comments": ("comments", "webmentions", "contact_messages"),
    "members": ("members", "stripe_events"),
    "subscribers": ("subscribers", "ap_followers"),
    "stats": ("post_views_daily", "sources_daily", "post_reactions", "ap_interactions"),
}
# what else leaves a backup made without the category - never restored,
# but it's that category's people or words all the same
ALSO_LEFT_OUT = {"posts": ("posts", "post_links", "post_translations", "posts_fts"),
                 "members": ("member_sessions", "member_tokens")}
# what the restore screen counts, per table
COUNTED = {"post_revisions": ("revision", "revisions"), "settings": ("setting", "settings"),
           "comments": ("comment", "comments"), "webmentions": ("mention", "mentions"),
           "contact_messages": ("message", "messages"), "members": ("member", "members"),
           "subscribers": ("subscriber", "subscribers"), "ap_followers": ("follower", "followers")}


def counted(table: str, n: int) -> str:
    """"1 revision", "110 revisions" - the restore screen's count of one table."""
    one, many = COUNTED[table]
    return f"{n} {one if n == 1 else many}"


def _expand(include) -> set:
    """include, with trash going with its own kind."""
    include = set(CATEGORIES if include is None else include)
    include |= {kind for trash, kind in (("trashed_posts", "posts"), ("trashed_images", "images")) if trash in include}
    return include & set(CATEGORIES)


# a single fixed path, not a per-upload token - this is a single-admin
# app, so there's never more than one restore in flight, and a plain
# file is simpler than inventing session storage just for a two-step
# form
STAGED_RESTORE_PATH = os.path.join(config.data_dir(), "_pending_restore.zip")
# a locked backup (BACKUP_PASSPHRASE) the host's passphrase didn't open,
# waiting for the one it was made with - kept as it came
STAGED_LOCKED_PATH = os.path.join(config.data_dir(), "_pending_restore.zip.enc")
# an uploaded backup nobody restored or discarded goes after this long -
# it's a whole copy of a site, and nothing else would ever remove it
STAGED_MAX_AGE = 24 * 60 * 60


def staged_restore():
    """The uploaded backup waiting to be restored - {"size", "when"} - or
    None. One older than a day is deleted instead."""
    try:
        st = os.stat(STAGED_RESTORE_PATH)
    except OSError:
        return None
    if time.time() - st.st_mtime > STAGED_MAX_AGE:
        discard_staged()
        return None
    return {"size": st.st_size, "when": datetime.utcfromtimestamp(st.st_mtime).isoformat(timespec="seconds")}


def discard_staged():
    for path in (STAGED_RESTORE_PATH, STAGED_LOCKED_PATH):
        with contextlib.suppress(FileNotFoundError):
            os.remove(path)


def staged_locked():
    """The locked backup waiting for its passphrase, as it came, or None
    (one older than a day goes, as the waiting upload does)."""
    try:
        if time.time() - os.stat(STAGED_LOCKED_PATH).st_mtime > STAGED_MAX_AGE:
            discard_staged()
            return None
        with open(STAGED_LOCKED_PATH, "rb") as f:
            return f.read()
    except OSError:
        return None


def size_label(n: int) -> str:
    """Bytes as a person reads them: 820 KB, 48 MB, 1.2 GB."""
    for unit, step in (("GB", 1024 ** 3), ("MB", 1024 ** 2)):
        if n >= step:
            value = n / step
            return f"{value:.1f} {unit}" if value < 10 else f"{value:.0f} {unit}"
    return f"{max(1, round(n / 1024)) if n else 0} KB"


# Site health > Disk space: every file on the data disk,
# by what it is - the first rule that matches a file's path, from DATA_DIR,
# wins. A new kind of file needs a line here, or it shows as "Other files"
# (and tests/test_backup.py fails).
DISK_PARTS = [
    ("posts_trash", "Posts in trash", "posts/_trash/"),
    ("posts", "Posts and pages", "posts/"),
    ("images_trash", "Media in trash", "uploads/_trash/"),
    ("sizes", "Smaller copies of images", "uploads/_sizes/"),
    ("originals", "Originals of edited images", "uploads/_originals/"),
    ("images", "Media", "uploads/"),
    ("database", "Database", "blog.db"),
    ("cards", "Share cards", "cards/"),
    ("detail_log", "Detailed log", "logs/detail/"),
    ("log", "Problems log", "logs/"),
    ("pending", "An uploaded backup, not restored", os.path.basename(STAGED_RESTORE_PATH)),
    # a prefix can be a tuple - the few small files of the app's own
    # the setup token's file is gone once the account exists - this list
    # is only seen logged in, so it's the login secret by then
    ("keys", "Login secret", (".session_secret", "setup-token.txt")),
    ("demo", "The demo's own files", (".soloblog-demo", "demo-cache/")),
]
# not listed: the disk's own folder on a mounted volume, and the empty file
# a running copy holds so a second one can't share the folder (health.lock_path)
_NOT_LISTED_FOLDER, _NOT_LISTED_FILE = "lost+found/", ".running"


def disk_usage():
    """{"parts": [(key, label, bytes)] in DISK_PARTS order, only those with
    something in them; "other": {top-level name: bytes} for anything
    unrecognised; "total"; "disk": (size, free) of the disk it's on, or None}."""
    sizes, other = {}, {}
    root = config.data_dir()
    for folder, _, files in os.walk(root):
        for fn in files:
            path = os.path.join(folder, fn)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            if rel.startswith(_NOT_LISTED_FOLDER) or rel == _NOT_LISTED_FILE:
                continue
            try:
                n = os.path.getsize(path)
            except OSError:
                continue
            key = next((k for k, _, prefix in DISK_PARTS if rel.startswith(prefix)), None)
            if key:
                sizes[key] = sizes.get(key, 0) + n
            else:
                top = rel.split("/", 1)[0]
                other[top] = other.get(top, 0) + n
    try:
        usage = shutil.disk_usage(root)
        disk = (usage.total, usage.free)
    except OSError:
        disk = None
    parts = [(k, label, sizes[k]) for k, label, _ in DISK_PARTS if sizes.get(k)]
    return {"parts": parts, "other": other, "total": sum(sizes.values()) + sum(other.values()), "disk": disk}


def _add_dir(zf, dir_path, arc_prefix):
    """Adds every real file (not subdirectories) directly inside
    dir_path to the zip under arc_prefix/ - used for both posts/_trash
    and uploads/[_trash], which are otherwise identical "flat folder of
    files" cases."""
    if not os.path.exists(dir_path):
        return
    for fn in os.listdir(dir_path):
        path = os.path.join(dir_path, fn)
        if os.path.isfile(path):
            zf.write(path, arcname=f"{arc_prefix}/{fn}")


def build_backup_zip(include: set[str] | None = None) -> bytes:
    """include is a set of CATEGORIES to write - None means all of
    them, which is what a plain "download everything" should do."""
    include = _expand(include)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if "posts" in include and os.path.exists(config.posts_dir()):
            for fn in os.listdir(config.posts_dir()):
                if fn.endswith(".md"):
                    zf.write(os.path.join(config.posts_dir(), fn), arcname=f"posts/{fn}")
            _add_dir(zf, os.path.join(config.posts_dir(), "_trash"), "posts/_trash")
        if "images" in include:
            _add_dir(zf, config.uploads_dir(), "uploads")
            # the untouched original of an edited image - Restore original
            _add_dir(zf, os.path.join(config.uploads_dir(), "_originals"), "uploads/_originals")
            _add_dir(zf, os.path.join(config.uploads_dir(), "_trash"), "uploads/_trash")
        if include & set(TABLES) and os.path.exists(config.db_path()):
            # the live db runs in WAL mode (db.py): recent writes sit in the
            # -wal file until checkpointed, and a plain copy of blog.db
            # missed them. TRUNCATE moves them into blog.db first.
            get_db().execute("PRAGMA wal_checkpoint(TRUNCATE)")
            left_out = [cat for cat in TABLES if cat not in include]
            if left_out:
                zf.writestr("blog.db", _db_without(left_out))
            else:
                zf.write(config.db_path(), arcname="blog.db")
    buf.seek(0)
    return buf.read()


def _db_without(categories) -> bytes:
    """A copy of the database with these categories' rows taken out -
    really out: VACUUM rewrites the file, so deleted rows don't linger in
    its free pages."""
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "blog.db")
        copy = sqlite3.connect(path)
        try:
            get_db().backup(copy)
            names = {n for (n,) in copy.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            for cat in categories:
                for table in TABLES.get(cat, ()) + ALSO_LEFT_OUT.get(cat, ()):
                    if table in names:
                        copy.execute(f"DELETE FROM {table}")  # noqa: S608 - table names from TABLES
            copy.commit()
            copy.execute("VACUUM")
        finally:
            copy.close()
        with open(path, "rb") as f:
            return f.read()


def backup_filename() -> str:
    """"Mira's Kitchen-backup-2026-09-28.zip" - the site's title, and the
    date where the site is, so a folder of backups sorts itself out."""
    from soloblog import settings, tz
    title = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', "", settings.get("site_title") or "").strip()
    title = re.sub(r"\s+", " ", title).strip(" .") or "blog"
    return f"{title}-backup-{datetime.now(tz.site_zone()).strftime('%Y-%m-%d')}.zip"


def download_header(filename: str) -> str:
    """Content-Disposition for a name that may not be plain ASCII (a
    Japanese title): an ASCII stand-in, and the real name for browsers."""
    plain = re.sub(r"[^A-Za-z0-9 ._-]+", "", filename).strip() or "blog-backup.zip"
    return f"attachment; filename=\"{plain}\"; filename*=UTF-8''{quote(filename)}"


def csv_cell(value) -> str:
    """A spreadsheet runs a cell starting with = + - @ as a formula - a
    name, or a source another site chose, like "=HYPERLINK(...)" mustn't."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def csv_download(filename: str, header, rows):
    """A list's Export: a CSV, every cell safe to open in a spreadsheet."""
    import csv
    from starlette.responses import Response
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(header)
    w.writerows([csv_cell(v) for v in row] for row in rows)
    return Response(out.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": download_header(filename)})


def _safe_member(name: str, prefix: str) -> str | None:
    """Returns the bare filename if `name` is exactly "prefix/filename"
    - no nesting, no ../ climbing, nothing that could write outside the
    directory this entry is meant for. None if it doesn't match."""
    if not name.startswith(prefix):
        return None
    base = name[len(prefix):]
    if not base or "/" in base or base != os.path.basename(base):
        return None
    return base


def _table_row_count(conn, table: str) -> int:
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]  # noqa: S608 - table names from TABLES
    except sqlite3.OperationalError:
        return 0


def inspect_zip(file_bytes: bytes) -> dict:
    """What's actually inside an uploaded backup zip, per category -
    the restore UI only offers a checkbox for something that's really
    there, rather than a fixed list that might restore nothing for a
    category and confuse the admin into thinking it did. Counts (not
    just presence) so the admin can tell "12 posts" from "0 posts"
    before deciding to restore either."""
    result = {cat: {"present": False, "count": 0, "trashed": 0} for cat in CATEGORIES}
    db_bytes = None
    if not zipfile.is_zipfile(io.BytesIO(file_bytes)):
        return result  # nothing in it - "doesn't look like a Soloblog backup"
    with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
        for info in zf.infolist():
            name = info.filename
            if (base := _safe_member(name, "posts/_trash/")) and base.endswith(".md"):
                result["posts"]["trashed"] += 1
            elif (base := _safe_member(name, "posts/")) and base.endswith(".md"):
                result["posts"]["count"] += 1
            elif _safe_member(name, "uploads/_trash/"):
                result["images"]["trashed"] += 1
            elif _safe_member(name, "uploads/"):
                result["images"]["count"] += 1
            elif name == "blog.db":
                db_bytes = zf.read(info)

    if db_bytes is not None:
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
                tmp.write(db_bytes)
                tmp_path = tmp.name
            conn = sqlite3.connect(tmp_path)
            for cat, tables in TABLES.items():
                rows = {table: _table_row_count(conn, table) for table in tables}
                result[cat]["rows"] = {t: n for t, n in rows.items() if n}
                # posts and images are counted by their files
                if cat not in ("posts", "images"):
                    result[cat]["count"] = sum(rows.values())
            conn.close()
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

    for cat in CATEGORIES:
        result[cat]["present"] = result[cat]["count"] + result[cat]["trashed"] > 0
    return result


# tables a restore leaves as they are, and why - every other table is in
# one of the TABLES categories
NOT_RESTORED = {
    "admin": "your password and two-step sign-in stay as they are",
    "passkeys": "they sign in to this admin, like the password",
    "api_keys": "a key revoked since the backup would work again",
    "indieauth_codes": "short-lived", "member_sessions": "short-lived", "member_tokens": "short-lived",
    "rate_hits": "short-lived",
    "schema_migrations": "this install's own",
    "posts": "rebuilt from the post files", "post_links": "rebuilt from the post files",
    "post_translations": "a cache", "ap_actors": "a cache",
}
# merged into what's there rather than replacing it
MERGED = ("settings", "image_meta")


def _tables(conn) -> set[str]:
    return {name for (name,) in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
        "AND name NOT LIKE 'posts_fts%'")}


def _restore_db_data(db_bytes: bytes, include: set[str]) -> dict:
    """Copies the chosen categories' tables (TABLES) from the backup's
    blog.db into the LIVE database, through the app's own get_db()
    connection - never by swapping blog.db itself, which would pull the
    file out from under a running process (WAL files, other threads'
    connections). Each table is replaced with the backup's rows; settings
    and image details are merged. A table the backup has no rows in is
    left alone - it was left out of that backup, or empty then. Only the
    columns both sides have are copied, so a backup from an older or
    newer version still restores. Returns rows per table."""
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            tmp.write(db_bytes)
            tmp_path = tmp.name
        src = sqlite3.connect(tmp_path)
        live = get_db()
        backed_up, here_now = _tables(src), _tables(live)
        counts = {}
        try:
            # names come from TABLES and the live database, never from the upload
            for table in sorted(t for cat in include for t in TABLES.get(cat, ())):
                if table not in backed_up or table not in here_now:
                    continue
                here = {r[1] for r in live.execute(f"PRAGMA table_info({table})")}
                cols = [r[1] for r in src.execute(f"PRAGMA table_info({table})") if r[1] in here]
                rows = src.execute(f"SELECT {', '.join(cols)} FROM {table}").fetchall() if cols else []  # noqa: S608 - table names from TABLES
                if not rows:
                    continue
                if table not in MERGED:
                    live.execute(f"DELETE FROM {table}")  # noqa: S608 - table names from TABLES
                live.executemany(f"INSERT OR REPLACE INTO {table} ({', '.join(cols)}) "  # noqa: S608 - table names from TABLES
                                 f"VALUES ({', '.join('?' * len(cols))})", rows)
                counts[table] = len(rows)
            if "members" in counts:
                # a member's id may be someone else's in the backup - everyone
                # signs in again rather than risk landing in another account
                live.execute("DELETE FROM member_sessions")
                live.execute("DELETE FROM member_tokens")
            live.commit()
        except Exception:
            # all or nothing - never a site with half its tables emptied
            live.rollback()
            raise
        finally:
            src.close()
        return counts
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


def import_backup_zip(file_bytes: bytes, include: set[str] | None = None) -> dict:
    """Restores whichever of posts (live and trashed), uploads (live
    and trashed), and comments/settings are both present in the zip
    and selected in `include` (None means everything present), with
    each one's part of the database (TABLES).
    Plain files are safe to write directly - trashed posts go straight
    into posts/_trash (no resync_from_file(), which would incorrectly
    un-trash them back into the live posts table), same for trashed
    uploads. Returns a dict of counts per category rather than one
    combined total, so the admin can actually see what came back, not
    just a number."""
    include = _expand(include)
    os.makedirs(config.posts_dir(), exist_ok=True)
    os.makedirs(os.path.join(config.posts_dir(), "_trash"), exist_ok=True)
    os.makedirs(config.uploads_dir(), exist_ok=True)
    os.makedirs(os.path.join(config.uploads_dir(), "_trash"), exist_ok=True)
    os.makedirs(os.path.join(config.uploads_dir(), "_originals"), exist_ok=True)
    counts = {"posts": 0, "trashed_posts": 0, "images": 0, "trashed_images": 0}
    db_bytes = None
    with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
        for info in zf.infolist():
            name = info.filename
            if (base := _safe_member(name, "posts/_trash/")) and base.endswith(".md"):
                dest, key = os.path.join(config.posts_dir(), "_trash", base), "trashed_posts"
            elif (base := _safe_member(name, "posts/")) and base.endswith(".md"):
                dest, key = os.path.join(config.posts_dir(), base), "posts"
            elif base := _safe_member(name, "uploads/_trash/"):
                dest, key = os.path.join(config.uploads_dir(), "_trash", base), "trashed_images"
            elif base := _safe_member(name, "uploads/_originals/"):
                if "images" in include:
                    with zf.open(info) as src, open(os.path.join(config.uploads_dir(), "_originals", base), "wb") as dst:
                        dst.write(src.read())
                continue
            elif base := _safe_member(name, "uploads/"):
                dest, key = os.path.join(config.uploads_dir(), base), "images"
            elif name == "blog.db":
                if include & set(TABLES):
                    db_bytes = zf.read(info)
                continue
            else:
                continue
            if {"trashed_posts": "posts", "trashed_images": "images"}.get(key, key) not in include:
                continue
            with zf.open(info) as src, open(dest, "wb") as dst:
                dst.write(src.read())
            if key == "posts":
                posts.resync_from_file(base[:-3])
            counts[key] += 1

    if db_bytes is not None:
        counts.update(_restore_db_data(db_bytes, include))

    # settings, image details and uploads may all have changed underneath
    # the in-memory caches
    cache.bump()
    return counts
