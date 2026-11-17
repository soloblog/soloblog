"""Pickers in place of long dropdowns (docs/DEVELOPMENT.md > Writing and
settings): a page is chosen from the link picker, by title."""
from conftest import save_post
from soloblog import settings


def test_the_page_picker_offers_only_pages(admin):
    page = save_post(admin, title="Chooser page", pinned="1", pin_location="header")
    post = save_post(admin, title="Chooser post")
    pages = admin.get("/admin/link-picker?kind=page&q=Chooser").text
    assert f'data-slug="{page}"' in pages and f'data-slug="{post}"' not in pages and "Built-in pages" not in pages
    # leaves out the page it's for, and anything that isn't a kind it knows is the plain link list
    assert f'data-slug="{page}"' not in admin.get(f"/admin/link-picker?kind=page&q=Chooser&exclude={page}").text
    assert "Built-in pages" in admin.get("/admin/link-picker?kind=x';--").text


def test_homepage_is_posts_wiki_or_a_picked_page(admin):
    before = settings.get("home_page")
    page = save_post(admin, title="Front door", pinned="1", pin_location="header")
    try:
        form = admin.get("/admin/settings?tab=name").text
        assert 'name="home_kind"' in form and 'data-picker-kind="home"' in form and 'id="link-picker-dialog"' in form
        for kind, slug, saved in (("page", page, page), ("wiki", page, "@wiki"), ("posts", page, ""),
                                  ("page", "no-such-page", "")):
            admin.post("/admin/settings/name", data={"home_kind": kind, "home_page": slug,
                                                        "declared_fields": "home_kind,home_page"},
                       headers={"HX-Request": "true"})
            assert settings.get("home_page") == saved, kind
        settings.set_many({"home_page": page})
        assert 'value="Front door"' in admin.get("/admin/settings?tab=name").text
    finally:
        settings.set_many({"home_page": before or ""})


def test_templates_are_chosen_from_cards_and_a_page_has_no_layout_to_choose(admin):
    """A new post's templates are cards in a dialog, grouped and searchable; there is no
    layout picker."""
    html = admin.get("/admin/new").text
    assert 'id="template-start-dialog"' in html and 'data-combo="template-start"' in html
    assert 'data-combo-group="Built-in"' in html and "data-combo-item=" in html
    assert "layout-dialog" not in html and 'name="layout"' not in html and 'id="layout-select"' not in html


def test_fonts_and_currencies_are_found_by_typing(admin):
    look = admin.get("/admin/settings?tab=style").text
    assert 'data-combo="font_body"' in look and 'style="font-family: Charter' in look and "<optgroup" not in look
    members = admin.get("/admin/settings?tab=members").text
    assert 'data-combo="members_currency"' in members and 'data-label="NOK - kr"' in members
    site = admin.get("/admin/settings?tab=language").text
    assert 'data-combo="site_language"' in site and 'data-label="Norsk"' in site


def test_the_pictures_are_the_blog_rolls_and_the_styles(admin):
    from soloblog import pages
    # no page has a picture of its own any more: only the blog roll's and the starting styles'
    assert pages.THUMBS and all(k.startswith(("roll-", "preset-")) for k in pages.THUMBS)
    html = admin.get("/admin/new").text
    assert '<svg viewBox="0 0 64 40"' not in html


def test_blog_layout_and_presets_have_pictures(admin):
    from soloblog import presets
    from soloblog.routes.admin_settings import PRESET_PICTURES
    from soloblog import pages
    html = admin.get("/admin/settings?tab=blog").text
    assert html.count('<svg viewBox="0 0 64 40"') >= 5 and 'name="roll_style"' in html
    # every style has one, Default too
    assert set(PRESET_PICTURES) == {presets.DEFAULT_KEY, presets.CUSTOM_KEY, *presets.PRESETS} and set(PRESET_PICTURES.values()) <= set(pages.THUMBS)
    assert admin.get("/admin/settings?tab=style").text.count('<svg viewBox="0 0 64 40"') >= len(presets.PRESETS)


def test_typing_double_brackets_suggests_titles_from_the_admin_only(admin, client):
    """The editor's [[ suggestions: every post and page, drafts marked,
    never the post being written - and only for the admin."""
    from conftest import editor_script
    live = save_post(admin, title="Suggest live")
    draft = save_post(admin, title="Suggest draft", published="")
    listed = {slug: (title, status) for title, slug, status in admin.get("/admin/post-titles.json").json()}
    assert listed[live] == ("Suggest live", "") and listed[draft] == ("Suggest draft", "Draft")
    assert live not in {s for _, s, _ in admin.get(f"/admin/post-titles.json?exclude={live}").json()}
    assert client.get("/admin/post-titles.json").status_code in (303, 401, 403)
    # the editor tells its script which post it is, and the script asks for the titles
    page = admin.get(f"/admin/edit/{live}").text
    assert f'data-own-slug="{live}"' in page and "/admin/post-titles.json" in editor_script(admin, page)


def test_every_picker_can_be_cleared(admin):
    # one ✕ for each Pick
    for tab in ("header", "banner", "profile", "sharing"):
        html = admin.get(f"/admin/settings?tab={tab}").text
        assert html.count('aria-label="Clear"') >= html.count("openMediaPicker") >= 1, tab
    html = admin.get("/admin/new").text
    assert html.count('aria-label="Clear"') >= html.count("openMediaPicker")
    assert "Arrange the menu" in admin.get("/admin/settings?tab=header").text


def test_an_image_is_never_its_own_other_version(admin):
    """Its dark mode and phone versions are other images: the picker
    leaves the image itself out, saving refuses it, and two images that
    name each other each show the other once - nothing goes round."""
    import io
    from PIL import Image
    from soloblog import images

    def upload(colour):
        data = io.BytesIO()
        Image.new("RGB", (40, 30), colour).save(data, "PNG")
        return images.save_upload(data.getvalue(), f"{colour} one").rsplit("/", 1)[1]
    one, two = upload("red"), upload("blue")
    details = admin.get(f"/admin/media/details/{one}").text
    assert details.count(f'data-picker-skip="{one}"') == 2
    assert "Photographer" not in details and "Who made the image" in details
    picker = admin.get(f"/admin/media/picker?skip={one}").text
    assert f"/uploads/{two}" in picker and one not in picker
    assert one in admin.get("/admin/media/picker").text
    # typed in by hand, or sent by something other than the picker
    admin.post(f"/admin/media/details/{one}", data={"dark_version": f"/uploads/{one}", "phone_version": one})
    assert images.get_meta(one)["dark_version"] == "" and images.get_meta(one)["phone_version"] == ""
    admin.post(f"/admin/media/details/{one}", data={"dark_version": f"/uploads/{two}"})
    admin.post(f"/admin/media/details/{two}", data={"dark_version": f"/uploads/{one}"})
    html = images.with_other_versions(f'<img src="/uploads/{one}"><img src="/uploads/{two}">')
    assert html.count("data-dark-src") == 2 and f'data-dark-src="/uploads/{two}"' in html
    # a credit typed here isn't always a photographer's
    images.set_meta(one, "", "", credit_name="Ana")
    assert images.credit_html(images.get_meta(one)) == "Image by Ana"
    for name in (one, two):
        images.move_to_trash(name)
