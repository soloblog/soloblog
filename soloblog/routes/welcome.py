from fasthtml.common import *

from soloblog import js
from soloblog import config
from soloblog import csp
from soloblog import posts
from soloblog import settings
from soloblog import translate
from soloblog import tz
from soloblog.ui import TimezoneCombobox, Combobox, EnglishSelect, GoLink
from soloblog import i18n
from soloblog.ui import (Layout, FormField, RadioGroupField, FIELD_GAP, MediaPickerDialog, MediaPickerButton,
                CHECK_SVG, EDIT_SVG, KEY_SVG, SEND_SVG, UPLOAD_SVG, GEAR_SVG, GLOBE_SVG, LINK_SVG, _nav_icon, _ICONS)

BOOK_SVG = _nav_icon(_ICONS["help"])
# heroicons outline "flag"
FLAG_ICON = _nav_icon("M3 3v1.5M3 21v-6m0 0 2.77-.693a9 9 0 0 1 6.208.682l.108.054a9 9 0 0 0 6.086.71l3.114-.732a48.524 "
                      "48.524 0 0 1-.005-10.499l-3.11.732a9 9 0 0 1-6.085-.711l-.108-.054a9 9 0 0 0-6.208-.682L3 4.5M3 15V4.5")

ar = APIRouter()

# The first-run wizard: straight after /setup creates the admin account,
# a few questions that make the blog feel like yours before the first
# post. It runs once; Settings > Name and homepage runs it again, and all
# of it lives in Settings. What comes after - email, a passkey, backups -
# is Getting started's list, each job done on its own settings page.
STEPS = [("site", "Your site"), ("you", "About you"), ("look", "Look"), ("style", "Style"), ("done", "Ready")]
INDEX = {key: i for i, (key, _) in enumerate(STEPS)}
ARROW_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" '
    'stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" '
    'd="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" /></svg>'
)

# a fresh install's timezone is "UTC" - the wizard suggests the browser's
# own instead, which is almost always the right answer
BROWSER_TZ_JS = js.read("browser_tz.js")


def StepsBar(current: int):
    """daisyUI steps - every step up to this one filled in."""
    # six don't fit a phone: there, where you are in words (Material's mobile stepper)
    return Div(
        Ul(*[Li(label, cls="step step-primary" if i <= current else "step") for i, (_, label) in enumerate(STEPS)],
           cls="steps w-full text-xs mb-6 max-sm:hidden"),
        P(f"Step {current + 1} of {len(STEPS)} · {STEPS[current][1]}",
          cls="text-xs font-medium text-base-content/60 mb-4 sm:hidden"),
    )


def WizardCard(index, title, intro, *fields):
    """One step: title and a line of explanation, the fields, then the
    action row - Back, and Continue as the primary action rightmost, the
    same order as every other form in the admin. Continue saves what the
    screen has, so a screen left as it is changes nothing."""
    title, intro = i18n.spell(title), i18n.spell(intro)
    prev_href = f"/admin/welcome?step={STEPS[index - 1][0]}" if index else None
    return Div(
        Div(
            StepsBar(index),
            Form(
                H1(title, cls="text-xl font-bold"),
                P(intro, cls="text-sm text-base-content/60 mb-4"),
                *fields,
                Div(
                    A("Back", href=prev_href, cls="btn btn-sm btn-ghost") if prev_href else None,
                    # where a field that isn't right says so, beside the buttons - in a
                    # box of its own: a message restyles the span, never the row
                    Div(Span(data_status_slot=True, role="status", cls="text-xs"), cls="flex-1 min-w-0 text-end"),
                    Button(ARROW_SVG, Span("Continue", cls="ml-1"), type="submit", cls="btn btn-primary btn-sm"),
                    cls="flex items-center justify-end gap-2 mt-6"
                ),
                action=f"/admin/welcome/{STEPS[index][0]}", method="post"
            ),
            cls="card-body p-6"
        ),
        cls="card card-border bg-base-100 max-w-xl mx-auto"
    )


