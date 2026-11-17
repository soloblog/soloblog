from pathlib import Path
import re
import os

from soloblog import config
from soloblog import settings
from conftest import save_post


def test_publish_and_view(admin, client):
    slug = save_post(admin, title="A published post", body="Some **bold** text.")
    r = client.get(f"/post/{slug}")
    assert r.status_code == 200
    assert "<strong>bold</strong>" in r.text


def test_draft_is_hidden_from_visitors(admin, client):
    slug = save_post(admin, title="Secret draft", published="")
    assert client.get(f"/post/{slug}").status_code == 404
    assert admin.get(f"/post/{slug}").status_code == 200


def test_post_file_is_the_source_of_truth(admin):
    slug = save_post(admin, title="On disk", body="Body text.", tags="a,b")
    text = Path(os.path.join(config.POSTS_DIR, f"{slug}.md")).read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "title: On disk" in text
    assert "Body text." in text


def test_windows_line_endings_are_saved_plain(admin):
    # what a browser sends from the editor
    slug = save_post(admin, title="Line endings", body="One.\r\n\r\n## Two\r\nThree.\r")
    raw = Path(os.path.join(config.POSTS_DIR, f"{slug}.md")).read_bytes()
    assert b"\r" not in raw and b"One.\n\n## Two\nThree." in raw


def test_scheduled_post_uses_site_timezone(admin, client):
    settings.set_many({"timezone": "Australia/Sydney"})
    try:
        # 9am in Sydney on Jan 1st (summer, UTC+11) is 22:00 UTC the day before
        slug = save_post(admin, title="Scheduled in Sydney", scheduled_at="2099-01-01T09:00")
        text = Path(os.path.join(config.POSTS_DIR, f"{slug}.md")).read_text(encoding="utf-8")
        assert "scheduled_at: 2098-12-31T22:00Z" in text
        assert client.get(f"/post/{slug}").status_code == 404
        # the editor shows it back in local time
        assert 'value="2099-01-01T09:00"' in admin.get(f"/admin/edit/{slug}").text
    finally:
        settings.set_many({"timezone": "UTC"})


def test_past_schedule_is_live(admin, client):
    slug = save_post(admin, title="Scheduled in the past", scheduled_at="2001-01-01T09:00")
    assert client.get(f"/post/{slug}").status_code == 200


def test_apostrophe_title_does_not_break_trash_button(admin):
    save_post(admin, title="Don't panic")
    html = admin.get("/admin/posts").text
    assert "Don&#x27;t panic" in html or "Don't panic" in html
    # Trash is a plain submit now (Undo comes after) - no title in any JS
    assert "confirmAction('Move" not in html


def test_search_finds_post(admin, client):
    save_post(admin, title="Searchable zebra", body="Stripes everywhere.")
    assert "Searchable zebra" in client.get("/search?q=zebra").text


def test_changing_url_redirects_old_one(admin, client):
    slug = save_post(admin, title="Old name", body="Moving soon.")
    child = save_post(admin, title="Child page", pin_location="header", parent_slug="")
    admin.post("/admin/pin/parent", data={"slug": child, "parent_slug": slug})
    r = admin.post(f"/admin/save?slug={slug}", headers={"hx-request": "true"},
                   data={"title": "Old name", "body": "Moving soon.", "published": "1", "new_slug": "new-name"})
    assert r.headers["hx-redirect"].startswith("/admin/edit/new-name")
    r = client.get(f"/post/{slug}")
    assert r.status_code == 301 and r.headers["location"] == "/post/new-name"
    assert client.get("/post/new-name").status_code == 200
    # renaming again keeps the first old URL working too
    admin.post("/admin/save?slug=new-name", headers={"hx-request": "true"},
               data={"title": "Old name", "body": "Moving soon.", "published": "1", "new_slug": "newest-name"})
    assert client.get(f"/post/{slug}").headers["location"] == "/post/newest-name"
    assert client.get("/post/new-name").headers["location"] == "/post/newest-name"
    text = Path(os.path.join(config.POSTS_DIR, "newest-name.md")).read_text(encoding="utf-8")
    assert f"- {slug}" in text and "- new-name" in text
    # the sub-page followed its parent
    assert "parent_slug: newest-name" in Path(os.path.join(config.POSTS_DIR, f"{child}.md")).read_text(encoding="utf-8")
    # a normal save keeps the redirect history
    admin.post("/admin/save?slug=newest-name", headers={"hx-request": "true"},
               data={"title": "Old name", "body": "Edited.", "published": "1", "new_slug": "newest-name"})
    assert client.get("/post/new-name").status_code == 301


