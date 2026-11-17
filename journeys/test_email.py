"""Email: the owner sets it up, sends themselves a test, and it arrives -
and every path that leans on it: setup's own email step, a forgotten
password, the newsletter and the contact form."""
import re

from conftest import PASSWORD, Window, outbox, publish


def choose(w, name, value):
    """A select, as a person picks from it (SELECT_JS draws its own)."""
    w.page.evaluate("([n, v]) => { const s = document.querySelector(`select[name=${n}]`); s.value = v;"
                    " s.dispatchEvent(new Event('change', {bubbles: true})); }", [name, value])


def link_in(message, base):
    return re.search(r"https?://\S+", message[2]).group(0).replace(base, "")


def open_sending(w):
    """Sending email is set up once: a row whose Edit opens it."""
    panel = w.page.locator("details[data-panel=email-sending]")
    if panel.get_attribute("open") is None:
        panel.locator("summary").click()


def set_up_email(w, address="owner@example.com"):
    """Settings > Email, as the owner fills it in: their own address, and
    an email account to send from (the journey's outbox catches what goes)."""
    w.go("/admin/settings?tab=email")
    w.page.fill("input[name=admin_email]", address)
    w.page.fill("input[name=admin_email_confirm]", address)
    open_sending(w)
    w.page.locator("input[name=email_provider][value=smtp]").check(force=True)
    choose(w, "smtp_provider", "")
    w.page.fill("input[name=smtp_host]", "smtp.example.com")
    w.page.fill("input[name=smtp_from]", "blog@example.com")
    # Save shows once something's changed - already set up, there's nothing to save
    save = w.page.locator("form[hx-post='/admin/settings/email'] button[type=submit]:visible")
    if save.count():
        save.last.click()
        w.page.wait_for_timeout(800)


def test_set_up_email_and_send_a_test(owner, site):
    set_up_email(owner)
    owner.go("/admin/settings?tab=email")
    # what was saved is what shows
    assert owner.page.input_value("input[name=smtp_host]") == "smtp.example.com"
    before = len(outbox(site))
    owner.page.get_by_role("button", name="Send a test email").click()
    owner.page.wait_for_timeout(1000)
    assert "Sent" in owner.page.locator("#email-test-status").inner_text()
    sent = outbox(site)[before:]
    assert sent and sent[-1][0] == "owner@example.com"


def test_a_provider_from_the_list_and_a_test_without_saving(owner, site):
    set_up_email(owner)
    owner.go("/admin/settings?tab=email")
    open_sending(owner)
    choose(owner, "smtp_provider", "gmail")
    # the server is the provider's: not asked for, and the app password is explained
    assert not owner.page.locator("input[name=smtp_host]").is_visible()
    assert "app password" in owner.page.locator("details[data-panel=email-sending]").inner_text()
    choose(owner, "smtp_provider", "outlook")
    assert not owner.page.locator("input[name=smtp_from]").is_visible()
    choose(owner, "smtp_provider", "gmail")
    owner.page.fill("input[name=smtp_from]", "me@gmail.example")
    # no Save: the test saves what's on screen, then sends
    before = len(outbox(site))
    owner.page.get_by_role("button", name="Send a test email").click()
    owner.page.wait_for_timeout(1000)
    assert "Sent" in owner.page.locator("#email-test-status").inner_text()
    assert len(outbox(site)) == before + 1
    owner.go("/admin/settings?tab=email")
    assert owner.page.input_value("select[name=smtp_provider]") == "gmail"
    assert owner.page.input_value("input[name=smtp_from]") == "me@gmail.example"
    set_up_email(owner)


