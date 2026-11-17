"""Admin > Help: the user guide, FAQ, what's new and the hosting guide, from docs/ - the same files GitHub shows - and a search over them."""
import os
import re

from fasthtml.common import *

from soloblog import config
from soloblog import settings
from soloblog import posts
from soloblog import i18n
from soloblog.ui import HELP_GROUPS, PageNav
from soloblog.ui import (Layout, PageHeader, TableOfContents)

from soloblog.routes.admin_settings import _cached

ar = APIRouter()


def _help_text(tab: str) -> str:
    """A Help page's markdown, as the page shows it."""
    from soloblog.ui import HELP_SECTIONS
    name = HELP_PAGES[tab]
    try:
        with open(os.path.join(DOCS_DIR, name), encoding="utf-8") as f:
            text = f.read()
    except OSError:
        online = f"{config.PROJECT_URL}/blob/master/{os.path.normpath('docs/' + name)}"
        text = f"# {dict(HELP_SECTIONS)[tab]}\n\nThis page isn't in this install. Read it online: [{online}]({online})\n"
    if tab == "whatsnew":
        from soloblog import whatsnew
        text = whatsnew.for_help(text)
    # the guide's own first heading and contents line are the page title
    # and the sidebar here
    text = re.sub(r"\A# [^\n]*\n", "", text)
    text = re.sub(r"\n\*\*Contents:\*\*.*?\n\n", "\n\n", text, count=1, flags=re.S)
    if not i18n.british():
        text = i18n.spell(text)
    return text


_HEADING = re.compile(r"<h([234])\b[^>]*>.*?</h\1>", re.S)
# headings that say nothing on their own - their words count as the
# section's above, not as a result of their own
_GENERIC = {"more", "settings", "how it works", "advanced", "other", "notes", "overview", "example", "examples"}


def help_index() -> list:
    """Every section of every Help page - its heading and its words - for
    the search box over Help."""
    stamps = []
    for name in HELP_PAGES.values():
        try:
            stamps.append(os.path.getmtime(os.path.join(DOCS_DIR, name)))
        except OSError:
            stamps.append(0)
    return _cached(("help", tuple(stamps), i18n.british(), config.VERSION), _help_index)


def _help_index() -> list:
    from soloblog import pages
    from soloblog.render import render_post
    from soloblog.ui import HELP_SECTIONS
    entries = []
    for tab, label in HELP_SECTIONS:
        html, _ = render_post(_help_text(tab))
        heads = [m for m in _HEADING.finditer(html) if pages.text_of(m.group(0)).strip().lower() not in _GENERIC]
        # each result names the heading it's under: a ### its ##, a #### its ###
        parents = {"2": "", "3": ""}
        for i, m in enumerate(heads):
            title, level = pages.text_of(m.group(0)), m.group(1)
            if level in parents:
                parents[level] = title
                if level == "2":
                    parents["3"] = ""
            under = parents["2"] if level == "3" else (parents["3"] or parents["2"]) if level == "4" else ""
            # its own words, to the next heading - a ####'s aren't its ###'s too
            body = html[m.end():heads[i + 1].start() if i + 1 < len(heads) else len(html)]
            entries.append({"group": label, "title": title, "sub": under,
                            "text": " ".join(pages.text_of(body).split())[:4000],
                            "href": f"/admin/help?tab={tab}#{pages._id_of(m.group(0))}"})
    return entries


@ar.get("/admin/help/search-index")
def help_search_index(session):
    return JSONResponse(help_index(), headers={"Cache-Control": "private, no-store"})


# the admin's own pages for the top bar's search - Site health and its
# log weren't findable there, being neither a setting nor in Help:
# (title, what's there, where, other words people look for it by)
ADMIN_PAGES = [
    ("Posts and pages", "Write, edit, publish, pin and tag; drafts and scheduled posts.", "/admin/posts",
     "articles blog entries list"),
    ("Drafts", "Posts and pages not published yet.", "/admin/posts?status=draft", "unpublished"),
    ("Scheduled posts", "Posts set to go live later.", "/admin/posts?status=scheduled", "publish later queue"),
    ("Trash", "Posts and pages moved to the trash.", "/admin/posts?status=trash", "deleted restore bin"),
    ("Calendar", "Your posts by the day they were published.", "/admin/posts?status=calendar", "dates month"),
    ("Tags", "Rename and tidy your tags.", "/admin/posts?status=tags", "categories labels"),
    ("Media", "Images, audio, video and PDFs: upload, describe, crop.", "/admin/media",
     "pictures photos files uploads library"),
    ("Comments", "Comments waiting for you, approved ones and mentions.", "/admin/comments",
     "moderation pending replies spam webmentions"),
    ("Contact messages", "What visitors sent through your contact form.", "/admin/messages", "inbox mail form"),
    ("Members", "Your members, free and paid.", "/admin/members", "subscribers paid readers"),
    ("Newsletter", "Everyone who gets your posts by email.", "/admin/newsletter",
     "subscribers mailing list email list"),
    ("Stats", "Visits, popular posts and where readers come from.", "/admin/stats",
     "analytics views traffic visitors referrers"),
    ("Site health", "Backups, security, email and updates - what needs you.", "/admin/health",
     "status problems checks warnings"),
    ("Site health log", "Problems your site ran into, and a detailed log to download.", "/admin/health?tab=log",
     "logs errors problems debug download"),
    ("Site health info", "Version, disk space and how your site is set up.", "/admin/health?tab=info",
     "version disk storage system details"),
    ("Run setup again", "Your site's name, about you, look and style, one screen at a time.", "/admin/welcome",
     "welcome wizard setup start again onboarding"),
    ("Getting started", "What's left to do: email, a passkey, backups, your first post.",
     "/admin/settings?tab=name&panel=name-identity", "checklist next steps to do list onboarding"),
]


