import contextlib
import logging
import os
import re
import secrets
import shutil
import threading
import io
from datetime import datetime
from functools import lru_cache
from PIL import Image

from soloblog import cache
from soloblog import config
from soloblog import storage
from soloblog.db import get_db

log = logging.getLogger(__name__)

# what opening or converting an image can raise: a missing or unreadable
# file and anything Pillow can't decode (OSError, which its
# UnidentifiedImageError is), a bad value, or a decompression bomb
IMAGE_ERRORS = (OSError, ValueError, Image.DecompressionBombError)

# as big as a wide screen at twice the density needs (a 1280px band on a
# laptop's sharp screen) - 1600 showed soft there.
MAX_DIMENSION = 2560
# what an upload may be - not every format Pillow can read (EPS, PSD...)
FORMATS = ("JPEG", "PNG", "GIF", "WEBP", "BMP", "TIFF")
# decoding is width x height x 3 bytes, whatever the file's size - a
# small PNG can say 20,000 x 20,000 and want gigabytes. A JPEG is decoded
# at a fraction of its size (draft), so a 200-megapixel phone photo is
# fine; anything else this big is refused before it's decoded.
MAX_PIXELS = 50_000_000
# Pillow's own guard warns, then refuses at twice its limit - too late
# for a small server; MAX_PIXELS above is the guard instead
Image.MAX_IMAGE_PIXELS = None

# Smaller copies for pages that show an image smaller than it is: a card
# or thumbnail asks for /uploads/x.webp?w=400, and srcset lets the
# browser choose. Made on first request and kept in uploads/_sizes/<w>/
# - a subfolder, so the media library, backups and bucket sync (which
# all read only the top folder) never see them, and a fresh disk simply
# makes them again from the original.
SIZES = (400, 800, 1600)


def plain_name(filename: str) -> bool:
    """A file name from outside that can only mean one upload: not empty,
    no folder in it, and not one of the uploads folder's own (_trash,
    _sizes, _originals) - "" or "_sizes" pointed at a whole folder."""
    return bool(filename) and not any(c in filename for c in "/\\\0") and ".." not in filename \
        and not filename.startswith((".", "_"))


def name_part(name: str) -> str:
    """"Balcony Tomatoes (1).JPG" -> "balcony-tomatoes-1": the readable part
    of a file name - letters, numbers and dashes, at most 40 characters."""
    import unicodedata
    base = os.path.splitext(os.path.basename(name or ""))[0]
    base = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", base).strip("-")[:40].strip("-")


def _new_name(name: str, ext: str) -> str:
    """A readable name from the file's own, and four random characters so
    two photos both called IMG_0001 never collide: img-0001-3f9a.webp."""
    base = name_part(name) or "image"
    while True:
        filename = f"{base}-{secrets.token_hex(2)}.{ext}"
        if not os.path.exists(os.path.join(config.uploads_dir(), filename)):
            return filename


def save_upload(file_bytes: bytes, name: str = "") -> str:
    """name - what the file was called, for a readable name here. Raises
    ValueError for something that isn't an image it takes."""
    try:
        img = Image.open(io.BytesIO(file_bytes), formats=FORMATS)
    except IMAGE_ERRORS as e:
        raise ValueError("not an image Soloblog can use (JPEG, PNG, GIF, WebP)") from e
    if img.format in ("JPEG", "MPO"):
        img.draft("RGB", (MAX_DIMENSION, MAX_DIMENSION))
    if img.size[0] * img.size[1] > MAX_PIXELS:
        raise ValueError("too many pixels - make it smaller than 50 megapixels first")
    # a see-through PNG (a logo, a cut-out) stays see-through - flattened,
    # its clear parts came out black
    clear = img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info)
    img = img.convert("RGBA" if clear else "RGB")
    if max(img.size) > MAX_DIMENSION:
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION))

    os.makedirs(config.uploads_dir(), exist_ok=True)
    filename = _new_name(name, "webp")
    img.save(os.path.join(config.uploads_dir(), filename), "WEBP", quality=82)
    storage.mirror_upload(filename)
    cache.bump()
    return f"/uploads/{filename}"


# audio and video the media library takes as they are (no converting):
# extension -> ("audio" | "video", what the file's first bytes must hold)
MEDIA_TYPES = {
    "mp4": "video", "m4v": "video", "mov": "video", "webm": "video",
    "mp3": "audio", "m4a": "audio", "ogg": "audio", "oga": "audio", "wav": "audio", "flac": "audio",
    "pdf": "document",
}


def kind_of(filename: str) -> str:
    """"image", "audio", "video" or "document" (a PDF), by extension."""
    return MEDIA_TYPES.get(filename.rsplit(".", 1)[-1].lower(), "image")


