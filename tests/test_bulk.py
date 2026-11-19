from pathlib import Path
import os

from PIL import Image

from soloblog import comments
from soloblog import config
from soloblog import contact
from soloblog import images
from soloblog import posts
from conftest import editor_script, save_post


def _upload(name):
    os.makedirs(config.UPLOADS_DIR, exist_ok=True)
    Image.new("RGB", (300, 200), (30, 120, 200)).save(os.path.join(config.UPLOADS_DIR, name), "WEBP")
    images.cache.bump()


def test_media_bulk(admin):
    _upload("bulk-a.webp")
    _upload("bulk-b.webp")
    html = admin.get("/admin/media?tab=unused").text
    assert 'id="media-bulk"' in html and 'form="media-bulk"' in html
    r = admin.post("/admin/media/bulk", data={"action": "trash", "filenames": ["bulk-a.webp", "bulk-b.webp"],
                                              "return_to": "/admin/media?tab=unused"})
    assert r.status_code == 303 and "2%20files" in r.headers["location"].replace("+", "%20")
    trashed = {t["filename"] for t in images.list_trash()}
    assert {"bulk-a.webp", "bulk-b.webp"} <= trashed
    admin.post("/admin/media/bulk", data={"action": "restore", "filenames": ["bulk-a.webp"]})
    admin.post("/admin/media/bulk", data={"action": "delete", "filenames": ["bulk-b.webp"]})
    assert "bulk-a.webp" in {i["filename"] for i in images.list_uploads()}
    assert "bulk-b.webp" not in {t["filename"] for t in images.list_trash()}
    r = admin.post("/admin/media/bulk", data={"action": "trash"})
    assert "Tick" in r.headers["location"]


def test_comments_and_messages_bulk(admin, client):
    slug = save_post(admin, title="Bulk comments")
    ids = [comments.get_db().execute("SELECT id FROM comments WHERE confirm_token=?",
                                     (comments.add_comment(slug, f"Reader {n}", f"r{n}@example.com", "Hi",
                                                           auto_confirm=True),)).fetchone()[0] for n in range(2)]
    html = admin.get("/admin/comments?tab=pending").text
    assert 'id="comments-bulk"' in html and 'form="comments-bulk"' in html
    admin.post("/admin/comments/bulk", data={"action": "approve", "ids": ids})
    assert all(comments.get(i)["approved"] for i in ids)
    admin.post("/admin/comments/bulk", data={"action": "trash", "ids": ids})
    assert all(comments.get(i)["trashed_at"] for i in ids)
    admin.post("/admin/comments/bulk", data={"action": "delete", "ids": ids})
    assert all(comments.get(i) is None for i in ids)

    first, second = contact.add("A", "a@example.com", "One"), contact.add("B", "b@example.com", "Two")
    html = admin.get("/admin/messages").text
    assert 'id="messages-bulk"' in html and 'value="unread"' in html
    # read, then back to unread - as each message's own menu can
    admin.post("/admin/messages/bulk", data={"action": "read", "ids": [first, second]})
    assert all(contact.get(i)["is_read"] for i in (first, second))
    r = admin.post("/admin/messages/bulk", data={"action": "unread", "ids": [first, second]})
    assert not any(contact.get(i)["is_read"] for i in (first, second))
    assert "Marked%202%20messages%20as%20unread" in r.headers["location"]
    # not offered in Trash, so not done there either
    contact.mark_read(first)
    admin.post("/admin/messages/bulk", data={"action": "unread", "ids": [first], "in_tab": "trash"})
    assert contact.get(first)["is_read"]
    admin.post("/admin/messages/bulk", data={"action": "trash", "ids": [first, second]})
    left = {m["id"] for m in contact.list_all(1, 100)}
    assert first not in left and second not in left
    admin.post("/admin/messages/bulk", data={"action": "delete", "ids": [first, second], "in_tab": "trash"})
    assert contact.get(first) is None and contact.get(second) is None


def test_footer_and_social_order(admin, client):
    from soloblog import settings
    before = {k: settings.get(k) for k in ("footer_order", "footer_note", "footer_show_note",
                                            "footer_show_bio", "author_bio", "social_order")}
    settings.set_many({"footer_note": "Note line", "footer_show_note": "1", "footer_show_bio": "1",
                       "author_bio": "Bio line"})
    try:
        admin.post("/admin/settings/style", headers={"hx-request": "true"},
                   data={"footer_order": "note,bogus,bio", "declared_fields": "footer_order"})
        # unknown keys dropped, missing ones kept after (| - a split footer's right side)
        assert settings.get("footer_order") == "note,bio,|,socials,links,small"
        html = client.get("/").text.split("<footer")[1]
        assert html.index("Note line") < html.index("Bio line")
        assert 'data-sortable' in admin.get("/admin/settings?tab=header").text
        admin.post("/admin/settings/profile", headers={"hx-request": "true"},
                   data={"social_order": "github,twitter", "declared_fields": "social_order"})
        assert settings.get("social_order").startswith("github,twitter,")
    finally:
        settings.set_many(before)


