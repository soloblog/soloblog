"""Writes soloblog/editor_icons.py: the Lucide icons the editor's commands
use (editor_config.COMMANDS, MENUS and EXTRA_ICONS), as SVG markup.

    python tools/editor_icons.py

Run it after giving a command an icon it didn't have. It fetches each one
from jsdelivr, pinned to one Lucide version, and puts Lucide's licence at
the top of the file.
"""
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from soloblog import editor_config  # noqa: E402

VERSION = "0.469.0"
BASE = f"https://cdn.jsdelivr.net/npm/lucide-static@{VERSION}"


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=20) as r:  # noqa: S310 - a fixed jsDelivr address
        return r.read().decode("utf-8")


def main():
    names = list(dict.fromkeys([c["icon"] for c in editor_config.COMMANDS]
                               + [icon for _, icon in editor_config.MENUS.values()]
                               + list(editor_config.EXTRA_ICONS)))
    icons = {}
    for name in names:
        inner = re.search(r"<svg[^>]*>(.*)</svg>", get(f"/icons/{name}.svg"), re.S).group(1)
        # one line, no comments, no whitespace between elements
        inner = re.sub(r"<!--.*?-->", "", inner, flags=re.S)
        icons[name] = re.sub(r">\s+<", "><", inner.strip())
    licence = get("/LICENSE").strip()

    lines = ['"""The editor\'s icons: Lucide (https://lucide.dev), version ' + VERSION + ',',
             "copied in as SVG markup - only the ones the editor uses. Made by",
             "tools/editor_icons.py; run it again after giving a command a new icon.", "",
             "Lucide's licence:", ""]
    lines += ["    " + line if line else "" for line in licence.splitlines()]
    lines += ['"""', "", "# the attributes every icon shares; each entry is what goes inside <svg>",
              'SVG = (\'<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" '
              'fill="none" \'',
              '       \'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" \'',
              '       \'aria-hidden="true" class="editor-icon">{}</svg>\')', "", "ICONS = {"]
    lines += [f"    {name!r}: {icons[name]!r}," for name in names]
    lines += ["}", "", "", "def svg(name: str) -> str:", "    return SVG.format(ICONS[name])", ""]
    (ROOT / "soloblog" / "editor_icons.py").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(len(icons), "icons")


if __name__ == "__main__":
    main()
