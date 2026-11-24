from pathlib import Path
import json
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, UTC

from fasthtml.common import Button, Div, Span

from soloblog import js
from soloblog import netguard
from soloblog import config
from soloblog import i18n
from soloblog.actions import on, EL

# Another comment system instead of Soloblog's own (Settings > Comments and messages).
# Giscus, Isso and Remark42 are a script from another site: nothing loads
# until the reader clicks (loadComments, EXT_COMMENTS_JS), unless the
# admin turns that off. Each follows the site's light or dark theme, and
# Giscus and Isso take on its actual colors. Bluesky is different: the
# server fetches the replies and draws them like Soloblog's own comments.
# (Disqus, Cusdis and Hyvor Talk were dropped before 0.4: Disqus tracks
# readers; a site still set to one shows Soloblog's own comments.)

URL_RE = re.compile(r"^https?://[^\s\"'<>]+$")
# older GitHub ids are base64, "=" and all
ID_RE = re.compile(r"^[\w=-]{0,100}$")

# setting: (label, placeholder, pattern the value must match)
FIELDS = {
    "giscus_repo": ("Repository", "you/your-blog", re.compile(r"^([\w.-]+/[\w.-]+)?$")),
    "giscus_repo_id": ("Repository ID", "R_kgDO...", ID_RE),
    "giscus_category": ("Category", "Announcements", re.compile(r"^[^<>\"]{0,100}$")),
    "giscus_category_id": ("Category ID", "DIC_kwDO...", ID_RE),
    "bluesky_handle": ("Bluesky handle", "you.bsky.social", re.compile(r"^[a-z0-9.-]{0,253}$")),
    "isso_url": ("Isso URL", "https://comments.example.com", URL_RE),
    "remark42_url": ("Remark42 URL", "https://remark42.example.com", URL_RE),
    "remark42_site_id": ("Site ID", "remark", ID_RE),
}

# name: (label, what it is, host readers load it from, fields - the
# first ones listed are required)
SYSTEMS = {
    "giscus": ("Giscus", "GitHub Discussions, readers sign in with GitHub", "GitHub",
               ["giscus_repo", "giscus_repo_id", "giscus_category", "giscus_category_id"]),
    "bluesky": ("Bluesky", "the replies to your post about it on Bluesky", "Bluesky", ["bluesky_handle"]),
    "isso": ("Isso", "self-hosted, anonymous comments", "your Isso server", ["isso_url"]),
    "remark42": ("Remark42", "self-hosted, social logins or anonymous", "your Remark42 server",
                 ["remark42_url", "remark42_site_id"]),
}
REQUIRED = {"remark42": ["remark42_url"]}


def clean(key: str, value: str) -> str:
    """A field as the admin typed it, or "" if it isn't the right shape
    - every one ends up in an attribute or a script address."""
    value = (value or "").strip()
    if key == "bluesky_handle":
        value = value.lstrip("@").lower()
    elif FIELDS[key][2] is URL_RE:
        value = value.rstrip("/")
    return value if FIELDS[key][2].match(value) else ""


def system(s) -> str:
    """The comment system in use: one of SYSTEMS, or "" for Soloblog's
    own - including when the chosen one isn't set up yet."""
    name = s.get("comments_system") or ""
    if name not in SYSTEMS:
        return ""
    return name if all(s.get(k) for k in REQUIRED.get(name, SYSTEMS[name][3])) else ""


