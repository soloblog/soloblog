"""The 0.3 follow-ups: covers, bulk renaming, redirects, templates,
History diffs and the calendar."""
from pathlib import Path
import glob
import os
import re

from soloblog import config
from soloblog import images
from soloblog import posts
from soloblog import settings
from conftest import save_post
from test_bulk import _upload


def test_list_style_has_no_empty_cover_tile(admin, client):
    save_post(admin, title="No cover here")
    before = settings.get("roll_style")
    settings.set_many({"roll_style": "list"})
    try:
        home = client.get("/").text
        item = home[home.index("No cover here") - 1500:home.index("No cover here")]
        assert "bg-base-300 rounded-box" not in item
    finally:
        settings.set_many({"roll_style": before})


def test_covers_in_post_lists(admin, client):
    keys = ("roll_style", "roll_list_cover", "roll_placeholder")
    before = {k: settings.get(k) for k in keys}
    hidden = save_post(admin, title="Cover kept off lists", cover_image="/uploads/qq-hidden-img.webp",
                       hide_list_cover="1")
    save_post(admin, title="Cover in lists", cover_image="/uploads/qq-shown-img.webp")
    save_post(admin, title="Never had a cover")
    try:
        # the post keeps its cover; the lists don't show it
        assert posts.get_post(hidden)["hide_list_cover"] == 1
        assert "list_cover: false" in Path(posts._path(hidden)).read_text(encoding="utf-8")
        assert "qq-hidden-img" in client.get(f"/post/{hidden}").text
        for style in ("list", "cards", "magazine", "timeline"):
            settings.set_many({"roll_style": style})
            home = client.get("/").text
            assert "qq-shown-img" in home and "qq-hidden-img" not in home, style
        # the file is the source of truth: a rebuilt index still knows
        posts.get_db().execute("UPDATE posts SET hide_list_cover=0 WHERE slug=?", (hidden,))
        posts._index_redirects(hidden, posts._parse_file(posts._path(hidden))[0])
        assert posts.get_post(hidden)["hide_list_cover"] == 1

        # no placeholder tile where a card has no cover
        settings.set_many({"roll_style": "cards", "roll_placeholder": "1"})
        assert "from-primary/20 to-secondary/20" in client.get("/").text
        admin.post("/admin/settings/style", headers={"hx-request": "true"},
                   data={"roll_style": "cards", "declared_fields": "roll_style,roll_placeholder"})
        assert settings.get("roll_placeholder") == "0"
        assert "from-primary/20 to-secondary/20" not in client.get("/").text.split('id="main"')[1]

        # List's picture on either side of the text
        admin.post("/admin/settings/style", headers={"hx-request": "true"},
                   data={"roll_style": "list", "roll_list_cover": "left",
                         "declared_fields": "roll_style,roll_list_cover"})
        home = client.get("/").text
        assert home.index("qq-shown-img") < home.index(">Cover in lists</a>")
        settings.set_many({"roll_list_cover": "right"})
        home = client.get("/").text
        assert home.index("qq-shown-img") > home.index(">Cover in lists</a>")
        admin.post("/admin/settings/style", headers={"hx-request": "true"},
                   data={"roll_list_cover": "top", "declared_fields": "roll_list_cover"})
        assert settings.get("roll_list_cover") == "right"
    finally:
        settings.set_many(before)


def test_minimal_titles_share_one_edge(admin, client):
    save_post(admin, title="A short date")
    before = {k: settings.get(k) for k in ("roll_style", "roll_shows")}
    try:
        # one date column for the whole list, so "Sep 5" and "Sep 15" don't push titles about
        settings.set_many({"roll_style": "minimal"})
        home = client.get("/").text
        assert 'class="list grid grid-cols-[auto_1fr]' in home
        assert "list-row items-baseline py-3 col-span-2 grid-cols-subgrid" in home
        # no dates, no columns - the title takes the row
        settings.set_many({"roll_shows": "summary"})
        assert "grid-cols-subgrid" not in client.get("/").text
    finally:
        settings.set_many(before)


def test_minimal_groups_by_year_or_month(admin, client):
    from soloblog.render import short_date_format, local_datetime
    slug = save_post(admin, title="Grouped minimal post")
    day = local_datetime(posts.get_post(slug)["created_at"])
    month = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
             "October", "November", "December"][day.month - 1]
    before = {k: settings.get(k) for k in ("roll_style", "minimal_group")}
    try:
        settings.set_many({"roll_style": "minimal"})
        admin.post("/admin/settings/style", headers={"hx-request": "true"},
                   data={"minimal_group": "year", "declared_fields": "minimal_group"})
        home = client.get("/").text
        assert f'<h2 class="text-lg font-semibold">{day.year}</h2>' in home
        assert re.search(rf"whitespace-nowrap\">\s*{month[:3]} {day.day}</span>", home) and re.search(r"<h3>\s*<a", home)
        settings.set_many({"minimal_group": "month"})
        home = client.get("/").text
        assert f'<h2 class="text-lg font-semibold">{month} {day.year}</h2>' in home
        assert re.search(rf"whitespace-nowrap\">\s*{day.day}</span>", home)
        # search is by relevance - no headings there
        assert "font-semibold\">" + month not in client.get("/search?q=Grouped").text
        # nonsense is no grouping
        admin.post("/admin/settings/style", headers={"hx-request": "true"},
                   data={"minimal_group": "week", "declared_fields": "minimal_group"})
        assert settings.get("minimal_group") == "none"
    finally:
        settings.set_many(before)
    # the date without what the heading already says, in any language
    assert short_date_format("{month} {day}, {year}") == "{month} {day}"
    assert short_date_format("{day} de {month} de {year}", month=False) == "{day}"
    assert short_date_format("{year}年{month}{day}日") == "{month}{day}日"
    assert short_date_format("{year}년 {month} {day}일", month=False) == "{day}일"
    assert short_date_format("{day} {month} {year} г.") == "{day} {month}"


def test_empty_field_is_named(admin, client):
    # "Please fill out this field" beside the buttons didn't say which one
    slug = save_post(admin, title="Say which field")
    page = client.get(f"/post/{slug}").text
    assert 'aria-label="Name"' in page and 'aria-label="Email"' in page and 'aria-label="Comment"' in page
    before = settings.get("site_language")
    settings.set_many({"site_language": "de"})
    try:
        # the script's words, in the site's language
        assert "{field} ist ein Pflichtfeld" in client.get(f"/post/{slug}").text
    finally:
        settings.set_many({"site_language": before})


def test_pages_show_just_their_content(admin, client):
    from soloblog import pages
    share = 'role="group" aria-label="Share"'

    def show(slug, **form):
        # the editor's Page > Show, as the form sends it
        return save_post(admin, slug=slug, **form)

    post = save_post(admin, title="An ordinary post")
    page = save_post(admin, title="A plain page", pin_location="header")
    html = client.get(f"/post/{post}").text
    assert "min read" in html and share in html
    # a page: its title and text, no byline, share buttons or author box
    html = client.get(f"/{page}").text
    assert "A plain page" in html and "min read" not in html and share not in html
    # a page can have some back
    show(page, title="A plain page", pin_location="header", extras=["share"], extras_before="",
         extras_before_page="1")
    assert posts.get_post(page)["extras"] == "share"
    assert "extras: share" in Path(posts._path(page)).read_text(encoding="utf-8")
    html = client.get(f"/{page}").text
    assert share in html and "min read" not in html
    # and a post can drop them all
    show(post, title="An ordinary post", extras=[], extras_before="", extras_before_page="")
    assert posts.get_post(post)["extras"] == "none" and "min read" not in client.get(f"/post/{post}").text
    # untouched, a post moved to the menu follows the page default
    moved = save_post(admin, title="Moved to the menu")
    show(moved, title="Moved to the menu", pin_location="header", extras=sorted(pages.default_extras(False)),
         extras_before="", extras_before_page="")
    assert posts.get_post(moved)["extras"] == "" and "min read" not in client.get(f"/{moved}").text
    # a save without the Show switches (a script) keeps the choice
    save_post(admin, slug=page, title="A plain page", pin_location="header")
    assert posts.get_post(page)["extras"] == "share"
    # the editor ticks what shows
    form = admin.get(f"/admin/edit/{page}").text
    boxes = {re.search(r'value="(\w+)"', m).group(1): "checked" in m
             for m in re.findall(r'<input[^>]*name="extras"[^>]*>', form)}
    assert boxes == {key: key == "share" for key in pages.EXTRAS}, boxes
    # nonsense in a file is dropped
    assert pages.clean_extras("share,evil,tags") == "tags,share" and pages.clean_extras("none") == "none"


def test_search_finds_word_starts_and_titles_first(admin, client):
    from soloblog import posts
    plans = save_post(admin, title="Plans", body="What each costs.", summary="Four plans, from free to premium",
                      pin_location="header")
    save_post(admin, title="A long ramble", body="Our plans changed, and plans again, and more plans.")
    # a word's start finds it, as it's typed
    found = [p["slug"] for p in posts.search("plan")]
    assert plans in found
    # the title match comes first, ahead of text that only mentions it
    assert posts.search("plans")[0]["slug"] == plans
    # results say what each is about; a page has no date
    html = client.get("/search/results?q=plans").text
    first = html.split('<a ')[1]
    assert "Plans" in first and "Four plans, from free to premium" in first
    assert "Nothing found for" in client.get("/search/results?q=zzqqxx").text


def test_bulk_rename_from_alt_text_or_post(admin):
    _upload("a1b2c3d4e5.webp")
    _upload("f6g7h8i9j0.webp")
    _upload("k1l2m3n4o5.webp")
    images.set_meta("a1b2c3d4e5.webp", "Sunrise over the harbour", "")
    slug = save_post(admin, title="Balcony tomatoes", body="![](/uploads/f6g7h8i9j0.webp)")
    r = admin.post("/admin/media/bulk", data={"action": "rename", "return_to": "/admin/media",
                                              "filenames": ["a1b2c3d4e5.webp", "f6g7h8i9j0.webp", "k1l2m3n4o5.webp"]},
                   follow_redirects=False)
    from urllib.parse import unquote_plus
    said = unquote_plus(r.headers["location"])
    assert "Renamed 2 images" in said and "1 kept its name" in said
    assert os.path.exists(os.path.join(config.UPLOADS_DIR, "sunrise-over-the-harbour.webp"))
    assert os.path.exists(os.path.join(config.UPLOADS_DIR, "balcony-tomatoes.webp"))
    assert "/uploads/balcony-tomatoes.webp" in posts.load_post_body(slug)
    assert images.renamed_to("a1b2c3d4e5.webp") == "sunrise-over-the-harbour.webp"


