from pathlib import Path
import hashlib
import json
import logging
import re
from dataclasses import dataclass, fields
from soloblog.tz import utcnow
from urllib.parse import quote

from fasthtml.common import *

from soloblog import js
from soloblog import newsletter
from soloblog import posts
from soloblog import post_templates
from soloblog import pages
from soloblog import sections as section_registry
from soloblog import settings
from soloblog import tz
from soloblog import config
from soloblog import csp
from soloblog import editor_config
from soloblog import editor_icons
from soloblog import images
from soloblog import members
from soloblog.render import format_date, render_post
from soloblog.actions import on, EL, VALUE
from soloblog.ui import Tabs, TABS_CLS, LinkPickerButton
from soloblog.ui import IconAction, FOCUS_SVG, DOTS_SVG, PLUS_SVG, CHEVRON_DOWN_SVG, EYE_SVG, EYE_OFF_SVG, SITE_ROW_WORDS, SITE_LABEL_MAX
from soloblog.ui import DEFAULT_TAG, SCROLLS_X, RowActions, MenuLabel, SearchBox, DRAWER_W, DRAWER_BACKDROP, TEMPLATE_SVG, SCROLLS, SEARCH_DIALOG_BOX, SEARCH_DIALOG_ACTION
from soloblog.ui import (ListHeader, BulkButton, SearchField, FilterSelect, list_summary, RowCheck, TICK_ROW, TICK_ROW_CLS, DUPLICATE_SVG, Layout, EmptyState, FIELD_GAP, FormField, ToggleField, MediaPickerDialog, MediaPickerButton,
                 LinkPickerDialog, SettingsPanel, TagList, SaveStatus, EDIT_SVG, TRASH_SVG, RESTORE_SVG, VIEW_SVG, MOVE_SVG, CHECK_SVG, GEAR_SVG, X_SVG, COPY_SVG,
                 Pagination, rows_per_page, PageHeader, ListToolbar, glass_fill, PreviewScripts, LinkPickerResults,
                 DOCKED_FILL)
from soloblog.guards import is_local_path, status_redirect, undo_url

ar = APIRouter()
log = logging.getLogger(__name__)


def _toast_redirect(path: str, message: str, kind: str = "success", undo: str = ""):
    return status_redirect(path, message, kind, undo)

SLASH_MENU_JS = js.read("slash_menu.js")

EDITOR_INIT_JS = js.read("editor_init.js")

COPY_LINK_JS = js.read("copy_link.js")

PIN_LOCATION_JS = js.read("pin_location.js")

APPLY_TEMPLATE_JS = js.read("apply_template.js")


# every shortcut, for Windows and Mac - the command list's, plus the two
# the page itself answers (Save, and Esc)
def _shortcut_keys():
    rows = [("Save", "Ctrl+S", "Cmd+S")]
    rows += [(c["label"], editor_config.key_text(c["keys"]), editor_config.key_text(c["keys"], mac=True))
             for c in editor_config.COMMANDS if c["keys"]]
    rows.append(("Leave preview or Focus", "Esc", "Esc"))
    # Tab indents a line, so this is how the keyboard leaves the text
    rows.append(("Move out of the text", "Esc, then Tab", "Esc, then Tab"))
    return rows


_SHORTCUT_KEYS = _shortcut_keys()


def _icon(name):
    return NotStr(editor_icons.svg(name))


# The Help panel: what you can write, each with its example, the
# commands that write it (their icon, shortcuts and slash word) and an
# Insert button that puts the example in the post. By section; the
# editor's own buttons, the templates and every shortcut follow.
# (name, example, note, command ids, icon when there's no command)
_HELP = [
    ("start", "Writing", [
        ("Headings", "## Section\n### Sub-section", "## is a section of the post; ### a part of it.",
         ("heading", "subheading", "small-heading", "paragraph"), None),
        ("Emphasis", "**bold**, *italic*, ~~struck~~, `code`", None,
         ("bold", "italic", "strikethrough", "inline-code"), None),
        ("Links", "[text](https://example.com)\n[[Another post]]",
         "[[Title]] links one of your own posts - red while it doesn't exist yet. Type [[ for "
         "suggestions. Link to a post or page picks one from a list.", ("link", "link-picker", "wiki-link"), None),
        ("Lists", "- item\n1. numbered\n- [ ] to do\n- [x] done", None,
         ("unordered-list", "ordered-list", "check-list"), None),
        ("Image", "![Alt text](/uploads/photo.webp)",
         "Paste or drop one in, or pick one from your library. On its own line it shows its caption and credit.",
         ("library", "upload-image", "image"), None),
    ]),
    ("formatting", "Formatting", [
        ("Highlight", "==worth noticing==", None, ("highlight",), None),
        ("Superscript and subscript", "x^2^ and H~2~O", None, ("superscript", "subscript"), None),
        ("Keyboard keys", "Press ++ctrl+c++ to copy.", None, ("keys",), None),
        ("Emoji", ":coffee: :tada: :man:", "Shows the emoji itself. Type : and two letters for suggestions.",
         ("emoji",), None),
        ("Symbols", "(c) (tm) --> 1/2 1st", "Become © ™ → ½ and 1st with a raised st.", (), "copyright"),
        ("Quote", "> Something worth quoting", None, ("quote",), None),
    ]),
    ("blocks", "Blocks", [
        ("Code block", "```\nprint('hello')\n```", "Kept exactly as typed, in a fixed-width font.", ("code",), None),
        ("Table", "| Name | Role |\n|------|------|\n| Ann  | Owner |", None, ("table",), None),
        ("Callout", "!!! tip \"Good to know\"\n    Indented text inside it.", "Also note, warning and danger.",
         ("callout", "callout-tip", "callout-warning", "callout-danger"), None),
        ("Tabs", "=== \"First\"\n\n    In the first tab.\n\n=== \"Second\"\n\n    In the second tab.",
         "Readers switch between them - the same content for, say, Windows and Mac.", ("tabs",), None),
        ("Buttons", "Buttons: [Join](/join) [Read more](/about)", "On a line of its own. The first stands out.",
         ("buttons",), None),
        ("Collapsible", "??? \"A heading\"\n    The text it opens to.", "???+ starts it open.", ("collapsible",), None),
        ("Pull quote", "Pull quote: A line worth repeating.", "On a line of its own: big, set apart.",
         ("pull-quote",), None),
        ("Countdown", "Countdown: 12 March 2027", "Days to go, then just the date once it's passed.",
         ("days-to-go",), None),
        ("Divider", "---", "A line across the post.", ("horizontal-rule",), None),
        ("Members only from here", "<!-- members only from here -->",
         "On a post for members: everyone reads up to here, members read on.", ("members-cut",), None),
        ("Footnote", "A claim.[^1]\n\n[^1]: The source.", None, ("footnote",), None),
        ("Definition", "Term\n: What it means", None, ("definition",), None),
        ("Abbreviation", "*[HTML]: HyperText Markup Language", "Hovering HTML anywhere in the post shows it.",
         ("abbreviation",), None),
        ("Diagram", "```mermaid\ngraph LR; Idea --> Post\n```", ("Shows once diagrams are on.", "Turn it on", "/admin/settings?tab=editor&panel=editor-markdown"),
         ("diagram",), None),
        ("Math", "$E = mc^2$  or  $$ ... $$", ("Shows once math is on.", "Turn it on", "/admin/settings?tab=editor&panel=editor-markdown"), ("math",),
         None),
    ]),
    ("media", "Media", [
        ("Gallery", "```gallery masonry\n/uploads/a.webp\n/uploads/b.webp | A caption\n```",
         "Styles: grid, masonry, justified, slider, filmstrip. The Gallery button builds this for you.",
         ("gallery",), None),
        ("Video or post embed", "https://www.youtube.com/watch?v=...",
         "A link alone on a line: YouTube, Vimeo, Spotify, Mastodon, X, Facebook, Instagram, TikTok. "
         "It loads only when the reader clicks.", ("embed",), None),
        ("Map", "https://www.openstreetmap.org/#map=15/51.507/-0.128", "OpenStreetMap or Google Maps links.",
         (), "map"),
        ("Form", "https://tally.so/r/abc123", "Tally, Typeform, Google Forms, Jotform, Microsoft Forms, Airtable.",
         (), "clipboard-list"),
        ("Audio or video file", "/uploads/episode.mp3", "Upload it in Media, then put its link on its own line.",
         (), "file-audio"),
    ]),
    # sections - in any post (sections.REGISTRY), the same list as Insert's
    ("sections", "Sections", [
        (entry["label"], section_registry.markdown(key), f"{entry['about']}.", (f"section-{key}",), None)
        for key, entry in section_registry.REGISTRY.items()]),
]
# the editor's own buttons - they change how you write, not what
# said once at the top of a section, not under every entry
_HELP_INTRO = {
    "sections": ("In any post or page: a ## heading, then a Section: line saying what kind it is. It runs to the "
                 "next ##. The Go to button, beside Insert on the toolbar, jumps to one. ", "Every section", "/admin/help?tab=sections-templates#sections"),
}
UNLISTED_NOTE = "It's in the {place}, so anyone can still open it there - it's left out of search and feeds"
_HELP_EDITOR = ("insert", "preview", "side-by-side", "fullscreen", "clean-block", "undo", "redo")
_HELP_JUMPS = (("start", "Writing"), ("blocks", "Blocks"), ("media", "Media"), ("sections", "Sections"),
               ("templates", "Templates"), ("keys", "Key: values"), ("editor", "Editor"),
               ("shortcuts", "Shortcuts"))


def _slash_word(c):
    """What to type after / to find a command: its name, or its first
    slash word when the name is two words (a space closes the menu)."""
    return c["label"].lower() if " " not in c["label"] else c["slash"][0] if c["slash"] else ""


def _keys(keys):
    # a phone has no keyboard to press them on; a Mac shows Cmd (EDITOR_HELP_JS)
    return Kbd(editor_config.key_text(keys), data_mac=editor_config.key_text(keys, mac=True),
               cls="kbd kbd-xs max-sm:hidden")


# where each short entry is explained in full - by default, its group's
# place; a mark, its own heading in Reference > Markdown and extras
_MD = "reference.md#"
_HELP_MORE = {"start": "writing.md#write-and-format-a-post", "formatting": _MD + "text-styles",
              "blocks": _MD + "callouts-tabs-and-other-blocks", "media": "writing.md#embed-from-other-sites",
              "Headings": _MD + "paragraphs-and-headings", "Emphasis": _MD + "text-styles", "Links": _MD + "links",
              "Lists": _MD + "lists", "Quote": _MD + "quotes", "Pull quote": _MD + "quotes",
              "Code block": _MD + "code", "Diagram": _MD + "code", "Table": _MD + "tables-and-dividers",
              "Divider": _MD + "tables-and-dividers", "Footnote": _MD + "notes-terms-and-abbreviations",
              "Definition": _MD + "notes-terms-and-abbreviations",
              "Abbreviation": _MD + "notes-terms-and-abbreviations", "Math": _MD + "videos-maps-and-math",
              "Image": "writing.md#add-images-and-galleries", "Gallery": "reference.md#galleries",
              "Audio or video file": "writing.md#add-video-audio-and-pdfs",
              "Members only from here": "grow.md#let-readers-become-members"}


def _help_entry(name, example, note, ids, icon, more=""):
    cmds = [editor_config.COMMAND[i] for i in ids]
    keys = [c["keys"] for c in cmds if c["keys"]]
    slash = _slash_word(cmds[0]) if cmds and cmds[0]["slash"] else ""
    # a note can end with a link: (text, link words, where)
    text, link = (note[0], A(note[1], href=note[2], cls="link")) if isinstance(note, tuple) else (note, None)
    words = " ".join([name, example, text or ""] + [c["label"] + " " + " ".join(c["slash"]) for c in cmds])
    meta = [_keys(k) for k in keys] + ([Span(f"/{slash}", cls="font-mono")] if slash else [])
    return Div(
        Div(Span(_icon(icon or cmds[0]["icon"]), cls="flex text-base-content/70"),
            P(name, cls="font-medium flex-1"),
            # a row's action: an icon named by its tooltip (ui.IconAction) - in
            # words, it left a long name a word a line
            IconAction(PLUS_SVG, "Insert", menu_label=False, size="sm", type="button", tip="tooltip-left",
                       data_help_insert=True, aria_label=f"Insert {name}"),
            cls="flex items-center gap-2"),
        Pre(Code(example), cls="bg-base-200 rounded-box px-3 py-2 text-xs overflow-x-auto my-1 whitespace-pre-wrap"),
        P(text, " ", link, " " if note else "", _help_link(more, "More") if more else None,
          cls="text-xs text-base-content/60") if note or more else None,
        Div(*meta, cls="flex flex-wrap items-center gap-1 text-xs text-base-content/60") if meta else None,
        data_help_entry=True, data_words=words.lower(), cls="py-2")


def _help_intro(key):
    if key not in _HELP_INTRO:
        return None
    text, link, href = _HELP_INTRO[key]
    return P(text, A(link, href=href, target="_blank", cls="link"), ", in full.",
             cls="text-xs text-base-content/60 mb-1")


def _help_section(key, title, *content, words=None, cls=""):
    return Section(H3(title, cls="font-semibold text-sm mt-4 mb-1"), *content, data_help_section=key,
                   data_words=words, cls=cls)


def _help_editor_row(c):
    return Li(Span(_icon(c["icon"]), cls="flex text-base-content/70"),
              Div(P(c["label"], cls="font-medium"), P(c["about"], cls="text-xs text-base-content/60")),
              _keys(c["keys"]) if c["keys"] else None,
              data_help_entry=True, data_words=f"{c['label']} {c['about']} {' '.join(c['slash'])}".lower(),
              cls="list-row items-center px-0 py-2")


def _help_link(target, words="In Help"):
    """A link into the guide, in a new tab - from a page's own link
    (reference.md#galleries, #section-pricing in Sections and
    templates) to the admin's Help page."""
    from soloblog.routes.help_routes import HELP_PAGES
    page, _, anchor = target.partition("#")
    tab = next((k for k, f in HELP_PAGES.items() if f.endswith("/" + page) or f == page), "sections-templates") \
        if page else "sections-templates"
    # the guide links GitHub's way (#project--photo-story), Help's ids have one dash
    anchor = re.sub("-{2,}", "-", anchor)
    return A(words, href=f"/admin/help?tab={tab}" + (f"#{anchor}" if anchor else ""), target="_blank", cls="link")


def _anchor(heading):
    # the id Help gives a heading: "Section: Pricing" is section-pricing
    return re.sub(r"[\s-]+", "-", re.sub(r"[^\w\s-]", "", heading.lower())).strip("-")


def _key_index():
    """Every Key: value, from the guide's own index (Sections and
    templates > Key: value index) - so the panel and the guide never
    disagree: [(key cell, where, values, link)]."""
    from soloblog.routes.help_routes import DOCS_DIR
    try:
        text = Path(f"{DOCS_DIR}/guide/sections-templates.md").read_text(encoding="utf-8")
    except OSError:
        return []
    part = text.split("## Key: value index", 1)[-1]
    rows = []
    for line in part.splitlines():
        if not line.startswith("| ") or line.startswith("| Key ") or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split(" | ")]
        if len(cells) != 4:
            continue
        link = re.search(r"\]\(([^)]*)\)", cells[3])
        rows.append((cells[0], cells[1], cells[2], link.group(1) if link else ""))
    return rows


def _inline(text):
    """`code` in a line of the guide as code, the rest as it is."""
    return [Code(part, cls="text-xs") if i % 2 else part for i, part in enumerate(text.split("`")) if part]


def _keys_for(name):
    """The keys a section reads, by its name in the index's Where."""
    return [re.findall(r"`([^`]+)`", key)[0] for key, where, *_ in _key_index()
            if "`" in key and name in [w.strip() for w in where.split(",")]]


def _help_row(name, about, body, words, icon=None):
    """One of a long list, folded to its name - opening to its example,
    the lines it reads and Insert. A search opens the ones it finds."""
    return Details(
        Summary(Span(_icon(icon), cls="flex text-base-content/70") if icon else None,
                Span(Span(name, cls="font-medium"), Span(about, cls="block text-xs text-base-content/60 truncate"),
                     cls="flex-1 min-w-0"),
                Span(CHEVRON_DOWN_SVG, cls="flex text-base-content/50 transition-transform group-open/row:rotate-180"),
                cls="flex items-center gap-2 py-2 cursor-pointer list-none [&::-webkit-details-marker]:hidden"),
        Div(*body, cls="pb-3 ps-6"),
        data_help_entry=True, data_words=words.lower(),
        cls="group/row border-b-[length:var(--border)] border-base-300 last:border-0")


def _help_example(example, insert_name):
    return Div(Pre(Code(example), cls="bg-base-200 rounded-box px-3 py-2 text-xs overflow-x-auto my-1 "
                                       "whitespace-pre-wrap"),
               IconAction(PLUS_SVG, "Insert", menu_label=False, size="sm", type="button", tip="tooltip-left",
                          data_help_insert=True, aria_label=f"Insert {insert_name}"),
               data_help_example=True, cls="flex items-start gap-1 [&>pre]:flex-1 [&>pre]:min-w-0")


def _keys_line(keys):
    return P("Reads ", *[el for i, k in enumerate(keys) for el in ((", " if i else ""), Code(k, cls="text-xs"))], ".",
             cls="text-xs text-base-content/60 mt-1") if keys else None


