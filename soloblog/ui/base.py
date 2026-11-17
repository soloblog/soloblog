"""Spacing, widths and the small parts every area uses."""
import contextvars
from fasthtml.common import *
from soloblog import i18n
from soloblog.actions import on, EL
from soloblog import posts
from soloblog import settings
from soloblog.ui.icons import (
    ARROW_RIGHT_SVG, CHEVRON_DOWN_SVG, DOTS_SVG, EXTERNAL_SVG, PAUSE_SVG, SEARCH_SVG, SPEAKER_SVG, X_SVG,
)

# one set of spacing conventions, reused everywhere instead of picking
# a number per page. if this ever needs to change, it changes in one place.
# kept intentionally tight - a dense, "product" feel over a spacious,
# marketing-page feel.
SECTION_GAP = "mb-6"
FIELD_GAP = "mb-3"
PAGE_PAD = "px-4 py-8"

# The reading column's width (Settings > body_width). There's no full
# width: lines that long are hard to read. WIDE_WIDTH is what "wide"
# things (the banner) reach - the standard column's width, so on a narrow
# column they break out and on a standard one they don't. Components read
# widths through content_width() and WIDE_WIDTH, never these strings.
# The page's own title: a post or page, a page's opening, the wiki,
# Contact - and a list's (the archive, a tag, search, an author)
TITLE_CLS = "text-3xl sm:text-4xl lg:text-5xl font-bold leading-tight"
LIST_TITLE_CLS = "text-2xl sm:text-3xl font-bold leading-tight"
BODY_WIDTHS = {"standard": "max-w-3xl", "narrow": "max-w-2xl"}
WIDE_WIDTH = BODY_WIDTHS["standard"]
# Breakout's "wide": the column and both margins' side panels (Beside,
# 13rem and a 2.5rem gap each) - 48+31 and 42+31
MARGIN_WIDTHS = {"standard": "max-w-[79rem]", "narrow": "max-w-[73rem]"}
# A page that runs wide (pages.is_wide): the same Wide, plus the page's own
# 1rem padding each side, so its content lines up with a wide header,
# cover or banner - three widths in all: Column, Wide, Edge to edge
WIDE_PAGE_WIDTHS = {"standard": "max-w-[81rem]", "narrow": "max-w-[75rem]"}


def content_width(settings) -> str:
    return BODY_WIDTHS.get(settings.get("body_width"), BODY_WIDTHS["standard"])


def Breakout(content, width, settings):
    """Something wider than the reading column (the homepage banner, a
    post's cover): "wide" out to the side panels' outer edges, "full"
    edge to edge, "column" (pages.COVER_WIDTHS) left as it is. The
    100vw-and-negative-margin breakout - it has to sit in the centred
    column, and above the side panels, which start where the column's
    `relative` box does."""
    if width == "full":
        return Div(content, cls="w-screen mx-[calc(50%-50vw)]")
    if width == "wide":
        margins = MARGIN_WIDTHS.get(settings.get("body_width"), MARGIN_WIDTHS["standard"])
        return Div(Div(content, cls=f"{margins} mx-auto"), cls="w-screen mx-[calc(50%-50vw)] px-4")
    return content


def SoundButton(url):
    """A post's or page's background sound (Post settings > Page): a
    round button at the bottom right, under Back to top and like it - never
    playing until it's pressed (browsers wouldn't let it, and a reader
    must be able to stop it). toggleSound, app.py."""
    play, stop = i18n.t("Play the background sound"), i18n.t("Stop the background sound")
    return Div(
        Audio(src=url, loop=True, preload="none", id="background-sound"),
        Button(Span(SPEAKER_SVG, data_sound_off=True), Span(PAUSE_SVG, data_sound_on=True, cls="hidden"),
               type="button", aria_label=play, aria_pressed="false", data_tip=play, data_play=play, data_stop=stop,
               cls="btn btn-neutral btn-circle btn-sm tooltip tooltip-left", **on("click", "toggleSound", EL)),
        id="sound-float", cls="fixed bottom-6 right-6 z-20 print:hidden"
    )


