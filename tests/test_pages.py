from pathlib import Path
import json
import re

from soloblog import posts
from conftest import save_post
from page_samples import SAMPLES


def _save(admin, key, template=None, **extra):
    """A sample page; template - it also has that template's Post settings."""
    from soloblog import post_templates
    title, summary, body = SAMPLES[key]
    slug = save_post(admin, title=f"{title} ({key})", summary=summary, body=body, **extra)
    if template:
        chosen = post_templates.get(template)["settings"]
        posts.write(slug, **{k: v for k, v in chosen.items() if k != "link_url"})
    return slug


def _ld(html, kind):
    blocks = [json.loads(b) for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]
    return next((b for b in blocks if b["@type"] == kind), None)


def test_a_layout_line_is_never_written_and_does_nothing(admin, client):
    slug = _save(admin, "recipe")
    path = posts._path(slug)
    assert "layout" not in Path(path).read_text(encoding="utf-8")
    # a stray line - an old file, a pasted one - is an unknown line like any other: no error, no effect
    text = Path(path).read_text(encoding="utf-8")
    Path(path).write_text(text.replace("---\n", "---\nlayout: landing\n", 1), encoding="utf-8")
    posts.reindex_from_disk()
    html = client.get(f"/post/{slug}").text
    assert client.get(f"/post/{slug}").status_code == 200 and "Tomato soup" in html
    assert 'data-section="ingredients"' in html and 'data-section="hero"' not in html
    # saved again, the line is gone
    posts.write(slug, title="Tomato soup (recipe)")
    assert "layout" not in Path(path).read_text(encoding="utf-8")
    # the editor has no layout to choose
    page = admin.get(f"/admin/edit/{slug}").text
    assert 'name="layout"' not in page and 'id="layout-select"' not in page and "Page layout" not in page


def test_every_sample_page_renders(admin, client):
    for key in SAMPLES:
        extra = {"link_url": "https://example.com/essay"} if key == "link" else {}
        slug = _save(admin, key, **extra)
        r = client.get(f"/post/{slug}")
        assert r.status_code == 200, key
        assert "data-layout" not in r.text and "Section:" not in r.text.split("<article", 1)[1], key


def test_resume(admin, client):
    html = client.get(f"/post/{_save(admin, 'resume', template='resume')}").text
    assert 'data-onclick="printPage"' in html and "2021 – Present" in html
    assert '<span class="badge badge-outline">Figma</span>' in html
    assert _ld(html, "ProfilePage")


def test_timeline_faq_projects(admin, client):
    html = client.get(f"/post/{_save(admin, 'milestones')}").text
    assert 'class="timeline ' in html and ">2019<" in html and "The first sale" in html
    html = client.get(f"/post/{_save(admin, 'faq')}").text
    assert _body(html, "faq").count("collapse collapse-arrow join-item") == 2 or \
        _body(html, "faq").split('data-section="faq"')[1].count("collapse collapse-arrow") == 2
    assert [q["name"] for q in _ld(html, "FAQPage")["mainEntity"]] == ["Do you ship abroad?",
                                                                      "How long does delivery take?"]
    html = client.get(f"/post/{_save(admin, 'portfolio')}").text
    body = _body(html, "portfolio")
    # a Portfolio: the pictures first, each leading to its page
    assert html.count("<h1") == 1
    assert 'data-portfolio="grid"' in body and 'href="https://example.com/tides"' in body
    # no picture: a quiet tile of its own words
    assert "Soloblog theme" in body and "bg-base-content/5" in body


def test_pricing(admin, client):
    from soloblog import post_templates
    html = client.get(f"/post/{_save(admin, 'pricing')}").text
    body = _body(html, "pricing")
    # a plan per ## with a Price line; the rest stays text under the cards
    assert body.count('class="card card-border bg-base-100') == 2 and "@lg:grid-cols-2" in body
    assert '<span class="text-3xl font-bold">US$12</span>' in body and "> a month</span>" in body
    assert "Billed" in body and "never" in body
    # the one with a badge is pointed out, with the page's one primary button
    assert 'class="card card-border bg-base-100 border-primary transition' in body or "border-primary transition" in body
    assert body.count("btn-primary") == 1 and 'href="https://example.com/pro" class="btn btn-block btn-primary"' in body
    assert 'href="/contact" class="btn btn-block "' in body
    assert body.index("Prices include tax.") > body.rindex("card-actions")
    # a starting point in the editor: a page with a Pricing section
    assert "Section: Pricing" in post_templates.BUILT_IN["pricing"][1]


def test_a_new_post_offers_no_outline_to_fill_in(admin):
    # the templates are pages made of sections - there is nothing to offer when a layout is chosen
    page = admin.get("/admin/new").text
    assert "layout-outline" not in page and "layout-outlines" not in page and "Use outline" not in page


def test_timezones_found_by_typing(admin):
    """The time zone is a box you type a place or region into (ui.Combobox),
    grouped by region - not a list of 400."""
    for url in ("/admin/settings?tab=language", "/admin/welcome"):
        html = admin.get(url).text
        assert 'data-combo="timezone"' in html and 'data-combo-group="Australia"' in html, url
        assert 'data-value="Australia/Sydney" data-label="Sydney"' in html, url
        assert 'data-combo-item="argentina - buenos aires america america/argentina/buenos_aires"' in html, url
        assert "<optgroup" not in html, url


def test_wiki_links_and_backlinks(admin, client):
    target = save_post(admin, title="Baking bread")
    slug = _save(admin, "wiki")
    for note in (target, slug):
        posts.write(note, in_wiki=True)
    html = client.get(f"/post/{slug}").text
    assert f'<a href="/post/{target}" class="wiki-link">Baking bread</a>' in html
    # a page that doesn't exist: plain text for visitors, a "create" link for the admin
    assert 'data-tip="Not written yet">what hydration means</span>' in html
    # a note started from a link is one of the wiki's, whatever new posts start from
    assert '/admin/new?template=wiki&amp;title=Hydration' in admin.get(f"/post/{slug}").text
    form = admin.get("/admin/new?template=wiki&title=Hydration").text
    assert 'name="in_wiki" value="1" checked' in form
    assert "<code>[[not a link]]</code>" in html
    # the target lists what links to it, and /wiki lists both
    assert f'href="/post/{slug}"' in client.get(f"/post/{target}").text.split("Linked from")[1]
    wiki = client.get("/wiki").text
    assert f'href="/post/{target}"' in wiki and f'href="/post/{slug}"' in wiki
    # a new post's editor can start with the missing page's title
    assert 'value="Hydration"' in admin.get("/admin/new?title=Hydration").text


def test_wiki_front_page(admin, client):
    """/wiki: the notes pinned to start from, the latest edited, the most
    read, the topics and every note A to Z - and it can be the homepage,
    where the notes' breadcrumbs then lead."""
    from soloblog import settings
    from soloblog.db import get_db
    hub = save_post(admin, title="Zettel index", tags="method", pinned="1", pin_location="top")
    note = save_post(admin, title="Atomic notes", body="One idea a note. See [[Zettel index]].")
    for page in (hub, note):
        posts.write(page, in_wiki=True)
    get_db().execute("UPDATE posts SET views=500 WHERE slug=?", (note,))
    get_db().commit()
    # notes live in the wiki, not the blog roll - the archive still has them
    assert f'href="/post/{note}"' not in client.get("/").text and f'/post/{note}"' in client.get("/archive").text
    wiki = client.get("/wiki").text
    start, rest = wiki.split("Start here", 1)[1].split("Recently edited", 1)
    assert f'href="/post/{hub}"' in start and f'href="/post/{note}"' not in start
    assert "Most read" in rest and f'href="/post/{note}"' in rest.split("Most read")[1]
    assert "Topics" in wiki and "Every page, A to Z" in wiki
    # a note says where it leads, as well as what leads to it
    page = client.get(f"/post/{note}").text
    assert f'href="/post/{hub}"' in page.split("Links from here")[1] and 'href="/wiki"' in page
    before = settings.get("home_page")
    try:
        r = admin.post("/admin/settings/name", data={"home_page": "@wiki", "declared_fields": "home_page"},
                       headers={"HX-Request": "true"})
        assert r.status_code == 200 and settings.get("home_page") == "@wiki"
        home = client.get("/").text
        assert "Recently edited" in home and f'href="/post/{note}"' in home
        assert client.get("/wiki", follow_redirects=False).headers["location"] == "/"
        assert client.get("/blog").status_code == 200
        crumbs = client.get(f"/post/{note}").text.split('aria-label="Breadcrumbs"', 1)
        assert len(crumbs) == 1 or 'href="/wiki"' not in crumbs[1].split("</nav>")[0]
    finally:
        settings.set_many({"home_page": before or ""})


