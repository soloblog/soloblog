"""Home, Blog and the built-in pages are rows in the header's menu and the footer, among
their pinned pages: moved with them, added, renamed, taken out."""
from pathlib import Path
import re

import pytest
from conftest import save_post

from soloblog import config, posts, settings
from soloblog.db import get_db

NAV_KEYS = tuple(k for k in settings.DEFAULTS if k.startswith(("nav_", "foot_"))) + (
    "home_page", "site_language", "header_align", "links_enabled", "contact_enabled", "newsletter_mode",
    "footer_enabled", "footer_show_pages", "footer_show_browse", "footer_layout", "email_provider")
_made = []  # the pages a test made, taken away after it so the next test's menu is its own


@pytest.fixture(autouse=True)
def plain_menu():
    """The menu as an existing site has it: none of these set."""
    before = {k: settings.get(k) for k in NAV_KEYS}
    settings.set_many({k: settings.DEFAULTS[k] for k in NAV_KEYS})
    # other tests' wiki notes are not this test's wiki
    db = get_db()
    notes = [r["slug"] for r in db.execute("SELECT slug FROM posts WHERE in_wiki=1")]
    db.execute("UPDATE posts SET in_wiki=0")
    db.commit()
    yield
    settings.set_many(before)
    for slug in notes:
        db.execute("UPDATE posts SET in_wiki=1 WHERE slug=?", (slug,))
    db.commit()
    for slug in _made:
        posts.delete_post(slug)
    _made.clear()


def _pin(admin, title):
    slug = save_post(admin, title=title, pinned="1", pin_location="header")
    _made.append(slug)
    return slug


def _two_pages(admin):
    return _pin(admin, "Menu page one"), _pin(admin, "Menu page two")


def _home_page(admin):
    slug = save_post(admin, title="Menu home page")
    _made.append(slug)
    settings.set_many({"home_page": slug})
    return slug


def _row(html, marker):
    """One list row of the Pinned tab, from its marker to the next row."""
    start = html.index(marker)
    end = html.find('class="list-row', start + len(marker) + 30)
    return html[start:end if end > 0 else None]


def _menu(html, part="row"):
    """The words of the links in the header's row (or the phone's list), as a visitor reads them."""
    if part == "phone":
        start = html.index('id="nav-mobile-menu"')
        return re.findall(r"<a [^>]*>([^<]*)</a>", html[start:html.index("data-nav-menu", start)])
    start = html.index("data-nav-menu")
    return re.findall(r"<a [^>]*>([^<]*)</a>", html[start:html.index("<li data-nav-more", start)])


def _ours(labels, *pages):
    return [x for x in labels if x in ("Home", "Blog", *pages)]


def test_an_existing_site_has_the_menu_it_had(admin, client):
    _two_pages(admin)
    _home_page(admin)
    first = posts.list_pinned_tree()[0][0]["title"]
    html = client.get("/").text
    assert _menu(html)[:3] == ["Home", "Blog", first]
    assert _menu(html, "phone")[:3] == ["Home", "Blog", first]


def test_blog_is_in_the_menu_only_while_a_page_is_the_homepage(admin, client):
    assert "Blog" not in _menu(client.get("/").text)
    assert 'id="site-row-blog"' not in admin.get("/admin/posts?status=pinned").text
    _home_page(admin)
    assert "Blog" in _menu(client.get("/").text)
    assert 'id="site-row-blog"' in admin.get("/admin/posts?status=pinned").text


def test_the_pinned_tab_lists_home_and_blog_as_site_pages(admin):
    _two_pages(admin)
    html = admin.get("/admin/posts?status=pinned").text
    assert 'id="site-row-home"' in html and 'id="site-row-blog"' not in html
    assert html.count("Site page") == 1
    row = _row(html, 'id="site-row-home"')
    assert "Move down" in row and "Move up" not in row  # first
    assert "Rename" in row and "Hide from menu" in row
    assert "/admin/edit/" not in row and "Trash" not in row and "Nest under" not in row
    _home_page(admin)
    blog = _row(admin.get("/admin/posts?status=pinned").text, 'id="site-row-blog"')
    assert "Move up" in blog and "Move down" in blog and "Rename" in blog and "Hide from menu" not in blog


