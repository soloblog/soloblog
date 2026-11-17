"""The Design pages: presets, your own colours, the forms and their live preview."""
import json
import re
from fasthtml.common import *
from soloblog import config
from soloblog import settings
from soloblog import fonts
from soloblog import reactions
from soloblog import posts
from soloblog import gallery
from soloblog import pages
from soloblog.themes import OWN_LIMIT, THEME_MODES, delete_own, own_themes, parse_theme, save_own
from soloblog import i18n
from soloblog.ui import Tabs, TABS_CLS, side_where, SIDE_WHERE, SIDE_KEYS, PLUS_SVG, GoLink
from soloblog.ui import PageField, PictureChoiceField
from soloblog.ui import FontCombobox
from soloblog.ui import IconAction, EDIT_SVG
from soloblog.ui import RowActions
from soloblog.ui import (
    FIELD_GAP, SECTION_GAP, FormField, ToggleField, RadioGroupField, SettingsPanel, MediaPickerButton, SaveBar,
    RESTORE_SVG, CHECK_SVG, X_SVG, TRASH_SVG, SortableList, footer_order, SIDE_PLACES, HEADER_ALIGNS, HEADER_WIDTHS,
    FOOTER_LAYOUTS, FOOTER_SPLIT, ROLL_PARTS, LIST_COVER_SIDES, MINIMAL_GROUPS, TIMELINE_ALIGNS, FOOTER_PIECES,
    footer_order as footer_order_of, side_order,
)
from soloblog.guards import status_redirect
from soloblog.ui import SETTINGS_SECTIONS as TABS
from soloblog.routes.admin_settings.base import ThemePicker, _toast_redirect, ar
from soloblog.routes.admin_settings.saves import CARDS_PER_ROW, DESIGN_FIELDS, FONT_SIZES, clean_form

# a small picture of each preset's look (pages.THUMBS)
PRESET_PICTURES = {"default": "preset-default", "custom": "preset-custom", "personal": "preset-personal", "notebook": "preset-notebook", "magazine": "preset-magazine",
                   "photo": "preset-photo", "portfolio": "preset-portfolio", "docs": "preset-docs", "wiki": "preset-wiki", "launch": "preset-launch",
                   "link-in-bio": "preset-link-in-bio", "journal": "preset-journal", "freelancer": "preset-freelancer",
                   "business": "preset-business"}

ROLL_STYLES = {"list": "List", "cards": "Cards", "magazine": "Magazine", "minimal": "Minimal - dates and titles",
               "timeline": "Timeline"}
BODY_COLUMNS = {"standard": "Standard", "narrow": "Narrow — a tighter column for reading"}
HEADER_POSITIONS = {"inline": "Inline — scrolls with the page",
                    "fixed": "Fixed — stays visible at the top, full width",
                    "floating": "Floating — stays visible, inset as its own bar"}


def _extras_of(value: str) -> set:
    """What each post shows, from a post_shows value (pages.default_extras)."""
    if not value:
        return {k for k in pages.EXTRAS if k not in pages.OFF_BY_DEFAULT}
    return set() if value == "none" else set(value.split(",")) & set(pages.EXTRAS)


# Settings > Posts > Breadcrumbs and Header and footer > Footer position
BREADCRUMBS = {"auto": "Home › series or first tag › post", "tag": "Home › first tag › post",
               "home": "Home › post", "off": "Off"}
FOOTER_POSITIONS = {"inline": "Inline — scrolls with the page",
                    "fixed": "Fixed — stays visible at the bottom, full width",
                    "floating": "Floating — stays visible, inset as its own bar"}


