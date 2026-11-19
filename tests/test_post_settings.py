"""Post settings > Page: Title, Page width, the folded More group, and the
bar and Reset that mark what a page sets differently from the site."""
import re

import pytest

from conftest import save_post
from soloblog import pages, post_templates, posts, sections, settings


def _block(html, name):
    """The fieldset around the field called name."""
    return re.search(rf'<fieldset[^>]*>(?:(?!</fieldset>).)*?name="{name}"(?:(?!</fieldset>).)*</fieldset>',
                     html, re.S).group(0)


def _shown(html_part, what):
    """Whether the element carrying data-<what> is visible (no hidden class)."""
    tag = re.search(rf'<(?:span|button)\b[^>]*\bdata-{what}\b[^>]*>', html_part)
    assert tag, f"no {what} in {html_part[:200]}"
    return "hidden" not in re.search(r'class="([^"]*)"', tag.group(0)).group(1).split()


def _changed(html_part):
    """Whether the setting's fieldset carries the changed bar (data-changed)."""
    return "data-changed" in re.match(r"<fieldset[^>]*>", html_part.lstrip()).group(0)


def _panel(html, key):
    return re.search(rf'<details[^>]*data-panel="{key}"[^>]*>.*?</summary>', html, re.S).group(0)


def _count(html, key="page"):
    text = re.sub(r"<[^>]+>", "", re.search(r"<summary[^>]*>(.*?)</summary>", _panel(html, key), re.S).group(1))
    return " ".join(text.split())


def _more(html):
    return re.search(r'<details[^>]*id="page-more"[^>]*>', html).group(0)


def _editor(admin, slug=None):
    return admin.get(f"/admin/edit/{slug}" if slug else "/admin/new").text


@pytest.fixture
def site_settings():
    """Changes site settings for one test, and puts them back."""
    before = {}

    def change(**values):
        before.update({k: settings.get(k) for k in values if k not in before})
        settings.set_many(values)
    yield change
    settings.set_many(before)


@pytest.fixture(autouse=True)
def plain_site(site_settings):
    """The site as it starts, whatever an earlier test left."""
    site_settings(**{k: settings.DEFAULTS[k] for k in ("toc_style", "heading_fold", "cover_width", "section_space",
                                                       "section_motion", "post_shows", "comments_enabled")},
                  side_tags="off", side_archive="off", side_author="off", side_tags_where="", side_archive_where="",
                  side_author_where="")


def test_the_page_panel_has_the_new_settings_with_their_defaults(admin):
    html = _editor(admin)
    assert _count(html) == "Page" and "Layout" not in _panel(html, "page")
    assert 'name="layout"' not in html
    assert re.search(r'<select name="title_style".*?<option value="" selected>Left \(default\)</option>'
                     r'<option value="centre">Centred</option><option value="hidden">Hidden</option>', html, re.S)
    assert re.search(r'<select name="page_width"[^>]*>.*?<option value="" selected>Column \(default\)</option>'
                     r'<option value="wide">Wide</option>', html, re.S)
    # in the order the plan has: title, width, then the rest, Show, and More last
    assert html.index('name="title_style"') < html.index('name="page_width"') \
        < html.index('name="toc_style"') < html.index('name="extras"') < html.index('id="page-more"')
    more = html[html.index('id="page-more"'):html.index('data-panel="template"')]
    for name in ("slides", "in_wiki", "remind_update", "link_url"):
        assert f'name="{name}"' in more
        assert f'name="{name}"' not in html[:html.index('id="page-more"')]
    for label in ("Show as slides", "In the wiki", "Remind me to update", "Link to"):
        assert label in more
    # nothing set: folded, and no count in the heading
    assert " open" not in _more(html)


@pytest.mark.parametrize("setting", ["slides", "in_wiki", "remind_update", "link_url"])
def test_more_opens_by_itself_when_one_is_set(admin, setting):
    value = "https://example.com/essay" if setting == "link_url" else "1"
    slug = save_post(admin, title=f"More {setting}", **{setting: value})
    assert " open" in _more(_editor(admin, slug))
    plain = save_post(admin, title=f"Plain {setting}")
    assert " open" not in _more(_editor(admin, plain))


