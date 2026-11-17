import json

from soloblog import passkeys


def test_registration_options_need_login(client):
    assert client.post("/admin/passkeys/options", headers={"Sec-Fetch-Mode": "same-origin"}).status_code == 401


def test_registration_options(admin):
    r = admin.post("/admin/passkeys/options")
    opts = json.loads(r.text)
    assert opts["rp"]["id"] == "testserver"
    assert opts["authenticatorSelection"]["residentKey"] == "required"
    assert opts["challenge"] and opts["user"]["id"]


def test_bad_registration_is_refused_and_challenge_used_up(admin):
    admin.post("/admin/passkeys/options")
    r = admin.post("/admin/passkeys/register", json={"name": "x", "credential": {"id": "abc", "response": {}}})
    assert r.json()["error"]
    # the challenge went with that attempt - a second try needs new options
    r = admin.post("/admin/passkeys/register", json={"name": "x", "credential": {"id": "abc", "response": {}}})
    assert "too long" in r.json()["error"]
    assert passkeys.count() == 0


def test_login_verify_refuses_unknown_credentials(client):
    opts = json.loads(client.post("/login/passkey/options").text)
    assert opts["rpId"] == "testserver" and opts["challenge"]
    r = client.post("/login/passkey/verify", json={"id": "nope", "response": {}})
    assert r.status_code == 400
    assert client.get("/admin/posts").headers["location"] == "/login"


def test_login_page_offers_passkeys_only_when_one_exists(client):
    assert "Log in with a passkey" not in client.get("/login").text


class _Req:
    def __init__(self, host, scheme="http", headers=None):
        from starlette.datastructures import URL
        self.url = URL(f"{scheme}://{host}/")
        self.headers = {"host": host, **(headers or {})}


def test_relying_party_follows_the_real_origin():
    assert passkeys.relying_party(_Req("localhost:5001")) == ("localhost", ["http://localhost:5001"])
    # behind a TLS-terminating proxy the app sees http, the browser https
    rp, origins = passkeys.relying_party(_Req("blog.example.com", headers={"x-forwarded-proto": "https"}))
    assert rp == "blog.example.com" and origins == ["https://blog.example.com"]
