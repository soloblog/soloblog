from soloblog.actions import on, on_attrs, EL
import json
import re
from datetime import datetime
from soloblog.tz import utcnow
from html import escape, unescape

from fasthtml.common import (A, Button, Details, Div, Figcaption, Figure, H2, H3, Img, Input, Label, Li, Nav, NotStr, Ol, P, Script,
                             Section, Span, Summary, Table, Tbody, Td, Tr, Ul, to_xml)

from soloblog import config
from soloblog import i18n
from soloblog import images
# not `sections`: this module has a function of that name
from soloblog import sections as section_registry

# The page around the writing, and what draws a section. A post is always
# plain markdown; render() takes its already-rendered, already-sanitized
# html and returns what the post page should show instead of its plain body:
# its sections drawn in place (a ## with a "Section:" line), heading
# links and folds, the wiki note, the reminder, Link to and slides.
# Every page is drawn the same way; a template only fills in a page's
# sections and settings.

# A small picture of each blog roll look and each starting style - drawn in the
# palette's own colours, so it suits every theme. On a 64 x 40 grid,
# one shape a line: h heading, t text line (x y width), p picture,
# b box, o outline, a accent (x y width height), c circle (x y r).
THUMBS = {
    # how the blog roll looks (Settings > Blog layout)
    "roll-list": "h 6 4 30|t 6 8 36|p 46 3 12 8|h 6 15 30|t 6 19 36|p 46 14 12 8|h 6 26 30|t 6 30 36|p 46 25 12 8",
    "roll-cards": "p 4 4 17 10|h 4 16 14|t 4 20 16|p 23.5 4 17 10|h 23.5 16 14|t 23.5 20 16|p 43 4 17 10|h 43 16 14|"
                  "t 43 20 16|p 4 26 17 10|p 23.5 26 17 10|p 43 26 17 10",
    "roll-magazine": "p 4 3 56 15|h 4 20 36|t 4 24 44|p 4 29 17 8|p 23.5 29 17 8|p 43 29 17 8",
    "roll-minimal": "a 6 5 10 1.6|t 20 5 32|a 6 10 10 1.6|t 20 10 28|a 6 15 10 1.6|t 20 15 34|a 6 20 10 1.6|"
                    "t 20 20 26|a 6 25 10 1.6|t 20 25 30|a 6 30 10 1.6|t 20 30 22",
    # what each preset (presets.PRESETS) looks like
    # your own look: a mix of the others
    "preset-portfolio": "h 4 3 26|p 4 8 18 13|t 4 23 12|p 23 8 18 13|t 23 23 12|p 42 8 18 13|t 42 23 12|p 4 28 18 10|"
                "p 23 28 18 10|p 42 28 18 10",
    "preset-freelancer": "h 8 3 24|o 4 9 17 18|t 7 12 10|h 7 16 8|a 7 22 11 3|o 23.5 9 17 18|t 26.5 12 10|h 26.5 16 8|"
                "a 26.5 22 11 3|o 43 9 17 18|t 46 12 10|h 46 16 8|a 46 22 11 3|c 9 33 1.6|t 13 32.5 12|c 33 33 1.6|"
                "t 37 32.5 12",
    "preset-custom": "o 4 2 56 5|p 4 10 26 13|h 34 11 22|t 34 15 24|t 34 18 18|h 4 28 26|t 4 32 30|"
                     "p 34 27 26 9",
    # Soloblog as it comes: a floating header, a list with pictures on the right
    "preset-default": "o 4 2 56 5|h 6 11 28|t 6 15 34|p 44 10 14 8|h 6 22 28|t 6 26 34|p 44 21 14 8|h 6 33 28|"
                      "p 44 32 14 6",
    # a list, each post's picture on its right, and you beside it
    "preset-personal": "h 4 5 24|t 4 9 28|p 33 4 9 7|h 4 16 24|t 4 20 28|p 33 15 9 7|h 4 27 24|t 4 31 28|"
                       "p 33 26 9 7|o 46 4 14 18|c 53 9 3|t 48 15 10|t 48 18 8",
    "preset-notebook": "h 18 4 14|a 18 9 6 1.4|t 26 9 20|a 18 12 6 1.4|t 26 12 16|h 18 18 14|a 18 23 6 1.4|"
                       "t 26 23 18|a 18 26 6 1.4|t 26 26 14|t 4 9 10|t 4 12 8",
    "preset-magazine": "h 18 3 28|p 4 8 56 13|h 4 23 34|p 4 29 17 8|p 23.5 29 17 8|p 43 29 17 8",
    "preset-photo": "p 0 3 64 14|p 2 20 29 9|p 33 20 29 9|p 2 31 29 7|p 33 31 29 7",
    # posts along a line, each with its picture
    "preset-journal": "a 31.6 3 0.8 34|c 32 8 1.6|p 8 5 14 7|t 36 7.5 18|c 32 20 1.6|p 42 17 14 7|t 10 19.5 18|"
                      "c 32 32 1.6|p 8 29 14 7|t 36 31.5 18",
    "preset-docs": "t 4 6 12|t 4 10 10|a 4 14 12 1.4|t 4 18 9|t 4 22 11|h 22 5 30|t 22 11 36|t 22 14 34|t 22 17 36|"
                   "t 22 22 30|b 22 30 16 5|b 40 30 16 5",
    "preset-wiki": "h 8 3 26|t 8 9 20|a 29 9 12 1.4|t 42 9 12|t 8 12 46|t 8 15 18|a 27 15 14 1.4|t 42 15 10|"
                   "o 8 22 48 14|t 11 25 18|t 11 28 14|t 35 25 16",
    "preset-launch": "h 14 4 36|t 18 9 28|a 26 12 12 4|p 6 19 24 9|t 34 21 22|t 34 24 18|p 34 30 24 9|t 6 32 22|"
                     "t 6 35 18",
    "preset-link-in-bio": "c 32 10 6|h 18 19 28|t 14 24 36|b 14 29 11 5|b 27 29 11 5|b 40 29 11 5",
    "preset-business": "h 8 3 30|b 8 8 14 5|b 24 8 14 5|b 40 8 14 5|t 8 17 14|t 30 17 12|t 8 20 14|t 30 20 12|"
                       "t 8 23 14|t 30 23 12|p 8 28 48 10",
}

# a tint of the text colour reads on every palette's background, where
# base-300 all but vanishes on some
_THUMB_SHAPE = {"h": ("fill-base-content", "0.75"), "t": ("fill-base-content", "0.3"), "p": ("fill-primary", "0.35"),
                "b": ("fill-base-content", "0.14"), "a": ("fill-primary", "0.85"), "c": ("fill-base-content", "0.22")}


def thumb(name):
    """A small picture (THUMBS), as an <svg>."""
    from fasthtml.common import NotStr
    shapes = []
    for part in THUMBS.get(name, THUMBS["preset-default"]).split("|"):
        kind, *n = part.split()
        if kind == "c":
            cls, op = _THUMB_SHAPE["c"]
            shapes.append(f'<circle cx="{n[0]}" cy="{n[1]}" r="{n[2]}" class="{cls}" opacity="{op}"/>')
        elif kind == "o":
            shapes.append(f'<rect x="{n[0]}" y="{n[1]}" width="{n[2]}" height="{n[3]}" rx="1.5" fill="none" '
                          'class="stroke-base-content" stroke-opacity="0.25" stroke-width="0.6"/>')
        else:
            x, y, w, *h = n
            height = h[0] if h else ("2.4" if kind == "h" else "1.4")
            cls, op = _THUMB_SHAPE[kind]
            shapes.append(f'<rect x="{x}" y="{y}" width="{w}" height="{height}" rx="{"1.5" if h else "0.7"}" '
                          f'class="{cls}" opacity="{op}"/>')
    return NotStr('<svg viewBox="0 0 64 40" aria-hidden="true" class="w-full h-auto rounded-field bg-base-100 '
                  'border border-base-300">' + "".join(shapes) + "</svg>")


# What a post shows around its text, each switched on or off per post
# (Post settings > Page > Show). A post shows them all; a page in the menu or
# footer just its title and content, like pages on WordPress or Ghost.
# Comments keep their own switch, "Allow comments".
EXTRAS = {"breadcrumbs": "Breadcrumbs", "progress": "Reading progress bar", "byline": "Author and date",
          "tags": "Tags", "listen": "Listen button", "reactions": "Likes", "share": "Share buttons",
          "print": "Print or save as PDF", "support": "Support links", "series": "Series links",
          "related": "Related posts", "author": "About the author", "newsletter": "Newsletter sign-up",
          "sides": "Side panels"}
# what a page shows of them, unless it says otherwise - when the posts do
PAGE_EXTRAS = {"breadcrumbs", "progress", "series", "sides"}
# off until it's chosen in Each post shows
OFF_BY_DEFAULT = {"print"}


def default_extras(page: bool) -> set:
    """What a post shows unless it says otherwise: Settings > Appearance >
    Each post shows (post_shows). A page, just its title and content -
    and of PAGE_EXTRAS, those the posts show."""
    from soloblog import settings
    chosen = settings.get("post_shows") or ""
    if chosen:
        shown = set() if chosen == "none" else set(chosen.split(",")) & set(EXTRAS)
    else:
        shown = {k for k in EXTRAS if k not in OFF_BY_DEFAULT}
    return shown & PAGE_EXTRAS if page else shown


def show_on_posts(key, on: bool):
    """Ticks or unticks one of Each post shows - for the switches that
    also sit with their own settings (the newsletter's, Support's)."""
    from soloblog import settings
    shown = default_extras(False)
    shown = shown | {key} if on else shown - {key}
    settings.set_many({"post_shows": ",".join(k for k in EXTRAS if k in shown) or "none"})


def shown_extras(row) -> set:
    """The EXTRAS this post shows: its own choice (row["extras"], "none"
    for none), or the default for a post or a page."""
    from soloblog import posts
    return shown_from(row["extras"] if "extras" in row.keys() else "", posts.is_page(row))


def shown_from(value, page: bool) -> set:
    """The EXTRAS a stored choice shows ("" follows the default for a post
    or a page) - a post's, or a template's before there's a post."""
    if not value:
        return default_extras(page)
    return set() if value == "none" else set(value.split(",")) & set(EXTRAS)


def extras_value(shown, page: bool) -> str:
    """How a choice of EXTRAS is stored: "" when it's the default for a
    post or a page (so it follows it), "none", or the list."""
    shown = [k for k in EXTRAS if k in shown]
    if set(shown) == default_extras(page):
        return ""
    return ",".join(shown) or "none"


def clean_extras(value) -> str:
    value = str(value or "").strip().lower()
    if value == "none":
        return value
    return ",".join(k for k in EXTRAS if k in value.split(","))


def is_wide(row) -> bool:
    """A page's Page width: Wide (posts.PAGE_WIDTHS)."""
    return _own(row, "page_width") == "wide"


# The table of contents and folding sections. Each post can choose
# (Post settings > Page, "toc:" and "fold:" in the front matter);
# "" there means the site's own choice (Settings > Appearance).
# a place, said the same way everywhere (ui.SIDE_PLACES too): where it
# goes, then Off
TOC_STYLES = {"top": "At the top", "side": "On the left", "right": "On the right", "off": "Off"}
# whether a ## in the contents folds its ###s away (site-wide)
TOC_FOLDS = {"auto": "Follow the reader", "open": "Collapsible, open", "off": "Always open"}
FOLD_STYLES = {"off": "Off", "open": "On, open", "folded": "On, collapsed"}
# a post's cover and the homepage banner (ui.Breakout)
COVER_WIDTHS = {"column": "Column - as wide as the text", "wide": "Wide - out to the side panels",
                "full": "Edge to edge"}
# a post's cover - those, or the whole screen with the title over it (the
# homepage banner keeps COVER_WIDTHS: it has its own words over it)
COVER_STYLES = {**COVER_WIDTHS, "screen": "Full screen - the whole screen, the title over it"}


def _own(row, key) -> str:
    return (row[key] if key in row.keys() else "") or ""


# Settings > Posts > Table of contents > Shows on
TOC_WHERE = {"posts": "Posts", "pages": "Pages"}


def counts_as_page(row, s) -> bool:
    """A page in the menu or the footer, or the post that's the homepage:
    what the Shows on of the contents and side panels call a page."""
    from soloblog import posts
    return posts.is_page(row) or bool(row["slug"] and row["slug"] == s.get("home_page"))


def toc_style(row, s) -> str:
    """Where this post's contents go: "top", "side" (left), "right" or "off".
    Beside a wide page (Slides) there's only room on a very wide screen -
    placeSidePanels (app.py) measures. The site's choice is only for posts
    or pages it's ticked to show on; a post's own choice always counts."""
    if _own(row, "toc_style"):
        return _own(row, "toc_style")
    kind = "pages" if counts_as_page(row, s) else "posts"
    shows = set((s.get("toc_style_where") or "posts,pages").split(","))
    return (s.get("toc_style") or "top") if kind in shows else "off"


def cover_width(row, s) -> str:
    width = _own(row, "cover_width") or s.get("cover_width") or "column"
    return width if width in COVER_STYLES else "column"


def section_space(row, s) -> str:
    space = _own(row, "section_space") or s.get("section_space") or "medium"
    return space if space in SPACINGS else "medium"


def section_motion(row, s) -> str:
    """How this page's sections come into view: its own, else the site's."""
    motion = _own(row, "section_motion") or s.get("section_motion") or "fade"
    return motion if motion in SECTION_MOTIONS else "fade"


def fold_style(row, s) -> str:
    style = _own(row, "heading_fold") or s.get("heading_fold") or "off"
    return style if style in FOLD_STYLES else "off"