def test_a_page_cannot_nest_under_home_or_blog(admin):
    one, _ = _two_pages(admin)
    for _ in range(100):
        admin.post("/admin/pin/move", data={"slug": one, "direction": "up"})
    # first of the pages and right after Home: no page before it to nest under
    html = admin.get("/admin/posts?status=pinned").text
    assert "Nest under" not in _row(html, f'href="/admin/edit/{one}"')


def test_home_moves_after_a_page_and_back(admin, client):
    one, two = _two_pages(admin)
    titles = ["Menu page one", "Menu page two"]
    for _ in range(100):
        if _ours(_menu(client.get("/").text), *titles) == titles + ["Home"]:
            break
        admin.post("/admin/nav/move", data={"site": "home", "direction": "down"})
    else:
        pytest.fail("Home never got past the pages")
    # the pages' own order is unchanged by Home passing them
    assert posts.get_post(one)["pin_order"] < posts.get_post(two)["pin_order"]
    assert _ours(_menu(client.get("/").text, "phone"), *titles) == titles + ["Home"]
    admin.post("/admin/nav/move", data={"site": "home", "direction": "up"})
    assert _ours(_menu(client.get("/").text), *titles) == [titles[0], "Home", titles[1]]


def test_a_page_moves_before_home(admin, client):
    one, _ = _two_pages(admin)
    for _ in range(100):
        admin.post("/admin/pin/move", data={"slug": one, "direction": "up"})
    assert _ours(_menu(client.get("/").text), "Menu page one") == ["Menu page one", "Home"]
    # and its number reached its file, where a reindex reads it
    number = posts.get_post(one)["pin_order"]
    text = Path(config.POSTS_DIR, f"{one}.md").read_text()
    assert re.search(rf"^pin_order: {number}$", text, re.M) or number == 0


def test_moving_past_home_keeps_the_pages_in_their_order(admin):
    _two_pages(admin)
    before = [p["slug"] for p, _ in posts.list_pinned_tree(drafts=True)]
    admin.post("/admin/nav/move", data={"site": "home", "direction": "down"})
    admin.post("/admin/nav/move", data={"site": "home", "direction": "up"})
    assert [p["slug"] for p, _ in posts.list_pinned_tree(drafts=True)] == before


def test_moving_at_the_ends_and_with_junk_does_nothing(admin):
    _two_pages(admin)
    for data in ({"site": "home", "direction": "up"}, {"site": "nope", "direction": "down"},
                 {"site": "home", "direction": "sideways"}, {"site": "", "direction": ""}):
        assert admin.post("/admin/nav/move", data=data).status_code == 303
    assert settings.get("nav_home_order") == ""
    assert admin.post("/admin/pin/move", data={"slug": "no-such-page", "direction": "up"}).status_code == 303


def test_a_page_called_home_is_not_the_home_row(admin):
    page = _pin(admin, "Home")
    _pin(admin, "Other room")
    admin.post("/admin/nav/move", data={"site": "home", "direction": "down"})
    assert settings.get("nav_home_order") != ""
    assert posts.get_post(page)["pin_order"] > 0


def test_rename_shows_in_the_header_and_empty_goes_back(admin, client):
    _home_page(admin)
    r = admin.post("/admin/nav/rename", data={"site": "blog", "label": "  Writing  "})
    assert r.status_code == 303 and "Writing" in r.headers["location"]
    assert _menu(client.get("/").text)[:2] == ["Home", "Writing"]
    assert _menu(client.get("/").text, "phone")[:2] == ["Home", "Writing"]
    assert 'value="Writing"' in admin.get("/admin/posts?status=pinned").text
    admin.post("/admin/nav/rename", data={"site": "blog", "label": "   "})
    assert settings.get("nav_blog_label") == ""
    assert _menu(client.get("/").text)[:2] == ["Home", "Blog"]


def test_the_default_word_is_translated_and_a_custom_one_is_not(admin, client):
    settings.set_many({"site_language": "de"})
    assert _menu(client.get("/").text)[0] == "Startseite"
    admin.post("/admin/nav/rename", data={"site": "home", "label": "Start"})
    assert _menu(client.get("/").text)[0] == "Start"
    admin.post("/admin/nav/rename", data={"site": "home", "label": ""})
    assert _menu(client.get("/").text)[0] == "Startseite"


