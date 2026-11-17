"""Share cards (cards.py): the picture a shared link shows for a post
with no image of its own, and for the site's other pages."""
import io
import os

from PIL import Image

from conftest import save_post
from soloblog import cards, posts, settings


def test_a_post_without_an_image_gets_a_card(admin, client):
    slug = save_post(admin, title="Bread, bicycles and the fog over the bay")
    r = client.get(f"/card/{slug}.png")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert Image.open(io.BytesIO(r.content)).size == (1200, 630)
    # kept on disk, and drawn again - under a new name - when the title changes
    first = cards.post_card_url(posts.get_post(slug))
    assert first in client.get(f"/post/{slug}").text.replace("&amp;", "&")
    save_post(admin, title="Bread, bicycles and fog", slug=slug)
    second = cards.post_card_url(posts.get_post(slug))
    assert second != first
    kept = [n for n in os.listdir(cards.cards_dir()) if n.startswith(slug + "-")]
    assert len(kept) == 1  # the old card is gone
    # its own image wins: a cover, or Post settings > Search engines
    save_post(admin, title="Bread, bicycles and fog", slug=slug, cover_image="/uploads/loaf.webp")
    assert "/uploads/loaf.webp" in client.get(f"/post/{slug}").text


def test_cards_only_for_what_is_live_and_drawable(admin, client):
    draft = save_post(admin, title="Not yet", published="")
    assert client.get(f"/card/{draft}.png").status_code == 404
    assert client.get("/card/no-such-post.png").status_code == 404
    # Latin with accents, Greek and Cyrillic draw; an emoji is left out;
    # another script gets no card rather than empty boxes
    assert cards._drawable("Crème brûlée 🍮 – Ψωμί, хлеб") == "Crème brûlée – Ψωμί, хлеб"
    assert cards._drawable("面包和自行车") is None
    cjk = save_post(admin, title="面包和自行车")
    assert cards.post_card_url(posts.get_post(cjk)) is None
    assert client.get(f"/card/{cjk}.png").status_code == 404


def test_the_site_card_and_its_colours(client):
    r = client.get("/card.png")
    assert r.status_code == 200
    img = Image.open(io.BytesIO(r.content)).convert("RGB")
    # the page in the palette's base colour, its own colour along the foot
    colours = cards._colours()
    assert img.getpixel((5, 5)) == colours["base-100"]
    assert img.getpixel((600, 625)) == colours["fill"]
    before, url = settings.get("theme"), cards.site_card_url()
    try:
        # a new palette is a new card, under a new address
        settings.set_many({"theme": "nord"})
        assert cards.site_card_url() != url
        img = Image.open(io.BytesIO(client.get("/card.png").content)).convert("RGB")
        assert img.getpixel((5, 5)) == cards._colours()["base-100"] != (255, 255, 255)
    finally:
        settings.set_many({"theme": before})


def test_cards_are_listed_on_the_disk_and_can_be_cleared(admin, client):
    from soloblog import backup
    client.get("/card.png")
    assert any(key == "cards" for key, _, _ in backup.disk_usage()["parts"])
    r = admin.post("/admin/disk/clear-cards")
    assert r.status_code in (302, 303) and not os.path.exists(cards.cards_dir())
    assert client.get("/card.png").status_code == 200  # made again
