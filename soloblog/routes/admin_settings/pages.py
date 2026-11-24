"""Putting the Settings pages together: which panels make a page, what's shown
as changed, the search over them and the page itself."""
import os
from urllib.parse import quote
from fasthtml.common import *
from soloblog import csp
from soloblog import settings
from soloblog import mail
from soloblog import backup
from soloblog import captcha
from soloblog import updates
from soloblog import translate
from soloblog import posts
from soloblog import i18n
from soloblog.ui import Layout, SECTION_GAP, MediaPickerDialog, LinkPickerDialog, SaveBar, PageHeader, SetUpFirst, EMAIL_SETUP
from soloblog.routes.welcome import ShowGettingStartedForm
from soloblog.ui import SETTINGS_SECTIONS as TABS
from soloblog.routes.admin_settings.base import DESIGN_PREVIEW_JS, DESIGN_SAVED_JS, SettingsNav, TOOLBAR_ORDER_JS, ar
from soloblog.routes.admin_settings.design import (
    DESIGN_BODY, DESIGN_TABS, DesignPreview, DesignPreviewButton, OwnThemeForms, PresetsPanel, _design_form,
    _extras_of,
)
from soloblog.routes.admin_settings.panels import (
    BannerTab, ENV_VARS, EditorTab, GeneralPanels, MembersTab, ProfileTab, ReaderPanels, SecretPanels, SitePanels,
    SpamNote,
)
from soloblog.routes.admin_settings.integrations import ApiKeysPanel, WebhooksPanel, YourEmailPanel


# ---- the pages (ui.SETTINGS_GROUPS): each takes its panels from the
# forms in the other files by key, a few at a time, and saves where they
# always have

def _panels(*forms) -> dict:
    """The SettingsPanels in these forms, by key."""
    return {p.attrs["data-panel"]: p for form in forms
            for p in _find(form, lambda n: n.tag == "details" and n.attrs.get("data-panel"))}


def SettingsForm(action, *panels):
    """A settings page's form: switches and choices save as they change
    (AUTOSAVE_JS), what's typed with Save."""
    from soloblog import presets
    _mark_changed(panels, presets.baseline())
    return Form(
        Div(*panels, cls=f"flex flex-col gap-3 {SECTION_GAP}"),
        SaveBar(),
        hx_post=action, hx_target="#save-status", hx_swap="outerHTML show:none focus-scroll:false",
        data_declare_fields=True, data_autosave=True
    )


def _mark_changed(panels, base):
    """Every switch, choice and tick list that has a default: its value by
    default (the starting style's, or Soloblog's) on each of its inputs,
    for CUSTOM_TAGS_JS to show a bar while it differs, with Reset - the same
    row as Post settings. What's typed has no default to mark."""
    from soloblog.ui import CHANGED_BAR, ResetButton, _descendants

    def choices(node):
        return [c for c in _descendants(node.children) if getattr(c, "tag", "") == "select" or
                (getattr(c, "tag", "") == "input" and c.attrs.get("type") in ("checkbox", "radio"))]

    def visit(node):
        if not hasattr(node, "tag"):
            return False
        found = False
        for child in node.children:
            found = visit(child) or found
        if found or node.tag != "fieldset":
            return found
        inputs = choices(node)
        names = {c.attrs.get("name") for c in inputs}
        if len(names) != 1 or next(iter(names)) not in base:
            return False
        name = names.pop()
        value = str(base[name] or "")
        # empty is Soloblog's usual set there, as the page reads it
        ticks = sorted(_extras_of(value)) if name == "post_shows" else value.split(",")
        switch = len(inputs) == 1 and inputs[0].attrs.get("type") == "checkbox"
        for el in inputs:
            if el.tag == "select" or el.attrs.get("type") == "radio":
                el.attrs["data-default-value"] = value
            elif switch:
                el.attrs["data-default-value"] = "1" if value not in ("", "0") else "0"
            else:  # one tick of a list: in what the default ticks, or not
                el.attrs["data-default-value"] = "1" if str(el.attrs.get("value")) in ticks else "0"
        node.attrs["data-custom-field"] = True
        node.attrs["class"] = CHANGED_BAR + " " + node.attrs.get("class", "").replace("p-0", "").strip()
        reset = ResetButton(default_label=("On" if value not in ("", "0") else "Off") if switch else "")
        if switch:
            # beside the switch, inside its label - pressing a button there
            # doesn't turn the switch
            row = next(c for c in _descendants(node.children)
                       if getattr(c, "tag", "") == "label" and inputs[0] in c.children)
            # the label names its switch: left to itself it takes the first
            # control inside it, which is now Reset - the words reset the
            # setting and never turned it on
            inputs[0].attrs.setdefault("id", f"sw-{name}")
            row.attrs["for"] = inputs[0].attrs["id"]
            at = row.children.index(inputs[0])
            # right beside the switch, the two on one line
            inputs[0].attrs["class"] = inputs[0].attrs.get("class", "").replace(" mt-0.5", "")
            group = Span(reset, inputs[0], cls="flex items-center gap-1 shrink-0 min-h-6")
            row.children = (*row.children[:at], group, *row.children[at + 1:])
        else:
            legend = next((c for c in node.children if getattr(c, "tag", "") == "legend"), None)
            if legend is not None:
                legend.children = (*legend.children, reset)
                legend.attrs["class"] = legend.attrs.get("class", "") + " w-full flex items-center gap-1.5"
            else:
                node.children = (reset, *node.children)
        return True

    for p in panels:
        visit(p)


