import contextlib
import json
import logging
import os
import re
import threading
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from soloblog.tz import utcnow

from soloblog import config
from soloblog import netguard
from soloblog import posts
from soloblog import settings
from soloblog.render import render_post

log = logging.getLogger(__name__)

# Finds broken links in your posts: other posts that no longer exist,
# images missing from uploads, and outside pages that answer with an
# error or not at all. Runs in a background thread (a few dozen outside
# requests can take a while); the Stats page polls for the result.

# whole attributes only - not data-embed-src, an embed's own player url
_HREF = re.compile(r'(?<=\s)(?:href|src)="([^"#]+)')
TIMEOUT = 8
UA = {"User-Agent": "Mozilla/5.0 (compatible; Soloblog link checker)"}

_running = False
_lock = threading.Lock()


def state() -> dict:
    last = {"checked_at": "", "broken": [], "total": 0}
    with contextlib.suppress(ValueError):
        last.update(json.loads(settings.get("linkcheck_last") or "{}"))
    return {**last, "running": _running}


def _links_by_post():
    """{url: [(slug, title), ...]} across every post, drafts included."""
    found = {}
    for p in posts.list_posts(include_drafts=True):
        html, _ = render_post(posts.load_post_body(p["slug"]))
        for url in set(_HREF.findall(html)):
            if url.startswith(("http://", "https://", "/post/", "/uploads/")):
                found.setdefault(url, []).append((p["slug"], p["title"]))
    return found


def check_url(url: str) -> str:
    """"" if the link works, else a short reason."""
    from html import unescape
    url = unescape(url)
    if url.startswith("/post/"):
        slug = url[len("/post/"):].split("?")[0].strip("/")
        return "" if posts.get_post(slug) or posts.find_redirect(slug) else "No such post"
    if url.startswith("/uploads/"):
        name = url[len("/uploads/"):]
        return "" if os.path.exists(os.path.join(config.uploads_dir(), name)) else "Image missing"
    for method in ("HEAD", "GET"):  # some servers refuse HEAD
        try:
            req = urllib.request.Request(url, method=method, headers=UA)  # noqa: S310 - opened through netguard
            with netguard.open_url(req, timeout=TIMEOUT):
                return ""
        except netguard.PrivateAddress:
            # a link into a private network isn't ours to probe
            return ""
        except urllib.error.HTTPError as e:
            if method == "HEAD" and e.code in (403, 405, 501):
                continue
            return f"HTTP {e.code}"
        except Exception as e:  # anything a server can answer with - the reason is the result, shown on Stats
            reason = getattr(e, "reason", e)
            return f"Unreachable ({str(reason)[:60]})"
    return ""


def _run():
    global _running
    try:
        links = _links_by_post()
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = dict(zip(links, pool.map(check_url, links)))
        broken = sorted(
            [{"url": url, "reason": results[url], "posts": links[url]} for url in links if results[url]],
            key=lambda b: b["posts"][0][1].lower()
        )
        settings.set_many({"linkcheck_last": json.dumps(
            {"broken": broken, "total": len(links), "checked_at": utcnow().isoformat()})})
    except Exception:  # a background thread - its traceback would otherwise go only to the console
        log.exception("the broken-link check stopped")
    finally:
        _running = False


def start() -> bool:
    """Starts a check unless one is already running."""
    global _running
    with _lock:
        if _running:
            return False
        _running = True
    threading.Thread(target=_run, daemon=True).start()
    return True
