from soloblog import comments
from conftest import PASSWORD, save_post


def test_comment_needs_approval(admin, client):
    slug = save_post(admin, title="Commentable")
    r = client.post(f"/post/{slug}/comment",
                    data={"author_name": "Visitor", "email": "v@example.com", "body": "First!", "website": ""})
    assert r.status_code == 303
    assert "First!" not in client.get(f"/post/{slug}").text
    pending = [c for c in comments.list_by_status("pending", per_page=500) if c["body"] == "First!"]
    assert pending
    admin.post("/admin/comments/approve", data={"comment_id": pending[0]["id"]})
    assert "First!" in client.get(f"/post/{slug}").text


def test_honeypot_drops_comment(admin, client):
    slug = save_post(admin, title="Honeypot target")
    client.post(f"/post/{slug}/comment",
                data={"author_name": "Bot", "email": "b@example.com", "body": "spam spam", "website": "http://x"})
    assert not [c for c in comments.list_by_status("pending", per_page=500) if c["body"] == "spam spam"]


def test_password_change_needs_current_password(admin):
    r = admin.post("/admin/settings/password",
                   data={"current": "wrong", "password": "newpassword1", "confirm": "newpassword1"})
    assert "Current password is wrong" in r.text
    r = admin.post("/admin/settings/password",
                   data={"current": PASSWORD, "password": PASSWORD, "confirm": PASSWORD})
    assert "Password updated" in r.text


def test_contact_form(admin, client):
    from soloblog import contact
    from test_basics import GENERAL
    assert client.get("/contact").status_code == 404
    admin.post("/admin/settings/name", headers={"hx-request": "true"}, data={**GENERAL, "contact_enabled": "1"})
    try:
        # into the menu the way any page of yours gets there: a pinned Link post
        save_post(admin, title="Contact me", link_url="/contact", pin_location="header")
        home = client.get("/").text
        link = home[home.index('href="/contact"') - 200:home.index('href="/contact"') + 200]
        assert "Contact me" in link and 'target="_blank"' not in link
        r = client.post("/contact", data={"name": "Ada", "email": "ada@example.com", "body": "Hello there"})
        assert "Sent" in r.text
        unread = contact.count_unread()
        client.post("/contact", data={"name": "Bot", "email": "b@example.com", "body": "spam", "website": "x"})
        assert contact.count_unread() == unread
        page = admin.get("/admin/messages").text
        assert "Hello there" in page and "spam" not in page
        # read one at a time, as email is - seeing the list isn't reading them
        assert contact.count_unread() == unread
    finally:
        admin.post("/admin/settings/name", headers={"hx-request": "true"}, data=GENERAL)


def test_a_contact_message_is_answered_by_replying(admin, client, monkeypatch):
    from soloblog import mail
    from soloblog import settings
    from test_basics import GENERAL
    sent = []
    monkeypatch.setattr(mail, "send_email", lambda to, subject, body, headers=None: sent.append(headers) or True)
    before = {k: settings.get(k) for k in ("contact_email",)}
    admin.post("/admin/settings/name", headers={"hx-request": "true"}, data={**GENERAL, "contact_enabled": "1"})
    try:
        settings.set_many({"contact_email": "hello.soloblog@example.com"})
        client.post("/contact", data={"name": "Ada", "email": "Ada@Example.com", "body": "A question"})
        assert sent[-1] == {"Reply-To": "Ada@example.com"}
        # an address that tries to add a header of its own is left out
        sent.clear()
        client.post("/contact", data={"name": "Eve", "email": "eve@example.com\r\nBcc: x@y.z", "body": "Hi"})
        assert all(headers is None for headers in sent)
    finally:
        settings.set_many(before)
        admin.post("/admin/settings/name", headers={"hx-request": "true"}, data=GENERAL)


def test_contact_forwards_to_form_service(admin, client, monkeypatch):
    from soloblog import contact
    from soloblog import formservices
    from test_basics import GENERAL
    sent = []
    monkeypatch.setattr(formservices, "_post", lambda url, data: sent.append((url, data)))
    r = admin.post("/admin/settings/name", headers={"hx-request": "true"}, data={
        **GENERAL, "contact_enabled": "1", "contact_service": "formspree", "contact_service_id": "xyzabcd"})
    assert "Saved" in r.text and "text-success" in r.text
    try:
        client.post("/contact", data={"name": "Ada", "email": "ada@example.com", "body": "Forward me"})
        for _ in range(50):
            if sent:
                break
            import time
            time.sleep(0.05)
        url, data = sent[0]
        assert url == "https://formspree.io/f/xyzabcd"
        assert data["message"] == "Forward me" and data["email"] == "ada@example.com"
        # still kept in the inbox too
        assert any(m["body"] == "Forward me" for m in contact.list_all(per_page=100))
        r = admin.post("/admin/settings/name", headers={"hx-request": "true"}, data={
            **GENERAL, "contact_enabled": "1", "contact_service": "formspree", "contact_service_id": "bad id!"})
        assert "doesn&#x27;t look like" in r.text or "doesn't look like" in r.text
    finally:
        admin.post("/admin/settings/name", headers={"hx-request": "true"}, data=GENERAL)


