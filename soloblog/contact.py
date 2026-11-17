from soloblog.tz import utcnow

from soloblog.db import get_db


def add(name: str, email: str, body: str) -> int:
    cur = get_db().execute(
        "INSERT INTO contact_messages (name, email, body, created_at) VALUES (?, ?, ?, ?)",
        (name.strip()[:100], email.strip()[:200], body.strip()[:5000], utcnow().isoformat()))
    get_db().commit()
    return cur.lastrowid


def _matching(q, trash=False):
    like = f"%{q.strip()}%"
    return (f"(name LIKE ? OR email LIKE ? OR body LIKE ?) AND trashed_at IS {'NOT ' if trash else ''}NULL",
            [like, like, like])


def list_all(page: int = 1, per_page: int = 20, q: str = "", sort: str = "newest", trash: bool = False):
    where, args = _matching(q, trash)
    order = "ASC" if sort == "oldest" else "DESC"
    return get_db().execute(f"SELECT * FROM contact_messages WHERE {where} ORDER BY created_at {order} "  # noqa: S608 - written in the code
                            "LIMIT ? OFFSET ?", (*args, per_page, (max(1, page) - 1) * per_page)).fetchall()


def count(q: str = "", trash: bool = False) -> int:
    where, args = _matching(q, trash)
    return get_db().execute(f"SELECT COUNT(*) AS n FROM contact_messages WHERE {where}", args).fetchone()["n"]  # noqa: S608 - written in the code


def in_use() -> bool:
    """The form is on, or messages it took are still kept."""
    from soloblog import settings
    return settings.get("contact_enabled") == "1" or \
        get_db().execute("SELECT 1 FROM contact_messages LIMIT 1").fetchone() is not None


def count_unread() -> int:
    return get_db().execute("SELECT COUNT(*) AS n FROM contact_messages WHERE is_read=0 AND trashed_at IS NULL"
                            ).fetchone()["n"]


def get(message_id: int):
    return get_db().execute("SELECT * FROM contact_messages WHERE id=?", (message_id,)).fetchone()


def mark_read(message_id: int, read: bool = True):
    get_db().execute("UPDATE contact_messages SET is_read=? WHERE id=?", (1 if read else 0, message_id))
    get_db().commit()


def move_to_trash(message_id: int):
    get_db().execute("UPDATE contact_messages SET trashed_at=? WHERE id=?", (utcnow().isoformat(), message_id))
    get_db().commit()


def restore(message_id: int):
    get_db().execute("UPDATE contact_messages SET trashed_at=NULL WHERE id=?", (message_id,))
    get_db().commit()


def delete(message_id: int):
    get_db().execute("DELETE FROM contact_messages WHERE id=?", (message_id,))
    get_db().commit()


def empty_trash() -> int:
    db = get_db()
    n = db.execute("DELETE FROM contact_messages WHERE trashed_at IS NOT NULL").rowcount
    db.commit()
    return n


def export_csv(ids) -> str:
    """The ticked messages, for a spreadsheet - Admin > Messages > Export."""
    import csv
    import io
    from soloblog.backup import csv_cell
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["name", "email", "message", "received"])
    chosen = {int(i) for i in ids}
    for m in get_db().execute("SELECT * FROM contact_messages ORDER BY created_at"):
        if m["id"] in chosen:
            w.writerow([csv_cell(m["name"]), csv_cell(m["email"]), csv_cell(m["body"]), m["created_at"]])
    return out.getvalue()
