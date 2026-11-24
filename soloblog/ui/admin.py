"""The admin's own frame: its menu, top bar and banners."""
from fasthtml.common import *
from soloblog import comments
from soloblog import i18n
from soloblog.actions import on, EL
from soloblog import settings
from soloblog.ui.icons import CHECK_SVG, CHEVRON_DOWN_SVG, CHEVRON_UP_SVG, REPLY_SVG, SEARCH_SVG, X_SVG
from soloblog.ui.base import IconAction, SCROLLS, SearchBox, _request, _title_block
from soloblog.ui.nav import AdminMenu, AdminMenuButton, VisitorThemeSwitcher, _health_dot

# the admin menu: the size the rest of the app's text is (14px rows of
# about 36px, as Linear's, Notion's and Ghost's menus are), its headings
# small and quiet with room above, so each group reads as one
MENU_HEADING = "menu-title text-xs font-semibold text-base-content/50 pt-4 pb-1"


def _nav_icon(d: str):
    return NotStr('<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" '
                  f'stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path stroke-linecap="round" '
                  f'stroke-linejoin="round" d="{d}"/></svg>')


# heroicons (outline), for the sidebar
_ICONS = {
    "posts": "M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z",
    "media": "m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 0 0 1.5-1.5V6a1.5 1.5 0 0 0-1.5-1.5H3.75A1.5 1.5 0 0 0 2.25 6v12a1.5 1.5 0 0 0 1.5 1.5Zm10.5-11.25h.008v.008h-.008V8.25Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z",
    "comments": "M2.25 12.76c0 1.6 1.123 2.994 2.707 3.227 1.087.16 2.185.283 3.293.369V21l4.076-4.076a1.526 1.526 0 0 1 1.037-.443 48.282 48.282 0 0 0 5.68-.494c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018Z",
    "messages": "M2.25 13.5h3.86a2.25 2.25 0 0 1 2.012 1.244l.256.512a2.25 2.25 0 0 0 2.013 1.244h3.218a2.25 2.25 0 0 0 2.013-1.244l.256-.512a2.25 2.25 0 0 1 2.013-1.244h3.859m-19.5.338V18a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18v-4.162c0-.224-.034-.447-.1-.661L19.24 5.338a2.25 2.25 0 0 0-2.15-1.588H6.911a2.25 2.25 0 0 0-2.15 1.588L2.35 13.177a2.25 2.25 0 0 0-.1.661Z",
    "members": "M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z",
    "newsletter": "M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75",
    "stats": "M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z",
    "settings": "M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z",
    "health": "M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12Z",
    "help": "M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 5.25h.008v.008H12v-.008Z",
    "new": "M12 4.5v15m7.5-7.5h-15",
    "site": "M13.5 6H5.25A2.25 2.25 0 0 0 3 8.25v10.5A2.25 2.25 0 0 0 5.25 21h10.5A2.25 2.25 0 0 0 18 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25",
    "logout": "M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15m3 0 3-3m0 0-3-3m3 3H9",
}

# Settings' pages, under small headings, one page at a time - as Notion
# and Ghost group theirs (docs/DEVELOPMENT.md > Writing and settings).
# The keys are in addresses (?tab=) - rename the labels only.
SETTINGS_GROUPS = [
    ("Site", [("name", "Name and homepage"), ("url", "URL and SEO"), ("language", "Language and time")]),
    ("Design", [("style", "Style"), ("blog", "Blog layout"), ("posts", "Posts"),
                ("header", "Header and footer"), ("banner", "Banner")]),
    ("You", [("profile", "Profile and links")]),
    ("Readers", [("messages", "Comments and messages"), ("newsletter", "Newsletter"), ("members", "Members")]),
    ("Growth", [("analytics", "Analytics and ads"), ("sharing", "Sharing")]),
    ("Writing", [("editor", "Editor")]),
    ("Advanced", [("email", "Email"), ("integrations", "Integrations"), ("security", "Security"),
                  ("backup", "Backup and import")]),
]
SETTINGS_SECTIONS = [page for _, pages in SETTINGS_GROUPS for page in pages]

