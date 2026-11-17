"""Paid members through Stripe, against a pretend Stripe: setting up the
product, prices and webhook; Checkout and back; the webhook - signed,
handled once, in any order - and what a member and the admin see. With
the abuse cases: forged and replayed webhooks, someone else's Checkout
session, a member id used again."""
import hashlib
import hmac
import json
import time

import pytest

from soloblog import config
from soloblog import members
from soloblog import settings
from soloblog import stripe_members as pay
from soloblog.db import get_db
from conftest import save_post
from test_members import BODY, SECRET, _signed_in, on  # noqa: F401 - the fixture

WEBHOOK_SECRET = "whsec_pretend"
PAY_KEYS = ("stripe_key", "members_currency", "members_price_month", "members_price_year", "members_trial_days",
            "members_tax", "stripe_product_id", "stripe_price_month", "stripe_price_month_is", "stripe_price_year",
            "stripe_price_year_is", "stripe_webhook_id", "stripe_webhook_secret", "stripe_last_ok_at",
            "stripe_last_failed_at", "stripe_last_error")
PERIOD_END = 1893456000  # 2030-01-01


class FakeStripe:
    """Just enough of Stripe's API: what was asked, and subscriptions as
    they are 'now'."""

    def __init__(self):
        self.calls = []
        self.subs = {}
        self.sessions = {}
        self.n = 0
        self.down = False

    def _id(self, prefix):
        self.n += 1
        return f"{prefix}_{self.n}"

    def __call__(self, method, path, data=None, secret=None):
        if self.down:
            raise pay.StripeError("couldn't reach Stripe")
        self.calls.append((method, path, data or {}))
        parts = path.strip("/").split("/")
        if method == "POST" and path == "/products":
            return {"id": self._id("prod"), "active": True}
        if method == "GET" and parts[0] == "products":
            return {"id": parts[1], "active": True}
        if method == "POST" and path == "/prices":
            return {"id": self._id("price")}
        if parts[0] == "webhook_endpoints":
            if method == "POST":
                return {"id": self._id("we"), "secret": WEBHOOK_SECRET}
            if method == "GET":
                return {"id": parts[1], "url": config.BASE_URL + pay.WEBHOOK_PATH, "status": "enabled"}
            return {}
        if method == "POST" and path == "/checkout/sessions":
            sid = self._id("cs_test")
            self.sessions[sid] = data
            return {"id": sid, "url": f"https://checkout.stripe.com/c/pay/{sid}"}
        if method == "GET" and parts[0] == "checkout":
            data = self.sessions[parts[2]]
            return {"id": parts[2], "client_reference_id": data["client_reference_id"],
                    "subscription": data.get("_sub")}
        if parts[0] == "subscriptions":
            sub = self.subs[parts[1]]
            if method == "POST":
                sub.update(data)
            return sub
        if parts[0] == "billing_portal":
            return {"url": "https://billing.stripe.com/p/session/test"}
        return {}

    def subscription(self, member, status="active", interval="month", amount=500, sub_id=None, **extra):
        sub_id = sub_id or self._id("sub")
        self.subs[sub_id] = {
            "id": sub_id, "customer": extra.pop("customer", f"cus_{member['id']}"), "status": status,
            "cancel_at_period_end": False, "current_period_end": PERIOD_END,
            "metadata": {"member_id": str(member["id"]), "email": member["email"]},
            "items": {"data": [{"price": {"unit_amount": amount, "currency": "usd",
                                          "recurring": {"interval": interval}}}]}, **extra}
        return self.subs[sub_id]


@pytest.fixture
def stripe(on, monkeypatch):
    """Members on, paid plans ready, and Stripe pretend."""
    before = {k: settings.get(k) for k in PAY_KEYS}
    fake = FakeStripe()
    monkeypatch.setattr(pay, "api", fake)
    settings.set_many({"stripe_key": "rk_test_pretend", "members_currency": "usd", "members_price_month": "5",
                       "members_price_year": "50", "members_trial_days": "0", "members_tax": "0",
                       "stripe_product_id": "prod_0", "stripe_price_month": "price_m", "stripe_price_year": "price_y",
                       "stripe_webhook_id": "we_0", "stripe_webhook_secret": WEBHOOK_SECRET})
    yield fake
    settings.set_many(before)
    get_db().execute("DELETE FROM stripe_events")
    get_db().commit()


