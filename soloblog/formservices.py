import logging
import json
import re
import threading
import urllib.request

from soloblog import netguard

log = logging.getLogger(__name__)

# Online form services, two ways:
#
# FORWARDERS take what Soloblog's own contact form collected and pass it
# on - their dashboards, email alerts, spam filtering and integrations
# (Slack, Zapier, sheets...) without any mail setup here. The message is
# always kept in Admin > Messages too, so a service outage loses nothing.
#
# Hosted forms (Tally, Typeform, Google Forms...) are the whole form,
# built on their site - render.py embeds those, click-to-load, wherever
# their link appears: as the contact page, or on its own line in a post.

# key -> (label, endpoint template, what the ID field wants, ID pattern)
FORWARDERS = {
    "formspree": ("Formspree", "https://formspree.io/f/{}", "The form ID from its endpoint, e.g. xyzabcd",
                  r"[A-Za-z0-9]{4,32}"),
    "getform": ("Getform", "https://getform.io/f/{}", "The form ID from its endpoint",
                r"[A-Za-z0-9_-]{4,64}"),
    "basin": ("Basin", "https://usebasin.com/f/{}", "The form ID from its endpoint",
              r"[A-Za-z0-9_-]{4,64}"),
    "formcarry": ("Formcarry", "https://formcarry.com/s/{}", "The form ID from its endpoint",
                  r"[A-Za-z0-9_-]{4,64}"),
    "formsubmit": ("FormSubmit", "https://formsubmit.co/ajax/{}",
                   "Your email address (FormSubmit sends a one-time activation link to it first)",
                   r"[^@\s/]+@[^@\s/]+\.[^@\s/]+"),
}


def valid_id(provider: str, form_id: str) -> bool:
    spec = FORWARDERS.get(provider)
    return bool(spec and re.fullmatch(spec[3], form_id or ""))


def endpoint(provider: str, form_id: str) -> str:
    return FORWARDERS[provider][1].format(form_id)


def _post(url: str, data: dict):
    req = urllib.request.Request(url, data=json.dumps(data).encode(), method="POST", headers={  # noqa: S310 - opened through netguard
        "Content-Type": "application/json", "Accept": "application/json",
        "User-Agent": "Soloblog contact form",
    })
    try:
        with netguard.open_url(req, timeout=10) as resp:
            resp.read()
    except Exception as e:
        # a service that's down or misconfigured never costs the message -
        # it's already in Admin > Messages
        log.warning("forwarding to %s failed: %s", url, e)


def forward(provider: str, form_id: str, name: str, email: str, message: str, subject: str):
    """Sends one contact message on to the chosen service, in the
    background so the visitor isn't kept waiting on it."""
    if not valid_id(provider, form_id):
        return None
    data = {"name": name, "email": email, "message": message, "_subject": subject, "_replyto": email}
    t = threading.Thread(target=_post, args=(endpoint(provider, form_id), data), daemon=True)
    t.start()
    return t
