"""Resume, Skills, Profile, Bios, Project facts, Photo story and the Hero's
Window style - sections that take over what the Resume, Profile, Media kit,
Project and Landing templates are made of."""
from pathlib import Path
import json
import re

import pytest
from conftest import save_post

from soloblog import sections


def _page(admin, client, body, title="A page", **fields):
    slug = save_post(admin, title=title, body=body + "\n\n## After\n\nEnd.\n", **fields)
    return client.get(f"/post/{slug}").text


def _section(page, kind, nth=0):
    """The html of one section, up to the next one (or the page's end)."""
    marks = [m.start() for m in re.finditer(r'data-section="', page)]
    here = [m.start() for m in re.finditer(f'data-section="{kind}"', page)][nth]
    after = [m for m in marks if m > here]
    return page[here:after[0] if after else page.index('id="after"', here)]


def _person_data(page):
    found = re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)
    return [d for d in (json.loads(f) for f in found) if d.get("@type") == "ProfilePage"]


def test_each_sample_renders_without_its_lines(admin, client):
    for key in ("resume", "skills", "profile", "bios", "project_facts", "photo_story", "story"):
        page = _page(admin, client, f"Words.\n\n{sections.markdown(key)}\n\n## After\n\nEnd.", title=f"Sample {key}")
        main = page.split("<main")[1]
        assert f'data-section="{key}"' in main, key
        assert "Section:" not in main and ": Default" not in main, key
    # and the Window style's sample is what the menu writes
    page = _page(admin, client, sections.markdown("hero", {"Style": "Window"}), title="Sample window")
    assert "Style:" not in page.split("<main")[1] and "w-screen" in page


def test_resume_entries_and_dates(admin, client):
    body = ("## Experience\n\nSection: Resume\n\n### Designer, Acme · 2021 – 2024\n\nMade things.\n\n"
            "### Baker\n\nNo dates here.\n\n## Education\n\nSection: Resume\n\n### Bakery school · 2019\n\nFlour.\n")
    page = _page(admin, client, body, title="CV")
    first, second = _section(page, "resume"), _section(page, "resume", 1)
    # the dates on the right, the title and its words
    assert "Designer, Acme" in first and "2021 – 2024" in first and "text-sm text-base-content/60 shrink-0" in first
    assert "Baker" in first and "No dates here." in first
    assert "Bakery school" in second and "2019" in second
    # the heading is the page's own ##, and the entries' titles are headings under it
    assert 'id="experience"' in page and "<h3" in first


def test_skills_are_badges_and_a_long_item_keeps_the_list(admin, client):
    page = _page(admin, client, "## Skills\n\nSection: Skills\n\n- Baking\n- Spanish\n", title="Short skills")
    part = _section(page, "skills")
    assert part.count("badge badge-outline") == 2 and "<ul" not in part
    long = "A skill described at such length that it can't be a badge, really"
    page = _page(admin, client, f"## Skills\n\nSection: Skills\n\nSome words.\n\n- Baking\n- {long}\n", title="Long skills")
    part = _section(page, "skills")
    assert "badge-outline" not in part and long in part and "<ul" in part and "Some words." in part


def test_person_data_once_for_resume_profile_both_or_neither(admin, client):
    resume = "## Experience\n\nSection: Resume\n\n### Baker · 2020\n\nBread.\n"
    profile = "## Alex\n\nSection: Profile\n\nA line.\n"
    one = _person_data(_page(admin, client, resume, title="Only resume"))
    two = _person_data(_page(admin, client, profile, title="Only profile"))
    both = _person_data(_page(admin, client, resume + "\n" + profile + "\n" + resume.replace("Baker", "Cook"),
                              title="Both and more"))
    none = _person_data(_page(admin, client, "## Plans\n\nSection: Skills\n\n- One\n", title="Neither"))
    assert len(one) == len(two) == len(both) == 1 and none == []
    assert one[0]["mainEntity"]["@type"] == "Person" and one[0]["mainEntity"]["name"] == "Only resume"


