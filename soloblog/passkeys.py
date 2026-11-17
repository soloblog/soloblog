import logging
import secrets
import time
from soloblog.tz import utcnow
from urllib.parse import urlsplit

import webauthn
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url, options_to_json
from webauthn.helpers.structs import (AuthenticatorSelectionCriteria, PublicKeyCredentialDescriptor,
                                      ResidentKeyRequirement, UserVerificationRequirement)

from soloblog import config
from soloblog import settings
from soloblog.db import get_db

log = logging.getLogger(__name__)

# Passkeys (WebAuthn): log in with a fingerprint, face or device PIN
# instead of a password. The heavy lifting - CBOR, attestation, signature
# checks - is py_webauthn's; this file is the storage and the two
# ceremonies (register, log in), with their challenges kept in the
# session for five minutes.

CHALLENGE_TTL = 300


def relying_party(request):
    """(rp_id, allowed origins). The rp_id is the host the admin is
    actually on; the allowed origins are that exact origin (scheme from
    X-Forwarded-Proto behind a proxy) and BASE_URL's. A passkey is bound
    to its rp_id by the browser itself, so it can't be used on any other
    site, and the origin check rejects a login relayed through one."""
    host = request.url.hostname or "localhost"
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    netloc = request.headers.get("host") or request.url.netloc
    origins = {f"{proto}://{netloc}"}
    base = urlsplit(config.BASE_URL)
    if base.hostname == host:
        origins.add(f"{base.scheme}://{base.netloc}")
    return host, sorted(origins)


def _user_id() -> bytes:
    """A random, stable handle for the one admin - never their name."""
    value = settings.get("passkey_user_id")
    if not value:
        value = bytes_to_base64url(secrets.token_bytes(16))
        settings.set_many({"passkey_user_id": value})
    return base64url_to_bytes(value)


def list_all():
    return get_db().execute("SELECT * FROM passkeys ORDER BY created_at").fetchall()


def count() -> int:
    return get_db().execute("SELECT COUNT(*) AS n FROM passkeys").fetchone()["n"]


def delete(credential_id: str):
    get_db().execute("DELETE FROM passkeys WHERE id=?", (credential_id,))
    get_db().commit()


def _remember(session, key, challenge: bytes):
    session[key] = {"c": bytes_to_base64url(challenge), "t": int(time.time())}


def _take(session, key):
    """The stored challenge, used up - each one works exactly once."""
    item = session.pop(key, None)
    if not item or time.time() - item["t"] > CHALLENGE_TTL:
        return None
    return base64url_to_bytes(item["c"])


def registration_options(request, session) -> str:
    rp_id, _ = relying_party(request)
    options = webauthn.generate_registration_options(
        rp_id=rp_id, rp_name=settings.get("site_title") or "Soloblog",
        user_id=_user_id(), user_name=settings.get("author_name") or "admin",
        user_display_name=settings.get("author_name") or "Admin",
        # a discoverable credential, so the login page needs no username
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.PREFERRED),
        exclude_credentials=[PublicKeyCredentialDescriptor(id=base64url_to_bytes(p["id"])) for p in list_all()],
    )
    _remember(session, "pk_register", options.challenge)
    return options_to_json(options)


def register(request, session, credential: dict, name: str) -> str:
    """"" once stored, else why not."""
    challenge = _take(session, "pk_register")
    if not challenge:
        return "That took too long - try again"
    rp_id, origins = relying_party(request)
    try:
        verified = webauthn.verify_registration_response(
            credential=credential, expected_challenge=challenge, expected_rp_id=rp_id, expected_origin=origins)
    except Exception as e:
        log.warning("registration rejected: %s", e)
        return "Your device's answer didn't check out"
    transports = ",".join((credential.get("response") or {}).get("transports") or [])
    get_db().execute(
        "INSERT INTO passkeys (id, public_key, sign_count, name, transports, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (bytes_to_base64url(verified.credential_id), verified.credential_public_key, verified.sign_count,
         (name or "").strip()[:60] or "Passkey", transports, utcnow().isoformat()))
    get_db().commit()
    return ""


def login_options(request, session) -> str:
    rp_id, _ = relying_party(request)
    options = webauthn.generate_authentication_options(
        rp_id=rp_id, user_verification=UserVerificationRequirement.PREFERRED)
    _remember(session, "pk_login", options.challenge)
    return options_to_json(options)


def verify_login(request, session, credential: dict) -> bool:
    challenge = _take(session, "pk_login")
    row = get_db().execute("SELECT * FROM passkeys WHERE id=?", (str(credential.get("id", "")),)).fetchone()
    if not challenge or not row:
        return False
    rp_id, origins = relying_party(request)
    try:
        verified = webauthn.verify_authentication_response(
            credential=credential, expected_challenge=challenge, expected_rp_id=rp_id, expected_origin=origins,
            credential_public_key=row["public_key"], credential_current_sign_count=row["sign_count"])
    except Exception as e:
        log.warning("login rejected: %s", e)
        return False
    get_db().execute("UPDATE passkeys SET sign_count=?, last_used_at=? WHERE id=?",
                     (verified.new_sign_count, utcnow().isoformat(), row["id"]))
    get_db().commit()
    return True
