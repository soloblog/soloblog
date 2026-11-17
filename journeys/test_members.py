"""Members: the owner opens a members-only post, a reader joins by email
and reads it."""
import re

from conftest import Window, outbox, save, write
from test_email import set_up_email


def test_join_by_email_and_read_a_members_post(owner, browser, site):
    set_up_email(owner)
    # Settings > Members: on
    owner.go("/admin/settings?tab=members")
    # a switch saves as it changes
    owner.page.locator("input[name=members_enabled]").check(force=True)
    owner.page.wait_for_timeout(1500)
    owner.go("/admin/settings?tab=members")
    assert owner.page.locator("input[name=members_enabled]").is_checked()
    # a post for members
    owner.go("/admin/new")
    write(owner, "Members only bread", "The start, for everyone.\n\n<!-- members only from here -->\n\nThe secret crumb.")
    owner.page.evaluate("() => togglePostSettings(true)")
    owner.page.locator("#post-settings-panel input[name=published]").check()
    owner.page.evaluate("() => { const s = document.querySelector('select[name=visibility]'); s.value = 'members';"
                        " s.dispatchEvent(new Event('change', {bubbles: true})); }")
    save(owner)
    post = "/post/" + owner.page.url.rstrip("/").rsplit("/", 1)[-1]
    # a reader sees the start, and is asked to join
    reader = Window(browser, site["base"])
    reader.go(post)
    assert "The start, for everyone." in reader.page.content()
    assert "The secret crumb." not in reader.page.content()
    reader.go("/join")
    reader.page.fill("input[name=email]", "reader@example.com")
    before = len(outbox(site))
    reader.page.get_by_role("button", name="Join").click()
    reader.page.wait_for_load_state("networkidle")
    sent = [m for m in outbox(site)[before:] if m[0] == "reader@example.com"]
    assert sent, "no sign-in email"
    link = re.search(r"https?://\S+", sent[-1][2]).group(0)
    reader.go(link.replace(site["base"], ""))
    # follow a confirm step if there is one
    confirm = reader.page.locator("main form button[type=submit]")
    if confirm.count() and "/signin" in reader.page.url:
        confirm.first.click()
        reader.page.wait_for_load_state("networkidle")
    reader.go(post)
    assert "The secret crumb." in reader.page.content()
    reader.close()
