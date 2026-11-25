from soloblog.actions import on_attrs, EL
import hashlib
import re
import threading
from collections import OrderedDict
import math

from soloblog import config, i18n, sections
from datetime import datetime
from soloblog.tz import utcnow
import markdown
import pymdownx.emoji
import nh3

# the admin is the only one writing posts, but nh3 stays anyway - it's
# free insurance against a stray <script> pasted in from somewhere else,
# and comments ARE public input that goes through the same renderer.
ALLOWED_TAGS = {
    "p", "br", "hr", "strong", "em", "del", "code", "pre",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "blockquote",
    "a", "img", "table", "thead", "tbody", "tr", "th", "td", "span", "div",
    # footnotes, definition lists, abbreviations
    "sup", "sub", "dl", "dt", "dd", "abbr",
    # ==highlight==, ^^inserted^^, ++keyboard keys++, and content tabs
    # (radio buttons and their labels - posts are only ever the admin's)
    "mark", "ins", "kbd", "input", "label",
    # ??? "Title" - a heading that opens to its text (pymdownx.details)
    "details", "summary",
}
ALLOWED_ATTRS = {
    "a": {"href", "title", "class"},  # rel is handled by nh3 itself; class for footnote links
    "img": {"src", "alt", "title"},
    "code": {"class"},               # codehilite's language class
    "pre": {"class"},                # "mermaid" - see _MERMAID below
    "span": {"class"},
    "div": {"class"},
    "p": {"class"},                  # an admonition's own title line
    "sup": {"id"}, "li": {"id"},     # footnote anchors
    "abbr": {"title"},
    "kbd": {"class"},
    "input": {"type", "id", "name", "checked"}, "label": {"for"},
    "h1": {"id"}, "h2": {"id"}, "h3": {"id"}, "h4": {"id"}, "h5": {"id"}, "h6": {"id"},
    "details": {"open"},
}

# everything a post can use beyond plain markdown - all from
# Python-Markdown itself, no extra dependency: footnotes[^1], term/
# definition lists, *[HTML]: abbreviations, and !!! note callouts
# pymdown-extensions: :emoji:, ==highlight==, ^superscript^ and ^^insert^^,
# ~subscript~ and ~~strikethrough~~, ++ctrl+c++ keys, (c) -> © and friends,
# and === "Tab" content tabs. Not snippets - it reads files from the server.
EXTRAS = ["pymdownx.emoji", "pymdownx.mark", "pymdownx.caret", "pymdownx.tilde", "pymdownx.keys",
          "pymdownx.smartsymbols", "pymdownx.tabbed"]
# SuperFences and Highlight in place of fenced_code and codehilite: the
# same highlighted code, but a code block inside a tab or a callout works
POST_EXTENSIONS = ["pymdownx.superfences", "pymdownx.highlight", "pymdownx.details", "tables", "toc", "footnotes",
                   "def_list", "abbr",
                   "admonition", "sane_lists"] + EXTRAS
# :smile: and the rest of GitHub's shortcodes, as the emoji character
# itself - nothing to download, and it looks like the reader's own emoji
EXTRAS_CONFIG = {"pymdownx.emoji": {"emoji_index": pymdownx.emoji.gemoji,
                                    "emoji_generator": pymdownx.emoji.to_alt},
                 "pymdownx.tabbed": {"alternate_style": True},
                 "pymdownx.highlight": {"css_class": "codehilite"}}

# ```mermaid fences become a <pre class="mermaid"> before markdown ever
# sees them - codehilite would otherwise turn them into highlighted
# code. With diagrams off (Settings > Editor) they simply stay a plain
# code block; with them on, mermaid.js draws them in the browser.
_MERMAID = re.compile(r"^```mermaid[ \t]*\n(.*?)^```[ \t]*$", re.M | re.S)
# ```gallery [style] [auto] fences - gallery.py turns their image lines into a
# gallery; "auto" moves a slider along by itself
_GALLERY = re.compile(r"^```gallery(?:[ \t]+([a-z]+))?(?:[ \t]+(auto))?[ \t]*\n(.*?)^```[ \t]*$", re.M | re.S)
# a ````-or-longer (or ~~~) fence - how a post shows a ```gallery or
# ```mermaid block as an example instead of running it
_OUTER_FENCE = re.compile(r"^(`{4,}|~{3,})[^\n]*\n.*?^\1[ \t]*$", re.M | re.S)
# fenced code and inline code - math is never looked for inside these
_CODE = re.compile(r"(^```.*?^```[ \t]*$|`[^`\n]+`)", re.M | re.S)
# $$display$$, and $inline$ with pandoc's rule: no space just inside
# either $, and no digit right after the closing one - so "$5 and $10"
# is still just money
_MATH_DISPLAY = re.compile(r"\$\$(.+?)\$\$", re.S)
_MATH_INLINE = re.compile(r"(?<![\\$])\$(?=\S)([^$\n]+?)(?<=\S)\$(?!\d)")
_TASK = re.compile(r"<li>\[( |x|X)\] ")
_STRIKE = re.compile(r"~~(?=\S)(.+?)(?<=\S)~~")
# code, inline or a block - shown as typed, so ~~ in it stays ~~
_CODE_HTML = re.compile(r"(<pre\b.*?</pre>|<code\b.*?</code>)", re.S)


