"""Sections - a ## with a "Section:" line (Pricing, Testimonials...) - in
any post or page, not only a Landing page (pages.place_sections)."""
from pathlib import Path
import os
import re

import pytest
from conftest import save_post

PRICING = """Some words first.

## Plans

Section: Pricing

### Basic

Price: US$10 a month

- Every post

[Choose Basic](/join)

### Pro

Price: US$20 a month
Badge: Most popular

- Everything

[Choose Pro](/join)

## After the plans

More words.
"""


def test_a_section_in_a_standard_post_stays_where_it_was_written(admin, client):
    slug = save_post(admin, title="Sections in a post", body=PRICING)
    page = client.get(f"/post/{slug}").text
    # its cards, in place: after the words before it, before the next heading
    assert 'data-section="pricing"' in page and "Most popular" in page and "US$20" in page
    assert page.index("Some words first") < page.index('data-section="pricing"') < page.index('id="after-the-plans"')
    # the line saying what kind it is never shows as words
    assert "Section: Pricing" not in page
    # its heading is the post's own: a real heading, with its id
    assert 'id="plans"' in page
    # its cards follow the column's width, not the screen's
    assert "@lg:grid-cols-2" in page and "@container" in page


def test_a_misspelt_kind_stays_text(admin, client):
    slug = save_post(admin, title="A typo", body="## Plans\n\nSection: Pricnig\n\n### Basic\n\nPrice: $1\n")
    page = client.get(f"/post/{slug}").text
    assert "Section: Pricnig" in page and "data-section=" not in page


def test_a_section_stays_where_it_was_written_among_plain_headings(admin, client):
    # a resume's plain ##s are plain writing: a section sits between them, where it was put
    body = ("## Experience\n\n### Baker, Corner Café · 2020 – 2024\nBread.\n\n## Kind words\n\nSection: Testimonials\n\n"
            "### Sam\n\nRole: Baker\n\n> Lovely.\n\n## Education\n\n### Bakery school · 2019\nFlour.\n")
    slug = save_post(admin, title="A resume with a section", body=body)
    page = client.get(f"/post/{slug}").text
    assert page.rindex("Baker, Corner") < page.index('data-section="testimonials"') < page.rindex("Bakery school")
    assert "Lovely." in page


def test_no_section_lines_no_change(admin, client):
    slug = save_post(admin, title="Plain", body="## A heading\n\nWords.\n")
    page = client.get(f"/post/{slug}").text
    assert "data-section=" not in page and "Words." in page


def test_section_lines_never_reach_a_reader_as_words(admin, client):
    # the line is for the page: not in its description, a feed, an email
    from soloblog import newsletter, posts, settings
    from soloblog.render import excerpt, render_post
    slug = save_post(admin, title="Lines kept out", body=PRICING)
    html, _ = render_post(PRICING)
    assert "Section: Pricing" not in excerpt(html)
    assert "Section: Pricing" not in client.get(f"/post/{slug}").text
    assert "Section: Pricing" not in client.get("/rss").text
    kept = settings.get("newsletter_full")
    try:
        settings.set_many({"newsletter_full": "1"})
        email = newsletter.post_email(posts.get_post(slug), settings.get_all(), "token")
        assert "Section: Pricing" not in email and "Price: US$10 a month" in email
    finally:
        settings.set_many({"newsletter_full": kept})
    # someone's own "Section: 3" paragraph is their words, and stays
    assert "Section: 3" in excerpt(render_post("Section: 3\n")[0])


def test_a_translation_keeps_each_section_line_after_its_heading():
    # translated, "Section: Pricing" would read "Sección: Precios" - which
    # names no kind, so the page would lose its cards
    from soloblog import translate
    from soloblog.render import render_post
    html, _ = render_post(PRICING + "\n## Quotes\n\nSection: Testimonials\n\n### Sam\n\n> Hi\n")
    held_html, held = translate._hold_section_lines(html)
    assert "Section:" not in held_html and len(held) == 2
    # as a translation service might return it
    spanish = held_html.replace("Plans", "Planes").replace("Quotes", "Citas")
    back = translate._restore_section_lines(spanish, held)
    assert back.index("Planes") < back.index("Section: Pricing") < back.index("Basic")
    assert back.index("Citas") < back.index("Section: Testimonials")


NOTHING_ALONE = {"contents", "previous_next"}


def test_every_section_renders_in_a_post_and_is_in_the_guide(admin, client):
    # what Insert > Sections adds, all in one ordinary post: each drawn,
    # none of their lines shown - and each in the user guide's table
    import os
    from soloblog import sections
    snippets = [sections.markdown(key) for key in sections.REGISTRY]
    slug = save_post(admin, title="Every one", body="\n\n".join(snippets))
    page = client.get(f"/post/{slug}").text
    lines = [next(s for s in snippet.split("\n") if s.startswith("Section: ")) for snippet in snippets]
    kinds = {sections.NAMES[line[9:].lower()] for line in lines}
    assert kinds == set(sections.REGISTRY)
    for kind in kinds - NOTHING_ALONE:
        assert f'data-section="{kind}"' in page, kind
    # a series' contents and a page's neighbours show nothing to a reader on a page with neither
    assert not NOTHING_ALONE & set(re.findall(r'data-section="([a-z_]+)"', page))
    # none of the lines Insert writes shows - the option lines (Width: Default...) included
    main = page.split("<main")[1]
    assert "Section:" not in main and ": Default" not in main
    # each has its own entry, headed with the line Insert writes
    guide = Path(os.path.join(os.path.dirname(__file__), "..", "docs", "guide", "sections-templates.md")).read_text()
    for kind, line in zip(sections.REGISTRY, lines):
        assert f"\n### {line}\n" in guide, line
        # and says every other name it can be written under, and every Key: line it reads
        entry = guide.split(f"\n### {line}\n")[1].split("\n### ")[0].split("\n## ")[0]
        for name in sections.REGISTRY[kind]["names"][1:]:
            assert f"`Section: {name}`" in entry, (line, name)
        for name in sections.REGISTRY[kind]["options"]:
            assert f"`{name}:" in entry, (line, name)


def test_the_new_sections_and_blocks(admin, client):
    # Features (a grid now - Picture and text is the band), Columns,
    # Sign-up, Contact form, Latest posts and Compare; and the blocks
    # written as a line: Buttons, Pull quote, Countdown, and a fold
    from soloblog import sections, settings
    snippets = {key: sections.markdown(key) for key in sections.REGISTRY}
    save_post(admin, title="An older one to list", body="Words.", tags="baking")
    kept = {k: settings.get(k) for k in ("contact_enabled", "newsletter_mode", "email_provider")}
    try:
        settings.set_many({"contact_enabled": "1", "newsletter_mode": "builtin", "email_provider": "smtp"})
        body = "\n\n".join(snippets[k] for k in ("features", "columns", "signup", "contact", "latest", "compare"))
        body += ("\n\n## Some writing\n\nButtons: [Join](/join) [Read more](/about)\n\n"
                 "Pull quote: A line worth repeating.\n\nCountdown: 12 March 2099\n\n"
                 '??? "A heading"\n    The text it opens to.\n')
        slug = save_post(admin, title="The new ones", body=body)
        page = client.get(f"/post/{slug}").text
        for kind in ("features", "columns", "signup", "contact", "latest", "compare"):
            assert f'data-section="{kind}"' in page, kind
        assert "size-11 rounded-box bg-primary/10" in page and "Real bread" in page  # features, a line icon
        assert 'id="contact-form"' in page and 'name="email"' in page     # contact, sign-up
        assert "An older one to list" in page and "The new ones" not in page.split('data-section="latest"')[1][:3000]
        assert '<span class="sr-only">Yes</span>' in page and '<span class="sr-only">No</span>' in page  # compare
        assert 'class="btn btn-primary">Join</a>' in page and 'class="btn">Read more</a>' in page        # buttons
        assert "border-s-4 border-primary" in page and "A line worth repeating." in page               # pull quote
        assert 'data-countdown="2099-03-12"' in page and "days to go" in page                          # countdown
        assert "<details" in page and "<summary>A heading</summary>" in page                            # fold
        for line in ("Section:", "Buttons:", "Pull quote:", "Countdown:"):
            assert line not in page.split("<main")[1], line
        # off, a sign-up or contact section is just its words
        settings.set_many({"contact_enabled": "0", "newsletter_mode": ""})
        page = client.get(f"/post/{slug}").text
        assert 'id="contact-form"' not in page and "A line about what to write about." in page
    finally:
        settings.set_many(kept)


