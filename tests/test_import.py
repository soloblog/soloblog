import io
import json
import time
import zipfile

from PIL import Image

from soloblog import comments
from soloblog import importers
from soloblog import posts

WXR = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:excerpt="http://wordpress.org/export/1.2/excerpt/"
  xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:wp="http://wordpress.org/export/1.2/">
<channel><title>Old WP</title>
<item>
  <title>Hello from WordPress</title>
  <wp:post_name>hello-from-wordpress</wp:post_name>
  <wp:post_type>post</wp:post_type><wp:status>publish</wp:status>
  <wp:post_date_gmt>2019-03-04 05:06:07</wp:post_date_gmt>
  <category domain="category" nicename="uncategorized"><![CDATA[Uncategorized]]></category>
  <category domain="post_tag" nicename="travel"><![CDATA[Travel]]></category>
  <excerpt:encoded><![CDATA[A short trip.]]></excerpt:encoded>
  <content:encoded><![CDATA[First paragraph with <strong>bold</strong>.

[caption id="x" align="alignnone"]<img src="https://example.com/a.jpg" alt="A view" /> A view[/caption]

<iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ"></iframe>

Last line.]]></content:encoded>
  <wp:comment><wp:comment_id>7</wp:comment_id><wp:comment_author>Reader</wp:comment_author>
    <wp:comment_author_email>r@example.com</wp:comment_author_email>
    <wp:comment_date_gmt>2019-03-05 00:00:00</wp:comment_date_gmt>
    <wp:comment_content><![CDATA[<p>Great post</p>]]></wp:comment_content>
    <wp:comment_approved>1</wp:comment_approved><wp:comment_type></wp:comment_type><wp:comment_parent>0</wp:comment_parent></wp:comment>
  <wp:comment><wp:comment_id>8</wp:comment_id><wp:comment_author>Author</wp:comment_author>
    <wp:comment_date_gmt>2019-03-06 00:00:00</wp:comment_date_gmt>
    <wp:comment_content><![CDATA[Thanks!]]></wp:comment_content>
    <wp:comment_approved>1</wp:comment_approved><wp:comment_type>comment</wp:comment_type><wp:comment_parent>7</wp:comment_parent></wp:comment>
  <wp:comment><wp:comment_id>9</wp:comment_id><wp:comment_author>Spammer</wp:comment_author>
    <wp:comment_content><![CDATA[buy now]]></wp:comment_content>
    <wp:comment_approved>spam</wp:comment_approved><wp:comment_parent>0</wp:comment_parent></wp:comment>
</item>
<item><title>About me</title><wp:post_name>about-me-wp</wp:post_name><wp:post_type>page</wp:post_type>
  <wp:status>publish</wp:status><content:encoded><![CDATA[<p>Hi.</p>]]></content:encoded></item>
<item><title>Unfinished</title><wp:post_name>unfinished-wp</wp:post_name><wp:post_type>post</wp:post_type>
  <wp:status>draft</wp:status><content:encoded><![CDATA[<p>Soon.</p>]]></content:encoded></item>
<item><title>photo.jpg</title><wp:post_type>attachment</wp:post_type><wp:status>inherit</wp:status></item>
</channel></rss>"""

GHOST = json.dumps({"db": [{"data": {
    "posts": [
        {"id": "1", "title": "Hello from Ghost", "slug": "hello-from-ghost", "status": "published", "type": "post",
         "html": "<h2>Intro</h2><p>Ghost <em>post</em>.</p><figure><img src='__GHOST_URL__/content/images/x.png'><figcaption>Cap</figcaption></figure>",
         "published_at": "2021-06-07T08:09:10.000Z", "custom_excerpt": "Ghostly.", "feature_image": None},
        {"id": "2", "title": "Ghost page", "slug": "ghost-page", "status": "published", "type": "page", "html": "<p>Page</p>"},
    ],
    "tags": [{"id": "t1", "name": "Spooky"}, {"id": "t2", "name": "#internal"}],
    "posts_tags": [{"post_id": "1", "tag_id": "t1"}, {"post_id": "1", "tag_id": "t2"}],
}}]}).encode()


def _medium_zip():
    page = """<html><head><title>Hello from Medium</title></head><body><article>
      <h1 class="p-name">Hello from Medium</h1>
      <section data-field="subtitle">A subtitle</section>
      <section data-field="body" class="e-content"><h3 class="graf--title">Hello from Medium</h3>
      <p>Medium <a href="https://example.com">link</a>.</p><pre>code()</pre></section>
      <footer><time class="dt-published" datetime="2018-01-02T03:04:05.000Z">Jan 2</time></footer>
    </article></body></html>"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("posts/2018-01-02_Hello-from-Medium-0123456789ab.html", page)
        zf.writestr("posts/draft_Medium-draft-abcdefabcdef.html", page.replace("Hello from Medium", "Medium draft"))
        zf.writestr("profile/profile.html", "<html></html>")
    return buf.getvalue()