def test_link_interview_now(admin, client):
    slug = _save(admin, "link", link_url="https://example.com/essay")
    html = client.get(f"/post/{slug}").text
    assert 'href="https://example.com/essay"' in html and "Read it on example.com" in html
    feed = client.get("/feed.json").json()
    item = next(i for i in feed["items"] if i["url"].endswith(f"/post/{slug}"))
    assert item["external_url"] == "https://example.com/essay"

    html = client.get(f"/post/{_save(admin, 'interview')}").text
    assert html.count("chat chat-start") == 2 and html.count("chat chat-end") == 2
    assert "Start before you" in html

    # Remind me to update is what shows when it was last updated
    now = _save(admin, "now")
    assert "Last updated" not in client.get(f"/post/{now}").text
    posts.write(now, remind_update=True)
    html = client.get(f"/post/{now}").text
    assert "Last updated" in html and "nownownow.com" not in html


def test_recipe_bookshelf_uses_slides_docs(admin, client):
    html = client.get(f"/post/{_save(admin, 'recipe')}").text
    recipe = _ld(html, "Recipe")
    assert recipe["recipeYield"] == "4" and recipe["prepTime"] == "PT10M" and recipe["cookTime"] == "PT1H20M"
    assert recipe["recipeIngredient"] == ["1 kg tomatoes", "1 onion", "Salt"]
    assert len(recipe["recipeInstructions"]) == 3
    assert html.count('type="checkbox" class="peer checkbox') == 3 and "stat-title" in html

    html = client.get(f"/post/{_save(admin, 'reviews')}").text
    reviews = _ld(html, "ItemList")["itemListElement"]
    assert reviews[0]["item"]["reviewRating"]["ratingValue"] == 5
    assert reviews[1]["item"]["reviewRating"]["ratingValue"] == 4
    assert reviews[0]["item"]["itemReviewed"]["author"]["name"] == "Ursula K. Le Guin"
    assert 'aria-label="5 out of 5"' in html

    html = client.get(f"/post/{_save(admin, 'uses')}").text
    assert html.count('class="list-row') == 3 and 'href="https://example.com/monitor"' in html


    docs = _save(admin, "docs", template="docs", series_name="Guide", series_order="1")
    save_post(admin, title="Next steps", series_name="Guide", series_order="2")
    html = client.get(f"/post/{docs}").text
    # its contents beside it, in the margin of a normal-width page
    assert "data-toc" in html and "data-side-panel" in html and "max-w-6xl" not in html and "Next steps →" in html


def test_a_pinned_link_post_is_an_outside_menu_item(admin, client):
    from conftest import save_post
    slug = save_post(admin, title="My shop", body="", link_url="https://shop.example.com/",
                     pinned="1", pin_location="header")
    html = client.get("/").text
    assert 'href="https://shop.example.com/" target="_blank"' in html
    # nothing of its own to say, so its page forwards visitors on
    r = client.get(f"/{slug}")
    assert r.status_code == 302 and r.headers["location"] == "https://shop.example.com/"
    assert admin.get(f"/{slug}").status_code == 200
    save_post(admin, slug=slug, title="My shop", body="", pinned="")


def test_pages_live_at_the_root(admin, client):
    from conftest import save_post
    slug = save_post(admin, title="About me", pinned="1", pin_location="header")
    try:
        assert f'href="/{slug}"' in client.get("/").text
        r = client.get(f"/post/{slug}")
        assert r.status_code == 301 and r.headers["location"] == f"/{slug}"
        page = client.get(f"/{slug}")
        assert page.status_code == 200 and f'rel="canonical" href="http://localhost:5001/{slug}"' in page.text \
            or f'/{slug}"' in page.text
        # a slug a real route already uses keeps its /post/ address
        taken = save_post(admin, title="Tags", pinned="1", pin_location="footer")
        assert taken == "tags" and client.get("/post/tags").status_code == 200
        assert "Tags" in client.get("/tags").text
    finally:
        save_post(admin, slug=slug, title="About me", pinned="")
        save_post(admin, slug="tags", title="Tags", pinned="")


def test_old_addresses_find_their_post(admin, client):
    from conftest import save_post
    slug = save_post(admin, title="Moved from WordPress")
    for old in (f"/2019/04/{slug}/", f"/{slug}.html", f"/blog/{slug}/amp", f"/{slug}"):
        r = client.get(old)
        assert r.status_code == 301 and r.headers["location"] == f"/post/{slug}", old
    assert client.get("/2019/04/nothing-here/").status_code == 404
    assert client.get("/no-such-page").status_code == 404


def test_dark_mode_theme(admin, client):
    from soloblog import settings
    before = {k: settings.get(k) for k in ("theme", "theme_dark", "theme_mode")}

    def save(**values):
        r = admin.post("/admin/settings/style", headers={"hx-request": "true"},
                       data={**values, "declared_fields": ",".join(values)})
        assert r.status_code == 200

    try:
        # match the device: the light theme, the dark one ready to swap in
        save(theme="winter", theme_dark="night", theme_mode="auto")
        html = client.get("/").text
        assert 'data-theme="winter"' in html and 'data-dark-theme="night"' in html
        assert "prefers-color-scheme: dark" in html
        # always light, always dark
        save(theme_mode="light")
        html = client.get("/").text
        assert 'data-theme="winter"' in html and "data-dark-theme" not in html
        save(theme_mode="dark")
        assert 'data-theme="night"' in client.get("/").text
        # the dark theme is always a dark one
        save(theme_dark="light")
        assert settings.get("theme_dark") == "dark"
        # a site from before the pickers keeps its look
        from soloblog.themes import theme_choice
        assert theme_choice({"theme": "dracula", "theme_dark": ""}) == ("light", "dracula", "dark")
        assert theme_choice({"theme": "nord", "theme_dark": ""}) == ("nord", "dark", "light")
        # matching pairs pick both
        assert "choosePair" in admin.get("/admin/settings?tab=style").text
    finally:
        settings.set_many(before)


def test_font_choice(admin, client):
    from soloblog import settings
    assert "font-family: Charter" not in client.get("/").text
    admin.post("/admin/settings/style", headers={"hx-request": "true"},
               data={"theme": "light", "font_body": "transitional", "font_headings": "geometric", "font_x": "1",
                     "declared_fields": "theme,font_body,font_headings"})
    try:
        html = client.get("/").text
        assert "body { font-family: Charter" in html and "h1, h2, h3, h4, .card-title { font-family: Avenir" in html
        # every chosen font is sized by its small letters, so a serif with
        # short ones doesn't read a size smaller than the default
        assert html.count("font-size-adjust: 0.53") == 2
        admin.post("/admin/settings/style", headers={"hx-request": "true"},
                   data={"theme": "light", "font_body": "comic-sans", "declared_fields": "font_body"})
        assert settings.get("font_body") == ""
    finally:
        settings.set_many({"font_body": "", "font_headings": ""})


def test_text_size(admin, client):
    from soloblog import settings
    assert "data-font-size" not in client.get("/").text
    admin.post("/admin/settings/style", headers={"hx-request": "true"},
               data={"font_size": "large", "declared_fields": "font_size"})
    try:
        assert 'data-font-size="large"' in client.get("/").text
        assert 'data-font-size="large"' in admin.get("/admin/posts").text  # the admin too
        admin.post("/admin/settings/style", headers={"hx-request": "true"},
                   data={"font_size": "huge", "declared_fields": "font_size"})
        assert settings.get("font_size") == "medium" and "data-font-size" not in client.get("/").text
    finally:
        settings.set_many({"font_size": "medium"})


