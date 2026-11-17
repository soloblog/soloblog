import io
import json

from soloblog import crosspost
from soloblog import extcomments
from soloblog import netguard
from soloblog import publishing
from soloblog import settings
from conftest import save_post

OFF = {"crosspost_bluesky": "0", "crosspost_mastodon": "0", "bluesky_handle": "", "bluesky_app_password": "",
       "mastodon_instance": "", "mastodon_token": "", "comments_system": ""}


def _site(admin, **fields):
    return admin.post("/admin/settings/address", headers={"hx-request": "true"},
                      data={**fields, "declared_fields": ",".join(fields)})


def test_new_posts_go_to_bluesky_and_mastodon(admin, client, monkeypatch):
    calls, toots = [], []

    def fake_json(url, data=None, token="", body=None, content_type="application/json"):
        calls.append((url.rsplit(".", 1)[1], data))  # com.atproto.repo.createRecord -> createRecord
        if url.endswith("createSession"):
            return {"accessJwt": "jwt", "did": "did:plc:me"}
        return {"uri": "at://did:plc:me/app.bsky.feed.post/3kmine"}

    class Answer(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): pass

    def fake_open(req, timeout=10):
        toots.append((req.full_url, json.loads(req.data), req.headers))
        return Answer(b'{"url": "https://mastodon.example/@me/1"}')
    monkeypatch.setattr(crosspost, "_json", fake_json)
    monkeypatch.setattr(netguard, "open_url", fake_open)
    old = save_post(admin, title="Already live before sharing")
    try:
        r = _site(admin, crosspost_bluesky="1", bluesky_handle="@Me.bsky.social", bluesky_app_password="abcd-efgh-ijkl-mnop",
                  crosspost_mastodon="1", mastodon_instance="https://mastodon.example/", mastodon_token="tok123")
        assert "text-success" in r.text, r.text
        assert settings.get("bluesky_handle") == "me.bsky.social"
        publishing.check()
        assert not calls and not toots  # the back catalogue isn't shared
        slug = save_post(admin, title="Worth sharing", summary="The gist")
        save_post(admin, title="A page, not a post", pinned="1", pin_location="footer")
        publishing.check()
        record = [d for name, d in calls if name == "createRecord"][0]["record"]
        assert record["text"] == "Worth sharing" and record["embed"]["external"]["uri"].endswith(f"/post/{slug}")
        assert len(toots) == 1 and toots[0][0] == "https://mastodon.example/api/v1/statuses"
        assert "The gist" in toots[0][1]["status"] and f"/post/{slug}" in toots[0][1]["status"]
        # an edit isn't shared again
        save_post(admin, slug=slug, title="Worth sharing", body="Edited")
        publishing.check()
        assert len([c for c in calls if c[0] == "createRecord"]) == 1 and len(toots) == 1
        # and the shared post is where Bluesky comments are read from
        monkeypatch.setattr(extcomments, "_get", lambda method, **p: {"thread": {"replies": []}})
        reply_url, _ = extcomments.thread("me.bsky.social", "https://x.example/post/" + slug, slug)
        assert reply_url == "https://bsky.app/profile/me.bsky.social/post/3kmine"
        assert old
    finally:
        settings.set_many(OFF)


def test_sharing_needs_its_credentials(admin):
    try:
        r = _site(admin, crosspost_mastodon="1", mastodon_instance="http://insecure.example", mastodon_token="t")
        assert "https://" in r.text and settings.get("mastodon_instance") == ""
    finally:
        settings.set_many(OFF)
