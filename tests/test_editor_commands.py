"""The editor's command list (editor_config.COMMANDS) is what the toolbar,
its menus, the slash menu, the shortcuts and the help are made from - so
a command missing a part shows up here, not as a blank button."""
from pathlib import Path
import html
import json
import os
import re

from soloblog import editor_config, editor_icons, sections
from soloblog.routes import editor

COMMANDS = editor_config.COMMANDS

# keys a browser keeps for itself, or that people know as the browser's:
# new tab/window, print, find, history, bookmarks, the developer tools,
# Firefox's Reader view (F9) and console (Ctrl+Shift+K) - and Save,
# which the editor's page answers itself
BROWSER_KEYS = {
    "F9", "F11", "F12", "Cmd-T", "Cmd-W", "Cmd-N", "Cmd-P", "Cmd-F", "Cmd-L", "Cmd-D", "Cmd-H", "Cmd-J",
    "Cmd-R", "Cmd-U", "Cmd-O", "Cmd-G", "Cmd-S", "Shift-Cmd-B", "Shift-Cmd-C", "Shift-Cmd-D", "Shift-Cmd-H",
    "Shift-Cmd-I", "Shift-Cmd-J", "Shift-Cmd-K", "Shift-Cmd-M", "Shift-Cmd-N", "Shift-Cmd-O", "Shift-Cmd-P",
    "Shift-Cmd-T", "Shift-Cmd-W", "Shift-Cmd-Delete",
}


def test_every_command_has_every_part():
    places = {"toolbar", "more", "slash"}
    for c in COMMANDS:
        assert c["label"] and c["label"][0].isupper(), c["id"]
        assert c["about"] and len(c["about"]) < 60 and not c["about"].endswith("."), c["id"]
        assert c["group"] in editor_config.GROUPS, c["id"]
        assert c["icon"] in editor_icons.ICONS, c["id"]
        assert c["place"] in places, c["id"]
        # everything is in the slash menu but Undo and Redo - Ctrl+Z is
        # what people reach for - and Insert, which opens that list
        assert c["slash"] or c["id"] in editor_config.BUILT_IN_KEYS | {"insert"}, c["id"]


def test_ids_labels_and_icons_are_each_used_once():
    for field in ("id", "icon"):
        values = [c[field] for c in COMMANDS]
        assert len(values) == len(set(values)), field
    # every label once
    from collections import Counter
    assert all(n == 1 for label, n in Counter(c["label"] for c in COMMANDS).items())


def test_every_command_does_something():
    actions = editor.EDITOR_INIT_JS[editor.EDITOR_INIT_JS.index("var ACTIONS = {"):]
    actions = actions[:actions.index("\n  };\n")]
    for c in COMMANDS:
        # a Landing page's sections add their markdown (sections.REGISTRY)
        assert f"'{c['id']}':" in actions or c["snippet"], c["id"]
    assert "if (c.snippet) ACTIONS[c.id] = block(c.snippet);" in editor.EDITOR_INIT_JS


def test_shortcuts_are_unique_fire_and_leave_the_browser_alone():
    keys = [c["keys"] for c in COMMANDS if c["keys"]]
    assert len(keys) == len(set(keys))
    for k in keys:
        # CodeMirror only matches Shift, then Cmd, then Alt
        assert re.fullmatch(r"(Shift-)?Cmd-(Alt-)?[^-]+", k), k
        assert k not in BROWSER_KEYS, k


def test_toolbar_defaults_come_from_the_list():
    on_toolbar = {c["id"] for c in COMMANDS if c["place"] == "toolbar"}
    assert on_toolbar == set(editor_config.DEFAULT_ORDER)
    # every button Settings > Editor offers is a command
    assert set(editor_config.ALL_KEYS) <= set(editor_config.COMMAND)


def test_the_help_covers_every_command_and_shortcut():
    import fasthtml.common as fh
    # every command is in the Help panel: an example that writes it, or
    # one of the editor's own buttons - Help and Keyboard shortcuts are
    # the panel and its last section
    covered = {i for _, _, entries in editor._HELP for e in entries for i in e[3]}
    covered |= set(editor._HELP_EDITOR) | {"guide", "shortcuts"}
    assert covered == set(editor_config.COMMAND), set(editor_config.COMMAND) ^ covered
    panel = fh.to_xml(fh.Div(*editor.EditorHelpParts()))
    for _, _, entries in editor._HELP:
        for name, example, *_ in entries:
            assert html.escape(name, quote=False) in panel and html.escape(example, quote=False) in panel, name
    for c in editor_config.COMMANDS:
        if c["keys"]:
            assert f'data-mac="{editor_config.key_text(c["keys"], mac=True)}"' in panel, c["id"]
    rows = {label: (win, mac) for label, win, mac in editor._SHORTCUT_KEYS}
    assert rows["Save"] == ("Ctrl+S", "Cmd+S")
    assert rows["Strikethrough"] == ("Ctrl+Shift+X", "Cmd+Shift+X")
    assert rows["Heading"] == ("Ctrl+Alt+2", "Cmd+Alt+2")
    assert rows["Help"] == ("Ctrl+/", "Cmd+/")
    assert {c["label"] for c in COMMANDS if c["keys"]} <= set(rows)
    # a notice for a setting that's off links to "it", the setting
    notes = [e[2] for _, _, entries in editor._HELP for e in entries if isinstance(e[2], tuple)]
    assert notes and all(link == "Turn it on" for _, link, _ in notes)


def test_the_icons_are_drawn_in_the_text_colour():
    for name in editor_icons.ICONS:
        svg = editor_icons.svg(name)
        assert svg.startswith("<svg") and 'stroke="currentColor"' in svg and "class=\"editor-icon\"" in svg
        assert "<script" not in svg and not re.search(r"\son\w+=", svg), name


def test_toolbar_menus_close_on_a_second_click_and_fit():
    # EasyMDE's onclick focuses a menu's button, which reopened it - the
    # click after a closing mousedown is swallowed (routes/editor.py)
    js = editor.EDITOR_INIT_JS
    assert "closing = dropdown;" in js and "}, true);" in js[js.index("closing = dropdown;"):]
    # all: unset dropped border-box, so full-width menu items stuck out
    css = Path("static/css/input.css").read_text(encoding="utf-8")
    assert "all: unset; box-sizing: border-box;" in css


def test_one_bar_over_the_text(admin):
    # between the title and the text: the tabs' slot, the save dot with the
    # status slot, the post's actions (behind ⋯ on a phone) and Save
    html = admin.get("/admin/new").text
    bar = html[html.index('id="editor-bar"'):html.index('id="body-editor"')]
    assert html.index('name="title"') < html.index('id="editor-bar"') < html.index('id="body-editor"')
    for part in ('id="editor-views"', "data-save-dot", 'id="save-status"', 'aria-label="Discard"',
                 'aria-label="Settings"', 'aria-label="Help"', "btn btn-primary btn-sm"):
        assert part in bar, part
    # nothing else on the page is a second Save
    assert html.count('type="submit" class="btn btn-primary') == 1
    css = Path("static/css/input.css").read_text(encoding="utf-8")
    # the toolbar's reset left daisyUI's own links alone
    assert ".editor-toolbar a:where(:not(.btn))" in css and ".editor-toolbar a {" not in css
    # it sticks flush under the header - no strip, no copy of the buttons
    assert "editor-save-row" not in editor.EDITOR_INIT_JS and "0.5rem)" not in html.split("--editor-sticky:")[1][:60]


