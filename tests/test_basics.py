from datetime import UTC
def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_homepage_renders(client):
    assert client.get("/").status_code == 200


def test_admin_pages_need_login(client):
    for path in ("/admin/posts", "/admin/media", "/admin/comments", "/admin/settings"):
        r = client.get(path)
        assert r.status_code == 303 and r.headers["location"] == "/login", path


def test_admin_pages_render(admin):
    for path in ("/admin/posts", "/admin/new", "/admin/media", "/admin/comments"):
        assert admin.get(path).status_code == 200, path
    for tab in ("name", "visitors", "style", "banner", "profile", "editor", "integrations", "security", "backup"):
        assert admin.get(f"/admin/settings?tab={tab}").status_code == 200, tab


def test_wrong_password_is_rejected(client):
    r = client.post("/login", data={"password": "nope"})
    assert r.status_code == 200
    assert "Wrong password" in r.text


def test_feeds(client):
    assert client.get("/rss").status_code == 200
    assert client.get("/sitemap.xml").status_code == 200
    assert "Sitemap" in client.get("/robots.txt").text


# everything the General form sends - an unchecked checkbox is
# simply absent, so leaving comments_enabled out would turn comments off
GENERAL = {"site_title": "My Blog", "comments_enabled": "1", "timezone": "UTC"}


def test_analytics_only_for_visitors(admin, client):
    admin.post("/admin/settings/name", headers={"hx-request": "true"},
               data={**GENERAL, "analytics_provider": "plausible", "analytics_id": "example.com"})
    try:
        assert 'data-domain="example.com"' in client.get("/").text
        assert "plausible.io" not in admin.get("/").text
        assert "plausible.io" not in client.get("/login").text
    finally:
        admin.post("/admin/settings/name", headers={"hx-request": "true"},
                   data={**GENERAL, "analytics_provider": "", "analytics_id": ""})


def test_analytics_id_is_validated(admin):
    from soloblog import settings
    admin.post("/admin/settings/name", headers={"hx-request": "true"},
               data={**GENERAL, "analytics_provider": "google", "analytics_id": "x');alert(1)//"})
    assert settings.get("analytics_id") == ""
    admin.post("/admin/settings/name", headers={"hx-request": "true"},
               data={**GENERAL, "analytics_provider": "", "analytics_id": ""})


def test_links_page_and_support(admin, client):
    assert client.get("/links").status_code == 404
    admin.post("/admin/settings/profile", headers={"hx-request": "true"}, data={
        "author_name": "Sam", "links_enabled": "1", "links_items": "Newsletter|https://example.com/n\nBad|javascript:alert(1)",
        "support_kofi": "https://ko-fi.com/sam", "support_paypal": "javascript:alert(1)",
        "links_show_support": "1", "links_show_posts": "1", "support_on_posts": "1"})
    try:
        r = client.get("/links")
        assert r.status_code == 200
        assert "Newsletter" in r.text and "https://ko-fi.com/sam" in r.text
        assert "javascript:" not in r.text
        from conftest import save_post
        slug = save_post(admin, title="Supported post")
        assert "ko-fi.com/sam" in client.get(f"/post/{slug}").text
    finally:
        admin.post("/admin/settings/profile", headers={"hx-request": "true"}, data={"author_name": ""})


def test_stats_page_counts_visitor_views(admin, client):
    from conftest import save_post
    from soloblog import posts
    slug = save_post(admin, title="Counted post")
    client.get(f"/post/{slug}")
    client.get(f"/post/{slug}")
    admin.get(f"/post/{slug}")  # the admin's own visit doesn't count
    assert posts.daily_views(30)[-1][1] >= 2
    assert posts.views_since(posts.daily_views(30)[0][0])[slug] == 2
    r = admin.get("/admin/stats")
    assert r.status_code == 200 and "Counted post" in r.text
    for key, buckets in (("7d", 7), ("90d", 13), ("12m", 12)):
        series = posts.views_by_period(key)
        assert len(series) == buckets and series[-1]["views"] >= 2
        assert admin.get(f"/admin/stats?range={key}").status_code == 200
    # the months keep their names where the site writes the day first -
    # every one read "1 2026"
    from datetime import date
    from soloblog import settings
    settings.set_many({"english_spelling": "gb"})
    try:
        page = admin.get("/admin/stats?range=12m").text
        assert date.today().strftime("%b %Y") in page and f"1 {date.today().year}" not in page
        assert admin.get("/admin/stats?range=90d").status_code == 200
    finally:
        settings.set_many({"english_spelling": "us"})