def test_contact_page_can_be_a_hosted_form(admin, client):
    from test_basics import GENERAL
    admin.post("/admin/settings/name", headers={"hx-request": "true"}, data={
        **GENERAL, "contact_enabled": "1", "contact_mode": "embed", "contact_form_url": "https://tally.so/r/w4Ab9X"})
    try:
        html = client.get("/contact").text
        assert "https://tally.so/embed/w4Ab9X" in html and "Load from Tally" in html
        assert 'id="contact-form"' not in html
    finally:
        admin.post("/admin/settings/name", headers={"hx-request": "true"}, data=GENERAL)


def test_hosted_forms_embed_in_posts():
    from soloblog.render import render_post
    html, _ = render_post("RSVP here:\n\nhttps://docs.google.com/forms/d/e/1FAIpQLSf_abc/viewform\n")
    assert "viewform?embedded=true" in html and "<iframe" not in html


def test_spam_check_on_comments_and_contact(admin, client, monkeypatch):
    import io
    from soloblog import captcha
    from soloblog import settings
    from conftest import save_post
    slug = save_post(admin, title="Spam check post")
    settings.set_many({"captcha_provider": "turnstile", "captcha_site_key": "0x4AAAsite",
                       "captcha_secret": "0x4AAAsecret", "contact_enabled": "1"})
    asked = []

    class Answer(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): pass

    def fake_urlopen(req, timeout=10):
        asked.append(req.data)
        return Answer(b'{"success": true}' if b"response=good" in req.data else b'{"success": false}')
    monkeypatch.setattr(captcha.netguard, "open_url", fake_urlopen)
    try:
        html = client.get(f"/post/{slug}").text
        assert 'data-captcha="0x4AAAsite"' in html and "challenges.cloudflare.com/turnstile" in html
        comment = {"author_name": "Ada", "email": "ada@example.com", "body": "Hi"}
        hx = {"hx-request": "true"}
        assert "spam check" in client.post(f"/post/{slug}/comment", headers=hx, data=comment).text
        assert "spam check" in client.post(f"/post/{slug}/comment", headers=hx,
                                           data={**comment, "captcha_token": "bad"}).text
        assert "spam check" not in client.post(f"/post/{slug}/comment", headers=hx,
                                               data={**comment, "captcha_token": "good"}).text
        assert b"secret=0x4AAAsecret" in asked[-1]
        assert "data-captcha" in client.get("/contact").text
        assert "spam check" in client.post("/contact", data={"name": "Ada", "email": "a@example.com",
                                                             "body": "Hello"}).text
    finally:
        settings.set_many({"captcha_provider": "", "captcha_site_key": "", "captcha_secret": "",
                           "contact_enabled": "0"})
    assert "data-captcha" not in client.get(f"/post/{slug}").text


def test_comment_blocklist(admin, client):
    from soloblog import settings
    slug = save_post(admin, title="Blocklist target")
    settings.set_many({"comment_blocklist": "Casino\nspammer.example"})
    try:
        client.post(f"/post/{slug}/comment", data={"author_name": "Bob", "email": "bob@spammer.example",
                                                   "body": "Nice post"})
        client.post(f"/post/{slug}/comment", data={"author_name": "Eve", "email": "e@example.com",
                                                   "body": "Best CASINO bonus"})
        client.post(f"/post/{slug}/comment", data={"author_name": "Ann", "email": "a@example.com",
                                                   "body": "Genuinely helpful"})
        pending = [c["body"] for c in comments.list_by_status("pending", slug, per_page=50)]
        trashed = [c["body"] for c in comments.list_by_status("trash", slug, per_page=50)]
        assert pending == ["Genuinely helpful"]
        assert sorted(trashed) == ["Best CASINO bonus", "Nice post"]
    finally:
        settings.set_many({"comment_blocklist": ""})


def test_spam_protection_is_in_security(admin):
    from soloblog import settings
    link = "/admin/settings?tab=security&amp;panel=security-spam"
    security = admin.get("/admin/settings?tab=security").text
    assert 'name="captcha_provider"' in security and 'data-panel="security-spam"' in security
    for tab in ("messages",):
        page = admin.get(f"/admin/settings?tab={tab}").text
        assert 'name="captcha_provider"' not in page
        assert f'href="{link}"' in page and "Spam protection is in" in page
    index = admin.get("/admin/settings/search-index").json()
    spam = [e for e in index if e["title"] == "Spam protection"]
    assert spam and spam[0]["group"] == "Security" and "panel=security-spam" in spam[0]["href"]
    keep = settings.get_all()
    try:
        admin.post("/admin/settings/security", headers={"HX-Request": "true"}, data={
            "captcha_provider": "turnstile", "captcha_site_key": "0x4AAAsite", "captcha_secret": "0x4AAAsecret",
            "declared_fields": "captcha_provider,captcha_site_key,captcha_secret"})
        assert settings.get("captcha_provider") == "turnstile" and settings.get("captcha_site_key") == "0x4AAAsite"
        assert settings.get("captcha_secret") == "0x4AAAsecret"
        # saving Comments and messages leaves the check alone
        admin.post("/admin/settings/messages", headers={"HX-Request": "true"},
                   data={"notify_comments": "1", "declared_fields": "notify_comments"})
        admin.post("/admin/settings/messages", headers={"HX-Request": "true"},
                   data={"contact_intro": "Hi", "declared_fields": "contact_intro"})
        assert settings.get("captcha_provider") == "turnstile" and settings.get("captcha_secret")
    finally:
        settings.set_many({k: keep[k] for k in ("captcha_provider", "captcha_site_key", "captcha_secret",
                                                "notify_comments", "contact_intro")})
