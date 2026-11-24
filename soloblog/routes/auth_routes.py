import hashlib
import hmac
import secrets
import time
from urllib.parse import quote

from fasthtml.common import *

from soloblog import auth
from soloblog import settings
from soloblog import ratelimit
from soloblog import posts
from soloblog import totp
from soloblog import passkeys
from soloblog import config
from soloblog import mail
from soloblog import notify
from soloblog.ui import (Layout, Alert, FormField, FIELD_GAP, CHECK_SVG, LOGIN_SVG, KEY_SVG, COPY_SVG, DOWNLOAD_SVG,
                         RESTORE_SVG)

ar = APIRouter()

# how long a correct password stays good for while the second step
# (the authenticator code) is still to come
TWO_FACTOR_WINDOW = 300


def AuthCard(title, description, *content):
    """Setup, log in and the two-factor step - one small centered card,
    with the same labelled fields and icon buttons as the rest of the
    admin rather than bare placeholder-only inputs."""
    return Div(
        Div(
            H1(title, cls="text-xl font-bold"),
            P(description, cls="text-sm text-base-content/60 mb-2") if description else None,
            *content,
            cls="card-body p-6"
        ),
        cls="card card-border bg-base-100 max-w-sm mx-auto"
    )


def _page(hdrs, title, path, card):
    if hdrs is not None:
        from soloblog.seo import page_meta
        page_meta(hdrs, title, path=path)
    return Layout(card, settings=settings.get_all(), pinned_tree=posts.list_pinned_tree())


def _submit(label, icon=CHECK_SVG):
    return Button(icon, Span(label, cls="ml-1"), type="submit", cls="btn btn-primary btn-sm w-full mt-2")


def AccountName():
    """The account a password belongs to, for password managers - they save
    and fill a login by its username. There's one admin, so nothing to
    type: a hidden field with the admin's email, if they gave one."""
    return Input(type="text", name="username", autocomplete="username", hidden=True, tabindex="-1",
                 value=settings.get("admin_email") or "admin")


def NewPasswordFields(label="Password"):
    """A new password, typed twice - the second has to match as it's typed
    (data-must-match, app.js), and again when it's sent."""
    return (
        FormField(label, Input(type="password", name="password", required=True, minlength="8",
                               autocomplete="new-password", cls="input input-sm w-full"),
                  help="At least 8 characters.", cls=FIELD_GAP),
        FormField("Type it again", Input(type="password", name="confirm", required=True, minlength="8",
                                         autocomplete="new-password", aria_label=f"{label}, again",
                                         data_must_match="password", data_mismatch="The passwords don't match",
                                         cls="input input-sm w-full")),
    )


def RecoveryKeyCard(key, title, intro, next_href, next_label):
    """A recovery key, shown the once: to copy, download or write down."""
    s = settings.get_all()
    text = (f"Recovery key for {s.get('site_title')} ({config.BASE_URL})\n\n{key}\n\n"
            f"It resets the admin password at {config.BASE_URL}/forgot-password - keep it private.\n")
    return AuthCard(
        title, intro,
        Code(key, cls="block text-center font-mono text-lg tracking-wide bg-base-200 rounded-box px-3 py-3 "
                      "my-2 break-all select-all"),
        Div(Button(COPY_SVG, Span("Copy", cls="ml-1"), type="button", cls="btn btn-sm join-item", data_copy=key),
            A(DOWNLOAD_SVG, Span("Download", cls="ml-1"), cls="btn btn-sm join-item",
              href="data:text/plain;charset=utf-8," + quote(text), download="soloblog-recovery-key.txt"),
            cls="join self-center"),
        P("A password manager, or printed and put away, are good places. It won't be shown again.",
          cls="text-xs text-base-content/60 mt-3"),
        A(CHECK_SVG, Span(next_label, cls="ml-1"), href=next_href, cls="btn btn-primary btn-sm w-full mt-2"),
    )


# a browser that's signed in here before, remembered by a cookie signed
# with the session secret - so a sign-in from anywhere new can be told
# apart (notify.sign_in), and the cookie can't be made up to hide one
DEVICE_COOKIE = "known_device"


def _device_sig(token: str) -> str:
    return hmac.new(config.SESSION_SECRET.encode(), token.encode(), hashlib.sha256).hexdigest()[:32]


