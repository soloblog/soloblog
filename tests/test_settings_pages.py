"""Settings, one page at a time under small headings (ui.SETTINGS_GROUPS):
switches and choices save as they change, set-up groups are a row that
opens, rare ones are under Advanced (docs/DEVELOPMENT.md > Writing and
settings)."""
import re

from soloblog import settings
from soloblog.ui import SETTINGS_GROUPS, SETTINGS_SECTIONS


def test_every_page_opens_under_its_heading(admin):
    assert len(SETTINGS_SECTIONS) == len(dict(SETTINGS_SECTIONS))
    for group, pages in SETTINGS_GROUPS:
        for key, label in pages:
            html = admin.get(f"/admin/settings?tab={key}").text
            assert f"Settings: {label}" in html and f"{group} ›" in html, key
            assert 'aria-current="page"' in html.split('id="settings-nav"')[1].split("</ul>")[0], key
    # an address from before the regroup still lands
    assert "Settings: Analytics and ads" in admin.get("/admin/settings?tab=analytics").text


def test_pages_save_as_they_change_and_groups_together(admin):
    html = admin.get("/admin/settings?tab=analytics").text
    assert 'data-autosave' in html
    # set up once: a row with how it stands, and Edit
    analytics = re.search(r'<details[^>]*data-panel="analytics-main"[^>]*>', html).group(0)
    assert "data-autosave-off" in analytics and " open" not in analytics
    assert re.search(r'data-panel="analytics-main".*?Off</span>.*?>Edit<', html, re.S)
    # rare ones fold away at the foot
    assert ">Advanced<" in admin.get("/admin/settings?tab=address").text


def test_set_once_and_rare_settings_fold_away(admin):
    """Sending email and sharing to an account are set up once: a row
    with how it stands. What few people need sits under Advanced."""
    before = {k: settings.get(k) for k in ("crosspost_bluesky", "bluesky_handle", "comment_webhook_url")}
    try:
        settings.set_many({"crosspost_bluesky": "1", "bluesky_handle": "me.bsky.social"})
        rows = {"email": "email-sending", "sharing": "sharing-bluesky"}
        for tab, key in rows.items():
            html = admin.get(f"/admin/settings?tab={tab}").text
            assert re.search(rf'data-panel="{key}".*?>Edit<', html, re.S), tab
        assert "me.bsky.social</span>" in admin.get("/admin/settings?tab=sharing").text
        rare = {"address": "address-verify", "sharing": "sharing-webmentions", "header": "header-app",
                "integrations": "integrations-code"}
        for tab, key in rare.items():
            html = admin.get(f"/admin/settings?tab={tab}").text
            assert html.index(">Advanced<") < html.index(f'data-panel="{key}"'), tab
        # the Slack or Discord address saves from Comments and messages now
        admin.post("/admin/settings/name", data={"comment_webhook_url": "https://hooks.slack.com/x",
                                                    "declared_fields": "comment_webhook_url"},
                   headers={"HX-Request": "true"})
        assert settings.get("comment_webhook_url") == "https://hooks.slack.com/x"
    finally:
        settings.set_many(before)


def test_one_setting_saves_on_its_own(admin):
    """What a switch sends as it changes - just itself - leaves the rest
    alone, and the homepage's kind brings its page with it."""
    before = {k: settings.get(k) for k in ("relative_dates", "show_updated", "home_page")}
    try:
        settings.set_many({"relative_dates": "0", "show_updated": "1"})
        r = admin.post("/admin/settings/style", data={"relative_dates": "1", "declared_fields": "relative_dates"},
                       headers={"HX-Request": "true"})
        assert "text-success" in r.text
        assert settings.get("relative_dates") == "1" and settings.get("show_updated") == "1"
        settings.set_many({"home_page": "@wiki"})
        admin.post("/admin/settings/name", data={"home_kind": "posts", "declared_fields": "home_kind"},
                   headers={"HX-Request": "true"})
        assert settings.get("home_page") == ""
    finally:
        settings.set_many(before)