def test_folding_sections():
    from soloblog import pages
    html = ('<p>lead</p><h2 id="a">A</h2><p>1</p><blockquote><h2>quoted</h2></blockquote><h3 id="b">B</h3>'
            '<p>2</p><h2 id="c">C</h2><p>3</p><div class="footnote"><ol></ol></div>')
    out = pages.fold_sections(html, open_=True)
    assert out.startswith('<p>lead</p><div class="relative') and out.count("<details") == 3 and out.count(" open>") == 3
    # ### folds inside its ##; a heading in a quote stays put; footnotes stay out
    assert out.index('id="b"') > out.index('id="a"') and out.index('id="b"') < out.index('id="c"')
    assert "<blockquote><h2>quoted</h2></blockquote>" in out
    assert out.endswith('</details></div><div class="footnote"><ol></ol></div>')
    assert " open>" not in pages.fold_sections(html, open_=False)
    assert pages.fold_sections("<p>no headings</p>") == "<p>no headings</p>"
    # a heading's copy-link button can't be inside the summary that folds it
    # (a button in a button): it's beside it, and knows which section it's for
    out = pages.fold_sections(pages.heading_links(html))
    import re
    assert "copyHeadingLink" in out and not re.search(r"<summary[^>]*>(?:(?!</summary>).)*<button", out, re.S)
    assert 'data-target="a"' in out and 'data-target="b"' in out and 'data-target="c"' in out
    # without folding, it stays beside the heading's words
    assert re.search(r'<h2[^>]*id="a"[^>]*>A<button', pages.heading_links(html))


def test_contents_and_folding_choices(admin, client):
    from soloblog import settings
    body = "## One\n\nText.\n\n## Two\n\nText.\n\n## Three\n\nText.\n\n| a | b |\n|---|---|\n| 1 | 2 |\n"
    # set what the first check relies on - the shared settings are whatever
    # earlier tests left, and settings.py's own toc_style default is a side panel
    keys = ("toc_style", "heading_fold", "side_tags", "side_archive", "side_author")
    before = {k: settings.get(k) for k in keys}
    settings.set_many({"toc_style": "top", "heading_fold": "open", "side_tags": "off", "side_archive": "off",
                       "side_author": "off"})
    slug = save_post(admin, title="Folding and contents", body=body)
    try:
        html = client.get(f"/post/{slug}").text
        # contents at the top, sections foldable and open
        assert "data-toc" in html and "data-side-panel" not in html
        assert '<details class="group/fold collapse collapse-arrow' in html and 'open><summary' in html
        # a wide table scrolls, its columns kept readable on a phone
        assert '<div class="overflow-x-auto [&_:is(td,th)]:min-w-28"><table>' in html
        settings.set_many({"toc_style": "side", "heading_fold": "folded"})
        html = client.get(f"/post/{slug}").text
        assert "data-side-panel" in html and 'open><summary class="collapse-title' not in html
        # a post's own choice wins, and is kept in its file
        save_post(admin, slug=slug, title="Folding and contents", body=body, toc_style="off", heading_fold="off")
        html = client.get(f"/post/{slug}").text
        assert "data-toc" not in html and "collapse-arrow" not in html.split("<article")[1][:3000]
        assert "toc: 'off'" in Path(posts._path(slug)).read_text(encoding="utf-8")
        assert posts.get_post(slug)["heading_fold"] == "off"
    finally:
        settings.set_many(before)


def test_contents_nest_fold_and_link(admin, client):
    from soloblog import settings
    body = "## One\n\nText.\n\n### One a\n\nText.\n\n## Two\n\nText.\n\n## Three\n\nText.\n"
    # an earlier test's full Appearance save can leave these off
    settings.set_many({"toc_style": "top", "toc_fold": "auto", "heading_links": "1", "smooth_scroll": "1",
                       "heading_fold": "open"})
    slug = save_post(admin, title="Nested contents", body=body)
    try:
        html = client.get(f"/post/{slug}").text
        toc = html.split("data-toc=")[1].split("</ul></div>")[0]
        # the ### is in the contents, folded under its ##
        assert '<details open><summary><a href="#one">One</a></summary><ul><li><a href="#one-a">' in toc
        assert 'data-toc="auto"' in html
        # a copy-link button beside each heading, and smooth scrolling
        assert html.count('data-onclick="copyHeadingLink"') == 4 and 'data-smooth-scroll' in html
        settings.set_many({"toc_fold": "off", "heading_links": "0", "smooth_scroll": "0"})
        html = client.get(f"/post/{slug}").text
        toc = html.split("data-toc=")[1].split("</ul></div>")[0]
        assert "<details" not in toc and '<a href="#one-a">' in toc
        assert "copyHeadingLink" not in html and "data-smooth-scroll" not in html
    finally:
        settings.set_many({"toc_fold": "auto", "heading_links": "1", "smooth_scroll": "1"})


def _body(html, key=None):
    """What the page has between its start and its comments."""
    return html.split("<article", 1)[1].split('id="comments"')[0]


def test_profile(admin, client):
    save_post(admin, title="A recent post for the profile")
    html = client.get(f"/post/{_save(admin, 'profile', template='profile')}").text
    body = _body(html)
    # the page's own title is hidden for screen readers; the section draws the name, the photo round,
    # the line big, the links as buttons
    assert html.count("<h1") == 1 and '<h1 class="sr-only">Mira Castell (profile)</h1>' in html
    assert 'class="w-28 rounded-full' in body and 'class="text-xl text-base-content/80' in body
    assert 'href="/contact" class="btn btn-primary">Work with me' in body and 'href="/blog" class="btn ">' in body
    assert "Latest posts" in body and "A recent post for the profile" in body
    assert _ld(html, "ProfilePage")


def test_a_plain_heading_with_a_picture_is_plain_writing(admin, client):
    # nothing guessed: a ## without a Section: line is just writing, on a wide page too - a picture in
    # it isn't a band, and a short last one with a link isn't the closing card
    plain = "A line.\n\n## Words\n\n![A picture](/uploads/p.webp)\n\nSome words.\n\n## Last\n\nShort.\n\n[Go](/go)"
    body = _body(client.get(f"/post/{save_post(admin, title='Plain parts', body=plain, page_width='wide')}").text)
    assert "lg:grid-cols-[3fr_2fr]" not in body and "bg-primary text-primary-content" not in body
    assert "Some words." in body and 'href="/go"' in body


def test_services_testimonials_case_study(admin, client):
    body = _body(client.get(f"/post/{_save(admin, 'services')}").text, "services")
    assert body.count('class="card card-border bg-base-100"') == 2 and "US$1,200" in body
    # a numbered list under a ## is the steps
    assert body.count("size-9 rounded-full bg-primary") == 3
    body = _body(client.get(f"/post/{_save(admin, 'testimonials')}").text, "testimonials")
    assert body.count('class="card card-border bg-base-100 p-5 sm:p-6"') == 2 and "Owner, Corner Café" in body
    assert "<blockquote>" not in body and 'class="w-10 rounded-full"' in body
    html = client.get(f"/post/{_save(admin, 'project', template='project')}").text
    body = _body(html)
    assert "uppercase tracking-widest" in body and "Corner Café" in body
    # wide, with what follows the post in the reading column
    assert 'class="max-w-3xl mx-auto w-full"' in html


def test_events(admin, client):
    from soloblog.pages import event_date
    from datetime import date
    assert event_date("12 March 2026") == date(2026, 3, 12) == event_date("March 12, 2026") == event_date("2026-03-12")
    assert event_date("Thursday 12th Mar 2026, 7pm") == date(2026, 3, 12)
    assert event_date("sometime in spring") is None and event_date("31 February 2026") is None
    html = client.get(f"/post/{_save(admin, 'events')}").text
    body = _body(html, "events").split('data-section="events"')[1]
    # the one to come under Coming up; the past one folded away
    assert body.index("Coming up") < body.index("Mending as design practice") < body.index("Past events")
    assert body.index("Past events") < body.index("Repair café open day")
    assert '<details class="collapse' in body and "<details open" not in body
    assert _ld(html, "Event")["startDate"] in ("2099-03-12", "2020-06-04")


