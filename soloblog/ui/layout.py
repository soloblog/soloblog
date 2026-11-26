"""Layout: the page every route returns."""
from fasthtml.common import *
from soloblog import i18n
from soloblog.ui.icons import HEART_SVG, HOME_SVG, SEARCH_BTN_SVG
from soloblog.ui.base import EmptyState, PAGE_PAD, WIDE_PAGE_WIDTHS, _request, content_width
from soloblog.ui.post import ConfirmDialog, ScrollToTopButton, SiteFooter, ToastContainer
from soloblog.ui.nav import Nav, SearchModal
from soloblog.ui.admin import AdminRail, AdminSidebar, AdminTopBar, DemoBanner, PreviewBanner

ERROR_PAGES = {
    404: ("Page not found", "The page you're looking for doesn't exist or has moved.", "🔍"),
    500: ("Something went wrong", "That didn't work on our end. Try again in a moment.", "⚠️"),
}

# The admin's controls and small print a size up from daisyUI's -sm and
# Tailwind's text-xs: 36px buttons and fields with 14px text, 14px
# choices, 13px help and details, 12px pills - the size its menu is, as
# in most apps. Only inside the admin; the site's
# own pages keep theirs. A text-xs with its own size at a breakpoint
# (sm:text-sm) keeps that.
ADMIN_SCALE = (
    "[&_.btn-sm]:[--fontsize:0.875rem] [&_.btn-sm]:[--size:calc(var(--size-field,0.25rem)*9)] "
    "[&_.input-sm]:[--in-size-mul:9] [&_.input-sm]:[--font-size-min:0.875rem] "
    "[&_.select-sm]:[--sl-size-mul:9] [&_.select-sm]:[--font-size-min:0.875rem] "
    "[&_.textarea-sm]:[--font-size-min:0.875rem] "
    "[&_.badge-xs]:[--size:calc(var(--size-selector,0.25rem)*5)] [&_.badge-xs]:text-[0.75rem] "
    # a fieldset's own text - a choice's words beside its radio; daisyUI sets it to 0.75rem
    "[&_.fieldset]:text-[0.875rem] [&_.fieldset-legend]:text-[0.8125rem]/5 [&_.fieldset-label]:text-[0.8125rem]/5 "
    # \: is a colon in a CSS identifier - a quote here would trip themes.lean_css
    r"[&_.text-xs:not([class*=\:text-])]:text-[0.8125rem]/5"
)


def ErrorPage(code: int, settings, logged_in=False, pinned_tree=()):
    """The 404 and 500 pages - the site's own header and footer around
    an EmptyState, so a wrong link still feels like part of the blog
    and always offers a way back: Home, or Search."""
    title, message, icon = ERROR_PAGES.get(code, ERROR_PAGES[500])
    title, message = i18n.t(title), i18n.t(message)
    actions = [
        Button(SEARCH_BTN_SVG, Span(i18n.t("Search"), cls="ml-1"), type="button", cls="btn btn-sm",
               data_open_dialog="search-modal"),
        A(HOME_SVG, Span(i18n.t("Home"), cls="ml-1"), href="/", cls="btn btn-primary btn-sm"),
    ]
    from soloblog import seo
    seo._page_title.set(f"{title} — {settings['site_title']}")
    return Layout(
        EmptyState(message, icon, title=title, actions=actions),
        settings=settings, logged_in=logged_in, pinned_tree=pinned_tree
    )