def _looks_like(ext: str, head: bytes) -> bool:
    """A quick check of the file's signature, so a renamed file of some
    other kind isn't served as media."""
    if ext in ("mp4", "m4v", "mov", "m4a"):
        return head[4:8] in (b"ftyp", b"moov", b"mdat", b"wide", b"free")
    if ext == "webm":
        return head[:4] == b"\x1a\x45\xdf\xa3"
    if ext == "mp3":
        return head[:3] == b"ID3" or (len(head) > 1 and head[0] == 0xFF and head[1] & 0xE0 == 0xE0)
    if ext in ("ogg", "oga"):
        return head[:4] == b"OggS"
    if ext == "wav":
        return head[:4] == b"RIFF" and head[8:12] == b"WAVE"
    if ext == "flac":
        return head[:4] == b"fLaC"
    if ext == "pdf":
        return head[:5] == b"%PDF-"
    return False


def save_media(file_bytes: bytes, original_name: str) -> str:
    """An audio or video file, or a PDF, into the library, as it is.
    Raises ValueError for anything that isn't one of MEDIA_TYPES."""
    ext = (original_name or "").rsplit(".", 1)[-1].lower()
    if ext not in MEDIA_TYPES or not _looks_like(ext, file_bytes[:16]):
        raise ValueError("not a supported audio, video or PDF file")
    if len(file_bytes) > config.MAX_MEDIA_MB * 1024 * 1024:
        raise ValueError(f"over {config.MAX_MEDIA_MB} MB")
    os.makedirs(config.uploads_dir(), exist_ok=True)
    filename = _new_name(original_name, ext)
    with open(os.path.join(config.uploads_dir(), filename), "wb") as f:
        f.write(file_bytes)
    storage.mirror_upload(filename)
    cache.bump()
    return f"/uploads/{filename}"


def _sizes_path(width: int, filename: str) -> str:
    return os.path.join(config.uploads_dir(), "_sizes", str(width), filename)


def clear_sizes():
    """Every image's smaller copies - sized() makes each again the next
    time a page asks for it (Site health > Disk space)."""
    shutil.rmtree(os.path.join(config.uploads_dir(), "_sizes"), ignore_errors=True)


def _drop_sizes(filename: str):
    for width in SIZES:
        with contextlib.suppress(OSError):
            os.remove(_sizes_path(width, filename))


# Making a smaller copy decodes the whole picture. A page of 80 new ones
# asked for at once ran a 512 MB server out of memory, and every picture
# asked for while it restarted failed - so two are made at a time, and the
# rest wait their turn.
_RESIZING = threading.BoundedSemaphore(2)


def sized(filename: str, width: int) -> str:
    """The path to serve for filename at most width px wide: its smaller
    copy, made now if it's missing or older than the original - or the
    original itself when it's no wider than that, isn't a size we make,
    or can't be resized (an animation, an unreadable file)."""
    src = os.path.join(config.uploads_dir(), filename)
    if width not in SIZES:
        return src
    dest = _sizes_path(width, filename)
    if _fresh(dest, src):
        return dest
    with _RESIZING:
        return _make_sized(src, dest, width)


def _fresh(dest, src) -> bool:
    try:
        return os.path.getmtime(dest) >= os.path.getmtime(src)
    except OSError:
        return False


def _make_sized(src, dest, width) -> str:
    # made while this one waited its turn
    if _fresh(dest, src):
        return dest
    try:
        with Image.open(src) as img:
            fmt = img.format
            if img.width <= width or getattr(img, "is_animated", False) or fmt not in ("WEBP", "JPEG", "PNG"):
                return src
            # thumbnail, not resize: it shrinks in steps (a JPEG decodes small
            # to begin with), so the full picture is never held at full size twice
            img.draft("RGB", (width, img.height))
            img.thumbnail((width, img.height), Image.LANCZOS, reducing_gap=3.0)
            small = img.convert("RGBA" if img.mode in ("RGBA", "LA", "P") and fmt != "JPEG" else "RGB")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        # written aside and renamed: two first requests at once can't
        # serve each other a half-written file
        tmp = f"{dest}.{secrets.token_hex(4)}.tmp"
        small.save(tmp, fmt, quality=80)
        os.replace(tmp, dest)
        return dest
    except IMAGE_ERRORS as e:
        log.warning("couldn't make a smaller copy of %s: %s", src, e)
        return src


@lru_cache(maxsize=2048)
def _width(path: str, mtime: float):
    try:
        with Image.open(path) as img:
            return img.width
    except IMAGE_ERRORS:
        return None