_TAG_ANY = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)\b[^>]*?(/?)>")
_VOID = {"area", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


def _top_headings(html):
    """[level, start, end] of each <h2>/<h3> not inside anything else -
    one in a blockquote or a callout stays where it is."""
    depth, found = 0, []
    for m in _TAG_ANY.finditer(html):
        closing, name = m.group(1), m.group(2).lower()
        if closing:
            depth -= 1
            if depth == 0 and name in ("h2", "h3", "div") and found and found[-1][2] is None:
                found[-1][2] = m.end()
        elif name not in _VOID and not m.group(3):
            if depth == 0 and name in ("h2", "h3"):
                found.append([int(name[1]), m.start(), None])
            elif depth == 0 and name == "div" and "data-fold-break" in m.group(0):
                # a section: it never folds, and it starts a new part of
                # the page - not folded into the writing before it
                found.append([2, m.start(), None])
            depth += 1
    return [h for h in found if h[2]]


def _fold(html, heads, level, open_):
    mine = [h for h in heads if h[0] == level]
    if not mine:
        return _fold(html, heads, 3, open_) if level == 2 else html
    first = mine[0][1]
    parts = [_fold(html[:first], [h for h in heads if h[2] <= first], 3, open_) if level == 2 else html[:first]]
    for i, (_, start, end) in enumerate(mine):
        stop = mine[i + 1][1] if i + 1 < len(mine) else len(html)
        if html.startswith("<div", start):
            # a section (data-fold-break) and what follows it, as written
            parts.append(html[start:stop])
            continue
        inner = html[end:stop]
        if level == 2:
            inner = _fold(inner, [[lv, s - end, e - end] for lv, s, e in heads if lv == 3 and end <= s < stop], 3, open_)
        # the heading's own margins move to the section, so the arrow
        # lines up with it; what follows starts close, as after a heading
        heading = html[start:end]
        if "class=" not in heading.split(">", 1)[0]:
            heading = re.sub(r"^<h([23])", r'<h\1 class=""', heading)
        gap = "mt-8" if level == 2 else "mt-5"
        if level == 2 and HEADING_GAP in heading:
            # a section's heading: the gap above it moves to the section too
            # (with its own Space:, which sets the gap)
            own = re.search(r'class="([^"]*)"', heading).group(1)
            moved = [c for c in own.split() if c.startswith(("[--section-gap:", "sm:[--section-gap:"))]
            kept_cls = [c for c in own.split() if c not in moved and c != HEADING_GAP]
            heading = heading.replace(f'class="{own}"', f'class="{" ".join(kept_cls)}"', 1)
            gap = " ".join([*moved, "mt-(--section-gap)"])
        heading = heading.replace('class="', 'class="my-0! ', 1)
        # the copy-link button can't be inside the heading that folds the
        # section (a button in a button); it sits at the row's end, beside
        # the arrow, in a box the height of the heading's first line - 2em
        # of the text in every text size
        copy = _COPY_BUTTON.search(heading)
        if copy:
            heading = heading.replace(copy.group(0), "")
            button = copy.group(0).replace(_COPY_HIDDEN, _COPY_SHOWN)
            button = button.replace("<button ", f'<button data-target="{_id_of(heading)}" ', 1)
            copy = f'<span class="absolute top-0 end-8 h-[2em] flex items-center">{button}</span>'
        parts.append(f'<div class="relative {gap}">'
                     f'<details class="group/fold collapse collapse-arrow rounded-none"{" open" if open_ else ""}>'
                     f'<summary class="collapse-title ps-0 {"pe-16" if copy else "pe-8"} py-0 min-h-0">{heading}</summary>'
                     f'<div class="collapse-content px-0 pb-0 group-open/fold:pt-3 [&>:first-child]:mt-0">{inner}</div>'
                     f'</details>{copy or ""}</div>')
    return "".join(parts)


_LINK_ICON = ('<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" '
              'stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" '
              'd="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 '
              '1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244" /></svg>')
# beside a heading's words it shows on hover; at the end of a folding
# section's row (_fold), always - quietly, until pointed at
_COPY_HIDDEN = ("align-middle ms-1 opacity-0 group-hover/h:opacity-60 focus-visible:opacity-100 "
                "[@media(hover:none)]:opacity-40")
_COPY_SHOWN = "opacity-50 hover:opacity-100 focus-visible:opacity-100"
_COPY_BUTTON = re.compile(r'<button type="button" aria-label="[^"]*" data-tip="[^"]*" class="[^"]*"[^>]*copyHeadingLink.*?</button>', re.S)
_HEADING = re.compile(r'<h([23])((?:\s[^>]*)?\sid="([^"]+)"[^>]*)>(.*?)</h\1>', re.S)


# a heading that opens the page over its picture (a Hero, Style: Cover):
# the first thing anyone sees, centred - a link to the top of the page
# helps no one, and on a phone, where it always shows, it sat beside the
# title and pulled it off centre
_NO_COPY = "data-no-copy-link"


def heading_links(html: str) -> str:
    """A small button after each ## and ### that copies the address of
    that section - shown on hover, always on a touch screen."""
    label = escape(i18n.t("Copy link"))

    def add(m):
        level, attrs, _, inner = m.groups()
        if _NO_COPY in attrs:
            return m.group(0)
        attrs = attrs.replace('class="', 'class="group/h ', 1) if "class=" in attrs else ' class="group/h"' + attrs
        return (f'<h{level}{attrs}>{inner}<button type="button" aria-label="{label}" data-tip="{label}" '
                f'class="btn btn-ghost btn-xs btn-square tooltip {_COPY_HIDDEN}" '
                f'{on_attrs("click", "copyHeadingLink", EL)}>{_LINK_ICON}</button></h{level}>')
    return _HEADING.sub(add, html)


def fold_sections(html: str, open_: bool = True) -> str:
    """Each ## (and each ### inside it) becomes a section the reader can
    fold by clicking its heading. Footnotes stay out of the last one."""
    end = html.find('<div class="footnote">')
    end = len(html) if end < 0 else end
    heads = _top_headings(html[:end])
    return _fold(html[:end], heads, 2, open_) + html[end:] if heads else html

_H2 = re.compile(r"(<h2\b[^>]*>.*?</h2>)", re.S)
_H3 = re.compile(r"(<h3\b[^>]*>.*?</h3>)", re.S)
_TAG = re.compile(r"<[^>]+>")
_YEAR = re.compile(r"\b(1[89]\d\d|20\d\d)\b|\b(present|now|today)\b", re.I)
_FACT_LINE = re.compile(r"^\s*([A-Z][A-Za-z ]{0,24}):\s*(.+?)\s*$")


def text_of(html: str) -> str:
    return unescape(_TAG.sub("", html)).strip()


def _inner(heading_html: str) -> str:
    return re.sub(r"^<h\d\b[^>]*>|</h\d>$", "", heading_html.strip(), flags=re.S)


def _id_of(heading_html: str) -> str:
    m = re.search(r'\bid="([^"]+)"', heading_html)
    return m.group(1) if m else ""


def sections(html: str, splitter=_H2):
    """(intro html, [(heading html, heading inner html, body html)])."""
    parts = splitter.split(html)
    intro, rest = parts[0], parts[1:]
    return intro, [(rest[i], _inner(rest[i]), rest[i + 1] if i + 1 < len(rest) else "")
                   for i in range(0, len(rest), 2)]


def split_date(inner_html: str):
    """"Designer, Acme · 2021 – 2024" -> ("Designer, Acme", "2021 – 2024"):
    of the parts around a ·, | or —, the one holding a year (or
    "Present") is the date. ("", title) when there's none."""
    for sep in (" · ", " | ", " — ", " – ", ": "):
        if sep in inner_html:
            left, right = inner_html.split(sep, 1)
            if _YEAR.search(text_of(right)) and not _YEAR.search(text_of(left)):
                return left.strip(), right.strip()
            if _YEAR.search(text_of(left)):
                return right.strip(), left.strip()
    return inner_html, ""


def facts(html: str, before_heading=False):
    """Leading "Key: value" lines - a recipe's Serves/Prep, a book's
    Author/Rating - as ([(key, value html)], the html without them).
    Written as consecutive lines, they arrive as one paragraph.
    before_heading - any paragraph ahead of the first ##, not only the
    first one, so a line of introduction can come before them."""
    head = html.find("<h2")
    for m in re.finditer(r"<p>(.*?)</p>", html[:head] if head >= 0 else html, re.S):
        if not before_heading and html[:m.start()].strip():
            break
        lines = [line for line in re.split(r"\n|<br\s*/?>", m.group(1)) if line.strip()]
        found = [_FACT_LINE.match(text_of(line)) for line in lines]
        if not lines or not all(found):
            continue
        pairs = [(f.group(1).strip(), line.split(":", 1)[1].strip()) for line, f in zip(lines, found)]
        return pairs, html[:m.start()] + html[m.end():]
    return [], html


def _first(pattern, html):
    m = re.search(pattern, html, re.S)
    return m.group(0) if m else ""


def _ld(data) -> Script:
    return Script(NotStr(json.dumps(data, ensure_ascii=False).replace("</", "<\\/")), type="application/ld+json")


# daisyUI fills inline code, and code blocks, with base-200 - the admin's
# own background, where a lone / or # vanished and a block was only an
# outline. A tint of the text colour shows on any background, the same
# for both; ! as daisyUI's :root .prose rule outranks it.
INLINE_CODE = "[&_:not(pre)>code]:bg-base-content/10! [&_:not(pre)>code]:wrap-anywhere [&_pre]:bg-base-content/10!"
# a short list reads as one block: 4px between its items, not the 12px
# the text styling gives them (items holding paragraphs keep those apart)
LIST_GAP = "prose-li:my-1"


def _prose(html, cls="", small=False, **attrs):
    """Writing, at the reading size - 16 px on a phone, 18 px from a tablet
    up - or small, inside a card (a plan, a quote). A size in cls wins."""
    size = "" if re.search(r"\bprose-(sm|base|lg|xl)\b", cls) else ("prose-sm" if small else "md:prose-lg")
    return Div(NotStr(html), cls=f"prose {size} max-w-none {INLINE_CODE} {LIST_GAP} {cls}".strip(),
               **attrs) if html.strip() else None


def _section_spans(html):
    """[(start, end)] of each section at the page's top level - a
    data-fold-break <div>, as place_sections draws every one."""
    depth, spans, start = 0, [], None
    for m in _TAG_ANY.finditer(html):
        closing, name = m.group(1), m.group(2).lower()
        if closing:
            depth -= 1
            if depth == 0 and start is not None:
                spans.append((start, m.end()))
                start = None
        elif name not in _VOID and not m.group(3):
            if depth == 0 and name == "div" and "data-fold-break" in m.group(0):
                start = m.start()
            depth += 1
    return spans


# the writing's size and line height (prose, md:prose-lg), on the whole
# post: a section's words, beside the writing now, read at the same size
READING_TEXT = "text-base leading-[1.75] md:text-lg md:leading-[1.7777778]"


def prose_around_sections(html, prose_cls="", outer_cls="", post_body=True, text=READING_TEXT):
    """The writing in its text styling, and each section beside it rather
    than inside it: the text styling can't be switched back on under a
    not-prose, so a section inside the writing lost its own words'
    links, lists and paragraph spacing. Writing after a section starts
    as far below it as a section after writing does. The whole is
    [data-post-body], for the scripts that read the post."""
    mark = {"data_post_body": True} if post_body else {}
    spans = _section_spans(html)
    if not spans:
        return _prose(html, f"{prose_cls} {outer_cls}".strip(), **mark) or Div(**mark, cls=outer_cls)
    parts, at, after_section = [], 0, False
    for start, end in [*spans, (len(html), len(html))]:
        words = html[at:start]
        if words.strip():
            parts.append(_prose(words, f"{prose_cls} {WORDS_AFTER_SECTION if after_section else ''}".strip()))
        if start < end:
            parts.append(NotStr(html[start:end]))
        after_section, at = start < end or (after_section and not words.strip()), end
    return Div(*parts, **mark, cls=f"{text} {outer_cls}".strip())


def _icon(d):
    """The admin-wide button icon: h-3.5 outline."""
    return NotStr('<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" '
                  f'stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" '
                  f'd="{d}" /></svg>')


PRINT_ICON = ("M6.72 13.83c-.24.03-.48.06-.72.1m.72-.1a42.4 42.4 0 0 1 10.56 0m-10.56 0L6.34 18m10.94-4.17c.24.03"
              ".48.06.72.1m-.72-.1L17.66 18m0 0 .23 2.5a1.13 1.13 0 0 1-1.12 1.23H7.23a1.13 1.13 0 0 1-1.12-1.23L6.34"
              " 18m11.32 0h1.09A2.25 2.25 0 0 0 21 15.75V9.46c0-1.08-.77-2.01-1.84-2.2a48.4 48.4 0 0 0-1.41-.2M6.34 18"
              "H5.25A2.25 2.25 0 0 1 3 15.75V9.46c0-1.08.77-2.01 1.84-2.2.47-.08.94-.15 1.41-.2m10.5 0a48.5 48.5 0 0 "
              "0-10.5 0m10.5 0V3.38c0-.62-.5-1.13-1.13-1.13H7.88c-.62 0-1.13.5-1.13 1.13v3.66M18 10.5h.01v.01H18v-.01Z")
EXTERNAL_ICON = "M13.5 6H5.25A2.25 2.25 0 0 0 3 8.25v10.5A2.25 2.25 0 0 0 5.25 21h10.5A2.25 2.25 0 0 0 18 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"
LEFT_ICON = "M15.75 19.5 8.25 12l7.5-7.5"
RIGHT_ICON = "m8.25 4.5 7.5 7.5-7.5 7.5"
EXPAND_ICON = "M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15"


def PrintButton(label):
    """Beside Listen and Like at the top of a post, in their outline look."""
    return Button(_icon(PRINT_ICON), Span(label, cls="text-sm font-medium"), type="button", data_onclick="printPage",
                  cls="btn btn-sm btn-outline border-base-300 print:hidden")


# ---- wiki links

_WIKI = re.compile(r"\[\[([^\[\]|\n]{1,120})(?:\|([^\[\]\n]{1,120}))?\]\]")


def _post_index(live_only: bool) -> dict:
    """title (any case) and slug -> (slug, title)."""
    from soloblog import posts
    rows = posts.list_all_published() if live_only else posts.list_posts(include_drafts=True)
    index = {}
    for r in rows:
        index[r["slug"]] = (r["slug"], r["title"])
        index.setdefault(r["title"].strip().lower(), (r["slug"], r["title"]))
    return index


def _resolve(target: str, index: dict):
    from soloblog import posts
    target = unescape(target).strip()
    return index.get(target.lower()) or index.get(posts.slugify(target))


def wiki_targets(body_md: str) -> set:
    """The slugs a post's [[links]] point at - drafts included, so a link
    counts as soon as its target is published."""
    if "[[" not in (body_md or ""):
        return set()
    index = _post_index(live_only=False)
    return {hit[0] for m in _WIKI.finditer(body_md) if (hit := _resolve(m.group(1), index))}


def link_wiki(html: str, logged_in: bool) -> str:
    """[[Title]] and [[slug|text]] in rendered html become links - outside
    code, which keeps its brackets. A page that doesn't exist yet is a
    "create it" link for the admin and plain text for a visitor."""
    if "[[" not in html:
        return html
    index = _post_index(live_only=not logged_in)
    from urllib.parse import quote

    def replace(m):
        target, label = m.group(1), m.group(2) or m.group(1)
        hit = _resolve(target, index)
        if hit:
            return f'<a href="/post/{hit[0]}" class="wiki-link">{label}</a>'
        if logged_in:
            return (f'<a href="/admin/new?template=wiki&amp;title={quote(unescape(target))}" class="wiki-link link link-error tooltip" '
                    f'data-tip="Not written yet - start it">{label}</a>')
        return f'<span class="text-base-content/60 tooltip" data-tip="Not written yet">{label}</span>'

    # only outside <pre> and <code>
    pieces = re.split(r"(<pre\b.*?</pre>|<code\b.*?</code>)", html, flags=re.S)
    return "".join(p if i % 2 else _WIKI.sub(replace, p) for i, p in enumerate(pieces))


def backlinks(slug: str, logged_in: bool) -> list:
    from soloblog import posts
    from soloblog.db import get_db
    rows = get_db().execute("SELECT p.* FROM post_links l JOIN posts p ON p.slug = l.from_slug "
                            "WHERE l.to_slug=? ORDER BY p.title", (slug,)).fetchall()
    return [r for r in rows if logged_in or posts.is_live(r)]


# ---- a page

# marks the words between a section's heading and its items, which
# Heading: Centred centres (place_sections) and the items stay as they are
INTRO = "section-intro"
INTRO_CENTRED = "[&_.section-intro]:text-center"


def _with_heading_class(h, cls):
    """A ## with more classes."""
    if '<h2 class="' in h:
        return h.replace('<h2 class="', f'<h2 class="{cls} ', 1)
    return re.sub(r"<h2\b", f'<h2 class="{cls}"', h, count=1)


def _section_heading(h, centred, room, lead=False, after_words=False):
    """A section's ## as it sits in the page: centred, and with the gap
    above it (the section's own Space: if it has one) - none for the
    first thing on a page, a heading's after plain writing."""
    h = _centred(h) if centred else h
    if lead:
        return h
    if after_words and not room:
        return _with_heading_class(h, SECTION_AFTER_WORDS)
    return _with_heading_class(h, f"{SECTION_GAPS.get(room, '')} {HEADING_GAP}".strip())


def _appearing(h, motion):
    """A section's ## comes into view as its section does (its Appear) - on
    the heading itself, so the contents and folding still find it at the
    page's top level."""
    return re.sub(r"(<h2\b[^>]*)>", rf'\1 data-reveal="{motion}">', _with_heading_class(h, _REVEAL), count=1)


def _centred(h):
    """A section's ## centred, its id kept for the contents' links. The
    copy-link button beside it floats free of the words, which would
    otherwise sit off-centre by its width; a fold's own padding is made up
    on the other side."""
    return re.sub(r"<h2\b", '<h2 class="text-center [&_button]:absolute in-[summary.pe-16]:ps-16 in-[summary.pe-8]:ps-8"', h, count=1)


def _intro(intro, space=""):
    return _prose(intro, f"{INTRO} {space or GROUP_SPACE}")


# the writing's own children at the site's width, whatever the page - a
# section (data-section, or the breakout holding one) is left to run wider.
# Written out whole, as Tailwind needs to find them
WRITING_IN_COLUMN = {
    "max-w-3xl": "[&>:not([data-section],:has([data-section]))]:max-w-3xl "
                 "[&>:not([data-section],:has([data-section]))]:mx-auto",
    "max-w-2xl": "[&>:not([data-section],:has([data-section]))]:max-w-2xl "
                 "[&>:not([data-section],:has([data-section]))]:mx-auto",
}


def _toc_without(toc_html, ids):
    """The table of contents without the headings that aren't on the page."""
    for hid in ids:
        pattern = re.escape(f'<a href="#{hid}">')
        toc_html = re.sub(rf"<li><details open><summary>{pattern}.*?</details></li>|<li>{pattern}.*?</a></li>", "",
                          toc_html, flags=re.S)
    return toc_html if "<li>" in toc_html else None


def render(row, s, html, toc_html, logged_in, series=None, deck=True):
    """{"body": what replaces the post body, "wide": bool, "has_wide_section":
    True when a section runs wider than the column, "ld": [extra
    structured data], "before": shown above the title, "column": the
    width of what stays in the reading column of a wide page}."""
    html = link_wiki(html, logged_in)
    from soloblog.ui import content_width
    wide = is_wide(row)
    out = {"body": None, "wide": wide, "ld": [], "before": None,
           # on a wide page, what stays in the reading column - the title,
           # reactions, share buttons, author and comments - at the site's
           # own width (Settings > Appearance > Page width), Narrow or Standard
           "column": f"{content_width(s)} mx-auto w-full" if wide else ""}
    # sections (Pricing, Testimonials...) before the headings get their
    # links and folds, so theirs are made like any heading's
    recipe = _recipe_of_sections(row, html)
    if recipe is not None:
        out["ld"].append(recipe)
    html = place_sections(row, s, html, toc_html, logged_in, series or [], out)
    # a last section carries its own room below: what follows the post adds no gap
    out["ends_with_section"] = SECTION_LAST in html
    if out.get("dropped") and toc_html:
        out["toc"] = _toc_without(toc_html, out["dropped"])
    # a deck is cut at its --- lines, before heading links and folds wrap them
    plain = html
    if s.get("heading_links", "1") == "1":
        html = heading_links(html)
    if fold_style(row, s) != "off":
        html = fold_sections(html, fold_style(row, s) == "open")
    # on a wide page the writing stays in the site's column; only sections go wider
    out["body"] = prose_around_sections(html, outer_cls=WRITING_IN_COLUMN[content_width(s)] if wide else "")
    if row["in_wiki"]:
        _wiki_note(out, row, s, html, logged_in)
    if row["remind_update"]:
        _remind_update(out, row, logged_in)
    if row["link_url"]:
        _link_to(out, row, s)
    if row["slides"] and deck:
        _slide_deck(out, plain)
    # a Contact details or Opening hours section tells search engines of the business
    if out.get("business"):
        out["ld"].append(_business_data(row, out["business"]))
    # a Resume and a Profile section on one page tell search engines of the person once
    out["ld"] = list({to_xml(item): item for item in out["ld"]}.values())
    return out


def _render_milestones(out, row, s, html, toc, logged_in, series):
    """Milestones: each ## an entry, its date first. Settings >
    Appearance > Blog layout picks where the line runs; centred,
    the dates sit across the line from their entries, alternating."""
    from soloblog.ui import timeline_cls, timeline_side, timeline_stagger
    align = s.get("milestones_align") if s.get("milestones_align") in ("left", "center", "right") else "left"
    intro, secs = sections(html)
    items = []
    for i, (_, inner, body) in enumerate(secs):
        title, when = split_date(inner)
        side = timeline_side(align, i)
        date = Div(NotStr(when), cls="text-sm text-base-content/60") if when else None
        box = Div(date if align != "center" else None, H3(NotStr(title), cls=ITEM_TITLE), _prose(body, "mt-1", small=True),
                  cls="timeline-box !bg-base-100 w-full")
        across = "timeline-end" if side == "timeline-start" else "timeline-start"
        items.append(Li(
            Hr() if i else None,
            # centred: the date on the other side of the line, facing it
            Div(date, cls=f"{across} max-md:hidden {'text-end' if across == 'timeline-start' else ''}")
            if align == "center" and when else None,
            Div(NotStr('<span class="block h-3 w-3 rounded-full bg-primary"></span>'), cls="timeline-middle"),
            Div(Div(NotStr(when), cls="text-sm text-base-content/60 md:hidden") if align == "center" and when else None,
                box, cls=f"{side} mb-6 justify-self-stretch min-w-0"),
            Hr() if i < len(secs) - 1 else None,
        ))
    out["body"] = Div(_intro(intro, GROUP_SPACE), Ul(*items, cls=timeline_cls(align), **timeline_stagger(align)))


def Hr():
    from fasthtml.common import Hr as _Hr
    return _Hr(cls="bg-base-300")


_WIKI_LINK = re.compile(r'<a href="(/post/[^"]+)" class="wiki-link">(.*?)</a>', re.S)


def _wiki_note(out, row, s, html, logged_in):
    """A note in the wiki: when it was last updated, and what it links to
    and what links to it."""
    from soloblog import posts
    from soloblog.render import format_date
    links = backlinks(row["slug"], logged_in)
    # the notes this one links to, in the order they come up
    onward = list(dict.fromkeys((href, text_of(label)) for href, label in _WIKI_LINK.findall(html)))
    home = "/" if s.get("home_page") == posts.WIKI_HOME else "/wiki"

    def column(label, items, empty):
        return Div(H2(label, cls="text-sm font-semibold mb-2"),
                   Ul(*[Li(A(title, href=href, cls="link link-hover")) for href, title in items],
                      cls="text-sm list-disc pl-5 space-y-1") if items else empty)

    out["body"] = Div(
        P(i18n.t("Last updated {date}", date=format_date(row['updated_at'] or row['created_at'])),
          cls="text-xs text-base-content/60 mb-3"),
        out["body"],
        Div(Div(
            Div(column(i18n.t("Links from here"), onward, P("-", cls="text-sm text-base-content/50")),
                column(i18n.t("Linked from"), [(f"/post/{r['slug']}", r["title"]) for r in links],
                       P(i18n.t("Nothing links here yet. Link to this page with") + " ",
                         Span(f"[[{row['title']}]]", cls="font-mono"), ".", cls="text-sm text-base-content/60")),
                cls=f"grid sm:grid-cols-2 {ITEMS_GAP}"),
            A(i18n.t("All wiki pages"), href=home, cls="link link-hover text-xs mt-3 inline-block"),
            cls=f"card-body {CARD_PAD} gap-2"), cls="card card-border bg-base-100 mt-8"),
    )


def _render_faq(out, row, s, html, toc, logged_in, series):
    intro, secs = sections(html)
    out["body"] = Div(
        _intro(intro, "mb-4"),
        Div(*[Details(Summary(NotStr(inner), cls="collapse-title font-semibold"),
                      Div(_prose(body), cls="collapse-content"),
                      cls="collapse collapse-arrow join-item border-[length:var(--border)] border-base-300 "
                          "bg-base-100", id=_id_of(h) or None, open=(i == 0))
              for i, (h, inner, body) in enumerate(secs)],
            cls="join join-vertical w-full"))
    out["ld"].append(_ld({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": text_of(inner),
         "acceptedAnswer": {"@type": "Answer", "text": text_of(body)[:2000]}} for _, inner, body in secs]}))


# how a Portfolio shows its work: the site's own choice (Settings >
# Appearance > Images), or a page's "Show as: Rows" line
PORTFOLIO_STYLES = {"grid": "Grid — even tiles, a title under each",
                    "masonry": "Masonry — each image at its own shape, nothing cut off",
                    "rows": "Rows — edge to edge, each row the same height",
                    "screen": "Full screen — one piece at a time, as you scroll",
                    "sideways": "Sideways — a row of tall images you swipe along"}
_SHOW_AS = {"grid": "grid", "masonry": "masonry", "rows": "rows", "full screen": "screen",
            "screen": "screen", "sideways": "sideways"}
# how wide one picture shows in each, so the browser fetches a copy sharp enough
_PORTFOLIO_SIZES = {"grid": "(min-width: 1024px) 26rem, (min-width: 640px) 50vw, 100vw",
                    "masonry": "(min-width: 1024px) 26rem, (min-width: 640px) 50vw, 100vw",
                    "rows": "(min-width: 640px) 40rem, 100vw", "screen": "100vw",
                    "sideways": "(min-width: 640px) 36rem, 85vw"}
_LINK = re.compile(r'<a href="([^"]+)"[^>]*>(.*?)</a>', re.S)
# a picture grows a little as a pointer comes over it - not with "reduce motion"
_ZOOM = "transition-transform duration-700 ease-out group-hover:scale-[1.03] motion-reduce:transition-none"


def _cover_img(url, title):
    """A post's cover as an <img>, as a picture written in it would be."""
    options = images.srcset(url)
    sized = f' srcset="{escape(options)}" sizes=""' if options else ""
    return (f'<img src="{escape(url)}"{sized} alt="{escape(images.alt_text_for_url(url) or title)}" '
            f'loading="lazy">')


