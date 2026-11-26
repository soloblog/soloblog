"""Settings > Security: your password, two-step login, passkeys, the recovery key and where you're logged in."""
from urllib.parse import quote

from fasthtml.common import *

from soloblog import auth
from soloblog import config
from soloblog import settings
from soloblog import ratelimit
from soloblog import totp
from soloblog import passkeys
from soloblog.actions import on
from soloblog.render import format_date, format_when
from soloblog.ui import IconAction, STATUS_BESIDE, STATUS_ROW
from soloblog.ui import RowActions
from soloblog.ui import (FIELD_GAP, FormField, SettingsPanel,
                SaveStatus,
                DOWNLOAD_SVG, RESTORE_SVG, KEY_SVG, CHECK_SVG, X_SVG, COPY_SVG, TRASH_SVG)

from soloblog.routes.admin_settings import _toast_redirect

ar = APIRouter()


def _action_row(*buttons, status="", status_id="twofactor-status"):
    """Buttons right, their status just left of them - the SaveBar row
    shape, for a panel with its own actions instead of the tab's Save."""
    return Div(
        Span(status, id=status_id, role="status", cls=f"text-xs {STATUS_BESIDE}" + (" text-error" if status else "")),
        Div(*buttons, cls="flex items-center gap-2"),
        cls=f"{STATUS_ROW} mt-3"
    )


def _twofactor_swap(**kw):
    return dict(hx_target="#twofactor-body", hx_swap="innerHTML", **kw)


def TwoFactorBody(state=None, secret="", codes=None, error=""):
    """The two-factor panel's content, swapped in place as it moves
    between off -> setting up -> showing recovery codes -> on."""
    state = state or ("on" if totp.is_enabled() else "off")
    if state == "off":
        return Div(
            P(Span("Off", cls="badge badge-sm badge-ghost mr-2"),
              "After your password, logging in asks for a 6-digit code from an authenticator app on your phone "
              "(1Password, Google Authenticator, Aegis...).", cls="text-sm text-base-content/70"),
            _action_row(Button(KEY_SVG, Span("Set up", cls="ml-1"), type="button", cls="btn btn-sm",
                               **_twofactor_swap(hx_get="/admin/2fa/setup")), status=error),
        )
    if state == "setup":
        uri = totp.provisioning_uri(secret, settings.get("author_name") or "admin", settings.get("site_title"))
        return Form(
            P("1. Scan this with your authenticator app, or type the key in by hand.",
              cls="text-sm text-base-content/70 mb-2"),
            Div(
                # a QR code has to stay dark-on-light to scan reliably, so
                # this one surface is white on purpose, whatever the theme
                Div(NotStr(totp.qr_svg(uri)), cls="w-36 h-36 bg-white p-1 rounded-box [&>svg]:w-full [&>svg]:h-full"),
                Code(" ".join(secret[i:i + 4] for i in range(0, len(secret), 4)),
                     cls="text-xs font-mono break-all bg-base-200 rounded-field px-2 py-1"),
                cls="flex flex-col sm:flex-row items-start sm:items-center gap-3 mb-3"
            ),
            FormField("2. Enter the code it shows",
                      Input(name="code", required=True, autocomplete="one-time-code", inputmode="numeric",
                            maxlength="6", cls="input input-sm w-40 font-mono tracking-widest")),
            _action_row(
                Button(X_SVG, Span("Discard", cls="ml-1"), type="button", cls="btn btn-sm",
                       **_twofactor_swap(hx_get="/admin/2fa/panel")),
                Button(CHECK_SVG, Span("Turn on", cls="ml-1"), type="submit", cls="btn btn-primary btn-sm"),
                status=error
            ),
            **_twofactor_swap(hx_post="/admin/2fa/enable")
        )
    if state == "codes":
        text = "\n".join(codes)
        return Div(
            P("Save these recovery codes somewhere safe - they get you in if you lose your phone. Each works "
              "once, and they won't be shown again.",
              cls="text-sm text-base-content/70 mb-3"),
            Div(*[Code(c, cls="font-mono text-sm") for c in codes],
                cls="grid grid-cols-2 gap-x-6 gap-y-1 bg-base-200 rounded-box p-3 w-fit"),
            _action_row(
                Button(COPY_SVG, Span("Copy", cls="ml-1"), type="button", cls="btn btn-sm",
                       data_copy=text),
                A(DOWNLOAD_SVG, Span("Download", cls="ml-1"), cls="btn btn-sm",
                  href="data:text/plain;charset=utf-8," + quote(text), download="soloblog-recovery-codes.txt"),
                Button(CHECK_SVG, Span("Done", cls="ml-1"), type="button", cls="btn btn-primary btn-sm",
                       **_twofactor_swap(hx_get="/admin/2fa/panel")),
            ),
        )
    left = totp.recovery_codes_left()
    return Form(
        P(Span("On", cls="badge badge-sm badge-success mr-2"),
          f"Logging in asks for a code from your authenticator app. {left} recovery "
          f"code{'s' if left != 1 else ''} left.", cls="text-sm text-base-content/70 mb-3"),
        FormField("Password", Input(type="password", name="password", required=True,
                                    autocomplete="current-password", cls="input input-sm w-full"),
                  help="To make a change here, confirm it's you."),
        _action_row(
            Button(RESTORE_SVG, Span("New recovery codes", cls="ml-1"), type="submit", cls="btn btn-sm",
                   hx_post="/admin/2fa/recovery"),
            Button(X_SVG, Span("Turn off", cls="ml-1"), type="submit", cls="btn btn-sm text-error",
                   hx_post="/admin/2fa/disable"),
            status=error
        ),
        **_twofactor_swap()
    )


