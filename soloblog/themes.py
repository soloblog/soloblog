from pathlib import Path
import math
import os
import re
from functools import lru_cache

# every theme daisyUI v5 ships (@plugin "daisyui" { themes: all; } in
# static/css/input.css is what actually bakes these into output.css -
# this list just drives the admin's swatch picker)
DAISYUI_THEMES = [
    "light", "dark", "cupcake", "bumblebee", "emerald", "corporate",
    "synthwave", "retro", "cyberpunk", "valentine", "halloween",
    "garden", "forest", "aqua", "lofi", "pastel", "fantasy", "wireframe",
    "black", "luxury", "dracula", "cmyk", "autumn", "business", "acid",
    "lemonade", "night", "coffee", "winter", "dim", "nord", "sunset",
    "caramellatte", "abyss", "silk",
]
# the ones with a dark color-scheme - the choices for "Dark mode"
# (Settings > Appearance), the theme a device in dark mode gets
# the rest - the choices for the light theme
def _light():
    return [t for t in DAISYUI_THEMES if t not in DARK_THEMES]


DARK_THEMES = ["dark", "synthwave", "halloween", "forest", "aqua", "black", "luxury", "dracula", "business",
               "night", "coffee", "dim", "sunset", "abyss"]
LIGHT_THEMES = _light()

# light and dark themes that go together - one click picks both
# (Settings > Appearance, the welcome's Pick a look). Each pair has the
# same corner rounding on buttons and cards (--radius-field and
# --radius-box), not just colours that suit - switching to dark mode
# shouldn't reshape the page. Mono is the one near miss: no dark grey
# palette has wireframe's slight rounding, and black's square corners
# are the closest.
THEME_PAIRS = [("Classic", "light", "dark"), ("Nord", "nord", "abyss"), ("Rose", "garden", "dracula"),
               ("Mint", "cupcake", "forest"), ("Office", "corporate", "business"),
               ("Garden", "emerald", "dim"), ("Café", "caramellatte", "coffee"), ("Winter", "winter", "night"),
               ("Mono", "wireframe", "black"), ("Autumn", "autumn", "sunset"), ("Silk", "silk", "luxury"),
               ("Fantasy", "fantasy", "synthwave")]

# which of the two visitors see
THEME_MODES = [("auto", "Match each visitor's device - light, or dark when it's in dark mode"),
               ("light", "Always the light palette"), ("dark", "Always the dark palette")]


def theme_choice(s) -> tuple[str, str, str]:
    """(light, dark, mode) as the pickers show them. A site from before
    the pickers keeps its look: one theme and no dark one is "always
    light"; a dark theme as its only theme is "always dark"."""
    theme, dark, mode = s.get("theme") or "light", s.get("theme_dark") or "", s.get("theme_mode") or "auto"
    if is_dark(theme, s if "own_themes" in s else None):
        return "light", theme, "dark"
    if not dark:
        return theme, "dark", "light"
    return theme, dark, mode if mode in dict(THEME_MODES) else "auto"


# ---- the palettes' colours, as the built CSS has them (daisyUI's own
# values) - for what isn't CSS: share cards (cards.py), and
# tools/theme_contrast.py. oklch -> oklab -> linear sRGB.

def parse_oklch(value):
    m = re.match(r"oklch\(\s*([\d.]+)(%?)\s+([\d.]+)\s+([\d.]+)", value or "")
    if not m:
        return None
    L = float(m.group(1)) / (100 if m.group(2) else 1)
    C, H = float(m.group(3)), math.radians(float(m.group(4)))
    return (L, C * math.cos(H), C * math.sin(H))  # oklab


def linear_srgb(lab):
    L, a, b = lab
    l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    rgb = (4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
           -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
           -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_)
    return tuple(min(max(c, 0.0), 1.0) for c in rgb)


def _gamma(c):
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def theme_colours(css, name):
    out = {}
    for m in re.finditer(r"([^{}]*)\{([^{}]*)\}", css):
        selector, body = m.group(1), m.group(2)
        if selector.strip().startswith("html"):  # our own overrides, from an earlier run
            continue
        if re.search(r'\[data-theme="?' + re.escape(name) + r'"?\]', selector):
            for key, value in re.findall(r"--color-([a-z0-9-]+):\s*([^;]+);", body):
                out[key] = value.strip()
    return out


