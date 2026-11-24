"""Paid members, through Stripe - its hosted Checkout to pay and its
Customer Portal to change a card, see invoices or cancel, so card details
never reach this site.

Set up from one restricted key (Settings > Members): Soloblog makes the
product, a monthly and a yearly price, and the webhook that tells it about
payments. Plain HTTPS, no Stripe package (docs/DECISIONS.md), on a pinned
API version, through netguard. Webhooks are checked against their signing
secret and their timestamp, and each event is handled once (stripe_events).
"""
import contextlib
import hashlib
import hmac
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, UTC

from soloblog import config
from soloblog import netguard
from soloblog import settings

API = "https://api.stripe.com/v1"
# the shape of what Stripe sends back - requests and the webhook alike
API_VERSION = "2024-06-20"
TOLERANCE = 300  # seconds a webhook's timestamp may be off - Stripe's own default
EVENTS = ("checkout.session.completed", "customer.subscription.created", "customer.subscription.updated",
          "customer.subscription.deleted")
WEBHOOK_PATH = "/stripe/webhook"

# code: (symbol, decimals) - the currencies a site is likely to charge in
CURRENCIES = {"usd": ("US$", 2), "eur": ("€", 2), "gbp": ("£", 2), "aud": ("A$", 2), "cad": ("CA$", 2),
              "nzd": ("NZ$", 2), "chf": ("CHF ", 2), "sek": ("kr ", 2), "nok": ("kr ", 2), "dkk": ("kr ", 2),
              "pln": ("zł ", 2), "czk": ("Kč ", 2), "inr": ("₹", 2), "sgd": ("S$", 2), "hkd": ("HK$", 2),
              "brl": ("R$", 2), "mxn": ("MX$", 2), "zar": ("R ", 2), "jpy": ("¥", 0), "krw": ("₩", 0)}


class StripeError(Exception):
    pass


def key() -> str:
    return (settings.get("stripe_key") or "").strip()


def test_mode() -> bool:
    return "_test_" in key()


def ready(s=None) -> bool:
    """Paid members can join: a key, prices and a webhook."""
    s = s or settings.get_all()
    return bool(s.get("stripe_key") and s.get("stripe_webhook_secret")
                and (s.get("stripe_price_month") or s.get("stripe_price_year")))


# ---- money

def minor(amount: str, currency: str):
    """"5" or "4.50" in the currency's smallest unit (500, 450) - None if it
    isn't an amount."""
    try:
        value = float(str(amount).strip().replace(",", "."))
    except ValueError:
        return None
    if value < 0 or value > 100000:
        return None
    return int(round(value * 10 ** CURRENCIES.get(currency, ("", 2))[1]))


def money(amount_minor: int, currency: str) -> str:
    symbol, decimals = CURRENCIES.get(currency, (currency.upper() + " ", 2))
    value = amount_minor / 10 ** decimals
    text = f"{value:,.0f}" if decimals == 0 or value == int(value) else f"{value:,.2f}"
    return f"{symbol}{text}"


# ---- talking to Stripe

def _form(data, prefix=""):
    """Stripe's form encoding: nested dicts and lists as a[b][0]=..."""
    out = []
    items = data.items() if isinstance(data, dict) else enumerate(data)
    for k, v in items:
        name = f"{prefix}[{k}]" if prefix else str(k)
        if isinstance(v, (dict, list, tuple)):
            out += _form(v, name)
        elif isinstance(v, bool):
            out.append((name, "true" if v else "false"))
        elif v is not None:
            out.append((name, str(v)))
    return out


