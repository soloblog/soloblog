"""Saving a Settings page: each page's table of fields, how each field is
cleaned, and the handler that stores it."""
import json
import re
from fasthtml.common import *
from soloblog import auth
from soloblog import config
from soloblog import editor_config
from soloblog import settings
from soloblog import ratelimit
from soloblog import mail
from soloblog import captcha
from soloblog import extcomments
from soloblog import fonts
from soloblog import newsletter
from soloblog import reactions
from soloblog import translate
from soloblog import posts
from soloblog import tz
from soloblog import formservices
from soloblog import ads
from soloblog import gallery
from soloblog import pages
from soloblog import post_templates
from soloblog.formservices import FORWARDERS
from soloblog.render import embed_url
from soloblog.themes import THEME_MODES, all_choices, dark_choices
from soloblog import i18n
from soloblog.ui import SIDE_WHERE, SIDE_KEYS
from soloblog.ui import (
    SaveStatus, ordered_social_platforms, safe_url, SIDE_PLACES, HEADER_ALIGNS, HEADER_WIDTHS, FOOTER_LAYOUTS,
    ROLL_PARTS, LIST_COVER_SIDES, MINIMAL_GROUPS, TIMELINE_ALIGNS, footer_order as footer_order_of,
    side_order as side_order_of,
)
from soloblog.routes.admin_settings.base import ANALYTICS_ID_RE, ANALYTICS_PROVIDERS, VERIFICATION_RE, ar

CARDS_PER_ROW = {"3": "Three", "2": "Two", "1": "One - each post large, its image behind its text"}


def _register_saves():
    """Each settings page saves to its own address, as its link is named:
    /admin/settings/<page> - to the handler that knows its fields (some
    serve several pages, which share their groups of fields)."""
    for page, handler in {"name": save_general, "messages": save_general, "newsletter": save_general,
                          "security": save_general, "analytics": save_general,
                          "url": save_site, "language": save_site, "sharing": save_site,
                          "style": save_design, "blog": save_design, "posts": save_design, "header": save_design,
                          "banner": save_banner, "profile": save_profile, "members": save_members,
                          "editor": save_editor, "email": save_secrets, "integrations": save_secrets}.items():
        ar.post(f"/admin/settings/{page}")(handler)


def _home_page(kind, slug) -> str:
    """Settings > Name and homepage > Homepage, as saved: "" for the posts, the
    wiki's own value, or a page that exists."""
    if kind == "posts":
        return ""
    if kind == "wiki" or (kind is None and slug == posts.WIKI_HOME):
        return posts.WIKI_HOME
    if kind == "page" and not slug:
        # chosen, but no page picked yet - the homepage stays a page it already is
        current = settings.get("home_page")
        return current if current != posts.WIKI_HOME and posts.get_post(current or "") else ""
    return slug if slug and posts.get_post(slug) else ""


# How a form's value becomes the stored one. Each takes the form and the
# setting's name; anything not allowed is the setting's default
# (settings.DEFAULTS), so a stray or old value can't be saved.
def flag(form, key):
    """A switch: "1" when it's on (a ticked box sends its value), "0" when not."""
    return "1" if form.get(key) else "0"


def one_of(options):
    """One of options - a list, a dict's keys, or a function giving them (when
    they're only known later, like the fonts)."""
    def clean(form, key):
        value = form.get(key) or ""
        return value if value in (options() if callable(options) else options) else settings.DEFAULTS[key]
    return clean


def _shows_on_cleared(form, where_key, where_options):
    # its Shows on ticks were in the form, and none was ticked
    return where_key in (form.get("declared_fields") or "").split(",") and \
        not some_of(where_options)(form, where_key)


def placed(options, where_options):
    """Where something goes, with its Shows on ticks (a side panel, the
    contents): Off when every tick is cleared, so the two never mean the
    same thing apart."""
    def clean(form, key):
        return "off" if _shows_on_cleared(form, f"{key}_where", where_options) else one_of(options)(form, key)
    return clean


