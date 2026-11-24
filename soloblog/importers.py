import logging
import io
import json
import re
import threading
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, UTC
from soloblog.tz import utcnow

from bs4 import BeautifulSoup
from markdownify import MarkdownConverter

from soloblog import cache
from soloblog import netguard
from soloblog import posts
from soloblog import settings

log = logging.getLogger(__name__)

# Moving a blog in: a WordPress export (.xml, Tools > Export), a Ghost
# export (.json, Settings > Labs > Export), a Medium export (.zip,
# Settings > Security and apps > Download your information), a Substack
# export (.zip, Settings > Exports - its subscribers come too) or a zip
# of markdown files (Jekyll, Hugo, Obsidian, Eleventy...). Each is
# read into the same list of plain dicts - title, slug, html, date,
# tags, draft or not, page or post - and saved as markdown posts, so
# the rest of Soloblog never knows where a post came from.
#
# Images can be copied into the media library as they're found; the
# copy runs in the background (start/status below) since a big blog
# can have hundreds.

MAX_IMPORT_BYTES = 50 * 1024 * 1024

WP = {
    "content": "http://purl.org/rss/1.0/modules/content/",
    "excerpt": "http://wordpress.org/export/1.2/excerpt/",
    "wp": "http://wordpress.org/export/1.2/",
    "dc": "http://purl.org/dc/elements/1.1/",
}


class ImportError_(ValueError):
    pass


# ---- html -> markdown

class _Converter(MarkdownConverter):
    """markdownify, plus what blog exports contain that it doesn't know:
    embeds become the bare link on its own line (Soloblog turns those
    back into click-to-load players), and figure captions stay under
    their image."""

    def convert_iframe(self, el, text, parent_tags=None):
        src = el.get("src") or ""
        if src.startswith("//"):
            src = "https:" + src
        m = re.search(r"youtube(?:-nocookie)?\.com/embed/([\w-]{6,})", src)
        if m:
            src = f"https://www.youtube.com/watch?v={m.group(1)}"
        m = re.search(r"player\.vimeo\.com/video/(\d+)", src)
        if m:
            src = f"https://vimeo.com/{m.group(1)}"
        return f"\n\n{src}\n\n" if src.startswith("http") else ""

    def convert_figcaption(self, el, text, parent_tags=None):
        return f"\n\n*{text.strip()}*\n\n" if text.strip() else ""

    def convert_script(self, el, text, parent_tags=None):
        return ""

    def convert_style(self, el, text, parent_tags=None):
        return ""


def _wp_autop(html: str) -> str:
    """WordPress's classic editor stores paragraphs as blank lines, not
    <p> tags - put them back before the html is read as html."""
    if re.search(r"<p[\s>]", html, re.I):
        return html
    blocks = [b.strip() for b in re.split(r"\n\s*\n", html) if b.strip()]
    return "\n".join(b if re.match(r"<(h\d|ul|ol|blockquote|pre|figure|div|table|iframe)", b, re.I)
                     else f"<p>{b.replace(chr(10), '<br>')}</p>" for b in blocks)


def _strip_shortcodes(html: str) -> str:
    # [caption ...]<img ...> Text[/caption] keeps its image and text;
    # anything else in [brackets] that looks like a shortcode goes
    html = re.sub(r"\[/?caption[^\]]*\]", "", html)
    return re.sub(r"\[/?[a-z_-]+(?:\s[^\]]*)?\]", "", html)


