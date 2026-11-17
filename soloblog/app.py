from fasthtml.common import *

import atexit
import logging

from starlette.middleware.gzip import GZipMiddleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
import hashlib
import json
import re
import time
from urllib.parse import parse_qs

from soloblog import js
from soloblog import config
from soloblog.guards import admin_guard
from soloblog import csp
from soloblog.db import run_migrations
from soloblog import settings
from soloblog import posts
from soloblog import auth
from soloblog import ads
from soloblog import captcha
from soloblog import extcomments
from soloblog import fonts
from soloblog import i18n
from soloblog import images
from soloblog import storage
from soloblog import themes
from soloblog.ui import CHECK_SVG
from soloblog.ui import post as ui_post

# one line per entry, its module's name saying where it came from - set up
# once here unless the server (or the tests) already have. LOG_LEVEL is for
# Soloblog's own lines; the libraries it uses say only what went wrong.
logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
# Soloblog notes everything (INFO) for its detailed log; the server's own
# output still shows only what LOG_LEVEL asks for
logging.getLogger("soloblog").setLevel(min(logging.INFO, logging.getLevelName(config.LOG_LEVEL)
                                          if isinstance(logging.getLevelName(config.LOG_LEVEL), int)
                                          else logging.INFO))
for _out in logging.getLogger().handlers:
    _out.setLevel(config.LOG_LEVEL)
# and its problems kept for Site health > Log, and everything for the download
from soloblog import health as _health  # noqa: E402
logging.getLogger("soloblog").addHandler(_health.log_handler())
_detail_log = _health.detail_handler()
logging.getLogger("soloblog").addHandler(_detail_log)
log = logging.getLogger(__name__)

# Tailwind + daisyUI are compiled locally by DaisyFT (static/css/input.css
# -> static/css/output.css) rather than pulled from a CDN - see
# static/css/input.css for the prose/EasyMDE/Pygments theming that used
# to live here as Python string constants.

# the stylesheet's link carries a hash of what's served (app_css), so a
# rebuild gets a new address and no browser keeps an old copy

CODE_COPY_JS = js.read("code_copy.js")

MASTODON_SHARE_JS = js.read("mastodon_share.js")

LIKE_JS = js.read("like.js")


MEDIA_PICKER_JS = js.read("media_picker.js")


LINK_PICKER_JS = js.read("link_picker.js")


SCROLL_TOP_JS = js.read("scroll_top.js")

FOOTER_CLEARANCE_JS = js.read("footer_clearance.js")

CHROME_OFFSETS_JS = js.read("chrome_offsets.js")

AUTOSAVE_JS = js.read("autosave.js")

SAVE_STATUS_CLEAR_JS = js.read("save_status_clear.js")

SORTABLE_JS = js.read("sortable.js")

PANEL_STATE_JS = js.read("panel_state.js")


TOAST_JS = js.read("toast.js").replace("__CHECK_ICON__", json.dumps(str(CHECK_SVG)))

COMMENTER_NAME_JS = js.read("commenter_name.js")

ACTIONS_JS = js.read("actions.js")

PAGE_HELPERS_JS = js.read("page_helpers.js")

CONFIRM_JS = js.read("confirm.js")


POPOVER_DROPDOWN_JS = js.read("popover_dropdown.js")
NAV_HOVER_JS = js.read("nav_hover.js")
COUNTDOWN_JS = js.read("countdown.js")

SELECT_JS = js.read("select.js")

LIVE_JS = js.read("live.js")

SCROLL_RESTORE_JS = js.read("scroll_restore.js")

ROW_LINKS_JS = js.read("row_links.js")

SIDENOTES_JS = js.read("sidenotes.js")

READING_JS = js.read("reading.js")

SLIDES_JS = js.read("slides.js")

LIGHTBOX_JS = js.read("lightbox.js")
MOTION_JS = js.read("motion.js")
TIMELINE_JS = js.read("timeline.js")

PASSKEY_JS = js.read("passkey.js")

BUSY_JS = js.read("busy.js")

VISITOR_THEME_INIT_JS = js.read("visitor_theme_init.js")
PICTURE_VERSIONS_JS = js.read("picture_versions.js")
DESIGN_OPEN_EARLY_JS = js.read("design_open_early.js")
DEMO_NOTE_EARLY_JS = js.read("demo_note_early.js")


def analytics_tags(provider: str, site_id: str):
    """The provider's own snippet. site_id was checked against a strict
    pattern when it was saved (admin_settings.ANALYTICS_ID_RE)."""
    if not site_id:
        return []
    if provider == "cloudflare":
        return [Script(src="https://static.cloudflareinsights.com/beacon.min.js", defer=True,
                       data_cf_beacon=json.dumps({"token": site_id}), nonce=csp.NONCE)]
    if provider == "plausible":
        return [Script(src="https://plausible.io/js/script.js", defer=True, data_domain=site_id, nonce=csp.NONCE)]
    if provider == "google":
        return [Script(src=f"https://www.googletagmanager.com/gtag/js?id={site_id}", **{"async": True}, nonce=csp.NONCE),
                Script("window.dataLayer = window.dataLayer || []; function gtag(){dataLayer.push(arguments);} "
                       f"gtag('js', new Date()); gtag('config', {json.dumps(site_id)});", nonce=csp.NONCE)]
    return []


def fediverse_creator(profile_url: str) -> str:
    """https://mastodon.social/@ann -> @ann@mastodon.social, else ""."""
    import re
    m = re.match(r"^https://([a-z0-9.-]+\.[a-z]{2,})/@([A-Za-z0-9_]+)/?$", (profile_url or "").strip())
    return f"@{m.group(2)}@{m.group(1)}" if m else ""