def _onwards(key):
    """After a setup screen: the next one. The last one's Continue is what
    finishes the setup - a form sent, never a page only looked at."""
    following = STEPS[INDEX[key] + 1][0]
    if following == "done":
        settings.set_many({"setup_done": "1"})
    return RedirectResponse(f"/admin/welcome?step={following}", status_code=303)


# addresses a host gives every site - a site still on one hasn't got a
# domain of its own yet
HOST_ADDRESSES = (".fly.dev", ".onrender.com", ".railway.app", ".koyeb.app", ".herokuapp.com",
                  ".ondigitalocean.app", ".pikapod.net", ".trycloudflare.com", ".ts.net", ".nip.io", ".sslip.io",
                  ".localhost", ".local", ".test")


def has_own_domain() -> bool:
    import ipaddress
    from urllib.parse import urlparse
    host = (urlparse(config.BASE_URL).hostname or "").lower()
    if not host or "." not in host or host.endswith(HOST_ADDRESSES):
        return False
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        return True


def next_steps(s):
    """[(icon, title, what, where, done)] - the jobs that make a new site
    safe and ready to share, each once, each ticked off by what's actually
    set up, not by a click. Each leads to the very place it's done (a
    setting's own panel, opened and marked as a search result's is)."""
    from soloblog import passkeys, storage, totp
    from soloblog.db import get_db
    return [
        # done as Site health sees it: your address, and a way to send
        (SEND_SVG, "Set up email", "So password resets, sign-in alerts and new comments reach you.",
         # the panel that's still to do: the address first, then a way to send
         "/admin/settings?tab=email&panel=" + ("email-sending" if s.get("admin_email") else "email-admin"),
         s.get("email_provider") in ("smtp", "api") and bool(s.get("admin_email"))),
        (KEY_SVG, "Protect your login", "Add a passkey: sign in with your fingerprint, face or device PIN.",
         "/admin/settings?tab=security&panel=security-passkeys", totp.is_enabled() or passkeys.count() > 0),
        (UPLOAD_SVG, "Plan your backups", "Download one now, or connect cloud storage to have them made for you.",
         "/admin/settings?tab=backup&panel=backup-download", storage.enabled() or bool(s.get("last_backup_download"))),
        # a tagline is what search results show until there's a description
        (GLOBE_SVG, "Describe your site", "A sentence for search results and link previews.",
         "/admin/settings?tab=url&panel=url-search&setting=Description",
         bool((s.get("meta_description") or s.get("tagline") or "").strip())),
        (LINK_SVG, "Use a custom domain", "A domain like yourname.com instead of your host's.",
         "/admin/help?tab=deployment#use-a-custom-domain", has_own_domain()),
        # the welcome draft every site starts with doesn't count
        (EDIT_SVG, "Write your first post", "Markdown, with a live preview.", "/admin/new",
         get_db().execute("SELECT 1 FROM posts WHERE slug != ? LIMIT 1", (WELCOME_SLUG,)).fetchone() is not None),
    ]


def _started(s):
    """next_steps and how many are done - None once they all are, or it's
    been dismissed."""
    steps = next_steps(s)
    done = sum(1 for *_, finished in steps if finished)
    if done == len(steps) or s.get("getting_started_hidden") == "1":
        return None
    return steps, done


def GettingStartedEntry(s):
    """At the foot of the admin menu until the next steps are all done or
    it's dismissed: how far along - it opens them in a
    box in the middle of the screen (GettingStartedDialog), so they're
    never in a page's way, and never opened for you."""
    started = _started(s)
    if not started:
        return None
    steps, done = started
    # a flag, as the menu's other items have icons - a ring this small
    # read as something still loading
    return Li(Button(
        FLAG_ICON,
        Span("Getting started", cls="flex-1 text-left"),
        Span(f"{done} of {len(steps)}", cls="text-xs text-base-content/60"),
        type="button", data_open_dialog="getting-started"))