def test_a_link_check_that_breaks_is_logged_and_can_run_again(monkeypatch, caplog):
    import logging
    from soloblog import linkcheck

    def broken():
        raise RuntimeError("a bug")
    monkeypatch.setattr(linkcheck, "_links_by_post", broken)
    monkeypatch.setattr(linkcheck, "_running", True)
    with caplog.at_level(logging.ERROR, logger="soloblog.linkcheck"):
        linkcheck._run()
    assert any("stopped" in r.getMessage() and r.exc_info for r in caplog.records)
    assert not linkcheck.state()["running"]


def test_an_error_page_that_fails_falls_back_to_words_and_is_logged(app, monkeypatch, caplog):
    import logging
    from starlette.testclient import TestClient
    from soloblog import ui
    client = TestClient(app, raise_server_exceptions=False)

    def broken(*a, **kw):
        raise RuntimeError("the error page broke")
    monkeypatch.setattr(ui, "ErrorPage", broken)
    with caplog.at_level(logging.ERROR, logger="soloblog.app"):
        r = client.get("/no-such-address-anywhere")
    # the missing page's own ErrorPage fails first (a 500), then the 500's
    assert r.status_code == 500 and r.text == "Something went wrong"
    assert any("couldn't be shown" in r.getMessage() and r.exc_info for r in caplog.records)


def test_link_checker_finds_internal_breakage(admin):
    import time
    from soloblog import linkcheck
    from conftest import save_post
    save_post(admin, title="Links out", body="[gone](/post/never-existed) [here](/post/links-out) ![](/uploads/nope.webp)")
    assert linkcheck.check_url("/post/never-existed") == "No such post"
    assert linkcheck.check_url("/uploads/nope.webp") == "Image missing"
    admin.post("/admin/stats/links", headers={"hx-request": "true"})
    for _ in range(100):
        if not linkcheck.state()["running"]:
            break
        time.sleep(0.1)
    broken = {b["url"] for b in linkcheck.state()["broken"]}
    assert "/post/never-existed" in broken and "/uploads/nope.webp" in broken
    assert "/post/links-out" not in broken
    # kept in the database, so a restart doesn't lose it
    from soloblog import settings
    assert "/post/never-existed" in settings.get("linkcheck_last")
    assert "never-existed" in admin.get("/admin/stats").text


def test_setup_wizard(admin):
    from soloblog import settings
    settings.set_many({"setup_done": "0"})
    for step in ("site", "you", "look", "style", "done"):
        r = admin.get(f"/admin/welcome?step={step}")
        assert r.status_code == 200 and 'class="steps' in r.text, step
    # looking at the last screen finishes nothing: the last Continue does
    assert settings.get("setup_done") == "0"
    # Back and Continue, and nothing else to choose between: a screen left as it is changes nothing
    you = admin.get("/admin/welcome?step=you").text
    assert ">Skip<" not in you and 'href="/admin/welcome?step=site"' in you
    # email isn't a screen of the setup: it has one home, Settings > Email. An address
    # the setup doesn't know opens its first screen
    email = admin.get("/admin/welcome?step=email").text
    assert 'name="admin_email"' not in email and 'name="site_title"' in email
    r = admin.post("/admin/welcome/site", data={"site_title": "Wizard Blog", "tagline": "Hi", "timezone": "Europe/Paris"})
    assert r.headers["location"] == "/admin/welcome?step=you"
    assert settings.get("timezone") == "Europe/Paris"
    r = admin.post("/admin/welcome/you", data={"author_name": "Wiz"})
    assert r.headers["location"] == "/admin/welcome?step=look"
    look = admin.get("/admin/welcome?step=look").text
    assert 'name="header_icon_url"' in look and 'name="theme"' in look
    r = admin.post("/admin/welcome/look", data={"theme": "dracula", "header_icon_url": "/uploads/logo.webp"})
    assert r.headers["location"] == "/admin/welcome?step=style"
    assert settings.get("header_icon_url") == "/uploads/logo.webp"
    assert "Writer's notebook" in admin.get("/admin/welcome?step=style").text
    r = admin.post("/admin/welcome/style", data={"preset": "notebook"})
    assert r.headers["location"] == "/admin/welcome?step=done" and settings.get("roll_style") == "minimal"
    # only one of the site's own uploads
    admin.post("/admin/welcome/look", data={"theme": "dracula", "header_icon_url": "https://evil.example/x.png"})
    assert settings.get("header_icon_url") == "/uploads/logo.webp"
    from soloblog import presets
    presets.undo()
    assert settings.get("theme") == "dracula" and settings.get("setup_done") == "1"
    # gone through again later, it ends on the same screen
    done = admin.get("/admin/welcome?step=done").text
    assert "is ready</h1>" in done and 'class="steps' in done
    settings.set_many({"site_title": "My Blog", "tagline": "", "timezone": "UTC", "author_name": "",
                       "theme": "light", "roll_style": "list", "header_icon_url": ""})