def test_media_search(admin):
    _upload("search-sunset.webp")
    _upload("search-other.webp")
    images.set_meta("search-sunset.webp", "Orange sky over the bay", "")
    html = admin.get("/admin/media?tab=unused&q=orange+bay").text
    assert "search-sunset.webp" in html and "search-other.webp" not in html
    assert "search-other.webp" in admin.get("/admin/media?tab=unused&q=other").text
    assert "search-sunset.webp" not in admin.get("/admin/media?tab=unused&kind=audio").text
    # the image picker searches the same words, on the server
    picker = admin.get("/admin/media/picker?q=orange+sky").text
    assert "search-sunset.webp" in picker and "search-other.webp" not in picker
    assert 'id="picker-unused"' in picker and 'hx-swap-oob="true"' in picker
    assert "search-sunset.webp" not in admin.get("/admin/new").text  # not with the page


def test_editor_defaults_and_options(admin):
    import json
    from soloblog import editor_config
    from soloblog import settings
    assert editor_config.pinned_from_setting("bold,italic") == ["bold", "italic", "insert"]
    before = {k: settings.get(k) for k in ("editor_toolbar_rows", "editor_slash", "editor_spellcheck")}
    try:
        admin.post("/admin/settings/editor", headers={"hx-request": "true"},
                   data={"editor_toolbar_rows": "all", "editor_spellcheck": "1",
                         "declared_fields": "editor_toolbar_rows,editor_slash,editor_spellcheck"})
        prefs = json.loads(admin.get("/admin/new").text.split("window.EDITOR_PREFS = ")[1].split(";</script>")[0])
        # "Everything" is gone: it's the one row, Normal
        assert prefs["rows"] == "one" and prefs["slash"] is False and prefs["spellcheck"] is True
        assert settings.get("editor_toolbar_rows") == "one"
        admin.post("/admin/settings/editor", headers={"hx-request": "true"},
                   data={"editor_toolbar_rows": "none", "declared_fields": "editor_toolbar_rows"})
        page = admin.get("/admin/new").text
        assert 'data-editor-toolbar="none"' in page
        # the fixed part, in the editor's kept script
        script = editor_script(admin, page)
        fixed = json.loads(script.split("Object.assign(window.EDITOR_PREFS || {}, ")[1].split(");\n")[0])
        assert fixed["groups"]["heading"] == "Text" and fixed["headings"][0] == "paragraph"
    finally:
        settings.set_many(before)



def test_editor_names_placeholder_and_minimal(admin):
    import json
    from soloblog import editor_config
    from soloblog import settings
    # one name per command: the tooltips, the ⋯ menu and Settings all read these
    assert editor_config.LABELS["code"] == "Code block" and editor_config.LABELS["inline-code"] == "Inline code"
    before = {k: settings.get(k) for k in ("editor_toolbar_rows", "editor_slash")}
    try:
        settings.set_many({"editor_slash": "1"})
        prefs = json.loads(admin.get("/admin/new").text.split("window.EDITOR_PREFS = ")[1].split(";</script>")[0])
        assert "Type /" in prefs["placeholder"]
        # no slash menu, no talk of one
        settings.set_many({"editor_slash": "0"})
        prefs = json.loads(admin.get("/admin/new").text.split("window.EDITOR_PREFS = ")[1].split(";</script>")[0])
        assert prefs["placeholder"] and "/" not in prefs["placeholder"]
        page = admin.get("/admin/settings?tab=editor").text
        assert "Icons - a row of the buttons you choose" in page and "Menus - like a word processor" in page \
            and "None - the slash menu" in page \
            and "Everything" not in page
    finally:
        settings.set_many(before)


def test_editor_shortcuts_stay_clear_of_the_browser():
    import re
    from soloblog.routes import editor
    js = editor.EDITOR_INIT_JS
    # the ones a browser keeps for itself: full screen, Firefox's Reader
    # view, console and history
    for taken in ("'F11'", "'F9'", "Shift-Ctrl-K", "Shift-Cmd-K", "Shift-Ctrl-H", "Shift-Cmd-H"):
        assert taken not in js, taken
    # CodeMirror only reads a key with Shift first - "Ctrl-Shift-9" never fires
    assert not re.search(r"'(Cmd|Ctrl)-(Alt-)?Shift-", js)
    shown = {name: win for name, win, mac in editor._SHORTCUT_KEYS}
    assert shown["Save"] == "Ctrl+S" and shown["Heading"] == "Ctrl+Alt+2" and "Heading 1" not in shown
    assert all("F9" not in k and "F11" not in k for k in shown.values())
    # the help lists every shortcut the toolbar shows
    for key in ("Ctrl+Shift+X", "Ctrl+Alt+H", "Ctrl+E", "Ctrl+Shift+8", "Ctrl+Alt+P", "Ctrl+Shift+F", "Ctrl+/"):
        assert key in shown.values(), key

def test_animations_setting(admin, client):
    from soloblog import settings
    settings.set_many({"page_animations": "1"})
    try:
        assert 'data-animate="1"' in client.get("/").text
        admin.post("/admin/settings/style", headers={"hx-request": "true"},
                   data={"declared_fields": "page_animations"})
        assert settings.get("page_animations") == "0" and "data-animate" not in client.get("/").text
    finally:
        settings.set_many({"page_animations": "1"})