def test_a_label_is_text_and_has_a_limit(admin, client):
    admin.post("/admin/nav/rename", data={"site": "home", "label": '<script>alert(1)</script><img src=x onerror=alert(2)>'})
    for html in (client.get("/").text, admin.get("/admin/posts?status=pinned").text):
        assert "<script>alert(1)" not in html and "<img src=x onerror" not in html
        assert "&lt;script&gt;" in html
    admin.post("/admin/nav/rename", data={"site": "home", "label": "x" * 500})
    assert settings.get("nav_home_label") == "x" * 40
    admin.post("/admin/nav/rename", data={"site": "home", "label": "two\n\nlines\there"})
    assert settings.get("nav_home_label") == "two lines here"


def test_hiding_home_takes_it_out_of_every_copy_of_the_menu(admin, client):
    _two_pages(admin)
    html = client.get("/").text
    assert "Home" in _menu(html) and "Home" in _menu(html, "phone")
    assert admin.post("/admin/nav/hide", data={"hidden": "1"}).status_code == 303
    html = client.get("/").text
    assert "Home" not in _menu(html) and "Home" not in _menu(html, "phone")
    assert 'href="/"' in html  # the site's name still goes home
    row = _row(admin.get("/admin/posts?status=pinned").text, 'id="site-row-home"')
    assert "Hidden" in row and "Show in menu" in row and "Hide from menu" not in row
    admin.post("/admin/nav/hide", data={"hidden": ""})
    assert "Home" in _menu(client.get("/").text)


def test_the_stacked_header_follows_the_same_order_and_hiding(admin, client):
    _two_pages(admin)
    settings.set_many({"header_align": "stacked", "nav_home_hidden": "1"})
    labels = _menu(client.get("/").text)
    assert "Home" not in labels and "Menu page one" in labels


def test_the_routes_need_the_admin(client):
    for url, data in (("/admin/nav/move", {"site": "home", "direction": "down"}),
                      ("/admin/nav/rename", {"site": "home", "label": "Start"}),
                      ("/admin/nav/hide", {"hidden": "1"})):
        r = client.post(url, data=data)
        assert r.status_code in (303, 401) and "login" in r.headers.get("location", "login")
    assert settings.get("nav_home_label") == "" and settings.get("nav_home_hidden") == ""
    assert settings.get("nav_home_order") == ""


# the built-in pages, in the header's menu and the footer

def _wiki_note(admin):
    slug = save_post(admin, title="Menu wiki note", in_wiki="1")
    _made.append(slug)
    return slug


def _add(admin, site, where="header"):
    return admin.post("/admin/nav/add", data={"site": site, "where": where})


def _failed(response):
    return "toast_type=error" in response.headers["location"]


def _footer(html):
    """The words of the links in the footer, its pages and its small print, as a visitor reads them."""
    return re.findall(r"<a [^>]*>([^<]*)</a>", html.split("<footer")[1])


def _groups(admin):
    """The Pinned tab's header group and its footer group."""
    html = admin.get("/admin/posts?status=pinned").text
    return html[html.index(">Header<"):html.index(">Footer<")], html[html.index(">Footer<"):]


def _offers(group):
    return re.findall(r'name="site" value="(\w+)"', group[:group.find("<ul class=\"list\"")] if '<ul class="list"' in group else group)


def test_a_site_without_the_new_settings_has_the_menu_it_had(admin, client):
    html = client.get("/").text
    assert _menu(html)[0] == "Home"
    own = {page["title"] for page, _ in posts.list_pinned_tree()}  # other tests' pages
    for word in ("Archive", "Tags", "Search", "Wiki", "Links", "Contact", "Newsletter", "RSS feed"):
        assert word in own or word not in _menu(html)
    pinned = admin.get("/admin/posts?status=pinned").text
    assert 'id="site-row-archive"' not in pinned and 'id="site-row-foot-archive"' not in pinned
    # the footer's own small print is as it was
    assert {"Archive", "Tags", "RSS"} <= set(_footer(html))


