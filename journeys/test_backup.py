"""A backup: downloaded, and a post's earlier words brought back from it."""
import os

from conftest import Window, publish, save


def test_download_a_backup_and_restore_from_it(owner, browser, site, tmp_path):
    post = publish(owner, "Kept safe", "The words in the backup.")
    # Settings > Backup > Download
    owner.go("/admin/settings?tab=backup")
    with owner.page.expect_download() as got:
        owner.page.locator("form[action='/admin/backup/download'] button[type=submit]").click()
    path = os.path.join(tmp_path, "backup.zip")
    got.value.save_as(path)
    assert os.path.getsize(path) > 1000
    # the post changed since
    owner.go("/admin/edit/" + post.rsplit("/", 1)[-1])
    owner.page.locator(".CodeMirror").first.click()
    owner.page.keyboard.press("Control+A")
    owner.page.keyboard.type("Words written after the backup.")
    save(owner)
    reader = Window(browser, site["base"])
    reader.go(post)
    assert "Words written after the backup." in reader.page.content()
    # Restore: upload it, see what's in it, choose, confirm
    owner.go("/admin/settings?tab=backup")
    with owner.page.expect_navigation():
        owner.page.set_input_files("input[name=backup_zip]", path)
    owner.page.wait_for_load_state("networkidle")
    restore = owner.page.locator("form[action='/admin/backup/restore-confirm']")
    assert restore.count() == 1, owner.page.locator("main").inner_text()[:600]
    restore.get_by_role("button", name="Restore").click()
    owner.page.locator("dialog[open]").get_by_role("button", name="Restore").click()
    owner.page.wait_for_load_state("networkidle")
    owner.page.wait_for_timeout(1000)
    reader.go(post)
    assert "The words in the backup." in reader.page.content()
    reader.close()
