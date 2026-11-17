"""What every Settings file shares: the router, the page's menu and the colour pickers."""
import logging
import re
from fasthtml.common import *
from soloblog import js
from soloblog import settings
from soloblog.actions import on
from soloblog.themes import THEME_MODES, THEME_PAIRS, dark_choices, light_choices, theme_choice, theme_label
from soloblog.ui import DEFAULT_TAG
from soloblog.ui import FIELD_GAP, FormField, RadioGroupField
from soloblog.guards import status_redirect
from soloblog.ui import SETTINGS_GROUPS as PAGE_GROUPS, PageNav

log = logging.getLogger(__name__)

ar = APIRouter()

# a verification code is dropped into a <meta> tag - only its own shape is kept
VERIFICATION_RE = re.compile(r"^[A-Za-z0-9_=-]{0,120}$")

# drives Settings > Editor > Toolbar order (#toolbar-order-list): a
# drag-to-reorder list per section of only the currently-ticked buttons
# (plus Insert, always on - see editor_config.py), kept in step with the
# checkboxes above it and joined into one hidden input
# (#editor-toolbar-input) on every change. That input's csv is the single
# value the form submits - which buttons are on and their order.
TOOLBAR_ORDER_JS = js.read("toolbar_order.js")


ANALYTICS_PROVIDERS = ("cloudflare", "plausible", "google")
ANALYTICS_ID_RE = re.compile(r"^[A-Za-z0-9._-]{0,80}$")


def _toast_redirect(path: str, message: str, kind: str = "success"):
    return status_redirect(path, message, kind)


def SettingsNav(tab):
    """The settings pages where the admin menu isn't beside the page: the
    same grouped menu as Help's (ui.PageNav)."""
    return PageNav(PAGE_GROUPS, tab, "/admin/settings", "settings-nav", "Settings pages")


def ThemeSwatch(name, selected, field="theme", label=None):
    """label - a theme of your own goes by the name you gave it."""
    is_selected = name == selected
    return Label(
        Input(type="radio", name=field, value=name, checked=is_selected, cls="hidden peer"),
        Div(
            Div(
                Div(cls="w-3 h-3 rounded-full bg-primary"),
                Div(cls="w-3 h-3 rounded-full bg-secondary"),
                Div(cls="w-3 h-3 rounded-full bg-accent"),
                cls="flex gap-1"
            ),
            Div("✓", cls="absolute top-1 right-1 w-3.5 h-3.5 rounded-full bg-primary text-primary-content "
                          "text-[10px] flex items-center justify-center opacity-0 peer-checked:opacity-100"),
            data_theme=name,
            # rounded-field/border-[length:var(--border)] instead of a
            # fixed rounded-lg/border-2 - follows the *previewed* theme's
            # own tokens (data-theme is set right here on this element)
            # rather than a hardcoded shape that only fits some themes
            cls="relative flex gap-1 p-1.5 rounded-field border-[length:var(--border)] border-base-300 bg-base-100 "
                "peer-checked:border-primary peer-checked:ring-2 peer-checked:ring-primary "
                "peer-checked:ring-offset-2 peer-checked:ring-offset-base-100 transition-all"
        ),
        Div(label or name, cls=f"text-[11px] text-center mt-1 truncate {'font-semibold' if is_selected else ''}"),
        # the palette a new site starts with
        Div(Span("Default", cls=DEFAULT_TAG), cls="flex justify-center mt-0.5")
        if settings.DEFAULTS.get(field) == name else None,
        # data-set-theme is theme-change's own trigger attribute - clicking
        # this label previews that theme on the whole page immediately,
        # on top of (not instead of) the native label-click-checks-radio
        # behavior the actual form submission still relies on
        # data-key isolates this preview to its own localStorage entry,
        # separate from the visitor-facing switcher's - without this
        # they'd share the same "theme" key, and clearing one for
        # cleanup could wipe out a real visitor preference if the
        # admin ever browses their own site in the same browser
        data_set_theme=name, data_key="admin-preview", cls="cursor-pointer"
    )


# Appearance changes the whole page - the theme, the header, the fonts -
# so a save reloads it to show them, where you were, saying "Saved"
DESIGN_PREVIEW_JS = js.read("design_preview.js")

DESIGN_SAVED_JS = js.read("design_saved.js")


def ThemePair(label, light, dark):
    """A light theme and its dark partner, side by side - one click picks
    both (choosePair, app.py)."""
    def half(theme):
        return Div(Div(cls="w-2.5 h-2.5 rounded-full bg-primary"), Div(cls="w-2.5 h-2.5 rounded-full bg-accent"),
                   data_theme=theme, cls="flex gap-1 p-1.5 bg-base-100 flex-1 justify-center")
    return Button(
        Div(half(light), half(dark), cls="flex rounded-field overflow-hidden border-[length:var(--border)] "
                                         "border-base-300 w-full"),
        Span(label, cls="text-[11px] mt-1"),
        type="button", aria_label=f"{label}: {light} and {dark}", data_tip=f"{light} · {dark}",
        cls="tooltip flex flex-col items-center cursor-pointer", **on("click", "choosePair", light, dark)
    )


def ThemePicker(s, modes=True):
    """Settings > Appearance's colour palettes, and the welcome's: matching
    pairs, then a light and a dark palette, each from its own kind, and
    which one visitors see. (daisyUI calls them themes; to a person
    they're colours, on the one design.)"""
    light, dark, mode = theme_choice(s)
    return (
        FormField("Matching pairs", Div(*[ThemePair(*pair) for pair in THEME_PAIRS],
                                        cls="grid grid-cols-4 sm:grid-cols-6 gap-2"),
                  help="A light palette and a dark one that go together, in one click.", cls=FIELD_GAP),
        # custom ones first (Custom colours), then daisyUI's
        FormField("Light palette", Div(*[ThemeSwatch(t, light, label=theme_label(t, s)) for t in light_choices(s)],
                                     cls="grid grid-cols-4 sm:grid-cols-6 gap-2"), cls=FIELD_GAP),
        FormField("Dark palette", Div(*[ThemeSwatch(t, dark, "theme_dark", theme_label(t, s)) for t in dark_choices(s)],
                                    cls="grid grid-cols-4 sm:grid-cols-6 gap-2"),
                  help="Choose a palette to see it on this page.", cls=FIELD_GAP),
        RadioGroupField("Visitors see", "theme_mode", THEME_MODES, mode,
                        cls=FIELD_GAP)
        if modes else Input(type="hidden", name="theme_mode", value=mode),
    )
