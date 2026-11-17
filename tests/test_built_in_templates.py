"""The built-in templates, each rebuilt from sections and Post settings, and
the search-engine data a page gets from its sections."""
import json
from html.parser import HTMLParser
import re

import pytest

from soloblog import pages, post_templates, posts, sections, settings


def _own_lines(body):
    """[(the section's kind, [its lines up to the first blank one])] for each ## section in a template."""
    found = []
    for block in re.split(r"^## .*\n", body, flags=re.M)[1:]:
        lines = block.strip("\n").split("\n\n")[0].split("\n")
        if lines[0].startswith("Section:"):
            found.append((sections.NAMES[lines[0].partition(":")[2].strip().lower()], lines))
    return found


def _shown(key, **change):
    """A post made from a built-in template, as a visitor sees its main part."""
    t = post_templates.get(key)
    slug = posts.write(title=f"From {key}", body=t["body"], published=True, **t["settings"], **change)
    return slug


def _page(client, slug):
    return client.get(f"/post/{slug}")


def _data(html, kind):
    found = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    return [d for d in (json.loads(f) for f in found) if d.get("@type") == kind]


@pytest.fixture(autouse=True)
def _site_shows_the_default():
    before = {k: settings.get(k) for k in ("post_shows", "post_templates")}
    settings.set_many({"post_shows": "", "post_templates": "[]"})
    yield
    settings.set_many(before)


def test_every_template_has_its_shape():
    assert len(post_templates.BUILT_IN) == 31
    for key, (name, body) in post_templates.BUILT_IN.items():
        got = post_templates.get(key)
        assert got["name"] == name and got["body"] == body, key
        assert "layout" not in got, key
        assert set(got["settings"]) == set(post_templates.NO_SETTINGS), key
        assert {"tags", "summary", "cover", "pin"} <= set(got), key
        # a setting the page knows, in the form a page keeps it
        assert got["settings"] == post_templates.clean_settings(got["settings"]), key


def test_every_section_in_every_template_has_every_option_in_order():
    for key, (_, body) in post_templates.BUILT_IN.items():
        for kind, lines in _own_lines(body):
            expected = [name for name in sections.option_names(kind)]
            assert [line.partition(":")[0] for line in lines[1:]] == expected, (key, kind)
            for line in lines[1:]:
                name, _, value = line.partition(":")
                assert sections.accepts(name, value.strip(), kind), (key, line)
    # and the templates use sections for their parts
    kinds = {key: [k for k, _ in _own_lines(body)] for key, (_, body) in post_templates.BUILT_IN.items()}
    assert kinds["recipe"] == ["recipe_facts", "ingredients", "method"]
    assert kinds["resume"] == ["resume", "resume", "skills"]
    assert kinds["interview"] == ["interview"]
    assert kinds["profile"] == ["profile", "latest"]
    assert kinds["landing"][0] == "hero" and "pricing" in kinds["landing"] and kinds["landing"][-1] == "cta"
    assert kinds["project"] == ["project_facts", "photo_story", "previous_next"]
    assert kinds["business"] == ["details", "hours"]
    assert kinds["media-kit"] == ["bios"] and kinds["coming-soon"] == ["signup"]
    assert "Style: Window" in post_templates.BUILT_IN["landing"][1]


def test_every_template_renders_and_shows_no_option_line(admin, client):
    for key, (_, body) in post_templates.BUILT_IN.items():
        slug = _shown(key)
        r = _page(client, slug)
        assert r.status_code == 200, key
        main = r.text.split("<main")[1]
        assert "Section:" not in main and ": Default" not in main, key
        # a value the template means is read, not shown
        for line in re.findall(r"^(?:Width|Style): (?!Default).*$", body, re.M):
            assert line not in main, (key, line)
        for kind, _ in _own_lines(body):
            # Previous and next draws nothing while no other page shares the first tag
            assert f'data-section="{kind}"' in main or kind in ("hero", "previous_next"), (key, kind)
        assert "Traceback" not in r.text, key


def test_the_howto_steps_are_a_section_and_stay_in_the_contents(admin, client):
    body = post_templates.get("howto")["body"]
    assert [k for k, _ in _own_lines(body)] == ["steps"]
    main = _page(client, _shown("howto")).text.split("<main")[1]
    assert 'data-section="steps"' in main
    # the contents at the top still lists all three parts
    for anchor in ("what-youll-need", "steps", "if-something-goes-wrong"):
        assert f'href="#{anchor}"' in main, anchor


def test_the_settings_a_template_sets():
    get = post_templates.get
    assert get("wiki")["settings"]["in_wiki"] is True and get("now")["settings"]["remind_update"] is True
    assert get("slides")["settings"]["slides"] is True
    for key in ("profile", "landing"):
        assert get(key)["settings"]["title_style"] == "hidden", key
    assert get("coming-soon")["settings"]["title_style"] == "centre"
    for key in ("landing", "project", "photo-story", "portfolio", "pricing", "team", "shop"):
        assert get(key)["settings"]["page_width"] == "wide", key
    for key in ("project", "photo-story"):
        assert get(key)["settings"]["cover_width"] == "screen", key
    assert get("landing")["settings"]["section_space"] == "large"
    assert get("recipe")["settings"]["page_width"] == "" and get("recipe")["settings"]["toc_style"] == "off"
    assert get("docs")["settings"]["toc_style"] == "side" and get("howto")["settings"]["toc_style"] == "top"
    # Link post: its words say where Link to is
    assert get("link")["settings"]["link_url"] == "" and "Link to" in get("link")["body"]
    assert "nownownow.com" in get("now")["body"]