def test_the_recommended_toolbar_is_fifteen_buttons_in_sections():
    # headings, bold, italic and Clear formatting | lists and quote |
    # links, images and Insert | Undo and Redo - Preview, Focus mode and
    # Help are on the bar over it, ⋯ only for any that don't fit (fitToolbar)
    assert len(editor_config.DEFAULT_ORDER) == 15 and "clean-block" in editor_config.DEFAULT_ORDER and editor_config.DEFAULT_ORDER[-2:] == ["undo", "redo"]
    assert not {"preview", "fullscreen", "side-by-side", "guide"} & set(editor_config.DEFAULT_ORDER)
    assert "function fitToolbar" in editor.EDITOR_INIT_JS
    assert editor_config.DEFAULT_ORDER == editor_config.pinned_from_setting(",".join(editor_config.DEFAULT_ORDER))


def test_toolbar_buttons_stay_in_their_sections():
    # no heading menu any more: the levels are ordinary Text buttons, and
    # Insert is the one that's always there
    assert "headings" not in editor_config.MENUS and "headings" not in editor_config.ORDERABLE_KEYS
    assert "insert" not in editor_config.ALL_KEYS and "insert" in editor_config.ORDERABLE_KEYS
    assert {"paragraph", "heading", "subheading", "small-heading"} <= set(editor_config.ALL_KEYS)
    assert "headingsMenu" not in editor.EDITOR_INIT_JS
    # a saved order comes back a section at a time, sections in their
    # fixed order, each section's buttons in the order chosen; an old
    # "headings" is dropped, and Insert added if it's missing
    assert editor_config.pinned_from_setting("link,undo,italic,headings,bold,quote") == \
        ["italic", "bold", "quote", "link", "insert", "undo"]
    groups = [editor_config.GROUP_OF[k] for k in editor_config.pinned_from_setting(",".join(editor_config.ALL_KEYS[::-1]))]
    assert groups == sorted(groups, key=editor_config.GROUPS.index)


def test_settings_orders_the_toolbar_by_section(admin):
    html = admin.get("/admin/settings?tab=editor").text
    assert 'id="toolbar-order-list"' in html and "data-sections=" in html and 'data-always="insert"' in html
    assert 'name="tb_insert"' not in html and 'name="tb_heading"' in html
    # a saved order is sorted into sections, whatever order it was sent in
    admin.post("/admin/settings/editor", data={
        "editor_toolbar": "gallery,bold,heading", "tb_gallery": "1", "tb_bold": "1", "tb_heading": "1",
        "declared_fields": "editor_toolbar,tb_gallery,tb_bold,tb_heading"})
    from soloblog import settings
    assert settings.get_all()["editor_toolbar"] == "bold,heading,gallery,insert"


def test_the_phone_bar_follows_its_setting(admin):
    import json
    from soloblog import settings
    # On a phone: your buttons (the default), sections or none - anything
    # else (an old "match", a typed-in value) is your buttons
    assert editor_config.PHONE_BARS == ("buttons", "sections", "none")
    assert settings.DEFAULTS["editor_phone_bar"] == "buttons"
    assert "The same as the toolbar" not in admin.get("/admin/settings?tab=editor").text
    s = {"editor_phone_bar": "match", "editor_toolbar_rows": "one"}
    assert editor_config.phone_bar(s) == "buttons"
    assert editor_config.phone_bar({**s, "editor_toolbar_rows": "menus"}) == "buttons"
    assert editor_config.phone_bar({**s, "editor_phone_bar": "sections"}) == "sections"
    assert editor_config.phone_bar({**s, "editor_phone_bar": "nonsense"}) == "buttons"
    # Undo, Redo and Help are buttons like the rest: in the row when
    # they're yours, and always in their sections - nothing fixed at the
    # bar's end but All
    assert editor_config.PHONE_SECTIONS == ["Text", "Blocks", "Insert", "Sections", "History", "View", "Help"]
    js = editor.EDITOR_INIT_JS
    bar = js[js.index("var MODE = PREFS.phone"):js.index("document.body.appendChild(phoneBar);")]
    assert "openSection" in bar and "openAll" in bar and "oneTap" not in js and "var SHEETS" not in js
    assert "MODE !== 'none' && PHONE.matches" in js
    for icon in editor_config.SECTION_ICONS.values():
        assert icon in editor_icons.ICONS, icon
    # every command a phone can run has something to do
    actions = js[js.index("var ACTIONS = {"):js.index("var PREFS = window.EDITOR_PREFS")]
    for _, ids in editor_config.SECTION_MENUS:
        for cid in ids:
            assert f"'{cid}'" in actions or editor_config.COMMAND[cid]["snippet"], cid
    # saved, and handed to the editor
    before = settings.get("editor_phone_bar")
    try:
        admin.post("/admin/settings/editor", headers={"hx-request": "true"},
                   data={"editor_phone_bar": "sections", "declared_fields": "editor_phone_bar"})
        prefs = json.loads(admin.get("/admin/new").text.split("window.EDITOR_PREFS = ")[1].split(";</script>")[0])
        assert prefs["phone"] == "sections" and prefs["phoneSections"] == editor_config.PHONE_SECTIONS
        admin.post("/admin/settings/editor", headers={"hx-request": "true"},
                   data={"editor_phone_bar": "<b>", "declared_fields": "editor_phone_bar"})
        assert settings.get("editor_phone_bar") == "buttons"
    finally:
        settings.set_many({"editor_phone_bar": before})


def test_icons_sections_end_with_the_rest():
    # each Icons section ends with a ▾ for what you didn't choose from
    # it, and ⋯ has a copy of all of it for when it doesn't fit
    js = editor.EDITOR_INIT_JS
    assert "'data-rest': group" in js and "'More in ' + group" in js
    assert "hasAttribute('data-rest')" in js  # fitToolbar


def test_views_row_edges_and_the_header(admin):
    from soloblog import app as app_module
    js = editor.EDITOR_INIT_JS
    # Write / Preview and Focus mode over the toolbar, at the start of the
    # page's row once pinned, side by side only in focus mode
    assert "['focus', 'Focus']" in js and "getElementById('editor-views')" in js and "sideBySideFullscreen" not in js
    # the Insert list kept inside the editor
    assert "closest('.EasyMDEContainer').getBoundingClientRect()" in editor.SLASH_MENU_JS
    # tooltips at the screen's edge turn inwards; the header is measured as it changes
    shared = "\n".join(app_module.SHARED_SCRIPTS)
    assert "function _fitTooltip" in shared and "new ResizeObserver(syncChromeOffsets)" in shared
    # the admin menu keeps its own width
    html = admin.get("/admin/posts").text
    assert "h-dvh w-64 bg-base-100" in html and "flex-1 min-h-0 overflow-y-auto overscroll-contain" in html