def preset_changes(values: dict, s, every=False) -> list:
    """What `values` (a preset's settings) would change on a site set as
    `s` - in the words each setting has on its own page, only the ones
    that differ: "Posts are shown as: Cards → Minimal". every: each one
    it sets, as (line, changes) - "Posts are shown as: List" where the
    site has that already."""
    short = lambda text: re.split(r" — | - ", text, maxsplit=1)[0]  # noqa: E731
    font = lambda v: short(fonts.STACKS[v][0]) if v in fonts.STACKS else "Default"  # noqa: E731
    on_off = {"1": "On", "0": "Off"}
    palette = lambda v: v.capitalize() if v else "-"  # noqa: E731
    one = {"roll_style": ("Posts are shown as", ROLL_STYLES), "cards_per_row": ("Cards in a row", CARDS_PER_ROW),
           "minimal_group": ("Group posts by", MINIMAL_GROUPS),
           "roll_placeholder": ("Placeholder for posts without a cover", on_off),
           "body_width": ("Reading column", BODY_COLUMNS),
           "section_space": ("Space between sections", pages.SPACINGS),
           "section_heading_align": ("Section headings", pages.SECTION_HEADINGS), "font_body": ("Text font", font),
           "font_headings": ("Heading font", font), "font_size": ("Text size", FONT_SIZES),
           "header_style": ("Header position", HEADER_POSITIONS), "header_align": ("Header layout", HEADER_ALIGNS),
           "header_width": ("Header width", HEADER_WIDTHS),
           **{k: (SIDE_LABELS[k][0], SIDE_PLACES) for k in SIDE_KEYS},
           "toc_style": ("Table of contents", pages.TOC_STYLES), "toc_numbers": ("Number the contents", on_off),
           "heading_fold": ("Fold headings", pages.FOLD_STYLES), "cover_width": ("Cover image", pages.COVER_STYLES),
           "gallery_style": ("Default gallery style", gallery.STYLES),
           "portfolio_style": ("Portfolio pages", pages.PORTFOLIO_STYLES), "page_animations": ("Animations", on_off),
           "section_motion": ("Sections appear", pages.SECTION_MOTIONS),
           # what Settings > Banner and Width and spacing call them
           "banner_width": ("Banner width", pages.COVER_WIDTHS),
           "side_plain": ("Blend side panels into the page", on_off),
           # the rest of the look - what Default and Custom set as well -
           # in the words of the pages they're on
           "theme": ("Light palette", palette), "theme_dark": ("Dark palette", palette),
           "theme_mode": ("Visitors see", dict(THEME_MODES)),
           "visitor_theme_switching": ("Let readers pick other colours", on_off),
           "glass_effect": ("Frosted glass", on_off), "smooth_scroll": ("Smooth scrolling", on_off),
           "posts_per_page": ("Posts per page", lambda v: v or "-"),
           "roll_list_cover": ("Cover position", LIST_COVER_SIDES),
           "timeline_align": ("Timeline line", TIMELINE_ALIGNS),
           "milestones_align": ("Line in Milestones sections", TIMELINE_ALIGNS),
           "breadcrumbs": ("Breadcrumbs", BREADCRUMBS),
           "relative_dates": ("Use relative dates", on_off),
           "show_updated": ("Show when a post was updated", on_off),
           "scroll_to_top": ("Show a “back to top” button", on_off),
           "sidenotes": ("Footnotes beside the text", on_off),
           "links_new_tab": ("Open links to other sites in a new tab", on_off),
           "reactions_style": ("Reader reactions", dict(reactions.STYLES)),
           "toc_fold": ("Fold contents", pages.TOC_FOLDS),
           "heading_links": ("A copy-link button beside each heading", on_off),
           "lightbox_images": ("Open any image bigger with a click", on_off),
           "footer_enabled": ("Show the footer", on_off), "footer_style": ("Footer position", FOOTER_POSITIONS),
           "footer_layout": ("Footer layout", FOOTER_LAYOUTS),
           "footer_show_bio": ("Author bio in the footer", on_off),
           "footer_show_socials": ("Social links in the footer", on_off),
           "footer_show_pages": ("Pinned pages in the footer", on_off),
           "footer_show_note": ("Footer note / copyright in the footer", on_off),
           "footer_show_browse": ("Archive, Tags and RSS links in the footer", on_off),
           "footer_show_powered_by": ("“Powered by Soloblog” in the footer", on_off)}
    many = {"roll_shows": ("Each post in the list shows", ROLL_PARTS, lambda d: set((d.get("roll_shows") or "").split(","))),
            "post_shows": ("Each post shows", pages.EXTRAS, lambda d: _extras_of(d.get("post_shows") or "")),
            **{f"{k}_where": (f"{SIDE_LABELS[k][0]} shows on", SIDE_WHERE, lambda d, k=k: side_where(d, k))
               for k in SIDE_KEYS},
            "toc_style_where": ("Table of contents shows on", pages.TOC_WHERE,
                                lambda d: set((d.get("toc_style_where") or "").split(","))),
            "reaction_emojis": ("Emoji offered", {k: f"{e} {name}" for k, (e, name) in reactions.CHOICES.items()},
                                lambda d: set(reactions.enabled_keys(d.get("reaction_emojis") or "")))}
    lines = []
    for key, value in values.items():
        if key in one:
            label, words = one[key]
            before, after = [words(v) if callable(words) else short(words.get(v, v or "-"))
                             for v in (s.get(key) or "", value)]
            if before != after:
                lines.append((f"{label}: {before} → {after}", True) if every else f"{label}: {before} → {after}")
            elif every:
                lines.append((f"{label}: {after}", False))
        elif key in many:
            label, words, read = many[key]
            now, then = read(s) & set(words), read({key: value}) & set(words)
            if every:
                lines.append((f"{label}: " + (", ".join(short(words[k]) for k in words if k in then) or "Nothing"),
                              now != then))
                continue
            added = [short(words[k]) for k in words if k in then - now]
            dropped = [short(words[k]) for k in words if k in now - then]
            if added or dropped:
                lines.append(f"{label}: " + "; ".join(filter(None, [
                    "adds " + ", ".join(added) if added else "", "takes off " + ", ".join(dropped) if dropped else ""])))
        elif key == "side_order":
            moved = [k for k in (value or "").split(",") if k] != side_order(s)
            line = "Side panels' order: " + ", ".join(SIDE_LABELS[k][0] for k in value.split(",") if k in SIDE_LABELS)
            if every:
                lines.append((line, moved))
            elif moved:
                lines.append(line)
        elif key == "footer_order":
            order = lambda v: [k for k in (v or "").split(",") if k in FOOTER_PIECES]  # noqa: E731
            moved = order(value) != order(",".join(footer_order_of(s)))
            line = "Footer's order: " + ", ".join(FOOTER_PIECES[k] for k in order(value))
            if every:
                lines.append((line, moved))
            elif moved:
                lines.append(line)
        elif key == "home_page" and not value and s.get("home_page"):
            lines.append(("Homepage: back to your posts", True) if every else "Homepage: back to your posts")
    return lines


def PresetChanges(lines, summary):
    """A folded list of what a preset sets (preset_changes): a line, or
    (line, changes) - what it would change in bold, reading "now → then"."""
    return Details(Summary(summary, cls="cursor-pointer w-fit link link-hover py-2"),
                   Ul(*[Li(Strong(line[0], cls="text-base-content") if isinstance(line, tuple) and line[1]
                           else line[0] if isinstance(line, tuple) else line)
                        for line in lines], cls="list-disc pl-4 flex flex-col gap-0.5"),
                   cls="text-xs text-base-content/70 mt-1")


def _sets_summary(lines) -> str:
    """A card's: how many it sets, and how many of those it would change."""
    total, changes = len(lines), sum(1 for _, changed in lines if changed)
    if not changes:
        return f"Your site looks like this - sets {total} setting" + ("" if total == 1 else "s")
    return f"Changes {changes} of {total} settings"


def UsingPreset(name, changed):
    """Beside Undo: the preset in use, opening to what Undo puts back."""
    if not changed:
        return Span(f"Using {name}" if name else "", cls="text-xs text-base-content/60 py-2")
    n = len(changed)
    return Details(Summary(f"Using {name} - changed {n} setting" + ("" if n == 1 else "s"),
                           cls="cursor-pointer w-fit link link-hover py-2"),
                   Ul(*[Li(line) for line in changed], cls="list-disc pl-4 flex flex-col gap-0.5"),
                   cls="text-xs text-base-content/70 min-w-0")


# Side panels' names and help (Settings > Blog layout)
SIDE_LABELS = {"side_tags": ("Tag cloud", "Your most used tags."),
               "side_archive": ("Archive links", "The last 12 months."),
               "side_author": ("About the author", "Your photo, name, bio and links. Where it shows, it takes the "
                                                   "place of About the author under each post.")}


def _undo_changes(s) -> list:
    """What the preset in use changed, from what Undo keeps."""
    try:
        before = json.loads(s.get("preset_undo") or "")["before"]
    except (ValueError, KeyError, TypeError):
        return []
    return preset_changes({k: s.get(k) for k in before}, before)


def _custom_words(presets):
    """Custom's name and line: when it was saved."""
    from datetime import date
    saved = presets.custom_saved_on()
    try:
        when = date.fromisoformat(saved).strftime("%-d %b %Y")
    except ValueError:
        when = ""
    return "Custom", f"Your own look, saved {when}." if when else "Your own look, as you saved it."