def _known_device(req) -> bool:
    token, _, sig = (req.cookies.get(DEVICE_COOKIE) or "").partition(".")
    return bool(token) and hmac.compare_digest(sig, _device_sig(token))


def landing(session) -> str:
    """Where to go once logged in: the page that sent you to log in (an app
    asking to sign in with your site, say), else the home page."""
    from soloblog.guards import is_local_path
    after = session.pop("after_login", "")
    return after if is_local_path(after) else "/"


def _signed_in(req, session, resp):
    """Logged in - and a browser it hasn't seen before is reported to the
    admin, then remembered."""
    auth.log_in(session, keep=not session.pop("keep_off", False))
    if not _known_device(req):
        notify.sign_in(req)
        token = secrets.token_urlsafe(12)
        resp.set_cookie(DEVICE_COOKIE, f"{token}.{_device_sig(token)}", max_age=400 * 86400, httponly=True,
                        samesite="lax", secure=config.BASE_URL.startswith("https://"))
    return resp


# where each host shows the server's log, for the setup token printed there
TOKEN_IN_LOG = {
    "Render": "In Render, open this service's Logs",
    "Railway": "In Railway, open the latest deployment's logs",
    "Fly.io": "Run fly logs, or open Live Logs in Fly's dashboard",
    "Heroku": "Run heroku logs",
    "Koyeb": "In Koyeb, open this service's logs",
    "Kubernetes": "Run kubectl logs for the Soloblog pod",
    "Docker": "Run docker logs with the container's name, or docker compose logs",
    # app stores and self-hosting panels, named by their package's HOSTED_ON
    "Zeabur": "In Zeabur, open this service's logs",
    "Sealos": "In Sealos, open the app's details, then its logs",
    "Coolify": "In Coolify, open this service's logs",
    "CapRover": "In CapRover, open the app's Deployment tab, then its logs",
    "Dokploy": "In Dokploy, open this service's logs",
    "Easypanel": "In Easypanel, open this service's logs",
    "CasaOS": "In CasaOS, open Soloblog's settings, then Terminal and Logs",
    "Unraid": "In Unraid's Docker tab, select Soloblog's icon, then Logs",
    "TrueNAS": "In TrueNAS, open Apps, select Soloblog, then its logs under Workloads",
    "Cloudron": "In Cloudron, open the app's Logs",
}


# where each host shows its settings, for a SETUP_TOKEN set there - the
# Render and Heroku buttons make one by themselves
TOKEN_IN_SETTINGS = {
    "Render": "In Render, open this service's Environment",
    "Railway": "In Railway, open this service's Variables",
    "Heroku": "In Heroku, open Settings and select Reveal Config Vars",
    "Koyeb": "In Koyeb, open this service's Settings, then Environment variables",
}


# where a platform that made the token itself shows it, said in full
TOKEN_SHOWN = {
    "umbrelOS": "In umbrelOS, right-click Soloblog on the home screen and choose Show default "
                "credentials. The password it shows is your setup token.",
}


def token_help() -> str:
    from soloblog import health
    if auth.setup_token() == config.SETUP_TOKEN:
        if health.host_kind() in TOKEN_SHOWN:
            return TOKEN_SHOWN[health.host_kind()]
        where = TOKEN_IN_SETTINGS.get(health.host_kind())
        if where:
            return f"{where} and copy SETUP_TOKEN."
        return "Enter the SETUP_TOKEN you chose when you deployed it."
    where = TOKEN_IN_LOG.get(health.host_kind())
    if where:
        return f"{where} and copy the token from the lines marked [setup]."
    return "It's in the server's log, on the lines marked [setup], and in setup-token.txt in the data folder."


HELD_WHY = {
    "locked": "Your bucket has a backup of this site, locked with a passphrase other than the one on your "
              "host. Type the passphrase it was made with.",
    "unreachable": "Your storage bucket didn't answer, so your site couldn't be restored. Check the S3_ "
                   "settings on your host, then try again.",
    "damaged": "The newest backup in your bucket couldn't be opened. Choose an earlier one.",
}
PASSPHRASE_MAX = 1000


