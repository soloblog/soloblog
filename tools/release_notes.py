"""Prints a version's release notes - its part of CHANGELOG.md - for the
GitHub Release a version tag makes (.github/workflows/docker.yml).

    python tools/release_notes.py v1.0.0-beta

Fails, so no release is made, if the changelog has nothing for that
version or soloblog/config.py's VERSION says something else.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from soloblog import whatsnew  # noqa: E402


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: python tools/release_notes.py v1.0.0-beta")
    version = sys.argv[1].removeprefix("v")
    with open(os.path.join(ROOT, "soloblog", "config.py"), encoding="utf-8") as f:
        m = re.search(r'^VERSION = "([^"]+)"', f.read(), re.M)
    if not m or m.group(1) != version:
        sys.exit(f"soloblog/config.py says VERSION = {m.group(1) if m else '?'!r}, not {version!r} - "
                 "bump it before tagging (docs/DEVELOPMENT.md > Releasing)")
    notes = whatsnew.section(whatsnew.read(), version)
    if not notes:
        sys.exit(f"CHANGELOG.md has no \"## [{version}]\" section - move Unreleased under it first")
    print(notes)


if __name__ == "__main__":
    main()
