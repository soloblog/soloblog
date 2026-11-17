import logging
import json
import mimetypes
import os
import urllib.request
import uuid
from datetime import datetime, UTC

from soloblog import config
from soloblog import netguard

log = logging.getLogger(__name__)

# New posts shared to the admin's own Bluesky and Mastodon accounts (Settings >
# Site > Sharing), through the publishing queue: once each, when a
# post goes live - never an edit or a page. The Bluesky post gets a link card
# with the cover image, and becomes the thread Bluesky comments are read from.

BLUESKY_PDS = "https://bsky.social"


def bluesky_on(s) -> bool:
    return s.get("crosspost_bluesky") == "1" and bool(s.get("bluesky_handle")) and bool(s.get("bluesky_app_password"))


def mastodon_on(s) -> bool:
    return s.get("crosspost_mastodon") == "1" and bool(s.get("mastodon_instance")) and bool(s.get("mastodon_token"))


def _post_url(row) -> str:
    from soloblog import posts
    return config.BASE_URL + posts.url_for(row)


def _summary(row) -> str:
    from soloblog import posts
    from soloblog.render import excerpt, render_post
    if posts.is_protected(row):
        return row["summary"]
    return row["summary"] or excerpt(render_post(posts.public_part(posts.load_post_body(row["slug"]),
                                                                    row["visibility"]))[0])


def _json(url: str, data: dict = None, token: str = "", body: bytes = None, content_type: str = "application/json"):
    headers = {"Content-Type": content_type, "Accept": "application/json", "User-Agent": "Soloblog"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = body if body is not None else json.dumps(data).encode()
    req = urllib.request.Request(url, data=payload, method="POST", headers=headers)  # noqa: S310 - opened through netguard
    with netguard.open_url(req, timeout=15) as resp:
        return json.loads(resp.read())


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def to_bluesky(row, s) -> str:
    """Posts it; returns the new post's at:// address."""
    session = _json(f"{BLUESKY_PDS}/xrpc/com.atproto.server.createSession",
                    {"identifier": s["bluesky_handle"], "password": s["bluesky_app_password"]})
    token, did = session["accessJwt"], session["did"]
    card = {"uri": _post_url(row), "title": row["title"], "description": _clip(_summary(row), 300)}
    thumb = _cover_blob(row, token)
    if thumb:
        card["thumb"] = thumb
    from soloblog import translate
    record = {
        "$type": "app.bsky.feed.post",
        "text": _clip(row["title"], 300),
        "createdAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "langs": [translate.site_language(s)],
        "embed": {"$type": "app.bsky.embed.external", "external": card},
    }
    made = _json(f"{BLUESKY_PDS}/xrpc/com.atproto.repo.createRecord",
                 {"repo": did, "collection": "app.bsky.feed.post", "record": record}, token=token)
    return made["uri"]


def _cover_blob(row, token: str):
    """The cover image, uploaded for the link card - its 800px copy, as
    Bluesky caps a card image at 1 MB. None if there isn't one."""
    from soloblog import images
    cover = row["cover_image"] or ""
    if not cover.startswith("/uploads/"):
        return None
    try:
        path = images.sized(cover.rsplit("/", 1)[1], 800)
        if not path or not os.path.exists(path) or os.path.getsize(path) > 950_000:
            return None
        with open(path, "rb") as f:
            return _json(f"{BLUESKY_PDS}/xrpc/com.atproto.repo.uploadBlob", body=f.read(), token=token,
                         content_type=mimetypes.guess_type(path)[0] or "image/webp")["blob"]
    except Exception as e:
        log.warning("no card image for Bluesky: %s", e)
        return None


def to_mastodon(row, s) -> str:
    """Posts it; returns the status's own link."""
    text = _clip(f"{row['title']}\n\n{_summary(row)}", 450) + f"\n\n{_post_url(row)}"
    instance = s["mastodon_instance"].rstrip("/")
    req = urllib.request.Request(  # noqa: S310 - opened through netguard
        f"{instance}/api/v1/statuses", method="POST",
        data=json.dumps({"status": text, "visibility": "public"}).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {s['mastodon_token']}",
                 # the same post never goes out twice, even if a request is retried
                 "Idempotency-Key": str(uuid.uuid5(uuid.NAMESPACE_URL, _post_url(row))), "User-Agent": "Soloblog"})
    # the instance is the admin's, but never a private address
    with netguard.open_url(req, timeout=15) as resp:
        return json.loads(resp.read()).get("url", "")
