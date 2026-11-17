"""Every link between the docs, checked: the file is there, and so is the
#anchor - the heading ids the docs actually get (render.render_post, as on
GitHub and in Help). Outside links aren't fetched. Prints what's broken;
exits 1 if anything is.

    python tools/doclinks.py
"""
from pathlib import Path
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)")


_ANCHORS = {}


def anchors(path, cache=_ANCHORS):
    if path not in cache:
        from soloblog.render import render_post
        html, _ = render_post(Path(path).read_text(encoding="utf-8"))
        cache[path] = set(re.findall(r'\bid="([^"]+)"', html))
    return cache[path]


def main():
    files = [os.path.join(ROOT, f) for f in ("README.md", "CHANGELOG.md", "SECURITY.md", "SUPPORT.md",
                                             "CONTRIBUTING.md") if os.path.exists(os.path.join(ROOT, f))]
    files += sorted(os.path.join(ROOT, "docs", f) for f in os.listdir(os.path.join(ROOT, "docs")) if f.endswith(".md"))
    broken = []
    for path in files:
        text = re.sub(r"```.*?```", "", Path(path).read_text(encoding="utf-8"), flags=re.S)
        for target in LINK.findall(text):
            if re.match(r"[a-z]+:", target) or target.startswith("/"):
                continue  # outside links, mail, and the app's own addresses
            file_part, _, anchor = target.partition("#")
            dest = os.path.normpath(os.path.join(os.path.dirname(path), file_part)) if file_part else path
            where = os.path.relpath(path, ROOT)
            if not os.path.exists(dest):
                broken.append(f"{where}: {target} - no such file")
            elif anchor and dest.endswith(".md") and anchor not in anchors(dest):
                broken.append(f"{where}: {target} - no such heading")
    print("\n".join(broken) or "Every link between the docs works.")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
