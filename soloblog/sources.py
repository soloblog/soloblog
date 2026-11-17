import re
from urllib.parse import parse_qs, urlsplit

from soloblog.db import get_db

# Where readers come from, for Stats: the site that sent them (a link's
# utm_source if it has one), by name and per day. Nothing else is kept -
# not the full address, not who the reader is - and a visit with no
# referrer (typed in, a bookmark, many apps) isn't counted as a source.

# the start of a host (without www.) -> the name people know it by
KNOWN = [
    ("google.", "Google"), ("bing.com", "Bing"), ("duckduckgo.com", "DuckDuckGo"),
    ("search.brave.com", "Brave Search"), ("ecosia.org", "Ecosia"), ("search.yahoo.com", "Yahoo"),
    ("yandex.", "Yandex"), ("baidu.com", "Baidu"), ("kagi.com", "Kagi"),
    ("t.co", "X"), ("x.com", "X"), ("twitter.com", "X"),
    ("facebook.com", "Facebook"), ("l.facebook.com", "Facebook"), ("m.facebook.com", "Facebook"),
    ("lm.facebook.com", "Facebook"), ("instagram.com", "Instagram"), ("l.instagram.com", "Instagram"),
    ("threads.net", "Threads"), ("bsky.app", "Bluesky"), ("linkedin.com", "LinkedIn"), ("lnkd.in", "LinkedIn"),
    ("reddit.com", "Reddit"), ("old.reddit.com", "Reddit"), ("out.reddit.com", "Reddit"),
    ("news.ycombinator.com", "Hacker News"), ("lobste.rs", "Lobsters"), ("youtube.com", "YouTube"),
    ("pinterest.", "Pinterest"), ("github.com", "GitHub"), ("chatgpt.com", "ChatGPT"),
    ("perplexity.ai", "Perplexity"), ("feedly.com", "Feedly"), ("inoreader.com", "Inoreader"),
]


def name(referer: str, query: str = "", own_host: str = "") -> str:
    """The source to count, or "" for none."""
    utm = parse_qs(query or "").get("utm_source", [""])[0].strip()
    if utm:
        return re.sub(r"[^\w .-]", "", utm)[:60]
    host = (urlsplit(referer or "").hostname or "").lower()
    host = host[4:] if host.startswith("www.") else host
    if not host or host == own_host.lower().removeprefix("www."):
        return ""
    for start, label in KNOWN:
        if host == start or (start.endswith(".") and host.startswith(start)) or host.endswith("." + start):
            return label
    return host[:60]


def count(source: str, day: str):
    if not source:
        return
    db = get_db()
    db.execute("INSERT INTO sources_daily (day, source, views) VALUES (?, ?, 1) "
               "ON CONFLICT(day, source) DO UPDATE SET views = views + 1", (day, source))
    db.commit()


def top(since_day: str, limit: int = 10) -> list:
    """[(source, views)] since a day, most first."""
    return [(r["source"], r["n"]) for r in get_db().execute(
        "SELECT source, SUM(views) AS n FROM sources_daily WHERE day >= ? GROUP BY source ORDER BY n DESC, source "
        "LIMIT ?", (since_day, limit))]