# a list item's first line - a numbered list that interrupts a paragraph
# has to start at 1, so "...in\n2019. It was great" stays a sentence
_ITEM = re.compile(r"[ ]{0,3}(?:[-*+]|1[.)])[ \t]+\S")
_RULE = re.compile(r"[ ]{0,3}([-*_])(?:[ \t]*\1){2,}[ \t]*$")
_FENCE = re.compile(r"[ ]{0,3}(`{3,}|~{3,})")
_QUOTE = re.compile(r"(?:[ ]{0,3}>[ ]?)+")
# a line that starts something of its own, so a list under it isn't "after a paragraph"
_NOT_PARAGRAPH = ("#", "<", "|", "!!!", "???", "===", ": ", ":\t", "{:", "*[", "[^")
_REFERENCE = re.compile(r"\[[^\]]+\]:")


def _list_after_paragraph(body: str) -> str:
    """Markdown wants an empty line between a paragraph and the list under
    it, and runs the two together without one. This adds the line - never
    inside code, a table or a list that's already going."""
    out, fence, in_list, gap, prev = [], None, False, False, ""
    for line in body.split("\n"):
        f = _FENCE.match(line)
        if fence:
            if f and f.group(1)[0] == fence[0] and len(f.group(1)) >= len(fence) and not line.strip(f.group(1)[0] + " \t"):
                fence = None
            out.append(line)
            continue
        if f:
            fence, in_list = f.group(1), False
            out.append(line)
            prev = ""
            continue
        q = _QUOTE.match(line)
        prefix = q.group(0) if q else ""
        text = line[len(prefix):]
        before = _QUOTE.match(prev)
        prev_prefix = before.group(0) if before else ""
        prev_text = prev[len(prev_prefix):]
        if prefix.count(">") != prev_prefix.count(">"):
            in_list = False
        if not text.strip():
            gap = True
        else:
            # a paragraph after an empty line ends the list; an indented one belongs to its item
            if in_list and gap and not text.startswith((" ", "\t")) and not _ITEM.match(text):
                in_list = False
            gap = False
        if text.strip() and _ITEM.match(text) and not _RULE.match(text):
            if (not in_list and prev_text.strip() and prefix.count(">") == prev_prefix.count(">")
                    and not _ITEM.match(prev_text) and not _RULE.match(prev_text)
                    and not prev_text.startswith((" " * 4, "\t"))
                    and not prev_text.lstrip().startswith(_NOT_PARAGRAPH)
                    and not _REFERENCE.match(prev_text.lstrip())
                    and "|" not in prev_text):
                out.append(prefix.rstrip())
            in_list = True
        out.append(line)
        prev = line
    return "\n".join(out)


def _protect(body: str, math: bool):
    """Pulls mermaid blocks and (when math is on) TeX out of the body,
    leaving alphanumeric placeholders markdown won't touch, so neither
    gets mangled by emphasis or escaping. _restore puts them back after
    sanitizing - escaped, since that html skips nh3."""
    from html import escape
    saved = []

    def keep(html):
        saved.append(html)
        return f"SOLOBLOGKEEP{len(saved) - 1}X"

    def gallery_block(m):
        from soloblog import gallery
        from soloblog import settings
        style = m.group(1) or settings.get("gallery_style") or "grid"
        return "\n" + keep(gallery.render(style, gallery.parse(m.group(3)), f"gallery-{len(saved)}",
                                          auto=bool(m.group(2)))) + "\n"

    # only outside the longer fences - inside one they're just an example
    parts, last = [], 0
    for m in _OUTER_FENCE.finditer(body):
        parts += [body[last:m.start()], m.group(0)]
        last = m.end()
    parts.append(body[last:])
    for i in range(0, len(parts), 2):
        parts[i] = _MERMAID.sub(lambda m: "\n" + keep(f'<pre class="mermaid">{escape(m.group(1))}</pre>') + "\n", parts[i])
        parts[i] = _GALLERY.sub(gallery_block, parts[i])
    body = "".join(parts)
    if not math:
        return body, saved
    parts = _CODE.split(body)
    for i in range(0, len(parts), 2):  # even parts are outside code
        parts[i] = _MATH_DISPLAY.sub(lambda m: keep(f'<div class="math-display">\\[{escape(m.group(1))}\\]</div>'),
                                     parts[i])
        parts[i] = _MATH_INLINE.sub(lambda m: keep(f'<span class="math-inline">\\({escape(m.group(1))}\\)</span>'),
                                    parts[i])
    return "".join(parts), saved


def _restore(html: str, saved: list) -> str:
    for i, piece in enumerate(saved):
        # a block placeholder on its own line comes back wrapped in <p>
        html = html.replace(f"<p>SOLOBLOGKEEP{i}X</p>", piece).replace(f"SOLOBLOGKEEP{i}X", piece)
    return html