def width_of(url: str):
    """Pixel width of one of our uploads, or None (not ours, not on disk)."""
    if not url or not url.startswith("/uploads/"):
        return None
    path = os.path.join(config.uploads_dir(), url[len("/uploads/"):])
    try:
        return _width(path, os.path.getmtime(path))
    except OSError:
        return None


def srcset(url: str) -> str:
    """"x?w=400 400w, x?w=800 800w, x 1600w" - every smaller copy worth
    having plus the original, or "" when there's nothing smaller."""
    width = width_of(url)
    if not width:
        return ""
    smaller = [f"{url}?w={s} {s}w" for s in SIZES if s < width]
    return ", ".join(smaller + [f"{url} {width}w"]) if smaller else ""


def responsive(url: str, sizes: str) -> dict:
    """src, srcset and sizes for an Img(**...). sizes says how wide the
    image shows on the page, e.g. "(min-width: 768px) 768px, 100vw"."""
    options = srcset(url)
    return {"src": url, "srcset": options, "sizes": sizes} if options else {"src": url}


def thumb(url: str) -> str:
    """The 400 px copy's URL for a small thumbnail - the original when
    it's no wider than that anyway."""
    width = width_of(url)
    return f"{url}?w={SIZES[0]}" if width and width > SIZES[0] else url


def _dimensions(path):
    """(width, height) in pixels, or None if the file can't be read as
    an image - a media card shouldn't 500 the whole page over one
    corrupt or in-flight upload, it should just skip that one detail."""
    try:
        return _dimensions_of(path, os.stat(path).st_mtime_ns)
    except OSError:
        return None


# opening every image for its size made a big library slow to list;
# the file's mtime in the key means an edited image is read again
@lru_cache(maxsize=20000)
def _dimensions_of(path, mtime_ns):
    try:
        with Image.open(path) as img:
            return img.size
    except IMAGE_ERRORS:
        return None


def list_uploads():
    """Newest first - so the image you just uploaded is easy to find."""
    if not os.path.exists(config.uploads_dir()):
        return []
    items = []
    for fn in os.listdir(config.uploads_dir()):
        path = os.path.join(config.uploads_dir(), fn)
        if not os.path.isfile(path):
            continue
        stat = os.stat(path)
        items.append({
            "filename": fn,
            "url": f"/uploads/{fn}",
            "size_kb": round(stat.st_size / 1024, 1),
            "kind": kind_of(fn),
            "dimensions": _dimensions(path) if kind_of(fn) == "image" else None,
            "modified": datetime.utcfromtimestamp(stat.st_mtime).isoformat(),
            "mtime": int(stat.st_mtime),
        })
    items.sort(key=lambda x: x["modified"], reverse=True)
    return items


def delete_upload(filename: str) -> bool:
    if not plain_name(filename):
        return False
    path = os.path.join(config.uploads_dir(), filename)
    if os.path.isfile(path):
        os.remove(path)
        _drop_sizes(filename)
        _drop_original(filename)
        storage.mirror_delete(filename)
        cache.bump()
        return True
    return False


_usage = {"key": None, "map": {}}


def usage_map() -> dict:
    """usage_map_scan(), kept until a post file or a setting changes -
    the Media page, its details form and the image picker all ask, and
    reading every post each time got slow with a few thousand."""
    from soloblog import cache as _cache
    try:
        files = tuple(sorted((e.name, e.stat().st_mtime_ns) for e in os.scandir(config.posts_dir())
                             if e.name.endswith(".md")))
    except OSError:
        files = ()
    key = (files, _cache.generation())
    if _usage["key"] != key:
        _usage["map"], _usage["key"] = usage_map_scan(), key
    return _usage["map"]


# what Media's "Used in" calls a setting that holds a file
SETTING_NAMES = {"author_avatar_url": "Author avatar", "favicon_url": "Favicon", "header_icon_url": "Header icon",
                 "app_icon_url": "App icon", "share_image_url": "Share image", "banner_image_url": "Banner",
                 "custom_css": "Custom CSS", "custom_head": "Custom code"}


