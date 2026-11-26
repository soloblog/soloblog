"""Posting from writing apps: Micropub (w3.org/TR/micropub), with "sign
in with your site" (IndieAuth, indieauth.spec.indieweb.org) to connect
them.

Connecting: the app is given the site's address. It finds the endpoints
in the home page's <link>s (Discovery, app.py), sends the admin here to
approve it (/indieauth/auth, logged in, a page with the app's name and
what it may do), and swaps the one-time code it gets back for an API key
(/indieauth/token, with PKCE). The key is an ordinary one (apikeys.py),
listed in Settings > Security, revocable like any other.

Posting: /micropub takes an entry as a form or JSON, and every save goes
through posts.write, the editor's own. HTML from an app becomes markdown;
photos land in the media library. A post arrives as the app asks -
published or a draft - unless the key only writes drafts, or Settings
keeps publishing to the admin (apikeys.may_publish).

The token, micropub and media endpoints are plain Starlette routes, for
the same reason as the API's (api.py). The approval page is FastHTML."""
import base64
import hashlib
import json
import logging
import re
import secrets
from datetime import timedelta
from soloblog.tz import utcnow
from html import unescape
from urllib.parse import urlencode, urlsplit

from fasthtml.common import *
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from soloblog import apikeys
from soloblog import auth
from soloblog import config
from soloblog import images
from soloblog import netguard
from soloblog import posts
from soloblog import ratelimit
from soloblog import settings
from soloblog.db import get_db
from soloblog.routes.api import _key as api_key, _author, MAX_IMAGE

log = logging.getLogger(__name__)
ar = APIRouter()
CODE_MINUTES = 10
# what Micropub asks for, and the key scope each needs at least
WANTS_PUBLISH = {"create", "update", "delete", "undelete"}


def me() -> str:
    """The site, as IndieAuth names it - its home page."""
    return config.BASE_URL + "/"


def discovery_links():
    """For the home page's <head>: where apps find the endpoints."""
    return (Link(rel="indieauth-metadata", href=f"{config.BASE_URL}/.well-known/oauth-authorization-server"),
            Link(rel="authorization_endpoint", href=f"{config.BASE_URL}/indieauth/auth"),
            Link(rel="token_endpoint", href=f"{config.BASE_URL}/indieauth/token"),
            Link(rel="micropub", href=f"{config.BASE_URL}/micropub"))


# ---- the app asking to connect

def _valid_client(client_id: str) -> bool:
    """An http(s) address with a host - no password, no #fragment, no ..
    tricks (the IndieAuth client identifier rules, simply)."""
    try:
        parts = urlsplit(client_id)
    except ValueError:
        return False
    return (parts.scheme in ("https", "http") and bool(parts.hostname) and not parts.username
            and not parts.password and not parts.fragment and "/." not in parts.path and len(client_id) < 500)


def _origin(url: str) -> tuple:
    p = urlsplit(url)
    return p.scheme, (p.hostname or "").lower(), p.port


def client_info(client_id: str) -> dict:
    """The app's name and the addresses it may be sent back to, from its own
    page (JSON client metadata, or HTML with <title> and
    <link rel="redirect_uri">) - fetched from the public internet only. An
    app whose page can't be read is named by its host."""
    info = {"name": urlsplit(client_id).hostname or client_id, "redirect_uris": []}
    try:
        raw = netguard.fetch(client_id, max_bytes=200_000, timeout=5).decode("utf-8", "replace")
    except Exception as e:  # anything a server can answer with - see DEVELOPMENT.md > Errors
        log.info("couldn't read the app's page at %s - named by its host: %s", info["name"], e)
        return info
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            info["name"] = str(data.get("client_name") or info["name"])[:80]
            info["redirect_uris"] = [u for u in data.get("redirect_uris") or [] if isinstance(u, str)]
            return info
    except ValueError:
        pass
    name = re.search(r'class="[^"]*\bh-app\b[^"]*"[^>]*>.*?class="[^"]*\bp-name\b[^"]*"[^>]*>([^<]{1,80})<', raw, re.S) \
        or re.search(r"<title[^>]*>([^<]{1,80})</title>", raw, re.I)
    if name:
        info["name"] = unescape(name.group(1)).strip() or info["name"]
    info["redirect_uris"] = re.findall(r'<link[^>]+rel="[^"]*\bredirect_uri\b[^"]*"[^>]+href="([^"]+)"', raw, re.I) + \
        re.findall(r'<link[^>]+href="([^"]+)"[^>]+rel="[^"]*\bredirect_uri\b[^"]*"', raw, re.I)
    return info


