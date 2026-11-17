"""The Go to menu at the toolbar's right end: every section of the post,
in order, and choosing one takes the cursor to its heading - in the
normal editor, side by side, Focus mode and on a phone."""
from conftest import write

FILLER = "\n\n".join(f"Paragraph {n} of words to push the sections apart." for n in range(14))
BODY = (f"Intro.\n\n{FILLER}\n\n## Plans\n\nSection: Pricing\n\n{FILLER}\n\n"
        f"## Kind words\n\nSection: Testimonials\n\n{FILLER}\n\n## Questions\n\nSection: FAQ\n\n{FILLER}\n\n"
        f"## More plans\n\nSection: Pricing\n\n{FILLER}\n")

CURSOR = "() => { const cm = window._activeEasyMDE.codemirror; const c = cm.getCursor(); return [c.line, c.ch, cm.getLine(c.line)]; }"
VISIBLE = """() => { const cm = window._activeEasyMDE.codemirror, c = cm.getCursor();
    const r = cm.charCoords(c, 'window'); return r.top >= 0 && r.bottom <= innerHeight; }"""
BUTTON = ".editor-toolbar button.goto"
ROWS = "#slash-list a"


def _open(w, text=BODY):
    w.go("/admin/new")
    write(w, "Section links", "")
    w.page.evaluate("(t) => window._activeEasyMDE.value(t)", text)
    w.page.wait_for_timeout(500)


def _rows(w):
    return [r.replace("\n", " ") for r in w.page.locator(ROWS).all_inner_texts()]


def _choose(w, n):
    w.page.locator(ROWS).nth(n).click()
    w.page.wait_for_timeout(500)


def _check_menu(w):
    """Open the menu, check its rows, choose the second, and again the last."""
    w.page.locator(BUTTON).click()
    assert w.page.locator(BUTTON).get_attribute("aria-expanded") == "true"
    # one row per section, two of a kind both there, the heading's words beside the kind
    assert _rows(w) == ["Pricing Plans", "Testimonials Kind words", "FAQ Questions", "Pricing More plans"]
    _choose(w, 1)
    assert w.page.locator(ROWS).count() == 0
    assert w.page.locator(BUTTON).get_attribute("aria-expanded") == "false"
    assert w.page.evaluate(CURSOR)[1:] == [0, "## Kind words"]
    assert w.page.evaluate(VISIBLE)
    assert w.page.evaluate("() => document.activeElement.closest('.CodeMirror') !== null")
    # the section the cursor's in is marked
    w.page.locator(BUTTON).click()
    assert w.page.locator(f"{ROWS}[aria-current=true]").inner_text().startswith("Testimonials")
    assert w.page.locator(f"{ROWS}[aria-current=true]").count() == 1
    _choose(w, 3)
    assert w.page.evaluate(CURSOR)[2] == "## More plans" and w.page.evaluate(VISIBLE)


def test_the_menu_goes_to_a_sections_heading(owner):
    _open(owner)
    # not names under the title any more
    assert "Pricing" not in owner.page.locator("#post-pills").inner_text()
    assert "Go to" not in owner.page.locator("#post-pills").inner_text()
    _check_menu(owner)
    # no sideways scrolling from the button
    assert owner.page.evaluate("() => document.documentElement.scrollWidth <= innerWidth")


def test_the_menu_in_side_by_side_and_focus(owner):
    _open(owner)
    owner.page.evaluate("() => EasyMDE.toggleSideBySide(window._activeEasyMDE)")
    owner.page.wait_for_timeout(500)
    _check_menu(owner)
    # the preview follows the cursor to the same heading
    assert owner.page.evaluate(
        """() => { const h = [...document.querySelectorAll('.editor-preview-side h2')].find(x => x.textContent === 'More plans');
                  const r = h.getBoundingClientRect(); return r.bottom > 0 && r.top < innerHeight; }""")
    owner.page.evaluate("() => EasyMDE.toggleSideBySide(window._activeEasyMDE)")
    owner.page.wait_for_timeout(300)
    owner.page.locator(".editor-tabs").get_by_text("Focus", exact=True).first.click()
    owner.page.wait_for_timeout(600)
    assert owner.page.locator(BUTTON).is_visible()
    _check_menu(owner)


