"""The API (routes/api.py) with API keys (apikeys.py): what each scope
may do, and the abuse cases - no key, a wrong, revoked or guessed key,
the admin's login cookie on its own, a key reaching past its scope, an
image address inside the server's own network, the demo."""
from pathlib import Path
import io

import pytest
from PIL import Image
from starlette.testclient import TestClient

from soloblog import apikeys
from soloblog import config
from soloblog import posts
from soloblog.db import get_db
from conftest import save_post


@pytest.fixture
def keys():
    made = {scope: apikeys.create(f"test {scope}", scope) for scope in apikeys.SCOPES}
    yield made
    db = get_db()
    db.execute("DELETE FROM api_keys")
    db.execute("DELETE FROM rate_hits WHERE bucket IN ('api', 'api-fail')")
    db.commit()


def _as(app, key):
    c = TestClient(app, follow_redirects=False)
    c.headers["Authorization"] = f"Bearer {key}"
    return c


def test_no_key_no_entry(app, client, admin, keys):
    assert client.get("/api/v1/posts").status_code == 401
    assert client.get("/api/v1/posts").headers["www-authenticate"].startswith("Bearer")
    # the admin's login is not a key - a page on another site can't use it through the browser
    assert admin.get("/api/v1/posts").status_code == 401
    assert admin.post("/api/v1/posts", json={"title": "Sneaky"}, headers={"Origin": "https://evil.example"}
                      ).status_code == 401
    # a key in the address (where logs keep it) isn't read
    assert client.get(f"/api/v1/posts?key={keys['read']}").status_code == 401
    assert _as(app, "sb_" + "x" * 43).get("/api/v1/site").status_code == 401
    assert _as(app, keys["read"]).get("/api/v1/site").json()["key"]["scope"] == "read"


def test_keys_are_kept_as_hashes_and_can_be_revoked(app, keys):
    stored = " ".join(str(v) for r in get_db().execute("SELECT * FROM api_keys") for v in tuple(r))
    assert not any(k in stored for k in keys.values())
    assert _as(app, keys["read"]).get("/api/v1/posts").status_code == 200
    row = get_db().execute("SELECT * FROM api_keys WHERE scope='read'").fetchone()
    assert row["last_used_at"]
    apikeys.revoke(row["id"])
    assert _as(app, keys["read"]).get("/api/v1/posts").status_code == 401


def test_read_sees_everything_but_writes_nothing(app, admin, keys):
    slug = save_post(admin, title="A draft for the API", body="Secret draft words.", published="")
    c = _as(app, keys["read"])
    listed = c.get("/api/v1/posts?status=draft").json()
    assert any(p["slug"] == slug and p["status"] == "draft" for p in listed["posts"])
    one = c.get(f"/api/v1/posts/{slug}").json()
    assert one["body"].strip() == "Secret draft words." and one["title"] == "A draft for the API"
    assert c.get("/api/v1/posts/no-such-post").status_code == 404
    assert c.post("/api/v1/posts", json={"title": "Nope"}).status_code == 403
    assert c.post(f"/api/v1/posts/{slug}/publish").status_code == 403


def test_a_layout_field_is_ignored_not_refused_and_never_given_or_written(app, keys):
    # an app written before layouts went still sends one
    c = _as(app, keys["draft"])
    r = c.post("/api/v1/posts", json={"title": "Sent with an old field", "body": "Words.", "layout": "recipe"})
    assert r.status_code == 201, r.text
    assert "layout" not in r.json()
    slug = r.json()["slug"]
    assert "layout" not in Path(posts._path(slug)).read_text(encoding="utf-8")
    r = c.patch(f"/api/v1/posts/{slug}", json={"layout": "landing", "summary": "Kept"})
    assert r.status_code == 200 and r.json()["summary"] == "Kept" and "layout" not in r.json()
    # a typo is still an error, and a layout that isn't text is no different from one that is
    assert c.post("/api/v1/posts", json={"title": "x", "layut": "recipe"}).status_code == 400
    assert c.post("/api/v1/posts", json={"title": "Odd one", "layout": 12}).status_code == 201
    assert "layout" not in c.get(f"/api/v1/posts/{slug}").json()


