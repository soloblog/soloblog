"""On a phone: the owner writes a post with a section from the / menu,
and a reader finds it through the menu and search."""
from conftest import Window, save


def test_write_with_a_section_and_read_on_a_phone(owner_phone, browser, site):
    w = owner_phone
    w.go("/admin/new")
    w.page.locator("[placeholder=Title], input.text-2xl").first.fill("Pocket plans")
    w.page.locator(".CodeMirror").first.click()
    w.page.keyboard.type("Plans for a phone.")
    w.page.keyboard.press("Enter")
    w.page.keyboard.press("Enter")
    # the / menu finds the Pricing section by name
    w.page.keyboard.type("/pricing")
    w.page.wait_for_timeout(400)
    w.page.keyboard.press("Enter")
    w.page.wait_for_timeout(400)
    assert "Section: Pricing" in w.page.evaluate("() => window._activeEasyMDE.value()")
    w.page.evaluate("() => togglePostSettings(true)")
    w.page.locator("#post-settings-panel input[name=published]").check()
    save(w)
    slug = w.page.url.rstrip("/").rsplit("/", 1)[-1]
    # a reader on a phone: the plans as cards, nothing scrolling sideways
    reader = Window(browser, site["base"], 375, 812, phone=True)
    reader.go(f"/post/{slug}")
    assert reader.page.locator('[data-section="pricing"] .card').count() >= 2
    assert not reader.page.evaluate("() => document.documentElement.scrollWidth > innerWidth")
    # the menu opens and goes home
    reader.page.locator("[popovertarget=nav-mobile-menu]").click()
    reader.page.locator("#nav-mobile-menu a[href='/']").first.click()
    reader.page.wait_for_load_state("networkidle")
    assert reader.page.url.rstrip("/") == site["base"]
    # search finds the post, and a tap anywhere on its row opens it
    reader.go("/search?q=pocket")
    reader.page.locator("[data-click-rows] li, [data-click-rows] .card").first.click(position={"x": 5, "y": 5})
    reader.page.wait_for_load_state("networkidle")
    assert slug in reader.page.url
    reader.close()


def test_admin_bar_on_a_phone(owner_phone):
    """Where the admin menu folds away: the gear's menu is in the bar, as
    on the site, the magnifier comes before the colours, and Esc or a tap
    on the page closes the search it opened."""
    w = owner_phone
    w.go("/admin/posts")
    w.page.locator("[data-admin-bar] [popovertarget=nav-admin-menu]").click()
    menu = w.page.locator("#nav-admin-menu")
    assert menu.get_by_role("link", name="Settings").is_visible()
    w.page.keyboard.press("Escape")
    menu.wait_for(state="hidden", timeout=2000)
    w.page.get_by_role("button", name="Search settings and help").click()
    w.page.keyboard.type("email")
    w.page.keyboard.press("Escape")
    w.page.locator("#admin-search").wait_for(state="hidden", timeout=2000)
    assert w.page.locator("#admin-search").input_value() == ""
    magnifier = w.page.locator("[data-admin-bar] button[aria-label='Search settings and help']")
    # the first of the bar's buttons on the right (the colours can be off)
    gear = w.page.locator("[data-admin-bar] [popovertarget=nav-admin-menu]")
    assert magnifier.evaluate("b => b.parentElement.firstElementChild === b") and gear.is_visible()
    # empty: a tap on the page closes it
    magnifier.click()
    w.page.locator("#admin-search").wait_for(state="visible", timeout=2000)
    w.page.locator("#page-content").click(position={"x": 10, "y": 300})
    w.page.locator("#admin-search").wait_for(state="hidden", timeout=2000)
    # with a search in it the results are the page: a tap there keeps them
    magnifier.click()
    w.page.keyboard.type("email")
    w.page.locator("#page-content-results").wait_for(state="visible", timeout=5000)
    w.page.locator("#page-content-results p[role=status]").click()
    assert w.page.locator("#admin-search").is_visible()
    # a result reads top to bottom - its title, where it's from, its words -
    # not squeezed side by side by the touch screen's bigger links
    link = w.page.locator("#page-content-results ul a").first
    assert link.evaluate("a => getComputedStyle(a).display") == "block"