def apply_site_config(req, session):
    """Runs before every request - sets the server-rendered data-theme
    to the site's configured default, swaps in a custom favicon if
    one's been set, and - only when the admin has turned it on - loads
    the visitor-facing theme switcher (theme-change) for everyone, not
    just the admin. Off by default: most personal blogs don't want
    readers changing their look, but some do."""
    from soloblog.themes import all_choices, is_dark, own_css
    theme, dark = settings.get("theme") or "light", settings.get("theme_dark") or ""
    # a palette of your own that's since been deleted: the default again
    choices = all_choices()
    theme = theme if theme in choices else settings.DEFAULTS["theme"]
    dark = dark if not dark or dark in choices else settings.DEFAULTS["theme_dark"]
    mode = settings.get("theme_mode") or "auto"
    # your own palettes, on every page as daisyUI's are in the stylesheet
    css = own_css()
    if css:
        req.hdrs.append(Style(NotStr(css)))
    # always dark: the dark theme; otherwise the light one, and with "match
    # the device" the dark one too, for PICTURE_VERSIONS_JS to swap in
    req.htmlkw["data-theme"] = dark if mode == "dark" and dark else theme
    follow_device = mode == "auto" and dark and not is_dark(theme)
    # whether it's dark - images with a dark mode version follow it
    req.htmlkw["data-scheme"] = "dark" if is_dark(req.htmlkw["data-theme"]) else "light"
    if settings.get("smooth_scroll") == "1":
        req.htmlkw["data-smooth-scroll"] = "1"
    if settings.get("sidenotes") == "1":
        req.htmlkw["data-sidenotes"] = "1"
    if settings.get("page_animations") == "1":
        req.htmlkw["data-animate"] = "1"
        # how sections come into view (pages.SECTION_MOTIONS); fading is the stylesheet's own
        if settings.get("section_motion") not in ("", "fade", None):
            req.htmlkw["data-reveal"] = settings.get("section_motion")
    if settings.get("glass_effect") == "1":
        req.htmlkw["data-glass"] = "1"
    if settings.get("font_size") in ("small", "large"):
        req.htmlkw["data-font-size"] = settings.get("font_size")
    if follow_device:
        req.htmlkw["data-dark-theme"] = dark
    from soloblog import translate
    lang = translate.site_language()
    req.htmlkw["lang"] = i18n.ENGLISH_LANG.get(settings.get("english_spelling"), "en-US") if lang == "en" else lang
    if i18n.lang() != "en":
        req.htmlkw["data-i18n"] = json.dumps(i18n.script_words(), ensure_ascii=False)
    s = settings.get_all()
    path = req.url.path
    logged_in = auth.is_logged_in(session)
    # visitors only - never the admin's own browsing, never admin pages
    if not logged_in and not path.startswith(("/admin", "/login", "/setup")):
        tags = list(analytics_tags(s["analytics_provider"], s["analytics_id"]))
        if ads.consent_needed(s):
            # what tracks visitors waits for their yes (ads.py) - Google
            # Analytics, and custom code marked as needing it
            from soloblog.ui import glass_fill
            if ads.custom_head_gated(s):
                tags.append(NotStr(csp.nonce_scripts(s["custom_head"])))
            req.hdrs.append(ads.ConsentGate(tags))
            req.ftrs.append(ads.ConsentBanner(s, glass_fill(s)))
        else:
            req.hdrs.extend(tags)
    pinned_page = False
    # a page is at /about, or at /post/<slug> if a route has its slug
    slug = path[len("/post/"):] if path.startswith("/post/") else path[1:] if path.count("/") == 1 else ""
    if slug.strip("/"):
        row = posts.get_post(slug.strip("/"))
        pinned_page = bool(row and row["pinned"])
    if ads.ads_active(s, path, logged_in, pinned_page):
        req.hdrs.append(ads.adsense_script(s["adsense_client"]))
    # your favicon, else one made from your app icon or header icon, or
    # from the site title's first letter (appicon.py)
    from soloblog import appicon
    icon_v = appicon.version(s)
    req.hdrs.append(Link(rel="icon", href=settings.get("favicon_url") or f"/icon-32.png?v={icon_v}"))
    # Settings > Site
    req.hdrs.append(Link(rel="manifest", href="/manifest.webmanifest"))
    req.hdrs.append(Link(rel="apple-touch-icon", href=f"/icon-180.png?v={icon_v}"))
    if s["search_noindex"] == "1" or config.DEMO_MODE:
        req.hdrs.append(Meta(name="robots", content="noindex, nofollow"))
    public = not path.startswith(("/admin", "/login", "/setup"))
    if logged_in or path.startswith("/admin"):
        req.hdrs.append(Script(src=f"/admin.js?v={ADMIN_JS_VERSION}", nonce=csp.NONCE))
    if path == "/admin/settings":
        req.hdrs.append(Script(DESIGN_OPEN_EARLY_JS, nonce=csp.NONCE))
    if config.DEMO_MODE:
        req.hdrs.append(Script(DEMO_NOTE_EARLY_JS, nonce=csp.NONCE))
    # the chosen fonts - in the admin, only its editor's preview
    font_css = fonts.style(s, admin=path.startswith("/admin"))
    if font_css:
        req.hdrs.append(font_css)
    # the fediverse and the IndieWeb find the blog's account and endpoints here
    from soloblog import fediverse
    from soloblog import webmention
    if public and fediverse.enabled(s):
        req.hdrs.append(Link(rel="alternate", type=fediverse.CONTENT_TYPE,
                             href=f"{config.BASE_URL}{path}" if path.startswith("/post/") else fediverse.actor_id()))
    if public and webmention.receiving(s):
        req.hdrs.append(Link(rel="webmention", href=webmention.endpoint_url()))
    if path == "/" and not config.DEMO_MODE:
        # writing apps find "sign in with your site" and Micropub here
        from soloblog.routes import micropub as _micropub
        req.hdrs.extend(_micropub.discovery_links())
    mastodon = fediverse_creator(s.get("social_mastodon", ""))
    if public and mastodon:
        # Mastodon's "More from ..." byline on link previews of your posts
        req.hdrs.append(Meta(name="fediverse:creator", content=mastodon))
    if public:
        if s["google_site_verification"]:
            req.hdrs.append(Meta(name="google-site-verification", content=s["google_site_verification"]))
        if s["bing_site_verification"]:
            req.hdrs.append(Meta(name="msvalidate.01", content=s["bing_site_verification"]))
        # public pages only - broken custom code can't lock the admin out
        if s["custom_css"]:
            req.hdrs.append(Style(NotStr(s["custom_css"])))
        # (when it needs consent, it's in the gate above - and the admin, who
        # never answers the banner, doesn't run it)
        if s["custom_head"] and not ads.custom_head_gated(s):
            req.hdrs.append(NotStr(csp.nonce_scripts(s["custom_head"])))
    themed = (settings.get("visitor_theme_switching") == "1" or req.htmlkw.get("data-dark-theme")
              or req.htmlkw.get("data-scheme") == "dark")
    # inserted near the front so they run before daisyUI's CSS loads
    if themed or images.has_phone_versions():
        req.hdrs.insert(0, Script(PICTURE_VERSIONS_JS, nonce=csp.NONCE))
    if themed:
        req.hdrs.insert(0, Script(VISITOR_THEME_INIT_JS, nonce=csp.NONCE))
    if settings.get("visitor_theme_switching") == "1":
        req.hdrs.append(Script(src="/static/vendor/theme-change-2.5.0.js", nonce=csp.NONCE))


