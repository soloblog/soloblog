"""The admin's words stay short (docs/DEVELOPMENT.md > Writing and
settings): a help line under a setting is one line, not a paragraph."""
import re

from soloblog.ui import SETTINGS_SECTIONS

PAGES = [f"/admin/settings?tab={t}" for t, _ in SETTINGS_SECTIONS]
# a field's help (FormField) and a switch's (ToggleField)
HELP = re.compile(r'<p id="[^"]*-h" class="fieldset-label">(.*?)</p>'
                  r'|<span class="block text-xs text-base-content/60 mt-0.5">(.*?)</span>', re.S)
LONGEST = 140


def _text(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html)).strip()


def test_help_lines_are_one_line(admin):
    from conftest import save_post
    slug = save_post(admin, title="Copy check")
    long = []
    for url in PAGES + [f"/admin/edit/{slug}"]:
        for m in HELP.finditer(admin.get(url).text):
            text = _text(m.group(1) or m.group(2))
            if len(text) > LONGEST:
                long.append((url, text))
    assert not long, long


def test_no_directions_around_the_admin(admin):
    """Somewhere to set up first is a link, not "(Integrations > Email)"."""
    for url in PAGES:
        page = _text(admin.get(url).text.split('id="page-content"', 1)[1])
        assert not re.search(r"\((?:Settings|Integrations|Appearance|Visitors|Site|Security) > ", page), url


def test_the_check_sees_the_help_lines(admin):
    assert len(HELP.findall(admin.get("/admin/settings?tab=posts").text)) > 5
