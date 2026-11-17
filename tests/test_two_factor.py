import re
import time

from starlette.testclient import TestClient

from soloblog import totp
from conftest import PASSWORD


def _current_code(secret):
    return totp._code_at(secret, int(time.time() // totp.STEP))


def test_rfc6238_vector():
    import base64
    secret = base64.b32encode(b"12345678901234567890").decode()
    # RFC 6238's SHA1 vector at T=59 is 94287082; six digits keep the last six
    assert totp.matching_step(secret, "287082", now=59) == 1
    assert totp.matching_step(secret, "000000", now=59) is None


def test_two_factor_login_flow(app, admin):
    r = admin.get("/admin/2fa/setup")
    secret = re.search(r"<code[^>]*>([A-Z2-7 ]+)</code>", r.text).group(1).replace(" ", "")
    assert "<svg" in r.text  # the QR code

    r = admin.post("/admin/2fa/enable", data={"code": "000000"})
    assert "didn&#x27;t match" in r.text or "didn't match" in r.text
    r = admin.post("/admin/2fa/enable", data={"code": _current_code(secret)})
    codes = re.findall(r"<code[^>]*>([0-9a-f]{5}-[0-9a-f]{5})</code>", r.text)
    assert len(codes) == 10 and totp.is_enabled()

    try:
        # a correct password alone no longer logs in
        c = TestClient(app, follow_redirects=False)
        r = c.post("/login", data={"password": PASSWORD})
        assert r.headers["location"] == "/login/code"
        assert c.get("/admin/posts").headers["location"] == "/login"
        assert "didn" in c.post("/login/code", data={"code": "123456"}).text
        r = c.post("/login/code", data={"code": _current_code(secret)})
        assert r.status_code == 303 and r.headers["location"] == "/"
        assert c.get("/admin/posts").status_code == 200

        # a recovery code works once
        c2 = TestClient(app, follow_redirects=False)
        c2.post("/login", data={"password": PASSWORD})
        assert c2.post("/login/code", data={"code": codes[0]}).headers.get("location") == "/"
        assert not totp.check(codes[0])
        assert totp.recovery_codes_left() == 9

        # the code step can't skip the password step
        c3 = TestClient(app, follow_redirects=False)
        assert c3.post("/login/code", data={"code": codes[1]}).headers["location"] == "/login"
    finally:
        r = admin.post("/admin/2fa/disable", data={"password": "wrong"})
        assert "Wrong password" in r.text and totp.is_enabled()
        admin.post("/admin/2fa/disable", data={"password": PASSWORD})
        assert not totp.is_enabled()


def test_same_code_cannot_be_used_twice():
    secret = totp.new_secret()
    totp.enable(secret)
    try:
        code = _current_code(secret)
        assert totp.check(code)
        assert not totp.check(code)
    finally:
        totp.disable()