def test_custom_redirects(admin, client):
    admin.post("/admin/settings/address", headers={"hx-request": "true"}, data={
        "redirects": "/old-page /archive\n/shop https://shop.example.com\n/2019/* /tags\nnot a redirect\n/x javascript:y",
        "declared_fields": "redirects"})
    try:
        assert settings.get("redirects") == "/old-page /archive\n/shop https://shop.example.com\n/2019/* /tags"
        r = client.get("/old-page", follow_redirects=False)
        assert r.status_code == 301 and r.headers["location"] == "/archive"
        assert client.get("/shop", follow_redirects=False).headers["location"] == "https://shop.example.com"
        assert client.get("/2019/05/something", follow_redirects=False).headers["location"] == "/tags"
        assert client.get("/nothing-here", follow_redirects=False).status_code == 404
        # a real page always wins
        admin.post("/admin/settings/address", headers={"hx-request": "true"},
                   data={"redirects": "/archive /tags", "declared_fields": "redirects"})
        assert client.get("/archive", follow_redirects=False).status_code == 200
    finally:
        settings.set_many({"redirects": ""})


def test_post_templates(admin):
    from soloblog import post_templates
    page = admin.get("/admin/new?template=recipe").text
    assert "## Ingredients" in page and "Section: Recipe facts" in page
    r = admin.post("/admin/templates/save", data={"template_name": "Weekly notes", "title": "Week 1",
                                                  "body": "## Wins\n\n## Next", "tags": "weekly"})
    assert "Saved “Weekly notes”" in r.text
    mine = post_templates.saved()[0]
    assert mine["name"] == "Weekly notes" and mine["tags"] == "weekly"
    page = admin.get(f"/admin/new?template=mine-{mine['id']}").text
    assert "## Wins" in page and 'value="weekly"' in page
    # the same name replaces it
    admin.post("/admin/templates/save", data={"template_name": "weekly notes", "body": "## Changed"})
    assert len([t for t in post_templates.saved() if t["name"].lower() == "weekly notes"]) == 1
    assert "Weekly notes" not in admin.post(f"/admin/templates/delete/{post_templates.saved()[0]['id']}").text
    assert "Give it a name" in admin.post("/admin/templates/save", data={"body": ""}).text


def test_history_diff(admin):
    slug = save_post(admin, title="Diff me", body="one\ntwo\nthree")
    save_post(admin, slug=slug, title="Diff me again", body="one\n2\nthree")
    # the change is the post now's own, from the version before it
    html = admin.get(f"/admin/history/{slug}/now").text
    assert "bg-error/15" in html and ">two<" in html and ">2<" in html
    assert "Title: Diff me again" in html
    assert 'id="revision-diff-dialog"' in admin.get(f"/admin/edit/{slug}").text


def test_posts_calendar(admin):
    from datetime import datetime, timedelta
    save_post(admin, title="On the calendar")
    soon = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT10:30")
    save_post(admin, title="Coming up", scheduled_at=soon)
    month = soon[:7]
    html = admin.get(f"/admin/posts?status=calendar&month={month}").text
    assert "Coming up" in html and "10:30" in html and "bg-warning/15" in html
    assert "On the calendar" in admin.get("/admin/posts?status=calendar").text
    empty = admin.get("/admin/posts?status=calendar&month=1999-01").text
    assert "Nothing this month" in empty
    # on a narrow phone the count wraps under the month instead of being squeezed
    assert 'class="flex flex-wrap items-center gap-x-3 gap-y-1 mb-3"' in empty
    assert admin.get("/admin/posts?status=calendar&month=bogus").status_code == 200


def test_project_button_skips_the_photo_credit():
    from soloblog import pages
    html = ('<h2 id="p">Project</h2><figure><img src="/uploads/x.webp" alt="">'
            '<figcaption>Photo by <a href="https://unsplash.com/@someone">Someone</a></figcaption></figure>'
            '<p>What it is. <a href="https://example.com/it">See it</a></p>')
    _, _, items = pages.portfolio_items({"slug": "x"}, html)
    # the piece leads to its own page, not the photographer's - whose credit stays with the picture
    assert items[0]["href"] == "https://example.com/it" and "Someone" in items[0]["credit"]


def test_favicon_address(client):
    before = settings.get("favicon_url")
    try:
        settings.set_many({"favicon_url": ""})
        r = client.get("/favicon.ico", follow_redirects=False)
        assert r.status_code == 302 and r.headers["location"] == "/icon-32.png"
        settings.set_many({"favicon_url": "/uploads/icon.png"})
        r = client.get("/favicon.ico", follow_redirects=False)
        assert r.status_code == 302 and r.headers["location"] == "/uploads/icon.png"
    finally:
        settings.set_many({"favicon_url": before})


def test_what_each_post_shows(admin, client):
    save_post(admin, title="Shows test post", tags="showtag", summary="A summary to show")
    before = {k: settings.get(k) for k in ("roll_style", "roll_shows")}
    try:
        for style in ("list", "cards", "magazine", "timeline"):
            settings.set_many({"roll_style": style, "roll_shows": "cover,date,reading,summary,tags"})
            assert "A summary to show" in client.get("/").text, style
            admin.post("/admin/settings/style", headers={"hx-request": "true"},
                       data={"roll_shows": ["date"], "declared_fields": "roll_shows"})
            home = client.get("/").text
            assert "A summary to show" not in home and 'href="/tag/showtag"' not in home.split("<main")[1], style
            assert "min read" not in home.split("<main")[1], style
        assert settings.get("roll_shows") == "date"
        # cards without a cover get a soft tile, the timeline none at all
        settings.set_many({"roll_style": "cards", "roll_shows": "cover,date"})
        assert "from-primary/20 to-secondary/20" in client.get("/").text
        settings.set_many({"roll_style": "timeline"})
        assert "bg-base-300 rounded-box" not in client.get("/").text
    finally:
        settings.set_many(before)


def test_templates_keep_summary_cover_and_contents(admin):
    from soloblog import post_templates
    admin.post("/admin/templates/save", data={"template_name": "Full template", "body": "## One",
                                              "summary": "Its summary", "cover_image": "/uploads/c.webp",
                                              "toc_style": "right"})
    t = next(t for t in post_templates.saved() if t["name"] == "Full template")
    page = admin.get(f"/admin/new?template=mine-{t['id']}").text
    assert "Its summary" in page and 'value="/uploads/c.webp"' in page and 'value="right" selected' in page
    assert "## What you'll need" in admin.get("/admin/new?template=howto").text
    assert "## Next week" in admin.get("/admin/new?template=journal").text
    post_templates.delete(t["id"])


def test_interview_host_bubble_is_plain(admin, client):
    slug = save_post(admin, title="Chat test", body="## Chat\n\nSection: Interview\n\n**Sam:** Hi\n\n**Alex:** Hello")
    page = client.get(posts.url_for(posts.get_post(slug)), follow_redirects=True).text
    assert "chat-bubble-neutral" not in page and "chat-bubble-primary" in page


def test_timeline_alignments(admin, client):
    from soloblog.ui import timeline_cls
    assert "timeline-compact" in timeline_cls("left") and "--timeline-col-end:0" in timeline_cls("right")
    assert "max-md:timeline-compact" in timeline_cls("center")
    save_post(admin, title="Timeline align post")
    slug = save_post(admin, title="Milestones align",
                     body="## So far\n\nSection: Milestones\n\n### 2020 · One\n\nA\n\n### 2021 · Two\n\nB")
    before = {k: settings.get(k) for k in ("roll_style", "timeline_align", "milestones_align")}
    try:
        for align, marker in (("left", "timeline-compact"), ("right", "--timeline-col-end:0"),
                              ("center", "max-md:timeline-compact")):
            admin.post("/admin/settings/style", headers={"hx-request": "true"},
                       data={"roll_style": "timeline", "timeline_align": align, "milestones_align": align,
                             "declared_fields": "roll_style,timeline_align,milestones_align"})
            home = client.get("/").text
            assert marker in home, align
            page = client.get(posts.url_for(posts.get_post(slug)), follow_redirects=True).text
            assert marker in page and ">2021<" in page, align
            # a line in the middle left half the page empty beside each entry: there,
            # TIMELINE_JS moves each one up beside the one across the line
            assert ("data-stagger" in home) == ("data-stagger" in page) == (align == "center"), align
        # centred: the date faces its entry from across the line
        assert "max-md:hidden" in page
        from soloblog import app as built
        assert built.TIMELINE_JS in built.SHARED_SCRIPTS and "[data-stagger]" in built.TIMELINE_JS
    finally:
        settings.set_many(before)


def test_search_engine_basics(admin, client):
    home = client.get("/").text
    assert '"@type": "WebSite"' in home and "search_term_string" in home
    assert 'content="noindex, follow"' in client.get("/search?q=x").text
    for n in range(12):
        save_post(admin, title=f"Paging post {n}")
    before = settings.get("posts_per_page")
    settings.set_many({"posts_per_page": "5"})
    try:
        page2 = client.get("/?page=2").text
        assert 'rel="canonical" href="' in page2 and '/?page=2"' in page2
        assert "Page 2 of" in page2.split("</title>")[0]
    finally:
        settings.set_many({"posts_per_page": before})



def test_post_seo_title_and_share_image(admin, client):
    slug = save_post(admin, title="A long and wordy post title", body="Words.",
                     seo_title="Short search title", share_image="/uploads/share-me.webp")
    row = posts.get_post(slug)
    assert row["seo_title"] == "Short search title" and row["share_image"] == "/uploads/share-me.webp"
    page = client.get(posts.url_for(row), follow_redirects=True).text
    head = page.split("</head>")[0]
    assert "<title>Short search title" in head and 'og:title" content="Short search title' in head
    assert 'og:image" content="' in head and "/uploads/share-me.webp" in head
    assert ">A long and wordy post title</h1>" in page  # the page itself keeps its title
    # kept in the file, so a rebuilt index still has them
    text = Path(os.path.join(config.POSTS_DIR, f"{slug}.md")).read_text(encoding="utf-8")
    assert "seo_title: Short search title" in text and "share_image: /uploads/share-me.webp" in text


def test_update_now_calls_the_hook(admin, monkeypatch):
    import threading
    from soloblog import updates
    calls, done = [], threading.Event()

    class Resp:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake_open(req, timeout=0):
        calls.append((req.full_url, req.get_method(), req.get_header("Authorization")))
        done.set()
        return Resp()
    monkeypatch.setattr(updates.urllib.request, "urlopen", fake_open)
    assert "Set up updates first" in admin.post("/admin/update").text
    admin.post("/admin/settings/integrations", headers={"hx-request": "true"},
               data={"update_hook_url": "http://watchtower:8080/v1/update", "update_hook_token": "tok",
                     "declared_fields": "update_hook_url,update_hook_token"})
    try:
        assert "Updating" in admin.post("/admin/update").text
        assert done.wait(5)
        assert calls == [("http://watchtower:8080/v1/update", "POST", "Bearer tok")]
        # not a web address: not kept
        admin.post("/admin/settings/integrations", headers={"hx-request": "true"},
                   data={"update_hook_url": "file:///etc/passwd", "declared_fields": "update_hook_url"})
        assert settings.get("update_hook_url") == ""
    finally:
        settings.set_many({"update_hook_url": "", "update_hook_token": ""})