def BringBackCard(error="", token="", key=""):
    """While storage.held: the site's own backups, offered before a fresh
    start - a blank site set up here would be backed up over them."""
    from soloblog import storage
    from soloblog.routes.backup_routes import backup_when
    why = storage.held.get("why", "damaged")
    try:
        backups = storage.list_backups()[:10] if why != "unreachable" else []
    except storage.StorageError:
        backups, why = [], "unreachable"
    return AuthCard(
        "Restore your site",
        HELD_WHY[why],
        Alert(error, "error") if error else None,
        Form(
            FormField("Setup token", Input(type="text", name="token", required=True, autocomplete="off",
                                           value=token, cls="input input-sm w-full font-mono"), help=token_help(),
                      cls=FIELD_GAP),
            FormField("Backup", Select(*[Option(backup_when(b["key"]) or b["key"], value=b["key"],
                                                selected=b["key"] == key) for b in backups],
                                       name="key", cls="select select-sm w-full"),
                      cls=FIELD_GAP) if backups else None,
            FormField("Passphrase", Input(type="password", name="passphrase", autocomplete="off",
                                          maxlength=str(PASSPHRASE_MAX), cls="input input-sm w-full"),
                      help="The one the backup was made with", cls=FIELD_GAP) if why == "locked" else None,
            Span(data_status_slot=True, role="status", cls="text-xs block mt-2"),
            _submit("Try again" if why == "unreachable" else "Restore", RESTORE_SVG),
            action="/setup/restore", method="post"
        ),
        A("Start a new site instead", href="/setup?new=1",
          cls="link link-hover text-xs text-base-content/60 mt-3 self-center"),
    )


@ar.get("/setup")
def setup_page(hdrs=None, error: str = "", new: str = "", token: str = "", key: str = ""):
    if auth.admin_exists():
        return RedirectResponse("/login", status_code=303)
    from soloblog import health, storage
    if storage.held and not new:
        return _page(hdrs, "Restore your site", "/setup", BringBackCard(error, token, key))
    return _page(hdrs, "Set up your site", "/setup", AuthCard(
        "Set up your site",
        token_help(),
        # before anything's written: a site that won't survive its next update
        None if health.data_kept() else Alert(
            "This site isn't on lasting storage, so your posts would be lost on the next update. "
            + health.keep_it(), "warning"),
        # a fresh start beside backups that couldn't be opened
        Alert("Your bucket's backups stay there for now, but each new backup replaces the oldest, as usual.",
              "warning")
        if storage.held else None,
        Alert(error, "error") if error else None,
        Form(
            AccountName(),
            FormField("Setup token", Input(type="text", name="token", required=True, autocomplete="off",
                                           cls="input input-sm w-full font-mono"), cls=FIELD_GAP),
            *NewPasswordFields(),
            Span(data_status_slot=True, role="status", cls="text-xs block mt-2"),
            _submit("Create admin account"),
            Input(type="hidden", name="new", value="1") if storage.held else None,
            action="/setup", method="post"
        ),
    ))


@ar.post("/setup/restore")
def setup_restore(req, token: str = "", key: str = "", passphrase: str = ""):
    from soloblog import storage
    if auth.admin_exists() or not storage.held:
        return RedirectResponse("/login", status_code=303)
    if not ratelimit.hit(f"ip:{ratelimit.client_ip(req)}", "setup", limit=10, window_minutes=15):
        return setup_page(error="Too many attempts. Try again in a few minutes.")
    if not secrets.compare_digest(token.strip(), auth.setup_token()):
        return setup_page(error="That setup token isn't right - check it and try again.")
    if len(passphrase) > PASSPHRASE_MAX:
        return setup_page(token=token, key=key, error="Wrong passphrase, try again")
    try:
        if not key:  # the bucket didn't answer before: the newest, if it does now
            try:
                backups = storage.list_backups()
            except storage.StorageError as e:
                raise storage.BucketSilent(str(e)) from None
            if not backups:
                storage.release_hold()
                return RedirectResponse("/setup", status_code=303)
            key = backups[0]["key"]
        storage.restore_held(key, passphrase)
    except storage.BucketSilent:
        storage.held["why"] = "unreachable"
        return setup_page(token=token, key=key, error="Your storage bucket didn't answer. Check the S3_ settings "
                                                      "on your host, then try again.")
    except storage.WontOpen:
        storage.held["why"] = "locked"
        return setup_page(token=token, key=key, error="Wrong passphrase, try again" if passphrase
                          else "Type the passphrase the backup was made with")
    except storage.StorageError:
        return setup_page(token=token, key=key, error="That backup couldn't be opened. Choose an earlier one.")
    auth.forget_setup_token()
    return RedirectResponse("/login?back=1", status_code=303)


