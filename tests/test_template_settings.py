"""A custom template keeps every Post setting - Save as a template stores
them, a new post and Apply a template start from them, an old one without
them still loads, and nothing odd that's sent or stored gets through."""
from pathlib import Path
import json
import re

import pytest

from soloblog import pages, post_templates, settings

ALL = {"title_style": "centre", "page_width": "wide", "cover_width": "full", "toc_style": "side",
       "heading_fold": "folded", "section_space": "large", "section_motion": "rise", "sides_tags": "left",
       "sides_archive": "off",
       "sides_author": "right", "slides": "1", "in_wiki": "1", "remind_update": "1",
       "link_url": "https://example.com/the-article"}
KEPT = {"title_style": "centre", "page_width": "wide", "cover_width": "full", "toc_style": "side",
        "heading_fold": "folded", "section_space": "large", "section_motion": "rise",
        "sides": "tags=left,archive=off,author=right",
        "extras": "byline,tags", "slides": True, "in_wiki": True, "remind_update": True,
        "link_url": "https://example.com/the-article"}


@pytest.fixture(autouse=True)
def plain_site():
    before = {k: settings.get(k) for k in ("post_templates", "post_shows", "new_post_start", "template_recent")}
    settings.set_many({"post_templates": "[]", "post_shows": settings.DEFAULTS["post_shows"], "new_post_start": "",
                       "template_recent": ""})
    yield
    settings.set_many(before)


def _save(admin, **fields):
    data = {"template_name": "Mine", "title": "A post", "body": "## One\n\nWords.", "extras_before": "",
            "extras_before_page": "", **fields}
    r = admin.post("/admin/templates/save", data=data, headers={"hx-request": "true"})
    assert r.status_code == 200 and "Saved" in r.text, r.text
    return post_templates.saved()[0]


def _select(html, name):
    """The value chosen in the select called name."""
    block = re.search(rf'<select[^>]*name="{name}".*?</select>', html, re.S).group(0)
    return re.search(r'<option value="([^"]*)" selected', block).group(1)


def _ticked(html):
    return {m.group(1) for m in re.finditer(r'<input type="checkbox" name="extras" value="([a-z]+)"[^>]*checked', html)}


def _on(html, name):
    return bool(re.search(rf'<input type="checkbox" name="{name}" value="1" checked', html))


def test_save_as_a_template_keeps_every_setting(admin):
    mine = _save(admin, **ALL, extras=["byline", "tags"])
    assert mine["settings"] == KEPT and "toc_style" not in mine
    got = post_templates.get(f"mine-{mine['id']}")
    assert post_templates.settings_of(got) == KEPT


def test_show_ticks_as_the_site_has_them_are_kept_as_following_the_site(admin):
    assert _save(admin, extras=sorted(pages.default_extras(False)))["settings"]["extras"] == ""
    # none ticked is none, not the site's
    assert _save(admin, template_name="None shown")["settings"]["extras"] == "none"
    # a page's fewer, as the site has them for a page
    assert _save(admin, template_name="A page", extras=["breadcrumbs", "progress", "series", "sides"],
                 pin_location="header", extras_before_page="1")["settings"]["extras"] == ""


def test_a_template_saved_from_a_form_without_settings_has_the_defaults(admin):
    r = admin.post("/admin/templates/save", data={"template_name": "Bare", "body": "Words."})
    assert "Saved" in r.text
    assert post_templates.settings_of(post_templates.saved()[0]) == {**post_templates.NO_SETTINGS}


def test_one_with_its_settings_at_the_top_loads_with_the_defaults(admin):
    old = {"id": "abc123", "name": "Old one", "layout": "docs", "tags": "a", "body": "Words.", "summary": "S",
           "cover": "", "toc_style": "right"}
    settings.set_many({"post_templates": json.dumps([old])})
    got = post_templates.get("mine-abc123")
    assert got["body"] == "Words." and post_templates.settings_of(got) == post_templates.NO_SETTINGS
    assert admin.get("/admin/template/mine-abc123").json()["settings"]["toc_style"] == ""
    assert admin.get("/admin/new?template=mine-abc123").status_code == 200


def test_the_template_route_gives_every_setting(admin):
    mine = _save(admin, **ALL, extras=["byline", "tags"])
    t = admin.get(f"/admin/template/mine-{mine['id']}").json()
    assert t["settings"] == KEPT
    assert set(admin.get("/admin/template/recipe").json()["settings"]) == set(post_templates.NO_SETTINGS)


