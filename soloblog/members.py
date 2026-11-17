"""Members: readers who sign in by email to read members-only posts - free,
or paid (stripe_members.py). Never writers: there's still one admin.

Sign-in is the usual passwordless pattern (Ghost, Substack, Medium): an
emailed link, with a 6-digit code beside it for when the email is open on
another device. Both are kept only as keyed hashes, work once and for 15
minutes; a code allows five guesses. A signed-in browser holds a random
session cookie, also kept only as a keyed hash - apart from the admin's
own login, which it can never stand in for.

Who can read what is decided in one place, can_read(); what of a post may
leave the site for anyone - feeds, search, the fediverse, emails to those
who can't read it - is posts.public_part()."""
import contextvars
import hashlib
import hmac
import secrets
from datetime import timedelta
from soloblog.tz import utcnow

from soloblog import config
from soloblog import settings
from soloblog.db import get_db

TOKEN_MINUTES = 15
CODE_TRIES = 5
SESSION_DAYS = 180
COOKIE = "soloblog_member"
STATUSES = ("free", "paid", "comped")
# Stripe statuses that still mean paid: a trial, a payment being retried
PAID_STATES = ("active", "trialing", "past_due")

# the member this request is from (MemberSession middleware, app.py)
_current = contextvars.ContextVar("member", default=None)


def enabled(s=None) -> bool:
    return (s or settings.get_all()).get("members_enabled") == "1"


def _now():
    return utcnow()


def _key(value: str) -> str:
    """A keyed hash, so a copy of the database alone can't be used to sign
    in - nor a 6-digit code be tried offline."""
    return hmac.new(config.SESSION_SECRET.encode(), value.encode(), hashlib.sha256).hexdigest()


# ---- members

def get(member_id):
    return get_db().execute("SELECT * FROM members WHERE id=?", (member_id,)).fetchone()


def by_email(email: str):
    return get_db().execute("SELECT * FROM members WHERE email=?", ((email or "").strip(),)).fetchone()


def add(email: str, name: str = "", status: str = "free"):
    """The member with this address - made if there isn't one."""
    found = by_email(email)
    if found:
        return found
    db = get_db()
    db.execute("INSERT INTO members (email, name, status, created_at) VALUES (?, ?, ?, ?)",
               (email.strip()[:254], (name or "").strip()[:100], status if status in STATUSES else "free",
                _now().isoformat(timespec="seconds")))
    db.commit()
    return by_email(email)


# the columns of Admin > Members > Export, and what Import reads back
CSV_COLUMNS = ("email", "name", "status", "joined", "last_seen", "newsletter", "plan", "amount", "currency",
               "subscription", "renews_or_ends", "stripe_customer")


def export_csv(ids=None) -> str:
    """Every member, or those ids - the ones ticked in Admin > Members."""
    import csv
    import io
    from soloblog import newsletter
    from soloblog.backup import csv_cell as _cell
    from soloblog.stripe_members import CURRENCIES
    subscribed = {r["email"].lower() for r in newsletter.confirmed()}
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(CSV_COLUMNS)
    chosen = None if ids is None else {int(i) for i in ids}
    for m in get_db().execute("SELECT * FROM members ORDER BY created_at"):
        if chosen is not None and m["id"] not in chosen:
            continue
        paying = bool(m["stripe_subscription_id"])
        w.writerow([_cell(v) for v in (
            m["email"], m["name"], m["status"], m["created_at"], m["last_seen_at"] or "",
            "yes" if m["email"].lower() in subscribed else "no",
            m["plan_interval"] if paying else "",
            m["plan_amount"] / 10 ** CURRENCIES.get(m["plan_currency"], ("", 2))[1] if paying else "",
            m["plan_currency"] if paying else "", m["subscription_status"] if paying else "",
            m["current_period_end"] or "" if paying else "", m["stripe_customer_id"])])
    return out.getvalue()