def api(method: str, path: str, data=None, secret: str = None):
    """One call to Stripe's API, as JSON. Raises StripeError with Stripe's
    own message."""
    secret = secret or key()
    if not secret:
        raise StripeError("no Stripe key")
    body = None
    url = API + path
    if data and method == "GET":
        url += "?" + urllib.parse.urlencode(_form(data))
    elif data:
        body = urllib.parse.urlencode(_form(data)).encode()
    req = urllib.request.Request(url, data=body, method=method, headers={  # noqa: S310 - opened through netguard
        "Authorization": f"Bearer {secret}", "Stripe-Version": API_VERSION, "User-Agent": "Soloblog",
        "Content-Type": "application/x-www-form-urlencoded"})
    try:
        with netguard.open_url(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            message = json.loads(e.read())["error"]["message"]
        except (AttributeError, OSError, ValueError, KeyError, TypeError):
            # no body, or not Stripe's JSON error shape: the status says it
            message = f"HTTP {e.code}"
        raise StripeError(message) from None
    except (urllib.error.URLError, OSError, netguard.Blocked) as e:
        raise StripeError(f"couldn't reach Stripe: {e}") from None


# ---- setting up: product, prices, webhook

def set_up(secret, currency, month, year) -> list:
    """Makes (or updates) what Stripe needs from the settings: the product,
    the prices - a price can't change, so a new amount is a new price and
    the old one is archived - and the webhook. Returns what's still wrong,
    in plain words ([] when ready)."""
    s = settings.get_all()
    out = {}
    problems = []
    product = s.get("stripe_product_id")
    if product:
        try:
            if not api("GET", f"/products/{product}", secret=secret).get("active"):
                product = ""
        except StripeError:
            product = ""
    if not product:
        product = api("POST", "/products", {"name": f"{s.get('site_title') or 'Blog'} membership",
                                            "metadata": {"soloblog": "membership"}}, secret=secret)["id"]
    out["stripe_product_id"] = product
    for interval, amount in (("month", month), ("year", year)):
        current, current_amount = s.get(f"stripe_price_{interval}"), s.get(f"stripe_price_{interval}_is")
        # the product in it too: another account or test/live mode needs prices of its own
        wanted = f"{amount}:{currency}:{product}" if amount else ""
        if (current and wanted and current_amount == wanted) or (not current and not amount):
            continue
        if current:
            with contextlib.suppress(StripeError):
                api("POST", f"/prices/{current}", {"active": False}, secret=secret)
        if amount:
            # tax included: with Stripe Tax on, readers still pay the price they were shown
            price = api("POST", "/prices", {"product": product, "currency": currency, "unit_amount": amount,
                                            "recurring": {"interval": interval}, "tax_behavior": "inclusive"},
                        secret=secret)
            out[f"stripe_price_{interval}"], out[f"stripe_price_{interval}_is"] = price["id"], wanted
        else:
            out[f"stripe_price_{interval}"], out[f"stripe_price_{interval}_is"] = "", ""
    # the webhook: on a real address only - Stripe can't reach this computer
    if config.BASE_URL.startswith("https://"):
        url = config.BASE_URL + WEBHOOK_PATH
        hook = s.get("stripe_webhook_id")
        alive = False
        if hook:
            try:
                found = api("GET", f"/webhook_endpoints/{hook}", secret=secret)
                alive = found.get("url") == url and found.get("status") == "enabled"
            except StripeError:
                alive = False
        if not alive:
            if hook:
                with contextlib.suppress(StripeError):
                    api("DELETE", f"/webhook_endpoints/{hook}", secret=secret)
            made = api("POST", "/webhook_endpoints", {"url": url, "enabled_events": list(EVENTS),
                                                      "api_version": API_VERSION,
                                                      "description": "Soloblog: paid members"}, secret=secret)
            out["stripe_webhook_id"], out["stripe_webhook_secret"] = made["id"], made["secret"]
    else:
        problems.append("Stripe can't tell this site about payments until BASE_URL is its https:// URL")
    settings.set_many(out)
    return problems


def note(error=None):
    """How the last payment step went, for Site health."""
    from soloblog import members
    now = members._now().isoformat()
    settings.set_many({"stripe_last_error": str(error)[:300], "stripe_last_failed_at": now} if error
                      else {"stripe_last_ok_at": now})


# ---- joining and paying

def checkout_url(member, interval: str, next_url: str = "") -> str:
    """Stripe Checkout for the plan, to come back to /account - and on to
    next_url, the post they were reading."""
    s = settings.get_all()
    price = s.get(f"stripe_price_{interval}")
    if not price:
        raise StripeError("that plan isn't offered")
    data = {
        "mode": "subscription",
        "line_items": [{"price": price, "quantity": 1}],
        "success_url": f"{config.BASE_URL}/account?paid={{CHECKOUT_SESSION_ID}}"
                       + (f"&next={urllib.parse.quote(next_url)}" if next_url else ""),
        "cancel_url": f"{config.BASE_URL}/account",
        "client_reference_id": str(member["id"]),
        "allow_promotion_codes": True,
        "subscription_data": {"metadata": {"member_id": str(member["id"]), "email": member["email"]}},
    }
    if member["stripe_customer_id"]:
        data["customer"] = member["stripe_customer_id"]
    else:
        data["customer_email"] = member["email"]
    trial = int(s.get("members_trial_days") or 0)
    if trial > 0:
        data["subscription_data"]["trial_period_days"] = trial
    if s.get("members_tax") == "1":
        data["automatic_tax"] = {"enabled": True}
        if member["stripe_customer_id"]:
            data["customer_update"] = {"address": "auto"}
    return api("POST", "/checkout/sessions", data)["url"]


def portal_url(member) -> str:
    """Stripe's Customer Portal - card, invoices, cancelling. Made with a
    sensible set-up the first time, if the account has none yet."""
    data = {"customer": member["stripe_customer_id"], "return_url": f"{config.BASE_URL}/account"}
    try:
        return api("POST", "/billing_portal/sessions", data)["url"]
    except StripeError as e:
        if "configuration" not in str(e).lower():
            raise
    api("POST", "/billing_portal/configurations", {
        "business_profile": {"headline": settings.get("site_title") or "Membership"},
        "features": {"payment_method_update": {"enabled": True}, "invoice_history": {"enabled": True},
                     "customer_update": {"enabled": True, "allowed_updates": ["email", "address"]},
                     "subscription_cancel": {"enabled": True, "mode": "at_period_end"}},
        "default_return_url": f"{config.BASE_URL}/account"})
    return api("POST", "/billing_portal/sessions", data)["url"]


def cancel_at_period_end(member):
    """The admin's End plan: it runs to the end of what's paid, then stops."""
    sub = api("POST", f"/subscriptions/{member['stripe_subscription_id']}", {"cancel_at_period_end": True})
    apply_subscription(sub, member["id"])


# ---- what Stripe tells us

def verify(payload: bytes, header: str, secret: str, now=None) -> bool:
    """Stripe-Signature: t=timestamp,v1=signature - an HMAC-SHA256 of
    "timestamp.payload" with the endpoint's secret, within TOLERANCE."""
    if not header or not secret:
        return False
    parts = {}
    for item in header.split(","):
        k, _, v = item.strip().partition("=")
        parts.setdefault(k, []).append(v)
    try:
        stamp = int(parts.get("t", ["0"])[0])
    except ValueError:
        return False
    if abs((now or time.time()) - stamp) > TOLERANCE:
        return False
    expected = hmac.new(secret.encode(), f"{stamp}.".encode() + payload, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, sig) for sig in parts.get("v1", []))


