import re

from fasthtml.common import *

from soloblog import js
from soloblog import csp
from soloblog import i18n
from soloblog.actions import on

# Visitor-facing third-party scripts that need rules about who sees them:
# Google AdSense, and the cookie-consent banner that gates Google
# Analytics. The analytics snippets themselves are built in app.py
# (analytics_tags); this decides when they may load.

CLIENT_RE = re.compile(r"^ca-pub-\d{10,20}$")
SLOT_RE = re.compile(r"^\d{6,20}$")

# where fixed ad units can go - settings key -> label
AD_SLOTS = {"adsense_slot_post": "After each post", "adsense_slot_roll": "Below the blog roll"}


def valid_client(client: str) -> bool:
    return bool(CLIENT_RE.match(client or ""))


def ads_active(settings, path: str, logged_in: bool, pinned_page: bool = False) -> bool:
    """Ads load for visitors only - never while you're logged in
    (clicking your own ads is against AdSense's rules), never on admin,
    login or setup pages, and on pages (pinned posts) only if allowed."""
    if logged_in or not valid_client(settings.get("adsense_client")):
        return False
    if path.startswith(("/admin", "/login", "/setup")):
        return False
    return not (pinned_page and settings.get("adsense_on_pages") != "1")


def adsense_script(client: str):
    return Script(src=f"https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={client}",
                  crossorigin="anonymous", **{"async": True}, nonce=csp.NONCE)


def ads_txt(client: str) -> str:
    """AdSense's authorized-seller line for /ads.txt. Google's own
    certification-authority ID (f08c47fec0942fa0) is the same for every
    publisher."""
    return f"google.com, {client.replace('ca-', '')}, DIRECT, f08c47fec0942fa0\n"


def AdSlot(settings, key: str, logged_in: bool, cls="mt-6"):
    """A fixed ad unit, labelled as one. Nothing at all when ads are off,
    the slot isn't set, or the viewer is the admin. cls: its room - none
    under a post, where the group around it spaces it."""
    slot = settings.get(key) or ""
    client = settings.get("adsense_client") or ""
    if logged_in or not valid_client(client) or not SLOT_RE.match(slot):
        return None
    return Div(
        P(i18n.t("Advertisement"), cls="text-xs text-base-content/40 mb-1"),
        Ins(cls="adsbygoogle", style="display:block", data_ad_client=client, data_ad_slot=slot,
            data_ad_format="auto", data_full_width_responsive="true"),
        Script("(adsbygoogle = window.adsbygoogle || []).push({});", nonce=csp.NONCE),
        cls=cls or None
    )


# ---- cookie consent

def consent_reasons(settings) -> list:
    """What on this site sets cookies or tracks visitors, so has to wait
    for a yes: Google Analytics (Cloudflare Web Analytics and Plausible are
    cookieless), and custom code the admin says does. Soloblog's own
    cookies - logins, a member's sign-in - are the essential kind that
    need no consent."""
    reasons = []
    if settings.get("analytics_provider") == "google" and settings.get("analytics_id"):
        reasons.append("Google Analytics")
    if settings.get("custom_head_consent") == "1" and (settings.get("custom_head") or "").strip():
        reasons.append("your custom code")
    return reasons


def consent_needed(settings) -> bool:
    """The banner, when it's on and there's something for it to ask about."""
    return settings.get("consent_banner") == "1" and bool(consent_reasons(settings))


def custom_head_gated(settings) -> bool:
    return consent_needed(settings) and "your custom code" in consent_reasons(settings)


def ConsentGate(tags):
    """The scripts that wait for a yes. A <template> keeps the browser
    from running them; CONSENT_JS copies them into the page on consent."""
    return Template(*tags, id="consent-scripts")


def ConsentBanner(settings, glass: str):
    privacy = settings.get("consent_privacy_url") or ""
    message = settings.get("consent_message") or i18n.t("This site uses cookies to understand how it's read.")
    return Div(
        Div(
            Div(
                P(message, " ", A(i18n.t("Privacy"), href=privacy, cls="link") if privacy else None, cls="text-sm"),
                Div(
                    Button(i18n.t("Decline"), type="button", cls="btn btn-sm", **on("click", "setConsent", "denied")),
                    Button(i18n.t("Accept"), type="button", cls="btn btn-sm btn-primary", **on("click", "setConsent", "granted")),
                    cls="flex gap-2 justify-end shrink-0"
                ),
                cls="card-body p-4 flex-col sm:flex-row sm:items-center gap-3"
            ),
            cls=f"card card-border {glass} shadow-lg max-w-2xl mx-auto"
        ),
        id="consent-banner", role="dialog", aria_label=i18n.t("Cookie consent"),
        cls="hidden fixed bottom-4 inset-x-0 z-50 px-4"
    )


CONSENT_JS = js.read("consent.js")
