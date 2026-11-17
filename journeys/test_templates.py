"""Templates: New posts start from, and Apply a template to a page that's
already written."""
import re

from playwright.sync_api import expect

from conftest import publish, save as _save


def _text(w):
    return w.page.evaluate("() => window._activeEasyMDE.value()")


def _open_settings(w):
    w.page.evaluate("() => { togglePostSettings(true); document.querySelectorAll('#post-settings-panel "
                    "details[data-panel]').forEach(d => d.open = true); }")


def _start_from(w, name):
    """Settings > Editor > New posts start from, picked from its list."""
    w.go("/admin/settings?tab=editor")
    w.page.locator("fieldset:has(#new_post_start) button[popovertarget]").click()
    w.page.locator("#new_post_start-combo button", has_text=name).first.click()
    w.page.wait_for_timeout(800)
    w.go("/admin/settings?tab=editor")
    assert w.page.locator("#new_post_start-label").inner_text().strip() == name


def _apply(w, search, name):
    _open_settings(w)
    w.page.locator("#post-settings-panel").get_by_role("button", name="Apply a template").click()
    dialog = w.page.locator("#template-dialog")
    dialog.locator("input[type=search]").fill(search)
    dialog.get_by_role("button", name=re.compile("^" + name)).first.click()


def _value(w, name):
    return w.page.locator(f"#post-settings-panel [name={name}]").input_value()


def test_new_posts_start_from_a_template_and_a_page_applies_one(owner):
    w = owner
    slug = publish(w, "Apply journey", "Words I wrote myself.").rsplit("/", 1)[-1]
    try:
        # New posts start from FAQ: New post opens with its sections, no picker
        _start_from(w, "FAQ")
        w.page.get_by_role("link", name="New post").first.click()
        w.page.wait_for_load_state("networkidle")
        assert "The first question?" in _text(w)
        assert w.page.locator("#template-start-dialog[open]").count() == 0
        # the Blank card in the picker still starts an empty post
        w.go("/admin/new?template=")
        assert "The first question?" not in _text(w)
    finally:
        _start_from(w, "Blank")
    w.go("/admin/new")
    assert _text(w).strip() == ""

    # an existing page: Apply a template adds the words at the end and uses its settings
    w.go(f"/admin/edit/{slug}")
    _open_settings(w)
    before = _text(w)
    status = w.page.locator("#save-status")
    _apply(w, "landing", "Landing page")
    expect(status).to_contain_text("Landing page applied · 5 settings changed")
    assert _text(w).startswith(before.rstrip()) and "Who it's for" in _text(w)
    assert _value(w, "title_style") == "hidden" and _value(w, "page_width") == "wide"
    # the Custom tags show what changed
    assert w.page.locator("#post-settings-panel details[data-panel=page] > summary").inner_text().strip() \
        == "Page · 4 changed"
    # Undo puts the text and the settings back
    status.get_by_role("button", name="Undo").click()
    assert _text(w) == before
    assert _value(w, "title_style") == "" and _value(w, "page_width") == ""
    assert w.page.locator("#save-status").inner_text().strip() == "Unsaved"

    # two in a row: the second one's settings win; Save keeps them
    _apply(w, "landing", "Landing page")
    expect(status).to_contain_text("Landing page applied")
    _apply(w, "slides", "Slides")
    expect(status).to_contain_text("Slides applied · 6 settings changed")
    assert w.page.locator("#post-settings-panel input[name=slides]").is_checked()
    assert _value(w, "title_style") == "" and _value(w, "page_width") == ""
    assert w.page.locator("#page-more").get_attribute("open") is not None
    both = _text(w)
    assert "Who it's for" in both and "The talk's title" in both and both.startswith(before.rstrip())
    _save(w)
    w.go(f"/admin/edit/{slug}")
    _open_settings(w)
    assert w.page.locator("#post-settings-panel input[name=slides]").is_checked()
    assert _value(w, "title_style") == "" and _value(w, "page_width") == ""
    assert _text(w).strip() == both.strip()


def _choose(w, name, words):
    """Picks from a choice's list, as a person does."""
    w.page.locator(f"#post-settings-panel fieldset:has([name={name}])").first.locator("button[popovertarget]").click()
    w.page.locator("ul[popover]:popover-open button", has_text=words).first.click()


def _likes(w):
    return w.page.locator("#post-settings-panel input[name=extras][value=reactions]")


def test_a_custom_template_keeps_every_setting_and_brings_them_all_back(owner):
    w = owner
    first = publish(w, "Frame to keep", "The words of the template.").rsplit("/", 1)[-1]
    other = publish(w, "Frame to change", "Words that stay.").rsplit("/", 1)[-1]

    # Custom settings on one post: Wide, Contents off, Likes unticked under Show
    w.go(f"/admin/edit/{first}")
    _open_settings(w)
    _choose(w, "page_width", "Wide")
    _choose(w, "toc_style", "Off")
    w.page.locator("#post-settings-panel label:has(input[name=extras][value=reactions])").click()
    # Save as a template, named as the post is
    panel = w.page.locator("#post-settings-panel details[data-panel=template]")
    panel.get_by_role("button", name="Save", exact=True).click()
    expect(w.page.locator("#template-status")).to_contain_text("Saved")

    # a new post from it has every setting, and says what's changed
    w.go("/admin/settings?tab=editor")
    href = w.page.locator("#templates-list a[href*='/admin/new?template=mine-']").first.get_attribute("href")
    w.go(href)
    _open_settings(w)
    assert _value(w, "page_width") == "wide" and _value(w, "toc_style") == "off" and _value(w, "title_style") == ""
    assert not _likes(w).is_checked()
    assert w.page.locator("#post-settings-panel input[name=extras][value=tags]").is_checked()
    assert w.page.locator("#post-settings-panel details[data-panel=page] > summary").inner_text().strip() \
        == "Page · 3 changed"

    # Apply it to the other post: all three set and counted, Undo puts every one back
    w.go(f"/admin/edit/{other}")
    _open_settings(w)
    assert _value(w, "page_width") == "" and _likes(w).is_checked()
    _apply(w, "Frame to keep", "Frame to keep")
    status = w.page.locator("#save-status")
    expect(status).to_contain_text("Frame to keep applied · 3 settings changed")
    assert _value(w, "page_width") == "wide" and _value(w, "toc_style") == "off" and not _likes(w).is_checked()
    status.get_by_role("button", name="Undo").click()
    assert _value(w, "page_width") == "" and _value(w, "toc_style") == "" and _likes(w).is_checked()
    # the template's words stay out of Undo's way: the post's own text is as it was
    assert "The words of the template." not in _text(w)
