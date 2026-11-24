from urllib.parse import quote

from fasthtml.common import *

from soloblog import auth
from soloblog import captcha
from soloblog import config
from soloblog import comments
from soloblog import i18n
from soloblog import contact
from soloblog import formservices
from soloblog import mail
from soloblog import notify
from soloblog import posts
from soloblog import ratelimit
from soloblog import settings
from soloblog.render import format_date, embed_url
from soloblog.ui import IconAction, TITLE_CLS, Tabs, TABS_CLS
from soloblog.ui import RowActions
from soloblog.ui import (ListHeader, BulkButton, list_summary, ListToolbar, SearchField, FilterSelect, OffNotice, RowCheck, TICK_ROW, TICK_ROW_CLS, Layout, PageHeader, EmptyState, ErrorPage, FormField, Pagination, rows_per_page, FIELD_GAP, TRASH_SVG,
                REPLY_SVG, SEND_SVG, RESTORE_SVG, CHECK_SVG, MAIL_SVG)
from soloblog.guards import is_local_path, status_redirect, undo_url
from soloblog.seo import page_meta

ar = APIRouter()

PER_PAGE = 20


@ar.get("/contact")
def contact_page(session, hdrs):
    s = settings.get_all()
    logged_in = auth.is_logged_in(session)
    if s.get("contact_enabled") != "1":
        return FtResponse(ErrorPage(404, s, logged_in, posts.list_pinned_tree()), status_code=404)
    page_meta(hdrs, i18n.t("Contact"), i18n.t("Send {name} a message.", name=s['author_name'] or s['site_title']),
              "/contact")
    intro = s["contact_intro"]
    if s.get("contact_mode") == "embed" and embed_url(s["contact_form_url"]):
        intro = intro or i18n.t("Send me a message.")
    else:
        intro = intro or i18n.t("Send me a message - I'll reply by email.")
    return Layout(
        H1(i18n.t("Contact"), cls=f"{TITLE_CLS} mb-1"),
        P(intro, cls="text-sm text-base-content/70 mb-5"),
        *ContactForm(s),
        settings=s, logged_in=logged_in, pinned_tree=posts.list_pinned_tree()
    )


def ContactForm(s):
    """The contact form - the Contact page's, and a Contact form section's
    in any post (pages._render_contact). A form built on Tally,
    Typeform, Google Forms... is the same click-to-load card as in a post,
    so nothing loads from that service until the visitor asks for it."""
    hosted = embed_url(s["contact_form_url"]) if s.get("contact_mode") == "embed" else None
    if hosted:
        return (Div(NotStr(hosted), cls="prose max-w-none [&_:not(pre)>code]:wrap-anywhere"),)
    # the same card, fields and status-left/button-right row as the
    # comment form under every post
    return (
        Div(Div(
            Form(
                Div(
                    FormField(i18n.t("Name"), Input(name="name", required=True, maxlength="100", autocomplete="name",
                                            cls="input input-sm w-full remember-name-field")),
                    FormField(i18n.t("Email"), Input(name="email", type="email", required=True, maxlength="200",
                                             autocomplete="email", cls="input input-sm w-full")),
                    cls=f"grid grid-cols-1 sm:grid-cols-2 gap-2 {FIELD_GAP}"
                ),
                FormField(i18n.t("Message"), Textarea(name="body", required=True, rows="6", maxlength="5000",
                                              cls="textarea textarea-sm w-full")),
                # honeypot - invisible to a person, filled in by bots
                Input(name="website", cls="hidden", tabindex="-1", autocomplete="off"),
                captcha.Widget(s, cls="mt-3"),
                Div(
                    Span(id="contact-status", data_status_slot=True, role="status", cls="text-xs text-base-content/50"),
                    Button(SEND_SVG, Span(i18n.t("Send"), cls="ml-1"), type="submit", cls="btn btn-primary btn-sm ml-auto"),
                    cls="flex items-center gap-2 mt-3"
                ),
                hx_post="/contact", hx_target="#contact-status", hx_swap="outerHTML show:none focus-scroll:false",
                id="contact-form"
            ),
            cls="card-body p-5"
        ), cls="card card-border bg-base-100"),
        captcha.ApiScript(s),
    )


