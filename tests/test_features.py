from pathlib import Path
import os
import re

from soloblog import posts
from soloblog import settings
from conftest import save_post
from soloblog.db import get_db


def test_a_page_as_the_homepage(admin, client):
    slug = save_post(admin, title="Welcome home", body="Hello from the front page.", pin_location="header")
    save_post(admin, title="An ordinary post")
    assert client.get("/blog").status_code in (301, 307)  # no homepage page: the roll is at /
    admin.post("/admin/settings/name", headers={"hx-request": "true"},
               data={"home_page": slug, "declared_fields": "home_page"})
    try:
        home = client.get("/").text
        assert "Hello from the front page." in home and 'href="/blog"' in home
        assert 'class="breadcrumbs' not in home
        blog = client.get("/blog").text
        assert "An ordinary post" in blog and "Hello from the front page." not in blog
        # just the page, until Settings adds things back
        assert ">Welcome home</h1>" not in home and 'id="comments"' not in home
        # its one address is / - in lists and search, and its own page goes there
        assert posts.url_for(posts.get_post(slug)) == "/"
        own = client.get(f"/post/{slug}")
        assert own.status_code in (301, 302, 303, 307, 308) and own.headers["location"].endswith("/")
        admin.post("/admin/settings/name", headers={"hx-request": "true"},
                   data={"home_page": slug, "home_page_shows": ["title", "comments", "bogus"],
                         "declared_fields": "home_page,home_page_shows"})
        assert settings.get("home_page_shows") == "title,comments"
        home = client.get("/").text
        assert ">Welcome home</h1>" in home and 'id="comments"' in home
        # the picker offers pages, not every post
        picker = admin.get("/admin/settings?tab=name").text
        picker = picker[picker.index('name="home_page"'):][:5000]
        assert "Welcome home" in picker and "An ordinary post" not in picker
        admin.post("/admin/settings/name", headers={"hx-request": "true"},
                   data={"home_page": "no-such-post", "declared_fields": "home_page"})
        assert settings.get("home_page") == ""
    finally:
        settings.set_many({"home_page": "", "home_page_shows": ""})


def test_unlisted_posts(admin, client):
    slug = save_post(admin, title="Just for friends", body="A quiet note.", tags="quiet", unlisted="1")
    row = posts.get_post(slug)
    assert row["unlisted"] and posts.post_status(row) == "Unlisted"
    assert "unlisted: true" in Path(posts._path(slug)).read_text(encoding="utf-8")
    page = client.get(f"/post/{slug}")
    assert page.status_code == 200 and '<meta name="robots" content="noindex"' in page.text
    for path in ("/", "/rss", "/tags", "/sitemap.xml", "/search?q=quiet"):
        assert "Just for friends" not in client.get(path).text and f"/post/{slug}" not in client.get(path).text, path
    assert slug not in {p["slug"] for p in posts.list_all_published()}  # never announced


def test_duplicate_a_post(admin):
    slug = save_post(admin, title="Original recipe", body="Flour and water.", tags="bread")
    r = admin.post("/admin/posts/duplicate", data={"slug": slug})
    new = r.headers["location"].split("?")[0].rsplit("/", 1)[-1]
    copy = posts.get_post(new)
    assert copy["title"] == "Original recipe (copy)" and not copy["published"] and copy["tags"] == "bread"
    assert posts.load_post_body(new).strip() == "Flour and water."


def test_rename_merge_and_remove_tags(admin, client):
    a = save_post(admin, title="Tag one", tags="Garden, plants")
    b = save_post(admin, title="Tag two", tags="gardening")
    html = admin.get("/admin/posts?status=tags").text
    assert "/admin/tags/rename" in html and "gardening" in html
    admin.post("/admin/tags/rename", data={"old": "gardening", "new": "garden"})
    assert posts.get_post(b)["tags"] == "garden"
    assert dict(posts.tag_counts_all())["Garden"] == 2  # merged, whatever the case
    admin.post("/admin/tags/remove", data={"tag": "plants"})
    assert posts.get_post(a)["tags"] == "Garden"
    assert "plants" not in Path(posts._path(a)).read_text(encoding="utf-8")


def test_updated_date_shows_after_a_later_edit(admin, client):
    slug = save_post(admin, title="Old news", body="First version.")
    assert "Updated" not in client.get(f"/post/{slug}").text
    get_db().execute("UPDATE posts SET created_at='2020-01-01T10:00:00' WHERE slug=?", (slug,))
    get_db().commit()
    settings.set_many({"show_updated": "1"})
    assert "Updated" in client.get(f"/post/{slug}").text
    settings.set_many({"show_updated": "0"})
    assert "Updated" not in client.get(f"/post/{slug}").text
    settings.set_many({"show_updated": "1"})


def test_images_without_alt_text(admin):
    from soloblog import images
    from PIL import Image
    from soloblog import config
    os.makedirs(config.UPLOADS_DIR, exist_ok=True)
    for name in ("alt-yes.webp", "alt-no.webp"):
        Image.new("RGB", (200, 100)).save(os.path.join(config.UPLOADS_DIR, name), "WEBP")
    images.set_meta("alt-yes.webp", "A described picture", "")
    body = "![](/uploads/alt-yes.webp)\n\n![](/uploads/alt-no.webp)\n\n![typed here](/uploads/alt-no.webp)\n"
    assert images.missing_alt(body) == 1
    slug = save_post(admin, title="Pictures")
    r = admin.post("/admin/save", headers={"hx-request": "true"},
                   data={"slug": slug, "title": "Pictures", "body": body, "published": "1"})
    assert "1 image without alt text" in r.text
    html = admin.get("/admin/media?tab=unused&kind=noalt").text + admin.get("/admin/media?kind=noalt").text
    assert "alt-no.webp" in html and "alt-yes.webp" not in html


def test_a_page_on_a_reserved_address_says_where_it_lives(admin, client):
    slug = save_post(admin, title="Archive", pin_location="header")
    assert slug == "archive" and posts.url_for(posts.get_post(slug)) == "/post/archive"
    assert "/archive is taken, so this page is at /post/archive" in admin.get(f"/admin/edit/{slug}").text
    about = save_post(admin, title="About me here", pin_location="header")
    assert "is taken, so this page" not in admin.get(f"/admin/edit/{about}").text


def test_contents_on_the_right(admin, client):
    body = "## One\n\nText.\n\n## Two\n\nText.\n\n## Three\n\nText.\n"
    slug = save_post(admin, title="Contents right", body=body, toc_style="right")
    html = client.get(f"/post/{slug}").text
    assert 'data-side-panel="right"' in html and "data-[beside]:left-full" in html
    save_post(admin, slug=slug, title="Contents right", body=body, toc_style="side")
    assert 'data-side-panel="left"' in client.get(f"/post/{slug}").text


def test_contents_shows_on_posts_or_pages(admin, client):
    # like the side panels: the site's choice only where it's ticked to
    # show - a post's own choice still counts, and clearing both is Off
    body = "## One\n\nText.\n\n## Two\n\nText.\n\n## Three\n\nText.\n"
    before = {k: settings.get(k) for k in ("toc_style", "toc_style_where")}
    try:
        settings.set_many({"toc_style": "right", "toc_style_where": "posts"})
        post = save_post(admin, title="Contents post", body=body)
        page = save_post(admin, title="Contents page", body=body, pinned="1", pin_location="footer")
        own = save_post(admin, title="Contents own page", body=body, pinned="1", pin_location="footer",
                        toc_style="right")
        assert 'data-side-panel="right"' in client.get(f"/post/{post}", follow_redirects=True).text
        assert 'data-side-panel="right"' not in client.get(f"/post/{page}", follow_redirects=True).text
        assert 'data-side-panel="right"' in client.get(f"/post/{own}", follow_redirects=True).text
        admin.post("/admin/settings/style", headers={"hx-request": "true"},
                   data={"declared_fields": "toc_style,toc_style_where", "toc_style": "right"})
        assert settings.get("toc_style") == "off" and settings.get("toc_style_where") == "posts,pages"
        assert 'data-shown-for="toc_style!=off" hidden' in admin.get("/admin/settings?tab=posts").text
    finally:
        settings.set_many(before)


def test_filmstrip_has_arrows():
    from soloblog import gallery
    html = gallery.render("filmstrip", [("/uploads/a.webp", ""), ("/uploads/b.webp", "")], "g1")
    assert html.count('data-onclick="slideGallery"') == 2 and 'data-onscroll="syncSlider"' in html


def test_list_header_says_what_is_shown(admin):
    save_post(admin, title="Header coffee one", tags="brew")
    html = admin.get("/admin/posts?q=coffee").text
    assert "data-live-search" in html and "matching “coffee”" in html and 'href="/admin/posts?status=all&amp;sort=newest"' in html
    assert "data-bulk-busy" in html and 'value="publish"' in html
    assert ">Clear<" not in admin.get("/admin/posts").text
    # each filter names itself in its own button
    assert re.search(r'>Tag<span class="sr-only">:</span></span> <span class="truncate">All<', html), 'Tag: All'


def test_matching_pairs_have_the_same_rounding():
    """Switching a pair to dark mode changes the colours, not the shape of
    buttons and cards (themes.THEME_PAIRS)."""
    import re
    import pytest
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    built = os.path.join(here, "static", "css", "output.css")
    if not os.path.exists(built):
        if os.environ.get("CI"):
            pytest.fail("static/css/output.css wasn't built")
        pytest.skip("needs the built CSS")
    from soloblog.themes import THEME_PAIRS, DARK_THEMES
    css = Path(built).read_text(encoding="utf-8")

    def rounding(theme):
        for m in re.finditer(r'\[data-theme="?' + theme + r'"?\][^{]*\{([^}]*)\}', css):
            found = dict(re.findall(r"--radius-(field|box):\s*([^;]+);", m.group(1)))
            if len(found) == 2:
                return found
        raise AssertionError(f"no rounding for {theme}")
    names = [name for name, _, _ in THEME_PAIRS]
    assert len(set(names)) == len(names)
    for name, light, dark in THEME_PAIRS:
        assert light not in DARK_THEMES and dark in DARK_THEMES, name
        # Mono's the closest there is: no dark grey palette is rounded like wireframe
        if name != "Mono":
            assert rounding(light) == rounding(dark), (name, light, dark)


