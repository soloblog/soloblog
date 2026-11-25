"""What a visitor's page is made of: a post's parts, lists of posts, the side
panels and the footer."""
import contextvars

from fasthtml.common import *
from soloblog import csp
from soloblog import gallery
from soloblog import i18n
from soloblog import newsletter
from soloblog.actions import on
from soloblog import posts
from soloblog import settings
from soloblog.render import format_date
from soloblog.ui.icons import (
    CHECK_SVG, EXTRA_LINK_ICONS, HEART_OUTLINE_SVG, HEART_SVG, LINK_SVG, PAUSE_SVG, SPEAKER_SVG, X_SVG,
    ordered_social_platforms,
)
from soloblog.ui.base import (
    Breakout, MARGIN_WIDTHS, PageLink, SCROLLS, SettingsPanel, SiteLink, TOUCH_LINK, content_width, glass_fill, safe_url,
    tag_url,
)


def ReactionBar(slug: str, s, counts: dict, logged_in: bool = False):
    """The emoji row under a post (reactions.py). Same pill buttons as
    the like button - outline, quiet until pressed; a pressed one turns
    primary. The admin sees the counts only, like the like button."""
    from soloblog import reactions
    keys = reactions.enabled_keys(s.get("reaction_emojis"))
    pills = []
    for key in keys:
        emoji, label = reactions.CHOICES[key]
        count = Span(str(counts.get(key, 0)), cls="reaction-count text-xs tabular-nums")
        # read as "Heart 3": the word in place of the emoji, then the count
        face = (Span(emoji, aria_hidden="true"), Span(i18n.t(label), cls="sr-only"))
        if logged_in:
            pills.append(Span(*face, count, cls="btn btn-sm btn-ghost pointer-events-none gap-1"))
        else:
            pills.append(Button(*face, count, type="button", data_reaction=key, data_tip=i18n.t(label),
                                cls="reaction tooltip btn btn-sm btn-outline border-base-300 gap-1 "
                                    "hover:border-primary aria-pressed:btn-primary",
                                aria_pressed="false"))
    return Div(*pills, id="reactions", data_slug=slug, cls="flex flex-wrap gap-2 print:hidden")


def LikeButton(slug: str, likes: int, logged_in: bool = False):
    """Outline heart until liked, then fills in and turns red with a
    little pop - the sync between the two states (and the pop
    animation) happens client-side in LIKE_JS. One like per browser,
    tracked in localStorage - no accounts, no server-side dedup beyond
    that. Good enough for a personal blog.

    The admin can't like their own post - liking your own writing
    isn't a meaningful signal, so logged-in view just shows the count,
    no button at all."""
    if logged_in:
        return Div(
            HEART_OUTLINE_SVG, Span(str(likes), cls="ml-1.5 text-sm font-medium tabular-nums"),
            cls="flex items-center text-base-content/50"
        )
    return Button(
        Span(HEART_OUTLINE_SVG, cls="heart-outline"),
        Span(HEART_SVG, cls="heart-filled text-error hidden"),
        Span(str(likes), id="like-count", cls="text-sm font-medium tabular-nums"),
        type="button", **on("click", "toggleLike", slug), id="like-button",
        # btn-outline (it always has a border) with a quieter
        # border-base-300, and red on hover - daisyUI has no way to dim
        # just the border, or that cue
        cls="btn btn-sm btn-outline border-base-300 hover:border-error/50 hover:text-error"
    )


def ListenButton():
    """Reads the post aloud with the browser's own speech synthesis -
    no service, no audio files. Same outline look as LikeButton beside
    it. Starts hidden: READING_JS (app.py) only reveals it on a browser
    that can actually speak, and swaps Listen/Pause/Resume as it goes."""
    return Button(
        Span(SPEAKER_SVG, cls="listen-icon-play"),
        Span(PAUSE_SVG, cls="listen-icon-pause hidden"),
        Span(i18n.t("Listen"), cls="listen-label text-sm font-medium"),
        type="button", id="listen-button", **on("click", "toggleListen"),
        cls="btn btn-sm btn-outline border-base-300 hidden print:hidden"
    )


def ReadingProgress():
    """A thin bar pinned to the top of the viewport, filled by
    READING_JS (app.py) as the reader scrolls through the article."""
    return Progress(value="0", max="100", id="reading-progress", aria_label=i18n.t("Reading progress"),
                    cls="progress progress-primary fixed top-0 left-0 w-full h-1 rounded-none z-50 bg-transparent")


# exact versions with integrity hashes, loaded only on a post that needs
# them - the browser refuses the file if the CDN ever serves anything else
MERMAID_JS = ("https://cdn.jsdelivr.net/npm/mermaid@12.0.0/dist/mermaid.min.js",
              "sha384-xzghz1GQ5u9HCpVskeDPqMsdogD1yvuMQbEK53+wi+G70+6J1AG0L2cfi9PHjDWI")
KATEX_VERSION = "0.16.11"
KATEX_SRI = {
    "katex.min.js": "sha384-7zkQWkzuo3B5mTepMUcHkMB5jZaolc2xDwL6VFqjFALcbeS9Ggm/Yr2r3Dy4lfFg",
    "katex.min.css": "sha384-nB0miv6/jRmo5UMMR1wu3Gz6NLsoTkbqJghGIsx//Rlm+ZU03BU6SQNC66uf4l5+",
    "contrib/auto-render.min.js": "sha384-43gviWU0YVjaDtb/GhzOouOXtZMP/7XUzwPTstBeZFe/+rCMvRwr4yROQP43s0Xk",
}


def LightboxDialog(settings):
    """One popout viewer per page, shared by every gallery and (when
    Settings > Appearance > Images allows) every single image in a post.
    The same modal-box, glass fill, backdrop and btn-sm row as the site's
    other dialogs - image on top, caption left, count and buttons right,
    Close last. LIGHTBOX_JS (app.py) fills and drives it."""
    return Dialog(
        Div(
            Div(
                Img(id="lightbox-img", alt="", draggable="false",
                    cls="max-h-[80vh] max-w-full object-contain select-none transition-transform duration-200"),
                Span(id="lightbox-loading", role="status", aria_label=i18n.t("Loading"),
                     cls="loading loading-spinner loading-md absolute inset-0 m-auto text-base-content/60 hidden"),
                id="lightbox-stage",
                # frosted like the rest of the viewer when that's on
                cls=f"relative overflow-hidden rounded-box {glass_fill(settings, 'bg-base-200')} flex items-center "
                    "justify-center min-h-48 cursor-zoom-in touch-none"
            ),
            Div(
                # a line of its own on a phone, not squeezed by the buttons beside it
                P(id="lightbox-caption", cls="text-sm text-base-content/70 w-full sm:w-auto sm:flex-1 min-w-0 "
                                             "empty:hidden"),
                # pushed right with the buttons - with a caption beside it or none
                Span(id="lightbox-count", cls="text-xs text-base-content/50 tabular-nums ml-auto"),
                Div(
                    Button(NotStr(gallery.CHEVRON_LEFT), type="button", cls="btn btn-sm join-item",
                           aria_label=i18n.t("Previous image"), **on("click", "stepLightbox", -1)),
                    Button(NotStr(gallery.CHEVRON_RIGHT), type="button", cls="btn btn-sm join-item",
                           aria_label=i18n.t("Next image"), **on("click", "stepLightbox", 1)),
                    id="lightbox-nav", cls="join"
                ),
                Button(X_SVG, Span(i18n.t("Close"), cls="ml-1"), type="button", cls="btn btn-sm",
                       data_close_dialog="lightbox"),
                # as wide as the picture, however long the caption
                cls="flex flex-wrap items-center gap-3 mt-3 w-0 min-w-full"
            ),
            # the picture's own size, up to most of the screen - so it grows and shrinks with each
            # one, and a wide screenshot doesn't open smaller than the slider it came from
            cls=f"modal-box w-fit min-w-[min(20rem,92vw)] max-w-[min(80rem,92vw)] p-3 {glass_fill(settings)}"
        ),
        Form(Button(cls="cursor-default", aria_label=i18n.t("Close")), method="dialog", cls="modal-backdrop"),
        id="lightbox", aria_label=i18n.t("Image"), cls="modal", data_single="1" if settings.get("lightbox_images") == "1" else "0"
    )