def test_url_change_rejects_taken_or_bad_slugs(admin):
    a = save_post(admin, title="Taken one")
    b = save_post(admin, title="Wants the taken URL")
    r = admin.post(f"/admin/save?slug={b}", headers={"hx-request": "true"},
                   data={"title": "x", "body": "x", "new_slug": a})
    assert "already used" in r.text
    r = admin.post(f"/admin/save?slug={b}", headers={"hx-request": "true"},
                   data={"title": "x", "body": "x", "new_slug": "Bad Slug!"})
    assert "lowercase" in r.text


def test_error_pages(client, app):
    from starlette.testclient import TestClient
    r = client.get("/definitely/not/here")
    assert r.status_code == 404 and "Page not found" in r.text
    assert "Page not found" in client.get("/post/no-such-post").text

    # two parts, so the /{slug} page route (added last) doesn't catch it first
    @app.route("/__boom/now")
    def boom():
        raise RuntimeError("boom")
    r = TestClient(app, raise_server_exceptions=False).get("/__boom/now")
    assert r.status_code == 500 and "Something went wrong" in r.text


def test_a_hang_up_is_not_logged_as_an_error(app, caplog):
    import logging
    from starlette.requests import ClientDisconnect
    from starlette.testclient import TestClient

    @app.route("/__gone/now", methods=["POST"])
    def gone():
        raise ClientDisconnect()
    with caplog.at_level(logging.INFO, logger="soloblog"):
        r = TestClient(app, raise_server_exceptions=False).post("/__gone/now?token=secret")
    assert r.status_code == 400
    assert not [x for x in caplog.records if x.levelno >= logging.WARNING]
    noted = [x.getMessage() for x in caplog.records if "hung up" in x.getMessage()]
    assert noted == ["POST /__gone/now ended early: the sender hung up"]


def test_revisions_keep_earlier_versions(admin):
    from soloblog import posts
    slug = save_post(admin, title="Versioned", body="First draft.")
    save_post(admin, slug=slug, title="Versioned", body="First draft.", summary="only a setting changed")
    assert posts.list_revisions(slug) == []  # same words - nothing to keep
    admin.post(f"/admin/save?slug={slug}", headers={"hx-request": "true"},
               data={"title": "Versioned", "body": "Second draft.", "published": "1"})
    revs = posts.list_revisions(slug)
    assert len(revs) == 1
    r = admin.get(f"/admin/revisions/{revs[0]['id']}")
    assert r.json() == {"title": "Versioned", "body": "First draft."}
    assert "History" in admin.get(f"/admin/edit/{slug}").text


def test_breadcrumbs_and_series_page(admin, client):
    import json
    import re
    from soloblog import settings
    a = save_post(admin, title="Trail part one", series_name="Trail Guide", series_order="1", tags="hiking")
    b = save_post(admin, title="Trail part two", series_name="Trail Guide", series_order="2", tags="hiking")
    html = client.get(f"/post/{b}").text
    assert 'class="breadcrumbs' in html and 'href="/series/trail-guide"' in html
    blocks = [json.loads(b) for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]
    ld = next(b for b in blocks if b["@type"] == "BreadcrumbList")
    assert [i["name"] for i in ld["itemListElement"]] == ["Home", "Trail Guide", "Trail part two"]
    assert "Part 2 of 2 in" in html

    page = client.get("/series/trail-guide")
    assert page.status_code == 200
    assert page.text.index("Trail part one") < page.text.index("Trail part two")
    assert client.get("/series/no-such-series").status_code == 404

    settings.set_many({"breadcrumbs": "tag"})
    try:
        assert 'href="/tag/hiking"' in client.get(f"/post/{a}").text
        settings.set_many({"breadcrumbs": "off"})
        assert 'class="breadcrumbs' not in client.get(f"/post/{a}").text
    finally:
        settings.set_many({"breadcrumbs": "auto"})


