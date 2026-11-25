from pathlib import Path
import re
from soloblog import images
from soloblog.render import render_markdown, render_post, render_comment


def test_scripts_are_stripped():
    assert "<script" not in render_markdown("hi <script>alert(1)</script>")
    assert "<script" not in render_comment("<script>alert(1)</script>")
    # nothing typed becomes a tag: a picture from elsewhere would tell its
    # sender who read the page; a heading or a link would shout or lure
    out = render_comment('Hi <img src="https://elsewhere.example/p.gif"> <h1>Big</h1>\n'
                         '<a href="https://elsewhere.example">here</a> & "done"')
    assert not re.search(r"<(?!/?p>|br>)", out), out
    assert "&lt;img" in out and "<br>" in out and "&amp;" in out


def test_toc_needs_three_headings():
    _, toc = render_post("## One\n\n## Two\n")
    assert toc is None
    _, toc = render_post("## One\n\n## Two\n\n## Three\n")
    assert 'href="#three"' in toc


def test_credit_line():
    meta = {"caption": "A <b>quiet</b> morning", "credit_name": "Ana", "credit_url": "https://example.com/ana",
            "credit_source": "pexels"}
    line = images.figcaption_html(meta)
    assert line.startswith("A &lt;b&gt;quiet&lt;/b&gt; morning · Photo by <a href=\"https://example.com/ana\"")
    assert line.endswith(" on Pexels")


def test_credit_url_must_be_http():
    images.set_meta("x.webp", "", "", credit_name="Ana", credit_url="javascript:alert(1)")
    assert images.get_meta("x.webp")["credit_url"] == ""


def test_body_image_gets_caption_and_credit():
    images.set_meta("photo.webp", "A lake", "Morning", credit_name="Ben", credit_source="pixabay")
    html, _ = render_post("Intro\n\n![](/uploads/photo.webp)\n")
    assert "<figure>" in html
    assert 'alt="A lake"' in html
    assert "Morning · Photo by Ben on Pixabay" in html


def test_set_meta_keeps_credit_when_not_given():
    images.set_meta("keep.webp", "alt", "", credit_name="Cam")
    images.set_meta("keep.webp", "new alt", "caption")
    assert images.get_meta("keep.webp")["credit_name"] == "Cam"


def test_markdown_extras():
    html, _ = render_post("Note[^1] and ~~old~~.\n\n- [ ] todo\n- [x] done\n\n!!! tip\n    Nice.\n\n[^1]: Foot.\n")
    assert 'class="footnote-ref"' in html and 'id="fn:1"' in html
    assert "<del>old</del>" in html
    assert '<input type="checkbox" disabled aria-label="Not done">' in html and 'disabled checked aria-label="Done"' in html
    assert '<div class="admonition tip">' in html


def test_mermaid_block_is_kept_as_source():
    html, _ = render_post("```mermaid\ngraph LR; A-->B\n```\n")
    assert '<pre class="mermaid">graph LR; A--&gt;B' in html


def test_math_only_when_enabled():
    from soloblog import settings
    body = "Price $5 and $10, and $x^2$.\n\n$$\na_1\n$$\n\n`$code$`\n"
    html, _ = render_post(body)
    assert "math-inline" not in html
    settings.set_many({"markdown_math": "1"})
    try:
        html, _ = render_post(body)
        assert "Price $5 and $10" in html
        assert '<span class="math-inline">\\(x^2\\)</span>' in html
        assert '<div class="math-display">\\[\na_1\n\\]</div>' in html
        assert "<code>$code$</code>" in html
    finally:
        settings.set_many({"markdown_math": "0"})


def test_math_cannot_inject_html():
    from soloblog import settings
    settings.set_many({"markdown_math": "1"})
    try:
        html, _ = render_post("$<script>alert(1)</script>$\n")
        assert "<script>" not in html
    finally:
        settings.set_many({"markdown_math": "0"})


def test_embeds_load_only_on_click():
    html, _ = render_post("https://www.youtube.com/watch?v=dQw4w9WgXcQ\n\n<https://vimeo.com/123456>\n")
    assert 'data-embed-src="https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ?autoplay=1"' in html
    assert "player.vimeo.com/video/123456" in html
    assert "<iframe" not in html  # nothing loads until clicked


