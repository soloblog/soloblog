import logging
import sqlite3
import os
import glob
import threading
from soloblog import config

log = logging.getLogger(__name__)

# One connection per thread: requests run on a pool of threads, and one
# sqlite3 connection isn't safe to share between them (check_same_thread=
# False only turns the check off) - shared, busy moments raised
# InterfaceError. WAL mode lets the connections read and write without
# waiting on each other much.
_local = threading.local()


def get_db():
    if config.VISITOR_DIR.get():
        return _visitor_db(config.db_path())
    if not hasattr(_local, "conn"):
        os.makedirs(config.data_dir(), exist_ok=True)
        conn = sqlite3.connect(config.db_path())
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        _local.conn = conn
    return _local.conn


def _visitor_db(path):
    """A demo visitor's own copy (demo.Sandbox) - a few kept open per
    thread, the longest unused closed."""
    conns = getattr(_local, "visitors", None)
    if conns is None:
        conns = _local.visitors = {}
    conn = conns.pop(path, None)
    if conn is None:
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
    conns[path] = conn
    while len(conns) > 8:
        conns.pop(next(iter(conns))).close()
    return conn


def forget_visitor(path):
    """This thread's connection to a copy that's being removed."""
    conn = getattr(_local, "visitors", {}).pop(path, None)
    if conn:
        conn.close()


BASELINE = "001_schema.sql"


def run_migrations():
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            filename TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    applied = {row["filename"] for row in db.execute("SELECT filename FROM schema_migrations")}
    # 001_schema.sql is every development migration folded into one,
    # before anything was deployed - a database made by the old files
    # can't be brought up to date from it
    if applied and BASELINE not in applied:
        raise RuntimeError("This database is from an early development build of Soloblog and can't be "
                           "upgraded. Start with a fresh data folder and restore a backup's posts and "
                           "images into it.")

    here = os.path.dirname(os.path.abspath(__file__))
    files = sorted(glob.glob(os.path.join(here, "migrations", "*.sql")))
    for path in files:
        name = os.path.basename(path)
        if name in applied:
            continue
        with open(path, encoding="utf-8") as f:
            db.executescript(f.read())
        db.execute("INSERT INTO schema_migrations (filename) VALUES (?)", (name,))
        db.commit()
        log.info("applied migration %s", name)