@ar.post("/contact")
def send_message(req, name: str = "", email: str = "", body: str = "", website: str = "",
                 captcha_token: str = ""):
    def status(message, ok=True):
        return Span(message, id="contact-status", data_status_slot=True, role="status",
                    cls=f"text-xs {'text-success' if ok else 'text-error'}")

    sent = status(i18n.t("Sent - thank you!"))
    if settings.get("contact_enabled") != "1":
        return status(i18n.t("The contact form is turned off."), False)
    if website.strip():
        return sent  # honeypot: look like it worked
    if not (name.strip() and "@" in email and body.strip()):
        return status(i18n.t("Please fill in every field."), False)
    if comments.is_blocked(settings.get("comment_blocklist"), name, email, body):
        return sent  # the same blocklist as comments - looks sent, goes nowhere
    if not captcha.passes(settings.get_all(), captcha_token, ratelimit.client_ip(req)):
        return status(i18n.t("Please complete the spam check"), False)
    if not ratelimit.hit(f"ip:{ratelimit.client_ip(req)}", "contact", limit=3, window_minutes=60):
        return status(i18n.t("Too many messages - try again later."), False)

    contact.add(name, email, body)
    subject = f"New message from {name.strip()[:100]} via {settings.get('site_title')}"
    formservices.forward(settings.get("contact_service"), settings.get("contact_service_id"),
                         name.strip(), email.strip(), body.strip(), subject)
    to = settings.get("contact_email")
    if to:
        # Reply answers the visitor, not the site's own address
        reply_to = mail.clean_email(email)
        mail.send_email(to, subject,
                        f"{name.strip()} <{email.strip()}> sent a message from your contact page:\n\n"
                        f"{body.strip()}\n\n"
                        + ("To answer, reply to this email.\n\n" if reply_to else "")
                        + f"All your messages:\n{config.BASE_URL}/admin/messages\n",
                        headers={"Reply-To": reply_to} if reply_to else None)
    notify.notify(settings.get("comment_webhook_url"), f"{name.strip()[:100]} sent a message: {body.strip()[:200]}\n"
                                                      f"Read it: {config.BASE_URL}/admin/messages")
    return sent


def MessageRow(m, tab="inbox"):
    # the same list-row shape as a comment in the moderation queue:
    # who and when, the message, and actions on the right
    def act(icon, label, path, **kw):
        return Form(Input(type="hidden", name="message_id", value=m["id"]), IconAction(icon, label, **kw),
                    action=path, method="post", cls="contents")
    if tab == "trash":
        actions = [act(RESTORE_SVG, "Restore", "/admin/messages/restore"),
                   act(TRASH_SVG, "Delete forever", "/admin/messages/delete-forever", danger=True,
                       confirm="Permanently delete this message? This can't be undone.")]
    else:
        actions = [IconAction(REPLY_SVG, "Reply", href=f"mailto:{m['email']}?subject=Re:%20your%20message"),
                   act(MAIL_SVG, "Mark as unread", "/admin/messages/unread") if m["is_read"] else
                   act(CHECK_SVG, "Mark as read", "/admin/messages/read"),
                   act(TRASH_SVG, "Move to trash", "/admin/messages/delete", danger=True,
                       confirm="Move this message to trash? You can restore it from Trash.")]
    when = f"Deleted {format_date(m['trashed_at'])}" if tab == "trash" else format_date(m["created_at"])
    unread = not m["is_read"] and tab != "trash"
    return Li(Div(
        RowCheck("messages-bulk", "ids", m["id"], f"message from {m['name']}", "mt-0.5"),
        Div(
            Div(Span(m["name"], cls="font-bold" if unread else "font-medium"),
                Span(f" <{m['email']}>", cls="text-xs text-base-content/50"),
                Span(f" · {when}", cls="text-xs text-base-content/50"),
                Span("New", cls="badge badge-xs badge-primary ml-2") if unread else None,
                cls="text-sm"),
            P(m["body"], cls=f"my-2 whitespace-pre-line {'font-medium' if unread else ''}"),
            cls="flex-1 min-w-0"
        ),
        RowActions(*actions, id=f"message-acts-{m['id']}"),
        cls="list-col-grow flex justify-between items-start gap-3"
    ), cls=f"list-row {TICK_ROW_CLS}", **TICK_ROW)


MESSAGE_SORTS = [("newest", "Newest"), ("oldest", "Oldest")]
MESSAGE_TABS = [("inbox", "Inbox"), ("trash", "Trash")]


