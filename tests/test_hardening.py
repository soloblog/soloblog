from conftest import save_post
from soloblog.guards import is_local_path


def test_security_headers_and_caching(client):
    r = client.get("/")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "SAMEORIGIN"
    assert r.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "camera=()" in r.headers["permissions-policy"] and "fullscreen" not in r.headers["permissions-policy"]
    assert r.headers["cross-origin-opener-policy"] == "same-origin"
    assert "immutable" in client.get("/static/vendor/htmx-2.0.7.min.js").headers.get("cache-control", "")


CSP_PAGES = ["/admin/new", "/admin/posts", "/admin/media", "/admin/stats", "/admin/messages",
             "/admin/settings?tab=name", "/admin/settings?tab=style", "/admin/settings?tab=editor"]


def test_every_script_carries_the_pages_nonce(admin, client):
    from soloblog import csp
    import re
    slug = save_post(admin, title="Nonce check")
    for c, path in [(client, "/"), (client, f"/post/{slug}"), (client, "/nope")] + [(admin, p) for p in CSP_PAGES]:
        r = c.get(path)
        policy = r.headers["content-security-policy"]
        nonce = re.search(r"'nonce-([^']+)'", policy).group(1)
        assert csp.NONCE not in r.text, path  # the marker never leaves the server
        for tag in re.findall(r"<script\b[^>]*>", r.text):
            assert f'nonce="{nonce}"' in tag or "application/ld+json" in tag, (path, tag)
        # no inline handlers - they'd be blocked (see actions.py)
        assert not re.findall(r"<[a-z][^>]*\son[a-z]+=", r.text), path


def test_scripts_run_only_with_the_nonce(client):
    # no fallback that lets an injected script run in an older browser
    policy = client.get("/").headers["content-security-policy"]
    scripts = next(part for part in policy.split("; ") if part.startswith("script-src "))
    assert "'unsafe-inline'" not in scripts and "https:" not in scripts and "*" not in scripts
    assert "'strict-dynamic'" in scripts


def test_nonce_changes_every_response(client):
    first, second = (client.get("/").headers["content-security-policy"] for _ in range(2))
    assert first != second and "object-src 'none'" in first


def test_custom_head_scripts_get_the_nonce():
    from soloblog import csp
    assert csp.nonce_scripts('<SCRIPT src="x.js"></SCRIPT>') == f'<script nonce="{csp.NONCE}" src="x.js"></SCRIPT>'


def test_pages_are_compressed(client):
    r = client.get("/", headers={"Accept-Encoding": "gzip"})
    assert r.headers.get("content-encoding") == "gzip"


def test_editor_scripts_only_on_the_editor(admin, client):
    assert "easymde.min.js" not in client.get("/").text
    html = admin.get("/admin/new").text
    assert "/static/vendor/easymde-2.20.0/easymde.min.js" in html
    assert "font-awesome" not in html  # the toolbar icons are inline Lucide SVGs


def test_redirect_targets_stay_on_site():
    assert is_local_path("/admin/posts?status=trash")
    for bad in ("//evil.example", "/\\evil.example", "https://evil.example", ""):
        assert not is_local_path(bad)


def test_delete_ignores_offsite_return_to(admin):
    slug = save_post(admin, title="Redirect target test")
    r = admin.post("/admin/delete", data={"slug": slug, "return_to": "//evil.example/x"})
    assert r.headers["location"].startswith("/admin/posts")


def test_series_nav_hides_scheduled_parts(admin, client):
    save_post(admin, title="Visible part", series_name="Leak Check", series_order="1")
    later = save_post(admin, title="Secret future part", series_name="Leak Check", series_order="2",
                      scheduled_at="2099-01-01T09:00")
    first = client.get("/post/visible-part").text
    assert "Secret future part" not in first
    assert "Secret future part" in admin.get("/post/visible-part").text
    assert client.get(f"/post/{later}").status_code == 404


def test_no_unpinned_third_party_scripts(client):
    import re
    html = client.get("/").text
    scripts = re.findall(r'<script[^>]*src="([^"]+)"', html)
    assert "/static/vendor/htmx-2.0.7.min.js" in scripts
    assert not [s for s in scripts if s.startswith("http")], scripts


