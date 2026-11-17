"""Publishing from apps that publish to Ghost - Ulysses, and iA Writer on
Apple devices - by answering the small part of Ghost's Admin API they use:
the site, the signed-in user, tags, posts (create, read, update, trash)
and image uploads. Nothing else, and none of Ghost's branding - only the
addresses and shapes these apps expect.

The app signs each request with a signed key (apikeys.create_signed,
Settings > Security > API keys > "For apps that publish to Ghost"):
"Authorization: Ghost <token>". Scopes as for any key; every save goes
through posts.write, the editor's own. HTML becomes markdown."""
import json
import logging
import re
from datetime import datetime, UTC

from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from soloblog import apikeys
from soloblog import config
from soloblog import images
from soloblog import posts
from soloblog import ratelimit
from soloblog import settings
from soloblog.routes.api import _author, MAX_IMAGE

log = logging.getLogger(__name__)

# the addresses apps use, newest first - older apps name a version
PREFIXES = ("/ghost/api/admin", "/ghost/api/v4/admin", "/ghost/api/v3/admin", "/ghost/api/v2/admin",
            "/ghost/api/canary/admin")
# what the site says it is, for an app checking it's new enough
COMPATIBLE_VERSION = "5.0"


def _error(status, kind, message):
    return JSONResponse({"errors": [{"message": message, "type": kind}]}, status_code=status)


def _key(req, scope):
    if config.DEMO_MODE:
        return None, _error(403, "NoPermissionError", "Apps can't publish to the demo - it's shared with everyone")
    auth = req.headers.get("authorization", "")
    row = apikeys.check_signed(auth[6:].strip()) if auth[:6].lower() == "ghost " else None
    if not row:
        if not ratelimit.hit(f"ip:{ratelimit.client_ip(req)}", "api-fail", limit=20, window_minutes=15):
            return None, _error(429, "TooManyRequestsError", "Too many tries with a wrong key - wait a few minutes")
        return None, _error(401, "UnauthorizedError", "This needs a key made in Settings > Integrations > API keys")
    if not ratelimit.hit(f"key:{row['id']}", "api", limit=600, window_minutes=10):
        return None, _error(429, "TooManyRequestsError", "Too many requests - slow down a little")
    if apikeys.held_back(row) and scope == "publish":
        return None, _error(403, "NoPermissionError", apikeys.HELD_BACK)
    if not apikeys.allows(row, scope):
        return None, _error(403, "NoPermissionError", f"This key can't do that - it needs "
                                                      f"{apikeys.SCOPE_LABELS[scope]}")
    return row, None


def _when(value):
    return (value.replace(" ", "T")[:19] + ".000Z") if value else None


def _post(row):
    from soloblog.render import render_post
    body = posts.load_post_body(row["slug"])
    tags = [t.strip() for t in (row["tags"] or "").split(",") if t.strip()]
    status = "draft" if not row["published"] else ("published" if posts.is_live(row) else "scheduled")
    return {
        "id": str(row["id"]), "uuid": str(row["id"]), "title": row["title"], "slug": row["slug"],
        "html": render_post(body)[0], "status": status, "url": config.BASE_URL + posts.url_for(row),
        "visibility": posts.clean_visibility(row["visibility"]),
        "feature_image": (config.BASE_URL + row["cover_image"]) if (row["cover_image"] or "").startswith("/")
        else (row["cover_image"] or None),
        "custom_excerpt": row["summary"] or None, "meta_title": row["seo_title"] or None,
        "tags": [{"id": t, "name": t, "slug": posts.slugify(t)} for t in tags],
        "created_at": _when(row["created_at"]), "updated_at": _when(row["updated_at"]),
        "published_at": _when(row["scheduled_at"] or (row["created_at"] if row["published"] else None)),
    }


def _row(post_id):
    from soloblog.db import get_db
    return get_db().execute("SELECT * FROM posts WHERE id=?", (post_id,)).fetchone() if str(post_id).isdigit() \
        else None