# a URL alone on its own line - as plain text, or as markdown's <url> link
_LONE_URL = re.compile(r'<p>(?:<a href="([^"]+)"[^>]*>[^<]*</a>|(https?://[^\s<]+|/uploads/[^\s<]+))</p>')
def _fb_plugin(url: str) -> str:
    """Facebook's own embed page for a post or a video - the same thing
    its SDK would build, without loading the SDK."""
    from urllib.parse import quote
    kind = "video" if re.search(r"/videos?/|/watch|/reel/|fb\.watch", url) else "post"
    return f"https://www.facebook.com/plugins/{kind}.php?href={quote(url, safe='')}&show_text=true&width=500"


def _osm(m) -> str:
    """An OpenStreetMap link's #map=zoom/lat/lon as its embeddable map."""
    zoom, lat, lon = int(m.group(1)), float(m.group(2)), float(m.group(3))
    span = 360 / 2 ** max(1, min(zoom, 19))
    bbox = f"{lon - span:.5f},{lat - span / 2:.5f},{lon + span:.5f},{lat + span / 2:.5f}"
    return f"https://www.openstreetmap.org/export/embed.html?bbox={bbox}&layer=mapnik&marker={lat:.5f},{lon:.5f}"


def _google_map(m) -> str:
    """A Google Maps place or @lat,lon link as Google's keyless embed."""
    from urllib.parse import quote
    place, lat, lon, zoom = m.group(1), m.group(2), m.group(3), m.group(4)
    if lat and lon:
        # the exact spot - a place name alongside it can make Google pick another
        query, z = f"{lat},{lon}", int(float(zoom or 14))
    else:
        query, z = (place or "").replace("+", " "), 14
    return f"https://maps.google.com/maps?q={quote(query)}&z={z}&output=embed"


_EMBEDS = [
    # (provider, pattern, embed url template - or a function of the
    # match - and the card's height class)
    ("YouTube", re.compile(r"^https://(?:www\.|m\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)"
                           r"([A-Za-z0-9_-]{11})"),
     "https://www.youtube-nocookie.com/embed/{}?autoplay=1", "aspect-video"),
    ("Vimeo", re.compile(r"^https://(?:www\.)?vimeo\.com/(\d+)"),
     "https://player.vimeo.com/video/{}?autoplay=1&dnt=1", "aspect-video"),
    ("Spotify", re.compile(r"^https://open\.spotify\.com/((?:track|album|playlist|episode|show)/[A-Za-z0-9]+)"),
     "https://open.spotify.com/embed/{}", "h-40"),
    ("Mastodon", re.compile(r"^(https://[a-z0-9.-]+\.[a-z]{2,}/@[A-Za-z0-9_]+/\d+)$"),
     "{}/embed", "h-96"),
    # X's own embed page (what its widgets.js builds) - no script needed
    ("X", re.compile(r"^https://(?:www\.|mobile\.)?(?:twitter|x)\.com/[A-Za-z0-9_]{1,15}/status/(\d+)"),
     "https://platform.twitter.com/embed/Tweet.html?id={}&dnt=true", "h-[36rem]"),
    ("Facebook", re.compile(r"^(https://(?:www\.|m\.)?(?:facebook\.com/(?:[A-Za-z0-9.]+/(?:posts|videos|photos)/[^\s]+"
                            r"|permalink\.php\?[^\s]+|watch/?\?v=\d+|reel/\d+)|fb\.watch/[A-Za-z0-9_-]+/?))$"),
     lambda m: _fb_plugin(m.group(1)), "h-[36rem]"),
    ("Instagram", re.compile(r"^https://(?:www\.)?instagram\.com/(?:[A-Za-z0-9_.]+/)?(p|reel)/([A-Za-z0-9_-]+)"),
     lambda m: f"https://www.instagram.com/{m.group(1)}/{m.group(2)}/embed", "h-[40rem]"),
    ("TikTok", re.compile(r"^https://(?:www\.)?tiktok\.com/@[A-Za-z0-9_.]+/video/(\d+)"),
     "https://www.tiktok.com/embed/v2/{}", "h-[46rem]"),
    ("OpenStreetMap", re.compile(r"^https://(?:www\.)?openstreetmap\.org/[^\s#]*#map=(\d{1,2})/(-?[\d.]+)/(-?[\d.]+)"),
     _osm, "h-96"),
    ("Google Maps", re.compile(r"^https://(?:www\.|maps\.)?google\.[a-z.]+/maps(?:/place/([^/@\s]+))?"
                               r"(?:/@(-?[\d.]+),(-?[\d.]+),([\d.]+)z)?"),
     _google_map, "h-96"),
]
_FORM_EMBEDS = [
    # hosted forms - a survey, sign-up or RSVP anywhere in a post, or the
    # whole contact page (formservices.py)
    (name, re.compile(pattern), template, "h-[36rem]") for name, pattern, template in (
        ("Tally", r"^https://tally\.so/r/([A-Za-z0-9]+)", "https://tally.so/embed/{}?transparentBackground=1"),
        ("Typeform", r"^(https://[a-z0-9-]+\.typeform\.com/to/[A-Za-z0-9]+)", "{}"),
        ("Google Forms", r"^https://docs\.google\.com/forms/d/e/([A-Za-z0-9_-]+)/viewform",
         "https://docs.google.com/forms/d/e/{}/viewform?embedded=true"),
        ("Jotform", r"^https://form\.jotform\.com/(\d+)", "https://form.jotform.com/{}"),
        ("Microsoft Forms", r"^https://forms\.office\.com/Pages/ResponsePage\.aspx\?id=([A-Za-z0-9_-]+)",
         "https://forms.office.com/Pages/ResponsePage.aspx?id={}&embed=true"),
        ("Airtable", r"^https://airtable\.com/((?:app[A-Za-z0-9]+/)?shr[A-Za-z0-9]+)", "https://airtable.com/embed/{}"),
    )
]
FORM_PROVIDERS = [e[0] for e in _FORM_EMBEDS]
_EMBEDS = _EMBEDS + _FORM_EMBEDS


