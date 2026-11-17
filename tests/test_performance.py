import io
import os

from PIL import Image

from soloblog import app as app_module
from soloblog import config
from soloblog import images
from soloblog import settings
from soloblog.render import render_post


def _upload(name, size=(1200, 600)):
    os.makedirs(config.UPLOADS_DIR, exist_ok=True)
    Image.new("RGB", size, (30, 120, 200)).save(os.path.join(config.UPLOADS_DIR, name), "WEBP")
    images.cache.bump()
    return f"/uploads/{name}"


def test_settings_are_cached_until_changed():
    before = settings.get("tagline")
    settings.set_many({"tagline": "Cached?"})
    assert settings.get("tagline") == "Cached?"
    copy = settings.get_all()
    copy["tagline"] = "changed by a caller"
    assert settings.get("tagline") == "Cached?"
    settings.set_many({"tagline": before})
    assert settings.get("tagline") == before


def test_rendered_posts_are_cached_until_something_changes():
    url = _upload("perf-caption.webp")
    body = f"Intro\n\n![]({url})\n"
    first = render_post(body)
    assert render_post(body) is first
    images.set_meta("perf-caption.webp", "Alt", "A fresh caption")
    again = render_post(body)
    assert again is not first and "A fresh caption" in again[0]
    images.delete_upload("perf-caption.webp")


def test_smaller_copies_of_uploads(client):
    url = _upload("perf-wide.webp")
    assert images.srcset(url) == f"{url}?w=400 400w, {url}?w=800 800w, {url} 1200w"
    r = client.get(url + "?w=400")
    # an hour, not immutable - an image can be edited in place
    assert r.status_code == 200 and "max-age=3600" in r.headers["cache-control"]
    assert Image.open(io.BytesIO(r.content)).size == (400, 200)
    # any other width is just the original
    assert Image.open(io.BytesIO(client.get(url + "?w=123").content)).size == (1200, 600)
    # the copies stay out of the media library, and go with the original
    assert all("_sizes" not in i["filename"] for i in images.list_uploads())
    images.delete_upload("perf-wide.webp")
    assert not os.path.exists(os.path.join(config.UPLOADS_DIR, "_sizes", "400", "perf-wide.webp"))


def test_small_images_get_no_srcset():
    url = _upload("perf-small.webp", (300, 200))
    assert images.srcset(url) == ""
    assert images.thumb(url) == url
    assert images.srcset("https://example.com/a.jpg") == ""
    images.delete_upload("perf-small.webp")


def test_post_images_carry_srcset():
    url = _upload("perf-body.webp")
    html, _ = render_post(f"Intro\n\n![A photo]({url})\n\n```gallery grid\n{url}\n```\n")
    assert html.count(f'{url}?w=400 400w') == 2
    images.delete_upload("perf-body.webp")


def test_shared_scripts_are_one_cached_file(client):
    page = client.get("/").text
    assert f'/app.js?v={app_module.APP_JS_VERSION}' in page
    assert "function showStatus" not in page
    r = client.get("/app.js")
    assert r.status_code == 200 and "function showStatus" in r.text
    assert "immutable" in r.headers["cache-control"]


def test_rotate_crop_and_restore(admin):
    url = _upload("perf-edit.webp", (1200, 600))
    admin.post("/admin/media/edit/perf-edit.webp", data={"action": "right"}, headers={"hx-request": "true"})
    assert images._dimensions(os.path.join(config.UPLOADS_DIR, "perf-edit.webp")) == (600, 1200)
    r = admin.post("/admin/media/edit/perf-edit.webp", data={"action": "crop", "ratio": "1:1", "keep": "top"},
                   headers={"hx-request": "true"})
    assert "Cropped" in r.text and "Restore original" in r.text
    assert images._dimensions(os.path.join(config.UPLOADS_DIR, "perf-edit.webp")) == (600, 600)
    # the smaller copies are made again from the edited file
    assert images.srcset(url) == f"{url}?w=400 400w, {url} 600w"
    r = admin.post("/admin/media/edit/perf-edit.webp", data={"action": "restore"}, headers={"hx-request": "true"})
    assert "Restored" in r.text and "Restore original" not in r.text
    assert images._dimensions(os.path.join(config.UPLOADS_DIR, "perf-edit.webp")) == (1200, 600)
    r = admin.post("/admin/media/edit/perf-edit.webp", data={"action": "crop", "ratio": "7:3"}, headers={"hx-request": "true"})
    assert "Couldn't edit" in r.text
    admin.post("/admin/media/edit/perf-edit.webp", data={"action": "left"}, headers={"hx-request": "true"})
    assert images.has_original("perf-edit.webp")
    images.delete_upload("perf-edit.webp")
    assert not images.has_original("perf-edit.webp")


def test_visitors_do_not_download_the_admin_scripts(client, admin):
    visitor_js, admin_js = client.get("/app.js").text, client.get("/admin.js")
    assert admin_js.status_code == 200 and "immutable" in admin_js.headers["cache-control"]
    for script in app_module.ADMIN_SCRIPTS:
        assert script.strip() in admin_js.text and script.strip() not in visitor_js
    for script in app_module.SHARED_SCRIPTS:
        assert script.strip() not in admin_js.text
    tag = f'/admin.js?v={app_module.ADMIN_JS_VERSION}'
    assert tag not in client.get("/").text
    # the admin's own pages, and any page they see signed in, load it after app.js
    for path in ("/admin/posts", "/admin/new", "/", "/archive"):
        page = admin.get(path).text
        assert tag in page and page.index("/app.js?v=") < page.index(tag), path


def test_visitor_scripts_never_call_the_admins_unguarded():
    # syncUnsaved moved to /admin.js, and the contact form's save broke on
    # a visitor's page: any call from app.js must check it's there first
    import re
    from soloblog import app as app_module
    admin_only = set(re.findall(r"^function (\w+)\(", app_module.ADMIN_JS, re.M))
    bare = []
    for name in admin_only:
        for m in re.finditer(rf"(?<![\w.]){name}\(", app_module.APP_JS):
            before = app_module.APP_JS[max(0, m.start() - 60):m.start()]
            if f"typeof {name} === 'function'" not in before and not before.rstrip().endswith("function"):
                bare.append(name)
    assert not bare, bare