def usage_map_scan() -> dict:
    """filename -> where it's used: a {"slug", "title"} for each post
    that has it as its cover or in its text, and for each setting that
    holds it (slug None - "Favicon" isn't a post). For Media's "Used in"
    and its search; what isn't here is unused (list_orphans), so the two
    always agree."""
    import re
    from soloblog import config as _config
    from soloblog import settings as _settings
    from soloblog import posts as _posts

    usage = {}
    if os.path.exists(_config.posts_dir()):
        for fn in os.listdir(_config.posts_dir()):
            if not fn.endswith(".md"):
                continue
            path = os.path.join(_config.posts_dir(), fn)
            with open(path, encoding="utf-8") as f:
                content = f.read()
            filenames = set(re.findall(r"/uploads/([\w\-]+\.\w+)", content))
            if not filenames:
                continue
            slug = fn[:-3]
            meta, _ = _posts._parse_file(path)
            title = meta.get("title", slug.replace("-", " ").title())
            for filename in filenames:
                usage.setdefault(filename, []).append({"slug": slug, "title": title})

    # every setting, not a list of some: the header icon, app icon and
    # share image were missed, showed as unused, and were trashed as such
    for key, val in _settings.get_all().items():
        for filename in set(re.findall(r"/uploads/([\w\-]+\.\w+)", str(val or ""))):
            usage.setdefault(filename, []).append({"slug": None, "title": SETTING_NAMES.get(key, "Settings")})

    # an image's dark mode and phone versions are used wherever the image is -
    # phone first, so a phone version's own dark version is counted too
    for column in reversed(VERSIONS.values()):
        for row in get_db().execute(f"SELECT filename, {column} FROM image_meta WHERE {column} != ''"):  # noqa: S608 - column names from VERSIONS
            if row["filename"] in usage:
                usage.setdefault(row[column], []).extend(usage[row["filename"]])

    return usage


_UPLOAD_IMG = re.compile(r'<img\b[^>]*\bsrc="/uploads/([^"/]+)"[^>]*>')


_ANY_IMG = re.compile(r"<img\b[^>]*>")
_OUR_SRC = re.compile(r'\ssrc="/uploads/([^"/?]+)(?:\?(?:[^"]*&amp;)?w=(\d+))?[^"]*"')


def with_sizes(html: str) -> str:
    """A page's pictures of ours, each saying its width and height, so the
    page keeps their room while they load and nothing jumps. On a whole
    page, every picture after the first in <main> also waits until it's
    near the screen (loading="lazy") - unless whoever drew it said."""
    from urllib.parse import unquote
    from html import unescape
    main = html.find("<main")
    seen = 0

    def add(m):
        nonlocal seen
        tag, extra = m.group(0), ""
        in_main = main >= 0 and m.start() > main
        seen += in_main
        src = _OUR_SRC.search(tag)
        if src and " width=" not in tag and " height=" not in tag:
            name = unquote(unescape(src.group(1)))
            size = _dimensions(os.path.join(config.uploads_dir(), name)) if plain_name(name) else None
            if size and all(size):
                width, height = size
                # a smaller copy is as wide as it was asked for
                asked = int(src.group(2) or 0)
                if 0 < asked < width:
                    width, height = asked, max(1, round(height * asked / width))
                extra += f' width="{width}" height="{height}"'
        if in_main and seen > 1 and " loading=" not in tag and " fetchpriority=" not in tag:
            extra += ' loading="lazy"'
        return tag.replace("<img", "<img" + extra, 1) if extra else tag

    return _ANY_IMG.sub(add, html) if "<img" in html else html


# the shapes a picture sits in - a link, a figure, a gallery's tile - that
# are empty once it's gone, with its caption over the foot or beneath
_WRAPPER_OPEN = re.compile(r"<(a|p|figure|picture|div)\b[^>]*>\s*$")
_CAPTIONS = r"(?:<span\b[^>]*>[^<]*</span>|<figcaption\b[^>]*>.*?</figcaption>)*"
_MISSING_BOX = ('<div class="flex items-center justify-center border border-dashed border-base-content/30 '
                'rounded-box p-4 text-center text-sm text-base-content/60 {shape}">'
                'Image not found - replace it</div>')
_KEEP_SHAPE = re.compile(r"^(?:aspect-\S+|w-full|h-\S+|min-h-\S+|absolute|inset-\S+)$")


def is_missing(src: str) -> bool:
    """Whether a picture's address is one of our uploads that isn't on
    disk - a template's sample picture nobody has replaced yet."""
    if not src.startswith("/uploads/"):
        return False
    from urllib.parse import unquote
    from html import unescape
    name = unquote(unescape(src[len("/uploads/"):].split("?")[0]))
    return not (plain_name(name) and os.path.isfile(os.path.join(config.uploads_dir(), name)))