def test_classic_menus_have_every_command_once(admin):
    import json
    from soloblog import settings
    # a menu per section, in GROUPS order, together every command but
    # Insert's own list - which is what the Insert menu is
    assert [group for group, _ in editor_config.SECTION_MENUS] == editor_config.GROUPS
    ids = [cid for _, section in editor_config.SECTION_MENUS for cid in section]
    assert sorted(ids) == sorted(c["id"] for c in COMMANDS if c["id"] != "insert")
    assert "PREFS.rows === 'menus'" in editor.EDITOR_INIT_JS and "data-section" in editor.EDITOR_INIT_JS
    # an unknown style is Icons; Classic menus is saved and reaches the editor
    assert editor_config.toolbar_style("all") == "one" and editor_config.toolbar_style("menus") == "menus"
    before = settings.get("editor_toolbar_rows")
    try:
        admin.post("/admin/settings/editor", headers={"hx-request": "true"},
                   data={"editor_toolbar_rows": "menus", "declared_fields": "editor_toolbar_rows"})
        page = admin.get("/admin/new").text
        prefs = json.loads(page.split("window.EDITOR_PREFS = ")[1].split(";</script>")[0])
        assert prefs["rows"] == "menus" and 'data-editor-toolbar="menus"' in page
        assert [s["name"] for s in prefs["sections"]] == editor_config.GROUPS
        # Settings shows the choice, and hides the button lists it doesn't use
        html = admin.get("/admin/settings?tab=editor").text
        assert 'value="menus" checked' in html or 'checked value="menus"' in html or \
            re.search(r'value="menus"[^>]*checked', html)
        assert 'data-shown-for="editor_toolbar_rows=one;editor_phone_bar=buttons"' in html
    finally:
        settings.set_many({"editor_toolbar_rows": before})


def test_focus_mode_typewriter_and_fade(admin):
    import json
    from soloblog import settings
    # both on out of the box, each its own switch in Settings > Editor
    page = admin.get("/admin/new").text
    prefs = json.loads(page.split("window.EDITOR_PREFS = ")[1].split(";</script>")[0])
    assert prefs["typewriter"] is True and prefs["fade"] == "paragraph" and prefs["focusToolbar"] == "all"
    assert "data-typewriter" in page and 'data-fade="paragraph"' in page and "data-focus-quiet" in page
    js = editor.EDITOR_INIT_JS
    assert "addLineClass(n, 'wrap', 'cm-para-now')" in js and "focusText.scrollTo(null" in js
    assert "className: 'cm-dim'" in js and "cursorBlinkRate" in js
    before = {k: settings.get(k) for k in ("editor_typewriter", "editor_fade", "editor_focus_toolbar")}
    try:
        admin.post("/admin/settings/editor", headers={"hx-request": "true"},
                   data={"editor_fade": "off", "editor_focus_toolbar": "none",
                         "declared_fields": "editor_typewriter,editor_fade,editor_focus_toolbar"})
        page = admin.get("/admin/new").text
        prefs = json.loads(page.split("window.EDITOR_PREFS = ")[1].split(";</script>")[0])
        assert prefs["typewriter"] is False and prefs["fade"] == "off" and prefs["focusToolbar"] == "none"
        assert "PREFS.focusToolbar !== 'none'" in editor.EDITOR_INIT_JS
        assert "data-typewriter" not in page and "data-fade" not in page and "data-focus-quiet" not in page
        admin.post("/admin/settings/editor", headers={"hx-request": "true"},
                   data={"editor_fade": "sentence", "editor_focus_toolbar": "toolbar",
                         "declared_fields": "editor_fade,editor_focus_toolbar"})
        page = admin.get("/admin/new").text
        # the old "hide just the toolbar" is now "hide everything"
        assert 'data-fade="sentence"' in page and "data-focus-quiet" in page
        admin.post("/admin/settings/editor", headers={"hx-request": "true"},
                   data={"editor_fade": "loud", "declared_fields": "editor_fade"})
        assert settings.get("editor_fade") == "paragraph"
    finally:
        settings.set_many(before)


def test_focus_mode_sessions_and_text_size():
    # in Focus mode's bar: a writing session (a time or a number of
    # words, kept for the tab) and the writing's size (kept per browser)
    js = editor.EDITOR_INIT_JS
    for part in ("'25 minutes'", "'500 words'", "'End session'", "'Goal reached · '", "sessionStorage",
                 "'focus-session-custom'", "'Pause'", "'Resume'", "'Paused · '",
                 "'Smaller text'", "'Larger text'", "'Reset text size'", "bg-base-content/30",
                 "localStorage.setItem('focus-text-size'", "--focus-scale"):
        assert part in js, part
    assert "if (sessionTick) sessionTick(n);" in js  # the status line keeps it up to date
    # your own length is always in the menu - a Custom… step closed it
    draw = js[js.index("var drawMenu = function"):js.index("var sessionButton")]
    assert "'Custom…'" not in js and "panel.appendChild(customForm());" in draw
    for icon in ("timer", "a-arrow-down", "a-arrow-up"):
        assert icon in editor_icons.ICONS


def test_focus_mode_one_bar_and_the_corner_dot(admin):
    import json
    # one bar on a wide screen, the caret coloured
    page = admin.get("/admin/new").text
    prefs = json.loads(page.split("window.EDITOR_PREFS = ")[1].split(";</script>")[0])
    assert prefs["focusBars"] == "one" and "data-caret" in page
    js = editor.EDITOR_INIT_JS
    assert "var mergeBars = function" in js and "editor-focus-dot" in js and "data-focus-one-bar" in js
    assert "in-data-[focus-one-bar]:hidden" in page
    # reading the preview, a second without the mouse sends the bars away
    assert "var restIdle = function" in js and "mde.isPreviewActive()" in js
    # a custom session's row sits under the list, not in daisyUI's menu
    assert "editor-session-custom" in js and "count.inputMode = 'numeric'" in js
    # one bar, and a coloured caret, are no longer choices
    assert 'name="editor_focus_bars"' not in admin.get("/admin/settings?tab=editor").text


def test_undo_and_redo_are_greyed_out_with_nothing_to_undo_or_redo():
    # the toolbar, its menus and ⋯, and a phone's bar - kept in step with
    # CodeMirror's own history as it changes (checked in a browser too)
    js = editor.EDITOR_INIT_JS
    assert "historySize()" in js and "on('changes', syncHistory)" in js
    for where in (".editor-toolbar button.", "-more", '.editor-phonebar [data-id="'):
        assert where in js[js.index("function syncHistory"):], where


def test_insert_sits_at_the_toolbars_right_end():
    # set apart by its divider and a space, and never folded into ⋯ -
    # the rest fold first (checked in a browser at the widths that fold)
    js = editor.EDITOR_INIT_JS
    build = js[js.index("function buildToolbar"):js.index("function daisyTooltips")]
    assert "return id !== 'insert'" in build and build.index("bar.push(goToButton(), item('insert'))") > build.index("var last")
    # the divider before Go to (which is just before Insert) takes the space
    assert "insertGap.classList.add('ms-auto!')" in js and "goToBtn.previousElementSibling" in js
    assert "items[i] === insertBtn || items[i] === goToBtn || items[i] === insertGap) continue" in js


def test_the_slash_menu_fits_the_window():
    # in a short window it ran off the top or bottom: now below or above,
    # whichever has more room, and no taller - the list scrolls inside
    # (checked in a browser at 420 and 300 px tall)
    js = editor.SLASH_MENU_JS
    place = js[js.index("function place()"):js.index("function draw()")]
    assert "roomAbove > roomBelow" in place and "listEl.style.maxHeight = Math.max(96" in place
    assert "vv.offsetTop + vv.height" in place  # not under a phone's keyboard