def shows_on(where_options):
    """Its Shows on ticks - back to the usual when every one is cleared
    (it's Off then), so choosing a place again has some ticked."""
    def clean(form, key):
        return settings.DEFAULTS[key] if _shows_on_cleared(form, key, where_options) else \
            some_of(where_options)(form, key)
    return clean


def some_of(options, empty="", in_form_order=False):
    """Ticked boxes, in options' order - or the order they came in, where
    you arrange them (reactions) - and empty when none are ticked."""
    def clean(form, key):
        allowed = options() if callable(options) else options
        chosen = form.getlist(key)
        kept = [k for k in chosen if k in allowed] if in_form_order else [k for k in allowed if k in chosen]
        return ",".join(dict.fromkeys(kept)) or empty
    return clean


def text(limit=None):
    """Typed text, trimmed - to limit characters, if given."""
    return lambda form, key: (form.get(key) or "").strip()[:limit]


def ordered(order_of):
    """A drag-ordered list (ui.SortableList), cleaned by the function that
    reads it back (footer_order, side_order)."""
    return lambda form, key: ",".join(order_of({key: form.get(key) or ""}))


def matching(pattern):
    """Typed text in a strict shape (a regex), or empty."""
    def clean(form, key):
        value = (form.get(key) or "").strip()
        return value if re.fullmatch(pattern, value) else ""
    return clean


def checked(test):
    """Typed text that test() accepts, otherwise empty."""
    def clean(form, key):
        value = (form.get(key) or "").strip()
        return value if test(value) else ""
    return clean


def cleaned(fn):
    """Typed text, through fn - which makes it safe, or empty."""
    return lambda form, key: fn(form.get(key) or "")


def _posts_per_page(form, key):
    value = form.get(key) or ""
    return value if value.isdigit() and 1 <= int(value) <= 100 else settings.DEFAULTS[key]


def secret(inner=None):
    """A key, password or token (ui.SecretInput): left empty, the saved one
    stays - the page never had it; with its "Remove" ticked, it goes."""
    def clean(form, key):
        if form.get(f"{key}__remove"):
            return ""
        if not (form.get(key) or "").strip():
            # the saved one - not the host's, which isn't ours to copy into the site
            return settings.stored(key)
        return inner(form, key) if inner else (form.get(key) or "").strip()
    return clean


def upload(form, key):
    """One of your uploads (an address starting /uploads/), or empty."""
    value = (form.get(key) or "").strip()
    return value if value.startswith("/uploads/") else ""


def clean_form(form, fields, declared=None) -> dict:
    """The stored values for what a form sent: only the fields it declares
    (declared_fields, so one switch changing saves just that switch), or
    every one of them when it doesn't say (a script posting the whole form)."""
    declared = form.get("declared_fields") if declared is None else declared
    names = [n for n in declared.split(",") if n in fields] if declared is not None else list(fields)
    return {name: fields[name](form, name) for name in names}