def test_a_countdown_counts_and_a_date_it_cant_read_stays_text():
    from soloblog.render import render_post
    assert "data-countdown" not in render_post("Countdown: someday soon\n")[0]
    assert "Countdown: someday soon" in render_post("Countdown: someday soon\n")[0]
    assert 'data-countdown="2099-03-12"' in render_post("Countdown: 2099-03-12\n")[0]
    # a date gone by: the date, and no count
    html = render_post("Countdown: 1 January 2001\n")[0]
    assert "data-countdown-left></span>" in html


def test_contact_details_wrap_on_a_phone(admin, client):
    # a long address ran off a 320 px screen: a button never wraps its words
    body = "## Find us\n\nSection: Contact details\n\nEmail: someone@example.com\nAddress: A very long street name, a town\n"
    slug = save_post(admin, title="Find us", body=body)
    page = client.get(f"/post/{slug}").text
    assert 'data-section="details"' in page and "whitespace-normal" in page and "mailto:someone@example.com" in page


def test_hero_and_bento_and_a_sections_width(admin, client):
    # a Hero's heading is inside its picture, and the page's folds treat it
    # as a part of its own; a Bento grid's first tile is big; Width: takes
    # any section wider than the column - or keeps one in it
    from soloblog import settings
    body = ("Intro.\n\n## Before\n\nWords.\n\n## Fix it\n\nSection: Hero\n\n![A bench](/uploads/a.webp)\n\n"
            "A line.\n\n[Come along](/join)\n\n## Tiles\n\nSection: Bento grid\n\n### Big one\n\nA line.\n\n"
            "### Small\n\nA line.\n\n## Plans\n\nSection: Numbers\nWidth: Full\n\n### 3\nthings\n\n"
            "## Kept in\n\nSection: Hero\nWidth: Column\n\nJust words.\n")
    kept = settings.get("heading_fold")
    try:
        settings.set_many({"heading_fold": "open"})
        slug = save_post(admin, title="Wide ones", body=body)
        page = client.get(f"/post/{slug}").text
        hero = page[page.index('data-section="hero"'):]
        hero = hero[:hero.index("data-section=\"bento\"")]
        assert 'id="fix-it"' in hero and "Come along" in hero and "from-black/85" in hero and "text-white/90" in hero
        # not inside the fold of the heading before it
        before = page[page.index('id="before"'):page.index('data-section="hero"')]
        assert "</details>" in before  # the fold before it ends before it
        # wide by default, full, and kept in the column when it says so
        assert page.count("w-screen mx-[calc(50%-50vw)]") == 3
        assert '@lg:col-span-2 @lg:row-span-2' in page and 'data-section="bento"' in page
        assert "Width:" not in page.split("<main")[1]
    finally:
        settings.set_many({"heading_fold": kept})


# What people could write after "Section:" before the registry (pages.SECTION_KINDS):
# pinned, so a name never changes the kind it means - pages in the wild use them
OLD_NAMES = {"features": "features", "picture and text": "picture_and_text", "picture": "picture_and_text",
             "columns": "columns", "sign-up": "signup", "signup": "signup", "newsletter": "signup",
             "contact form": "contact", "contact": "contact", "latest posts": "latest", "posts": "latest",
             "compare": "compare", "comparison": "compare",
             "steps": "steps", "how it works": "steps", "milestones": "milestones", "timeline": "milestones",
             "events": "events", "talks": "events", "menu": "menu", "projects": "portfolio",
             "portfolio": "portfolio", "reviews": "reviews", "books": "reviews", "uses": "uses",
             "opening hours": "hours", "hours": "hours", "contact details": "details",
             "hero": "hero", "bento": "bento", "bento grid": "bento",
             "testimonials": "testimonials", "pricing": "pricing", "plans": "pricing",
             "faq": "faq", "questions": "faq", "products": "products", "shop": "products", "services": "services",
             "team": "team", "people": "team", "photo gallery": "gallery",
             "numbers": "numbers", "stats": "numbers", "logos": "logos",
             "call to action": "cta", "cta": "cta",
             "resume": "resume", "cv": "resume", "skills": "skills", "profile": "profile", "bios": "bios",
             "media kit": "bios", "project facts": "project_facts", "photo story": "photo_story"}


NEW_NAMES = {"recipe facts": "recipe_facts", "ingredients": "ingredients", "method": "method",
             "instructions": "method", "directions": "method", "interview": "interview",
             "contents": "contents", "parts": "contents", "previous and next": "previous_next",
             "story": "story", "scroll story": "story"}


def test_the_registry_is_complete_and_keeps_every_name():
    from soloblog import editor_icons, pages, sections
    assert sections.NAMES == {**OLD_NAMES, **NEW_NAMES}
    # no two kinds claim one name
    assert sum(len(e["names"]) for e in sections.REGISTRY.values()) == len(sections.NAMES)
    assert len(sections.REGISTRY) == 41
    for key, entry in sections.REGISTRY.items():
        assert entry["label"] == entry["names"][0] and entry["about"] and entry["heading"], key
        assert entry["icon"] in editor_icons.ICONS, key
        # Width, Style and Heading first, then its own - each one defined
        names = sections.option_names(key)
        assert names[:3] == ("Width", "Style", "Heading") and all(n in sections.OPTIONS for n in names), key
        assert entry["width"] in ("", "wide", "full"), key
        # every kind is drawn by its own function in pages.py - one path, no kind drawn inline
        assert callable(getattr(pages, entry["draw"])), key
    assert sections.REGISTRY["latest"]["options"].keys() == {"Count", "Tag"}
    assert sections.REGISTRY["portfolio"]["options"].keys() == {"Show as", "Tag"}
    assert sections.REGISTRY["hero"]["width"] == "full" and sections.REGISTRY["bento"]["width"] == "wide"
    # every option says what it is and what Default does, and its values have an icon
    for name, option in sections.OPTIONS.items():
        assert option["about"] and option["default"], name
        for _, label, about, icon in (sections.values(name) if option["type"] == "choice" else ()):
            assert label and about and icon in editor_icons.ICONS, (name, label)


def test_the_markdown_that_adds_a_section_writes_every_option_as_default():
    from soloblog import sections
    assert sections.markdown("latest") == (
        "## Lately\n\nSection: Latest posts\nWidth: Default\nStyle: Default\nHeading: Default\nSpace: Default\n"
        "Appear: Default\nCount: Default\nTag: Default")
    for key, entry in sections.REGISTRY.items():
        text = sections.markdown(key)
        lines = text.split("\n")
        assert lines[0] == f"## {entry['heading']}" and lines[2] == f"Section: {entry['label']}", key
        count = len(sections.option_names(key))
        assert [line.split(": ")[0] for line in lines[3:3 + count]] == list(sections.option_names(key)), key
        assert all(line.endswith(": Default") for line in lines[3:3 + count]), key
        # then a blank line and the sample words
        assert (lines[3 + count:4 + count] == [""]) == bool(entry["body"]), key
        assert text.endswith(entry["body"]), key
    # a template may give its own values - never one the page can't read
    mine = sections.markdown("portfolio", {"Show as": "Rows", "Tag": "baking"})
    assert "Width: Default\nStyle: Default\nHeading: Default\nSpace: Default\nAppear: Default\nShow as: Rows\nTag: baking" in mine
    for key, given in (("latest", {"Count": "40"}), ("latest", {"Show as": "Rows"}), ("pricing", {"Width": "Tall"})):
        with pytest.raises(ValueError):
            sections.markdown(key, given)


