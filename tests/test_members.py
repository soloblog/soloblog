"""The members area: joining and signing in by an emailed link or code,
who can read what, and that a members post's text never leaves the site
for anyone who can't read it - through the page, feeds, search, the
fediverse or the newsletter. With the abuse cases: reused, expired and
guessed links and codes, address fishing, open redirects, a member's
cookie aimed at the admin."""
from pathlib import Path
import json
from urllib.parse import unquote
from datetime import timedelta
from soloblog.tz import utcnow

import pytest
from starlette.testclient import TestClient

from soloblog import members
from soloblog import posts
from soloblog import settings
from soloblog.db import get_db
from conftest import save_post

SECRET = "The heron's name is Gerald Junior."
BODY = f"Everyone can read this first part.\n\n<!-- members only from here -->\n\n{SECRET}"
KEYS = ("members_enabled", "members_header", "email_provider", "email_api_key", "email_api_from",
        "newsletter_mode", "newsletter_full", "reactions_style", "members_comments", "comments_enabled", "members_welcome")


@pytest.fixture
def on(monkeypatch):
    """The members area on, with email - and every sign-in email caught
    here instead of sent."""
    from soloblog.routes import members_routes
    before = {k: settings.get(k) for k in KEYS}
    last_subscriber = get_db().execute("SELECT COALESCE(MAX(id), 0) FROM subscribers").fetchone()[0]
    sent = []
    monkeypatch.setattr(members_routes, "_send", lambda email, token, code, purpose, s:
                        sent.append({"email": email, "token": token, "code": code, "purpose": purpose}))
    monkeypatch.setattr(members_routes, "_no_account", lambda email, s: sent.append({"email": email, "purpose": "none"}))
    settings.set_many({"members_enabled": "1", "members_header": "1", "email_provider": "api",
                       "email_api_key": "re_test", "email_api_from": "blog@example.com"})
    yield sent
    settings.set_many(before)
    db = get_db()
    for table in ("members", "member_tokens", "member_sessions"):
        db.execute(f"DELETE FROM {table}")  # noqa: S608 - fixed table names
    # the subscribers these tests made - the newsletter's own tests count them
    db.execute("DELETE FROM subscribers WHERE id > ?", (last_subscriber,))
    db.commit()


def _signed_in(app, sent, email="reader@example.com", name="Reader"):
    """A visitor who joins through the real flow - returns their client."""
    c = TestClient(app, follow_redirects=False)
    r = c.post("/join", data={"email": email, "name": name})
    assert r.status_code == 303 and r.headers["location"] == "/signin/check"
    r = c.post("/signin/link", data={"token": sent[-1]["token"]})
    assert r.status_code == 303 and members.COOKIE in r.cookies
    return c


def test_off_by_default_and_everything_public(client, admin):
    before = settings.get("members_enabled")
    try:
        settings.set_many({"members_enabled": "0"})
        for path in ("/join", "/signin", "/account"):
            assert client.get(path).status_code == 404, path
        slug = save_post(admin, title="Paid but off", body=BODY, visibility="paid")
        # with members off, a post for members is open to everyone
        assert SECRET in client.get(f"/post/{slug}").text
        assert 'href="/login"' in client.get("/").text and 'href="/signin"' not in client.get("/").text
    finally:
        settings.set_many({"members_enabled": before})


