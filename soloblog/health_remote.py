"""Site health's checks that ask other servers: the HTTPS certificate,
the domain's registration (RDAP) and the email domain's SPF, DKIM and
DMARC records (DNS over HTTPS - Cloudflare, then Google). Once a day in
the background, or on Check again; only public names are sent, always
through netguard, and Settings can turn them off (health_remote).

A check that can't reach its server says nothing rather than raise a
false alarm - it tries again next time."""
import logging
import json
import socket
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from soloblog.tz import utcnow

from soloblog import config
from soloblog import health
from soloblog import netguard
from soloblog import settings
from soloblog.health import CRITICAL, GOOD, RECOMMENDED, check

log = logging.getLogger(__name__)

DAY = 24 * 3600
TIMEOUT = 6
DOH = ("https://cloudflare-dns.com/dns-query", "https://dns.google/resolve")
# the background loop; the tests turn it off and call refresh() themselves
AUTOMATIC = True
# addresses on a host's own domain - its registration is the host's, not yours
HOSTED = ("fly.dev", "onrender.com", "railway.app", "up.railway.app", "herokuapp.com", "netlify.app",
          "vercel.app", "pages.dev", "workers.dev", "github.io", "pikapod.net", "koyeb.app", "ondigitalocean.app",
          "elest.io", "cloudron.app", "repl.co", "glitch.me")
# DKIM keys live under a name the sender picks; these are the usual ones
DKIM_SELECTORS = ("default", "google", "selector1", "selector2", "k1", "k2", "s1", "s2", "mail", "dkim", "smtp",
                  "fm1", "protonmail", "zoho", "mxvault", "mandrill", "pm", "sendgrid", "mailjet")

_lock = threading.Lock()
_running = False


# ---- asking