def theme_rgb(name: str) -> dict:
    """A palette's colours as 0-255 sRGB, by daisyUI's names (base-100,
    base-content, primary...) and the readable text ones (tx-primary...) -
    your own from what's saved, daisyUI's from the built CSS."""
    if name.startswith(OWN_PREFIX):
        theme = next((t for t in own_themes() if t["key"] == name), None)
        if not theme:
            return _built_in_rgb("light")
        colours = {k[8:]: v for k, v in theme["values"].items() if k.startswith("--color-")}
        colours.update({"tx-" + k: v for line in theme["readable"]
                        for k, v in re.findall(r"--tx-([a-z0-9-]+):\s*([^;]+);", line)})
        return {k: tuple(round(_gamma(c) * 255) for c in linear_srgb(lab))
                for k, v in colours.items() if (lab := parse_oklch(v))}
    return _built_in_rgb(name)


@lru_cache(maxsize=64)
def _built_in_rgb(name: str) -> dict:
    """Empty if the CSS hasn't been built."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = {}
    try:
        built = Path(os.path.join(root, "static", "css", "output.css")).read_text(encoding="utf-8")
        readable = Path(os.path.join(root, "static", "css", "contrast.css")).read_text(encoding="utf-8")
    except OSError:
        return out
    colours = theme_colours(built, name)
    for m in re.finditer(r'html\[data-theme="' + re.escape(name) + r'"\]\s*\{([^}]*)\}', readable):
        colours.update({"tx-" + k: v.strip() for k, v in re.findall(r"--tx-([a-z0-9-]+):\s*([^;]+);", m.group(1))})
    for key, value in colours.items():
        lab = parse_oklch(value)
        if lab:
            out[key] = tuple(round(_gamma(c) * 255) for c in linear_srgb(lab))
    return out


# ---- readable text in any palette (tools/theme_contrast.py writes the
# built-in themes' into contrast.css; your own get theirs when saved)

# 4.5:1 is WCAG AA for text; a little over it, so rounding the written
# colours can't land them just under
NEEDED = 4.6
TEXT_COLOURS = ("primary", "secondary", "accent", "info", "success", "warning", "error")
FILLS = ("primary", "secondary", "accent", "neutral", "info", "success", "warning", "error")
MUTED = (40, 50, 60, 70)
# how far selected text has to stand out from the page (contrast of the
# two backgrounds) - where halloween's 15% of primary already looked right
SELECTION_SEEN = 1.6


# ---- colour maths: oklch <-> oklab <-> linear sRGB, and WCAG contrast

def to_oklch_css(lab):
    L, a, b = lab
    C = math.hypot(a, b)
    H = math.degrees(math.atan2(b, a)) % 360
    return f"oklch({L * 100:.2f}% {C:.4f} {H:.2f})"


def _ungamma(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def over(fg_lin, bg_lin, alpha):
    """fg at alpha over bg, composited in gamma sRGB as browsers do."""
    return tuple(_ungamma(alpha * _gamma(f) + (1 - alpha) * _gamma(b)) for f, b in zip(fg_lin, bg_lin))


def contrast(a_lin, b_lin):
    la = 0.2126 * a_lin[0] + 0.7152 * a_lin[1] + 0.0722 * a_lin[2]
    lb = 0.2126 * b_lin[0] + 0.7152 * b_lin[1] + 0.0722 * b_lin[2]
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def lab_mix(a, b, t):
    """t of a, the rest b - color-mix(in oklab, a t, b)."""
    return tuple(t * x + (1 - t) * y for x, y in zip(a, b))


def most_of(colour, towards, backgrounds):
    """The largest share of colour (moved towards `towards`) that still
    reads at NEEDED on every background. 1.0 when it already does."""
    def ok(t):
        c = linear_srgb(lab_mix(colour, towards, t))
        return all(contrast(c, linear_srgb(bg)) >= NEEDED for bg in backgrounds)
    if ok(1.0):
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(30):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if ok(mid) else (lo, mid)
    return lo


# ---- the themes, as the built CSS has them (daisyUI's own values)

def overrides(colours):
    base = parse_oklch(colours["base-content"])
    backgrounds = [parse_oklch(colours["base-100"]), parse_oklch(colours["base-200"])]
    lines = []
    for name in TEXT_COLOURS:
        colour = parse_oklch(colours.get(name))
        if not colour:
            continue
        # and on its own soft badge: daisyUI's 8% of the colour in base-100
        t = most_of(colour, base, backgrounds + [lab_mix(colour, backgrounds[0], 0.08)])
        if t < 1.0:
            lines.append(f"--tx-{name}: {to_oklch_css(lab_mix(colour, base, t))};")
    base_lin = linear_srgb(base)
    for n in MUTED:
        alpha = n / 100
        while alpha < 1 and not all(contrast(over(base_lin, linear_srgb(bg), alpha), linear_srgb(bg)) >= NEEDED
                                    for bg in backgrounds):
            alpha = round(alpha + 0.01, 2)
        if alpha > n / 100:
            lines.append(f"--tx-muted-{n}: color-mix(in oklab, var(--color-base-content) {alpha * 100:.0f}%, transparent);")
    for name in FILLS:
        fill, text = parse_oklch(colours.get(name)), parse_oklch(colours.get(f"{name}-content"))
        if not fill or not text:
            continue
        fill_lin = linear_srgb(fill)
        if contrast(linear_srgb(text), fill_lin) >= NEEDED:
            continue
        # towards whichever of black and white stands out more on this fill
        black, white = (0.0, 0.0, 0.0), (1.0, 0.0, 0.0)
        end = white if contrast((1, 1, 1), fill_lin) >= contrast((0, 0, 0), fill_lin) else black
        t = most_of(text, end, [fill])
        lines.append(f"--color-{name}-content: {to_oklch_css(lab_mix(text, end, t))};")
    return lines


def highlight(colours):
    """==highlight== (.prose mark): the warning colour at 40% over the page,
    lighter where the text wouldn't read on it - and where even 15% isn't
    enough, the text moved towards black or white instead."""
    text, warn = parse_oklch(colours["base-content"]), linear_srgb(parse_oklch(colours["warning"]))
    pages = [linear_srgb(parse_oklch(colours[k])) for k in ("base-100", "base-200")]

    def reads(colour_lin, pct):
        return all(contrast(colour_lin, over(warn, page, pct / 100)) >= NEEDED for page in pages)
    pct = next((p for p in range(40, 14, -1) if reads(linear_srgb(text), p)), None)
    if pct == 40:
        return []
    if pct:
        return [f"--mark-bg: color-mix(in oklab, var(--color-warning) {pct}%, transparent);"]
    tint = over(warn, pages[0], 0.4)
    end = (1.0, 0.0, 0.0) if contrast((1, 1, 1), tint) >= contrast((0, 0, 0), tint) else (0.0, 0.0, 0.0)
    t = next((i / 100 for i in range(100, -1, -1) if reads(linear_srgb(lab_mix(text, end, i / 100)), 40)), 0.0)
    return [f"--mark-text: {to_oklch_css(lab_mix(text, end, t))};"]


def selection(colours):
    """The editor's selected text: the palette's primary blended into the
    page, from 15% up, until it stands out (SELECTION_SEEN). A primary too
    pale or grey to stand out even at full strength (pastel, wireframe)
    is deepened towards the text colour. The text on it keeps NEEDED."""
    primary, page, text = (parse_oklch(colours[k]) for k in ("primary", "base-100", "base-content"))
    page_lin, text_lin = linear_srgb(page), linear_srgb(text)
    steps = [lab_mix(primary, page, i / 100) for i in range(15, 101)]
    steps += [lab_mix(text, primary, i / 100) for i in range(1, 101)]
    chosen = steps[0]
    for colour in steps:
        lin = linear_srgb(colour)
        if contrast(text_lin, lin) < NEEDED:
            break
        chosen = colour
        if contrast(lin, page_lin) >= SELECTION_SEEN:
            break
    return f"--selection: {to_oklch_css(chosen)};"


def readable(colours):
    """Every line a palette needs to read at 4.5:1 - text colours,
    muted text, text on fills, highlights and selected text."""
    return overrides(colours) + highlight(colours) + [selection(colours)]


# ---- your own colours (Settings > Style > Colours): a daisyUI theme pasted
# from its theme generator. Read, not copied: only daisyUI's own 28 values,
# each checked, and the colours turned into oklch - what reaches a page is
# built from them, never the pasted text. Stored in the own_themes setting.

OWN_PREFIX = "own-"
OWN_LIMIT = 10
_FILLS = ("primary", "secondary", "accent", "neutral", "info", "success", "warning", "error")
COLOUR_VARS = ("base-100", "base-200", "base-300", "base-content", *[x for n in _FILLS for x in (n, f"{n}-content")])
SIZE_VARS = ("radius-selector", "radius-field", "radius-box", "size-selector", "size-field", "border")
EFFECT_VARS = ("depth", "noise")
_OKLCH = re.compile(r"^oklch\(\s*([\d.]+)(%?)\s+([\d.]+)(%?)\s+([\d.]+)(?:deg)?\s*(?:/\s*[\d.]+%?)?\s*\)$", re.I)
_HEX = re.compile(r"^#([0-9a-f]{3}|[0-9a-f]{6}|[0-9a-f]{8})$", re.I)
_RGB = re.compile(r"^rgba?\(\s*([\d.]+)\s*[ ,]\s*([\d.]+)\s*[ ,]\s*([\d.]+)\s*(?:[,/]\s*[\d.]+%?\s*)?\)$", re.I)
_HSL = re.compile(r"^hsla?\(\s*([\d.]+)(?:deg)?\s*[ ,]\s*([\d.]+)%\s*[ ,]\s*([\d.]+)%\s*(?:[,/]\s*[\d.]+%?\s*)?\)$", re.I)
_LENGTH = re.compile(r"^\d{1,3}(\.\d{1,4})?(rem|px|em)?$")
_EFFECT = re.compile(r"^[01](\.\d{1,3})?$")
_LINE = re.compile(r"--([a-z0-9-]{3,30})\s*:\s*([^;{}<>\n]{1,80});")


def _oklab_of_srgb(r, g, b):
    """0-1 sRGB -> oklab."""
    r, g, b = (_ungamma(c) for c in (r, g, b))
    l_ = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m_ = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s_ = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
            1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
            0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_)


def colour_to_oklch(value: str):
    """A colour as daisyUI writes them (oklch) from any of the usual ways -
    oklch(), #hex, rgb(), hsl() - or None if it isn't one."""
    import colorsys
    v = value.strip()
    m = _OKLCH.match(v)
    if m:
        L = float(m.group(1)) / (100 if m.group(2) else 1)
        C = float(m.group(3)) * (0.004 if m.group(4) else 1)  # oklch's 100% chroma is 0.4
        if not (0 <= L <= 1 and 0 <= C <= 0.5 and 0 <= float(m.group(5)) <= 360):
            return None
        return f"oklch({L * 100:.2f}% {C:.4f} {float(m.group(5)):.2f})"
    m = _HEX.match(v)
    if m:
        h = m.group(1)
        h = "".join(c * 2 for c in h) if len(h) == 3 else h[:6]
        rgb = tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    elif (m := _RGB.match(v)):
        rgb = tuple(min(float(x), 255) / 255 for x in m.groups())
    elif (m := _HSL.match(v)):
        rgb = colorsys.hls_to_rgb(float(m.group(1)) % 360 / 360, min(float(m.group(3)), 100) / 100,
                                  min(float(m.group(2)), 100) / 100)
    else:
        return None
    return to_oklch_css(_oklab_of_srgb(*rgb))


