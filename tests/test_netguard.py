import http.client
import http.server
import pathlib
import re
import socket
import threading
import urllib.request
import pytest

from soloblog import netguard

SOURCE = pathlib.Path(netguard.__file__).parent


@pytest.fixture
def inside():
    """A server on this machine, as something on the site's own network
    would be. Yields (port, the paths asked for)."""
    asked = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            asked.append(self.path)
            self.send_response(200)
            self.send_header("Content-Length", "6")
            self.end_headers()
            self.wfile.write(b"secret")

        def log_message(self, *a):
            pass
    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server.server_port, asked
    server.shutdown()
    server.server_close()


def _answers(monkeypatch, *addresses):
    """The name resolves to each address in turn, then the last for good."""
    left = list(addresses)
    asked = []

    def lookup(host, port, *a, **kw):
        asked.append(host)
        address = left.pop(0) if len(left) > 1 else left[0]
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port))]
    monkeypatch.setattr(socket, "getaddrinfo", lookup)
    return asked


def test_every_request_goes_through_netguard():
    # urlopen opens file:// and connects to any address; only the update
    # hook, which the admin sets for their own host, may use it
    direct = [p.name for p in sorted(SOURCE.rglob("*.py"))
              if p.name not in ("netguard.py", "updates.py") and re.search(r"\burlopen\b", p.read_text())]
    assert direct == []


def test_a_name_that_answers_differently_the_second_time(inside, monkeypatch):
    # DNS rebinding: a public address when it's checked, this machine
    # when it's connected to
    port, asked = inside
    _answers(monkeypatch, "93.184.216.34", "127.0.0.1")
    with pytest.raises(netguard.PrivateAddress):
        netguard.open_url(f"http://rebind.example:{port}/admin", timeout=3)
    assert asked == []


def test_it_connects_to_the_address_it_checked(monkeypatch):
    looked_up = _answers(monkeypatch, "93.184.216.34")
    connected = []

    class Sock:
        def __init__(self, *a):
            pass

        def settimeout(self, t):
            pass

        def connect(self, sockaddr):
            connected.append(sockaddr)
            raise ConnectionRefusedError("far enough")

        def close(self):
            pass
    monkeypatch.setattr(socket, "socket", Sock)
    with pytest.raises(OSError):
        netguard.open_url("http://rebind.example/", timeout=3)
    # the number, not the name - and no lookup after the one for the connection
    assert connected == [("93.184.216.34", 80)]
    assert looked_up == ["rebind.example", "rebind.example"]


def test_a_redirect_inward_is_refused_on_the_way(inside, monkeypatch):
    port, asked = inside

    class Outside(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(302)
            self.send_header("Location", f"http://127.0.0.1:{port}/admin")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *a):
            pass
    outside = http.server.HTTPServer(("127.0.0.1", 0), Outside)
    threading.Thread(target=outside.serve_forever, daemon=True).start()
    try:
        # private_ok reaches the admin's own server, and follows it anywhere http(s)
        with netguard.open_url(f"http://127.0.0.1:{outside.server_port}/", timeout=3, private_ok=True) as resp:
            assert resp.read() == b"secret"
        assert asked == ["/admin"]
        # without it, not even the first address
        with pytest.raises(netguard.PrivateAddress):
            netguard.open_url(f"http://127.0.0.1:{outside.server_port}/", timeout=3)
    finally:
        outside.shutdown()
        outside.server_close()


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://example.com/x", "gopher://127.0.0.1:6379/_x", "http:///x"])
def test_only_http_even_for_the_admins_own_server(url):
    with pytest.raises(netguard.Blocked):
        netguard.open_url(url, private_ok=True)
    with pytest.raises(netguard.Blocked):
        netguard.open_url(url)


def test_through_a_proxy_the_check_still_runs(monkeypatch):
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("http_proxy", "http://127.0.0.1:9")
    with pytest.raises(netguard.PrivateAddress):
        netguard.open_url("http://127.0.0.1/", timeout=1)