def test_a_new_post_starts_with_every_setting(admin):
    mine = _save(admin, **ALL, extras=["byline", "tags"])
    html = admin.get(f"/admin/new?template=mine-{mine['id']}").text
    for name in ("title_style", "page_width", "cover_width", "toc_style", "heading_fold", "section_space",
                 "section_motion", "sides_tags", "sides_archive", "sides_author"):
        want = ALL.get(name)
        assert _select(html, name) == want, name
    assert _ticked(html) == {"byline", "tags"}
    for name in ("slides", "in_wiki", "remind_update"):
        assert _on(html, name), name
    assert 'value="https://example.com/the-article"' in html
    # the panel's heading counts what's set differently from the site
    assert re.search(r"Page · \d+ changed", re.sub(r"<[^>]+>", "", html))


def test_a_new_post_from_a_template_that_follows_the_site_shows_the_sites_ticks(admin):
    mine = _save(admin, extras=sorted(pages.default_extras(False)))
    html = admin.get(f"/admin/new?template=mine-{mine['id']}").text
    assert _ticked(html) == pages.default_extras(False)


JUNK = ["", " ", "x" * 5000, "<script>alert(1)</script>", "javascript:alert(1)", "../../etc/passwd", "😀", "%00",
        "centre,wide", "none,byline", "tags=<b>,author=left", "--", "‮"]


@pytest.mark.parametrize("junk", JUNK)
def test_junk_in_the_form_is_cleaned_when_saving(admin, junk):
    mine = _save(admin, title_style=junk, page_width=junk, cover_width=junk, toc_style=junk, heading_fold=junk,
                 section_space=junk, section_motion=junk, sides_tags=junk, sides_archive=junk, sides_author=junk, link_url=junk,
                 slides=junk, in_wiki=junk, remind_update=junk, extras=[junk, "byline"], template_name=f"T{len(junk)}")
    got = mine["settings"]
    assert set(got) == set(post_templates.NO_SETTINGS)
    assert got == post_templates.clean_settings(got)  # nothing a post's own save wouldn't keep
    for name in ("title_style", "page_width", "cover_width", "toc_style", "heading_fold", "section_space",
                 "section_motion"):
        assert got[name] == "", name
    assert got["sides"] == "" and got["link_url"] == "" and not any(
        got[k] for k in ("slides", "in_wiki", "remind_update"))
    assert got["extras"] in ("", "byline", "none") and "<" not in json.dumps(got)
    assert admin.get(f"/admin/new?template=mine-{mine['id']}").status_code == 200


@pytest.mark.parametrize("junk", JUNK)
def test_junk_in_a_posts_tick_boxes_is_a_box_left_empty(admin, junk):
    from soloblog import posts
    r = admin.post("/admin/save", data={
        "title": f"Ticks {len(junk)}", "body": "Words.", "published": junk, "unlisted": junk, "slides": junk,
        "in_wiki": junk, "remind_update": junk, "post_noindex": junk, "comments_enabled": junk,
        "hide_list_cover": junk, "sides_tags": junk}, follow_redirects=False)
    assert r.status_code < 500
    row = posts.get_post(f"ticks-{len(junk)}")
    assert row and not any(row[k] for k in ("published", "unlisted", "slides", "in_wiki", "noindex")) \
        and not row["sides"]


def test_a_long_link_is_cut_not_kept_whole(admin):
    link = "https://example.com/" + "a" * 5000
    assert _save(admin, link_url=link)["settings"]["link_url"] == link[:posts_max_link()]


def posts_max_link():
    from soloblog import posts
    return posts.MAX_LINK


@pytest.mark.parametrize("stored", [None, [], "text", 7, {"title_style": ["centre"]},
                                    {"extras": {"a": 1}, "sides": 3, "link_url": {"x": 1}, "slides": "no",
                                     "toc_style": "<script>"},
                                    {"extras": "<script>,byline", "link_url": "javascript:alert(1)"}])
def test_settings_edited_by_hand_in_the_stored_json_never_break_a_page(admin, stored):
    one = {"id": "zz1", "name": "Hand made", "layout": "standard", "body": "Words.", "settings": stored}
    settings.set_many({"post_templates": json.dumps([one])})
    clean = post_templates.settings_of(post_templates.get("mine-zz1"))
    assert set(clean) == set(post_templates.NO_SETTINGS) and clean == post_templates.clean_settings(clean)
    assert "<script>" not in json.dumps(clean) and not clean["link_url"].startswith("javascript")
    for url in ("/admin/new?template=mine-zz1", "/admin/template/mine-zz1", "/admin/settings?tab=editor"):
        assert admin.get(url).status_code == 200, url


def test_the_apply_script_sets_every_setting_and_counts_show_once():
    source = Path("soloblog/js/apply_template.js").read_text(encoding="utf-8")
    for name in ("cover_width", "heading_fold", "section_space", "section_motion", "'sides_'", "input[name=\"extras\"]"):
        assert name in source, name