def test_profile_draws_the_heading_as_the_name(admin, client):
    body = ("Some words.\n\n## Alex Rivera\n\nSection: Profile\n\n![Alex](/uploads/a.webp)\n\nBaker and writer.\n\n"
            "A couple of sentences about the work.\n\n[Writing](/blog) [Email me](mailto:a@example.com)\n\n"
            "## After\n\nEnd.\n")
    page = _page(admin, client, body, title="Profile page")
    part = _section(page, "profile")
    assert 'id="alex-rivera"' in part and ">Alex Rivera<" in part and "text-3xl" in part
    # the name is drawn once, in the section - not again above it
    assert len(re.findall(r'<h2[^>]*id="alex-rivera"', page)) == 1
    assert "rounded-full" in part and "Baker and writer." in part and "text-xl" in part
    assert 'class="btn btn-primary">Writing</a>' in part and "mailto:a@example.com" in part
    assert "A couple of sentences" in part and "text-center" in part
    # no photo, no links: just the name and the words
    bare = _section(_page(admin, client, "## Alex\n\nSection: Profile\n\nOnly a line.\n", title="Bare profile"), "profile")
    assert 'class="avatar' not in bare and "btn btn-primary" not in bare and "Only a line." in bare


def test_profile_on_a_wide_page_draws_its_own_heading_once(admin, client):
    body = "Buy it.\n\n[Buy](/join)\n\n## Alex Rivera\n\nSection: Profile\n\nA line.\n\n[Say hi](/contact)\n"
    page = _page(admin, client, body, title="Wide profile", page_width="wide")
    assert len(re.findall(r'<h2[^>]*id="alex-rivera"', page)) == 1 and "Say hi" in page


def test_bios_copy_and_download(admin, client):
    body = ("## For the press\n\nSection: Bios\n\n### Short bio\n\nTwo sentences.\n\n"
            "### With a link\n\nSee [my site](https://example.com).\n\n"
            "### Photos\n\n![Alex](/uploads/a.webp)\n![Alex again](/uploads/b.webp)\n")
    page = _page(admin, client, body, title="Press")
    part = _section(page, "bios")
    # a Copy button for plain words, none where a link would be lost
    assert part.count("data-copy=") == 1 and 'data-copy="Two sentences."' in part and "data-copied" in part
    # each photo with a Download link to the file itself
    assert part.count("download") >= 2 and 'href="/uploads/a.webp"' in part and "Download" in part
    assert "<h3" in part


def test_project_facts_strip(admin, client):
    body = "## At a glance\n\nSection: Project facts\n\nClient: Corner Café\nYear: 2026\nRole: Packaging\n"
    part = _section(_page(admin, client, body, title="Facts"), "project_facts")
    for word in ("Client", "Corner Café", "Year", "2026", "Role", "Packaging"):
        assert word in part
    assert "uppercase tracking-widest" in part and "border-y" in part


def test_project_facts_written_straight_under_the_section_line(admin, client):
    # the fact lines aren't options: they sit in the same paragraph as the Section: line
    # and must neither be lost nor leave "Section:" in an excerpt
    from soloblog.render import excerpt, render_post, without_section_lines_text
    body = ("Intro.\n\n## At a glance\n\nSection: Project facts\nWidth: Wide\nClient: Corner Café\nYear: 2026\n\n"
            "Words after.\n")
    page = _page(admin, client, body, title="Facts together")
    part = _section(page, "project_facts")
    assert "Corner Café" in part and "2026" in part and "Section:" not in part and "Width" not in part
    text = excerpt(render_post(body)[0], 400)
    assert "Section:" not in text and "Words after." in text
    assert "Section:" not in without_section_lines_text(body)


def test_photo_story_arrangements_and_each_option(admin, client):
    head = "## Story\n\nSection: Photo story\n{}\n"
    story = ("The opening paragraph.\n\n![One](/uploads/a.webp)\n\nA short line after it.\n\n> A quote.\n\n"
             "![Two](/uploads/b.webp)\n![Three](/uploads/c.webp)\n")

    def draw(lines, title):
        return _section(_page(admin, client, head.format(lines) + "\n" + story, title=title), "photo_story")

    plain, defaults = draw("", "Story plain"), draw(
        "First paragraph: Default\nPictures together: Default\nA line after a picture: Default", "Story default")
    assert plain == defaults and ": Default" not in defaults
    # the defaults: a big first paragraph, a line beside its picture, pictures in a row, a pull quote
    assert "prose-lg @xl:prose-xl" in plain and "@3xl:grid-cols-[3fr_2fr]" in plain and "@xl:flex-row" in plain
    assert "A quote.</p></blockquote>" in plain and "text-2xl @xl:text-3xl" in plain
    # each option changes only its own part
    normal = draw("First paragraph: Normal", "Story normal")
    assert "prose-lg @xl:prose-xl" not in normal and "@3xl:grid-cols-[3fr_2fr]" in normal and "@xl:flex-row" in normal
    stacked = draw("Pictures together: One under another", "Story stacked")
    assert "@xl:flex-row" not in stacked and "prose-lg @xl:prose-xl" in stacked and "@3xl:grid-cols-[3fr_2fr]" in stacked
    assert stacked.count("<figure") == plain.count("<figure") and stacked.count("flex flex-col gap-4") == 0
    under = draw("A line after a picture: Under it", "Story under")
    assert "@3xl:grid-cols-[3fr_2fr]" not in under and "A short line after it." in under
    assert "prose-lg @xl:prose-xl" in under and "@xl:flex-row" in under
    # words people may write: the label in any case, and the option lines never show
    assert draw("First paragraph: NORMAL", "Story any case") == normal
    # a value the page doesn't know is the default
    assert draw("First paragraph: Huge", "Story unknown") == plain
    for page_part in (normal, stacked, under):
        assert "First paragraph" not in page_part and "Pictures together" not in page_part