def test_business_and_menu(admin, client):
    html = client.get(f"/post/{_save(admin, 'business')}").text
    body = _body(html, "business")
    assert 'href="tel:0290000000"' in body and 'href="mailto:hello@example.com"' in body
    assert "openstreetmap.org/search?query=12%20Maple%20Street" in body
    assert '<table class="table table-sm' in body and ">Saturday</td>" in body
    biz = _ld(html, "LocalBusiness")
    assert biz["telephone"] == "02 9000 0000" and biz["openingHours"] == ["Monday Closed", "Saturday 10am - 2pm"]
    body = _body(client.get(f"/post/{_save(admin, 'menu')}").text, "menu")
    # list items and plain lines alike, the price on the right
    assert body.count("break-inside-avoid") == 4 and "@lg:columns-2" in body
    assert ">$9</span>" in body and "a country loaf" in body and ">$4.5</span>" in body


def test_press_coming_soon_team_shop(admin, client):
    body = _body(client.get(f"/post/{_save(admin, 'media-kit')}").text, "media-kit")
    assert 'data-copy="Mira Castell is a designer based in Springfield."' in body
    assert 'href="/uploads/portrait.webp" download=""' in body and "Download" in body
    # a list of links isn't something to copy (the other is the share buttons' Copy link)
    assert body.count('class="btn btn-xs">Copy</button>') == 1
    html = client.get(f"/post/{_save(admin, 'coming-soon')}").text
    assert html.count("<h1") == 1
    body = _body(client.get(f"/post/{_save(admin, 'team')}").text, "team")
    assert body.count("card card-border bg-base-100 overflow-hidden") == 2 and "Founder" in body
    # a ## that isn't a person stays text, under the cards
    assert body.rindex("Volunteer with us") > body.rindex("card-body")
    html = client.get(f"/post/{_save(admin, 'shop')}").text
    body = _body(html, "shop")
    assert body.count("card card-border bg-base-100 overflow-hidden") == 2 and "US$25" in body
    # each button goes to the seller's own checkout - nothing is bought here
    assert 'href="https://buy.stripe.com/test_harbour" target="_blank" rel="noopener"' in body
    assert '<span class="badge badge-sm self-start">Sold out</span>' in body
    assert body.index("Worldwide, within a week.") > body.rindex("card-body")


def test_wide_pages_keep_the_rest_in_the_column(admin, client):
    """A project, a landing page and the rest that widen the page keep
    the title, reactions, share buttons and comments at the reading
    column's width - the site's own, Narrow or Standard."""
    from soloblog import settings
    before = {k: settings.get(k) for k in ("body_width", "reactions_style")}
    try:
        settings.set_many({"reactions_style": "emoji"})
        for width, cls in (("standard", "max-w-3xl"), ("narrow", "max-w-2xl")):
            settings.set_many({"body_width": width})
            for key, extra in (("project", {}), ("recipe", {"page_width": "wide"})):
                html = client.get(f"/post/{_save(admin, key, template='project' if not extra else None, **extra)}").text
                after = html.split("<article")[1]
                # the emoji row, and what follows the post
                assert re.search(rf'<div class="{cls} mx-auto w-full[^"]*">\s*(?:<div[^>]*>\s*)?<div[^>]*id="reactions"', after), \
                    (key, width)
                assert re.search(rf'<div class="{cls} mx-auto w-full[^"]*">(?:(?!</article>).)*?id="comments"', html, re.S) \
                    or 'id="comments"' not in html, (key, width)
    finally:
        settings.set_many(before)


def test_the_end_of_a_post_is_one_group_spaced_by_the_page(admin, client):
    """Reactions, Share, Print, Support, series, related posts, the
    author and comments: one group PART_GAP from the
    writing, each part SECTION_GAP from the next - both follow Space. A
    fixed margin or a divider of its own made a band under one and left
    the next almost touching."""
    from bs4 import BeautifulSoup
    from soloblog import pages, settings
    keys = ("reactions_style", "post_shows", "support_kofi", "social_mastodon", "author_name", "author_bio",
            "side_author")
    before = {k: settings.get(k) for k in keys}
    try:
        settings.set_many({"reactions_style": "emoji", "post_shows": ",".join(pages.EXTRAS),
                           "support_kofi": "https://ko-fi.com/sam", "social_mastodon": "https://m.example/@sam",
                           "author_name": "Sam", "author_bio": "Writes things.", "side_author": "off"})
        save_post(admin, title="Gaps one", tags="gaps", series_name="Gaps")
        slug = save_post(admin, title="Gaps two", tags="gaps", series_name="Gaps")
        soup = BeautifulSoup(client.get(f"/post/{slug}").text, "html.parser")
        group = soup.find(id="comments").find_parent(class_="flex-col")
        assert set(pages.PART_GAP.split()) | set(pages.PARTS.split()) <= set(group["class"])
        parts = group.find_all(recursive=False)
        assert len(parts) >= 6, [p.get("id") or p.get("class") for p in parts]
        for part in parts:
            # its own room, or room above what it starts with
            first = part.find(recursive=False)
            fixed = [c for c in part.get("class", []) if re.match(r"(sm:)?(m[tby]-|divider)", c)] + \
                [c for c in (first.get("class", []) if first else []) if re.match(r"(sm:)?(m[ty]-|divider)", c)]
            assert not fixed, (part.get("id") or part.get("class"), fixed)
            assert not part.find(class_="divider"), part.get("class")
        for kind in ("reactions", "comments"):
            assert group.find(id=kind), kind
    finally:
        settings.set_many(before)


def test_print_sits_with_listen_and_reactions_with_share(admin, client):
    """Print is one of the post's buttons at the top, in their outline
    look; the reactions and Share share one row at the end, the same
    pills. Each still follows its own Show setting, and none prints."""
    from bs4 import BeautifulSoup
    from soloblog import pages, settings
    from soloblog.ui import SHARE_PILL
    before = {k: settings.get(k) for k in ("reactions_style", "post_shows")}
    try:
        settings.set_many({"reactions_style": "emoji", "post_shows": ",".join(pages.EXTRAS)})
        slug = save_post(admin, title="Buttons together")
        soup = BeautifulSoup(client.get(f"/post/{slug}").text, "html.parser")
        top = soup.find(id="listen-button").parent
        printer = top.find(attrs={"data-onclick": "printPage"})
        assert printer and printer.get_text(strip=True) == "Print"
        assert {"btn-outline", "btn-sm", "print:hidden"} <= set(printer["class"]) and "print:hidden" in top["class"]
        row = soup.find(id="reactions").parent
        share = row.find(attrs={"aria-label": "Share"})
        assert share and share.parent is row and {"sm:flex-row", "print:hidden"} <= set(row["class"])
        assert all(set(SHARE_PILL.split()) <= set(b["class"]) for b in share.find_all(["a", "button"]))
        assert all("btn-outline" in b["class"] for b in soup.find(id="reactions").find_all("button"))
        # each off on its own
        settings.set_many({"post_shows": ",".join(k for k in pages.EXTRAS if k not in ("print", "share"))})
        html = client.get(f"/post/{slug}").text
        assert "printPage" not in html and 'aria-label="Share"' not in html and 'id="reactions"' in html
    finally:
        settings.set_many(before)


def test_a_landing_page_built_from_sections(admin, client):
    # each ## can say what kind of section it is ("Section: Pricing"), its
    # ### items shown as that section shows them - built from what Insert >
    # Sections adds, so those always work
    from soloblog import sections
    snippets = {key: sections.markdown(key) for key in sections.REGISTRY}
    body_md = ("Everything you need, in one tin.\n\n[Get it](/shop)\n\n"
               + "\n\n".join(snippets[k] for k in ("picture_and_text", "numbers", "testimonials", "logos", "pricing",
                                                   "products", "services", "team", "faq", "cta"))
               + "\n\n## A plain one\n\nSection: Nonsense\n\nJust words.")
    slug = save_post(admin, title="The kit", body=body_md, page_width="wide")
    html = client.get(f"/post/{slug}").text
    body = _body(html)
    assert "Section:" not in body.replace("Section: Nonsense", "")  # the lines are read, not shown
    assert "tabular-nums leading-none" in body and "10,000" in body                               # numbers
    assert body.count("text-6xl leading-[0.6] text-primary/50") == 1 and "What they do" in body  # testimonials
    assert "object-contain opacity-80" in body and "data-drift" in body                # logos, drifting when too many
    assert "Most popular" in body and "US$20" in body and "border-primary" in body     # pricing
    assert "Buy" in body and "US$25" in body and "From" in body                        # products, services
    assert "Their photo" in body and "aspect-square" in body                           # team
    assert "collapse collapse-arrow" in body and _ld(html, "FAQPage")                  # questions
    assert "Ready to start?" in body and "bg-primary text-primary-content" in body              # call to action, a card
    # an unknown kind is a plain section, its line left as written
    assert "Section: Nonsense" in body and "Just words." in body
    # one background throughout - no stripes
    assert "100vmax" not in body
    # one h1
    assert html.count("<h1") == 1