def test_admin_sidebar(admin, client):
    settings.set_many({"contact_enabled": "1"})
    html = admin.get("/admin/media").text
    # two copies: in the rail on a wide screen and in the drawer
    assert html.count("data-admin-nav") == 2 and 'class="drawer ' in html and "data-admin-rail" in html
    assert 'for="admin-drawer"' in html and html.count('id="admin-logout-form"') == 1
    side = html[html.index("data-admin-nav"):]
    import re
    def active(h):
        return re.findall(r'<a [^>]*aria-current="page"[^>]*class="menu-active"[^>]*>', h[h.index("data-admin-nav"):])
    assert len(active(html)) == 2 and 'href="/admin/media"' in active(html)[0]
    assert "Contact messages" in side and "<span>Help</span>" in side
    # one name for each place, in the sidebar, the gear menu and on the page itself
    for name, path in (("Posts and pages", "/admin/posts"), ("Media", "/admin/media"),
                       ("Contact messages", "/admin/messages"), ("Stats", "/admin/stats")):
        page = admin.get(path).text
        assert page.count(f">{name}<") >= 3 or (f"<span>{name}</span>" in page and f">{name}</a>" in page), name
    settings.set_many({"contact_enabled": "0"})
    help_page = admin.get("/admin/help?tab=deployment").text
    assert 'href="/admin/help?tab=deployment"' in active(help_page)[0]
    # Settings' sections are in the menu too, and the tabs only show where it isn't beside the page
    appearance = admin.get("/admin/settings?tab=style").text
    assert 'href="/admin/settings?tab=style"' in active(appearance)[0]
    assert "[html[data-admin-beside]_&amp;]:hidden" in appearance and "Settings: Style" in appearance
    # under their headings, as Notion's are
    assert '<li class="menu-title text-xs font-normal pt-3 pb-1">Design</li>' in appearance
    assert '<li class="menu-title text-xs font-normal pt-3 pb-1">Readers</li>' in appearance
    # the menu's own headings aren't the same words as Settings' ones
    from soloblog import ui
    assert all(f'<li class="{ui.MENU_HEADING}">{h}</li>' in appearance for h in ("Content", "Audience", "Manage"))
    # the public site keeps its own header menu, no sidebar
    assert "data-admin-nav" not in admin.get("/").text and 'id="nav-admin-menu"' in admin.get("/").text


def test_cover_and_hero_widths(admin, client):
    before = {k: settings.get(k) for k in ("cover_width", "banner_width", "banner_enabled", "banner_heading", "header_width")}
    try:
        # the header as wide as the text, so its width isn't the cover's
        settings.set_many({"cover_width": "column", "header_width": "column"})
        slug = save_post(admin, title="A wide cover", cover_image="/uploads/wide.webp")
        column = client.get(f"/post/{slug}").text
        assert "w-screen mx-[calc(50%-50vw)]" not in column
        # the site's setting, then the post's own
        settings.set_many({"cover_width": "wide"})
        assert "max-w-[79rem]" in client.get(f"/post/{slug}").text
        save_post(admin, slug=slug, title="A wide cover", cover_image="/uploads/wide.webp", cover_width="full")
        assert posts.get_post(slug)["cover_width"] == "full"
        assert "cover_width: full" in Path(posts._path(slug)).read_text(encoding="utf-8")
        full = client.get(f"/post/{slug}").text
        assert "w-full max-h-[28rem] object-cover" in full and "max-w-[79rem]" not in full
        # nonsense is the site's own again
        save_post(admin, slug=slug, title="A wide cover", cover_image="/uploads/wide.webp", cover_width="huge")
        assert posts.get_post(slug)["cover_width"] == ""
        settings.set_many({"banner_enabled": "1", "banner_heading": "Hello there", "banner_width": "wide",
                           "body_width": "narrow"})
        assert "max-w-[73rem]" in client.get("/").text
    finally:
        settings.set_many({**before, "body_width": "standard"})


def test_plain_side_panels_and_frosted_glass(admin, client):
    before = {k: settings.get(k) for k in ("side_plain", "side_tags", "glass_effect")}
    try:
        save_post(admin, title="Tagged for the cloud", tags="fog")
        settings.set_many({"side_tags": "right", "side_plain": "1"})
        assert "data-[beside]:[&amp;_.collapse]:bg-transparent" in client.get("/").text
        # on or off - the look itself is the stylesheet's
        admin.post("/admin/settings/style", data={"glass_effect": "1", "declared_fields": "glass_effect"},
                   headers={"HX-Request": "true"})
        home = client.get("/").text
        assert "glass-fill" in home and 'data-glass="1"' in home and "--glass-blur:" not in home
    finally:
        settings.set_many(before)


def test_the_admin_has_its_own_thin_bar_and_one_menu_button(admin):
    # no site header or footer on an admin page at any width: a thin bar
    # with the menu button, the site's name and the colours - and, where
    # the rail folds into that button, the site header's gear too - no
    # search for posts: the admin's own lists do that
    html = admin.get("/admin/posts").text
    bar = html[html.rindex("<", 0, html.index("data-admin-bar")):]
    bar = bar[:bar.index("</header>")]
    assert "data-site-header" in bar and "h-12" in bar and 'data-toggles="admin-drawer"' in bar
    assert "Open the admin menu" in bar and 'data-open-dialog="search-modal"' not in bar
    # the colours line up with the rail's contents on a wide screen
    assert "lg:w-[calc(16rem-1.5rem)]" in bar
    # docked side panels are solid like the rail - never blended or glass
    from soloblog import ui
    for page in ("/admin/new", "/admin/media"):
        assert ui.DOCKED_FILL in admin.get(page).text
    assert "data-[docked]:bg-transparent!" not in admin.get("/admin/new").text
    assert html.count("data-site-header") == 1 and html.count('id="nav-admin-menu"') == 1 and "<footer" not in html
    assert html.count('id="admin-logout-form"') == 1
    # the rail sits under it, and the page starts beside it on a wide screen
    rail = html[html.rindex("<", 0, html.index("data-admin-rail")):]
    assert "top-12" in rail[:rail.index(">")] and "lg:mx-0" in html
    # the setting that chose between the two buttons is gone; a saved one is ignored
    settings.set_many({"admin_icons": "gear"})
    assert "Buttons in the header" not in admin.get("/admin/settings?tab=header").text
    assert "Open the admin menu" in admin.get("/admin/posts").text
    # the site's own pages keep the gear: the way back to the admin
    assert 'id="nav-admin-menu"' in admin.get("/").text


def test_reply_box_opens_under_the_comment(admin, client):
    from soloblog import comments
    slug = save_post(admin, title="Somewhere to reply")
    comments.add_comment(slug, "Ada", "ada@example.com", "Lovely", auto_confirm=True)
    from soloblog.db import get_db
    cid = get_db().execute("SELECT id FROM comments WHERE post_slug=?", (slug,)).fetchone()["id"]
    comments.approve(cid)
    html = admin.get("/admin/comments?tab=approved").text
    box = html[html.index(f'id="reply-{cid}"') - 300:]
    # a form under the comment, hidden until Reply opens it
    assert f'action="/post/{slug}/reply"' in box and "data-reply-box" in box and "hidden" in box[:400]
    assert f'data-args=\'["reply-{cid}", "$el"]\'' in html or f"reply-{cid}&quot;" in html


def test_trash_asks_and_tooltips_are_daisyuis(admin):
    import re
    slug = save_post(admin, title="Something to trash")
    pages = ["/admin/posts", "/admin/posts?status=pinned", "/admin/posts?status=trash", "/admin/posts?status=tags",
             "/admin/comments", "/admin/comments?tab=approved", "/admin/media", "/admin/messages",
             "/admin/settings?tab=security", f"/admin/edit/{slug}"]
    for page in pages:
        html = admin.get(page).text
        # every trash or delete button asks first
        for button in re.findall(r"<button[^>]*>(?:(?!</button>).)*?(?:Trash|Delete|Remove)(?:(?!</button>).)*?</button>",
                                 html, re.S):
            if 'name="action"' in button and 'value="trash"' not in button and 'value="delete"' not in button:
                continue
            assert "data-confirm" in button, (page, button[:200])
        # no browser tooltips on buttons or links
        assert not re.search(r"<(?:button|a)\b[^>]*\stitle=", html), page


def test_welcome_asks_the_language_and_runs_again(admin):
    before = {k: settings.get(k) for k in ("site_title", "tagline", "timezone", "site_language")}
    try:
        assert 'name="site_language"' in admin.get("/admin/welcome").text
        admin.post("/admin/welcome/site", data={"site_title": "Mira", "timezone": "UTC", "site_language": "fr"})
        assert settings.get("site_language") == "fr"
        # Settings > Name and homepage starts it again
        page = admin.get("/admin/settings?tab=name").text
        assert 'href="/admin/welcome" class="btn btn-sm">Run setup again' in page
    finally:
        settings.set_many(before)


def test_cover_order_and_tagline_placement(admin, client):
    before = {k: settings.get(k) for k in ("cover_width", "tagline", "banner_enabled", "banner_heading", "banner_subheading")}
    try:
        slug = save_post(admin, title="Order of things", cover_image="/uploads/order.webp")
        settings.set_many({"cover_width": "column"})
        html = client.get(f"/post/{slug}").text
        # column: the title first, then the picture
        picture = '<img src="/uploads/order.webp'
        assert html.index("Order of things</h1>") < html.index(picture)
        settings.set_many({"cover_width": "full"})
        html = client.get(f"/post/{slug}").text
        # edge to edge: the picture opens the page, before the title
        assert html.index(picture) < html.index("Order of things</h1>")
        # the tagline: above the posts without a banner; the banner's subheading with one
        settings.set_many({"tagline": "Bread, bikes and fog", "banner_enabled": "0"})
        assert client.get("/").text.count("Bread, bikes and fog") >= 1
        settings.set_many({"banner_enabled": "1", "banner_heading": "Hello", "banner_subheading": ""})
        home = client.get("/").text
        assert 'class="py-4 text-lg">Bread, bikes and fog' in home
        assert 'text-base-content/70 mb-6">Bread, bikes and fog' not in home
    finally:
        settings.set_many(before)


