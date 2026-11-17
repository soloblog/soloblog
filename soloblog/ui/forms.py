"""A settings page's parts: panels, fields, switches, pickers of one value."""
from fasthtml.common import *
from soloblog import i18n
from soloblog.actions import on, EL
from soloblog import settings
from soloblog.ui.icons import CHEVRON_DOWN_SVG, CHEVRON_UP_SVG, RESTORE_SVG
from soloblog.ui.base import FIELD_GAP, MenuLabel, RowActions, SCROLLS, SearchBox, glass_fill


def SetUpFirst(what, href, cls="text-sm"):
    """What has to be set up before a setting works, as a link straight
    there - shown only while it isn't (docs/DEVELOPMENT.md > Writing and
    settings: no directions around the admin)."""
    # one child - an alert lays each of its children out as a column
    return Div(Span(A(f"Set up {what}", href=href, cls="link font-medium"), " first."),
               cls=f"alert alert-warning {cls} mb-3")


EMAIL_SETUP = "/admin/settings?tab=email"


def OffNotice(text, href, link="Turn it on"):
    """A list page whose feature is off: what that means, and a link that
    turns it on - like SetUpFirst, never directions around the admin."""
    return Div(Span(f"{text}. ", A(link, href=href, cls="link font-medium")), cls="alert alert-warning text-sm mb-4")


def EnglishSelect(s):
    """American, British or Australian spelling - Settings and the welcome."""
    return Select(*[Option(label, value=code, selected=(code == s.get("english_spelling")))
                    for code, label in i18n.ENGLISH.items()],
                  name="english_spelling", cls="select select-sm w-full")


def EmailFields(name, value, help=None):
    """An email address typed twice. The second has to match - as it's
    typed (data-must-match, app.js), and again when it's saved - so one
    slip of a key can't send password resets somewhere else."""
    return Div(
        FormField("Email address", Input(type="email", name=name, id=name, value=value, autocomplete="email", maxlength="254",
                                      placeholder="you@example.com", cls="input input-sm w-full"),
                  cls=FIELD_GAP),
        FormField("Type it again", Input(type="email", name=f"{name}_confirm", value=value, autocomplete="off",
                                         maxlength="254", aria_label="Email address, again", data_must_match=name,
                                         data_mismatch="The email addresses don't match",
                                         cls="input input-sm w-full"),
                  help=help),
    )


def Combobox(name, options, selected, label, search="Type to find…", field=None, tags=None, prefix=None):
    """A long list to choose from by typing (docs/DEVELOPMENT.md > Writing
    and settings: past about a dozen choices) - a box that looks like a
    select, opening a list with a search at its top. options: (value,
    text, group or None[, style]), in order; a group's name is searched
    too, and a style shows the choice as it'll look (a font).
    pickCombo / filterCombo, app.py. The value is a text field, hidden,
    so the unsaved-changes check sees it change. field: that field's own
    attributes, in place of saving as it changes - with form=, its search
    is outside that form too;
    tags: {value: a word shown beside it}; prefix: the label shown in the
    box, before the choice, as a select's own label is."""
    chosen = next((o for o in options if o[0] == selected), (selected, selected, None))
    rows, last = [], None
    for value, text, group, *style in options:
        if group and group != last:
            rows.append(Li(group, cls="menu-title", data_combo_group=group))
            last = group
        tag = (tags or {}).get(value) or ("Default" if value == settings.DEFAULTS.get(name) else "")
        rows.append(Li(Button(text, Span(tag, cls=DEFAULT_TAG) if tag else None,
                              type="button", data_value=value, data_label=text,
                              style=style[0] if style else None,
                              aria_selected="true" if value == selected else "false",
                              cls="menu-active" if value == selected else None),
                       data_combo_item=f"{text} {tag + ' ' if tag else ''}{group or ''} {value}".lower()))
    glass = glass_fill(settings.get_all())
    return Div(
        Input(type="text", hidden=True, name=name, id=name, value=selected, **(field or {"data_autosave": True})),
        Button(Span(prefix, cls="label") if prefix else Span(f"{label}, ", cls="sr-only"),
               Span(chosen[1], id=f"{name}-label", cls="truncate min-w-0",
                    style=chosen[3] if len(chosen) > 3 else None),
               type="button", popovertarget=f"{name}-combo", aria_haspopup="listbox",
               cls="select select-sm w-full max-w-full min-w-0 text-left font-normal"),
        Div(SearchBox("w-full mb-1 shrink-0", placeholder=search, aria_label=search, autocomplete="off",
                      **({"form": field["form"]} if field and "form" in field else {}),
                      **on("input", "filterCombo", EL)),
            # squeezed above a phone's keyboard, the list gives way, not the search
            Ul(*rows, role="listbox", data_scroll_hint=True,
               cls=f"menu menu-sm w-full max-h-64 min-h-0 flex-1 overflow-y-auto flex-nowrap p-0 {SCROLLS}"),
            popover="auto", id=f"{name}-combo", data_combo=name,
            cls=f"dropdown-content [&:popover-open]:flex flex-col rounded-box border border-base-300 {glass} shadow-lg p-2 w-72 "
                "max-w-[calc(100vw-2rem)]"),
        cls="w-full min-w-0"
    )