def test_joining_by_the_emailed_link(app, client, on):
    r = client.post("/join", data={"email": "Mira@Example.com", "name": "Mira"})
    assert r.status_code == 303 and r.headers["location"] == "/signin/check"
    assert on[-1]["purpose"] == "signup" and on[-1]["email"] == "Mira@example.com"
    # not a member until the link's used
    assert members.by_email("mira@example.com") is None
    # the link opens a page that signs in with a press - scanners don't use it up
    page = client.get(f"/signin/link?token={on[-1]['token']}").text
    assert 'action="/signin/link"' in page and on[-1]["token"] in page
    assert members.by_email("mira@example.com") is None
    r = client.post("/signin/link", data={"token": on[-1]["token"]})
    assert r.status_code == 303 and r.headers["location"] == "/account"
    cookie = r.headers["set-cookie"]
    assert members.COOKIE in cookie and "HttpOnly" in cookie and "samesite=lax" in cookie.lower()
    member = members.by_email("mira@example.com")
    assert member and member["name"] == "Mira" and member["status"] == "free"
    account = client.get("/account").text
    assert "mira@example.com" in account.lower() and "Free member" in account
    # the header says so
    assert 'href="/account"' in client.get("/").text
    # the same link a second time: no
    again = TestClient(app, follow_redirects=False)
    r = again.post("/signin/link", data={"token": on[-1]["token"]})
    assert r.status_code == 200 and "run out" in r.text and members.COOKIE not in r.cookies


def test_the_code_beside_the_link(app, on):
    _signed_in(app, on, "coder@example.com")
    c = TestClient(app, follow_redirects=False)
    c.post("/signin", data={"email": "coder@example.com"})
    code = on[-1]["code"]
    wrong = "000000" if code != "000000" else "111111"
    # four wrong guesses, then the right one still works
    for _ in range(4):
        assert c.post("/signin/code", data={"code": wrong}).headers["location"] == "/signin/check?error=code"
    r = c.post("/signin/code", data={"code": code})
    assert r.status_code == 303 and r.headers["location"] == "/account"
    # the fifth wrong guess ends it - the right code is no good after
    get_db().execute("DELETE FROM rate_hits")
    get_db().commit()
    c2 = TestClient(app, follow_redirects=False)
    c2.post("/signin", data={"email": "coder@example.com"})
    code = on[-1]["code"]
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(5):
        c2.post("/signin/code", data={"code": wrong})
    assert c2.post("/signin/code", data={"code": code}).headers["location"] == "/signin/check?error=code"
    # a code is only good for the address it went to
    get_db().execute("DELETE FROM rate_hits")
    get_db().commit()
    c3 = TestClient(app, follow_redirects=False)
    c3.post("/signin", data={"email": "coder@example.com"})
    stolen = on[-1]["code"]
    c4 = TestClient(app, follow_redirects=False)
    c4.cookies.set("soloblog_member_pending", "someone-else@example.com")
    assert c4.post("/signin/code", data={"code": stolen}).headers["location"] == "/signin/check?error=code"


def test_expired_and_replaced_links(app, on):
    _signed_in(app, on, "late@example.com")
    c = TestClient(app, follow_redirects=False)
    c.post("/signin", data={"email": "late@example.com"})
    first = on[-1]["token"]
    get_db().execute("UPDATE member_tokens SET expires_at=? WHERE used_at IS NULL",
                     ((utcnow() - timedelta(minutes=1)).isoformat(),))
    get_db().commit()
    assert members.COOKIE not in c.post("/signin/link", data={"token": first}).cookies
    # asking again replaces the one before (the hourly limit aside - that's tested on its own)
    get_db().execute("DELETE FROM rate_hits")
    get_db().commit()
    c.post("/signin", data={"email": "late@example.com"})
    older = on[-1]["token"]
    c.post("/signin", data={"email": "late@example.com"})
    assert members.COOKIE not in c.post("/signin/link", data={"token": older}).cookies
    assert members.COOKIE in c.post("/signin/link", data={"token": on[-1]["token"]}).cookies


def test_signing_in_says_nothing_about_who_is_a_member(client, on):
    """The same answer for a member's address and anyone else's - anyone
    else gets an email saying there's no account, with no way in."""
    r = client.post("/signin", data={"email": "nobody@example.com"})
    assert r.status_code == 303 and r.headers["location"] == "/signin/check"
    assert on == [{"email": "nobody@example.com", "purpose": "none"}]
    # and nothing about it can be learned by asking - three an hour per address
    for _ in range(3):
        client.post("/join", data={"email": "flood@example.com"})
    r = client.post("/join", data={"email": "flood@example.com"})
    assert "error=limit" in r.headers["location"] and len(on) == 4
    for _ in range(3):
        client.post("/signin", data={"email": "flood2@example.com"})
    assert "error=limit" in client.post("/signin", data={"email": "flood2@example.com"}).headers["location"]
    assert len(on) == 7


