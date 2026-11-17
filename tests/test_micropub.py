"""Posting from writing apps: "sign in with your site" (IndieAuth) and
Micropub (routes/micropub.py). The whole connection as an app makes it,
and the abuse cases - a code used twice, a wrong PKCE verifier, an app
asking to be sent back somewhere else, a drafts key reaching past its
scope, a photo address on the server's own network."""
import base64
import hashlib
import io
from urllib.parse import parse_qs, urlsplit

import pytest
from PIL import Image
from starlette.testclient import TestClient

from soloblog import apikeys
from soloblog import config
from soloblog import netguard
from soloblog import posts
from soloblog import settings
from soloblog.db import get_db
from conftest import save_post

APP = "https://writer.example/"
BACK = "https://writer.example/callback"


@pytest.fixture
def app_page(monkeypatch):
    """The writing app's own page, as the site fetches it."""
    page = (b'<html><head><title>Example Writer</title>'
            b'<link rel="redirect_uri" href="https://other.example/back"></head></html>')
    real = netguard.fetch
    monkeypatch.setattr(netguard, "fetch", lambda url, **kw: page if url == APP else real(url, **kw))
    yield
    db = get_db()
    db.execute("DELETE FROM api_keys")
    db.execute("DELETE FROM indieauth_codes")
    db.execute("DELETE FROM rate_hits WHERE bucket IN ('api', 'api-fail', 'indieauth-token')")
    db.commit()
    settings.set_many({"apps_publish": "apps"})


def _pkce():
    verifier = "v" * 50
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def _ask(admin, challenge, scope="create update delete media", redirect=BACK, state="xyz"):
    return admin.get("/indieauth/auth", params={
        "response_type": "code", "client_id": APP, "redirect_uri": redirect, "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256", "scope": scope, "me": config.BASE_URL})


def _approve(admin, challenge, scope="publish", decision="allow", redirect=BACK):
    return admin.post("/indieauth/auth", data={
        "client_id": APP, "redirect_uri": redirect, "state": "xyz", "code_challenge": challenge,
        "code_challenge_method": "S256", "requested": "create update delete media", "scope": scope,
        "decision": decision})


def _connect(app, admin, scope="publish"):
    """The whole connection; returns the app's key."""
    verifier, challenge = _pkce()
    back = _approve(admin, challenge, scope)
    code = parse_qs(urlsplit(back.headers["location"]).query)["code"][0]
    r = TestClient(app).post("/indieauth/token", data={
        "grant_type": "authorization_code", "code": code, "client_id": APP, "redirect_uri": BACK,
        "code_verifier": verifier})
    return r.json()["access_token"]


def test_apps_find_the_endpoints(client):
    home = client.get("/").text
    for rel in ("micropub", "authorization_endpoint", "token_endpoint", "indieauth-metadata"):
        assert f'rel="{rel}"' in home, rel
    meta = client.get("/.well-known/oauth-authorization-server").json()
    assert meta["code_challenge_methods_supported"] == ["S256"] and meta["issuer"] == config.BASE_URL


def test_connecting_an_app(app, admin, app_page):
    verifier, challenge = _pkce()
    page = _ask(admin, challenge).text
    assert "Connect Example Writer?" in page and "writer.example" in page
    back = _approve(admin, challenge)
    assert back.status_code == 302 and back.headers["location"].startswith(BACK)
    params = parse_qs(urlsplit(back.headers["location"]).query)
    assert params["state"] == ["xyz"] and params["iss"] == [config.BASE_URL]
    code = params["code"][0]
    app_client = TestClient(app)
    swap = {"grant_type": "authorization_code", "code": code, "client_id": APP, "redirect_uri": BACK,
            "code_verifier": "wrong" * 10}
    # the wrong verifier spends the code too - one try
    assert app_client.post("/indieauth/token", data=swap).json()["error"] == "invalid_grant"
    assert app_client.post("/indieauth/token", data={**swap, "code_verifier": verifier}).status_code == 400
    # a fresh approval, done right
    key = _connect(app, admin)
    assert key.startswith("sb_") and apikeys.check(key)["scope"] == "publish"
    assert apikeys.check(key)["client_id"] == APP and "Example Writer" in apikeys.check(key)["name"]
    # and it shows in Settings, where it can be disconnected
    assert "Example Writer (connected)" in admin.get("/admin/settings?tab=integrations").text