def test_theme_text_is_readable_in_every_theme():
    """Every theme's coloured and quieter text reads at 4.5:1 on the page
    and on cards, and fills' text on its fill (tools/theme_contrast.py)."""
    import re
    import pytest
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    built = os.path.join(here, "static", "css", "output.css")
    if not os.path.exists(built):
        # CI builds it first (.github/workflows/docker.yml), so there a
        # missing stylesheet is a failure, not a skip
        if os.environ.get("CI"):
            pytest.fail("static/css/output.css wasn't built")
        pytest.skip("needs the built CSS")
    # the contrast maths lives in soloblog.themes (the tool and your own
    # palettes share it); the tool writes contrast.css from it
    from soloblog import themes as tc
    from soloblog.themes import DAISYUI_THEMES
    css = Path(built).read_text(encoding="utf-8")
    gen = Path(os.path.join(here, "static", "css", "contrast.css")).read_text(encoding="utf-8")
    for theme in DAISYUI_THEMES:
        colours = tc.theme_colours(css, theme)
        block = re.search(r'html\[data-theme="' + theme + r'"\]\s*\{([^}]*)\}', gen)
        values = dict(re.findall(r"--([a-z0-9-]+):\s*([^;]+);", block.group(1))) if block else {}
        lab = lambda v: tc.linear_srgb(tc.parse_oklch(v))  # noqa: E731
        for bg in ("base-100", "base-200"):
            for name in tc.TEXT_COLOURS:
                assert tc.contrast(lab(values.get(f"tx-{name}", colours[name])), lab(colours[bg])) >= 4.5, (theme, name, bg)
            for n in tc.MUTED:
                a = int(re.search(r"(\d+)%", values[f"tx-muted-{n}"]).group(1)) / 100 if f"tx-muted-{n}" in values else n / 100
                shade = tc.over(lab(colours["base-content"]), lab(colours[bg]), a)
                assert tc.contrast(shade, lab(colours[bg])) >= 4.5, (theme, n, bg)
        for fill in tc.FILLS:
            text = values.get(f"color-{fill}-content", colours[f"{fill}-content"])
            assert tc.contrast(lab(text), lab(colours[fill])) >= 4.5, (theme, fill)
        # the editor's selected text reads, and stands out from the page
        # unless the text needed it paler (valentine's low-contrast text)
        sel = lab(values["selection"])
        assert tc.contrast(lab(colours["base-content"]), sel) >= 4.5, theme
        assert tc.contrast(sel, lab(colours["base-100"])) >= 1.15, theme


def test_placeholders_and_disabled_controls_are_readable_in_every_theme():
    """daisyUI's placeholders (50% of the text colour) and disabled
    controls (20-40%) are moved to the muted steps in input.css; those
    steps reach 4.5:1 per theme (contrast.css), so placeholders must read
    at 4.5:1 and disabled buttons and fields at 3:1."""
    import re
    import pytest
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    built = os.path.join(here, "static", "css", "output.css")
    if not os.path.exists(built):
        if os.environ.get("CI"):
            pytest.fail("static/css/output.css wasn't built")
        pytest.skip("needs the built CSS")
    from soloblog import themes as tc
    from soloblog.themes import DAISYUI_THEMES
    src = Path(os.path.join(here, "static", "css", "input.css")).read_text(encoding="utf-8")
    # the rules that use the steps are really there
    assert re.search(r"::placeholder,[^{]*\{\s*color: var\(--tx-muted-60\); opacity: 1;", src)
    assert re.search(r"\.btn-disabled,[^{]*\{\s*color: var\(--tx-muted-40\);", src)
    assert re.search(r"::placeholder\s*\{\s*color: var\(--tx-muted-40\); opacity: 1;", src)
    css = Path(built).read_text(encoding="utf-8")
    gen = Path(os.path.join(here, "static", "css", "contrast.css")).read_text(encoding="utf-8")
    lab = lambda v: tc.linear_srgb(tc.parse_oklch(v))  # noqa: E731
    for theme in DAISYUI_THEMES:
        colours = tc.theme_colours(css, theme)
        block = re.search(r'html\[data-theme="' + theme + r'"\]\s*\{([^}]*)\}', gen)
        values = dict(re.findall(r"--([a-z0-9-]+):\s*([^;]+);", block.group(1))) if block else {}

        def step(n, values=values):
            m = re.search(r"(\d+)%", values.get(f"tx-muted-{n}", ""))
            return int(m.group(1)) / 100 if m else n / 100
        text = lab(colours["base-content"])
        for bg in ("base-100", "base-200"):
            page = lab(colours[bg])
            shade = tc.over(text, page, step(60))
            assert tc.contrast(shade, page) >= 4.5, (theme, "placeholder", bg)
            # a disabled button: daisyUI's 10% tint of the text colour behind it
            tint = tc.over(text, page, 0.10)
            assert tc.contrast(tc.over(text, tint, step(40)), tint) >= 3, (theme, "disabled button", bg)
        field = lab(colours["base-200"])
        assert tc.contrast(tc.over(text, field, step(40)), field) >= 3, (theme, "disabled field")


def test_readable_image_names_and_renaming(admin, client):
    import io
    from soloblog import images
    from soloblog import settings
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (60, 40), (200, 50, 50)).save(buf, "PNG")
    url = images.save_upload(buf.getvalue(), "Balcony Tomatoes (1).PNG")
    name = url.rsplit("/", 1)[-1]
    assert name.startswith("balcony-tomatoes-1-") and name.endswith(".webp") and len(name) == len("balcony-tomatoes-1-") + 4 + 5
    assert images.save_upload(buf.getvalue(), "").rsplit("/", 1)[-1].startswith("image-")
    images.set_meta(name, "Red tomatoes", "")
    slug = save_post(admin, title="Tomato post", body=f"![]({url})\n\nMore.", cover_image=url)
    before = posts.get_post(slug)["updated_at"]
    settings.set_many({"share_image_url": url})
    try:
        r = admin.post(f"/admin/media/rename/{name}", data={"name": "My Tomatoes"}, headers={"hx-request": "true"})
        assert "Renamed - 1 post updated" in r.text
        new_url = "/uploads/my-tomatoes.webp"
        body = Path(posts._path(slug)).read_text(encoding="utf-8")
        assert new_url in body and url not in body and posts.get_post(slug)["cover_image"] == new_url
        assert posts.get_post(slug)["updated_at"] == before  # not an edit of the post
        assert images.get_meta("my-tomatoes.webp")["alt_text"] == "Red tomatoes"
        assert settings.get("share_image_url") == new_url
        old = client.get(url, follow_redirects=False)
        assert old.status_code == 301 and old.headers["location"] == new_url
        assert client.get(new_url).status_code == 200
    finally:
        settings.set_many({"share_image_url": ""})


def test_tag_cloud_archive_links_and_pages(admin, client):
    from soloblog import settings
    save_post(admin, title="Cloud one", tags="alpha, beta")
    save_post(admin, title="Cloud two", tags="alpha")
    tags = client.get("/tags").text
    assert "badge-xl" in tags  # the most used tag is the biggest
    archive = client.get("/archive").text
    assert 'href="/archive#' in archive and 'id="20' in archive
    off = {"side_tags": "off", "side_archive": "off", "side_author": "off", "side_tags_where": "roll",
           "side_archive_where": "roll", "toc_numbers": "0"}
    try:
        settings.set_many({**off, "side_tags": "under", "side_archive": "left"})
        home = client.get("/").text
        assert 'data-panel="side-tags"' in home and 'data-panel="side-archive"' in home
        assert home.index('data-panel="side-archive"') < home.index('data-panel="side-tags"')  # beside, then under
        assert 'data-side-panel="left"' in home and 'data-side-fallback="left"' in home
        # posts only get them when asked, stacked under a contents on the same side
        body = "## One\n\ntext\n\n## Two\n\ntext\n\n### Two point one\n\ntext"
        slug = save_post(admin, title="Side panel post", body=body)
        settings.set_many({"toc_style": "side"})
        assert "side-archive" not in client.get(f"/{slug}", follow_redirects=True).text
        settings.set_many({"side_tags_where": "roll,posts", "side_archive_where": "roll,posts", "toc_numbers": "1"})
        page = client.get(f"/{slug}", follow_redirects=True).text
        column = page[page.index('data-side-panel="left"'):]
        assert column.index('data-panel="toc"') < column.index('data-panel="side-archive"')
        assert "data-toc-numbers" in page and "[&_a]:whitespace-normal" in page
        # not on pages unless asked - About stays clean
        about = save_post(admin, title="About me here", body="Hello.", pinned="1", pin_location="header")
        assert posts.is_page(posts.get_post(about))
        page = client.get(f"/{about}", follow_redirects=True).text
        assert "About me here" in page and "side-archive" not in page and "side-tags" not in page
        settings.set_many(off)
        assert "side-tags" not in client.get("/").text
    finally:
        settings.set_many({**off, "toc_style": "top"})


def test_pagination_numbers():
    from soloblog.ui import Pagination
    html = str(Pagination(5, 12, "/"))
    for n in ("1", "4", "6", "12"):
        assert f'href="/?page={n}"' in html
    assert 'aria-current="page"' in html and "…" in html and 'href="/?page=9"' not in html


