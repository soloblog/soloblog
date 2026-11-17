import threading
from soloblog.tz import utcnow
from urllib.parse import quote

from fasthtml.common import *

from soloblog import auth
from soloblog import captcha
from soloblog import i18n
from soloblog import members
from soloblog import newsletter
from soloblog import posts
from soloblog import ratelimit
from soloblog import settings
from soloblog.db import get_db
from soloblog.render import format_date
from soloblog.ui import IconAction
from soloblog.ui import RowActions
from soloblog.ui import (Layout, PageHeader, EmptyState, ErrorPage, Pagination, rows_per_page, SearchField, FilterSelect,
                         ListToolbar, ListHeader, list_summary, OffNotice, SetUpFirst, EMAIL_SETUP, TRASH_SVG, SEND_SVG,
                         UPLOAD_SVG, BulkButton, RowCheck, TICK_ROW, TICK_ROW_CLS)
from soloblog.guards import is_local_path, status_redirect
from soloblog.seo import page_meta

ar = APIRouter()


def _off(session):
    return FtResponse(ErrorPage(404, settings.get_all(), auth.is_logged_in(session), posts.list_pinned_tree()),
                      status_code=404)


def _notice(title, text, session):
    return Layout(Div(Div(H1(title, cls="text-xl font-bold"), P(text, cls="text-sm text-base-content/70"),
                          A(i18n.t("Back to the blog"), href="/", cls="link text-sm mt-2"), cls="card-body p-6"),
                      cls="card card-border bg-base-100 max-w-md mx-auto"),
                  settings=settings.get_all(), logged_in=auth.is_logged_in(session),
                  pinned_tree=posts.list_pinned_tree())


@ar.get("/newsletter")
def newsletter_page(session, hdrs):
    s = settings.get_all()
    box = newsletter.Box(s, page=True)
    if not box and members.current():
        return RedirectResponse("/account", status_code=303)  # a member already getting it
    if not box:
        return _off(session)
    page_meta(hdrs, s.get("newsletter_title") or i18n.t("Newsletter"),
              s.get("newsletter_intro") or i18n.t("New posts from {site} by email.", site=s["site_title"]), "/newsletter")
    return Layout(box, settings=s, logged_in=auth.is_logged_in(session),
                  pinned_tree=posts.list_pinned_tree())


@ar.post("/newsletter/subscribe")
def subscribe(req, email: str = "", website: str = "", captcha_token: str = ""):
    s = settings.get_all()

    def status(message, ok=True):
        return Span(message, id="newsletter-status", data_status_slot=True, role="status",
                    cls=f"text-xs mt-2 block {'text-success' if ok else 'text-error'}")
    # the same answer whether or not the address was already on the list
    done = status(i18n.t("Check your email to confirm"))
    if newsletter.mode(s) != "builtin":
        return status(i18n.t("The newsletter is turned off"), False)
    if website.strip():
        return done  # honeypot
    if not newsletter.EMAIL_RE.match(email.strip()):
        return status(i18n.t("That doesn't look like an email address"), False)
    if not captcha.passes(s, captcha_token, ratelimit.client_ip(req)):
        return status(i18n.t("Please complete the spam check"), False)
    if not ratelimit.hit(f"ip:{ratelimit.client_ip(req)}", "subscribe", limit=5, window_minutes=60):
        return status(i18n.t("Too many tries - try again later"), False)
    token = newsletter.subscribe(email)
    if token:
        threading.Thread(target=newsletter.send_confirm, args=(email.strip(), token, s), daemon=True).start()
    return done


@ar.get("/newsletter/confirm/{token}")
def confirm(session, hdrs, token: str):
    page_meta(hdrs, i18n.t("Newsletter"), path="/newsletter/confirm")
    if newsletter.confirm(token):
        return _notice(i18n.t("You're subscribed"),
                       i18n.t("New posts from {site} will arrive by email.", site=settings.get("site_title")), session)
    return _notice(i18n.t("That link has expired"), i18n.t("Subscribe again from the blog to get a new one."), session)


