import re

from soloblog import mail
from soloblog import newsletter
from soloblog import publishing
from soloblog import settings
from conftest import save_post
from soloblog.db import get_db

ON = {"newsletter_mode": "builtin", "email_provider": "smtp", "newsletter_auto": "1", "newsletter_on_posts": "1",
      "newsletter_on_home": "1"}
OFF = {"newsletter_mode": "", "email_provider": "", "newsletter_kit": ""}


def _outbox(monkeypatch):
    sent = []
    monkeypatch.setattr(mail, "send_email",
                        lambda to, subject, body, headers=None, html=None:
                        sent.append((to, subject, body, headers, html)) or True)
    monkeypatch.setattr(newsletter.time, "sleep", lambda s: None)
    return sent


def _wait(sent, n):
    import time
    for _ in range(100):
        if len(sent) >= n:
            return
        time.sleep(0.02)


def test_subscribe_confirm_unsubscribe(client, monkeypatch):
    sent = _outbox(monkeypatch)
    settings.set_many(ON)
    try:
        assert 'hx-post="/newsletter/subscribe"' in client.get("/").text
        assert "Newsletter" in client.get("/newsletter").text
        r = client.post("/newsletter/subscribe", data={"email": "reader@example.com"})
        assert "Check your email" in r.text
        _wait(sent, 1)
        token = re.search(r"/newsletter/confirm/(\S+)", sent[0][2]).group(1)
        assert newsletter.count() == 0  # not until it's confirmed
        assert "You're subscribed" in client.get(f"/newsletter/confirm/{token}").text
        assert newsletter.count() == 1
        # the same answer for an address already on the list - and no second email
        assert "Check your email" in client.post("/newsletter/subscribe", data={"email": "READER@example.com"}).text
        assert len(sent) == 1
        assert "Unsubscribe?" in client.get(f"/newsletter/unsubscribe/{token}").text
        client.post(f"/newsletter/unsubscribe/{token}")
        assert newsletter.count() == 0
        assert "doesn't look like" in client.post("/newsletter/subscribe", data={"email": "nope"}).text
    finally:
        settings.set_many(OFF)
        get_db().execute("DELETE FROM subscribers")
        get_db().commit()


def test_new_posts_are_emailed_once(admin, client, monkeypatch):
    sent = _outbox(monkeypatch)
    old = save_post(admin, title="Before the newsletter")
    settings.set_many({**ON, "newsletter_auto": "0"})
    token = newsletter.subscribe("fan@example.com")
    newsletter.confirm(token)
    try:
        # turning automatic sending on: what's already live isn't sent
        admin.post("/admin/settings/name", headers={"hx-request": "true"},
                   data={"site_title": "My Blog", "newsletter_mode": "builtin", "newsletter_auto": "1",
                         "declared_fields": "newsletter_mode,newsletter_auto"})
        publishing.check()
        assert not sent
        slug = save_post(admin, title="Fresh post", summary="The short version")
        save_post(admin, title="A page", pinned="1", pin_location="header")
        publishing.check()
        assert [s[1] for s in sent] == ["Fresh post"]
        to, subject, body, headers, html = sent[0]
        assert to == "fan@example.com" and "The short version" in body and f"/post/{slug}" in body
        assert headers["List-Unsubscribe"] == f"<{newsletter.unsubscribe_url(token)}>"
        # an edit isn't news
        save_post(admin, slug=slug, title="Fresh post", body="Edited.")
        publishing.check()
        assert len(sent) == 1
        assert old
    finally:
        settings.set_many(OFF)
        get_db().execute("DELETE FROM subscribers")
        get_db().commit()


def test_another_service_signs_readers_up(client):
    settings.set_many({"newsletter_mode": "kit", "newsletter_kit": "1234567"})
    try:
        html = client.get("/").text
        assert 'action="https://app.kit.com/forms/1234567/subscriptions"' in html and 'name="email_address"' in html
        assert "https://app.kit.com" in client.get("/").headers["content-security-policy"]
    finally:
        settings.set_many(OFF)
    assert 'id="newsletter"' not in client.get("/").text


