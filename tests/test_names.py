"""One name for one thing, everywhere: what people read, and what the code,
the addresses and the links call it. Before launch every older name went
(2026-11-09); these keep a new one from drifting away from its label.
The settings pages' own (address, groups, save) are in test_settings_pages."""
from pathlib import Path
import re

from soloblog import post_templates, sections
from soloblog.ui import SETTINGS_SECTIONS


def _words(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def _named_by(key, label):
    """A key is its label, or words from it - "reviews" for Book or film
    reviews, "media-kit" for Media kit / press, "howto" for How-to - or
    its initials (cta, Call to action)."""
    words, parts = _words(label), _words(key)
    joined = "".join(words)
    return all(p in words or p in joined for p in parts) or key == "".join(w[0] for w in words)


def test_each_section_is_named_by_its_label():
    wrong = {k: e["label"] for k, e in sections.REGISTRY.items() if not _named_by(k, e["label"])}
    assert not wrong, wrong
    # a section is found by the name people write, which is its label first
    for key, entry in sections.REGISTRY.items():
        assert sections.NAMES[entry["label"].lower()] == key, key


def test_each_template_is_named_by_its_name():
    wrong = {k: v[0] for k, v in post_templates.BUILT_IN.items() if not _named_by(k, v[0])}
    assert not wrong, wrong


def test_each_settings_page_is_named_by_its_title():
    for key, label in SETTINGS_SECTIONS:
        # the first word - but Comments and messages is /messages: comments was
        # the address of the page before it, and old addresses are gone
        assert label.lower().split()[0] == key or (key, label) == ("messages", "Comments and messages"), (key, label)


def test_each_admin_menu_item_is_at_an_address_from_its_label(admin):
    """Newsletter at /admin/newsletter, Site health at /admin/health - every
    admin link named in plain words, in the header's menu and the side one."""
    html = admin.get("/admin/posts").text
    items = set(re.findall(r'<a href="/admin/([a-z-]+)"[^>]*>\s*([A-Z][A-Za-z ]+?)\s*</a>', html))
    items |= {(p, label) for p, label in re.findall(
        r'<a[^>]*href="/admin/([a-z-]+)"[^>]*>(?:(?!</a>).)*?<span>([^<]+)</span>', html, re.S)}
    assert {p for p, _ in items} >= {"posts", "media", "comments", "stats", "health"}, items
    for path, label in items:
        assert path in _words(label), (path, label)


def test_settings_and_help_share_one_menu_on_a_phone(admin):
    """Settings' twenty pages and Help's sixteen: the same grouped menu where
    the admin menu isn't beside the page (ui.PageNav) - tabs are for a few
    choices. Help had tabs with the rest under More."""
    # a backup's own screens (checked after an upload, _backup_page) use the Settings one too
    backup = Path("soloblog/routes/backup_routes.py").read_text(encoding="utf-8")
    assert backup.count('SettingsNav("backup")') == 1 and "SettingsTabs" not in backup
    for url, nav in (("/admin/settings?tab=email", "settings-nav"), ("/admin/help?tab=faq", "help-nav")):
        html = admin.get(url, follow_redirects=True).text
        assert f'popovertarget="{nav}"' in html and f'id="{nav}"' in html, url
        menu = html.split(f'id="{nav}"')[1].split("</ul>")[0]
        assert 'class="menu-title"' in menu and 'aria-current="page"' in menu, url
        assert 'id="help-tabs"' not in html and 'id="settings-tabs"' not in html, url