def test_migrations_from_one_file(monkeypatch):
    import sqlite3
    import pytest
    from soloblog import db
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    monkeypatch.setattr(db._local, "conn", conn, raising=False)
    # a new database: the one schema file makes everything
    db.run_migrations()
    columns = {r["name"] for r in conn.execute("PRAGMA table_info(posts)")}
    assert {"unlisted", "seo_title", "share_image", "heading_fold", "cover_width"} <= columns
    assert "hide_list_cover" in columns
    files = sorted(f for f in os.listdir(os.path.join(os.path.dirname(db.__file__), "migrations")) if f.endswith(".sql"))
    assert files[0] == "001_schema.sql"
    # 002-016 were folded in: sites from before have those names recorded
    assert not [f for f in files[1:] if int(f[:3]) <= 16], files
    # a new site starts without page layouts, and with what 013-015 added
    assert "layout" not in columns and "section_space" in columns
    assert {"dark_version", "phone_version"} <= {r["name"] for r in conn.execute("PRAGMA table_info(image_meta)")}
    assert {"sides"} <= columns and "last_used_via" in {r["name"] for r in conn.execute("PRAGMA table_info(api_keys)")}
    assert [r["filename"] for r in conn.execute("SELECT filename FROM schema_migrations")] == files
    db.run_migrations()  # and running again changes nothing
    # a site from before the files were folded into one (the demo, the
    # project's website) ran 001-008 already: it's left as it is, posts and all
    live = sqlite3.connect(":memory:")
    live.row_factory = sqlite3.Row
    monkeypatch.setattr(db._local, "conn", live, raising=False)
    live.execute("CREATE TABLE schema_migrations (filename TEXT PRIMARY KEY, applied_at TEXT)")
    live.executescript(Path(os.path.join(os.path.dirname(db.__file__), "migrations", "001_schema.sql")).read_text())
    live.executemany("INSERT INTO schema_migrations (filename) VALUES (?)",
                     [(f"0{n:02d}_x.sql",) for n in range(2, 13)] + [("001_schema.sql",)])
    live.execute("INSERT INTO posts (slug, title, created_at, updated_at) VALUES ('hello', 'Hello', '2026-01-01', "
                 "'2026-01-01')")
    db.run_migrations()
    assert live.execute("SELECT visibility, sound FROM posts WHERE slug='hello'").fetchone()["visibility"] == "public"
    assert "in_wiki" in columns and "title_style" in columns
    # a database from the old development files can't be brought up to date
    old = sqlite3.connect(":memory:")
    old.row_factory = sqlite3.Row
    monkeypatch.setattr(db._local, "conn", old, raising=False)
    old.execute("CREATE TABLE schema_migrations (filename TEXT PRIMARY KEY, applied_at TEXT)")
    old.execute("INSERT INTO schema_migrations (filename) VALUES ('032_post_reading.sql')")
    with pytest.raises(RuntimeError):
        db.run_migrations()


def test_split_footer_and_stacked_header(client):
    from soloblog import settings
    keys = ("footer_order", "footer_layout", "footer_note", "footer_show_note", "footer_show_bio",
            "author_bio", "header_align")
    before = {k: settings.get(k) for k in keys}
    settings.set_many({"footer_note": "Note line", "footer_show_note": "1", "footer_show_bio": "1",
                       "author_bio": "Bio line", "footer_order": "bio,|,note", "footer_layout": "split",
                       "header_align": "stacked"})
    try:
        html = client.get("/").text
        footer = html.split("<footer")[1]
        assert "sm:justify-between" in footer and "sm:items-end" in footer
        right = footer[footer.index("sm:items-end"):]
        assert "Note line" in right and "Bio line" not in right
        # stacked: the menu on its own row under the title, from lg up
        # the menu on its own row, folded into the menu button when it won't fit
        assert "hidden md:flex group-data-[nav-folded]/header:hidden! justify-center" in html.split("<main")[0]
        settings.set_many({"footer_layout": "center"})
        footer = client.get("/").text.split("<footer")[1]
        assert "sm:items-end" not in footer and "items-center text-center" in footer
    finally:
        settings.set_many(before)


def test_writing_width_and_markdown_marks(admin):
    from soloblog import settings
    before = {k: settings.get(k) for k in ("editor_width", "editor_marks")}
    try:
        html = admin.get("/admin/new").text
        assert 'data-editor-width="comfortable"' in html and 'data-editor-marks="dimmed"' in html
        admin.post("/admin/settings/editor", headers={"hx-request": "true"},
                   data={"editor_width": "wide", "editor_marks": "full", "declared_fields": "editor_width,editor_marks"})
        html = admin.get("/admin/new").text
        assert 'data-editor-width="wide"' in html and 'data-editor-marks="full"' in html
        # anything else is the default, never stored as sent
        admin.post("/admin/settings/editor", headers={"hx-request": "true"},
                   data={"editor_width": "<script>", "editor_marks": "x", "declared_fields": "editor_width,editor_marks"})
        assert settings.get("editor_width") == "comfortable" and settings.get("editor_marks") == "dimmed"
        page = admin.get("/admin/settings?tab=editor").text
        assert "Writing width" in page and "Markdown marks" in page
    finally:
        settings.set_many(before)