@ar.get("/newsletter/unsubscribe/{token}")
def unsubscribe_page(session, hdrs, token: str):
    """Asks first - a link scanner opening it shouldn't unsubscribe anyone."""
    page_meta(hdrs, i18n.t("Unsubscribe"), path="/newsletter/unsubscribe")
    return Layout(Div(Div(
        H1(i18n.t("Unsubscribe?"), cls="text-xl font-bold"),
        P(i18n.t("You won't get new posts from {site} by email any more.", site=settings.get("site_title")),
          cls="text-sm text-base-content/70"),
        Form(Button(i18n.t("Unsubscribe"), type="submit", cls="btn btn-primary btn-sm"),
             action=f"/newsletter/unsubscribe/{token}", method="post", cls="mt-2"),
        cls="card-body p-6"), cls="card card-border bg-base-100 max-w-md mx-auto"),
        settings=settings.get_all(), logged_in=auth.is_logged_in(session), pinned_tree=posts.list_pinned_tree())


@ar.post("/newsletter/unsubscribe/{token}")
def unsubscribe(session, token: str):
    # also what a mail app's own one-click "Unsubscribe" posts to (List-Unsubscribe-Post)
    newsletter.unsubscribe(token)
    return _notice(i18n.t("You're unsubscribed"),
                   i18n.t("No more emails will be sent. You can subscribe again any time."), session)


# ---- Admin > Subscribers

def SubscriberRow(sub, relative, member=None):
    """Laid out as a member's row is (members_routes.MemberRow): the address
    and what it is, then a line of when. member - the same address as a
    member: their name, and Member or Paid member, as a member's row says
    Newsletter."""
    if sub["unsubscribed_at"]:
        state = Span("Unsubscribed", cls="badge badge-sm badge-ghost")
    elif not sub["confirmed_at"]:
        state = Span("Not confirmed", cls="badge badge-sm badge-warning")
    else:
        state = None
    paid = member and (member["status"] == "comped" or (member["status"] == "paid"
                                                        and member["subscription_status"] in members.PAID_STATES))
    # when they signed up - confirmed, or still to - and when they left
    when = [f"subscribed {format_date(sub['confirmed_at'] or sub['created_at'], relative)}",
            f"unsubscribed {format_date(sub['unsubscribed_at'], relative)}" if sub["unsubscribed_at"] else ""]
    return Li(Div(
        RowCheck("subscribers-bulk", "ids", sub["id"], sub["email"]),
        Div(Div(Strong(sub["email"], cls="break-all"), " ", state,
                Span("Paid member" if paid else "Member", cls="badge badge-sm badge-outline ml-1" if state
                     else "badge badge-sm badge-outline") if member else None),
            Div(" · ".join(x for x in (member["name"] if member else "", *when) if x),
                cls="text-xs text-base-content/50 mt-0.5"),
            cls="min-w-0 flex-1 text-sm"),
        RowActions(Form(Input(type="hidden", name="subscriber_id", value=sub["id"]),
                        IconAction(TRASH_SVG, "Remove", danger=True,
                                   confirm=f"Remove {sub['email']}? They won't get any more emails."),
                        action="/admin/newsletter/remove", method="post", cls="contents"),
                   id=f"subscriber-acts-{sub['id']}"),
        cls="list-col-grow flex justify-between items-center gap-3"
    ), cls=f"list-row {TICK_ROW_CLS}", **TICK_ROW)


SUBSCRIBERS_PER_PAGE = 50
SUBSCRIBER_STATES = [("", "All"), ("confirmed", "Confirmed"), ("unconfirmed", "Not confirmed"),
                     ("unsubscribed", "Unsubscribed")]
SUBSCRIBER_SORTS = [("newest", "Newest"), ("oldest", "Oldest"), ("email", "Email A-Z")]


def _held_title(e):
    if len(e["slugs"]) > 1:
        return "Your digest"
    row = posts.get_post(e["slugs"][0])
    return f"“{row['title'] if row else e['slugs'][0]}”"


