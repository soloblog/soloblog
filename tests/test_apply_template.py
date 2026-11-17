"""New posts start from (Settings > Editor), and Apply a template in the
editor: the route that gives the editor a template's words and settings, and
the dialog that offers them."""
from pathlib import Path
import re
from html import unescape as html_unescape

import pytest

from conftest import editor_script, save_post
from soloblog import post_templates, settings

RECIPE_WORDS = "A line or two about the dish"
FAQ_WORDS = "The first question?"


@pytest.fixture(autouse=True)
def blank_start():
    """The setting as a new site has it, and put back after."""
    before = {k: settings.get(k) for k in ("new_post_start", "post_templates", "template_recent")}
    settings.set_many({"new_post_start": "", "post_templates": "[]", "template_recent": ""})
    yield
    settings.set_many(before)


def _new(admin, query=""):
    """The words in a new post's text box (the page also carries the outlines, as data)."""
    r = admin.get("/admin/new" + query)
    assert r.status_code == 200
    return r.text


def _text(html):
    return html_unescape(re.search(r'<textarea[^>]*id="body-editor"[^>]*>(.*?)</textarea>', html, re.S).group(1))


def _choose(admin, value):
    """Picks it in Settings > Editor, as its picker does (autosave: that one setting)."""
    r = admin.post("/admin/settings/editor", data={"new_post_start": value, "declared_fields": "new_post_start"},
                   headers={"hx-request": "true"})
    assert r.status_code == 200, r.text


def _custom(name="My starting point", body="Words from my own template."):
    return f"mine-{post_templates.save(name, 'one, two', body, summary='Its summary', cover='/uploads/x.png')}"


def test_a_new_site_starts_new_posts_blank(admin):
    assert settings.DEFAULTS["new_post_start"] == "" and post_templates.start_key() == ""
    text = _text(_new(admin))
    assert RECIPE_WORDS not in text and FAQ_WORDS not in text


def test_new_posts_start_from_a_built_in_template_without_a_picker(admin):
    _choose(admin, "recipe")
    assert settings.get("new_post_start") == "recipe"
    html = _new(admin)
    assert RECIPE_WORDS in _text(html)
    # the picker is the Template label's, shut until it's asked for
    assert 'id="template-start-dialog"' in html and "template-start-dialog\" open" not in html
    assert ">Template: Recipe<" in html
    # it counts as used, for Recent
    assert post_templates.recent()[0] == "recipe"


def test_new_posts_start_from_a_custom_template_with_its_words_and_settings(admin):
    key = _custom()
    _choose(admin, key)
    html = _new(admin)
    assert "Words from my own template." in _text(html) and "Its summary" in html and "/uploads/x.png" in html
    assert "one, two" in html


def test_a_page_starts_from_it_as_a_post_does(admin):
    # Privacy policy starts as a footer page - New post and New page are one route
    _choose(admin, "privacy")
    html = _new(admin)
    assert post_templates.BUILT_IN["privacy"][1].split("\n")[0] in _text(html)
    assert re.search(r'<option value="footer"[^>]* selected', html) or 'value="footer" selected' in html


def test_a_deleted_custom_template_falls_back_to_blank_and_the_setting_shows_blank(admin):
    key = _custom()
    _choose(admin, key)
    post_templates.delete(key.removeprefix("mine-"))
    assert post_templates.start_key() == ""
    assert "Words from my own template." not in _text(_new(admin))
    page = admin.get("/admin/settings?tab=editor").text
    assert re.search(r'id="new_post_start-label"[^>]*>Blank<', page)


@pytest.mark.parametrize("junk", ["../../etc/passwd", "mine-", "mine-zzzz", "😀", "x" * 5000, "recipe,faq", " recipe"])
def test_a_value_that_is_not_a_template_is_cleaned_to_blank(admin, junk):
    _choose(admin, "recipe")
    _choose(admin, junk)
    assert settings.get("new_post_start") == ""
    assert admin.get("/admin/new").status_code == 200


def test_a_stale_value_in_the_database_never_breaks_new_post(admin):
    settings.set_many({"new_post_start": "mine-gone"})
    assert RECIPE_WORDS not in _text(_new(admin))
    assert admin.get("/admin/settings?tab=editor").status_code == 200


def test_the_address_overrides_the_setting(admin):
    _choose(admin, "recipe")
    faq = _text(_new(admin, "?template=faq"))
    assert FAQ_WORDS in faq and RECIPE_WORDS not in faq
    # an empty one is the Blank card's: an empty post, not the setting
    blank = _text(_new(admin, "?template="))
    assert FAQ_WORDS not in blank and RECIPE_WORDS not in blank
    # one that isn't a template is blank too
    assert RECIPE_WORDS not in _text(_new(admin, "?template=nope"))


def test_the_blank_card_asks_for_blank_and_the_setting_marks_the_chosen_one(admin):
    _choose(admin, "recipe")
    html = _new(admin)
    assert 'href="/admin/new?template="' in html
    card = re.search(r'<a[^>]*href="/admin/new\?template=recipe"[^>]*>', html).group(0)
    assert 'aria-selected="true"' in card