def _help_sections():
    """Every section, folded: an intro with its Key: lines, then each kind
    with its example, the keys it reads and a link to its entry."""
    rows = []
    for key, entry in section_registry.REGISTRY.items():
        label, about, snippet = entry["label"], entry["about"], section_registry.markdown(key)
        cmd = editor_config.COMMAND[f"section-{key}"]
        rows.append(_help_row(label, about, (
            _help_example(snippet, label),
            _keys_line(_keys_for(label)),
            P(Span(f"/{_slash_word(cmd)}", cls="font-mono"), " · ", _help_link(f"#section-{_anchor(label)}"),
              cls="text-xs text-base-content/60 mt-1"),
        ), f"{label} {about} {snippet} section {' '.join(cmd['slash'])}", entry["icon"]))

    def lower(words):
        return words[0].lower() + words[1:]
    lines = [(f"{name}: {label}", lower(about)) for name in section_registry.SHARED
             for _, label, about, _ in section_registry.values(name)]
    cover = section_registry.COVER
    labels = section_registry.cover_labels()
    lines.insert(lines.index(("Style: Card", lower(section_registry.values("Style")[0][2]))) + 1,
                 (f"Style: {cover[1]}", f"{lower(cover[2])}, on {', '.join(labels[:-1])} and {labels[-1]} only"))
    lines += [(f"{name}: {section_registry.DEFAULT}", lower(section_registry.OPTIONS[name]["default"]))
              for name in section_registry.SHARED]
    looks = Div(
        P(Span("Width, style, heading, space and appear", cls="font-medium"), cls="mb-1"),
        Ul(*[Li(Code(line, cls="text-xs"), " - ", what, cls="py-0.5") for line, what in lines], cls="text-xs"),
        P("On a line under Section:. Default is the same as no line. Or put your cursor in the section and "
          "open Insert: its options come first. ", _help_link("#width-style-heading-space-and-appear"),
          cls="text-xs text-base-content/60 mt-1"),
        data_help_entry=True,
        data_words="width style heading centred left column wide full card cover space room gap small large "
                   "appear motion animation fade rise zoom slide default section look",
        cls="rounded-box bg-base-200 px-3 py-2 my-2")
    return looks, *rows


def _help_templates():
    """The built-in templates and the custom ones, each with its sections."""
    def row(name, body, custom=False):
        extra = ", ".join(section_names(body))
        return Li(Span(name, cls="font-medium"),
                  Span("Custom", cls="badge badge-xs badge-ghost ms-1") if custom else None,
                  P(extra, cls="text-xs text-base-content/60") if extra else None,
                  data_help_entry=True, data_words=f"{name} {extra} template".lower(), cls="py-1")
    built = [row(name, body) for name, body in post_templates.BUILT_IN.values()]
    mine = [row(t["name"], t["body"], True) for t in post_templates.saved()]
    return Ul(*mine, *built, cls="text-sm")


def _help_keys():
    """Every Key: value, A to Z, from the guide's index."""
    return Ul(*[Li(P(*_inline(key), cls="text-xs"),
                   P(where.replace("`", ""), " - ", *_inline(values), " ",
                     _help_link(link, "More") if link else None, cls="text-xs text-base-content/60"),
                   data_help_entry=True, data_words=f"{key} {where} {values} key value".lower().replace("`", ""),
                   cls="py-1.5 border-b-[length:var(--border)] border-base-300 last:border-0")
                for key, where, values, link in _key_index()])


EDITOR_HELP_JS = js.read("editor_help.js")


def EditorHelpPanel():
    """The editor's one Help panel (Ctrl+/, the Help button, /help): what
    you can write with an example of each and Insert, the editor's own
    buttons, the templates and every shortcut - searchable, and the
    full user guide at its foot."""
    return (
        Div(id="editor-help-backdrop", cls=DRAWER_BACKDROP,
            **on("click", "toggleEditorHelp", False)),
        Aside(Div(
            # its title, search and where to jump stay at the top as it scrolls
            Div(
                Div(H2("Help", cls="font-semibold"),
                    Button(X_SVG, type="button", cls="btn btn-sm btn-ghost btn-square tooltip tooltip-left",
                           data_tip="Close", aria_label="Close help", **on("click", "toggleEditorHelp", False)),
                    cls="flex items-center justify-between mb-2"),
                SearchBox(placeholder="Search help… try table or video", aria_label="Search help", autocomplete="off"),
                # a row you swipe along on a phone
                # a phone has no keyboard, so no Shortcuts part to jump to
                Div(*[Button(title, type="button", data_help_jump=key,
                             cls="btn btn-xs btn-ghost shrink-0" + (" max-sm:hidden" if key == "shortcuts" else ""))
                      for key, title in _HELP_JUMPS],
                    data_scroll_x=True, cls=f"flex sm:flex-wrap gap-1 overflow-x-auto -mx-1 px-1 mt-2 {SCROLLS_X}"),
                # solid, not frosted - what scrolls under it showed through
                # its words
                id="editor-help-head", cls="sticky top-0 z-10 -mx-3 px-3 pt-3 pb-2 bg-base-100"),
            Div(Span(cls="text-xs text-base-content/60"),
                Button(X_SVG, Span("Clear search", cls="ml-1"), type="button", cls="btn btn-sm"),
                id="editor-help-count", hidden=True,
                cls="flex items-center justify-between gap-2 rounded-box bg-base-200 px-3 py-1.5 mt-3"),
            P("Nothing here - try another word, or ",
              A("search all of Help", id="editor-help-guide-search", href="/admin/help", target="_blank",
                cls="link"), ".", id="editor-help-empty", hidden=True, cls="text-sm text-base-content/60 mt-4"),
            # the parts come the first time Help opens (EditorHelpParts,
            # /admin/editor/help) - 2,000 of them, half the editor's page
            Div(id="editor-help-parts"),
            Div(A(pages._icon(pages.EXTERNAL_ICON), Span("Full user guide", cls="ml-1"), href="/admin/help",
                  id="editor-help-guide", target="_blank", cls="btn btn-sm"),
                cls="mt-6 mb-2"),
            # the fade is a mask: on the panel itself it would fade its fill too.
            # Hidden while the panel is closed: off screen, its 2,000 parts were
            # still laid out on every key typed, slowing the editor down
            id="editor-help-scroll", data_scroll_hint=True,
            cls=f"relative hidden h-full overflow-y-auto overscroll-contain px-3 pb-3 {SCROLLS}"),
            id="editor-help-panel", aria_label="Help", inert=True, data_own_scroll=True,
            cls=f"fixed inset-y-0 right-0 z-40 {DRAWER_W} translate-x-full "
                f"{glass_fill(settings.get_all())} text-sm shadow-xl transition-transform duration-200"
        ),
    )


def EditorHelpParts():
    """What the editor's Help panel holds: what you can write with an
    example of each and Insert, the sections and templates, the editor's
    own buttons, Focus and every shortcut."""
    editor_rows = [editor_config.COMMAND[i] for i in _HELP_EDITOR]
    return (
        *[_help_section(key, title, _help_intro(key),
                        *[_help_entry(*e, more=_HELP_MORE.get(e[0], _HELP_MORE.get(key, ""))) for e in entries])
          for key, title, entries in _HELP if key != "sections"],
        _help_section("sections", "Sections", _help_intro("sections"), *_help_sections()),
        _help_section(
            "templates", "Templates",
            P("A new post starts from the one chosen in Settings > Editor; the Template label above a new "
              "post starts it from another. Apply one to a post in Post settings > Template, and save any "
              "post as a custom one there. ", _help_link("#templates", "Every template"),
              ", in full.", cls="text-xs text-base-content/60 mb-1"),
            _help_templates()),
        _help_section(
            "keys", "Key: values",
            P("A key, a colon and a value on a line of its own, like Price: €12 - readers never see it. ",
              _help_link("put-together.md#writing-a-key-value", "Writing a Key: value"), ".",
              cls="text-xs text-base-content/60 mb-1"),
            _help_keys()),
        _help_section("editor", "Editor", Ul(*[_help_editor_row(c) for c in editor_rows], cls="list")),
        # what's in Focus mode, beyond the button that opens it
        _help_section(
            "focus", "Focus",
            Ul(*[Li(Span(name, cls="font-medium"), " - ", about, cls="py-1") for name, about in (
                ("Only your words", "start typing and the bars slide away; move the mouse to bring them back"),
                ("Typewriter scrolling", "the line you're writing stays in the middle of the screen"),
                ("Fade", "the paragraph or sentence you're in stays bright, the rest steps back"),
                ("Writing session", "the timer: 25 or 50 minutes, 500 or 1,000 words, or your own - "
                                    "a thin line along the top fills as you go"),
                ("A− and A+", "the writing smaller or larger, just in Focus"),
                ("Esc", "leaves Focus"),
            )], cls="text-sm"),
            P(A("Focus settings", href="/admin/settings?tab=editor&panel=editor-focus", cls="link"),
              " set how each of them behaves.", cls="text-xs text-base-content/60 mt-1"),
        ),
        _help_section(
            "shortcuts", "Shortcuts",
            P("On a Mac they use Cmd.", cls="text-xs text-base-content/60 mb-1 max-sm:hidden"),
            Table(Tbody(*[Tr(Td(action), Td(Kbd(win, data_mac=mac, cls="kbd kbd-sm"), cls="text-right"),
                             data_help_entry=True, data_words=f"{action} {win} shortcut keys".lower())
                          for action, win, mac in _SHORTCUT_KEYS]),
                  cls="table table-sm"),
            # a phone has no keyboard to press them on
            words="keyboard shortcuts keys", cls="max-sm:hidden"),
    )


@ar.get("/admin/editor/help")
def editor_help_parts(session):
    # just the parts, not a page around them: the panel's script puts them in
    return HTMLResponse(to_xml(Div(*EditorHelpParts())))


def InsertSearch():
    """The search box at the top of the editor's Insert list, for its
    script (SLASH_MENU_JS) to copy."""
    return Template(SearchBox(placeholder="Search…", aria_label="Search what to insert", autocomplete="off"),
                    id="insert-search")


# the markdown editor - loaded only on the editor pages, not on every
# page of the site the way it used to be
EDITOR_ASSETS = (
    Link(rel="stylesheet", href="/static/vendor/easymde-2.20.0/easymde.min.css"),
    Script(src="/static/vendor/easymde-2.20.0/easymde.min.js", nonce=csp.NONCE),
)


def RevisionsPanel(slug):
    """Earlier versions of this post. Restore only loads one into the
    editor - nothing is saved until Save, and Discard undoes it - so
    looking back is never destructive."""
    return SettingsPanel("History", RevisionsList(slug), RevisionDiffDialog(), open_=False, key="history")


def RevisionsList(slug, oob=False):
    """History's list: the post as it is now, then each earlier version,
    newest first - when it was written, its words and how many more or
    fewer than the one before. Compare shows what that version changed;
    Restore loads it. Sent again with every save (oob), so the version a
    save just kept is there without reloading the page."""
    revisions = posts.list_revisions(slug)
    if not revisions:
        return Div(P("Earlier versions appear here each time you save a change to the words.",
                     cls="text-xs text-base-content/60"),
                   id="history-list", hx_swap_oob="true" if oob else None)
    now = posts.current_version(slug)

    def compare(url):
        # innerHTML: inside the post form, it'd inherit the form's
        # outerHTML swap and replace #revision-diff itself, leaving the
        # next Compare nowhere to go
        # row actions are icons, named by their tooltips (ui.IconAction) -
        # with words, two buttons squeezed the date to a word a line
        # the list scrolls in its box, which cuts off a tooltip above the first row
        return IconAction(VIEW_SVG, "Compare", menu_label=False, size="sm", type="button", tip="tooltip-left",
                          data_open_dialog="revision-diff-dialog", hx_get=url, hx_target="#revision-diff",
                          hx_swap="innerHTML")

    def row(when, version, buttons, current=False):
        words = f"{version['words']:,} word{'s' if version['words'] != 1 else ''}"
        if version["added"]:
            words += " · " + f"{version['added']:+,}".replace("-", "−")
        return Div(
            Div(P(Span("Now · ", cls="font-medium") if current else None, when, cls="text-sm"),
                P(words, cls="text-xs text-base-content/50 truncate"), cls="min-w-0"),
            Div(*buttons, cls="join shrink-0"),
            cls="flex items-center justify-between gap-2 py-1.5 border-b-[length:var(--border)] "
                "border-base-300 last:border-0"
        )
    rows = [row(_when(now["written_at"]), now, [compare(f"/admin/history/{slug}/now")], current=True)]
    for r in revisions:
        when = _when(r["written_at"]) if r["written_at"] else f"Before {_when(r['saved_at'])}"
        rows.append(row(when, r, [
            compare(f"/admin/revisions/{r['id']}/diff"),
            IconAction(RESTORE_SVG, "Restore", menu_label=False, size="sm", type="button", tip="tooltip-left",
                       data_revision=r["id"], data_when=when[0].lower() + when[1:] if r["written_at"] is None else when,
                       **on("click", "restoreRevision", EL))]))
    return Div(Div(*rows, cls="max-h-64 overflow-y-auto"), id="history-list",
               hx_swap_oob="true" if oob else None)


def RevisionDiffDialog():
    """History > Compare: what one version changed from the one before it
    (RevisionChanges, filled in when it opens)."""
    return Dialog(
        Div(
            H3("What changed", id="revision-diff-title", cls="font-semibold mb-1"),
            Div(Span(cls="loading loading-spinner loading-sm"), id="revision-diff",
                cls="max-h-[60vh] overflow-y-auto"),
            Div(Button(X_SVG, Span("Close", cls="ml-1"), type="button", cls="btn btn-sm",
                       data_close_dialog="revision-diff-dialog"), cls="modal-action"),
            cls="modal-box max-w-3xl"
        ),
        Form(Button(cls="cursor-default", aria_label="Close"), method="dialog", cls="modal-backdrop"),
        id="revision-diff-dialog", aria_labelledby="revision-diff-title", cls="modal"
    )


def RevisionChanges(when, before, after, first=False):
    """Compare's answer: whose changes these are, the key to the colours,
    and the diff. before is None for the oldest version kept - all of it
    is shown as written then."""
    if before is None:
        intro = P(f"The version from {when} is the oldest kept" + ("" if first else
                  " - the ones before it are no longer kept") + ", so here it is as it was written.",
                  cls="text-xs text-base-content/60 mb-3")
    else:
        intro = P(f"In the version from {when}: ", Span("red", cls="text-error font-medium"), " was taken out, ",
                  Span("green", cls="text-success font-medium"), " was added.",
                  cls="text-xs text-base-content/60 mb-3")
    return (intro,
            RevisionDiff(before["title"] if before else after["title"], before["body"] if before else "",
                         after["title"], after["body"]))


def RevisionDiff(old_title, old_body, title, body):
    """A line-by-line diff, with two lines of context around each change
    and ⋯ for the unchanged stretches between."""
    import difflib
    rows = []
    if old_title != title:
        rows += [Div(Span("−", cls="w-4 shrink-0"), Span(f"Title: {old_title}"), cls="flex bg-error/15 px-2"),
                 Div(Span("+", cls="w-4 shrink-0"), Span(f"Title: {title}"), cls="flex bg-success/15 px-2")]
    hunks = 0
    for line in list(difflib.unified_diff(old_body.splitlines(), body.splitlines(), lineterm="", n=2))[2:]:
        if line.startswith("@@"):
            # between two stretches of changes - or before the first, when
            # it doesn't start at the top
            hunks += 1
            if hunks > 1 or not line.startswith(("@@ -1,", "@@ -0,", "@@ -1 ")):
                rows.append(Div("⋯", cls="px-2 text-base-content/40"))
        elif line.startswith("-"):
            rows.append(Div(Span("−", cls="w-4 shrink-0"), Span(line[1:] or " ", cls="whitespace-pre-wrap break-words min-w-0"),
                            cls="flex bg-error/15 px-2"))
        elif line.startswith("+"):
            rows.append(Div(Span("+", cls="w-4 shrink-0"), Span(line[1:] or " ", cls="whitespace-pre-wrap break-words min-w-0"),
                            cls="flex bg-success/15 px-2"))
        else:
            rows.append(Div(Span("", cls="w-4 shrink-0"), Span(line[1:] or " ", cls="whitespace-pre-wrap break-words min-w-0"),
                            cls="flex px-2 text-base-content/70"))
    if not rows:
        return P("No changes to the words - only the post's settings.", cls="text-sm text-base-content/60")
    return Div(*rows, cls="font-mono text-xs leading-relaxed rounded-box border-[length:var(--border)] "
                          "border-base-300 py-1")


def _when(iso: str) -> str:
    """"Sep 24, 2026 14:05" in the site's timezone - just the date for a
    value that has no time (an imported post's), rather than a made-up
    one."""
    from datetime import datetime
    if len(iso or "") <= 10:
        return format_date(iso)
    try:
        local = tz.to_local(datetime.fromisoformat(iso[:19]))
    except ValueError:
        return iso
    return f"{format_date(iso)} {local.strftime('%H:%M')}"


REVISIONS_JS = js.read("revisions.js")

# the editor's scripts in one file the browser keeps (/admin/editor.js),
# its address carrying a hash of them - inline, all 200 KB came again with
# every post opened. In the order they ran inline; each waits for the page
# (DOMContentLoaded) before touching it.
EDITOR_JS = "\n".join(part.strip() + "\n;" for part in (
    editor_config.fixed_prefs_script(), EDITOR_HELP_JS, SLASH_MENU_JS, EDITOR_INIT_JS, COPY_LINK_JS,
    PIN_LOCATION_JS, REVISIONS_JS, APPLY_TEMPLATE_JS))
