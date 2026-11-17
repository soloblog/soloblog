"""docs/TEMPLATES.md has an entry for every template and every section, so a
new one can't be added without it."""
from pathlib import Path
import os
import re

from soloblog import post_templates, sections

DOC = Path(os.path.join(os.path.dirname(__file__), "..", "docs", "TEMPLATES.md")).read_text(encoding="utf-8")


def _rows(heading):
    part = DOC.split(f"\n## {heading}\n")[1].split("\n## ")[0]
    return [line for line in part.splitlines() if line.startswith("| ") and not line.startswith("| ---")]


def test_every_template_has_an_entry():
    names = [row.split(" | ")[0].removeprefix("| ") for row in _rows("Templates")]
    for name, *_ in post_templates.BUILT_IN.values():
        assert name in names, name
    assert len(names) == len(post_templates.BUILT_IN) + 1  # and the header


def test_every_section_has_an_entry():
    first = [row.split(" | ")[0].removeprefix("| ") for row in _rows("Sections")]
    for entry in sections.REGISTRY.values():
        assert any(re.match(rf"{re.escape(entry['label'])}( \(also .*\))?$", cell) for cell in first), entry["label"]
        # every name people may write is there, too
        for name in entry["names"][1:]:
            assert name in first[[i for i, c in enumerate(first) if c.startswith(entry["label"])][0]], name
    assert len(first) == len(sections.REGISTRY) + 1


def test_development_links_to_it():
    development = Path(os.path.join(os.path.dirname(__file__), "..", "docs", "DEVELOPMENT.md")).read_text(encoding="utf-8")
    assert "TEMPLATES.md" in development.split("## Adding a section")[1].split("\n## ")[0]
