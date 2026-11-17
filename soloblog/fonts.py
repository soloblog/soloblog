from fasthtml.common import NotStr, Style

# Settings > Appearance > Fonts: the text and heading typefaces, as font
# stacks of fonts already on readers' devices (modernfontstacks.com) - no
# web font downloads, so nothing to wait for and nothing sent to a font
# service. "" keeps the theme's own.

# name: (label, stack)
STACKS = {
    "transitional": ("Transitional serif - Charter, Cambria",
                     "Charter, 'Bitstream Charter', 'Sitka Text', Cambria, serif"),
    "old-style": ("Old-style serif - Iowan, Palatino",
                  "'Iowan Old Style', 'Palatino Linotype', 'URW Palladio L', P052, serif"),
    "humanist": ("Humanist sans - Seravek, Gill Sans, Calibri",
                 "Seravek, 'Gill Sans Nova', Ubuntu, Calibri, 'DejaVu Sans', source-sans-pro, sans-serif"),
    "geometric": ("Geometric sans - Avenir, Montserrat",
                  "Avenir, Montserrat, Corbel, 'URW Gothic', source-sans-pro, sans-serif"),
    "neo-grotesque": ("Neo-grotesque - Inter, Roboto, Helvetica",
                      "Inter, Roboto, 'Helvetica Neue', 'Arial Nova', 'Nimbus Sans', Arial, sans-serif"),
    "rounded": ("Rounded - Quicksand, Arial Rounded",
                "ui-rounded, 'Hiragino Maru Gothic ProN', Quicksand, Comfortaa, Manjari, 'Arial Rounded MT', "
                "'Arial Rounded MT Bold', Calibri, source-sans-pro, sans-serif"),
    "slab": ("Slab serif - Rockwell, Roboto Slab",
             "Rockwell, 'Rockwell Nova', 'Roboto Slab', 'DejaVu Serif', 'Sitka Small', serif"),
    "monospace": ("Monospace - Cascadia, Menlo, Consolas",
                  "ui-monospace, 'Cascadia Code', 'Source Code Pro', Menlo, Consolas, 'DejaVu Sans Mono', monospace"),
    "system": ("System UI - the device's own",
               "system-ui, sans-serif"),
    "classical-humanist": ("Classical humanist - Optima, Candara",
                           "Optima, Candara, 'Noto Sans', source-sans-pro, sans-serif"),
    "industrial": ("Industrial - Bahnschrift, DIN",
                   "Bahnschrift, 'DIN Alternate', 'Franklin Gothic Medium', 'Nimbus Sans Narrow', sans-serif-condensed, "
                   "sans-serif"),
    "antique": ("Antique - Bookman, Georgia",
                "Superclarendon, 'Bookman Old Style', 'URW Bookman', 'URW Bookman L', 'Georgia Pro', Georgia, serif"),
    "didone": ("Didone - Didot, Bodoni",
               "Didot, 'Bodoni MT', 'Noto Serif Display', 'URW Palladio L', P052, Sylfaen, serif"),
    "monospace-slab": ("Monospace slab - Courier",
                       "'Nimbus Mono PS', 'Courier New', monospace"),
    "handwritten": ("Handwritten - Segoe Print, Bradley Hand",
                    "'Segoe Print', 'Bradley Hand', Chilanka, TSCu_Comic, casual, cursive"),
}

# how the picker groups them
GROUPS = (("Serif", ("transitional", "old-style", "antique", "didone", "slab")),
          ("Sans-serif", ("system", "neo-grotesque", "humanist", "classical-humanist", "geometric", "rounded",
                          "industrial")),
          ("Other", ("monospace", "monospace-slab", "handwritten")))


# What a font looks like it's set at is the height of its small letters,
# not its size: Charter or Palatino at 16px read a size smaller than the
# system font beside it (x-height 0.46 against 0.54). font-size-adjust
# sizes every stack to this x-height - the system fonts' own, 0.50-0.54 -
# so whichever is chosen reads the same size as the default.
X_HEIGHT = 0.53


# the admin is a tool and keeps its own font - only the editor's preview
# shows the site's, so it looks as the post will
PREVIEW = (".editor-preview", ".editor-preview-side")


def style(s, admin=False):
    """The <style> that applies the chosen fonts, or None for the theme's own."""
    body, heads = STACKS.get(s.get("font_body") or ""), STACKS.get(s.get("font_headings") or "")
    headings = ("h1", "h2", "h3", "h4", ".card-title")
    within = PREVIEW if admin else ("",)
    css = ""
    if body:
        css += f"{', '.join(PREVIEW) if admin else 'body'} {{ font-family: {body[1]}; font-size-adjust: {X_HEIGHT}; }}\n"
    if heads:
        targets = ", ".join(f"{scope} {h}".strip() for scope in within for h in headings)
        css += f"{targets} {{ font-family: {heads[1]}; font-size-adjust: {X_HEIGHT}; }}\n"
    return Style(NotStr(css)) if css else None
