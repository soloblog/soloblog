import re
import time

from soloblog import auth
from soloblog import config
from soloblog import mail
from soloblog import settings
from conftest import PASSWORD
from datetime import UTC


def _keep(*keys):
    return {k: settings.get(k) for k in keys}


def test_recovery_key_is_kept_as_a_hash_and_forgiving_to_type():
    before = _keep("recovery_key_hash", "recovery_key_made")
    try:
        key = auth.new_recovery_key()
        assert re.fullmatch(r"([0-9A-HJKMNP-TV-Z]{4}-){4}[0-9A-HJKMNP-TV-Z]{4}", key)
        # only its hash is kept
        assert key.replace("-", "") not in str(settings.get_all())
        assert auth.recovery_key_ok(key)
        # lower case, spaces, no dashes, O for 0 and I or L for 1 all still work
        typed = key.lower().replace("-", " ").replace("0", "o").replace("1", "l")
        assert auth.recovery_key_ok(typed)
        assert not auth.recovery_key_ok(key[:-1] + ("A" if key[-1] != "A" else "B"))
        assert not auth.recovery_key_ok("") and not auth.recovery_key_ok("x" * 400)
        # a new key and the old one stops working
        auth.new_recovery_key()
        assert not auth.recovery_key_ok(key)
    finally:
        settings.set_many(before)


def test_a_damaged_stored_hash_refuses_and_is_logged(caplog):
    import logging
    before = _keep("recovery_key_hash")
    try:
        key = auth.new_recovery_key()
        settings.set_many({"recovery_key_hash": "not-an-argon2-hash"})
        with caplog.at_level(logging.ERROR, logger="soloblog.auth"):
            assert auth.recovery_key_ok(key) is False
        assert any("recovery key is damaged" in r.getMessage() for r in caplog.records)
        # a wrong key is routine - nothing logged
        caplog.clear()
        settings.set_many(before)
        with caplog.at_level(logging.WARNING, logger="soloblog.auth"):
            assert auth.recovery_key_ok("A" * 20) is False
        assert not caplog.records
    finally:
        settings.set_many(before)


def test_a_timezone_this_system_lacks_falls_back_to_utc():
    from soloblog import tz
    before = _keep("timezone")
    try:
        for name in ("Nowhere/Atlantis", "../etc/passwd", "x" * 300):
            settings.set_many({"timezone": name})
            assert tz.site_zone() is UTC, name
    finally:
        settings.set_many(before)


def test_forgot_password_with_the_recovery_key(client):
    before = _keep("recovery_key_hash", "recovery_key_made", "session_version")
    key = auth.new_recovery_key()
    try:
        page = client.get("/forgot-password").text
        assert 'action="/forgot-password/key"' in page and 'autocomplete="username"' in page
        # a wrong key changes nothing
        r = client.post("/forgot-password/key", data={"key": "AAAA-AAAA-AAAA-AAAA-AAAA", "password": "new password 1",
                                                       "confirm": "new password 1"})
        assert "That recovery key isn't right" in r.text and auth.verify_password(PASSWORD)
        # nor do passwords that don't match
        r = client.post("/forgot-password/key", data={"key": key, "password": "new password 1",
                                                       "confirm": "new password 2"})
        assert "The passwords don't match" in r.text and auth.verify_password(PASSWORD)
        # the right key: a new password, and a new key shown - the old one is used up
        r = client.post("/forgot-password/key", data={"key": key, "password": "new password 1",
                                                       "confirm": "new password 1"})
        assert r.status_code == 200 and "Password changed" in r.text
        assert auth.verify_password("new password 1") and not auth.recovery_key_ok(key)
        shown = re.search(r"([0-9A-Z]{4}-){4}[0-9A-Z]{4}", r.text).group(0)
        assert auth.recovery_key_ok(shown)
    finally:
        auth.set_password(PASSWORD)
        settings.set_many(before)


def test_recovery_key_guesses_are_limited(client):
    before = _keep("recovery_key_hash", "recovery_key_made")
    key = auth.new_recovery_key()
    try:
        for _ in range(5):
            client.post("/forgot-password/key", data={"key": "ZZZZ-ZZZZ-ZZZZ-ZZZZ-ZZZZ", "password": "whatever 12",
                                                       "confirm": "whatever 12"})
        # the sixth try is turned away, even with the right key
        r = client.post("/forgot-password/key", data={"key": key, "password": "whatever 12", "confirm": "whatever 12"})
        assert "Too many attempts" in r.text and auth.verify_password(PASSWORD)
    finally:
        settings.set_many(before)