def test_the_no_account_email(monkeypatch):
    from soloblog import mail
    from soloblog.routes import members_routes
    sent = []
    monkeypatch.setattr(mail, "send_email", lambda to, subject, body: sent.append((to, subject, body)))
    monkeypatch.setattr(members_routes.threading, "Thread",
                        lambda target, args, daemon: type("T", (), {"start": lambda self: target(*args)})())
    members_routes._no_account("nobody@example.com", {"site_title": "Mira's"})
    to, subject, body = sent[0]
    assert to == "nobody@example.com" and subject == "Sign in to Mira's"
    assert "no account" in body and "/join" in body and "/signin/link" not in body


def test_only_ever_back_to_this_site():
    for bad in ("//evil.example", "https://evil.example/", "/\\evil.example", "javascript:alert(1)"):
        assert members.safe_next(bad) == "", bad
    assert members.safe_next("/post/hello") == "/post/hello"


def test_who_can_read_what(app, admin, client, on):
    member_slug = save_post(admin, title="For members", body=BODY, visibility="members")
    paid_slug = save_post(admin, title="For paid members", body=BODY, visibility="paid")
    # a visitor: the preview, the card to join, no comments, never cached
    r = client.get(f"/post/{member_slug}")
    assert "Everyone can read this first part." in r.text and SECRET not in r.text
    assert "This post is for members" in r.text and 'href="/join?next=' in r.text
    assert 'id="comments"' not in r.text and r.headers["cache-control"] == "private, no-store"
    assert '"isAccessibleForFree": false' in r.text and "members-only" in r.text
    # a free member reads the members post, not the paid one
    reader = _signed_in(app, on, "free@example.com")
    assert SECRET in reader.get(f"/post/{member_slug}").text
    paid = reader.get(f"/post/{paid_slug}").text
    assert SECRET not in paid and "This post is for paid members" in paid and "free@example.com" in paid
    # paid access given by the admin opens it; so does being the admin
    members.update(members.by_email("free@example.com")["id"], status="comped")
    assert SECRET in reader.get(f"/post/{paid_slug}").text
    assert SECRET in admin.get(f"/post/{paid_slug}").text
    # without a cut, the summary is the preview
    no_cut = save_post(admin, title="No cut", summary="What it's about.", body=SECRET, visibility="members")
    page = client.get(f"/post/{no_cut}").text
    assert "What it's about." in page and SECRET not in page
    # kept in the post's own file, and back from it
    assert "visibility: paid" in Path(posts._path(paid_slug)).read_text(encoding="utf-8")


def test_the_rest_never_leaves_the_site(app, admin, client, on, monkeypatch):
    from soloblog import fediverse, newsletter
    slug = save_post(admin, title="Members only sketch", body=BODY, visibility="members")
    row = posts.get_post(slug)
    for feed in ("/rss", "/atom.xml", "/feed.json"):
        text = client.get(feed).text
        assert "Everyone can read this first part." in text and SECRET not in text, feed
        assert "This post is for members." in text, feed
    assert SECRET not in json.dumps(fediverse.post_object(row))
    # search finds only what anyone may read: its first part, not the rest
    assert slug not in [r["slug"] for r in posts.search("Junior")]
    assert slug in [r["slug"] for r in posts.search("Everyone")]
    assert "Members only sketch" not in client.get("/search?q=Junior").text
    # the newsletter: all of it to a member, the preview to anyone else
    settings.set_many({"newsletter_mode": "builtin", "newsletter_full": "1"})
    member = _signed_in(app, on, "letter@example.com")  # noqa: F841
    got = {}
    monkeypatch.setattr("soloblog.mail.send_email", lambda to, subject, body, headers=None, **kw: got.__setitem__(to, body) or True)
    subs = [{"email": "letter@example.com", "token": "t1"}, {"email": "stranger@example.com", "token": "t2"}]
    newsletter.send_post(row, to=subs)
    assert SECRET in got["letter@example.com"]
    assert SECRET not in got["stranger@example.com"] and "This post is for members." in got["stranger@example.com"]