def portfolio_items(row, html):
    """(the intro, its arrangement, [{id, title, href, label, img, credit,
    words}]) - each ## a piece of work, then any posts and pages with the
    intro's "Tag:"."""
    from soloblog import posts
    intro, secs = sections(html)
    show, intro = section_registry.take_line(intro, "show as")
    tag, intro = section_registry.take_line(intro, "tag")
    items = []
    for h, inner, body in secs:
        img, credit, rest = _take_image(body)
        # not a link in the picture's caption - a photo credit isn't the work
        link = _LINK.search(re.sub(r"<figcaption\b.*?</figcaption>", "", rest, flags=re.S))
        if link:
            # a paragraph that was only the link goes with it
            rest = re.sub(r"<p>\s*" + re.escape(link.group(0)) + r"\s*</p>", "", rest, count=1)
        rest = re.sub(r"<figure>\s*</figure>|<p>\s*</p>", "", rest)
        items.append({"id": _id_of(h), "title": inner, "href": unescape(link.group(1)) if link else "",
                      "label": link.group(2) if link else "", "img": img, "credit": credit, "words": rest.strip()})
    if tag:
        mine = posts.url_for(row) if "slug" in row.keys() else ""
        for p in posts.list_tagged(tag.lstrip("#")):
            if posts.url_for(p) == mine or posts.is_protected(p):
                continue
            items.append({"id": "", "title": escape(p["title"]), "href": posts.url_for(p), "label": "",
                          "img": _cover_img(p["cover_image"], p["title"]) if p["cover_image"] else "",
                          "credit": "", "words": f"<p>{escape(posts.teaser(p))}</p>" if posts.teaser(p) else ""})
    return intro, _SHOW_AS.get(show, ""), items


def _portfolio_picture(item, style, cls, n, credit_cls=None):
    """A piece's picture, linked to its page - or, with no page, opening
    bigger in the lightbox, as a gallery's do - its credit over its corner."""
    img = re.sub(r'\s(?:loading|fetchpriority)="[^"]*"', "", item["img"])
    img = re.sub(r'\bsizes="[^"]*"', f'sizes="{_PORTFOLIO_SIZES[style]}"', img)
    # the first few are what anyone sees first: fetched straight away
    img = _with_class(img, cls).replace("<img ", '<img loading="lazy" ' if n > 2 else "<img ", 1)
    if item["href"]:
        away = _portfolio_away(item)
        link = A(NotStr(img), href=item["href"], tabindex="-1", aria_hidden="true",
                 target="_blank" if away else None, rel="noopener" if away else None,
                 cls="block overflow-hidden rounded-box")
    else:
        src = re.sub(r'^src="|"$', "", _first(r'src="([^"]+)"', img))
        link = A(NotStr(img), href=unescape(src), data_lightbox="portfolio", data_title=text_of(item["title"]),
                 data_caption=item["credit"], cls="block overflow-hidden rounded-box")
    credit = Div(NotStr(item["credit"]), cls=credit_cls or CREDIT_OVER) if item["credit"] else None
    return Div(link, credit, cls="relative")


def _portfolio_away(item):
    """A piece whose link goes to another site - its title says so with
    ↗, and it opens in a new tab. One of this site's pages doesn't."""
    from urllib.parse import urlsplit
    href = item["href"]
    if not href.startswith(("https://", "http://")):
        return False
    host = (urlsplit(href).hostname or "").removeprefix("www.")
    return not host or host != (urlsplit(config.BASE_URL).hostname or "").removeprefix("www.")


def _portfolio_title(item, cls):
    inner = NotStr(item["title"])
    if not item["href"]:
        return H3(inner, cls=cls)
    away = _portfolio_away(item)
    return H3(A(inner, NotStr(' <span aria-hidden="true">↗</span>') if away else None, href=item["href"],
                target="_blank" if away else None, rel="noopener" if away else None, cls="link link-hover"), cls=cls)


def _render_portfolio(out, row, s, html, toc, logged_in, series):
    """A portfolio: the title big, a line about the work, then the work
    itself, pictures first - as tiles, uncropped columns, rows edge to
    edge, a screen each or a row you swipe along (PORTFOLIO_STYLES). A
    piece with no picture is a quiet tile of its own words."""
    from soloblog.gallery import CHEVRON_LEFT, CHEVRON_RIGHT
    from soloblog.ui import Breakout
    intro, show, items = portfolio_items(row, html)
    style = show or s.get("portfolio_style") or "grid"
    style = style if style in PORTFOLIO_STYLES else "grid"
    head = _intro(intro, GROUP_SPACE) if text_of(intro) else None
    words_cls = "prose prose-sm max-w-none text-base-content/70 [&_p]:my-1 [&_:not(pre)>code]:wrap-anywhere mt-1"

    def below(item):
        return Div(_portfolio_title(item, f"{ITEM_TITLE} tracking-tight m-0"),
                   Div(NotStr(item["words"]), cls=f"{words_cls} line-clamp-3") if text_of(item["words"]) else None,
                   cls="mt-4")

    def plain(item):
        # no picture: its words on the page's quieter tone, the size of a picture
        return Div(_portfolio_title(item, f"{LEAD_TITLE} tracking-tight m-0"),
                   Div(NotStr(item["words"]), cls=words_cls) if text_of(item["words"]) else None,
                   cls=f"rounded-box bg-base-content/5 {PANEL_PAD} flex flex-col justify-end gap-2 min-h-56")

    tiles = []
    for n, item in enumerate(items):
        hid = item["id"] or None
        if not item["img"]:
            tiles.append(Div(plain(item), id=hid, cls=f"{_REVEAL} break-inside-avoid mb-10"
                         if style == "masonry" else _REVEAL))
        elif style == "grid":
            tiles.append(Div(_portfolio_picture(item, style, f"w-full aspect-[4/3] object-cover {_ZOOM}", n),
                             below(item), id=hid, cls=f"group {_REVEAL}"))
        elif style == "masonry":
            tiles.append(Div(_portfolio_picture(item, style, f"w-full h-auto {_ZOOM}", n), below(item),
                             id=hid, cls=f"group break-inside-avoid mb-10 sm:mb-12 {_REVEAL}"))
        elif style == "rows":
            ratio = 1.5
            src = re.search(r'src="(/uploads/[^"?]+)"', item["img"])
            if src:
                from soloblog.gallery import ratio as ratio_of
                ratio = ratio_of(src.group(1))
            # each grows in proportion to its own shape: every row the same
            # height, filling the width exactly (as a justified gallery)
            tiles.append(Div(
                _portfolio_picture(item, style, f"w-full h-64 sm:h-80 lg:h-96 object-cover {_ZOOM}", n,
                                   CREDIT_OVER.replace("bottom-1.5", "top-1.5")),
                Div(_portfolio_title(item, f"{ITEM_TITLE} m-0 text-white [&_a]:text-white [&_a]:no-underline"),
                    cls="pointer-events-none [&_a]:pointer-events-auto absolute inset-x-0 bottom-0 rounded-b-box "
                        "px-4 pb-3 pt-12 bg-linear-to-t from-black/75 to-transparent opacity-0 transition-opacity "
                        "group-hover:opacity-100 group-focus-within:opacity-100 pointer-coarse:opacity-100"),
                id=hid, style=f"flex: {ratio:.3f} 1 {ratio * 16:.1f}rem", cls=f"group relative {_REVEAL}"))
        elif style == "screen":
            tiles.append(Div(Breakout(Div(
                NotStr(_with_class(re.sub(r'\bsizes="[^"]*"', 'sizes="100vw"', item["img"]),
                                   "absolute inset-0 w-full h-full object-cover")
                       .replace(' loading="lazy"', "" if n == 0 else ' loading="lazy"')),
                Div(cls="absolute inset-0 bg-gradient-to-t from-black/80 via-black/30 to-transparent"),
                Div(_portfolio_title(item, "text-4xl sm:text-6xl font-extrabold tracking-tighter leading-[1.05] "
                                           "text-balance m-0 [&_a]:text-white [&_a]:no-underline"),
                    Div(NotStr(item["words"]), cls="text-lg sm:text-xl text-white/85 max-w-2xl [&_p]:m-0 "
                                                   "[&_a]:text-white [&_a]:underline")
                    if text_of(item["words"]) else None,
                    A(NotStr(item["label"] or escape(i18n.t("View"))),
                      NotStr(f' <span aria-hidden="true">{"↗" if _portfolio_away(item) else "→"}</span>'),
                      href=item["href"], target="_blank" if _portfolio_away(item) else None,
                      rel="noopener" if _portfolio_away(item) else None, cls="btn self-start mt-2")
                    if item["href"] else None,
                    cls=f"relative z-10 flex flex-col gap-4 {_col(s).replace('max-w-3xl', 'max-w-5xl')} "
                        "px-4 sm:px-8 pb-14 sm:pb-20 text-white"),
                Div(NotStr(item["credit"]), cls=images.CAPTION_OVER_CLS) if item["credit"] else None,
                cls="relative flex items-end overflow-hidden min-h-[calc(100svh-var(--header-h,0px))]"), "full", s),
                id=hid, cls=_REVEAL))
        else:  # sideways
            tiles.append(Div(_portfolio_picture(item, style, f"h-[55vh] sm:h-[68vh] w-full object-cover {_ZOOM}", n),
                             below(item), id=hid, cls="carousel-item group flex-col w-[82vw] sm:w-[34rem]"))
    if style == "grid":
        cols = "sm:grid-cols-2" if len(tiles) in (2, 4) else "sm:grid-cols-2 lg:grid-cols-3"
        work = Div(*tiles, cls=f"grid {cols} {GALLERY_GAP}")
    elif style == "masonry":
        work = Div(*tiles, cls=f"columns-1 sm:columns-2 lg:columns-3 {ITEMS_GAP}")
    elif style == "rows":
        # the last row stays near its pieces' own widths, not stretched across
        work = Breakout(Div(*tiles, Div(cls="grow-[4] basis-0 h-0"), cls="flex flex-wrap gap-2 px-2"), "full", s)
    elif style == "screen":
        work = Div(*tiles, cls="flex flex-col gap-2")
    else:
        work = Breakout(Div(
            Div(*tiles, cls="carousel carousel-start w-full gap-6 px-4 sm:px-8 pb-2 scroll-px-4 sm:scroll-px-8",
                **on("scroll", "syncSlider", EL)),
            Button(NotStr(CHEVRON_LEFT), type="button", aria_label=i18n.t("Previous"),
                   cls="btn btn-circle absolute left-4 top-[34vh] -translate-y-1/2",
                   **on("click", "slideGallery", EL, -1)),
            Button(NotStr(CHEVRON_RIGHT), type="button", aria_label=i18n.t("Next"),
                   cls="btn btn-circle absolute right-4 top-[34vh] -translate-y-1/2",
                   **on("click", "slideGallery", EL, 1)),
            cls="gallery-slider relative"), "full", s)
    out["body"] = Div(head, work,
                      cls=f"portfolio portfolio-{style}", data_portfolio=style)


# a plan's cards side by side, as many as fit
_PLAN_COLUMNS = {1: "", 2: "sm:grid-cols-2", 3: "sm:grid-cols-2 lg:grid-cols-3", 4: "sm:grid-cols-2 lg:grid-cols-4"}


def _render_pricing(out, row, s, html, toc, logged_in, series):
    """Plans as cards: a ## with a "Price:" line is a plan. The first one
    with a "Badge:" line is pointed out - its border, badge and button in
    the primary colour, the page's one primary action. Other ## sections
    (notes, questions) stay text under the cards."""
    intro, secs = sections(html)
    plans, after = [], []
    for h, inner, body in secs:
        pairs, rest = facts(body.strip())
        price = next((v for k, v in pairs if k.lower() == "price"), None)
        if price is None:
            after.append(h + body)
            continue
        link = None
        for m in re.finditer(r'<a href="([^"]+)"[^>]*>(.*?)</a>',
                             re.sub(r"<figcaption\b.*?</figcaption>", "", rest, flags=re.S), re.S):
            link = m
        if link:
            # a paragraph that was only the link becomes the button alone
            rest = re.sub(r"<p>\s*" + re.escape(link.group(0)) + r"\s*</p>", "", rest, count=1)
        plans.append((h, inner, text_of(price), pairs, rest, link))
    featured = next((i for i, p in enumerate(plans)
                     if any(k.lower() == "badge" for k, _ in p[3])), None)
    cards = []
    for i, (h, inner, price, pairs, rest, link) in enumerate(plans):
        amount, _, per = price.partition(" ")
        badge = next((text_of(v) for k, v in pairs if k.lower() == "badge"), "")
        star = i == featured
        cards.append(Div(Div(
            Span(badge, cls=f"badge badge-sm self-start {'badge-primary' if star else ''}") if badge else None,
            H3(NotStr(inner), cls=ITEM_TITLE),
            # Divs, not Ps: daisyUI stretches a card's paragraphs to fill it
            Div(Span(amount, cls="text-3xl font-bold"),
                Span(f" {per}", cls="text-base-content/60") if per else None, cls="mb-1"),
            *[Div(Span(k, cls="text-base-content/60"), " ", Span(NotStr(v)), cls="text-sm")
              for k, v in pairs if k.lower() not in ("price", "badge")],
            # what a plan includes, one line each - no bullets in a card
            _prose(rest, "prose-ul:list-none prose-ul:ps-0 prose-ul:my-0 prose-li:ps-0", small=True),
            Div(A(NotStr(link.group(2)), href=link.group(1), cls=f"btn btn-block {'btn-primary' if star else ''}"),
                cls="card-actions mt-auto pt-4") if link else None,
            cls=f"card-body {CARD_PAD} gap-2"),
            id=_id_of(h) or None,
            cls=f"card card-border bg-base-100 {'border-primary' if star else ''} {LIFT if link else ''}"))
    out["body"] = Div(
        Div(_intro(intro), cls=_col(s)),
        Div(*cards, cls=f"grid {ITEMS_GAP} {_PLAN_COLUMNS.get(len(cards), 'sm:grid-cols-2 lg:grid-cols-3')}")
        if cards else None,
        Div(_prose("".join(after), "mt-12 sm:mt-16"), cls=_col(s)) if after else None,
    )


def _remind_update(out, row, logged_in):
    """When the page was last updated, and for the admin, a nudge once it's
    been three months."""
    from soloblog.render import format_date
    updated = row["updated_at"] or row["created_at"]
    try:
        age = (utcnow() - datetime.fromisoformat(updated[:19])).days
    except ValueError:
        age = 0
    out["before"] = Div(
        Span(i18n.t("Last updated {date}", date=format_date(updated)), cls="font-medium"),
        cls="alert alert-info alert-soft text-sm mb-4 block")
    if logged_in and age > 90:
        out["before"] = Div(out["before"], Div(f"It's been {age} days - time for an update?",
                                               cls="alert alert-warning alert-soft text-sm mb-4"))


def _link_to(out, row, s):
    """A page that points at another outside the site: the title goes
    there, and a button under the words. One of this site's own pages
    is just the words - a visitor is sent straight there."""
    url = row["link_url"]
    from soloblog import posts
    from urllib.parse import urlsplit
    if posts.is_local_link(url):
        return
    out["title_href"] = url
    host = urlsplit(url).hostname or url
    host = host[4:] if host.startswith("www.") else host
    out["body"] = Div(out["body"], Div(
        A(_icon(EXTERNAL_ICON), Span(i18n.t("Read it on {site}", site=host), cls="ml-1"), href=url, target="_blank",
          rel="noopener", cls="btn btn-sm btn-primary"), cls="flex justify-end mt-4"))


_SPEAKER = re.compile(r"<p>\s*<strong>([^<]{1,40}?):?\s*</strong>\s*:?\s*(.*?)</p>", re.S)


def _chat(html):
    """The conversation in html - each paragraph starting with a bold
    speaker a bubble, other paragraphs between - or None without a speaker."""
    first = None
    pieces, pos = [], 0
    for m in _SPEAKER.finditer(html):
        name = unescape(m.group(1)).strip().rstrip(":")
        first = first or name
        if m.start() > pos:
            pieces.append(_prose(html[pos:m.start()], "my-3"))
        side = "chat-start" if name == first else "chat-end"
        # the host in the plain bubble (base-300), the guest in the brand colour
        bubble = "" if name == first else "chat-bubble-primary"
        pieces.append(Div(Div(name, cls="chat-header text-xs mb-1"),
                          Div(NotStr(m.group(2)), cls=f"chat-bubble {bubble} max-w-[85%]"), cls=f"chat {side}"))
        pos = m.end()
    if first is None:
        return None
    if pos < len(html):
        pieces.append(_prose(html[pos:], "my-3"))
    return Div(*pieces, cls="interview flex flex-col gap-1")


def _render_interview_part(out, row, s, html, toc, logged_in, series):
    chat = _chat(html)
    out["body"] = chat if chat is not None else _prose(html)


def _render_contents(out, row, s, html, toc, logged_in, series):
    """A series' parts in their order, each a link - this page's own series,
    or the one a "Series:" line names. Read each time the page is shown,
    so a part added or moved shows at once."""
    from soloblog import posts
    named, rest = section_registry.take_line(html, "series")
    name = (posts.find_series(posts.slugify(named)) or "") if named else row["series_name"]
    parts = [p for p in posts.series_siblings(name) if logged_in or posts.is_live(p)] if name else []
    if not parts:
        out["nothing"] = not logged_in
        # for the admin, why - a visitor sees nothing
        why = (f"there's no series called “{named}”" if named and not name else
               f"“{name}” has no published parts yet" if name else "this page isn't in a series")
        fix = "" if name else " Choose one in Post settings, or add a Series line."
        out["body"] = Div(f"Contents is empty - {why}.{fix} Only you see this.", cls="alert alert-soft text-sm")
        return
    items = [Li(A(p["title"], href=posts.url_for(p), aria_current="page" if p["slug"] == row["slug"] else None,
                  cls="link link-hover pointer-coarse:inline-block pointer-coarse:min-h-11 "
                      + ("font-semibold no-underline" if p["slug"] == row["slug"] else "")),
                cls="ps-1 marker:text-base-content/60") for p in parts]
    out["body"] = Div(_prose(rest, "mb-4"), Nav(Ol(*items, cls="list-decimal ms-6 flex flex-col gap-1"),
                                                aria_label=i18n.t("Contents")))


def _render_previous_next(out, row, s, html, toc, logged_in, series):
    """The pages before and after this one that share its first tag, as
    large pictures - nothing without a tag, or alone in it."""
    cards = next_in_portfolio(row, (i18n.t("Previous"), i18n.t("Next")))
    out["nothing"] = cards is None
    out["body"] = Div(_prose(html, "mb-4"), cards)


_DURATION = re.compile(r"(?:(\d+)\s*h(?:ours?|rs?)?)?\s*(?:(\d+)\s*m(?:in(?:utes?|s)?)?)?", re.I)


def _iso_duration(text: str):
    m = _DURATION.fullmatch(text.strip())
    if not m or not (m.group(1) or m.group(2)):
        return None
    return "PT" + (f"{m.group(1)}H" if m.group(1) else "") + (f"{m.group(2)}M" if m.group(2) else "")


def _facts_strip(pairs):
    """A recipe's Serves, Prep, Cook... side by side."""
    return Div(*[Div(Div(k, cls="stat-title"), Div(NotStr(v), cls="stat-value text-lg"), cls="stat py-2 px-4")
                 for k, v in pairs],
               cls="stats stats-vertical sm:stats-horizontal w-full bg-base-100 border-[length:var(--border)] "
                   "border-base-300 mb-6") if pairs else None


def _tick_list(items):
    return Div(*[Label(Input(type="checkbox", cls="peer checkbox checkbox-sm checkbox-primary"),
                       Span(NotStr(i), cls="peer-checked:line-through"), cls="flex items-start gap-2 cursor-pointer")
                 for i in items], cls="flex flex-col gap-2 mb-6")


def _numbered_steps(items):
    return Ul(*[Li(Span(str(n), cls="badge badge-primary badge-lg shrink-0"), Div(NotStr(i), cls="pt-0.5"),
                   cls="flex items-start gap-3") for n, i in enumerate(items, 1)],
              cls="flex flex-col gap-4 mb-6")


_LI = re.compile(r"<li(?:\s[^>]*)?>(.*?)</li>", re.S)
_LIST = re.compile(r"<[uo]l(?:\s[^>]*)?>(.*?)</[uo]l>", re.S)


def _list_part(html, draw):
    """Words before a list, the list drawn by draw, words after it - the
    words only when there's no list."""
    m = _LIST.search(html)
    items = _LI.findall(m.group(1)) if m else []
    if not items:
        return _prose(html)
    return Div(_prose(html[:m.start()], "mb-4"), draw(items), _prose(html[m.end():], "mt-2"))


def _render_ingredients(out, row, s, html, toc, logged_in, series):
    out["body"] = _list_part(html, _tick_list)