def apply_subscription(sub: dict, member_id=None):
    """A member's paid state from a Stripe subscription."""
    from soloblog import members
    from soloblog.db import get_db
    meta = sub.get("metadata") or {}
    customer = sub.get("customer") or ""
    member = None
    if customer:
        member = get_db().execute("SELECT * FROM members WHERE stripe_customer_id=?", (customer,)).fetchone()
    if not member:
        wanted = member_id or (int(meta["member_id"]) if str(meta.get("member_id", "")).isdigit() else None)
        member = members.get(wanted) if wanted else None
        # an id can be used again after a member is deleted: only theirs if it's the same person
        if member and (member["stripe_customer_id"] not in ("", customer)
                       or (meta.get("email") and meta["email"].lower() != member["email"].lower())):
            member = None
    if not member:
        return None
    item = ((sub.get("items") or {}).get("data") or [{}])[0]
    price = item.get("price") or {}
    status = sub.get("status", "")
    ended = status in ("canceled", "incomplete_expired")
    period_end = sub.get("current_period_end") or item.get("current_period_end")
    members.update(
        member["id"],
        status="comped" if member["status"] == "comped" else ("free" if ended else "paid"),
        stripe_customer_id=sub.get("customer") or member["stripe_customer_id"],
        stripe_subscription_id="" if ended else sub.get("id", ""),
        subscription_status=status,
        plan_interval=(price.get("recurring") or {}).get("interval", ""),
        plan_amount=int(price.get("unit_amount") or 0),
        plan_currency=price.get("currency", ""),
        current_period_end=datetime.fromtimestamp(period_end, UTC).replace(tzinfo=None).isoformat() if period_end else None,
        cancel_at_period_end=int(bool(sub.get("cancel_at_period_end"))))
    return members.get(member["id"])


