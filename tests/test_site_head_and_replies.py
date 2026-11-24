from pathlib import Path
import io
import os
import threading

from PIL import Image

from soloblog import comments
from soloblog import config
from soloblog import replymail
from soloblog import settings
from conftest import save_post

SITE = {"google_site_verification": "abc123-XYZ", "bing_site_verification": "B1NG", "app_name": "Probe"}
# saved under Integrations (it was under Search engines)
CODE = {"custom_head": '<meta name="custom-probe" content="1">', "custom_css": "body{--probe:1}</style><script>"}


def test_search_and_code_settings(admin, client):
    r = admin.post("/admin/settings/url", data=SITE, headers={"hx-request": "true"})
    assert "Saved" in r.text
    r = admin.post("/admin/settings/integrations", data={**CODE, "declared_fields": "custom_head,custom_css"},
                   headers={"hx-request": "true"})
    assert "Saved" in r.text
    try:
        public = client.get("/").text
        assert '<meta name="google-site-verification" content="abc123-XYZ">' in public
        assert '<meta name="msvalidate.01" content="B1NG">' in public
        assert '<meta name="custom-probe" content="1">' in public
        assert "--probe:1" in public and "</style><script>" not in public
        # never on admin pages
        admin_page = admin.get("/admin/settings?tab=url").text
        assert '<meta name="custom-probe"' not in admin_page and "--probe:1" not in admin_page.split("</head>")[0]
        # a whole tag pasted as the code is refused
        r = admin.post("/admin/settings/url", data={**SITE, "google_site_verification": '<meta content="x">'},
                       headers={"hx-request": "true"})
        assert "text-error" in r.text and settings.get("google_site_verification") == ""
    finally:
        settings.set_many({k: "" for k in {**SITE, **CODE}})


def test_hide_from_search_engines(client):
    settings.set_many({"search_noindex": "1"})
    try:
        assert '<meta name="robots" content="noindex, nofollow">' in client.get("/").text
        assert "Disallow: /\n" in client.get("/robots.txt").text
    finally:
        settings.set_many({"search_noindex": "0"})
    assert "Sitemap:" in client.get("/robots.txt").text


def test_manifest_and_icons(client):
    # nothing uploaded: an icon made from the title's first letter
    manifest = client.get("/manifest.webmanifest").json()
    assert manifest["start_url"] == "/" and manifest["icons"][0]["src"].startswith("/icon-192.png?v=")
    made = client.get("/icon-192.png")
    assert made.headers["content-type"] == "image/png" and Image.open(io.BytesIO(made.content)).size == (192, 192)
    assert 'rel="icon" href="/icon-32.png?v=' in client.get("/").text

    os.makedirs(config.UPLOADS_DIR, exist_ok=True)
    Image.new("RGB", (900, 600), (10, 20, 30)).save(os.path.join(config.UPLOADS_DIR, "appicon.webp"), "WEBP")
    settings.set_many({"app_icon_url": "/uploads/appicon.webp", "app_name": "Short"})
    try:
        manifest = client.get("/manifest.webmanifest").json()
        assert manifest["short_name"] == "Short" and manifest["icons"][0]["src"].startswith("/icon-192.png?v=")
        icon = client.get("/icon-512.png")
        assert icon.headers["content-type"] == "image/png"
        assert Image.open(io.BytesIO(icon.content)).size == (512, 512)
        assert 'rel="apple-touch-icon" href="/icon-180.png?v=' in client.get("/").text
        # the upload, not the letter: a dark square
        assert max(Image.open(io.BytesIO(icon.content)).convert("RGB").getpixel((256, 256))) < 40
        assert client.get("/icon-64.png").status_code == 404
    finally:
        settings.set_many({"app_icon_url": "", "app_name": ""})


def test_reply_emails(admin, client, monkeypatch):
    sent = []
    done = threading.Event()

    def fake_send(to, subject, body):
        if "replied" in subject:  # not the comment's confirmation email
            sent.append((to, subject, body))
            done.set()
        return True
    monkeypatch.setattr(replymail.mail, "send_email", fake_send)
    settings.set_many({"email_provider": "smtp", "reply_emails": "1"})
    try:
        slug = save_post(admin, title="Replies wanted")
        assert "Email me when someone replies" in client.get(f"/post/{slug}").text
        client.post(f"/post/{slug}/comment", data={"author_name": "Ann", "email": "ann@example.com",
                                                   "body": "Tell me more", "website": "", "notify_replies": "1"})
        c = [x for x in comments.list_by_status("pending", per_page=500) if x["body"] == "Tell me more"]
        assert not c  # waiting on the confirmation link first
        row = comments.get_db().execute("SELECT * FROM comments WHERE body='Tell me more'").fetchone()
        assert row["notify_replies"] == 1 and row["notify_token"]
        comments.confirm(row["confirm_token"])
        admin.post("/admin/comments/approve", data={"comment_id": row["id"]})

        admin.post(f"/post/{slug}/reply", data={"parent_id": row["id"], "body": "Here is more"})
        assert done.wait(5)
        to, subject, body = sent[0]
        assert to == "ann@example.com" and "replied to your comment" in subject
        assert "Here is more" in body and f"/comment/unsubscribe/{row['notify_token']}" in body
        assert "#comment-" in body

        # the link asks first, then stops them
        assert "Stop reply emails" in client.get(f"/comment/unsubscribe/{row['notify_token']}").text
        assert "no more reply emails" in client.post(f"/comment/unsubscribe/{row['notify_token']}").text
        assert comments.get(row["id"])["notify_replies"] == 0
        sent.clear()
        done.clear()
        admin.post(f"/post/{slug}/reply", data={"parent_id": row["id"], "body": "Anyone there?"})
        assert not done.wait(0.5)
    finally:
        settings.set_many({"email_provider": "", "reply_emails": "1"})


def test_a_reply_email_that_fails_doesnt_stop_the_ones_after_it(monkeypatch, caplog):
    sent = []

    def fake_send(to, subject, body):
        if to == "first@example.com":
            raise OSError("refused first@example.com")
        sent.append(to)
    monkeypatch.setattr(replymail.mail, "send_email", fake_send)
    with caplog.at_level("WARNING", logger="soloblog.replymail"):
        replymail._send_all([("first@example.com", "s", "b"), ("second@example.com", "s", "b")])
    assert sent == ["second@example.com"]
    assert "OSError" in caplog.text and "example.com" not in caplog.text


def test_a_developers_outbox_catches_email(monkeypatch, tmp_path):
    # MAIL_OUTBOX (the journeys, a developer): written to a file, not sent
    from soloblog import mail
    monkeypatch.setattr(config, "MAIL_OUTBOX", str(tmp_path))
    settings.set_many({"email_provider": "smtp"})
    try:
        assert mail.send_email("ann@example.com", "Hello", "The body.")
        files = os.listdir(tmp_path)
        assert len(files) == 1 and b"ann@example.com" in Path(os.path.join(tmp_path, files[0])).read_bytes()
    finally:
        settings.set_many({"email_provider": ""})