@lru_cache(maxsize=4)
def _built_in(name: str) -> dict:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        return theme_colours(open(os.path.join(root, "static", "css", "output.css"), encoding="utf-8").read(), name)
    except OSError:
        return {}


def parse_theme(text: str):
    """A theme from what daisyUI's theme generator exports (its
    @plugin "daisyui/theme" block) or plain CSS variables: (theme, problem).
    theme: {"name", "scheme", "values": {"--color-base-100": "oklch(...)"...}}."""
    text = text or ""
    if len(text) > 20000:
        return None, "That's too long for a theme - paste just the theme's CSS."
    values = {}
    for key, value in _LINE.findall(text):
        value = value.strip()
        if key.startswith("color-") and key[6:] in COLOUR_VARS:
            colour = colour_to_oklch(value)
            if colour:
                values[f"--{key}"] = colour
        elif key in SIZE_VARS and _LENGTH.match(value):  # noqa: SIM114 - one test per kind of value
            values[f"--{key}"] = value
        elif key in EFFECT_VARS and _EFFECT.match(value):
            values[f"--{key}"] = value
    if not any(k.startswith("--color-") for k in values):
        return None, "No colours found - copy the CSS from daisyUI's theme generator and paste it here."
    m = re.search(r'\bname\s*:\s*"([^"]{1,60})"', text) or re.search(r"\bname\s*:\s*'([^']{1,60})'", text)
    name = re.sub(r"[^\w '-]+", "", m.group(1)).strip()[:40] if m else ""
    name = name[:1].upper() + name[1:]  # the generator writes names in lower case
    m = re.search(r"\bcolor-scheme\s*:\s*\"?(light|dark)\b", text)
    base = values.get("--color-base-100")
    scheme = m.group(1) if m else ("dark" if base and parse_oklch(base)[0] < 0.5 else "light")
    # what it doesn't say, daisyUI's own light or dark palette says
    for key, value in _built_in("dark" if scheme == "dark" else "light").items():
        if key in COLOUR_VARS:
            values.setdefault(f"--color-{key}", value)
    return {"name": name, "scheme": scheme, "values": values}, ""