def FontCombobox(name, selected, label):
    """A font, each shown in itself (fonts.py), found by typing a name."""
    from soloblog import fonts
    options = [("", "Default", None)] + [(k, fonts.STACKS[k][0], group, f"font-family: {fonts.STACKS[k][1]}")
                                         for group, keys in fonts.GROUPS for k in keys]
    return Combobox(name, options, selected or "", label, search="Type a font…")


def TimezoneCombobox(selected: str):
    """Every time zone, found by typing a place or region - "Oslo",
    "Europe"."""
    from soloblog import tz
    options = [("UTC", "UTC", None)]
    for zone in tz.zone_names():
        region, _, place = zone.partition("/")
        if place:
            options.append((zone, place.replace("_", " ").replace("/", " - "), region))
    return Combobox("timezone", options, selected or "UTC", "Time zone", search="Type a city or region…")


def SecretInput(name, saved, placeholder="", **attrs):
    """A key, password or token. What's saved never goes back to the page -
    anyone looking at it, or its source, would read it: the box says it's
    saved, left empty it stays (admin_settings.secret), and a tick removes it."""
    box = Input(type="password", name=name, value="", autocomplete="new-password", spellcheck="false",
                placeholder="Saved - type a new one to replace it" if saved else placeholder, **attrs)
    if not saved:
        return box
    return Div(box,
               # waits for Save with the rest, not saved the moment it's ticked
               Label(Input(type="checkbox", name=f"{name}__remove", value="1", cls="checkbox checkbox-xs"),
                     Span("Remove the saved one", cls="text-xs"), data_autosave_off="1",
                     cls="flex items-center gap-1.5 mt-1.5 w-fit cursor-pointer"),
               cls="min-w-0")


def FormField(label, *content, help=None, cls="", custom=None):
    """v5's replacement for a standalone .label caption above a field -
    daisyUI dropped form-control/label-text in favor of fieldset+legend,
    and v5's own .label is now inline-flex + nowrap (meant for a label
    sitting next to a checkbox, not a full-width heading above an
    input), so the old Div(Label(...), input) pattern would no longer
    sit on its own line or wrap a long caption. custom: None for a
    setting the site doesn't have; otherwise whether this post sets it
    differently now - a bar on its left edge (CHANGED_BAR) and a Reset
    button (ResetButton) on the label's line."""
    label, help = i18n.spell(label), i18n.spell(help)
    # a legend names the group, not the field in it - screen readers need
    # the field itself named, and the help read with it
    key = f"ff-{next(_field_ids)}"
    fields = [c for c in _descendants(content) if getattr(c, "tag", "") in ("input", "select", "textarea")
              and c.attrs.get("type") not in ("hidden", "checkbox", "radio")]
    if len(fields) == 1 and not ({"aria-label", "aria-labelledby"} & set(fields[0].attrs)):
        fields[0].attrs["aria-labelledby"] = f"{key}-l"
        if help:
            fields[0].attrs.setdefault("aria-describedby", f"{key}-h")
    return Fieldset(
        # the label whole; Reset to the right - on the next line only if there's no room
        Legend(Span(Span(label, id=f"{key}-l", cls="shrink-0"), ResetButton(custom),
                    cls="flex flex-wrap items-center gap-x-1.5 gap-y-0.5 w-full min-w-0"), cls="fieldset-legend w-full")
        if custom is not None else Legend(label, id=f"{key}-l", cls="fieldset-legend"),
        *content,
        P(help, id=f"{key}-h", cls="fieldset-label") if help else None,
        # a fieldset is as wide as its content by default - a long choice
        # (a Combobox) would push it off a phone's screen
        **_changed_attrs(custom),
        cls=f"{CHANGED_BAR if custom is not None else 'p-0'} fieldset min-w-0 {cls}"
    )


