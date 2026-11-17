import contextlib
import base64
import hashlib
import json
from datetime import datetime, UTC
from soloblog.tz import utcnow
from email.utils import format_datetime

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from soloblog import comments
from soloblog import config
from soloblog import fediverse
from soloblog import publishing
from soloblog import settings
from soloblog import webmention
from conftest import save_post

REMOTE = "https://social.example/users/ann"
REMOTE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
REMOTE_ACTOR = {
    "id": REMOTE, "type": "Person", "preferredUsername": "ann", "name": "Ann",
    "url": "https://social.example/@ann", "inbox": f"{REMOTE}/inbox",
    "endpoints": {"sharedInbox": "https://social.example/inbox"},
    "icon": {"type": "Image", "url": "https://social.example/ann.png"},
    "publicKey": {"id": f"{REMOTE}#main-key", "owner": REMOTE, "publicKeyPem": REMOTE_KEY.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()},
}
AP = {"Accept": "application/activity+json"}


def _signed(activity, key=REMOTE_KEY):
    """What Mastodon would send: a JSON body signed with the sender's key."""
    body = json.dumps(activity).encode()
    date = format_datetime(datetime.now(UTC), usegmt=True)
    digest = "SHA-256=" + base64.b64encode(hashlib.sha256(body).digest()).decode()
    signing = f"(request-target): post /ap/inbox\nhost: testserver\ndate: {date}\ndigest: {digest}"
    sig = base64.b64encode(key.sign(signing.encode(), padding.PKCS1v15(), hashes.SHA256())).decode()
    return body, {"Date": date, "Digest": digest, "Content-Type": "application/activity+json",
                  "Signature": f'keyId="{REMOTE}#main-key",algorithm="rsa-sha256",'
                               f'headers="(request-target) host date digest",signature="{sig}"'}


@pytest.fixture
def fedi(monkeypatch):
    monkeypatch.setattr(config, "BASE_URL", "https://blog.example")
    monkeypatch.setattr(fediverse, "fetch_actor", lambda url, refresh=False: REMOTE_ACTOR)
    sent = []
    monkeypatch.setattr(fediverse, "signed_post", lambda url, doc: sent.append((url, doc)) or 202)
    before = settings.get_all()
    settings.set_many({"activitypub_enabled": "1", "activitypub_username": "blog"})
    yield sent
    fediverse.wait()
    settings.set_many({k: before[k] for k in ("activitypub_enabled", "activitypub_username", "webmention_receive",
                                              "webmention_send", "webmention_moderate")})


def _inbox(client, activity, key=REMOTE_KEY):
    body, headers = _signed(activity, key)
    r = client.post("/ap/inbox", content=body, headers=headers)
    fediverse.wait()
    return r


def test_discovery(client, admin, fedi):
    jrd = client.get("/.well-known/webfinger?resource=acct:blog@blog.example").json()
    assert jrd["links"][0]["href"] == "https://blog.example/ap/actor"
    assert client.get("/.well-known/webfinger?resource=acct:other@blog.example").status_code == 404
    actor = client.get("/ap/actor", headers=AP).json()
    assert actor["type"] == "Person" and actor["preferredUsername"] == "blog"
    assert "BEGIN PUBLIC KEY" in actor["publicKey"]["publicKeyPem"]
    assert client.get("/", headers=AP).json()["id"] == actor["id"]
    assert client.get("/.well-known/nodeinfo").json()["links"][0]["href"].endswith("/nodeinfo/2.0")
    slug = save_post(admin, title="Federated post", tags="fedi, test", summary="Short")
    obj = client.get(f"/post/{slug}", headers=AP).json()
    assert obj["type"] == "Article" and obj["name"] == "Federated post" and obj["id"].endswith(f"/post/{slug}")
    assert {t["name"] for t in obj["tag"]} == {"#fedi", "#test"} and "summary" not in obj
    # a normal visit still gets the page
    assert "<html" in client.get(f"/post/{slug}").text