def test_photo_story_with_no_pictures_and_only_pictures(admin, client):
    words = _section(_page(admin, client, "## S\n\nSection: Photo story\n\nJust words.\n\nMore words.\n",
                           title="Story words"), "photo_story")
    assert "Just words." in words and "<figure" not in words and "prose-lg @xl:prose-xl" in words
    pictures = _section(_page(admin, client, "## S\n\nSection: Photo story\n\n![One](/uploads/a.webp)\n\n"
                                             "![Two](/uploads/b.webp)\n", title="Story pictures"), "photo_story")
    assert pictures.count("<figure") == 2 and "@xl:flex-row" in pictures
    empty = _section(_page(admin, client, "## S\n\nSection: Photo story\n", title="Story empty"), "photo_story")
    assert "<figure" not in empty


WINDOW = ("## Make it yours\n\nSection: Hero\nStyle: Window\n\nLabel: Free and open source\n\n"
          "![The app](/uploads/a.webp)\n\nA line about it.\n\n[Try the demo](/demo) [Get started](/start)\n\n"
          "- Free\n- No account\n")


def test_hero_window_style(admin, client):
    page = _page(admin, client, WINDOW, title="Window")
    part = _section(page, "hero")
    # label, big heading, line, buttons, points, framed picture
    assert 'badge badge-soft badge-primary mb-6">Free and open source' in part
    assert "text-5xl sm:text-7xl font-extrabold tracking-tighter" in part and 'id="make-it-yours"' in part
    assert "btn btn-lg btn-primary" in part and "btn btn-lg btn-ghost" in part and "/start" in part
    assert part.count("text-primary") >= 2 and "No account" in part
    assert "rounded-box border border-base-content/10 shadow-xl" in part and "blur-3xl" in part and "data-tilt" in part
    assert 'fetchpriority="high"' in part
    # not the dark cover, and its lines never show
    assert "from-black/85" not in part and "Style:" not in part and "Label:" not in part
    # no picture, no label
    bare = _section(_page(admin, client, "## Hello\n\nSection: Hero\nStyle: Window\n\nA line.\n\n[Go](/go)\n",
                          title="Window bare"), "hero")
    assert "shadow-xl" not in bare and "badge" not in bare and "A line." in bare and "btn-primary" in bare
    for classes in ("badge badge-soft badge-primary mb-6", "btn btn-lg btn-primary", "btn btn-lg btn-ghost",
                    "rounded-box border border-base-content/10 shadow-xl", "flex flex-wrap justify-center gap-x-6 gap-y-2 mt-6"):
        assert classes in part, classes


def test_hero_window_label_in_its_own_paragraph_and_other_styles_unchanged(admin, client):
    body = "## H\n\nSection: Hero\nStyle: Window\n\nLabel: New\n"
    assert 'mb-6">New' in _section(_page(admin, client, body, title="Window label below"), "hero")
    cover = _section(_page(admin, client, "## H\n\nSection: Hero\nStyle: Cover\n\n![P](/uploads/a.webp)\n\nWords.\n",
                           title="Cover still"), "hero")
    assert "from-black/85" in cover and "badge" not in cover
    plain = _section(_page(admin, client, "## H\n\nSection: Hero\n\n![P](/uploads/a.webp)\n\nWords.\n",
                           title="Hero still"), "hero")
    assert "from-black/85" in plain
    # Window means nothing to another section
    pricing = _page(admin, client, "## Plans\n\nSection: Pricing\nStyle: Window\n\n### Basic\n\nPrice: $1\n", title="No window")
    assert 'data-section="pricing"' in pricing and "shadow-xl" not in pricing