def test_the_settings_page_has_the_field_as_a_picker(admin):
    _choose(admin, "faq")
    html = admin.get("/admin/settings?tab=editor").text
    assert "New posts start from" in html
    assert 'popovertarget="new_post_start-combo"' in html and 'data-combo="new_post_start"' in html
    assert re.search(r'id="new_post_start-label"[^>]*>FAQ<', html)
    combo = html[html.index('id="new_post_start-combo"'):]
    combo = combo[:combo.index("</ul>")]
    # Blank, then custom ones, then the built-in ones
    assert combo.index(">Blank<") < combo.index(">Recipe<") < combo.index(">FAQ<")
    assert 'data-value=""' in combo and 'data-value="recipe"' in combo
    key = _custom("Zebra start")
    combo = re.search(r'id="new_post_start-combo".*?</ul>',
                      admin.get("/admin/settings?tab=editor").text, re.S).group(0)
    assert combo.index("Zebra start") < combo.index(">Recipe<") and f'data-value="{key}"' in combo
    # found by the search over Settings
    from soloblog.routes import admin_settings
    assert any(e["title"] == "New posts start from" for e in admin_settings.settings_index())


# ---- Apply a template

def test_the_template_route_gives_words_and_settings(admin):
    r = admin.get("/admin/template/landing")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/json")
    t = r.json()
    assert set(t) == {"name", "body", "tags", "summary", "cover", "settings"}
    assert t["name"] == post_templates.BUILT_IN["landing"][0] and t["body"] == post_templates.BUILT_IN["landing"][1]
    assert t["settings"] == post_templates.get("landing")["settings"]
    assert {k: t["settings"][k] for k in ("title_style", "page_width", "toc_style", "slides", "link_url")} == {
        "title_style": "hidden", "page_width": "wide", "toc_style": "off", "slides": False, "link_url": ""}
    # a custom one, and one that sets something
    key = _custom()
    mine = admin.get(f"/admin/template/{key}").json()
    assert mine["body"] == "Words from my own template." and mine["summary"] == "Its summary"
    assert mine["cover"] == "/uploads/x.png" and mine["tags"] == "one, two"
    assert admin.get("/admin/template/slides").json()["settings"]["slides"] is True
    assert admin.get("/admin/template/howto").json()["settings"]["toc_style"] == "top"


def test_every_built_in_template_can_be_applied(admin):
    for key in post_templates.BUILT_IN:
        r = admin.get(f"/admin/template/{key}")
        assert r.status_code == 200 and r.json()["body"], key


@pytest.mark.parametrize("key", ["nope", "mine-", "mine-zzzz", "..", "%2e%2e%2fetc%2fpasswd", "..%2f..%2fetc%2fpasswd",
                                 "😀", "x" * 3000, "%00", "recipe%00", "_trash"])
def test_the_template_route_never_errors_on_junk(admin, key):
    # a folder-like name never reaches the route (the client resolves it to another page)
    r = admin.get(f"/admin/template/{key}")
    assert r.status_code in (303, 404) and RECIPE_WORDS not in r.text


def test_an_unknown_template_is_a_json_404(admin):
    r = admin.get("/admin/template/nope")
    assert r.status_code == 404 and r.json() == {"error": "not found"}


def test_the_template_route_is_for_the_admin_only(client):
    r = client.get("/admin/template/recipe")
    assert r.status_code == 303 and r.headers["location"] == "/login"
    # a script's fetch is told to log in again, never given the words
    r = client.get("/admin/template/recipe", headers={"sec-fetch-mode": "cors"})
    assert r.status_code == 401 and "Recipe" not in r.text


def test_a_template_that_is_gone_is_a_404_for_the_route(admin):
    key = _custom()
    post_templates.delete(key.removeprefix("mine-"))
    assert admin.get(f"/admin/template/{key}").status_code == 404


def test_the_editor_offers_apply_a_template_on_a_post_and_on_a_new_one(admin):
    slug = save_post(admin, title="Apply here")
    key = _custom()
    for html in (admin.get(f"/admin/edit/{slug}").text, _new(admin)):
        # the button in Post settings > Template, beside Save as a template
        panel = html[html.index('data-panel="template"'):]
        panel = panel[:panel.index("</details>")]
        assert 'data-open-dialog="template-dialog"' in panel and "Apply a template" in panel
        assert panel.index("Apply a template") < panel.index("Save as a template")
        # the dialog: the same groups as the Templates tab, every card pressing Apply
        dialog = html[html.index('id="template-dialog"'):]
        dialog = dialog[:dialog.index("</dialog>")]
        assert "Apply a template" in dialog and "Adds its sections at the end and uses its settings." in dialog
        assert dialog.count("Custom") >= 2 and "Built-in" in dialog
        assert dialog.index("My starting point") < dialog.index("Recipe")
        assert f'data-args="[&quot;{key}&quot;]"' in dialog or f'data-args=\'["{key}"]\'' in dialog
        assert dialog.count('data-onclick="applyTemplate"') == len(post_templates.listed())
        assert 'href="/admin/new?template' not in dialog
        assert "applyTemplate" in editor_script(admin, html)
        # a script sits in the page with its nonce, no inline handler
        assert "function applyTemplate" in editor_script(admin, html)
        assert " onclick=" not in dialog


def test_recent_templates_come_first_in_the_apply_dialog_too(admin):
    post_templates.used("faq")
    slug = save_post(admin, title="Recent here")
    html = admin.get(f"/admin/edit/{slug}").text
    dialog = html[html.index('id="template-dialog"'):]
    dialog = dialog[:dialog.index("</dialog>")]
    assert dialog.index("Recent") < dialog.index("FAQ") < dialog.index("Built-in")


def test_a_saved_draft_message_leaves_an_undo_alone():
    source = Path("soloblog/js/editor_init.js").read_text(encoding="utf-8")
    assert "!status.querySelector('button')) status.textContent = 'Unsaved'" in source