def _readable_for(values: dict) -> list:
    return readable({k[8:]: v for k, v in values.items() if k.startswith("--color-")})


def own_themes(s=None) -> list:
    """Your own themes: [{"key", "name", "scheme", "values", "readable"}] -
    a theme with a value that's no longer valid is used without it."""
    raw = (s or {}).get("own_themes") if s is not None else None
    if raw is None:
        from soloblog import settings
        raw = settings.get("own_themes")
    return [dict(t) for t in _own_themes(raw or "")]


@lru_cache(maxsize=8)
def _own_themes(raw: str) -> tuple:
    import json
    try:
        found = json.loads(raw or "[]")
    except ValueError:
        return ()
    out = []
    for t in found if isinstance(found, list) else []:
        if not isinstance(t, dict) or not str(t.get("key", "")).startswith(OWN_PREFIX):
            continue
        theme, _ = parse_theme("".join(f"{k}: {v};" for k, v in (t.get("values") or {}).items()))
        if theme:
            out.append({"key": t["key"], "name": t.get("name") or t["key"],
                        "scheme": "dark" if t.get("scheme") == "dark" else "light",
                        "values": theme["values"], "readable": [ln for ln in t.get("readable", []) if _LINE.match(ln)]})
    return tuple(out)


def save_own(theme: dict, name: str, key: str = "") -> str:
    """Adds a theme (or replaces the one with this key): its key, or ""
    when there are already OWN_LIMIT."""
    import json
    from soloblog import settings
    themes = own_themes()
    if not key:
        if len(themes) >= OWN_LIMIT:
            return ""
        used = {t["key"] for t in themes}
        key = next(f"{OWN_PREFIX}{i}" for i in range(1, OWN_LIMIT + 2) if f"{OWN_PREFIX}{i}" not in used)
    entry = {"key": key, "name": name or theme["name"] or "My colours", "scheme": theme["scheme"],
             "values": theme["values"], "readable": _readable_for(theme["values"])}
    themes = [entry if t["key"] == key else t for t in themes] + ([] if any(t["key"] == key for t in themes) else [entry])
    settings.set_many({"own_themes": json.dumps(themes)})
    return key


