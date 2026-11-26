"""A visitor's header: the menu, search and the colour picker."""
from fasthtml.common import *
from soloblog import comments
from soloblog import i18n
from soloblog import posts
from soloblog.actions import on
from soloblog import settings
from soloblog.themes import OWN_PREFIX, all_choices, theme_choice, theme_label
from soloblog.ui.icons import CHEVRON_DOWN_SVG, GEAR_SVG, HAMBURGER_SVG, PALETTE_SVG, SEARCH_SVG, X_SVG
from soloblog.ui.base import (
    LoginButton, MARGIN_WIDTHS, MENU_SCROLLS, MoreBelowSlot, PageLink, RESULTS_CLS, SCROLLS, SiteLink, site_label, SEARCH_DIALOG_ACTION,
    SEARCH_DIALOG_BOX, SearchBox, TOUCH_BAR, TOUCH_BTN, _title_block, content_width, glass_fill,
)


def _health_dot() -> bool:
    """Something in Site health needs attention (health_alerts.note)."""
    from soloblog import health_alerts
    return health_alerts.needs_attention() > 0


def AdminMenuButton():
    """The one button that opens the admin menu in a drawer, where the
    rail doesn't show."""
    return Button(HAMBURGER_SVG, Span("Open the admin menu", cls="sr-only"), type="button",
                  data_toggles="admin-drawer", data_tip="Menu",
                  cls="btn btn-ghost btn-sm btn-square drawer-button tooltip tooltip-bottom lg:hidden")


def AdminMenu(fill="bg-base-100", logout_form=True):
    """Every admin action lives behind this one menu - not scattered
    across the top nav next to pinned pages. One entry point, findable
    in one place, and it never grows the public-facing nav.

    New post isn't listed separately - it lives as a button on the
    Posts page, so there's one way to start a post, not two."""
    pending = comments.count_pending()
    from soloblog import contact
    unread = contact.count_unread()
    # a plain sibling badge, not indicator/indicator-item - indicator
    # overlays its item on a *corner* of whatever it's attached to,
    # which read as "sitting slightly on top of" the word "Comments"
    # instead of next to it. justify-between just puts the two side by
    # side like the rest of daisyUI's own "badge in a menu row" examples.
    comments_item = (
        A(Span("Comments"), Span(str(pending), cls="badge badge-warning badge-xs"),
          href="/admin/comments", cls="justify-between")
        if pending else A("Comments", href="/admin/comments")
    )
    items = [
        Li(A("Posts and pages", href="/admin/posts")),
        Li(A("Media", href="/admin/media")),
        Li(comments_item),
        Li(A(Span("Contact messages"), Span(str(unread), cls="badge badge-warning badge-xs"),
             href="/admin/messages", cls="justify-between") if unread else A("Contact messages", href="/admin/messages"))
        if contact.in_use() else None,
        Li(A("Members", href="/admin/members")) if settings.get("members_enabled") == "1" else None,
        Li(A("Newsletter", href="/admin/newsletter")) if settings.get("newsletter_mode") == "builtin" else None,
        Li(A("Stats", href="/admin/stats")),
        Li(A(Span("Site health"), Span(cls="status status-error", aria_label="Needs attention", role="img"),
             href="/admin/health", cls="justify-between") if _health_dot() else A("Site health", href="/admin/health")),
        Li(A("Settings", href="/admin/settings")),
        Li(A("Help", href="/admin/help")),
        # a POST, not a link - a logout link can be triggered from any other site
        # form= points at the form outside the menu, so the button stays a
        # direct child of its <li> and gets the menu's own item styling
        Li(Button("Log out", type="submit", form="admin-logout-form"),
           cls="border-t-[length:var(--border)] border-base-300 mt-1 pt-1"),
    ]
    # popover="auto", not :focus-within - see POPOVER_DROPDOWN_JS
    # (app.py) for why: a real backdrop-filter compositing bug, proven
    # live, not a style preference. Gets outside-click/Escape-to-close
    # for free as part of the same fix.
    return Div(
        Button(GEAR_SVG, type="button", popovertarget="nav-admin-menu",
               cls=f"btn btn-ghost btn-xs {TOUCH_BTN} tooltip tooltip-bottom", data_tip="Admin", aria_label="Admin menu"),
        Ul(*items, id="nav-admin-menu", popover="auto",
           cls=f"menu menu-sm {MENU_SCROLLS} dropdown-content dropdown-end w-max {fill} rounded-box "
               "z-20 mt-2 p-2 shadow border-[length:var(--border)] border-base-200"),
        # on an admin page the drawer's sidebar has it already
        Form(id="admin-logout-form", action="/logout", method="post", cls="hidden") if logout_form else None,
        data_hover_menu=True
    )