# Settings > Name and homepage, Comments and messages, Newsletter, and
# Analytics and ads - one form each, saved here
GENERAL_FIELDS = {
    "site_title": lambda form, key: (form.get(key) or "").strip() or "My Blog", "tagline": text(),
    "timezone": one_of(lambda: tz.zone_names()),
    "home_page": lambda form, key: _home_page(form.get("home_kind"), form.get("home_page") or ""),
    "home_page_shows": some_of(lambda: posts.HOME_EXTRAS),
    # Comments
    "comments_enabled": flag, "reply_emails": flag, "comments_autoload": flag, "notify_comments": flag,
    "comment_webhook_url": text(),
    "comments_system": one_of(lambda: extcomments.SYSTEMS),
    **{key: cleaned(lambda value, key=key: extcomments.clean(key, value))
       for key in ("giscus_repo", "giscus_repo_id", "giscus_category", "giscus_category_id", "bluesky_handle",
                   "isso_url", "remark42_url", "remark42_site_id")},
    "comment_blocklist": cleaned(lambda value: "\n".join(w.strip() for w in value.splitlines() if w.strip())[:5000]),
    "captcha_provider": one_of(lambda: captcha.PROVIDERS),
    "captcha_site_key": checked(lambda v: captcha.KEY_RE.match(v)),
    "captcha_secret": secret(checked(lambda v: captcha.KEY_RE.match(v))),
    # Newsletter
    "newsletter_mode": one_of(lambda: ("builtin", *newsletter.SERVICES)),
    **{f"newsletter_{name}": checked(lambda v, name=name: newsletter.SERVICES[name][2].match(v))
       for name in ("buttondown", "kit", "mailchimp", "substack")},
    "newsletter_title": text(100), "newsletter_intro": text(300),
    "newsletter_auto": flag, "newsletter_digest": one_of(("", "week", "month")), "newsletter_full": flag, "newsletter_on_home": flag,
    # Contact form
    "contact_enabled": flag, "contact_intro": text(), "contact_email": text(),
    "contact_mode": one_of(("builtin", "embed")), "contact_service": one_of(lambda: FORWARDERS),
    "contact_service_id": text(), "contact_form_url": checked(lambda v: embed_url(v)),
    # Analytics and ads - all dropped into script tags and ads.txt, so only their exact shapes
    "analytics_provider": one_of(lambda: ANALYTICS_PROVIDERS),
    "analytics_id": checked(lambda v: ANALYTICS_ID_RE.match(v)),
    "consent_banner": flag, "consent_message": text(), "consent_privacy_url": cleaned(safe_url),
    "adsense_client": checked(lambda v: ads.valid_client(v)),
    "adsense_slot_post": checked(lambda v: ads.SLOT_RE.match(v)),
    "adsense_slot_roll": checked(lambda v: ads.SLOT_RE.match(v)),
    "adsense_on_pages": flag,
}


async def save_general(request):
    form = await request.form()
    declared = form.get("declared_fields")
    # the homepage's kind and its page are one setting
    if declared is not None and "home_kind" in declared.split(","):
        declared += ",home_page"
    names = declared.split(",") if declared is not None else None
    values = clean_form(form, GENERAL_FIELDS, declared)
    mode = values.get("newsletter_mode")
    # switching on automatic sending: what's already live counts as sent,
    # so subscribers aren't sent the whole back catalogue
    before = settings.get_all()
    if mode == "builtin" and form.get("newsletter_auto") and not (newsletter.sending(before) or newsletter.digest(before)):
        from soloblog import publishing
        publishing.baseline("newsletter")
    settings.set_declared(declared, values)
    # a switch among "Each post shows" (pages.EXTRAS), set on the Newsletter page
    if names is None or "newsletter_on_posts" in names:
        pages.show_on_posts("newsletter", bool(form.get("newsletter_on_posts")))
    # what was typed and couldn't be kept, then what's now saved - with
    # one field saving on its own, the rest come from what was there
    typed = lambda key: (form.get(key) or "").strip()  # noqa: E731
    now = settings.get_all()
    if typed("adsense_client") and not values.get("adsense_client"):
        return SaveStatus("Saved - but a publisher ID looks like ca-pub- and 16 digits", "error")
    if mode in newsletter.SERVICES and not now[f"newsletter_{mode}"]:
        return SaveStatus(f"Saved - but that {newsletter.SERVICES[mode][1].lower()} doesn't look right, so the "
                          "newsletter stays off", "error")
    system = values.get("comments_system")
    if system in extcomments.SYSTEMS:
        label = extcomments.SYSTEMS[system][0]
        if any(typed(k) and not values.get(k) for k in extcomments.SYSTEMS[system][3]):
            return SaveStatus(f"Saved - but a {label} field doesn't look right, so it was left empty", "error")
        if not extcomments.system(settings.get_all()):
            return SaveStatus(f"Saved - but posts keep Soloblog's own comments until {label} is filled in", "error")
    spam_check = ("captcha_provider", "captcha_site_key", "captcha_secret")
    if any(k in values for k in spam_check) and now["captcha_provider"] and not (now["captcha_site_key"] and now["captcha_secret"]):
        return SaveStatus("Saved - but the spam check stays off until both keys are in", "error")
    if values.get("contact_mode") == "embed" and not now["contact_form_url"]:
        return SaveStatus("Saved - but that form link isn't one Soloblog can embed", "error")
    service = values.get("contact_service")
    if service and not formservices.valid_id(service, now["contact_service_id"]):
        return SaveStatus("Saved - but that doesn't look like a form ID for " + FORWARDERS[service][0], "error")
    return SaveStatus("Saved")


