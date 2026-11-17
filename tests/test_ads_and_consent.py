from soloblog import settings
from conftest import save_post
from test_basics import GENERAL

CLIENT = "ca-pub-1234567890123456"


def _general(admin, **extra):
    r = admin.post("/admin/settings/name", headers={"hx-request": "true"}, data={**GENERAL, **extra})
    assert r.status_code == 200
    return r


def test_adsense_for_visitors_only(admin, client):
    assert client.get("/ads.txt").status_code == 404
    _general(admin, adsense_client=CLIENT, adsense_slot_post="1111111111", adsense_slot_roll="2222222222")
    try:
        assert client.get("/ads.txt").text == "google.com, pub-1234567890123456, DIRECT, f08c47fec0942fa0\n"
        home = client.get("/").text
        assert f"adsbygoogle.js?client={CLIENT}" in home and 'data-ad-slot="2222222222"' in home
        slug = save_post(admin, title="Ad supported")
        page = client.get(f"/post/{slug}").text
        assert 'data-ad-slot="1111111111"' in page and "Advertisement" in page
        # never for the logged-in admin, never on admin pages
        assert "adsbygoogle" not in admin.get(f"/post/{slug}").text
        assert "adsbygoogle" not in client.get("/login").text
        # pages (pinned posts) stay ad-free unless allowed
        page_slug = save_post(admin, title="About ads", pin_location="footer")
        assert "adsbygoogle" not in client.get(f"/{page_slug}").text
        _general(admin, adsense_client=CLIENT, adsense_on_pages="1")
        assert "adsbygoogle" in client.get(f"/{page_slug}").text
    finally:
        _general(admin)


def test_adsense_ids_are_validated(admin):
    r = _general(admin, adsense_client="ca-pub-123\"><script>", adsense_slot_post="abc")
    assert "ca-pub-" in r.text and "text-error" in r.text
    assert settings.get("adsense_client") == "" and settings.get("adsense_slot_post") == ""


def test_google_analytics_waits_for_consent(admin, client):
    _general(admin, analytics_provider="google", analytics_id="G-ABC123", consent_banner="1")
    try:
        html = client.get("/").text
        assert '<template id="consent-scripts">' in html and 'id="consent-banner"' in html
        # the GA script only exists inside the template, where it can't run
        before, _, after = html.partition('<template id="consent-scripts">')
        assert "googletagmanager" not in before and "googletagmanager" in after.split("</template>")[0]
        assert "Cookie choices" in html
        # without the banner, it loads straight away
        _general(admin, analytics_provider="google", analytics_id="G-ABC123")
        html = client.get("/").text
        assert 'id="consent-banner"' not in html and "googletagmanager" in html
        # cookieless providers never ask
        _general(admin, analytics_provider="plausible", analytics_id="example.com", consent_banner="1")
        assert 'id="consent-banner"' not in client.get("/").text
    finally:
        _general(admin)


def test_powered_by_line(admin, client):
    assert "Powered by" in client.get("/").text
    # the switch left out of the form reads as off - the way a browser sends it
    admin.post("/admin/settings/style", headers={"hx-request": "true"},
               data={"footer_enabled": "1", "declared_fields": "footer_enabled,footer_show_powered_by"})
    try:
        assert "Powered by" not in client.get("/").text
    finally:
        admin.post("/admin/settings/style", headers={"hx-request": "true"},
                   data={"footer_show_powered_by": "1", "declared_fields": "footer_show_powered_by"})
    assert "Support Soloblog" in admin.get("/admin/settings").text


def test_custom_code_that_tracks_waits_for_consent(admin, client):
    from soloblog import ads
    keys = ("custom_head", "custom_head_consent", "consent_banner", "analytics_provider", "analytics_id")
    before = {k: settings.get(k) for k in keys}
    code = '<script>window.trackerRan = 1;</script><meta name="tracker-check" content="1">'
    try:
        # not marked: it runs as before, and with nothing else to ask about there's no banner
        settings.set_many({"custom_head": code, "custom_head_consent": "0", "consent_banner": "1",
                           "analytics_provider": "", "analytics_id": ""})
        page = client.get("/").text
        assert "window.trackerRan" in page and 'id="consent-banner"' not in page
        assert ads.consent_reasons(settings.get_all()) == []
        # marked as tracking: inside the gate, the banner asks, Settings says why
        settings.set_many({"custom_head_consent": "1"})
        page = client.get("/").text
        gate = page[page.index('id="consent-scripts"'):]
        assert "window.trackerRan" in gate.split("</template>")[0] and 'id="consent-banner"' in page
        assert page.count("window.trackerRan") == 1
        assert "It asks about: your custom code." in admin.get("/admin/settings?tab=analytics").text
        # the admin never answers the banner, so never runs it
        assert "window.trackerRan" not in admin.get("/").text
        # the banner off: nothing waits, it runs as the admin chose
        settings.set_many({"consent_banner": "0"})
        page = client.get("/").text
        assert "window.trackerRan" in page and 'id="consent-scripts"' not in page
    finally:
        settings.set_many(before)


def test_a_site_still_set_to_a_dropped_comment_system_keeps_its_own(admin, client):
    """Disqus, Cusdis and Hyvor Talk were dropped: a site set to one shows
    Soloblog's own comments, and nothing from them loads."""
    keys = ("comments_system", "comments_enabled")
    before = {k: settings.get(k) for k in keys}
    try:
        for gone in ("disqus", "cusdis", "hyvor"):
            settings.set_many({"comments_system": gone, "comments_enabled": "1"})
            slug = save_post(admin, title=f"Comments after {gone}", body="Hello.")
            page = client.get(f"/post/{slug}").text
            assert 'id="comment-form"' in page and "data-ext-comments" not in page, gone
    finally:
        settings.set_many(before)
