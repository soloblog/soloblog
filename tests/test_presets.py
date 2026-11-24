"""Settings presets (presets.py): applied, undone, previewed - and never
the colours or the writing."""
from conftest import save_post
from soloblog import pages, posts, presets, settings

KEYS = sorted({k for _, _, values, _ in presets.PRESETS.values() for k in values} |
              {"theme", "preset", "preset_undo", "home_page"})


def _keep():
    return {k: settings.get(k) for k in KEYS}


def test_every_preset_sets_real_settings_with_valid_values():
    for key, (name, about, values, _needs) in presets.PRESETS.items():
        assert name and about, key
        assert set(values) <= set(settings.DEFAULTS), (key, set(values) - set(settings.DEFAULTS))
        assert "theme" not in values and "theme_dark" not in values, key  # colours are chosen on their own


def test_presets_cover_the_same_settings_with_values_the_forms_take():
    """One applied after another leaves nothing of the first - and every
    value is one Settings itself would save."""
    from soloblog import fonts, pages, ui
    keys = {frozenset(set(values) - {"home_page"}) for _, _, values, _ in presets.PRESETS.values()}
    assert len(keys) == 1
    # the homepage only from a style with a page of its own (or the wiki's):
    # one without leaves yours alone
    for key, (_, _, v, needs) in presets.PRESETS.items():
        assert "home_page" not in v or needs or v["home_page"] == posts.WIKI_HOME, key
    for key, (_, _, v, _) in presets.PRESETS.items():
        assert v["roll_style"] in ("list", "cards", "magazine", "minimal", "timeline"), key
        assert v["font_body"] in ("", *fonts.STACKS) and v["font_headings"] in ("", *fonts.STACKS), key
        assert v["header_align"] in ui.HEADER_ALIGNS and v["minimal_group"] in ui.MINIMAL_GROUPS, key
        assert v["toc_style"] in pages.TOC_STYLES and v["cover_width"] in pages.COVER_STYLES, key
        assert set(v["post_shows"].split(",")) <= set(pages.EXTRAS), key
        assert set(v["roll_shows"].split(",")) <= set(ui.ROLL_PARTS), key
        for side in ("side_tags", "side_archive", "side_author"):
            assert v[side] in ui.SIDE_PLACES, key


def test_a_stacked_header_never_floats():
    """The title over its menu, floating over the page, covers too much of
    it: those styles keep it in place or at the top."""
    stacked = {k for k, (_, _, v, _) in presets.PRESETS.items() if v["header_align"] == "stacked"}
    assert stacked >= {"notebook", "magazine", "launch", "link-in-bio"}
    for key in stacked:
        assert presets.PRESETS[key][2]["header_style"] in ("inline", "fixed"), key


def test_the_wiki_preset(admin, client):
    """Its front page is the homepage, with a first note only if there are
    none - and Undo takes both back."""
    before = _keep()
    try:
        wikis = [p for p in posts.list_posts(include_drafts=True) if p["in_wiki"]]
        assert not presets.uses_page("wiki") and presets.uses_page("docs")
        made = presets.apply("wiki")["made"]
        assert settings.get("home_page") == "@wiki" and bool(made) == (not wikis)
        assert "Recently edited" in client.get("/").text
        presets.undo()
        assert settings.get("home_page") == before["home_page"]
    finally:
        settings.set_many(before)


def test_apply_then_undo(admin):
    before = _keep()
    try:
        settings.set_many({"roll_style": "list", "font_body": "", "theme": "cupcake"})
        r = admin.post("/admin/presets/apply", data={"key": "notebook"})
        # Undo is the panel's own (Undo it), not in the message too
        assert r.status_code == 303 and "undo=" not in r.headers["location"]
        assert settings.get("roll_style") == "minimal" and settings.get("font_body") == "transitional"
        assert settings.get("theme") == "cupcake" and settings.get("preset") == "notebook"
        admin.post("/admin/presets/undo")
        assert settings.get("roll_style") == "list" and settings.get("font_body") == "" and not settings.get("preset")
    finally:
        settings.set_many(before)