def _part(page):
    # a line taken out can leave a blank one behind, which draws nothing
    return re.sub(r"\s+", " ", page[page.index('data-section="'):page.index('id="after"')])


def _renders_the_same(admin, client, section, lines, title):
    head = f"Words.\n\n## Part\n\nSection: {section}"
    tail = "\n\n### An item\n\nSome words.\n\n## After\n\nEnd."
    plain = save_post(admin, title=f"{title} plain", body=head + tail)
    written = save_post(admin, title=f"{title} lines", body=head + "\n" + lines + tail)
    a, b = (_part(client.get(f"/post/{s}").text) for s in (plain, written))
    assert a == b and ": Default" not in b and ": default" not in b.lower(), title
    return b


def test_default_is_the_same_as_no_line(admin, client):
    # Width, Style, Show as, Count and Tag, in any case, on a page that has
    # something for each to change - and the line itself never shows
    for n in range(4):
        save_post(admin, title=f"Something to list {n}", body="Words.", tags="baking")
    _renders_the_same(admin, client, "Pricing", "Width: Default\nStyle: default", "Plain")
    _renders_the_same(admin, client, "Hero", "Width: DEFAULT", "Hero")
    _renders_the_same(admin, client, "Bento grid", "Width: Default\nStyle: Default", "Bento")
    # (a latest list names the other posts, so it can't be compared page to page)
    lately = save_post(admin, title="Lately", body="Words.\n\n## Part\n\nSection: Latest posts\nCount: Default\nTag: Default\n\n## After\n\nEnd.")
    latest = _part(client.get(f"/post/{lately}").text)
    assert latest.count("<h3") == 3 and "Default" not in latest
    _renders_the_same(admin, client, "Portfolio", "Show as: Default\nTag: Default", "Portfolio")
    _renders_the_same(admin, client, "Portfolio", "Width: Default\nStyle: Default\nShow as: Default\nTag: Default", "All")
    # a real value still wins: Count 6 isn't the default's three
    six = save_post(admin, title="Six", body="Words.\n\n## Part\n\nSection: Latest posts\nCount: 6\nTag: baking\n\n## After\n\nEnd.")
    assert _part(client.get(f"/post/{six}").text).count("<h3") > 3


def test_default_on_every_page(admin, client):
    # the same lines on a column page and a wide one
    section = "## Plans\n\nSection: Pricing\n{}\n### Basic\n\nPrice: US$10\n\n- Every post"
    for name, extra in (("column", {}), ("wide", {"page_width": "wide"})):
        written = save_post(admin, title=f"Default on {name}", body="Intro.\n\n" + section.format("Width: Default\nStyle: Default\n"),
                            **extra)
        bare = save_post(admin, title=f"Bare on {name}", body="Intro.\n\n" + section.format(""), **extra)
        a, b = (client.get(f"/post/{s}").text for s in (written, bare))
        a, b = (x[x.index('id="plans"') - 200:x.index("US$10") + 400] for x in (a, b))
        assert a == b and "Default" not in a, name


def test_excerpts_feeds_and_emails_leave_out_every_option_line(admin, client):
    from soloblog import newsletter, posts, settings
    from soloblog.render import excerpt, render_post, without_section_lines_text
    body = ("Intro.\n\n## Lately\n\nSection: Latest posts\nWidth: Default\nStyle: Default\nCount: Default\nTag: Default\n\n"
            "## Work\n\nSection: Portfolio\nShow as: Rows\nTag: baking\n\n### A project\n\nWhat it is.\n")
    text = excerpt(render_post(body)[0], 500)
    for line in ("Default", "Section:", "Count", "Show as", "baking"):
        assert line not in text, line
    assert "Intro." in text and "What it is." in text
    assert re.sub(r"\n{3,}", "\n\n", without_section_lines_text(body)).strip() == (
        "Intro.\n\n## Lately\n\n## Work\n\n### A project\n\nWhat it is.")
    slug = save_post(admin, title="Option lines kept out", body=body)
    assert "Default" not in client.get("/rss").text.split("Option lines kept out")[1].split("</item>")[0]
    kept = settings.get("newsletter_full")
    try:
        settings.set_many({"newsletter_full": "1"})
        email = newsletter.post_email(posts.get_post(slug), settings.get_all(), "token")
        assert "Width: Default" not in email and "Count: Default" not in email and "Show as: Rows" not in email
    finally:
        settings.set_many({"newsletter_full": kept})
    # words that only look like a setting are someone's: a count or a tag alone, a value the page doesn't know
    for words in ("Count: 3", "Tag: baking", "Width: Tall", "Show as: a list"):
        assert words in excerpt(render_post(words + "\n")[0])


def test_a_translation_holds_the_option_lines_too():
    from soloblog import translate
    from soloblog.render import render_post
    html, _ = render_post("## Lately\n\nSection: Latest posts\nCount: 6\nTag: baking\n\nWords.\n")
    held_html, held = translate._hold_section_lines(html)
    assert "Count" not in held_html and "Tag:" not in held_html and len(held) == 1
    assert "Count: 6" in translate._restore_section_lines(held_html.replace("Lately", "Ahora"), held)


def test_the_editor_gets_the_registry(admin):
    from soloblog import editor_config, js, sections
    o = editor_config.block_options()
    assert set(o["sections"]) == set(sections.REGISTRY) and set(o["options"]) == set(sections.OPTIONS)
    assert o["kinds"] == sections.NAMES and o["shared"] == ["Width", "Style", "Heading", "Space", "Appear"]
    for key, entry in sections.REGISTRY.items():
        assert o["sections"][key]["options"] == list(sections.option_names(key)) and o["sections"][key]["label"] == entry["label"]
    # the editor highlights what the registry names - and a Features item's Icon: line
    assert o["lineKeys"] == ["Width", "Style", "Heading", "Space", "Appear", "Show as", "Count", "Tag", "Series",
                             "First paragraph", "Pictures together", "A line after a picture", "Icon"]
    # what the editor says under each kind of wrong value
    assert o["options"]["Style"]["note"] == "Style can be Card or Default"
    assert o["options"]["Show as"]["note"] == "Show as can be Grid, Masonry, Rows, Full screen, Sideways or Default"
    assert o["options"]["Count"]["note"] == "Count is a number from 1 to 12, or Default"
    assert {"default", "column"} <= set(o["options"]["Width"]["accepts"]) and "narrow" not in o["options"]["Width"]["accepts"]
    assert {"default", "full screen", "screen"} <= set(o["options"]["Show as"]["accepts"])
    page = admin.get("/admin/new").text
    assert '"lineKeys": ["Width", "Style", "Heading", "Space", "Appear", "Show as", "Count", "Tag", "Series", ' \
           '"First paragraph", "Pictures together", "A line after a picture", "Icon"]' in page
    assert '"reserved": "Default is a reserved word"' in page
    # the highlighting reads those names, not a list of its own
    init = Path(os.path.join(os.path.dirname(js.__file__), "editor_init.js")).read_text()
    assert "(PREFS.options || {}).lineKeys" in init and "Width|Style|Count" not in init
    # every inserted section is the registry's markdown, in one piece
    for key in sections.REGISTRY:
        assert editor_config.COMMAND[f"section-{key}"]["snippet"] == sections.markdown(key)


def test_a_tag_called_default_is_flagged_only_when_the_site_has_one(admin):
    from soloblog import editor_config, posts
    assert editor_config.block_options()["defaultTag"] is False
    slug = save_post(admin, title="Tagged Default", body="Words.", tags="default", published="")
    try:
        # a draft's tag counts: it can go live any day
        assert editor_config.block_options()["defaultTag"] is True
    finally:
        posts.delete_post(slug)
    assert editor_config.block_options()["defaultTag"] is False