def test_sub_page_breadcrumb_shows_parent(admin, client):
    parent = save_post(admin, title="Crumb parent", pin_location="header")
    child = save_post(admin, title="Crumb child", pin_location="header")
    admin.post("/admin/pin/parent", data={"slug": child, "parent_slug": parent})
    html = client.get(f"/{child}").text
    assert f'href="/{parent}"' in html.split('class="breadcrumbs')[1].split("</nav>")[0]


def test_admin_posts_search(admin):
    save_post(admin, title="Sourdough diaries", body="Starter, flour and patience.")
    save_post(admin, title="Something else", body="Nothing about bread.")
    html = admin.get("/admin/posts?q=patience").text
    assert "Sourdough diaries" in html and "Something else" not in html
    assert "Sourdough diaries" in admin.get("/admin/posts?q=sourdough").text
    assert "Nothing matches" in admin.get('/admin/posts?q=zzz"*').text  # fts syntax is just text
    assert 'name="q"' in html and 'value="patience"' in html
    # a word half typed finds what the whole word does
    assert "Sourdough diaries" in admin.get("/admin/posts?q=patien").text
    for odd in ("-", "AND", "a* OR", '"', "NEAR(", "^x"):
        assert admin.get("/admin/posts", params={"q": odd}).status_code == 200


def test_admin_posts_search_puts_title_matches_first(admin):
    hours = save_post(admin, title="Opening hours", body="Get in touch on the Contact page.")
    contact = save_post(admin, title="Contact", body="Write to me.")
    save_post(admin, title="Later news", body="Nothing here.")
    html = admin.get("/admin/posts?q=Contac").text
    assert html.index(f"/admin/edit/{contact}") < html.index(f"/admin/edit/{hours}") and "Later news" not in html
    assert 'id="live-search"' in html


def test_password_protected_post(admin, client):
    from soloblog import feeds
    from soloblog import posts
    slug = save_post(admin, title="Friends only", summary="A small update", body="The secret recipe is love.",
                     post_password="hunter2")
    page = client.get(f"/post/{slug}")
    assert "Friends only" in page.text and "secret recipe" not in page.text
    assert 'action="/post/' + slug + '/unlock"' in page.text and 'content="noindex"' in page.text
    # the admin never needs it
    assert "secret recipe" in admin.get(f"/post/{slug}").text
    # nowhere else gives it away
    assert "secret recipe" not in client.get("/rss").text and "protected with a password" in client.get("/rss").text
    assert not [p for p in posts.search("recipe") if p["slug"] == slug]
    # a wrong password, then the right one - remembered for the session
    r = client.post(f"/post/{slug}/unlock", data={"password": "nope"})
    assert r.headers["location"].endswith("?wrong=1")
    assert "not the password" in client.get(r.headers["location"]).text
    client.post(f"/post/{slug}/unlock", data={"password": "hunter2"})
    assert "secret recipe" in client.get(f"/post/{slug}").text
    # it lives in the post's file too
    assert "password: hunter2" in Path(posts._path(slug)).read_text(encoding="utf-8")
    assert feeds


def test_list_shows_an_excerpt_without_a_summary(admin, client):
    save_post(admin, title="No summary here", body="The opening line says what this is about.")
    assert "The opening line says what this is about." in client.get("/").text
    save_post(admin, title="Locked teaser", body="Hidden words inside.", post_password="pw")
    assert "Hidden words inside." not in client.get("/").text


