"""Settings presets: a starting style for a site in one go - how the blog
roll, the page and its side panels look, what each post shows around
it, and its fonts. Never content, and never the colour palette (chosen
on its own). A preset that's built around a page - a portfolio, docs, a
link-in-bio - uses one of the site's pages as the homepage, or makes one
from a template; the wiki's makes its front page the homepage, and a
first note if there are none.

Applying one keeps what it changed (preset_undo), so Undo puts every
setting back - and moves a page it made to the trash, if it's still as
it was made. Previewing one (the preview_preset cookie, app.PresetPreview)
shows the site in it without saving anything.
"""
import hashlib
import json
import re

from soloblog import sections, settings
from soloblog.posts import WIKI_HOME

# Every preset sets all of these, so one applied after another leaves
# nothing of the first behind: the blog roll, the page, the side panels,
# the fonts and what each post shows around it (pages.EXTRAS). What a
# preset doesn't choose is Soloblog's own default (settings.DEFAULTS) -
# each says only what makes it different.
_BASE = {"roll_style": "list", "cards_per_row": "2", "roll_shows": "cover,date,reading,summary,tags",
         "minimal_group": "none", "roll_placeholder": "1", "body_width": "standard", "section_space": "medium", "section_heading_align": "left",
         "font_body": "",
         "font_headings": "", "font_size": "medium", "header_align": "left", "header_style": "floating",
         "header_width": "wide", "banner_width": "full",
         "side_order": "side_tags,side_archive,side_author",
         "side_tags": "off", "side_tags_where": "roll", "side_archive": "off", "side_archive_where": "roll",
         "side_author": "off", "side_author_where": "posts", "toc_style": "right", "toc_numbers": "0",
         "heading_fold": "open", "cover_width": "screen", "gallery_style": "grid", "portfolio_style": "grid", "page_animations": "1", "side_plain": "1",
         "post_shows": "breadcrumbs,progress,byline,tags,listen,reactions,share,support,series,related,author,"
                       "newsletter,sides"}
# No "home_page": a style without a page of its own leaves your homepage as
# it is - trying a look shouldn't take away a landing page you chose. One
# that makes or uses a page (needs) still sets it, as does the wiki's.


def _look(**values) -> dict:
    return {**_BASE, **values}


# key: (name, what it's for, settings, (template, page title) when it needs a page).
# A stacked header - the title over its menu - never floats: two lines over
# the page cover too much of it, so it scrolls away or stays at the top.
PRESETS = {
    "personal": ("Personal blog", "A list of your posts with their images, your tags under them, and you beside every post.",
                 # the list with its picture on the right - more room per post
                 _look(side_tags="under", side_author="right",
                       font_headings="humanist",
                       post_shows="byline,tags,reactions,share,support,series,related,author,newsletter,sides"), None),
    "notebook": ("Writer's notebook", "Just the words: titles and dates by year, a narrow column, a book's "
                 "typeface, notes in the margin and nothing else.",
                 _look(roll_style="minimal", minimal_group="year", body_width="narrow", font_body="transitional",
                       font_headings="transitional", header_align="stacked", header_style="inline", toc_style="top",
                       # the banner as wide as the words, not a photo across the screen
                       cover_width="column", banner_width="column", page_animations="0",
                       post_shows="progress,byline,series,author,newsletter"), None),
    "magazine": ("Magazine", "The newest post up front and large, the rest in a grid, a masthead and bold "
                 "display headings.",
                 # a masthead: the title over its menu
                 _look(roll_style="magazine", font_headings="didone", header_align="stacked", header_style="fixed",
                       side_tags="right", cover_width="full"), None),
    "photo": ("Photo journal", "Big images, two to a row, covers edge to edge, galleries in rows - and few "
              "words around them.",
              _look(roll_style="cards", roll_shows="cover,date", roll_placeholder="0", font_headings="geometric",
                    toc_style="off", cover_width="full", gallery_style="justified", portfolio_style="rows",
                    post_shows="byline,tags,reactions,share,series,related"), None),
    "portfolio": ("Portfolio", "Your work first, images large - a portfolio as the homepage, each project "
                  "laid out like a magazine, the blog a click away.",
                  _look(roll_style="cards", font_headings="neo-grotesque", font_body="neo-grotesque",
                        gallery_style="masonry", portfolio_style="masonry",
                        post_shows="breadcrumbs,byline,tags,share,related"),
                  ("portfolio", "Work")),
    "journal": ("Journal", "Your posts along a line by date, each with its image - a diary, a travel log "
                "or a year of making things.",
                _look(roll_style="timeline", roll_shows="cover,date,summary", font_headings="slab",
                      body_width="narrow", toc_style="off", cover_width="column",
                      post_shows="byline,tags,reactions,share,series,related,newsletter,sides"), None),
    "freelancer": ("Freelancer", "What you offer as your homepage - your services with their prices and how "
                   "working with you goes - with your work and your blog a click away.",
                   _look(roll_style="cards", font_headings="neo-grotesque", toc_style="off", cover_width="full",
                         portfolio_style="grid", post_shows="byline,tags,share,related,author"),
                   ("services", "Work with me")),
    "business": ("Small business", "A shop, studio or café: your phone, address and opening hours as the "
                 "homepage, with your news beside them.",
                 _look(roll_style="cards", cards_per_row="3", roll_shows="cover,date,summary",
                       font_headings="humanist", font_body="humanist", toc_style="off", cover_width="full",
                       section_space="small", post_shows="byline,share,related"),
                 ("business", "Visit us")),
    "docs": ("Docs", "A knowledge base or a guide: a start page, numbered contents beside each page, sections "
             "that collapse and pages that print well.",
             _look(roll_style="minimal", toc_numbers="1", cover_width="column", heading_fold="folded",
                   post_shows="breadcrumbs,progress,print,series,related,sides"),
             ("docs", "Start here")),
    "wiki": ("Wiki", "Linked notes, with the wiki's front page as your homepage: what's new, what's read most "
             "and every note A to Z.",
             _look(roll_style="minimal", minimal_group="month", font_headings="old-style", toc_style="right",
                   cover_width="column", post_shows="breadcrumbs,byline,tags,related,sides",
                   home_page=WIKI_HOME),
             ("wiki", "Start here")),
    "launch": ("Launch", "A book, a course or a product, front and centre: a landing page as your homepage, "
               "built section by section, with the blog a click away.",
               _look(font_headings="geometric", header_align="stacked", header_style="fixed", cover_width="full",
                     section_space="large", section_heading_align="centre", toc_style="off", post_shows="byline,tags,share,related,newsletter"),
               ("landing", "Your launch")),
    "link-in-bio": ("Link in bio", "One page: your photo, a line about you and your links - for a profile "
                    "link.",
                    _look(body_width="narrow", font_headings="rounded", header_align="stacked", header_style="inline",
                          toc_style="off", post_shows="byline,share"),
                    ("profile", "Hello")),
}


