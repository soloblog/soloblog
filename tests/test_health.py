"""Site health: each check's verdict, the page, Verify a backup, and that
nothing secret ever reaches the Info tab."""
import io
import zipfile
from collections import namedtuple
from datetime import timedelta
from soloblog.tz import utcnow

from soloblog import config
from soloblog import health
from soloblog import settings

KEYS = ("backup_last_at", "last_backup_download", "backup_verified_at", "backup_verified_result", "email_provider",
        "email_api_key", "email_api_from", "mail_last_ok_at", "mail_last_failed_at", "mail_last_error",
        "search_noindex", "site_title", "admin_email", "smtp_password", "health_remote", "health_alerts",
        "db_check_at", "db_check_result")


def _keep():
    return {k: settings.get(k) for k in KEYS}


def _ago(**kw):
    return (utcnow() - timedelta(**kw)).isoformat()


def test_backups(monkeypatch):
    before = _keep()
    try:
        settings.set_many({"backup_last_at": "", "last_backup_download": ""})
        assert health.backup_check()["status"] == health.CRITICAL
        settings.set_many({"last_backup_download": _ago(days=40)})
        assert health.backup_check()["status"] == health.CRITICAL
        settings.set_many({"last_backup_download": _ago(days=10)})
        assert health.backup_check()["status"] == health.RECOMMENDED
        # the newer of a download and a bucket backup counts
        settings.set_many({"backup_last_at": _ago(hours=2)})
        r = health.backup_check()
        assert r["status"] == health.GOOD and "today" in r["title"]
        # without a bucket there's nothing here to verify; with one, never checked is a recommendation
        assert health.verify_check() is None
        from soloblog import storage
        monkeypatch.setattr(storage, "enabled", lambda: True)
        # a pretend bucket - no automatic backup may set off for it
        monkeypatch.setattr(storage, "note_change", lambda: None)
        monkeypatch.setattr(storage, "last_status", lambda: {"at": None, "error": "", "pending": False})
        assert health.verify_check()["status"] == health.RECOMMENDED
        settings.set_many({"backup_verified_at": _ago(days=1), "backup_verified_result": "it couldn't be opened"})
        assert health.verify_check()["status"] == health.CRITICAL
        settings.set_many({"backup_verified_result": "ok"})
        assert health.verify_check()["status"] == health.GOOD
        # a failed automatic backup outranks everything else about backups
        monkeypatch.setattr(storage, "last_status", lambda: {"at": None, "error": "access denied", "pending": False})
        r = health.backup_check()
        assert r["status"] == health.CRITICAL and "access denied" in r["why"]
    finally:
        settings.set_many(before)


def test_a_connected_bucket_with_no_backup_says_so(monkeypatch):
    # connected but empty: no "connect cloud storage", and nothing to verify yet
    from soloblog import storage
    before = _keep()
    try:
        monkeypatch.setattr(storage, "enabled", lambda: True)
        monkeypatch.setattr(storage, "note_change", lambda: None)
        monkeypatch.setattr(storage, "last_status", lambda: {"at": None, "error": "", "pending": False})
        settings.set_many({"backup_last_at": "", "last_backup_download": _ago(days=52)})
        r = health.backup_check()
        assert r["status"] == health.CRITICAL and "connect cloud storage" not in r["why"]
        assert "no backup has been made there yet" in r["why"]
        assert health.verify_check() is None
        settings.set_many({"last_backup_download": ""})
        assert health.backup_check()["title"] == "No backup has reached your bucket yet"
        # once one has, it's checked as before
        settings.set_many({"backup_last_at": _ago(hours=1)})
        assert health.backup_check()["status"] == health.GOOD
        assert health.verify_check()["status"] in (health.RECOMMENDED, health.GOOD, health.CRITICAL)
    finally:
        settings.set_many(before)


def test_security(monkeypatch):
    monkeypatch.setattr(config, "SESSION_SECRET", health.DEFAULT_SECRET)
    assert health.secret_check()["status"] == health.CRITICAL
    monkeypatch.setattr(config, "SESSION_SECRET", "x" * 64)
    assert health.secret_check()["status"] == health.GOOD
    # HTTPS only matters on a real address
    monkeypatch.setattr(config, "BASE_URL", "http://localhost:5001")
    assert health.https_check() is None
    monkeypatch.setattr(config, "BASE_URL", "http://blog.example.com")
    assert health.https_check()["status"] == health.CRITICAL
    monkeypatch.setattr(config, "BASE_URL", "https://blog.example.com")
    assert health.https_check()["status"] == health.GOOD
    # BASE_URL against the address the site is reached at
    assert health.address_check("blog.example.com")["status"] == health.GOOD
    assert health.address_check("www.example.com")["status"] == health.RECOMMENDED
    assert health.address_check("") is None