def _render_method(out, row, s, html, toc, logged_in, series):
    out["body"] = _list_part(html, _numbered_steps)


def _render_recipe_facts(out, row, s, html, toc, logged_in, series):
    pairs, rest = facts(html, before_heading=True)
    out["body"] = Div(_facts_strip(pairs), _prose(rest)) if pairs else _prose(html)


def _recipe_ld(row, pairs, ingredients, steps):
    data = {"@context": "https://schema.org", "@type": "Recipe", "name": row["title"],
            "description": row["summary"] or None, "recipeIngredient": ingredients,
            "recipeInstructions": [{"@type": "HowToStep", "text": t} for t in steps]}
    for k, v in pairs:
        key, value = k.lower(), text_of(v)
        if key in ("serves", "servings", "yield", "makes"):
            data["recipeYield"] = value
        elif key in ("prep", "prep time"):
            data["prepTime"] = _iso_duration(value)
        elif key in ("cook", "cook time", "bake"):
            data["cookTime"] = _iso_duration(value)
        elif key in ("total", "total time"):
            data["totalTime"] = _iso_duration(value)
    if row["cover_image"]:
        data["image"] = config.BASE_URL + row["cover_image"] if row["cover_image"].startswith("/") else row["cover_image"]
    return _ld({k: v for k, v in data.items() if v})


def _recipe_of_sections(row, html):
    """Search engines hear a page is a recipe when it has an Ingredients or
    a Method section: the first of each, and of Recipe facts, say what
    the recipe is. None otherwise."""
    first = {}
    for _, _, body in sections(html)[1]:
        found = section_registry.section_kind(body)
        if found and found[0] in ("ingredients", "method", "recipe_facts"):
            text = found[1]
            for name in section_registry.SHARED:
                text = section_registry.take_line(text, name.lower())[1]
            first.setdefault(found[0], text)
    if "ingredients" not in first and "method" not in first:
        return None
    def items(kind):
        return [text_of(i) for i in _LI.findall(first.get(kind, ""))]
    return _recipe_ld(row, facts(first.get("recipe_facts", ""), before_heading=True)[0],
                      items("ingredients"), items("method"))


def _rating(value: str):
    """"4/5", "4", "★★★★" or "4.5 out of 5" -> 0..5, or None."""
    if "★" in value:
        return float(value.count("★"))
    m = re.search(r"(\d+(?:\.\d)?)\s*(?:/|out of)\s*(\d+)", value) or re.fullmatch(r"\s*(\d(?:\.\d)?)\s*", value)
    if not m:
        return None
    top = float(m.group(2)) if m.lastindex and m.lastindex > 1 else 5.0
    return max(0.0, min(5.0, float(m.group(1)) * 5 / top)) if top else None


def Stars(score: float):
    """daisyUI rating, read-only."""
    full = int(round(score))
    return Div(*[Span(cls=f"mask mask-star-2 bg-warning w-4 h-4 {'' if i < full else 'opacity-20'}")
                 # not daisyUI's .rating - that dims every star unless it's a checked input
                 for i in range(5)], cls="flex gap-0.5 my-1", aria_label=f"{score:g} out of 5",
               role="img")


def _render_reviews(out, row, s, html, toc, logged_in, series):
    intro, secs = sections(html)
    items, reviews = [], []
    for h, inner, body in secs:
        img = _first(r"<img\b[^>]*>", body)
        rest = body.replace(img, "", 1) if img else body
        rest = re.sub(r"<p>\s*</p>|<figure>\s*(<figcaption>.*?</figcaption>)?\s*</figure>", "", rest, flags=re.S)
        pairs, notes = facts(rest.strip())
        score = None
        shown = []
        for k, v in pairs:
            if k.lower() == "rating":
                score = _rating(text_of(v))
            else:
                shown.append(Div(Span(k, cls="text-base-content/60"), " ", Span(NotStr(v)), cls="text-sm"))
        items.append(Div(
            Div(NotStr(img.replace("<img ", f'<img class="w-24 h-36 object-cover rounded-box {SHADOW_REST}" ', 1)),
                cls="shrink-0") if img else None,
            Div(H3(NotStr(inner), cls=ITEM_TITLE), Stars(score) if score is not None else None,
                *shown, _prose(notes, "mt-2"), cls="min-w-0 flex-1"),
            id=_id_of(h) or None,
            cls="flex gap-4 py-6 border-b-[length:var(--border)] border-base-300 last:border-0"))
        review = {"@type": "Review", "itemReviewed": {"@type": "Book", "name": text_of(inner)},
                  "author": {"@type": "Person", "name": s.get("author_name") or s["site_title"]}}
        author = next((text_of(v) for k, v in pairs if k.lower() == "author"), None)
        if author:
            review["itemReviewed"]["author"] = {"@type": "Person", "name": author}
        if score is not None:
            review["reviewRating"] = {"@type": "Rating", "ratingValue": score, "bestRating": 5}
        reviews.append(review)
    out["body"] = Div(_intro(intro, "mb-2"), Div(*items))
    if reviews:
        out["ld"].append(_ld({"@context": "https://schema.org", "@type": "ItemList",
                              "itemListElement": [{"@type": "ListItem", "position": i + 1, "item": r}
                                                  for i, r in enumerate(reviews)]}))


_USE_ITEM = re.compile(r"^\s*(<strong>.*?</strong>|<a\b[^>]*>.*?</a>)\s*(?:[-–—:]\s*)?(.*)$", re.S)


def _render_uses(out, row, s, html, toc, logged_in, series):
    intro, secs = sections(html)
    groups = []
    for h, inner, body in secs:
        items = re.findall(r"<li>(.*?)</li>", body, re.S)
        rows = []
        for item in items:
            m = _USE_ITEM.match(item)
            name, desc = (m.group(1), m.group(2)) if m else (item, "")
            name = re.sub(r"</?strong>", "", name)
            name = name.replace("<a ", '<a class="link link-hover" ', 1)
            # on a phone the description goes under the name - daisyUI's list
            # puts a row's parts all in its first grid row, and the name was
            # left a column a letter wide
            rows.append(Li(Div(NotStr(name), cls="font-medium"),
                           Div(NotStr(desc), cls="text-sm text-base-content/70 max-sm:row-start-2!")
                           if desc.strip() else None,
                           cls="list-row py-2 grid-cols-1 sm:grid-cols-[12rem_1fr] max-sm:gap-y-1"))
        rest = re.sub(r"<ul>.*?</ul>", "", body, count=1, flags=re.S) if items else body
        groups.append(Div(Div(
            H3(NotStr(inner), cls=ITEM_TITLE),
            _prose(rest, small=True),
            Ul(*rows, cls="list") if rows else None,
            cls=f"card-body {CARD_PAD} gap-2"), id=_id_of(h) or None, cls="card card-border bg-base-100"))
    out["body"] = Div(_intro(intro, "mb-4"), Div(*groups, cls=f"flex flex-col {ITEMS_GAP}"))


def _slide_deck(out, html):
    """The page as a deck, one slide between each --- line, filling the
    screen (public.py). Under two slides it stays a page."""
    slides = [p for p in re.split(r"<hr\s*/?>", html) if p.strip()]
    if len(slides) < 2:
        return
    out["deck"] = True
    out["wide"] = True
    out["body"] = Div(
        # the way back to the site - the deck has no header (Esc goes there too, slides.js)
        A(_icon(LEFT_ICON), Span(i18n.t("Back to the site"), cls="ml-1"), href="/", data_slides_exit=True,
          cls="btn btn-ghost btn-sm absolute top-2 left-2 z-10"),
        Div(*[Div(prose_around_sections(p, "prose-lg lg:prose-2xl text-center [&_img]:mx-auto [&_img]:max-h-[60dvh]",
                                        post_body=False,
                                        text="text-center text-lg leading-[1.7777778] lg:text-2xl lg:leading-[1.6666667]"),
                  # box-border: daisyUI's carousel-item is content-box, so the
                  # padding made each slide 64px bigger than the frame - it
                  # could be dragged about, and each swipe landed further off
                  cls="slide carousel-item box-border w-full h-full items-center justify-center p-8 sm:p-12 "
                      "overflow-x-hidden overflow-y-auto",
                  data_index=str(i)) for i, p in enumerate(slides)],
            cls="slides-track carousel w-full flex-1 min-h-0 overflow-y-hidden overscroll-x-contain bg-base-100",
            tabindex="0", **on("scroll", "syncSlides", EL)),
        Div(
            Div(Button(_icon(LEFT_ICON), type="button", cls="btn btn-sm join-item", aria_label=i18n.t("Previous slide"),
                       **on("click", "moveSlide", EL, -1)),
                Button(_icon(RIGHT_ICON), type="button", cls="btn btn-sm join-item", aria_label=i18n.t("Next slide"),
                       **on("click", "moveSlide", EL, 1)), cls="join"),
            Span(f"1 / {len(slides)}", cls="slides-count text-sm tabular-nums"),
            Button(_icon(EXPAND_ICON), Span(i18n.t("Full screen"), cls="ml-1"), type="button", cls="btn btn-sm ml-auto",
                   **on("click", "fullscreenSlides", EL)),
            cls="flex items-center gap-2 px-3 py-2 bg-base-100 border-t-[length:var(--border)] border-base-300"),
        cls="slides relative flex flex-col h-dvh bg-base-100", data_count=str(len(slides)))


# ---- sections for a small business or a club.
# Each is still plain markdown: a ### is an item (a service, a person, a
# product, an event), and short "Key: value" lines under it are its facts.

# The site's spacing, by role - tight inside a group, wide between them,
# so a page shows what belongs together. Every section, the blog roll and
# the page itself use these (public.py too), not a gap of their own.
CARD_PAD = "p-5 sm:p-6"            # inside a card
PANEL_PAD = "p-6 sm:p-8"           # inside a panel: a whole section on a card, a tile of words
# Space between sections (Settings > Width and spacing, or a page's own):
# the gaps between a page's parts are multiplied by --space, which Small
# and Large set on the page - Medium is the gaps as written
SPACINGS = {"small": "Small", "medium": "Medium", "large": "Large"}
# Section headings (Settings > Width and spacing, or a section's own Heading: line)
SECTION_HEADINGS = {"left": "On the left", "centre": "Centred"}
# The room from one section to the next (--section-gap) - the one place to
# change it: a phone's first, then a wide screen's. Written out whole, as
# Tailwind needs.
SECTION_GAPS = {"small": "[--section-gap:2rem] sm:[--section-gap:3rem]",
                "medium": "[--section-gap:5rem] sm:[--section-gap:9rem]",
                "large": "[--section-gap:9rem] sm:[--section-gap:18rem]"}
# the page's own: the gap, and --space for the gaps inside a section
SPACE_SCALE = {"small": f"{SECTION_GAPS['small']} [--space:0.5] [&_.prose>h2]:mt-[1.25em]",
               "medium": SECTION_GAPS["medium"],
               "large": f"{SECTION_GAPS['large']} [--space:1.5] [&_.prose>h2]:mt-[3em]"}
# a section's own Space: its own gap and --space
SECTION_ROOM = {"small": f"{SECTION_GAPS['small']} [--space:0.5]", "medium": f"{SECTION_GAPS['medium']} [--space:1]",
                "large": f"{SECTION_GAPS['large']} [--space:1.5]"}
# a section's heading starts it: the gap above it (important, as the page's
# rule on .prose>h2 is more specific)
HEADING_GAP = "mt-(--section-gap)!"
# a section in a post. The room is above each one (a section is followed
# by another ##, where the next room starts): the words under a heading,
# or the gap where the section starts itself
SECTION_GAP = "mt-[calc(1.5rem*var(--space,1))] sm:mt-[calc(2rem*var(--space,1))]"
# ...and where a section meets plain writing, or sits on a page with
# writing of its own, the room a heading has there: the whole gap is for
# one section to the next on a page made of them - in a post it opened
# a hole in the middle of the reading. On a section's ##
# (important, as the page's rule on .prose>h2 is more specific), as a
# folded heading's (_fold) - the writing above keeps its last margin -
# and on the writing after a section, whose own first margin goes, as
# under anything with no margin of its own
SECTION_AFTER_WORDS = "mt-[calc(2rem*var(--space,1))]!"
WORDS_AFTER_SECTION = "mt-[calc(2rem*var(--space,1))] [&>:first-child]:mt-0!"
# A section ends where its last thing does: a margin under its last
# block (a grid, a list) is for words after it, and only pushed the next
# part of the page further away, by a different amount in each section
SECTION_ENDS = ("[&>:last-child]:mb-0! [&>:last-child>:last-child]:mb-0! "
                "[&>:last-child>:last-child>:last-child]:mb-0!")
SECTION_APART = "mt-(--section-gap)"
# ...and the last one on the page half that room under it, before what
# follows the post and the footer - the footer is a break of its own, and
# a whole gap there read as too much on a page set to Large
SECTION_LAST = "pb-[calc(var(--section-gap)/2)]"
PART_GAP = "mt-[calc(3rem*var(--space,1))] sm:mt-[calc(4rem*var(--space,1))]"     # a part after the items
# a group's parts stacked SECTION_GAP apart - what follows a post, a
# built-in page's parts. A gap, not a margin on each: a part hidden in the
# browser (a side panel shown beside the column) leaves no room behind
PARTS_SPACE = "gap-[calc(1.5rem*var(--space,1))] sm:gap-[calc(2rem*var(--space,1))]"   # side by side too
PARTS = f"flex flex-col {PARTS_SPACE}"
ITEMS_GAP = "gap-6 sm:gap-8"       # between cards or entries
TIGHT_GAP = "gap-4"                # between tiles or rows that read as one block
# a gallery's tiles: as far apart as cards, with room under each for its title
GALLERY_GAP = "gap-x-6 gap-y-12 sm:gap-x-8 sm:gap-y-16"
# An item's title - a card's, a column's, an entry's: one size in every
# section, an <h3> under the section's own <h2>. LEAD_TITLE is the one
# item a section makes big (a bento's first tile).
ITEM_TITLE = "text-lg font-semibold leading-snug"
LEAD_TITLE = "text-2xl font-semibold leading-tight"
# Two shadows: a small one under a small picture, a deep one under a card
# or picture set apart from the page. (LIFT's is a card under the pointer.)
SHADOW_REST = "shadow-sm"
SHADOW_RAISED = "shadow-xl"
GROUP_SPACE = "mb-8 sm:mb-12"      # an intro or heading, before its items
# a call to action: a card in the main colour, its words in the colour made for it
CTA_CARD = (f"card bg-primary text-primary-content {SHADOW_RAISED} px-6 py-14 sm:py-20 text-center items-center "
            "overflow-hidden")
ON_PRIMARY = "text-primary-content/85 [&_a]:text-primary-content [&_strong]:text-primary-content"
# a quieter second button on the main colour, or over a photo's dark layer:
# daisyUI's outline button takes the page's text colour, which can vanish
# there, so its own colour variables are set to the card's text colour (white
# on a photo) - filled with it on hover
BTN_ON_PRIMARY = ("btn btn-outline [--btn-color:var(--color-primary-content)] "
                  "[--btn-border:var(--color-primary-content)] [--btn-fg:var(--color-primary)]")
BTN_ON_PHOTO = "btn btn-outline [--btn-color:var(--color-white)] [--btn-border:var(--color-white)] [--btn-fg:var(--color-black)]"
# a card you act on (it has a button) rises a little under the pointer - not
# one you only read, which would look clickable when it isn't
LIFT = ("transition duration-200 hover:-translate-y-1 hover:shadow-lg motion-reduce:transition-none "
        "motion-reduce:hover:translate-y-0")


def _title_cls() -> str:
    from soloblog.ui import TITLE_CLS
    return TITLE_CLS


def _col(s) -> str:
    """The reading column at the site's own width (Narrow or Standard) -
    for the text on a wide page."""
    from soloblog.ui import content_width
    return f"{content_width(s)} mx-auto w-full"


def _take_image(body):
    """(the first <img>, its credit html, the body without it). The image's
    figure or paragraph goes with it; its credit is kept, to show with it
    (a photo library's terms ask for one)."""
    m = re.search(r"<img\b[^>]*>", body)
    if not m:
        return "", "", body
    img = m.group(0)
    start = body.rfind("<figure", 0, m.start())
    if start >= 0 and "</figure>" not in body[start:m.start()]:
        end = body.find("</figure>", m.end())
        if end >= 0:
            figure = body[start:end + 9]
            credit = _first(r"<figcaption\b[^>]*>(.*?)</figcaption>", figure)
            credit = re.sub(r"^<figcaption\b[^>]*>|</figcaption>$", "", credit)
            return img, credit, body[:start] + body[end + 9:]
    start = body.rfind("<p>", 0, m.start())
    if start >= 0 and "</p>" not in body[start:m.start()]:
        end = body.find("</p>", m.end())
        if end >= 0 and not text_of(body[start:end + 4]):
            return img, "", body[:start] + body[end + 4:]
    return img, "", body[:m.start()] + body[m.end():]


def _take_button(body):
    """(href, label html, the body without it) for the last link in a
    section - its button - or (None, None, body). A paragraph that was
    only that link goes with it."""
    found = None
    for m in re.finditer(r'<a href="([^"]+)"[^>]*>(.*?)</a>',
                         re.sub(r"<figcaption\b.*?</figcaption>", "", body, flags=re.S), re.S):
        found = m
    if not found:
        return None, None, body
    alone = re.compile(r"<p>\s*" + re.escape(found.group(0)) + r"\s*</p>")
    rest = alone.sub("", body, count=1) if alone.search(body) else body
    return found.group(1), found.group(2), rest


def _with_class(img, cls):
    """An <img> with these classes in place of its own."""
    return re.sub(r"<img\b", f'<img class="{cls}"', re.sub(r'\sclass="[^"]*"', "", img), count=1)


# a photo credit over a card's picture, small, in its corner - a line of
# its own under the picture crowded the card's words
CREDIT_OVER = ("absolute bottom-1.5 end-2 rounded-field bg-black/45 px-1.5 py-0.5 text-xs text-white/85 "
               "[&_a]:text-white [&_a]:no-underline")


def _pictured(img, credit, cls):
    """A card's picture, its credit over its corner."""
    if not img:
        return None
    return Figure(NotStr(_with_class(img, cls)), Div(NotStr(credit), cls=CREDIT_OVER) if credit else None,
                  cls="relative")


def _card_image(img, credit, cls):
    if not img:
        return None
    # flex-col: a card's figure lays out in a row, which put the credit beside the picture
    return Figure(NotStr(_with_class(img, cls)),
                  Figcaption(NotStr(credit), cls=f"{images.CAPTION_CLS} mt-1.5") if credit else None,
                  cls="flex-col items-stretch")


def _fact_rows(pairs, skip=()):
    return [Div(Span(k, cls="text-base-content/60"), " ", Span(NotStr(v)), cls="text-sm")
            for k, v in pairs if k.lower() not in skip]


def _grid(n):
    return f"grid {ITEMS_GAP} {_PLAN_COLUMNS.get(n, 'sm:grid-cols-2 lg:grid-cols-3')}"


_LINKS_ONLY = re.compile(r"<p>((?:\s*<a\b[^>]*>.*?</a>\s*[·|,]?\s*)+)</p>|"
                         r"<ul>((?:\s*<li>\s*<a\b[^>]*>.*?</a>\s*</li>)+\s*)</ul>", re.S)


def _link_buttons(html):
    """The first paragraph or list of nothing but links, as buttons - the
    first the page's one primary action - and the html without it."""
    m = _LINKS_ONLY.search(html)
    if not m:
        return None, html
    links = re.findall(r'<a href="([^"]+)"[^>]*>(.*?)</a>', m.group(0), re.S)
    return Div(*[A(NotStr(label), href=href, cls=f"btn {'btn-primary' if i == 0 else ''}")
                 for i, (href, label) in enumerate(links)],
               cls="flex flex-wrap justify-center gap-2"), html[:m.start()] + html[m.end():]


# Sections (sections.REGISTRY): a "Section: Pricing" line under a ## shows its ### items as
# that section draws them.
# each section comes into view as it scrolls in (MOTION_JS marks it when it
# does) - not with Animations off or "reduce motion". How (Settings > Style >
# Motion) is the page's --reveal, from data-reveal: input.css [section-reveal].
# Played once on arriving, not tied to the scroll bar, which only some
# browsers can do - in the rest, sections simply sat there
SECTION_MOTIONS = {"fade": "Fade", "rise": "Rise", "zoom": "Zoom", "slide": "Slide left", "slide-right": "Slide right",
                   "alternate": "Slide both ways", "blur": "Focus", "tilt": "Tilt", "none": "None"}