def test_a_sliders_slides_are_named_to_pick_from(admin, client):
    """Every slide captioned: the names above it, the first picked, each
    one a button to its slide; without captions, no names."""
    named = save_post(admin, title="Named slides",
                      body="```gallery slider\n/uploads/a.webp | Notebook, in Silk\n/uploads/b.webp | Photo journal\n```")
    page = client.get(f"/post/{named}").text
    names = page[page.index("data-slider-names"):page.index("gallery-slider relative")]
    assert ">Notebook</button>" in names and ">Photo journal</button>" in names
    assert names.count('data-onclick="showSlide"') == 2 and names.count('aria-pressed="true"') == 1
    # ten named slides keep their names too - the website's "Every kind of page" lost them at nine
    ten = "\n".join(f"/uploads/s{i}.webp | Slide {i}" for i in range(10))
    many = client.get(f"/post/{save_post(admin, title='Ten slides', body=f'```gallery slider\n{ten}\n```')}").text
    assert many.count('data-onclick="showSlide"') == 10
    plain = save_post(admin, title="Plain slides", body="```gallery slider\n/uploads/a.webp\n/uploads/b.webp\n```")
    assert "data-slider-names" not in client.get(f"/post/{plain}").text


def test_sections_take_a_width_and_a_style_on_a_wide_page(admin, client):
    """A section on a wide page: Width: Column, Wide or Full; Style: Card
    sets it apart on a card, Style: Cover (or Section: Hero, which broke
    the page) puts it over its picture across the whole screen. Short
    feature items are centred; framed pictures tilt toward the pointer;
    numbers count up."""
    import io
    from PIL import Image
    from soloblog import images
    buf = io.BytesIO()
    Image.new("RGB", (1200, 800), (60, 90, 120)).save(buf, "PNG")
    pic = images.save_upload(buf.getvalue(), "cover-photo.png")
    body_md = ("A line.\n\n"
               "## Narrow words\n\nSection: Features\nWidth: Column\n\n### One\n\nIcon: leaf\nA line.\n\n"
               "## Carded\n\nSection: Numbers\nStyle: Card\n\n### 12\nthings\n\n"
               f"## Across\n\nSection: Picture and text\nStyle: Cover\n\n![A view]({pic})\n\nOver the picture.\n\n[Look](/look)\n\n"
               f"## A hero\n\nSection: Hero\n\n![A view]({pic})\n\nBig words.\n\n"
               "## Edge to edge\n\nSection: Features\nWidth: Full\n\n### Two\n\nA line.")
    r = client.get(f"/post/{save_post(admin, title='Sized sections', body=body_md, page_width='wide')}")
    assert r.status_code == 200
    body = _body(r.text)
    assert "Width:" not in body and "Style:" not in body
    assert "text-center max-w-sm mx-auto" in body and "mb-4 mx-auto" in body
    assert "card border border-base-content/10 bg-base-content/4 p-6 sm:p-8" in body
    assert body.count("w-screen mx-[calc(50%-50vw)]") == 4 and body.count("sm:min-h-[30rem]") == 2
    assert "Over the picture." in body and "Big words." in body
    assert "data-count-up" in body


def test_a_sections_widths_have_the_same_names_on_every_page(admin, client):
    """Column keeps a Hero in the column; with no Width line it runs across."""
    body_md = ("Intro.\n\n## In the column\n\nSection: Hero\nWidth: Column\n\nBig words.\n\n"
               "## Across\n\nSection: Hero\n\nAcross words.")
    body = _body(client.get(f"/post/{save_post(admin, title='Widths in a post', body=body_md)}").text, "standard")
    assert body.count("w-screen") == 1 and "Width:" not in body


def test_how_sections_appear_is_a_setting(admin, client):
    """Settings > Style > Motion > Sections appear: the page says which
    (input.css [section-reveal]); fading is the default, and nothing is
    said with Animations off."""
    from soloblog import pages, settings
    try:
        page = admin.get("/admin/settings?tab=style").text
        assert "Sections appear" in page and all(f'value="{k}"' in page for k in pages.SECTION_MOTIONS)
        admin.post("/admin/settings/style", headers={"hx-request": "true"},
                   data={"section_motion": "rise", "declared_fields": "section_motion"})
        assert settings.get("section_motion") == "rise" and 'data-reveal="rise"' in client.get("/").text
        admin.post("/admin/settings/style", headers={"hx-request": "true"},
                   data={"section_motion": "spin", "declared_fields": "section_motion"})
        assert settings.get("section_motion") != "spin"
        settings.set_many({"section_motion": "rise", "page_animations": "0"})
        assert "data-reveal" not in client.get("/").text
    finally:
        settings.set_many({"section_motion": "fade", "page_animations": "1"})


def test_section_headings_are_a_setting(admin, client):
    """Settings > Header and footer > Width and spacing > Section headings: on the
    left unless the site says Centred; anything else is left."""
    from soloblog import pages, settings
    try:
        assert settings.DEFAULTS["section_heading_align"] == "left"
        page = admin.get("/admin/settings?tab=header").text
        assert "Section headings" in page and all(f'value="{k}"' in page for k in pages.SECTION_HEADINGS)
        assert "On the left" in page
        for value, saved in (("centre", "centre"), ("left", "left"), ("diagonal", "left"), ("", "left")):
            admin.post("/admin/settings/style", headers={"hx-request": "true"},
                       data={"section_heading_align": value, "declared_fields": "section_heading_align"})
            assert settings.get("section_heading_align") == saved, value
    finally:
        settings.set_many({"section_heading_align": "left"})


def test_gallery_pictures_show_their_captions(admin, client):
    """A gallery's pictures carry their caption, over their foot, as the
    lightbox does; a slider shows it under the picture with the count,
    not over it - and "auto" makes it move along, with a pause button."""
    slug = save_post(admin, title="Captioned", body="```gallery\n/uploads/a.webp | A harbour at dawn\n```\n\n"
                                                  "```gallery slider auto\n/uploads/a.webp | One\n/uploads/b.webp | Two\n```")
    page = client.get(f"/post/{slug}").text
    assert "group-hover:opacity-100 pointer-coarse:opacity-100" in page and ">A harbour at dawn</span>" in page
    assert 'data-title="One"' in page and 'class="slider-caption' in page and ">One</p>" in page
    assert "badge badge-sm absolute bottom-2" not in page and "slider-count text-xs" in page
    assert "data-autoplay" in page and "data-slider-pause" in page and 'aria-label="Pause"' in page
    still = save_post(admin, title="Still slider", body="```gallery slider\n/uploads/a.webp\n/uploads/b.webp\n```")
    assert "data-autoplay" not in client.get(f"/post/{still}").text


def test_a_posts_sections_take_a_style_too(admin, client):
    """Style: Card and Style: Cover work in any post's sections, as on a
    landing page; a gallery's pictures have the framed pictures' edge and
    shadow."""
    body_md = ("Words.\n\n## Carded\n\nSection: Numbers\nStyle: Card\n\n### 3\nthings\n\n"
               "## Covered\n\nSection: Picture and text\nStyle: Cover\n\n![A view](/uploads/a.webp)\n\nOver it.\n\n"
               "## Photos\n\nSection: Gallery\n\n```gallery\n/uploads/a.webp\n```")
    page = client.get(f"/post/{save_post(admin, title='Styled sections', body=body_md)}").text
    assert "Style:" not in page and "card border border-base-content/10 bg-base-content/4 p-6 sm:p-8" in page
    assert 'data-section="hero"' in page and "Over it." in page
    assert "rounded-box hover:opacity-90 border border-base-content/10 shadow-lg" in page


