"""A backup: downloaded, and a post's earlier words brought back from it."""
import os

import shutil

from conftest import PASSWORD, TOKEN, Window, publish, save, start_server


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


def test_move_to_a_new_host_with_a_downloaded_backup(owner, browser, site, tmp_path):
    """Moving host: a backup downloaded from the old site, restored at
    the new site's setup - and the old password logs in, the posts there."""
    post = publish(owner, "Coming with me", "Words that move host.")
    owner.go("/admin/settings?tab=backup")
    with owner.page.expect_download() as got:
        owner.page.locator("form[action='/admin/backup/download'] button[type=submit]").click()
    path = os.path.join(tmp_path, "backup.zip")
    got.value.save_as(path)
    server, new = start_server()
    try:
        w = Window(browser, new["base"])
        w.go("/setup")
        w.page.get_by_role("link", name="Moving your site? Restore a backup").click()
        w.page.wait_for_load_state("networkidle")
        w.page.fill("input[name=token]", TOKEN)
        w.page.set_input_files("input[name=backup_zip]", path)
        w.page.get_by_role("button", name="Restore").click()
        w.page.wait_for_load_state("networkidle")
        assert "/login" in w.page.url and "Your site is back" in w.page.content()
        w.page.fill("input[name=password]", PASSWORD)
        w.page.get_by_role("button", name="Log in").click()
        w.page.wait_for_load_state("networkidle")
        assert "/login" not in w.page.url
        w.go(post)
        assert "Words that move host." in w.page.content()
        w.close()
    finally:
        server.terminate()
        server.wait(timeout=10)
        shutil.rmtree(new["data"], ignore_errors=True)