def test_link_to_shows_on_every_post(admin):
    for kind, body in (("plain", "Words."), ("recipe", sections.markdown("recipe_facts")), ("slides", "One\n\n---\n\nTwo")):
        slug = save_post(admin, title=f"Link on {kind}", body=body)
        html = _editor(admin, slug)
        assert 'name="link_url"' in html and "link-url-field" not in html


def test_the_new_settings_round_trip_through_save(admin):
    slug = save_post(admin, title="All the page settings", title_style="centre", page_width="wide", slides="1",
                     in_wiki="1", remind_update="1", link_url="https://example.com/essay")
    row = posts.get_post(slug)
    assert (row["title_style"], row["page_width"], row["slides"], row["in_wiki"], row["remind_update"]) \
        == ("centre", "wide", 1, 1, 1)
    html = _editor(admin, slug)
    assert re.search(r'<option value="centre" selected>', _block(html, "title_style"))
    assert re.search(r'<option value="wide" selected>', _block(html, "page_width"))
    for name in ("slides", "in_wiki", "remind_update"):
        assert re.search(rf'<input type="checkbox" name="{name}" value="1" checked', html)
    assert 'name="link_url" value="https://example.com/essay"' in html
    # unticked and put back to the defaults
    save_post(admin, slug=slug, title="All the page settings", title_style="", page_width="")
    row = posts.get_post(slug)
    assert (row["title_style"], row["page_width"], row["slides"], row["in_wiki"], row["remind_update"]) \
        == ("", "", 0, 0, 0)


def test_bad_values_are_cleaned(admin):
    slug = save_post(admin, title="Bad page settings", title_style="<script>", page_width="huge")
    row = posts.get_post(slug)
    assert row["title_style"] == "" and row["page_width"] == ""
    # a form that doesn't send the choices keeps them
    slug = save_post(admin, title="Kept page settings", title_style="hidden", page_width="wide")
    posts.write(slug, summary="a line")
    assert posts.get_post(slug)["title_style"] == "hidden" and posts.get_post(slug)["page_width"] == "wide"
    post = {"title": "Kept page settings", "body": "Hello.", "slug": slug, "published": "1", "comments_enabled": "1"}
    admin.post("/admin/save", data=post, headers={"hx-request": "true"})
    assert posts.get_post(slug)["title_style"] == "hidden"


def test_a_fresh_post_has_nothing_changed(admin):
    for html in (_editor(admin), _editor(admin, save_post(admin, title="Nothing changed here"))):
        assert " changed" not in _count(html) and " changed" not in _count(html, "publishing")
        assert not re.search(r"<fieldset[^>]*data-changed", html)
        for part in re.findall(r'<[a-z]+ [^>]*data-custom-reset[^>]*>', html):
            assert "hidden" in re.search(r'class="([^"]*)"', part).group(1).split(), part


@pytest.mark.parametrize("name,value,site", [
    ("toc_style", "off", "right"), ("heading_fold", "folded", "open"), ("cover_width", "column", "screen"),
    ("section_space", "large", "medium"), ("section_motion", "rise", "fade"), ("page_width", "wide", ""),
])
def test_a_choice_that_differs_from_the_site_is_changed(admin, name, value, site):
    slug = save_post(admin, title=f"Own {name}", **{name: value})
    html = _editor(admin, slug)
    block = _block(html, name)
    assert f'data-site-value="{site}"' in block
    assert _changed(block) and _shown(block, "custom-reset")
    assert _count(html) == "Page · 1 changed"
    # the others aren't
    for other in ("toc_style", "heading_fold", "cover_width", "section_space", "section_motion", "page_width"):
        if other != name:
            assert not _changed(_block(html, other))


