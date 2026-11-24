import json

from soloblog import editor_icons, sections

# Every command the post editor has, in one place. The toolbar, its ⋯
# menu, the heading menu, the slash menu, the keyboard shortcuts, the
# help and Settings > Editor are all made from this list, so they can't
# disagree about a name, an icon or a shortcut
# (tests/test_editor_commands.py checks none is missing a part).
#
# keys: CodeMirror's spelling - dashes, and Shift, then Cmd, then Alt;
#       Cmd is Ctrl off a Mac. None: no shortcut.
# md: the markdown it writes, shown beside it in the slash menu.
# slash: words the slash menu finds it by (its name always finds it);
#        () keeps it out of the slash menu.
# place: "toolbar" (on it out of the box), "more" (off the toolbar, but
#        one tick away in Settings > Editor), "slash" (slash menu and help only).
GROUPS = ["Text", "Blocks", "Insert", "Sections", "History", "View", "Help"]


def _c(id, label, about, group, icon, keys=None, md=None, slash=(), place="more", snippet=None):
    return {"id": id, "label": label, "about": about, "group": group, "icon": icon, "keys": keys,
            "md": md, "slash": list(slash), "place": place, "snippet": snippet}


COMMANDS = [
    _c("paragraph", "Paragraph", "Plain text", "Text", "pilcrow", "Cmd-Alt-0", None, ("text", "normal")),
    _c("heading", "Heading", "A new section", "Text", "heading-2", "Cmd-Alt-2", "##", ("h2", "title", "section"),
       "toolbar"),
    _c("subheading", "Subheading", "A part of a section", "Text", "heading-3", "Cmd-Alt-3", "###", ("h3",),
       "toolbar"),
    _c("small-heading", "Small heading", "A heading for a few lines", "Text", "heading-4", "Cmd-Alt-4", "####",
       ("h4",)),
    _c("bold", "Bold", "Makes words stand out", "Text", "bold", "Cmd-B", "**", ("strong",), "toolbar"),
    _c("italic", "Italic", "Slants words, for emphasis", "Text", "italic", "Cmd-I", "*", ("emphasis",), "toolbar"),
    _c("strikethrough", "Strikethrough", "Crosses words out", "Text", "strikethrough", "Shift-Cmd-X", "~~",
       ("strike", "cross out")),
    _c("inline-code", "Inline code", "Code inside a sentence", "Text", "code", "Cmd-E", "`", ("code",)),
    _c("highlight", "Highlight", "Marks words in your palette's colour", "Text", "highlighter", "Cmd-Alt-H",
       "==", ("mark", "marker")),
    _c("superscript", "Superscript", "Raised text, like x²", "Text", "superscript", None, "^", ("sup", "power")),
    _c("subscript", "Subscript", "Lowered text, like H₂O", "Text", "subscript", None, "~", ("sub", "chemistry")),
    _c("keys", "Keyboard keys", "Shows keys as keys, like Ctrl+C", "Text", "keyboard", None, "++",
       ("kbd", "hotkey")),
    _c("emoji", "Emoji", "Pick one as you type its name", "Text", "smile", None, ":", ("smiley", "icon")),
    _c("clean-block", "Clear formatting", "Takes heading, list or quote off a line", "Text", "remove-formatting",
       "Cmd-\\", None, ("plain", "remove"), "toolbar"),
    _c("quote", "Quote", "Someone else's words", "Blocks", "text-quote", "Cmd-'", ">", ("blockquote",), "toolbar"),
    _c("unordered-list", "Bulleted list", "Points in no particular order", "Blocks", "list", "Shift-Cmd-8", "-",
       ("bullet", "ul", "list"), "toolbar"),
    _c("ordered-list", "Numbered list", "Steps, in order", "Blocks", "list-ordered", "Shift-Cmd-7", "1.",
       ("number", "ol", "steps"), "toolbar"),
    _c("check-list", "Checklist", "Things to tick off", "Blocks", "list-checks", "Shift-Cmd-9", "[ ]",
       ("todo", "task")),
    _c("code", "Code block", "Lines of code, kept as typed", "Blocks", "square-code", "Cmd-Alt-C", "```",
       ("pre", "program")),
    _c("callout", "Callout", "A note in a box that stands out", "Blocks", "info", None, "!!!",
       ("note", "info", "admonition", "box")),
    _c("callout-tip", "Tip", "A helpful hint, in a box", "Blocks", "lightbulb", None, "!!!", ("callout", "hint"),
       "slash"),
    _c("callout-warning", "Warning", "Something to watch out for", "Blocks", "triangle-alert", None, "!!!",
       ("callout", "caution"), "slash"),
    _c("callout-danger", "Danger", "Something that could go wrong", "Blocks", "octagon-alert", None, "!!!",
       ("callout", "error"), "slash"),
    _c("tabs", "Tabs", "The same content, one tab each", "Blocks", "panels-top-left", None, "===", ("tabbed",)),
    _c("definition", "Definition", "A term and what it means", "Blocks", "book-a", None, ":", ("term", "glossary")),
    _c("footnote", "Footnote", "A numbered note at the end", "Blocks", "asterisk", None, "[^1]",
       ("reference", "source")),
    _c("abbreviation", "Abbreviation", "Explains a short form on hover", "Blocks", "a-large-small", None, "*[",
       ("acronym",)),
    # blocks written as a line of their own (render._blocks), and a fold
    _c("buttons", "Buttons", "One or two buttons in the text", "Blocks", "mouse-pointer-click", None, "Buttons:",
       ("button", "links", "cta"), "slash", "Buttons: [Join](/join) [Read more](/about)"),
    _c("collapsible", "Collapsible", "A heading that opens to its text", "Blocks", "list-collapse", None, "???",
       ("fold", "details", "accordion", "spoiler"), "slash", '??? "A heading"\n    The text it opens to.'),
    _c("pull-quote", "Pull quote", "A big quote that stands out", "Blocks", "speech", None, "Pull quote:",
       ("highlight", "big quote"), "slash", "Pull quote: A line worth repeating."),
    _c("days-to-go", "Countdown", "Days to go until a date", "Blocks", "hourglass", None, "Countdown:",
       ("timer", "launch", "date"), "slash", "Countdown: 12 March 2027"),
    # the slash menu's list, from a button - not in the list itself
    _c("insert", "Insert", "Everything you can add, in one list", "Insert", "plus", None, None, (), "toolbar"),
    _c("link", "Link", "Links words to an address", "Insert", "link", "Cmd-K", "[]()", ("url", "address"),
       "toolbar"),
    _c("link-picker", "Link to a post or page", "One of your own, from a list", "Insert", "file-symlink",
       "Cmd-Alt-K", None, ("post", "page", "internal"), "toolbar"),
    _c("wiki-link", "Link by title", "Another post, by its title", "Insert", "brackets", None, "[[",
       ("wiki", "title")),
    _c("library", "Image from your library", "Pick an image, or upload one", "Insert", "image", "Cmd-Alt-I", None,
       ("image", "picture", "photo", "media"), "toolbar"),
    _c("upload-image", "Upload image", "An image from your device", "Insert", "image-up", None, None,
       ("image", "photo")),
    _c("image", "Image by URL", "An image from another site's address", "Insert", "image-plus", None, "![]()",
       ("picture", "address")),
    _c("gallery", "Gallery", "Images inside your writing, as a grid or slider", "Insert", "images", "Cmd-Alt-G", None,
       ("photos", "images", "slider"), "toolbar"),
    _c("table", "Table", "Rows and columns", "Insert", "table", None, "|", ("grid", "columns")),
    _c("horizontal-rule", "Divider", "A line across the post", "Insert", "minus", None, "---", ("hr", "line", "rule")),
    # the members area: where a members post's free preview ends (posts.MEMBERS_CUT)
    _c("members-cut", "Members only from here", "Where a members post's free preview ends", "Insert", "lock", None,
       "<!-- members only from here -->", ("members", "paywall", "preview")),
    _c("embed", "Video or embed", "YouTube, Vimeo, a map or a form", "Insert", "square-play", None, "URL",
       ("video", "youtube", "map", "form")),
    _c("math", "Math", "An equation", "Insert", "sigma", None, "$", ("equation", "latex", "formula")),
    _c("diagram", "Diagram", "A flowchart or chart, drawn from text", "Insert", "workflow", None, "```",
       ("mermaid", "chart", "flowchart")),
    # sections (sections.REGISTRY) - always offered, the same list in every
    # post; and in Help
    *[_c(f"section-{key}", entry["label"], entry["about"], "Sections", entry["icon"], None, "##",
         sections.search_words(key), "slash", sections.markdown(key)) for key, entry in sections.REGISTRY.items()],
    # Undo and Redo are CodeMirror's own keys - listed, not bound again
    _c("undo", "Undo", "Takes back the last change", "History", "undo-2", "Cmd-Z", place="toolbar"),
    _c("redo", "Redo", "Brings it back", "History", "redo-2", "Cmd-Y", place="toolbar"),
    _c("preview", "Preview", "The post as readers will see it", "View", "eye", "Cmd-Alt-P", None, ("view", "read")),
    _c("side-by-side", "Side by side", "Writing and preview together", "View", "columns-2", None, None,
       ("split", "preview")),
    _c("fullscreen", "Focus", "Only your writing, filling the screen", "View", "maximize-2", "Shift-Cmd-F", None,
       ("focus", "distraction")),
    _c("guide", "Help", "Examples, shortcuts and templates", "Help", "circle-help", "Cmd-/", None,
       ("help", "guide", "markdown", "examples")),
    _c("shortcuts", "Keyboard shortcuts", "Every shortcut, for your keyboard", "Help", "command", None, None,
       ("keys", "hotkeys", "help")),
]
COMMAND = {c["id"]: c for c in COMMANDS}
# CodeMirror's own - shown in the help, never bound a second time
BUILT_IN_KEYS = {"undo", "redo"}

