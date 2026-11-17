"""What's new: the changelog read for the card on Posts, Help and the
release notes a tag makes."""
import subprocess
import sys

from soloblog import config
from soloblog import settings
from soloblog import whatsnew

CHANGELOG = """# Changelog

## [Unreleased]

## [0.5.0-beta] - 2026-11-01

**Upgrading**

1. Nothing yet.

### Added

- **Site health**: one page that says whether anything needs you,
  as [the guide](docs/guide/run.md) says.
- **What's new** after an update.
- A `small` thing - with a dash in it.

### Fixed

- Something that was broken.

## [0.4.0-beta] - 2026-10-20

### Added

- An older thing.

[Unreleased]: https://example.com/compare/v0.5.0-beta...HEAD
[0.5.0-beta]: https://example.com/releases/tag/v0.5.0-beta
"""


def test_a_version_and_its_headlines():
    body = whatsnew.section(CHANGELOG, "0.5.0-beta")
    assert body.startswith("**Upgrading**") and "An older thing" not in body and "example.com" not in body
    # the bold ones are the big ones - the rest wait for the full notes
    assert whatsnew.highlights(body) == ["Site health", "What's new"]
    assert whatsnew.needs_upgrading(body)
    older = whatsnew.section(CHANGELOG, "0.4.0-beta")
    assert whatsnew.highlights(older) == ["An older thing"] and not whatsnew.needs_upgrading(older)
    assert whatsnew.highlights("- A `small` thing - with a dash in it.") == ["A small thing"]
    assert whatsnew.section(CHANGELOG, "9.9.9") == ""
    # Help: plain version headings, no empty Unreleased, no link list
    help_text = whatsnew.for_help(CHANGELOG)
    assert "## 0.5.0-beta - 2026-11-01" in help_text and "Unreleased" not in help_text
    assert "example.com" not in help_text and help_text.startswith("# Changelog\n")
    filled = whatsnew.for_help(CHANGELOG.replace("## [Unreleased]\n", "## [Unreleased]\n\n- **Next**\n"))
    assert "## Unreleased" in filled and "- **Next**" in filled


def test_the_card_shows_once_per_version(admin, monkeypatch):
    before = settings.get("whatsnew_seen")
    monkeypatch.setattr(config, "VERSION", "0.5.0-beta")
    monkeypatch.setattr(whatsnew, "read", lambda path=None: CHANGELOG)
    try:
        settings.set_many({"whatsnew_seen": "0.4.0-beta"})
        html = admin.get("/admin/posts").text
        assert "What's new in 0.5.0-beta" in html and "Site health" in html and "Upgrading" in html
        assert 'href="/admin/help?tab=whatsnew"' in html
        # only on the list's first view, not a filtered one
        assert "What's new in" not in admin.get("/admin/posts?status=draft").text
        r = admin.post("/admin/whatsnew/dismiss")
        assert r.status_code == 303 and settings.get("whatsnew_seen") == "0.5.0-beta"
        assert "What's new in" not in admin.get("/admin/posts").text
        # a version the changelog doesn't have: no empty card
        monkeypatch.setattr(config, "VERSION", "9.9.9")
        assert "What's new in" not in admin.get("/admin/posts").text
    finally:
        settings.set_many({"whatsnew_seen": before})


def test_dismissing_needs_the_login(client):
    before = settings.get("whatsnew_seen")
    r = client.post("/admin/whatsnew/dismiss")
    assert r.status_code in (302, 303) and "/login" in r.headers["location"]
    assert settings.get("whatsnew_seen") == before


def test_help_has_the_changelog(admin):
    html = admin.get("/admin/help?tab=whatsnew").text
    assert "What&#x27;s new" in html or "What's new" in html
    assert config.VERSION in html
    # every Help page lists it
    assert 'href="/admin/help?tab=whatsnew"' in admin.get("/admin/help").text


def test_release_notes_tool(tmp_path):
    """In a copy with a changelog of its own - the real one's [Unreleased]
    is the next release's summary, with no section for VERSION yet."""
    import os
    import re
    import shutil
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for rel in ("tools/release_notes.py", "soloblog/config.py", "soloblog/whatsnew.py"):
        os.makedirs(tmp_path / os.path.dirname(rel), exist_ok=True)
        shutil.copy(os.path.join(root, rel), tmp_path / rel)
    (tmp_path / "soloblog" / "__init__.py").write_text("")
    (tmp_path / "CHANGELOG.md").write_text(CHANGELOG.replace("0.5.0-beta", config.VERSION))
    tool = [sys.executable, "tools/release_notes.py"]
    ok = subprocess.run(tool + [f"v{config.VERSION}"], capture_output=True, text=True, cwd=tmp_path)
    assert ok.returncode == 0, ok.stderr
    section = whatsnew.section(CHANGELOG.replace("0.5.0-beta", config.VERSION), config.VERSION)
    # the same words, each paragraph and list item on one line - a GitHub
    # Release keeps every line break
    assert [w for w in ok.stdout.split() if "](" not in w] == [w for w in section.split() if "](" not in w]
    # a link into the repository goes to it from the Release page
    assert not re.search(r"\]\((?!https?:|#|mailto:)", ok.stdout), ok.stdout
    assert not any(line.startswith(" ") and not line.lstrip().startswith(("-", "*")) for line in
                   ok.stdout.splitlines()), ok.stdout
    # a tag VERSION wasn't bumped to: no release
    bad = subprocess.run(tool + ["v9.9.9"], capture_output=True, text=True, cwd=tmp_path)
    assert bad.returncode != 0 and "VERSION" in bad.stderr
