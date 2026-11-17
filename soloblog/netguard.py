import http.client
import ipaddress
import socket
import urllib.parse
import urllib.request

# Every outbound request goes through here (the admin's own update hook
# aside - a test checks). Those the admin sets off - importing a blog's
# images, the link checker, the comment webhook - go only to the public
# internet. Without this, a URL like http://169.254.169.254/ (a cloud
# host's metadata service) or http://localhost:6379/ would be fetched from
# inside the server's own network. Every redirect is checked too.


class Blocked(ValueError):
    pass


class PrivateAddress(Blocked):
    pass


def _public_addresses(host: str, port: int) -> list:
    """Every address host has, as socket.getaddrinfo gives them. Raises
    Blocked when it has none, or when any of them isn't a public one."""
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError) as e:
        raise Blocked(f"can't find {host}") from e
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        if not ip.is_global or ip.is_multicast:
            raise PrivateAddress(f"{host} is a private address")
    return infos


def check_url(url: str, hosts: set | None = None):
    """Raises Blocked unless url is http(s) and every address its host
    resolves to is a public one. With hosts, it must also be https and
    its host one of them."""
    parts = _http_parts(url)
    if hosts is not None and (parts.scheme != "https" or parts.hostname not in hosts):
        raise Blocked("not an allowed address")
    _public_addresses(parts.hostname, parts.port or (443 if parts.scheme == "https" else 80))


def _http_parts(url: str):
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise Blocked("only http and https links")
    return parts


def _connect_checked(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None):
    """socket.create_connection, to an address that was looked up once,
    checked, and then connected to as a number. Looked up again by name
    for the connection, the name could answer differently the second
    time - a public address for the check, 127.0.0.1 for the request
    (DNS rebinding)."""
    host, port = address
    error = None
    for family, kind, proto, _, sockaddr in _public_addresses(host, port):
        sock = None
        try:
            sock = socket.socket(family, kind, proto)
            if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
                sock.settimeout(timeout)
            if source_address:
                sock.bind(source_address)
            sock.connect(sockaddr)
            return sock
        except OSError as e:
            error = e
            if sock is not None:
                sock.close()
    raise error or OSError(f"can't connect to {host}")


# the certificate is still checked against the name: only the socket is
# made here, http.client wraps it with the host it was asked for
class _CheckedHTTP(http.client.HTTPConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._create_connection = _connect_checked


class _CheckedHTTPS(http.client.HTTPSConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._create_connection = _connect_checked


class _CheckedHTTPHandler(urllib.request.HTTPHandler):
    def http_open(self, req):
        return self.do_open(_CheckedHTTP, req)


class _CheckedHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(_CheckedHTTPS, req)


class _CheckedRedirects(urllib.request.HTTPRedirectHandler):
    def __init__(self, hosts: set | None = None):
        self.hosts = hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_url(newurl, self.hosts)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class _HTTPRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _http_parts(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _CheckedHTTPHandler, _CheckedHTTPSHandler,
                                      _CheckedRedirects)
# a server that reaches the internet through a proxy (HTTPS_PROXY): the
# proxy looks the name up and connects, so there's no address of ours to
# hold it to - the check before is all there is
_proxied_opener = urllib.request.build_opener(_CheckedRedirects)
# for an address the admin gave for their own server (private_ok)
_private_opener = urllib.request.build_opener(_HTTPRedirects)


def open_url(request, timeout: float = 10, private_ok: bool = False, hosts: set | None = None):
    """urllib.request.urlopen, for http(s) and public addresses only.
    request is a URL or a urllib.request.Request. private_ok: an address
    the admin typed for a server of their own (a translation server, a
    storage bucket on the home network) - still http(s) only. hosts: only
    these names, over https, and the same for every redirect."""
    url = request.full_url if isinstance(request, urllib.request.Request) else request
    if private_ok:
        _http_parts(url)
        return _private_opener.open(request, timeout=timeout)
    check_url(url, hosts)
    proxied = urllib.request.getproxies() and not urllib.request.proxy_bypass(_http_parts(url).hostname)
    if hosts is not None:
        handlers = [_CheckedRedirects(hosts)]
        if not proxied:
            handlers = [urllib.request.ProxyHandler({}), _CheckedHTTPHandler, _CheckedHTTPSHandler, *handlers]
        return urllib.request.build_opener(*handlers).open(request, timeout=timeout)
    return (_proxied_opener if proxied else _opener).open(request, timeout=timeout)


def fetch(url: str, max_bytes: int = 15 * 1024 * 1024, timeout: float = 15) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Soloblog importer"})  # noqa: S310 - the guard's own opener
    with open_url(req, timeout=timeout) as resp:
        data = resp.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise Blocked("file too large")
    return data