def test_link_posts_to_your_own_pages(admin, client):
    slug = save_post(admin, title="Travel posts", link_url="/tag/travel", body="")
    assert posts.get_post(slug)["link_url"] == "/tag/travel"
    for bad in ("//evil.example", "javascript:alert(1)", "/a b", '/x"onmouseover'):
        assert posts.clean_link(bad) == ""
    # a visitor goes straight there, like an outside link
    r = client.get(posts.url_for(posts.get_post(slug)), follow_redirects=False)
    assert r.headers.get("location") == "/tag/travel"


def test_custom_css_is_listed_where_it_can_be_reverted():
    # every custom CSS override approved since the list began is tagged in
    # input.css and has a row in docs/DEVELOPMENT.md > Custom CSS - one
    # without the other can't be found again, or taken out cleanly
    import re
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    css = Path(os.path.join(root, "static", "css", "input.css")).read_text(encoding="utf-8")
    doc = Path(os.path.join(root, "docs", "DEVELOPMENT.md")).read_text(encoding="utf-8")
    section = doc.split("## Custom CSS", 1)[1].split("\n## ", 1)[0]
    tagged = re.findall(r"\[custom-css: ([a-z0-9-]+)\]", css)
    listed = re.findall(r"^\| `([a-z0-9-]+)` \|", section, re.M)
    # one override can cover rules in more than one place - each is tagged
    assert tagged and len(listed) == len(set(listed))
    assert set(tagged) == set(listed)


def test_the_daisyui_rules_that_slowed_every_page_are_left_out(client):
    # each made the browser restyle the whole page on every change - every
    # key typed in the editor. They're taken out as the stylesheet is
    # served (docs/DEVELOPMENT.md > Removed daisyUI rules): gone from what's
    # served, and still in the build - a daisyUI update that renamed one
    # would bring it back under a name nothing here takes out
    from soloblog import themes
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    built = Path(os.path.join(root, "static", "css", "output.css")).read_text(encoding="utf-8")
    page = client.get("/").text
    href = re.search(r'href="(/static/css/output\.css\?v=\w+)"', page).group(1)
    r = client.get(href)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/css")
    served = r.text
    for name, rule in themes.REMOVED_RULES.items():
        assert any(rule.search(s) for s in _has_selectors(built)), f"{name} isn't in daisyUI's build any more"
        assert not any(rule.search(s) for s in _has_selectors(served)), name
    # and nothing else went: every palette, and daisyUI's other :has() rules
    for theme in themes.DAISYUI_THEMES:
        assert f"[data-theme={theme}]" in served, theme
    assert ".list .list-row:has(" in served and served.count("{") == served.count("}")
    doc = Path(os.path.join(root, "docs", "DEVELOPMENT.md")).read_text(encoding="utf-8")
    section = doc.split("## Removed daisyUI rules", 1)[1].split("\n## ", 1)[0]
    assert set(re.findall(r"^\| `([a-z-]+)` \|", section, re.M)) == set(themes.REMOVED_RULES)
    # our own: off :has() where it isn't on what's styled (sibling rules,
    # attributes set by a script instead)
    css = Path(os.path.join(root, "static", "css", "input.css")).read_text(encoding="utf-8")
    assert "body:has(" not in css and "editor-phonebar:has(" not in css
    assert ":has(.EasyMDEContainer" not in css and ".EasyMDEContainer:has(" not in css
    for folder, _dirs, names in os.walk(os.path.join(root, "soloblog")):
        for name in names:
            if name.endswith((".py", ".js")):
                text = Path(os.path.join(folder, name)).read_text(encoding="utf-8")
                assert "group-has-[" not in text and "grid:has(" not in text and "[body:has(" not in text, name


def _has_selectors(css):
    from soloblog import themes
    for m in re.finditer(r"([^{};]+)\{", css):
        prelude = m.group(1).strip()
        if ":has(" in prelude and not prelude.startswith("@"):
            yield from (" ".join(s.split()) for s in themes._top_commas(prelude))


def test_lean_css_takes_out_only_the_selectors_it_names():
    from soloblog import themes
    css = ('@layer x{.toggle:has(:checked) > :nth-child(2){opacity:0}'
           ':root:has(input.theme-controller[value=nord]:checked),[data-theme=nord]{color-scheme:light;--a:1}'
           '.filter [type="radio"].btn{a:b}.keep:has(> .x){c:d}'
           '.card{color:red;&:hover{color:blue}.input:has( > input[disabled]) ::placeholder{e:f}}'
           '.a::after{content:"{not a block};"}}')
    lean = themes.lean_css(css)
    assert ".toggle" not in lean and "theme-controller" not in lean and "input[disabled]" not in lean
    assert "[data-theme=nord]{color-scheme:light;--a:1}" in lean
    for kept in ('.filter [type="radio"].btn{a:b}', ".keep:has(> .x){c:d}", "&:hover{color:blue}",
                 'content:"{not a block};"'):
        assert kept in lean, kept
    assert lean.count("{") == lean.count("}")
    # minified or spread out, the same
    assert themes.lean_css(css.replace("{", " {\n  ").replace(";", ";\n")).count("toggle") == 0


def test_shown_for_blocks_start_out_right(admin):
    # a block shown for one choice (data-shown-for) is hidden or shown by
    # the server from what's saved - the script only follows changes, so
    # one without hidden= showed the wrong thing until a field changed
    # (Classic menus' button lists, back after a reload)
    from html.parser import HTMLParser
    from soloblog import settings
    from soloblog.ui import SETTINGS_SECTIONS

    class Page(HTMLParser):
        def __init__(self):
            super().__init__()
            self.values, self.blocks, self.select = {}, [], None

        def handle_starttag(self, tag, attrs):
            a = dict(attrs)
            if a.get("data-shown-for"):
                self.blocks.append((a["data-shown-for"], "hidden" in a))
            if tag == "input" and a.get("name"):
                if a.get("type") in ("radio", "checkbox"):
                    if "checked" in a:
                        self.values[a["name"]] = a.get("value", "on")
                    else:
                        self.values.setdefault(a["name"], "")
                else:
                    self.values[a["name"]] = a.get("value", "")
            if tag == "select":
                self.select = a.get("name")
                self.values.setdefault(self.select, None)
            if tag == "option" and self.select and ("selected" in a or self.values[self.select] is None):
                self.values[self.select] = a.get("value", "")

        def handle_endtag(self, tag):
            if tag == "select":
                self.select = None

    def check(tab):
        page = Page()
        page.feed(admin.get(f"/admin/settings?tab={tab}").text)
        for rules, hidden in page.blocks:
            # "a=x;b=y": shown while either holds (_syncShownFor, app.py)
            results = []
            for rule in rules.split(";"):
                negate = "!=" in rule
                name, wanted = rule.split("!=" if negate else "=", 1)
                if name in page.values:
                    match = (page.values[name] or "") in wanted.split("|")
                    results.append(not match if negate else match)
            if results:
                assert hidden == (not any(results)), (tab, rules, page.values)

    before = {k: settings.get(k) for k in ("editor_toolbar_rows", "editor_phone_bar")}
    try:
        for style in ("one", "menus", "none"):
            for phone in ("sections", "buttons", "none"):
                settings.set_many({"editor_toolbar_rows": style, "editor_phone_bar": phone})
                check("editor")
        for tab, _ in SETTINGS_SECTIONS:
            check(tab)
    finally:
        settings.set_many(before)


def test_footnotes_beside_the_text(admin, client):
    # on out of the box: the page says so, and app.js places them
    slug = save_post(admin, title="Sources", body="A claim.[^1]\n\n[^1]: The source.")
    assert 'data-sidenotes="1"' in client.get(f"/post/{slug}").text
    js = client.get("/app.js").text
    assert "function place()" in js and "sidenote not-prose" in js and "details:not([open])" in js
    # Settings > Appearance > Reading experience turns it off
    before = settings.get("sidenotes")
    try:
        admin.post("/admin/settings/style", data={"declared_fields": "sidenotes"})
        assert settings.get("sidenotes") == "0"
        assert "data-sidenotes" not in client.get(f"/post/{slug}").text
        admin.post("/admin/settings/style", data={"sidenotes": "1", "declared_fields": "sidenotes"})
        assert settings.get("sidenotes") == "1"
    finally:
        settings.set_many({"sidenotes": before})


def test_search_results_open_from_anywhere_on_them(admin, client):
    # the search page's rows open on a click anywhere (ROW_LINKS_JS), the
    # live results under the magnifier are each one link
    save_post(admin, title="Brinebread by the sea", body="Bread and fog.")
    page = client.get("/search?q=brinebread").text
    assert "data-click-rows" in page
    assert "[data-click-rows]" in client.get("/app.js").text
    live = client.get("/search/results?q=brinebread").text
    assert live.count("<a ") == 1 and "Brinebread by the sea" in live and "hover:bg-base-200" in live
    # the link picker's rows look and work the same - one row, one button
    from soloblog.ui import RESULT_ROW
    picker = admin.get("/admin/link-picker?q=brinebread").text
    assert RESULT_ROW in picker and RESULT_ROW in live and 'type="button"' in picker


def test_cards_fill_their_last_row():
    """10 posts in rows of 3 left one card alone - with Cards the page
    size rounds up to fill the row; 2 in a row, or the narrow width, 2."""
    from soloblog.routes.public import card_columns, page_size
    s = {"roll_style": "cards", "posts_per_page": "10", "cards_per_row": "3", "body_width": "standard"}
    assert card_columns(s) == 3 and page_size(s) == 12
    assert page_size({**s, "cards_per_row": "2"}) == 10 and page_size({**s, "posts_per_page": "9"}) == 9
    assert card_columns({**s, "body_width": "narrow"}) == 2 and page_size({**s, "body_width": "narrow"}) == 10
    assert page_size({**s, "roll_style": "list"}) == 10 and page_size({**s, "posts_per_page": "x"}) == 12


