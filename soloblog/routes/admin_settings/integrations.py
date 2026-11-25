"""API keys, webhooks and the email test: panels that change by themselves, with their routes."""
from fasthtml.common import *
from soloblog import settings
from soloblog import ratelimit
from soloblog import mail
from soloblog.render import format_date, format_when
from soloblog.ui import PLUS_SVG
from soloblog.ui import EmailFields, SEND_SVG
from soloblog.ui import IconAction
from soloblog.ui import RowActions
from soloblog.ui import (
    FIELD_GAP, FormField, ToggleField, RadioGroupField, SettingsPanel, KEY_SVG, COPY_SVG, TRASH_SVG,
)
from soloblog.routes.admin_settings.base import ar
from soloblog.routes.admin_settings.saves import SECRETS_FIELDS, _tell_old_address, _your_email, clean_form


def ApiKeysBody(new_key="", error=""):
    """Settings > Security > API keys, swapped in place: the keys there
    are, the form for a new one - and a new key, the once it's shown."""
    from soloblog import apikeys
    swap = dict(hx_target="#api-keys-body", hx_swap="innerHTML")
    choice = settings.get("apps_publish")
    held = {"publish": {"none": "Everything it posts arrives as a draft",
                        "apps": "AI assistants using it write drafts"}.get(choice)}
    rows = [
        Div(
            Div(P(k["name"], " ", Span(apikeys.SCOPE_LABELS[k["scope"]],
                                       cls="badge badge-xs badge-outline ml-1 whitespace-nowrap"),
                  Span("Ghost apps", cls="badge badge-xs badge-outline ml-1 whitespace-nowrap")
                  if k["kind"] == "signed" else None, cls="text-sm"),
                # a Publish key the site keeps to drafts says so, on its own row
                # (a Ghost app's key is for Ghost apps only - no assistant uses it)
                P(held[k["scope"]], cls="text-xs text-base-content/70")
                if held.get(k["scope"]) and (k["kind"] != "signed" or choice == "none") else None,
                P(Span(k["prefix"] + "…", cls="font-mono"), f" · made {format_date(k['created_at'])}" +
                  (f" · last used {format_when(k['last_used_at'])}" +
                   (f" by {apikeys.VIA[k['last_used_via']]}" if k["last_used_via"] in apikeys.VIA else "")
                   if k["last_used_at"] else " · not used yet"),
                  cls="text-xs text-base-content/50")),
            RowActions(Form(IconAction(TRASH_SVG, "Revoke", danger=True,
                                       confirm=f"Revoke the key “{k['name']}”? Anything using it stops working at once."),
                            hx_post=f"/admin/apikeys/{k['id']}/revoke", **swap, cls="contents"),
                       id=f"apikey-acts-{k['id']}"),
            cls="flex items-center justify-between gap-3 py-2 border-b-[length:var(--border)] border-base-300 "
                "last:border-0"
        ) for k in apikeys.listed()
    ]
    return Div(
        Div(P("Your new key - copy it now. For your safety it isn't shown again.",
              cls="text-sm font-medium"),
            Code(new_key, cls="block font-mono text-sm bg-base-100 rounded-box px-3 py-2 break-all select-all my-2"),
            Button(COPY_SVG, Span("Copy", cls="ml-1"), type="button", cls="btn btn-sm",
                   data_copy=new_key, data_copied="Copied"),
            role="status", cls="rounded-box border-[length:var(--border)] border-success bg-base-200 p-3 mb-3")
        if new_key else None,
        P(error, role="alert", cls="text-sm text-error mb-2") if error else None,
        Div(*rows, cls="mb-3") if rows else None,
        Form(RadioGroupField("Who may publish with a Publish key", "apps_publish", list(apikeys.PUBLISH_CHOICES.items()),
                             choice, help="Whatever's held back arrives as a draft, for you to publish."),
             hx_post="/admin/apikeys/publishing", hx_trigger="change", **swap, cls=FIELD_GAP),
        Form(
            FormField("Name", Input(name="name", required=True, maxlength="60", placeholder="e.g. iA Writer, My laptop",
                                    cls="input input-sm w-full"),
                      help="So you can tell your keys apart later.", cls=FIELD_GAP),
            RadioGroupField("What it can do", "scope",
                            [(k, f"{apikeys.SCOPE_LABELS[k]} - {apikeys.SCOPE_HELP[k]}") for k in apikeys.SCOPES],
                            "draft", help="Give each app only what it needs.", cls=FIELD_GAP),
            RadioGroupField("For", "kind",
                            [("bearer", "Most apps, scripts and AI assistants"),
                             ("signed", "Apps that publish to Ghost - Ulysses, iA Writer")],
                            "bearer", help="In Ulysses and iA Writer, paste it as the \"Admin API key\"."),
            Div(Button(KEY_SVG, Span("Make a key", cls="ml-1"), type="submit", cls="btn btn-sm"),
                cls="flex justify-end mt-3"),
            hx_post="/admin/apikeys/new", **swap
        )
    )