def test_search_names_a_set_up_group_by_its_name(admin):
    """A set-up row's heading also says how it stands - search shows just
    its name."""
    found = admin.get("/admin/settings/search-index").json()
    stripe = next(e for e in found if e["title"] == "Stripe key")
    assert stripe["sub"] == "Paid members" and stripe["group"] == "Members" and "tab=members" in stripe["href"]


def test_design_preview_shows_the_form_unsaved(admin, client):
    """A Design page's preview: the form as it stands, on the site, for the
    admin's frame only - nothing saved, nothing for anyone else."""
    before = settings.get("footer_note"), settings.get("footer_show_note")
    try:
        settings.set_many({"footer_note": "Saved note", "footer_show_note": "1"})
        token = admin.post("/admin/design/preview", data={
            "footer_note": "Trying a new note", "footer_show_note": "1", "admin_email": "evil@example.com",
            "declared_fields": "footer_note,footer_show_note,admin_email"}).json()["token"]
        assert "Trying a new note" in admin.get(f"/?design_preview={token}").text
        assert settings.get("footer_note") == "Saved note" and settings.get("admin_email") != "evil@example.com"
        # a visitor with the address sees the site as it is
        assert "Trying a new note" not in client.get(f"/?design_preview={token}").text
        assert "Trying a new note" not in admin.get("/").text
        # an unticked switch is off in the preview
        token = admin.post("/admin/design/preview", data={"declared_fields": "footer_show_note"}).json()["token"]
        assert "Saved note" not in admin.get(f"/?design_preview={token}").text
        page = admin.get("/admin/settings?tab=header").text
        assert "data-design-preview" in page and "data-preview-frame" in page and "data-preview-show" in page
        # the same width as every other settings page; the frame loads only when opened
        assert "max-w-6xl" not in page and 'data-preview-frame src=' not in page
        assert "data-design-preview" not in admin.get("/admin/settings?tab=messages").text
    finally:
        settings.set_many({"footer_note": before[0] or "", "footer_show_note": before[1] or "1"})


def test_header_width_and_more(admin, client):
    from soloblog import settings
    before = settings.get("header_width")
    try:
        settings.set_many({"header_width": "column"})
        html = client.get("/").text
        # More is there, hidden until links don't fit (fitNav)
        assert 'data-nav-more' in html and "max-w-3xl" in html
        admin.post("/admin/settings/style", data={"header_width": "wide", "declared_fields": "header_width"})
        assert settings.get("header_width") == "wide"
        assert "max-w-[79rem]" in client.get("/").text
        admin.post("/admin/settings/style", data={"header_width": "huge", "declared_fields": "header_width"})
        assert settings.get("header_width") == settings.DEFAULTS["header_width"]  # nonsense: the default
    finally:
        settings.set_many({"header_width": before})



def test_defaults_are_tagged(admin):
    # a choice's default option says so in its list; each switch and choice
    # has Reset, shown while it differs (CUSTOM_TAGS_JS)
    html = admin.get("/admin/settings?tab=blog").text
    assert ">Default<" in html and "Reset to default" in html
    assert ">Default<" in admin.get("/admin/settings?tab=style").text


def test_side_panels_follow_their_order(admin, client):
    from soloblog import settings
    from tests.conftest import save_post
    save_post(admin, title="A tagged post for the side panels", tags="sidepanels")
    keys = ("side_tags", "side_archive", "side_author", "side_tags_where", "side_archive_where",
            "side_author_where", "side_order", "author_bio")
    keep = {k: settings.get(k) for k in keys}
    try:
        settings.set_many({"side_tags": "right", "side_author": "right", "side_archive": "off",
                           "side_tags_where": "roll", "side_author_where": "roll", "author_bio": "Hello there."})
        html = client.get("/").text
        assert html.index('data-panel="side-tags"') < html.index('data-panel="side-author"')
        admin.post("/admin/settings/style", data={"side_order": "side_author,nonsense,side_tags",
                                                        "declared_fields": "side_order"})
        assert settings.get("side_order") == "side_author,side_tags,side_archive"
        html = client.get("/").text
        assert html.index('data-panel="side-author"') < html.index('data-panel="side-tags"')
        assert 'name="side_order"' in admin.get("/admin/settings?tab=blog").text
    finally:
        settings.set_many(keep)


