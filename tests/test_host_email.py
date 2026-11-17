"""Email and the admin's address set on the host (SMTP_HOST and the rest,
RESEND_API_KEY, RESEND_FROM, ADMIN_EMAIL): used until Settings has its
own, never shown. SMTP first; Resend when it's all the host has, or when
SMTP fails."""
import pytest

from soloblog import cache
from soloblog import config
from soloblog import mail
from soloblog import settings
from soloblog.db import get_db

KEYS = ("email_provider", "email_api_key", "email_api_from", "admin_email", "smtp_provider", "smtp_host",
        "smtp_port", "smtp_user", "smtp_password", "smtp_from")
SMTP_SECRET = "smtp-hostsecret-6789"
SECRET = "re_hostsecret_12345"


@pytest.fixture
def host(monkeypatch):
    """A site that has saved none of the four, on a host that sets them."""
    db = get_db()
    before = {r["key"]: r["value"] for r in db.execute("SELECT key, value FROM settings")
              if r["key"] in KEYS}
    db.execute(f"DELETE FROM settings WHERE key IN ({','.join('?' * len(KEYS))})", KEYS)  # noqa: S608 - fixed table names
    db.commit()
    cache.bump()
    monkeypatch.setattr(config, "RESEND_API_KEY", SECRET)
    monkeypatch.setattr(config, "RESEND_FROM", "hello@host.example")
    monkeypatch.setattr(config, "ADMIN_EMAIL", "owner@host.example")
    for name in ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM"):
        monkeypatch.setattr(config, name, "")
    cache.bump()
    yield
    db.execute(f"DELETE FROM settings WHERE key IN ({','.join('?' * len(KEYS))})", KEYS)  # noqa: S608 - fixed table names
    db.commit()
    settings.set_many(before)


def test_the_host_fills_in_what_settings_has_not_set(host):
    assert mail.can_send() and settings.get("email_provider") == "api"
    assert settings.get("email_api_key") == SECRET
    assert settings.get("email_api_from") == "hello@host.example"
    assert settings.get("admin_email") == "owner@host.example"
    assert settings.get_all()["email_provider"] == "api"
    assert settings.on_host("email_api_key") and settings.on_host("admin_email")


def test_settings_win_over_the_host(host):
    settings.set_many({"email_api_key": "re_mine", "email_api_from": "me@mine.example",
                       "admin_email": "me@mine.example"})
    assert settings.get("email_api_key") == "re_mine"
    assert settings.get("email_api_from") == "me@mine.example"
    assert settings.get("admin_email") == "me@mine.example"
    assert not settings.on_host("email_api_key") and not settings.on_host("admin_email")


def test_choosing_nothing_on_purpose_stays_off(host):
    settings.set_many({"email_provider": ""})
    assert settings.get("email_provider") == "" and not mail.can_send()
    settings.set_many({"email_provider": "smtp"})
    assert settings.get("email_provider") == "smtp"


def test_without_a_host_setting_nothing_changes(host, monkeypatch):
    monkeypatch.setattr(config, "RESEND_API_KEY", "")
    monkeypatch.setattr(config, "RESEND_FROM", "")
    monkeypatch.setattr(config, "ADMIN_EMAIL", "")
    cache.bump()
    assert not mail.can_send() and settings.get("admin_email") == ""


def test_the_host_key_is_sent_with_the_email(host, monkeypatch):
    seen = {}

    def fake(req, timeout):
        seen["auth"] = req.headers.get("Authorization")
        return None
    monkeypatch.setattr(mail.netguard, "open_url", fake)
    assert mail.send_email("reader@example.org", "Hi", "Body")
    assert seen["auth"] == f"Bearer {SECRET}"


def test_the_host_key_is_in_no_page(host, admin):
    for tab in ("email", "integrations", "backup", "name", "members", "newsletter"):
        page = admin.get(f"/admin/settings?tab={tab}").text
        assert SECRET not in page, tab
    page = admin.get("/admin/settings?tab=email").text
    assert "Set on your host" in page
    for path in ("/admin/health", "/admin/welcome", "/admin"):
        assert SECRET not in admin.get(path).text, path
    assert "RESEND_API_KEY" in admin.get("/admin/settings?tab=integrations").text


def test_saving_the_email_page_does_not_copy_the_host_key(host, admin):
    admin.post("/admin/settings/email", data={
        "declared_fields": "email_provider,email_api_key,email_api_from", "email_provider": "api",
        "email_api_key": "", "email_api_from": ""})
    assert settings.stored("email_api_key") == "" and settings.get("email_api_key") == SECRET


@pytest.fixture
def smtp_host(host, monkeypatch):
    """The same host, with an SMTP server named as well."""
    monkeypatch.setattr(config, "SMTP_HOST", "smtp.host.example")
    monkeypatch.setattr(config, "SMTP_PORT", "465")
    monkeypatch.setattr(config, "SMTP_USER", "owner@host.example")
    monkeypatch.setattr(config, "SMTP_PASSWORD", SMTP_SECRET)
    monkeypatch.setattr(config, "SMTP_FROM", "owner@host.example")
    cache.bump()


def test_smtp_on_the_host_comes_first(smtp_host):
    assert settings.get("email_provider") == "smtp" and mail.can_send()
    assert mail.smtp_server() == ("smtp.host.example", 465, "owner@host.example")
    assert settings.get("smtp_password") == SMTP_SECRET and settings.on_host("smtp_password")
    # a server saved in Settings wins, port and all
    settings.set_many({"smtp_host": "smtp.mine.example", "smtp_port": "587"})
    assert mail.smtp_server()[:2] == ("smtp.mine.example", 587)


def test_when_smtp_fails_resend_takes_it(smtp_host, monkeypatch):
    sent = []
    monkeypatch.setattr(mail, "_send_smtp", lambda *a: sent.append("smtp") or False)
    monkeypatch.setattr(mail, "_send_api", lambda *a: sent.append("api") or True)
    assert mail.send_email("reader@example.org", "Hi", "Body") and sent == ["smtp", "api"]
    # without a Resend key, a failure is a failure
    monkeypatch.setattr(config, "RESEND_API_KEY", "")
    cache.bump()
    sent.clear()
    assert not mail.send_email("reader@example.org", "Hi", "Body") and sent == ["smtp"]


def test_the_host_smtp_password_is_in_no_page(smtp_host, admin):
    for tab in ("email", "integrations"):
        assert SMTP_SECRET not in admin.get(f"/admin/settings?tab={tab}").text, tab
    assert "SMTP_HOST" in admin.get("/admin/settings?tab=integrations").text