class SiteLanguage:
    """The language i18n.t() uses for this request: a translated page's
    own (/es/post/...), English for the admin, else the site's - and the
    path, for the admin sidebar. Set here, around the whole request, so
    every handler thread inherits them."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            from soloblog import translate
            path = scope["path"]
            code = path[1:3] if len(path) > 4 and path[3] == "/" and path[4:9] == "post/" else ""
            english = settings.get("english_spelling")
            if path.startswith(("/admin", "/login", "/setup", "/forgot-password", "/reset-password")):
                i18n.use("en", english)
            else:
                i18n.use(code if code in translate.LANGUAGES else translate.site_language(), english)
            # where this request is, for the admin sidebar (ui.AdminSidebar)
            from urllib.parse import parse_qs
            from soloblog.ui import set_request
            tab = parse_qs(scope.get("query_string", b"").decode("latin-1")).get("tab", [""])[0]
            set_request(path, tab)
            # the signed-in member, if any (members.py) - from their cookie,
            # once a request; never on the admin's own pages
            from soloblog import members
            member = None
            if not path.startswith("/admin") and members.enabled():
                from http.cookies import CookieError, SimpleCookie
                raw = next((v.decode("latin-1") for k, v in scope.get("headers", []) if k == b"cookie"), "")
                jar = SimpleCookie()
                try:
                    jar.load(raw)
                except CookieError:  # a browser's or a bot's malformed cookie: not signed in
                    jar = {}
                if members.COOKIE in jar:
                    member = members.from_cookie(jar[members.COOKIE].value)
            members.set_current(member)
            if member:
                # a page with a member's own details on it is never kept by a shared cache
                async def private(message):
                    if message["type"] == "http.response.start":
                        headers = list(message.get("headers", []))
                        if not any(k.lower() == b"cache-control" for k, _ in headers):
                            message = {**message, "headers": headers + [(b"cache-control", b"private, no-store")]}
                    await send(message)
                return await self.app(scope, receive, private)
        return await self.app(scope, receive, send)


_REQUESTS = logging.getLogger("soloblog.requests")
# only into the detailed log: the server's own output already lists each
# request (uvicorn's access log), and these aren't problems
_REQUESTS.propagate = False
_REQUESTS.addHandler(_detail_log)
# not worth a line each: files, and the host's own check every 30 seconds
_QUIET = ("/static/", "/uploads/", "/cards/", "/healthz", "/app.js", "/admin.js", "/favicon", "/robots.txt", "/apple-touch-icon")


class RequestLog:
    """Each page and admin action as a line of the detailed log (Site health >
    Log): "GET /post/x 200 35 ms". The path only - what follows a ? can be a
    reset or preview token - and never who asked (no address, no browser)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        if scope["type"] != "http" or path.startswith(_QUIET):
            return await self.app(scope, receive, send)
        started, status = time.monotonic(), {}

        async def noting(message):
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
            await send(message)
        try:
            await self.app(scope, receive, noting)
        finally:
            _REQUESTS.info("%s %s %s %d ms", scope.get("method", ""), path[:300], status.get("code", "-"),
                           (time.monotonic() - started) * 1000)