def test_all_media_shows_unused_files_with_a_pill(admin):
    _upload("pill-lonely.webp")
    _upload("pill-used.webp")
    save_post(admin, title="Uses a picture", body="![a picture](/uploads/pill-used.webp)")
    html = admin.get("/admin/media?q=pill-").text
    assert ">All<" in html and "pill-lonely.webp" in html and "pill-used.webp" in html
    lonely = html[html.index("pill-lonely.webp"):][:3000]
    used = html[html.index("pill-used.webp"):][:3000]
    assert ">Unused</span>" in lonely.split("card card-border")[0]
    assert ">Unused</span>" not in used.split("card card-border")[0]


def test_lists_search_filter_and_sort(admin):
    """Comments, Messages, Members and Subscribers have the toolbar Posts
    and Media have: search, filters, sort, and Clear once narrowed."""
    from soloblog import members, newsletter, settings
    slug = save_post(admin, title="Toolbar comments")
    for who, text in (("Ada", "Lovely garden"), ("Bob", "Nice bikes")):
        comments.add_comment(slug, who, f"{who.lower()}@example.com", text, auto_confirm=True)
    html = admin.get("/admin/comments?tab=pending&q=garden").text
    assert "Lovely garden" in html and "Nice bikes" not in html and 'name="q"' in html
    assert "Clear" in html and "Approve all" not in html
    old = admin.get(f"/admin/comments?tab=pending&post={slug}&sort=oldest").text
    assert old.index("Lovely garden") < old.index("Nice bikes")
    # one way to act on them all: tick the box above the list, then Select all
    for tab in ("pending", "approved"):
        page = admin.get(f"/admin/comments?tab={tab}").text
        assert "Approve all" not in page and "Trash all" not in page and "/trash-all" not in page
    assert admin.post("/admin/comments/approve-all").status_code in (404, 405)

    contact.add("Carol", "carol@example.com", "About the workshop")
    contact.add("Dan", "dan@example.com", "Hello there")
    html = admin.get("/admin/messages?q=workshop").text
    assert "About the workshop" in html and "Hello there" not in html and "Search messages" in html

    members.add("zed@sorting.test", "Zed")
    members.add("amy@sorting.test", "Amy")
    html = admin.get("/admin/members?sort=name&q=sorting.test").text
    assert html.index("amy@sorting.test") < html.index("zed@sorting.test") and "Search by email or name" in html

    newsletter.subscribe_confirmed("in@example.com")
    newsletter.subscribe("waiting@example.com")
    html = admin.get("/admin/newsletter?state=unconfirmed").text
    assert "waiting@example.com" in html and "in@example.com" not in html and "Search by email" in html
    # nonsense in the address falls back, never an error
    assert admin.get("/admin/newsletter?state=x&sort=y").status_code == 200
    assert admin.get("/admin/members?sort=1;DROP").status_code == 200

    # off: a link that turns it on, not directions around the admin
    settings.set_many({"newsletter_mode": "", "contact_enabled": "0"})
    assert 'href="/admin/settings?tab=newsletter"' in admin.get("/admin/newsletter").text
    assert 'href="/admin/settings?tab=messages&amp;panel=messages-contact"' in admin.get("/admin/messages").text
    settings.set_many({"newsletter_mode": "builtin", "email_provider": ""})
    assert "Set up email" in admin.get("/admin/newsletter").text


def test_mentions_stats_and_row_menus(admin):
    from soloblog import newsletter
    from soloblog.db import get_db
    slug = save_post(admin, title="Mentioned post")
    for n, (who, approved) in enumerate((("Wren", 0), ("Yara", 1))):
        get_db().execute("INSERT INTO webmentions (post_slug, source, target, kind, author_name, author_url, "
                         "author_photo, content, published, approved, received_at) VALUES (?, ?, ?, 'mention', ?, "
                         "'', '', ?, '', ?, ?)", (slug, f"https://m{n}.example/x", f"/post/{slug}", who,
                                                  f"{who} wrote", approved, f"2026-10-0{n + 1}T00:00:00"))
    get_db().commit()
    html = admin.get("/admin/comments?tab=mentions&q=Wren").text
    assert "Wren wrote" in html and "Yara wrote" not in html and "Search mentions" in html
    html = admin.get("/admin/comments?tab=mentions&state=approved").text
    assert "Yara wrote" in html and "Wren wrote" not in html
    assert admin.get("/admin/comments?tab=mentions&state=x&sort=y").status_code == 200

    # the range picker names itself, like every other list filter
    html = admin.get("/admin/stats").text
    assert 'popovertarget="filter-range"' in html and 'data-go="/admin/stats?range="' not in html

    # a lone Remove sits in the row's ⋯ menu on a phone too
    newsletter.subscribe_confirmed("menu@example.com")
    assert 'popovertarget="subscriber-acts-' in admin.get("/admin/newsletter?q=menu@").text


def test_settings_links_open_their_panel():
    """A link to one setting (?panel=) opens it, without a search."""
    from soloblog import js
    assert "if (!find && !params.get('panel') && !next) return;" in js.read("index_search.js")


