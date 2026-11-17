"""Webhooks: when something happens on the site, a JSON message to the
addresses the admin set up (Settings > Security > Webhooks) - for Zapier,
Make, n8n or a script of their own.

Each message is signed, so whoever receives it can check it came from
this site: X-Soloblog-Signature: t=<timestamp>,v1=<HMAC-SHA256 of
"<timestamp>.<body>" with the webhook's secret, in hex>. The secret isn't
stored - it's worked out from SESSION_SECRET and the webhook's id, and
shown in Settings. Sent in the background, to public addresses only
(netguard), tried three times."""
import hashlib
import hmac
import json
import threading
import time
import urllib.error
import urllib.request
import uuid
from soloblog.tz import utcnow

from soloblog import config
from soloblog import netguard
from soloblog.db import get_db

EVENTS = {"post.published": "A post goes live", "comment.created": "A comment arrives"}
RETRIES = (2, 10)  # seconds before the second and third tries


def secret_for(hook_id: int) -> str:
    return "whsec_" + hmac.new(config.SESSION_SECRET.encode(), f"webhook:{hook_id}".encode(),
                               hashlib.sha256).hexdigest()


def listed():
    return get_db().execute("SELECT * FROM webhooks ORDER BY created_at").fetchall()


def wanted(event: str) -> list:
    return [h for h in listed() if event in h["events"].split(",")]


def add(url: str, events: list) -> str:
    """"" when it's added, else what's wrong, in plain words."""
    url = (url or "").strip()
    events = [e for e in events if e in EVENTS]
    if not url.startswith(("https://", "http://")) or len(url) > 500:
        return "The address starts with https://"
    if not events:
        return "Choose at least one thing to tell it about"
    try:
        netguard.check_url(url)
    except netguard.Blocked as e:
        return f"That address can't be used - {e}"
    first_post_hook = "post.published" in events and not wanted("post.published")
    db = get_db()
    db.execute("INSERT INTO webhooks (url, events, created_at) VALUES (?, ?, ?)",
               (url, ",".join(events), utcnow().isoformat(timespec="seconds")))
    db.commit()
    if first_post_hook:
        # what's live already isn't news: only posts from now on
        from soloblog import publishing
        publishing.baseline("webhook")
    return ""


def remove(hook_id: int):
    db = get_db()
    db.execute("DELETE FROM webhooks WHERE id=?", (hook_id,))
    db.commit()


def signature(secret: str, body: bytes, stamp: int) -> str:
    return hmac.new(secret.encode(), f"{stamp}.".encode() + body, hashlib.sha256).hexdigest()


def deliver(hook, event: str, data: dict, retries=RETRIES) -> int:
    """One message to one webhook, tried again if it fails. Returns the
    last HTTP status (0: couldn't connect)."""
    body = json.dumps({"id": str(uuid.uuid4()), "event": event, "site": config.BASE_URL,
                       "created_at": utcnow().isoformat(timespec="seconds") + "Z", "data": data},
                      ensure_ascii=False).encode()
    status, error = 0, ""
    for wait in (0, *retries):
        time.sleep(wait)
        stamp = int(time.time())
        req = urllib.request.Request(hook["url"], data=body, method="POST", headers={  # noqa: S310 - opened through netguard
            "Content-Type": "application/json", "User-Agent": "Soloblog-Webhook", "X-Soloblog-Event": event,
            "X-Soloblog-Signature": f"t={stamp},v1={signature(secret_for(hook['id']), body, stamp)}"})
        try:
            with netguard.open_url(req, timeout=10) as resp:
                status, error = resp.status, ""
        except urllib.error.HTTPError as e:
            status, error = e.code, f"It answered {e.code}"
        except (urllib.error.URLError, OSError, netguard.Blocked) as e:
            status, error = 0, f"Couldn't reach it: {getattr(e, 'reason', e)}"
        if 200 <= status < 300:
            break
    db = get_db()
    db.execute("UPDATE webhooks SET last_at=?, last_status=?, last_error=? WHERE id=?",
               (utcnow().isoformat(timespec="seconds"), status, error[:300], hook["id"]))
    db.commit()
    return status


def send(event: str, data: dict):
    """To every webhook that wants this event - in the background, so a
    slow receiver never holds anything up."""
    for hook in wanted(event):
        threading.Thread(target=deliver, args=(dict(hook), event, data), daemon=True).start()


def comment_data(post_slug: str, author_name: str, body: str) -> dict:
    """A comment as a webhook tells of it - no email address."""
    from soloblog import posts
    return {"post": post_slug, "post_url": config.BASE_URL + posts.url_for_slug(post_slug),
            "author": author_name, "body": body, "moderate": f"{config.BASE_URL}/admin/comments"}