def test_vendored_files_are_served(client):
    for path in ("/static/vendor/htmx-2.0.7.min.js", "/static/vendor/easymde-2.20.0/easymde.min.js",
                 "/static/vendor/theme-change-2.5.0.js"):
        assert client.get(path).status_code == 200, path


def test_cross_site_posts_are_refused(app):
    from starlette.testclient import TestClient
    c = TestClient(app, follow_redirects=False)
    evil = {"Origin": "https://evil.example"}
    assert c.post("/login", data={"password": "x"}, headers=evil).status_code == 403
    assert c.post("/login", data={"password": "x"}, headers={"Origin": "null"}).status_code == 403
    assert c.post("/login", data={"password": "x"}, headers={"Referer": "https://evil.example/page"}).status_code == 403
    # same-origin, and header-less (not a browser page), both pass
    assert c.post("/login", data={"password": "x"}, headers={"Origin": "http://testserver"}).status_code == 200
    assert c.post("/contact", data={}).status_code == 200


def test_logout_needs_a_post(app):
    from starlette.testclient import TestClient
    from conftest import PASSWORD
    c = TestClient(app, follow_redirects=False)
    c.post("/login", data={"password": PASSWORD})
    assert "Log out?" in c.get("/logout").text
    assert c.get("/admin/posts").status_code == 200  # a GET didn't log out
    c.post("/logout")
    assert c.get("/admin/posts").headers["location"] == "/login"


def test_ending_other_sessions(app, admin):
    from starlette.testclient import TestClient
    from conftest import PASSWORD
    other = TestClient(app, follow_redirects=False)
    other.post("/login", data={"password": PASSWORD})
    assert other.get("/admin/posts").status_code == 200
    r = admin.post("/admin/sessions/end-others")
    assert "Logged out everywhere else" in r.headers["location"].replace("%20", " ")
    assert other.get("/admin/posts").headers["location"] == "/login"   # the other browser is out
    assert admin.get("/admin/posts").status_code == 200                 # this one stays in


def test_password_change_ends_other_sessions(app, admin):
    from starlette.testclient import TestClient
    from conftest import PASSWORD
    other = TestClient(app, follow_redirects=False)
    other.post("/login", data={"password": PASSWORD})
    r = admin.post("/admin/settings/password", data={"current": PASSWORD, "password": PASSWORD, "confirm": PASSWORD})
    assert "other devices" in r.text
    assert other.get("/admin/posts").headers["location"] == "/login"
    assert admin.get("/admin/posts").status_code == 200


def test_session_cookie_lifetime(app):
    from starlette.testclient import TestClient
    from conftest import PASSWORD
    c = TestClient(app, follow_redirects=False)
    r = c.post("/login", data={"password": PASSWORD, "keep": "1"})
    assert "Max-Age=1209600" in r.headers["set-cookie"]  # 14 days


def test_only_static_folder_is_served(client, tmp_path):
    # FastHTML's own catch-all served any .txt/.yml/.zip/... from the
    # working directory, and an encoded ../ walked out of it entirely
    secret = tmp_path / "secret-probe.txt"
    secret.write_text("TOPSECRET")
    ups = "%2e%2e/" * 12
    for path in ("/requirements.txt", "/docker-compose.yml", "/CHANGELOG.md",
                 f"/{ups}{str(secret).lstrip('/')}", f"/static/{ups}{str(secret).lstrip('/')}",
                 "/" + "..%2F" * 12 + str(secret).lstrip("/").replace("/", "%2F")):
        r = client.get(path)
        assert r.status_code == 404, path
        assert "TOPSECRET" not in r.text
    r = client.get("/static/vendor/htmx-2.0.7.min.js")
    assert r.status_code == 200 and "immutable" in r.headers["cache-control"]
    assert "cache-control" not in client.get("/static/nope.css").headers


def test_password_reset_link(client, admin):
    from soloblog import auth
    from conftest import PASSWORD
    assert "Forgot password?" in client.get("/login").text
    # no email set up: the page explains the RESET_PASSWORD route instead
    assert "RESET_PASSWORD=1" in client.get("/forgot-password").text
    assert "expired" in client.get("/reset-password?token=nope").text
    token = auth.start_reset()
    r = client.post("/reset-password", data={"token": token, "password": "brand new pass",
                                             "confirm": "brand new pass"})
    assert r.status_code == 303 and auth.verify_password("brand new pass")
    # used once, then gone - and the old logins are over
    assert not auth.reset_token_ok(token)
    assert admin.get("/admin/posts").status_code == 303
    auth.set_password(PASSWORD)
    admin.post("/login", data={"password": PASSWORD})