def _redirect_allowed(client_id: str, redirect_uri: str, info: dict) -> bool:
    """Back to the app's own site - or to an address the app itself lists.
    Anything else could hand the key to someone else."""
    if not _valid_client(redirect_uri):
        return False
    if _origin(redirect_uri) == _origin(client_id) or redirect_uri in info["redirect_uris"]:
        return True
    # an app on the computer itself listens on a port it picks each time
    # (RFC 8252): a listed loopback address matches on any port
    loopback = ("127.0.0.1", "localhost", "::1")
    want = urlsplit(redirect_uri)
    return want.scheme == "http" and want.hostname in loopback and any(
        urlsplit(u).scheme == "http" and urlsplit(u).hostname == want.hostname and urlsplit(u).path == want.path
        for u in info["redirect_uris"])


def _scope_for(requested: str) -> str:
    """What to suggest on the approval page, from what the app asked."""
    words = set(requested.split())
    if words & WANTS_PUBLISH:
        return "publish"
    if words & {"draft", "media"}:
        return "draft"
    return "read"


def _back(redirect_uri: str, **params) -> RedirectResponse:
    params["iss"] = config.BASE_URL
    sep = "&" if "?" in redirect_uri else "?"
    return RedirectResponse(redirect_uri + sep + urlencode({k: v for k, v in params.items() if v is not None}),
                            status_code=302)


def _ask_page(error: str = "", **ctx):
    s = settings.get_all()
    from soloblog.ui import RadioGroupField, FIELD_GAP
    if error:
        body = (H1("Can't connect this app", cls="text-xl font-bold"), P(error, cls="text-sm text-base-content/70"),
                A("Back to your site", href="/", cls="btn btn-sm"))
    else:
        chosen = ctx["scope"]
        body = (
            H1(f"Connect {ctx['name']}?", cls="text-xl font-bold"),
            P(Strong(ctx["name"]), " (", Span(urlsplit(ctx["client_id"]).hostname, cls="font-mono"),
              ") wants to work on ", Strong(s.get("site_title") or "your site"), ".", cls="text-sm"),
            Form(
                *[Input(type="hidden", name=k, value=ctx[k]) for k in
                  ("client_id", "redirect_uri", "state", "code_challenge", "code_challenge_method", "requested")],
                RadioGroupField("What the app can do", "scope",
                                [(k, f"{apikeys.SCOPE_LABELS[k]} - {apikeys.SCOPE_HELP[k]}") for k in apikeys.SCOPES],
                                chosen, help="The app asked for: " + (ctx["requested"] or "signing in only") + ".",
                                cls=FIELD_GAP),
                P("Everything the app posts arrives as a draft.",
                  cls="text-xs text-base-content/60 mb-2") if s.get("apps_publish") == "none" else None,
                P("You can disconnect it any time in ",
                  A("API keys", href="/admin/settings?tab=integrations&panel=integrations-apikeys", target="_blank",
                    rel="noopener", cls="link"), ".", cls="text-xs text-base-content/60"),
                Div(Button("Cancel", type="submit", name="decision", value="deny", cls="btn btn-sm"),
                    Button("Connect", type="submit", name="decision", value="allow", cls="btn btn-primary btn-sm"),
                    cls="flex justify-end gap-2 mt-4"),
                action="/indieauth/auth", method="post"),
        )
    from soloblog.ui import Layout
    return Layout(Div(Div(*body, cls="card-body p-6 gap-3"), cls="card card-border bg-base-100 max-w-lg mx-auto"),
                  settings=s, logged_in=True, pinned_tree=posts.list_pinned_tree())


def _check_request(client_id, redirect_uri, code_challenge, code_challenge_method):
    """(app info, None), or (None, why it can't go on)."""
    if config.DEMO_MODE:
        return None, "Apps can't connect to the demo - it's shared with everyone."
    if not _valid_client(client_id):
        return None, "The app didn't say which app it is."
    if not code_challenge or code_challenge_method != "S256":
        return None, "The app needs to prove it's the one asking (PKCE with S256), and it didn't."
    info = client_info(client_id)
    if not _redirect_allowed(client_id, redirect_uri, info):
        return None, "The app asked to be sent back to a URL that isn't its own."
    return info, None


