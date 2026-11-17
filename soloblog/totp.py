import base64
import hashlib
import hmac
import json
import secrets
import struct
import time
from urllib.parse import quote

from soloblog.db import get_db

# Time-based one-time passwords (RFC 6238) - the six-digit codes an
# authenticator app shows. Standard library only: HMAC-SHA1 over a
# 30-second counter is the whole algorithm.

STEP = 30
DIGITS = 6
RECOVERY_CODE_COUNT = 10


def new_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _code_at(secret: str, step: int) -> str:
    key = base64.b32decode(secret + "=" * (-len(secret) % 8), casefold=True)
    digest = hmac.new(key, struct.pack(">Q", step), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    number = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(number % 10 ** DIGITS).zfill(DIGITS)


def matching_step(secret: str, code: str, now: float = None, window: int = 1):
    """The time step code is valid for (allowing one step either side
    for clock drift), or None."""
    code = "".join(c for c in (code or "") if c.isdigit())
    if len(code) != DIGITS or not secret:
        return None
    current = int((now if now is not None else time.time()) // STEP)
    for step in range(current - window, current + window + 1):
        if hmac.compare_digest(_code_at(secret, step), code):
            return step
    return None


def provisioning_uri(secret: str, account: str, issuer: str) -> str:
    """What the QR code holds - authenticator apps read this format."""
    label = quote(f"{issuer}:{account}")
    return f"otpauth://totp/{label}?secret={secret}&issuer={quote(issuer)}&digits={DIGITS}&period={STEP}"


def qr_svg(data: str) -> str:
    import qrcode
    import qrcode.image.svg
    img = qrcode.make(data, image_factory=qrcode.image.svg.SvgPathImage, box_size=8, border=2)
    return img.to_string(encoding="unicode")


# ---- the admin account's own 2FA state

def _row():
    return get_db().execute("SELECT totp_secret, recovery_codes, totp_last_step FROM admin WHERE id=1").fetchone()


def is_enabled() -> bool:
    row = _row()
    return bool(row and row["totp_secret"])


def _hash(code: str) -> str:
    return hashlib.sha256(code.strip().lower().replace("-", "").encode()).hexdigest()


def _new_recovery_codes():
    # 10 hex characters in two halves - easy to read out, still 40 bits each
    codes = [f"{secrets.token_hex(5)[:5]}-{secrets.token_hex(5)[:5]}" for _ in range(RECOVERY_CODE_COUNT)]
    return codes, json.dumps([_hash(c) for c in codes])


def enable(secret: str) -> list:
    """Turns 2FA on with an already-verified secret. Returns the
    recovery codes - the only time they exist in plain text."""
    codes, hashed = _new_recovery_codes()
    get_db().execute("UPDATE admin SET totp_secret=?, recovery_codes=?, totp_last_step=0 WHERE id=1",
                     (secret, hashed))
    get_db().commit()
    return codes


def regenerate_recovery_codes() -> list:
    codes, hashed = _new_recovery_codes()
    get_db().execute("UPDATE admin SET recovery_codes=? WHERE id=1", (hashed,))
    get_db().commit()
    return codes


def disable():
    get_db().execute("UPDATE admin SET totp_secret='', recovery_codes='[]', totp_last_step=0 WHERE id=1")
    get_db().commit()


def recovery_codes_left() -> int:
    row = _row()
    return len(json.loads(row["recovery_codes"] or "[]")) if row else 0


def check(code: str) -> bool:
    """A login's second step: a current authenticator code (never the
    same one twice), or an unused recovery code (used up by this)."""
    row = _row()
    if not row or not row["totp_secret"]:
        return False
    step = matching_step(row["totp_secret"], code)
    if step is not None:
        if step <= row["totp_last_step"]:
            return False
        get_db().execute("UPDATE admin SET totp_last_step=? WHERE id=1", (step,))
        get_db().commit()
        return True
    hashes = json.loads(row["recovery_codes"] or "[]")
    h = _hash(code or "")
    if code and h in hashes:
        hashes.remove(h)
        get_db().execute("UPDATE admin SET recovery_codes=? WHERE id=1", (json.dumps(hashes),))
        get_db().commit()
        return True
    return False