def test_getting_started_ticks_off_and_dismisses(admin):
    before = {k: settings.get(k) for k in ("getting_started_hidden", "email_provider", "last_backup_download")}
    try:
        settings.set_many({"getting_started_hidden": "0", "email_provider": "", "last_backup_download": ""})
        save_post(admin, title="A first post")
        # in the admin menu, opening a box in the middle of the screen - not
        # a card at the top of Posts and every Settings page
        page = admin.get("/admin/posts").text
        assert 'data-open-dialog="getting-started"' in page and 'id="getting-started"' in page
        box = page[page.index('id="getting-started"') - 300:]
        assert "line-through" in box[:box.index("Write your first post") + 30] and re.search(r">\d of 6<", page)
        assert "See what" not in page
        done = admin.get("/admin/welcome?step=done").text
        # the same list as the box's, ticked the same way
        assert "Write your first post" in done and "line-through" in done
        # a backup download counts as planning backups
        admin.get("/admin/backup/download?posts=1")
        assert settings.get("last_backup_download")
        # on every admin page, and dismissed from one, gone from all
        assert 'id="getting-started"' in admin.get("/admin/settings?tab=style").text
        r = admin.post("/admin/welcome/dismiss", data={"back": "/admin/settings?tab=style"},
                       follow_redirects=False)
        assert r.headers["location"] == "/admin/settings?tab=style"
        assert 'data-open-dialog="getting-started"' not in admin.get("/admin/posts").text
        # gone from the menu everywhere - only the way back is left, in Settings
        general = admin.get("/admin/settings?tab=name").text
        assert 'id="getting-started"' not in general and "Open Getting started" in general
        # it only ever goes back to an admin page
        r = admin.post("/admin/welcome/dismiss", data={"back": "https://evil.example/"}, follow_redirects=False)
        assert r.headers["location"] == "/admin/posts"
    finally:
        settings.set_many(before)


def test_templates_sit_above_save(admin):
    html = admin.get("/admin/settings?tab=editor").text
    form = html[html.index("data-declare-fields"):]
    # inside the Editor form, among its panels - not after its Save
    assert 'data-panel="editor-templates"' in form
    assert form.index('data-panel="editor-templates"') < form.index('id="save-status"')


def test_a_backup_is_named_after_the_site(admin):
    from soloblog import settings
    before = settings.get("site_title")
    try:
        settings.set_many({"site_title": "Mira's Kitchen"})
        r = admin.get("/admin/backup/download?posts=1")
        header = r.headers["content-disposition"]
        assert re.search(r"filename=\"Miras Kitchen-backup-\d{4}-\d{2}-\d{2}\.zip\"", header), header
        assert "filename*=UTF-8''Mira%27s%20Kitchen-backup-" in header
        # a title with characters no file may have, or none at all
        settings.set_many({"site_title": 'a/b: "c"?'})
        assert "ab c-backup-" in admin.get("/admin/backup/download?posts=1").headers["content-disposition"]
        settings.set_many({"site_title": "  "})
        assert "blog-backup-" in admin.get("/admin/backup/download?posts=1").headers["content-disposition"]
    finally:
        settings.set_many({"site_title": before})


def test_the_import_button_says_upload(admin):
    html = admin.get("/admin/settings?tab=backup").text
    assert "Choose export file" not in html


def test_settings_live_where_they_are_used(admin):
    """Each setting is saved by the tab that shows it - and a tab it left
    behind never clears it."""
    keys = ("footer_note", "meta_description", "app_icon_url", "app_name", "share_image_url")
    before = {k: settings.get(k) for k in keys}
    hx = {"HX-Request": "true"}
    try:
        r = admin.post("/admin/settings/style", headers=hx, data={
            "footer_note": "© Mira", "app_icon_url": "/uploads/icon.webp", "app_name": "Mira",
            "declared_fields": "footer_note,app_icon_url,app_name"})
        assert "text-success" in r.text
        admin.post("/admin/settings/address", headers=hx, data={
            "meta_description": "Fog and ferries", "share_image_url": "/uploads/share.webp",
            "declared_fields": "meta_description,share_image_url"})
        assert {k: settings.get(k) for k in keys} == {
            "footer_note": "© Mira", "meta_description": "Fog and ferries", "app_icon_url": "/uploads/icon.webp",
            "app_name": "Mira", "share_image_url": "/uploads/share.webp"}
        # General no longer has the first two: posting them there changes nothing
        admin.post("/admin/settings/name", headers=hx, data={
            "site_title": "Mira", "footer_note": "", "meta_description": "",
            "declared_fields": "site_title,footer_note,meta_description"})
        assert settings.get("footer_note") == "© Mira" and settings.get("meta_description") == "Fog and ferries"
        # an icon from somewhere else isn't kept, and says why
        r = admin.post("/admin/settings/style", headers=hx, data={
            "app_icon_url": "https://example.com/i.png", "declared_fields": "app_icon_url"})
        assert "one of your uploads" in r.text and settings.get("app_icon_url") == ""
        pages = {tab: admin.get(f"/admin/settings?tab={tab}").text
                 for tab in ("name", "header", "address", "integrations", "security", "email", "backup", "sharing")}
        assert 'name="footer_note"' in pages["header"] and 'name="app_name"' in pages["header"]
        assert 'name="meta_description"' in pages["address"] and 'name="footer_note"' not in pages["name"]
        assert 'name="share_image_url"' in pages["sharing"]
        assert 'name="app_icon_url"' not in pages["address"] and 'name="admin_email"' in pages["email"]
        assert "S3_BUCKET" in pages["backup"] and "S3_BUCKET" not in pages["integrations"]
    finally:
        settings.set_many(before)


def test_a_click_outside_a_drawer_closes_it(admin):
    """Each drawer's backdrop sits over everything but the drawer - the
    header, and in Focus mode the full-screen writing and its bars - so a
    click anywhere outside it lands on the backdrop and closes it."""
    from soloblog.ui import DRAWER_BACKDROP
    assert "z-[39]" in DRAWER_BACKDROP
    slug = save_post(admin, title="Drawer check")
    editor = admin.get(f"/admin/edit/{slug}").text
    media = admin.get("/admin/media").text
    for page, backdrop in ((editor, "post-settings-backdrop"), (editor, "editor-help-backdrop"),
                           (media, "media-details-backdrop")):
        tag = re.search(rf'<div[^>]*id="{backdrop}"[^>]*>', page).group(0)
        assert "z-[39]" in tag and "data-onclick" in tag, tag
    # the writing in Focus mode and its bars stay under it
    css = Path(os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "css", "input.css")).read_text()
    assert "CodeMirror-fullscreen { z-index: 35" in css and "z-index: 38" in css


def test_a_roll_with_the_summary_off_shows_no_false(admin, client):
    # "summary" off printed False under every title (an `and` chain's False)
    from soloblog import settings
    keep = {k: settings.get(k) for k in ("roll_style", "roll_shows")}
    try:
        for style in ("list", "cards", "magazine", "timeline"):
            settings.set_many({"roll_style": style, "roll_shows": "cover,date,tags"})
            assert ">False<" not in client.get("/").text, style
    finally:
        settings.set_many(keep)


def test_page_details_from_the_maintainers_round(admin, client):
    from soloblog import app as app_module, settings
    from soloblog.routes import editor
    js = app_module.CHROME_OFFSETS_JS + app_module.PAGE_HELPERS_JS + editor.PIN_LOCATION_JS
    # one-sided timeline cards stretch - w-full and the gap ran them into the line
    keep = {k: settings.get(k) for k in ("roll_style", "timeline_align", "cover_width")}
    try:
        settings.set_many({"roll_style": "timeline", "timeline_align": "right"})
        save_post(admin, title="On the line", body="Words.")
        home = client.get("/").text
        assert "justify-self-stretch min-w-0 me-3" in home and "w-full justify-self-stretch" not in home
        # edge to edge meets the header (and a landing page's last band, the footer)
        settings.set_many({"cover_width": "full"})
        slug = save_post(admin, title="Edge to edge", body="Words.", cover_image="/uploads/x.webp")
        assert "data-flush" in client.get(f"/post/{slug}").text and "function flushEdges(content)" in js
    finally:
        settings.set_many(keep)
    # the wheel over a side panel scrolls it or nothing, never the page behind
    assert "[data-own-scroll]" in js and "{passive: false}" in js
    assert "data-own-scroll" in admin.get("/admin/new").text
    # a link clicked in a Design preview keeps the preview
    assert "['design_preview', 'preset_preview']" in js
    # Post settings a full-height rail on the right, as the admin's is on the left
    assert "document.querySelector('[data-admin-rail]')" in js and "window.innerWidth - left - 22.5 * rem >= 50 * rem" in js


def test_animations_off_stops_every_transition():
    # only the scripts written to check it stopped; drawers, menus, fades
    # and the editor's sheet still moved - one rule ends them all at once
    css = Path("static/css/input.css").read_text(encoding="utf-8")
    rule = css[css.index("[custom-css: animations-off]"):]
    assert "html:not([data-animate]) :is(*, *::before, *::after):not(.loading)" in rule
    assert "transition-duration: 0.01ms !important" in rule and "prefers-reduced-motion: reduce" in rule


def test_a_drafts_notice_goes_under_a_cover_that_opens_the_page(admin):
    # above it, the cover wasn't first, so it never met the header: a
    # strip of page at the top, the notice under the cover, the arrow
    # off the screen
    for width in ("screen", "full"):
        slug = save_post(admin, title=f"Draft cover {width}", body="Words.", cover_image="/uploads/hills.webp",
                         cover_width=width, published="")
        page = admin.get(f"/post/{slug}").text
        assert page.index('data-flush="open"') < page.index("only visible to you"), width
    slug = save_post(admin, title="Draft column cover", body="Words.", cover_image="/uploads/hills.webp",
                     cover_width="column", published="")
    page = admin.get(f"/post/{slug}").text
    assert page.index("only visible to you") < page.index("Draft column cover</h1>")


def test_a_full_screen_cover(admin, client):
    # the cover as tall as the window, the title over its foot, an arrow down
    from soloblog import pages, posts
    assert "screen" in pages.COVER_STYLES and "screen" not in pages.COVER_WIDTHS  # not the banner's
    slug = save_post(admin, title="Over the hills", body="The words.", cover_image="/uploads/hills.webp",
                     cover_width="screen")
    assert posts.get_post(slug)["cover_width"] == "screen"
    page = client.get(f"/post/{slug}").text
    assert "min-h-[calc(100svh-var(--header-h,0px)+var(--flush-top,0px))]" in page
    assert 'href="#read-on"' in page and 'id="read-on"' in page and page.count("Over the hills</h1>") == 1
    # the arrow leaves none of the photo over a floating header, and room
    # under the header for Listen (checked in a browser at 1377 and 375 px)
    assert "scroll-mt-[calc(-1*var(--header-h,0px)_-_1rem)]" in page
    assert "mb-[max(2rem,calc(var(--header-h,0px)_+_0.5rem))]" in page
    assert "Cover image" in admin.get("/admin/settings?tab=posts").text
    # its caption over its corner, as every picture shown at size has one
    from soloblog import images
    images.set_meta("hills.webp", "Hills", "Evening over the hills")
    try:
        page = admin.get(f"/post/{slug}").text
        at = page.index("Evening over the hills")
        assert "absolute bottom-2 end-3" in page[at - 120:at]
    finally:
        images.set_meta("hills.webp", "", "")


