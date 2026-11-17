import contextlib
import hashlib
import json
import logging
import os
import secrets
import time
from soloblog.tz import utcnow
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from soloblog import config
from soloblog.db import get_db

log = logging.getLogger(__name__)
ph = PasswordHasher()

# regenerated every boot, lives only in memory, and stops mattering the
# moment an admin account exists. this is what makes first-run setup
# safe without shipping a default password or needing email/SMS:
# whoever can read the process log is the one setting the password.
_setup_token = secrets.token_urlsafe(24)


# the setup token in a file too, for a host with the data folder in reach
# (SFTP, a file manager) but no log to read - gone once there's an admin
SETUP_TOKEN_FILE = os.path.join(config.data_dir(), "setup-token.txt")


def write_setup_token():
    try:
        fd = os.open(SETUP_TOKEN_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(f"{setup_token()}\n\nThe setup token for your new Soloblog: open /setup on your site and "
                    "paste it there. This file is deleted once your admin account exists.\n")
    except OSError:
        pass


def forget_setup_token():
    with contextlib.suppress(OSError):
        os.remove(SETUP_TOKEN_FILE)


def setup_token() -> str:
    """The SETUP_TOKEN the host set, when there's one long enough to be
    safe - you chose it, so there's no log to dig through - else the one
    made at boot and printed to the log."""
    return config.SETUP_TOKEN if len(config.SETUP_TOKEN) >= 16 else _setup_token


# A recovery key resets the password when it's forgotten - no email and no
# server log needed. Made at setup and in Settings > Security, shown once,
# kept only as a hash, like the password; using it makes a new one.
# Crockford's base32: no I, L, O or U to misread, and dashes every four.
KEY_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
KEY_LENGTH = 20


def new_recovery_key() -> str:
    from soloblog import settings
    raw = "".join(secrets.choice(KEY_ALPHABET) for _ in range(KEY_LENGTH))
    settings.set_many({"recovery_key_hash": ph.hash(raw), "recovery_key_made": utcnow().isoformat()})
    return "-".join(raw[i:i + 4] for i in range(0, KEY_LENGTH, 4))


def _clean_key(key: str) -> str:
    """As typed: any case, spaces or dashes, and the letters people swap
    for digits (O for 0, I or L for 1)."""
    key = (key or "").upper().translate(str.maketrans("OIL", "011"))
    return "".join(c for c in key if c in KEY_ALPHABET)


def recovery_key_ok(key: str) -> bool:
    from soloblog import settings
    stored = settings.get("recovery_key_hash")
    key = _clean_key(key)
    if not stored or len(key) != KEY_LENGTH:
        return False
    try:
        return ph.verify(stored, key)
    except VerificationError:  # the wrong key
        return False
    except InvalidHashError:
        log.error("the stored recovery key is damaged - make a new one in Settings > Security")
        return False


def has_recovery_key() -> bool:
    from soloblog import settings
    return bool(settings.get("recovery_key_hash"))


# a forgotten password: a one-time reset link, printed to the log when
# the server starts with RESET_PASSWORD=1, or emailed to the admin's own
# address from "Forgot password?". Only each link's hash is kept, in
# Settings, so a link outlives a restart and works whichever worker
# answers. A new link never ends an older one: anyone can ask for one,
# and that must not kill the link the admin is about to use.
RESET_LINKS = 5        # alive at once; the oldest goes
RESET_EMAIL_GAP = 600  # seconds between two emailed links


def _reset_hash(token: str) -> str:
    return hashlib.sha256((token or "").encode()).hexdigest()


def _reset_links() -> list:
    from soloblog import settings
    try:
        links = json.loads(settings.get("reset_links") or "[]")
    except ValueError:
        return []
    return [x for x in links if isinstance(x, dict) and x.get("expires", 0) > time.time()]


def _keep_reset_links(links: list):
    from soloblog import settings
    settings.set_many({"reset_links": json.dumps(links[-RESET_LINKS:]) if links else ""})


def start_reset(minutes: int = 60, by_email: bool = False) -> str:
    """by_email: the link went to the admin's inbox - which proves only the
    inbox, so two-factor login stays on and its code is still asked for.
    One from the server's log proves more, and can turn it off."""
    token = secrets.token_urlsafe(24)
    now = time.time()
    _keep_reset_links(_reset_links() + [{"hash": _reset_hash(token), "expires": now + minutes * 60,
                                         "by_email": by_email, "made": now}])
    return token


def reset_emailed_lately() -> bool:
    """A link was emailed in the last few minutes: another isn't sent yet."""
    return any(x.get("by_email") and time.time() - x.get("made", 0) < RESET_EMAIL_GAP for x in _reset_links())


def _reset_link(token: str):
    wanted = _reset_hash(token)
    return next((x for x in _reset_links() if secrets.compare_digest(x.get("hash", ""), wanted)), None)


def reset_by_email(token: str) -> bool:
    return bool((_reset_link(token) or {}).get("by_email"))


def reset_token_ok(token: str) -> bool:
    return bool(token) and _reset_link(token) is not None


def finish_reset():
    """The password was changed: every link is used up."""
    _keep_reset_links([])


def admin_exists() -> bool:
    return get_db().execute("SELECT 1 FROM admin WHERE id=1").fetchone() is not None


def create_admin(password: str):
    get_db().execute(
        "INSERT INTO admin (id, password_hash, created_at) VALUES (1, ?, ?)",
        (ph.hash(password), utcnow().isoformat())
    )
    get_db().commit()
    forget_setup_token()


def set_password(password: str):
    get_db().execute("UPDATE admin SET password_hash=? WHERE id=1", (ph.hash(password),))
    get_db().commit()


def verify_password(password: str) -> bool:
    row = get_db().execute("SELECT password_hash FROM admin WHERE id=1").fetchone()
    if not row:
        return False
    try:
        return ph.verify(row["password_hash"], password)
    except VerifyMismatchError:
        return False
    except VerificationError as e:
        log.warning("the password couldn't be checked: %s", e)
        return False
    except InvalidHashError:
        log.error("the stored password is damaged - log in with the recovery key and set a new one")
        return False


# Sessions are signed cookies, so the server can't delete one. Instead
# each login carries the session version current when it was made; bump
# the version and every older session stops counting as logged in.
def _session_version() -> str:
    from soloblog import settings
    return settings.get("session_version") or "1"


def is_logged_in(session) -> bool:
    return session.get("admin") is True and session.get("sv") == _session_version()


# in the session when "Keep me signed in" was unticked (app.BrowserOnlySession)
BROWSER_ONLY = "browser_only"


def log_in(session, keep=True):
    session["admin"] = True
    session["sv"] = _session_version()
    if keep:
        session.pop(BROWSER_ONLY, None)
    else:
        session[BROWSER_ONLY] = True


def end_other_sessions(session=None):
    """Logs out every other browser - after a password or 2FA change, or
    on request. The browser making the change (session) stays logged in."""
    from soloblog import settings
    new = str(int(_session_version()) + 1)
    settings.set_many({"session_version": new})
    if session is not None and session.get("admin") is True:
        session["sv"] = new


def log_out(session):
    session.clear()
