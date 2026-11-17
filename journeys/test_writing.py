"""Writing: a new post, published, changed, and an earlier version back."""
from pathlib import Path
import re

from conftest import Window, publish, save as _save, write as _write  # noqa: F401


def test_write_publish_change_and_restore(owner, browser, site):
    w = owner
    w.go("/admin/new")
    _write(w, "Journey loaf", "The first version of this post.")
    # published: Post settings > Published
    w.page.evaluate("() => togglePostSettings(true)")
    w.page.locator("#post-settings-panel input[name=published]").check()
    _save(w)
    assert re.search(r"/admin/edit/journey-loaf", w.page.url), w.page.url
    # readers see it, on the homepage and its own page
    reader = Window(browser, site["base"])
    reader.go("/")
    assert "Journey loaf" in reader.page.content()
    reader.go("/post/journey-loaf")
    assert "The first version of this post." in reader.page.content()
    # changed and saved again: History has the earlier version
    w.page.locator(".CodeMirror").first.click()
    w.page.keyboard.press("Control+End")
    w.page.keyboard.type(" A second sentence.")
    _save(w)
    reader.go("/post/journey-loaf")
    assert "A second sentence." in reader.page.content()
    w.go("/admin/edit/journey-loaf")
    w.page.evaluate("() => { togglePostSettings(true); document.querySelectorAll('#post-settings-panel details')"
                    ".forEach(d => d.open = true); }")
    rows = w.page.locator("#history-list [aria-label=Restore]")
    assert rows.count() >= 1
    # Compare shows what changed
    w.page.locator("#history-list [aria-label=Compare]").last.click()
    w.page.wait_for_timeout(800)
    assert w.page.locator("#revision-diff-dialog[open]").count() == 1
    w.page.keyboard.press("Escape")
    # Restore puts the first version back in the editor; saving publishes it
    rows.last.click()
    w.page.wait_for_timeout(500)
    yes = w.page.locator("dialog[open]").get_by_role("button", name=re.compile("Restore|Yes"))
    if yes.count():
        yes.first.click()
    w.page.wait_for_timeout(500)
    _save(w)
    reader.go("/post/journey-loaf")
    assert "The first version of this post." in reader.page.content()
    assert "A second sentence." not in reader.page.content()
    reader.close()


def test_ticking_posts_never_moves_the_list(owner, browser, site):
    """The bar of what to do with ticked posts keeps its height - what
    doesn't fit goes under More - on a laptop and on a phone."""
    publish(owner, "Tick one", "A post to tick.")
    publish(owner, "Tick two", "Another post to tick.")
    state = owner.context.storage_state()
    for width, height, phone in ((1050, 800, False), (375, 812, True), (320, 700, True)):
        w = Window(browser, site["base"], width, height, phone=phone, state=state)
        w.go("/admin/posts")
        ticks = w.page.locator("input[type=checkbox][form]")
        before = first_row(w)
        # the boxes are out of sight until they're wanted
        w.page.mouse.move(0, 0)
        w.page.wait_for_timeout(300)
        assert w.page.evaluate("() => getComputedStyle(document.querySelector('input[type=checkbox][form]')).opacity") == "0"
        if phone:
            # pressing and holding a row ticks it - a tap doesn't, nor opens it
            hold(w, 1, 150)
            assert not ticks.nth(1).is_checked() and "/admin/posts" in w.page.url
            hold(w, 0, 650)
            assert ticks.nth(0).is_checked() and "/admin/posts" in w.page.url
        else:
            ticks.nth(0).check()
        assert first_row(w) == before, f"{width}px: the list moved on the first tick"
        ticks.nth(1).check()
        w.page.locator("[data-select-all]").check()
        assert first_row(w) == before, f"{width}px: the list moved"
        assert not w.page.evaluate("() => document.documentElement.scrollWidth > innerWidth")
        # a tag typed a letter at a time keeps every letter, and the cursor
        tag = w.page.locator("form[data-bulk] input[name=tag]")
        if not tag.is_visible():
            w.page.locator("[data-bulk-more]").click()
        tag.click()
        w.page.keyboard.type("garden")
        assert tag.input_value() == "garden"
        assert w.page.evaluate("() => document.activeElement.name") == "tag"
        w.page.keyboard.press("Escape")
        # what's under More still asks before moving to trash
        if w.page.locator("[data-bulk-more]").is_visible():
            w.page.locator("[data-bulk-more]").click()
            w.page.locator("[popover]:popover-open button", has_text="Move to trash").click()
            dialog = w.page.locator("dialog[open]")
            assert "trash" in dialog.inner_text()
            dialog.get_by_role("button", name="Cancel").click()
        w.page.locator("[data-bulk-cancel]").click()
        assert first_row(w) == before, f"{width}px: the list moved back"
        w.close()