def _reached_at(req) -> str:
    """The address this request came to - behind a proxy, as the visitor
    typed it (X-Forwarded-Proto and -Host), not as the proxy passed it on."""
    proto = (req.headers.get("x-forwarded-proto") or req.url.scheme or "http").split(",")[0].strip()
    host = (req.headers.get("x-forwarded-host") or req.headers.get("host") or "").split(",")[0].strip()
    return f"{proto}://{host}" if host else ""


@ar.post("/setup")
def do_setup(req, session, token: str, password: str, confirm: str, new: str = ""):
    if auth.admin_exists():
        return RedirectResponse("/login", status_code=303)

    if not ratelimit.hit(f"ip:{ratelimit.client_ip(req)}", "setup", limit=10, window_minutes=15):
        return setup_page(new=new, error="Too many attempts. Try again in a few minutes.")
    if not secrets.compare_digest(token.strip(), auth.setup_token()):
        return setup_page(new=new, error="That setup token isn't right - check it and try again.")
    if len(password) < 8:
        return setup_page(new=new, error="Password needs to be at least 8 characters.")
    if password != confirm:
        return setup_page(new=new, error="Passwords didn't match.")

    from soloblog import storage
    # a fresh start, chosen over the backups that couldn't be opened
    storage.release_hold()
    auth.create_admin(password)
    settings.set_many({"whatsnew_seen": config.VERSION})
    from soloblog.routes.welcome import make_welcome_post
    make_welcome_post()
    # no address set on the host: the one setup was opened at - the person
    # holding the setup token is the owner, so it's theirs to trust
    if not config.BASE_URL_FIXED:
        reached = settings.clean_site_url(_reached_at(req))
        if reached:
            settings.set_many({"site_url": reached})
            settings.use_site_url(reached)
    auth.log_in(session)
    # the way back in if the password's ever forgotten - then straight into
    # the first-run wizard, a few questions, all skippable
    return _page(None, "Your recovery key", "/setup", RecoveryKeyCard(
        auth.new_recovery_key(), "Save your recovery key",
        "If you ever forget your password, this key resets it - no email or server access needed.",
        "/admin/welcome", "I've saved it"))


@ar.get("/login")
def login_page(hdrs=None, error: str = "", back: str = ""):
    if not auth.admin_exists():
        return RedirectResponse("/setup", status_code=303)
    return _page(hdrs, "Log in", "/login", AuthCard(
        "Log in", None,
        Alert(error, "error") if error else None,
        Alert("Your site is back. Log in with its password.", "success") if back and not error else None,
        Alert(Span("Password: ", Strong(config.DEMO_PASSWORD)), "info")
        if config.DEMO_MODE else None,
        Form(
            AccountName(),
            FormField("Password", Input(type="password", name="password", required=True, autofocus=True,
                                        autocomplete="current-password", cls="input input-sm w-full")),
            KeepSignedIn(),
            _submit("Log in", LOGIN_SVG),
            action="/login", method="post"
        ),
        A("Forgot password?", href="/forgot-password", cls="link link-hover text-xs text-base-content/60 mt-2 self-center"),
        # only once a passkey exists - no dead-end button on a new blog
        Div(
            Div("or", cls="divider text-xs text-base-content/50 my-2"),
            Button(KEY_SVG, Span("Log in with a passkey", cls="ml-1"), type="button", cls="btn btn-sm w-full",
                   data_onclick="loginWithPasskey"),
            P(id="passkey-login-status", role="status", cls="text-xs mt-2"),
        ) if passkeys.count() else None,
    ))


def KeepSignedIn():
    # unticked, for a shared computer: logged out when the browser closes
    return Label(Input(type="checkbox", name="keep", value="1", checked=True, id="keep-signed-in",
                       cls="checkbox checkbox-sm"),
                 Span("Keep me signed in", cls="text-sm"), cls="flex items-center gap-2 mt-3 cursor-pointer")