def test_follow_publish_reply_like_and_undo(client, admin, fedi):
    sent = fedi
    publishing.baseline("activitypub")  # what's already live counts as announced
    _inbox(client, {"id": "https://social.example/f1", "type": "Follow", "actor": REMOTE,
                    "object": "https://blog.example/ap/actor"})
    assert fediverse.follower_count() == 1
    accept = [d for u, d in sent if d["type"] == "Accept"]
    assert accept and sent[0][0] == f"{REMOTE}/inbox"

    sent.clear()
    slug = save_post(admin, title="Hello followers")
    publishing.check()
    fediverse.wait()
    create = [(u, d) for u, d in sent if d["type"] == "Create"]
    assert create and create[0][0] == "https://social.example/inbox"
    assert create[0][1]["object"]["name"] == "Hello followers"
    # nothing changed - nothing is sent again
    sent.clear()
    publishing.check()
    fediverse.wait()
    assert not sent

    # a reply comes in as a comment waiting for approval
    note = {"id": "https://social.example/notes/1", "type": "Note", "attributedTo": REMOTE,
            "inReplyTo": f"https://blog.example/post/{slug}", "content": "<p>Lovely <b>post</b></p>"}
    _inbox(client, {"id": "https://social.example/c1", "type": "Create", "actor": REMOTE, "object": note})
    row = comments.get_db().execute("SELECT * FROM comments WHERE source_url=?", (note["id"],)).fetchone()
    assert row and row["body"] == "Lovely post" and row["source"] == "activitypub" and not row["approved"]
    admin.post("/admin/comments/approve", data={"comment_id": row["id"]})
    page = client.get(f"/post/{slug}").text
    assert "Lovely post" in page and ">fediverse<" in page and 'href="https://social.example/@ann"' in page

    # the author's reply goes back to Ann
    sent.clear()
    comments.get_db().execute("INSERT OR REPLACE INTO ap_actors (id, data, fetched_at) VALUES (?, ?, ?)",
                              (REMOTE, json.dumps(REMOTE_ACTOR), utcnow().isoformat()))
    comments.get_db().commit()
    admin.post(f"/post/{slug}/reply", data={"parent_id": row["id"], "body": "Thank you!"})
    fediverse.wait()
    reply = [d for u, d in sent if d["type"] == "Create" and d["object"]["type"] == "Note"]
    assert reply and reply[0]["object"]["inReplyTo"] == note["id"] and "Thank you!" in reply[0]["object"]["content"]
    note_id = reply[0]["object"]["id"]
    assert client.get(note_id.replace("https://blog.example", ""), headers=AP).json()["type"] == "Note"

    # favourites are counted
    _inbox(client, {"id": "https://social.example/l1", "type": "Like", "actor": REMOTE,
                    "object": f"https://blog.example/post/{slug}"})
    # an English site spells it its way - American by default
    assert "1 favorite on the fediverse" in client.get(f"/post/{slug}").text

    # trashing a published post tells followers
    sent.clear()
    admin.post("/admin/delete", data={"slug": slug})
    fediverse.wait()
    assert any(d["type"] == "Delete" for u, d in sent)

    _inbox(client, {"id": "https://social.example/u1", "type": "Undo", "actor": REMOTE,
                    "object": {"id": "https://social.example/f1", "type": "Follow", "actor": REMOTE}})
    assert fediverse.follower_count() == 0


def test_bad_signatures_are_ignored(client, fedi):
    stranger = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    _inbox(client, {"id": "https://social.example/f9", "type": "Follow", "actor": REMOTE,
                    "object": "https://blog.example/ap/actor"}, key=stranger)
    assert fediverse.follower_count() == 0
    # and unsigned is refused before anything else
    r = client.post("/ap/inbox", content=b'{"type": "Follow"}', headers={"Content-Type": "application/activity+json"})
    fediverse.wait()
    assert r.status_code == 202 and fediverse.follower_count() == 0


def test_off_means_404(client):
    assert client.get("/ap/actor", headers=AP).status_code == 404
    assert client.get("/.well-known/webfinger?resource=acct:blog@x").status_code == 404
    assert client.post("/webmention", data={"source": "https://a.example", "target": "https://b.example"}).status_code == 404