def test_email_and_its_last_send(monkeypatch):
    from soloblog import mail
    before = _keep()
    try:
        settings.set_many({"email_provider": "", "mail_last_ok_at": "", "mail_last_failed_at": "", "mail_last_error": "",
                           "admin_email": ""})
        # one check for email, saying which half is missing - not two
        assert health.email_check()["title"] == "Email isn't set up"
        settings.set_many({"admin_email": "me@example.com"})
        assert health.email_check()["title"] == "Email can't be sent yet"
        settings.set_many({"admin_email": "", "email_provider": "api", "email_api_key": "re_test",
                           "email_api_from": "a@example.com"})
        r = health.email_check()
        assert r["status"] == health.RECOMMENDED and "address" in r["title"] and "tab=email" in r["href"]
        assert not hasattr(health, "admin_email_check")
        settings.set_many({"admin_email": "me@example.com"})
        r = health.email_check()
        assert r["status"] == health.GOOD and "Nothing's been sent yet" in r["why"]
        # send_email notes how each one went
        monkeypatch.setattr(mail, "_send_api", lambda *a: True)
        assert mail.send_email("x@example.com", "Hi", "Body")
        assert settings.get("mail_last_ok_at") and health.email_check()["status"] == health.GOOD

        def refused(*a):
            mail._last_error.text = "HTTP Error 403: Forbidden"
            return False
        monkeypatch.setattr(mail, "_send_api", refused)
        assert not mail.send_email("x@example.com", "Hi", "Body")
        r = health.email_check()
        assert r["status"] == health.CRITICAL and "403" in r["why"]
        # one that goes out again puts it right
        monkeypatch.setattr(mail, "_send_api", lambda *a: True)
        mail.send_email("x@example.com", "Hi", "Body")
        assert health.email_check()["status"] == health.GOOD
    finally:
        settings.set_many(before)


def test_updates_disk_database_visibility_scheduler(monkeypatch):
    from soloblog import publishing, updates
    before = _keep()
    try:
        monkeypatch.setattr(config, "UPDATE_CHECK", True)
        monkeypatch.setattr(updates, "newer", lambda: None)
        assert health.updates_check()["status"] == health.GOOD
        monkeypatch.setattr(updates, "newer", lambda: ("9.0.0", "https://example.com"))
        monkeypatch.setitem(updates._state, "notes", "### Added\n\n- **Something**")
        assert health.updates_check()["status"] == health.RECOMMENDED
        monkeypatch.setitem(updates._state, "notes", "### Security\n\n- A fix")
        assert health.updates_check()["status"] == health.CRITICAL
        Usage = namedtuple("Usage", "total used free")
        monkeypatch.setattr(health.shutil, "disk_usage", lambda p: Usage(100 * 2**30, 97 * 2**30, 3 * 2**30))
        assert health.disk_check()["status"] == health.CRITICAL
        monkeypatch.setattr(health.shutil, "disk_usage", lambda p: Usage(100 * 2**30, 90 * 2**30, 10 * 2**30))
        assert health.disk_check()["status"] == health.RECOMMENDED
        # the integrity check runs when it's a week old, and its answer is kept
        settings.set_many({"db_check_at": "", "db_check_result": ""})
        # on its own connection: the app's long-lived ones gave false alarms about the search index
        assert health.database_check()["status"] == health.GOOD and settings.get("db_check_result") == "ok", \
            settings.get("db_check_result")
        settings.set_many({"db_check_at": _ago(days=1), "db_check_result": "row 3 missing from index"})
        assert health.database_check()["status"] == health.CRITICAL
        settings.set_many({"search_noindex": "1", "site_title": "My Blog"})
        assert {r["key"]: r["status"] for r in health.visibility_checks()} == {
            "noindex": health.RECOMMENDED, "title": health.RECOMMENDED}
        # the scheduler: only once it's running
        monkeypatch.setattr(publishing, "AUTOMATIC", True)
        monkeypatch.setattr(publishing, "_last_run", None)
        assert health.scheduler_check() is None
        monkeypatch.setattr(publishing, "_last_run", utcnow().timestamp() - 3600)
        assert health.scheduler_check()["status"] == health.CRITICAL
        monkeypatch.setattr(publishing, "_last_run", utcnow().timestamp() - 30)
        assert health.scheduler_check()["status"] == health.GOOD
    finally:
        settings.set_many(before)


