"""The API, version 1 (docs/API.md): reading and writing the site's posts
with an API key (apikeys.py) - for apps, scripts and AI assistants.

Only a key in the Authorization header opens it - never the admin's
login cookie, so a page on another site can't use it through the
browser, and CSRF doesn't apply. Every save goes through posts.write,
the editor's own. JSON in and out; an error is {"error": "..."}.

Plain Starlette routes (mount, below), not FastHTML's: FastHTML reads a
request's body itself before the handler, and stops at JSON that isn't
an object - the API reads its own and answers with its own errors."""
import json
import logging
from datetime import datetime, UTC
from urllib.parse import urlsplit

from starlette.responses import JSONResponse
from starlette.routing import Route

from soloblog import apikeys
from soloblog import config
from soloblog import images
from soloblog import netguard
from soloblog import posts
from soloblog import ratelimit
from soloblog import settings

log = logging.getLogger(__name__)
V1 = "/api/v1"
MAX_BODY = 2 * 1024 * 1024   # a request's JSON
MAX_IMAGE = 8 * 1024 * 1024  # as the editor's own upload
# what a post's JSON may set - anything else is an error, so a typo isn't lost quietly
FIELDS = {"title", "body", "tags", "summary", "cover_image", "visibility", "published", "scheduled_at",
          "pin_location", "unlisted", "comments_enabled", "series_name", "series_order", "seo_title",
          "title_style", "page_width", "slides", "in_wiki", "remind_update", "link_url"}
# fields that no longer mean anything: a client that still sends one isn't told off
IGNORED = {"layout"}
# changing these on a post, or a live post at all, takes the publish scope
PUBLISHING = {"published", "scheduled_at", "pin_location"}


ROUTES = []


def _route(method: str, path: str):
    def add(fn):
        ROUTES.append(Route(V1 + path, fn, methods=[method]))
        return fn
    return add


def mount(app):
    """Ahead of every other route, so nothing of the site's own catches an
    /api/ address."""
    app.router.routes[0:0] = ROUTES


def _ok(data, status: int = 200, **headers):
    return JSONResponse(data, status_code=status, headers=headers or None)


def _int(req, name: str, default: int) -> int:
    try:
        return int(req.query_params.get(name, default))
    except ValueError:
        return default


def _error(status: int, message: str, **headers):
    return JSONResponse({"error": message}, status_code=status, headers=headers or None)


def _key(req, scope: str, via: str = "api"):
    """(key row, None) when the request's key may do what needs `scope`,
    else (None, the error to send). via: what's using it (apikeys.VIA)."""
    if config.DEMO_MODE:
        return None, _error(403, "The API is off in the demo - it's shared with everyone")
    auth = req.headers.get("authorization", "")
    # (Micropub may send it as a form's access_token instead - micropub.py)
    token = auth[7:].strip() if auth[:7].lower() == "bearer " else getattr(req.state, "access_token", "")
    row = apikeys.check(token, via)
    if not row:
        # guessing is pointless (a key is 256 random bits), and is slowed down anyway
        if not ratelimit.hit(f"ip:{ratelimit.client_ip(req)}", "api-fail", limit=20, window_minutes=15):
            return None, _error(429, "Too many tries with a wrong key - wait a few minutes")
        return None, _error(401, "An API key is needed: Authorization: Bearer <key>",
                            **{"WWW-Authenticate": 'Bearer realm="soloblog"'})
    if not ratelimit.hit(f"key:{row['id']}", "api", limit=600, window_minutes=10):
        return None, _error(429, "Too many requests - slow down a little", **{"Retry-After": "60"})
    if apikeys.held_back(row) and scope == "publish":
        return None, _error(403, apikeys.HELD_BACK)
    if not apikeys.allows(row, scope):
        return None, _error(403, f"This key can't do that - it needs {apikeys.SCOPE_LABELS[scope]} "
                                 f"(it has {apikeys.SCOPE_LABELS[row['scope']]})")
    return row, None


def _status(row) -> str:
    if not row["published"]:
        return "draft"
    return "published" if posts.is_live(row) else "scheduled"


