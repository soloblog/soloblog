"""The public demo (DEMO_MODE=1): its own process, since config is read
once at import."""
from pathlib import Path
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCRIPT = r'''
import os, sys
sys.path.insert(0, os.getcwd())
from soloblog.app import app
from soloblog import settings, config
from starlette.testclient import TestClient
from contextlib import contextmanager
from soloblog import demo


@contextmanager
def seen_by(client):
    """What this visitor's own copy of the site holds."""
    token = config.VISITOR_DIR.set(demo._copies[client.cookies.get("soloblog_demo")])
    try:
        yield
    finally:
        config.VISITOR_DIR.reset(token)


c = TestClient(app, follow_redirects=False)
home = c.get("/").text
assert "Soloblog demo</strong> · resets in" in home and "Mira Castell" in home, "banner"
# floating, so it never moves the site's own layout, and it can be put away
assert "data-demo-note" in home and "closeDemoNote" in home and "fixed z-40 bottom-" in home
# on a phone one line, which opens to its links
assert 'id="demo-note-more"' in home and 'for="demo-note-more"' in home
assert home.count("max-sm:hidden max-sm:peer-checked:block") == 1, "the links fold away on a phone"
# each page says what it's made with, and every template has a page to see it on
assert 'href="/tour"' in home and 'href="/templates"' in home and "This page:" not in home, "the tour, in the menu"
assert ">Take the tour</a>" in home, "the tour, in the note"
every_template = c.get("/templates").text
assert "Every template" in every_template and every_template.count("block overflow-hidden rounded-box") >= 15, "templates page"
assert 'id="writing"' in every_template and 'href="/sections"' in every_template, "grouped, then sections"
styles = c.get("/styles").text
assert "/demo/style/magazine" in styles and 'href="/demo/style"' in styles, "styles to try, and the way back"
tour = c.get("/tour").text
assert 'data-section="hero"' in tour and 'href="/sections"' in tour and 'href="/styles"' in tour, "the tour"
# Mira's work in every arrangement, from her Work page and from each copy of it
work = c.get("/projects").text
assert all(f'href="/post/projects-{k}"' in work for k in ("grid", "masonry", "rows", "screen", "sideways")), "views"
rows = c.get("/post/projects-rows").text
assert "<strong>Rows</strong>" in rows and 'href="/post/projects-grid"' in rows, "the one shown, in bold"
wiki = c.get("/wiki").text
assert "How these notes work" in wiki and "Recently edited" in wiki and "Hydration" in wiki, "wiki"
assert 'content="noindex, nofollow"' in home and "Disallow: /" in c.get("/robots.txt").text
assert "Password: <strong>demo</strong>" in c.get("/login").text
r = c.post("/login", data={"password": "demo"})
assert r.status_code == 303, ("login", r.status_code)
# logged in, the site's own pages don't claim to be the admin
assert "Open the admin" in c.get("/").text, "banner on site"
admin_page = c.get("/admin/settings").text
assert "Soloblog demo</strong>" in admin_page and "Everyone sees" not in admin_page and ">Open the admin</a>" not in admin_page
# the password, secrets and outbound requests are refused
r = c.post("/admin/settings/password", data={"current": "demo", "new": "hijacked1", "confirm": "hijacked1"},
           headers={"HX-Request": "true"})
assert "Not in the demo" in r.text, "password"
r = c.post("/admin/settings/integrations", data={"smtp_host": "evil"}, headers={"Referer": "http://testserver/admin/settings?tab=integrations"})
assert r.status_code == 303 and "Not+in+the+demo" in r.headers["location"].replace("%20", "+"), r.headers.get("location")
# the mail server saves from the Email page too - refused there as well
r = c.post("/admin/settings/email", data={"smtp_host": "evil"}, headers={"Referer": "http://testserver/admin/settings?tab=email"})
assert r.status_code == 303 and "Not+in+the+demo" in r.headers["location"].replace("%20", "+"), r.headers.get("location")
# refused, it goes back to the tab it came from - restoring a backup isn't
# for a shared demo, and the message shows beside the Upload button
r = c.post("/admin/backup/inspect", headers={"Referer": "http://testserver/admin/settings?tab=backup&toast=Old"})
loc = r.headers["location"]
assert loc.startswith("/admin/settings?tab=backup&toast=") and "Old" not in loc, loc
# the banner's link into the admin goes somewhere
assert c.get("/admin").headers["location"] == "/admin/posts", "admin link"
# what the server itself would call - a translation server inside the
# network, the site's own address - can't be changed, by any form
before = {k: settings.get(k) for k in ("translate_url", "translate_provider", "site_url")}
c.post("/admin/settings/url", data={"translate_provider": "libretranslate", "translate_url": "http://10.0.0.9:5000",
                                     "site_url": "https://evil.example",
                                     "declared_fields": "translate_provider,translate_url,site_url"},
       headers={"HX-Request": "true"})
with seen_by(c):
    assert {k: settings.get(k) for k in before} == before, "server-side settings"
# a visitor tries a style, just for themselves - the site's own is untouched
v = TestClient(app, follow_redirects=False)
r = v.get("/demo/style/photo")
assert r.status_code == 303 and "preview_preset=photo" in r.headers["set-cookie"], "style"
v.cookies.set("preview_preset", "photo")
page = v.get("/").text
assert "Trying the " in page and "Photo journal" in page and "/demo/style/magazine" in page, "trying"
assert ">Back to Mira&#x27;s look<" in page.replace("'", "&#x27;") and "Use it" not in page, "the way back"
# (Mira's covers fill the screen; the photo journal's run edge to edge)
assert settings.get("cover_width") == "screen" and settings.get("roll_style") == "cards", "untouched"
# one cookie, as a browser keeps it - a newer Starlette's test client sent the
# style's own Set-Cookie and this one side by side
v.cookies.clear()
v.cookies.set("preview_preset", "portfolio")
assert "Things I&#x27;ve made in the evenings" in v.get("/").text.replace("'", "&#x27;"), "portfolio shows Mira's projects page"
assert "/demo/style/photo" in TestClient(app).get("/styles").text, "offered"
# custom code is kept out of the pages; everything else saves
c.post("/admin/settings/url", data={"custom_head": "<script>alert(1)</script>", "redirects": "/x /about",
                                     "declared_fields": "custom_head,redirects"}, headers={"HX-Request": "true"})
with seen_by(c):
    assert settings.get("custom_head") == "" and settings.get("redirects") == "/x /about"
# members: shown, but nobody's email is taken and nothing is paid
v = TestClient(app, follow_redirects=False)
paid = v.get("/post/the-five-minute-rule-and-other-tricks-for-finishing-things").text
assert "This post is for paid members" in paid and "Tell one person" not in paid, "paid post"
assert "US$4" in v.get("/membership").text, "plans"
r = v.post("/join", data={"email": "someone@example.com"}, headers={"Referer": "http://testserver/join"})
assert "Not+in+the+demo" in r.headers["location"].replace("%20", "+"), "join"
from soloblog.db import get_db
assert not get_db().execute("SELECT 1 FROM member_tokens").fetchone(), "join kept an address"
with seen_by(v):
    assert not get_db().execute("SELECT 1 FROM member_tokens").fetchone(), "join kept an address"
assert v.post("/stripe/webhook", content=b"{}").status_code != 200, "webhook"
c.post("/admin/settings/members", data={"members_enabled": "1", "stripe_key": "rk_live_x", "members_price_month": "9",
                                        "declared_fields": "members_enabled,stripe_key,members_price_month"},
       headers={"HX-Request": "true"})
with seen_by(c):
    assert settings.get("stripe_key") == "rk_test_demo" and settings.get("members_price_month") == "4", "stripe locked"

# what one visitor writes, nobody else sees: a post, an edit to one of
# Mira's, an upload, a setting, a comment left without logging in
import io
from PIL import Image
r = c.post("/admin/save", data={"title": "Rude words here", "body": "Offensive text.", "published": "1",
                                "comments_enabled": "1"}, headers={"hx-request": "true"})
assert r.status_code == 200, ("save", r.status_code)
slug = "the-five-minute-rule-and-other-tricks-for-finishing-things"
from soloblog import posts
with seen_by(c):
    mine = posts.get_post(slug)
r = c.post("/admin/save", data={"slug": slug, "title": "Defaced", "body": "Offensive text.", "published": "1",
                                "comments_enabled": "1", "visibility": mine["visibility"]},
           headers={"hx-request": "true"})
assert r.status_code == 200, ("edit", r.status_code)
c.post("/admin/settings/name", data={"site_title": "Rude title", "declared_fields": "site_title"},
       headers={"HX-Request": "true"})
png = io.BytesIO()
Image.new("RGB", (40, 30), "red").save(png, "PNG")
c.post("/admin/media/upload", files={"image": ("rude-picture.png", png.getvalue(), "image/png")})
with seen_by(c):
    upload = [f for f in os.listdir(config.uploads_dir()) if f.startswith("rude-picture")]
assert upload and not os.path.exists(os.path.join(config.uploads_dir(), upload[0])), "uploaded, for them"
upload = upload[0]
commenter = TestClient(app, follow_redirects=False)
commenter.post("/post/hydration/comment", data={"body": "A rude comment", "author_name": "Troll"},
               headers={"hx-request": "true"})
# the visitor sees their own changes
home = c.get("/").text
assert "Rude title" in home and "Rude words here" in c.get("/search/results?q=Rude").text, "theirs"
assert "Defaced" in c.get(f"/post/{slug}").text, "their edit"
assert commenter.cookies.get("soloblog_demo"), "a copy of their own, for their comment"
assert not get_db().execute("SELECT 1 FROM comments WHERE author_name = 'Troll'").fetchone(), "not on the site"
assert c.get("/uploads/" + upload).status_code == 200
# everyone else - logged out, or another visitor logged in - sees Mira's site
other = TestClient(app, follow_redirects=False)
d = TestClient(app, follow_redirects=False)
assert d.post("/login", data={"password": "demo"}).status_code == 303
for who in (other, d):
    assert "Rude words" not in who.get("/search/results?q=offensive").text, "search"
    for page in ("/", "/rss", "/atom.xml", "/feed.json", "/sitemap.xml", "/post/hydration",
                 f"/post/{slug}", "/admin/posts", "/admin/comments", "/admin/media"):
        text = who.get(page).text
        assert not any(w in text for w in ("Rude", "Defaced", "Offensive", "Troll")), (page, who is d)
    assert who.get("/uploads/" + upload).status_code == 404, "upload"
assert "Mira Castell" in other.get("/").text and settings.get("site_title") == "Mira Castell"
assert not get_db().execute("SELECT 1 FROM posts WHERE title LIKE '%Rude%' OR title = 'Defaced'").fetchone()
print("ok")
'''