def test_focus_modes_bars_stay_away_until_wanted():
    # the mouse anywhere brought them back, and Shift+arrows did; a phone
    # never sent them away (checked in a browser, desktop and phone)
    js = editor.EDITOR_INIT_JS
    quiet = js[js.index("var MOUSE = matchMedia"):js.index("// the Classic") if "// the Classic" in js else None]
    assert "e.clientY > (reach || 120) + 24) return" in quiet
    assert "cm.somethingSelected() && byPointer" in quiet
    assert "/^\\+(input|delete)/.test(change.origin" in quiet
    assert "top < lastTop - 40" in quiet


def test_a_phone_has_focus_mode_beside_write_and_preview():
    # it was hidden on a phone for want of room; on a narrow one it's its
    # icon (checked in a browser: 412, 375 and 320 px, Save in view)
    css = Path("static/css/input.css").read_text(encoding="utf-8")
    phone = css[css.index("/* a phone: the tabs closer together"):]
    assert '.tab[data-mode="focus"] { display: none; }' not in phone[:phone.index("}\n") + 2]
    js = editor.EDITOR_INIT_JS
    # a phone shows them as icons - room for the post's buttons beside Save
    assert "sm:hidden group-data-[icons]/tabs:inline" in js and "max-sm:sr-only" in js
    # Write and Preview too, so the three look alike
    assert "{ write: 'pencil', preview: 'eye', side: 'columns-2', focus: 'maximize-2' }" in js
    # in the fixed part of the editor's settings, in its kept script
    script = editor.EDITOR_JS
    for icon in ("pencil", "eye", "maximize-2", "columns-2"):
        assert f'"{icon}": "<svg' in script, icon


def test_a_swipe_across_alls_grid_goes_to_the_tab_beside():
    # checked in a browser: left and right, a small move does nothing,
    # and it stops at the last tab
    js = editor.EDITOR_INIT_JS
    sheet = js[js.index("var openAll = function"):js.index("var barButton = function")]
    assert "addEventListener('touchend'" in sheet and "Math.abs(dx) >= 48" in sheet


def test_a_phones_one_plus_opens_every_section():
    # no separate Insert on a phone's row: the + at its end opens All's
    # tabs, at Insert (checked in a browser)
    js = editor.EDITOR_INIT_JS
    assert "PHONE_SKIP.indexOf(id) === -1 && id !== 'insert'" in js
    assert "barButton(phoneBar, 'all', COMMANDS.insert.icon, 'All', openAll, true)" in js
    assert "names.indexOf('Insert')" in js


def test_a_touch_screen_gets_a_resize_grip_a_thumb_can_hold():
    # the browser's own corner is too small to drag on a phone (checked in
    # a browser: 44 px, a drag makes the box taller, none on a computer)
    js = editor.EDITOR_INIT_JS
    assert "hidden pointer-coarse:flex absolute bottom-0 right-0 z-10 size-11" in js
    assert "Math.max(300, from.h + e.clientY - from.y)" in js and "pointer-coarse:resize-none!" in js


def test_focus_mode_has_the_title_as_a_heading_you_type_into():
    # checked in a browser: kept in step with the title field both ways,
    # Enter goes on to the writing, it survives everything being deleted,
    # and leaves with Focus mode; the bar no longer repeats it
    js = editor.EDITOR_INIT_JS
    assert "heading.placeholder = 'Title'" in js and "cmFocus.addLineWidget(0, heading, { above: true })" in js
    assert "titleField.dispatchEvent(new Event('input', { bubbles: true }))" in js
    assert "focusTitle.textContent" not in js


def test_a_reached_goal_stays_in_the_palettes_success_colour():
    # it reset after 8 seconds; now it stays until the session's ended
    # (checked in a browser: still there after 9 s, counting on)
    js = editor.EDITOR_INIT_JS
    tick = js[js.index("sessionTick = function"):js.index("var panel = document.createElement('div')")]
    assert "if (session.done)" in tick and "line.classList.add('bg-success')" in tick
    assert "sessionText.classList.add('text-success')" in tick and "setTimeout(function () {\n          doneAt" not in js
    assert "motion-safe:shadow-[0_0_12px_var(--color-success)]" in tick
    # the palette's colour, never a fixed one
    assert not re.search(r"#[0-9a-fA-F]{3,6}\b|rgb\(", tick)
    assert "statusEls.words.classList.toggle('text-success', !!reached)" in js


def test_focus_modes_views_sit_on_the_left_by_the_way_out():
    # with the title gone from the bar, Write / Preview / Side by side
    # moved left, by ✕ (checked in a browser at 1280 px)
    js = editor.EDITOR_INIT_JS
    assert "if (want) focusTitle.before(tabsEl)" in js and "focusTitle.after(tabsEl)" not in js


def test_focus_modes_counts_sit_in_the_middle_of_its_bar():
    # the words, read time, words today and a session's progress, centred
    # (checked in a browser at 640 to 1152 px: centred, clear of both sides)
    js = editor.EDITOR_INIT_JS
    assert "sm:absolute sm:left-1/2 sm:-translate-x-1/2" in js
    assert "focusMiddle.appendChild(focusWords)" in js and "focusMiddle.appendChild(sessionText)" in js


def test_post_settings_sits_beside_the_editor_where_theres_room(admin):
    # a rail on the right, always there like the admin's on the left; a
    # sidebar elsewhere and in Focus mode, changing at once (checked in a
    # browser: docked at 1440 and 1600 px, a sidebar at 1280)
    js = editor.PIN_LOCATION_JS
    place = js[js.index("function placePostSettings"):]
    # a full-height rail on the right of the admin's frame, where the
    # editor keeps 50rem between it and the admin's rail
    assert "window.innerWidth - left - 22.5 * rem >= 50 * rem" in place
    assert "toggleAttribute('data-settings-docked', dock)" in place
    # straight after the page's column, not at the screen's far edge
    # (checked in a browser at 1440 and 1600 px: its left edge on the column's right)
    assert "_dockBeside(panel, dock);" in place and "'top-12'" in js
    assert "!document.documentElement.hasAttribute('data-focus-mode')" in place
    assert "panel.style.transition = 'none'" in place and "b.hidden = dock" in place
    assert "localStorage" not in js
    assert "if (panel.hasAttribute('data-docked')) return;" in js
    assert "if (e.key === 'Escape' && !postSettingsDocked() && !document.querySelector('dialog[open], :popover-open'))" in js
    page = admin.get("/admin/new").text
    inner = page[page.rindex("<", 0, page.index('id="post-settings"')):page.index(">", page.index('id="post-settings"'))]
    assert "data-scroll-hint" in inner and "overflow-y-auto" in inner
    card = page[page.rindex("<", 0, page.index('id="post-settings-panel"')):page.index(">", page.index('id="post-settings-panel"'))]
    assert "overflow-hidden" in card and "overflow-y-auto" not in card
    # loading an old version closes a sidebar, to show the text - not a side panel
    assert "!postSettingsDocked()) togglePostSettings(false)" in editor.REVISIONS_JS