def test_a_member_is_never_the_admin(app, on):
    reader = _signed_in(app, on, "notadmin@example.com")
    for path in ("/admin/posts", "/admin/members", "/admin/settings"):
        r = reader.get(path)
        assert r.status_code in (302, 303) and "/login" in r.headers["location"], path
    assert reader.post("/admin/members/add", data={"email": "x@example.com"}).status_code in (302, 303)
    assert members.by_email("x@example.com") is None


def test_the_account_page(app, on):
    reader = _signed_in(app, on, "acct@example.com", name="Ann")
    reader.post("/account/name", data={"name": "Ann Lee"})
    assert members.by_email("acct@example.com")["name"] == "Ann Lee"
    data = reader.get("/account/data")
    assert data.headers["content-disposition"].startswith("attachment") and data.json()["email"] == "acct@example.com"
    # signed out: the cookie no longer works
    reader.post("/signout")
    assert reader.get("/account").headers["location"] == "/signin?next=/account"
    # everywhere: every other browser too
    one, two = _signed_in(app, on, "two@example.com"), None
    two = TestClient(app, follow_redirects=False)
    two.post("/signin", data={"email": "two@example.com"})
    two.post("/signin/link", data={"token": on[-1]["token"]})
    assert two.get("/account").status_code == 200
    one.post("/account/signout-everywhere")
    assert two.get("/account").status_code == 303
    # deleting: gone, and signed out
    three = _signed_in(app, on, "bye@example.com")
    three.post("/account/delete")
    assert members.by_email("bye@example.com") is None and three.get("/account").status_code == 303


def test_subscribers_become_members(admin, on):
    from soloblog import newsletter
    settings.set_many({"members_enabled": "0", "newsletter_mode": "builtin"})
    token = newsletter.subscribe("subscriber@example.com")
    newsletter.confirm(token)
    assert members.by_email("subscriber@example.com") is None
    r = admin.post("/admin/settings/members", headers={"HX-Request": "true"},
                   data={"members_enabled": "1", "declared_fields": "members_enabled"})
    assert "now a member" in r.text or "now members" in r.text
    assert members.by_email("subscriber@example.com")["status"] == "free"
    # and each new one as they confirm
    newsletter.confirm(newsletter.subscribe("later@example.com"))
    assert members.by_email("later@example.com")


def test_admin_members_page(admin, client, on):
    assert client.get("/admin/members").status_code in (302, 303)
    admin.post("/admin/members/add", data={"email": "gift@example.com", "name": "Gift", "comp": "1"})
    m = members.by_email("gift@example.com")
    assert m["status"] == "comped" and members.has_paid(m)
    page = admin.get("/admin/members").text
    assert "gift@example.com" in page and "Paid · given" in page
    assert "gift@example.com" in admin.get("/admin/members?status=paid").text
    assert "gift@example.com" not in admin.get("/admin/members?status=free").text
    admin.post(f"/admin/members/{m['id']}/comp", data={"on": ""})
    assert members.by_email("gift@example.com")["status"] == "free"
    admin.post(f"/admin/members/{m['id']}/remove")
    assert members.by_email("gift@example.com") is None
    # the editor offers who can read it
    assert 'name="visibility"' in admin.get("/admin/new").text


def test_the_cut_line():
    preview, rest = posts.split_members("A\n\n<!-- members -->\n\nB")
    assert (preview, rest) == ("A", "B")
    assert posts.split_members("A\n\n<!--Members only from here-->\nB")[0] == "A"
    # inside text it's not a cut
    assert posts.split_members("A <!-- members --> B") == ("", "A <!-- members --> B")


def _comments_by(slug):
    return get_db().execute("SELECT * FROM comments WHERE post_slug=? ORDER BY id", (slug,)).fetchall()