def PostScripts(settings, html_body: str):
    """The extra scripts a post's own content asks for - Mermaid for a
    diagram, KaTeX for math - and nothing on a post without either.
    The lightbox too, when there's a gallery or an image to open in it."""
    out = []
    if "data-lightbox" in html_body or (settings.get("lightbox_images") == "1" and "<img" in html_body):
        out.append(LightboxDialog(settings))
    if settings.get("markdown_mermaid") == "1" and 'class="mermaid"' in html_body:
        src, sri = MERMAID_JS
        out.append(Script(src=src, integrity=sri, crossorigin="anonymous", defer=True,
                          **on("load", "initMermaid", True), nonce=csp.NONCE))
    if settings.get("markdown_math") == "1" and 'class="math-' in html_body:
        base = f"https://cdn.jsdelivr.net/npm/katex@{KATEX_VERSION}/dist"
        out += [
            Link(rel="stylesheet", href=f"{base}/katex.min.css", integrity=KATEX_SRI["katex.min.css"],
                 crossorigin="anonymous"),
            Script(src=f"{base}/katex.min.js", defer=True, integrity=KATEX_SRI["katex.min.js"],
                   crossorigin="anonymous", nonce=csp.NONCE),
            Script(src=f"{base}/contrib/auto-render.min.js", defer=True,
                   integrity=KATEX_SRI["contrib/auto-render.min.js"], crossorigin="anonymous",
                   **on("load", "renderPostMath"), nonce=csp.NONCE),
        ]
    return out


def PreviewScripts(settings):
    """Mermaid and KaTeX for the editor's preview, when they're turned on
    - loaded, not run; the preview runs them on what it renders."""
    out = []
    if settings.get("markdown_mermaid") == "1":
        src, sri = MERMAID_JS
        out.append(Script(src=src, integrity=sri, crossorigin="anonymous", defer=True,
                          **on("load", "initMermaid", False), nonce=csp.NONCE))
    if settings.get("markdown_math") == "1":
        base = f"https://cdn.jsdelivr.net/npm/katex@{KATEX_VERSION}/dist"
        out += [
            Link(rel="stylesheet", href=f"{base}/katex.min.css", integrity=KATEX_SRI["katex.min.css"],
                 crossorigin="anonymous"),
            Script(src=f"{base}/katex.min.js", defer=True, integrity=KATEX_SRI["katex.min.js"],
                   crossorigin="anonymous", nonce=csp.NONCE),
            Script(src=f"{base}/contrib/auto-render.min.js", defer=True,
                   integrity=KATEX_SRI["contrib/auto-render.min.js"], crossorigin="anonymous", nonce=csp.NONCE),
        ]
    return out


# how many rows an admin list shows, and which of these it's showing right
# now: the request's choice (?per=, or the cookie it was kept in - see
# app.RowsPerPage), set for the length of the request
ROWS_CHOICES = (10, 20, 50)
_rows_chosen = contextvars.ContextVar("rows_chosen", default=None)


def rows_choice(value):
    """value as one of ROWS_CHOICES, or None for anything else."""
    try:
        n = int(str(value).strip())
    except ValueError:
        return None
    return n if n in ROWS_CHOICES else None


def rows_per_page(default: int) -> int:
    """What the list being drawn shows per page: the visitor's choice, else
    its own default - kept if it is one of the choices, else 20."""
    return _rows_chosen.get() or (default if default in ROWS_CHOICES else 20)


def RowsPerPage(current: int, base_path: str):
    """10, 20 or 50 rows, as one group of links beside the page buttons (not
    a select: each choice is a link, so a live list swaps in place and the
    group is as small on a phone as the page buttons are). A link leaves out
    ?page=, so a new size starts on page 1, and keeps the rest of base_path
    - the search, filters and sort."""
    sep = "&" if "?" in base_path else "?"
    return Div(
        Span("Per page", cls="text-sm text-base-content/70"),
        Div(*[A(str(n), href=f"{base_path}{sep}per={n}", rel="nofollow",
                aria_current="true" if n == current else None,
                aria_label=f"{n} per page",
                cls=f"join-item btn btn-sm {'btn-active' if n == current else ''}") for n in ROWS_CHOICES],
            role="group", aria_label="Rows per page", cls="join"),
        cls="flex items-center gap-2")


def Pagination(page: int, total_pages: int, base_path: str = "/", labels=None, per_page=None, total=0):
    """The one pagination style for the whole app - join-grouped
    prev/current/next, btn-sm, current page shown as a disabled join
    member rather than a bare number. labels defaults to the public
    blog roll's own chronological "Newer/Older" wording; the admin
    posts list (sortable by title/views, not just date) passes
    ("« Prev", "Next »") instead - same shape and style, just wording
    that doesn't silently claim a direction that isn't always true."""
    # an admin list says how many rows it shows (per_page) once it has more
    # than the smallest choice - even on one page, so it can be made smaller
    chooser = RowsPerPage(per_page, base_path) if per_page and total > ROWS_CHOICES[0] else None
    if total_pages <= 1 and not chooser:
        return None
    if per_page:
        sep = "&" if "?" in base_path else "?"
        base_path = f"{base_path}{sep}per={per_page}"
    prev_label, next_label = labels or (i18n.t("« Newer"), i18n.t("Older »"))
    sep = "&" if "?" in base_path else "?"
    prev = A(prev_label, href=f"{base_path}{sep}page={page - 1}", cls="join-item btn btn-sm") \
        if page > 1 else Span(prev_label, aria_disabled="true", cls="join-item btn btn-sm btn-disabled")
    next_ = A(next_label, href=f"{base_path}{sep}page={page + 1}", cls="join-item btn btn-sm") \
        if page < total_pages else Span(next_label, aria_disabled="true", cls="join-item btn btn-sm btn-disabled")
    # every page number near this one, plus the first and last, so any
    # page is a click or two away; … stands in for the ones between
    shown = sorted({1, total_pages, *range(max(1, page - 1), min(total_pages, page + 1) + 1)})
    # on a phone just this one, as "2 / 5", between Prev and Next: every
    # number at 44 px ran off a 320 px screen
    numbers, last = [], 0
    for n in shown:
        if n - last > 1:
            numbers.append(Span("…", cls="join-item btn btn-sm btn-disabled max-sm:hidden", aria_hidden="true"))
        numbers.append(
            Span(str(n), Span(f" / {total_pages}", cls="sm:hidden whitespace-pre"), aria_current="page",
                 cls="join-item btn btn-sm btn-active",
                 aria_label=i18n.t("Page {page} of {total}", page=n, total=total_pages)) if n == page
            else A(str(n), href=f"{base_path}{sep}page={n}", cls="join-item btn btn-sm max-sm:hidden"))
        last = n
    return Div(
        Div(prev, *numbers, next_, cls="join") if total_pages > 1 else None,
        chooser,
        cls="flex flex-wrap justify-center items-center gap-x-6 gap-y-3 mt-8 pt-5 "
            "border-t-[length:var(--border)] border-base-300"
    )