@ar.get("/admin/messages")
def messages_page(session, page: int = 1, q: str = "", sort: str = "newest", tab: str = "inbox"):
    q = q.strip()
    sort = sort if sort in dict(MESSAGE_SORTS) else "newest"
    tab = tab if tab in dict(MESSAGE_TABS) else "inbox"
    trash = tab == "trash"
    per = rows_per_page(PER_PAGE)
    rows = contact.list_all(page, per, q, sort, trash)
    matched = contact.count(q, trash)
    total_pages = max(1, -(-matched // per))
    keep = f"tab={tab}&q={quote(q)}&sort={sort}"
    body = Ul(*[MessageRow(m, tab) for m in rows], cls="list") if rows else EmptyState(
        f"Nothing matches “{q}”." if q else ("Trash is empty." if trash else "No messages yet. What readers send from your contact form shows here."),
        "🗑️" if trash else "✉️")
    tabs = Tabs(*[A(label, href=f"/admin/messages?tab={key}",
                    cls=f"tab tab-sm {'tab-active font-semibold' if key == tab else ''}")
                  for key, label in MESSAGE_TABS], id="message-tabs", cls=f"{TABS_CLS} mb-4")
    empty = Form(
        Button(TRASH_SVG, Span("Empty trash", cls="ml-1"), type="button", cls="btn btn-sm text-error",
               data_confirm="Permanently delete everything in trash? This can't be undone."),
        action="/admin/messages/empty-trash", method="post") if trash and contact.count("", True) else None
    buttons = [BulkButton("Restore", "restore"),
               BulkButton("Delete", "delete", danger=True,
                          confirm="Permanently delete the selected messages? This can't be undone.",
                          confirm_all="Permanently delete all {n} messages in the trash? This can't be undone.")] \
        if trash else [BulkButton("Mark as read", "read"), BulkButton("Mark as unread", "unread"),
                       BulkButton("Export", "export", download=True),
                       BulkButton("Move to trash", "trash", danger=True)]
    return Layout(
        PageHeader("Contact messages"),
        None if settings.get("contact_enabled") == "1" else OffNotice(
            "The contact form is off, so nobody can write to you", "/admin/settings?tab=messages&panel=messages-contact"),
        tabs,
        ListToolbar([SearchField(q, "Search messages…", "/admin/messages", {"tab": tab, "sort": sort}),
                     FilterSelect("Sort", "sort", MESSAGE_SORTS, sort, f"/admin/messages?tab={tab}&q={quote(q)}&sort=")],
                    empty),
        ListHeader(list_summary(matched, "message", q), clear=f"/admin/messages?tab={tab}" if q else None,
                   form_id="messages-bulk" if rows else None,
                   action="/admin/messages/bulk", return_to=f"/admin/messages?{keep}&page={page}",
                   total=matched, scope={"in_tab": tab, "in_q": q}, buttons=buttons),
        body,
        Pagination(page, total_pages, f"/admin/messages?{keep}", labels=("« Prev", "Next »"), per_page=per,
                   total=matched),
        settings=settings.get_all(), logged_in=True, pinned_tree=posts.list_pinned_tree(), admin_page=True, live=True
    )


# what each tab's bulk bar offers - "all" is only ever done within one tab
MESSAGE_ACTIONS = {"inbox": ("read", "unread", "export", "trash"), "trash": ("restore", "delete")}


@ar.post("/admin/messages/bulk")
def bulk_messages(session, action: str = "", ids: list[int] = None, return_to: str = "/admin/messages",
                  all_matching: str = "", in_tab: str = "inbox", in_q: str = ""):
    target = return_to if is_local_path(return_to) else "/admin/messages"
    in_tab = in_tab if in_tab in MESSAGE_ACTIONS else "inbox"
    if all_matching == "1":
        ids = [m["id"] for m in contact.list_all(1, 10 ** 6, in_q, trash=in_tab == "trash")]
    else:
        ids = [i for i in (ids or []) if i]
    if action not in MESSAGE_ACTIONS[in_tab] or not ids:
        return status_redirect(target, "Select some messages first", "error")
    if action == "export":
        return Response(contact.export_csv(ids), media_type="text/csv",
                        headers={"Content-Disposition": 'attachment; filename="messages.csv"',
                                 "Cache-Control": "private, no-store"})
    do = {"read": contact.mark_read, "unread": lambda i: contact.mark_read(i, False),
          "trash": contact.move_to_trash, "restore": contact.restore, "delete": contact.delete}[action]
    for message_id in ids:
        do(message_id)
    n = f"{len(ids)} message{'s' if len(ids) != 1 else ''}"
    return status_redirect(target, {"read": f"Marked {n} as read", "unread": f"Marked {n} as unread",
                                    "trash": f"Moved {n} to trash",
                                    "restore": f"Restored {n}", "delete": f"Permanently deleted {n}"}[action])


def _back(return_to, tab="inbox"):
    return return_to if is_local_path(return_to) else f"/admin/messages?tab={tab}"


@ar.post("/admin/messages/read")
def read_message(session, message_id: int, return_to: str = ""):
    contact.mark_read(message_id)
    return status_redirect(_back(return_to), "Marked as read")


@ar.post("/admin/messages/unread")
def unread_message(session, message_id: int, return_to: str = ""):
    contact.mark_read(message_id, False)
    return status_redirect(_back(return_to), "Marked as unread")


@ar.post("/admin/messages/delete")
def delete_message(session, message_id: int, return_to: str = ""):
    contact.move_to_trash(message_id)
    target = _back(return_to)
    return status_redirect(target, "Moved to trash",
                           undo=undo_url("/admin/messages/restore", message_id=message_id, return_to=target))


@ar.post("/admin/messages/restore")
def restore_message(session, message_id: int, return_to: str = ""):
    contact.restore(message_id)
    return status_redirect(_back(return_to, "trash"), "Restored")


@ar.post("/admin/messages/delete-forever")
def delete_message_forever(session, message_id: int):
    contact.delete(message_id)
    return status_redirect("/admin/messages?tab=trash", "Permanently deleted")


@ar.post("/admin/messages/empty-trash")
def empty_message_trash(session):
    n = contact.empty_trash()
    return status_redirect("/admin/messages?tab=trash", f"Permanently deleted {n} message{'s' if n != 1 else ''}")