def _signed(payload: bytes, secret=WEBHOOK_SECRET, stamp=None):
    stamp = int(stamp or time.time())
    sig = hmac.new(secret.encode(), f"{stamp}.".encode() + payload, hashlib.sha256).hexdigest()
    return {"Stripe-Signature": f"t={stamp},v1={sig}", "Content-Type": "application/json"}


def _event(kind, obj, event_id=None):
    return json.dumps({"id": event_id or f"evt_{time.time_ns()}", "type": kind,
                       "data": {"object": obj}}).encode()


def _post(client, payload, **kw):
    return client.post("/stripe/webhook", content=payload, headers=_signed(payload, **kw))


# ---- the signature

def test_signature_checks():
    payload = b'{"id": "evt_1"}'
    now = 1_800_000_000
    good = _signed(payload, stamp=now)["Stripe-Signature"]
    assert pay.verify(payload, good, WEBHOOK_SECRET, now=now)
    assert not pay.verify(payload, good, "whsec_other", now=now)
    assert not pay.verify(payload + b" ", good, WEBHOOK_SECRET, now=now)
    # an old one sent again
    assert not pay.verify(payload, good, WEBHOOK_SECRET, now=now + pay.TOLERANCE + 1)
    assert not pay.verify(payload, "", WEBHOOK_SECRET, now=now)
    assert not pay.verify(payload, good, "", now=now)
    assert not pay.verify(payload, "t=abc,v1=00", WEBHOOK_SECRET, now=now)
    # Stripe sends a second v1 while a secret is being rolled
    assert pay.verify(payload, f"t={now},v1=deadbeef," + good.split(",")[1], WEBHOOK_SECRET, now=now)


def test_forged_webhooks_change_nothing(app, stripe, on):
    c = _signed_in(app, on, "forger@example.com")
    member = members.by_email("forger@example.com")
    stripe.subscription(member, sub_id="sub_forged")
    payload = _event("customer.subscription.created", stripe.subs["sub_forged"])
    for headers in ({}, {"Stripe-Signature": "t=1,v1=00"}, _signed(payload, secret="whsec_guess")):
        r = c.post("/stripe/webhook", content=payload, headers=headers)
        assert r.status_code == 400
    assert members.by_email("forger@example.com")["status"] == "free"
    huge = b"{" + b" " * (600 * 1024) + b"}"
    assert c.post("/stripe/webhook", content=huge, headers=_signed(huge)).status_code == 413


# ---- paying

def test_choosing_a_plan_goes_to_checkout(app, client, stripe, on):
    # not signed in: the plans, and joining on the way
    page = client.get("/membership?next=/post/x").text
    assert "US$5" in page and "US$50" in page and "Save 17%" in page
    assert "/join?next=" in page
    r = client.post("/membership", data={"interval": "month"})
    assert r.status_code == 303 and r.headers["location"].startswith("/signin")

    c = _signed_in(app, on, "payer@example.com")
    settings.set_many({"members_trial_days": "14"})
    r = c.post("/membership", data={"interval": "year", "next": "/post/x"})
    assert r.status_code == 303 and r.headers["location"].startswith("https://checkout.stripe.com/")
    data = list(stripe.sessions.values())[-1]
    member = members.by_email("payer@example.com")
    assert data["line_items"][0]["price"] == "price_y" and data["client_reference_id"] == str(member["id"])
    assert data["customer_email"] == "payer@example.com"
    assert data["subscription_data"]["trial_period_days"] == 14
    assert "next=/post/x" in data["success_url"]
    # a plan that isn't offered
    settings.set_many({"stripe_price_year": ""})
    assert c.post("/membership", data={"interval": "year"}).headers["location"] == "/membership"


def test_back_from_checkout_and_the_webhook(app, stripe, on):
    c = _signed_in(app, on, "paid@example.com")
    member = members.by_email("paid@example.com")
    c.post("/membership", data={"interval": "month"})
    sid = list(stripe.sessions)[-1]
    sub = stripe.subscription(member, status="active")
    stripe.sessions[sid]["_sub"] = sub["id"]
    # back from Checkout: paid at once
    r = c.get(f"/account?paid={sid}")
    assert "you&#x27;re a paid member now" in r.text or "you're a paid member now" in r.text
    m = members.by_email("paid@example.com")
    assert m["status"] == "paid" and m["plan_amount"] == 500 and m["stripe_customer_id"] == sub["customer"]
    assert members.has_paid(m)
    assert "US$5 a month" in r.text and "Renews on" in r.text and "Manage billing" in r.text
    r = c.post("/account/billing")
    assert r.headers["location"].startswith("https://billing.stripe.com/")
    # the webhook for the same thing changes nothing more, and only counts once
    payload = _event("checkout.session.completed",
                     {"mode": "subscription", "subscription": sub["id"], "client_reference_id": str(m["id"])},
                     event_id="evt_once")
    assert _post(c, payload).status_code == 200
    assert _post(c, payload).status_code == 200
    assert get_db().execute("SELECT COUNT(*) FROM stripe_events WHERE id='evt_once'").fetchone()[0] == 1
    # cancelled at Stripe: free again
    sub["status"] = "canceled"
    _post(c, _event("customer.subscription.deleted", sub))
    m = members.by_email("paid@example.com")
    assert m["status"] == "free" and not members.has_paid(m) and m["stripe_subscription_id"] == ""


