"""Post settings: what a page sets differently from the site shows a bar and Reset
before it's saved, Reset puts it back, and it's still marked after."""
from conftest import Window, publish, save as _save, write as _write  # noqa: F401


def _open_settings(w):
    w.page.evaluate("() => { togglePostSettings(true); document.querySelectorAll('#post-settings-panel "
                    "details[data-panel]').forEach(d => d.open = true); }")


def _field(w, name):
    return w.page.locator(f"#post-settings-panel fieldset:has([name={name}])").first


def _heading(w, key):
    return w.page.locator(f"#post-settings-panel details[data-panel={key}] > summary").inner_text().strip()


def _choose(w, name, words):
    """Picks from a choice's list, as a person does."""
    _field(w, name).locator("button[popovertarget]").click()
    w.page.locator("ul[popover]:popover-open button", has_text=words).first.click()


def test_the_bar_and_reset_appear_as_things_change_and_go_with_use_the_sites(owner):
    w = owner
    w.go("/admin/new")
    _write(w, "Changed settings journey", "A page that changes some things from the site.")
    _open_settings(w)
    bar = "data-changed"
    assert _heading(w, "page") == "Page" and _field(w, "toc_style").get_attribute(bar) is None
    # a choice that isn't the site's: tagged at once, and counted
    _choose(w, "toc_style", "Off")
    assert _field(w, "toc_style").get_attribute(bar) is not None
    assert _field(w, "toc_style").get_by_role("button", name="Reset").is_visible()
    assert _heading(w, "page") == "Page · 1 changed"
    # a tick that isn't what the site shows
    w.page.locator("#post-settings-panel label:has(input[name=extras][value=tags])").click()
    assert _heading(w, "page") == "Page · 2 changed"
    # comments off, in the other panel
    w.page.locator("#post-settings-panel label:has(input[name=comments_enabled])").click()
    assert _heading(w, "publishing") == "Publishing · 1 changed"
    # Reset, beside each: a choice empties, a tick goes back
    _field(w, "toc_style").get_by_role("button", name="Reset").click()
    assert w.page.locator("#post-settings-panel select[name=toc_style]").input_value() == ""
    assert _field(w, "toc_style").get_attribute(bar) is None
    assert _field(w, "toc_style").get_by_role("button", name="Reset").is_hidden()
    assert _heading(w, "page") == "Page · 1 changed"
    w.page.locator("#post-settings-panel fieldset:has(input[name=extras]) legend").get_by_role(
        "button", name="Reset").click()
    assert w.page.locator("#post-settings-panel input[name=extras][value=tags]").is_checked()
    assert _heading(w, "page") == "Page"
    w.page.locator("#post-settings-panel fieldset:has(input[name=comments_enabled])").get_by_role(
        "button", name="Reset").click()
    assert _heading(w, "publishing") == "Publishing"


def test_a_changed_setting_is_still_marked_once_saved(owner):
    w = owner
    w.go("/admin/new")
    _write(w, "Wide changed page", "A wide page on a column site.")
    _open_settings(w)
    _choose(w, "page_width", "Wide")
    # the less common ones open their fold
    w.page.locator("#page-more summary").click()
    w.page.locator("#post-settings-panel label:has(input[name=remind_update])").click()
    w.page.locator("#post-settings-panel input[name=published]").check()
    _save(w)
    w.go(w.page.url)
    _open_settings(w)
    assert _heading(w, "page") == "Page · 1 changed"
    assert _field(w, "page_width").get_attribute("data-changed") is not None
    assert w.page.locator("#page-more").get_attribute("open") is not None
    assert w.page.locator("#post-settings-panel input[name=remind_update]").is_checked()
    # back to following the site, saved
    _field(w, "page_width").get_by_role("button", name="Reset").click()
    _save(w)
    w.go(w.page.url)
    _open_settings(w)
    assert _heading(w, "page") == "Page"
    assert w.page.locator("#post-settings-panel select[name=page_width]").input_value() == ""