def test_hero_window_on_a_wide_page(admin, client):
    body = "Intro.\n\n[Buy](/join)\n\n" + WINDOW
    page = _page(admin, client, body, title="Wide window", page_width="wide")
    assert "Free and open source" in page and page.count("text-5xl sm:text-7xl") == 1 and "Style:" not in page


def test_the_editor_knows_the_windows_style():
    from soloblog import editor_config
    o = editor_config.block_options()
    hero = o["sections"]["hero"]
    assert [v[0] for v in hero["styles"]] == ["cover", "window"] and hero["styleNote"] == "Style can be Card, Cover, Window or Default"
    assert {"window", "card", "cover", "default"} <= set(hero["styleAccepts"])
    assert o["sections"]["pricing"]["styles"] == [] and o["sections"]["pricing"]["styleAccepts"] == ["card", "default"]
    # the shared Style has no Cover: only the kinds that take it list it
    assert o["options"]["Style"]["note"] == "Style can be Card or Default" and "window" not in o["options"]["Style"]["accepts"]
    assert sections.accepts("Style", "Window", "hero") and not sections.accepts("Style", "Window", "pricing")
    with pytest.raises(ValueError):
        sections.markdown("pricing", {"Style": "Window"})
    assert "Style: Window" in sections.markdown("hero", {"Style": "Window"})


def test_the_photo_storys_options(admin):
    from soloblog import editor_config
    o = editor_config.block_options()
    assert o["sections"]["photo_story"]["options"] == ["Width", "Style", "Heading", "Space", "Appear",
                                                      "First paragraph", "Pictures together",
                                                      "A line after a picture"]
    for name, default in (("First paragraph", "Big"), ("Pictures together", "Side by side"),
                          ("A line after a picture", "Beside it")):
        assert o["options"][name]["default"] == default and o["options"][name]["type"] == "choice"
    assert sections.pick("Pictures together", "One under another") == "stack"
    assert sections.pick("Pictures together", "default") == "" and sections.pick("First paragraph", "huge") == ""
    assert sections.REGISTRY["photo_story"]["width"] == "wide"
    # the option names fit a Key: line
    assert all(re.fullmatch(r"[A-Z][A-Za-z ]{0,24}", n) for n in sections.OPTIONS)


@pytest.mark.parametrize("kind", ["resume", "skills", "profile", "bios", "project_facts", "photo_story", "story", "hero"])
def test_huge_and_broken_input_never_raises(admin, client, kind):
    label = "Hero" if kind == "hero" else sections.REGISTRY[kind]["label"]
    style = "Style: Window\n" if kind == "hero" else ""
    junk = ("![x](" + "a" * 5000 + ")\n\n" + "### " + "word " * 2000 + "\n\n" + "- " + "long " * 3000 + "\n" * 2
            + "<b>unclosed <i>tags &amp; &bogus; \n\n> " + "q" * 5000 + "\n\n" + "Client: " + "v" * 500 + "\n"
            + "[" + "l" * 3000 + "](/x) [" + "m" * 10 + "](/y)\n\n" + "![a](/uploads/a.webp)\n" * 60)
    bodies = [f"## H\n\nSection: {label}\n{style}\n{junk}", f"## H\n\nSection: {label}\n{style}",
              f"## \n\nSection: {label}\n{style}\n### \n\n![]()\n\n###\n"]
    for n, body in enumerate(bodies):
        page = _page(admin, client, body, title=f"Junk {kind} {n}")
        assert 'data-section="' in page or kind == "hero" or n == 2


def test_new_sections_on_a_column_page_and_a_wide_one(admin, client):
    body = "Intro.\n\n" + "\n\n".join(sections.markdown(k) for k in ("resume", "skills", "bios", "project_facts", "photo_story"))
    for name, extra in (("column", {}), ("wide", {"page_width": "wide"})):
        page = _page(admin, client, body, title=f"All on a {name} page", **extra)
        for kind in ("skills", "bios", "project_facts", "photo_story"):
            assert f'data-section="{kind}"' in page, (name, kind)
        assert "Section:" not in page.split("<main")[1], name


def test_a_translation_holds_the_section_line_above_item_lines():
    # Project facts' lines written straight under the Section: line: the line that
    # names the kind is held out, the facts are words to translate
    from soloblog import translate
    from soloblog.render import render_post
    html, _ = render_post("## At a glance\n\nSection: Project facts\nWidth: Wide\nClient: Acme\nYear: 2026\n\nWords.\n")
    held_html, held = translate._hold_section_lines(html)
    assert "Section:" not in held_html and "Width" not in held_html and "Client: Acme" in held_html and len(held) == 1
    back = translate._restore_section_lines(held_html.replace("At a glance", "De un vistazo"), held)
    assert back.index("De un vistazo") < back.index("Section: Project facts") < back.index("Client: Acme")