def test_search_dialogs_fit_above_the_keyboard(admin):
    """A phone's keyboard shrinks what you can see, not 100dvh: the
    pickers and site search fit --seen-h, so Close stays in sight (#36)."""
    from soloblog import js
    from soloblog.ui import SEARCH_DIALOG_BOX
    assert "--seen-h" in js.read("page_helpers.js") and "--seen-h" in SEARCH_DIALOG_BOX
    html = admin.get("/admin/new").text
    dialogs = [d for d in ("media-picker-dialog", "link-picker-dialog", "template-start-dialog", "template-dialog",
                                      "search-modal")
               if f'id="{d}"' in html]
    assert len(dialogs) >= 3 and html.count(SEARCH_DIALOG_BOX.split()[-1]) == len(dialogs)


def test_back_to_top_stays_in_its_corner():
    """Where every site keeps it - over the footer, not pushed up by it -
    but above the save bar while that's pinned to the foot."""
    from soloblog import app as soloblog_app
    from soloblog.ui import ScrollToTopButton
    from fasthtml.common import to_xml
    assert "FloatClearance" not in soloblog_app.APP_JS
    html = to_xml(ScrollToTopButton())
    # set on <html> by the scripts (syncUnsaved, _markSound), not read with body:has()
    assert "bottom-6" in html and "[html[data-unsaved]_&amp;]:bottom-20" in html
    assert "[html[data-sound]_&amp;]:bottom-16" in html and "body:has(" not in html
    assert "function syncUnsaved()" in soloblog_app.ADMIN_JS and "data-sound" in soloblog_app.APP_JS


def test_more_below_shares_the_close_row(admin):
    html = admin.get("/admin/new").text
    assert 'data-scroll-more="link-picker-more"' in html and 'id="link-picker-more"' in html


def test_folded_migration_numbers_never_come_back():
    """002-008 were folded into 001 for 1.0.0-beta; the sites from before have
    those names recorded and would skip a new file that reused one."""
    from soloblog import db
    names = os.listdir(os.path.join(os.path.dirname(db.__file__), "migrations"))
    assert not [n for n in names if n[:3] in {f"00{i}" for i in range(2, 9)}]


def test_accessibility_fixes_stay(admin, client):
    """axe-core's findings 15 and 17: the site header is a landmark, a side
    panel's title isn't a link inside its fold button, closed slide-overs
    are out of reach, and the admin drawer opens with a real button."""
    home = client.get("/").text
    assert "<header" in home and "data-site-header" in home.split("<header", 1)[1][:200]
    assert '<summary class="collapse-title font-semibold text-sm min-h-0 py-3"><a' not in home
    editor = admin.get("/admin/new").text
    tag = next(t for t in editor.split("<") if 'id="post-settings-panel"' in t)
    assert " inert" in tag.split(">")[0]
    page = admin.get("/admin/posts").text
    assert 'data-toggles="admin-drawer"' in page and 'aria-hidden="true" tabindex="-1"' in page


def test_one_author_section_and_wide_templates_keep_panels_below(admin, client):
    """The About the author side panel takes the place of the one under
    the post; a wide page (Page width: Wide) puts the side panels after it,
    not out past its wider content."""
    from soloblog import settings
    keys = ("side_author", "side_author_where", "author_name", "author_bio")
    before = {k: settings.get(k) for k in keys}
    marker = 'text-base font-semibold text-accent mb-2">Author<'
    plain = save_post(admin, title="Plain author post")
    deck = save_post(admin, title="Deck author post", body="One\n\nTwo")
    posts.write(deck, page_width="wide")
    try:
        settings.set_many({"author_name": "Ada", "author_bio": "Writes things", "side_author": "off"})
        assert marker in client.get(f"/post/{plain}").text
        settings.set_many({"side_author": "right", "side_author_where": "posts"})
        page = client.get(f"/post/{plain}").text
        assert marker not in page and 'data-panel="side-author"' in page and 'data-side-panel="right"' in page
        slides = client.get(f"/post/{deck}").text
        assert 'data-panel="side-author"' in slides and 'data-side-panel="right"' not in slides
    finally:
        settings.set_many(before)


def test_bucket_errors_are_words_with_details_in_the_log():
    from soloblog import storage
    from soloblog.routes.backup_routes import _bucket_problem
    raw = storage.StorageError("upload failed (403): b'<Error><Code>AccessDenied</Code></Error>'")
    said = _bucket_problem("The backup didn't reach your bucket", raw)
    assert "403" not in said and "<Error>" not in said and "Log" in said
    passphrase = storage.StorageError("wrong BACKUP_PASSPHRASE, or the backup is damaged")
    assert "BACKUP_PASSPHRASE" in _bucket_problem("Couldn't restore that backup", passphrase)


def test_members_and_subscribers_say_where_they_stand(admin):
    """A plan that's been ended says so on the row, Give paid access says
    how long, and a subscriber who's a member shows their name and tier."""
    from soloblog import members, newsletter
    m = members.add("ending@example.com", "Edie", "paid")
    members.update(m["id"], stripe_subscription_id="sub_x", subscription_status="active", cancel_at_period_end=1,
                   plan_amount=400, plan_currency="usd", plan_interval="month")
    free = members.add("given@example.com", "Gil")
    page = admin.get("/admin/members?q=example.com").text
    assert "Paid · ending" in page
    assert "It lasts until you take it away" in page and "given@example.com" in page
    newsletter.subscribe_confirmed("ending@example.com")
    subs = admin.get("/admin/newsletter?q=ending@").text
    assert "Edie" in subs and ">Paid member<" in subs
    assert free


