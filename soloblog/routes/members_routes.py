"""The members area's pages: joining, signing in (a link and a code by
email), the member's own account - and Admin > Members."""
import contextlib
import json
import threading
from urllib.parse import quote

from fasthtml.common import *

from soloblog import auth
from soloblog import captcha
from soloblog import config
from soloblog import csp
from soloblog import i18n
from soloblog import mail
from soloblog import members
from soloblog import newsletter
from soloblog import posts
from soloblog import ratelimit
from soloblog import settings
from soloblog import stripe_members as pay
from soloblog.render import format_date
from soloblog.seo import page_meta
from soloblog.ui import Layout, ErrorPage

ar = APIRouter()

# which address the code page is for, between the form and the code - a
# cookie, not the address bar, so an email never sits in a URL or a log
PENDING = "soloblog_member_pending"
# "Keep me signed in" unticked, between the form and the code or link
SHORT = "soloblog_member_short"


def _off(session):
    return FtResponse(ErrorPage(404, settings.get_all(), auth.is_logged_in(session), posts.list_pinned_tree()),
                      status_code=404)


def _page(session, *content, width="max-w-md"):
    # data-status-slot: where a message sent back to the page shows (showStatus, app.py)
    return Layout(Div(Div(*content, P(data_status_slot=True, role="status", cls="empty:hidden"),
                          cls="card-body p-6 gap-3"),
                      cls=f"card card-border bg-base-100 {width} mx-auto"),
                  settings=settings.get_all(), logged_in=auth.is_logged_in(session),
                  pinned_tree=posts.list_pinned_tree())


def _error(text):
    return P(text, role="alert", cls="text-sm text-error") if text else None