def _markdown(data: dict):
    """The post's words as markdown: from html, or a markdown card in the
    mobiledoc or lexical formats some apps send."""
    from soloblog.importers import html_to_markdown
    if isinstance(data.get("html"), str):
        return html_to_markdown(data["html"])
    for field in ("mobiledoc", "lexical"):
        raw = data.get(field)
        try:
            doc = json.loads(raw) if isinstance(raw, str) else None
        except ValueError:
            doc = None
        if field == "mobiledoc" and isinstance(doc, dict):
            cards = [c[1].get("markdown") for c in doc.get("cards") or [] if isinstance(c, list) and len(c) == 2
                     and c[0] == "markdown" and isinstance(c[1], dict)]
            if cards:
                return "\n\n".join(str(c) for c in cards)
        if field == "lexical" and isinstance(doc, dict):
            found = re.findall(r'"markdown":\s*"((?:[^"\\]|\\.)*)"', raw)
            if found:
                return "\n\n".join(json.loads(f'"{m}"') for m in found)
    return None


def _fields(data: dict):
    """(posts.write fields, wants it live, error)."""
    fields = {}
    if "title" in data:
        fields["title"] = str(data["title"] or "")[:300]
    body = _markdown(data)
    if body is not None:
        fields["body"] = body
    if "tags" in data and isinstance(data["tags"], list):
        names = [t.get("name") if isinstance(t, dict) else t for t in data["tags"]]
        fields["tags"] = ", ".join(str(n).strip() for n in names if n and not str(n).startswith("#"))
    if "custom_excerpt" in data:
        fields["summary"] = str(data["custom_excerpt"] or "")
    if "meta_title" in data:
        fields["seo_title"] = str(data["meta_title"] or "")
    if "feature_image" in data:
        image = str(data["feature_image"] or "")
        fields["cover_image"] = image.replace(config.BASE_URL, "", 1) if image.startswith(config.BASE_URL) else image
    if data.get("visibility") in posts.VISIBILITIES:
        fields["visibility"] = data["visibility"]
    status = data.get("status")
    if status not in (None, "draft", "published", "scheduled"):
        return None, False, _error(422, "ValidationError", "status is draft, published or scheduled")
    if status:
        fields["published"] = status != "draft"
    if status == "scheduled" and data.get("published_at"):
        try:
            when = datetime.fromisoformat(str(data["published_at"]).replace("Z", "+00:00"))
            fields["scheduled_at"] = when.astimezone(UTC).replace(tzinfo=None).isoformat(timespec="seconds")
        except ValueError:
            return None, False, _error(422, "ValidationError", "published_at is a date and time")
    return fields, status in ("published", "scheduled"), None


async def _body(req):
    raw = await req.body()
    if len(raw) > 2 * 1024 * 1024:
        return None, _error(413, "RequestEntityTooLargeError", "That's too big - 2 MB at most")
    try:
        data = json.loads(raw or b"{}")
        post = data["posts"][0]
        if not isinstance(post, dict):
            raise TypeError
    except (ValueError, KeyError, IndexError, TypeError):
        return None, _error(422, "ValidationError", 'Send {"posts": [{...}]}')
    return post, None


def site(req):
    s = settings.get_all()
    return JSONResponse({"site": {"title": s["site_title"], "description": s.get("tagline") or "",
                                  "logo": None, "url": config.BASE_URL + "/", "version": COMPATIBLE_VERSION}})


def me(req):
    key, err = _key(req, "read")
    if err:
        return err
    return JSONResponse({"users": [{"id": "1", "name": _author(), "slug": "admin", "email": "",
                                    "roles": [{"name": "Administrator"}]}]})


def tags(req):
    key, err = _key(req, "read")
    if err:
        return err
    found = [{"id": t, "name": t, "slug": posts.slugify(t)} for t, _ in posts.tag_counts_all()]
    return JSONResponse({"tags": found, "meta": {"pagination": {"page": 1, "pages": 1, "total": len(found),
                                                                "limit": "all", "next": None, "prev": None}}})