def test_the_editor_fades_a_setting_left_at_default():
    from soloblog import js
    css = Path(os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "css", "input.css")).read_text()
    assert ".EasyMDEContainer .CodeMirror-line.sb-default > span {" in css
    init = Path(os.path.join(os.path.dirname(js.__file__), "editor_init.js")).read_text()
    assert "UNCHANGED.test(line) ? ' line-sb-default'" in init


# Recipe facts, Ingredients, Method, Interview, Contents, Previous and next -
# the jobs the Recipe, Interview, Docs and Project templates do

FACTS = "## At a glance\n\nSection: Recipe facts\n\nServes: 4\nPrep: 15 min\nCook: 1 h 20 min\n"
INGREDIENTS = "## Ingredients\n\nSection: Ingredients\n\n- 1 kg tomatoes\n- 1 onion\n- Salt\n"
METHOD = "## Method\n\nSection: Method\n\n1. Chop.\n2. Cook.\n3. Serve.\n"
CONTENTS = "## In this series\n\nSection: Contents\n"


def _recipes(html):
    import json
    blocks = [json.loads(b) for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]
    return [b for b in blocks if b["@type"] == "Recipe"]


def _section(page, kind, until="</main>"):
    """What a section drew, from its wrapper to the end of its part of the page."""
    part = page[page.index(f'data-section="{kind}"'):]
    return part[:part.index(until)]


def test_recipe_sections_look_like_a_recipes_parts(admin, client):
    slug = save_post(admin, title="Tomato soup", body=f"Words.\n\n{FACTS}\n{INGREDIENTS}\n{METHOD}")
    page = client.get(f"/post/{slug}").text
    facts = _section(page, "recipe_facts", 'data-section="ingredients"')
    assert facts.count('class="stat py-2 px-4"') == 3 and ">Serves<" in facts and "1 h 20 min" in facts
    assert "@lg:stats-horizontal" in facts
    ingredients = _section(page, "ingredients", 'data-section="method"')
    assert ingredients.count('type="checkbox"') == 3 and "peer-checked:line-through" in ingredients
    method = _section(page, "method")
    assert method.count("badge badge-primary badge-lg") == 3 and "Serve." in method
    # the headings are the page's own
    assert 'id="ingredients"' in page and 'id="method"' in page
    assert "Section:" not in page.split("<main")[1]


def test_method_has_three_names_and_ingredients_keep_the_words_around_the_list(admin, client):
    body = ("## Directions\n\nSection: Instructions\n\n1. One.\n2. Two.\n\n"
            "## Shopping\n\nSection: Ingredients\n\nFor the soup:\n\n- Leeks\n- Stock\n\nOr use a tin.\n")
    page = client.get(f"/post/{save_post(admin, title='Names', body=body)}").text
    assert page.count("badge badge-primary badge-lg") == 2
    part = _section(page, "ingredients")
    assert part.index("For the soup:") < part.index('type="checkbox"') < part.index("Or use a tin.")
    # no list: its words, not an empty list
    bare = save_post(admin, title="No list", body="## Ingredients\n\nSection: Ingredients\n\nJust words.\n")
    page = client.get(f"/post/{bare}").text
    assert "Just words." in page and 'type="checkbox"' not in page


def test_recipe_facts_tells_its_own_option_lines_from_the_recipes_facts(admin, client):
    # Width and Style belong to the section; Serves and Prep to the recipe -
    # under Section: in one paragraph, or after a blank line
    for name, body in (("Apart", "Section: Recipe facts\nWidth: Default\nStyle: Default\n\nServes: 4\nPrep: 5 min\n"),
                       ("Together", "Section: Recipe facts\nWidth: Column\nServes: 4\nPrep: 5 min\n")):
        page = client.get(f"/post/{save_post(admin, title=name, body='## Facts' + chr(10) * 2 + body)}").text
        part = _section(page, "recipe_facts")
        assert part.count("stat-title") == 2 and ">Serves<" in part and ">Prep<" in part, name
        assert ">Width<" not in part and ">Style<" not in part and "Default" not in part, name


def test_the_recipe_search_data(admin, client):
    def recipe(title, body, **extra):
        slug = save_post(admin, title=title, body=body, summary="A soup", **extra)
        return _recipes(client.get(f"/post/{slug}").text)

    both = recipe("Both", f"{FACTS}\n{INGREDIENTS}\n{METHOD}")
    assert len(both) == 1
    data = both[0]
    assert data["name"] == "Both" and data["description"] == "A soup"
    assert data["recipeIngredient"] == ["1 kg tomatoes", "1 onion", "Salt"]
    assert [s["text"] for s in data["recipeInstructions"]] == ["Chop.", "Cook.", "Serve."]
    assert data["recipeYield"] == "4" and data["prepTime"] == "PT15M" and data["cookTime"] == "PT1H20M"
    # either list is enough; neither is not a recipe - nor are the facts alone
    only_ingredients = recipe("Ingredients only", INGREDIENTS)
    assert len(only_ingredients) == 1 and "recipeInstructions" not in only_ingredients[0]
    assert only_ingredients[0]["recipeIngredient"] == ["1 kg tomatoes", "1 onion", "Salt"]
    only_method = recipe("Method only", METHOD)
    assert len(only_method) == 1 and "recipeIngredient" not in only_method[0]
    assert len(only_method[0]["recipeInstructions"]) == 3
    assert recipe("Neither", "## A heading\n\nWords.\n") == []
    assert recipe("Facts only", FACTS) == []
    # a width or style on the facts' own lines doesn't hide them from it
    styled = recipe("Styled", "## Facts\n\nSection: Recipe facts\nWidth: Wide\nStyle: Card\n\nServes: 2\n\n" + METHOD)
    assert styled[0]["recipeYield"] == "2"
    # two of a kind on one page: still one recipe, read from the first of each
    more = ("## More ingredients\n\nSection: Ingredients\n\n- Cream\n\n## Other method\n\nSection: Method\n\n1. Stir.\n")
    twice = recipe("Twice", f"{FACTS}\n{INGREDIENTS}\n{METHOD}\n{more}")
    assert len(twice) == 1 and twice[0]["recipeIngredient"] == ["1 kg tomatoes", "1 onion", "Salt"]
    assert len(twice[0]["recipeInstructions"]) == 3
    # on a wide page too
    assert len(recipe("On a wide page", f"Words.\n\n[Go](/join)\n\n{INGREDIENTS}", page_width="wide")) == 1


INTERVIEW = ("## The talk\n\nSection: Interview\n\n**Sam:** What got you started?\n\n"
             "**Alex:** A broken bike.\n\nA word from the editor.\n\n**Sam:** And now?\n\n**Alex:** More bikes.\n")


def test_interview_section_is_a_chat(admin, client):
    page = client.get(f"/post/{save_post(admin, title='Chat', body=INTERVIEW)}").text
    part = _section(page, "interview")
    assert part.count("chat chat-start") == 2 and part.count("chat chat-end") == 2
    # the first speaker in the plain bubble, the rest in the main colour
    assert part.count("chat-bubble-primary") == 2 and ">Alex<" in part
    # words between stay words, in order
    assert part.index("A broken bike.") < part.index("A word from the editor.") < part.index("And now?")
    # no speaker: just the words
    body = "## Talk\n\nSection: Interview\n\nOnly words.\n"
    plain = client.get(f"/post/{save_post(admin, title='No speakers', body=body)}").text
    assert "Only words." in plain and "chat-bubble" not in plain


def test_width_and_style_work_on_the_new_sections(admin, client):
    body = ("Words.\n\n## Chat\n\nSection: Interview\nWidth: Wide\nStyle: Card\n\n**Sam:** Hi\n\n**Alex:** Hello\n\n"
            "## After\n\nEnd.")
    page = client.get(f"/post/{save_post(admin, title='Wide chat', body=body)}").text
    assert "w-screen mx-[calc(50%-50vw)]" in page and "card border border-base-content/10" in page
    assert "Width:" not in page.split("<main")[1] and "Style:" not in page.split("<main")[1]


