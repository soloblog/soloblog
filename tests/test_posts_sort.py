"""The Posts list's "Last edited" sort: by when a post was saved, newest
first - and only a real edit moves a post, not a view or a like."""
import re

from conftest import save_post
from soloblog import posts
from soloblog.db import get_db

# the site is shared by every test, so each one names its posts apart
NAMES = ("Zed", "Amy", "Bob")


def _set_edited(slug, when):
    get_db().execute("UPDATE posts SET updated_at=? WHERE slug=?", (when, slug))
    get_db().commit()


def _order(admin, query, n):
    # the word in each title keeps other tests' posts out of the page
    html = admin.get(f"/admin/posts?{query}&q=srt{n}").text if "q=" not in query else admin.get("/admin/posts?" + query).text
    found = re.findall(rf">({'|'.join(NAMES)}) srt{n}<", html)
    return list(dict.fromkeys(found))  # a title shows twice in a row


def _three(admin, n):
    # written Zed, Amy, Bob; edited most recently: Amy, then Zed, then Bob
    slugs = {t: save_post(admin, title=f"{t} srt{n}", body=f"{t} apple{n}", tags="" if t == "Bob" else f"fruit{n}")
             for t in NAMES}
    for i, t in enumerate(("Bob", "Zed", "Amy")):
        _set_edited(slugs[t], f"2020-01-0{i + 1}T00:00:00")
    return slugs


def test_last_edited_orders_by_updated_time(admin):
    _three(admin, 1)
    assert "sort=edited" in admin.get("/admin/posts").text
    assert _order(admin, "sort=edited", 1) == ["Amy", "Zed", "Bob"]
    assert _order(admin, "sort=newest", 1) == ["Bob", "Amy", "Zed"]


def test_last_edited_keeps_search_tabs_and_type(admin):
    slugs = _three(admin, 2)
    assert _order(admin, "sort=edited&q=srt2", 2) == ["Amy", "Zed", "Bob"]
    assert _order(admin, "sort=edited&tag=fruit2", 2) == ["Amy", "Zed"]
    assert _order(admin, "sort=edited&kind=posts", 2) == ["Amy", "Zed", "Bob"]
    get_db().execute("UPDATE posts SET published=0 WHERE slug IN (?, ?)", (slugs["Zed"], slugs["Bob"]))
    get_db().commit()
    assert _order(admin, "sort=edited&status=draft", 2) == ["Zed", "Bob"]
    assert _order(admin, "sort=edited&status=published", 2) == ["Amy"]
    assert _order(admin, "sort=nonsense", 2) == ["Bob", "Amy", "Zed"]


def test_saving_moves_a_post_but_views_and_likes_do_not(admin):
    slugs = _three(admin, 3)
    before = posts.get_post(slugs["Bob"])["updated_at"]
    get_db().execute("UPDATE posts SET views=views+5, likes=likes+1 WHERE slug=?", (slugs["Bob"],))
    get_db().commit()
    assert posts.get_post(slugs["Bob"])["updated_at"] == before
    assert _order(admin, "sort=edited", 3) == ["Amy", "Zed", "Bob"]
    save_post(admin, slug=slugs["Bob"], title="Bob srt3", body="Edited")
    assert _order(admin, "sort=edited", 3)[0] == "Bob"
