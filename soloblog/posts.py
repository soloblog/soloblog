import logging
import os
import re
import secrets
import yaml
from dataclasses import asdict, dataclass, fields, replace
from datetime import datetime
from soloblog.tz import utcnow

from soloblog import config
from soloblog import settings
from soloblog import tz
from soloblog.db import get_db

log = logging.getLogger(__name__)

VALID_PIN_LOCATIONS = ("header", "footer", "top")
# first path parts the app's own routes use (/tags, /contact...) - filled
# in by app.py once every route exists. A page with one of these slugs
# can't have it as its address, so it stays at /post/<slug>.
RESERVED_PATHS = set()


def is_page(row) -> bool:
    """Pinned to the header or footer - About, Privacy. Posts pinned to
    the top of the homepage are still posts."""
    keys = row.keys()
    return "pinned" in keys and bool(row["pinned"]) and row["pin_location"] in ("header", "footer")


# Settings > Name and homepage > Homepage's value for the wiki's front page - never
# a slug, which can't start with @
WIKI_HOME = "@wiki"

# Settings > Name and homepage > Homepage: what a page shows as the homepage,
# besides itself - none of these unless switched on
HOME_EXTRAS = {"title": "Title, date and cover", "reactions": "Reactions", "share": "Share buttons",
               "related": "Related posts", "author": "About the author", "newsletter": "Newsletter sign-up",
               "comments": "Comments"}


def url_for(row) -> str:
    """A post's address: / for the one that's the homepage, /about for a
    page, /post/<slug> for the rest."""
    if row["slug"] and row["slug"] == settings.get("home_page"):
        return "/"
    if is_page(row) and row["slug"] not in RESERVED_PATHS:
        return f"/{row['slug']}"
    return f"/post/{row['slug']}"


def parse_redirects(text: str) -> list:
    """Settings > Site > Redirects: one "from to" pair a line. from is a
    path on this site - ending in * for everything under it; to is a
    path here or another site's address. Lines that aren't are left out."""
    pairs = []
    for line in (text or "").splitlines():
        parts = line.split()
        if len(parts) != 2:
            continue
        src, dest = parts
        if not is_local_link(src) or not (is_local_link(dest) or re.fullmatch(r"https?://\S+", dest)):
            continue
        pairs.append((src, dest))
    return pairs


def custom_redirect(path: str, text: str):
    """Where one of the admin's own redirects sends path, or None. Only
    asked for an address nothing else answers, so a real page always wins."""
    here = path.rstrip("/").lower() or "/"
    for src, dest in parse_redirects(text):
        if src.endswith("*"):
            if here.startswith(src[:-1].rstrip("/").lower()):
                return dest
        elif here == (src.rstrip("/").lower() or "/"):
            return dest
    return None


def old_address(path: str):
    """Where an address from before an import went: the last part of
    /2020/01/my-post/, /my-post.html or /blog/my-post/amp is tried as a
    post's URL. None if nothing live matches."""
    import re
    if path.startswith(("/admin", "/static", "/uploads")):
        return None
    parts = [p for p in path.lower().split("/") if p]
    if parts and parts[-1] in ("amp", "feed", "comments") and len(parts) > 1:
        parts.pop()
    if not parts:
        return None
    slug = re.sub(r"\.(html?|php|aspx?)$", "", parts[-1])
    row = get_post(slug)
    if not row:
        moved = find_redirect(slug)
        row = get_post(moved) if moved else None
    if not row or not is_live(row):
        return None
    target = url_for(row)
    return target if target != path else None


def is_protected(row) -> bool:
    """Needs a password to open. Everything that shows a post somewhere
    else - feeds, the fediverse, the newsletter, search - shows only its
    title and summary."""
    return "password" in row.keys() and bool(row["password"])


def teaser(row, length: int = 160) -> str:
    """What a post list shows under the title: the summary, or the start
    of the post when it has none - never a protected post's text, nor a
    members post's past its free preview (lists are public)."""
    if row["summary"] or is_protected(row):
        return row["summary"]
    from soloblog.render import excerpt, render_post
    body = public_part(load_post_body(row["slug"]), row["visibility"] if "visibility" in row.keys() else "")
    return excerpt(render_post(body)[0], length) if body.strip() else ""


def url_for_slug(slug: str) -> str:
    row = get_post(slug)
    return url_for(row) if row else f"/post/{slug}"


def _path(slug: str) -> str:
    os.makedirs(config.posts_dir(), exist_ok=True)
    return os.path.join(config.posts_dir(), f"{slug}.md")


def slugify(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.strip().lower()).strip("-")
    return s or "post"


def unique_slug(title: str, existing_slug: str = None) -> str:
    base = slugify(title)
    if existing_slug and get_post(existing_slug):
        return existing_slug
    slug, n = base, 2
    while get_post(slug):
        slug = f"{base}-{n}"
        n += 1
    return slug


def _parse_file(filepath):
    """Reads a post file straight off disk - front matter + body. This
    is the one place that understands the file format, used both by
    save/load and by the disk->db reindex."""
    with open(filepath, encoding="utf-8") as f:
        content = f.read()
    meta, body = {}, content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            meta = yaml.safe_load(parts[1]) or {}
            body = parts[2]
    return meta, body.strip()


@dataclass
class PostFields:
    """A post's words and every Post setting - all a save can change, each
    with what a new post starts as. One object carries them from whoever
    is saving to the database and the file: a new setting is added here,
    and nothing on the way down lists forty names where two could swap.
    pin_location "" is a post that isn't pinned."""
    title: str = ""
    body: str = ""
    tags: str = ""
    summary: str = ""
    cover_image: str = ""
    scheduled_at: str = ""
    series_name: str = ""
    series_order: int = 0
    parent_slug: str = ""
    pin_location: str = ""
    published: bool = False
    comments_enabled: bool = True
    link_url: str = ""
    password: str = ""
    noindex: bool = False
    canonical_url: str = ""
    toc_style: str = ""
    heading_fold: str = ""
    unlisted: bool = False
    seo_title: str = ""
    share_image: str = ""
    cover_width: str = ""
    hide_list_cover: bool = False
    extras: str = ""
    visibility: str = "public"
    sound: str = ""
    sides: str = ""
    section_space: str = ""
    title_style: str = ""
    page_width: str = ""
    slides: bool = False
    in_wiki: bool = False
    remind_update: bool = False
    section_motion: str = ""

    @property
    def pinned(self) -> bool:
        return bool(self.pin_location)

    @classmethod
    def of(cls, row, body: str) -> "PostFields":
        """A saved post's fields, from its row and its file's words."""
        keys = row.keys()
        f = cls(**{x.name: row[x.name] for x in fields(cls) if x.name in keys})
        return replace(f, body=body, pin_location=row["pin_location"] if row["pinned"] else "")

    def cleaned(self) -> "PostFields":
        """Each value as it's stored: a choice that isn't one becomes the
        site's own, an address that isn't one is dropped - never an error,
        whoever sent it."""
        return replace(
            self,
            title=str(self.title or "").strip(),
            # a browser sends the editor's text with Windows line endings - kept,
            # they'd sit in the file and trip anything that reads a line to its end
            body=(self.body or "").replace("\r\n", "\n").replace("\r", "\n"),
            tags=self.tags or "", summary=self.summary or "", cover_image=self.cover_image or "",
            scheduled_at=self.scheduled_at or "", series_name=self.series_name or "",
            series_order=int(self.series_order or 0), parent_slug=self.parent_slug or "",
            pin_location=self.pin_location if self.pin_location in ("", *VALID_PIN_LOCATIONS) else "header",
            published=bool(self.published), comments_enabled=bool(self.comments_enabled),
            link_url=clean_link(self.link_url), password=str(self.password or "").strip()[:100],
            noindex=bool(self.noindex), canonical_url=clean_link(self.canonical_url),
            toc_style=clean_choice(self.toc_style, "TOC_STYLES"),
            heading_fold=clean_choice(self.heading_fold, "FOLD_STYLES"), unlisted=bool(self.unlisted),
            seo_title=_clean_seo_title(self.seo_title), share_image=clean_link(self.share_image),
            cover_width=clean_choice(self.cover_width, "COVER_STYLES"),
            hide_list_cover=bool(self.hide_list_cover), extras=_pages().clean_extras(self.extras),
            visibility=clean_visibility(self.visibility), sound=clean_sound(self.sound),
            sides=clean_sides(self.sides), section_space=clean_choice(self.section_space, "SPACINGS"),
            title_style=clean_title_style(self.title_style), page_width=clean_page_width(self.page_width),
            slides=clean_flag(self.slides), in_wiki=clean_flag(self.in_wiki),
            remind_update=clean_flag(self.remind_update),
            section_motion=clean_choice(self.section_motion, "SECTION_MOTIONS"))