def EmptyCustomCard():
    """Custom before anything's saved there: the way to save the look you have."""
    return Div(
        Div(pages.thumb(PRESET_PICTURES["custom"]), cls="mb-2 @max-lg:mb-0 @max-lg:row-span-4"),
        Span("Custom", cls="font-medium text-sm"),
        P("Save the look you have now, to come back to after trying others.",
          cls="text-xs text-base-content/60 mt-1"),
        Form(Div(Button(CHECK_SVG, Span("Save current look", cls="ml-1"), type="submit", cls="btn btn-sm"),
                 cls="flex items-center justify-end gap-3 mt-2"),
             action="/admin/presets/save-custom", method="post", cls="mt-auto"),
        cls="rounded-box border-[length:var(--border)] border-base-300 p-3 flex flex-col "
            "@max-lg:grid @max-lg:grid-cols-[6rem_minmax(0,1fr)] @max-lg:gap-x-3 @max-lg:items-start "
            "@max-lg:[&>form]:col-span-2"
    )


def PresetsPanel(s):
    """Settings > Style > Settings presets (presets.py): a starting style in one
    go - previewed first, used with a click, undone with another."""
    from soloblog import presets
    own_pages = [p for p in posts.list_posts(include_drafts=True) if posts.is_page(p)]
    current = s.get("preset")

    def card(key, name, about, needs):
        # a new page, or one of yours - the picker shows once you choose that
        radio = lambda value, label, checked=False: Label(  # noqa: E731
            Input(type="radio", name="page_from", value=value, checked=checked, cls="radio radio-xs"),
            Span(label), cls="flex items-center gap-2 text-sm cursor-pointer")
        page_choice = Fieldset(
            Legend("Homepage", cls="sr-only"),
            radio("new", "A new page", True), radio("mine", "One of your pages"),
            Div(PageField("page", "", "page", placeholder="Choose a page", id=f"preset-page-{key}"),
                data_shown_for="page_from=mine", hidden=True),
            cls="flex flex-col gap-1.5 mt-2 min-w-0") if presets.uses_page(key) and own_pages else None
        # one to a row (a narrow column - Preview mode's, a phone's): the
        # picture beside the words, not across the card at full size
        return Div(
            Div(pages.thumb(PRESET_PICTURES.get(key, "preset-default")),
                cls="mb-2 @max-lg:mb-0 @max-lg:row-span-4"),
            Div(Span(name, cls="font-medium text-sm"),
                Span("In use", cls="badge badge-xs badge-success badge-soft") if key == current else None,
                cls="flex items-center gap-2"),
            P(about, cls="text-xs text-base-content/60 mt-1"),
            # what it would change on the site as it is now - not the ~30 it sets
            # everything it sets - in use too; what it would change in bold
            PresetChanges(lines := preset_changes(presets.find(key)[2], s, every=True), _sets_summary(lines)),
            P("Its homepage is a page of yours:" if presets.uses_page(key) and pages else
              "Makes a page for your homepage." if presets.uses_page(key) else
              "Your wiki's front page becomes the homepage - with a first note, if you have none.",
              cls="text-xs text-base-content/50 mt-1") if needs else None,
            Form(Input(type="hidden", name="key", value=key), page_choice,
                 # Custom: the look as it is now, in place of the one saved - a
                 # line of its own, three didn't fit in the buttons' row
                 Div(Button("Save current look", type="submit", formaction="/admin/presets/save-custom",
                            cls="link text-xs inline-block py-3 -my-3",
                            data_confirm="Replace Custom with the look you have now?"),
                     cls="mt-2") if key == presets.CUSTOM_KEY else None,
                 Div(GoLink("Preview", f"/admin/presets/preview/{key}"),
                     Button(CHECK_SVG, Span("Use this", cls="ml-1"), type="submit", cls="btn btn-sm",
                            data_confirm="Use the Default style? Your colours go back to the default too; your "
                                         "writing stays." if key == presets.DEFAULT_KEY else
                            "Use your Custom look? Its colours too; your writing stays." if key == presets.CUSTOM_KEY
                            else f"Use the {name} style? Your colours and writing stay as they are."),
                     cls="flex items-center justify-end gap-3 mt-2"),
                 # at the card's foot, level with its neighbour's when a list opens
                 action="/admin/presets/apply", method="post", cls="mt-auto"),
            cls="rounded-box border-[length:var(--border)] border-base-300 p-3 flex flex-col "
                "@max-lg:grid @max-lg:grid-cols-[6rem_minmax(0,1fr)] @max-lg:gap-x-3 @max-lg:items-start "
                # its buttons across the whole card, under the picture and words
                "@max-lg:[&>form]:col-span-2"
        )
    return SettingsPanel(
        "Settings presets",
        P("A starting style for your whole site, in one go. Your colours and writing stay as they are.",
          cls="text-sm text-base-content/70 mb-3"),
        # Custom first, your own look saved; then Default, every look setting
        # back to how Soloblog comes. Two to a row where their column has
        # room (@container): in Preview mode's narrow settings column, one -
        # two squeezed their buttons out
        Div(Div(card(presets.CUSTOM_KEY, *_custom_words(presets), None) if presets.find(presets.CUSTOM_KEY)
                else EmptyCustomCard(),
                card(presets.DEFAULT_KEY, *presets.find(presets.DEFAULT_KEY)[:2], None),
                *[card(key, name, about, needs) for key, (name, about, _, needs) in presets.PRESETS.items()],
                cls="grid grid-cols-1 @lg:grid-cols-2 gap-3"), cls="@container"),
        Form(Div(UsingPreset(presets.find(current)[0] if presets.find(current) else "", _undo_changes(s)),
                 Button(RESTORE_SVG, Span("Undo it", cls="ml-1"), type="submit", cls="btn btn-sm btn-ghost shrink-0"),
                 cls="flex items-start justify-end gap-3 mt-3"),
             action="/admin/presets/undo", method="post")
        if s.get("preset_undo") else None,
        key="style-presets"
    )


def DesignPanels(s):
    return Div(PresetsPanel(s), _design_form(s), cls="flex flex-col gap-3")





# ---- Custom colours: daisyUI themes made in its theme generator
# (themes.parse_theme), beside the built-in palettes

GENERATOR_URL = "https://daisyui.com/theme-generator/"


def OwnPreview(values):
    """A pasted theme's look before it's saved: its own values on a sample,
    as daisyUI's components read them (all checked by themes.parse_theme)."""
    style = ";".join(f"{k}:{v}" for k, v in values.items())
    return Div(
        P("Aa", cls="text-2xl font-bold leading-none"),
        Div(Span("Primary", cls="btn btn-sm btn-primary"), Span("Secondary", cls="btn btn-sm btn-secondary"),
            Span("Accent", cls="btn btn-sm btn-accent"), cls="flex flex-wrap gap-2"),
        Div(Span("A badge", cls="badge badge-neutral"), Span("Words on the page", cls="text-sm"),
            cls="flex flex-wrap items-center gap-2"),
        style=style, aria_hidden="true",
        cls="bg-base-200 text-base-content rounded-box border-[length:var(--border)] border-base-300 p-4 "
            "flex flex-col gap-3")


