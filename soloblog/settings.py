import contextvars
import re
from soloblog import cache
from soloblog import config
from soloblog.db import get_db
from soloblog import editor_config

DEFAULTS = {
    "site_title": "My Blog",
    "site_url": "",                 # the site's address, when BASE_URL isn't set on the host (use_site_url)
    "author_name": "",
    "author_bio": "",
    "author_avatar_url": "",
    "tagline": "",
    "theme": "light",
    "meta_description": "",
    "footer_note": "",
    "favicon_url": "",
    "roll_style": "list",       # list, cards, magazine, minimal or timeline - how the homepage roll looks
    "roll_shows": "cover,date,reading,summary,tags",  # what each post in it shows - ui.ROLL_PARTS
    "roll_list_cover": "right",  # List's picture, left or right of the text - ui.LIST_COVER_SIDES
    "minimal_group": "none",     # Minimal's headings: none, year or month - ui.MINIMAL_GROUPS
    "roll_placeholder": "1",     # "1" = a tile in the theme's colours where a card has no cover
    "timeline_align": "center",   # the Timeline style's line: ui.TIMELINE_ALIGNS
    "milestones_align": "left",   # the Milestones section's line, the same
    "relative_dates": "0",       # "1" = "2 days ago", "0" = "Aug 30, 2026"
    "comment_webhook_url": "",   # optional - POSTed a small JSON payload on new comments
    "update_hook_url": "",       # Settings > Integrations > Updates: POSTed by Update now (updates.trigger)
    "update_hook_token": "",     # sent with it as a Bearer token, if set
    "social_twitter": "",
    "social_facebook": "",
    "social_github": "",
    "social_mastodon": "",
    "social_instagram": "",
    "social_youtube": "",
    "social_linkedin": "",
    "social_bluesky": "",
    "social_threads": "",
    "social_website": "",
    "extra_social_links": "",    # one per line, "Label|https://url" - for anything not in the fixed list
    # display/priority order for the 9 fixed platforms above - drives
    # both the footer/bio social row and which of them show up (and in
    # what order) as post-sharing buttons. SOCIAL_PLATFORMS (ui) is
    # the source of truth for which keys are valid; this is just their
    # order, so a fresh install's default here has to list every one
    # of them or a platform would never render at all until the admin
    # explicitly reordered something.
    "social_order": "twitter,facebook,mastodon,bluesky,threads,linkedin,github,instagram,youtube,website",
    "posts_per_page": "12",
    "preset": "",                 # the settings preset last applied (presets.py)
    "template_recent": "",        # the templates last started from, for the template picker (post_templates.py)
    "preset_undo": "",            # what it changed, for Undo
    "custom_preset": "",          # your own look, saved as the Custom preset (presets.save_custom)
    "own_themes": "",             # your own colours, from daisyUI's theme generator (themes.own_themes)
    "post_shows": "",             # what a post shows around its text (pages.EXTRAS); "" - all but Print and the newsletter sign-up
    "cards_per_row": "2",          # Cards: 1, 2 or 3 in a row (3 is 2 in the narrow column); 1 is Magazine's first, each
    # IANA name - what "Publish at" is typed in, and what dates on the
    # site are shown in. Everything is still stored as UTC (see tz.py).
    "timezone": "UTC",
    "setup_done": "0",            # "1" once the first-run wizard (/admin/welcome) has been finished
    "getting_started_hidden": "0",  # "1": the Getting started card on Posts dismissed
    # the members area (members.py)
    "members_enabled": "0",         # "1": readers can join, and posts can be for members
    "members_header": "1",          # "1": Sign in / your account in the site's header
    "members_intro": "",            # the line on /join; a default when empty
    "members_comments": "everyone", # who can comment: everyone | members | paid (with members on)
    "members_welcome": "",          # the welcome email's text; empty: none is sent
    # paid members, through Stripe (stripe_members.py)
    "apps_publish": "apps",         # who may publish with a Publish key: none | apps (not AI assistants) | all
    "stripe_key": "",               # a restricted (rk_) or secret (sk_) key; _test_ in it is test mode
    "members_currency": "usd",
    "members_price_month": "",      # amounts as typed ("5", "4.50"); empty: no such plan
    "members_price_year": "",
    "members_trial_days": "0",
    "members_tax": "0",             # "1": Stripe Tax works out and adds sales tax
    # what set_up made at Stripe - not edited by hand
    "stripe_product_id": "",
    "stripe_price_month": "",
    "stripe_price_month_is": "",    # "500:usd" - the amount the price was made for
    "stripe_price_year": "",
    "stripe_price_year_is": "",
    "stripe_webhook_id": "",
    "stripe_webhook_secret": "",
    "stripe_last_ok_at": "",        # how the last Checkout or portal went (Site health)
    "stripe_last_failed_at": "",
    "stripe_last_error": "",
    # Site health (health.py): what it last found, kept between visits
    "backup_last_at": "",           # the last backup made to the bucket
    "backup_last_error": "",        # why the last automatic backup failed, until one works
    "images_not_in_bucket": "",     # images whose copy to the bucket failed, a line each, until they reach it
    "bucket_deletes_left": "",      # images deleted here whose delete in the bucket failed, a line each, until it goes
    "backup_verified_at": "",       # Verify a backup: when, and "ok" or what was wrong
    "backup_verified_result": "",
    "mail_last_ok_at": "",          # the last email that went out, and the last that didn't
    "mail_last_failed_at": "",
    "mail_last_error": "",
    "db_check_at": "",              # SQLite's quick_check, weekly
    "db_check_result": "",
    "health_remote": "1",           # "0": none of the checks that ask other servers
    "health_remote_results": "",    # their last results (JSON), refreshed daily
    "health_alerts": "1",           # "0": no email when something becomes critical
    "detail_log": "1",              # "0": no detailed log (Site health > Log's download)
    "health_alerted": "",           # JSON {check: when it was last emailed about}
    "health_critical": "0",         # how many need attention - the admin menu's dot
    # the version whose What's new card was dismissed (whatsnew.py) - set
    # at setup too, so a new site doesn't open on one
    "whatsnew_seen": "",
    "last_backup_download": "",   # when a backup zip was last downloaded - Getting started
    # "standard" (max-w-3xl) or "narrow" (max-w-2xl) - the page's own
    # reading-column width. Wide elements (the hero) ignore this and
    # always render at the "standard" width regardless - see
    # ui's BODY_WIDTHS/WIDE_WIDTH for the one place both live.
    "body_width": "standard",
    "section_space": "medium",      # pages.SPACINGS - each post or page can choose its own
    "section_heading_align": "left",  # pages.SECTION_HEADINGS - each section can choose its own
    "footer_style": "inline",    # "inline" (scrolls with content), "fixed" (stuck to the viewport edge, full-width bar), or "floating" (fixed, inset from the edge, its own rounded/bordered pill)
    "footer_enabled": "1",       # master switch - "0" hides the footer entirely
    "footer_show_bio": "1",      # avatar + name + bio, left side
    "footer_show_note": "1",  # the footer_note/copyright line, left side under the bio
    "footer_show_pages": "1",    # footer-pinned pages, right side
    "footer_show_socials": "1",  # social links, right side under the pinned pages
    "header_style": "floating",     # "inline", "fixed", or "floating" - same three options and meaning as footer_style above
    "header_align": "left",      # ui.HEADER_ALIGNS: "left", "center" or "stacked"
    "header_width": "wide",    # ui.HEADER_WIDTHS: "column" (the text's width) or "wide" (out to the side panels)
    # "1" or "0": frosted glass for the header, footer, drawers, menus and
    # dialogs together - read only by ui.glass_fill()
    "glass_effect": "1",
    "header_icon_url": "",       # small custom icon shown before the site title
    "comments_enabled": "1",     # global kill switch - existing comments aren't deleted, just hidden
    "banner_enabled": "0",
    "banner_heading": "",
    "banner_subheading": "",
    "banner_button_text": "",
    "banner_button_url": "",
    "banner_image_url": "",
    "banner_width": "full",       # pages.COVER_WIDTHS
    "scroll_to_top": "1",
    "links_new_tab": "0",         # links to other sites in a post open in a new tab
    "gallery_style": "grid",      # default style for ```gallery blocks - gallery.STYLES
    "portfolio_style": "grid",    # how a Portfolio page shows its work - pages.PORTFOLIO_STYLES
    "lightbox_images": "1",       # single images in posts open in the lightbox too
    # breadcrumbs above a post: "auto" (series, else first tag), "tag",
    # "home" (Home > Post only - sub-pages still show their parent), "off"
    "breadcrumbs": "auto",
    "font_size": "medium",        # small / medium / large - the whole page's text, input.css
    "cover_width": "screen",     # pages.COVER_STYLES - each post can choose its own
    "toc_style": "right",           # pages.TOC_STYLES - each post can choose its own
    "toc_style_where": "posts,pages",  # pages.TOC_WHERE: where the site's choice applies
    "heading_fold": "open",       # pages.FOLD_STYLES - each post can choose its own
    "toc_fold": "auto",           # pages.TOC_FOLDS
    "heading_links": "1",         # a copy-link button beside each heading
    "smooth_scroll": "1",
    "sidenotes": "1",              # footnotes in the margin beside their line, where there's room
    "page_animations": "1",       # pages fade in, images shimmer until they load
    "section_motion": "fade",     # how sections come into view (pages.SECTION_MOTIONS) - each post or page can choose
    "show_updated": "1",          # "Updated ..." beside a post's date once it's edited on a later day
    "side_tags": "off",           # the tag cloud: off, under the posts, left or right (ui.SIDE_PLACES)
    "side_archive": "off",        # archive links to the last 12 months, the same
    "side_plain": "1",            # no card around the panels in the margins
    "side_author": "off",          # About the author beside the page (ui.SIDE_PLACES)
    # where each shows (ui.SIDE_WHERE): the blog roll, posts, pages
    "side_tags_where": "roll",
    "side_archive_where": "roll",
    "side_author_where": "roll,posts",
    "side_order": "side_tags,side_archive,side_author",  # their order on a side and under the posts (ui.side_order)
    "toc_numbers": "0",           # number the contents 1, 2, 2.1
    "home_page": "",              # a post's slug: that page is the homepage, the blog roll moves to /blog
    "home_page_shows": "",        # what else that page shows there, from posts.HOME_EXTRAS - just the page by default
    # Home and Blog in the header's menu (Posts and pages > Pinned): where each sits, in a page's
    # pin_order numbers (unset: before every page), the words for each (unset: Home, Blog), and
    # whether Home is left out
    "nav_home_order": "",
    "nav_blog_order": "",
    "nav_home_label": "",
    "nav_blog_label": "",
    "nav_home_hidden": "",
    "reactions_style": "like",     # reactions.STYLES: "like" (heart), "emoji" (a row), "off"
    "reaction_emojis": "heart,clap,laugh,wow,think",  # which of reactions.CHOICES, in order
    "markdown_mermaid": "0",      # draw ```mermaid blocks as diagrams (loads mermaid.js on those posts)
    "markdown_math": "0",         # render $...$ / $$...$$ with KaTeX
    "visitor_theme_switching": "0",
    "email_provider": "",         # "" (disabled), "smtp", or "api" - see mail.py
    "smtp_provider": "",            # mail.SMTP_PRESETS key - its server and port; "" for one you set up yourself
    "smtp_host": "",
    "smtp_port": "587",
    "smtp_user": "",
    "smtp_password": "",
    "smtp_from": "",
    "email_api_key": "",
    "email_api_from": "",
    "pixabay_api_key": "",        # stock photo tabs in the image picker - see stock.py
    "pexels_api_key": "",
    # which post-editor toolbar buttons show, and in what order (the
    # rest sit in its "..." menu) - keys/order live in editor_config.py,
    # which is the source of truth for what's valid
    "editor_toolbar": ",".join(editor_config.DEFAULT_ORDER),
    "editor_autosave": "1",         # keep an unsaved draft on this device while writing
    "editor_settings_beside": "1",  # Post settings beside the editor where there's room; 0: always the sidebar
    "editor_toolbar_rows": "one",   # one: Icons; menus: Classic menus; none: Minimal (editor_config.toolbar_style)
    "editor_phone_bar": "buttons",  # the bar above a phone's keyboard: buttons (yours), sections or none
    "editor_slash": "1",            # type / at the start of a line for a menu of things to insert
    "editor_spellcheck": "1",       # the browser's own spell check while writing
    "editor_width": "comfortable",  # comfortable: a column about 70 characters wide; wide: the whole box
    "editor_marks": "dimmed",       # dimmed: markdown's ## ** [ ] step back; full: the text's own colour
    "editor_typewriter": "1",       # focus mode keeps the line you're writing in the middle of the screen
    "editor_fade": "paragraph",     # focus mode fades all but the paragraph (or sentence) you're in; off
    "editor_focus_toolbar": "all",  # focus mode while you type: all (the toolbar away, the bars quiet), or none
    "editor_progress": "1",         # words written today by the word count, and each post's word goal
    "editor_goals": "{}",           # each post's word goal, by its id - routes/editor.py word_goal
    "editor_goal_default": "",      # every post's word goal unless it has its own; "" for none
    "post_templates": "[]",         # posts saved as templates - post_templates.py
    "new_post_start": "",           # the template a new post starts from - "" for a blank one (post_templates.start_key)
    # visitor analytics - "", "cloudflare", "google" or "plausible", and
    # that provider's token / measurement ID / domain. Never loaded for
    # a logged-in admin or on admin pages (see app.apply_site_config).
    "analytics_provider": "",
    "analytics_id": "",
    # Google AdSense (ads.py) - the ca-pub-... publisher ID turns it on
    "adsense_client": "",
    "adsense_slot_post": "",      # optional fixed ad unit after each post
    "adsense_slot_roll": "",      # optional fixed ad unit below the blog roll
    "adsense_on_pages": "0",      # also on pages (pinned posts)
    # cookie consent - only ever shown when something needs it (Google Analytics)
    "consent_banner": "1",
    "custom_head_consent": "0",     # "1": Custom code > In <head> waits for Accept, like Google Analytics
    "consent_message": "",
    "consent_privacy_url": "",
    "footer_order": "bio,socials,|,links,note,small",   # ui.FOOTER_PIECES, top to bottom; | starts a split's right side
    "footer_layout": "center",    # ui.FOOTER_LAYOUTS
    "footer_show_browse": "1",     # Archive · Tags · RSS links in the footer's small print
    "footer_show_powered_by": "1",  # a small "Powered by Soloblog" line in the footer
    # support/donation links - keys match SUPPORT_PLATFORMS (ui)
    "support_kofi": "",
    "support_buymeacoffee": "",
    "support_github": "",
    "support_patreon": "",
    "support_liberapay": "",
    "support_paypal": "",
    "support_message": "",
    # how many automatic backups the bucket keeps (Backup > Cloud storage) -
    # S3_BACKUP_KEEP only sets the starting value
    "backup_keep": str(config.S3_BACKUP_KEEP),
    # how often they're made: "changes" (a minute after things go quiet), "day" or "week" - only when
    # something's changed since the last one
    "backup_every": "changes",
    # which BACKUP_PASSPHRASE the bucket's images are sealed with (a fingerprint, storage.reseal_images)
    "bucket_images_sealed": "",
    # what the automatic backups include (Backup > Cloud storage), comma
    # separated - blank is everything but images, which the bucket keeps one by one
    "backup_include": "",
    # the /contact form
    "contact_enabled": "0",
    "contact_intro": "",          # a line shown above the form
    "contact_email": "",          # where messages are emailed (blank = inbox only)
    "contact_mode": "builtin",    # "builtin" (Soloblog's own form) or "embed" (a hosted form, contact_form_url)
    "contact_service": "",        # also forward built-in messages to a service - formservices.FORWARDERS key
    "contact_service_id": "",     # that service's form ID (or email, for FormSubmit)
    "contact_form_url": "",       # a Tally/Typeform/Google Forms/... link, for contact_mode "embed"
    # the /links page (link-in-bio)
    "links_enabled": "0",
    "links_items": "",            # one per line, "Label|https://url" - same format as extra_social_links
    "links_show_socials": "1",
    "links_show_posts": "1",      # the three newest posts
    "links_show_support": "1",
    # Settings > Site
    "unsplash_access_key": "",
    # Settings > Site > Languages (translate.py)
    "site_language": "en",          # what posts are written in - <html lang>
    "english_spelling": "us",       # an English site's spelling and dates: i18n.ENGLISH (us, gb, au)
    "translate_provider": "",       # "", "deepl", "google" or "libretranslate"
    "translate_api_key": "",
    "translate_url": "",            # a LibreTranslate server; empty = libretranslate.com
    "translate_languages": "",      # comma list of translate.LANGUAGES codes to offer
    # Settings > Site > Fediverse (fediverse.py) and Webmentions (webmention.py)
    "activitypub_enabled": "0",
    "activitypub_username": "blog",
    "activitypub_private_key": "",  # made on first use - see fediverse._keys
    "activitypub_public_key": "",
    "webmention_receive": "0",
    "webmention_send": "0",
    "webmention_moderate": "1",     # replies and mentions wait for approval; likes and reposts don't
    "google_site_verification": "",
    "bing_site_verification": "",
    "search_noindex": "0",          # "1" asks search engines not to list the site
    "custom_head": "",              # raw html for public pages' <head>
    "custom_css": "",
    "redirects": "",                # "old new" a line - posts.parse_redirects
    "app_icon_url": "",             # an upload - the web app manifest and touch icons are made from it
    "share_image_url": "",          # an upload - shared for pages without a cover image of their own
    "upload_renames": "{}",         # old upload file name -> new (images.rename_upload)
    "app_name": "",                 # the manifest's short_name; empty = site title
    # comment reply emails (opt-in per comment, needs an email provider)
    "reply_emails": "1",
    "comment_blocklist": "",        # one word, phrase, address or domain a line (comments.is_blocked)
    # Settings > Comments and messages: another comment system instead of
    # Soloblog's own (extcomments.py) - "" is Soloblog's own
    "comments_system": "",
    "comments_autoload": "0",       # load it without waiting for a click
    "giscus_repo": "",
    "giscus_repo_id": "",
    "giscus_category": "",
    "giscus_category_id": "",
    "bluesky_handle": "",
    "isso_url": "",
    "remark42_url": "",
    "remark42_site_id": "remark",
    # Settings > Security > Spam protection (captcha.py)
    "captcha_provider": "",         # "", "turnstile" or "hcaptcha"
    "captcha_site_key": "",
    "captcha_secret": "",
    # the admin's own address (Settings > Email > Admin email) - password
    # reset links, and new-comment emails when notify_comments is on
    # (Settings > Comments and messages)
    "admin_email": "",
    "notify_comments": "0",
    "signin_alerts": "1",           # email the admin when a browser it hasn't seen signs in
    # the password's recovery key (auth.py): its hash and when it was made
    "recovery_key_hash": "",
    "recovery_key_made": "",
    "reset_links": "",              # password reset links still alive, hashed (auth.py)
    # Settings > Visitors > Newsletter (newsletter.py)
    "newsletter_mode": "",          # "", "builtin", or one of newsletter.SERVICES
    "newsletter_title": "",
    "newsletter_intro": "",
    "newsletter_auto": "1",         # email new posts as they go live
    "newsletter_full": "0",         # the whole post, not the summary and a link
    "newsletter_digest": "",        # "" each post as it goes live, "week" or "month": one email with them all
    "newsletter_digest_last": "",   # the week or month the last one went out for ("2026-W44", "2026-11")
    "newsletter_held": "",          # who a newsletter hasn't reached yet, held back by the email service's limit (JSON)
    "newsletter_on_home": "1",
    "newsletter_buttondown": "",
    "newsletter_kit": "",
    "newsletter_mailchimp": "",
    "newsletter_substack": "",
    # Settings > Site > Sharing (crosspost.py). bluesky_handle (the
    # comments' too) is the account; an app password, never the real one
    "crosspost_bluesky": "0",
    "bluesky_app_password": "",
    "crosspost_mastodon": "0",
    "mastodon_instance": "",
    "mastodon_token": "",
    # Settings > Appearance > Colour palette > fonts (fonts.py) - "" is the default
    "font_body": "",
    "font_headings": "",
    # Settings > Appearance > Dark mode: the theme a visitor whose device is
    # in dark mode sees ("" = always the main theme)
    "theme_dark": "dark",         # the dark theme (themes.theme_choice)
    "theme_mode": "auto",         # which visitors see: themes.THEME_MODES
    # the last link check's result (linkcheck.py), as JSON - kept here so
    # a restart doesn't lose it
    "linkcheck_last": "",
}
# The footer's pages (Posts and pages > Pinned > Footer) and the built-in pages in either menu, as
# the header's Home and Blog above: <menu>_<page>_on/_order/_label, nav_ for the header and foot_
# for the footer (posts.SITE_PAGES). None on: a menu as it was.
for _menu in ("nav", "foot"):
    for _page in ("home", "blog", "archive", "tags", "search", "wiki", "links", "contact", "newsletter", "rss"):
        for _what in ("on", "order", "label"):
            DEFAULTS.setdefault(f"{_menu}_{_page}_{_what}", "")


