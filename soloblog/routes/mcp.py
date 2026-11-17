"""An MCP server (modelcontextprotocol.io) at /mcp, so an AI assistant -
Claude, ChatGPT, Cursor and others - can help with the site: search and
read posts, write and edit drafts, read comments, find images without alt
text and describe them, and publish only if the admin allows it.

Streamable HTTP, without its optional parts: each message is a JSON-RPC
POST answered with JSON (no event streams, no sessions). It needs an API
key (apikeys.py) - as a Bearer header, or made by the assistant signing
in with the site (micropub.py is the OAuth server; /.well-known/
oauth-protected-resource points assistants to it). Every save goes
through posts.write, the editor's own.

Settings > Integrations > API keys keeps AI assistants to drafts unless
the admin chooses otherwise (apikeys.may_publish), whatever their key -
publishing and changing live posts stay the admin's."""
import json
from urllib.parse import urlsplit

from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from soloblog import apikeys
from soloblog import comments
from soloblog import config
from soloblog import images
from soloblog import posts
from soloblog import settings
from soloblog.routes.api import _key as api_key, _author, post_json

VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
INSTRUCTIONS = ("This is a Soloblog site: one person's blog. Posts are markdown. Write and change drafts freely; "
                "the author decides what's published. Keep the author's own voice - suggest, don't rewrite whole "
                "posts unless asked.")


class ToolError(Exception):
    pass


def _drafts_only() -> bool:
    return not apikeys.may_publish("mcp")


def _post(slug):
    row = posts.get_post(slug or "")
    if not row:
        raise ToolError(f"No post with the slug {slug!r} - search_posts finds slugs")
    return row


def _may_change(key, row):
    """A draft with a drafts key; a live post only with Publish, and only
    when the admin lets assistants publish."""
    if row["published"] and (not apikeys.allows(key, "publish") or _drafts_only()):
        raise ToolError("That post is live, and this assistant can only change drafts. Make a draft copy with "
                        "create_draft, or ask the author to change it.")


# ---- the tools: (description, input schema, the scope it needs, function(key, args) -> result)

def search_posts(key, a):
    status = a.get("status") or "all"
    if status not in ("all", "published", "draft", "scheduled"):
        raise ToolError("status is all, published, draft or scheduled")
    limit = min(max(int(a.get("limit") or 20), 1), 50)
    rows = posts.list_by_status(status, "newest", a.get("tag") or "", 1, limit, a.get("query") or "")
    return {"posts": [post_json(r) for r in rows], "total": posts.count_by_status(status, a.get("tag") or "",
                                                                                  a.get("query") or "")}


def get_post(key, a):
    return post_json(_post(a.get("slug")), body=True)


def list_tags(key, a):
    return {"tags": [{"tag": t, "posts": n} for t, n in posts.tag_counts_all()]}


def list_comments(key, a):
    status = a.get("status") or "approved"
    if status not in ("approved", "pending"):
        raise ToolError("status is approved or pending")
    rows = comments.list_by_status(status, a.get("slug") or "", 1, min(max(int(a.get("limit") or 20), 1), 50))
    return {"comments": [{"id": c["id"], "post": c["post_slug"], "author": c["author_name"], "body": c["body"],
                          "created_at": c["created_at"], "reply_to": c["parent_id"]} for c in rows]}


def create_draft(key, a):
    if not str(a.get("title") or "").strip():
        raise ToolError("A draft needs a title")
    tags = a.get("tags") or []
    slug = posts.write(None, _author(), title=str(a["title"])[:300], body=str(a.get("body") or ""),
                       tags=", ".join(str(t) for t in tags) if isinstance(tags, list) else str(tags),
                       summary=str(a.get("summary") or ""), published=False)
    return {"created": post_json(posts.get_post(slug)), "note": "Saved as a draft - the author publishes it."}


def update_post(key, a):
    row = _post(a.get("slug"))
    _may_change(key, row)
    fields = {k: str(a[k]) for k in ("title", "body", "summary") if a.get(k) is not None}
    if a.get("tags") is not None:
        fields["tags"] = ", ".join(str(t) for t in a["tags"]) if isinstance(a["tags"], list) else str(a["tags"])
    if "title" in fields and not fields["title"].strip():
        raise ToolError("A post needs a title")
    posts.write(row["slug"], _author(), **fields)
    return {"updated": post_json(posts.get_post(row["slug"]))}


def publish_post(key, a):
    if _drafts_only():
        raise ToolError("The author has kept AI assistants to drafts (Settings > Integrations > API keys). "
                        "The draft is ready for them to publish.")
    row = _post(a.get("slug"))
    posts.write(row["slug"], _author(), published=True)
    return {"published": post_json(posts.get_post(row["slug"]))}