STORY = ("## The tour\n\nSection: Story\n\nA line before the steps.\n\n### One\n\n![First picture](/uploads/a.webp)\n\n"
         "First words.\n\n### Two\n\n![Second picture](/uploads/b.webp)\n\nSecond words.\n\n[Go on](/two)\n\n"
         "### Three\n\nOnly words here.\n")


def test_a_story_reads_top_to_bottom_with_each_picture_once(admin, client):
    part = _section(_page(admin, client, STORY, title="A story"), "story")
    # a step each, in order, with its words and (if it has one) its picture and button
    assert part.count("data-story-step=") == 3 and part.count("data-story-words") == 3
    assert part.index("First words") < part.index("Second words") < part.index("Only words here")
    assert part.index('data-story-step="0"') < part.index('data-story-step="1"') < part.index('data-story-step="2"')
    assert 'href="/two"' in part and "Go on" in part and "A line before the steps." in part
    # a screen reader reads each picture once: the step's own keeps its alt, the held copies have none
    assert 'alt="First picture"' in part and 'alt="Second picture"' in part
    held = part[part.index('aria-hidden="true"'):]
    assert held.count('alt=""') == 2 and 'alt="First picture"' not in held
    # the step's own picture is only moved out of sight (sr-only) while the story is live - never display:none
    assert "group-data-[live]/story:sr-only" in part and "group-data-[live]/story:hidden" not in part
    # the empty space round the held picture, over the opening words, takes no press; beside the
    # words the picture is held at the top of its space, right under the heading
    assert "story-lift" not in part and "group-data-[active]/frame:pointer-events-auto" in part
    assert "@5xl:group-data-[live]/story:flex @5xl:items-start" in part
    # a step with no picture keeps the one before it held
    assert re.search(r'data-story-step="2"[^>]*data-story-pic="1"', part)
    assert re.search(r'data-story-step="0"[^>]*data-story-pic="0"', part)
    # nothing of its own shows as words, nothing is wired inline (the CSP blocks it)
    assert "Section:" not in part and ": Default" not in part and "onclick" not in part and "onscroll" not in part


def test_a_storys_phone_look_fades_into_the_pages_colour_and_words_are_the_themes(admin, client):
    part = _section(_page(admin, client, STORY, title="A story look"), "story")
    held = part[part.index("sticky"):]
    # the layer starts under the header and fills the rest of the screen; its fade is the page's colour, clear over the top
    sticky = re.search(r'<div[^>]*aria-hidden="true"[^>]*sticky[^>]*>', part).group(0)
    assert "top-[var(--story-top,var(--header-h,0px))]" in sticky and "h-[calc(100svh-var(--header-h,0px))]" in sticky
    # lighter than it was (2026-11-09): clear to 60%, half the page's colour by 76%, nearly whole at the foot
    assert "from-transparent from-60% via-base-200/55 via-76% to-base-200/90 to-95% @5xl:hidden" in held
    # the page's own background is base-200 (main), so the fade ends there - and nothing solid sits behind a picture
    assert "bg-base-100" not in held.split("data-story-mark")[0] and "bg-black/" not in held.replace("bg-black/45", "")
    steps = part.split("data-story-step=")[1:]
    assert len(steps) == 3
    # nothing of its own moves with the words: no band, no fade strip
    scrolling = part[:part.index("sticky")]
    assert "bg-linear" not in scrolling and "bg-black" not in scrolling
    words = re.findall(r'<div[^>]*data-story-words[^>]*>', part)
    assert len(words) == 3
    for tag in words:
        assert "bg-black" not in tag and "bg-transparent" not in tag and "group-data-[live]/story:pb-16" in tag
        # the theme's own text colour, not forced white; a soft shadow in the page's colour on a phone only
        assert "base-content:white" not in tag and "text-white" not in tag
        assert "group-data-[live]/story:text-shadow-lg" in tag and "group-data-[live]/story:text-shadow-base-200" in tag
        assert "@5xl:group-data-[live]/story:text-shadow-none" in tag
        assert "@5xl:group-data-[live]/story:max-w-md" in tag
    assert "white" not in part.replace("whitespace", "")
    assert "group-data-[live]/story:justify-end" in steps[0] and "@5xl:group-data-[live]/story:justify-center" in steps[0]
    # not live (no script, less motion): none of it applies
    assert not re.search(r'class="[^"]*(?<![\]\w:/-])(?:bg-black/85|text-shadow)', part)


