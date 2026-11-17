from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit

from soloblog import comments
from soloblog import images
from soloblog import posts
from conftest import save_post


def _status(location):
    """The ?toast=, ?toast_type= and ?undo= a redirect carries."""
    query = parse_qs(urlsplit(location).query)
    return {k: v[0] for k, v in query.items()}


def _undo(admin, undo):
    """What the Undo button does: POST the undo URL's fields to its path."""
    parts = urlsplit(undo)
    fields = {k: v[0] for k, v in parse_qs(parts.query).items()}
    return admin.post(parts.path, data=fields)


def test_admin_lists_are_live(admin):
    for path in ("/admin/posts", "/admin/comments", "/admin/media", "/admin/messages"):
        html = admin.get(path).text
        tag = re.search(r'<div[^>]*id="page-content"[^>]*>', html).group(0)
        assert 'data-live="1"' in tag, path
    # the editor and settings still behave as ordinary pages
    assert 'data-live="1"' not in admin.get("/admin/settings").text
    assert 'data-live="1"' not in admin.get("/admin/new").text


def test_live_swap_gets_content_and_menu(admin):
    # LIVE_JS asks with HX-Request and swaps #page-content, plus the admin
    # sidebar's counts - both have to be in FastHTML's body-only answer
    html = admin.get("/admin/posts", headers={"HX-Request": "true"}).text
    assert 'id="page-content"' in html
    assert 'id="admin-nav"' in html and 'id="admin-nav-margin"' in html


def test_trash_post_then_undo(admin):
    slug = save_post(admin, title="Undo me")
    back = "/admin/posts?status=all&sort=newest&tag="
    r = admin.post("/admin/delete", data={"slug": slug, "return_to": back})
    assert r.status_code == 303
    status = _status(r.headers["location"])
    assert status["toast"] == "Moved to trash"
    assert urlsplit(status["undo"]).path == "/admin/posts/restore"
    assert posts.get_post(slug) is None or posts.get_post(slug).get("trashed_at")

    r = _undo(admin, status["undo"])
    assert r.status_code == 303
    assert r.headers["location"].startswith(back)
    assert _status(r.headers["location"])["toast"] == "Restored"
    assert posts.get_post(slug) is not None


def test_trash_comment_then_undo(admin, client):
    slug = save_post(admin, title="Comment undo")
    client.post(f"/post/{slug}/comment",
                data={"author_name": "V", "email": "v@example.com", "body": "Undo this comment", "website": ""})
    comment = [c for c in comments.list_by_status("pending", per_page=500) if c["body"] == "Undo this comment"][0]
    r = admin.post("/admin/comments/delete", data={"comment_id": comment["id"], "tab": "pending", "post": ""})
    status = _status(r.headers["location"])
    assert status["toast"] == "Moved to trash"
    assert comments.get(comment["id"])["trashed_at"]

    r = _undo(admin, status["undo"])
    assert r.headers["location"].startswith("/admin/comments?tab=pending")
    assert not comments.get(comment["id"])["trashed_at"]


def test_trash_image_then_undo(admin):
    import os
    from soloblog import config
    name = "undo-test.webp"
    os.makedirs(config.UPLOADS_DIR, exist_ok=True)
    with open(os.path.join(config.UPLOADS_DIR, name), "wb") as f:
        f.write(b"not really an image")
    r = admin.post("/admin/media/trash", data={"filename": name, "return_to": "/admin/media?tab=unused"})
    status = _status(r.headers["location"])
    assert status["toast"] == "Moved to trash"
    assert not os.path.exists(os.path.join(config.UPLOADS_DIR, name))

    r = _undo(admin, status["undo"])
    assert r.headers["location"].startswith("/admin/media?tab=unused")
    assert os.path.exists(os.path.join(config.UPLOADS_DIR, name))
    images.delete_upload(name)


def test_media_trash_tab_shows_a_trashed_image(admin):
    import io
    import os
    from PIL import Image
    from soloblog import config
    name = "trash-tab-test.png"
    os.makedirs(config.UPLOADS_DIR, exist_ok=True)
    buf = io.BytesIO()
    Image.new("RGB", (20, 20), "red").save(buf, "PNG")
    with open(os.path.join(config.UPLOADS_DIR, name), "wb") as f:
        f.write(buf.getvalue())
    admin.post("/admin/media/trash", data={"filename": name, "return_to": "/admin/media"})
    try:
        r = admin.get("/admin/media?tab=trash&q=&kind=")
        assert r.status_code == 200 and name in r.text
    finally:
        images.restore_from_trash(name)
        images.delete_upload(name)


