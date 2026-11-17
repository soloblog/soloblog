from pathlib import Path
import ast
import glob
import json
import os
import re

from soloblog import i18n
from soloblog import settings
from soloblog import translate

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(ROOT, "soloblog")


def _keys_in_code() -> set:
    """Every literal the code hands to i18n.t() or i18n.plural() - plus
    the few it passes through a variable (error pages, reactions, a
    self-hosted comment server's name)."""
    from soloblog import extcomments
    from soloblog import reactions
    from soloblog import ui
    keys = set(i18n.SCRIPT_WORDS)
    keys |= {text for title, message, _ in ui.ERROR_PAGES.values() for text in (title, message)}
    keys |= set(ui.SITE_ROW_WORDS.values())
    keys |= {label for _, label in reactions.CHOICES.values()}
    keys |= {host for _, _, host, _ in extcomments.SYSTEMS.values() if host.startswith("your ")}
    for path in glob.glob(os.path.join(PKG, "**", "*.py"), recursive=True):
        for node in ast.walk(ast.parse(Path(path).read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                    and getattr(node.func.value, "id", None) == "i18n" and node.args:
                args = node.args[:1] if node.func.attr == "t" else node.args[1:3] if node.func.attr == "plural" else []
                for a in args:
                    for c in ([a] if isinstance(a, ast.Constant) else [a.body, a.orelse] if isinstance(a, ast.IfExp)
                              else a.value.values if isinstance(a, ast.Subscript) and isinstance(a.value, ast.Dict)
                              else []):
                        if isinstance(c, ast.Constant) and isinstance(c.value, str):
                            keys.add(c.value)
    return keys


def test_every_language_has_a_locale_file():
    for code in translate.LANGUAGES:
        if code != "en":
            assert os.path.exists(os.path.join(PKG, "locales", f"{code}.json")), code


def test_locale_files_are_safe_and_complete():
    known = _keys_in_code()
    ph = lambda s: set(re.findall(r"\{(\w+)\}", s))  # noqa: E731
    for path in glob.glob(os.path.join(PKG, "locales", "*.json")):
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        name = os.path.basename(path)
        assert len(d["_months"]) == 12 and len(d["_months_full"]) == 12, name
        assert ph(d["_date"]) == {"day", "month", "year"}, name
        for k, v in d.items():
            if k.startswith("_"):
                continue
            base = k.split("|")[0]
            assert base in known, (name, k)  # a leftover from a string that changed
            assert not ph(v) - ph(base), (name, k)  # a placeholder the code never fills in
        missing = known - set(d)
        assert not missing, (name, sorted(missing)[:5])


def test_plural_forms():
    i18n.use("ru")
    try:
        assert i18n.plural(1, "{n} day ago", "{n} days ago") == "1 день назад"
        assert i18n.plural(3, "{n} day ago", "{n} days ago") == "3 дня назад"
        assert i18n.plural(5, "{n} day ago", "{n} days ago") == "5 дней назад"
        assert i18n.plural(21, "{n} day ago", "{n} days ago") == "21 день назад"
        # Arabic counts 3-10 parts as أجزاء, 11 and up as جزءًا
        i18n.use("ar")
        series = ("A series in {n} part.", "A series in {n} parts.")
        assert "أجزاء" in i18n.plural(3, *series)
        assert "جزءًا" in i18n.plural(11, *series)
    finally:
        i18n.use("en")


def test_the_site_speaks_its_language(admin, client):
    from conftest import save_post
    slug = save_post(admin, title="Auf Deutsch", body="Hallo.")
    settings.set_many({"site_language": "de"})
    try:
        html = client.get(f"/post/{slug}").text
        assert "Kommentare" in html and "Min. Lesezeit" in html and "Teilen" in html
        assert "data-i18n=" in html and "Kopieren" in html
        assert re.search(r"\d+\. (Jan\.|Feb\.|März|Apr\.|Mai|Juni|Juli|Aug\.|Sept\.|Okt\.|Nov\.|Dez\.) \d{4}", html)
        assert "Seite nicht gefunden" in client.get("/no-such-page").text
        # the admin stays in English
        assert "Comments" in admin.get("/admin/comments").text
    finally:
        settings.set_many({"site_language": "en"})
    assert "Comments" in client.get(f"/post/{slug}").text


def test_english_spelling(admin, client):
    from soloblog import i18n, settings
    before = {k: settings.get(k) for k in ("site_language", "english_spelling", "visitor_theme_switching")}
    try:
        settings.set_many({"site_language": "en", "english_spelling": "au", "visitor_theme_switching": "1"})
        home = client.get("/").text
        assert '<html lang="en-AU"' in home.replace("  ", " ") or 'lang="en-AU"' in home
        assert 'data-tip="Colours"' in home
        appearance = admin.get("/admin/settings?tab=style").text
        assert re.search(r">\s*Colours\s*<", appearance) and "Light palette" in appearance
        assert "Centred" in admin.get("/admin/settings?tab=blog").text
        settings.set_many({"english_spelling": "us"})
        home = client.get("/").text
        assert 'lang="en-US"' in home and 'data-tip="Colors"' in home
        appearance = admin.get("/admin/settings?tab=style").text + admin.get("/admin/settings?tab=blog").text
        assert re.search(r">\s*Colors\s*<", appearance) and "Centered" in appearance and "Colour" not in appearance
        # Help, written in British English, reads American on an American site
        assert "colour" not in admin.get("/admin/help?tab=design").text.lower().split('data-toc')[-1]
        # saved from Settings, and only a known spelling
        admin.post("/admin/settings/address", headers={"hx-request": "true"},
                   data={"site_language": "en", "english_spelling": "gb",
                         "declared_fields": "site_language,english_spelling"})
        assert settings.get("english_spelling") == "gb"
        admin.post("/admin/settings/address", headers={"hx-request": "true"},
                   data={"english_spelling": "klingon", "declared_fields": "english_spelling"})
        assert settings.get("english_spelling") == "us"
        # another language: no spelling games
        settings.set_many({"site_language": "de"})
        assert 'data-tip="Farben"' in client.get("/").text
    finally:
        settings.set_many(before)
    # dates: British and Australian day first
    i18n.use("en", "gb")
    assert i18n.date_format() == "{day} {month} {year}"
    i18n.use("en", "us")
    assert i18n.date_format() == "{month} {day}, {year}" and i18n.spell("a grey Centre") == "a gray Center"
    i18n.use("en", "us")


def test_visitors_see_both_defaults(client):
    from soloblog import settings
    keys = ("theme", "theme_dark", "theme_mode", "visitor_theme_switching", "site_language")
    before = {k: settings.get(k) for k in keys}
    try:
        settings.set_many({"theme": "silk", "theme_dark": "dim", "theme_mode": "auto",
                           "visitor_theme_switching": "1", "site_language": "en"})
        menu = client.get("/").text.split('id="nav-theme-menu"')[1]
        assert "light default" in menu and "dark default" in menu
        # the defaults come first, light then dark
        assert menu.index('data-set-theme="silk"') < menu.index('data-set-theme="dim"') < \
            menu.index('data-set-theme="cupcake"')
        # always light: only the light one is the default
        settings.set_many({"theme_mode": "light"})
        menu = client.get("/").text.split('id="nav-theme-menu"')[1]
        assert "dark default" not in menu and ">default</span>" in menu
        # in the visitor's language
        settings.set_many({"site_language": "de", "theme_mode": "auto"})
        menu = client.get("/").text.split('id="nav-theme-menu"')[1]
        assert "Standard hell" in menu and "Standard dunkel" in menu and "(default)" not in menu
    finally:
        settings.set_many(before)


def test_english_spelling_files_are_safe():
    known = _keys_in_code()
    for path in glob.glob(os.path.join(PKG, "locales", "english", "*.json")):
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        for k, v in d.items():
            if k == "_date":
                assert set(re.findall(r"\{(\w+)\}", v)) == {"day", "month", "year"}
                continue
            assert k.split("|")[0] in known, (path, k)


def test_emails_to_visitors_are_in_the_sites_language(monkeypatch):
    """A newsletter confirmation, a comment confirmation and a reply email
    go out in the site's language - even sent from the admin, which is
    English (i18n.in_site_language)."""
    from soloblog import i18n, mail, newsletter, settings
    sent = []
    monkeypatch.setattr(mail, "send_email", lambda to, subject, body, **kw: sent.append((subject, body)) or True)
    before = settings.get("site_language")
    try:
        settings.set_many({"site_language": "fr"})
        i18n.use("en")  # as on an admin page
        newsletter.send_confirm("reader@example.com", "tok", {"site_title": "Mon blog"})
        subject, body = sent[-1]
        assert subject == "Confirmez votre abonnement à Mon blog" and "Confirmez votre adresse e-mail" in body
        footer = newsletter.post_email({"title": "Bonjour", "slug": "x", "summary": "Un mot", "visibility": "public",
                                        "password": None, "published": 1}, {"site_title": "Mon blog", "newsletter_full": "0"},
                                       "tok")
        assert "Lire sur Mon blog" in footer and "Se désabonner" in footer
        assert i18n.lang() == "en"  # the page's own language is left as it was
    finally:
        settings.set_many({"site_language": before})