def test_receiving_webmentions(client, admin, fedi, monkeypatch):
    settings.set_many({"webmention_receive": "1", "webmention_moderate": "1"})
    slug = save_post(admin, title="Mention me")
    target = f"https://blog.example/post/{slug}"
    pages = {
        "https://other.example/likes/1": f'<div class="h-entry"><a class="u-like-of" href="{target}">liked</a>'
                                         f'<a class="p-author h-card" href="https://other.example/">'
                                         f'<img class="u-photo" src="/me.png">Bo</a></div>',
        "https://other.example/replies/1": f'<article class="h-entry"><a class="u-in-reply-to" href="{target}">re</a>'
                                           f'<div class="e-content">Great read, thanks.</div>'
                                           f'<a class="p-author h-card" href="https://other.example/">Bo</a></article>',
        "https://other.example/nolink": "<p>Nothing to see</p>",
    }
    monkeypatch.setattr(webmention, "_fetch", lambda url: (url, "text/html", {}, pages[url]))
    assert "blog.example/webmention" in client.get(f"/post/{slug}").text
    for source in pages:
        r = client.post("/webmention", data={"source": source, "target": target})
        assert r.status_code == 202
    webmention.wait()
    mentions = webmention.for_post(slug, approved_only=False)
    kinds = {m["source"]: (m["kind"], m["approved"]) for m in mentions}
    assert kinds == {"https://other.example/likes/1": ("like", 1), "https://other.example/replies/1": ("reply", 0)}
    like = next(m for m in mentions if m["kind"] == "like")
    assert like["author_name"] == "Bo" and like["author_photo"] == "https://other.example/me.png"
    # the reply waits in Comments > Mentions
    queue = admin.get("/admin/comments?tab=mentions").text
    assert "Great read, thanks." in queue and "Waiting for approval" in queue
    reply = next(m for m in mentions if m["kind"] == "reply")
    admin.post("/admin/mentions/approve", data={"mention_id": reply["id"]})
    page = client.get(f"/post/{slug}").text
    assert 'id="mentions"' in page and "Great read, thanks." in page and "Bo liked this" in page
    # bad requests are refused up front
    assert client.post("/webmention", data={"source": "https://x.example", "target": "https://elsewhere.example/"}).status_code == 400
    assert client.post("/webmention", data={"source": target, "target": target}).status_code == 400


def test_sending_webmentions(admin, fedi, monkeypatch):
    sent = []
    monkeypatch.setattr(webmention, "send_one", lambda source, target: sent.append((source, target)) or "sent (202)")
    settings.set_many({"webmention_send": "1", "activitypub_enabled": "0"})
    publishing.baseline("webmention")
    slug = save_post(admin, title="Linking out", body="See [this](https://friend.example/post) and [me](/about).")
    publishing.check()
    webmention.wait()
    assert sent == [(f"https://blog.example/post/{slug}", "https://friend.example/post")]


def test_our_signatures_verify(fedi, monkeypatch):
    body = b'{"type": "Create"}'
    headers = fediverse.signed_headers("POST", "https://social.example/inbox", body)
    monkeypatch.setattr(fediverse, "fetch_actor", lambda url, refresh=False: fediverse.actor())
    who = fediverse.verify("POST", "/inbox", headers, body)
    assert who["id"] == "https://blog.example/ap/actor"
    try:
        fediverse.verify("POST", "/inbox", headers, b'{"type": "Delete"}')
    except ValueError:
        pass
    else:
        raise AssertionError("a changed body must not verify")


def test_a_retried_delivery_goes_to_its_own_inbox(monkeypatch):
    """A delivery that failed is retried five minutes later - with its own
    inbox and post, not whatever the queue had moved on to by then."""
    from soloblog import fediverse

    class Stop(Exception):
        pass

    jobs = [("https://a.example/inbox", {"id": "a"}, 0), ("https://b.example/inbox", {"id": "b"}, 0)]
    retried, timers = [], []

    class Queue:
        def get(self):
            if not jobs:
                raise Stop
            return jobs.pop(0)

        def put(self, item):
            retried.append(item)

        def task_done(self):
            pass

    class Timer:
        def __init__(self, delay, fn):
            timers.append(fn)

        def start(self):
            pass

    monkeypatch.setattr(fediverse, "_out_queue", Queue())
    monkeypatch.setattr(fediverse, "signed_post", lambda inbox, doc: 503)
    monkeypatch.setattr(fediverse.threading, "Timer", Timer)
    with contextlib.suppress(Stop):
        fediverse._out_loop()
    for fn in timers:
        fn()
    assert retried == [("https://a.example/inbox", {"id": "a"}, 1), ("https://b.example/inbox", {"id": "b"}, 1)]