def embed_url(url: str):
    """The click-to-load card for a supported embed link, or None."""
    return _embed(url)
_MEDIA = re.compile(r"^(?:https?://[^\s\"<>]+|/uploads/[^\s\"<>/]+)\.(mp4|webm|mov|m4v|mp3|m4a|ogg|oga|wav|flac)$",
                    re.I)
_AUDIO = {"mp3", "m4a", "ogg", "oga", "wav", "flac"}


def _embed(url: str):
    """The html for a URL on its own line, or None to leave it be.

    Video/audio files become the browser's own player. A YouTube, Vimeo,
    Spotify, Mastodon, X, Facebook, Instagram, TikTok or map link becomes
    a placeholder card - nothing is loaded from that site, no cookie
    set, until the reader clicks it (loadEmbed, READING_JS in app.py)."""
    from html import escape, unescape
    url = unescape(url)
    if re.match(r"^/uploads/[^\s\"<>/]+\.pdf$", url, re.I):
        # the browser's own PDF viewer, and the file itself for a browser
        # without one in a page (most phones)
        return (f'<div class="not-prose my-4"><iframe src="{escape(url)}" title="PDF" loading="lazy" '
                f'class="w-full h-[70vh] rounded-box border-[length:var(--border)] border-base-300 max-sm:hidden">'
                f'</iframe><a class="link text-sm inline-flex items-center pointer-coarse:min-h-11" href="{escape(url)}" target="_blank" rel="noopener">'
                f'{escape(i18n.t("Open the PDF"))}</a></div>')
    media = _MEDIA.match(url)
    if media:
        tag = "audio" if media.group(1).lower() in _AUDIO else "video"
        cls = "w-full" if tag == "audio" else "w-full rounded-box"
        return f'<{tag} controls preload="metadata" class="{cls} my-4" src="{escape(url)}"></{tag}>'
    for provider, pattern, template, size in _EMBEDS:
        m = pattern.match(url)
        if m:
            src = template(m) if callable(template) else template.format(m.group(1))
            if provider == "Google Maps" and not (m.group(1) or m.group(2)):
                continue  # a maps link with no place or position in it
            return (f'<div class="embed not-prose card card-border bg-base-100 {size} my-4 overflow-hidden '
                    f'flex flex-col items-center justify-center gap-2 p-4 text-center" data-embed-src="{escape(src)}">'
                    f'<button type="button" {on_attrs("click", "loadEmbed", EL)} class="btn btn-primary btn-sm">{_PLAY}'
                    f'<span class="ml-1">{escape(i18n.t("Load from {service}", service=provider))}</span></button>'
                    f'<span class="text-xs text-base-content/60">'
                    f'{escape(i18n.t("Nothing from {service} loads until you click.", service=provider))} '
                    f'<a class="link" href="{escape(url)}" target="_blank" rel="noopener">'
                    f'{escape(i18n.t("Open it there instead"))}</a></span></div>')
    return None


_PLAY = ('<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="currentColor">'
         '<path d="M8 5.14v13.72a1 1 0 0 0 1.5.86l11.2-6.86a1 1 0 0 0 0-1.72L9.5 4.28A1 1 0 0 0 8 5.14Z"/></svg>')


# Blocks written as a line of their own (Help > Reference > Markdown and extras): Buttons:,
# Pull quote:, Countdown: - read from the html, so a feed or an email
# still gets the links and the words
_BUTTONS = re.compile(r"<p>Buttons:\s*((?:<a\b[^>]*>.*?</a>[\s,·|]*)+)</p>", re.S)
_PULL = re.compile(r"<p>Pull quote:\s*(.+?)</p>", re.S)
_COUNTDOWN = re.compile(r"<p>Countdown:\s*([^<]{4,40}?)\s*</p>")
_DATE_FORMATS = ("%Y-%m-%d", "%d %B %Y", "%B %d, %Y", "%B %d %Y", "%d %b %Y", "%b %d, %Y", "%b %d %Y")


