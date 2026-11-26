"""The page's own settings - Title, Page width, Show as slides, In the wiki,
Remind me to update, Link to (posts.py, pages.py): stored, kept in the
post's file, read back from it, cleaned, carried by the API and Micropub -
and what each does on the page, on any page."""
from pathlib import Path
import itertools
import os
import re
from datetime import timedelta
from html import unescape
from html.parser import HTMLParser

import pytest
from conftest import save_post
from starlette.testclient import TestClient

from soloblog import apikeys
from soloblog import config
from soloblog import pages
from soloblog import post_templates
from soloblog import posts
from soloblog import sections
from soloblog import settings
from soloblog import ui
from soloblog.db import get_db
from soloblog.posts import utcnow

DECK = "# One\n\n---\n\n## Two\n\n- A point\n\n---\n\n## Three\n\nWords."


class _Slides(HTMLParser):
    """Which element holds each slide - they all must hold the same one."""

    def __init__(self):
        super().__init__()
        self.stack, self.parents = [], []

    def handle_starttag(self, tag, attrs):
        if tag in ("hr", "img", "br", "input", "meta", "link"):
            return
        cls = dict(attrs).get("class") or ""
        if "slide carousel-item" in cls:
            self.parents.append(id(self.stack[-1]) if self.stack else 0)
        self.stack.append(object())

    def handle_endtag(self, tag):
        if self.stack and tag not in ("hr", "img", "br", "input", "meta", "link"):
            self.stack.pop()


def _slide_parents(page) -> list:
    parser = _Slides()
    parser.feed(page)
    return parser.parents


def _front(slug) -> dict:
    return posts._parse_file(posts._path(slug))[0]


def _make(title, body="Words.", **fields) -> str:
    """A live post through posts.write, the one way in every save takes."""
    return posts.write(None, "Tester", title=title, body=body, published=True, **fields)


def _reindexed(slug):
    """The row as the file alone gives it back (a backup, a moved site)."""
    get_db().execute("DELETE FROM posts WHERE slug=?", (slug,))
    get_db().commit()
    posts.resync_from_file(slug)
    return posts.get_post(slug)


# ---- stored, kept in the file, read back, cleaned

def test_the_settings_are_stored_kept_in_the_file_and_read_back():
    slug = _make("Every setting", title_style="centre", page_width="wide", slides=True, in_wiki=True,
                 remind_update=True, link_url="https://example.com/essay")
    row = posts.get_post(slug)
    assert (row["title_style"], row["page_width"], row["slides"], row["in_wiki"], row["remind_update"],
            row["link_url"]) == ("centre", "wide", 1, 1, 1, "https://example.com/essay")
    front = _front(slug)
    assert front["title_style"] == "centre" and front["page_width"] == "wide" and front["slides"] is True
    assert front["wiki"] is True and front["remind_update"] is True and front["link"] == "https://example.com/essay"
    back = _reindexed(slug)
    assert (back["title_style"], back["page_width"], back["slides"], back["in_wiki"], back["remind_update"],
            back["link_url"]) == ("centre", "wide", 1, 1, 1, "https://example.com/essay")
    # a draft copy keeps them
    copy = posts.get_post(posts.duplicate_post(slug))
    assert (copy["title_style"], copy["page_width"], copy["slides"], copy["in_wiki"], copy["remind_update"],
            copy["link_url"]) == ("centre", "wide", 1, 1, 1, "https://example.com/essay")
    # and so does a change to something else
    posts.write(slug, "Tester", summary="Changed")
    assert posts.get_post(slug)["in_wiki"] == 1 and _front(slug)["wiki"] is True


def test_a_page_without_them_writes_none_of_them():
    slug = _make("Plain page")
    row = posts.get_post(slug)
    assert (row["title_style"], row["page_width"], row["slides"], row["in_wiki"], row["remind_update"],
            row["link_url"]) == ("", "", 0, 0, 0, "")
    assert not {"title_style", "page_width", "slides", "wiki", "remind_update", "link"} & set(_front(slug))
    # switched off again, they leave the file
    on = _make("Switched on and off", in_wiki=True, slides=True)
    posts.write(on, "Tester", in_wiki=False, slides=False)
    assert not {"wiki", "slides"} & set(_front(on))


