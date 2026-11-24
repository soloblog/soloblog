"""Writing in Chinese, Japanese or Korean: while a word is being composed,
Enter, the arrows and Esc pick and confirm characters - the editor's
title and the Insert search leave them to the input method."""
from conftest import write

# A key pressed while composing, as the browser sends it - Playwright's
# keyboard can't compose
KEY = """(key) => {
    const el = document.activeElement;
    el.dispatchEvent(new KeyboardEvent('keydown', {key, isComposing: true, bubbles: true, cancelable: true}));
    return document.activeElement === el; }"""


def test_enter_in_the_title_confirms_the_word(owner):
    owner.go("/admin/new")
    write(owner, "", "")
    owner.page.evaluate("() => window._activeEasyMDE.titleInput.focus()")
    assert owner.page.evaluate(KEY, "Enter"), "a composed Enter left the title"
    owner.page.keyboard.press("Enter")
    assert owner.page.evaluate("() => document.activeElement.closest('.CodeMirror') !== null")


def test_the_insert_search_while_composing(owner):
    owner.go("/admin/new")
    write(owner, "Composing", "")
    owner.page.evaluate("() => window._activeEasyMDE.openInsert(null)")
    owner.page.wait_for_timeout(300)
    picked = owner.page.locator("#slash-list a[aria-selected=true]").inner_text()
    for key in ("ArrowDown", "Enter", "Escape"):
        owner.page.evaluate(KEY, key)
    assert owner.page.evaluate("() => window._activeEasyMDE.insertOpen()"), "a composed key closed Insert"
    assert owner.page.locator("#slash-list a[aria-selected=true]").inner_text() == picked
    assert owner.page.evaluate("() => window._activeEasyMDE.value()") == ""
    owner.page.keyboard.press("Escape")
    assert not owner.page.evaluate("() => window._activeEasyMDE.insertOpen()")
