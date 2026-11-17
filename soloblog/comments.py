import secrets
from soloblog.tz import utcnow
from soloblog.db import get_db


def add_comment(post_slug: str, author_name: str, email: str, body: str,
                 auto_confirm: bool = False, parent_id: int = None, notify_replies: bool = False,
                 member_id: int = None) -> str:
    """Saves a comment and returns its confirm_token. It stays hidden
    until the emailed link brings the token back (confirm()); with
    auto_confirm - no email set up, or a signed-in member - it goes
    straight to the queue for approval. The caller decides
    (submit_comment). The token is 24 random bytes, not guessable.

    parent_id makes it a visitor's reply, checked and approved like any
    comment - the author's own replies are add_reply's."""
    token = secrets.token_urlsafe(24)
    confirmed_at = utcnow().isoformat() if auto_confirm else None
    get_db().execute(
        "INSERT INTO comments (post_slug, author_name, email, body, confirm_token, confirmed_at, parent_id, created_at, "
        "notify_replies, notify_token, member_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (post_slug, author_name.strip()[:80], email.strip()[:200], body.strip()[:2000], token, confirmed_at,
         parent_id, utcnow().isoformat(), 1 if notify_replies else 0,
         secrets.token_urlsafe(18) if notify_replies else None, member_id)
    )
    get_db().commit()
    return token


def is_blocked(blocklist: str, *texts) -> bool:
    """Settings > Comments and messages > Comments: a line (a word, a phrase,
    an address or a domain) found anywhere in the name, email or text,
    ignoring case."""
    words = [w.strip().lower() for w in (blocklist or "").splitlines() if w.strip()]
    haystack = "\n".join(t or "" for t in texts).lower()
    return any(w in haystack for w in words)


def trash_by_token(token: str):
    get_db().execute("UPDATE comments SET trashed_at=? WHERE confirm_token=?", (utcnow().isoformat(), token))
    get_db().commit()


def get(comment_id: int):
    return get_db().execute("SELECT * FROM comments WHERE id=?", (comment_id,)).fetchone()


def confirm(token: str):
    """Marks a comment confirmed via its emailed link. Returns the row
    (the caller needs post_slug to redirect back to the right post) or
    None for a bad or already-used token."""
    db = get_db()
    row = db.execute(
        "SELECT * FROM comments WHERE confirm_token=? AND confirmed_at IS NULL", (token,)
    ).fetchone()
    if not row:
        return None
    db.execute("UPDATE comments SET confirmed_at=? WHERE id=?", (utcnow().isoformat(), row["id"]))
    db.commit()
    return row


def list_approved_all():
    return get_db().execute(
        "SELECT * FROM comments WHERE approved=1 ORDER BY created_at DESC"
    ).fetchall()


def _status_where(status: str):
    """Shared by list_by_status and count_by_status - same reasoning
    as posts.py's own _status_where: one place decides what counts as
    a page of results vs. the total behind it, so the two can never
    quietly drift apart. status is one of: pending, approved, trash."""
    if status == "trash":
        return "trashed_at IS NOT NULL", []
    if status == "approved":
        return "trashed_at IS NULL AND approved=1", []
    # confirmed_at IS NOT NULL - an unconfirmed comment isn't real yet
    # (the visitor may never click the link at all), so it doesn't
    # belong in the queue an admin is actually expected to act on
    return "trashed_at IS NULL AND approved=0 AND confirmed_at IS NOT NULL", []


def _scope(status, post_slug, q):
    where, params = _status_where(status)
    if post_slug:
        where += " AND post_slug=?"
        params = params + [post_slug]
    if q.strip():
        like = f"%{q.strip()}%"
        where += " AND (author_name LIKE ? OR email LIKE ? OR body LIKE ?)"
        params = params + [like, like, like]
    return where, params


def list_by_status(status: str, post_slug: str = "", page: int = 1, per_page: int = 20, *, q: str = "",
                   sort: str = "newest"):
    """Backs the tabbed/paginated/filterable admin comments page."""
    where, params = _scope(status, post_slug, q)
    column = "trashed_at" if status == "trash" else "created_at"
    order = f"{column} {'ASC' if sort == 'oldest' else 'DESC'}"
    params = params + [per_page, (max(1, page) - 1) * per_page]
    sql = f"SELECT * FROM comments WHERE {where} ORDER BY {order} LIMIT ? OFFSET ?"  # noqa: S608 - written in the code
    return get_db().execute(sql, params).fetchall()


def count_by_status(status: str, post_slug: str = "", *, q: str = "") -> int:
    where, params = _scope(status, post_slug, q)
    return get_db().execute(f"SELECT COUNT(*) AS n FROM comments WHERE {where}", params).fetchone()["n"]  # noqa: S608 - written in the code


def list_approved_in_scope(post_slug: str = ""):
    """Every approved comment in scope that isn't in the trash, replies
    too, unpaged - the caller (build_thread_tree) works out which are
    top-level. "parent_id IS NULL" can't: a reply whose parent was
    trashed still has a parent_id, and would vanish with its replies."""
    where = "trashed_at IS NULL AND approved=1"
    params = []
    if post_slug:
        where += " AND post_slug=?"
        params.append(post_slug)
    return get_db().execute(f"SELECT * FROM comments WHERE {where} ORDER BY created_at", params).fetchall()  # noqa: S608 - written in the code


def list_approved_with_deleted_parents(post_slug: str = ""):
    """list_approved_in_scope, plus a placeholder for each parent in the
    trash that still has replies - "deleted" holds the thread together,
    as on most comment systems. A parent deleted for good has no
    placeholder; its replies move up a level (build_thread_tree). One
    lookup per missing parent - a handful at most."""
    rows = list_approved_in_scope(post_slug)
    by_id = {c["id"]: c for c in rows}
    missing_parent_ids = {c["parent_id"] for c in rows if c["parent_id"] and c["parent_id"] not in by_id}
    placeholders = []
    for pid in missing_parent_ids:
        parent = get(pid)
        if parent and parent["trashed_at"]:
            placeholders.append(parent)
    return rows + placeholders