def test_media_files_get_players():
    html, _ = render_post("https://example.com/a.mp3\n\n/uploads/clip.webm\n")
    assert '<audio controls preload="metadata" class="w-full my-4" src="https://example.com/a.mp3">' in html
    assert '<video controls' in html and 'src="/uploads/clip.webm"' in html


def test_urls_in_sentences_are_left_alone():
    html, _ = render_post("Watch https://youtu.be/dQw4w9WgXcQ later.\n\nhttps://example.com/page\n")
    assert "embed" not in html and "<audio" not in html
    html, _ = render_post('https://evil.example/@a/1"onload="x\n')
    # not a valid Mastodon URL, so it stays plain (escaped) text
    assert "embed" not in html and "<p>https://evil.example" in html


def test_gallery_blocks_render_each_style():
    from soloblog import gallery
    for style in gallery.STYLES:
        html, _ = render_post(f"```gallery {style}\n/uploads/a.webp | Cap\nhttps://example.com/b.jpg\n```\n")
        assert f'class="gallery gallery-{style} not-prose my-6"' in html
        assert html.count('data-lightbox="gallery-0"') == 2
        assert 'href="/uploads/a.webp"' in html


def test_gallery_uses_site_default_and_drops_non_images():
    from soloblog import settings
    settings.set_many({"gallery_style": "masonry"})
    try:
        html, _ = render_post("```gallery\n/uploads/a.webp\njavascript:alert(1)\n/etc/passwd\n```\n")
        assert "gallery-masonry" in html
        assert "javascript" not in html and "passwd" not in html
    finally:
        settings.set_many({"gallery_style": "grid"})


def test_gallery_captions_are_escaped_and_credited():
    images.set_meta("g1.webp", "Alt one", "Library caption", credit_name="Dee", credit_source="pexels")
    html, _ = render_post("```gallery\n/uploads/g1.webp\n/uploads/g2.webp | <script>x</script>\n```\n")
    assert 'alt="Alt one"' in html
    assert "Library caption · Photo by Dee on Pexels" in html
    assert "<script>x" not in html


def test_lightbox_dialog_only_where_needed(admin, client):
    from conftest import save_post
    slug = save_post(admin, title="Gallery post", body="```gallery\n/uploads/a.webp\n```\n")
    assert 'id="lightbox"' in client.get(f"/post/{slug}").text
    plain = save_post(admin, title="No images here", body="Just words.")
    assert 'id="lightbox"' not in client.get(f"/post/{plain}").text


def test_social_and_map_embeds_load_only_on_click():
    cases = {
        "https://x.com/jack/status/20": "platform.twitter.com/embed/Tweet.html?id=20",
        "https://www.facebook.com/nasa/posts/pfbid02abc": "facebook.com/plugins/post.php?href=https%3A%2F%2Fwww.facebook.com",
        "https://www.facebook.com/nasa/videos/123456/": "facebook.com/plugins/video.php",
        "https://www.instagram.com/p/C1abcDEF/": "instagram.com/p/C1abcDEF/embed",
        "https://www.tiktok.com/@user/video/7123456789": "tiktok.com/embed/v2/7123456789",
        "https://www.openstreetmap.org/#map=15/51.50740/-0.12780": "openstreetmap.org/export/embed.html?bbox=",
        "https://www.google.com/maps/place/Eiffel+Tower/@48.8584,2.2945,17z": "maps.google.com/maps?q=48.8584%2C2.2945",
    }
    for url, src in cases.items():
        html, _ = render_post(f"Look:\n\n{url}\n")
        assert "data-embed-src=" in html and src in html, url
        assert "<iframe" not in html
    # the same link inside a sentence stays a plain link
    html, _ = render_post("See https://x.com/jack/status/20 for more.\n")
    assert "data-embed-src" not in html


def test_unsplash_picks_are_hotlinked_and_credited(admin, monkeypatch):
    from soloblog import stock
    pinged = []
    monkeypatch.setattr(stock, "track_download", lambda loc: pinged.append(loc))
    url = "https://images.unsplash.com/photo-1?ixid=abc&w=1080"
    r = admin.post("/admin/media/import", data={
        "url": url, "alt": "A lake", "credit": "Jo Doe", "credit_url": "https://unsplash.com/@jo?utm_source=soloblog",
        "source": "unsplash", "download": "https://api.unsplash.com/photos/1/download"})
    assert r.json() == {"url": url}
    assert pinged == ["https://api.unsplash.com/photos/1/download"]
    html, _ = render_post(f"Intro\n\n![]({url})\n")
    assert 'alt="A lake"' in html
    assert "Photo by" in html and ">Jo Doe</a>" in html and ">Unsplash</a>" in html
    # only Unsplash's own image host is accepted this way
    r = admin.post("/admin/media/import", data={"url": "https://evil.example/x.jpg", "source": "unsplash"})
    assert r.status_code == 400