# the menu on the toolbar that isn't a command itself
# Go to: the post's own sections, to jump to one - at the toolbar's right
# end beside Insert, and not one of the buttons you can choose. Not called
# Sections: Classic menus has a Sections menu that inserts them.
MENUS = {"more": ("More", "ellipsis"), "goto": ("Go to", "table-of-contents")}
# Go to is also in the / menu, in every toolbar style (even none): it opens
# the same list at the cursor and inserts nothing, so it isn't one of
# COMMANDS - those are buttons, menus and Help's lists too. Its name is the
# button's tooltip and, on a phone, its name for a screen reader. Under View
# in the list; the words are what finds it.
GO_TO = {"label": "Go to a section", "about": "Jump to any section of the text", "group": "View",
         "slash": ("go", "jump", "section", "sections", "heading")}
# the line styles - the slash menu lists them first, under Headings
HEADINGS = ["paragraph", "heading", "subheading", "small-heading"]
# each section's own icon - its button on a phone's bar
SECTION_ICONS = {"Text": "type", "Blocks": "blocks", "Insert": "plus", "Sections": "layout-dashboard",
                 "History": "history", "View": "eye", "Help": "circle-help"}
# icons beside the commands' own: the classic menus' arrow, focus mode's
# bar (its full screen, writing sessions and text size), the sections',
# and the help's for what no command writes (a map, a form)
# what a Features section's item may name on an "Icon:" line - the ones
# feature lists reach for, as line icons in place of an emoji
FEATURE_ICONS = ("pen-line", "palette", "layout-template", "mail", "users", "smartphone", "shield-check",
                 "database-backup", "key-round", "chart-column", "refresh-cw", "luggage", "bot", "globe", "lock",
                 "zap", "heart", "rocket", "sparkles", "check", "clock", "star", "message-circle", "bell",
                 "search", "book-open", "image", "camera", "music", "coffee", "gift", "map-pin", "calendar",
                 "credit-card", "download", "cloud", "code", "server", "wand-sparkles", "leaf", "puzzle",
                 "life-buoy", "languages", "rss", "feather", "eye-off", "hand-heart", "house", "store", "truck")