def test_default_is_the_same_as_no_line_on_the_new_sections(admin, client):
    for kind, body in (("Recipe facts", "Serves: 4\nCook: 10 min"), ("Ingredients", "- Flour\n- Salt"),
                       ("Method", "1. Mix.\n2. Bake."), ("Interview", "**A:** Hi\n\n**B:** Hello")):
        head = f"Words.\n\n## Part\n\nSection: {kind}"
        tail = f"\n\n{body}\n\n## After\n\nEnd."
        plain = save_post(admin, title=f"{kind} plain", body=head + tail)
        lines = save_post(admin, title=f"{kind} lines", body=head + "\nWidth: Default\nStyle: default" + tail)
        a, b = (_part(client.get(f"/post/{s}").text) for s in (plain, lines))
        assert a == b and "efault" not in b, kind


def test_the_new_sections_never_raise(admin, client):
    from soloblog import pages
    junk = ["", "<", "<li>" * 5000, "</li>" * 5000, "<ul><li>" + "x" * 200000 + "</li></ul>",
            "<p><strong>" + "A" * 50000 + ":</strong>" * 50, "<ol><ol><li><li></ul>", "Serves: " + "9" * 10000,
            "<h2 id=a>" * 500, "Series: " + "<b>" * 3000, "\x00�" * 1000]
    row = {"title": "T", "summary": "", "cover_image": "", "series_name": "", "slug": "t", "tags": ""}
    for kind in ("recipe_facts", "ingredients", "method", "interview", "contents", "previous_next"):
        draw = getattr(pages, pages.section_registry.REGISTRY[kind]["draw"])
        for text in junk:
            part = {"body": None, "ld": [], "wide": False, "before": None}
            draw(part, row, {}, text, None, False, [])
        assert pages._recipe_of_sections(row, "<h2>x</h2>Section: " + kind) is None
    # and through the whole page, with each kind given each kind of junk
    body = "\n\n".join(f"## H{i}\n\nSection: {k}\n\n{text}" for i, k in enumerate(
        ("Recipe facts", "Ingredients", "Method", "Interview", "Contents", "Previous and next")) for text in junk[:8])
    assert client.get(f"/post/{save_post(admin, title='Junk', body=body)}").status_code == 200


def _parts(admin, name, titles, **extra):
    return [save_post(admin, title=t, body=CONTENTS, series_name=name, series_order=str(n), **extra)
            for n, t in enumerate(titles, 1)]


def _list(page):
    return _section(page, "contents", "</nav>")


def test_contents_lists_the_series_in_order_and_marks_this_page(admin, client):
    first, second, third = _parts(admin, "Hiking contents guide", ["Packing", "Boots", "Maps"])
    part = _list(client.get(f"/post/{second}").text)
    assert part.index("Packing") < part.index("Boots") < part.index("Maps")
    assert part.count("<li") == 3 and "<ol" in part
    # this page marked, once; the others are plain links
    assert part.count('aria-current="page"') == 1
    marked = re.search(r'<a [^>]*aria-current="page"[^>]*>', part).group(0)
    assert f'href="/post/{second}"' in marked
    assert f'href="/post/{first}"' in part and f'href="/post/{third}"' in part
    assert "Section:" not in client.get(f"/post/{second}").text.split("<main")[1]


def test_contents_follows_the_series_and_hides_drafts_and_other_series(admin, client):
    first, _ = _parts(admin, "Bread Book", ["Flour", "Water"])
    save_post(admin, title="Salt (not ready)", body="x", series_name="Bread Book", series_order="3", published="")
    save_post(admin, title="Another thing", body="x", series_name="Cheese", series_order="1")
    part = _list(client.get(f"/post/{first}").text)
    assert "Water" in part and "Salt" not in part and "Another thing" not in part
    # a part added later, and a part moved, show at once - the page is drawn each time
    save_post(admin, title="Yeast", body="x", series_name="Bread Book", series_order="0")
    part = _list(client.get(f"/post/{first}").text)
    assert part.index("Yeast") < part.index("Flour") < part.index("Water")
    # a draft isn't a part for the admin either
    assert "Salt" not in _list(admin.get(f"/post/{first}").text)


def test_contents_can_name_another_series(admin, client):
    _parts(admin, "Guide to Guides", ["First part", "Second part"])
    body = "## Start here\n\nSection: Contents\nSeries: guide to guides\n\nPick one.\n"
    page = client.get(f"/post/{save_post(admin, title='Front page', body=body)}").text
    part = _list(page)
    assert part.index("First part") < part.index("Second part") and "aria-current" not in part
    assert part.index("Pick one.") < part.index("First part")
    # Default is this page's own series
    own = save_post(admin, title="Own", body="## Parts\n\nSection: Contents\nSeries: Default\n",
                    series_name="Guide to Guides", series_order="3")
    assert "First part" in _list(client.get(f"/post/{own}").text)


def test_contents_with_no_series_shows_a_reader_nothing_and_the_admin_why(admin, client):
    # an unknown name: no list, not even its heading
    body = "Words.\n\n## Start here\n\nSection: Contents\nSeries: No such series\n\n## After\n\nEnd."
    gone = save_post(admin, title="Gone", body=body)
    page = client.get(f"/post/{gone}").text
    assert 'data-section="contents"' not in page and 'id="start-here"' not in page
    assert "Contents is empty" not in page and 'id="after"' in page
    note = admin.get(f"/post/{gone}").text
    assert "Contents is empty" in note and "no series called" in note and "Only you see this" in note
    # a page in no series
    alone = save_post(admin, title="Alone", body="## Start here\n\nSection: Contents\n")
    assert 'data-section="contents"' not in client.get(f"/post/{alone}").text
    assert "isn't in a series" in admin.get(f"/post/{alone}").text
    # a series whose parts are all drafts
    save_post(admin, title="Unfinished", body="x", series_name="Not yet", series_order="1", published="")
    empty = save_post(admin, title="Empty", body="## Start here\n\nSection: Contents\nSeries: Not yet\n")
    assert 'data-section="contents"' not in client.get(f"/post/{empty}").text
    assert "has no published parts yet" in admin.get(f"/post/{empty}").text


def test_contents_escapes_what_it_shows(admin, client):
    evil = "<script>alert(1)</script>"
    _parts(admin, "Safe series", [evil, "Fine"])
    body = "## Start\n\nSection: Contents\nSeries: Safe series\n"
    page = client.get(f"/post/{save_post(admin, title='Safe front', body=body)}").text
    assert evil not in page and "&lt;script&gt;alert(1)&lt;/script&gt;" in _list(page)
    # a series called with markup: never raw and never an error, in the admin's note too
    _parts(admin, evil, ["One"])
    marked = save_post(admin, title="Markup", body=f"## Start\n\nSection: Contents\nSeries: {evil}\n")
    assert client.get(f"/post/{marked}").status_code == 200
    assert evil not in admin.get(f"/post/{marked}").text
    own = save_post(admin, title="Markup own", body=CONTENTS, series_name=evil, series_order="2")
    assert evil not in client.get(f"/post/{own}").text and evil not in admin.get(f"/post/{own}").text


def test_a_heading_with_nothing_under_it_leaves_the_table_of_contents_too(admin, client):
    from soloblog import pages
    body = "## Intro\n\nWords.\n\n## Parts\n\nSection: Contents\n\n## Other\n\nMore.\n"
    page = client.get(f"/post/{save_post(admin, title='Toc', body=body)}").text
    assert 'id="parts"' not in page and 'href="#parts"' not in page
    assert 'href="#intro"' in page and 'href="#other"' in page
    toc = ('<ul><li><a href="#a">A</a></li><li><details open><summary><a href="#b">B</a></summary>'
           '<ul><li><a href="#c">C</a></li></ul></details></li></ul>')
    assert pages._toc_without(toc, ["b"]) == '<ul><li><a href="#a">A</a></li></ul>'
    assert pages._toc_without('<ul><li><a href="#a">A</a></li></ul>', ["a"]) is None