def _together(panel):
    """A group whose fields only work together - a service and its key,
    a palette pair - saved with Save, not as each changes."""
    panel.attrs["data-autosave-off"] = "1"
    return panel


def _open_link(word="Edit"):
    """What opens a folded group, beside how it stands - the same on every
    one that starts folded, set up once or Advanced."""
    return Span(word, cls="text-xs font-normal link shrink-0 group-open:hidden")


# folded groups there's nothing to change in - what's set on the host
_READ_ONLY = {"integrations-env"}


def _setup(panel, state):
    """Something set up once (Ghost's pattern): closed, one row - its
    name, how it's set up now, and Edit; open, its fields, saved
    together with Save."""
    _with_state(panel, state, _open_link())
    panel.attrs.pop("open", None)
    return _together(panel)


def _with_state(panel, state, *after):
    """A section's heading with how it stands beside it - "Off", "2 keys" -
    so a folded one says what's inside without opening it. Open, its
    fields say it, so it goes, as Edit does."""
    summary = panel.children[0]
    summary.children = (Span(*summary.children, cls="shrink-0", data_panel_title=True),
                        Span(state, data_panel_state=True,
                             cls="ml-auto min-w-0 truncate text-xs font-normal text-base-content/60 group-open:hidden"),
                        *after)
    summary.attrs["class"] = summary.attrs.get("class", "") + " flex items-center gap-3 pe-10"
    panel.attrs["class"] = panel.attrs.get("class", "") + " group"
    return panel


def _folded_states(s) -> dict:
    """How each section that starts folded stands, by its key."""
    def count(n, one, many, none):
        return f"{n} {one if n == 1 else many}" if n else none
    redirects = [line for line in (s.get("redirects") or "").splitlines() if line.strip()]
    verified = [n for n, k in (("Google", "google_site_verification"), ("Bing", "bing_site_verification")) if s.get(k)]
    code = [n for n, k in (("code", "custom_head"), ("CSS", "custom_css")) if (s.get(k) or "").strip()]
    host = sum(1 for name, _ in ENV_VARS if os.environ.get(name))
    from soloblog import apikeys, webhooks
    return {
        "url-redirects": count(len(redirects), "redirect", "redirects", "None"),
        "url-verify": " and ".join(verified) or "Not set",
        "style-motion": "Animations on" if s.get("page_animations") == "1" else "Animations off",
        "posts-milestones": {"left": "Line on the left", "center": "Line in the middle",
                                  "right": "Line on the right"}.get(s.get("milestones_align"), ""),
        "header-app": "Your own icon" if s.get("app_icon_url") else "Your favicon",
        "sharing-webmentions": "On" if s.get("webmention_receive") == "1" else "Off",
        "integrations-code": "Your " + " and ".join(code) if code else "Nothing added",
        "integrations-env": count(host, "set on your host", "set on your host", "None set on your host"),
        "integrations-apikeys": count(len(apikeys.listed()), "key", "keys", "No keys"),
        "integrations-webhooks": count(len(webhooks.listed()), "webhook", "webhooks", "No webhooks"),
    }