def PinnedNavItem(page, children, fill="bg-base-100", id_suffix=""):
    """A pinned page in the header menu; with sub-pages (About > CV) its
    name goes to its page and its arrow opens a list of the sub-pages -
    or a mouse resting on it does (NAV_HOVER_JS). On a phone's list they
    fold under it, opened by its arrow. Its own page was the list's first
    line, the same name twice.

    The list is a popover, not <details>: nested in the header, a
    <details> list never drew its frosted-glass blur (see
    POPOVER_DROPDOWN_JS). id_suffix: Nav() renders the menu twice (the
    phone list, "-m", and the row), and each needs its own popover ids."""
    return NavParent(lambda cls=None: PageLink(page, cls=cls), page["title"], page["slug"], children, fill, id_suffix)


def SiteNavItem(settings, key, children, fill="bg-base-100", id_suffix=""):
    """One of the site's own pages in the header menu (Home, Blog...) -
    with pages nested under it, the same list as a page's sub-pages."""
    return NavParent(lambda cls=None: SiteLink(settings, "header", key, cls=cls),
                     site_label(settings, "header", key), f"site-{key}", children, fill, id_suffix)


def NavParent(link, title, ident, children, fill="bg-base-100", id_suffix=""):
    """A header menu item and the pages under it: link(cls) - its own
    link; ident - what its list's id is made from."""
    if not children:
        return Li(link())
    if id_suffix == "-m":
        # folded until its arrow is tapped - its name still opens its page
        return Li(Details(Summary(link()), Ul(*[Li(PageLink(c)) for c in children])))
    menu_id = f"pin-submenu-{ident}{id_suffix}"
    # fill matches whatever the header bar itself is using (opaque or
    # glass) - a solid flyout hanging off a see-through header would
    # look like a mismatched patch instead of one consistent bar
    return Li(
        # the name and its arrow as one item, each its own target
        # (the menu's own padding is on the item, here split between them)
        Div(link(cls="py-1.5 ps-3 pe-1"),
            Button(CHEVRON_DOWN_SVG, type="button", popovertarget=menu_id,
                   aria_label=i18n.t("Pages under {title}").format(title=title),
                   cls="flex items-center self-stretch ps-1 pe-3"),
            data_nav_parent=True, cls="flex items-stretch p-0 gap-0 [[data-nav-more-list]_&]:hidden"),
        # moved under More (fitNav): folded under its name, opened by its
        # arrow, as on a phone - a list opening from inside a list covered
        # its neighbours
        Details(Summary(link()), Ul(*[Li(PageLink(c)) for c in children]),
                cls="hidden [[data-nav-more-list]_&]:block"),
        Ul(
            *[Li(PageLink(c)) for c in children],
            id=menu_id, popover="auto",
            # as wide as its longest title (up to a limit) - a fixed width made
            # a long one scroll sideways, a scrollbar under the rounded corner
            cls=f"dropdown-content menu {MENU_SCROLLS} {fill} rounded-box z-20 mt-2 w-max max-w-72 "
                "[&>li>a]:whitespace-normal overflow-x-hidden p-2 shadow border-[length:var(--border)] border-base-200"
        ),
        data_hover_menu=True
    )