def StepRow(icon, title, what, where, finished=False):
    """One line of the list, the same in the box and on the setup's last
    screen: what it is and why, ticked and crossed out once it's done."""
    # the link is a block and the row inside it: as a row itself, a phone's
    # rule for a link alone in its line centred the icon against both lines
    return Li(A(Span(Span(CHECK_SVG if finished else icon,
                          cls=f"mt-1 shrink-0 {'text-success' if finished else 'text-base-content/60'}"),
                     Span(Span(title, cls="block font-medium" + (" line-through text-base-content/60" if finished else "")),
                          Span(what, cls="block text-xs text-base-content/60"), cls="min-w-0"),
                     cls="flex items-start gap-3"),
                href=where, cls="block rounded-box px-3 py-2.5 hover:bg-base-200"))


def Progress_(steps):
    done = sum(1 for *_, finished in steps if finished)
    return (P(f"{done} of {len(steps)} done", cls="text-xs text-base-content/60 mt-1"),
            Progress(value=str(done), max=str(len(steps)), aria_label="Getting started", cls="progress w-full h-1.5 mt-2"))


def SetupLine(s):
    """Under the list, while the setup's own screens were never finished:
    the way back to them."""
    if s.get("setup_done") == "1":
        return None
    return P(A("Finish setting up your site's name, about you and look", href="/admin/welcome",
               cls="link link-hover"), cls="text-xs text-base-content/60 mt-3")


def GettingStartedDialog(s, back="/admin/posts"):
    """The next steps, each a link to where it's done and ticked off by
    what's actually set up - Dismiss puts them away for good. back -
    where Dismiss returns to."""
    started = _started(s)
    if not started:
        return None
    steps, _ = started
    return Dialog(
        Div(
            H3("Getting started", id="getting-started-title", cls="font-semibold text-lg"),
            *Progress_(steps),
            Ul(*[StepRow(*step) for step in steps], cls="flex flex-col gap-1 mt-4 -mx-3"),
            SetupLine(s),
            # what each does, in its words: later keeps it in the menu;
            # Don't show again takes it out (Settings > Name and homepage >
            # Open Getting started brings it back)
            Div(Form(Input(type="hidden", name="back", value=back),
                     Button("Don't show again", type="submit", cls="btn btn-sm btn-ghost whitespace-nowrap"),
                     action="/admin/welcome/dismiss", method="post"),
                Form(Button("Remind me later", cls="btn btn-sm whitespace-nowrap"), method="dialog"),
                # on a narrow phone the two don't fit side by side
                cls="modal-action flex-wrap gap-y-2 mt-4"),
            cls="modal-box max-w-md"),
        Form(Button(cls="cursor-default", aria_label="Close"), method="dialog", cls="modal-backdrop"),
        id="getting-started", aria_labelledby="getting-started-title", cls="modal"
    )


def WhatsNew(s):
    """On Posts, the first time the admin's opened on a new version, until
    it's dismissed: that version's headlines from the changelog, and the
    way to the rest (Help > What's new)."""
    from soloblog import config, whatsnew
    if s.get("whatsnew_seen") == config.VERSION:
        return None
    body = whatsnew.section(whatsnew.read(), config.VERSION)
    titles = whatsnew.highlights(body)
    if not titles:
        return None
    shown = titles[:4]
    return Div(
        Div(
            Strong(f"What's new in {config.VERSION}", cls="text-sm"),
            P("This version asks you to do something after updating - see Upgrading.",
              cls="text-sm text-warning mt-1") if whatsnew.needs_upgrading(body) else None,
            Ul(*[Li(t) for t in shown], cls="list-disc pl-5 mt-1 text-sm text-base-content/80"),
            P(f"And {len(titles) - len(shown)} more.", cls="text-xs text-base-content/60 mt-1")
            if len(titles) > len(shown) else None,
            cls="flex-1 min-w-0"
        ),
        Div(
            Form(Button("Dismiss", type="submit", cls="btn btn-sm btn-ghost"),
                 action="/admin/whatsnew/dismiss", method="post"),
            GoLink("See what's new", "/admin/help?tab=whatsnew"),
            cls="flex items-center justify-end gap-2 shrink-0"
        ),
        cls="flex flex-col sm:flex-row sm:items-start gap-3 p-4 mb-4 rounded-box "
            "border-[length:var(--border)] border-base-300 bg-base-100"
    )