def test_the_admin_keeps_its_own_font(admin, client):
    """The site's fonts are for its pages and the editor's preview - the
    admin, a tool, stays in its own."""
    from soloblog import fonts, settings
    assert {k for _, keys in fonts.GROUPS for k in keys} == set(fonts.STACKS)
    before = {k: settings.get(k) for k in ("font_body", "font_headings")}
    settings.set_many({"font_body": "didone", "font_headings": "industrial"})
    try:
        site, panel = client.get("/").text, admin.get("/admin/posts").text
        assert "body { font-family: Didot" in site and "h1, h2, h3, h4, .card-title { font-family: Bahnschrift" in site
        assert "body { font-family" not in panel and ".editor-preview h1" in panel
    finally:
        settings.set_many(before)


def test_a_page_past_the_end_goes_to_the_last(client):
    r = client.get("/?page=999")
    assert r.status_code == 302 and (r.headers["location"] == "/" or r.headers["location"].startswith("/?page="))


def test_side_panels_each_where_it_is_wanted(admin, client):
    """Tags on posts, archive on pages, the author on the blog roll - each
    panel shows where it's set to, and a post can leave them all out."""
    from soloblog import settings
    keys = ("side_tags", "side_archive", "side_author", "side_tags_where", "side_archive_where",
            "side_author_where", "author_name", "author_bio")
    before = {k: settings.get(k) for k in keys}
    try:
        settings.set_many({"side_tags": "under", "side_archive": "under", "side_author": "under",
                           "side_tags_where": "posts", "side_archive_where": "pages", "side_author_where": "roll",
                           "author_name": "Mira", "author_bio": "Baker of emergency bread."})
        home = client.get("/").text
        assert 'data-panel="side-author"' in home and "Baker of emergency bread." in home
        assert 'data-panel="side-tags"' not in home and 'data-panel="side-archive"' not in home
        slug = save_post(admin, title="A post with tags beside", tags="sidepanel")
        post = client.get(f"/post/{slug}").text
        assert 'data-panel="side-tags"' in post and 'data-panel="side-archive"' not in post
        page = save_post(admin, title="A page with the archive", pinned="1", pin_location="header")
        assert 'data-panel="side-archive"' in client.get(f"/{page}", follow_redirects=True).text
        # this post leaves them out (Show > Side panels unticked)
        save_post(admin, slug=slug, title="A post with tags beside", tags="sidepanel",
                  extras=["byline", "tags"], extras_before="", extras_before_page="")
        assert 'data-panel="side-tags"' not in client.get(f"/post/{slug}").text
    finally:
        settings.set_many({k: v or "" for k, v in before.items()})

def test_one_primary_button_per_admin_page(admin):
    """docs/DEVELOPMENT.md > Buttons: at most one filled button in a page's
    content - its Save, or its one main action. The sidebar's New post and
    dialogs (their own confirm) aside."""
    import re
    from soloblog.ui import SETTINGS_SECTIONS
    pages = ["/admin/posts", "/admin/new", "/admin/media", "/admin/comments", "/admin/messages", "/admin/health",
             "/admin/stats", "/admin/help"] + [f"/admin/settings?tab={key}" for key, _ in SETTINGS_SECTIONS]
    for path in pages:
        html = admin.get(path).text
        main = re.sub(r"<dialog\b.*?</dialog>|<aside\b.*?</aside>|<nav\b.*?</nav>", "", html, flags=re.S)
        main = main.split("<main", 1)[-1] if "<main" in main else main
        # the sidebar's own full-width New post (in the margin and the drawer)
        main = re.sub(r'<a [^>]*class="btn btn-primary btn-sm w-full shrink-0"[^>]*href="/admin/new"[^>]*>', "", main)
        main = re.sub(r'<a [^>]*href="/admin/new"[^>]*class="btn btn-primary btn-sm w-full shrink-0"[^>]*>', "", main)
        primaries = re.findall(r'class="[^"]*\bbtn-primary\b[^"]*"', main)
        assert len(primaries) <= 1, (path, len(primaries))


def test_visitors_can_go_back_to_the_default_theme(client):
    from soloblog import settings
    before = settings.get("visitor_theme_switching")
    settings.set_many({"visitor_theme_switching": "1"})
    try:
        page = client.get("/").text
        assert "data-theme-default" in page and 'data-onclick="resetTheme"' in page and "window.siteTheme" in page
    finally:
        settings.set_many({"visitor_theme_switching": before or "0"})


def test_a_save_that_changes_the_frame_reloads_the_page(admin):
    """Text size, the palette, the sidebar's items - saved in place they'd
    only show on the next page, so their Save says to reload; others don't."""
    from soloblog import settings
    before = settings.get("font_size")
    try:
        other = "large" if before != "large" else "small"
        r = admin.post("/admin/settings/style", data={"font_size": other, "declared_fields": "font_size"},
                       headers={"HX-Request": "true"})
        assert 'data-reload="1"' in r.text
        r = admin.post("/admin/settings/style", data={"font_size": other, "declared_fields": "font_size"},
                       headers={"HX-Request": "true"})
        assert "data-reload" not in r.text  # nothing changed this time
    finally:
        settings.set_many({"font_size": before or "medium"})


def test_print_button_off_until_chosen(admin, client):
    from soloblog import settings
    before = settings.get("post_shows")
    try:
        # a new site: everything around a post but Print
        settings.set_many({"post_shows": ""})
        slug = save_post(admin, title="Printable recipe")
        page = client.get(f"/post/{slug}").text
        assert "printPage" not in page and 'id="listen-button"' in page and 'id="reading-progress"' in page
        settings.set_many({"post_shows": "print,byline"})
        page = client.get(f"/post/{slug}").text
        assert 'data-onclick="printPage"' in page and '<span class="text-sm font-medium">Print</span>' in page
        # the header, footer and side panels stay off the paper
        assert "print:hidden" in page
    finally:
        settings.set_many({"post_shows": before or ""})


def test_each_post_shows_setting(admin, client):
    """Settings > Appearance > Each post shows: share buttons, related
    posts, the author and the rest switched off for every post at once -
    and a post that says otherwise keeps its own."""
    from soloblog import settings
    before = settings.get("post_shows")
    slug = save_post(admin, title="Shows little")
    try:
        r = admin.post("/admin/settings/style", data={"post_shows": ["byline", "tags"],
                                                           "declared_fields": "post_shows"},
                       headers={"HX-Request": "true"})
        assert r.status_code == 200 and settings.get("post_shows") == "byline,tags"
        page = client.get(f"/post/{slug}").text
        assert 'data-share' not in page and "Related posts" not in page and 'id="listen-button"' not in page
        form = admin.get("/admin/settings?tab=posts").text
        assert 'name="post_shows" value="share"' in form and 'name="listen_button"' not in form
        # nothing ticked is nothing, not the default
        admin.post("/admin/settings/style", data={"declared_fields": "post_shows"},
                   headers={"HX-Request": "true"})
        assert settings.get("post_shows") == "none"
        from soloblog import pages
        assert pages.default_extras(False) == set() == pages.default_extras(True)
    finally:
        settings.set_many({"post_shows": before or ""})


def test_a_rows_menu_closes_after_a_choice_and_its_icons_match(admin):
    # Discard, Settings or Help in the editor's ⋯ left the menu open on a
    # phone - every row menu closes once its item has done its work
    from soloblog import app as app_module, ui
    js = app_module.POPOVER_DROPDOWN_JS
    assert "[popover]:is([data-row-menu], [data-more-menu]) :is(button, a)" in js and "menu.hidePopover()" in js
    # one icon size in a phone's menu - the editor's Help icon was 18 px
    # beside 14 and 16
    assert "max-sm:[&_.btn>svg]:size-4" in ui.ROW_MENU_CLS
    html = admin.get("/admin/new").text
    bar = html[html.index('id="editor-actions"'):html.index('id="body-editor"')]
    assert 'class="editor-icon"' not in bar


def test_rows_you_swipe_fade_where_there_is_more(admin):
    # the phone's toolbar row, All's tabs and the bulk bar (checked in a
    # browser: right at the start, both mid-way, left at the end)
    from soloblog import app as app_module, ui
    from soloblog.routes import editor
    js = app_module.LIVE_JS
    copy = js[js.index("var SCROLLS_X = "):js.index("';", js.index("var SCROLLS_X = ")) + 1]
    assert "".join(re.findall(r"'([^']*)'", copy)) == ui.SCROLLS_X
    assert "function _scrollHintX" in js and "querySelectorAll('[data-scroll-x]')" in js
    init = editor.EDITOR_INIT_JS
    assert init.count("' + SCROLLS_X") == 3 and "_scrollHintX(row)" in init
    save_post(admin, title="A row to select")
    html = admin.get("/admin/posts").text
    assert "data-scroll-x" in html and ui.SCROLLS_X.split()[1] in html


def test_search_and_picker_dialogs_float_centred_on_a_phone(admin):
    # glued to the screen's top and sides on a phone, and on the left of
    # one wider than the box (checked in a browser at 320, 412 and 600)
    from soloblog import ui
    for part in ("mx-auto", "max-sm:mt-2", "max-sm:w-[calc(100%-1rem)]", "max-sm:rounded-box"):
        assert part in ui.SEARCH_DIALOG_BOX, part
    page = admin.get("/admin/new").text
    for dialog in ("search-modal", "media-picker-dialog", "link-picker-dialog", "template-start-dialog", "template-dialog"):
        at = page.index(f'id="{dialog}"')
        box = page[at:page.index("</dialog>", at)]
        assert "max-sm:rounded-box" in box, dialog


