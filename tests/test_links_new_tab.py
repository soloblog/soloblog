from soloblog import config, posts, settings
from soloblog.render import new_tab_links, render_post
from soloblog.newsletter import post_email_html
from conftest import save_post

def body_md():
    return (f"[out](https://other.example/a?x=1&y=2) [own]({config.BASE_URL}/about) [rel](/about) [anchor](#top) "
        "[mail](mailto:me@other.example) [tel](tel:+123) "
        '<a href="https://hand.example" target="_blank">hand</a> [bad](javascript:alert(1))')


NOTE = "(opens in a new tab)"


def _page(client, slug):
    return client.get(f"/post/{slug}").text.split("<article", 1)[-1].split("</article>")[0]


def test_off_by_default_and_when_missing(admin, client):
    assert settings.DEFAULTS["links_new_tab"] == "0"
    slug = save_post(admin, title="Links off", body=body_md())
    page = _page(client, slug)
    assert "https://other.example/a" in page and 'target="_blank"' not in page and NOTE not in page


def test_on_marks_only_links_to_other_sites(admin, client):
    slug = save_post(admin, title="Links on", body=body_md())
    settings.set_many({"links_new_tab": "1"})
    try:
        body = _page(client, slug)
    finally:
        settings.set_many({"links_new_tab": "0"})
    assert body.count('target="_blank"') == 2  # out, and hand - its own target was cleaned, so not doubled
    assert f'target="_blank">out<span class="sr-only"> {NOTE}</span></a>' in body
    assert "other.example/a?x=1&amp;y=2" in body
    assert 'rel="noopener' in body.split(">out<")[0].rsplit("<a", 1)[1]
    for text in ("own", "rel", "anchor", "mail", "tel"):
        tag = body.split(f">{text}</a>")[0].rsplit("<a", 1)[-1]
        assert "target" not in tag, text
    assert "javascript:" not in body  # the sanitiser still drops it


def test_a_hand_written_target_is_not_doubled():
    html = new_tab_links('<a href="https://x.example" target="_blank" rel="noopener">x</a>')
    assert html.count("target=") == 1 and NOTE not in html
    # nh3 removes a hand-written target, and the link then gets exactly one
    out = new_tab_links(render_post('<a href="https://x.example" target="_self">x</a>')[0])
    assert out.count("target=") == 1 and "_self" not in out


def test_own_domain_with_or_without_www_stays():
    host = config.BASE_URL.split("://", 1)[1].split("/")[0].split(":")[0]
    html = new_tab_links(f'<a href="https://www.{host}/a">a</a><a href="//{host}/b">b</a><a href="//o.example/c">c</a>')
    assert html.count('target="_blank"') == 1 and ">c<span" in html


def test_odd_addresses_do_not_crash():
    odd = '<a href="http://[bad">x</a><a href="">y</a><a>z</a>'
    assert new_tab_links(odd) == odd


def test_feeds_and_newsletter_stay_plain(admin, client):
    slug = save_post(admin, title="Plain feeds", body="[out](https://other.example/a)")
    settings.set_many({"links_new_tab": "1", "newsletter_full": "1"})
    try:
        assert "_blank" not in client.get("/rss").text and NOTE not in client.get("/rss").text
        assert "_blank" not in client.get("/feed.json").text
        mail = post_email_html(posts.get_post(slug), settings.get_all(), "tok")
        assert "other.example/a" in mail and "_blank" not in mail and NOTE not in mail
    finally:
        settings.set_many({"links_new_tab": "0", "newsletter_full": "0"})


def test_the_switch_is_in_settings_reading(admin):
    html = admin.get("/admin/settings?tab=posts").text
    assert "Open links to other sites in a new tab" in html and 'name="links_new_tab"' in html
