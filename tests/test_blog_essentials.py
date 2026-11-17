import json
import re
import xml.etree.ElementTree as ET

from soloblog import settings
from conftest import save_post


def _ld(html, kind):
    blocks = [json.loads(b) for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]
    return next((b for b in blocks if b["@type"] == kind), None)


def test_article_structured_data(admin, client):
    slug = save_post(admin, title="Structured </script> post", summary="About data.", tags="seo, data",
                     cover_image="/uploads/cover.webp")
    html = client.get(f"/post/{slug}").text
    data = _ld(html, "BlogPosting")
    assert data["headline"] == "Structured </script> post"
    assert data["description"] == "About data."
    assert data["image"].endswith("/uploads/cover.webp") and data["image"].startswith("http")
    assert data["keywords"] == ["seo", "data"]
    assert "</script> post" not in html.split("application/ld+json")[1].split("</script>")[0]


def test_titles_use_the_site_title_setting(client):
    settings.set_many({"site_title": "Renamed Blog"})
    try:
        assert "<title>Tags — Renamed Blog</title>" in client.get("/tags").text
    finally:
        settings.set_many({"site_title": "My Blog"})


def test_tag_pages_paginate_and_encode(admin, client):
    settings.set_many({"posts_per_page": "2"})
    try:
        for i in range(3):
            save_post(admin, title=f"Paged tag post {i}", tags="c#, paging")
        def shown(html):
            return len(set(re.findall(r'/post/(paged-tag-post-\d[\w-]*)', html)))
        first = client.get("/tag/paging").text
        assert shown(first) == 2 and 'href="/tag/paging?page=2"' in first
        assert shown(client.get("/tag/paging?page=2").text) == 1
        # "#" in a tag is encoded in its links, and the page finds it
        assert 'href="/tag/c%23"' in first
        assert shown(client.get("/tag/c%23").text) == 2
    finally:
        settings.set_many({"posts_per_page": "10"})


def test_tags_index_and_archive(admin, client):
    save_post(admin, title="Indexed post", tags="indexing")
    tags = client.get("/tags").text
    assert 'href="/tag/indexing"' in tags
    archive = client.get("/archive").text
    assert "Indexed post" in archive and "<h2" in archive


def test_feeds(admin, client):
    slug = save_post(admin, title="Feed post", body="Hello ![](/uploads/x.webp)", tags="feeds", summary="Sum")
    rss = client.get("/rss")
    root = ET.fromstring(rss.content)
    item = next(i for i in root.iter("item") if i.findtext("title") == "Feed post")
    assert re.match(r"\w{3}, \d{2} \w{3} \d{4}", item.findtext("pubDate"))
    content = item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded")
    assert 'src="http' in content and "/uploads/x.webp" in content

    tag_rss = ET.fromstring(client.get("/tag/feeds/rss").content)
    assert [i.findtext("title") for i in tag_rss.iter("item")] == ["Feed post"]

    atom = ET.fromstring(client.get("/atom.xml").content)
    ns = "{http://www.w3.org/2005/Atom}"
    assert any(e.findtext(f"{ns}title") == "Feed post" for e in atom.iter(f"{ns}entry"))

    feed = client.get("/feed.json").json()
    assert feed["version"].startswith("https://jsonfeed.org")
    item = next(i for i in feed["items"] if i["title"] == "Feed post")
    assert item["url"].endswith(f"/post/{slug}") and item["tags"] == ["feeds"]


def test_sitemap_lists_pages_tags_and_dates(admin, client):
    save_post(admin, title="Mapped", tags="mapping")
    xml = client.get("/sitemap.xml").text
    assert "/archive</loc>" in xml and "/tag/mapping</loc>" in xml and "<lastmod>" in xml
    ET.fromstring(xml.encode())


def test_every_page_has_one_title_and_canonical(admin, client):
    slug = save_post(admin, title="Titled post")
    for path in ("/", f"/post/{slug}", "/tags", "/archive", "/nope"):
        html = client.get(path).text
        assert len(re.findall(r"<title>", html)) == 1, path
        assert "FastHTML page" not in html
        assert len(re.findall(r'rel="canonical"', html)) <= 1, path
    assert "<title>Titled post — " in client.get(f"/post/{slug}").text