EDITOR_JS_VERSION = hashlib.sha256(EDITOR_JS.encode("utf-8")).hexdigest()[:12]


@ar.get("/admin/editor.js")
def editor_js(session):
    return Response(EDITOR_JS, media_type="text/javascript; charset=utf-8",
                    headers={"Cache-Control": "private, max-age=31536000, immutable"})


def EditorScripts():
    """The editor's settings, then its scripts - after everything they work on."""
    return (Script(editor_config.prefs_script(settings.get_all()), nonce=csp.NONCE),
            Script(src=f"/admin/editor.js?v={EDITOR_JS_VERSION}", nonce=csp.NONCE))


@ar.get("/admin/emoji.json")
def emoji_json(session):
    from starlette.responses import JSONResponse
    from soloblog.render import emoji_list
    # the same for every post - the browser keeps it a day
    return JSONResponse(emoji_list(), headers={"Cache-Control": "private, max-age=86400"})


@ar.get("/admin/post-titles.json")
def post_titles_json(session, exclude: str = ""):
    """Every post and page, drafts too like the link picker, newest first:
    [title, slug, status] - what typing [[ in the editor suggests. The
    post being written (exclude) isn't in it. Status is empty for a
    published one."""
    from starlette.responses import JSONResponse
    rows = posts.pick_list("", limit=100000, exclude="")[0]
    return JSONResponse([[r["title"], r["slug"], "" if posts.post_status(r) in ("Published", "Pinned") else posts.post_status(r)]
                         for r in rows if r["slug"] != exclude], headers={"Cache-Control": "no-store"})


def TemplateCards(card, group_cls, start_key="", apply=False):
    """The template picker's cards - Recent, Custom, Built-in, each with the
    sections it has. A new post's cards are links to a post made from it
    (Blank first, as a link that says so, since an empty address follows
    Settings > Editor > New posts start from); Apply a template's press
    adds it to the post being written (apply_template.js)."""
    items, last = [], None
    for key, name, group in ([] if apply else [("", "Blank", "")]) + post_templates.choices():
        if group != last:
            if group:
                items.append(P(group, data_combo_group=group, cls=group_cls))
            last = group
        names = section_names(post_templates.get(key)["body"]) if key else []
        about = "An empty post" if not key else (
            ", ".join(names[:3]) + (f" and {len(names) - 3} more" if len(names) > 3 else "") if names else "Words only")
        parts = (Span(Span(name, cls="min-w-0"),
                      Span("Custom", cls="badge badge-xs badge-ghost shrink-0") if key.startswith("mine-") else None,
                      cls="flex items-center gap-1.5 font-semibold text-sm"),
                 Span(about, cls="text-xs text-base-content/70"))
        items.append(Div(
            Button(*parts, type="button", data_combo_pick=True, cls=card, **on("click", "applyTemplate", key)) if apply
            else A(*parts, href=f"/admin/new?template={key}", aria_selected="true" if key == start_key else "false",
                   cls=card),
            data_combo_item=f"{name} {about} {group}".lower()))
    return items


def TemplateDialog(start_key=None):
    """The templates, found by typing. Post settings > Template > Apply a
    template (start_key None) adds the chosen one to the post in the editor
    (apply_template.js); on a new post the Template label opens it with
    start_key set to the one the post started from ("" for Blank), and
    choosing one opens a new post from it, the unsaved-changes warning
    first if you've written something."""
    start = start_key is not None
    card = ("flex flex-col items-start gap-0.5 text-left w-full h-full rounded-box border border-base-300 p-3 "
            "hover:border-primary aria-selected:border-primary aria-selected:bg-base-200 cursor-pointer")
    group_cls = "col-span-full text-xs font-semibold text-base-content/60 pt-2 first:pt-0"
    dialog_id = "template-start-dialog" if start else "template-dialog"
    return Dialog(
        Div(H3("Choose a template" if start else "Apply a template", id=f"{dialog_id}-title", cls="font-semibold mb-1"),
            P("Opens a new post with its sections and settings." if start
              else "Adds its sections at the end and uses its settings.", cls="text-sm text-base-content/70 mb-3"),
            SearchBox("w-full mb-2", placeholder="Type to find…", aria_label="Find a template", autocomplete="off",
                      autofocus=True, **on("input", "filterCombo", EL)),
            Div(*TemplateCards(card, group_cls, start_key or "", apply=not start), data_scroll_hint=True,
                cls=f"grid grid-cols-2 sm:grid-cols-3 gap-2 max-h-[60vh] min-h-0 overflow-y-auto {SCROLLS}"),
            Div(Button(X_SVG, Span("Close", cls="ml-1"), type="button", cls="btn btn-sm",
                       data_close_dialog=dialog_id), cls=SEARCH_DIALOG_ACTION),
            data_combo="template-start" if start else "template-apply", cls=f"{SEARCH_DIALOG_BOX} max-w-3xl"),
        Form(Button(cls="cursor-default", aria_label="Close"), method="dialog", cls="modal-backdrop"),
        id=dialog_id, aria_labelledby=f"{dialog_id}-title", cls="modal modal-top sm:modal-middle"
    )


@ar.get("/admin/template/{key}")
def template_json(session, key: str):
    """A template's words and settings, for Apply a template. The key
    only ever finds a built-in template or one of the admin's own."""
    from starlette.responses import JSONResponse
    t = post_templates.get(key)
    if not t:
        return JSONResponse({"error": "not found"}, status_code=404)
    return JSONResponse({"name": t["name"], "body": t["body"], "tags": t["tags"], "summary": t["summary"],
                         "cover": t["cover"], "settings": post_templates.settings_of(t)})


OWN_SIDE_PLACES = [("under", "Under the post"), ("left", "On the left"), ("right", "On the right"), ("off", "Off")]


def _site_value(name):
    return settings.get(name) or settings.DEFAULTS.get(name, "")


def _site_default(choices, name):
    """A post's "follow the site" choice, saying what the site's is -
    "On the right (default)", the value first, as the box is narrow - so
    the post can be left to it knowingly."""
    value = _site_value(name)
    return Option(f"{choices.get(value, choices.get(settings.DEFAULTS.get(name), '')).split(' - ')[0]} (default)",
                  value="")


def _site_side_place(name, page=False):
    """Where the site puts a side panel on a post or a page (Settings >
    Blog layout): its place if it shows beside that kind, else off."""
    place = settings.get(f"side_{name}") or "off"
    shown_here = ("pages" if page else "posts") in (settings.get(f"side_{name}_where") or "").split(",")
    return place if shown_here else "off"


def _site_side(name, page=False):
    return dict(OWN_SIDE_PLACES).get(_site_side_place(name, page), "Off")


def _site_toc(page):
    """Where the site puts a post's or a page's contents: off where
    Shows on leaves that kind out (pages.toc_style)."""
    kind = "pages" if page else "posts"
    shows = (settings.get("toc_style_where") or "posts,pages").split(",")
    return _site_value("toc_style") if kind in shows else "off"


# Settings, opened at one setting (the search's own links, tab, panel and
# setting) - a test checks each is still there
SETTING_LINKS = {
    ("Shows on", "Contents and sections"): ("posts", "posts-contents"),
    ("Tag cloud", "Side panels"): ("blog", "blog-side"),
    ("Archive links", "Side panels"): ("blog", "blog-side"),
    ("About the author", "Side panels"): ("blog", "blog-side"),
    ("Allow comments", "Comments"): ("messages", "messages-comments"),
    ("Add a support link", "Support"): ("profile", "profile-support"),
    ("Bio", ""): ("profile", "profile-bio"),
    ("Readers subscribe with", "Newsletter"): ("newsletter", "newsletter-main"),
    ("Reader reactions", "Reading"): ("posts", "posts-reading"),
    ("Each post in the list shows", "Blog layout"): ("blog", "blog-layout"),
}


def _setting_href(name, panel):
    tab, key = SETTING_LINKS[(name, panel)]
    return f"/admin/settings?tab={tab}&panel={key}" + (f"&setting={quote(name)}" if panel else "")


def SiteTurnsOff(text, name, panel, link="Change in Settings"):
    """A setting here that the site's Settings turns off for this post:
    what that means, and a link straight there - shown only while it's so
    (docs/DEVELOPMENT.md > Writing and settings)."""
    return P(f"{text} ", A(link, href=_setting_href(name, panel), cls="link"),
             cls="text-xs text-base-content/60")


TITLE_STYLES = {"": "Left (default)", "centre": "Centred", "hidden": "Hidden"}
PAGE_WIDTHS = {"": "Column (default)", "wide": "Wide"}


def PagePanel(row, start=None, page=False):
    """The page's frame and kind (Post settings > Page): how it's
    presented (pages.py) - its title and width, what shows around it, and a folded
    group of the less common settings. Each setting that follows the
    site gets a bar and Reset while this page sets it differently
    (CUSTOM_TAGS_JS), the panel's heading counting them.
    start - a new post's, from the template it starts from.
    page - it's in the menu or the footer, where the site shows less."""
    start = start or {}
    page = posts.is_page(row) if row else page
    # a new post's settings are its template's
    chosen = {} if row else post_templates.settings_of(start)
    shown = pages.shown_extras(row) if row else pages.shown_from(chosen.get("extras", ""), page)
    site_shown = pages.default_extras(page)

    def own(name):
        return row[name] if row else chosen.get(name, "")

    link_url, title_style, page_width = own("link_url"), own("title_style"), own("page_width")
    more = [own("slides"), own("in_wiki"), own("remind_update"), link_url]
    own_sides = dict(part.split("=", 1) for part in (row["sides"] if row else chosen.get("sides", "")).split(",")
                     if "=" in part)
    # what the site does for each setting that follows it: a choice is
    # changed when it's set and isn't that (choosing what the site has isn't
    # changed, though it won't follow the site any more); the page's width
    # follows the site's column, so any width of its own is
    sites = {"toc_style": _site_toc(page), "heading_fold": _site_value("heading_fold"),
             "cover_width": _site_value("cover_width"), "section_space": _site_value("section_space"),
             "section_motion": _site_value("section_motion"), "page_width": "", **{f"sides_{n}": _site_side_place(n, page) for n in ("tags", "archive", "author")}}
    values = {**{n: own(n) for n in sites if not n.startswith("sides_")},
              **{f"sides_{n}": own_sides.get(n, "") for n in ("tags", "archive", "author")}}
    custom = {n: bool(values[n]) and values[n] != site for n, site in sites.items()}
    differing_ticks = {key for key in pages.EXTRAS if (key in shown) != (key in site_shown)}
    extras_notes = ExtrasNotes()
    return SettingsPanel(
        "Page",
        Div(
            FormField("Title", Select(
                *[Option(label, value=key, selected=(title_style == key)) for key, label in TITLE_STYLES.items()],
                name="title_style", cls="select select-sm w-full")),
            FormField("Page width", Select(
                *[Option(label, value=key, selected=(page_width == key)) for key, label in PAGE_WIDTHS.items()],
                name="page_width", data_site_value=sites["page_width"], cls="select select-sm w-full"),
                custom=bool(custom["page_width"])),
            FormField("Contents", Select(
                Option(f"{pages.TOC_STYLES.get(sites['toc_style'], 'Off')} (default)", value=""),
                *[Option(label, value=key, selected=(values["toc_style"] == key))
                  for key, label in pages.TOC_STYLES.items()],
                name="toc_style", data_site_value=sites["toc_style"], cls="select select-sm w-full"),
                # off only because Shows on leaves this kind out: say so, and where
                SiteTurnsOff(f"Contents are off for {'pages' if page else 'posts'}.", "Shows on",
                             "Contents and sections")
                if sites["toc_style"] == "off" and _site_value("toc_style") != "off" else None,
                custom=bool(custom["toc_style"])),
            FormField("Fold headings", Select(
                _site_default(pages.FOLD_STYLES, "heading_fold"),
                *[Option(label, value=key, selected=(values["heading_fold"] == key))
                  for key, label in pages.FOLD_STYLES.items()],
                name="heading_fold", data_site_value=sites["heading_fold"], cls="select select-sm w-full"),
                custom=bool(custom["heading_fold"])),
            FormField("Cover image", Select(
                _site_default(pages.COVER_STYLES, "cover_width"),
                *[Option(label.split(" - ")[0], value=key, selected=(values["cover_width"] == key))
                  for key, label in pages.COVER_STYLES.items()],
                name="cover_width", data_site_value=sites["cover_width"], cls="select select-sm w-full"),
                custom=bool(custom["cover_width"])),
            FormField("Space between sections", Select(
                _site_default(pages.SPACINGS, "section_space"),
                *[Option(label, value=key, selected=(values["section_space"] == key))
                  for key, label in pages.SPACINGS.items()],
                name="section_space", data_site_value=sites["section_space"], cls="select select-sm w-full"),
                custom=bool(custom["section_space"])),
            FormField("Sections appear", Select(
                _site_default(pages.SECTION_MOTIONS, "section_motion"),
                *[Option(label, value=key, selected=(values["section_motion"] == key))
                  for key, label in pages.SECTION_MOTIONS.items()],
                name="section_motion", data_site_value=sites["section_motion"], cls="select select-sm w-full"),
                custom=bool(custom["section_motion"])),
            # this post's own places for the side panels - greyed out while
            # Show leaves them out altogether (data-off-unless, ACTIONS_JS)
            Div(*[FormField(label, Select(
                    Option(f"{_site_side(name, page)} (default)", value=""),
                    *[Option(text, value=key, selected=own_sides.get(name) == key) for key, text in OWN_SIDE_PLACES],
                    name=f"sides_{name}", data_site_value=sites[f"sides_{name}"], cls="select select-sm w-full"),
                    SiteTurnsOff(f"Off for {'pages' if page else 'posts'}.", label, "Side panels")
                    if sites[f"sides_{name}"] == "off" and (settings.get(f"side_{name}") or "off") != "off" else None,
                    custom=bool(custom[f"sides_{name}"]))
                  for name, label in (("tags", "Tag cloud"), ("archive", "Archive links"),
                                      ("author", "About the author"))],
                P("Beside the post where there's room - under it on a phone, on a wide page or on slides.",
                  cls="text-xs text-base-content/60"),
                P("Off for this post: Side panels isn't ticked under Show.", data_off_note=True, hidden=True,
                  cls="text-xs text-warning"),
                data_off_unless="extras=sides", cls="grid gap-3"),
            cls="grid gap-3"
        ),

        SoundField(row),
        FormField("Show", Div(Div(
            # what the site shows on its own (Settings > Posts > Each post shows),
            # a page's own fewer for a page. A tick that differs loses its
            # Default tag
            *[Label(Input(type="checkbox", name="extras", value=key, cls="checkbox checkbox-xs",
                          checked=key in shown, data_site_value="1" if key in site_shown else "0"),
                    Span(label, cls="text-sm"),
                    Span("Default", data_default_tag=True,
                         cls=f"{DEFAULT_TAG}{' hidden' if key in differing_ticks else ''}")
                    if key in site_shown else None,
                    data_default_field=True, cls="flex items-center gap-2 cursor-pointer")
              for key, label in pages.EXTRAS.items()],
            # two columns where the panel has room - in a phone's 320 px,
            # "Reading progress bar" broke a word a line
            cls="grid @xs:grid-cols-2 gap-2"),
            cls="@container"),
            # what it was, so a post that's only moved to the menu still
            # follows the page default instead of keeping a post's extras
            Input(type="hidden", name="extras_before", value=row["extras"] if row else ""),
            Input(type="hidden", name="extras_before_page", value="1" if row and posts.is_page(row) else ""),
            help="Around the text.", cls="" if extras_notes else FIELD_GAP, custom=bool(differing_ticks)),
        # ticks that show nothing until something's set up, or the site has them off
        Div(extras_notes, cls=FIELD_GAP) if extras_notes else None,
        # what few pages use, in one fold that opens by itself when the
        # page uses one of them
        Details(
            Summary("More", cls="cursor-pointer w-fit link link-hover py-2 text-sm font-medium"),
            Div(ToggleField("Show as slides", "slides", checked=bool(own("slides")),
                            help="Each part between --- lines is a slide.", cls=FIELD_GAP),
                ToggleField("In the wiki", "in_wiki", checked=bool(own("in_wiki")),
                            help="Listed on the wiki's front page, not in the blog.", cls=FIELD_GAP),
                ToggleField("Remind me to update", "remind_update", checked=bool(own("remind_update")),
                            help="Shows when it was last updated, and reminds you after three months.", cls=FIELD_GAP),
                FormField("Link to", Div(Input(name="link_url", id="link_url", value=link_url, inputmode="url",
                                               autocomplete="off", placeholder="https://example.com/the-article",
                                               cls="input input-sm flex-1 min-w-0 join-item"),
                                         LinkPickerButton("link_url"), cls="join w-full"),
                          help="The page this post is about. Its title links there."),
                cls="pt-2"),
            open=any(more), id="page-more"),
        open_=bool(title_style or page_width or any(more) or (row and (
            row["toc_style"] or row["heading_fold"] or row["cover_width"] or row["section_space"]
            or row["section_motion"] or row["extras"] or row["sound"] or row["sides"])) or any(chosen.get(n) for n in (
                "toc_style", "heading_fold", "cover_width", "section_space", "section_motion", "sides", "extras"))),
        # Show is one setting, however many of its ticks differ
        custom=sum(custom.values()) + bool(differing_ticks),
        key="page"
    )