# (generation, values, stored) - read once, then served from memory until
# something bumps cache.generation() (set_many below, a restored backup).
# A page asks for settings several times over (the layout, the admin
# menu, the renderer...), and each was its own query before. stored is
# what's in the database alone, without what the host fills in.
_cached = (None, {}, {}, frozenset())


def _values() -> dict:
    global _cached
    # the generation is taken before the read: a change that lands while
    # this reads bumps it, so the copy stored here is already stale and
    # gets read again next time rather than kept
    gen = cache.generation()
    cached_gen, values = _cached[:2]
    if cached_gen != gen:
        rows = get_db().execute("SELECT key, value FROM settings").fetchall()
        stored = {r["key"]: r["value"] for r in rows}
        values = {**DEFAULTS, **stored}
        _cached = (gen, values, stored, _from_host(values, stored))
    return values


def _from_host(values, stored) -> frozenset:
    """What the host sets (config.SMTP_HOST, config.RESEND_API_KEY...)
    fills in where the site has nothing of its own saved - so everything
    that reads email sees it as set up, and Settings always wins. Returns
    the keys it filled."""
    filled = set()

    def fill(key, value):
        if value and not values[key]:
            values[key] = value
            filled.add(key)
    # a provider that was never saved is a site that never chose; a saved
    # empty one is "Nothing", chosen on purpose, and stays off. SMTP when
    # the host names a server, Resend when it only has Resend's key
    if "email_provider" not in stored and (config.SMTP_HOST or config.RESEND_API_KEY):
        values["email_provider"] = "smtp" if config.SMTP_HOST else "api"
        filled.add("email_provider")
    if config.SMTP_HOST and not values["smtp_provider"] and not values["smtp_host"]:
        fill("smtp_host", config.SMTP_HOST)
        if config.SMTP_PORT.isdigit() and "smtp_port" not in stored:
            values["smtp_port"] = config.SMTP_PORT
            filled.add("smtp_port")
        fill("smtp_user", config.SMTP_USER)
    fill("smtp_password", config.SMTP_PASSWORD)
    fill("smtp_from", config.SMTP_FROM)
    if config.RESEND_API_KEY and not values["email_api_key"]:
        values["email_api_key"] = config.RESEND_API_KEY
        filled.add("email_api_key")
    if config.RESEND_FROM and not values["email_api_from"]:
        values["email_api_from"] = config.RESEND_FROM
        filled.add("email_api_from")
    if config.ADMIN_EMAIL and not values["admin_email"]:
        values["admin_email"] = config.ADMIN_EMAIL
        filled.add("admin_email")
    return frozenset(filled)


