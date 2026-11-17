import logging
import json
import re
import urllib.parse
import urllib.request

from fasthtml.common import Div, Script

from soloblog import js
from soloblog import netguard
from soloblog import csp

log = logging.getLogger(__name__)

# An optional spam check on the comment, contact, newsletter and members
# forms (Settings > Security > Spam protection), on top of the honeypot
# and rate limit they always have. Both services are free. The widget's token is
# copied into one captcha_token field on submit (CAPTCHA_JS), so the
# server reads the same field whichever service it is.

# name: (label, script, verify url)
PROVIDERS = {
    "turnstile": ("Cloudflare Turnstile", "https://challenges.cloudflare.com/turnstile/v0/api.js",
                  "https://challenges.cloudflare.com/turnstile/v0/siteverify"),
    "hcaptcha": ("hCaptcha", "https://js.hcaptcha.com/1/api.js", "https://api.hcaptcha.com/siteverify"),
}
# keys are dropped into an attribute and a POST body - their own shapes only
KEY_RE = re.compile(r"^[A-Za-z0-9_.-]{0,100}$")


def enabled(s) -> bool:
    return s.get("captcha_provider") in PROVIDERS and bool(s.get("captcha_site_key")) \
        and bool(s.get("captcha_secret"))


def Widget(s, cls="mb-2"):
    """Where the check draws itself, inside a form. CAPTCHA_JS renders
    it - a reply form's only once its popover opens."""
    if not enabled(s):
        return None
    return Div(data_captcha=s["captcha_site_key"], cls=cls)


def ApiScript(s):
    if not enabled(s):
        return None
    src = PROVIDERS[s["captcha_provider"]][1]
    return Script(src=f"{src}?render=explicit&onload=captchaReady", defer=True, nonce=csp.NONCE)


def passes(s, token: str, ip: str = "") -> bool:
    """True when the check is off, or the service vouches for token.
    A service that can't be reached counts as a fail - the visitor can
    try again, and spam doesn't slip through an outage."""
    if not enabled(s):
        return True
    if not token:
        return False
    data = urllib.parse.urlencode({"secret": s["captcha_secret"], "response": token, "remoteip": ip}).encode()
    req = urllib.request.Request(PROVIDERS[s["captcha_provider"]][2], data=data, method="POST",  # noqa: S310 - opened through netguard
                                 headers={"User-Agent": "Soloblog"})
    try:
        with netguard.open_url(req, timeout=10) as resp:
            return json.loads(resp.read()).get("success") is True
    except Exception as e:
        log.warning("verifying failed: %s", e)
        return False


CAPTCHA_JS = js.read("captcha.js")