def ExtrasNotes():
    """Under Show: each tick that shows nothing on any post yet - what it
    needs, with a link straight there."""
    from soloblog.ui.post import support_links
    s = settings.get_all()
    notes = [
        ("Support links need a link first.", "Add a support link", "Support", "Add a support link")
        if not support_links(s) else None,
        ("About the author needs your name or bio.", "Bio", "", "Add them in Settings")
        if not (s.get("author_name") or s.get("author_bio")) else None,
        ("Newsletter sign-up needs the newsletter set up.", "Readers subscribe with", "Newsletter", "Set it up")
        if not (newsletter.mode(s) or members.enabled(s)) else None,
        ("Likes are off for the whole site.", "Reader reactions", "Reading", "Change in Settings")
        if s.get("reactions_style") == "off" else None,
    ]
    notes = [SiteTurnsOff(text, name, panel, link) for text, name, panel, link in filter(None, notes)]
    return Div(*notes, cls="grid gap-1 mt-1") if notes else None


def word_goal(post_id):
    """A post's own word goal (Post settings > Details): a number, 0 for
    none even with a default, or None to follow the default (Settings >
    Editor). Kept in a setting by the post's id, not in its file: it's for
    the writer, not part of the post, and the id stays the same when the
    URL changes."""
    try:
        value = json.loads(settings.get("editor_goals") or "{}").get(str(post_id))
        return None if value is None else int(value)
    except (ValueError, TypeError, AttributeError):
        return None


def default_goal() -> int:
    """Every post's word goal unless it has its own (Settings > Editor), 0 for none."""
    value = settings.get("editor_goal_default") or ""
    return int(value) if value.isdigit() else 0


def set_word_goal(post_id, value):
    try:
        goals = json.loads(settings.get("editor_goals") or "{}")
        goals = goals if isinstance(goals, dict) else {}
    except ValueError:
        goals = {}
    value = str(value).strip()
    if not value:
        goals.pop(str(post_id), None)  # empty: the default
    else:
        try:
            goals[str(post_id)] = max(0, min(int(value), 1_000_000))  # 0: none, whatever the default
        except ValueError:
            return
    settings.set_many({"editor_goals": json.dumps(goals)})


def _placing(row, start):
    """Whether a post is pinned, and where - a new one as its template says."""
    # bool(...), not just the raw sqlite int (0/1) - `pinned and X`
    # below would otherwise return 0 (Python's `and` hands back the
    # actual falsy operand, not a real False) whenever this post isn't
    # pinned. FastHTML renders `selected`/`checked` for anything that
    # isn't the literal `False`, so a bare 0 still rendered the
    # attribute - every "Where this post appears" <option> ended up
    # marked selected at once, and the browser just shows the *last*
    # one in that situation, which is why an unpinned post kept
    # reappearing as "Promoted at top of the blog roll" on reload.
    # a Privacy policy or Terms starts as a footer page (post_templates.FOOTER_PAGES)
    pinned = bool(row["pinned"]) if row else bool(start and start.get("pin"))
    pin_location = row["pin_location"] if row else ((start and start.get("pin")) or "header")
    return pinned, pin_location


def PreviewLinkCard(preview_url):
    """A draft's preview link, to copy and share."""
    if not preview_url:
        return None
    return Div(
        Div(
            P("Share this link to preview the draft without logging in:", cls="text-xs text-base-content/60 mb-1"),
            Div(
                Input(value=preview_url, readonly=True, cls="input input-sm flex-1 min-w-0 font-mono join-item"),
                Button(COPY_SVG, Span("Copy", cls="ml-1"), type="button", cls="btn btn-sm join-item", **on("click", "copyPreviewLink", preview_url)),
                cls="join w-full"
            ),
            Span("Copied", id="preview-copied", cls="text-xs text-success hidden"),
            cls="card-body p-3"
        ),
        cls=f"card card-border bg-base-100 {FIELD_GAP}"
    )


def EditorHeading(row, start, pinned, pin_location):
    """Over the editor: which post this is, its state and what's set on it."""
    # "Post: …" or "Page: …" - which it is, kept up to date as it's put
    # in the menu or taken out (syncPills, EDITOR_INIT_JS)
    kind = "Page" if pinned and pin_location in ("header", "footer") else "Post"
    heading = (Span(f"{kind}:", data_post_kind=True, cls="font-normal text-base-content/60"), " ", row["title"]) \
        if row else ("New post",)

    # the page's heading; the buttons are in editor_bar, over the text.
    # the post's state beside its heading - kept up to date as Post
    # settings change, before it's saved (EDITOR_INIT_JS). data-now: the
    # site's own time now, to tell a schedule still to come
    state = posts.post_status(dict(row, pinned=0)) if row else "Draft"
    return Div(
        Div(H1(*heading, cls="text-lg sm:text-xl font-bold truncate min-w-0"),
            Span(state, id="post-state", data_now=tz.utc_to_local_input(utcnow().isoformat(timespec="seconds")),
                 cls=f"badge badge-sm badge-soft {STATE_LOOK[state]} whitespace-nowrap shrink-0"),
            EditorPills(pin_location if pinned else "", row["visibility"] if row else "public",
                        bool(row and row["password"]), None if row else start["name"] if start else "Blank"),
            cls="flex flex-wrap items-center gap-x-2 gap-y-1 mb-2 [&>h1]:max-w-full"),
        cls="mb-4"
    )


def EditorBar(own_slug):
    # One bar over the text: Write / Preview / Focus mode on its left
    # (EDITOR_INIT_JS puts them in #editor-views),
    # the save state as a dot and the post's actions on its right - on a
    # phone behind a ⋯, like a list row's. It sticks under the header as
    # the post scrolls, and the toolbar under it; in focus mode it's
    # under focus mode's own bar.
    return Div(
        Div(id="editor-views", cls="shrink-0"),
        # the status slot (showStatus, app.py; a save's answer) - read out
        # as a dot, its words the dot's tooltip (input.css)
        Div(Span(data_save_dot=True, role="img", cls="status status-md"),
            Span(Span(id="save-status", data_status_slot=True, role="status", cls="text-xs text-base-content/50"),
                 data_save_slot=True, cls="truncate min-w-0"),
            cls="editor-status tooltip tooltip-bottom flex items-center gap-2 min-w-0 ml-auto"),
        # the post's buttons beside Save, as icons - on a phone too; the ones
        # that don't fit fold into ⋯, which only shows then, Discard and View
        # first (fitEditorBar, EDITOR_INIT_JS)
        Div(
            Div(
                IconAction(X_SVG, "Discard", size="sm", tip="tooltip-bottom", menu_label="folded", data_fold_first=True,
                           **on("click", "discardForm", EL)),
                # "View", as the post lists have it: the post on your site -
                # the eye is Preview's, the tab beside it
                IconAction(VIEW_SVG, "View", size="sm", tip="tooltip-bottom", menu_label="folded", data_fold_first=True,
                           href=f"/post/{own_slug}") if own_slug else None,
                IconAction(GEAR_SVG, "Settings", size="sm", tip="tooltip-bottom", menu_label="folded",
                           **on("click", "togglePostSettings", "button")),
                # the editor's icon at the size of the ui icons beside it, not the toolbar's
                IconAction(NotStr(editor_icons.svg("circle-help").replace('class="editor-icon"', 'class="h-4 w-4"')),
                           "Help", size="sm", tip="tooltip-bottom", menu_label="folded",
                           **on("click", "toggleEditorHelp")),
                # a phone: square buttons, so all four fit beside Save
                data_actions_row=True, cls="join max-sm:[&>.btn]:px-2"),
            Button(DOTS_SVG, type="button", popovertarget="editor-actions", aria_label="More", hidden=True,
                   data_actions_more=True, cls="btn btn-ghost btn-sm btn-square"),
            Div(id="editor-actions", popover="auto", data_row_menu=True,
                cls="join join-vertical m-0 inset-auto p-1 w-max whitespace-nowrap bg-base-100 text-base-content rounded-box "
                    "border border-base-300 shadow-lg [&:not(:popover-open)]:hidden max-sm:[&_.btn>svg]:size-4"),
            cls="shrink-0 flex items-center gap-1"),
        Button(CHECK_SVG, Span("Save", cls="ml-1"), type="submit", cls="btn btn-primary btn-sm shrink-0"),
        id="editor-bar", cls="editor-bar flex items-center gap-2 mb-1 in-data-[focus-one-bar]:hidden"
    )


def PublishingPanel(row, pinned, pin_location):
    """Post settings > Publishing: whether it's out, when, where and for whom."""
    published = row["published"] if row else False
    scheduled_at = row["scheduled_at"] if row else ""
    parent_slug = row["parent_slug"] if row else ""
    comments_enabled = bool(row["comments_enabled"]) if row else True
    # Settings > Comments and messages: with comments off for the whole site, nothing here is changed
    site_comments = settings.get("comments_enabled") == "1"
    own_slug = row["slug"] if row else None

    # The menu nests one level (posts._tree), so only top-level pages
    # are offered as a parent - a page under a page under a page would
    # never show. Only the header menu nests; the footer is a flat row of
    # links (PinnedLinksRow), so its pages get no parent picker.
    all_pinned = posts.list_pinned()
    has_own_children = any(p["parent_slug"] == own_slug for p in all_pinned if own_slug)

    def parent_options(location):
        opts = [Option("None (top-level page)", value="", selected=(parent_slug == ""))]
        for p in all_pinned:
            if p["slug"] == own_slug or p["parent_slug"] or p["pin_location"] != location:
                continue
            opts.append(Option(p["title"], value=p["slug"], selected=(p["slug"] == parent_slug)))
        return opts

    is_header_pin = pinned and pin_location == "header"
    nestable = pinned and pin_location in posts.NESTING


    return SettingsPanel(
        "Publishing",
        ToggleField("Published", "published", checked=bool(published),
                    help="Off, it's a draft only you see.", cls=FIELD_GAP),
        FormField(
            "Publish at",
            Input(name="scheduled_at", type="datetime-local", value=tz.utc_to_local_input(scheduled_at),
                  cls="input input-sm w-full", **on("change", "scheduleChanged", EL)),
            help=f"It goes live then ({settings.get('timezone') or 'UTC'} time).", cls=FIELD_GAP
        ),
        # one control for one decision: "not pinned" is just another
        # option here instead of a separate checkbox that has to
        # agree with this select - no more two clicks (check the
        # box, then also pick a location) to express one choice
        FormField(
            "Where it appears",
            Select(
                Option("In the blog roll", value="", selected=not pinned),
                Option("In the menu", value="header", selected=is_header_pin),
                Option("In the footer", value="footer", selected=(pinned and pin_location == "footer")),
                Option("Pinned to the top of the blog roll", value="top",
                       selected=(pinned and pin_location == "top")),
                name="pin_location", id="pin_location", cls="select select-sm w-full",
                **on("change", "updateParentField", VALUE)
            ),
            cls=FIELD_GAP
        ),
        Div(
            FormField(
                "Parent page",
                P("It has sub-pages of its own, so it can't go under another page.",
                  cls="text-xs text-base-content/60") if has_own_children else
                Div(*[Select(*parent_options(where), name="parent_slug", id=f"parent-slug-{where}",
                             disabled=not (pinned and pin_location == where),
                             cls=f"select select-sm w-full {'' if pin_location == where else 'hidden'}")
                      for where in posts.NESTING]),
                help=None if has_own_children else "To show it under another page in the menu."
            ),
            id="parent-page-field", cls=FIELD_GAP + ("" if nestable else " hidden")
        ),
        ToggleField("Unlisted", "unlisted", checked=bool(row and row["unlisted"]),
                    help="Only people with the link find it.",
                    cls=FIELD_GAP),
        # unlisted but in the menu or footer: everyone sees it
        # there, so say what Unlisted still does (syncUnlisted,
        # EDITOR_INIT_JS)
        P(UNLISTED_NOTE.format(place="footer" if pin_location == "footer" else "menu"),
          id="unlisted-note", hidden=not (row and row["unlisted"] and pinned
                                           and pin_location in ("header", "footer")),
          cls=f"text-xs text-base-content/60 -mt-2 {FIELD_GAP}"),
        ToggleField("Allow comments on this post", "comments_enabled", checked=bool(comments_enabled),
                    cls="" if not site_comments else FIELD_GAP, site="1" if site_comments else None,
                    custom=(site_comments and not comments_enabled) if site_comments else None),
        None if site_comments else Div(SiteTurnsOff("Comments are off for the whole site.", "Allow comments",
                                                    "Comments"), cls=f"-mt-1 {FIELD_GAP}"),
        NewsletterChoice(row),
        # the members area (members.py) - only while it's on
        FormField("Who can read it", Select(
            *[Option(label, value=key, selected=((row["visibility"] if row else "public") == key))
              for key, label in (("public", "Everyone"), ("members", "Members"),
                                 ("paid", "Paid members"))],
            name="visibility", cls="select select-sm w-full"),
            help="Others see the start, and are asked to join.", cls=FIELD_GAP)
        if settings.get("members_enabled") == "1" else None,
        FormField("Password", Input(name="post_password", value=row["password"] if row else "",
                                    autocomplete="off", placeholder="None - anyone can read it",
                                    cls="input input-sm w-full"),
                  help="Readers need it to open the post. Don't use a password you use anywhere else."),
        key="publishing",
        custom=int(site_comments and not comments_enabled) + int(held_from_subscribers(row))
    )


def DetailsPanel(row, start):
    """Post settings > Details: its address, cover, summary, tags and word goal."""
    own_slug = row["slug"] if row else None
    tags = row["tags"] if row else (start["tags"] if start else "")
    summary = row["summary"] if row else (start["summary"] if start else "")
    cover_image = row["cover_image"] if row else (start["cover"] if start else "")
    # the blog roll shows covers: hiding one post's is set differently from the site
    lists_covers = "cover" in (settings.get("roll_shows") or "").split(",")
    hides_cover = bool(row and row["hide_list_cover"])
    # the blog roll shows no covers at all: hiding this one changes nothing yet
    progress = settings.get("editor_progress") == "1"
    goal = word_goal(row["id"]) if row else None
    usual = default_goal()
    # a goal of its own, not the usual one (changed)
    own_goal = goal is not None and goal != (usual or 0)
    return SettingsPanel(
        "Details",
        # only once a post exists - a new post's URL comes from
        # its title on the first save
        FormField(
            "URL",
            Div(
                # where it really lives: a page at /about, a post at /post/...
                Span(posts.url_for(row)[:-len(own_slug)],
                     cls="join-item flex items-center px-2 text-xs text-base-content/60 "
                         "bg-base-200 border border-base-300 rounded-l-field"),
                Input(name="new_slug", value=own_slug, pattern="[a-z0-9]+(-[a-z0-9]+)*",
                      title="Lowercase letters, numbers and dashes",
                      cls="input input-sm flex-1 min-w-0 join-item font-mono"),
                cls="join w-full"
            ),
            help=(f"/{own_slug} is taken, so this page is at /post/{own_slug}."
                  if posts.is_page(row) and own_slug in posts.RESERVED_PATHS else None),
            cls=FIELD_GAP
        ) if own_slug else None,
        FormField(
            "Cover image",
            Div(
                Input(name="cover_image", id="cover_image", value=cover_image,
                      placeholder="/uploads/your-image.webp", cls="input input-sm flex-1 min-w-0 join-item"),
                MediaPickerButton("cover_image"),
                cls="join w-full"
            ),
            cls=FIELD_GAP
        ),
        ToggleField("Hide the cover in post lists", "hide_list_cover", checked=hides_cover,
                    help="It still shows on the post.", cls=FIELD_GAP if lists_covers else "",
                    site="0" if lists_covers else None,
                    custom=hides_cover if lists_covers else None),
        None if lists_covers else Div(SiteTurnsOff("Post lists don't show covers.", "Each post in the list shows",
                                                   "Blog layout"), cls=f"-mt-1 {FIELD_GAP}"),
        # room to read a summary back whole; it's still one line (save)
        FormField("Summary", Textarea(summary, name="summary", rows=3,
                                      cls="textarea textarea-sm w-full field-sizing-content min-h-20"),
                  help="A line about the post, in lists and search results.", cls=FIELD_GAP),
        FormField(
            "Tags",
            Input(name="tags", value=tags, id="tags-input", placeholder="travel, cooking",
                  cls="input input-sm w-full"),
            # real daisyUI badges, not a native <input list=""> - that
            # renders its own browser-chrome combobox arrow with no
            # theme styling at all, which is exactly the kind of
            # non-daisyUI element to avoid. clicking a badge just
            # appends it to the text field via addTag() (PIN_LOCATION_JS)
            # all_tags is fetched once, in the condition - this used to query twice
            # your 30 most used - all of them got long
            # 24px at least for a mouse too (WCAG 2.2's minimum), more for a finger
            Div(*[Button(t, type="button", cls="badge badge-soft badge-xs cursor-pointer min-h-6 "
                                               "hover:badge-secondary transition-colors "
                                               "[@media(pointer:coarse)]:min-h-7 "
                                               "[@media(pointer:coarse)]:px-2.5",
                         **on("click", "addTag", t)) for t in all_tags],
                cls="flex flex-wrap gap-1 mt-1.5") if (all_tags := posts.top_tags(30)) else None,
            help="Separate them with commas, or click one to add it."
        ),
        FormField(
            "Word goal",
            Input(name="word_goal", type="number", min="0", step="50",
                  value="" if goal is None else goal, data_default=usual or None,
                  data_site_value=str(usual or 0),
                  placeholder=f"{usual:,}" if usual else "None", inputmode="numeric",
                  cls="input input-sm w-full"),
            help=f"Only you see it. Empty: your default, {usual:,} words. 0: no goal." if usual else
                 "Only you see it.",
            cls="mt-3", custom=bool(own_goal)
        ) if progress else None,
        key="details",
        custom=int(hides_cover and lists_covers) + int(own_goal and bool(progress))
    )