def stored(key: str) -> str:
    """A setting as saved on the site, without what the host fills in."""
    _values()
    return _cached[2].get(key, DEFAULTS.get(key, ""))


def saved(key: str) -> bool:
    """Whether the site has a value of its own saved for a setting - not
    a default, not the host's, not saved empty."""
    _values()
    return bool(_cached[2].get(key))


def on_host(key: str) -> bool:
    """Whether a setting's value is the host's, not one saved in Settings."""
    _values()
    return key in _cached[3]


# a preset being previewed (app.PresetPreview): this request sees its
# settings over the saved ones, and nothing is saved
_overlay = contextvars.ContextVar("overlay", default=None)


def preview(values):
    _overlay.set(values or None)


def get_all() -> dict:
    # a copy - a caller adding a key for its own use mustn't change the cache
    values = dict(_values())
    if _overlay.get():
        values.update(_overlay.get())
    return values


def get(key: str) -> str:
    over = _overlay.get()
    if over and key in over:
        return over[key]
    return _values().get(key, DEFAULTS.get(key, ""))


# what the frame around every page reads - the palette, text size, glass,
# the admin sidebar's items, the header (apply_site_config, AdminSidebar,
# Nav). Saving a change to one reloads the page it was saved on (SaveStatus),
# since saving in place leaves the frame as it was.
FRAME = {"theme", "theme_dark", "theme_mode", "font_size", "glass_effect", "page_animations", "smooth_scroll",
         "sidenotes", "favicon_url", "english_spelling", "visitor_theme_switching", "members_enabled",
         "newsletter_mode", "side_plain", "site_title", "header_align", "header_style", "header_width",
         "header_icon_url", "contact_enabled", "comments_enabled"}