def test_one_search_in_the_top_bar_for_settings_and_help(admin, client):
    # from any admin page, every setting and every Help page (checked in a
    # browser at 1440 and 375 px: results take the page's place, Clear
    # brings it back, a result opens its setting; the phone's magnifier
    # opens it as a row under the bar)
    html = admin.get("/admin/posts").text
    bar = html[html.index("data-admin-bar"):html.index("</header>", html.index("data-admin-bar"))]
    assert 'id="admin-search"' in bar and 'data-index-search="/admin/search-index"' in bar
    assert 'data-recent-searches="admin"' in bar
    assert 'data-index-body="page-content"' in bar and "data-index-no-url" in bar
    assert 'id="page-content-results"' in html and "toggleAdminSearch" in bar
    entries = admin.get("/admin/search-index").json()
    groups = {e["group"].split(": ")[0] for e in entries}
    assert groups == {"Admin", "Settings", "Help"} and any(e["title"] == "Favicon" for e in entries)
    # the admin's own pages too - Site health and its log weren't findable
    pages = {e["title"]: e["href"] for e in entries if e["group"] == "Admin"}
    assert pages["Site health log"] == "/admin/health?tab=log" and pages["Stats"] == "/admin/stats"
    assert client.get("/admin/search-index", follow_redirects=False).status_code in (302, 303)
    # no second box on Settings or Help: the bar's searches both, a phone's too
    for page in ("/admin/settings?tab=name", "/admin/help"):
        assert admin.get(page).text.count("data-index-search=") == 1
    from soloblog import app as app_module
    js = app_module.INDEX_SEARCH_JS
    assert "if (!box.hasAttribute('data-index-no-url'))" in js and "function toggleAdminSearch" in js
    assert "out.id.slice(0, -'-results'.length)" in js and "2 * (first.length - at)" in js
    assert 'data-index-first="Admin|Settings: "' in html


def test_no_undo_once_a_setting_is_back_where_it_started():
    # Standard, then Narrow, then Standard again offered Undo - there's
    # nothing to undo when it's as the page opened (autosave.js)
    from soloblog import app as app_module
    js = app_module.AUTOSAVE_JS
    assert "if (!(name in form._opened)) form._opened[name] = _snapKey(before);" in js
    assert "if (ok && !undoing && !back) {" in js


def test_full_screen_is_the_covers_default():
    # the app's own default, Mira's, and every preset that doesn't choose
    from soloblog import demo, presets
    assert settings.DEFAULTS["cover_width"] == "screen"
    assert presets._BASE["cover_width"] == "screen"
    assert '"cover_width": "screen"' in Path(demo.__file__).read_text(encoding="utf-8")


def test_view_is_drawn_like_the_other_row_actions(admin):
    # it borrowed the small, faded icon beside a menu's outside link
    from soloblog import ui
    assert 'class="h-3.5 w-3.5"' in ui.VIEW_SVG and 'stroke-width="2"' in ui.VIEW_SVG
    assert "opacity" not in ui.VIEW_SVG
    save_post(admin, title="A row to view")
    html = admin.get("/admin/posts").text
    view = html[html.index('aria-label="View"'):]
    assert str(ui.VIEW_SVG) in view[:view.index("</a>")]


def test_what_opens_the_page_is_drawn_at_the_top_from_the_start(admin, client):
    # a full-width banner or cover first showed below the header, a strip
    # of page above it, until the script moved it up (checked with scripts
    # off: the banner and a full screen cover both at 0)
    from soloblog import ui
    keep = {k: settings.get(k) for k in ("banner_enabled", "banner_heading", "banner_width", "header_style", "cover_width")}
    try:
        settings.set_many({"banner_enabled": "1", "banner_heading": "Hello", "banner_width": "full",
                           "header_style": "floating", "cover_width": "screen"})
        home = client.get("/").text
        assert 'data-flush="open"' in home and ui.FLUSH_GUESS["floating"].split()[0].replace("&", "&amp;") in home
        slug = save_post(admin, title="Over the top", cover_image="/uploads/top.webp")
        page = admin.get(f"/post/{slug}").text
        assert 'data-flush="open"' in page
        # Edit's buttons over the photo keep the theme's own colours - a dark
        # fill of their own was custom, unlike every other button
        assert "_.btn]:bg-black" not in page and "a:not(.btn)]:text-white" in page
    finally:
        settings.set_many(keep)


def test_a_banner_behind_a_floating_header_is_taller_by_it(client):
    # under a floating header the banner lost the header's height to it -
    # it's that much taller there, so what's on it keeps its room
    keep = {k: settings.get(k) for k in ("banner_enabled", "banner_heading", "banner_width")}
    try:
        settings.set_many({"banner_enabled": "1", "banner_heading": "Hello", "banner_width": "full"})
        home = client.get("/").text
        assert "min-h-[calc(26rem+var(--flush-top,0px))]" in home
        # the room under the header is the content's: the overlay covers the
        # whole photo (padding on the banner left a lighter strip, and a line)
        assert "hero-content text-center pt-[calc(1rem+var(--flush-top,0px))]" in home
        assert "pt-(--flush-top)" not in home
    finally:
        settings.set_many(keep)


def test_the_admin_is_a_size_up_and_the_site_menu_14px(admin, client):
    # the admin's controls and small print were a size below its own menu
    # (input.css, admin-scale); the site's header menu was 12px
    from soloblog.ui.layout import ADMIN_SCALE
    for c in ("[&_.btn-sm]:[--size:calc(var(--size-field,0.25rem)*9)]", "[&_.badge-xs]:text-[0.75rem]",
              "[&_.fieldset]:text-[0.875rem]", r"[&_.text-xs:not([class*=\:text-])]:text-[0.8125rem]/5"):
        assert c in ADMIN_SCALE
    assert "'" not in ADMIN_SCALE and '"' not in ADMIN_SCALE  # a quote in a class trips themes.lean_css
    css = Path("static/css/input.css").read_text(encoding="utf-8")
    assert re.search(r'data-admin class="drawer \[&amp;_\.btn-sm\]', admin.get("/admin/posts").text)
    assert "data-admin" not in client.get("/").text
    assert 'text-xl sm:text-2xl font-bold min-w-0">Posts and pages' in admin.get("/admin/posts").text
    home = client.get("/").text
    assert "menu menu-horizontal menu-sm" not in home and "menu menu-horizontal px-1" in home
    # the writing at the size it's read (pages._prose: 16px, 18px from 48rem)
    assert "--editor-fs: 1.125rem" in css and "[&>*]:max-w-[calc(36*var(--editor-fs,1rem))]" in admin.get("/admin/editor.js").text


def test_a_sliders_pictures_fill_its_frame():
    # whole pictures left bars beside or above them; like a cover, each
    # fills the frame - the lightbox shows it whole - in one shape at
    # every width, a photo's own 3:2, so a 3:2 picture is never cropped
    from soloblog import gallery
    src = Path(gallery.__file__).read_text(encoding="utf-8")
    slider = src[src.index("else:  # slider"):]
    assert '"w-full aspect-[3/2] object-cover"' in slider and "object-contain" not in slider[:600]


def test_setup_and_getting_started_are_two_things(admin, monkeypatch):
    # the setup's screens and the list of what's next sent people to each
    # other: the list's email job was a setup-looking screen, the list
    # offered the setup again, and "Open Getting started" opened the setup
    # once the list was done. Now the setup asks about the site and runs
    # once (again from Settings); the list's jobs are each a settings page
    from soloblog.routes import welcome
    before = {k: settings.get(k) for k in ("getting_started_hidden", "email_provider", "setup_done", "admin_email")}
    try:
        settings.set_many({"getting_started_hidden": "0", "email_provider": "", "setup_done": "1", "admin_email": ""})
        steps = welcome.next_steps(settings.get_all())
        # email: the address first, then a way to send - on Settings > Email
        assert steps[0][1] == "Set up email" and not steps[0][4]
        assert steps[0][3] == "/admin/settings?tab=email&panel=email-admin"
        settings.set_many({"admin_email": "mira@example.com"})
        assert welcome.next_steps(settings.get_all())[0][3] == "/admin/settings?tab=email&panel=email-sending"
        # no job of the list is a screen of the setup
        assert not [where for _, _, _, where, _ in steps if where.startswith("/admin/welcome")]
        page = admin.get("/admin/settings?tab=name").text
        assert 'href="/admin/welcome" class="btn btn-sm">Run setup again' in page
        assert 'data-open-dialog="getting-started" class="btn btn-sm">Open Getting started' in page
        # the box doesn't lead to the setup once it's been finished
        box = admin.get("/admin/posts").text
        box = box[box.index('id="getting-started"'):]
        assert "/admin/welcome?" not in box[:box.index("</dialog>")] \
            and 'href="/admin/welcome"' not in box[:box.index("</dialog>")]
        # dismissed: the same button brings it back, its box open
        admin.post("/admin/welcome/dismiss", data={"back": "/admin/posts"})
        page = admin.get("/admin/settings?tab=name").text
        assert 'form="show-getting-started" class="btn btn-sm">Open Getting started' in page
        settings_form = page[page.index('hx-post="/admin/settings/name"'):]
        settings_form = settings_form[:settings_form.index("</form>")]
        assert 'id="show-getting-started"' not in settings_form and 'id="show-getting-started"' in page
        r = admin.post("/admin/welcome/show", data={"back": "/admin/settings?tab=name#getting-started"},
                       follow_redirects=False)
        assert r.headers["location"] == "/admin/settings?tab=name#getting-started"
        assert 'data-open-dialog="getting-started"' in admin.get("/admin/posts").text
        r = admin.post("/admin/welcome/show", data={"back": "https://evil.example/"}, follow_redirects=False)
        assert r.headers["location"] == "/admin/posts"
        # never finished (the browser closed halfway): the box says so
        settings.set_many({"setup_done": "0"})
        assert "Finish setting up your site" in admin.get("/admin/posts").text
        # every job done: nothing left to open, and the setup is still there to run again
        monkeypatch.setattr(welcome, "next_steps", lambda s: [(None, "Done", "", "/admin/posts", True)])
        page = admin.get("/admin/settings?tab=name").text
        assert "Open Getting started" not in page and "Run setup again" in page
    finally:
        settings.set_many(before)


def test_setup_again_changes_nothing_by_itself(admin):
    # the style screen came back with the site's style chosen, so Continue
    # applied it again over everything changed since
    before = {k: settings.get(k) for k in ("preset", "setup_done", "list_style")}
    try:
        settings.set_many({"preset": "magazine", "setup_done": "1"})
        html = admin.get("/admin/welcome?step=style").text
        ticked = re.findall(r'<input[^>]*name="preset"[^>]*checked[^>]*>', html)
        assert len(ticked) == 1 and 'value=""' in ticked[0]
        # and it's a screen to change things on, not a welcome
        first = admin.get("/admin/welcome").text
        assert "Welcome to Soloblog" not in first and "Your site</h1>" in first
    finally:
        settings.set_many(before)