def html_to_markdown(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    md = _Converter(heading_style="ATX", bullets="-", code_language="", escape_underscores=False,
                    escape_asterisks=False).convert_soup(soup)
    return re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"


def _text(html: str, limit: int = 300) -> str:
    text = re.sub(r"\s+", " ", BeautifulSoup(html or "", "html.parser").get_text(" ")).strip()
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "…"


def _stamp(value: str) -> str:
    """Any of the exports' date formats -> our stored UTC form."""
    value = (value or "").strip()
    if not value or value.startswith("0000"):
        return ""
    for parse in (lambda v: datetime.fromisoformat(v.replace("Z", "+00:00")),
                  lambda v: datetime.strptime(v, "%Y-%m-%d %H:%M:%S")):
        try:
            dt = parse(value)
        except ValueError:
            continue
        if dt.tzinfo:
            dt = dt.astimezone(UTC).replace(tzinfo=None)
        return dt.isoformat(timespec="seconds")
    return ""


# ---- readers

def read_wordpress(data: bytes) -> list:
    try:
        root = ET.fromstring(data)  # noqa: S314 - an upload only the admin makes; ElementTree reads no outside entities
    except ET.ParseError as e:
        raise ImportError_("That doesn't look like a WordPress export file") from e
    items = []
    for item in root.iter("item"):
        kind = item.findtext("wp:post_type", "", WP)
        status = item.findtext("wp:status", "", WP)
        if kind not in ("post", "page") or status in ("trash", "auto-draft", "inherit"):
            continue
        html = _wp_autop(_strip_shortcodes(item.findtext("content:encoded", "", WP)))
        comments = []
        for c in item.findall("wp:comment", WP):
            if c.findtext("wp:comment_approved", "", WP) != "1" or c.findtext("wp:comment_type", "", WP) not in ("", "comment"):
                continue
            comments.append({
                "id": c.findtext("wp:comment_id", "", WP), "parent": c.findtext("wp:comment_parent", "0", WP),
                "author": c.findtext("wp:comment_author", "", WP) or "Anonymous",
                "email": c.findtext("wp:comment_author_email", "", WP),
                "date": _stamp(c.findtext("wp:comment_date_gmt", "", WP) or c.findtext("wp:comment_date", "", WP)),
                "body": _text(c.findtext("wp:comment_content", "", WP), 2000),
            })
        items.append({
            "title": (item.findtext("title") or "").strip() or "Untitled",
            "slug": item.findtext("wp:post_name", "", WP),
            "html": html,
            "summary": _text(item.findtext("excerpt:encoded", "", WP)),
            "date": _stamp(item.findtext("wp:post_date_gmt", "", WP) or item.findtext("wp:post_date", "", WP)),
            "published": status == "publish",
            "page": kind == "page",
            "tags": [c.text.strip() for c in item.findall("category") if c.text and c.get("domain") in ("post_tag", "category")
                     and c.text.strip().lower() != "uncategorized"],
            "cover": "",
            "comments": comments,
        })
    return items


def read_ghost(data: bytes, old_url: str = "") -> list:
    try:
        doc = json.loads(data)
    except (ValueError, UnicodeDecodeError) as e:
        raise ImportError_("That doesn't look like a Ghost export file") from e
    db = doc["db"][0]["data"] if isinstance(doc.get("db"), list) else doc.get("data", doc)
    tag_names = {t["id"]: t["name"] for t in db.get("tags", [])}
    post_tags = {}
    for pt in sorted(db.get("posts_tags", []), key=lambda x: x.get("sort_order", 0)):
        name = tag_names.get(pt["tag_id"])
        if name and not name.startswith("#"):  # "#internal" tags are Ghost's own
            post_tags.setdefault(pt["post_id"], []).append(name)
    items = []
    for p in db.get("posts", []):
        if p.get("status") not in ("published", "draft", "scheduled"):
            continue
        # Ghost writes its own address as __GHOST_URL__ - the old blog's
        # address, if given, makes those images reachable again
        html = (p.get("html") or "").replace("__GHOST_URL__", old_url)
        cover = (p.get("feature_image") or "").replace("__GHOST_URL__", old_url)
        items.append({
            "title": p.get("title") or "Untitled",
            "slug": p.get("slug") or "",
            "html": html,
            "summary": p.get("custom_excerpt") or _text(html),
            "date": _stamp(p.get("published_at") or p.get("created_at") or ""),
            "published": p.get("status") == "published",
            "page": p.get("type") == "page" or bool(p.get("page")),
            "tags": post_tags.get(p["id"], []),
            "cover": cover if cover.startswith("http") else "",
            "comments": [],
        })
    return items


def read_medium(data: bytes) -> list:
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as e:
        raise ImportError_("That doesn't look like a Medium export (.zip)") from e
    items = []
    for name in zf.namelist():
        if not re.match(r"^(?:[^/]+/)?posts/[^/]+\.html$", name):
            continue
        soup = BeautifulSoup(zf.read(name).decode("utf-8", "replace"), "html.parser")
        title = soup.find(class_="p-name") or soup.find("h1") or soup.find("title")
        body = soup.find("section", attrs={"data-field": "body"}) or soup.find("body")
        if body is None:
            continue
        # Medium repeats the title and subtitle as the body's first lines
        for dup in body.find_all(["h3", "h4"], class_=re.compile("graf--title|graf--subtitle")):
            dup.decompose()
        when = soup.find("time", class_="dt-published")
        subtitle = soup.find("section", attrs={"data-field": "subtitle"})
        base = name.rsplit("/", 1)[-1][:-5]
        slug = re.sub(r"-[0-9a-f]{10,12}$", "", re.sub(r"^\d{4}-\d{2}-\d{2}_", "", base))
        items.append({
            "title": title.get_text(" ", strip=True) if title else "Untitled",
            "slug": slug if not base.startswith("draft_") else slug[len("draft_"):],
            "html": body.decode_contents(),
            "summary": subtitle.get_text(" ", strip=True) if subtitle else "",
            "date": _stamp(when.get("datetime", "")) if when else "",
            "published": not base.startswith("draft_"),
            "page": False,
            "tags": [],
            "cover": "",
            "comments": [],
        })
    if not items:
        raise ImportError_("No posts found in that zip - Medium exports keep them in a posts/ folder")
    return items


def read_substack(zf) -> list:
    """posts.csv lists every post; posts/<id>.html holds each one's body.
    The subscriber list (email_list*.csv) comes along as one extra item."""
    import csv
    names = zf.namelist()
    index = next(n for n in names if n.rsplit("/", 1)[-1] == "posts.csv")
    folder = index[:-len("posts.csv")]
    items = []
    for row in csv.DictReader(io.StringIO(zf.read(index).decode("utf-8-sig", "replace"))):
        post_id = row.get("post_id") or ""
        path = f"{folder}posts/{post_id}.html"
        if path not in names:
            continue
        items.append({
            "title": (row.get("title") or "").strip() or "Untitled",
            "slug": post_id.split(".", 1)[1] if "." in post_id else "",
            "html": zf.read(path).decode("utf-8", "replace"),
            "summary": (row.get("subtitle") or "").strip(),
            "date": _stamp(row.get("post_date") or ""),
            "published": (row.get("is_published") or "").lower() == "true",
            "page": False,
            "tags": [],
            "cover": "",
            "comments": [],
        })
    for n in names:
        if re.search(r"(^|/)email_list[^/]*\.csv$", n):
            items.append({"kind": "subscribers", "title": "Subscribers",
                          "csv": zf.read(n).decode("utf-8-sig", "replace")})
    if not any(i.get("kind") != "subscribers" for i in items):
        raise ImportError_("No posts found in that Substack export")
    return items


_FRONT = re.compile(r"\A(?:\ufeff)?---\s*\n(.*?)\n---\s*\n", re.S)
_IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".svg")


