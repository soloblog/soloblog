"""A reader's comment: written, confirmed from their email, approved by
the owner, and there for everyone."""
import re

from conftest import Window, outbox, publish
from test_email import set_up_email


def test_comment_confirm_approve_and_read(owner, browser, site):
    set_up_email(owner)
    post = publish(owner, "Talk to me", "Tell me what you think.")
    # a reader comments
    reader = Window(browser, site["base"])
    reader.go(post)
    reader.page.fill("input[name=author_name]", "Ann")
    reader.page.fill("input[name=email]", "ann@example.com")
    reader.page.fill("textarea[name=body]", "Lovely post, thank you.")
    before = len(outbox(site))
    reader.page.locator("form:has(textarea[name=body]) button[type=submit]").click()
    reader.page.wait_for_timeout(1000)
    # it asks them to confirm, and the email to do it arrives
    sent = [m for m in outbox(site)[before:] if m[0] == "ann@example.com"]
    assert sent, "no confirmation email"
    link = re.search(r"https?://\S+/comment/confirm/\S+", sent[-1][2]).group(0)
    reader.go(link.replace(site["base"], ""))
    # not public until the owner approves it
    reader.go(post)
    assert "Lovely post, thank you." not in reader.page.content()
    owner.go("/admin/comments")
    row = owner.page.locator("li, .list-row", has_text="Lovely post, thank you.").first
    row.locator("[aria-label=Approve]").first.click()
    owner.page.wait_for_load_state("networkidle")
    reader.go(post)
    assert "Lovely post, thank you." in reader.page.content() and "Ann" in reader.page.content()
    reader.close()
