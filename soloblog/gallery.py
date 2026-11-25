from soloblog.actions import on_attrs, EL
import os
import re
from functools import lru_cache
from html import escape

from soloblog import config

# Image galleries in a post. Written as a fenced block, so a post stays a
# plain markdown file:
#
#   ```gallery masonry
#   /uploads/a.webp
#   /uploads/b.webp | An optional caption
#   ```
#
# The style after "gallery" is optional - without it the site's default
# (Settings > Appearance > Images) is used. Every image opens in the
# lightbox (LightboxDialog in ui, LIGHTBOX_JS in app.py).

STYLES = {
    "grid": "Grid — even squares",
    "masonry": "Masonry — columns, each image at its own height",
    "justified": "Justified — rows of equal height, edge to edge",
    "slider": "Slider — one image at a time, with arrows",
    "filmstrip": "Filmstrip — a row you scroll sideways",
}

# /uploads/ files, or an outside https image - nothing else is an image here
_SRC = re.compile(r"^(/uploads/[A-Za-z0-9._-]+|https://[^\s\"'<>]+)$")

CHEVRON_LEFT = ('<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" '
                'stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" '
                'd="M15.75 19.5 8.25 12l7.5-7.5" /></svg>')
CHEVRON_RIGHT = ('<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" '
                 'stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" '
                 'd="m8.25 4.5 7.5 7.5-7.5 7.5" /></svg>')


def parse(lines: str) -> list:
    """[(src, caption)] from a gallery block's lines - src first, then
    an optional "| caption". Anything that isn't an image is skipped."""
    items = []
    for line in lines.splitlines():
        src, _, caption = line.partition("|")
        src = src.strip()
        if _SRC.match(src):
            items.append((src, caption.strip()))
    return items


@lru_cache(maxsize=512)
def _ratio(path: str, mtime: float) -> float:
    from PIL import Image
    from soloblog.images import IMAGE_ERRORS
    try:
        with Image.open(path) as img:
            w, h = img.size
            return w / h if h else 1.5
    except IMAGE_ERRORS:
        return 1.5


def ratio(src: str) -> float:
    """Width / height, for the justified layout - read from the file for
    our own uploads, a typical 3:2 for anything else."""
    if not src.startswith("/uploads/"):
        return 1.5
    path = os.path.join(config.uploads_dir(), src[len("/uploads/"):])
    try:
        return _ratio(path, os.path.getmtime(path))
    except OSError:
        return 1.5


def _caption(src: str, caption: str) -> str:
    """The line the lightbox shows: this gallery's own caption if it has
    one, else the media library's, plus the photo credit either way."""
    from soloblog import images
    meta = images.meta_for_url(src)
    if caption:
        meta = {**meta, "caption": caption}
    return images.figcaption_html(meta)


def _alt(src: str, caption: str) -> str:
    from soloblog import images
    return images.meta_for_url(src)["alt_text"] or caption


PAUSE_SVG = ('<svg data-icon="pause" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" '
             'aria-hidden="true"><rect x="6" y="5" width="4" height="14" rx="1"/><rect x="14" y="5" width="4" '
             'height="14" rx="1"/></svg>')
PLAY_SVG = ('<svg data-icon="play" class="hidden" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" '
            'aria-hidden="true"><path d="M8 5.5v13a1 1 0 0 0 1.5.86l11-6.5a1 1 0 0 0 0-1.72l-11-6.5A1 1 0 0 0 8 5.5Z"/></svg>')
# how wide a gallery's pictures show in the column - a wide or full
# section gives them its own width (pages._wider_sizes)
SLIDER_SIZES = "(min-width: 768px) 48rem, 100vw"
TILE_SIZES = "(min-width: 640px) 16rem, 50vw"
# a justified row's pictures grow to fill it, a phone's one to a row - the
# browsers that can measure a lazy picture (auto) do, the rest go by the width
JUSTIFIED_SIZES = "auto, (min-width: 640px) 24rem, 100vw"