def _write_file(slug, f: PostFields, *, author, pin_order, preview_token, created_at):
    front = {
        "title": f.title, "date": tz.local_date(created_at), "author": author,
        "tags": f.tags, "summary": f.summary, "cover_image": f.cover_image,
        "published": bool(f.published), "pinned": f.pinned,
    }
    if f.scheduled_at:
        # stored as UTC, marked with a "Z" so the file says so itself
        front["scheduled_at"] = tz.normalize_stored(f.scheduled_at) + "Z"
    if f.series_name:
        front["series_name"] = f.series_name
        front["series_order"] = f.series_order
    if f.parent_slug:
        front["parent_slug"] = f.parent_slug
    if f.pinned and f.pin_location != "header":
        front["pin_location"] = f.pin_location
    if f.pinned and pin_order:
        front["pin_order"] = pin_order
    if not f.comments_enabled:
        front["comments_enabled"] = False
    if preview_token:
        front["preview_token"] = preview_token
    # a line only for what isn't the site's own: (the file's word, its value)
    for line, value in (("link", f.link_url), ("password", f.password), ("noindex", bool(f.noindex)),
                        ("canonical", f.canonical_url), ("toc", f.toc_style), ("fold", f.heading_fold),
                        ("cover_width", f.cover_width), ("spacing", f.section_space),
                        ("motion", f.section_motion), ("title_style", f.title_style),
                        ("page_width", f.page_width), ("slides", bool(f.slides)), ("wiki", bool(f.in_wiki)),
                        ("remind_update", bool(f.remind_update)), ("extras", f.extras), ("sound", f.sound),
                        ("sides", (f.sides or "").replace(",", ", "))):
        if value:
            front[line] = value
    if f.visibility in ("members", "paid"):
        front["visibility"] = f.visibility
    if f.hide_list_cover:
        front["list_cover"] = False
    if f.unlisted:
        front["unlisted"] = True
    if f.seo_title:
        front["seo_title"] = f.seo_title
    if f.share_image:
        front["share_image"] = f.share_image
    # former slugs aren't an editor field - they only come from a rename,
    # so a normal save keeps whatever the file already had
    old = _redirects_in_file(slug)
    if old:
        front["redirect_from"] = old
    text = "---\n" + yaml.safe_dump(front, sort_keys=False).strip() + "\n---\n\n" + f.body.strip() + "\n"
    with open(_path(slug), "w", encoding="utf-8", newline="\n") as out:
        out.write(text)


VISIBILITIES = ("public", "members", "paid")
# where a members post's free preview ends - a line of its own (the
# editor's Members only from here); an HTML comment, so it's invisible
# wherever the post is shown whole
# \r too: a browser sends the editor's text with Windows line endings
MEMBERS_CUT = re.compile(r"^[ \t]*<!--\s*members(?:[ -]only)?(?:\s+from\s+here)?\s*-->[ \t\r]*$", re.M | re.I)


def clean_visibility(value) -> str:
    value = str(value or "").strip().lower()
    return value if value in VISIBILITIES else "public"


def split_members(body_md: str):
    """(the free preview, the rest) of a post at its Members only from here
    line - ("", body) when it has none."""
    m = MEMBERS_CUT.search(body_md or "")
    if not m:
        return "", body_md or ""
    return body_md[:m.start()].rstrip(), body_md[m.end():].lstrip()


def public_part(body_md: str, visibility) -> str:
    """What of a post anyone may read: all of a public one; of a members or
    paid one, only its free preview (nothing, without one). Everything
    that sends a post's text anywhere - feeds, the fediverse, search,
    shares, emails to those who can't read it - goes through this."""
    if clean_visibility(visibility) == "public" or settings.get("members_enabled") != "1":
        return body_md or ""
    return split_members(body_md)[0]


def is_gated(row) -> bool:
    """A members or paid post, with members on - its text past the preview
    is only for those who can read it."""
    value = row["visibility"] if "visibility" in row.keys() else ""
    return clean_visibility(value) != "public" and settings.get("members_enabled") == "1"


def access_label(row) -> str:
    """" · Members" or " · Paid members" for the admin's lists - "" for a
    post anyone can read."""
    if not is_gated(row):
        return ""
    return " · Paid members" if clean_visibility(row["visibility"]) == "paid" else " · Members"


def members_note(row) -> str:
    """The line in place of the rest of a members post, wherever it goes
    outside the site - a feed, the fediverse, an email."""
    from soloblog import i18n
    from html import escape
    url = config.BASE_URL + url_for(row)
    say = i18n.t("This post is for paid members.") if clean_visibility(row["visibility"]) == "paid" \
        else i18n.t("This post is for members.")
    return f'<p><em>{escape(say)}</em> <a href="{escape(url)}">{escape(i18n.t("Read it on the site"))}</a></p>'


def refresh_search():
    """Search's copy of every post again - after members are turned on or
    off, which changes what of a members post anyone may find."""
    db = get_db()
    for row in db.execute("SELECT * FROM posts").fetchall():
        _sync_fts(row["slug"], row["title"], "" if is_protected(row) else
                  public_part(load_post_body(row["slug"]), row["visibility"]), row["tags"])
    db.commit()


def _redirects_in_file(slug) -> list:
    path = _path(slug)
    if not os.path.exists(path):
        return []
    return _as_slug_list(_parse_file(path)[0].get("redirect_from"))


def _as_slug_list(value) -> list:
    if not value:
        return []
    if isinstance(value, str):
        value = value.split(",")
    return [str(v).strip() for v in value if str(v).strip()]


def _index_redirects(slug, meta):
    get_db().execute("UPDATE posts SET redirect_from=?, link_url=?, password=?, noindex=?, "
                     "canonical_url=?, toc_style=?, heading_fold=?, unlisted=?, seo_title=?, share_image=?, "
                     "cover_width=?, hide_list_cover=?, extras=?, visibility=?, sound=?, sides=?, section_space=?, "
                     "title_style=?, page_width=?, slides=?, in_wiki=?, remind_update=?, section_motion=? WHERE slug=?",
                     (",".join(_as_slug_list(meta.get("redirect_from"))), clean_link(meta.get("link")), str(meta.get("password") or "")[:100],
                      int(bool(meta.get("noindex"))), clean_link(meta.get("canonical")),
                      clean_choice(meta.get("toc"), "TOC_STYLES"), clean_choice(meta.get("fold"), "FOLD_STYLES"),
                      int(bool(meta.get("unlisted"))), _clean_seo_title(meta.get("seo_title")),
                      clean_link(meta.get("share_image")), clean_choice(meta.get("cover_width"), "COVER_STYLES"),
                      int(meta.get("list_cover") is False), _pages().clean_extras(meta.get("extras")),
                      clean_visibility(meta.get("visibility")), clean_sound(meta.get("sound")),
                      clean_sides(meta.get("sides")), clean_choice(meta.get("spacing"), "SPACINGS"),
                      clean_title_style(meta.get("title_style")), clean_page_width(meta.get("page_width")),
                      clean_flag(meta.get("slides")), clean_flag(meta.get("wiki")),
                      clean_flag(meta.get("remind_update")), clean_choice(meta.get("motion"), "SECTION_MOTIONS"), slug))


def _clean_seo_title(value) -> str:
    return " ".join(str(value or "").split())[:120]


def _pages():
    from soloblog import pages
    return pages


def clean_choice(value, choices: str) -> str:
    """"" (the site's own setting) or one of pages.TOC_STYLES/FOLD_STYLES."""
    from soloblog import pages
    value = str(value or "").strip().lower()
    return value if value in getattr(pages, choices) else ""


SIDE_NAMES = ("tags", "archive", "author")  # a post's own side panels: ui.SIDE_KEYS without "side_"


def clean_sides(value) -> str:
    """A post's own side panel places, as stored: "tags=left,author=off" -
    only known panels and places, in a fixed order; anything else is
    dropped, never an error (a file edited by hand, an old backup)."""
    from soloblog import ui
    own = {}
    for part in str(value or "").replace(";", ",").split(","):
        name, _, place = part.partition("=")
        name, place = name.strip().lower(), place.strip().lower()
        if name in SIDE_NAMES and place in ui.SIDE_PLACES:
            own[name] = place
    return ",".join(f"{n}={own[n]}" for n in SIDE_NAMES if n in own)


def clean_sound(value) -> str:
    """A background sound: one of the media library's own audio files -
    never another site's, which would load from it for every visitor."""
    value = str(value or "").strip()
    return value if re.fullmatch(r"/uploads/[A-Za-z0-9._-]+\.(mp3|m4a|ogg|oga|wav|flac)", value) else ""


TITLE_STYLES = {"": "Left", "centre": "Centred", "hidden": "Hidden"}
PAGE_WIDTHS = {"": "Column", "wide": "Wide"}


def clean_title_style(value) -> str:
    value = str(value or "").strip().lower()
    return value if value in TITLE_STYLES else ""


def clean_page_width(value) -> str:
    value = str(value or "").strip().lower()
    return value if value in PAGE_WIDTHS else ""


def clean_flag(value) -> int:
    """1 for a real yes - true, 1, or the words true/yes/on - else 0. Not
    bool(): a hand-edited file saying "no" or "false" is a string, and
    any string would count as on."""
    if isinstance(value, str):
        return int(value.strip().lower() in ("true", "yes", "on", "1"))
    return int(value is True or value == 1)


MAX_LINK = 2000


def clean_link(value) -> str:
    """A Link post's address: another site's, or a path on this one
    (/contact, /tag/travel) - how those get into the menu."""
    value = str(value or "").strip()[:MAX_LINK]
    if is_local_link(value):
        return value
    return value if value.startswith(("https://", "http://")) else ""


def is_local_link(url) -> bool:
    return bool(url) and url.startswith("/") and not url.startswith("//") and not re.search(r"[\s\\\"'<>]", url)


def rebuild_wiki_links():
    for fn in os.listdir(config.posts_dir()) if os.path.exists(config.posts_dir()) else []:
        if fn.endswith(".md"):
            _index_wiki_links(fn[:-3], _parse_file(os.path.join(config.posts_dir(), fn))[1])


def _index_wiki_links(slug, body):
    """Which posts this one's [[links]] point at (post_links)."""
    from soloblog import pages
    db = get_db()
    db.execute("DELETE FROM post_links WHERE from_slug=?", (slug,))
    for target in pages.wiki_targets(body):
        if target != slug:
            db.execute("INSERT OR IGNORE INTO post_links (from_slug, to_slug) VALUES (?, ?)", (slug, target))