def test_the_menu_by_keyboard(owner):
    _open(owner)
    button = owner.page.locator(BUTTON)
    assert button.get_attribute("aria-haspopup") == "listbox"
    button.focus()
    owner.page.keyboard.press("Enter")
    assert button.get_attribute("aria-expanded") == "true"
    # it opens on the section the cursor's in - none yet, so the first
    owner.page.keyboard.press("ArrowDown")
    owner.page.keyboard.press("ArrowDown")
    owner.page.keyboard.press("Enter")
    owner.page.wait_for_timeout(400)
    assert owner.page.evaluate(CURSOR)[2] == "## Questions"
    # Esc closes it and the focus goes back to the button
    button.focus()
    owner.page.keyboard.press("Space")
    assert owner.page.locator(ROWS).count() == 4
    owner.page.keyboard.press("Escape")
    assert owner.page.locator(ROWS).count() == 0
    assert owner.page.evaluate("() => document.activeElement.classList.contains('goto')")
    assert button.get_attribute("aria-expanded") == "false"
    # Esc didn't leave the editor
    assert owner.page.locator(".CodeMirror").first.is_visible()


def test_no_sections_yet(owner):
    _open(owner, "Only plain writing.\n\n## A heading\n\nNot a section.\n")
    owner.page.locator(BUTTON).click()
    assert owner.page.locator("#slash-list").inner_text().startswith("No sections yet")
    assert _rows(owner) == ["Insert a section…"]
    owner.page.locator(ROWS).click()
    owner.page.wait_for_timeout(300)
    # Insert, at its Sections group
    assert owner.page.locator(BUTTON).get_attribute("aria-expanded") == "false"
    assert owner.page.locator("#slash-list .menu-title").all_inner_texts() == ["Sections"]
    assert "Hero" in owner.page.locator("#slash-list").inner_text()
    assert "Bold" not in owner.page.locator("#slash-list").inner_text()


def _style(w, rows):
    w.go("/admin/settings?tab=editor")
    w.page.locator(f"input[name=editor_toolbar_rows][value={rows}]").check()
    w.page.evaluate("() => document.querySelector(\"form[hx-post='/admin/settings/editor']\").requestSubmit()")
    w.page.wait_for_load_state("networkidle")
    w.page.wait_for_timeout(300)


def test_the_menu_on_each_toolbar_style(owner):
    """Classic menus and Icons have it at the right end; Minimal has no
    toolbar at all."""
    style = lambda rows: _style(owner, rows)  # noqa: E731
    try:
        for rows in ("menus", "one"):
            style(rows)
            _open(owner)
            assert owner.page.evaluate('() => window.EDITOR_PREFS.rows') == rows
            after = owner.page.evaluate(
                """() => { const kids = [...document.querySelector('.editor-toolbar').children].filter(el => !el.hidden);
                           return kids.slice(kids.findIndex(el => el.classList.contains('goto')) + 1)
                                      .map(el => el.classList[0]); }""")
            # Icons: just before Insert (and the ⋯ that may follow); Classic menus: last of all
            assert after == (["insert"] if rows == "one" else []) or (rows == "one" and after[:1] == ["insert"])
            _check_menu(owner)
    finally:
        style("one")


def test_classic_menus_has_one_sections_and_one_go_to(owner):
    """Sections inserts one; Go to jumps to one - two buttons, two words."""
    try:
        _style(owner, "menus")
        _open(owner)
        words = [w.strip() for w in owner.page.locator(".editor-toolbar .toolbar-word").all_inner_texts()]
        assert words.count("Sections") == 1 and words.count("Go to") == 1
        assert owner.page.locator(".editor-toolbar button.goto").inner_text().strip() == "Go to"
        # Sections is the menu that adds one
        owner.page.locator(".editor-toolbar [data-section=Sections]").click()
        assert "Hero" in owner.page.locator(".editor-toolbar .easymde-dropdown-content:visible").inner_text()
    finally:
        _style(owner, "one")