def _date_of(text: str):
    from datetime import datetime
    for f in _DATE_FORMATS:
        try:
            return datetime.strptime(text.strip().rstrip("."), f).date()
        except ValueError:
            continue
    return None


def _buttons(m) -> str:
    # the first the way on; the rest beside it
    links = re.findall(r'<a\b([^>]*)>(.*?)</a>', m.group(1), re.S)
    return ('<div class="not-prose flex flex-wrap gap-2 my-6">' +
            "".join(f'<a{attrs} class="btn{" btn-primary" if i == 0 else ""}">{label}</a>'
                    for i, (attrs, label) in enumerate(links)) + "</div>")


def _countdown(m) -> str:
    """Days to go until a date - a count, not a ticking clock: nothing
    moves on its own (WCAG 2.2.2) or talks over a screen reader. COUNTDOWN_JS
    counts again on the visitor's own day."""
    from html import escape
    day = _date_of(m.group(1))
    if not day:
        return m.group(0)  # not a date it knows: left as written
    left = (day - utcnow().date()).days
    words = (i18n.t("Today") if left == 0 else i18n.t("1 day to go") if left == 1
             else i18n.t("{n} days to go", n=left) if left > 1 else "")
    return (f'<div class="not-prose my-6 flex flex-wrap items-baseline gap-x-3 gap-y-1" data-countdown="{day.isoformat()}" '
            f'data-today="{escape(i18n.t("Today"))}" data-one="{escape(i18n.t("1 day to go"))}" '
            f'data-many="{escape(i18n.t("{n} days to go"))}">'
            f'<span class="text-3xl sm:text-4xl font-bold text-primary [&:empty]:hidden" data-countdown-left>'
            f'{escape(words)}</span>'
            f'<span class="text-base-content/70">{escape(format_date(day.isoformat()))}</span></div>')


# a section's own lines with a block line straight under them, no empty line between
_BLOCK_UNDER_OWN = re.compile(r"<p>(\s*Section:[^<\n]{1,40}?\s*(?:(?:<br\s*/?>|\n)\s*(?:" + sections.LINE_KEYS_RE +
                              r"):[^<\n]{1,40}?\s*)*)(?:<br\s*/?>|\n)\s*(?=(?:Buttons|Pull quote|Countdown):)", re.I)


def _blocks(html: str) -> str:
    html = _BLOCK_UNDER_OWN.sub(lambda m: f"<p>{m.group(1)}</p>\n<p>", html)
    html = _BUTTONS.sub(_buttons, html)
    html = _PULL.sub(lambda m: '<blockquote class="not-prose my-8 border-s-4 border-primary ps-5 sm:ps-6 '
                               'text-2xl sm:text-3xl font-semibold leading-snug text-balance">'
                               f'{m.group(1).strip()}</blockquote>', html)
    html = _COUNTDOWN.sub(_countdown, html)
    # ??? "Title": a fold, in the page's own look
    return re.sub(r"<details(?: open=\"open\")?>", lambda m: m.group(0)[:-1] + (
        ' class="my-4 rounded-box border-[length:var(--border)] border-base-300 px-4 [&>summary]:cursor-pointer '
        '[&>summary]:font-semibold [&>summary]:py-3 [&[open]>summary]:mb-1">'), html)


def _finish(html: str) -> str:
    """Small additions on already-sanitized html: - [ ] task list
    checkboxes, ~~strikethrough~~ (Python-Markdown has neither), the
    line blocks (Buttons:, Pull quote:, Countdown:) and folds, and
    embeds/players for a URL on its own line."""
    from html import escape
    html = _blocks(html)
    html = _TASK.sub(lambda m: '<li class="task-item"><input type="checkbox" disabled'
                               + (f' checked aria-label="{escape(i18n.t("Done"))}"' if m.group(1) != " "
                                  else f' aria-label="{escape(i18n.t("Not done"))}"') + "> ", html)
    html = "".join(part if i % 2 else _STRIKE.sub(r"<del>\1</del>", part)
                   for i, part in enumerate(_CODE_HTML.split(html)))
    # a wide table scrolls sideways on its own instead of pushing past the column
    # each column at least 7rem: on a phone a table squeezed its last
    # column to a word a line, rather than scrolling
    html = html.replace("<table>", '<div class="overflow-x-auto [&_:is(td,th)]:min-w-28"><table>').replace(
        "</table>", "</table></div>")
    return _LONE_URL.sub(lambda m: _embed(m.group(1) or m.group(2)) or m.group(0), html)


_LINK = re.compile(r'<a\b([^>]*)>(.*?)</a>', re.S)
_HREF = re.compile(r'\bhref="([^"]*)"')