def test_audio_and_video_uploads(admin):
    from soloblog import images
    mp3 = b"ID3\x03\x00\x00\x00" + b"\x00" * 200
    r = admin.post("/admin/media/upload", files=[("image", ("song.mp3", mp3, "audio/mpeg")),
                                                 ("image", ("fake.mp4", b"not a video at all", "video/mp4"))])
    assert "Uploaded" in r.headers["location"]
    audio = [u for u in images.list_uploads() if u["kind"] == "audio"]
    assert len(audio) == 1 and audio[0]["filename"].endswith(".mp3")
    assert not any(u["filename"].endswith(".mp4") for u in images.list_uploads())
    page = admin.get("/admin/media?tab=unused").text
    # the card shows an icon that opens the details; the player is there
    assert "<audio" not in page and f'hx-get="/admin/media/details/{audio[0]["filename"]}"' in page
    details = admin.get(f"/admin/media/details/{audio[0]['filename']}").text
    assert "<audio" in details and audio[0]["url"] in details and "Audio details" in details
    # an image's alt text, caption and credit would show nowhere for audio
    assert "Alt text" not in details and "Caption" not in details and "MP3" in details
    html, _ = render_post(f"Listen:\n\n{audio[0]['url']}\n")
    assert f'<audio controls preload="metadata" class="w-full my-4" src="{audio[0]["url"]}">' in html
    images.delete_upload(audio[0]["filename"])


def test_editor_preview_matches_the_post(admin, client):
    body = "!!! tip\n    Callout\n\nhttps://www.youtube.com/watch?v=dQw4w9WgXcQ\n\n```gallery grid\n/uploads/a.webp\n```\n"
    html = admin.post("/admin/preview", data={"body": body}).text
    assert 'class="admonition tip"' in html
    assert "data-embed-src" in html and "gallery-grid" in html
    from conftest import editor_script
    assert "previewRender" in editor_script(admin, admin.get("/admin/new").text)
    assert client.post("/admin/preview", data={"body": "x"}).status_code in (303, 401, 403)


def test_emoji_shortcodes(admin):
    from soloblog.render import render_post
    html = render_post("Coffee :coffee: at 10:30:00, `:smile:` in code, :notanemoji:")[0]
    assert "☕" in html and "10:30:00" in html and "<code>:smile:</code>" in html and ":notanemoji:" in html
    # the editor's suggestions: the same list, as [shortcode, emoji]
    listed = admin.get("/admin/emoji.json").json()
    assert ["coffee", "☕"] in listed and ["man", "\U0001f468"] in listed


def test_markdown_extras_survive_the_sanitiser():
    from soloblog.render import render_post
    html = render_post('==marked== x^2^ H~2~O ~~gone~~ ++ctrl+c++ (c)\n\n'
                       '=== "One"\n\n    First.\n\n=== "Two"\n\n    Second.\n')[0]
    assert "<mark>marked</mark>" in html and "x<sup>2</sup>" in html and "H<sub>2</sub>O" in html
    assert "<del>gone</del>" in html and '<kbd class="key-control">Ctrl</kbd>' in html and "©" in html
    # tabs: radio buttons and labels, so they switch without scripts
    assert 'type="radio"' in html and '<label for="__tabbed_1_2">Two</label>' in html
    assert html.count('class="tabbed-block"') == 2


def test_strikethrough_marks_in_code_stay_as_typed():
    # code shows what to type - `~~words~~` in a sentence or a block
    # crossed the words out instead
    html = render_post("Type `~~words~~` to ~~cross out~~.\n\n```\n~~kept~~\n```\n")[0]
    assert "<code>~~words~~</code>" in html and "<del>cross out</del>" in html
    assert "~~kept~~" in html and "<del>kept</del>" not in html