def Advanced(*panels):
    """The rarely changed ones, at the foot of a page, closed - each with
    how it stands beside its name."""
    states = _folded_states(settings.get_all())
    for p in panels:
        p.attrs.pop("open", None)
        key = p.attrs.get("data-panel")
        if key in states:
            _with_state(p, states[key], _open_link("Show" if key in _READ_ONLY else "Edit"))
    return Div(P("Advanced", cls="text-xs font-semibold text-base-content/60 px-1 mt-3"), *panels,
               cls="flex flex-col gap-3")


def _states(s) -> dict:
    """How each set-up group stands, for its summary row."""
    from soloblog import stripe_members
    host = mail.smtp_server()[0]
    email = {"smtp": f"SMTP · {host}" if host else "SMTP", "api": "Resend"}
    names = {"cloudflare": "Cloudflare", "plausible": "Plausible", "google": "Google Analytics"}
    langs = translate.targets(s)
    return {
        "analytics": (names.get(s["analytics_provider"], "Off")
                      + (f" · {s['analytics_id']}" if s["analytics_id"] and s["analytics_provider"] else "")),
        "ads": "AdSense" if s["adsense_client"] else "Off",
        "captcha": captcha.PROVIDERS[s["captcha_provider"]][0] if s["captcha_provider"] in captcha.PROVIDERS
        else "Off",
        "email": email.get(s["email_provider"], "Off"),
        "bluesky": (s["bluesky_handle"] or "On") if s["crosspost_bluesky"] == "1" else "Off",
        "mastodon": (s["mastodon_instance"].removeprefix("https://") or "On") if s["crosspost_mastodon"] == "1"
        else "Off",
        "updates": "Set up" if s["update_hook_url"] else "Not set up",
        "stock": ", ".join(n for n, k in (("Pixabay", "pixabay_api_key"), ("Pexels", "pexels_api_key"),
                                          ("Unsplash", "unsplash_access_key")) if s[k]) or "No keys",
        "paid": ("Not set up" if not s.get("stripe_key") else "Test mode" if "_test_" in s["stripe_key"]
                 else "Live" if stripe_members.ready(s) else "Not finished"),
        "translation": (f"{translate.PROVIDERS.get(s['translate_provider'], s['translate_provider'])}"
                        f" · {len(langs)} language{'s' if len(langs) != 1 else ''}")
                       if translate.enabled(s) else "Off",
    }


