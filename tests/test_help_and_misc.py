from pathlib import Path
from soloblog import config
from soloblog import settings
from conftest import save_post


def test_help_page_shows_the_user_guide(admin, client):
    # Help opens at the guide's start; the reference has the details
    html = admin.get("/admin/help").text
    assert "data-toc" in html and "Set up the site" in html and "?tab=troubleshooting" in html
    # every section has its entry on its own page, and the reference points there
    entries = admin.get("/admin/help?tab=sections-templates").text
    assert "Section: Recipe facts" in entries and "Section: Pricing" in entries and "Key: value index" in entries
    html = admin.get("/admin/help?tab=reference").text
    assert "?tab=sections-templates" in html
    # the gallery example in the guide is an example, not a gallery
    assert "/uploads/one.webp" in html and "<img" not in html.split("/uploads/one.webp")[0][-300:]
    # sections fold and each heading has its copy-link button, like a post
    assert html.count("copyHeadingLink") > 20 and "<details" in html.split('data-toc')[-1]
    # admin pages always get back-to-top, whatever the public site's setting
    assert 'id="scroll-top-btn"' in html
    assert 'href="/admin/help"' in admin.get("/admin/settings").text
    assert client.get("/admin/help").status_code in (303, 302)


def test_editor_help_has_examples_for_everything(admin, client):
    page = admin.get("/admin/new").text
    # the panel's parts come the first time it opens - not in every editor page
    assert 'id="editor-help-parts"></div>' in page and 'data-help-section="start"' not in page
    html = page + admin.get("/admin/editor/help").text
    assert not admin.get("/admin/editor/help").text.startswith("<!doctype")
    assert client.get("/admin/editor/help").status_code in (302, 303)
    for section in ("start", "formatting", "blocks", "media", "editor", "templates", "shortcuts"):
        assert f'data-help-section="{section}"' in html, section
    assert "!!! tip" in html and "```gallery masonry" in html and "Landing page" in html
    assert 'id="editor-help-panel"' in html and "data-help-insert" in html
    # one panel: the old dialogs are gone
    assert "editor-help-dialog" not in html and "editor-shortcuts-dialog" not in html


def test_client_ip_header(client, monkeypatch):
    from soloblog import ratelimit

    class Req:
        headers = {"cf-connecting-ip": "203.0.113.9", "x-forwarded-for": "10.0.0.1, 198.51.100.2"}
        client = None
    assert ratelimit.client_ip(Req()) == "198.51.100.2"
    monkeypatch.setattr(config, "CLIENT_IP_HEADER", "cf-connecting-ip")
    assert ratelimit.client_ip(Req()) == "203.0.113.9"


def test_threads_sharing(admin, client):
    settings.set_many({"social_threads": "https://www.threads.net/@ann"})
    try:
        slug = save_post(admin, title="Share on Threads")
        assert "https://www.threads.net/intent/post?text=" in client.get(f"/post/{slug}").text
    finally:
        settings.set_many({"social_threads": ""})


def test_help_sections_come_from_docs(admin):
    for tab, words in (("faq", "Can several people write"), ("deployment", "About the links in this guide"),
                       ("api", "Webhooks"), ("sponsor", "ko-fi.com/zrplus_studio")):
        html = admin.get(f"/admin/help?tab={tab}").text
        assert words in html, tab
    faq = admin.get("/admin/help?tab=faq").text
    # links between the docs stay in Help; the rest of the repository opens on GitHub
    assert 'href="/admin/help?tab=deployment#put-it-on-a-hosting-service"' in faq
    assert 'href="/admin/help?tab=run#update-soloblog"' in faq
    assert f'href="{config.PROJECT_URL}/blob/master/SUPPORT.md' in faq
    # the developers' guide is for people changing the code - on GitHub, not in Help
    assert "Developing Soloblog" not in admin.get("/admin/help?tab=development").text
    # an old address, or one that's wrong, opens the guide's start
    for tab in ("guide", "nonsense"):
        assert "Set up the site" in admin.get(f"/admin/help?tab={tab}").text
    assert 'href="/admin/help?tab=sponsor"' in admin.get("/admin/settings").text


