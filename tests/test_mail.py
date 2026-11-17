"""Sending email (mail.py) through a pretend SMTP server and a pretend
Resend, and the abuse cases: a visitor's "address" that is really a list,
or a name with a line break in it."""
import json
import urllib.request

import pytest

from conftest import save_post
from soloblog import comments
from soloblog import mail
from soloblog import netguard
from soloblog import settings

KEYS = ("site_title", "email_provider", "smtp_host", "smtp_port", "smtp_user", "smtp_password", "smtp_from", "email_api_key",
        "email_api_from", "mail_last_ok_at", "mail_last_failed_at", "mail_last_error")


@pytest.fixture
def keep():
    before = {k: settings.get(k) for k in KEYS}
    yield
    settings.set_many(before)


class Server:
    """Just enough smtplib.SMTP."""
    sent = []

    def __init__(self, host, port, context=None, timeout=None):
        self.host, self.port, self.tls = host, port, context is not None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass

    def starttls(self, context=None):
        self.tls = True

    def login(self, user, password):
        if password != "app-password":
            raise OSError("535 authentication failed")

    def send_message(self, msg):
        assert self.tls, "never in the clear"
        Server.sent.append(msg)


@pytest.fixture
def smtp(keep, monkeypatch):
    Server.sent = []
    monkeypatch.setattr(mail.smtplib, "SMTP", Server)
    monkeypatch.setattr(mail.smtplib, "SMTP_SSL", Server)
    settings.set_many({"email_provider": "smtp", "smtp_host": "smtp.example.net", "smtp_port": "587",
                       "smtp_user": "mira", "smtp_password": "app-password", "smtp_from": "mira@example.com"})
    return Server.sent


def test_smtp(smtp):
    # the site's name as the sender, quoted where it needs to be
    settings.set_many({"site_title": "Mira, writing"})
    assert mail.send_email("reader@example.org", "Hello", "Body text", headers={"Reply-To": "kai@example.org"})
    msg = smtp[0]
    assert (msg["To"], msg["From"], msg["Subject"], msg["Reply-To"]) == \
        ("reader@example.org", '"Mira, writing" <mira@example.com>', "Hello", "kai@example.org")
    assert msg.get_content().strip() == "Body text" and settings.get("mail_last_ok_at")
    settings.set_many({"smtp_port": "465"})
    assert mail.send_email("reader@example.org", "Over 465", "x")


def test_a_failure_is_noted_not_raised(smtp):
    settings.set_many({"smtp_password": "wrong"})
    assert mail.send_email("reader@example.org", "Hello", "x") is False
    assert "authentication failed" in settings.get("mail_last_error")
    assert "app password" in mail.explain(settings.get("mail_last_error"))


def test_what_went_wrong_in_plain_words(admin, smtp, monkeypatch):
    for raw, words in (("[Errno 110] Connection timed out", "block email ports"),
                       ("[Errno 101] Network is unreachable", "Resend works"),
                       ("[SSL: WRONG_VERSION_NUMBER] wrong version number (_ssl.c:1000)", "Try 587"),
                       ("[Errno -2] Name or service not known", "no email server by that name"),
                       ("(553, b'Sender address rejected: not owned by user')", "own address"),
                       ("HTTP Error 403: Forbidden - The example.com domain is not verified.", "domain you've verified"),
                       ("[SSL: CERTIFICATE_VERIFY_FAILED] Hostname mismatch", "certificate is for another name"),
                       ("something new", "something new")):
        assert words in mail.explain(raw), raw
    # the test email says it, beside its button
    settings.set_many({"smtp_password": "wrong", "admin_email": "me@example.com"})
    assert "Couldn't send it: The server didn't accept the username" in admin.post("/admin/email/test").text


def test_resends_reason_is_kept(keep, monkeypatch):
    import io
    import urllib.error

    def refuse(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, io.BytesIO(
            b'{"statusCode":403,"message":"The example.com domain is not verified."}'))
    monkeypatch.setattr(mail.netguard, "open_url", refuse)
    settings.set_many({"email_provider": "api", "email_api_key": "re_test", "email_api_from": "mira@example.com"})
    assert not mail.send_email("reader@example.org", "Hi", "Body")
    assert "domain is not verified" in settings.get("mail_last_error")