def test_drafts_key_writes_drafts_only(app, admin, keys):
    c = _as(app, keys["draft"])
    r = c.post("/api/v1/posts", json={"title": "Written by an app", "body": "Hello from the API.",
                                       "tags": ["api", "test"]})
    assert r.status_code == 201, r.text
    post = r.json()
    assert post["status"] == "draft" and post["tags"] == ["api", "test"] and r.headers["location"].endswith(post["slug"])
    # the same save as the editor's: the file on disk, search
    assert "Hello from the API." in Path(posts._path(post["slug"])).read_text(encoding="utf-8")
    # changing it - only what's sent changes
    r = c.patch(f"/api/v1/posts/{post['slug']}", json={"summary": "Short"})
    assert r.json()["summary"] == "Short" and r.json()["tags"] == ["api", "test"]
    assert r.json()["body"].strip() == "Hello from the API."
    # anything that goes live needs Publish
    assert c.post("/api/v1/posts", json={"title": "Live", "published": True}).status_code == 403
    assert c.patch(f"/api/v1/posts/{post['slug']}", json={"published": True}).status_code == 403
    assert c.patch(f"/api/v1/posts/{post['slug']}", json={"scheduled_at": "2099-01-01T09:00:00Z"}).status_code == 403
    live = save_post(admin, title="Already live", body="Live words.")
    assert c.patch(f"/api/v1/posts/{live}", json={"body": "Defaced"}).status_code == 403
    assert "Defaced" not in posts.load_post_body(live)
    assert c.delete(f"/api/v1/posts/{post['slug']}").status_code == 403


def test_publish_key_publishes_and_trashes(app, keys):
    c = _as(app, keys["publish"])
    slug = c.post("/api/v1/posts", json={"title": "Publish me"}).json()["slug"]
    assert c.post(f"/api/v1/posts/{slug}/publish").json()["status"] == "published"
    assert posts.is_live(posts.get_post(slug))
    when = c.patch(f"/api/v1/posts/{slug}", json={"scheduled_at": "2099-01-01T09:00:00+10:00"}).json()
    assert when["status"] == "scheduled" and when["scheduled_at"] == "2098-12-31T23:00:00"
    assert c.post(f"/api/v1/posts/{slug}/unpublish").json()["status"] == "draft"
    assert c.delete(f"/api/v1/posts/{slug}").json() == {"trashed": slug}
    assert not posts.get_post(slug) and any(t["slug"] == slug for t in posts.list_trash())


def test_what_is_sent_is_checked(app, keys):
    c = _as(app, keys["publish"])
    assert "Not a field" in c.post("/api/v1/posts", json={"title": "x", "author": "me"}).json()["error"]
    assert c.post("/api/v1/posts", content=b"not json").status_code == 400
    assert c.post("/api/v1/posts", content=b"{broken", headers={"Content-Type": "application/json"}).status_code == 400
    assert c.post("/api/v1/posts", json=["a list"]).status_code == 400
    assert c.post("/api/v1/posts", json={"title": " "}).status_code == 400
    assert c.post("/api/v1/posts", json={"title": "x", "published": "yes"}).status_code == 400
    assert c.post("/api/v1/posts", json={"title": "x", "visibility": "secret"}).status_code == 400
    assert c.post("/api/v1/posts", json={"title": "x", "scheduled_at": "soon"}).status_code == 400
    assert c.post("/api/v1/posts", content=b'{"title": "' + b"x" * (2 * 1024 * 1024) + b'"}').status_code == 413


def test_an_image_turned_away_is_logged(app, keys, caplog):
    import logging
    c = _as(app, keys["draft"])
    with caplog.at_level(logging.INFO, logger="soloblog.routes.api"):
        assert c.post("/api/v1/media", files={"file": ("x.png", b"not an image", "image/png")}).status_code == 400
    assert any("turned away" in r.getMessage() and "not an image" in r.getMessage() for r in caplog.records)


def test_images_but_never_from_inside_the_network(app, keys):
    c = _as(app, keys["draft"])
    buf = io.BytesIO()
    Image.new("RGB", (40, 30), (200, 40, 40)).save(buf, "PNG")
    r = c.post("/api/v1/media", files={"file": ("red.png", buf.getvalue(), "image/png")})
    assert r.status_code == 201 and r.json()["url"].startswith("/uploads/")
    assert c.post("/api/v1/media", files={"file": ("x.png", b"not an image", "image/png")}).status_code == 400
    for inside in ("http://127.0.0.1/secret.png", "http://169.254.169.254/latest/meta-data/",
                   "http://localhost:6379/", "file:///etc/passwd"):
        assert c.post("/api/v1/media", json={"url": inside}).status_code == 400, inside
    assert _as(app, keys["read"]).post("/api/v1/media", json={"url": "https://example.com/a.png"}).status_code == 403


def test_guessing_is_slowed_down(app, keys):
    wrong = _as(app, "sb_wrong")
    codes = [wrong.get("/api/v1/site").status_code for _ in range(22)]
    assert codes[0] == 401 and codes[-1] == 429


def test_off_in_the_demo(app, keys, monkeypatch):
    monkeypatch.setattr(config, "DEMO_MODE", True)
    assert _as(app, keys["publish"]).get("/api/v1/posts").status_code == 403