def _theme_text(t):
    """A saved theme as the generator writes one - to change and paste again."""
    lines = [f'  name: "{t["name"]}";', f"  color-scheme: {t['scheme']};"]
    lines += [f"  {k}: {v};" for k, v in t["values"].items()]
    return '@plugin "daisyui/theme" {\n' + "\n".join(lines) + "\n}"


def OwnThemeDialog(t=None, error="", pasted=None, name=None):
    """Add (or change) one of your own palettes: paste the generator's
    CSS, see it, name it, save."""
    key = t["key"] if t else "new"
    return Dialog(
        Form(
            H3(f"Change {t['name']}" if t else i18n.spell("Add custom colours"), id=f"own-title-{key}", cls="font-semibold text-lg mb-1"),
            P("Make a theme in ", A("daisyUI's theme generator", href=GENERATOR_URL, target="_blank", rel="noopener",
                                    cls="link"),
              ", copy its CSS and paste it here. Its corners, borders, sizes and shadows come with its colours.",
              cls="text-sm text-base-content/70 mb-3"),
            Input(type="hidden", name="key", value=t["key"] if t else ""),
            FormField("The theme's CSS", Textarea(pasted if pasted is not None else (_theme_text(t) if t else ""),
                                                  name="css", rows="7", required=True, spellcheck="false",
                                                  placeholder='@plugin "daisyui/theme" { ... }',
                                                  hx_post="/admin/themes/preview", hx_trigger="input changed delay:400ms",
                                                  hx_target=f"#own-preview-{key}", hx_swap="innerHTML",
                                                  cls="textarea textarea-sm w-full font-mono text-xs"), cls=FIELD_GAP),
            Div(OwnPreview(t["values"]) if t else P("A preview shows here once you paste.",
                                                   cls="text-sm text-base-content/60"),
                id=f"own-preview-{key}", cls=FIELD_GAP),
            FormField("Name", Input(name="name", value=name if name is not None else (t["name"] if t else ""),
                                    maxlength="40", placeholder="The theme's own name", cls="input input-sm w-full")),
            Div(Span(error, id=f"own-status-{key}", data_status_slot=True, role="status",
                     cls=f"text-xs {'text-error' if error else 'text-base-content/50'}"),
                Div(Button(X_SVG, Span("Cancel", cls="ml-1"), type="button", cls="btn btn-sm",
                           data_close_dialog=f"own-theme-{key}"),
                    Button(CHECK_SVG, Span("Save", cls="ml-1"), type="submit", cls="btn btn-sm btn-primary"),
                    cls="flex gap-2 ml-auto"),
                cls="flex items-center gap-2 mt-4"),
            hx_post="/admin/themes/save", hx_target=f"#own-theme-{key}", hx_swap="outerHTML",
            cls="modal-box max-w-lg"),
        Form(Button(cls="cursor-default", aria_label="Close"), method="dialog", cls="modal-backdrop"),
        id=f"own-theme-{key}", aria_labelledby=f"own-title-{key}", open=bool(error) or None, cls="modal")


def OwnThemeForms(s):
    """Outside the Style form: each palette's dialog and delete form."""
    themes = own_themes(s)
    return (OwnThemeDialog(), *[OwnThemeDialog(t) for t in themes],
            *[Form(Input(type="hidden", name="key", value=t["key"]), id=f"own-delete-{t['key']}",
                   action="/admin/themes/delete", method="post", cls="hidden") for t in themes])


def OwnThemes(s):
    """Settings > Style > Colours: your own palettes, each with its swatch,
    light or dark, and Change and Delete."""
    themes = own_themes(s)
    full = len(themes) >= OWN_LIMIT
    rows = [Div(
        Div(Div(cls="w-3 h-3 rounded-full bg-primary"), Div(cls="w-3 h-3 rounded-full bg-secondary"),
            Div(cls="w-3 h-3 rounded-full bg-accent"), data_theme=t["key"],
            cls="flex gap-1 p-1.5 rounded-field border-[length:var(--border)] border-base-300 bg-base-100 shrink-0"),
        Div(P(t["name"], cls="text-sm font-medium truncate"),
            P("Dark" if t["scheme"] == "dark" else "Light", cls="text-xs text-base-content/60"), cls="flex-1 min-w-0"),
        RowActions(IconAction(EDIT_SVG, "Change", type="button", data_open_dialog=f"own-theme-{t['key']}"),
                   IconAction(TRASH_SVG, "Delete", danger=True, form=f"own-delete-{t['key']}",
                              confirm=f"Delete {t['name']}? A palette using it goes back to the default."),
                   id=f"own-acts-{t['key']}"),
        cls="flex items-center gap-3 py-2 border-b-[length:var(--border)] border-base-300 last:border-0")
        for t in themes]
    return FormField("Custom colours", Div(
        *rows,
        Div(Button(PLUS_SVG, Span(i18n.spell("Add colours"), cls="ml-1"), type="button", cls="btn btn-sm",
                   data_open_dialog="own-theme-new", disabled=full or None),
            Span(f"That's {OWN_LIMIT} - delete one to add another" if full else "", cls="text-xs text-base-content/60"),
            cls="flex items-center gap-3 mt-2")),
        help="Colours, corners, borders and shadows, made in daisyUI's theme generator. Shown with the palettes above.",
        cls=FIELD_GAP)


def _look_panels(s) -> list:
    """Colours and fonts."""
    return [
        SettingsPanel(
            "Colours",
            *ThemePicker(s),
            OwnThemes(s),
            ToggleField(
                "Let readers pick other colours", "visitor_theme_switching",
                checked=(s["visitor_theme_switching"] == "1"),
                help="A Colours menu in the header, for themselves only.",
                cls=FIELD_GAP
            ),
            ToggleField(
                "Frosted glass", "glass_effect", checked=(s["glass_effect"] == "1"),
                help="The header, menus and popups let the page show through, blurred."
            ),
            key="style-colours"
        ),
        SettingsPanel(
            "Fonts and text size",
            Div(
                *[FormField(label, FontCombobox(key, s[key], label))
                  for key, label in (("font_body", "Text font"), ("font_headings", "Heading font"))],
                cls="grid grid-cols-1 sm:grid-cols-2 gap-2"
            ),
            Div(cls=FIELD_GAP),
            RadioGroupField("Text size", "font_size", list(FONT_SIZES.items()),
                            s["font_size"] if s["font_size"] in FONT_SIZES else "medium",
                            help="For your whole site and the admin."),
            key="style-fonts"
        ),
    ]