def post_json(row, body: bool = False) -> dict:
    """A post as the API gives it."""
    out = {
        "slug": row["slug"], "title": row["title"], "status": _status(row),
        "url": config.BASE_URL + posts.url_for(row), "page": posts.is_page(row),
        "pin_location": row["pin_location"] if row["pinned"] else "",
        "visibility": posts.clean_visibility(row["visibility"]),
        "tags": [t.strip() for t in (row["tags"] or "").split(",") if t.strip()],
        "summary": row["summary"] or "", "cover_image": row["cover_image"] or "",
        "unlisted": bool(row["unlisted"]), "password_protected": posts.is_protected(row),
        "comments_enabled": bool(row["comments_enabled"]),
        "series_name": row["series_name"] or "", "series_order": row["series_order"] or 0,
        "seo_title": row["seo_title"] or "", "link_url": row["link_url"] or "",
        "title_style": row["title_style"], "page_width": row["page_width"], "slides": bool(row["slides"]),
        "in_wiki": bool(row["in_wiki"]), "remind_update": bool(row["remind_update"]),
        "scheduled_at": row["scheduled_at"] or None, "created_at": row["created_at"], "updated_at": row["updated_at"],
    }
    if body:
        out["body"] = posts.load_post_body(row["slug"])
    return out


async def _json(req):
    """(fields, None) from the request's JSON, or (None, the error)."""
    raw = await req.body()
    if len(raw) > MAX_BODY:
        return None, _error(413, "That's too big - 2 MB at most")
    try:
        data = json.loads(raw or b"{}")
    except ValueError:
        return None, _error(400, "That isn't JSON")
    if not isinstance(data, dict):
        return None, _error(400, "Send a JSON object")
    unknown = sorted(set(data) - FIELDS - IGNORED)
    if unknown:
        return None, _error(400, f"Not a field a post has: {', '.join(unknown)}")
    fields = {k: v for k, v in data.items() if k not in IGNORED}
    if "tags" in fields:
        tags = fields["tags"]
        if isinstance(tags, list) and all(isinstance(t, str) for t in tags):
            fields["tags"] = ", ".join(t.strip() for t in tags if t.strip())
        elif not isinstance(tags, str):
            return None, _error(400, "tags is a list of words, or one string with commas")
    for name in ("title", "body", "summary", "cover_image", "series_name", "seo_title", "title_style",
                 "page_width", "link_url"):
        if name in fields and not isinstance(fields[name], str):
            return None, _error(400, f"{name} is text")
    if "title" in fields and len(fields["title"]) > 300:
        return None, _error(400, "A title is 300 characters at most")
    for name in ("published", "unlisted", "comments_enabled", "slides", "in_wiki", "remind_update"):
        if name in fields and not isinstance(fields[name], bool):
            return None, _error(400, f"{name} is true or false")
    if "title_style" in fields and fields["title_style"] not in posts.TITLE_STYLES:
        return None, _error(400, "title_style is empty (left), centre or hidden")
    if "page_width" in fields and fields["page_width"] not in posts.PAGE_WIDTHS:
        return None, _error(400, "page_width is empty (the site's column) or wide")
    if fields.get("link_url") and posts.clean_link(fields["link_url"]) != fields["link_url"].strip():
        return None, _error(400, "link_url is an address starting with https://, or a path on this site")
    if "visibility" in fields and fields["visibility"] not in posts.VISIBILITIES:
        return None, _error(400, "visibility is public, members or paid")
    if "pin_location" in fields and fields["pin_location"] not in ("", *posts.VALID_PIN_LOCATIONS):
        return None, _error(400, f"pin_location is one of: {', '.join(posts.VALID_PIN_LOCATIONS)}, or empty")
    if "series_order" in fields and not isinstance(fields["series_order"], int):
        return None, _error(400, "series_order is a whole number")
    if fields.get("scheduled_at"):
        try:
            when = datetime.fromisoformat(str(fields["scheduled_at"]).replace("Z", "+00:00"))
        except ValueError:
            return None, _error(400, "scheduled_at is a date and time, like 2026-11-01T09:00:00Z")
        if when.tzinfo:
            when = when.astimezone(UTC).replace(tzinfo=None)
        fields["scheduled_at"] = when.isoformat(timespec="seconds")
    return fields, None