def test_what_a_hand_edited_file_says_is_cleaned():
    slug = _make("Odd file")
    path = posts._path(slug)
    text = Path(path).read_text(encoding="utf-8")
    odd = ("title_style: sideways\npage_width: 5\nslides: yes please\nwiki: 'no'\nremind_update: [1]\n"
           "link: javascript:alert(1)\n")
    Path(path).write_text(text.replace("\n---\n", "\n" + odd + "---\n", 1), encoding="utf-8")
    row = _reindexed(slug)
    assert (row["title_style"], row["page_width"], row["slides"], row["in_wiki"], row["remind_update"],
            row["link_url"]) == ("", "", 0, 0, 0, "")
    # the ways of saying yes
    for said, want in (("true", 1), ("yes", 1), ("'on'", 1), ("1", 1), ("false", 0), ("'false'", 0), ("0", 0),
                       ("2", 0), ("''", 0)):
        Path(path).write_text(text.replace("\n---\n", f"\nwiki: {said}\n---\n", 1), encoding="utf-8")
        assert _reindexed(slug)["in_wiki"] == want, said
    # a long address is clipped, whatever is in the file
    Path(path).write_text(
        text.replace("\n---\n", "\nlink: https://example.com/" + "a" * 5000 + "\n---\n", 1), encoding="utf-8")
    assert 0 < len(_reindexed(slug)["link_url"]) <= posts.MAX_LINK


def test_what_write_is_given_is_cleaned():
    slug = _make("Odd values", title_style="Sideways", page_width="huge", slides="yes please", in_wiki="false",
                 remind_update=7, link_url="javascript:alert(1)")
    row = posts.get_post(slug)
    assert (row["title_style"], row["page_width"], row["slides"], row["in_wiki"], row["remind_update"],
            row["link_url"]) == ("", "", 0, 0, 0, "")
    for bad in ("javascript:alert(1)", "data:text/html,hi", "//evil.example/", "/a b", "ftp://example.com/x"):
        posts.write(slug, "Tester", link_url=bad)
        assert posts.get_post(slug)["link_url"] == "", bad
    posts.write(slug, "Tester", link_url="/contact", title_style="HIDDEN", page_width=" Wide ", slides="true")
    row = posts.get_post(slug)
    assert (row["link_url"], row["title_style"], row["page_width"], row["slides"]) == ("/contact", "hidden", "wide", 1)
    posts.write(slug, "Tester", link_url="https://example.com/" + "a" * 5000)
    assert len(posts.get_post(slug)["link_url"]) <= posts.MAX_LINK


def test_the_columns_are_added_with_their_defaults():
    cols = {r["name"]: r for r in get_db().execute("PRAGMA table_info(posts)")}
    for name, default in (("title_style", "''"), ("page_width", "''"), ("slides", "0"), ("in_wiki", "0"),
                          ("remind_update", "0")):
        assert cols[name]["notnull"] == 1 and cols[name]["dflt_value"] == default, name


def test_templates_say_which_settings_they_switch_on():
    off = {"title_style": "", "page_width": "", "slides": False, "in_wiki": False, "remind_update": False,
           "link_url": ""}
    for key in post_templates.BUILT_IN:
        got = post_templates.get(key)["settings"]
        assert {k: got[k] for k in off} == {**off, **{k: v for k, v in post_templates.SETTINGS.get(key, {}).items()
                                                      if k in off}}, key
    assert post_templates.get("wiki")["settings"]["in_wiki"] is True
    assert post_templates.get("now")["settings"]["remind_update"] is True
    assert post_templates.get("slides")["settings"]["slides"] is True
    for key in ("profile", "landing"):
        assert post_templates.get(key)["settings"]["title_style"] == "hidden", key
    for key in ("landing", "project"):
        assert post_templates.get(key)["settings"]["page_width"] == "wide", key
    assert post_templates.get("recipe")["settings"]["page_width"] == ""
    assert "nownownow.com" in post_templates.get("now")["body"]
    # one of your own: off unless it kept them
    post_templates.save("My plain one", "", "Words.")
    mine = next(k for k, name, *_ in post_templates.choices() if name == "My plain one")
    assert {k: post_templates.settings_of(post_templates.get(mine))[k] for k in off} == off