def test_each_step_opens_the_place_its_done(admin):
    # three led to the top of a Settings tab, and "Describe your site" to
    # the wrong tab: the description is under Address and sharing
    from soloblog.routes import welcome
    before = {k: settings.get(k) for k in ("meta_description", "tagline")}
    try:
        settings.set_many({"meta_description": "", "tagline": ""})
        steps = {title: (where, done) for _, title, _, where, done in welcome.next_steps(settings.get_all())}
        for title, panel in (("Protect your login", "security-passkeys"), ("Plan your backups", "backup-download"),
                             ("Describe your site", "address-search")):
            where = steps[title][0]
            assert f"panel={panel}" in where, title
            assert f'data-panel="{panel}"' in admin.get(where).text, title
        assert "setting=Description" in steps["Describe your site"][0] and not steps["Describe your site"][1]
        assert ">Description<" in admin.get(steps["Describe your site"][0]).text
        # a tagline is what search results show until there's a description
        settings.set_many({"tagline": "Bread and bikes"})
        assert dict((t, d) for _, t, _, _, d in welcome.next_steps(settings.get_all()))["Describe your site"]
    finally:
        settings.set_many(before)


def test_getting_started_says_what_its_buttons_do(admin):
    # Close and Dismiss didn't say what happens to it; and from a phone's
    # menu drawer, closing left the drawer open, as if nothing had closed
    before = {k: settings.get(k) for k in ("getting_started_hidden", "email_provider")}
    try:
        settings.set_many({"getting_started_hidden": "0", "email_provider": ""})
        page = admin.get("/admin/posts").text
        box = page[page.index('id="getting-started"'):]
        box = box[:box.index('</dialog>')]
        assert ">Remind me later<" in box and ">Don't show again<" in box
        assert ">Close<" not in box and ">Dismiss<" not in box
    finally:
        settings.set_many(before)
    from soloblog import app as app_module
    js = app_module.ACTIONS_JS
    assert "drawer.parentElement.querySelector(':scope > .drawer-toggle')" in js and "toggle.checked = false" in js


def test_every_settings_page_is_in_the_search(admin):
    # Name and homepage dropped out of it when its page became two pieces
    from soloblog.ui import SETTINGS_SECTIONS
    entries = admin.get("/admin/settings/search-index").json()
    titles = {(e["group"], e["title"]) for e in entries}
    assert ("Name and homepage", "Tagline") in titles and ("Name and homepage", "Site title") in titles
    for _, label in SETTINGS_SECTIONS:
        assert sum(1 for e in entries if e["group"] == label) > 1, label


def test_the_look_resets_to_soloblogs_own_and_undoes(admin):
    # one go, asked first, everything that's yours kept, Undo brings it back
    from soloblog import presets
    keep = {k: settings.get(k) for k in ("theme", "header_style", "banner_heading", "footer_note", "preset",
                                          "preset_undo", "site_title")}
    try:
        settings.set_many({"theme": "nord", "header_style": "inline", "banner_heading": "Mine", "footer_note": "© me"})
        values = presets.find(presets.DEFAULT_KEY)[2]
        assert values["theme"] == settings.DEFAULTS["theme"] and "banner_heading" not in values
        assert "site_title" not in values and "home_page" not in values and "footer_note" not in values
        page = admin.get("/admin/settings?tab=style").text
        # among the styles, after Custom, with a picture like the rest, and it asks first
        panel = page[page.index('data-panel="style-presets"'):]
        assert panel.index(">Custom<") < panel.index(">Default<") < panel.index(">Personal blog<")
        assert presets.find(presets.DEFAULT_KEY)[0] == "Default"
        assert "Use the Default style? Your colours go back to the default too" in page
        assert "own look" not in page
        admin.post("/admin/presets/apply", data={"key": presets.DEFAULT_KEY})
        assert settings.get("theme") == settings.DEFAULTS["theme"]
        assert settings.get("header_style") == settings.DEFAULTS["header_style"]
        assert settings.get("banner_heading") == "Mine" and settings.get("footer_note") == "© me"
        admin.post("/admin/presets/undo")
        assert settings.get("theme") == "nord" and settings.get("header_style") == "inline"
    finally:
        settings.set_many(keep)


def test_custom_code_and_comment_emails_are_where_theyre_about(admin):
    # Custom code was under Search engines, comment emails under Integrations
    site = admin.get("/admin/settings?tab=address").text
    integrations = admin.get("/admin/settings?tab=integrations").text
    comments = admin.get("/admin/settings?tab=messages").text
    assert 'name="custom_head"' not in site and 'name="custom_head"' in integrations
    assert 'name="notify_comments"' in comments and 'name="notify_comments"' not in integrations
    keep = {k: settings.get(k) for k in ("custom_css", "notify_comments")}
    try:
        admin.post("/admin/settings/integrations", data={"custom_css": "p{color:red}</style><script>x</script>",
                                                    "declared_fields": "custom_css"}, headers={"HX-Request": "true"})
        assert settings.get("custom_css").startswith("p{color:red}") and "</style" not in settings.get("custom_css")
        admin.post("/admin/settings/name", data={"notify_comments": "1", "declared_fields": "notify_comments"},
                   headers={"HX-Request": "true"})
        assert settings.get("notify_comments") == "1"
    finally:
        settings.set_many(keep)


def test_preview_mode_matches_the_admin(admin):
    # its controls were a size below the admin's, its backdrop a third shade,
    # and the style cards two to a row in its narrow column, squeezing their
    # buttons - they go by their column's width now (@container)
    page = admin.get("/admin/settings?tab=style").text
    pane = page[page.index("data-design-preview"):]
    pane = pane[:pane.index('data-preview-frame')]
    assert "btn-xs" not in pane and "select-xs" not in pane and "select select-sm" in pane
    assert "bg-base-300" not in pane[:pane.index(">")] and "bg-base-200" in pane[:pane.index(">")]
    presets_panel = page[page.index('data-panel="style-presets"'):]
    assert 'class="@container"' in presets_panel and "@lg:grid-cols-2" in presets_panel
    assert "@max-lg:grid-cols-[6rem_minmax(0,1fr)]" in presets_panel


def test_copy_stays_put_and_uses_names_read_on_a_phone(admin, client):
    # Copy was inside the code, so it scrolled away with a long line; on a
    # phone the Uses page's names were a letter wide (checked in a browser
    # at 375 and 320 px)
    from soloblog import app as app_module
    js = app_module.CODE_COPY_JS
    assert "wrap.appendChild(pre);" in js and "wrap.appendChild(btn);" in js and "pre.appendChild(btn)" not in js
    slug = save_post(admin, title="My desk",
                     body="## What I use\n\nSection: Uses\n\n### Desk\n\n- **A laptop** - for most things\n")
    assert "max-sm:row-start-2!" in client.get(f"/post/{slug}").text


def test_contact_messages_only_in_the_menu_while_in_use(admin):
    from soloblog import contact
    from soloblog.db import get_db
    get_db().execute("DELETE FROM contact_messages")
    settings.set_many({"contact_enabled": "0"})
    assert 'href="/admin/messages"' not in admin.get("/admin/media").text
    # the page still opens, with a link that turns the form on
    assert 'href="/admin/settings?tab=messages&amp;panel=messages-contact"' in admin.get("/admin/messages").text
    # messages kept from when it was on stay findable
    contact.add("Ada", "ada@example.com", "Hello")
    assert admin.get("/admin/media").text.count('href="/admin/messages"') >= 2
    get_db().execute("DELETE FROM contact_messages")
    settings.set_many({"contact_enabled": "1"})
    assert 'href="/admin/messages"' in admin.get("/admin/media").text
    settings.set_many({"contact_enabled": "0"})


def test_admin_bar_has_the_gear_where_the_rail_folds(admin):
    html = admin.get("/admin/posts").text
    bar = html[html.index("data-admin-bar"):]
    bar = bar[:bar.index("</header>")]
    assert 'popovertarget="nav-admin-menu"' in bar
    # its Log out uses the drawer's form - one form, one id
    assert html.count('id="admin-logout-form"') == 1
    assert html.count('id="nav-admin-menu"') == 1


def test_pinned_pages_in_published_and_pinned_drafts_in_pinned(admin, client):
    live = save_post(admin, title="A pinned live page", pinned="1", pin_location="footer")
    draft = save_post(admin, title="A pinned draft page", pinned="1", pin_location="footer", published="")
    try:
        assert posts.get_post(draft)["published"] == 0 and posts.get_post(draft)["pinned"] == 1
        published = admin.get("/admin/posts?status=published&q=pinned").text
        assert "A pinned live page" in published and "A pinned draft page" not in published
        pinned = admin.get("/admin/posts?status=pinned").text
        assert "A pinned live page" in pinned and "A pinned draft page" in pinned
        assert "A pinned draft page" in admin.get("/admin/posts?status=draft&q=pinned").text
        # visitors still never see a draft in the menu
        footer = client.get("/").text
        assert "A pinned live page" in footer and "A pinned draft page" not in footer
    finally:
        for slug in (live, draft):
            posts.delete_post(slug)


def test_type_filter_shows_only_posts_pages_or_series(admin):
    # tabs are for a post's state; what kind it is is a filter beside Tag
    page = save_post(admin, title="Kindonly about page", pinned="1", pin_location="header")
    top = save_post(admin, title="Kindonly pinned post", pinned="1", pin_location="top")
    plain = save_post(admin, title="Kindonly plain post", published="")
    part = save_post(admin, title="Kindonly series part", series_name="Kindonly series")
    try:
        html = admin.get("/admin/posts?kind=posts&q=kindonly").text
        assert "Kindonly plain post" in html and "Kindonly pinned post" in html and "Kindonly about page" not in html
        assert 'placeholder="Search posts and pages…"' in html
        html = admin.get("/admin/posts?kind=pages&q=kindonly").text
        assert "Kindonly about page" in html and "Kindonly plain post" not in html and "1 page " in html
        html = admin.get("/admin/posts?kind=series&q=kindonly").text
        assert "Kindonly series part" in html and "Kindonly plain post" not in html
        # with a state tab: drafts that are posts
        html = admin.get("/admin/posts?status=draft&kind=posts&q=kindonly").text
        assert "Kindonly plain post" in html and "Kindonly pinned post" not in html
        # the addresses the Posts and Series tabs had still work
        html = admin.get("/admin/posts?status=posts&q=kindonly").text
        assert "Kindonly plain post" in html and "Kindonly about page" not in html
        html = admin.get("/admin/posts?status=series&q=kindonly").text
        assert "Kindonly series part" in html and "Kindonly plain post" not in html
        # a kind nobody offers is no filter, not an error
        assert "Kindonly about page" in admin.get("/admin/posts?kind=bogus&q=kindonly").text
    finally:
        for slug in (page, top, plain, part):
            posts.delete_post(slug)