def test_a_menu_parent_opens_its_own_page(admin, client):
    parent = save_post(admin, title="Menu parent", pin_location="header")
    child = save_post(admin, title="Menu child", pin_location="header", parent_slug=parent)
    html = client.get("/").text
    submenu = html.split(f'id="pin-submenu-{parent}-d"')[1].split("</ul>")[0]
    # its name is the link to its page, its arrow opens the sub-pages - the
    # list led with the parent too, the same name twice
    assert f'href="/{child}"' in submenu and f'href="/{parent}"' not in submenu
    row = html.split('data-nav-menu')[1]
    parent_item = row[row.index('data-nav-parent'):row.index(f'id="pin-submenu-{parent}-d"')]
    assert f'href="/{parent}"' in parent_item and 'aria-label="Pages under Menu parent"' in parent_item
    # the phone's list: folded under it until its arrow is tapped - they
    # were all open, a long list
    phone = html.split('id="nav-mobile-menu"')[1]
    folded = phone[phone.index("<details>"):phone.index("</details>")]
    assert f'pin-submenu-{parent}-m' not in html and f'href="/{child}"' in folded
    assert f'<summary><a href="/{parent}">' in folded
    # 80% of a phone's width up to 360 px, long names wrapping - an opened
    # parent's sub-pages ran past a fixed width's edge (checked at 320-700 px)
    tag = html[html.rindex("<ul", 0, html.index('id="nav-mobile-menu"')):]
    tag = tag[:tag.index(">")]
    # rows a finger can hit on a touch screen come from the one touch-size
    # rule (input.css), as every menu's do - not a class of the header's own
    assert "menu-lg" not in tag
    assert "w-[min(80vw,22.5rem)]" in tag and "[&amp;_:is(a,summary)]:whitespace-normal" in tag
    # moved under More, folded the same way - they showed open there
    item = row[row.index('data-nav-parent'):]
    item = item[:item.index(f'id="pin-submenu-{parent}-d"')]
    assert '<details class="hidden [[data-nav-more-list]_&amp;]:block">' in item and f'href="/{child}"' in item
    # the list opens under the page's name, not under its arrow
    from soloblog.app import POPOVER_DROPDOWN_JS
    assert "trigger.closest('[data-nav-parent]') || trigger" in POPOVER_DROPDOWN_JS
    # and a mouse resting on it opens the list (NAV_HOVER_JS)
    from soloblog.app import NAV_HOVER_JS, SHARED_SCRIPTS
    assert NAV_HOVER_JS in SHARED_SCRIPTS and "(hover: hover) and (pointer: fine)" in NAV_HOVER_JS
    assert "item.closest('[data-nav-more-list]')" in NAV_HOVER_JS
    # Colours and the admin's gear open the same way (checked in a browser)
    from soloblog import settings, ui
    assert 'data-hover-menu' in str(ui.to_xml(ui.AdminMenu()))
    kept = settings.get("visitor_theme_switching")
    try:
        settings.set_many({"visitor_theme_switching": "1"})
        assert 'data-hover-menu' in str(ui.to_xml(ui.VisitorThemeSwitcher(settings.get_all())))
    finally:
        settings.set_many({"visitor_theme_switching": kept})


def test_header_menu_folds_instead_of_wrapping(client):
    html = client.get("/").text
    # one line, never a link broken over two; FIT_NAV_JS folds it when it won't fit
    assert "data-nav-menu" in html and "[&amp;_a]:whitespace-nowrap" in html
    assert "group-data-[nav-folded]/header:hidden!" in html and "group-data-[nav-folded]/header:inline-flex!" in html
    from soloblog.app import APP_JS
    assert "function fitNav()" in APP_JS


def test_environment_warns_only_about_real_problems(admin):
    import re
    html = admin.get("/admin/settings?tab=integrations").text

    def badge(name):
        row = html.split(f">{name}</span>")[1][:200]
        return re.search(r'class="badge ([\w-]+) badge-sm">([^<]+)<', row).groups()
    # defaults that are right for a real site aren't a warning
    assert badge("SITE_TITLE") == ("badge-ghost", "Default")
    assert f"Your title: {settings.get('site_title')}" in html
    # a site at localhost has no public address for its feeds and links
    assert badge("BASE_URL")[1] in ("Set", "Detected", "Not set", "From Settings")
    assert "Using default" not in html


def test_one_agent_prompt_for_everywhere(admin):
    import re
    from soloblog.routes.help_routes import DOCS_DIR
    text = Path(f"{DOCS_DIR}/DEPLOYMENT.md").read_text(encoding="utf-8")
    section = text.split("## Set it up with an AI agent")[1].split("\n## ")[0]
    prompts = re.findall(r"```text\n(.*?)```", section, re.S)
    # one prompt for every host, server and domain - nothing to keep in step
    assert len(prompts) == 1
    prompt = prompts[0]
    for part in ("Where it should run", "Use a custom domain", "Any other host", "Cloudflare", "SSH with a key",
                 "Windows, Mac or Linux", "SETUP_TOKEN", "don't press me"):
        assert part in prompt, part
    # every part of the guide it sends the agent to is a heading there
    named = re.findall(r'guide\'s\s+"([^"]+)"|follow\s+"([^"]+)"|\("([^"]+)"', prompt)
    names = {" ".join(n.split()) for group in named for n in group if n}
    headings = {line.lstrip("#").strip() for line in text.splitlines() if line.startswith("#")}
    assert names and names <= headings, names - headings
    # one click to copy in Help too
    assert "Set it up with an AI agent" in admin.get("/admin/help?tab=deployment").text