def test_cards_show_their_pictures_unsquashed(admin, client):
    """A card's picture is a photo's 3:2 - a short strip looked squashed -
    with its credit over its corner, not a line under it; steps fit their
    own width, three across only where long ones have room."""
    import io
    from PIL import Image
    from soloblog import images
    buf = io.BytesIO()
    Image.new("RGB", (900, 600), (40, 120, 90)).save(buf, "PNG")
    pic = images.save_upload(buf.getvalue(), "a-project.png")
    images.set_meta(pic.rsplit("/", 1)[1], "A project", "", credit_name="A. Photographer")
    body = _body(client.get(f"/post/{save_post(admin, title='Squash', body=f'## Work\n\nSection: Portfolio\n\n### One\n\n![A project]({pic})\n\nMade.\n\n[See it](/one)')}").text, "portfolio")
    assert "w-full aspect-[4/3] object-cover" in body and "absolute bottom-1.5 end-2" in body and "A. Photographer" in body
    long = "1. " + "A step with a good deal to say about it. " * 4 + "\n2. Two.\n3. Three."
    short = "1. One.\n2. Two.\n3. Three."
    page = client.get(f"/post/{save_post(admin, title='Long steps', body=f'## How\n\nSection: Steps\n\n{long}')}").text
    assert "@3xl:grid-cols-3" in page and "@container" in page
    page = client.get(f"/post/{save_post(admin, title='Short steps', body=f'## How\n\nSection: Steps\n\n{short}')}").text
    assert "@xl:grid-cols-3" in page


def test_privacy_and_terms_templates_start_as_footer_pages(admin):
    # a site that collects emails needs a privacy policy - there was no
    # template to start one from, though cookie consent asks for its page
    from soloblog import post_templates, settings
    names = {c[0]: c[1] for c in post_templates.choices()}
    assert names["privacy"] == "Privacy policy" and names["terms"] == "Terms"
    for key in ("privacy", "terms"):
        page = admin.get(f"/admin/new?template={key}").text
        footer = page[page.index('value="footer"') - 80:page.index('value="footer"') + 40]
        assert "selected" in footer, key
        assert "[your name]" in page.lower() and "delete this line" in page
    # any other template is still a post in the blog roll
    page = admin.get("/admin/new?template=recipe").text
    assert "selected" not in page[page.index('value="footer"') - 80:page.index('value="footer"') + 40]
    # Cookie consent's Privacy page offers the template while it's empty
    kept = settings.get("consent_privacy_url")
    try:
        settings.set_many({"consent_privacy_url": ""})
        assert "/admin/new?template=privacy" in admin.get("/admin/settings?tab=analytics").text
        settings.set_many({"consent_privacy_url": "/post/privacy"})
        assert "/admin/new?template=privacy" not in admin.get("/admin/settings?tab=analytics").text
    finally:
        settings.set_many({"consent_privacy_url": kept})


def test_a_features_item_can_name_a_line_icon(admin, client):
    """"Icon: palette" under an item draws that line icon in a tile; an
    emoji first in the heading still works; a name it doesn't know stays
    in view, so the slip shows."""
    body_md = ("## Why\n\nSection: Features\n\n### Your look\n\nIcon: palette\nColours and fonts.\n\n"
               "### Bread\n\nA line.\n\n### 🍞 Real bread\n\nAnother.\n\n### Typo\n\nIcon: palete\nOops.")
    body = client.get(f"/post/{save_post(admin, title='Icons', body=body_md)}").text
    assert "size-11 rounded-box bg-primary/10" in body and "Icon: palette" not in body
    assert "🍞" in body and "Icon: palete" in body


def _picture(name, size=(900, 600)):
    import io
    from PIL import Image
    from soloblog import images
    buf = io.BytesIO()
    Image.new("RGB", size, (60, 90, 140)).save(buf, "PNG")
    return images.save_upload(buf.getvalue(), f"{name}.png")


def test_a_portfolio_in_each_arrangement(admin, client):
    """Grid, Masonry, Rows, Full screen and Sideways - the site's choice,
    or the page's own "Show as:" line; a piece with no link opens bigger."""
    from soloblog import pages, settings
    a, b = _picture("work-a"), _picture("work-b", (600, 900))
    work = f"### One\n\n![First]({a})\n\nMade.\n\n[See it](/one)\n\n### Two\n\n![Second]({b})\n\nAlso made."
    body = "## Work\n\nSection: Portfolio\n\nA line about the work.\n\n" + work
    slug = save_post(admin, title="Work", body=body)
    before = settings.get("portfolio_style")
    try:
        # in a post's column, its columns follow the column's width (_FIT)
        marks = {"grid": "aspect-[4/3]", "masonry": "columns-1 @lg:columns-2", "rows": "flex: 0.667 1",
                 "screen": "min-h-[calc(100svh-var(--header-h,0px))]", "sideways": "carousel-item"}
        for style, mark in marks.items():
            settings.set_many({"portfolio_style": style})
            page = _body(client.get(f"/post/{slug}").text, "portfolio")
            assert f'data-portfolio="{style}"' in page and mark in page, style
        assert "slideGallery" in page
        # the page's own line wins, and isn't shown as words
        slug2 = save_post(admin, title="Rows of work", body="## Work\n\nSection: Portfolio\nShow as: Rows\n\n" + work)
        page = _body(client.get(f"/post/{slug2}").text, "portfolio")
        assert 'data-portfolio="rows"' in page and "Show as" not in page
    finally:
        settings.set_many({"portfolio_style": before})
    page = _body(client.get(f"/post/{slug}").text, "portfolio")
    assert 'href="/one"' in page and 'data-lightbox="portfolio"' in page
    # the first pictures load straight away, as anyone sees them first
    work = page.split('data-section="portfolio"')[1]
    assert 'loading="lazy"' not in work.split("Two")[0].split("<img")[1]
    # a setting from outside is one of the choices, or refused
    for value in ("masonry", "spiral"):
        admin.post("/admin/settings/style", data={"declared_fields": "portfolio_style", "portfolio_style": value},
                   headers={"hx-request": "true"})
        assert settings.get("portfolio_style") in pages.PORTFOLIO_STYLES, value
    assert settings.get("portfolio_style") == "grid"
    settings.set_many({"portfolio_style": before})


def test_a_portfolio_shows_tagged_work(admin, client):
    """"Tag: work" brings in every post and page with that tag, by its cover."""
    cover = _picture("cafe-cover")
    first = save_post(admin, title="Café site", body="Client: A café\n\nThe story.", tags="work",
                      cover_image=cover)
    save_post(admin, title="Bakery site", body="Client: A bakery\n\nThe story.", tags="work")
    save_post(admin, title="Not work", body="Hi.", tags="life")
    folio = save_post(admin, title="Selected work", body="## Work\n\nSection: Portfolio\nTag: work\n\nWhat I make.")
    page = _body(client.get(f"/post/{folio}").text, "portfolio")
    assert "Café site" in page and "Bakery site" in page and "Not work" not in page and "Tag:" not in page
    assert f'href="/post/{first}"' in page


def _project(admin, title, tags="", **extra):
    """A page that ends with Previous and next."""
    from soloblog import sections
    return save_post(admin, title=title, body=f"The story.\n\n{sections.markdown('previous_next')}", tags=tags,
                     **extra)


def test_previous_and_next_lead_to_the_pages_with_the_same_first_tag(admin, client):
    """Pages sharing a first tag lead on to each other, newest first and
    round from the last; a Portfolio section on some other page has no say
    - it's a part of its own page only."""
    first = _project(admin, "Café site", tags="clients, web")
    second = _project(admin, "Bakery site", tags="clients")
    html = client.get(f"/post/{first}").text
    assert ">Next<" in html and f'href="/post/{second}"' in html
    # only two: the other is the next, not the previous as well
    assert ">Previous<" not in html
    # a tag that isn't its first leads nowhere, and the section isn't drawn
    other = _project(admin, "Side thing", tags="web")
    assert ">Next<" not in client.get(f"/post/{other}").text
    assert "Keep reading" not in client.get(f"/post/{other}").text
    # nor does a Portfolio elsewhere that shows it
    save_post(admin, title="Everything", body=f"## All\n\nSection: Portfolio\n\n### Café\n\n[See it](/post/{first})"
                                               f"\n\n### Side\n\n[See it](/post/{other})")
    assert ">Next<" not in client.get(f"/post/{other}").text
    lone = _project(admin, "Alone")
    assert ">Next<" not in client.get(f"/post/{lone}").text