def test_health_dot_is_known_soon_after_start():
    from soloblog import health_remote
    assert health_remote.FIRST_AFTER <= 60


def test_ready_page_counts_only_its_steps(admin):
    page = admin.get("/admin/welcome?step=done").text
    # six jobs, email first - the setup's own screens aren't one of them
    assert "of 6 done" in page and "Whenever you like" in page and "Set up email" in page
    assert "Set up the site" not in page
    assert page.index("Whenever you like") < page.index("Explore settings")


def test_posts_bulk_fits_its_selection(admin):
    """An empty tag is refused in words; Publish and Move to drafts only
    change the posts they fit and say how many were left; a scheduled post
    published goes live now; Export gives just the ticked ones."""
    from soloblog import posts
    a = save_post(admin, title="Bulk live one")
    b = save_post(admin, title="Bulk draft one", published="")
    c = save_post(admin, title="Bulk later one", scheduled_at="2099-01-01T09:00")
    r = admin.post("/admin/posts/bulk", data={"action": "tag", "tag": "  ", "slugs": [a]})
    assert "Type+a+tag" in r.headers["location"].replace("%20", "+")
    page = admin.get("/admin/posts?q=Bulk").text
    assert 'data-needs="tag"' in page and 'data-bulk-for="draft,scheduled"' in page
    assert 'data-state="draft"' in page and 'data-state="scheduled"' in page and 'data-state="published"' in page
    r = admin.post("/admin/posts/bulk", data={"action": "publish", "slugs": [a, b, c]})
    loc = r.headers["location"].replace("%20", " ").replace("+", " ")
    assert "2 posts" in loc and "1 already were" in loc
    assert posts.bulk_state(posts.get_post(c)) == "published" and posts.get_post(b)["published"]
    r = admin.post("/admin/posts/bulk", data={"action": "export", "slugs": [a]})
    assert r.headers["content-type"].startswith("text/csv") and "Bulk live one" in r.text \
        and "Bulk draft one" not in r.text


def test_select_all_pages_stays_inside_the_filters(admin):
    """Select all N rebuilds the set from the list's own filters - a
    search, a tag - and never reaches anything outside them."""
    from soloblog import posts
    inside = [save_post(admin, title=f"Zebra stripe {i}", tags="zebras") for i in range(3)]
    outside = save_post(admin, title="Zebra stripe outsider")
    page = admin.get("/admin/posts?tag=zebras").text
    assert 'data-bulk-total="3"' in page and 'name="in_tag" value="zebras"' in page
    r = admin.post("/admin/posts/bulk", data={"action": "draft", "all_matching": "1", "in_status": "all",
                                              "in_tag": "zebras", "slugs": inside[:1]})
    assert all(not posts.get_post(s)["published"] for s in inside)
    assert posts.get_post(outside)["published"]
    # an unknown tab isn't widened to All
    r = admin.post("/admin/posts/bulk", data={"action": "draft", "all_matching": "1", "in_status": "trash"})
    assert "Choose+posts" in r.headers["location"].replace("%20", "+") and posts.get_post(outside)["published"]
    # the Type filter counts as one of them
    page = save_post(admin, title="Zebra stripe page", pinned="1", pin_location="footer")
    html = admin.get("/admin/posts?kind=pages&q=zebra").text
    assert 'data-bulk-total="1"' in html and 'name="in_kind" value="pages"' in html
    admin.post("/admin/posts/bulk", data={"action": "draft", "all_matching": "1", "in_status": "all",
                                          "in_q": "zebra", "in_kind": "pages", "slugs": [page]})
    assert not posts.get_post(page)["published"] and posts.get_post(outside)["published"]
    for slug in inside + [outside, page]:
        posts.delete_post(slug)


def test_select_all_on_messages_comments_and_media(admin):
    from soloblog import contact, comments
    keep = contact.add("Kept", "kept@example.com", "Nothing about seals")
    for i in range(2):
        contact.add("W", "w@example.com", f"About walruses {i}")
    admin.post("/admin/messages/bulk", data={"action": "trash", "all_matching": "1", "in_q": "walruses"})
    left = [m["body"] for m in contact.list_all(1, 1000)]
    assert "Nothing about seals" in left and not any("About walruses" in b for b in left)
    admin.post("/admin/messages/bulk", data={"action": "delete", "all_matching": "1", "in_tab": "trash"})
    assert contact.count("", trash=True) == 0
    contact.delete(keep)  # later tests count unread messages
    slug = save_post(admin, title="Select all comments")
    for i in range(2):
        comments.add_comment(slug, "Reader", "r@example.com", f"Otter note {i}", auto_confirm=True)
    # an action that isn't the tab's own is refused, even with all_matching
    r = admin.post("/admin/comments/bulk", data={"action": "delete", "all_matching": "1", "in_tab": "pending",
                                                 "in_q": "Otter note"})
    assert "Tick+some" in r.headers["location"].replace("%20", "+")
    admin.post("/admin/comments/bulk", data={"action": "approve", "all_matching": "1", "in_tab": "pending",
                                             "in_post": slug, "in_q": "Otter note"})
    assert comments.count_by_status("approved", slug, q="Otter note") == 2
    r = admin.post("/admin/media/bulk", data={"action": "delete", "all_matching": "1", "in_tab": "gallery"})
    assert "Tick+some" in r.headers["location"].replace("%20", "+")