def test_previous_and_next_are_the_pages_either_side_by_first_tag(admin, client):
    one = save_post(admin, title="Tide one", body="Words.", tags="tides, sea")
    two = save_post(admin, title="Tide two", body="Words.\n\n## Keep reading\n\nSection: Previous and next\n", tags="tides")
    three = save_post(admin, title="Tide three", body="Words.", tags="tides")
    other = save_post(admin, title="Other tag", body="Words.", tags="sea, tides")
    part = _section(client.get(f"/post/{two}").text, "previous_next")
    # the pages either side in the tag's newest-first list - not one whose first tag is another
    assert re.findall(r'<a href="(/post/[^"]+)" class="group relative', part) == [f"/post/{three}", f"/post/{one}"]
    assert ">Previous<" in part and ">Next<" in part and "Tide one" in part
    assert other not in "".join(re.findall(r'<a href="([^"]+)" class="group relative', part))
    # no tag, or alone in it: nothing, and no heading
    for name, tags in (("No tag", ""), ("Only one", "lonely")):
        slug = save_post(admin, title=name, body="Words.\n\n## Keep reading\n\nSection: Previous and next\n", tags=tags)
        page = client.get(f"/post/{slug}").text
        assert 'data-section="previous_next"' not in page and 'id="keep-reading"' not in page


def test_the_series_option_is_known_to_the_registry_and_the_editor(admin):
    from soloblog import editor_config, sections
    assert sections.accepts("Series", "My guide") and sections.accepts("Series", "Default")
    assert not sections.accepts("Series", "  ")
    assert sections.REGISTRY["contents"]["options"].keys() == {"Series"}
    assert sections.option_names("contents") == ("Width", "Style", "Heading", "Space", "Appear", "Series")
    assert sections.markdown("contents").endswith("Series: Default")
    assert "Series: Trail Guide" in sections.markdown("contents", {"Series": "Trail Guide"})
    assert sections.only_own_lines("Section: Contents<br>Series: Trail Guide")
    assert not sections.only_own_lines("Series: Trail Guide")
    save_post(admin, title="A part", body="Words.", series_name="Editor series")
    o = editor_config.block_options()
    assert "Editor series" in o["series"] and o["options"]["Series"]["type"] == "series"
    assert o["options"]["Series"]["note"] == "" and o["icons"]["series"]


def test_the_new_sections_leave_their_lines_out_of_excerpts(admin, client):
    from soloblog.render import excerpt, render_post
    body = ("Intro.\n\n## Parts\n\nSection: Contents\nSeries: Default\nWidth: Default\n\n"
            "## Facts\n\nSection: Recipe facts\nStyle: Card\n\nServes: 4\n")
    text = excerpt(render_post(body)[0], 500)
    assert "Intro." in text
    for line in ("Section:", "Series", "Width", "Style"):
        assert line not in text, line


# ---- Heading: where a section's ## and the words under it sit

HEADED = """Some words first.

## Plans

Section: {kind}
{line}

Words that come before the items.

### {first}

{item}

### {second}

{item}

## After

End.
"""


def _is_centred(html):
    # the page's own heading code may add classes of its own
    return bool(re.search(r'<h2 class="[^"]*\btext-center\b[^"]*" id="plans"', html))


def _headed(admin, client, line="", kind="Features", **extra):
    body = HEADED.format(kind=kind, line=line, first="First", second="Second", item="A line.")
    slug = save_post(admin, title=f"Heading {line} {kind} {extra}", body=body, **extra)
    page = client.get(f"/post/{slug}").text
    return page[page.index('id="plans"') - 300:page.index('id="after"')]


def test_the_shared_options_are_every_sections_first():
    from soloblog import sections
    option = sections.OPTIONS["Heading"]
    assert [v[0] for v in sections.values("Heading")] == ["left", "centre"]
    assert [v[1] for v in sections.values("Heading")] == ["Left", "Centred"]
    assert option["aliases"] == {"center": "centre", "centered": "centre"}
    assert sections.SHARED == ("Width", "Style", "Heading", "Space", "Appear")
    for key in sections.REGISTRY:
        assert sections.option_names(key)[:5] == sections.SHARED, key
        assert "\nHeading: Default\nSpace: Default\nAppear: Default" in sections.markdown(key), key
    for value, picked in (("Centred", "centre"), ("centre", "centre"), ("Center", "centre"), ("LEFT", "left"),
                          ("Default", ""), ("", ""), ("Middle", "")):
        assert sections.pick("Heading", value) == picked, value
    assert sections.accepts("Heading", "Centred") and sections.accepts("Heading", "default")
    assert not sections.accepts("Heading", "Middle")
    assert sections.note("Heading") == "Heading can be Left, Centred or Default"


def test_the_editor_gets_the_heading_option():
    from soloblog import editor_config
    o = editor_config.block_options()["options"]["Heading"]
    assert o["default"] == "Follow the site" and o["type"] == "choice"
    assert [v[0] for v in o["values"]] == ["left", "centre"] and {"centred", "left", "default"} <= set(o["accepts"])
    assert o["note"] == "Heading can be Left, Centred or Default"
    assert all("<svg" in v[3] for v in o["values"])


def test_a_centred_heading_centres_the_heading_and_the_words_under_it_not_the_items(admin, client):
    part = _headed(admin, client, "Heading: Centred")
    assert _is_centred(part)
    # the words under the heading carry the mark the section's rule centres; the items don't
    assert "[&amp;_.section-intro]:text-center" in part or "[&_.section-intro]:text-center" in part
    assert 'class="prose' in part and "section-intro" in part
    assert "Heading: Centred" not in part
    plain = _headed(admin, client)
    assert not _is_centred(plain) and ".section-intro]:text-center" not in plain
    assert part.count("Second") == plain.count("Second") and "Heading:" not in plain


def test_a_centred_heading_on_a_wide_section_goes_with_its_breakout(admin, client):
    for width in ("Wide", "Full"):
        part = _headed(admin, client, f"Width: {width}\nHeading: Centred")
        assert _is_centred(part) and ".section-intro]:text-center" in part, width
        assert part.index('id="plans"') < part.index('data-section="features"'), width


def test_every_kind_that_draws_the_posts_heading_centres_it(admin, client):
    from soloblog import sections
    for key, entry in sections.REGISTRY.items():
        if entry["own_heading"] or key == "hero":
            continue
        body = f"Words.\n\n{sections.markdown(key, {'Heading': 'Centred'}, heading='Plans')}\n\n## After\n\nEnd."
        page = client.get(f"/post/{save_post(admin, title=f'Centred {key}', body=body)}").text
        if 'id="plans"' not in page:
            continue  # a section with nothing to show yet draws nothing
        assert _is_centred(page), key
        assert "Heading: Centred" not in page and "Heading: Default" not in page, key


def test_the_sites_setting_is_followed_unless_the_section_says_otherwise(admin, client):
    from soloblog import settings
    try:
        settings.set_many({"section_heading_align": "centre"})
        for line in ("", "Heading: Default"):
            assert _is_centred(_headed(admin, client, line)), line
        left = _headed(admin, client, "Heading: Left")
        assert not _is_centred(left) and ".section-intro]:text-center" not in left
        settings.set_many({"section_heading_align": "left"})
        assert not _is_centred(_headed(admin, client))
        assert _is_centred(_headed(admin, client, "Heading: Centred"))
        settings.set_many({"section_heading_align": "diagonal"})
        assert not _is_centred(_headed(admin, client))
    finally:
        settings.set_many({"section_heading_align": "left"})


def test_a_section_that_draws_its_own_heading_ignores_heading(admin, client):
    def page(line):
        body = f"Words.\n\n## Jo Park\n\nSection: Profile\n{line}\n\nOne line about me.\n\n## After\n\nEnd."
        text = client.get(f"/post/{save_post(admin, title=f'Profile {line}', body=body)}").text
        return text[text.index('data-section="profile"'):text.index('id="after"')]
    assert page("Heading: Centred") == page("Heading: Left") == page("")
    assert "Heading:" not in page("Heading: Centred")