def render(style: str, items: list, gallery_id: str, auto: bool = False) -> str:
    """The gallery's html. Every image is a link to its full file (so it
    still works with no JavaScript) that LIGHTBOX_JS opens in the
    lightbox instead. auto: a slider moves along by itself."""
    style = style if style in STYLES else "grid"
    if not items:
        return ""

    from soloblog import i18n, images
    # how wide one image shows, per style - the browser picks the
    # smallest copy (images.srcset) that's still sharp at that width
    shown = {"grid": TILE_SIZES, "masonry": TILE_SIZES, "justified": JUSTIFIED_SIZES, "filmstrip": "24rem",
             "slider": SLIDER_SIZES}[style]

    def title(src, caption):
        """Its caption, as words - the gallery's own, or the media library's."""
        return caption or images.meta_for_url(src).get("caption") or ""

    # the same thin edge and soft shadow as a page's framed pictures
    edge = "border border-base-content/10 shadow-lg"

    def link(src, caption, cls, img_cls, style_attr="", overlay=True):
        options = images.srcset(src)
        sized = f' srcset="{escape(options)}" sizes="{shown}"' if options else ""
        named = title(src, caption)
        # its caption over its foot, as the lightbox shows it: on a pointer's
        # hover, and always on a phone, where there's no hovering
        over = (f'<span class="pointer-events-none absolute inset-x-0 bottom-0 rounded-b-box px-3 pb-2 pt-8 '
                f'text-xs text-white text-left bg-linear-to-t from-black/75 to-transparent opacity-0 '
                f'transition-opacity group-hover:opacity-100 pointer-coarse:opacity-100 line-clamp-2">'
                f'{escape(named)}</span>') if named and overlay else ""
        # the link itself is the full-size original, for the lightbox
        return (f'<a href="{escape(src)}" class="gallery-item group relative {cls}" data-lightbox="{gallery_id}" '
                f'data-caption="{escape(_caption(src, caption))}" data-title="{escape(named)}"{style_attr}>'
                f'<img src="{escape(src)}"{sized} alt="{escape(_alt(src, caption))}" loading="lazy" '
                f'class="{img_cls}">{over}</a>')

    if style == "grid":
        inner = "".join(link(s, c, "block", f"w-full aspect-square object-cover rounded-box hover:opacity-90 {edge}")
                        for s, c in items)
        body = f'<div class="grid grid-cols-2 sm:grid-cols-3 gap-2">{inner}</div>'
    elif style == "masonry":
        inner = "".join(link(s, c, "block mb-2 break-inside-avoid", f"w-full h-auto rounded-box hover:opacity-90 {edge}")
                        for s, c in items)
        body = f'<div class="columns-2 sm:columns-3 gap-2">{inner}</div>'
    elif style == "justified":
        # each item grows in proportion to its own shape, so every row
        # comes out the same height and fills the width exactly
        inner = "".join(link(s, c, "block", f"w-full h-40 sm:h-48 object-cover rounded-box hover:opacity-90 {edge}",
                             f' style="flex: {ratio(s):.3f} 1 {ratio(s) * 10:.1f}rem"')
                        for s, c in items)
        body = f'<div class="flex flex-wrap gap-2">{inner}</div>'
    elif style == "filmstrip":
        inner = "".join(link(s, c, "carousel-item", f"h-40 sm:h-56 w-auto rounded-box hover:opacity-90 {edge}")
                        for s, c in items)
        # room below for the pictures' shadows, which a scrolling row cuts off.
        # The slider's arrows too - a sideways row gave no hint it scrolls,
        # nor a way to without a trackpad; each hides at its own end
        body = (f'<div class="gallery-slider relative">'
                f'<div class="carousel carousel-start w-full gap-2 rounded-box pb-4 px-1" '
                f'{on_attrs("scroll", "syncSlider", EL)}>{inner}</div>'
                f'<button type="button" class="btn btn-circle btn-sm absolute left-2 top-1/2 -translate-y-1/2" '
                f'aria-label="Previous images" {on_attrs("click", "slideGallery", EL, -1)}>{CHEVRON_LEFT}</button>'
                f'<button type="button" class="btn btn-circle btn-sm absolute right-2 top-1/2 -translate-y-1/2" '
                f'aria-label="Next images" {on_attrs("click", "slideGallery", EL, 1)}>{CHEVRON_RIGHT}</button>'
                f'</div>')
    else:  # slider - daisyUI's carousel, one image across, our own arrows and counter
        # each filling the frame, as a cover does - a picture of another
        # shape had bars beside or above it; the lightbox shows it whole.
        # One shape at every width, a photo's own 3:2: a fixed height cut
        # a wide band's pictures to a strip, and a phone's to nearly square
        slides = "".join(link(s, c, "carousel-item w-full", "w-full aspect-[3/2] object-cover", overlay=False)
                         for s, c in items)
        count = len(items)
        # every slide named (a caption each, a dozen at most): the names in a
        # row above, to pick one - the start of each caption, to its comma
        names = ""
        if 1 < count <= 12 and all(c for _, c in items):
            # one row you swipe along where they don't all fit, as a phone's toolbars are
            names = ('<div class="overflow-x-auto mb-4 [scrollbar-width:none]" data-slider-names>'
                     '<div class="flex gap-2 w-max mx-auto">' + "".join(
                f'<button type="button" aria-pressed="{"true" if i == 0 else "false"}" '
                f'class="btn btn-sm rounded-full {"btn-soft btn-primary" if i == 0 else "btn-ghost"}" '
                f'{on_attrs("click", "showSlide", EL, i)}>{escape(re.split(r",| - | — ", c)[0].strip())}</button>'
                for i, (_, c) in enumerate(items)) + '</div></div>')
        body = (f'{names}<div class="gallery-slider relative">'
                f'<div class="carousel w-full rounded-box border border-base-content/10 shadow-xl" '
                f'{on_attrs("scroll", "syncSlider", EL)}>{slides}</div>'
                f'<button type="button" class="btn btn-circle btn-sm absolute left-2 top-1/2 -translate-y-1/2" '
                f'aria-label="Previous image" {on_attrs("click", "slideGallery", EL, -1)}>{CHEVRON_LEFT}</button>'
                f'<button type="button" class="btn btn-circle btn-sm absolute right-2 top-1/2 -translate-y-1/2" '
                f'aria-label="Next image" {on_attrs("click", "slideGallery", EL, 1)}>{CHEVRON_RIGHT}</button>'
                f'</div>'
                # under it, not over the picture: the slide's caption, the count -
                # and, when it moves by itself, a button to stop it
                f'<div class="flex items-center gap-3 mt-3 min-h-8">'
                f'<p class="slider-caption flex-1 min-w-0 truncate text-sm text-base-content/70">'
                f'{escape(title(*items[0]))}</p>'
                + (f'<button type="button" class="btn btn-ghost btn-sm btn-square" data-slider-pause '
                   f'aria-label="{escape(i18n.t("Pause"))}">{PAUSE_SVG}{PLAY_SVG}</button>' if auto else "")
                + f'<span class="slider-count text-xs tabular-nums text-base-content/60">1 / {count}</span></div>')
        if auto:
            body = body.replace('<div class="gallery-slider relative">', '<div class="gallery-slider relative" data-autoplay>', 1)
    return f'<div class="gallery gallery-{style} not-prose my-6" data-gallery="{gallery_id}">{body}</div>'