def test_admin_subscribers_page(admin, client, monkeypatch):
    _outbox(monkeypatch)
    settings.set_many(ON)
    newsletter.confirm(newsletter.subscribe("a@example.com"))
    newsletter.subscribe("b@example.com")
    try:
        html = admin.get("/admin/newsletter").text
        assert "a@example.com" in html and "Not confirmed" in html and "1 subscriber" in html
        # export is ticking, as on Posts - no button that takes everyone
        assert "/admin/newsletter/export" not in html and 'id="subscribers-bulk"' in html
        csv = admin.post("/admin/newsletter/bulk", data={"action": "export", "all_matching": "1"})
        assert csv.headers["content-type"].startswith("text/csv") and "b@example.com" in csv.text
        assert client.get("/admin/newsletter").status_code == 303
    finally:
        settings.set_many(OFF)
        get_db().execute("DELETE FROM subscribers")
        get_db().commit()


def test_import_subscribers_from_another_service(admin):
    csv = "﻿Email,Name,Subscribed\nann@example.com,Ann,2024-01-01\nnot-an-email,x,y\nbob@example.com,Bob,2024-02-01\n"
    try:
        r = admin.post("/admin/newsletter/import", files={"csv": ("subs.csv", csv.encode(), "text/csv")})
        assert r.status_code == 303 and "Imported+2" in r.headers["location"] and "skipped+1" in r.headers["location"]
        assert newsletter.count() == 2
        # again: all already here
        added, skipped = newsletter.import_csv(csv)
        assert added == 0 and skipped == 3
        # no header row: the first column with an @
        assert newsletter.import_csv("x,carol@example.com\n") == (1, 0)
    finally:
        get_db().execute("DELETE FROM subscribers")
        get_db().commit()


def test_ticking_subscribers(admin, client, monkeypatch):
    _outbox(monkeypatch)
    settings.set_many(ON)
    keep = newsletter.subscribe("keep@example.com")
    newsletter.confirm(keep)
    newsletter.subscribe("spam1@example.com")
    newsletter.subscribe("spam2@example.com")
    ids = {r["email"]: r["id"] for r in newsletter.list_all()}
    try:
        # the ticked ones only
        csv = admin.post("/admin/newsletter/bulk", data={"action": "export", "ids": [ids["spam1@example.com"]]})
        assert "spam1@example.com" in csv.text and "keep@example.com" not in csv.text
        # every page Status matches - not the confirmed one
        r = admin.post("/admin/newsletter/bulk", data={"action": "remove", "all_matching": "1",
                                                        "in_state": "unconfirmed", "in_q": "spam",
                                                        "return_to": "https://evil.example/"})
        assert r.status_code == 303 and r.headers["location"].startswith("/admin/newsletter")
        assert [r["email"] for r in newsletter.list_all()] == ["keep@example.com"]
        # someone else can't, and nothing ticked does nothing
        r = client.post("/admin/newsletter/bulk", data={"action": "remove", "ids": [ids["keep@example.com"]]})
        assert r.status_code in (302, 303) and "toast" not in r.headers["location"]
        r = admin.post("/admin/newsletter/bulk", data={"action": "remove"})
        assert "Tick" in r.headers["location"] and newsletter.list_all()
        assert admin.get("/admin/newsletter/export").status_code in (404, 405)
    finally:
        settings.set_many(OFF)
        get_db().execute("DELETE FROM subscribers")
        get_db().commit()


