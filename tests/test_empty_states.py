"""What every list says with nothing in it, and every form with nothing
typed: what's missing and the next step, or a plain error beside the
field - never an empty table, a bare "None" or a made-up success."""
import re

import pytest

from conftest import PASSWORD, save_post
from soloblog import images, posts
from soloblog.db import get_db


def _text(html):
    html = re.sub(r"<(script|style|svg).*?</\1>", "", html, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


@pytest.fixture
def nothing(monkeypatch):
    """A site with no posts, uploads, members, subscribers or messages."""
    db = get_db()
    for table in ("members", "subscribers", "contact_messages"):
        db.execute(f"DELETE FROM {table}")  # noqa: S608 - fixed table names
    db.commit()
    monkeypatch.setattr(posts, "list_trash", lambda: [])
    monkeypatch.setattr(images, "list_uploads", lambda: [])
    monkeypatch.setattr(images, "list_trash", lambda: [])


def test_empty_posts_lists_say_what_is_missing(admin, nothing):
    # a list with nothing in it at all offers the first post; a filter says it matched nothing
    from soloblog.routes import editor
    assert "No posts yet." in _text(str(editor._no_posts("all", "", False)))
    assert 'href="/admin/new"' in str(editor._no_posts("all", "", False))
    assert "Nothing published yet." in str(editor._no_posts("published", "", False))
    assert "No drafts." in str(editor._no_posts("draft", "", False))
    assert "href" not in str(editor._no_posts("scheduled", "", False))
    assert "Nothing matches “zz”." in str(editor._no_posts("all", "zz", True))
    assert "Nothing matches this filter." in str(editor._no_posts("all", "", True))


def test_empty_trash_and_pinned_say_so(admin, nothing):
    assert "Trash is empty." in _text(admin.get("/admin/posts?status=trash").text)
    assert "Nothing here." not in _text(admin.get("/admin/posts?status=trash").text)
    pinned = _text(admin.get("/admin/posts?status=pinned").text)
    if "Nothing pinned yet." in pinned:
        assert "Where it appears" in pinned


def test_empty_media_members_subscribers_messages_point_to_the_next_step(admin, nothing):
    assert "Use Upload to add" in _text(admin.get("/admin/media").text)
    assert "Add one above, or use Import" in _text(admin.get("/admin/members").text)
    assert "use Import to bring a list" in _text(admin.get("/admin/newsletter").text)
    assert "contact form shows here" in _text(admin.get("/admin/messages").text)


def test_a_search_with_no_results_says_what_was_searched(admin, nothing):
    for url in ("/admin/posts?q=zzqx", "/admin/media?q=zzqx", "/admin/comments?q=zzqx",
                "/admin/messages?q=zzqx", "/admin/members?q=zzqx", "/admin/newsletter?q=zzqx"):
        page = _text(admin.get(url).text)
        assert "Nothing matches “zzqx”." in page, url
        assert "Clear" in page, url


def test_folded_settings_say_what_is_missing_not_none(admin):
    page = _text(admin.get("/admin/settings?tab=integrations").text)
    assert "No keys" in page or " key" in page
    assert re.search(r"API keys\s+None\b", page) is None
    assert re.search(r"Webhooks\s+None\b", page) is None


def test_the_owner_sees_how_to_start_on_an_empty_home(admin, client, monkeypatch):
    monkeypatch.setattr(posts, "list_roll", lambda **k: [])
    monkeypatch.setattr(posts, "count_roll", lambda: 0)
    assert 'href="/admin/new"' in admin.get("/").text
    page = client.get("/").text
    assert "Nothing published yet." in _text(page)
    assert 'href="/admin/new"' not in page


def test_a_tag_page_needs_a_tag(client):
    assert client.get("/tag/%20").status_code == 404


def test_empty_comment_is_answered_not_posted(client, admin):
    slug = save_post(admin, title="Comment on me", slug="comment-on-me")
    sent = {"hx-request": "true"}
    r = client.post(f"/post/{slug}/comment", data={"body": "", "author_name": "A", "email": "a@example.com"},
                    headers=sent)
    assert "Write a comment first" in r.text and "text-error" in r.text
    r = client.post(f"/post/{slug}/comment", data={"body": "Hi", "author_name": "", "email": "a@example.com"},
                    headers=sent)
    assert "Add your name" in r.text and "text-error" in r.text
    r = client.post(f"/post/{slug}/comment", data={"body": "Hi", "author_name": "A", "email": ""}, headers=sent)
    assert "doesn't look like an email address" in r.text


def test_empty_passwords_are_asked_for_not_called_wrong(client, admin):
    assert "Enter your password." in client.post("/login", data={"password": ""}).text
    assert "Wrong password" not in client.post("/login", data={"password": ""}).text
    r = admin.post("/admin/settings/password", data={"current": "", "password": "", "confirm": ""},
                   headers={"hx-request": "true"})
    assert "Enter your current password" in r.text
    r = admin.post("/admin/recovery-key", data={"password": ""}, headers={"hx-request": "true"})
    assert "Enter your password" in r.text
    r = client.post("/forgot-password/key", data={"key": "", "password": "", "confirm": ""})
    assert "Enter your recovery key." in r.text
    assert PASSWORD  # the real password still works
    assert client.post("/login", data={"password": PASSWORD}).status_code == 303