def without_missing(html: str, admin: bool = False) -> str:
    """A page's pictures of ours that aren't on disk: left out for a visitor
    along with the empty link, figure or tile around each, so nothing
    shows broken or empty; the admin sees a dashed box saying where one
    belongs."""
    if "/uploads/" not in html:
        return html
    out, last = [], 0
    for m in _ANY_IMG.finditer(html):
        src = re.search(r'\ssrc="([^"]*)"', m.group(0))
        if m.start() < last or not src or not is_missing(src.group(1)):
            continue
        if admin:
            kept = (re.search(r'\sclass="([^"]*)"', m.group(0)) or [0, ""])[1].split()
            shape = " ".join(c for c in kept if _KEEP_SHAPE.match(c)) or "min-h-24"
            out += [html[last:m.start()], _MISSING_BOX.format(shape=shape)]
            last = m.end()
            continue
        start, end = m.start(), m.end()
        while True:
            before = _WRAPPER_OPEN.search(html, max(last, start - 600), start)
            if not before:
                break
            closing = re.compile(r"\s*" + _CAPTIONS + r"\s*</" + before.group(1) + ">", re.S).match(html, end)
            if not closing:
                break
            start, end = before.start(), closing.end()
        out.append(html[last:start])
        last = end
    out.append(html[last:])
    return "".join(out)


# the other versions an image can have, shown in its place while the page
# is dark or on a phone (PICTURE_VERSIONS_JS): name -> image_meta column
VERSIONS = {"dark": "dark_version", "phone": "phone_version"}


_phone_seen = {}


def has_phone_versions() -> bool:
    """Whether any image has a phone version - then every page carries the
    script that swaps it in, themes or not. Remembered until the next
    change (cache.generation)."""
    key = cache.generation()
    if _phone_seen.get("key") != key:
        found = get_db().execute("SELECT 1 FROM image_meta WHERE phone_version != '' LIMIT 1").fetchone()
        _phone_seen.update(key=key, found=bool(found))
    return _phone_seen["found"]


def with_other_versions(html: str) -> str:
    """Each image with a dark mode or phone version gets it as data-dark-src
    or data-phone-src (its smaller copies as data-dark-srcset or
    data-phone-srcset); the page swaps it in while it's dark, or on a
    phone (PICTURE_VERSIONS_JS). A phone version that has a dark mode
    version of its own adds it as data-phone-dark-src (and -srcset), for a
    phone while the page is dark. One attribute, not a second <img>: pages
    pick a post's first image out and restyle it."""
    db = get_db()
    twins = {name: {r["filename"]: r[column] for r in db.execute(
        f"SELECT filename, {column} FROM image_meta WHERE {column} != ''")} for name, column in VERSIONS.items()}  # noqa: S608 - column names from VERSIONS
    if not any(twins.values()):
        return html
    from html import escape

    def add(m):
        tag, extra = m.group(0), ""
        pairs = [(name, found.get(m.group(1))) for name, found in twins.items()]
        pairs.append(("phone-dark", twins["dark"].get(twins["phone"].get(m.group(1)))))
        for name, other in pairs:
            if (not other or f"data-{name}-src" in tag
                    or not os.path.isfile(os.path.join(config.uploads_dir(), other))):
                continue
            extra += f' data-{name}-src="/uploads/{escape(other)}"'
            options = srcset(f"/uploads/{other}")
            if options:
                extra += f' data-{name}-srcset="{escape(options)}"'
        return tag.replace("<img", "<img" + extra, 1) if extra else tag

    return _UPLOAD_IMG.sub(add, html)


def list_orphans():
    """Uploads that don't appear to be used anywhere - candidates for
    the purge button. Best-effort: it only knows what it can find by
    scanning post files and settings, so anything referenced some other
    way (an external embed, a manually-typed path) won't be caught."""
    used = usage_map()
    return [u for u in list_uploads() if u["filename"] not in used]


def move_to_trash(filename: str) -> bool:
    if not plain_name(filename):
        return False
    src = os.path.join(config.uploads_dir(), filename)
    if not os.path.isfile(src):
        return False
    trash_dir = os.path.join(config.uploads_dir(), "_trash")
    os.makedirs(trash_dir, exist_ok=True)
    os.rename(src, os.path.join(trash_dir, filename))
    storage.mirror_move(filename, to_trash=True)
    cache.bump()
    return True


def list_trash():
    trash_dir = os.path.join(config.uploads_dir(), "_trash")
    if not os.path.exists(trash_dir):
        return []
    items = []
    for fn in os.listdir(trash_dir):
        path = os.path.join(trash_dir, fn)
        if os.path.isfile(path):
            # a real url, but not the public /uploads/ one - that route
            # only ever looks inside UPLOADS_DIR's own root and rejects
            # any "/" in the filename, so a trashed file (moved into
            # _trash/ specifically to stop being servable while trashed)
            # was never reachable there. This points at its own
            # login-gated route (routes/media.py) instead, just for
            # rendering a real thumbnail on this admin-only trash card.
            stat = os.stat(path)
            items.append({
                "filename": fn, "url": f"/admin/media/trash-file/{fn}",
                "size_kb": round(stat.st_size / 1024, 1),
                "dimensions": _dimensions(path),
                # the card's preview needs it, as a library item's does
                "mtime": int(stat.st_mtime),
            })
    return items