def DoneCard(s):
    """The setup's last screen: the site is ready, and the list of what's
    next (the same list as Getting started's box, while it's shown)."""
    steps = next_steps(s)
    left = _started(s) is not None
    return Div(
        Div(Div(
            StepsBar(INDEX["done"]),
            H1(f"{s['site_title']} is ready", cls="text-xl font-bold"),
            P("A few things to do before you share it. Each is checked off as you do it, and the list stays in "
              "Getting started, at the bottom of the admin menu.", cls="text-sm text-base-content/60") if left else None,
            *Progress_(steps),
            Ul(*[StepRow(*step) for step in steps], cls="flex flex-col gap-1 mt-4 -mx-3"),
            # not steps to tick off - set apart, so the count above
            # matches the list it's about
            P("Whenever you like", cls="text-xs font-semibold text-base-content/60 pt-5"),
            Ul(StepRow(GEAR_SVG, "Explore settings", "Comments, analytics, the footer and more.", "/admin/settings"),
               StepRow(BOOK_SVG, "Read the guide", "Everything Soloblog can do, and how.", "/admin/help"),
               cls="flex flex-col gap-1 mt-1 -mx-3"),
            Div(A(CHECK_SVG, Span("View your site", cls="ml-1"), href="/", cls="btn btn-sm"),
                cls="flex justify-end mt-4"),
            cls="card-body p-6"
        ), cls="card card-border bg-base-100 max-w-xl mx-auto")
    )


@ar.get("/admin/welcome")
def welcome(session, step: str = "site"):
    s = settings.get_all()
    first = s.get("setup_done") != "1"
    keys = [k for k, _ in STEPS]
    index = keys.index(step) if step in keys else 0
    extra = []
    if index == 0:
        body = WizardCard(
            0, *(("Welcome to Soloblog", "Let's start with the basics - what your site is called, and where you are.")
                 if first else ("Your site", "What your site is called, and where you are.")),
            FormField("Site title", Input(name="site_title", value=s["site_title"], required=True,
                                          cls="input input-sm w-full"), cls=FIELD_GAP),
            FormField("Tagline", Input(name="tagline", value=s["tagline"], placeholder="e.g. Notes on small software",
                                       cls="input input-sm w-full"),
                      help="Optional. A short line under your site title.", cls=FIELD_GAP),
            FormField("Language",
                      Combobox("site_language", [(code, name, None) for code, name in
                                                 sorted(translate.LANGUAGES.items(), key=lambda x: x[1])],
                               translate.site_language(s), "Language", search="Type a language…"),
                      help="What you'll write in. Dates and buttons on your site follow it.", cls=FIELD_GAP),
            Div(FormField("Spelling", EnglishSelect(s), cls=FIELD_GAP),
                data_shown_for="site_language=en", hidden=translate.site_language(s) != "en"),
            FormField("Timezone",
                      TimezoneCombobox(s["timezone"]),
                      help="Scheduled posts go live at this local time."),
        )
        extra.append(Script(BROWSER_TZ_JS, nonce=csp.NONCE))
    elif index == 1:
        body = WizardCard(
            1, "About you", "Shown as the byline on your posts, and in the author box under them.",
            FormField("Your name", Input(name="author_name", value=s["author_name"], cls="input input-sm w-full"),
                      cls=FIELD_GAP),
            FormField("Photo", Div(Input(name="author_avatar_url", id="author_avatar_url",
                                         value=s["author_avatar_url"], placeholder="/uploads/avatar.webp",
                                         cls="input input-sm flex-1 min-w-0 join-item"),
                                   MediaPickerButton("author_avatar_url"), cls="join w-full"),
                      help="Optional. Pick or upload one.", cls=FIELD_GAP),
            FormField("Short bio", Textarea(s["author_bio"], name="author_bio", rows="3",
                                            cls="textarea textarea-sm w-full"),
                      help="Optional. A sentence or two.", cls=FIELD_GAP),
        )
        extra.append(MediaPickerDialog(s))
    elif index == INDEX["look"]:
        from soloblog.routes.admin_settings import ThemePicker
        body = WizardCard(
            INDEX["look"], "Choose your look", "Your icon, and the colours your site is in. You can change them "
                                               "any time.",
            FormField("Icon or logo", Div(Input(name="header_icon_url", id="header_icon_url",
                                                value=s["header_icon_url"], placeholder="/uploads/logo.webp",
                                                cls="input input-sm flex-1 min-w-0 join-item"),
                                          MediaPickerButton("header_icon_url"), cls="join w-full"),
                      help="Beside your site's name, and in browser tabs. Empty: your site's first letter.",
                      cls=FIELD_GAP),
            *ThemePicker(s, modes=False),
        )
        extra += [MediaPickerDialog(s), Script("localStorage.removeItem('admin-preview');", nonce=csp.NONCE),
                  Script(src="/static/vendor/theme-change-2.5.0.js", nonce=csp.NONCE)]
    elif index == INDEX["style"]:
        from soloblog import presets
        from soloblog.routes.admin_settings import preset_changes
        body = WizardCard(
            INDEX["style"], "Choose a starting style", "How your posts are listed, the header, what each post "
                                                       "shows and the fonts, in one go. Your colours stay as you "
                                                       "picked them.",
            RadioGroupField("Style", "preset", [("", "Keep it as it is")] + [
                (key, f"{name} - {about}") for key, (name, about, _, _) in presets.PRESETS.items()],
                # never the one it has: Continue would apply it again, over
                # everything changed since
                "",
                help="Portfolio, Docs, Launch and Link in bio make a page for your homepage, to fill in; Wiki makes "
                     "a first note."),
            # what each would change, for anyone who wants to know before choosing
            Details(Summary("What each one changes", cls="cursor-pointer w-fit link link-hover text-sm py-2"),
                    *[Div(P(name, cls="font-medium text-xs mt-3"),
                          Ul(*[Li(line) for line in lines] or [Li("Nothing - your site already looks like this")],
                             cls="list-disc pl-4 text-xs text-base-content/70 flex flex-col gap-0.5"))
                      for key, (name, _, values, _) in presets.PRESETS.items()
                      for lines in [preset_changes(values, s)]],
                    cls="mt-3"),
        )
    else:
        body = DoneCard(s)
    return Layout(body, *extra, settings=s, logged_in=True, pinned_tree=posts.list_pinned_tree(), admin_page=True)