def _header_panels(s) -> list:
    """The header: its width, bar, icons and the app it installs as."""
    return [
        SettingsPanel(
            "Width and spacing",
            RadioGroupField(
                "Reading column", "body_width", list(BODY_COLUMNS.items()),
                selected="narrow" if s["body_width"] == "narrow" else "standard", cls=FIELD_GAP
            ),
            RadioGroupField("Space between sections", "section_space", list(pages.SPACINGS.items()),
                            s["section_space"] if s["section_space"] in pages.SPACINGS else "medium",
                            help="On every page. Each post or page can choose its own.", cls=FIELD_GAP),
            RadioGroupField("Section headings", "section_heading_align", list(pages.SECTION_HEADINGS.items()),
                            s["section_heading_align"] if s["section_heading_align"] in pages.SECTION_HEADINGS
                            else "left",
                            help="The heading and the words under it. Each section can choose its own."),
            key="header-width"
        ),
        SettingsPanel(
            "Header",
            RadioGroupField(
                "Header position", "header_style", list(HEADER_POSITIONS.items()),
                selected=s["header_style"] if s["header_style"] in ("fixed", "floating") else "inline",
                cls=FIELD_GAP
            ),
            RadioGroupField(
                "Header layout", "header_align", list(HEADER_ALIGNS.items()),
                selected=s["header_align"] if s["header_align"] in HEADER_ALIGNS else "left",
                help="On a phone, the menu is always behind a button.", cls=FIELD_GAP
            ),
            RadioGroupField(
                "Header width", "header_width", list(HEADER_WIDTHS.items()),
                selected=s["header_width"] if s["header_width"] in HEADER_WIDTHS else "column",
                help="Links that don't fit go under More.", cls=FIELD_GAP
            ),
            # the menu's pages and their order live with the pages themselves
            P(A("Arrange the menu", href="/admin/posts?status=pinned", cls="link"),
              " - its pages, their order and what's under each.", cls="text-sm text-base-content/70"),
            key="header-bar"
        ),
        SettingsPanel(
            "Icons",
            P("Add one and it's used for the others too.", cls=f"text-sm text-base-content/60 {FIELD_GAP}"),
            FormField(
                "Header icon",
                Div(
                    Input(name="header_icon_url", id="header_icon_url", value=s["header_icon_url"],
                          placeholder="/uploads/logo.webp", cls="input input-sm flex-1 min-w-0 join-item"),
                    MediaPickerButton("header_icon_url"),
                    cls="join w-full"
                ),
                help="Beside your site's name in the header - a logo, say.",
                cls=FIELD_GAP
            ),
            FormField(
                "Favicon",
                Div(
                    Input(name="favicon_url", id="favicon_url", value=s["favicon_url"],
                          placeholder="/uploads/favicon.png", cls="input input-sm flex-1 min-w-0 join-item"),
                    MediaPickerButton("favicon_url"),
                    cls="join w-full"
                ),
                help="In browser tabs and bookmarks."
            ),
            key="header-icons"
        ),
        SettingsPanel(
            "On a phone's home screen",
            P("When someone adds your site to their phone's home screen, like an app.",
              cls=f"text-sm text-base-content/60 {FIELD_GAP}"),
            FormField("App icon", Div(Input(name="app_icon_url", id="app_icon_url", value=s["app_icon_url"],
                                            placeholder="/uploads/icon.webp",
                                            cls="input input-sm flex-1 min-w-0 join-item"),
                                      MediaPickerButton("app_icon_url"), cls="join w-full"),
                      help="Square, 512 × 512 or larger. Empty: your favicon.",
                      cls=FIELD_GAP),
            FormField("App name", Input(name="app_name", value=s["app_name"], maxlength="30",
                                        placeholder=s["site_title"], cls="input input-sm w-full"),
                      help="Under the icon. Empty: your site's title."),
            key="header-app"
        ),
    ]


def _blog_panels(s) -> list:
    """The blog roll: its layout, and what's beside it."""
    return [
        SettingsPanel(
            "Blog layout",
            PictureChoiceField(
                "Posts are shown as", "roll_style",
                [(k, label, "timeline" if k == "timeline" else f"roll-{k}") for k, label in ROLL_STYLES.items()],
                selected=s["roll_style"], cls=FIELD_GAP
            ),
            Div(RadioGroupField("Timeline line", "timeline_align", list(TIMELINE_ALIGNS.items()),
                                s["timeline_align"] if s["timeline_align"] in TIMELINE_ALIGNS else "center",
                                help="On a phone, Centred shows on the left.", cls=FIELD_GAP),
                data_shown_for="roll_style=timeline", hidden=s["roll_style"] != "timeline"),
            FormField("Each post in the list shows", Div(
                *[Label(Input(type="checkbox", name="roll_shows", value=key, cls="checkbox checkbox-xs",
                              checked=key in s["roll_shows"].split(",")),
                        Span(label, cls="text-sm"), cls="flex items-center gap-2 cursor-pointer")
                  for key, label in ROLL_PARTS.items()],
                cls="grid grid-cols-2 sm:grid-cols-3 gap-2"),
                cls=FIELD_GAP),
            Div(RadioGroupField("Group posts by", "minimal_group", list(MINIMAL_GROUPS.items()),
                                s["minimal_group"] if s["minimal_group"] in MINIMAL_GROUPS else "none",
                                cls=FIELD_GAP),
                data_shown_for="roll_style=minimal", hidden=s["roll_style"] != "minimal"),
            Div(RadioGroupField("Cover position", "roll_list_cover", list(LIST_COVER_SIDES.items()),
                                s["roll_list_cover"] if s["roll_list_cover"] in LIST_COVER_SIDES else "right",
                                cls=FIELD_GAP),
                data_shown_for="roll_style=list", hidden=s["roll_style"] != "list"),
            Div(ToggleField("Placeholder for posts without a cover", "roll_placeholder",
                            checked=s["roll_placeholder"] != "0",
                            help="A tile in your colours, so the cards line up.", cls=FIELD_GAP),
                data_shown_for="roll_style=cards|magazine", hidden=s["roll_style"] not in ("cards", "magazine")),
            Div(RadioGroupField("Cards in a row", "cards_per_row", list(CARDS_PER_ROW.items()),
                                s["cards_per_row"] if s["cards_per_row"] in CARDS_PER_ROW else "3",
                                cls=FIELD_GAP),
                data_shown_for="roll_style=cards", hidden=s["roll_style"] != "cards"),
            FormField(
                "Posts per page",
                Select(*[Option(str(n), value=str(n), selected=(s["posts_per_page"] == str(n)),
                                data_default=str(n) == settings.DEFAULTS["posts_per_page"] or None)
                         for n in sorted(set(PER_PAGE) | ({int(s["posts_per_page"])}
                                                          if s["posts_per_page"].isdigit() else set()))],
                       name="posts_per_page", cls="select select-sm"),
                cls=FIELD_GAP
            ),
            key="blog-layout"
        ),
        SettingsPanel(
            "Side panels",
            # in the order they come on a side, or under the posts
            SortableList("side_order", [(key, Div(
                RadioGroupField(label, key, list(SIDE_PLACES.items()),
                                s[key] if s[key] in SIDE_PLACES else "off", help=help, cls="mb-2"),
                # nothing to choose while it's off; clearing every tick turns it off (placed)
                Div(FormField("Shows on", Div(
                    *[Label(Input(type="checkbox", name=f"{key}_where", value=where, cls="checkbox checkbox-xs",
                                  checked=where in side_where(s, key)),
                            Span(text, cls="text-sm"), cls="flex items-center gap-1.5 cursor-pointer")
                      for where, text in SIDE_WHERE.items()],
                    cls="flex flex-wrap gap-x-4 gap-y-1")),
                    data_shown_for=f"{key}!=off", hidden=s[key] not in SIDE_PLACES or s[key] == "off")))
                for key, (label, help) in sorted(SIDE_LABELS.items(), key=lambda kv: side_order(s).index(kv[0]))]),
            P("Drag them into the order they come in. Each post or page can leave them out.",
              cls=f"text-xs text-base-content/60 {FIELD_GAP}"),
            # how they look, with where they go (it was under Header and footer)
            ToggleField("Blend side panels into the page", "side_plain", checked=(s["side_plain"] == "1"),
                        help="No box around the panels beside the page."),
            key="blog-side"
        ),
    ]