_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def is_valid_slug(slug: str) -> bool:
    return bool(_SLUG_RE.match(slug or ""))


def find_redirect(old_slug: str):
    """The slug a post moved to from old_slug, or None."""
    if not is_valid_slug(old_slug):
        return None
    row = get_db().execute(
        "SELECT slug FROM posts WHERE ',' || redirect_from || ',' LIKE ?", (f"%,{old_slug},%",)
    ).fetchone()
    return row["slug"] if row else None


def _rewrite_front_matter(slug, **changes):
    """Changes some front matter keys of an existing post file in place,
    leaving everything else - body included - exactly as it was."""
    path = _path(slug)
    meta, body = _parse_file(path)
    meta.update(changes)
    meta = {k: v for k, v in meta.items() if v not in (None, [], "")}
    text = "---\n" + yaml.safe_dump(meta, sort_keys=False).strip() + "\n---\n\n" + body.strip() + "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def rename_post(old_slug: str, new_slug: str) -> str:
    """Moves a post to a new URL. The old slug (and any it had before)
    is kept in the post's redirect_from, so every link that ever pointed
    at it still lands on the post. Comments, likes, views and sub-pages
    follow it. Returns "" on success, or why it couldn't."""
    if not is_valid_slug(new_slug):
        return "Use lowercase letters, numbers and dashes"
    if new_slug == old_slug:
        return ""
    if get_post(new_slug) or os.path.exists(_path(new_slug)):
        return "That URL is already used by another post"
    if not get_post(old_slug):
        return "Post not found"

    meta, _ = _parse_file(_path(old_slug))
    history = [s for s in _as_slug_list(meta.get("redirect_from")) + [old_slug] if s != new_slug]
    _rewrite_front_matter(old_slug, redirect_from=history)
    os.rename(_path(old_slug), _path(new_slug))

    db = get_db()
    db.execute("UPDATE posts SET slug=?, redirect_from=? WHERE slug=?", (new_slug, ",".join(history), old_slug))
    db.execute("UPDATE posts_fts SET slug=? WHERE slug=?", (new_slug, old_slug))
    db.execute("UPDATE comments SET post_slug=? WHERE post_slug=?", (new_slug, old_slug))
    db.execute("UPDATE post_views_daily SET slug=? WHERE slug=?", (new_slug, old_slug))
    db.execute("UPDATE post_revisions SET slug=? WHERE slug=?", (new_slug, old_slug))
    db.execute("UPDATE post_reactions SET post_slug=? WHERE post_slug=?", (new_slug, old_slug))
    db.execute("UPDATE post_links SET from_slug=? WHERE from_slug=?", (new_slug, old_slug))
    db.execute("UPDATE post_links SET to_slug=? WHERE to_slug=?", (new_slug, old_slug))
    db.execute("UPDATE post_translations SET slug=? WHERE slug=?", (new_slug, old_slug))
    children = [r["slug"] for r in db.execute("SELECT slug FROM posts WHERE parent_slug=?", (old_slug,))]
    db.execute("UPDATE posts SET parent_slug=? WHERE parent_slug=?", (new_slug, old_slug))
    db.commit()
    for child in children:
        _rewrite_front_matter(child, parent_slug=new_slug)
    return ""


def _sync_fts(slug, title, body, tags):
    db = get_db()
    db.execute("DELETE FROM posts_fts WHERE slug=?", (slug,))
    db.execute("INSERT INTO posts_fts (slug, title, body, tags) VALUES (?, ?, ?, ?)",
               (slug, title, body, tags))


_UPSERT_SQL = """
    INSERT INTO posts (slug, title, summary, tags, published, pinned, cover_image,
                        scheduled_at, series_name, series_order, parent_slug, pin_location, pin_order,
                        comments_enabled, preview_token, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(slug) DO UPDATE SET
        title=excluded.title, summary=excluded.summary, tags=excluded.tags,
        published=excluded.published, pinned=excluded.pinned, cover_image=excluded.cover_image,
        scheduled_at=excluded.scheduled_at, series_name=excluded.series_name,
        series_order=excluded.series_order, parent_slug=excluded.parent_slug,
        pin_location=excluded.pin_location, pin_order=excluded.pin_order,
        comments_enabled=excluded.comments_enabled,
        preview_token=excluded.preview_token, updated_at=excluded.updated_at
"""


def save_post(slug, title, author, body_md, tags, summary, published, pinned, cover_image="", *,
              pin_location="header", preview_token=None, pin_order=None, created_at=None, **settings):
    """A save for a caller with the values in hand - the demo, an import,
    a copy. settings are PostFields' own names; one it hasn't is an error.
    created_at - only for a new post that has its own history (an
    import); an existing post always keeps its original date."""
    _save(slug, author,
          PostFields(title=title, body=body_md, tags=tags, summary=summary, published=published,
                     cover_image=cover_image, pin_location=(pin_location or "header") if pinned else "",
                     **settings),
          preview_token=preview_token, pin_order=pin_order, created_at=created_at)


def _save(slug, author, f: PostFields, *, preview_token=None, pin_order=None, created_at=None):
    f = f.cleaned()
    # the row keeps a place even for a post that isn't pinned
    pin_location = f.pin_location or "header"
    db = get_db()
    now = utcnow().isoformat()
    existing = get_post(slug)
    created_at = existing["created_at"] if existing else (created_at or now)
    if preview_token is None:
        preview_token = existing["preview_token"] if existing else ""
    if pin_order is None:
        # editing an existing pin keeps its place in the order; a post
        # that's only just becoming pinned starts at the back of
        # whichever (location, parent) group it lands in, not at 0 -
        # 0 is reserved for "explicitly moved to the front"
        if existing and existing["pinned"] and existing["pin_location"] == pin_location \
                and existing["parent_slug"] == f.parent_slug:
            pin_order = existing["pin_order"]
        elif f.pinned:
            pin_order = _next_pin_order(pin_location, f.parent_slug)
        else:
            pin_order = 0

    if existing and os.path.exists(_path(slug)):
        _keep_revision(slug, f.body, f.title)
    db.execute(_UPSERT_SQL, (
        slug, f.title, f.summary, f.tags, int(f.published), int(f.pinned), f.cover_image,
        f.scheduled_at, f.series_name, f.series_order, f.parent_slug, pin_location, pin_order,
        int(f.comments_enabled), preview_token, created_at, now
    ))
    db.execute("UPDATE posts SET link_url=?, password=?, noindex=?, canonical_url=?, toc_style=?, "
               "heading_fold=?, unlisted=?, seo_title=?, share_image=?, cover_width=?, hide_list_cover=?, "
               "extras=?, visibility=?, sound=?, sides=?, section_space=?, title_style=?, page_width=?, "
               "slides=?, in_wiki=?, remind_update=?, section_motion=? WHERE slug=?",
               (f.link_url, f.password, int(f.noindex), f.canonical_url, f.toc_style, f.heading_fold,
                int(f.unlisted), f.seo_title, f.share_image, f.cover_width, int(f.hide_list_cover), f.extras,
                f.visibility, f.sound, f.sides, f.section_space, f.title_style, f.page_width, f.slides,
                f.in_wiki, f.remind_update, f.section_motion, slug))
    # search finds only what anyone may read
    _sync_fts(slug, f.title, "" if f.password else public_part(f.body, f.visibility), f.tags)
    _index_wiki_links(slug, f.body)
    db.commit()
    _write_file(slug, f, author=author, pin_order=pin_order, preview_token=preview_token, created_at=created_at)


# ---- one way in: every save - the editor, the API, Micropub, an AI
# assistant - goes through write(), so a post behaves the same however
# it was written

# what write() takes, and what a new post starts as
WRITABLE = asdict(PostFields())


def write(slug: str = None, author: str = "", **changes) -> str:
    """Creates a post (slug None) or changes one, and returns its slug.
    Only what's given changes - everything else keeps what it had - so a
    caller that knows about three fields can't wipe the rest. pin_location
    "" means not pinned. Then what follows any save: translations, and
    telling followers and linked pages about a live post."""
    old = get_post(slug) if slug else None
    if slug and not old:
        raise KeyError(slug)
    values = dict(WRITABLE)
    if old:
        keys = old.keys()
        values.update({k: old[k] for k in WRITABLE if k in keys})
        values["body"] = load_post_body(slug)
        values["pin_location"] = old["pin_location"] if old["pinned"] else ""
    values.update({k: v for k, v in changes.items() if k in WRITABLE and v is not None})
    if not str(values["title"]).strip():
        raise ValueError("A post needs a title")
    new_slug = unique_slug(values["title"], existing_slug=slug)
    _save(new_slug, author, PostFields(**values))
    after_save(new_slug)
    return new_slug


def after_save(slug: str):
    """What follows a save that changed a live post: its translations made
    or remade in the background, and the fediverse and linked pages told
    (publishing.py)."""
    row = get_post(slug)
    if row and is_live(row):
        from soloblog import translate
        from soloblog import publishing
        translate.queue_post(slug)
        publishing.kick()


MAX_REVISIONS = 50


def _keep_revision(slug, new_body, new_title):
    """Before a post's file is overwritten, the version on disk becomes a
    revision - but only when the words actually change, so toggling a
    setting doesn't fill the history with identical copies."""
    meta, old_body = _parse_file(_path(slug))
    old_title = str(meta.get("title", ""))
    if old_body.strip() == (new_body or "").strip() and old_title == new_title:
        return
    db = get_db()
    db.execute("INSERT INTO post_revisions (slug, title, body, saved_at) VALUES (?, ?, ?, ?)",
               (slug, old_title, old_body, utcnow().isoformat()))
    db.execute("DELETE FROM post_revisions WHERE slug=? AND id NOT IN "
               "(SELECT id FROM post_revisions WHERE slug=? ORDER BY id DESC LIMIT ?)",
               (slug, slug, MAX_REVISIONS))