def import_csv(text: str) -> tuple:
    """Members from a CSV - this site's own export, Ghost's, or any list
    with an email column (and name, if there is one). They come in free;
    "comped" in a status column, or Ghost's complimentary_plan, gives
    paid access. A paid plan elsewhere stays there. Returns (added, skipped)."""
    import csv
    import io
    import re
    rows = list(csv.reader(io.StringIO(text.lstrip("\ufeff"))))
    if not rows:
        return 0, 0
    header = [h.strip().lower() for h in rows[0]]
    find = lambda *names: next((i for i, h in enumerate(header) if h in names), None)  # noqa: E731
    col = find("email", "email address", "e-mail")
    body = rows[1:] if col is not None else rows
    if col is None:
        col = next((i for i, v in enumerate(rows[0]) if "@" in v), 0)
    name_col, status_col, comp_col = find("name", "full name"), find("status"), find("complimentary_plan")
    valid = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    added = skipped = 0
    for row in body:
        cell = lambda i, row=row: row[i].strip() if i is not None and len(row) > i else ""  # noqa: E731
        email = cell(col)[:254]
        if not valid.match(email) or by_email(email):
            skipped += 1
            continue
        comped = cell(status_col).lower().lstrip("'") == "comped" or cell(comp_col).lower() in ("true", "1", "yes")
        add(email, cell(name_col).lstrip("'"), "comped" if comped else "free")
        added += 1
    return added, skipped


def update(member_id, **fields):
    allowed = {"name", "status", "note", "stripe_customer_id", "stripe_subscription_id", "subscription_status",
               "plan_interval", "plan_amount", "plan_currency", "current_period_end", "cancel_at_period_end",
               "last_seen_at"}
    fields = {k: v for k, v in fields.items() if k in allowed}
    if not fields:
        return
    db = get_db()
    db.execute(f"UPDATE members SET {', '.join(f'{k}=?' for k in fields)} WHERE id=?",  # noqa: S608 - columns from a fixed list
               (*fields.values(), member_id))
    db.commit()


def delete(member_id):
    """The member, their sessions and any sign-in in progress - not their
    newsletter subscription, which is its own (and has its own unsubscribe)."""
    member = get(member_id)
    if not member:
        return
    db = get_db()
    db.execute("DELETE FROM member_sessions WHERE member_id=?", (member_id,))
    db.execute("DELETE FROM member_tokens WHERE email=?", (member["email"],))
    db.execute("UPDATE comments SET member_id=NULL WHERE member_id=?", (member_id,))
    db.execute("DELETE FROM members WHERE id=?", (member_id,))
    db.commit()


def has_paid(member) -> bool:
    """Paid access: given by the admin, or a subscription that's live - in
    its trial, paid, or with a payment being retried."""
    if not member:
        return False
    if member["status"] == "comped":
        return True
    return member["status"] == "paid" and member["subscription_status"] in PAID_STATES


def can_comment(member, s=None) -> bool:
    """Settings > Members > Who can comment. With members off, everyone."""
    s = s or settings.get_all()
    who = s.get("members_comments") or "everyone"
    if not enabled(s) or who not in ("members", "paid"):
        return True
    return bool(member) and (who == "members" or has_paid(member))


def can_read(row, member=None, admin=False) -> bool:
    """Whether this reader may read the whole post: a public one, anyone; a
    members one, any member; a paid one, a member with paid access. The
    admin always."""
    from soloblog import posts
    visibility = posts.clean_visibility(row["visibility"] if "visibility" in row.keys() else "public")
    # members off: every post is public again (Settings > Members says so)
    if visibility == "public" or admin or not enabled():
        return True
    if visibility == "members":
        return member is not None
    return has_paid(member)


SORTS = {"newest": "created_at DESC", "oldest": "created_at ASC", "name": "name = '', name COLLATE NOCASE, email",
         "email": "email COLLATE NOCASE"}


def search(q="", status="", page=1, per_page=50, sort="newest"):
    where, args = [], []
    if q:
        where.append("(email LIKE ? OR name LIKE ?)")
        args += [f"%{q}%", f"%{q}%"]
    if status == "paid":
        where.append("(status='comped' OR (status='paid' AND subscription_status IN ('active','trialing','past_due')))")
    elif status == "past_due":
        where.append("status='paid' AND subscription_status='past_due'")
    elif status in STATUSES:
        where.append("status=?")
        args.append(status)
    sql = "FROM members" + (" WHERE " + " AND ".join(where) if where else "")
    db = get_db()
    total = db.execute(f"SELECT COUNT(*) {sql}", args).fetchone()[0]
    rows = db.execute(f"SELECT * {sql} ORDER BY {SORTS.get(sort, SORTS['newest'])} LIMIT ? OFFSET ?",
                      (*args, per_page, (max(page, 1) - 1) * per_page)).fetchall()
    return rows, total