def _post_panels(s) -> list:
    """A post: its breadcrumbs, images, contents, reading aids and extras."""
    return [
        SettingsPanel(
            "Breadcrumbs",
            RadioGroupField(
                "Above each post", "breadcrumbs", list(BREADCRUMBS.items()),
                selected=s["breadcrumbs"] if s["breadcrumbs"] in ("auto", "tag", "home", "off") else "auto",
            ),
            key="posts-breadcrumbs"
        ),
        SettingsPanel(
            "Images",
            # the biggest choice first: how a post opens
            RadioGroupField("Cover image", "cover_width", list(pages.COVER_STYLES.items()),
                            s["cover_width"] if s["cover_width"] in pages.COVER_STYLES else "column",
                            help="Each post can choose its own.", cls=FIELD_GAP),
            RadioGroupField(
                "Default gallery style", "gallery_style", list(gallery.STYLES.items()),
                selected=s["gallery_style"] if s["gallery_style"] in gallery.STYLES else "grid",
                help="Each gallery can choose its own.", cls=FIELD_GAP
            ),
            RadioGroupField(
                "Portfolio pages", "portfolio_style", list(pages.PORTFOLIO_STYLES.items()),
                selected=s["portfolio_style"] if s["portfolio_style"] in pages.PORTFOLIO_STYLES else "grid",
                help="Each portfolio can choose its own.", cls=FIELD_GAP
            ),
            ToggleField("Open any image bigger with a click", "lightbox_images",
                        checked=(s["lightbox_images"] == "1"),
                        help="Gallery images always do."),
            key="posts-images"
        ),
        SettingsPanel(
            "Contents and sections",
            RadioGroupField("Table of contents", "toc_style", list(pages.TOC_STYLES.items()),
                            s["toc_style"] if s["toc_style"] in pages.TOC_STYLES else "top",
                            help="For posts with three or more headings. Each post can choose its own.",
                            cls="mb-2"),
            Div(FormField("Shows on", Div(
                *[Label(Input(type="checkbox", name="toc_style_where", value=where, cls="checkbox checkbox-xs",
                              checked=where in s["toc_style_where"].split(",")),
                        Span(text, cls="text-sm"), cls="flex items-center gap-1.5 cursor-pointer")
                  for where, text in pages.TOC_WHERE.items()],
                cls="flex flex-wrap gap-x-4 gap-y-1")),
                data_shown_for="toc_style!=off", hidden=s["toc_style"] == "off", cls=FIELD_GAP),
            RadioGroupField("Fold contents", "toc_fold", list(pages.TOC_FOLDS.items()),
                            s["toc_fold"] if s["toc_fold"] in pages.TOC_FOLDS else "auto",
                            help="Whether subheadings fold under their heading.",
                            cls=FIELD_GAP),
            ToggleField("Number the contents", "toc_numbers", checked=(s["toc_numbers"] == "1"),
                        help="1, 2, 2.1 - handy for guides.", cls=FIELD_GAP),
            ToggleField("A copy-link button beside each heading", "heading_links",
                        checked=(s["heading_links"] == "1"), help="To share a section.", cls=FIELD_GAP),
            RadioGroupField("Fold headings", "heading_fold", list(pages.FOLD_STYLES.items()),
                            s["heading_fold"] if s["heading_fold"] in pages.FOLD_STYLES else "off",
                            help="Readers fold the writing under a heading by selecting it. Sections don't fold."),
            key="posts-contents"
        ),
        SettingsPanel(
            "Reading",
            ToggleField("Use relative dates", "relative_dates", checked=(s["relative_dates"] == "1"),
                         help="“2 days ago” instead of “30 Aug 2026”.", cls=FIELD_GAP),
            ToggleField("Show when a post was updated", "show_updated", checked=(s["show_updated"] == "1"),
                        cls=FIELD_GAP),
            ToggleField("Show a “back to top” button", "scroll_to_top", checked=(s["scroll_to_top"] == "1"),
                         cls=FIELD_GAP),
            ToggleField("Footnotes beside the text", "sidenotes", checked=(s["sidenotes"] == "1"),
                        help="In the margin on a wide screen, at the end on a phone.", cls=FIELD_GAP),
            ToggleField("Open links to other sites in a new tab", "links_new_tab",
                        checked=(s["links_new_tab"] == "1"), cls=FIELD_GAP),
            RadioGroupField("Reader reactions", "reactions_style", reactions.STYLES,
                            s["reactions_style"] if s["reactions_style"] in dict(reactions.STYLES) else "like",
                            cls=FIELD_GAP),
            FormField("Emoji offered", Div(
                *[Label(Input(type="checkbox", name="reaction_emojis", value=key, cls="checkbox checkbox-xs",
                              checked=key in reactions.enabled_keys(s["reaction_emojis"])),
                        Span(emoji, cls="text-base"), Span(label, cls="text-xs text-base-content/70"),
                        cls="flex items-center gap-1.5 cursor-pointer")
                  for key, (emoji, label) in reactions.CHOICES.items()],
                cls="grid grid-cols-2 sm:grid-cols-3 gap-2"),
                ),
            key="posts-reading"
        ),
        SettingsPanel(
            "Each post shows",
            FormField("Around the text", Div(
                *[Label(Input(type="checkbox", name="post_shows", value=key, cls="checkbox checkbox-xs",
                              checked=key in pages.default_extras(False)),
                        Span(label, cls="text-sm"), cls="flex items-center gap-2 cursor-pointer")
                  for key, label in pages.EXTRAS.items()],
                cls="grid grid-cols-1 sm:grid-cols-2 gap-2"),
                help="Each post or page can choose its own."),
            key="posts-shows"
        ),
        SettingsPanel(
            "Milestones sections",
            RadioGroupField("Line in Milestones sections", "milestones_align", list(TIMELINE_ALIGNS.items()),
                            s["milestones_align"] if s["milestones_align"] in TIMELINE_ALIGNS else "left",
                            ),
            key="posts-milestones"
        ),
    ]