def read_markdown(zf) -> list:
    """Markdown files with (or without) YAML front matter, as Jekyll,
    Hugo, Eleventy, Obsidian and most static site tools write them.
    Images inside the zip come along with their posts."""
    import yaml
    names = zf.namelist()
    images = {n: n.rsplit("/", 1)[-1].lower() for n in names if n.lower().endswith(_IMAGE_EXT)}
    items = []
    for name in names:
        low = name.lower()
        if not low.endswith((".md", ".markdown")) or "/." in "/" + name or low.rsplit("/", 1)[-1] in ("readme.md",):
            continue
        text = zf.read(name).decode("utf-8", "replace")
        meta, body = {}, text
        m = _FRONT.match(text)
        if m:
            try:
                meta = yaml.safe_load(m.group(1)) or {}
            except yaml.YAMLError:
                meta = {}
            body = text[m.end():]
            if not isinstance(meta, dict):
                meta = {}
        base = name.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        # a Hugo page bundle (my-post/index.md) is named by its folder
        if base in ("index", "_index") and "/" in name:
            base = name.rsplit("/", 2)[-2]
        heading = re.match(r"\s*#\s+(.+)", body)
        title = str(meta.get("title") or (heading.group(1).strip() if heading else "") or base.replace("-", " "))
        if heading and not meta.get("title"):
            body = body[heading.end():]  # the title isn't repeated as the first line
        tags = meta.get("tags") or []
        tags = [t.strip() for t in (tags.split(",") if isinstance(tags, str) else tags) if str(t).strip()]
        cats = meta.get("categories") or []
        tags += [str(c) for c in (cats.split(",") if isinstance(cats, str) else cats) if str(c).strip()]
        date = meta.get("date") or re.match(r"(\d{4}-\d{2}-\d{2})", base)
        date = date.group(1) if isinstance(date, re.Match) else str(date or "")
        cover = str(meta.get("cover") or meta.get("image") or meta.get("featured_image") or "")
        if isinstance(meta.get("cover"), dict):
            cover = str(meta["cover"].get("image") or "")
        items.append({
            "title": title,
            # Jekyll names files 2020-01-01-my-post.md
            "slug": str(meta.get("slug") or re.sub(r"^\d{4}-\d{2}-\d{2}-", "", base)),
            "markdown": body.strip() + "\n",
            "html": "",
            "summary": str(meta.get("description") or meta.get("summary") or meta.get("excerpt") or ""),
            "date": _stamp(date[:19]) if len(date) > 10 else date[:10],
            "published": not (meta.get("draft") or "/_drafts/" in "/" + name or meta.get("published") is False),
            "page": False,
            "tags": [str(t) for t in tags],
            "cover": cover,
            "comments": [],
            "zip_images": {path: zf.read(path) for path in images},
            "zip_dir": name.rsplit("/", 1)[0] + "/" if "/" in name else "",
        })
    if not items:
        raise ImportError_("No markdown files (.md) found in that zip")
    return items