def test_a_post_kept_out_of_the_newsletter(admin, monkeypatch):
    sent = _outbox(monkeypatch)
    settings.set_many(ON)
    publishing.baseline("newsletter")
    newsletter.confirm(newsletter.subscribe("kept@example.com"))
    try:
        assert 'name="newsletter_email"' in admin.get("/admin/new").text
        slug = save_post(admin, title="Not for email", newsletter_choice="1")  # the switch unticked
        publishing.check()
        assert not sent and newsletter.skipped(slug)
        tag = re.search(r'<input[^>]*name="newsletter_email"[^>]*>', admin.get(f"/admin/edit/{slug}").text).group(0)
        assert "checked" not in tag
        # a save from somewhere without the switch leaves it as it was
        save_post(admin, slug=slug, title="Not for email", body="Edited.")
        assert newsletter.skipped(slug)
        # ticked again before it goes: it goes
        save_post(admin, slug=slug, title="Not for email", newsletter_choice="1", newsletter_email="1")
        publishing.check()
        assert [m[1] for m in sent] == ["Not for email"]
        assert "Emailed to subscribers" in admin.get(f"/admin/edit/{slug}").text
    finally:
        settings.set_many(OFF)
        get_db().execute("DELETE FROM subscribers")
        get_db().commit()


def test_a_weekly_email_with_the_weeks_posts(admin, monkeypatch):
    from datetime import datetime
    sent = _outbox(monkeypatch)
    settings.set_many({**ON, "newsletter_digest": "week", "newsletter_digest_last": ""})
    publishing.baseline("newsletter")
    newsletter.confirm(newsletter.subscribe("weekly@example.com"))
    try:
        assert not newsletter.sending(settings.get_all())
        one = save_post(admin, title="Monday bread", summary="Crust")
        save_post(admin, title="Thursday bikes", summary="Gears")
        skipped = save_post(admin, title="Not this one", newsletter_choice="1")
        # on a Tuesday: run on a Monday morning, the check sent the week's email itself
        monkeypatch.setattr(publishing, "utcnow", lambda: datetime(2026, 11, 3, 10))
        publishing.check()
        assert not sent  # each post doesn't go by itself
        s = settings.get_all()
        assert not newsletter.digest_due(s, datetime(2026, 11, 3, 10))  # a Tuesday
        assert not newsletter.digest_due(s, datetime(2026, 11, 2, 8))  # Monday, before 9
        monday = datetime(2026, 11, 2, 9, 30)
        assert newsletter.digest_due(s, monday)
        assert newsletter.send_digest(s, monday) == 1
        to, subject, body, headers, html = sent[0]
        assert subject == f"This week on {settings.get('site_title')}" and "Monday bread" in body and "Thursday bikes" in body
        assert "Not this one" not in body and f"/post/{one}" in html and "Unsubscribe" in html
        assert body.index("Monday bread") < body.index("Thursday bikes")
        # once a week; and nothing new means no email
        assert not newsletter.digest_due(settings.get_all(), monday)
        assert newsletter.send_digest(settings.get_all(), datetime(2026, 11, 9, 9)) == 0 and len(sent) == 1
        assert newsletter.skipped(skipped)
        # monthly: the 1st
        settings.set_many({"newsletter_digest": "month"})
        assert newsletter.digest_due(settings.get_all(), datetime(2026, 12, 1, 9))
        assert not newsletter.digest_due(settings.get_all(), datetime(2026, 12, 2, 9))
    finally:
        settings.set_many({**OFF, "newsletter_digest": ""})
        get_db().execute("DELETE FROM subscribers")
        get_db().commit()


def test_the_designed_email_and_a_test_to_yourself(admin, monkeypatch):
    sent = _outbox(monkeypatch)
    settings.set_many({**ON, "newsletter_full": "1", "admin_email": "me@example.com"})
    try:
        slug = save_post(admin, title="Pictures <and> words",
                         body="Hello **there**.\n\n![A loaf](/uploads/loaf.webp)\n\n<script>x()</script>")
        row = __import__("soloblog.posts", fromlist=["x"]).get_post(slug)
        html = newsletter.post_email_html(row, settings.get_all(), "tok")
        assert "<strong>there</strong>" in html and "Pictures &lt;and&gt; words" in html
        assert 'src="http' in html and 'src="/uploads' not in html and "<script" not in html
        assert "max-width:100%" in html and newsletter.unsubscribe_url("tok") in html
        page = admin.get("/admin/newsletter").text
        assert "Send me a test" in page
        r = admin.post("/admin/newsletter/test", data={"slug": slug})
        assert "Test+sent" in r.headers["location"].replace("%20", "+")
        assert sent[-1][0] == "me@example.com" and sent[-1][4]
    finally:
        settings.set_many({**OFF, "newsletter_full": "0", "admin_email": ""})