# words as the editor counts them (updateStatus): runs of letters and
# numbers, joined by an apostrophe or a dash - markdown's marks don't count
_WORD = re.compile(r"[^\W_]+(?:['’-][^\W_]+)*")


def count_words(text: str) -> int:
    return len(_WORD.findall(text or ""))


def words_at_day_start(slug: str) -> int:
    """How many words the post had at today's midnight (site timezone),
    for "+180 today" in the editor. A revision is the text as it was until
    it was replaced, so the first one replaced today is how the day began;
    with none, the saved post is. A post made today began at nothing."""
    from soloblog import tz
    post = get_post(slug)
    if not post:
        return 0
    start = tz.day_start_utc()
    if (post["created_at"] or "") >= start:
        return 0
    row = get_db().execute("SELECT body FROM post_revisions WHERE slug=? AND saved_at>=? ORDER BY id LIMIT 1",
                           (slug, start)).fetchone()
    return count_words(row["body"] if row else _parse_file(_path(slug))[1])


def list_revisions(slug: str):
    """Newest first, each with written_at: when that version was written.
    saved_at is when it was replaced - the save that kept it - so a
    version was written when the one before it was replaced, and the
    oldest when the post was made. Once the oldest have been dropped
    (MAX_REVISIONS) the last one's time isn't known: None. words and
    added (words more than the version before it; None for the oldest)."""
    rows = [dict(r) for r in get_db().execute(
        "SELECT id, title, body, saved_at FROM post_revisions WHERE slug=? ORDER BY id DESC",
        (slug,)).fetchall()]
    post = get_post(slug)
    for newer, older in zip(rows, rows[1:]):
        newer["written_at"] = older["saved_at"]
    if rows:
        rows[-1]["written_at"] = post["created_at"] if post and len(rows) < MAX_REVISIONS else None
    for r in rows:
        r["words"] = count_words(r.pop("body"))
    for newer, older in zip(rows, rows[1:]):
        newer["added"] = newer["words"] - older["words"]
    if rows:
        rows[-1]["added"] = None
    return rows


def current_version(slug: str):
    """The post as it's saved now, as History's top row: written when the
    newest revision was replaced (or when the post was made), its words,
    and how many more than that revision."""
    post = get_post(slug)
    if not post:
        return None
    body = load_post_body(slug)
    newest = get_db().execute("SELECT body, saved_at FROM post_revisions WHERE slug=? ORDER BY id DESC LIMIT 1",
                              (slug,)).fetchone()
    words = count_words(body)
    return {"title": post["title"], "body": body, "words": words,
            "written_at": newest["saved_at"] if newest else post["created_at"],
            "added": words - count_words(newest["body"]) if newest else None}


def revision_before(rev):
    """The version a revision replaced - what its changes are measured
    against - or None for the oldest kept."""
    return get_db().execute("SELECT * FROM post_revisions WHERE slug=? AND id<? ORDER BY id DESC LIMIT 1",
                            (rev["slug"], rev["id"])).fetchone()


def get_revision(revision_id: int):
    return get_db().execute("SELECT * FROM post_revisions WHERE id=?", (revision_id,)).fetchone()


def get_post(slug: str):
    return get_db().execute("SELECT * FROM posts WHERE slug=?", (slug,)).fetchone()


def is_live(row) -> bool:
    """Published isn't quite the same as visible - a scheduled post is
    published=1 but shouldn't show until its time comes."""
    if not row["published"]:
        return False
    return not (row["scheduled_at"] and row["scheduled_at"] > utcnow().isoformat())


def post_status(row) -> str:
    if row["pinned"]:
        return "Pinned"
    if not row["published"]:
        return "Draft"
    if row["scheduled_at"] and row["scheduled_at"] > utcnow().isoformat():
        return "Scheduled"
    return "Unlisted" if row["unlisted"] else "Published"


def list_between(start: str, end: str):
    """Published posts (scheduled ones too) going live between two UTC
    dates - Posts > Calendar."""
    return get_db().execute(
        "SELECT * FROM posts WHERE published=1 AND COALESCE(NULLIF(scheduled_at, ''), created_at) >= ? "
        "AND COALESCE(NULLIF(scheduled_at, ''), created_at) < ? ORDER BY created_at", (start, end)).fetchall()


def list_posts(include_drafts=False):
    if include_drafts:
        q = "SELECT * FROM posts ORDER BY pinned DESC, created_at DESC"
        return get_db().execute(q).fetchall()
    now = utcnow().isoformat()
    q = ("SELECT * FROM posts WHERE published=1 AND unlisted=0 AND (scheduled_at='' OR scheduled_at<=?) "
         "ORDER BY pinned DESC, created_at DESC")
    return get_db().execute(q, (now,)).fetchall()


def _status_where(status: str):
    """Shared by list_by_status and count_by_status so the two can
    never quietly drift apart and start disagreeing on what counts as
    a page of results vs. the total behind it."""
    now = utcnow().isoformat()
    if status == "published":
        # pinned pages too: they're published, and the Pinned tab only orders them
        return "published=1 AND (scheduled_at='' OR scheduled_at<=?)", [now]
    if status == "draft":
        return "published=0", []
    if status == "scheduled":
        return "published=1 AND scheduled_at!='' AND scheduled_at>?", [now]
    if status == "pinned":
        return "pinned=1", []
    # posts and series: a kind (KINDS), still taken here for the API's ?status=
    return KINDS.get(status, "1=1"), []


KINDS = {"posts": "NOT (pinned=1 AND pin_location IN ('header', 'footer'))",
         "pages": "pinned=1 AND pin_location IN ('header', 'footer')",
         "series": "series_name!=''"}


def _filter(where: str, params: list, tag: str, q: str, access: str = "", kind: str = ""):
    """The admin list's filters and search box: a word in the title,
    summary or tags, or anywhere in the post's text. access: who can
    read it - public, members or paid. kind: posts, pages (is_page) or
    series (those in one)."""
    if kind in KINDS:
        where += f" AND {KINDS[kind]}"
    if access in VISIBILITIES:
        where += " AND visibility=?"
        params = params + [access]
    if tag:
        where += " AND tags LIKE ?"
        params.append(f"%{tag}%")
    q = q.strip()
    if q:
        like = f"%{q}%"
        where += (" AND (title LIKE ? OR summary LIKE ? OR tags LIKE ? OR slug IN "
                  "(SELECT slug FROM posts_fts WHERE posts_fts MATCH ?))")
        params += [like, like, like, _words_starting(q)]
    return where, params


def _words_starting(q: str) -> str:
    """An fts5 query for text with words starting as each of q's do, so
    a word half typed finds what the whole word does. Each quoted, so a
    stray " or * is just text to fts5, not syntax."""
    return " ".join('"' + w.replace('"', '""') + '"*' for w in q.split())


def list_by_status(status: str, sort: str = "newest", tag: str = "", page: int = 1, per_page: int = 10,
                   q: str = "", access: str = "", kind: str = ""):
    """Backs the tabbed/sorted/filterable/searchable/paginated admin posts
    page. status is one of: all, published, draft, scheduled, pinned (and
    posts or series, which are kinds); kind: one of KINDS."""
    where, params = _filter(*_status_where(status), tag, q, access, kind)

    order = {
        "newest": "created_at DESC",
        "oldest": "created_at ASC",
        "title": "title ASC",
        "views": "views DESC",
        "edited": "updated_at DESC",
    }.get(sort, "created_at DESC")
    if q.strip():
        # a search: those with it in their title first, then the rest
        order = f"title LIKE ? DESC, {order}"
        params.append(f"%{q.strip()}%")

    params += [per_page, (max(1, page) - 1) * per_page]
    q = f"SELECT * FROM posts WHERE {where} ORDER BY {order} LIMIT ? OFFSET ?"  # noqa: S608 - fixed lists, values bound
    return get_db().execute(q, params).fetchall()


def count_by_status(status: str, tag: str = "", q: str = "", access: str = "", kind: str = "") -> int:
    where, params = _filter(*_status_where(status), tag, q, access, kind)
    return get_db().execute(f"SELECT COUNT(*) AS n FROM posts WHERE {where}", params).fetchone()["n"]  # noqa: S608 - fixed lists, values bound


# the blog roll leaves out wiki notes - they live in the wiki (/wiki), as
# pages live in the menu; tags, search, the archive and feeds keep them
# the post chosen as the homepage (Settings > Name and homepage) is the
# homepage, never also a post in the lists and feeds - it needed Unlisted
# to keep out, which kept it out of search too
NOT_HOME = "slug NOT IN (SELECT value FROM settings WHERE key='home_page')"
_ROLL = ("published=1 AND pinned=0 AND unlisted=0 AND in_wiki=0 AND (scheduled_at='' OR scheduled_at<=?) "
         f"AND {NOT_HOME}")


def count_roll() -> int:
    now = utcnow().isoformat()
    q = f"SELECT COUNT(*) AS n FROM posts WHERE {_ROLL}"  # noqa: S608 - fixed lists, values bound
    return get_db().execute(q, (now,)).fetchone()["n"]