EXTRA_ICONS = ("chevron-down", "x", "expand", "shrink", "align-left", "align-center",
               "fold-vertical", "align-vertical-space-around", "unfold-vertical", "blend", "arrow-up-from-line",
               "zoom-in", "arrow-right-from-line", "arrow-left-from-line", "arrow-left-right", "focus", "rotate-3d",
               "ban", "copyright", "map", "clipboard-list", "file-audio",
               "timer", "a-arrow-down", "a-arrow-up", "pencil", *SECTION_ICONS.values(), *FEATURE_ICONS)

# Settings > Editor's checkboxes: (key, label, on the toolbar out of the
# box), grouped by section. The toolbar's ORDER is a separate, draggable
# setting (editor_toolbar). Insert has no checkbox: it's always on.
ALWAYS_ON = "insert"
TOOLBAR_GROUPS = [(group, [(c["id"], c["label"], c["place"] == "toolbar") for c in COMMANDS
                           if c["group"] == group and c["place"] in ("toolbar", "more") and c["id"] != ALWAYS_ON])
                  for group in GROUPS]
TOOLBAR_GROUPS = [(group, items) for group, items in TOOLBAR_GROUPS if items]

LABELS = {key: label for _, items in TOOLBAR_GROUPS for key, label, _ in items}
LABELS[ALWAYS_ON] = COMMAND[ALWAYS_ON]["label"]