def PasskeysPanel():
    rows = [
        Div(
            Div(P(p["name"], cls="text-sm"),
                P(f"Added {format_date(p['created_at'])}" +
                  (f" · last used {format_when(p['last_used_at'])}" if p["last_used_at"] else " · not used yet"),
                  cls="text-xs text-base-content/50")),
            RowActions(Form(Input(type="hidden", name="credential_id", value=p["id"]),
                            IconAction(TRASH_SVG, "Remove", danger=True,
                                       confirm=f"Remove the passkey “{p['name']}”? That device won't log in with "
                                               "it any more."),
                            action="/admin/passkeys/delete", method="post", cls="contents"),
                       id=f"passkey-acts-{p['id']}"),
            cls="flex items-center justify-between py-2 border-b-[length:var(--border)] border-base-300 last:border-0"
        ) for p in passkeys.list_all()
    ]
    return SettingsPanel(
        "Passkeys",
        P("Log in with your fingerprint, face or device PIN instead of a password. Passkeys can't be phished, "
          "and skip the two-factor code.", cls="text-sm text-base-content/70 mb-3"),
        Div(*rows, cls="mb-3") if rows else None,
        FormField("Name", Input(id="passkey-name", placeholder="e.g. MacBook, iPhone, YubiKey", maxlength="60",
                                cls="input input-sm w-full"),
                  help="So you can tell your passkeys apart later."),
        Div(
            # removing one reports here too (a redirect to #passkey-status)
            Span(id="passkey-status", data_status_slot=True, role="status", cls=f"text-xs {STATUS_BESIDE}"),
            Button(KEY_SVG, Span("Add a passkey", cls="ml-1"), type="button", cls="btn btn-sm",
                   **on("click", "addPasskey")),
            cls=f"{STATUS_ROW} mt-3"
        ),
        key="security-passkeys"
    )