class RowsPerPage:
    """How many rows an admin list shows (ui.RowsPerPage): ?per= when it's
    10, 20 or 50, else what was last chosen for that page, kept in a cookie
    - a list has no setting of its own for it. Anything else is ignored."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        parts = scope.get("path", "").split("/")
        if scope["type"] != "http" or scope["method"] != "GET" or parts[:2] != ["", "admin"] or len(parts) < 3 \
                or not parts[2].isalpha():
            return await self.app(scope, receive, send)
        name = "per_" + parts[2].lower()[:30]
        asked = ui_post.rows_choice((parse_qs(scope.get("query_string", b"").decode("latin-1")).get("per") or [""])[0])
        kept = ui_post.rows_choice(Request(scope).cookies.get(name))
        token = ui_post._rows_chosen.set(asked or kept)

        async def keeping(message):
            if message["type"] == "http.response.start" and asked and asked != kept:
                cookie = f"{name}={asked}; Path=/admin; Max-Age=31536000; SameSite=Lax; HttpOnly"
                message["headers"] = [*message.get("headers", []),
                                      (b"set-cookie", (cookie + ("; Secure" if https_visit(scope) else "")).encode())]
            await send(message)
        try:
            await self.app(scope, receive, keeping)
        finally:
            ui_post._rows_chosen.reset(token)


class PictureSizes:
    """A visitor's page, its pictures given their width and height
    (images.with_sizes) - one place, whoever drew them: a post's words, a
    section, a cover, a theme's own header."""

    SKIP = ("/admin", "/uploads/", "/static/", "/api/")

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "GET" or scope["path"].startswith(self.SKIP):
            return await self.app(scope, receive, send)
        start, parts = None, []

        async def hold(message):
            nonlocal start
            if message["type"] == "http.response.start":
                kind = next((v for k, v in message.get("headers", []) if k.lower() == b"content-type"), b"")
                if not kind.startswith(b"text/html"):
                    return await send(message)
                start = message
                return
            if start is None or message["type"] != "http.response.body":
                return await send(message)
            parts.append(message.get("body", b""))
            if message.get("more_body"):
                return
            body = b"".join(parts)
            try:
                page = images.without_missing(body.decode("utf-8"), auth.is_logged_in(scope.get("session") or {}))
                body = images.with_sizes(page).encode("utf-8")
            except UnicodeDecodeError:
                pass
            headers = [(k, v) for k, v in start.get("headers", []) if k.lower() != b"content-length"]
            await send({**start, "headers": headers + [(b"content-length", str(len(body)).encode())]})
            await send({"type": "http.response.body", "body": body})

        await self.app(scope, receive, hold)


class SecurityHeaders:
    """Headers every response gets: no MIME sniffing, no framing by other
    sites (clickjacking), no full URLs leaked to other sites in the
    Referer, no camera, microphone, location, USB or payment requests from
    the page or anything embedded in it, and no other site's window
    keeping a hold on this one. The stylesheet's URL carries its build
    time (?v=...), so it can be cached for a year."""

    # the features embeds do use (autoplay, full screen, picture in
    # picture - reading.js) and passkeys stay as browsers have them
    HEADERS = [(b"x-content-type-options", b"nosniff"), (b"x-frame-options", b"SAMEORIGIN"),
               (b"referrer-policy", b"strict-origin-when-cross-origin"),
               (b"permissions-policy", b"camera=(), microphone=(), geolocation=(), usb=(), payment=()"),
               (b"cross-origin-opener-policy", b"same-origin")]

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        # in the request's own context - apply_site_config runs on a worker
        # thread, with a copy of it, where a reset wouldn't reach the route
        settings.new_request()
        static = scope["path"].startswith("/static/")
        # the admin's pages, and every page seen with the admin's cookie (its
        # edit buttons, drafts), are never kept by a shared cache or shown
        # again from the browser's after logging out - unless a route says
        cookies = next((v for k, v in scope.get("headers", []) if k == b"cookie"), b"")
        admin = scope["path"].startswith("/admin") or b"blog_session=" in cookies
        # HTTPS from now on, for a site that has it - a year, this host only
        hsts = config.IS_PROD and config.BASE_URL.startswith("https://")

        async def add_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", [])) + self.HEADERS
                has_cache = any(k.lower() == b"cache-control" for k, _ in headers)
                # never a 404 - a file added later must still be found
                if static and message["status"] < 400:
                    headers.append((b"cache-control", b"public, max-age=31536000, immutable"))
                elif admin and not static and not has_cache:
                    headers.append((b"cache-control", b"private, no-store"))
                if hsts:
                    headers.append((b"strict-transport-security", b"max-age=31536000"))
                message = {**message, "headers": headers}
            await send(message)
        return await self.app(scope, receive, add_headers)