def test_sections_appear_is_in_the_page_panel_after_the_space_between_sections(admin, site_settings):
    html = _editor(admin)
    assert html.index('name="section_space"') < html.index('name="section_motion"') < html.index('name="sides_tags"')
    block = _block(html, "section_motion")
    assert "Sections appear" in block and '<option value="">Fade (default)</option>' in block
    assert all(f'value="{key}"' in block for key in pages.SECTION_MOTIONS)
    # it says what the site does, and follows it
    site_settings(section_motion="tilt")
    assert '<option value="">Tilt (default)</option>' in _block(_editor(admin), "section_motion")


def test_choosing_what_the_site_has_is_not_changed(admin):
    # it won't follow the site's later changes, but it isn't different now
    slug = save_post(admin, title="Same as the site", toc_style="right", section_space="medium",
                     section_motion="fade")
    html = _editor(admin, slug)
    assert not _changed(_block(html, "toc_style"))
    assert not _changed(_block(html, "section_space")) and _count(html) == "Page"
    assert not _changed(_block(html, "section_motion"))


def test_changed_follows_the_site_when_it_changes(admin, site_settings):
    slug = save_post(admin, title="Follows the site", toc_style="off")
    assert _changed(_block(_editor(admin, slug), "toc_style"))
    site_settings(toc_style="off")
    html = _editor(admin, slug)
    assert 'data-site-value="off"' in _block(html, "toc_style")
    assert not _changed(_block(html, "toc_style"))


def test_a_side_panel_place_that_differs_is_changed(admin, site_settings):
    site_settings(side_tags="off", side_tags_where="", side_archive="right", side_archive_where="posts")
    slug = save_post(admin, title="Own sides", sides_tags="left", sides_archive="right")
    html = _editor(admin, slug)
    assert 'data-site-value="off"' in _block(html, "sides_tags") and _changed(_block(html, "sides_tags"))
    # the site puts it on the right already
    assert 'data-site-value="right"' in _block(html, "sides_archive")
    assert not _changed(_block(html, "sides_archive"))
    assert _count(html) == "Page · 1 changed"


def test_show_ticks_that_differ_are_changed_one_by_one(admin):
    from soloblog import pages
    slug = save_post(admin, title="Own show", extras=["byline", "print"], extras_before="")
    assert posts.get_post(slug)["extras"]
    html = _editor(admin, slug)
    show = html[html.index('name="extras" value="breadcrumbs"') - 200:html.index('name="extras_before"')]
    ticks = {m.group(1): m.group(0) for m in re.finditer(
        r'<label data-default-field[^>]*>.*?name="extras" value="(\w+)".*?</label>', show, re.S)}
    assert set(ticks) == set(pages.EXTRAS)
    on_by_site = pages.default_extras(False)
    ticked = {"byline", "print"}
    for key, label in ticks.items():
        differs = (key in ticked) != (key in on_by_site)
        assert "data-changed" not in label, key  # the group has the bar, not a tick
        # Default stands in for a tick the site shows and this page does too
        if key in on_by_site:
            assert _shown(label, "default-tag") == (not differs), key
    # one Reset for the group, and Show counted once, however many ticks differ
    group = re.search(r'<legend class="fieldset-legend[^"]*">.{0,300}?Show.*?</legend>', html, re.S).group(0)
    assert _shown(group, "custom-reset")
    assert re.search(r'<fieldset[^>]*data-changed[^>]*><legend[^>]*>.{0,300}?Show', html, re.S)
    assert sum((k in ticked) != (k in on_by_site) for k in pages.EXTRAS) > 1
    assert _count(html) == "Page · 1 changed"


def test_show_follows_the_site_when_untouched(admin):
    slug = save_post(admin, title="Default show")
    html = _editor(admin, slug)
    assert " changed" not in _count(html)
    assert not any("data-changed" in m for m in re.findall(
        r'<label data-default-field[^>]*>.*?</label>', html, re.S) if 'name="extras"' in m)


def test_a_page_is_compared_with_what_the_site_shows_on_a_page(admin):
    from soloblog import pages
    slug = save_post(admin, title="An about page", pin_location="header")
    html = _editor(admin, slug)
    ticks = re.findall(r'<input type="checkbox" name="extras" value="(\w+)"( checked)? data-site-value="(\d)"', html)
    assert {k for k, _, site in ticks if site == "1"} == pages.default_extras(True)
    assert " changed" not in _count(html)