_REVEAL = "reveal-item"


def _numbers(body):
    """Big figures: each ### is one ("10,000"), the words under it what it
    counts - large and free-standing, as a launch page shows them, not in
    a bordered table; two to a row on a phone."""
    intro, items = sections(body)
    n = len(items)
    # a row that wraps, each its share of the width (less the gap), the last
    # row centred - five are three and then two in the middle, not two left
    # over at the side
    width = {1: "w-full", 2: "w-[calc(50%-0.75rem)]",
             4: "w-[calc(50%-0.75rem)] sm:w-[calc(25%-1.125rem)]"}.get(
        n, "w-[calc(50%-0.75rem)] sm:w-[calc(33.333%-1rem)]")
    return Div(_prose(intro, "mb-6 text-center"),
               Div(*[Div(Div(NotStr(inner), cls="text-4xl sm:text-5xl font-extrabold tracking-tighter text-primary "
                                                 "tabular-nums leading-none", data_count_up=True),
                         Div(NotStr(re.sub(r"</?p>", "", text).strip()),
                             cls="text-sm text-base-content/70 mt-3 text-balance"),
                         cls=f"text-center min-w-0 {width}")
                     for _, inner, text in items],
                   cls="flex flex-wrap justify-center gap-x-6 gap-y-10") if items else None)


_LOGO = re.compile(r'(?:<a href="([^"]+)"[^>]*>\s*)?(<img\b[^>]*>)(?:\s*</a>)?', re.S)


def _logos(body):
    """A row of logos ("As seen in"), each its image - a link if it has one."""
    logos = [(href, img) for href, img in _LOGO.findall(body)]
    rest = _LOGO.sub("", body)
    rest = re.sub(r"<p>\s*</p>|<figure\b[^>]*>\s*(?:<figcaption\b.*?</figcaption>)?\s*</figure>", "", rest, flags=re.S)
    shown = [NotStr(_with_class(img, "h-8 sm:h-10 w-auto max-w-32 object-contain opacity-80"))
             for _, img in logos]
    # more than fit in a row drift slowly sideways instead (MOTION_JS)
    return Div(_prose(rest, "mb-6 text-center"),
               Div(*[A(img, href=href) if href else img for (href, _), img in zip(logos, shown)],
                   data_drift=True, cls="flex flex-wrap items-center justify-center gap-x-10 gap-y-6")
               if logos else None)


# ---- more sections

_EMOJI_START = re.compile(r"^\s*([^\w\s<&][^\s<]{0,7})\s+(.+)$", re.S)


def _short_grid(n):
    """Short items (a feature, a column of text) three across where cards
    would be two: a third on its own row looked left over."""
    return f"grid {ITEMS_GAP} {'sm:grid-cols-3' if n % 3 == 0 or n > 4 else 'sm:grid-cols-2' if n > 1 else ''}"


def _render_features(out, row, s, html, toc, logged_in, series):
    """A grid of short items - an icon, a title and a line or two (as
    feature grids are: three across at most, one on a phone). An item's
    icon is a line icon named on an "Icon: palette" line
    (editor_config.FEATURE_ICONS), or an emoji at the start of its heading."""
    from soloblog import editor_icons
    intro, secs = sections(html)
    items = []
    for h, inner, body in secs:
        # its first line, before the words under it (one paragraph with them)
        m = re.match(r"\s*<p>\s*Icon:\s*([\w-]+)\s*(?:<br\s*/?>|\n|(?=</p>))", body, re.I)
        named = m.group(1).lower() if m else ""
        if named in editor_icons.ICONS:
            body = "<p>" + body[m.end():]
            icon = Div(NotStr(editor_icons.SVG.format(editor_icons.ICONS[named]).replace(
                'width="18" height="18"', 'width="22" height="22"')),
                cls="size-11 rounded-box bg-primary/10 text-primary grid place-items-center mb-4 mx-auto")
            title = inner
        else:
            m = _EMOJI_START.match(inner)
            emoji, title = (m.group(1), m.group(2)) if m and not m.group(1)[0].isalnum() else (None, inner)
            icon = Div(emoji, cls="text-3xl leading-none mb-3", aria_hidden="true") if emoji else None
        # short items centred under the section's centred heading
        items.append(Div(icon, H3(NotStr(title), cls=f"{ITEM_TITLE} mb-1"),
                         _prose(body, small=True, cls="text-base-content/75"), id=_id_of(h) or None,
                         cls="text-center max-w-sm mx-auto w-full"))
    out["body"] = Div(_intro(intro, GROUP_SPACE), Div(*items, cls=_short_grid(len(items))) if items else None)


def _render_columns(out, row, s, html, toc, logged_in, series):
    """Plain columns: each ### a column, side by side where there's room,
    stacked on a phone. Nothing more - no widths, no nesting."""
    intro, secs = sections(html)
    cols = [Div(H3(NotStr(inner), cls=f"{ITEM_TITLE} mb-2"), _prose(body), id=_id_of(h) or None,
                cls="min-w-0") for h, inner, body in secs]
    out["body"] = Div(_intro(intro, GROUP_SPACE), Div(*cols, cls=_short_grid(len(cols))) if cols else None)


def _render_signup(out, row, s, html, toc, logged_in, series):
    """The newsletter's sign-up box, here - nothing when the newsletter's off."""
    from soloblog import newsletter
    out["body"] = Div(_prose(html, GROUP_SPACE), newsletter.Box(s))


def _render_contact(out, row, s, html, toc, logged_in, series):
    """The contact form, here - nothing when it's off (Settings > Comments and messages)."""
    from soloblog.routes.contact import ContactForm
    out["body"] = Div(_prose(html, GROUP_SPACE), *ContactForm(s) if s.get("contact_enabled") == "1" else ())


def _render_latest(out, row, s, html, toc, logged_in, series):
    """The newest few posts as cards - "Tag: baking" for one tag's,
    "Count: 6" for more (3 unless it says)."""
    from soloblog import posts
    from soloblog.render import format_date
    pairs, rest = facts(html)
    said = {k.lower(): text_of(v).strip() for k, v in pairs if not section_registry.is_default(text_of(v))}
    count = int(said["count"]) if said.get("count", "").isdigit() else 3
    tag = said.get("tag", "").lstrip("#").lower()
    found = [p for p in posts.list_roll_all() if p["slug"] != row["slug"]
             and (not tag or tag in [t.strip().lower() for t in (p["tags"] or "").split(",")])][:max(1, min(count, 12))]
    cards = [Div(Div(H3(A(p["title"], href=posts.url_for(p), cls="link link-hover"), cls=ITEM_TITLE),
                     Div(format_date(p["created_at"]), cls="text-xs text-base-content/60"),
                     P(posts.teaser(p), cls="text-sm text-base-content/80 line-clamp-3") if posts.teaser(p) else None,
                     cls=f"card-body {CARD_PAD} gap-1"), cls="card card-border bg-base-100")
             for p in found]
    # a card opens from anywhere on it, as a list's posts do (ROW_LINKS_JS)
    out["body"] = Div(_prose(rest, GROUP_SPACE),
                      Div(*cards, data_click_rows=True, cls=f"{_short_grid(len(cards))} [&_.card]:cursor-pointer")
                      if cards else None)


_YES = re.compile(r"<td>\s*(✓|✔|✅|yes|y)\s*</td>", re.I)
_NO = re.compile(r"<td>\s*(✗|✘|❌|×|no|n|-|—)\s*</td>", re.I)


def _render_compare(out, row, s, html, toc, logged_in, series):
    """A table of plans or options: ✓ and ✗ (or yes and no) as marks a
    screen reader says, the first column kept in view as it scrolls."""
    from html import escape
    yes = ('<td><span class="text-success text-lg" aria-hidden="true">✓</span>'
           f'<span class="sr-only">{escape(i18n.t("Yes"))}</span></td>')
    no = ('<td><span class="text-base-content/40 text-lg" aria-hidden="true">–</span>'
          f'<span class="sr-only">{escape(i18n.t("No"))}</span></td>')
    html = _NO.sub(no, _YES.sub(yes, html))
    html = html.replace("<table>", '<table class="table [&_th:first-child]:sticky [&_th:first-child]:left-0 '
                                   '[&_td:first-child]:sticky [&_td:first-child]:left-0 [&_:is(th,td):first-child]:bg-base-100 '
                                   '[&_td:first-child]:font-medium">')
    # daisyUI's table, not the writing's: it sets its own sizes and padding
    html = html.replace('<div class="overflow-x-auto [&_:is(td,th)]:min-w-28"><table',
                        '<div class="not-prose overflow-x-auto rounded-box border-[length:var(--border)] border-base-300"><table')
    out["body"] = _prose(html, "prose-table:my-0")


def _render_picture_and_text(out, row, s, html, toc, logged_in, series):
    """A picture beside its words; the words alone when there's no picture."""
    img, credit, rest = _take_image(html)
    if not img:
        out["body"] = _prose(rest)
        return
    out["body"] = Div(Div(_card_image(img, credit, f"{_FRAME} object-cover"), cls="min-w-0"),
                      _prose(rest), cls=f"grid {ITEMS_GAP} items-center @lg:grid-cols-2")


def _render_cta(out, row, s, html, toc, logged_in, series):
    """One line and a button on a card in the main colour, as a landing
    page closes. A ### first is the card's own headline. A Buttons line,
    or a paragraph of only links, gives the card a main button and quieter
    ones beside it."""
    buttons, rest = _take_buttons(html)
    head = re.match(r"\s*<h2[^>]*>(.*?)</h2>", rest, re.S)
    rest = rest[head.end():] if head else rest
    out["body"] = Div(H3(NotStr(head.group(1)), cls="text-3xl sm:text-4xl font-extrabold tracking-tighter text-balance")
                      if head else None,
                      _prose(rest, ON_PRIMARY),
                      # on the main colour: the first in the page's base colour,
                      # the rest outlined in the card's text colour
                      Div(*[A(NotStr(label), href=href, cls="btn" if i == 0 else BTN_ON_PRIMARY)
                            for i, (href, label) in enumerate(buttons)],
                          cls="mt-4 flex flex-wrap justify-center gap-2") if buttons else None,
                      cls=f"{CTA_CARD} gap-2")


def _render_numbers(out, row, s, html, toc, logged_in, series):
    out["body"] = _numbers(html)


def _render_logos(out, row, s, html, toc, logged_in, series):
    out["body"] = _logos(html)


def _render_gallery(out, row, s, html, toc, logged_in, series):
    """A gallery under its own heading: its words before the photos are
    its intro, centred with the heading."""
    first = re.search(r"<(?:div|figure)\b", html)
    if not first:
        out["body"] = _prose(html)
        return
    intro, photos = html[:first.start()], html[first.start():]
    out["body"] = Div(_intro(intro) if intro.strip() else None, _prose(photos))


def _render_hero(out, row, s, html, toc, logged_in, series):
    """A Hero, or any section with Style: Cover: its heading inside its
    picture or its words. Style: Window is a launch page's opening."""
    h, full = out["heading"].replace("<h2", f"<h2 {_NO_COPY}", 1), out.get("full", False)
    if out.get("style") == "window":
        label, html = _label_line(html)
        opening = _window_opening(_styled_heading(h, _OPENING_HEADING), label, html, s,
                                  "pt-4 sm:pt-8" if out.get("lead") else "")
        out["body"] = Div(opening, cls="px-4 sm:px-8") if full else opening
    else:
        out["body"] = _hero(h, html, s, full)


# A section in a post sits in its reading column, so its cards follow the
# width they're given - a container's - not the screen's: three pricing
# cards in a 700 px column were three slivers. The sections' own classes,
# each as its container query (spelled out whole, so Tailwind builds them)
_FIT = {"sm:grid-cols-2": "@lg:grid-cols-2", "sm:grid-cols-3": "@xl:grid-cols-3",
        "md:grid-cols-2": "@xl:grid-cols-2", "lg:grid-cols-3": "@3xl:grid-cols-3",
        "lg:grid-cols-4": "@4xl:grid-cols-4", "sm:columns-2": "@lg:columns-2",
        "sm:grid-cols-[12rem_1fr]": "@lg:grid-cols-[12rem_1fr]", "sm:row-start-2": "@lg:row-start-2",
        "sm:stats-horizontal": "@lg:stats-horizontal"}
_FIT_RE = re.compile(r"(?<![\w:@\[-])(" + "|".join(re.escape(k) for k in _FIT) + r")(?![\w\[-])")


def _fitted(el) -> str:
    """A section's html, its columns following its container."""
    return _FIT_RE.sub(lambda m: _FIT[m.group(1)], to_xml(el)) if el is not None else ""


_H2_TAG = re.compile(r"<(/?)h2\b([^>]*)>")


def _items_as_h3(html: str, own_id: str = "") -> str:
    """A section's html, every heading in it an <h3>: the page's <h2> is
    the section's own title (kept by its id where the section draws it
    itself), so readers and screen readers get one outline on every page."""
    keep = False

    def swap(m):
        nonlocal keep
        if not m.group(1):
            keep = bool(own_id) and f'id="{own_id}"' in m.group(2)
        return m.group(0) if keep else f"<{m.group(1)}h3{m.group(2)}>"
    return _H2_TAG.sub(swap, html)


# what a section returns when it has nothing for a reader (a series' contents
# with no series): neither it nor its heading is shown
NOTHING = object()


def _section_content(kind, text, row, s, toc, logged_in, series, out, heading="", **given):
    """What a section shows in a post's column - its heading is the post's
    own ##, above it, unless the kind draws its own (heading is that ##).
    Every kind is drawn by its own function, named in sections.REGISTRY."""
    # each reads its ### items as ##s (pages.sections splits on those);
    # _items_as_h3 gives the page its <h3>s back
    part = {"body": None, "ld": [], "wide": False, "before": None, "heading": heading, **given}
    globals()[section_registry.REGISTRY[kind]["draw"]](part, row, s, re.sub(r"<(/?)h3\b", r"<\1h2", text), toc,
                                                      logged_in, series)
    if part.get("nothing"):
        return NOTHING
    # search engines hear of it once: render() drops a repeat
    out["ld"].extend(part["ld"])
    # a business page's contact details and hours are what it tells search engines
    out.setdefault("business", {}).update(part.get("business") or {})
    return part["body"]


def _styled_heading(h, cls):
    """A section's ## with these classes - its id kept, so the contents link to it."""
    return NotStr(re.sub(r"^<h2", f'<h2 class="{cls}"', h.strip(), count=1))


def _label_line(text):
    """(the "Label: Free and open source" line of a window opening, the
    html without it) - as written, not lower case."""
    pairs, rest = facts(text)
    return next((v for k, v in pairs if k.lower() == "label"), ""), rest


def _hero(h, text, s, full):
    """A big heading, a line and a button over a picture - on a dark layer,
    so white words read on any photo (WCAG 1.4.3), as a full-screen cover's
    do. Without a picture, the same on the page's quieter tone."""
    img, credit, rest = _take_image(text)
    buttons, rest = _take_buttons(rest)
    heading = re.sub(r"^<h2", '<h2 class="text-3xl sm:text-5xl font-bold leading-tight text-balance m-0"', h.strip(), count=1)
    # over a photo, the words white whatever the theme (daisyUI sets prose's colours)
    line = Div(NotStr(rest), cls=f"text-lg sm:text-xl [&_p]:m-0 [&_p+p]:mt-2 "
                                 f"{'text-white/90 [&_a]:text-white [&_a]:underline' if img else 'text-base-content/80'}")
    words = Div(NotStr(heading), line if text_of(rest) else None,
                Div(*[A(NotStr(label), href=href,
                        cls="btn btn-primary" if i == 0 else BTN_ON_PHOTO if img else "btn btn-outline")
                      for i, (href, label) in enumerate(buttons)],
                    cls="mt-1 flex flex-wrap gap-2") if buttons else None,
                cls=f"relative z-10 flex flex-col gap-3 py-10 sm:py-14 px-6 sm:px-10 {_col(s) if full else ''} "
                    f"{'text-white' if img else ''}")
    if not img:
        return Div(words, cls=f"bg-base-content/5 flex items-center min-h-[18rem] {'' if full else 'rounded-box'}")
    return Div(NotStr(_with_class(img, "absolute inset-0 w-full h-full object-cover")),
               Div(cls="absolute inset-0 bg-gradient-to-t from-black/85 via-black/45 to-black/15"),
               words,
               Div(NotStr(credit), cls=images.CAPTION_OVER_CLS) if credit else None,
               # full width it's square-cornered - but rounded again in the column beside a side panel
               cls=f"relative overflow-hidden flex items-end "
                   f"min-h-[24rem] sm:min-h-[30rem] "
                   f"{'[html[data-side-beside]_&]:rounded-box' if full else 'rounded-box'}")


def _render_bento(out, row, s, html, toc, logged_in, series):
    """Tiles of different sizes in one grid - the first big, the rest
    around it; one column on a phone, the big one first."""
    intro, secs = sections(html)
    tiles = []
    for i, (h, inner, body) in enumerate(secs):
        img, credit, rest = _take_image(body)
        href, label, rest = _take_button(rest)
        big = i == 0
        tiles.append(Div(
            Figure(NotStr(_with_class(img, _SCROLL_PICTURE)),
                   cls=f"overflow-hidden {'h-48 @lg:h-auto @lg:flex-1' if big else 'h-36'}") if img else None,
            Div(H3(NotStr(inner), cls=LEAD_TITLE if big else ITEM_TITLE),
                _prose(rest, small=not big),
                A(NotStr(label), href=href, cls="btn btn-sm self-start mt-1") if href else None,
                cls=f"{CARD_PAD} flex flex-col gap-2"),
            id=_id_of(h) or None,
            cls=f"card card-border bg-base-100 overflow-hidden flex flex-col {'@lg:col-span-2 @lg:row-span-2' if big else ''} "
                f"{LIFT if href else ''}"))
    out["body"] = Div(_intro(intro, GROUP_SPACE),
                      Div(Div(*tiles, cls=f"grid {TIGHT_GAP} @lg:grid-cols-2 @3xl:grid-cols-4 @lg:auto-rows-[minmax(11rem,auto)]"),
                          cls="@container") if tiles else None)


# a section's own width in a post's column: Width: Wide or Full, or its kind's
_WIDTHS = ("wide", "full")
# ...but in the column while a side panel sits in the margin it'd spread
# over (contents, tags - placeSidePanels sets data-beside)
_IN_COLUMN_BESIDE = ("[html[data-side-beside]_&]:w-auto "
                     "[html[data-side-beside]_&]:mx-0 "
                     "[html[data-side-beside]_&]:px-0")


def _wider(html, width, s):
    from soloblog.ui import Breakout
    return to_xml(Breakout(NotStr(html), width, s)).replace('class="w-screen', f'class="{_IN_COLUMN_BESIDE} w-screen', 1)


_UNFOLDED = "<div data-fold-break>"

# A story's heading, held under the site's header while the story is live and
# wide (MOTION_JS marks the wrapper live with its story), with the held picture right
# under it: MOTION_JS measures the gap the page has under a heading (--story-gap), how far
# down the pair sits to be centred on a tall window (--story-shift), how far in the
# heading - as wide as its words - starts to be centred across the story (--story-head-x),
# and where the picture is held (--story-top), and marks the wrapper data-held. A sticky box
# stays inside its parent until the parent ends, and the story's picture is let go a
# window's height before that, so the heading's margin is that much deeper and the story's
# (_STORY_BODY) pulls back by the same - the two let go at the same moment, and the gap
# between them is the page's own.
_STORY_HEAD = ("@5xl:group-data-[live]/sw:sticky @5xl:group-data-[live]/sw:top-[calc(var(--header-h,0px)+var(--story-shift,0px))] "
               "@5xl:group-data-[live]/sw:z-20 @5xl:group-data-[live]/sw:bg-base-200 "
               "@5xl:group-data-[held]/sw:w-fit @5xl:group-data-[held]/sw:ms-(--story-head-x)! "
               "@5xl:group-data-[held]/sw:mb-[calc(var(--story-pic-h,calc(100svh-var(--story-top)-var(--footer-h,0px)))+var(--story-gap))]!")
_STORY_BODY = "@5xl:group-data-[held]/sw:mt-[calc(0px-var(--story-pic-h,calc(100svh-var(--story-top)-var(--footer-h,0px))))]! "
_STORY_WRAP = "group/sw @container"