def _pages(s):
    """Each settings page, built when it's asked for."""
    # here, not at the top: these modules import this one
    from soloblog.routes.backup_routes import BackupTab
    from soloblog.routes.security_routes import SecurityTab

    def general():
        p = _panels(GeneralPanels(s))
        # Open Getting started's own form, outside the settings' (welcome.GettingStartedLink) -
        # in one box with them: the search's index reads a page as one piece
        return Div(SettingsForm("/admin/settings/name", p["name-identity"], p["name-homepage"]),
                   ShowGettingStartedForm(s))

    def site():
        p = _panels(SitePanels(s))
        return SettingsForm("/admin/settings/url", p["url-site"], p["url-search"],
                            Advanced(p["url-verify"], p["url-redirects"]))

    def language():
        g, p = _panels(GeneralPanels(s)), _panels(SitePanels(s))
        return SettingsForm("/admin/settings/language", g["language-time"], p["language-site"],
                            _setup(p["language-translation"], _states(s)["translation"]))

    def design(page, *keys, advanced=()):
        p = _panels(_design_form(s))
        if "style-colours" in p:
            _together(p["style-colours"])
        return SettingsForm(f"/admin/settings/{page}", *[p[k] for k in keys],
                            Advanced(*[p[k] for k in advanced]) if advanced else None)

    def messages():
        g, v = _panels(GeneralPanels(s)), _panels(ReaderPanels(s))
        # blocked words, the alerts and the email notice are for either feature: they wait for one of the switches
        either = "comments_enabled=1;contact_enabled=1"
        off = s["comments_enabled"] != "1" and s["contact_enabled"] != "1"
        blocked, notify = g["messages-blocked"], v["messages-notify"]
        for panel in (blocked, notify):
            panel.attrs["data-shown-for"] = either
            if off:
                panel.attrs["hidden"] = True
        # once, at the top: both the reply emails and the alerts need it
        email = None if s["email_provider"] in ("smtp", "api") else Div(
            SetUpFirst("email", EMAIL_SETUP), data_shown_for=either, hidden=off or None)
        return SettingsForm("/admin/settings/messages", email, g["messages-comments"],
                            _together(v["messages-contact"]), blocked, notify, SpamNote())

    def readers(page, *keys, after=None):
        v = _panels(ReaderPanels(s))
        return SettingsForm(f"/admin/settings/{page}", *[_together(v[k]) for k in keys], after)

    def security():
        # the Security cards save on their own, so this one has its own bar -
        # and its status goes to its own form, not the Password card's
        spam = SettingsForm("/admin/settings/security",
                            _setup(_panels(ReaderPanels(s))["security-spam"], _states(s)["captcha"]))
        spam.attrs["hx-target"] = "find #save-status"
        return Div(SecurityTab(), spam, cls="flex flex-col gap-3")

    def analytics():
        v, st = _panels(ReaderPanels(s)), _states(s)
        return SettingsForm("/admin/settings/analytics", _setup(v["analytics-main"], st["analytics"]),
                            v["analytics-consent"], _setup(v["analytics-ads"], st["ads"]))

    def sharing():
        p = _panels(SitePanels(s))
        st = _states(s)
        return SettingsForm("/admin/settings/sharing", p["sharing-main"], _setup(p["sharing-bluesky"], st["bluesky"]),
                            _setup(p["sharing-mastodon"], st["mastodon"]), p["sharing-fediverse"],
                            Advanced(p["sharing-webmentions"]))

    def members():
        p = _panels(MembersTab(s))
        return SettingsForm("/admin/settings/members", p["members-on"],
                            _setup(p["members-paid"], _states(s)["paid"]))

    def email():
        # everything about email on one page: where it comes to you, and
        # how the site sends it
        p = _panels(SecretPanels(s))
        return SettingsForm("/admin/settings/email", YourEmailPanel(s), _setup(p["email-sending"], _states(s)["email"]))

    def integrations():
        p, st = _panels(SecretPanels(s)), _states(s)
        # Custom code: on every page, from you - with the other things wired
        # in, not under Search engines (SitePanels draws it)
        code = _panels(SitePanels(s))["integrations-code"]
        folded = _folded_states(s)
        return Div(_with_state(ApiKeysPanel(), folded["integrations-apikeys"], _open_link()),
                   _with_state(WebhooksPanel(), folded["integrations-webhooks"], _open_link()),
                   SettingsForm("/admin/settings/integrations", _setup(p["integrations-stock"], st["stock"]),
                                _setup(p["integrations-updates"], st["updates"]), Advanced(code, p["integrations-env"])),
                   cls="flex flex-col gap-3")

    def editor():
        return autosaving(EditorTab(s))

    def autosaving(form):
        # saves as it changes, and marks what differs, as SettingsForm does
        from soloblog import presets
        form.attrs["data-autosave"] = "1"
        _mark_changed([form], presets.baseline())
        return form

    return {
        "name": general, "url": site, "language": language,
        # Custom colours' dialogs and delete forms sit outside the Style
        # form: forms can't nest, and the list's buttons inside it name them (form=)
        "style": lambda: Div(PresetsPanel(s), design("style", "style-colours", "style-fonts",
                                                               advanced=("style-motion",)),
                                  *OwnThemeForms(s), cls="flex flex-col gap-3"),
        "blog": lambda: design("blog", "blog-layout", "blog-side"),
        "posts": lambda: design("posts", "posts-shows", "posts-breadcrumbs", "posts-reading",
                                    "posts-contents", "posts-images",
                                    advanced=("posts-milestones",)),
        "header": lambda: design("header", "header-width", "header-bar", "header-footer",
                                     "header-icons", advanced=("header-app",)),
        "banner": lambda: autosaving(BannerTab(s)),
        "profile": lambda: autosaving(ProfileTab(s)),
        "messages": messages,
        "newsletter": lambda: readers("newsletter", "newsletter-main"),
        "members": members,
        "analytics": analytics,
        "sharing": sharing,
        "editor": editor,
        "email": email,
        "integrations": integrations,
        "security": security,
        "backup": BackupTab,
    }


