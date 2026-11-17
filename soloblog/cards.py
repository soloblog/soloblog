"""Share cards: the picture a link shows when it's shared - on social
media, in a chat - for a post with no image of its own, and for the
site's other pages. The post's title on the site's light palette, the
site's name above it and its address below, drawn here with Pillow in
Noto Sans (fonts/, SIL Open Font License) and kept on disk until the
words or the palette change.

Noto Sans draws Latin, Greek and Cyrillic. A title in another script
(Chinese, Arabic, Hindi...) gets no card - the page falls back to the
site's share image - rather than a row of empty boxes."""
import hashlib
import io
import os
import unicodedata
from functools import lru_cache
from urllib.parse import urlparse

from PIL import Image, ImageDraw, ImageFont

from soloblog import config, settings, themes

FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
WIDTH, HEIGHT, MARGIN = 1200, 630, 80
# part of every card's name - change it when the design changes, so
# cached cards (here, and at the sites they were shared on) are redrawn
DESIGN = "2"
# when the palette's colours can't be read (the CSS hasn't been built)
FALLBACK = {"base-100": (255, 255, 255), "base-content": (24, 24, 27), "primary": (96, 93, 255)}


def cards_dir() -> str:
    return os.path.join(config.data_dir(), "cards")


@lru_cache(maxsize=16)
def _font(bold: bool, size: int):
    return ImageFont.truetype(os.path.join(FONTS, "NotoSans-Bold.ttf" if bold else "NotoSans-Regular.ttf"), size)


@lru_cache(maxsize=4096)
def _has_glyph(ch: str) -> bool:
    # a character the font doesn't have draws as its "missing" box - the
    # same shape as a private-use character, which no font draws
    font = _font(True, 40)
    return bytes(font.getmask(ch)) != bytes(font.getmask(""))


def _drawable(text: str) -> str | None:
    """The text, emoji and the like dropped, if the font can draw the
    rest of it; None if it can't (another script)."""
    kept = []
    for ch in text:
        if ch.isspace() or _has_glyph(ch):
            kept.append(ch)
        elif not unicodedata.category(ch).startswith("S"):  # a letter it hasn't got
            return None
    text = " ".join("".join(kept).split())
    return text or None


def _colours() -> dict:
    found = themes.theme_rgb(settings.get("theme") or "light")
    c = {k: found.get(k) or FALLBACK.get(k) for k in ("base-100", "base-content", "primary")}
    c["primary"] = found.get("tx-primary") or c["primary"]  # as text, the readable one
    c["fill"] = found.get("primary") or FALLBACK["primary"]
    # quieter text: the text colour, two thirds of the way over the page
    c["muted"] = tuple(round(t * 0.62 + b * 0.38) for t, b in zip(c["base-content"], c["base-100"]))
    return c


def _site_bits():
    s = settings.get_all()
    return s["site_title"] or config.SITE_TITLE, urlparse(config.BASE_URL).netloc or ""


def _wrap(draw, text, font, width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def _title_lines(draw, title, width, max_lines, largest=76):
    """The biggest size, from `largest` down, at which the title fits; at
    the smallest, it's cut short with an ellipsis."""
    for size in range(largest, 46, -4):
        font = _font(True, size)
        lines = _wrap(draw, title, font, width)
        if len(lines) <= max_lines and all(draw.textlength(ln, font=font) <= width for ln in lines):
            return font, lines
    lines = lines[:max_lines]
    while lines and draw.textlength(lines[-1] + "…", font=font) > width:
        lines[-1] = lines[-1].rsplit(" ", 1)[0] if " " in lines[-1] else lines[-1][:-1]
    lines[-1] += "…"
    return font, lines


def _draw(kicker: str, title: str, subtitle: str, footer: str) -> bytes:
    c = _colours()
    img = Image.new("RGB", (WIDTH, HEIGHT), c["base-100"])
    draw = ImageDraw.Draw(img)
    width = WIDTH - 2 * MARGIN
    # a post's card: its site's name, then the title, from the top. The
    # site's own: its name and tagline, larger, in the middle.
    font, lines = _title_lines(draw, title, width, 3 if subtitle else 4, 76 if kicker else 96)
    step = round(font.size * 1.18)
    sub_font = _font(False, 36)
    subs = _wrap(draw, subtitle, sub_font, width)[:2] if subtitle else []
    if kicker:
        y = MARGIN
        draw.text((MARGIN, y), kicker, font=_font(True, 30), fill=c["primary"])
        y += 70
    else:
        y = (HEIGHT - 14 - (step * len(lines) + 52 * len(subs))) // 2 - 20
    for line in lines:
        draw.text((MARGIN, y), line, font=font, fill=c["base-content"])
        y += step
    for line in subs:
        y += 8
        draw.text((MARGIN, y), line, font=sub_font, fill=c["muted"])
        y += 44
    if footer:
        draw.text((MARGIN, HEIGHT - MARGIN - 34), footer, font=_font(False, 28), fill=c["muted"])
    # the palette's own colour along the foot
    draw.rectangle((0, HEIGHT - 14, WIDTH, HEIGHT), fill=c["fill"])
    out = io.BytesIO()
    img.save(out, "PNG", optimize=True)
    return out.getvalue()


def _card(name: str, parts) -> tuple[str, bytes]:
    """(its key, the PNG) - drawn once and kept in cards/<name>-<key>.png;
    an older card for the same name is removed when a new one is drawn."""
    key = hashlib.sha1("\0".join((DESIGN, settings.get("theme") or "light", *parts)).encode(), usedforsecurity=False).hexdigest()[:12]
    folder = cards_dir()
    path = os.path.join(folder, f"{name}-{key}.png")
    if os.path.exists(path):
        with open(path, "rb") as f:
            return key, f.read()
    png = _draw(*parts)
    os.makedirs(folder, exist_ok=True)
    for old in os.listdir(folder):
        if old.startswith(name + "-") and old[len(name) + 1:-4].isalnum() and len(old) == len(name) + 17:
            os.remove(os.path.join(folder, old))
    with open(path, "wb") as f:
        f.write(png)
    return key, png


def _post_parts(row):
    title = _drawable(row["title"] or "")
    if not title:
        return None
    site, domain = _site_bits()
    author = settings.get("author_name") or ""
    kicker = _drawable(site) or ""
    footer = " · ".join(x for x in (_drawable(author) if author != site else "", domain) if x)
    return kicker, title, "", footer


def _site_parts():
    site, domain = _site_bits()
    title = _drawable(site)
    if not title:
        return None
    return "", title, _drawable(settings.get("tagline") or "") or "", domain


def post_card(row) -> bytes | None:
    parts = _post_parts(row)
    return _card(row["slug"], parts)[1] if parts else None


def site_card() -> bytes | None:
    parts = _site_parts()
    return _card("_site", parts)[1] if parts else None


def post_card_url(row) -> str | None:
    """The card's address, its key in it so a changed title is fetched
    afresh - None when the title can't be drawn."""
    parts = _post_parts(row)
    return f"/card/{row['slug']}.png?v={_card(row['slug'], parts)[0]}" if parts else None


def site_card_url() -> str | None:
    parts = _site_parts()
    return f"/card.png?v={_card('_site', parts)[0]}" if parts else None