@ar.get("/admin/newsletter")
def subscribers_page(session, page: int = 1, q: str = "", state: str = "", sort: str = "newest"):
    s = settings.get_all()
    q = q.strip()
    state = state if state in newsletter.STATES else ""
    sort = sort if sort in newsletter.SORTS else "newest"
    per = rows_per_page(SUBSCRIBERS_PER_PAGE)
    rows, matched = newsletter.list_page(max(1, page), per, q, state, sort)
    total_pages = max(1, -(-matched // per))
    relative = s.get("relative_dates") == "1"
    total = newsletter.count()
    recent = [p for p in posts.list_all_published() if not posts.is_page(p)][:20]
    sent = {r["slug"] for r in get_db().execute("SELECT slug FROM published_log WHERE channel='newsletter' "
                                                 "AND content_hash != ?", (newsletter.SKIP,))}
    send_form = Form(
        Select(*[Option(("✓ " if p["slug"] in sent else "") + p["title"], value=p["slug"]) for p in recent],
               name="slug", aria_label="Post to send", cls="select select-sm join-item flex-1 min-w-0"),
        # how it'll look, in your own inbox first
        Button("Send me a test", type="submit", formaction="/admin/newsletter/test", cls="btn btn-sm join-item")
        if s.get("admin_email") else None,
        Button(SEND_SVG, Span(f"Send to {total}", cls="ml-1"), type="button", cls="btn btn-sm btn-primary join-item",
               data_confirm=f"Email this post to {total} subscriber{'s' if total != 1 else ''} now?")
        if total else None,
        action="/admin/newsletter/send", method="post", cls="join w-full sm:w-auto"
    ) if recent and (total or s.get("admin_email")) and newsletter.mode(s) == "builtin" else None
    chosen = s.get("newsletter_mode") or ""
    if newsletter.mode(s) == "builtin":
        note = None
    elif chosen == "builtin":
        note = SetUpFirst("email", EMAIL_SETUP)
    elif chosen in newsletter.SERVICES and newsletter.mode(s):
        note = OffNotice(f"Sign-ups go to {newsletter.SERVICES[chosen][0]}, so they're listed there",
                         "/admin/settings?tab=newsletter", "Change it")
    else:
        note = OffNotice("The newsletter is off, so nobody can subscribe", "/admin/settings?tab=newsletter")
    filtered = q or state
    # who among them is a member - one query for the page, not one a row
    marks = ",".join("?" * len(rows))
    known = {m["email"].lower(): m for m in get_db().execute(
        f"SELECT * FROM members WHERE lower(email) IN ({marks})", [r["email"].lower() for r in rows])} if rows else {}  # noqa: S608 - only ? placeholders are added
    body = Ul(*[SubscriberRow(r, relative, known.get(r["email"].lower())) for r in rows],
              cls="list") if rows else EmptyState(
        f"Nothing matches “{q}”." if q else "None of these yet." if state
        else "No subscribers yet. Readers who sign up show here, or use Import to bring a list.", "📬")
    keep = f"q={quote(q)}&state={state}&sort={sort}"
    return Layout(
        # Import where every list page keeps its actions, the way Media's
        # Upload works: pick a file, it goes. Export is ticking, as on Posts
        PageHeader("Newsletter", Div(
            # just their icons on a narrow phone, where the words pushed past the edge
            Form(Label(UPLOAD_SVG, Span("Import", cls="ml-1 hidden sm:inline", aria_hidden="true"),
                       Span("Import subscribers", cls="sr-only"),
                       Input(type="file", name="csv", accept=".csv,text/csv", required=True, aria_label="CSV file",
                             cls="hidden", data_autosubmit=True),
                       data_tip="Import",
                       cls="btn btn-sm cursor-pointer tooltip tooltip-bottom sm:before:hidden sm:after:hidden"),
                 action="/admin/newsletter/import", method="post", enctype="multipart/form-data"),
            cls="flex items-center gap-2")),
        note,
        *[P(_held_title(e), ": ", newsletter.held_note(e), cls="text-xs text-base-content/70 mb-2")
          for e in newsletter.held()],
        Div(send_form, cls="flex justify-end mb-1") if send_form else None,
        P("Moving from Substack, Buttondown, Mailchimp or Kit? Import their subscriber export (CSV) - they come "
          "in confirmed, and anyone already here is skipped.", cls="text-xs text-base-content/50 mb-4"),
        P("✓ marks a post that's already been sent. ",
          A("Send new posts by themselves", href="/admin/settings?tab=newsletter", cls="link")
          if not (newsletter.sending(s) or newsletter.digest(s)) else None,
          cls="text-xs text-base-content/50 mb-4") if send_form else None,
        ListToolbar([SearchField(q, "Search by email…", "/admin/newsletter",
                                 {k: v for k, v in (("state", state), ("sort", sort)) if v}),
                     FilterSelect("Status", "state", SUBSCRIBER_STATES, state,
                                  f"/admin/newsletter?q={quote(q)}&sort={sort}&state="),
                     FilterSelect("Sort", "sort", SUBSCRIBER_SORTS, sort,
                                  f"/admin/newsletter?q={quote(q)}&state={state}&sort=")],
                    filtered=bool(state or sort != "newest")),
        ListHeader(list_summary(matched, "subscriber", q, dict(SUBSCRIBER_STATES)[state].lower() if state else ""),
                   clear="/admin/newsletter" if filtered else None,
                   form_id="subscribers-bulk" if rows else None, action="/admin/newsletter/bulk",
                   return_to=f"/admin/newsletter?{keep}&page={page}", total=matched,
                   scope={"in_q": q, "in_state": state},
                   buttons=[BulkButton("Export", "export", download=True),
                            BulkButton("Remove", "remove", danger=True,
                                       confirm="Remove the selected subscribers? They won't get any more emails.",
                                       confirm_all="Remove all {n} subscribers? They won't get any more "
                                                   "emails.")]),
        body,
        Pagination(min(page, total_pages), total_pages, f"/admin/newsletter?{keep}",
                   labels=("« Prev", "Next »"), per_page=per, total=matched),
        settings=s, logged_in=True, pinned_tree=posts.list_pinned_tree(), admin_page=True, live=True
    )


@ar.post("/admin/newsletter/remove")
def remove_subscriber(session, subscriber_id: int):
    newsletter.remove(subscriber_id)
    return RedirectResponse("/admin/newsletter?toast=Removed&toast_type=success", status_code=303)


@ar.post("/admin/newsletter/test")
def send_test(session, slug: str = ""):
    s = settings.get_all()
    row = posts.get_post(slug)
    to = s.get("admin_email")
    if not row or not to or newsletter.mode(s) != "builtin":
        return status_redirect("/admin/newsletter", "Choose a post first", "error")
    if not newsletter.send_test(row, s, to):
        return status_redirect("/admin/newsletter", "Couldn't send it - Site health says why", "error")
    return status_redirect("/admin/newsletter", f"Test sent to {to}")


@ar.post("/admin/newsletter/send")
def send_now(session, slug: str = ""):
    row = posts.get_post(slug)
    if not row or not posts.is_live(row) or newsletter.mode(settings.get_all()) != "builtin":
        return RedirectResponse("/admin/newsletter", status_code=303)
    from soloblog import publishing
    # remembered as sent, so the automatic sending doesn't send it again
    get_db().execute("INSERT INTO published_log (slug, channel, content_hash, done_at) VALUES (?, 'newsletter', ?, ?) "
                     "ON CONFLICT(slug, channel) DO UPDATE SET done_at=excluded.done_at",
                     (slug, publishing._hash(row), utcnow().isoformat(timespec="seconds")))
    get_db().commit()
    threading.Thread(target=newsletter.send_post, args=(row,), daemon=True).start()
    return RedirectResponse("/admin/newsletter?toast=Sending&toast_type=success", status_code=303)


@ar.post("/admin/newsletter/import")
async def import_subscribers(session, request):
    file = (await request.form()).get("csv")
    data = await file.read(5_000_001) if file and getattr(file, "filename", "") else b""
    if not data or len(data) > 5_000_000:
        return RedirectResponse("/admin/newsletter?toast=Choose+a+CSV+file+under+5+MB&toast_type=error",
                                status_code=303)
    added, skipped = newsletter.import_csv(data.decode("utf-8", errors="replace"))
    note = f"Imported {added}" + (f" · skipped {skipped}" if skipped else "")
    return RedirectResponse(f"/admin/newsletter?toast={note.replace(' ', '+')}&toast_type=success", status_code=303)


@ar.post("/admin/newsletter/bulk")
def bulk_subscribers(session, action: str = "", ids: list[int] = None, return_to: str = "/admin/newsletter",
                     all_matching: str = "", in_q: str = "", in_state: str = ""):
    target = return_to if is_local_path(return_to) else "/admin/newsletter"
    if all_matching == "1":
        # every page the list's search and Status match, rebuilt here
        rows = newsletter.list_page(1, 10 ** 6, in_q, in_state if in_state in newsletter.STATES else "")[0]
    else:
        rows = newsletter.by_ids(i for i in (ids or []) if i)
    if not rows or action not in ("export", "remove"):
        return status_redirect(target, "Tick some subscribers first", "error")
    if action == "export":
        from soloblog.backup import csv_download
        return csv_download("subscribers.csv", ["email", "subscribed", "confirmed", "unsubscribed"],
                            [(r["email"], r["created_at"], r["confirmed_at"], r["unsubscribed_at"]) for r in rows])
    for r in rows:
        newsletter.remove(r["id"])
    return status_redirect(target, f"Removed {len(rows)} subscriber{'s' if len(rows) != 1 else ''}")