def test_design_pages_save_through_one_table(admin):
    """routes/admin_settings.DESIGN_FIELDS: every setting on a Design page
    is in it, a value it doesn't allow is the setting's default, and the
    live preview cleans what it's sent the same way."""
    import re
    from soloblog import settings
    from soloblog.routes.admin_settings import DESIGN_FIELDS, DESIGN_TABS, design_preview_values
    for tab in DESIGN_TABS:
        html = admin.get(f"/admin/settings?tab={tab}").text
        # the settings forms - the ones that say which fields they have
        forms = "".join(re.findall(r'<form[^>]*data-declare-fields[^>]*>(.*?)</form>', html, re.S))
        names = set(re.findall(r'<(?:input|select|textarea)[^>]*\bname="([a-z_]+)"', forms))
        assert names and names <= set(DESIGN_FIELDS), (tab, names - set(DESIGN_FIELDS))
    keep = {k: settings.get(k) for k in ("roll_style", "header_style", "theme", "posts_per_page")}
    try:
        admin.post("/admin/settings/style", data={
            "roll_style": "carousel", "header_style": "sideways", "theme": "no-such-theme", "posts_per_page": "9000",
            "declared_fields": "roll_style,header_style,theme,posts_per_page"})
        assert {k: settings.get(k) for k in keep} == {k: settings.DEFAULTS[k] for k in keep}
        token = admin.post("/admin/design/preview", data={
            "theme": "<script>", "roll_style": "magazine", "declared_fields": "theme,roll_style"}).json()["token"]
        shown = design_preview_values(token)
        assert shown["theme"] == settings.DEFAULTS["theme"] and shown["roll_style"] == "magazine"
    finally:
        settings.set_many(keep)


def test_every_settings_form_saves_through_its_table(admin):
    """Each form posting to a save handler with a field table (FIELDS in
    routes/admin_settings/saves.py) only has fields that table cleans - a new
    setting added to a page and not to its table fails here."""
    import re
    from soloblog.routes import admin_settings as a
    from soloblog.ui import SETTINGS_GROUPS
    # every page's address, to the table of the handler it saves through
    tables = {**{f"/admin/settings/{p}": a.GENERAL_FIELDS for p in ("name", "messages", "newsletter", "analytics")},
              **{f"/admin/settings/{p}": a.SITE_FIELDS for p in ("address", "language", "sharing")},
              **{f"/admin/settings/{p}": a.DESIGN_FIELDS for p in ("style", "blog", "posts", "header", "banner")},
              **{f"/admin/settings/{p}": a.SECRETS_FIELDS for p in ("email", "integrations")},
              "/admin/settings/profile": a.PROFILE_FIELDS}
    # what a form sends that isn't itself a setting
    helpers = {"home_kind", "newsletter_on_posts", "support_on_posts", "site_url", "support_add", "admin_email_confirm",
               "current_password"}
    seen = set()
    for _group, pages in SETTINGS_GROUPS:
        for tab, _label in pages:
            html = admin.get(f"/admin/settings?tab={tab}").text
            for url, body in re.findall(r'<form[^>]*hx-post="(/admin/settings/[a-z]+)"[^>]*data-declare-fields[^>]*>'
                                        r'(.*?)</form>', html, re.S):
                if url not in tables:
                    continue
                names = {n for n in re.findall(r'<(?:input|select|textarea)[^>]*\bname="([a-z_0-9]+)"', body)
                         if not n.endswith("__remove")} - helpers
                assert names <= set(tables[url]), (tab, url, names - set(tables[url]))
                seen.add(url)
    assert seen == set(tables)