def _wait():
    for _ in range(100):
        if not importers.status()["running"]:
            return importers.status()
        time.sleep(0.05)
    raise AssertionError("import didn't finish")


def test_detects_each_format():
    assert importers.read("x.xml", WXR)[0] == "WordPress"
    assert importers.read("x.json", GHOST)[0] == "Ghost"
    assert importers.read("x.zip", _medium_zip())[0] == "Medium"
    try:
        importers.read("x.txt", b"hello")
    except importers.ImportError_:
        pass
    else:
        raise AssertionError("expected a refusal")


def test_wordpress_import(admin, monkeypatch):
    png = io.BytesIO()
    Image.new("RGB", (20, 20), (1, 2, 3)).save(png, "PNG")
    monkeypatch.setattr(importers.netguard, "fetch", lambda url: png.getvalue())
    r = admin.post("/admin/import", files={"export": ("wp.xml", WXR, "text/xml")},
                   data={"copy_images": "1"})
    assert "Starting" in r.text or "Importing" in r.text or "Imported" in r.text
    st = _wait()
    assert "Imported 2 posts, 1 page, 2 comments, 1 image from WordPress" in st["message"], st

    post = posts.get_post("hello-from-wordpress")
    assert post["published"] and post["created_at"].startswith("2019-03-04T05:06:07")
    assert post["tags"] == "Travel" and post["summary"] == "A short trip."
    body = posts.load_post_body("hello-from-wordpress")
    assert "First paragraph with **bold**." in body
    assert "https://www.youtube.com/watch?v=dQw4w9WgXcQ" in body
    assert "](/uploads/" in body and "[caption" not in body and "Last line." in body
    assert not posts.get_post("unfinished-wp")["published"]
    about = posts.get_post("about-me-wp")
    assert about["pinned"] and about["pin_location"] == "footer"
    thread = comments.list_approved_with_deleted_parents("hello-from-wordpress")
    reply = next(c for c in thread if c["body"] == "Thanks!")
    assert next(c for c in thread if c["id"] == reply["parent_id"])["body"] == "Great post"

    # the same file again changes nothing
    admin.post("/admin/import", files={"export": ("wp.xml", WXR, "text/xml")})
    assert "3 already here, skipped" in _wait()["message"]


def test_ghost_and_medium_imports(admin):
    admin.post("/admin/import", files={"export": ("g.json", GHOST, "application/json")},
               data={"as_drafts": "1", "old_url": "https://ghost.example.com/"})
    assert "from Ghost" in _wait()["message"]
    ghost = posts.get_post("hello-from-ghost")
    assert ghost["tags"] == "Spooky" and not ghost["published"]  # as drafts
    body = posts.load_post_body("hello-from-ghost")
    assert "## Intro" in body and "*post*" in body and "*Cap*" in body
    assert "](https://ghost.example.com/content/images/x.png)" in body

    admin.post("/admin/import", files={"export": ("m.zip", _medium_zip(), "application/zip")})
    assert "Imported 2 posts from Medium" in _wait()["message"]
    medium = posts.get_post("hello-from-medium")
    assert medium["published"] and medium["summary"] == "A subtitle"
    body = posts.load_post_body("hello-from-medium")
    assert "[link](https://example.com)" in body and "code()" in body
    assert body.count("Hello from Medium") == 0  # the repeated title is dropped
    assert not posts.get_post("medium-draft")["published"]