def test_the_add_button_lists_what_applies_with_what_each_is(admin):
    header, footer = _groups(admin)
    assert "Add to menu" in header and "Every post, by month" in header and "Search the site" in header
    assert _offers(header) == ["archive", "tags", "search", "rss"]
    # Home and Blog are in the header already; Blog only matters once a page is the homepage
    assert _offers(footer) == ["home", "archive", "tags", "search", "rss"] and "Add to footer" in footer
    _wiki_note(admin)
    settings.set_many({"links_enabled": "1", "contact_enabled": "1", "email_provider": "smtp", "newsletter_mode": "builtin"})
    _home_page(admin)
    header, footer = _groups(admin)
    assert _offers(header) == ["archive", "tags", "search", "wiki", "links", "contact", "newsletter", "rss"]
    assert _offers(footer)[:2] == ["home", "blog"]


def test_nothing_left_to_add_means_no_button(admin):
    for site in ("archive", "tags", "search", "rss"):
        _add(admin, site)
    header, _ = _groups(admin)
    assert "Add to menu" not in header


def test_the_wiki_is_not_offered_when_it_is_the_homepage(admin):
    _wiki_note(admin)
    settings.set_many({"home_page": posts.WIKI_HOME})
    header, _ = _groups(admin)
    assert "wiki" not in _offers(header)
    assert _failed(_add(admin, "wiki")) and settings.get("nav_wiki_on") == ""


def test_adding_a_page_puts_it_last_as_a_site_page_row(admin, client):
    _two_pages(admin)
    for site in ("archive", "tags", "search"):
        assert not _failed(_add(admin, site))
    assert _menu(client.get("/").text)[-3:] == ["Archive", "Tags", "Search"]
    assert _menu(client.get("/").text, "phone")[-3:] == ["Archive", "Tags", "Search"]
    html = admin.get("/admin/posts?status=pinned").text
    assert html.count("Site page") == 4
    row = _row(html, 'id="site-row-archive"')
    assert "Move up" in row and "Rename" in row and "Remove from menu" in row
    assert "/admin/edit/" not in row and "Trash" not in row and "Nest under" not in row and "Hide from menu" not in row
    # added already: not offered again
    assert _offers(_groups(admin)[0]) == ["rss"]
    # a page pinned afterwards joins the end, behind them
    late = _pin(admin, "Pinned afterwards")
    assert _menu(client.get("/").text)[-1] == "Pinned afterwards"
    assert posts.get_post(late)["pin_order"] > int(settings.get("nav_search_order"))


def test_each_page_that_applies_can_be_added(admin, client):
    _wiki_note(admin)
    settings.set_many({"links_enabled": "1", "contact_enabled": "1", "email_provider": "smtp", "newsletter_mode": "builtin"})
    for site in ("archive", "tags", "search", "wiki", "links", "contact", "newsletter", "rss"):
        assert not _failed(_add(admin, site)), site
    assert _menu(client.get("/").text)[-8:] == ["Archive", "Tags", "Search", "Wiki", "Links", "Contact", "Newsletter", "RSS feed"]
    html = client.get("/").text
    for href in ("/archive", "/tags", "/search", "/wiki", "/links", "/contact", "/newsletter", "/rss"):
        assert f'href="{href}"' in html


def test_a_page_that_does_not_apply_cannot_be_added(admin):
    for site in ("wiki", "links", "contact", "newsletter"):
        for where in ("header", "footer"):
            assert _failed(_add(admin, site, where)), (site, where)
    assert settings.get("nav_wiki_on") == "" and settings.get("foot_links_on") == ""
    # a draft is no wiki to a visitor
    _made.append(save_post(admin, title="Menu draft wiki note", in_wiki="1", published=""))
    assert _failed(_add(admin, "wiki"))