# Default (Settings > Style, the first of the presets): every look setting
# - a preset's, and the rest of the Design pages' - back to its default,
# previewed and undone like a preset. What's yours stays: the banner's
# words and picture, your icons, your footer note and the homepage.
DEFAULT_KEY = "default"
YOURS = {"banner_enabled", "banner_heading", "banner_subheading", "banner_button_text", "banner_button_url", "banner_image_url",
         "header_icon_url", "favicon_url", "app_icon_url", "app_name", "footer_note", "home_page"}


def default_values() -> dict:
    from soloblog.routes.admin_settings import DESIGN_FIELDS
    # in the presets' own order (the blog roll, the page, the header...), then the rest
    keys = [k for k in _BASE if k not in YOURS] + sorted(set(DESIGN_FIELDS) - set(_BASE) - YOURS)
    return {k: settings.DEFAULTS[k] for k in keys if k in settings.DEFAULTS}


# Custom (Settings > Style, beside Default): one look of your own, saved
# from the site as it is - every setting Default would reset - to come
# back to after trying others. Saving again replaces it.
CUSTOM_KEY = "custom"


def _custom():
    try:
        saved = json.loads(settings.get("custom_preset") or "")
    except ValueError:
        return None
    return saved if isinstance(saved, dict) and isinstance(saved.get("values"), dict) else None


def save_custom():
    """The look as it is now, kept as Custom - only the look's own settings."""
    from soloblog.tz import utcnow
    values = {k: settings.get(k) for k in default_values()}
    settings.set_many({"custom_preset": json.dumps({"values": values, "saved": utcnow().date().isoformat()})})


def custom_saved_on() -> str:
    saved = _custom()
    return saved.get("saved", "") if saved else ""


def find(key):
    if key == CUSTOM_KEY:
        saved = _custom()
        if not saved:
            return None
        # only what's still a look setting: one saved by an older version
        # may hold a setting since gone
        values = {k: v for k, v in saved["values"].items() if k in default_values()}
        return ("Custom", "Your own look, as you saved it.", values, None)
    if key == DEFAULT_KEY:
        return ("Default", "Soloblog as it comes: a list of posts, a floating header and full screen covers, "
                "colours too.", default_values(), None)
    return PRESETS.get(key)


def baseline(s=None) -> dict:
    """What each setting is "by default" on this site: the starting style
    chosen last (Custom, your saved look), over Soloblog's own defaults -
    what the settings pages mark a setting as changed from, and Reset puts
    back. Picking a style marks nothing; what you change after it does."""
    s = s if s is not None else settings.get_all()
    base = dict(settings.DEFAULTS)
    chosen = find(s.get("preset")) if s.get("preset") else None
    if chosen:
        base.update({k: v for k, v in chosen[2].items() if k in base})
    return base