def test_per_post_search_settings_and_share_image(admin, client):
    from soloblog import settings
    slug = save_post(admin, title="Hidden from Google", post_noindex="1",
                     canonical_url="https://medium.com/@me/original")
    html = client.get(f"/post/{slug}").text
    assert '<meta name="robots" content="noindex">' in html
    assert 'rel="canonical" href="https://medium.com/@me/original"' in html
    assert f"/post/{slug}" not in client.get("/sitemap.xml").text
    from soloblog import posts
    text = Path(posts._path(slug)).read_text(encoding="utf-8")
    assert "noindex: true" in text and "canonical: https://medium.com/@me/original" in text
    # a post with no image of its own shares a card with its title
    # (cards.py) - even when the site has a share image, which the other
    # pages use instead of the site's card
    plain = save_post(admin, title="No cover here")
    assert re.search(rf'property="og:image" content="[^"]*/card/{plain}\.png\?v=', client.get(f"/post/{plain}").text)
    settings.set_many({"share_image_url": "/uploads/share.webp"})
    try:
        assert f"/card/{plain}.png" in client.get(f"/post/{plain}").text
        assert re.search(r'property="og:image" content="[^"]*/uploads/share\.webp"', client.get("/tags").text)
    finally:
        settings.set_many({"share_image_url": ""})
    assert re.search(r'property="og:image" content="[^"]*/card\.png\?v=', client.get("/tags").text)


def test_bulk_actions(admin, client):
    from soloblog import posts
    a = save_post(admin, title="Bulk one", published="")
    b = save_post(admin, title="Bulk two", published="")
    html = admin.get("/admin/posts?status=draft").text
    assert 'id="bulk-form"' in html and html.count('form="bulk-form"') >= 2
    r = admin.post("/admin/posts/bulk", data={"action": "publish", "slugs": [a, b], "return_to": "/admin/posts"})
    assert r.status_code == 303 and "Published" in r.headers["location"]
    assert posts.get_post(a)["published"] and posts.get_post(b)["published"]
    admin.post("/admin/posts/bulk", data={"action": "tag", "tag": "batch", "slugs": [a, b]})
    assert "batch" in posts.get_post(a)["tags"] and "batch" in Path(posts._path(b)).read_text(encoding="utf-8")
    admin.post("/admin/posts/bulk", data={"action": "draft", "slugs": [a]})
    assert not posts.get_post(a)["published"]
    admin.post("/admin/posts/bulk", data={"action": "trash", "slugs": [a, b]})
    assert posts.get_post(a) is None and posts.get_post(b) is None
    r = admin.post("/admin/posts/bulk", data={"action": "tag", "slugs": []})
    assert "Choose" in r.headers["location"]


def test_words_written_today_and_word_goals(admin):
    import json
    from soloblog import posts, settings
    from soloblog.db import get_db
    from soloblog.routes import editor
    assert posts.count_words("## Rise **and** shine - it's 7 o'clock, well-kneaded.") == 7
    # made today: today began at nothing
    slug = save_post(admin, title="Morning pages", body="One two three.")
    assert posts.words_at_day_start(slug) == 0
    # made yesterday and saved twice today: the day began with the text
    # the first of today's saves replaced
    get_db().execute("UPDATE posts SET created_at='2000-01-01T00:00:00' WHERE slug=?", (slug,))
    get_db().commit()
    assert posts.words_at_day_start(slug) == 3
    save_post(admin, title="Morning pages", body="One two three four five.", slug=slug)
    save_post(admin, title="Morning pages", body="One two three four five six seven.", slug=slug)
    assert posts.words_at_day_start(slug) == 3
    page = admin.get(f"/admin/edit/{slug}").text
    assert 'data-day-words="3"' in page and 'name="word_goal"' in page
    # a goal is saved with the post, by its id - and cleared by emptying it
    save_post(admin, title="Morning pages", body="One.", slug=slug, word_goal="750")
    post_id = posts.get_post(slug)["id"]
    assert editor.word_goal(post_id) == 750 and 'value="750"' in admin.get(f"/admin/edit/{slug}").text
    save_post(admin, title="Morning pages", body="One.", slug=slug, word_goal="lots")
    assert editor.word_goal(post_id) == 750  # nonsense leaves it be
    save_post(admin, title="Morning pages", body="One.", slug=slug, word_goal="")
    assert str(post_id) not in json.loads(settings.get("editor_goals"))
    # Settings > Editor > Writing progress off: no count, no goal field
    before = settings.get("editor_progress")
    try:
        admin.post("/admin/settings/editor", headers={"hx-request": "true"},
                   data={"declared_fields": "editor_progress"})
        page = admin.get(f"/admin/edit/{slug}").text
        assert "data-day-words" not in page and 'name="word_goal"' not in page
    finally:
        settings.set_many({"editor_progress": before})