def test_a_new_recovery_key_needs_the_password(admin):
    before = _keep("recovery_key_hash", "recovery_key_made")
    try:
        page = admin.get("/admin/settings?tab=security").text
        assert 'id="recovery-key-body"' in page
        r = admin.post("/admin/recovery-key", data={"password": "not it"}, headers={"hx-request": "true"})
        assert "That password isn't right" in r.text
        r = admin.post("/admin/recovery-key", data={"password": PASSWORD}, headers={"hx-request": "true"})
        shown = re.search(r"([0-9A-Z]{4}-){4}[0-9A-Z]{4}", r.text).group(0)
        assert auth.recovery_key_ok(shown) and "I've saved it" in r.text
        assert "Saved" in admin.get("/admin/recovery-key/panel").text
    finally:
        settings.set_many(before)


def test_a_setup_token_you_choose(monkeypatch):
    monkeypatch.setattr(config, "SETUP_TOKEN", "my-own-long-setup-token")
    assert auth.setup_token() == "my-own-long-setup-token"
    # too short to be safe: the one made at boot instead
    monkeypatch.setattr(config, "SETUP_TOKEN", "short")
    assert auth.setup_token() != "short" and len(auth.setup_token()) > 20


def test_email_addresses_are_checked():
    assert mail.clean_email(" Mira@Example.COM ") == "Mira@example.com"
    for bad in ("mira", "mira@example", "mira @example.com", "mira@example..com", "@example.com", "a@b.c."):
        assert mail.clean_email(bad) == "", bad


def test_the_admin_email_changes_only_with_the_password(admin, monkeypatch):
    """Password resets go to the admin email, so whoever can change it has
    the site: a logged-in browser alone isn't enough, and the old address
    is told."""
    before = _keep("admin_email")
    sent = []
    monkeypatch.setattr(mail, "can_send", lambda: True)
    monkeypatch.setattr(mail, "send_email", lambda to, subject, body, **kw: sent.append((to, subject, body)) or True)
    new = {"admin_email": "thief@example.com", "admin_email_confirm": "thief@example.com",
           "declared_fields": "admin_email,admin_email_confirm"}
    try:
        settings.set_many({"admin_email": "mira@example.com"})
        for password, says in (("", "Enter your password"), ("not-the-password", "That password isn")):
            r = admin.post("/admin/settings/email", headers={"hx-request": "true"},
                           data={**new, "current_password": password})
            assert says in r.text and settings.get("admin_email") == "mira@example.com", password
            # Send a test email saves what's on screen first: no way round
            admin.post("/admin/email/test", data={**new, "current_password": password})
            assert settings.get("admin_email") == "mira@example.com", password
        # and no other page takes an address: the setup once had a screen that did
        assert admin.post("/admin/welcome/email", data=new).status_code in (404, 405)
        assert settings.get("admin_email") == "mira@example.com"
        assert not sent
        # the same address saved again, with the page's other settings, asks nothing
        r = admin.post("/admin/settings/email", headers={"hx-request": "true"},
                       data={"admin_email": "mira@example.com", "admin_email_confirm": "mira@example.com",
                             "declared_fields": "admin_email,admin_email_confirm"})
        assert "Saved" in r.text and not sent
        r = admin.post("/admin/settings/email", headers={"hx-request": "true"},
                       data={**new, "current_password": PASSWORD})
        assert "Saved" in r.text and settings.get("admin_email") == "thief@example.com"
        assert [to for to, _, _ in sent] == ["mira@example.com"]
        assert "thief@example.com" in sent[0][2] and "/forgot-password" in sent[0][2]
        assert 'name="current_password"' in admin.get("/admin/settings?tab=email").text
    finally:
        settings.set_many(before)
        from soloblog.db import get_db
        conn = get_db()
        conn.execute("DELETE FROM rate_hits WHERE bucket = 'confirm-password'")
        conn.commit()