def test_the_page(admin, client):
    assert client.get("/admin/health").status_code in (302, 303)
    html = admin.get("/admin/health").text
    # most serious first, what passed folded away, Disk space and the options below
    assert "Site health" in html and 'id="disk"' in html and 'name="health_remote"' in html
    assert html.find("Needs attention") < html.find("Recommended") < html.find("Passed (")
    assert 'href="/admin/health"' in admin.get("/admin/posts").text
    info = admin.get("/admin/health?tab=info").text
    assert config.VERSION in info and "Copy for a bug report" in info


def test_info_never_has_a_secret(admin):
    before = _keep()
    try:
        settings.set_many({"smtp_password": "hunter2-secret", "email_api_key": "re_live_secret_key"})
        text = health.info_text()
        page = admin.get("/admin/health?tab=info").text
        for secret in ("hunter2-secret", "re_live_secret_key", config.SESSION_SECRET):
            assert secret not in text and secret not in page
    finally:
        settings.set_many(before)


def test_verify_a_backup(admin, monkeypatch):
    from soloblog import backup, storage
    before = _keep()
    try:
        monkeypatch.setattr(storage, "enabled", lambda: True)
        monkeypatch.setattr(storage, "note_change", lambda: None)
        monkeypatch.setattr(storage, "list_backups", lambda: [{"key": "backups/soloblog-1.zip"}])
        settings.set_many({"backup_last_at": _ago(hours=1)})
        good = backup.build_backup_zip({"posts", "settings", "comments"})
        monkeypatch.setattr(storage, "get_backup", lambda key: good)
        r = admin.post("/admin/health/verify")
        assert r.status_code == 303 and settings.get("backup_verified_result") == "ok"
        # a damaged one, and one with no database, are problems - said plainly
        monkeypatch.setattr(storage, "get_backup", lambda key: b"not a zip at all")
        admin.post("/admin/health/verify")
        assert "couldn't be opened" in settings.get("backup_verified_result")
        empty = io.BytesIO()
        with zipfile.ZipFile(empty, "w") as zf:
            zf.writestr("posts/a.md", "---\ntitle: A\n---\nHi")
        monkeypatch.setattr(storage, "get_backup", lambda key: empty.getvalue())
        admin.post("/admin/health/verify")
        assert "no settings" in settings.get("backup_verified_result")
        assert health.verify_check()["status"] == health.CRITICAL
    finally:
        settings.set_many(before)


def test_options(admin, client):
    before = _keep()
    try:
        r = admin.post("/admin/health/options", headers={"HX-Request": "true"},
                       data={"health_alerts": "1", "declared_fields": "health_remote,health_alerts"})
        assert "Saved" in r.text
        assert settings.get("health_remote") == "0" and settings.get("health_alerts") == "1"
        # someone else can't switch them
        client.post("/admin/health/options", data={"declared_fields": "health_alerts"})
        assert settings.get("health_alerts") == "1"
    finally:
        settings.set_many(before)


# ---- the checks that ask other servers (nothing here reaches the internet)

def _doh(records_by_name):
    """A stand-in for DNS over HTTPS: {name: [txt, ...]} - a missing name
    is NXDOMAIN."""
    def answer(url, headers=None):
        from urllib.parse import parse_qs, urlparse
        name = parse_qs(urlparse(url).query)["name"][0]
        if name not in records_by_name:
            return {"Status": 3}
        return {"Status": 0, "Answer": [{"type": 16, "data": f'"{r}"'} for r in records_by_name[name]]}
    return answer