@ar.post("/admin/welcome/dismiss")
def dismiss_getting_started(session, back: str = "/admin/posts"):
    settings.set_many({"getting_started_hidden": "1"})
    # back where it was dismissed - only ever one of our own admin pages
    return RedirectResponse(back if back.startswith("/admin/") and "//" not in back else "/admin/posts",
                            status_code=303)


@ar.post("/admin/welcome/show")
def show_getting_started(session, back: str = "/admin/settings?tab=name"):
    """Getting started back in the admin menu, after it was dismissed."""
    settings.set_many({"getting_started_hidden": "0"})
    return RedirectResponse(back if back.startswith("/admin/") and "//" not in back else "/admin/posts",
                            status_code=303)


def GettingStartedLink(s):
    """Settings > Name and homepage's way to Getting started, while it has
    steps left: it opens the box (bringing it back first if it was
    dismissed - its form sits outside the settings' own, as one form can't
    be inside another: ShowGettingStartedForm)."""
    label = "Open Getting started"
    if all(finished for *_, finished in next_steps(s)):
        return None
    if s.get("getting_started_hidden") == "1":
        return Button(label, type="submit", form="show-getting-started", cls="btn btn-sm")
    return Button(label, type="button", data_open_dialog="getting-started", cls="btn btn-sm")


def SetupAgain(s):
    """Settings > Name and homepage: the setup's screens again, whenever
    they're wanted, and Getting started beside it while it has steps left."""
    return Div(
        P("Go through your site's name, about you, look and style again, one screen at a time.",
          cls="text-xs text-base-content/60 mb-2"),
        Div(A("Run setup again", href="/admin/welcome", cls="btn btn-sm"), GettingStartedLink(s),
            cls="flex flex-wrap gap-2"),
        cls="mt-5")