def test_searching_settings_and_help(admin, client):
    # the indexes are the admin's, made from the pages themselves
    assert client.get("/admin/settings/search-index").status_code in (302, 303)
    assert client.get("/admin/help/search-index").status_code in (302, 303)
    found = admin.get("/admin/settings/search-index").json()
    welcome = [e for e in found if e["title"] == "Welcome email"]
    assert welcome and welcome[0]["group"] == "Members" and welcome[0]["sub"] == "Members"
    assert "tab=members" in welcome[0]["href"] and "setting=Welcome%20email" in welcome[0]["href"]
    # a list's choices can be searched for, though they aren't shown
    assert any("Paid members" in e.get("words", "") for e in found if e["title"] == "Who can comment")
    sections = admin.get("/admin/help/search-index").json()
    backups = [e for e in sections if e["title"] == "How do I back up?"]
    assert backups and backups[0]["group"] == "Common questions" and backups[0]["href"].endswith("#how-do-i-back-up")
    # one box for both, the top bar's; a search in the address of Settings
    # or Help comes back in it (index_search.js)
    page = admin.get("/admin/settings?tab=url&q=address").text
    assert 'id="admin-search"' in page and "settings/search-index" not in page
    from soloblog import app as app_module
    assert "(settings|help)$/.test(location.pathname)) bar.value = asked" in app_module.INDEX_SEARCH_JS


def test_settings_search_knows_everyday_words(admin):
    found = admin.get("/admin/settings/search-index").json()
    hay = lambda e: " ".join([e["title"], e["sub"], e["text"], e.get("words", "")]).lower()  # noqa: E731
    assert any("theme" in hay(e) and e["group"] == "Style" for e in found)
    # the site's URL by the words people also use for it
    assert any(e["title"] == "Site URL" and "domain" in hay(e) and "address" in hay(e) for e in found)
    assert any("logo" in hay(e) and e["title"] == "Header icon" for e in found)


def test_every_admin_page_ends_with_the_version_and_help(admin, client):
    from soloblog import config
    for path in ("/admin/posts", "/admin/media", "/admin/comments", "/admin/settings?tab=url",
                 "/admin/help?tab=faq", "/admin/health", "/admin/new"):
        page = admin.get(path).text
        assert page.count(f"Soloblog {config.VERSION} · ") == 1, path
        assert "Report a problem" in page and "Support Soloblog" in page, path
    # not on the public site
    assert f"Soloblog {config.VERSION} · " not in client.get("/").text


def test_every_help_page_is_in_the_image():
    """The image leaves docs/ out except the pages Help shows - a new Help
    page has to be let back in, or the live site says it isn't there."""
    import os
    from soloblog.routes.help_routes import HELP_PAGES
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    allowed = {line[1:].strip() for line in Path(os.path.join(root, ".dockerignore")).read_text().splitlines() if line.startswith("!")}
    for name in HELP_PAGES.values():
        path = os.path.normpath(os.path.join("docs", name))
        assert path in allowed, f"{path} is a Help page but .dockerignore leaves it out of the image"


def test_every_page_has_a_description(client):
    from soloblog import settings
    before = {k: settings.get(k) for k in ("tagline", "members_enabled")}
    settings.set_many({"tagline": "Bread and bicycles", "members_enabled": "1"})
    try:
        for path in ("/join", "/signin"):
            assert '<meta name="description" content="Bread and bicycles">' in client.get(path).text, path
    finally:
        settings.set_many({k: v or "" for k, v in before.items()})