def test_a_storys_picture_keeps_its_shape_on_the_page_with_its_credit_on_it(admin, client):
    from soloblog import pages
    out = {"ld": []}
    pages._render_story(out, None, {}, '<h2 id="one">One</h2><figure><img src="/uploads/a.webp" alt="A"><figcaption>'
                        'Photo by <a href="https://u.example">Someone</a></figcaption></figure><p>Words.</p>', [], False, None)
    part = pages.to_xml(out["body"])
    held = part[part.index("sticky"):]
    assert "aspect-[4/3]" not in part
    frame = re.search(r'<div[^>]*data-story-picture="0"[^>]*>', held).group(0)
    # 1rem under the header and a little in from the sides, over the page's own background (nothing solid)
    for cls in ("top-4", "inset-x-3", "@5xl:inset-0", "[--story-h:calc(100svh-var(--header-h,0px)-1rem)]", "group/frame"):
        assert cls in frame, cls
    assert "bg-base-100" not in frame and "bg-black" not in frame and "overflow-hidden" not in frame
    inner = held[held.index(frame):]
    wrap = re.search(r'<div[^>]*relative w-fit[^>]*>', inner).group(0)
    img = re.search(r'<img[^>]*>', inner).group(0)
    # a picture that's whole keeps its own shape, its corners and edge on the picture itself; a phone's landscape one fills the area
    for cls in ("max-w-full", "max-h-(--story-h)", "rounded-box", "group-data-[fit=cover]/frame:object-cover", "@5xl:shadow-xl"):
        assert cls in img, cls
    assert "group-data-[fit=cover]/frame:h-full" in wrap and "rounded" not in wrap
    # the credit is inside the picture's own wrapper, over the picture: at the top on a phone, at the foot beside the words
    assert inner.index("relative w-fit") < inner.index("Photo by") and "top-1.5 @5xl:top-auto @5xl:bottom-1.5" in inner
    # one step has nothing to count
    assert "data-story-mark" not in held
    pages._render_story(out, None, {}, '<h2>One</h2><p><img src="/uploads/a.webp" alt="A"></p><p>Words.</p>'
                        '<h2>Two</h2><p><img src="/uploads/b.webp" alt="B"></p><p>More.</p>', [], False, None)
    part = pages.to_xml(out["body"])
    held = part[part.index("sticky"):]
    # beside the words the markers sit before the picture in a space of their own, not over its edge;
    # a phone has no such space, so they're over the edge there, on the page's own colour
    marks = re.search(r'<div[^>]*order-first[^>]*>', held).group(0)
    assert "@5xl:static" in marks and "-left-6" not in marks and "@5xl:me-6" in marks
    assert "absolute end-5" in marks and "bg-base-200/70" in marks and "@5xl:bg-transparent" in marks
    assert "data-[active]:h-10 data-[active]:bg-primary" in held and "data-story-held" in part
    motion = Path("soloblog/js/motion.js").read_text(encoding="utf-8")
    # what tells a wide story from a phone's is the held layer's own shape - the markers show on both
    assert "offsetParent" not in motion and "getComputedStyle(held).display" in motion


def test_a_storys_pictures_fetch_the_right_size_and_in_turn(admin, client):
    from soloblog import pages
    img = ('<p><img src="/uploads/{0}.webp" srcset="/uploads/{0}.webp?w=400 400w, /uploads/{0}.webp 1600w" '
           'sizes="(min-width: 768px) 48rem, 100vw" alt="Picture {0}" loading="lazy"></p>')
    body = "".join(f'<h2 id="s{n}">Step {n}</h2>{img.format(n)}<p>Words.</p>' for n in range(2))
    out = {"ld": []}
    pages._render_story(out, None, {}, body, [], False, None)
    html = pages.to_xml(out["body"])
    # the step's own picture and its held copy are the same file at the same width, so one download
    sizes = pages.SCROLL_STORY_SIZES
    assert html.count(f'sizes="{sizes}"') == 4 and "100vw" in sizes and "61rem" in sizes and "48rem" not in html.replace(sizes, "")
    held = html[html.index('aria-hidden="true"'):]
    first, second = (f.split("<img")[1].split(">")[0] for f in held.split("data-story-picture=")[1:3])
    # the first held picture at once, the next when its turn nears
    assert "loading" not in first and 'loading="lazy"' in second