# ---- the API and Micropub

def _as(app, key):
    c = TestClient(app, follow_redirects=False)
    c.headers["Authorization"] = f"Bearer {key}"
    return c


@pytest.fixture
def key():
    made = apikeys.create("page settings", "publish")
    yield made
    get_db().execute("DELETE FROM api_keys")
    get_db().execute("DELETE FROM rate_hits WHERE bucket IN ('api', 'api-fail')")
    get_db().commit()


def test_the_api_reads_and_writes_them(app, key):
    c = _as(app, key)
    r = c.post("/api/v1/posts", json={"title": "Through the API", "title_style": "centre", "page_width": "wide",
                                      "slides": True, "in_wiki": True, "remind_update": True,
                                      "link_url": "https://example.com/essay"})
    assert r.status_code == 201, r.text
    post = r.json()
    for name, value in (("title_style", "centre"), ("page_width", "wide"), ("slides", True), ("in_wiki", True),
                        ("remind_update", True), ("link_url", "https://example.com/essay")):
        assert post[name] == value, name
    assert _front(post["slug"])["wiki"] is True
    again = c.get(f"/api/v1/posts/{post['slug']}").json()
    assert again["in_wiki"] is True and again["link_url"] == "https://example.com/essay"
    # only what's sent changes
    r = c.patch(f"/api/v1/posts/{post['slug']}", json={"in_wiki": False}).json()
    assert r["in_wiki"] is False and r["slides"] is True and r["title_style"] == "centre"
    r = c.patch(f"/api/v1/posts/{post['slug']}", json={"title_style": "", "link_url": ""}).json()
    assert r["title_style"] == "" and r["link_url"] == ""
    # a plain post says so
    assert c.post("/api/v1/posts", json={"title": "Plain through the API"}).json()["in_wiki"] is False


def test_the_api_refuses_what_isnt_one_of_them(app, key):
    c = _as(app, key)
    for body in ({"title_style": "sideways"}, {"title_style": 3}, {"page_width": "huge"}, {"slides": "yes please"},
                 {"in_wiki": 1}, {"remind_update": "true"}, {"link_url": "javascript:alert(1)"},
                 {"link_url": "//evil.example/"}, {"link_url": ["https://example.com"]},
                 {"link_url": "x" * 5000}):
        r = c.post("/api/v1/posts", json={"title": "Refused", **body})
        assert r.status_code == 400, body
    assert not any(p["title"] == "Refused" for p in posts.list_posts(include_drafts=True))


# ---- In the wiki

def test_a_note_in_the_wiki_on_any_page(admin, client):
    other = _make("A plain post about nothing", "Words.")
    note = _make("Sourdough starter note", "See [[A plain post about nothing]].", in_wiki=True)
    # on the wiki's front page, not in the blog; the archive still has it
    wiki = client.get("/wiki").text
    assert f'href="/post/{note}"' in wiki and f'href="/post/{other}"' not in wiki
    home = client.get("/").text
    assert f'href="/post/{note}"' not in home and f'href="/post/{other}"' in home
    assert f'/post/{note}"' in client.get("/archive").text
    # the note: when it was edited, what it links to, a way back to the wiki
    page = client.get(f"/post/{note}").text
    assert "Last updated" in page and "Links from here" in page and "All wiki pages" in page
    assert f'href="/post/{other}"' in page.split("Links from here")[1]
    assert f'"name": "Wiki", "item": "{config.BASE_URL}/wiki"' in page
    # what it links to lists it, though it isn't in the wiki itself
    assert "Last updated" not in client.get(f"/post/{other}").text
    # the link picker offers the Wiki page once there are notes
    assert any(url == "/wiki" for _, url, _ in ui.builtin_pages(settings.get_all()))


def test_the_wiki_without_notes_says_so(admin, client):
    db = get_db()
    held = [r["slug"] for r in db.execute("SELECT slug FROM posts WHERE in_wiki=1")]
    db.execute("UPDATE posts SET in_wiki=0")
    db.commit()
    try:
        assert "No wiki pages yet." in client.get("/wiki").text
        assert "In the wiki" not in client.get("/wiki").text
        assert "switch on In the wiki" in admin.get("/wiki").text
        assert not any(url == "/wiki" for _, url, _ in ui.builtin_pages(settings.get_all()))
    finally:
        for slug in held:
            db.execute("UPDATE posts SET in_wiki=1 WHERE slug=?", (slug,))
        db.commit()