def uses_page(key) -> bool:
    """A preset with a page of yours as the homepage - one it makes, or one
    you choose. (The wiki's front page is a page of its own.)"""
    preset = find(key)
    return bool(preset and preset[3] and preset[2].get("home_page") != WIKI_HOME)


def preview_values(key) -> dict:
    """What the site looks like in a preset - its settings, not saved."""
    preset = find(key)
    if not preset:
        return {}
    # a preview doesn't make pages: one built around a page shows the
    # site's own page like the template's start page as the homepage, if there is one
    values = {k: v for k, v in preset[2].items() if k != "home_page"}
    if preset[2].get("home_page") == WIKI_HOME:
        values["home_page"] = WIKI_HOME
    elif preset[3]:
        from soloblog import posts
        page = next((r["slug"] for r in posts.list_posts() if posts.is_page(r) and _fits(r, preset[3][0])), None)
        if page:
            values["home_page"] = page
    elif "home_page" in preset[2]:
        values["home_page"] = ""
    return {**values, "_previewing": key}


def _kinds(body) -> list:
    """The kinds of the sections a text has, in order (Section: Pricing)."""
    return [sections.NAMES.get(name.strip().lower()) for name in re.findall(r"^Section:\s*(.+)$", body or "", re.M)]


def _start_text(template) -> str:
    """The words a style's page starts with: the template's, and for Docs a
    Contents section, so a guide's front page lists its parts without
    anyone linking them by hand (unless the template has one already)."""
    from soloblog import post_templates
    body = post_templates.get(template)["body"]
    if template == "docs" and "contents" not in _kinds(body):
        body = body.rstrip() + "\n\n" + sections.markdown("contents")
    return body


def _fits(row, template) -> bool:
    """A page like the one this style makes: it has the same first section
    as the template's start page (a Portfolio, Services...). A template
    with no section has no page that fits it."""
    from soloblog import posts
    # Docs' own Steps is part of its pages; what marks the start page is the Contents added to it
    first = "contents" if template == "docs" else next((k for k in _kinds(_start_text(template)) if k), None)
    return bool(first) and first in _kinds(posts.load_post_body(row["slug"]))


def apply(key, page: str = "") -> dict:
    """Applies a preset and keeps what Undo needs. page - for a preset that
    needs one: an existing page's slug, or "" to make one from its
    template. Returns {"made": slug of a page it made, or ""}."""
    from soloblog import posts, post_templates
    name, _, values, needs = find(key)
    values = dict(values)
    made = ""
    before = {k: settings.get(k) for k in [*values, *(["home_page"] if needs else [])]}
    # the style's look first: a page made from a template shows what the
    # style shows around a page, not what the site showed before it
    settings.set_many({k: v for k, v in values.items() if k != "home_page"})
    if needs and values.get("home_page") == WIKI_HOME:
        # the wiki's front page is the homepage - a first note, if there are none
        if not any(r["in_wiki"] for r in posts.list_posts(include_drafts=True)):
            template, title = needs
            made = posts.write(title=title, body=_start_text(template), published=True,
                               author=settings.get("author_name") or "",
                               **{**post_templates.settings_of(post_templates.get(template)), "in_wiki": True})
    elif needs:
        if page and posts.get_post(page) and posts.is_page(posts.get_post(page)):
            values["home_page"] = page
        else:
            template, title = needs
            made = posts.write(title=title, body=_start_text(template), published=True, pin_location="header",
                               author=settings.get("author_name") or "",
                               # a guide's start page is its first part, so its Contents lists the guide
                               **({"series_name": "Guide", "series_order": 1} if template == "docs" else {}),
                               **post_templates.settings_of(post_templates.get(template)))
            values["home_page"] = made
    settings.set_many({**values, "preset": key, "preset_undo": json.dumps({
        "preset": key, "before": before, "made": made,
        "made_hash": _hash(made) if made else ""})})
    return {"made": made}


def undo() -> bool:
    """Puts back what the last preset changed. A page it made goes to the
    trash only if it's still as it was made."""
    from soloblog import posts
    try:
        kept = json.loads(settings.get("preset_undo") or "")
    except ValueError:
        return False
    if not kept:
        return False
    settings.set_many({**kept["before"], "preset": "", "preset_undo": ""})
    made = kept.get("made")
    if made and posts.get_post(made) and _hash(made) == kept.get("made_hash"):
        posts.delete_post(made)
    return True


def _hash(slug) -> str:
    from soloblog import posts
    return hashlib.sha256((posts.load_post_body(slug) or "").encode()).hexdigest()