def TemplatePanel(title):
    """Post settings > Template: apply one, or keep this post as one."""
    return SettingsPanel(
        "Template",
        Div(Button(TEMPLATE_SVG, Span("Apply a template", cls="ml-1"), type="button",
                   data_open_dialog="template-dialog", cls="btn btn-sm"), cls=FIELD_GAP),
        FormField("Save as a template",
                  # the post's title, as text you can change - and it follows
                  # the title until you do (data-follows, ACTIONS_JS)
                  Div(Input(name="template_name", value=title, placeholder="Its name", autocomplete="off",
                            aria_label="Template name", data_follows="title",
                            cls="input input-sm join-item flex-1 min-w-0"),
                      Button("Save", type="button", cls="btn btn-sm join-item", data_needs="template_name",
                             hx_post="/admin/templates/save", hx_include="closest form",
                             hx_target="#template-status", hx_swap="outerHTML"),
                      cls="join w-full"),
                  help="Keeps the words and the Page settings, to start a post from or apply to another."),
        Span(id="template-status", role="status", cls="text-xs"),
        key="template", open_=False
    )


def SearchEnginesPanel(row):
    """Post settings > Search engines: how this post looks to them, or that it doesn't."""
    # the site is listed by search engines: hiding this one is changed
    site_listed = settings.get("search_noindex") != "1"
    hidden_post = bool(row and row["noindex"])
    return SettingsPanel(
        "Search engines",
        ToggleField("Hide this post from search engines", "post_noindex", checked=hidden_post,
                    help="It stays on your site.", cls=FIELD_GAP,
                    site="0" if site_listed else None,
                    custom=hidden_post if site_listed else None),
        FormField("Title for search engines", Input(name="seo_title", maxlength="120",
                                                    value=row["seo_title"] if row else "",
                                                    placeholder="The post's own title",
                                                    cls="input input-sm w-full"),
                  help="About 60 characters shows in full. Empty: the post's own title.", cls=FIELD_GAP),
        FormField("Share image", Div(
            Input(name="share_image", id="share_image", value=row["share_image"] if row else "",
                  placeholder="The cover image", cls="input input-sm flex-1 min-w-0 join-item"),
            MediaPickerButton("share_image"), cls="join w-full"),
                  help="When it's shared, instead of the cover. About 1200 × 630.", cls=FIELD_GAP),
        FormField("Original URL", Input(name="canonical_url", type="url",
                                        value=row["canonical_url"] if row else "",
                                        placeholder="https://medium.com/@you/the-first-copy",
                                        cls="input input-sm w-full"),
                  help="Only if it was published somewhere else first."),
        open_=bool(row and (row["noindex"] or row["canonical_url"] or row["seo_title"]
                            or row["share_image"])), key="seo",
        custom=int(hidden_post and site_listed)
    )


def SeriesPanel(row):
    """Post settings > Series: the series this post is a part of."""
    series_name = row["series_name"] if row else ""
    series_order = row["series_order"] if row else 0
    return SettingsPanel(
        "Series",
        Div(
            FormField("Name",
                      Input(name="series_name", value=series_name, placeholder="e.g. Learning Rust",
                            cls="input input-sm w-full")),
            FormField("Order",
                      Input(name="series_order", type="number", value=series_order or "",
                            cls="input input-sm w-full")),
            cls="grid grid-cols-2 gap-3"
        ),
        open_=bool(series_name), key="series"
    )


def PostForm(action, row=None, body_md="", preview_url=None, prefill_title="", start=None, start_key=""):
    # prefill_title - a wiki page's "not written yet" link starts one with its title
    # start - (name, tags, body...) of the template a new post starts from
    title = row["title"] if row else prefill_title
    progress = settings.get("editor_progress") == "1"
    if start and not row:
        body_md = start["body"]
    pinned, pin_location = _placing(row, start)
    own_slug = row["slug"] if row else None

    # the bar sticks just under the admin's top bar - its measured height
    # (--header-h, syncChromeOffsets in app.py)
    editor_sticky = "var(--header-h, 3rem)"
    drawer_fill = glass_fill(settings)

    return Form(
        EditorHeading(row, start, pinned, pin_location),
        # the text keeps the site's column width at every size, and Post
        # settings slides over it - docked beside, it squeezed the text or
        # widened the page
        Div(
            # the title is typed into a heading at the top of the writing
            # (EDITOR_INIT_JS) - this is what's saved
            Input(type="hidden", name="title", value=title),
            EditorBar(own_slug),
            Textarea(body_md, name="body", id="body-editor"),
            Div(id="post-settings-backdrop", cls=DRAWER_BACKDROP,
                **on("click", "togglePostSettings", False)),
            Aside(
              Div(
                Div(
                    H2("Post settings", cls="font-semibold"),
                    Button(X_SVG, type="button", cls="btn btn-sm btn-ghost btn-square",
                           aria_label="Close settings", **on("click", "togglePostSettings", False)),
                    cls="flex items-center justify-between"
                ),
                PreviewLinkCard(preview_url),
                PublishingPanel(row, pinned, pin_location),
                DetailsPanel(row, start),
                PagePanel(row, start, pinned and pin_location in ("header", "footer")),
                TemplatePanel(title),
                SearchEnginesPanel(row),
                SeriesPanel(row),
                RevisionsPanel(own_slug) if own_slug else None,
                # what scrolls is inside the card, so its scrollbar can't
                # square off the card's rounded corners
                id="post-settings", data_scroll_hint=True,
                # [&>*]:shrink-0: a section folding (its height animated)
                # was squeezed to nothing for a moment by this column
                cls=f"flex flex-col gap-3 flex-1 min-h-0 overflow-y-auto p-3 [&>*]:shrink-0 {SCROLLS}"
              ),
              # what's changed here is saved with the post - so it says so,
              # with Save, at the panel's foot while there's something to save
              # (updateStatus, EDITOR_INIT_JS) - only while the panel covers
              # the editor: beside it, the editor's own Save is in view. No
              # Discard: it threw away the text too, from a settings panel
              Div(Span("Unsaved changes", cls="text-xs text-warning"),
                  # not primary: the editor's own Save is the one on the page
                  Button(CHECK_SVG, Span("Save", cls="ml-1"), type="submit", cls="btn btn-sm"),
                  cls="hidden [form[data-unsaved]_#post-settings-panel:not([data-docked])_&]:flex items-center "
                      "justify-between gap-2 shrink-0 px-3 py-2 border-t-[length:var(--border)] border-base-300"),
              # a slide-over: closed it's off-screen (translate-x-full), open
              # it's over the page with a backdrop - or, where there's room, a
              # card beside the editor (placePostSettings, PIN_LOCATION_JS)
              id="post-settings-panel", aria_label="Post settings", inert=True, data_own_scroll=True,
              cls=f"fixed inset-y-0 right-0 z-40 {DRAWER_W} translate-x-full flex flex-col overflow-hidden {drawer_fill} "
                  f"shadow-xl transition-transform duration-200 {DOCKED_FILL}"
            ),
            cls="relative"
        ),
        hx_post=action, hx_target="#save-status", hx_swap="outerHTML show:none focus-scroll:false", id="post-form",
        # Settings > Editor > Writing width, Markdown marks, Toolbar (input.css)
        data_editor_width=settings.get("editor_width"), data_editor_marks=settings.get("editor_marks"),
        data_typewriter=settings.get("editor_typewriter") == "1" or None, data_fade=settings.get("editor_fade") if settings.get("editor_fade") in ("paragraph", "sentence") else None,
        # Focus mode: the bars go quiet while you type, not only the toolbar
        cls="group/pf",
        data_focus_quiet=settings.get("editor_focus_toolbar") != "none" or None,
        # the caret in the palette's colour
        data_caret=True,
        # words written today and the goal (updateStatus) - Settings > Editor > Writing progress
        data_day_words=str(posts.words_at_day_start(row["slug"]) if row else 0) if progress else None,
        data_editor_toolbar=editor_config.toolbar_style(settings.get("editor_toolbar_rows")),
        data_draft_key=f"post-{row['id']}" if row else "new",
        # the post's own title isn't suggested after [[ (slash_menu.js)
        data_own_slug=row["slug"] if row else None,
        # the formatting toolbar (input.css) stays sticky while scrolling
        # a long post - unlike the action bar above, that's a real,
        # requested feature, not a bug. It only needs to clear the site's
        # own fixed/floating header, if there is one - the action bar it
        # used to also have to clear is gone now that that bar scrolls
        # normally.
        style=f"--editor-sticky: {editor_sticky}"
    )


@ar.get("/admin/new")
def new_post(session, title: str = "", template: str = None):
    # no template in the address: the one Settings > Editor > New posts
    # start from names. An empty one (the Blank card) means Blank
    template = post_templates.start_key() if template is None else template
    start = post_templates.get(template) if template else None
    if start:
        post_templates.used(template)
    return Layout(
        *EDITOR_ASSETS,
        PostForm("/admin/save", prefill_title=title[:200], start=start, start_key=template if start else ""),
        *PreviewScripts(settings.get_all()),
        MediaPickerDialog(settings.get_all()),
        LinkPickerDialog(),
        # out here, not in the settings drawer - its slide breaks a dialog's layout
        TemplateDialog(template if start else ""),
        *EditorHelpPanel(), InsertSearch(), TemplateDialog(), *EditorScripts(),
        settings=settings.get_all(), logged_in=True, pinned_tree=posts.list_pinned_tree(), admin_page=True
    )


# what a ticked box sends; anything else is a box left empty
TICKED = ("1", "on", "true", "yes")


@dataclass
class SentPost(posts.PostFields):
    """What the editor's form sends: a post's fields under their own names
    (posts.PostFields - a new setting needs no line here), and the few the
    form sends another way. None is a field the form didn't have (members
    are off, an older page still open): the post keeps what it had."""
    comments_enabled: bool = False  # a tick box: not sent is off
    visibility: str = None
    section_space: str = None
    section_motion: str = None
    sound: str = None
    title_style: str = None
    page_width: str = None
    # named apart from a login's own fields, which a browser would fill in
    post_password: str = ""
    post_noindex: bool = False
    # Show: what's ticked, and what the post had when the form was made
    extras: list[str] = None
    extras_before: str = None
    extras_before_page: str = ""
    sides_tags: str = None
    sides_archive: str = None
    sides_author: str = None

    def __post_init__(self):
        for f in fields(self):
            if f.type in (bool, "bool"):
                value = getattr(self, f.name)
                setattr(self, f.name, value is True or str(value).strip().lower() in TICKED)

    def changes(self) -> dict:
        """The fields as posts.write takes them."""
        sides = (("tags", self.sides_tags), ("archive", self.sides_archive), ("author", self.sides_author))
        return {
            **{name: getattr(self, name) for name in posts.WRITABLE},
            "summary": " ".join((self.summary or "").split()),
            "scheduled_at": tz.local_input_to_utc(self.scheduled_at),  # typed in the site's timezone
            "password": self.post_password, "noindex": self.post_noindex,
            "sides": None if all(v is None for _, v in sides) else ",".join(
                # one place each: a comma inside one would name another panel's
                f"{n}={v}" for n, v in sides if v in dict(OWN_SIDE_PLACES)),
            "extras": extras_choice(self.extras, self.extras_before, self.extras_before_page, self.pin_location),
        }


# FastHTML fills a form's object from the class's own annotations only -
# without the inherited ones every post field would arrive empty. A tick
# box is read as text (__post_init__): as a bool, anything but yes or no
# in one was a server error
SentPost.__annotations__ = {f.name: str if f.type in (bool, "bool") else f.type for f in fields(SentPost)}


@ar.post("/admin/templates/save")
def save_template(session, request, form: SentPost, template_name: str = ""):
    name = template_name.strip() or form.title.strip()
    if not name or not form.body.strip():
        return Span("Give it a name and some text first", id="template-status", role="status", cls="text-xs text-error")
    # every Post setting a template has, read as the post's own save reads them;
    # the rest of the form (its publishing, its address) is never a template's
    sent = form.changes()
    post_templates.save(name, form.tags, form.body, form.summary, form.cover_image,
                        {key: sent[key] or "" for key in post_templates.NO_SETTINGS})
    return Span(f"Saved “{' '.join(name.split())[:80]}” - it's under Templates when you start a new post",
                id="template-status", role="status", cls="text-xs text-success")


@ar.post("/admin/templates/delete/{template_id}")
def delete_template(session, request, template_id: str):
    post_templates.delete(template_id)
    return TemplatesList()


def TemplatesList():
    """Settings > Editor > Custom templates: the ones you've saved, each with Remove."""
    mine = post_templates.saved()
    if not mine:
        return Div(P("None yet. Save one from a post's settings: Template > Save as a template.",
                     cls="text-sm text-base-content/60"), id="templates-list")
    return Div(Ul(*[Li(Div(Span(t["name"], cls="text-sm font-medium"),
                           Span(", ".join(section_names(t["body"])), cls="text-xs text-base-content/50"),
                           cls="list-col-grow flex flex-col"),
                       RowActions(IconAction(EDIT_SVG, "New post from it",
                                             href=f"/admin/new?template=mine-{t['id']}"),
                                  IconAction(TRASH_SVG, "Remove", danger=True, type="button",
                                             hx_post=f"/admin/templates/delete/{t['id']}", hx_target="#templates-list",
                                             hx_swap="outerHTML",
                                             hx_confirm=f"Remove the template “{t['name']}”? Posts made from it stay."),
                                  id=f"template-acts-{t['id']}"),
                       cls="list-row items-center") for t in mine], cls="list"), id="templates-list")


@ar.get("/admin/revisions/{revision_id}/diff")
def revision_diff(session, revision_id: int):
    """What that version changed from the one it replaced."""
    rev = posts.get_revision(revision_id)
    if not rev or not posts.get_post(rev["slug"]):
        return P("That version is gone.", cls="text-sm text-error")
    listed = {r["id"]: r for r in posts.list_revisions(rev["slug"])}
    mine = listed.get(rev["id"])
    when = _when(mine["written_at"]) if mine and mine["written_at"] else f"before {_when(rev['saved_at'])}"
    return RevisionChanges(when, posts.revision_before(rev), rev,
                           first=len(listed) < posts.MAX_REVISIONS)


@ar.get("/admin/history/{slug}/now")
def history_now_diff(session, slug: str):
    """What the post as it's saved now changed from the version before."""
    now = posts.current_version(slug)
    if not now:
        return P("That post is gone.", cls="text-sm text-error")
    newest = posts.list_revisions(slug)
    before = posts.get_revision(newest[0]["id"]) if newest else None
    return RevisionChanges(_when(now["written_at"]), before, now, first=True)


@ar.get("/admin/revisions/{revision_id}")
def revision_json(session, revision_id: int):
    rev = posts.get_revision(revision_id)
    if not rev:
        return JSONResponse({"error": "not found"}, status_code=404)
    return JSONResponse({"title": rev["title"], "body": rev["body"]})


@ar.get("/admin/edit/{slug}")
def edit_post(session, slug: str):
    row = posts.get_post(slug)
    if not row:
        return RedirectResponse("/admin/posts", status_code=303)
    body_md = posts.load_post_body(slug)
    preview_url = None
    if not posts.is_live(row):
        token = posts.ensure_preview_token(slug)
        preview_url = f"{config.BASE_URL}/post/{slug}?preview={token}"
    return Layout(
        *EDITOR_ASSETS,
        PostForm(f"/admin/save?slug={slug}", row=row, body_md=body_md, preview_url=preview_url),
        *PreviewScripts(settings.get_all()),
        MediaPickerDialog(settings.get_all()),
        LinkPickerDialog(),
        *EditorHelpPanel(), InsertSearch(), TemplateDialog(), *EditorScripts(),
        settings=settings.get_all(), logged_in=True, pinned_tree=posts.list_pinned_tree(), admin_page=True
    )


# the tabs are a post's state, and only that; what kind it is is a filter
# (KIND_OPTIONS), and the other pages about posts are the head's links
STATUS_TABS = [("all", "All"), ("published", "Published"), ("scheduled", "Scheduled"), ("draft", "Drafts"),
               ("trash", "Trash")]
POSTS_VIEWS = [("pinned", "Pinned"), ("tags", "Tags"), ("calendar", "Calendar")]
KIND_OPTIONS = [("", "All"), ("posts", "Posts"), ("pages", "Pages"), ("series", "In a series")]
SORT_OPTIONS = [("newest", "Newest"), ("oldest", "Oldest"), ("title", "Title A-Z"), ("views", "Most viewed"),
                ("edited", "Last edited")]
# no "Most viewed" here - views/likes are runtime usage data that only
# ever lived in the DB row, which is gone the moment a post is trashed
# (see list_trash()'s own docstring in posts.py); "newest"/"oldest"
# here mean most/least recently trashed, not written/published
TRASH_SORT_OPTIONS = [("newest", "Recently deleted"), ("oldest", "Oldest deleted"), ("title", "Title A-Z")]
POSTS_PER_PAGE = 10
ACCESS_OPTIONS = [("", "All"), ("public", "Everyone"), ("members", "Members"), ("paid", "Paid members")]