def test_previous_and_next_lead_back_too(admin, client):
    # three with one tag: the middle one has both, the first goes round to the last
    slugs = [_project(admin, f"Piece {n}", tags="pieces") for n in (1, 2, 3)]
    html = client.get(f"/post/{slugs[1]}").text
    tail = html[html.index(">Previous<"):]
    assert ">Next<" in tail
    # each card links somewhere else, never to itself
    links = {s for s in slugs if f'href="/post/{s}"' in tail}
    assert slugs[1] not in links and len(links) == 2
    first = client.get(f"/post/{slugs[0]}").text
    assert ">Previous<" in first and ">Next<" in first


def test_a_section_keeps_the_pages_own_title(admin, client):
    """A section never takes over the page's title - only a photo story
    opens big."""
    body_md = "Intro.\n\n## Kind words\n\nSection: Testimonials\n\nWhat they say.\n\n### Sam\n\n> Lovely."
    page = client.get(f"/post/{save_post(admin, title='With a section', body=body_md)}").text
    assert "text-4xl sm:text-6xl font-extrabold" not in page and "max-w-2xl mx-auto text-center" not in page


def test_a_portfolio_section_in_a_folding_post_zooms_one_picture_at_a_time(admin, client):
    """A folding heading's box is a hover group of its own name - unnamed,
    every picture in a Portfolio section (and every gallery caption)
    answered to it and zoomed at once. Inside a section the intro is the
    section's size, not a Portfolio page's big opening."""
    from soloblog import settings
    before = settings.get("heading_fold")
    settings.set_many({"heading_fold": "open"})
    try:
        pic = _picture("fold-piece")
        body_md = (f"Intro.\n\n## Plain part\n\nWords.\n\n## Recent work\n\nSection: Portfolio\n\nA line about it.\n\n"
                   f"### One\n\n![One]({pic})\n\n[See it](/one)\n\n### Two\n\n![Two]({pic})\n\n[See it](/two)")
        page = client.get(f"/post/{save_post(admin, title='Folding work', body=body_md)}").text
        assert '<details class="group/fold' in page and '<details class="group ' not in page
        # the plain part folds; the section never does
        assert "data-section" not in page.split('<details class="group/fold')[1].split("</details>")[0]
        assert page.count('class="group reveal-item"') == 2 and "group-hover:scale-[1.03]" in page
        assert "sm:prose-xl" not in page.split('data-section="portfolio"')[1].split("</section>")[0][:3000]
    finally:
        settings.set_many({"heading_fold": before})


def test_space_between_sections_for_the_site_and_for_one_page(admin, client):
    # Medium is the gaps as written; Small and Large scale every one of them,
    # and a page's own choice wins over the site's
    from soloblog import posts, settings
    body = "Words.\n\n## Plans\n\nSection: Numbers\n\n### 3\nthings\n"
    slug = save_post(admin, title="Spaced", body=body)
    # the form resets what it isn't sent - everything goes back after
    before = settings.get_all()
    try:
        page = client.get(f"/post/{slug}").text
        assert "[--space:" not in page and "calc(1.5rem*var(--space,1))" in page
        r = admin.post("/admin/settings/style", headers={"hx-request": "true"},
                       data={"section_space": "large"})
        assert r.status_code == 200 and settings.get("section_space") == "large"
        assert "[--space:1.5]" in client.get(f"/post/{slug}").text
        save_post(admin, slug=slug, title="Spaced", body=body, section_space="small")
        assert posts.get_post(slug)["section_space"] == "small"
        assert "spacing: small" in Path(posts._path(slug)).read_text(encoding="utf-8")
        assert "[--space:0.5]" in client.get(f"/post/{slug}").text
        # something it doesn't know is the site's
        save_post(admin, slug=slug, title="Spaced", body=body, section_space="huge")
        assert posts.get_post(slug)["section_space"] == ""
        assert "[--space:1.5]" in client.get(f"/post/{slug}").text
    finally:
        settings.set_many(before)


GAP_VALUES = {"small": ("2rem", "3rem"), "medium": ("5rem", "9rem"), "large": ("9rem", "18rem")}


def test_the_room_between_sections_is_one_variable_per_spacing(admin, client):
    # small, medium and large are 0.5, 1.5 and 3 inches on a wide screen (a
    # phone's smaller), held in --section-gap on the page and on a section
    from soloblog import pages, settings
    for key, (phone, wide) in GAP_VALUES.items():
        assert pages.SECTION_GAPS[key] == f"[--section-gap:{phone}] sm:[--section-gap:{wide}]"
        assert pages.SECTION_GAPS[key] in pages.SPACE_SCALE[key] and pages.SECTION_GAPS[key] in pages.SECTION_ROOM[key]
    body = "Words.\n\n## Plans\n\nSection: Numbers\n\n### 3\nthings\n\n## Cost\n\nSection: Numbers\nSpace: Large\n\n### 4\nmore\n"
    slug = save_post(admin, title="Roomy", body=body)
    before = settings.get_all()
    try:
        for key in GAP_VALUES:
            settings.set_many({"section_space": key})
            page = _body(client.get(f"/post/{slug}").text)
            # the site's, on the page; each section's heading carries the gap above it
            assert pages.SECTION_GAPS[key] in client.get(f"/post/{slug}").text
            assert page.count("mt-(--section-gap)") >= 2
        settings.set_many({"section_space": "small"})
        html = client.get(f"/post/{slug}").text
        # a section's own Space: its own value, in its heading too
        assert pages.SECTION_GAPS["large"] in html
        save_post(admin, slug=slug, title="Roomy", body=body, section_space="medium")
        assert pages.SECTION_GAPS["medium"] in client.get(f"/post/{slug}").text
    finally:
        settings.set_many(before)


def test_business_profile_coming_soon_guess_nothing(admin, client):
    # a Phone: line or day/time lines without their section are just writing
    plain = "We fix things.\n\nPhone: 02 9000 0000\n\n## Hours\n\nMonday: 9am - 5pm\nTuesday: 9am - 5pm"
    html = client.get(f"/post/{save_post(admin, title='Plain shop', body=plain)}").text
    body = _body(html)
    assert 'href="tel:' not in body and "table table-sm" not in body
    assert _ld(html, "LocalBusiness") is None
    # nothing added by itself: no latest posts on a profile, no sign-up on coming soon
    save_post(admin, title="A post a profile mustn't list by itself")
    body = _body(client.get(f"/post/{save_post(admin, title='Just me', body='Hello.')}").text)
    assert 'data-section="latest"' not in body
    body = _body(client.get(f"/post/{save_post(admin, title='Soon', body='Soon.')}").text)
    assert "newsletter/subscribe" not in body


def test_a_call_to_action_can_have_a_heading_of_its_own(admin, client):
    """A ### first in a Call to action section is the card's own big
    heading; without one the card is a line and a button, as before."""
    body = ("Intro.\n\n## Join in\n\nSection: Call to action\n\n### Bring a friend\n\nA line.\n\n"
            "[Come along](/contact)\n\n## Plain\n\nSection: Call to action\n\nJust a line.\n\n[Go](/contact)")
    page = client.get(f"/post/{save_post(admin, title='Card heading', body=body)}").text
    cards = page.split('data-section="cta"')[1:]
    assert ">Bring a friend</h3>" in cards[0].split("</a>")[0] and "font-extrabold" in cards[0]
    assert "<h3" not in cards[1].split("</a>")[0] and ">Just a line.</p>" in cards[1]


def test_a_buttons_line_in_a_call_to_action_or_hero_gives_its_buttons_once(admin, client):
    """A Buttons line in a Call to action or a Hero is the card's buttons -
    the first the main one, the rest beside it - not a row in the text
    with its last link repeated as the card's button."""
    buttons = "Buttons: [Get started](/get-started) [Try the demo](https://demo.example.org)"
    body = (f"Intro.\n\n## Try it\n\nSection: Call to action\n\nA line.\n\n{buttons}\n\n"
            f"## Big\n\nSection: Hero\n\nA line.\n\n{buttons}")
    page = client.get(f"/post/{save_post(admin, title='Two buttons', body=body)}").text
    cta = page.split('data-section="cta"')[1].split('data-section=')[0]
    hero = page.split('data-section="hero"')[1].split("</section>")[0]
    from soloblog.pages import BTN_ON_PRIMARY
    for card, main, quiet in ((cta, "btn", BTN_ON_PRIMARY), (hero, "btn btn-primary", "btn btn-outline")):
        assert card.count(">Try the demo</a>") == 1 and card.count(">Get started</a>") == 1
        assert f'<a href="/get-started" class="{main}">' in card
        assert f'<a href="https://demo.example.org" class="{quiet}">' in card
        assert "not-prose flex flex-wrap" not in card
    # one link is still the one button, as before
    page = client.get(f"/post/{save_post(admin, title='One button', body='Intro.\n\n## Go\n\n'
                                         'Section: Call to action\n\nA line.\n\n[Come along](/contact)')}").text
    assert page.split('data-section="cta"')[1].count('class="btn"') == 1