def test_a_heading_value_the_page_cannot_use_leaves_the_heading_alone(admin, client):
    assert not _is_centred(_headed(admin, client, "Heading: Diagonal"))


def test_the_heading_line_never_shows_in_excerpts(admin, client):
    from soloblog.render import excerpt, render_post
    text = excerpt(render_post("Intro.\n\n## Facts\n\nSection: Recipe facts\nHeading: Centred\n\nServes: 4\n")[0], 500)
    assert "Heading" not in text and "Section:" not in text


def test_a_photos_sections_words_centre_with_its_heading(admin, client):
    """Photos draws its words before the gallery itself - they're its intro,
    centred with a centred heading; the gallery isn't touched."""
    from conftest import save_post
    body = ("## Photos\n\nSection: Photo gallery\nHeading: Centred\n\nA line about them.\n\n"
            "```gallery\n/uploads/a.webp\n/uploads/b.webp\n```")
    page = client.get(f"/post/{save_post(admin, title='Centred photos', body=body)}").text
    words = page.rindex("A line about them.")  # not the description in the head
    assert page.rfind("section-intro", 0, words) > page.rfind('data-section="gallery"', 0, words)
    assert "[&amp;_.section-intro]:text-center" in page or "[&_.section-intro]:text-center" in page


# ---- Space: and Appear: - the room around a section and how it comes into view

def test_space_and_appear_are_registered_for_every_section():
    from soloblog import editor_config, pages, sections
    assert [v[0] for v in sections.values("Space")] == list(pages.SPACINGS)
    assert [v[1] for v in sections.values("Space")] == list(pages.SPACINGS.values()) == ["Small", "Medium", "Large"]
    assert [v[0] for v in sections.values("Appear")] == list(pages.SECTION_MOTIONS)
    assert [v[1] for v in sections.values("Appear")] == list(pages.SECTION_MOTIONS.values())
    for name in ("Space", "Appear"):
        option = sections.OPTIONS[name]
        assert option["type"] == "choice" and option["default"] == "Follow the page"
        # every value has words and an icon the editor has
        assert all(about and svg in editor_config.editor_icons.ICONS for _, _, about, svg in sections.values(name)), name
        assert sections.accepts(name, "Default") and not sections.accepts(name, "Huge")
        assert editor_config.block_options()["options"][name]["note"] == sections.note(name)
    assert sections.note("Space") == "Space can be Small, Medium, Large or Default"
    assert sections.note("Appear").startswith("Appear can be Fade, Rise, Zoom, Slide left,")
    for value, picked in (("Small", "small"), ("LARGE", "large"), ("Default", ""), ("Huge", "")):
        assert sections.pick("Space", value) == picked, value
    for value, picked in (("Fade", "fade"), ("rise", "rise"), ("Slide left", "slide"),
                          ("Slide both ways", "alternate"), ("Focus", "blur"),
                          ("None", "none"), ("Default", ""), ("Spin", "")):
        assert sections.pick("Appear", value) == picked, value


def test_an_inserted_section_and_every_template_write_space_and_appear_after_heading(admin):
    from soloblog import post_templates, sections
    for key in sections.REGISTRY:
        assert "\nHeading: Default\nSpace: Default\nAppear: Default\n" in sections.markdown(key) + "\n", key
    for key in post_templates.BUILT_IN:
        body = post_templates.get(key)["body"]
        for kind in re.findall(r"^Section: (.+)$", body, re.M):
            block = body[body.index(f"Section: {kind}"):].split("\n\n")[0]
            assert "Heading: Default\nSpace: Default\nAppear: Default" in block or "Style: Window" in block or \
                "Space:" in block, (key, kind)


def test_the_slash_menu_and_help_list_space_and_appear(admin):
    from soloblog import sections
    # the editor, and its Help panel's parts (they come when it opens)
    page = admin.get("/admin/new").text + admin.get("/admin/editor/help").text
    assert '"shared": ["Width", "Style", "Heading", "Space", "Appear"]' in page
    for label in ("Fades in", "Rises into place", "Slides in from each side, in turn", "Is there from the start",
                  "Less room around it", "More room around it"):
        assert label in page, label
    # the editor's Help lists them with the other shared lines
    assert "Space: Small" in page and "Appear: Rise" in page and "Appear: Default" in page
    assert "Width, style, heading, space and appear" in page
    assert sections.SHARED[3:] == ("Space", "Appear")


def test_write_out_options_fills_in_what_a_section_doesnt_say():
    """A page written before every option was written out gets the rest as
    Default, in order, keeping what its lines said - and its item lines."""
    from soloblog import sections
    text = ("Intro.\n\n## Story\n\nSection: Story\nWidth: Wide\n\n### One\n\nWords.\n\n"
            "## Facts\n\nSection: Recipe facts\nServes: 4\n\n## Plain\n\nJust words.\nKey: not a section")
    out = sections.write_out_options(text)
    assert "Section: Story\nWidth: Wide\nStyle: Default\nHeading: Default\nSpace: Default\nAppear: Default\n" in out
    assert "Section: Recipe facts\nWidth: Default\nStyle: Default\nHeading: Default\nSpace: Default\nAppear: Default\n" \
           "Serves: 4" in out
    assert out.endswith("Just words.\nKey: not a section")
    assert sections.write_out_options(out) == out  # running it again changes nothing


def test_every_section_in_the_built_demo_has_every_option(tmp_path):
    """Every page of the built demo - its posts and the tour's own pages -
    has each section's options written out."""
    import re
    import subprocess
    import sys
    data = tmp_path / "demo"
    subprocess.run([sys.executable, "-c", f"import os; os.environ['DATA_DIR'] = {str(data)!r}; "
                    "os.environ['SESSION_SECRET'] = 'x'; os.environ['DEMO_OFFLINE'] = '1'; "
                    "from soloblog import demo; demo.build()"],
                   check=True, capture_output=True, cwd=os.path.dirname(os.path.dirname(__file__)))
    from soloblog import sections
    for path in (data / "posts").glob("*.md"):
        body = path.read_text(encoding="utf-8")
        for m in re.finditer(r"^Section: (.+)$", body, re.M):
            kind = sections.NAMES.get(m.group(1).strip().lower())
            if kind:
                after = body[m.end() + 1:].split("\n")[:len(sections.option_names(kind))]
                assert [line.split(":")[0] for line in after] == list(sections.option_names(kind)), path.name


def test_every_section_in_the_demo_has_every_option():
    from soloblog import demo, sections
    for slug, _, _, _, body, _ in demo.posts_and_pages({}):
        body = sections.write_out_options(body)
        for m in re.finditer(r"^Section: (.+)$", body, re.M):
            kind = sections.NAMES.get(m.group(1).strip().lower())
            if kind:
                after = body[m.end() + 1:].split("\n")[:len(sections.option_names(kind))]
                assert [line.split(":")[0] for line in after] == list(sections.option_names(kind)), slug


def test_a_sections_heading_appears_with_its_section(admin, client):
    """The ## above a section comes into view as the section does - its own
    Appear:, else the page's - on the heading itself, so the contents and
    folding still find it."""
    page = _headed(admin, client, "Appear: Zoom")
    head = re.search(r'<h2 [^>]*id="plans"[^>]*>', page).group(0)
    assert "reveal-item" in head and 'data-reveal="zoom"' in head
    folded = _headed(admin, client, "Appear: Rise", heading_fold="open")
    assert "<summary" in folded and re.search(r'<h2 [^>]*id="plans"[^>]*data-reveal="rise"', folded)