def test_a_side_panel_fits_between_the_header_and_the_columns_end(admin):
    # the admin menu with Settings open, on a short page: pushed up under
    # the header, its foot flush on the footer - it gets shorter instead,
    # and fades where its list goes on (checked in a browser at 800 and
    # 600 px tall: 24 px clear of each)
    from soloblog import app as app_module
    js = app_module.CHROME_OFFSETS_JS
    fit = js[js.index("function fitSidePanels"):js.index("var _fitPending")]
    assert "var room = end - stuckAt" in fit and "_scrollHint(inner)" in fit
    assert "fitSidePanels();" in js[js.index("function placeSidePanels"):]
    html = admin.get("/admin/settings?tab=name").text
    rail = html[html.rindex("<", 0, html.index("data-admin-rail")):]
    # only its list of pages scrolls, with the fade at its foot (a mask on
    # the rail would fade its fill); New post, View your site and Log out stay
    assert "data-own-scroll" in rail[:rail.index(">")]
    pages = rail[rail.rindex("<div", 0, rail.index('id="admin-nav-margin"')):]
    pages = pages[:pages.index(">")]
    assert "data-scroll-hint" in pages and "overflow-y-auto" in pages
    assert rail.index("New post") < rail.index(pages) < rail.index("View your site")


def test_settings_presets_and_preset_and_custom_templates_are_named_apart(admin):
    # "preset" alone meant the site's looks; the starting texts were
    # "outlines" - one name each now, everywhere (decided 2026-10-19)
    assert "Settings presets" in admin.get("/admin/settings?tab=style").text
    assert "Custom templates" in admin.get("/admin/settings?tab=editor").text
    editor_page = admin.get("/admin/new").text
    assert "Apply a template" in editor_page and "Use outline" not in editor_page
    reference = Path("docs/guide/reference.md").read_text(encoding="utf-8")
    write = Path("docs/guide/writing.md").read_text(encoding="utf-8")
    assert "### Settings presets" in reference and "**Built-in**" in write
    assert "Use\noutline" not in reference + write


def test_a_new_posts_template_picker_has_its_templates_recent_custom_and_built_in(admin):
    # a new post's Template label opens the picker - no Start from box beside
    # it. A template card shows the sections it has and goes to a new post from it
    import json
    from soloblog import post_templates
    before = {k: settings.get(k) for k in ("post_templates", "template_recent")}
    try:
        settings.set_many({"template_recent": "", "post_templates": json.dumps([
            {"id": "aa11", "name": "Weekend bake", "tags": "",
             "body": "## Ingredients\n\nSection: Ingredients\n\n- Flour"},
            {"id": "bb22", "name": "Monthly letter", "tags": "", "body": "Dear reader"}])})
        groups = [c[2] for c in post_templates.choices()]
        assert groups[:2] == ["Custom"] * 2 and set(groups[2:]) == {"Built-in"}
        assert all(len(c) == 3 for c in post_templates.choices())
        # starting from one puts it first under Recent, three at most, gone ones left out
        for key in ("faq", "mine-aa11", "recipe", "faq"):
            admin.get(f"/admin/new?template={key}")
        first = post_templates.choices()[:3]
        assert [c[0] for c in first] == ["faq", "recipe", "mine-aa11"] and {c[2] for c in first} == {"Recent"}
        assert [c[0] for c in post_templates.choices()].count("faq") == 1
        settings.set_many({"template_recent": "mine-gone,faq"})
        assert post_templates.recent() == ["faq"]
        page = admin.get("/admin/new").text
        assert 'id="start_from"' not in page and "Start from" not in page
        dialog = page[page.index('id="template-start-dialog"'):].split("</dialog>")[0]
        assert ">Choose a template</h3>" in dialog and ">Custom</p>" in dialog and ">Built-in</p>" in dialog
        assert ">Recent</p>" in dialog or "Recent" not in dialog
        bake = dialog[dialog.index('href="/admin/new?template=mine-aa11"'):][:2500]
        assert "<svg" not in bake and ">Weekend bake</span>" in bake and ">Custom</span>" in bake
        assert ">Ingredients</span>" in bake
        assert "Yours" not in dialog
        # a blank one first, chosen while it's not from a template - its address says blank,
        # since an address without a template follows Settings > Editor > New posts start from
        assert re.search(r'<a href="/admin/new\?template=" aria-selected="true"', dialog)
        # a post you're editing starts from nothing: no Template label, only Apply a template
        slug = posts.write(None, "Test", title="Saved already", body="Words.")
        try:
            edit = admin.get(f"/admin/edit/{slug}").text
            assert 'id="template-start-dialog"' not in edit and "Template: " not in edit
            assert 'id="template-dialog"' in edit
        finally:
            posts.delete_post(slug)
    finally:
        settings.set_many(before)


def test_a_search_box_takes_the_cursor_only_where_theres_a_keyboard():
    # on a phone the keyboard came up over the list - planned fix 24
    # (checked in a browser: a phone focuses the dialog, a computer the box)
    from soloblog import app as app_module
    from soloblog.routes import editor
    js = app_module.ACTIONS_JS
    assert "function _keyboardToHand() { return matchMedia('(hover: hover)').matches; }" in js
    assert "function showDialog(d)" in js and "if (d) showDialog(d);" in js
    for script in (app_module.MEDIA_PICKER_JS, app_module.LINK_PICKER_JS):
        assert "showDialog(dlg)" in script and "showModal" not in script
    assert "if (_keyboardToHand()) search.focus();" in app_module.POPOVER_DROPDOWN_JS
    assert "if (_keyboardToHand()) input.focus();" in editor.SLASH_MENU_JS
    assert "if (_keyboardToHand()) box.focus();" in app_module.INDEX_SEARCH_JS
    assert "_keyboardToHand()" in editor.EDITOR_HELP_JS


def test_every_place_choice_is_worded_and_ordered_alike(admin):
    # Contents said "Beside the post, on the left", side panels "Beside,
    # on the left", with Off first in one and last in the other
    from soloblog import pages, ui
    from soloblog.routes import editor
    assert list(pages.TOC_STYLES.values()) == ["At the top", "On the left", "On the right", "Off"]
    assert [t for _, t in editor.OWN_SIDE_PLACES] == ["Under the post", "On the left", "On the right", "Off"]
    assert list(ui.SIDE_PLACES.values()) == ["Under the posts", "On the left", "On the right", "Off"]
    page = admin.get("/admin/new").text
    assert "Beside the post, on the" not in page and "Beside, on the" not in page


def test_the_editor_shows_the_posts_state_beside_its_heading(admin):
    # checked in a browser: Draft, Published, Scheduled, Unlisted as Post
    # settings change, back again on Discard, desktop and phone
    from soloblog.routes import editor
    page = admin.get("/admin/new").text
    head = page[page.index("<h1"):page.index("<h1") + 600]
    assert 'id="post-state"' in head and ">Draft<" in head and "badge-warning" in head and "data-now=" in head
    slug = save_post(admin, title="Out in the world", published=True)
    page = admin.get(f"/admin/edit/{slug}").text
    head = page[page.index("<h1"):page.index("<h1") + 600]
    assert ">Published<" in head and "badge-success" in head
    js = editor.EDITOR_INIT_JS
    assert "var syncState = function" in js and "form.addEventListener('reset'" in js
    for state, look in editor.STATE_LOOK.items():
        assert f"{state}: '{look}'" in js, state


def test_focus_is_called_focus_everywhere(admin):
    # one name, decided 2026-10-19 - it was "Focus mode"
    slug = save_post(admin, title="A post to focus on")
    for path in ("/admin/new", f"/admin/edit/{slug}", "/admin/posts", "/admin/settings?tab=editor"):
        # what people read - not the comments in the page's scripts
        shown = re.sub(r"<script\b.*?</script>", "", admin.get(path).text, flags=re.S)
        assert "Focus mode" not in shown, path
    import glob
    for doc in glob.glob("docs/guide/*.md") + ["docs/FAQ.md", "README.md"]:
        assert "Focus mode" not in Path(doc).read_text(encoding="utf-8"), doc


def test_every_sidebar_scrolls_alike(admin):
    # a thin scrollbar and a fade at its foot while there's more: Post
    # settings had it, Help, Media's details and the admin's didn't
    from soloblog import ui
    edit = admin.get("/admin/new").text
    # Post settings scrolls inside its card (#post-settings), so the
    # scrollbar can't square off the card's rounded corners
    def tag(html, mark):
        return html[html.rindex("<", 0, html.index(mark)):html.index(">", html.index(mark))]

    def next_tag(html, mark):
        # the last one: the phone's drawer comes after the side column's copy
        at = html.index("<", html.rindex(mark))
        return html[at:html.index(">", at)]
    for panel in ("post-settings", "editor-help-scroll"):
        t = tag(edit, f'id="{panel}"')
        assert "data-scroll-hint" in t and ui.SCROLLS.split()[0] in t, panel
    # the fade is a mask: on a panel with a fill, the fill faded too and
    # the page showed through Help's foot - so it's on a box inside
    media = admin.get("/admin/media").text
    for html, panel in ((edit, 'id="editor-help-panel"'), (media, 'id="media-details-panel"'),
                        (media, 'class="drawer-side')):
        assert "mask-image" not in tag(html, panel) and "data-scroll-hint" not in tag(html, panel), panel
    inner = next_tag(media, 'id="media-details-panel"')
    assert "data-scroll-hint" in inner and ui.SCROLLS.split()[0] in inner and "bg-base" not in inner
    # the admin's menu scrolls only its list of pages: New post above and
    # View your site and Log out below stay in sight, in the rail and the drawer
    assert media.count('id="admin-nav') == 2
    for at in (m.start() for m in re.finditer('id="admin-nav', media)):
        box = media[media.rindex("<div", 0, at):at]
        assert "data-scroll-hint" in box and "overflow-y-auto" in box and ui.SCROLLS.split()[0] in box
        assert "bg-base" not in box and "View your site" not in box
        rest = media[at:media.index("Log out", at)]
        assert rest.index("</ul>") < rest.index("</div>") < rest.index("View your site")


