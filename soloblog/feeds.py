import json
import re
from datetime import datetime, UTC
from email.utils import format_datetime
from html import escape

from soloblog import config
from soloblog import i18n
from soloblog import posts
from soloblog.render import render_post, without_section_lines

# The site's feeds, all built from the same list of posts: RSS 2.0
# (/rss, and /tag/<tag>/rss per tag), Atom (/atom.xml) and JSON Feed
# (/feed.json). Each carries the full post, so a reader app can show it
# without a visit, plus the summary.

FEED_SIZE = 20
_RELATIVE = re.compile(r'(\s(?:src|href|srcset)=")/(?!/)')


def _when(value: str) -> datetime:
    """A stored UTC stamp ("2026-09-24T08:00:00", "...Z" or a bare date)
    as an aware datetime."""
    try:
        dt = datetime.fromisoformat(value[:19].rstrip("Z"))
    except ValueError:
        dt = datetime(1970, 1, 1)
    return dt.replace(tzinfo=UTC)


def _absolute(html: str) -> str:
    # a feed reader has no page to resolve "/uploads/x.webp" against
    html = _RELATIVE.sub(lambda m: f'{m.group(1)}{config.BASE_URL}/', html)
    return re.sub(r'(srcset="[^"]*")', lambda m: m.group(1).replace(", /", f", {config.BASE_URL}/"), html)


def _entries(rows):
    for p in rows[:FEED_SIZE]:
        html, _ = render_post(posts.public_part(posts.load_post_body(p["slug"]) or "", p["visibility"]))
        html = without_section_lines(html)
        if posts.is_gated(p):
            html += posts.members_note(p)
        if posts.is_protected(p):
            html = f'<p>{escape(i18n.t("This post is protected with a password."))}</p>'
        yield {
            "p": p,
            "url": f"{config.BASE_URL}/post/{p['slug']}",
            # a post with a Link to has a feed item that points at the page it's about
            "link": p["link_url"] if p["link_url"] else f"{config.BASE_URL}/post/{p['slug']}",
            "html": _absolute(html),
            "published": _when(p["created_at"]),
            "updated": _when(p["updated_at"] or p["created_at"]),
            "tags": [t.strip() for t in p["tags"].split(",") if t.strip()],
            "image": config.BASE_URL + p["cover_image"] if p["cover_image"].startswith("/") else p["cover_image"],
        }


def rss(rows, s, title=None, path="/rss"):
    items = "\n".join(f"""    <item>
      <title>{escape(e['p']['title'])}</title>
      <link>{escape(e['link'])}</link>
      <guid isPermaLink="true">{e['url']}</guid>
      <pubDate>{format_datetime(e['published'])}</pubDate>
      {''.join(f'<category>{escape(t)}</category>' for t in e['tags'])}
      <description>{escape(e['p']['summary'])}</description>
      <content:encoded><![CDATA[{e['html'].replace(']]>', ']]]]><![CDATA[>')}]]></content:encoded>
    </item>""" for e in _entries(rows))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>{escape(title or s['site_title'])}</title>
  <link>{config.BASE_URL}/</link>
  <atom:link href="{config.BASE_URL}{escape(path)}" rel="self" type="application/rss+xml"/>
  <description>{escape(s['tagline'] or s['site_title'])}</description>
  <lastBuildDate>{format_datetime(datetime.now(UTC))}</lastBuildDate>
{items}
</channel>
</rss>"""


def atom(rows, s):
    entries = list(_entries(rows))
    updated = max((e["updated"] for e in entries), default=datetime.now(UTC))
    author = escape(s.get("author_name") or s["site_title"])
    body = "\n".join(f"""  <entry>
    <title>{escape(e['p']['title'])}</title>
    <link href="{escape(e['link'])}"/>
    <id>{e['url']}</id>
    <published>{e['published'].isoformat()}</published>
    <updated>{e['updated'].isoformat()}</updated>
    {''.join(f'<category term="{escape(t)}"/>' for t in e['tags'])}
    <summary>{escape(e['p']['summary'])}</summary>
    <content type="html">{escape(e['html'])}</content>
  </entry>""" for e in entries)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>{escape(s['site_title'])}</title>
  <subtitle>{escape(s['tagline'])}</subtitle>
  <link href="{config.BASE_URL}/"/>
  <link rel="self" href="{config.BASE_URL}/atom.xml"/>
  <id>{config.BASE_URL}/</id>
  <updated>{updated.isoformat()}</updated>
  <author><name>{author}</name></author>
{body}
</feed>"""


def json_feed(rows, s):
    items = []
    for e in _entries(rows):
        item = {"id": e["url"], "url": e["url"], "title": e["p"]["title"], "content_html": e["html"],
                **({"external_url": e["link"]} if e["link"] != e["url"] else {}),
                "date_published": e["published"].isoformat(), "date_modified": e["updated"].isoformat()}
        if e["p"]["summary"]:
            item["summary"] = e["p"]["summary"]
        if e["tags"]:
            item["tags"] = e["tags"]
        if e["image"]:
            item["image"] = e["image"]
        items.append(item)
    feed = {"version": "https://jsonfeed.org/version/1.1", "title": s["site_title"],
            "home_page_url": f"{config.BASE_URL}/", "feed_url": f"{config.BASE_URL}/feed.json",
            "items": items}
    if s.get("tagline"):
        feed["description"] = s["tagline"]
    if s.get("author_name"):
        feed["authors"] = [{"name": s["author_name"]}]
    return json.dumps(feed, ensure_ascii=False, indent=1)