def test_dns_and_the_email_records(monkeypatch):
    from soloblog import health_remote
    before = _keep()
    try:
        settings.set_many({"email_provider": "api", "email_api_key": "re_x", "email_api_from": "Mira <mira@Example.com>"})
        assert health_remote.sending_domain() == "example.com"
        monkeypatch.setattr(health_remote, "_json", _doh({
            "example.com": ["v=spf1 include:amazonses.com ~all", "google-site-verification=abc"],
            "_dmarc.example.com": ["v=DMARC1; p=none"],
            "resend._domainkey.example.com": ["p=MIGfMA0GCSqGSIb3DQEB"]}))
        found = {r["key"]: r["status"] for r in health_remote.email_checks()}
        assert found == {"spf": health.GOOD, "dmarc": health.GOOD, "dkim": health.GOOD}
        monkeypatch.setattr(health_remote, "_json", _doh({"example.com": ["v=spf1 a ~all", "v=spf1 mx ~all"]}))
        found = {r["key"]: r for r in health_remote.email_checks()}
        assert found["spf"]["status"] == health.RECOMMENDED and "2 SPF records" in found["spf"]["title"]
        assert found["dmarc"]["status"] == health.RECOMMENDED and found["dkim"]["status"] == health.RECOMMENDED

        # no DNS server answers: nothing is said, rather than a false alarm
        def down(url, headers=None):
            raise OSError("network is unreachable")
        monkeypatch.setattr(health_remote, "_json", down)
        assert health_remote.txt_records("example.com") is None and health_remote.email_checks() == []
        # without email, there's nothing to check
        settings.set_many({"email_provider": ""})
        assert health_remote.email_checks() == []
    finally:
        settings.set_many(before)


def test_the_certificate_and_the_domain(monkeypatch):
    import ssl
    import urllib.error
    from soloblog import health_remote
    soon = lambda days: utcnow() + timedelta(days=days, hours=1)  # noqa: E731
    for days, status in ((3, health.CRITICAL), (10, health.RECOMMENDED), (60, health.GOOD)):
        monkeypatch.setattr(health_remote, "cert_expiry", lambda host, d=days: soon(d))
        assert health_remote.cert_check("blog.example.com")["status"] == status, days

    def invalid(host):
        raise ssl.SSLCertVerificationError(1, "certificate has expired")
    monkeypatch.setattr(health_remote, "cert_expiry", invalid)
    assert health_remote.cert_check("blog.example.com")["status"] == health.CRITICAL

    def unreachable(host):
        raise OSError("timed out")
    monkeypatch.setattr(health_remote, "cert_expiry", unreachable)
    assert health_remote.cert_check("blog.example.com") is None
    # RDAP: the address itself isn't registered, the domain above it is
    asked = []

    def rdap(url, headers=None):
        asked.append(url.rsplit("/", 1)[1])
        if url.endswith("/blog.example.com"):
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
        return {"events": [{"eventAction": "registration", "eventDate": "2020-01-01T00:00:00Z"},
                           {"eventAction": "expiration", "eventDate": soon(20).isoformat() + "Z"}]}
    monkeypatch.setattr(health_remote, "_json", rdap)
    r = health_remote.domain_check("blog.example.com")
    assert asked == ["blog.example.com", "example.com"] and r["status"] == health.RECOMMENDED
    assert r["title"].startswith("example.com runs out in")
    # an address on the host's own domain: its renewal isn't yours
    asked.clear()
    assert health_remote.domain_check("myblog.fly.dev") is None and asked == []


def test_results_are_kept_and_shown(admin, monkeypatch):
    from soloblog import health_remote
    before = _keep()
    try:
        settings.set_many({"health_remote": "1", "health_remote_results": ""})
        monkeypatch.setattr(health_remote, "run_remote", lambda: [health.check(
            "cert", "domain", health.RECOMMENDED, "Your HTTPS certificate runs out in 10 days", "Check it.")])
        health_remote.refresh()
        assert [r["key"] for r in health_remote.stored()] == ["cert"]
        assert health_remote.checked_label() == "just now"
        html = admin.get("/admin/health").text
        assert "runs out in 10 days" in html and "Certificate, domain and email checked just now" in html
        # says what's checked, not how
        assert "other servers" not in html and "Check certificate, domain and email" in html
        # turned off: none of them, and no Check again
        settings.set_many({"health_remote": "0"})
        assert health_remote.stored() == [] and "Check again" not in admin.get("/admin/health").text
    finally:
        settings.set_many(before)