def GoLink(label, href):
    """Somewhere else to go - a link, not a button (docs/DEVELOPMENT.md >
    Buttons): words and an arrow, where a card's buttons would sit."""
    outside = href.startswith("http")
    return A(Span(label), EXTERNAL_SVG if outside else ARROW_RIGHT_SVG, href=href,
             # 44 px tall on a touch screen, as a footer's links are (TOUCH_LINK)
             cls="link link-hover text-sm inline-flex items-center gap-1 pointer-coarse:min-h-11",
             **({"target": "_blank", "rel": "noopener"} if outside else {}))


LOGIN_CLS = "btn btn-ghost btn-sm text-sm"


def LoginButton(settings=None):
    """For a visitor: with the members area on, Sign in - or Your account,
    once they're in (members.py); the admin's own Log in stays at /login,
    linked from the sign-in page. Otherwise Log in."""
    from soloblog import members
    s = settings or {}
    # the menu's own size beside it (14px), not a button's smaller text
    if s.get("members_enabled") == "1" and s.get("members_header") != "0":
        if members.current():
            return A(i18n.t("Your account"), href="/account", cls=LOGIN_CLS)
        return A(i18n.t("Sign in"), href="/signin", cls=LOGIN_CLS)
    return A(i18n.t("Log in"), href="/login", cls=LOGIN_CLS)


# the page being served - set per request (app.apply_site_config), so the
# admin sidebar can mark where you are without any script
_request = contextvars.ContextVar("request_where", default=("", ""))


def set_request(path: str, tab: str = ""):
    _request.set((path, tab))


# A row you swipe along - a phone's toolbar, the bulk bar - fades
# at the side there's more on (data-scroll-x, live.js; the same classes as
# SCROLLS_X there, for the rows scripts make)
SCROLLS_X = ("[scrollbar-width:none] "
             "data-[right]:[mask-image:linear-gradient(to_right,black_calc(100%-1.5rem),transparent)] "
             "data-[left]:[mask-image:linear-gradient(to_left,black_calc(100%-1.5rem),transparent)] "
             # one whole class a line - Tailwind only builds what it reads whole
             "data-[left]:data-[right]:[mask-image:linear-gradient(to_right,transparent,black_1.5rem,black_calc(100%-1.5rem),transparent)]")


# a page's row of tabs, for a few choices (Posts, Comments, Media) - a set
# of many pages (Settings, Help) is a PageNav instead
TABS_CLS = "tabs tabs-border flex-nowrap overflow-x-auto [scrollbar-width:none]"


def Tabs(*tabs, id, cls=TABS_CLS):
    """A row of tabs that always shows them all: where they don't fit
    (a phone), the ones that do stay - the current one always - and the
    rest go under More at the end (fitTabs, app.py), as GitHub and Gmail
    do. Without scripts, the row scrolls sideways instead."""
    return Div(
        *tabs,
        Button("More", CHEVRON_DOWN_SVG, type="button", popovertarget=f"{id}-more", hidden=True, data_tabs_more=True,
               aria_label="More tabs", cls="tab tab-sm gap-1 whitespace-nowrap shrink-0"),
        # a long list (Help's pages) scrolls down inside the screen - a
        # menu's items otherwise wrap into more columns, off to the side
        Ul(id=f"{id}-more", popover="auto", data_scroll_hint=True,
           cls=f"menu menu-sm flex-nowrap dropdown-content dropdown-end w-max max-w-[80vw] max-h-[70vh] overflow-y-auto "
               f"{SCROLLS} [&_a]:whitespace-normal {glass_fill(settings.get_all())} rounded-box z-20 "
               "p-2 shadow border-[length:var(--border)] border-base-200"),
        data_fit_tabs=True, cls=cls
    )