def _author():
    s = settings.get_all()
    return s["author_name"] or s["site_title"]


# ---- reading

@_route("GET", "/site")
def api_site(req):
    key, err = _key(req, "read")
    if err:
        return err
    s = settings.get_all()
    return _ok({"title": s["site_title"], "url": config.BASE_URL, "version": config.VERSION,
                "language": s.get("site_language") or "en", "key": {"name": key["name"], "scope": key["scope"]}})


@_route("GET", "/posts")
def api_posts(req):
    key, err = _key(req, "read")
    if err:
        return err
    params = req.query_params
    status = params.get("status", "all")
    status = status if status in ("all", "published", "draft", "scheduled", "pinned") else "all"
    q, tag = params.get("q", "")[:200], params.get("tag", "")[:100]
    page, per_page = max(1, _int(req, "page", 1)), min(max(1, _int(req, "per_page", 20)), 100)
    rows = posts.list_by_status(status, "newest", tag, page, per_page, q)
    return _ok({"posts": [post_json(r) for r in rows], "total": posts.count_by_status(status, tag, q),
                "page": page, "per_page": per_page})


@_route("GET", "/posts/{slug}")
def api_post(req):
    key, err = _key(req, "read")
    if err:
        return err
    row = posts.get_post(req.path_params["slug"])
    return _ok(post_json(row, body=True)) if row else _error(404, "No post with that slug")


# ---- writing

def _needs_publish(fields: dict, row=None) -> bool:
    """Publishing, scheduling or pinning - or changing a post that's
    already published - takes the publish scope."""
    return bool(PUBLISHING & {k for k, v in fields.items() if v}) or bool(row and row["published"])


@_route("POST", "/posts")
async def api_create(req):
    key, err = _key(req, "draft")
    if err:
        return err
    fields, err = await _json(req)
    if err:
        return err
    if _needs_publish(fields) and not apikeys.allows(key, "publish"):
        if not apikeys.held_back(key):
            return _error(403, "This key writes drafts only - publishing needs a key with Publish")
        # the author keeps publishing: it arrives as a draft
        fields = {k: v for k, v in fields.items() if k not in PUBLISHING}
    if not str(fields.get("title", "")).strip():
        return _error(400, "A post needs a title")
    slug = posts.write(None, _author(), **fields)
    return _ok(post_json(posts.get_post(slug), body=True), 201, Location=f"{V1}/posts/{slug}")


@_route("PATCH", "/posts/{slug}")
async def api_update(req):
    key, err = _key(req, "draft")
    if err:
        return err
    slug = req.path_params["slug"]
    row = posts.get_post(slug)
    if not row:
        return _error(404, "No post with that slug")
    fields, err = await _json(req)
    if err:
        return err
    if _needs_publish(fields, row) and not apikeys.allows(key, "publish"):
        return _error(403, apikeys.HELD_BACK if apikeys.held_back(key) else
                      "This key changes drafts only - a published post, or publishing, needs a key with Publish")
    if "title" in fields and not fields["title"].strip():
        return _error(400, "A post needs a title")
    posts.write(slug, _author(), **fields)
    return _ok(post_json(posts.get_post(slug), body=True))


def _set_published(req, on: bool):
    key, err = _key(req, "publish")
    if err:
        return err
    slug = req.path_params["slug"]
    if not posts.get_post(slug):
        return _error(404, "No post with that slug")
    posts.write(slug, _author(), published=on)
    return _ok(post_json(posts.get_post(slug)))


@_route("POST", "/posts/{slug}/publish")
def api_publish(req):
    return _set_published(req, True)


@_route("POST", "/posts/{slug}/unpublish")
def api_unpublish(req):
    return _set_published(req, False)