def TagCloud(counts, limit=None, narrow=False):
    """Tags as a cloud: the more posts a tag has, the bigger it is (five
    steps, spread by how many posts the most and least used have).
    limit - only the most used, still A to Z. narrow - beside the page,
    where the biggest steps broke a long tag across two lines."""
    import math
    if limit:
        counts = sorted(sorted(counts, key=lambda c: -c[1])[:limit], key=lambda c: c[0].lower())
    if not counts:
        return None
    low, high = math.log(min(n for _, n in counts)), math.log(max(n for _, n in counts))
    sizes = ("badge-xs", "badge-sm", "badge-sm", "badge-md", "badge-md") if narrow else         ("badge-xs", "badge-sm", "badge-md", "badge-lg", "badge-xl")

    def size(n):
        return sizes[round((math.log(n) - low) / (high - low) * 4)] if high > low else "badge-md"
    # a name too long for the space ends in … rather than breaking the badge
    return Div(*[A(Span(f"#{t}", cls="truncate min-w-0"), Span(str(n), cls="text-base-content/50 tabular-nums shrink-0"),
                   href=tag_url(t), cls=f"badge badge-soft {size(n)} max-w-full whitespace-nowrap hover:underline "
                                        "[@media(pointer:coarse)]:min-h-6")
                 for t, n in counts],
               cls="flex flex-wrap items-center gap-2")


def top_options(options, current, limit=30):
    """A filter's (value, label) options past a sensible length: the
    first limit (callers put the busiest first), the current one kept,
    then by label - so a select stays usable with thousands of posts."""
    kept = options[:limit] + [o for o in options[limit:] if o[0] == current]
    return sorted(kept, key=lambda o: o[1].lower())


def month_counts(rows):
    """[(year, month, posts)] newest first, in the site's timezone - the
    archive's own grouping, for links to it."""
    from soloblog import tz
    from datetime import datetime as _dt
    counts = {}
    for p in rows:
        try:
            stamp = p["created_at"]
            when = _dt.fromisoformat(stamp[:19].rstrip("Z"))
            when = tz.to_local(when) if len(stamp) > 10 else when
        except ValueError:
            continue
        counts[(when.year, when.month)] = counts.get((when.year, when.month), 0) + 1
    return [(y, m, n) for (y, m), n in sorted(counts.items(), reverse=True)]


def ArchiveLinks(months, limit=None, narrow=False):
    """"September 2026 (4)" for each month, to its place on /archive.
    narrow - one column, for beside the posts."""
    months = months[:limit] if limit else months
    if not months:
        return None
    names = i18n.months(full=True)
    return Ul(*[Li(A(f"{names[m - 1]} {y}", Span(f" ({n})", cls="text-base-content/50 tabular-nums whitespace-nowrap"),
                     href=f"/archive#{y}-{m:02d}", cls="link link-hover inline-block py-0.5"))
                for y, m, n in months],
              cls="flex flex-col gap-1 text-sm" if narrow
              else "grid grid-cols-1 min-[420px]:grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-1 text-sm")


# where a timeline's line runs (daisyUI's timeline) - the Timeline
# homepage style and the Milestones section each have their own setting
TIMELINE_ALIGNS = {"left": "Left — the line on the left, entries beside it",
                   "center": "Centred — entries either side of the line",
                   "right": "Right — the line on the right, entries beside it"}


def timeline_cls(align, extra=""):
    """The timeline <ul>'s classes: compact puts every entry after the
    line; the right-hand version keeps them before it and gives the empty
    column no width. Centred falls back to the left below md, where two
    columns don't fit."""
    return "timeline timeline-vertical " + {
        "left": "timeline-compact",
        "right": "[&>li]:[--timeline-col-end:0]",
    }.get(align, "max-md:timeline-compact") + (f" {extra}" if extra else "")


def timeline_stagger(align):
    """The <ul>'s mark for a line down the middle: TIMELINE_JS draws each
    entry up beside the one before, where a row each left one side empty."""
    return {} if align in ("left", "right") else {"data_stagger": True}


def timeline_side(align, index):
    """Which side of the line entry number index sits on."""
    if align in ("left", "right"):
        return "timeline-end" if align == "left" else "timeline-start"
    return "timeline-start" if index % 2 == 0 else "timeline-end"


# Settings > Appearance > Blog layout > What each post shows (routes.public.roll_shows)
MINIMAL_GROUPS = {"none": "None — the full date on every post",
                  "year": "Year — a heading for each year; dates show the day and month",
                  "month": "Month — a heading for each month; dates show the day"}
LIST_COVER_SIDES = {"left": "Left of the text", "right": "Right of the text"}
ROLL_PARTS = {"cover": "Cover image", "date": "Date", "reading": "Reading time", "summary": "Summary", "tags": "Tags"}

# Settings > Appearance > Tags and archive: where each panel goes
SIDE_PLACES = {"under": "Under the posts", "left": "On the left", "right": "On the right", "off": "Off"}


def _see_all(label, href):
    # under the panel, not its title: a link inside the button that folds
    # the panel was two controls in one, and a small target to tap
    return P(A(label, href=href, cls="link link-hover inline-flex items-center py-1 pointer-coarse:min-h-11"),
             cls="text-sm mt-2")


def _extra_panel(key, narrow):
    if key == "side_tags" and (counts := posts.tag_counts()):
        return SettingsPanel(i18n.t("Tags"), TagCloud(counts, limit=30, narrow=narrow),
                             _see_all(i18n.t("All tags"), "/tags"), key="side-tags")
    if key == "side_archive" and (months := month_counts(posts.list_roll_all(columns="created_at"))):
        return SettingsPanel(i18n.t("Archive"), ArchiveLinks(months, limit=12, narrow=narrow),
                             _see_all(i18n.t("Every month"), "/archive"), key="side-archive")
    if key == "side_author" and (panel := AuthorPanel(settings.get_all())):
        return SettingsPanel(i18n.t("Author"), panel, key="side-author")
    return None


def AuthorPanel(s):
    """About the author, for a side panel: photo, name, the line about
    them and their links - the same as under a post, made to fit a margin."""
    if not s.get("author_bio") and not s.get("author_name"):
        return None
    avatar = s.get("author_avatar_url")
    return Div(
        Div(Div(Img(src=avatar, alt="", cls="object-cover"), cls="w-12 rounded-full"), cls="avatar")
        if avatar else None,
        P(s.get("author_name") or s["site_title"], cls="font-semibold text-sm"),
        P(s.get("author_bio"), cls="text-sm text-base-content/70") if s.get("author_bio") else None,
        SocialLinks(s, icons=True, cls_extra="!mt-1"),
        cls="flex flex-col gap-1.5"
    )


# Settings > Appearance > Side panels: each panel's place, and where it shows
SIDE_KEYS = ("side_tags", "side_archive", "side_author")
SIDE_WHERE = {"roll": "The blog roll", "posts": "Posts", "pages": "Pages"}


def side_order(settings) -> list:
    """The side panels in the admin's order (Settings > Blog layout > Side
    panels) - any it doesn't name after them."""
    saved = [k.strip() for k in (settings.get("side_order") or "").split(",") if k.strip() in SIDE_KEYS]
    return list(dict.fromkeys(saved + list(SIDE_KEYS)))


def side_where(settings, key) -> set:
    """Where a side panel shows: the blog roll, posts, pages (side_tags_where...)."""
    return set((settings.get(f"{key}_where") or "").split(",")) & set(SIDE_WHERE)


