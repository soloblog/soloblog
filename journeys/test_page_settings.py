"""A page's own settings, as people meet them: a note put in the wiki,
linked from another post and found; a talk shown as slides, moved with the
keys and left with Esc.

The settings are switched on through the API for now - the editor's own
form for them is built beside these journeys."""
import re

from conftest import Window, publish


def _set(w, site, path, **fields):
    """Changes a post's settings the way an app would: with an API key."""
    made = w.page.evaluate("""() => fetch('/admin/apikeys/new', {method: 'POST', credentials: 'same-origin',
        headers: {'HX-Request': 'true', 'Content-Type': 'application/x-www-form-urlencoded'},
        body: 'name=journey&scope=publish'}).then(r => r.text())""")
    found = re.search(r"sb_[A-Za-z0-9_-]{20,}", made)
    assert found, made[:600]
    changed = w.page.request.patch(site["base"] + "/api/v1/posts/" + path.rsplit("/", 1)[-1], data=fields,
                                   headers={"Authorization": f"Bearer {found.group(0)}"})
    assert changed.ok, changed.text()
    return changed.json()


def test_a_note_in_the_wiki_is_linked_and_found(owner, browser, site):
    w = owner
    note = publish(w, "Journey note", "A short note about starters.")
    other = publish(w, "Journey linking post", "I wrote it up in [[Journey note]].")
    assert _set(w, site, note, in_wiki=True)["in_wiki"] is True

    reader = Window(browser, site["base"])
    # the blog lists the post that links, not the note
    reader.go("/")
    page = reader.page.content()
    assert f'href="{other}"' in page and f'href="{note}"' not in page
    # the link leads to the note, which says what links to it
    reader.go(other)
    reader.page.get_by_role("link", name="Journey note").first.click()
    reader.page.wait_for_load_state("networkidle")
    assert reader.page.url.endswith(note)
    assert reader.page.get_by_text("Linked from").count() == 1
    assert reader.page.locator("a", has_text="Journey linking post").count() >= 1
    # and from the note, the wiki's front page lists it
    reader.page.get_by_role("link", name="All wiki pages").click()
    reader.page.wait_for_load_state("networkidle")
    assert reader.page.url.endswith("/wiki")
    assert reader.page.locator("a", has_text="Journey note").count() >= 1
    assert "Journey linking post" not in reader.page.content()
    reader.close()


def test_a_talk_as_slides_moves_with_the_keys_and_esc_leaves(owner, browser, site):
    talk = publish(owner, "Journey talk", "The first slide.\n\n---\n\nThe second slide.\n\n---\n\nThe third slide.")
    assert _set(owner, site, talk, slides=True)["slides"] is True

    reader = Window(browser, site["base"])
    reader.go(talk)
    # the whole screen: the deck, a way back, none of the site around it
    assert reader.page.locator("[data-site-header]").count() == 0 and reader.page.locator("footer").count() == 0
    box = reader.page.locator(".slides").bounding_box()
    assert box["width"] >= 1279 and box["height"] >= 899
    assert reader.page.get_by_role("link", name="Back to the site").count() == 1
    count = reader.page.locator(".slides-count")
    assert count.inner_text() == "1 / 3"
    # the arrow keys move between slides
    reader.page.keyboard.press("ArrowRight")
    reader.page.wait_for_function("() => document.querySelector('.slides-count').textContent === '2 / 3'")
    reader.page.keyboard.press("ArrowLeft")
    reader.page.wait_for_function("() => document.querySelector('.slides-count').textContent === '1 / 3'")
    # Esc goes back to the site
    reader.page.keyboard.press("Escape")
    reader.page.wait_for_url(site["base"] + "/")
    reader.page.wait_for_load_state("networkidle")
    assert reader.page.locator("[data-site-header]").count() == 1
    # and so does the link
    reader.go(talk)
    reader.page.get_by_role("link", name="Back to the site").click()
    reader.page.wait_for_url(site["base"] + "/")
    reader.close()
