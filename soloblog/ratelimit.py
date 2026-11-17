import ipaddress
import os
import time
from datetime import datetime, timedelta
from soloblog.tz import utcnow
from soloblog.db import get_db


# rows older than any window (the longest is a day) - cleared now and then
KEEP_DAYS = 2
_cleared = 0.0


def _who(identifier: str) -> str:
    """An IPv6 address counts as its /64 - the block a home line or a
    phone is given whole. Counted one by one, anyone on IPv6 had millions
    of addresses to guess from, each with its own limit."""
    if not identifier.startswith("ip:") or ":" not in identifier[3:]:
        return identifier
    try:
        address = ipaddress.ip_address(identifier[3:].split("%")[0])
    except ValueError:
        return identifier
    if address.version == 4:
        return identifier
    if address.ipv4_mapped:
        return f"ip:{address.ipv4_mapped}"
    return f"ip:{ipaddress.ip_network((address, 64), strict=False).network_address}/64"


def hit(identifier: str, bucket: str, limit: int, window_minutes: int) -> bool:
    """Returns True if under the limit (and records the hit), False if
    the caller should be blocked. identifier is usually the ip."""
    global _cleared
    db = get_db()
    now = utcnow()
    who = _who(identifier)
    cutoff = (now - timedelta(minutes=window_minutes)).isoformat()
    # counted and recorded in one statement: counted first and recorded
    # after, requests arriving together all saw room and all got through
    added = db.execute(
        "INSERT INTO rate_hits (identifier, bucket, created_at) SELECT ?, ?, ? WHERE "
        "(SELECT COUNT(*) FROM rate_hits WHERE identifier=? AND bucket=? AND created_at > ?) < ?",
        (who, bucket, now.isoformat(), who, bucket, cutoff, limit)).rowcount
    db.commit()
    if time.monotonic() - _cleared > 3600:
        _cleared = time.monotonic()
        db.execute("DELETE FROM rate_hits WHERE created_at <= ?", ((now - timedelta(days=KEEP_DAYS)).isoformat(),))
        db.commit()
    return added == 1


def take_back(identifier: str, bucket: str):
    """The last try didn't count after all - a sign-in that worked. Only
    failed ones should use up the limit (OWASP): an owner signing in on
    several devices in a row was locked out by their own successes."""
    db = get_db()
    who = _who(identifier)
    db.execute("DELETE FROM rate_hits WHERE id = (SELECT MAX(id) FROM rate_hits WHERE identifier=? AND bucket=?)",
               (who, bucket))
    db.commit()


def count(identifier: str, bucket: str, window_minutes: int) -> int:
    """How many tries are counted in the window."""
    return get_db().execute(
        "SELECT COUNT(*) AS n FROM rate_hits WHERE identifier=? AND bucket=? AND created_at > ?",
        (_who(identifier), bucket, (utcnow() - timedelta(minutes=window_minutes)).isoformat())).fetchone()["n"]


def wait_minutes(identifier: str, bucket: str, window_minutes: int) -> int:
    """How long until the oldest counted try runs out and another is
    allowed - for "Try again in 12 minutes" rather than "a few"."""
    oldest = get_db().execute(
        "SELECT MIN(created_at) AS t FROM rate_hits WHERE identifier=? AND bucket=? AND created_at > ?",
        (_who(identifier), bucket, (utcnow() - timedelta(minutes=window_minutes)).isoformat())).fetchone()["t"]
    if not oldest:
        return 1
    left = datetime.fromisoformat(oldest) + timedelta(minutes=window_minutes) - utcnow()
    return max(1, -(-int(left.total_seconds()) // 60))


def client_ip(request) -> str:
    """The visitor's address behind a reverse proxy (Fly.io, nginx,
    Caddy) - request.client is the proxy's, the same for everyone.

    The *last* X-Forwarded-For entry: the proxy appends the address it
    saw to whatever the visitor sent, so the first entry is whatever
    the visitor claims - trusting it would let anyone dodge the login
    and comment limits. Assumes one proxy in front, as these hosts are."""
    from soloblog import config
    peer = request.client.host if request.client else ""
    # TRUSTED_PROXY names who may speak for a visitor; anyone else's
    # headers are the visitor's own words, and the caller is the visitor
    if config.TRUSTED_PROXY and not _trusted(peer, config.TRUSTED_PROXY):
        return peer or "unknown"
    if config.CLIENT_IP_HEADER:
        # a proxy or CDN that says who the visitor is (CF-Connecting-IP...)
        named = request.headers.get(config.CLIENT_IP_HEADER, "").split(",")[0].strip()
        if named:
            return named
    # on Fly.io the last X-Forwarded-For entry is Fly's own edge - the
    # site's shared address, the same for every visitor, so one person's
    # wrong passwords locked everyone out. Fly says who it is in
    # Fly-Client-IP, which it sets itself (a visitor's own is replaced)
    listed = bool(config.TRUSTED_PROXY)
    if os.getenv("FLY_APP_NAME") and (listed or not _public(peer)):
        fly = request.headers.get("fly-client-ip", "").strip()
        if fly:
            return fly
    fwd = request.headers.get("x-forwarded-for")
    # only a proxy on a private network (Fly's, Docker's, nginx on the same
    # machine) is believed - reached straight from the internet, the header
    # is whatever the visitor wrote, a new address for every guess
    if fwd and (listed or not _public(peer)):
        return fwd.split(",")[-1].strip()
    return peer or "unknown"


def _trusted(peer: str, wanted: str) -> bool:
    """Is the caller one of TRUSTED_PROXY's addresses or networks? "none"
    and anything that isn't an address match nobody - a mistyped setting
    must not turn into trusting everyone."""
    try:
        address = ipaddress.ip_address(peer)
    except ValueError:
        return False
    if getattr(address, "ipv4_mapped", None):
        address = address.ipv4_mapped
    for part in wanted.split(","):
        try:
            if address in ipaddress.ip_network(part.strip(), strict=False):
                return True
        except (ValueError, TypeError):
            continue
    return False


def _public(address: str) -> bool:
    try:
        return ipaddress.ip_address(address).is_global
    except ValueError:  # a socket, or the test client - not the internet
        return False