ALL_KEYS = [key for _, items in TOOLBAR_GROUPS for key, _, _ in items]  # checkbox-controllable
ORDERABLE_KEYS = ALL_KEYS + [ALWAYS_ON]  # every key that can legally appear in a saved order

# which section each button is in. The toolbar keeps a section's buttons
# together, sections in GROUPS order, with a divider between them - you
# order the buttons within a section, never across.
GROUP_OF = {c["id"]: c["group"] for c in COMMANDS}

# the toolbar's out-of-the-box order: the buttons a blogger reaches for
# most - headings, bold, italic and Clear formatting | lists and quote |
# links, images and Insert | undo and redo - shown, as Google Docs, Word
# and WordPress do, for anyone who doesn't know Ctrl+Z. Preview, focus mode and help are on
# the bar over it (side by side is a tab in focus mode, where there's
# room for it); a button that doesn't fit the row goes under ⋯. The rest
# are a click away in Insert (strikethrough, checklist, code, table).
# Also the fallback order for any key missing from a saved setting (a
# button added in a later version).
DEFAULT_ORDER = ["heading", "subheading", "bold", "italic", "clean-block", "unordered-list", "ordered-list", "quote",
                 "link", "link-picker", "library", "gallery", "insert", "undo", "redo"]
DEFAULT_PINNED = DEFAULT_ORDER


# Classic menus (Settings > Editor > Toolbar): Text ▾ Blocks ▾ Insert ▾
# History ▾ View ▾ Help ▾, each listing every command in its section - all
# of them, ticked or not, as a word processor's menus do. Not Insert's
# own list: in a menu bar, the Insert menu is that list.
SECTION_MENUS = [(group, [c["id"] for c in COMMANDS if c["group"] == group and c["id"] != ALWAYS_ON])
                 for group in GROUPS]
TOOLBAR_STYLES = ("one", "menus", "none")
# Settings > Editor > Writing > While you type, in Focus mode
FOCUS_QUIET = ("all", "none")
# ... > Fade, in Focus mode: everything but the paragraph or sentence you're in
FOCUS_FADES = ("paragraph", "sentence", "off")