def images_without_alt(key, a):
    has = images.alt_texts()
    usage = images.usage_map()
    found = [{"url": u["url"], "used_in": [p["slug"] for p in usage.get(u["filename"], [])]}
             for u in images.list_uploads() if u["kind"] == "image" and u["filename"] not in has]
    return {"images": found[:min(max(int(a.get("limit") or 20), 1), 100)], "total": len(found),
            "note": "Look at each image to describe it - the url is on the site's own address."}


def set_alt_text(key, a):
    url = str(a.get("image_url") or "").replace(config.BASE_URL, "", 1)
    if not url.startswith("/uploads/") or "/" in url[len("/uploads/"):]:
        raise ToolError("image_url is one of the site's images, like /uploads/photo.webp")
    filename = url[len("/uploads/"):]
    if not any(u["filename"] == filename for u in images.list_uploads()):
        raise ToolError("There's no image with that address in the media library")
    alt = str(a.get("alt_text") or "").strip()
    if not alt or len(alt) > 300:
        raise ToolError("alt_text is a short description - up to 300 characters")
    images.set_meta(filename, alt, images.meta_for_url(url).get("caption") or "")
    return {"image": url, "alt_text": alt}


TOOLS = {
    "search_posts": ("Find posts and pages - by words, tag or status (drafts included). Returns slugs and details, "
                     "not the full text.",
                     {"type": "object", "properties": {
                         "query": {"type": "string", "description": "Words to look for"},
                         "tag": {"type": "string"},
                         "status": {"type": "string", "enum": ["all", "published", "draft", "scheduled"]},
                         "limit": {"type": "integer", "minimum": 1, "maximum": 50}}},
                     "read", search_posts),
    "get_post": ("Read one post: its markdown body and details.",
                 {"type": "object", "properties": {"slug": {"type": "string"}}, "required": ["slug"]},
                 "read", get_post),
    "list_tags": ("Every tag on the site, with how many posts have it - to suggest tags that already exist.",
                  {"type": "object", "properties": {}}, "read", list_tags),
    "list_comments": ("Read readers' comments - approved, or waiting for approval - on the site or one post.",
                      {"type": "object", "properties": {
                          "status": {"type": "string", "enum": ["approved", "pending"]},
                          "slug": {"type": "string", "description": "Only this post's"},
                          "limit": {"type": "integer", "minimum": 1, "maximum": 50}}},
                      "read", list_comments),
    "create_draft": ("Write a new post, saved as a draft for the author to publish.",
                     {"type": "object", "properties": {
                         "title": {"type": "string"}, "body": {"type": "string", "description": "Markdown"},
                         "tags": {"type": "array", "items": {"type": "string"}},
                         "summary": {"type": "string"}}, "required": ["title"]},
                     "draft", create_draft),
    "update_post": ("Change a post's title, body, tags or summary - only what's given changes. Drafts only, "
                    "unless the author lets assistants change live posts.",
                    {"type": "object", "properties": {
                        "slug": {"type": "string"}, "title": {"type": "string"},
                        "body": {"type": "string", "description": "Markdown - the whole body"},
                        "tags": {"type": "array", "items": {"type": "string"}}, "summary": {"type": "string"}},
                     "required": ["slug"]},
                    "draft", update_post),
    "publish_post": ("Publish a draft - only if the author allows assistants to publish.",
                     {"type": "object", "properties": {"slug": {"type": "string"}}, "required": ["slug"]},
                     "publish", publish_post),
    "images_without_alt": ("Images in the media library with no description for screen readers.",
                           {"type": "object", "properties": {"limit": {"type": "integer", "minimum": 1,
                                                                       "maximum": 100}}},
                           "read", images_without_alt),
    "set_alt_text": ("Describe an image for screen readers - its alt text, used wherever it appears.",
                     {"type": "object", "properties": {
                         "image_url": {"type": "string", "description": "Like /uploads/photo.webp"},
                         "alt_text": {"type": "string", "description": "What the image shows, briefly"}},
                      "required": ["image_url", "alt_text"]},
                     "draft", set_alt_text),
}


def _checked(schema, args) -> dict:
    """The arguments as the tool's schema describes them, or a ToolError in
    words an assistant can act on - never Python's own. Lenient where it's
    clear what was meant: "20" for 20, 5 for "5"."""
    props = schema.get("properties", {})
    for name in schema.get("required", []):
        if args.get(name) is None:
            raise ToolError(f"{name} is needed")
    out = dict(args)
    for name, value in args.items():
        kind = props.get(name, {}).get("type")
        if value is None or not kind:
            continue
        if kind == "integer":
            if isinstance(value, str) and value.strip().isdigit():  # noqa: SIM114 - one test per kind of value
                value = int(value)
            elif isinstance(value, float) and value.is_integer():
                value = int(value)
            if not isinstance(value, int) or isinstance(value, bool):
                raise ToolError(f"{name} should be a number, like 20")
        elif kind == "string":
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                value = str(value)
            if not isinstance(value, str):
                raise ToolError(f"{name} should be text")
        elif kind == "array":
            if not isinstance(value, (list, str)) or (
                    isinstance(value, list) and not all(isinstance(v, (str, int, float)) for v in value)):
                raise ToolError(f'{name} should be a list of words, like ["travel", "food"]')
        out[name] = value
    return out