def test_the_whole_dots_menu_moves_when_focus_modes_bars_part():
    # the menu moved without its ⋯ button, which was left by the views - by
    # Preview on a phone - once a wide Focus mode window narrowed (checked
    # in a browser: 1280 to 573 px, ⋯ beside Save again)
    js = editor.EDITOR_INIT_JS
    merge = js[js.index("var mergeBars = function"):js.index("onWidth(mergeBars)")]
    assert "actions && actions.parentElement" in merge


def test_focus_is_a_switch_beside_the_three_views():
    # it disappeared in Focus; then it was a fourth tab; it's a switch:
    # filled while on, never underlined - Write, Preview or Side by side
    # keep the underline for the view (checked in a browser, 1280 and 412)
    css = Path("static/css/input.css").read_text(encoding="utf-8")
    assert '.tab[data-mode="focus"] { display: none; }' not in css
    js = editor.EDITOR_INIT_JS
    sync = js[js.index("var syncTabs = function"):js.index("var viewsSlot")]
    assert "tab.classList.toggle('bg-base-300', on)" in sync and "aria-pressed" in sync
    assert "mde.isFullscreenActive() ? 'focus' : 'write'" not in js


def test_focus_is_one_bar_at_every_width_folding_what_doesnt_fit():
    # three rows of bars below 1,152 px; now one, with the toolbar (checked
    # in a browser from 320 to 1280 px: never overflowing, the counts last)
    js = editor.EDITOR_INIT_JS
    assert "wideEnough" not in js and "var want = PREFS.focusBars === 'one' && mde.isFullscreenActive() && !!bar" in js
    fit = js[js.index("var fitFocusBar = function"):js.index("// Focus mode, as writing apps") if "// Focus mode, as writing apps" in js else None]
    order = [fit.index(part) for part in ("focusMiddle.setAttribute('data-flow'", "toolFolds.forEach",
                                           "tabsBox.setAttribute('data-icons'", "focusWords.setAttribute('data-short'",
                                           "focusMiddle.hidden = true")]
    assert order == sorted(order)
    assert "toolFolds = [[browserBars], [smaller, sizeReset, larger], [sessionMenu]]" in js
    # folded into ⋯, a tool says its name
    assert "[[data-row-menu]_&]:inline" in js
    # Focus's tab has its own icon, not full screen's
    assert "focus: 'maximize-2'" in js and "side: 'columns-2'" in js


def test_an_empty_posts_hint_sits_under_focus_s_title():
    js = editor.EDITOR_INIT_JS
    assert "[&_.CodeMirror-placeholder]:top-(--title-h)!" in js


def test_the_title_is_the_heading_in_write_mode_too(admin):
    # no title box above the toolbar - the heading at the top of the
    # writing, as in Focus (checked in a browser: desktop and phone, an
    # empty title still refused on Save)
    page = admin.get("/admin/new").text
    assert '<input type="hidden" name="title"' in page and 'placeholder="Post title"' not in page
    js = Path(os.path.join(os.path.dirname(editor.__file__), "..", "js", "editor_init.js")).read_text()
    assert "placeHeading();  // in Write and in Focus alike" in js
    assert "if (!toolbar.classList.contains('fullscreen')) {\n        if (headingAt)" not in js


def test_the_settings_button_goes_while_post_settings_is_beside_the_editor():
    # nothing to open there (checked in a browser: hidden at 1700 px, back at 1300)
    assert """'[data-actions-row] [aria-label="Settings"]""" in editor.PIN_LOCATION_JS
    assert "b.hidden = dock; });" in editor.PIN_LOCATION_JS


def test_the_plus_menus_tabs_slide_with_the_finger():
    # a swipe just switched the grid; now it follows the finger with the
    # next tab beside it, slides, and springs back if it's not far enough
    # (checked in a browser with touch; less motion: it just changes)
    js = editor.EDITOR_INIT_JS
    sheet = js[js.index("var openAll = function"):js.index("var barButton = function")]
    for part in ("addEventListener('touchmove'", "peek = grid(names[at + dir])", "translateX(calc(",
                 "still.matches", "touch-pan-y", "g.style.transform = 'translateX(0)'"):
        assert part in sheet, part


def test_a_timed_sessions_line_glides():
    # it moved every 15 seconds, and when you typed (checked in a browser:
    # every second, a linear 1 s glide)
    js = editor.EDITOR_INIT_JS
    assert "sessionTick(); }, 1000);" in js and "}, 15000);" not in js
    assert "line.classList.toggle('ease-linear', timed)" in js


def test_post_settings_beside_the_editor_dims_under_a_sidebar():
    # it stayed sharp over Help's backdrop (checked in a browser: the
    # backdrop is on top of it beside the editor, under it as a sidebar)
    js = editor.PIN_LOCATION_JS
    assert "var _DOCKED_CLS = ['z-30', 'top-12', 'border-r-[length:var(--border)]', 'border-base-300'];" in js and "'duration-200', 'z-40']" in js


def test_the_plus_sheets_height_eases_between_tabs():
    # it jumped going to History; then it kept the tallest tab's height; now
    # it grows and shrinks with the slide (checked in a browser: 314 to 110
    # px over a quarter of a second, and back)
    js = editor.EDITOR_INIT_JS
    sheet = js[js.index("var openAll = function"):js.index("var barButton = function")]
    assert "body.style.height = next.offsetHeight + 'px'" in sheet and "transition = 'height 0.25s" in sheet
    assert "minHeight = tallest" not in sheet


def test_preview_grows_to_what_it_shows():
    # it scrolled inside Write's height (checked in a browser: a short post
    # with eight pictures - 491 px writing, 3,461 px preview, 491 back)
    js = editor.EDITOR_INIT_JS
    assert "wrap.dataset.writeHeight" in js and "Math.max(pv.scrollHeight" in js
    assert "pv.addEventListener('load', fit, true)" in js


def test_post_settings_beside_the_editor_can_be_turned_off(admin):
    # Settings > Editor: off, it's the sidebar whatever the room (checked
    # in a browser at 1700 px, on and off)
    import json
    from soloblog import settings
    assert settings.DEFAULTS["editor_settings_beside"] == "1"
    try:
        admin.post("/admin/settings/editor", headers={"hx-request": "true"},
                   data={"declared_fields": "editor_settings_beside"})
        assert settings.get("editor_settings_beside") == "0"
        prefs = json.loads(admin.get("/admin/new").text.split("window.EDITOR_PREFS = ")[1].split(";</script>")[0])
        assert prefs["settingsBeside"] is False
    finally:
        settings.set_many({"editor_settings_beside": "1"})
    assert "EDITOR_PREFS.settingsBeside !== false" in editor.PIN_LOCATION_JS


def test_in_full_screen_the_phones_bar_sits_above_the_keyboard():
    # in the browser's full screen Chrome lays the keyboard over the page,
    # and the bar sat under it (seen on a Pixel) - the keyboard API says how
    # tall it is there; the text stops above the bar
    js = editor.EDITOR_INIT_JS
    assert "vk.overlaysContent = !!document.fullscreenElement" in js
    assert "vk.addEventListener('geometrychange', placeBar)" in js
    assert "phoneBar.style.bottom = kb + 'px'" in js and "wrap.style.bottom = kb ?" in js


def test_preview_shows_the_title_at_its_top():
    # the title moved into the writing as a heading, and Preview lost it
    # (checked in a browser: Preview on a computer and a phone, Side by side)
    js = editor.EDITOR_INIT_JS
    assert "title.dataset.previewTitle = ''" in js and "preview.prepend(title)" in js
    assert "querySelectorAll('[data-preview-title]')" in js


