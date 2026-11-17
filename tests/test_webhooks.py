"""Webhooks (webhooks.py) and the API's comments: what's sent and when,
that it's signed, retried and never sent inside the server's network -
and that turning one on doesn't flood it with every old post."""
import hashlib
import hmac
import json
import urllib.error

import pytest
from starlette.testclient import TestClient

from soloblog import apikeys
from soloblog import comments
from soloblog import notify
from soloblog import publishing
from soloblog import webhooks
from soloblog.db import get_db
from conftest import save_post


class Receiver:
    """Catches what would go out, and answers as told."""
    def __init__(self):
        self.got, self.answers = [], []

    def __call__(self, req, timeout=10):
        self.got.append(req)
        answer = self.answers.pop(0) if self.answers else 200
        if isinstance(answer, Exception):
            raise answer
        if answer >= 400:
            raise urllib.error.HTTPError(req.full_url, answer, "no", {}, None)

        class Resp:
            status = answer

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        return Resp()


@pytest.fixture
def hooks(monkeypatch):
    r = Receiver()
    monkeypatch.setattr(webhooks.netguard, "open_url", r)
    monkeypatch.setattr(webhooks.netguard, "check_url", lambda url: None if "127.0.0.1" not in url else
                        (_ for _ in ()).throw(webhooks.netguard.PrivateAddress("127.0.0.1 is a private address")))
    monkeypatch.setattr(webhooks.time, "sleep", lambda s: None)

    class Now:
        def __init__(self, target, args, daemon=True):
            self.run = lambda: target(*args)

        def start(self):
            self.run()
    monkeypatch.setattr(webhooks.threading, "Thread", Now)
    yield r
    db = get_db()
    db.execute("DELETE FROM webhooks")
    db.execute("DELETE FROM published_log WHERE channel='webhook'")
    db.execute("DELETE FROM api_keys")
    db.commit()


def _event(req):
    return json.loads(req.data)


def test_what_can_be_added(hooks):
    assert "https://" in webhooks.add("ftp://example.com/x", ["post.published"])
    assert "private address" in webhooks.add("http://127.0.0.1/hook", ["post.published"])
    assert "at least one" in webhooks.add("https://hooks.example.com/a", ["nonsense"])
    assert webhooks.add("https://hooks.example.com/a", ["post.published", "comment.created"]) == ""


def test_a_new_post_is_sent_once_and_signed(admin, hooks):
    old = save_post(admin, title="Already live before the hook", body="Old.")
    publishing.check()
    webhooks.add("https://hooks.example.com/a", ["post.published"])
    publishing.check()
    assert not hooks.got  # nothing from the back catalogue
    new = save_post(admin, title="Fresh off the press", body="New.")
    publishing.check()
    publishing.check()  # and only once
    assert len(hooks.got) == 1
    req = hooks.got[0]
    event = _event(req)
    assert event["event"] == "post.published" and event["data"]["slug"] == new and old != new
    stamp, sig = (p.split("=", 1)[1] for p in req.headers["X-soloblog-signature"].split(","))
    hook = webhooks.listed()[0]
    expected = hmac.new(webhooks.secret_for(hook["id"]).encode(), f"{stamp}.".encode() + req.data,
                        hashlib.sha256).hexdigest()
    assert sig == expected and req.headers["X-soloblog-event"] == "post.published"


def test_comments_and_retries(hooks):
    webhooks.add("https://hooks.example.com/c", ["comment.created"])
    hooks.answers = [urllib.error.URLError("down"), 503, 200]
    notify.comment_waiting("some-post", "Ada", "Lovely post")
    assert len(hooks.got) == 3
    event = _event(hooks.got[-1])
    assert event["event"] == "comment.created" and event["data"]["author"] == "Ada"
    assert "email" not in json.dumps(event["data"])
    assert webhooks.listed()[0]["last_status"] == 200
    hooks.answers = [500, 500, 500]
    notify.comment_waiting("some-post", "Bo", "Hi")
    assert webhooks.listed()[0]["last_status"] == 500 and "500" in webhooks.listed()[0]["last_error"]