def test_forgot_password_by_the_emailed_link(owner, browser, site):
    set_up_email(owner)
    w = Window(browser, site["base"])
    try:
        w.go("/forgot-password")
        before = len(outbox(site))
        w.page.get_by_role("button", name="Email me a reset link").click()
        w.page.wait_for_load_state("networkidle")
        sent = outbox(site)[before:]
        assert sent and sent[-1][0] == "owner@example.com", "no reset email"
        w.go(link_in(sent[-1], site["base"]))
        w.page.fill("input[name=password]", PASSWORD)
        w.page.fill("input[name=confirm]", PASSWORD)
        w.page.get_by_role("button", name="Save and log in").click()
        w.page.wait_for_load_state("networkidle")
        assert "/admin" in w.page.url, w.page.url
        # the link is used up
        w.go(link_in(sent[-1], site["base"]))
        assert w.page.locator("input[name=password]").count() == 0
    finally:
        w.close()


def test_subscribe_confirm_and_get_the_next_post(owner, browser, site):
    set_up_email(owner)
    owner.go("/admin/settings?tab=newsletter")
    owner.page.locator("input[name=newsletter_mode][value=builtin]").check(force=True)
    owner.page.locator("form button[type=submit]:visible").last.click()
    owner.page.wait_for_timeout(800)
    reader = Window(browser, site["base"])
    try:
        reader.go("/newsletter")
        reader.page.fill("input[name=email]", "subscriber@example.com")
        before = len(outbox(site))
        reader.page.get_by_role("button", name="Subscribe").first.click()
        reader.page.wait_for_load_state("networkidle")
        confirm = [m for m in outbox(site)[before:] if m[0] == "subscriber@example.com"]
        assert confirm, "no confirmation email"
        reader.go(link_in(confirm[-1], site["base"]))
        # a new post goes to them, once
        before = len(outbox(site))
        publish(owner, "Sourdough for subscribers", "A loaf, emailed.")
        for _ in range(20):
            got = [m for m in outbox(site)[before:] if m[0] == "subscriber@example.com"]
            if got:
                break
            owner.page.wait_for_timeout(500)
        assert len(got) == 1 and "Sourdough for subscribers" in got[0][1]
        owner.page.wait_for_timeout(1500)
        assert len([m for m in outbox(site)[before:] if m[0] == "subscriber@example.com"]) == 1
    finally:
        reader.close()


def test_a_message_from_the_contact_form(owner, browser, site):
    set_up_email(owner)
    owner.go("/admin/settings?tab=messages")
    owner.page.locator("input[name=contact_enabled]").check(force=True)
    owner.page.fill("input[name=contact_email]", "owner@example.com")
    owner.page.locator("form button[type=submit]:visible").last.click()
    owner.page.wait_for_timeout(800)
    visitor = Window(browser, site["base"])
    try:
        visitor.go("/contact")
        visitor.page.fill("input[name=name]", "Ada")
        visitor.page.fill("input[name=email]", "ada@example.com")
        visitor.page.fill("textarea[name=body]", "Your sourdough worked.")
        before = len(outbox(site))
        visitor.page.get_by_role("button", name="Send").click()
        visitor.page.wait_for_load_state("networkidle")
        visitor.page.wait_for_timeout(800)
        assert [m for m in outbox(site)[before:] if m[0] == "owner@example.com"], "not emailed to the owner"
    finally:
        visitor.close()
    # and in the admin, where the menu now lists it
    owner.go("/admin/messages")
    assert "Your sourdough worked." in owner.page.content()
    assert owner.page.locator("a[href='/admin/messages']").count()


def test_your_email_speaks_in_the_save_bar(owner, site):
    """Unsaved changes, and an address typed twice that doesn't match,
    show beside Save and Discard - not beside Send a test email, though
    that comes first in the form."""
    set_up_email(owner)
    owner.go("/admin/settings?tab=email")
    owner.page.fill("input[name=admin_email]", "new@example.com")
    bar = owner.page.locator("#save-status")
    assert bar.inner_text() == "Unsaved changes"
    assert "Unsaved" not in owner.page.locator("#email-test-status").inner_text()
    owner.page.fill("input[name=admin_email_confirm]", "new@example.co")
    owner.page.locator("form[hx-post='/admin/settings/email'] button[type=submit]:visible").last.click()
    owner.page.wait_for_timeout(300)
    assert "don't match" in bar.inner_text()
    owner.page.get_by_role("button", name="Discard").last.click()
