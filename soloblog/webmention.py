import logging
import queue
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
from soloblog.tz import utcnow

from bs4 import BeautifulSoup

from soloblog import config
from soloblog import netguard
from soloblog import settings
from soloblog.db import get_db

log = logging.getLogger(__name__)

# Webmentions (webmention.net) - how independent sites tell each other
# "I linked to you". Received: another site POSTs source (its page) and
# target (our post); we fetch the source, check it really links here,
# read who wrote it and what kind of mention it is (a reply, a like, a
# repost...) from its microformats, and keep it - replies and mentions
# wait for approval unless that's switched off. Sent: when a post goes
# live or changes, every site it links to that accepts webmentions is
# told. Bridgy (brid.gy) turns Mastodon, Bluesky and other replies into
# webmentions too.

KINDS = {"in-reply-to": "reply", "like-of": "like", "repost-of": "repost", "bookmark-of": "bookmark"}
MAX_BYTES = 1024 * 1024
UA = {"User-Agent": f"Soloblog/{config.VERSION} (webmention)"}


def receiving(s=None) -> bool:
    s = s or settings.get_all()
    return s.get("webmention_receive") == "1"


def sending(s=None) -> bool:
    s = s or settings.get_all()
    return s.get("webmention_send") == "1"


def endpoint_url() -> str:
    return f"{config.BASE_URL}/webmention"


def target_slug(target: str):
    """Our live post a target URL names, else None."""
    from soloblog import posts
    base = config.BASE_URL + "/post/"
    if not target.startswith(base):
        return None
    slug = target[len(base):].split("#")[0].split("?")[0].strip("/")
    row = posts.get_post(slug)
    return slug if row and posts.is_live(row) else None


def _fetch(url: str):
    """(final url, content type, text) - public addresses only."""
    req = urllib.request.Request(url, headers={**UA, "Accept": "text/html, */*;q=0.5"})  # noqa: S310 - opened through netguard
    with netguard.open_url(req, timeout=15) as resp:
        data = resp.read(MAX_BYTES)
        return resp.geturl(), resp.headers.get("Content-Type", ""), resp.headers, data.decode("utf-8", "replace")


def _links_to(soup, text: str, target: str) -> bool:
    bare = target.rstrip("/")
    for tag in soup.find_all(["a", "link", "img", "video", "audio"], href=True) + soup.find_all(src=True):
        href = (tag.get("href") or tag.get("src") or "").split("#")[0].rstrip("/")
        if href == bare:
            return True
    return bare in text  # plain text or JSON sources


def _text(el):
    return re.sub(r"\s+", " ", el.get_text(" ")).strip() if el else ""


def parse(html: str, source: str, target: str) -> dict:
    """What a source page says about us: author, kind, a short excerpt -
    from its h-entry microformats where it has them."""
    soup = BeautifulSoup(html, "html.parser")
    entry = soup.find(class_="h-entry") or soup
    kind = "mention"
    bare = target.rstrip("/")
    for cls, name in KINDS.items():
        for link in entry.find_all(class_=f"u-{cls}"):
            href = (link.get("href") or "").split("#")[0].rstrip("/")
            if href == bare or bare in _text(link):
                kind = name
    author = entry.find(class_="p-author") or entry.find(class_="h-card") or soup.find(class_="h-card")
    name, url, photo = "", "", ""
    if author:
        name = _text(author.find(class_="p-name")) or _text(author)
        link = author if author.name == "a" else author.find(class_="u-url") or author.find("a")
        url = (link.get("href") if link else "") or ""
        img = author.find(class_="u-photo") or author.find("img")
        photo = (img.get("src") if img else "") or ""
    if not name:
        name = urllib.parse.urlsplit(source).hostname or source
    content = entry.find(class_="e-content") or entry.find(class_="p-content") or entry.find(class_="p-summary")
    excerpt = _text(content) if content else _text(entry.find(class_="p-name"))
    published = entry.find(class_="dt-published")
    when = (published.get("datetime") or _text(published)) if published else ""
    from soloblog.render import web_url
    absolute = lambda u: web_url(urllib.parse.urljoin(source, u)) if u else ""  # noqa: E731
    return {"kind": kind, "author_name": name[:120], "author_url": absolute(url)[:500],
            "author_photo": absolute(photo)[:500], "content": excerpt[:600], "published": when[:40]}