def test_a_failed_send_is_logged_with_the_service_and_status(keep, monkeypatch, caplog):
    import io
    import logging
    import urllib.error

    def refuse(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 422, "Unprocessable", {}, io.BytesIO(
            b'{"message":"reader@example.org is not allowed"}'))
    monkeypatch.setattr(mail.netguard, "open_url", refuse)
    settings.set_many({"email_provider": "api", "email_api_key": "re_secret_key", "email_api_from": "mira@example.com"})
    with caplog.at_level(logging.WARNING, logger="soloblog.mail"):
        assert mail.send_email("reader@example.org", "Hi", "Body") is False
    logged = " ".join(r.getMessage() for r in caplog.records)
    assert "Resend" in logged and "HTTP 422" in logged
    assert "reader@example.org" not in logged and "re_secret_key" not in logged


def test_a_refused_recipient_is_logged_without_their_address(smtp, monkeypatch, caplog):
    import logging
    import smtplib

    class Refusing(Server):
        def send_message(self, msg):
            raise smtplib.SMTPRecipientsRefused({"reader@example.org": (550, b"no such user reader@example.org")})
    monkeypatch.setattr(mail.smtplib, "SMTP", Refusing)
    with caplog.at_level(logging.WARNING, logger="soloblog.mail"):
        assert mail.send_email("reader@example.org", "Hello", "x") is False
    logged = " ".join(r.getMessage() for r in caplog.records)
    assert "smtp.example.net" in logged and "550" in logged and "reader@example.org" not in logged


def test_resend(keep, monkeypatch):
    sent = []
    monkeypatch.setattr(mail.netguard, "open_url", lambda req, timeout: sent.append(req))
    settings.set_many({"email_provider": "api", "email_api_key": "re_test", "email_api_from": "mira@example.com"})
    assert mail.send_email("reader@example.org", "Hi", "Body", headers={"List-Unsubscribe": "<https://x.example/u>"})
    body = json.loads(sent[0].data)
    assert body["to"] == ["reader@example.org"] and body["headers"]["List-Unsubscribe"]
    assert body["from"].endswith("<mira@example.com>")
    # one written with its own name stays as it is
    settings.set_many({"email_api_from": "Mira <mira@example.com>"})
    mail.send_email("reader@example.org", "Hi", "Body")
    assert json.loads(sent[1].data)["from"] == "Mira <mira@example.com>"
    assert sent[0].get_header("Authorization") == "Bearer re_test"
    # Resend's firewall refuses Python's default name
    assert sent[0].get_header("User-agent") == "Soloblog"


@pytest.mark.parametrize("to", ["a@example.org, b@example.org", "a@example.org;b@example.org",
                                "a,b@example.org", "Eve <a@example.org>", "a@example.org\nBcc: b@example.org", ""])
def test_one_address_never_a_list(smtp, to):
    assert mail.send_email(to, "Hello", "x") is False and not smtp


def test_a_line_break_cant_add_a_header(smtp):
    assert mail.send_email("reader@example.org", "Message from Eve\r\nBcc: victim@example.org", "x",
                           headers={"Reply-To": "eve@example.org\nBcc: victim@example.org"})
    msg = smtp[0]
    assert msg["Bcc"] is None and "\n" not in msg["Subject"] and msg["Subject"].startswith("Message from Eve Bcc")


def test_comment_with_a_list_for_an_email(admin, client, smtp):
    slug = save_post(admin, title="Spam relay")
    r = client.post(f"/post/{slug}/comment", headers={"HX-Request": "true"},
                    data={"author_name": "V", "email": "a@example.org, b@example.org", "body": "Relay me", "website": ""})
    assert "look like an email address" in r.text and not smtp
    assert not [c for c in comments.list_by_status("pending", per_page=500) if c["body"] == "Relay me"]


def test_contact_name_with_a_line_break(admin, client, smtp):
    before = {k: settings.get(k) for k in ("contact_enabled", "contact_email")}
    settings.set_many({"contact_enabled": "1", "contact_email": "mira@example.com"})
    try:
        r = client.post("/contact", headers={"HX-Request": "true"},
                        data={"name": "Eve\nBcc: victim@example.org", "email": "eve@example.org", "body": "Hi"})
        assert r.status_code == 200 and smtp and smtp[0]["Bcc"] is None
    finally:
        settings.set_many(before)