def ShowGettingStartedForm(s):
    """What GettingStartedLink sends once Getting started was dismissed -
    placed after the settings' form; back with its box open."""
    if s.get("getting_started_hidden") != "1":
        return None
    return Form(Input(type="hidden", name="back", value="/admin/settings?tab=name#getting-started"),
                id="show-getting-started", action="/admin/welcome/show", method="post", hidden=True)


@ar.post("/admin/whatsnew/dismiss")
def dismiss_whatsnew(session):
    from soloblog import config
    settings.set_many({"whatsnew_seen": config.VERSION})
    return RedirectResponse("/admin/posts", status_code=303)


@ar.post("/admin/welcome/site")
def save_site(session, site_title: str = "", tagline: str = "", timezone: str = "UTC", site_language: str = "en",
              english_spelling: str = "us"):
    settings.set_many({"site_title": site_title.strip() or "My Blog", "tagline": tagline.strip(),
                       "timezone": timezone if timezone in tz.zone_names() else "UTC",
                       "site_language": site_language if site_language in translate.LANGUAGES else "en",
                       "english_spelling": english_spelling if english_spelling in i18n.ENGLISH else "us"})
    return _onwards("site")


@ar.post("/admin/welcome/you")
def save_you(session, author_name: str = "", author_avatar_url: str = "", author_bio: str = ""):
    settings.set_many({"author_name": author_name.strip(), "author_avatar_url": author_avatar_url.strip(),
                       "author_bio": author_bio.strip()})
    return _onwards("you")


@ar.post("/admin/welcome/look")
def save_look(session, theme: str = "", theme_dark: str = "dark", theme_mode: str = "auto",
              header_icon_url: str = ""):
    from soloblog import images
    from soloblog.themes import THEME_MODES, all_choices, dark_choices
    values = {"theme_dark": theme_dark if theme_dark in dark_choices() else "dark",
              "theme_mode": theme_mode if theme_mode in dict(THEME_MODES) else "auto"}
    if theme in all_choices():
        values["theme"] = theme
    icon = header_icon_url.strip()
    if not icon or icon.startswith("/uploads/") and images.plain_name(icon.rsplit("/", 1)[-1]):
        values["header_icon_url"] = icon
    settings.set_many(values)
    return _onwards("look")


@ar.post("/admin/welcome/style")
def save_style(session, preset: str = ""):
    from soloblog import presets
    if presets.find(preset):
        presets.apply(preset)
    return _onwards("style")


# The draft a new site starts with (do_setup): where things are, and how
# to be rid of it. A draft, so only the owner ever sees it - nothing on a
# new site for its readers but what its owner writes.
WELCOME_SLUG = "welcome-to-your-new-site"
WELCOME_TITLE = "Welcome to your new site"
WELCOME_POST = f"""This post is a draft, so only you can see it. When you've read it, move it to the trash from
**Posts and pages**.

## What to do first

**Getting started**, at the bottom of the admin menu, lists the jobs that make your site safe and ready to
share: email, a passkey, backups, a description for search results, your own domain and your first post. Each
one is ticked off as you do it.

## Where things are

- **New post** is at the top of the admin menu. Type **/** on an empty line for headings, images, galleries and
  more.
- **Settings** has everything about your site, from its name and colours to comments, the newsletter and
  members.
- **Site health** checks your site every day and tells you if something needs fixing.
- **Help** is the whole guide, arranged by what you want to do. [Writing posts](/admin/help?tab=writing) is a
  good place to start.

## About Soloblog

Soloblog is free and open source, made by ZRPlus Studio. If it's useful to you, you can
[support it](/admin/help?tab=sponsor). Questions and ideas are welcome in
[the discussions]({config.PROJECT_URL}/discussions).

Happy writing.
"""


def make_welcome_post():
    """The welcome draft, once - on a brand new site."""
    from soloblog import posts
    posts.save_post(WELCOME_SLUG, WELCOME_TITLE, settings.get("author_name") or "", WELCOME_POST, "", "",
                    published=False, pinned=False)