def test_go_to_a_section_from_the_slash_menu_with_no_toolbar(owner):
    """None hides the toolbar on a wide screen: / still opens Go to, which
    inserts nothing and moves the cursor to the section chosen."""
    try:
        _style(owner, "none")
        _open(owner)
        assert not owner.page.locator(BUTTON).is_visible()
        owner.page.locator(".CodeMirror").first.click()
        owner.page.keyboard.press("Control+Home")
        owner.page.keyboard.press("End")
        before = owner.page.evaluate("() => window._activeEasyMDE.value()")
        owner.page.keyboard.type("\n\n")
        owner.page.wait_for_timeout(400)
        owner.page.keyboard.type("/go")
        owner.page.wait_for_timeout(300)
        # found by "go",
        names = owner.page.locator("#slash-list a").all_inner_texts()
        assert any("Go to a section" in n for n in names), names
        owner.page.locator("#slash-list a", has_text="Go to a section").click()
        owner.page.wait_for_timeout(400)
        # the typed words are gone and nothing was put in the text
        text = owner.page.evaluate("() => window._activeEasyMDE.value()")
        assert "/go" not in text and text == before.replace("Intro.", "Intro.\n\n", 1)
        # the same list, at the cursor, worked from the keyboard
        assert _rows(owner) == ["Pricing Plans", "Testimonials Kind words", "FAQ Questions", "Pricing More plans"]
        owner.page.keyboard.press("ArrowDown")
        owner.page.keyboard.press("ArrowDown")
        owner.page.keyboard.press("Enter")
        owner.page.wait_for_timeout(400)
        assert owner.page.locator(ROWS).count() == 0
        assert owner.page.evaluate(CURSOR)[1:] == [0, "## Questions"] and owner.page.evaluate(VISIBLE)
        # "section" finds it, and Insert's sections too; Insert's own list leaves it out
        _open(owner)
        owner.page.locator(".CodeMirror").first.click()
        owner.page.keyboard.press("Control+Home")
        owner.page.keyboard.press("End")
        owner.page.keyboard.type("\n\n/section")
        owner.page.wait_for_timeout(300)
        found = owner.page.locator("#slash-list a").all_inner_texts()
        assert any("Go to a section" in n for n in found) and any("Hero" in n for n in found), found
        # Enter adds a section, as it did before Go to was there
        assert owner.page.locator("#slash-list a[aria-selected=true]").count() == 1
        assert "Go to a section" not in owner.page.locator("#slash-list a[aria-selected=true]").inner_text()
        owner.page.keyboard.press("Escape")
        owner.page.evaluate("() => window._activeEasyMDE.openInsert(null)")
        owner.page.wait_for_timeout(300)
        assert "Go to a section" not in owner.page.locator("#slash-list").inner_text()
    finally:
        _style(owner, "one")


def test_the_menu_on_a_phone(owner_phone):
    w = owner_phone
    _open(w)
    w.page.locator(".CodeMirror").first.tap()
    w.page.wait_for_timeout(500)
    button = w.page.locator(".editor-phonebar button[data-id=sections-jump]")
    # just its icon, named for a screen reader
    assert button.get_attribute("aria-label") == "Go to a section"
    assert button.inner_text().strip() == ""
    box = button.bounding_box()
    assert box["width"] >= 44 and box["height"] >= 44 and box["x"] + box["width"] <= 375
    button.tap()
    w.page.wait_for_timeout(300)
    assert _rows(w) == ["Pricing Plans", "Testimonials Kind words", "FAQ Questions", "Pricing More plans"]
    # a sheet over the bar: the width of the screen
    sheet = w.page.locator("#slash-list").evaluate("el => el.closest('.fixed').getBoundingClientRect().toJSON()")
    assert sheet["left"] >= 0 and sheet["right"] <= 375
    w.page.locator(ROWS).nth(2).tap()
    w.page.wait_for_timeout(500)
    assert w.page.locator("#slash-list").count() == 0
    assert w.page.evaluate(CURSOR)[2] == "## Questions" and w.page.evaluate(VISIBLE)
    assert w.page.evaluate("() => document.documentElement.scrollWidth <= innerWidth")