# ---- Remind me to update

def test_remind_me_to_update_on_a_standard_post(admin, client):
    slug = _make("Not a now page")
    assert "Last updated" not in client.get(f"/post/{slug}").text
    posts.write(slug, "Tester", remind_update=True)
    page = client.get(f"/post/{slug}").text
    assert "Last updated" in page and "alert-info" in page
    # nothing about nownownow.com: it isn't necessarily a now page
    assert "nownownow.com" not in page and "A now page" not in page
    # only the admin is nudged, and only after three months
    assert "time for an update" not in admin.get(f"/post/{slug}").text
    old = (utcnow() - timedelta(days=120)).isoformat()
    get_db().execute("UPDATE posts SET updated_at=? WHERE slug=?", (old, slug))
    get_db().commit()
    assert "Last updated 120 days ago" in admin.get(f"/post/{slug}").text
    assert "time for an update" not in client.get(f"/post/{slug}").text


# ---- Link to

def test_link_to_on_a_standard_post(admin, client):
    slug = _make("Worth reading", "Why it matters.", link_url="https://example.com/essay")
    page = client.get(f"/post/{slug}").text
    assert '<a href="https://example.com/essay" target="_blank" rel="noopener" class="link link-hover">Worth reading' in page
    assert "Read it on example.com" in page
    item = next(i for i in client.get("/feed.json").json()["items"] if i["url"].endswith(f"/post/{slug}"))
    assert item["external_url"] == "https://example.com/essay"
    assert "<link>https://example.com/essay</link>" in client.get("/rss").text
    # the same on a post made of sections
    recipe = _make("A recipe with a link", sections.markdown("recipe_facts") + "\n\nWords.", link_url="https://example.com/r")
    assert "Read it on example.com" in client.get(f"/post/{recipe}").text
    # a page on this site: the same tab, no outside icon
    local = _make("Goes to contact", "Words.", link_url="/contact")
    page = client.get(f"/post/{local}").text
    # no linked title and no button - the words alone
    assert "Read it on" not in page.split("Goes to contact", 1)[1]
    assert 'class="link link-hover">Goes' not in page and 'href="/contact" class="btn btn-sm btn-primary"' not in page and "Words." in page


def test_a_pinned_page_with_a_link_is_a_menu_item(client):
    slug = _make("Our shop", "", link_url="https://shop.example.com/", pinned=False)
    posts.write(slug, "Tester", pin_location="header")
    home = client.get("/").text
    assert 'href="https://shop.example.com/" target="_blank" rel="noopener"' in home
    here = _make("Our contact page", "", link_url="/contact", pinned=False)
    posts.write(here, "Tester", pin_location="header")
    assert re.search(r'<a href="/contact"[^>]*>Our contact page</a>', client.get("/").text)


def test_a_page_with_a_link_and_no_words_forwards(admin, client):
    slug = _make("Forwards on", "", link_url="https://example.com/elsewhere")
    r = client.get(f"/post/{slug}")
    assert r.status_code == 302 and r.headers["location"] == "https://example.com/elsewhere"
    # the admin still sees it, to edit; and with words of its own it stays
    assert admin.get(f"/post/{slug}").status_code == 200
    posts.write(slug, "Tester", body="Some words of its own.")
    assert client.get(f"/post/{slug}").status_code == 200


# ---- Show as slides