def test_what_a_template_shows_follows_the_site():
    def shown(key):
        return pages.shown_extras({"extras": post_templates.get(key)["settings"]["extras"], "pinned": 0,
                                     "pin_location": ""})

    assert post_templates.get("faq")["settings"]["extras"] == ""
    resume = shown("resume")
    assert "print" in resume and not resume & {"byline", "tags", "reactions", "share", "series", "related", "author"}
    assert "print" in shown("recipe") and shown("recipe") - {"print"} == pages.default_extras(False)
    assert shown("coming-soon") == set()
    assert not shown("landing") & {"byline", "related", "series", "sides"}
    assert "series" in shown("docs")
    # on a site that shows less, a template doesn't switch the rest back on
    settings.set_many({"post_shows": "byline,share"})
    assert shown("resume") == {"print"} and shown("docs") == {"byline", "share", "series"}
    assert post_templates.get("faq")["settings"]["extras"] == ""


def test_the_recipe_page_has_recipe_data_and_a_print_button(admin, client):
    r = _page(client, _shown("recipe"))
    recipe = _data(r.text, "Recipe")
    assert len(recipe) == 1 and recipe[0]["recipeIngredient"] and recipe[0]["recipeInstructions"]
    assert recipe[0]["recipeYield"] and recipe[0]["prepTime"] == "PT15M"
    assert 'data-onclick="printPage"' in r.text and "crossed" not in r.text.split("<main")[0]


def test_the_people_pages_have_person_data(admin, client):
    for key in ("resume", "profile"):
        found = _data(_page(client, _shown(key)).text, "ProfilePage")
        assert len(found) == 1 and found[0]["mainEntity"]["@type"] == "Person", key


def test_the_faq_page_has_faq_data(admin, client):
    found = _data(_page(client, _shown("faq")).text, "FAQPage")
    assert len(found) == 1 and len(found[0]["mainEntity"]) == 3


def test_the_business_page_has_business_data_once(admin, client):
    found = _data(_page(client, _shown("business")).text, "LocalBusiness")
    assert len(found) == 1
    assert found[0]["telephone"] and found[0]["email"] and found[0]["address"] and found[0]["openingHours"]


def _with(client, body, **change):
    slug = posts.write(title="A shop", body=body, published=True, **change)
    return _page(client, slug).text


def test_local_business_data_comes_from_the_sections(admin, client):
    details = sections.markdown("details", body="Phone: +1 555 0100\nEmail: hi@example.com")
    hours = sections.markdown("hours", body="Monday: 9am - 5pm\nTuesday: Closed")
    only_details = _data(_with(client, f"Words.\n\n{details}\n"), "LocalBusiness")
    assert len(only_details) == 1 and only_details[0]["telephone"] and "openingHours" not in only_details[0]
    only_hours = _data(_with(client, f"Words.\n\n{hours}\n"), "LocalBusiness")
    assert len(only_hours) == 1 and only_hours[0]["openingHours"] and "telephone" not in only_hours[0]
    both = _data(_with(client, f"Words.\n\n{details}\n\n{hours}\n"), "LocalBusiness")
    assert len(both) == 1 and both[0]["telephone"] and both[0]["openingHours"]
    # none, and no other section, tells search engines of a business
    assert not _data(_with(client, f"Words.\n\n{sections.markdown('faq')}\n"), "LocalBusiness")
    assert not _data(_with(client, "Plain words.\n"), "LocalBusiness")
    # a page made from the Small business template has it once, not twice
    business = post_templates.get("business")
    page = _with(client, business["body"], **business["settings"])
    assert len(_data(page, "LocalBusiness")) == 1
    # with no section there's nothing to say about a business
    assert not _data(_with(client, "Plain words.\n", **business["settings"]), "LocalBusiness")
    # on a wide page of sections too
    landing = post_templates.get("landing")["settings"]
    assert len(_data(_with(client, f"Words.\n\n{details}\n", **landing), "LocalBusiness")) == 1


def test_a_custom_template_has_the_same_shape(admin):
    key = f"mine-{post_templates.save('My own', 'a, b', 'Words.', summary='Why', cover='/uploads/x.png')}"
    got = post_templates.get(key)
    assert got["name"] == "My own" and "layout" not in got and got["tags"] == "a, b"
    assert got["summary"] == "Why" and got["cover"] == "/uploads/x.png"
    assert got["settings"] == post_templates.NO_SETTINGS
    assert post_templates.get("mine-nothing") is None and post_templates.get("nothing") is None