def _fediverse_name(form, key):
    # @name@your-site - can't be left blank, so a bad one keeps the old
    from soloblog import fediverse
    value = (form.get(key) or "").strip()
    return value if fediverse.USERNAME_RE.match(value) else settings.get(key)


# Settings > URL and SEO, Language and time, Sharing, and Integrations >
# Custom code - one form each, saved here
SITE_FIELDS = {
    "timezone": one_of(lambda: tz.zone_names()),
    "site_language": one_of(lambda: translate.LANGUAGES), "english_spelling": one_of(lambda: i18n.ENGLISH),
    "translate_provider": one_of(lambda: translate.PROVIDERS), "translate_api_key": secret(),
    "translate_url": checked(lambda v: v.startswith(("https://", "http://"))),
    "translate_languages": some_of(lambda: translate.LANGUAGES, in_form_order=True),
    "google_site_verification": checked(lambda v: VERIFICATION_RE.match(v)),
    "bing_site_verification": checked(lambda v: VERIFICATION_RE.match(v)),
    "search_noindex": flag, "meta_description": text(), "share_image_url": upload,
    "redirects": cleaned(lambda v: "\n".join(f"{a} {b}" for a, b in posts.parse_redirects(v))),
    "activitypub_enabled": flag, "activitypub_username": _fediverse_name,
    "webmention_receive": flag, "webmention_send": flag, "webmention_moderate": flag,
    "crosspost_bluesky": flag, "bluesky_handle": cleaned(lambda v: extcomments.clean("bluesky_handle", v)),
    "bluesky_app_password": secret(matching(r"[\w-]{0,100}")),
    "crosspost_mastodon": flag,
    "mastodon_instance": cleaned(lambda v: v.strip().rstrip("/") if re.fullmatch(r"https://[\w.-]+(:\d+)?",
                                                                              v.strip().rstrip("/")) else ""),
    "mastodon_token": secret(matching(r"[\w-]{0,200}")),
}


async def save_site(request):
    form = await request.form()
    site_url = form.get("site_url")
    # the demo's own address isn't for a visitor to change (demo.LOCKED_SETTINGS)
    if site_url is not None and not config.BASE_URL_FIXED and not config.DEMO_MODE:
        address = settings.clean_site_url(site_url)
        if site_url.strip() and not address:
            return SaveStatus("The site URL is just https:// and the domain, like https://example.com",
                              "error")
        settings.set_many({"site_url": address})
        settings.use_site_url(address)
    from soloblog import publishing
    values = clean_form(form, SITE_FIELDS)
    before = settings.get_all()
    # turning announcing or sharing on: what's already live counts as done, so
    # followers, linked sites and Bluesky or Mastodon aren't flooded with the
    # back catalogue
    for switch, channel in (("activitypub_enabled", "activitypub"), ("webmention_send", "webmention"),
                            ("crosspost_bluesky", "bluesky"), ("crosspost_mastodon", "mastodon")):
        if values.get(switch) == "1" and before[switch] != "1":
            publishing.baseline(channel)
    settings.set_declared(form.get("declared_fields"), values)
    now = settings.get_all()
    typed = lambda key: (form.get(key) or "").strip()  # noqa: E731
    if values.get("crosspost_bluesky") == "1" and not (now["bluesky_handle"] and now["bluesky_app_password"]):
        return SaveStatus("Saved - but Bluesky needs its handle and an app password", "error")
    if values.get("crosspost_mastodon") == "1" and not (now["mastodon_instance"] and now["mastodon_token"]):
        return SaveStatus("Saved - but Mastodon needs its server's https:// URL and an access token", "error")
    if any(typed(k) and not values.get(k) for k in ("google_site_verification", "bing_site_verification")):
        return SaveStatus("Saved - but a verification code is only the content=\"...\" part", "error")
    if typed("share_image_url") and not values.get("share_image_url"):
        return SaveStatus("Saved - but the share image has to be one of your uploads", "error")
    return SaveStatus("Saved")


