"""API keys: how an app, a script or an AI assistant works on the site
for its one admin - made in Settings > Security, shown once, kept only as
a hash, revocable. Each has a scope, and each scope allows what the one
before it does:

- read: posts and pages, drafts and members posts included
- draft: also writes and changes drafts, and uploads images
- publish: also publishes, unpublishes, changes live posts and trashes

Keys are high-entropy random strings, so a plain SHA-256 is enough to
keep them - no password hashing needed - and it doesn't depend on
SESSION_SECRET, so a key survives the secret changing."""
import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import timedelta
from soloblog.tz import utcnow

from soloblog import config, settings
from soloblog.db import get_db

SCOPES = ("read", "draft", "publish")
SCOPE_LABELS = {"read": "Read", "draft": "Write drafts", "publish": "Publish"}
SCOPE_HELP = {
    "read": "See posts and pages, drafts and members posts included",
    "draft": "Also write and change drafts, and upload images",
    "publish": "Also publish, change live posts and move posts to trash",
}
PREFIX = "sb_"
# "last used" is written at most this often, not on every request -
# often enough that the time shown is right to the minute
TOUCH_EVERY = timedelta(minutes=1)
# what used it last, as the key's row says it
VIA = {"api": "the API", "micropub": "a writing app", "mcp": "an AI assistant", "ghost": "a Ghost app"}
# Settings > Integrations > API keys: who a Publish key may publish for,
# whatever its own scope (the apps_publish setting)
PUBLISH_CHOICES = {"none": "No one - everything arrives as a draft",
                   "apps": "Apps, not AI assistants",
                   "all": "Apps and AI assistants"}
HELD_BACK = "Publishing is kept to the author (Settings > Integrations > API keys)"


def _hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def _now():
    return utcnow()


def create(name: str, scope: str, client_id: str = "") -> str:
    """A new key - returned this once, never again. client_id: the app it
    was made for by signing in with the site (micropub.py)."""
    scope = scope if scope in SCOPES else "read"
    key = PREFIX + secrets.token_urlsafe(32)
    db = get_db()
    db.execute("INSERT INTO api_keys (name, scope, key_hash, prefix, created_at, client_id) VALUES (?, ?, ?, ?, ?, ?)",
               ((name or "").strip()[:60] or "API key", scope, _hash(key), key[:len(PREFIX) + 6],
                _now().isoformat(timespec="seconds"), client_id[:500]))
    db.commit()
    return key


def revoke_key(key: str) -> bool:
    """Revoke by the key itself - what an app sends to sign out."""
    row = check(key)
    return revoke(row["id"]) if row else False


# ---- signed keys, for apps that publish to Ghost (ghost.py)
#
# "id:secret", 24 and 64 hex characters, as those apps expect. The app
# never sends the secret: it signs a short-lived token (a JWT, HS256)
# with it. The site has to check that signature, so it needs the secret -
# rather than keep it, it works it out again from the site's own
# SESSION_SECRET, so a copy of the database (a backup) doesn't hold it.
# Changing SESSION_SECRET means making these keys again.

TOKEN_MINUTES = 5  # how long a signed token may live, as the apps make them


def _secret_for(key_id: str) -> bytes:
    return hmac.new(config.SESSION_SECRET.encode(), f"signed-key:{key_id}".encode(), hashlib.sha256).digest()


def create_signed(name: str, scope: str) -> str:
    """A new signed key, "id:secret" - returned this once."""
    scope = scope if scope in SCOPES else "read"
    key_id = secrets.token_hex(12)
    secret = _secret_for(key_id).hex()
    db = get_db()
    db.execute("INSERT INTO api_keys (name, scope, key_hash, prefix, created_at, kind, key_id) "
               "VALUES (?, ?, ?, ?, ?, 'signed', ?)",
               ((name or "").strip()[:60] or "API key", scope, _hash(f"{key_id}:{secret}"), key_id[:8],
                _now().isoformat(timespec="seconds"), key_id))
    db.commit()
    return f"{key_id}:{secret}"


def _b64(part: str) -> bytes:
    return base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))


def _touch(db, row, via: str):
    """Notes when and how the key was used - at most every TOUCH_EVERY,
    unless something else is using it now."""
    stale = not row["last_used_at"] or row["last_used_at"] < (_now() - TOUCH_EVERY).isoformat()
    if stale or row["last_used_via"] != via:
        db.execute("UPDATE api_keys SET last_used_at=?, last_used_via=? WHERE id=?",
                   (_now().isoformat(timespec="seconds"), via, row["id"]))
        db.commit()


def check_signed(token: str, audience_suffix: str = "/admin/", via: str = "ghost"):
    """The key's row for a signed token - HS256 only, signed with a live
    signed key's secret, for this kind of request (its aud), and
    short-lived - else None."""
    try:
        head, body, sig = token.split(".")
        header, claims = json.loads(_b64(head)), json.loads(_b64(body))
    except (ValueError, TypeError):
        return None
    if not isinstance(header, dict) or header.get("alg") != "HS256" or not isinstance(claims, dict):
        return None
    key_id = str(header.get("kid") or "")
    row = get_db().execute("SELECT * FROM api_keys WHERE kind='signed' AND key_id=? AND revoked_at IS NULL",
                           (key_id,)).fetchone() if len(key_id) == 24 else None
    if not row:
        return None
    expected = hmac.new(_secret_for(key_id), f"{head}.{body}".encode(), hashlib.sha256).digest()
    try:
        if not hmac.compare_digest(expected, _b64(sig)):
            return None
    except (ValueError, TypeError):
        return None
    now = time.time()
    iat, exp = claims.get("iat"), claims.get("exp")
    if not isinstance(iat, (int, float)) or not isinstance(exp, (int, float)):
        return None
    if exp < now or iat > now + 60 or exp - iat > TOKEN_MINUTES * 60:
        return None
    if not str(claims.get("aud") or "").endswith(audience_suffix):
        return None
    _touch(get_db(), row, via)
    return {**dict(row), "via": via}


def listed():
    return get_db().execute("SELECT * FROM api_keys WHERE revoked_at IS NULL ORDER BY created_at DESC").fetchall()


def revoke(key_id: int) -> bool:
    db = get_db()
    done = db.execute("UPDATE api_keys SET revoked_at=? WHERE id=? AND revoked_at IS NULL",
                      (_now().isoformat(timespec="seconds"), key_id)).rowcount
    db.commit()
    return bool(done)


def check(key: str, via: str = "api"):
    """The key's row if it's a live one, else None. Compared by hash, in
    the database - never by looping over keys in Python."""
    if not key or not key.startswith(PREFIX) or len(key) > 200:
        return None
    db = get_db()
    row = db.execute("SELECT * FROM api_keys WHERE key_hash=? AND revoked_at IS NULL AND kind='bearer'",
                     (_hash(key),)).fetchone()
    if row:
        _touch(db, row, via)
        return {**dict(row), "via": via}
    return None


def may_publish(via: str) -> bool:
    """Whether the site lets what's using a key (VIA) publish with it."""
    choice = settings.get("apps_publish")
    return choice == "all" or (choice != "none" and via != "mcp")


def held_back(row) -> bool:
    """A Publish key the site keeps to drafts, for what's using it now."""
    return bool(row) and row["scope"] == "publish" and not may_publish(row.get("via", "api"))


def allows(row, scope: str) -> bool:
    """Whether a key with row's scope may do what needs `scope` - for
    publishing, only where the site lets what's using it publish."""
    if not row or SCOPES.index(row["scope"]) < SCOPES.index(scope):
        return False
    return scope != "publish" or not held_back(row)