def test_template_name_is_the_title_as_real_text(admin):
    slug = save_post(admin, title="Weekly bread notes")
    page = admin.get(f"/admin/edit/{slug}").text
    field = next(t for t in page.split("<") if 'name="template_name"' in t)
    assert 'value="Weekly bread notes"' in field and 'data-follows="title"' in field
    assert 'data-needs="template_name"' in page


def test_a_post_places_its_own_side_panels(admin, client):
    """Post settings > Page: each side panel's place for this post wins
    over Settings; Show's Side panels box still turns them all off; About
    the author still shows once; a wide page puts them after the post;
    the choice lives in the post's file, so it survives a re-read."""
    from soloblog import posts, settings
    assert posts.clean_sides("tags=left, author = OFF, archive=sideways, x=left") == "tags=left,author=off"
    keys = ("side_tags", "side_tags_where", "side_author", "side_author_where", "author_name", "author_bio")
    before = {k: settings.get(k) for k in keys}
    marker = 'text-base font-semibold text-accent mb-2">Author<'
    try:
        settings.set_many({"side_tags": "off", "side_author": "off", "author_name": "Ada", "author_bio": "Bio",
                           "side_tags_where": "", "side_author_where": ""})
        slug = save_post(admin, title="Own sides post", tags="otters", sides_tags="left", sides_author="right")
        assert posts.get_post(slug)["sides"] == "tags=left,author=right"
        page = client.get(f"/post/{slug}").text
        assert 'data-panel="side-tags"' in page and 'data-side-panel="left"' in page
        assert 'data-panel="side-author"' in page and marker not in page  # once
        # the file has it; a re-read from the files keeps it
        assert "sides: tags=left, author=right" in Path(posts._path(slug)).read_text(encoding="utf-8")
        # the database rebuilt from the files (a restore): it comes back
        posts.get_db().execute("DELETE FROM posts WHERE slug=?", (slug,))
        posts.get_db().commit()
        posts.reindex_from_disk()
        assert posts.get_post(slug)["sides"] == "tags=left,author=right"
        # a save that doesn't send them keeps them
        posts.write(slug, title="Own sides post", summary="changed")
        assert posts.get_post(slug)["sides"] == "tags=left,author=right"
        # its own Off hides a panel Settings shows
        settings.set_many({"side_author": "right", "side_author_where": "posts"})
        save_post(admin, slug=slug, title="Own sides post", sides_tags="", sides_archive="", sides_author="off")
        page = client.get(f"/post/{slug}").text
        assert 'data-panel="side-author"' not in page and marker in page
        # Show without Side panels: none, whatever it chose
        save_post(admin, slug=slug, title="Own sides post", sides_tags="left", extras=["meta"],
                  extras_before="")
        assert 'data-panel="side-tags"' not in client.get(f"/post/{slug}").text
        # a wide page: after the post, not beside it
        deck = save_post(admin, title="Own sides deck", body="A\n\nB", sides_tags="left", tags="otters")
        posts.write(deck, page_width="wide")
        page = client.get(f"/post/{deck}").text
        assert 'data-panel="side-tags"' in page and 'data-side-panel="left"' not in page
        # duplicated, it keeps them
        assert posts.get_post(posts.duplicate_post(deck))["sides"] == "tags=left"
        # the editor shows the choices, greyed out without Show's box
        editor = admin.get(f"/admin/edit/{deck}").text
        assert 'name="sides_tags"' in editor and 'data-off-unless="extras=sides"' in editor
    finally:
        settings.set_many(before)


def test_messages_read_trash_and_export(admin):
    from soloblog import contact
    one, two = contact.add("Ann", "ann@example.com", "=HYPERLINK(1)"), contact.add("Bo", "bo@example.com", "Hi")
    try:
        admin.get("/admin/messages")
        assert contact.get(one)["is_read"] == 0
        admin.post("/admin/messages/read", data={"message_id": one})
        assert contact.get(one)["is_read"] == 1 and "Mark as unread" in admin.get("/admin/messages").text
        admin.post("/admin/messages/unread", data={"message_id": one})
        admin.post("/admin/messages/bulk", data={"action": "read", "ids": [one, two]})
        assert contact.get(one)["is_read"] == contact.get(two)["is_read"] == 1
        csv = admin.post("/admin/messages/bulk", data={"action": "export", "ids": [one]})
        assert csv.headers["content-type"].startswith("text/csv") and "'=HYPERLINK(1)" in csv.text
        assert "bo@example.com" not in csv.text
        # trash, with Undo; out of the inbox and the count
        r = admin.post("/admin/messages/delete", data={"message_id": one})
        assert "undo=" in r.headers["location"] and contact.get(one)["trashed_at"]
        assert one not in [m["id"] for m in contact.list_all(1, 1000)]
        assert "=HYPERLINK(1)" in admin.get("/admin/messages?tab=trash").text
        admin.post("/admin/messages/restore", data={"message_id": one})
        assert not contact.get(one)["trashed_at"]
        # in trash, only restore or delete for good - not export
        admin.post("/admin/messages/bulk", data={"action": "trash", "ids": [one, two]})
        r = admin.post("/admin/messages/bulk", data={"action": "export", "ids": [one], "in_tab": "trash"})
        assert r.status_code == 303
        admin.post("/admin/messages/delete-forever", data={"message_id": one})
        assert contact.get(one) is None
        admin.post("/admin/messages/empty-trash")
        assert contact.get(two) is None
    finally:
        contact.delete(one)
        contact.delete(two)