def test_a_custom_template_with_settings_at_its_top_loads_without_them(admin):
    """Settings kept anywhere but "settings" (a hand-edited or very old row)
    are ignored - the template still loads, with the defaults."""
    old = {"id": "abc123", "name": "From before", "layout": "recipe", "tags": "x", "body": "Old words.",
           "summary": "", "cover": "", "toc_style": "side", "title_style": "centre", "page_width": "wide",
           "slides": True, "in_wiki": False, "remind_update": False, "link_url": ""}
    older = {"id": "def456", "name": "Older still", "layout": "docs", "tags": "", "body": "Older words."}
    settings.set_many({"post_templates": json.dumps([old, older])})
    got = post_templates.get("mine-abc123")
    assert "layout" not in got and got["body"] == "Old words."
    assert got["settings"] == post_templates.NO_SETTINGS
    assert post_templates.get("mine-def456")["settings"] == post_templates.NO_SETTINGS
    # a template that keeps its settings together, with anything wrong in it dropped
    new = {"id": "ghi789", "name": "Together", "layout": "standard", "body": "Words.",
           "settings": {"toc_style": "off", "section_space": "large", "extras": "print,nonsense", "page_width": "huge",
                        "link_url": "javascript:alert(1)", "sides": "tags=left,bogus=right", "in_wiki": "yes"}}
    settings.set_many({"post_templates": json.dumps([new])})
    got = post_templates.get("mine-ghi789")["settings"]
    assert got == {**post_templates.NO_SETTINGS, "toc_style": "off", "section_space": "large", "extras": "print",
                   "sides": "tags=left", "in_wiki": True}
    # not a list of settings at all
    settings.set_many({"post_templates": json.dumps([{**new, "settings": "no"}])})
    assert post_templates.get("mine-ghi789")["settings"] == post_templates.NO_SETTINGS


class _Parts(HTMLParser):
    """Visible text of a page, and the text and pictures inside each data-section element."""

    def __init__(self):
        super().__init__()
        self.text, self.skip, self.stack, self.parts = [], 0, [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "style", "template"):
            self.skip += 1
        if tag in ("img", "svg", "input", "iframe", "video", "audio", "canvas", "form", "picture"):
            for open_ in self.stack:
                open_["media"] += 1
        if "data-section" in a:
            self.stack.append({"kind": a["data-section"], "tag": tag, "depth": 0, "text": [], "media": 0})
        elif self.stack and tag == self.stack[-1]["tag"]:
            self.stack[-1]["depth"] += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "template"):
            self.skip -= 1
        elif self.stack and tag == self.stack[-1]["tag"]:
            if self.stack[-1]["depth"]:
                self.stack[-1]["depth"] -= 1
            else:
                self.parts.append(self.stack.pop())

    def handle_data(self, data):
        if not self.skip:
            self.text.append(data)
            for open_ in self.stack:
                open_["text"].append(data)


def test_every_template_starts_a_page_that_shows_whole(admin, client):
    """Open the editor on each template, make a published page from it and
    read it as a visitor: it loads, every part has something in it and no setting is
    left showing as words."""
    keys = {name for kind in sections.REGISTRY for name in sections.option_names(kind)}
    for key, (_, body) in post_templates.BUILT_IN.items():
        assert admin.get(f"/admin/new?template={key}").status_code == 200, key
        for kind, lines in _own_lines(body):
            assert {line.partition(":")[0] for line in lines[1:]} <= set(sections.option_names(kind)), (key, kind)
        for name in re.findall(r"^Section: *(.*)$", body, re.M):
            assert name.strip().lower() in sections.NAMES, (key, name)
        r = client.get(f"/post/{_shown(key)}")
        assert r.status_code == 200 and "Traceback" not in r.text, key
        page = _Parts()
        page.feed(r.text.split("<main")[1])
        words = "\n".join(page.text)
        assert not re.search(rf"^\s*(?:Section|{'|'.join(keys)}):", words, re.M), key
        for part in page.parts:
            # Previous and next draws nothing while no other page shares its tag
            if part["kind"] != "previous_next":
                assert "".join(part["text"]).strip() or part["media"], (key, part["kind"])


def test_the_now_page_headings_have_a_sample_line_and_stay_plain():
    body = post_templates.get("now")["body"]
    for heading, line in (("Working on", "What you're building."), ("Reading", "A book or two."),
                          ("Learning", "Something new.")):
        assert f"## {heading}\n\n{line}" in body
    assert not _own_lines(body)


def test_the_docs_steps_are_a_section_and_stay_in_the_contents(admin, client):
    body = post_templates.get("docs")["body"]
    assert [k for k, _ in _own_lines(body)] == ["steps"]
    main = _page(client, _shown("docs")).text.split("<main")[1]
    assert 'data-section="steps"' in main
    for anchor in ("before-you-start", "steps", "check-it-worked", "next"):
        assert f'href="#{anchor}"' in main, anchor


def test_the_media_kit_sample_sentence_shows_what_to_replace():
    assert "[Your name] is a [what you do] based in [where]." in post_templates.get("media-kit")["body"]
