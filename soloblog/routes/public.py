import logging
from fasthtml.common import *
from xml.sax.saxutils import escape
from urllib.parse import quote
import mimetypes
import os
import json
import secrets

from soloblog import cards
from soloblog import config
from soloblog import storage
from soloblog import ads
from soloblog import captcha
from soloblog import extcomments
from soloblog import i18n
from soloblog import newsletter
from soloblog import members
from soloblog import posts
from soloblog import settings
from soloblog import comments
from soloblog import images
from soloblog import auth
from soloblog import ratelimit
from soloblog import notify
from soloblog import mail
from soloblog import replymail
from soloblog import reactions
from soloblog import pages
from soloblog import translate
from soloblog import tz
from soloblog.render import new_tab_links, render_post, render_comment, reading_time, excerpt, format_date, local_datetime, \
    short_date, web_url
from soloblog.ui import (STATUS_BESIDE, STATUS_ROW, TITLE_CLS, LIST_TITLE_CLS, CHEVRON_DOWN_SVG, content_width, RESULT_ROW, RESULT_TITLE, RESULT_ABOUT, RESULT_EMPTY, ROLL_PARTS, Breakout, timeline_cls, timeline_side, timeline_stagger, TagCloud, ArchiveLinks, month_counts, SidePanels, side_places, toc_panel, Layout, TagBadge, ReactionBar, Alert, TagList, AuthorBio, EmptyState, ErrorPage, ListenButton, ReadingProgress, PostScripts, SupportButtons, SoundButton, Breadcrumbs, SocialLinks, parse_link_lines, TableOfContents, RelatedPosts, SearchBox,
                 SeriesNav, ShareButtons, ReactAndShare, EditPostLink, LikeButton, Pagination, CommentsSection,
                 HeroSection, tag_url, RSS_SVG, TRASH_SVG, REPLY_SVG, CHECK_SVG, ReplyBox, ReplyButton, IconAction)
from soloblog.seo import page_meta, article_data
from soloblog.guards import require_login, is_local_path

log = logging.getLogger(__name__)

ar = APIRouter()

# a push-pin (Lucide's, ISC licence), outlined like the other icons
PIN_SVG = NotStr(
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M12 17v5"/><path d="M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h12a1 1 0 '
    '0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V7a1 1 0 0 1 1-1 2 2 0 0 0 0-4H8a2 2 0 0 0 0 4 '
    '1 1 0 0 1 1 1z"/></svg>'
)


def _col(row, key, default=""):
    """A column that older or placeholder comment rows may not have."""
    try:
        return row[key] or default
    except (IndexError, KeyError):
        return default


def WebMentions(slug, s):
    """Favourites and boosts from the fediverse, and webmentions - likes,
    reposts, replies and mentions from other sites - under the comments."""
    from soloblog import fediverse
    from soloblog import webmention
    from urllib.parse import urlsplit
    counts = fediverse.interactions(slug) if fediverse.enabled(s) else {}
    mentions = webmention.for_post(slug) if webmention.receiving(s) else []
    faces = [m for m in mentions if m["kind"] in ("like", "repost", "bookmark")]
    talk = [m for m in mentions if m["kind"] not in ("like", "repost", "bookmark")]
    if not (counts or mentions):
        return None
    tally = []
    if counts.get("like"):
        tally.append(i18n.plural(counts["like"], "{n} favourite", "{n} favourites"))
    if counts.get("boost"):
        tally.append(i18n.plural(counts["boost"], "{n} boost", "{n} boosts"))

    def face(m):
        label = i18n.t({"like": "{name} liked this", "repost": "{name} reposted this",
                        "bookmark": "{name} bookmarked this"}[m["kind"]], name=m["author_name"])
        inner = (Img(src=web_url(m["author_photo"]), alt="", loading="lazy", cls="rounded-full") if web_url(m["author_photo"])
                 else Span(m["author_name"][:1].upper(), cls="text-xs"))
        return A(Div(inner, cls="w-8 rounded-full bg-base-300 flex items-center justify-center"),
                 href=web_url(m["author_url"]) or web_url(m["source"]), target="_blank", rel="nofollow ugc noopener",
                 data_tip=label, aria_label=label, cls="avatar tooltip")
    return CommentsSection(
        H2(i18n.t("Mentions"), cls="text-base font-semibold text-accent mb-2"),
        P(i18n.t("{counts} on the fediverse", counts=" · ".join(tally)), cls="text-sm text-base-content/70 mb-3")
        if tally else None,
        Div(*[face(m) for m in faces], cls="avatar-group -space-x-2 mb-3") if faces else None,
        Ul(*[Li(
            Div(A(m["author_name"], href=web_url(m["author_url"]) or web_url(m["source"]), target="_blank",
                  rel="nofollow ugc noopener",
                  cls="font-medium link link-hover"),
                Span(" " + i18n.t("replied on" if m["kind"] == "reply" else "mentioned this on") + " ",
                     cls="text-base-content/60"),
                A(urlsplit(m["source"]).hostname or m["source"], href=m["source"], target="_blank",
                  rel="nofollow ugc noopener", cls="link link-hover text-base-content/60"),
                cls="text-sm"),
            P(m["content"], cls="text-sm mt-1") if m["content"] else None,
            cls="py-2 border-b-[length:var(--border)] border-base-300 last:border-0") for m in talk])
        if talk else None,
        id="mentions"
    )


def ReplyEmailsCheckbox():
    """Opt-in to "someone replied" emails - only offered when they can
    actually be sent (replymail.offered)."""
    if not replymail.offered():
        return None
    return Label(Input(type="checkbox", name="notify_replies", value="1", cls="checkbox checkbox-xs"),
                 Span(i18n.t("Email me when someone replies"), cls="text-xs text-base-content/70"),
                 cls="flex items-center gap-1.5 cursor-pointer")


def PinnedIcon():
    # An icon at the right of the title's row, never inside the title -
    # a long title wraps without taking it along. Accent, like the
    # "Pinned" label above them (home()); primary is for the main action.
    return Span(PIN_SVG, cls="text-accent shrink-0 tooltip", data_tip=i18n.t("Pinned"), role="img",
                aria_label=i18n.t("Pinned"))


# a post with no cover, where the style has room for one: a soft tile in
# the theme's own colours, like Magazine's featured post - flat grey read
# as an image that failed to load
NO_COVER = "bg-gradient-to-br from-primary/20 to-secondary/20"


def roll_shows(s=None) -> set:
    """What each post in the blog roll shows (Settings > Appearance >
    Blog layout) - ROLL_PARTS keys."""
    raw = (s or settings.get_all()).get("roll_shows")
    return set(ROLL_PARTS) if raw is None else {k for k in raw.split(",") if k in ROLL_PARTS}


def list_cover(p, show) -> str:
    """The post's cover in a list of posts - none where the site's lists
    show no covers, or the post keeps its own out of them."""
    try:
        hidden = p["hide_list_cover"]
    except (KeyError, IndexError):
        hidden = 0
    return p["cover_image"] if "cover" in show and not hidden else ""


def roll_placeholder() -> bool:
    return settings.get_all().get("roll_placeholder") != "0"


def _meta(p, relative_dates, show, reading=True):
    """The date and reading time line, as far as show wants them."""
    parts = [format_date(p["created_at"], relative_dates)] if "date" in show else []
    if reading and "reading" in show:
        parts.append(reading_time(posts.load_post_body(p["slug"])))
    return " · ".join(parts)


def PostCardList(p, relative_dates=False, show=None):
    # list-col-grow: one full-width column (list-row's two assume an
    # avatar); the lines between rows are the list's own.
    # The text first and the picture on its right, the way Medium and
    # Substack list posts: every title starts at the same edge, cover or
    # not (a picture ahead of the text made the titles zig-zag), and the
    # picture can be a real size - 176x128 on a wide screen, 96 square on
    # a phone - instead of a stamp. No cover, no picture: in a list an
    # empty tile reads as a broken image.
    # Left is there too, for a site that wants the picture first.
    show = roll_shows() if show is None else show
    cover = list_cover(p, show)
    thumb = A(
        Img(src=images.thumb(cover), alt=images.alt_text_for_url(cover),
            loading="lazy", cls="h-24 w-24 sm:h-32 sm:w-44 object-cover rounded-box"),
        href=posts.url_for(p), aria_label=p["title"], cls="block shrink-0 self-start"
    ) if cover else None
    left = settings.get_all().get("roll_list_cover") == "left"
    meta = _meta(p, relative_dates, show)
    return Li(
        thumb if left else None,
        Div(
            Div(meta, cls="text-xs text-base-content/50") if meta else None,
            Div(
                H2(A(p["title"], href=posts.url_for(p), cls="link link-hover text-lg sm:text-xl font-semibold "
                                                                "leading-snug break-words")),
                PinnedIcon() if p["pinned"] else None,
                cls="flex items-start justify-between gap-2 mt-1"
            ),
            (teaser := posts.teaser(p)) and ("summary" in show or None)
            and P(teaser, cls="text-sm sm:text-base text-base-content/70 mt-2 line-clamp-2 flex-none"),
            TagList(p["tags"], small=True) if "tags" in show else None,
            cls="list-col-grow min-w-0"
        ),
        None if left else thumb,
        cls="list-row gap-4 sm:gap-6 py-6 sm:py-8"
    )


def PostCardGrid(p, relative_dates=False, show=None):
    show = roll_shows() if show is None else show
    meta = _meta(p, relative_dates, show)
    cover = list_cover(p, show)
    return Div(
        (Figure(A(Img(**images.responsive(cover, "(min-width: 640px) 24rem, 100vw"),
                      alt=images.alt_text_for_url(cover), loading="lazy",
                      cls="aspect-[3/2] w-full object-cover"),
                  href=posts.url_for(p), aria_label=p["title"], cls="block w-full")) if cover
         else Figure(A(Div(cls=f"aspect-[3/2] w-full {NO_COVER}"),
                       href=posts.url_for(p), aria_label=p["title"], cls="block w-full"))
         if roll_placeholder() else None)
        if "cover" in show else None,
        Div(
            Div(
                H2(A(p["title"], href=posts.url_for(p), cls="link link-hover card-title text-lg leading-snug break-words")),
                PinnedIcon() if p["pinned"] else None,
                cls="flex items-start justify-between gap-2 min-w-0"
            ),
            Div(meta, cls="text-xs text-base-content/50 -mt-1") if meta else None,
            (teaser := posts.teaser(p)) and ("summary" in show or None)
            # flex-none: a card's paragraphs stretch to fill it (daisyUI), and
            # the clamp's two lines grew to four, the "…" in the middle
            and P(teaser, cls="text-sm text-base-content/70 line-clamp-2 flex-none"),
            TagList(p["tags"], small=True) if "tags" in show else None,
            # three to a row in the reading column: 20 px, so the words keep their room
            cls="card-body p-5 gap-3"
        ),
        cls="card card-border bg-base-100 transition-shadow hover:shadow-lg"
    )


def PostCardMinimal(p, relative_dates=False, show=None, date=None, heading=H2):
    """A date and a title, nothing else - a reading list. In list-row's
    two columns: the date, then the title with a pinned post's icon.
    The title is still an H2, so screen readers and search engines see
    a heading for each post; Tailwind gives an H2 no look of its own."""
    show = roll_shows() if show is None else show
    date = date or format_date(p["created_at"], relative_dates)
    first_tag = next((t.strip() for t in (p["tags"] or "").split(",") if t.strip()), "") if "tags" in show else ""
    return Li(
        Span(date, cls="text-xs text-base-content/50 font-mono whitespace-nowrap") if "date" in show else None,
        Div(
            heading(A(p["title"], href=posts.url_for(p), cls="link link-hover break-words")),
            Div(PinnedIcon() if p["pinned"] else None,
                # the right of the row, where a reading list has it: the
                # post's first tag and how long it takes, small - it was empty
                A(f"#{first_tag}", href=tag_url(first_tag), cls="link link-hover hidden sm:inline")
                if first_tag else None,
                Span(reading_time(posts.load_post_body(p["slug"]))) if "reading" in show else None,
                cls="flex items-center gap-3 shrink-0 text-xs text-base-content/50 whitespace-nowrap"),
            cls="flex items-baseline justify-between gap-4 min-w-0" + ("" if "date" in show else " list-col-grow")
        ),
        # the list's own columns (minimal_list_cls), so every title starts
        # at the same edge - "Sep 5" is narrower than "Sep 15"
        cls="list-row items-baseline py-3" + (" col-span-2 grid-cols-subgrid" if "date" in show else "")
    )


def MinimalList(posts_list, relative_dates, show, grouped=True, extra=""):
    """grouped - under a heading for each year or month (Settings >
    Appearance > Blog layout), where the posts are in date order. The
    dates then leave out what the heading says."""
    group = settings.get_all().get("minimal_group") if grouped else "none"
    if group not in ("year", "month"):
        return Ul(*[PostCardMinimal(p, relative_dates, show=show) for p in posts_list],
                  cls=minimal_list_cls(show, extra))
    names, items, last = i18n.months(full=True), [], None
    for p in posts_list:
        day = local_datetime(p["created_at"])
        key = (day.year, day.month if group == "month" else 0)
        if key != last:
            items.append(Li(H2(f"{names[day.month - 1]} {day.year}" if group == "month" else str(day.year),
                               cls="text-lg font-semibold"),
                            cls=f"col-span-2 px-4 pb-1 {'pt-2' if last is None else 'pt-8'}"))
            last = key
        items.append(PostCardMinimal(p, show=show, date=short_date(day, month=group == "year"), heading=H3))
    return Ul(*items, cls=minimal_list_cls(show, extra))