def _run(data, extra=None):
    env = {**os.environ, "DEMO_MODE": "1", "DEMO_OFFLINE": "1", "DATA_DIR": str(data), "SESSION_SECRET": "t",
           "UPDATE_CHECK": "0", **(extra or {})}
    env.pop("ENV", None)
    return subprocess.run([sys.executable, "-c", SCRIPT], cwd=ROOT, env=env, capture_output=True, text=True,
                          timeout=240)


def test_demo_mode(tmp_path):
    r = _run(tmp_path / "data")
    assert r.returncode == 0 and "ok" in r.stdout, (r.stdout + r.stderr)[-3000:]
    assert (tmp_path / "data" / ".soloblog-demo").exists()
    # a second start soon after (a sleeping host waking it) keeps the copy;
    # one after the reset time wipes and rebuilds it
    (tmp_path / "data" / "kept.txt").write_text("still here")
    r = _run(tmp_path / "data")
    assert r.returncode == 0 and (tmp_path / "data" / "kept.txt").exists(), r.stderr[-2000:]
    # a copy made by an older build of the app is rebuilt - its database
    # may miss a column the new one needs
    marker = tmp_path / "data" / ".soloblog-demo"
    built = marker.read_text()
    marker.write_text("The Soloblog demo: this folder is wiped and rebuilt every few hours.\n")
    r = _run(tmp_path / "data")
    assert r.returncode == 0 and not (tmp_path / "data" / "kept.txt").exists(), r.stderr[-2000:]
    assert marker.read_text() == built
    (tmp_path / "data" / "kept.txt").write_text("still here")
    old = os.path.getmtime(tmp_path / "data" / ".soloblog-demo") - 4 * 3600
    os.utime(tmp_path / "data" / ".soloblog-demo", (old, old))
    r = _run(tmp_path / "data")
    assert r.returncode == 0 and not (tmp_path / "data" / "kept.txt").exists(), r.stderr[-2000:]