def test_csv_exports(admin):
    """Posts, stats and sources as spreadsheets - and a cell another site
    chose (a source) can't run as a formula."""
    import csv
    import io
    from soloblog.db import get_db
    slug = save_post(admin, title="In the export")
    get_db().execute("INSERT OR REPLACE INTO post_views_daily (slug, day, views) VALUES (?, date('now'), 7)", (slug,))
    get_db().execute("INSERT OR REPLACE INTO sources_daily (day, source, views) VALUES (date('now'), ?, 3)",
                     ('=HYPERLINK("https://evil.example","click")',))
    get_db().commit()
    rows = list(csv.reader(io.StringIO(admin.post("/admin/posts/bulk", data={
        "action": "export", "all_matching": "1"}).text)))
    assert rows[0][:2] == ["title", "address"] and any(r[0] == "In the export" and r[1].endswith(slug) for r in rows)
    views = admin.get("/admin/stats/export?range=30d").text
    assert "In the export" in views and ",7" in views
    sources = admin.get("/admin/stats/export?range=30d&kind=sources").text
    assert "'=HYPERLINK" in sources and "\n=HYPERLINK" not in sources and ",=HYPERLINK" not in sources
    # one way to export posts: tick them (or Select all), then Export
    assert "/admin/posts/export" not in admin.get("/admin/posts").text
    assert 'href="/admin/stats/export?range=30d"' in admin.get("/admin/stats").text


def test_blended_side_panels_include_the_contents(admin):
    """Blend side panels into the page reaches Help's contents too."""
    from soloblog import settings
    from soloblog.ui import SIDE_PLAIN
    before = settings.get("side_plain")
    try:
        settings.set_many({"side_plain": "1"})
        blended = "_.collapse]:bg-transparent"  # SIDE_PLAIN, as it reads in HTML (& escaped)
        assert blended in SIDE_PLAIN and blended in admin.get("/admin/help?tab=reference").text
        settings.set_many({"side_plain": "0"})
        assert blended not in admin.get("/admin/help?tab=reference").text
    finally:
        settings.set_many({"side_plain": before or "0"})


def test_the_readme_and_changelog_count_templates_and_sections_right():
    import os
    import re
    from soloblog import post_templates, sections
    root = os.path.dirname(os.path.dirname(__file__))
    for name in ("README.md", "CHANGELOG.md"):
        text = Path(os.path.join(root, name)).read_text(encoding="utf-8")
        assert {int(n) for n in re.findall(r"(\d+) templates", text)} == {len(post_templates.BUILT_IN)}, name
        assert {int(n) for n in re.findall(r"(\d+) kinds of\s+section", text)} == {len(sections.REGISTRY)}, name
        assert "page layouts" not in text, name


def test_help_search_puts_whats_new_last(admin):
    """The changelog matches most words; its results come after the guide's
    (ui.AdminSearch data-index-last, index_search.js)."""
    html = admin.get("/admin/help").text
    assert "data-index-last=\"Help: What&#x27;s new\"" in html or "data-index-last=\"Help: What's new\"" in html
    from soloblog import js
    script = js.read("index_search.js")
    assert "_LITTLE" in script and "indexLast" in script


def test_a_result_on_the_open_page_is_gone_to_not_loaded(admin):
    # a result that differs only by its #place loads nothing: the click
    # closes the results and opens the place as an arrival does
    from soloblog import js
    script = js.read("index_search.js")
    assert "function _arrive()" in script and script.count("_arrive();") == 2
    handler = script.split("function _arrive()")[1].split("var same = ")[1]
    assert "e.preventDefault()" in handler and "_indexSearch(box)" in handler and "replaceState" in handler
    assert "to.pathname !== location.pathname" in script


def test_help_search_finds_the_guides_smallest_headings(admin):
    # the settings reference's #### headings were part of their ###: a
    # search for one landed on "Security" (planned fix 29)
    sections = admin.get("/admin/help/search-index").json()
    two = [e for e in sections if e["title"] == "Two-factor authentication (2FA)" and e["group"] == "Reference"]
    assert two and two[0]["sub"] == "Security" and two[0]["href"].endswith("#two-factor-authentication-2fa")
    # its words are its own, not the section's above too
    security = [e for e in sections if e["title"] == "Security" and e["group"] == "Reference"]
    assert security and two[0]["text"][:40] not in security[0]["text"]
    # a heading that says nothing on its own is the section's above
    from soloblog.routes import help_routes
    assert {"more", "how it works", "settings"} <= help_routes._GENERIC
    assert not any(e["title"].lower() in help_routes._GENERIC for e in sections)


def test_a_search_for_a_pages_name_finds_it_once_on_top(admin):
    # Settings: each page has its own result - unless a panel on it has
    # the page's name (Newsletter), which is then that one result
    found = admin.get("/admin/settings/search-index").json()
    email = [e for e in found if e["title"] == "Email" and e["group"] == "Email"]
    assert len(email) == 1 and email[0]["href"] == "/admin/settings?tab=email" and not email[0]["sub"]
    assert len([e for e in found if e["title"] == "Comments" and e["group"] == "Comments and messages"
                and not e["sub"]]) == 1
    # and the search puts an exact name first, folding in what only
    # matched through it (checked in a browser: "email", "comments",
    # "security", "two-factor authentication")
    from soloblog import app as app_module
    js = app_module.INDEX_SEARCH_JS
    assert "e._title === _fold(q) ? 20 : whole(e) ? 10 : 0" in js
    assert "named[e.group + '|' + e.group]" in js


