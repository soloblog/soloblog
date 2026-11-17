"""A scroll story: the owner adds one from the / menu, and a reader scrolls
through it - on a phone each picture fills the screen below the header,
clear at the top and fading into the page's colour at the foot, with the
words scrolling over it; on a wide screen the picture is held beside them,
whole, with the step markers in a space of their own."""
import re

from conftest import Window, save

FRAMES = "[data-story-picture]"


def _opacities(w):
    return w.page.evaluate("() => [...document.querySelectorAll('[data-story-picture]')]"
                           ".map(f => Number(getComputedStyle(f).opacity))")


def _scroll_to_step(w, n):
    w.page.evaluate("""(n) => { const s = document.querySelectorAll('[data-story-step]')[n].getBoundingClientRect();
        scrollTo(0, scrollY + s.top + s.height / 2 - innerHeight / 2); }""", n)
    # the fade takes 0.7 seconds
    w.page.wait_for_timeout(1100)


def _story_post(owner):
    owner.go("/admin/new")
    owner.page.locator("[placeholder=Title], input.text-2xl").first.fill("Story journey")
    owner.page.locator(".CodeMirror").first.click()
    owner.page.keyboard.type("A tour.")
    owner.page.keyboard.press("Enter")
    owner.page.keyboard.press("Enter")
    owner.page.keyboard.type("/story")
    owner.page.wait_for_timeout(400)
    owner.page.keyboard.press("Enter")
    owner.page.wait_for_timeout(400)
    text = owner.page.evaluate("() => window._activeEasyMDE.value()")
    assert "Section: Story" in text and text.count("### ") == 3
    owner.page.evaluate("() => { togglePostSettings(true); document.querySelectorAll('#post-settings-panel "
                        "details[data-panel]').forEach(d => d.open = true); }")
    owner.page.locator("#post-settings-panel input[name=published]").check()
    # no contents beside the post: a section stays in the column while one sits there
    owner.page.evaluate("() => { const s = document.querySelector('#post-settings-panel select[name=toc_style]'); "
                        "s.value = 'off'; s.dispatchEvent(new Event('change', {bubbles: true})); }")
    save(owner)
    return owner.page.url.rstrip("/").rsplit("/", 1)[-1]