def test_new_comment_emails_the_admin(admin, client, monkeypatch):
    from soloblog import mail
    from soloblog import settings
    from conftest import save_post
    sent = []
    monkeypatch.setattr(mail, "send_email", lambda to, subject, body: sent.append((to, subject)) or True)
    slug = save_post(admin, title="Tell me about it")
    settings.set_many({"admin_email": "me@example.com", "notify_comments": "1"})
    try:
        client.post(f"/post/{slug}/comment", data={"author_name": "Ann", "email": "a@example.com", "body": "Hi"})
        import time
        for _ in range(50):
            if sent:
                break
            time.sleep(0.05)
        assert sent == [("me@example.com", "Ann commented on “Tell me about it”")]
    finally:
        settings.set_many({"admin_email": "", "notify_comments": "0"})


def test_no_inline_handlers_in_sections_and_galleries(admin, client):
    import re
    from conftest import save_post
    from page_samples import SAMPLES
    from soloblog.render import render_post
    from soloblog import gallery
    for style in gallery.STYLES:
        html, _ = render_post(f"```gallery {style}\n/uploads/a.webp | Cap\nhttps://example.com/b.jpg\n```\n")
        assert not re.findall(r"\son[a-z]+=", html), style
    for kind, (_title, summary, body) in SAMPLES.items():
        slug = save_post(admin, title=f"Handlers {kind}", body=body, summary=summary)
        page = client.get(f"/post/{slug}").text
        assert not re.findall(r"<[a-z][^>]*\son[a-z]+=", page), kind


def test_update_notice(admin, monkeypatch):
    from soloblog import config
    from soloblog import updates
    assert updates._key("v0.10.0") > updates._key("0.9.1") > updates._key("0.9.1-beta")
    # the betas before 1.0.0: each later one is newer, and 1.0.0 newer than all
    assert (updates._key("1.0.0") > updates._key("v1.0.0-beta.10") > updates._key("1.0.0-beta.2")
            > updates._key("1.0.0-beta") > updates._key("0.3.0-beta"))
    assert updates._key("1.0.0-beta.1") == updates._key("1.0.0-beta")
    assert updates._key("1.0.0-beta.x") is None and updates._key("one") is None
    monkeypatch.setattr(config, "UPDATE_CHECK", True)
    monkeypatch.setattr(updates, "_state", {"latest": "v9.0.0", "url": "https://example.com/r", "checked": 9e12,
                                            "running": False})
    assert "9.0.0 is out" in admin.get("/admin/settings").text
    monkeypatch.setattr(config, "UPDATE_CHECK", False)
    assert "is out" not in admin.get("/admin/settings").text
    monkeypatch.setattr(config, "UPDATE_CHECK", True)
    monkeypatch.setattr(updates, "_state", {"latest": "v" + config.VERSION, "url": "", "checked": 9e12,
                                            "running": False})
    assert "is out" not in admin.get("/admin/settings").text