def RecoveryKeyBody(state=None, key="", error=""):
    """Security's recovery key, swapped in place: none yet or saved, and
    the new key shown the once."""
    swap = dict(hx_target="#recovery-key-body", hx_swap="innerHTML")
    if state == "show":
        s = settings.get_all()
        text = (f"Recovery key for {s.get('site_title')} ({config.BASE_URL})\n\n{key}\n\n"
                f"It resets the admin password at {config.BASE_URL}/forgot-password - keep it private.\n")
        return Div(
            P("Save the key somewhere safe, like a password manager. It won't be shown again, and your old key "
              "stops working.", cls="text-sm text-base-content/70 mb-3"),
            Code(key, cls="block w-fit font-mono text-base tracking-wide bg-base-200 rounded-box px-3 py-2 "
                          "break-all select-all"),
            _action_row(
                Button(COPY_SVG, Span("Copy", cls="ml-1"), type="button", cls="btn btn-sm", data_copy=key),
                A(DOWNLOAD_SVG, Span("Download", cls="ml-1"), cls="btn btn-sm",
                  href="data:text/plain;charset=utf-8," + quote(text), download="soloblog-recovery-key.txt"),
                Button(CHECK_SVG, Span("I've saved it", cls="ml-1"), type="button", cls="btn btn-primary btn-sm",
                       hx_get="/admin/recovery-key/panel", **swap),
                status_id="recovery-key-status"),
        )
    made = settings.get("recovery_key_made")
    return Form(
        P(Span("Saved", cls="badge badge-sm badge-success mr-2"),
          f"Made {format_date(made)}. The key resets your password if you forget it. Lost it? Make a new one.",
          cls="text-sm text-base-content/70 mb-3") if auth.has_recovery_key() else
        P(Span("Not made", cls="badge badge-sm badge-ghost mr-2"),
          "A recovery key resets your password if you forget it. Make one and keep it safe.",
          cls="text-sm text-base-content/70 mb-3"),
        FormField("Password", Input(type="password", name="password", required=True,
                                    autocomplete="current-password", cls="input input-sm w-full"),
                  help="To make a new key, confirm it's you."),
        _action_row(
            Button(KEY_SVG, Span("Make a new key" if auth.has_recovery_key() else "Make a recovery key", cls="ml-1"),
                   type="submit", cls="btn btn-sm"),
            status=error, status_id="recovery-key-status"),
        hx_post="/admin/recovery-key", **swap
    )


def SessionsPanel():
    return SettingsPanel(
        "Sessions",
        P(f"With Keep me signed in selected, you stay logged in for {config.SESSION_DAYS} days on each browser. "
          "Changing your password logs out the others.", cls="text-sm text-base-content/70"),
        Form(
            Div(Span(id="sessions-status", data_status_slot=True, role="status", cls=f"text-xs {STATUS_BESIDE}"),
                Button(X_SVG, Span("Log out other devices", cls="ml-1"), type="button", cls="btn btn-sm",
                       data_confirm="Log out every other browser and device? This one stays logged in."),
                cls=f"{STATUS_ROW} mt-3"),
            action="/admin/sessions/end-others", method="post"
        ),
        key="security-sessions"
    )


def SecurityTab():
    from soloblog.routes.auth_routes import AccountName, NewPasswordFields
    return Div(
        SettingsPanel("Two-factor authentication (2FA)", Div(TwoFactorBody(), id="twofactor-body"), key="security-2fa"),
        PasskeysPanel(),
        SettingsPanel("Recovery key", Div(RecoveryKeyBody(), id="recovery-key-body"), key="security-recovery"),
        SessionsPanel(),
        # each card here does its own thing at once (no page Save): the
        # password too
        Form(
            SettingsPanel(
                "Password",
                AccountName(),
                FormField("Current password",
                           Input(type="password", name="current", required=True, autocomplete="current-password",
                                 cls="input input-sm w-full"), cls=FIELD_GAP),
                *NewPasswordFields("New password"),
                _action_row(Button(KEY_SVG, Span("Change password", cls="ml-1"), type="submit", cls="btn btn-sm"),
                            status_id="save-status"),
                key="security-password"
            ),
            hx_post="/admin/settings/password", hx_target="#save-status",
            hx_swap="outerHTML show:none focus-scroll:false"
        ),
        cls="flex flex-col gap-3"
    )


@ar.post("/admin/passkeys/options")
def passkey_options(session, request):
    return Response(passkeys.registration_options(request, session), media_type="application/json")