def test_a_footer_in_columns(admin, client):
    # a footer page with pages under it is a column, its title the heading
    from soloblog import posts, settings
    keys = ("footer_order", "footer_layout", "footer_show_pages", "footer_show_bio", "author_bio")
    before = {k: settings.get(k) for k in keys}
    help_slug = save_post(admin, title="Help centre", pinned="1", pin_location="footer")
    faq = save_post(admin, title="Questions", pinned="1", pin_location="footer", parent_slug=help_slug)
    alone = save_post(admin, title="Imprint", pinned="1", pin_location="footer")
    try:
        assert posts.get_post(faq)["parent_slug"] == help_slug
        # the editor offers footer pages to go under, and the Pinned list's Move menu too
        assert 'id="parent-slug-footer"' in admin.get(f"/admin/edit/{alone}").text
        assert posts.set_parent(alone, help_slug) and posts.set_parent(alone, "")
        assert not posts.set_parent(alone, faq)  # one level deep
        settings.set_many({"footer_layout": "columns", "footer_show_pages": "1", "footer_show_bio": "1",
                           "author_bio": "Bio line", "footer_order": "bio,links,note,small"})
        footer = client.get("/").text.split("<footer")[1]
        assert "sm:grid-cols-[repeat(auto-fit,minmax(9rem,1fr))]" in footer
        assert footer.index("Bio line") < footer.index("Imprint") < footer.index("Help centre") < footer.index("Questions")
        assert "font-semibold" in footer[footer.index("Help centre") - 300:footer.index("Help centre")]
    finally:
        settings.set_many(before)
        for slug in (faq, help_slug, alone):
            admin.post("/admin/delete", data={"slug": slug})


def test_ticking_posts_in_trash(admin):
    from soloblog import posts
    a, b, c = (save_post(admin, title=f"Trash me {n}") for n in "abc")
    for slug in (a, b, c):
        posts.delete_post(slug)
    html = admin.get("/admin/posts?status=trash").text
    assert 'id="trash-bulk"' in html and 'form="trash-bulk"' in html and 'value="restore"' in html
    r = admin.post("/admin/posts/trash-bulk", data={"action": "restore", "slugs": [a, b]})
    assert "Restored%202%20posts" in r.headers["location"]
    assert posts.get_post(a) and posts.get_post(b) and not posts.get_post(c)
    # nothing ticked, or something that isn't in trash: nothing happens
    assert "Tick" in admin.post("/admin/posts/trash-bulk", data={"action": "delete", "slugs": [a]}).headers["location"]
    assert posts.get_post(a)
    admin.post("/admin/posts/trash-bulk", data={"action": "delete", "slugs": ["../../etc/passwd", c]})
    assert c not in {t["slug"] for t in posts.list_trash()}
    for slug in (a, b):
        posts.delete_post(slug)
    admin.post("/admin/posts/trash-bulk", data={"action": "delete", "all_matching": "1"})
    assert not {a, b} & {t["slug"] for t in posts.list_trash()}


def test_tags_can_be_searched(admin):
    save_post(admin, title="Tagged for search", tags="sourdough, cycling")
    page = admin.get("/admin/posts?status=tags&q=sour").text
    assert 'id="live-search"' in page and 'value="sourdough"' in page and 'value="cycling"' not in page
    assert "matching “sour”" in page
    assert "Nothing matches “zzz”" in admin.get("/admin/posts?status=tags&q=zzz").text


def test_followers_say_how_many_more(monkeypatch):
    from fasthtml.common import to_xml
    from soloblog import fediverse, settings
    from soloblog.routes.admin_settings import FediversePanel
    monkeypatch.setattr(fediverse, "reachable", lambda: "")
    monkeypatch.setattr(fediverse, "follower_count", lambda: 280)
    monkeypatch.setattr(fediverse, "list_followers", lambda n: [{"handle": f"@f{i}@example.social"} for i in range(n)])
    html = to_xml(FediversePanel({**settings.get_all(), "activitypub_enabled": "1"}))
    assert "280 followers" in html and "And 230 more" in html
    monkeypatch.setattr(fediverse, "follower_count", lambda: 3)
    monkeypatch.setattr(fediverse, "list_followers", lambda n: [{"handle": "@a@example.social"}] * 3)
    assert "more" not in to_xml(FediversePanel({**settings.get_all(), "activitypub_enabled": "1"}))