def hold(w, n, ms):
    """A finger on the nth row's words for ms, then lifted."""
    w.page.evaluate("""async ([n, ms]) => {
        const row = document.querySelectorAll('[data-tick-row]')[n];
        const target = row.querySelector('.text-xs') || row, r = target.getBoundingClientRect();
        const touch = new Touch({identifier: 1, target, clientX: r.left + 5, clientY: r.top + 5});
        const send = (type, touches) => target.dispatchEvent(new TouchEvent(type,
            {bubbles: true, cancelable: true, touches, changedTouches: [touch]}));
        send('touchstart', [touch]);
        await new Promise(x => setTimeout(x, ms));
        if (send('touchend', [])) target.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
    }""", [n, ms])
    # a person's next tap - sooner is taken for the lifted finger's own click
    w.page.wait_for_timeout(500)


def first_row(w):
    """Where the list's first row starts on the screen."""
    return w.page.evaluate("() => document.querySelector('input[type=checkbox][form]').getBoundingClientRect().top")


def test_export_downloads_the_ticked_posts(owner):
    """Export in the bar of ticked posts gives a file of just those, and
    the page stays as it was."""
    w = owner
    publish(w, "Export one", "The first.")
    publish(w, "Export two", "The second.")
    w.go("/admin/posts")
    ticks = w.page.locator("input[type=checkbox][form]")
    ticks.nth(0).check()
    ticks.nth(1).check()
    export = w.page.locator("form[data-bulk] button[name=action][value=export]")
    with w.page.expect_download() as got:
        if export.is_visible():
            export.click()
        else:
            w.page.locator("[data-bulk-more]").click()
            w.page.locator("[popover]:popover-open button", has_text="Export").click()
    rows = Path(got.value.path()).read_text(encoding="utf-8").strip().splitlines()
    assert got.value.suggested_filename == "posts.csv" and len(rows) == 3, rows
    assert "/admin/posts" in w.page.url and not export.get_attribute("data-busy")


def test_only_real_links_look_like_links(owner):
    # [TOTAL] in a table is a placeholder, not a link: it isn't styled as one,
    # and the Link button stays off while the cursor is in it
    errors = []
    owner.page.on("pageerror", lambda e: errors.append(str(e)))
    owner.go("/admin/new")
    _write(owner, "Links or not", "Total US$[TOTAL] here")
    owner.page.keyboard.press("Enter")
    owner.page.keyboard.type("A [real link](https://example.com) and [[A note]]")
    owner.page.wait_for_timeout(300)
    styled = owner.page.evaluate("Array.from(document.querySelectorAll('.CodeMirror .cm-link'))"
                                 ".map(e => e.textContent).join('')")
    assert "TOTAL" not in styled and "real link" in styled and "A note" in styled
    cm = "document.querySelector('.CodeMirror').CodeMirror"
    owner.page.evaluate(cm + ".setCursor({line: 0, ch: 12})")
    owner.page.wait_for_timeout(200)
    assert not owner.page.locator(".editor-toolbar button.link.active").count()
    owner.page.evaluate(cm + ".setCursor({line: 1, ch: 5})")
    owner.page.wait_for_timeout(200)
    assert owner.page.locator(".editor-toolbar button.link.active").count()
    assert not errors, errors