def _motion_panel(s):
    """Movement and effects."""
    return SettingsPanel(
        "Motion",
        ToggleField("Animations", "page_animations", checked=(s["page_animations"] == "1"),
                    help="Pages fade in, panels slide, sections fold - never for readers who've asked "
                         "their device for less motion.", cls=FIELD_GAP),
        RadioGroupField("Sections appear", "section_motion", list(pages.SECTION_MOTIONS.items()),
                        s["section_motion"] if s["section_motion"] in pages.SECTION_MOTIONS else "fade",
                        help="As each part of a landing page scrolls into view.", cls=FIELD_GAP),
        ToggleField("Smooth scrolling", "smooth_scroll", checked=(s["smooth_scroll"] == "1")),
        key="style-motion"
    )


def _footer_panel(s):
    """The footer."""
    return SettingsPanel(
        "Footer",
        ToggleField("Show the footer", "footer_enabled", checked=(s["footer_enabled"] == "1"),
                     cls=FIELD_GAP),
        RadioGroupField(
            "Footer position", "footer_style", list(FOOTER_POSITIONS.items()),
            selected=s["footer_style"] if s["footer_style"] in ("fixed", "floating") else "inline",
            cls=FIELD_GAP
        ),
        RadioGroupField("Layout", "footer_layout", list(FOOTER_LAYOUTS.items()),
                        s["footer_layout"] if s["footer_layout"] in FOOTER_LAYOUTS else "center",
                        help="For columns, put pages under a footer page, in each one's Post settings.",
                        cls=FIELD_GAP),
        FormField(
            "What to show",
            SortableList("footer_order", [(key, {
                # the split's line between left and right - only
                # there while Split is chosen (data-shown-for)
                FOOTER_SPLIT: Div(P("Right side", cls="text-sm font-semibold"),
                                  P("What's below this goes on the right", cls="text-xs text-base-content/60")),
                "bio": ToggleField("Author bio", "footer_show_bio", checked=(s["footer_show_bio"] == "1")),
                "socials": ToggleField("Social links", "footer_show_socials",
                                       checked=(s["footer_show_socials"] == "1")),
                "links": ToggleField("Pinned pages", "footer_show_pages",
                                     checked=(s["footer_show_pages"] == "1")),
                "note": ToggleField("Footer note / copyright", "footer_show_note",
                                    checked=(s["footer_show_note"] == "1")),
                "small": Div(
                    ToggleField("Archive, Tags and RSS links", "footer_show_browse",
                                checked=(s["footer_show_browse"] == "1"), cls="mb-2"),
                    ToggleField("“Powered by Soloblog”", "footer_show_powered_by",
                                checked=(s["footer_show_powered_by"] == "1"),
                                ),
                ),
            }[key], {"data_shown_for": "footer_layout=split", "hidden": s["footer_layout"] != "split"}
              if key == FOOTER_SPLIT else {}) for key in footer_order(s)]),
            help="Drag to reorder.", cls=FIELD_GAP
        ),
        FormField(
            "Footer note",
            Input(name="footer_note", value=s["footer_note"], placeholder=f"© {s['site_title']}",
                  cls="input input-sm w-full"),
            help=f"Empty: “© {s['site_title']}”."
        ),
        key="header-footer"
    )


def _design_form(s):
    return Form(
        Div(
            *_look_panels(s), *_header_panels(s), *_blog_panels(s), *_post_panels(s),
            _motion_panel(s), _footer_panel(s),
            cls=f"flex flex-col gap-3 {SECTION_GAP}"
        ),

        SaveBar(),
        hx_post="/admin/settings/style", hx_target="#save-status", hx_swap="outerHTML show:none focus-scroll:false",
        data_declare_fields=True
    )


@ar.get("/admin/presets/preview/{key}")
def preview_preset(session, key: str):
    """The site in a preset, nothing saved (app.PresetPreview) - until
    Stop previewing, or the browser closes."""
    from soloblog import presets
    from soloblog.app import PresetPreview
    if not presets.find(key):
        return _toast_redirect("/admin/settings?tab=style", "That preset doesn't exist", "error")
    r = RedirectResponse("/", status_code=303)
    r.set_cookie(PresetPreview.COOKIE, key, httponly=True, samesite="lax", path="/",
                 secure=config.BASE_URL.startswith("https://"))
    return r


@ar.post("/admin/presets/stop")
def stop_preview(session):
    from soloblog.app import PresetPreview
    r = RedirectResponse("/admin/settings?tab=style", status_code=303)
    r.delete_cookie(PresetPreview.COOKIE, path="/")
    return r


@ar.post("/admin/presets/apply")
def apply_preset(session, key: str = "", page: str = "", page_from: str = ""):
    from soloblog import presets
    from soloblog.app import PresetPreview
    if not presets.find(key):
        return _toast_redirect("/admin/settings?tab=style", "That preset doesn't exist", "error")
    made = presets.apply(key, "" if page_from == "new" else page)["made"]
    name = presets.find(key)[0]
    message = f"Now using {name}" + (" - with a new page as your homepage" if made else "")
    # no Undo here: the panel's own Undo it, at its foot, says what it puts back
    r = status_redirect("/admin/settings?tab=style", message)
    r.delete_cookie(PresetPreview.COOKIE, path="/")
    return r


@ar.post("/admin/themes/preview")
def preview_own_theme(css: str = ""):
    """The pasted theme on a sample, as you paste it (OwnThemeDialog)."""
    theme, problem = parse_theme(css)
    if not theme:
        return P(problem if css.strip() else "A preview shows here once you paste.",
                 cls=f"text-sm {'text-error' if css.strip() else 'text-base-content/60'}")
    return OwnPreview(theme["values"])