_frame_changed = contextvars.ContextVar("frame_changed", default=False)


def frame_changed() -> bool:
    return _frame_changed.get()


def new_request():
    """A fresh start for frame_changed - before every request (app.py)."""
    _frame_changed.set(False)


def set_many(values: dict):
    if any(k in FRAME and get(k) != v for k, v in values.items()):
        _frame_changed.set(True)
    db = get_db()
    for k, v in values.items():
        db.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (k, v)
        )
    db.commit()
    cache.bump()


SITE_URL = re.compile(r"^https?://[a-z0-9]([a-z0-9.-]*[a-z0-9])?(:\d{1,5})?$", re.I)


def clean_site_url(value: str) -> str:
    """"https://example.com" from what was typed or the address setup was
    reached at - just the scheme, the host and a port; "" if it isn't one."""
    value = (value or "").strip().rstrip("/")
    return value.lower() if SITE_URL.match(value) else ""


def use_site_url(url: str = None):
    """The site's address everywhere (config.BASE_URL) - the site_url
    setting, unless the host sets BASE_URL; without either, the
    platform's own address (Fly, Render, Railway)."""
    if config.BASE_URL_FIXED:
        return
    config.BASE_URL = (url if url is not None else get("site_url")) or config.PLATFORM_URL or config.LOCAL_URL


def set_declared(declared, values: dict):
    """set_many, limited to the fields the form says it has (its
    declared_fields, which app.js adds) - so a form that leaves a setting
    out leaves it alone, instead of an unsent checkbox reading as "off".
    Without that list (a script posting directly) every key is saved."""
    if declared is not None:
        names = set(declared.split(","))
        values = {k: v for k, v in values.items() if k in names}
    from soloblog import config
    if config.DEMO_MODE:
        from soloblog.demo import LOCKED_SETTINGS, _locked_by_name
        locked = LOCKED_SETTINGS | _locked_by_name()
        values = {k: v for k, v in values.items() if k not in locked}
    set_many(values)