def test_a_search_result_is_marked_with_a_wash_that_fades():
    # a ring set off from it looked like a frame round a heading, and its
    # rounded corners stayed: a wash of the palette's primary, fading away
    from soloblog import app as app_module
    js = app_module.INDEX_SEARCH_JS
    assert "ring-offset-4" not in js and "bg-primary/15" in js and "duration-1000" in js
    assert "target.classList.remove.apply(target.classList, FADE)" in js


def test_phone_header_and_footer_are_sized_for_a_finger(client):
    # measured below the guidelines on a phone: a 50 px bar, 24 px icons,
    # 28 px footer icons touching, 13-16 px tall footer links. Now on a touch
    # screen: Material's 56 px bar and 48 px buttons (40 px under 360 px,
    # where four at 48 left the site's name a letter), 48 px footer icons
    # 8 px apart (web.dev), 44 px footer links at 14 px (Apple) - checked in
    # a browser at 320, 360, 375 and 1440 px, the name whole at each
    from soloblog import settings, ui
    assert ui.TOUCH_BAR == "pointer-coarse:min-h-14 pointer-coarse:py-1"
    assert ui.TOUCH_BTN == "pointer-coarse:btn-square"  # 44 px from the touch-size rule
    html = client.get("/").text
    assert html.count(ui.TOUCH_BTN) >= 2 and ui.TOUCH_BAR in html
    kept = {k: settings.get(k) for k in ("footer_enabled", "footer_show_socials", "social_github", "footer_show_powered_by")}
    try:
        settings.set_many({"footer_enabled": "1", "footer_show_socials": "1", "social_github": "https://github.com/x",
                           "footer_show_powered_by": "1"})
        footer = client.get("/").text.split("<footer")[1]
        assert "btn btn-ghost btn-square btn-sm" in footer and "pointer-coarse:gap-2" in footer
        assert ui.TOUCH_LINK in footer
    finally:
        settings.set_many(kept)


def test_a_tall_header_menu_scrolls_in_one_column(client):
    # on a phone, opened sub-pages made the menu taller than the screen: it
    # fanned out into a second column, cut off (.menu wraps), and opening a
    # page's sub-pages after it opened never re-measured it (checked in a
    # browser at 375x667 and 320x568: one column, scrolling to its foot)
    from soloblog import ui
    from soloblog.app import POPOVER_DROPDOWN_JS
    assert "flex-nowrap overflow-y-auto" in ui.MENU_SCROLLS
    html = client.get("/").text
    phone = html[html.rindex("<ul", 0, html.index('id="nav-mobile-menu"')):]
    assert ui.MENU_SCROLLS in phone[:phone.index(">")]
    assert "e.target.matches('details') && e.target.closest(':popover-open')" in POPOVER_DROPDOWN_JS


def test_one_touch_size_rule_for_every_control(admin):
    # measured on a phone, most controls were under 44 px - in pages,
    # panels, dialogs and menus - and fields' 14 px text made an iPhone
    # zoom in. One rule on daisyUI's own size variables (touch-size), and
    # the phone check holds every page to it on a touch screen
    import os
    import re
    css = Path(os.path.join(os.path.dirname(__file__), "..", "static", "css", "input.css")).read_text()
    rule = css[css.index("[custom-css: touch-size]"):]
    rule = rule[rule.index("@media (pointer: coarse)"):]
    for part in (":root .btn:not(.btn-lg, .btn-xl, .sr-only) { --size: 2.75rem; min-width: 2.75rem; }",
                 "--in-size-mul: 11; --sl-size-mul: 11;", "--font-size-min: 1rem;", "--tab-height: 2.75rem;",
                 "min-height: 2.75rem; align-content: center; font-size: 1rem;", "--size: 1.5rem;",
                 ":root :is(a, button).badge:not([data-tap-area]) { --size: 2rem;", "summary:is(.collapse-title, .link)",
                 ":root :is(li, td, p) > a:only-child:not(.menu *, .btn, .block)", "[data-row-menu] .btn"):
        assert part in rule, part
    dev = Path(os.path.join(os.path.dirname(__file__), "..", "docs", "DEVELOPMENT.md")).read_text()
    assert "| `touch-size` |" in dev
    check = Path(os.path.join(os.path.dirname(__file__), "..", "tools", "phone_check.py")).read_text()
    assert "big = touch ? 44 : 24" in check
    # on a phone, pagination is Prev, "2 / 5" and Next - every number ran off 320 px
    from soloblog import ui
    html = str(ui.to_xml(ui.Pagination(2, 5, "/admin/posts")))
    assert re.search(r'btn-active[^>]*>2<span class="sm:hidden whitespace-pre"> / 5</span>', html)
    assert 'class="join-item btn btn-sm max-sm:hidden">3</a>' in html
    # a page's buttons keep their size, its title wraps
    page = admin.get("/admin/posts").text
    assert 'flex items-center gap-3 shrink-0' in page


