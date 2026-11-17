"""What a screen reader relies on: one h1 and headings in order, names on
dialogs and navigation, status messages that are announced."""
import re
from html.parser import HTMLParser

from soloblog.ui import Alert, SettingsPanel
from soloblog.ui.lists import SaveStatus
from fasthtml.common import to_xml
from conftest import save_post

VOID = {"br", "hr", "img", "input", "meta", "link", "source", "path", "circle", "rect", "line", "polyline", "use"}


class _Page(HTMLParser):
    """Headings, dialogs, navs and status spans of one page, in order."""

    def __init__(self):
        super().__init__()
        self.headings, self.dialogs, self.navs, self.statuses = [], [], [], []
        self.ids, self.stack = set(), []
        self._heading = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        in_dialog = "dialog" in self.stack
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6") and not in_dialog:
            self._heading = [int(tag[1]), ""]
            self.headings.append(self._heading)
        if tag == "dialog":
            self.dialogs.append(a)
        if tag == "nav":
            self.navs.append(a)
        if "data-status-slot" in a or (a.get("id", "").endswith("-status") and tag == "span"):
            self.statuses.append(a)
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self.stack:
            while self.stack and self.stack.pop() != tag:
                pass
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._heading = None

    def handle_data(self, data):
        if self._heading:
            self._heading[1] += data


def _page(html):
    p = _Page()
    p.feed(html)
    return p


def _pages(admin, client):
    slug = save_post(admin, title="A post for the screen reader", body="## Part one\n\nText.\n\n### A detail\n\nMore.")
    visitor = ["/", f"/post/{slug}", "/tags", "/archive", "/search?q=post"]
    owner = ["/admin/posts", "/admin/new", f"/admin/edit/{slug}", "/admin/media", "/admin/comments",
             "/admin/settings?tab=name", "/admin/settings?tab=style", "/admin/settings?tab=comments",
             "/admin/help"]
    out = {}
    for path in visitor:
        out[path] = client.get(path).text
    for path in owner:
        r = admin.get(path)
        if r.status_code == 200:
            out[path] = r.text
    return out


def test_a_page_has_one_h1_and_no_heading_jumps(admin, client):
    for path, html in _pages(admin, client).items():
        levels = [lvl for lvl, _ in _page(html).headings]
        assert levels.count(1) == 1, (path, levels)
        for before, after in zip(levels, levels[1:]):
            assert after <= before + 1, (path, f"jumps from h{before} to h{after}", levels)


def test_settings_panels_are_headings(admin):
    html = admin.get("/admin/settings?tab=name").text
    titles = [t.strip() for lvl, t in _page(html).headings if lvl == 2]
    assert "Identity" in titles and "Homepage" in titles
    # the heading sits in the summary: the title still opens and closes the panel
    assert re.search(r"<summary[^>]*>\s*<h2[^>]*>\s*Identity", html)
    assert "<h2" in to_xml(SettingsPanel("Panel", "x", key="t"))


def test_every_dialog_has_a_name(admin, client):
    for path, html in _pages(admin, client).items():
        page = _page(html)
        for d in page.dialogs:
            label = d.get("aria-label") or ""
            by = d.get("aria-labelledby") or ""
            assert label or by, (path, d.get("id"))
            assert not by or by in page.ids, (path, d.get("id"), by)


def test_the_admin_menu_is_a_navigation_landmark(admin):
    for path in ("/admin/posts", "/admin/settings?tab=name", "/admin/new"):
        navs = _page(admin.get(path).text).navs
        assert any(n.get("aria-label") == "Admin" for n in navs), path


def test_status_messages_are_announced(admin, client):
    for path, html in _pages(admin, client).items():
        for s in _page(html).statuses:
            assert s.get("role") in ("status", "alert") or s.get("aria-live"), (path, s)
    assert 'role="status"' in to_xml(SaveStatus("Saved"))
    assert 'role="alert"' in to_xml(Alert("It didn't work", "error"))
    assert 'role="status"' in to_xml(Alert("Saved", "success"))


def test_icon_buttons_have_names(admin, client):
    for path, html in _pages(admin, client).items():
        for m in re.finditer(r"<button\b([^>]*)>(.*?)</button>", html, re.S):
            attrs, inner = m.groups()
            text = re.sub(r"<[^>]+>", "", re.sub(r"<svg.*?</svg>", "", inner, flags=re.S)).strip()
            assert text or "aria-label=" in attrs or "aria-labelledby=" in attrs or "hidden" in attrs.split(), \
                (path, m.group(0)[:160])


def test_the_comment_form_says_what_happens(client, admin):
    slug = save_post(admin, title="Comment status post")
    html = client.get(f"/post/{slug}").text
    assert re.search(r'<span[^>]*role="status"[^>]*id="comment-status"|<span[^>]*id="comment-status"[^>]*role="status"', html)