def place_sections(row, s, html, toc, logged_in, series, out):
    """Sections in any post or page (a ## with a "Section:" line), drawn
    where they were written. The html with them in."""
    intro, secs = sections(html)
    found = [section_registry.section_kind(body) for _, _, body in secs]
    if not any(found):
        return html
    kept = [intro]
    # a page with writing of its own (a plain ##) reads as one post: its
    # sections sit as close as headings, one after another too. The page's
    # gap between sections is for a page made of them
    writing_page = any(not kind_text for kind_text in found)
    page_motion = section_motion(row, s)
    drawn = 0
    # (where in kept, where its outer <div> starts) of a section that's
    # last so far - None once plain writing follows it
    last = None
    for (h, _, body), kind_text in zip(secs, found):
        if not kind_text:
            kept.append(h + body)
            last = None if (h + body).strip() else last
            continue
        kind, text = kind_text
        # the first thing on the page has no gap above it
        lead = not "".join(kept).strip()
        # plain writing above it, or on the page: it follows on as a heading does
        after_words = not lead and (last is None or writing_page)
        width, text = section_registry.section_width(text)
        # Style: Cover is a hero (on the kinds that take it), Style: Card sets it apart
        style, text = section_registry.take_line(text, "style")
        heading_line, text = section_registry.take_line(text, "heading")
        space_line, text = section_registry.take_line(text, "space")
        appear_line, text = section_registry.take_line(text, "appear")
        if style == "cover":
            # only where words over a picture means something; elsewhere it's ignored
            if section_registry.REGISTRY[kind]["cover"]:
                kind = "hero"
            else:
                style = ""
        # Heading: its own, else the site's - the ## and its intro, not the items
        picked = section_registry.pick("Heading", heading_line)
        centred = (picked or s.get("section_heading_align")) == "centre"
        # a section's own Width: first, then the kind's, then a wide page's
        width = width if width in _WIDTHS else "" if width == "column" else \
            section_registry.REGISTRY[kind]["width"] or ("wide" if is_wide(row) else "")
        # Space: and Appear: its own, else the page's, else the site's (the
        # page's --space and data-reveal carry the site's)
        room = section_registry.pick("Space", space_line)
        # the gap that starts a section drawing its own heading
        apart = SECTION_GAP if lead or (after_words and not room) else SECTION_APART
        motion = section_registry.pick("Appear", appear_line) or page_motion
        if motion == "alternate" and kind != "portfolio":
            # Photos' tiles alternate among themselves (input.css, section-reveal)
            motion = "slide" if drawn % 2 == 0 else "slide-right"
        drawn += 1
        if width:
            # view_post then keeps the margins free: contents on top, panels under
            out["has_wide_section"] = True
        # Photos' tiles come in one by one, so the section itself holds still
        look = f'{SECTION_ROOM.get(room, "")} {"" if kind == "portfolio" else _REVEAL}'.strip()
        appear = f'data-reveal="{motion}"'
        if kind == "hero":
            # its heading is inside its picture, or its words
            hero = to_xml(_section_content(kind, text, row, s, toc, logged_in, series, out, h, style=style,
                                           full=width == "full", lead=lead))
            hero = f'<div class="{apart} {look}" data-section="hero" {appear}>{hero}</div>'
            if width:
                hero = _wider(hero, width, s)
            kept.append(hero.replace("<div", "<div data-fold-break", 1))
            last = (len(kept) - 1, 0)
            continue
        own = section_registry.REGISTRY[kind]["own_heading"]
        content = _section_content(kind, text, row, s, toc, logged_in, series, out, h if own else "")
        if content is NOTHING:
            out.setdefault("dropped", []).append(_id_of(h))
            continue
        block = _items_as_h3(_fitted(content), _id_of(h) if own else "")
        if kind == "story":
            block = block.replace(_STORY_CAP, _STORY_CAPS.get(width, _STORY_CAP))
        if style == "card":
            # a Story's fade ends in the card's own colour, not the page's (_STORY_CARD_FADE)
            story_card = {"data_story_card": True} if kind == "story" else {}
            block = to_xml(Div(NotStr(block), **story_card, cls=(
                f"card border border-base-content/10 bg-base-content/4 {PANEL_PAD}"
                + (f" {_STORY_CARD_FADE}" if story_card else ""))))
        # a lone card (one product, one person) at a card's width - across
        # the column, its photo filled the screen
        own_cls = f"{INTRO_CENTRED} " if centred and not own else ""
        # a section that draws its own heading starts itself; otherwise the
        # ## above it does
        space_cls = apart if own else SECTION_GAP
        inside = (f'<div class="@container {SECTION_ENDS} {own_cls}{_STORY_BODY if kind == "story" else ""}{space_cls} {look} '
                  f'[&_.grid>:only-child]:max-w-sm" data-section="{kind}" {appear}>{block}</div>')
        if width and not own:
            # wider than the column, its heading goes with it - left in the
            # column, it sat apart from the words and pictures under it
            holds = kind == "story"
            head = to_xml(_prose(_appearing(_section_heading(h, centred, room, lead, after_words), motion),
                                 ("px-4 sm:px-8 " if width == "full" else "") + (_STORY_HEAD if holds else "")))
            if holds:
                head = head.replace("<div", "<div data-story-head", 1)
                head, inside = f'<div class="{_STORY_WRAP}" data-story-wrap>{head}', f"{inside}</div>"
            kept.append(_wider(head + inside, width, s).replace("<div", "<div data-fold-break", 1))
            last = (len(kept) - 1, 0)
            continue
        if width:
            inside = _wider(inside, width, s)
        if own:
            # it draws its heading itself, and starts a new part of the page as a Hero does
            kept.append(inside.replace("<div", "<div data-fold-break", 1))
            last = (len(kept) - 1, 0)
        else:
            # its heading stays the post's own: in the contents, with its
            # link - and, as every section, it never folds: only plain
            # writing under a ## does
            heading = _appearing(_section_heading(h, centred, room, lead, after_words), motion)
            opener = _UNFOLDED
            # the page's writing is beside the section, not around it: its
            # heading has a text styling of its own - held as a wide
            # story's is, by the box around it
            heading = to_xml(_prose(heading, _STORY_HEAD if kind == "story" else ""))
            if kind == "story":
                heading = heading.replace("<div", "<div data-story-head", 1)
                opener = f'<div data-fold-break class="{_STORY_WRAP}" data-story-wrap>'
            kept.append(f"{opener}{heading}{inside}</div>")
            last = (len(kept) - 1, len(opener) + len(heading))
    if last:
        at, start = last
        kept[at] = kept[at][:start] + kept[at][start:].replace('class="', f'class="{SECTION_LAST} ', 1)
    return "".join(kept)


def _take_buttons(body):
    """[(href, label html)] and the body without them: a Buttons line's,
    or a paragraph of only links - an opening's "Try the demo · Get
    started" - in the order written; otherwise the last link alone, as
    _take_button."""
    row = re.search(r'<div class="not-prose flex flex-wrap gap-2 my-6">(.*?)</div>', body, re.S)
    if row:
        return (re.findall(r'<a href="([^"]+)"[^>]*>(.*?)</a>', row.group(1), re.S),
                body[:row.start()] + body[row.end():])
    for m in re.finditer(r"<p>(.*?)</p>", body, re.S):
        links = re.findall(r'<a href="([^"]+)"[^>]*>(.*?)</a>', m.group(1), re.S)
        left = re.sub(r'<a href="[^"]+"[^>]*>.*?</a>|<strong>|</strong>|[\s·|]', "", m.group(1), flags=re.S)
        if len(links) > 1 and not left:
            return links, body[:m.start()] + body[m.end():]
    href, label, rest = _take_button(body)
    return ([(href, label)] if href else []), rest


# a picture as a product's own window: a thin edge, a deep soft shadow,
# and a glow of the site's main colour behind it
_FRAME = f"w-full rounded-box border border-base-content/10 {SHADOW_RAISED}"
# within the screen on a phone, out past the picture where there's room:
# the main colour on one side and the second on the other, as two soft lights
_GLOWS = (Div(cls="pointer-events-none absolute left-0 sm:-left-16 top-0 h-3/4 w-2/3 rounded-full bg-primary/25 "
                  "blur-3xl"),
          Div(cls="pointer-events-none absolute right-0 sm:-right-16 bottom-0 h-3/4 w-2/3 rounded-full "
                  "bg-secondary/20 blur-3xl"))
# light catching the opening picture as the mouse moves over it (MOTION_JS
# sets where): white whatever the palette - it's a glare on glass, not a
# colour of the page - and only with Animations on and no "reduce motion"
_SHEEN = ("pointer-events-none absolute inset-0 rounded-box opacity-0 transition-opacity duration-300 mix-blend-overlay "
          "bg-[radial-gradient(circle_at_var(--sheen-x,50%)_var(--sheen-y,30%),rgb(255_255_255/0.5),transparent_55%)] "
          "motion-safe:[html[data-animate]_[data-tilt]:hover>&]:opacity-100")
_CHECK = ('<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" '
          'stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" '
          'aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>')


# a launch page's opening, whether the page's title or a section's heading is its big words
_OPENING_HEADING = "text-5xl sm:text-7xl font-extrabold tracking-tighter leading-[1.02] text-balance"


def _window_opening(heading, label, intro, s, top):
    """The opening of a launch page: a small label, the big heading, a
    line, its buttons (a paragraph of links is a main one and quieter
    ones), a short list as small points in a row, and its first picture
    framed as the product's window under them."""
    buttons, intro_text = _take_buttons(intro)
    shot, shot_credit, intro_text = _take_image(intro_text)
    # a short list in the opening: its points, small, in a row under the buttons
    points = re.search(r"<ul>(.*?)</ul>", intro_text, re.S)
    if points:
        intro_text = intro_text[:points.start()] + intro_text[points.end():]
        points = re.findall(r"<li>(.*?)</li>", points.group(1), re.S)
    hero = Div(
        Span(NotStr(label), cls="badge badge-soft badge-primary mb-6") if label else None,
        heading,
        _prose(intro_text, "prose-base sm:prose-xl text-base-content/75 mx-auto max-w-2xl mt-6 [&_p]:my-2 text-balance"),
        Div(*[A(NotStr(text), href=link, cls=f"btn btn-lg {'btn-primary' if i == 0 else 'btn-ghost'}")
              for i, (link, text) in enumerate(buttons)], cls="flex flex-wrap justify-center gap-3 mt-9")
        if buttons else None,
        Ul(*[Li(Span(NotStr(_CHECK), cls="text-primary"), NotStr(p), cls="flex items-center gap-1.5")
             for p in points], cls="flex flex-wrap justify-center gap-x-6 gap-y-2 mt-6 text-sm text-base-content/70")
        if points else None,
        cls=f"{_col(s)} text-center {top}")
    # the product's window wider than the words above it, as a launch page
    # shows it - told so, the browser fetches a sharp enough copy
    if shot:
        # the first thing anyone sees: fetched first, not when its turn comes
        shot = re.sub(r'\s(?:loading|fetchpriority)="[^"]*"', "", shot)
        shot = re.sub(r'\bsizes="[^"]*"', 'sizes="(min-width: 64rem) 64rem, 100vw"', shot).replace(
            "<img ", '<img fetchpriority="high" ', 1)
    picture = Div(*_GLOWS, Div(_card_image(shot, shot_credit, _FRAME), Div(cls=_SHEEN), cls="relative", data_tilt=True),
                  cls="relative max-w-5xl mx-auto w-full mt-14 sm:mt-16") if shot else None
    return Div(hero, picture, cls="pb-6")


PICTURE_LEFT = "lg:grid-cols-[3fr_2fr]"
PICTURE_RIGHT = "lg:grid-cols-[2fr_3fr]"
# the picture's width in that row, at its Width (Wide is the row itself);
# side by side from a laptop's width - narrower, it's above its words
PICTURE_SIZES = {"": "(min-width: 1800px) 58rem, (min-width: 1024px) 46rem, 100vw",
                 "column": "(min-width: 1024px) 28rem, 100vw", "full": "(min-width: 1024px) 60vw, 100vw"}


def _render_services(out, row, s, html, toc, logged_in, series):
    """A freelancer's offer: each ## with a "From:" (or "Price:") line is a
    service card; a ## that's a numbered list is the steps of how it
    works; anything else stays text."""
    intro, secs = sections(html)
    blocks, cards = [_intro(intro)], []

    def flush():
        if cards:
            blocks.append(Div(*cards, cls=f"{_grid(min(len(cards), 2))} {GROUP_SPACE}"))
            cards.clear()
    for h, inner, body in secs:
        pairs, rest = facts(body.strip())
        price = next((v for k, v in pairs if k.lower() in ("from", "price", "starts at", "starting at")), None)
        if price is not None:
            href, label, rest = _take_button(rest)
            cards.append(Div(Div(
                H3(NotStr(inner), cls=ITEM_TITLE),
                *_fact_rows(pairs),
                _prose(rest, small=True),
                Div(A(NotStr(label), href=href, cls="btn btn-sm"), cls="card-actions mt-auto pt-3") if href else None,
                cls=f"card-body {CARD_PAD} gap-2"), id=_id_of(h) or None, cls="card card-border bg-base-100"))
            continue
        flush()
        steps = re.fullmatch(r"\s*<ol>(.*)</ol>\s*", body, re.S)
        if steps:
            blocks.append(Section(H3(NotStr(inner), cls=f"{ITEM_TITLE} mb-3"), _steps(steps.group(1)),
                                  id=_id_of(h) or None, cls="mb-8"))
        else:
            blocks.append(Section(H3(NotStr(inner), cls=f"{ITEM_TITLE} mb-2"), _prose(body),
                                  id=_id_of(h) or None, cls="mb-8"))
    flush()
    out["body"] = Div(*blocks)


def _render_testimonials(out, row, s, html, toc, logged_in, series):
    """Kind words: each ## is a person - their quote, a "Role:" line and
    an optional photo - as a grid of quote cards."""
    intro, secs = sections(html)
    cards = []
    for h, inner, body in secs:
        img, credit, rest = _take_image(body)
        pairs, rest = facts(rest.strip())
        role = next((v for k, v in pairs if k.lower() in ("role", "who", "from", "company")), None)
        quote = re.sub(r"</?blockquote>", "", rest).strip()
        cards.append(Figure(
            Div(NotStr("“"), cls="text-6xl leading-[0.6] text-primary/50 font-serif h-6", aria_hidden="true"),
            # the words are the point: larger than the name under them, as a quote set apart
            _prose(quote, "text-base-content [&_p]:my-1 [&_p]:text-lg sm:[&_p]:text-xl [&_p]:leading-relaxed"),
            Div(Div(Div(NotStr(_with_class(img, "object-cover")), cls="w-10 rounded-full"),
                    cls="avatar shrink-0") if img else None,
                Div(Div(NotStr(inner), cls="font-semibold text-sm"),
                    Div(NotStr(role), cls="text-xs text-base-content/60") if role else None,
                    Div(NotStr(credit), cls="text-xs text-base-content/50") if credit else None),
                cls="flex items-center gap-3 mt-3"),
            id=_id_of(h) or None,
            cls=f"card card-border bg-base-100 {CARD_PAD}"))
    out["body"] = Div(_intro(intro), Div(*cards, cls=_grid(min(len(cards), 2))) if cards else None)


# Photo story: its own grid - a narrow column for each
# ##'s heading beside a reading column for its words, pictures out across
# both and wider
_SPREAD = "max-w-6xl mx-auto w-full"
_SPREAD_TEXT = "grid gap-x-12 gap-y-3 lg:grid-cols-[13rem_minmax(0,1fr)]"
_SPREAD_WIDE = ("max-w-7xl mx-auto w-full min-[1800px]:max-w-none min-[1800px]:w-[100rem] "
                "min-[1800px]:mx-[calc(50%-50rem)]")
# A photo story's classes, written out whole as Tailwind needs. On a page of
# its own they follow the screen's width; as a section, its container's - a
# column of writing isn't a wide screen.
_STORY_PAGE = {
    "spread": _SPREAD, "wide": _SPREAD_WIDE, "text": _SPREAD_TEXT,
    "gap": "gap-[calc(3rem*var(--space,1))] sm:gap-[calc(5rem*var(--space,1))]",
    "lede": "prose-lg sm:prose-2xl", "quote": "py-4 sm:py-8", "quote_text": "text-2xl sm:text-4xl",
    "beside": "grid gap-8 lg:gap-16 items-center", "left": PICTURE_LEFT,
    "right": f"{PICTURE_RIGHT} lg:[&>*:first-child]:order-2",
    "three": "grid gap-4 sm:gap-6 sm:grid-cols-3 sm:grid-rows-2", "first": "sm:col-span-2 sm:row-span-2",
    "rows": "flex flex-col gap-4 sm:gap-6", "row": "flex flex-col sm:flex-row gap-4 sm:gap-6 items-start"}
_STORY_SECTION = {
    "spread": "w-full", "wide": "w-full",
    "text": "grid gap-x-8 gap-y-3 @3xl:grid-cols-[10rem_minmax(0,1fr)]",
    "gap": "gap-10 @3xl:gap-14",
    "lede": "prose-lg @xl:prose-xl", "quote": "py-2 @xl:py-6", "quote_text": "text-2xl @xl:text-3xl",
    "beside": "grid gap-8 @3xl:gap-12 items-center", "left": "@3xl:grid-cols-[3fr_2fr]",
    "right": "@3xl:grid-cols-[2fr_3fr] @3xl:[&>*:first-child]:order-2",
    "three": "grid gap-4 @xl:gap-6 @xl:grid-cols-3 @xl:grid-rows-2", "first": "@xl:col-span-2 @xl:row-span-2",
    "rows": "flex flex-col gap-4 @xl:gap-6", "row": "flex flex-col @xl:flex-row gap-4 @xl:gap-6 items-start"}
_VOID = {"img", "br", "hr", "input", "source", "meta", "link", "wbr", "col", "area", "track"}
_TAG = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)\b[^>]*?(/?)>")


def top_blocks(html: str) -> list:
    """The html's top-level elements, in order, each whole."""
    blocks, depth, start = [], 0, None
    for m in _TAG.finditer(html):
        closing, name, selfclosing = m.group(1), m.group(2).lower(), m.group(3)
        if depth == 0 and not closing:
            start = m.start()
        if name in _VOID or selfclosing:
            if depth == 0:
                blocks.append(html[start:m.end()])
            continue
        depth += -1 if closing else 1
        if depth == 0 and start is not None:
            blocks.append(html[start:m.end()])
            start = None
        depth = max(depth, 0)
    return blocks


def _pictures_of(block):
    """[(img, caption html)] for a block that's nothing but pictures - a
    figure, or a paragraph of one or more - else None."""
    if 'class="gallery' in block or text_of(re.sub(r"<figcaption\b.*?</figcaption>", "", block, flags=re.S)).strip():
        return None
    found = re.findall(r"<img\b[^>]*>", block)
    if not found or not re.match(r"<(figure|p)\b", block):
        return None
    caption = _first(r"<figcaption\b[^>]*>(.*?)</figcaption>", block)
    caption = re.sub(r"^<figcaption\b[^>]*>|</figcaption>$", "", caption)
    return [(img, caption if len(found) == 1 else "") for img in found]


def _spread_picture(img, caption, sizes, cls="", img_cls="w-full h-auto rounded-box"):
    img = re.sub(r'\bsizes="[^"]*"', f'sizes="{sizes}"', img)
    return Figure(NotStr(_with_class(img, img_cls)),
                  Figcaption(NotStr(caption), cls="mt-3 text-xs sm:text-sm text-base-content/60 text-left "
                                                  "[&_a]:underline") if caption else None,
                  cls=f"m-0 {cls}")


def _shape(img) -> float:
    from soloblog.gallery import ratio
    src = re.search(r'src="(/uploads/[^"?]+)"', img)
    return ratio(unescape(src.group(1))) if src else 1.5


def _pictures_row(pics, c=_STORY_PAGE):
    """Pictures written one after another, side by side and the same
    height, none of them cut - each as wide as its shape asks; three as
    one large and two beside it; more, two to a row."""
    if len(pics) == 3:
        (first, cap), *rest = pics
        fill = "w-full h-full object-cover rounded-box"
        return Div(_spread_picture(first, cap, "(min-width: 640px) 56rem, 100vw", c["first"], fill),
                   *[_spread_picture(i, cap, "(min-width: 640px) 28rem, 100vw", "", fill) for i, cap in rest],
                   cls=f"{c['wide']} {c['three']}")
    rows = [pics[n:n + 2] for n in range(0, len(pics), 2)]
    return Div(*[Div(*[Div(_spread_picture(i, cap, "(min-width: 640px) 40rem, 100vw"), cls="min-w-0",
                           style=f"flex: {_shape(i):.3f} 1 0%") for i, cap in row],
                     cls=c["row"]) for row in rows],
               cls=f"{c['wide']} {c['rows']}")