def test_redirects_to_a_private_address_are_refused():
    # a public page that redirects inward is checked again at each hop
    handler = next(h for h in netguard._opener.handlers if isinstance(h, netguard._CheckedRedirects))
    req = urllib.request.Request("https://example.com/")
    for inward in ("http://127.0.0.1/admin", "http://169.254.169.254/latest/meta-data/", "http://[::1]/",
                   "http://10.0.0.5/", "file:///etc/passwd"):
        with pytest.raises(netguard.Blocked):
            handler.redirect_request(req, None, 302, "Found", {}, inward)


def test_too_big_and_unknown(monkeypatch):
    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def read(self, n):
            return b"x" * n
    monkeypatch.setattr(netguard, "open_url", lambda req, timeout: Resp())
    with pytest.raises(netguard.Blocked, match="too large"):
        netguard.fetch("https://example.com/huge", max_bytes=10)
    monkeypatch.undo()
    with pytest.raises(netguard.Blocked, match="can't find"):
        netguard.check_url("https://no-such-host.invalid/")


def test_a_provider_from_the_list_needs_no_server(smtp, monkeypatch):
    used = []
    monkeypatch.setattr(mail.smtplib, "SMTP", lambda host, port, **kw: used.append((host, port)) or Server(host, port))
    settings.set_many({"smtp_provider": "gmail", "smtp_host": "", "smtp_user": "", "smtp_from": "me@gmail.com"})
    try:
        assert mail.send_email("reader@example.org", "Hello", "x")
        assert used == [("smtp.gmail.com", 587)] and mail.smtp_server()[2] == "me@gmail.com"
        # "Another provider": what's typed
        settings.set_many({"smtp_provider": "", "smtp_host": "smtp.example.net", "smtp_user": "mira"})
        assert mail.smtp_server() == ("smtp.example.net", 587, "mira")
    finally:
        settings.set_many({"smtp_provider": ""})


def test_the_email_page_leads_with_resend_and_lists_providers(admin):
    settings.set_many({"email_provider": "smtp", "smtp_provider": "outlook"})
    try:
        page = admin.get("/admin/settings?tab=email").text
        assert page.index('value="api"') < page.index('value="smtp"') < page.index('name="email_provider" value=""')
        assert "(Recommended)" in page and "app password" in page and 'name="smtp_provider"' in page
        # Outlook: why not, and no fields to fill
        assert "choose Resend above instead" in page
        # a provider that isn't in the list is never kept
        admin.post("/admin/settings/integrations", data={"smtp_provider": "evil", "declared_fields": "smtp_provider"})
        assert settings.get("smtp_provider") == ""
    finally:
        settings.set_many({"email_provider": "", "smtp_provider": ""})


def test_a_test_email_tests_whats_on_screen(admin, smtp):
    settings.set_many({"admin_email": "me@example.com", "smtp_password": "wrong"})
    r = admin.post("/admin/email/test", data={
        "declared_fields": "email_provider,smtp_provider,smtp_host,smtp_port,smtp_user,smtp_password,smtp_from",
        "email_provider": "smtp", "smtp_provider": "", "smtp_host": "smtp.example.net", "smtp_port": "587",
        "smtp_user": "mira", "smtp_password": "app-password", "smtp_from": "mira@example.com"})
    assert "Sent to me@example.com" in r.text and 'data-saved' in r.text
    assert settings.get("smtp_password") == "app-password" and smtp
    # nothing declared (a script, an old page): nothing saved, never wiped
    admin.post("/admin/email/test")
    assert settings.get("smtp_host") == "smtp.example.net"


def test_a_test_from_resend_dev_says_it_reaches_only_you(admin, keep, monkeypatch):
    # the owner's test arrives from Resend's try-out address - so it has to
    # say nobody else's will, or it looks like everything works
    monkeypatch.setattr(mail, "_send_api", lambda *a: True)
    settings.set_many({"admin_email": "me@example.com"})
    fields = {"declared_fields": "email_provider,email_api_key,email_api_from", "email_provider": "api",
              "email_api_key": "re_test", "email_api_from": "onboarding@resend.dev"}
    r = admin.post("/admin/email/test", data=fields)
    assert "reaches only you" in r.text and "text-error" in r.text
    r = admin.post("/admin/email/test", data={**fields, "email_api_from": "hello@mirabakes.com"})
    assert "check your inbox" in r.text and "reaches only you" not in r.text
    # and the screens say so before anyone tries
    assert "not resend.dev" in admin.get("/admin/settings?tab=email").text
