"""A new owner's first minutes: the setup page, then their own site."""
from conftest import PASSWORD, Window, sign_in


def test_setting_up_and_signing_in(browser, site, set_up):
    w = Window(browser, site["base"])
    # the site is theirs now: setup is closed, the login page asks
    w.go("/setup")
    assert "/setup" not in w.page.url or "Create admin account" not in w.page.content()
    sign_in(w)
    # signed in: the admin opens, not the login page
    w.go("/admin/posts")
    assert "/admin/posts" in w.page.url and "Posts and pages" in w.page.content()
    # a wrong password is said plainly, and doesn't sign in
    other = Window(browser, site["base"])
    other.go("/login")
    other.page.fill("input[name=password]", PASSWORD + "x")
    other.page.get_by_role("button", name="Log in").click()
    other.page.wait_for_load_state("networkidle")
    assert "Wrong password" in other.page.content() and "/admin" not in other.page.url
    other.close()
    # the site itself, for anyone
    w.go("/")
    assert w.page.locator("header").count() == 1
    w.close()


def test_the_setup_screens_then_getting_started(owner):
    # the screens after setup: your site, about you, your look - then what's next
    owner.go("/admin/welcome")
    assert "Your site" in owner.page.content()
    owner.page.get_by_role("button", name="Continue").click()
    owner.page.wait_for_load_state("networkidle")
    assert "step=you" in owner.page.url
    # no Skip: Continue on a screen left as it is changes nothing
    assert owner.page.get_by_role("button", name="Skip", exact=True).count() == 0
    owner.page.fill('main input[name="author_name"]', "Mira Castell")
    owner.page.get_by_role("button", name="Continue").click()
    owner.page.wait_for_load_state("networkidle")
    assert "step=look" in owner.page.url
    assert "Icon or logo" in owner.page.content()
    owner.page.get_by_role("button", name="Continue").click()
    owner.page.wait_for_load_state("networkidle")
    assert "step=style" in owner.page.url and "Writer's notebook" in owner.page.content()
    owner.page.get_by_role("button", name="Continue").click()
    owner.page.wait_for_load_state("networkidle")
    assert "step=done" in owner.page.url
    # what's next: six jobs, email first, each once
    done = owner.page.content()
    for job in ("Set up email", "Protect your login", "Plan your backups", "Describe your site",
                "Use a custom domain", "Write your first post"):
        assert job in done, job
    assert "Save a recovery key" not in done
    # each job is done on its own settings page: email on Settings > Email,
    # not on a screen of the setup
    owner.page.get_by_role("link", name="Set up email").first.click()
    owner.page.wait_for_load_state("networkidle")
    assert "/admin/settings?tab=email" in owner.page.url and "Step 1 of" not in owner.page.content()
    # and the list is one press away in the menu from there
    owner.page.locator('[data-open-dialog="getting-started"]').first.click()
    box = owner.page.locator("dialog#getting-started")
    box.wait_for(state="visible")
    # the setup was finished, so the list doesn't offer it
    assert "Finish setting up" not in box.inner_text()
    box.get_by_role("link", name="Describe your site").first.click()
    owner.page.wait_for_load_state("networkidle")
    assert "tab=url" in owner.page.url and owner.page.locator('[name="meta_description"]').is_visible()
    # the setup runs again from Settings > Name and homepage
    owner.go("/admin/settings?tab=name&panel=name-identity")
    owner.page.get_by_role("link", name="Run setup again").click()
    owner.page.wait_for_load_state("networkidle")
    assert owner.page.url.endswith("/admin/welcome") and "Your site" in owner.page.content()