# RowActions' buttons: a join beside the row from sm up; on a phone a
# popover menu (positioned by POPOVER_DROPDOWN_JS, app.py). A popover the
# page forces visible stays in the page's flow - that's the sm: half.
# max-sm:...:hidden because .join's own display beats the browser's
# "a closed popover isn't shown". Its items' look on a phone: input.css.
# on a phone, every item's icon one size, as in any menu - the buttons'
# own icons differ by a pixel or two, which shows once they're stacked
ROW_MENU_CLS = ("join join-vertical m-0 inset-auto p-1 w-max whitespace-nowrap bg-base-100 text-base-content rounded-box "
                "border border-base-300 shadow-lg max-sm:[&:not(:popover-open)]:hidden max-sm:[&_.btn>svg]:size-4 "
                "sm:join-horizontal sm:flex sm:static sm:overflow-visible sm:min-w-0 sm:p-0 sm:bg-transparent "
                "sm:rounded-none sm:border-0 sm:shadow-none")


# the ⋯ at the end of a row with more than three buttons: on a phone its
# buttons are simply more of the row's one menu (contents); from sm up a
# little menu of its own, its items drawn as the phone's are (input.css)
# a column when open, so it's as wide as its longest item - as a block
# its buttons counted side by side, and it came out three times too wide
MORE_MENU_CLS = ("max-sm:contents m-0 inset-auto p-1 w-max whitespace-nowrap bg-base-100 text-base-content rounded-box "
                 "border border-base-300 shadow-lg [&_.btn>svg]:size-4 sm:[&:popover-open]:flex sm:flex-col "
                 "sm:max-h-[70vh] sm:overflow-y-auto sm:[scrollbar-width:thin] "
                 "[&_form:not(.contents)]:w-full [&_.btn]:w-full [&_.btn]:justify-start [&_.btn]:h-[max(2.25rem,var(--size))] "
                 "[&_.btn]:px-3 [&_.btn]:text-[0.875rem] [&_.btn]:font-normal [&_.btn]:bg-transparent [&_.btn]:bg-none "
                 "[&_.btn]:border-transparent [&_.btn]:shadow-none [&_.btn]:rounded-field [&_.btn:hover]:bg-base-200 "
                 "[&_.tooltip]:before:hidden [&_.tooltip]:after:hidden")


def RowActions(*actions, id):
    """A list row's buttons (Posts, Pinned, Trash, Comments, Messages,
    Mentions): in a row beside it where there's room, behind a ⋯ menu
    on a phone - five buttons beside a title left it one word per line.
    More than three, and only the first two stay beside the row: the
    rest are under a ⋯ at their end, at any width - so the two used most
    go first. The same buttons either way, so their forms, Undo and
    are-you-sure dialogs work as they are. An icon-only button needs a
    MenuLabel for the menu."""
    actions = [a for a in actions if a is not None]
    more = actions[2:] if len(actions) > 3 else []
    fold = Div(
        Button(DOTS_SVG, type="button", popovertarget=f"{id}-more", aria_label="More", data_tip="More",
               cls="btn btn-xs join-item tooltip max-sm:hidden"),
        Div(*more, id=f"{id}-more", popover="auto", data_more_menu=True,
            cls=f"{MORE_MENU_CLS} {glass_fill(settings.get_all())}"),
        cls="contents") if more else None
    return Div(
        Button(DOTS_SVG, type="button", popovertarget=id, aria_label="Actions",
               cls="btn btn-ghost btn-sm btn-square sm:hidden"),
        Div(*(actions[:2] if more else actions), fold, id=id, popover="auto", data_row_menu=True,
            cls=f"{ROW_MENU_CLS} {glass_fill(settings.get_all())}"),
        cls="shrink-0"
    )


def MenuLabel(text):
    """An icon-only row button's words - shown in the phone's ⋯ menu,
    and in a row's own ⋯ (RowActions) at any width."""
    return Span(text, cls="ml-1 sm:hidden [[data-more-menu]_&]:inline")