def test_a_story_changes_its_picture_as_the_words_scroll(owner, browser, site):
    slug = _story_post(owner)

    # a phone: each picture fills the screen under the header, a fade on it that stays still, the words scrolling over it
    phone = Window(browser, site["base"], 375, 812, phone=True)
    phone.go(f"/post/{slug}")
    assert phone.page.locator("[data-story][data-live]").count() == 1
    assert phone.page.locator("[data-story-step]").count() == 3
    header = phone.page.evaluate("() => parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--header-h'))")
    assert header > 0
    for n in range(3):
        _scroll_to_step(phone, n)
        assert _opacities(phone) == [1.0 if i == n else 0.0 for i in range(3)], n
        layer = phone.page.locator("[data-story] [aria-hidden=true].sticky").bounding_box()
        assert abs(layer["y"] - header) < 1 and abs(layer["height"] - (812 - header)) < 1 and layer["width"] == 375, layer
        heading = phone.page.locator("[data-story-step]").nth(n).locator("h3")
        # the theme's own text colour (dark in the light theme), not white
        assert phone.page.evaluate("(h) => getComputedStyle(h).color", heading.element_handle()) != "rgb(255, 255, 255)"
        # the words of the step being read sit in the bottom half, with no band of their own
        words = phone.page.locator("[data-story-words]").nth(n).bounding_box()
        assert words["y"] + words["height"] / 2 > 812 / 2 and words["y"] + words["height"] <= 812 + 1, words
        band = phone.page.evaluate("(w) => getComputedStyle(w).backgroundColor", phone.page.locator("[data-story-words]").nth(n).element_handle())
        assert band == "rgba(0, 0, 0, 0)", band
        # the picture sits 1rem under the header, in from the sides, its corners rounded, over the page's own background
        pic = phone.page.locator("[data-story-picture]").nth(n).locator("img").bounding_box()
        assert abs(pic["y"] - (header + 16)) < 1 and pic["x"] >= 11 and pic["x"] + pic["width"] <= 375 - 11, pic
        look = phone.page.evaluate("""(i) => { const s = getComputedStyle(i); const f = i.closest('[data-story-picture]');
            return [parseFloat(s.borderTopLeftRadius) > 0, getComputedStyle(f.parentElement).backgroundColor,
                    getComputedStyle(document.querySelector('main')).backgroundColor]; }""",
                                  phone.page.locator("[data-story-picture]").nth(n).locator("img").element_handle())
        assert look[0] and look[1] == "rgba(0, 0, 0, 0)", look
        # the words of the step being read are fully clear, the others' faded away
        fades = phone.page.evaluate("() => [...document.querySelectorAll('[data-story-words]')].map(e => Number(getComputedStyle(e).opacity))")
        assert fades[n] == 1 and sum(fades) == 1, fades
        # the top of the picture isn't covered: the layer over it is clear there, the page's colour at the foot
        fade = phone.page.evaluate("""() => { const el = document.querySelector(
            '[data-story] [aria-hidden=true].sticky > div > div:last-child'); const s = getComputedStyle(el);
            const probe = document.createElement('i'); probe.style.color = 'var(--color-base-100)';
            document.body.appendChild(probe); const base = getComputedStyle(probe).color; probe.remove();
            return [s.backgroundImage, base]; }""")
        stops = re.findall(r"(\d+)%", fade[0])
        assert stops == ["60", "76", "95"] and "0, 0, 0" not in fade[0].replace("0, 0, 0, 0", ""), fade
        # it ends in the colour of the page behind it (main), so no band shows where it meets the page
        assert phone.page.evaluate("() => { const p = document.createElement('i'); p.style.color = 'var(--color-base-200)'; "
                                   "document.body.appendChild(p); const c = getComputedStyle(p).color; p.remove(); "
                                   "return c === getComputedStyle(document.querySelector('main')).backgroundColor; }")
    # the fade doesn't move as the words do
    _scroll_to_step(phone, 1)
    dark = phone.page.locator("[data-story] [aria-hidden=true].sticky > div > div:last-child")
    words = phone.page.locator("[data-story-words]").nth(1)
    layer_top, words_top = dark.bounding_box()["y"], words.bounding_box()["y"]
    phone.page.evaluate("() => scrollBy(0, 150)")
    phone.page.wait_for_timeout(300)
    assert abs(dark.bounding_box()["y"] - layer_top) < 1 and abs(layer_top - header) < 1
    # they drift a little as they fade, so a bit more than the scroll
    assert 150 - 5 < words_top - words.bounding_box()["y"] < 150 + 40, (words_top, words.bounding_box())
    assert not phone.page.evaluate("() => document.documentElement.scrollWidth > innerWidth")
    phone.close()

    # a wide screen: the words in a column, the picture held beside them, changing with the step
    wide = Window(browser, site["base"], 1400, 900)
    wide.go(f"/post/{slug}")
    story = wide.page.locator("[data-story][data-live]")
    assert story.count() == 1
    # it starts right under what's above it: the picture is held at the top of its space, so none
    # of that space's empty top is left under the heading
    wide.page.wait_for_function("() => { const i = document.querySelector('[data-story-picture] img'); "
                                "return i.complete; }")
    wide.page.wait_for_timeout(300)
    gap = wide.page.evaluate("""() => { const s = document.querySelector('[data-story]'), r = (e) => e.getBoundingClientRect();
        const before = [...document.querySelectorAll('main h1, main h2, main p')].filter(
            (e) => !s.contains(e) && s.compareDocumentPosition(e) & Node.DOCUMENT_POSITION_PRECEDING).pop();
        return r(s.querySelector('[data-story-picture] img')).top - r(before).bottom; }""")
    assert 0 <= gap < 120, gap
    for n in range(3):
        _scroll_to_step(wide, n)
        assert _opacities(wide) == [1.0 if i == n else 0.0 for i in range(3)], n
        held = wide.page.locator("[data-story] [aria-hidden=true].sticky").bounding_box()
        step = wide.page.locator("[data-story-step]").nth(n).bounding_box()
        # beside the words, not over them
        assert held["x"] >= step["x"] + step["width"], (held, step)
        # the markers have a space of their own: not over the picture's edge, none of it cropped
        marks = wide.page.locator("[data-story-mark]").nth(0).locator("xpath=..").bounding_box()
        pic = wide.page.locator("[data-story-picture]").nth(n).locator("img")
        box = pic.bounding_box()
        assert marks["x"] + marks["width"] <= box["x"] - 8, (marks, box)
        assert box["y"] >= held["y"] - 1 and box["y"] + box["height"] <= held["y"] + held["height"] + 1, (box, held)
        # the whole picture, in its own shape
        natural = wide.page.evaluate("(i) => i.naturalWidth ? i.naturalWidth / i.naturalHeight : 0", pic.element_handle())
        assert not natural or abs(box["width"] / box["height"] - natural) < 0.02, (box, natural)
    # the picture stays still under a mouse - it doesn't tilt toward it
    _scroll_to_step(wide, 0)
    held = wide.page.locator("[data-story] [aria-hidden=true].sticky").bounding_box()
    wide.page.mouse.move(held["x"] + 20, held["y"] + 20)
    wide.page.mouse.move(held["x"] + held["width"] - 20, min(held["y"] + held["height"], 900) - 20, steps=4)
    wide.page.wait_for_timeout(500)
    transform = wide.page.evaluate(
        "() => getComputedStyle(document.querySelector('[data-story-picture][data-active] img')).transform")
    assert transform == "none", transform
    # the heading and the picture are held together: the heading just under the header, the picture
    # under it the gap every section's heading has above what it introduces, and the two let go
    # at the same moment, so the heading never stays behind over what follows
    header = wide.page.evaluate("() => parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--header-h'))")
    heading = wide.page.locator("[data-story-head]")
    shown = "[data-story-picture][data-active] img"

    def places():
        hb = heading.bounding_box()
        pb = wide.page.locator(shown).bounding_box()
        return {"head": hb["y"], "head_bottom": hb["y"] + hb["height"], "pic": pb["y"],
                "held": wide.page.locator("[data-story] [aria-hidden=true].sticky").bounding_box()["y"]}

    def scroll_story(by):
        wide.page.evaluate("""(by) => { const r = document.querySelector('[data-story-wrap]').getBoundingClientRect();
            scrollTo(0, scrollY + r.top + by); }""", by)
        wide.page.wait_for_timeout(400)

    # at rest, before it plays, the heading scrolls with the page and the picture is that gap below it
    wide.page.evaluate("() => scrollTo(0, 0)")
    wide.page.wait_for_timeout(300)
    rest = places()
    gap = rest["pic"] - rest["head_bottom"]
    assert 8 < gap < 120 and rest["head"] > header + 1, (rest, header)
    total = wide.page.evaluate("() => document.querySelector('[data-story-wrap]').getBoundingClientRect().height")
    # while it plays: always the same gap, the heading at the header's foot, never over the picture
    for by in (200, total * 0.2, total * 0.35, total * 0.5):
        scroll_story(by)
        now = places()
        assert abs(now["pic"] - now["head_bottom"] - gap) <= 2, (by, now, gap)
        assert abs(now["head"] - header) <= 1 and now["head_bottom"] <= now["pic"], (by, now, header)
    # the heading's place doesn't change as the words scroll past
    before = places()
    wide.page.evaluate("() => scrollBy(0, 120)")
    wide.page.wait_for_timeout(300)
    assert places() == before, (places(), before)
    # at the end they go together: each moves by the same amount, the gap stays, and the heading is
    # gone from under the header when the picture is, not before or after
    wide.page.evaluate("() => scrollTo(0, document.documentElement.scrollHeight)")
    wide.page.wait_for_timeout(400)
    last = places()
    assert last["head"] < header - 1, last
    assert abs(last["pic"] - last["head_bottom"] - gap) <= 2, (last, gap)
    steps = []
    wide.page.evaluate("() => scrollTo(0, document.documentElement.scrollHeight - 700)")
    wide.page.wait_for_timeout(300)
    for _ in range(3):
        a = places()
        wide.page.evaluate("() => scrollBy(0, 90)")
        wide.page.wait_for_timeout(250)
        b = places()
        steps.append((a, b))
    for a, b in steps:
        assert abs((a["head"] - b["head"]) - (a["pic"] - b["pic"])) <= 1, (a, b)
        assert b["head_bottom"] <= b["pic"], b
    wide.close()

    # with less motion asked for, nothing is held or fades: a plain stack, every picture and its words
    still = Window(browser, site["base"], 375, 812, phone=True)
    still.context.close()
    still.context = browser.new_context(viewport={"width": 375, "height": 812}, base_url=site["base"],
                                        reduced_motion="reduce", is_mobile=True, has_touch=True)
    still.page = still.context.new_page()
    still.errors = []
    still.page.on("pageerror", lambda e: still.errors.append(str(e)))
    still.go(f"/post/{slug}")
    assert still.page.locator("[data-story][data-live]").count() == 0
    assert still.page.locator("[data-story] [aria-hidden=true].sticky").is_hidden()
    pictures = still.page.locator("[data-story-real] img")
    assert pictures.count() == 3 and all(pictures.nth(i).is_visible() for i in range(3))
    assert not still.page.evaluate("() => document.documentElement.scrollWidth > innerWidth")
    still.close()