def test_the_email_typed_twice(admin):
    before = _keep("admin_email", "author_name")
    try:
        settings.set_many({"admin_email": "Mira@example.com"})
        # Settings > Email > Admin email: a mismatch saves nothing and says why
        r = admin.post("/admin/settings/email", headers={"hx-request": "true"},
                       data={"admin_email": "new@example.com", "admin_email_confirm": "new@example.co",
                             "declared_fields": "admin_email,admin_email_confirm"})
        assert "don't match" in r.text and settings.get("admin_email") == "Mira@example.com"
        r = admin.post("/admin/settings/email", headers={"hx-request": "true"},
                       data={"admin_email": "new@example.com", "admin_email_confirm": "NEW@example.com",
                             "current_password": PASSWORD, "declared_fields": "admin_email,admin_email_confirm"})
        assert "Saved" in r.text and settings.get("admin_email") == "new@example.com"
        form = admin.get("/admin/settings?tab=email").text
        # with the page's own Save, as every setting is - no form of its own
        assert 'data-must-match="admin_email"' in form and form.count('hx-post="/admin/settings/email"') == 1
        # one place for it: not on Security too
        assert 'name="admin_email"' not in admin.get("/admin/settings?tab=security").text
        # and no longer among the integrations; without the second copy it isn't changed
        assert 'name="admin_email"' not in admin.get("/admin/settings?tab=integrations").text
        admin.post("/admin/settings/email", headers={"hx-request": "true"},
                   data={"admin_email": "x@example.com", "declared_fields": "admin_email"})
        assert settings.get("admin_email") == "new@example.com"
    finally:
        settings.set_many(before)


def test_password_managers_see_the_account(client, admin):
    assert 'autocomplete="username"' in client.get("/login").text
    security = admin.get("/admin/settings?tab=security").text
    assert 'autocomplete="username"' in security and 'data-must-match="password"' in security


def test_a_new_device_signing_in_is_reported(app, monkeypatch):
    from starlette.testclient import TestClient
    sent = []
    monkeypatch.setattr(mail, "send_email", lambda to, subject, body, headers=None: sent.append((to, subject)) or True)
    before = _keep("email_provider", "admin_email", "signin_alerts")
    settings.set_many({"email_provider": "api", "admin_email": "mira@example.com", "signin_alerts": "1"})

    def wait():
        for _ in range(40):
            if sent:
                return
            time.sleep(0.05)
    try:
        first = TestClient(app, follow_redirects=False)
        r = first.post("/login", data={"password": PASSWORD})
        wait()
        assert r.status_code == 303 and sent and sent[0][0] == "mira@example.com" and "New sign-in" in sent[0][1]
        assert "known_device" in r.cookies
        # the same browser again: nothing new to report
        sent.clear()
        first.post("/login", data={"password": PASSWORD})
        time.sleep(0.3)
        assert not sent
        # a made-up cookie doesn't hide a sign-in
        forged = TestClient(app, follow_redirects=False, cookies={"known_device": "abc.def"})
        forged.post("/login", data={"password": PASSWORD})
        wait()
        assert sent
        # switched off: no email
        sent.clear()
        settings.set_many({"signin_alerts": "0"})
        TestClient(app, follow_redirects=False).post("/login", data={"password": PASSWORD})
        time.sleep(0.3)
        assert not sent
    finally:
        settings.set_many(before)


def test_test_email_and_next_steps(admin):
    from soloblog.routes.welcome import next_steps
    before = _keep("email_provider", "admin_email")
    try:
        settings.set_many({"email_provider": "", "admin_email": "mira@example.com"})
        assert "Choose how email is sent" in admin.post("/admin/email/test").text
        titles = [step[1] for step in next_steps(settings.get_all())]
        # the recovery key is saved at setup, so it isn't a job left to do
        assert "Save a recovery key" not in titles and "Protect your login" in titles
        assert titles[0] == "Set up email" and "Use a custom domain" in titles and len(titles) == 6
    finally:
        settings.set_many(before)


def test_a_new_site_starts_with_a_welcome_draft(admin, client):
    """Made once at setup (conftest's admin_account), a draft: the owner
    sees it, readers never do."""
    from soloblog import posts
    row = posts.get_post("welcome-to-your-new-site")
    assert row and not row["published"]
    body = posts.load_post_body("welcome-to-your-new-site")
    assert "/admin/help?tab=sponsor" in body and "/discussions" in body and "trash" in body
    assert client.get("/post/welcome-to-your-new-site").status_code == 404
    assert "Welcome to your new site" not in client.get("/").text