def test_history_keeps_up_with_the_editor(admin):
    """History lists the post as it is now, then each earlier version at
    the time it was written; the list comes back with every save (no
    reload); and Compare shows what each version changed, again and
    again."""
    from soloblog import posts
    slug = save_post(admin, title="History", body="One.")
    editor = admin.get(f"/admin/edit/{slug}").text
    # the Compare dialog is there before there's anything to compare
    assert 'id="revision-diff-dialog"' in editor and 'id="history-list"' in editor
    r = admin.post(f"/admin/save?slug={slug}", headers={"hx-request": "true"},
                   data={"title": "History", "body": "Two words.", "published": "1"})
    # the save's answer brings the list along, with the version it just kept
    assert re.search(r'<div[^>]*hx-swap-oob="true"[^>]*id="history-list"', r.text) and "/diff" in r.text
    admin.post(f"/admin/save?slug={slug}", headers={"hx-request": "true"},
               data={"title": "History", "body": "Now three words.", "published": "1"})
    revs = posts.list_revisions(slug)
    assert len(revs) == 2
    # "Two words." was written when "One." was replaced; "One." when the post was made
    assert revs[0]["written_at"] == revs[1]["saved_at"]
    assert revs[1]["written_at"] == posts.get_post(slug)["created_at"]
    assert (revs[0]["words"], revs[0]["added"], revs[1]["added"]) == (2, 1, None)
    now = posts.current_version(slug)
    assert now["words"] == 3 and now["added"] == 1 and now["written_at"] == revs[0]["saved_at"]
    editor = admin.get(f"/admin/edit/{slug}").text
    history = editor[editor.index('id="history-list"'):editor.index('id="revision-diff-dialog"')]
    # the post now on top, then both versions, each with its words
    assert "Now · " in history and history.count('aria-label="Compare"') == 3 and history.count('aria-label="Restore"') == 2
    # the list scrolls in its box, which cut off a tooltip above the top row: they show to the left
    assert history.count("tooltip tooltip-left") == 5
    assert "3 words · +1" in history and "2 words · +1" in history
    # Compare swaps only its own box - inside the post form it would
    # otherwise inherit the form's outerHTML and remove #revision-diff
    assert re.search(r'hx-get="/admin/revisions/\d+/diff"[^>]*hx-swap="innerHTML"', history)
    # each Compare is that version's own change, from the one before it
    newer = admin.get(f"/admin/revisions/{revs[0]['id']}/diff").text
    assert "One." in newer and "Two words." in newer and "Now three words." not in newer
    oldest = admin.get(f"/admin/revisions/{revs[1]['id']}/diff").text
    assert "the oldest kept" in oldest and "One." in oldest and "Two words." not in oldest
    latest = admin.get(f"/admin/history/{slug}/now").text
    assert "Two words." in latest and "Now three words." in latest and "One." not in latest
    # a date with no time (an imported post's) isn't given a made-up one
    from soloblog.routes.editor import _when
    assert ":" not in _when("2026-09-27")


def test_history_needs_the_login(client):
    assert client.get("/admin/history/anything/now").status_code in (302, 303)


