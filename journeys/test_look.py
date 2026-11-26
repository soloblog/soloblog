"""The look: a palette chosen, one of your own added, and a style tried
then taken back."""
import re

from conftest import Window, publish

THEME = """@plugin "daisyui/theme" {
  name: "journey";
  color-scheme: "light";
  --color-base-100: oklch(98% 0.01 100);
  --color-primary: oklch(50% 0.2 20);
}"""


def _save_style(w):
    w.page.locator("form[hx-post='/admin/settings/style'] button[type=submit]").last.click()
    w.page.wait_for_load_state("networkidle")
    w.page.wait_for_timeout(800)


def test_choose_a_palette_add_your_own_and_undo_a_style(owner, browser, site):
    reader = Window(browser, site["base"])
    # a built-in palette, always shown
    owner.go("/admin/settings?tab=style&panel=style-colours")
    owner.page.locator("label:has(input[name=theme][value=cupcake])").click()
    owner.page.locator("input[name=theme_mode][value=light]").check(force=True)
    _save_style(owner)
    reader.go("/")
    assert reader.page.locator("html").get_attribute("data-theme") == "cupcake"
    # your own: pasted, previewed, saved, chosen
    owner.go("/admin/settings?tab=style&panel=style-colours")
    owner.page.get_by_role("button", name=re.compile(r"^Add colou?rs$")).click()
    owner.page.fill("#own-theme-new textarea[name=css]", THEME)
    owner.page.wait_for_timeout(900)
    assert owner.page.locator("#own-preview-new .btn-primary").count() == 1
    owner.page.locator("#own-theme-new button[type=submit]").click()
    owner.page.wait_for_load_state("networkidle")
    owner.page.wait_for_timeout(800)
    owner.page.locator("label:has(input[name=theme][value=own-1])").click()
    _save_style(owner)
    reader.go("/")
    assert reader.page.locator("html").get_attribute("data-theme") == "own-1"
    primary = reader.page.evaluate("() => getComputedStyle(document.documentElement).getPropertyValue('--color-primary')")
    assert primary.startswith("oklch(50.00%"), primary
    # a style, used and taken back with Undo it
    owner.go("/admin/settings?tab=style")
    before = reader.go("/") and reader.page.locator("main").inner_html()
    card = owner.page.locator("form[action='/admin/presets/apply']:has(input[name=key][value=notebook])")
    card.get_by_role("button", name="Use this").click()
    owner.page.locator("dialog[open]").get_by_role("button", name="Use this").click()
    owner.page.wait_for_load_state("networkidle")
    reader.go("/")
    assert reader.page.locator("main").inner_html() != before
    owner.go("/admin/settings?tab=style")
    owner.page.get_by_role("button", name="Undo it").click()
    owner.page.wait_for_load_state("networkidle")
    reader.go("/")
    assert reader.page.locator("html").get_attribute("data-theme") == "own-1"
    reader.close()


SPACED = """Words before the first section.

## Counts

Section: Numbers

### 3
things

## Across

Section: Numbers
Width: Wide

### 4
more things

## Welcome

Section: Hero
Style: Window

A line under the heading.

## Last

Section: Numbers
{own}

### 5
things
"""
# from the foot of a section to the top of the next one's heading: a wide
# screen, then a phone (px) - 0.5, 1.5 and 3 inches wide, scaled down on a phone
GAPS = {"small": (48, 32), "medium": (144, 80), "large": (288, 144)}
HEADINGS = ["Counts", "Across", "Welcome", "Last"]
MEASURE = """(names) => {
    const sections = [...document.querySelectorAll('article [data-section]')];
    const tops = names.map(n => [...document.querySelectorAll('article h2')]
        .find(h => h.textContent.includes(n)).getBoundingClientRect().top);
    return names.slice(1).map((_, i) => Math.round(tops[i + 1] - sections[i].getBoundingClientRect().bottom));
}"""


def _save_space(w):
    # a choice saves as it's made
    w.page.wait_for_load_state("networkidle")
    w.page.wait_for_timeout(800)


def _gaps(reader, path):
    gaps = {}
    for width in (1400, 375):
        reader.page.set_viewport_size({"width": width, "height": 900})
        reader.go(path)
        gaps[width] = reader.page.evaluate(MEASURE, HEADINGS)
    return gaps


def test_space_between_sections_is_as_big_as_it_says(owner, browser, site):
    path = publish(owner, "Spaced out", SPACED.format(own=""))
    reader = Window(browser, site["base"])
    for space, (wide, phone) in GAPS.items():
        owner.go("/admin/settings?tab=header&panel=header-width")
        owner.page.locator(f"input[name=section_space][value={space}]").check(force=True)
        _save_space(owner)
        gaps = _gaps(reader, path)
        for got, want, where in ((gaps[1400], wide, "wide"), (gaps[375], phone, "phone")):
            assert all(abs(g - want) <= 8 for g in got), f"{space} on a {where} screen: {got}, want {want}"
    # one section's own Space: sets the room above it, whatever the site says
    owner.go("/admin/settings?tab=header&panel=header-width")
    owner.page.locator("input[name=section_space][value=medium]").check(force=True)
    _save_space(owner)
    own =publish(owner, "Spaced by one", SPACED.format(own="Space: Large"))
    gaps = _gaps(reader, own)
    assert abs(gaps[1400][-1] - 288) <= 8 and abs(gaps[375][-1] - 144) <= 8, gaps
    assert all(abs(g - 288) > 100 for g in gaps[1400][:-1]), gaps
    reader.close()


def test_a_picture_card_opens_from_anywhere_on_it(owner, browser, site):
    """In the blog list, a post opens from anywhere on its card - its
    summary, not only its title - as on most blogs. Magazine's big card
    first, then its smaller ones."""
    first = publish(owner, "The older one", "A summary to click on, below the title.")
    newest = publish(owner, "The newest one", "The big card's summary, below the title.")
    owner.go("/admin/settings?tab=blog&panel=blog-layout")
    owner.page.locator("label:has(input[name=roll_style][value=magazine])").click()
    _save_space(owner)
    reader = Window(browser, site["base"])
    reader.go("/")
    reader.page.get_by_text("The big card's summary").first.click()
    reader.page.wait_for_url(f"**{newest}")
    reader.go("/")
    reader.page.get_by_text("A summary to click on").first.click()
    reader.page.wait_for_url(f"**{first}")
    reader.close()
    owner.go("/admin/settings?tab=blog&panel=blog-layout")
    owner.page.locator("label:has(input[name=roll_style][value=list])").click()
    _save_space(owner)