def test_a_preset_that_needs_a_page_makes_one_or_uses_yours(admin):
    before = _keep()
    try:
        admin.post("/admin/presets/apply", data={"key": "portfolio"})
        made = settings.get("home_page")
        assert made and posts.is_page(posts.get_post(made))
        # made from the template: its sections, and its settings
        assert posts.get_post(made)["page_width"] == "wide" and "Section: Portfolio" in posts.load_post_body(made)
        assert "Section: Portfolio" in posts.load_post_body(made)
        admin.post("/admin/presets/undo")  # untouched, so it goes to the trash
        assert not posts.get_post(made) and settings.get("home_page") == before["home_page"]
        # one of your own pages instead
        mine = save_post(admin, title="My own start page", pinned="1", pin_location="header")
        admin.post("/admin/presets/apply", data={"key": "docs", "page_from": "mine", "page": mine})
        assert settings.get("home_page") == mine
        admin.post("/admin/presets/undo")
        assert posts.get_post(mine)  # never yours
        # "A new page" chosen, with a page picked earlier still in the field
        admin.post("/admin/presets/apply", data={"key": "docs", "page_from": "new", "page": mine})
        assert settings.get("home_page") not in ("", mine)
        admin.post("/admin/presets/undo")
        html = admin.get("/admin/settings?tab=style").text
        assert "A new page" in html and "One of your pages" in html
        # a made page you've edited stays when you undo
        admin.post("/admin/presets/apply", data={"key": "link-in-bio"})
        made = settings.get("home_page")
        posts.write(made, body="My own words now.")
        admin.post("/admin/presets/undo")
        assert posts.get_post(made)
    finally:
        settings.set_many(before)


def test_preview_is_for_the_admin_only_and_saves_nothing(app, admin, client):
    from starlette.testclient import TestClient
    before = settings.get("roll_style")
    r = admin.get("/admin/presets/preview/magazine")
    assert r.status_code == 303 and "preview_preset=magazine" in r.headers.get("set-cookie", "")
    page = admin.get("/").text
    assert "Previewing the Magazine style" in page and settings.get("roll_style") == before
    stranger = TestClient(app, cookies={"preview_preset": "magazine"})
    assert "Previewing" not in stranger.get("/").text
    admin.post("/admin/presets/stop")
    admin.cookies.delete("preview_preset")
    assert "Previewing" not in admin.get("/").text


def test_a_preset_shows_in_the_design_preview_frame(admin, client):
    import re
    from soloblog import settings
    same = lambda html: re.sub(r'nonce="[^"]*"', "", html)  # noqa: E731
    before = settings.get("roll_style")
    # the full-screen preview's frame: the admin sees the preset, with no cookie and nothing saved
    assert same(admin.get("/?preset_preview=magazine").text) != same(admin.get("/").text)
    assert "preview_preset" not in admin.cookies and settings.get("roll_style") == before
    # a visitor sees the site as it is
    assert same(client.get("/?preset_preview=magazine").text) == same(client.get("/").text)
    assert admin.get("/?preset_preview=nonsense").status_code == 200


