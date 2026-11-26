# Roadmap

What's planned for Soloblog and not built yet, nearest first. Once the
public Roadmap board on GitHub exists
([MAINTAINING.md](MAINTAINING.md) > Where feedback goes), the items move
there and this page goes.

Every item still has to pass the usual test: does it help one person run
their own site? The reasons behind what's here, and behind what was left
out, are in [DECISIONS.md](DECISIONS.md). An idea of your own starts in
[Discussions > Ideas](https://github.com/soloblog/soloblog/discussions/categories/ideas).

- [For 1.1](#for-11)
- [Later](#later)
- [Soloblog on the desktop](#soloblog-on-the-desktop)

## For 1.1

- **Export and import of custom templates.** A custom template as one
  file - markdown with its settings at the top, readable like a post -
  exported and imported in **Settings > Editor > Custom templates**.
  Images become placeholders on export (an image's URL points to
  its own site's uploads); the template still shows where each goes. An
  import is cleaned like anything typed into a post, so a shared file
  can't put a script on a site - with a test for the abuse case. Later,
  if people use it: a gallery of templates on the Soloblog website.
- **An image's size, chosen in the editor.** Small, Medium or Large for
  an image in a post - three sizes only, no dragging and no numbers, so
  images line up from post to post and still fit a phone.
- **Looks: a few curated design styles for the site.** A Look is the
  site's shapes and type; a palette stays its colours, so every Look
  works with every palette. To start: **Classic** (today's), **Editorial**
  (big confident headings, hairline rules instead of shadows, flat
  surfaces) and **Brutal** (neubrutalism: thick borders, hard offset
  shadows, square corners, extra-bold headings); later Soft and Glass.
  A Look is one small stylesheet and an entry in a registry: it sets
  daisyUI's own shape values (corners, borders, depth) and a short,
  fixed list of Soloblog's (heading scale, card border and shadow,
  section bands, image shapes, footer tone) that every section already
  reads through the shared names in `pages.py` - so a new section gets
  every Look with no extra work, and adding a Look later is one folder.
  Chosen in **Settings > Style** beside the palette, with the live
  preview; a starting style names one. The admin keeps its own neutral
  light and dark look, apart from the site's palette and Look, as a
  publishing app's own screens are - the site's look shows only where the
  admin previews the site. An update keeps Classic, so nothing changes until it's chosen.
- **A scratchpad beside the editor.** One pad for the whole site, as a
  scratch buffer is in a text editor: somewhere to park words while
  writing, there whichever post is open. Saved as you type, on the
  server, so it's on a phone too, and in backups with the settings;
  readers never see it. Opened from the editor's toolbar or a keyboard
  shortcut - a panel beside the editor on a wide screen, rising from
  the bottom on a phone - in the editor, focus mode and on a phone.
  **Add selection** puts the post's selected words at its end, and
  **Insert** puts the pad's words at the cursor. Plain text; one pad,
  not one per post.
- **A note for sample words left in.** Applying a template adds its
  sample words ("The first step."), which can reach a live page.
  Publishing a page that still has them says so, gently.
- **Referral and paid links marked for search engines.** A link can be
  marked as a referral or paid link, and gets `rel="sponsored"`, which
  search engines ask for on links that earn money. The simplest way: a
  choice in the link box.
- **Side panels placed separately for posts and pages.** In Settings,
  the contents and each side panel (tag cloud, archive links, About the
  author) get a place for posts and a place for pages - contents on the
  left on pages and on the right on posts, say - instead of one place and
  a **Shows on**. Each post or page can still choose its own. A site's
  Shows on carries over, so nothing changes on update.
- **Restoring a backup restores the images it saw.** Each version of
  an image is kept once in the bucket, named by a fingerprint of what's
  in it, and each backup lists which version every image had. Restoring
  an old backup puts back those versions - an image edited or deleted
  since included - and storage stays close to the images themselves, as
  an unchanged one is never kept twice. A version no kept backup or page
  uses goes with the last backup that did. It works the same with every
  storage company, and locked with a passphrase too; an existing bucket
  is changed over once, automatically.
- **Screenshots in Help, if people get lost.** The guide is written to
  work without screenshots (every step names the button and where it is);
  screenshots would add to every install and need retaking when the look
  changes. Add a few for the hardest steps if people say they need them.
- **More email services over HTTPS.** Today email goes out by SMTP,
  with Resend's API for hosts that block SMTP. Add the APIs of other
  sending services - Postmark, Brevo, Mailgun, Amazon SES - as choices
  beside Resend in **Settings > Email** and as host settings, so no host
  ties a site to one company.
- **Better animations and spacing for sections.** Sections that come
  into view with a little spring, and scrolling that settles into place
  where it helps (the Story, a slider). Even spacing between and inside
  sections, so a page keeps the same rhythm on a phone and a wide screen.
  Our own CSS, in every palette; "reduce motion" respected; no new
  dependency.
- **Automations with n8n, Zapier and Make.** They work today through the
  webhooks and the API ([API.md](API.md)); this makes them easy. In order
  of value for the work:
  1. **An "Automate your site" guide page** with three or four workflows
     to import - share a new post to Bluesky, Mastodon or LinkedIn; a
     comment alert to Telegram or email; a draft from Notion; posts
     copied to Google Drive. No new code.
  2. **More webhook events** (two today: a post goes live, a comment
     arrives): a post changed or unpublished, a new member, a new
     newsletter subscriber, a contact message, a member who paid, a
     failed backup or a Site health alert.
  3. **Members and subscribers in the API**, to keep a mailing tool in
     step - personal data, so its own key permission and the abuse-case
     tests.
  4. **A Soloblog step for n8n** (a community node), only if people ask.
- **AI that helps you build your site.** The AI writes what a person
  would - pages of sections, settings, answers from the guide - and it's
  saved and checked like anything typed. The admin and the visitor's
  pages stay the same every time: an admin that rearranges itself can't
  be learned or described in Help, and a page made fresh for every
  visitor can't be cached, found by search engines or checked. It's
  optional and uses the owner's own AI account and key; a site works
  the same without it. In order:
  1. **"Make me a page for…"** Describe the page you need ("my pottery
     classes, with prices and a booking button") and get sections, their
     `Key:` lines and sample text, made only from the kinds and values
     Soloblog has (`sections.py` as the description an AI follows). It
     opens as a preview to change before saving - a template made to
     order, with no tie to it afterwards.
  2. **Your own AI assistant runs your site** - Claude, ChatGPT or
     another - through an MCP server built on the API's keys
     ([API.md](API.md)): draft a post, add a section, find out why the
     newsletter didn't send. Each key's permissions still apply, with
     tests for the abuse case.
  3. **Help that answers questions** in the admin, from the guide's own
     pages, each answer linking to the setting or page it's about.
- **Faster pages, lighter downloads.** Measured on the sample blog with
  `tools/measure.py`: about 45 pages a second on one core, 20 ms a page.
  Biggest win first:
  - **Keep finished pages for visitors who aren't signed in**, thrown
    away whenever anything is saved - most pages in under a millisecond.
    Likes, members-only posts, password-protected posts and comment
    forms must stay right.
  - **A visitors' script and an admin script:** every reader downloads
    the whole app script today, much of it the admin's.
  - **Only the site's own palettes in its styles:** the stylesheet
    carries all 35; readers need the ones the site offers.
  - **One sheet of icons, not each one inline:** an admin page repeats
    its icons in full; each drawn once and used by name (`<use href>`).
  - **Database settings for writes:** `synchronous=NORMAL` with WAL, a
    larger page cache.
  - **Tests in parallel** (pytest-xdist - a development dependency, so
    the maintainer's OK first) and **journeys that wait for the thing**,
    not a fixed time.

  Meanwhile, Cloudflare in front ([DEPLOYMENT.md](DEPLOYMENT.md)) caches
  images and assets near readers, with no code.

## Later

Ideas, with no date.

- **The admin in other languages**, at least the editor and the posts
  list - visitors already get 23 languages, so a writer shouldn't have to
  run their site in English. This reopens "The admin is English"
  ([DECISIONS.md](DECISIONS.md)).
- **An editor that shows the page as it looks**, beside today's markdown
  one - for writers who've never used markdown. The post stays a markdown
  file underneath.
- **Plugins for other apps** (an Obsidian or VS Code "publish" button)
  are for anyone to build on the API - Soloblog itself doesn't sync.

## Soloblog on the desktop

A first-class app for Windows, macOS and Linux that runs your site from
your own computer: write in a window of its own, offline if need be, and
publish when you're ready. Still one person and their own site - the app
is a window onto it, never a second copy to keep in step. On a phone, the
admin in the browser already does this.

| Part | What it gives you |
|---|---|
| **Sign in with your site** | Type your blog's address, approve the app on the site, done - it gets its own key, shown in Settings and revocable there. Several sites in one app, if you run more than one |
| **The same editor** | The toolbar, slash menu, Focus mode, writing sessions and word goals you know from the admin, with your settings from the site - one editor, not a lookalike |
| **Your posts and pages** | Search, open, edit, schedule, publish, unpublish and trash, with the same status and History as the admin |
| **Write offline** | New posts and edits are kept on your computer and sent when you're back online. If the post changed on the site meanwhile, you see both and choose - nothing is overwritten quietly |
| **A true preview** | Rendered by your site itself, so it looks exactly as readers will see it, in your palette |
| **Images** | Drag in or paste an image; it goes to the media library, resized the way the site does |
| **Comments at a glance** | What's waiting for approval, with Approve and Reply |
| **Updates** | The app updates itself; it says so when the site needs a newer version for something |

### What it needs first

- **A preview address** that renders markdown with the site's own
  templates and theme, for the app's preview.
- **A way to tell an app's edit from the admin's**, so a post changed in
  both shows the choice rather than the last save winning.

The keys and the REST API it would use are built ([API.md](API.md)).

### Still to decide

- **What it's built with.** Tauri (small installers, the system's own web
  view, so the editor's own scripts run as they are) is the likely fit;
  Electron is heavier but the same everywhere; a native app per system
  is the most work.
- **Signed installers.** Without signing, macOS and Windows warn people
  off the app; signing needs a developer account for each, renewed every
  year.
- **Where it's offered:** GitHub Releases from the start; app stores and
  Linux packages (Flatpak, AppImage) later.