def restore_from_trash(filename: str) -> bool:
    if not plain_name(filename):
        return False
    trash_dir = os.path.join(config.uploads_dir(), "_trash")
    src = os.path.join(trash_dir, filename)
    if not os.path.isfile(src):
        return False
    os.rename(src, os.path.join(config.uploads_dir(), filename))
    storage.mirror_move(filename, to_trash=False)
    cache.bump()
    return True


def delete_forever(filename: str) -> bool:
    """Permanently removes one trashed image - the single-item version
    of empty_trash(), for deleting just one without waiting to clear
    everything else out too."""
    if not plain_name(filename):
        return False
    path = os.path.join(config.uploads_dir(), "_trash", filename)
    if not os.path.isfile(path):
        return False
    os.remove(path)
    _drop_sizes(filename)
    _drop_original(filename)
    storage.mirror_delete(filename, trash=True)
    cache.bump()
    return True


def empty_trash() -> int:
    trash_dir = os.path.join(config.uploads_dir(), "_trash")
    if not os.path.exists(trash_dir):
        return 0
    count = 0
    for fn in os.listdir(trash_dir):
        path = os.path.join(trash_dir, fn)
        if os.path.isfile(path):
            os.remove(path)
            _drop_sizes(fn)
            _drop_original(fn)
            storage.mirror_delete(fn, trash=True)
            count += 1
    cache.bump()
    return count


_EMPTY_META = {"alt_text": "", "caption": "", "credit_name": "", "credit_url": "", "credit_source": "",
               "dark_version": "", "phone_version": ""}

# where an imported photo came from, for the "on Pexels" half of a credit
CREDIT_SOURCES = {"pixabay": "Pixabay", "pexels": "Pexels", "unsplash": "Unsplash"}
# the source's own site, linked from "on Unsplash" where its terms ask for it
CREDIT_SOURCE_URLS = {"unsplash": "https://unsplash.com/?utm_source=soloblog&utm_medium=referral"}


# ---- rotating and cropping (Admin > Media > an image's details)

# name: (label, width / height)
RATIOS = {"16:9": ("Wide 16:9", 16 / 9), "3:2": ("Photo 3:2", 3 / 2), "4:3": ("4:3", 4 / 3),
          "1:1": ("Square", 1.0), "4:5": ("Portrait 4:5", 4 / 5)}
KEEP = ("center", "top", "bottom", "left", "right")


def _original_path(filename: str) -> str:
    return os.path.join(config.uploads_dir(), "_originals", filename)


def has_original(filename: str) -> bool:
    return os.path.exists(_original_path(filename))


def _drop_original(filename: str):
    if has_original(filename):
        os.remove(_original_path(filename))


def _saved_edit(filename: str):
    """After a change to the file itself: its smaller copies are stale,
    rendered posts carry its size, and the bucket wants the new one."""
    _drop_sizes(filename)
    cache.bump()
    storage.mirror_upload(filename)


