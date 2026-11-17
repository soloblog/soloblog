"""Lists that could grow to thousands stay a page at a time."""
from soloblog import posts
from conftest import save_post
from soloblog.db import get_db


def test_link_picker_searches_on_the_server(admin):
    for n in range(35):
        save_post(admin, title=f"Picker post {n:02d}", published="")
    html = admin.get("/admin/link-picker?q=picker+post").text
    assert html.count("link-picker-row") == 30 and "The newest 30 of 35" in html
    one = admin.get("/admin/link-picker?q=Picker post 07").text
    assert one.count("link-picker-row") == 1 and "newest" not in one
    assert "Nothing matches" in admin.get("/admin/link-picker?q=zzqq").text
    # 100% and _ are words, not wildcards
    assert "Nothing matches" in admin.get("/admin/link-picker?q=%25").text
    # the dialog itself carries none of them
    assert "Picker post 07" not in admin.get("/admin/new").text


def test_top_tags_and_filter_caps(admin):
    from soloblog.ui import top_options
    # the most used tag, whatever other tests have saved on the shared site
    busiest = max((n for _, n in posts.tag_counts_all()), default=0)
    for n in range(busiest + 1):
        save_post(admin, title=f"Busy tag post {n}", tags="busytag")
    save_post(admin, title="Rare tag post", tags="raretag")
    assert "busytag" in posts.top_tags(1)
    assert posts.top_tags(1) == ["busytag"]
    assert "raretag" in posts.top_tags(1, keep="RareTag")
    options = [(str(n), f"Post {n:03d}") for n in range(100)]
    capped = top_options(options, "99", limit=5)
    assert [v for v, _ in capped] == ["0", "1", "2", "3", "4", "99"]


def test_subscribers_page_at_a_time(admin):
    db = get_db()
    for n in range(55):
        db.execute("INSERT INTO subscribers (email, token, created_at) VALUES (?, ?, ?)",
                   (f"reader{n:02d}@example.com", f"scale-token-{n}", f"2026-01-01T00:00:{n:02d}"))
    db.commit()
    try:
        first = admin.get("/admin/newsletter").text
        assert first.count("list-row") == 50 and "page=2" in first
        second = admin.get("/admin/newsletter?page=2").text
        assert "reader00@example.com" in second
        found = admin.get("/admin/newsletter?q=reader07").text
        assert found.count("list-row") == 1
    finally:
        db.execute("DELETE FROM subscribers WHERE token LIKE 'scale-token-%'")
        db.commit()


def test_feed_reads_only_its_newest(admin, client):
    from soloblog import feeds
    assert len(posts.list_roll_all(feeds.FEED_SIZE)) <= feeds.FEED_SIZE
    assert client.get("/rss").status_code == 200


def test_link_picker_lists_the_built_in_pages(admin):
    from soloblog import settings
    before = {k: settings.get(k) for k in ("contact_enabled", "newsletter_mode", "newsletter_buttondown")}
    try:
        settings.set_many({"contact_enabled": "", "newsletter_mode": ""})
        html = admin.get("/admin/link-picker").text
        # first, ahead of the posts - the addresses nobody can guess
        assert html.index("Built-in pages") < html.index("Posts and pages")
        for url in ('data-url="/archive"', 'data-url="/tags"', 'data-url="/search"', 'data-url="/rss"'):
            assert url in html
        # only the ones that are there right now
        assert 'data-url="/contact"' not in html and 'data-url="/newsletter"' not in html
        settings.set_many({"contact_enabled": "1", "newsletter_mode": "buttondown",
                           "newsletter_buttondown": "someone"})
        html = admin.get("/admin/link-picker").text
        assert 'data-url="/contact"' in html and 'data-url="/newsletter"' in html
        # typing finds them by name or address, and leaves the rest out
        found = admin.get("/admin/link-picker?q=news").text
        assert 'data-title="Newsletter"' in found and 'data-url="/archive"' not in found
        assert 'data-url="/contact"' in admin.get("/admin/link-picker?q=/contact").text
    finally:
        settings.set_many(before)