def test_uploads_are_served_as_what_they_are(client):
    from test_bulk import _upload
    _upload("typed-right.webp")
    r = client.get("/uploads/typed-right.webp")
    assert r.status_code == 200 and r.headers["content-type"] == "image/webp"


def test_pdfs_in_the_media_library_and_posts(admin, client):
    import pytest
    from conftest import save_post
    """A PDF uploads as it is (checked by its first bytes, not its name),
    and on a line of its own in a post becomes the browser's own viewer -
    with the file itself for a phone without one."""
    import os
    from soloblog import config, images
    pdf = b"%PDF-1.4\n1 0 obj << >> endobj\ntrailer << >>\n%%EOF\n"
    r = admin.post("/admin/media/upload", files={"image": ("Menu card.pdf", pdf, "application/pdf")})
    assert r.status_code in (200, 303)
    name = next(f for f in os.listdir(config.UPLOADS_DIR) if f.startswith("menu-card-") and f.endswith(".pdf"))
    assert images.kind_of(name) == "document"
    with pytest.raises(ValueError):
        images.save_media(b"<html>not a pdf</html>", "evil.pdf")
    assert "PDF" in admin.get("/admin/media?kind=document").text
    slug = save_post(admin, title="Our menu", body=f"Have a look:\n\n/uploads/{name}\n")
    page = client.get(f"/post/{slug}")
    assert f'<iframe src="/uploads/{name}"' in page.text and "Open the PDF" in page.text
    assert "frame-src 'self' https:" in page.headers["content-security-policy"]
    os.remove(os.path.join(config.UPLOADS_DIR, name))


def test_a_page_with_a_background_sound(admin, client):
    """Chosen from the media library's audio; a visitor's button plays and
    stops it, and nothing plays by itself. Another site's file isn't taken."""
    import os
    from conftest import save_post
    from soloblog import config, posts
    os.makedirs(config.UPLOADS_DIR, exist_ok=True)
    with open(os.path.join(config.UPLOADS_DIR, "band-loop.mp3"), "wb") as f:
        f.write(b"ID3\x03\x00\x00\x00\x00\x00\x00")
    try:
        # picked like an image: the picker, showing just the audio
        editor = admin.get("/admin/new").text
        assert 'data-picker-kind="audio"' in editor and 'id="media-picker-kind"' in editor
        picker = admin.get("/admin/media/picker?kind=audio").text
        assert "band-loop.mp3" in picker and "<img" not in picker
        assert "band-loop.mp3" not in admin.get("/admin/media/picker").text
        slug = save_post(admin, title="Our band", body="Turn it up.", sound="/uploads/band-loop.mp3")
        assert posts.get_post(slug)["sound"] == "/uploads/band-loop.mp3"
        page = client.get(f"/post/{slug}").text
        assert 'id="background-sound"' in page and 'data-onclick="toggleSound"' in page
        assert "autoplay" not in page and "Play the background sound" in page
        save_post(admin, slug=slug, title="Our band", body="Turn it up.", sound="https://evil.example/a.mp3")
        assert posts.get_post(slug)["sound"] == "" and "background-sound" not in client.get(f"/post/{slug}").text
    finally:
        os.remove(os.path.join(config.UPLOADS_DIR, "band-loop.mp3"))


def test_the_sound_picker_uploads_audio_only(admin):
    """Upload in the picker for a sound field takes an audio file, as it
    is - an image, or a file that only says it's audio, is turned away."""
    import os
    from soloblog import config
    r = admin.post("/admin/upload-image", data={"kind": "audio"},
                   files={"image": ("street.mp3", b"ID3\x03\x00\x00\x00\x00\x00\x00", "audio/mpeg")})
    assert r.status_code == 200 and r.json()["url"].endswith(".mp3")
    os.remove(os.path.join(config.UPLOADS_DIR, r.json()["url"].rsplit("/", 1)[1]))
    r = admin.post("/admin/upload-image", data={"kind": "audio"},
                   files={"image": ("fake.mp3", b"<html><script>", "audio/mpeg")})
    assert r.status_code == 400
    r = admin.post("/admin/upload-image", data={"kind": "audio"},
                   files={"image": ("photo.png", b"\x89PNG\r\n\x1a\n", "image/png")})
    assert r.status_code == 400 and "audio" in r.json()["error"]


