"""Every admin list with page buttons also lets its owner pick 10, 20 or 50
rows per page: the same control beside the page buttons, ?per= in the
address, the last choice kept in a cookie for that list - and anything
else sent as ?per= ignored."""
import os
import re

import pytest
from PIL import Image

from conftest import save_post
from soloblog import comments, config, contact, images, members, newsletter, posts
from soloblog.db import get_db

N = 60  # more than the largest choice, so every size has a next page


def _mark(i):
    return f"rpp-{i:02d}"


HOST = "rpp-host-post"


def _seed_posts(admin):
    save_post(admin, title="rpp host post")  # the comments' post, older than the rest
    for i in range(N):
        save_post(admin, title=_mark(i), body="Hello.")


def _seed_comments(admin):
    slug = HOST
    for i in range(N):
        comments.add_comment(slug, "Reader", f"{_mark(i)}@example.com", _mark(i), auto_confirm=True)


def _seed_messages(admin):
    for i in range(N):
        contact.add("Reader", f"{_mark(i)}@example.com", _mark(i))


def _seed_members(admin):
    for i in range(N):
        members.add(f"{_mark(i)}@example.com", "Reader")


def _seed_subscribers(admin):
    for i in range(N):
        newsletter.subscribe_confirmed(f"{_mark(i)}@example.com")


def _seed_media(admin):
    os.makedirs(config.UPLOADS_DIR, exist_ok=True)
    for i in range(N):
        Image.new("RGB", (40, 30), (30, 120, 200)).save(os.path.join(config.UPLOADS_DIR, _mark(i) + ".webp"), "WEBP")
    images.cache.bump()


def _seed_mentions(admin):
    db = get_db()
    for i in range(N):
        db.execute("INSERT INTO webmentions (post_slug, source, target, content, received_at) VALUES (?, ?, ?, ?, ?)",
                   ("", f"https://rpp.example/{_mark(i)}", "https://me.example/", _mark(i), f"2031-01-01T00:{i:02d}:00"))
    db.commit()


# name, address, seed, rows shown with no choice made (the list's own size)
LISTS = [
    ("posts", "/admin/posts", _seed_posts, 10),
    ("comments", "/admin/comments", _seed_comments, 20),
    ("comments", "/admin/comments?tab=mentions", _seed_mentions, 20),
    ("messages", "/admin/messages", _seed_messages, 20),
    ("members", "/admin/members", _seed_members, 50),
    ("newsletter", "/admin/newsletter", _seed_subscribers, 50),
    ("media", "/admin/media", _seed_media, 20),
]


@pytest.fixture(scope="module")
def seeded(admin):
    """Every list filled past its largest page, once - and emptied again at
    the end: other tests count rows in these lists."""
    # what the tests look at is the newest: so these first
    for i in range(12):
        contact.add("Reader", "solo@example.com", f"solo-{i:02d}")
    for _, _, seed, _ in LISTS:
        seed(admin)
    yield
    db = get_db()
    for sql in ("DELETE FROM comments WHERE body LIKE 'rpp-%'", "DELETE FROM contact_messages WHERE body LIKE 'rpp-%' "
                "OR body LIKE 'solo-%'", "DELETE FROM members WHERE email LIKE 'rpp-%'",
                "DELETE FROM subscribers WHERE email LIKE 'rpp-%'", "DELETE FROM webmentions WHERE content LIKE 'rpp-%'"):
        db.execute(sql)
    db.commit()
    for i in range(N):
        images.delete_upload(_mark(i) + ".webp")
    for row in db.execute("SELECT slug FROM posts WHERE slug LIKE 'rpp-%'").fetchall():
        posts.delete_post(row["slug"])
        posts.delete_forever(row["slug"])


@pytest.fixture(autouse=True)
def forget_choices(admin):
    """A choice is a cookie, and the admin's client is shared by every test."""
    yield
    for cookie in list(admin.cookies.jar):
        if cookie.name.startswith("per_"):
            admin.cookies.jar.clear(cookie.domain, cookie.path, cookie.name)