def list_roll_all(limit=None, columns="*"):
    """Same as list_roll but every match, no pagination - for internal
    uses like RSS where paginating first and filtering after would
    silently drop older matches. limit - the newest that many (a feed);
    columns - just the ones needed, for a count over thousands of posts."""
    now = utcnow().isoformat()
    q = (f"SELECT {columns} FROM posts WHERE published=1 AND pinned=0 AND unlisted=0 AND {NOT_HOME} "  # noqa: S608 - fixed lists, values bound
         "AND (scheduled_at='' OR scheduled_at<=?) ORDER BY created_at DESC")
    params = (now,)
    if limit:
        q, params = q + " LIMIT ?", (now, limit)
    return get_db().execute(q, params).fetchall()


def list_all_published():
    """Every published post, pinned ones too - for tag pages. The blog
    roll leaves pinned posts out (they're shown above it); here a tag
    used only on a pinned post would have found nothing."""
    now = utcnow().isoformat()
    q = (f"SELECT * FROM posts WHERE published=1 AND unlisted=0 AND {NOT_HOME} "  # noqa: S608 - fixed text
         "AND (scheduled_at='' OR scheduled_at<=?) ORDER BY created_at DESC")
    return get_db().execute(q, (now,)).fetchall()


def bulk_state(row) -> str:
    """draft, scheduled or published - what Admin > Posts' bulk actions
    can do to it (Publish fits the first two, Move to drafts the last two)."""
    if not row["published"]:
        return "draft"
    if row["scheduled_at"] and row["scheduled_at"] > utcnow().isoformat():
        return "scheduled"
    return "published"


def update_post(slug: str, published=None, add_tag: str = "") -> bool:
    """A quick change from Admin > Posts (its bulk actions), without the
    editor: publish or unpublish, or add a tag. The file is rewritten
    like any save."""
    row = get_post(slug)
    if not row:
        return False
    tags = split_tags(row["tags"])
    add_tag = add_tag.strip().replace(",", " ")
    if add_tag and add_tag not in tags:
        tags.append(add_tag)
    db = get_db()
    # Publish means live now: a date still to come would keep it waiting
    scheduled = row["scheduled_at"]
    if published and scheduled and scheduled > utcnow().isoformat():
        scheduled = ""
    db.execute("UPDATE posts SET published=?, scheduled_at=?, tags=?, updated_at=? WHERE slug=?",
               (row["published"] if published is None else int(bool(published)), scheduled, ", ".join(tags),
                utcnow().isoformat(), slug))
    db.commit()
    row = get_post(slug)
    _rewrite_file_from_row(row)
    _sync_fts(slug, row["title"], "" if is_protected(row) else public_part(load_post_body(slug), row["visibility"]), row["tags"])
    db.commit()
    return True


def duplicate_post(slug: str):
    """A draft copy of a post - the text, tags, summary, cover and settings -
    to start a similar one from. Returns its slug."""
    row = get_post(slug)
    if not row:
        return None
    s = settings.get_all()
    title = f"{row['title']} (copy)"
    new = unique_slug(title)
    save_post(new, title, s["author_name"] or s["site_title"], load_post_body(slug), row["tags"], row["summary"],
              False, False, row["cover_image"], link_url=row["link_url"],
              toc_style=row["toc_style"], heading_fold=row["heading_fold"], cover_width=row["cover_width"],
              hide_list_cover=bool(row["hide_list_cover"]), extras=row["extras"], visibility=row["visibility"],
              sound=row["sound"], sides=row["sides"], section_space=row["section_space"],
              title_style=row["title_style"], page_width=row["page_width"], slides=row["slides"],
              in_wiki=row["in_wiki"], remind_update=row["remind_update"], section_motion=row["section_motion"])
    return new


def tag_counts_all() -> list:
    """[(tag, posts)] across every post, drafts too, by name - Admin >
    Posts > Tags. Tags that differ only in case count as one."""
    counts, spellings = {}, {}
    for row in get_db().execute("SELECT tags FROM posts").fetchall():
        for t in split_tags(row["tags"]):
            counts[t.lower()] = counts.get(t.lower(), 0) + 1
            spellings.setdefault(t.lower(), t)
    return sorted(((spellings[k], n) for k, n in counts.items()), key=lambda x: x[0].lower())


def rename_tag(old: str, new: str) -> int:
    """Every post tagged old (in any case) gets new instead - which merges
    the two when new is already a tag. An empty new takes it off. The
    number of posts changed."""
    old_key, new = old.strip().lower(), new.strip().replace(",", " ")
    changed = 0
    for row in get_db().execute("SELECT slug, tags FROM posts").fetchall():
        tags = split_tags(row["tags"])
        if old_key not in (t.lower() for t in tags):
            continue
        out = []
        for t in tags:
            t = new if t.lower() == old_key else t
            if t and t.lower() not in (x.lower() for x in out):
                out.append(t)
        _set_tags(row["slug"], out)
        changed += 1
    return changed


def _set_tags(slug: str, tags: list):
    db = get_db()
    db.execute("UPDATE posts SET tags=? WHERE slug=?", (", ".join(tags), slug))
    db.commit()
    row = get_post(slug)
    _rewrite_file_from_row(row)
    _sync_fts(slug, row["title"], "" if is_protected(row) else public_part(load_post_body(slug), row["visibility"]), row["tags"])
    db.commit()


def split_tags(tags_csv: str) -> list:
    return [t.strip() for t in (tags_csv or "").split(",") if t.strip()]


def list_tagged(tag: str):
    """Every live post carrying tag (any case), newest first - pinned
    pages included, like list_all_published."""
    wanted = tag.strip().lower()
    return [p for p in list_all_published() if wanted in (t.lower() for t in split_tags(p["tags"]))]


def tag_counts() -> list:
    """[(tag, number of live posts)] for the /tags index, by name. Tags
    that differ only in case count as one, under their most used form."""
    counts, spellings = {}, {}
    now = utcnow().isoformat()
    rows = get_db().execute("SELECT tags FROM posts WHERE published=1 AND unlisted=0 AND tags != '' "
                            "AND (scheduled_at='' OR scheduled_at<=?)", (now,)).fetchall()
    for p in rows:
        for t in split_tags(p["tags"]):
            key = t.lower()
            counts[key] = counts.get(key, 0) + 1
            spellings.setdefault(key, {}).setdefault(t, 0)
            spellings[key][t] += 1
    return sorted(((max(spellings[k], key=spellings[k].get), n) for k, n in counts.items()),
                  key=lambda x: x[0].lower())


def list_roll(page: int = 1, per_page: int = 10):
    """Published, non-pinned, not still scheduled for the future, not a
    wiki note - the normal reverse-chron blog roll. Paginated."""
    now = utcnow().isoformat()
    offset = max(0, (page - 1) * per_page)
    q = f"SELECT * FROM posts WHERE {_ROLL} ORDER BY created_at DESC LIMIT ? OFFSET ?"  # noqa: S608 - fixed lists, values bound
    return get_db().execute(q, (now, per_page, offset)).fetchall()


def list_pinned():
    """Published, pinned - these act as static pages (About, etc)."""
    q = "SELECT * FROM posts WHERE published=1 AND pinned=1 ORDER BY title"
    return get_db().execute(q).fetchall()


def list_pinned_by_location(location: str, drafts: bool = False):
    """drafts - the admin's Pinned tab, where a pinned draft is listed
    in its place; the menus never show one."""
    # title is just the tiebreaker for posts that share a pin_order
    # (new pins default to the same "back of the line" value within
    # their group) - manual reordering is what actually moves things
    q = ("SELECT * FROM posts WHERE pinned=1 AND pin_location=?" + ("" if drafts else " AND published=1") +  # noqa: S608 - fixed lists, values bound
         " ORDER BY pin_order, title")
    return get_db().execute(q, (location,)).fetchall()


def _next_pin_order(pin_location: str, parent_slug: str) -> int:
    """One past the current max pin_order among this page's actual
    siblings (same location, same parent) - a newly-pinned page joins
    the back of its own group instead of the back of the whole
    location's flat pin_order range, which would put it who-knows-
    where once parents and children are mixed together."""
    row = get_db().execute(
        "SELECT MAX(pin_order) AS m FROM posts WHERE pinned=1 AND pin_location=? AND parent_slug=?",
        (pin_location, parent_slug)
    ).fetchone()
    last = row["m"] or 0
    if pin_location in MENUS and not parent_slug:
        # the menu's top level includes the built-in pages put in it
        s = settings.get_all()
        last = max([last] + [n for k in site_rows(s, pin_location, True) if (n := site_order(s, pin_location, k)) < _SITE_LAST])
    return last + 1


# The header's menu and the footer's pages are each a list of the owner's pages
# with Soloblog's own pages among them - Home, Blog and the built-in pages
# (SITE_PAGES), the same list the link picker offers. Where one sits, what it's
# called and whether it's there are settings, per menu: nav_wiki_on,
# nav_wiki_order (in a page's pin_order numbers), nav_wiki_label for the header,
# foot_wiki_... for the footer. Home and Blog are in the header unless left
# out (nav_home_hidden); everything else is there once added.
# key -> (address, the words it's called by default, what it is)
SITE_PAGES = {
    "home": ("/", "Home", "Your homepage"),
    "blog": ("/blog", "Blog", "Every post, newest first"),
    "archive": ("/archive", "Archive", "Every post, by month"),
    "tags": ("/tags", "Tags", "Every tag, and its posts"),
    "search": ("/search", "Search", "Search the site"),
    "wiki": ("/wiki", "Wiki", "Every Wiki page, A to Z"),
    "links": ("/links", "Links", "Your link-in-bio page"),
    "contact": ("/contact", "Contact", "The contact form"),
    "newsletter": ("/newsletter", "Newsletter", "The newsletter sign-up"),
    "rss": ("/rss", "RSS feed", "New posts, for feed readers"),
}
SITE_ROWS = tuple(SITE_PAGES)
# the menus' own names, and their settings' prefixes
MENUS = {"header": "nav", "footer": "foot"}
_SITE_FIRST = {"home": -2, "blog": -1}  # the header's, unset: before every page, Home first
_SITE_LAST = 999999999                    # unset on anything else: after every page