class TooBigIsNotFound:
    """A number too big for the database in an address
    (/admin/revisions/99999999999999999999) raised OverflowError deep in
    a query - nothing has that id, so it's Not found, not a crash."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        started = False

        async def watch(message):
            nonlocal started
            started = started or message["type"] == "http.response.start"
            await send(message)
        try:
            await self.app(scope, receive, watch)
        except OverflowError as exc:
            if started:
                raise
            from starlette.requests import Request
            await error_page(Request(scope, receive), exc)(scope, receive, send)


class JsonBodies:
    """FastHTML reads a JSON body into a route's arguments before the
    route runs, and one that isn't JSON, or isn't an object ([1, 2],
    "words"), raised a server error on every address. Such a body is a
    Bad request, answered before FastHTML sees it. Only a body sent as
    exactly application/json - the one FastHTML parses; ActivityPub's and
    Stripe's types reach their routes untouched - and only to FastHTML's
    routes: the APIs (MCP, Micropub, Ghost's, our own) read their bodies
    themselves and answer in their own words, batches and all."""

    def __init__(self, app):
        self.app = app

    @staticmethod
    def _api(scope) -> bool:
        from starlette.routing import Match
        return any(type(route) is Route and route.matches(scope)[0] != Match.NONE for route in app.router.routes)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or dict(scope.get("headers", [])).get(b"content-type") != b"application/json" \
                or self._api(scope):
            return await self.app(scope, receive, send)
        messages, body = [], b""
        while True:
            message = await receive()
            messages.append(message)
            if message["type"] != "http.request":
                break
            body += message.get("body", b"")
            if not message.get("more_body"):
                break
        if body:
            try:
                ok = isinstance(json.loads(body), dict)
            except ValueError:  # not JSON, or not UTF-8
                ok = False
            if not ok:
                return await PlainTextResponse("Bad request", status_code=400)(scope, receive, send)

        async def replay():
            return messages.pop(0) if messages else await receive()
        return await self.app(scope, replay, send)


class BodyLimit:
    """How much a request may send: a form, a comment, a webhook is a few
    kilobytes, so anyone else is held to 16 MB - FastHTML reads a form
    before a route can say "log in first", and a multi-gigabyte upload to
    an admin address would fill the disk before being refused. An API key
    may send a media file; the logged-in admin, a whole backup to restore.
    Sits inside the session middleware, to know who's logged in."""
    ANYONE = 16 * 1024 * 1024

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or auth.is_logged_in(scope.get("session") or {}):
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        limit = (config.MAX_MEDIA_MB + 10) * 1024 * 1024 if b"authorization" in headers else self.ANYONE
        try:
            declared = int(headers.get(b"content-length", b"0"))
        except ValueError:
            declared = 0
        if declared > limit:
            return await PlainTextResponse("Too large", status_code=413)(scope, receive, send)
        seen = 0

        async def counted():
            nonlocal seen
            message = await receive()
            if message["type"] == "http.request":
                seen += len(message.get("body", b""))
                if seen > limit:  # no Content-Length, or a false one
                    return {"type": "http.disconnect"}
            return message
        return await self.app(scope, counted, send)


def https_visit(scope) -> bool:
    """The visit came over HTTPS - itself, or through a proxy that says so
    (X-Forwarded-Proto, as Fly, Railway and Cloudflare send) - or the site's
    address is https. Not "is this the Docker image": a home server opened at
    http://umbrel.local would get a Secure login cookie its browser never
    sends back, and its owner could never log in."""
    if scope.get("scheme") == "https" or config.BASE_URL.startswith("https://"):
        return True
    proto = dict(scope.get("headers") or []).get(b"x-forwarded-proto", b"")
    return proto.split(b",")[0].strip().lower() == b"https"


class BrowserOnlySession:
    """The login cookie, as it leaves: Secure on an HTTPS visit
    (https_visit), and without "Keep me signed in" (auth.BROWSER_ONLY) it
    loses its Max-Age, so it's gone when the browser closes. Outside the
    session middleware, which sets the cookie the same way for everyone."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        secure = https_visit(scope)

        def cookie(v):
            if not v.startswith(b"blog_session="):
                return v
            if (scope.get("session") or {}).get(auth.BROWSER_ONLY):
                v = re.sub(rb"; Max-Age=\d+", b"", v)
            return v + b"; secure" if secure else v

        async def sending(message):
            if message["type"] == "http.response.start":
                message["headers"] = [(k, cookie(v) if k == b"set-cookie" else v) for k, v in message["headers"]]
            await send(message)
        return await self.app(scope, receive, sending)


class SignedUndo:
    """A page's Undo button comes from ?undo= in its address (toast.js) and
    sends a POST as the admin. Only one this site signed (guards.sign_undo)
    reaches the page; any other is dropped from the address first, so a
    link from elsewhere can't put an action of its choosing under Undo."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["method"] in ("GET", "HEAD") \
                and b"undo" in scope.get("query_string", b""):
            from urllib.parse import parse_qsl, quote, urlencode
            from starlette.responses import RedirectResponse
            from soloblog.guards import undo_signed
            pairs = parse_qsl(scope["query_string"].decode("latin-1"), keep_blank_values=True)
            given = dict(pairs)
            if ("undo" in given or "undo_sig" in given) \
                    and not undo_signed(given.get("undo", ""), given.get("undo_sig", "")):
                rest = urlencode([(k, v) for k, v in pairs if k not in ("undo", "undo_sig")])
                to = quote(scope["path"]) + (f"?{rest}" if rest else "")
                return await RedirectResponse(to, status_code=303)(scope, receive, send)
        return await self.app(scope, receive, send)


class PresetPreview:
    """Shows the site in a settings preset without saving it (presets.py):
    the preview_preset cookie, for the logged-in admin - and, on the demo,
    for any visitor, so each can try them all without changing the site
    for anyone else. Inside the session middleware, to know who's in."""
    COOKIE = "preview_preset"

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        settings.preview(None)
        if scope["type"] == "http" and not scope["path"].startswith(("/static/", "/admin")):
            from http.cookies import CookieError, SimpleCookie
            raw = next((v.decode("latin-1") for k, v in scope.get("headers", []) if k == b"cookie"), "")
            jar = SimpleCookie()
            try:
                jar.load(raw)
            except CookieError:  # a malformed cookie: no preview
                jar = {}
            key = jar[self.COOKIE].value if self.COOKIE in jar else ""
            if key and (config.DEMO_MODE or auth.is_logged_in(scope.get("session") or {})):
                from soloblog import presets
                settings.preview(presets.preview_values(key))
            # a Design page's live preview (routes/admin_settings.design_preview): its
            # frame's address carries the page's unsaved form - for the admin only
            from urllib.parse import parse_qs
            query = parse_qs(scope.get("query_string", b"").decode("latin-1"))
            # or a preset, shown in that frame without the cookie a preset's own
            # Preview sets for browsing the whole site in it
            framed = query.get("preset_preview", [""])[0]
            if framed and (config.DEMO_MODE or auth.is_logged_in(scope.get("session") or {})):
                from soloblog import presets
                if presets.find(framed):
                    settings.preview(presets.preview_values(framed))
            token = query.get("design_preview", [""])[0]
            if token and auth.is_logged_in(scope.get("session") or {}):
                from soloblog.routes.admin_settings import design_preview_values
                values = design_preview_values(token)
                if values:
                    settings.preview(values)
        return await self.app(scope, receive, send)


class SameOriginOnly:
    """CSRF protection: a request that changes something (anything but
    GET/HEAD/OPTIONS) must come from a page on this site. Browsers send
    Origin on every such request (Referer as the fallback); another
    site's form or script can't fake it. A request with neither isn't
    from a browser page - no cookie-riding to defend against - so it
    passes. This sits on top of the session cookie's SameSite=Lax."""

    SAFE = ("GET", "HEAD", "OPTIONS")
    # server-to-server endpoints other sites are meant to POST to; they
    # never act on a session, so there's nothing for CSRF to ride
    OPEN = ("/ap/inbox", "/webmention", "/stripe/webhook")
    # the API takes only a key in a header, never the login cookie - a page
    # on another site can't ride on it, so there's nothing to check
    OPEN_PREFIXES = ("/api/", "/micropub", "/indieauth/token", "/indieauth/revoke", "/mcp", "/ghost/api/")

    def __init__(self, app):
        self.app = app

    @staticmethod
    def _allowed_hosts(scope):
        from urllib.parse import urlsplit
        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        hosts = {headers.get("host", ""), headers.get("x-forwarded-host", ""), urlsplit(config.BASE_URL).netloc}
        return {h.lower() for h in hosts if h}, headers

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] in self.SAFE or scope["path"] in self.OPEN \
                or scope["path"].startswith(self.OPEN_PREFIXES):
            return await self.app(scope, receive, send)
        from urllib.parse import urlsplit
        hosts, headers = self._allowed_hosts(scope)
        source = headers.get("origin") or headers.get("referer")
        if source is not None and (source == "null" or urlsplit(source).netloc.lower() not in hosts):
            response = PlainTextResponse("Cross-site request refused", status_code=403)
            return await response(scope, receive, send)
        return await self.app(scope, receive, send)