def test_alerts(admin, monkeypatch):
    from soloblog import health_alerts, mail
    before = _keep()
    sent = []
    try:
        settings.set_many({"admin_email": "mira@example.com", "health_alerts": "1", "health_alerted": "",
                           "health_critical": "0"})
        monkeypatch.setattr(mail, "can_send", lambda: True)
        monkeypatch.setattr(mail, "send_email", lambda to, subject, body, headers=None: sent.append(subject) or True)
        bad = [health.check("backup", "backups", health.CRITICAL, "There's no backup yet", "Back up."),
               health.check("login", "security", health.RECOMMENDED, "Your login has only a password", "Add one.")]
        assert [r["key"] for r in health_alerts.check_and_send(bad)] == ["backup"]
        assert len(sent) == 1 and "There's no backup yet" in sent[0]
        # the menu shows the dot while it's there
        assert health_alerts.needs_attention() == 1 and "status status-error" in admin.get("/admin/posts").text
        # not again within the week
        assert health_alerts.check_and_send(bad) == [] and len(sent) == 1
        # put right, then wrong again: a new email
        health_alerts.check_and_send(bad[1:])
        assert health_alerts.needs_attention() == 0 and "status status-error" not in admin.get("/admin/posts").text
        health_alerts.check_and_send(bad)
        assert len(sent) == 2
        # turned off, or nowhere to send it: nothing
        settings.set_many({"health_alerted": "", "health_alerts": "0"})
        assert health_alerts.check_and_send(bad) == [] and len(sent) == 2
    finally:
        settings.set_many({**before, "health_alerted": "", "health_critical": "0"})


def test_bug_report_says_what_is_used_but_nothing_personal(admin):
    from soloblog import health
    from soloblog import settings
    settings.set_many({"site_title": "A Very Private Diary"})
    text = health.info_text()
    assert "## Features in use" in text and "- Members:" in text and "- Host:" in text
    assert "A Very Private Diary" not in text
    # how the address is set, never the address itself - it's pasted in public
    from soloblog import config
    assert config.BASE_URL.split("://")[1] not in text and "- Address: http" in text
    assert health._about(0) == "none" and health._about(12) == "10-49" and health._about(5000) == "1,000+"


def test_problems_are_logged_shown_and_cleaned_for_a_report(admin):
    """Site health > Log: Soloblog's warnings and errors are kept for two
    weeks, shown once with how many times, cleared from Disk space - and
    in a bug report without anything that says whose site it is."""
    import json
    import logging
    from soloblog import backup, health
    health.clear_log()
    log = logging.getLogger("soloblog.mail")
    log.info("a routine event isn't a problem")
    for _ in range(2):
        log.warning("smtp send failed for jane@smith.org via smtp.smith.org: %s", "535 not accepted")
    try:
        raise ValueError("token tok51HxYZabc123def456GHI789 was refused")
    except ValueError:
        logging.getLogger("soloblog.storage").exception("copying to the bucket failed")
    # an old one, past the two weeks
    with open(health.LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps({"at": "2001-01-01T00:00:00", "level": "WARNING", "where": "soloblog.mail",
                            "message": "long ago", "detail": ""}) + "\n")
    found = health.problems()
    assert [e["where"] for e in found] == ["soloblog.storage", "soloblog.mail", "soloblog.mail"]
    page = admin.get("/admin/health?tab=log").text
    assert "Email" in page and "2 times" in page and "Cloud storage" in page and "long ago" not in page
    assert "routine event" not in page and "Traceback" in page
    report = health.info_text("myblog.example")
    assert "## Recent problems" in report and "Email · warning" in report and "(2 times)" in report
    assert "jane@smith.org" not in report and "[email]" in report and "tok51HxYZ" not in report
    assert "ValueError" in report and "soloblog/" in report
    assert "[email]" in admin.get("/admin/health?tab=info").text
    # Disk space lists it, and clears it
    assert "log" in [k for k, _, _ in backup.disk_usage()["parts"]]
    r = admin.post("/admin/disk/clear-log", data={"back": "log"})
    assert r.status_code == 303 and "tab=log" in r.headers["location"] and health.problems() == []
    assert "Nothing&#x27;s gone wrong lately" in admin.get("/admin/health?tab=log").text \
        or "Nothing's gone wrong lately" in admin.get("/admin/health?tab=log").text