def test_demo_mode_leaves_a_real_blog_alone(tmp_path):
    real = tmp_path / "real"
    (real / "posts").mkdir(parents=True)
    (real / "posts" / "my-post.md").write_text("---\ntitle: Mine\n---\nMine.", encoding="utf-8")
    r = _run(real)
    assert r.returncode != 0 and "isn't the demo" in r.stderr
    assert (real / "posts" / "my-post.md").exists()


def test_demo_mode_on_a_fresh_volume(tmp_path):
    # a new disk's lost+found (a Fly.io volume has one) isn't a blog
    (tmp_path / "data" / "lost+found").mkdir(parents=True)
    r = _run(tmp_path / "data")
    assert r.returncode == 0 and "ok" in r.stdout, (r.stdout + r.stderr)[-2000:]
    assert (tmp_path / "data" / "lost+found").exists()
    # nor is the app's own .session_secret, written before demo mode looks
    # when the host sets no SESSION_SECRET
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    (fresh / ".session_secret").write_text("x" * 64)
    r = _run(fresh)
    assert r.returncode == 0 and "ok" in r.stdout, (r.stdout + r.stderr)[-2000:]


def test_the_data_folder_is_read_through_the_visitors_copy():
    # the demo's copies only work if every read goes through these - a
    # direct config.UPLOADS_DIR wrote a visitor's upload into the shared
    # folder, where everyone could see it
    import glob
    import re
    direct = re.compile(r"\bconfig\.(DATA_DIR|POSTS_DIR|UPLOADS_DIR|DB_PATH)\b")
    found = [f"{path}:{n}" for path in glob.glob(os.path.join(ROOT, "soloblog", "**", "*.py"), recursive=True)
             if not path.endswith("config.py")
             for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1) if direct.search(line)]
    assert not found, found


def test_miras_footer_is_short():
    # two rows on a wide screen: her links and the © on the left, Privacy
    # and Powered by on the right - no notes link, bio or browse links
    src = Path(os.path.join(ROOT, "soloblog", "demo.py")).read_text(encoding="utf-8")
    assert '"footer_layout": "split", "footer_order": "socials,note,|,links,small"' in src
    assert '"footer_show_bio": "0", "footer_show_browse": "0"' in src
    notes = src[src.index('("notes-start-here"'):src.index('("notes-hydration"')]
    assert 'pin_location="footer"' not in notes