def test_a_deck_fills_the_screen_on_a_standard_post(admin, client):
    slug = _make("A talk", DECK, slides=True)
    before = settings.get("heading_fold")
    try:
        # headings that fold or carry links never cut a slide in two
        settings.set_many({"heading_fold": "open"})
        page = client.get(f"/post/{slug}").text
    finally:
        settings.set_many({"heading_fold": before})
    assert page.count('class="slide carousel-item') == 3 and "1 / 3" in page
    assert len(set(_slide_parents(page))) == 1 and "<details" not in page
    # the whole screen: no header, footer or side panels around it
    assert "data-site-header" not in page and "<footer" not in page and "Skip to content" not in page
    assert 'id="reading-progress"' not in page and 'data-side-panel' not in page
    assert "h-dvh" in page
    # a link home, named for what it does, and Esc goes there (slides.js)
    exit_link = re.search(r'<a href="/" [^>]*data-slides-exit[^>]*>.*?</a>', page, re.S)
    assert exit_link and "Back to the site" in exit_link.group(0)
    js = Path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "soloblog", "js", "slides.js")).read_text(encoding="utf-8")
    assert "'Escape'" in js and "document.fullscreenElement" in js and "data-slides-exit" in js
    # the buttons, count and Full screen stay
    assert 'aria-label="Previous slide"' in page and 'aria-label="Next slide"' in page and "Full screen" in page
    # the admin gets the same deck
    assert admin.get(f"/post/{slug}").text.count('class="slide carousel-item') == 3


def test_under_two_slides_is_a_page(client):
    slug = _make("A talk of one", "Just one slide.", slides=True)
    page = client.get(f"/post/{slug}").text
    assert 'class="slide carousel-item' not in page and "data-site-header" in page and "Just one slide." in page
    assert "data-slides-exit" not in page


def test_a_deck_cut_short_for_a_visitor_stays_a_page(admin, client):
    before = settings.get("members_enabled")
    body = "One\n\n---\n\nTwo\n\n<!-- members only from here -->\n\nThree\n\n---\n\nFour"
    slug = _make("A members talk", body, slides=True, visibility="members")
    try:
        settings.set_many({"members_enabled": "1"})
        page = client.get(f"/post/{slug}").text
        assert "This post is for members" in page and "data-site-header" in page
        assert 'class="slide carousel-item' not in page and "Three" not in page
        assert admin.get(f"/post/{slug}").text.count('class="slide carousel-item') == 3
    finally:
        settings.set_many({"members_enabled": before})


# ---- Title

def test_the_title_left_centred_or_hidden(client):
    plain = _make("Left title post", "Words.")
    centre = _make("Centred title post", "Words.", title_style="centre")
    hidden = _make("Hidden title post", "Words.", title_style="hidden")
    page = client.get(f"/post/{plain}").text
    assert re.search(r'<h1 class="text-3xl[^"]*">Left title post</h1>', page) and "text-center" not in page.split("<h1")[1][:200]
    assert "min read" in page
    page = client.get(f"/post/{centre}").text
    assert re.search(r'<h1 class="text-3xl[^"]*text-center">Centred title post</h1>', page)
    # and what's under it, centred too
    assert 'min read' in page and re.search(r'text-sm text-base-content/60 mb-5 text-center', page)
    # hidden: still in the page for screen readers and search engines - and the byline with it
    page = client.get(f"/post/{hidden}").text
    assert '<h1 class="sr-only">Hidden title post</h1>' in page and "min read" not in page
    assert '"headline": "Hidden title post"' in page or "Hidden title post" in page.split("</head>")[0]


def test_a_title_that_links_is_centred_and_hidden_too(client):
    centre = _make("Centred link", "Words.", title_style="centre", link_url="https://example.com/x")
    assert re.search(r'<h1 class="[^"]*text-center">\s*<a href="https://example.com/x"', client.get(f"/post/{centre}").text)
    hidden = _make("Hidden link", "Words.", title_style="hidden", link_url="https://example.com/x")
    assert re.search(r'<h1 class="sr-only">\s*<a href="https://example.com/x"', client.get(f"/post/{hidden}").text)


# ---- Page width, and which setting wins

def test_a_wide_standard_post(client):
    wide = _make("A wide standard post", "Some writing.\n\n## Tiles\n\nSection: Numbers\n\n### 3\nthings\n",
                 page_width="wide", tags="otters")
    plain = _make("A column standard post", "Some writing.\n\n## Tiles\n\nSection: Numbers\n\n### 3\nthings\n")
    page = unescape(client.get(f"/post/{wide}").text)
    assert "max-w-[81rem]" in page and "max-w-[81rem]" not in client.get(f"/post/{plain}").text
    # the writing stays at the site's width; a section, with no Width: of its own, runs wide
    assert "[&>:not([data-section],:has([data-section]))]:max-w-3xl" in page
    # its heading goes wide with it
    assert "w-screen" in page.split('data-section="numbers"')[0].rsplit("Some writing.", 1)[1]
    assert "[&>:not([data-section]" not in unescape(client.get(f"/post/{plain}").text)
    # the title, byline and comments keep the reading column
    assert "max-w-3xl mx-auto w-full" in page
    # the site's narrower column is the writing's column
    before = settings.get("body_width")
    try:
        settings.set_many({"body_width": "narrow"})
        assert "[&>:not([data-section],:has([data-section]))]:max-w-2xl" in unescape(client.get(f"/post/{wide}").text)
    finally:
        settings.set_many({"body_width": before})