def toolbar_style(value: str) -> str:
    """Settings > Editor > Toolbar: "one" (Icons - a row of the buttons
    you tick), "menus" (Classic menus) or "none" (Minimal). Anything else
    is Icons."""
    return value if value in TOOLBAR_STYLES else "one"


# The bar above a phone's keyboard (Settings > Editor > On a phone):
# "sections" - a button per section, each opening its commands as a grid;
# "buttons" - the Icons toolbar's own buttons in a row, and All for the
# rest; "none" - no bar. Undo, Redo and Help are buttons
# like any other: on the bar when they're among yours, always in their
# sections (History, Help).
PHONE_BARS = ("buttons", "sections", "none")
PHONE_SECTIONS = GROUPS


def phone_bar(settings: dict) -> str:
    """What the phone's bar is: buttons, sections or none - anything else
    is buttons."""
    value = settings.get("editor_phone_bar") or "buttons"
    return value if value in PHONE_BARS else "buttons"


def icon_svg(key: str) -> str:
    """A toolbar slot's icon - a command's, or the ⋯ menu's."""
    name = MENUS[key][1] if key in MENUS else COMMAND[key]["icon"]
    return editor_icons.svg(name)


def key_text(keys: str, mac: bool = False) -> str:
    """A shortcut as people write it: "Shift-Cmd-X" -> "Ctrl+Shift+X"
    (or "Cmd+Shift+X" on a Mac)."""
    parts = keys.replace("Cmd", "Cmd" if mac else "Ctrl").split("-")
    if len(parts) > 2 and parts[0] == "Shift":  # the modifier people say first
        parts[0], parts[1] = parts[1], parts[0]
    return "+".join(parts)


def pinned_from_setting(value: str) -> list[str]:
    """The saved comma list of toolbar keys: cleaned down to real, known
    keys, deduplicated, and each section's buttons together, sections in
    GROUPS order - within a section, the admin's own order. An unknown key
    (an old setting, a hand-edited row, the heading menu from before it
    went) is dropped rather than putting a broken button on the toolbar.
    Insert is always there - it has no checkbox to add it back."""
    seen = []
    for k in value.split(","):
        k = k.strip()
        if k in ORDERABLE_KEYS and k not in seen:
            seen.append(k)
    if ALWAYS_ON not in seen:
        seen.append(ALWAYS_ON)
    return sorted(seen, key=lambda k: GROUPS.index(GROUP_OF[k]))  # stable: keeps the order within a section


def block_options(settings: dict | None = None) -> dict:
    """What the / menu offers first in a block (slash_menu.js): a section's
    Key: lines (sections.editor_data), a gallery's style, a callout's kind,
    a fold's - (value, label, what it does, icon)."""
    from soloblog import gallery, posts
    icon = editor_icons.svg
    data = sections.editor_data()
    # what Default does for Show as: follow Settings > Posts
    site = (settings or {}).get("portfolio_style") or "grid"
    shows = data["options"]["Show as"]
    named = next((v[1] for v in shows["values"] if v[0] == site), "")
    if named:
        shows["default"] = f"Follow the site ({named})"
    tags = [t for t, _ in sorted(posts.tag_counts(), key=lambda tc: -tc[1])[:10]]
    return {
        **data,
        "gallery": [(key, label.split(" — ")[0], label.split(" — ")[1].capitalize(),
                     icon({"grid": "grid-2x2", "masonry": "layout-dashboard", "justified": "layout-grid",
                           "slider": "images", "filmstrip": "panels-top-left"}[key]))
                    for key, label in gallery.STYLES.items()],
        "galleryDefault": (settings or {}).get("gallery_style") or "grid",
        # the tags used most, to pick from - another can still be typed
        "tags": tags,
        # the series, to pick from
        "series": posts.series_names(),
        # a tag called Default (on any post, a draft too) can't be picked with "Tag: Default"
        "defaultTag": any(t.lower() == sections.DEFAULT.lower() for t, _ in posts.tag_counts_all()),
        # a callout's kind and whether a fold starts open
        "callout": [("note", "Note", "A note in a box", icon("info")),
                    ("tip", "Tip", "A helpful hint", icon("lightbulb")),
                    ("warning", "Warning", "Something to watch out for", icon("triangle-alert")),
                    ("danger", "Danger", "Something that could go wrong", icon("octagon-alert"))],
        "icons": {"default": icon("remove-formatting"), "auto": icon("timer"), "count": icon("list-ordered"),
                  "tag": icon("tag"), "series": icon("list-ordered"), "open": icon("eye"), "closed": icon("list-collapse")},
    }