@ar.post("/admin/translate/all")
def translate_all(session):
    if not translate.enabled():
        return Span("Choose a service and at least one language, then save first.", cls="text-error")
    live = posts.list_all_published()
    for p in live:
        translate.queue_post(p["slug"])
    return Span(f"Translating {len(live)} post{'s' if len(live) != 1 else ''} in the background - reload "
                "this page to see progress.", cls="text-success")


def _port(fallback):
    """A port number, or fallback."""
    return cleaned(lambda v: v.strip() if v.strip().isdigit() else fallback)


# Settings > Email and Integrations: the services Soloblog talks to
SECRETS_FIELDS = {
    "email_provider": one_of(("", "smtp", "api")), "smtp_host": text(), "smtp_port": _port("587"),
    "smtp_user": text(), "smtp_password": secret(), "smtp_from": text(),
    "smtp_provider": one_of(lambda: ("", *mail.SMTP_PRESETS)),
    "email_api_key": secret(), "email_api_from": text(),
    # Admin email: checked as typed twice in save_secrets first
    "admin_email": text(), "signin_alerts": flag,
    # Custom code (Integrations; it was under Search engines)
    "custom_head": text(), "custom_head_consent": flag,
    # it goes inside a <style> - it mustn't be able to close it
    "custom_css": cleaned(lambda v: re.sub(r"</\s*style", "", v.strip(), flags=re.I)),
    "update_hook_url": checked(lambda v: v.startswith(("http://", "https://"))), "update_hook_token": secret(),
    "pixabay_api_key": secret(), "pexels_api_key": secret(), "unsplash_access_key": secret(),
}


async def save_secrets(request):
    form = await request.form()
    values = clean_form(form, SECRETS_FIELDS)
    if problem := _your_email(request, form, values):
        return SaveStatus(problem, "error")
    was = settings.get("admin_email")
    settings.set_declared(form.get("declared_fields"), values)
    _tell_old_address(was)
    return SaveStatus("Saved")


def _tell_old_address(was):
    """Password resets go to the admin email: the address they went to
    until now hears that they've moved."""
    now = settings.get("admin_email")
    if was and was.lower() != now.lower() and mail.can_send():
        title = settings.get("site_title")
        mail.send_email(was, f"The admin email for {title} was changed",
                        f"The admin email for {title} ({config.BASE_URL}) is now {now or 'empty'}. Password "
                        "resets and sign-in alerts no longer come to this address.\n\n"
                        "If you changed it, there's nothing to do.\n\n"
                        "If you didn't, log in, change your password and set the email back. "
                        f"Locked out? Use your recovery key:\n{config.BASE_URL}/forgot-password\n")