@ar.get("/indieauth/auth")
def indieauth_ask(req, session, client_id: str = "", redirect_uri: str = "", state: str = "",
                  code_challenge: str = "", code_challenge_method: str = "", scope: str = "",
                  response_type: str = "code"):
    if not auth.admin_exists():
        return RedirectResponse("/setup", status_code=303)
    if not auth.is_logged_in(session):
        # back here once logged in, through two-factor or a passkey
        session["after_login"] = req.url.path + "?" + req.url.query
        return RedirectResponse("/login", status_code=303)
    info, error = _check_request(client_id, redirect_uri, code_challenge, code_challenge_method)
    if error:
        return _ask_page(error=error)
    if response_type not in ("code", "id"):
        return _back(redirect_uri, error="unsupported_response_type", state=state)
    requested = " ".join(w for w in scope.split() if re.fullmatch(r"[a-z_]{1,20}", w))[:200]
    return _ask_page(client_id=client_id, redirect_uri=redirect_uri, state=state[:500],
                     code_challenge=code_challenge, code_challenge_method=code_challenge_method,
                     requested=requested, scope=_scope_for(requested), name=info["name"])


@ar.post("/indieauth/auth")
async def indieauth_decide(req, session):
    form = await req.form()
    if form.get("grant_type") == "authorization_code":
        # an app signing in only - its code swapped for who the site is
        return JSONResponse(*_redeem(form, profile_only=True))
    if not auth.is_logged_in(session):
        return RedirectResponse("/login", status_code=303)
    client_id, redirect_uri = form.get("client_id", ""), form.get("redirect_uri", "")
    info, error = _check_request(client_id, redirect_uri, form.get("code_challenge", ""),
                                 form.get("code_challenge_method", ""))
    if error:
        return _ask_page(error=error)
    state = form.get("state", "")
    if form.get("decision") != "allow":
        return _back(redirect_uri, error="access_denied", state=state)
    scope = form.get("scope") if form.get("scope") in apikeys.SCOPES else "read"
    code = secrets.token_urlsafe(32)
    now = utcnow()
    db = get_db()
    db.execute("INSERT INTO indieauth_codes (code_hash, client_id, client_name, redirect_uri, code_challenge, scope, "
               "requested, created_at, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
               (hashlib.sha256(code.encode()).hexdigest(), client_id, info["name"], redirect_uri,
                form.get("code_challenge", ""), scope, form.get("requested", "")[:200], now.isoformat(),
                (now + timedelta(minutes=CODE_MINUTES)).isoformat()))
    db.commit()
    return _back(redirect_uri, code=code, state=state)


# ---- the app fetching its key

def _redeem(form, profile_only=False):
    """(json, status) for a code: once, unexpired, the same app and address,
    and the PKCE verifier that matches."""
    code, verifier = form.get("code", ""), form.get("code_verifier", "")
    db = get_db()
    row = db.execute("SELECT * FROM indieauth_codes WHERE code_hash=?",
                     (hashlib.sha256(code.encode()).hexdigest(),)).fetchone()
    bad = ({"error": "invalid_grant", "error_description": "That code isn't valid any more"}, 400)
    if not row or row["used_at"] or row["expires_at"] < utcnow().isoformat():
        return bad
    # used now, whatever happens next - a code is good for one try
    db.execute("UPDATE indieauth_codes SET used_at=? WHERE id=?", (utcnow().isoformat(), row["id"]))
    db.commit()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    if (form.get("client_id") != row["client_id"] or form.get("redirect_uri") != row["redirect_uri"]
            or not verifier or not secrets.compare_digest(challenge, row["code_challenge"])):
        return bad
    if profile_only:
        return {"me": me()}, 200
    key = apikeys.create(f"{row['client_name']} (connected)", row["scope"], client_id=row["client_id"])
    return {"access_token": key, "token_type": "Bearer", "scope": row["requested"] or row["scope"], "me": me()}, 200