def IconAction(icon, label, href=None, danger=False, confirm=None, menu_label=True, size="xs", tip="", **attrs):
    """A list row's or card's action: an icon, named by a daisyUI tooltip
    (and aria-label), and by its words in a phone's ⋯ menu (RowActions).
    Every list's actions look alike this way - icons, never some with
    words and some without. confirm: asked first (confirmAction, app.py).
    A button with neither href, confirm nor a click action submits its
    form. size: the button's (sm beside other sm buttons); tip: the
    tooltip's side, when not above. menu_label="folded": its words only
    once it's folded into a ⋯ menu (the editor's buttons), at any width."""
    cls = f"btn btn-{size} join-item tooltip {tip}{' text-error' if danger else ''}".replace("  ", " ")
    words = Span(label, cls="hidden [[data-row-menu]_&]:inline ml-1") if menu_label == "folded" else \
        MenuLabel(label) if menu_label else None
    content = (icon, words)
    attrs = {"aria_label": label, "data_tip": label, **attrs}
    if href:
        return A(*content, href=href, cls=cls, **attrs)
    kind = "button" if confirm or "data_onclick" in attrs else "submit"
    return Button(*content, type=attrs.pop("type", kind), data_confirm=confirm, cls=cls, **attrs)


def PageLink(page, cls=None):
    """A pinned page's link in the header or footer. A page with a Link to
    goes straight to the page it points at, in a new tab - how an outside
    link gets into the menu."""
    if posts.is_local_link(page["link_url"]):
        return A(page["title"], href=page["link_url"], cls=cls)
    if page["link_url"]:
        return A(page["title"], EXTERNAL_SVG, Span("(opens in a new tab)", cls="sr-only"),
                 href=page["link_url"], target="_blank", rel="noopener",
                 cls=f"inline-flex items-center gap-1 {cls or ''}")
    return A(page["title"], href=posts.url_for(page), cls=cls)


SITE_ROW_WORDS = {key: page[1] for key, page in posts.SITE_PAGES.items()}
SITE_LABEL_MAX = 40


def site_label(settings, where, key):
    """What a menu calls one of the site's own pages: the owner's own words,
    as typed in every language, or the default word in the visitor's."""
    return (settings.get(posts.site_key(where, key, "label")) or "").strip() or i18n.t(SITE_ROW_WORDS[key])


def SiteLink(settings, where, key, cls=None):
    """A site page's link in the header or footer."""
    return A(site_label(settings, where, key), href=posts.SITE_PAGES[key][0], cls=cls)


# a header menu taller than the room under it scrolls (placeMenu caps its
# height): .menu's own flex-wrap fanned it out into a second column, cut off
MENU_SCROLLS = "flex-nowrap overflow-y-auto [scrollbar-width:thin]"
# the header's icon buttons square on a touch screen - 44 px, as every
# button there is (touch-size, input.css) - in Material's 56 px bar
TOUCH_BTN = "pointer-coarse:btn-square"
TOUCH_BAR = "pointer-coarse:min-h-14 pointer-coarse:py-1"
# the footer's links on a touch screen: 44 px tall (Apple's touch target),
# at 14 px - its 12 px small print was hard to read and to hit
TOUCH_LINK = "inline-flex items-center pointer-coarse:min-h-11 pointer-coarse:text-sm"


def _title_block(settings):
    icon = settings.get("header_icon_url")
    return Div(
        Img(src=icon, cls="h-6 w-6 object-contain rounded shrink-0") if icon else None,
        # a long title shortens with … on a narrow phone instead of
        # pushing the icons off the edge
        A(Span(settings["site_title"], data_site_title=True, cls="truncate"), href="/",
          cls="btn btn-ghost btn-sm pointer-coarse:px-2 text-base min-w-0 max-w-full"),
        cls="flex items-center gap-1 min-w-0"
    )


# a list scrolling inside a box: a thin scrollbar, and a fade at its foot
# while there's more below (data-more, set by SCROLL_HINT_JS) - Firefox
# and macOS hide a scrollbar until the pointer's on it
SCROLLS = "[scrollbar-width:thin] data-[more]:[mask-image:linear-gradient(to_bottom,black_calc(100%-2.5rem),transparent)]"


