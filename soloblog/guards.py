from starlette.responses import JSONResponse, RedirectResponse, Response
from soloblog import auth


def require_login(session, request=None):
    """Returns (True, None) or (False, response).

    `request` is optional and only matters for HTMX-submitted forms: a
    fetch()-based htmx request follows a normal redirect transparently,
    which would dump the destination page's raw HTML into whatever
    small element the form was targeting instead of actually getting
    there. Passing the request lets an expired-session redirect go out
    as HX-Redirect instead (htmx does a real browser navigation for
    that), but only when the request actually came from htmx - a
    plain page load still gets a normal 303."""
    if not auth.admin_exists():
        return False, _redirect("/setup", request)
    if not auth.is_logged_in(session):
        return False, _redirect("/login", request)
    return True, None


# the one admin address open to everyone: on the demo, any visitor can try
# a preset (app.PresetPreview), and this is how they stop
ADMIN_OPEN = {"/admin/presets/stop"}


def admin_guard(req, session):
    """Runs before every request (app.py, fast_app's before=): everything
    under /admin needs the admin logged in, so a new admin page is
    protected without asking."""
    path = req.url.path
    if not (path == "/admin" or path.startswith("/admin/")) or path in ADMIN_OPEN:
        return None
    resp = require_login(session, req)[1]
    # a script's own request (fetch: passkeys, an upload, a revision) gets
    # an answer it can read, not the login page; a page or an htmx swap is
    # sent there (require_login)
    if resp is not None and req.headers.get("sec-fetch-mode", "navigate") != "navigate" \
            and req.headers.get("hx-request") != "true":
        return JSONResponse({"error": "Log in again"}, status_code=401)
    return resp


def _redirect(url, request):
    if request is not None and request.headers.get("hx-request") == "true":
        return Response(status_code=200, headers={"HX-Redirect": url})
    return RedirectResponse(url, status_code=303)


def is_local_path(target: str) -> bool:
    """A redirect target that stays on this site. "/admin" yes; "//evil.com"
    and "/\\evil.com" no - browsers treat both as another host."""
    return bool(target) and target.startswith("/") and not target.startswith(("//", "/\\"))


def status_redirect(path: str, message: str, kind: str = "success", undo: str = ""):
    """The one way an admin action reports back: redirect to path with the
    message (and optionally an undo action) in the query string, where the
    page's status slot picks it up - showStatus in app.py. undo is a local
    POST path with its fields as query params, e.g.
    "/admin/posts/restore?slug=x&return_to=/admin/posts"."""
    from urllib.parse import quote
    from starlette.responses import RedirectResponse
    base, _, frag = path.partition("#")
    extra = f"toast={quote(message)}&toast_type={kind}"
    if undo and is_local_path(undo):
        extra += f"&undo={quote(undo)}&undo_sig={sign_undo(undo)}"
    sep = "&" if "?" in base else "?"
    return RedirectResponse(f"{base}{sep}{extra}" + (f"#{frag}" if frag else ""), status_code=303)


UNDO_LIFE = 300


def sign_undo(undo: str, now: float | None = None) -> str:
    """Says this site offered that Undo, a moment ago. The button sends a
    POST as the admin, so an address can't be allowed to make one up."""
    import hashlib
    import hmac
    import time
    from soloblog import config
    until = int((time.time() if now is None else now) + UNDO_LIFE)
    made = hmac.new(config.SESSION_SECRET.encode(), f"{until}:{undo}".encode(), hashlib.sha256).hexdigest()
    return f"{until}.{made}"


def undo_signed(undo: str, sig: str) -> bool:
    import hmac
    import time
    until, _, made = (sig or "").partition(".")
    if not undo or not until.isdigit() or int(until) < time.time():
        return False
    return hmac.compare_digest(sign_undo(undo, int(until) - UNDO_LIFE), f"{until}.{made}")


def undo_url(path: str, **fields) -> str:
    from urllib.parse import urlencode
    return f"{path}?{urlencode(fields)}"