@ar.post("/admin/passkeys/register")
async def passkey_register(session, request):
    try:
        body = await request.json()
    except ValueError:  # not JSON, or not UTF-8
        return JSONResponse({"error": "Something went wrong - try again"}, status_code=400)
    error = passkeys.register(request, session, body.get("credential") or {}, body.get("name") or "")
    return JSONResponse({"error": error} if error else {"ok": True})


@ar.post("/admin/passkeys/delete")
def passkey_delete(session, credential_id: str = ""):
    passkeys.delete(credential_id)
    auth.end_other_sessions(session)
    return _toast_redirect("/admin/settings?tab=security#passkey-status", "Passkey removed - other devices are logged out")


@ar.post("/admin/recovery-key")
def make_recovery_key(request, session, password: str = ""):
    if not ratelimit.hit(f"ip:{ratelimit.client_ip(request)}", "confirm-password", limit=10, window_minutes=15):
        return RecoveryKeyBody(error="Too many attempts. Try again in a few minutes")
    if not password:
        return RecoveryKeyBody(error="Enter your password")
    if not auth.verify_password(password):
        return RecoveryKeyBody(error="That password isn't right")
    return RecoveryKeyBody("show", key=auth.new_recovery_key())


@ar.get("/admin/recovery-key/panel")
def recovery_key_panel(session):
    return RecoveryKeyBody()


@ar.post("/admin/sessions/end-others")
def end_other_sessions(session):
    auth.end_other_sessions(session)
    return _toast_redirect("/admin/settings?tab=security#sessions-status", "Logged out everywhere else")


@ar.get("/admin/2fa/panel")
def twofactor_panel(session):
    return TwoFactorBody()


@ar.get("/admin/2fa/setup")
def twofactor_setup(session, request):
    # held in the session, not the database, until a code proves the
    # app has it - an abandoned setup changes nothing
    session["2fa_setup"] = totp.new_secret()
    return TwoFactorBody("setup", secret=session["2fa_setup"])


@ar.post("/admin/2fa/enable")
def twofactor_enable(session, request, code: str = ""):
    secret = session.get("2fa_setup")
    if not secret:
        return TwoFactorBody("off", error="Setup expired - start again")
    if totp.matching_step(secret, code) is None:
        return TwoFactorBody("setup", secret=secret, error="That code didn't match - try the next one")
    session.pop("2fa_setup", None)
    codes = totp.enable(secret)
    auth.end_other_sessions(session)
    return TwoFactorBody("codes", codes=codes)


def _confirm_password(password):
    if not ratelimit.hit("admin", "confirm_password", limit=10, window_minutes=60):
        return "Too many attempts, try later"
    return "" if auth.verify_password(password) else "Wrong password"


@ar.post("/admin/2fa/recovery")
def twofactor_recovery(session, request, password: str = ""):
    error = _confirm_password(password)
    if error:
        return TwoFactorBody("on", error=error)
    return TwoFactorBody("codes", codes=totp.regenerate_recovery_codes())


@ar.post("/admin/2fa/disable")
def twofactor_disable(session, request, password: str = ""):
    error = _confirm_password(password)
    if error:
        return TwoFactorBody("on", error=error)
    totp.disable()
    auth.end_other_sessions(session)
    return TwoFactorBody("off")


@ar.post("/admin/settings/password")
def save_password(req, session, password: str, confirm: str, current: str = ""):

    if not ratelimit.hit("admin", "set_password", limit=10, window_minutes=60):
        return SaveStatus("Too many attempts, try later", "error")
    # a logged-in browser left open shouldn't be enough to take the
    # account over for good
    if not current:
        return SaveStatus("Enter your current password", "error")
    if not auth.verify_password(current):
        return SaveStatus("Current password is wrong", "error")
    if len(password) < 8:
        return SaveStatus("Password needs 8+ characters", "error")
    if password != confirm:
        return SaveStatus("Passwords didn't match", "error")

    auth.set_password(password)
    auth.end_other_sessions(session)
    return SaveStatus("Password updated - other devices are logged out")