def test_keys_are_made_and_revoked_in_settings(admin, keys):
    r = admin.post("/admin/apikeys/new", data={"name": "My laptop", "scope": "publish"}, headers={"HX-Request": "true"})
    shown = r.text.split('data-copy="')[1].split('"')[0]
    assert shown.startswith("sb_") and "copy it now" in r.text
    assert apikeys.check(shown)["scope"] == "publish" and apikeys.check(shown)["name"] == "My laptop"
    # never again
    page = admin.get("/admin/settings?tab=integrations").text
    assert shown not in page and "My laptop" in page and shown[:9] in page
    key_id = apikeys.check(shown)["id"]
    admin.post(f"/admin/apikeys/{key_id}/revoke", headers={"HX-Request": "true"})
    assert apikeys.check(shown) is None
    assert "Give the key a name" in admin.post("/admin/apikeys/new", data={"name": " "}).text


def test_one_choice_for_who_may_publish(app, admin, keys):
    # two switches that looked the same: "Posts from apps arrive as drafts"
    # covered only Micropub, and nothing said either one limited a key.
    # Now one choice, for every way in - and a key's row says what it does.
    from soloblog import settings
    try:
        page = admin.post("/admin/apikeys/publishing", data={"apps_publish": "none"},
                          headers={"HX-Request": "true"}).text
        assert settings.get("apps_publish") == "none" and "Everything posted with this key arrives as a draft" in page
        admin.post("/admin/apikeys/publishing", data={"apps_publish": "everyone!"}, headers={"HX-Request": "true"})
        assert settings.get("apps_publish") == "none"
        # held back: a new post asked to go live arrives as a draft; the rest says why
        c = _as(app, keys["publish"])
        r = c.post("/api/v1/posts", json={"title": "Held back", "published": True})
        assert r.status_code == 201 and r.json()["status"] == "draft", r.json()
        r = c.post(f"/api/v1/posts/{r.json()['slug']}/publish")
        assert r.status_code == 403 and "kept to the author" in r.json()["error"]
        # a drafts key is still told it's the key
        r = _as(app, keys["draft"]).post("/api/v1/posts", json={"title": "No", "published": True})
        assert r.status_code == 403 and "needs a key with Publish" in r.json()["error"]
        settings.set_many({"apps_publish": "apps"})
        assert c.post("/api/v1/posts", json={"title": "Live now", "published": True}).json()["status"] == "published"
        assert "AI assistants using this key write drafts" in admin.get("/admin/settings?tab=integrations").text
        assert apikeys.may_publish("api") and apikeys.may_publish("ghost") and not apikeys.may_publish("mcp")
        settings.set_many({"apps_publish": "all"})
        assert apikeys.may_publish("mcp")
        assert "write drafts" not in admin.get("/admin/settings?tab=integrations").text.split("api-keys-body")[1][:3000]
    finally:
        settings.set_many({"apps_publish": "apps"})



def test_a_key_says_what_last_used_it_and_when(app, admin, keys):
    # "last used" was a date, noted every 5 minutes; now the time, to the
    # minute, and what used it - so an unexpected use stands out
    from datetime import timedelta
    from soloblog import render, tz
    assert apikeys.TOUCH_EVERY == timedelta(minutes=1)
    key = keys["publish"]
    via = lambda: get_db().execute("SELECT last_used_via FROM api_keys WHERE scope='publish'").fetchone()[0]  # noqa: E731
    _as(app, key).get("/api/v1/posts")
    assert via() == "api"
    # something else using it is noted at once, inside the minute
    _as(app, key).post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    assert via() == "mcp"
    _as(app, key).get("/micropub?q=config")
    assert via() == "micropub"
    body = admin.get("/admin/settings?tab=integrations").text
    assert "last used today at " in body and " by a writing app" in body
    # a wrong key notes nothing
    _as(app, key + "x").get("/api/v1/posts")
    assert via() == "micropub"
    now = tz.utcnow()
    assert render.format_when(now.isoformat()) == f"today at {tz.to_local(now).strftime('%H:%M')}"
    assert render.format_when((now - timedelta(days=1)).isoformat()).startswith("yesterday at ")
    assert " at " in render.format_when((now - timedelta(days=9)).isoformat())
    assert render.format_when("nonsense") == "nonsense"


def test_a_ghost_apps_key_isnt_said_to_be_held_back_from_assistants(admin):
    from soloblog import settings
    apikeys.create_signed("Ulysses", "publish")
    try:
        page = admin.get("/admin/settings?tab=integrations").text
        assert "AI assistants using this key write drafts" not in page
        settings.set_many({"apps_publish": "none"})
        assert "Everything posted with this key arrives as a draft" in admin.get("/admin/settings?tab=integrations").text
    finally:
        settings.set_many({"apps_publish": "apps"})
        get_db().execute("DELETE FROM api_keys")
        get_db().commit()