def _without_admin():
    from soloblog.db import get_db
    row = get_db().execute("SELECT * FROM admin WHERE id=1").fetchone()
    get_db().execute("DELETE FROM admin")
    get_db().commit()
    return row


def _put_admin_back(row):
    from soloblog.db import get_db
    if not auth.admin_exists():
        get_db().execute("INSERT INTO admin VALUES (?, ?, ?, ?, ?, ?)", tuple(row))
        get_db().commit()


def test_setup_restores_a_downloaded_backup_with_its_login(admin, client):
    """Moving host with a downloaded backup: setup takes it, with the
    token, and the whole site comes back - posts, images and the login,
    so there's no new account to make."""
    import io
    import os
    import zipfile
    from conftest import save_post
    from soloblog import backup, images, posts
    save_post(admin, title="Moved with me")
    name = images.save_upload(_png()).rsplit("/", 1)[1]
    whole = backup.build_backup_zip(None)
    row = _without_admin()
    os.remove(os.path.join(config.posts_dir(), "moved-with-me.md"))
    os.remove(os.path.join(config.uploads_dir(), name))
    try:
        assert 'href="/setup?restore=1"' in client.get("/setup").text
        page = client.get("/setup?restore=1").text
        assert "Restore a backup" in page and 'action="/setup/upload"' in page and 'name="backup_zip"' in page
        token = auth.setup_token()
        # a file that only pretends: names that climb out of the folders, no database
        sly = io.BytesIO()
        with zipfile.ZipFile(sly, "w") as zf:
            zf.writestr("posts/../../escaped.md", "x")
            zf.writestr("uploads/../../escaped.png", "x")
        tries = [({"token": "not it"}, whole, "setup token isn"),
                 ({"token": token}, b"not a zip at all", "isn't a whole Soloblog backup"),
                 ({"token": token}, sly.getvalue(), "isn't a whole Soloblog backup"),
                 ({"token": token}, storage_seal(whole, "a passphrase"), "That backup is locked"),
                 ({"token": token, "passphrase": "not it"}, storage_seal(whole, "a passphrase"), "Wrong passphrase"),
                 ({"token": token, "passphrase": "x" * 5000}, whole, "too big")]
        for fields, data, said in tries:
            r = client.post("/setup/upload", data=fields, files={"backup_zip": ("site.zip", data, "application/zip")})
            text = r.text.replace("&#x27;", "'")
            assert r.status_code == 200 and said in text, said
            assert not auth.admin_exists() and not os.path.isfile(os.path.join(config.posts_dir(), "moved-with-me.md"))
        assert not os.path.exists(os.path.join(config.data_dir(), "..", "escaped.md"))
        r = client.post("/setup/upload", data={"token": token, "passphrase": "a passphrase"},
                        files={"backup_zip": ("site.zip.enc", storage_seal(whole, "a passphrase"), "application/octet-stream")})
        assert r.status_code == 303 and r.headers["location"] == "/login?back=1"
        assert "Your site is back" in client.get("/login?back=1").text
        assert auth.admin_exists() and auth.verify_password(PASSWORD)
        assert posts.get_post("moved-with-me") and os.path.isfile(os.path.join(config.posts_dir(), "moved-with-me.md"))
        assert os.path.isfile(os.path.join(config.uploads_dir(), name))
        # once there's an admin, it's closed: nothing restores over a site
        r = client.post("/setup/upload", data={"token": token}, files={"backup_zip": ("site.zip", whole, "application/zip")})
        assert r.status_code == 303 and r.headers["location"] == "/login"
    finally:
        _put_admin_back(row)


def test_setup_takes_a_whole_backup_only_before_there_is_an_admin(admin, client):
    big = b"x" * (17 * 1024 * 1024)  # more than anyone not logged in may send
    files = {"backup_zip": ("site.zip", big, "application/zip")}
    assert client.post("/setup/upload", data={"token": "t"}, files=files).status_code == 413
    row = _without_admin()
    try:
        r = client.post("/setup/upload", data={"token": "not it"}, files=files)
        assert r.status_code == 200 and "setup token isn" in r.text
    finally:
        _put_admin_back(row)


def storage_seal(data, passphrase):
    from soloblog import storage
    return storage.seal(data, passphrase)


def _png():
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), "blue").save(buf, "PNG")
    return buf.getvalue()