def test_a_sections_own_width_beats_the_pages(client):
    body = ("Intro.\n\n## Narrow one\n\nSection: Numbers\nWidth: Column\n\n### 3\nthings\n\n"
            "## Full one\n\nSection: Numbers\nWidth: Full\n\n### 4\nmore\n\n"
            "## Default one\n\nSection: Numbers\n\n### 5\nmost\n")
    wide = unescape(client.get(f"/post/{_make('Widths in order', body, page_width='wide')}").text)
    parts = wide.split('data-section="numbers"')
    assert len(parts) == 4
    # Column: no breakout; Full: edge to edge; none: wide, as the page is -
    # each breakout opening before its section's heading
    assert "w-screen" not in parts[0].split("Intro.")[1]
    assert "w-screen mx-[calc(50%-50vw)]" in parts[1] and "max-w-[79rem]" not in parts[1]
    assert "max-w-[79rem]" in parts[2]
    # on a column page, a section without Width: stays in the column
    column = unescape(client.get(f"/post/{_make('Widths on a column', body)}").text).split('data-section="numbers"')
    assert "w-screen" not in column[0].split("Intro.")[1] and "w-screen" not in column[2]


def test_the_page_beats_the_site_for_section_space(client):
    before = settings.get("section_space")
    try:
        settings.set_many({"section_space": "small"})
        own = _make("Its own space", "Words.", section_space="large")
        follows = _make("Follows the site", "Words.")
        assert "[--space:1.5]" in client.get(f"/post/{own}").text
        assert "[--space:0.5]" in client.get(f"/post/{follows}").text
        row = posts.get_post(own)
        assert pages.section_space(row, settings.get_all()) == "large"
        assert pages.section_space(posts.get_post(follows), settings.get_all()) == "small"
    finally:
        settings.set_many({"section_space": before})


# ---- Sections appear and a section's Space and Appear: page, then section

def test_a_pages_own_sections_appear_is_stored_kept_in_the_file_and_read_back():
    slug = _make("Rises", section_motion="rise")
    assert posts.get_post(slug)["section_motion"] == "rise" and _front(slug)["motion"] == "rise"
    assert _reindexed(slug)["section_motion"] == "rise"
    assert posts.get_post(posts.duplicate_post(slug))["section_motion"] == "rise"
    # a change to something else keeps it, and none at all writes nothing
    posts.write(slug, "Tester", summary="Changed")
    assert posts.get_post(slug)["section_motion"] == "rise"
    posts.write(slug, "Tester", section_motion="")
    assert posts.get_post(slug)["section_motion"] == "" and "motion" not in _front(slug)
    assert "motion" not in _front(_make("Follows the site"))
    cols = {r["name"]: r for r in get_db().execute("PRAGMA table_info(posts)")}
    assert cols["section_motion"]["notnull"] == 1 and cols["section_motion"]["dflt_value"] == "''"


def test_a_pages_sections_appear_is_cleaned():
    slug = _make("Odd motion", section_motion="Spin")
    assert posts.get_post(slug)["section_motion"] == ""
    for bad in ("<script>", "rise,zoom", "x" * 5000, "../fade", "none!"):
        posts.write(slug, "Tester", section_motion=bad)
        assert posts.get_post(slug)["section_motion"] == "", bad
    posts.write(slug, "Tester", section_motion=" Slide-Right ")
    assert posts.get_post(slug)["section_motion"] == "slide-right"
    path = posts._path(slug)
    text = re.sub(r"\nmotion: .*", "", Path(path).read_text(encoding="utf-8"))
    for said, want in (("tilt", "tilt"), ("spin", ""), ("[rise]", ""), ("1", ""), ("''", "")):
        Path(path).write_text(text.replace("\n---\n", f"\nmotion: {said}\n---\n", 1), encoding="utf-8")
        assert _reindexed(slug)["section_motion"] == want, said


