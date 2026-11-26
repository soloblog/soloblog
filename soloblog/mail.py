import contextlib
import logging
import os
import smtplib
import ssl
import json
import threading
import urllib.error
import urllib.request
from soloblog.tz import utcnow
from email.message import EmailMessage

import re

from soloblog import config, netguard, settings

log = logging.getLogger(__name__)

# no commas, semicolons or brackets: in a To line they'd make a list
_EMAIL = re.compile(r"[^@\s,;<>\"()]+@[^@\s.,;<>\"()]+(\.[^@\s.,;<>\"()]+)+")


def clean_email(value: str) -> str:
    """An email address as it should be kept - trimmed, the domain in lower
    case - or "" when it isn't one (no @, no dot in the domain, spaces)."""
    value = (value or "").strip()
    if len(value) > 254 or not _EMAIL.fullmatch(value):
        return ""
    local, domain = value.rsplit("@", 1)
    return f"{local}@{domain.lower()}"


# Settings > Email's "Your email provider": its server and port, and the
# one thing people trip on there. The username is the address itself.
# Outlook and Microsoft 365 take only OAuth now - no server to offer.
SMTP_PRESETS = {
    "gmail": ("Gmail", "smtp.gmail.com", 587,
              "Needs an app password: turn on 2-Step Verification, then make one at myaccount.google.com/apppasswords"),
    "icloud": ("iCloud Mail", "smtp.mail.me.com", 587,
               "Needs an app-specific password, from account.apple.com > Sign-In and Security"),
    "yahoo": ("Yahoo Mail", "smtp.mail.yahoo.com", 465,
              "Needs an app password, from Yahoo's Account security page"),
    "fastmail": ("Fastmail", "smtp.fastmail.com", 465,
                 "Needs an app password, from Fastmail's Settings > Privacy & Security"),
    "proton": ("Proton Mail", "smtp.protonmail.ch", 587,
               "Paid plans with your own domain: make an SMTP token in Proton's settings, under IMAP/SMTP"),
    "outlook": ("Outlook or Microsoft 365", "", 0,
                "Outlook and Microsoft 365 no longer let a site send with a password - choose Resend above instead"),
}


def smtp_server() -> tuple:
    """(host, port, username) - the provider's when one's picked."""
    preset = SMTP_PRESETS.get(settings.get("smtp_provider"))
    if preset:
        return preset[1], preset[2], settings.get("smtp_from")
    return settings.get("smtp_host"), int(settings.get("smtp_port") or "587"), settings.get("smtp_user")


def can_send() -> bool:
    return settings.get("email_provider") in ("smtp", "api")


# Resend's address for trying it out: it sends only to the address the
# Resend account was made with, so the owner's test arrives and nobody
# else's email does
TRY_OUT_DOMAINS = ("resend.dev",)


def only_reaches_you() -> bool:
    from email.utils import parseaddr
    if settings.get("email_provider") != "api":
        return False
    address = parseaddr(settings.get("email_api_from") or "")[1].lower()
    return address.rsplit("@", 1)[-1] in TRY_OUT_DOMAINS if "@" in address else False

# the one place anything in the app sends a real email to a real
# person - comment confirmation today, whatever needs it next. Every
# caller just calls send_email(); which of the two paths below
# actually fires is decided once, here, by the "email_provider"
# setting - a caller never needs to know or care which one is
# configured. Returns True/False rather than raising: a broken mail
# setup should never crash whatever triggered it, same reasoning as
# notify.py's own webhook failure handling.


_last_error = threading.local()


def send_email(to: str, subject: str, body: str, headers: dict = None, html: str = None) -> bool:
    """headers - extra ones, like the newsletter's List-Unsubscribe. html -
    a designed version, sent beside the plain text (the newsletter). How it
    went is kept for Site health: when the last one went out, or why the
    last one didn't."""
    provider = settings.get("email_provider")
    if provider not in ("smtp", "api"):
        return False
    # to is often what a visitor typed - one address, never a list; and a
    # line break in a subject or header is refused by the email library
    to = clean_email(to)
    if not to:
        return False
    subject = _one_line(subject)
    headers = {name: _one_line(value) for name, value in (headers or {}).items()}
    _last_error.text = ""
    ok = _to_outbox(to, subject, body, headers, html) if config.MAIL_OUTBOX else \
        (_send_smtp if provider == "smtp" else _send_api)(to, subject, body, headers, html)
    if not ok and provider == "smtp" and settings.get("email_api_key") and not config.MAIL_OUTBOX:
        # many hosts block SMTP's ports: with a Resend key as well, it goes that way
        log.warning("SMTP didn't take it; sending through Resend instead")
        ok = _send_api(to, subject, body, headers, html)
    now = utcnow().isoformat()
    try:
        settings.set_many({"mail_last_ok_at": now} if ok else
                          {"mail_last_failed_at": now,
                           "mail_last_error": (_last_error.text or "the email service didn't accept it")[:300]})
    except Exception as e:  # noting it must never stop the email
        log.warning("couldn't note the result: %s", e)
    return ok


def _to_outbox(to, subject, body, headers, html=None) -> bool:
    """MAIL_OUTBOX: the email as a file, for a developer or a journey to read."""
    import time
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, settings.get("smtp_from") or "site@localhost", to
    for name, value in (headers or {}).items():
        msg[name] = value
    msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")
    os.makedirs(config.MAIL_OUTBOX, exist_ok=True)
    path = os.path.join(config.MAIL_OUTBOX, f"{time.time_ns()}.eml")
    with open(path, "wb") as f:
        f.write(bytes(msg))
    return True


