import json

from fasthtml.common import *

from soloblog import config
from soloblog import fediverse
from soloblog import ratelimit
from soloblog import webmention

ar = APIRouter()

# The fediverse's and the IndieWeb's addresses (fediverse.py,
# webmention.py). Everything here answers 404 while its feature is off.


def _json(doc, status=200, kind=fediverse.CONTENT_TYPE):
    return Response(json.dumps(doc, ensure_ascii=False), status_code=status, media_type=kind,
                    headers={"Access-Control-Allow-Origin": "*"})


def _off():
    return Response("Not found", status_code=404, media_type="text/plain")


@ar.get("/.well-known/webfinger")
def webfinger(resource: str = ""):
    if not fediverse.enabled():
        return _off()
    doc = fediverse.webfinger(resource)
    return _json(doc, kind="application/jrd+json") if doc else _off()


@ar.get("/.well-known/nodeinfo")
def nodeinfo_links():
    if not fediverse.enabled():
        return _off()
    return _json({"links": [{"rel": "http://nodeinfo.diaspora.software/ns/schema/2.0",
                             "href": f"{config.BASE_URL}/nodeinfo/2.0"}]}, kind="application/json")


@ar.get("/nodeinfo/2.0")
def nodeinfo():
    if not fediverse.enabled():
        return _off()
    return _json(fediverse.nodeinfo(),
                 kind='application/json; profile="http://nodeinfo.diaspora.software/ns/schema/2.0#"')


@ar.get("/ap/actor")
def actor(request):
    if not fediverse.enabled():
        return _off()
    if not fediverse.wants_json(request.headers.get("accept", "")):
        # a person following the link lands on the blog itself
        return RedirectResponse("/", status_code=302)
    return _json(fediverse.actor())


@ar.get("/ap/outbox")
def outbox():
    return _json(fediverse.outbox()) if fediverse.enabled() else _off()


@ar.get("/ap/followers")
def followers():
    return _json(fediverse.followers_collection()) if fediverse.enabled() else _off()


@ar.get("/ap/following")
def following():
    return _json(fediverse.following_collection()) if fediverse.enabled() else _off()


@ar.get("/ap/note/{comment_id}")
def note(request, comment_id: int):
    if not fediverse.enabled():
        return _off()
    doc = fediverse.note_for(comment_id)
    if not doc:
        return _off()
    if not fediverse.wants_json(request.headers.get("accept", "")):
        return RedirectResponse(doc["url"], status_code=302)
    return _json(doc)


@ar.post("/ap/inbox")
async def inbox(request):
    if not fediverse.enabled():
        return _off()
    if not ratelimit.hit(f"ip:{ratelimit.client_ip(request)}", "ap-inbox", limit=300, window_minutes=5):
        return Response("Slow down", status_code=429)
    body = await request.body()
    if len(body) > fediverse.MAX_INBOX_BYTES:
        return Response("Too large", status_code=413)
    try:
        json.loads(body)
    except ValueError:
        return Response("Not JSON", status_code=400)
    headers = {k.lower(): v for k, v in request.headers.items()}
    path = request.url.path + (f"?{request.url.query}" if request.url.query else "")
    fediverse.receive("POST", path, headers, body)
    return Response("", status_code=202)


@ar.post("/webmention")
def receive_webmention(request, source: str = "", target: str = ""):
    if not webmention.receiving():
        return _off()
    if not ratelimit.hit(f"ip:{ratelimit.client_ip(request)}", "webmention", limit=30, window_minutes=60):
        return Response("Slow down", status_code=429, media_type="text/plain")
    problem = webmention.accept(source.strip(), target.strip())
    if problem:
        return Response(problem, status_code=400, media_type="text/plain")
    return Response("Accepted - it'll be checked shortly.", status_code=202, media_type="text/plain")


@ar.get("/webmention")
def webmention_info():
    if not webmention.receiving():
        return _off()
    return Response("This is a Webmention endpoint (https://www.w3.org/TR/webmention/). POST source and target.",
                    media_type="text/plain")