def test_a_preset_says_what_it_would_change(admin):
    # a card said what a preset was for, not what it would change: now the
    # settings that differ from the site as it is, in their own pages' words
    from soloblog.routes.admin_settings import preset_changes
    kept = _keep()
    try:
        settings.set_many({**presets.PRESETS["personal"][2]})
        notebook = preset_changes(presets.PRESETS["notebook"][2], settings.get_all())
        assert "Posts are shown as: List → Minimal" in notebook
        assert "Banner width: Edge to edge → Column" in notebook and "Animations: On → Off" in notebook
        assert any(line.startswith("Each post shows: ") and "takes off" in line for line in notebook)
        # every line is one that differs - and the same values change nothing
        assert len(notebook) < len(presets.PRESETS["notebook"][2])
        assert preset_changes(presets.PRESETS["personal"][2], settings.get_all()) == []
        page = admin.get("/admin/settings?tab=style").text
        # every card lists all it sets - what it would change reads "now → then"
        every = preset_changes(presets.PRESETS["notebook"][2], settings.get_all(), every=True)
        assert f"Changes {len(notebook)} of {len(every)} settings" in page
        assert sum(1 for _, changes in every if changes) == len(notebook)
        assert ("Posts are shown as: List → Minimal", True) in every
        assert "<strong class=\"text-base-content\">Posts are shown as: List → Minimal</strong>" in page
        # in use, too: what it sets, nothing to change
        sets = preset_changes(presets.PRESETS["personal"][2], settings.get_all(), every=True)
        assert f"Your site looks like this - sets {len(sets)} settings" in page
        assert ("Posts are shown as: List", False) in sets and ("Header position: Floating", False) in sets
        # used: beside Undo, what it changed
        admin.post("/admin/presets/apply", data={"key": "notebook"})
        page = admin.get("/admin/settings?tab=style").text
        assert f"Using Writer&#x27;s notebook - changed {len(notebook)} settings" in page or \
               f"Using Writer's notebook - changed {len(notebook)} settings" in page
        assert "Posts are shown as: List → Minimal" in page
        # and the welcome's style step, for each one
        assert "What each one changes" in admin.get("/admin/welcome?step=style").text
    finally:
        presets.undo()
        settings.set_many(kept)


def test_launch_makes_a_landing_page_the_homepage(admin, client):
    # a book, a course or a product: a landing page built from sections
    kept = _keep()
    try:
        made = presets.apply("launch")["made"]
        row = posts.get_post(made)
        assert settings.get("home_page") == made
        assert (row["title_style"], row["page_width"]) == ("hidden", "wide")
        assert "Section: Pricing" in posts.load_post_body(made)
        home = client.get("/").text
        assert "tabular-nums leading-none" in home and "Most popular" in home  # its sections, on the homepage
    finally:
        presets.undo()
        settings.set_many(kept)


def test_launch_centres_section_headings_and_every_style_says_where(admin):
    # every style sets it, so one applied after Launch leaves nothing behind - and Undo puts it back
    assert all(values["section_heading_align"] in pages.SECTION_HEADINGS for _, _, values, _ in presets.PRESETS.values())
    assert [k for k, p in presets.PRESETS.items() if p[2]["section_heading_align"] == "centre"] == ["launch"]
    assert "section_heading_align" in presets.default_values()
    assert presets.preview_values("launch")["section_heading_align"] == "centre"
    kept = _keep()
    settings.set_many({"section_heading_align": "left"})
    try:
        presets.apply("launch")
        assert settings.get("section_heading_align") == "centre"
        assert presets.undo() and settings.get("section_heading_align") == "left"
    finally:
        presets.undo()
        settings.set_many({**kept, "section_heading_align": "left"})


