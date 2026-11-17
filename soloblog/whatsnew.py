"""What's new: one version's part of CHANGELOG.md - for the card on Posts
after an update, Help > What's new, and the GitHub Release a version tag
makes (tools/release_notes.py, which is why nothing here imports the
rest of the app)."""
import os
import re

CHANGELOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "CHANGELOG.md")
_VERSION_HEADING = re.compile(r"^## \[([^\]]+)\]", re.M)
# the link definitions at the foot ("[0.3.0-beta]: https://...")
_LINK_DEFS = re.compile(r"^\[[^\]]+\]: \S+\s*$", re.M)


def read(path: str = CHANGELOG) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def section(text: str, version: str) -> str:
    """The changelog under "## [version]", without its heading - "" if
    that version isn't there."""
    for m in _VERSION_HEADING.finditer(text):
        if m.group(1) == version:
            rest = text[m.end():].split("\n", 1)[1] if "\n" in text[m.end():] else ""
            following = _VERSION_HEADING.search(rest)
            body = rest[:following.start()] if following else rest
            return _LINK_DEFS.sub("", body).strip()
    return ""


def for_help(text: str) -> str:
    """The changelog as Help shows it: each version a plain heading (not a
    link to GitHub), without the note on its format that's meant for
    developers, and without the empty "Unreleased" a release still has."""
    if not section(text, "Unreleased").strip("- \n#"):
        text = re.sub(r"^## \[Unreleased\][^\n]*\n(?:(?!^## \[).*\n?)*", "", text, count=1, flags=re.M)
    first = _VERSION_HEADING.search(text)
    if first:
        text = text[:first.start()].split("\n", 1)[0] + "\n\n" + text[first.start():]
    text = _LINK_DEFS.sub("", text)
    return re.sub(r"^## \[([^\]]+)\]", r"## \1", text, flags=re.M)


def highlights(body: str) -> list[str]:
    """The headline of each top-level entry. The ones that open with bold
    words are the big ones, so where there are any, only those; otherwise
    each entry's first sentence, kept short."""
    bold, plain = [], []
    for line in body.splitlines():
        if not line.startswith("- "):
            continue
        entry = line[2:].strip()
        m = re.match(r"\*\*(.+?)\*\*", entry)
        if m:
            bold.append(m.group(1).rstrip(":.").replace("`", ""))
            continue
        title = re.split(r"(?<=[.:;])\s| - ", entry, maxsplit=1)[0].rstrip(".:;,").replace("`", "")
        if len(title) > 80:
            title = title[:77].rsplit(" ", 1)[0] + "…"
        plain.append(title)
    return bold or plain


def needs_upgrading(body: str) -> bool:
    """Whether the version asks the person running it to do something - it
    starts with an Upgrading part (docs/DEVELOPMENT.md > Releasing)."""
    return bool(re.search(r"^(?:#+ |\*\*)Upgrading", body, re.M))