def minimal_list_cls(show, extra=""):
    """One date column for the whole Minimal list, as wide as its widest
    date in any language, instead of each row sizing its own."""
    return f"list {'grid grid-cols-[auto_1fr]' if 'date' in show else ''} {extra}"


def _timeline_dot(pinned: bool):
    # neutral for a regular entry, matching the rail's own color (see
    # PostCardTimeline's docstring on why neutral, not primary) - a
    # pinned post's dot switches to accent, the same token "Pinned"
    # elsewhere in the app uses, so it reads as a pinned marker at a
    # glance without needing PinnedIcon's own label repeated here too.
    # the text colour, faded - neutral sat near the page's own colour in
    # dark themes (dim), and the line vanished
    color = "text-accent" if pinned else "text-base-content/50"
    return NotStr(
        f'<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 {color}" viewBox="0 0 24 24" '
        'fill="currentColor"><circle cx="12" cy="12" r="6"/></svg>'
    )


def PostCardTimeline(p, relative_dates, is_first, is_last, index, show=None, align="center"):
    """One post on daisyUI's timeline: the line is its <hr>s, the dot
    `neutral` (primary is for the page's one main action, and this
    repeats). Boxes alternate sides (timeline-start, timeline-end); on a
    narrow screen the list is timeline-compact, one side (PostRoll). The
    date is inside the box, the cover above the text with its own inset.
    All boxes are one width; a post without a cover has no picture."""
    show = roll_shows() if show is None else show
    meta = _meta(p, relative_dates, show)
    cover = list_cover(p, show)
    box = Div(
        A(Img(**images.responsive(cover, "(min-width: 640px) 24rem, 100vw"),
              alt=images.alt_text_for_url(cover), loading="lazy",
              cls="aspect-[3/2] w-full object-cover rounded-box"),
          href=posts.url_for(p), aria_label=p["title"], cls="block mb-2")
        if cover else None,
        Div(
            # text-base - a timeline box sets its own smaller size
            H2(A(p["title"], href=posts.url_for(p), cls="link link-hover text-base font-semibold break-words")),
            PinnedIcon() if p["pinned"] else None,
            cls="flex items-start justify-between gap-2 min-w-0"
        ),
        Div(meta, cls="text-xs text-base-content/50 mt-0.5") if meta else None,
        (teaser := posts.teaser(p)) and ("summary" in show or None) and P(teaser, cls="text-sm text-base-content/70 mt-1"),
        TagList(p["tags"], small=True) if "tags" in show else None,
    )
    side_cls = timeline_side(align, index)
    # alternating boxes leave a little air on the far side; one-sided
    # ones take the whole width beside the line
    # ones take the whole width beside the line - stretched, not w-full:
    # w-full and the gap to the line ran the card 12 px into the line
    width = "md:w-[85%]" if align == "center" else "justify-self-stretch"
    return Li(
        None if is_first else Hr(cls="bg-base-content/25"),
        # p-4: .timeline-box's own padding is less above and below than at
        # the sides, so the picture looked flush with the top
        # a little air between the card and the line, on whichever side
        Div(box, cls=f"{side_cls} timeline-box mb-4 p-4 {width} min-w-0 "
                     f"{'ms-3' if side_cls == 'timeline-end' else 'me-3 max-md:me-0 max-md:ms-3' if align == 'center' else 'me-3'}"),
        Div(_timeline_dot(p["pinned"]), cls="timeline-middle"),
        None if is_last else Hr(cls="bg-base-content/25"),
    )


def MagazineFeatured(p, relative_dates=False, show=None):
    """The newest post, given real weight - title and summary sit
    directly on the cover image behind a bottom gradient scrim, the
    same image-behind-text idea HeroSection uses, just anchored
    bottom-left like a magazine cover credit block instead of
    HeroSection's own centered treatment - so this reads as the
    homepage's focal point instead of an oversized PostCardGrid card.
    No image falls back to a tint in the theme's colours, with plain
    base-content text over it."""
    show = roll_shows() if show is None else show
    image = list_cover(p, show)
    meta = _meta(p, relative_dates, show)
    return Div(
        # dark enough behind the whole text block - a long title reaches up
        # into the lighter top of the photo on a phone
        Div(cls="absolute inset-0 bg-gradient-to-t from-black/90 via-black/60 to-black/20") if image else None,
        Div(
            Div(
                H2(A(p["title"], href=posts.url_for(p),
                     cls=f"link link-hover card-title text-xl sm:text-2xl md:text-3xl break-words "
                         f"{'text-white' if image else ''}")),
                PinnedIcon() if p["pinned"] else None,
                cls="flex items-start justify-between gap-2 min-w-0"
            ),
            Div(meta, cls=f"text-xs {'text-white/70' if image else 'text-base-content/50'}") if meta else None,
            (teaser := posts.teaser(p)) and ("summary" in show or None)
            and P(teaser, cls="line-clamp-3 flex-none " + ("text-white/90" if image else "text-base-content/70")),
            TagList(p["tags"], small=True) if "tags" in show else None,
            cls="relative z-10 min-w-0 flex flex-col gap-1.5"
        ),
        style=f"background-image: url({image}); background-size: cover; background-position: center;" if image else None,
        cls="relative rounded-box overflow-hidden min-h-64 sm:min-h-80 flex flex-col justify-end gap-1 p-5 sm:p-8 mb-10"
             + ("" if image else " bg-gradient-to-br from-primary/30 to-secondary/30")
    )


def MagazineRestCard(p, relative_dates=False, show=None):
    """A lighter sibling to PostCardGrid, used only for magazine's
    'rest' grid below the featured post - no border/bg box, so these
    read as secondary items supporting the featured post above rather
    than competing with it as equally-weighted cards."""
    show = roll_shows() if show is None else show
    meta = _meta(p, relative_dates, show)
    cover = list_cover(p, show)
    return Div(
        A(Img(**images.responsive(cover, "(min-width: 640px) 16rem, 100vw"),
              alt=images.alt_text_for_url(cover), loading="lazy",
              cls="aspect-[3/2] w-full object-cover rounded-box") if cover
          else Div(cls=f"aspect-[3/2] w-full rounded-box {NO_COVER}"),
          href=posts.url_for(p), aria_label=p["title"], cls="block mb-3")
        if cover or ("cover" in show and roll_placeholder()) else None,
        Div(
            H2(A(p["title"], href=posts.url_for(p), cls="link link-hover text-lg font-semibold leading-snug "
                                                            "break-words")),
            PinnedIcon() if p["pinned"] else None,
            cls="flex items-start justify-between gap-2 min-w-0"
        ),
        Div(meta, cls="text-xs text-base-content/50 mt-1") if meta else None,
        (teaser := posts.teaser(p)) and ("summary" in show or None)
        and P(teaser, cls="text-sm text-base-content/70 line-clamp-2 mt-1 flex-none"),
        TagList(p["tags"], small=True) if "tags" in show else None,
        cls="min-w-0"
    )


def _cards_grid_cls(body_width, extra=""):
    # cards in a row follow the column's width (body_width), not the
    # screen's: 2 in a narrow column, 3 in a standard one. A last card on
    # its own stays the size of the others.
    cols = "sm:grid-cols-2" if card_columns(settings.get_all(), body_width) == 2 else "sm:grid-cols-3"
    return f"grid grid-cols-1 {cols} gap-6 {extra}".strip()


def card_columns(s, body_width=None) -> int:
    """Cards in a row (Settings > Appearance): 2 or 3 - never 3 in the
    narrow column, where they'd be too cramped."""
    if s.get("cards_per_row") == "1":
        return 1
    if (body_width or s.get("body_width")) == "narrow":
        return 2
    return 2 if s.get("cards_per_row") == "2" else 3