def error_page(req, exc):
    """404 and 500 for every route, not just a missing post - the site's
    own page (ErrorPage, ui) instead of a bare "404 Not Found".
    Falls back to plain text if even that can't render (a 500 caused
    by the database itself, say)."""
    from starlette.requests import ClientDisconnect
    from soloblog.ui import ErrorPage
    # the sender hung up partway through (scanners do it all day) -
    # nothing went wrong here, so not a problem, but the detailed log
    # keeps it in case an upload of the admin's was cut off on the way
    if isinstance(exc, ClientDisconnect):
        log.info("%s %s ended early: the sender hung up", req.method, req.url.path)
        return PlainTextResponse("", status_code=400)
    code = getattr(exc, "status_code", 500)
    # a number too big for the database, in an address (/admin/revisions/
    # 99999999999999999999) - nothing has that id, so it isn't there
    code = 404 if code == 404 or isinstance(exc, OverflowError) else 500
    if code == 500:
        log.error("%s %s failed", req.method, req.url.path, exc_info=exc)
    # one of the admin's own redirects (Settings > Site > Redirects), or
    # an address from the old blog, before an import - the post it was
    elif req.method in ("GET", "HEAD") and (moved := posts.custom_redirect(req.url.path, settings.get("redirects"))
                                             or posts.old_address(req.url.path)):
        return RedirectResponse(moved, status_code=301)
    try:
        session = req.scope.get("session") or {}
        apply_site_config(req, session)
        return ErrorPage(code, settings.get_all(), auth.is_logged_in(session), posts.list_pinned_tree())
    except Exception:  # the error page itself failed: plain words, never a second traceback page
        log.exception("the %s page couldn't be shown for %s %s", code, req.method, req.url.path)
        return PlainTextResponse("Not found" if code == 404 else "Something went wrong", status_code=code)


# The scripts every visitor's pages use, in the order they run. Served as
# one file (/app.js, below) instead of ~45 KB of inline <script> in every
# page: the browser downloads it once and caches it for a year, since its
# URL carries a hash of its contents and changes whenever any of them does.
# The order matters - later scripts use functions from earlier ones.
INDEX_SEARCH_JS = js.read("index_search.js")
# a setting's bar and Reset while it differs from its default - Post
# settings and the settings pages alike
CUSTOM_TAGS_JS = js.read("custom_tags.js")


SHARED_SCRIPTS = [ACTIONS_JS, PAGE_HELPERS_JS, CODE_COPY_JS, MASTODON_SHARE_JS, PANEL_STATE_JS, LIKE_JS, SCROLL_TOP_JS, TOAST_JS, COMMENTER_NAME_JS, CONFIRM_JS, POPOVER_DROPDOWN_JS, NAV_HOVER_JS, COUNTDOWN_JS, SELECT_JS, FOOTER_CLEARANCE_JS, CHROME_OFFSETS_JS, SAVE_STATUS_CLEAR_JS, LIVE_JS, SCROLL_RESTORE_JS, READING_JS, SIDENOTES_JS, ROW_LINKS_JS, ads.CONSENT_JS, captcha.CAPTCHA_JS, extcomments.EXT_COMMENTS_JS, LIGHTBOX_JS, MOTION_JS, TIMELINE_JS, PASSKEY_JS, BUSY_JS, SLIDES_JS]
APP_JS = "\n".join(script.strip() + "\n;" for script in SHARED_SCRIPTS)
APP_JS_VERSION = hashlib.sha256(APP_JS.encode("utf-8")).hexdigest()[:12]