def test_a_refused_delivery_is_logged_and_the_rest_still_go(monkeypatch, caplog):
    import logging
    from soloblog import fediverse

    class Stop(BaseException):
        pass

    jobs = [("https://gone.example/inbox", {"id": "a"}, 0), ("https://broken.example/inbox", {"id": "b"}, 0),
            ("https://fine.example/inbox", {"id": "c"}, 0)]
    sent = []

    class Queue:
        def get(self):
            if not jobs:
                raise Stop
            return jobs.pop(0)

        def task_done(self):
            pass

    def post(inbox, doc):
        sent.append(inbox)
        if "broken" in inbox:
            raise OSError("connection reset")
        return 410 if "gone" in inbox else 202

    monkeypatch.setattr(fediverse, "_out_queue", Queue())
    monkeypatch.setattr(fediverse, "signed_post", post)
    with caplog.at_level(logging.INFO, logger="soloblog.fediverse"), pytest.raises(Stop):
        fediverse._out_loop()
    logged = [r.getMessage() for r in caplog.records]
    assert sent == ["https://gone.example/inbox", "https://broken.example/inbox", "https://fine.example/inbox"]
    assert any("gone.example" in m and "410" in m for m in logged)
    assert any("broken.example" in m and "connection reset" in m for m in logged)


def test_a_failed_webmention_is_logged_with_its_answer(monkeypatch, caplog):
    import logging
    import urllib.error

    def refuse(req, timeout=15):
        raise urllib.error.HTTPError(req.full_url, 400, "Bad Request", {}, None)
    monkeypatch.setattr(webmention, "discover", lambda url: "https://endpoint.example/wm")
    monkeypatch.setattr(webmention.netguard, "open_url", refuse)
    with caplog.at_level(logging.INFO, logger="soloblog.webmention"):
        assert webmention.send_one("https://me.example/post/a", "https://other.example/b") == "refused (400)"
    assert any("endpoint.example" in r.getMessage() and "400" in r.getMessage() for r in caplog.records)


def test_ticking_mentions(admin, client):
    from soloblog.db import get_db
    from soloblog.tz import utcnow
    db = get_db()
    db.execute("DELETE FROM webmentions")
    for n, approved in ((1, 0), (2, 0), (3, 1)):
        db.execute("INSERT INTO webmentions (post_slug, source, target, kind, author_name, author_url, author_photo, "
                   "content, published, approved, received_at) VALUES ('p', ?, 't', 'reply', 'Bo', '', '', "
                   "'hi', '', ?, ?)", (f"https://other.example/{n}", approved, utcnow().isoformat()))
    db.commit()
    rows = {m["source"][-1]: m for m in webmention.list_all("", 1, 50)}
    try:
        html = admin.get("/admin/comments?tab=mentions").text
        assert 'id="mentions-bulk"' in html and 'data-state="waiting"' in html
        # Approve with every waiting one: the approved one isn't counted again
        r = admin.post("/admin/mentions/bulk", data={"action": "approve", "all_matching": "1", "in_state": "pending"})
        assert "Approved 2 mentions" in r.headers["location"].replace("%20", " ")
        assert webmention.count("pending") == 0
        admin.post("/admin/mentions/bulk", data={"action": "delete", "ids": [rows["1"]["id"], rows["3"]["id"]]})
        assert [m["source"][-1] for m in webmention.list_all("", 1, 50)] == ["2"]
        # someone else can't
        client.post("/admin/mentions/bulk", data={"action": "delete", "ids": [rows["2"]["id"]]})
        assert webmention.count("") == 1
    finally:
        db.execute("DELETE FROM webmentions")
        db.commit()