def SearchButton():
    """Opens SearchModal (defined below, rendered once per page in
    Layout) - a plain button, not a dropdown, so there's no
    hover/focus-close behavior to get right here at all."""
    return Button(SEARCH_SVG, type="button",
                  cls=f"btn btn-ghost btn-xs {TOUCH_BTN} tooltip tooltip-bottom", data_tip=i18n.t("Search"), aria_label=i18n.t("Search"),
                  data_open_dialog="search-modal")


def SearchModal(settings):
    """Search without leaving the page: results load right under the
    input as you type. Uses HTMX (already loaded by FastHTML itself for
    every page here - not an extra dependency, it's core to how this
    framework talks to the server) to hit a small results-only endpoint
    and swap the response straight into #search-modal-results. No
    other JavaScript involved - the modal open/close is native <dialog>,
    and autofocus is a plain HTML attribute the browser honors itself
    when showModal() runs, no manual focus() timing needed.
    The full /search page still exists too (direct links, no-JS
    fallback) - this is an additional, faster way to search, not a
    replacement for it."""
    return Dialog(
        Div(
            H3(i18n.t("Search"), id="search-modal-title", cls="font-semibold mb-3"),
            SearchBox(name="q", placeholder=i18n.t("Search posts..."), autofocus=True,
                      aria_label=i18n.t("Search"), autocomplete="off",
                      hx_get="/search/results", hx_target="#search-modal-results",
                      hx_swap="innerHTML show:none focus-scroll:false",
                      hx_trigger="input changed delay:400ms, search"),
            Div(id="search-modal-results", data_scroll_hint=True, data_scroll_more="search-modal-more",
                cls=f"mt-3 {RESULTS_CLS}"),
            Div(MoreBelowSlot("search-modal-more"),
                Button(X_SVG, Span(i18n.t("Close"), cls="ml-1"), type="button", cls="btn btn-sm",
                       data_close_dialog="search-modal"),
                cls=SEARCH_DIALOG_ACTION),
            cls=f"{SEARCH_DIALOG_BOX} max-w-lg {glass_fill(settings)}"
        ),
        Form(Button(cls="cursor-default", aria_label=i18n.t("Close")), method="dialog", cls="modal-backdrop"),
        id="search-modal", aria_labelledby="search-modal-title", cls="modal modal-top sm:modal-middle"
    )


def _theme_swatch_preview(t):
    """A tiny 3-dot preview of a theme's own colors, scoped to just
    this element via its own data-theme - same trick the admin's
    ThemeSwatch (routes/admin_settings) uses, shrunk down for a
    menu row instead of a settings-page grid."""
    return Div(
        Div(cls="w-1.5 h-1.5 rounded-full bg-primary"),
        Div(cls="w-1.5 h-1.5 rounded-full bg-secondary"),
        Div(cls="w-1.5 h-1.5 rounded-full bg-accent"),
        data_theme=t, cls="flex gap-0.5 p-1 rounded-field border-[length:var(--border)] border-base-300 shrink-0"
    )