def test_a_fade_shows_only_while_there_is_more_to_scroll_to():
    # a side panel kept its fade after Settings folded away in it - the
    # fold ends after its animation; and a sliver of padding counted as more
    from soloblog import app as app_module
    assert "el.scrollHeight - el.scrollTop - el.clientHeight > 16" in app_module.LIVE_JS
    fit = app_module.CHROME_OFFSETS_JS
    assert "new ResizeObserver(function () { fitSidePanels(); })" in fit[fit.index("function fitSidePanels"):]
    # a sliver short, it keeps its rounded foot rather than being cut
    assert "if (room < inner.offsetHeight - 16)" in fit


def test_side_panels_stop_where_they_start():
    # the admin side panel and Post settings crept up 24 px on the first
    # scroll (checked in a browser: a long post, a Settings page, and the
    # end of a short page, where it may use the room to fit whole)
    from soloblog import app as app_module
    from soloblog.routes import editor
    fit = app_module.CHROME_OFFSETS_JS
    fit = fit[fit.index("function fitSidePanels"):]
    assert "startsAt - stopsAt <= 3 * rem && !fitsOnlyHigher" in fit and "window.innerHeight - 1.5 * rem" in fit
    assert "as the admin's rail is on the left" in Path(os.path.join(os.path.dirname(editor.__file__), "..", "js",
                                                                     "pin_location.js")).read_text()


def test_a_fade_follows_its_box_changing_size():
    # folding Post settings' sections left the fade at its foot (checked in
    # a browser: gone once everything fits, back when it doesn't)
    from soloblog import app as app_module
    js = app_module.LIVE_JS
    assert "function _watchHint(el)" in js and "_watchHint(el);" in js[js.index("function _scrollHint(el)"):]


def test_a_side_panel_uses_the_room_down_to_the_footer():
    # on a short page the admin menu stopped at its column's end, empty room
    # under it while its list was cut (checked in a browser at 1430 x 1170:
    # it runs to 24 px above the footer, then fades)
    from soloblog import app as app_module
    fit = app_module.CHROME_OFFSETS_JS
    fit = fit[fit.index("function fitSidePanels"):]
    assert "footer.getBoundingClientRect().top - 1.5 * rem" in fit
    assert "side.getBoundingClientRect().bottom - parseFloat" not in fit


def test_a_phone_keyboard_leaves_the_timers_own_length_open():
    # the keyboard made the window shorter, the bar refit and moved the
    # timer in ⋯ - closing it under your finger; and the field sat under it
    from soloblog import app as app_module
    from soloblog.routes import editor
    init = editor.EDITOR_INIT_JS
    assert "onWidth(fitEditorBar)" in init and "onWidth(mergeBars)" in init
    assert "window.addEventListener('resize', mergeBars)" not in init
    assert "field.scrollIntoView({block: 'nearest'})" in app_module.POPOVER_DROPDOWN_JS


def test_the_full_screen_phone_bar_sits_on_the_keyboards_top_edge():
    # its height left out Android's strip below it, and the bar sat under it
    from soloblog.routes import editor
    assert "window.innerHeight - rect.top" in editor.EDITOR_INIT_JS


def test_preview_outside_focus_has_no_scrollbar_of_its_own():
    # it was fitted 2 px short (the box's borders), and on a phone that tiny
    # scrollbar caught the first swipe instead of the page
    from soloblog.routes import editor
    js = Path(os.path.join(os.path.dirname(editor.__file__), "..", "js", "editor_init.js")).read_text()
    fit = js[js.index("// Preview, outside Focus"):js.index("// on a touch screen the browser's own corner")]
    assert "pv.scrollHeight + borders" in fit and "pv.style.overflowY = 'hidden'" in fit
    # Focus scrolls it again, and leaves Write's height for the way out
    assert "if (mde.isFullscreenActive()) { if (pv) pv.style.overflowY = ''; return; }" in fit
    assert "attributeFilter: ['class']" in fit and "document.fonts.ready.then(fit)" in fit


def test_a_fields_list_fits_above_a_phones_keyboard(admin):
    # the time zone list didn't flip above the keyboard and then closed:
    # placed in what you can see, again as the keyboard moves, closed only
    # by a scroll you made, and a squeezed list gives way - not its search
    from soloblog import app as app_module
    js = app_module.POPOVER_DROPDOWN_JS
    place = js[js.index("function placeMenu"):js.index("document.addEventListener('toggle', function (e) {\n  if (e.newState === 'open' && _placedMenu")]
    assert "seen.bottom - r.bottom" in place and "window.innerHeight - r.bottom" not in place
    assert "Date.now() - _scrolledAt < 800" in place and "trigger.scrollIntoView({block: 'nearest'})" in place
    assert "visualViewport.addEventListener('resize', _keyboardMoved)" in js
    assert "if (box.matches(':popover-open')) placeMenu(box)" in js
    html = admin.get("/admin/settings?tab=language").text
    at = html.rindex("<div", 0, html.index('id="timezone-combo"'))
    combo = html[at:at + 4000]
    assert "[&amp;:popover-open]:flex" in combo or "[&:popover-open]:flex" in combo
    assert "min-h-0 flex-1 overflow-y-auto" in combo and "w-full mb-1 shrink-0" in combo


def test_the_phone_bar_sits_on_what_you_can_see_without_a_keyboard_api():
    # Firefox has no keyboard API: placed from the window's foot, its full
    # screen put the bar under the keyboard - now from what's shown
    from soloblog.routes import editor
    js = editor.EDITOR_INIT_JS
    assert "phoneBar.style.top = Math.max(0, vv.offsetTop + vv.height - phoneBar.offsetHeight) + 'px'" in js
    assert "window.innerHeight - vv.height - vv.offsetTop" not in js


def test_a_fallback_says_so_and_an_example_looks_like_one(admin):
    # grey text read as a value already set: a field that follows something
    # else when empty says "Empty: ..." every time, and an example says e.g.
    from soloblog import settings
    settings.set_many({"tagline": "Bread and bikes", "site_title": "Mira's"})
    try:
        pages = "".join(admin.get(f"/admin/settings?tab={t}").text
                        for t in ("name", "address", "header", "banner", "newsletter", "members", "messages",
                                  "analytics", "sharing", "profile"))
        for name in ("app_name", "members_intro", "newsletter_title", "newsletter_intro", "consent_message",
                     "contact_intro", "banner_heading", "banner_subheading", "banner_button_text", "support_message"):
            assert f'name="{name}"' in pages, name
            at = pages.index(f'name="{name}"')
            assert "Empty:" in pages[at:at + 1500], name
        assert 'placeholder="Bread and bikes"' in pages  # the Description and banner fall back to it
        assert 'placeholder="5"' not in pages and 'placeholder="50"' not in pages
    finally:
        settings.set_many({"tagline": "", "site_title": "My Blog"})


def test_cards_one_a_row_are_each_like_magazines_first(admin, client):
    from soloblog import settings
    keep = {k: settings.get(k) for k in ("roll_style", "cards_per_row")}
    try:
        admin.post("/admin/settings/style", data={"roll_style": "cards", "cards_per_row": "1",
                                                       "declared_fields": "roll_style,cards_per_row"},
                   headers={"HX-Request": "true"})
        assert settings.get("cards_per_row") == "1"
        save_post(admin, title="One wide card", body="Words.", cover_image="/uploads/x.webp")
        home = client.get("/").text
        assert "min-h-64 sm:min-h-80" in home and "sm:grid-cols-3" not in home.split("<main")[1]
    finally:
        settings.set_many(keep)


def test_tabs_that_lose_their_more_menu_are_left_alone():
    # Help's tabs threw a script error when its content was swapped while
    # they were being fitted (the phone check, at 375 px)
    from soloblog import app as app_module
    fit = app_module.CHROME_OFFSETS_JS
    fit = fit[fit.index("function fitTabs"):]
    assert fit.index("if (!menu) return;") < fit.index("menu.replaceChildren()")


def test_worded_buttons_are_one_size_with_an_icon(admin):
    # Empty trash, the bulk bar, Revisions' Compare and others were a size
    # smaller than the rest, some without an icon (docs/DEVELOPMENT.md > Buttons)
    from soloblog import ui
    bulk = str(ui.to_xml(ui.BulkButton("Move to trash", "trash", danger=True)))
    assert "btn btn-sm text-error" in bulk and "<svg" in bulk
    for url in ("/admin/media?tab=trash", "/admin/comments?tab=pending", "/admin/posts", "/admin/new"):
        page = admin.get(url).text
        assert 'btn btn-xs text-error' not in page and 'btn btn-xs"' not in page, url


def test_a_see_through_upload_stays_see_through():
    """A transparent PNG (a logo) was flattened on upload, its clear parts
    turned black. A photo is still saved without an alpha channel."""
    import io
    import os
    from PIL import Image
    from soloblog import config, images
    clear = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
    clear.paste((96, 93, 255, 255), (10, 10, 30, 30))
    buf = io.BytesIO()
    clear.save(buf, "PNG")
    url = images.save_upload(buf.getvalue(), "logo.png")
    with Image.open(os.path.join(config.uploads_dir(), url.rsplit("/", 1)[1])) as saved:
        assert saved.mode == "RGBA" and saved.getpixel((1, 1))[3] == 0
    photo = io.BytesIO()
    Image.new("RGB", (40, 40), (200, 120, 40)).save(photo, "JPEG")
    url = images.save_upload(photo.getvalue(), "photo.jpg")
    with Image.open(os.path.join(config.uploads_dir(), url.rsplit("/", 1)[1])) as saved:
        assert saved.mode == "RGB"