def prefs_script(settings: dict) -> str:
    """The inline JS that hands the commands and the saved preferences to
    EDITOR_INIT_JS. Built only from the fixed lists above plus the admin's
    own saved order, so there's nothing user-typed in it that needs
    escaping."""
    prefs = {
        "pinned": pinned_from_setting(settings["editor_toolbar"]),
        "autosave": settings["editor_autosave"] == "1",
        "settingsBeside": settings["editor_settings_beside"] == "1",
        # what the / menu and Insert offer first while the cursor is in a
        # section or a gallery (slash_menu.js, blockOptions): its lines, by
        # the names Help and the page use
        "options": block_options(settings),
        "rows": toolbar_style(settings["editor_toolbar_rows"]),
        "phone": phone_bar(settings), "phoneSections": PHONE_SECTIONS,
        # Classic menus: every command, a menu per section
        "sections": [{"name": group, "ids": ids, "icon": editor_icons.svg(SECTION_ICONS[group])}
                     for group, ids in SECTION_MENUS],
        "slash": settings["editor_slash"] == "1",
        "spellcheck": settings["editor_spellcheck"] == "1",
        "typewriter": settings["editor_typewriter"] == "1",
        "fade": settings["editor_fade"] if settings["editor_fade"] in FOCUS_FADES else "paragraph",
        # Focus mode while you type: "all" (the toolbar away, the bars
        # quiet) or "none" - an old "toolbar" is "all"
        "focusToolbar": "none" if settings["editor_focus_toolbar"] == "none" else "all",
        # on a wide screen, one bar: the one over the text joins Focus mode's
        "focusBars": "one",
        # an empty post says what to do - and where the slash menu is
        "placeholder": "Write something… Type / to add a heading, image or more"
                       if settings["editor_slash"] == "1" else "Write something…",
    }
    return f"window.EDITOR_PREFS = {json.dumps(prefs)};"


def fixed_prefs_script() -> str:
    """The rest of EDITOR_PREFS - the same for everyone, so it goes in the
    editor's script the browser keeps (EDITOR_JS), not in every page."""
    fixed = {
        "labels": LABELS,
        "order": ORDERABLE_KEYS,  # canonical fallback order for anything missing from "pinned"
        "groups": GROUP_OF,
        "commands": [{**c, "icon": editor_icons.svg(c["icon"]), "builtin": c["id"] in BUILT_IN_KEYS}
                     for c in COMMANDS],
        "menus": {key: {"label": label, "icon": editor_icons.svg(icon)} for key, (label, icon) in MENUS.items()},
        "icons": {name: editor_icons.svg(name) for name in ("chevron-down", "check", "x", "expand", "shrink", "type", "timer",
                                                            "a-arrow-down", "a-arrow-up", "pencil", "eye", "maximize-2", "columns-2")},
        "headings": HEADINGS,
        "goTo": {**GO_TO, "icon": editor_icons.svg(MENUS["goto"][1])},
    }
    return f"window.EDITOR_PREFS = Object.assign(window.EDITOR_PREFS || {{}}, {json.dumps(fixed)});"