def test_a_default_word_goal_each_post_can_change_or_turn_off(admin):
    # a goal on every post from Settings > Editor; a post can have its own,
    # or none (0), and empty follows the default
    import json
    from soloblog.routes import editor
    from soloblog.db import get_db
    try:
        admin.post("/admin/settings/editor", data={"editor_progress": "1", "editor_goal_default": "500"},
                   headers={"HX-Request": "true"})
        assert settings.get("editor_goal_default") == "500" and editor.default_goal() == 500
        page = admin.get("/admin/new").text
        assert 'data-default="500"' in page and "Empty: your default, 500 words. 0: no goal." in page
        slug = save_post(admin, title="Goal pages", body="One.")
        post_id = get_db().execute("SELECT id FROM posts WHERE slug=?", (slug,)).fetchone()[0]
        assert editor.word_goal(post_id) is None  # follows the default
        save_post(admin, title="Goal pages", body="One.", slug=slug, word_goal="0")
        assert editor.word_goal(post_id) == 0 and 'value="0"' in admin.get(f"/admin/edit/{slug}").text
        save_post(admin, title="Goal pages", body="One.", slug=slug, word_goal="900")
        assert editor.word_goal(post_id) == 900
        save_post(admin, title="Goal pages", body="One.", slug=slug, word_goal="")
        assert str(post_id) not in json.loads(settings.get("editor_goals"))
        # nonsense, or 0, as the default is none
        admin.post("/admin/settings/editor", data={"editor_progress": "1", "editor_goal_default": "lots"},
                   headers={"HX-Request": "true"})
        assert settings.get("editor_goal_default") == "" and "0: no goal" not in admin.get("/admin/new").text
    finally:
        settings.set_many({"editor_goal_default": ""})


def test_nothing_writes_a_layout_line(admin):
    """Every way of writing a post - the editor's form, posts.write, a template, a copy - leaves layout
    out of the file, and asking for one changes nothing."""
    import re
    from soloblog import demo, post_templates, posts
    assert "layout" not in posts.WRITABLE
    slug = save_post(admin, title="Written from the form", layout="recipe")
    other = posts.write(None, "A", title="Written by write", body="Words.", layout="landing")
    copy = posts.duplicate_post(slug)
    for s in (slug, other, copy):
        assert not re.search(r"(?m)^layout:", Path(posts._path(s)).read_text(encoding="utf-8")), s
    # no template starts a page with a layout line, and none of the demo's pages is made with one
    for name, body in post_templates.BUILT_IN.values():
        assert not re.search(r"(?mi)^layout:", body), name
    photos = {k: f"/uploads/{k}.webp" for k in demo.PHOTOS}
    for slug_, _title, _tags, _summary, body, f in demo.posts_and_pages(photos):
        assert "layout" not in f and not re.search(r"(?mi)^layout:", body), slug_
    for s in (slug, other, copy):
        posts.delete_post(s)


def test_admin_buttons_sit_above_the_title_on_a_phone(admin, client):
    slug = save_post(admin, title="A title that is long enough to wrap", body="Words.")
    mine = admin.get(f"/post/{slug}").text
    row = mine[mine.rindex('class="flex flex-col-reverse', 0, mine.index(f"/admin/edit/{slug}")):]
    # title first in the page, reversed to sit second on a phone; a row from sm up
    assert row.index("A title that is long") < row.index(f"/admin/edit/{slug}")
    assert "sm:flex-row" in row[:120]
    assert f"/admin/edit/{slug}" not in client.get(f"/post/{slug}").text


def test_new_post_button_on_posts_has_the_plus_icon_of_the_menu(admin):
    import re
    html = admin.get("/admin/posts").text
    button = re.search(r'<a [^>]*href="/admin/new"[^>]*lg:hidden[^>]*>(.*?)</a>', html, re.S)
    assert button and "<svg" in button.group(1) and "M12 4.5v15m7.5-7.5h-15" in button.group(1)
    assert ">New post</span>" in button.group(1)