def Section(s, row, url: str, lang: str = "en"):
    """What sits in the Comments card instead of Soloblog's own list and form."""
    name = system(s)
    slug = row["slug"]
    if name == "bluesky":
        # fetched after the page, so a slow Bluesky never slows the post
        return Div(Span(cls="loading loading-spinner loading-sm"), hx_get=f"/post/{slug}/bluesky",
                   hx_trigger="revealed", hx_swap="outerHTML", cls="flex justify-center py-6")
    label, _, host, _ = SYSTEMS[name]
    data = {"url": url, "id": slug, "path": url.replace(config.BASE_URL, "", 1), "title": row["title"], "lang": lang,
            "autoload": "1" if s.get("comments_autoload") == "1" else None}
    if name == "giscus":
        data.update(repo=s["giscus_repo"], repo_id=s["giscus_repo_id"], category=s["giscus_category"],
                    category_id=s["giscus_category_id"], theme=s.get("theme") or "light",
                    # giscus.app fetches a custom theme itself, so it has to be a public https address
                    theme_url=f"{config.BASE_URL}/comments/giscus-theme"
                    if config.BASE_URL.startswith("https://") else None)
    elif name == "isso":
        data["host"] = s["isso_url"]
    elif name == "remark42":
        data.update(host=s["remark42_url"], site=s.get("remark42_site_id") or "remark")
    attrs = {f"data_{k}": v for k, v in data.items() if v is not None}
    return Div(
        Button(i18n.t("Load comments"), type="button", cls="btn btn-primary btn-sm", **on("click", "loadComments", EL)),
        Span(i18n.t("Comments are hosted by {service}. Nothing loads from {host} until you click.",
                    service=label, host=i18n.t(host) if host.startswith("your ") else host),
             cls="text-xs text-base-content/60"),
        data_ext_comments=name, **attrs, cls="flex flex-col items-center gap-2 py-6 text-center"
    )


# ---- Giscus: a theme made from the site's own colors

_theme_cache = (None, {})


def _theme_blocks() -> dict:
    """{theme: {"color-scheme": ..., "--color-base-100": ...}} read from
    the built stylesheet, where daisyUI writes every theme out."""
    global _theme_cache
    path = os.path.join("static", "css", "output.css")
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return {}
    if _theme_cache[0] != mtime:
        css = Path(path).read_text(encoding="utf-8")
        themes = {}
        for name, body in re.findall(r"\[data-theme=[\"']?([\w-]+)[\"']?\]\s*\{([^}]*)\}", css):
            props = dict(re.findall(r"(color-scheme|--color-[\w-]+)\s*:\s*([^;]+)", body))
            if props:
                themes.setdefault(name, {}).update({k: v.strip() for k, v in props.items()})
        _theme_cache = (mtime, themes)
    return _theme_cache[1]


def giscus_css(theme: str) -> str:
    from soloblog import themes
    own = {o["key"]: {"color-scheme": o["scheme"], **o["values"]} for o in themes.own_themes()}
    t = own.get(theme) or _theme_blocks().get(theme, {})
    base = "dark" if t.get("color-scheme", "").strip() == "dark" else "light"
    out = f'@import url("https://giscus.app/themes/{base}.css");\n'
    if not t:
        return out

    def c(name, pct=None):
        v = t.get(f"--color-{name}", "")
        return f"color-mix(in oklab, {v} {pct}%, transparent)" if pct else v
    pairs = {
        "canvas-default": c("base-100"), "canvas-overlay": c("base-100"), "canvas-inset": c("base-200"),
        "canvas-subtle": c("base-200"), "border-default": c("base-300"), "border-muted": c("base-300"),
        "neutral-muted": c("base-content", 12), "fg-default": c("base-content"), "fg-muted": c("base-content", 70),
        "fg-subtle": c("base-content", 50), "accent-fg": c("primary"), "accent-emphasis": c("primary"),
        "accent-muted": c("primary", 40), "accent-subtle": c("primary", 12), "success-fg": c("success"),
        "attention-fg": c("warning"), "danger-fg": c("error"), "btn-text": c("base-content"),
        "btn-bg": c("base-200"), "btn-border": c("base-300"), "btn-hover-bg": c("base-300"),
        "btn-active-bg": c("base-300"), "btn-primary-text": c("primary-content"), "btn-primary-bg": c("primary"),
        "btn-primary-border": c("primary"), "btn-primary-hover-bg": c("primary"),
        "btn-primary-disabled-bg": c("primary", 60), "social-reaction-bg-hover": c("base-200"),
        "social-reaction-bg-reacted-hover": c("primary", 20),
    }
    body = "".join(f"  --color-{k}: {v};\n" for k, v in pairs.items() if v)
    return out + f"main {{\n  color-scheme: {base};\n{body}}}\n"