def _json(url: str, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": "Soloblog site health", **(headers or {})})  # noqa: S310 - opened through netguard
    with netguard.open_url(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read(512 * 1024))


def txt_records(name: str):
    """The TXT records at a name, each joined into one string - [] when it
    has none, None when no DNS server could be asked."""
    for server in DOH:
        try:
            data = _json(f"{server}?{urllib.parse.urlencode({'name': name, 'type': 'TXT'})}",
                         {"Accept": "application/dns-json"})
        except Exception as e:
            log.warning("DNS over HTTPS (%s): %s", server, e)
            continue
        if data.get("Status") == 3:  # no such name
            return []
        if data.get("Status") != 0:
            continue
        out = []
        for answer in data.get("Answer") or []:
            if answer.get("type") == 16:
                # a long record arrives as several quoted pieces
                out.append("".join(part.strip('"') for part in answer.get("data", "").split('" "')))
        return out
    return None


def cert_expiry(host: str):
    """When the certificate the site shows runs out - or the reason it
    isn't valid now (raised as ssl.SSLError)."""
    netguard.check_url(f"https://{host}/")
    context = ssl.create_default_context()
    with socket.create_connection((host, 443), timeout=TIMEOUT) as sock, \
            context.wrap_socket(sock, server_hostname=host) as tls:
        not_after = tls.getpeercert()["notAfter"]
    return datetime.utcfromtimestamp(ssl.cert_time_to_seconds(not_after))


def domain_expiry(host: str):
    """(the registered domain, when its registration runs out) from RDAP -
    trying the address, then each name above it (blog.example.com, then
    example.com). (None, None) when there's no answer."""
    labels = host.lower().rstrip(".").split(".")
    for i in range(0, len(labels) - 1):
        name = ".".join(labels[i:])
        try:
            data = _json(f"https://rdap.org/domain/{name}", {"Accept": "application/rdap+json"})
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            log.warning("RDAP for %s: %s", name, e)
            return None, None
        except Exception as e:
            log.warning("RDAP for %s: %s", name, e)
            return None, None
        for event in data.get("events") or []:
            if event.get("eventAction") == "expiration" and event.get("eventDate"):
                return name, datetime.fromisoformat(event["eventDate"].replace("Z", "+00:00")).replace(tzinfo=None)
        return name, None
    return None, None


def _date(when) -> str:
    """"14 November 2026" - spelled out, so it reads the same anywhere."""
    return f"{when.day} {when.strftime('%B %Y')}"


def _days_left(when) -> int:
    return (when - utcnow()).days


# ---- the checks

def cert_check(host: str):
    try:
        expires = cert_expiry(host)
    except ssl.SSLCertVerificationError as e:
        return check("cert", "domain", CRITICAL, "Your HTTPS certificate isn't valid",
                     f"Browsers warn visitors away. The error was: {getattr(e, 'verify_message', '') or e}. Most hosts "
                     "renew certificates themselves - check your host's domain or certificate settings.")
    except Exception as e:
        log.warning("certificate for %s: %s", host, e)
        return None
    left = _days_left(expires)
    when = _date(expires)
    if left < 7:
        return check("cert", "domain", CRITICAL, f"Your HTTPS certificate runs out in {max(left, 0)} days",
                     f"On {when}. Hosts renew it automatically about a month ahead - if yours hasn't, check "
                     "its certificate settings now, or visitors will be warned away.")
    if left < 14:
        return check("cert", "domain", RECOMMENDED, f"Your HTTPS certificate runs out in {left} days",
                     f"On {when}. The certificate should have renewed by now - check your host's certificate settings.")
    return check("cert", "domain", GOOD, "Your HTTPS certificate is valid",
                 f"Until {when}. Your host renews it on its own.")


def domain_check(host: str):
    if any(host == h or host.endswith("." + h) for h in HOSTED):
        return None
    name, expires = domain_expiry(host)
    if not name or not expires:
        return None
    left = _days_left(expires)
    when = _date(expires)
    if left < 7:
        return check("domain", "domain", CRITICAL, f"{name} runs out in {max(left, 0)} days",
                     f"The domain's registration ends on {when}. Renew it at your registrar now - when it lapses, the "
                     "site and its email stop working, and someone else can buy the name.")
    if left < 30:
        return check("domain", "domain", RECOMMENDED, f"{name} runs out in {left} days",
                     f"The domain's registration ends on {when}. Renew it at your registrar, or turn on auto-renew.")
    return check("domain", "domain", GOOD, f"{name} is registered until {when}",
                 "Turning on auto-renew at your registrar keeps it that way.")


def sending_domain():
    """The domain email goes out from, or "" without email."""
    s = settings.get_all()
    sender = (s.get("email_api_from") if s.get("email_provider") == "api" else
              s.get("smtp_from") or s.get("smtp_user")) if s.get("email_provider") in ("smtp", "api") else ""
    sender = (sender or "").strip()
    if "<" in sender:
        sender = sender.split("<", 1)[1].rstrip(">")
    return sender.rsplit("@", 1)[1].lower() if "@" in sender else ""


def email_checks():
    domain = sending_domain()
    if not domain:
        return []
    out = []
    spf = txt_records(domain)
    if spf is not None:
        found = [r for r in spf if r.lower().startswith("v=spf1")]
        if len(found) > 1:
            out.append(check("spf", "email", RECOMMENDED, f"{domain} has {len(found)} SPF records",
                             "There should be one: with two, receiving servers can ignore both and treat your "
                             "email as unchecked. Merge them into one at your DNS provider.",
                             "How to set it up", "/admin/help?tab=how-it-works#why-email-lands-in-spam"))
        elif found:
            out.append(check("spf", "email", GOOD, f"{domain} has an SPF record",
                             "The SPF record names the servers allowed to send the domain's email."))
        else:
            out.append(check("spf", "email", RECOMMENDED, f"{domain} has no SPF record",
                             "An SPF record tells receiving servers who may send email for your domain - without one, more "
                             "of yours lands in spam. Your email provider's setup page gives the record to add.",
                             "How to set it up", "/admin/help?tab=how-it-works#why-email-lands-in-spam"))
    dmarc = txt_records(f"_dmarc.{domain}")
    if dmarc is not None:
        if any(r.lower().startswith("v=dmarc1") for r in dmarc):
            out.append(check("dmarc", "email", GOOD, f"{domain} has a DMARC record",
                             "Receiving servers know what to do with email that fails its checks."))
        else:
            out.append(check("dmarc", "email", RECOMMENDED, f"{domain} has no DMARC record",
                             "Gmail and Yahoo expect one from anyone sending in numbers, like a newsletter. The "
                             "simplest is a TXT record at _dmarc with the value v=DMARC1; p=none.",
                             "How to set it up", "/admin/help?tab=how-it-works#why-email-lands-in-spam"))
    selectors = ("resend",) if settings.get("email_provider") == "api" else DKIM_SELECTORS
    asked = False
    for selector in selectors:
        records = txt_records(f"{selector}._domainkey.{domain}")
        if records is None:
            continue
        asked = True
        if any("p=" in r for r in records):
            out.append(check("dkim", "email", GOOD, f"{domain} signs its email (DKIM)",
                             "Receiving servers can tell your email really came from you."))
            break
    else:
        if asked:
            out.append(check("dkim", "email", RECOMMENDED, f"No DKIM key found for {domain}",
                             "Your provider signs email with a key published in DNS - without the key, more email "
                             "lands in spam. Your provider's setup page gives the record to add. (If your provider "
                             "uses an unusual name for the key, it may be there and just not found here.)",
                             "How to set it up", "/admin/help?tab=how-it-works#why-email-lands-in-spam"))
    return out


def run_remote() -> list:
    from urllib.parse import urlparse
    out = []
    host = urlparse(config.BASE_URL).hostname or ""
    if host and not health.is_local():
        out += [cert_check(host), domain_check(host)]
    out += email_checks()
    return [r for r in out if r]


# ---- kept between visits

def refresh():
    """Runs them all now and keeps the results."""
    global _running
    if settings.get("health_remote") == "0":
        return
    try:
        results = run_remote()
        settings.set_many({"health_remote_results": json.dumps({"at": utcnow().isoformat(),
                                                               "results": results})})
    except Exception as e:  # a background thread - never let it die silently
        log.warning("remote checks: %s", e)
    finally:
        _running = False


def _kept():
    try:
        data = json.loads(settings.get("health_remote_results") or "{}")
        return data if isinstance(data, dict) else {}
    except ValueError:
        return {}


def stored() -> list:
    """The last results - starting a fresh run in the background when
    they're a day old."""
    if settings.get("health_remote") == "0":
        return []
    data = _kept()
    age = health._ago(data.get("at"))
    if AUTOMATIC and (age is None or age > timedelta(days=1)):
        _in_background()
    return [r for r in data.get("results") or [] if isinstance(r, dict) and r.get("status") in health.ORDER]


def checked_label() -> str:
    age = health._ago(_kept().get("at"))
    if age is None:
        return ""
    minutes = int(age.total_seconds() // 60)
    if minutes < 1:
        return "just now"
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    hours = minutes // 60
    return f"{hours} hour{'s' if hours != 1 else ''} ago" if hours < 48 else f"{hours // 24} days ago"


def _in_background():
    global _running
    with _lock:
        if _running:
            return
        _running = True
    threading.Thread(target=refresh, name="health", daemon=True).start()


FIRST_AFTER = 30  # seconds after the server starts


def _loop():
    # the first look soon after starting, not an hour later: until then the
    # menu's dot (health_alerts.note) only knew what the page last found -
    # and a host that sleeps when idle restarts it before the hour is up
    wait = FIRST_AFTER
    while True:
        time.sleep(wait)
        wait = 3600
        if not AUTOMATIC:
            continue
        try:
            age = health._ago(_kept().get("at"))
            if settings.get("health_remote") != "0" and (age is None or age > timedelta(days=1)):
                refresh()
            from soloblog import health_alerts
            health_alerts.check_and_send()
        except Exception:
            log.exception("the daily health check failed")


_thread = None


def start():
    """The daily run, and the alerts, without anyone opening the page."""
    global _thread
    with _lock:
        if _thread is None:
            _thread = threading.Thread(target=_loop, name="health-daily", daemon=True)
            _thread.start()