# A list of results to pick from, the same in every dialog that has one -
# the site's search and the link picker: rows a little apart, each lit as
# a whole on hover or focus, its title in the palette's colour and a line
# about it under that. One link or button per row, so the whole row works.
RESULTS_CLS = f"flex flex-col gap-0.5 max-h-80 min-h-0 overflow-y-auto {SCROLLS}"
# a dialog you search in (site search, the pickers): no taller than what
# you can see (--seen-h, PAGE_HELPERS_JS), so with a phone's keyboard up
# its list shrinks and scrolls while Close stays in sight. On a phone, a
# card floating at the top, centred - not glued to the screen's edges, or
# on the left of one wider than the box (a phone on its side)
SEARCH_DIALOG_BOX = ("modal-box mx-auto flex flex-col overflow-hidden max-h-[calc(var(--seen-h,100dvh)_-_2rem)] "
                     "max-sm:mt-2 max-sm:w-[calc(100%-1rem)] max-sm:rounded-box")
SEARCH_DIALOG_ACTION = "modal-action shrink-0 items-center"


def MoreBelowSlot(id):
    """Where a dialog's list puts "More below" (data-scroll-more=id,
    LIVE_JS): the start of its row, Close at the end - one line, not two."""
    return Span(id=id, cls="me-auto")
RESULT_ROW = ("block w-full text-left px-3 py-2 rounded-field cursor-pointer hover:bg-base-200 "
              "focus-visible:bg-base-200 focus-visible:outline-none")
RESULT_TITLE = "block font-medium text-sm text-primary"
RESULT_ABOUT = "block text-xs text-base-content/60 mt-0.5 line-clamp-2"
RESULT_EMPTY = "text-sm text-base-content/60 text-center py-6"


def glass_fill(settings, base: str = "bg-base-100") -> str:
    """The fill for anything that can be frosted glass (the header,
    footer, drawers, menus, dialogs) - the one place that decides, from
    the one Glass switch. Glass: the base colour see-through, with a
    blur; otherwise plain `base`. Drawers pass base-200, the page's tone.

    The blur is input.css's glass-blur, not Tailwind's backdrop-blur-md:
    Tailwind builds backdrop-filter from eight chained variables, which
    Firefox doesn't always resolve - a single plain value always works."""
    if settings.get("glass_effect") != "1":
        return base
    # glass-fill (input.css): the theme's base colour, see-through
    tone = "[--glass-base:var(--color-base-200)] " if base == "bg-base-200" else ""
    return f"glass-fill {tone}glass-blur [will-change:backdrop-filter]"


def CancelButton(compact=False, label="Discard"):
    """Discard: the form back to what was last saved, in place (the
    browser's form.reset() - no reload, no jump), saying "Discarded"
    where Save says "Saved". discardForm() (app.py) also resets what a
    plain reset() misses: the editor's text and the parent-page field."""
    # compact - label hidden below sm (icon only), for the post editor's
    # action bar where phone width has no room for four labels
    return Button(X_SVG, Span(label, cls="ml-1 hidden sm:inline" if compact else "ml-1"), type="button",
                  **on("click", "discardForm", EL), cls="btn btn-sm", aria_label="Discard unsaved changes" if compact else None)


def SearchBox(cls="w-full", **attrs):
    """Every search field: the magnifier, the box, and a button that
    clears it once there's something typed - the same in every browser
    (Firefox has no clear button of its own, and Chrome's own is hidden
    so there aren't two). attrs go to the <input>; it needs a
    placeholder, which is how the button knows the box is empty."""
    return Label(
        Span(SEARCH_SVG, cls="opacity-50"),
        Input(type="search", data_search_box=True,
              cls="peer grow min-w-0 [&::-webkit-search-cancel-button]:appearance-none "
                  "[&::-webkit-search-cancel-button]:hidden", **attrs),
        Button(X_SVG, type="button", data_clear_search=True, aria_label=i18n.t("Clear"),
               data_tip=i18n.t("Clear"),
               cls="btn btn-ghost btn-xs btn-circle -me-1.5 tooltip tooltip-left "
                   "peer-placeholder-shown:hidden"),
        cls=f"input input-sm {cls}"
    )