def test_one_custom_look_saved_used_and_replaced(admin):
    # Custom, beside Default: the look as it is, saved to come back to -
    # a card like the others, and saving again replaces it
    keep = _keep()
    before = {k: settings.get(k) for k in ("custom_preset", "header_style", "theme", "site_title")}
    try:
        settings.set_many({"custom_preset": ""})
        page = admin.get("/admin/settings?tab=style").text
        assert presets.find(presets.CUSTOM_KEY) is None and "Save the look you have now" in page
        settings.set_many({"header_style": "inline", "theme": "nord"})
        admin.post("/admin/presets/save-custom")
        saved = presets.find(presets.CUSTOM_KEY)[2]
        assert saved["header_style"] == "inline" and saved["theme"] == "nord" and "site_title" not in saved
        settings.set_many({"header_style": "fixed"})
        page = admin.get("/admin/settings?tab=style").text
        assert "Your own look, saved" in page and "Replace Custom with the look you have now?" in page
        admin.post("/admin/presets/apply", data={"key": presets.CUSTOM_KEY})
        assert settings.get("header_style") == "inline"
        admin.post("/admin/presets/undo")
        assert settings.get("header_style") == "fixed"
        # replaced by the look as it is now
        admin.post("/admin/presets/save-custom")
        assert presets.find(presets.CUSTOM_KEY)[2]["header_style"] == "fixed"
        # a saved look with a setting since gone is used without it
        import json
        settings.set_many({"custom_preset": json.dumps({"values": {"header_style": "inline", "gone_setting": "x"},
                                                         "saved": "2026-10-21"})})
        assert presets.find(presets.CUSTOM_KEY)[2] == {"header_style": "inline"}
    finally:
        settings.set_many({**keep, **before})


def test_one_undo_after_using_a_style(admin):
    # "Now using Default · Undo" at the top and the panel's own Undo it
    # undid the same thing - the panel's stays, it says what it puts back
    keep = _keep()
    try:
        r = admin.post("/admin/presets/apply", data={"key": "notebook"}, follow_redirects=False)
        assert "undo=" not in r.headers["location"]
        assert "Undo it" in admin.get(r.headers["location"]).text
    finally:
        settings.set_many(keep)
        admin.post("/admin/presets/undo")


def test_every_look_setting_has_a_line_in_a_styles_list():
    # Default and Custom set the colours too, but their lists left them
    # out - each setting now has its own page's words, a new one included
    from soloblog.routes.admin_settings import preset_changes
    values = presets.find(presets.DEFAULT_KEY)[2]
    site = dict(settings.DEFAULTS)
    assert [k for k in values if not preset_changes({k: values[k]}, site, every=True)] == []
    lines = dict(preset_changes(values, {**site, "theme": "nord"}, every=True))
    assert lines["Light palette: Nord → Light"] is True


# ---- the styles built around a page: its words and settings come from a template

_PAGE_STYLES = {"portfolio": "portfolio", "freelancer": "services", "business": "business", "docs": "docs",
                "launch": "landing", "link-in-bio": "profile"}
_COLUMNS = ("title_style", "page_width", "cover_width", "toc_style", "heading_fold", "section_space", "section_motion",
            "sides", "extras")


def _row_settings(row):
    return {**{c: row[c] for c in _COLUMNS}, **{c: bool(row[c]) for c in ("slides", "in_wiki", "remind_update")},
            "link_url": row["link_url"]}


def test_each_style_makes_its_homepage_from_the_templates_sections_and_settings(admin):
    from soloblog import post_templates
    kept = _keep()
    try:
        for key, template in _PAGE_STYLES.items():
            made = presets.apply(key)["made"]
            row = posts.get_post(made)
            assert settings.get("home_page") == made, key
            wanted = post_templates.settings_of(post_templates.get(template))
            assert _row_settings(row) == wanted, key
            first = presets._kinds(presets._start_text(template))[:1]
            assert first == presets._kinds(posts.load_post_body(made))[:1], key
            presets.undo()
            assert not posts.get_post(made), key  # untouched, so it goes to the trash
    finally:
        settings.set_many(kept)


def test_a_style_writes_every_setting_its_template_holds(admin, monkeypatch):
    from soloblog import post_templates
    held = {"title_style": "centre", "page_width": "wide", "cover_width": "full", "toc_style": "side",
            "heading_fold": "folded", "section_space": "large", "section_motion": "rise", "sides": "tags=left,author=off",
            "extras": "byline,print", "slides": True, "in_wiki": False, "remind_update": True,
            "link_url": "https://example.com/there"}
    real = post_templates.get
    monkeypatch.setattr(post_templates, "get", lambda key: {**real(key), "settings": held}
                        if key == "portfolio" else real(key))
    kept = _keep()
    try:
        row = posts.get_post(presets.apply("portfolio")["made"])
        assert _row_settings(row) == held
    finally:
        presets.undo()
        settings.set_many(kept)