def test_a_post_in_any_list_opens_from_anywhere_on_it(admin, client):
    # only the title opened it - on a phone a 20 px line to hit; the search
    # page's rows already opened from anywhere (ROW_LINKS_JS)
    slug = save_post(admin, title="Whole row zebrafinch")
    for url in ("/", "/search?q=zebrafinch"):
        assert 'data-click-rows' in client.get(url).text and slug in client.get(url).text, url


def test_help_links_lead_somewhere(admin):
    """Every link from one Help page to another lands on a heading that's
    there - a renamed heading fails here instead of quietly breaking a link."""
    import re
    from soloblog.routes.help_routes import HELP_PAGES
    pages = {tab: admin.get(f"/admin/help?tab={tab}").text for tab in HELP_PAGES}
    broken = []
    for tab, html in pages.items():
        body = html.split('id="help-body"')[1]
        for to, anchor in re.findall(r'href="(?:/admin/help\?tab=([\w-]+))?#([^"]+)"', body):
            if f'id="{anchor}"' not in pages[to or tab]:
                broken.append(f"{tab} -> {to or tab}#{anchor}")
    assert not broken, broken


def test_nothing_links_to_the_old_single_guide():
    """The guide was one page, USER_GUIDE.md (Help's ?tab=guide), until it
    was split by task before the first public release - every link was moved, none redirected."""
    import glob
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    files = [f for pattern in ("*.md", "docs/**/*.md", "soloblog/**/*.py", "soloblog/js/*.js")
             for f in glob.glob(os.path.join(root, pattern), recursive=True)]
    assert len(files) > 50
    found = [os.path.relpath(f, root) for f in files
             if "USER_GUIDE.md" in (text := Path(f).read_text(encoding="utf-8")) or "tab=guide" in text]
    assert not found, found


def test_the_apps_help_links_lead_somewhere(admin):
    """Site health, Settings and the rest link into Help by section - each
    lands on a heading that's there, so a renamed one fails here."""
    import glob
    import os
    import re
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    links = set()
    for f in glob.glob(os.path.join(root, "soloblog", "**", "*.py"), recursive=True):
        links |= set(re.findall(r"/admin/help\?tab=([\w-]+)#([\w-]+)", Path(f).read_text(encoding="utf-8")))
    assert len(links) > 5
    pages = {}
    broken = [f"{tab}#{anchor}" for tab, anchor in sorted(links)
              if f'id="{anchor}"' not in pages.setdefault(tab, admin.get(f"/admin/help?tab={tab}").text)]
    assert not broken, broken


def test_no_line_in_help_turns_into_a_quote_by_accident():
    """A menu path wrapped so a line starts with "> " (**Settings
    > Profile**) became a quote, with the ** showing. A real quote has a
    blank line before it."""
    import glob
    files = glob.glob("docs/guide/*.md") + ["docs/FAQ.md", "docs/DEPLOYMENT.md", "docs/API.md", "docs/SPONSORS.md"]
    found = []
    for name in files:
        lines = Path(name).read_text(encoding="utf-8").split("\n")
        in_code = False
        for i, line in enumerate(lines):
            if line.lstrip().startswith("```"):
                in_code = not in_code
            prev = lines[i - 1].strip() if i else ""
            if not in_code and line.lstrip().startswith("> ") and prev and not prev.startswith(">"):
                found.append(f"{name}:{i + 1}")
    assert not found, found


def test_every_settings_page_links_to_its_help(admin):
    # the reference has a ## for each settings page - renamed on one side
    # only, this fails rather than a link going nowhere
    from soloblog.routes.admin_settings import TABS, settings_help
    reference = admin.get("/admin/help?tab=reference").text
    for tab, _ in TABS:
        href = settings_help(tab)
        assert f'id="{href.split("#")[1]}"' in reference, tab
        assert f'href="{href}"' in admin.get(f"/admin/settings?tab={tab}").text, tab


