"""Publishing from apps that publish to Ghost (routes/ghost.py) with a
signed key (apikeys.create_signed). Tokens are made as Ghost's own client
libraries make them - and every way one can be wrong is refused."""
import base64
import hashlib
import hmac
import io
import json
import time

import pytest
from PIL import Image
from starlette.testclient import TestClient

from soloblog import apikeys
from soloblog import config
from soloblog import posts
from soloblog.db import get_db
from conftest import save_post

ADMIN = "/ghost/api/admin"


def _b64(data) -> str:
    raw = data if isinstance(data, bytes) else json.dumps(data, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def token(key, aud="/admin/", ttl=300, alg="HS256", iat=None, secret=None):
    kid, hex_secret = key.split(":")
    iat = int(time.time()) if iat is None else iat
    signing = f"{_b64({'alg': alg, 'typ': 'JWT', 'kid': kid})}.{_b64({'iat': iat, 'exp': iat + ttl, 'aud': aud})}"
    sig = hmac.new(bytes.fromhex(secret or hex_secret), signing.encode(), hashlib.sha256).digest()
    return f"{signing}.{_b64(sig)}"


@pytest.fixture
def keys():
    made = {scope: apikeys.create_signed(f"ghost {scope}", scope) for scope in apikeys.SCOPES}
    yield made
    db = get_db()
    db.execute("DELETE FROM api_keys")
    db.execute("DELETE FROM rate_hits WHERE bucket IN ('api', 'api-fail')")
    db.commit()


def _as(app, key, **kw):
    return TestClient(app, headers={"Authorization": f"Ghost {token(key, **kw)}"})


def test_the_key_and_its_tokens(app, client, keys):
    key = keys["publish"]
    kid, secret = key.split(":")
    assert len(kid) == 24 and len(secret) == 64
    # the secret isn't kept - not even in a backup of the database
    stored = " ".join(str(v) for r in get_db().execute("SELECT * FROM api_keys") for v in tuple(r))
    assert secret not in stored
    assert client.get(f"{ADMIN}/site/").json()["site"]["url"] == config.BASE_URL + "/"
    assert _as(app, key).get(f"{ADMIN}/users/me/").status_code == 200
    # every way a token can be wrong
    for bad in ({"alg": "none"}, {"secret": "00" * 32}, {"ttl": 3600}, {"iat": int(time.time()) - 600},
                {"aud": "/content/"}):
        assert _as(app, key, **bad).get(f"{ADMIN}/users/me/").status_code == 401, bad
    assert client.get(f"{ADMIN}/users/me/").status_code == 401
    assert client.get(f"{ADMIN}/users/me/", headers={"Authorization": "Ghost not.a.token"}).status_code == 401
    # a signed key isn't a bearer key, nor the other way round
    assert client.get("/api/v1/site", headers={"Authorization": f"Bearer {key}"}).status_code == 401
    bearer = apikeys.create("plain", "publish")
    assert client.get(f"{ADMIN}/users/me/", headers={"Authorization": f"Ghost {bearer}"}).status_code == 401
    # revoked
    apikeys.revoke(get_db().execute("SELECT id FROM api_keys WHERE key_id=?", (kid,)).fetchone()["id"])
    assert _as(app, key).get(f"{ADMIN}/users/me/").status_code == 401


def test_publishing_like_ulysses(app, admin, keys):
    c = _as(app, keys["publish"])
    r = c.post(f"{ADMIN}/posts/?source=html", json={"posts": [{
        "title": "From Ulysses", "html": "<p>Written <em>elsewhere</em>.</p><h2>A part</h2><p>More.</p>",
        "status": "draft", "tags": [{"name": "writing"}, "apps"], "custom_excerpt": "Short", "slug": "ulysses-post",
        "visibility": "members"}]})
    assert r.status_code == 201, r.text
    post = r.json()["posts"][0]
    assert post["slug"] == "ulysses-post" and post["status"] == "draft" and post["visibility"] == "members"
    body = posts.load_post_body("ulysses-post")
    assert "*elsewhere*" in body and "## A part" in body
    assert posts.get_post("ulysses-post")["tags"] == "writing, apps"
    # update, then publish
    r = c.put(f"{ADMIN}/posts/{post['id']}/?source=html", json={"posts": [{
        "title": "From Ulysses, again", "html": "<p>Changed.</p>", "updated_at": post["updated_at"],
        "status": "published"}]})
    assert r.status_code == 200 and r.json()["posts"][0]["status"] == "published"
    assert posts.is_live(posts.get_post("ulysses-post")) and posts.load_post_body("ulysses-post").strip() == "Changed."
    assert c.get(f"{ADMIN}/posts/{post['id']}/").json()["posts"][0]["title"] == "From Ulysses, again"
    assert any(t["name"] == "writing" for t in c.get(f"{ADMIN}/tags/?limit=all").json()["tags"])
    assert c.delete(f"{ADMIN}/posts/{post['id']}/").status_code == 204 and not posts.get_post("ulysses-post")


def test_markdown_from_mobiledoc_and_older_addresses(app, keys):
    doc = json.dumps({"version": "0.3.1", "cards": [["markdown", {"markdown": "# Hi\n\nIn **markdown**."}]]})
    r = _as(app, keys["draft"], aud="/v3/admin/").post("/ghost/api/v3/admin/posts/",
                                                       json={"posts": [{"title": "Mobiledoc", "mobiledoc": doc}]})
    assert r.status_code == 201
    assert "In **markdown**." in posts.load_post_body(r.json()["posts"][0]["slug"])


def test_a_drafts_key_stays_in_drafts(app, admin, keys):
    c = _as(app, keys["draft"])
    assert c.post(f"{ADMIN}/posts/", json={"posts": [{"title": "Live?", "html": "<p>x</p>",
                                                       "status": "published"}]}).status_code == 403
    live = save_post(admin, title="Live via the editor", body="Mine.")
    row = posts.get_post(live)
    assert c.put(f"{ADMIN}/posts/{row['id']}/", json={"posts": [{"html": "<p>Defaced</p>"}]}).status_code == 403
    assert c.delete(f"{ADMIN}/posts/{row['id']}/").status_code == 403
    assert posts.load_post_body(live).strip() == "Mine."
    assert _as(app, keys["read"]).post(f"{ADMIN}/posts/", json={"posts": [{"title": "x"}]}).status_code == 403


def test_images(app, keys):
    buf = io.BytesIO()
    Image.new("RGB", (16, 16), (90, 10, 10)).save(buf, "PNG")
    r = _as(app, keys["draft"]).post(f"{ADMIN}/images/upload/", files={"file": ("dark.png", buf.getvalue(), "image/png")},
                                     data={"ref": "dark.png"})
    assert r.status_code == 201
    image = r.json()["images"][0]
    assert image["url"].startswith(config.BASE_URL + "/uploads/") and image["ref"] == "dark.png"
    # as a cover, it's kept as the site's own address
    r = _as(app, keys["draft"]).post(f"{ADMIN}/posts/", json={"posts": [{"title": "With a cover", "html": "<p>x</p>",
                                                                          "feature_image": image["url"]}]})
    assert posts.get_post(r.json()["posts"][0]["slug"])["cover_image"].startswith("/uploads/")


def test_made_in_settings(admin, keys):
    r = admin.post("/admin/apikeys/new", data={"name": "Ulysses", "scope": "publish", "kind": "signed"},
                   headers={"HX-Request": "true"})
    shown = r.text.split('data-copy="')[1].split('"')[0]
    assert len(shown.split(":")[0]) == 24 and len(shown.split(":")[1]) == 64
    assert "Ghost apps" in admin.get("/admin/settings?tab=integrations").text


def test_not_on_the_demo(app, keys, monkeypatch):
    monkeypatch.setattr(config, "DEMO_MODE", True)
    assert _as(app, keys["publish"]).get(f"{ADMIN}/users/me/").status_code == 403


def test_a_ghost_app_held_back_writes_drafts(app, admin, keys):
    # "Posts from apps arrive as drafts" never covered Ghost apps, despite
    # its name; the one choice does
    from soloblog import settings
    settings.set_many({"apps_publish": "none"})
    try:
        c = _as(app, keys["publish"])
        r = c.post(f"{ADMIN}/posts/", json={"posts": [{"title": "Held", "html": "<p>x</p>", "status": "published"}]})
        assert r.status_code == 201 and r.json()["posts"][0]["status"] == "draft"
        live = posts.get_post(save_post(admin, title="Mine, live", body="Mine."))
        r = c.put(f"{ADMIN}/posts/{live['id']}/", json={"posts": [{"html": "<p>Changed</p>"}]})
        assert r.status_code == 403 and "kept to the author" in r.text
        assert c.delete(f"{ADMIN}/posts/{live['id']}/").status_code == 403
    finally:
        settings.set_many({"apps_publish": "apps"})