def _sender(address: str) -> str:
    """The From line: the site's name, then the address - as people see
    who an email is from. One written with a name already ("Name <a@b>")
    stays as it is."""
    from email.utils import formataddr
    title = _one_line(settings.get("site_title")).strip()
    return address if "<" in address or not title else formataddr((title, address))


def _one_line(text: str) -> str:
    return re.sub(r"[\r\n]+\s*", " ", text or "")


def _send_smtp(to: str, subject: str, body: str, headers: dict = None, html: str = None) -> bool:
    host, port, user = smtp_server()
    from_addr = settings.get("smtp_from") or user
    if not host or not from_addr:
        _last_error.text = "the SMTP host or the From address is missing"
        return False
    password = settings.get("smtp_password")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = _sender(from_addr)
    msg["To"] = to
    for name, value in (headers or {}).items():
        msg[name] = value
    msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")

    try:
        context = ssl.create_default_context()
        # 465 is the implicit-TLS convention (connect already encrypted);
        # every other port (587, 25...) connects plain then upgrades via
        # STARTTLS - the two aren't interchangeable, picking the wrong
        # one for a given provider just fails the handshake
        if port == 465:
            with smtplib.SMTP_SSL(host, port, context=context, timeout=10) as server:
                if user:
                    server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=10) as server:
                server.starttls(context=context)
                if user:
                    server.login(user, password)
                server.send_message(msg)
        return True
    except Exception as e:
        if isinstance(e, smtplib.SMTPRecipientsRefused):
            # its text is the reader's address: only the server's codes
            log.warning("the SMTP server at %s refused the recipient (%s)", host,
                        ", ".join(str(code) for code, _ in e.recipients.values()))
        else:
            log.warning("sending by SMTP through %s failed: %s", host, e)
        _last_error.text = str(e)
        return False


def _send_api(to: str, subject: str, body: str, headers: dict = None, html: str = None) -> bool:
    # Resend's API (resend.com) - one HTTPS POST, no SDK. Picked as the
    # API option because its request shape is about as simple as
    # transactional email gets (a bearer token and a flat JSON body) -
    # a different provider would slot in here the same way, its own
    # small function selected by email_provider, without touching any
    # caller of send_email().
    api_key = settings.get("email_api_key")
    from_addr = settings.get("email_api_from")
    if not api_key or not from_addr:
        _last_error.text = "the API key or the From address is missing"
        return False

    payload = json.dumps({
        "from": _sender(from_addr),
        "to": [to],
        "subject": subject,
        "text": body,
        **({"html": html} if html else {}),
        **({"headers": headers} if headers else {}),
    }).encode()
    req = urllib.request.Request(
        "https://api.resend.com/emails", data=payload, method="POST",
        # named: Resend's firewall turns away Python's default name (error 1010)
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}", "User-Agent": "Soloblog"}
    )
    try:
        netguard.open_url(req, timeout=10)
        return True
    except Exception as e:
        # the status, not Resend's reason: that can name the reader's address
        log.warning("sending through Resend failed: %s",
                    f"HTTP {e.code}" if isinstance(e, urllib.error.HTTPError) else e)
        _last_error.text = str(e)
        # Resend says why in the body ("The example.com domain is not
        # verified..."); the status line alone doesn't. Only an HTTPError
        # has a body, and it may not be the JSON Resend sends - then the
        # status line is all there is to say
        with contextlib.suppress(AttributeError, OSError, ValueError, KeyError, TypeError):
            _last_error.text += " - " + json.loads(e.read())["message"]
        return False


# a refusal for the email service's daily or monthly limit, not for the
# address: Resend's 429 "...exceeded your daily email sending quota",
# Gmail's "5.4.5 Daily user sending limit exceeded"
_OVER_LIMIT = ("quota", "5.4.5", "sending limit")


def over_limit() -> bool:
    """The last send_email in this thread was turned away because the
    email service's daily or monthly limit is reached."""
    text = (getattr(_last_error, "text", "") or "").lower()
    return any(words in text for words in _OVER_LIMIT)


# what an email server's refusal means, for someone who isn't a developer:
# (words in the error, lower case) -> what to do
_EXPLAINED = (
    (("535", "534", "username and password", "authentication", "auth", "credentials"),
     "The server didn't accept the username or password. Gmail, iCloud and Yahoo need an app password, "
     "not the one you sign in with"),
    (("timed out", "unreachable", "refused", "errno 101", "errno 111", "errno 110"),
     "Couldn't reach the email server. Some hosts block email ports - Resend works on all of them"),
    (("certificate",), "The server's certificate is for another name - check the server, as your email "
                       "provider writes it"),
    (("wrong version number", "unexpected eof", "ssl", "starttls"),
     "The port doesn't match the server. Try 587, or 465"),
    (("name or service not known", "nodename nor servname", "getaddrinfo", "no address associated"),
     "There's no email server by that name - check the server"),
    (("domain is not verified", "verify a domain", "testing emails to your own"),
     "Resend only sends from an address at a domain you've verified there - add your domain in Resend, "
     "or until then send to the address you signed up to Resend with"),
    (("api key is invalid", "401"),
     "Resend didn't accept the API key - copy it again from Resend"),
    (("553", "550", "sender", "from address", "not owned", "not allowed to send"),
     "The server won't send from that address - use your email account's own address as the From address"),
    (("missing",), "Fill in the server and the From address"),
)


def explain(error: str) -> str:
    """mail_last_error in plain words, with what to try - or the error as
    it came when it's not one of the usual ones."""
    low = (error or "").lower()
    for words, meaning in _EXPLAINED:
        if any(w in low for w in words):
            return meaning
    return error