def site_addable(where: str) -> tuple:
    """What can be added to a menu: the header already has Home and Blog."""
    return SITE_ROWS[2:] if where == "header" else SITE_ROWS


def site_key(where: str, key: str, what: str) -> str:
    """A site row's setting: what is "on", "order" or "label"."""
    return f"{MENUS[where]}_{key}_{what}"


def site_note(s, key: str) -> str:
    """Why a built-in page isn't there right now, or empty."""
    if key == "blog" and not s.get("home_page"):
        return "Your posts are the homepage"
    if key == "wiki" and not any(is_live(r) for r in get_db().execute(
            "SELECT published, scheduled_at FROM posts WHERE in_wiki=1")):
        return "No wiki notes yet"
    if key == "links" and s.get("links_enabled") != "1":
        return "Link in bio is off"
    if key == "contact" and s.get("contact_enabled") != "1":
        return "The contact form is off"
    if key == "newsletter":
        from soloblog import newsletter
        if not newsletter.mode(s):
            return "The newsletter is off"
    return ""


def menu_note(s, key: str) -> str:
    """The same, for a menu: the wiki as the homepage is Home."""
    if key == "wiki" and s.get("home_page") == WIKI_HOME:
        return "The wiki is your homepage"
    return site_note(s, key)


def site_rows(s, where: str = "header", unavailable=False) -> list:
    """The site's own rows in a menu now: in the header Home, and Blog while
    a page of the owner's is the homepage, then what was added. One that
    doesn't apply (no wiki notes, Link in bio off) is left out - unless
    unavailable, for the Pinned list, which still shows it."""
    rows = (["home", "blog"] if s.get("home_page") else ["home"]) if where == "header" else []
    return rows + [k for k in site_addable(where) if s.get(site_key(where, k, "on")) == "1"
                   and (unavailable or not menu_note(s, k))]


def site_order(s, where: str, key: str) -> int:
    raw = str(s.get(site_key(where, key, "order")) or "").strip()
    return int(raw) if re.fullmatch(r"-?\d{1,9}", raw) else _SITE_FIRST.get(key, _SITE_LAST) if where == "header" else _SITE_LAST


# a page nested under one of the site's own pages: its parent_slug is this
# and the page's key (site:home, site:blog) - a slug never has a colon
SITE_PARENT = "site:"


class SiteItem(str):
    """A menu's site row - its key, as a plain string - with the pages
    nested under it (children: [page], in their order)."""
    children = ()


def site_parent(slug: str):
    """The site page's key a parent_slug names, or None for a page's slug."""
    return slug[len(SITE_PARENT):] if (slug or "").startswith(SITE_PARENT) else None


def menu_items(s, tree, where: str = "header", unavailable=False) -> list:
    """A menu's top-level items in order: a site row's key ("home", "wiki"...,
    a SiteItem, with the pages nested under it) or a (page, sub-pages) pair.
    The site rows go first before the pages are sorted, so a tie keeps them
    ahead of a page. A page under a site page that isn't in the menu now
    (Blog while the posts are the homepage) is a top-level page meanwhile -
    never left out."""
    rows = site_rows(s, where, unavailable)
    under, pages = {}, []
    for p, c in tree:
        key = site_parent(p["parent_slug"])
        if key in rows:
            under.setdefault(key, []).append(p)
        else:
            pages.append((p, c))
    sites = []
    for k in rows:
        item = SiteItem(k)
        item.children = sorted(under.get(k, []), key=lambda p: p["pin_order"] or 0)
        sites.append((site_order(s, where, k), item))
    items = sites + [(p["pin_order"] or 0, (p, c)) for p, c in pages]
    return [item for _, item in sorted(items, key=lambda x: x[0])]


def _menu_tree(where: str):
    return list_pinned_tree(drafts=True) if where == "header" else list_pinned_tree_footer(drafts=True)


def add_site_page(where: str, key: str):
    """Puts a page at the end of a menu."""
    s = settings.get_all()
    if where not in MENUS or key not in site_addable(where) or s.get(site_key(where, key, "on")) == "1":
        return
    last = [site_order(s, where, x) if isinstance(x, str) else x[0]["pin_order"] or 0
            for x in menu_items(s, _menu_tree(where), where, True)]
    settings.set_many({site_key(where, key, "on"): "1",
                       site_key(where, key, "order"): str(max([n for n in last if n < _SITE_LAST], default=0) + 1)})


def remove_site_page(where: str, key: str):
    """Takes a page out of a menu, with the words it was given there."""
    if where in MENUS and key in site_addable(where):
        settings.set_many({site_key(where, key, w): "" for w in ("on", "order", "label")})


def move_menu_item(key: str, direction: str, where: str = "header"):
    """Moves a top-level page (by slug), or a site row ("@home", "@wiki"...), one place
    up or down among all of them. The two swap their numbers; when those
    are equal, or would leave a site row's unset one behind a page,
    everything is numbered 1, 2, 3... so the move shows. Only pages whose
    number changed are written."""
    if where not in MENUS:
        return
    s = settings.get_all()
    items = menu_items(s, _menu_tree(where), where, True)
    pages = {i[0]["slug"]: i[0]["pin_order"] or 0 for i in items if not isinstance(i, str)}
    keys = ["@" + i if isinstance(i, str) else i[0]["slug"] for i in items]  # "@": never a slug, as a page can be named home
    if key not in keys or direction not in ("up", "down"):
        return
    i = keys.index(key)
    j = i - 1 if direction == "up" else i + 1
    if j < 0 or j >= len(keys):
        return
    order = {k: pages[k] if k in pages else site_order(s, where, k[1:]) for k in keys}
    new = dict(order)
    new[keys[i]], new[keys[j]] = order[keys[j]], order[keys[i]]
    if order[keys[i]] == order[keys[j]] or min(new.values()) < 0 or max(new.values()) >= _SITE_LAST:
        keys[i], keys[j] = keys[j], keys[i]
        new = {k: n for n, k in enumerate(keys, 1)}
    settings.set_many({site_key(where, k[1:], "order"): str(n) for k, n in new.items() if k not in pages})
    changed = [k for k in pages if new[k] != order[k]]
    db = get_db()
    for k in changed:
        db.execute("UPDATE posts SET pin_order=? WHERE slug=?", (new[k], k))
    db.commit()
    for k in changed:
        _rewrite_file_from_row(get_post(k))


def move_pin(slug: str, direction: str):
    """Swaps this pinned page's pin_order with whichever sibling (same
    pin_location + parent_slug) sits immediately before/after it -
    reordering is always scoped to one group, never the whole location,
    since that's the only grouping that's ever visually meaningful
    (a dropdown's own item order, or one footer group's order). The
    top level of the header and of the footer is one group with the site's own rows (move_menu_item)."""
    row = get_post(slug)
    if not row or not row["pinned"]:
        return
    if row["pin_location"] in MENUS and not row["parent_slug"]:
        return move_menu_item(slug, direction, row["pin_location"])
    siblings = get_db().execute(
        "SELECT slug, pin_order FROM posts WHERE pinned=1 AND pin_location=? AND parent_slug=? "
        "ORDER BY pin_order, title",
        (row["pin_location"], row["parent_slug"])
    ).fetchall()
    idx = next((i for i, s in enumerate(siblings) if s["slug"] == slug), None)
    if idx is None:
        return
    swap_idx = idx - 1 if direction == "up" else idx + 1
    if swap_idx < 0 or swap_idx >= len(siblings):
        return
    a, b = siblings[idx], siblings[swap_idx]
    db = get_db()
    db.execute("UPDATE posts SET pin_order=? WHERE slug=?", (b["pin_order"], a["slug"]))
    db.execute("UPDATE posts SET pin_order=? WHERE slug=?", (a["pin_order"], b["slug"]))
    db.commit()
    # pin_order is real content (it controls what a visitor sees), not
    # usage data like likes/views - so unlike those, it has to reach
    # the file too, or a reindex from disk would forget the reorder
    _rewrite_file_from_row(get_post(a["slug"]))
    _rewrite_file_from_row(get_post(b["slug"]))


# where a pinned page can go under another: the header's menu, and the
# footer, where a page and those under it are a column
NESTING = ("header", "footer")


def set_parent(slug: str, parent_slug: str) -> bool:
    """Reparents a header-pinned page from the Pinned tab's list view
    directly - a narrower version of what save_post() does when the
    editor's own Parent page field changes, for when that's the only
    thing actually changing. Same one-level-deep nesting rule the
    editor form already enforces client-side, checked here again
    server-side since this is its own entry point, not routed through
    the form. Returns False (a no-op) for any of: an unpinned or non-
    header page, a nonexistent slug, self-parenting, a parent that
    isn't itself a top-level header pin, or a page that already has
    its own children (it would need those moved first - same
    "move children first" rule the editor's own dropdown shows)."""
    row = get_post(slug)
    # the footer's pages nest too, as its columns (ui.SiteFooter)
    if not row or not row["pinned"] or row["pin_location"] not in NESTING:
        return False
    if parent_slug == slug:
        return False
    db = get_db()
    if (key := site_parent(parent_slug)) is not None:
        # under one of the site's own pages that's in this menu
        if key not in site_rows(settings.get_all(), row["pin_location"], True):
            return False
    elif parent_slug:
        parent = get_post(parent_slug)
        if not parent or parent["pin_location"] != row["pin_location"] or parent["parent_slug"]:
            return False
    if parent_slug:
        has_children = db.execute(
            "SELECT 1 FROM posts WHERE parent_slug=? LIMIT 1", (slug,)
        ).fetchone()
        if has_children:
            return False
    if row["parent_slug"] == parent_slug:
        return True
    new_order = _next_pin_order(row["pin_location"], parent_slug)
    db.execute("UPDATE posts SET parent_slug=?, pin_order=? WHERE slug=?", (parent_slug, new_order, slug))
    db.commit()
    _rewrite_file_from_row(get_post(slug))
    return True