def test_comments_off_on_a_site_with_comments_is_changed(admin, site_settings):
    site_settings(comments_enabled="1")
    off = save_post(admin, title="Comments off here", comments_enabled="")
    html = _editor(admin, off)
    block = _block(html, "comments_enabled")
    assert 'data-site-value="1"' in block and _changed(block) and _shown(block, "custom-reset")
    assert _count(html, "publishing") == "Publishing · 1 changed"
    # one line: the words, Reset (an icon, saying what the default is), the
    # switch - Reset outside both labels, where pressing it can't turn it
    assert block.index("</label>") < block.index("data-custom-reset") < block.rindex("<label")
    assert 'data-tip="Reset to default (On)"' in block and ">Reset<" not in block
    on = save_post(admin, title="Comments on here")
    html = _editor(admin, on)
    assert not _changed(_block(html, "comments_enabled")) and _count(html, "publishing") == "Publishing"


def test_with_comments_off_for_the_site_nothing_is_changed(admin, site_settings):
    site_settings(comments_enabled="0")
    html = _editor(admin, save_post(admin, title="Site comments off", comments_enabled=""))
    block = _block(html, "comments_enabled")
    assert "data-custom" not in block and "data-site-value" not in block
    assert _count(html, "publishing") == "Publishing"


def test_a_new_post_starts_with_its_templates_page_settings(admin, monkeypatch):
    real = post_templates.get

    def get(key):
        start = real(key)
        return start and {**start, "settings": {**start["settings"], "title_style": "hidden", "page_width": "wide",
                                                "slides": True, "in_wiki": True, "remind_update": True,
                                                "link_url": "https://example.com/from-the-template"}}
    monkeypatch.setattr(post_templates, "get", get)
    html = admin.get("/admin/new?template=howto").text
    assert re.search(r'<option value="hidden" selected>', _block(html, "title_style"))
    assert re.search(r'<option value="wide" selected>', _block(html, "page_width"))
    # a how-to also starts with its contents at the top, which the site doesn't
    assert _changed(_block(html, "page_width")) and _changed(_block(html, "toc_style"))
    assert _count(html) == "Page · 2 changed"
    for name in ("slides", "in_wiki", "remind_update"):
        assert re.search(rf'<input type="checkbox" name="{name}" value="1" checked', html)
    assert 'value="https://example.com/from-the-template"' in html and " open" in _more(html)


def test_a_template_without_them_starts_with_the_defaults(admin):
    # a template from before these settings, or one that doesn't set them
    for key in ("", "howto", "recipe"):
        html = admin.get(f"/admin/new?template={key}").text
        assert re.search(r'<option value="" selected>Left', _block(html, "title_style"))
        assert " open" not in _more(html)


def test_the_script_is_on_the_editor_pages_and_in_order(admin):
    slug = save_post(admin, title="Script is here")
    for html in (_editor(admin), _editor(admin, slug)):
        # in the admin script: the settings pages use it too
        from soloblog import app as soloblog_app
        assert re.search(r"function updateCustomTags[\s\S]*function customReset", soloblog_app.ADMIN_JS)
        # wired through actions.on, never an inline handler
        assert 'data-onclick="customReset"' in html and "onclick=" not in html.replace("data-onclick=", "")


def test_a_cover_hidden_from_lists_that_show_covers_is_changed(admin, site_settings):
    site_settings(roll_shows="cover,date,summary")
    hidden = save_post(admin, title="Cover hidden here", hide_list_cover="1")
    html = _editor(admin, hidden)
    block = _block(html, "hide_list_cover")
    assert 'data-site-value="0"' in block and _changed(block) and _shown(block, "custom-reset")
    assert block.index("It still shows on the post") < block.index("data-custom-reset")
    assert _count(html, "details") == "Details · 1 changed"
    shown = _editor(admin, save_post(admin, title="Cover shown here"))
    assert not _changed(_block(shown, "hide_list_cover")) and " changed" not in _count(shown, "details")
    # lists that show no covers: hiding one changes nothing, so nothing is marked
    site_settings(roll_shows="date,summary")
    html = _editor(admin, hidden)
    assert "data-custom-reset" not in _block(html, "hide_list_cover") and " changed" not in _count(html, "details")