def test_someone_elses_checkout_session_does_nothing(app, stripe, on):
    a = _signed_in(app, on, "alice@example.com")
    a.post("/membership", data={"interval": "month"})
    sid = list(stripe.sessions)[-1]
    alice = members.by_email("alice@example.com")
    stripe.sessions[sid]["_sub"] = stripe.subscription(alice)["id"]
    b = _signed_in(app, on, "bob@example.com")
    b.get(f"/account?paid={sid}")
    assert members.by_email("bob@example.com")["status"] == "free"


def test_events_out_of_order_use_the_latest(app, stripe, on):
    c = _signed_in(app, on, "order@example.com")
    member = members.by_email("order@example.com")
    sub = stripe.subscription(member, status="canceled")
    # an older "active" copy arrives after the subscription was cancelled
    stale = {**sub, "status": "active"}
    _post(c, _event("customer.subscription.updated", stale))
    assert members.by_email("order@example.com")["status"] == "free"


def test_past_due_and_cancelling(app, admin, stripe, on):
    c = _signed_in(app, on, "late@example.com")
    member = members.by_email("late@example.com")
    sub = stripe.subscription(member, status="past_due")
    _post(c, _event("customer.subscription.updated", sub))
    m = members.by_email("late@example.com")
    assert members.has_paid(m)  # Stripe is still trying the card
    assert "Update your card" in c.get("/account").text
    # their account can't be deleted with a live plan - nor removed by the admin
    assert c.post("/account/delete").headers["location"] == "/account?error=paid"
    admin.post(f"/admin/members/{m['id']}/remove")
    assert members.by_email("late@example.com")
    page = admin.get("/admin/members?status=past_due").text
    assert "late@example.com" in page and "Past due" in page and "Monthly revenue" in page
    # the admin cancels: it runs to the end of the period
    admin.post(f"/admin/members/{m['id']}/cancel")
    assert stripe.subs[sub["id"]]["cancel_at_period_end"] is True
    m = members.by_email("late@example.com")
    assert m["cancel_at_period_end"] == 1 and "Ends on" in c.get("/account").text
    # and then they can go
    assert c.post("/account/delete").headers["location"] == "/"


def test_a_member_id_used_again_isnt_matched(app, stripe, on):
    _signed_in(app, on, "new@example.com")
    member = members.by_email("new@example.com")
    sub = stripe.subscription(member)
    sub["metadata"]["email"] = "someone-gone@example.com"
    assert pay.apply_subscription(sub) is None
    assert members.by_email("new@example.com")["status"] == "free"


def test_stripe_down_means_try_again(app, stripe, on):
    c = _signed_in(app, on, "retry@example.com")
    member = members.by_email("retry@example.com")
    sub = stripe.subscription(member)
    payload = _event("checkout.session.completed",
                     {"mode": "subscription", "subscription": sub["id"], "client_reference_id": str(member["id"])},
                     event_id="evt_retry")
    stripe.down = True
    assert _post(c, payload).status_code == 503
    # not marked as handled, so Stripe's next try works
    stripe.down = False
    assert _post(c, payload).status_code == 200
    assert members.by_email("retry@example.com")["status"] == "paid"


def test_site_health_says_when_a_reader_couldnt_pay(app, stripe, on):
    from soloblog import health
    assert health.payments_check()["title"] == "Payments are in test mode"
    c = _signed_in(app, on, "unlucky@example.com")
    stripe.down = True
    r = c.post("/membership", data={"interval": "month"})
    assert r.headers["location"] == "/membership?error=stripe"
    assert "try again later" in c.get("/membership?error=stripe").text
    found = health.payments_check()
    assert found["status"] == health.CRITICAL and "couldn't reach Stripe" in found["why"]
    stripe.down = False
    c.post("/membership", data={"interval": "month"})
    assert health.payments_check()["status"] != health.CRITICAL
    # not set up yet
    settings.set_many({"stripe_webhook_secret": ""})
    assert health.payments_check()["title"] == "Paid members aren't finished"