def SearchField(value, placeholder, go, keep: dict):
    """A search box that narrows the list as you type (LIVE_JS). A plain
    GET form underneath, so Enter - and a browser without JavaScript -
    still work. keep: the other filters it leaves as they are."""
    return Form(
        # the id lets the box stay as it is while the list swaps (LIVE_JS)
        SearchBox("w-56", name="q", value=value, placeholder=placeholder, autocomplete="off",
                  aria_label=placeholder.rstrip("…"), data_live_search=True, id="live-search"),
        *[Input(type="hidden", name=k, value=v) for k, v in keep.items()],
        action=go, method="get", role="search"
    )


def tag_url(tag: str) -> str:
    """A tag's page - quoted, so "#", "?" and spaces survive the trip."""
    from urllib.parse import quote
    return f"/tag/{quote(tag, safe='')}"


def safe_url(url: str) -> str:
    """A link the admin typed, only if it's a real web or mail address -
    never javascript: or anything else a browser would run."""
    url = (url or "").strip()
    return url if url.startswith(("https://", "http://", "mailto:", "/")) else ""


def EmptyState(message: str, icon: str = "📭", title: str = None, actions=None):
    """One consistent look for every 'nothing here' moment - post not
    found, no posts yet, no comments yet, empty search - instead of
    each one being whatever plain text happened to be written first.
    title and actions are for the bigger moments (an error page): a
    heading above the message, and a row of buttons below it."""
    return Div(
        Div(icon, cls="text-3xl mb-2"),
        H1(title, cls="text-xl font-bold mb-1") if title else None,
        P(message, cls="text-sm text-base-content/60"),
        Div(*actions, cls="flex justify-center gap-2 mt-5") if actions else None,
        cls="text-center py-12"
    )


def SettingsPanel(title, *content, key, open_=True, custom=None):
    title = i18n.spell(title)
    """A collapsible section for a settings sidebar - daisyUI collapse
    on a real <details>, not a checkbox hack. data_panel + PANEL_STATE_JS
    (app.py) is what lets each section's open/closed state persist
    across page loads (localStorage, per browser) - once you've toggled
    one, that choice wins over open_'s own default from then on. key
    must be unique across every panel that can appear on the same page
    at once (the post editor's own Publishing/Details/Series, Media's
    own Info/Edit, ...), since it's the localStorage key. custom: how
    many of its settings this page sets differently from the site (the
    bar beside each, CUSTOM_TAGS_JS) - counted after the title, kept up as
    they change."""
    return Details(
        # a real heading, so a screen reader's list of headings has the page's
        # panels in it, not only its title
        Summary(H2(title, Span(f" · {custom} changed" if custom else "", data_custom_count=True,
                               cls="font-normal text-base-content/60") if custom is not None else None,
                   cls="inline"),
                cls="collapse-title font-semibold text-sm min-h-0 py-3"),
        Div(*content, cls="collapse-content"),
        cls="collapse collapse-arrow bg-base-100 border border-base-300", open=open_, data_panel=key
    )


# Every side panel - Post settings, Help, Media's details: 360px, the
# usual width for a side sheet, and on a phone never more than the screen
# less 56px, so the page shows beside it and a tap there closes it. The
# admin menu is a list of links and keeps its own narrower 16rem.
DRAWER_W = "w-[22.5rem] max-w-[calc(100vw-3.5rem)]"
# Docked beside the page (Post settings, Media's details), a side panel is
# solid, as the admin's rail is - never the glass or the blended look of
# the site's own side panels, so the admin's frame is one look
DOCKED_FILL = "data-[docked]:bg-base-100! data-[docked]:backdrop-filter-none!"
# what's behind an open drawer (z-40): a click anywhere on it closes the
# drawer - above the header (z-30) and, in Focus mode, the full-screen
# writing and its bars (z-35 to z-38), or a click there missed it. The
# same dimming as the admin sidebar's; drawer-backdrop (input.css) gives
# every one the same light blur, with Frosted glass, and the same fade.
DRAWER_BACKDROP = "drawer-backdrop hidden fixed inset-0 z-[39] bg-black/40"


def Alert(message, kind="info"):
    if not message:
        return None
    return Div(message, role="alert" if kind == "error" else "status", cls=f"alert alert-{kind} py-2 text-sm {FIELD_GAP}")