_field_ids = __import__("itertools").count(1)


def _descendants(items):
    for c in items:
        if hasattr(c, "tag"):
            yield c
            yield from _descendants(c.children)


def ToggleField(label, name, checked, help=None, cls="", custom=None, site=None):
    """An on/off setting the way settings pages usually show one: its
    name, with a short description under it, on the left and a switch
    on the right - so every switch on a page lines up in one column.
    The whole row is the click target. Checkboxes stay for picking
    several things from a list (emoji, toolbar buttons, rows). custom:
    None for a setting the site doesn't have; otherwise whether this post
    sets the switch differently now - a bar on the left edge and Reset, an
    icon before the switch, on the same line. site: "1" or "0", what the
    site does - what the bar compares with. (On the settings pages,
    SettingsForm gives a switch its bar and Reset, against the starting
    style.)"""
    label, help = i18n.spell(label), i18n.spell(help)
    words = Span(Span(label, cls="block text-sm font-medium"),
                 Span(help, cls="block text-xs text-base-content/60 mt-0.5") if help else None,
                 cls="flex-1 min-w-0")
    switch = Input(type="checkbox", name=name, value="1", checked=checked, data_site_value=site,
                   cls="toggle toggle-sm shrink-0 mt-0.5")
    if custom is None:
        row = Label(words, switch, cls="flex items-start justify-between gap-4 cursor-pointer")
        return Fieldset(row, cls=f"fieldset p-0 {cls}")
    # the words and the switch are one click target; Reset sits between,
    # outside them, where pressing it can't turn the switch
    key = f"tf-{name}"
    switch.attrs["id"] = key
    row = Div(Label(words, fr=key, cls="flex-1 min-w-0 cursor-pointer"),
              # Reset right beside the switch, the two on one line
              Div(ResetButton(custom, default_label="On" if site == "1" else "Off"),
                  Label(switch, fr=key, cls="flex cursor-pointer"), cls="flex items-center gap-1 shrink-0 min-h-6"),
              cls="flex items-start justify-between gap-3")
    return Fieldset(row, **_changed_attrs(custom), cls=f"{CHANGED_BAR} fieldset {cls}")


def SortMoves(id):
    """A sortable row's Move up and Move down - on a phone behind the
    row's ⋯ menu, with their words: two 44 px buttons beside a switch left
    its name a word a line. Settings > Editor > Toolbar order's rows, made
    by TOOLBAR_ORDER_JS, use the same (its __ID__ replaced)."""
    return RowActions(Button(CHEVRON_UP_SVG, MenuLabel("Move up"), type="button", data_sort_move="up",
                             aria_label="Move up", cls="btn btn-xs btn-square btn-ghost"),
                      Button(CHEVRON_DOWN_SVG, MenuLabel("Move down"), type="button", data_sort_move="down",
                             aria_label="Move down", cls="btn btn-xs btn-square btn-ghost"),
                      id=id)


def SortableList(name, rows):
    """Rows put in order by dragging their handle, or with their arrow
    buttons from the keyboard. rows: (key, content) or (key, content, attrs). The order goes with
    the form as `name`, a comma list of keys - a hidden text field, so
    the unsaved-changes warning and Discard both see it (SORTABLE_JS)."""
    rows = [(r[0], r[1], r[2] if len(r) > 2 else {}) for r in rows]
    keys = [k for k, _, _ in rows]
    return Div(
        Input(type="text", name=name, value=",".join(keys), hidden=True, data_sort_order=True),
        Ul(*[Li(
            # under 360 px its ⋯ menu moves it - the handle's room is the name's
            Span("\u22ee\u22ee", data_sort_handle=True, aria_hidden="true", data_tip="Drag to reorder",
                 cls="tooltip cursor-move opacity-40 select-none text-xs px-2 py-1.5 -my-1 touch-none max-[359px]:hidden"),
            Div(content, cls="flex-1 min-w-0"),
            SortMoves(f"sort-{name}-{key}"),
            data_key=key, cls="flex items-center gap-2 p-2 rounded-box bg-base-100 border border-base-300", **attrs
        ) for key, content, attrs in rows], data_sortable=True, cls="flex flex-col gap-1")
    )