def _delete_form(p, return_to="/admin/posts"):
    # return_to: after a delete, back to the same tab, sort and filter.
    # cls="contents": the form takes no box of its own, so its button
    # lines up in the join with Edit's link
    return Form(
        Input(type="hidden", name="slug", value=p["slug"]),
        Input(type="hidden", name="return_to", value=return_to),
        IconAction(TRASH_SVG, "Trash", danger=True,
                   confirm=f"Move “{p['title']}” to trash? You can restore it from Trash."),
        action="/admin/delete", method="post", cls="contents"
    )


def _pin_action_item(label, slug, direction=None, parent_slug=None, li_cls="", site=False):
    """One row inside the pinned-page Move menu - a real POST, not a
    link, styled to sit flush in the menu (w-full text-left, no button
    chrome) so it reads as a menu item rather than a button floating
    inside one."""
    if site:
        hidden = [Input(type="hidden", name="site", value=slug), Input(type="hidden", name="where", value=site),
                  Input(type="hidden", name="direction", value=direction)]
        action = "/admin/nav/move"
    elif direction:
        hidden = [Input(type="hidden", name="slug", value=slug), Input(type="hidden", name="direction", value=direction)]
        action = "/admin/pin/move"
    else:
        hidden = [Input(type="hidden", name="slug", value=slug), Input(type="hidden", name="parent_slug", value=parent_slug or "")]
        action = "/admin/pin/parent"
    return Li(Form(*hidden, Button(label, type="submit", cls="w-full text-left cursor-pointer"), action=action, method="post"), cls=li_cls)


def _move_menu(p, is_first, is_last, prev_top_level, has_children_slugs):
    """One Move menu for every pinned row, header or not - three
    earlier attempts at this specific control (a parent-picker
    dropdown, a pair of indent/outdent arrows next to separate reorder
    arrows, then a menu that only header pins got while everyone else
    kept plain arrows) each turned out to be its own kind of
    inconsistent or confusing. Plain labeled text ("Nest under About")
    beats icon-guessing, one control beats two, and reusing the app's
    own real dropdown/menu widget (same one AdminMenu already uses)
    means this isn't a new pattern, just another instance of one
    already in use. Nesting-related items only ever show up for header
    pins - footer/top-of-roll pins don't nest (see PostForm's own note
    on that), so theirs is just Move up / Move down."""
    site = p["where"] if p["pin_location"] == "site" else None
    items = [
        _pin_action_item("Move up", p["slug"], direction="up", site=site) if not is_first else None,
        _pin_action_item("Move down", p["slug"], direction="down", site=site) if not is_last else None,
    ]
    items = [i for i in items if i]
    if p["pin_location"] in posts.NESTING:
        is_child = bool(p["parent_slug"])
        has_children = p["slug"] in has_children_slugs
        # border-t/mt-1/pt-1 - the same divider-before-the-odd-one-out
        # technique AdminMenu already uses ahead of its own "Log out"
        divider_cls = "border-t-[length:var(--border)] border-base-300 mt-1 pt-1"
        nest_item = None
        if is_child:
            nest_item = _pin_action_item("Make top-level", p["slug"], parent_slug="", li_cls=divider_cls)
        elif prev_top_level and not has_children:
            nest_item = _pin_action_item(f'Nest under "{prev_top_level["title"]}"', p["slug"],
                                          parent_slug=prev_top_level["slug"], li_cls=divider_cls)
        if nest_item:
            items.append(nest_item)
    if not items:
        return None
    # join-item on the button only: on the wrapper too it drew a second
    # border around it. The wrapper is flex so the button lines up with
    # the row exactly - in plain inline flow it sat half a pixel low.
    return Div(
        Label(MOVE_SVG, MenuLabel("Move"), tabindex="0", role="button", aria_label="Move", data_tip="Move",
              cls="btn btn-xs join-item tooltip"),
        Ul(*items, tabindex="0",
           cls=f"menu menu-sm dropdown-content w-max {glass_fill(settings.get_all())} rounded-box z-20 mt-2 p-2 shadow "
               "border-[length:var(--border)] border-base-200"),
        cls="dropdown flex"
    )


# each state's pill - the lists' and the editor's own (EDITOR_INIT_JS has
# the same, for the one it keeps up to date)
STATE_LOOK = {"Published": "badge-success", "Draft": "badge-warning", "Scheduled": "badge-info",
              "Unlisted": "badge-neutral"}


def PostPills(p):
    """What a post is, at a glance - the same pills on every list of posts:
    its state, post or page, pinned, who can read it, a password."""
    # its state alone - post_status() says Pinned before anything else
    state = posts.post_status(dict(p, pinned=0))
    look = STATE_LOOK[state]
    pill = lambda text, cls: Span(text, cls=f"badge badge-xs {cls} whitespace-nowrap")  # noqa: E731
    access = posts.clean_visibility(p["visibility"])
    return Div(
        pill(state, f"{look} badge-soft"),
        pill("Page" if posts.is_page(p) else "Post", "badge-outline"),
        pill("Pinned", "badge-outline") if p["pinned"] and not posts.is_page(p) else None,
        pill("Paid members", "badge-primary") if access == "paid" else
        pill("Members", "badge-primary badge-soft") if access == "members" else None,
        pill("Password", "badge-outline") if posts.is_protected(p) else None,
        cls="flex flex-wrap items-center gap-1 mt-1"
    )


def section_names(body):
    """The sections a post's text has, by their "Section:" lines, in order."""
    seen = {}
    for name in re.findall(r"(?mi)^Section:[ \t]*(\S[^\n]*?)[ \t]*$", body or ""):
        seen.setdefault(name.lower(), name)
    return list(seen.values())


def EditorPills(where, visibility, password, started_from):
    """Under the editor's heading and its state: the template a new post
    started from (None on a saved one; choosing opens the template picker),
    pinned and who can read it - the lists' pills (PostPills), kept up to
    date as Post settings change (syncPills, EDITOR_INIT_JS). Nothing to
    show: no row. The sections are in the toolbar's Go to menu."""
    pill = lambda text, cls="badge-outline", **kw: Span(text, cls=f"badge badge-sm {cls} whitespace-nowrap", **kw)  # noqa: E731
    access = posts.clean_visibility(visibility)
    pills = (
        # the pills' size, with a ▾ for what opens a picker - on a touch
        # screen its tap area reaches past its edges (touch-size, input.css)
        Span(Button(Span(f"Template: {started_from}", data_template_name=True),
                    CHEVRON_DOWN_SVG, type="button", data_open_dialog="template-start-dialog", data_tap_area=True,
                    aria_label="Choose another template",
                    cls="badge badge-sm badge-outline gap-1 whitespace-nowrap cursor-pointer hover:border-primary"),
             data_tip="Choose another template", cls="tooltip tooltip-bottom") if started_from is not None else None,
        pill("Pinned") if where == "top" else None,
        pill("Paid members", "badge-primary") if access == "paid" else
        pill("Members", "badge-primary badge-soft") if access == "members" else None,
        pill("Password") if password else None,
    )
    shown = [p for p in pills if p is not None]
    # a line of their own under the heading, on any screen
    return Div(*shown, id="post-pills", hidden=not shown, cls="basis-full flex flex-wrap items-center gap-x-2 gap-y-1")


def PostMeta(p, relative, extra=""):
    """Its dates - written or going live, and edited on a later day - and
    how it's doing."""
    if posts.post_status(p) == "Scheduled":
        when = f"Goes live {format_date(p['scheduled_at'], relative)}"
    else:
        when = f"{'Published' if p['published'] else 'Started'} {format_date(p['created_at'], relative)}"
    edited = p["updated_at"] and tz.local_date(p["updated_at"]) != tz.local_date(p["created_at"])
    return Div(" · ".join(x for x in (when, f"edited {format_date(p['updated_at'], relative)}" if edited else "",
                                      f"{p['views']} views", f"{p['likes']} likes", extra) if x),
               cls="text-xs text-base-content/60 mt-0.5")


def PinRow(p, indent, is_first, is_last, prev_top_level, has_children_slugs):
    """One row in the Pinned tab's grouped view - same title/status/
    tags layout as the regular posts list (manage_posts, below), so
    the two read as one consistent list style. Move joins the same
    button group as Edit/Delete, in front of them, rather than sitting
    as a separate control on the row's other side."""
    move_menu = _move_menu(p, is_first, is_last, prev_top_level, has_children_slugs)
    # daisyUI's .list-row is a CSS grid that only stretches whichever of
    # its OWN DIRECT children carries .list-col-grow to fill the row
    # (:has(.list-col-grow:nth-child(N)) picks the grid template - see
    # input.css's daisyUI layer) - matching manage_posts()'s own PostRow
    # shape exactly (Li's one direct child IS the list-col-grow/
    # justify-between element) keeps Edit/Delete pinned to the right.
    return Li(
        Div(
            Div(
                # the title edits, as in any admin list; the eye views it
                A(p["title"], href=f"/admin/edit/{p['slug']}", cls="link text-sm"),
                PostPills(p),
                PostMeta(p, settings.get("relative_dates") == "1"),
                TagList(p["tags"], small=True),
            ),
            RowActions(move_menu,
                       IconAction(EDIT_SVG, "Edit", href=f"/admin/edit/{p['slug']}"),
                       IconAction(VIEW_SVG, "View", href=posts.url_for(p)),
                       IconAction(FOCUS_SVG, "Edit in Focus", href=f"/admin/edit/{p['slug']}?focus=1"),
                       _delete_form(p, return_to="/admin/posts?status=pinned"), id=f"pin-acts-{p['slug']}"),
            cls="list-col-grow flex justify-between items-start gap-3"
        ),
        cls="list-row" + (" pl-10" if indent else "")
    )


def SiteRow(key, where, is_first, is_last):
    """One of the site's own pages (Home, Archive...) in the Pinned tab's
    header or footer group: moved and renamed like a page, never edited
    or trashed - nothing nests under it. Home can be left out of the
    header's menu, the others taken out of the one they were added to.
    One that doesn't apply right now says why, and isn't shown."""
    s = settings.get_all()
    menu = "menu" if where == "header" else "footer"
    default = SITE_ROW_WORDS[key]
    label = (s.get(posts.site_key(where, key, "label")) or "").strip()
    hidden = where == "header" and key == "home" and bool(s.get("nav_home_hidden"))
    note = posts.menu_note(s, key) if key in posts.site_addable(where) else ""
    ident = key if where == "header" else f"foot-{key}"
    # the same dropdown as Move: opens under the button, closes when you leave it
    rename = Div(
        Label(EDIT_SVG, MenuLabel("Rename…"), tabindex="0", role="button", aria_label="Rename", data_tip="Rename…",
              cls="btn btn-xs join-item tooltip"),
        # the form sits inside the dropdown's box: a `flex` on the box itself beats the
        # closed state's display:none
        Div(Form(Input(type="hidden", name="site", value=key), Input(type="hidden", name="where", value=where),
                 Input(name="label", value=label, placeholder=default, maxlength=SITE_LABEL_MAX,
                       aria_label=f"What the {menu} calls {default}", cls="input input-sm w-44"),
                 Button("Save", type="submit", cls="btn btn-sm"),
                 action="/admin/nav/rename", method="post", cls="flex gap-2"),
            tabindex="0",
            cls=f"dropdown-content top-full {glass_fill(s)} rounded-box z-20 mt-2 p-2 shadow "
                "border-[length:var(--border)] border-base-200"),
        cls="dropdown dropdown-end flex"
    )
    if where == "header" and key == "home":
        leave = Form(Input(type="hidden", name="hidden", value="" if hidden else "1"),
                     IconAction(EYE_SVG if hidden else EYE_OFF_SVG, "Show in menu" if hidden else "Hide from menu"),
                     action="/admin/nav/hide", method="post", cls="contents")
    elif key in posts.site_addable(where):
        leave = Form(Input(type="hidden", name="site", value=key), Input(type="hidden", name="where", value=where),
                     IconAction(X_SVG, f"Remove from {menu}"), action="/admin/nav/remove", method="post", cls="contents")
    else:
        leave = None
    return Li(
        Div(
            Div(
                Span(label or default, cls="text-sm"),
                Div(Span("Site page", cls="text-xs text-base-content/60"),
                    Span("Hidden", cls="badge badge-sm badge-outline whitespace-nowrap") if hidden else None,
                    Span(note, cls="badge badge-sm badge-outline whitespace-nowrap") if note else None,
                    cls="flex flex-wrap items-center gap-2 mt-1"),
                cls="opacity-60" if hidden or note else ""
            ),
            RowActions(_move_menu({"slug": key, "pin_location": "site", "where": where}, is_first, is_last, None, set()),
                       rename, leave, id=f"pin-acts-site-{ident}"),
            cls="list-col-grow flex justify-between items-start gap-3"
        ),
        cls="list-row", id=f"site-row-{ident}"
    )


def AddToMenu(where):
    """The header's or the footer's Add button: the built-in pages that
    aren't in it yet and apply to the site now, each with what it is.
    Nothing to add, no button."""
    s = settings.get_all()
    menu = "menu" if where == "header" else "footer"
    offers = [k for k in posts.site_addable(where) if s.get(posts.site_key(where, k, "on")) != "1"
              and not posts.menu_note(s, k)]
    if not offers:
        return None
    return Div(
        Label(Span(f"Add to {menu}"), CHEVRON_DOWN_SVG, tabindex="0", role="button", cls="btn btn-sm gap-1"),
        Ul(*[Li(Form(Input(type="hidden", name="site", value=k), Input(type="hidden", name="where", value=where),
                     Button(Span(SITE_ROW_WORDS[k], cls="block"),
                            Span(posts.SITE_PAGES[k][2], cls="block text-xs text-base-content/60"),
                            type="submit", cls="w-full text-left cursor-pointer"),
                     action="/admin/nav/add", method="post")) for k in offers],
           tabindex="0",
           cls=f"menu menu-sm dropdown-content w-max {glass_fill(s)} rounded-box z-20 mt-2 p-2 shadow "
               "border-[length:var(--border)] border-base-200"),
        cls="dropdown dropdown-end"
    )


def PinnedGroup(label, tree, where=None):
    """where: "header" or "footer", whose group has the site's own pages
    as rows among the pages (posts.menu_items) and an Add button."""
    if not tree and not where:
        return None
    # has_children comes from the full header tree, not just this
    # group's own - a page's children only ever show up in ITS OWN
    # tree entry, and this fires for the footer/top-of-roll groups too
    # (where it's simply unused - _reparent_col already gates on
    # pin_location before ever consulting it)
    has_children_slugs = {page["slug"] for page, children in posts.list_pinned_tree(drafts=True) +
                          posts.list_pinned_tree_footer(drafts=True) if children}
    s = settings.get_all()
    items = posts.menu_items(s, tree, where, True) if where else tree
    rows = []
    for i, item in enumerate(items):
        first, last = i == 0, i == len(items) - 1
        if isinstance(item, str):
            rows.append(SiteRow(item, where, first, last))
            continue
        page, children = item
        # a page nests under the page before it, never under a site page
        before = items[i - 1] if i > 0 else None
        prev_top_level = before[0] if before and not isinstance(before, str) else None
        rows.append(PinRow(page, indent=False, is_first=first, is_last=last,
                            prev_top_level=prev_top_level, has_children_slugs=has_children_slugs))
        for j, c in enumerate(children):
            rows.append(PinRow(c, indent=True, is_first=(j == 0), is_last=(j == len(children) - 1),
                                prev_top_level=None, has_children_slugs=has_children_slugs))
    off = ""
    if where == "footer":
        off = "Not shown: the footer is off" if s.get("footer_enabled") != "1" else \
            "Not shown: pinned pages are off in the footer" if s.get("footer_show_pages") != "1" else ""

    # text-base font-semibold mb-3, matching Settings' own H2 section
    # headings exactly (routes/admin_settings) - mt-6 between groups
    # is this page's own addition, Settings doesn't need it since
    # SECTION_GAP on the previous field already provides that gap
    return Div(Div(H2(label, cls="text-base font-semibold"), AddToMenu(where) if where else None,
                   cls="flex items-center justify-between gap-3 mb-3 mt-6"),
               P(off, cls="text-xs text-base-content/60 -mt-2 mb-3") if off else None,
               Ul(*rows, cls="list"))


def TrashRow(t):
    return Li(
        RowCheck("trash-bulk", "slugs", t["slug"], t["title"], "mt-0.5"),
        Div(
            Div(t["title"], cls="text-sm"),
            Div(f"Deleted {format_date(t['trashed_at'])}", cls="text-xs text-base-content/50"),
            TagList(t["tags"], small=True),
            cls="list-col-grow"
        ),
        # same Restore + Delete forever pairing, icon, label, and
        # confirm as Comments' own trash tab (comments_routes.py) -
        # cls="contents" on each form (not join-item on the form
        # itself) so the actual buttons are .join's real flex
        # children - see the eighty-sixth follow-up's alignment fix,
        # same reasoning applies here
        RowActions(
            Form(Input(type="hidden", name="slug", value=t["slug"]),
                 IconAction(RESTORE_SVG, "Restore"),
                 action="/admin/posts/restore", method="post", cls="contents"),
            Form(Input(type="hidden", name="slug", value=t["slug"]),
                 IconAction(TRASH_SVG, "Delete forever", danger=True,
                            confirm="Permanently delete this post? This can't be undone."),
                 action="/admin/posts/delete-forever", method="post", cls="contents"),
            id=f"trash-acts-{t['slug']}"
        ),
        cls=f"list-row {TICK_ROW_CLS}", **TICK_ROW
    )