def delete_own(key: str):
    """Removes a theme; a palette that was using it goes back to the default."""
    import json
    from soloblog import settings
    themes = [t for t in own_themes() if t["key"] != key]
    changes = {"own_themes": json.dumps(themes)}
    for field in ("theme", "theme_dark"):
        if settings.get(field) == key:
            changes[field] = settings.DEFAULTS.get(field, "light")
    settings.set_many(changes)


def own_css(s=None) -> str:
    """The CSS for your own themes - on every page, as daisyUI's own are
    in the built stylesheet. Made once per change to them."""
    from soloblog import settings
    return _own_css(settings.get("own_themes") if s is None else s.get("own_themes", ""))


@lru_cache(maxsize=8)
def _own_css(raw: str) -> str:
    out = []
    for t in own_themes({"own_themes": raw}):
        body = ";".join(f"{k}:{v}" for k, v in t["values"].items())
        out.append(f'[data-theme="{t["key"]}"]{{color-scheme:{t["scheme"]};{body}}}')
        if t["readable"]:
            out.append(f'html[data-theme="{t["key"]}"]{{{"".join(t["readable"])}}}')
    return "\n".join(out)


def own_names(s=None) -> dict:
    return {t["key"]: t["name"] for t in own_themes(s)}


def is_dark(name: str, s=None) -> bool:
    if name.startswith(OWN_PREFIX):
        return any(t["key"] == name and t["scheme"] == "dark" for t in own_themes(s))
    return name in DARK_THEMES