def test_cleaning_keeps_what_diagnoses_and_drops_what_identifies():
    from soloblog.health import clean_for_report as clean
    assert clean("for jane@smith.org at 10:42:01") == "for [email] at 10:42:01"
    assert clean("fetch https://smith.org/feed?token=abc failed") == "fetch [link] failed"
    assert clean("from 192.168.1.20 and 2001:db8::1") == "from [address] and [address]"
    assert clean("list_approved_with_deleted_parents failed") == "list_approved_with_deleted_parents failed"
    assert clean("can't read holiday-in-rome.jpg") == "can't read [file]"
    assert clean("GET /post/my-secret-plans failed") == "GET /post/[name] failed"
    assert clean("delivery to myblog.example failed", "myblog.example") == "delivery to [your site] failed"


def test_the_detailed_log(admin, client, monkeypatch, tmp_path):
    """Everything noted, four weeks, one file a day; the path of each page
    but never what follows a ? or who asked; problems stay in their own
    log too; the download warns what's in it; the switch stops it."""
    import logging
    import os
    monkeypatch.setattr(health, "DETAIL_DIR", str(tmp_path / "detail"))
    log = logging.getLogger("soloblog.test_detail")
    log.info("a routine step")
    client.get("/post/does-not-exist?token=secret-reset-token", headers={"X-Forwarded-For": "203.0.113.9"})
    text = health.detail_text("example.com")
    assert "a routine step" in text and "GET /post/does-not-exist 404" in text
    assert "secret-reset-token" not in text and "203.0.113.9" not in text
    assert "personal details" in text and "example.com" in text
    # the routine step isn't a problem
    assert not any("a routine step" in e["message"] for e in health.problems())
    # a day older than four weeks goes; past the size limit, the oldest first
    old = tmp_path / "detail" / "2000-01-01.log"
    old.write_text("old\n")
    health.prune_detail()
    assert not old.exists()
    monkeypatch.setattr(health, "DETAIL_MAX", 10)
    (tmp_path / "detail" / "2999-01-01.log").write_text("x" * 50)
    health.prune_detail()
    assert len(os.listdir(tmp_path / "detail")) == 1  # the newest day always stays
    # the download, its warning, and its file
    page = admin.get("/admin/health?tab=log").text
    assert "Download detailed log" in page and "Keep it to yourself" in page
    r = admin.get("/admin/health/log/download")
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    assert r.headers["content-type"].startswith("text/plain")
    assert client.get("/admin/health/log/download").status_code in (302, 303)  # only the admin
    # the switch: off, nothing more is written
    settings.set_many({"detail_log": "0"})
    try:
        log.info("while it's off")
        assert "while it's off" not in health.detail_text()
    finally:
        settings.set_many({"detail_log": "1"})
    # Disk space has it apart from the problems log, with its own Clear
    from soloblog import backup
    assert ("detail_log", "Detailed log", "logs/detail/") in backup.DISK_PARTS
    admin.post("/admin/disk/clear-detail-log")
    # it starts again from now - the Clear itself is its first line
    assert "a routine step" not in health.detail_text() and "clear-detail-log" in health.detail_text()


def test_alerts_say_where_your_email_is(admin):
    # "Admin email" (once "Your email") moved from Security to Email; the alerts' line still
    # said Security - now a link that opens the field
    page = admin.get("/admin/health").text
    assert "(Security)" not in page and 'href="/admin/settings?tab=email#admin_email"' in page
    assert 'id="admin_email"' in admin.get("/admin/settings?tab=email").text


def test_a_site_that_wouldnt_survive_its_next_update(monkeypatch, tmp_path):
    from soloblog import config, storage
    monkeypatch.setattr(config, "data_dir", lambda: str(tmp_path))
    monkeypatch.setattr(config, "BASE_URL", "https://blog.example.com")
    monkeypatch.setattr(storage, "enabled", lambda: False)
    # a server's own disk keeps it, with or without mounts
    monkeypatch.setattr(health, "host_kind", lambda: "other")
    assert health.data_kept() and health.storage_check() is None
    # in a container: kept only on a volume - the folder or one above it
    monkeypatch.setattr(health, "host_kind", lambda: "Railway")
    monkeypatch.setattr(health.os.path, "ismount", lambda p: p == "/")
    r = health.storage_check()
    assert r["status"] == health.CRITICAL and "lost on the next update" in r["title"]
    assert "In Railway, add a volume" in r["why"] and str(tmp_path) in r["why"] and "tab=backup" in r["href"]
    monkeypatch.setattr(health.os.path, "ismount", lambda p: p == str(tmp_path.parent))
    assert health.data_kept()
    # put back from a bucket on each start: survivable, but say so
    monkeypatch.setattr(health.os.path, "ismount", lambda p: p == "/")
    monkeypatch.setattr(storage, "enabled", lambda: True)
    monkeypatch.setattr(config, "S3_RESTORE_ON_BOOT", True)
    assert health.storage_check()["status"] == health.RECOMMENDED
    # trying it out on a computer, or the demo: never
    monkeypatch.setattr(config, "BASE_URL", "http://localhost:5001")
    assert health.data_kept()