def _no_posts(status, q, filtered):
    """What an empty Posts and pages list says: what's missing, and for a
    list with nothing in it at all, the way to write one."""
    if q:
        return EmptyState(f"Nothing matches “{q}”.", "🗂️")
    if filtered:
        return EmptyState("Nothing matches this filter.", "🗂️")
    said = {"published": "Nothing published yet.", "scheduled": "Nothing scheduled.", "draft": "No drafts."}
    return EmptyState(said.get(status, "No posts yet."), "🗂️",
                      actions=[A(PLUS_SVG, Span("New post", cls="ml-1"), href="/admin/new", cls="btn btn-sm")]
                      if status in ("all", "published") else None)


def PostsActions(view=""):
    """The head of Posts and pages: its other pages (the order of what's
    pinned, the tags, the calendar) and New post."""
    views = RowActions(*[A(label, href=f"/admin/posts?status={key}", aria_current="page" if key == view else None,
                           cls=f"btn btn-sm join-item{' btn-active' if key == view else ''}")
                         for key, label in POSTS_VIEWS], id="posts-views")
    # a wide screen has New post at the top of the admin's rail
    return Div(views, A(PLUS_SVG, Span("New post", cls="ml-1"), href="/admin/new", cls="btn btn-primary btn-sm lg:hidden"),
               cls="flex items-center gap-2")


def _posts_tabs(status, query=""):
    return Tabs(*[A(label, href=f"/admin/posts?status={key}{query}", aria_current="page" if key == status else None,
                    cls=f"tab tab-sm whitespace-nowrap shrink-0 {'tab-active font-semibold' if key == status else ''}")
                  for key, label in STATUS_TABS], id="post-tabs", cls=f"{TABS_CLS} mb-4")


def _posts_csv(rows):
    from soloblog.backup import csv_download
    return csv_download("posts.csv", ["title", "address", "type", "status", "created", "updated", "tags", "series",
                                      "views"],
                        [(r["title"], config.BASE_URL + posts.url_for_slug(r["slug"]),
                          "page" if posts.is_page(r) else "post", posts.post_status(r).lower(), r["created_at"],
                          r["updated_at"], r["tags"], r["series_name"], r["views"])
                         for r in rows])


@ar.get("/admin")
def admin_home(session):
    # the address people guess (and the demo's banner links to)
    return RedirectResponse("/admin/posts", status_code=303)