def VisitorThemeSwitcher(settings, fill="bg-base-100"):
    """The readers' colours menu, when it's turned on: each choice
    applies at once and is remembered in that reader's browser
    (theme-change's data-set-theme). The choices have no href - they
    aren't links, and "#" would jump the page; tabindex keeps them in
    reach of the keyboard. data-act-class marks the one in use."""
    if settings.get("visitor_theme_switching") != "1":
        return None
    # the defaults first, and named: both when the site follows each
    # visitor's device, only the one it always shows otherwise
    light, dark, mode = theme_choice(settings)
    if mode == "auto":
        marks = {light: i18n.t("light default"), dark: i18n.t("dark default")}
    else:
        marks = {light if mode == "light" else dark: i18n.t("default")}
    # the defaults, then your own palettes (themes.own_themes), then daisyUI's
    themes = list(marks) + [t for t in all_choices() if t not in marks]
    # first: forget the visitor's pick - back to the site's own, following
    # their device when the site does (resetTheme, app.py)
    items = [Li(A(i18n.t("Default"), tabindex="0", data_theme_default=True, data_prevent_default=True,
                  **on("click", "resetTheme")),
                cls="border-b-[length:var(--border)] border-base-200 mb-1 pb-1")] + [
        Li(A(_theme_swatch_preview(t), theme_label(t) if t.startswith(OWN_PREFIX) else t.capitalize(),
             # a badge brings its own background - grey text alone vanished
             # on the highlighted row, whose text turns neutral-content
             Span(marks[t], cls="badge badge-xs") if t in marks else None,
             tabindex="0", data_set_theme=t, data_act_class="menu-active",
             # FastHTML's A() defaults href to "#" when none is given,
             # and theme-change's own click handler doesn't preventDefault
             # - without this, every click also appended a bare # to the
             # URL. theme-change's own logic doesn't depend on the
             # default action, so suppressing it here is safe.
             data_prevent_default=True))
        for t in themes
    ]
    # popover="auto", not :focus-within - see POPOVER_DROPDOWN_JS
    # (app.py) for why: a real backdrop-filter compositing bug, proven
    # live, not a style preference. Gets outside-click/Escape-to-close
    # for free as part of the same fix.
    return Div(
        Button(PALETTE_SVG, type="button", popovertarget="nav-theme-menu",
               cls=f"btn btn-ghost btn-xs {TOUCH_BTN} tooltip tooltip-bottom", data_tip=i18n.t("Colours"),
               aria_label=i18n.t("Colours")),
        # a rounded box that clips, with the list scrolling inside it - on
        # the list itself, the scrollbar sat on the rounded edge and
        # squared off the corners. .menu's own flex-wrap would fan a
        # height-capped list out into columns, hence flex-nowrap.
        Div(Ul(*items, data_scroll_hint=True,
               cls=f"menu menu-sm flex-nowrap w-max max-h-72 overflow-y-auto {SCROLLS}"),
            # thirty palette names are words on every page: search
            # engines quoted them as the site's description
            id="nav-theme-menu", popover="auto", data_nosnippet=True,
            cls=f"dropdown-content dropdown-end {fill} rounded-box overflow-hidden z-20 mt-2 p-1 shadow "
                "border-[length:var(--border)] border-base-200"),
        data_hover_menu=True
    )


HEADER_WIDTHS = {"column": "As wide as the text", "wide": "As wide as the side panels"}
HEADER_ALIGNS = {"left": "Title on the left, the menu beside it",
                 "center": "Title centered, the menu behind a button",
                 "stacked": "Title centered, the menu on its own row below"}


# The header's menu stays on one line: a link never breaks over two, and
# the ones that don't fit go under More (fitNav, app.py) - or, when even
# that doesn't fit, the whole menu folds into the menu button, as on a
# phone (data-nav-folded). So it can be shown from a tablet's width up.
NAV_ONE_LINE = "flex-nowrap [&_a]:whitespace-nowrap [&_summary]:whitespace-nowrap [&_button]:whitespace-nowrap"