def verify(source: str, target: str):
    """Fetches source and stores (or updates, or removes) its mention."""
    slug = target_slug(target)
    if not slug:
        return
    db = get_db()
    try:
        _, ctype, _, text = _fetch(source)
    except urllib.error.HTTPError as e:
        if e.code in (404, 410):  # the page is gone - so is its mention
            db.execute("DELETE FROM webmentions WHERE source=? AND target=?", (source, target))
            db.commit()
        return
    except Exception as e:
        log.warning("couldn't check %s: %s", source, e)
        return
    soup = BeautifulSoup(text, "html.parser") if "html" in ctype or "<" in text[:200] else None
    if not (soup and _links_to(soup, text, target)) and target.rstrip("/") not in text:
        # no longer links here - an update that removed us
        db.execute("DELETE FROM webmentions WHERE source=? AND target=?", (source, target))
        db.commit()
        return
    info = parse(text, source, target) if soup else {"kind": "mention", "author_name": source, "author_url": "",
                                                      "author_photo": "", "content": "", "published": ""}
    auto = info["kind"] in ("like", "repost", "bookmark") or settings.get("webmention_moderate") != "1"
    db.execute(
        "INSERT INTO webmentions (post_slug, source, target, kind, author_name, author_url, author_photo, content, "
        "published, approved, received_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(source, target) DO "
        "UPDATE SET kind=excluded.kind, author_name=excluded.author_name, author_url=excluded.author_url, "
        "author_photo=excluded.author_photo, content=excluded.content, published=excluded.published",
        (slug, source, target, info["kind"], info["author_name"], info["author_url"], info["author_photo"],
         info["content"], info["published"], 1 if auto else 0, utcnow().isoformat(timespec="seconds")))
    db.commit()


_queue = queue.Queue()
_worker = None
_lock = threading.Lock()


def _start():
    global _worker
    with _lock:
        if _worker is None:
            _worker = threading.Thread(target=_loop, name="webmention", daemon=True)
            _worker.start()


def _loop():
    while True:
        job = _queue.get()
        try:
            job[0](*job[1:])
        except Exception:
            log.exception("a webmention job failed")
        finally:
            _queue.task_done()


def accept(source: str, target: str) -> str:
    """"" if the mention was queued, else why it was refused (the
    endpoint's 400 message)."""
    if not source.startswith(("http://", "https://")) or not target.startswith(("http://", "https://")):
        return "source and target must be http(s) URLs"
    if source.split("#")[0] == target.split("#")[0]:
        return "source and target are the same"
    if not target_slug(target):
        return "target isn't a post on this site"
    _start()
    _queue.put((verify, source, target))
    return ""


def wait():
    _queue.join()


# ---- listing

def for_post(slug: str, approved_only: bool = True) -> list:
    q = "SELECT * FROM webmentions WHERE post_slug=?" + (" AND approved=1" if approved_only else "")  # noqa: S608 - written in the code
    return get_db().execute(q + " ORDER BY received_at", (slug,)).fetchall()


def _scope(status, q):
    where, args = [], []
    if status in ("pending", "approved"):
        where.append("approved=?")
        args.append(1 if status == "approved" else 0)
    if q.strip():
        like = f"%{q.strip()}%"
        where.append("(author_name LIKE ? OR content LIKE ? OR source LIKE ?)")
        args += [like, like, like]
    return (" WHERE " + " AND ".join(where)) if where else "", args


def list_all(status: str = "pending", page: int = 1, per_page: int = 20, q: str = "", sort: str = "newest") -> list:
    """status "" is both, waiting ones first."""
    where, args = _scope(status, q)
    order = "approved, " + ("received_at ASC" if sort == "oldest" else "received_at DESC")
    return get_db().execute(f"SELECT * FROM webmentions{where} ORDER BY {order} LIMIT ? OFFSET ?",  # noqa: S608 - written in the code
                            (*args, per_page, (max(1, page) - 1) * per_page)).fetchall()