def test_pdf_details_and_filter(admin):
    from soloblog import images
    pdf = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
    admin.post("/admin/media/upload", files=[("image", ("price-list.pdf", pdf, "application/pdf"))])
    item = next(u for u in images.list_uploads() if u["kind"] == "document")
    # the PDFs filter finds it, and the Images one doesn't
    assert item["filename"] in admin.get("/admin/media?kind=document").text
    assert item["filename"] not in admin.get("/admin/media?kind=image").text
    details = admin.get(f"/admin/media/details/{item['filename']}").text
    assert "PDF details" in details and "Open the PDF" in details and "Image details" not in details
    assert "Alt text" not in details and "Rotate" not in details
    images.delete_upload(item["filename"])


def test_a_broken_image_is_logged_not_raised(caplog):
    import logging
    import os
    from soloblog import config, images
    name = "broken-on-purpose.webp"
    os.makedirs(config.UPLOADS_DIR, exist_ok=True)
    path = os.path.join(config.UPLOADS_DIR, name)
    with open(path, "wb") as f:
        f.write(b"RIFF\x00\x00\x00\x00WEBPnot really a picture")
    try:
        assert images._dimensions_of(path, os.stat(path).st_mtime_ns) is None
        with caplog.at_level(logging.WARNING, logger="soloblog.images"):
            # too wide a request for nothing: served as it is, and said why
            assert images.sized(name, images.SIZES[0]) == path
        assert any(name in r.getMessage() for r in caplog.records)
    finally:
        os.remove(path)


def test_smaller_copies_are_made_two_at_a_time(monkeypatch):
    """images.sized: a page asking for dozens of new copies at once ran a
    small server out of memory - at most two are made at the same time."""
    import os
    import threading
    import time
    from PIL import Image
    from soloblog import config, images
    os.makedirs(config.UPLOADS_DIR, exist_ok=True)
    names = []
    for i in range(8):
        name = f"many-at-once-{i}.jpg"
        Image.new("RGB", (1600, 1200), (i * 20, 80, 120)).save(os.path.join(config.UPLOADS_DIR, name), "JPEG")
        names.append(name)
    busy, most, lock = [0], [0], threading.Lock()
    make = images._make_sized

    def counted(*args):
        with lock:
            busy[0] += 1
            most[0] = max(most[0], busy[0])
        time.sleep(0.02)
        try:
            return make(*args)
        finally:
            with lock:
                busy[0] -= 1
    monkeypatch.setattr(images, "_make_sized", counted)
    try:
        threads = [threading.Thread(target=images.sized, args=(n, w)) for n in names for w in images.SIZES]
        [t.start() for t in threads]
        [t.join() for t in threads]
        assert most[0] == 2
        for n in names:
            with Image.open(images.sized(n, 400)) as small:
                assert small.size == (400, 300)
    finally:
        for n in names:
            for path in [os.path.join(config.UPLOADS_DIR, n)] + [images._sizes_path(w, n) for w in images.SIZES]:
                if os.path.exists(path):
                    os.remove(path)


def test_image_details_save_and_discard_only_once_changed(admin):
    # Save always showed; now Discard and Save, as in Settings and the
    # post's own panel, only while something's changed (syncSettingsDirty)
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (900, 120), (200, 30, 30)).save(buf, "PNG")
    admin.post("/admin/media/upload", files=[("image", ("wide-logo.png", buf.getvalue(), "image/png"))])
    item = next(u for u in images.list_uploads() if u["filename"].startswith("wide-logo"))
    try:
        details = admin.get(f"/admin/media/details/{item['filename']}").text
        form = details[details.rindex("<form", 0, details.index("Description")):]
        assert "data-declare-fields" in details and "discardForm" in form
        assert "hidden in-data-dirty:flex" in form  # the buttons wait for a change
        # the whole picture, a wide logo too - not its middle letters
        assert "object-contain" in details
        saved = admin.post(f"/admin/media/details/{item['filename']}",
                           data={"alt_text": "Our logo", "declared_fields": "alt_text"}).text
        assert 'id="save-status"' in saved and "Saved" in saved
        assert images.get_meta(item["filename"])["alt_text"] == "Our logo"
        # two to a row on a phone
        assert "grid grid-cols-2 sm:grid-cols-3" in admin.get("/admin/media").text
    finally:
        images.delete_upload(item["filename"])