def _your_email(request, form, values) -> str:
    """The admin email, typed twice, and an address - checked before anything's
    saved, so a slip doesn't send password resets somewhere else - and
    changed only with the password, since whoever gets the resets has the
    site. Puts the tidied address in values; returns what's wrong, or ""."""
    if "admin_email" not in values:
        return ""
    if "admin_email" not in form:
        values.pop("admin_email")
        return ""
    typed = form.get("admin_email") or ""
    email = mail.clean_email(typed)
    if typed.strip() and not email:
        return "That email address isn't complete - check it"
    if email and mail.clean_email(form.get("admin_email_confirm") or "").lower() != email.lower():
        return "The email addresses don't match"
    # the first address needs none: there's no one yet to take it from
    was = settings.get("admin_email")
    if was and email.lower() != was.lower():
        if not form.get("current_password"):
            return "Enter your password to change the admin email"
        if not ratelimit.hit(f"ip:{ratelimit.client_ip(request)}", "confirm-password", limit=10, window_minutes=15):
            return "Too many attempts. Try again in a few minutes"
        if not auth.verify_password(form.get("current_password")):
            return "That password isn't right"
    values["admin_email"] = email
    return ""


# Settings > Appearance > Text size - the percentages are in input.css
FONT_SIZES = {"small": "Small", "medium": "Medium", "large": "Large"}


# Every setting the Design pages set: saving them (save_design,
# save_banner) and the live preview (design_preview) both read this.
CHROME_STYLES = ("inline", "fixed", "floating")
DESIGN_FIELDS = {
    # Style
    # your own palettes too (themes.own_themes)
    "theme": one_of(lambda: all_choices()), "theme_dark": one_of(lambda: dark_choices()),
    "theme_mode": one_of(dict(THEME_MODES)),
    "font_body": one_of(lambda: fonts.STACKS), "font_headings": one_of(lambda: fonts.STACKS),
    "font_size": one_of(FONT_SIZES), "glass_effect": flag, "page_animations": flag, "smooth_scroll": flag,
    "section_motion": one_of(lambda: pages.SECTION_MOTIONS),
    "section_space": one_of(lambda: pages.SPACINGS),
    "section_heading_align": one_of(lambda: pages.SECTION_HEADINGS),
    "visitor_theme_switching": flag, "favicon_url": text(), "header_icon_url": text(), "app_icon_url": upload,
    "app_name": text(30),
    # Blog layout
    "roll_style": one_of(("list", "cards", "magazine", "minimal", "timeline")),
    "roll_shows": some_of(ROLL_PARTS), "roll_list_cover": one_of(LIST_COVER_SIDES), "roll_placeholder": flag,
    "minimal_group": one_of(MINIMAL_GROUPS), "timeline_align": one_of(TIMELINE_ALIGNS),
    "posts_per_page": _posts_per_page, "cards_per_row": one_of(tuple(CARDS_PER_ROW)), "relative_dates": flag,
    **{key: placed(SIDE_PLACES, SIDE_WHERE) for key in SIDE_KEYS},
    **{f"{key}_where": shows_on(SIDE_WHERE) for key in SIDE_KEYS},
    "side_order": ordered(side_order_of), "side_plain": flag,
    # Posts
    "post_shows": some_of(lambda: pages.EXTRAS, empty="none"),
    "toc_style": placed(pages.TOC_STYLES, pages.TOC_WHERE), "toc_style_where": shows_on(pages.TOC_WHERE),
    "toc_fold": one_of(lambda: pages.TOC_FOLDS),
    "toc_numbers": flag, "heading_fold": one_of(lambda: pages.FOLD_STYLES), "heading_links": flag,
    "breadcrumbs": one_of(("auto", "tag", "home", "off")), "cover_width": one_of(lambda: pages.COVER_STYLES),
    "gallery_style": one_of(lambda: gallery.STYLES), "portfolio_style": one_of(lambda: pages.PORTFOLIO_STYLES),
    "lightbox_images": flag, "sidenotes": flag, "links_new_tab": flag,
    "show_updated": flag, "scroll_to_top": flag, "milestones_align": one_of(TIMELINE_ALIGNS),
    "reactions_style": one_of(lambda: dict(reactions.STYLES)),
    "reaction_emojis": some_of(lambda: reactions.CHOICES, empty=reactions.DEFAULT, in_form_order=True),
    # Header and footer
    "body_width": one_of(("standard", "narrow")), "header_style": one_of(CHROME_STYLES),
    "header_align": one_of(HEADER_ALIGNS), "header_width": one_of(HEADER_WIDTHS),
    "footer_style": one_of(CHROME_STYLES), "footer_enabled": flag, "footer_layout": one_of(FOOTER_LAYOUTS),
    "footer_order": ordered(footer_order_of), "footer_note": text(),
    **{f"footer_show_{part}": flag for part in ("bio", "note", "pages", "socials", "powered_by", "browse")},
    # Banner
    "banner_enabled": flag, "banner_heading": text(), "banner_subheading": text(), "banner_button_text": text(),
    "banner_button_url": text(), "banner_image_url": text(), "banner_width": one_of(lambda: pages.COVER_WIDTHS),
}
BANNER_FIELDS = {k for k in DESIGN_FIELDS if k.startswith("banner_")}


