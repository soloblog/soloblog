"""Soloblog's brand files, concept B (the dot), in #605DFF.

The wordmark is Sora SemiBold (SIL Open Font License) turned into
outlines, so it looks the same everywhere without the font: a browser
page loads Sora from Google Fonts and opentype.js from cdnjs, lays the
letters out, and hands back the shapes. The "o" is a filled circle the
exact size and place of Sora's own o. PNGs are the SVGs rendered by the
same browser. Needs Playwright and an internet connection:

    python tools/brand.py              # into docs/brand
    python tools/brand.py some-folder  # somewhere else, to compare
"""
import os
import sys
import tempfile

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "docs", "brand")
os.makedirs(OUT, exist_ok=True)

ACCENT = "#605DFF"
INK = "#16161A"        # on light backgrounds, and the app icon's square
INK_DARK = "#ECEAE6"   # on dark backgrounds
PAPER = "#FAF8F5"
PAPER_DARK = "#17191E"
S_STROKE = "M41 22c-3-5-19-5-19 3 0 8 20 5 20 14 0 9-17 9-22 3"

# an old browser's user agent: Google Fonts then serves TTF, which
# opentype.js reads (it can't read WOFF2)
OLD_UA = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/534.30 (KHTML, like Gecko) Safari/534.30"

LAYOUT_JS = r"""
async ([text, size, tracking]) => {
  const css = await (await fetch('https://fonts.googleapis.com/css2?family=Sora:wght@600')).text();
  // the plain latin subset - the file listed first is latin-ext, without a-z
  const url = css.split('/* latin */')[1].match(/url\((https:[^)]+)\)/)[1];
  const font = opentype.parse(await (await fetch(url)).arrayBuffer());
  const scale = size / font.unitsPerEm;
  let x = 0, parts = [], prev = null, top = 0, bottom = 0, dotted = false;
  for (const ch of text) {
    const g = font.charToGlyph(ch);
    if (g.name === '.notdef') throw new Error('no glyph for ' + ch);
    if (prev) x += font.getKerningValue(prev, g) * scale;
    if (ch === 'o' && !dotted) {
      dotted = true;
      // the first o is the dot: where Sora's o sits, as big as the o
      const b = g.getBoundingBox();
      // a solid disc looks bigger than an outlined o of the same size
      const r = (b.y2 - b.y1) * scale / 2 * 0.86;
      parts.push({dot: true, cx: x + (b.x1 + b.x2) / 2 * scale, cy: -(b.y1 + b.y2) / 2 * scale, r});
    } else {
      parts.push({d: g.getPath(x, 0, size).toPathData(2)});
    }
    const b = g.getBoundingBox();
    top = Math.max(top, b.y2 * scale); bottom = Math.min(bottom, b.y1 * scale);
    x += g.advanceWidth * scale + tracking * size;
    prev = g;
  }
  const last = font.charToGlyph(text[text.length - 1]);
  const width = x - tracking * size - (last.advanceWidth - last.getBoundingBox().x2) * scale;
  const first = font.charToGlyph(text[0]).getBoundingBox().x1 * scale;
  return {parts, left: first, width: width - first, top, bottom, font: font.names.fullName.en};
}
"""


def write(name, text):
    with open(os.path.join(OUT, name), "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def icon_svg(size=None):
    dims = f' width="{size}" height="{size}"' if size else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"{dims} role="img" aria-label="Soloblog">'
            f'<rect width="64" height="64" rx="14" fill="{INK}"/>'
            f'<path d="{S_STROKE}" fill="none" stroke="#FFFFFF" stroke-width="6" stroke-linecap="round"/>'
            f'<circle cx="46" cy="47" r="5" fill="{ACCENT}"/></svg>\n')


def mark_svg(ink):
    # the S and the dot with no square, for beside the name or on a page
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="14 14 38 40" role="img" aria-label="Soloblog">'
            f'<path d="{S_STROKE}" fill="none" stroke="{ink}" stroke-width="6" stroke-linecap="round"/>'
            f'<circle cx="46" cy="47" r="5" fill="{ACCENT}"/></svg>\n')


