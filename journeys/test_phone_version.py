"""A picture with a phone version: the owner uploads a wide screenshot and a
phone one, gives the wide one the phone one as its phone version in Media,
and a reader sees the phone one on a phone and the wide one on a laptop -
and it changes by itself when the window is resized."""
from PIL import Image

from conftest import Window, publish


def _shows(w, which):
    """The post's picture is the 'phone' or the 'wide' file - given a moment
    for the browser to fetch what the page swapped in."""
    w.page.wait_for_function("(which) => { const i = document.querySelector('article img'); "
                             "return i && i.complete && i.currentSrc.includes('journey-' + which); }", arg=which)


def test_a_phone_shows_the_phone_version_and_a_laptop_the_wide_one(owner, browser, site, tmp_path):
    wide, phone_shot = tmp_path / "journey-wide.png", tmp_path / "journey-phone.png"
    Image.new("RGB", (1600, 900), (200, 60, 60)).save(wide)
    Image.new("RGB", (600, 1200), (60, 60, 200)).save(phone_shot)

    # upload both in Media
    owner.go("/admin/media")
    owner.page.set_input_files("input[name=image]", [str(wide), str(phone_shot)])
    owner.page.wait_for_load_state("networkidle")
    owner.page.wait_for_selector("span.link")
    names = owner.page.evaluate("() => [...document.querySelectorAll('span.link')].map(s => s.textContent.trim())")
    wide_name = next(n for n in names if n.startswith("journey-wide"))
    phone_name = next(n for n in names if n.startswith("journey-phone"))

    # the wide one's details: the Phone version field, a picture chosen from the picker, saved
    owner.page.locator(f"span.link:text-is('{wide_name}')").click()
    field = owner.page.locator("#media-phone-version")
    field.wait_for()
    assert field.input_value() == ""
    owner.page.locator("#media-phone-version ~ button:has-text('Pick')").click()
    owner.page.locator(f"#media-picker-dialog img[alt='{phone_name}']").first.click()
    assert field.input_value() == f"/uploads/{phone_name}"
    # picking marks the form changed, so Save shows
    owner.page.get_by_role("button", name="Save", exact=True).click()
    owner.page.wait_for_load_state("networkidle")
    owner.page.wait_for_timeout(500)
    owner.go("/admin/media")
    owner.page.locator(f"span.link:text-is('{wide_name}')").click()
    assert owner.page.locator("#media-phone-version").input_value() == f"/uploads/{phone_name}"

    # a post with the wide one in it
    url = publish(owner, "Phone version journey", f"![The app](/uploads/{wide_name})\n")

    # a phone: the phone version
    reader = Window(browser, site["base"], 375, 812, phone=True)
    reader.go(url)
    _shows(reader, "phone")
    assert not reader.page.evaluate("() => document.documentElement.scrollWidth > innerWidth")
    # turned sideways, on a laptop: the wide one - and back again
    reader.page.set_viewport_size({"width": 1280, "height": 800})
    _shows(reader, "wide")
    reader.page.set_viewport_size({"width": 375, "height": 812})
    _shows(reader, "phone")
    reader.close()

    # a wide screen straight away: the wide one
    laptop = Window(browser, site["base"], 1280, 800)
    laptop.go(url)
    _shows(laptop, "wide")
    laptop.close()


def _pick(owner, name, field, other):
    """Open a picture's details in Media and choose another upload for one of its version fields."""
    owner.go("/admin/media")
    owner.page.locator(f"span.link:text-is('{name}')").click()
    owner.page.locator(f"#{field}").wait_for()
    owner.page.locator(f"#{field} ~ button:has-text('Pick')").click()
    owner.page.locator(f"#media-picker-dialog img[alt='{other}']").first.click()
    owner.page.get_by_role("button", name="Save", exact=True).click()
    owner.page.wait_for_load_state("networkidle")
    owner.page.wait_for_timeout(500)


def _shows_token(w, token):
    w.page.wait_for_function("(token) => { const i = document.querySelector('article img'); "
                             "return i && i.complete && i.currentSrc.includes(token); }", arg=token)


def test_a_phone_picture_with_its_own_dark_version(owner, browser, site, tmp_path):
    """The phone picture gets a Dark mode version in its own details: a phone
    shows it while the page is dark, and the phone picture while it's light;
    a wide screen shows the wide picture's dark version, or the wide one."""
    # follow each reader's device, whatever an earlier journey left the site showing
    owner.go("/admin/settings?tab=style&panel=style-colours")
    owner.page.locator("label:has(input[name=theme][value=light])").click()
    owner.page.locator("label:has(input[name=theme_dark][value=dark])").click()
    owner.page.locator("input[name=theme_mode][value=auto]").check(force=True)
    owner.page.locator("form[hx-post='/admin/settings/style'] button[type=submit]").last.click()
    owner.page.wait_for_load_state("networkidle")
    owner.page.wait_for_timeout(800)
    shots = {"alpha-wide": (1600, 900), "bravo-phone": (600, 1200), "charlie-phonenight": (600, 1200),
             "delta-widenight": (1600, 900)}
    paths = []
    for n, (name, size) in enumerate(shots.items()):
        path = tmp_path / f"{name}.png"
        Image.new("RGB", size, (40 * n + 20, 60, 200 - 40 * n)).save(path)
        paths.append(str(path))
    owner.go("/admin/media")
    owner.page.set_input_files("input[name=image]", paths)
    owner.page.wait_for_load_state("networkidle")
    for key in shots:
        owner.page.locator(f"span.link:text-matches('^{key}')").first.wait_for()
    names = owner.page.evaluate("() => [...document.querySelectorAll('span.link')].map(s => s.textContent.trim())")
    found = {key: next(n for n in names if n.startswith(key)) for key in shots}

    _pick(owner, found["alpha-wide"], "media-phone-version", found["bravo-phone"])
    _pick(owner, found["alpha-wide"], "media-dark-version", found["delta-widenight"])
    _pick(owner, found["bravo-phone"], "media-dark-version", found["charlie-phonenight"])
    url = publish(owner, "Phone dark journey", f"![The app](/uploads/{found['alpha-wide']})\n")

    for width, height, scheme, token in ((375, 812, "light", "bravo-phone"), (375, 812, "dark", "charlie-phonenight"),
                                         (1280, 800, "light", "alpha-wide"), (1280, 800, "dark", "delta-widenight")):
        reader = Window(browser, site["base"], width, height, phone=width < 768)
        reader.page.emulate_media(color_scheme=scheme)
        reader.go(url)
        _shows_token(reader, token)
        assert not reader.page.evaluate("() => document.documentElement.scrollWidth > innerWidth")
        if width == 375:
            # turned over, on a laptop, and back again
            reader.page.set_viewport_size({"width": 1280, "height": 800})
            _shows_token(reader, "delta-widenight" if scheme == "dark" else "alpha-wide")
            reader.page.set_viewport_size({"width": 375, "height": 812})
            _shows_token(reader, token)
            # the device changes theme while it's open
            other = "light" if scheme == "dark" else "dark"
            reader.page.emulate_media(color_scheme=other)
            _shows_token(reader, "bravo-phone" if other == "light" else "charlie-phonenight")
        reader.close()