def test_a_post_hidden_from_search_engines_on_a_listed_site_is_changed(admin, site_settings):
    site_settings(search_noindex="0")
    hidden = save_post(admin, title="Hidden from search", post_noindex="1")
    html = _editor(admin, hidden)
    assert _changed(_block(html, "post_noindex")) and _count(html, "seo") == "Search engines · 1 changed"
    # a site that asks not to be listed at all: hiding one post changes nothing
    site_settings(search_noindex="1")
    html = _editor(admin, hidden)
    assert "data-custom-reset" not in _block(html, "post_noindex") and " changed" not in _count(html, "seo")


def test_a_word_goal_of_its_own_is_changed(admin, site_settings):
    import json
    from soloblog import posts
    site_settings(editor_goal_default="800", editor_progress="1")
    slug = save_post(admin, title="A longer one")
    site_settings(editor_goals=json.dumps({str(posts.get_post(slug)["id"]): 2000}))
    html = _editor(admin, slug)
    block = _block(html, "word_goal")
    assert 'data-site-value="800"' in block and _changed(block) and _shown(block, "custom-reset")
    assert _count(html, "details") == "Details · 1 changed"
    site_settings(editor_goals="{}")
    assert not _changed(_block(_editor(admin, slug), "word_goal"))


def test_a_post_held_back_from_subscribers_is_changed(admin, monkeypatch):
    """New posts go to subscribers by themselves; one that won't is changed."""
    from soloblog import newsletter
    slug = save_post(admin, title="Not for the newsletter")
    monkeypatch.setattr(newsletter, "sending", lambda s: True)
    monkeypatch.setattr(newsletter, "emailed", lambda slug: False)
    monkeypatch.setattr(newsletter, "skipped", lambda s: s == slug)
    html = _editor(admin, slug)
    block = _block(html, "newsletter_email")
    assert 'data-site-value="1"' in block and _changed(block)
    assert _count(html, "publishing").endswith("changed")
    monkeypatch.setattr(newsletter, "skipped", lambda s: False)
    assert not _changed(_block(_editor(admin, slug), "newsletter_email"))


def test_a_default_says_what_this_post_or_page_gets(admin):
    # the site's place for the contents and a side panel counts only where
    # Shows on has that kind - a page left out gets "Off (default)", and a
    # line saying where that's set
    keys = ("toc_style", "toc_style_where", "side_tags", "side_tags_where")
    before = {k: settings.get(k) for k in keys}
    settings.set_many({"toc_style": "right", "toc_style_where": "posts", "side_tags": "left",
                       "side_tags_where": "posts"})
    try:
        post = admin.get(f"/admin/edit/{save_post(admin, title='A post', body='Words.')}").text
        assert '<option value="">On the right (default)</option>' in post
        assert '<option value="">On the left (default)</option>' in post
        assert "Contents are off for posts." not in post
        page = admin.get(f"/admin/edit/{save_post(admin, title='A page', body='Words.', pin_location='header')}").text
        toc = _block(page, "toc_style")
        assert '<option value="">Off (default)</option>' in toc
        assert "Contents are off for pages." in toc and "tab=posts&amp;panel=posts-contents" in toc
        tags = _block(page, "sides_tags")
        assert '<option value="">Off (default)</option>' in tags
        assert "Off for pages." in tags and "tab=blog&amp;panel=blog-side" in tags
    finally:
        settings.set_many(before)