def test_every_picture_on_a_page_says_its_size(admin, client):
    """Width and height on each of our pictures, so a page keeps their room
    while they load; all but the first wait until they're near the screen."""
    import os
    from PIL import Image
    from conftest import save_post
    from soloblog import config
    for name, size in (("wide.jpg", (1600, 1200)), ("tall.jpg", (600, 900))):
        Image.new("RGB", size, (20, 80, 120)).save(os.path.join(config.uploads_dir(), name), "JPEG")
    slug = save_post(admin, title="Pictures", cover_image="/uploads/wide.jpg",
                     body="Words.\n\n![A](/uploads/tall.jpg)\n\n![B](/uploads/wide.jpg)\n\n"
                          "![Elsewhere](https://example.com/x.jpg)\n\n![Gone](/uploads/missing.jpg)")
    page = client.get(f"/post/{slug}").text
    tags = re.findall(r"<img\b[^>]*>", page[page.index("<main"):])
    ours = [t for t in tags if 'src="/uploads/wide.jpg' in t or 'src="/uploads/tall.jpg' in t]
    assert len(ours) >= 3
    for tag in ours:
        w, h = (int(re.search(rf' {k}="(\d+)"', tag).group(1)) for k in ("width", "height"))
        assert (w, h) in ((1600, 1200), (600, 900)), tag
    # someone else's picture, and one that isn't there, are left as written
    assert all(" width=" not in t for t in tags if "example.com" in t or "missing.jpg" in t)
    assert " loading=" not in tags[0] or "fetchpriority" in tags[0]
    assert all(' loading="lazy"' in t or " fetchpriority=" in t for t in tags[1:]), tags
    # the home page's cards too, and the number sent matches the page
    home = client.get("/", headers={"accept-encoding": "identity"})
    assert int(home.headers["content-length"]) == len(home.content)
    assert all(" width=" in t for t in re.findall(r'<img\b[^>]*src="/uploads/wide[^>]*>', home.text))


def test_picture_sizes_follow_the_copy_asked_for():
    import os
    from PIL import Image
    from soloblog import config
    Image.new("RGB", (1600, 1200), (9, 9, 9)).save(os.path.join(config.uploads_dir(), "big.jpg"), "JPEG")
    out = images.with_sizes('<img src="/uploads/big.jpg?w=400" alt=""><img width="5" src="/uploads/big.jpg">'
                            '<img src="/uploads/_trash/big.jpg"><img src="/uploads/..%2Fbig.jpg">')
    assert '<img width="400" height="300" src="/uploads/big.jpg?w=400"' in out
    assert out.count("height=") == 1 and "lazy" not in out


def test_the_image_picker_works_from_the_keyboard_and_keeps_a_gallerys_choices(admin):
    """A picture in the picker was an image a keyboard couldn't reach. And
    for a gallery, a search drew the grid again with nothing marked, while
    a stock photo pressed twice was added to the library twice."""
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (40, 30), "teal").save(buf, "PNG")
    admin.post("/admin/upload-image", files={"image": ("keys.png", buf.getvalue(), "image/png")})
    grid = admin.get("/admin/media/picker").text
    assert 'role="button"' in grid and 'tabindex="0"' in grid
    from fasthtml.common import to_xml
    from soloblog.ui import StockResults
    stock = to_xml(StockResults("pexels", [{"thumb": "https://t/x.jpg", "full": "https://f/x.jpg", "alt": ""}]))
    assert 'role="button"' in stock and 'alt="Pexels photo"' in stock
    js = Path("soloblog/js/media_picker.js").read_text(encoding="utf-8")
    assert "e.key !== 'Enter' && e.key !== ' '" in js
    assert "htmx:afterSettle" in js and "img.dataset.added" in js


def test_no_text_under_12px_for_visitors():
    # picture credits and every other line a visitor reads stay at 12px or
    # more; the admin's theme swatch labels are the only small text
    import pathlib
    small = re.compile(r"text-\[(\d*\.?\d+)(px|rem)\]")
    found = []
    for path in pathlib.Path(images.__file__).parent.rglob("*.py"):
        if "admin_settings" in path.parts:
            continue
        for m in small.finditer(path.read_text()):
            px = float(m.group(1)) * (16 if m.group(2) == "rem" else 1)
            if px < 12:
                found.append(f"{path.name}: {m.group(0)}")
    assert not found, found
    assert "text-xs" in images.CAPTION_OVER_CLS