def test_spelling_is_checked_again_only_when_the_whole_text_is_replaced():
    # Chrome only checks text you've touched, so text put in at once got no
    # underlines; turning spell check off and on asks again. Doing it on
    # every pause and scroll made the underlines flicker and, on a phone,
    # dropped a long press's selection (checked in a browser: no change to
    # the attribute while typing or scrolling, one after mde.value())
    js = editor.EDITOR_INIT_JS
    part = js[js.index("var recheckAt = 0"):js.index("addEventListener('contextmenu'")]
    assert "field.setAttribute('spellcheck', 'false')" in part
    assert "c.origin === 'setValue'" in part
    assert "on('scroll'" not in part and "on('refresh'" not in part
    assert "composing || touching > 0 || cmSpell.somethingSelected() || !window.getSelection().isCollapsed" in part


def test_a_long_press_on_a_phone_keeps_its_selection():
    # a tap gives the focus back so the keyboard opens; a long press
    # selects a word, and away and back dropped it
    js = editor.EDITOR_INIT_JS
    part = js[js.index("var tapFrom = null"):]
    assert "when: Date.now()" in part
    assert "Date.now() - from.when >= 400 || cm.somethingSelected() || !window.getSelection().isCollapsed" in part
    assert part.index("from.when >= 400") < part.index("input.blur()")

def test_a_phone_has_a_button_to_bring_the_focus_bars_back():
    # once the bars have gone quiet there's no mouse to bring them back
    js = editor.EDITOR_INIT_JS
    part = js[js.index("var showBars = "):js.index("var iconButton")]
    assert "showBars.hidden = !on" in js[js.index("var setTyping"):js.index("var showBars = ")]
    assert "sm:hidden" in part and "aria-label', 'Show the toolbar'" in part
    assert "icons['chevron-down']" in part
    assert "addEventListener('pointerdown', function (e) { e.preventDefault(); })" in part
    assert "addEventListener('click', function () { setTyping(false); })" in part


def test_a_closed_keyboard_takes_the_focus_off_the_text():
    # closed with its own button, the text kept its focus and the next
    # scroll or cursor redraw brought the keyboard back
    js = editor.EDITOR_INIT_JS
    part = js[js.index("var keyboardUp = false"):js.index("var tapFrom = null")]
    assert "if (!was || up || !PHONE.matches) return;" in part
    assert "cm.getWrapperElement().contains(at)) at.blur()" in part
    assert "vk.boundingRect.height > 0 : viewHeight() < tallest - 120" in part
    assert "vv.addEventListener('resize', keyboardMoved)" in js and "geometrychange', keyboardMoved" in js


def test_the_title_keeps_its_typing_events_to_itself():
    # the title sits inside the writing's editable area, which reads every
    # input and composition event that reaches it - fast typing dropped
    # characters on a phone. And its hidden field's echo must not rewrite
    # the title, which cancels a word being composed.
    js = editor.EDITOR_INIT_JS
    part = js[js.index("var titleField = "):js.index("var placeHeading")]
    assert "['keypress', 'beforeinput', 'input', 'compositionstart'" in part
    assert "e.stopPropagation()" in part
    assert "heading.value !== titleField.value" in part


def test_post_settings_sections_are_never_squeezed(admin):
    # folding Publishing, it was squeezed to nothing and the rest jumped
    # (checked in a browser: it eases 552 to 46 px, the others unchanged)
    page = admin.get("/admin/new").text
    inner = page[page.rindex("<", 0, page.index('id="post-settings"')):page.index(">", page.index('id="post-settings"'))]
    assert "[&amp;&gt;*]:shrink-0" in inner or "[&>*]:shrink-0" in inner



def test_the_posts_buttons_sit_beside_save_folding_what_doesnt_fit(admin):
    # on a phone they were all behind ⋯; now beside Save as icons, as many as
    # fit, the rest in ⋯ - which only shows then (checked in a browser: all
    # four at 412 and 375 px, one at 320 with three in ⋯, and Focus's bar)
    page = admin.get("/admin/new").text
    bar = page[page.index('id="editor-bar"'):page.index('id="body-editor"')]
    assert "data-actions-row" in bar and 'data-actions-more' in bar and "hidden" in bar
    assert bar.index('aria-label="Discard"') < bar.index('id="editor-actions"')
    assert "[[data-row-menu]_&amp;]:inline" in bar or "[[data-row-menu]_&]:inline" in bar
    js = editor.EDITOR_INIT_JS
    assert "var fitEditorBar = function" in js and "steps.push(foldOneAction)" in js


def test_every_group_shows_in_the_insert_list():
    # the list draws only the groups it names: Sections, new, didn't show
    js = editor.SLASH_MENU_JS
    order = js[js.index("var ORDER = ["):js.index("];", js.index("var ORDER = ["))]
    for group in editor_config.GROUPS:
        if any(c["slash"] for c in COMMANDS if c["group"] == group) and group != "Text":
            assert f"'{group}'" in order, group


def test_nothing_in_the_editor_depends_on_a_layout():
    # the pieces a layout used to add to Insert are sections (or Help's examples) now
    assert "Layout" not in editor_config.GROUPS and "Layout" not in editor_config.SECTION_ICONS
    assert all("layout" not in c for c in COMMANDS)
    js, slash = editor.EDITOR_INIT_JS, editor.SLASH_MENU_JS
    for source in (js, slash):
        assert "forLayout" not in source and "editorLayout" not in source and "layout-select" not in source


def test_sections_are_offered_in_every_post():
    # sections work in any post: always in Insert, the same list everywhere
    own = [c for c in COMMANDS if c["group"] == "Sections"]
    assert len(own) == len(sections.REGISTRY) and all(c["snippet"] for c in own)
    by_id = {c["id"]: c for c in own}
    assert "pricing" in by_id["section-pricing"]["slash"] and "plans" in by_id["section-pricing"]["slash"]
    # every section's snippet says what kind it is, and the page reads it
    for key in sections.REGISTRY:
        line = next(line for line in sections.markdown(key).split("\n") if line.startswith("Section: "))
        assert sections.NAMES[line[9:].lower()] == key, key
    assert "'Sections'" in editor.SLASH_MENU_JS
    # Help lists every one, as Insert does
    help_sections = dict((key, items) for key, _, items in editor._HELP)["sections"]
    assert [ids for *_, ids, _ in help_sections] == [(c["id"],) for c in own]


def test_a_long_title_fades_where_it_goes_on():
    # a title longer than the line was cut off with nothing to say there
    # was more (checked in a browser at 1440 and 375 px: faded at the right,
    # and at both sides once moved along)
    init = editor.EDITOR_INIT_JS
    title = init[init.index("heading = document.createElement('input')"):init.index("var placeHeading")]
    assert "SCROLLS_X" in title and "heading.setAttribute('data-scroll-x', '')" in title
    assert "_scrollHintX(heading)" in init