def test_a_section_comes_with_every_option_and_default_is_set_from_the_menu(owner, browser, site):
    """Insert a section from the / menu: every option line written out and
    faded as Default; set Width from the menu, then back to Default; save -
    and the page is the section, no option line showing."""
    w = owner
    cm = "document.querySelector('.CodeMirror').CodeMirror"
    w.go("/admin/new")
    _write(w, "Journey sections", "Some words first.")
    w.page.keyboard.press("Enter")
    w.page.keyboard.press("Enter")
    # the / menu: Latest posts, in one go
    w.page.keyboard.type("/latest")
    w.page.wait_for_timeout(300)
    w.page.keyboard.press("Enter")
    w.page.wait_for_timeout(300)
    text = w.page.evaluate(cm + ".getValue()")
    assert ("## Lately\n\nSection: Latest posts\nWidth: Default\nStyle: Default\nHeading: Default\nSpace: Default\n"
            "Appear: Default\nCount: Default\nTag: Default" in text), text
    # one undo takes the whole section back out, as it came in
    w.page.evaluate(cm + ".undo()")
    assert "Section:" not in w.page.evaluate(cm + ".getValue()")
    w.page.evaluate(cm + ".redo()")
    assert "Tag: Default" in w.page.evaluate(cm + ".getValue()")

    def line_of(prefix):
        return w.page.evaluate("(p) => { const c = " + cm + "; for (let i = 0; i < c.lineCount(); i++) "
                               "if (c.getLine(i).startsWith(p)) return i; return -1; }", prefix)

    def faded():
        return w.page.evaluate("Array.from(document.querySelectorAll('.CodeMirror-line.sb-default')).map(e => e.textContent)")
    # every option is a setting line, every one faded while it's Default
    assert w.page.locator(".CodeMirror-line.sb-setting").count() == 7 and len(faded()) == 7
    assert w.page.evaluate("getComputedStyle(document.querySelector('.CodeMirror-line.sb-default > span')).opacity") == "0.6"
    # Width from the menu, on its own line: Wide, no longer faded
    w.page.evaluate(cm + f".setCursor({{line: {line_of('Width:')}, ch: 0}})")
    w.page.keyboard.type("/wide")
    w.page.wait_for_timeout(300)
    assert "Width: Wide" in w.page.locator(".fixed.z-50 ul[role=listbox]").inner_text()
    w.page.keyboard.press("Enter")
    w.page.wait_for_timeout(700)
    assert w.page.evaluate(cm + f".getLine({line_of('Width:')})") == "Width: Wide"
    assert len(faded()) == 6 and "Width: Wide" not in " ".join(faded())
    # a value the page can't use is underlined, with what it can be
    w.page.evaluate(cm + f".replaceRange('Tall', {{line: {line_of('Width:')}, ch: 7}}, {{line: {line_of('Width:')}, ch: 11}})")
    w.page.wait_for_timeout(900)
    assert w.page.locator(".CodeMirror .decoration-wavy").inner_text() == "Tall"
    assert w.page.get_by_text("Width can be Column, Wide, Full or Default").count() == 1
    # a tag called Default is a reserved word - flagged only once the site has one
    w.page.evaluate("window.EDITOR_PREFS.options.defaultTag = true")
    w.page.evaluate(cm + f".replaceRange('Wide', {{line: {line_of('Width:')}, ch: 7}}, {{line: {line_of('Width:')}, ch: 11}})")
    w.page.wait_for_timeout(900)
    assert w.page.locator(".CodeMirror .decoration-wavy").inner_text() == "Default"
    assert w.page.get_by_text("Default is a reserved word", exact=True).count() == 1
    w.page.evaluate("window.EDITOR_PREFS.options.defaultTag = false")
    w.page.evaluate(cm + ".replaceRange('Still ', {line: 0, ch: 0})")
    w.page.wait_for_timeout(900)
    assert w.page.locator(".CodeMirror .decoration-wavy").count() == 0
    # Width back to Default - the same menu, a line written, none deleted
    w.page.evaluate(cm + f".setCursor({{line: {line_of('Width:')}, ch: 0}})")
    w.page.keyboard.type("/default")
    w.page.wait_for_timeout(300)
    w.page.keyboard.press("Enter")
    w.page.wait_for_timeout(700)
    assert w.page.evaluate(cm + f".getLine({line_of('Width:')})") == "Width: Default"
    assert len(faded()) == 7
    # saved and published: the page shows the section, and none of its lines
    w.page.evaluate("() => togglePostSettings(true)")
    w.page.locator("#post-settings-panel input[name=published]").check()
    _save(w)
    slug = w.page.url.rstrip("/").rsplit("/", 1)[-1]
    reader = Window(browser, site["base"])
    reader.go(f"/post/{slug}")
    page = reader.page.content()
    assert 'data-section="latest"' in page and "Some words first." in page
    assert "Section: Latest posts" not in page and "Width: Default" not in page and "Count: Default" not in page
    reader.close()
    with open(f"{site['data']}/posts/{slug}.md", encoding="utf-8") as f:
        assert ("Width: Default\nStyle: Default\nHeading: Default\nSpace: Default\nAppear: Default\nCount: Default\n"
                "Tag: Default") in f.read()