def test_undo_never_redirects_off_site(admin):
    slug = save_post(admin, title="Undo off site")
    admin.post("/admin/delete", data={"slug": slug})
    r = admin.post("/admin/posts/restore", data={"slug": slug, "return_to": "//evil.example/x"})
    assert r.headers["location"].startswith("/admin/posts?status=trash")
    # and a foreign return_to never becomes an Undo link either
    r = admin.post("/admin/delete", data={"slug": slug, "return_to": "https://evil.example/"})
    status = _status(r.headers["location"])
    assert "evil" not in status["undo"]


def test_leaving_with_unsaved_changes_offers_save(admin):
    # the shared confirm dialog has a Save and leave button, hidden until
    # the leave-page check asks with something to save (saveThenLeave)
    for path in ("/admin/new", "/admin/settings"):
        html = admin.get(path).text
        assert 'id="confirm-save-btn"' in html, path
    js = admin.get("/admin.js").text
    assert "saveThenLeave" in js and "_t('Discard'), function () { saveThenLeave(a.href); }, _t('Save'))" in js
    assert "_t('Save changes before you leave?')" in js


def test_save_and_leave_can_tell_a_failed_save(admin):
    # saveThenLeave only goes on when a save was accepted: a redirect or
    # a green status. A refused one answers 200 with a red status, which
    # it has to see to stay on the page.
    first = save_post(admin, title="First post")
    second = save_post(admin, title="Second post")
    refused = admin.post("/admin/save", headers={"hx-request": "true"},
                         data={"title": "Second post", "body": "Hi.", "slug": second, "new_slug": first})
    assert refused.status_code == 200 and "text-error" in refused.text
    saved = admin.post("/admin/save", headers={"hx-request": "true"},
                       data={"title": "Second post", "body": "Edited.", "slug": second})
    assert saved.status_code == 200 and "text-success" in saved.text and "text-error" not in saved.text


def test_an_undo_this_site_did_not_offer_never_reaches_the_page(admin, client):
    """The Undo button sends a POST as the admin to the path in ?undo=. A
    link from elsewhere could name any admin action there - so only an
    undo the site signed, a few minutes ago, stays in the address."""
    import time
    from soloblog import guards
    forged = "/admin/settings/email?admin_email=thief@example.com&admin_email_confirm=thief@example.com"
    for path in ("/admin/posts", "/", "/admin/no-such-page"):
        for who in (admin, client):
            r = who.get(path, params={"toast": "Session expired", "undo": forged})
            assert r.status_code == 303, path
            assert "undo" not in r.headers["location"] and "toast=Session" in r.headers["location"], path
    # a signature from another undo, one that's run out, or none at all
    real = guards.undo_url("/admin/posts/restore", slug="x", return_to="/admin/posts")
    for sig in (guards.sign_undo(real + "x"), guards.sign_undo(real, time.time() - guards.UNDO_LIFE - 5), "", "1.2", "x"):
        r = admin.get("/admin/posts", params={"toast": "Moved to trash", "undo": real, "undo_sig": sig})
        assert r.status_code == 303 and "undo" not in r.headers["location"], sig
    assert admin.get("/admin/posts", params={"undo_sig": guards.sign_undo(real)}).status_code == 303
    # the site's own: as it was
    slug = save_post(admin, title="Signed undo")
    r = admin.post("/admin/delete", data={"slug": slug, "return_to": "/admin/posts"})
    status = _status(r.headers["location"])
    assert guards.undo_signed(status["undo"], status["undo_sig"])
    assert admin.get(r.headers["location"]).status_code == 200
    _undo(admin, status["undo"])


def test_the_undo_button_only_puts_things_back():
    """And in the browser: only a list's own restore address gets a button."""
    js = Path("soloblog/js/toast.js").read_text(encoding="utf-8")
    assert "if (_isUndoPath(undo))" in js and "restore$/" in js
    for name in ("toast.js", "live.js"):
        assert "undo_sig" in Path(f"soloblog/js/{name}").read_text(encoding="utf-8"), name
    import re as _re
    made = _re.findall(r'undo_url\("([^"]+)"', "".join(
        p.read_text(encoding="utf-8") for p in __import__("pathlib").Path("soloblog/routes").rglob("*.py")))
    assert made and all(_re.fullmatch(r"/admin/[a-z]+/restore", m) for m in made), made