def test_what_an_app_cant_do(app, admin, client, app_page):
    verifier, challenge = _pkce()
    # be sent back somewhere it doesn't list
    assert "isn't its own" in _ask(admin, challenge, redirect="https://evil.example/steal").text
    assert "isn't its own" in _approve(admin, challenge, redirect="https://evil.example/steal").text
    # (an address it does list is fine)
    assert "Connect Example Writer?" in _ask(admin, challenge, redirect="https://other.example/back").text
    # skip PKCE
    no_pkce = admin.get("/indieauth/auth", params={"client_id": APP, "redirect_uri": BACK, "state": "s"}).text
    assert "PKCE" in no_pkce
    # a refusal goes back as one
    denied = _approve(admin, challenge, decision="deny")
    assert "error=access_denied" in denied.headers["location"]
    # nobody logged in: the login first, then back to the approval page
    r = client.get("/indieauth/auth", params={"client_id": APP, "redirect_uri": BACK, "code_challenge": challenge,
                                              "code_challenge_method": "S256"}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login"
    from conftest import PASSWORD
    r = client.post("/login", data={"password": PASSWORD}, follow_redirects=False)
    assert r.headers["location"].startswith("/indieauth/auth?")


def test_micropub_posts_as_the_app_asks(app, admin, app_page):
    key = _connect(app, admin, "publish")
    mp = TestClient(app)
    # a form, the token in its body as Micropub allows
    r = mp.post("/micropub", data={"h": "entry", "content": "Hello from my phone. It works!",
                                   "category[]": ["phone", "test"], "access_token": key})
    assert r.status_code == 201
    slug = urlsplit(r.headers["location"]).path.rsplit("/", 1)[-1]
    row = posts.get_post(slug)
    assert posts.is_live(row) and row["title"] == "Hello from my phone. It works!" and "phone" in row["tags"]
    # JSON, HTML content, a draft
    r = mp.post("/micropub", headers={"Authorization": f"Bearer {key}"},
                json={"type": ["h-entry"], "properties": {"name": ["A proper post"],
                                                          "content": [{"html": "<p>Some <strong>bold</strong> words</p>"}],
                                                          "post-status": ["draft"], "mp-slug": ["proper"]}})
    assert r.status_code == 201 and r.headers["location"].endswith("/post/proper")
    assert not posts.get_post("proper")["published"] and "**bold**" in posts.load_post_body("proper")
    # the admin's "always drafts" wins over the app
    settings.set_many({"apps_publish": "none"})
    r = mp.post("/micropub", data={"h": "entry", "content": "Should wait", "access_token": key})
    assert not posts.get_post(urlsplit(r.headers["location"]).path.rsplit("/", 1)[-1])["published"]


def test_a_bookmark_is_a_page_with_a_link(app, admin, app_page):
    key = _connect(app, admin, "publish")
    mp = TestClient(app, headers={"Authorization": f"Bearer {key}"})
    r = mp.post("/micropub", data={"h": "entry", "bookmark-of": "https://example.com/worth-reading",
                                   "content": "Why it's good."})
    assert r.status_code == 201
    row = posts.get_post(urlsplit(r.headers["location"]).path.rsplit("/", 1)[-1])
    # Link to, on any post
    assert row["link_url"] == "https://example.com/worth-reading"
    # an address that isn't a web page is no bookmark
    r = mp.post("/micropub", data={"h": "entry", "bookmark-of": "javascript:alert(1)", "content": "Not a link."})
    assert posts.get_post(urlsplit(r.headers["location"]).path.rsplit("/", 1)[-1])["link_url"] == ""


def test_a_drafts_key_stays_in_drafts(app, admin, app_page):
    key = _connect(app, admin, "draft")
    mp = TestClient(app, headers={"Authorization": f"Bearer {key}"})
    r = mp.post("/micropub", data={"h": "entry", "content": "Asked to be live"})
    assert not posts.get_post(urlsplit(r.headers["location"]).path.rsplit("/", 1)[-1])["published"]
    live = save_post(admin, title="Live already", body="Untouched.")
    url = config.BASE_URL + f"/post/{live}"
    assert mp.post("/micropub", json={"action": "update", "url": url,
                                      "replace": {"content": ["Defaced"]}}).status_code == 403
    assert mp.post("/micropub", json={"action": "delete", "url": url}).status_code == 403
    assert posts.load_post_body(live).strip() == "Untouched."


def test_update_delete_undelete_and_query(app, admin, app_page):
    key = _connect(app, admin, "publish")
    mp = TestClient(app, headers={"Authorization": f"Bearer {key}"})
    slug = save_post(admin, title="Edit me", body="First words.", tags="one, two")
    url = config.BASE_URL + f"/post/{slug}"
    assert mp.post("/micropub", json={"action": "update", "url": url, "replace": {"content": ["New words."]},
                                      "add": {"category": ["three"]}, "delete": {"category": ["one"]}}
                   ).status_code == 204
    row = posts.get_post(slug)
    assert posts.load_post_body(slug).strip() == "New words." and row["tags"] == "two, three"
    source = mp.get("/micropub", params={"q": "source", "url": url}).json()
    assert source["properties"]["content"] == ["New words."] and source["properties"]["name"] == ["Edit me"]
    assert mp.get("/micropub", params={"q": "config"}).json()["media-endpoint"].endswith("/micropub/media")
    assert mp.post("/micropub", json={"action": "delete", "url": url}).status_code == 204
    assert not posts.get_post(slug)
    assert mp.post("/micropub", json={"action": "undelete", "url": url}).status_code == 204
    assert posts.get_post(slug)


def test_photos_and_the_media_endpoint(app, admin, app_page):
    key = _connect(app, admin, "draft")
    mp = TestClient(app, headers={"Authorization": f"Bearer {key}"})
    buf = io.BytesIO()
    Image.new("RGB", (30, 20), (10, 120, 200)).save(buf, "PNG")
    r = mp.post("/micropub/media", files={"file": ("blue.png", buf.getvalue(), "image/png")})
    assert r.status_code == 201 and "/uploads/" in r.headers["location"]
    photo = r.headers["location"]
    # a photo from the library, and one on the server's own network that's never fetched
    r = mp.post("/micropub", json={"type": ["h-entry"], "properties": {
        "content": ["With pictures"], "photo": [{"value": photo, "alt": "Blue"}, "http://127.0.0.1/secret.png"]}})
    body = posts.load_post_body(urlsplit(r.headers["location"]).path.rsplit("/", 1)[-1])
    assert "![Blue](/uploads/" in body and "127.0.0.1" not in body


def test_signing_out_revokes_the_key(app, admin, app_page):
    key = _connect(app, admin, "read")
    TestClient(app).post("/indieauth/token", data={"action": "revoke", "token": key})
    assert apikeys.check(key) is None
    assert TestClient(app, headers={"Authorization": f"Bearer {key}"}).get("/micropub?q=config").status_code == 401


def test_not_on_the_demo(app, admin, app_page, monkeypatch):
    _, challenge = _pkce()
    monkeypatch.setattr(config, "DEMO_MODE", True)
    assert "the demo" in _ask(admin, challenge).text