def _latest(sub_id: str, fallback=None) -> dict:
    """The subscription as it is now. Events can arrive out of order, so
    an event's own copy may be older than one already applied."""
    try:
        return api("GET", f"/subscriptions/{sub_id}")
    except StripeError:
        if fallback is None:
            raise
        return fallback


def handle(event: dict) -> str:
    """One webhook event - each only once, though applying one twice does
    no harm. A failure raises, so Stripe sends it again later. Returns
    what was done."""
    from soloblog.db import get_db
    db = get_db()
    if db.execute("SELECT 1 FROM stripe_events WHERE id=?", (event["id"],)).fetchone():
        return "already handled"
    kind, obj = event.get("type"), (event.get("data") or {}).get("object") or {}
    done = "ignored"
    if kind == "checkout.session.completed" and obj.get("mode") == "subscription" and obj.get("subscription"):
        ref = str(obj.get("client_reference_id") or "")
        apply_subscription(_latest(obj["subscription"]), int(ref) if ref.isdigit() else None)
        done = "checkout"
    elif kind in ("customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"):
        apply_subscription(_latest(obj["id"], obj) if obj.get("id") else obj)
        done = "subscription"
    db.execute("INSERT OR IGNORE INTO stripe_events (id, type, received_at) VALUES (?, ?, ?)",
               (event["id"], kind or "", datetime.now(UTC).replace(tzinfo=None).isoformat()))
    db.commit()
    return done


def sync_checkout(session_id: str, member):
    """Coming back from Checkout: the plan at once, rather than whenever the
    webhook arrives - only for this member's own session."""
    # it comes from the address bar: only ever Checkout's own shape of id,
    # so it can't point the request at another part of Stripe's API
    if not re.fullmatch(r"cs_(test_|live_)?[A-Za-z0-9]{1,200}", session_id or ""):
        return None
    session = api("GET", f"/checkout/sessions/{session_id}")
    if str(session.get("client_reference_id")) != str(member["id"]) or not session.get("subscription"):
        return None
    return apply_subscription(api("GET", f"/subscriptions/{session['subscription']}"), member["id"])


def monthly_revenue() -> dict:
    """{currency: amount in minor units} a month from live plans - a yearly
    one counted as a twelfth."""
    from soloblog.db import get_db
    out = {}
    for row in get_db().execute("SELECT plan_amount, plan_currency, plan_interval FROM members WHERE status='paid' "
                                "AND subscription_status IN ('active','past_due')"):
        amount = row["plan_amount"] / 12 if row["plan_interval"] == "year" else row["plan_amount"]
        out[row["plan_currency"]] = out.get(row["plan_currency"], 0) + amount
    return {k: int(round(v)) for k, v in out.items() if k}
