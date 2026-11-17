import contextvars
import json

from fasthtml.common import Meta, Link, Script, NotStr
from soloblog import config


# the current request's page title - set by page_meta, read by Layout
# (ui), which renders it as the page's only <title>. Each request's
# handler runs in its own copy of the context, so this never leaks
# from one request into another.
_page_title = contextvars.ContextVar("page_title", default=None)


def current_title():
    return _page_title.get()


def page_meta(hdrs, title: str, description: str = "", path: str = "/", image: str = None, type_: str = "website",
              canonical: str = ""):
    """Appends title/description/canonical/OG tags for the current
    request. Call this once per route, passing the `hdrs` special param
    FastHTML injects - it's a per-request list, so this only affects
    the page being rendered right now, not the global defaults.
    """
    from soloblog import settings
    url = config.BASE_URL + path
    # the site's title as set in Settings - config.SITE_TITLE is only
    # the environment's starting default
    site_title = settings.get("site_title") or config.SITE_TITLE
    full_title = f"{title} — {site_title}" if title != site_title else title

    _page_title.set(full_title)
    # a post first published elsewhere credits that page (Post settings)
    hdrs.append(Link(rel="canonical", href=canonical or url))
    # a page with no image of its own shares the site's (Settings > Site),
    # or else a card with the site's name (cards.py)
    if not image:
        from soloblog import cards
        image = settings.get("share_image_url") or cards.site_card_url()
    # a page with nothing of its own to say (Join, Membership) says what the site is
    description = description or settings.get("tagline") or ""
    if description:
        hdrs.append(Meta(name="description", content=description))
    hdrs.append(Meta(property="og:title", content=full_title))
    hdrs.append(Meta(property="og:type", content=type_))
    hdrs.append(Meta(property="og:url", content=url))
    if description:
        hdrs.append(Meta(property="og:description", content=description))
    if image:
        image, size = _share_size(image)
        hdrs.append(Meta(property="og:image", content=config.BASE_URL + image))
        if size:
            hdrs += [Meta(property="og:image:width", content=str(size[0])),
                     Meta(property="og:image:height", content=str(size[1]))]
    hdrs.append(Meta(name="twitter:card", content="summary_large_image" if image else "summary"))


def _share_size(image):
    """(address, (width, height) or None) for a shared picture: one of our
    own uploads wider than a preview needs is shared as its 1600 px copy
    (images.SIZES) - a 2560 px cover showed in no preview on WhatsApp -
    with its size, so apps draw the preview big straight away."""
    import os
    from PIL import Image
    from soloblog import images
    if not image.startswith("/uploads/") or "?" in image or not images.plain_name(image[9:]):
        return image, None
    path = os.path.join(config.uploads_dir(), image[9:])
    try:
        with Image.open(path) as img:
            w, h = img.size
    except (OSError, ValueError, Image.DecompressionBombError):
        return image, None
    if w > 1600:
        return f"{image}?w=1600", (1600, round(h * 1600 / w))
    return image, (w, h)


def website_data(s) -> Script:
    """schema.org WebSite for the homepage: the site's name, and its
    search, which search engines can offer as a search box."""
    data = {"@context": "https://schema.org", "@type": "WebSite", "name": s["site_title"],
            "url": config.BASE_URL + "/",
            "potentialAction": {"@type": "SearchAction",
                                "target": config.BASE_URL + "/search?q={search_term_string}",
                                "query-input": "required name=search_term_string"}}
    if s.get("tagline"):
        data["description"] = s["tagline"]
    return Script(NotStr(json.dumps(data, ensure_ascii=False).replace("</", "<\\/")), type="application/ld+json")


def _stamp(value: str) -> str:
    """A stored UTC stamp as ISO 8601 with its timezone."""
    value = (value or "")[:19].rstrip("Z")
    return value + ("Z" if len(value) > 10 else "")


def article_data(row, s, description: str = ""):
    """schema.org BlogPosting for a post page (WebPage for a pinned page):
    lets search engines show the date, author and image with the result."""
    from soloblog import posts
    url = config.BASE_URL + posts.url_for(row)
    author = s.get("author_name") or s["site_title"]
    data = {
        "@context": "https://schema.org",
        "@type": "WebPage" if row["pinned"] else "BlogPosting",
        "headline": row["title"][:110],
        "url": url,
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "datePublished": _stamp(row["created_at"]),
        "dateModified": _stamp(row["updated_at"] or row["created_at"]),
        "author": {"@type": "Person", "name": author, "url": config.BASE_URL + "/"},
        "publisher": {"@type": "Organization", "name": s["site_title"], "url": config.BASE_URL + "/"},
    }
    if description:
        data["description"] = description
    if row["cover_image"]:
        image = row["cover_image"]
        data["image"] = config.BASE_URL + image if image.startswith("/") else image
    tags = [t.strip() for t in row["tags"].split(",") if t.strip()]
    if tags:
        data["keywords"] = tags
    # a members post: Google's markup for content behind a sign-in, so its
    # preview isn't taken for hiding text from readers (cloaking)
    from soloblog import members
    if posts.clean_visibility(row["visibility"] if "visibility" in row.keys() else "") != "public" \
            and members.enabled(s):
        data["isAccessibleForFree"] = False
        data["hasPart"] = {"@type": "WebPageElement", "isAccessibleForFree": False, "cssSelector": ".members-only"}
    # "</" can't appear inside a <script>, whatever a title contains
    return Script(NotStr(json.dumps(data, ensure_ascii=False).replace("</", "<\\/")), type="application/ld+json")