def _tab_builders(s):
    return _pages(s)





# ---- searching Settings and Help (ui.AdminSearch): an index of what's
# there, made from the pages themselves, so it can't fall out of step

_SKIP_TEXT = {"script", "style", "svg", "select", "option", "textarea", "input", "kbd", "template", "dialog"}


def _text(node) -> str:
    """The words a reader sees in an FT tree - not icons, scripts or
    form values."""
    from fastcore.xml import FT
    if isinstance(node, str):
        return "" if type(node).__name__ == "NotStr" else node
    if not isinstance(node, FT) or node.tag in _SKIP_TEXT:
        return ""
    return " ".join(t for t in (_text(c) for c in node.children) if t.strip())


def _find(node, test):
    from fastcore.xml import FT
    if not isinstance(node, FT):
        return []
    found = [node] if test(node) else []
    for c in node.children:
        found += _find(c, test)
    return found


# the words people search for that a setting's own name doesn't use
SEARCH_ALSO = {
    "Colors": "theme themes colour scheme dark mode light mode",
    "Settings presets": "preset look style theme", "Templates": "template outline start from",
    "Light palette": "theme light mode colour", "Dark palette": "theme dark mode night colour",
    "Visitors see": "theme dark mode light mode", "Let readers pick other colors": "theme switcher",
    "Time zone": "timezone date time clock", "Your homepage shows": "front page home page landing",
    "Header icon": "logo", "Favicon": "logo icon browser tab", "App icon": "logo icon phone home screen",
    "Text font": "typeface typography", "Heading font": "typeface typography", "Text size": "font size bigger",
    "Site title": "name blog name", "Custom code": "css javascript script analytics head html",
    "Analytics": "stats tracking visitors google plausible",
    "Notifications": "email alerts slack discord webhook new comment message", "Redirects": "old links moved 301",
    "Site URL": "address web address domain base_url", "Search engines": "seo google", "Collapsible headings": "fold folding accordion",
    "Collapsible contents": "fold folding table of contents",
}

_index_cache = {}


def _cached(key, make):
    """One copy of an index until what it's made from changes."""
    if _index_cache.get(key[0], (None,))[0] != key:
        _index_cache[key[0]] = (key, make())
    return _index_cache[key[0]][1]


def settings_index(s=None) -> list:
    """Every setting - its section, panel, name and help - and every panel,
    for the search box over Settings."""
    from soloblog import cache
    return _cached(("settings", cache.generation(), i18n.british()), lambda: _settings_index(s))