async def token_endpoint(req):
    if config.DEMO_MODE:
        return JSONResponse({"error": "access_denied"}, status_code=403)
    if req.method == "GET":
        # an old-style check of a key: who it's for and what it may do
        key, err = api_key(req, "read", via="micropub")
        if err:
            return err
        return JSONResponse({"me": me(), "client_id": key["client_id"], "scope": key["scope"]})
    if not ratelimit.hit(f"ip:{ratelimit.client_ip(req)}", "indieauth-token", limit=30, window_minutes=15):
        return JSONResponse({"error": "slow_down"}, status_code=429)
    form = await req.form()
    if form.get("action") == "revoke":
        apikeys.revoke_key(form.get("token", ""))
        return Response(status_code=200)
    if form.get("grant_type") != "authorization_code":
        return JSONResponse({"error": "unsupported_grant_type"}, status_code=400)
    data, status = _redeem(form)
    return JSONResponse(data, status_code=status, headers={"Cache-Control": "no-store"})


async def revoke_endpoint(req):
    form = await req.form()
    apikeys.revoke_key(form.get("token", ""))
    return Response(status_code=200)


def metadata(req):
    base = config.BASE_URL
    return JSONResponse({
        "issuer": base, "authorization_endpoint": f"{base}/indieauth/auth",
        "token_endpoint": f"{base}/indieauth/token", "revocation_endpoint": f"{base}/indieauth/revoke",
        "code_challenge_methods_supported": ["S256"], "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"], "authorization_response_iss_parameter_supported": True,
        "scopes_supported": ["create", "update", "delete", "undelete", "media", "draft", "profile"],
    })


# ---- Micropub

def _token(req, form=None):
    """As Micropub allows, a key in a form's access_token field (never the
    address) - the key check (api._key) takes it when there's no header."""
    if form is not None and isinstance(form.get("access_token"), str):
        req.state.access_token = form.get("access_token")
    return req


def _mp_error(status, error, description):
    return JSONResponse({"error": error, "error_description": description}, status_code=status)


def _slug_from_url(url: str):
    """The post an address on this site is for."""
    path = urlsplit(url or "").path
    slug = path[len("/post/"):] if path.startswith("/post/") else path.strip("/")
    return slug if slug and "/" not in slug and posts.get_post(slug) else None


def _values(props: dict, name: str) -> list:
    v = props.get(name, [])
    return v if isinstance(v, list) else [v]


def _content(value) -> str:
    """Micropub content - plain text, or {"html": ...} turned to markdown."""
    if isinstance(value, dict):
        if "html" in value:
            from soloblog.importers import html_to_markdown
            return html_to_markdown(str(value["html"]))
        return str(value.get("value", ""))
    return str(value or "")


def _title_from(body: str) -> str:
    """A note has no name - its title is how it begins."""
    line = next((ln for ln in body.splitlines() if ln.strip() and not ln.strip().startswith("![")), "")
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", line)            # images
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)        # links: their words
    text = re.sub(r"^[\s#>*+-]+|[*_`]{1,3}", "", text).strip()    # headings, quotes, lists, emphasis
    if len(text) > 70:
        text = text[:70].rsplit(" ", 1)[0] + "…"
    return text or "Note"


def _photo(value, uploads) -> str:
    """A photo as markdown: an uploaded file, an image already in the media
    library, or an address fetched into it (public internet only)."""
    alt = ""
    if isinstance(value, dict):
        value, alt = value.get("value", ""), str(value.get("alt", ""))
    url = str(value or "")
    if not url:
        return ""
    if url.startswith(config.BASE_URL + "/uploads/") or url.startswith("/uploads/"):
        saved = url.replace(config.BASE_URL, "", 1)
    else:
        try:
            saved = images.save_upload(netguard.fetch(url, max_bytes=MAX_IMAGE), url.rsplit("/", 1)[-1].split("?")[0])
        except Exception as e:  # another server, then Pillow - more than either documents
            log.info("a Micropub photo from %s was left out: %s", urlsplit(url).hostname, e)
            return ""
    return f"![{alt}]({saved})"