def ApiKeysPanel():
    return SettingsPanel(
        "API keys",
        P("Let an app, a script or an AI assistant work on your site. ",
          A("How it works", href="/admin/help?tab=api", cls="link"), ".",
          cls="text-sm text-base-content/70 mb-3"),
        Div(ApiKeysBody(), id="api-keys-body"),
        key="integrations-apikeys", open_=False
    )


@ar.post("/admin/apikeys/new")
def apikey_new(session, request, name: str = "", scope: str = "draft", kind: str = "bearer"):
    from soloblog import apikeys
    if not name.strip():
        return ApiKeysBody(error="Give the key a name")
    return ApiKeysBody(new_key=apikeys.create_signed(name, scope) if kind == "signed" else apikeys.create(name, scope))


@ar.post("/admin/apikeys/publishing")
def apikey_publishing(session, request, apps_publish: str = ""):
    from soloblog import apikeys
    if apps_publish in apikeys.PUBLISH_CHOICES:
        settings.set_many({"apps_publish": apps_publish})
    return ApiKeysBody()


@ar.post("/admin/apikeys/{key_id}/revoke")
def apikey_revoke(session, request, key_id: int):
    from soloblog import apikeys
    apikeys.revoke(key_id)
    return ApiKeysBody()


def WebhooksBody(error="", tested=None):
    """Settings > Security > Webhooks, swapped in place."""
    from soloblog import webhooks
    swap = dict(hx_target="#webhooks-body", hx_swap="innerHTML")

    def last(h):
        if tested and tested[0] == h["id"]:
            ok = 200 <= tested[1] < 300
            return Span("Test sent - it answered " + str(tested[1]) if tested[1] else "Test couldn't reach it",
                        cls="text-success" if ok else "text-error")
        if not h["last_at"]:
            return "nothing sent yet"
        if 200 <= (h["last_status"] or 0) < 300:
            return f"last sent {format_date(h['last_at'])}"
        return Span(f"failed {format_date(h['last_at'])} - {h['last_error']}", cls="text-error")

    rows = [
        Div(
            Div(P(Span(h["url"], cls="font-mono break-all"), cls="text-sm"),
                P(", ".join(webhooks.EVENTS[e] for e in h["events"].split(",") if e in webhooks.EVENTS), " · ",
                  last(h), cls="text-xs text-base-content/60"),
                Details(Summary("Signing secret", cls="text-xs link link-hover w-fit"),
                        Div(Code(webhooks.secret_for(h["id"]), cls="font-mono text-xs break-all select-all"),
                            Button(COPY_SVG, Span("Copy", cls="ml-1"), type="button", cls="btn btn-sm",
                                   data_copy=webhooks.secret_for(h["id"]), data_copied="Copied"),
                            cls="flex flex-wrap items-center gap-2 mt-1")),
                cls="min-w-0 flex-1"),
            RowActions(Form(IconAction(SEND_SVG, "Send a test"),
                            hx_post=f"/admin/webhooks/{h['id']}/test", **swap, cls="contents"),
                       Form(IconAction(TRASH_SVG, "Remove", danger=True,
                                       confirm=f"Remove the webhook to {h['url']}? Nothing more is sent there."),
                            hx_post=f"/admin/webhooks/{h['id']}/remove", **swap, cls="contents"),
                       id=f"webhook-acts-{h['id']}"),
            cls="flex items-start justify-between gap-3 py-2 border-b-[length:var(--border)] border-base-300 "
                "last:border-0"
        ) for h in webhooks.listed()
    ]
    return Div(
        P(error, role="alert", cls="text-sm text-error mb-2") if error else None,
        Div(*rows, cls="mb-3") if rows else None,
        Form(
            FormField("URL", Input(name="url", type="url", required=True, placeholder="https://hooks.example.com/…",
                                       cls="input input-sm w-full font-mono"), cls=FIELD_GAP),
            Fieldset(Legend("Tell it when", cls="fieldset-legend"),
                     *[Label(Input(type="checkbox", name="events", value=k, checked=True, cls="checkbox checkbox-sm"),
                             Span(label, cls="text-sm"), cls="flex items-center gap-2 cursor-pointer")
                       for k, label in webhooks.EVENTS.items()], cls="fieldset p-0 gap-1"),
            Div(Button(PLUS_SVG, Span("Add", cls="ml-1"), type="submit", cls="btn btn-sm"), cls="flex justify-end mt-3"),
            hx_post="/admin/webhooks/add", **swap
        )
    )