def _settings_index(s=None) -> list:
    s = s or settings.get_all()
    tabs = dict(TABS)
    entries = []
    for tab, build in _tab_builders(s).items():
        # the page itself: searching its name finds it once, on top
        # (index_search.js) - unless a panel on it has that name
        page_at = len(entries)
        entries.append({"group": tabs[tab], "title": tabs[tab], "sub": "", "text": "",
                        "href": f"/admin/settings?tab={tab}", "words": ""})
        for panel in _find(build(), lambda n: n.tag == "details" and n.attrs.get("data-panel")):
            key = panel.attrs["data-panel"]
            summary = next(iter(_find(panel, lambda n: n.tag == "summary")), None)
            # a set-up row's summary also says how it stands (_setup) - just its name
            named = _find(summary, lambda n: n.attrs.get("data-panel-title")) if summary is not None else []
            title = " ".join(_text(named[0] if named else summary).split())
            href = f"/admin/settings?tab={tab}&panel={key}"
            # every word in the panel finds it, for what isn't a named field (the palettes' swatches)
            entries.append({"group": tabs[tab], "title": title, "sub": "", "text": "", "href": href,
                            "words": f"{SEARCH_ALSO.get(title, '')} {' '.join(_text(panel).split())[:3000]}"})
            for field in _find(panel, lambda n: n.tag == "fieldset"):
                legend = next(iter(_find(field, lambda n: n.tag == "legend")), None)
                helps = _find(field, lambda n: "fieldset-label" in str(n.attrs.get("class", "")))
                if legend is not None:
                    name = _text(legend)
                else:
                    spans = _find(field, lambda n: n.tag == "span" and "font-medium" in str(n.attrs.get("class", "")))
                    name = _text(spans[0]) if spans else ""
                    helps = _find(field, lambda n: n.tag == "span" and "text-xs" in str(n.attrs.get("class", "")))
                name = " ".join(name.split())
                if not name or name == title:
                    continue
                options = " ".join(c for o in _find(field, lambda n: n.tag == "option") for c in o.children
                                   if isinstance(c, str))
                entries.append({"group": tabs[tab], "title": name, "sub": title,
                                "text": " ".join(" ".join(_text(h) for h in helps).split()),
                                "words": f"{options} {SEARCH_ALSO.get(name, '')}", "href": f"{href}&setting={quote(name)}"})
        if any(e["title"] == tabs[tab] for e in entries[page_at + 1:]):
            del entries[page_at]
    return entries


@ar.get("/admin/settings/search-index")
def settings_search_index(session):
    return JSONResponse(settings_index(), headers={"Cache-Control": "private, no-store"})


@ar.get("/admin/settings")
def settings_page(session, tab: str = "name", q: str = ""):
    backup.staged_restore()  # a day-old upload goes, whichever tab this is
    s = settings.get_all()
    if tab not in dict(TABS):
        tab = "name"

    # only the open tab is built
    panels = _tab_builders(s)

    return Layout(
        PageHeader(f"Settings: {dict(TABS)[tab]}", SettingsHelpLink(tab)),
        Div(SettingsNav(tab), panels[tab](), id="settings-body") if tab not in DESIGN_TABS else
        # a Design page: its controls, and Preview to see the site as they stand
        Div(SettingsNav(tab), DesignPreviewButton(tab), panels[tab](),
            id="settings-body", cls=DESIGN_BODY),
        DesignPreview(tab) if tab in DESIGN_TABS else None,
        Script(DESIGN_PREVIEW_JS, nonce=csp.NONCE) if tab in DESIGN_TABS else None,
        MediaPickerDialog(s) if tab in ("header", "profile", "banner", "sharing") else None,
        LinkPickerDialog() if tab in ("banner", "analytics", "name", "style") else None,
        # Clicking a palette previews it on this page (theme-change, under
        # its own "admin-preview" key - never a reader's). It's cleared
        # before theme-change loads, which would otherwise reopen the page
        # on the last palette tried rather than the saved one, and again
        # when a save reloads the page (DESIGN_SAVED_JS).
        Script("localStorage.removeItem('admin-preview');", nonce=csp.NONCE) if tab == "style" else None,
        Script(DESIGN_SAVED_JS, nonce=csp.NONCE) if tab == "style" else None,
        Script(src="/static/vendor/theme-change-2.5.0.js", nonce=csp.NONCE) if tab == "style" else None,
        Script(TOOLBAR_ORDER_JS, nonce=csp.NONCE) if tab == "editor" else None,
        settings=s, logged_in=True, pinned_tree=posts.list_pinned_tree(), admin_page=True
    )


def settings_help(tab) -> str:
    """Where Help explains this settings page: the reference's ## of the
    same name (a test checks every one is there)."""
    from markdown.extensions.toc import slugify
    return f"/admin/help?tab=reference#{slugify(dict(TABS)[tab], '-')}"


def SettingsHelpLink(tab):
    return A("Help", href=settings_help(tab), cls="btn btn-ghost btn-sm")


@ar.post("/admin/update")
def update_now(session, request):
    if not updates.trigger(settings.get_all()):
        return Span("Set up updates first, in Integrations", cls="text-error")
    return Span("Updating - reload in a minute or two", cls="text-success")