def light_choices(s=None) -> list:
    """Your light themes first, then daisyUI's."""
    return [t["key"] for t in own_themes(s) if t["scheme"] == "light"] + LIGHT_THEMES


def dark_choices(s=None) -> list:
    return [t["key"] for t in own_themes(s) if t["scheme"] == "dark"] + DARK_THEMES


def all_choices(s=None) -> list:
    return [t["key"] for t in own_themes(s)] + DAISYUI_THEMES


def theme_label(name: str, s=None) -> str:
    """A palette's name as people see it: yours as you named it."""
    return own_names(s).get(name, name)


# ---- the stylesheet as it's served: output.css, less some daisyUI rules.
# Each has a :has() that isn't on the element it styles, and any one of them
# made the browser restyle the whole page on every change - every key typed
# in the editor (about 290 ms a key on a phone). Each is for something
# Soloblog doesn't use. docs/DEVELOPMENT.md > Removed daisyUI rules lists
# them, what each did, and how to bring one back.
REMOVED_RULES = {
    "toggle-wrapped": re.compile(r"\.toggle:has\("),
    "field-wrapped-disabled": re.compile(r"\.(input|select|textarea):has\(\s*>\s*(input|select|textarea)\[disabled\]\)"),
    "filter": re.compile(r"\.filter(?![\w-])"),
    "theme-controller": re.compile(r":root:has\(\s*input\.theme-controller"),
}
_CSS_TOKEN = re.compile(r'[{};]|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', re.S)


def _top_commas(prelude: str) -> list:
    parts, depth, start = [], 0, 0
    for i, ch in enumerate(prelude):
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(prelude[start:i])
            start = i + 1
    return parts + [prelude[start:]]


def _keep(selector: str) -> bool:
    return ":has(" not in selector or not any(p.search(selector) for p in REMOVED_RULES.values())


def lean_css(css: str) -> str:
    """css without the REMOVED_RULES selectors: a rule left with none goes,
    one that keeps others keeps them. Only selectors with a :has() can go."""
    # per open block: the parts of its body so far, and its prelude
    stack, preludes, buf, pos = [[]], [], [], 0
    for m in _CSS_TOKEN.finditer(css):
        tok = m.group()
        if tok not in "{};":
            continue
        buf.append(css[pos:m.start()])
        pos = m.end()
        text = "".join(buf)
        buf = []
        if tok == ";":
            stack[-1].append(text + ";")
        elif tok == "{":
            preludes.append(text)
            stack.append([])
        else:
            body = "".join(stack.pop() + [text])
            if not preludes:  # a stray } - kept as it was
                stack[-1].append(body + "}")
                continue
            prelude = preludes.pop()
            lead = prelude[:len(prelude) - len(prelude.lstrip())]
            sel = prelude.strip()
            if not sel.startswith("@") and ":has(" in sel:
                kept = [s for s in _top_commas(sel) if _keep(s)]
                if not kept:
                    continue
                prelude = lead + ",".join(kept)
            stack[-1].append(prelude + "{" + body + "}")
    return "".join(stack[0] + preludes + ["".join(buf), css[pos:]])


@lru_cache(maxsize=1)
def served_css(path: str = os.path.join("static", "css", "output.css")) -> tuple:
    """(the stylesheet the app serves, a short hash of it for its address) -
    read once, as output.css only changes with a rebuild."""
    import hashlib
    try:
        with open(path, encoding="utf-8") as f:
            css = lean_css(f.read())
    except OSError:
        return "", "0"
    return css, hashlib.sha256(css.encode("utf-8")).hexdigest()[:12]