def side_places(settings, where="roll", shown=True, own="") -> dict:
    """Where each side panel goes on this page: {key: off/under/left/right},
    in the admin's order. A post's own choice (own, posts.clean_sides:
    "tags=left") wins, wherever Settings shows the panel; otherwise
    Settings' place, where it's set to show (side_where). shown: False
    when the post leaves side panels out altogether (its Show list)."""
    if not shown:
        return {}
    mine = dict(part.split("=", 1) for part in (own or "").split(",") if "=" in part)
    places = {}
    for key in side_order(settings):
        if mine.get(key.removeprefix("side_")) in SIDE_PLACES:
            places[key] = mine[key.removeprefix("side_")]
        elif settings.get(key) in SIDE_PLACES and where in side_where(settings, key):
            places[key] = settings.get(key)
    return places


def SidePanels(settings, toc=None, toc_side=None, where="roll", shown=True, beside=True, own=""):
    """The panels around a column: a post's contents, and the tag cloud,
    archive links and author (SIDE_KEYS), each in its place where it's set
    to show - the blog roll, posts or pages (side_where). shown: False for
    a post or page that leaves them out (its Show list's Side panels).
    Returns (columns, after): the Beside columns, for the top of the
    `relative` container - on each side, the contents first, then the
    others - and a block for after the content.

    Where a side has no room, the contents stay at the top of the post
    (Beside's own fallback) but the others show in `after` instead:
    hidden in the column (data-beside-only), and their copy in `after`
    hidden once their column is beside (placeSidePanels).

    beside: False for a wide page (Page width: Wide, a project, a landing page), which runs
    out to where the panels would go - the tag cloud, archive and author
    show after it instead, as on a phone."""
    places = side_places(settings, where, shown, own)
    columns = []
    for side in ("left", "right"):
        content = [toc] if toc is not None and toc_side == side else []
        for key, place in places.items():
            if beside and place == side and (panel := _extra_panel(key, narrow=True)):
                content.append(Div(panel, data_beside_only=True, cls="hidden group-data-[beside]/side:block"))
        if content:
            columns.append(Beside(*content, side=side, cls="mb-6" if toc_side == side else "",
                                  plain=settings.get("side_plain") == "1"))
    after = [Div(panel, data_side_fallback=place if place != "under" and beside else None, cls="print:hidden")
             for key, place in places.items() if place in ("under", "left", "right")
             and (panel := _extra_panel(key, narrow=False))]
    return columns, (Div(*after, cls="flex flex-col gap-3 mt-8 print:hidden") if after else None)


def TagBadge(tag: str, small=False):
    # a neutral badge-soft: its text is base-content, readable on every
    # theme - a coloured one keeps the colour as its text, which nearly
    # vanishes on cupcake and pastel
    # whitespace-nowrap - squeezed on a phone, a long tag broke inside its badge
    return A(f"#{tag}", href=tag_url(tag),
             cls=f"badge badge-soft {'badge-sm' if small else ''} hover:underline whitespace-nowrap")


def TagList(tags_csv: str, small=False):
    """small - in a list of posts, where the tags support the titles
    instead of competing with them; the post itself keeps the full size."""
    tags = [t.strip() for t in tags_csv.split(",") if t.strip()]
    if not tags:
        return None
    # flex-wrap + gap, not a per-tag mr-1 - mr-1 only ever gave
    # horizontal spacing, so tags sat right on top of each other
    # vertically the moment they wrapped to a second line. Matches the
    # flex-wrap gap-* pattern already used everywhere else in the app
    # for a wrapping row of small elements (ShareButtons, the editor's
    # own tag-suggestion chips, SocialLinks' icon row) - this was the
    # one place still doing it the old way.
    return Div(*[TagBadge(t, small) for t in tags], cls="flex flex-wrap gap-1 mt-2")


def SocialLinks(settings, cls_extra="", icons=False):
    """icons=False (the default) keeps the original plain-text link row.
    icons=True (the footer, and AuthorBio on post pages) swaps each
    link's visible content for its real brand mark instead - a generic
    globe/link glyph for Website and any custom extra_social_links
    entry, since those aren't one specific brand.

    Order follows ordered_social_platforms - whatever the admin's set
    under Author > Social links (the same up/down reordering
    ShareButtons' own platform subset follows too, on a post page)."""
    fixed = [(settings.get(f"social_{key}"), label, icon)
             for key, label, icon, _ in ordered_social_platforms(settings)]
    extra = []
    for line in (settings.get("extra_social_links") or "").splitlines():
        if "|" not in line:
            continue
        # Label|URL, or Label|URL|icon_key (EXTRA_LINK_ICONS) - the icon
        # field is new and optional, so an older 2-field line (or a typo'd/
        # unknown key) still works, just with the original plain-link glyph
        # every one of these used to be stuck with regardless of icon field.
        parts = line.split("|", 2)
        label, url = parts[0].strip(), parts[1].strip()
        icon_key = parts[2].strip().lower() if len(parts) > 2 else ""
        if label and url:
            extra.append((url, label, EXTRA_LINK_ICONS.get(icon_key, LINK_SVG)))

    # extra (free-text, not one of the 9 fixed platforms) always comes
    # last, unordered among themselves - there's no reorder mechanism
    # for these, and they weren't asked to have one
    present = [(url, label, icon) for url, label, icon in fixed if url] + extra
    if not present:
        return None
    if icons:
        # mt-2, matching the text-mode branch below - this row sits
        # right under a paragraph of bio text, and needs the same
        # breathing room from it that the text version already gets
        # daisyUI's square buttons: 44 px on a touch screen (touch-size,
        # input.css), 8 px apart (web.dev)
        return Div(*[A(icon, href=url, target="_blank", rel="me", aria_label=label,
                       cls="btn btn-ghost btn-square btn-sm text-base-content/70 tooltip",
                       data_tip=label)
                     for url, label, icon in present],
                   # left-aligned, each icon's own edge lines up with the text
                   # beside it, not its button's
                   cls=f"flex flex-wrap items-center gap-1 pointer-coarse:gap-2 mt-2 [&.justify-start]:-ms-2 "
                       f"pointer-coarse:[&.justify-start]:-ms-3.5 {cls_extra}")
    return Div(*[A(label, href=url, target="_blank", rel="me",
                   cls="link link-hover text-sm text-base-content/70 mr-3")
                 for url, label, icon in present], cls=f"mt-2 {cls_extra}")


# one first-party "share this URL" intent per share-capable platform
# (SOCIAL_PLATFORMS' own 4th field) - kept separate from SOCIAL_PLATFORMS
# itself since these are share-intent URL templates, not brand/display
# info, and nothing outside ShareButtons needs them. mastodon isn't
# here - it can't be a plain href (see shareToMastodon, MASTODON_SHARE_JS
# in app.py), so ShareButtons special-cases it below instead.
_SHARE_INTENTS = {
    "twitter": lambda u, t: f"https://twitter.com/intent/tweet?url={u}&text={t}",
    "facebook": lambda u, t: f"https://www.facebook.com/sharer/sharer.php?u={u}",
    "linkedin": lambda u, t: f"https://www.linkedin.com/sharing/share-offsite/?url={u}",
    "bluesky": lambda u, t: f"https://bsky.app/intent/compose?text={t}%20{u}",
    "threads": lambda u, t: f"https://www.threads.net/intent/post?text={t}%20{u}",
}