def _tool_list(key):
    """The tools this key can use - an assistant isn't offered what it
    can't do."""
    out = []
    for name, (description, schema, scope, _) in TOOLS.items():
        if not apikeys.allows(key, scope) or (name == "publish_post" and _drafts_only()):
            continue
        out.append({"name": name, "description": description, "inputSchema": schema})
    return out


def _reply(msg_id, result=None, error=None):
    out = {"jsonrpc": "2.0", "id": msg_id}
    if error:
        out["error"] = {"code": error[0], "message": error[1]}
    else:
        out["result"] = result
    return out


def _handle(key, msg):
    """One JSON-RPC message - its reply, or None for a notification."""
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or not isinstance(msg.get("method"), str):
        return _reply(msg.get("id") if isinstance(msg, dict) else None, error=(-32600, "Not a JSON-RPC request"))
    method, params, msg_id = msg["method"], msg.get("params") or {}, msg.get("id")
    if "id" not in msg:
        return None  # notifications/initialized and the like: nothing to say
    if method == "initialize":
        asked = params.get("protocolVersion")
        return _reply(msg_id, {"protocolVersion": asked if asked in VERSIONS else VERSIONS[0],
                               "capabilities": {"tools": {"listChanged": False}},
                               "serverInfo": {"name": "soloblog", "title": settings.get("site_title") or "Soloblog",
                                              "version": config.VERSION},
                               "instructions": INSTRUCTIONS})
    if method == "ping":
        return _reply(msg_id, {})
    if method == "tools/list":
        return _reply(msg_id, {"tools": _tool_list(key)})
    if method == "tools/call":
        name, args = params.get("name"), params.get("arguments") or {}
        if name not in TOOLS or not isinstance(args, dict):
            return _reply(msg_id, error=(-32602, f"No tool called {name!r}"))
        _, schema, scope, fn = TOOLS[name]
        if not apikeys.allows(key, scope):
            result, failed = f"This key can't do that - it needs {apikeys.SCOPE_LABELS[scope]}", True
        else:
            try:
                result, failed = fn(key, _checked(schema, args)), False
            except ToolError as e:
                result, failed = str(e), True
            except (ValueError, TypeError):
                result, failed = f"Those arguments don't fit {name} - its description says what it takes", True
        content = {"content": [{"type": "text", "text": result if failed else json.dumps(result, ensure_ascii=False)}],
                   "isError": failed}
        if not failed:
            content["structuredContent"] = result
        return _reply(msg_id, content)
    return _reply(msg_id, error=(-32601, f"Soloblog doesn't do {method}"))


def _same_site(req) -> bool:
    """A browser page on another site can't reach it (DNS rebinding) - apps
    send no Origin at all."""
    origin = req.headers.get("origin")
    return not origin or urlsplit(origin).netloc.lower() in {urlsplit(config.BASE_URL).netloc.lower(),
                                                            req.headers.get("host", "").lower()}


async def mcp(req):
    if req.method != "POST":
        # no server-sent stream - every reply comes with its request
        return Response(status_code=405, headers={"Allow": "POST"})
    if not _same_site(req):
        return JSONResponse({"error": "Not from this site"}, status_code=403)
    key, err = api_key(req, "read", via="mcp")
    if err:
        if err.status_code == 401:
            # where an assistant finds how to sign in (MCP authorization)
            err.headers["WWW-Authenticate"] = (f'Bearer resource_metadata="{config.BASE_URL}'
                                               f'/.well-known/oauth-protected-resource"')
        return err
    raw = await req.body()
    if len(raw) > 2 * 1024 * 1024:
        return JSONResponse(_reply(None, error=(-32600, "Too big - 2 MB at most")), status_code=413)
    try:
        data = json.loads(raw)
    except ValueError:
        return JSONResponse(_reply(None, error=(-32700, "That isn't JSON")), status_code=400)
    if isinstance(data, list):
        replies = [r for r in (_handle(key, m) for m in data) if r is not None]
        return JSONResponse(replies) if replies else Response(status_code=202)
    reply = _handle(key, data)
    return JSONResponse(reply) if reply is not None else Response(status_code=202)


def resource_metadata(req):
    return JSONResponse({"resource": f"{config.BASE_URL}/mcp", "authorization_servers": [config.BASE_URL],
                         "bearer_methods_supported": ["header"], "resource_name": settings.get("site_title")})


ROUTES = [Route("/mcp", mcp, methods=["GET", "POST", "DELETE"]),
          Route("/.well-known/oauth-protected-resource", resource_metadata, methods=["GET"]),
          Route("/.well-known/oauth-protected-resource/mcp", resource_metadata, methods=["GET"])]


def mount(app):
    app.router.routes[0:0] = ROUTES