def test_help_contents_on_a_phone(owner_phone):
    """On a phone the contents sit at the top of a Help page: folded, they
    don't fade as if there were more below, and a link in them lands on
    its heading, just under the bar - not past it."""
    w = owner_phone
    w.go("/admin/help?tab=reference")
    toc = w.page.locator("[data-toc]")
    box = w.page.locator("[data-scroll-hint]:has([data-toc])")
    # as it is for a moment while the page is drawn: beside the text, a box
    # that scrolls, fading at its foot - then placed in the page for a phone
    toc.evaluate("t => { const d = t.closest('details'); if (d) d.open = true; }")
    box.evaluate("b => { b.closest('[data-side-panel]').setAttribute('data-beside', ''); _scrollHints(); }")
    # beside, it does fade - once the fold has finished opening (it grows)
    box.evaluate("b => new Promise(r => { const t = setInterval(() => { if (b.hasAttribute('data-more')) "
                 "{ clearInterval(t); r(); } }, 50); setTimeout(() => { clearInterval(t); r(); }, 3000); })")
    assert box.evaluate("b => b.hasAttribute('data-more')")
    w.page.evaluate("placeSidePanels()")
    toc.evaluate("t => { const d = t.closest('details'); if (d) d.open = false; }")
    w.page.wait_for_timeout(300)
    assert not box.evaluate("b => b.hasAttribute('data-more')")
    toc.evaluate("t => { const d = t.closest('details'); if (d) d.open = true; }")
    toc.locator("a[href='#keyboard-shortcuts']").click()
    w.page.wait_for_function(
        "() => { const h = document.getElementById('keyboard-shortcuts').getBoundingClientRect().top;"
        " const want = parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop);"
        " return Math.abs(h - want) <= 4; }", timeout=8000)


LONG = "\n\n".join("Words that run on for a while, so the text is much taller than a phone's screen. " * 3
                   for _ in range(30))
PLACE = """() => { const cm = window._activeEasyMDE.codemirror;
    return [Math.round(scrollY), cm.getCursor().line, cm.hasFocus(), window.blurs]; }"""


def _swipe(w, x, y, dist):
    """A finger put down at (x, y), moved dist up or down the screen and
    lifted - real touches, so the browser scrolls as a phone does."""
    cdp = w.context.new_cdp_session(w.page)
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y}]})
    for i in range(1, 13):
        cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x, "y": y + dist * i / 12}]})
        w.page.wait_for_timeout(16)
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    w.page.wait_for_timeout(600)


def _long_text(w):
    w.go("/admin/new")
    w.page.evaluate("(t) => window._activeEasyMDE.value(t)", LONG)
    w.page.wait_for_timeout(500)
    w.page.touchscreen.tap(180, 420)
    w.page.wait_for_timeout(400)
    w.page.evaluate("""() => { window.blurs = 0;
        window._activeEasyMDE.codemirror.getInputField().addEventListener('blur', () => window.blurs++); }""")


def test_scrolling_the_text_on_a_phone_leaves_the_keyboard_and_the_cursor(owner_phone):
    """Only a tap in the text asks for the keyboard. A finger that scrolled
    the text asked for it too, which brought it back up and the page back
    to the cursor."""
    w = owner_phone
    _long_text(w)
    line = w.page.evaluate(PLACE)[1]
    _swipe(w, 180, 600, -450)
    top, now, focused, blurs = w.page.evaluate(PLACE)
    assert top > 300 and now == line and focused and blurs == 0
    _swipe(w, 180, 300, 200)
    back, now, focused, blurs = w.page.evaluate(PLACE)
    assert 100 < back < top and now == line and blurs == 0
    # a tap asks again (the field is left and come back to, which is what
    # brings a phone's keyboard up) - and the page stays where the tap was
    w.page.touchscreen.tap(180, 420)
    w.page.wait_for_timeout(400)
    after, now, focused, blurs = w.page.evaluate(PLACE)
    assert blurs == 1 and focused and now != line and abs(after - back) < 4


def test_a_swipe_on_the_phone_menu_leaves_the_text_where_it_is(owner_phone):
    w = owner_phone
    _long_text(w)
    _swipe(w, 180, 600, -300)
    top = w.page.evaluate(PLACE)[0]
    w.page.locator(".editor-phonebar [data-id=all]").tap()
    w.page.wait_for_timeout(400)
    sheet = w.page.locator(".editor-sheet")
    # a short tab, all of it showing: up and down on it does nothing
    sheet.get_by_role("tab", name="Text").click()
    w.page.wait_for_timeout(400)
    box = sheet.bounding_box()
    for dist in (-150, 150):
        _swipe(w, 180, box["y"] + box["height"] / 2, dist)
        assert w.page.evaluate(PLACE)[0] == top and sheet.count() == 1
    # a long one scrolls under its tabs, and at its end the text behind
    # still doesn't move
    sheet.get_by_role("tab", name="Sections").click()
    w.page.wait_for_timeout(400)
    box = sheet.bounding_box()
    tabs_at = sheet.get_by_role("tablist").bounding_box()["y"]
    for _ in range(4):
        _swipe(w, 180, box["y"] + box["height"] - 80, -400)
    assert w.page.evaluate("() => document.querySelector('.editor-sheet [data-scroll-hint]').scrollTop") > 30
    assert sheet.get_by_role("tablist").bounding_box()["y"] == tabs_at
    assert w.page.evaluate(PLACE)[0] == top