def test_help_lists_every_address_a_page_cant_have():
    # Reference > URLs Soloblog uses: the same names as the app's own
    # routes (posts.RESERVED_PATHS), so a new one can't go missing
    import os
    import re
    from soloblog import posts
    ref = Path(os.path.join(os.path.dirname(__file__), "..", "docs", "guide", "reference.md")).read_text()
    part = ref.split("### URLs Soloblog uses")[1].split("\n## ")[0].split("\n- ", 1)[1]
    assert set(re.findall(r"`([^`]+)`", part)) == posts.RESERVED_PATHS


def test_help_lists_every_built_in_template():
    import os
    from soloblog import post_templates
    guide = Path(os.path.join(os.path.dirname(__file__), "..", "docs", "guide", "sections-templates.md")).read_text()
    part = guide.split("\n## Templates\n")[1].split("\n## ")[0]
    for name, *_ in post_templates.BUILT_IN.values():
        assert f"| {name} |" in part, name


def _no_code(text):
    """Markdown with its fenced blocks blanked - a fence closes only with as
    many backticks (or tildes) as opened it - lines kept for numbering."""
    import re
    out, fence = [], None
    for line in text.split("\n"):
        m = re.match(r"^\s*(`{3,}|~{3,})", line)
        if fence:
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) \
                    and not line.strip()[len(m.group(1)):].strip():
                fence = None
            out.append("")
        elif m:
            fence = m.group(1)
            out.append("")
        else:
            out.append(line)
    return "\n".join(out)


def test_every_link_in_the_repositorys_text_files_lands():
    # every link between the repository's Markdown files goes to a file
    # that's there, and to a heading that's there - by GitHub's ids
    # (a heading with " / " in it is #a--b on GitHub; Help reads those
    # as its own, help_routes._help_links)
    import os
    import re
    import subprocess
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    files = [f for f in subprocess.run(["git", "ls-files", "*.md"], cwd=root, capture_output=True,
                                       text=True).stdout.split() if not f.startswith("static/vendor")]

    def slug(heading):
        heading = re.sub(r"`|\*\*|\*|\[|\]\([^)]*\)", "", heading).strip().lower()
        return re.sub(r"\s", "-", re.sub(r"[^\w\s-]", "", heading))
    ids = {}
    for f in files:
        seen, found = {}, set()
        for m in re.finditer(r"^#{1,6}\s+(.+?)\s*#*\s*$", _no_code(Path(os.path.join(root, f)).read_text(encoding="utf-8")),
                             re.M):
            s = slug(m.group(1))
            found.add(s if s not in seen else f"{s}-{seen[s]}")
            seen[s] = seen.get(s, 0) + 1
        ids[f] = found
    bad = []
    for f in files:
        text = re.sub(r"`[^`\n]*`", "", _no_code(Path(os.path.join(root, f)).read_text(encoding="utf-8")))
        for m in re.finditer(r"\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)", text):
            url = m.group(1)
            if url.startswith(("http://", "https://", "mailto:", "/")) or url == "...":
                continue
            path, _, anchor = url.partition("#")
            target = os.path.normpath(os.path.join(os.path.dirname(f), path)) if path else f
            if path and not os.path.exists(os.path.join(root, target)):
                bad.append(f"{f}: {url} - no such file")
            elif anchor and target in ids and anchor not in ids[target]:
                bad.append(f"{f}: {url} - no such heading")
    assert not bad, "\n".join(bad)


def test_help_reads_a_github_style_heading_link_as_its_own():
    # GitHub keeps both dashes of a heading like "Wiki / notes", Help one
    from soloblog.routes.help_routes import _help_links
    html = _help_links('<a href="sections-templates.md#wiki--notes">x</a> <a href="#wiki--notes">y</a>', "pages")
    assert 'href="/admin/help?tab=sections-templates#wiki-notes"' in html and 'href="#wiki-notes"' in html
    assert "wiki--notes" not in html


def test_the_guide_has_no_page_layouts():
    """A page's frame and kind are Post settings, templates and sections - no
    page layout is left in the docs (the blog's and the footer's are other
    things)."""
    import glob
    import re
    files = glob.glob("docs/guide/*.md") + ["docs/FAQ.md", "README.md", "CHANGELOG.md"]
    found = []
    for name in files:
        for i, line in enumerate(Path(name).read_text(encoding="utf-8").split("\n"), 1):
            if re.search(r"page layout|layouts-sections|Layout >|Choose a layout|layout:", line, re.I):
                found.append(f"{name}:{i}")
    assert not found, found