def test_diagrams_keep_their_source_and_redraw_when_the_palette_changes():
    # Mermaid swaps a diagram's text for SVG; a palette change draws it
    # again from the kept text (on a post and in the editor's preview)
    from soloblog import js
    actions = js.read("actions.js")
    assert "dataset.src" in actions and "data-processed" in actions
    assert "attributeFilter: ['data-theme']" in actions
    assert "data-print-from" in actions.split("function drawMermaid")[1].split("function")[0]
    assert "drawMermaid(preview.querySelectorAll('pre.mermaid'))" in js.read("editor_init.js")


def _html(body):
    from soloblog import render
    return render.render_post(body)[0]


def test_a_list_straight_after_a_paragraph_line_is_a_list():
    assert "<ul>" in _html("A paragraph\n- one\n- two")
    assert "<p>A paragraph</p>" in _html("A paragraph\n- one\n- two")
    assert "<ol>" in _html("Steps:\n1. one\n2. two")
    assert "<ul>" in _html("Items:\n* a\n* b") and "<ul>" in _html("Items:\n+ a\n+ b")
    # in a quote
    quoted = _html("> A line\n> - b\n> - c")
    assert "<blockquote>" in quoted and "<ul>" in quoted


def test_a_list_is_only_added_where_one_was_meant():
    plain = ["2026 - the year\nnext line", "Price - 10\nmore", "words\n2019. It was great", "a\n---\nb",
             "```\ntext\n- not a list\n```", "~~~\ntext\n- not a list\n~~~", "    code\n    - x",
             "| a | b |\n|---|---|\n| 1 | 2 |\n- x", "# Heading\n- one", "- one\ncontinued\n- two",
             "- one\n\n  more of one\n- two", "A\n\n- one\n- two", "***bold italic*** x\ntext"]
    from soloblog import render
    for body in plain:
        assert render._list_after_paragraph(body) == body, body
    assert "<ul>" not in _html("```\ntext\n- not a list\n```")
    assert _html("2026 - the year\nnext") == "<p>2026 - the year\nnext</p>"
    # one list stays one list, its items tight
    assert _html("- one\ncontinued\n- two").count("<ul>") == 1
    assert "<p>" not in _html("- one\n- two")


def _pictures_page(body, **fields):
    from soloblog import posts
    return posts.write(title="Pictures", body=body, published=True, **fields)


def test_a_missing_picture_is_left_out_for_a_visitor_and_boxed_for_the_admin(client, admin, real_pictures):
    """A template's sample picture (/uploads/me.webp) that nobody has replaced
    showed as a broken image on the published page."""
    import os
    from PIL import Image
    from soloblog import config
    os.makedirs(config.uploads_dir(), exist_ok=True)
    Image.new("RGB", (40, 30), "teal").save(os.path.join(config.uploads_dir(), "here.png"), "PNG")
    slug = _pictures_page(
        "Hello.\n\n![](/uploads/nowhere.webp)\n\n![](/uploads/here.png)\n\n![](https://example.com/far.jpg)\n\n"
        "```gallery grid\n/uploads/gone1.webp | A\n/uploads/here.png | B\n```\n")
    seen = client.get(f"/post/{slug}").text
    assert "nowhere.webp" not in seen and "gone1.webp" not in seen and "Image not found" not in seen
    assert 'src="/uploads/here.png' in seen and 'src="https://example.com/far.jpg"' in seen
    assert seen.count("gallery-item") == 1
    mine = admin.get(f"/post/{slug}").text
    assert "nowhere.webp" not in mine and mine.count("Image not found - replace it") == 2
    assert "border-dashed" in mine and 'src="/uploads/here.png' in mine


def test_a_missing_picture_takes_its_empty_frame_with_it(real_pictures):
    from soloblog import images
    cards = ('<figure><a href="/x" class="block"><img src="/uploads/nope.webp" alt=""></a></figure>'
             '<figure><img src="/uploads/nope.webp"><figcaption>Cap</figcaption></figure><p>Words</p>'
             '<img src="/uploads/_trash/x.webp"><img src="/uploads/..%2Fx.webp"><img src="/uploads/">')
    assert images.without_missing(cards) == "<p>Words</p>"