def test_a_page_that_stops_applying_leaves_the_menu_and_says_so(admin, client):
    note = _wiki_note(admin)
    settings.set_many({"links_enabled": "1"})
    _add(admin, "wiki")
    _add(admin, "links")
    assert _menu(client.get("/").text)[-2:] == ["Wiki", "Links"]
    settings.set_many({"links_enabled": ""})
    assert "Links" not in _menu(client.get("/").text) and "Links" not in _menu(client.get("/").text, "phone")
    row = _row(admin.get("/admin/posts?status=pinned").text, 'id="site-row-links"')
    assert "Link in bio is off" in row and "opacity-60" in row
    posts.delete_post(note)
    _made.remove(note)
    assert "Wiki" not in _menu(client.get("/").text)
    assert "No wiki notes yet" in _row(admin.get("/admin/posts?status=pinned").text, 'id="site-row-wiki"')
    # the rows keep their places, and are back when the page applies again
    settings.set_many({"links_enabled": "1"})
    assert _menu(client.get("/").text)[-1] == "Links"
    _wiki_note(admin)
    assert _menu(client.get("/").text)[-2:] == ["Wiki", "Links"]


def test_added_pages_move_with_the_pages(admin, client):
    one, _ = _two_pages(admin)
    _add(admin, "archive")
    _add(admin, "tags")
    admin.post("/admin/nav/move", data={"site": "archive", "direction": "up"})
    assert _menu(client.get("/").text)[-3:] == ["Archive", "Menu page two", "Tags"]
    admin.post("/admin/nav/move", data={"site": "archive", "direction": "down"})
    admin.post("/admin/nav/move", data={"site": "archive", "direction": "down"})  # last already
    assert _menu(client.get("/").text)[-2:] == ["Tags", "Archive"]
    for _n in range(100):
        admin.post("/admin/nav/move", data={"site": "tags", "direction": "up"})
    assert _menu(client.get("/").text)[0] == "Tags"
    # a page's own buttons take it past them
    for _n in range(100):
        admin.post("/admin/pin/move", data={"slug": one, "direction": "down"})
    assert _menu(client.get("/").text)[-1] == "Menu page one"


def test_a_page_called_archive_is_not_the_archive_row(admin, client):
    base = _menu(client.get("/").text).count("Archive")
    _pin(admin, "Archive")
    _add(admin, "archive")
    admin.post("/admin/nav/move", data={"site": "archive", "direction": "up"})
    assert _menu(client.get("/").text).count("Archive") == base + 2


def test_rename_a_built_in_page_and_remove_it(admin, client):
    base = _menu(client.get("/").text).count("Archive")
    _add(admin, "archive")
    r = admin.post("/admin/nav/rename", data={"site": "archive", "label": "  Everything  "})
    assert r.status_code == 303 and "Everything" in r.headers["location"]
    assert _menu(client.get("/").text)[-1] == "Everything" and _menu(client.get("/").text, "phone")[-1] == "Everything"
    assert 'value="Everything"' in admin.get("/admin/posts?status=pinned").text
    admin.post("/admin/nav/rename", data={"site": "archive", "label": ""})
    assert _menu(client.get("/").text)[-1] == "Archive"
    admin.post("/admin/nav/rename", data={"site": "archive", "label": "Old words"})
    assert not _failed(admin.post("/admin/nav/remove", data={"site": "archive"}))
    assert _menu(client.get("/").text).count("Archive") == base
    assert [settings.get(f"nav_archive_{k}") for k in ("on", "order", "label")] == ["", "", ""]
    header, _ = _groups(admin)
    assert 'id="site-row-archive"' not in header and "archive" in _offers(header)
    _add(admin, "archive")
    assert _menu(client.get("/").text)[-1] == "Archive"


def test_the_default_word_of_an_added_page_is_translated_and_a_custom_one_is_not(admin, client):
    settings.set_many({"site_language": "de", "links_enabled": "1"})
    _add(admin, "archive")
    _add(admin, "links")
    assert _menu(client.get("/").text)[-2:] == ["Archiv", "Links"]
    admin.post("/admin/nav/rename", data={"site": "archive", "label": "Alles"})
    assert _menu(client.get("/").text)[-2] == "Alles"


def test_a_label_on_an_added_page_is_text_and_limited(admin, client):
    _add(admin, "tags")
    admin.post("/admin/nav/rename", data={"site": "tags", "label": "<script>alert(1)</script>" + "x" * 80})
    assert len(settings.get("nav_tags_label")) == 40
    for html in (client.get("/").text, admin.get("/admin/posts?status=pinned").text):
        assert "<script>alert(1)" not in html and "&lt;script&gt;" in html