async def save_design(request):
    form = await request.form()
    settings.set_declared(form.get("declared_fields"),
                          clean_form(form, {k: f for k, f in DESIGN_FIELDS.items() if k not in BANNER_FIELDS}))
    # 'design-saved': the page reloads to show the new look (DESIGN_SAVED_JS)
    typed_icon = (form.get("app_icon_url") or "").strip()
    saved = SaveStatus("Saved - but the app icon has to be one of your uploads", "error") \
        if typed_icon and not typed_icon.startswith("/uploads/") else SaveStatus("Saved")
    return FtResponse(saved, headers={"HX-Trigger": json.dumps({"design-saved": ""})})





def save_members(request, session, members_enabled: bool = False, members_header: bool = False,
                 members_intro: str = "", members_comments: str = "everyone", members_welcome: str = "",
                 stripe_key: str = "", stripe_key__remove: bool = False, members_currency: str = "usd",
                 members_price_month: str = "", members_price_year: str = "", members_trial_days: str = "0",
                 members_tax: bool = False, declared_fields: str = None):
    from soloblog import members
    from soloblog import stripe_members as pay
    values = {"members_enabled": "1" if members_enabled else "0",
              "members_header": "1" if members_header else "0",
              "members_intro": members_intro.strip()[:300],
              "members_comments": members_comments if members_comments in ("members", "paid") else "everyone",
              "members_welcome": members_welcome.strip()[:3000]}
    paid_form = declared_fields is None or "stripe_key" in declared_fields.split(",")
    if paid_form:
        # a secret: left empty, the saved one stays (ui.SecretInput)
        key = "" if stripe_key__remove else (stripe_key.strip() or settings.get("stripe_key"))
        currency = members_currency if members_currency in pay.CURRENCIES else "usd"
        month, year = members_price_month.strip(), members_price_year.strip()
        if key and not key.startswith(("sk_", "rk_")):
            return SaveStatus("Use a restricted key (rk_…) or a secret key (sk_…) - not the publishable one",
                              "error")
        amounts = {k: pay.minor(v, currency) if v else 0 for k, v in (("month", month), ("year", year))}
        if None in amounts.values():
            return SaveStatus("Prices are amounts, like 5 or 4.50", "error")
        trial = members_trial_days.strip() or "0"
        if not trial.isdigit() or int(trial) > 365:
            return SaveStatus("A free trial is 0 to 365 days", "error")
        values.update({"stripe_key": key, "members_currency": currency, "members_price_month": month,
                       "members_price_year": year, "members_trial_days": str(int(trial)),
                       "members_tax": "1" if members_tax else "0"})
    was = settings.get("members_enabled") == "1"
    settings.set_declared(declared_fields, values)
    now = settings.get("members_enabled") == "1"
    if now != was:
        # what of a members post search may find changes with it
        posts.refresh_search()
    said = "Saved"
    if now and not was:
        added = members.sync_subscribers()
        if added:
            said = (f"Saved - your {added} newsletter subscriber{'s are' if added != 1 else ' is'} "
                    f"now {'members' if added != 1 else 'a member'}")
    if paid_form and settings.get("stripe_key") and (amounts["month"] or amounts["year"]) and not config.DEMO_MODE:
        try:
            problems = pay.set_up(settings.get("stripe_key"), settings.get("members_currency"),
                                  amounts["month"], amounts["year"])
        except pay.StripeError as e:
            return SaveStatus(f"Saved, but Stripe said: {e}", "error")
        if problems:
            return SaveStatus(f"Saved - but {problems[0]}", "error")
    return SaveStatus(said)