def test_a_storys_held_credit_links_are_out_of_the_tab_order(admin, client):
    from soloblog import pages
    body = ('<h2 id="one">One</h2><figure><img src="/uploads/a.webp" alt="A">'
            '<figcaption>Photo by <a href="https://u.example">Someone</a></figcaption></figure><p>Words.</p>')
    out = {"ld": []}
    pages._render_story(out, None, {}, body, [], False, None)
    html = pages.to_xml(out["body"])
    held = html[html.index('aria-hidden="true"'):]
    assert '<a tabindex="-1" href="https://u.example"' in held
    # its real link (in the step, where it is read) is untouched
    assert html.count('<a href="https://u.example"') == 1


def test_a_story_follows_its_width_and_default_is_a_missing_line(admin, client):
    base = _page(admin, client, STORY, title="Story width")
    default = _page(admin, client, STORY.replace("Section: Story\n", "Section: Story\nWidth: Default\nStyle: Default\n"),
                    title="Story width")
    assert base.count("w-screen") >= 1 and ": Default" not in default and default.count("w-screen") == base.count("w-screen")
    column = _page(admin, client, STORY.replace("Section: Story\n", "Section: Story\nWidth: Column\n"), title="Story column")
    assert column.count("w-screen") < base.count("w-screen") and 'data-section="story"' in column
    card = _section(_page(admin, client, STORY.replace("Section: Story\n", "Section: Story\nStyle: Card\n"),
                          title="Story card"), "story")
    assert "card border" in card and card.count("data-story-step=") == 3
    # in a card the fade and the words' shadow end in the card's colour; without one they're the page's, as ever
    assert "data-story-card" in card and "[--story-fade:" in card and "in-data-[story-card]:via-(--story-fade)/55" in card
    plain = _section(_page(admin, client, STORY, title="Story no card"), "story")
    assert " data-story-card" not in plain and "[--story-fade:" not in plain and "via-base-200/55" in plain
    named = _page(admin, client, STORY.replace("Section: Story", "Section: scroll story"), title="Story other name")
    assert named.count("data-story-step=") == 3


def test_a_story_with_no_pictures_one_step_fifty_steps_or_broken_words(admin, client):
    plain = _section(_page(admin, client, "## S\n\nSection: Story\n\n### A\n\nWords.\n\n### B\n\nMore words.\n",
                           title="Story no pictures"), "story")
    assert plain.count("data-story-step=") == 2 and "data-story-picture" not in plain and 'data-story-pic=""' in plain
    assert "More words." in plain
    one = _section(_page(admin, client, "## S\n\nSection: Story\n\n### Only\n\n![P](/uploads/a.webp)\n\nJust this.\n",
                         title="Story one step"), "story")
    assert one.count("data-story-step=") == 1 and "Just this." in one
    many = "## S\n\nSection: Story\n\n" + "".join(f"### Step {n}\n\n![P{n}](/uploads/a.webp)\n\nWords {n}.\n\n" for n in range(50))
    big = _section(_page(admin, client, many, title="Story fifty"), "story")
    assert big.count("data-story-step=") == 50 and big.count("data-story-picture=") == 50 and "Words 49." in big
    # no steps: the words under it show, and nothing when there are none either
    only = _page(admin, client, "## Lonely\n\nSection: Story\n\nJust a line.\n", title="Story no steps")
    assert "Just a line." in only and "data-story-step" not in only
    empty = _page(admin, client, "## Empty\n\nSection: Story\n", title="Story nothing")
    assert "data-story-step" not in empty
    broken = _page(admin, client, "## S\n\nSection: Story\n\n### <b>x\n\n![](\n\n[unclosed\n\n### \n\n![a]()\n", title="Story broken")
    assert "data-story" in broken


def test_the_story_script_watches_with_the_browser_never_a_scroll_listener():
    from soloblog import js
    script = js.read("motion.js")
    block = script[script.index("function stories()"):script.index("function drift()")]
    # live only where it works and motion is allowed - reduce motion and Animations off leave a plain stack
    assert "still()" in block and "IntersectionObserver" in block and "live(story, true)" in block
    assert "'scroll'" not in block and "getBoundingClientRect" not in block
    # the held picture stays still - it doesn't follow the mouse
    assert "function tilt(" not in script and "pointermove" not in block
    assert "start() { watch(); reveal(); stories(); drift(); }" in script