def test_the_admin_says_site_not_blog():
    # a site may be a portfolio or a homepage page, not a blog: the admin's
    # own words say "your site" (a design preset's sample words may still
    # mention a blog that's part of a site)
    import pathlib
    import re
    found = [f"{p}:{n}" for p in pathlib.Path("soloblog").rglob("*.py") if p.name not in ("demo.py", "presets.py")
             for n, line in enumerate(p.read_text(encoding="utf-8").split("\n"), 1)
             if re.search(r"\byour blog\b|View your blog", line, re.I)]
    assert not found, found


def test_every_page_with_a_referral_link_says_so_under_its_title():
    """A page with a link that earns the project something says so under
    its title, in the words the programmes ask for - one notice that
    covers every link on the page, so none needs its own label
    (DECISIONS.md > Community; DEPLOYMENT.md > About the links in this
    guide)."""
    import re
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    found = 0
    for path in [root / "README.md", *sorted((root / "docs").rglob("*.md"))]:
        text = path.read_text(encoding="utf-8")
        if not re.search(r"\]\((https?://[^)\s]*(?:referral|[?&]ref=|[?&]aff|affiliate|awin)[^)\s]*)\)", text, re.I):
            continue
        found += 1
        top = re.sub(r"\s+", " ", text.split("\n## ", 1)[0])
        assert "We earn commissions when you shop through the links below." in top, path.name
        # a label on some links would suggest the others earn nothing
        assert "(referral link)" not in text, path.name
    assert found, "the hosting guide, at least"


def test_docs_read_as_the_project_not_a_log():
    """No dated notes in the public docs (CLAUDE.md > Written as the
    project, not a log) - a date only in the changelog, or inside code as
    an example."""
    import re
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    files = [root / name for name in ("README.md", "CLAUDE.md", "CONTRIBUTING.md", "SECURITY.md", "SUPPORT.md", "ACCESSIBILITY.md")]
    files += sorted((root / "docs").rglob("*.md")) + sorted((root / ".github").rglob("*.md"))
    found = []
    for path in files:
        text = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.S)
        text = re.sub(r"`[^`\n]*`", "", text)
        for m in re.finditer(r"\b20\d\d-[01]\d(?:-[0-3]\d)?\b|\bdone \(", text):
            found.append(f"{path.relative_to(root)}: {text[max(0, m.start() - 40):m.end() + 20]!r}")
    assert not found, found


def test_a_page_nests_under_one_of_the_sites_own_pages(admin, client):
    # Home, Blog... can have pages under them, in the header and the footer, as a page can
    from soloblog import posts, settings
    before = {k: settings.get(k) for k in ("home_page", "foot_archive_on", "footer_enabled", "footer_show_pages",
                                           "footer_layout")}
    try:
        child = save_post(admin, title="Under home", pin_location="header", pinned="1")
        assert posts.set_parent(child, "site:home")
        html = client.get("/").text
        submenu = html.split('id="pin-submenu-site-home-d"')[1].split("</ul>")[0]
        assert f'href="/{child}"' in submenu
        assert 'aria-label="Pages under Home"' in html
        # its breadcrumbs: Home is the first one already
        settings.set_many({"home_page": ""})
        # the Pinned tab shows it under Home, and Post settings offer the site's pages
        pinned = admin.get("/admin/posts?status=pinned").text
        assert "Make top-level" in pinned
        assert 'value="site:home"' in admin.get(f"/admin/edit/{child}").text
        # the footer: under Archive, a column of its own in Columns
        settings.set_many({"foot_archive_on": "1", "footer_enabled": "1", "footer_show_pages": "1",
                           "footer_layout": "columns"})
        foot = save_post(admin, title="Under archive", pin_location="footer", pinned="1")
        assert posts.set_parent(foot, "site:archive")
        page = client.get("/").text
        footer = page[page.rindex("<footer"):]
        assert f'href="/{foot}"' in footer and 'font-semibold' in footer.split('href="/archive"')[0][-200:] + \
            footer.split('href="/archive"')[1][:200]
        crumbs = client.get(f"/{foot}").text
        assert 'href="/archive"' in crumbs
        # a site page that isn't in that menu, junk, and a page with pages under it can't be parents
        assert not posts.set_parent(foot, "site:contact")
        assert not posts.set_parent(foot, "site:nothing")
        assert not posts.set_parent(foot, "site:")
        # one whose site page leaves the menu is a top-level page meanwhile, never lost
        settings.set_many({"foot_archive_on": ""})
        assert f'href="/{foot}"' in client.get("/").text
    finally:
        settings.set_many(before)
        # out of the menus, so the tests after see the menu they expect
        for slug in [s for s in ("under-home", "under-archive") if posts.get_post(s)]:
            posts.delete_post(slug)