DEFAULT_TAG = "badge badge-ghost badge-xs shrink-0"
# a Post setting this page sets differently from the site (CUSTOM_TAGS_JS)
# gets a thin bar on its left edge: the border is always there, clear, so
# nothing moves when it shows, and the negative margin keeps the text in line
CHANGED_BAR = "border-s-2 border-transparent data-[changed]:border-accent py-0 pe-0 ps-2 -ms-2.5"


def _changed_attrs(changed):
    """A tracked setting's wrapper: what CUSTOM_TAGS_JS looks for, and
    what the bar follows."""
    if changed is None:
        return {}
    return {"data_custom_field": True, **({"data_changed": True} if changed else {})}


def ResetButton(shown=False, cls="", default_label=""):
    """Reset: an icon beside a changed setting (VS Code's way) that puts it
    back to the default - in Post settings following the site again (a
    choice empties, so it keeps following later changes), on the settings
    pages the starting style's value. Shown only while the setting differs;
    the bar beside it says so too. default_label: what the default is, for
    its tooltip ("On")."""
    tip = f"Reset to default ({default_label})" if default_label else "Reset to default"
    return Button(RESTORE_SVG, type="button", data_custom_reset=True, data_tip=tip, aria_label=tip,
                  **on("click", "customReset", EL),
                  cls=f"btn btn-ghost btn-xs btn-square tooltip tooltip-left ms-auto shrink-0 font-normal {cls}"
                      f"{'' if shown else ' hidden'}".replace("  ", " "))


_FROM_SETTINGS = object()


def RadioGroupField(label, name, options, selected, help=None, cls="", default=_FROM_SETTINGS):
    label, help = i18n.spell(label), i18n.spell(help)
    options = [(value, i18n.spell(text)) for value, text in options]
    # the choice a new site starts with is tagged Default - the setting's
    # own default (settings.DEFAULTS), unless the caller says otherwise
    if default is _FROM_SETTINGS:
        default = settings.DEFAULTS.get(name)
    """A radio-button choice, same fieldset/legend/help grammar as
    FormField and ToggleField - options is a list of (value, label)
    pairs. Replaces what used to be a bare, unlabeled stack of radio
    rows with no fieldset/legend of its own at all (the "choice" itself
    had no title, only its individual options did) - every other kind
    of setting on this page names what it's a choice *of* before
    listing the choices; radio groups are the one control type that
    hadn't been doing that."""
    return Fieldset(
        Legend(label, cls="fieldset-legend"),
        *[Label(Input(type="radio", name=name, value=value, checked=(value == selected), cls="radio radio-sm"),
                # whitespace-normal - .label never wraps, and a long option ran off a phone screen
                opt_label, Span("Default", cls=DEFAULT_TAG) if value == default else None,
                cls="label w-full cursor-pointer justify-start gap-2 py-1 whitespace-normal")
          for value, opt_label in options],
        P(help, cls="fieldset-label") if help else None,
        cls=f"fieldset p-0 {cls}"
    )


def PictureChoiceField(label, name, options, selected, help=None, cls="", default=_FROM_SETTINGS):
    """A choice shown as small pictures, like the blog roll picker: options
    are (value, label, thumb) - a pages.THUMBS key. Real radios
    underneath, so saving and what shows for each choice work as with
    RadioGroupField."""
    from soloblog import pages
    if default is _FROM_SETTINGS:
        default = settings.DEFAULTS.get(name)
    return Fieldset(
        Legend(i18n.spell(label), cls="fieldset-legend"),
        Div(*[Label(Input(type="radio", name=name, value=value, checked=(value == selected), cls="peer sr-only"),
                    # a border that's always there, coloured when chosen - a ring outside
                    # made the chosen picture look bigger than the rest
                    Div(pages.thumb(picture),
                        cls="rounded-field border-2 border-transparent p-0.5 peer-checked:border-primary "
                            "peer-focus-visible:border-primary"),
                    Div(Span(i18n.spell(text)), Span("Default", cls=DEFAULT_TAG) if value == default else None,
                        cls="flex flex-wrap items-center justify-center gap-1 text-xs text-center "
                            "peer-checked:font-semibold"),
                    cls="flex flex-col gap-1.5 cursor-pointer min-w-0")
              for value, text, picture in options],
            cls="grid grid-cols-2 sm:grid-cols-3 gap-3"),
        P(i18n.spell(help), cls="fieldset-label") if help else None,
        cls=f"fieldset p-0 min-w-0 {cls}"
    )