async def posts_collection(req):
    if req.method == "GET":
        key, err = _key(req, "read")
        if err:
            return err
        rows = posts.list_by_status("all", "newest", "", 1, 50)
        return JSONResponse({"posts": [_post(r) for r in rows],
                             "meta": {"pagination": {"page": 1, "pages": 1, "limit": 50, "total": len(rows)}}})
    key, err = _key(req, "draft")
    if err:
        return err
    data, err = await _body(req)
    if err:
        return err
    fields, live, err = _fields(data)
    if err:
        return err
    if live and not apikeys.allows(key, "publish"):
        if not apikeys.held_back(key):
            return _error(403, "NoPermissionError", "This key writes drafts only - publishing needs a key with Publish")
        # the author keeps publishing: it arrives as a draft
        fields = {**{k: v for k, v in fields.items() if k != "scheduled_at"}, "published": False}
    if not str(fields.get("title", "")).strip():
        fields["title"] = "Untitled"
    slug = posts.write(None, _author(), **fields)
    wanted = str(data.get("slug") or "").strip().lower()
    if wanted and wanted != slug and posts.is_valid_slug(wanted) and not posts.get_post(wanted) \
            and not posts.rename_post(slug, wanted):
        slug = wanted
    return JSONResponse({"posts": [_post(posts.get_post(slug))]}, status_code=201)


async def posts_item(req):
    row = _row(req.path_params["id"])
    if req.method == "GET":
        key, err = _key(req, "read")
        if err:
            return err
        return JSONResponse({"posts": [_post(row)]}) if row else _error(404, "NotFoundError", "No such post")
    if req.method == "DELETE":
        key, err = _key(req, "publish")
        if err:
            return err
        if not row:
            return _error(404, "NotFoundError", "No such post")
        from soloblog import publishing
        posts.delete_post(row["slug"])
        publishing.retract(row["slug"])
        return Response(status_code=204)
    key, err = _key(req, "draft")
    if err:
        return err
    if not row:
        return _error(404, "NotFoundError", "No such post")
    data, err = await _body(req)
    if err:
        return err
    fields, live, err = _fields(data)
    if err:
        return err
    if (live or row["published"]) and not apikeys.allows(key, "publish"):
        return _error(403, "NoPermissionError", apikeys.HELD_BACK if apikeys.held_back(key) else
                      "This key changes drafts only - a published post, or publishing, needs a key with Publish")
    if "title" in fields and not fields["title"].strip():
        fields.pop("title")
    posts.write(row["slug"], _author(), **fields)
    return JSONResponse({"posts": [_post(posts.get_post(row["slug"]))]})


async def image_upload(req):
    key, err = _key(req, "draft")
    if err:
        return err
    if not req.headers.get("content-type", "").startswith("multipart/form-data"):
        return _error(422, "ValidationError", "Send the image as multipart, field \"file\"")
    form = await req.form()
    upload = form.get("file")
    if not upload or not getattr(upload, "filename", ""):
        return _error(422, "ValidationError", "Send the image as the field \"file\"")
    data = await upload.read(MAX_IMAGE + 1)
    if len(data) > MAX_IMAGE:
        return _error(413, "RequestEntityTooLargeError", "That image is too big - 8 MB at most")
    try:
        saved = images.save_upload(data, upload.filename)
    except Exception as e:  # Pillow, reading what anyone sent - more than it documents
        log.info("an image sent to the Ghost API was turned away: %s", e)
        return _error(415, "UnsupportedMediaTypeError", "That isn't an image Soloblog can read")
    return JSONResponse({"images": [{"url": config.BASE_URL + saved, "ref": form.get("ref")}]}, status_code=201)


ROUTES = [r for p in PREFIXES for r in (
    Route(f"{p}/site/", site, methods=["GET"]),
    Route(f"{p}/users/me/", me, methods=["GET"]),
    Route(f"{p}/tags/", tags, methods=["GET"]),
    Route(f"{p}/posts/", posts_collection, methods=["GET", "POST"]),
    Route(f"{p}/posts/{{id}}/", posts_item, methods=["GET", "PUT", "DELETE"]),
    Route(f"{p}/images/upload/", image_upload, methods=["POST"]),
)]


def mount(app):
    app.router.routes[0:0] = ROUTES
