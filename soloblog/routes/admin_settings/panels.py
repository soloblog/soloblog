"""The form on each Settings page outside Design."""
import json
import os
from fasthtml.common import *
from soloblog import config
from soloblog import csp
from soloblog import editor_config
from soloblog import settings
from soloblog import mail
from soloblog import captcha
from soloblog import extcomments
from soloblog import newsletter
from soloblog import translate
from soloblog import posts
from soloblog import ads
from soloblog import pages
from soloblog import post_templates
from soloblog.formservices import FORWARDERS
from soloblog.render import FORM_PROVIDERS
from soloblog.ui import EnglishSelect, SetUpFirst, EMAIL_SETUP, PageField, SecretInput
from soloblog.ui import TimezoneCombobox, Combobox, SEND_SVG
from soloblog.ui import SortMoves
from soloblog.ui import (
    Alert, FIELD_GAP, SECTION_GAP, FormField, ToggleField, RadioGroupField, SettingsPanel, MediaPickerButton,
    LinkPickerButton, SaveBar, ordered_social_platforms, RESTORE_SVG, EXTRA_LINK_ICONS, SUPPORT_PLATFORMS, COPY_SVG,
    SYNC_SVG, SortableList,
)
from soloblog.routes.welcome import SetupAgain
from soloblog.routes.admin_settings.base import ANALYTICS_PROVIDERS

# where to find each system's settings
COMMENT_SYSTEM_HELP = {
    "giscus": "All four are on giscus.app, once Discussions is on for a public GitHub repository.",
    "bluesky": "Share each post from this account - the replies to it show under the post.",
    "isso": "Your Isso server's URL.",
    "remark42": "Your Remark42 server's URL, and its SITE setting.",
}


def CommentSystemFields(s, name):
    fields = extcomments.SYSTEMS[name][3]
    return Div(
        Div(*[FormField(extcomments.FIELDS[k][0],
                        Input(name=k, value=s.get(k, ""), placeholder=extcomments.FIELDS[k][1],
                              cls="input input-sm w-full font-mono")) for k in fields],
            cls="grid grid-cols-1 sm:grid-cols-2 gap-2"),
        P(COMMENT_SYSTEM_HELP[name], cls="fieldset-label text-xs text-base-content/60 mt-1"),
        data_shown_for=f"comments_system={name}", hidden=s["comments_system"] != name, cls="mt-3"
    )


def home_kind(home_page) -> str:
    """What Settings > Name and homepage > Homepage has chosen: posts, wiki or page."""
    return "posts" if not home_page else "wiki" if home_page == posts.WIKI_HOME else "page"


def GeneralPanels(s):
    return Form(
        Div(
            SettingsPanel(
                "Identity",
                FormField("Site title", Input(name="site_title", value=s["site_title"], required=True,
                                               cls="input input-sm w-full"),
                           cls=FIELD_GAP),
                FormField("Tagline", Input(name="tagline", value=s["tagline"], cls="input input-sm w-full"),
                           help="A short line under your site's name on the homepage."),
                SetupAgain(s),
                key="name-identity"
            ),
            SettingsPanel(
                "Homepage",
                RadioGroupField("Your homepage shows", "home_kind",
                                [("posts", "Your latest posts"), ("wiki", "Your wiki"), ("page", "One of your pages")],
                                home_kind(s["home_page"]), default="posts",
                                help="With a page or the wiki there, your posts move to /blog, with a Blog link "
                                     "in the menu."),
                Div(PageField("home_page", "" if home_kind(s["home_page"]) != "page" else s["home_page"], "home",
                              placeholder="Choose a page"),
                    data_shown_for="home_kind=page", hidden=home_kind(s["home_page"]) != "page", cls="mt-2"),
                Div(FormField("It also shows", Div(
                    *[Label(Input(type="checkbox", name="home_page_shows", value=key, cls="checkbox checkbox-xs",
                                  checked=key in s["home_page_shows"].split(",")),
                            Span(label, cls="text-sm"), cls="flex items-center gap-2 cursor-pointer")
                      for key, label in posts.HOME_EXTRAS.items()],
                    cls="grid grid-cols-1 sm:grid-cols-2 gap-2"),
                    ),
                    data_shown_for="home_kind=page", hidden=home_kind(s["home_page"]) != "page", cls="mt-3"),
                key="name-homepage"
            ),
            SettingsPanel(
                "Time zone",
                FormField(
                    "Time zone",
                    TimezoneCombobox(s["timezone"]),
                    # filled in by the script below - the one thing the
                    # server can't know is where the admin actually is
                    help=Span("For your post dates and scheduled posts. ", Span(id="browser-tz-hint")),
                ),
                Script("""(function () {
  var z = Intl.DateTimeFormat().resolvedOptions().timeZone;
  var hint = document.getElementById('browser-tz-hint');
  if (z && hint) hint.textContent = "You're in " + z.replace(/_/g, ' ') + '.';
})();""", nonce=csp.NONCE),
                key="language-time"
            ),
            SettingsPanel(
                "Comments",
                ToggleField(
                    "Allow comments", "comments_enabled", checked=(s["comments_enabled"] == "1"),
                    help="Each post can turn them off too."
                ),
                Div(
                Div(RadioGroupField(
                    "Comments use", "comments_system",
                    [("", "Soloblog's own — you approve them in Comments")]
                    + [(k, f"{label} — {what}") for k, (label, what, _, _) in extcomments.SYSTEMS.items()],
                    selected=s["comments_system"] if s["comments_system"] in extcomments.SYSTEMS else "",
                    cls="mt-3"
                ),
                    *[CommentSystemFields(s, name) for name in extcomments.SYSTEMS],
                    # chosen and filled in together, with Save (AUTOSAVE_JS)
                    data_autosave_off=True),
                Div(
                    ToggleField(
                        "Let commenters get replies by email", "reply_emails", checked=(s["reply_emails"] == "1"),
                        help="Adds \"Email me when someone replies\" to the comment form."
                    ),
                    data_shown_for="comments_system=", hidden=bool(s["comments_system"]), cls="mt-3"
                ),
                Div(
                    ToggleField(
                        "Load comments without a click", "comments_autoload",
                        checked=(s["comments_autoload"] == "1"),
                        help="Off, readers click to show them."
                    ),
                    data_shown_for="comments_system!=", hidden=not s["comments_system"], cls="mt-3"
                ),
                    data_shown_for="comments_enabled=1", hidden=s["comments_enabled"] != "1"),
                key="messages-comments"
            ),
            # comments and contact messages both go through it, so it waits for either switch (pages.messages)
            SettingsPanel(
                "Blocked words",
                FormField("Blocked words", Textarea(s["comment_blocklist"], name="comment_blocklist", rows="3",
                                                    placeholder="casino\nspam@example.com\nspammy-domain.com",
                                                    cls="textarea textarea-sm w-full font-mono"),
                          help="One word, phrase, email address or domain a line. Comments and messages "
                               "with any of them go straight to the trash."),
                key="messages-blocked"
            ),
            cls=f"flex flex-col gap-3 {SECTION_GAP}"
        ),
        SaveBar(),
        hx_post="/admin/settings/name", hx_target="#save-status", hx_swap="outerHTML show:none focus-scroll:false",
        data_declare_fields=True
    )


NEWSLETTER_HELP = {
    "buttondown": "The name in buttondown.com/yourname.",
    "kit": "The number in your form's URL: app.kit.com/forms/1234567.",
    "mailchimp": "From Mailchimp's embedded sign-up form: the URL after action=\" in its code.",
    "substack": "The name in yourname.substack.com.",
}