def _pull_quote(block, text_cls="text-2xl sm:text-4xl"):
    """A quote, big across the page - its last line, when it starts with
    a dash, the person who said it."""
    inner = re.sub(r"^<blockquote\b[^>]*>|</blockquote>$", "", block.strip())
    paras = re.findall(r"<p>(.*?)</p>", inner, re.S) or [inner]
    who = None
    if len(paras) > 1 and re.match(r"\s*(—|–|-)\s", text_of(paras[-1])):
        who = re.sub(r"^\s*(—|–|-)\s*", "", paras.pop())
    return Figure(
        Div("“", cls="text-primary text-7xl sm:text-8xl leading-none font-serif h-12 sm:h-14", aria_hidden="true"),
        NotStr(f"<blockquote class=\"{text_cls} font-semibold tracking-tight leading-snug text-balance "
               "m-0 [&_p]:m-0 [&_p+p]:mt-4\">" + "".join(f"<p>{p}</p>" for p in paras) + "</blockquote>"),
        Figcaption(NotStr(who), cls="mt-6 text-sm text-base-content/60") if who else None,
        cls="max-w-4xl mx-auto text-center m-0")


def _facts_cells(pairs):
    """Each "Key: value" as a small label over its value, for a strip of facts."""
    return [Div(Div(k, cls="text-xs uppercase tracking-widest text-base-content/50"),
                Div(NotStr(v), cls="mt-1 font-medium [&_a]:link"), cls="min-w-0")
            for k, v in pairs]


def _story_rows(rest, c, big=True, together=True, beside=True):
    """The rows of a story in pictures, laid out like a magazine - each
    ##'s heading beside its words, and the pictures placed by how they're
    written: one alone wide, a few in a row side by side, one with a short
    paragraph after it beside that paragraph; a quote is a pull quote and
    the opening paragraph is large. c: the classes (_STORY_PAGE or
    _STORY_SECTION). big, together and beside turn the opening paragraph,
    the row of pictures and the paragraph beside a picture off."""
    blocks = top_blocks(rest)
    rows, text, heading, side = [], [], None, 0

    def flush():
        nonlocal text, heading
        if text or heading:
            rows.append(Div(Div(NotStr(heading or ""), cls="lg:pt-1.5 [&_h2]:m-0 [&_h2]:text-sm [&_h2]:uppercase "
                                                           "[&_h2]:tracking-widest [&_h2]:text-base-content/60"),
                            _prose("".join(text), "max-w-2xl min-w-0") if text else Div(),
                            cls=f"{c['spread']} {c['text']}"))
        text, heading = [], None

    lede = big
    n = 0
    while n < len(blocks):
        block = blocks[n]
        pics = _pictures_of(block)
        if pics:
            # lines of pictures together are a row; pictures alone one after
            # another, with nothing between them, are one too
            if together and len(pics) == 1:
                while n + 1 < len(blocks) and len(_pictures_of(blocks[n + 1]) or []) == 1:
                    n += 1
                    pics += _pictures_of(blocks[n])
            following = blocks[n + 1] if n + 1 < len(blocks) else ""
            after = blocks[n + 2] if n + 2 < len(blocks) else ""
            flush()
            lede = False
            if (beside and len(pics) == 1 and following.startswith("<p>") and not _pictures_of(following)
                    and len(text_of(following)) <= 320 and not after.startswith("<p>")):
                # a short paragraph straight after a picture: beside it, sides taking turns
                img, cap = pics[0]
                rows.append(Div(Div(_spread_picture(img, cap, PICTURE_SIZES[""]), cls="min-w-0"),
                                _prose(following, "min-w-0 max-w-md prose-lg"),
                                cls=f"{c['wide']} {c['beside']} " + (c["right"] if side % 2 else c["left"])))
                side += 1
                n += 2
                continue
            if len(pics) == 1 or not together:
                rows.extend(Div(_spread_picture(img, cap, "(min-width: 80rem) 80rem, 100vw"), cls=c["wide"])
                            for img, cap in pics)
            else:
                rows.append(_pictures_row(pics, c))
            n += 1
            continue
        if block.startswith("<blockquote"):
            flush()
            rows.append(Div(_pull_quote(block, c["quote_text"]), cls=c["quote"]))
        elif block.startswith("<h2"):
            flush()
            heading = block
        elif block.startswith("<p>") and lede and not heading:
            # the opening paragraph, large, as a magazine's standfirst
            rows.append(Div(Div(), _prose(block, f"max-w-3xl min-w-0 {c['lede']} text-base-content/80 "
                                                 "[&_p]:my-0 leading-snug"), cls=f"{c['spread']} {c['text']}"))
            lede = False
        elif 'class="gallery' in block[:200] or 'data-section=' in block[:300] or block.startswith("<div"):
            # a gallery or a section: out across the page
            flush()
            rows.append(Div(_prose(block, "max-w-none"), cls=c["spread"]))
        else:
            lede = False
            text.append(block)
        n += 1
    flush()
    return rows


def next_in_portfolio(row, labels):
    """The pages before and after this one among those with the same
    first tag, newest first as on the tag's page - as large pictures to go
    on to, round from the last to the first. Just the next where there are
    only two. None without a tag, or alone in it. labels - what the two
    are called."""
    from soloblog import posts
    tags = posts.split_tags(row["tags"])
    if not tags:
        return None
    mine = posts.url_for(row)
    first = tags[0].lower()
    hrefs = [posts.url_for(p) for p in posts.list_tagged(first)
             if posts.split_tags(p["tags"])[0].lower() == first and not posts.is_protected(p)]
    if mine not in hrefs or len(hrefs) < 2:
        return None
    return _next_cards(hrefs, mine, labels)


def _next_cards(hrefs, mine, labels):
    at = hrefs.index(mine)
    ways = [(labels[0], hrefs[at - 1]), (labels[1], hrefs[(at + 1) % len(hrefs)])]
    if ways[0][1] == ways[1][1]:
        ways = ways[1:]
    cards = [_project_card(label, href, last=i == len(ways) - 1 and len(ways) == 2, big=len(ways) == 1)
             for i, (label, href) in enumerate(ways)]
    return Div(*cards, cls=f"{_SPREAD} grid gap-4 sm:gap-6 {'sm:grid-cols-2' if len(cards) == 2 else ''} mt-4 sm:mt-8")


def _live_post(href):
    from soloblog import posts
    found = posts.get_post(href.rstrip("/").rsplit("/", 1)[-1])
    # by its own address - "/series/the-peugeot" isn't a post called the-peugeot
    return found if found and posts.is_live(found) and href.rstrip("/") in (
        posts.url_for(found), f"/post/{found['slug']}") else None


def _project_card(label, href, last=False, big=False):
    """A project to go on to: its picture, with what it is and its title over it."""
    found = _live_post(href)
    cover = found["cover_image"]
    words = Div(Div(label, cls="text-xs uppercase tracking-widest opacity-80"),
                Div(found["title"], cls="mt-2 font-extrabold tracking-tighter text-balance "
                    + ("text-3xl sm:text-5xl" if big else "text-2xl sm:text-4xl")),
                cls=f"relative z-10 p-6 sm:p-10 {'text-white' if cover else ''} {'sm:text-end' if last else ''}")
    tall = "min-h-[20rem] sm:min-h-[28rem]" if big else "min-h-[16rem] sm:min-h-[22rem]"
    return A(Img(**images.responsive(cover, "(min-width: 72rem) 72rem, 100vw" if big else "(min-width: 40rem) 36rem, 100vw"),
                 alt="", loading="lazy", cls=f"absolute inset-0 w-full h-full object-cover {_ZOOM}") if cover else None,
             Div(cls="absolute inset-0 bg-gradient-to-t from-black/80 via-black/30 to-transparent") if cover else None,
             words, href=href,
             cls=f"group relative overflow-hidden rounded-box flex items-end no-underline "
                 f"{'sm:justify-end' if last else ''} {tall if cover else 'bg-base-content/5 min-h-48'}")


_MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov",
                                       "dec"], 1)}


def event_date(text: str):
    """"12 March 2026", "March 12, 2026", "2026-03-12" -> a date, or None -
    to tell the events to come from the past ones."""
    from datetime import date
    t = text.strip().lower()
    m = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", t)
    try:
        if m:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        m = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([a-z]{3})[a-z]*\.?,?\s+(\d{4})\b", t)
        if m and m.group(2) in _MONTHS:
            return date(int(m.group(3)), _MONTHS[m.group(2)], int(m.group(1)))
        m = re.search(r"\b([a-z]{3})[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b", t)
        if m and m.group(1) in _MONTHS:
            return date(int(m.group(3)), _MONTHS[m.group(1)], int(m.group(2)))
    except ValueError:
        return None
    return None


def _render_events(out, row, s, html, toc, logged_in, series):
    """Talks, workshops, readings: each ## an event with "Date:" and
    "Place:" lines and links to slides or video. The ones to come first,
    soonest first; past ones fold away, newest first."""
    from datetime import date
    from soloblog import tz
    today = date.fromisoformat(tz.local_date(utcnow().isoformat()))
    intro, secs = sections(html)
    coming, past, data = [], [], []
    for h, inner, body in secs:
        pairs, rest = facts(body.strip())
        when = next((v for k, v in pairs if k.lower() in ("date", "when")), "")
        place = next((v for k, v in pairs if k.lower() in ("place", "where", "venue", "location")), "")
        day = event_date(text_of(when)) if when else None
        # a card each, its day on a calendar leaf - a list of lines read
        # as plain text, the dates hard to find
        leaf = Div(Div(str(day.day), cls="text-2xl font-bold leading-none"),
                   Div(i18n.months()[day.month - 1], cls="text-xs uppercase tracking-wide mt-1"),
                   cls="w-14 shrink-0 self-start rounded-box bg-primary/10 text-primary text-center py-2.5",
                   aria_hidden="true") if day else None
        item = Div(
            leaf,
            Div(Div(Span(NotStr(when), cls="font-medium") if when else None,
                    Span(" · ", NotStr(place), cls="text-base-content/60") if place else None, cls="text-sm"),
                H3(NotStr(inner), cls=f"{ITEM_TITLE} mt-0.5"),
                *_fact_rows(pairs, skip=("date", "when", "place", "where", "venue", "location")),
                _prose(rest, "mt-1", small=True), cls="min-w-0"),
            id=_id_of(h) or None,
            cls=f"card card-border bg-base-100 {CARD_PAD} flex-row gap-4")
        (past if day and day < today else coming).append((day, item))
        if day:
            event = {"@type": "Event", "name": text_of(inner), "startDate": day.isoformat()}
            if place:
                event["location"] = {"@type": "Place", "name": text_of(place), "address": text_of(place)}
            data.append(event)
    coming.sort(key=lambda p: (p[0] is None, p[0] or today))
    past.sort(key=lambda p: p[0], reverse=True)
    out["body"] = Div(
        _intro(intro, "mb-4"),
        Section(H3(i18n.t("Coming up"), cls="text-base font-semibold text-accent mb-1"),
                Div(*[i for _, i in coming], cls=f"flex flex-col {TIGHT_GAP}"),
                cls="mb-6") if coming and past else Div(*[i for _, i in coming], cls=f"flex flex-col {TIGHT_GAP}"),
        Details(Summary(i18n.t("Past events"), cls="collapse-title font-semibold min-h-0 py-3"),
                Div(*[i for _, i in past], cls=f"collapse-content flex flex-col {TIGHT_GAP}"),
                cls="collapse collapse-arrow bg-base-100 border-[length:var(--border)] border-base-300",
                open=not coming) if past else None,
    )
    for d in data:
        out["ld"].append(_ld({"@context": "https://schema.org", **{k: v for k, v in d.items() if v}}))


_PHONE = re.compile(r"^\+?[\d\s().-]{6,20}$")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", re.I)
_HOURS_ROW = re.compile(r"^\s*([^:]{1,30}):\s*(.+?)\s*$")


def _steps(ol_inner):
    """A numbered list's items as steps, each a card with its number: a
    bold start is its title, and a link at its end its button."""
    items = re.findall(r"<li>(.*?)</li>", ol_inner, re.S)
    cards = []
    # by its own width (a landing page's band, a post's column): three cards
    # side by side squeezed their words to a few to a line in a column
    # - short steps (a line each) still three across, where they fit
    short = all(len(text_of(i)) < 120 for i in items)
    cols = {1: "", 2: "@lg:grid-cols-2", 3: "@xl:grid-cols-3" if short else "@3xl:grid-cols-3",
            4: "@lg:grid-cols-2 @5xl:grid-cols-4"}.get(len(items), "@lg:grid-cols-2 @4xl:grid-cols-3")
    for n, item in enumerate(items, 1):
        item = re.sub(r"^\s*<p>|</p>\s*$", "", item.strip())
        title = None
        m = re.match(r"\s*<strong>(.*?)</strong>\s*", item, re.S)
        if m:
            title, item = m.group(1).strip().rstrip("."), item[m.end():]
        link = re.search(r'\s*<a href="([^"]+)"[^>]*>(.*?)</a>\s*\.?\s*$', item, re.S)
        button = None
        if link:
            button = A(NotStr(link.group(2)), href=link.group(1), cls="btn btn-sm btn-soft btn-primary self-start mt-auto")
            item = item[:link.start()]
        cards.append(Li(
            Span(str(n), cls="size-9 rounded-full bg-primary text-primary-content grid place-items-center font-bold"),
            H3(NotStr(title), cls=ITEM_TITLE) if title else None,
            Div(NotStr(item), cls="text-base-content/75") if text_of(item).strip() else None,
            button, cls=f"card card-border bg-base-100 {CARD_PAD} gap-3 {LIFT if button else ''}"))
    return Div(Ol(*cards, cls=f"grid {ITEMS_GAP} {cols}"), cls="@container")


def _render_steps(out, row, s, html, toc, logged_in, series):
    """Steps: a numbered list, each step its number - how it works, how to
    order. Words before and after it stay words."""
    m = re.search(r"<ol>(.*?)</ol>", html, re.S)
    out["body"] = Div(_prose(html[:m.start()], GROUP_SPACE), _steps(m.group(1)), _prose(html[m.end():], "mt-6")) \
        if m else _prose(html)


def _render_hours(out, row, s, html, toc, logged_in, series):
    """Opening hours: "Day: hours" lines as a table; anything else words."""
    rows = []
    for m in re.finditer(r"<p>.*?</p>", html, re.S):
        rows = _hours_rows(m.group(0))
        if rows:
            out["body"] = Div(_prose(html[:m.start()], "mb-4"), _hours_table(rows), _prose(html[m.end():], "mt-4"))
            out["business"] = {"openingHours": [f"{r.group(1)} {r.group(2)}" for r in rows]}
            return
    out["body"] = _prose(html)


def _render_details(out, row, s, html, toc, logged_in, series):
    """Contact details: Phone, Email and Address lines as buttons to call,
    write and find you on a map."""
    pairs, rest = facts(html, before_heading=True)
    out["business"] = {}
    buttons = _contact_buttons(pairs, out["business"])
    out["body"] = Div(Div(*buttons, cls="flex flex-wrap gap-2") if buttons else None, _prose(rest, "mt-4"))


def _business_data(row, found):
    data = {"@context": "https://schema.org", "@type": "LocalBusiness", "name": row["title"],
            "description": row["summary"] or None, **found}
    return _ld({k: v for k, v in data.items() if v})


_CONTACT_BTN = "btn btn-sm h-auto min-h-[var(--size)] max-w-full whitespace-normal text-start py-1"


def _contact_buttons(pairs, data):
    """Phone, Email and Address lines as buttons to call, write and see it
    on a map (into data, for search engines); any other line as text."""
    from urllib.parse import quote
    buttons = []
    # a long address or email wraps inside the screen, as a button doesn't
    for k, v in pairs:
        value = text_of(v)
        if _EMAIL.match(value):
            buttons.append(A(_icon(_MAIL_ICON), Span(value, cls="ml-1"), href=f"mailto:{value}", cls=_CONTACT_BTN))
            data["email"] = value
        elif _PHONE.match(value):
            buttons.append(A(_icon(_PHONE_ICON), Span(value, cls="ml-1"), href="tel:" + re.sub(r"[^\d+]", "", value),
                             cls=_CONTACT_BTN))
            data["telephone"] = value
        elif k.lower() in ("address", "where", "find us", "location"):
            buttons.append(A(_icon(_PIN_ICON), Span(value, cls="ml-1"),
                             href=f"https://www.openstreetmap.org/search?query={quote(value)}", target="_blank",
                             rel="noopener", cls=_CONTACT_BTN))
            data["address"] = value
        else:
            buttons.append(Div(Span(k, cls="text-base-content/60"), " ", Span(NotStr(v)), cls="text-sm self-center"))
    return buttons


def _hours_rows(body):
    """A paragraph of "Day: hours" lines (two or more), as matches - or []."""
    para = re.fullmatch(r"\s*<p>(.*?)</p>\s*", body, re.S)
    lines = [ln for ln in re.split(r"\n|<br\s*/?>", para.group(1)) if ln.strip()] if para else []
    rows = [_HOURS_ROW.match(text_of(ln)) for ln in lines]
    return rows if len(rows) >= 2 and all(rows) else []


def _hours_table(rows):
    return Table(Tbody(*[Tr(Td(m.group(1), cls="font-medium"), Td(m.group(2), cls="text-right")) for m in rows]),
                 cls="table table-sm max-w-md")


_MAIL_ICON = ("M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 "
              "0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 "
              "0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75")
_PHONE_ICON = ("M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 0 0 2.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-"
               "4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 0 1-"
               "7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 "
               "1.125 0 0 0-1.091-.852H4.5A2.25 2.25 0 0 0 2.25 4.5v2.25Z")
_PIN_ICON = ("M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 "
             "7.5 0 1 1 15 0Z")
_DOWNLOAD_ICON = "M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3"
_MENU_ITEM = re.compile(r"^(?P<name>.+?)(?:\s+[-–—]\s+(?P<about>.+?))?(?:\s+·\s+(?P<price>[^·]+))?$", re.S)


def _render_menu(out, row, s, html, toc, logged_in, series):
    """A café's menu: each ## is a course; each item, a list item or a line,
    "Name - description · price", in two columns, its price on the right."""
    intro, secs = sections(html)
    blocks = []
    for h, inner, body in secs:
        raw = re.findall(r"<li>(.*?)</li>", body, re.S)
        # with the dishes in a list, what isn't - a note under the course - shows under them
        rest = re.sub(r"<(ul|ol)\b.*?</\1>", "", body, flags=re.S) if raw else ""
        if not raw:
            for p in re.findall(r"<p>(.*?)</p>", body, re.S):
                raw += [ln for ln in re.split(r"\n|<br\s*/?>", p) if ln.strip()]
        items = []
        for item in raw:
            m = _MENU_ITEM.match(item.strip())
            if not m:
                continue
            items.append(Div(
                Div(Span(NotStr(m.group("name")), cls="font-semibold"),
                    Span(cls="flex-1 border-b-[length:var(--border)] border-dotted border-base-content/30 mx-2 "
                             "translate-y-[-0.3em]") if m.group("price") else None,
                    Span(NotStr(m.group("price").strip()), cls="font-semibold tabular-nums shrink-0")
                    if m.group("price") else None, cls="flex items-baseline"),
                Div(NotStr(m.group("about")), cls="text-sm text-base-content/70") if m.group("about") else None,
                cls="break-inside-avoid mb-3"))
        blocks.append(Section(H3(NotStr(inner), cls=f"{ITEM_TITLE} mb-3"),
                              Div(*items, cls="sm:columns-2 gap-8") if items else None,
                              _prose(rest, "mt-3") if items else _prose(body),
                              id=_id_of(h) or None, cls="mb-8"))
    out["body"] = Div(_intro(intro), *blocks)