@ar.get("/admin/search-index")
def admin_search_index(session):
    """The admin's own pages, Settings and Help together, for the admin's
    top bar (ui.AdminSearch) - each group named for where it is."""
    from soloblog.routes.admin_settings import settings_index
    entries = [{"group": "Admin", "title": title, "sub": "", "text": text, "href": href, "words": words}
               for title, text, href, words in ADMIN_PAGES]
    entries += [{**e, "group": f"Settings: {e['group']}"} for e in settings_index()]
    entries += [{**e, "group": f"Help: {e['group']}"} for e in help_index()]
    return JSONResponse(entries, headers={"Cache-Control": "private, no-store"})


# docs/ sits beside the soloblog package, at the top of the repository
DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "docs")


# Help's sections: the files in docs/, the same ones GitHub shows - one
# source for both. The sidebar lists them (ui.HELP_SECTIONS).
HELP_PAGES = {"getting-started": "guide/getting-started.md", "writing": "guide/writing.md",
              "pages": "guide/pages.md", "design": "guide/design.md", "grow": "guide/grow.md",
              "run": "guide/run.md", "how-it-works": "guide/how-it-works.md",
              "put-together": "guide/put-together.md",
              "sections-templates": "guide/sections-templates.md", "reference": "guide/reference.md",
              "faq": "FAQ.md", "troubleshooting": "guide/troubleshooting.md", "whatsnew": "../CHANGELOG.md",
              "deployment": "DEPLOYMENT.md", "api": "API.md", "sponsor": "SPONSORS.md"}


_DOC_LINK = re.compile(r'href="(\.\./|docs/)?((?:guide/)?[A-Za-z_-]+\.md)(#[^"]*)?"')


_REPO_LINK = re.compile(r'href="(\.\./)*([^"#:/][^":]*)"')


def _help_links(html: str, tab: str) -> str:
    """Links between the docs stay in Help (DEPLOYMENT.md#put-https-in-front ->
    ?tab=deployment#put-https-in-front); other files in the repository (README,
    DEVELOPMENT.md, deploy/ configs) open on GitHub."""
    tabs = {os.path.basename(name): key for key, name in HELP_PAGES.items()}
    # a bare name is beside the page: CHANGELOG is at the top, the rest in docs/
    here = "" if tab == "whatsnew" else "docs/"
    # the guide's groups are a folder down: ../ is docs/ for them
    up = "docs/" if HELP_PAGES[tab].startswith("guide/") else ""
    here = "docs/guide/" if up else here

    def doc(m):
        key = tabs.get(os.path.basename(m.group(2)))
        if key:
            return f'href="/admin/help?tab={key}{m.group(3) or ""}"'
        folder = {"../": up, "docs/": "docs/"}.get(m.group(1), here)
        return f'href="{config.PROJECT_URL}/blob/master/{folder}{m.group(2)}{m.group(3) or ""}"'
    html = _DOC_LINK.sub(doc, html)
    # GitHub keeps "Sign-up / newsletter" as #sign-up--newsletter, Help
    # as #sign-up-newsletter: the docs link GitHub's way, and here a link
    # within Help gets Help's
    html = re.sub(r'href="((?:/admin/help\?tab=[a-z-]+)?#)([^"]+)"',
                  lambda m: f'href="{m.group(1)}{re.sub("-{2,}", "-", m.group(2))}"', html)
    return _REPO_LINK.sub(lambda m: f'href="{config.PROJECT_URL}/blob/master/{m.group(2)}"', html)


@ar.get("/admin/help")
def help_page(session, tab: str = "getting-started", q: str = ""):
    """Help: a section per file in docs/ - the guide, questions and
    answers, deploying, the API, sponsoring - each with its contents
    beside it."""
    from html import escape
    from soloblog import pages
    from soloblog.render import render_post, toc_markup
    from soloblog.ui import HELP_SECTIONS
    tab = tab if tab in HELP_PAGES else "getting-started"
    html, _ = render_post(_help_text(tab))
    # like a post: a copy-link button on each heading, and sections that
    # fold - always, whatever the blog's own posts do
    html = pages.fold_sections(pages.heading_links(html))
    html = _help_links(html, tab)
    # every ## and ### - Help wants its outline even when a page is short
    heads = re.findall(r'<h([23])\b[^>]*\bid="([^"]+)"[^>]*>(.*?)</h\1>', html, re.S)
    toc = toc_markup([(int(level), hid, escape(pages.text_of(inner))) for level, hid, inner in heads])
    return Layout(
        PageHeader(dict(HELP_SECTIONS)[tab]),
        Div(
            # the admin menu lists these; where it isn't beside the page, the
            # same grouped menu as Settings
            PageNav(HELP_GROUPS, tab, "/admin/help", "help-nav", "Help pages"),
            # the contents on the right - the admin sidebar is on the left
            Div(TableOfContents(toc, "right", settings.get("toc_fold")), pages._prose(html), cls="relative"),
            id="help-body"),
        settings=settings.get_all(), logged_in=True, pinned_tree=posts.list_pinned_tree(), admin_page=True
    )