def ShareButtons(post_url: str, title: str, settings):
    """A button per share-capable platform (X/Facebook/Mastodon/Bluesky/
    LinkedIn - see SOCIAL_PLATFORMS) the author has actually filled in,
    in the exact same order as their social links - reordering one
    reorders both, since both read from ordered_social_platforms.
    GitHub/Instagram/YouTube/Website are real social links but have no
    "share a post" semantics at all, so they never show up here even if
    configured - only in SocialLinks. Email and Copy link always come
    last, in that order, regardless of the author's own reordering -
    neither is tied to one of the author's own social platforms (Email
    doesn't require the author to have listed one at all; Copy link
    isn't a platform), so there's nothing for reordering to apply to."""
    from urllib.parse import quote
    encoded_url, encoded_title = quote(post_url, safe=""), quote(title, safe="")

    def _button(key, label, icon):
        if key == "mastodon":
            # data attributes, not an interpolated JS string - a title
            # with an apostrophe would otherwise end the string early
            return Button(label, type="button", cls=SHARE_PILL, data_url=post_url, data_title=title,
                          **on("click", "shareToMastodon", post_url, title))
        return A(label, href=_SHARE_INTENTS[key](encoded_url, encoded_title), target="_blank", cls=SHARE_PILL)

    platform_buttons = [
        _button(key, label, icon)
        for key, label, icon, share_capable in ordered_social_platforms(settings)
        if share_capable and settings.get(f"social_{key}")
    ]
    mail_subject = quote(title, safe="")
    mail_body = quote(post_url, safe="")
    return Div(
        Span(i18n.t("Share"), cls="text-sm text-base-content/60 me-1"),
        *platform_buttons,
        A(i18n.t("Email"), href=f"mailto:?subject={mail_subject}&body={mail_body}", cls=SHARE_PILL),
        Button(i18n.t("Copy link"), type="button", cls=SHARE_PILL,
               data_copy=post_url, data_copied=i18n.t("Copied")),
        role="group", aria_label=i18n.t("Share"),
        cls="flex flex-wrap items-center gap-2 print:hidden"
    )


# Share's buttons, the same pill as the reactions beside them
SHARE_PILL = "btn btn-sm btn-outline border-base-300 hover:border-primary"


def ReactAndShare(reacts, share):
    """One row at the end of a post: the reactions on the left, Share on
    the right, the one under the other on a phone - or whichever of them
    shows."""
    parts = [p for p in (reacts, share) if p is not None]
    if not parts:
        return None
    return Div(*parts, cls="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between "
                           "print:hidden")


# support/donation platforms - key (matches settings.py's
# "support_{key}"), the button label, and a placeholder showing the
# kind of address that belongs in the field
SUPPORT_PLATFORMS = [
    ("kofi", "Ko-fi", "https://ko-fi.com/you"),
    ("buymeacoffee", "Buy Me a Coffee", "https://buymeacoffee.com/you"),
    ("github", "GitHub Sponsors", "https://github.com/sponsors/you"),
    ("patreon", "Patreon", "https://patreon.com/you"),
    ("liberapay", "Liberapay", "https://liberapay.com/you"),
    ("paypal", "PayPal", "https://paypal.me/you"),
]


def parse_link_lines(text: str) -> list:
    """"Label|https://url" lines -> [(label, url)], skipping anything
    malformed - the one format every free-text link list here uses."""
    out = []
    for line in (text or "").splitlines():
        if "|" not in line:
            continue
        label, url = (p.strip() for p in line.split("|", 2)[:2])
        url = safe_url(url)
        if label and url:
            out.append((label, url))
    return out


def support_links(settings) -> list:
    return [(label, settings.get(f"support_{key}")) for key, label, _ in SUPPORT_PLATFORMS
            if safe_url(settings.get(f"support_{key}") or "")]


def SupportButtons(settings, block=False):
    """The author's donation links, under a post with their own eyebrow
    label; block=True is the full-width button version for the /links
    page."""
    links = support_links(settings)
    if not links:
        return None
    message = settings.get("support_message")
    if block:
        return Div(P(message, cls="text-sm text-base-content/70") if message else None,
                   *[A(label, href=url, target="_blank", rel="noopener", cls="btn btn-block")
                     for label, url in links], cls="flex flex-col gap-2 w-full")
    return Div(
        P(i18n.t("Support"), cls="text-base font-semibold text-accent mb-2"),
        P(message, cls="text-sm text-base-content/70 mb-2") if message else None,
        Div(*[A(label, href=url, target="_blank", rel="noopener", cls="btn btn-xs btn-soft")
              for label, url in links], cls="flex gap-2 flex-wrap"),
        cls="print:hidden"
    )


def AuthorBio(settings):
    # photo, name and bio, no links - quieter than the footer's, since it
    # sits right after the post
    if not settings.get("author_bio") and not settings.get("author_name"):
        return None
    avatar = settings.get("author_avatar_url")
    return Div(
        # same eyebrow-label treatment as ShareButtons/RelatedPosts/
        # Comments - one consistent grammar for every labeled section
        # stacked below a post, not a heavier heading style here and
        # a lighter one there.
        P(i18n.t("Author"), cls="text-base font-semibold text-accent mb-2"),
        Div(
            # self-start on the photo too: daisyUI's .avatar centres itself,
            # whatever the row says
            Div(Div(Img(src=avatar, alt="", cls="object-cover"), cls="w-12 rounded-full"), cls="avatar self-start") if avatar else None,
            Div(
                P(settings.get("author_name") or settings["site_title"], cls="font-semibold text-sm"),
                P(settings.get("author_bio"), cls="text-sm text-base-content/70") if settings.get("author_bio") else None,
            ),
            cls="flex items-start gap-3"
        ),
    )


def FooterBio(settings):
    """Name + bio only, centered - no avatar. The footer's identity
    block sits in a single centered column now (bio, then socials,
    then links, then copyright), not a left-aligned avatar row, so
    there's no avatar to align against."""
    if not settings.get("author_bio") and not settings.get("author_name"):
        return None
    return Div(
        P(settings.get("author_name") or settings["site_title"], cls="font-semibold text-sm"),
        P(settings.get("author_bio"), cls="text-xs text-base-content/70") if settings.get("author_bio") else None,
    )


def HeroSection(settings):
    """Optional banner above the blog roll, wherever it is (the homepage,
    or /blog when the homepage is a page) - a heading, an optional
    subheading, and a call-to-action button. Renders the same way
    regardless of which roll layout is chosen, since it's just
    prepended content above whatever PostRoll draws.

    Uses DaisyUI's actual hero/hero-content/hero-overlay component
    structure rather than a hand-rolled bordered box - this is
    literally what that component exists for."""
    if settings.get("banner_enabled") != "1":
        return None
    heading = settings.get("banner_heading")
    if not heading:
        return None

    image = settings.get("banner_image_url")
    subheading = settings.get("banner_subheading") or settings.get("tagline")
    width = settings.get("banner_width") if settings.get("banner_width") in ("wide", "full") else "column"
    cta_text = settings.get("banner_button_text")
    cta_url = settings.get("banner_button_url")

    hero_box = Div(
        Div(cls="hero-overlay") if image else None,
        Div(
            Div(
                H1(heading, cls="text-4xl md:text-5xl font-bold"),
                # without one of its own, the site's tagline
                P(subheading, cls="py-4 text-lg") if subheading else None,
                A(cta_text, href=cta_url or "#", cls="btn btn-primary") if cta_text and cta_url else None,
                cls="max-w-lg"
            ),
            # below a floating header (--flush-top): the room is the content's,
            # not the banner's - daisyUI's hero is a grid, and its overlay
            # only covers the grid's area, so padding on the banner left a
            # strip of photo above the overlay, lighter, with a line under it
            cls=f"hero-content text-center pt-[calc(1rem+var(--flush-top,0px))] {'text-neutral-content' if image else ''}"
        ),
        style=f"background-image: url({image});" if image else None,
        # rounded-box, not a fixed rounded-lg - follows the theme's own
        # --radius-box token (0 on cyberpunk, 2rem on silk, etc) instead
        # of a hardcoded 0.5rem that only happens to look right on some
        # themes. overflow-hidden matters here, not just decorative -
        # hero-overlay is a plain square 100%x100% box stacked in the
        # same grid cell as the background image, so without it the
        # overlay's sharp corners poke past the parent's rounded ones.
        # its height is what makes it read as a banner rather than a tall
        # alert box - and behind a floating header (--flush-top,
        # flushEdges) it's taller by the header, so what's under it keeps
        # its room
        cls=f"hero bg-base-200 {'' if width == 'full' else 'rounded-box'} overflow-hidden "
            "min-h-[calc(26rem+var(--flush-top,0px))]"
    )
    # as wide as the column, out to the side panels, or edge to edge
    # (Settings > Banner)
    # "open": it opens the page, drawn there from the start (FLUSH_GUESS)
    return Div(Breakout(hero_box, width, settings), data_flush="open" if width == "full" else None, cls="mb-8")