# Help's sections (routes/help_routes.HELP_PAGES) - each a file in docs/ -
# under small headings in the admin menu, as Settings' pages are
HELP_GROUPS = [
    ("User guide", [("getting-started", "Getting started"), ("writing", "Writing posts"),
                    ("pages", "Creating pages"), ("design", "Designing the site"), ("grow", "Growing an audience"),
                    ("run", "Running the site"), ("put-together", "How a site is put together"),
                    ("sections-templates", "Sections and templates"), ("how-it-works", "Privacy and how it works"),
                    ("reference", "Reference")]),
    ("More help", [("faq", "Common questions"), ("troubleshooting", "Troubleshooting"),
                   ("whatsnew", "What's new"), ("deployment", "Hosting and deploying"), ("api", "The API"),
                   ("sponsor", "Support Soloblog")]),
]
HELP_SECTIONS = [page for _, pages in HELP_GROUPS for page in pages]


def ReplyButton(comment_id, menu_label=True):
    """Opens a comment's ReplyBox (openReply, app.py) - and closes the ⋯
    menu it's in, and any other reply box. menu_label: its word in a
    phone's ⋯ menu (the admin); beside a comment bubble there's no room."""
    return IconAction(REPLY_SVG, i18n.t("Reply"), aria_controls=f"reply-{comment_id}", menu_label=menu_label,
                      **on("click", "openReply", f"reply-{comment_id}", EL))


def ReplyBox(action, comment_id, *fields, redirect_to=None):
    """Replying to a comment: a box that opens under it, where you'd look
    for it - the same on the post page and in the admin's comments, on a
    phone and a wide screen. fields: what else the form needs (a
    visitor's name and email). Hidden until its ReplyButton opens it."""
    return Form(
        Input(type="hidden", name="parent_id", value=comment_id),
        Input(type="hidden", name="redirect_to", value=redirect_to) if redirect_to else None,
        *fields,
        Textarea(name="body", placeholder=i18n.t("Write a reply..."), required=True, aria_label=i18n.t("Reply"),
                 cls="textarea textarea-sm w-full mb-2", rows="3"),
        Div(
            Span(data_status_slot=True, role="status", cls="text-xs text-base-content/50"),
            Div(Button(CHECK_SVG, Span(i18n.t("Post"), cls="ml-1"), type="submit", cls="btn btn-xs join-item"),
                Button(X_SVG, Span(i18n.t("Discard"), cls="ml-1"), type="button", cls="btn btn-xs join-item",
                       **on("click", "closeReply", EL)),
                cls="join ml-auto"),
            cls="flex items-center gap-2 w-full"
        ),
        action=action, method="post", id=f"reply-{comment_id}", hidden=True, data_reply_box=True,
        cls="flex flex-col items-end mt-2 mb-2"
    )


def DemoBanner(logged_in, admin_page=False):
    """The public demo's note (config.DEMO_MODE): floating in the corner,
    so it never moves the site's own layout, with a ✕ that puts it away
    on that page (it's back on the next). What this is, when it resets, the next step - and the
    style being tried, with the others. On a phone it's one line, which
    opens to the rest: all of it covered the bottom fifth of the screen."""
    from soloblog import config, demo, presets
    if not config.DEMO_MODE or settings.get("_design_preview"):
        return None
    left = demo.minutes_left()
    when = f"{left // 60} h {left % 60} min" if left >= 60 else f"{left} min"
    trying = settings.get("_previewing")
    trying = trying if trying and presets.find(trying) else ""
    link = "link font-medium"
    # on a phone one thin line, which opens to the rest (open already while a
    # style is being tried, for its way back); from sm up, all of it
    more = "basis-full max-sm:hidden max-sm:peer-checked:block"
    # the soft tint is see-through: on a solid card, over the page
    return Div(Div(
        Input(type="checkbox", id="demo-note-more", checked=bool(trying), cls="peer sr-only"),
        Label(Span(Strong("Soloblog demo"), f" · resets in {when}"),
              Span(CHEVRON_UP_SVG, data_chevron=True, cls="inline-flex sm:hidden opacity-60"),
              fr="demo-note-more",
              cls="flex-1 flex items-center gap-2 max-sm:min-h-11 max-sm:cursor-pointer rounded-field "
                  "peer-checked:[&>[data-chevron]]:rotate-180 "
                  "peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2"),
        Button(X_SVG, type="button", aria_label="Close", data_tip="Close",
               cls="btn btn-ghost btn-xs btn-square tooltip tooltip-left -my-1 -me-2", **on("click", "closeDemoNote")),
        Div(DemoStyles(trying), cls=more) if trying else None,
        Div(*([] if admin_page else [A("Take the tour", href="/tour", cls=link), " · "]),
            *([A("Open the admin", href="/admin", cls=link), " · "] if logged_in and not admin_page else
              [A("Log in", href="/login", cls=link), " · password ", Code(config.DEMO_PASSWORD), " · "]
              if not logged_in else []),
            A("Get Soloblog", href=f"{config.WEBSITE_URL}/get-started", target="_blank", rel="noopener", cls=link),
            cls=more),
        cls="alert alert-info alert-soft text-sm flex flex-wrap items-center gap-x-2 gap-y-1 max-sm:py-1"),
        role="note", data_demo_note=True,
        # bottom left, above a fixed footer; in the admin, beside its rail
        cls="fixed z-40 bottom-[calc(var(--footer-h,0px)+1rem)] left-4 right-4 sm:right-auto sm:max-w-sm "
            "bg-base-100 rounded-box shadow-lg print:hidden [html[data-demo-note-closed]_&]:hidden"
            + (" lg:left-[17rem]" if admin_page else "")
    )