@ar.post("/admin/themes/save")
def save_own_theme(key: str = "", css: str = "", name: str = ""):
    existing = next((t for t in own_themes() if t["key"] == key), None)
    theme, problem = parse_theme(css)
    name = re.sub(r"[^\w '-]+", "", name).strip()[:40]
    if not theme:
        return OwnThemeDialog(existing, error=problem, pasted=css, name=name)
    if not save_own(theme, name, existing["key"] if existing else ""):
        return OwnThemeDialog(None, error=f"That's {OWN_LIMIT} already - delete one to add another.", pasted=css,
                              name=name)
    # the palettes and the page's own CSS change with it: the page again, at Colours
    return Response("", headers={"HX-Redirect": "/admin/settings?tab=style&panel=style-colours"})


@ar.post("/admin/themes/delete")
def delete_own_theme(key: str = ""):
    delete_own(key)
    return RedirectResponse("/admin/settings?tab=style&panel=style-colours", status_code=303)


@ar.post("/admin/presets/save-custom")
def save_custom_preset(session):
    from soloblog import presets
    presets.save_custom()
    return _toast_redirect("/admin/settings?tab=style", "Saved as Custom")


@ar.post("/admin/presets/undo")
def undo_preset(session):
    from soloblog import presets
    if not presets.undo():
        return _toast_redirect("/admin/settings?tab=style", "Nothing to undo", "error")
    return _toast_redirect("/admin/settings?tab=style", "Put back as it was")


# Settings > Appearance > Posts per page: numbers that fill rows of 2 and 3
PER_PAGE = (6, 9, 12, 18, 24, 48)







# ---- the Design pages' live preview (DesignPreview, DESIGN_PREVIEW_JS):
# the page's form, as it stands, shown on the site beside it - nothing
# saved. Each change is kept here a few minutes under a token the preview
# frame's address carries; app.PresetPreview applies it, for the admin.

DESIGN_TABS = ("style", "blog", "posts", "header", "banner")
_previews = {}


def design_preview_values(token):
    """The settings a preview frame shows, or None once it's gone."""
    import time
    found = _previews.get(token or "")
    return found[1] if found and found[0] > time.time() else None


@ar.post("/admin/design/preview")
async def design_preview(session, request):
    import secrets
    import time
    form = await request.form()
    # cleaned as a save would be - only what this page's form sends
    values = clean_form(form, DESIGN_FIELDS)
    now = time.time()
    for t in [t for t, (until, _) in _previews.items() if until < now] + list(_previews)[:-100]:
        _previews.pop(t, None)
    token = secrets.token_urlsafe(12)
    _previews[token] = (now + 600, {**values, "_design_preview": "1"})
    return JSONResponse({"token": token})


# the Design view, full screen (DesignPreview, DESIGN_PREVIEW_JS): the
# page's settings down the left, the preview filling the rest
# each class spelled out whole - Tailwind only builds what it can read
DESIGN_BODY = ("[html[data-design-open]_&]:fixed [html[data-design-open]_&]:inset-y-0 "
               "[html[data-design-open]_&]:left-0 [html[data-design-open]_&]:w-[min(30rem,40vw)] "
               "[html[data-design-open]_&]:z-[60] [html[data-design-open]_&]:overflow-y-auto "
               "[html[data-design-open]_&]:overflow-x-hidden "
               "[html[data-design-open]_&]:overscroll-contain [html[data-design-open]_&]:bg-base-200 "
               "[html[data-design-open]_&]:p-4 [html[data-design-open]_&]:border-r "
               "[html[data-design-open]_&]:border-base-300")


def DesignPreview(tab):
    """A Design page's preview, full screen beside its settings (Ghost's
    design view): the homepage, a post or a page, at a computer's width
    or a phone's. Hidden until Preview (DesignPreviewButton) opens it;
    the frame loads only then."""
    from soloblog.ui import EXTERNAL_SVG
    latest = next(iter(posts.list_roll(1, 1)), None)
    page = next((p for p in posts.list_pinned_by_location("header") if posts.is_live(p)), None)
    places = [("/", "Homepage")] + ([(posts.url_for(latest), "A post")] if latest else []) \
        + ([(posts.url_for(page), "A page")] if page else [])
    start = places[1][0] if tab == "posts" and latest else "/"
    # the admin's own sizes (sm, admin-scale): a size below, they read as another app's
    device = lambda key, label: Button(label, type="button", data_preview_device=key,  # noqa: E731
                                       aria_pressed="true" if key == "desktop" else "false",
                                       cls="btn btn-sm join-item aria-pressed:btn-active")
    return Div(
        Div(Select(*[Option(label, value=path, selected=path == start) for path, label in places],
                   aria_label="What to preview", data_preview_path=True, cls="select select-sm w-auto"),
            Div(device("desktop", "Computer"), device("phone", "Phone"), cls="join"),
            Button(EXTERNAL_SVG, Span("Open", cls="ml-1"), type="button", data_preview_open=True,
                   cls="btn btn-sm btn-ghost ml-auto"),
            Button(X_SVG, Span("Close", cls="ml-1"), type="button", data_preview_close=True, cls="btn btn-sm"),
            cls="flex items-center gap-2"),
        Div(Iframe(title="Preview of your site", data_preview_frame=True,
                   cls="absolute top-0 left-0 border-0 origin-top-left bg-base-100"),
            data_preview_box=True,
            cls="relative flex-1 overflow-hidden rounded-box border border-base-300 bg-base-100"),
        data_design_preview=True, role="region", aria_label="Preview",
        # the page's own shade, as the rest of the admin - the settings beside
        # it have the line between them (DESIGN_BODY)
        cls="hidden [html[data-design-open]_&]:flex flex-col gap-3 fixed inset-y-0 right-0 left-[min(30rem,40vw)] "
            "z-[60] p-4 bg-base-200"
    )


def DesignPreviewButton(tab):
    """Opens the preview - full screen beside the settings, or in a tab
    on a screen without room for both. In the full-screen view, the Design
    pages head the settings as tabs, so you can move between them with
    the preview still open (it reopens on the next page)."""
    from soloblog.ui import EYE_SVG
    return Div(
        Div(Tabs(*[A(dict(TABS)[key], href=f"/admin/settings?tab={key}",
                     aria_current="page" if key == tab else None,
                     cls=f"tab tab-sm whitespace-nowrap shrink-0 {'tab-active font-semibold' if key == tab else ''}")
                   for key in DESIGN_TABS], id="design-tabs", cls=TABS_CLS),
            cls="hidden [html[data-design-open]_&]:block mb-3"),
        Div(Button(EYE_SVG, Span("Preview mode", cls="ml-1"), type="button", data_preview_show=True, cls="btn btn-sm"),
            cls="flex justify-end mb-3 [html[data-design-open]_&]:hidden"))