def test_the_stories_look_waits_for_the_script():
    # the layout, the held pictures and the white words all hang on data-live: without it, a plain stack
    from soloblog import pages
    for name in ("_SCROLL_STEP", "_SCROLL_WORDS", "_SCROLL_FRAME"):
        for cls in getattr(pages, name).split():
            if cls.startswith(("@5xl:", "group-data")) or "min-h-svh" in cls:
                # the frame is inside the held layer, which is hidden until live: its own @5xl: shape needs no gate
                assert "group-data-[live]/story" in cls or (name == "_SCROLL_FRAME" and cls.startswith("@5xl:")), cls
    css = Path("static/css/input.css").read_text(encoding="utf-8")
    assert "[data-story][data-live] [data-story-step]" in css and "story-scroll" in css
    # the words fade on a phone and a wide screen alike; where the browser can't tie them to the scroll, the step being read shows
    block = css[css.index("[custom-css: story-scroll]"):css.index("[custom-css: animations-off]")]
    assert "@keyframes story-words-phone" in block and "@keyframes story-words " in block
    assert "@supports not (animation-timeline: view())" in block and "[data-active] [data-story-words]" in block
    # the picture going shrinks as it fades (its frame's classes), and the page
    # settles on a step - only where a story is live
    # - and only where a finger scrolls: a mouse wheel's turn that stopped short of
    # halfway was pulled back to the step it left, so it took two to move one
    assert "story-settle" not in block
    assert "@media (pointer: coarse) {\n  html[data-story-snap] { scroll-snap-type: y proximity; }\n}" in block
    assert block.count("scroll-snap-type") == 1
    # beside the picture, the first and last steps are as tall as puts their words level with the
    # held picture's middle, so it's held from the first words reaching it until the last have -
    # worked out by MOTION_JS, else the picture's own space
    space = "calc(100svh-var(--story-top,var(--header-h,0px))-var(--footer-h,0px)+1rem)"
    for which in ("first", "last"):
        assert f"@5xl:group-data-[live]/story:{which}:min-h-[var(--story-{which}-h,{space})]" in pages._SCROLL_STEP
        assert f"'--story-{which}-h'" in Path("soloblog/js/motion.js").read_text(encoding="utf-8")
    assert "[data-story][data-live] [data-story-step] { scroll-snap-align: center; }" in block
    from soloblog import pages
    assert "scale-[0.96]" in pages._SCROLL_FRAME and "data-[active]:scale-100" in pages._SCROLL_FRAME
    assert "motion-reduce:scale-100" in pages._SCROLL_FRAME
    motion = Path("soloblog/js/motion.js").read_text(encoding="utf-8")
    # ...and only while a story fills the window: left on for the whole page, a
    # phone was pulled back to the last step from the section below the story
    assert "toggleAttribute('data-story-snap', inside)" in motion
    assert "setAttribute('data-story-snap'" not in motion
    assert "'0px 0px -100% 0px'" in motion and "'-100% 0px 0px 0px'" in motion


def test_a_storys_width_decides_how_far_it_spreads(admin, client):
    """Wide and Full looked the same - the Story capped its own content at
    one width. Now Wide fills the wide area and Full spreads further."""
    from conftest import save_post
    def page(width):
        body = (f"## A story\n\nSection: Story\nWidth: {width}\n\n### One\n\n![a](/uploads/a.webp)\n\nWords.\n\n"
                "### Two\n\n![b](/uploads/b.webp)\n\nMore.")
        return client.get(f"/post/{save_post(admin, title=f'Story {width}', body=body)}").text
    wide, full, column = page("Wide"), page("Full"), page("Column")
    cap = "@5xl:group-data-[live]/story:max-w-"
    assert cap + "full" in wide and cap + "[110rem]" not in wide
    assert cap + "[110rem]" in full and cap + "full" not in full
    assert cap + "7xl" in column


def test_a_story_lets_go_where_its_picture_ends(admin, client):
    # beside the words, the held box is the picture's height (--story-pic-h), not down to
    # the window's foot - so on a tall window the next section follows at its own gap,
    # not after a screen of empty box; the last step is the picture's height, as the first
    from soloblog import js, pages
    html = _page(admin, client, STORY, title="A story end")
    held = re.search(r'<div[^>]*data-story-held[^>]*>', html).group(0)
    assert "@5xl:h-[var(--story-pic-h," in held
    assert "var(--story-pic-h," in pages._STORY_HEAD and "var(--story-pic-h," in pages._STORY_BODY
    motion = js.read("motion.js")
    assert "setProperty('--story-pic-h'" in motion and "setProperty('--story-last-h', Math.round(picture)" in motion
