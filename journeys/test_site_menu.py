"""Home and Blog in the menu: the owner puts a page in the menu, moves Home
after it, renames Blog to Writing, hides Home - and a visitor sees the
header change, on a laptop and in a phone's menu."""
from conftest import Window, save, write


def _menu_page(w, title):
    """A page in the menu, written and published in the editor."""
    w.go("/admin/new")
    write(w, title, "A page.")
    w.page.evaluate("() => togglePostSettings(true)")
    w.page.locator("#post-settings-panel input[name=published]").check()
    # the styled picker over the select: the choice it makes is the select's value
    w.page.locator("#pin_location").evaluate("el => { el.value = 'header'; el.dispatchEvent(new Event('change', {bubbles: true})); }")
    save(w)
    return w.page.url.rstrip("/").rsplit("/", 1)[-1]


def _set_homepage(w, slug):
    """Settings > Name and homepage saves a page as the homepage ('' puts the posts back) - sent as
    the page's own form does, from the settings page."""
    return w.page.evaluate("""async (slug) => {
        const r = await fetch('/admin/settings/name', {method: 'POST', headers: {'hx-request': 'true'},
            body: new URLSearchParams({home_page: slug, declared_fields: 'home_page'})});
        return r.status;
    }""", slug)


def _row_words(w):
    """The links in the header's row on a wide screen."""
    return w.page.evaluate("() => [...document.querySelectorAll('[data-nav-menu] > li:not([data-nav-more]) > a, "
                           "[data-nav-menu] > li:not([data-nav-more]) summary > a')].map(a => a.textContent.trim())")


def _phone_words(w):
    w.page.locator("button[popovertarget=nav-mobile-menu]").click()
    words = w.page.evaluate("() => [...document.querySelectorAll('#nav-mobile-menu > li > a, "
                            "#nav-mobile-menu > li > details > summary a')].map(a => a.textContent.trim())")
    w.page.keyboard.press("Escape")
    return words


def test_the_owner_moves_renames_and_hides_home_and_a_visitor_sees_it(owner, browser, site):
    _menu_page(owner, "Journey about")
    # the homepage is a page of the owner's, so the menu has a Blog
    owner.go("/admin/posts?status=pinned")
    row = owner.page.locator("#site-row-home")
    assert "Site page" in row.inner_text()

    visitor = Window(browser, site["base"])
    visitor.go("/")
    assert _row_words(visitor)[0] == "Home" and "Journey about" in _row_words(visitor)

    # Home moves down, behind the page
    owner.page.locator("#pin-acts-site-home [aria-label=Move]").click()
    with owner.page.expect_navigation():
        owner.page.locator("#pin-acts-site-home form[action='/admin/nav/move'] button").click()
    visitor.go("/")
    words = _row_words(visitor)
    assert words.index("Journey about") < words.index("Home")

    # renamed, in the box that opens under the pencil
    owner.page.locator("#pin-acts-site-home [aria-label=Rename]").click()
    owner.page.locator("#pin-acts-site-home input[name=label]").fill("Start here")
    with owner.page.expect_navigation():
        owner.page.get_by_role("button", name="Save", exact=True).click()
    assert "Renamed to Start here" in owner.page.locator("body").inner_text()
    assert "Start here" in owner.page.locator("#site-row-home").inner_text()
    visitor.go("/")
    assert "Start here" in _row_words(visitor) and "Home" not in _row_words(visitor)

    # hidden: gone from the row, and the row says so
    with owner.page.expect_navigation():
        owner.page.locator("#pin-acts-site-home [aria-label='Hide from menu']").click()
    assert "Hidden" in owner.page.locator("#site-row-home").inner_text()
    visitor.go("/")
    assert "Start here" not in _row_words(visitor) and "Journey about" in _row_words(visitor)
    visitor.close()

    phone = Window(browser, site["base"], 375, 812, phone=True)
    phone.go("/")
    words = _phone_words(phone)
    assert "Start here" not in words and "Journey about" in words
    assert not phone.page.evaluate("() => document.documentElement.scrollWidth > innerWidth")
    phone.close()

    # shown again, and the owner's own words stay
    with owner.page.expect_navigation():
        owner.page.locator("#pin-acts-site-home [aria-label='Show in menu']").click()
    phone = Window(browser, site["base"], 375, 812, phone=True)
    phone.go("/")
    assert "Start here" in _phone_words(phone)
    phone.close()


def test_the_owner_renames_blog_to_writing(owner, browser, site):
    slug = _menu_page(owner, "Journey front page")
    # a page of the owner's as the homepage puts the posts at /blog, and a Blog in the menu
    owner.go("/admin/settings/name")
    assert _set_homepage(owner, slug) == 200
    owner.go("/admin/posts?status=pinned")
    assert "Site page" in owner.page.locator("#site-row-blog").inner_text()
    owner.page.locator("#pin-acts-site-blog [aria-label=Rename]").click()
    owner.page.locator("#pin-acts-site-blog input[name=label]").fill("Writing")
    with owner.page.expect_navigation():
        owner.page.locator("#pin-acts-site-blog").get_by_role("button", name="Save", exact=True).click()
    assert "Renamed to Writing" in owner.page.locator("body").inner_text()

    for window in (Window(browser, site["base"]), Window(browser, site["base"], 375, 812, phone=True)):
        window.go("/")
        words = _phone_words(window) if window.page.viewport_size["width"] < 400 else _row_words(window)
        assert "Writing" in words and "Blog" not in words
        window.close()
    assert _set_homepage(owner, "") == 200