async def _entry(req):
    """(properties dict, uploaded photos, action dict or None, error)."""
    kind = req.headers.get("content-type", "")
    if kind.startswith("application/json"):
        try:
            data = json.loads(await req.body() or b"{}")
        except ValueError:
            return None, [], None, _mp_error(400, "invalid_request", "That isn't JSON")
        if not isinstance(data, dict):
            return None, [], None, _mp_error(400, "invalid_request", "Send a JSON object")
        if data.get("action"):
            return None, [], data, None
        if data.get("type") not in (["h-entry"], None):
            return None, [], None, _mp_error(400, "invalid_request", "Soloblog takes entries (h-entry) only")
        props = data.get("properties") or {}
        return (props if isinstance(props, dict) else {}), [], None, None
    form = await req.form()
    _token(req, form)
    if form.get("action"):
        return None, [], {"action": form.get("action"), "url": form.get("url")}, None
    if form.get("h", "entry") != "entry":
        return None, [], None, _mp_error(400, "invalid_request", "Soloblog takes entries (h-entry) only")
    props, uploads = {}, []
    for k in set(form.keys()):
        if k in ("h", "access_token"):
            continue
        values = form.getlist(k)
        name = k[:-2] if k.endswith("[]") else k
        for v in values:
            if hasattr(v, "read"):
                uploads.append(v)
            else:
                props.setdefault(name, []).append(v)
    return props, uploads, None, None


async def micropub(req):
    if req.method == "GET":
        key, err = api_key(req, "read", via="micropub")
        if err:
            return err
        q = req.query_params.get("q", "")
        if q == "config":
            return JSONResponse({"media-endpoint": f"{config.BASE_URL}/micropub/media", "syndicate-to": [],
                                 "post-types": [{"type": "note", "name": "Note"}, {"type": "article", "name": "Post"},
                                                {"type": "photo", "name": "Photo"}],
                                 "q": ["config", "source", "syndicate-to", "category"]})
        if q == "syndicate-to":
            return JSONResponse({"syndicate-to": []})
        if q == "category":
            return JSONResponse({"categories": [t for t, _ in posts.tag_counts_all()]})
        if q == "source":
            slug = _slug_from_url(req.query_params.get("url", ""))
            if not slug:
                return _mp_error(400, "invalid_request", "No post at that URL")
            row = posts.get_post(slug)
            props = {"name": [row["title"]], "content": [posts.load_post_body(slug)],
                     "category": [t.strip() for t in (row["tags"] or "").split(",") if t.strip()],
                     "summary": [row["summary"]] if row["summary"] else [],
                     "post-status": ["published" if row["published"] else "draft"],
                     "published": [row["created_at"]], "url": [config.BASE_URL + posts.url_for(row)]}
            wanted = req.query_params.getlist("properties[]") or req.query_params.getlist("properties")
            if wanted:
                return JSONResponse({"properties": {k: v for k, v in props.items() if k in wanted}})
            return JSONResponse({"type": ["h-entry"], "properties": props})
        return _mp_error(400, "invalid_request", "Ask for q=config, source, syndicate-to or category")

    props, uploads, action, err = await _entry(req)
    if err:
        return err
    if action:
        return await _act(req, action)
    key, err = api_key(req, "draft", via="micropub")
    if err:
        return err
    body = "\n\n".join(_content(c) for c in _values(props, "content") if c)
    photos = [md for md in (_photo(p, uploads) for p in _values(props, "photo")) if md]
    for upload in uploads:
        data = await upload.read(MAX_IMAGE + 1)
        if len(data) <= MAX_IMAGE:
            try:
                photos.append(f"![]({images.save_upload(data, upload.filename or '')})")
            except Exception as e:  # Pillow, reading what anyone sent - more than it documents
                log.info("a photo sent by Micropub was left out: %s", e)
    body = "\n\n".join(x for x in (body, *photos) if x)
    title = str((_values(props, "name") or [""])[0]).strip()
    bookmark = str((_values(props, "bookmark-of") or [""])[0])
    fields = {"title": title or (bookmark if bookmark and not body else _title_from(body)), "body": body,
              "tags": ", ".join(str(t) for t in _values(props, "category") if str(t).strip()),
              "summary": str((_values(props, "summary") or [""])[0])}
    if bookmark.startswith(("http://", "https://")):
        fields["link_url"] = bookmark
    wants_live = str((_values(props, "post-status") or ["published"])[0]) != "draft"
    # live only when the app asks and may publish (its key, and Settings)
    fields["published"] = wants_live and apikeys.allows(key, "publish")
    slug = posts.write(None, _author(), **fields)
    wanted_slug = str((_values(props, "mp-slug") or [""])[0]).strip().lower()
    if wanted_slug and wanted_slug != slug and posts.is_valid_slug(wanted_slug) and not posts.get_post(wanted_slug) \
            and not posts.rename_post(slug, wanted_slug):
        slug = wanted_slug
    row = posts.get_post(slug)
    return Response(status_code=201, headers={"Location": config.BASE_URL + posts.url_for(row)})