def test_media_details_sit_beside_the_page_on_a_wide_screen():
    # beside the column like Post settings, always there with "Pick a file"
    # until one is; a sidebar elsewhere (checked in a browser at 1440 px:
    # docked at the column's edge, still docked after a tab's live swap;
    # at 1280 and 375 px it slides over)
    from soloblog import app as app_module
    js = app_module.PAGE_HELPERS_JS
    place = js[js.index("function placeMediaDetails"):]
    assert "window.innerWidth - left - 22.5 * rem >= 50 * rem" in place
    assert "_dockBeside(panel, dock);" in place and "column.parentElement.getBoundingClientRect().right" in js
    # nothing there until a file is picked; its ✕ puts it away again
    assert "panel.hidden = !open;" in js and "panel.toggleAttribute('data-open', !!open);" in js
    assert "document.addEventListener('htmx:afterSettle', placeMediaDetails)" in js
    toggle = js[js.index("function toggleMediaDetails"):js.index("function placeMediaDetails")]
    assert "if (panel.hasAttribute('data-docked')) { _showDocked(panel); return; }" in toggle


def test_the_phones_sheet_opens_on_the_tab_used_last():
    # it always opened on Insert (checked in a browser at 375 px: Text
    # chosen, closed, reopened and after a reload, it opens on Text)
    js = editor.EDITOR_INIT_JS
    all_sheet = js[js.index("var openAll = function"):]
    assert "localStorage.getItem('editor-sheet-tab')" in all_sheet
    assert "localStorage.setItem('editor-sheet-tab', names[i])" in all_sheet
    assert "Math.max(0, names.indexOf('Insert'))" in all_sheet  # until a tab's been chosen


def test_the_preview_is_the_writings_size_in_and_out_of_focus(admin):
    # the preview was prose-sm (14px) beside writing at the post's 18px,
    # and Focus's A- and A+ grew only the writing (checked in a browser:
    # both 18px, both 22.5px at 125%)
    js = editor.EDITOR_INIT_JS
    assert 'previewClass: ["editor-preview", "prose", "md:prose-lg", "max-w-none", "prose-li:my-1", "[&_:not(pre)>code]:wrap-anywhere",' in js
    # the writing's own column, and Wide (the form is the group) filling the box
    assert '"[&>*]:max-w-[calc(36*var(--editor-fs,1rem))]", "[&>*]:mx-auto", "group-data-[editor-width=wide]/pf:[&>*]:max-w-none"]' in js
    assert "group/pf" in admin.get("/admin/new").text
    css = Path("static/css/input.css").read_text(encoding="utf-8")
    assert "html[data-focus-mode] .EasyMDEContainer :is(.CodeMirror-fullscreen, .editor-preview-side) {" in css


def test_post_settings_unsaved_bar_saves_only_while_it_covers_the_editor(admin):
    # its Discard threw away the text too, from a settings panel - gone, it's
    # the editor bar's alone, and asks first once the text has changed. Its
    # Save shows only while the panel covers the editor: docked beside it,
    # the editor's own Save is in view (checked in a browser at 1000 and
    # 1700 px)
    page = admin.get("/admin/new").text
    panel = page[page.index('id="post-settings-panel"'):]
    start = panel.rindex("<div", 0, panel.index("Unsaved changes"))
    bar = panel[start:panel.index("</div>", start)]
    assert "discardForm" not in bar and 'type="submit"' in bar
    assert "[form[data-unsaved]_#post-settings-panel:not([data-docked])_&amp;]:flex" in bar
    js = Path("soloblog/js/save_status_clear.js").read_text(encoding="utf-8")
    assert "confirmAction('Discard your changes? The post goes back to how it was last saved.'" in js
    assert "window._activeEasyMDE.value() !== text.defaultValue" in js


def test_a_new_commands_id_is_no_css_class():
    # a command's id is its toolbar button's class: "countdown" is also
    # daisyUI's countdown, which drew the button as the digits "00 0"
    import os
    import re
    css = Path(os.path.join(os.path.dirname(__file__), "..", "static", "css", "output.css")).read_text()
    clashes = [c["id"] for c in COMMANDS if re.search(r"(?<![\w-])\." + re.escape(c["id"]) + r"(?![\w-])", css)]
    # these were there first, and draw as they should
    assert set(clashes) <= {"italic", "keys", "tabs", "footnote", "link", "table"}, clashes


def _markdown_reference():
    text = Path(os.path.join(os.path.dirname(__file__), "..", "docs", "guide", "reference.md")).read_text(encoding="utf-8")
    start = text.index("\n## Markdown and extras\n")
    return text[start:text.index("\n## ", start + 1)]


def test_the_markdown_reference_has_a_row_for_every_command():
    """Reference > Markdown and extras has a row for every command that
    writes something into a post. A row is found by the command's label,
    in bold, in the first cell of a table row - the name the toolbar,
    Insert and the slash menu show, so renaming a command fails here
    until the guide uses its new name too. One row may name several
    commands (**Callout**, **Tip**...). Left out: Insert (it's the list
    of the others) and the sections, which each have an entry in Sections
    and templates; History, View and Help change the editor, not the
    post."""
    named = set()
    for line in _markdown_reference().splitlines():
        if line.startswith("| ") and not line.startswith("|---"):
            named |= set(re.findall(r"\*\*(.+?)\*\*", line.split("|")[1]))
    writes = {c["label"] for c in COMMANDS if c["group"] in ("Text", "Blocks", "Insert") and c["id"] != "insert"}
    assert writes - named == set(), writes - named


def test_editor_help_links_each_mark_to_its_own_place():
    # Headings, Lists, Quote... each lead to their own heading in the
    # guide, not the top of a page that has every mark on it (the
    # anchors are checked to exist by the test below)
    tops = {"writing.md#write-and-format-a-post", "reference.md#markdown-and-extras"}
    headings = set(re.findall(r"^### (.+)$", _markdown_reference(), re.M))
    for key, _, entries in editor._HELP:
        if key not in ("start", "formatting", "blocks"):
            continue
        for name, *_ in entries:
            target = editor._HELP_MORE.get(name, editor._HELP_MORE.get(key, ""))
            assert target and target not in tops, name
            if target.startswith("reference.md#"):
                assert target.split("#")[1] in {editor._anchor(h) for h in headings}, name


def test_the_help_panel_has_everything_and_its_links_land(admin):
    # every section, template and Key: value is in the editor's
    # Help panel, each linking to its entry in Help - and every link lands
    # on a heading that's there
    import re
    from soloblog import post_templates
    page = admin.get("/admin/new").text
    # its parts come when it first opens (/admin/editor/help), its head with the page
    panel = page[page.index('id="editor-help-panel"'):] + admin.get("/admin/editor/help").text
    for key in ("sections", "templates", "keys"):
        assert f'data-help-jump="{key}"' in panel and f'data-help-section="{key}"' in panel, key
    # each jump says what its part's heading says, and a phone (which hides
    # Shortcuts) has no Shortcuts jump - it went to the top
    for key, title in editor._HELP_JUMPS:
        part = panel.split(f'data-help-section="{key}"')[1][:400]
        assert f">{title}" in part, key
    assert re.search(r'data-help-jump="shortcuts"[^>]*max-sm:hidden', panel)
    for entry in sections.REGISTRY.values():
        assert f">{html.escape(entry['label'])}</span>" in panel, entry['label']
    assert 'data-help-section="layouts"' not in panel
    for name, *_ in post_templates.BUILT_IN.values():
        assert f">{html.escape(name)}</span>" in panel, name
    assert len(editor._key_index()) >= 25 and "Width: Column" in panel and "Style: Cover" in panel
    guide_pages = {}
    for tab, anchor in set(re.findall(r'href="/admin/help\?tab=([a-z-]+)#([a-z0-9-]+)"', panel)):
        guide_pages.setdefault(tab, admin.get(f"/admin/help?tab={tab}").text)
        assert f'id="{anchor}"' in guide_pages[tab], (tab, anchor)