def AdminFooter(s):
    """The quiet line at the foot of every admin page: the version (and a
    newer one, with how to get it), Help, where to report a problem or
    ask, and how to support the project - on every screen of the admin."""
    from soloblog import config, updates
    return P(f"Soloblog {config.VERSION} · ",
             *([A(f"{newer[0]} is out", href=newer[1], target="_blank", rel="noopener",
                  cls="link link-hover text-primary font-medium"), " · ",
                # with an update hook set up (Integrations > Updates), one click
                Button("Update now", type="button", cls="link link-hover font-medium",
                       hx_post="/admin/update", hx_target="this", hx_swap="outerHTML",
                       data_confirm="Update to the new version now? The blog restarts, and is back in a minute or "
                                    "two. A backup first is a good idea while Soloblog is in beta.")
                if s.get("update_hook_url") else
                A("How to update", href="/admin/help?tab=run#update-soloblog", cls="link link-hover"), " · "]
               if (newer := updates.newer()) else []),
             A("Help", href="/admin/help", cls="link link-hover"), " · ",
             A("Report a problem", href=f"{config.PROJECT_URL}/issues/new/choose", target="_blank", rel="noopener",
               cls="link link-hover"), " · ",
             A("Ideas and questions", href=f"{config.PROJECT_URL}/discussions", target="_blank", rel="noopener",
               cls="link link-hover"), " · ",
             A(HEART_SVG, Span("Support Soloblog", cls="ml-1"), href="/admin/help?tab=sponsor",
               cls="link link-hover inline-flex items-center [&>svg]:h-3 [&>svg]:w-3 text-error"),
             cls="text-xs text-base-content/50 text-center mt-8")


# Something edge to edge that opens the page (data-flush: a full-width
# banner or cover) meets the header - flushEdges (chrome_offsets.js)
# measures it once the page is there; this is where it's drawn until
# then, from the top padding below (TOP_PAD) and the header's height, so
# it doesn't show a strip of page first and then jump
# (data-flush="open": the banner, a post's full-width or full screen cover)
FLUSH_GUESS = {
    "inline": "[&_[data-flush=open]]:-mt-14",
    "fixed": "[&_[data-flush=open]]:-mt-10",
    "floating": "[&_[data-flush=open]]:-mt-28 [&_[data-flush=open]]:[--flush-top:4.75rem]",
}


def _getting_started_dialog(settings):
    from soloblog.routes.welcome import GettingStartedDialog
    return GettingStartedDialog(settings, back=_request.get()[0] or "/admin/posts")