@ar.get("/admin/posts")
def manage_posts(session, status: str = "all", sort: str = "newest", tag: str = "", page: int = 1, q: str = "",
                 month: str = "", access: str = "", kind: str = ""):
    access = access if access in dict(ACCESS_OPTIONS) else ""
    if status in ("posts", "series"):
        # these were tabs once: the same list, by its filter
        status, kind = "all", status
    kind = kind if kind in dict(KIND_OPTIONS) else ""
    if status not in dict(STATUS_TABS + POSTS_VIEWS):
        status = "all"
    if sort not in dict(SORT_OPTIONS):
        sort = "newest"
    page = max(1, page)
    if status in ("tags", "calendar"):
        return Layout(
            PageHeader("Posts and pages", PostsActions(status)),
            _posts_tabs(status),
            TagsManager(q) if status == "tags" else PostsCalendar(month),
            settings=settings.get_all(), logged_in=True, pinned_tree=posts.list_pinned_tree(), admin_page=True,
            live=True
        )

    sort_picker = None
    tag_filter = None
    access_filter = None
    kind_filter = None
    search_box = None
    pagination = None
    bulk_actions = None
    header = None

    if status == "pinned":
        # order here is whatever manual reordering set, not the sort/
        # tag/page controls - those apply to every other tab but don't
        # mean anything once position is manual
        # drafts too, in their place - each says Draft beside its title
        groups = [PinnedGroup("Header", posts.list_pinned_tree(drafts=True), "header"),
                  PinnedGroup("Posts", posts.list_pinned_tree_top(drafts=True)),
                  PinnedGroup("Footer", posts.list_pinned_tree_footer(drafts=True), "footer")]
        body = Div(*groups) if any(groups) else EmptyState(
            "Nothing pinned yet. In a post's Details, choose Where it appears to put it in the menu, "
            "the footer or the top of the blog.", "📌")
    elif status == "trash":
        # list_trash() is a plain filesystem scan (a trashed post has
        # already left the posts table entirely, see its own
        # docstring) - no LIMIT/OFFSET or WHERE/ORDER BY to push down
        # to, so tag filtering, sorting, and pagination all happen here
        # in Python against the already-fetched list, same as Media's
        # gallery tab already does for its own in-memory upload list
        raw_trash = posts.list_trash()
        trash_sort = sort if sort in dict(TRASH_SORT_OPTIONS) else "newest"
        all_trash = [t for t in raw_trash if tag in [x.strip() for x in t["tags"].split(",")]] if tag else raw_trash
        if trash_sort == "oldest":
            all_trash = sorted(all_trash, key=lambda t: t["trashed_at"])
        elif trash_sort == "title":
            all_trash = sorted(all_trash, key=lambda t: t["title"].lower())
        # "newest" needs no re-sort - list_trash() already returns that order
        per = rows_per_page(POSTS_PER_PAGE)
        total_pages = max(1, -(-len(all_trash) // per))
        trash_items = all_trash[(page - 1) * per: page * per]
        base_path = f"/admin/posts?status=trash&sort={trash_sort}&tag={quote(tag)}"
        pagination = Pagination(page, total_pages, base_path, labels=("« Prev", "Next »"), per_page=per,
                                total=len(all_trash))
        # empties everything, not just what's currently filtered -
        # so its own visibility is keyed off raw_trash, not the
        # filtered/paginated all_trash above
        bulk_actions = Form(
            Button(TRASH_SVG, Span("Empty trash", cls="ml-1"), type="button", cls="btn btn-sm text-error",
                   data_confirm="Permanently delete everything in trash? This can't be undone."),
            action="/admin/posts/empty-trash", method="post"
        ) if raw_trash else None
        body = Ul(*[TrashRow(t) for t in trash_items], cls="list") if trash_items else EmptyState(
            "Nothing in trash matches this tag." if tag else "Trash is empty.", "🗑️")
        sort_picker = FilterSelect("Sort", "sort", TRASH_SORT_OPTIONS, trash_sort,
                                   f"/admin/posts?status=trash&tag={quote(tag)}&sort=")
        trash_tags = sorted({x.strip() for t in raw_trash for x in t["tags"].split(",") if x.strip()})
        tag_filter = FilterSelect("Tag", "tag", [("", "All")] + [(t, t) for t in trash_tags], tag,
                                  f"/admin/posts?status=trash&sort={trash_sort}&tag=") if trash_tags else None
        header = ListHeader(
            list_summary(len(all_trash), "post", "", f"tagged {tag}" if tag else ""),
            clear=f"/admin/posts?status=trash&sort={trash_sort}" if tag else None,
            form_id="trash-bulk" if trash_items else None, action="/admin/posts/trash-bulk",
            return_to=f"{base_path}&page={page}", total=len(all_trash), scope={"in_tag": tag},
            buttons=[BulkButton("Restore", "restore"),
                     BulkButton("Delete forever", "delete", danger=True,
                                confirm="Permanently delete the selected posts? This can't be undone.",
                                confirm_all="Permanently delete all {n} posts in trash? This can't be undone.")]
        ) if raw_trash else None
    else:
        per = rows_per_page(POSTS_PER_PAGE)
        rows = posts.list_by_status(status, sort, tag, page, per, q, access, kind)

        def without(name):
            # the list's address less one filter - what that filter's choices add to
            parts = {"status": status, "sort": sort, "tag": tag, "q": q, "access": access, "kind": kind}
            return "/admin/posts?" + "&".join(f"{k}={quote(v)}" for k, v in parts.items() if k != name)
        relative = settings.get("relative_dates") == "1"
        items = []
        for p in rows:
            extra = f"Part of \"{p['series_name']}\"" if p["series_name"] else ""
            items.append(Li(
                Div(
                    # form= ties it to the bulk bar's form, outside the list - each row
                    # already has its own Trash form, and forms can't nest
                    RowCheck("bulk-form", "slugs", p["slug"], p["title"], "mt-0.5", state=posts.bulk_state(p)),
                    Div(
                        A(p["title"], href=f"/admin/edit/{p['slug']}", cls="link text-sm"),
                        PostPills(p),
                        PostMeta(p, relative, extra),
                        TagList(p["tags"], small=True),
                        cls="flex-1 min-w-0"
                    ),
                    # the two used most stay beside the row, the rest under its ⋯
                    RowActions(
                        IconAction(EDIT_SVG, "Edit", href=f"/admin/edit/{p['slug']}"),
                        IconAction(VIEW_SVG, "View", href=posts.url_for(p)),
                        IconAction(FOCUS_SVG, "Edit in Focus", href=f"/admin/edit/{p['slug']}?focus=1"),
                        IconAction(COPY_SVG, "Copy link", **on("click", "copyLink", f"/post/{p['slug']}", EL)),
                        Form(Input(type="hidden", name="slug", value=p["slug"]),
                             IconAction(DUPLICATE_SVG, "Duplicate"),
                             action="/admin/posts/duplicate", method="post", cls="contents"),
                        _delete_form(p, return_to=without("")),
                        id=f"acts-{p['slug']}"),
                    cls="list-col-grow flex justify-between items-start gap-3"
                ),
                cls=f"list-row {TICK_ROW_CLS}", **TICK_ROW
            ))
        body = Ul(*items, cls="list") if items else _no_posts(status, q, bool(tag or access or kind))

        base_path = without("")
        sort_picker = FilterSelect("Sort", "sort", SORT_OPTIONS, sort, without("sort") + "&sort=")
        kind_filter = FilterSelect("Type", "kind", KIND_OPTIONS, kind, without("kind") + "&kind=")
        # who can read it - once there's a choice (members on, or a members post already)
        access_filter = FilterSelect("Who can read", "access", ACCESS_OPTIONS, access, without("access") + "&access=") \
            if members.enabled() or access or posts.count_by_status("all", access="members") \
            or posts.count_by_status("all", access="paid") else None
        # the 40 most used (every tag is under Tags)
        all_tags = posts.top_tags(40, keep=tag)
        tag_filter = FilterSelect("Tag", "tag", [("", "All")] + [(t, t) for t in all_tags], tag,
                                  without("tag") + "&tag=") if all_tags else None
        search_box = SearchField(q, "Search posts and pages…", "/admin/posts",
                                 {"status": status, "sort": sort, "tag": tag, "access": access, "kind": kind})
        total = posts.count_by_status(status, tag, q, access, kind)
        noun = {"posts": "post", "pages": "page", "series": "post"}.get(kind, "post")
        header = ListHeader(
            list_summary(total, noun, q, "in a series" if kind == "series" else "", f"tagged {tag}" if tag else "",
                         f"for {dict(ACCESS_OPTIONS)[access].lower()}" if access else ""),
            clear=f"/admin/posts?status={status}&sort={sort}" if q or tag or access or kind else None,
            form_id="bulk-form" if items else None, action="/admin/posts/bulk", return_to=base_path,
            total=total, scope={"in_status": status, "in_tag": tag, "in_q": q, "in_access": access, "in_kind": kind},
            extra=[Input(name="tag", placeholder="Tag", aria_label="Tag to add", cls="input input-sm w-28"),
                   BulkButton("Add tag", "tag", needs="tag")],
            buttons=[BulkButton("Publish", "publish", for_states=("draft", "scheduled")),
                     BulkButton("Move to drafts", "draft", for_states=("published", "scheduled")),
                     BulkButton("Export", "export", download=True),
                     BulkButton("Move to trash", "trash", danger=True,
                                confirm_all="Move all {n} posts to trash? You can restore them from Trash.")])
        total_pages = max(1, -(-total // per))
        pagination = Pagination(page, total_pages, base_path, labels=("« Prev", "Next »"), per_page=per, total=total)

    # the tabs keep the filters, so Drafts of a tag is one step
    tabs = _posts_tabs(status, "" if status in ("pinned", "trash") else
                       f"&sort={sort}&tag={quote(tag)}&q={quote(q)}&access={access}&kind={kind}")
    from soloblog.routes.welcome import WhatsNew
    return Layout(
        PageHeader("Posts and pages", PostsActions(status)),
        WhatsNew(settings.get_all()) if status == "all" and page == 1 else None,
        tabs,
        ListToolbar([search_box, kind_filter, tag_filter, access_filter, sort_picker], bulk_actions,
                    filtered=bool(kind or tag or access or sort != "newest")),
        header,
        body,
        pagination,
        settings=settings.get_all(), logged_in=True, pinned_tree=posts.list_pinned_tree(), admin_page=True, live=True
    )


def PostsCalendar(month: str):
    """Posts > Calendar: a month of what's published and what's
    scheduled, on the day it goes live (in the site's timezone). A grid
    on wider screens, just the days with posts on a phone."""
    import calendar
    from datetime import date, datetime, timedelta
    today = tz.to_local(utcnow()).date()
    try:
        first = date(int(month[:4]), int(month[5:7]), 1)
    except (ValueError, IndexError):
        first = today.replace(day=1)
    days_in = calendar.monthrange(first.year, first.month)[1]
    # a day either side, for the timezone - then sorted onto local days
    lo = (first - timedelta(days=1)).isoformat()
    hi = (first + timedelta(days=days_in + 1)).isoformat()
    by_day = {}
    for p in posts.list_between(lo, hi):
        when = p["scheduled_at"] or p["created_at"]
        try:
            local = tz.to_local(datetime.fromisoformat(when[:19]))
        except ValueError:
            continue
        if (local.year, local.month) == (first.year, first.month):
            by_day.setdefault(local.day, []).append((local, p))

    def entry(local, p):
        scheduled = posts.post_status(p) == "Scheduled"
        # the whole title in a tooltip, outside the link - its … would cut one off
        return Div(A(Span(local.strftime("%H:%M"), cls="text-base-content/50 mr-1") if scheduled else None, p["title"],
                     href=f"/admin/edit/{p['slug']}",
                     cls=f"block truncate text-xs rounded px-1 py-0.5 pointer-coarse:min-h-11 pointer-coarse:content-center "
                         "hover:bg-base-300 "
                         f"{'bg-warning/15' if scheduled else 'bg-base-200'}"),
                   data_tip=p["title"], cls="tooltip block")

    prev_m = (first - timedelta(days=1)).strftime("%Y-%m")
    next_m = (first + timedelta(days=days_in)).strftime("%Y-%m")
    total = sum(len(v) for v in by_day.values())
    nav = Div(
        Div(A("«", href=f"/admin/posts?status=calendar&month={prev_m}", cls="join-item btn btn-sm",
              aria_label="Previous month"),
            Span(f"{calendar.month_name[first.month]} {first.year}", cls="join-item btn btn-sm btn-active w-40"),
            A("»", href=f"/admin/posts?status=calendar&month={next_m}", cls="join-item btn btn-sm",
              aria_label="Next month"), cls="join"),
        A("Today", href="/admin/posts?status=calendar", cls="btn btn-sm") if first != today.replace(day=1) else None,
        Span(f"{total} post{'s' if total != 1 else ''}" if total else "Nothing this month",
             cls="text-sm text-base-content/60 ml-auto"),
        # on a narrow phone the count goes under the month, not squeezed beside it
        cls="flex flex-wrap items-center gap-x-3 gap-y-1 mb-3"
    )
    cells = [Div(cls="min-h-24") for _ in range(first.weekday())]
    for d in range(1, days_in + 1):
        is_today = date(first.year, first.month, d) == today
        day = [entry(local, p) for local, p in sorted(by_day.get(d, []), key=lambda x: x[0])]
        # a busy day folds past four, so one day doesn't stretch its week
        if len(day) > 4:
            day = day[:3] + [Details(Summary(f"{len(day) - 3} more", cls="text-xs text-base-content/60 "
                                                                         "cursor-pointer px-1"),
                                     Div(*day[3:], cls="flex flex-col gap-0.5 mt-0.5"))]
        cells.append(Div(
            Div(str(d), cls=f"text-xs mb-1 {'font-bold text-primary' if is_today else 'text-base-content/60'}"),
            *day,
            cls="min-h-24 min-w-0 p-1 flex flex-col gap-0.5 rounded-box border-[length:var(--border)] border-base-300"
        ))
    grid = Div(
        *[Div(name, cls="text-xs text-base-content/50 text-center") for name in calendar.day_abbr],
        *cells, cls="hidden sm:grid grid-cols-7 gap-1"
    )
    phone = Ul(*[Li(Div(Div(f"{calendar.day_abbr[date(first.year, first.month, d).weekday()]} {d}",
                            cls="text-xs text-base-content/60 w-14 shrink-0 pt-0.5"),
                        Div(*[entry(local, p) for local, p in sorted(items, key=lambda x: x[0])],
                            cls="flex flex-col gap-0.5 min-w-0 flex-1"), cls="flex gap-2"), cls="list-row")
                 for d, items in sorted(by_day.items())], cls="list sm:hidden") if by_day else None
    return Div(nav, grid, phone,
               P(Span("Yellow", cls="bg-warning/15 text-base-content px-1 rounded"), " is scheduled, with the time it goes live. "
                 "Drafts have no date, so they aren't here.", cls="text-xs text-base-content/50 mt-3"))


@ar.post("/admin/pin/move")
def pin_move(session, slug: str, direction: str):
    if direction in ("up", "down"):
        posts.move_pin(slug, direction)
    return RedirectResponse("/admin/posts?status=pinned", status_code=303)


@ar.post("/admin/nav/move")
def nav_move(session, site: str = "", direction: str = "", where: str = "header"):
    if site in posts.SITE_ROWS:
        posts.move_menu_item("@" + site, direction, where)
    return RedirectResponse("/admin/posts?status=pinned", status_code=303)


def _menu_word(where):
    return "footer" if where == "footer" else "menu"


@ar.post("/admin/nav/add")
def nav_add(session, site: str = "", where: str = "header"):
    s = settings.get_all()
    if where not in posts.MENUS or site not in posts.site_addable(where):
        return status_redirect("/admin/posts?status=pinned", "Choose a page to add", "error")
    if note := posts.menu_note(s, site):
        return status_redirect("/admin/posts?status=pinned", f"{SITE_ROW_WORDS[site]} can't be added: {note}", "error")
    posts.add_site_page(where, site)
    return status_redirect("/admin/posts?status=pinned", f"{SITE_ROW_WORDS[site]} is in the {_menu_word(where)}")


@ar.post("/admin/nav/remove")
def nav_remove(session, site: str = "", where: str = "header"):
    if where not in posts.MENUS or site not in posts.site_addable(where):
        return status_redirect("/admin/posts?status=pinned", "Choose a page to remove", "error")
    posts.remove_site_page(where, site)
    return status_redirect("/admin/posts?status=pinned", f"{SITE_ROW_WORDS[site]} is out of the {_menu_word(where)}")


@ar.post("/admin/nav/rename")
def nav_rename(session, site: str = "", label: str = "", where: str = "header"):
    if where not in posts.MENUS or site not in posts.site_rows(settings.get_all(), where, True):
        return status_redirect("/admin/posts?status=pinned", "Choose a page in the menu", "error")
    label = " ".join(label.split())[:SITE_LABEL_MAX]
    settings.set_many({posts.site_key(where, site, "label"): label})
    return status_redirect("/admin/posts?status=pinned",
                           f"Renamed to {label}" if label else f"Back to {SITE_ROW_WORDS[site]}")


@ar.post("/admin/nav/hide")
def nav_hide(session, hidden: str = ""):
    settings.set_many({"nav_home_hidden": "1" if hidden == "1" else ""})
    return status_redirect("/admin/posts?status=pinned", "Home is hidden from the menu" if hidden == "1"
                           else "Home is in the menu")


@ar.post("/admin/pin/parent")
def pin_parent(session, slug: str, parent_slug: str = ""):
    posts.set_parent(slug, parent_slug)
    return RedirectResponse("/admin/posts?status=pinned", status_code=303)


@ar.post("/admin/posts/restore")
def restore_post(session, slug: str, return_to: str = ""):
    posts.restore_from_trash(slug)
    # return_to - an Undo lands back where the post was trashed from
    target = return_to if is_local_path(return_to) else "/admin/posts?status=trash"
    return _toast_redirect(target, "Restored")


@ar.post("/admin/posts/trash-bulk")
def trash_bulk(session, action: str = "", slugs: list[str] = None, return_to: str = "/admin/posts?status=trash",
               all_matching: str = "", in_tag: str = ""):
    """Restore or delete for good the posts ticked in Trash - or, with
    Select all, every one there (with the tag it was filtered by)."""
    target = return_to if is_local_path(return_to) else "/admin/posts?status=trash"
    trashed = {t["slug"]: t for t in posts.list_trash()}
    if all_matching == "1":
        chosen = [slug for slug, t in trashed.items()
                  if not in_tag or in_tag in [x.strip() for x in t["tags"].split(",")]]
    else:
        chosen = [slug for slug in (slugs or []) if slug in trashed]
    if action not in ("restore", "delete") or not chosen:
        return _toast_redirect(target, "Tick some posts first", "error")
    for slug in chosen:
        posts.restore_from_trash(slug) if action == "restore" else posts.delete_forever(slug)
    n = f"{len(chosen)} post{'s' if len(chosen) != 1 else ''}"
    return _toast_redirect(target, f"Restored {n}" if action == "restore" else f"Permanently deleted {n}")


@ar.post("/admin/posts/delete-forever")
def delete_post_forever(session, slug: str):
    posts.delete_forever(slug)
    return _toast_redirect("/admin/posts?status=trash", "Permanently deleted")


@ar.post("/admin/posts/empty-trash")
def empty_posts_trash(session):
    count = posts.empty_trash()
    return _toast_redirect("/admin/posts?status=trash", f"Permanently deleted {count} post(s)")


def extras_choice(checked, before, before_page, pin_location):
    """Page > Show, as stored. Untouched, a post keeps following the
    default - so moving it to the menu makes it show just its content.
    None when the form had no Show (an older form, or a script) - the
    post keeps what it had."""
    if before is None:
        return None
    was = pages.shown_extras({"extras": before, "pinned": bool(before_page),
                                "pin_location": "header" if before_page else ""})
    checked = set(checked or [])
    if not before and checked == was:
        return ""
    return pages.extras_value(checked, pin_location in ("header", "footer"))


def SoundField(row):
    """Post settings > Page > Background sound: one of the media
    library's audio files, picked like an image (the media picker, showing
    just audio), looping for whoever presses play."""
    from soloblog.ui import SPEAKER_SVG
    return FormField("Background sound", Div(
        Input(name="sound", id="sound", value=row["sound"] if row else "", data_picker_kind="audio",
              placeholder="/uploads/your-sound.mp3", cls="input input-sm flex-1 min-w-0 join-item"),
        MediaPickerButton("sound", icon=SPEAKER_SVG), cls="join w-full"),
        help="Loops while a visitor has it on. It never starts by itself.", cls="mt-3")


def NewsletterChoice(row):
    """Whether this post goes to subscribers - while new posts go out by
    themselves and it hasn't gone yet. Pages never do."""
    s = settings.get_all()
    how = "each" if newsletter.sending(s) else newsletter.digest(s)
    if not how or (row and posts.is_page(row)):
        return None
    if row and newsletter.emailed(row["slug"]):
        held = newsletter.held_for(row["slug"])
        return P(newsletter.held_note(held) if held else "Emailed to subscribers",
                 cls=f"text-xs text-base-content/60 {FIELD_GAP}")
    held_back = bool(row and newsletter.skipped(row["slug"]))
    return Div(Input(type="hidden", name="newsletter_choice", value="1"),
               ToggleField("Email it to subscribers", "newsletter_email", checked=not held_back,
                           help={"each": "When it's published.", "week": "In the next weekly email.",
                                 "month": "In the next monthly email."}[how],
                           site="1", custom=held_back),
               cls=FIELD_GAP)


def held_from_subscribers(row) -> bool:
    """This post won't be emailed, though new posts go to subscribers (the
    changed count in Publishing)."""
    s = settings.get_all()
    return bool(row and not posts.is_page(row) and (newsletter.sending(s) or newsletter.digest(s))
                and not newsletter.emailed(row["slug"]) and newsletter.skipped(row["slug"]))


@ar.post("/admin/save")
def save(request, session, form: SentPost, slug: str = None, new_slug: str = "", word_goal: str = None,
         newsletter_choice: str = "", newsletter_email: bool = False):
    title, body, cover_image = form.title, form.body, form.cover_image
    s = settings.get_all()
    is_new = not slug
    wanted_slug = new_slug.strip().lower()
    renaming = not is_new and wanted_slug and wanted_slug != slug
    # deleted in another tab, or an address that never was one
    if not is_new and not posts.get_post(slug):
        return SaveStatus("This post isn't here any more - it may have been deleted", "error")
    if renaming:
        # checked before anything is saved, so a bad URL never leaves
        # half a change behind
        if not posts.is_valid_slug(wanted_slug):
            return SaveStatus("URL can only use lowercase letters, numbers and dashes", "error")
        if posts.get_post(wanted_slug):
            return SaveStatus("That URL is already used by another post", "error")
    # the same save as every other way in (posts.write) - what isn't sent
    # (visibility while members are off, the extras of a form
    # with no Show) keeps what it had
    if not title.strip():
        return SaveStatus("Give the post a title first", "error")
    new_slug = posts.write(slug if not is_new else None, s["author_name"] or s["site_title"], **form.changes())
    saved = posts.get_post(new_slug)
    if saved and newsletter_choice:
        newsletter.set_skipped(new_slug, not newsletter_email)
    if saved and word_goal is not None:
        set_word_goal(saved["id"], word_goal)
    if is_new:
        # a genuinely new post needs a genuinely new URL - to edit it
        # further, get its preview link, etc - so this is the one save
        # that still navigates. HX-Redirect makes htmx do a real
        # browser navigation there instead of trying to swap the
        # destination page's full HTML into the small status span.
        return FtResponse("", headers={"HX-Redirect": f"/admin/edit/{new_slug}"})
    if renaming:
        error = posts.rename_post(slug, wanted_slug)
        if error:
            return SaveStatus(error, "error")
        # the editor's own URL (and its form action) name the old slug
        return FtResponse("", headers={"HX-Redirect": f"/admin/edit/{wanted_slug}?toast={quote('Saved - URL changed')}"})
    # images screen readers can't describe - a nudge, not a stop
    missing = images.missing_alt(body, cover_image)
    history = RevisionsList(new_slug, oob=True)
    if missing:
        return Span("Saved", Span(f" · {missing} image{'s' if missing != 1 else ''} without alt text "
                                  "(Admin > Media, No alt text)", cls="text-warning"),
                    id="save-status", role="status", cls="text-xs text-success"), history
    return SaveStatus("Saved"), history


def TagsManager(q=""):
    """Admin > Posts > Tags: every tag with its post count - rename it
    everywhere at once (to another tag's name to merge the two), or take
    it off every post. q: the search box's words, for an imported blog's
    hundreds of tags."""
    every = posts.tag_counts_all()
    if not every:
        return EmptyState("No tags yet - add some in a post's Details.", "🏷️")
    q = q.strip()
    rows = [(tag, n) for tag, n in every if q.lower() in tag.lower()] if q else every
    return Div(
        P("Rename a tag to change it on every post at once. Rename it to another tag's name to merge the two.",
          cls="text-sm text-base-content/60 mb-3"),
        ListToolbar([SearchField(q, "Search tags…", "/admin/posts", {"status": "tags"})]),
        ListHeader(list_summary(len(rows), "tag", q), clear="/admin/posts?status=tags" if q else None),
        EmptyState(f"Nothing matches “{q}”.", "🏷️") if not rows else
        Ul(*[Li(Div(
            Form(Input(type="hidden", name="old", value=tag),
                 Input(name="new", value=tag, aria_label=f"New name for {tag}", required=True,
                       cls="input input-sm flex-1 min-w-0 sm:flex-none sm:w-48"),
                 Span(f"{n} post{'s' if n != 1 else ''}", cls="text-xs text-base-content/60 whitespace-nowrap"),
                 id=f"rename-{i}", action="/admin/tags/rename", method="post",
                 cls="flex items-center gap-2 flex-1 min-w-0"),
            RowActions(IconAction(CHECK_SVG, "Rename", type="submit", form=f"rename-{i}"),
                       Form(Input(type="hidden", name="tag", value=tag),
                            IconAction(TRASH_SVG, "Remove", danger=True,
                                       confirm=f"Take “{tag}” off {n} post{'s' if n != 1 else ''}? The posts stay."),
                            action="/admin/tags/remove", method="post", cls="contents"),
                       id=f"tag-acts-{i}"),
            cls="list-col-grow flex items-center gap-2"
        ), cls="list-row") for i, (tag, n) in enumerate(rows)], cls="list")
    )


@ar.post("/admin/tags/rename")
def rename_tag(session, old: str = "", new: str = ""):
    if not old.strip() or not new.strip():
        return _toast_redirect("/admin/posts?status=tags", "Give the tag a name", "error")
    n = posts.rename_tag(old, new)
    return _toast_redirect("/admin/posts?status=tags", f"Renamed on {n} post{'s' if n != 1 else ''}")


@ar.post("/admin/tags/remove")
def remove_tag(session, tag: str = ""):
    n = posts.rename_tag(tag, "")
    return _toast_redirect("/admin/posts?status=tags", f"Removed from {n} post{'s' if n != 1 else ''}")


@ar.post("/admin/posts/duplicate")
def duplicate(session, slug: str = ""):
    new = posts.duplicate_post(slug)
    if not new:
        return _toast_redirect("/admin/posts", "That post is gone", "error")
    return _toast_redirect(f"/admin/edit/{new}", "Duplicated - this is the draft copy")


@ar.post("/admin/posts/bulk")
def bulk(session, action: str = "", tag: str = "", slugs: list[str] = None, return_to: str = "/admin/posts",
         all_matching: str = "", in_status: str = "all", in_tag: str = "", in_q: str = "", in_access: str = "",
         in_kind: str = ""):
    target = return_to if is_local_path(return_to) else "/admin/posts"
    if all_matching == "1":
        # every page the list's filters match, rebuilt here - never more:
        # a tab with no bulk bar (or none at all) isn't widened to All
        if in_status not in ("all", "published", "draft", "scheduled"):
            return _toast_redirect(target, "Choose posts and an action first", "error")
        rows = posts.list_by_status(in_status, "newest", in_tag, 1, 10 ** 6, in_q, in_access, in_kind)
    else:
        rows = [r for r in (posts.get_post(s) for s in (slugs or []) if s) if r]
    if not rows or action not in ("publish", "draft", "tag", "trash", "export"):
        return _toast_redirect(target, "Choose posts and an action first", "error")
    if action == "tag" and not tag.strip():
        return _toast_redirect(target, "Type a tag to add", "error")
    if action == "export":
        return _posts_csv(rows)
    fits = {"publish": ("draft", "scheduled"), "draft": ("published", "scheduled")}.get(action)
    todo = [r for r in rows if not fits or posts.bulk_state(r) in fits]
    from soloblog import publishing
    for r in todo:
        if action == "trash":
            posts.delete_post(r["slug"])
            publishing.retract(r["slug"])
        else:
            posts.update_post(r["slug"], published={"publish": True, "draft": False}.get(action), add_tag=tag)
    publishing.kick()
    n, skipped = len(todo), len(rows) - len(todo)
    done = {"publish": "Published", "draft": "Moved to drafts", "tag": "Tagged", "trash": "Moved to trash"}[action]
    already = {"publish": "already were", "draft": "already drafts"}.get(action, "")
    return _toast_redirect(target, f"{done} · {n} post{'s' if n != 1 else ''}" +
                           (f" · {skipped} {already}" if skipped else ""), "success" if n else "error")


@ar.post("/admin/delete")
def delete(session, slug: str, return_to: str = "/admin/posts"):
    posts.delete_post(slug)
    from soloblog import publishing
    publishing.retract(slug)
    # only ever our own rendered value (_delete_form's hidden field),
    # but checked for a leading "/" anyway rather than trusted
    # outright - same caution any redirect target deserves
    target = return_to if is_local_path(return_to) else "/admin/posts"
    return _toast_redirect(target, "Moved to trash",
                           undo=undo_url("/admin/posts/restore", slug=slug, return_to=target))


@ar.post("/admin/preview")
def preview(session, body: str = ""):
    """The editor's preview: the markdown as the published post renders
    it (wiki links included, as the admin sees them)."""
    # the members-only line is an HTML comment - shown here, so the free part's end can be seen
    marker = "SOLOBLOGMEMBERSCUT"
    html, toc = render_post(posts.MEMBERS_CUT.sub(f"\n{marker}\n", body, count=1))
    html = html.replace(f"<p>{marker}</p>", '<div class="divider text-xs text-base-content/60">'
                                             'Members only from here</div>', 1).replace(marker, "")
    return Response(pages.link_wiki(html, logged_in=True), media_type="text/html")


@ar.post("/admin/upload-image")
async def upload_image(session, request):

    form = await request.form()
    file = form.get("image")
    if not file:
        return JSONResponse({"error": "no file"}, status_code=400)

    data = await file.read()
    if form.get("kind") == "audio":
        # the picker for a sound field (Background sound) - audio only,
        # kept as it is, like Media's own uploads
        name = getattr(file, "filename", "") or ""
        if images.MEDIA_TYPES.get(name.rsplit(".", 1)[-1].lower()) != "audio":
            return JSONResponse({"error": "not an audio file"}, status_code=400)
        try:
            return JSONResponse({"url": images.save_media(data, name)})
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=400)
    if len(data) > 8 * 1024 * 1024:
        return JSONResponse({"error": "file too large"}, status_code=400)

    try:
        url = images.save_upload(data, getattr(file, "filename", "") or "")
    except Exception as e:
        # not a readable image (Pillow can raise more than it documents on
        # a damaged file) - a clean 400 for the caller to report, not a 500
        log.info("an image dropped in the editor was turned away: %s", e)
        return JSONResponse({"error": "not an image"}, status_code=400)
    return JSONResponse({"url": url})


@ar.get("/admin/link-picker")
def link_picker(session, q: str = "", kind: str = "", exclude: str = ""):
    """The link picker's list (ui.LinkPickerResults), as you type - or,
    for a page field (ui.PageField), just the pages it can take."""
    kind = kind if kind in posts.PICK_KINDS else ""
    return LinkPickerResults(*posts.pick_list(q, kind=kind, exclude=exclude), q=q, kind=kind)