def test_junk_for_the_menu_routes_never_crashes_or_changes_anything(admin):
    sites = ["", "nope", "../x", "😀", "x" * 300, "ARCHIVE", "archive\x00", "home", "blog"]
    for site in sites:
        for where in ("", "header", "footer", "sideways", "😀"):
            for action in ("add", "remove", "rename", "move"):
                r = admin.post(f"/admin/nav/{action}", data={"site": site, "where": where, "label": "x", "direction": "up"})
                assert r.status_code == 303, (action, site, where)
    # the junk touched nothing a real choice didn't: Home and Blog can't be added or removed
    assert settings.get("nav_home_on") == "" and settings.get("nav_blog_on") == "" and settings.get("nav_home_hidden") == ""
    assert not any(settings.get(f"{m}_{k}_on") for m in ("nav", "foot") for k in ("wiki", "links", "contact", "newsletter"))


def test_home_cannot_be_removed_from_the_header(admin, client):
    admin.post("/admin/nav/remove", data={"site": "home", "where": "header"})
    assert "Home" in _menu(client.get("/").text)
    row = _row(admin.get("/admin/posts?status=pinned").text, 'id="site-row-home"')
    assert "Remove from menu" not in row and "Hide from menu" in row


def test_the_footer_pages_are_the_footers_own(admin, client):
    base = _menu(client.get("/").text).count("Archive")
    assert not _failed(_add(admin, "archive", "footer"))
    assert settings.get("nav_archive_on") == "" and settings.get("foot_archive_on") == "1"
    assert _menu(client.get("/").text).count("Archive") == base
    # in the footer's pages once, and not again in the small print
    feet = _footer(client.get("/").text)
    assert feet.count("Archive") == 1 and "Tags" in feet and "RSS" in feet
    row = _row(admin.get("/admin/posts?status=pinned").text, 'id="site-row-foot-archive"')
    assert "Remove from footer" in row and "Rename" in row
    # also in the header, with its own place and words
    _add(admin, "archive", "header")
    admin.post("/admin/nav/rename", data={"site": "archive", "where": "footer", "label": "Everything"})
    assert _menu(client.get("/").text)[-1] == "Archive"
    feet = _footer(client.get("/").text)
    assert "Everything" in feet and "Archive" not in feet
    # out of the footer's pages, it is in the small print again
    admin.post("/admin/nav/remove", data={"site": "archive", "where": "footer"})
    assert _menu(client.get("/").text)[-1] == "Archive"
    feet = _footer(client.get("/").text)
    assert "Everything" not in feet and feet.count("Archive") == 1


def test_home_and_blog_can_be_added_to_the_footer(admin, client):
    assert "blog" not in _offers(_groups(admin)[1])
    assert _failed(_add(admin, "blog", "footer"))
    _add(admin, "home", "footer")
    assert "Home" in _footer(client.get("/").text)
    assert 'id="site-row-foot-home"' in admin.get("/admin/posts?status=pinned").text
    _home_page(admin)
    _add(admin, "blog", "footer")
    feet = _footer(client.get("/").text)
    assert feet.index("Home") + 1 == feet.index("Blog")
    # the header's own Home is not the footer's
    assert settings.get("nav_home_hidden") == "" and "Home" in _menu(client.get("/").text)
    admin.post("/admin/nav/remove", data={"site": "home", "where": "footer"})
    assert "Home" not in _footer(client.get("/").text)


def test_footer_rows_move_among_the_footer_pages(admin, client):
    one = save_post(admin, title="Footer page one", pinned="1", pin_location="footer")
    two = save_post(admin, title="Footer page two", pinned="1", pin_location="footer")
    _made.extend([one, two])
    settings.set_many({"contact_enabled": "1"})
    _add(admin, "contact", "footer")
    _add(admin, "archive", "footer")
    feet = _footer(client.get("/").text)
    assert feet.index("Footer page two") < feet.index("Contact") < feet.index("Archive")
    admin.post("/admin/nav/move", data={"site": "archive", "where": "footer", "direction": "up", "label": ""})
    feet = _footer(client.get("/").text)
    assert feet.index("Footer page two") < feet.index("Archive") < feet.index("Contact")
    # a page's own buttons take it past a site page
    for _n in range(100):
        admin.post("/admin/pin/move", data={"slug": one, "direction": "down"})
    feet = _footer(client.get("/").text)
    assert feet.index("Contact") < feet.index("Footer page one")
    # the header's order is separate
    assert settings.get("nav_archive_order") == "" and settings.get("foot_archive_order") != ""