def _shown(admin, url, extra=""):
    html = admin.get(url + ("&" if "?" in url else "?") + extra).text
    return html, len(set(re.findall(r"rpp-(\d\d)", html)))


def _chosen(html):
    """Which of the three the page says it is showing."""
    return re.findall(r'<a href="[^"]*per=(\d+)"[^>]*aria-current="true"', html) or \
        re.findall(r'aria-current="true"[^>]*href="[^"]*per=(\d+)"', html)


@pytest.mark.parametrize("name, url, seed, default", LISTS, ids=[u for _, u, _, _ in LISTS])
def test_each_list_has_the_choice(admin, seeded, name, url, seed, default):
    html, shown = _shown(admin, url)
    assert shown == default
    assert _chosen(html) == [str(default)]
    for n in (10, 20, 50):
        r = admin.get(url + ("&" if "?" in url else "?") + f"per={n}")
        assert _shown(admin, url, f"per={n}")[1] == n
        assert f"per_{name}={n}" in r.headers.get("set-cookie", "")
        # kept: the next visit, with no ?per=, shows the same
        assert _shown(admin, url)[1] == n
    # anything else is ignored - the last choice stands
    for junk in ("7", "0", "-1", "abc", "20;x", "1" * 40, "%00", "20.0", ""):
        r = admin.get(url + ("&" if "?" in url else "?") + f"per={junk}")
        assert r.status_code == 200, junk
        assert "per_" not in r.headers.get("set-cookie", ""), junk
        assert _shown(admin, url, f"per={junk}")[1] == 50, junk


@pytest.mark.parametrize("name, url, seed, default", LISTS[:1] + LISTS[3:4], ids=["posts", "messages"])
def test_a_junk_choice_with_nothing_kept_is_the_default(admin, seeded, name, url, seed, default):
    assert _shown(admin, url, "per=999")[1] == default
    assert _shown(admin, url, "per=x")[1] == default


def test_changing_the_size_goes_to_page_one_and_keeps_the_filters(admin, seeded):
    html, _ = _shown(admin, "/admin/posts", "sort=oldest&q=rpp&per=10&page=3")
    links = re.findall(r'href="([^"]*per=\d+[^"]*)"', html)
    sizes = [h for h in links if re.search(r"per=\d+$", h.replace("&amp;", "&"))]
    assert len(sizes) >= 3
    for h in sizes[:3]:
        h = h.replace("&amp;", "&")
        assert "sort=oldest" in h and "q=rpp" in h and "page=" not in h, h
    # the page buttons keep the size
    page_links = [h for h in links if "page=" in h]
    assert page_links and all("per=10" in h for h in page_links)


def test_the_choice_shows_only_when_there_is_more_than_ten(admin, seeded):
    html = admin.get("/admin/messages?q=solo-").text
    assert "Per page" in html  # twelve, on one page: still there, to make it smaller
    assert "Page 1 of" not in html
    html = admin.get("/admin/messages?q=solo-11").text
    assert "Per page" not in html  # one
    # ten (solo-00 to solo-09): nothing to choose between
    assert "Per page" not in admin.get("/admin/messages?q=solo-0").text


def test_a_choice_is_kept_for_its_own_list(admin, seeded):
    _shown(admin, "/admin/posts", "per=10")
    assert _shown(admin, "/admin/messages")[1] == 20
    _shown(admin, "/admin/messages", "per=50")
    assert _shown(admin, "/admin/posts")[1] == 10


def test_only_a_get_of_an_admin_list_sets_the_cookie(admin, client, seeded):
    r = client.get("/?per=20")
    assert "per_" not in r.headers.get("set-cookie", "")
    r = admin.get("/admin/posts?per=20")
    cookie = r.headers["set-cookie"]
    assert "Path=/admin" in cookie and "HttpOnly" in cookie and "SameSite=lax" in cookie.replace("Lax", "lax")