def counts() -> dict:
    db = get_db()
    one = lambda q: db.execute(q).fetchone()[0]  # noqa: E731
    month_start = _now().replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    return {
        "all": one("SELECT COUNT(*) FROM members"),
        "paid": one("SELECT COUNT(*) FROM members WHERE status='comped' OR (status='paid' "
                    "AND subscription_status IN ('active','trialing','past_due'))"),
        "new": db.execute("SELECT COUNT(*) FROM members WHERE created_at >= ?", (month_start,)).fetchone()[0],
        "paying": one("SELECT COUNT(*) FROM members WHERE stripe_subscription_id != ''"),
    }


def sync_subscribers() -> int:
    """Newsletter subscribers become free members - when members are turned
    on, and as each new one confirms. Returns how many were added."""
    from soloblog import newsletter
    added = 0
    db = get_db()
    for sub in newsletter.confirmed():
        if not by_email(sub["email"]):
            # a member since they subscribed, not since the switch was turned on
            member = add(sub["email"])
            db.execute("UPDATE members SET created_at=? WHERE id=?",
                       (sub["confirmed_at"] or member["created_at"], member["id"]))
            added += 1
    db.commit()
    return added


# ---- signing in: an emailed link, and a code beside it

def start(email: str, purpose: str = "signin", name: str = "", newsletter: bool = False, next_url: str = ""):
    """(token, code) for the email. Only the newest one for an address
    works - asking again replaces it."""
    token, code = secrets.token_urlsafe(32), f"{secrets.randbelow(1_000_000):06d}"
    now = _now()
    db = get_db()
    db.execute("UPDATE member_tokens SET used_at=? WHERE email=? AND used_at IS NULL",
               (now.isoformat(), email))
    db.execute("INSERT INTO member_tokens (email, token_hash, code_hash, purpose, name, newsletter, next, "
               "created_at, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
               (email, _key("link:" + token), _key(f"code:{email.lower()}:{code}"),
                purpose if purpose in ("signin", "signup") else "signin", (name or "").strip()[:100],
                int(bool(newsletter)), safe_next(next_url), now.isoformat(),
                (now + timedelta(minutes=TOKEN_MINUTES)).isoformat()))
    db.commit()
    return token, code


def _usable(row) -> bool:
    return bool(row) and not row["used_at"] and row["expires_at"] > _now().isoformat()


def _use(row):
    db = get_db()
    db.execute("UPDATE member_tokens SET used_at=? WHERE id=?", (_now().isoformat(), row["id"]))
    db.commit()


def redeem_link(token: str):
    """The sign-in the emailed link was for - once, within its 15 minutes."""
    if not token or len(token) > 100:
        return None
    row = get_db().execute("SELECT * FROM member_tokens WHERE token_hash=?", (_key("link:" + token),)).fetchone()
    if not _usable(row):
        return None
    _use(row)
    return row


def redeem_code(email: str, code: str):
    """The sign-in a code was for. The newest one for the address only; a
    wrong guess counts, and the fifth ends it."""
    code = "".join(ch for ch in (code or "") if ch.isdigit())
    db = get_db()
    row = db.execute("SELECT * FROM member_tokens WHERE email=? AND used_at IS NULL ORDER BY id DESC LIMIT 1",
                     ((email or "").strip(),)).fetchone()
    if not _usable(row) or len(code) != 6:
        return None
    if not hmac.compare_digest(row["code_hash"], _key(f"code:{row['email'].lower()}:{code}")):
        db.execute("UPDATE member_tokens SET attempts=attempts+1, used_at=CASE WHEN attempts+1>=? THEN ? "
                   "ELSE used_at END WHERE id=?", (CODE_TRIES, _now().isoformat(), row["id"]))
        db.commit()
        return None
    _use(row)
    return row