def test_a_section_appears_its_own_way_then_the_pages_then_the_sites(owner, browser, site):
    """Appear: from the / menu is the section's own; take it back to Default
    and the page's Sections appear (Post settings > Page, marked Custom)
    is what shows; with neither, the site's."""
    w = owner
    cm = "document.querySelector('.CodeMirror').CodeMirror"
    w.go("/admin/new")
    _write(w, "Journey appearing", "Some words first.")
    w.page.keyboard.press("Enter")
    w.page.keyboard.press("Enter")
    w.page.keyboard.type("/latest")
    w.page.wait_for_timeout(300)
    w.page.keyboard.press("Enter")
    w.page.wait_for_timeout(300)

    def line_of(prefix):
        return w.page.evaluate("(p) => { const c = " + cm + "; for (let i = 0; i < c.lineCount(); i++) "
                               "if (c.getLine(i).startsWith(p)) return i; return -1; }", prefix)

    def choose_appear(words):
        w.page.evaluate(cm + ".focus()")
        w.page.evaluate(cm + f".setCursor({{line: {line_of('Appear:')}, ch: 0}})")
        w.page.keyboard.type("/" + words)
        w.page.wait_for_timeout(300)
        w.page.keyboard.press("Enter")
        w.page.wait_for_timeout(700)
    choose_appear("rise")
    assert w.page.evaluate(cm + f".getLine({line_of('Appear:')})") == "Appear: Rise"
    # the page's own, in Post settings > Page
    w.page.evaluate("() => { togglePostSettings(true); document.querySelectorAll('#post-settings-panel "
                    "details[data-panel]').forEach(d => d.open = true); }")
    field = w.page.locator("#post-settings-panel fieldset:has([name=section_motion])").first
    assert field.get_attribute("data-changed") is None
    field.locator("button[popovertarget]").click()
    w.page.locator("ul[popover]:popover-open button", has_text="Zoom").first.click()
    assert field.get_attribute("data-changed") is not None
    w.page.locator("#post-settings-panel input[name=published]").check()
    _save(w)
    slug = w.page.url.rstrip("/").rsplit("/", 1)[-1]
    reader = Window(browser, site["base"])

    def revealed():
        reader.go(f"/post/{slug}")
        return reader.page.locator("[data-section=latest]").get_attribute("data-reveal")
    assert revealed() == "rise"
    # Default: the page's
    choose_appear("default")
    _save(w)
    assert revealed() == "zoom"
    # and with the page following the site, the site's
    w.page.evaluate("() => togglePostSettings(true)")
    field.get_by_role("button", name="Reset").click()
    assert field.get_attribute("data-changed") is None
    _save(w)
    assert revealed() == "fade"
    reader.close()