# ---- Bluesky: the replies to the post that links here

_API = "https://public.api.bsky.app/xrpc/"
_cache = {}


def _get(method: str, **params) -> dict:
    url = _API + method + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Soloblog", "Accept": "application/json"})  # noqa: S310 - opened through netguard
    with netguard.open_url(req, timeout=8) as resp:
        return json.loads(resp.read())


def _cached(key, seconds, fn):
    hit = _cache.get(key)
    if hit and hit[0] > time.monotonic():
        return hit[1]
    value = fn()
    _cache[key] = (time.monotonic() + seconds, value)
    return value


def _norm(url: str) -> str:
    return url.split("://", 1)[-1].split("?", 1)[0].split("#", 1)[0].rstrip("/").lower()


def _links(record: dict) -> list:
    out = [f["uri"] for facet in record.get("facets", []) for f in facet.get("features", []) if f.get("uri")]
    embed = record.get("embed") or {}
    external = embed.get("external") or (embed.get("media") or {}).get("external") or {}
    if external.get("uri"):
        out.append(external["uri"])
    return out


def find_thread(handle: str, post_url: str):
    """The at:// address of the handle's own post linking to post_url -
    looked for in their last 300 posts, and remembered for a while."""
    target = _norm(post_url)

    def look():
        cursor = None
        for _ in range(3):
            params = {"actor": handle, "limit": 100, "filter": "posts_no_replies"}
            if cursor:
                params["cursor"] = cursor
            page = _get("app.bsky.feed.getAuthorFeed", **params)
            for item in page.get("feed", []):
                post = item.get("post", {})
                if post.get("author", {}).get("handle") != handle:
                    continue  # a repost
                record = post.get("record", {})
                if any(_norm(u) == target for u in _links(record)) or target in record.get("text", "").lower():
                    return post["uri"]
            cursor = page.get("cursor")
            if not cursor:
                break
        return None
    return _cached(("thread", handle, target), 30 * 60, look)


def _when(value: str) -> str:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return ""
    return dt.astimezone(UTC).replace(tzinfo=None).isoformat()


def _tree(replies: list) -> list:
    out = []
    for r in replies or []:
        post = r.get("post")
        if not post or r.get("$type", "").endswith(("blockedPost", "notFoundPost")):
            continue
        author = post.get("author", {})
        out.append({
            "name": author.get("displayName") or author.get("handle", ""),
            "handle": author.get("handle", ""),
            "text": post.get("record", {}).get("text", ""),
            "created_at": _when(post.get("record", {}).get("createdAt", "")),
            "likes": post.get("likeCount", 0),
            "url": f"https://bsky.app/profile/{author.get('handle', '')}/post/{post['uri'].rsplit('/', 1)[-1]}",
            "replies": _tree(r.get("replies")),
        })
    return sorted(out, key=lambda c: c["created_at"])


def thread(handle: str, post_url: str, slug: str = ""):
    """(where to reply on Bluesky, [replies with their own replies]),
    or (None, []) when there's no post linking here yet - the one Soloblog
    shared itself (crosspost.py) if there is one, else found in the feed."""
    from soloblog.db import get_db
    shared = get_db().execute("SELECT remote_id FROM published_log WHERE slug=? AND channel='bluesky'",
                              (slug,)).fetchone() if slug else None
    uri = shared["remote_id"] if shared and shared["remote_id"] else find_thread(handle, post_url)
    if not uri:
        return None, []

    def fetch():
        t = _get("app.bsky.feed.getPostThread", uri=uri, depth=6, parentHeight=0).get("thread", {})
        return _tree(t.get("replies"))
    reply_url = f"https://bsky.app/profile/{handle}/post/{uri.rsplit('/', 1)[-1]}"
    return reply_url, _cached(("replies", uri), 5 * 60, fetch)


EXT_COMMENTS_JS = js.read("ext_comments.js")