def _zip_images_to_uploads(md: str, item: dict, copied: dict) -> str:
    """Images the post points at inside the zip - by relative path, from
    the zip's root, or (Obsidian's ![[photo.png]]) by name alone - saved
    to the media library, and the links pointed there."""
    files = item.get("zip_images") or {}
    if not files:
        return md
    from soloblog import images
    by_name = {}
    for path in files:
        by_name.setdefault(path.rsplit("/", 1)[-1].lower(), path)

    def upload(ref: str):
        ref = ref.split("#")[0].split("?")[0].strip().strip("<>")
        if ref.startswith(("http://", "https://", "/uploads/")):
            return None
        candidates = [item["zip_dir"] + ref, ref.lstrip("/")]
        path = next((c for c in candidates if c in files), None) or by_name.get(ref.rsplit("/", 1)[-1].lower())
        if not path:
            return None
        if path not in copied:
            try:
                copied[path] = images.save_upload(files[path], path)
            except Exception as e:
                log.warning("skipped image %s: %s", path, e)
                copied[path] = None
        return copied[path]

    md = re.sub(r"!\[\[([^\]|]+)(?:\|[^\]]*)?\]\]",
                lambda m: f"![]({upload(m.group(1)) or m.group(1)})", md)
    return re.sub(r"(!\[[^\]]*\]\()([^)\s]+)", lambda m: m.group(1) + (upload(m.group(2)) or m.group(2)), md)


def _absolute_images(items: list, old_url: str):
    """Root-relative image paths ("/wp-content/uploads/x.jpg") point at
    the old blog - with its address given, make them full links."""
    if not old_url:
        return items
    for item in items:
        if item.get("kind") == "subscribers":
            continue
        item["html"] = re.sub(r'(<img\b[^>]*?\bsrc=")(/(?!/)[^"]*)"', lambda m: f'{m.group(1)}{old_url}{m.group(2)}"',
                              item["html"], flags=re.I)
        if item["cover"].startswith("/") and not item["cover"].startswith("//"):
            item["cover"] = old_url + item["cover"]
    return items


def read(filename: str, data: bytes, old_url: str = "") -> tuple:
    """(source name, items) for an uploaded export, by what it contains.
    old_url - the old blog's address, for images the export only gives
    as paths on it."""
    old_url = old_url.strip().rstrip("/")
    if old_url and not re.match(r"^https?://[^/\s]+(/[^\s]*)?$", old_url):
        raise ImportError_("The old blog's URL should look like https://blog.example.com")
    source, items = _read(data, old_url)
    return source, _absolute_images(items, old_url)


def _read(data: bytes, old_url: str) -> tuple:
    head = data[:2000].lstrip()
    if data[:2] == b"PK":
        try:
            zf = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile as e:
            raise ImportError_("That zip file couldn't be opened") from e
        names = zf.namelist()
        if any(n.rsplit("/", 1)[-1] == "posts.csv" for n in names):
            return "Substack", read_substack(zf)
        if any(n.lower().endswith((".md", ".markdown")) for n in names):
            return "Markdown", read_markdown(zf)
        return "Medium", read_medium(data)
    if head.startswith(b"<") and b"wordpress.org/export" in data[:20000]:
        return "WordPress", read_wordpress(data)
    if head.startswith(b"{"):
        return "Ghost", read_ghost(data, old_url)
    raise ImportError_("Choose a WordPress .xml, a Ghost .json, or a Medium, Substack or markdown .zip")


# ---- saving

_IMG = re.compile(r'<img\b[^>]*?\bsrc="(https?://[^"]+)"', re.I)


def _copy_image(url: str, copied: dict) -> str:
    """The media library's copy of an outside image, or the original URL
    if it can't be fetched (it stays a working link either way)."""
    if url in copied:
        return copied[url]
    from soloblog import images
    try:
        local = images.save_upload(netguard.fetch(url), url.split("?")[0].rsplit("/", 1)[-1])
    except Exception as e:
        log.warning("kept %s as a link: %s", url, e)
        local = url
    copied[url] = local
    return local