def test_bad_file_is_refused(admin):
    r = admin.post("/admin/import", files={"export": ("x.txt", b"not an export", "text/plain")})
    assert "alert-error" in r.text


def test_private_addresses_are_refused():
    from soloblog import netguard
    for url in ("http://127.0.0.1/x", "http://169.254.169.254/latest", "http://localhost:6379/", "file:///etc/passwd"):
        try:
            netguard.check_url(url)
        except netguard.Blocked:
            continue
        raise AssertionError(url)


def _zip(files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buf.getvalue()


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), "blue").save(buf, "PNG")
    return buf.getvalue()


def test_substack_import_with_subscribers():
    from soloblog import newsletter
    from soloblog.db import get_db
    data = _zip({
        "posts.csv": "post_id,post_date,is_published,title,subtitle\n"
                     "101.my-first-letter,2024-03-01T09:00:00.000Z,true,My First Letter,Hello readers\n"
                     "102.draft-idea,2024-04-01T09:00:00.000Z,false,Draft Idea,\n",
        "posts/101.my-first-letter.html": "<p>Welcome to the <strong>letter</strong>.</p>",
        "posts/102.draft-idea.html": "<p>Not yet.</p>",
        "email_list.mysub.csv": "email,active_subscription,created_at\nreader1@example.com,false,2024-01-01\n"
                                "reader2@example.com,false,2024-01-02\n",
    })
    source, items = importers.read("export.zip", data)
    assert source == "Substack" and [i["title"] for i in items if i.get("kind") != "subscribers"] == \
        ["My First Letter", "Draft Idea"]
    try:
        counts = importers.save_all(items)
        assert counts["posts"] == 2 and counts["subscribers"] == 2
        row = posts.get_post("my-first-letter")
        assert row and row["summary"] == "Hello readers" and row["published"]
        assert "**letter**" in posts.load_post_body("my-first-letter")
        assert not posts.get_post("draft-idea")["published"]
        assert newsletter.count() >= 2
    finally:
        get_db().execute("DELETE FROM subscribers")
        get_db().commit()


def test_markdown_folder_import():
    png = _png()
    data = _zip({
        "_posts/2023-05-06-hello-jekyll.md": "---\ntitle: Hello Jekyll\ntags: [notes, jekyll]\n"
                                              "description: A first post\n---\n\nSome text.\n\n![A shot](/assets/shot.png)\n",
        "content/posts/bundle-post/index.md": "---\ntitle: A Hugo Bundle\ndate: 2022-01-02T10:00:00Z\n"
                                              "categories: [travel]\ncover: cover.png\n---\n\nWith a cover.\n",
        "content/posts/bundle-post/cover.png": png,
        "assets/shot.png": png,
        "vault/Obsidian Note.md": "# Obsidian Note\n\nAn embed: ![[pic.png]] and a [[Wiki Link]].\n",
        "vault/attachments/pic.png": png,
        "_drafts/unfinished.md": "---\ntitle: Unfinished\n---\n\nLater.\n",
        "README.md": "# not a post\n",
    })
    source, items = importers.read("site.zip", data)
    assert source == "Markdown"
    assert sorted(i["title"] for i in items) == ["A Hugo Bundle", "Hello Jekyll", "Obsidian Note", "Unfinished"]
    counts = importers.save_all(items)
    assert counts["posts"] == 4 and counts["images"] >= 3
    jekyll = posts.get_post("hello-jekyll")
    assert jekyll["created_at"].startswith("2023-05-06") and "jekyll" in jekyll["tags"]
    assert jekyll["summary"] == "A first post"
    assert "](/uploads/" in posts.load_post_body("hello-jekyll")
    bundle = posts.get_post("bundle-post")
    assert bundle["cover_image"].startswith("/uploads/") and "travel" in bundle["tags"]
    note = posts.load_post_body("obsidian-note")
    assert "](/uploads/" in note and "[[Wiki Link]]" in note and not note.lstrip().startswith("# Obsidian")
    assert not posts.get_post("unfinished")["published"]
    assert not posts.get_post("readme")