def test_the_editors_help_opens_jumps_inserts_and_steps_out_of_the_way(owner):
    """Help beside the editor: it opens, a part's name goes to that part, an
    example goes into the post - and once closed it isn't laid out any more,
    which made every key typed slow."""
    w = owner
    w.go("/admin/new")
    _write(w, "Help at hand", "")
    shown = "() => getComputedStyle(document.getElementById('editor-help-scroll')).display !== 'none'"
    assert not w.page.evaluate(shown)
    w.page.locator("#editor-bar [aria-label=Help]").first.click()
    panel = w.page.locator("#editor-help-panel")
    w.page.wait_for_timeout(300)
    assert panel.get_attribute("inert") is None and w.page.evaluate(shown)
    assert panel.locator("#editor-help-guide").is_visible()
    # a part's name, then Insert on its first example
    panel.locator("[data-help-jump=sections]").click()
    # it scrolls there smoothly, a long way down
    w.page.wait_for_function("() => document.querySelector('[data-help-section=sections]').getBoundingClientRect().top < 400")
    part = panel.locator("[data-help-section=sections]")
    # each section is a row that opens to its example
    part.locator("details summary").first.click()
    part.locator("[data-help-insert]:visible").first.click()
    w.page.wait_for_timeout(400)
    assert panel.get_attribute("inert") is not None
    assert "Section:" in w.page.evaluate("() => window._activeEasyMDE.value()")
    assert not w.page.evaluate(shown)


def _link_by_title(w, tag):
    """[[ lists the titles, typing narrows them, Enter or Tab writes one,
    Esc leaves what's typed - in whatever window it's given."""
    first, second = publish(w, "Hydration notes" + tag, "About water."), publish(w, "Héron story" + tag, "About a bird.")
    assert first and second
    w.go("/admin/new")
    _write(w, "Linking", "See [[")
    menu, text = w.page.locator("#slash-list"), "() => window._activeEasyMDE.value()"
    menu.wait_for(state="visible")
    # every other post, the newest first
    assert menu.locator("a").all_inner_texts()[:2] == ["Héron story" + tag, "Hydration notes" + tag]
    # narrowed by what is typed, any case, no accents needed
    w.page.keyboard.type("HYDRATION NOTES" + tag)
    assert menu.locator("a").all_inner_texts() == ["Hydration notes" + tag]
    w.page.keyboard.press("Enter")
    assert not menu.count() and w.page.evaluate(text) == f"See [[Hydration notes{tag}]]"
    # Tab does the same, and the cursor is after the link
    w.page.keyboard.type(" and [[heron story" + tag)
    assert menu.locator("a").all_inner_texts() == ["Héron story" + tag]
    w.page.keyboard.press("Tab")
    w.page.keyboard.type("!")
    assert w.page.evaluate(text) == f"See [[Hydration notes{tag}]] and [[Héron story{tag}]]!"
    # a "]]" that's there already isn't doubled
    w.page.evaluate("() => { var m = window._activeEasyMDE; m.value('a ]]'); m.codemirror.setCursor({line: 0, ch: 2}); m.codemirror.focus(); }")
    w.page.keyboard.type("[[")
    menu.wait_for(state="visible")
    w.page.keyboard.press("ArrowDown")
    w.page.keyboard.press("Enter")
    assert w.page.evaluate(text) == f"a [[Hydration notes{tag}]]"
    # nothing found closes it; Esc leaves what was typed
    w.page.evaluate("() => { var m = window._activeEasyMDE; m.value(''); m.codemirror.focus(); }")
    w.page.keyboard.type("[[zzzz")
    assert not menu.count()
    w.page.evaluate("() => { window._activeEasyMDE.value(''); }")
    w.page.keyboard.type("[[Hyd")
    menu.wait_for(state="visible")
    w.page.keyboard.press("Escape")
    assert not menu.count() and w.page.evaluate(text) == "[[Hyd"


def test_double_brackets_suggest_titles_to_link(owner):
    _link_by_title(owner, " (wide)")


