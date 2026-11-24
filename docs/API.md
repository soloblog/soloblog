# The Soloblog API

The API is how other programs talk to your site. It lets an app, a
script or an AI assistant work on your site for you - read your posts,
write drafts, publish. It's yours alone: Soloblog has one admin, and
every request needs a key you made.

**You don't need this page to use Soloblog.** It's for people writing
their own scripts or apps. To connect a writing app like iA Writer or
Ulysses, or an AI assistant, follow
[Connect writing apps and AI assistants](guide/run.md#connect-writing-apps-and-ai-assistants)
instead - no code needed.

**Contents:** [Keys](#keys) · [Making a request](#making-a-request) ·
[Posts](#posts) · [Images](#images) · [Errors and limits](#errors-and-limits) ·
[Micropub and signing in](#micropub-and-signing-in) ·
[AI assistants (MCP)](#ai-assistants-mcp) ·
[Apps that publish to Ghost](#apps-that-publish-to-ghost) ·
[Comments](#comments) · [Webhooks](#webhooks)

## Keys

An API key is a password for one app or script. Make one in **Settings >
Integrations**, under **API keys**. Give it a name you'll recognise ("iA
Writer", "My laptop") and choose what it can do:

| Key | Can |
|---|---|
| **Read** | See your posts and pages - drafts and members posts too |
| **Write drafts** | Everything Read can, and write and change drafts, and upload images |
| **Publish** | Everything above, and publish, unpublish, change live posts and move posts to trash |

Give each app only what it needs: a key that writes drafts can't change
anything your readers see.

Even a Publish key can only publish if **Who may publish with a Publish
key**, on the same page, allows it:
- **No one** - every app's posts arrive as drafts.
- **Apps, not AI assistants** (to start with) - apps can publish; AI
  assistants' posts arrive as drafts.
- **Apps and AI assistants** - both can publish.

When publishing isn't allowed, a new post sent to be published arrives
as a draft instead - its `status` says so - and a request to publish or
change a live post gets "403", saying publishing is kept to the author.

The key is shown **once**, when you make it - copy it then. Soloblog keeps
only a scrambled copy, like a password, so it can't show it again. Lost
it? Revoke it and make another. **Revoke** stops a key at once; anything using it gets
"401" from then on.

Keep keys out of anything you share or publish. Anyone holding one can
do what it allows.

## Making a request

Every URL starts with your site's URL and `/api/v1`. The key goes
in the `Authorization` header - never in the URL, where logs keep it:

```bash
curl https://yourblog.com/api/v1/site \
  -H "Authorization: Bearer sb_your_key_here"
```

```json
{"title": "My Blog", "url": "https://yourblog.com", "version": "1.0.0-beta",
 "language": "en", "key": {"name": "My laptop", "scope": "draft"}}
```

What you send and get back is JSON. The API is off on the public demo.

## Posts

### List posts

```bash
curl "https://yourblog.com/api/v1/posts?status=draft&per_page=10" \
  -H "Authorization: Bearer sb_your_key_here"
```

| Parameter | What it does |
|---|---|
| `status` | `all` (the default), `published`, `draft`, `scheduled` or `pinned` |
| `q` | Words to search for |
| `tag` | Only posts with this tag |
| `page`, `per_page` | Which page, and how many on it (up to 100; 20 by default) |

You get `{"posts": [...], "total": 42, "page": 1, "per_page": 10}`. Each
post looks like this - `body` only when you ask for one post:

```json
{
  "slug": "my-first-post", "title": "My first post", "status": "published",
  "url": "https://yourblog.com/post/my-first-post", "page": false, "pin_location": "",
  "visibility": "public", "tags": ["notes"], "summary": "", "cover_image": "",
  "unlisted": false, "password_protected": false,
  "comments_enabled": true, "series_name": "", "series_order": 0, "seo_title": "",
  "link_url": "", "title_style": "", "page_width": "", "slides": false, "in_wiki": false,
  "remind_update": false, "scheduled_at": null, "created_at": "2026-10-01T09:00:00", "updated_at": "2026-10-02T10:30:00"
}
```

### Read one post

```bash
curl https://yourblog.com/api/v1/posts/my-first-post \
  -H "Authorization: Bearer sb_your_key_here"
```

The same, with `body`: the post in markdown.

### Write a draft

Needs a **Write drafts** key (or Publish).

```bash
curl https://yourblog.com/api/v1/posts \
  -H "Authorization: Bearer sb_your_key_here" \
  -H "Content-Type: application/json" \
  -d '{"title": "Notes from the weekend", "body": "It rained.", "tags": ["weekend", "notes"]}'
```

You get the new post back, with `201 Created`. Only `title` is needed.
What a post can have:

| Field | What it takes |
|---|---|
| `title` | Text, up to 300 characters |
| `body` | Markdown |
| `tags` | A list of words, or one string with commas |
| `summary` | Text |
| `cover_image` | An image's URL - one from [Images](#images) |
| `visibility` | `public`, `members` or `paid` |
| `unlisted`, `comments_enabled` | `true` or `false` |
| `title_style` | `""` (left), `centre` or `hidden` |
| `page_width` | `""` (the site's column) or `wide` |
| `slides`, `in_wiki`, `remind_update` | `true` or `false` - the page as slides, a note in the wiki, a reminder to update it |
| `link_url` | A URL starting with `https://`, or a path on this site - the title points there |
| `series_name`, `series_order` | A series' name, and the post's place in it |
| `seo_title` | The title search engines show |
| `published` | `true` publishes it - needs a **Publish** key |
| `scheduled_at` | When it goes live, like `2026-11-01T09:00:00Z` - needs **Publish** |
| `pin_location` | `header`, `footer` or `top`, or `""` - needs **Publish** |

A field the API doesn't know is an error, so a typo is never lost
quietly. The one exception is `layout`, which older tools still send: it
is ignored.

### Change a post

Send only what changes - everything else stays as it is:

```bash
curl -X PATCH https://yourblog.com/api/v1/posts/notes-from-the-weekend \
  -H "Authorization: Bearer sb_your_key_here" \
  -H "Content-Type: application/json" \
  -d '{"summary": "A short one"}'
```

A **Write drafts** key changes drafts only. A post that's live, or
publishing, scheduling or pinning, needs **Publish**.

### Publish, unpublish, trash

Each needs a **Publish** key.

```bash
curl -X POST https://yourblog.com/api/v1/posts/notes-from-the-weekend/publish \
  -H "Authorization: Bearer sb_your_key_here"
```

`/unpublish` makes it a draft again. `DELETE /api/v1/posts/<slug>` moves
it to trash - restore it from **Posts and pages > Trash**.

A post saved through the API is saved exactly as the editor saves it:
its history, search, translations and the fediverse all follow.

## Images

Upload one into your media library (a **Write drafts** key):

```bash
curl https://yourblog.com/api/v1/media \
  -H "Authorization: Bearer sb_your_key_here" \
  -F "file=@photo.jpg"
```

Or give a URL for Soloblog to fetch:

```bash
curl https://yourblog.com/api/v1/media \
  -H "Authorization: Bearer sb_your_key_here" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/photo.jpg"}'
```

You get `{"url": "/uploads/photo-1a2b.webp", "absolute_url": "https://..."}` -
put `url` in a post's markdown, or its `cover_image`. Up to 8 MB.
Soloblog only fetches from the public internet, never from addresses
inside your own network.

## Errors and limits

Something wrong gets a status and a sentence saying what:

```json
{"error": "This key can't do that - it needs Publish (it has Write drafts)"}
```

| Status | Means |
|---|---|
| 400 | What you sent isn't right - the message says why |
| 401 | No key, or the key is wrong or revoked |
| 403 | The key can't do that, or you're on the demo |
| 404 | No post with that slug |
| 413 | Too big - 2 MB for JSON, 8 MB for an image |
| 429 | Too many requests - 600 per 10 minutes for a key; 20 wrong keys in 15 minutes from one IP address |

## Micropub and signing in

Writing apps don't need a key typed in: they **sign in with your site**
(IndieAuth) and post with **Micropub** - both open standards, so any app
that speaks them works. Your home page tells apps where to go:

| For | Address |
|---|---|
| Micropub | `/micropub` - with `q=config`, `q=source`, `q=category` and `q=syndicate-to` |
| Media | `/micropub/media` |
| Signing in | `/indieauth/auth` (you approve the app there) and `/indieauth/token` |
| Details for apps | `/.well-known/oauth-authorization-server` |

How it works, for the curious:

- The app sends you to your site's **Connect** page, with a PKCE
  challenge (S256 only - an app that can't prove it's the one asking
  isn't allowed). You choose what it can do.
- Your site sends you back to the app - only to a URL on the app's
  own site, or one it lists on its page - with a code that works once,
  for 10 minutes.
- The app swaps the code for an API key. It's listed under **Settings >
  Integrations > API keys** like any other, and revoking it disconnects the
  app (as does the app signing out, `action=revoke`).
- Micropub posts an **entry** (`h=entry`) as a form or JSON: `name` (the
  title - a note without one is titled by how it begins), `content`
  (text, or HTML that becomes markdown), `category` (tags), `summary`,
  `photo` (files, or URLs fetched into your media library - public
  ones only), `post-status`, `mp-slug` and `bookmark-of` (the page gets a Link to).
  `update` (replace, add, delete), `delete` and `undelete` work on a post
  by its address.
- A **Write drafts** key always makes drafts and can't change a live
  post; so does a Publish key when **Who may publish with a Publish key**
  is **No one**.

## AI assistants (MCP)

`/mcp` is a Model Context Protocol server, so an AI assistant can work on
your site with its own tools. It takes the same keys - a Bearer header,
or a key the assistant gets by signing in with your site (it finds how at
`/.well-known/oauth-protected-resource`).

| Tool | Needs | Does |
|---|---|---|
| `search_posts` | Read | Finds posts by words, tag or status |
| `get_post` | Read | One post, with its markdown |
| `list_tags` | Read | Every tag, with how many posts have it |
| `list_comments` | Read | Readers' comments, approved or waiting |
| `images_without_alt` | Read | Images with no description for screen readers |
| `create_draft` | Write drafts | A new post, as a draft |
| `update_post` | Write drafts | Changes a draft's title, body, tags or summary |
| `set_alt_text` | Write drafts | Describes an image |
| `publish_post` | Publish | Publishes a draft |

**Who may publish with a Publish key** is **Apps, not AI assistants** to
start with, which keeps every assistant to drafts whatever its key:
`publish_post` isn't offered, and a live post can't be changed. An
assistant only sees the tools its key allows.

The details: Streamable HTTP, each request a JSON-RPC POST answered with
JSON (no event stream, no sessions); protocol versions `2025-06-18`,
`2025-03-26` and `2024-11-05`. A request from a page on another site
(`Origin`) is refused.

## Apps that publish to Ghost

Ulysses and iA Writer (on Apple devices) can publish to Ghost, and
Soloblog answers the part of Ghost's Admin API they use - so they publish
here too. Make a key with **For: Apps that publish to Ghost**: it's an
`id:secret` pair the app signs each request with (a JWT, HS256, valid for
up to 5 minutes), sent as `Authorization: Ghost <token>`.

| Address (under `/ghost/api/admin/`) | What it is |
|---|---|
| `site/` | The site's name and URL - no key needed |
| `users/me/` | Who's signed in |
| `tags/` | Every tag |
| `posts/` | List, or create (`html`, or a markdown card in `mobiledoc`) |
| `posts/{id}/` | Read, update (`PUT`) or move to trash (`DELETE`) |
| `images/upload/` | Upload an image (multipart, `file`) |

Older apps' URLs (`/ghost/api/v3/admin/` and the like) work the
same. Scopes are as for any key. The site doesn't keep a signed key's
secret: it works it out from its own `SESSION_SECRET` when it needs it,
so changing that secret means making these keys again.

## Comments

| Request | Needs | Does |
|---|---|---|
| `GET /api/v1/comments` | Read | `status` = `pending` (the default), `approved` or `trash`; `post` (a slug); `page`, `per_page` |
| `POST /api/v1/comments/<id>/approve` | Publish | Shows it on the site |
| `DELETE /api/v1/comments/<id>` | Publish | Moves it to trash |

Each comment: `id`, `post`, `author`, `body`, `status`, `reply_to`,
`by_author` and `created_at` - never the reader's email address.

## Webhooks

A webhook tells another service - Zapier, Make, n8n or your own script -
when something happens. Add one in **Settings > Integrations > Webhooks**: an
address, and what to tell it about.

| Event | Sent when | `data` |
|---|---|---|
| `post.published` | A post goes live - when it's published, or when its scheduled time comes. Once per post; not pages, not edits, and not the posts that were live before the webhook was added | The post, as the API gives it |
| `comment.created` | A comment arrives for you to approve | `post`, `post_url`, `author`, `body`, `moderate` (where to approve it) |
| `ping` | You select **Send a test** | `message` |

Each is a `POST` of JSON:

```json
{"id": "6f9c…", "event": "post.published", "site": "https://yourblog.com",
 "created_at": "2026-10-09T09:00:00Z", "data": {"slug": "…", "title": "…", "url": "…"}}
```

**Checking it's from your site.** Each message has
`X-Soloblog-Signature: t=<timestamp>,v1=<signature>`. The signature is an
HMAC-SHA256, in hex, of `<timestamp>.<the body exactly as sent>` with the
webhook's signing secret (**Settings > Integrations > Webhooks** shows it,
under the webhook). In
Python:

```python
import hashlib, hmac, time

def from_my_site(body: bytes, header: str, secret: str) -> bool:
    parts = dict(p.split("=", 1) for p in header.split(","))
    expected = hmac.new(secret.encode(), f"{parts['t']}.".encode() + body, hashlib.sha256).hexdigest()
    fresh = abs(time.time() - int(parts["t"])) < 300
    return fresh and hmac.compare_digest(expected, parts["v1"])
```

A message that doesn't get a `2xx` answer is tried twice more (after 2
and 10 seconds). Settings shows how the last one went. Webhooks only go to
public addresses - never to the server's own network.

