from pathlib import Path
import hashlib
import io
import logging
import json
import math
import os
import re
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

from soloblog import config
from soloblog.images import IMAGE_ERRORS

log = logging.getLogger(__name__)

# The web app manifest, the favicon and the icons phones use for "Add
# to home screen" (Settings > Appearance > Icons), made from one uploaded
# image: squared off from the centre and resized to each size needed.
# With nothing uploaded they're made for you: the site title's first
# letter on the theme's primary colour.

SIZES = (32, 180, 192, 512)


def source(s) -> str:
    """The upload the icons are made from - the app icon, else the
    favicon or the header icon if that's an upload - or "" for none."""
    for url in (s.get("app_icon_url", ""), s.get("favicon_url", ""), s.get("header_icon_url", "")):
        name = url[len("/uploads/"):]
        if url.startswith("/uploads/") and "/" not in name and os.path.exists(os.path.join(config.uploads_dir(), name)):
            return url
    return ""


@lru_cache(maxsize=16)
def _png(path: str, mtime: float, size: int) -> bytes:
    with Image.open(path) as img:
        img = img.convert("RGBA")
        side = min(img.size)
        left, top = (img.width - side) // 2, (img.height - side) // 2
        img = img.crop((left, top, left + side, top + side)).resize((size, size), Image.LANCZOS)
        out = io.BytesIO()
        img.save(out, "PNG", optimize=True)
        return out.getvalue()


def png(s, size: int):
    """The icon at size px as PNG bytes, or None for a size we don't make."""
    if size not in SIZES:
        return None
    url = source(s)
    if url:
        path = os.path.join(config.uploads_dir(), url[len("/uploads/"):])
        try:
            return _png(path, os.path.getmtime(path), size)
        except IMAGE_ERRORS as e:
            log.warning("couldn't use %s as the app icon: %s", url, e)
    background, ink = theme_colours(s.get("theme") or "light")
    return _letter_png(initial(s), background, ink, size)


def initial(s) -> str:
    """The first letter or digit of the site title."""
    m = re.search(r"\w", s.get("site_title") or "")
    return m.group(0).upper() if m else "S"


def version(s) -> str:
    """Changes whenever the icon would, so a browser doesn't keep an old one."""
    url = source(s)
    mtime = os.path.getmtime(os.path.join(config.uploads_dir(), url[len("/uploads/"):])) if url else 0
    key = f"{url}|{mtime}|{initial(s)}|{s.get('theme')}"
    return hashlib.sha1(key.encode(), usedforsecurity=False).hexdigest()[:8]


@lru_cache(maxsize=32)
def _letter_png(letter: str, background: tuple, ink: tuple, size: int) -> bytes:
    # drawn at 4x and scaled down, for smooth edges on the rounded square
    big = size * 4
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((0, 0, big - 1, big - 1), radius=int(big * 0.22), fill=background)
    font = ImageFont.load_default(size=int(big * 0.66))
    # the built-in font is a light weight - a stroke of its own colour
    # thickens it enough to read in a browser tab
    draw.text((big / 2, big / 2), letter, font=font, fill=ink, anchor="mm",
              stroke_width=max(1, int(big * 0.03)), stroke_fill=ink)
    img = img.resize((size, size), Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, "PNG", optimize=True)
    return out.getvalue()


def _srgb(value):
    """An oklch() colour from the theme as an (r, g, b) tuple."""
    m = re.match(r"oklch\(\s*([\d.]+)(%?)\s+([\d.]+)\s+([\d.]+)", value or "")
    if not m:
        return None
    L = float(m.group(1)) / (100 if m.group(2) else 1)
    C, H = float(m.group(3)), math.radians(float(m.group(4)))
    a, b = C * math.cos(H), C * math.sin(H)
    l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    linear = (4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
              -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
              -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_)
    gamma = [12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
             for c in (min(max(c, 0.0), 1.0) for c in linear)]
    return tuple(round(c * 255) for c in gamma)


def theme_colours(theme: str):
    """The theme's primary and primary-content, from the built stylesheet -
    daisyUI's own values, so the icon matches the buttons. A neutral pair
    if the stylesheet isn't there."""
    path = os.path.join("static", "css", "output.css")
    try:
        return _theme_colours(theme, os.path.getmtime(path))
    except OSError:
        return (55, 65, 81), (255, 255, 255)


@lru_cache(maxsize=64)
def _theme_colours(theme: str, mtime: float):
    css = Path(os.path.join("static", "css", "output.css")).read_text(encoding="utf-8")
    found = {}
    for m in re.finditer(r"([^{}]*)\{([^{}]*)\}", css):
        if re.search(r'\[data-theme="?' + re.escape(theme) + r'"?\]', m.group(1)) \
                and not m.group(1).strip().startswith("html"):
            found.update(re.findall(r"--color-(primary|primary-content):\s*([^;]+);", m.group(2)))
    background, ink = _srgb(found.get("primary")), _srgb(found.get("primary-content"))
    return (background or (55, 65, 81)), (ink or (255, 255, 255))


def manifest(s) -> str:
    data = {
        "name": s["site_title"],
        "short_name": (s.get("app_name") or s["site_title"])[:30],
        "description": s.get("tagline") or s.get("meta_description") or "",
        "start_url": "/",
        "scope": "/",
        "display": "minimal-ui",
    }
    v = version(s)
    data["icons"] = [{"src": f"/icon-{n}.png?v={v}", "sizes": f"{n}x{n}", "type": "image/png", "purpose": "any"}
                     for n in (192, 512)]
    return json.dumps(data, ensure_ascii=False)