def new_tab_links(html: str) -> str:
    """Links in finished post html that go to another site get
    target=_blank, and a hidden note for screen readers. Done on the page
    only - feeds and emails render the same post and keep plain links.
    Runs after nh3, which would remove target."""
    from html import escape, unescape
    from urllib.parse import urlsplit

    def bare(host):
        return (host or "").lower().removeprefix("www.")
    own = bare(urlsplit(config.BASE_URL).hostname)

    def tag(m):
        attrs = m.group(1)
        href = _HREF.search(attrs)
        if not href or "target=" in attrs:
            return m.group(0)
        url = unescape(href.group(1)).strip()
        if not url.lower().startswith(("http://", "https://", "//")):
            return m.group(0)
        try:
            host = bare(urlsplit(url).hostname)
        except ValueError:
            return m.group(0)
        if not host or host == own:
            return m.group(0)
        note = escape(i18n.t("(opens in a new tab)"))
        return f'<a{attrs} target="_blank">{m.group(2)}<span class="sr-only"> {note}</span></a>'
    return _LINK.sub(tag, html)


def render_markdown(body: str) -> str:
    html = markdown.markdown(body, extensions=["pymdownx.superfences", "pymdownx.highlight", "tables", "toc"] + EXTRAS,
                             extension_configs=EXTRAS_CONFIG)
    return nh3.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS)


# our uploads, and hotlinked Unsplash photos (stock.py), whose credit is saved too
_IMG_SRC = re.compile(r'<img [^>]*src="(/uploads/[^"]+|https://images\.unsplash\.com/[^"]+)"[^>]*>')
_LONE_IMG = re.compile(r'<p>(<img [^>]*src="(?:/uploads/|https://images\.unsplash\.com/)[^"]+"[^>]*>)</p>')


# how wide a picture in a post's words shows: its column, 48rem at most (a
# wide or full section gives it its own width - pages._wider_sizes)
BODY_SIZES = "(min-width: 768px) 48rem, 100vw"


def _enrich_images(html: str) -> str:
    """Body images from the media library get what the library knows
    about them: saved alt text when the markdown left it blank, and an
    image on its own line becomes a figure with its caption and photo
    credit underneath - the same line a cover image gets. Runs after
    nh3, on html it just produced, so nothing here is user input."""
    from soloblog import images
    from html import escape

    from html import unescape

    def fill_alt(m):
        tag = m.group(0)
        if 'alt=""' in tag or "alt=" not in tag:
            alt = images.meta_for_url(unescape(m.group(1)))["alt_text"]
            if alt:
                tag = tag.replace('alt=""', "").replace("<img ", f'<img alt="{escape(alt)}" ', 1)
        # smaller copies for narrow screens - a post's column is 48rem at most
        options = images.srcset(m.group(1))
        if options and "srcset=" not in tag:
            tag = tag.replace("<img ", f'<img srcset="{escape(options)}" sizes="{BODY_SIZES}" ', 1)
        return tag

    def to_figure(m):
        src = unescape(_IMG_SRC.match(m.group(1)).group(1))
        caption = images.figcaption_html(images.meta_for_url(src))
        if not caption:
            return m.group(0)
        return (f'<figure>{m.group(1)}<figcaption class="{images.CAPTION_CLS}">'
                f'{caption}</figcaption></figure>')

    return _LONE_IMG.sub(to_figure, _IMG_SRC.sub(fill_alt, html))


# rendered posts, newest use last: (body hash, cache generation) ->
# (html, toc). A post's html depends on its text, a few settings (math,
# the gallery style) and the images' saved alt text, captions and
# credits - all covered by cache.generation(), which settings and image
# changes bump. Markdown, nh3 and the image lookups then run once per
# edit rather than once per view.
_POST_CACHE = OrderedDict()
_POST_CACHE_SIZE = 200
_post_cache_lock = threading.Lock()


def render_post(body: str):
    from soloblog import cache
    key = (hashlib.sha1(body.encode("utf-8"), usedforsecurity=False).hexdigest(), cache.generation(), i18n.lang())
    with _post_cache_lock:
        hit = _POST_CACHE.get(key)
        if hit is not None:
            _POST_CACHE.move_to_end(key)
            return hit
    result = _render_post(body)
    with _post_cache_lock:
        _POST_CACHE[key] = result
        while len(_POST_CACHE) > _POST_CACHE_SIZE:
            _POST_CACHE.popitem(last=False)
    return result


_NO_HREF = re.compile(r"<a(?![^>]*\bhref=)((?:\s[^>]*)?)>")
_NO_SRC = re.compile(r"<img(?![^>]*\bsrc=)((?:\s[^>]*)?)>")


def _samples(html: str) -> str:
    """A sample's link and image with nothing after https:// yet - nh3
    drops a URL that's only that. The link still goes somewhere, so it's
    drawn as the button it will be; the image counts as one of ours
    that's missing (images.without_missing), as a template's unreplaced
    picture does."""
    html = _NO_HREF.sub(r'<a href="#"\1>', html)
    return _NO_SRC.sub(r'<img src="/uploads/"\1>', html)


