import threading
from datetime import timedelta

from soloblog import ratelimit
from soloblog.db import get_db
from soloblog.tz import utcnow


def _tries(address, n, bucket="login", limit=5):
    return [ratelimit.hit(f"ip:{address}", bucket, limit=limit, window_minutes=15) for _ in range(n)]


def test_an_ipv6_line_is_one_caller(app):
    # a home line on IPv6 has a whole /64: a new address for every guess
    assert all(_tries("2001:db8:1:2::1", 3))
    assert _tries("2001:db8:1:2:aaaa:bbbb:cccc:dddd", 3) == [True, True, False]
    assert not ratelimit.hit("ip:2001:db8:1:2::ffff", "login", limit=5, window_minutes=15)
    # the line next door has its own
    assert all(_tries("2001:db8:1:3::1", 5))
    # and so does every IPv4 address, as before
    assert all(_tries("192.0.2.1", 5)) and all(_tries("192.0.2.2", 5))
    # an IPv4 address written the IPv6 way is that IPv4 address
    assert not ratelimit.hit("ip:::ffff:192.0.2.1", "login", limit=5, window_minutes=15)


def test_taking_back_and_waiting_use_the_same_line(app):
    assert all(_tries("2001:db8:9:9::1", 5))
    assert ratelimit.wait_minutes("ip:2001:db8:9:9::2", "login", 15) == 15
    ratelimit.take_back("ip:2001:db8:9:9::3", "login")
    assert ratelimit.hit("ip:2001:db8:9:9::4", "login", limit=5, window_minutes=15)


def test_what_isnt_an_address_is_left_alone(app):
    for who in ("member:ann@example.com", "ip:unknown", "key:12", "ip:not:an:address"):
        assert ratelimit._who(who) == who
    assert ratelimit._who("ip:fe80::1%eth0") == "ip:fe80::/64"


def test_requests_arriving_together_share_one_limit(app):
    # counted first and recorded after, all twenty saw room
    passed = []
    start = threading.Barrier(20)

    def guess():
        start.wait()
        passed.append(ratelimit.hit("ip:198.51.100.77", "together", limit=5, window_minutes=15))
    threads = [threading.Thread(target=guess) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(passed) == [False] * 15 + [True] * 5


def test_old_rows_are_cleared(app, monkeypatch):
    db = get_db()
    old = (utcnow() - timedelta(days=3)).isoformat()
    db.execute("INSERT INTO rate_hits (identifier, bucket, created_at) VALUES ('ip:192.0.2.9', 'never-again', ?)", (old,))
    db.commit()
    monkeypatch.setattr(ratelimit, "_cleared", 0.0)
    monkeypatch.setattr(ratelimit.time, "monotonic", lambda: 10_000.0)
    assert ratelimit.hit("ip:192.0.2.1", "login", limit=5, window_minutes=15)
    assert db.execute("SELECT COUNT(*) FROM rate_hits WHERE bucket='never-again'").fetchone()[0] == 0


def test_only_a_trusted_proxy_may_say_who_the_visitor_is(monkeypatch):
    """Reached straight from the internet, or through Docker with no proxy
    in front, X-Forwarded-For is whatever the visitor wrote: a new address
    for every guess. TRUSTED_PROXY says whose word counts."""
    from soloblog import config

    class Peer:
        def __init__(self, host):
            self.host = host

    class Req:
        def __init__(self, peer, **headers):
            self.client = Peer(peer)
            self.headers = headers

    faked = {"x-forwarded-for": "198.51.100.7", "cf-connecting-ip": "198.51.100.8"}
    # unset, as before: a caller on a private network is believed
    assert ratelimit.client_ip(Req("172.17.0.1", **faked)) == "198.51.100.7"
    # none: nobody is - every guess counts against the caller
    monkeypatch.setattr(config, "TRUSTED_PROXY", "none")
    monkeypatch.setattr(config, "CLIENT_IP_HEADER", "cf-connecting-ip")
    assert ratelimit.client_ip(Req("172.17.0.1", **faked)) == "172.17.0.1"
    assert ratelimit.client_ip(Req("203.0.113.5", **faked)) == "203.0.113.5"
    # the proxy's own address or network: only it
    monkeypatch.setattr(config, "TRUSTED_PROXY", "10.0.0.2, 192.168.5.0/24, 2001:db8::/32")
    assert ratelimit.client_ip(Req("10.0.0.2", **faked)) == "198.51.100.8"
    assert ratelimit.client_ip(Req("192.168.5.77", **faked)) == "198.51.100.8"
    assert ratelimit.client_ip(Req("::ffff:10.0.0.2", **faked)) == "198.51.100.8"
    assert ratelimit.client_ip(Req("2001:db8::9", **faked)) == "198.51.100.8"
    assert ratelimit.client_ip(Req("10.0.0.3", **faked)) == "10.0.0.3"
    monkeypatch.setattr(config, "CLIENT_IP_HEADER", "")
    assert ratelimit.client_ip(Req("10.0.0.2", **faked)) == "198.51.100.7"
    # mistyped: trusts nobody, never everybody, and never an error
    monkeypatch.setattr(config, "TRUSTED_PROXY", "yes please, 999.1.1.1/99")
    assert ratelimit.client_ip(Req("172.17.0.1", **faked)) == "172.17.0.1"
    assert ratelimit.client_ip(Req("testclient", **faked)) == "testclient"