def test_posts_tabs_are_states_and_a_row_keeps_two_buttons(admin):
    import re
    slug = save_post(admin, title="A row with a More menu")
    try:
        html = admin.get("/admin/posts").text
        tabs = re.findall(r'href="/admin/posts\?status=(\w+)[^>]*class="tab ', html)
        assert list(dict.fromkeys(tabs)) == ["all", "published", "scheduled", "draft", "trash"]
        # Pinned, Tags and Calendar are other pages: links beside the title
        views = html[html.index('id="posts-views"'):][:1500]
        assert all(f"status={v}" in views for v in ("pinned", "tags", "calendar"))
        # Edit and View beside the row, the rest under its More
        acts = html[html.index(f'id="acts-{slug}"'):]
        more = acts.index(f'id="acts-{slug}-more"')
        assert 'aria-label="Edit"' in acts[:more] and 'aria-label="View"' in acts[:more]
        assert 'aria-label="Duplicate"' not in acts[:more]
        menu = acts[more:][:6000]
        assert all(f'aria-label="{name}"' in menu for name in ("Edit in Focus", "Copy link", "Duplicate", "Trash"))
        # on a phone the filters wait behind one Filter button; set, they show
        assert "data-filter-toggle" in html and not re.search(r"<input[^>]*data-filter-toggle[^>]*checked", html)
        assert re.search(r"<input[^>]*data-filter-toggle[^>]*checked|<input[^>]*checked[^>]*data-filter-toggle",
                         admin.get("/admin/posts?kind=pages").text)
    finally:
        posts.delete_post(slug)


def test_getting_started_knows_a_domain_and_a_real_first_post(admin, monkeypatch):
    from soloblog import config
    from soloblog.routes import welcome
    for address, own in (("https://myblog.fly.dev", False), ("https://blog.onrender.com", False),
                         ("http://localhost:5001", False), ("http://192.168.1.20:8080", False),
                         ("https://myblog.up.railway.app", False), ("https://miracastell.com", True),
                         ("https://blog.miracastell.com", True)):
        monkeypatch.setattr(config, "BASE_URL", address)
        assert welcome.has_own_domain() is own, address
    # the welcome draft every site starts with isn't a first post
    rows = posts.list_posts(include_drafts=True)
    keep = [r["slug"] for r in rows if r["slug"] != welcome.WELCOME_SLUG]
    first = lambda: dict((title, done) for _, title, _, _, done in welcome.next_steps(settings.get_all()))[  # noqa: E731
        "Write your first post"]
    assert first() == bool(keep)
    slug = save_post(admin, title="Really mine")
    assert first()
    posts.delete_post(slug)


def test_the_editor_says_what_a_post_is_beside_its_state(admin):
    # "Post:" or "Page:" before its name; under it, on a line of their own:
    # on a new post the template it started from (a pill that opens the picker, the
    # others' size), pinned and who can read it. The sections are in the
    # toolbar's Go to menu, not under the heading.
    body = "Hi.\n\n## Plans\n\nSection: Pricing\n\n## Kind words\n\nSection: Testimonials\n"
    page = save_post(admin, title="Pills page", body=body, pinned="1", pin_location="header")
    post = save_post(admin, title="Pills post", body=body, pinned="1", pin_location="top")
    try:
        html = admin.get(f"/admin/edit/{page}").text
        assert re.search(r"<h1[^>]*>\s*<span data-post-kind[^>]*>Page:</span> Pills page\s*</h1>", html)
        assert "Editing:" not in html
        # a saved page with nothing to show has no row (it's hidden, not an empty gap)
        assert re.search(r'<div hidden id="post-pills" class="basis-full', html)
        assert "Sections:" not in html and "Go to this section" not in html and "goToSection" not in html
        assert 'aria-label="Go to Pricing section"' not in html
        # a new post's pill opens the picker, the same size as the others
        pills = admin.get("/admin/new").text.split('id="post-pills"')[1].split("</div>")[0]
        assert re.search(r'<button[^>]*data-tap-area[^>]*class="badge badge-sm', pills)
        assert 'data-open-dialog="template-start-dialog"' in pills and ">Template: Blank</span>" in pills
        assert "Sections" not in pills
        html = admin.get(f"/admin/edit/{post}").text
        assert re.search(r"<span data-post-kind[^>]*>Post:</span> Pills post\s*</h1>", html)
        pills = html.split('id="post-pills"')[1].split("</div>")[0]
        assert ">Pinned</span>" in pills and '<div id="post-pills"' in html
        assert "Pricing" not in pills
        assert ">New post</h1>" in admin.get("/admin/new").text
    finally:
        posts.delete_post(page)
        posts.delete_post(post)


def test_the_sections_menu_writes_names_as_text():
    # a section's kind and heading come from what's typed in the post: set as
    # text, never as markup, wherever the menu is drawn
    js = Path("soloblog/js/slash_menu.js").read_text(encoding="utf-8")
    row = js.split("function sectionRow(it, i) {")[1].split("mde.openSections")[0]
    assert "kind.textContent = it.label" in row and "about.textContent = it.about" in row
    assert "innerHTML" not in row.replace("icon.innerHTML = it.icon", "").replace("tick.innerHTML", "")
    init = Path("soloblog/js/editor_init.js").read_text(encoding="utf-8")
    assert "goToSection" not in init and "Go to this section" not in init


def test_the_summary_box_shows_a_few_lines_and_saves_one(admin):
    slug = save_post(admin, title="Summary lines", summary="A first line\nand a second  one")
    try:
        assert posts.get_post(slug)["summary"] == "A first line and a second one"
        html = admin.get(f"/admin/edit/{slug}").text
        assert re.search(r'<textarea[^>]*name="summary"[^>]*rows="3"', html) or \
            re.search(r'<textarea[^>]*rows="3"[^>]*name="summary"', html)
    finally:
        posts.delete_post(slug)


def test_the_lightbox_fits_each_picture_and_never_flashes_the_last(client):
    from soloblog import js, settings as site
    from soloblog.ui import LightboxDialog
    from fasthtml.common import to_xml
    box = to_xml(LightboxDialog(site.get_all()))
    assert "modal-box w-fit" in box and "w-0 min-w-full" in box
    # its caption a line of its own on a phone, not squeezed by the buttons
    assert "w-full sm:w-auto sm:flex-1" in box
    # the count and buttons on the right, a caption beside them or none
    assert "tabular-nums ml-auto\"" in box and "sm:ml-0" not in box
    script = Path(os.path.join(os.path.dirname(js.__file__), "lightbox.js")).read_text()
    # opening empties it first and opens once the picture's there; moving
    # fades the old into the new (no slide, no empty box between), with the
    # pictures either side loaded ahead and a spinner for a slow one
    assert "img.removeAttribute('src')" in script and "_lbLoaded(item.src)" in script
    assert "translateX" not in script and "data-lightbox-ghost" in script and "_lbAhead()" in script
    assert 'id="lightbox-loading"' in box and "loading-spinner" in box
    opening = script.split("function openLightbox")[1].split("function stepLightbox")[0]
    assert opening.index("_lbLoaded(item.src)") < opening.rindex("showModal()")


def test_a_toolbars_tooltip_shows_over_the_sidebar():
    css = Path(os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "css", "input.css")).read_text()
    assert ".editor-toolbar:has(.tooltip:is(:hover, :focus-visible))" in css


def test_the_editor_marks_sections_and_blocks_apart_from_the_writing():
    from soloblog import js
    script = Path(os.path.join(os.path.dirname(js.__file__), "editor_init.js")).read_text()
    assert "line-sb-section" in script and "line-sb-setting" in script and "line-sb-block" in script
    css = Path(os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "css", "input.css")).read_text()
    for kind in ("sb-section", "sb-setting", "sb-block"):
        assert f".EasyMDEContainer .CodeMirror-line.{kind}" in css


def test_the_insert_menu_offers_a_sections_and_a_gallerys_options_first(admin):
    # with the cursor in a section, its Key: lines come first in the / menu
    # and Insert - Default first in each, the one in use marked; in a
    # gallery, its styles
    from soloblog import gallery, js, pages
    from soloblog.editor_config import block_options
    o = block_options()
    assert [w[0] for w in o["options"]["Width"]["values"]] == ["column", "wide", "full"]
    assert [s[0] for s in o["options"]["Style"]["values"]] == ["card"]
    assert [g[0] for g in o["gallery"]] == list(gallery.STYLES) and o["sections"]["hero"]["width"] == "full"
    # a section's own lines (Portfolio, Latest posts), a callout's kind and
    # a fold's - what Default does for Show as follows Settings > Posts
    assert [a[0] for a in o["options"]["Show as"]["values"]] == list(pages.PORTFOLIO_STYLES)
    assert o["options"]["Count"]["suggest"] == [3, 6, 9, 12]
    assert [c[0] for c in o["callout"]] == ["note", "tip", "warning", "danger"]
    assert o["kinds"]["portfolio"] == "portfolio" and o["kinds"]["latest posts"] == "latest"
    assert o["sections"]["latest"]["options"] == ["Width", "Style", "Heading", "Space", "Appear", "Count", "Tag"]
    assert o["options"]["Show as"]["default"] == "Follow the site (Grid)"
    assert block_options({"portfolio_style": "rows"})["options"]["Show as"]["default"] == "Follow the site (Rows)"
    assert '"options": {' in admin.get("/admin/new").text
    script = Path(os.path.join(os.path.dirname(js.__file__), "slash_menu.js")).read_text()
    assert "var here = blockOptions();" in script and "'In use'" in script and "' section'" in script
    # on a phone, the + sheet opens on a tab of them (checked at 375 px)
    assert "mde.blockOptions = blockOptions;" in script
    assert "return ['Callout', out];" in script and "return ['Collapsible', out];" in script
    assert "OPTIONS.sections[OPTIONS.kinds[" in script and "write(OPTIONS.defaultWord)" in script
    # a value the page can't use is underlined, with what it can be under it
    # (checked in a browser: Width: Tall, Count: 40, a gallery's wobbly,
    # Section: Pricng - and the demo's every section loads with none)
    assert "cm.addLineWidget(line, note)" in script and "OPTIONS.reserved" in script
    assert o["options"]["Width"]["note"] == "Width can be Column, Wide, Full or Default"
    assert "{ className: 'underline decoration-wavy decoration-error underline-offset-3' }" in script
    init = Path(os.path.join(os.path.dirname(js.__file__), "editor_init.js")).read_text()
    assert "if (here && here[1].length) { names.unshift(BLOCK); first = 0; }" in init
    for name in ("Site address", "Admin email"):
        assert name in admin.get("/admin/settings?tab=address" if name == "Site address" else "/admin/settings?tab=email").text
    assert "Custom colo" in admin.get("/admin/settings?tab=style").text