def test_the_docs_start_page_has_a_contents_section(admin):
    kept = _keep()
    try:
        made = presets.apply("docs")["made"]
        body = posts.load_post_body(made)
        assert body.count("Section: Contents") == 1
        # it's the guide's first part, so its Contents lists the guide, not a note that it's in no series
        assert posts.get_post(made)["series_name"] == "Guide"
        page = admin.get("/").text  # it's the homepage
        assert 'aria-current="page"' in page and "isn't in a series" not in page
        # the template's own words stay, and Contents follows them
        assert body.startswith("What this part covers") and body.index("## Next") < body.index("Section: Contents")
    finally:
        presets.undo()
        settings.set_many(kept)


def test_a_docs_template_with_a_contents_section_does_not_get_a_second(monkeypatch):
    from soloblog import post_templates
    real = post_templates.get
    own = "Words.\n\n## Parts\n\nSection: Contents\n"
    monkeypatch.setattr(post_templates, "get", lambda key: {**real(key), "body": own} if key == "docs" else real(key))
    assert presets._start_text("docs") == own  # its own Contents section, under another heading


def test_a_preview_shows_the_page_that_has_the_templates_first_section(admin):
    kept = _keep()
    try:
        posts.write(title="Plain page", body="Just words.", published=True, pin_location="header")
        assert "home_page" not in presets.preview_values("portfolio")
        mine = posts.write(title="My work", body="## Work\n\nSection: Portfolio\n\n### One\n\nWords.", published=True,
                           pin_location="header")
        assert presets.preview_values("portfolio")["home_page"] == mine
        # another style's first section isn't it, and a post that isn't a page never is
        assert "home_page" not in presets.preview_values("launch")
        posts.write(title="A post", body="## Work\n\nSection: Pricing", published=True)
        assert "home_page" not in presets.preview_values("launch")
        # Docs looks for a Contents section, the one its start page opens with
        guide = posts.write(title="Guide", body="## Parts\n\nSection: Contents", published=True, pin_location="header")
        assert presets.preview_values("docs")["home_page"] == guide
    finally:
        settings.set_many(kept)


def test_the_wiki_style_looks_for_notes_by_in_the_wiki_and_starts_one(admin):
    kept = _keep()
    # notes an earlier test left: the style asks whether there are any
    notes = [r["slug"] for r in posts.list_posts(include_drafts=True) if r["in_wiki"]]
    for slug in notes:
        posts.write(slug, in_wiki=False)
    try:
        # a post that only reads like a note isn't one
        posts.write(title="Looks like a note", body="Words.", published=True)
        made = presets.apply("wiki")["made"]
        note = posts.get_post(made)
        assert note["in_wiki"] and settings.get("home_page") == posts.WIKI_HOME
        presets.undo()
        assert not posts.get_post(made)
        # with a note already in the wiki, none is made
        posts.write(title="A real note", body="Words.", published=True, in_wiki=True)
        assert presets.apply("wiki")["made"] == ""
    finally:
        presets.undo()
        for slug in notes:
            posts.write(slug, in_wiki=True)
        settings.set_many(kept)


def test_a_style_without_a_page_leaves_your_homepage_alone(admin):
    """Trying Personal blog on a site whose homepage is a landing page of
    yours kept the look and dropped the page for the blog roll."""
    before = _keep()
    try:
        mine = save_post(admin, title="My landing page", body="Welcome.", pin_location="header")
        settings.set_many({"home_page": mine})
        presets.apply("personal")
        assert settings.get("home_page") == mine and settings.get("preset") == "personal"
    finally:
        settings.set_many(before)