def complete(token_row):
    """The member a redeemed sign-in is for - made now, for a sign-up -
    with their newsletter choice kept."""
    from soloblog import newsletter
    member = add(token_row["email"], token_row["name"]) if token_row["purpose"] == "signup" \
        else by_email(token_row["email"])
    if member and token_row["newsletter"] and newsletter.mode(settings.get_all()) == "builtin":
        newsletter.subscribe_confirmed(member["email"])
    return member


def safe_next(url: str) -> str:
    """Only somewhere on this site - never another one."""
    url = (url or "").strip()
    return url if url.startswith("/") and not url.startswith(("//", "/\\")) and len(url) < 300 else ""


# ---- sessions

def new_session(member_id) -> str:
    """The cookie value for a newly signed-in browser."""
    value = secrets.token_urlsafe(32)
    now = _now()
    db = get_db()
    db.execute("INSERT INTO member_sessions (id, member_id, created_at, last_seen_at, expires_at) "
               "VALUES (?, ?, ?, ?, ?)", (_key("session:" + value), member_id, now.isoformat(), now.isoformat(),
                                          (now + timedelta(days=SESSION_DAYS)).isoformat()))
    db.execute("UPDATE members SET last_seen_at=? WHERE id=?", (now.isoformat(timespec="seconds"), member_id))
    db.commit()
    return value


def from_cookie(value: str):
    """The member a session cookie belongs to, or None. A session in use is
    kept going (at most one write a day)."""
    if not value or len(value) > 100:
        return None
    db = get_db()
    row = db.execute("SELECT * FROM member_sessions WHERE id=?", (_key("session:" + value),)).fetchone()
    if not row:
        return None
    now = _now()
    if row["expires_at"] <= now.isoformat():
        db.execute("DELETE FROM member_sessions WHERE id=?", (row["id"],))
        db.commit()
        return None
    if row["last_seen_at"] < (now - timedelta(days=1)).isoformat():
        db.execute("UPDATE member_sessions SET last_seen_at=?, expires_at=? WHERE id=?",
                   (now.isoformat(), (now + timedelta(days=SESSION_DAYS)).isoformat(), row["id"]))
        db.execute("UPDATE members SET last_seen_at=? WHERE id=?", (now.isoformat(timespec="seconds"),
                                                                    row["member_id"]))
        db.commit()
    return get(row["member_id"])


def end_session(value: str):
    if value:
        db = get_db()
        db.execute("DELETE FROM member_sessions WHERE id=?", (_key("session:" + value),))
        db.commit()


def end_all_sessions(member_id):
    db = get_db()
    db.execute("DELETE FROM member_sessions WHERE member_id=?", (member_id,))
    db.commit()


def current():
    """The member this request is from, or None."""
    return _current.get()


def set_current(member):
    return _current.set(member)


def cookie_kwargs(keep=True) -> dict:
    """How the session cookie is set: only over HTTPS on a real site, out of
    reach of the page's scripts, and not sent along with another site's
    form posts. keep=False ("Keep me signed in" unticked): until the
    browser closes."""
    return {"httponly": True, "secure": config.BASE_URL.startswith("https://"), "samesite": "lax", "path": "/",
            **({"max_age": SESSION_DAYS * 24 * 3600} if keep else {})}


def data_for(member) -> dict:
    """Download my data: everything kept about a member."""
    from soloblog import newsletter
    db = get_db()
    return {
        "email": member["email"], "name": member["name"], "status": member["status"],
        "member_since": member["created_at"], "last_seen": member["last_seen_at"],
        "newsletter": newsletter.is_subscribed(member["email"]),
        "subscription": {k: member[k] for k in ("subscription_status", "plan_interval", "plan_amount",
                                               "plan_currency", "current_period_end", "cancel_at_period_end")}
        if member["stripe_subscription_id"] else None,
        "signed_in_browsers": db.execute("SELECT COUNT(*) FROM member_sessions WHERE member_id=?",
                                         (member["id"],)).fetchone()[0],
        "comments": [dict(c) for c in db.execute(
            "SELECT post_slug, body, created_at FROM comments WHERE member_id=? ORDER BY created_at",
            (member["id"],)).fetchall()],
    }