def build_thread_tree(rows):
    """Groups a flat list of approved comments into (top_level,
    children_by_parent) - shared by the live post page (view_post,
    routes/public.py) and the admin comments list (comment_queue,
    routes/comments_routes.py) so this exact orphan-handling logic
    can't quietly drift out of sync between the two the way it already
    did once (the admin list's own query used a bare "parent_id IS
    NULL" check and silently dropped orphaned replies entirely, rather
    than re-rooting them the way the live page always has). `rows`
    must be every non-trashed approved comment in scope, not a partial
    or paginated slice - a reply's parent needs to actually be present
    for the orphan check below to tell the two cases apart."""
    by_id = {c["id"]: c for c in rows}
    children_by_parent = {}
    for c in rows:
        if c["parent_id"] and c["parent_id"] in by_id:
            children_by_parent.setdefault(c["parent_id"], []).append(c)
    top_level = [c for c in rows if not c["parent_id"] or c["parent_id"] not in by_id]
    return top_level, children_by_parent


def list_commented_slugs(status: str = None):
    """The posts with comments in this status, for the comments page's
    post filter - so a tab only offers posts it has comments for.
    status=None: posts with any comment."""
    if status:
        where, params = _status_where(status)
        q = f"SELECT post_slug FROM comments WHERE {where} GROUP BY post_slug ORDER BY MAX(created_at) DESC"  # noqa: S608 - written in the code
    else:
        q, params = "SELECT post_slug FROM comments GROUP BY post_slug ORDER BY MAX(created_at) DESC", []
    rows = get_db().execute(q, params).fetchall()
    return [r["post_slug"] for r in rows]


def count_pending() -> int:
    # same WHERE a bare list_by_status("pending", ...) count would use,
    # but the admin nav badge (ui) wants just the number, every page
    # load, so this skips building a full page of rows for it
    return get_db().execute(
        "SELECT COUNT(*) AS n FROM comments WHERE approved=0 AND trashed_at IS NULL AND confirmed_at IS NOT NULL"
    ).fetchone()["n"]


def approve(comment_id: int):
    get_db().execute("UPDATE comments SET approved=1 WHERE id=?", (comment_id,))
    get_db().commit()


def reply_recipient(reply_id: int):
    """The comment reply_id answers, if its writer asked to hear about
    replies and can be emailed: they confirmed their address, it isn't
    trashed, and the reply isn't their own."""
    reply = get(reply_id)
    if not reply or not reply["parent_id"] or not reply["approved"] or reply["trashed_at"]:
        return None
    parent = get(reply["parent_id"])
    if (not parent or not parent["notify_replies"] or not parent["email"] or not parent["confirmed_at"]
            or parent["trashed_at"] or parent["is_author"]):
        return None
    if reply["email"] and reply["email"].strip().lower() == parent["email"].strip().lower():
        return None
    return parent


def unsubscribe(token: str):
    """Stops reply emails to the address behind token, on every comment
    it left. Returns that comment, or None for an unknown token."""
    if not token:
        return None
    db = get_db()
    row = db.execute("SELECT * FROM comments WHERE notify_token=?", (token,)).fetchone()
    if row:
        db.execute("UPDATE comments SET notify_replies=0 WHERE lower(email)=lower(?)", (row["email"],))
        db.commit()
    return row


def add_reply(post_slug: str, parent_id: int, author_name: str, body: str):
    """A reply posted by the blog's own author, not a visitor -
    published immediately (no approval queue - it isn't third-party
    content waiting on moderation). is_author=1 is the real,
    unambiguous flag that separates this from a visitor's own reply
    (add_comment with a parent_id, which goes through full
    verification/moderation instead) - the two can nest at any depth
    under MAX_REPLY_DEPTH now (routes/public.py), on either side, so
    "who posted it" can no longer be inferred from position alone the
    way it could back when only the author could ever reply at all."""
    cur = get_db().execute(
        "INSERT INTO comments (post_slug, author_name, body, approved, parent_id, is_author, created_at) "
        "VALUES (?, ?, ?, 1, ?, 1, ?)",
        (post_slug, author_name.strip()[:80], body.strip()[:2000], parent_id, utcnow().isoformat())
    )
    get_db().commit()
    return cur.lastrowid


def move_to_trash(comment_id: int):
    get_db().execute(
        "UPDATE comments SET trashed_at=? WHERE id=?",
        (utcnow().isoformat(), comment_id)
    )
    get_db().commit()


def restore_from_trash(comment_id: int):
    get_db().execute("UPDATE comments SET trashed_at=NULL WHERE id=?", (comment_id,))
    get_db().commit()


def empty_trash() -> int:
    """Permanently removes every trashed comment, returns how many."""
    db = get_db()
    count = db.execute("SELECT COUNT(*) AS n FROM comments WHERE trashed_at IS NOT NULL").fetchone()["n"]
    db.execute("DELETE FROM comments WHERE trashed_at IS NOT NULL")
    db.commit()
    return count


def delete_permanently(comment_id: int):
    """Empty-trash for one specific comment, not everything - the
    "delete this placeholder forever" action. WHERE trashed_at IS NOT
    NULL, not a bare id match - this only ever removes something
    that's already been through the trash step, never a live comment
    directly (that's what move_to_trash is for)."""
    get_db().execute("DELETE FROM comments WHERE id=? AND trashed_at IS NOT NULL", (comment_id,))
    get_db().commit()