def _footer_words(w):
    return w.page.evaluate("() => [...document.querySelectorAll('footer a')].map(a => a.textContent.trim())")


def _add_from(owner, where, word):
    """Add to menu (or footer): open the button's list, choose a page."""
    owner.page.locator(f"label:has-text('Add to {'menu' if where == 'header' else 'footer'}')").click()
    with owner.page.expect_navigation():
        owner.page.locator(f"form[action='/admin/nav/add']:has(input[value={where}]) button:has-text('{word}')").click()


def test_the_owner_adds_built_in_pages_to_the_menu_and_the_footer(owner, browser, site):
    owner.go("/admin/posts?status=pinned")
    # a wiki note, so the wiki can be added
    slug = owner.page.evaluate("""async () => {
        const r = await fetch('/admin/save', {method: 'POST', headers: {'hx-request': 'true'}, body: new URLSearchParams(
            {title: 'Journey wiki note', body: 'A note.', published: '1', in_wiki: '1', comments_enabled: '1'})});
        return (r.headers.get('hx-redirect') || '').split('/').pop();
    }""")
    owner.go("/admin/posts?status=pinned")
    _add_from(owner, "header", "Archive")
    assert "Archive is in the menu" in owner.page.locator("body").inner_text()
    _add_from(owner, "header", "Wiki")
    assert "Site page" in owner.page.locator("#site-row-archive").inner_text()

    wide = Window(browser, site["base"])
    phone = Window(browser, site["base"], 375, 812, phone=True)
    wide.go("/")
    phone.go("/")
    assert _row_words(wide)[-2:] == ["Archive", "Wiki"] and _phone_words(phone)[-2:] == ["Archive", "Wiki"]

    # Wiki moves up, Archive is renamed
    owner.page.locator("#pin-acts-site-wiki [aria-label=Move]").click()
    with owner.page.expect_navigation():
        owner.page.locator("#pin-acts-site-wiki form[action='/admin/nav/move'] button:has-text('Move up')").click()
    owner.page.locator("#pin-acts-site-archive [aria-label=Rename]").click()
    owner.page.locator("#pin-acts-site-archive input[name=label]").fill("All posts")
    with owner.page.expect_navigation():
        owner.page.locator("#pin-acts-site-archive").get_by_role("button", name="Save", exact=True).click()
    assert "Renamed to All posts" in owner.page.locator("body").inner_text()
    wide.go("/")
    phone.go("/")
    assert _row_words(wide)[-2:] == ["Wiki", "All posts"] and _phone_words(phone)[-2:] == ["Wiki", "All posts"]
    assert not phone.page.evaluate("() => document.documentElement.scrollWidth > innerWidth")

    # Wiki comes out, and can be added again
    with owner.page.expect_navigation():
        owner.page.locator("#pin-acts-site-wiki [aria-label='Remove from menu']").click()
    assert "Wiki is out of the menu" in owner.page.locator("body").inner_text()
    wide.go("/")
    assert "Wiki" not in _row_words(wide) and "All posts" in _row_words(wide)
    owner.page.locator("label:has-text('Add to menu')").click()
    assert owner.page.locator("form[action='/admin/nav/add']:has(input[value=header]) button:has-text('Wiki')").count() == 1

    # the footer's own list: Archive once there, and not again in its small print
    _add_from(owner, "footer", "Archive")
    wide.go("/")
    words = _footer_words(wide)
    assert words.count("Archive") == 1 and "Tags" in words
    assert "All posts" in _row_words(wide)  # the header's words are the header's own

    # put the site back as it was
    with owner.page.expect_navigation():
        owner.page.locator("#pin-acts-site-foot-archive [aria-label='Remove from footer']").click()
    with owner.page.expect_navigation():
        owner.page.locator("#pin-acts-site-archive [aria-label='Remove from menu']").click()
    owner.page.evaluate("async (slug) => { await fetch('/admin/delete', {method: 'POST', body: new URLSearchParams({slug})}); }", slug)
    wide.close()
    phone.close()


def test_the_banner_shows_over_the_posts_at_blog(owner, browser, site):
    slug = _menu_page(owner, "Journey banner front")
    owner.go("/admin/settings?tab=name")
    assert _set_homepage(owner, slug) == 200
    try:
        # the owner turns the banner on and gives it a heading
        owner.go("/admin/settings?tab=banner")
        switch = owner.page.locator("input[name=banner_enabled]")
        if not switch.is_checked():
            switch.locator("xpath=ancestor::label[1]").click()
        owner.page.locator("input[name=banner_heading]").fill("Fresh from the oven")
        owner.page.get_by_role("button", name="Save", exact=True).click()
        owner.page.locator("#save-status.text-success").wait_for()
        # a visitor finds it over the posts, where the menu's Blog goes (its
        # name is the owner's to change)
        visitor = Window(browser, site["base"])
        visitor.go("/")
        assert visitor.page.get_by_text("Fresh from the oven").count() == 0
        visitor.page.locator("header a[href='/blog']:visible").first.click()
        visitor.page.wait_for_url("**/blog")
        assert visitor.page.get_by_role("heading", name="Fresh from the oven").is_visible()
        visitor.close()
    finally:
        _set_homepage(owner, "")
        owner.page.evaluate("""() => fetch('/admin/settings/banner', {method: 'POST', headers: {'hx-request': 'true'},
            body: new URLSearchParams({banner_enabled: '', banner_heading: '',
                                       declared_fields: 'banner_enabled,banner_heading'})})""")
