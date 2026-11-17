"""The keyboard's way through the editor and the panels: out of the text,
the title first, the list the text points at, focus handed in and back."""
import re

from soloblog.js import read as read_js
from conftest import editor_script


def test_the_editor_text_does_not_trap_the_keyboard(admin):
    html = admin.get("/admin/new").text
    script = editor_script(admin, html)
    # Tab indents, so Esc then Tab has to be the way out
    assert "tabLeaves" in script and "e.key === 'Escape'" in script
    # the title is the first stop in the box and the last out of it
    assert "mde.titleInput" in script


def test_the_insert_list_is_a_listbox_the_text_points_at(admin):
    js = read_js("slash_menu.js")
    assert "setAttribute('role', 'option')" in js
    assert "aria-activedescendant" in js and "aria-controls" in js


def test_slide_over_panels_take_and_return_the_keyboard():
    actions = read_js("actions.js")
    assert "function panelOpened" in actions and "function panelClosed" in actions
    for name in ("pin_location.js", "editor_help.js", "page_helpers.js"):
        js = read_js(name)
        assert "panelOpened" in js or "_panelFrom" in js, name
        assert "panelClosed" in js, name


def test_a_busy_button_gives_the_keyboard_back():
    js = read_js("busy.js")
    assert "_keyHad" in js and "btn.focus(" in js


def test_the_code_box_is_where_the_keyboard_starts(client):
    from soloblog import settings
    settings.set_many({"members_enabled": "1"})
    client.post("/signin", data={"email": "reader@example.com"}, headers={"origin": "http://testserver"})
    r = client.get("/signin/check")
    settings.set_many({"members_enabled": "0"})
    assert r.status_code == 200 and 'name="code"' in r.text
    assert re.search(r"<input[^>]*name=\"code\"[^>]*autofocus|<input[^>]*autofocus[^>]*name=\"code\"", r.text)