def test_what_the_site_turns_off_says_so_beside_it(admin):
    keys = ("comments_enabled", "support_kofi", "author_name", "author_bio", "newsletter_mode", "members_enabled",
            "reactions_style", "roll_shows")
    before = {k: settings.get(k) for k in keys}
    try:
        settings.set_many({"comments_enabled": "0", "support_kofi": "", "author_name": "", "author_bio": "",
                           "newsletter_mode": "", "members_enabled": "0", "reactions_style": "off",
                           "roll_shows": "title,date"})
        html = admin.get(f"/admin/edit/{save_post(admin, title='Quiet', body='Words.')}").text
        for line in ("Comments are off for the whole site.", "Support links need a link first.",
                     "About the author needs your name or bio.",
                     "Newsletter sign-up needs the newsletter set up.", "Likes are off for the whole site.",
                     "Post lists don't show covers."):
            assert line in html, line
        # each with a link straight to its setting
        assert "tab=messages&amp;panel=messages-comments" in html and "tab=posts&amp;panel=posts-reading" in html
        settings.set_many({"comments_enabled": "1", "author_name": "Sam", "reactions_style": "like",
                           "roll_shows": "title,cover"})
        html = admin.get(f"/admin/edit/{save_post(admin, title='Loud', body='Words.')}").text
        for line in ("Comments are off for the whole site.", "About the author needs your name or bio.",
                     "Likes are off for the whole site.", "Post lists don't show covers."):
            assert line not in html, line
    finally:
        settings.set_many(before)


def test_each_link_to_a_setting_is_still_there(admin):
    # the links beside what the site turns off open Settings at that setting,
    # as its search does
    from soloblog.routes import editor
    from soloblog.routes.admin_settings.pages import settings_index
    hrefs = {e["href"] for e in settings_index()}
    for name, panel in editor.SETTING_LINKS:
        assert editor._setting_href(name, panel) in hrefs, (name, panel)


def test_the_homepage_is_a_page_to_the_contents_shows_on(admin, client):
    # a post chosen as the homepage counts as a page for the contents and
    # the side panels, on the site and in its own settings
    keys = ("toc_style", "toc_style_where", "home_page")
    before = {k: settings.get(k) for k in keys}
    body = "## One\n\nWords.\n\n## Two\n\nWords.\n\n## Three\n\nWords.\n"
    slug = save_post(admin, title="Home", body=body)
    try:
        settings.set_many({"toc_style": "right", "toc_style_where": "posts", "home_page": slug})
        assert 'href="#three"' not in client.get("/").text
        toc = _block(admin.get(f"/admin/edit/{slug}").text, "toc_style")
        assert '<option value="">Off (default)</option>' in toc and "Contents are off for pages." in toc
        settings.set_many({"toc_style_where": "posts,pages"})
        assert 'href="#three"' in client.get("/").text
    finally:
        settings.set_many(before)


def test_no_dropdown_lists_a_choice_twice(admin):
    # the site's choice is the "(default)" entry, which follows the site;
    # listed again on its own it read as the same choice twice
    keys = ("toc_style", "heading_fold", "cover_width", "section_space", "side_tags", "side_tags_where")
    before = {k: settings.get(k) for k in keys}
    try:
        settings.set_many({"toc_style": "right", "heading_fold": "off", "cover_width": "screen",
                           "side_tags": "left", "side_tags_where": "posts,pages"})
        for fields in ({}, {"pin_location": "header"}, {"toc_style": "right", "heading_fold": "off"}):
            html = admin.get(f"/admin/edit/{save_post(admin, title='Twice', body='Words.', **fields)}").text
            # the ones that follow the site, with a "(default)" entry
            for select in [s for s in re.findall(r"<select\b.*?</select>", html, re.S) if "(default)" in s]:
                labels = [re.sub(r"\s*\(default\)$", "", label.strip())
                          for label in re.findall(r"<option\b[^>]*>(.*?)</option>", select, re.S)]
                assert len(labels) == len(set(labels)), labels
        # a post set to just what the site has shows it as the default, and keeps following it
        html = admin.get(f"/admin/edit/{save_post(admin, title='Same', body='Words.', toc_style='right')}").text
        toc = _block(html, "toc_style")
        assert '<option value="">On the right (default)</option>' in toc and '<option value="right"' not in toc
    finally:
        settings.set_many(before)