def test_saved_secrets_never_go_back_to_the_page(admin):
    """ui.SecretInput: a saved key, password or token isn't in the page; an
    empty box keeps it, a new one replaces it, and Remove clears it."""
    from soloblog import settings
    keep = {k: settings.get(k) for k in ("smtp_password", "pixabay_api_key", "stripe_key")}
    try:
        settings.set_many({"smtp_password": "hunter2-very-secret", "pixabay_api_key": "not-a-real-pixabay-key"})
        html = admin.get("/admin/settings?tab=email").text + admin.get("/admin/settings?tab=integrations").text
        assert "hunter2-very-secret" not in html and "not-a-real-pixabay-key" not in html
        assert "Saved - type a new one to replace it" in html and 'name="smtp_password__remove"' in html
        post = lambda **f: admin.post("/admin/settings/integrations", data={**f, "declared_fields": ",".join(f)})  # noqa: E731
        post(smtp_password="")
        assert settings.get("smtp_password") == "hunter2-very-secret"
        post(smtp_password="a-new-one")
        assert settings.get("smtp_password") == "a-new-one"
        admin.post("/admin/settings/integrations", data={"smtp_password": "", "smtp_password__remove": "1",
                                                     "declared_fields": "smtp_password"})
        assert settings.get("smtp_password") == ""
        # the Stripe key, saved by its own handler, the same way
        settings.set_many({"stripe_key": "rk_test_not-a-real-key"})
        assert "rk_test_not-a-real-key" not in admin.get("/admin/settings?tab=members").text
        admin.post("/admin/settings/members", data={"stripe_key": "", "declared_fields": "stripe_key"})
        assert settings.get("stripe_key") == "rk_test_not-a-real-key"
        admin.post("/admin/settings/members", data={"stripe_key": "", "stripe_key__remove": "1",
                                                    "declared_fields": "stripe_key"})
        assert settings.get("stripe_key") == ""
    finally:
        settings.set_many(keep)


def test_support_links_show_what_you_have_and_add_the_rest(admin):
    """Profile and links > Support: the links you have, and "Add a support
    link" for the rest - not six empty boxes."""
    import re
    from soloblog import settings
    keys = [f"support_{k}" for k in ("kofi", "buymeacoffee", "github", "patreon", "liberapay", "paypal")]
    keep = {k: settings.get(k) for k in keys}
    try:
        settings.set_many({k: "" for k in keys} | {"support_patreon": "https://patreon.com/mira"})
        html = admin.get("/admin/settings?tab=profile").text
        support = html[html.index('data-panel="profile-support"'):]
        support = support[:support.index('data-panel="author-links-page"')] if 'data-panel="author-links-page"' in support else support
        # Patreon shows as itself; the other five wait under the picker, hidden
        assert 'value="https://patreon.com/mira"' in support and "Add another" in support
        assert len(re.findall(r'data-shown-for="support_add=', support)) == 5
        admin.post("/admin/settings/profile", data={"support_kofi": "https://ko-fi.com/mira", "support_add": "kofi",
                                                   "declared_fields": "support_kofi,support_add"})
        assert settings.get("support_kofi") == "https://ko-fi.com/mira"
    finally:
        settings.set_many(keep)


def test_settings_are_marked_against_the_starting_style(admin):
    """A switch, a choice and a list of ticks carry their default - the
    starting style's, over Soloblog's - for the bar and Reset (as Post
    settings has them); no "On/Off by default" label. Picking a style
    marks nothing; what's changed after it does."""
    from soloblog import presets, settings

    def field(html, name):
        at = html.index(f'name="{name}"')
        start = html.rindex("<fieldset", 0, at)
        return html[start:html.index("</fieldset>", at)]
    keys = ("preset", "roll_style", "editor_spellcheck", "roll_shows")
    before = {k: settings.get(k) for k in keys}
    try:
        settings.set_many({"preset": "magazine"})
        base = presets.baseline()
        assert base["roll_style"] == presets.find("magazine")[2]["roll_style"]
        assert base["editor_spellcheck"] == settings.DEFAULTS["editor_spellcheck"]
        html = admin.get("/admin/settings?tab=editor").text
        assert "by default</span>" not in html
        spell = field(html, "editor_spellcheck")
        assert "data-custom-field" in spell and "data-custom-reset" in spell
        on = "1" if settings.DEFAULTS["editor_spellcheck"] not in ("", "0") else "0"
        assert f'data-default-value="{on}"' in spell
        assert "Reset to default (On)" in spell or "Reset to default (Off)" in spell
        # the words turn the switch, not Reset - the first control in the label
        assert 'for="sw-editor_spellcheck"' in spell and 'id="sw-editor_spellcheck"' in spell
        blog = admin.get("/admin/settings?tab=blog").text
        roll = field(blog, "roll_style")
        assert roll.count(f'data-default-value="{base["roll_style"]}"') >= 2 and "data-custom-reset" in roll
        shows = field(blog, "roll_shows")
        ticked = base["roll_shows"].split(",")
        # each tick: on by default if the starting style ticks it
        offered = [t for t in ticked if f'value="{t}"' in shows]
        assert offered and shows.count('data-default-value="1"') == len(offered)
        # what's typed has no default to mark
        assert "data-default-value" not in field(admin.get("/admin/settings?tab=name").text, "site_title")
    finally:
        settings.set_many(before)