def _render_post(body: str):
    """Same rendering as render_markdown, but also hands back a table
    of contents. Needs markdown's object API instead of the markdown()
    shortcut - the shortcut throws its Markdown instance away, and the
    toc extension's output only lives on that instance (.toc_tokens)."""
    from soloblog import images, settings
    body, saved = _protect(body, math=settings.get("markdown_math") == "1")
    body = _list_after_paragraph(body)
    # U+FE0E asks for the text form of ↩ - some systems draw an emoji otherwise
    md = markdown.Markdown(extensions=POST_EXTENSIONS,
                           extension_configs={"footnotes": {"BACKLINK_TEXT": "\u21a9\ufe0e"}, **EXTRAS_CONFIG})
    html = nh3.clean(md.convert(body), tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS)
    html = images.with_other_versions(_restore(_finish(_enrich_images(_samples(html))), saved))
    # only bother with a toc when there's enough structure to justify one.
    # toc_tokens nest - each ### is among its ##'s children
    def walk(tokens):
        for t in tokens:
            yield t
            yield from walk(t["children"])
    headings = [(t["level"], t["id"], t["name"]) for t in walk(md.toc_tokens) if t["level"] in (2, 3)]
    return html, toc_markup(headings) if len(headings) >= 3 else None


def toc_markup(headings) -> str | None:
    """The table of contents' list, from (level, id, text) for each ##
    and ###: a daisyUI menu where a ## folds its ###s away
    (TableOfContents, ui, decides whether they can)."""
    items, i = [], 0
    while i < len(headings):
        level, hid, name = headings[i]
        j = i + 1
        while level == 2 and j < len(headings) and headings[j][0] == 3:
            j += 1
        link = f'<a href="#{hid}">{name}</a>'
        subs = "".join(f'<li><a href="#{k}">{n}</a></li>' for _, k, n in headings[i + 1:j])
        items.append(f'<li><details open><summary>{link}</summary><ul>{subs}</ul></details></li>' if subs
                     else f'<li>{link}</li>')
        i = j
    # whitespace-normal - a menu item doesn't wrap, and a long heading ran off the panel
    return (f'<ul class="menu menu-sm w-full p-0 [&_a]:whitespace-normal [&_summary]:whitespace-normal">'
            f'{"".join(items)}</ul>' if items else None)


_EMOJI_LIST = None


def emoji_list() -> list:
    """[[shortcode, emoji]] for the editor's : suggestions, most familiar
    names first - GitHub's list, the same one posts render with."""
    global _EMOJI_LIST
    if _EMOJI_LIST is None:
        index = pymdownx.emoji.gemoji(None, None)
        def char(info):
            return "".join(chr(int(h, 16)) for h in (info.get("unicode_alt") or info["unicode"]).split("-"))
        names = [(code.strip(":"), char(info)) for code, info in index["emoji"].items() if info.get("unicode")]
        names += [(alias.strip(":"), char(index["emoji"][code])) for alias, code in index["aliases"].items()
                  if index["emoji"].get(code, {}).get("unicode")]
        _EMOJI_LIST = sorted(names, key=lambda n: (len(n[0]), n[0]))
    return _EMOJI_LIST


def render_comment(body: str) -> str:
    """Comments are plain text with linebreaks: anything typed as HTML
    shows as it was typed - no pictures from elsewhere (which would tell
    their sender who read the page), no headings, no links."""
    from html import escape
    return "<p>" + escape(body or "").replace("\n", "<br>") + "</p>"


def reading_time(html_body: str) -> str:
    plain = re.sub(r"<[^>]+>", " ", html_body)
    words = len(plain.split())
    return i18n.t("{n} min read", n=max(1, math.ceil(words / 200)))


def web_url(url) -> str:
    """An address another site sent us (a webmention's author, a fediverse
    profile), fit for a link or an image: http(s) only - never
    javascript: or data: - else ""."""
    url = (url or "").strip() if isinstance(url, str) else ""
    return url if url.lower().startswith(("https://", "http://")) else ""


# a section's own lines - "Section: Pricing", and "Width: Wide" or "Count: 6"
# with it (sections.OPTIONS) - a paragraph of nothing else
_SECTION_LINES = re.compile(r"<p>\s*((?:(?:" + sections.LINE_KEYS_RE + r"):[^<\n]{1,40}?\s*(?:<br\s*/?>)?\s*)+)</p>\s*",
                            re.I)
# a Features item's "Icon: palette", first in its paragraph
_ICON_LINE = re.compile(r"(<p>)\s*Icon:\s*([\w-]{1,30})\s*(?:<br\s*/?>|\n|(?=</p>))", re.I)
_ICON_LINE_TEXT = re.compile(r"^Icon:[ \t]*([\w-]{1,30})[ \t]*(?:\n|$)", re.M | re.I)


