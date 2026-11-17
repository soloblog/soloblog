from soloblog import settings
from conftest import save_post


def test_emoji_reactions(admin, client):
    settings.set_many({"reactions_style": "emoji", "reaction_emojis": "heart,fire"})
    try:
        slug = save_post(admin, title="React to me")
        page = client.get(f"/post/{slug}").text
        assert 'id="reactions"' in page and 'data-reaction="fire"' in page and 'data-reaction="clap"' not in page
        assert 'id="like-button"' not in page

        r = client.post(f"/post/{slug}/react", data={"reaction": "fire"})
        assert r.json()["counts"] == {"fire": 1}
        # the same address can't pile on the same reaction...
        assert client.post(f"/post/{slug}/react", data={"reaction": "fire"}).json()["counts"] == {"fire": 1}
        # ...but can add a different one
        assert client.post(f"/post/{slug}/react", data={"reaction": "heart"}).json()["counts"] == {"fire": 1, "heart": 1}
        # one that isn't offered, and the admin, change nothing
        assert client.post(f"/post/{slug}/react", data={"reaction": "clap"}).json()["counts"] == {"fire": 1, "heart": 1}
        assert admin.post(f"/post/{slug}/react", data={"reaction": "heart"}).json()["counts"]["heart"] == 1
        assert 'pointer-events-none' in admin.get(f"/post/{slug}").text
    finally:
        settings.set_many({"reactions_style": "like", "reaction_emojis": "heart,clap,laugh,wow,think"})
    # switched off, the endpoint is gone
    assert client.post(f"/post/{slug}/react", data={"reaction": "fire"}).status_code == 404


def test_reaction_settings_save(admin):
    before = settings.get_all()
    page = admin.get("/admin/settings?tab=posts").text
    assert 'name="reactions_style"' in page and 'value="party"' in page
    r = admin.post("/admin/settings/style", headers={"hx-request": "true"},
                   data={"theme": "light", "reactions_style": "emoji", "reaction_emojis": ["party", "clap", "bogus"]})
    assert r.status_code == 200
    try:
        assert settings.get("reactions_style") == "emoji"
        assert settings.get("reaction_emojis") == "party,clap"
    finally:
        # the form resets what it wasn't sent - put everything back
        settings.set_many(before)