def test_the_backup_choices_save_as_they_change():
    from unittest import mock
    from fasthtml.common import to_xml
    from soloblog.routes.backup_routes import CloudStoragePanel
    with mock.patch("soloblog.storage.enabled", return_value=True), \
            mock.patch("soloblog.storage.check", return_value=""), \
            mock.patch("soloblog.storage.last_status", return_value={"error": "", "at": ""}), \
            mock.patch("soloblog.storage.list_backups", return_value=[]):
        html = to_xml(CloudStoragePanel())
    for url in ("/admin/backup/every", "/admin/backup/keep", "/admin/backup/include"):
        form = re.search(rf'<form[^>]*hx-post="{url}"[^>]*>', html)
        assert form and 'hx-trigger="change"' in form.group(0), url


def test_folded_sections_say_how_they_stand(admin):
    """A section that starts folded has its state beside its name and Edit,
    as a set-up row does - every folded group looks alike. Show for what's
    set on the host, which can't be changed here."""
    before = {k: settings.get(k) for k in ("redirects", "webmention_receive")}
    try:
        settings.set_many({"redirects": "/old /new\n/2019/* /archive", "webmention_receive": "1"})
        site = admin.get("/admin/settings?tab=address").text
        assert re.search(r'data-panel="address-redirects".*?2 addresses</span>', site, re.S)
        assert re.search(r'data-panel="address-verify".*?Not set</span>', site, re.S)
        sharing = admin.get("/admin/settings?tab=sharing").text
        webmentions = re.search(r'data-panel="sharing-webmentions".*?</summary>', sharing, re.S).group(0)
        assert ">On</span>" in webmentions and ">Edit</span>" in webmentions
        secrets = admin.get("/admin/settings?tab=integrations").text
        env = re.search(r'data-panel="integrations-env".*?</summary>', secrets, re.S).group(0)
        assert ">Show</span>" in env and ">Edit</span>" not in env
        assert re.search(r'data-panel="integrations-apikeys".*?(No keys|\d+ keys?)</span>',
                         admin.get("/admin/settings?tab=integrations").text, re.S)
    finally:
        settings.set_many(before)


def test_each_settings_page_is_at_its_names_address_and_saves_there(admin):
    """A page's address is a word of its name (Name and homepage is
    ?tab=name, Comments and messages ?tab=messages), its groups are named after it (name-identity), and its form
    saves to /admin/settings/<page> - one name for the page everywhere."""
    import re as _re
    from soloblog.ui import SETTINGS_SECTIONS
    for key, label in SETTINGS_SECTIONS:
        assert key in label.lower().split(), (key, label)
        html = admin.get(f"/admin/settings?tab={key}").text
        for panel in set(_re.findall(r'data-panel="([a-z0-9_-]+)"', html)):
            assert panel.startswith(key + "-"), (key, panel)
        for action in set(_re.findall(r'hx-post="(/admin/settings/[a-z-]+)"', html)) - {"/admin/settings/password"}:
            assert action == f"/admin/settings/{key}", (key, action)
    # the old names are gone, not kept as another way in
    for old in ("general", "site", "appearance", "chrome", "hero", "author", "secrets"):
        assert old not in dict(SETTINGS_SECTIONS)
        assert admin.post(f"/admin/settings/{old}", headers={"hx-request": "true"}).status_code in (404, 405)