def PreviewBanner(settings):
    """At the top of the site while a settings preset is being previewed
    (app.PresetPreview) - what it is, and the ways out."""
    from soloblog import presets
    key = settings.get("_previewing")
    if not key or not presets.find(key):
        return None
    name = presets.find(key)[0]
    from soloblog import config
    if config.DEMO_MODE:
        # the demo's own note says which style it is, with the others (DemoBanner)
        return None
    return Div(
        Span(Strong(f"Previewing the {name} style. "), "Nothing is saved until you use it. "),
        Form(Input(type="hidden", name="key", value=key),
             Button("Use it", type="submit", formaction="/admin/presets/apply", cls="btn btn-xs btn-primary"),
             Button("Stop previewing", type="submit", formaction="/admin/presets/stop", cls="btn btn-xs"),
             method="post", cls="inline-flex gap-2 ms-2 align-middle"),
        role="note", cls="alert alert-info alert-soft text-sm mb-6 block print:hidden"
    )


def DemoStyles(current):
    """While a visitor tries one of the demo's styles (presets.py,
    /demo/style): which, the others in a menu
    that opens upward from the corner, and the way back to Mira's own."""
    from soloblog import presets
    others = [Li(A(name, href=f"/demo/style/{key}")) for key, (name, *_) in presets.PRESETS.items() if key != current]
    return Div(
        Span("Trying the ", Strong(presets.find(current)[0]), " style"),
        Div(Details(Summary("Try another", Span(CHEVRON_DOWN_SVG, cls="inline-flex rotate-180"),
                            cls="btn btn-xs"),
                    Ul(*others, cls="dropdown-content menu menu-sm bg-base-100 rounded-box shadow-lg z-50 w-max p-2 mb-1"),
                    cls="dropdown dropdown-top"),
            A("Back to Mira's look", href="/demo/style", cls="btn btn-xs btn-ghost"),
            cls="flex flex-wrap items-center gap-2"),
        cls="flex flex-col gap-1.5 py-1")


def _getting_started_entry(settings):
    from soloblog.routes.welcome import GettingStartedEntry
    return GettingStartedEntry(settings)


