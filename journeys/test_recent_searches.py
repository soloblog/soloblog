"""The admin's search remembers what was searched: back in the empty
box, the last few searches are listed, one runs, and the list clears."""
from conftest import Window

BOX = "#admin-search"
LIST = "#recent-admin"


def _search(w, q):
    w.page.fill(BOX, q)
    w.page.keyboard.press("Enter")
    w.page.wait_for_selector("#page-content-results [role=status]")
    w.page.fill(BOX, "")
    w.page.locator("#page-content-results").wait_for(state="hidden")


def test_search_comes_back_runs_and_clears(owner):
    owner.go("/admin/settings")
    # nothing searched yet: nothing to show
    owner.page.click(BOX)
    assert not owner.page.locator(LIST).is_visible()
    for q in ["email", "backup", "Email", "tags", "comments", "themes", "domain"]:
        _search(owner, q)
    owner.page.keyboard.press("Escape")
    # a new page: the box, focused and empty, lists the last five, newest
    # first, "Email" and "email" being one search
    owner.go("/admin/settings")
    owner.page.click(BOX)
    rows = owner.page.locator(f"{LIST} [data-recent-query]")
    assert rows.all_inner_texts() == ["domain", "themes", "comments", "tags", "Email"]
    assert owner.page.locator(BOX).get_attribute("aria-expanded") == "true"
    # arrows and Enter run the second one
    owner.page.keyboard.press("ArrowDown")
    owner.page.keyboard.press("ArrowDown")
    owner.page.keyboard.press("Enter")
    owner.page.wait_for_selector("#page-content-results [role=status]")
    assert owner.page.input_value(BOX) == "themes"
    assert not owner.page.locator(LIST).is_visible()
    # Esc closes the list, a click on a row runs it, Clear empties it
    owner.page.fill(BOX, "")
    assert owner.page.locator(LIST).is_visible()
    owner.page.keyboard.press("Escape")
    assert not owner.page.locator(LIST).is_visible()
    owner.page.fill(BOX, "x")
    owner.page.fill(BOX, "")
    owner.page.locator(f"{LIST} [data-recent-query]", has_text="tags").click()
    assert owner.page.input_value(BOX) == "tags"
    owner.page.fill(BOX, "")
    assert owner.page.locator(f"{LIST} [data-recent-query]").first.inner_text() == "tags"
    owner.page.get_by_text("Clear recent searches").click()
    assert not owner.page.locator(LIST).is_visible()
    owner.page.keyboard.press("Tab")
    owner.page.click(BOX)
    assert not owner.page.locator(LIST).is_visible()


def test_recent_searches_fit_a_phone(browser, site, set_up):
    from conftest import sign_in
    w = Window(browser, site["base"], 320, 640, phone=True)
    sign_in(w)
    w.go("/admin/settings")
    w.page.locator("[aria-label='Search settings and help']").first.click()
    w.page.fill(BOX, "a long search for the sake of the width of this list ok")
    w.page.keyboard.press("Enter")
    w.page.fill(BOX, "")
    box = w.page.locator(LIST).bounding_box()
    assert box["x"] >= 0 and box["x"] + box["width"] <= 320
    assert w.page.locator(f"{LIST} [data-recent-query]").first.bounding_box()["height"] >= 44
    w.close()