def Nav(settings, logged_in, pinned_tree=(), admin_page=False):
    centered = settings.get("header_align") == "center"
    stacked = settings.get("header_align") == "stacked"
    header_style = settings.get("header_style")
    fixed = header_style == "fixed"
    floating = header_style == "floating"
    width = MARGIN_WIDTHS.get(settings.get("body_width"), MARGIN_WIDTHS["standard"]) \
        if settings.get("header_width") == "wide" else content_width(settings)
    # Glass is frosted, never fully clear - text over moving content was
    # hard to read. The same fill goes to every menu the header opens, so
    # they match the bar they hang from.
    fill = glass_fill(settings)

    # The menu's links (Search is an icon beside it, not one of them). A
    # function: the menu is drawn twice, the phone list and the row, and
    # each copy needs its own popover ids (id_suffix).
    # the header's menus at 14px (daisyUI's menu, not menu-sm): the main way
    # around a site, about the size most sites use
    def build_page_links(id_suffix):
        links = []
        # Home, Blog and the built-in pages sit among the pages where Posts and pages > Pinned put
        # them. A page of your own as the homepage (Settings > Name and homepage) moves the posts
        # to /blog
        for item in posts.menu_items(settings, pinned_tree):
            if isinstance(item, str):
                if not (item == "home" and settings.get("nav_home_hidden")):
                    links.append(SiteNavItem(settings, item, getattr(item, "children", ()), fill, id_suffix))
                else:
                    # Home left out of the menu: the pages under it still are
                    links += [Li(PageLink(c)) for c in getattr(item, "children", ())]
            else:
                links.append(PinnedNavItem(item[0], item[1], fill, id_suffix))
        return links

    def more_item(id_suffix):
        """Where the links that don't fit on the row go (fitNav, app.py) -
        hidden while they all fit."""
        menu_id = f"nav-more{id_suffix}"
        return Li(Button(i18n.t("More"), CHEVRON_DOWN_SVG, type="button", popovertarget=menu_id,
                         cls="flex items-center gap-1"),
                  Ul(id=menu_id, popover="auto", data_nav_more_list=True,
                     cls=f"dropdown-content menu {MENU_SCROLLS} {fill} rounded-box z-20 mt-2 w-max max-w-72 "
                         "[&>li>a]:whitespace-normal overflow-x-hidden p-2 shadow border-[length:var(--border)] "
                         "border-base-200"),
                  data_nav_more=True, hidden=True)
    page_links = build_page_links("-m")

    # the floating pill's own look - both branches below (centered/left)
    # add this to their own width-capped `inner`, since that's the div
    # that needs to actually look like a detached bar; the plain
    # inline/fixed cases don't touch this at all.
    pill_cls = f" rounded-box border border-base-300 shadow-lg {fill}" if floating else ""
    search_menu = SearchButton()
    theme_switcher = VisitorThemeSwitcher(settings, fill)

    # mobile: a dropdown behind a hamburger button, content links only -
    # admin stays in its own menu even on mobile, never mixed in.
    # label+tabindex, matching Search/Theme/Admin - opens on tap/click,
    # stays open regardless of the mouse, closes only on a tap/click
    # elsewhere. md:hidden only in the LEFT-aligned layout, which still
    # has room for a real horizontal menu at desktop width - centered
    # stays collapsed at every width (see `centered` branch below), so
    # its own hamburger has to stay clickable there too.
    hamburger_cls = f"btn btn-ghost btn-sm {TOUCH_BTN} tooltip tooltip-bottom" if centered \
        else f"btn btn-ghost btn-sm {TOUCH_BTN} md:hidden group-data-[nav-folded]/header:inline-flex! tooltip tooltip-bottom"
    # popover="auto", not :focus-within - see POPOVER_DROPDOWN_JS
    # (app.py) for why: a real backdrop-filter compositing bug, proven
    # live, not a style preference. Gets outside-click/Escape-to-close
    # for free as part of the same fix.
    mobile_menu = Div(
        Button(HAMBURGER_SVG, type="button", popovertarget="nav-mobile-menu", cls=hamburger_cls, data_tip=i18n.t("Menu"),
               aria_label=i18n.t("Menu")),
        # 80% of a phone's width, as a navigation drawer is, up to 360 px
        # on anything wider; a long name wraps - an opened page's
        # sub-pages ran past a fixed width's right edge
        Ul(*page_links, id="nav-mobile-menu", popover="auto",
           cls=f"menu {MENU_SCROLLS} dropdown-content {fill} rounded-box z-20 mt-3 w-[min(80vw,22.5rem)] p-2 shadow "
               "[&_:is(a,summary)]:whitespace-normal overflow-x-hidden border-[length:var(--border)] border-base-200")
    )

    # the site's own pages: the gear is the way back to the admin
    admin_area = AdminMenu(fill) if logged_in else LoginButton(settings)

    if centered:
        # One row at every width - the menu button on the left, the title
        # centred, the icons on the right - the same height as the left
        # layout. navbar-start and navbar-end are each half the row, so
        # the title is centred whatever sits beside it.
        inner = Div(
            Div(mobile_menu, Div(_title_block(settings), cls="sm:hidden min-w-0"), cls="navbar-start min-w-0 gap-1"),
            Div(_title_block(settings), cls="navbar-center min-w-0 hidden sm:flex"),
            Div(search_menu, theme_switcher, admin_area, cls="navbar-end min-w-0 gap-0.5 pointer-coarse:gap-0 sm:gap-2"),
            cls=f"navbar min-h-12 {TOUCH_BAR} {width} mx-auto px-2 sm:px-4{pill_cls}"
        )
    elif stacked:
        # the classic blog masthead: the title in the middle of its own
        # row, the menu centered on the next - the menu button stands in
        # for that row on narrower screens
        inner = Div(
            Div(
                Div(mobile_menu, Div(_title_block(settings), cls="sm:hidden min-w-0"), cls="navbar-start min-w-0 gap-1"),
                Div(_title_block(settings), cls="navbar-center min-w-0 hidden sm:flex"),
                Div(search_menu, theme_switcher, admin_area, cls="navbar-end min-w-0 gap-0.5 pointer-coarse:gap-0 sm:gap-2"),
                cls=f"navbar min-h-12 {TOUCH_BAR} p-0"
            ),
            Div(Ul(*build_page_links("-d"), more_item("-d"), data_nav_menu=True,
                   cls=f"menu menu-horizontal px-1 {NAV_ONE_LINE}"),
                cls="hidden md:flex group-data-[nav-folded]/header:hidden! justify-center"),
            cls=f"{width} mx-auto px-2 sm:px-4 py-1{pill_cls}"
        )
    else:
        desktop_menu = Ul(*build_page_links("-d"), more_item("-d"), data_nav_menu=True,
                          cls=f"menu menu-horizontal px-1 hidden md:flex {NAV_ONE_LINE} "
                              "group-data-[nav-folded]/header:hidden!")
        # not the navbar's own 50/50 split here: the title takes what it
        # needs and the menu gets the rest - at half the row, four page
        # links plus the three icons already wrapped onto a second line
        inner = Div(
            Div(mobile_menu, _title_block(settings), cls="navbar-start w-auto min-w-0 gap-1"),
            Div(desktop_menu, search_menu, theme_switcher, admin_area, cls="navbar-end w-auto flex-1 gap-0.5 pointer-coarse:gap-0 sm:gap-2"),
            cls=f"navbar min-h-12 {TOUCH_BAR} {width} mx-auto px-2 sm:px-4{pill_cls}"
        )

    # Inline and fixed: the bar runs edge to edge, its contents as wide as
    # the column - a border under an inline one, a shadow under a fixed
    # one. Floating: `inner` is the bar (pill_cls), and the outer element
    # only holds it in place, px-4 from the screen's edges.
    if floating:
        # 8 px from a phone's edges, not 16: room for the site's name
        # beside four buttons a finger can hit
        outer_cls = "fixed top-4 inset-x-0 z-30 px-4 max-sm:px-2"
    elif fixed:
        outer_cls = f"{fill} fixed top-0 left-0 right-0 z-30 shadow-sm"
    else:
        outer_cls = f"{fill} border-b-[length:var(--border)] border-base-200"
    # data-site-header - CHROME_OFFSETS_JS (app.py) measures it
    return Header(inner, data_site_header=True, cls=f"{outer_cls} group/header print:hidden")