@_route("DELETE", "/posts/{slug}")
def api_trash(req):
    """To trash, as in the admin - it can be restored from there."""
    key, err = _key(req, "publish")
    if err:
        return err
    slug = req.path_params["slug"]
    if not posts.get_post(slug):
        return _error(404, "No post with that slug")
    from soloblog import publishing
    posts.delete_post(slug)
    publishing.retract(slug)
    return _ok({"trashed": slug})


def comment_json(c) -> dict:
    return {"id": c["id"], "post": c["post_slug"], "author": c["author_name"], "body": c["body"],
            "status": "trash" if c["trashed_at"] else ("approved" if c["approved"] else "pending"),
            "reply_to": c["parent_id"], "by_author": bool(c["is_author"]), "created_at": c["created_at"]}


@_route("GET", "/comments")
def api_comments(req):
    key, err = _key(req, "read")
    if err:
        return err
    from soloblog import comments
    status = req.query_params.get("status", "pending")
    if status not in ("pending", "approved", "trash"):
        return _error(400, "status is pending, approved or trash")
    post = req.query_params.get("post", "")
    page, per_page = max(1, _int(req, "page", 1)), min(max(1, _int(req, "per_page", 20)), 100)
    rows = comments.list_by_status(status, post, page, per_page) if status != "trash" else \
        comments.list_by_status("trash", page=page, per_page=per_page)
    total = comments.count_by_status(status, post) if status != "trash" else comments.count_by_status("trash")
    return _ok({"comments": [comment_json(c) for c in rows], "total": total, "page": page, "per_page": per_page})


def _comment(req):
    from soloblog import comments
    cid = req.path_params["id"]
    return comments.get(int(cid)) if str(cid).isdigit() else None


@_route("POST", "/comments/{id}/approve")
def api_approve_comment(req):
    """Approving shows it to everyone - a Publish key's to do."""
    key, err = _key(req, "publish")
    if err:
        return err
    from soloblog import comments
    c = _comment(req)
    if not c or c["trashed_at"]:
        return _error(404, "No comment with that id")
    comments.approve(c["id"])
    return _ok(comment_json(comments.get(c["id"])))


@_route("DELETE", "/comments/{id}")
def api_trash_comment(req):
    key, err = _key(req, "publish")
    if err:
        return err
    from soloblog import comments
    c = _comment(req)
    if not c:
        return _error(404, "No comment with that id")
    comments.move_to_trash(c["id"])
    return _ok({"trashed": c["id"]})


@_route("POST", "/media")
async def api_media(req):
    """An image into the media library: a file (multipart, field "file"), or
    {"url": ...} fetched from the public internet - never from the
    server's own network (netguard)."""
    key, err = _key(req, "draft")
    if err:
        return err
    kind = req.headers.get("content-type", "")
    name = ""
    if kind.startswith("multipart/form-data"):
        upload = (await req.form()).get("file")
        if not upload or not getattr(upload, "filename", ""):
            return _error(400, "Send the image as the field \"file\"")
        data, name = await upload.read(MAX_IMAGE + 1), upload.filename
    else:
        raw = await req.body()
        try:
            url = json.loads(raw or b"{}").get("url", "")
        except (ValueError, AttributeError):
            return _error(400, "Send a file, or JSON with \"url\"")
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            return _error(400, "url is an http or https address")
        try:
            data = netguard.fetch(url, max_bytes=MAX_IMAGE)
        except netguard.Blocked as e:
            return _error(400, f"Couldn't fetch that: {e}")
        except Exception as e:  # anything a server can answer with - see DEVELOPMENT.md > Errors
            log.info("an image for the API couldn't be fetched from %s: %s", urlsplit(url).hostname, e)
            return _error(400, "Couldn't fetch that address")
        name = url.rsplit("/", 1)[-1].split("?")[0]
    if len(data) > MAX_IMAGE:
        return _error(413, "That image is too big - 8 MB at most")
    try:
        saved = images.save_upload(data, name)
    except Exception as e:  # Pillow, reading what anyone sent - more than it documents
        log.info("an image sent to the API was turned away: %s", e)
        return _error(400, "That isn't an image Soloblog can read")
    return _ok({"url": saved, "absolute_url": config.BASE_URL + saved}, 201)