def test_comments_for_members(app, admin, client, on):
    settings.set_many({"members_comments": "members", "comments_enabled": "1"})
    slug = save_post(admin, title="Talk to me", body="Open to all.")
    page = client.get(f"/post/{slug}").text
    assert "Only members can comment." in page and 'name="author_name"' not in page
    # posted straight at the route anyway: refused, nothing kept
    r = client.post(f"/post/{slug}/comment", data={"author_name": "Bot", "email": "bot@example.com", "body": "Hi"},
                    headers={"HX-Request": "true"})
    assert "Only members can comment." in r.text and not _comments_by(slug)
    # a member: known already - no email, no spam check, no confirming
    c = _signed_in(app, on, "talker@example.com", "Talia")
    page = c.get(f"/post/{slug}").text
    assert "Commenting as Talia" in page and 'name="email"' not in page
    c.post(f"/post/{slug}/comment", data={"body": "Lovely post", "email": "someone-else@example.com"},
           headers={"HX-Request": "true"})
    [comment] = _comments_by(slug)
    member = members.by_email("talker@example.com")
    assert comment["member_id"] == member["id"] and comment["email"] == "talker@example.com"
    assert comment["author_name"] == "Talia" and comment["confirmed_at"] and not comment["approved"]
    # paid members only: a free member is asked to pay
    settings.set_many({"members_comments": "paid"})
    assert "Only paid members can comment." in c.get(f"/post/{slug}").text
    r = c.post(f"/post/{slug}/comment", data={"body": "Again"}, headers={"HX-Request": "true"})
    assert "Only paid members" in r.text and len(_comments_by(slug)) == 1


def test_a_member_without_a_name_gives_one(app, admin, on):
    settings.set_many({"members_comments": "everyone", "comments_enabled": "1"})
    slug = save_post(admin, title="Names please", body="Hello.")
    c = _signed_in(app, on, "noname@example.com", "")
    page = c.get(f"/post/{slug}").text
    assert 'name="author_name"' in page and 'name="email"' not in page
    c.post(f"/post/{slug}/comment", data={"author_name": "Nadia", "body": "Hi"}, headers={"HX-Request": "true"})
    assert members.by_email("noname@example.com")["name"] == "Nadia"
    assert _comments_by(slug)[0]["author_name"] == "Nadia"


def test_no_comments_on_a_post_they_cant_read(app, admin, on):
    settings.set_many({"members_comments": "everyone", "comments_enabled": "1"})
    slug = save_post(admin, title="Paid talk", body=BODY, visibility="paid")
    c = _signed_in(app, on, "freebie@example.com")
    c.post(f"/post/{slug}/comment", data={"body": "Let me in"}, headers={"HX-Request": "true"})
    assert not _comments_by(slug)


def test_a_members_pages_arent_cached(app, on):
    c = _signed_in(app, on, "private@example.com")
    for path in ("/", "/account"):
        assert "no-store" in c.get(path).headers.get("cache-control", ""), path