def save_all(items: list, as_drafts: bool = False, copy_images: bool = False, progress=None) -> dict:
    """Saves each item as a post. A post already imported (same slug
    and title) is skipped, so running an import twice is harmless."""
    s = settings.get_all()
    author = s.get("author_name") or s["site_title"]
    counts = {"posts": 0, "pages": 0, "skipped": 0, "comments": 0, "images": 0, "subscribers": 0}
    copied = {}
    for n, item in enumerate(items, 1):
        if progress:
            progress(f"Importing {n} of {len(items)}: {item['title'][:60]}")
        if item.get("kind") == "subscribers":
            from soloblog import newsletter
            counts["subscribers"] += newsletter.import_csv(item["csv"])[0]
            continue
        wanted = posts.slugify(item["slug"] or item["title"]) or "post"
        existing = posts.get_post(wanted)
        if existing and existing["title"] == item["title"]:
            counts["skipped"] += 1
            continue
        html = item["html"]
        cover = item["cover"]
        if copy_images:
            before = len(copied)
            html = _IMG.sub(lambda m: m.group(0).replace(m.group(1), _copy_image(m.group(1), copied)), html)
            if cover:
                cover = _copy_image(cover, copied)
            counts["images"] += sum(1 for u in list(copied)[before:] if copied[u].startswith("/uploads/"))
        body = item.get("markdown") or html_to_markdown(html)
        if item.get("zip_images"):
            before = sum(1 for v in copied.values() if v)
            body = _zip_images_to_uploads(body, item, copied)
            if cover and not cover.startswith(("http", "/uploads/")):
                cover = _zip_images_to_uploads(f"![]({cover})", item, copied)[4:-1]
            counts["images"] += sum(1 for v in copied.values() if v) - before
        # the old address's slug where it's free, else the same with -2, -3...
        slug = posts.unique_slug(wanted)
        posts.save_post(
            slug, item["title"], author, body, ", ".join(item["tags"]), item["summary"],
            published=item["published"] and not as_drafts, pinned=item["page"], cover_image=cover,
            pin_location="footer", created_at=item["date"] or None,
        )
        counts["pages" if item["page"] else "posts"] += 1
        counts["comments"] += _save_comments(slug, item["comments"])
    cache.bump()
    return counts


def _save_comments(slug: str, items: list) -> int:
    """A WordPress post's approved comments, threads kept, as already
    approved and confirmed - they were moderated where they came from."""
    from soloblog.db import get_db
    db = get_db()
    ids = {}
    for c in sorted(items, key=lambda c: c["date"]):
        cur = db.execute(
            "INSERT INTO comments (post_slug, author_name, email, body, approved, confirmed_at, parent_id, created_at) "
            "VALUES (?, ?, ?, ?, 1, ?, ?, ?)",
            (slug, c["author"][:80], c["email"][:200], c["body"], c["date"] or utcnow().isoformat(),
             ids.get(c["parent"]), c["date"] or utcnow().isoformat()))
        ids[c["id"]] = cur.lastrowid
    db.commit()
    return len(items)


# ---- running in the background

_state = {"running": False, "message": "", "error": False}
_lock = threading.Lock()


def status() -> dict:
    with _lock:
        return dict(_state)


def start(items: list, source: str, as_drafts: bool, copy_images: bool) -> bool:
    """Runs save_all on a background thread. False if one is already running."""
    with _lock:
        if _state["running"]:
            return False
        _state.update(running=True, message=f"Starting the {source} import…", error=False)

    def progress(message):
        with _lock:
            _state["message"] = message

    def run():
        try:
            c = save_all(items, as_drafts, copy_images, progress)
            parts = [f"{c['posts']} post{'s' if c['posts'] != 1 else ''}"]
            if c["pages"]:
                parts.append(f"{c['pages']} page{'s' if c['pages'] != 1 else ''}")
            if c["comments"]:
                parts.append(f"{c['comments']} comment{'s' if c['comments'] != 1 else ''}")
            if c["images"]:
                parts.append(f"{c['images']} image{'s' if c['images'] != 1 else ''}")
            if c["subscribers"]:
                parts.append(f"{c['subscribers']} subscriber{'s' if c['subscribers'] != 1 else ''}")
            message = f"Imported {', '.join(parts)} from {source}."
            if c["skipped"]:
                message += f" {c['skipped']} already here, skipped."
            error = False
        except Exception:
            # the details (a missing field, a damaged file) are for whoever
            # looks into it: Site health > Log, and the bug report
            log.exception("the import from %s stopped", source)
            message, error = ("The import stopped - the file wasn't quite what was expected. Site health's Log "
                              "has the details"), True
        with _lock:
            _state.update(running=False, message=message, error=error)

    threading.Thread(target=run, name="import", daemon=True).start()
    return True