async def _act(req, action: dict):
    """update, delete and undelete, on a post at an address on this site."""
    what = action.get("action")
    if what not in ("update", "delete", "undelete"):
        return _mp_error(400, "invalid_request", "Soloblog can update, delete or undelete")
    url = str(action.get("url", ""))
    if what == "undelete":
        key, err = api_key(req, "publish", via="micropub")
        if err:
            return err
        slug = urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1]
        if not posts.restore_from_trash(slug):
            return _mp_error(400, "invalid_request", "Nothing in trash at that URL")
        return Response(status_code=204)
    slug = _slug_from_url(url)
    if not slug:
        return _mp_error(400, "invalid_request", "No post at that URL")
    row = posts.get_post(slug)
    if what == "delete":
        key, err = api_key(req, "publish", via="micropub")
        if err:
            return err
        from soloblog import publishing
        posts.delete_post(slug)
        publishing.retract(slug)
        return Response(status_code=204)
    # update: a draft with a drafts key; a live post, or making it live, needs publish
    replace, add, delete = action.get("replace") or {}, action.get("add") or {}, action.get("delete") or {}
    if not all(isinstance(x, (dict, list)) for x in (replace, add, delete)):
        return _mp_error(400, "invalid_request", "replace and add are objects, delete an object or a list")
    going_live = str((replace.get("post-status") or [""])[0]) == "published"
    key, err = api_key(req, "publish" if row["published"] or going_live else "draft", via="micropub")
    if err:
        return err
    tags = [t.strip() for t in (row["tags"] or "").split(",") if t.strip()]
    fields = {}
    if "name" in replace:
        fields["title"] = str((replace["name"] or [""])[0]) or row["title"]
    if "content" in replace:
        fields["body"] = "\n\n".join(_content(c) for c in _values(replace, "content"))
    if "content" in add:
        fields["body"] = "\n\n".join([posts.load_post_body(slug)] + [_content(c) for c in _values(add, "content")])
    if "summary" in replace:
        fields["summary"] = str((replace["summary"] or [""])[0])
    if "category" in replace:
        tags = [str(t) for t in _values(replace, "category")]
    tags += [str(t) for t in _values(add, "category") if str(t) not in tags]
    if isinstance(delete, list):
        if "category" in delete:
            tags = []
        if "summary" in delete:
            fields["summary"] = ""
    elif "category" in delete:
        gone = {str(t) for t in _values(delete, "category")}
        tags = [t for t in tags if t not in gone]
    fields["tags"] = ", ".join(tags)
    if "post-status" in replace:
        fields["published"] = going_live and apikeys.allows(key, "publish")
    posts.write(slug, _author(), **fields)
    return Response(status_code=204)


async def media_endpoint(req):
    key, err = api_key(req, "draft", via="micropub")
    if err:
        return err
    if not req.headers.get("content-type", "").startswith("multipart/form-data"):
        return _mp_error(400, "invalid_request", "Send the file as multipart, field \"file\"")
    upload = (await req.form()).get("file")
    if not upload or not getattr(upload, "filename", ""):
        return _mp_error(400, "invalid_request", "Send the file as the field \"file\"")
    data = await upload.read(MAX_IMAGE + 1)
    if len(data) > MAX_IMAGE:
        return _mp_error(413, "invalid_request", "That image is too big - 8 MB at most")
    try:
        saved = images.save_upload(data, upload.filename)
    except Exception as e:  # Pillow, reading what anyone sent - more than it documents
        log.info("an image sent to Micropub's media endpoint was turned away: %s", e)
        return _mp_error(400, "invalid_request", "That isn't an image Soloblog can read")
    return Response(status_code=201, headers={"Location": config.BASE_URL + saved})


ROUTES = [
    Route("/.well-known/oauth-authorization-server", metadata, methods=["GET"]),
    Route("/indieauth/token", token_endpoint, methods=["GET", "POST"]),
    Route("/indieauth/revoke", revoke_endpoint, methods=["POST"]),
    Route("/micropub", micropub, methods=["GET", "POST"]),
    Route("/micropub/media", media_endpoint, methods=["POST"]),
]


def mount(app):
    app.router.routes[0:0] = ROUTES