def TableOfContents(toc_html, style="top", fold="auto"):
    """A folding panel like Settings' own sections, remembered open or
    folded per browser. fold - pages.TOC_FOLDS: whether each ## folds
    its ###s away, and in "auto" only the one being read stays open.

    "side" / "right": in the margin beside the post (Beside). A small
    screen, large text or a wide page (Photo essay) keeps it at the top."""
    if not toc_html:
        return None
    panel = toc_panel(toc_html, fold)
    if style not in ("side", "right"):
        return Div(panel, cls="mb-6")
    return Beside(panel, side="right" if style == "right" else "left", cls="mb-6",
                  plain=settings.get("side_plain") == "1")


def toc_panel(toc_html, fold="auto"):
    """The contents' folding panel on its own, for TableOfContents and
    SidePanels. Numbered 1, 2, 2.1 when Settings asks (input.css)."""
    if fold == "off":
        toc_html = re.sub(r"</?(?:details|summary)[^>]*>", "", toc_html)
    # data-toc - READING_JS's scrollspy finds its links through this
    return SettingsPanel(i18n.t("Contents"),
                         Div(NotStr(toc_html), data_toc=fold,
                             data_toc_numbers=settings.get("toc_numbers") == "1" or None, cls="text-sm"),
                         key="toc")


# Beside's plain panels: the collapse cards' fill and border go
SIDE_PLAIN = "data-[beside]:[&_.collapse]:bg-transparent data-[beside]:[&_.collapse]:border-transparent"


def Beside(*content, side="left", cls="", width="data-[beside]:w-52", room=None, plain=False, **attrs):
    """Panels in the margin beside the column (the parent is `relative`),
    following the reader down between the header and a fixed footer
    (--header-h, --footer-h) - but only where the margin has room for
    them (placeSidePanels, app.py, sets data-beside). Where it hasn't, they
    stay where they are in the page, in its flow; cls is for then.
    width and room (in rem, the margin it needs) are for a wider panel.
    plain (Settings' side_plain) - no card around them in the margin, so
    they blend into the page; in the flow they keep it."""
    # each side spelled out whole - Tailwind only builds classes it can read
    # 2.5rem from the column: room between the reading and what's beside it
    edge = ("data-[beside]:left-full data-[beside]:ml-10" if side == "right"
            else "data-[beside]:right-full data-[beside]:mr-10")
    return Div(
        # scrolling inside, it fades at its foot like any list in a box
        Div(*content, data_scroll_hint=True,
            cls=f"flex flex-col gap-6 {SCROLLS} group-data-[beside]/side:sticky group-data-[beside]/side:overflow-y-auto "
                          "group-data-[beside]/side:top-[calc(var(--header-h,0px)+1.5rem)] "
                          "group-data-[beside]/side:max-h-[calc(100vh-var(--header-h,0px)-var(--footer-h,0px)-3rem)]"),
        # placed straight away, not after the whole page loads, so it doesn't jump
        Script("placeSidePanels()", nonce=csp.NONCE),
        data_side_panel=side, data_side_room=room, **attrs,
        # pb: the panel stops short of the page's foot, not flush on the footer
        cls=f"group/side print:hidden {cls} data-[beside]:m-0 data-[beside]:absolute data-[beside]:inset-y-0 data-[beside]:pb-6 "
            f"{edge} {width} "
            f"{SIDE_PLAIN if plain else ''}".strip()
    )


def RelatedPosts(posts_list, relative_dates=False):
    """posts.related_posts() already caps this at 3 - matches the
    3-column grid below exactly, so on a wide screen every related
    post sits in one row, side by side, none left dangling alone on
    its own row.

    Cards, not a plain link list - same card grammar the homepage's
    "Cards" roll layout already uses (card card-border bg-base-100,
    same title/date/summary/tags shape) minus the cover-image figure,
    which is what makes these read as minimal rather than a second
    full post-card grid competing with the post the reader's already
    on."""
    if not posts_list:
        return None
    return Div(
        H2(i18n.t("Related posts"), cls="text-base font-semibold text-accent mb-2"),
        Div(*[
            Div(
                Div(
                    H3(A(p["title"], href=f"/post/{p['slug']}", cls="link link-hover card-title text-sm")),
                    Div(format_date(p["created_at"], relative_dates), cls="text-xs text-base-content/50"),
                    (teaser := posts.teaser(p)) and P(teaser, cls="text-sm text-base-content/70 line-clamp-2"),
                    TagList(p["tags"], small=True),
                    cls="card-body p-3"
                ),
                cls="card card-border bg-base-100"
            ) for p in posts_list
        # each card opens from anywhere on it, as a list's posts do (ROW_LINKS_JS)
        ], data_click_rows=True, cls="grid grid-cols-1 sm:grid-cols-3 gap-4 [&_.card]:cursor-pointer"),
        cls="print:hidden"
    )


def Breadcrumbs(crumbs):
    """daisyUI breadcrumbs - [(label, href)], the last one being the page
    itself (href None, not a link). Also emits the same trail as
    schema.org BreadcrumbList data, which search engines can show in
    place of the bare URL."""
    import json
    from soloblog import config
    if len(crumbs) < 2:
        return None
    items = [Li(A(label, href=href, cls="link link-hover") if href else
                Span(label, cls="truncate max-w-[12rem] sm:max-w-sm", aria_current="page"))
             for label, href in crumbs]
    data = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": label,
             **({"item": config.BASE_URL + href} if href else {})}
            for i, (label, href) in enumerate(crumbs)
        ],
    }
    # "</" can't appear inside a <script>, whatever a title contains
    ld = json.dumps(data).replace("</", "<\\/")
    return Div(
        # ft("nav"), not Nav() - this module's own Nav() is the site header
        # a trail too long for a phone still swipes, without a scrollbar drawn under it
        ft("nav", Ul(*items), aria_label=i18n.t("Breadcrumb"),
           cls="breadcrumbs text-sm text-base-content/60 py-0 [scrollbar-width:none]"),
        Script(NotStr(ld), type="application/ld+json"),
        cls="mb-2"
    )


def SeriesNav(current_slug, siblings):
    if len(siblings) < 2:
        return None
    idx = next((i for i, p in enumerate(siblings) if p["slug"] == current_slug), None)
    if idx is None:
        return None
    total = len(siblings)
    prev_p = siblings[idx - 1] if idx > 0 else None
    next_p = siblings[idx + 1] if idx < total - 1 else None
    return Div(
        Div(
            P(i18n.t("Part {n} of {total} in ", n=idx + 1, total=total),
              A(siblings[0]["series_name"], href=f"/series/{posts.series_slug(siblings[0]['series_name'])}",
                cls="link link-hover"),
              cls="text-base font-semibold text-accent mb-2"),
            Div(
                # 44 px tall on a touch screen, as a footer's links are
                A(f"← {prev_p['title']}", href=f"/post/{prev_p['slug']}", cls="link link-hover text-sm inline-flex items-center pointer-coarse:min-h-11")
                if prev_p else Span(),
                A(f"{next_p['title']} →", href=f"/post/{next_p['slug']}", cls="link link-hover text-sm ml-auto inline-flex items-center pointer-coarse:min-h-11")
                if next_p else Span(),
                cls="flex justify-between gap-4"
            ),
            cls="card-body p-4"
        ),
        cls="card card-border bg-base-100"
    )