def wordmark_svg(layout, ink, pad=2):
    x0, w = layout["left"] - pad, layout["width"] + 2 * pad
    y0, h = -layout["top"] - pad, layout["top"] - layout["bottom"] + 2 * pad
    body = "".join(
        f'<circle cx="{p["cx"]:.2f}" cy="{p["cy"]:.2f}" r="{p["r"]:.2f}" fill="{ACCENT}"/>' if p.get("dot")
        else f'<path d="{p["d"]}"/>' for p in layout["parts"])
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0:.2f} {y0:.2f} {w:.2f} {h:.2f}" '
            f'role="img" aria-label="Soloblog"><g fill="{ink}">{body}</g></svg>\n')


def social_html(wordmark):
    # GitHub's social preview and the website's share image: 1280 x 640
    return f"""<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Sora:wght@400&display=block">
<style>html,body{{margin:0}}body{{width:1280px;height:640px;background:{PAPER};display:flex;align-items:center;
justify-content:center;font-family:Sora,sans-serif}}.box{{display:flex;flex-direction:column;align-items:center;gap:40px}}
.row{{display:flex;align-items:center;gap:44px}}.row svg:first-child{{width:168px;height:168px}}
.row svg:last-child{{height:104px;width:auto}}p{{margin:0;font-size:38px;color:#5F5F68;letter-spacing:-0.01em}}</style>
</head><body><div class="box"><div class="row">{icon_svg()}{wordmark}</div>
<p>Your own blog and website. Yours to keep.</p></div></body></html>"""


with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge")
    page = browser.new_context(user_agent=OLD_UA).new_page()
    page.goto("about:blank")
    page.add_script_tag(url="https://cdnjs.cloudflare.com/ajax/libs/opentype.js/1.3.4/opentype.min.js")
    layout = page.evaluate(LAYOUT_JS, ["soloblog", 100, -0.02])
    print("font:", layout["font"], "| width", round(layout["width"]), "| dot r", round(
        [q for q in layout["parts"] if q.get("dot")][0]["r"], 1))

    write("soloblog-icon.svg", icon_svg())
    write("soloblog-mark.svg", mark_svg(INK))
    write("soloblog-mark-dark.svg", mark_svg(INK_DARK))
    write("soloblog-wordmark.svg", wordmark_svg(layout, INK))
    write("soloblog-wordmark-dark.svg", wordmark_svg(layout, INK_DARK))

    shot = browser.new_context(device_scale_factor=1).new_page()
    for size in (512, 180, 32):
        shot.set_viewport_size({"width": size, "height": size})
        shot.set_content(f'<html><body style="margin:0;background:transparent">{icon_svg(size)}</body></html>')
        shot.screenshot(path=os.path.join(OUT, f"soloblog-icon-{size}.png"), omit_background=True)
    shot.set_viewport_size({"width": 1280, "height": 640})
    shot.set_content(social_html(wordmark_svg(layout, INK)), wait_until="networkidle")
    shot.evaluate("document.fonts.ready")
    shot.screenshot(path=os.path.join(OUT, "soloblog-social.png"))
    # a look at everything, light and dark - kept out of the folder
    sheet = "".join(
        f'<div style="background:{bg};padding:40px;display:flex;align-items:center;gap:32px">'
        f'<img src="{OUT}/soloblog-icon.svg" height="96"><img src="{OUT}/soloblog-mark{sfx}.svg" height="80">'
        f'<img src="{OUT}/soloblog-wordmark{sfx}.svg" height="56"></div>'
        for bg, sfx in ((PAPER, ""), ("#FFFFFF", ""), (PAPER_DARK, "-dark"), ("#1D232A", "-dark")))
    sheet_png = os.path.join(tempfile.gettempdir(), "soloblog-brand-sheet.png")
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(f'<html><body style="margin:0">{sheet}</body></html>')
    shot.set_viewport_size({"width": 900, "height": 700})
    shot.goto("file:///" + f.name.replace("\\", "/"))
    shot.screenshot(path=sheet_png, full_page=True)
    os.remove(f.name)
    browser.close()
print("written:", sorted(os.listdir(OUT)))
print("all of them together:", sheet_png)
