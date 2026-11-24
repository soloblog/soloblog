from soloblog import settings
from soloblog import translate
from conftest import save_post


def _fake(texts, target, source, html, s=None):
    # stands in for DeepL/Google/LibreTranslate - and tries to sneak a script in
    return [f"[{target}] {t}" + ("<script>alert(1)</script>" if html else "") for t in texts]


def test_translated_posts(admin, client, monkeypatch):
    monkeypatch.setattr(translate, "translate_texts", _fake)
    settings.set_many({"translate_provider": "deepl", "translate_api_key": "k:fx", "translate_languages": "es,ar"})
    try:
        slug = save_post(admin, title="Hello world post", summary="Greetings", body="## Part\n\nSome words.")
        translate.wait()
        es = client.get(f"/es/post/{slug}").text
        assert "[es] Hello world post" in es and 'lang="es"' in es.split("<head>")[0]
        assert "<script>alert(1)</script>" not in es
        # the banner speaks the page's own language
        assert "Traducción automática" in es and f'href="/post/{slug}"' in es
        assert "Los comentarios están en la entrada original" in es
        assert 'dir="rtl"' in client.get(f"/ar/post/{slug}").text.split("<head>")[0]

        original = client.get(f"/post/{slug}").text
        assert 'lang="en-US"' in original.split("<head>")[0]
        assert 'hreflang="es"' in original and f'/es/post/{slug}"' in original
        assert "Also in:" in original and "Español" in original
        # the same, for search engines: each language, and the original as the default
        head = original.split("</head>")[0]
        assert 'rel="alternate" hreflang="es" href="' in head and 'hreflang="x-default"' in head
        assert 'hreflang="en"' in client.get(f"/es/post/{slug}").text.split("</head>")[0]
        assert f"/es/post/{slug}</loc>" in client.get("/sitemap.xml").text

        # a language that isn't offered isn't there
        assert client.get(f"/de/post/{slug}").status_code == 404
        # changing the post makes its translation stale, and it's remade
        save_post(admin, slug=slug, title="Hello again post", summary="Greetings", body="New words.")
        translate.wait()
        assert "[es] Hello again post" in client.get(f"/es/post/{slug}").text
    finally:
        settings.set_many({"translate_provider": "", "translate_languages": ""})
    assert client.get(f"/es/post/{slug}").status_code == 404


def test_untranslated_page_shows_original_and_is_not_indexed(admin, client, monkeypatch):
    calls = []
    monkeypatch.setattr(translate, "queue_post", lambda slug, langs=None: calls.append((slug, langs)))
    settings.set_many({"translate_provider": "deepl", "translate_languages": "fr"})
    try:
        slug = save_post(admin, title="Not yet translated")
        html = client.get(f"/fr/post/{slug}").text
        assert "Not yet translated" in html and 'content="noindex"' in html and "Pas encore traduit" in html
        assert (slug, ["fr"]) in calls
    finally:
        settings.set_many({"translate_provider": "", "translate_languages": ""})


def test_languages_settings(admin):
    before = settings.get_all()
    try:
        r = admin.post("/admin/settings/url", headers={"hx-request": "true"}, data={
            "site_language": "fr", "translate_provider": "libretranslate", "translate_url": "http://lt:5000",
            "translate_languages": ["en", "de", "xx"]})
        assert "Saved" in r.text
        assert settings.get("site_language") == "fr" and settings.get("translate_languages") == "en,de"
        assert translate.targets() == ["en", "de"]
    finally:
        settings.set_many(before)