def CommentsSection(*content, **attrs):
    """Visually distinct from the post itself - a card, not just more
    text flowing directly under the article."""
    return Div(Div(*content, cls="card-body p-5"), cls="card card-border bg-base-100", **attrs)


def PinnedLinkColumns(pinned_tree, s):
    """The Columns footer: a page with pages under it is a column, its
    title the heading - as product sites group Product, Help, Legal. Pages
    on their own, and the site's own (Archive, Contact), share a column of
    their own, first. pinned_tree: posts.menu_items for the footer."""
    link = f"link link-hover text-sm text-base-content/70 {TOUCH_LINK}"
    head = f"link link-hover text-sm font-semibold {TOUCH_LINK}"

    def under(item):
        # the pages under a page, or under one of the site's own (a SiteItem)
        return getattr(item, "children", ()) if isinstance(item, str) else item[1]
    alone = [item for item in pinned_tree if not under(item)]
    columns = [Ul(*[Li(SiteLink(s, "footer", i, cls=link) if isinstance(i, str) else PageLink(i[0], cls=link))
                    for i in alone], cls="flex flex-col gap-1.5")] if alone else []
    columns += [Div(SiteLink(s, "footer", i, cls=head) if isinstance(i, str) else PageLink(i[0], cls=head),
                    Ul(*[Li(PageLink(c, cls=link)) for c in under(i)], cls="flex flex-col gap-1.5 mt-2"))
                for i in pinned_tree if under(i)]
    return Div(*columns, cls="grid grid-cols-2 sm:grid-cols-[repeat(auto-fit,minmax(9rem,1fr))] gap-x-6 gap-y-8 "
                             "flex-1 min-w-0") if columns else None


def PinnedLinksRow(pinned_tree, s):
    """Footer-pinned pages (About, Privacy Policy, Terms...) and the site's
    own (Archive, Contact) - always plain, flat daisyUI Footer-style links
    (`link link-hover`, matching daisyUI's own Footer docs examples),
    parent and child alike, no dropdown/submenu here at all - deliberately
    different from the header nav, which keeps its own real PinnedNavItem
    submenu dropdown for a page with children, untouched by this.
    pinned_tree: posts.menu_items for the footer."""
    if not pinned_tree:
        return None
    cls = f"link link-hover text-xs {TOUCH_LINK}"
    items = []
    for item in pinned_tree:
        if isinstance(item, str):
            items.append(SiteLink(s, "footer", item, cls=cls))
            # the pages nested under it follow it, as a page's sub-pages do
            items += [PageLink(c, cls=cls) for c in getattr(item, "children", ())]
            continue
        items.append(PageLink(item[0], cls=cls))
        for c in item[1]:
            items.append(PageLink(c, cls=cls))
    return Div(*items, cls="flex flex-wrap items-center gap-x-3 pointer-coarse:gap-x-4")


FOOTER_PIECES = {"bio": "Author bio", "socials": "Social links", "links": "Pinned pages",
                 "note": "Footer note / copyright", "small": "Small print"}
# Settings > Appearance > Footer > Layout
FOOTER_LAYOUTS = {"center": "Centered — one column", "left": "Left-aligned — one column",
                  "split": "Split — some on the left, some on the right",
                  "columns": "Columns — each footer page with the pages under it"}
# in footer_order: where a split footer's right side starts
FOOTER_SPLIT = "|"


def footer_order(settings) -> list:
    """The footer's pieces in the admin's order (Settings > Appearance >
    Footer), any it doesn't name after them - and FOOTER_SPLIT, the
    split layout's line between left and right (after the first two
    unless it's been moved)."""
    saved = [k.strip() for k in (settings.get("footer_order") or "").split(",")
             if k.strip() in FOOTER_PIECES or k.strip() == FOOTER_SPLIT]
    order = list(dict.fromkeys(saved + list(FOOTER_PIECES)))
    if FOOTER_SPLIT not in order:
        order.insert(min(2, len(order)), FOOTER_SPLIT)
    return order