def test_a_saved_template_and_the_route_carry_the_pages_sections_appear(admin):
    before = settings.get("post_templates")
    try:
        for name, motion in (("Rising", "zoom"), ("Junk", "<b>")):
            admin.post("/admin/templates/save", data={"template_name": name, "body": "Words.", "section_motion": motion},
                       headers={"hx-request": "true"})
        mine = {t["name"]: t for t in post_templates.saved()}
        assert mine["Rising"]["settings"]["section_motion"] == "zoom" and mine["Junk"]["settings"]["section_motion"] == ""
        assert admin.get(f"/admin/template/mine-{mine['Rising']['id']}").json()["settings"]["section_motion"] == "zoom"
        assert post_templates.NO_SETTINGS["section_motion"] == ""
        # the built-in ones leave it to the site
        assert {post_templates.get(k)["settings"]["section_motion"] for k in post_templates.BUILT_IN} == {""}
    finally:
        settings.set_many({"post_templates": before})


_TWO = ("Intro.\n\n## First\n\nSection: Features\n{first}\n\n### A\n\nWords.\n\n"
        "## Second\n\nSection: Features\n{second}\n\n### B\n\nWords.\n\n## Plain\n\nEnd.")


_WRAPPED = itertools.count(1)


def _wrappers(client, first="", second="", **fields):
    """The opening tags of the two sections' wrappers, as drawn."""
    body = _TWO.format(first=first, second=second)
    page = unescape(client.get(f"/post/{_make(f'Wrapped {next(_WRAPPED)}', body, **fields)}").text)
    found = re.findall(r'<div class="[^"]*" data-section="features"[^>]*>', page)
    # the lines are the section's own - never shown, whatever they say
    drawn = page[page.index('data-section="features"'):page.index('id="plain"')]
    assert len(found) == 2 and "Space:" not in drawn and "Appear:" not in drawn
    return found


def test_a_sections_space_beats_the_pages_which_beats_the_sites(client):
    before = settings.get("section_space")
    try:
        settings.set_many({"section_space": "small"})
        # no line: the page's --space does it, from the site's or its own - nothing on the section
        assert "[--space:" not in _wrappers(client)[0]
        assert "[--space:" not in _wrappers(client, section_space="large")[0]
        # its own, whatever the page and site say
        small, medium = _wrappers(client, "Space: Small", "Space: Medium", section_space="large")
        assert "[--space:0.5]" in small and "[--space:1]" in medium
        assert "[--space:1.5]" in _wrappers(client, "Space: LARGE")[0]
        # Default, a missing line and junk follow the page
        for line in ("Space: Default", "Space: Huge", "Space: DEFAULT"):
            assert "[--space:" not in _wrappers(client, line)[0], line
    finally:
        settings.set_many({"section_space": before})


def test_a_sections_space_goes_on_every_kind_of_section_and_its_heading(admin, client):
    body = ("## Big\n\nSection: Hero\nSpace: Large\n\nBig words.\n\n## Story\n\nSection: Story\nSpace: Small\n\n"
            "### One\n\nWords.\n\n## Wide\n\nSection: Features\nWidth: Wide\nSpace: Large\n\n### A\n\nWords.\n\n"
            "## Plain\n\nEnd.")
    page = unescape(client.get(f"/post/{save_post(admin, title='Space everywhere', body=body)}").text)
    wrapper = {kind: tag for tag, kind in re.findall(r'(<div class="[^"]*" data-section="(\w+)"[^>]*>)', page)}
    assert "[--space:1.5]" in wrapper["hero"] and "[--space:0.5]" in wrapper["story"]
    assert "[--space:1.5]" in wrapper["features"]
    # a section that leaves its heading to the page has its room above it too, over the page's own rule
    assert pages.SECTION_GAPS["large"] in re.search(r'<h2[^>]*id="wide"', page).group(0)
    assert "section-gap" not in re.search(r'<h2[^>]*id="plain"', page).group(0)