async def save_banner(request):
    form = await request.form()
    settings.set_declared(form.get("declared_fields"), clean_form(form, {k: DESIGN_FIELDS[k] for k in BANNER_FIELDS}))
    return SaveStatus("Saved")


# Settings > Profile and links: you, your links, the links page and support
PROFILE_FIELDS = {
    "author_name": text(), "author_avatar_url": text(), "author_bio": text(),
    **{f"social_{name}": text() for name in ("twitter", "facebook", "github", "mastodon", "instagram", "youtube",
                                             "linkedin", "bluesky", "threads", "website")},
    "extra_social_links": text(),
    "social_order": cleaned(lambda v: ",".join(k for k, *_ in ordered_social_platforms({"social_order": v}))),
    **{f"support_{name}": cleaned(safe_url)
       for name in ("kofi", "buymeacoffee", "github", "patreon", "liberapay", "paypal")},
    "support_message": text(),
    "links_enabled": flag, "links_items": text(), "links_show_socials": flag, "links_show_support": flag,
    "links_show_posts": flag,
}


async def save_profile(request):
    form = await request.form()
    declared = form.get("declared_fields")
    settings.set_declared(declared, clean_form(form, PROFILE_FIELDS))
    # a switch among "Each post shows" (pages.EXTRAS), set here
    if declared is None or "support_on_posts" in declared.split(","):
        pages.show_on_posts("support", bool(form.get("support_on_posts")))
    return SaveStatus("Saved")


async def save_editor(request, session):
    form = await request.form()
    # the hidden input (kept in sync client-side by the drag-reorder
    # list) carries both membership AND order in one csv - sanitized
    # again here rather than trusted outright, same as any other
    # client-supplied value
    pinned = editor_config.pinned_from_setting(form.get("editor_toolbar", ""))
    settings.set_declared(form.get("declared_fields"), {
        "editor_toolbar": ",".join(pinned),
        "editor_autosave": "1" if form.get("editor_autosave") else "0",
        "editor_settings_beside": "1" if form.get("editor_settings_beside") else "0",
        "markdown_mermaid": "1" if form.get("markdown_mermaid") else "0",
        "markdown_math": "1" if form.get("markdown_math") else "0",
        "editor_toolbar_rows": editor_config.toolbar_style(form.get("editor_toolbar_rows", "")),
        "editor_phone_bar": form.get("editor_phone_bar") if form.get("editor_phone_bar") in editor_config.PHONE_BARS
        else "buttons",
        "editor_slash": "1" if form.get("editor_slash") else "0",
        "editor_spellcheck": "1" if form.get("editor_spellcheck") else "0",
        "editor_width": "wide" if form.get("editor_width") == "wide" else "comfortable",
        "editor_marks": "full" if form.get("editor_marks") == "full" else "dimmed",
        "editor_typewriter": "1" if form.get("editor_typewriter") else "0",
        "editor_fade": form.get("editor_fade") if form.get("editor_fade") in editor_config.FOCUS_FADES
        else "paragraph",
        "editor_focus_toolbar": "none" if form.get("editor_focus_toolbar") == "none" else "all",
        "editor_progress": "1" if form.get("editor_progress") else "0",
        "new_post_start": post_templates.clean_start(form.get("new_post_start")),
        "editor_goal_default": str(min(int(goal), 1_000_000)) if (goal := (form.get("editor_goal_default") or "").strip())
        .isdigit() and int(goal) else "",
    })
    return SaveStatus("Saved")

_register_saves()