def count(status: str = "pending", q: str = "") -> int:
    where, args = _scope(status, q)
    return get_db().execute(f"SELECT COUNT(*) FROM webmentions{where}", args).fetchone()[0]  # noqa: S608 - written in the code


def approve(mention_id: int):
    get_db().execute("UPDATE webmentions SET approved=1 WHERE id=?", (mention_id,))
    get_db().commit()


def delete(mention_id: int):
    get_db().execute("DELETE FROM webmentions WHERE id=?", (mention_id,))
    get_db().commit()


# ---- sending

def discover(url: str):
    """The webmention endpoint a page advertises (Link header, then
    <link>/<a rel="webmention">), or None."""
    try:
        final, ctype, headers, text = _fetch(url)
    except Exception as e:  # anything a server can answer with - see DEVELOPMENT.md > Errors
        log.info("couldn't fetch %s to find where to send a mention: %s", url, e)
        return None
    for value in headers.get_all("Link") or []:
        for part in value.split(","):
            m = re.match(r'\s*<([^>]*)>\s*;(.*)', part)
            if m and re.search(r'rel\s*=\s*"?[^"]*\bwebmention\b', m.group(2)):
                return urllib.parse.urljoin(final, m.group(1))
    if "html" not in ctype:
        return None
    soup = BeautifulSoup(text, "html.parser")
    tag = soup.find(["link", "a"], rel=lambda r: r and "webmention" in (r if isinstance(r, list) else r.split()),
                    href=True)
    if tag is not None:
        return urllib.parse.urljoin(final, tag["href"])
    return None


def send_one(source: str, target: str) -> str:
    endpoint = discover(target)
    if not endpoint:
        return "no endpoint"
    body = urllib.parse.urlencode({"source": source, "target": target}).encode()
    req = urllib.request.Request(endpoint, data=body, method="POST",  # noqa: S310 - opened through netguard
                                 headers={**UA, "Content-Type": "application/x-www-form-urlencoded"})
    try:
        with netguard.open_url(req, timeout=15) as resp:
            return f"sent ({resp.status})"
    except urllib.error.HTTPError as e:
        log.info("the webmention endpoint at %s refused the mention of %s: HTTP %s",
                 urllib.parse.urlsplit(endpoint).hostname, target, e.code)
        return f"refused ({e.code})"
    except Exception as e:  # anything a server can answer with - see DEVELOPMENT.md > Errors
        log.info("couldn't send the mention of %s to %s: %s", target, urllib.parse.urlsplit(endpoint).hostname, e)
        return f"failed ({str(e)[:60]})"


def outbound_links(slug: str) -> set:
    from soloblog import posts
    from soloblog.render import render_post
    row = posts.get_post(slug)
    if row and posts.is_protected(row):
        return set()  # its links would give its text away
    html, _ = render_post(posts.load_post_body(slug))
    links = set(re.findall(r'<a\s[^>]*?href="(https?://[^"]+)"', html))
    own = config.BASE_URL.rstrip("/")
    return {u.replace("&amp;", "&") for u in links if not u.startswith(own)}


def send_for(slug: str):
    """Tells every page this post links to - plus any it used to link to,
    so a removed link gets re-checked - in the background."""
    db = get_db()
    source = f"{config.BASE_URL}/post/{slug}"
    targets = outbound_links(slug) | {r["target"] for r in db.execute(
        "SELECT target FROM webmentions_sent WHERE slug=?", (slug,))}

    def run():
        from soloblog.db import get_db as db_here
        for target in sorted(targets):
            status = send_one(source, target)
            db_here().execute("INSERT INTO webmentions_sent (slug, target, status, sent_at) VALUES (?, ?, ?, ?) "
                              "ON CONFLICT(slug, target) DO UPDATE SET status=excluded.status, sent_at=excluded.sent_at",
                              (slug, target, status, utcnow().isoformat(timespec="seconds")))
            db_here().commit()
    _start()
    _queue.put((run,))