STOCK = {"images.pexels.com", "cdn.pixabay.com"}
WITH_INTERNAL = STOCK | {"internal.pexels.example"}


@pytest.fixture
def stock_site(monkeypatch):
    """https to the allowed names, answered by a plain server on this
    machine (no certificate to make). Every name resolves publicly,
    except internal.pexels.example."""
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            where = {"/hop": "https://cdn.pixabay.com/ok", "/off": "https://evil.example/ok",
                     "/plain": "http://images.pexels.com/ok", "/inward": "https://internal.pexels.example/ok"}
            if self.path in where:
                self.send_response(302)
                self.send_header("Location", where[self.path])
                self.send_header("Content-Length", "0")
            else:
                self.send_response(200)
                self.send_header("Content-Length", "5")
            self.end_headers()
            if self.path == "/ok":
                self.wfile.write(b"photo")

        def log_message(self, *a):
            pass
    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    class Local(netguard._CheckedHTTPSHandler):
        def https_open(self, req):
            return self.do_open(Conn, req)

    class Conn(http.client.HTTPConnection):
        def connect(self):
            self.sock = socket.create_connection(("127.0.0.1", server.server_port), timeout=self.timeout)
    monkeypatch.setattr(netguard, "_CheckedHTTPSHandler", Local)

    real = socket.getaddrinfo

    def lookup(host, port, *a, **kw):
        if host == "127.0.0.1":
            return real(host, port, *a, **kw)
        address = "127.0.0.1" if host == "internal.pexels.example" else "93.184.216.34"
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port))]
    monkeypatch.setattr(socket, "getaddrinfo", lookup)
    yield
    server.shutdown()
    server.server_close()


def test_hosts_allows_an_allowed_host(stock_site):
    with netguard.open_url("https://images.pexels.com/ok", timeout=3, hosts=STOCK) as resp:
        assert resp.read() == b"photo"


def test_hosts_allows_a_redirect_to_another_allowed_host(stock_site):
    with netguard.open_url("https://images.pexels.com/hop", timeout=3, hosts=STOCK) as resp:
        assert resp.read() == b"photo"


@pytest.mark.parametrize("url", ["https://evil.example/ok", "http://images.pexels.com/ok"])
def test_hosts_refuses_a_host_off_the_list_and_plain_http(stock_site, url):
    with pytest.raises(netguard.Blocked):
        netguard.open_url(url, timeout=3, hosts=STOCK)


@pytest.mark.parametrize("path", ["off", "plain"])
def test_hosts_refuses_a_redirect_off_the_list_or_down_to_http(stock_site, path):
    with pytest.raises(netguard.Blocked):
        netguard.open_url(f"https://images.pexels.com/{path}", timeout=3, hosts=STOCK)


def test_hosts_still_checks_the_address_first_and_on_a_redirect(stock_site):
    with pytest.raises(netguard.PrivateAddress):
        netguard.open_url("https://internal.pexels.example/ok", timeout=3, hosts=WITH_INTERNAL)
    with pytest.raises(netguard.PrivateAddress):
        netguard.open_url("https://images.pexels.com/inward", timeout=3, hosts=WITH_INTERNAL)


def test_without_hosts_any_public_name_and_redirect_still_work(stock_site, monkeypatch):
    monkeypatch.setattr(netguard, "_opener", urllib.request.build_opener(
        urllib.request.ProxyHandler({}), netguard._CheckedHTTPSHandler, netguard._CheckedRedirects))
    with netguard.open_url("https://evil.example/ok", timeout=3) as resp:
        assert resp.read() == b"photo"
    with netguard.open_url("https://images.pexels.com/off", timeout=3) as resp:
        assert resp.read() == b"photo"


def test_stock_download_only_takes_the_allowed_hosts(stock_site):
    from soloblog import stock
    assert stock.download("https://images.pexels.com/ok") == b"photo"
    for url in ("https://evil.example/ok", "http://images.pexels.com/ok", "https://images.pexels.com/off"):
        with pytest.raises(ValueError):
            stock.download(url)