def test_the_email_services_limit_is_told_apart(monkeypatch):
    def refused(text):
        monkeypatch.setattr(mail._last_error, "text", text, raising=False)
        return mail.over_limit()
    assert refused("HTTP Error 429: Too Many Requests - You have exceeded your daily email sending quota.")
    assert refused("HTTP Error 429: Too Many Requests - You have exceeded your monthly email sending quota.")
    assert refused("(550, b'5.4.5 Daily user sending limit exceeded.')")
    # not the limit: a bad address, a domain not set up, going a little too fast
    assert not refused("(550, b'5.1.1 The email account that you tried to reach does not exist')")
    assert not refused("HTTP Error 403: Forbidden - The example.com domain is not verified.")
    assert not refused("HTTP Error 429: Too Many Requests - Too many requests. Please limit the number of requests "
                       "per second.")
    assert not refused("")


def test_a_newsletter_cut_off_by_the_daily_limit_finishes_the_next_day(admin, monkeypatch):
    from datetime import datetime
    sent, allow = [], [2]

    def send(to, subject, body, headers=None, html=None):
        if len(sent) >= allow[0]:
            mail._last_error.text = ("HTTP Error 429: Too Many Requests - You have exceeded your daily email "
                                     "sending quota.")
            return False
        mail._last_error.text = ""
        sent.append((to, subject))
        return True
    monkeypatch.setattr(mail, "send_email", send)
    monkeypatch.setattr(newsletter.time, "sleep", lambda s: None)
    today = datetime(2026, 11, 4, 9)
    monkeypatch.setattr(newsletter, "utcnow", lambda: today)
    settings.set_many({**ON, "newsletter_held": "", "timezone": "UTC"})
    publishing.baseline("newsletter")
    tokens = [newsletter.subscribe(f"reader{n}@example.com") for n in range(5)]
    for token in tokens:
        newsletter.confirm(token)
    try:
        slug = save_post(admin, title="Big news")
        publishing.check()
        assert len(sent) == 2 and newsletter.emailed(slug)
        note = "Sent to 2 of 5 subscribers - your email service's limit was reached, so the rest go out tomorrow"
        assert note in admin.get(f"/admin/edit/{slug}").text
        assert "“Big news”" in admin.get("/admin/newsletter").text
        # not again the same day - and one of the rest unsubscribes meanwhile
        publishing.check()
        assert len(sent) == 2
        waiting = newsletter.held_for(slug)["ids"]
        gone = get_db().execute("SELECT token FROM subscribers WHERE id=?", (waiting[0],)).fetchone()["token"]
        newsletter.unsubscribe(gone)
        # the next day, after midnight UTC: the rest, once each
        today = datetime(2026, 11, 5, 0, 10)
        allow[0] = 100
        publishing.check()
        assert len(sent) == 4 and len({to for to, _ in sent}) == 4
        assert all(subject == "Big news" for _, subject in sent)
        assert newsletter.held() == [] and "Emailed to subscribers" in admin.get(f"/admin/edit/{slug}").text
        # a digest held back the same way still goes as a digest
        sent.clear()
        allow[0] = 1
        from soloblog import posts
        rows = [posts.get_post(slug), posts.get_post(save_post(admin, title="More news"))]
        newsletter.send_posts(rows, settings.get_all())
        assert len(sent) == 1 and len(newsletter.held()[0]["slugs"]) == 2
        assert "Your digest" in admin.get("/admin/newsletter").text
        today = datetime(2026, 11, 6, 1)
        allow[0] = 100
        newsletter.send_held(settings.get_all())
        assert len(sent) == 4 and len({subject for _, subject in sent}) == 1 and newsletter.held() == []
    finally:
        settings.set_many({**OFF, "newsletter_held": ""})
        get_db().execute("DELETE FROM subscribers")
        get_db().commit()