# What only the admin's pages use (pickers, autosave, the unsaved-changes
# warning, the settings search), loaded after app.js on every /admin page
# and on any page while the admin is signed in. Visitors never download it.
ADMIN_SCRIPTS = [MEDIA_PICKER_JS, LINK_PICKER_JS, AUTOSAVE_JS, SORTABLE_JS, INDEX_SEARCH_JS, CUSTOM_TAGS_JS]
ADMIN_JS = "\n".join(script.strip() + "\n;" for script in ADMIN_SCRIPTS)
ADMIN_JS_VERSION = hashlib.sha256(ADMIN_JS.encode("utf-8")).hexdigest()[:12]


def app_css(req):
    # output.css less the daisyUI rules that slowed every page down
    # (themes.REMOVED_RULES); its address carries a hash of what's served
    return Response(themes.served_css()[0], media_type="text/css; charset=utf-8")


def app_js(req):
    return Response(APP_JS, media_type="text/javascript; charset=utf-8",
                    headers={"Cache-Control": "public, max-age=31536000, immutable"})


def admin_js(req):
    return Response(ADMIN_JS, media_type="text/javascript; charset=utf-8",
                    headers={"Cache-Control": "public, max-age=31536000, immutable"})


# Pages are made in a pool of threads - 40 by default, each holding a page
# in memory while it's made. Python makes them one core's worth at a time
# whatever the number, so 40 only raised the peak: 32 requests at once
# reached 510 MB, past what a 512 MB server leaves the app. 16 keeps it
# near 350 MB with the same pages a second, and enough places that a few
# slow requests (an upload, a fediverse delivery) don't hold the rest up.
PAGE_THREADS = 16


async def _cap_page_threads():
    import anyio.to_thread
    anyio.to_thread.current_default_thread_limiter().total_tokens = PAGE_THREADS


async def _one_copy():
    # here, not at import: a reloader imports the app too, but only the
    # process that serves it starts up
    from soloblog import health
    health.watch_for_second_copy()


app, rt = fast_app(
    on_startup=[_cap_page_threads, _one_copy],
    # page_meta (seo.py) writes the canonical link from BASE_URL - FastHTML's
    # own, from the request URL, would be a second, disagreeing one
    canonical=False,
    secret_key=config.SESSION_SECRET,
    session_cookie="blog_session",
    # FastHTML's default is a year; a login now lasts SESSION_DAYS unused
    max_age=config.SESSION_DAYS * 24 * 3600,
    # Secure is added on an HTTPS visit, by BrowserOnlySession
    sess_https_only=False,
    pico=False,
    # FastHTML's surreal.js and css-scope-inline aren't used anywhere here,
    # and it loads both from GitHub's moving @main branch - unpinned code
    # on every page for nothing. htmx itself stays (version-pinned).
    surreal=False,
    # htmx is served from static/vendor (below) instead of FastHTML's CDN
    # copy - pinned, minified, and no third-party host in the loop. That
    # also drops fasthtml.js, a set of helpers nothing here calls.
    htmx=False,
    # the admin's login first (guards.admin_guard), then the site's look
    before=[admin_guard, apply_site_config],
    exception_handlers={404: error_page, 500: error_page},
    # the theme's background on <body>: daisyUI's themes only define the
    # colours, and nothing else paints the page (or a phone's overscroll)
    bodykw=dict(cls="bg-base-100"),
    hdrs=(
        Meta(name="viewport",
             content="width=device-width, initial-scale=1, viewport-fit=cover, interactive-widget=resizes-content"),
        Meta(name="color-scheme", content="light dark"),
        Link(rel="alternate", type="application/rss+xml", title="RSS", href="/rss"),
        Link(rel="alternate", type="application/atom+xml", title="Atom", href="/atom.xml"),
        Link(rel="alternate", type="application/feed+json", title="JSON Feed", href="/feed.json"),
        Link(rel="stylesheet", href=f"/static/css/output.css?v={themes.served_css()[1]}"),
        # htmx never runs a <script> inside swapped-in HTML - every live
        # update's behavior already lives in app.js (see ACTIONS_JS)
        Meta(name="htmx-config", content='{"allowScriptTags": false}'),
        Script(src="/static/vendor/htmx-2.0.7.min.js", nonce=csp.NONCE),
        # every shared script in one file (APP_JS below), cached like the
        # stylesheet. Not deferred - it runs where the inline copies did.
        Script(src=f"/app.js?v={APP_JS_VERSION}", nonce=csp.NONCE),
    ),
)

# the public demo: a fresh copy of the sample blog on every start
if config.DEMO_MODE:
    from soloblog import demo as _demo
    _demo.boot()
# a fresh, empty disk with a bucket configured: bring the newest backup
# back first, so the migrations below upgrade the restored database
storage.restore_on_boot()
run_migrations()
# the address saved at first-time setup, when the host doesn't set one
settings.use_site_url()
posts.reindex_from_disk()
# an uploaded backup left unrestored for a day goes
from soloblog import backup as _backup  # noqa: E402
_backup.staged_restore()
# announces posts to fediverse followers and linked pages (publishing.py)
from soloblog import publishing  # noqa: E402
publishing.start()
# Site health's daily checks and its alerts (health_remote.py)
from soloblog import health_remote  # noqa: E402
health_remote.start()
# inside the session middleware (the others go outside it), so it knows
# whether the admin is logged in
from starlette.middleware import Middleware  # noqa: E402
app.user_middleware.append(Middleware(BodyLimit))
app.user_middleware.append(Middleware(PresetPreview))
app.user_middleware.append(Middleware(TooBigIsNotFound))
# inside BodyLimit, so a huge body is refused before it's read whole
app.user_middleware.append(Middleware(JsonBodies))
app.add_middleware(BrowserOnlySession)
app.add_middleware(storage.ChangeTracker)
app.add_middleware(SameOriginOnly)
app.add_middleware(SignedUndo)
if config.DEMO_MODE:
    app.add_middleware(_demo.DemoGuard)
