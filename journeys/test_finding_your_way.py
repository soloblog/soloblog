"""Finding your way: back to the list from a post, the tab you were on,
Back after following the contents, and the editor showing marks as they
are until they're closed."""
from conftest import publish


def test_a_post_links_back_to_posts_and_pages(owner):
    w = owner
    path = publish(w, "Way back", "A post to come back from.")
    w.go(path)
    w.page.locator("a[aria-label='Posts and pages'][href='/admin/posts']").first.click()
    w.page.wait_for_load_state("networkidle")
    assert w.page.url.endswith("/admin/posts"), w.page.url


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