def AdminSidebar(settings, in_margin=False, rail=False):
    """Every admin page, named in full. Two copies on each admin page
    (Layout): in the page's left margin, right beside the content, where
    the screen is wide enough - on a 4K screen it would be far off at the
    edge otherwise - and in a drawer, opened by the gear button, where it
    isn't. Where you are is marked from the request itself (set_request)."""
    path, tab = _request.get()
    pending = comments.count_pending()
    from soloblog import contact
    unread = contact.count_unread()

    def item(label, href, icon, badge=0, active=None, dot=False):
        here = active if active is not None else (path == href or path.startswith(href + "/"))
        return Li(A(_nav_icon(_ICONS[icon]), Span(label, cls="flex-1"),
                    Span(str(badge), cls="badge badge-warning badge-xs") if badge else None,
                    Span(cls="status status-error", aria_label="Needs attention", role="img") if dot else None,
                    href=href, cls="menu-active" if here else None, aria_current="page" if here else None))

    on_help = path == "/admin/help"
    help_tab = tab if tab in dict(HELP_SECTIONS) else "getting-started"
    on_settings = path == "/admin/settings"
    settings_tab = tab if tab in dict(SETTINGS_SECTIONS) else "name"

    def sections(items, base, on, current, groups=None):
        def link(key, label):
            return Li(A(label, href=f"{base}?tab={key}", cls="menu-active" if on and key == current else None,
                        aria_current="page" if on and key == current else None))
        if groups:
            return Ul(*[part for group, pages in groups
                        # a level below the menu's own headings: not bold, so the two don't read alike
                        for part in [Li(group, cls="menu-title text-xs font-normal pt-3 pb-1")]
                        + [link(k, label) for k, label in pages]])
        return Ul(*[link(k, label) for k, label in items])
    parts = (
        # the site's name - beside the page, the header just above already says it
        None if in_margin else Div(
            A(settings.get("site_title") or "Soloblog", href="/",
              cls="font-semibold truncate px-2 min-w-0 pointer-coarse:min-h-11 pointer-coarse:content-center"),
            Button(X_SVG, type="button", data_toggles="admin-drawer", aria_label="Close the admin menu",
                   cls="btn btn-sm btn-ghost btn-square shrink-0"),
            cls="flex items-center justify-between gap-2 mb-3"),
        A(_nav_icon(_ICONS["new"]), Span("New post"), href="/admin/new",
          cls="btn btn-primary btn-sm w-full shrink-0"),
        # only the pages scroll: New post above and View your site and Log
        # out below stay where they are, as in other apps' side menus. The
        # fade is a mask, so the scroll is inside, clear of the menu's fill
        Div(Ul(
            Li("Content", cls=MENU_HEADING),
            item("Posts and pages", "/admin/posts", "posts",
                 active=path in ("/admin/posts",) or path.startswith("/admin/edit")),
            item("Media", "/admin/media", "media"),
            Li("Audience", cls=MENU_HEADING),
            item("Comments", "/admin/comments", "comments", pending),
            # the form off and nothing in it: one less thing to wonder about
            item("Contact messages", "/admin/messages", "messages", unread) if contact.in_use() else None,
            item("Members", "/admin/members", "members") if settings.get("members_enabled") == "1" else None,
            item("Newsletter", "/admin/newsletter", "newsletter")
            if settings.get("newsletter_mode") == "builtin" else None,
            item("Stats", "/admin/stats", "stats"),
            Li("Manage", cls=MENU_HEADING),
            item("Site health", "/admin/health", "health", dot=_health_dot()),
            Li(Details(
                Summary(_nav_icon(_ICONS["settings"]), Span("Settings")),
                sections(SETTINGS_SECTIONS, "/admin/settings", on_settings, settings_tab, SETTINGS_GROUPS),
                open=on_settings or None)),
            Li(Details(
                Summary(_nav_icon(_ICONS["help"]), Span("Help")),
                sections(HELP_SECTIONS, "/admin/help", on_help, help_tab, HELP_GROUPS),
                open=on_help or None)),
            # id - LIVE_JS refreshes both copies with the list, for the counts
            id="admin-nav-margin" if in_margin else "admin-nav", cls="menu w-full p-0 mt-2 mb-3 gap-0.5"
        ), data_scroll_hint=True, cls=f"flex-1 min-h-0 overflow-y-auto overscroll-contain -mx-3 px-3 {SCROLLS}"),
        Ul(
            # until the first things are set up: they open in a box in the
            # middle of the screen (routes/welcome.py)
            _getting_started_entry(settings),
            Li(A(_nav_icon(_ICONS["site"]), Span("View your site"), href="/", target="_blank", rel="noopener")),
            # a POST, not a link - a logout link can be triggered from any other site
            Li(Button(_nav_icon(_ICONS["logout"]), Span("Log out"), type="submit", form="admin-logout-form")),
            cls="menu w-full p-0 pt-3 gap-0.5 shrink-0 border-t-[length:var(--border)] border-base-300"
        ),
        None if in_margin else Form(id="admin-logout-form", action="/logout", method="post", cls="hidden"),
    )
    if rail:
        # in AdminRail: no card of its own - the rail is the frame
        return Nav(*parts, data_admin_nav=True, aria_label="Admin", cls="w-full flex flex-col flex-1 min-h-0")
    # daisyUI's drawer-side doesn't scroll a menu taller than the screen
    # (Settings and Help both open), it cut it off
    return Nav(Div(*parts, cls="h-full p-3 flex flex-col"),
               data_admin_nav=True, data_own_scroll=True, aria_label="Admin",
               cls="h-dvh w-64 bg-base-100 border-r-[length:var(--border)] border-base-300")