def WebhooksPanel():
    return SettingsPanel(
        "Webhooks",
        P("Tell another service - Zapier, Make, n8n - when a post goes live or a comment arrives. ",
          A("What's sent", href="/admin/help?tab=api#webhooks", cls="link"), ".",
          cls="text-sm text-base-content/70 mb-3"),
        Div(WebhooksBody(), id="webhooks-body"),
        key="integrations-webhooks", open_=False
    )


@ar.post("/admin/webhooks/add")
def webhook_add(session, request, url: str = "", events: list[str] = None):
    from soloblog import webhooks
    return WebhooksBody(error=webhooks.add(url, events or []))


@ar.post("/admin/webhooks/{hook_id}/test")
def webhook_test(session, request, hook_id: int):
    from soloblog import webhooks
    hook = next((h for h in webhooks.listed() if h["id"] == hook_id), None)
    if not hook:
        return WebhooksBody()
    status = webhooks.deliver(dict(hook), "ping", {"message": "A test from your Soloblog site"}, retries=())
    return WebhooksBody(tested=(hook_id, status))


@ar.post("/admin/webhooks/{hook_id}/remove")
def webhook_remove(session, request, hook_id: int):
    from soloblog import webhooks
    webhooks.remove(hook_id)
    return WebhooksBody()


def YourEmailPanel(s):
    """Where password resets and sign-in alerts go - on the Email page,
    above how email is sent, saved with the page's own Save like any other
    setting (save_secrets checks the address typed twice, and the password
    when it changes)."""
    return SettingsPanel(
        "Admin email",
        Div(EmailFields("admin_email", s["admin_email"],
                        help=("Set on your host. " if settings.on_host("admin_email") else "")
                        + "For password resets, sign-in alerts and comment emails. Never shown on your site."),
            cls=FIELD_GAP),
        FormField("Password", Input(type="password", name="current_password", autocomplete="current-password",
                                    cls="input input-sm w-full"),
                  help="Only to change the email address", cls=FIELD_GAP),
        ToggleField("Email me when a new device signs in", "signin_alerts",
                    checked=(s["signin_alerts"] != "0"),
                    help="The first time a browser signs in."),
        key="email-admin"
    )


@ar.post("/admin/email/test")
async def send_test_email(request, session):
    """Settings > Email: an email to your own address, to see it arrives -
    the surest check that the address, and the email settings, are right.
    What's on screen is saved first, so it's what's tested."""
    form = await request.form()
    # only with the form's own list of fields - without it, every unsent field would read as empty
    saved = bool(form.get("declared_fields"))
    values = clean_form(form, SECRETS_FIELDS) if saved else {}
    problem, was = _your_email(request, form, values), settings.get("admin_email")
    saved = saved and not problem
    if saved:
        settings.set_declared(form.get("declared_fields"), values)
        _tell_old_address(was)
    to = settings.get("admin_email")
    # data-saved: the form's fields are now its saved values, whatever the email did (SAVE_STATUS_CLEAR_JS)
    status = lambda text, kind="": Span(text, id="email-test-status", data_status_slot=True, role="status",  # noqa: E731
                                         data_saved=saved or None,
                                         cls="text-xs flex-1 min-w-48 text-end " + ("text-error" if kind == "error" else "text-success"))
    if problem:
        return status(problem, "error")
    if not mail.can_send():
        return status("Choose how email is sent first", "error")
    if not ratelimit.hit(f"ip:{ratelimit.client_ip(request)}", "test-email", limit=5, window_minutes=15):
        return status("Too many tests. Try again in a few minutes", "error")
    if not mail.send_email(to, f"Test email from {settings.get('site_title')}",
                           f"Email from {settings.get('site_title')} is working.\n\n"
                           "This test was sent from Settings > Email. Password resets and "
                           "sign-in alerts will reach you at this address.\n"):
        return status("Couldn't send it: " + mail.explain(settings.get("mail_last_error")), "error")
    if mail.only_reaches_you():
        return status(f"Sent to {to} - but from resend.dev it reaches only you. Use an address at your own domain",
                      "error")
    return status(f"Sent to {to} - check your inbox")