def edit_image(filename: str, action: str, ratio: str = "", keep: str = "center") -> bool:
    """Rotates it a quarter turn ("left"/"right") or crops it to one of
    RATIOS, keeping the part `keep` names - in place, so every post using
    it shows the change. The first edit keeps the untouched file, for
    restore_original."""
    path = os.path.join(config.uploads_dir(), filename)
    if not plain_name(filename) or not os.path.isfile(path) or kind_of(filename) != "image":
        return False
    try:
        with Image.open(path) as im:
            fmt = im.format
            if fmt not in ("WEBP", "JPEG", "PNG") or getattr(im, "is_animated", False):
                return False
            im.load()
            if action in ("left", "right"):
                out = im.rotate(90 if action == "left" else -90, expand=True)
            elif action == "crop" and ratio in RATIOS:
                target = RATIOS[ratio][1]
                w, h = im.size
                cw, ch = (w, round(w / target)) if w / h < target else (round(h * target), h)
                x = {"left": 0, "right": w - cw}.get(keep, (w - cw) // 2)
                y = {"top": 0, "bottom": h - ch}.get(keep, (h - ch) // 2)
                out = im.crop((x, y, x + cw, y + ch))
            else:
                return False
        if not has_original(filename):
            os.makedirs(os.path.dirname(_original_path(filename)), exist_ok=True)
            shutil.copy2(path, _original_path(filename))
        tmp = f"{path}.{secrets.token_hex(4)}.tmp"
        out.save(tmp, fmt, quality=90)
        os.replace(tmp, path)
    except Exception as e:  # Pillow decoding a damaged file raises more than IMAGE_ERRORS
        log.warning("couldn't edit %s: %s", filename, e)
        return False
    _saved_edit(filename)
    return True


def restore_original(filename: str) -> bool:
    if not plain_name(filename) or not has_original(filename):
        return False
    shutil.move(_original_path(filename), os.path.join(config.uploads_dir(), filename))
    _saved_edit(filename)
    return True


def search_text(items, usage) -> dict:
    """filename -> everything a search should find it by, lowercased:
    its name, alt text, caption, credit, and the titles of the posts it's
    in. One query for all the details, not one per image."""
    meta = {r["filename"]: r for r in get_db().execute(
        "SELECT filename, alt_text, caption, credit_name FROM image_meta").fetchall()}
    out = {}
    for item in items:
        name = item["filename"]
        m = meta.get(name)
        parts = [name] + ([m["alt_text"], m["caption"], m["credit_name"]] if m else [])
        parts += [u["title"] for u in usage.get(name, [])]
        out[name] = " ".join(p for p in parts if p).lower()
    return out


_MD_IMAGE = re.compile(r"!\[([^\]]*)\]\((/uploads/[^)\s]+)")
_GALLERY_BLOCK = re.compile(r"^```gallery[^\n]*\n(.*?)^```", re.M | re.S)


def missing_alt(body: str, cover: str = "") -> int:
    """How many of our images in a post have no alt text - none typed in
    the markdown, none saved in the media library. Screen readers have
    nothing to say for them."""
    urls = [url for alt, url in _MD_IMAGE.findall(body or "") if not alt.strip()]
    for block in _GALLERY_BLOCK.findall(body or ""):
        urls += [line.split("|")[0].strip() for line in block.splitlines() if line.strip().startswith("/uploads/")]
    if (cover or "").startswith("/uploads/"):
        urls.append(cover)
    return sum(1 for url in dict.fromkeys(urls) if not meta_for_url(url).get("alt_text"))


def alt_texts() -> dict:
    """filename -> its saved alt text, for every image that has one."""
    return {r["filename"]: r["alt_text"] for r in get_db().execute(
        "SELECT filename, alt_text FROM image_meta WHERE alt_text != ''").fetchall()}


def matches(text: str, query: str) -> bool:
    """Every word of the query is somewhere in text."""
    return all(word in text for word in query.lower().split())


def rename_upload(filename: str, name: str):
    """A new name for an upload - the file, its original (if it's been
    edited) and its details move with it. Returns the new file name, or
    None. Posts and settings are pointed at it by the caller
    (routes/media.py), and the old address keeps working (renamed_to)."""
    path = os.path.join(config.uploads_dir(), filename)
    base = name_part(name)
    if not plain_name(filename) or not base or not os.path.isfile(path):
        return None
    ext = filename.rsplit(".", 1)[-1]
    new = f"{base}.{ext}"
    if new == filename:
        return None
    if os.path.exists(os.path.join(config.uploads_dir(), new)):
        new = _new_name(base, ext)
    os.replace(path, os.path.join(config.uploads_dir(), new))
    if has_original(filename):
        os.replace(_original_path(filename), _original_path(new))
    _drop_sizes(filename)
    db = get_db()
    db.execute("UPDATE image_meta SET filename=? WHERE filename=?", (new, filename))
    for column in VERSIONS.values():
        db.execute(f"UPDATE image_meta SET {column}=? WHERE {column}=?", (new, filename))  # noqa: S608 - column names from VERSIONS
    db.commit()
    storage.mirror_upload(new)
    storage.mirror_delete(filename)
    # the old address, for links from other sites and old versions of posts
    import json
    from soloblog import settings
    renames = json.loads(settings.get("upload_renames") or "{}")
    renames = {old: (new if to == filename else to) for old, to in renames.items()}
    renames[filename] = new
    settings.set_many({"upload_renames": json.dumps(renames)})
    cache.bump()
    return new


def renamed_to(filename: str):
    """What an upload is called now, if it was renamed."""
    import json
    from soloblog import settings
    return json.loads(settings.get("upload_renames") or "{}").get(filename)


def get_meta(filename: str) -> dict:
    """Alt text, caption and photo credit for one upload - Gallery's own
    per-image details drawer, not anything derived from the file itself.
    Empty strings (not None) for an image nobody's ever annotated, so
    callers never need a None-check to use these safely."""
    row = get_db().execute(
        "SELECT alt_text, caption, credit_name, credit_url, credit_source, dark_version, "
        "phone_version FROM image_meta WHERE filename=?",
        (filename,)
    ).fetchone()
    return dict(row) if row else dict(_EMPTY_META)


def set_meta(filename: str, alt_text: str, caption: str, credit_name: str = None, credit_url: str = None,
             credit_source: str = None, dark_version: str = None, phone_version: str = None):
    """None for a credit field keeps whatever's already saved - the
    details drawer edits all of them, a stock import sets all of them,
    nothing else should wipe a credit by accident. dark_version and
    phone_version: another upload's file name, or "" for none - only an
    image that's there."""
    current = get_meta(filename)

    def other(version, column):
        version = current[column] if version is None else version
        version = version.strip().rsplit("/", 1)[-1]
        if version and (version == filename or kind_of(version) != "image" or not plain_name(version)
                        or not os.path.isfile(os.path.join(config.uploads_dir(), version))):
            return ""
        return version

    dark_version = other(dark_version, "dark_version")
    phone_version = other(phone_version, "phone_version")
    credit_name = current["credit_name"] if credit_name is None else credit_name.strip()
    credit_url = current["credit_url"] if credit_url is None else credit_url.strip()
    credit_source = current["credit_source"] if credit_source is None else credit_source
    if credit_url and not credit_url.startswith(("https://", "http://")):
        credit_url = ""
    db = get_db()
    db.execute(
        "INSERT INTO image_meta (filename, alt_text, caption, credit_name, credit_url, credit_source, dark_version, "
        "phone_version) VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(filename) DO UPDATE SET "
        "alt_text=excluded.alt_text, caption=excluded.caption, credit_name=excluded.credit_name, "
        "credit_url=excluded.credit_url, credit_source=excluded.credit_source, "
        "dark_version=excluded.dark_version, phone_version=excluded.phone_version",
        (filename, alt_text.strip(), caption.strip(), credit_name, credit_url, credit_source, dark_version,
         phone_version)
    )
    db.commit()
    cache.bump()


def meta_for_url(url: str) -> dict:
    """get_meta for a /uploads/ url - anything else (an outside image
    url) has no saved metadata and gets the empty set."""
    if url and url.startswith("https://images.unsplash.com/"):
        # hotlinked (stock.py) - its details are saved against the URL itself
        return get_meta(url)
    if not url or not url.startswith("/uploads/"):
        return dict(_EMPTY_META)
    return get_meta(url.rsplit("/", 1)[-1])


def credit_html(meta: dict) -> str:
    """"Photo by Name on Pexels" for a stock photo, "Image by Name" for a
    credit typed in Media - the name linked when there's a link, the
    source linked to its site. Escaped here,
    since it's dropped straight into rendered post html."""
    from html import escape
    name = meta.get("credit_name") or ""
    if not name:
        return ""
    url = meta.get("credit_url") or ""
    who = (f'<a href="{escape(url)}" class="link link-hover" rel="noopener" target="_blank">{escape(name)}</a>'
           if url else escape(name))
    source = CREDIT_SOURCES.get(meta.get("credit_source") or "")
    home = CREDIT_SOURCE_URLS.get(meta.get("credit_source") or "")
    if source and home:
        source = f'<a href="{escape(home)}" class="link link-hover" rel="noopener" target="_blank">{source}</a>'
    from soloblog import i18n
    # translated with placeholders, then the (already escaped) links go in
    if source:
        return escape(i18n.t("Photo by {name} on {source}", name="\0", source="\1")) \
            .replace("\0", who).replace("\1", source)
    # a credit typed by hand: a drawing, a diagram or a screenshot isn't a photo
    return escape(i18n.t("Image by {name}", name="\0")).replace("\0", who)


# how that line looks: under a picture, or over the corner of one that
# fills the screen with words on it
CAPTION_CLS = "text-xs text-base-content/60 text-center"
# on its own dark chip, as a gallery tile's credit (pages.CREDIT_OVER): the
# picture behind is any colour
CAPTION_OVER_CLS = ("absolute bottom-2 end-3 z-10 rounded-field bg-black/45 px-1.5 py-0.5 text-xs text-white/85 "
                    "[&_a]:text-white")


def figcaption_html(meta: dict) -> str:
    """Caption and credit together, the one line shown under an image."""
    from html import escape
    parts = [p for p in (escape(meta.get("caption") or ""), credit_html(meta)) if p]
    return " · ".join(parts)


def alt_text_for_url(url: str) -> str:
    """A post's cover image has no markdown syntax of its own to carry
    alt text the way a body image does (![alt text](url)) - this is its
    only source of one. Blank for anything without saved metadata, same
    as it's always rendered before this existed - no regression, just
    no worse than the status quo."""
    if not url:
        return ""
    filename = url.rsplit("/", 1)[-1]
    return get_meta(filename)["alt_text"]