def without_section_lines(html: str) -> str:
    """A section's "Section: Pricing" line (sections.section_kind) is for the
    page to read, not a person: left out of excerpts, feeds and emails.
    Only a kind the page knows - any other line is someone's words."""
    from soloblog.editor_icons import ICONS
    html = _ICON_LINE.sub(lambda m: m.group(1) if m.group(2).lower() in ICONS else m.group(0), html)
    html = _SECTION_LINES.sub(lambda m: "" if sections.only_own_lines(m.group(1)) else m.group(0), html)

    def keep_the_rest(m):
        own, rest = sections.split_own(m.group(1))
        return m.group(0) if not own else f"<p>{'<br>'.join(rest)}</p>\n" if rest else ""
    # lines of its items written straight under it (Project facts) are words, and stay
    return sections.SECTION_PARAGRAPH.sub(keep_the_rest, html)


_SECTION_LINE_TEXT = re.compile(r"(?:^(?:" + sections.LINE_KEYS_RE + r"):[ \t]*[^\n]{1,40}?[ \t]*(?:\n|$))+", re.M | re.I)


def without_section_lines_text(text: str) -> str:
    """The same, from the written text itself (a newsletter's whole post)."""
    from soloblog.editor_icons import ICONS
    text = _ICON_LINE_TEXT.sub(lambda m: "" if m.group(1).lower() in ICONS else m.group(0), text)
    return _SECTION_LINE_TEXT.sub(lambda m: "" if sections.only_own_lines(m.group(0)) else m.group(0), text)


def excerpt(html_body: str, length: int = 160) -> str:
    """Plain-text excerpt for meta descriptions / og:description, and a
    post list's teaser - from the paragraphs, so it doesn't read as a run
    of headings and list markers ("Ingredients - 2 eggs Method...")."""
    html_body = without_section_lines(html_body)
    paras = " ".join(re.findall(r"<p\b[^>]*>(.*?)</p>", html_body, re.S))
    plain = re.sub(r"<[^>]+>", " ", paras if paras.strip() else html_body)
    plain = re.sub(r"\s+", " ", plain).strip()
    return (plain[:length] + "…") if len(plain) > length else plain


def _abs_date(dt) -> str:
    """dt.strftime('%b %-d, %Y') would be simpler, but %-d is a
    glibc/macOS extension - it crashes on Windows' C runtime with
    'Invalid format string'. This works everywhere."""
    return i18n.date_format().format(month=i18n.months()[dt.month - 1], day=dt.day, year=dt.year)


def local_datetime(iso_date: str):
    """The day a post was written on, in the site's timezone - what
    format_date shows."""
    dt = datetime.fromisoformat(iso_date[:19])
    if len(iso_date) > 10:
        from soloblog import tz
        dt = tz.to_local(dt)
    return dt


def short_date_format(fmt: str, month: bool = True) -> str:
    """A language's date pattern without the year ("Sep 15", "15. Sept.",
    "9月15日"), or with the month gone too - what's left when a heading
    above already says them. The year and month take their joining words
    with them: ", ", "de", "年", "년", "г.". """
    fmt = re.sub(r"\s*(,|de)?\s*\{year\}(\s*(г\.|р\.)|年|년)?\s*", " ", fmt).strip()
    if not month:
        fmt = re.sub(r"\s*(de\s*)?\{month\}\s*", " ", fmt).strip()
    return fmt


def short_date(dt, month: bool = True) -> str:
    return short_date_format(i18n.date_format(), month).format(month=i18n.months()[dt.month - 1], day=dt.day)


def format_when(iso: str) -> str:
    """When something was last used, in the admin - "today at 11:31",
    "yesterday at 09:02" or "Oct 14, 2026 at 11:31", in the site's
    timezone."""
    from soloblog import tz
    try:
        local = tz.to_local(datetime.fromisoformat(iso[:19]))
    except (TypeError, ValueError):
        return iso or ""
    days = (tz.to_local(utcnow()).date() - local.date()).days
    day = "today" if days == 0 else "yesterday" if days == 1 else format_date(iso)
    return f"{day} at {local.strftime('%H:%M')}"


def format_date(iso_date: str, relative: bool = False) -> str:
    """One function, used everywhere a date shows up, so a post card,
    a post page, and a comment all agree on what a date looks like."""
    try:
        dt = datetime.fromisoformat(iso_date[:19])
    except ValueError:
        return iso_date

    if not relative:
        # a bare date (no time) is already a calendar day - shifting it
        # to another timezone would move it to the day before or after
        if len(iso_date) > 10:
            from soloblog import tz
            dt = tz.to_local(dt)
        return _abs_date(dt)

    delta = utcnow() - dt
    seconds = delta.total_seconds()
    if seconds < 60:
        return i18n.t("just now")
    if seconds < 3600:
        return i18n.plural(int(seconds // 60), "{n} minute ago", "{n} minutes ago")
    if seconds < 86400:
        return i18n.plural(int(seconds // 3600), "{n} hour ago", "{n} hours ago")
    if seconds < 2592000:
        return i18n.plural(int(seconds // 86400), "{n} day ago", "{n} days ago")
    return _abs_date(dt)  # falls back to absolute past a month