def test_settings_forms_save_only_their_own_fields(admin):
    from soloblog import settings
    before = settings.get("comments_enabled")
    # a form that doesn't list comments_enabled (an unsent checkbox would
    # otherwise read as "off") leaves it alone
    admin.post("/admin/settings/name", headers={"hx-request": "true"},
               data={"site_title": "Partial", "declared_fields": "site_title,tagline"})
    try:
        assert settings.get("site_title") == "Partial"
        assert settings.get("comments_enabled") == before
    finally:
        admin.post("/admin/settings/name", headers={"hx-request": "true"}, data=GENERAL)


def test_sources_by_name_only(admin, client):
    from soloblog import sources
    from conftest import save_post
    assert sources.name("https://www.google.com/search?q=x") == "Google"
    assert sources.name("https://news.ycombinator.com/item?id=1") == "Hacker News"
    assert sources.name("https://mastodon.social/@me/1") == "mastodon.social"
    assert sources.name("", "utm_source=newsletter&utm_medium=email") == "newsletter"
    assert sources.name("http://localhost:5001/", "", "localhost") == ""  # its own pages aren't a source
    slug = save_post(admin, title="Where from")
    client.get(f"/post/{slug}", headers={"referer": "https://t.co/abc"})
    client.get(f"/post/{slug}", headers={"referer": "https://t.co/xyz"})
    admin.get(f"/post/{slug}", headers={"referer": "https://t.co/admin"})  # the admin isn't counted
    assert dict(sources.top("2000-01-01"))["X"] == 2
    html = admin.get("/admin/stats").text
    assert "Top sources" in html and ">X<" in html


def test_now_is_stored_in_the_same_shape_as_before():
    """Times are kept as plain UTC text and compared as text in SQL - so
    utcnow() has no zone attached, or new times would gain "+00:00"."""
    from datetime import datetime
    from soloblog.tz import utcnow
    now = utcnow()
    assert now.tzinfo is None and "+" not in now.isoformat()
    assert abs((datetime.now(UTC).replace(tzinfo=None) - now).total_seconds()) < 5


def test_keep_me_signed_in(app):
    """Ticked (as it starts): the login outlasts the browser. Unticked, for
    a shared computer: gone when the browser closes."""
    from starlette.testclient import TestClient
    from conftest import PASSWORD
    assert 'name="keep" value="1" checked' in TestClient(app).get("/login").text
    for data, lasting in (({"password": PASSWORD, "keep": "1"}, True), ({"password": PASSWORD}, False)):
        c = TestClient(app, follow_redirects=False)
        r = c.post("/login", data=data)
        cookie = next(v for k, v in r.headers.multi_items() if k == "set-cookie" and v.startswith("blog_session="))
        assert ("Max-Age=" in cookie) == lasting, cookie
        assert c.get("/admin/posts").status_code == 200