def _bio_blocks(secs, heading):
    """Each ## of text (a short bio, a long one) with a Copy button, and
    every image a Download link; the rest stays as written. heading: H2
    (a page) or H3 (a section's items)."""
    blocks = []
    for h, inner, body in secs:
        if re.search(r"<img\b", body):
            # pictures written on lines together are one paragraph; each is a photo of its own
            body = re.sub(r"<p>((?:\s*<img\b[^>]*>\s*)+)</p>",
                          lambda m: "".join(f"<p>{i}</p>" for i in re.findall(r"<img\b[^>]*>", m.group(1))), body)
            # the photos, each with its credit and a Download link to the file itself
            photos, words = [], body
            while True:
                img, credit, words_left = _take_image(words)
                src = re.search(r'\bsrc="([^"]+)"', img or "")
                if not src:
                    break
                words = words_left
                photos.append(Figure(
                    NotStr(_with_class(img, "w-full aspect-square object-cover rounded-box")),
                    Div(NotStr(credit), cls="text-xs text-base-content/50 mt-1") if credit else None,
                    A(_icon(_DOWNLOAD_ICON), Span(i18n.t("Download"), cls="ml-1"), href=unescape(src.group(1)),
                      download="", cls="btn btn-xs mt-2")))
            content = Div(*photos, cls=f"grid grid-cols-2 sm:grid-cols-3 {ITEMS_GAP}")
            blocks.append(Section(heading(NotStr(inner), cls=f"{ITEM_TITLE} mb-2"), _prose(words, "mb-3"), content,
                                  id=_id_of(h) or None, cls="mb-8"))
            continue
        plain = not re.search(r"<(ul|ol|table|a)\b", body)
        blocks.append(Section(
            Div(heading(NotStr(inner), cls=ITEM_TITLE),
                Button(i18n.t("Copy"), type="button", cls="btn btn-xs", data_copy=text_of(body.replace("</p>", "</p>\n\n")).strip(),
                       data_copied=i18n.t("Copied")) if plain and text_of(body) else None,
                cls="flex items-center justify-between gap-3 mb-2"),
            _prose(body), id=_id_of(h) or None, cls="mb-8"))
    return blocks


def _render_bios(out, row, s, html, toc, logged_in, series):
    """Bios to copy and photos to download, each ### one of them."""
    intro, secs = sections(html)
    out["body"] = Div(_intro(intro, GROUP_SPACE) if intro.strip() else None, *_bio_blocks(secs, H3))


def _person_data(row, s):
    return _ld({"@context": "https://schema.org", "@type": "ProfilePage",
                "mainEntity": {"@type": "Person", "name": s.get("author_name") or row["title"],
                               "description": row["summary"] or None}})


def _render_resume_part(out, row, s, html, toc, logged_in, series):
    """Jobs or schooling: each ### an entry, its title and, after a ·, its
    dates on the right, its words under. The page tells search engines
    who the person is."""
    intro, entries = sections(html)
    out["body"] = Div(
        _intro(intro, GROUP_SPACE) if intro.strip() else None,
        Div(*[Div(
            Div(H3(NotStr(title), cls=ITEM_TITLE),
                Span(NotStr(when), cls="text-sm text-base-content/60 shrink-0") if when else None,
                cls="flex flex-wrap items-baseline justify-between gap-x-4"),
            _prose(body, "mt-1"), id=_id_of(h) or None, cls="py-2")
            for h, inner, body in entries for title, when in [split_date(inner)]],
            cls="flex flex-col"))
    out["ld"].append(_person_data(row, s))


def _render_skills(out, row, s, html, toc, logged_in, series):
    """Short items as badges; a list with a long item stays a list."""
    blocks, words = [], []

    def flush():
        if words:
            blocks.append(_prose("".join(words)))
            words.clear()

    for block in top_blocks(html):
        items = re.findall(r"<li>(.*?)</li>", block, re.S) if block.startswith("<ul>") else []
        if items and "<ul" not in block[4:] and all(len(text_of(i)) <= 40 for i in items):
            flush()
            blocks.append(Div(*[Span(NotStr(i), cls="badge badge-outline") for i in items], cls="flex flex-wrap gap-2"))
        else:
            words.append(block)
    flush()
    out["body"] = Div(*blocks, cls="flex flex-col gap-4")


def _render_profile_part(out, row, s, html, toc, logged_in, series):
    """A person's introduction, centred: the photo, their name big (the
    section's own ##), a big one-line intro, a short bio and buttons to
    their main links."""
    img, credit, rest = _take_image(html)
    lead = re.search(r"<p>(.*?)</p>", rest, re.S)
    if lead and not _LINKS_ONLY.fullmatch(lead.group(0)):
        rest = rest[:lead.start()] + rest[lead.end():]
    else:
        lead = None
    buttons, rest = _link_buttons(rest)
    out["body"] = Div(
        Div(Div(NotStr(_with_class(img, "object-cover")),
                cls="w-28 rounded-full ring-[length:var(--border)] ring-base-300"), cls="avatar mb-4")
        if img else None,
        _styled_heading(out["heading"], f"{_title_cls()} text-balance") if out.get("heading") else None,
        P(NotStr(lead.group(1)), cls="text-xl text-base-content/80 mt-2 max-w-xl") if lead else None,
        Div(NotStr(credit), cls="text-xs text-base-content/50 mt-1") if credit else None,
        _prose(rest, "mt-4 mx-auto max-w-xl text-center") if text_of(rest) else None,
        Div(buttons, cls="mt-6") if buttons else None,
        cls="flex flex-col items-center text-center")
    out["ld"].append(_person_data(row, s))


def _render_project_facts(out, row, s, html, toc, logged_in, series):
    """Each "Key: value" line (Client, Year, Role...) a fact, in a strip."""
    pairs, rest = facts(html)
    out["body"] = Div(
        Div(*_facts_cells(pairs), cls="grid grid-cols-2 @lg:grid-cols-[repeat(auto-fit,minmax(9rem,1fr))] gap-6 py-6 "
                                      "border-y border-base-content/10") if pairs else None,
        _prose(rest, "mt-6") if text_of(rest) else None)


def _render_photo_story(out, row, s, html, toc, logged_in, series):
    """Pictures and words laid out like a magazine (_story_rows). Three
    options turn its arrangements off."""
    chosen = {}
    for name in ("First paragraph", "Pictures together", "A line after a picture"):
        value, html = section_registry.take_line(html, name.lower())
        chosen[name] = section_registry.pick(name, value)
    rows = _story_rows(html, _STORY_SECTION, big=chosen["First paragraph"] != "normal",
                       together=chosen["Pictures together"] != "stack",
                       beside=chosen["A line after a picture"] != "under")
    out["body"] = Div(*rows, cls=f"flex flex-col {_STORY_SECTION['gap']}")


# A Story (Section: Story): the words scroll, each step's picture changes
# behind or beside them. Its classes apply only once MOTION_JS has marked it
# live (data-live: the browser can watch it and motion is allowed) - until
# then, and with Animations off or "reduce motion", it's a plain stack, each
# step's picture above its words. Live, from a laptop's width (the story's
# own width, so a Column one stays small): the words in a column, the
# pictures held beside them. Narrower: each picture fills the screen, held
# behind the words, which scroll up over it. Classes are
# written out whole, as Tailwind needs to find them.
# the picture's real width: the screen's on a phone; beside the words, about
# 56vw, never under a column's 48rem or over the widest story's 61rem
SCROLL_STORY_SIZES = "(min-width: 1024px) min(max(56vw, 48rem), 61rem), 100vw"
_SCROLL_STEP = ("flex flex-col gap-6 px-6 py-12 sm:px-10 sm:py-16 "
                "group-data-[live]/story:min-h-svh group-data-[live]/story:justify-end group-data-[live]/story:py-0 "
                "group-data-[live]/story:px-0 sm:group-data-[live]/story:px-0 group-data-[live]/story:gap-0 "
                "@5xl:group-data-[live]/story:min-h-[70svh] "
                # the first and last steps are as tall as the held picture's space (and the 1rem the
                # page keeps under its header), so their words are level with the picture's middle
                # from the moment it's held until it lets go - at 70svh it was still arriving
                # when the first words were in place, and leaving before the last were
                # (MOTION_JS works out --story-first-h and --story-last-h from the held picture's
                # height and place: the last step's words reach its middle before it lets go)
                "@5xl:group-data-[live]/story:first:min-h-[var(--story-first-h,calc(100svh-var(--story-top,var(--header-h,0px))-var(--footer-h,0px)+1rem))] "
                "@5xl:group-data-[live]/story:last:min-h-[var(--story-last-h,calc(100svh-var(--story-top,var(--header-h,0px))-var(--footer-h,0px)+1rem))] "
                "@5xl:group-data-[live]/story:justify-center @5xl:group-data-[live]/story:gap-6")
# On a phone the words scroll over the held picture, which fades into the
# page's own colour at the foot (see held below) - so the words are the
# theme's own text colour there too, and a soft shadow in the page's colour
# keeps them readable while they cross the picture's clear part
# a card is the page's colour (base-100) with 4% of the text colour over it
_STORY_CARD_FADE = "[--story-fade:color-mix(in_oklab,var(--color-base-content)_4%,var(--color-base-100))]"
_SCROLL_WORDS = ("mx-auto w-full max-w-3xl text-base-content group-data-[live]/story:max-w-none "
                 "group-data-[live]/story:mx-0 group-data-[live]/story:pointer-events-auto "
                 "group-data-[live]/story:px-6 group-data-[live]/story:text-shadow-lg "
                 "group-data-[live]/story:text-shadow-base-200 "
                 "in-data-[story-card]:group-data-[live]/story:text-shadow-(color:--story-fade) "
                 "@5xl:group-data-[live]/story:text-shadow-none "
                 "sm:group-data-[live]/story:px-10 group-data-[live]/story:pb-16 "
                 "@5xl:group-data-[live]/story:px-0 "
                 "@5xl:group-data-[live]/story:pb-0 @5xl:group-data-[live]/story:max-w-md")
# .prose sets its own link colour, so the words' one can't reach it from above
_SCROLL_PROSE = "text-base-content/85"
# how far a Story's words and picture spread on a wide screen: its own
# Width decides (place_sections swaps the cap) - Wide fills the wide
# area, Full goes further on a big screen, so the two don't look the same
_STORY_CAP = "@5xl:group-data-[live]/story:max-w-7xl"
_STORY_CAPS = {"wide": "@5xl:group-data-[live]/story:max-w-full",
               "full": "@5xl:group-data-[live]/story:max-w-[110rem]"}
_SCROLL_WORDS_INNER = "group-data-[live]/story:max-w-xl @5xl:group-data-[live]/story:max-w-none"
# A picture sits 1rem under the header and 0.75rem in from the sides, its
# corners rounded, over the page's own background (nothing solid behind it).
# Its credit is on the picture itself, so the wrapper is as big as the
# picture - a phone's landscape one (data-fit, set by MOTION_JS on the
# frame: nothing else can tell the shape) fills the area instead.
# --story-h is the area's height, the most a picture may take.
_SCROLL_FRAME = ("group/frame absolute inset-x-3 top-4 bottom-0 flex items-start justify-center "
                 "[--story-h:calc(100svh-var(--header-h,0px)-1rem)] "
                 # the one going shrinks a little as it fades; the next comes in at its size
                 "opacity-0 scale-[0.96] pointer-events-none transition-[opacity,scale] duration-700 "
                 "motion-reduce:transition-none motion-reduce:scale-100 data-[active]:opacity-100 "
                 "data-[active]:scale-100 data-[active]:transition-opacity "
                 "@5xl:inset-0 @5xl:items-start "
                 "@5xl:[--story-h:var(--story-pic-h,calc(100svh-var(--story-top,var(--header-h,0px))-var(--footer-h,0px)-3rem))]")
# only the shown picture takes a press, never the empty space round it, which lies over
# the story's opening words and their links
_SCROLL_WRAP = ("relative w-fit max-w-full group-data-[active]/frame:pointer-events-auto "
                "group-data-[fit=cover]/frame:h-full group-data-[fit=cover]/frame:w-full")
# a picture that's whole keeps its own shape; the corners and shadow are on
# the picture itself, so nothing frames empty space
# (no edge on a phone: a screenshot's own rounded frame showed a second one)
_SCROLL_PICTURE = ("block h-auto w-auto max-w-full max-h-(--story-h) rounded-box @5xl:border @5xl:border-base-content/10 "
                   "group-data-[fit=cover]/frame:h-full group-data-[fit=cover]/frame:w-full "
                   "group-data-[fit=cover]/frame:object-cover @5xl:shadow-xl")
# a credit over a phone's picture sits at the top: the foot fades into the page
_SCROLL_CREDIT = CREDIT_OVER.replace("absolute bottom-1.5", "absolute top-1.5 @5xl:top-auto @5xl:bottom-1.5")


def _scroll_story_picture(img, eager):
    """A step's picture for the held layer: not read out (its words and the
    picture in the step are), fetched when its turn nears - the first at
    once."""
    img = re.sub(r'\s(?:alt|sizes|loading|fetchpriority|decoding)="[^"]*"', "", _with_class(img, _SCROLL_PICTURE))
    lazy = "" if eager else 'loading="lazy" '
    return img.replace("<img ", f'<img alt="" aria-hidden="true" sizes="{SCROLL_STORY_SIZES}" {lazy}decoding="async" ', 1)


def _render_story(out, row, s, html, toc, logged_in, series):
    """Steps that tell a story as it's scrolled: each ## (a ### written) is
    a step with one picture and its words. A step without a picture keeps
    the one before it held; none at all, a plain layer."""
    intro, secs = sections(html)
    steps, frames, marks, picture = [], [], [], None
    for n, (h, inner, body) in enumerate(secs):
        img, credit, rest = _take_image(body)
        href, label, rest = _take_button(rest)
        sized = ""
        if img:
            picture = len(frames)
            sized = re.sub(r'\bsizes="[^"]*"', f'sizes="{SCROLL_STORY_SIZES}"', img)
            held = re.sub(r'<a\b', '<a tabindex="-1"', credit)
            frames.append(Div(Div(NotStr(_scroll_story_picture(img, not frames)),
                                  Div(NotStr(held), cls=_SCROLL_CREDIT) if credit else None, cls=_SCROLL_WRAP),
                              data_story_picture=str(picture), cls=_SCROLL_FRAME))
        steps.append(Div(
            Div(_card_image(sized, credit, f"{_FRAME} object-cover"),
                data_story_real=True, cls="mb-2 mx-auto w-full max-w-3xl group-data-[live]/story:sr-only") if img else None,
            Div(Div(Div(H3(NotStr(inner), cls="text-3xl sm:text-4xl font-bold tracking-tight text-balance mb-3"),
                        _prose(rest, _SCROLL_PROSE), cls="text-base-content"),
                    A(NotStr(label), href=href, cls="btn btn-primary mt-5") if href else None,
                    cls=_SCROLL_WORDS_INNER),
                data_story_words=True, cls=_SCROLL_WORDS),
            id=_id_of(h) or None, data_story_step=str(n), data_story_pic="" if picture is None else str(picture),
            cls=_SCROLL_STEP))
        marks.append(Span(data_story_mark=str(n), cls="block w-1 rounded-full bg-base-content/20 h-4 "
                          "data-[active]:h-10 data-[active]:bg-primary transition-all duration-500 "
                          "motion-reduce:transition-none"))
    if not steps:
        out["body"] = _prose(intro) or Div()
        return
    # on a phone the layer starts under the header and fills the rest of the
    # screen, sticking while the words scroll over it (same grid cell); on a
    # laptop it's the picture, centred, with the step markers in a space of
    # their own beside it. The fade is part of this layer, so it stays put as
    # the words move: clear over the top, the page's own colour behind the
    # words, where each step settles
    held = Div(Div(*frames, Div(cls="absolute inset-0 bg-linear-to-b from-transparent from-60% via-base-200/55 "
                                    "via-76% to-base-200/90 to-95% @5xl:hidden "
                                    "in-data-[story-card]:via-(--story-fade)/55 in-data-[story-card]:to-(--story-fade)/90"),
                   cls="relative h-full w-full "
                       "@5xl:h-[var(--story-pic-h,calc(100svh-var(--story-top,var(--header-h,0px))-var(--footer-h,0px)-3rem))] "
                       "@5xl:min-w-0 @5xl:flex-1"),
               # which step you're on: beside the picture on a wide screen, and on
               # a phone over its edge, on a pill of the page's colour so it shows on any picture
               Div(*marks, cls="order-first hidden flex-col items-center gap-2 group-data-[live]/story:flex "
                               "absolute end-5 top-1/2 -translate-y-1/2 rounded-full bg-base-200/70 "
                               "px-1.5 py-2 backdrop-blur-sm @5xl:static @5xl:translate-y-0 @5xl:shrink-0 "
                               "@5xl:me-6 @5xl:rounded-none @5xl:bg-transparent @5xl:p-0 "
                               "@5xl:backdrop-blur-none") if len(steps) > 1 else None,
               aria_hidden="true", data_story_held=True,
               cls="hidden group-data-[live]/story:block sticky top-[var(--story-top,var(--header-h,0px))] "
                   "h-[calc(100svh-var(--header-h,0px))] self-start min-w-0 pointer-events-none "
                   "[grid-area:1/1] @5xl:[grid-area:1/2] "
                   # as tall as the picture (--story-pic-h, MOTION_JS), so the story lets go
                   # when the picture's foot meets the section's - down to the window's foot,
                   # a tall window left a screen of empty box before the next section
                   "@5xl:h-[var(--story-pic-h,calc(100svh-var(--story-top,var(--header-h,0px))-var(--footer-h,0px)))] "
                   "@5xl:group-data-[live]/story:flex @5xl:items-start")
    out["body"] = Div(
        Div(_intro(intro), cls=_col(s)) if text_of(intro) else None,
        Div(Div(*steps, cls="min-w-0 group-data-[live]/story:relative group-data-[live]/story:z-10 "
                            "group-data-[live]/story:[grid-area:1/1] group-data-[live]/story:pointer-events-none"),
            held,
            cls="group-data-[live]/story:grid @5xl:group-data-[live]/story:grid-cols-[2fr_3fr] "
                f"@5xl:group-data-[live]/story:gap-16 {_STORY_CAP} "
                "@5xl:group-data-[live]/story:mx-auto @5xl:group-data-[live]/story:px-8"),
        data_story=True, cls="group/story relative")


def _render_team(out, row, s, html, toc, logged_in, series):
    """The people behind a shop, practice or project: each ## a person, with
    a photo, a "Role:" line and a short bio, as a grid of cards."""
    intro, secs = sections(html)
    cards, after = [], []
    for h, inner, body in secs:
        img, credit, rest = _take_image(body)
        pairs, rest = facts(rest.strip())
        if not img and not pairs:
            after.append(h + body)
            continue
        role = next((v for k, v in pairs if k.lower() in ("role", "job", "title", "position")), None)
        cards.append(Div(
            _pictured(img, credit, "w-full aspect-square object-cover"),
            Div(H3(NotStr(inner), cls=ITEM_TITLE),
                Div(NotStr(role), cls="text-sm text-primary -mt-1") if role else None,
                *_fact_rows(pairs, skip=("role", "job", "title", "position")),
                _prose(rest, "[&_p]:my-1", small=True), cls=f"card-body {CARD_PAD} gap-2"),
            id=_id_of(h) or None, cls="card card-border bg-base-100 overflow-hidden"))
    out["body"] = Div(Div(_intro(intro), cls=_col(s)),
                      Div(*cards, cls=_grid(len(cards))) if cards else None,
                      Div(_prose("".join(after), "mt-12 sm:mt-16"), cls=_col(s)) if after else None)


def _render_products(out, row, s, html, toc, logged_in, series):
    """A few things for sale: each ## with a "Price:" line is a product card
    - its image, description and a buy button that goes wherever the link
    points (Stripe, Gumroad, Lemon Squeezy, PayPal) - no cart or checkout
    here. "Badge: Sold out" or the like shows on the card. Other ##
    sections stay text, under the cards."""
    intro, secs = sections(html)
    cards, after = [], []
    for h, inner, body in secs:
        img, credit, rest = _take_image(body)
        pairs, rest = facts(rest.strip())
        price = next((v for k, v in pairs if k.lower() == "price"), None)
        if price is None:
            after.append(h + body)
            continue
        badge = next((text_of(v) for k, v in pairs if k.lower() == "badge"), "")
        href, label, rest = _take_button(rest)
        cards.append(Div(
            _pictured(img, credit, "w-full aspect-[4/3] object-cover"),
            Div(Span(badge, cls="badge badge-sm self-start") if badge else None,
                H3(NotStr(inner), cls=ITEM_TITLE),
                Div(NotStr(price), cls="text-xl font-bold"),
                *_fact_rows(pairs, skip=("price", "badge")),
                _prose(rest, "[&_p]:my-1", small=True),
                Div(A(NotStr(label), href=href, cls="btn btn-sm btn-block",
                      **({"target": "_blank", "rel": "noopener"} if href.startswith("http") else {})),
                    cls="card-actions mt-auto pt-3") if href else None,
                cls=f"card-body {CARD_PAD} gap-2"),
            id=_id_of(h) or None, cls="card card-border bg-base-100 overflow-hidden"))
    out["body"] = Div(Div(_intro(intro), cls=_col(s)),
                      Div(*cards, cls=_grid(len(cards))) if cards else None,
                      Div(_prose("".join(after), "mt-12 sm:mt-16"), cls=_col(s)) if after else None)