def test_media_in_use_shows_only_what_posts_use(admin):
    """Media's In use tab: the files a post or setting uses, and none of
    the unused ones - the other half of the Unused tab."""
    import io
    from PIL import Image
    from conftest import save_post
    from soloblog import images
    def upload(name):
        buf = io.BytesIO()
        Image.new("RGB", (20, 20), (10, 120, 200)).save(buf, "PNG")
        return images.save_upload(buf.getvalue(), name)
    used, idle = upload("in-use-picture.png"), upload("idle-picture.png")
    save_post(admin, title="Uses a picture", body=f"![A picture]({used})")
    page = admin.get("/admin/media?tab=used").text
    assert ">In use<" in page and used.rsplit("/", 1)[1] in page and idle.rsplit("/", 1)[1] not in page


def test_a_file_a_setting_uses_is_never_unused(admin):
    """The header icon, app icon and share image showed as unused - only
    the avatar and favicon were looked for - and a site's logo was trashed
    from the Unused tab. Every setting that holds a file counts."""
    import io
    from PIL import Image
    from soloblog import images, settings
    buf = io.BytesIO()
    Image.new("RGB", (20, 20), (96, 93, 255)).save(buf, "PNG")
    logo = images.save_upload(buf.getvalue(), "the-logo.png")
    before = settings.get("header_icon_url")
    try:
        settings.set_many({"header_icon_url": logo})
        name = logo.rsplit("/", 1)[1]
        assert name in images.usage_map() and images.usage_map()[name][0]["title"] == "Header icon"
        assert name not in {o["filename"] for o in images.list_orphans()}
    finally:
        settings.set_many({"header_icon_url": before})


def test_an_image_with_a_dark_mode_version(admin, client):
    """Media > an image's details > Dark mode version: posts carry the dark
    one for the page to swap in while it's dark, galleries too; the dark
    one counts as used and follows a rename; only a real image is taken."""
    import io
    from PIL import Image
    from soloblog import images
    def upload(name, colour):
        buf = io.BytesIO()
        Image.new("RGB", (20, 20), colour).save(buf, "PNG")
        return images.save_upload(buf.getvalue(), name)
    light, dark = upload("screen-light.png", (240, 240, 240)), upload("screen-dark.png", (20, 20, 20))
    light_name, dark_name = light.rsplit("/", 1)[1], dark.rsplit("/", 1)[1]
    r = admin.post(f"/admin/media/details/{light_name}", data={"alt_text": "A screen", "dark_version": dark})
    assert r.status_code == 200 and images.get_meta(light_name)["dark_version"] == dark_name
    assert f'value="{dark}"' in r.text and "Dark mode version" in r.text

    slug = save_post(admin, title="Light and dark", body=f"![A screen]({light})\n\n```gallery\n{light}\n```")
    page = client.get(posts.url_for(posts.get_post(slug)), follow_redirects=True).text
    assert page.count(f'data-dark-src="{dark}"') == 2
    assert 'data-scheme="light"' in page
    assert dark_name not in {o["filename"] for o in images.list_orphans()}

    # a rename keeps the pair
    new = images.rename_upload(dark_name, "screen-at-night")
    assert images.get_meta(light_name)["dark_version"] == new

    # not itself, not something that isn't there, not a way out of uploads
    for bad in (light, "/uploads/nothing-here.webp", "../../etc/passwd", "/uploads/_trash"):
        images.set_meta(light_name, "A screen", "", dark_version=bad)
        assert images.get_meta(light_name)["dark_version"] == ""


def test_an_image_with_a_phone_version(admin, client):
    """Media > an image's details > Phone version: posts carry it for the
    page to swap in on a phone - in a gallery and a story's held copy too -
    next to a dark mode version if there is one; it counts as used, follows
    a rename, and only a real image is taken."""
    import io
    from PIL import Image
    from soloblog import config, images

    def upload(name, size, colour):
        buf = io.BytesIO()
        Image.new("RGB", size, colour).save(buf, "PNG")
        return images.save_upload(buf.getvalue(), name)
    wide = upload("app-wide.png", (1600, 900), (240, 240, 240))
    phone = upload("app-phone.png", (1200, 2400), (200, 200, 240))
    dark = upload("app-dark.png", (20, 20), (20, 20, 20))
    wide_name, phone_name = wide.rsplit("/", 1)[1], phone.rsplit("/", 1)[1]
    with open(os.path.join(config.uploads_dir(), "notes.pdf"), "wb") as f:
        f.write(b"%PDF-1.4 not an image")

    # the field is there, empty, with its picker
    page = admin.get(f"/admin/media/details/{wide_name}").text
    assert "Phone version" in page and 'name="phone_version"' in page and 'id="media-phone-version"' in page
    assert "shown in place of this one on a phone" in page

    # a post with no phone version carries nothing for it
    slug = save_post(admin, title="Wide and phone", body=f"![App]({wide})\n\n```gallery\n{wide}\n```\n\n"
                     f"## The tour\n\nSection: Story\n\n### One\n\n![App]({wide})\n\nWords.\n")
    url = posts.url_for(posts.get_post(slug))
    assert ' data-phone-src=' not in client.get(url, follow_redirects=True).text

    r = admin.post(f"/admin/media/details/{wide_name}", data={"alt_text": "App", "phone_version": phone})
    assert r.status_code == 200 and images.get_meta(wide_name)["phone_version"] == phone_name
    assert f'value="{phone}"' in r.text and "Saved" in r.text
    assert images.get_meta(wide_name)["dark_version"] == ""
    page = client.get(url, follow_redirects=True).text
    # the picture, the gallery's, and the story's own and held copies; each with its smaller copies
    assert page.count(f'data-phone-src="{phone}"') == 4
    assert page.count(f'data-phone-srcset="{phone}?w=400 400w') == 4
    assert ' data-dark-src=' not in page
    assert phone_name not in {o["filename"] for o in images.list_orphans()}

    # a dark mode version too: both ride along, the page decides which wins
    images.set_meta(wide_name, "App", "", dark_version=dark)
    assert images.get_meta(wide_name)["phone_version"] == phone_name
    page = client.get(url, follow_redirects=True).text
    assert page.count(f'data-phone-src="{phone}"') == 4 and page.count(f'data-dark-src="{dark}"') == 4

    # a rename keeps it; saving the details without the field clears it
    new = images.rename_upload(phone_name, "app-on-a-phone")
    assert images.get_meta(wide_name)["phone_version"] == new
    admin.post(f"/admin/media/details/{wide_name}", data={"alt_text": "App", "phone_version": ""})
    assert images.get_meta(wide_name)["phone_version"] == ""
    assert ' data-phone-src=' not in client.get(url, follow_redirects=True).text

    # not itself, not something that isn't there, not a way out of uploads, not a file that isn't an image
    for bad in (wide, "/uploads/nothing-here.webp", "../../etc/passwd", "/uploads/_trash", "\x00", "😀",
                "/uploads/notes.pdf", "x" * 400):
        images.set_meta(wide_name, "App", "", phone_version=bad)
        assert images.get_meta(wide_name)["phone_version"] == "", bad
        r = admin.post(f"/admin/media/details/{wide_name}", data={"alt_text": "App", "phone_version": bad})
        assert r.status_code == 200 and images.get_meta(wide_name)["phone_version"] == "", bad


def test_a_phone_version_can_have_its_own_dark_mode_version(admin, client):
    """A picture chosen as another's phone version can itself have a Dark mode
    version: the post carries it as data-phone-dark-src for a phone while the
    page is dark. It counts as used, and a phone version without one adds
    nothing."""
    import io
    from PIL import Image
    from soloblog import images

    def upload(name, colour):
        buf = io.BytesIO()
        Image.new("RGB", (1200, 2400), colour).save(buf, "PNG")
        return images.save_upload(buf.getvalue(), name)
    wide, phone = upload("pd-wide.png", (240, 240, 240)), upload("pd-phone.png", (200, 200, 240))
    phone_dark = upload("pd-phone-dark.png", (20, 20, 40))
    wide_name, phone_name, phone_dark_name = (u.rsplit("/", 1)[1] for u in (wide, phone, phone_dark))
    slug = save_post(admin, title="Phone dark", body=f"![App]({wide})\n\n```gallery\n{wide}\n```\n")
    url = posts.url_for(posts.get_post(slug))
    images.set_meta(wide_name, "App", "", phone_version=phone)

    # a phone version with no dark version of its own: only the phone one
    page = client.get(url, follow_redirects=True).text
    assert page.count(f'data-phone-src="{phone}"') == 2 and " data-phone-dark-src=" not in page

    # give the phone picture its own Dark mode version, in its own details
    r = admin.post(f"/admin/media/details/{phone_name}", data={"alt_text": "App", "dark_version": phone_dark})
    assert r.status_code == 200 and images.get_meta(phone_name)["dark_version"] == phone_dark_name
    page = client.get(url, follow_redirects=True).text
    assert page.count(f'data-phone-src="{phone}"') == 2 and page.count(f'data-phone-dark-src="{phone_dark}"') == 2
    assert page.count(f'data-phone-dark-srcset="{phone_dark}?w=400 400w') == 2
    assert " data-dark-src=" not in page
    assert phone_dark_name not in {o["filename"] for o in images.list_orphans()}

    # the wide picture's own dark version rides along beside it
    wide_dark = upload("pd-wide-dark.png", (10, 10, 10))
    images.set_meta(wide_name, "App", "", dark_version=wide_dark, phone_version=phone)
    page = client.get(url, follow_redirects=True).text
    assert page.count(f'data-dark-src="{wide_dark}"') == 2 and page.count(f'data-phone-dark-src="{phone_dark}"') == 2

    # a phone picture used alone (not as anyone's phone version) never gets the phone attribute
    alone = save_post(admin, title="Phone alone", body=f"![Alone]({phone})\n")
    assert " data-phone-dark-src=" not in client.get(posts.url_for(posts.get_post(alone)), follow_redirects=True).text

    # taking the phone version away takes its dark one with it
    images.set_meta(wide_name, "App", "", phone_version="")
    assert " data-phone-dark-src=" not in client.get(url, follow_redirects=True).text