def test_a_sections_appear_beats_the_pages_which_beats_the_sites(client):
    before = settings.get("section_motion")
    try:
        settings.set_many({"section_motion": "zoom"})
        first, second = _wrappers(client, "", "Appear: Rise")
        assert 'data-reveal="zoom"' in first and 'data-reveal="rise"' in second
        first, second = _wrappers(client, "", "Appear: Rise", section_motion="tilt")
        assert 'data-reveal="tilt"' in first and 'data-reveal="rise"' in second
        # every value, by its label
        for key, label in pages.SECTION_MOTIONS.items():
            want = "slide" if key == "alternate" else key
            assert f'data-reveal="{want}"' in _wrappers(client, f"Appear: {label}")[0], key
        # Default, a missing line and junk follow the page
        for line in ("Appear: Default", "Appear: Spin", "Appear: DEFAULT"):
            assert 'data-reveal="tilt"' in _wrappers(client, line, section_motion="tilt")[0], line
            assert 'data-reveal="zoom"' in _wrappers(client, line)[0], line
        assert "reveal-item" in _wrappers(client, "Appear: Rise")[0]
    finally:
        settings.set_many({"section_motion": before})


def test_sections_that_alternate_take_turns_from_each_side(client):
    one, two = _wrappers(client, section_motion="alternate")
    assert 'data-reveal="slide"' in one and 'data-reveal="slide-right"' in two
    one, two = _wrappers(client, "Appear: Slide both ways", "Appear: Default")
    assert 'data-reveal="slide"' in one and 'data-reveal="alternate"' not in two


def test_photos_come_in_one_by_one_so_the_section_holds_still(admin, client):
    import io
    from PIL import Image
    from soloblog import images
    buf = io.BytesIO()
    Image.new("RGB", (900, 600), (60, 90, 140)).save(buf, "PNG")
    pic = images.save_upload(buf.getvalue(), "appearing.png")
    body = f"## Work\n\nSection: Portfolio\nAppear: Rise\n\n### One\n\n![One]({pic})\n\n## After\n\nEnd."
    page = client.get(f"/post/{save_post(admin, title='Photos appear', body=body)}").text
    tag = re.search(r'<div class="[^"]*" data-section="portfolio"[^>]*>', page).group(0)
    assert 'data-reveal="rise"' in tag and "reveal-item" not in tag and 'class="group reveal-item"' in page


def test_nothing_moves_without_animations_or_for_a_reader_who_wants_less(client):
    from soloblog import js
    css = Path("static/css/input.css").read_text(encoding="utf-8")
    rule = css[css.index("[custom-css: section-reveal]"):css.index("@keyframes reveal-rise")]
    # hidden and played only with Animations on (html[data-animate]) and no "reduce motion"
    assert "@media (prefers-reduced-motion: no-preference)" in rule and rule.count("html[data-animate]") == 2
    script = js.read("motion.js")
    assert "!document.documentElement.hasAttribute('data-animate')" in script and "prefers-reduced-motion: reduce" in script
    assert "if (still() || !window.IntersectionObserver) return;" in script
    # "None" has nothing to wait for
    assert "getPropertyValue('--reveal').trim() === 'none'" in script
    # a section's own value never turns Animations on
    before = settings.get("page_animations")
    try:
        settings.set_many({"page_animations": "0"})
        page = client.get(f"/post/{_make('Still', _TWO.format(first='Appear: Zoom', second=''))}").text
        assert "data-animate" not in page.split("<body")[0]
    finally:
        settings.set_many({"page_animations": before})


def test_what_hides_a_section_until_it_appears_is_only_for_those_who_allow_motion():
    # the one rule that hides a section waits inside the no-preference query, so
    # "reduce motion" (or no script, which never sets js-reveal) shows everything
    css = Path("static/css/input.css").read_text(encoding="utf-8")
    hiding = [m.start() for m in re.finditer(r"\.reveal-item:not\(\[data-revealed\]\)", css)]
    assert len(hiding) == 1
    before = css[:hiding[0]]
    start = before.rindex("@media")
    assert before[start:].startswith("@media (prefers-reduced-motion: no-preference)")
    assert before[start:].count("{") - before[start:].count("}") == 1  # still inside that block
    assert "js-reveal" in css[hiding[0] - 40:hiding[0]]