def test_comments_and_messages_is_one_page(admin):
    """Comments, the contact form, being told about new ones and the spam
    check on one page, in that order - and no page left under the old names."""
    html = admin.get("/admin/settings?tab=messages").text
    keys = ["messages-comments", "messages-contact", "messages-blocked", "messages-notify"]
    at = [html.index(f'data-panel="{k}"') for k in keys]
    assert at == sorted(at)
    # the alerts for comments and messages are together, not on a panel above
    notify = html[at[3]:]
    for name in ("notify_comments", "contact_email", "comment_webhook_url"):
        assert f'name="{name}"' in notify
    assert 'name="notify_comments"' not in html[:at[3]] and 'name="contact_email"' not in html[:at[3]]
    # an old address shows what any unknown page shows
    assert "Settings: Name and homepage" in admin.get("/admin/settings?tab=comments").text
    assert "Settings: Name and homepage" in admin.get("/admin/settings?tab=contact").text


def test_saving_one_panel_of_comments_and_messages_keeps_the_others(admin):
    keys = ("comments_enabled", "comment_blocklist", "contact_enabled", "contact_intro", "contact_email",
            "notify_comments", "comment_webhook_url", "captcha_provider")
    before = {k: settings.get(k) for k in keys}
    try:
        settings.set_many({"comments_enabled": "1", "comment_blocklist": "casino", "contact_enabled": "1",
                           "contact_intro": "Hi", "contact_email": "me@example.com", "notify_comments": "1",
                           "comment_webhook_url": "https://hooks.slack.com/x"})
        for fields, data in (("comment_blocklist", {"comment_blocklist": "spam"}),
                             ("contact_intro", {"contact_intro": "Write"}),
                             ("comment_webhook_url", {"comment_webhook_url": "https://hooks.slack.com/y"})):
            admin.post("/admin/settings/messages", data={**data, "declared_fields": fields},
                       headers={"HX-Request": "true"})
        assert settings.get("comment_blocklist") == "spam" and settings.get("contact_intro") == "Write"
        assert settings.get("comment_webhook_url") == "https://hooks.slack.com/y"
        assert settings.get("contact_email") == "me@example.com" and settings.get("notify_comments") == "1"
        assert settings.get("comments_enabled") == "1" and settings.get("contact_enabled") == "1"
    finally:
        settings.set_many(before)


def test_the_search_finds_comment_and_contact_settings_on_the_new_page(admin):
    entries = admin.get("/admin/settings/search-index").json()
    for title in ("Allow comments", "Turn on the contact form", "Email me about new comments",
                  "Send new comments and messages to", "Blocked words"):
        assert any(e["title"] == title and "tab=messages&" in e["href"] for e in entries), title
    assert not any("tab=comments" in e["href"] or "tab=contact" in e["href"] for e in entries)


def test_no_link_still_points_at_the_old_comments_and_contact_pages():
    import pathlib
    root = pathlib.Path(__file__).resolve().parent.parent
    old = ("tab=comments", "tab=contact", "settings/comments", "settings/contact")
    found = [f"{p.relative_to(root)}: {o}" for folder in ("soloblog", "docs", "tools")
             for p in (root / folder).rglob("*") if p.suffix in (".py", ".md", ".js") and "locales" not in p.parts
             for o in old if o in p.read_text(errors="ignore")]
    assert not found, found


def test_blocked_words_and_alerts_wait_for_either_switch_and_email_is_asked_for_once(admin):
    import re
    keys = ("comments_enabled", "contact_enabled", "email_provider")
    before = {k: settings.get(k) for k in keys}
    panel = lambda html, key: re.search(rf'<details[^>]*data-panel="{key}"[^>]*>', html).group(0)  # noqa: E731
    try:
        settings.set_many({"email_provider": "", "comments_enabled": "0", "contact_enabled": "0"})
        page = admin.get("/admin/settings?tab=messages").text
        assert " hidden" in panel(page, "messages-blocked") and " hidden" in panel(page, "messages-notify")
        body = page[page.index("id=\"settings-body\""):]
        assert body.count(">Set up email<") == 1
        # the contact form alone is enough to show them, with comments off
        settings.set_many({"contact_enabled": "1"})
        page = admin.get("/admin/settings?tab=messages").text
        assert " hidden" not in panel(page, "messages-blocked") and " hidden" not in panel(page, "messages-notify")
        assert 'data-shown-for="comments_enabled=1;contact_enabled=1"' in panel(page, "messages-blocked")
    finally:
        settings.set_many(before)