def _can_email_reset() -> bool:
    return bool(settings.get("admin_email")) and settings.get("email_provider") in ("smtp", "api")


def RecoveryKeyForm(error=""):
    return Form(
        AccountName(),
        FormField("Recovery key", Input(name="key", required=True, autocomplete="off", autocapitalize="characters",
                                        spellcheck="false", placeholder="XXXX-XXXX-XXXX-XXXX-XXXX",
                                        cls="input input-sm w-full font-mono"),
                  help="The key you saved when you set up your site, or made in Settings > Security.",
                  cls=FIELD_GAP),
        *NewPasswordFields("New password"),
        Label(Input(type="checkbox", name="disable_2fa", value="1", cls="checkbox checkbox-sm"),
              Span("Also turn off two-factor authentication", cls="text-sm"),
              cls="flex items-center gap-2 mt-3") if totp.is_enabled() else None,
        Span(error, data_status_slot=True, role="status", cls="text-xs text-error block mt-2" if error else "text-xs block mt-2"),
        _submit("Reset my password"),
        action="/forgot-password/key", method="post"
    )


@ar.get("/forgot-password")
def forgot_page(hdrs=None, sent: bool = False, error: str = ""):
    key = (P("Use your recovery key and choose a new password.", cls="text-sm text-base-content/70"),
           RecoveryKeyForm(error),
           Div("No recovery key?", cls="divider text-xs text-base-content/50 my-3"))
    if _can_email_reset():
        body = (Alert("Sent - the link works for an hour", "success") if sent else None,
                P("A reset link goes to the email address saved in Settings > Email.",
                  cls="text-sm text-base-content/70"),
                Form(_submit("Email me a reset link"), action="/forgot-password", method="post"))
    else:
        body = (P("Restart the server with the environment variable ", Code("RESET_PASSWORD=1"),
                  ". A one-time reset link is printed to its log. Remove the variable again afterwards.",
                  cls="text-sm text-base-content/70"),
                P("With email set up and your address saved in Settings > Email, this page can email you a "
                  "link instead.", cls="text-xs text-base-content/50 mt-2"))
    return _page(hdrs, "Forgot password", "/forgot-password", AuthCard("Forgot your password?", None, *key, *body))


@ar.post("/forgot-password/key")
def reset_with_key(req, session, key: str = "", password: str = "", confirm: str = "", disable_2fa: bool = False):
    if not key.strip():
        return forgot_page(error="Enter your recovery key.")
    # a key is 100 bits - but a guess costs nothing to send, so few of them
    who = f"ip:{ratelimit.client_ip(req)}"
    if not ratelimit.hit(who, "recovery-key", limit=5, window_minutes=60):
        return forgot_page(error=_wait(who, "recovery-key", 60))
    if not auth.recovery_key_ok(key):
        return forgot_page(error="That recovery key isn't right - check it and try again.")
    if len(password) < 8:
        return forgot_page(error="The password needs at least 8 characters.")
    if password != confirm:
        return forgot_page(error="The passwords don't match.")
    auth.set_password(password)
    if disable_2fa:
        totp.disable()
    auth.log_in(session)
    # every other browser is logged out - whoever had the old password included
    auth.end_other_sessions(session)
    # the old key is used up: a new one, shown the once
    return _page(None, "Your new recovery key", "/forgot-password", RecoveryKeyCard(
        auth.new_recovery_key(), "Password changed",
        "Your old recovery key is used up. Here's a new one - save it the same way.",
        "/admin/posts", "I've saved it"))


@ar.post("/forgot-password")
def send_reset(req):
    if not ratelimit.hit(f"ip:{ratelimit.client_ip(req)}", "reset", limit=3, window_minutes=60) \
            or not _can_email_reset():
        return RedirectResponse("/forgot-password", status_code=303)
    if auth.reset_emailed_lately():
        # the same answer, and no second email: asking again and again
        # can't fill the admin's inbox
        return RedirectResponse("/forgot-password?sent=1", status_code=303)
    link = f"{config.BASE_URL}/reset-password?token={auth.start_reset(60, by_email=True)}"
    site = settings.get("site_title")
    mail.send_email(settings.get("admin_email"), f"Reset your password for {site}",
                    f"A password reset was asked for on {site}.\n\n"
                    f"Choose a new password:\n{link}\n\n"
                    "The link works once, for an hour.\n\n"
                    "If you didn't ask for this, you can ignore this email. Your password stays as it is.\n")
    return RedirectResponse("/forgot-password?sent=1", status_code=303)