def test_a_portfolio_piece_on_another_site_says_so_with_an_arrow(admin, client):
    # its title ends in ↗ and it opens in a new tab - no extra Visit line;
    # a piece on this site is as it was
    body = ("Intro.\n\n## Work\n\nSection: Portfolio\n\n### Away\n\nA site of mine.\n\n[Visit](https://example.org)\n\n"
            "### Home\n\nOne of my pages.\n\n[See it](/about)")
    page = client.get(f"/post/{save_post(admin, title='Away and home', body=body)}").text
    assert re.search(r'<a href="https://example.org" target="_blank" rel="noopener" class="link link-hover">Away '
                     r'<span aria-hidden="true">↗</span></a>', page)
    assert re.search(r'<a href="/about" class="link link-hover">Home</a>', page)
    assert ">Visit <span" not in page and "Visit</a>" not in page


def test_a_numbers_last_row_is_centred(admin, client):
    # five numbers were three and then two at the left; a wrapping row,
    # centred, puts the two in the middle (checked at 1280 and 375 px)
    body = "Intro.\n\n## In numbers\n\nSection: Numbers\n\n" + "".join(f"### {n}\n\nThings\n\n" for n in range(1, 6))
    page = client.get(f"/post/{save_post(admin, title='Five numbers', body=body)}").text
    part = page.split('data-section="numbers"')[1][:3000]
    assert "flex flex-wrap justify-center" in part and "grid-cols" not in part
    assert part.count("w-[calc(50%-0.75rem)] sm:w-[calc(33.333%-1rem)]") == 5


def test_a_wider_sections_heading_goes_with_it(admin, client):
    """On a wide page a section runs wider than the column - its heading
    with it, lined up with its words, not left behind in the column."""
    body_md = ("Intro.\n\n## Wide numbers\n\nSection: Numbers\n\n### 3\nthings\n\n"
               "## In the column\n\nSection: Numbers\nWidth: Column\n\n### 4\nmore")
    slug = save_post(admin, title="Wide headings", body=body_md, page_width="wide")
    page = client.get(f"/post/{slug}").text
    heading = re.search(r'<h2[^>]*id="wide-numbers"', page).start()
    assert page.index("w-screen") < heading < page.index('data-section="numbers"')
    # one in the column keeps its heading where it was, outside any breakout
    column = re.search(r'<h2[^>]*id="in-the-column"', page).start()
    assert page.count("w-screen") == 1 and column > page.index('data-section="numbers"')


def test_built_in_pages_space_their_parts_by_the_page(admin, client):
    """The wiki, Archive, Tags, a tag, Search and Links: their parts one
    group, as far apart as Space says - not a fixed mb-6 or mt-4 that
    stayed the same whatever it was set to."""
    from bs4 import BeautifulSoup
    from soloblog import pages, settings
    before = {k: settings.get(k) for k in ("links_enabled", "links_items", "links_show_posts", "author_name")}
    try:
        settings.set_many({"links_enabled": "1", "links_items": "Shop|https://example.com", "links_show_posts": "1",
                           "author_name": "Sam"})
        slug = save_post(admin, title="Spaced note", tags="spaced", body="Words.")
        posts.write(slug, in_wiki=True, pinned=True)
        for path in ("/wiki", "/archive", "/tags", "/tag/spaced", "/search?q=spaced", "/search", "/links"):
            main = BeautifulSoup(client.get(path).text, "html.parser").find("main")
            group = main.find(class_=lambda c: c and set(pages.PARTS.split()) <= set(c.split()))
            assert group, path
            parts = group.find_all(recursive=False)
            assert len(parts) >= 2, path
            for part in parts:
                fixed = [c for c in part.get("class", []) if re.match(r"(sm:)?m[tby]-", c)]
                assert not fixed, (path, fixed)
        # the wiki's two lists side by side are as far apart as the rest
        wiki = BeautifulSoup(client.get("/wiki").text, "html.parser").find("main")
        assert not wiki.find(class_=lambda c: c and re.search(r"\bmb-6\b", c))
    finally:
        settings.set_many(before)


def test_the_last_section_has_room_under_it(admin, client):
    """The room is above each section; the last one on a page got none
    under it, so comments or the footer sat right against it. It gets
    the same room below - and a section with writing after it doesn't."""
    from soloblog import pages, sections
    from bs4 import BeautifulSoup

    def marked(body):
        soup = BeautifulSoup(client.get(f"/post/{save_post(admin, title='Room under', body=body)}").text,
                             "html.parser")
        return soup.select("[data-section]"), soup.find_all(
            class_=lambda c: c and set(pages.SECTION_LAST.split()) <= set(c.split()))

    for key in ("faq", "hero", "team", "numbers"):
        # in the column, wide or full, drawing its own heading or not
        for width in ("Default", "Full", "Column"):
            body = ("Opening words.\n\n" + sections.markdown("cta") + "\n\n"
                    + sections.markdown(key).replace("Width: Default", f"Width: {width}", 1))
            drawn, last = marked(body)
            assert drawn and len(last) == 1, (key, width)
            assert last[0] is drawn[-1] or drawn[-1] in last[0].descendants, (key, width)
    drawn, last = marked(sections.markdown("faq") + "\n\n## After\n\nWriting after it.")
    assert drawn and not last


def test_only_plain_writing_folds(admin, client):
    """One rule to guess: with Fold headings on, plain writing under a ##
    folds and a section never does, whatever its kind or width - before,
    a section in the column folded and a wide one didn't."""
    from bs4 import BeautifulSoup
    from soloblog import sections, settings
    before = settings.get("heading_fold")
    settings.set_many({"heading_fold": "open"})
    try:
        for key in sections.REGISTRY:
            for width in ("Column", "Default", "Full"):
                body = ("## Plain one\n\nWords.\n\n"
                        + sections.markdown(key).replace("Width: Default", f"Width: {width}", 1)
                        + "\n\n## Plain two\n\nMore words.")
                soup = BeautifulSoup(client.get(f"/post/{save_post(admin, title='Folds', body=body)}").text,
                                     "html.parser")
                folds = soup.find_all("details", class_="group/fold")
                assert [d.summary.get_text(strip=True) for d in folds] == ["Plain one", "Plain two"], (key, width)
                assert not any(d.find(attrs={"data-section": True}) for d in folds), (key, width)
    finally:
        settings.set_many({"heading_fold": before})


def test_after_a_last_section_the_end_of_the_post_adds_no_gap_of_its_own(admin, client):
    # the section's room below and the end group's PART_GAP made two gaps
    from bs4 import BeautifulSoup
    from soloblog import pages, sections

    def end_group(body):
        slug = save_post(admin, title="One gap", body=body, comments_enabled="1")
        soup = BeautifulSoup(client.get(f"/post/{slug}").text, "html.parser")
        return set(soup.find(id="comments").find_parent(class_="flex-col")["class"])

    assert not set(pages.PART_GAP.split()) & end_group("Words.\n\n" + sections.markdown("cta"))
    assert set(pages.PART_GAP.split()) <= end_group("Words only.")
    assert set(pages.PART_GAP.split()) <= end_group(sections.markdown("cta") + "\n\n## Plain\n\nWords after it.")


def test_a_short_list_reads_as_one_block(admin, client):
    # 4px between plain list items, not the text styling's 12px - in the
    # post and in the editor's preview alike
    from soloblog import pages
    from soloblog.routes import editor
    slug = save_post(admin, title="A list", body="Buy:\n\n- eggs\n- flour\n- butter")
    html = client.get(f"/post/{slug}").text
    assert pages.LIST_GAP in html and "<li>eggs</li>" in html
    assert f'"{pages.LIST_GAP}"' in editor.EDITOR_INIT_JS