def test_the_insert_and_emoji_lists_come_back_when_the_words_match_again():
    # ":" and two letters that found nothing closed the list, and only a
    # new ":" or "/" opened it - so deleting the letters and typing others
    # never brought it back (checked in a browser: :qx, two Backspaces, sm
    # shows the emoji; /zq, then ta, shows Table; Esc keeps it closed)
    js = editor.SLASH_MENU_JS
    part = js[js.index("function reopen()"):]
    assert "else if (!menu && change.origin === '+input') reopen();" in part
    assert "m[3].length < (m[2] === ':' ? 2 : 1)" in part
    assert "Esc: function () { dismissed = start; close(); }" in js
    # the words before the cursor that count: after a space or at the line's
    # start, never an address or a time
    pattern = re.compile(re.search(r"var m = /(.+?)/\.exec\(before\)", part).group(1).replace("\\/", "/"))
    for before, found in [("Hi :sm", (":", "sm")), ("/ta", ("/", "ta")), ("a /head", ("/", "head")),
                          ("see http://example.com/path", None), ("at 10:30", None),
                          ("Note: then", None), ("/he llo", None)]:
        m = pattern.search(before)
        assert (m and (m.group(2), m.group(3))) == found or (m is None and found is None), before


def test_tab_moves_a_line_four_spaces():
    # a tab counts as four spaces in markdown but showed two wide, so people
    # pressed it twice and got a code block. EasyMDE's own Tab and Shift+Tab
    # move the line in and out; the insert list's Tab still picks a row
    # (checked in a browser: a line, a list item and three selected lines
    # in by four spaces and back out)
    js = editor.EDITOR_INIT_JS
    assert "tabSize: 4," in js and "indentWithTabs: false," in js
    assert "Tab: function () { choose(active); }" in editor.SLASH_MENU_JS


def test_the_phones_tiles_draw_their_icons_a_size_up():
    # both grids (a section's commands, and Blocks) - the class beats .editor-icon's own size
    assert editor.EDITOR_INIT_JS.count("[&_.editor-icon]:size-5.5!") == 2


def test_the_phone_bars_row_swipes_and_keeps_its_buttons_44px():
    js = editor.EDITOR_INIT_JS
    assert "editor-phonebar-scroll flex flex-1 min-w-0 overflow-x-auto" in js
    assert "editor-phonebar-sep flex-none self-center w-px h-6 mx-0.5 bg-base-300" in js
    assert "'flex-none! w-11!'" in js


def test_the_go_to_button_is_at_the_toolbars_right_end_in_every_style():
    # Go to: the post's own sections, to jump to one. Not a command you
    # choose - it isn't in Settings > Editor, so it can't be taken off - and
    # added by buildToolbar in every style, beside Insert, with its icon and
    # its word like Insert. Not called Sections: Classic menus' Sections
    # menu inserts them.
    assert editor_config.MENUS["goto"] == ("Go to", "table-of-contents")
    assert "goto" not in editor_config.COMMAND and "goto" not in editor_config.ORDERABLE_KEYS
    assert "goto" not in editor_config.pinned_from_setting("goto,bold")
    assert "table-of-contents" in editor_icons.ICONS
    prefs = json.loads(editor_config.fixed_prefs_script().split("Object.assign(window.EDITOR_PREFS || {}, ")[1].rsplit(");", 1)[0])
    assert prefs["menus"]["goto"]["label"] == "Go to" and "<svg" in prefs["menus"]["goto"]["icon"]
    assert prefs["goTo"]["label"] == "Go to a section"
    assert "check" in prefs["icons"]
    js = editor.EDITOR_INIT_JS
    build = js.split("function buildToolbar() {")[1].split("// EasyMDE names its buttons")[0]
    # Minimal (hidden, like Insert), Classic menus (last of all), Icons (before Insert)
    assert "return [item('insert'), goToButton()];" in build
    assert "menus.push('|', goToButton());" in build
    assert "bar.push(goToButton(), item('insert'));" in build
    assert "'<span class=\"toolbar-word\">' + m.label + '</span>'" in js
    # named for a screen reader, with the tooltip on a wide screen and the popup's state
    assert "b.dataset.tip = PREFS.goTo.label" in js and "'aria-haspopup', 'listbox'" in js
    assert "'aria-expanded', 'false'" in js
    # never folded into ⋯ with the buttons that don't fit
    assert "items[i] === goToBtn" in js
    # on a phone: the icon alone, in the bar above the keyboard
    assert "PREFS.goTo.label" in js and "id === 'sections-jump'" in js


def test_the_sections_menu_is_built_from_the_text_each_time_it_opens():
    menu = editor.SLASH_MENU_JS
    assert "mde.openSections = function (button)" in menu and "mde.sections()" in menu
    # nothing yet: a line saying so and a way to add one, at Insert's Sections group
    assert "No sections yet" in menu and "Insert a section…" in menu and "mde.openInsert(from, 'Sections')" in menu
    # the section the cursor's in is marked
    assert "aria-current" in menu and "it.here" in menu
    # arrows, Enter, Space and Esc, the focus back on the button
    for key in ("ArrowDown", "ArrowUp", "'Enter'", "'Escape'", "back.focus()"):
        assert key in menu
    # as wide as its longest row, one line each
    assert "w-max" in menu and "whitespace-nowrap" in menu and "data-scroll-hint" in menu


def test_go_to_a_section_is_in_the_slash_menu_and_inserts_nothing():
    go = editor_config.GO_TO
    # not a command: those are buttons, menu rows and Help's lists - this
    # only opens the Go to list
    assert go["label"] == "Go to a section" and go["group"] in editor_config.GROUPS
    assert go["label"] not in [c["label"] for c in COMMANDS]
    # found by go, jump and section - and reading apart from what inserts one
    assert {"go", "jump", "section"} <= set(go["slash"])
    prefs = json.loads(editor_config.fixed_prefs_script().split("Object.assign(window.EDITOR_PREFS || {}, ")[1].rsplit(");", 1)[0])
    assert prefs["goTo"]["label"] == "Go to a section" and "<svg" in prefs["goTo"]["icon"]
    menu = editor.SLASH_MENU_JS
    # added to the slash menu's items, run by opening the list at the cursor
    assert "ITEMS.push(goTo)" in menu and "mde.openSections(null)" in menu and "slashOnly: true" in menu
    # not in Insert's list, which is for things to add - and /section and Enter
    # still adds a section
    assert "offered(it)" in menu and "!(it.slashOnly && mode === 'insert')" in menu and "!it.slashOnly &&" in menu
    # from the slash menu there's no button: the list goes at the cursor, Esc to the text
    assert "else start = cm.getCursor()" in menu and "back.focus(); else cm.focus()" in menu
    # Insert's Sections group is still found by "section" (each kind has it in its words)
    kinds = [c for c in COMMANDS if c["group"] == "Sections"]
    assert kinds and all("section" in c["slash"] for c in kinds)