def test_members_csv_out_and_back_in(admin, on):
    members.add("csv-one@example.com", "=HYPERLINK(\"http://evil\")")
    members.add("csv-two@example.com", "Two", "comped")
    assert "/admin/members/export" not in admin.get("/admin/members").text
    r = admin.post("/admin/members/bulk", data={"action": "export", "all_matching": "1"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    text = r.text
    assert text.splitlines()[0].startswith("email,name,status")
    # a name that would run as a formula in a spreadsheet doesn't
    assert "'=HYPERLINK" in text and ",=HYPERLINK" not in text
    db = get_db()
    db.execute("DELETE FROM members")
    db.commit()
    # back in: the same people, paid access kept, the name as it was
    r = admin.post("/admin/members/import", files={"csv": ("members.csv", text.encode(), "text/csv")})
    assert r.status_code == 303
    assert members.by_email("csv-two@example.com")["status"] == "comped"
    assert members.by_email("csv-one@example.com")["name"].startswith("=HYPERLINK")
    # again: all skipped; and Ghost's own columns
    assert members.import_csv(text) == (0, 2)
    ghost = "id,email,name,note,subscribed_to_emails,complimentary_plan\n1,g@example.com,Gee,,true,true\n" \
            "2,not-an-email,X,,true,false\n"
    assert members.import_csv(ghost) == (1, 1)
    assert members.by_email("g@example.com")["status"] == "comped"


def test_members_csv_is_the_admins(client):
    r = client.post("/admin/members/bulk", data={"action": "export", "all_matching": "1"})
    assert r.status_code in (302, 303) and "csv" not in r.headers.get("content-type", "")
    r = client.post("/admin/members/import", files={"csv": ("m.csv", b"email\nx@example.com\n", "text/csv")})
    assert r.status_code in (302, 303, 403) and not members.by_email("x@example.com")


def test_the_editor_preview_shows_the_line(admin):
    html = admin.post("/admin/preview", data={"body": BODY}).text
    assert "Members only from here" in html and SECRET in html and "SOLOBLOGMEMBERSCUT" not in html
    assert html.index("Everyone can read") < html.index("Members only from here") < html.index("Gerald")
    # as a browser sends it: Windows line endings
    html = admin.post("/admin/preview", files={"body": (None, BODY.replace("\n", "\r\n"))}).text
    assert "Members only from here" in html
    assert posts.split_members(BODY.replace("\n", "\r\n"))[0].strip() == "Everyone can read this first part."


def test_the_welcome_email_once_on_joining(app, on, monkeypatch):
    from soloblog import mail
    from soloblog.routes import members_routes
    sent = []

    class Now:
        def __init__(self, target, args, daemon=True):
            self.go = lambda: target(*args)

        def start(self):
            self.go()
    monkeypatch.setattr(members_routes.threading, "Thread", Now)
    monkeypatch.setattr(mail, "send_email", lambda to, subject, body, **kw: sent.append((to, subject, body)))
    settings.set_many({"members_welcome": ""})
    _signed_in(app, on, "quiet@example.com")
    assert not sent
    settings.set_many({"members_welcome": "Start with the bread posts."})
    c = _signed_in(app, on, "welcome@example.com")
    [(to, subject, body)] = sent
    assert to == "welcome@example.com" and subject.startswith("Welcome to") and "Start with the bread" in body
    # signing in again later: no second welcome
    c.post("/signout")
    c.post("/signin", data={"email": "welcome@example.com"})
    c.post("/signin/link", data={"token": on[-1]["token"]})
    assert len(sent) == 1


def test_posts_list_pills_and_who_can_read_filter(admin, on):
    free = save_post(admin, title="Open to all of them", body="Hi.")
    paid = save_post(admin, title="Only for the paying few", body=BODY, visibility="paid")
    page = admin.get("/admin/posts?access=paid").text
    assert "Only for the paying few" in page and "Open to all of them" not in page
    assert ">Readers" in page and "for paid members" in page
    assert ">Paid members</span>" in page and ">Published</span>" in page and ">Post</span>" in page
    page = admin.get("/admin/posts?access=public").text
    assert "Open to all of them" in page and "Only for the paying few" not in page
    assert free and paid


def test_comments_admin_shows_members(app, admin, on):
    settings.set_many({"members_comments": "everyone", "comments_enabled": "1"})
    slug = save_post(admin, title="Pill talk", body="Hello.")
    c = _signed_in(app, on, "pill@example.com", "Pip")
    c.post(f"/post/{slug}/comment", data={"body": "Hi from a member"}, headers={"HX-Request": "true"})
    page = admin.get("/admin/comments").text
    i = page.index("Hi from a member")
    assert ">Member</span>" in page[max(0, i - 3000):i]
    members.update(members.by_email("pill@example.com")["id"], status="comped")
    page = admin.get("/admin/comments").text
    i = page.index("Hi from a member")
    assert ">Paid member</span>" in page[max(0, i - 3000):i]


def test_lists_show_only_the_free_part(admin, client):
    """A post list's line under the title is public - for a members post
    without a summary it's the free preview, or nothing; never the rest."""
    from soloblog import settings
    before = settings.get("members_enabled")
    settings.set_many({"members_enabled": "1"})
    try:
        save_post(admin, title="Locked through and through", tags="lockedtag", visibility="members",
                  body="LOCKEDTEXT every word of it is for members.")
        save_post(admin, title="Free start then locked", tags="lockedtag", visibility="paid",
                  body="FREESTART anyone may read this.\n\n<!-- members only from here -->\n\nPAIDTEXT the rest.")
        for path in ("/", "/search?q=locked", "/tag/lockedtag"):
            page = client.get(path).text
            assert "LOCKEDTEXT" not in page and "PAIDTEXT" not in page, path
        assert "FREESTART" in client.get("/tag/lockedtag").text
    finally:
        settings.set_many({"members_enabled": before or "0"})


def test_ticking_members(admin, on):
    members.add("tick-one@example.com", "One")
    two = members.add("tick-two@example.com", "Two", "comped")
    paying = members.add("tick-paying@example.com", "Pays")
    members.update(paying["id"], status="paid", stripe_subscription_id="sub_1", subscription_status="active")
    try:
        html = admin.get("/admin/members").text
        assert 'id="members-bulk"' in html and "Remove" in html
        csv = admin.post("/admin/members/bulk", data={"action": "export", "ids": [two["id"]]}).text
        assert "tick-two@example.com" in csv and "tick-one@example.com" not in csv
        # someone on a live plan stays - they'd go on being charged
        r = admin.post("/admin/members/bulk", data={"action": "remove", "all_matching": "1", "in_q": "tick-"})
        assert "Removed 2 members" in unquote(r.headers["location"]) and "live plan" in unquote(r.headers["location"])
        assert members.by_email("tick-paying@example.com") and not members.by_email("tick-one@example.com")
    finally:
        get_db().execute("DELETE FROM members WHERE email LIKE 'tick-%'")
        get_db().commit()


def test_keep_me_signed_in(app, on):
    c = TestClient(app, follow_redirects=False)
    assert 'name="keep" value="1" checked' in c.get("/signin").text
    c.post("/join", data={"email": "kept@example.com"})
    c.post("/signin/link", data={"token": on[-1]["token"]})
    for data, lasting in (({"email": "kept@example.com", "keep": "1"}, True), ({"email": "kept@example.com"}, False)):
        c = TestClient(app, follow_redirects=False)
        c.post("/signin", data=data)
        r = c.post("/signin/link", data={"token": on[-1]["token"]})
        cookie = next(v for k, v in r.headers.multi_items() if k == "set-cookie" and v.startswith(members.COOKIE))
        assert ("Max-Age=" in cookie) == lasting, cookie


def test_with_members_on_the_newsletter_box_joins(app, admin, client, on):
    """One list, as Ghost has it: a visitor's box under a post joins them,
    ticking new posts by email; a member already getting them sees none."""
    from soloblog import newsletter
    before = settings.get("newsletter_mode")
    settings.set_many({"newsletter_mode": "builtin"})
    try:
        slug = save_post(admin, title="Joining from the box")
        # the box under posts and at /newsletter is the same (an earlier test
        # may have turned it off under posts)
        page = client.get("/newsletter").text
        box = page[page.index('id="newsletter"'):]
        box = box[:box.index("</form>")]
        assert 'action="/join"' in box and 'name="newsletter" value="1" checked' in box
        c = TestClient(app, follow_redirects=False)
        r = c.post("/join", data={"email": "boxed@example.com", "newsletter": "1"})
        assert r.headers["location"] == "/signin/check"
        c.post("/signin/link", data={"token": on[-1]["token"]})
        assert newsletter.is_subscribed("boxed@example.com")
        assert c.get("/newsletter").headers["location"] == "/account"
        assert slug
        # members off: the newsletter's own box again
        settings.set_many({"members_enabled": "0"})
        assert 'hx-post="/newsletter/subscribe"' in client.get("/newsletter").text
    finally:
        settings.set_many({"newsletter_mode": before})