@ar.get("/reset-password")
def reset_page(hdrs=None, token: str = "", error: str = ""):
    if not auth.reset_token_ok(token):
        return _page(hdrs, "Reset password", "/reset-password", AuthCard(
            "That link has expired", None,
            P("Ask for a new one from ", A("Forgot password?", href="/forgot-password", cls="link"), ".",
              cls="text-sm text-base-content/70")))
    return _page(hdrs, "Reset password", "/reset-password", AuthCard(
        "Choose a new password", None,
        Alert(error, "error") if error else None,
        Form(
            AccountName(),
            Input(type="hidden", name="token", value=token),
            *NewPasswordFields("New password"),
            Label(Input(type="checkbox", name="disable_2fa", value="1", cls="checkbox checkbox-sm"),
                  Span("Also turn off two-factor authentication", cls="text-sm"),
                  cls="flex items-center gap-2 mt-3") if totp.is_enabled() and not auth.reset_by_email(token) else None,
            P("Two-factor authentication stays on: you'll be asked for a code next.", cls="text-xs text-base-content/60 mt-3")
            if totp.is_enabled() and auth.reset_by_email(token) else None,
            _submit("Save and log in"),
            action="/reset-password", method="post"
        ),
    ))


@ar.post("/reset-password")
def do_reset(req, session, token: str = "", password: str = "", confirm: str = "", disable_2fa: bool = False):
    if not ratelimit.hit(f"ip:{ratelimit.client_ip(req)}", "reset-use", limit=10, window_minutes=15):
        return reset_page(token="")
    if not auth.reset_token_ok(token):
        return reset_page(token=token)
    if len(password) < 8:
        return reset_page(token=token, error="Password needs to be at least 8 characters.")
    if password != confirm:
        return reset_page(token=token, error="Passwords didn't match.")
    by_email = auth.reset_by_email(token)
    auth.set_password(password)
    auth.finish_reset()
    # every other browser is logged out - whoever had the old password included
    auth.end_other_sessions()
    if totp.is_enabled() and by_email:
        # an inbox alone isn't the second factor - the code still is
        session["2fa_pending"] = int(time.time())
        session["after_login"] = "/admin/posts?toast=Password+changed&toast_type=success"
        return RedirectResponse("/login/code", status_code=303)
    if disable_2fa:
        totp.disable()
    auth.log_in(session)
    return RedirectResponse("/admin/posts?toast=Password+changed&toast_type=success", status_code=303)


def _wait(who, bucket, window):
    """Not how many tries are left - that only helps someone guessing - but
    how long until the next one, which is what the owner needs."""
    n = ratelimit.wait_minutes(who, bucket, window)
    return f"Too many attempts. Try again in {n} minute{'s' if n != 1 else ''}."


# Each address has its own limit, which thousands of addresses guessing
# together walk straight past. So wrong passwords are also counted across
# the whole site: past this many in the window, only a browser that has
# signed in before (its signed cookie) may try a password, and the admin
# is told once an hour. The owner on a new device waits, or uses a
# passkey, the recovery key or a reset link - none of which can be guessed.
SITE_WRONG = 30
SITE_WINDOW = 15


def _guessing(req) -> bool:
    return not config.DEMO_MODE and not _known_device(req) \
        and ratelimit.count("site", "login-wrong", SITE_WINDOW) >= SITE_WRONG


def _wrong_password():
    ratelimit.hit("site", "login-wrong", limit=10 ** 6, window_minutes=SITE_WINDOW)
    if not config.DEMO_MODE and ratelimit.count("site", "login-wrong", SITE_WINDOW) >= SITE_WRONG \
            and ratelimit.hit("site", "login-wrong-alert", limit=1, window_minutes=60):
        notify.guessing(SITE_WINDOW)