def test_double_brackets_suggest_titles_on_a_phone(owner_phone):
    _link_by_title(owner_phone, " (phone)")


def _lists_open_at_the_end_of_a_long_post(w, tag):
    """On a long post's last line, typing scrolls the page to keep the
    cursor clear of the toolbar - the / list, emoji and [[ titles stay
    open beside the cursor, and go once the cursor is scrolled away."""
    assert publish(w, "Rain gauge" + tag, "About rain.")
    w.go("/admin/new")
    _write(w, "Long" + tag, "\n\n".join(f"Paragraph {n}." for n in range(80)))
    w.page.evaluate("() => { var cm = window._activeEasyMDE.codemirror; cm.focus(); cm.setCursor(cm.lineCount(), 0); }")
    menu = w.page.locator("#slash-list")

    def stays_open(typed):
        w.page.keyboard.press("Enter")
        w.page.keyboard.type(typed)
        menu.wait_for(state="visible")
        w.page.wait_for_timeout(400)
        assert menu.is_visible(), typed
        cursor = w.page.evaluate("() => window._activeEasyMDE.codemirror.cursorCoords(null, 'window')")
        box = menu.bounding_box()
        # beside the cursor: just under its line, or just above it
        assert abs(box["y"] - cursor["bottom"]) < 24 or abs(box["y"] + box["height"] - cursor["top"]) < 24, (box, cursor)
        w.page.keyboard.press("Escape")
        assert not menu.count()
    stays_open("/")
    stays_open(":co")
    stays_open("[[Rain")
    # the cursor scrolled out of sight: the list goes
    w.page.keyboard.press("Enter")
    w.page.keyboard.type("/")
    menu.wait_for(state="visible")
    w.page.evaluate("() => window.scrollTo(0, 0)")
    w.page.wait_for_timeout(300)
    assert not menu.count()


def test_lists_stay_open_at_the_end_of_a_long_post(owner):
    _lists_open_at_the_end_of_a_long_post(owner, " (wide)")


def test_lists_stay_open_at_the_end_of_a_long_post_on_a_phone(owner_phone):
    _lists_open_at_the_end_of_a_long_post(owner_phone, " (phone)")


def test_a_spelling_correction_stays_when_the_cursor_was_elsewhere(owner_firefox):
    """Right-click a word on another line than the one being typed on and
    take the browser's correction: the editor keeps it. The browser changes
    the word on the page itself, as here. In Firefox, where a right-click
    doesn't move the cursor by itself."""
    w = owner_firefox
    cm = "document.querySelector('.CodeMirror').CodeMirror"
    w.go("/admin/new")
    _write(w, "Spelling", "First line")
    for _ in range(6):
        w.page.keyboard.press("Enter")
    w.page.keyboard.type("A chainring here")
    w.page.evaluate(cm + ".setCursor({line: 0, ch: 2})")
    w.page.wait_for_timeout(200)
    at = w.page.evaluate(cm + ".charCoords({line: 6, ch: 5}, 'window')")
    w.page.mouse.click(at["left"] + 2, (at["top"] + at["bottom"]) / 2, button="right")
    w.page.wait_for_timeout(200)
    assert w.page.evaluate(cm + ".getCursor().line") == 6
    w.page.evaluate("""() => {
        var line = Array.from(document.querySelectorAll('.CodeMirror-line'))
            .find(function (l) { return l.textContent.indexOf('chainring') > -1; });
        var walk = document.createTreeWalker(line, NodeFilter.SHOW_TEXT), node;
        while ((node = walk.nextNode())) if (node.nodeValue.indexOf('chainring') > -1) break;
        node.nodeValue = node.nodeValue.replace('chainring', 'chain ring');
        document.querySelector('.CodeMirror').CodeMirror.getInputField()
            .dispatchEvent(new InputEvent('input', {bubbles: true, inputType: 'insertReplacementText'}));
    }""")
    w.page.wait_for_timeout(400)
    assert "A chain ring here" in w.page.evaluate(cm + ".getValue()")