def test_an_unlisted_page_in_the_menu_says_its_still_there(admin):
    # Unlisted left a menu page out of search while everyone saw it in the
    # menu - a line under the switch says so, kept in step as either changes
    from soloblog import js
    page = save_post(admin, title="Hidden menu page", body="Words.", pinned="1", pin_location="header", unlisted="1")
    post = save_post(admin, title="Hidden post", body="Words.", unlisted="1")
    try:
        html = admin.get(f"/admin/edit/{page}").text
        note = re.search(r'<p[^>]*id="unlisted-note"[^>]*>([^<]*)</p>', html)
        assert note and "hidden" not in note.group(0) and "in the menu, so anyone can still open it" in note.group(1)
        assert '<p hidden id="unlisted-note"' in admin.get(f"/admin/edit/{post}").text
        script = Path(os.path.join(os.path.dirname(js.__file__), "editor_init.js")).read_text()
        assert "form.addEventListener('change', syncUnlisted);" in script
    finally:
        posts.delete_post(page)
        posts.delete_post(post)


def test_a_phone_keeps_settings_and_help_beside_save(admin):
    # Discard and View fold into ⋯ first (checked at 412 px: Settings and
    # Help stay; at 375 px Help folds too)
    from soloblog import js
    html = admin.get(f"/admin/edit/{save_post(admin, title='Fold order', body='Words.')}").text
    row = html.split("data-actions-row")[1].split("data-actions-more")[0]
    assert row.count("data-fold-first") == 2 and re.search(r'aria-label="Discard"[^>]*data-fold-first|data-fold-first[^>]*aria-label="Discard"', row)
    script = Path(os.path.join(os.path.dirname(js.__file__), "editor_init.js")).read_text()
    assert "el.hasAttribute('data-fold-first')" in script


def test_a_shared_cover_is_a_preview_sized_copy_with_its_size(admin, client):
    # a 2560 px cover showed in no preview on WhatsApp: a wide upload is
    # shared as its 1600 px copy, and every one says its size
    import io
    from PIL import Image
    from soloblog import images
    buf = io.BytesIO()
    Image.new("RGB", (2400, 1500), (90, 120, 160)).save(buf, "PNG")
    big = images.save_upload(buf.getvalue(), "wide-share")
    buf = io.BytesIO()
    Image.new("RGB", (1200, 630), (90, 120, 160)).save(buf, "PNG")
    small = images.save_upload(buf.getvalue(), "card-share")
    wide = client.get(f"/post/{save_post(admin, title='Wide share', body='Words.', cover_image=big)}").text
    assert f'<meta property="og:image" content="{config.BASE_URL}{big}?w=1600">' in wide
    assert '<meta property="og:image:width" content="1600">' in wide
    assert '<meta property="og:image:height" content="1000">' in wide
    card = client.get(f"/post/{save_post(admin, title='Card share', body='Words.', cover_image=small)}").text
    assert f'<meta property="og:image" content="{config.BASE_URL}{small}">' in card
    assert '<meta property="og:image:width" content="1200">' in card
    assert client.get(f"{big}?w=1600").status_code == 200


def test_pages_are_made_16_at_once_and_the_health_check_never_waits(client):
    # 40 threads (the default) took 32 requests at once to 510 MB, past what a
    # 512 MB server leaves the app; 16 kept it near 330 MB at the same pages a
    # second (tools/measure.py). The health check is async, so a busy minute
    # isn't taken for a site that's down
    import inspect
    import anyio.to_thread
    from starlette.testclient import TestClient
    from soloblog import app as app_module
    from soloblog.routes import public
    assert app_module.PAGE_THREADS == 16
    # started as a server starts, the limit read from inside it
    with TestClient(app_module.app) as running:
        limit = running.portal.call(lambda: anyio.to_thread.current_default_thread_limiter().total_tokens)
        assert limit == 16
        assert running.get("/healthz").json()["status"] == "ok"
    assert "async def healthz():" in inspect.getsource(public)


def test_scripts_reach_the_page_without_their_comments(client):
    # the comments are for whoever works on a script, not every visitor's
    # page source - strings, regular expressions and divisions stay as written
    from soloblog.js import strip_comments
    src = """// a whole-line comment
var url = 'https://example.com'; // after code
var re = /^```gallery\\b/, half = total / 2 / 3; /* a block */
if (/\\/\\/x/.test(s)) x = "a // b /* c */"; // done
var cls = [/[/*]/, 'it\\'s'];
"""
    out = strip_comments(src)
    assert "comment" not in out and "after code" not in out and "a block" not in out and "done" not in out
    assert "'https://example.com'" in out and "/^```gallery\\b/" in out and "total / 2 / 3" in out
    assert '"a // b /* c */"' in out and "/\\/\\/x/" in out and "[/[/*]/, 'it\\'s']" in out
    app_js = client.get("/app.js").text
    assert not [line for line in app_js.split("\n") if line.strip().startswith(("//", "/*"))]
    page = client.get("/").text
    for script in re.findall(r"<script\b[^>]*>(.*?)</script>", page, re.S):
        assert "// a returning visitor" not in script and not re.search(r"^\s*//", script, re.M)


def test_post_settings_say_what_each_default_is(admin):
    # a choice that follows the site says what the site's is, value first;
    # what the site shows is tagged under Show; a new post's switches say
    # how they start
    from soloblog import pages
    before = {k: settings.get(k) for k in ("toc_style", "side_author", "side_author_where", "post_shows")}
    settings.set_many({"toc_style": "top", "side_author": "right", "side_author_where": "roll,posts",
                       "post_shows": "breadcrumbs,tags"})
    try:
        html = admin.get(f"/admin/edit/{save_post(admin, title='Defaults', body='Words.')}").text
        assert '<option value="">At the top (default)</option>' in html
        assert '<option value="">On the right (default)</option>' in html
        assert '<option value="">Medium (default)</option>' in html
        show = html.split('name="extras"')
        # (the tag carries data-default-tag now, so a Custom one can take its place)
        tagged = [label for label in pages.EXTRAS.values()
                  if re.search(rf'>{re.escape(label)}</span><span data-default-tag class="badge', html)]
        assert set(tagged) == {"Breadcrumbs", "Tags"}, (tagged, len(show))
        # a switch has no "On/Off by default" label: its bar and Reset say
        # it differs, and Reset's tooltip what the default is
        assert "by default</span>" not in html
    finally:
        settings.set_many(before)


def test_the_lightbox_shows_a_storys_pictures_once():
    """A story draws each picture twice - its step's copy (a phone's, kept
    for screen readers alone once the story is live: 1px, clipped, the
    picture inside it still full size) and the one held beside the words.
    Next from the first picture on a page went through both. Only what
    shows, and each picture once (checked in a browser on the sample
    blog's tour: 8 pictures, 5 in the lightbox)."""
    js = Path("soloblog/js/lightbox.js").read_text(encoding="utf-8")
    assert "function _lbClipped(img)" in js and "r.width <= 1 || r.height <= 1" in js
    assert "seen[img.src] && img !== trigger" in js


def test_every_admin_page_keeps_the_same_column(admin):
    """Lists and forms share one width - the editor's writing column - so
    nothing jumps sideways going from one admin page to the next."""
    column = re.compile(r'class="[^"]*(max-w-\S+) mx-auto lg:mx-0')
    for path in ("/admin/posts", "/admin/posts?status=pinned", "/admin/media", "/admin/comments",
                 "/admin/messages", "/admin/members", "/admin/newsletter",
                 "/admin/settings", "/admin/stats", "/admin/health"):
        found = column.search(admin.get(path).text)
        assert found and found.group(1) == "max-w-3xl", path


def test_a_posts_settings_are_one_list_passed_by_name():
    """A post's settings are listed once, in posts.PostFields, and carried
    as that one object - forty values in a row, and two swapped would save
    one setting as another without a word. A caller that still names them
    goes by name only, and a name that isn't a setting is refused."""
    import inspect
    import pytest
    from soloblog import posts
    assert list(posts.WRITABLE) == [f.name for f in posts.fields(posts.PostFields)]
    for fn, positional in ((posts.save_post, 9), (posts._write_file, 2), (posts._save, 3)):
        kinds = [p.kind for p in inspect.signature(fn).parameters.values()]
        assert kinds.count(inspect.Parameter.POSITIONAL_OR_KEYWORD) == positional, fn.__name__
        assert inspect.Parameter.KEYWORD_ONLY in kinds, fn.__name__
    with pytest.raises(TypeError):
        posts.save_post("never-saved", "T", "A", "Words.", "", "", True, False, no_such_setting="x")
    assert not posts.get_post("never-saved")
    # a choice that isn't one becomes the site's own; a place that isn't one, the menu
    f = posts.PostFields(title="  T ", body="a\r\nb", toc_style="sideways", pin_location="attic",
                         link_url="javascript:alert(1)", series_order=None, slides="no").cleaned()
    assert (f.title, f.body, f.toc_style, f.pin_location, f.link_url, f.series_order, f.slides) == \
        ("T", "a\nb", "", "header", "", 0, 0)


def test_a_drop_menu_is_as_wide_as_its_longest_item():
    """No drop menu sets a width of its own: it fits its longest item, and
    scrolls up and down when it's too tall. Three aren't menus of that kind:
    the phone's navigation drawer, and two with a field to fill in - a
    picker you type in (it would jump as the list narrows) and the writing
    session's own goal."""
    from soloblog import ui
    fixed = re.compile(r"(?<![\w:-])w-(\d+|\[|full|screen)")
    kept = ("nav-mobile-menu", "[&:popover-open]:flex flex-col rounded-box", "panel.className")
    for path in glob.glob("soloblog/**/*.py", recursive=True) + glob.glob("soloblog/js/*.js"):
        lines = Path(path).read_text(encoding="utf-8").splitlines()
        for n, line in enumerate(lines):
            if "dropdown-content" not in line:
                continue
            near = " ".join(lines[max(0, n - 1):n + 2])
            if any(k in near for k in kept):
                continue
            assert not fixed.search(near.split("dropdown-content", 1)[1]), f"{path}:{n + 1}"
    for cls in (ui.ROW_MENU_CLS, ui.MORE_MENU_CLS):
        assert "w-max" in cls and "min-w-40" not in cls
    # a block's buttons were measured side by side: three times too wide
    assert "sm:[&:popover-open]:flex sm:flex-col" in ui.MORE_MENU_CLS


def test_a_buttons_menu_opens_toward_the_room_it_has():
    """The header's menus ended under their button, opening leftwards, even
    in the middle of a wide window. With room beside the button a menu
    starts at it; at the window's edge it still ends under it. A row's ⋯
    menu always ends under its button."""
    from soloblog.app import POPOVER_DROPDOWN_JS as js
    place = js[js.index("var atEnd"):js.index("el.style.top")]
    assert "el.matches('[data-row-menu], [data-more-menu]') ||" in place
    assert "el.classList.contains('dropdown-end') && r.left + el.offsetWidth + 8 > window.innerWidth" in place
    # measured at its own width, not the one left from the last time it opened
    assert js.index("el.style.maxWidth = '';") < js.index("var atEnd")
