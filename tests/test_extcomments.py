from soloblog import config
from soloblog import extcomments
from soloblog import settings
from conftest import save_post
from test_basics import GENERAL

OFF = {"comments_system": "", "comments_autoload": "0", "giscus_repo": "", "giscus_repo_id": "",
       "giscus_category": "", "giscus_category_id": "", "bluesky_handle": "", "isso_url": "", "remark42_url": ""}


def _general(admin, **fields):
    return admin.post("/admin/settings/name", headers={"hx-request": "true"}, data={**GENERAL, **fields})


def test_each_system_replaces_the_comment_form(admin, client):
    slug = save_post(admin, title="Elsewhere comments")
    setups = {
        "giscus": {"giscus_repo": "you/blog", "giscus_repo_id": "R_kgDOabc", "giscus_category": "Comments",
                   "giscus_category_id": "DIC_kwDOabc"},
        "isso": {"isso_url": "https://comments.example.com/"},
        "remark42": {"remark42_url": "https://remark42.example.com", "remark42_site_id": "blog"},
    }
    try:
        for name, fields in setups.items():
            r = _general(admin, comments_system=name, comments_autoload="1", **fields)
            assert "text-success" in r.text, (name, r.text)
            html = client.get(f"/post/{slug}").text
            assert f'data-ext-comments="{name}"' in html and "Load comments" in html, name
            assert 'id="comment-form"' not in html, name
            # nothing from the service is on the page until the reader asks
            assert "giscus.app/client.js" not in html
            assert 'data-autoload="1"' in html, name
            if name == "isso":
                assert settings.get("isso_url") == "https://comments.example.com"
    finally:
        settings.set_many(OFF)
    assert 'id="comment-form"' in client.get(f"/post/{slug}").text


def test_an_unfinished_setup_keeps_soloblogs_own(admin, client):
    slug = save_post(admin, title="Half set up")
    try:
        r = _general(admin, comments_system="giscus", giscus_repo="you/blog")
        assert "until Giscus is filled in" in r.text
        assert 'id="comment-form"' in client.get(f"/post/{slug}").text
        r = _general(admin, comments_system="isso", isso_url="javascript:alert(1)")
        assert "doesn't look right" in r.text and settings.get("isso_url") == ""
    finally:
        settings.set_many(OFF)


def test_giscus_theme_uses_the_sites_colors(client, monkeypatch):
    monkeypatch.setattr(extcomments, "_theme_blocks", lambda: {
        "dracula": {"color-scheme": "dark", "--color-base-100": "oklch(28% 0.02 277)",
                    "--color-primary": "oklch(75% 0.18 346)"}})
    css = extcomments.giscus_css("dracula")
    assert css.startswith('@import url("https://giscus.app/themes/dark.css")')
    assert "--color-canvas-default: oklch(28% 0.02 277)" in css and "--color-accent-fg: oklch(75% 0.18 346)" in css
    r = client.get("/comments/giscus-theme?t=nope")
    assert r.headers["content-type"].startswith("text/css") and "themes/light.css" in r.text


def test_bluesky_replies_look_like_our_own(admin, client, monkeypatch):
    slug = save_post(admin, title="Talk about it on Bluesky")
    url = f"{config.BASE_URL}/post/{slug}"
    root = "at://did:plc:me/app.bsky.feed.post/3kroot"

    def fake(method, **params):
        if method == "app.bsky.feed.getAuthorFeed":
            return {"feed": [{"post": {"uri": root, "author": {"handle": "me.bsky.social"},
                                       "record": {"text": "New post", "embed": {"external": {"uri": url}}}}}]}
        return {"thread": {"replies": [{"post": {
            "uri": "at://did:plc:ann/app.bsky.feed.post/3kann", "likeCount": 2,
            "author": {"handle": "ann.bsky.social", "displayName": "Ann"},
            "record": {"text": "Loved this <b>post</b>", "createdAt": "2026-09-20T10:00:00.000Z"}},
            "replies": []}]}}
    monkeypatch.setattr(extcomments, "_get", fake)
    extcomments._cache.clear()
    settings.set_many({"comments_system": "bluesky", "bluesky_handle": "me.bsky.social"})
    try:
        page = client.get(f"/post/{slug}").text
        assert f'hx-get="/post/{slug}/bluesky"' in page
        html = client.get(f"/post/{slug}/bluesky").text
        assert "Ann" in html and "Loved this &lt;b&gt;post&lt;/b&gt;" in html and "chat-bubble" in html
        assert "https://bsky.app/profile/me.bsky.social/post/3kroot" in html
    finally:
        settings.set_many(OFF)
        extcomments._cache.clear()
