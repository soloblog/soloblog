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


# a line that starts something of its own, not the rest of the one before
_STARTS = re.compile(r"\s*([-*+] |\d+\. |#|>|\||```)")


def unwrapped(text: str) -> str:
    """CHANGELOG.md is wrapped at 72 characters; a GitHub Release keeps
    every line break, so each paragraph and list item is joined back into
    one line. Code blocks and tables stay as they are."""
    out, code = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            code = not code
            out.append(line)
        elif code or not line.strip() or not out or not out[-1].strip() or _STARTS.match(line) \
                or out[-1].lstrip().startswith(("#", "|", "```")):
            out.append(line)
        else:
            out[-1] = out[-1].rstrip() + " " + line.strip()
    return "\n".join(out)


def _project() -> str:
    with open(os.path.join(ROOT, "soloblog", "config.py"), encoding="utf-8") as f:
        m = re.search(r'^PROJECT_URL = "([^"]+)"', f.read(), re.M)
    return m.group(1) if m else "https://github.com/soloblog/soloblog"


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: python tools/release_notes.py v1.0.0-beta")
    version = sys.argv[1].removeprefix("v")
    with open(os.path.join(ROOT, "soloblog", "config.py"), encoding="utf-8") as f:
        m = re.search(r'^VERSION = "([^"]+)"', f.read(), re.M)
    if not m or m.group(1) != version:
        sys.exit(f"soloblog/config.py says VERSION = {m.group(1) if m else '?'!r}, not {version!r} - "
                 "bump it before tagging (docs/DEVELOPMENT.md > Releasing)")
    PROJECT = _project()
    notes = whatsnew.section(whatsnew.read(), version)
    if not notes:
        sys.exit(f"CHANGELOG.md has no \"## [{version}]\" section - move Unreleased under it first")
    # a link into the repository, as the changelog has it, leads nowhere
    # from the Release page
    notes = re.sub(r"\]\((?!https?:|#|mailto:)([^)\s]+)\)", rf"]({PROJECT}/blob/master/\1)", notes)
    print(unwrapped(notes))


if __name__ == "__main__":
    main()