def _rewrite_file_from_row(row):
    """Re-derives a post's front matter from its current DB row and
    rewrites the file - used after a DB-only change (currently just
    move_pin's pin_order swap) that needs to reach the file without
    going through the full save_post() flow, since that flow expects
    body text and an author string as fresh inputs, not a re-save of
    what's already there."""
    s = settings.get_all()
    _write_file(row["slug"], PostFields.of(row, load_post_body(row["slug"])),
                author=s["author_name"] or s["site_title"], pin_order=row["pin_order"],
                preview_token=row["preview_token"], created_at=row["created_at"])


def top_tags(limit, keep=""):
    """The limit most used tags (drafts too), by name - for a tag filter
    or the editor's suggestions, which get unwieldy with hundreds. keep
    stays in however rarely it's used (the filter's current choice)."""
    counts = tag_counts_all()
    top = {t for t, _ in sorted(counts, key=lambda x: -x[1])[:limit]}
    return [t for t, _ in counts if t in top or (keep and t.lower() == keep.lower())]


# what a page picker (ui.PageField) offers: "home" - what can be the
# homepage (a page, or an unlisted post); "page" - the pages in the menu or footer
PICK_KINDS = {"home": "published=1 AND (pinned=1 OR unlisted=1)",
               "page": "pinned=1 AND pin_location IN ('header', 'footer')"}


def pick_list(q="", limit=30, kind="", exclude=""):
    """Posts and pages, drafts too, newest first, whose title has q in
    it - the link picker's list, a page at a time however many there
    are; with kind, just those (PICK_KINDS), by title. Returns (rows,
    how many match in all)."""
    like = "%" + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
    where, order = "title LIKE ? ESCAPE '\\'", "created_at DESC"
    if kind in PICK_KINDS:
        where, order = f"{where} AND {PICK_KINDS[kind]} AND slug != ?", "title COLLATE NOCASE"
    params = [like] + ([exclude] if kind in PICK_KINDS else [])
    db = get_db()
    total = db.execute(f"SELECT COUNT(*) FROM posts WHERE {where}", params).fetchone()[0]  # noqa: S608 - fixed lists, values bound
    rows = db.execute(f"SELECT * FROM posts WHERE {where} ORDER BY {order} LIMIT ?", params + [limit]).fetchall()  # noqa: S608 - fixed lists, values bound
    return rows, total


def list_all_tags():
    """Every distinct tag currently in use across all posts, for the
    editor's tag autocomplete - there's no separate tags table, tags
    just live as a comma-separated string per post."""
    rows = get_db().execute("SELECT tags FROM posts WHERE tags != ''").fetchall()
    tags = set()
    for r in rows:
        for t in r["tags"].split(","):
            t = t.strip()
            if t:
                tags.add(t)
    return sorted(tags, key=str.lower)


def _tree(pinned_rows):
    """Shared tree-building logic for whichever subset of pinned pages
    (by location) is being rendered - About > Contact / About > FAQ."""
    by_slug = {p["slug"]: p for p in pinned_rows}
    children = {}
    top_level = []
    for p in pinned_rows:
        parent = p["parent_slug"]
        if parent and parent in by_slug:
            children.setdefault(parent, []).append(p)
        else:
            top_level.append(p)
    return [(p, children.get(p["slug"], [])) for p in top_level]


def list_pinned_tree(drafts: bool = False):
    """Header-pinned pages as (top-level page, [its sub-pages]) pairs.
    A sub-page whose parent isn't itself pinned-in-header just gets
    treated as top-level - never silently dropped."""
    return _tree(list_pinned_by_location("header", drafts))


def list_pinned_tree_footer(drafts: bool = False):
    return _tree(list_pinned_by_location("footer", drafts))


def list_pinned_tree_top(drafts: bool = False):
    return _tree(list_pinned_by_location("top", drafts))


def related_posts(slug: str, tags_csv: str, limit: int = 3):
    """Other published posts sharing at least one tag, most shared
    tags first, then most recent. Nothing fancy, just SQL."""
    tags = [t.strip() for t in tags_csv.split(",") if t.strip()]
    if not tags:
        return []
    now = utcnow().isoformat()
    placeholders = " OR ".join(["tags LIKE ?"] * len(tags))
    params = [f"%{t}%" for t in tags]
    q = f"""
        SELECT * FROM posts
        WHERE slug != ? AND published=1 AND pinned=0 AND unlisted=0 AND (scheduled_at='' OR scheduled_at<=?) AND {NOT_HOME}
        AND ({placeholders})
        ORDER BY created_at DESC LIMIT ?
    """  # noqa: S608 - the placeholders are only "tags LIKE ?", values bound
    return get_db().execute(q, [slug, now] + params + [limit]).fetchall()


def series_slug(series_name: str) -> str:
    return slugify(series_name) if series_name else ""


def series_names() -> list:
    """Every series' name, by name."""
    rows = get_db().execute("SELECT DISTINCT series_name FROM posts WHERE series_name != ''")
    return sorted((r["series_name"] for r in rows), key=str.lower)


def find_series(slug: str):
    """The series name whose /series/<slug> this is, or None."""
    for r in get_db().execute("SELECT DISTINCT series_name FROM posts WHERE series_name != ''"):
        if slugify(r["series_name"]) == slug:
            return r["series_name"]
    return None


def series_siblings(series_name: str):
    if not series_name:
        return []
    q = "SELECT * FROM posts WHERE series_name=? AND published=1 ORDER BY series_order, created_at"
    return get_db().execute(q, (series_name,)).fetchall()


def _today() -> str:
    return datetime.now(tz.site_zone()).strftime("%Y-%m-%d")


def increment_views(slug: str):
    db = get_db()
    db.execute("UPDATE posts SET views = views + 1 WHERE slug=?", (slug,))
    db.execute("INSERT INTO post_views_daily (slug, day, views) VALUES (?, ?, 1) "
               "ON CONFLICT(slug, day) DO UPDATE SET views = views + 1", (slug, _today()))
    db.commit()


def daily_views(days: int = 30) -> list:
    """[(day, views)] for the last `days` days, oldest first, every day
    present - a day nobody visited is a 0, not a gap."""
    from datetime import timedelta
    today = datetime.now(tz.site_zone()).date()
    start = today - timedelta(days=days - 1)
    rows = get_db().execute("SELECT day, SUM(views) AS n FROM post_views_daily WHERE day >= ? GROUP BY day",
                            (start.isoformat(),)).fetchall()
    counts = {r["day"]: r["n"] for r in rows}
    return [((start + timedelta(days=i)).isoformat(), counts.get((start + timedelta(days=i)).isoformat(), 0))
            for i in range(days)]


# the Stats page's ranges: key -> (label, how many buckets, bucket size)
VIEW_RANGES = {
    "7d": ("Last 7 days", 7, "day"),
    "30d": ("Last 30 days", 30, "day"),
    "90d": ("Last 90 days", 13, "week"),
    "12m": ("Last 12 months", 12, "month"),
}


def views_by_period(range_key: str = "30d") -> list:
    """[{"start", "end", "views"}] oldest first, every bucket present -
    days for a week or a month, weeks for 90 days, months for a year,
    so the chart never has more than about 30 bars."""
    from datetime import date, timedelta
    _, count, unit = VIEW_RANGES.get(range_key, VIEW_RANGES["30d"])
    today = datetime.now(tz.site_zone()).date()
    if unit == "day":
        return [{"start": d, "end": d, "views": n} for d, n in daily_views(count)]
    if unit == "week":
        first = today - timedelta(days=count * 7 - 1)
        buckets = [(first + timedelta(days=7 * i), first + timedelta(days=7 * i + 6)) for i in range(count)]
    else:
        buckets = []
        y, m = today.year, today.month
        for _ in range(count):
            nxt = date(y + (m == 12), m % 12 + 1, 1)
            buckets.insert(0, (date(y, m, 1), nxt - timedelta(days=1)))
            y, m = (y, m - 1) if m > 1 else (y - 1, 12)
    rows = get_db().execute("SELECT day, SUM(views) AS n FROM post_views_daily WHERE day >= ? GROUP BY day",
                            (buckets[0][0].isoformat(),)).fetchall()
    out = []
    for start, end in buckets:
        n = sum(r["n"] for r in rows if start.isoformat() <= r["day"] <= end.isoformat())
        out.append({"start": start.isoformat(), "end": end.isoformat(), "views": n})
    return out


def views_since(day: str) -> dict:
    """{slug: views} from day on."""
    rows = get_db().execute("SELECT slug, SUM(views) AS n FROM post_views_daily WHERE day >= ? GROUP BY slug",
                            (day,)).fetchall()
    return {r["slug"]: r["n"] for r in rows}


def increment_like(slug: str) -> int:
    db = get_db()
    db.execute("UPDATE posts SET likes = likes + 1 WHERE slug=?", (slug,))
    db.commit()
    return db.execute("SELECT likes FROM posts WHERE slug=?", (slug,)).fetchone()["likes"]