def test_every_section_follows_one_design(admin, client):
    """The demo's Every section page, as a visitor gets it: a section's own
    title is the page's <h2> and everything under it an <h3>, and an item's
    title is one size (docs/DEVELOPMENT.md > Section design)."""
    from soloblog import demo
    slug = save_post(admin, title="Every section", body=demo._sections_page({}))
    page = client.get(f"/post/{slug}").text
    parts = page.split("</article>")[0].split(' data-section="')[1:]
    assert len(parts) > 30
    titled = 0
    for part in parts:
        kind = part.split('"')[0]
        # the heading after a section belongs to the next one; its own is drawn first
        inside = part.rsplit("<h2", 1)[0]
        from soloblog import pages
        own = 1 if pages.section_registry.REGISTRY[kind].get("own_heading") or kind == "hero" else 0
        assert inside.count("<h2") <= own, kind
        assert "<h4" not in inside, kind
        titled += inside.count(f'class="{pages.ITEM_TITLE}')
    assert titled > 25


def test_section_code_uses_the_named_sizes():
    """A title size, a card's padding or a shadow written by hand in one
    section is how they drifted apart: pages.py names each once."""
    src = Path("soloblog/pages.py").read_text(encoding="utf-8")
    named = re.compile(r"^(CARD_PAD|PANEL_PAD|SHADOW_REST|SHADOW_RAISED|ITEM_TITLE|LEAD_TITLE|LIFT) = ", re.M)
    lines = [ln for ln in src.split("\n") if not named.match(ln)]
    by_hand = [ln.strip() for ln in lines if re.search(
        r'(?<![:\w-])shadow-(sm|md|lg|xl|2xl)\b|[" ]p-5\b|card-title|text-\[0\.\d+rem\]|\bH4\(|text-lg font-semibold', ln)]
    assert not by_hand, by_hand


COVER_KINDS = {"hero", "cta", "picture_and_text"}


def test_cover_is_offered_only_by_the_sections_it_means_something_for():
    from soloblog import editor_config, sections
    assert {k for k, e in sections.REGISTRY.items() if e["cover"]} == COVER_KINDS
    spec = editor_config.block_options()["sections"]
    for key in sections.REGISTRY:
        takes = key in COVER_KINDS
        assert sections.accepts("Style", "Cover", key) is takes, key
        assert ("cover" in spec[key]["styleAccepts"]) is takes, key
        assert any(v[0] == "cover" for v in spec[key]["styles"]) is takes, key
        assert ("Cover" in spec[key]["styleNote"]) is takes, key
        assert "card" in spec[key]["styleAccepts"] and "default" in spec[key]["styleAccepts"]
    # a kind that isn't known gets the shared ones: no Cover
    assert "cover" not in editor_config.block_options()["options"]["Style"]["accepts"]
    assert [v[0] for v in sections.values("Style", "hero")] == ["card", "cover", "window"]
    assert [v[0] for v in sections.values("Style", "pricing")] == ["card"]


def test_every_shared_option_value_draws_every_section_as_itself(admin, client):
    """Every section x every value of Width, Style (Cover too), Heading,
    Space and Appear draws without an error and stays its own kind -
    Style: Cover on one that can't take it is ignored, never a hero."""
    from soloblog import sections
    for kind in sections.REGISTRY:
        for name in sections.SHARED:
            offered = [v[0] for v in sections.values(name, kind if name == "Style" else "")]
            for value in dict.fromkeys([*offered, "cover" if name == "Style" else "default"]):
                text = sections.markdown(kind).replace(f"{name}: Default", f"{name}: {value}")
                page = client.get("/post/" + save_post(admin, title=f"{kind} {name} {value}", body=f"Intro.\n\n{text}"))
                assert page.status_code == 200, (kind, name, value)
                kinds = set(re.findall(r'data-section="([a-z_]+)"', page.text))
                becomes_hero = kind == "hero" or (name == "Style" and value == "cover" and kind in COVER_KINDS)
                assert ("hero" in kinds) is becomes_hero, (kind, name, value, kinds)
                assert f"{name}: {value}" not in page.text and "Section:" not in page.text, (kind, name, value)


def test_style_cover_on_a_section_that_cant_take_it_keeps_its_own_drawing(admin, client):
    pricing = "## Plans\n\nSection: Pricing\nStyle: Cover\n\n### Basic\n\nPrice: US$10 a month\n\n- Every post\n\n[Choose](/join)"
    page = client.get("/post/" + save_post(admin, title="Cover on pricing", body=pricing)).text
    assert 'data-section="pricing"' in page and "US$10" in page and 'data-section="hero"' not in page
    # drawn as Default: the same page as with no Style line
    plain = client.get("/post/" + save_post(admin, title="Cover on pricing", body=pricing.replace("Style: Cover", "Style: Default"))).text
    assert page.count("US$10") == plain.count("US$10") and page.count("Price:") == plain.count("Price:")
    covered = "## Over\n\nSection: Hero\nStyle: Cover\n\n![A](/uploads/a.webp)\n\nWords.\n\n[Go](/go)"
    assert 'data-section="hero"' in client.get("/post/" + save_post(admin, title="Cover on hero", body=covered)).text


def test_a_countdown_straight_under_a_sections_lines_is_a_countdown(admin, client):
    for gap in ("\n", "\n\n"):
        body = f"## Soon\n\nSection: Features\nStyle: Default{gap}Countdown: 2099-03-12\n\n### One\n\nIcon: leaf\nA line."
        page = client.get("/post/" + save_post(admin, title=f"Countdown {len(gap)}", body=body)).text
        assert 'data-countdown="2099-03-12"' in page, repr(gap)
        assert "Countdown:" not in page and "Section:" not in page


STORY = ("## The tour\n\nSection: Story\n{}\n\n### One\n\n![A](/uploads/a.webp)\n\nFirst words.\n\n"
         "### Two\n\n![B](/uploads/b.webp)\n\nMore words.\n")


@pytest.mark.parametrize("lines", ["", "Width: Full\n", "Width: Wide\n"])
def test_a_storys_heading_is_held_in_one_wrapper_with_its_story(admin, client, lines):
    slug = save_post(admin, title=f"Story {lines.strip() or 'column'}",
                     body=STORY.format(lines) + "\n## After\n\nEnd.\n")
    page = client.get(f"/post/{slug}").text
    wrap = page[page.index("data-story-wrap"):]
    wrap = wrap[:wrap.index('id="after"')]
    head = re.search(r"<(?:div|h2)\b[^>]*data-story-head[^>]*>", wrap).group(0)
    # held under the header, and lower by --story-shift on a tall window, where the pair is centred
    for held in ("@5xl:group-data-[live]/sw:sticky",
                 "@5xl:group-data-[live]/sw:top-[calc(var(--header-h,0px)+var(--story-shift,0px))]",
                 "@5xl:group-data-[live]/sw:bg-base-200"):
        assert held in head
    assert wrap.index("data-story-head") < wrap.index("data-story-held")
    # the held picture starts under the heading, from a laptop's width
    assert "sticky top-[var(--story-top,var(--header-h,0px))]" in wrap
    # the heading is let go when the picture is: its margin runs on by the picture's height and
    # the story's pulls back by the same
    assert "@5xl:group-data-[held]/sw:mb-[calc(100svh-var(--story-top)-var(--footer-h,0px)+var(--story-gap))]!" in head
    assert "@5xl:group-data-[held]/sw:mt-[calc(var(--story-top)+var(--footer-h,0px)-100svh)]!" in wrap


def test_only_a_storys_heading_is_held(admin, client):
    slug = save_post(admin, title="Heading of a pricing section", body=PRICING)
    page = client.get(f"/post/{slug}").text
    assert "data-story-head" not in page and "data-story-wrap" not in page


def test_a_note_under_a_menu_course_shows(admin, client):
    slug = save_post(admin, title="Lunch", body="## Menu\n\nSection: Menu\n\n### Breakfast\n\n"
                                              "- Toast - sourdough · $5\n\nServed until noon.\n")
    html = client.get(f"/post/{slug}").text
    assert "Toast" in html and "Served until noon." in html