def test_footer_site_rows_in_the_columns_layout_are_plain_links(admin, client):
    settings.set_many({"footer_layout": "columns"})
    _add(admin, "archive", "footer")
    help_slug = save_post(admin, title="Help centre", pinned="1", pin_location="footer")
    faq = save_post(admin, title="Questions", pinned="1", pin_location="footer", parent_slug=help_slug)
    _made.extend([faq, help_slug])
    footer = client.get("/").text.split("<footer")[1]
    assert "sm:grid-cols-[repeat(auto-fit,minmax(9rem,1fr))]" in footer
    assert footer.index("Archive") < footer.index("Help centre") < footer.index("Questions")
    assert "font-semibold" not in footer[footer.index("Archive") - 250:footer.index("Archive")]
    assert _footer(client.get("/").text).count("Archive") == 1


def test_footer_rows_follow_whether_the_footer_shows_its_pages(admin, client):
    settings.set_many({"contact_enabled": "1"})
    _add(admin, "contact", "footer")
    assert "Contact" in _footer(client.get("/").text)
    settings.set_many({"footer_show_pages": ""})
    assert "Contact" not in _footer(client.get("/").text)
    assert "pinned pages are off in the footer" in admin.get("/admin/posts?status=pinned").text
    # and the small print keeps its own links, as it always did
    assert {"Archive", "Tags", "RSS"} <= set(_footer(client.get("/").text))
    settings.set_many({"footer_show_pages": "1", "footer_enabled": ""})
    assert "the footer is off" in admin.get("/admin/posts?status=pinned").text


def test_the_small_print_leaves_out_what_the_footer_pages_already_link_to(admin, client):
    settings.set_many({"email_provider": "smtp", "newsletter_mode": "builtin"})
    assert {"Archive", "Tags", "RSS", "Newsletter"} <= set(_footer(client.get("/").text))
    for site, plain in (("tags", "Tags"), ("rss", "RSS"), ("newsletter", "Newsletter")):
        _add(admin, site, "footer")
        feet = _footer(client.get("/").text)
        assert feet.count(plain) == 0 if site == "rss" else feet.count(plain) == 1, (site, feet)
        assert "RSS feed" in feet if site == "rss" else True
    # one the footer's pages don't have is still there
    assert "Archive" in _footer(client.get("/").text)
    # with the small print's own links off, the pages row is all there is
    settings.set_many({"footer_show_browse": ""})
    assert "Archive" not in _footer(client.get("/").text)


def test_the_new_routes_need_the_admin(client):
    for url, data in (("/admin/nav/add", {"site": "archive", "where": "header"}),
                      ("/admin/nav/add", {"site": "archive", "where": "footer"}),
                      ("/admin/nav/remove", {"site": "archive", "where": "header"}),
                      ("/admin/nav/rename", {"site": "archive", "label": "x"})):
        r = client.post(url, data=data)
        assert r.status_code in (303, 401) and "login" in r.headers.get("location", "login")
    assert settings.get("nav_archive_on") == "" and settings.get("foot_archive_on") == ""
    assert settings.get("nav_archive_label") == ""


def test_the_link_picker_and_the_menu_share_one_list():
    from soloblog.ui.pickers import builtin_pages
    settings.set_many({"contact_enabled": "1"})
    s = settings.get_all()
    names = {title for title, _, _ in builtin_pages(s)}
    assert {"Home", "Archive", "Tags", "Search", "Contact", "RSS feed"} <= names
    assert not {"Wiki", "Links", "Newsletter"} & names
    assert [url for _, url, _ in builtin_pages(s)] == [posts.SITE_PAGES[k][0] for k in posts.SITE_PAGES if not posts.site_note(s, k)]