def test_an_emailed_reset_keeps_two_factor(app, admin):
    """The inbox alone isn't a second factor: an emailed link can't turn
    two-factor authentication off, and the code is still asked for after it."""
    import time
    from starlette.testclient import TestClient
    from soloblog import auth, totp
    from conftest import PASSWORD
    secret = totp.new_secret()
    totp.enable(secret)
    try:
        attacker = TestClient(app, follow_redirects=False)
        token = auth.start_reset(60, by_email=True)
        page = attacker.get(f"/reset-password?token={token}").text
        assert "Also turn off two-factor authentication" not in page and "asked for a code next" in page
        r = attacker.post("/reset-password", data={"token": token, "password": "attacker pass 1",
                                                   "confirm": "attacker pass 1", "disable_2fa": "1"})
        assert r.headers["location"] == "/login/code" and totp.is_enabled()
        assert attacker.get("/admin/posts").status_code == 303
        code = totp._code_at(secret, int(time.time() // totp.STEP))
        assert attacker.post("/login/code", data={"code": code}).headers["location"].startswith("/admin/posts")
        # a link from the server's log proves more - that one may turn it off
        token = auth.start_reset(60)
        assert "Also turn off two-factor authentication" in TestClient(app).get(f"/reset-password?token={token}").text
        auth.finish_reset()
    finally:
        totp.disable()
        auth.set_password(PASSWORD)
        admin.post("/login", data={"password": PASSWORD})


def test_a_made_up_forwarded_address_counts_for_nothing(app):
    """Straight from the internet, X-Forwarded-For is whatever the visitor
    wrote - so it can't buy a new address for every password guess."""
    from starlette.testclient import TestClient
    from soloblog import ratelimit
    from soloblog.db import get_db
    get_db().execute("DELETE FROM rate_hits WHERE identifier IN ('ip:93.184.216.34', 'ip:10.0.0.9')")
    get_db().commit()
    direct = TestClient(app, follow_redirects=False, client=("93.184.216.34", 50000))
    pages = [direct.post("/login", data={"password": f"guess {i}"},
                         headers={"X-Forwarded-For": f"198.51.100.{i}"}).text for i in range(6)]
    assert "Too many attempts" in pages[-1]
    # behind a proxy on a private network, it's the proxy's word that counts
    class Req:
        headers = {"x-forwarded-for": "198.51.100.1, 192.0.2.44"}
        client = type("C", (), {"host": "10.0.0.9"})
    assert ratelimit.client_ip(Req) == "192.0.2.44"
    Req.client.host = "93.184.216.34"
    assert ratelimit.client_ip(Req) == "93.184.216.34"


def test_admin_pages_are_never_cached(admin, client):
    """Admin pages, and public ones seen with the admin's cookie, aren't
    kept by a shared cache or the back button - a visitor's page is
    untouched, and a route's own rule wins."""
    assert admin.get("/admin/posts").headers["cache-control"] == "private, no-store"
    assert admin.get("/").headers["cache-control"] == "private, no-store"
    assert "cache-control" not in client.get("/").headers
    assert "immutable" in admin.get("/static/vendor/htmx-2.0.7.min.js").headers["cache-control"]


def test_a_remote_author_link_is_only_ever_a_web_address():
    """A webmention's page, or a fediverse server, picks its author's link -
    javascript: and data: never become a link or an image here."""
    from soloblog import webmention
    from soloblog.render import web_url
    page = ('<div class="h-entry"><a class="p-author h-card" href="javascript:alert(1)">Eve'
            '<img class="u-photo" src="data:image/svg+xml,<svg onload=alert(1)>"></a>'
            '<a class="u-in-reply-to" href="https://blog.example/post/x">re</a></div>')
    info = webmention.parse(page, "https://evil.example/post", "https://blog.example/post/x")
    assert info["author_url"] == "" and info["author_photo"] == "" and info["author_name"] == "Eve"
    assert webmention.parse(page.replace("javascript:alert(1)", "/about"), "https://ok.example/p",
                            "https://blog.example/post/x")["author_url"] == "https://ok.example/about"
    for bad in ("javascript:alert(1)", " JaVaScRiPt:x", "data:text/html,x", "vbscript:x", "//evil.example", None, 5):
        assert web_url(bad) == ""
    assert web_url("https://mastodon.social/@ann") == "https://mastodon.social/@ann"


def test_an_image_too_big_to_decode_is_refused_before_it_is():
    """Decoding needs width x height x 3 bytes, whatever the file's size: a
    small PNG mustn't make the server find gigabytes. A big JPEG decodes
    at a fraction of its size, so a phone's 50-megapixel photo is fine."""
    import io
    import os
    import pytest
    from PIL import Image
    from soloblog import images
    big = io.BytesIO()
    Image.new("1", (8000, 8000)).save(big, "PNG")  # 64 megapixels, a few kB
    assert len(big.getvalue()) < 200_000
    with pytest.raises(ValueError, match="megapixels"):
        images.save_upload(big.getvalue(), "bomb.png")
    photo = io.BytesIO()
    Image.new("L", (7500, 7000), 128).save(photo, "JPEG", quality=50)  # 52.5 megapixels
    url = images.save_upload(photo.getvalue(), "huge-phone-photo.jpg")
    with Image.open(os.path.join(images.config.UPLOADS_DIR, url.rsplit("/", 1)[-1])) as img:
        assert max(img.size) == images.MAX_DIMENSION
    for name, data in (("x.svg", b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>'),
                       ("x.eps", b"%!PS-Adobe-3.0 EPSF-3.0\n%%BoundingBox: 0 0 10 10\n"), ("x.png", b"not an image")):
        with pytest.raises(ValueError):
            images.save_upload(data, name)


def test_a_huge_request_is_refused_before_it_is_read(app, admin):
    """Anyone not logged in may send 16 MB - a big upload to an admin
    address is refused at once, not read to disk first. An API key may
    send a media file; the admin, a backup to restore."""
    from starlette.testclient import TestClient
    from soloblog.app import BodyLimit
    visitor = TestClient(app, follow_redirects=False)
    big = b"x" * (BodyLimit.ANYONE + 1)
    assert visitor.post("/admin/media/upload", files={"file": ("big.bin", big)}).status_code == 413
    assert visitor.post("/post/x/comment", content=big,
                        headers={"content-type": "application/x-www-form-urlencoded"}).status_code == 413
    # an API key's request may be bigger - it's the key that's checked then
    assert visitor.post("/api/v1/media", files={"file": ("big.bin", big)},
                        headers={"Authorization": "Bearer sb_wrong"}).status_code == 401
    # the admin restoring a backup isn't held to it
    r = admin.post("/admin/backup/inspect", files={"backup_zip": ("site.zip", big, "application/zip")})
    # (and a file that isn't a zip at all is said so, not a server error)
    assert r.status_code == 200 and "doesn't look like a Soloblog backup" in r.text
    from soloblog import backup
    assert not backup.staged_restore()


def _fediverse_request(fediverse, key, key_id, names=("(request-target)", "host", "date", "digest")):
    import base64
    import hashlib
    import json
    from email.utils import formatdate
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    body = json.dumps({"type": "Like", "actor": "https://mastodon.social/users/alice"}).encode()
    headers = {"host": "blog.example", "date": formatdate(usegmt=True),
               "digest": "SHA-256=" + base64.b64encode(hashlib.sha256(body).digest()).decode()}
    lines = ["(request-target): post /ap/inbox" if n == "(request-target)" else f"{n}: {headers[n]}" for n in names]
    sig = base64.b64encode(key.sign("\n".join(lines).encode(), padding.PKCS1v15(), hashes.SHA256())).decode()
    headers["signature"] = f'keyId="{key_id}",algorithm="rsa-sha256",headers="{" ".join(names)}",signature="{sig}"'
    return headers, body


def test_a_fediverse_actor_lives_where_it_says(monkeypatch):
    """A profile fetched from evil.example can't say it's someone on
    mastodon.social - or its key would sign as them."""
    import pytest
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from soloblog import fediverse
    from soloblog.db import get_db
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.public_key().public_bytes(serialization.Encoding.PEM,
                                        serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    docs = {"https://evil.example/actor": {"id": "https://mastodon.social/users/alice", "type": "Person",
                                           "publicKey": {"publicKeyPem": pem}},
            "https://ok.example/users/bob": {"id": "https://ok.example/users/bob", "type": "Person",
                                             "publicKey": {"publicKeyPem": pem}}}
    monkeypatch.setattr(fediverse, "signed_get", lambda url: docs[url])
    get_db().execute("DELETE FROM ap_actors")
    headers, body = _fediverse_request(fediverse, key, "https://evil.example/actor#main-key")
    with pytest.raises(ValueError):
        fediverse.verify("POST", "/ap/inbox", headers, body)
    headers, body = _fediverse_request(fediverse, key, "https://ok.example/users/bob#main-key")
    assert fediverse.verify("POST", "/ap/inbox", headers, body)["id"] == "https://ok.example/users/bob"
    # a signature that doesn't cover where it was sent, or when, could be replayed here
    headers, body = _fediverse_request(fediverse, key, "https://ok.example/users/bob#main-key", ("host", "digest"))
    with pytest.raises(ValueError):
        fediverse.verify("POST", "/ap/inbox", headers, body)


def test_too_many_logins_says_how_long_to_wait(app):
    """Not how many tries are left (that helps a guesser) - when to try again."""
    from starlette.testclient import TestClient
    c = TestClient(app, follow_redirects=False)
    pages = [c.post("/login", data={"password": f"wrong {i}"}).text for i in range(6)]
    assert "remaining" not in pages[0].lower() and "Try again in 15 minutes." in pages[-1]


def test_every_admin_address_needs_the_admin(app, admin):
    """guards.admin_guard: all of /admin is behind the login, whatever a
    route does itself - a page goes to the login, a script gets a 401."""
    import re
    from starlette.testclient import TestClient
    from soloblog.guards import ADMIN_OPEN
    stranger = TestClient(app, follow_redirects=False)
    paths = sorted({(r.path, m) for r in app.routes for m in (getattr(r, "methods", None) or ())
                    if (r.path == "/admin" or r.path.startswith("/admin/")) and m in ("GET", "POST")})
    assert len(paths) > 100
    for path, method in paths:
        url = re.sub(r"\{[^}]+\}", "1", path)
        r = stranger.request(method, url)
        if path in ADMIN_OPEN:
            continue
        assert r.status_code == 303 and r.headers["location"] in ("/login", "/setup"), (method, path, r.status_code)
        # the same from a script's fetch()
        r = stranger.request(method, url, headers={"Sec-Fetch-Mode": "same-origin"})
        assert r.status_code == 401 and r.json()["error"], (method, path)
    # and from htmx, a real navigation
    r = stranger.post("/admin/settings/name", headers={"HX-Request": "true"})
    assert r.status_code == 200 and r.headers["HX-Redirect"] == "/login"


def test_on_fly_each_visitor_has_their_own_limits(monkeypatch):
    # on Fly.io every visitor was the site's own shared address (the last
    # X-Forwarded-For entry is Fly's edge), so anyone's five wrong
    # passwords locked the owner out too. Fly's Fly-Client-IP says who it is
    from soloblog import ratelimit
    monkeypatch.setenv("FLY_APP_NAME", "my-blog")

    class Req:
        headers = {"fly-client-ip": "203.0.113.7", "x-forwarded-for": "203.0.113.7, 66.241.125.211"}
        client = type("C", (), {"host": "172.16.23.250"})
    assert ratelimit.client_ip(Req) == "203.0.113.7"
    # reached straight from the internet, a visitor's own header is ignored
    Req.client.host = "93.184.216.34"
    assert ratelimit.client_ip(Req) == "93.184.216.34"
    # and off Fly, the header means nothing
    monkeypatch.delenv("FLY_APP_NAME")
    Req.client.host = "10.0.0.9"
    assert ratelimit.client_ip(Req) == "66.241.125.211"


def test_only_wrong_passwords_use_up_the_login_limit(client):
    # every sign-in counted, so an owner signing in on six devices within
    # 15 minutes was locked out by their own successes
    from conftest import PASSWORD
    for _ in range(7):
        client.cookies.clear()
        r = client.post("/login", data={"password": PASSWORD}, follow_redirects=False)
        assert r.status_code == 303, r.text[:200]
    # wrong ones still stop at five
    pages = [client.post("/login", data={"password": "nope"}).text for _ in range(6)]
    assert "Too many attempts" in pages[-1] and "Too many attempts" not in pages[0]


def test_the_uploads_folder_itself_is_not_found(client):
    """A crawler asking for /uploads/ (or the trash folder in it) got a
    server error: the folder was handed to FileResponse as if a file."""
    import os
    from soloblog import config
    os.makedirs(os.path.join(config.uploads_dir(), "_trash"), exist_ok=True)
    for path in ("/uploads/", "/uploads/_trash"):
        r = client.get(path)
        assert r.status_code == 404, path


def test_no_route_breaks_on_odd_input(tmp_path):
    """tools/fuzz_routes.py: every route, as a visitor and as the admin,
    sent empty and folder-like names, numbers too big for the database,
    odd characters and nonsense fields - none may answer with a server
    error. Its own data folder, as it sends the admin's forms nonsense."""
    import subprocess
    import sys
    # its throwaway site in pytest's own temporary folder, which pytest tidies
    import os
    r = subprocess.run([sys.executable, "tools/fuzz_routes.py"], capture_output=True, text=True, timeout=600,
                       env={**os.environ, "TMPDIR": str(tmp_path)})
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]


def test_a_folder_is_never_taken_for_an_upload(admin):
    """"" and "_sizes" named a whole folder: trashing "_sizes" would have
    moved the folder, renaming "" crashed. Only a plain file name counts."""
    import os
    from soloblog import config, images
    os.makedirs(os.path.join(config.uploads_dir(), "_sizes"), exist_ok=True)
    for name in ("", "_sizes", "_trash", ".hidden", "a/b", "..", "x\x00.png"):
        assert not images.plain_name(name), name
        assert not images.move_to_trash(name) and not images.delete_upload(name)
    assert os.path.isdir(os.path.join(config.uploads_dir(), "_sizes"))
    assert images.plain_name("balcony-tomatoes.webp")
    assert admin.post("/admin/media/rename/_sizes", data={"name": "x"}).status_code == 404


def test_an_id_too_big_for_the_database_is_not_found(admin):
    assert admin.get("/admin/revisions/99999999999999999999").status_code == 404


def test_saving_a_post_that_is_gone_says_so(admin):
    r = admin.post("/admin/save", data={"slug": "never-was-a-post", "title": "x", "body": "y"},
                   headers={"hx-request": "true"})
    assert r.status_code == 200 and "isn't here any more" in r.text


def test_asking_again_never_ends_a_reset_link_or_fills_the_inbox(app, monkeypatch):
    """Anyone can press "Email me a reset link". Doing it again and again
    must not end the link the admin already has, nor send them a pile of
    email. Links are kept as hashes, in Settings, not in the server's
    memory - a restart keeps them."""
    import json
    from starlette.testclient import TestClient
    from soloblog import auth, mail, settings
    from soloblog.routes import auth_routes
    before = {k: settings.get(k) for k in ("admin_email", "email_provider", "reset_links")}
    sent = []
    monkeypatch.setattr(mail, "send_email", lambda *a, **k: sent.append(a))
    monkeypatch.setattr(auth_routes.ratelimit, "hit", lambda *a, **k: True)
    settings.set_many({"admin_email": "owner@example.com", "email_provider": "smtp", "reset_links": ""})
    try:
        anyone = TestClient(app, follow_redirects=False)
        for _ in range(4):
            assert anyone.post("/forgot-password").headers["location"] == "/forgot-password?sent=1"
        assert len(sent) == 1
        link = sent[0][2].split("token=")[1].split()[0]
        assert auth.reset_token_ok(link)
        # nothing readable is kept: only the link's hash
        assert link not in settings.get("reset_links")
        # once the gap has passed another is sent, and the first still works
        kept = json.loads(settings.get("reset_links"))
        kept[0]["made"] -= auth.RESET_EMAIL_GAP + 1
        settings.set_many({"reset_links": json.dumps(kept)})
        anyone.post("/forgot-password")
        assert len(sent) == 2 and auth.reset_token_ok(link)
        # never more than a handful alive, and the newest is one of them
        last = [auth.start_reset() for _ in range(auth.RESET_LINKS + 3)][-1]
        assert len(json.loads(settings.get("reset_links"))) == auth.RESET_LINKS and auth.reset_token_ok(last)
        # an old one is no good, nor an empty or made-up one
        kept = json.loads(settings.get("reset_links"))
        kept[-1]["expires"] = 1
        settings.set_many({"reset_links": json.dumps(kept)})
        assert not auth.reset_token_ok(last) and not auth.reset_token_ok("") and not auth.reset_token_ok("x" * 32)
        # a damaged list is no links, not an error
        settings.set_many({"reset_links": "{not a list"})
        assert anyone.get(f"/reset-password?token={link}").status_code == 200
        # using one ends them all
        a, b = auth.start_reset(), auth.start_reset()
        auth.finish_reset()
        assert not auth.reset_token_ok(a) and not auth.reset_token_ok(b)
    finally:
        settings.set_many(before)


def test_an_upload_can_never_run_as_a_page_of_the_site(client):
    """A restored backup can put any file in uploads. Opened by its
    address, a page or a picture with a script in it must not run as the
    site, and a file that isn't media is saved, not shown."""
    import os
    from soloblog import config
    files = {"evil.html": b"<script>alert(1)</script>", "evil.svg": b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>",
             "notes.txt": b"hello", "paper.pdf": b"%PDF-1.4", "pic.webp": b"RIFF"}
    for name, data in files.items():
        with open(os.path.join(config.uploads_dir(), name), "wb") as f:
            f.write(data)
    try:
        for name in files:
            r = client.get(f"/uploads/{name}")
            assert r.status_code == 200 and r.headers["x-content-type-options"] == "nosniff", name
            shown = name in ("evil.svg", "paper.pdf", "pic.webp")
            assert ("attachment" not in r.headers.get("content-disposition", "")) == shown, name
            if not shown:
                assert r.headers["content-type"] == "application/octet-stream", name
            sandboxed = r.headers.get("content-security-policy", "").startswith("sandbox")
            assert sandboxed == (name != "paper.pdf"), name
    finally:
        for name in files:
            os.remove(os.path.join(config.uploads_dir(), name))


def test_guessing_from_everywhere_shuts_out_new_browsers_only(app, admin_account, monkeypatch):
    """Each address has its own limit, so thousands of them guessing
    together never reach it. Wrong passwords are counted across the site
    too: past the limit, a browser that hasn't logged in before can't try
    one - not even the right one - while the owner's own browser still can."""
    import threading
    from starlette.testclient import TestClient
    from conftest import PASSWORD
    from soloblog import config, mail, settings
    from soloblog.db import get_db
    from soloblog.routes import auth_routes

    def clear():
        get_db().execute("DELETE FROM rate_hits WHERE bucket LIKE 'login%'")
        get_db().commit()

    def run_now(target=None, args=(), **kw):
        return type("T", (), {"start": lambda self: target(*args)})()

    sent = []
    monkeypatch.setattr(mail, "send_email", lambda to, subject, body, **kw: sent.append((to, subject)) or True)
    monkeypatch.setattr(mail, "can_send", lambda: True)
    monkeypatch.setattr(threading, "Thread", run_now)
    settings.set_many({"admin_email": "owner@example.com", "signin_alerts": "1"})
    clear()

    owner = TestClient(app, follow_redirects=False, client=("203.0.113.5", 50000))
    assert owner.post("/login", data={"password": PASSWORD}).status_code in (302, 303)
    owner.post("/logout")
    sent.clear()

    # a different address for every guess: no one address is near its limit
    for i in range(auth_routes.SITE_WRONG):
        guesser = TestClient(app, follow_redirects=False, client=(f"198.51.100.{i + 1}", 50000))
        assert "Wrong password" in guesser.post("/login", data={"password": f"guess {i}"}).text
    assert len(sent) == 1 and sent[0][0] == "owner@example.com" and "guessing" in sent[0][1]

    fresh = TestClient(app, follow_redirects=False, client=("198.51.100.200", 50000))
    page = fresh.post("/login", data={"password": PASSWORD})
    assert page.status_code == 200 and "Too many wrong passwords" in page.text
    assert "Log out" not in fresh.get("/admin", follow_redirects=True).text
    # more guesses are turned away unread, and don't write again
    fresh.post("/login", data={"password": "guess again"})
    assert len(sent) == 1

    # the owner's browser has been here before
    assert owner.post("/login", data={"password": PASSWORD}).status_code in (302, 303)

    # the demo's password is public: wrong ones there shut nobody out
    monkeypatch.setattr(config, "DEMO_MODE", True)
    assert "Too many wrong passwords" not in fresh.post("/login", data={"password": "nope"}).text
    clear()


def test_a_json_body_that_isnt_an_object_is_a_bad_request(client):
    # FastHTML reads it before the route runs - this used to be a server error everywhere
    for body in (b"{not json", b"[1, 2]", b'"words"', b"\xff"):
        for path in ("/login", "/search", "/post/x/comment"):
            r = client.post(path, content=body, headers={"content-type": "application/json"})
            assert r.status_code == 400, (path, body, r.status_code)
    # an object still reaches the route, and other JSON types aren't touched
    assert client.post("/login", content=b'{"password": "x"}',
                       headers={"content-type": "application/json"}).status_code < 500
    assert client.post("/search", content=b"[1]",
                       headers={"content-type": "application/activity+json"}).status_code != 400
    # an API answers bad JSON in its own words
    r = client.post("/mcp", content=b"{nope", headers={"content-type": "application/json"})
    assert r.status_code != 400 or "jsonrpc" in r.text