def test_gate_offers_the_plans(app, admin, client, stripe, on):
    slug = save_post(admin, title="For paying readers", body=BODY, visibility="paid")
    page = client.get(f"/post/{slug}").text
    assert SECRET not in page and f'href="/membership?next=/post/{slug}"' in page
    c = _signed_in(app, on, "free@example.com")
    page = c.get(f"/post/{slug}").text
    assert SECRET not in page and "/membership?next=" in page
    # not set up: no plans on offer
    settings.set_many({"stripe_webhook_secret": ""})
    assert "/membership" not in client.get(f"/post/{slug}").text
    assert client.get("/membership").status_code == 404


# ---- setting up

def test_set_up_makes_and_keeps_what_stripe_needs(stripe, monkeypatch):
    monkeypatch.setattr(config, "BASE_URL", "https://blog.example.com")
    settings.set_many({k: "" for k in PAY_KEYS if k.startswith("stripe_") and k != "stripe_key"})
    assert pay.set_up("rk_test_pretend", "usd", 500, 5000) == []
    s = settings.get_all()
    assert s["stripe_product_id"] and s["stripe_price_month"] and s["stripe_price_year"]
    assert s["stripe_webhook_secret"] == WEBHOOK_SECRET
    hook = [c for c in stripe.calls if c[:2] == ("POST", "/webhook_endpoints")][0][2]
    assert hook["url"] == "https://blog.example.com/stripe/webhook" and set(hook["enabled_events"]) == set(pay.EVENTS)
    made = len(stripe.calls)
    # saved again, the same: nothing new
    pay.set_up("rk_test_pretend", "usd", 500, 5000)
    assert not [c for c in stripe.calls[made:] if c[0] == "POST"]
    # a new monthly price: a new price, the old one archived, the yearly one kept
    old_month, year = s["stripe_price_month"], s["stripe_price_year"]
    pay.set_up("rk_test_pretend", "usd", 700, 5000)
    assert settings.get("stripe_price_month") != old_month and settings.get("stripe_price_year") == year
    assert ("POST", f"/prices/{old_month}", {"active": False}) in stripe.calls


def test_set_up_needs_https(stripe, monkeypatch):
    monkeypatch.setattr(config, "BASE_URL", "http://localhost:5001")
    problems = pay.set_up("rk_test_pretend", "usd", 500, 0)
    assert problems and "https://" in problems[0]


def test_settings_check_what_they_save(admin, stripe, monkeypatch):
    monkeypatch.setattr(config, "BASE_URL", "https://blog.example.com")
    def save(**fields):
        data = {"members_enabled": "1", "stripe_key": "rk_test_pretend", "members_currency": "usd",
                "members_price_month": "5", "members_price_year": "", "members_trial_days": "0", **fields}
        return admin.post("/admin/settings/members", data=data, headers={"HX-Request": "true"}).text
    assert "publishable" in save(stripe_key="pk_test_123")
    assert "amounts" in save(members_price_month="five")
    assert "365" in save(members_trial_days="900")
    assert "Saved" in save() and "error" not in save()
    assert settings.get("members_price_year") == "" and settings.get("stripe_price_year") == ""
    page = admin.get("/admin/settings?tab=members").text
    assert "Test mode" in page


def test_money():
    assert pay.minor("4.50", "usd") == 450 and pay.minor("4,50", "eur") == 450
    assert pay.minor("1000", "jpy") == 1000 and pay.minor("-1", "usd") is None
    assert pay.money(500, "usd") == "US$5" and pay.money(450, "gbp") == "£4.50" and pay.money(1000, "jpy") == "¥1,000"


def test_a_checkout_id_from_the_address_is_only_ever_one(monkeypatch):
    """?paid= comes from the address bar - it can't steer the request
    somewhere else in Stripe's API."""
    asked = []
    monkeypatch.setattr(pay, "api", lambda method, path, data=None, secret=None: asked.append(path) or {})
    for sneaky in ("cs_x/../../customers", "cs_test_1?expand=x", "cus_123", "cs_", "cs_test_a/b"):
        assert pay.sync_checkout(sneaky, {"id": 1}) is None
    assert asked == []
    pay.sync_checkout("cs_test_a1B2c3", {"id": 1})
    assert asked == ["/checkout/sessions/cs_test_a1B2c3"]