def test_the_settings_panel(admin, hooks):
    page = admin.post("/admin/webhooks/add", data={"url": "https://hooks.example.com/p", "events": ["comment.created"]},
                      headers={"HX-Request": "true"}).text
    assert "hooks.example.com/p" in page and "whsec_" in page
    hook = webhooks.listed()[0]
    page = admin.post(f"/admin/webhooks/{hook['id']}/test", headers={"HX-Request": "true"}).text
    assert "Test sent - it answered 200" in page and _event(hooks.got[-1])["event"] == "ping"
    assert "private address" in admin.post("/admin/webhooks/add", data={"url": "http://127.0.0.1/x",
                                                                        "events": ["comment.created"]}).text
    admin.post(f"/admin/webhooks/{hook['id']}/remove", headers={"HX-Request": "true"})
    assert not webhooks.listed()


def test_moderating_comments_through_the_api(app, admin, hooks):
    slug = save_post(admin, title="Talk about this", body="Hi.")
    token = comments.add_comment(slug, "Reader", "r@example.com", "Hello there", auto_confirm=True)
    cid = get_db().execute("SELECT id FROM comments WHERE confirm_token=?", (token,)).fetchone()["id"]
    read, drafts, publish = (apikeys.create(s, s) for s in ("read", "draft", "publish"))
    as_ = lambda key: TestClient(app, headers={"Authorization": f"Bearer {key}"})  # noqa: E731
    waiting = as_(read).get("/api/v1/comments?status=pending").json()["comments"]
    assert any(c["id"] == cid and c["body"] == "Hello there" and "email" not in c for c in waiting)
    assert as_(drafts).post(f"/api/v1/comments/{cid}/approve").status_code == 403
    assert as_(publish).post(f"/api/v1/comments/{cid}/approve").json()["status"] == "approved"
    assert as_(publish).delete(f"/api/v1/comments/{cid}").json() == {"trashed": cid}
    assert as_(read).get("/api/v1/comments?status=nope").status_code == 400


def test_chat_notices_name_the_app(monkeypatch):
    # Discord's firewall refuses Python's default name (error 1010)
    sent = []
    monkeypatch.setattr(notify.netguard, "open_url", lambda req, timeout=5: sent.append(req))
    notify.notify("https://discord.com/api/webhooks/1/x", "A message")
    notify.notify_new_comment("https://hooks.slack.com/x", "post", "Ada", "Hi")
    assert [r.get_header("User-agent") for r in sent] == ["Soloblog", "Soloblog"]


def test_a_failed_chat_notice_is_logged_not_raised(monkeypatch, caplog):
    import logging

    def refuse(req, timeout=5):
        raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)
    monkeypatch.setattr(notify.netguard, "open_url", refuse)
    with caplog.at_level(logging.WARNING, logger="soloblog.notify"):
        notify.notify("https://discord.com/api/webhooks/1/secret-token", "A message")
    logged = " ".join(r.getMessage() for r in caplog.records)
    # where and what it answered - never the address, whose path is its password
    assert "discord.com" in logged and "404" in logged and "secret-token" not in logged


def test_chat_notices_use_the_field_each_app_reads(monkeypatch):
    # Discord refuses a message without "content"; Slack reads "text"
    sent = []
    monkeypatch.setattr(notify.netguard, "open_url", lambda req, timeout=5: sent.append(json.loads(req.data)))
    notify.notify("https://discord.com/api/webhooks/1/x", "A message")
    notify.notify("https://discordapp.com/api/webhooks/1/x", "Old address")
    notify.notify_new_comment("https://hooks.slack.com/x", "A post", "Ada", "Hi")
    assert sent[:2] == [{"content": "A message"}, {"content": "Old address"}]
    assert sent[2]["text"].startswith("Ada commented on “A post”: Hi\nApprove or trash it: ")


def test_the_comment_notice_names_the_post_by_its_title(admin, monkeypatch):
    # it named the post by its address ("my-sourdough-starter-has-...")
    from conftest import save_post
    slug = save_post(admin, title="Bread at dawn")
    sent = []
    monkeypatch.setattr(notify, "notify_new_comment", lambda url, title, *a: sent.append(title))
    notify.comment_waiting(slug, "Ada", "Lovely")
    assert sent == ["Bread at dawn"]