@ar.post("/login")
def do_login(req, session, password: str, keep: str = ""):
    if not password:
        return login_page(error="Enter your password.")
    who = f"ip:{ratelimit.client_ip(req)}"
    if _guessing(req):
        n = ratelimit.wait_minutes("site", "login-wrong", SITE_WINDOW)
        return login_page(error="Too many wrong passwords from other places. Log in from a browser you've "
                                f"used before, or try again in {n} minute{'s' if n != 1 else ''}.")
    if not ratelimit.hit(who, "login", limit=5, window_minutes=15):
        return login_page(error=_wait(who, "login", 15))

    if not auth.verify_password(password):
        _wrong_password()
        return login_page(error="Wrong password.")
    ratelimit.take_back(who, "login")
    session["keep_off"] = not keep

    if totp.is_enabled():
        # the password was right - but the session isn't logged in until
        # the authenticator code is too
        session["2fa_pending"] = int(time.time())
        return RedirectResponse("/login/code", status_code=303)
    return _signed_in(req, session, RedirectResponse(landing(session), status_code=303))


def _pending(session) -> bool:
    started = session.get("2fa_pending")
    return bool(started) and time.time() - started < TWO_FACTOR_WINDOW


@ar.get("/login/code")
def login_code_page(session, hdrs=None, error: str = ""):
    if not _pending(session):
        return RedirectResponse("/login", status_code=303)
    return _page(hdrs, "Log in", "/login/code", AuthCard(
        "Two-factor code",
        "Enter the 6-digit code from your authenticator app.",
        Alert(error, "error") if error else None,
        Form(
            FormField("Code", Input(type="text", name="code", required=True, autofocus=True,
                                    autocomplete="one-time-code", inputmode="numeric", maxlength="11",
                                    cls="input input-sm w-full font-mono tracking-widest"),
                      help="Lost your phone? A recovery code works here too."),
            _submit("Verify", LOGIN_SVG),
            action="/login/code", method="post"
        ),
    ))


@ar.post("/login/code")
def do_login_code(req, session, code: str = ""):
    if not _pending(session):
        return RedirectResponse("/login", status_code=303)
    # the same budget as the password step - 5 wrong codes and wait
    who = f"ip:{ratelimit.client_ip(req)}"
    if not ratelimit.hit(who, "login-code", limit=5, window_minutes=15):
        return login_code_page(session, error=_wait(who, "login-code", 15))
    if not totp.check(code):
        return login_code_page(session, error="That code didn't work.")
    session.pop("2fa_pending", None)
    return _signed_in(req, session, RedirectResponse(landing(session), status_code=303))


@ar.post("/login/passkey/options")
def passkey_login_options(request, session):
    return Response(passkeys.login_options(request, session), media_type="application/json")


@ar.post("/login/passkey/verify")
async def passkey_login_verify(request, session, keep: str = ""):
    # the same budget as the password - a passkey can't be guessed, but
    # this endpoint shouldn't be free to hammer either
    if not ratelimit.hit(f"ip:{ratelimit.client_ip(request)}", "login-passkey", limit=10, window_minutes=15):
        return JSONResponse({"error": "Too many attempts. Try again in a few minutes."}, status_code=429)
    try:
        credential = await request.json()
    except ValueError:  # not JSON, or not UTF-8
        return JSONResponse({"error": "Something went wrong - try again"}, status_code=400)
    if not passkeys.verify_login(request, session, credential):
        return JSONResponse({"error": "That passkey didn't work"}, status_code=400)
    session.pop("2fa_pending", None)
    session["keep_off"] = not keep
    return _signed_in(request, session, JSONResponse({"ok": True, "redirect": landing(session)}))


@ar.get("/logout")
def logout_page(session, hdrs=None):
    """An old bookmark or a link from another site only gets a question -
    logging out itself is a POST (below)."""
    if not auth.is_logged_in(session):
        return RedirectResponse("/", status_code=303)
    return _page(hdrs, "Log out", "/logout", AuthCard(
        "Log out?", None,
        Form(_submit("Log out", LOGIN_SVG), action="/logout", method="post"),
    ))


@ar.post("/logout")
def logout(session):
    auth.log_out(session)
    return RedirectResponse("/", status_code=303)