def _send(email, token, code, purpose, s):
    """The email with the link and the code - in the background, so how
    long it takes doesn't tell anyone whether the address is a member's."""
    site = s.get("site_title") or "this site"
    link = f"{config.BASE_URL}/signin/link?token={quote(token)}"
    if purpose == "signup":
        subject = i18n.t("Finish joining {site}", site=site)
        lead = i18n.t("Here's the link to finish joining {site}:", site=site)
    else:
        subject = i18n.t("Sign in to {site}", site=site)
        lead = i18n.t("Here's your link to sign in to {site}:", site=site)
    body = (f"{lead}\n{link}\n\n{i18n.t('Or enter this code: {code}', code=code)}\n\n"
            f"{i18n.t('The link and the code work once, for 15 minutes.')}\n\n"
            f"{i18n.t("If you didn't ask for this, you can ignore this email.")}\n")
    threading.Thread(target=mail.send_email, args=(email, subject, body), daemon=True).start()


def _no_account(email, s):
    """Someone asked to sign in with an address that isn't a member's: tell
    them, so they're not left waiting. The page they see is the same as a
    member's, so it still doesn't show who's a member."""
    site = s.get("site_title") or "this site"
    body = (f"{i18n.t("There's no account for this email address at {site}. To become a member, go here:", site=site)}"
            f"\n{config.BASE_URL}/join\n\n{i18n.t("If you didn't ask for this, you can ignore this email.")}\n")
    threading.Thread(target=mail.send_email, args=(email, i18n.t("Sign in to {site}", site=site), body),
                     daemon=True).start()


def _welcome(member, s):
    """Settings > Members > Welcome email: sent once, when someone joins."""
    text = (s.get("members_welcome") or "").strip()
    if not text or not mail.can_send():
        return
    subject = i18n.t("Welcome to {site}", site=s.get("site_title") or config.BASE_URL)
    body = f"{text}\n\n{i18n.t('Your account')}: {config.BASE_URL}/account\n"
    threading.Thread(target=mail.send_email, args=(member["email"], subject, body), daemon=True).start()


def _signed_in(req, member, next_url):
    """Sets the session cookie and goes on."""
    resp = RedirectResponse(members.safe_next(next_url) or "/account", status_code=303)
    resp.set_cookie(members.COOKIE, members.new_session(member["id"]),
                    **members.cookie_kwargs(keep=not req.cookies.get(SHORT)))
    resp.delete_cookie(PENDING, path="/")
    resp.delete_cookie(SHORT, path="/")
    return resp


def _limited(req, email):
    """Ten tries an hour from a network, three an hour for an address -
    enough for a typo, not for flooding someone's inbox."""
    ip = ratelimit.client_ip(req)
    return not (ratelimit.hit(f"ip:{ip}", "member-email", limit=10, window_minutes=60)
                and ratelimit.hit(f"email:{email.lower()}", "member-email", limit=3, window_minutes=60))


# ---- joining and signing in

def JoinForm(s, next_url="", error=""):
    letter = newsletter.mode(s) == "builtin"
    return Form(
        _error(error),
        Label(Span(i18n.t("Email address"), cls="text-sm"),
              Input(type="email", name="email", required=True, autocomplete="email", autofocus=True,
                    maxlength="254", placeholder="you@example.com", cls="input w-full"),
              cls="flex flex-col gap-1"),
        Label(Span(i18n.t("Name"), Span(" " + i18n.t("(optional)"), cls="text-base-content/50"), cls="text-sm"),
              Input(name="name", autocomplete="name", maxlength="100", cls="input w-full"),
              cls="flex flex-col gap-1"),
        Label(Input(type="checkbox", name="newsletter", value="1", cls="checkbox checkbox-sm"),
              Span(i18n.t("Also email me new posts"), cls="text-sm"),
              cls="flex items-center gap-2 cursor-pointer") if letter else None,
        Input(name="website", cls="hidden", tabindex="-1", autocomplete="off"),
        Input(type="hidden", name="next", value=members.safe_next(next_url)),
        captcha.Widget(s),
        Button(i18n.t("Join"), type="submit", cls="btn btn-primary w-full mt-1"),
        action="/join", method="post", cls="flex flex-col gap-3"
    )


@ar.get("/join")
def join_page(session, hdrs, next: str = "", error: str = ""):
    s = settings.get_all()
    if not members.enabled(s):
        return _off(session)
    page_meta(hdrs, i18n.t("Become a member"), path="/join")
    hdrs.append(Meta(name="robots", content="noindex"))
    return _page(session,
                 H1(i18n.t("Become a member"), cls="text-xl font-bold"),
                 P(s.get("members_intro") or i18n.t("Members can read every members-only post. It's free."),
                   cls="text-sm text-base-content/70"),
                 JoinForm(s, next, {"email": i18n.t("That doesn't look like an email address"),
                                    "spam": i18n.t("Please complete the spam check"),
                                    "limit": i18n.t("Too many tries - try again later")}.get(error, "")),
                 P(i18n.t("Already a member?"), " ",
                   A(i18n.t("Sign in"), href=f"/signin?next={quote(members.safe_next(next))}", cls="link"),
                   cls="text-sm text-base-content/70 text-center"),
                 captcha.ApiScript(s))


@ar.post("/join")
def join(req, session, email: str = "", name: str = "", newsletter: bool = False, next: str = "",
         website: str = "", captcha_token: str = ""):
    s = settings.get_all()
    if not members.enabled(s):
        return _off(session)
    clean = mail.clean_email(email)
    back = f"/join?next={quote(members.safe_next(next))}&error="
    if not clean:
        return RedirectResponse(back + "email", status_code=303)
    if not captcha.passes(s, captcha_token, ratelimit.client_ip(req)):
        return RedirectResponse(back + "spam", status_code=303)
    if website.strip():
        return _check_email(clean, next)  # the honeypot - looks done, sends nothing
    if _limited(req, clean):
        return RedirectResponse(back + "limit", status_code=303)
    # someone joining who's already a member just gets a sign-in link
    purpose = "signin" if members.by_email(clean) else "signup"
    token, code = members.start(clean, purpose, name, newsletter, next)
    _send(clean, token, code, purpose, s)
    return _check_email(clean, next)


@ar.get("/signin")
def signin_page(session, hdrs, next: str = "", error: str = ""):
    s = settings.get_all()
    if not members.enabled(s):
        return _off(session)
    if members.current():
        return RedirectResponse(members.safe_next(next) or "/account", status_code=303)
    page_meta(hdrs, i18n.t("Sign in"), path="/signin")
    hdrs.append(Meta(name="robots", content="noindex"))
    return _page(session,
                 H1(i18n.t("Sign in"), cls="text-xl font-bold"),
                 P(i18n.t("We'll email you a link to sign in - no password needed."),
                   cls="text-sm text-base-content/70"),
                 Form(_error({"email": i18n.t("That doesn't look like an email address"),
                              "limit": i18n.t("Too many tries - try again later")}.get(error, "")),
                      Label(Span(i18n.t("Email address"), cls="text-sm"),
                            Input(type="email", name="email", required=True, autocomplete="email", autofocus=True,
                                  maxlength="254", placeholder="you@example.com", cls="input w-full"),
                            cls="flex flex-col gap-1"),
                      Label(Input(type="checkbox", name="keep", value="1", checked=True, cls="checkbox checkbox-sm"),
                            Span(i18n.t("Keep me signed in"), cls="text-sm"),
                            cls="flex items-center gap-2 cursor-pointer"),
                      Input(type="hidden", name="next", value=members.safe_next(next)),
                      Button(i18n.t("Email me a link"), type="submit", cls="btn btn-primary w-full mt-1"),
                      action="/signin", method="post", cls="flex flex-col gap-3"),
                 P(i18n.t("Not a member yet?"), " ",
                   A(i18n.t("Join"), href=f"/join?next={quote(members.safe_next(next))}", cls="link"),
                   cls="text-sm text-base-content/70 text-center"),
                 # the site's own admin signs in elsewhere
                 P(A(i18n.t("Site owner? Log in"), href="/login", cls="link link-hover"),
                   cls="text-xs text-base-content/50 text-center"))


@ar.post("/signin")
def signin(req, session, email: str = "", next: str = "", keep: str = ""):
    s = settings.get_all()
    if not members.enabled(s):
        return _off(session)
    clean = mail.clean_email(email)
    if not clean:
        return RedirectResponse(f"/signin?next={quote(members.safe_next(next))}&error=email", status_code=303)
    if _limited(req, clean):
        return RedirectResponse(f"/signin?next={quote(members.safe_next(next))}&error=limit", status_code=303)
    # the same answer whether or not the address is a member's
    if members.by_email(clean):
        token, code = members.start(clean, "signin", next_url=next)
        _send(clean, token, code, "signin", s)
    else:
        _no_account(clean, s)
    resp = _check_email(clean, next)
    if not keep:
        resp.set_cookie(SHORT, "1", max_age=members.TOKEN_MINUTES * 60, httponly=True, samesite="lax", path="/",
                        secure=config.BASE_URL.startswith("https://"))
    return resp


def _check_email(email, next_url):
    resp = RedirectResponse("/signin/check", status_code=303)
    resp.set_cookie(PENDING, email, max_age=members.TOKEN_MINUTES * 60, httponly=True, samesite="lax", path="/",
                    secure=config.BASE_URL.startswith("https://"))
    return resp


@ar.get("/signin/check")
def check_page(req, session, hdrs, error: str = ""):
    """Check your email - and the code, for when it's open on another device."""
    if not members.enabled():
        return _off(session)
    email = req.cookies.get(PENDING, "")
    page_meta(hdrs, i18n.t("Check your email"), path="/signin/check")
    hdrs.append(Meta(name="robots", content="noindex"))
    return _page(session,
                 H1(i18n.t("Check your email"), cls="text-xl font-bold"),
                 P(i18n.t("A link and a 6-digit code are on their way to {email}. They work once, for 15 minutes.",
                          email=email) if email else
                   i18n.t("A link and a 6-digit code are on their way. They work once, for 15 minutes."),
                   cls="text-sm text-base-content/70"),
                 Form(_error(i18n.t("That code isn't right, or it has run out") if error == "code" else ""),
                      Label(Span(i18n.t("Or enter the code"), cls="text-sm"),
                            Input(name="code", required=True, autofocus=True, inputmode="numeric", autocomplete="one-time-code",
                                  pattern="[0-9 ]{6,7}", maxlength="7", placeholder="123456",
                                  cls="input w-full text-center tracking-[0.3em] font-mono text-lg"),
                            cls="flex flex-col gap-1"),
                      Button(i18n.t("Continue"), type="submit", cls="btn btn-primary w-full"),
                      action="/signin/code", method="post", cls="flex flex-col gap-3") if email else None,
                 P(A(i18n.t("Send a new one"), href="/signin", cls="link"),
                   cls="text-sm text-base-content/70 text-center"))


@ar.post("/signin/code")
def signin_code(req, session, code: str = ""):
    if not members.enabled():
        return _off(session)
    email = req.cookies.get(PENDING, "")
    if not ratelimit.hit(f"ip:{ratelimit.client_ip(req)}", "member-code", limit=20, window_minutes=15):
        return RedirectResponse("/signin/check?error=code", status_code=303)
    row = members.redeem_code(email, code) if email else None
    member = members.complete(row) if row else None
    if not member:
        return RedirectResponse("/signin/check?error=code", status_code=303)
    if row["purpose"] == "signup":
        _welcome(member, settings.get_all())
    return _signed_in(req, member, row["next"])


@ar.get("/signin/link")
def link_page(session, hdrs, token: str = ""):
    """The emailed link: a page that signs in with a button press (done for
    you by the page) - mail scanners that open links to check them don't
    use the sign-in up."""
    if not members.enabled():
        return _off(session)
    page_meta(hdrs, i18n.t("Sign in"), path="/signin/link")
    hdrs.append(Meta(name="robots", content="noindex"))
    return _page(session,
                 H1(i18n.t("Signing you in"), cls="text-xl font-bold"),
                 Form(Input(type="hidden", name="token", value=token),
                      Button(i18n.t("Sign in"), type="submit", cls="btn btn-primary w-full"),
                      action="/signin/link", method="post", id="member-link-form"),
                 Script("document.getElementById('member-link-form').requestSubmit();", nonce=csp.NONCE))


@ar.post("/signin/link")
def signin_link(req, session, hdrs, token: str = ""):
    if not members.enabled():
        return _off(session)
    row = members.redeem_link(token)
    member = members.complete(row) if row else None
    if not member:
        page_meta(hdrs, i18n.t("Sign in"), path="/signin/link")
        return _page(session,
                     H1(i18n.t("That link has run out"), cls="text-xl font-bold"),
                     P(i18n.t("Each link works once, for 15 minutes. Ask for a new one."),
                       cls="text-sm text-base-content/70"),
                     A(i18n.t("Sign in"), href="/signin", cls="btn btn-primary"))
    if row["purpose"] == "signup":
        _welcome(member, settings.get_all())
    return _signed_in(req, member, row["next"])


@ar.post("/signout")
def signout(req):
    members.end_session(req.cookies.get(members.COOKIE, ""))
    resp = RedirectResponse("/", status_code=303)
    resp.delete_cookie(members.COOKIE, path="/")
    return resp


# ---- paying: the plans, Stripe Checkout, and back

def _plans(s):
    """[(interval, amount in minor units)] on offer."""
    currency = s.get("members_currency") or "usd"
    out = []
    for interval in ("month", "year"):
        amount = pay.minor(s.get(f"members_price_{interval}") or "", currency)
        if s.get(f"stripe_price_{interval}") and amount:
            out.append((interval, amount))
    return out


def PlanCard(interval, amount, s, member, next_url, saving=0, main=True):
    """main: the plan to point people to - the yearly one, when both are offered."""
    currency = s.get("members_currency") or "usd"
    per = i18n.t("a month") if interval == "month" else i18n.t("a year")
    look = f"btn {'btn-primary' if main else ''} btn-sm w-full"
    button = Button(i18n.t("Choose"), type="submit", cls=look) if member else \
        A(i18n.t("Choose"), href=f"/join?next={quote('/membership?next=' + quote(next_url))}", cls=look)
    return Form(
        Div(i18n.t("Monthly") if interval == "month" else i18n.t("Yearly"), cls="text-sm font-medium"),
        Div(Span(pay.money(amount, currency), cls="text-2xl font-bold tabular-nums"), " ",
            Span(per, cls="text-sm text-base-content/60")),
        Span(i18n.t("Save {percent}%", percent=saving), cls="badge badge-sm badge-success badge-soft")
        if saving else Span(cls="h-5 max-sm:hidden"),
        Input(type="hidden", name="interval", value=interval),
        Input(type="hidden", name="next", value=next_url),
        button,
        action="/membership", method="post",
        cls="card card-border border-base-300 p-4 gap-2 items-start flex-1 min-w-0"
    )


@ar.get("/membership")
def membership_page(session, hdrs, next: str = "", error: str = ""):
    s = settings.get_all()
    if not members.enabled(s) or not pay.ready(s):
        return _off(session)
    member = members.current()
    if member and members.has_paid(member):
        return RedirectResponse("/account", status_code=303)
    page_meta(hdrs, i18n.t("Become a paid member"), path="/membership")
    hdrs.append(Meta(name="robots", content="noindex"))
    plans = _plans(s)
    next_url = members.safe_next(next)
    month = dict(plans).get("month")
    year = dict(plans).get("year")
    saving = int(round(100 - year * 100 / (month * 12))) if month and year and year < month * 12 else 0
    trial = int(s.get("members_trial_days") or 0)
    return _page(session,
                 H1(i18n.t("Become a paid member"), cls="text-xl font-bold"),
                 P(i18n.t("Paid members can read every post, and help keep this site going."),
                   cls="text-sm text-base-content/70"),
                 _error({"stripe": i18n.t("Payments aren't working right now - try again later")}.get(error, "")),
                 Div(*[PlanCard(i, a, s, member, next_url, saving if i == "year" else 0,
                                main=i == "year" or len(plans) == 1) for i, a in plans],
                     cls="flex flex-col sm:flex-row gap-3"),
                 P(i18n.t("Free for the first {days} days. Cancel any time.", days=trial) if trial
                   else i18n.t("Cancel any time."), cls="text-xs text-base-content/60 text-center"),
                 None if member else P(i18n.t("Already a member?"), " ",
                                       A(i18n.t("Sign in"),
                                         href=f"/signin?next={quote('/membership?next=' + quote(next_url))}",
                                         cls="link"), cls="text-sm text-base-content/70 text-center"),
                 width="max-w-lg")


@ar.post("/membership")
def membership(session, interval: str = "", next: str = ""):
    s = settings.get_all()
    if not members.enabled(s) or not pay.ready(s):
        return _off(session)
    member = members.current()
    if not member:
        return RedirectResponse(f"/signin?next={quote('/membership')}", status_code=303)
    if members.has_paid(member):
        return RedirectResponse("/account", status_code=303)
    if interval not in dict(_plans(s)):
        return RedirectResponse("/membership", status_code=303)
    try:
        url = pay.checkout_url(member, interval, members.safe_next(next))
    except pay.StripeError as e:
        pay.note(e)
        return RedirectResponse("/membership?error=stripe", status_code=303)
    pay.note()
    return RedirectResponse(url, status_code=303)


@ar.post("/account/billing")
def account_billing():
    member = _member_or_signin()
    if not member:
        return RedirectResponse("/signin?next=/account", status_code=303)
    if not member["stripe_customer_id"]:
        return RedirectResponse("/account", status_code=303)
    try:
        url = pay.portal_url(member)
    except pay.StripeError as e:
        pay.note(e)
        return RedirectResponse("/account?error=stripe", status_code=303)
    pay.note()
    return RedirectResponse(url, status_code=303)


@ar.post("/stripe/webhook")
async def stripe_webhook(req):
    from starlette.concurrency import run_in_threadpool
    payload = await req.body()
    if len(payload) > 512 * 1024:  # Stripe's events are a few kilobytes
        return Response("too large", status_code=413)
    secret = settings.get("stripe_webhook_secret")
    if not pay.verify(payload, req.headers.get("stripe-signature", ""), secret):
        return Response("bad signature", status_code=400)
    try:
        event = json.loads(payload)
        # it may ask Stripe for the latest - not on the event loop
        await run_in_threadpool(pay.handle, event)
    except (ValueError, KeyError):
        return Response("not an event", status_code=400)
    except pay.StripeError:
        # Stripe tries again later, for up to three days
        return Response("try again", status_code=503)
    return Response("ok")


# ---- the member's own account

def PlanSection(member, s):
    """What they pay, when it renews or ends - and the way to Stripe's
    portal, or to a plan."""
    if member["status"] == "paid" and member["stripe_subscription_id"]:
        price = pay.money(member["plan_amount"], member["plan_currency"])
        per = i18n.t("{price} a month", price=price) if member["plan_interval"] == "month" else \
            i18n.t("{price} a year", price=price)
        date = format_date(member["current_period_end"]) if member["current_period_end"] else ""
        if member["subscription_status"] == "trialing":
            when = i18n.t("Free trial until {date}", date=date)
        elif member["cancel_at_period_end"]:
            when = i18n.t("Ends on {date}", date=date)
        else:
            when = i18n.t("Renews on {date}", date=date)
        line = P(per, " · ", when, cls="text-sm") if date else P(per, cls="text-sm")
    else:
        line = None
    late = member["status"] == "paid" and member["subscription_status"] == "past_due"
    billing = Form(Button(i18n.t("Manage billing"), type="submit", cls="btn btn-sm"),
                   action="/account/billing", method="post") if member["stripe_customer_id"] and pay.key() else None
    upgrade = A(i18n.t("Become a paid member"), href="/membership", cls="btn btn-primary btn-sm") \
        if not members.has_paid(member) and pay.ready(s) else None
    if not (line or late or billing or upgrade):
        return None
    return Div(line,
               P(i18n.t("Your last payment didn't go through. Update your card under Manage billing."),
                 role="alert", cls="text-sm text-warning") if late else None,
               Div(upgrade, billing, cls="flex flex-wrap gap-2") if upgrade or billing else None,
               cls="flex flex-col gap-2")


@ar.get("/account")
def account(session, hdrs, saved: str = "", error: str = "", paid: str = "", next: str = ""):
    s = settings.get_all()
    if not members.enabled(s):
        return _off(session)
    member = members.current()
    if not member:
        return RedirectResponse("/signin?next=/account", status_code=303)
    welcome = False
    if paid:
        # back from Checkout: the plan now, rather than when the webhook comes
        if not members.has_paid(member):
            with contextlib.suppress(pay.StripeError):
                member = pay.sync_checkout(paid, member) or member
        welcome = members.has_paid(member)
        if welcome and members.safe_next(next):
            return RedirectResponse(members.safe_next(next), status_code=303)
    page_meta(hdrs, i18n.t("Your account"), path="/account")
    hdrs.append(Meta(name="robots", content="noindex"))
    letter = newsletter.mode(s) == "builtin"
    return _page(session,
                 H1(i18n.t("Your account"), cls="text-xl font-bold"),
                 P(i18n.t("Saved"), role="status", cls="text-sm text-success") if saved else None,
                 P(i18n.t("Thank you - you're a paid member now"), role="status", cls="text-sm text-success")
                 if welcome else
                 P(i18n.t("Thank you - your payment is on its way, and your plan starts as soon as it arrives"),
                   role="status", cls="text-sm text-base-content/70") if paid else None,
                 _error({"paid": i18n.t("Cancel your plan first, under Manage billing"),
                         "stripe": i18n.t("Payments aren't working right now - try again later")}.get(error, "")),
                 Div(Div(member["email"], cls="font-medium break-all"),
                     Div(i18n.t("Paid member") if member["status"] in ("paid", "comped") else i18n.t("Free member"),
                         " · ",
                         i18n.t("Member since {date}", date=format_date(member["created_at"])),
                         cls="text-sm text-base-content/60"), cls="mb-2"),
                 PlanSection(member, s),
                 Form(Label(Span(i18n.t("Name"), cls="text-sm"),
                            Div(Input(name="name", value=member["name"], maxlength="100", autocomplete="name",
                                      cls="input join-item flex-1 min-w-0"),
                                Button(i18n.t("Save"), type="submit", cls="btn join-item"), cls="join w-full"),
                            cls="flex flex-col gap-1"),
                      action="/account/name", method="post"),
                 Form(Label(Input(type="checkbox", name="newsletter", value="1", cls="toggle toggle-sm",
                                  checked=newsletter.is_subscribed(member["email"]), data_autosubmit=True),
                            Span(i18n.t("Email me new posts"), cls="text-sm"),
                            cls="flex items-center gap-3 cursor-pointer"),
                      Noscript(Button(i18n.t("Save"), type="submit", cls="btn btn-sm mt-2")),
                      action="/account/newsletter", method="post") if letter else None,
                 Div(Form(Button(i18n.t("Sign out"), type="submit", cls="btn btn-sm"), action="/signout",
                          method="post"),
                     Form(Button(i18n.t("Sign out everywhere"), type="submit", cls="btn btn-sm btn-ghost"),
                          action="/account/signout-everywhere", method="post"),
                     A(i18n.t("Download my data"), href="/account/data", cls="btn btn-sm btn-ghost"),
                     cls="flex flex-wrap gap-2 pt-3 border-t-[length:var(--border)] border-base-300"),
                 Form(Button(i18n.t("Delete my account"), type="button", cls="btn btn-sm btn-ghost text-error",
                             data_confirm=i18n.t("Delete your membership? Members-only posts will be closed to "
                                                 "you, and it can't be undone.")),
                      action="/account/delete", method="post"))


def _member_or_signin():
    return members.current() if members.enabled() else None


@ar.post("/account/name")
def account_name(name: str = ""):
    member = _member_or_signin()
    if not member:
        return RedirectResponse("/signin?next=/account", status_code=303)
    members.update(member["id"], name=name.strip()[:100])
    return RedirectResponse("/account?saved=1", status_code=303)


@ar.post("/account/newsletter")
def account_newsletter(newsletter: bool = False):
    from soloblog import newsletter as letter
    member = _member_or_signin()
    if not member:
        return RedirectResponse("/signin?next=/account", status_code=303)
    if newsletter:
        letter.subscribe_confirmed(member["email"])
    else:
        letter.unsubscribe_email(member["email"])
    return RedirectResponse("/account?saved=1", status_code=303)


@ar.post("/account/signout-everywhere")
def account_signout_everywhere():
    member = _member_or_signin()
    if member:
        members.end_all_sessions(member["id"])
    resp = RedirectResponse("/", status_code=303)
    resp.delete_cookie(members.COOKIE, path="/")
    return resp


@ar.get("/account/data")
def account_data():
    member = _member_or_signin()
    if not member:
        return RedirectResponse("/signin?next=/account", status_code=303)
    return Response(json.dumps(members.data_for(member), ensure_ascii=False, indent=2),
                    media_type="application/json",
                    headers={"Content-Disposition": 'attachment; filename="my-membership.json"',
                             "Cache-Control": "private, no-store"})


@ar.post("/account/delete")
def account_delete():
    member = _member_or_signin()
    if not member:
        return RedirectResponse("/signin?next=/account", status_code=303)
    # a live subscription is cancelled at Stripe first, so nobody is charged for an account that's gone
    if member["stripe_subscription_id"] and member["subscription_status"] in members.PAID_STATES \
            and not member["cancel_at_period_end"]:
        return RedirectResponse("/account?error=paid", status_code=303)
    members.delete(member["id"])
    resp = RedirectResponse("/", status_code=303)
    resp.delete_cookie(members.COOKIE, path="/")
    return resp


# ---- Admin > Members

MEMBERS_PER_PAGE = 50
FILTERS = (("", "All"), ("free", "Free"), ("paid", "Paid"), ("past_due", "Past due"))


def _status_badge(m):
    if m["status"] == "comped":
        return Span("Paid · given", cls="badge badge-sm badge-primary badge-soft")
    if m["status"] == "paid":
        if m["subscription_status"] == "past_due":
            return Span("Past due", cls="badge badge-sm badge-warning")
        if m["subscription_status"] in members.PAID_STATES:
            # ended by them or with End plan: paid up to a date, then it stops
            if m["cancel_at_period_end"]:
                return Span("Paid · ending", cls="badge badge-sm badge-warning badge-soft")
            return Span("Paid", cls="badge badge-sm badge-primary")
        return Span("Plan ended", cls="badge badge-sm badge-outline")
    return Span("Free", cls="badge badge-sm badge-outline")


def _plan_line(m, relative):
    """"US$5 a month, renews 3 Nov" - for a member paying through Stripe."""
    if not (m["status"] == "paid" and m["stripe_subscription_id"] and m["plan_amount"]):
        return ""
    line = f"{pay.money(m['plan_amount'], m['plan_currency'])} a {m['plan_interval'] or 'month'}"
    if m["current_period_end"]:
        when = format_date(m["current_period_end"])
        line += (f", trial until {when}" if m["subscription_status"] == "trialing"
                 else f", ends {when}" if m["cancel_at_period_end"] else f", renews {when}")
    return line


def MemberRow(m, subscribed, relative):
    from soloblog.ui import IconAction, RowActions, RowCheck, TICK_ROW, TICK_ROW_CLS, TRASH_SVG, KEY_SVG, X_SVG, \
        EXTERNAL_SVG
    stripe_paid = m["status"] == "paid" and m["stripe_subscription_id"]
    actions = []
    if m["stripe_customer_id"] and not config.DEMO_MODE:
        test = "test/" if pay.test_mode() else ""
        actions.append(IconAction(EXTERNAL_SVG, "Open in Stripe", target="_blank", rel="noopener",
                                  href=f"https://dashboard.stripe.com/{test}customers/{m['stripe_customer_id']}"))
    if stripe_paid and m["subscription_status"] in members.PAID_STATES and not m["cancel_at_period_end"]:
        until = format_date(m["current_period_end"]) if m["current_period_end"] else "the end of what they've paid for"
        actions.append(Form(IconAction(X_SVG, "End plan",
                                       confirm=f"End {m['email']}'s plan? It runs until {until}, then stops - "
                                               "they're not charged again."),
                            action=f"/admin/members/{m['id']}/cancel", method="post", cls="contents"))
    if not stripe_paid:
        comp = m["status"] != "comped"
        actions.append(Form(IconAction(KEY_SVG if comp else X_SVG, "Give paid access" if comp else "Take paid access away",
                                       confirm=f"Give {m['email']} paid access for free? It lasts until you take it "
                                               "away - no end date, no payment." if comp else
                                       f"Take paid access away from {m['email']}? They stay a free member."),
                            Input(type="hidden", name="on", value="1" if comp else ""),
                            action=f"/admin/members/{m['id']}/comp", method="post", cls="contents"))
    actions.append(Form(IconAction(TRASH_SVG, "Remove", danger=True,
                                   confirm=f"Remove {m['email']}? They're signed out, and members-only posts are "
                                           "closed to them. Their newsletter subscription stays."),
                        action=f"/admin/members/{m['id']}/remove", method="post", cls="contents"))
    return Li(Div(
        RowCheck("members-bulk", "ids", m["id"], m["email"]),
        Div(Div(Strong(m["email"], cls="break-all"), " ", _status_badge(m),
                Span("Newsletter", cls="badge badge-sm badge-outline ml-1") if subscribed else None),
            Div(" · ".join(x for x in (m["name"], _plan_line(m, relative),
                                       f"joined {format_date(m['created_at'], relative)}",
                                       f"last seen {format_date(m['last_seen_at'], relative)}" if m["last_seen_at"]
                                       else "") if x), cls="text-xs text-base-content/50 mt-0.5"),
            cls="min-w-0 flex-1 text-sm"),
        RowActions(*actions, id=f"member-{m['id']}"),
        cls="list-col-grow flex justify-between items-center gap-3"
    ), cls=f"list-row {TICK_ROW_CLS}", **TICK_ROW)


MEMBER_SORTS = [("newest", "Newest"), ("oldest", "Oldest"), ("name", "Name A-Z"), ("email", "Email A-Z")]


@ar.get("/admin/members")
def members_page(session, q: str = "", status: str = "", page: int = 1, sort: str = "newest"):
    from soloblog.ui import (EmptyState, PageHeader, Pagination, rows_per_page, SearchField, Tabs, TABS_CLS, FormField,
                             SettingsPanel, FilterSelect, ListToolbar, ListHeader, list_summary, OffNotice,
                             BulkButton)
    s = settings.get_all()
    paying = pay.ready(s) or members.counts()["paying"]
    filters = FILTERS if paying else FILTERS[:3]
    status = status if status in dict(filters) else ""
    sort = sort if sort in dict(MEMBER_SORTS) else "newest"
    q = q.strip()
    per = rows_per_page(MEMBERS_PER_PAGE)
    rows, matched = members.search(q, status, max(page, 1), per, sort)
    pages = max(1, -(-matched // per))
    relative = s.get("relative_dates") == "1"
    subscribed = {r["email"].lower() for r in newsletter.confirmed()}
    n = members.counts()
    revenue = pay.monthly_revenue()
    tabs = Tabs(*[A(label, href=f"/admin/members?status={key}&q={quote(q)}&sort={sort}",
                    cls=f"tab tab-sm whitespace-nowrap shrink-0 {'tab-active font-semibold' if key == status else ''}")
                  for key, label in filters], id="member-tabs", cls=f"{TABS_CLS} mb-3")
    add = SettingsPanel(
        "Add a member",
        Form(
            Div(FormField("Email", Input(type="email", name="email", required=True, maxlength="254",
                                         cls="input input-sm w-full")),
                FormField("Name", Input(name="name", maxlength="100", cls="input input-sm w-full")),
                cls="grid grid-cols-1 sm:grid-cols-2 gap-3"),
            Label(Input(type="checkbox", name="comp", value="1", cls="checkbox checkbox-sm"),
                  Span("Give them paid access - free, until you take it away", cls="text-sm"),
                  cls="flex items-center gap-2 cursor-pointer mt-3"),
            P("They're not emailed: they sign in with this address whenever they like.",
              cls="text-xs text-base-content/50 mt-1"),
            P("Moving from Ghost or another site? Import its members export (CSV) above - anyone already here "
              "is skipped. They come in free, or with paid access if they had it for free there; a paid plan "
              "elsewhere stays there.", cls="text-xs text-base-content/50 mt-1"),
            Div(Button("Add", type="submit", cls="btn btn-sm"), cls="flex justify-end mt-2"),
            action="/admin/members/add", method="post"),
        open_=False, key="members-add")
    body = Ul(*[MemberRow(m, m["email"].lower() in subscribed, relative) for m in rows], cls="list") if rows else \
        EmptyState(f"Nothing matches “{q}”." if q else "None of these yet." if status
                   else "No members yet. Add one above, or use Import to bring a list.", "👥")
    from soloblog.ui import UPLOAD_SVG
    keep = f"status={status}&q={quote(q)}&sort={sort}"
    return Layout(
        # Import as on the Newsletter: pick a file, it goes. Export is
        # ticking, as on Posts
        PageHeader("Members", Div(
            Form(Label(UPLOAD_SVG, Span("Import", cls="ml-1 hidden sm:inline", aria_hidden="true"),
                       Span("Import members", cls="sr-only"),
                       Input(type="file", name="csv", accept=".csv,text/csv", required=True, aria_label="CSV file",
                             cls="hidden", data_autosubmit=True),
                       data_tip="Import",
                       cls="btn btn-sm cursor-pointer tooltip tooltip-bottom sm:before:hidden sm:after:hidden"),
                 action="/admin/members/import", method="post", enctype="multipart/form-data"),
            cls="flex items-center gap-2")),
        None if members.enabled(s) else OffNotice("The members area is off, so nobody can join or sign in",
                                                  "/admin/settings?tab=members"),
        Div(*[Div(Div(label, cls="stat-title"), Div(value, cls="stat-value text-2xl tabular-nums"), cls="stat")
              for label, value in (("Members", f"{n['all']:,}"), ("Paid", f"{n['paid']:,}"),
                                   ("New this month", f"{n['new']:,}"),
                                   ("Monthly revenue", " + ".join(pay.money(a, c) for c, a in revenue.items()))
                                   if revenue else (None, None)) if label],
            cls="stats stats-vertical sm:stats-horizontal w-full bg-base-100 border-[length:var(--border)] "
                "border-base-300 mb-4"),
        Div(add, cls="mb-4"),
        tabs,
        ListToolbar([SearchField(q, "Search by email or name…", "/admin/members",
                                 {k: v for k, v in (("status", status), ("sort", sort)) if v}),
                     FilterSelect("Sort", "sort", MEMBER_SORTS, sort,
                                  f"/admin/members?status={status}&q={quote(q)}&sort=")]),
        ListHeader(list_summary(matched, "member", q), clear=f"/admin/members?status={status}" if q else None,
                   form_id="members-bulk" if rows else None, action="/admin/members/bulk",
                   return_to=f"/admin/members?{keep}&page={page}", total=matched,
                   scope={"in_status": status, "in_q": q},
                   buttons=[BulkButton("Export", "export", download=True),
                            BulkButton("Remove", "remove", danger=True,
                                       confirm="Remove the selected members? They're signed out, and members-only "
                                               "posts are closed to them. Their newsletter subscriptions stay.",
                                       confirm_all="Remove all {n} members? They're signed out, and members-only "
                                                   "posts are closed to them. Their newsletter subscriptions "
                                                   "stay.")]),
        body,
        Pagination(min(page, pages), pages, f"/admin/members?status={status}&q={quote(q)}&sort={sort}",
                   labels=("« Prev", "Next »"), per_page=per, total=matched),
        settings=s, logged_in=True, pinned_tree=posts.list_pinned_tree(), admin_page=True, live=True
    )


def _back(text, kind="success"):
    from soloblog.routes.admin_settings import _toast_redirect
    return _toast_redirect("/admin/members", text, kind)


@ar.post("/admin/members/add")
def add_member(session, email: str = "", name: str = "", comp: bool = False):
    clean = mail.clean_email(email)
    if not clean:
        return _back("That doesn't look like an email address", "error")
    if members.by_email(clean):
        return _back(f"{clean} is already a member", "error")
    members.add(clean, name, "comped" if comp else "free")
    return _back(f"Added {clean}")


@ar.post("/admin/members/{member_id}/comp")
def comp_member(session, member_id: int, on: bool = False):
    m = members.get(member_id)
    if not m:
        return _back("That member is gone", "error")
    if m["status"] == "paid" and m["stripe_subscription_id"]:
        return _back("They pay through Stripe - change their plan there", "error")
    members.update(member_id, status="comped" if on else "free")
    return _back(f"{m['email']} has paid access now" if on else f"{m['email']} is a free member now")


@ar.post("/admin/members/{member_id}/remove")
def remove_member(session, member_id: int):
    m = members.get(member_id)
    if not m:
        return _back("That member is gone", "error")
    if _live_plan(m):
        return _back("They have a live plan - end it first, so they're not charged again", "error")
    members.delete(member_id)
    return _back(f"Removed {m['email']}")


@ar.post("/admin/members/{member_id}/cancel")
def cancel_member_plan(session, member_id: int):
    if config.DEMO_MODE:
        from soloblog.demo import BLOCKED_MESSAGE
        return _back(BLOCKED_MESSAGE, "error")
    m = members.get(member_id)
    if not m or not m["stripe_subscription_id"]:
        return _back("They have no plan to cancel", "error")
    try:
        pay.cancel_at_period_end(m)
    except pay.StripeError as e:
        return _back(f"Stripe said: {e}", "error")
    return _back(f"{m['email']}'s plan ends at the end of what they've paid for")


@ar.post("/admin/members/import")
async def import_members(session, request):
    file = (await request.form()).get("csv")
    data = await file.read(5_000_001) if file and getattr(file, "filename", "") else b""
    if not data or len(data) > 5_000_000:
        return _back("Choose a CSV file under 5 MB", "error")
    added, skipped = members.import_csv(data.decode("utf-8", errors="replace"))
    return _back(f"Imported {added}" + (f" · skipped {skipped}" if skipped else ""))


def _live_plan(m):
    """Paying through Stripe and not ending - removing them would leave
    them being charged."""
    return bool(m["stripe_subscription_id"]) and m["subscription_status"] in members.PAID_STATES \
        and not m["cancel_at_period_end"]


@ar.post("/admin/members/bulk")
def bulk_members(session, action: str = "", ids: list[int] = None, return_to: str = "/admin/members",
                 all_matching: str = "", in_status: str = "", in_q: str = ""):
    from soloblog.guards import is_local_path, status_redirect
    target = return_to if is_local_path(return_to) else "/admin/members"
    if all_matching == "1":
        # every page the tab and search match, rebuilt here
        rows = members.search(in_q, in_status if in_status in dict(FILTERS) else "", 1, 10 ** 6)[0]
    else:
        rows = [m for m in (members.get(i) for i in (ids or []) if i) if m]
    if not rows or action not in ("export", "remove"):
        return status_redirect(target, "Select some members first", "error")
    if action == "export":
        return Response(members.export_csv([m["id"] for m in rows]), media_type="text/csv",
                        headers={"Content-Disposition": 'attachment; filename="members.csv"',
                                 "Cache-Control": "private, no-store"})
    paying = [m for m in rows if _live_plan(m)]
    for m in rows:
        if not _live_plan(m):
            members.delete(m["id"])
    n = len(rows) - len(paying)
    said = f"Removed {n} member{'s' if n != 1 else ''}"
    if paying:
        said += f" · {len(paying)} with a live plan kept - end it first"
    return status_redirect(target, said, "success" if n else "error")