def AdminTopBar(settings):
    """The admin's own thin bar at every width, in place of the site's
    header and footer, as Ghost's and WordPress's are: the menu button
    (where the rail doesn't show), the site's name (it opens the site)
    and the colours - over the rail on a wide screen, at its edge."""
    return Header(
        Div(Div(AdminMenuButton(), _title_block(settings), cls="flex items-center gap-1 min-w-0"),
            # search first, as in most apps' bars - on a wide screen it's the
            # box beside the rail instead
            Div(Button(SEARCH_SVG, type="button", aria_label="Search settings and help", data_tip="Search",
                       cls="btn btn-ghost btn-xs tooltip tooltip-bottom lg:hidden", **on("click", "toggleAdminSearch")),
                VisitorThemeSwitcher(settings),
                # where the rail folds into the menu button, the gear the
                # site's own header has - the same menu, in reach
                Div(AdminMenu(logout_form=False), cls="lg:hidden"),
                cls="flex items-center gap-0.5 shrink-0"),
            # the rail's own width less the bar's padding: the colours
            # line up with the rail's contents
            cls="flex items-center justify-between gap-2 w-full lg:w-[calc(16rem-1.5rem)] lg:shrink-0"),
        AdminSearch(),
        # data-site-header: what sits under it is measured from it (CHROME_OFFSETS_JS)
        data_site_header=True, data_admin_bar=True,
        # z-[31]: over the rail (z-30), or the rail hid the colours' tooltip
        cls="fixed top-0 inset-x-0 z-[31] h-12 px-2 sm:px-3 flex items-center gap-2 bg-base-100 "
            "border-b-[length:var(--border)] border-base-300 print:hidden")


def AdminSearch():
    """One box for every setting and every Help page, from any admin page:
    what matches takes the page's place until it's cleared
    (INDEX_SEARCH_JS). Beside the rail, level with the page, on a wide
    screen; on a phone the bar's magnifier opens it as a row under the bar."""
    return Div(
        SearchBox("w-full", id="admin-search", placeholder="Search settings and help…",
                  aria_label="Search settings and help", autocomplete="off", data_index_search="/admin/search-index",
                  data_index_body="page-content", data_index_noun="result", data_index_nouns="results",
                  data_index_last="Help: What's new", data_index_first="Admin|Settings: ", data_index_no_url=True, data_recent_searches="admin"),
        # lg:ml-5: from the colours' edge to where the page's text starts
        data_admin_search_row=True, cls="hidden lg:block lg:relative lg:w-80 lg:ml-5 [html[data-admin-search]_&]:block max-lg:fixed max-lg:top-12 "
            "max-lg:inset-x-0 max-lg:p-2 max-lg:bg-base-100 max-lg:border-b-[length:var(--border)] "
            "max-lg:border-base-300")


def AdminRail(settings):
    """On a wide screen the admin menu is a rail on the left, under the
    top bar (AdminTopBar); narrower, the bar's menu button opens it in a
    drawer."""
    return Div(
        # the menu scrolls its pages itself (AdminSidebar)
        Div(AdminSidebar(settings, in_margin=True, rail=True), cls="flex-1 min-h-0 flex flex-col p-3"),
        data_admin_rail=True, data_own_scroll=True,
        cls="hidden lg:flex flex-col fixed top-12 bottom-0 left-0 z-30 w-64 "
            "bg-base-100 border-r-[length:var(--border)] border-base-300 print:hidden")