def SiteFooter(settings, logged_in=False, admin_page=False):
    """The footer's pieces in the admin's order, each one a settings
    toggle: one column, centered or left-aligned, or split - the pieces
    before FOOTER_SPLIT on the left and the rest on the right, stacked
    on a phone (footer_layout)."""
    if settings.get("footer_enabled") != "1":
        return None
    footer_style = settings.get("footer_style")
    fixed = footer_style == "fixed"
    floating = footer_style == "floating"
    # frosted glass, not true invisibility - same reasoning as Nav()'s
    # own fill (glass_fill, shared), and the one thing this toggles;
    # border/shadow stay identical to opaque in every style.
    fill = glass_fill(settings)
    # as wide as the header: Wide with a wide header, else the column
    width = MARGIN_WIDTHS.get(settings.get("body_width"), MARGIN_WIDTHS["standard"]) \
        if settings.get("header_width") == "wide" else content_width(settings)

    layout = settings.get("footer_layout") if settings.get("footer_layout") in FOOTER_LAYOUTS else "center"
    bio = FooterBio(settings) if settings.get("footer_show_bio") == "1" else None
    footer_pins = posts.menu_items(settings, posts.list_pinned_tree_footer(), "footer") \
        if settings.get("footer_show_pages") == "1" else []
    # a small-print link to a page that is already among them is left out
    footed = {posts.SITE_PAGES[i][0] for i in footer_pins if isinstance(i, str)}
    # ft('nav', ...) here, not Nav(...) - Nav is already this module's
    # own nav-building function, calling it directly would collide.
    links = ft("nav", PinnedLinksRow(footer_pins, settings)) if footer_pins else None
    disclaimer = P(settings.get("footer_note") or f"© {settings['site_title']}",
                   cls="text-xs pointer-coarse:text-sm text-base-content/50") if settings.get("footer_show_note") == "1" else None

    # small print under everything else: the visitor's cookie choices
    # (only when there's a consent banner to reopen) and the optional
    # "Powered by Soloblog" credit
    from soloblog import ads
    from soloblog import config
    small = [
        *([A(i18n.t("Archive"), href="/archive", cls=f"link link-hover {TOUCH_LINK}"),
           A(i18n.t("Tags"), href="/tags", cls=f"link link-hover {TOUCH_LINK}"),
           A("RSS", href="/rss", cls=f"link link-hover {TOUCH_LINK}")] if settings.get("footer_show_browse") == "1" else []),
        A(i18n.t("Newsletter"), href="/newsletter", cls=f"link link-hover {TOUCH_LINK}") if newsletter.mode(settings) else None,
        # never for the admin - the banner (and what it gates) never loads for them
        Button(i18n.t("Cookie choices"), type="button", cls=f"link link-hover {TOUCH_LINK}", **on("click", "openConsent"))
        if ads.consent_needed(settings) and not logged_in else None,
        Span(i18n.t("Powered by "), A("Soloblog", href=config.PROJECT_URL, target="_blank", rel="noopener",
                              cls=f"link link-hover {TOUCH_LINK}"), cls=f"{TOUCH_LINK} gap-1")
        if settings.get("footer_show_powered_by") == "1" else None,
    ]
    small = [x for x in small if x is not None and x.attrs.get("href") not in footed]

    def piece(key, justify):
        """One piece, its rows lined up with its column (justify)."""
        if key == "socials" and settings.get("footer_show_socials") == "1":
            # icons=True: real brand marks, the footer's compact row of
            # icons (AuthorBio on posts keeps plain text). !mt-0 - its own
            # margin assumes it sits under a bio; here the column's gap does it
            return SocialLinks(settings, cls_extra=f"!mt-0 {justify}", icons=True)
        if key == "small" and small:
            return Div(*small, cls=f"flex flex-wrap items-center {justify} gap-x-3 pointer-coarse:gap-x-4 gap-y-1 "
                                   "pointer-coarse:gap-y-0 text-xs pointer-coarse:text-sm text-base-content/50")
        return {"bio": bio, "links": links, "note": disclaimer}.get(key)

    order = footer_order(settings)
    cut = order.index(FOOTER_SPLIT)
    align = {"center": ("items-center text-center", "justify-center"),
             "left": ("items-start text-left", "justify-start")}
    if layout == "columns":
        # what comes before the pages beside them (you, your links), the
        # pages in columns, and what's after along the bottom
        keys = [k for k in order if k != FOOTER_SPLIT]
        at = keys.index("links")
        side = [p for k in keys[:at] if (p := piece(k, "justify-start")) is not None]
        grid = PinnedLinkColumns(footer_pins, settings) if footer_pins else None
        foot = [p for k in keys[at + 1:] if (p := piece(k, "justify-start sm:justify-end")) is not None]
        top = [Div(*side, cls="flex flex-col items-start text-left gap-3 min-w-0 lg:max-w-xs")] if side else []
        top += [ft("nav", grid, cls="flex-1 min-w-0")] if grid else []
        pieces = [Div(*top, cls="flex flex-col lg:flex-row gap-8 lg:gap-16")] if top else []
        if foot:
            pieces.append(Div(*foot, cls="flex flex-col sm:flex-row sm:flex-wrap sm:justify-between items-start "
                                         "sm:items-center gap-3 border-t-[length:var(--border)] border-base-200 pt-4"))
    elif layout == "split":
        left = [p for k in order[:cut] if (p := piece(k, "justify-start")) is not None]
        right = [p for k in order[cut + 1:] if (p := piece(k, "justify-start sm:justify-end")) is not None]
        columns = [Div(*left, cls="flex flex-col items-start text-left gap-3 min-w-0")] if left else []
        if right:
            columns.append(Div(*right, cls="flex flex-col items-start text-left sm:items-end sm:text-right "
                                           "gap-3 min-w-0"))
        pieces = columns
    else:
        pieces = [p for k in order if k != FOOTER_SPLIT and (p := piece(k, align[layout][1])) is not None]
    if not pieces:
        return None

    # As Nav(): the outer element edge to edge, its contents as wide as
    # the column; floating, the inner one is the pill. A plain flex column,
    # not daisyUI's .footer - that's a grid for columns of links.
    pill_cls = f" rounded-box border border-base-300 shadow-lg {fill}" if floating else ""
    arrange = ("flex flex-col sm:flex-row sm:justify-between gap-6" if layout == "split"
               else "flex flex-col gap-8" if layout == "columns" else f"flex flex-col {align[layout][0]} gap-3")
    inner = Div(*pieces, cls=f"{arrange} {width} mx-auto px-4 {'py-10' if layout == 'columns' else 'py-5'}{pill_cls}")
    if floating:
        # sm: - on a phone it wraps to a third of the screen, so there
        # it stays at the end of the page
        outer_cls = "text-base-content sm:fixed sm:bottom-4 sm:inset-x-0 z-20 px-4 max-sm:pb-4"
    else:
        # always the plain border-token line here, fixed or not - unlike
        # Nav()'s top edge, a bottom-fixed bar can't borrow daisyUI's real
        # shadow-sm for this: every standard Tailwind shadow utility casts
        # *downward* (light-from-above), so on an element already pinned to
        # the bottom of the viewport that shadow renders off-screen and is
        # never actually seen. A border has no such direction problem - it
        # sits right on the bar's own edge either way - so it does the job
        # correctly in both modes instead of faking a shadow that wouldn't
        # be visible, or hand-authoring an upward-only one ourselves.
        outer_cls = f"{fill} text-base-content border-t-[length:var(--border)] border-base-200"
        if fixed:
            outer_cls += " sm:fixed sm:bottom-0 sm:left-0 sm:right-0 z-20"
    return Footer(inner, cls=f"{outer_cls} print:hidden")


def ToastContainer():
    """One fixed container per page - showToast() (see TOAST_JS) just
    appends alerts into this, no per-call setup needed. This is the one
    standard toast system for the whole app - every server-side action
    that redirects with ?toast=message drives it (_toast_redirect,
    repeated per-route), and it's the only place a toast can render.

    toast-center, not toast-end - centered on the page, not tucked in a
    corner."""
    return Div(id="toast-container", cls="toast toast-center toast-bottom z-50")


def ConfirmDialog(settings):
    """One shared confirm dialog per page, DaisyUI-styled instead of
    the browser's native confirm() - confirmAction(message, onYes) in
    CONFIRM_JS is the one, standard way anything in the app asks
    'are you sure?' instead of each delete button rolling its own."""
    return Dialog(
        Div(
            P(id="confirm-message", cls="mb-4"),
            Div(
                Button(X_SVG, Span("Cancel", cls="ml-1"), type="button", cls="btn btn-sm",
                       data_close_dialog="confirm-dialog"),
                Button(CHECK_SVG, Span("Confirm", id="confirm-yes-label", cls="ml-1"), id="confirm-yes-btn", type="button",
                       cls="btn btn-sm btn-error"),
                # only when there's something to save first - leaving a
                # page with unsaved changes (confirmAction's onSave)
                Button(CHECK_SVG, Span("Save", id="confirm-save-label", cls="ml-1"), id="confirm-save-btn",
                       type="button", hidden=True, cls="btn btn-sm btn-primary"),
                # three don't fit a phone's row: full width, Save on top
                cls="modal-action max-sm:data-[stack]:flex-col-reverse max-sm:data-[stack]:items-stretch"
            ),
            cls=f"modal-box {glass_fill(settings)}"
        ),
        Form(Button(cls="cursor-default", aria_label=i18n.t("Close")), method="dialog", cls="modal-backdrop"),
        id="confirm-dialog", aria_labelledby="confirm-message", cls="modal"
    )


def ScrollToTopButton():
    """Back to top: it fades in once you've scrolled down (a setting,
    SCROLL_TOP_JS), in the corner where every site keeps it - over the
    footer too. Above the background sound's button when a page has one,
    and above the save bar while it's pinned there.

    btn-neutral: a plain button is base-200, the page's own colour, and
    disappeared into it. Neutral isn't an accent, so primary stays the
    page's one main action."""
    return Button(
        NotStr('<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" '
               'viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">'
               '<path stroke-linecap="round" stroke-linejoin="round" d="M5 15l7-7 7 7" /></svg>'),
        id="scroll-top-btn", type="button", aria_label=i18n.t("Back to top"), **on("click", "scrollToTop"),
        # above a bar pinned to the foot - the save bar while there's
        # something unsaved - as floating buttons do in every app
        cls="btn btn-neutral btn-circle btn-sm fixed bottom-6 [html[data-sound]_&]:bottom-16 "
            "[html[data-unsaved]_&]:bottom-20 right-6 z-20 opacity-0 "
            "pointer-events-none transition-opacity tooltip tooltip-left", data_tip=i18n.t("Back to top")
    )
