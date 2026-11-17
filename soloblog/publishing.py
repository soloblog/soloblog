import logging
import hashlib
import threading
import time
from soloblog.tz import utcnow

from soloblog.db import get_db

log = logging.getLogger(__name__)

# Announcing posts beyond the site itself - to fediverse followers
# (fediverse.py), to the pages a post links to (webmention.py) and to
# newsletter subscribers (newsletter.py) and to the admin's own Bluesky and
# Mastodon accounts (crosspost.py) - those three new posts only, never a page. A
# post is announced once it's live, whether that's the moment it's
# saved or when its scheduled time comes (nobody saves anything then,
# so a quiet background check every minute catches it), and again as
# an update whenever its content changes. published_log remembers what
# went out, per channel.
#
# Turning a channel on marks every post that's already live as done
# (baseline), so followers aren't flooded with the whole back catalogue.

CHANNELS = ("activitypub", "webmention", "newsletter", "bluesky", "mastodon", "webhook")
# sent once, when a post goes live - an edit isn't news, and a page isn't a post
NEW_POSTS_ONLY = ("newsletter", "bluesky", "mastodon", "webhook")
INTERVAL = 60
# the background ticker; the test suite turns it off and calls check()
# itself, so what's announced never depends on thread timing
AUTOMATIC = True

_kick = threading.Event()
_thread = None
_last_run = None


def last_run():
    """When the background check last ran (a timestamp), for Site health -
    None before it first has."""
    return _last_run
_lock = threading.Lock()
# one check at a time - two at once (the minute tick and a save) would
# both see a post as new and announce it twice
_check_lock = threading.Lock()


def _hash(row) -> str:
    from soloblog import posts
    return hashlib.sha256(f"{row['title']}\n{row['summary']}\n{row['cover_image']}\n{row['tags']}\n"
                          f"{posts.load_post_body(row['slug'])}".encode()).hexdigest()[:16]


def _channel_on(channel: str, s) -> bool:
    from soloblog import crosspost
    from soloblog import fediverse
    from soloblog import newsletter
    from soloblog import webmention
    if channel == "newsletter":
        return newsletter.sending(s)
    if channel == "bluesky":
        return crosspost.bluesky_on(s)
    if channel == "mastodon":
        return crosspost.mastodon_on(s)
    if channel == "webhook":
        from soloblog import webhooks
        return bool(webhooks.wanted("post.published"))
    return fediverse.enabled(s) if channel == "activitypub" else webmention.sending(s)


def baseline(channel: str):
    """Marks every live post as already announced on channel."""
    from soloblog import posts
    db = get_db()
    now = utcnow().isoformat(timespec="seconds")
    for row in posts.list_all_published():
        db.execute("INSERT OR IGNORE INTO published_log (slug, channel, content_hash, done_at) VALUES (?, ?, ?, ?)",
                   (row["slug"], channel, _hash(row), now))
    db.commit()


def check():
    """Announces whatever's live and new or changed since last time."""
    with _check_lock:
        _check()


def _check():
    from soloblog import crosspost
    from soloblog import fediverse
    from soloblog import newsletter
    from soloblog import posts
    from soloblog import settings
    from soloblog import webmention
    s = settings.get_all()
    db = get_db()
    now = utcnow().isoformat(timespec="seconds")
    for channel in CHANNELS:
        if not _channel_on(channel, s):
            continue
        done = {r["slug"]: r["content_hash"] for r in db.execute(
            "SELECT slug, content_hash FROM published_log WHERE channel=?", (channel,))}
        for row in posts.list_all_published():
            digest = _hash(row)
            if done.get(row["slug"]) == digest or (channel == "newsletter" and done.get(row["slug"]) == newsletter.SKIP):
                continue
            remote = None
            try:
                if channel in NEW_POSTS_ONLY and (row["slug"] in done or posts.is_page(row)):
                    pass  # just remember this version
                elif channel == "activitypub":
                    fediverse.publish(row, update=row["slug"] in done)
                elif channel == "newsletter":
                    newsletter.send_post(row, s)
                elif channel == "bluesky":
                    remote = crosspost.to_bluesky(row, s)
                elif channel == "mastodon":
                    remote = crosspost.to_mastodon(row, s)
                elif channel == "webhook":
                    from soloblog import webhooks
                    from soloblog.routes.api import post_json
                    webhooks.send("post.published", post_json(row))
                else:
                    webmention.send_for(row["slug"])
            except Exception as e:
                log.warning("%s %s: %s", channel, row['slug'], e)
                continue
            db.execute("INSERT INTO published_log (slug, channel, content_hash, done_at, remote_id) "
                       "VALUES (?, ?, ?, ?, ?) ON CONFLICT(slug, channel) DO UPDATE SET "
                       "content_hash=excluded.content_hash, done_at=excluded.done_at, "
                       "remote_id=COALESCE(excluded.remote_id, published_log.remote_id)",
                       (row["slug"], channel, digest, now, remote))
            db.commit()
    if newsletter.held():
        try:
            newsletter.send_held(s)
        except Exception as e:
            log.warning("newsletter, the rest: %s", e)
    if newsletter.digest(s):
        from soloblog.tz import to_local
        local = to_local(utcnow().replace(tzinfo=None))
        if newsletter.digest_due(s, local):
            try:
                newsletter.send_digest(s, local)
            except Exception as e:
                log.warning("newsletter digest: %s", e)


def retract(slug: str):
    """A post taken down (trashed): followers' servers are told."""
    from soloblog import fediverse
    db = get_db()
    if fediverse.enabled() and db.execute("SELECT 1 FROM published_log WHERE slug=? AND channel='activitypub'",
                                          (slug,)).fetchone():
        fediverse.retract(slug)
    db.execute("DELETE FROM published_log WHERE slug=? AND channel='activitypub'", (slug,))
    db.commit()


def kick():
    """Check now rather than at the next minute - after a save."""
    _kick.set()


def _loop():
    global _last_run
    while True:
        _kick.wait(INTERVAL)
        _kick.clear()
        if not AUTOMATIC:
            continue
        _last_run = time.time()
        try:
            check()
        except Exception:
            log.exception("checking for posts to send failed")


def start():
    global _thread
    with _lock:
        if _thread is None:
            _thread = threading.Thread(target=_loop, name="publishing", daemon=True)
            _thread.start()