def page_size(s) -> int:
    """Posts per page - with Cards, rounded up to fill the last row, so
    10 in rows of 3 doesn't leave one card alone at the bottom."""
    try:
        per_page = max(1, min(int(s.get("posts_per_page") or 12), 100))
    except ValueError:
        per_page = 12
    if s.get("roll_style") == "cards":
        cols = card_columns(s)
        per_page = -(-per_page // cols) * cols
    return per_page


# a post in a list opens on a click anywhere on it, not only its title
# (ROW_LINKS_JS) - on a phone a title was a 20 px line to hit
CLICK_ROWS = dict(data_click_rows=True, cls="[&_li]:cursor-pointer [&_.card]:cursor-pointer")


def PostRoll(posts_list, relative_dates, roll_style, empty_message, empty_icon="📭", body_width="standard",
             grouped=True):
    """grouped - False where the posts aren't in date order (search,
    a series): Minimal's year and month headings would repeat."""
    if not posts_list:
        return EmptyState(empty_message, empty_icon)
    return Div(_post_roll(posts_list, relative_dates, roll_style, body_width, grouped), **CLICK_ROWS)


def _post_roll(posts_list, relative_dates, roll_style, body_width, grouped):
    show = roll_shows()

    if roll_style == "cards" and card_columns(settings.get_all(), body_width) == 1:
        # one a row: each one as Magazine's first, its picture behind its words
        return Div(*[MagazineFeatured(p, relative_dates, show=show) for p in posts_list])
    if roll_style == "cards":
        return Div(*[PostCardGrid(p, relative_dates, show=show) for p in posts_list],
                    cls=_cards_grid_cls(body_width))

    if roll_style == "minimal":
        return MinimalList(posts_list, relative_dates, show, grouped)

    if roll_style == "timeline":
        n = len(posts_list)
        align = settings.get("timeline_align")
        return Ul(*[PostCardTimeline(p, relative_dates, i == 0, i == n - 1, i, show, align)
                    for i, p in enumerate(posts_list)], cls=timeline_cls(align), **timeline_stagger(align))

    if roll_style == "magazine":
        # home() itself fetches one extra post whenever magazine's own
        # hero+grid split would otherwise
        # leave the grid one short of a full pair, so the "gap" is
        # filled with a genuine next post pulled forward from what
        # would have been the next page, not a wider card standing in
        # for one. rest is only ever odd here on the actual last page,
        # where there truly isn't a next post to pull forward - that
        # last lone card stays exactly as wide as its siblings.
        featured, rest = posts_list[0], posts_list[1:]
        return Div(
            MagazineFeatured(featured, relative_dates, show=show),
            Div(*[MagazineRestCard(p, relative_dates, show=show) for p in rest],
                # room between them, a row apart - at gap-4 the rows ran together
                cls="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-10") if rest else None
        )

    return Ul(*[PostCardList(p, relative_dates, show=show) for p in posts_list], cls="list")


def PinnedPostRoll(posts_list, relative_dates, roll_style, body_width="standard"):
    """Posts pinned to the top of the blog, as cards in the roll's own
    style, each marked with PinnedIcon. Under Magazine each is a large
    featured post, as the roll's first is - pinned posts are meant to
    stand out at least that much."""
    if not posts_list:
        return None
    return Div(_pinned_roll(posts_list, relative_dates, roll_style, body_width), **CLICK_ROWS)


def _pinned_roll(posts_list, relative_dates, roll_style, body_width):
    show = roll_shows()
    if roll_style == "magazine" or (roll_style == "cards" and card_columns(settings.get_all(), body_width) == 1):
        return Div(*[MagazineFeatured(p, relative_dates, show=show) for p in posts_list])
    if roll_style == "cards":
        return Div(*[PostCardGrid(p, relative_dates, show=show) for p in posts_list],
                    cls=_cards_grid_cls(body_width, "mb-6"))
    if roll_style == "minimal":
        return Ul(*[PostCardMinimal(p, relative_dates, show=show) for p in posts_list],
                  cls=minimal_list_cls(show, "mb-6"))
    if roll_style == "timeline":
        n = len(posts_list)
        align = settings.get("timeline_align")
        return Ul(*[PostCardTimeline(p, relative_dates, i == 0, i == n - 1, i, show, align)
                    for i, p in enumerate(posts_list)], cls=timeline_cls(align, "mb-6"), **timeline_stagger(align))
    return Ul(*[PostCardList(p, relative_dates, show=show) for p in posts_list], cls="list mb-6")


@ar.get("/")
def home(req, session, hdrs, page: int = 1):
    s = settings.get_all()
    from soloblog import fediverse
    if fediverse.enabled(s) and fediverse.wants_json(req.headers.get("accept", "")):
        return Response(json.dumps(fediverse.actor(s), ensure_ascii=False), media_type=fediverse.CONTENT_TYPE)
    # Settings > Name and homepage > Homepage: one of your pages at the front, the posts at /blog
    # what a search engine should call the site, and that it can be searched
    from soloblog import seo
    hdrs.append(seo.website_data(s))
    if s.get("home_page") == posts.WIKI_HOME:
        return wiki_home(session, hdrs, at_home=True)
    front = posts.get_post(s["home_page"]) if s.get("home_page") else None
    if front and posts.is_live(front):
        return view_post(req, session, hdrs, front["slug"])
    return blog_roll(req, session, hdrs, page, "/")


@ar.get("/blog")
def blog(req, session, hdrs, page: int = 1):
    if not settings.get("home_page"):
        return RedirectResponse("/" + (f"?page={page}" if page > 1 else ""), status_code=301)
    return blog_roll(req, session, hdrs, page, "/blog")


def blog_roll(req, session, hdrs, page: int, base: str):
    """The blog roll - the homepage, or /blog when a page is the homepage."""
    s = settings.get_all()

    per_page = page_size(s)
    roll_style = s.get("roll_style", "list")
    # Magazine shows the first post large and the rest in pairs; with an
    # even number per page the last pair was one short, so it takes one
    # more post per page - the same number on every page, so paging works
    fetch_per_page = per_page + 1 if roll_style == "magazine" and per_page % 2 == 0 else per_page
    page = max(1, page)
    total = posts.count_roll()
    total_pages = max(1, -(-total // fetch_per_page))  # ceil division
    # past the end (an old link, after fewer posts per page): the last page
    if page > total_pages:
        return RedirectResponse(base + (f"?page={total_pages}" if total_pages > 1 else ""), status_code=302)
    # page 2 onwards: its own title and address, not a copy of the first
    # page's - search engines list them separately
    title = s["site_title"] if base == "/" else i18n.t("Blog")
    if page > 1:
        title = f"{title} - {i18n.t('Page {page} of {total}', page=page, total=total_pages)}"
    page_meta(hdrs, title, s["meta_description"] or s["tagline"], base + (f"?page={page}" if page > 1 else ""))
    roll = posts.list_roll(page=page, per_page=fetch_per_page)
    pinned_tree = posts.list_pinned_tree()
    # flat, not list_pinned_tree_top()'s (page, [children]) pairs - a
    # blogroll doesn't have the header/footer nav's "parent page with
    # sub-pages" structure, every pinned-top post is just its own card
    top_pins = posts.list_pinned_by_location("top")
    relative = s.get("relative_dates") == "1"
    roll_view = PostRoll(roll, relative, roll_style, i18n.t("Nothing published yet."), body_width=s.get("body_width"))
    if not roll and auth.is_logged_in(session):
        # the owner sees where to start; a visitor just the plain line
        roll_view = EmptyState("Nothing published yet. Write a post and it shows here.", "📭",
                               actions=[A("New post", href="/admin/new", cls="btn btn-sm")])
    pinned_view = PinnedPostRoll(top_pins, relative, roll_style, body_width=s.get("body_width"))

    centered = s.get("header_align") in ("center", "stacked")
    # with a banner, the tagline is its subheading instead (HeroSection)
    banner = s.get("banner_enabled") == "1" and s.get("banner_heading")
    intro = P(s["tagline"], cls=f"text-base-content/70 mb-6 {'text-center' if centered else ''}".strip()) \
        if s["tagline"] and not banner else None

    # a page's one h1 is its heading for a screen reader, drawn or not.
    # The banner goes with the list of posts: at /blog when the homepage is
    # a page, which has a Hero section of its own for that
    hero = HeroSection(s)
    return Layout(
        intro if base == "/" else None,
        hero or H1(s["site_title"] if base == "/" else i18n.t("Blog"), cls="sr-only"),
        # "Pinned" and "Latest" label the two parts, like the post page's
        # other sections - no divider as well
        # relative - a tag cloud or archive links beside the posts sit
        # against it (SidePanels); where there's no room they follow the posts
        Div(
            Div(P(i18n.t("Pinned"), cls="text-base font-semibold text-accent mb-2"), pinned_view) if pinned_view else None,
            P(i18n.t("Latest"), cls="text-base font-semibold text-accent mb-2") if pinned_view else None,
            roll_view,
            ads.AdSlot(s, "adsense_slot_roll", auth.is_logged_in(session)),
            Pagination(page, total_pages, base),
            *(side := SidePanels(s))[0],
            side[1],
            cls="relative"
        ),
        Div(box, cls="mt-6") if s.get("newsletter_on_home") == "1" and (box := newsletter.Box(s)) else None,
        settings=s, logged_in=auth.is_logged_in(session), pinned_tree=pinned_tree
    )


@ar.get("/links")
def links_page(session, hdrs):
    """A link-in-bio page: who you are, then a stack of big buttons -
    your own links, support links, newest posts. Turned on, and filled
    in, from Settings > Author > Links page."""
    s = settings.get_all()
    logged_in = auth.is_logged_in(session)
    if s.get("links_enabled") != "1":
        return FtResponse(ErrorPage(404, s, logged_in, posts.list_pinned_tree()), status_code=404)
    name = s["author_name"] or s["site_title"]
    # just the name - "Links - John Doe" came out as "Links - John Doe — John Doe"
    page_meta(hdrs, name, s["author_bio"] or s["tagline"], "/links")
    avatar = s.get("author_avatar_url")

    def section(label, *content):
        # the same eyebrow label posts use for Share/Support/Author
        return Div(P(label, cls="text-base font-semibold text-accent mb-2"), *content, cls="w-full")

    own = [A(label, href=url, target="_blank" if url.startswith("http") else None, rel="noopener",
             cls="btn btn-primary btn-block") for label, url in parse_link_lines(s["links_items"])]
    newest = posts.list_roll(page=1, per_page=3) if s.get("links_show_posts") == "1" else []
    support = SupportButtons(s, block=True) if s.get("links_show_support") == "1" else None
    return Layout(
        Div(
            # who you are, one part
            Div(Div(Div(Img(src=avatar, alt=name, cls="object-cover"), cls="w-24 rounded-full"), cls="avatar")
                if avatar else None,
                H1(name, cls=LIST_TITLE_CLS),
                P(s["author_bio"], cls="text-sm text-base-content/70") if s["author_bio"] else None,
                SocialLinks(s, cls_extra="!mt-0 justify-center", icons=True) if s.get("links_show_socials") == "1"
                else None,
                cls="flex flex-col items-center gap-3"),
            Div(*own, cls="flex flex-col gap-2 w-full") if own else None,
            section(i18n.t("Support"), support) if support else None,
            section(i18n.t("Latest posts"), Div(*[
                A(Span(p["title"], cls="truncate"), Span(format_date(p["created_at"], s["relative_dates"] == "1"),
                                                          cls="text-xs text-base-content/50 shrink-0"),
                  href=posts.url_for(p), cls="btn btn-block justify-between font-normal")
                for p in newest
            ], cls="flex flex-col gap-2")) if newest else None,
            cls=f"max-w-sm mx-auto {pages.PARTS} items-center text-center"
        ),
        settings=s, logged_in=logged_in, pinned_tree=posts.list_pinned_tree()
    )


def site_pages_found(q: str, s) -> list:
    """[(what the menu calls it, its address)] of the site's own pages in
    the header or footer (Blog, Archive, Contact...) whose name a word of
    the search starts - search looks through posts and pages, and these
    aren't either."""
    from soloblog.ui import site_label
    terms = re.findall(r"\w+", q.lower())
    found, seen = [], set()
    for where in ("header", "footer"):
        for key in posts.site_rows(s, where):
            label = site_label(s, where, key)
            if key in seen or not any(w.startswith(t) for t in terms for w in re.findall(r"\w+", label.lower())):
                continue
            seen.add(key)
            found.append((label, posts.SITE_PAGES[key][0]))
    return found


@ar.get("/search")
def search_page(session, hdrs, q: str = ""):
    s = settings.get_all()
    page_meta(hdrs, i18n.t("Search"), path="/search")
    # results are for the visitor, not for search engines to list
    hdrs.append(Meta(name="robots", content="noindex, follow"))
    relative = s.get("relative_dates") == "1"

    if q:
        results = posts.search(q)
        sites = site_pages_found(q, s)
        body = Div(
            # the site's own pages it matches, as the menu names them, before the posts
            Div(*[A(label, href=href, cls="btn btn-sm") for label, href in sites], cls="flex flex-wrap gap-2")
            if sites else None,
            PostRoll(results, relative, s.get("roll_style", "list"), i18n.t('Nothing found for "{q}"', q=q), "🔍",
                     s.get("body_width"), grouped=False) if results or not sites else None,
            cls=pages.PARTS)
    else:
        body = EmptyState(i18n.t("Type something to search the posts."), "🔎")

    return Layout(
        Div(
            H1(i18n.t("Search"), cls=LIST_TITLE_CLS),
            Form(
                SearchBox("flex-1", name="q", value=q, placeholder=i18n.t("Search posts..."), autofocus=True,
                          aria_label=i18n.t("Search")),
                Button(i18n.t("Search"), type="submit", cls="btn btn-primary btn-sm"),
                action="/search", method="get", cls="flex gap-2"
            ),
            body,
            cls=pages.PARTS
        ),
        settings=s, logged_in=auth.is_logged_in(session), pinned_tree=posts.list_pinned_tree()
    )


@ar.get("/search/results")
def search_results(q: str = ""):
    """Backs SearchModal's live-as-you-type results (ui) - an HTMX
    partial, not a full page. Each result: its title, a line or two of
    what it's about, and a post's date (a page's date means nothing)."""
    if not q.strip():
        return None
    s = settings.get_all()
    relative = s.get("relative_dates") == "1"
    results = posts.search(q)
    sites = site_pages_found(q, s)
    if not results and not sites:
        return P(i18n.t('Nothing found for "{q}"', q=q), cls=RESULT_EMPTY)
    # each result one link, the whole row - as the link picker's (ui.RESULT_ROW); the
    # site's own pages it matches first, with their address
    return (P(i18n.t("Results: {n}", n=len(results) + len(sites)), cls="text-xs text-base-content/50 px-1 pb-1"),) + tuple(
        A(Span(label, cls=RESULT_TITLE), Span(href, cls=RESULT_ABOUT), href=href, cls=RESULT_ROW) for label, href in sites
    ) + tuple(
        A(
            Span(p["title"], cls=RESULT_TITLE),
            Span(teaser, cls=RESULT_ABOUT) if (teaser := posts.teaser(p, 140)) else None,
            None if posts.is_page(p) else Span(format_date(p["created_at"], relative),
                                               cls="block text-xs text-base-content/50 mt-0.5"),
            href=posts.url_for(p), cls=RESULT_ROW
        ) for p in results
    )


# comment(depth 0) -> reply(1) -> reply(2) -> reply(3), then no more -
# Reply stops being offered past this depth, for the author and
# visitors alike (both can reply now, at any depth under the cap - see
# CommentBubble/VisitorReplyFields). Enforced server-side too, not
# just by hiding the button (submit_comment, below) - a visitor's own
# POST is untrusted input, unlike the admin-only /post/{slug}/reply.
# REPLY_INDENT has to be a literal list of complete class names, not
# an f-string computing "ml-{depth*8}" at render time - Tailwind's
# build-time scanner only ever generates a class it can see as one
# complete literal token in the source, the same reason the toast
# color bug happened a few follow-ups back.
MAX_REPLY_DEPTH = 3
REPLY_INDENT = ["", "ml-8", "ml-16", "ml-24"]



def CommenterFields(member):
    """Who's commenting: a signed-in member is known already - only a name,
    if they've none yet; anyone else gives a name and an email to confirm."""
    if member and member["name"]:
        return P(i18n.t("Commenting as {name}", name=member["name"]), cls="text-sm text-base-content/60 mb-2 w-full")
    if member:
        return Input(name="author_name", placeholder=i18n.t("Name"), aria_label=i18n.t("Name"), required=True,
                     maxlength="80", cls="input input-sm w-full mb-2")
    return Div(
        Input(name="author_name", placeholder=i18n.t("Name"), aria_label=i18n.t("Name"), required=True,
              cls="input input-sm w-full remember-name-field"),
        Input(name="email", type="email", placeholder=i18n.t("Email (for confirmation, never shown publicly)"),
              aria_label=i18n.t("Email"),
              required=True, cls="input input-sm w-full"),
        cls="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-2 w-full"
    )


def CommentGate(s, post_url):
    """In place of the comment form, when comments are for members."""
    from soloblog import stripe_members
    member = members.current()
    paid = s.get("members_comments") == "paid"
    back = quote(post_url + "#comments")
    if paid and stripe_members.ready(s):
        actions = [A(i18n.t("Become a paid member"), href=f"/membership?next={back}", cls="btn btn-primary btn-sm")]
    elif not member:
        actions = [A(i18n.t("Join"), href=f"/join?next={back}", cls="btn btn-primary btn-sm")]
    else:
        actions = []
    if not member:
        actions.append(A(i18n.t("Sign in"), href=f"/signin?next={back}", cls="btn btn-sm btn-ghost"))
    return Div(P(i18n.t("Only paid members can comment.") if paid else i18n.t("Only members can comment."),
                 cls="text-sm text-base-content/70"),
               Div(*actions, cls="flex flex-wrap gap-2") if actions else None,
               cls="flex flex-wrap items-center justify-between gap-3 mt-3")


def VisitorReplyFields(settings):
    """What a visitor's reply needs beyond the text - the same as the main
    comment form: a name (remembered, COMMENTER_NAME_JS), an email to
    confirm it, the honeypot, the spam check. It goes through the same
    moderation as any comment (/post/{slug}/comment with parent_id)."""
    member = members.current()
    return (
        CommenterFields(member),
        # honeypot - invisible to a real visitor, bots fill every field
        Input(name="website", cls="hidden", tabindex="-1", autocomplete="off"),
        None if member else captcha.Widget(settings, cls="self-start mb-2"),
        Div(ReplyEmailsCheckbox(), cls="self-start mb-2"),
    )


def CommentBubble(c, slug, logged_in, relative, settings, depth=0, show_reply=False):
    """One comment as a chat bubble - a reply is the same, with
    parent_id set. depth indents it (REPLY_INDENT) with a reply arrow;
    is_author adds an Author badge - a visitor can reply too, so the two
    are separate. Every bubble is chat-start, so a thread reads down one
    side.

    show_reply offers Reply below MAX_REPLY_DEPTH; Reply and Delete sit on
    the bubble's line, at the right. The .chat grid is made a flex column
    (!flex !flex-col) to put them there - the bubble's tail doesn't need
    the grid. Reply opens the same ReplyBox (ui) as the admin's list."""
    if c["trashed_at"]:
        # a placeholder for a trashed comment kept only because it
        # still has surviving replies nested under it (see
        # list_approved_with_deleted_parents, comments.py) - no name,
        # no body, no Reply/Delete for anyone; managing it (restoring
        # or permanently deleting it) is an admin-only action that
        # lives in the Trash tab, not cluttering the live public page
        return Div(
            Div(Em(i18n.t("This comment was deleted.")), cls="chat-bubble chat-bubble-neutral opacity-60"),
            cls=f"chat !flex !flex-col chat-start {REPLY_INDENT[depth]}".strip()
        )
    is_reply = depth > 0
    # icons only: the row shares its width with the bubble, which can be
    # up to 90% of it - each icon's tooltip names it
    delete_form = Form(
        Input(type="hidden", name="comment_id", value=c["id"]),
        Input(type="hidden", name="slug", value=slug),
        IconAction(TRASH_SVG, "Trash", danger=True, menu_label=False,
                   confirm="Move this comment to trash? You can restore it from Admin > Comments."),
        action="/admin/comments/delete", method="post", cls="contents"
    )
    # you get Reply (published straight away) and Trash; a visitor gets
    # Reply with their name and email, moderated like any comment. Both
    # open the same box, under the comment - as in the admin
    reply_button = ReplyButton(c["id"], menu_label=False) if show_reply else None
    reply_box = (ReplyBox(f"/post/{slug}/reply", c["id"]) if logged_in else
                 ReplyBox(f"/post/{slug}/comment", c["id"], *VisitorReplyFields(settings))) if show_reply else None
    actions = Div(reply_button, delete_form if logged_in else None, cls="join shrink-0") \
        if reply_button or logged_in else None

    return Div(
        Div(
            # dim reply-arrow glyph, not a color - "this is a reply"
            # signal that reads as a subtle marker, not another
            # attention-grabbing element competing with the badge/name
            Span(REPLY_SVG, cls="inline-flex opacity-40 mr-1 align-middle") if is_reply else None,
            # a reply from the fediverse: its author's own profile, and where it came from
            A(c["author_name"], href=web_url(_col(c, "author_url")), target="_blank", rel="nofollow ugc noopener",
              cls="link link-hover") if _col(c, "source") == "activitypub" and web_url(_col(c, "author_url"))
            else c["author_name"],
            Span("fediverse", cls="badge badge-ghost badge-xs ml-2") if _col(c, "source") == "activitypub" else None,
            # "Author" badge is keyed off is_author specifically, not
            # depth - visitors can reply now too (at any depth under
            # the cap), so nesting position alone no longer tells you
            # who actually wrote it
            Span(i18n.t("Author"), cls="badge badge-outline badge-xs ml-2") if c["is_author"] else None,
            Time(format_date(c["created_at"], relative), cls="text-xs text-base-content/60 ml-2"),
            cls="chat-header"
        ),
        Div(
            Div(NotStr(render_comment(c["body"])), cls="chat-bubble chat-bubble-neutral"),
            actions,
            cls="flex items-start justify-between gap-2"
        ),
        reply_box,
        # !items-stretch: chat-start's place-items:start outlives the flex
        # override, and shrank each row to its content
        # comment-<id> - where a reply email's link lands
        id=f"comment-{c['id']}",
        cls=f"chat !flex !flex-col !items-stretch gap-1.5 chat-start {REPLY_INDENT[depth]}".strip()
    )


def post_crumbs(row, s) -> list:
    """Home > [parent page | series | first tag] > this post."""
    mode = s.get("breadcrumbs") or "auto"
    if mode == "off":
        return []
    crumbs = [(i18n.t("Home"), "/")]
    if row["in_wiki"]:
        # a note's place is the wiki, wherever it's pinned
        crumbs.append((i18n.t("Wiki"), "/" if s.get("home_page") == posts.WIKI_HOME else "/wiki"))
        if s.get("home_page") == posts.WIKI_HOME:
            crumbs = crumbs[1:]
    elif row["pinned"]:
        key = posts.site_parent(row["parent_slug"])
        parent = posts.get_post(row["parent_slug"]) if row["parent_slug"] and key is None else None
        if parent:
            crumbs.append((parent["title"], posts.url_for(parent)))
        elif key in posts.SITE_PAGES and key != "home":
            # under one of the site's own pages (Home is the first crumb already)
            from soloblog.ui import site_label
            where = row["pin_location"] if row["pin_location"] in posts.MENUS else "header"
            crumbs.append((site_label(s, where, key), posts.SITE_PAGES[key][0]))
    elif mode == "auto" and row["series_name"]:
        crumbs.append((row["series_name"], f"/series/{posts.series_slug(row['series_name'])}"))
    elif mode in ("auto", "tag"):
        tag = next((t.strip() for t in (row["tags"] or "").split(",") if t.strip()), None)
        if tag:
            crumbs.append((f"#{tag}", tag_url(tag)))
    crumbs.append((row["title"], None))
    return crumbs


@ar.get("/{lang}/post/{slug}")
def view_translated_post(req, session, hdrs, lang: str, slug: str):
    """A post in another language (translate.py) - only for a language
    the site offers, and only once the post is live."""
    s = settings.get_all()
    row = posts.get_post(slug)
    if lang not in translate.targets(s) or not translate.enabled(s) or not row or not posts.is_live(row):
        return FtResponse(ErrorPage(404, s, auth.is_logged_in(session), posts.list_pinned_tree()), status_code=404)
    return view_post(req, session, hdrs, slug, lang=lang)


def LanguageLinks(slug, lang, s, has_translation):
    """"Also in: Español · Français", or on a translation, where it
    came from - kept small, under the post's date line."""
    own = translate.site_language(s)
    names = translate.LANGUAGES
    if lang:
        note = i18n.t("Machine translated from {language}." if has_translation
                      else "Not translated yet - this is the original, in {language}.", language=names[own])
        return Div(Span(note, " "),
                   A(i18n.t("Read the original"), href=posts.url_for_slug(slug), hreflang=own, lang=own, cls="link"),
                   cls="alert alert-info alert-soft text-xs py-2 mb-3 block")
    offered = [code for code in translate.available(slug) if code in translate.targets(s)]
    if not offered:
        return None
    return Div(Span(i18n.t("Also in:") + " ", cls="text-base-content/60"),
               *[x for i, code in enumerate(offered) for x in (
                   Span(" · ", cls="text-base-content/40") if i else None,
                   A(names[code], href=f"/{code}/post/{slug}", hreflang=code, lang=code, cls="link link-hover"))],
               cls="text-xs mb-3")


def _instead_of_the_post(req, session, hdrs, row, slug, preview, lang, s, logged_in):
    """What a request for a post gets in place of its page, when there's
    something: its new address, Not found, the post as ActivityPub JSON, or
    the form for its password. None when the page itself is the answer."""
    is_live = row and posts.is_live(row)
    has_preview_access = row and preview and preview == row["preview_token"]

    if not row:
        # a post whose URL changed keeps answering at its old one
        moved_to = posts.find_redirect(slug)
        if moved_to:
            query = f"?preview={quote(preview)}" if preview else ""
            return RedirectResponse(f"{posts.url_for_slug(moved_to)}{query}", status_code=301)
    if not row or not (is_live or logged_in or has_preview_access):
        if moved := posts.custom_redirect(req.url.path, s.get("redirects")):
            return RedirectResponse(moved, status_code=301)
        return FtResponse(ErrorPage(404, s, logged_in, posts.list_pinned_tree()), status_code=404)

    # a fediverse server asking for this post gets it as ActivityPub JSON
    from soloblog import fediverse
    if is_live and not lang and fediverse.enabled(s) and fediverse.wants_json(req.headers.get("accept", "")):
        return Response(json.dumps(fediverse.post_object(row, s), ensure_ascii=False),
                        media_type=fediverse.CONTENT_TYPE)

    # a protected post: its password first - once per visitor's session
    if posts.is_protected(row) and not logged_in and slug not in session.get("unlocked", []):
        return ProtectedPage(row, s, hdrs, wrong=req.query_params.get("wrong") == "1")
    return None


def _count_visit(req, slug):
    """One more read of a post, and where its reader came from."""
    posts.increment_views(slug)
    from soloblog import sources
    from urllib.parse import urlsplit
    own_host = urlsplit(config.BASE_URL).hostname or req.headers.get("host", "").split(":")[0]
    sources.count(sources.name(req.headers.get("referer", ""), req.url.query, own_host), posts._today())


def _in_language(req, hdrs, row, slug, lang, can_read, html_body, toc_html):
    """A post at its address in another language (/es/post/...): the
    translation if there is one - asked for if there isn't, or the post has
    changed since. Returns the post, its text and contents as they'll show,
    and the translation (None while there isn't one)."""
    translation = translate.get(slug, lang)
    if not translation or translate.is_stale(slug, lang):
        translate.queue_post(slug, [lang])
    if not translation:
        # the original, for now - not something to index under this address
        hdrs.append(Meta(name="robots", content="noindex"))
        return row, html_body, toc_html, None
    row = {**dict(row), "title": translation["title"], "summary": translation["summary"]}
    req.htmlkw["lang"] = lang
    if lang in translate.RTL:
        req.htmlkw["dir"] = "rtl"
    # a translation can't be cut where the original is - only the
    # translated title and summary, for someone who can't read it
    return row, (translation["html"] if can_read else ""), None, translation


def _post_head(hdrs, row, s, slug, lang, own, description, is_live):
    """What a post adds to the page's head: its title, description and
    share image, whether search engines may list it, and the other
    languages it's in."""
    # Post settings > Search engines: its own title and share image, if
    # it has them - a translation keeps its translated title
    page_meta(hdrs, (not lang and row["seo_title"]) or row["title"], description,
              f"/{lang}/post/{slug}" if lang else own,
              image=row["share_image"] or row["cover_image"] or cards.post_card_url(row), type_="article",
              canonical="" if lang else row["canonical_url"])
    if row["noindex"] or row["unlisted"]:
        hdrs.append(Meta(name="robots", content="noindex"))
    # every language this post is in, on each of them, so a search engine
    # shows a reader the one in their language
    if is_live and translate.enabled(s) and not row["noindex"] and not row["unlisted"]:
        offered = [code for code in translate.available(slug) if code in translate.targets(s)]
        if offered:
            original = config.BASE_URL + posts.url_for_slug(slug)
            hdrs.append(Link(rel="alternate", hreflang=translate.site_language(s), href=original))
            hdrs.extend(Link(rel="alternate", hreflang=code, href=f"{config.BASE_URL}/{code}/post/{slug}")
                        for code in offered)
            hdrs.append(Link(rel="alternate", hreflang="x-default", href=original))
    if is_live:
        hdrs.append(article_data(row, s, description))
        # every language this post is in, for search engines
        if translate.enabled(s):
            own_lang = translate.site_language(s)
            hdrs.append(Link(rel="alternate", hreflang=own_lang, href=config.BASE_URL + own))
            hdrs.append(Link(rel="alternate", hreflang="x-default", href=config.BASE_URL + own))
            for code in translate.available(slug):
                if code in translate.targets(s):
                    hdrs.append(Link(rel="alternate", hreflang=code, href=f"{config.BASE_URL}/{code}/post/{slug}"))


def _hidden_extras(row, s, can_read, at_home) -> set:
    """The extras this visit to a post doesn't show - a page by default
    shows just its title and content."""
    hides = set(pages.EXTRAS) - pages.shown_extras(row)
    if not can_read:
        # nothing to react to or discuss yet - and the discussion would tell
        hides = hides | {"comments", "reactions"}
    # a page as the homepage: just the page, plus whatever Settings adds back
    if at_home:
        shows = set(s.get("home_page_shows", "").split(","))
        hides = hides | ({"series", "reactions", "share", "related", "author", "comments", "support"} - shows) \
            | (set() if "title" in shows else {"meta"})
    return hides


def PostTitle(row, title_href):
    """A post's title, as its heading. Post settings > Title: centred (and
    what's under it), or hidden - still there for screen readers and search
    engines. A page with a Link to is that link."""
    title_style = row["title_style"]
    title_cls = f"{TITLE_CLS}{' text-center' if title_style == 'centre' else ''}"
    title_cls = "sr-only" if title_style == "hidden" else title_cls
    if not title_href:
        return H1(row["title"], cls=title_cls)
    if posts.is_local_link(title_href):
        # a page with a Link to one of this site's own pages
        return H1(A(row["title"], href=title_href, cls="link link-hover"), cls=title_cls)
    return H1(A(row["title"], Span(pages._icon(pages.EXTERNAL_ICON), cls="inline-flex align-middle ml-1.5 "
                                                                            "text-base-content/50 [&>svg]:h-4 [&>svg]:w-4"),
                href=title_href, target="_blank", rel="noopener", cls="link link-hover"),
              cls=title_cls)


def _byline(row, s, relative, html_body) -> str:
    """Who wrote a post, when, and how long it takes to read."""
    return f"{s['author_name'] or s['site_title']} · {format_date(row['created_at'], relative)} · {reading_time(html_body)}"


def PostButtons(row, s, slug, hides, logged_in):
    """Listen, Like and Print, together at the right of a post's header."""
    return Div(
        ListenButton() if "listen" not in hides else None,
        LikeButton(slug, row["likes"], logged_in=logged_in)
        if s.get("reactions_style", "like") == "like" and "reactions" not in hides else None,
        None if "print" in hides else pages.PrintButton(i18n.t("Print")),
        cls="flex flex-wrap items-center gap-2 shrink-0 print:hidden")


def PostCover(row, s, cover_width, caption, first):
    """A post's cover image at the width it's set to, with its caption.
    first: it opens the page, over the title."""
    if not row["cover_image"]:
        return None
    return Figure(
        Breakout(Img(**images.responsive(row["cover_image"], "(min-width: 768px) 48rem, 100vw"
                                          if cover_width == "column" else "100vw"),
                     alt=images.alt_text_for_url(row["cover_image"]),
                     cls={"column": "w-full max-h-80 object-cover rounded-box",
                          "wide": "w-full max-h-96 object-cover rounded-box",
                          "full": "w-full max-h-[28rem] object-cover"}[cover_width]), cover_width, s),
        Figcaption(NotStr(caption), cls=f"{images.CAPTION_CLS} mt-1.5")
        if caption else None,
        # edge to edge, first on the page: it meets the header (flushEdges),
        # drawn there from the start (ui.FLUSH_GUESS)
        data_flush=("open" if first else True) if cover_width == "full" else None,
        cls="mb-5" if first else "mt-5"
    )


def ScreenCover(row, s, hides, crumbs, title, edit, byline, caption):
    """The whole screen: the cover edge to edge and as tall as the
    window (behind a floating header), the title, byline and tags over
    its foot, and an arrow down to the words."""
    words = Div(
        crumbs,
        # on a phone the admin's buttons sit above the title, so it keeps the whole width
        Div(Div(title, cls="min-w-0 flex-1 break-words"),
            Div(edit, cls="flex justify-end shrink-0") if edit is not None else None,
            cls="flex flex-col-reverse gap-1 sm:flex-row sm:items-start sm:justify-between sm:gap-3"),
        None if "byline" in hides else Div(byline, cls="text-sm text-white/80 mt-3"),
        Div(TagList(row["tags"]), cls="mt-4") if "tags" not in hides and row["tags"] else None,
        # light on the photo's dark foot, whatever the palette: the
        # breadcrumbs and the tags' badges. Edit's buttons keep the
        # theme's own colours, as everywhere else
        cls=f"{content_width(s)} mx-auto w-full px-4 pb-16 sm:pb-20 relative z-10 text-white "
            "[&_a:not(.btn)]:text-white [&_.breadcrumbs_*]:text-white/80 [&_.badge]:bg-black/40 "
            "[&_.badge]:text-white [&_.badge]:border-white/20")
    return Div(Breakout(Div(
        # filling a tall phone screen, a photo is cropped at the sides: as wide
        # as the screen is tall and a half, as a 3:2 photo is
        Img(**images.responsive(row["cover_image"], "max(100vw, 150vh)"), alt=images.alt_text_for_url(row["cover_image"]),
            cls="absolute inset-0 w-full h-full object-cover"),
        Div(cls="absolute inset-0 bg-gradient-to-t from-black/85 via-black/35 to-black/10"),
        words,
        Div(NotStr(caption), cls=images.CAPTION_OVER_CLS) if caption else None,
        A(CHEVRON_DOWN_SVG, href="#read-on", aria_label=i18n.t("Continue"),
          cls="btn btn-circle btn-ghost btn-sm absolute bottom-4 left-1/2 -translate-x-1/2 z-10 text-white"),
        # the arrow lands with all of the cover above the screen - none
        # of it left in the gap over a floating header
        Span(id="read-on", cls="absolute bottom-0 left-0 scroll-mt-[calc(-1*var(--header-h,0px)_-_1rem)]"),
        # as tall as the window: under a fixed header, or all of it behind a floating one
        cls="relative flex items-end overflow-hidden "
            "min-h-[calc(100svh-var(--header-h,0px)+var(--flush-top,0px))]"), "full", s),
        # and room under it for the header, so the Listen button isn't behind it
        data_flush="open", cls="mb-[max(2rem,calc(var(--header-h,0px)_+_0.5rem))]")


def PostHeader(row, s, hides, *, crumbs, title, edit, byline, updated, languages, buttons, cover_width, caption):
    """The top of a post: breadcrumbs, title, byline, tags and its buttons,
    with the cover over them or under. updated: what the byline adds when
    the post was edited on a later day."""
    centred = row["title_style"] == "centre"
    full_cover = cover_width == "full"
    return Div(
        # an edge-to-edge cover opens the page, straight under the header;
        # a narrower one follows the title, byline and tags - the order
        # Ghost, Medium and Substack use
        PostCover(row, s, cover_width, caption, first=True) if full_cover else None,
        crumbs,
        Div(
            Div(title, cls="min-w-0 flex-1 break-words"),
            # over a centred title, on the breadcrumbs' line, not pushing the title off the middle
            # (a phone: above a left-aligned title too, so it keeps the whole width)
            Div(edit, cls="absolute bottom-full right-0" if centred else "flex justify-end shrink-0")
            if edit is not None else None,
            cls="flex flex-col-reverse gap-1 sm:flex-row sm:items-start sm:justify-between sm:gap-3 "
                f"mb-3 sm:mb-4 {'relative' if centred else ''}"
        ),
        None if "byline" in hides or row["title_style"] == "hidden" else Div(
            byline, updated,
            cls=f"text-sm text-base-content/60 mb-5 {'text-center' if centred else ''}"),
        languages,
        Div(
            (None if "tags" in hides else TagList(row["tags"])) or Div(),
            buttons,
            cls=f"flex flex-wrap items-center {'justify-center' if centred else 'justify-between'} gap-3"
        ),
        None if full_cover else PostCover(row, s, cover_width, caption, first=False),
    )


def _comment_bubbles(slug, s, logged_in, relative, may_comment) -> list:
    """A post's approved comments, each reply under what it answers."""
    # list_approved_with_deleted_parents, not the plain in-scope list -
    # a trashed comment that still has surviving replies renders as a
    # "This comment was deleted" placeholder (CommentBubble) so those
    # replies stay nested under it instead of re-rooting; a *fully*
    # deleted parent (empty trash) still isn't found here at all,
    # so its children still correctly re-root, same as before this.
    top_level, children_by_parent = comments.build_thread_tree(comments.list_approved_with_deleted_parents(slug))
    bubbles = []

    def add_thread(cm, depth):
        bubbles.append(CommentBubble(
            cm, slug, logged_in, relative, s, depth=depth,
            show_reply=depth < MAX_REPLY_DEPTH and (may_comment or logged_in)
        ))
        for child in children_by_parent.get(cm["id"], []):
            add_thread(child, depth + 1)

    for cm in top_level:
        add_thread(cm, 0)
    return bubbles or [P(i18n.t("No comments yet."), cls="text-sm text-base-content/50")]


def PostComments(row, s, slug, lang, own, member, logged_in, relative, shown):
    """Under a post: its comments and the form to add one. Another comment
    system (Settings > Comments and messages) takes the place of Soloblog's own list and
    form, in the same card; a translation links to the original's."""
    if not (s.get("comments_enabled", "1") == "1" and bool(row["comments_enabled"])):
        return None
    if lang:
        return Div(A(i18n.t("Comments are on the original post"), href=f"{posts.url_for_slug(slug)}#comments", cls="link"),
                   cls="text-sm")
    if not shown:
        return None
    heading = H2(i18n.t("Comments"), cls="text-base font-semibold text-accent mb-2")
    if extcomments.system(s):
        return CommentsSection(
            heading,
            extcomments.Section(s, row, config.BASE_URL + own, translate.site_language(s)),
            id="comments"
        )
    may_comment = members.can_comment(member, s)
    return CommentsSection(
        heading,
        *_comment_bubbles(slug, s, logged_in, relative, may_comment),
        CommentGate(s, own) if not may_comment else Form(
            CommenterFields(member),
            Textarea(name="body", placeholder=i18n.t("Say something..."), aria_label=i18n.t("Comment"), required=True,
                     cls="textarea textarea-sm w-full mb-2", rows="3"),
            # honeypot - invisible to a real visitor, bots fill every field
            Input(name="website", cls="hidden", tabindex="-1", autocomplete="off"),
            None if member else captcha.Widget(s),
            # status left, button right - same row shape as the admin's
            # own SaveBar, and where the confirmation shows (no toast)
            Div(
                # data-status-slot - also where a redirect back to
                # #comments confirms ("Reply posted", "Comment confirmed")
                Span(id="comment-status", data_status_slot=True, role="status",
                     cls=f"text-xs {STATUS_BESIDE} text-base-content/50"),
                Div(ReplyEmailsCheckbox(), Button(i18n.t("Post comment"), type="submit", cls="btn btn-primary btn-sm"),
                    cls="flex items-center gap-3"),
                cls=STATUS_ROW
            ),
            hx_post=f"/post/{slug}/comment", hx_target="#comment-status", hx_swap="outerHTML show:none focus-scroll:false",
            id="comment-form", cls="mt-3"
        ),
        id="comments"
    )


@ar.get("/post/{slug}")
def view_post(req, session, hdrs, slug: str, preview: str = "", lang: str = ""):
    s = settings.get_all()
    row = posts.get_post(slug)
    logged_in = auth.is_logged_in(session)
    relative = s.get("relative_dates") == "1"

    instead = _instead_of_the_post(req, session, hdrs, row, slug, preview, lang, s, logged_in)
    if instead is not None:
        return instead
    is_live = posts.is_live(row)
    if is_live and not logged_in:
        _count_visit(req, slug)  # don't count the admin's own visits

    # a page's address is /about - /post/about sends people there
    own = posts.url_for(row)
    if not lang and own != f"/post/{slug}" and req.url.path == f"/post/{slug}":
        query = f"?preview={quote(preview)}" if preview else ""
        return RedirectResponse(own + query, status_code=301)

    body_md = posts.load_post_body(slug)
    # a page with a Link to and nothing of its own to say (a menu item that
    # points elsewhere) just goes there - the admin still sees the page, to edit it
    if row["link_url"] and not body_md.strip() and not logged_in and not lang:
        return RedirectResponse(row["link_url"], status_code=302)
    # a members post (members.py): someone who can't read it all gets its
    # free preview, and the card to join or sign in, in place of the rest
    member = members.current()
    can_read = members.can_read(row, member, logged_in)
    if not can_read:
        # without a Members only from here line, its summary is the preview
        body_md = posts.split_members(body_md)[0] or (row["summary"] or "")
    html_body, toc_html = render_post(body_md)
    translation = None
    if lang:
        row, html_body, toc_html, translation = _in_language(req, hdrs, row, slug, lang, can_read, html_body, toc_html)
    _post_head(hdrs, row, s, slug, lang, own, row["summary"] or excerpt(html_body), is_live)

    if not is_live:
        why = "Draft" if not row["published"] else f"Scheduled for {row['scheduled_at'][:10]}"
        draft_notice = Alert(f"{why} — only visible to you or via a preview link.", "warning")
    else:
        draft_notice = None

    # caption and photo credit together ("A quiet morning · Photo by X on Pexels")
    cover_caption = images.figcaption_html(images.meta_for_url(row["cover_image"])) if row["cover_image"] else ""

    # the post as pages.py draws it - what replaces the plain body
    series = [p for p in posts.series_siblings(row["series_name"]) if logged_in or posts.is_live(p)]
    # a deck needs the whole screen, so one that's cut short for a visitor
    # (a members post) stays a page, with the way in
    lay = pages.render(row, s, new_tab_links(html_body) if s.get("links_new_tab") == "1" else html_body, toc_html, logged_in, series, deck=can_read)
    if lay.get("deck"):
        return Layout(lay["body"], *PostScripts(s, html_body), settings=s, logged_in=logged_in, bare=True)
    # a page as the homepage (Settings > Name and homepage > Homepage)
    at_home = req.url.path == "/"
    hides = _hidden_extras(row, s, can_read, at_home)
    hdrs.extend(lay["ld"])

    # header: breadcrumbs, then title, meta, tags, like button all together up top
    # none on the homepage itself
    crumbs = Breadcrumbs(post_crumbs(row, s)) if not at_home and "breadcrumbs" not in hides else None
    cover_width = pages.cover_width(row, s)
    opens_with_cover = bool(row["cover_image"]) and "meta" not in hides and cover_width in ("full", "screen")
    title = PostTitle(row, lay.get("title_href"))
    edit = EditPostLink(slug) if logged_in else None
    byline = _byline(row, s, relative, html_body)
    buttons = PostButtons(row, s, slug, hides, logged_in)
    if "meta" in hides:
        header_section = Div(crumbs, Div(edit, cls="flex justify-end") if logged_in else None)
    elif cover_width == "screen" and row["cover_image"]:
        header_section = Div(ScreenCover(row, s, hides, crumbs, title, edit, byline, cover_caption),
                             Div(buttons, cls="flex justify-end"))
    else:
        # edited on a later day: said so, beside the date
        updated = f" · {i18n.t('Updated {date}', date=format_date(row['updated_at'], relative))}" \
            if s.get("show_updated") == "1" and row["updated_at"] \
            and tz.local_date(row["updated_at"]) != tz.local_date(row["created_at"]) else ""
        header_section = PostHeader(
            row, s, hides, crumbs=crumbs, title=title, edit=edit, byline=byline, updated=updated, buttons=buttons,
            languages=LanguageLinks(slug, lang, s, translation is not None) if is_live and translate.enabled(s) else None,
            cover_width=cover_width, caption=cover_caption)

    # body: just the rendered content itself, clearly its own block
    # relative - a table of contents beside the post is placed against it
    toc_where = pages.toc_style(row, s)
    # a section wider than the column needs the margins: nothing sits beside the post
    nothing_beside = lay["wide"] or lay.get("has_wide_section")
    if lay.get("has_wide_section") and toc_where in ("side", "right"):
        toc_where = "top"
    toc_content = None if toc_where == "off" else lay.get("toc", toc_html)
    # beside the post: the contents, and the tag cloud and archive links if wanted there
    side_columns, side_after = SidePanels(
        s, toc_panel(toc_content, s.get("toc_fold")) if toc_content and toc_where in ("side", "right") else None,
        {"side": "left", "right": "right"}.get(toc_where), where="pages" if pages.counts_as_page(row, s) or at_home else "posts",
        shown="sides" not in hides, beside=not nothing_beside, own=row["sides"])
    side_author_here = side_places(s, "pages" if pages.counts_as_page(row, s) or at_home else "posts", "sides" not in hides,
                                   row["sides"]).get("side_author") in ("under", "left", "right")
    body_section = Div(
        lay["before"],
        *side_columns,
        TableOfContents(toc_content, "top", s.get("toc_fold")) if toc_content and toc_where == "top" else None,
        lay["body"],
        None if can_read else Div(MembersGate(row, s, member, own), cls=lay["column"]),
        cls="relative mt-6" if "meta" not in hides else "relative"
    )

    comments_section = PostComments(row, s, slug, lang, own, member, logged_in, relative,
                                    shown="comments" not in hides)
    # on the homepage the newsletter box is one of the things Settings adds back
    newsletter_here = "newsletter" in s.get("home_page_shows", "").split(",") if at_home \
        else "newsletter" not in hides and is_live and not lang

    page = Layout(
        ReadingProgress() if "progress" not in hides else None,
        # a cover that opens the page must come first to meet the header -
        # the notice goes under it there
        None if opens_with_cover else draft_notice,
        Article(Div(header_section, draft_notice if opens_with_cover else None, cls=lay["column"]), body_section),
        SoundButton(row["sound"]) if row["sound"] and can_read else None,
        # everything after the writing, one group in the reading column -
        # apart from the post as its sections are from each other, each
        # part as far from the next as the page's Space says
        Div(
            ReactAndShare(
                ReactionBar(slug, s, reactions.counts(slug), logged_in)
                if s.get("reactions_style") == "emoji" and is_live and "reactions" not in hides else None,
                None if "share" in hides else ShareButtons(config.BASE_URL + own, row["title"], s)),
            SupportButtons(s) if "support" not in hides else None,
            None if row["pinned"] and s.get("adsense_on_pages") != "1"
            else ads.AdSlot(s, "adsense_slot_post", logged_in, cls=""),
            # visitors only see parts that are live - not a scheduled one's title
            None if "series" in hides else SeriesNav(slug, series),
            # the tag cloud, archive and author where there's no room beside
            # the post: each its own part, so one shown beside leaves no gap
            *(side_after.children if side_after else ()),
            None if "related" in hides else RelatedPosts(posts.related_posts(slug, row["tags"]), relative),
            # once: the About the author side panel, where it's on, takes its place
            None if "author" in hides or side_author_here else AuthorBio(s),
            newsletter.Box(s) if newsletter_here else None,
            comments_section,
            WebMentions(slug, s) if is_live and not lang and "comments" not in hides else None,
            # a last section brings its own room below (SECTION_LAST): one gap, not two
            cls=f"{lay['column']} {'' if lay.get('ends_with_section') else pages.PART_GAP} {pages.PARTS} empty:hidden"
        ),
        *PostScripts(s, html_body),
        captcha.ApiScript(s) if comments_section and not extcomments.system(s) else None,
        settings=s, logged_in=logged_in, pinned_tree=posts.list_pinned_tree(), wide=lay["wide"],
        space=pages.section_space(row, s)
    )
    # a members post differs by who's reading - never kept by a cache
    if posts.clean_visibility(row["visibility"] if "visibility" in row.keys() else "") != "public" \
            and members.enabled(s):
        return FtResponse(page, headers={"Cache-Control": "private, no-store"})
    return page


def MembersGate(row, s, member, post_url):
    """In place of the rest of a members post: who it's for, and the way
    in - join (free), or sign in. The class is what search engines are
    told marks content behind a sign-in (seo.article_data)."""
    from soloblog import stripe_members
    paid = posts.clean_visibility(row["visibility"]) == "paid"
    back = quote(post_url)
    # paying is open: the plans, signing up on the way if need be
    plans = A(i18n.t("Become a paid member"), href=f"/membership?next={back}", cls="btn btn-primary btn-sm") \
        if paid and stripe_members.ready(s) else None
    if member:
        say = i18n.t("You're signed in as {email}. Paid members can read the rest.", email=member["email"])
        actions = [plans or A(i18n.t("Your account"), href="/account", cls="btn btn-sm")]
    else:
        say = i18n.t("Become a paid member to read the rest.") if paid else \
            i18n.t("Join to read the rest - it's free.")
        actions = [plans or A(i18n.t("Join"), href=f"/join?next={back}", cls="btn btn-primary btn-sm"),
                   A(i18n.t("Sign in"), href=f"/signin?next={back}", cls="btn btn-sm btn-ghost")]
    lock = NotStr('<svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" '
                  'stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path stroke-linecap="round" '
                  'stroke-linejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 '
                  '2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 '
                  '2.25 2.25Z"/></svg>')
    return Div(
        Span(lock, cls="text-primary"),
        P(i18n.t("This post is for paid members") if paid else i18n.t("This post is for members"),
          cls="text-lg font-semibold"),
        P(say, cls="text-sm text-base-content/70"),
        Div(*actions, cls="flex flex-wrap justify-center gap-2 mt-2"),
        cls="members-only card border-[length:var(--border)] border-base-300 bg-base-100 shadow-sm text-center "
            "items-center gap-2 p-6 mt-6"
    )


def ProtectedPage(row, s, hdrs, wrong=False):
    page_meta(hdrs, row["title"], row["summary"] or i18n.t("This post is protected with a password."),
              posts.url_for(row))
    hdrs.append(Meta(name="robots", content="noindex"))
    return Layout(Div(Div(
        H1(row["title"], cls=TITLE_CLS),
        P(row["summary"], cls="text-base-content/70") if row["summary"] else None,
        P(i18n.t("This post is protected with a password."), cls="text-sm text-base-content/60 mt-2"),
        Form(
            Div(Input(type="password", name="password", required=True, autofocus=True, autocomplete="off",
                      placeholder=i18n.t("Password"), aria_label=i18n.t("Password"),
                      cls="input input-sm join-item flex-1 min-w-0"),
                Button(i18n.t("Open"), type="submit", cls="btn btn-primary btn-sm join-item"), cls="join w-full"),
            P(i18n.t("That's not the password."), cls="text-xs text-error mt-2") if wrong else None,
            action=f"/post/{row['slug']}/unlock", method="post", cls="mt-3"
        ),
        cls="card-body p-6"), cls="card card-border bg-base-100 max-w-md mx-auto"),
        settings=s, logged_in=False, pinned_tree=posts.list_pinned_tree())


@ar.post("/post/{slug}/unlock")
def unlock(req, session, slug: str, password: str = ""):
    row = posts.get_post(slug)
    if not row or not posts.is_protected(row):
        return RedirectResponse("/", status_code=303)
    own = posts.url_for(row)
    # slow guessing down - a post password is usually short
    if not ratelimit.hit(f"ip:{ratelimit.client_ip(req)}", "unlock", limit=10, window_minutes=15) \
            or not secrets.compare_digest(password.strip().encode(), row["password"].encode()):
        return RedirectResponse(f"{own}?wrong=1", status_code=303)
    session["unlocked"] = (session.get("unlocked", []) + [slug])[-20:]
    return RedirectResponse(own, status_code=303)


@ar.post("/post/{slug}/like")
def like_post(req, session, slug: str):
    if auth.is_logged_in(session):
        # the UI already hides the like button for the admin - this is
        # the server-side half of that, in case someone hits the
        # endpoint directly
        row = posts.get_post(slug)
        return JSONResponse({"likes": row["likes"] if row else 0})
    row = posts.get_post(slug)
    if not row:
        return JSONResponse({"error": "not found"}, status_code=404)
    # this had no limit at all until a live test showed a script could
    # hammer it for an unbounded, instant like count - the UI's own
    # localStorage "already liked" flag (LikeButton) is a one-time
    # nudge for a real visitor, not a guard against a direct POST, so
    # the server needs its own. Generous on purpose - this just needs
    # to stop a script, not a genuinely enthusiastic reader.
    if not ratelimit.hit(f"ip:{ratelimit.client_ip(req)}", "like", limit=20, window_minutes=60):
        return JSONResponse({"likes": row["likes"]})
    likes = posts.increment_like(slug)
    return JSONResponse({"likes": likes})


@ar.post("/post/{slug}/react")
def react(req, session, slug: str, reaction: str = ""):
    """One emoji reaction. Readers are anonymous, so the server holds the
    line: each address adds each reaction to a post once a day, and at
    most 30 reactions an hour anywhere. Over either limit, the counts
    come back unchanged - nothing tells a script which limit it hit."""
    from soloblog import reactions
    row = posts.get_post(slug)
    if not row or not posts.is_live(row) or settings.get("reactions_style") != "emoji":
        return JSONResponse({"error": "not found"}, status_code=404)
    if reaction not in reactions.enabled_keys(settings.get("reaction_emojis")) or auth.is_logged_in(session):
        return JSONResponse({"counts": reactions.counts(slug)})
    ip = ratelimit.client_ip(req)
    if (ratelimit.hit(f"ip:{ip}", "react", limit=30, window_minutes=60)
            and ratelimit.hit(f"ip:{ip}", f"react:{slug}:{reaction}", limit=1, window_minutes=24 * 60)):
        return JSONResponse({"counts": reactions.add(slug, reaction)})
    return JSONResponse({"counts": reactions.counts(slug)})


@ar.post("/post/{slug}/comment")
def submit_comment(req, slug: str, body: str, author_name: str = "", email: str = "",
                    website: str = "", parent_id: int = 0, notify_replies: bool = False, captcha_token: str = ""):
    # the main comment form submits via htmx (in-place, no-scroll-jump
    # - see its hx_post/hx_target in view_post); a visitor's reply
    # (ReplyBox with VisitorReplyFields, above) is a plain form post
    # instead, like the admin's own reply - it needs a real
    # redirect back to #comments, not a tiny swap fragment with no
    # page around it. hx-request is the same header guards.py's own
    # require_login already checks for exactly this reason.
    is_htmx = req.headers.get("hx-request") == "true"

    # Every guard below - including the honeypot - answers with the
    # same response rather than a real error, on purpose: this is
    # public-facing, and revealing *why* a submission was rejected
    # (comments disabled, rate-limited, bot-trapped) would just help a
    # spammer calibrate their next attempt. The wording itself does
    # vary on one thing - whether email confirmation is actually
    # possible right now - but that's a site-wide setting, not
    # anything specific to this submission attempt, so it doesn't leak
    # anything a spammer could use.
    def respond(message, kind="success"):
        if is_htmx:
            return Span(message, id="comment-status", role="status",
                        cls=f"text-xs {STATUS_BESIDE} {'text-success' if kind == 'success' else 'text-error'}")
        return RedirectResponse(
            f"{posts.url_for_slug(slug)}?toast={quote(message)}&toast_type={kind}#comments", status_code=303
        )

    # without email set up there's no confirmation link to send, so the
    # comment goes straight to the queue for approval (auto_confirm) -
    # waiting for a link that never comes, it stayed stuck
    # a signed-in member's address is confirmed already: no email, no spam check
    member = members.current()
    if member:
        if not member["name"] and author_name.strip():
            members.update(member["id"], name=author_name.strip()[:100])
        author_name, email = member["name"] or author_name, member["email"]
    provider_configured = settings.get("email_provider") in ("smtp", "api") and not member
    posted = respond(i18n.t("Check your email to confirm your comment") if provider_configured
                     else i18n.t("Posted for approval"))
    # the form won't send these empty, so this is only a hand-made request - answered plainly
    if not body.strip():
        return respond(i18n.t("Write a comment first"), "error")
    if not author_name.strip():
        return respond(i18n.t("Add your name"), "error")
    if not mail.clean_email(email):
        return respond(i18n.t("That doesn't look like an email address"), "error")

    if settings.get("comments_enabled") != "1":
        return posted

    row = posts.get_post(slug)
    if not row or not row["comments_enabled"]:
        return posted

    if website.strip():
        # honeypot tripped - pretend it worked, don't tip off the bot
        return posted

    # the comments under a members post are for those who can read it
    if not members.can_read(row, member):
        return posted

    if not members.can_comment(member):
        return respond(i18n.t("Only paid members can comment.") if settings.get("members_comments") == "paid"
                       else i18n.t("Only members can comment."), "error")

    # unlike the guards above, this one says so - the check is right
    # there on the form, and a person who missed it needs to know
    if not member and not captcha.passes(settings.get_all(), captcha_token, ratelimit.client_ip(req)):
        return respond(i18n.t("Please complete the spam check"), "error")

    # on the blocklist: straight to Trash - nothing sent, nobody told,
    # and a false match can still be restored
    if comments.is_blocked(settings.get("comment_blocklist"), author_name, email, body):
        comments.trash_by_token(comments.add_comment(slug, author_name, email, body, auto_confirm=True,
                                                     parent_id=parent_id or None))
        return posted

    # a visitor's reply is just as capped as the author's own - see
    # MAX_REPLY_DEPTH above. The UI already hides Reply past that depth,
    # but that's presentation only; this is untrusted input, so the
    # cap gets enforced again here rather than trusted from the client.
    # Walking the parent chain (bounded by MAX_REPLY_DEPTH itself, so
    # never more than a few lookups) rather than storing a depth column
    # - depth is a property of the tree shape, not the row itself, and
    # would need updating on every reparent this app doesn't even have.
    if parent_id:
        parent = comments.get(parent_id)
        if not parent:
            return posted
        parent_depth = 0
        cur = parent
        while cur["parent_id"]:
            parent_depth += 1
            cur = comments.get(cur["parent_id"])
            if not cur:
                break
        if parent_depth >= MAX_REPLY_DEPTH:
            return posted

    if ratelimit.hit(f"ip:{ratelimit.client_ip(req)}", "comment", limit=5, window_minutes=60):
        token = comments.add_comment(slug, author_name, email, body,
                                      auto_confirm=not provider_configured, parent_id=parent_id or None,
                                      notify_replies=notify_replies and replymail.offered(),
                                      member_id=member["id"] if member else None)
        if provider_configured:
            confirm_url = f"{config.BASE_URL}/comment/confirm/{token}"
            site_title = settings.get("site_title")
            with i18n.in_site_language():
                subject = i18n.t("Confirm your comment on {site}", site=site_title)
                thanks = i18n.t("Thanks for your comment on “{title}”.", title=row["title"])
                confirm = i18n.t("Confirm your email address to send it in for approval:")
                ignore = i18n.t("If you didn't leave this comment, you can ignore this email.")
            mail.send_email(email.strip(), subject, f"{thanks}\n\n{confirm}\n{confirm_url}\n\n{ignore}\n")
        else:
            notify.comment_waiting(slug, author_name, body)

    return posted


@ar.get("/comments/giscus-theme")
def giscus_theme(t: str = "light"):
    """A Giscus theme in one of the site's own daisyUI themes' colors -
    giscus.app loads it into its comment frame."""
    return Response(extcomments.giscus_css(t), media_type="text/css",
                    headers={"Cache-Control": "public, max-age=3600", "Access-Control-Allow-Origin": "*"})


def BlueskyReply(c, relative, depth=0):
    """A reply from Bluesky, shaped like one of Soloblog's own comments."""
    return Div(
        Div(
            Span(REPLY_SVG, cls="inline-flex opacity-40 mr-1 align-middle") if depth else None,
            A(c["name"], href=f"https://bsky.app/profile/{c['handle']}", target="_blank", rel="nofollow ugc noopener",
              cls="link link-hover"),
            Span("Bluesky", cls="badge badge-ghost badge-xs ml-2"),
            A(Time(format_date(c["created_at"], relative)), href=c["url"], target="_blank", rel="noopener",
              cls="link link-hover text-xs text-base-content/60 ml-2"),
            cls="chat-header"
        ),
        Div(P(c["text"], cls="whitespace-pre-line"), cls="chat-bubble chat-bubble-neutral"),
        cls=f"chat !flex !flex-col !items-stretch gap-1.5 chat-start {REPLY_INDENT[min(depth, MAX_REPLY_DEPTH)]}".strip()
    )


@ar.get("/post/{slug}/bluesky")
def bluesky_replies(slug: str):
    """Loaded into the Comments card once it scrolls into view."""
    s = settings.get_all()
    row = posts.get_post(slug)
    if not row or not posts.is_live(row) or extcomments.system(s) != "bluesky":
        return Div()
    try:
        reply_url, replies = extcomments.thread(s["bluesky_handle"], config.BASE_URL + posts.url_for(row), slug)
    except Exception as e:
        log.warning("couldn't fetch replies: %s", e)
        return P(i18n.t("Couldn't reach Bluesky just now."), cls="text-sm text-base-content/50")
    relative = s.get("relative_dates") == "1"
    items = []

    def add(c, depth):
        items.append(BlueskyReply(c, relative, depth))
        for child in c["replies"]:
            add(child, depth + 1)
    for c in replies:
        add(c, 0)
    if not reply_url:
        return P(i18n.t("No conversation on Bluesky yet."), cls="text-sm text-base-content/50")
    return Div(
        *(items or [P(i18n.t("No replies yet."), cls="text-sm text-base-content/50")]),
        Div(A(i18n.t("Reply on Bluesky"), href=reply_url, target="_blank", rel="noopener", cls="btn btn-primary btn-sm"),
            cls="flex justify-end mt-3"),
        cls="flex flex-col gap-3"
    )


@ar.get("/comment/unsubscribe/{token}")
def unsubscribe_page(session, hdrs, token: str):
    """An email's "stop these emails" link asks first - a link scanner
    opening it shouldn't unsubscribe anyone."""
    s = settings.get_all()
    page_meta(hdrs, "Reply emails", path="/comment/unsubscribe")
    return Layout(Div(Div(
        H1("Stop reply emails?", cls="text-xl font-bold"),
        P("You won't get any more emails about replies to your comments on this site.",
          cls="text-sm text-base-content/60 mb-3"),
        Form(Button(CHECK_SVG, Span("Stop reply emails", cls="ml-1"), type="submit", cls="btn btn-primary btn-sm"),
             action=f"/comment/unsubscribe/{quote(token)}", method="post", cls="flex justify-end"),
        cls="card-body p-6"), cls="card card-border bg-base-100 max-w-sm mx-auto"),
        settings=s, logged_in=auth.is_logged_in(session), pinned_tree=posts.list_pinned_tree())


@ar.post("/comment/unsubscribe/{token}")
def unsubscribe(session, token: str):
    s = settings.get_all()
    row = comments.unsubscribe(token)
    message = ("Done - no more reply emails." if row
               else "That link has expired, but there's nothing to stop.")
    return Layout(Div(Div(H1("Reply emails", cls="text-xl font-bold"), Alert(message, "success" if row else "info"),
                          cls="card-body p-6"), cls="card card-border bg-base-100 max-w-sm mx-auto"),
                  settings=s, logged_in=auth.is_logged_in(session), pinned_tree=posts.list_pinned_tree())


@ar.get("/comment/confirm/{token}")
def confirm_comment(hdrs, token: str):
    row = comments.confirm(token)
    if not row:
        page_meta(hdrs, "Confirmation link", path=f"/comment/confirm/{token}")
        return Layout(
            EmptyState("That confirmation link is invalid or has already been used.", "❓"),
            A("Back home", href="/", cls="link"),
            settings=settings.get_all(), pinned_tree=posts.list_pinned_tree()
        )
    notify.comment_waiting(row["post_slug"], row["author_name"], row["body"])
    return RedirectResponse(
        f"{posts.url_for_slug(row['post_slug'])}?toast={quote('Comment confirmed - now awaiting approval')}"
        f"&toast_type=success#comments",
        status_code=303
    )


@ar.post("/post/{slug}/reply")
def submit_reply(session, slug: str, parent_id: int, body: str, redirect_to: str = ""):
    ok, resp = require_login(session)
    if resp:
        return resp
    author_label = settings.get("author_name") or settings.get("site_title")
    reply_id = comments.add_reply(slug, parent_id, author_label, body)
    replymail.send_for([reply_id])
    # a reply to someone on the fediverse goes back to them there too
    from soloblog import fediverse
    fediverse.reply(reply_id)
    # redirect_to (a hidden field on ReplyBox's form, ui) lets
    # the admin comments list send the admin back to the queue instead
    # of the live post page - only ever set by our own admin-rendered
    # markup, but still checked for a leading "/" rather than trusted
    # outright, same caution any redirect target deserves
    target = redirect_to if is_local_path(redirect_to) else f"{posts.url_for_slug(slug)}#comments"
    base, frag = (target.split("#", 1) + [""])[:2]
    sep = "&" if "?" in base else "?"
    frag_part = f"#{frag}" if frag else ""
    return RedirectResponse(f"{base}{sep}toast={quote('Reply posted')}&toast_type=success{frag_part}", status_code=303)


def FeedLinks(hdrs, title, path):
    hdrs.append(Link(rel="alternate", type="application/rss+xml", title=title, href=path))


@ar.get("/tag/{tag}")
def tag_page(session, hdrs, tag: str, page: int = 1):
    s = settings.get_all()
    if not tag.strip():
        return FtResponse(ErrorPage(404, s, auth.is_logged_in(session), posts.list_pinned_tree()), status_code=404)
    per_page = page_size(s)
    matches = posts.list_tagged(tag)
    total_pages = max(1, -(-len(matches) // per_page))
    page = min(max(1, page), total_pages)
    suffix = f" (page {page})" if page > 1 else ""
    page_meta(hdrs, i18n.t('Tagged "{tag}"', tag=tag) + suffix, i18n.t('Posts tagged "{tag}".', tag=tag),
              tag_url(tag) + (f"?page={page}" if page > 1 else ""))
    FeedLinks(hdrs, f'{s["site_title"]}: #{tag}', tag_url(tag) + "/rss")
    relative = s.get("relative_dates") == "1"
    shown = matches[(page - 1) * per_page: page * per_page]
    roll_view = PostRoll(shown, relative, s.get("roll_style", "list"), i18n.t('Nothing tagged "{tag}" yet.', tag=tag),
                         "🏷️", s.get("body_width"))
    return Layout(Breadcrumbs([(i18n.t("Home"), "/"), (i18n.t("Tags"), "/tags"), (f"#{tag}", None)]) if s.get("breadcrumbs") != "off" else None,
                  Div(Div(H1(i18n.t('Tagged "{tag}"', tag=tag), cls=LIST_TITLE_CLS),
                          A(RSS_SVG, Span("RSS", cls="ml-1"), href=tag_url(tag) + "/rss", cls="btn btn-ghost btn-xs"),
                          cls="flex items-center justify-between gap-3"),
                      roll_view, cls=pages.PARTS),
                  Pagination(page, total_pages, tag_url(tag)),
                  settings=s, logged_in=auth.is_logged_in(session), pinned_tree=posts.list_pinned_tree())


@ar.get("/tags")
def tags_index(session, hdrs):
    s = settings.get_all()
    page_meta(hdrs, i18n.t("Tags"), i18n.t("Every topic on this blog."), "/tags")
    # the same neutral badge-soft as a post's own tags (ui.TagBadge), sized by use
    body = TagCloud(posts.tag_counts()) or EmptyState(i18n.t("No tags yet."), "🏷️")
    return Layout(Breadcrumbs([(i18n.t("Home"), "/"), (i18n.t("Tags"), None)]) if s.get("breadcrumbs") != "off" else None,
                  Div(H1(i18n.t("Tags"), cls=LIST_TITLE_CLS), body, cls=pages.PARTS),
                  settings=s, logged_in=auth.is_logged_in(session), pinned_tree=posts.list_pinned_tree())


@ar.get("/wiki")
def wiki_index(session, hdrs):
    if settings.get("home_page") == posts.WIKI_HOME:
        return RedirectResponse("/", status_code=301)
    return wiki_home(session, hdrs, at_home=False)


def wiki_home(session, hdrs, at_home: bool):
    """The wiki's front page: the notes to start from (pinned ones, and
    the most linked to), what
    changed lately and what's read most, its topics, then every note A to
    Z. At /wiki, or the homepage (Settings > Name and homepage > Homepage)."""
    s = settings.get_all()
    logged_in = auth.is_logged_in(session)
    relative = s.get("relative_dates") == "1"
    title = s["site_title"] if at_home else i18n.t("Wiki")
    page_meta(hdrs, title, i18n.t("Every page in the wiki, A to Z."),
              "/" if at_home else "/wiki")
    rows = [p for p in posts.list_posts(include_drafts=logged_in) if p["in_wiki"]]
    if not rows:
        return Layout(Div(H1(title, cls=TITLE_CLS),
                          EmptyState("No wiki pages yet - switch on In the wiki in a post's settings." if logged_in
                                     else i18n.t("No wiki pages yet."), "📚"), cls=pages.PARTS),
                      settings=s, logged_in=logged_in, pinned_tree=posts.list_pinned_tree())
    live = [p for p in rows if posts.is_live(p)]
    edited = lambda p: p["updated_at"] or p["created_at"]  # noqa: E731
    latest = max((edited(p) for p in live), default="")
    from soloblog.db import get_db
    linked = dict(get_db().execute("SELECT to_slug, COUNT(*) FROM post_links GROUP BY to_slug").fetchall())

    def card(p):
        return Div(Div(
            H3(A(p["title"], href=posts.url_for(p), cls="link link-hover"), cls="font-semibold"),
            (teaser := posts.teaser(p)) and P(teaser, cls="text-sm text-base-content/70 line-clamp-2 flex-none"),
            cls="card-body p-4 gap-1"), cls="card card-border bg-base-100")

    def ranked(label, items, note):
        if not items:
            return None
        return Section(
            H2(label, cls="text-base font-semibold text-accent mb-2"),
            Ol(*[Li(A(p["title"], href=posts.url_for(p), cls="link link-hover min-w-0 truncate"),
                    Span(note(p), cls="text-xs text-base-content/50 shrink-0"),
                    cls="flex items-baseline justify-between gap-3 py-1.5 border-b border-base-300 last:border-0")
                 for p in items], cls="text-sm"),
            cls="card card-border bg-base-100 p-4")

    recent = sorted(live, key=edited, reverse=True)[:6]
    read = sorted((p for p in live if p["views"]), key=lambda p: -p["views"])[:6]
    hubs = sorted((p for p in live if linked.get(p["slug"])), key=lambda p: -linked[p["slug"]])[:6]
    # the pinned notes, and the most linked to until there's a row of them
    start = [p for p in live if p["pinned"]][:6]
    start += [p for p in hubs if p not in start][:max(0, 3 - len(start))]
    tags = {}
    for p in live:
        for t in (x.strip() for x in (p["tags"] or "").split(",")):
            if t:
                tags[t] = tags.get(t, 0) + 1

    groups = {}
    for p in sorted(rows, key=lambda p: p["title"].lower()):
        letter = p["title"][:1].upper()
        groups.setdefault(letter if letter.isalpha() else "#", []).append(p)
    a_to_z = Div(*[Div(H3(letter, cls="text-sm font-semibold text-accent mb-1"),
                       Ul(*[Li(A(p["title"], href=posts.url_for(p), cls="link link-hover"),
                               Span(" · draft", cls="text-xs text-base-content/50") if not posts.is_live(p) else None)
                            for p in items], cls="space-y-1 mb-4"),
                       cls="break-inside-avoid")
                   for letter, items in groups.items()], cls="columns-2 sm:columns-3 gap-6 text-sm")

    centered = s.get("header_align") in ("center", "stacked")
    return Layout(
        Breadcrumbs([(i18n.t("Home"), "/"), (i18n.t("Wiki"), None)])
        if s.get("breadcrumbs") != "off" and not at_home else None,
        # its parts as far apart as the site's Space says, as a post's are
        Div(
            Div(H1(title, cls=TITLE_CLS),
                P(s["tagline"], cls="text-base-content/70 mt-1") if at_home and s["tagline"] else None,
                P(i18n.t("{count} pages · last edited {date}", count=len(live), date=format_date(latest, relative))
                  if latest else "", cls="text-xs text-base-content/50 mt-2"),
                cls="text-center" if centered else None),
            Section(H2(i18n.t("Start here"), cls="text-base font-semibold text-accent mb-2"),
                    Div(*[card(p) for p in start], cls="grid sm:grid-cols-2 lg:grid-cols-3 gap-3")) if start else None,
            Div(ranked(i18n.t("Recently edited"), recent, lambda p: format_date(edited(p), relative)),
                ranked(i18n.t("Most read"), read, lambda p: "") if read else
                ranked(i18n.t("Most linked"), hubs, lambda p: ""),
                cls=f"grid md:grid-cols-2 {pages.PARTS_SPACE}"),
            Section(H2(i18n.t("Topics"), cls="text-base font-semibold text-accent mb-2"),
                    Div(*[TagBadge(t) for t in sorted(tags, key=str.lower)], cls="flex flex-wrap gap-1.5")) if tags else None,
            Section(H2(i18n.t("Every page, A to Z"), cls="text-base font-semibold text-accent mb-3"), a_to_z,
                    cls="card card-border bg-base-100 p-4"),
            cls=pages.PARTS),
        settings=s, logged_in=logged_in, pinned_tree=posts.list_pinned_tree()
    )


@ar.get("/archive")
def archive(session, hdrs):
    """Every post, grouped by year and then month in the site's
    timezone - the whole blog on one page."""
    from soloblog import tz
    from datetime import datetime as _dt
    s = settings.get_all()
    page_meta(hdrs, i18n.t("Archive"), i18n.t("Every post, by date."), "/archive")
    years = {}
    for p in posts.list_roll_all():
        try:
            stamp = p["created_at"]
            when = _dt.fromisoformat(stamp[:19].rstrip("Z"))
            when = tz.to_local(when) if len(stamp) > 10 else when
        except ValueError:
            continue
        years.setdefault(when.year, {}).setdefault(when.month, []).append((when, p))
    sections = []
    for year in sorted(years, reverse=True):
        months = years[year]
        count = sum(len(v) for v in months.values())
        sections.append(Section(
            H2(str(year), Span(i18n.plural(count, "{n} post", "{n} posts"),
                               cls="text-xs font-normal text-base-content/50 ml-2"),
               cls="text-lg font-bold mb-2"),
            # id - where ArchiveLinks (the month index above, the homepage) lead
            *[Div(H3(i18n.months(full=True)[m - 1], id=f"{year}-{m:02d}",
                     cls="text-sm font-semibold text-accent mt-3 mb-1 scroll-mt-4"),
                  Ul(*[Li(Span(f"{when.day:02d}", cls="text-xs text-base-content/50 font-mono"),
                          A(p["title"], href=posts.url_for(p), cls="link link-hover"),
                          cls="list-row py-1.5")
                       # a row opens its post from anywhere on it (ROW_LINKS_JS)
                       for when, p in months[m]], data_click_rows=True, cls="list [&_li]:cursor-pointer"))
              for m in sorted(months, reverse=True)]
        ))
    return Layout(Breadcrumbs([(i18n.t("Home"), "/"), (i18n.t("Archive"), None)]) if s.get("breadcrumbs") != "off" else None,
                  Div(H1(i18n.t("Archive"), cls=LIST_TITLE_CLS),
                      # every month at a glance, each a link down to it
                      ArchiveLinks(month_counts(posts.list_roll_all())) if sections else None,
                      *(sections or [EmptyState(i18n.t("Nothing published yet."))]), cls=pages.PARTS),
                  settings=s, logged_in=auth.is_logged_in(session), pinned_tree=posts.list_pinned_tree())


@ar.get("/series/{slug}")
def series_page(session, hdrs, slug: str):
    """Every part of a series, in order - where a post's breadcrumb and
    its "Part 2 of 4 in ..." label both lead."""
    s = settings.get_all()
    logged_in = auth.is_logged_in(session)
    name = posts.find_series(slug)
    parts = [p for p in posts.series_siblings(name) if logged_in or posts.is_live(p)] if name else []
    if not parts:
        return FtResponse(ErrorPage(404, s, logged_in, posts.list_pinned_tree()), status_code=404)
    page_meta(hdrs, name, i18n.plural(len(parts), "A series in {n} part.", "A series in {n} parts."), f"/series/{slug}")
    relative = s.get("relative_dates") == "1"
    return Layout(
        Breadcrumbs([(i18n.t("Home"), "/"), (name, None)]),
        H1(name, cls=LIST_TITLE_CLS),
        P(i18n.plural(len(parts), "A series in {n} part, in reading order.", "A series in {n} parts, in reading order."),
          cls="text-sm text-base-content/60 mb-4"),
        PostRoll(parts, relative, s.get("roll_style", "list"), i18n.t("Nothing in this series yet."), "📚",
                 s.get("body_width"), grouped=False),
        settings=s, logged_in=logged_in, pinned_tree=posts.list_pinned_tree()
    )


@ar.get("/rss")
def rss():
    from soloblog import feeds
    return Response(feeds.rss(posts.list_roll_all(feeds.FEED_SIZE), settings.get_all()), media_type="application/rss+xml; charset=utf-8")


@ar.get("/tag/{tag}/rss")
def tag_rss(tag: str):
    from soloblog import feeds
    s = settings.get_all()
    return Response(feeds.rss(posts.list_tagged(tag), s, f"{s['site_title']}: #{tag}", tag_url(tag) + "/rss"),
                    media_type="application/rss+xml; charset=utf-8")


@ar.get("/atom.xml")
def atom():
    from soloblog import feeds
    return Response(feeds.atom(posts.list_roll_all(feeds.FEED_SIZE), settings.get_all()), media_type="application/atom+xml; charset=utf-8")


@ar.get("/feed.json")
def json_feed():
    from soloblog import feeds
    return Response(feeds.json_feed(posts.list_roll_all(feeds.FEED_SIZE), settings.get_all()),
                    media_type="application/feed+json; charset=utf-8")


@ar.get("/sitemap.xml")
def sitemap():
    def entry(path, stamp=""):
        mod = f"<lastmod>{escape(stamp[:10])}</lastmod>" if stamp else ""
        return f"  <url><loc>{escape(config.BASE_URL + path)}</loc>{mod}</url>"
    # a post kept out of search engines isn't offered to them either
    live = [p for p in posts.list_posts() if not p["noindex"]]
    lines = [entry("/"), entry("/archive"), entry("/tags")] + ([entry("/blog")] if settings.get("home_page") else [])
    # the homepage's own post is "/", listed above
    lines += [entry(posts.url_for(p), p["updated_at"] or p["created_at"]) for p in live if posts.url_for(p) != "/"]
    if translate.enabled():
        offered = set(translate.targets())
        from soloblog.db import get_db
        live_slugs = {p["slug"] for p in live if posts.is_live(p)}
        lines += [entry(f"/{r['lang']}/post/{r['slug']}", r["translated_at"])
                  for r in get_db().execute("SELECT slug, lang, translated_at FROM post_translations")
                  if r["slug"] in live_slugs and r["lang"] in offered]
    lines += [entry(tag_url(t)) for t, _ in posts.tag_counts()]
    lines += [entry(f"/series/{posts.series_slug(n)}") for n in sorted({p["series_name"] for p in live if p["series_name"]})]
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "\n".join(lines) + "\n</urlset>")
    return Response(content=xml, media_type="application/xml; charset=utf-8")


@ar.get("/healthz")
async def healthz():
    # for Docker HEALTHCHECK and hosts' health checks (Render, Railway,
    # Fly) - touches the database so "up" means "can actually serve".
    # async, so it's answered at once, never queued behind pages being
    # made (app.PAGE_THREADS): a busy minute isn't a site that's down
    from soloblog.db import get_db
    get_db().execute("SELECT 1").fetchone()
    return JSONResponse({"status": "ok", "version": config.VERSION})


@ar.get("/ads.txt")
def ads_txt():
    """AdSense's authorized-seller file - only once a publisher ID is set."""
    client = settings.get("adsense_client")
    if not ads.valid_client(client):
        return Response("Not found", status_code=404, media_type="text/plain")
    return Response(ads.ads_txt(client), media_type="text/plain")


@ar.get("/favicon.ico")
def favicon():
    """Some browsers ask here whatever the page says - your favicon, or
    the one made for you (appicon.py)."""
    s = settings.get_all()
    return RedirectResponse(s.get("favicon_url") or "/icon-32.png", status_code=302)


@ar.get("/robots.txt")
def robots():
    if settings.get("search_noindex") == "1" or config.DEMO_MODE:
        return Response("User-agent: *\nDisallow: /\n", media_type="text/plain")
    return Response(f"User-agent: *\nAllow: /\nDisallow: /admin\nSitemap: {config.BASE_URL}/sitemap.xml\n",
                    media_type="text/plain")


@ar.get("/manifest.webmanifest")
def web_manifest():
    from soloblog import appicon
    return Response(appicon.manifest(settings.get_all()), media_type="application/manifest+json")


@ar.get("/icon-{size}.png")
def app_icon(size: int):
    from soloblog import appicon
    data = appicon.png(settings.get_all(), size)
    if data is None:
        return Response("Not found", status_code=404, media_type="text/plain")
    return Response(data, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})


# share cards (cards.py): a post's, for one with no image of its own, and
# the site's, for its other pages - only for what's live
@ar.get("/card/{slug}.png")
def share_card(slug: str):
    from soloblog import cards
    row = posts.get_post(slug)
    data = cards.post_card(row) if row and posts.is_live(row) else None
    if data is None:
        return Response("Not found", status_code=404, media_type="text/plain")
    return Response(data, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})


@ar.get("/card.png")
def site_share_card():
    from soloblog import cards
    data = cards.site_card()
    if data is None:
        return Response("Not found", status_code=404, media_type="text/plain")
    return Response(data, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})


@ar.get("/uploads/{filename}")
def uploaded_file(filename: str, w: int = 0):
    if not images.plain_name(filename):
        return Response("Not found", status_code=404)
    path = os.path.join(config.uploads_dir(), filename)
    # not on this disk (a host that starts every deploy empty) - the
    # bucket has every image, so fetch it back once and keep it here
    if not os.path.exists(path) and not storage.fetch_upload(filename):
        # renamed in the media library: the old address still works
        if new := images.renamed_to(filename):
            return RedirectResponse(f"/uploads/{new}" + (f"?w={w}" if w else ""), status_code=301)
        return Response("Not found", status_code=404)
    # /uploads/ itself, or the trash folder in it: only files are served
    if not os.path.isfile(path):
        return Response("Not found", status_code=404)
    # ?w=400 / ?w=800 - a smaller copy for cards and srcset (images.sized)
    if w:
        path = images.sized(filename, w)
    # an hour, not forever: an image can be rotated or cropped in place
    # (images.edit_image) - after that, browsers check back and get it
    headers = {"Cache-Control": "public, max-age=3600"}
    # Uploads are made by this site, but a restored backup or a bucket can
    # hold anything, and it's served from the site's own address. Opened
    # as a page, nothing in a file may run (an SVG's or an HTML file's
    # script would act as the site): sandbox. Not a PDF - a browser's
    # PDF reader won't open in a sandbox, and a PDF can't script the site.
    kind = mimetypes.guess_type(path)[0] or ""
    if kind != "application/pdf":
        headers["Content-Security-Policy"] = "sandbox; default-src 'none'; style-src 'unsafe-inline'; img-src data:"
    # and what isn't a picture, sound, video or PDF is saved, not shown
    if kind == "application/pdf" or kind.split("/")[0] in ("image", "audio", "video"):
        return FileResponse(path, headers=headers)
    return FileResponse(path, headers=headers, media_type="application/octet-stream",
                        filename=os.path.basename(path))


@ar.get("/demo/style/{key}")
def demo_style(key: str):
    """The public demo only: try a settings preset, just for this visitor
    (app.PresetPreview) - nothing changes for anyone else."""
    from soloblog import presets
    from soloblog.app import PresetPreview
    if not config.DEMO_MODE or not presets.find(key):
        return Response("Not found", status_code=404)
    r = RedirectResponse("/", status_code=303)
    r.set_cookie(PresetPreview.COOKIE, key, httponly=True, samesite="lax", path="/",
                 secure=config.BASE_URL.startswith("https://"))
    return r


@ar.get("/demo/style")
def demo_style_off():
    from soloblog.app import PresetPreview
    if not config.DEMO_MODE:
        return Response("Not found", status_code=404)
    r = RedirectResponse("/", status_code=303)
    r.delete_cookie(PresetPreview.COOKIE, path="/")
    return r
