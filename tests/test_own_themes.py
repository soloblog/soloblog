"""Custom colours: a daisyUI theme pasted from its theme generator
(themes.parse_theme), beside the built-in palettes - read, never copied."""
import json

from soloblog import settings, themes
from soloblog.demo import HARBOUR


def _clean():
    settings.set_many({"own_themes": "", "theme": settings.DEFAULTS["theme"],
                       "theme_dark": settings.DEFAULTS["theme_dark"]})


def test_the_generators_export_is_read():
    theme, problem = themes.parse_theme(HARBOUR)
    assert not problem and theme["name"] == "Harbour" and theme["scheme"] == "light"
    assert len(theme["values"]) == 28
    assert theme["values"]["--color-primary"].startswith("oklch(52.00%")
    assert theme["values"]["--radius-box"] == "1rem" and theme["values"]["--depth"] == "1"


def test_any_colour_way_becomes_oklch_and_missing_ones_come_from_daisyui():
    theme, _ = themes.parse_theme('--color-primary: #3366cc; --color-secondary: rgb(10 200 30);'
                                  '--color-accent: hsl(30, 80%, 50%); color-scheme: dark;')
    assert all(theme["values"][f"--color-{k}"].startswith("oklch(") for k in ("primary", "secondary", "accent"))
    # dark, so what it doesn't say is daisyUI's dark palette's
    assert theme["scheme"] == "dark" and "--color-base-100" in theme["values"] and len(
        [k for k in theme["values"] if k.startswith("--color-")]) == 20


def test_pasted_text_never_reaches_a_page():
    # only daisyUI's own values, each checked - nothing else gets through
    for attack in ('--color-primary: red;} body{display:none} [x]{--color-x: red;',
                   '--color-primary: url(https://evil.example/x.png);',
                   '--color-primary: oklch(50% 0.1 200)</style><script>alert(1)</script>;',
                   '@import url(https://evil.example/x.css); --color-primary: #fff;',
                   '--radius-box: expression(alert(1)); --color-primary: #fff;',
                   '--color-primary: #fff; --font-family: "Comic Sans";'):
        theme, _ = themes.parse_theme(attack)
        css = json.dumps(theme) if theme else ""
        for bad in ("display:none", "url(", "<", "script", "@import", "expression", "font-family", "evil"):
            assert bad not in css, (attack, bad)
    assert themes.parse_theme("x" * 30000)[1].startswith("That's too long")
    assert themes.parse_theme("not a theme at all")[1].startswith("No colours found")
    # a name is plain words
    theme, _ = themes.parse_theme('name: "<b>bold</b>"; --color-primary: #fff;')
    assert "<" not in theme["name"]


def test_add_use_and_delete_a_palette(admin, client):
    _clean()
    try:
        r = admin.post("/admin/themes/save", data={"css": HARBOUR, "name": ""}, headers={"hx-request": "true"})
        assert r.headers.get("hx-redirect", "").startswith("/admin/settings?tab=style")
        page = admin.get("/admin/settings?tab=style").text
        # first among the light palettes, by its own name; in the list
        assert 'value="own-1"' in page and ">Harbour<" in page and "Custom colo" in page
        assert page.index('name="theme" value="own-1"') < page.index('name="theme" value="light"')
        # every page carries its CSS, with its readable text lines
        settings.set_many({"theme": "own-1", "visitor_theme_switching": "1"})
        home = client.get("/").text
        assert 'data-theme="own-1"' in home and '[data-theme="own-1"]{color-scheme:light;' in home
        assert 'html[data-theme="own-1"]{--tx-' in home
        # readers' Colours menu has it, first after the defaults
        assert 'data-set-theme="own-1"' in home
        # what isn't CSS follows it too: share images and Giscus comments
        assert themes.theme_rgb("own-1")["primary"][2] > 150
        from soloblog import extcomments
        assert "oklch(52.00%" in extcomments.giscus_css("own-1")
        # deleted while in use: the default palette again
        admin.post("/admin/themes/delete", data={"key": "own-1"})
        assert settings.get("theme") == settings.DEFAULTS["theme"] and not themes.own_themes()
        assert '[data-theme="own-1"]' not in client.get("/").text
    finally:
        _clean()
        settings.set_many({"visitor_theme_switching": "0"})


def test_a_paste_that_isnt_a_theme_says_so_and_keeps_the_text(admin):
    _clean()
    r = admin.post("/admin/themes/save", data={"css": "hello", "name": "Mine"}, headers={"hx-request": "true"})
    assert "No colours found" in r.text and ">hello</textarea>" in r.text and 'value="Mine"' in r.text
    assert not themes.own_themes()


def test_ten_at_most_and_a_deleted_palette_falls_back(admin, client):
    _clean()
    try:
        theme, _ = themes.parse_theme(HARBOUR)
        keys = [themes.save_own(theme, f"Mine {i}") for i in range(themes.OWN_LIMIT + 1)]
        assert keys[-1] == "" and len(themes.own_themes()) == themes.OWN_LIMIT
        assert "That's 10 - delete one to add another" in admin.get("/admin/settings?tab=style").text
        # a palette set to one that's since gone (an old backup, a preset)
        settings.set_many({"own_themes": "", "theme": "own-3"})
        assert 'data-theme="light"' in client.get("/").text
    finally:
        _clean()


def test_a_preview_as_you_paste(admin):
    r = admin.post("/admin/themes/preview", data={"css": HARBOUR})
    assert "--color-primary:oklch(52.00%" in r.text and "btn-primary" in r.text
    assert "No colours found" in admin.post("/admin/themes/preview", data={"css": "nope"}).text