def test_setup_says_where_the_token_is_and_warns_about_storage(monkeypatch):
    from soloblog import auth, config
    from soloblog.routes import auth_routes
    monkeypatch.setattr(auth, "admin_exists", lambda: False)
    monkeypatch.setattr(config, "SETUP_TOKEN", "")
    monkeypatch.setattr(health, "host_kind", lambda: "Render")
    monkeypatch.setattr(health, "data_kept", lambda: False)
    page = str(auth_routes.setup_page())
    assert "In Render, open this service&#x27;s Logs" in page or "In Render, open this service's Logs" in page
    assert "alert-warning" in page and "add a disk" in page
    monkeypatch.setattr(health, "host_kind", lambda: "other")
    assert "setup-token.txt" in auth_routes.token_help()
    monkeypatch.setattr(config, "SETUP_TOKEN", "a-token-you-chose-1234")
    assert "you chose" in auth_routes.token_help()
    # the Render button makes the token: setup says where Render shows it
    monkeypatch.setattr(health, "host_kind", lambda: "Render")
    assert auth_routes.token_help() == "In Render, open this service's Environment and copy SETUP_TOKEN."



def test_an_app_store_package_names_its_platform(monkeypatch):
    """Umbrel, Unraid, Coolify... set nothing Soloblog can tell them by, so
    their packages say HOSTED_ON - and setup says where that platform shows
    the token. Umbrel shows no logs: its package uses the password umbrelOS
    shows as the token."""
    from soloblog import auth, config
    from soloblog.routes import auth_routes
    monkeypatch.setattr(auth, "admin_exists", lambda: False)
    for name in ("FLY_APP_NAME", "RENDER", "RAILWAY_ENVIRONMENT", "KOYEB_APP_NAME", "DYNO",
                 "KUBERNETES_SERVICE_HOST"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HOSTED_ON", " Unraid ")
    assert health.host_kind() == "Unraid"
    monkeypatch.setattr(config, "SETUP_TOKEN", "")
    assert auth_routes.token_help().startswith("In Unraid's Docker tab")
    monkeypatch.setenv("HOSTED_ON", "umbrelOS")
    monkeypatch.setattr(config, "SETUP_TOKEN", "a" * 64)
    monkeypatch.setattr(auth, "setup_token", lambda: "a" * 64)
    assert "Show default credentials" in auth_routes.token_help()
    # a platform without its own words still gets the general ones
    monkeypatch.setenv("HOSTED_ON", "Somewhere new")
    monkeypatch.setattr(config, "SETUP_TOKEN", "")
    monkeypatch.setattr(auth, "setup_token", lambda: "b" * 20)
    assert "setup-token.txt" in auth_routes.token_help()
    # every package in deploy/platforms names a platform setup knows
    import re
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent / "deploy" / "platforms"
    named = set()
    for f in root.rglob("*"):
        if f.is_file() and f.suffix in (".yml", ".yaml", ".toml", ".xml", ".json", ".ts", ".sh", ""):
            named |= set(re.findall(r"HOSTED_ON(?:\"[^>]*>|\W{1,8})([A-Za-z]+)", f.read_text(encoding="utf-8")))
    known = set(auth_routes.TOKEN_IN_LOG) | set(auth_routes.TOKEN_SHOWN)
    assert named and named <= known, named - known


def test_the_render_and_heroku_buttons_make_a_setup_token():
    import json
    from pathlib import Path
    import yaml
    root = Path(__file__).resolve().parent.parent
    render = yaml.safe_load((root / "render.yaml").read_text())
    env = {v["key"]: v for v in render["services"][0]["envVars"]}
    assert env["SETUP_TOKEN"].get("generateValue") is True
    heroku = json.loads((root / "app.json").read_text())
    assert heroku["env"]["SETUP_TOKEN"]["generator"] == "secret"


def test_a_placeholder_session_secret_is_never_used(monkeypatch, tmp_path):
    from soloblog import config
    monkeypatch.setattr(config, "SECRET_FILE", str(tmp_path / ".session_secret"))
    monkeypatch.setattr(config, "DATA_DIR", str(tmp_path))
    # the DigitalOcean template's old example: public, so anyone could sign a login with it
    monkeypatch.setenv("SESSION_SECRET", "change-me-to-a-long-random-string")
    secret, where = config._session_secret()
    assert where == "file" and len(secret) >= 32 and secret != "change-me-to-a-long-random-string"
    r = health.secret_check()
    assert r["status"] == health.RECOMMENDED and "placeholder" in r["title"]
    monkeypatch.setenv("SESSION_SECRET", "x" * 64)
    assert config._session_secret() == ("x" * 64, "env")


def test_email_from_resend_dev_only_reaches_you(monkeypatch):
    # Resend's try-out address sends only to the account's own address: the
    # owner's test arrives and members' sign-in links don't
    before = _keep()
    extra = {k: settings.get(k) for k in ("members_enabled", "newsletter_mode")}
    try:
        settings.set_many({"email_provider": "api", "email_api_key": "re_test", "admin_email": "me@example.com",
                           "email_api_from": "onboarding@resend.dev", "mail_last_ok_at": _ago(hours=1),
                           "mail_last_failed_at": "", "mail_last_error": "", "members_enabled": "0",
                           "newsletter_mode": ""})
        r = health.email_check()
        assert r["title"] == "Email only reaches you" and r["status"] == health.RECOMMENDED
        assert "resend.dev" in r["why"] and "tab=email" in r["href"]
        # worse while someone else depends on it
        settings.set_many({"members_enabled": "1"})
        assert health.email_check()["status"] == health.CRITICAL
        settings.set_many({"members_enabled": "0", "newsletter_mode": "builtin"})
        assert health.email_check()["status"] == health.CRITICAL
        # written with a name, or in capitals, it's the same address
        settings.set_many({"email_api_from": "Mira <Onboarding@Resend.dev>"})
        assert health.email_check()["title"] == "Email only reaches you"
        # an address at your own domain, or another way of sending, is fine
        settings.set_many({"email_api_from": "hello@mirabakes.com"})
        assert health.email_check()["status"] == health.GOOD
        settings.set_many({"email_api_from": "onboarding@resend.dev", "email_provider": "smtp"})
        assert health.email_check()["title"] != "Email only reaches you"
        # a domain that merely ends in it isn't Resend's
        settings.set_many({"email_provider": "api", "email_api_from": "a@notresend.dev"})
        assert health.email_check()["title"] != "Email only reaches you"
    finally:
        settings.set_many({**before, **extra})


def test_the_bug_report_names_the_sections_and_templates_in_use_not_layouts(admin):
    """Copy for a bug report: the kinds of section the site uses, rough counts only - no titles or words."""
    from conftest import save_post
    from soloblog import health, posts
    slug = save_post(admin, title="A page with sections", body="## Plans\n\nSection: Pricing\n\n### Basic\n\nPrice: US$1\n\n"
                                                           "## Questions\n\nSection: FAQ\n\n### Why?\n\nBecause.\n")
    try:
        rows = dict(health.features())
        assert "Page layouts" not in rows
        assert "Pricing (1-9)" in rows["Sections in use"] and "FAQ (1-9)" in rows["Sections in use"]
        assert rows["Custom templates"] in ("none", "1-9")
        assert "A page with sections" not in " ".join(str(v) for v in rows.values())
    finally:
        posts.delete_post(slug)


def test_a_second_copy_on_the_same_data_is_reported(monkeypatch, tmp_path):
    import fcntl
    lock = str(tmp_path / ".running")
    monkeypatch.setattr(health, "lock_path", lambda: lock)
    monkeypatch.setattr(health, "_claim", None)
    monkeypatch.setattr(health, "CLAIM_TRIES", 2)
    monkeypatch.setattr(health, "CLAIM_WAIT", 0)
    other = open(lock, "a")  # noqa: SIM115 - another copy holding the folder
    fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        health.claim_or_report()
        assert health._claim is None
        r = health.copies_check()
        assert r["status"] == health.CRITICAL and r in health.run()
    finally:
        other.close()
    # the other copy stopped: this one takes the folder, and the warning goes
    health.claim_or_report()
    assert health._claim is not None and health.copies_check() is None
    health._claim.close()