def ensure_preview_token(slug: str) -> str:
    """Drafts get a shareable, unguessable preview link on demand -
    generated the first time it's asked for, then reused."""
    row = get_post(slug)
    if row["preview_token"]:
        return row["preview_token"]
    token = secrets.token_urlsafe(16)
    get_db().execute("UPDATE posts SET preview_token=? WHERE slug=?", (token, slug))
    get_db().commit()
    return token


def search(query: str, limit: int = 20):
    if not query.strip():
        return []
    now = utcnow().isoformat()
    # sanitize FTS5 query syntax a plain search box shouldn't have to
    # think about - quote each term and OR them together. Each is a
    # prefix, so "plan" finds Plans and planning while it's being typed
    terms = re.findall(r"\w+", query)
    if not terms:
        return []
    match_expr = " OR ".join(f'"{t}"*' for t in terms)
    # a match in the title counts most, then the tags, then the text -
    # searching "plans" put the Plans page fourth, under pages that only
    # mentioned it (bm25's weights: slug, title, body, tags)
    # the homepage's own post is listed, Unlisted or not: it's at / for anyone
    # (an unlisted post is what the homepage picker offers, besides the menu's pages)
    q = """
        SELECT posts.* FROM posts_fts
        JOIN posts ON posts.slug = posts_fts.slug
        WHERE posts_fts MATCH ? AND posts.published=1
          AND (posts.unlisted=0 OR posts.slug IN (SELECT value FROM settings WHERE key='home_page'))
          AND (posts.scheduled_at='' OR posts.scheduled_at<=?)
        ORDER BY bm25(posts_fts, 0, 10.0, 1.0, 4.0) LIMIT ?
    """
    return get_db().execute(q, (match_expr, now, limit)).fetchall()


def load_post_body(slug: str) -> str:
    path = _path(slug)
    if not os.path.exists(path):
        return ""
    _, body = _parse_file(path)
    return body


def _trash_dir() -> str:
    d = os.path.join(config.posts_dir(), "_trash")
    os.makedirs(d, exist_ok=True)
    return d


def delete_post(slug: str):
    """Moves the post to trash - reversible, same "Delete" button and
    confirm dialog as before, but no longer instant/permanent. The
    underlying .md file moves into POSTS_DIR/_trash/, which
    reindex_from_disk() never looks inside (it's a flat os.listdir of
    POSTS_DIR itself), so a trashed post can't come back from the dead
    on a fresh boot the way a live one would. Only empty_trash()
    actually removes anything for good."""
    db = get_db()
    db.execute("DELETE FROM posts WHERE slug=?", (slug,))
    db.execute("DELETE FROM posts_fts WHERE slug=?", (slug,))
    db.execute("DELETE FROM post_links WHERE from_slug=?", (slug,))
    db.execute("DELETE FROM post_translations WHERE slug=?", (slug,))
    db.commit()
    path = _path(slug)
    if os.path.exists(path):
        os.rename(path, os.path.join(_trash_dir(), f"{slug}.md"))


def list_trash():
    """Mirrors images.list_trash()'s shape - a plain filesystem scan,
    no DB involvement, since a trashed post has already been removed
    from the posts table entirely. Title and tags come from re-parsing
    each file's own front matter (cheap, and there's no other copy of
    either once the DB row is gone - tags specifically so the trash
    tab can offer the same tag filter every other tab does); "trashed
    at" is the file's own mtime, which os.rename() (not a copy)
    preserves from whenever it actually landed in _trash/. views/likes
    aren't here and can't be - that's runtime usage data that was
    never written to the file to begin with, only ever lived in the
    now-deleted DB row."""
    trash_dir = _trash_dir()
    items = []
    for fn in os.listdir(trash_dir):
        if not fn.endswith(".md"):
            continue
        path = os.path.join(trash_dir, fn)
        meta, _ = _parse_file(path)
        items.append({
            "slug": fn[:-3],
            "title": meta.get("title", fn[:-3].replace("-", " ").title()),
            "tags": meta.get("tags", ""),
            "trashed_at": datetime.utcfromtimestamp(os.path.getmtime(path)).isoformat(),
        })
    items.sort(key=lambda i: i["trashed_at"], reverse=True)
    return items


def restore_from_trash(slug: str) -> bool:
    if "/" in slug or ".." in slug:
        return False
    src = os.path.join(_trash_dir(), f"{slug}.md")
    if not os.path.exists(src):
        return False
    os.rename(src, _path(slug))
    resync_from_file(slug)
    return True


def delete_forever(slug: str) -> bool:
    """Permanently removes one trashed post's file - the single-item
    version of empty_trash(), for deleting just one without waiting to
    clear everything else out too."""
    if "/" in slug or ".." in slug:
        return False
    path = os.path.join(_trash_dir(), f"{slug}.md")
    if not os.path.exists(path):
        return False
    os.remove(path)
    return True


def empty_trash() -> int:
    trash_dir = _trash_dir()
    count = 0
    for fn in os.listdir(trash_dir):
        path = os.path.join(trash_dir, fn)
        if os.path.isfile(path):
            os.remove(path)
            count += 1
    return count


def replace_upload_url(old: str, new: str) -> int:
    """Every post showing the upload at old - in its text or as its cover -
    points at new instead. The files are edited where they are, not saved
    as a new version, so no post looks updated. The number changed."""
    if not os.path.exists(config.posts_dir()):
        return 0
    whole = re.compile(re.escape(old) + r"(?![\w.-])")
    changed = 0
    for fn in sorted(os.listdir(config.posts_dir())):
        if not fn.endswith(".md"):
            continue
        path = os.path.join(config.posts_dir(), fn)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        updated = whole.sub(new, text)
        if updated == text:
            continue
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(updated)
        slug = fn[:-3]
        row = get_post(slug)
        resync_from_file(slug)
        if row:
            get_db().execute("UPDATE posts SET updated_at=? WHERE slug=?", (row["updated_at"], slug))
            get_db().commit()
        changed += 1
    return changed


def resync_from_file(slug: str):
    """Like reindex_from_disk's per-file logic, but overwrites an
    existing db row instead of skipping it - what a backup import
    needs, since the whole point is bringing possibly-changed content
    back in."""
    path = _path(slug)
    if not os.path.exists(path):
        return
    meta, body = _parse_file(path)
    now = utcnow().isoformat()
    existing = get_post(slug)
    created_at = str(meta.get("date", existing["created_at"] if existing else now[:10]))
    tags = str(meta.get("tags", ""))
    title = meta.get("title", slug.replace("-", " ").title())
    pin_location = str(meta.get("pin_location", "header"))
    if pin_location not in VALID_PIN_LOCATIONS:
        pin_location = "header"

    db = get_db()
    db.execute(_UPSERT_SQL, (
        slug, title, meta.get("summary", ""), tags,
        int(bool(meta.get("published", True))), int(bool(meta.get("pinned", False))),
        meta.get("cover_image", ""), tz.normalize_stored(meta.get("scheduled_at", "")),
        str(meta.get("series_name", "")), int(meta.get("series_order", 0) or 0),
        str(meta.get("parent_slug", "")), pin_location, int(meta.get("pin_order", 0) or 0),
        int(bool(meta.get("comments_enabled", True))),
        existing["preview_token"] if existing else str(meta.get("preview_token", "")),
        created_at, now,
    ))
    _sync_fts(slug, title, "" if meta.get("password") else public_part(body, meta.get("visibility")), tags)
    _index_redirects(slug, meta)
    _index_wiki_links(slug, body)
    db.commit()


def reindex_from_disk():
    """Rebuilds the posts table from whatever .md files exist. This is
    what makes the sqlite file genuinely disposable: delete blog.db,
    restart, and every post front-matter field comes back from the
    files themselves (except views/likes - that's usage data, not
    content, and deliberately isn't stored in the files).
    """
    if not os.path.exists(config.posts_dir()):
        return 0
    db = get_db()
    count = 0
    for fn in os.listdir(config.posts_dir()):
        if not fn.endswith(".md"):
            continue
        slug = fn[:-3]
        meta, body = _parse_file(os.path.join(config.posts_dir(), fn))
        if get_post(slug):
            continue  # already indexed, don't clobber updated_at etc
        now = utcnow().isoformat()
        tags = str(meta.get("tags", ""))
        title = meta.get("title", slug.replace("-", " ").title())
        pin_location = str(meta.get("pin_location", "header"))
        if pin_location not in VALID_PIN_LOCATIONS:
            pin_location = "header"
        db.execute(_UPSERT_SQL, (
            slug, title, meta.get("summary", ""), tags,
            int(bool(meta.get("published", True))),
            int(bool(meta.get("pinned", False))),
            meta.get("cover_image", ""),
            tz.normalize_stored(meta.get("scheduled_at", "")),
            str(meta.get("series_name", "")),
            int(meta.get("series_order", 0) or 0),
            str(meta.get("parent_slug", "")), pin_location, int(meta.get("pin_order", 0) or 0),
            int(bool(meta.get("comments_enabled", True))),
            str(meta.get("preview_token", "")),
            str(meta.get("date", now[:10])),
            now,
        ))
        _sync_fts(slug, title, "" if meta.get("password") else public_part(body, meta.get("visibility")), tags)
        _index_redirects(slug, meta)
        count += 1
    db.commit()
    if count:
        log.info("reindexed %s post(s) from disk", count)
    if count:
        # after every post is back: a [[link]] can point at a post the
        # loop above hadn't reached yet
        rebuild_wiki_links()
    db.commit()
    return count