def NewsletterPanel(s):
    m = s["newsletter_mode"]
    email_ready = s["email_provider"] in ("smtp", "api")
    return SettingsPanel(
        "Newsletter",
        RadioGroupField(
            "Readers subscribe with", "newsletter_mode",
            [("", "Nothing — no newsletter"),
             ("builtin", "Soloblog's own — your new posts, emailed to subscribers")]
            + [(k, f"{v[0]} — your account there sends the emails") for k, v in newsletter.SERVICES.items()],
            selected=m if m in ("builtin", *newsletter.SERVICES) else "", cls=FIELD_GAP
        ),
        Div(
            None if email_ready else SetUpFirst("email", EMAIL_SETUP),
            ToggleField("Email new posts to subscribers", "newsletter_auto",
                        checked=(s["newsletter_auto"] == "1"),
                        help="Off, you send the ones you choose, from Newsletter.", cls=FIELD_GAP),
            RadioGroupField("How often", "newsletter_digest",
                            [("", "Each post, as it's published"),
                             ("week", "Once a week, on Monday morning - that week's posts in one email"),
                             ("month", "Once a month, on the 1st - that month's posts in one email")],
                            selected=s["newsletter_digest"] if s["newsletter_digest"] in ("week", "month") else "",
                            help="A week or month with no new posts sends nothing.", cls=FIELD_GAP),
            ToggleField("Send the whole post", "newsletter_full", checked=(s["newsletter_full"] == "1"),
                        help="Off, the email has the summary and a link.", cls=FIELD_GAP),
            data_shown_for="newsletter_mode=builtin", hidden=m != "builtin"
        ),
        *[Div(FormField(label, Input(name=f"newsletter_{k}", value=s[f"newsletter_{k}"],
                                     cls="input input-sm w-full font-mono"), help=NEWSLETTER_HELP[k]),
              data_shown_for=f"newsletter_mode={k}", hidden=m != k, cls=FIELD_GAP)
          for k, (_, label, _, _, _) in newsletter.SERVICES.items()],
        Div(
            FormField("Heading", Input(name="newsletter_title", value=s["newsletter_title"],
                                       placeholder="Get new posts by email", cls="input input-sm w-full"),
                      help="Empty: the placeholder text.", cls=FIELD_GAP),
            FormField("Intro", Input(name="newsletter_intro", value=s["newsletter_intro"],
                                     placeholder="No spam - just the next post, when it's out. Unsubscribe any time.",
                                     cls="input input-sm w-full"),
                      help="Empty: the placeholder text.", cls=FIELD_GAP),
            # a tick in Each post shows (post_shows), here as well
            ToggleField("Show the sign-up box under each post", "newsletter_on_posts",
                        checked="newsletter" in pages.default_extras(False), cls=FIELD_GAP),
            ToggleField("Show it on the homepage too", "newsletter_on_home", checked=(s["newsletter_on_home"] == "1"),
                        help=Span("Readers can always sign up at ",
                                  A("/newsletter", href="/newsletter", target="_blank", cls="link"), ".")),
            data_shown_for="newsletter_mode!=", hidden=not m
        ),
        key="newsletter-main"
    )


SPAM_PANEL = "/admin/settings?tab=security&panel=security-spam"


def SpamNote():
    """Where the spam check went - on the Comments and messages page."""
    return P("Spam protection is in ", A("Security", href=SPAM_PANEL, cls="link font-medium"), ".",
             cls="text-sm text-base-content/70")


def ReaderPanels(s):
    """What visitors meet besides the posts: analytics, the cookie
    banner, ads and the contact form. Saved by the same handler as
    General - each form sends only its own fields (declared_fields)."""
    return Form(
        Div(
            NewsletterPanel(s),
            SettingsPanel(
                "Analytics",
                RadioGroupField(
                    "Provider", "analytics_provider",
                    [("", "None"),
                     ("cloudflare", "Cloudflare Web Analytics — free, no cookies"),
                     ("plausible", "Plausible — privacy-friendly, paid"),
                     ("google", "Google Analytics")],
                    selected=s["analytics_provider"] if s["analytics_provider"] in ANALYTICS_PROVIDERS else "",
                    cls=FIELD_GAP
                ),
                Div(FormField(
                    "Site ID",
                    Input(name="analytics_id", value=s["analytics_id"], placeholder="G-XXXXXXX or example.com",
                          cls="input input-sm w-full font-mono"),
                    help="Plausible: your site's domain. Google: the ID starting with G-. Cloudflare: the "
                         "token in its snippet. Your own visits aren't counted."
                ), data_shown_for="analytics_provider!=",
                    hidden=s["analytics_provider"] not in ANALYTICS_PROVIDERS),
                key="analytics-main"
            ),
            SettingsPanel(
                "Cookie consent",
                ToggleField(
                    "Ask visitors before anything that tracks them", "consent_banner",
                    checked=(s["consent_banner"] == "1"),
                    help="A small Accept / Decline banner, shown only when something on your site tracks "
                         "visitors.", cls=FIELD_GAP),
                P("It asks about: " + ", ".join(ads.consent_reasons(s)) + "." if ads.consent_reasons(s) else
                  "Nothing on your site tracks visitors right now, so no banner shows.",
                  cls=f"text-xs text-base-content/60 {FIELD_GAP}"),
                FormField("Message", Input(name="consent_message", value=s["consent_message"],
                                           placeholder="This site uses cookies to understand how it's read.",
                                           cls="input input-sm w-full"),
                          help="Empty: the placeholder text.", cls=FIELD_GAP),
                FormField(
                    "Privacy page",
                    Div(Input(name="consent_privacy_url", id="consent_privacy_url", value=s["consent_privacy_url"],
                              placeholder="/post/privacy", cls="input input-sm flex-1 min-w-0 join-item"),
                        LinkPickerButton("consent_privacy_url"), cls="join w-full"),
                    help="Linked from the banner." if s["consent_privacy_url"] else
                    Span("Linked from the banner. ", A("Write one from the Privacy policy template",
                                                       href="/admin/new?template=privacy", cls="link"))
                ),
                key="analytics-consent"
            ),
            SettingsPanel(
                "Ads",
                FormField("AdSense publisher ID", Input(name="adsense_client", value=s["adsense_client"],
                                                        placeholder="ca-pub-0000000000000000",
                                                        cls="input input-sm w-full font-mono"),
                          help="From AdSense, under Account information. AdSense places the ads; you won't see "
                               "them while you're logged in.",
                          cls=FIELD_GAP),
                Div(*[FormField(label, Input(name=key, value=s[key], placeholder="Ad unit ID, e.g. 1234567890",
                                             inputmode="numeric", cls="input input-sm w-full font-mono"))
                      for key, label in ads.AD_SLOTS.items()],
                    cls="grid grid-cols-1 sm:grid-cols-2 gap-2"),
                P("Spots of your own, besides the ones AdSense places: paste a display ad unit's ID.",
                  cls="fieldset-label text-xs text-base-content/60 mt-1 " + FIELD_GAP),
                ToggleField("Show ads on pages too", "adsense_on_pages", checked=(s["adsense_on_pages"] == "1"),
                            help="About, Privacy and the other pages in your menu and footer.",
                            cls=FIELD_GAP),
                # one paragraph - .alert lays its direct children out as grid columns
                Div(P(Strong("Visitors in the EU, UK and Switzerland: "),
                      "Google asks for its own consent message before showing them ads. Turn it on in AdSense, "
                      "under Privacy & messaging."),
                    cls="alert alert-info text-xs py-2"),
                key="analytics-ads"
            ),
            SettingsPanel(
                "Contact form",
                ToggleField(
                    "Turn on the contact form", "contact_enabled", checked=(s["contact_enabled"] == "1"),
                    help=Span("A page at ", A("/contact", href="/contact", target="_blank", cls="link"),
                              " where visitors can send you a message."),
                    cls=FIELD_GAP),
                Div(
                FormField("Intro", Input(name="contact_intro", value=s["contact_intro"],
                                         placeholder="Send me a message - I'll reply by email.",
                                         cls="input input-sm w-full"),
                          help="A line above the form. Empty: the placeholder text.", cls=FIELD_GAP),
                RadioGroupField(
                    "Which form", "contact_mode",
                    [("builtin", "Soloblog's own — messages arrive in Contact messages"),
                     ("embed", "One you made elsewhere — " + ", ".join(FORM_PROVIDERS))],
                    selected="embed" if s["contact_mode"] == "embed" else "builtin", cls=FIELD_GAP
                ),
                Div(
                    Div(
                        FormField("Also send to a form service",
                                  Select(Option("None", value="", selected=not s["contact_service"]),
                                         *[Option(label, value=key, selected=(key == s["contact_service"]))
                                           for key, (label, *_rest) in FORWARDERS.items()],
                                         name="contact_service", cls="select select-sm w-full")),
                        FormField("Form ID", Input(name="contact_service_id", value=s["contact_service_id"],
                                                   placeholder="xyzabcd", cls="input input-sm w-full font-mono")),
                        cls="grid grid-cols-1 sm:grid-cols-2 gap-2"
                    ),
                    P("Each message goes to that service as well. Formspree, Getform, Basin and Formcarry: the "
                      "ID in the form's address. FormSubmit: your email address.",
                      cls="fieldset-label text-xs text-base-content/60 mt-1"),
                    data_shown_for="contact_mode=builtin", hidden=s["contact_mode"] == "embed"
                ),
                Div(
                    FormField("Form link", Input(name="contact_form_url", type="url", value=s["contact_form_url"],
                                                 placeholder="https://tally.so/r/abc123", cls="input input-sm w-full"),
                              help="The form's share link."),
                    data_shown_for="contact_mode=embed", hidden=s["contact_mode"] != "embed"
                ),
                data_shown_for="contact_enabled=1", hidden=s["contact_enabled"] != "1"),
                key="messages-contact"
            ),
            SettingsPanel(
                "Spam protection",
                RadioGroupField(
                    "Extra check", "captcha_provider",
                    [("", "None"),
                     ("turnstile", "Cloudflare Turnstile — free, usually invisible"),
                     ("hcaptcha", "hCaptcha — free")],
                    selected=s["captcha_provider"] if s["captcha_provider"] in captcha.PROVIDERS else "",
                    help="On comments, the contact form, newsletter sign-ups and members signing in.",
                    cls=FIELD_GAP
                ),
                Div(
                    FormField("Site key", Input(name="captcha_site_key", value=s["captcha_site_key"],
                                                cls="input input-sm w-full font-mono")),
                    FormField("Secret key", SecretInput("captcha_secret", s["captcha_secret"],
                                                  cls="input input-sm w-full font-mono")),
                    cls="grid grid-cols-1 sm:grid-cols-2 gap-2"
                ),
                P("Both are in the service's dashboard once you add your site.",
                  cls="fieldset-label text-xs text-base-content/60 mt-1"),
                key="security-spam"
            ),
            SettingsPanel(
                "Notifications",
                Div(Div(ToggleField("Email me about new comments", "notify_comments",
                                    checked=(s["notify_comments"] == "1"),
                                    help="When one is waiting for your approval.", cls=FIELD_GAP),
                        data_shown_for="comments_system=", hidden=bool(s["comments_system"])),
                    data_shown_for="comments_enabled=1", hidden=s["comments_enabled"] != "1"),
                Div(Div(FormField("Also email messages to",
                                  Input(name="contact_email", type="email", value=s["contact_email"],
                                        placeholder="you@example.com", cls="input input-sm w-full"),
                                  cls=FIELD_GAP),
                        data_shown_for="contact_mode=builtin", hidden=s["contact_mode"] == "embed"),
                    data_shown_for="contact_enabled=1", hidden=s["contact_enabled"] != "1"),
                FormField(
                    "Send new comments and messages to",
                    Input(name="comment_webhook_url", value=s["comment_webhook_url"],
                          placeholder="https://hooks.slack.com/...", cls="input input-sm w-full"),
                    help="A webhook URL from Slack or Discord."
                ),
                key="messages-notify"
            ),
            cls=f"flex flex-col gap-3 {SECTION_GAP}"
        ),
        SaveBar(),
        hx_post="/admin/settings/messages", hx_target="#save-status", hx_swap="outerHTML show:none focus-scroll:false",
        data_declare_fields=True
    )


