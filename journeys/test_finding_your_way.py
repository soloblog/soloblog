"""Finding your way: back to the list from a post, the tab you were on,
Back after following the contents, and the editor showing marks as they
are until they're closed."""
import re

from conftest import publish


def test_a_post_links_back_to_posts_and_pages(owner):
    w = owner
    path = publish(w, "Way back", "A post to come back from.")
    w.go(path)
    w.page.locator("a[aria-label='Posts and pages'][href='/admin/posts']").first.click()
    w.page.wait_for_load_state("networkidle")
    assert w.page.url.endswith("/admin/posts"), w.page.url


def test_an_admin_page_opens_the_tab_you_were_on(owner):
    w = owner
    # a list's tabs open in place, without loading the page
    w.go("/admin/media")
    w.page.locator("[data-fit-tabs] a.tab[href*='tab=unused']").click()
    w.page.wait_for_url("**/admin/media?tab=unused*")
    w.go("/admin/posts")
    w.page.locator("[data-fit-tabs] a.tab[href*='status=draft']").click()
    w.page.wait_for_url("**/admin/posts?status=draft*")
    # from the menu: the address names no tab
    w.go("/admin/media")
    assert w.page.url.endswith("/admin/media?tab=unused"), w.page.url
    w.go("/admin/posts")
    assert w.page.url.endswith("/admin/posts?status=draft"), w.page.url
    # an address that names a tab keeps it, and is remembered in turn
    w.go("/admin/media?tab=all")
    assert w.page.url.endswith("?tab=all"), w.page.url
    # All is the page's own first tab: the plain address is enough
    w.go("/admin/media")
    assert w.page.url.endswith("/admin/media"), w.page.url
    assert "tab-active" in w.page.locator("a.tab[href*='tab=all']").get_attribute("class")


def test_back_after_the_contents_leaves_the_page(owner, site):
    w = owner
    text = "".join(f"\n\n## Part {n}\n\nSome words about part {n}." for n in range(1, 6))
    path = publish(w, "Many parts", text.strip())
    w.go("/")
    w.go(path)
    links = w.page.locator("[data-toc] a[href^='#']")
    assert links.count() >= 4
    before = w.page.evaluate("history.length")
    links.nth(1).click()
    w.page.wait_for_timeout(300)
    links.nth(3).click()
    w.page.wait_for_timeout(300)
    assert w.page.url.endswith("#part-4"), w.page.url
    assert w.page.evaluate("history.length") == before
    w.page.go_back()
    w.page.wait_for_load_state("networkidle")
    assert w.page.url.rstrip("/") == site["base"], w.page.url


def test_marks_that_are_never_closed_stay_plain(owner):
    w = owner
    w.go("/admin/new")
    styles = w.page.evaluate("""async () => {
        const cm = document.querySelector('.CodeMirror').CodeMirror;
        cm.setValue('**Never closed\\n\\n**closed** and *open\\n\\n~~struck~~ and ~~open\\n\\n**over\\ntwo lines**');
        cm.refresh();
        await new Promise(r => setTimeout(r, 200));
        // each line as drawn: its styled runs, text and class
        const drawn = [...document.querySelectorAll('.CodeMirror-code pre.CodeMirror-line')];
        return [0, 2, 4, 6, 7].map(n => [...drawn[n].querySelectorAll('span[class]')]
            .map(s => [s.textContent, s.className]));
    }""")
    never, mixed, struck, over, lines = styles
    assert not any("strong" in kind or "formatting" in kind for _, kind in never), never
    assert "strong" in dict(mixed)["closed"] and "open" not in dict(mixed), mixed
    assert "strikethrough" in dict(struck)["struck"] and "open" not in dict(struck), struck
    # bold over two lines of one paragraph is bold on both
    assert "strong" in dict(over)["over"] and "strong" in dict(lines)["two lines"], (over, lines)


def test_the_homepage_is_listed_as_a_page(owner):
    from test_site_menu import _set_homepage
    w = owner
    home = publish(w, "Front door", "Welcome in.")
    publish(w, "An ordinary post", "Words.")
    w.go("/admin/settings?tab=name")
    assert _set_homepage(w, home.rstrip("/").rsplit("/", 1)[-1]) == 200
    try:
        w.go("/admin/posts")
        row = w.page.locator("li", has=w.page.get_by_role("link", name="Front door", exact=True)).first
        assert row.get_by_text("Page", exact=True).is_visible()
        # the count names both kinds
        assert w.page.get_by_text(re.compile(r"^\d+ posts? and \d+ pages?$")).first.is_visible()
        # Type: Pages lists it, with the count of pages alone
        w.page.locator("button[popovertarget='filter-kind']").click()
        w.page.locator("#filter-kind").get_by_role("link", name="Pages", exact=True).click()
        w.page.wait_for_url("**kind=pages*")
        assert w.page.get_by_role("link", name="Front door", exact=True).is_visible()
        assert w.page.get_by_role("link", name="An ordinary post", exact=True).count() == 0
        assert w.page.get_by_text(re.compile(r"^\d+ pages?$")).first.is_visible()
    finally:
        _set_homepage(w, "")


def test_a_list_keeps_its_filters_until_cleared(owner):
    w = owner
    publish(w, "A post among pages", "Words.")
    w.go("/admin/posts?status=all")
    w.page.locator("button[popovertarget='filter-kind']").click()
    w.page.locator("#filter-kind").get_by_role("link", name="Pages", exact=True).click()
    w.page.wait_for_url("**kind=pages*")
    # away and back, by the admin's own menu
    w.page.locator("nav").get_by_role("link", name="Media", exact=True).first.click()
    w.page.wait_for_url("**/admin/media*")
    w.page.locator("nav").get_by_role("link", name="Posts and pages", exact=True).first.click()
    w.page.wait_for_url("**kind=pages*")
    assert "Pages" in w.page.locator("button[popovertarget='filter-kind']").inner_text()
    # Clear puts it back, and that's remembered too
    w.page.get_by_role("link", name="Clear", exact=True).click()
    w.page.wait_for_load_state("networkidle")
    w.go("/admin/posts")
    assert "kind=pages" not in w.page.url, w.page.url
    assert "All" in w.page.locator("button[popovertarget='filter-kind']").inner_text()