def test_a_phone_version_comes_back_with_a_backup(admin):
    import io
    from PIL import Image
    from soloblog import backup, images

    def upload(name):
        buf = io.BytesIO()
        Image.new("RGB", (20, 20), (9, 9, 9)).save(buf, "PNG")
        return images.save_upload(buf.getvalue(), name).rsplit("/", 1)[1]
    wide, phone = upload("backup-wide.png"), upload("backup-phone.png")
    images.set_meta(wide, "Wide", "", phone_version=phone)
    data = backup.build_backup_zip({"images"})
    get_db().execute("UPDATE image_meta SET phone_version='' WHERE filename=?", (wide,))
    get_db().commit()
    assert images.get_meta(wide)["phone_version"] == ""
    backup.import_backup_zip(data, {"images"})
    assert images.get_meta(wide)["phone_version"] == phone
    images.set_meta(wide, "Wide", "", phone_version="")


def test_the_script_that_swaps_pictures_knows_phones():
    """The narrow-screen swap watches for the screen changing and for
    pictures added later."""
    from soloblog import app
    js = app.PICTURE_VERSIONS_JS
    assert "(max-width: 767px)" in js and "data-phone-src" in js and "-srcset" in js
    assert "narrow.addEventListener('change', swapAll)" in js and "MutationObserver" in js


def test_a_site_with_a_phone_version_always_sends_the_swap_script(admin, client):
    """Even a site that's light only, with no theme switcher: the script
    comes with the first phone version and goes with the last - and
    without the theme script, which such a site has no use for."""
    import io
    from PIL import Image
    from soloblog import images
    keep = {k: settings.get(k) for k in ("theme_mode", "visitor_theme_switching")}
    buf = io.BytesIO()
    Image.new("RGB", (20, 20), (1, 2, 3)).save(buf, "PNG")
    wide = images.save_upload(buf.getvalue(), "swap-wide.png").rsplit("/", 1)[1]
    buf = io.BytesIO()
    Image.new("RGB", (20, 20), (3, 2, 1)).save(buf, "PNG")
    phone = images.save_upload(buf.getvalue(), "swap-phone.png").rsplit("/", 1)[1]
    try:
        settings.set_many({"theme_mode": "light", "visitor_theme_switching": "0"})
        images.set_meta(wide, "A", "", phone_version="")
        page = client.get("/").text
        assert "img[data-phone-src]" not in page and "function chosen()" not in page
        images.set_meta(wide, "A", "", phone_version=phone)
        page = client.get("/").text
        assert "img[data-phone-src]" in page and "function chosen()" not in page
        images.set_meta(wide, "A", "", phone_version="")
        assert "img[data-phone-src]" not in client.get("/").text
        # a themed site has both, the theme one first
        settings.set_many({"visitor_theme_switching": "1"})
        images.set_meta(wide, "A", "", phone_version=phone)
        page = client.get("/").text
        assert page.index("function chosen()") < page.index("img[data-phone-src]")
    finally:
        settings.set_many(keep)
        images.set_meta(wide, "A", "", phone_version="")
    # choosing a picture fills its field with an input event that reaches the form, or Save never shows
    from soloblog import js as scripts
    assert "new Event('input', {bubbles: true})" in scripts.read("media_picker.js")
    assert "new Event('input')" not in scripts.read("link_picker.js")


def test_a_side_panel_has_one_way_to_be_off(admin):
    # Off, and Shows on with nothing ticked, did the same: Shows on now
    # hides while it's Off, and clearing every tick saves Off
    keys = ("side_tags", "side_tags_where")
    before = {k: settings.get(k) for k in keys}
    post = lambda data: admin.post("/admin/settings/style", headers={"hx-request": "true"},  # noqa: E731
                                   data={"declared_fields": "side_tags,side_tags_where", **data})
    try:
        post({"side_tags": "right", "side_tags_where": ["roll", "posts"]})
        assert settings.get("side_tags") == "right" and settings.get("side_tags_where") == "roll,posts"
        post({"side_tags": "right"})  # every tick cleared
        assert settings.get("side_tags") == "off"
        assert settings.get("side_tags_where") == settings.DEFAULTS["side_tags_where"]  # ticked again when chosen
        page = admin.get("/admin/settings?tab=blog").text
        assert 'data-shown-for="side_tags!=off" hidden' in page
        # a form without the ticks (another tab's) leaves it alone
        settings.set_many({"side_tags": "left"})
        admin.post("/admin/settings/style", headers={"hx-request": "true"},
                   data={"declared_fields": "side_tags", "side_tags": "left"})
        assert settings.get("side_tags") == "left"
    finally:
        settings.set_many(before)


def test_search_engines_dont_quote_the_colours_menu(client):
    # its thirty palette names showed as a site's description in search results
    import re
    from soloblog import settings
    before = settings.get("visitor_theme_switching")
    try:
        settings.set_many({"visitor_theme_switching": "1"})
        html = client.get("/").text
        menu = re.search(r'<div[^>]*id="nav-theme-menu"[^>]*>', html).group(0)
        assert "data-nosnippet" in menu
    finally:
        settings.set_many({"visitor_theme_switching": before or ""})


def test_a_wide_section_leaves_nothing_beside_the_post(admin, client):
    # contents at the top, the other panels under the post, and the
    # section really wide - not squeezed back into the column
    intro = "## One\n\nText.\n\n## Two\n\nText.\n\n"
    for width in ("Wide", "Full"):
        body = intro + f"## Numbers\n\nSection: Numbers\nWidth: {width}\n\n### 4\nthings\n"
        slug = save_post(admin, title=f"Roomy {width}", body=body, tags="otters", toc_style="side",
                         sides_tags="left")
        html = client.get(f"/post/{slug}").text
        assert 'data-side-panel' not in html
        assert 'data-panel="side-tags"' in html and "data-side-fallback" not in html
        assert 'data-toc-top' in html or 'id="toc"' in html or "toc" in html
        assert "w-screen" in html and html.index("w-screen") > html.index("Text.")
    plain = save_post(admin, title="Roomy none", body=intro + "## Numbers\n\nSection: Numbers\nWidth: Column\n\n### 4\nthings\n",
                      tags="otters", toc_style="side", sides_tags="left")
    html = client.get(f"/post/{plain}").text
    assert html.count('data-side-panel="left"') == 1


def test_a_rows_more_menu_draws_its_buttons_as_menu_rows():
    from soloblog.ui.base import MORE_MENU_CLS
    for c in ("[&_.btn]:w-full", "[&_.btn]:justify-start", "[&_.btn]:border-transparent", "[&_.btn]:shadow-none",
              "[&_.btn:hover]:bg-base-200", "[&_.tooltip]:before:hidden"):
        assert c in MORE_MENU_CLS


def test_menu_items_and_ghost_buttons_show_a_keyboard_focus_ring():
    # daisyUI's own focus on a menu item or ghost button is a ~1.1:1 tint
    # (WCAG 2.4.7): a 2px ring, on :focus-visible only, never a mouse click
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    css = Path(os.path.join(root, "static", "css", "input.css")).read_text(encoding="utf-8")
    doc = Path(os.path.join(root, "docs", "DEVELOPMENT.md")).read_text(encoding="utf-8")
    start = css.index("[custom-css: menu-focus]")
    rule = css[start:css.index("\n\n", start)]
    assert ".menu" in rule and ".btn-ghost:focus-visible" in rule
    assert "outline: 2px solid currentColor" in rule
    assert ":focus-visible {" in rule and ":focus {" not in rule
    assert "| `menu-focus` |" in doc.split("## Custom CSS", 1)[1]


def test_the_homepage_post_is_the_homepage_not_also_a_post(admin, client):
    # left out of the blog list, feeds and tag pages by itself - it needed
    # Unlisted for that, which kept it out of search - and found in search at /
    slug = save_post(admin, title="Homepage words", body="A zanzibar of words.", tags="hometag")
    before = settings.get("home_page")
    try:
        settings.set_many({"home_page": slug})
        assert "Homepage words" not in client.get("/blog").text
        assert "Homepage words" not in client.get("/rss").text
        assert "Homepage words" not in client.get("/tag/hometag").text
        found = client.get("/search/results?q=zanzibar", headers={"HX-Request": "true"}).text
        assert "Homepage words" in found and f'href="/post/{slug}"' not in found and 'href="/"' in found
        # an Unlisted one too, as the homepage picker offers - it's open to anyone at /
        save_post(admin, slug=slug, title="Homepage words", body="A zanzibar of words.", unlisted="1")
        assert posts.get_post(slug)["unlisted"]
        assert "Homepage words" in client.get("/search/results?q=zanzibar", headers={"HX-Request": "true"}).text
        assert f"/post/{slug}" not in client.get("/sitemap.xml").text
    finally:
        settings.set_many({"home_page": before})


def test_search_finds_the_sites_own_pages_in_the_menu(admin, client):
    # Blog, Archive... aren't posts or pages: a search that a word of their
    # menu name starts lists them first, with their address
    keys = ("home_page", "nav_archive_on")
    before = {k: settings.get(k) for k in keys}
    try:
        settings.set_many({"nav_archive_on": "1"})
        found = client.get("/search/results?q=arch", headers={"HX-Request": "true"}).text
        assert 'href="/archive"' in found and ">Archive<" in found
        page = client.get("/search?q=archive").text
        assert 'href="/archive" class="btn btn-sm"' in page
        # one that's not in the menu isn't offered
        settings.set_many({"nav_archive_on": ""})
        assert 'href="/archive"' not in client.get("/search/results?q=arch", headers={"HX-Request": "true"}).text
    finally:
        settings.set_many(before)