# env vars config.py reads at startup - name, plus a one-line
# explanation of what it does. SESSION_SECRET is the only genuine
# secret here (its value is never shown, only whether it's actually
# set); the other four are plain deployment config, shown for the
# same "is this actually set" visibility but never worth calling a
# secret, and their current effective value is safe to print.
ENV_VARS = [
    ("SESSION_SECRET", "Keeps logins safe. Made for you if you don't set one."),
    ("BASE_URL", Span("The site URL. Without it, ", A("the one you set", href="/admin/settings?tab=url",
                                                            cls="link"), " is used.")),
    ("SITE_TITLE", "Only a new site's first name."),
    ("SETUP_TOKEN", "A code you choose, 16 characters or more, to start setting up without reading the "
                    "server's log."),
    ("DATA_DIR", "Where your posts, images and database are kept."),
    ("ENV", "\"production\" on a live site."),
    ("SMTP_HOST", "Your email provider's SMTP server - sends your email, until you set it up in Settings."),
    ("SMTP_PORT", "Its port: 587, or 465. Empty: 587."),
    ("SMTP_USER", "The username, usually your email address."),
    ("SMTP_PASSWORD", "The password - an app password for most providers."),
    ("SMTP_FROM", "The address your email comes from."),
    ("RESEND_API_KEY", "Sends through Resend instead - for a host that blocks SMTP. With SMTP set too, "
                       "it's used when SMTP fails."),
    ("RESEND_FROM", "The address Resend sends from."),
    ("ADMIN_EMAIL", "Your email, until you set one in Settings."),
]


