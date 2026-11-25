"""What an action did shows beside it, on the same line as its button -
on a wide screen and a phone - not at the far side of the row or the top
of the page."""
import re

# where the status's words are from its button: beside it on its line,
# or - too long for that, on a phone - on their own line just above it,
# ending where the button ends
PLACE = """([status, button]) => {
    const s = document.querySelector(status), b = document.querySelector(button);
    const r = document.createRange(); r.selectNodeContents(s);
    const t = r.getBoundingClientRect(), q = b.getBoundingClientRect();
    if (!t.width) return {shown: false};
    return {shown: true, sameLine: !(q.bottom < t.top || q.top > t.bottom),
            gap: q.left - t.right, above: q.top - t.bottom, ends: Math.abs(q.right - t.right)};
}"""


def beside(w, status, button):
    at = w.page.evaluate(PLACE, [status, button])
    assert at["shown"], status
    if at["sameLine"]:
        assert 0 <= at["gap"] <= 16, (status, at)
    else:
        assert 0 <= at["above"] <= 16 and at["ends"] <= 2, (status, at)


def test_unsaved_and_discarded_sit_beside_save(owner):
    w = owner
    w.go("/admin/settings?tab=name")
    w.page.locator("input[name=tagline]").press_sequentially(" and more")
    w.page.get_by_text("Unsaved changes").wait_for()
    beside(w, "#save-status", "#save-status + div")  # Discard and Save
    w.page.get_by_role("button", name="Discard").click()
    w.page.get_by_text("Discarded").wait_for()


def _log_out_others(w):
    w.go("/admin/settings?tab=security")
    w.page.get_by_role("button", name="Log out other devices").click()
    w.page.locator("dialog[open]").get_by_role("button", name=re.compile("Log out|Yes")).click()
    w.page.get_by_text("Logged out everywhere else").wait_for()
    beside(w, "#sessions-status", "form[action='/admin/sessions/end-others'] button")


def test_an_action_says_what_it_did_beside_its_button(owner):
    _log_out_others(owner)


def test_and_on_a_phone(owner_phone):
    _log_out_others(owner_phone)


def _wrong_password_for_a_recovery_key(w):
    w.go("/admin/settings?tab=security")
    form = w.page.locator("form:has(#recovery-key-status)")
    form.locator("input[name=password]").fill("not the password")
    form.locator("button[type=submit]").click()
    w.page.locator("#recovery-key-status.text-error").wait_for()
    beside(w, "#recovery-key-status", "#recovery-key-status + div")


def test_a_mistake_shows_beside_the_button_it_stopped(owner):
    _wrong_password_for_a_recovery_key(owner)


def test_a_mistake_beside_its_button_on_a_phone(owner_phone):
    _wrong_password_for_a_recovery_key(owner_phone)