def Layout(*content, settings, logged_in=False, pinned_tree=(), admin_page=False, live=False, wide=False,
           space=None, bare=False):
    """admin_page - true only for the actual admin management pages
    (Posts, Media, Comments, Settings, the post editor), not merely
    "logged_in" (a logged-in admin still sees the public site's own
    pages while browsing it, e.g. its own live posts, and those aren't
    this). They always get the back-to-top button - Settings' long tabs
    and the help page need it - where the public site only has it if
    scroll_to_top is on.

    wide - a page that needs more room (a project, a landing page, a post
    with Page width: Wide) runs Wide (WIDE_PAGE_WIDTHS) instead of the reading width.

    bare - only the page: no header, footer or padding around it (a slide
    deck fills the screen).

    space - a page's own space between sections (pages.SPACINGS); None,
    the site's.

    live - the admin lists (Posts, Comments, Media, Messages): their
    plain POST forms, tabs, filters and pagination swap #page-content
    in place instead of reloading the page (LIVE_JS, app.py)."""
    from soloblog import pages
    header_style = settings.get("header_style")
    footer_enabled = settings.get("footer_enabled") == "1"
    # also gated on footer_enabled - an off footer needs no clearance,
    # regardless of what footer_style happens to still be set to
    footer_style = settings.get("footer_style") if footer_enabled else "inline"

    # A fixed or floating header is out of the page's flow, so the page
    # starts below it - a first guess at its height, which
    # syncChromeOffsets (app.py) replaces with the measured one. Floating
    # is a step more, for its gap from the top.
    TOP_PAD = {"inline": "pt-14", "fixed": "pt-24", "floating": "pt-28"}
    top_pad = TOP_PAD[header_style]
    # a bit more than before (pb-24 -> pb-32) - the redesigned footer
    # can be two rows tall on its taller side (bio+disclaimer stacked,
    # or links+socials stacked) instead of the old single centered row.
    # floating gets one step more again, same reasoning as top_pad above.
    BOTTOM_PAD = {"inline": "pb-12", "fixed": "pb-12 sm:pb-36", "floating": "pb-12 sm:pb-40"}
    bottom_pad = BOTTOM_PAD[footer_style]
    width = WIDE_PAGE_WIDTHS.get(settings.get("body_width"), WIDE_PAGE_WIDTHS["standard"]) if wide \
        else content_width(settings)

    # the page's one <title>: page_meta's (seo.py), else the site's own.
    # Returned beside the page rather than added to hdrs - FastHTML puts
    # its own default title first unless the response itself has one.
    from soloblog import seo
    admin = admin_page and logged_in
    page = Div(
        # the first thing Tab reaches - keyboard and screen reader users
        # jump past the nav; hidden until focused
        None if bare else A(
            i18n.t("Skip to content"), href="#main",
            cls="btn btn-sm btn-primary sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-[100]"),
        # the admin's own frame: a thin bar, the rail on a wide screen, and
        # no site header or footer
        AdminTopBar(settings) if admin else None if bare else Nav(settings, logged_in, pinned_tree, admin_page=admin),
        AdminRail(settings) if admin else None,
        _getting_started_dialog(settings) if admin else None,
        # bg-base-200 on Main: a shade darker than the header and footer,
        # edge to edge; the column inside keeps the width. A theme colour,
        # so it's right on every theme.
        Main(
            # an admin page: beside the rail on a wide screen, as the eye
            # starts there (and beside Post settings, where it's docked -
            # placePostSettings); centred on a phone
            Div(Div(*content, AdminFooter(settings), id="page-content",
                    data_live="1" if live else None, cls=f"{PAGE_PAD} pt-20 pb-12"),
                # what the top bar's search finds (AdminSearch), in the page's place
                Div(id="page-content-results", hidden=True,
                    cls=f"{PAGE_PAD} pt-20 pb-12 max-lg:[html[data-admin-search]_&]:pt-36"),
                # on a wide screen the page's colour ends with its column,
                # and what's past it is the side panels' - one look whether
                # Post settings or Media's details is there or not
                cls=f"relative {width} mx-auto lg:mx-0 bg-base-200 lg:min-h-dvh lg:border-r-[length:var(--border)] "
                    "lg:border-base-300") if admin else
            Div(*content, id="page-content", cls="w-full") if bare else
            Div(PreviewBanner(settings), *content, id="page-content",
                data_live="1" if live else None,
                cls=f"{width} mx-auto {PAGE_PAD} {top_pad} {bottom_pad} {FLUSH_GUESS[header_style]} "
                    f"{pages.SPACE_SCALE.get(space or settings.get('section_space'), pages.SPACE_SCALE['medium'])}".strip()),
            id="main", tabindex="-1",
            cls="flex-1 w-full bg-base-200 outline-none" + (
                " lg:pl-64 lg:[html[data-settings-docked]_&]:pr-[22.5rem] lg:bg-base-100" if admin else "")
        ),
        None if admin or bare else SiteFooter(settings, logged_in, admin_page=admin),
        # floating, so outside the page's column: what opens the page is its first thing (flushEdges)
        None if bare else DemoBanner(logged_in, admin_page=admin),
        ScrollToTopButton() if not bare and (settings.get("scroll_to_top") == "1" or admin_page) else None,
        ToastContainer(),
        ConfirmDialog(settings),
        None if bare else SearchModal(settings),
        # flex-col with flex-1 on Main keeps the footer at the foot of a
        # short page. The page's colour comes from <body> (bodykw in
        # app.py).
        #
        # overflow-x-clip, not -hidden: the banner's full-width breakout
        # can overshoot by a scrollbar's width, and clip hides that.
        # hidden would make this a scroll container (one axis hidden
        # turns the other to auto), and the editor's toolbar would stop
        # sticking to the top of the screen.
        cls="min-h-screen flex flex-col overflow-x-clip"
    )
    title = Title(seo.current_title() or settings.get("site_title") or "Soloblog")
    if not admin:
        return title, page
    # admin pages: the menu in the rail on a wide screen (above), else in
    # a drawer - daisyUI's, opened by the top bar's menu button
    return title, Div(
        # the buttons that open and close it are what's pressed and read out
        Input(type="checkbox", id="admin-drawer", cls="drawer-toggle", aria_hidden="true", tabindex="-1"),
        Div(page, cls="drawer-content min-w-0"),
        Div(Label(fr="admin-drawer", aria_label="Close the admin menu", cls="drawer-overlay"),
            AdminSidebar(settings), cls="drawer-side z-40"),
        data_admin=True, cls=f"drawer {ADMIN_SCALE}"
    )