app.add_middleware(PictureSizes)
app.add_middleware(RowsPerPage)
app.add_middleware(RequestLog)
app.add_middleware(SecurityHeaders)
app.add_middleware(SiteLanguage)
# runs on the whole page before it's compressed (csp.py)
app.add_middleware(csp.ContentSecurityPolicy)
# pages carry ~40KB of inline script and markup - compress anything sizeable
app.add_middleware(GZipMiddleware, minimum_size=1000)
# outermost: the demo picks a visitor's own copy before anything reads the site
if config.DEMO_MODE:
    app.add_middleware(_demo.Sandbox)
# a pending automatic backup still gets written when the server stops
atexit.register(storage.flush)
# the bucket's images sealed again, in the background, when
# BACKUP_PASSPHRASE has been set, changed or removed since the last start
storage._mirror(storage.reseal_images)

# instructions for whoever is setting the site up, not log entries - they
# show whatever LOG_LEVEL is
if not auth.admin_exists() and auth.setup_token() == config.SETUP_TOKEN:
    print("\n[setup] No admin account yet. Visit /setup and use SETUP_TOKEN from your host's settings.\n")
elif not auth.admin_exists():
    if config.SETUP_TOKEN:
        print("\n[setup] SETUP_TOKEN is shorter than 16 characters, so it isn't used.")
    print(f"\n[setup] No admin account yet. Visit /setup and use this token:\n[setup] {auth.setup_token()}\n"
          f"[setup] (It's also in setup-token.txt in the data folder.)\n")
    auth.write_setup_token()
elif config.RESET_PASSWORD:
    print(f"\n[reset] RESET_PASSWORD is set. Choose a new password here (valid for 24 hours):\n"
          f"[reset] {config.BASE_URL}/reset-password?token={auth.start_reset(24 * 60)}\n"
          f"[reset] Then remove RESET_PASSWORD and restart.\n")
if auth.admin_exists():
    auth.forget_setup_token()

# each route module owns its own APIRouter, merged in here - keeps the
# route files independent of app wiring and of each other
from soloblog.routes import (public, auth_routes, editor, admin_settings, help_routes, backup_routes,  # noqa: E402
                             security_routes, comments_routes, media, stats, contact, welcome, fediverse_routes,
                             newsletter_routes, health, members_routes, api, micropub, mcp, ghost)

for mod in (public, auth_routes, editor, admin_settings, help_routes, backup_routes, security_routes,
            comments_routes, media, stats, contact, welcome, fediverse_routes, newsletter_routes, health,
            members_routes, micropub):
    mod.ar.to_app(app)
api.mount(app)
micropub.mount(app)
mcp.mount(app)
ghost.mount(app)

# fast_app() always registers a catch-all static-file route for common
# extensions (including .xml and .txt) ahead of anything we add - it'll
# swallow our dynamic routes before they ever see the request. Move
# ours to the front of the list so they're tried first.
#
# And that catch-all goes entirely. It served any file with a common
# extension (.txt, .yml, .zip, .png, .html...) from the working
# directory - the source tree, and a data/ folder kept there - and an
# encoded "../" (%2e%2e) walked out of it to anywhere on the disk. Only
# static/ is public, through Starlette's StaticFiles, which refuses any
# path that resolves outside it.
_dynamic_paths = {"/sitemap.xml", "/robots.txt", "/favicon.ico", "/ads.txt", "/manifest.webmanifest", "/icon-{size}.png", "/card/{slug}.png", "/card.png", "/uploads/{filename}", "/admin/media/trash-file/{filename}",
                   "/admin/media/details/{filename}"}
_catch_all = "/{fname:path}.{ext:static}"
_ours = [r for r in app.router.routes if getattr(r, "path", None) in _dynamic_paths]
_rest = [r for r in app.router.routes if getattr(r, "path", None) not in _dynamic_paths | {_catch_all}]
app.router.routes = [Route("/static/css/output.css", app_css),
                     Mount("/static", app=StaticFiles(directory="static"), name="static"),
                     Route("/app.js", app_js), Route("/admin.js", admin_js)] + _ours + _rest

# a page pinned to the header or footer lives at /<slug> (/about). This
# route comes after every other one, so a page can never shadow a real
# address; a slug one of them already uses stays at /post/<slug>.
posts.RESERVED_PATHS.update(
    part for part in (getattr(r, "path", "").split("/")[1] if getattr(r, "path", "").count("/") else ""
                      for r in app.router.routes) if part and "{" not in part)


@rt("/{slug}")
def page_at_root(req, session, hdrs, slug: str, preview: str = ""):
    row = posts.get_post(slug)
    if not row or posts.url_for(row) != f"/{slug}":
        # one of the admin's own redirects; /my-post from an old blog, or
        # any post's slug: the post itself
        if moved := posts.custom_redirect(f"/{slug}", settings.get("redirects")) or posts.old_address(f"/{slug}"):
            return RedirectResponse(moved, status_code=301)
        from soloblog.ui import ErrorPage
        return FtResponse(ErrorPage(404, settings.get_all(), auth.is_logged_in(session), posts.list_pinned_tree()),
                          status_code=404)
    return public.view_post(req, session, hdrs, slug, preview=preview)

if __name__ == "__main__":
    serve(reload=not config.IS_PROD)