# optional storage settings (storage.py) - "Not set" is a normal state
# for these, not a warning
S3_ENV_VARS = [
    ("S3_BUCKET", "Your bucket's name, exactly as your storage company shows it. With the two keys, it turns cloud "
                  "storage on."),
    ("S3_ENDPOINT", "Your bucket's S3 endpoint URL, from your storage company. Leave it out "
                    "for Amazon S3."),
    ("S3_REGION", "The bucket's region - \"auto\" for Cloudflare R2."),
    ("S3_ACCESS_KEY_ID", "The access key's ID - Backblaze calls it keyID."),
    ("S3_SECRET_ACCESS_KEY", "The access key's secret - Backblaze calls it applicationKey."),
    ("S3_PREFIX", "Optional: a folder in the bucket, if it holds anything else."),
    ("BACKUP_PASSPHRASE", "Optional: locks the backups and images in the bucket. Without it they can't be restored - "
                          "keep it in a password manager."),
]
SECRET_ENV = {"SESSION_SECRET", "SETUP_TOKEN", "RESEND_API_KEY", "SMTP_PASSWORD", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY", "BACKUP_PASSPHRASE"}
OPTIONAL_ENV = {name for name, _ in S3_ENV_VARS} | {"SETUP_TOKEN", "RESEND_API_KEY", "RESEND_FROM", "ADMIN_EMAIL",
                                                   "SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM"}


def EnvStatusRow(name, help_text):
    raw = os.environ.get(name)
    effective = getattr(config, name, "")
    is_secret = name in SECRET_ENV
    # a warning only where the default is wrong for a real site - a
    # default title, data folder or mode is just right, and "Using
    # default" in warning yellow read as a problem to fix
    if name == "SESSION_SECRET" and effective == config.DEFAULT_SECRET:
        badge = Span("Insecure default", cls="badge badge-error badge-sm")
    elif name == "SESSION_SECRET" and config.SESSION_SECRET_FROM == "file":  # noqa: S105 - a source name, not a secret
        badge = Span("Made for you", cls="badge badge-success badge-sm")
    elif name == "BASE_URL" and not config.BASE_URL_FIXED and settings.get("site_url"):
        badge = Span("From Settings", cls="badge badge-success badge-sm")
    elif raw:  # a blank value in an env file counts as unset, same as config.py
        badge = Span("Set", cls="badge badge-success badge-sm")
    elif name == "BASE_URL" and effective.startswith("http://localhost"):
        badge = Span("Not set", cls="badge badge-warning badge-sm")
    elif name == "BASE_URL":
        badge = Span("Detected", cls="badge badge-ghost badge-sm")
    elif name in OPTIONAL_ENV:
        badge = Span("Not set", cls="badge badge-ghost badge-sm")
    else:
        badge = Span("Default", cls="badge badge-ghost badge-sm")
    if name == "SITE_TITLE":
        # what the site is actually called - not the variable's own value,
        # which only a brand-new site ever uses
        effective = f"Your title: {settings.get('site_title')}"
    return Div(
        Div(Span(name, cls="font-mono text-sm font-medium"), badge, cls="flex items-center justify-between gap-2"),
        P(help_text, cls="text-xs text-base-content/60 mt-0.5"),
        None if is_secret else P(effective or "(empty)", cls="text-xs font-mono text-base-content/50 mt-1"),
        cls="py-2 border-b-[length:var(--border)] border-base-300 last:border-0"
    )


def SmtpFields(s, hidden):
    """An email account: its provider picked from a list fills in the
    server - only "Another provider" asks for one."""
    chosen = s["smtp_provider"] if s["smtp_provider"] in mail.SMTP_PRESETS else ""
    return Div(
        H2("Your email account", cls="text-base font-semibold mb-1"),
        FormField("Your email provider", Select(
            *[Option(name, value=key, selected=key == chosen) for key, (name, *_) in mail.SMTP_PRESETS.items()],
            Option("Another provider", value="", selected=not chosen),
            name="smtp_provider", cls="select select-sm w-full"), cls=FIELD_GAP),
        *[P(tip, data_shown_for=f"smtp_provider={key}", hidden=key != chosen,
            cls=f"text-sm {'text-warning' if key == 'outlook' else 'text-base-content/70'} {FIELD_GAP}")
          for key, (*_, tip) in mail.SMTP_PRESETS.items()],
        Div(
            Div(
                FormField("Server", Input(name="smtp_host", value=s["smtp_host"], placeholder="smtp.example.com",
                                          cls="input input-sm w-full"),
                          help=("Set on your host. " if settings.on_host("smtp_host") else "")
                          + "Your email provider's SMTP server."),
                FormField("Port", Input(name="smtp_port", value=s["smtp_port"], placeholder="587",
                                        cls="input input-sm w-full")),
                cls=f"grid grid-cols-1 sm:grid-cols-[1fr_8rem] gap-3 {FIELD_GAP}"
            ),
            FormField("Username", Input(name="smtp_user", value=s["smtp_user"], cls="input input-sm w-full"),
                      cls=FIELD_GAP),
            data_shown_for="smtp_provider=", hidden=bool(chosen)
        ),
        Div(
            FormField("Email address", Input(name="smtp_from", value=s["smtp_from"], type="email",
                                             placeholder="you@example.com", cls="input input-sm w-full"),
                      help=("Set on your host. " if settings.on_host("smtp_from") else "")
                      + "Emails come from it, with your site's name as the sender.", cls=FIELD_GAP),
            FormField("Password", SecretInput("smtp_password", settings.stored("smtp_password"),
                                              cls="input input-sm w-full"),
                      help=HOST_SET if settings.on_host("smtp_password") else None),
            data_shown_for="smtp_provider!=outlook", hidden=chosen == "outlook"
        ),
        data_shown_for="email_provider=smtp", hidden=hidden, cls="mt-6"
    )


HOST_SET = "Set on your host. Type one here to use it instead."


def SecretPanels(s):
    provider = s["email_provider"]
    return Form(
        Div(
            SettingsPanel(
                "Environment",
                P("Set on your host, not here - as secrets or in a .env file.",
                  cls=f"text-xs text-base-content/60 {FIELD_GAP}"),
                *[EnvStatusRow(name, help_text) for name, help_text in ENV_VARS],
                key="integrations-env"
            ),
            SettingsPanel(
                "Updates",
                P("Gives you an Update now button when a new version is out.",
                  cls=f"text-sm text-base-content/70 {FIELD_GAP}"),
                FormField("Update hook", Input(name="update_hook_url", value=s["update_hook_url"],
                                               placeholder="http://watchtower:8080/v1/update",
                                               cls="input input-sm w-full font-mono"),
                          help=Span("Your host's deploy hook, or Watchtower's URL with Docker Compose. ",
                                    A("How to set it up", href="/admin/help?tab=deployment#set-up-the-update-now-button",
                                      cls="link"),
                                    "."),
                          cls=FIELD_GAP),
                FormField("Token", SecretInput("update_hook_token", s["update_hook_token"], cls="input input-sm w-full font-mono"),
                          help="Watchtower's WATCHTOWER_HTTP_API_TOKEN. Empty for a deploy hook."),
                key="integrations-updates"
            ),
            SettingsPanel(
                "Sending email",
                RadioGroupField(
                    "Send email with", "email_provider",
                    [("api", "Resend — works on every host (Recommended)"),
                     ("smtp", "An email account you have (SMTP)"),
                     ("", "Nothing — no emails")],
                    selected=provider, default=None,
                    help="For sign-ins, comment confirmations, the newsletter and messages to you."
                ),
                Div(
                    H2("Resend", cls="text-base font-semibold mb-1"),
                    P("Make a free account at resend.com, add your own domain there, then paste its API key. "
                      "No domain yet? Use an email account you have.",
                      cls="text-sm text-base-content/60 mb-3"),
                    FormField("API key", SecretInput("email_api_key", settings.stored("email_api_key"),
                                                cls="input input-sm w-full"),
                              help=HOST_SET if settings.on_host("email_api_key") else None, cls=FIELD_GAP),
                    FormField("From address", Input(name="email_api_from", value=s["email_api_from"],
                                                     placeholder="hello@yourdomain.com", cls="input input-sm w-full"),
                              help=("Set on your host. " if settings.on_host("email_api_from") else "")
                              + "An address at the domain you verified in Resend - not resend.dev, which only "
                                "reaches you. Emails show your site's name as the sender."),
                    data_shown_for="email_provider=api", hidden=provider != "api", cls="mt-6"
                ),
                SmtpFields(s, hidden=provider != "smtp"),
                # a long reason takes its own line on a phone, not a squeezed column beside the button
                Div(Span(id="email-test-status", data_status_slot=True, role="status", cls="text-xs flex-1 min-w-48"),
                    # it saves what's above first - a test of what's on screen
                    Button(SEND_SVG, Span("Send a test email", cls="ml-1"), type="button", cls="btn btn-sm ml-auto",
                           hx_post="/admin/email/test", hx_include="closest form", hx_target="#email-test-status",
                           hx_swap="outerHTML"),
                    cls="flex flex-wrap items-center gap-2 mt-4")
                if s["admin_email"] else
                P("Add your email above to send yourself a test.", cls="text-xs text-base-content/60 mt-4"),
                key="email-sending"
            ),
            SettingsPanel(
                "Stock photos",
                P("Search free photos from the image picker. All three keys are free.",
                  cls=f"text-sm text-base-content/60 {FIELD_GAP}"),
                FormField("Pixabay API key", SecretInput("pixabay_api_key", s["pixabay_api_key"], cls="input input-sm w-full"),
                           help="From pixabay.com/api/docs", cls=FIELD_GAP),
                FormField("Pexels API key", SecretInput("pexels_api_key", s["pexels_api_key"], cls="input input-sm w-full"),
                           help="From pexels.com/api", cls=FIELD_GAP),
                FormField("Unsplash access key", SecretInput("unsplash_access_key", s["unsplash_access_key"], cls="input input-sm w-full"),
                           help="From unsplash.com/developers"),
                key="integrations-stock"
            ),
            cls=f"flex flex-col gap-3 {SECTION_GAP}"
        ),
        SaveBar(),
        hx_post="/admin/settings/integrations", hx_target="#save-status", hx_swap="outerHTML show:none focus-scroll:false",
        data_declare_fields=True
    )


def LanguagesPanel(s):
    chosen = set(translate.targets(s))
    status = None
    if translate.enabled(s):
        err = translate.last_error()
        n = translate.count()
        status = Div(
            P(f"{n} translation{'s' if n != 1 else ''} saved"
              + (f", {translate.pending()} on the way." if translate.pending() else "."),
              cls="text-sm text-base-content/70"),
            P(f"Last problem: {err['message']}", cls="text-xs text-error") if err["message"] else None,
            Div(Button(SYNC_SVG, Span("Translate every post now", cls="ml-1"), type="button", cls="btn btn-sm",
                       hx_post="/admin/translate/all", hx_target="#translate-status", hx_swap="innerHTML"),
                Span(id="translate-status", role="status", cls="text-xs"), cls="flex items-center gap-3 mt-2"),
            cls=FIELD_GAP)
    by_name = sorted(translate.LANGUAGES.items(), key=lambda x: x[1])
    return SettingsPanel(
        "Language",
        FormField("Posts are written in", Combobox(
            "site_language", [(code, name, None) for code, name in by_name], translate.site_language(s),
            "Posts are written in", search="Type a language…"),
            help="Helps screen readers and search engines.",
            cls=FIELD_GAP),
        Div(FormField("Spelling", EnglishSelect(s), help="For dates and the text Soloblog adds, like buttons."),
            data_shown_for="site_language=en", hidden=translate.site_language(s) != "en"),
        key="language-site"
    ), SettingsPanel(
        "Translation",
        FormField("Translation service", Select(
            *[Option(label, value=key, selected=(key == s["translate_provider"]))
              for key, label in translate.PROVIDERS.items()],
            name="translate_provider", cls="select select-sm w-full"),
            help="Offers each post in the languages you select, translated by the service.",
            cls=FIELD_GAP),
        FormField("API key", SecretInput("translate_api_key", s["translate_api_key"],
                                   cls="input input-sm w-full"),
                  help="DeepL: from deepl.com/pro-api. Google: a Cloud Translation key. LibreTranslate: only if "
                       "your server asks for one.", cls=FIELD_GAP),
        FormField("LibreTranslate server", Input(name="translate_url", value=s["translate_url"],
                                                 placeholder="https://libretranslate.com", cls="input input-sm w-full"),
                  help="Only if you run your own.",
                  cls=FIELD_GAP),
        FormField("Offer posts in", Div(
            *[Label(Input(type="checkbox", name="translate_languages", value=code, checked=code in chosen,
                          cls="checkbox checkbox-xs"), Span(name, cls="text-sm"),
                    cls="flex items-center gap-1.5 cursor-pointer") for code, name in by_name],
            cls="grid grid-cols-2 sm:grid-cols-3 gap-1.5"),
            help="Each one is another translation of every post - check the service's prices.",
            cls=FIELD_GAP),
        status,
        key="language-translation"
    )


def FediversePanel(s):
    from soloblog import fediverse
    problem = fediverse.reachable()
    on = s["activitypub_enabled"] == "1"
    followers = fediverse.list_followers(50) if on else []
    count = fediverse.follower_count() if on else 0
    return SettingsPanel(
        "Fediverse",
        P("People on Mastodon, Threads and the rest of the fediverse can follow your site. New posts show in "
          "their timelines, and their replies arrive in Comments.", cls=f"text-sm text-base-content/60 {FIELD_GAP}"),
        Alert(f"Your site needs a public URL first: {problem}", "warning")
        if problem else None,
        ToggleField("Let people follow this blog", "activitypub_enabled", checked=on, cls=FIELD_GAP),
        Div(
        FormField("Username", Div(
            Input(name="activitypub_username", value=fediverse.username(s), pattern="[A-Za-z0-9_]{1,30}",
                  cls="input input-sm flex-1 min-w-0 join-item font-mono"),
            Span(f"@{fediverse.host() or 'your.site'}", cls="join-item flex items-center px-2 text-xs "
                 "text-base-content/60 bg-base-200 border border-base-300 rounded-r-field"),
            cls="join w-full"),
            help="Letters, numbers and _. Changing it later loses your followers.", cls=FIELD_GAP),
        Div(
            P(Span("Your handle: ", cls="text-base-content/60"), Span(fediverse.handle(s), cls="font-mono"),
              Button(COPY_SVG, type="button", cls="btn btn-xs btn-ghost ml-1 tooltip", data_tip="Copy handle", aria_label="Copy handle",
                     data_copy=fediverse.handle(s)), cls="text-sm"),
            P(f"{count} follower{'s' if count != 1 else ''}", cls="text-sm text-base-content/70"),
            Ul(*[Li(f["handle"], cls="font-mono text-xs") for f in followers],
               cls="list-disc pl-5 max-h-40 overflow-y-auto mt-1") if followers else None,
            # the newest 50 are listed - the count says there are more
            P(f"And {count - len(followers)} more", cls="text-xs text-base-content/60 mt-1")
            if count > len(followers) else None,
            cls=FIELD_GAP) if on and not problem else None,
        data_shown_for="activitypub_enabled=1", hidden=not on),
        key="sharing-fediverse"
    )


def WebmentionsPanel(s):
    return SettingsPanel(
        "Webmentions",
        P("When other blogs link to, like or reply to your posts, it shows under them.",
          cls=f"text-sm text-base-content/60 {FIELD_GAP}"),
        ToggleField("Accept webmentions", "webmention_receive", checked=(s["webmention_receive"] == "1"),
                    cls=FIELD_GAP),
        ToggleField("Approve replies and mentions first", "webmention_moderate",
                    checked=(s["webmention_moderate"] == "1"),
                    help="Likes and reposts show straight away.", cls=FIELD_GAP),
        ToggleField("Tell sites when I link to them", "webmention_send", checked=(s["webmention_send"] == "1")),
        key="sharing-webmentions"
    )


def SharePanel(s):
    return SettingsPanel(
        "Sharing",
        FormField(
            "Share image",
            Div(Input(name="share_image_url", id="share_image_url", value=s["share_image_url"],
                      placeholder="/uploads/share.webp", cls="input input-sm flex-1 min-w-0 join-item"),
                MediaPickerButton("share_image_url"), cls="join w-full"),
            help="When a page without a cover is shared. About 1200 × 630 works best."),
        key="sharing-main"
    )


def BlueskyPanel(s):
    return SettingsPanel(
        "Share on Bluesky",
        P("Each new post is shared from your Bluesky account as it's published, with a link back.",
          cls=f"text-sm text-base-content/60 {FIELD_GAP}"),
        ToggleField("Post to Bluesky", "crosspost_bluesky", checked=(s["crosspost_bluesky"] == "1"),
                    cls=FIELD_GAP),
        Div(
            FormField("Bluesky handle", Input(name="bluesky_handle", value=s["bluesky_handle"],
                                              placeholder="you.bsky.social", cls="input input-sm w-full font-mono")),
            FormField("App password", SecretInput("bluesky_app_password", s["bluesky_app_password"], placeholder="xxxx-xxxx-xxxx-xxxx",
                                            cls="input input-sm w-full font-mono")),
            cls="grid grid-cols-1 sm:grid-cols-2 gap-2"
        ),
        P("An app password, from Bluesky's Privacy and security settings - not your own password.",
          cls="fieldset-label text-xs text-base-content/60 mt-1"),
        key="sharing-bluesky"
    )


def MastodonPanel(s):
    return SettingsPanel(
        "Share on Mastodon",
        P("Each new post is shared from your Mastodon account as it's published, with a link back.",
          cls=f"text-sm text-base-content/60 {FIELD_GAP}"),
        ToggleField("Post to Mastodon", "crosspost_mastodon", checked=(s["crosspost_mastodon"] == "1"),
                    cls=FIELD_GAP),
        Div(
            FormField("Server", Input(name="mastodon_instance", value=s["mastodon_instance"],
                                      placeholder="https://mastodon.social", cls="input input-sm w-full font-mono")),
            FormField("Access token", SecretInput("mastodon_token", s["mastodon_token"],
                                            cls="input input-sm w-full font-mono")),
            cls="grid grid-cols-1 sm:grid-cols-2 gap-2"
        ),
        P("Make an application in Mastodon's Development settings, with only write:statuses, and copy its "
          "access token.", cls="fieldset-label text-xs text-base-content/60 mt-1"),
        key="sharing-mastodon"
    )


def SitePanels(s):
    """Search engines, languages, the fediverse, sharing, custom code and
    redirects - how the site meets the rest of the web."""
    return Form(
        Div(
            SettingsPanel(
                "Site URL",
                FormField("URL", Input(value=config.BASE_URL, disabled=True, cls="input input-sm w-full font-mono"),
                          help="Set on your host, as BASE_URL.")
                if config.BASE_URL_FIXED else
                FormField("URL", Input(name="site_url", id="site_url", value=s.get("site_url"), type="url",
                                           placeholder=config.PLATFORM_URL or "https://example.com",
                                           spellcheck="false",
                                           cls="input input-sm w-full font-mono"),
                          help="Change it when you move to a new domain." +
                               (" Empty: the URL your host gave it." if config.PLATFORM_URL else "")),
                key="url-site"
            ),
            SettingsPanel(
                "Search engines",
                FormField("Description",
                          Input(name="meta_description", value=s["meta_description"], placeholder=s["tagline"],
                                cls="input input-sm w-full"),
                          help="Shown under your site's name in search results. Empty: your tagline.", cls=FIELD_GAP),
                ToggleField("Hide this site from search engines", "search_noindex",
                            checked=(s["search_noindex"] == "1"),
                            help="For a private or unfinished site."),
                key="url-search"
            ),
            SettingsPanel(
                "Verify with Google and Bing",
                P("Only if Google Search Console or Bing Webmaster Tools asks you to prove the site is yours.",
                  cls=f"text-sm text-base-content/60 {FIELD_GAP}"),
                FormField("Google Search Console", Input(name="google_site_verification",
                                                         value=s["google_site_verification"],
                                                         placeholder="The content=\"...\" part of the HTML tag",
                                                         cls="input input-sm w-full font-mono"),
                          help="From Search Console's HTML tag - just the code.",
                          cls=FIELD_GAP),
                FormField("Bing Webmaster Tools", Input(name="bing_site_verification",
                                                        value=s["bing_site_verification"],
                                                        cls="input input-sm w-full font-mono"),
                          help="The msvalidate.01 code."),
                key="url-verify"
            ),
            *LanguagesPanel(s),
            FediversePanel(s),
            WebmentionsPanel(s),
            SharePanel(s),
            BlueskyPanel(s),
            MastodonPanel(s),
            SettingsPanel(
                "Custom code",
                FormField("In <head>", Textarea(s["custom_head"], name="custom_head", rows="4", spellcheck="false",
                                                placeholder="<meta ...> or <script ...></script>",
                                                cls="textarea textarea-sm w-full font-mono text-xs"),
                          help="On every page of your site. Only paste code you trust.", cls=FIELD_GAP),
                ToggleField("This code sets cookies or tracks visitors", "custom_head_consent",
                            checked=s.get("custom_head_consent") == "1",
                            help="Then it waits until a visitor accepts cookies.", cls=FIELD_GAP),
                FormField("Custom CSS", Textarea(s["custom_css"], name="custom_css", rows="6", spellcheck="false",
                                                 placeholder=".prose h2 { letter-spacing: -0.01em; }",
                                                 cls="textarea textarea-sm w-full font-mono text-xs"),
                          help="Your palette's colours are var(--color-primary) and the like."),
                key="integrations-code"
            ),
            SettingsPanel(
                "Redirects",
                FormField("Old and new URLs",
                          Textarea(s["redirects"], name="redirects", rows="4", spellcheck="false",
                                   placeholder="/old-page /new-page\n/2019/* /archive\n/shop https://shop.example.com",
                                   cls="textarea textarea-sm w-full font-mono text-xs"),
                          help="One a line: the old URL, a space, and the new one. End the old one with * "
                               "for everything under it."),
                key="url-redirects"
            ),
            cls=f"flex flex-col gap-3 {SECTION_GAP}"
        ),
        SaveBar(),
        hx_post="/admin/settings/url", hx_target="#save-status", hx_swap="outerHTML show:none focus-scroll:false",
        data_declare_fields=True
    )


def SupportLinks(s):
    """The support links you have, and "Add a support link" for the rest -
    not six empty boxes. Picking one shows its box (data-shown-for); it's
    kept when you Save."""
    have = [(key, label, ph) for key, label, ph in SUPPORT_PLATFORMS if s[f"support_{key}"]]
    rest = [(key, label, ph) for key, label, ph in SUPPORT_PLATFORMS if not s[f"support_{key}"]]
    field = lambda key, label, ph: FormField(  # noqa: E731
        label, Input(name=f"support_{key}", type="url", value=s[f"support_{key}"], placeholder=ph,
                     cls="input input-sm w-full"), cls=FIELD_GAP)
    picker = FormField("Add another" if have else "Add a support link", Select(
        Option("Choose…", value="", selected=True), *[Option(label, value=key) for key, label, _ in rest],
        name="support_add", cls="select select-sm w-full"), cls=FIELD_GAP) if rest else None
    return (*[field(*p) for p in have],
            # choosing here isn't a change to save on its own
            Div(picker, *[Div(field(*p), data_shown_for=f"support_add={p[0]}", hidden=True) for p in rest],
                data_autosave_off="1") if rest else None)


def MembersTab(s):
    """The members area (members.py): readers who join with their email and
    sign in by an emailed link, to read the posts that are for members."""
    from soloblog import mail
    return Form(
        Div(
            SettingsPanel(
                "Members",
                ToggleField("Let readers become members", "members_enabled", checked=s.get("members_enabled") == "1",
                            help="They join with their email and sign in with a link - no passwords. Each post "
                                 "can then be for everyone, members or paid members.", cls=FIELD_GAP),
                Div(
                None if mail.can_send() else SetUpFirst("email", EMAIL_SETUP),
                ToggleField("Show Sign in in the header", "members_header", checked=s.get("members_header") != "0",
                            cls=FIELD_GAP),
                FormField("Who can comment", Select(
                    *[Option(label, value=value, selected=(s.get("members_comments") or "everyone") == value,
                             data_default=value == "everyone" or None)
                      for value, label in (("everyone", "Everyone"), ("members", "Members"),
                                           ("paid", "Paid members"))],
                    name="members_comments", cls="select select-sm w-full"),
                    cls=FIELD_GAP),
                FormField("On the join page", Input(name="members_intro", value=s.get("members_intro"),
                                                    maxlength="300",
                                                    placeholder="Members can read every members-only post. It's free.",
                                                    cls="input input-sm w-full"),
                          help="A line on the page where readers join. Empty: the placeholder text.", cls=FIELD_GAP),
                FormField("Welcome email", Textarea(s.get("members_welcome"), name="members_welcome", rows="4",
                                                    maxlength="3000",
                                                    placeholder="e.g. Thanks for joining! Here's where to start…",
                                                    cls="textarea textarea-sm w-full"),
                          help="Sent when someone joins. Empty: none."),
                P(A("See your members", href="/admin/members", cls="link"), cls="text-xs text-base-content/60 mt-3"),
                data_shown_for="members_enabled=1", hidden=s.get("members_enabled") != "1"),
                key="members-on"
            ),
            PaidMembersPanel(s),
            cls=f"flex flex-col gap-3 {SECTION_GAP}"
        ),
        SaveBar(),
        hx_post="/admin/settings/members", hx_target="#save-status", hx_swap="outerHTML show:none focus-scroll:false",
        data_declare_fields=True
    )


def PaidMembersPanel(s):
    """Stripe: a key, the prices, a trial and tax - Soloblog sets up the
    rest itself (stripe_members.set_up) when it's saved."""
    from soloblog import stripe_members as pay
    key = s.get("stripe_key", "")
    if not key:
        state = Span("Not set up", cls="badge badge-sm badge-ghost")
    elif pay.ready(s):
        state = Span("Test mode", cls="badge badge-sm badge-warning") if "_test_" in key else \
            Span("Live", cls="badge badge-sm badge-success")
    else:
        state = Span("Not finished", cls="badge badge-sm badge-warning")
    currency = s.get("members_currency") or "usd"
    return SettingsPanel(
        "Paid members",
        Div(Span("Payments", cls="text-sm"), state, cls=f"flex items-center justify-between {FIELD_GAP}"),
        P("Readers pay through Stripe, and the money goes to your Stripe account.",
          cls=f"text-xs text-base-content/60 {FIELD_GAP}"),
        FormField("Stripe key", SecretInput("stripe_key", key, placeholder="rk_test_…", cls="input input-sm w-full"),
                  help=Span("A restricted key from Stripe - ",
                            A("how to make one", href="/admin/help?tab=grow#let-readers-pay", cls="link"),
                            ". Try a test key first."),
                  cls=FIELD_GAP),
        Div(FormField("Currency", Combobox(
                "members_currency", [(code, f"{code.upper()} - {pay.CURRENCIES[code][0].strip()}", None)
                                     for code in sorted(pay.CURRENCIES)], currency, "Currency",
                search="Type a currency…")),
            FormField("A month", Input(name="members_price_month", value=s.get("members_price_month"),
                                       inputmode="decimal", placeholder="Not offered", cls="input input-sm w-full")),
            FormField("A year", Input(name="members_price_year", value=s.get("members_price_year"),
                                      inputmode="decimal", placeholder="Not offered", cls="input input-sm w-full")),
            cls=f"grid grid-cols-1 sm:grid-cols-3 gap-3 {FIELD_GAP}"),
        P("Leave one empty to offer only the other. People already paying keep their price.",
          cls=f"text-xs text-base-content/60 {FIELD_GAP}"),
        FormField("Free trial", Div(Input(type="number", name="members_trial_days", min="0", max="365",
                                          value=s.get("members_trial_days") or "0",
                                          cls="input input-sm w-24 join-item"),
                                    Span("days", cls="btn btn-sm join-item pointer-events-none"), cls="join"),
                  help="0 for none.", cls=FIELD_GAP),
        ToggleField("Add sales tax with Stripe Tax", "members_tax", checked=s.get("members_tax") == "1",
                    help="Turn on Stripe Tax in your Stripe account first - it has its own fee."),
        key="members-paid", open_=bool(key)
    )


def BannerTab(s):
    return Form(
        Div(
            SettingsPanel(
                "Content",
                ToggleField(
                    "Show a banner above your posts", "banner_enabled", checked=(s["banner_enabled"] == "1"),
                    help="A big welcome at the top of your homepage.",
                    cls=FIELD_GAP
                ),
                FormField("Heading", Input(name="banner_heading", value=s["banner_heading"],
                                            placeholder="e.g. Welcome to my blog", cls="input input-sm w-full"),
                           help="Empty: no banner.", cls=FIELD_GAP),
                FormField("Subheading",
                           Input(name="banner_subheading", value=s["banner_subheading"],
                                 placeholder=s["tagline"] or "A short line under the heading",
                                 cls="input input-sm w-full"),
                           help="Empty: your tagline." if s["tagline"] else "Empty: none."),
                key="banner-content"
            ),
            SettingsPanel(
                "Button",
                Div(
                    FormField("Button text", Input(name="banner_button_text", value=s["banner_button_text"],
                                                     placeholder="e.g. Read the latest post",
                                                     cls="input input-sm w-full"),
                              help="Empty: no button."),
                    FormField("Button link",
                               Div(
                                   Input(name="banner_button_url", id="banner_button_url", value=s["banner_button_url"],
                                         placeholder="/post/my-latest-post",
                                         cls="input input-sm flex-1 min-w-0 join-item"),
                                   LinkPickerButton("banner_button_url"),
                                   cls="join w-full"
                               )),
                    cls="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-1"
                ),
                P("Leave both empty for no button.",
                  cls="text-xs text-base-content/50"),
                key="banner-button"
            ),
            SettingsPanel(
                "Background",
                FormField(
                    "Background image",
                    Div(
                        Input(name="banner_image_url", id="banner_image_url", value=s["banner_image_url"],
                              placeholder="/uploads/hero-bg.webp", cls="input input-sm flex-1 join-item"),
                        MediaPickerButton("banner_image_url"),
                        cls="join"
                    ),
                    help="Behind the banner's text.", cls=FIELD_GAP
                ),
                RadioGroupField("Width", "banner_width", list(pages.COVER_WIDTHS.items()),
                                s["banner_width"] if s["banner_width"] in pages.COVER_WIDTHS else "column"),
                key="banner-background"
            ),
            cls=f"flex flex-col gap-3 {SECTION_GAP}"
        ),
        SaveBar(),
        hx_post="/admin/settings/banner", hx_target="#save-status", hx_swap="outerHTML show:none focus-scroll:false",
        data_declare_fields=True
    )


def SocialLinksList(s):
    """One row per platform, dragged into the order they show in."""
    return SortableList("social_order", [
        (key, Div(Span(icon, cls="opacity-60 shrink-0"),
                  Input(name=f"social_{key}", value=s.get(f"social_{key}"), placeholder=f"{label} URL",
                        aria_label=f"{label} URL", cls="input input-sm w-full"),
                  cls="flex items-center gap-2"))
        for key, label, icon, _ in ordered_social_platforms(s)])


def ProfileTab(s):
    return Form(
        Div(
            SettingsPanel(
                "Bio",
                FormField("Author name", Input(name="author_name", value=s["author_name"],
                                                cls="input input-sm w-full"),
                           help="Shown as the byline on every post.", cls=FIELD_GAP),
                FormField(
                    "Avatar",
                    Div(
                        Input(name="author_avatar_url", id="author_avatar_url", value=s["author_avatar_url"],
                              placeholder="/uploads/avatar.webp", cls="input input-sm flex-1 join-item"),
                        MediaPickerButton("author_avatar_url"),
                        cls="join"
                    ),
                    help="Beside your name, under posts and in the footer.", cls=FIELD_GAP
                ),
                FormField("Bio", Textarea(s["author_bio"], name="author_bio", rows="3",
                                           cls="textarea textarea-sm w-full"),
                           help="A line or two about you, under each post."),
                key="profile-bio"
            ),
            SettingsPanel(
                "Social links",
                FormField(
                    "Social links",
                    SocialLinksList(s),
                    help="Drag to reorder - share buttons follow the same order.",
                    cls=FIELD_GAP
                ),
                FormField(
                    "More links",
                    Textarea(s["extra_social_links"], name="extra_social_links", rows="3",
                             placeholder="TikTok|https://tiktok.com/@you|star\nThreads|https://threads.net/@you",
                             cls="textarea textarea-sm w-full font-mono text-xs"),
                    help="Any others, one a line: Name|URL. Add |icon to choose one: "
                         f"{', '.join(EXTRA_LINK_ICONS)}."
                ),
                key="profile-links"
            ),
            SettingsPanel(
                "Support",
                P("Where readers can support your writing.",
                  cls="text-sm text-base-content/60 mb-3"),
                *SupportLinks(s),
                FormField("Message", Input(name="support_message", value=s["support_message"],
                                           placeholder="e.g. Enjoyed this? You can buy me a coffee.",
                                           cls="input input-sm w-full"),
                          help="Above the buttons. Empty: none.", cls=FIELD_GAP),
                ToggleField("Show under each post", "support_on_posts",
                            checked="support" in pages.default_extras(False),
                            help="Each post or page can choose its own."),
                key="profile-support"
            ),
            SettingsPanel(
                "Links page",
                ToggleField(
                    "Turn on the links page", "links_enabled", checked=(s["links_enabled"] == "1"),
                    help=Span("Your photo, bio and a stack of links, at ",
                              A("/links", href="/links", target="_blank", cls="link"),
                              " - the link to put in a social profile."),
                    cls=FIELD_GAP
                ),
                FormField(
                    "Links",
                    Textarea(s["links_items"], name="links_items", rows="4",
                             placeholder="My newsletter|https://example.com/newsletter\nPodcast|https://example.com/podcast",
                             cls="textarea textarea-sm w-full font-mono text-xs"),
                    help="One a line: Name|URL.", cls=FIELD_GAP
                ),
                FormField(
                    "Also show",
                    ToggleField("Social links", "links_show_socials", checked=(s["links_show_socials"] == "1")),
                    ToggleField("Support links", "links_show_support", checked=(s["links_show_support"] == "1")),
                    ToggleField("Your three newest posts", "links_show_posts",
                                checked=(s["links_show_posts"] == "1")),
                ),
                key="profile-linkspage"
            ),
            cls=f"flex flex-col gap-3 {SECTION_GAP}"
        ),
        SaveBar(),
        hx_post="/admin/settings/profile", hx_target="#save-status", hx_swap="outerHTML show:none focus-scroll:false",
        data_declare_fields=True
    )


def EditorTab(s):
    pinned = set(editor_config.pinned_from_setting(s["editor_toolbar"]))
    order = editor_config.pinned_from_setting(s["editor_toolbar"])
    return EditorForm(s, pinned, order)


# when Settings > Editor's button lists are used - shown for either
PICKS_USED = "editor_toolbar_rows=one;editor_phone_bar=buttons"


def EditorForm(s, pinned, order):
    from soloblog.routes.editor import TemplatesList
    style = editor_config.toolbar_style(s["editor_toolbar_rows"])
    phone = editor_config.phone_bar(s)
    # the buttons you choose are only used by these two
    picks = style == "one" or phone == "buttons"
    return Form(
        Div(
            SettingsPanel(
                "Writing",
                ToggleField(
                    "Keep unsaved writing", "editor_autosave", checked=(s["editor_autosave"] == "1"),
                    help="If the page closes before you save, you can get your writing back.", cls=FIELD_GAP
                ),
                ToggleField("Post settings beside the editor", "editor_settings_beside",
                            checked=(s["editor_settings_beside"] == "1"),
                            help="On a wide screen. Off, the Settings button opens it over the text.", cls=FIELD_GAP),
                ToggleField("Slash menu", "editor_slash", checked=(s["editor_slash"] == "1"),
                            help="Type / at the start of a line to insert headings, images and more.",
                            cls=FIELD_GAP),
                ToggleField("Check spelling", "editor_spellcheck", checked=(s["editor_spellcheck"] == "1"),
                            cls=FIELD_GAP),
                RadioGroupField("Writing width", "editor_width",
                                [("comfortable", "Comfortable - a column that's easy to read back"),
                                 ("wide", "Wide - the text fills the box")],
                                "wide" if s["editor_width"] == "wide" else "comfortable", cls=FIELD_GAP),
                ToggleField("Writing progress", "editor_progress", checked=(s["editor_progress"] == "1"),
                            help="Words written today, and a word goal for each post.", cls=FIELD_GAP),
                FormField("Default word goal",
                          Input(name="editor_goal_default", type="number", min="0", step="50",
                                value=s["editor_goal_default"], placeholder="None", inputmode="numeric",
                                cls="input input-sm w-40"),
                          help="Every post and page starts with it; each can have its own in Post settings. "
                               "Empty: none.", cls=FIELD_GAP),
                RadioGroupField("Markdown marks", "editor_marks",
                                [("dimmed", "Dimmed - so your text stands out"),
                                 ("full", "Full - the same colour as your text")],
                                "full" if s["editor_marks"] == "full" else "dimmed"),
                key="editor-autosave"
            ),
            SettingsPanel(
                "Focus",
                P("Just your writing, filling the screen.", cls=f"text-sm text-base-content/60 {FIELD_GAP}"),
                ToggleField("Typewriter scrolling", "editor_typewriter", checked=(s["editor_typewriter"] == "1"),
                            help="The line you're writing stays in the middle of the screen.", cls=FIELD_GAP),
                RadioGroupField("While you type", "editor_focus_toolbar",
                                [("all", "Hide everything but your text"),
                                 ("none", "Keep the toolbar")],
                                "none" if s["editor_focus_toolbar"] == "none" else "all",
                                help="Moving the mouse brings it back.", cls=FIELD_GAP),
                RadioGroupField("Fade", "editor_fade",
                                [("paragraph", "All but the paragraph you're in"),
                                 ("sentence", "All but the sentence you're in"),
                                 ("off", "Nothing")],
                                s["editor_fade"] if s["editor_fade"] in editor_config.FOCUS_FADES else "paragraph"),
                key="editor-focus"
            ),
            SettingsPanel(
                "Markdown",
                P("Footnotes, checklists, callouts, galleries and embedded videos always work. These two are "
                  "extra:", cls="text-sm text-base-content/60 mb-3"),
                ToggleField("Diagrams", "markdown_mermaid", checked=(s["markdown_mermaid"] == "1"),
                            help="Flowcharts and timelines, from ```mermaid blocks.", cls=FIELD_GAP),
                ToggleField("Math", "markdown_math", checked=(s["markdown_math"] == "1"),
                            help="Formulas written between $ signs."),
                key="editor-markdown"
            ),
            SettingsPanel(
                "Toolbar buttons",
                RadioGroupField("Toolbar", "editor_toolbar_rows",
                                [("one", "Icons - a row of the buttons you choose"),
                                 ("menus", "Menus - like a word processor"),
                                 ("none", "None - the slash menu and keyboard shortcuts")],
                                style, cls=FIELD_GAP),
                RadioGroupField("On a phone", "editor_phone_bar",
                                [("buttons", "Your buttons - the ones you choose below"),
                                 ("sections", "Sections - each opens a grid of buttons"),
                                 ("none", "None - type / for the slash menu")],
                                phone, help="The bar above a phone's keyboard.", cls=FIELD_GAP),
                P("The ones you leave off are still in the slash menu.", cls="text-sm text-base-content/60 mb-3"),
                Div(
                    Div(
                        *[Fieldset(
                            Legend(group_label, cls="fieldset-legend"),
                            Div(*[Label(
                                    Input(type="checkbox", name=f"tb_{key}", value="1", checked=(key in pinned),
                                          data_default="1" if default else "0", cls="checkbox checkbox-sm"),
                                    Span(NotStr(editor_config.icon_svg(key)), cls="flex text-base-content/70"),
                                    label, cls="label cursor-pointer gap-2 justify-start"
                                  ) for key, label, default in items],
                                cls="grid grid-cols-1 sm:grid-cols-2 gap-1"),
                            cls="fieldset p-0 mb-3"
                          ) for group_label, items in editor_config.TOOLBAR_GROUPS],
                        id="toolbar-options", data_autosave_off=True
                    ),
                    data_shown_for=PICKS_USED, hidden=not picks),
                key="editor-buttons"
            ),
            SettingsPanel(
                "Toolbar order",
                Div(
                    P("Drag to reorder, or use the arrows.", cls="text-sm text-base-content/60 mb-3"),
                    Div(
                        id="toolbar-order-list", cls="flex flex-col gap-3 mb-2",
                        data_labels=json.dumps(editor_config.LABELS),
                        data_icons=json.dumps({key: editor_config.icon_svg(key) for key in editor_config.ORDERABLE_KEYS}),
                        data_groups=json.dumps({key: editor_config.GROUP_OF[key] for key in editor_config.ORDERABLE_KEYS}),
                        data_sections=json.dumps(editor_config.GROUPS), data_always=editor_config.ALWAYS_ON,
                        data_default_order=",".join(editor_config.DEFAULT_ORDER),
                        data_moves=to_xml(SortMoves("__ID__"))
                    ),
                    # text, not hidden: the unsaved-changes warning and Discard
                    # both go by a field's saved value, which hidden ones don't keep
                    Input(type="text", hidden=True, name="editor_toolbar", id="editor-toolbar-input",
                          data_sort_order=True, value=",".join(order)),
                    Button(RESTORE_SVG, Span("Reset to default", cls="ml-1"), type="button", id="toolbar-reset-btn",
                           cls="btn btn-sm btn-ghost"),
                    data_shown_for=PICKS_USED, hidden=not picks),
                key="editor-order"
            ),
            # among the other panels, above Save - its Remove buttons post on
            # their own (htmx), so nothing here waits for Save
            SettingsPanel(
                "Templates",
                FormField("New posts start from", Combobox(
                    "new_post_start", [("", "Blank", None)]
                    + [(key, name, group) for key, name, group in post_templates.listed()],
                    post_templates.start_key(), "New posts start from", search="Type a template…"),
                    help="The starting point for every new post and page.", cls="mb-4"),
                Div(H3("Custom templates", cls="text-sm font-medium"),
                    P("Posts you've saved to start new ones from.", cls="text-sm text-base-content/70 mb-3")),
                TemplatesList(), key="editor-templates"),
            cls=f"flex flex-col gap-3 {SECTION_GAP}"
        ),
        SaveBar(),
        hx_post="/admin/settings/editor", hx_target="#save-status", hx_swap="outerHTML show:none focus-scroll:false",
        data_declare_fields=True
    )
