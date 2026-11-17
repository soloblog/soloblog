"""The MCP server for AI assistants (routes/mcp.py): the protocol, each
tool, and the limits - drafts only unless the author allows more, a key's
scope, a page on another site, odd image addresses."""
import os

import pytest
from PIL import Image
from starlette.testclient import TestClient

from soloblog import apikeys
from soloblog import config
from soloblog import images
from soloblog import posts
from soloblog import settings
from soloblog.db import get_db
from conftest import save_post


@pytest.fixture
def keys():
    made = {scope: apikeys.create(f"assistant {scope}", scope) for scope in apikeys.SCOPES}
    yield made
    db = get_db()
    db.execute("DELETE FROM api_keys")
    db.execute("DELETE FROM rate_hits WHERE bucket IN ('api', 'api-fail')")
    db.commit()
    settings.set_many({"apps_publish": "apps"})


def _rpc(app, key, method, params=None, msg_id=1, **headers):
    c = TestClient(app)
    msg = {"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params or {}}
    return c.post("/mcp", json=msg, headers={"Authorization": f"Bearer {key}", **headers})


def _call(app, key, tool, **args):
    r = _rpc(app, key, "tools/call", {"name": tool, "arguments": args}).json()["result"]
    return r, r["isError"]


def test_the_protocol(app, client, keys):
    r = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    assert r.status_code == 401 and "resource_metadata=" in r.headers["www-authenticate"]
    assert client.get("/.well-known/oauth-protected-resource").json()["resource"].endswith("/mcp")
    init = _rpc(app, keys["read"], "initialize", {"protocolVersion": "2025-06-18"}).json()["result"]
    assert init["protocolVersion"] == "2025-06-18" and "tools" in init["capabilities"]
    assert init["serverInfo"]["name"] == "soloblog"
    c = TestClient(app, headers={"Authorization": f"Bearer {keys['read']}"})
    assert c.post("/mcp", json={"jsonrpc": "2.0", "method": "notifications/initialized"}).status_code == 202
    assert c.get("/mcp").status_code == 405
    assert c.post("/mcp", content=b"{nope").json()["error"]["code"] == -32700
    assert _rpc(app, keys["read"], "resources/list").json()["error"]["code"] == -32601
    batch = c.post("/mcp", json=[{"jsonrpc": "2.0", "id": 1, "method": "ping"},
                                 {"jsonrpc": "2.0", "id": 2, "method": "ping"}]).json()
    assert [b["id"] for b in batch] == [1, 2]
    # a page on another site, through someone's browser
    assert _rpc(app, keys["read"], "ping", Origin="https://evil.example").status_code == 403


def test_each_key_sees_the_tools_it_can_use(app, keys):
    names = lambda key: {t["name"] for t in _rpc(app, key, "tools/list").json()["result"]["tools"]}  # noqa: E731
    assert names(keys["read"]) == {"search_posts", "get_post", "list_tags", "list_comments", "images_without_alt"}
    assert {"create_draft", "update_post", "set_alt_text"} <= names(keys["draft"])
    # publishing isn't even offered while assistants are kept to drafts
    assert "publish_post" not in names(keys["publish"])
    settings.set_many({"apps_publish": "all"})
    assert "publish_post" in names(keys["publish"])
    result, failed = _call(app, keys["read"], "create_draft", title="Nope")
    assert failed and "needs Write drafts" in result["content"][0]["text"]


def test_writing_drafts_and_the_limits(app, admin, keys):
    result, failed = _call(app, keys["draft"], "create_draft", title="An assistant's idea", body="Some *notes*.",
                           tags=["ideas"])
    assert not failed
    slug = result["structuredContent"]["created"]["slug"]
    assert not posts.get_post(slug)["published"] and "ideas" in posts.get_post(slug)["tags"]
    result, failed = _call(app, keys["draft"], "update_post", slug=slug, summary="Short")
    assert not failed and posts.get_post(slug)["summary"] == "Short"
    assert posts.load_post_body(slug).strip() == "Some *notes*."
    # live posts are the author's - even with a Publish key, while kept to drafts
    live = save_post(admin, title="The author's own", body="Mine.")
    for key in (keys["draft"], keys["publish"]):
        result, failed = _call(app, key, "update_post", slug=live, body="Rewritten")
        assert failed and "live" in result["content"][0]["text"]
    result, failed = _call(app, keys["publish"], "publish_post", slug=slug)
    assert failed and not posts.get_post(slug)["published"]
    # until the author allows it
    settings.set_many({"apps_publish": "all"})
    result, failed = _call(app, keys["publish"], "publish_post", slug=slug)
    assert not failed and posts.is_live(posts.get_post(slug))
    assert posts.load_post_body(live).strip() == "Mine."


def test_reading(app, admin, keys):
    slug = save_post(admin, title="Herons and fog", body="A long story about herons.", tags="birds")
    result, failed = _call(app, keys["read"], "search_posts", query="herons")
    assert any(p["slug"] == slug for p in result["structuredContent"]["posts"])
    result, _ = _call(app, keys["read"], "get_post", slug=slug)
    assert "A long story" in result["structuredContent"]["body"]
    result, failed = _call(app, keys["read"], "get_post", slug="nope")
    assert failed and "search_posts" in result["content"][0]["text"]
    result, _ = _call(app, keys["read"], "list_tags")
    assert any(t["tag"] == "birds" for t in result["structuredContent"]["tags"])
    result, failed = _call(app, keys["read"], "list_comments", status="pending")
    assert not failed and "comments" in result["structuredContent"]


def test_arguments_of_the_wrong_kind_are_said_plainly(app, keys):
    result, failed = _call(app, keys["read"], "search_posts", limit="lots")
    assert failed and result["content"][0]["text"] == "limit should be a number, like 20"
    # what's clearly meant is taken as it was meant
    for limit in ("5", 5.0):
        result, failed = _call(app, keys["read"], "search_posts", limit=limit)
        assert not failed, limit
    result, failed = _call(app, keys["read"], "get_post", slug=["a", "b"])
    assert failed and result["content"][0]["text"] == "slug should be text"
    result, failed = _call(app, keys["read"], "get_post")
    assert failed and result["content"][0]["text"] == "slug is needed"
    result, failed = _call(app, keys["draft"], "create_draft", title="Tags", tags={"a": 1})
    assert failed and "should be a list of words" in result["content"][0]["text"]
    for args in ({"limit": True}, {"query": {"x": 1}}, {"tag": ["birds"]}):
        result, failed = _call(app, keys["read"], "search_posts", **args)
        text = result["content"][0]["text"]
        assert failed and "invalid literal" not in text and "Error" not in text, args


def test_describing_images(app, keys):
    os.makedirs(config.UPLOADS_DIR, exist_ok=True)
    Image.new("RGB", (20, 20), (1, 2, 3)).save(os.path.join(config.UPLOADS_DIR, "mcp-plain.webp"), "WEBP")
    images.cache.bump()
    result, _ = _call(app, keys["read"], "images_without_alt", limit=100)
    assert any(i["url"] == "/uploads/mcp-plain.webp" for i in result["structuredContent"]["images"])
    result, failed = _call(app, keys["draft"], "set_alt_text", image_url=config.BASE_URL + "/uploads/mcp-plain.webp",
                           alt_text="A dark square")
    assert not failed and images.alt_texts()["mcp-plain.webp"] == "A dark square"
    for odd in ("/uploads/../blog.db", "/etc/passwd", "/uploads/nope.webp", "https://evil.example/x.png"):
        result, failed = _call(app, keys["draft"], "set_alt_text", image_url=odd, alt_text="x")
        assert failed, odd


def test_desktop_assistants_sign_in_on_their_own_port():
    from soloblog.routes.micropub import _redirect_allowed
    info = {"redirect_uris": ["http://127.0.0.1/callback"]}
    app = "https://assistant.example/client.json"
    assert _redirect_allowed(app, "http://127.0.0.1:53682/callback", info)
    assert not _redirect_allowed(app, "http://127.0.0.1:53682/elsewhere", info)
    assert not _redirect_allowed(app, "http://192.168.1.5:53682/callback", info)
