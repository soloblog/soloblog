# Developing Soloblog

Notes for working on the code itself. For running or hosting a blog, see
the [README](../README.md) and [DEPLOYMENT.md](DEPLOYMENT.md). The working
rules for every change are in [CLAUDE.md](../CLAUDE.md); how releases,
feedback and dependencies are handled, in [MAINTAINING.md](MAINTAINING.md);
the reasons behind big choices, in [DECISIONS.md](DECISIONS.md).

## Change a site with an AI agent

Soloblog is yours to change. An AI coding agent - Claude Code, Codex,
Cursor or one like them - can add a feature to your own copy while you
describe it in plain words. You don't need to write code.

1. **Make your own copy.** Open the
   [Soloblog repository](https://github.com/soloblog/soloblog) on GitHub
   and select **Fork**. Your copy is where your changes live.
2. **Set it up on your computer.** Open your agent in an empty folder
   and paste this, with your GitHub name in it:

   ```text
   Clone https://github.com/YOUR-NAME/soloblog and set it up for
   development: read CLAUDE.md first, then follow docs/DEVELOPMENT.md >
   Local setup. Start the app and tell me the address to open.
   ```

   It installs what Soloblog needs into the project's own folder and
   starts a copy of the app at `http://localhost:5001`, with a blog of
   its own to try things on - your real blog isn't touched.
3. **Ask for what you want.** For example: "Add a reading list page
   where I can add books with a cover and a star rating", or "Show the
   weather where I am at the top of each post". The agent reads
   [CLAUDE.md](../CLAUDE.md), which tells it how this project is built
   and checked, so its changes follow the same rules as Soloblog's own.
4. **Look at it.** Open the address in your browser and try it. Ask for
   changes until it's right, then ask the agent to run the checks and
   save the change to your copy ("commit and push").
5. **Put it on your blog.** Point your host at your copy instead of
   Soloblog's - most hosts deploy from a GitHub repository you choose
   (see [DEPLOYMENT.md](DEPLOYMENT.md)). Download a backup first.
6. **Keep getting Soloblog's updates.** When a new version is out, ask:
   "Bring in the latest Soloblog from the original repository and keep my
   changes." The agent merges them and runs the checks.

**Agents that read a different file:** CLAUDE.md is the project's rules
for any agent - if yours looks for `AGENTS.md`, tell it to read CLAUDE.md.

**Something you'd like everyone to have?** Open an issue or a pull request
on the Soloblog repository - see [CONTRIBUTING.md](../CONTRIBUTING.md).

## Local setup

Requires Python 3.12+ (developed on 3.14, which the Docker image runs; CI
tests both). No Node.js anywhere.

Everything installs into the project's own virtual environment, `.venv`
(git ignores it), never into the system's Python:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate        # macOS and Linux
pip install -r requirements-dev.txt   # the app, the tests and the browser tools
python -m playwright install chromium firefox   # once: the browsers tools/phone_check.py drives
daisyft init --defaults --binaries --force   # once: downloads a Tailwind v4 + daisyUI v5 binary for your OS
daisyft build             # compiles static/css/input.css -> static/css/output.css
python app.py             # http://localhost:5001, auto-reloads on code changes
```

`--binaries --force` matters: the project's daisyft settings are already
committed, so a plain `daisyft init` asks whether to start the project
over, and stops without downloading anything if you say no. It records
the version it got in `.daisyft/daisyft.toml`; leave that change out of
your commits.

Activate `.venv` in each new terminal before running anything here. Only
the app's own packages are in `requirements.txt` (what the Docker image
installs); `requirements-dev.txt` adds pytest, the S3 stand-in the
storage tests use, and Playwright. Every version is pinned, the
packages those depend on too - so your machine, CI and the image run the
same code. Bump them deliberately; after one changes, `pip install -r
requirements-dev.txt` again.

`daisyft dev` rebuilds the CSS on every save. On Windows, set
`PYTHONUTF8=1` if `daisyft` fails with an encoding error.

**Rebuild CSS whenever you use a Tailwind or daisyUI class the codebase
hasn't used before.** Tailwind only generates classes it finds as
literal strings in the source, so a new class (or a class built by string
concatenation at runtime) silently does nothing until the next build.
`output.css` is generated and not committed.

## Project layout

```
app.py                starts it: python app.py
soloblog/             the app itself, one package
  app.py              app setup, middleware, the scripts bundled as /app.js and /admin.js
  js/*.js             every script, one file each: read by a FOO_JS constant
                      (js.read) and joined into /app.js (every page) or
                      /admin.js (only what the admin's pages use, listed in
                      ADMIN_SCRIPTS), or put inline with a nonce
  config.py           env vars and VERSION
  db.py               per-thread SQLite connections, migration runner
  migrations/*.sql    applied in filename order, once each (schema_migrations table)
  cache.py            one generation number; bumping it clears the settings and render caches
  ui/                 shared components, one file per area - all imported as
                      `from soloblog.ui import ...`, whichever file they're in.
                      A file imports only from the ones above it in this list:
    icons.py          the icons, as inline SVG
    base.py           spacing, widths and the small parts every area uses
                      (SearchBox, IconAction, RowActions, Tabs, Alert)
    forms.py          a settings page's parts: SettingsPanel, FormField, ToggleField...
    lists.py          an admin list's parts: ListHeader, ListToolbar, SaveBar
    pickers.py        the media and link pickers
    post.py           a visitor's page: a post's parts, side panels, SiteFooter
    nav.py            a visitor's header: Nav, search, the colour picker
    admin.py          the admin's frame: AdminSidebar, AdminTopBar, SETTINGS_GROUPS
    layout.py         Layout - the page every route returns - and ErrorPage
  routes/             one APIRouter per area
    public.py         homepage, posts (and /<lang>/post), tags, archive, wiki, feeds, comments, sitemap
    editor.py         post editor, preview, posts list, uploads from the editor
    admin_settings/   every Settings page - one router, shared by its files
      base.py         the router, the page's menu, the colour pickers
      saves.py        each page's field table and its save
      design.py       the Design pages: presets, own colours, the live preview
      panels.py       the forms on every other page
      integrations.py API keys, webhooks, the email test
      pages.py        which panels make a page, the search index, the page itself
    security_routes.py Settings > Security: password, two-step login, passkeys, sessions
    backup_routes.py  Settings > Backup and import, the cloud bucket, the disk panel
    help_routes.py    Admin > Help, from the files in docs/
    media.py          media library, stock photo search/import
    comments_routes.py moderation queue, mentions
    auth_routes.py    setup, login (password, 2FA, passkeys), logout
    fediverse_routes.py WebFinger, NodeInfo, ActivityPub actor/outbox/inbox, webmention endpoint
    stats.py, contact.py, welcome.py   stats, contact form + messages, first-run wizard
  posts.py            posts as markdown files + SQLite index/FTS search, wiki links, tags
  render.py           markdown -> sanitised html (cached), embeds, callouts, galleries, contents
  pages.py            the page around the writing - sections drawn in place, [[wiki links]], contents, folding, slides - and each section's drawing function
  sections.py         the registry of section kinds: names, options, sample words, what Insert writes
  gallery.py          ```gallery blocks
  editor_config.py    every editor command: name, icon, shortcut, slash words, toolbar order
  editor_icons.py     generated: the editor's Lucide icons (tools/editor_icons.py)
  post_templates.py   the built-in templates (sections, words, Post settings) and posts saved as templates
  actions.py, csp.py  data-on* event attributes; the per-response script nonce
  i18n.py, locales/   words visitors see, in 23 languages
  newsletter.py       subscribers, confirmation, sending
  crosspost.py        new posts to Bluesky and Mastodon
  extcomments.py      the seven outside comment systems
  captcha.py, ads.py  Turnstile/hCaptcha; AdSense and the consent banner
  sources.py, linkcheck.py   Stats' top sources and broken-link checker
  fonts.py, themes.py        font stacks; the daisyUI theme names
  updates.py          "a newer release is out", checked against GitHub once a day
  feeds.py            RSS, Atom, JSON Feed
  seo.py              titles, meta tags, article structured data
  cards.py            share cards: a post's title on the palette, drawn with Pillow
  fonts/              Noto Sans (SIL Open Font License) for the share cards
  comments.py         comments, threading, confirmation tokens
  images.py           uploads (WebP, audio, video), size copies, trash, alt text and credits
  settings.py         key/value settings with DEFAULTS, cached
  backup.py           zip export/inspect/restore
  importers.py        WordPress, Ghost, Medium, Substack and markdown-folder imports
  translate.py        machine translation, cached per post and language
  fediverse.py        ActivityPub: actor, objects, HTTP signatures, inbox, delivery
  webmention.py       webmentions received and sent
  publishing.py       announces posts to followers and linked pages, once each
  reactions.py, replymail.py, appicon.py, passkeys.py, totp.py, tz.py
  storage.py          optional S3-compatible bucket: SigV4 client, image
                      mirroring, automatic backups, restore on boot
  netguard.py         outbound requests go to public addresses only
  mail.py, notify.py, stock.py, formservices.py   other outside services
deploy/             proxy, Kubernetes, systemd, CapRover and Cloudflare Tunnel configs
static/css/input.css           Tailwind/daisyUI entry point + custom CSS
static/css/contrast.css        generated: readable text colours per theme
tools/theme_contrast.py        writes contrast.css (see UI conventions)
tools/editor_icons.py          writes soloblog/editor_icons.py from the commands' icon names
docs/*.md                      the guide, FAQ, deployment, development and sponsor pages -
                               also the admin's Help, each its own section (HELP_PAGES)
```

## How data is stored

- **Posts are markdown files** in `DATA_DIR/posts/*.md` (YAML front
  matter + body). The `posts` table and the FTS5 search index are only an
  index: `posts.reindex_from_disk()` rebuilds both from the files on
  every startup.
- **Everything else is SQLite only** (`DATA_DIR/blog.db`): the admin
  password hash, settings, comments, likes, view counts, image
  alt text/captions.
- **Uploads** are re-encoded to WebP (max 1600px) in `DATA_DIR/uploads/`,
  named after the file they came from plus four random characters
  (`images._new_name`). Beside them: `_trash/` (not publicly served),
  `_sizes/` (400 and 800 px copies, made on demand) and `_originals/` (an
  image's untouched original once it's rotated or cropped). A renamed
  upload's old name forwards to the new one (the `upload_renames` setting).
- **A picture's `sizes` says how wide it really shows**, so the browser
  picks a copy that's sharp there and no bigger (`images.srcset`). Words
  and galleries write the column's (`render.BODY_SIZES`,
  `gallery.SLIDER_SIZES`...); a Wide or Full section swaps them for its
  own (`pages._wider_sizes`). Something drawn another way - cropped to
  fill a tall screen, three across - writes its own.
- **Read the folders through `config.data_dir()`, `posts_dir()`,
  `uploads_dir()` and `db_path()`**, never `config.DATA_DIR` and the
  others directly: in the demo each visitor who changes anything gets a
  copy of their own (`demo.Sandbox`), and these point into it for their
  requests. (A module property did the same until Python 3.14's attribute
  cache skipped it and wrote into the shared folder - the demo's test
  caught it.)

`001_schema.sql` is the whole schema as of 1.0.0-beta. A change goes in a new
numbered file in `soloblog/migrations/`, starting at `019_...sql` (002-018
were folded into 001 before the public release, and the sites from
before have those names recorded, so they're never used again), and one that has shipped is never
edited. A database from the early development files
isn't upgraded - `db.run_migrations` says to start fresh and restore a
backup.

## UI conventions

The admin follows a small, deliberate set of rules. Keep new UI inside them.

- **The admin's frame.** An admin page has no site header or footer:
  `ui.AdminTopBar` is a thin fixed bar at every width (it's the
  `[data-site-header]` there, so what's measured from a header follows
  it). On a wide screen (`lg`) `ui.AdminRail` is the menu, fixed on the
  left under the bar, the page starts beside it (`lg:mx-0`), and Post
  settings docks straight after the page's column where the editor keeps
  50rem (`placePostSettings`, which sets `data-settings-docked` on
  `<html>` for Main's padding). Below `lg` the bar's menu button opens
  the drawer.
- **daisyUI components first.** Use the real component (card, tabs,
  collapse, modal, join...) and theme tokens (`bg-base-100`,
  `text-primary`, `border-base-300`). No hardcoded colors, so every one
  of the 35 themes works.
- **Text colours stay readable.** daisyUI's colours are made for fills;
  as text on the page many themes fall short. `input.css` points the text
  utilities (`text-primary`, `text-accent`, `text-success`,
  `text-base-content/50`...) at `--tx-*` variables, which
  `static/css/contrast.css` sets per theme to the nearest colour that
  reads at 4.5:1 on the page and on cards. In your own CSS, colour text
  with `var(--tx-primary)`, not `var(--color-primary)`. After a daisyUI
  update, run `python tools/theme_contrast.py` and rebuild the CSS;
  `tests/test_features.py` checks every theme.
- **Buttons** - one look per job, the same small size (`btn-sm`) and a
  leading icon on every worded one:
  - *Primary* (filled, `btn-primary`): at most one in a page's content -
    its Save, or where there's none, its one main action (New post,
    Download on Backup). In a dialog, or a card that has become a small
    step-by-step form (two-factor's "Turn on"), that step's confirm.
    `tests/test_features.py` checks every admin page.
  - *Card actions* (plain `btn btn-sm`): something a card does on its
    own, right away - Make a key, Add a passkey, Change password, Upload.
    At the card's foot on the right, status text on the left
    (`_action_row`). A page of such cards (Security) has no page Save.
  - *Quiet* (`btn-ghost`): Dismiss, Reset to default.
  - *Danger* (`text-error`, with its icon): removes or turns off, and
    asks first.
  - *Going somewhere else* is a link, not a button: `ui.GoLink` - words
    and an arrow ("Open Security →", "See what's left →"), where a card's
    buttons would sit.
  - *Row and card actions* are icons (`ui.IconAction`), below.
- **Touch screens get bigger targets, from one rule** (`touch-size` in
  input.css, on daisyUI's own size variables): every button, field,
  picker and tab 44px (Apple), menu rows 44px at 16px, checkboxes, radios
  and switches 24px, tag pills 32px with a 44px tap area, a link on its own in a list, cell or
  line 44px; fields' text 16px, or an iPhone zooms
  in when one is tapped. New daisyUI controls follow by themselves - don't
  add `pointer-coarse:` sizes of their own. Beyond it: the header bar 56px
  (`ui.TOUCH_BAR`), links that aren't buttons 44px tall
  (`ui.TOUCH_LINK`). A mouse keeps the denser sizes. `tools/phone_check.py`
  checks 44px on a touch screen.
- **On/off settings are `ToggleField`** - name and a short description on
  the left, a switch on the right. Checkboxes are for picking several
  things from a list.
- **A Post setting that follows a site setting is marked when a page
  sets it differently.** Its field carries the site's value
  (`data-site-value`: a choice's value, or "1"/"0" for a checkbox or switch)
  and sits in a `data-custom-field` that gets `data-changed` while it
  differs, which turns on its left-edge bar (`ui.CHANGED_BAR`, a border
  that's always there, clear, so nothing moves) and its `ui.ResetButton`
  (`FormField(custom=)`, `ToggleField(custom=, site=)` - `custom` is
  `None` for a setting with no site value, else whether it differs now).
  `CUSTOM_TAGS_JS` keeps them up as the field changes and
  `SettingsPanel(custom=n)` counts them in the heading ("Page · 2
  changed"). A choice is changed when it's set and isn't the site's
  value; Reset empties it. Reset is an icon (VS Code's way, its tooltip
  "Reset to default (On)"), on the label's line for a choice and before
  the switch for a switch - one line. A new Post setting with a site-wide
  value gets the same - no "Custom" word, no "On/Off by default" label.
- **The settings pages mark what's changed the same way:**
  `SettingsForm` (and the forms `autosaving()` makes) runs
  `_mark_changed`, which gives every switch, choice and checkbox list with a
  default its `data-default-value` - `presets.baseline()`: the starting
  style chosen last over `settings.DEFAULTS` - and a Reset. So a style
  just picked marks nothing; what's changed after it does. Reset puts the
  starting style's value back and it saves like any change there. What's
  typed has no default and isn't marked. An empty value that means a set
  of its own (`post_shows`) is read as the page reads it.
- **Ordering is `SortableList`** - a drag handle and up/down buttons per
  row, the order saved with the form as a comma list (the footer, social
  links, the editor toolbar).
- **Admin lists** share `SearchField` (filters as you type), `FilterSelect`
  (named in its own box, applies on change) and `ListHeader`: how many are
  shown and what they match, with Clear, and - once rows are selected with
  `RowCheck` - "N selected" with `BulkButton`s in its place.
- **Every admin page is one column wide.** Lists and forms share the
  column the editor writes in (`max-w-3xl`, beside the menu), so nothing
  jumps sideways going from one page to the next. A list doesn't widen
  to fill a big screen. `tests/test_fixes.py` checks.
- **A drop menu is as wide as its longest item** (`w-max`, its words on
  one line) - never a fixed width, never a minimum that leaves empty
  space beside the words. When it's too tall for the screen it scrolls up
  and down (`MENU_SCROLLS`, or `SCROLLS` with `data-scroll-hint`). A menu
  that isn't daisyUI's `.menu` is laid out as a column: as a plain block
  its buttons are measured side by side. Three aren't menus of this kind
  and keep a width: the phone's navigation drawer, a picker you type in
  (`ui.Combobox` - it would jump as the list narrows) and the writing
  session's own goal. `tests/test_fixes.py` checks.
- **Row and card actions:** `IconAction(icon, label, ...)` for each -
  an icon with a daisyUI tooltip, and its words in a phone's ⋯ menu -
  inside `RowActions(..., id=)`, which folds them into that menu below
  `sm`. More than three, and only the first two stay beside the row at
  any width - the rest go under a ⋯ at their end, so the two used most
  go first. Trash and delete pass `confirm=`. Tooltips are always daisyUI's
  (`tooltip` + `data-tip`), never `title=`.
- **Every admin list with page buttons** passes `Pagination(..., per_page=,
  total=)`, with `per = rows_per_page(its_default)` for its page size: a
  10 / 20 / 50 choice (`ui.RowsPerPage`) beside the page buttons, shown
  once there are more than 10 rows. `?per=` is checked by the
  `RowsPerPage` middleware (app.py) - anything but 10, 20 or 50 is
  ignored - and the last choice is kept per list in a `per_<list>`
  cookie, not a setting. A list's own default is used if it is one of the
  three, else 20. `tests/test_rows_per_page.py` covers every list.
- **Confirmations are inline, never popups.** Buttons sit on the right,
  the primary action (Save) rightmost, and the status just left of them:
  the row is `ui.STATUS_ROW`, the status `ui.STATUS_BESIDE`, which takes
  the free space and ends its words against the buttons - one too long
  takes its own line above them instead of a squeezed column on a phone.
  A script that writes into a slot changes only its colour
  (`paintStatus`, toast.js), so the slot keeps its place:
  - form saves return `SaveStatus(message)` into `#save-status`;
  - list actions redirect with `?toast=` and `showStatus()` (app.py)
    writes the message into the page's `[data-status-slot]`, which
    `PageHeader` provides;
  - every page should have a slot. The toast container is only a
    fallback for pages that don't.
- **Settings are pages of panels** (`ui.SETTINGS_GROUPS`, one page at a
  time). A panel is a `SettingsPanel` (collapsible, open/closed state
  remembered per browser) whose `key` is unique across the app - prefixed
  with its page's address. **One name for a page everywhere:** its address
  is a word of its title, the first unless that was once another page's
  address, which stays gone (Name and homepage is `?tab=name`; Comments
  and messages is `?tab=messages`), its
  panels are `name-…`, and its form saves to `/admin/settings/name`
  (`_register_saves` sends each page's address to the handler that knows
  its fields - `save_general`, `save_site`, `save_design`, `save_secrets`
  serve several pages). A test fails if a page, panel or save doesn't
  match. A page (`_pages` in `routes/admin_settings/pages.py`)
  takes panels by key from the forms that build them and wraps them in
  `SettingsForm(save_url, ...)`: switches, choices and pickers save the
  moment they change (`AUTOSAVE_JS` - just that setting, with Undo beside
  "Saved" in the panel's heading), typing waits for Save. `_setup(panel,
  state)` makes something set up once a closed row saying how it stands,
  saved together; `_together` keeps linked fields saving together without
  folding them; `Advanced(...)` puts rare ones at the page's foot. The
  Design pages (`DESIGN_TABS`) get `DesignPreview` beside them: the form
  as it stands goes to `/admin/design/preview`, kept a few minutes under
  a token the preview frame's address carries (`?design_preview=`), and
  `app.PresetPreview` shows it - only to the logged-in admin.
- **One place decides glass.** `glass_fill(settings)` returns the
  background classes for every header, footer, drawer, dropdown and dialog.
- **Words on a picture sit in `on_picture(settings)`'s box** - the
  theme's page colour and text, frosted with the same glass at 85%, as
  the homepage banner, a Hero, a full-screen cover, a picture card and
  a project card do. No dark fade with white words: a light picture, or
  one with words of its own, showed through them. A credit in a
  picture's corner keeps its own small dark chip (`images.CAPTION_OVER_CLS`).
- **Pickers attach to any field.** `MediaPickerButton(input_id)` and
  `LinkPickerButton(input_id)` fill a plain input. The post editor's own
  toolbar passes the EasyMDE instance instead, and the picker inserts
  markdown.
- **Copy stays short** and matches wording already used elsewhere
  ("Saved", "Discard", "Pick"). Buttons carry an icon. How to write it,
  and how to lay out settings: [Writing and settings](#writing-and-settings).
- **No inline event handlers, and every script carries the nonce.** The
  Content-Security-Policy (`csp.py`) blocks `onclick=` and any `<script>`
  without the page's nonce. Write `**on("click", "fnName", arg, EL)` from
  `actions.py` (it becomes `data-onclick` + `data-args`), with `fnName`
  a global function in `app.js` or the page's own script. Give every
  `Script(...)` `nonce=csp.NONCE`; JSON-LD data blocks don't need it.
  htmx never runs scripts inside swapped-in HTML, so anything a live
  update needs belongs in `app.js`. `ACTIONS_JS` (app.py) lists the other
  attributes: `data-confirm`, `data-copy`, `data-open-dialog`...
- **Words visitors see go through `i18n.t()`.** `i18n.t("Share")`, or
  `i18n.t("Read it on {site}", site=host)` with placeholders filled in
  after translating; `i18n.plural(n, "{n} post", "{n} posts")` for counts.
  Translations live in `soloblog/locales/<code>.json` - add the new English string
  to every file (a missing one just shows in English; `tests/test_i18n.py`
  lists what's missing). Admin pages stay English and don't need it.
- **Settings forms declare their fields.** A form with
  `data_declare_fields=True` sends the names of its fields, and the save
  handler stores only those (`settings.set_declared`), so a tab can leave
  a setting out without resetting it. `data_shown_for="field=value"`
  shows a block only while that radio or select has that value
  (`field!=value`: while it has any other).
- **Header dropdowns use the native `popover` API**, not daisyUI's
  `:focus-within` dropdown. Inside the header, `backdrop-filter` didn't
  render on nested dropdowns, and top-layer popovers avoid that.
  `[popover].dropdown-content` in `input.css` must keep `position: fixed`.
- **The site's spacing comes from one scale** (`pages.py`: `CARD_PAD`,
  `ITEMS_GAP`, `GROUP_SPACE`, `SECTION_SPACE`), by role: tight inside a
  group, wide between groups, so a page shows what belongs together.
  A section uses these, not a gap of its own. What follows a post is one
  group (`PARTS`), `PART_GAP` from the writing and each part
  `SECTION_GAP` from the next, both following Space - a part never
  carries a margin or a divider of its own. Reading text is `_prose()`
  (16 px on a phone, 18 px from a tablet up); text inside a card is
  `_prose(..., small=True)`. Page titles are `ui.TITLE_CLS`, a list's
  `ui.LIST_TITLE_CLS`.

## Themes

daisyUI's 35 themes are built into `output.css`; `tools/theme_contrast.py`
writes their readable-text lines to `contrast.css` (run it after a daisyUI
update). Custom colours (Settings > Style > Colours) live in the `own_themes`
setting and are CSS made at runtime: `themes.parse_theme` keeps only
daisyUI's 28 variables, each matched to a pattern, colours as oklch;
`themes.own_css` is on every page (`apply_site_config`). Anything that
lists or checks themes uses `themes.all_choices()`, `light_choices()`,
`dark_choices()` and `is_dark()` - never `DAISYUI_THEMES` alone - and
`theme_label()` for the name people see.

## Journeys

`journeys/` drives a real browser (Playwright) through what people do,
against a real server on a fresh, empty site: setting it up, writing and
restoring a post, a reader's comment from confirmation to approval,
members joining by email, the look, a backup and its restore, and the
same on a phone. They catch what reading the markup can't - a page that
fails only once some setting is on, a button something sits over, two
things that close at once. Any script error fails the journey.

    python -m pytest -q journeys

Email goes to an outbox folder instead of out (`MAIL_OUTBOX`, set only
by whoever starts the server - never in production), for a journey to
read as a person reads their inbox. A journey changes settings through
Settings, as people do, never straight in the database. Helpers -
signing in, writing, publishing, the outbox - are in
`journeys/conftest.py`.

## Templates, sections and Post settings

**A page is made of three things, and nothing else decides how it looks.**

- **A template** is a page ready to fill in: sections, sample words and Post
  settings. It is only ever a starting copy (`post_templates.py`) - a page
  keeps no tie to the template it started from, and nothing in the code asks
  which one it was.
- **A section** is one part of a page: a `##` with a `Section:` line under
  it, its items `###`. Any number, on any page. Every part of a page that
  isn't plain writing is a section.
- **Post settings** are the page's frame and kind - Title, Page width, Show
  as slides, In the wiki, Remind me to update, Link to, contents, cover,
  what shows around it. Every one works on every page. Which wins: a
  section's own `Key:` line, then the page's Post settings, then the
  site's settings, then Soloblog's default.
- **Nothing guesses parts from what's written.** A plain `##` is plain
  writing. A template may start a page with sections written out; the page
  never draws a part its own way.
- **A section looks the same on every page.** Its `Width:`, `Style:`,
  `Heading:`, `Space:` and `Appear:` lines, the site's
  section headings setting and the page's section spacing (`--section-gap`, from `pages.SECTION_GAPS`) and
  way of appearing (`data-reveal`) change it - not the page it's on.
- **A section sits beside the post's writing, not inside it.** The
  writing between sections is a `.prose` of its own and the whole post is
  `[data-post-body]` (`pages.prose_around_sections`) - so scripts that
  read the post look for `[data-post-body]`, not `.prose`. Under a
  `not-prose` the text styling can't be switched back on, so a section
  inside the writing lost its own words' links, lists and spacing. The
  page's section gap is for a page made of sections; on a page with a
  plain `##`, and after any writing, a section has a heading's room.
- **There are no page layouts, and a new kind of page is never one.** The
  pattern is: a Post setting, the places that check it, a template that
  switches it on and - if the pages need gathering - a built-in page. In the
  wiki is the example: the setting (`in_wiki`), what checks it (`pages._wiki_note`,
  the front page `/wiki`, the blog roll leaving the notes out) and the
  Wiki / notes template that switches it on. A podcast episode, an event or
  a product would be the same: a setting, its checks, a template, a page
  that gathers them - and sections for its parts.
- **A Post setting is listed once, in `posts.PostFields`** - its name and
  what a new post starts as. That one object goes from whoever is saving
  (`posts.write`, or `posts.save_post` for the demo and imports) to the
  row and the file, so a new setting is: a line there, how it's cleaned
  (`cleaned`), its column in `_save`, its line in `_write_file` and where
  the file is read back (`reindex_from_disk`). The editor's two forms fill
  the same object (`editor.SentPost`, which adds only what the form sends
  another way), so a new setting needs its field in the form and no line in
  `editor.save` or `editor.save_template`.

## Adding a section

A section (a `##` with a `Section:` line, user guide > Sections) works in
any post. Everything about a kind is one entry in `sections.REGISTRY`;
Insert, the `/` menu, the phone's + sheet, the editor's Help and
highlighting, the lines left out of excerpts and the page itself all read
it. Every kind, Key: line and value has one name, written one way:
another word people might use for a kind is one of its search words,
never a second name. A new kind needs, in one change:

1. **Its registry entry** in `sections.py`: its one name after
   `Section:`, what it is in one line, a Lucide
   icon (`editor_icons`), search words, its sample words (`heading`,
   `body`), the Key: lines it takes after Width, Style, Heading, Space and Appear (`options` -
   a new kind of option goes in `OPTIONS` first) and its default width.
2. **How it's drawn:** a `_render_<kind>` in `pages.py` that takes its
   `###` items as `##`s (the page gets them back as `<h3>`s) - every
   kind has one, however small; `draw` names it if it's called anything
   else. Follow Section design, below. Use the
   usual column classes (`sm:grid-cols-2`, `lg:grid-cols-3`...) - `_FIT`
   turns them into container queries so its cards fit a post's column; a
   class it doesn't know needs adding there. Draw the words before the
   items with `pages._intro`: it marks them for `Heading: Centred`. Read an option with
   `sections.take_line`, which gives "" for `Default`.
3. **Words:** anything a visitor reads that the section adds itself goes
   through `i18n.t()` and into every translation file.
4. **The user guide's table** in Sections, and a use of it in the demo's
   Every section page (`demo._sections_page`).

Three things a kind may add to its entry: `styles`, `Style:` values only it
has (the Hero's `Window`) - the `/` menu lists them for that kind alone and
the editor underlines them on any other - `cover=True`, for `Style: Cover`
(Hero, Call to action, Image and text: words over an image means
something there; on any other kind it is ignored and underlined, and the
list is that one argument) - and `own_heading`, when it draws
its `##` itself (Profile's is the person's name, big): its renderer reads
the heading from `out["heading"]`. Lines of a kind's items written straight
under its `Section:` line (Project facts' `Client:`) aren't options; they
stay words, in excerpts, feeds and translations (`sections.split_own`).

A new Key: value (a `Show as`) is an `OPTIONS` entry: its values with
what each does, what `Default` means for it, how it's checked. Every one
takes `Default`; the editor's menu, underline and faded line follow.

**[TEMPLATES.md](TEMPLATES.md)** lists what each template sets and what each
section reads and draws. A new section or template gets its entry there in
the same change; a test checks every one has it.

### Section design

Every section is built from the same few sizes, each named once in
`pages.py`. A size written by hand in one section is how they drift
apart, so a test fails on one.

| | Use | Is |
|---|---|---|
| A section's title | the page's `<h2>` | the theme's own heading |
| An item's title - a card's, a column's, an entry's | `ITEM_TITLE`, in an `<h3>` | 18px, semibold |
| The one item a section makes big (a bento's first tile) | `LEAD_TITLE` | 24px, semibold |
| Inside a card | `CARD_PAD` | 20px, 24px from a tablet up |
| Inside a panel - a whole section on a card, a tile of words | `PANEL_PAD` | 24px, 32px |
| Between cards or entries | `ITEMS_GAP` | 24px, 32px |
| Between tiles or rows that read as one block | `TIGHT_GAP` | 16px |
| A gallery's tiles | `GALLERY_GAP` | as cards, with room under each for its title |
| A card at rest | `SHADOW_REST` | a small shadow |
| An image or card that stands off the page | `SHADOW_RAISED` | a large one |

- **Headings:** a section's title is the only `<h2>` in it. Everything
  under it is an `<h3>` - `pages._items_as_h3` sees to it, so a screen
  reader's outline is the same on every page. No `<h4>`.
- **The smallest text is `text-xs`** (12px): a credit, a label, a date.
- **Images** take their shape from the section (`aspect-[4/3]` for a
  card's, `aspect-square` for a face), never from the file.
- The sign-up box and the contact form are the site's own, the same here
  as on their own pages.

`tests/test_sections.py` checks every entry is whole, that every name
still means what it did, that `Default` renders like a missing line and
that what Insert writes shows nothing but the section.

## Writing and settings

Every label, heading and line of help in the admin - Settings, Post
settings, Media - follows these rules, and so does every new feature's
settings. They come from how Ghost, Notion and Atlassian design for people
who aren't developers.

### Who we write for

Someone running their own site who isn't a developer and doesn't care
what happens behind the scenes. They scan the page for the setting they
came for, read its label, and maybe one line under it. Give them what
they need to decide, and nothing else.

Not a developer doesn't mean new to computers. They use the web every
day and know its words - a URL, an image, bold, a password manager - so
plain means leaving out the machinery, not those words.

### Labels

- **Name the thing, in their words.** "Time zone", "Cover image",
  "Comments". A word they'd type into search.
- **A switch says what's on when it's on:** "Let readers pick other
  colours", not "Visitor theme switching".
- **Sentence case, no full stop.** Verbs for actions ("Connect Stripe"),
  nouns for things.
- **The same idea has one name everywhere** - in a label, a heading, a
  button and the guide.

### Standard terms

- **Use the term people already know**, the one other apps, the
  standards and a search use: "URL", "Bold", "Placeholder",
  "Two-factor authentication (2FA)". Never a home-made paraphrase of it
  ("address", "Makes words stand out", "the words in grey", "a second
  step when you log in") - it makes people work out what we mean, and
  they can't search for it.
- **The test:** would Ghost, WordPress, Notion or Google Docs say it, or
  would someone type it into a search? Then it's a term, not jargon.
- **Common abbreviations stay short:** URL, RSS, HTML, CSS, DNS, HTTPS,
  API, SEO. A less common term gets a few words or a link once, where
  it first comes up: "Webmentions - replies and mentions from other sites".
- **Jargon only a developer knows stays out** - caches, requests,
  endpoints, payloads, "renders" - unless it must be typed (an
  environment variable, a DNS record, a key's prefix), and then it's
  written exactly.
- **Terms are names, not a style.** The sentence around a term stays
  short and plain.

| Instead of | Write |
|---|---|
| address (of a page or a site) | URL, or link |
| picture | image |
| words (of a post, a caption, a block) | text |
| the words in grey | placeholder |
| Makes words stand out, Crosses words out | Bold, Strikethrough |
| a second step when you log in, two-factor login | two-factor authentication (2FA) |
| bring back | restore |
| fold, foldable | collapse, collapsible |
| tick (a box) | select; a tick as a symbol is a checkmark |
| moves by itself | autoplay; sent or published automatically |

"Address" stays for an email or a postal address.

### Help text (the grey line)

- **One line, and only when the label isn't enough.** Most switches need
  none. Don't restate the label.
- **What it does for them or their readers - not how it works.** No
  caches, scripts, requests, storage, "loads", "renders", "fetches".
- **No reassurance about things people already expect.** Not "Nothing is
  lost", "You can turn it back on any time", "Nothing is saved until you
  click Save", "Each one is checked first". Off is reversible, Undo
  undoes, Save saves.
- **No directions around the admin.** If something must be set up first,
  say so with a link to it ("[Set up email](...) first"), and only while
  it isn't set up. Never "(Integrations > Email)" in running text.
- **A post's "(default)" says what this post gets.** A choice that
  follows the site names what the site gives *this* post or page - "Off
  (default)" where Settings leaves its kind out - never the site's value
  regardless. Whatever Settings turns off for it (comments for the whole
  site, a checkbox under Show that needs setting up) says so beside it, with
  a link to that setting (`editor.SiteTurnsOff`), only while it's so.
- **A dropdown lists each choice once.** The site's is the "(default)"
  entry, which follows the site, and isn't listed again on its own -
  two "Off"s read as a mistake. A test checks every dropdown in Post
  settings.
- **Codes from other services: one short line and a link** - "From
  AdSense, under Account information". Not the click path plus what the
  code looks like.
- **No "Optional."** An empty field is optional. Say "Required" on the
  rare one that isn't.

### Options

- **A name, then a few words:** "Cards - each post with its image". If a
  choice is visual, show it (an image, the font itself) instead of
  describing it.
- **"(recommended)" only where getting it wrong would hurt.** Otherwise
  the default already is the recommendation.

### Headings and sections

- **Short nouns people would search for:** "Comments", "Newsletter",
  "Fonts". A heading names what's in it, never a mood ("Make it yours").
- **No two places for one idea.** A setting lives in one section; if it
  belongs in two, it's one switch shown in both, saving to the same place
  (Each post shows and the Newsletter's "under each post" are one setting).

### Tone

Practical and direct, like a helpful colleague. Calm and specific where
people may be worried (security, payments, deleting). Warm is fine; jokes
aren't - a setting is read many times. Status messages and tooltips have
no full stop: "Saved", "Copied".

### Layout: keep settings short

- **A page fits in about three screens.** When a section grows past that,
  split it (its own entry in the settings menu), or fold the rarely
  changed part under **Advanced** at the foot.
- **Simple settings are rows:** the label and one line on the left, the
  control on the right (`ToggleField` for switches).
- **Things set up once are a summary that opens** (Ghost's pattern): one
  row with the name, the current state ("Off", "Plausible · your-site.com",
  "Stripe · test mode") and Edit, which opens its fields in place with
  Cancel and Save. Sending email, analytics, ads, paid members (Stripe),
  translation, the spam check, sharing to Bluesky and Mastodon, stock
  photos and the Update now button.
- **What few people need goes under Advanced**, at the foot of its page:
  redirects, search engine verification, the home screen icon, webmentions,
  custom code, the environment. Folded, each is the same
  row as a set-up group - name, current state, Edit (Show for the
  environment, which can't be changed here) - so every folded group looks
  alike, whether it saves as it changes or with Save.
- **More than about a dozen choices is a picker, not a dropdown:** the post
  picker for a post or page, the media picker for a file, a searchable box
  for long lists (time zone, language, currency), a gallery with images
  for templates, starting styles and fonts. Never a long `<select>` of posts.
- **Dropdowns look alike.** A short `<select class="select">` is fine to
  write: SELECT_JS (app.py) gives it the same styled list as a
  `ui.Combobox`. A list that opens from a field is at least as wide as the
  field; a menu from a button (⋯, More, the header's) is as wide as its
  contents. Both fit the window and stay with what opened them
  (`placeMenu`).
- **One section at a time.** The settings menu shows one page; search
  covers all of them.
- **Switches and choices save as they change; typing waits for Save.**
  Don't make anyone press Save for a switch, and don't save half-typed
  text.
- **Dangerous actions last**, apart from the rest, and they ask first.

### Before you add a setting

1. Does it need to be a setting? A good default beats an option.
2. Where would someone look for it? Put it there, and only there.
3. Write the label, then decide whether it needs a help line at all.
4. Read the page as the person above would: what can they skip? Cut it.
5. Does the page still fit? If not, fold or split before adding.
6. Give it a default in `settings.DEFAULTS`, and a line in its page's
   field table in `routes/admin_settings/saves.py` (`DESIGN_FIELDS`,
   `GENERAL_FIELDS`, `SITE_FIELDS`, `PROFILE_FIELDS`, `SECRETS_FIELDS`)
   saying how a form's value is cleaned - `flag` for a switch, `one_of`
   for a choice, `some_of` for selected checkboxes, `text`, or a stricter one.
   Anything not allowed is saved as the default. Saving, the Design
   preview and the Default tag all follow from that line; a test fails
   if a page shows a setting its table doesn't have.

### The user guide

The guide is written by task, the way Ghost's Help Center and Apple's
user guides are: people come to Help with something to do ("schedule a
post"), not to learn a feature. [Writing posts](guide/writing.md) is the model -
read it before writing a page.

**Where things go.** One file per group in `docs/guide/` (Getting started,
Writing posts, Creating pages, Designing the site, Growing an audience, Running the site,
How a site is put together, Sections and templates, Privacy and how it works,
Reference), each a page in Help (`HELP_PAGES`,
`ui.HELP_GROUPS`), with Troubleshooting beside the FAQ. Each task is a
`##` in its group's file; `docs/guide/README.md` lists the groups for
GitHub. A new feature gets a task in the group where someone would look
for it, and its options a line in the Reference - or, for a new section or
template, its own entry in Sections and templates, in the same shape
as the others, and its Key: values in the index there (tests check every
section and template has one).

**Kinds of page, written differently** (the Diátaxis split):
- **Getting started** teaches: one path from nothing to a working site.
- **The task groups** get one thing done.
- **The Reference** lists every option, one line each - every Settings
  page in admin-menu order, then Post settings, galleries, markdown and
  shortcuts. Lists of options live only here and in Sections and templates.
- **Sections and templates** is the dictionary of sections and templates:
  one entry for each section (what it's for, how to write it, its Key:
  values, what it does by itself), a table of every template, then an A-Z
  Key: value index.
- **How a site is put together** and **Privacy and how it works**
  explain why - how styles, templates, sections, Post settings and Key:
  values fit and which wins; privacy, email, where posts are kept. No steps, no lists.

**A task page:**

```markdown
## Schedule a post

Write now, and have the post go live by itself later.

1. In the editor, open **Settings**, then **Publishing**.
2. Set **Publish at** to the day and time. **Published** switches on by
   itself.
3. Select **Save**.

The post shows as **Scheduled** in **Posts and pages** and on the
**Calendar**. It goes live at that time, in your site's time zone.

**Change your mind?** Clear **Publish at** to publish now, or switch
**Published** off to keep it as a draft.

See also: [Write and format a post](#write-and-format-a-post)
```

- **Title:** a verb and the goal, in the reader's words - "Add images
  and galleries", "Restore an earlier version". Never a feature name
  alone ("History"), never a question.
- **First line:** what you'll get, in one sentence. No "This section
  explains".
- **Steps:** numbered, two to seven, each starting with a verb. More than
  seven is two tasks. Name every button, tab and field exactly as the
  screen shows it, in bold; a menu path is one bold span with `>`
  (**Settings > Editor > Focus**). Say what happens by itself, so nobody
  does it twice ("**Published** switches on by itself").
- **After the steps:** what you'll see, then the one to four questions
  people ask next, each a short bold question and its answer in a
  sentence or two ("**Wrong time zone?** Change it in ..."). These carry
  the options and edge cases that would clutter the steps.
- **See also:** two or three links, only where they help. Link rather
  than repeat - a thing is explained in one place.
- **Length:** a screen or two. If it's longer, it's two tasks, or the
  rest belongs in the reference.

**Write for someone who has never opened Soloblog.** They don't know how
the app works, so don't make them work it out from a compressed line.
Say what a thing is before what the screen does with it; say when
something appears and what each button is for; use everyday words
("bottom", "its current state") over shorthand ("at the foot", "how it
stands"). Everyday words aren't a reason to avoid a standard term
([Standard terms](#standard-terms)): say "URL", and explain a less
common term once, where it first comes up - new to Soloblog isn't new
to the web. Clear beats short - an extra sentence is fine if it saves
someone from getting lost.

> Not: What you type saves with **Save**, which shows at the foot of the
> screen, with **Discard**, while there's something unsaved.
>
> But: When you type something, a **Save** button shows at the bottom of
> the screen, with **Discard** beside it to throw away what you've typed.

**Sentences:**
- "You" for the reader; present tense; active voice. Short sentences, one
  idea each.
- Device-neutral verbs: select, open, choose, switch on, type, press (for
  keys). Never click or tap - except where the gesture matters ("press
  and hold", "swipe along").
- Shortcuts in bold after the button, or in brackets: **Ctrl+S**,
  **Preview** (Ctrl+Alt+P).
- What it does for them, never how it works: "Big images are made a
  sensible size", not the pixel limit. No machinery, no reassurance, no
  "simply", "just" or "easily".
- The same word as the screen and the rest of the guide for the same
  thing. If the app says **Copy URL**, so does the guide.

**Every step is checked against the code** before it's written - the
label, where it is, and what happens. If a step is wrong, the guide is
wrong, however well it reads.

**Links:** within a file, `#anchor`; to another group,
`writing.md#anchor`; to the hosting guide or FAQ, `../DEPLOYMENT.md#anchor`. The guide was
one long page until the first public release; nothing links to that page any more, and
`test_nothing_links_to_the_old_single_guide` keeps it so.
Help turns them into its own links. `test_help_links_lead_somewhere`
fails on any link to a heading that isn't there - rename a heading and
fix its links in the same change.

### Help's other pages

The same sentences, menu paths and verbs as the guide, in the shape each
kind of page needs:

- **Common questions** (`docs/FAQ.md`): the question as a `###`, in
  the reader's words, without a full stop. The answer first - "Yes",
  "No", "Usually not" - in two to five lines, then a link to the task
  that has the steps. No steps here.
- **Hosting and deploying** (`docs/DEPLOYMENT.md`): how-tos, like the
  guide's tasks - a verb title, numbered steps naming the host's own
  buttons, then what to check. Settings people must type (`BASE_URL`,
  `/data`) stay as they are, in code. What the guide already covers
  (backups, updating, troubleshooting) is a link there, not a copy. A
  host's steps are checked against its own current docs, since our code
  can't check them.
  **Every way of hosting says what it costs** - a **What it costs:** line
  first: paid or free, what for, and why a free plan won't do (no disk
  that's kept, a site that sleeps) - so nobody finds out from a bill. No
  prices: they change, so point to the host's own page.
- **The API** (`docs/API.md`): reference for people who write code -
  tables, requests and answers, technical words where they're the exact
  ones. Names of keys, settings and buttons are the app's own.
- **What's new** (`CHANGELOG.md`): its own rules, in CLAUDE.md > Every
  change.
- **Sponsor** (`docs/SPONSORS.md`): plain and short; no pressure.

## Custom CSS

Soloblog's look comes from daisyUI's components and theme tokens; custom
CSS in `static/css/input.css` is the exception, and needs a real reason
and the maintainer's OK ([CLAUDE.md](../CLAUDE.md)). Each override
is listed below and tagged in `input.css`
with its name - `[custom-css: name]` in the comment above it, on every
rule it covers - so it can be found and taken out again. `tests/test_features.py` fails if the list
and the tags disagree.

- **Adding one:** the maintainer's OK, a row here, the tag on its comment.
- **Reverting one:** delete the rule and its comment from `input.css` and
  its row here, run `daisyft build`, and check the page it was for - the
  last column says what comes back.

| Name | The rule | Why | Reverting restores |
|---|---|---|---|
| `menu-focus` | `.menu` items (`li > a`, `li > button`, `li > summary`) on `:focus-visible`: `outline: 2px solid currentColor`, `outline-offset: -2px` (inside the row); `.btn-ghost:focus-visible`: the same, `outline-offset: 2px` | With the keyboard, daisyUI shows focus on a menu item or a ghost button only as a faint tint, about 1.1:1 - WCAG 2.4.7 (Focus Visible) fails. A ring in the text colour, never on a mouse click; a menu row's sits inside it so a scroll box doesn't clip it | Focus shown only as a faint tint on menu items and ghost buttons |
| `tooltip-on-top` | `.tooltip` while pointed at or focused, and its bubble (`.tooltip-content`, `::before`, `::after`): `z-index: 100` | daisyUI puts a tooltip's bubble one layer up (z-index 1), so a sticky bar, a card, a join's focused button or the editor beside it covered the words. Lifted above the page, below an open menu (999) and dialogs | Tooltips hidden under what's beside them |
| `editor-blocks` | `.CodeMirror-line.sb-section`, `.sb-setting`, `.sb-block` in the editor: a tinted background and a 3px coloured left edge; `.sb-default`: a setting left at Default, its words at 0.6 opacity | The editor only colours words, so a `Section:` line, its settings and the one-line blocks (Buttons:, Pull quote:, folds, galleries) looked like any other text. Main colour for a section, a fainter one for its settings, grey for blocks | Sections and blocks written as plain lines in the editor |
| `touch-size` | `@media (pointer: coarse)`: daisyUI's `.btn` (not `-lg`/`-xl`) `--size` 44px (a setting's Reset, `[data-custom-reset]`, with `margin: -0.625rem`, so its 44px reach past the 24px it takes in its row), `-xs`/`-sm` text 14px; `.input`/`.select` 44px; `.input`/`.select`/`.textarea` text at least 16px; `.tabs` 44px; `.menu` rows at least 44px at 16px; `.checkbox`/`.radio`/`.toggle` 24px; a `.badge` that's a link or button 32px to look at and 44px to hit (its tap area reaches 6px above and below, and a 6px margin keeps the next row's clear; one marked `data-tap-area`, among pills you only read, keeps their size and reaches 44px past its edges); what opens a fold (`summary.collapse-title`, `summary.link`) and a link on its own in a list item, table cell or paragraph 44px; a row's ⋯ menu items 44px at 16px | Measured on a phone, most controls were under the 44px touch target (Apple; WCAG 2.5.5): 24-36px buttons and fields, 25-33px menu rows, 16-20px choices - in pages, panels, dialogs and menus alike. Fields' 14px text made an iPhone zoom in on every tap. One rule on daisyUI's own size variables, so everything follows - a mouse keeps the denser sizes | daisyUI's sizes on a touch screen |
| `story-scroll` | `@keyframes story-words` and `story-words-phone`, and where `animation-timeline: view()` is supported, a view timeline per Story step (`[data-story-step]`) driving its words (`[data-story-words]`) - opacity and a 32px drift, with stops for a phone's step and a wide one - for a Story that MOTION_JS has marked live (`[data-live]`); without it, `[data-active]` steps show their words and the others' fade (a transition); `html[data-story-snap]` (MOTION_JS, only while a live story fills the window from top to bottom, so the sections around it scroll freely - and only under a finger, `@media (pointer: coarse)`: a mouse wheel's turn that stopped short of halfway was pulled back) `scroll-snap-type: y proximity`, each live step `scroll-snap-align: center` - the page settles on a step near one; the picture going shrinks as it fades, by Tailwind classes | Words faded from a script lagged a frame behind Chrome's own scrolling - it felt rough. The browser ties them to the scroll itself. Nothing but a keyframe can fade a picture in from a hair larger without the one leaving doing it too. | The words of a Story all showing at once, and the picture changing with no settle |
| `section-reveal` | `@keyframes reveal-*`, `[data-reveal]` (on `<html>` for the site's, on a section's wrapper for the page's or its own `Appear:`) setting `--reveal`, and `.reveal-item` hidden until MOTION_JS marks it `data-revealed` | Sections appear (Settings > Style > Motion, a page's Post settings, a section's `Appear:`): Rise, Zoom, Slide left, Slide right, Slide both ways (even sections from the right), Focus and Tilt need keyframes of their own. `--reveal` is inherited, so the nearest `data-reveal` wins - one rule per value instead of one per level. Played once as a section scrolls in - tied to the scroll bar, only Chrome showed them. MOTION_JS also marks the pieces (`pieces()`): a section that's a grid of cards hands `reveal-item` to each card, so they arrive in turn (90ms apart, seven at most); plain writing between sections is marked block by block; and a heading shows with the section under it. Hidden first only while the script runs (`html.js-reveal`); each keyframe has only a "from", so nothing stays transformed once a section is in place. | Sections that all just fade in |
| `animations-off` | `html:not([data-animate]) :is(*, *::before, *::after):not(.loading)` - transitions and animations end at once | Settings > Style > Animations off left most motion on: only the scripts written to check it (folding, the side panels) stopped - drawers, menus, fades and the editor's sheet still moved. One rule covers every one, and any added later. | Animations that keep moving with Animations off |
| `classic-menu-buttons` | `.editor-toolbar button[data-section]` - width to fit, a small arrow | Classic menus' Text ▾ Blocks ▾ ... need their names on them; the toolbar's buttons are square icons otherwise (it replaced the heading menu's rule, which did the same) | Menu names cut off in square buttons |
| `classic-menu-edges` | `button:is([data-section], [data-rest]) > .easymde-dropdown-content { left: 0 }` | The button centres what's in it, so its menu was centred on it too - and ran off the left edge of a screen just wider than a phone. `placeMenus` moves a menu back in from either edge. | The Text menu running off the screen's edge |
| `section-rest-buttons` | `.editor-toolbar button[data-rest]` - 1.125rem wide, a small arrow | The ▾ after each Icons section, for the rest of it: an arrow, not a full button | A full-width square around each ▾ |
| `focus-typewriter` | `#post-form[data-typewriter] .CodeMirror-fullscreen .CodeMirror-lines { padding-bottom: 50vh }`, from 40rem | Typewriter scrolling keeps the line you're on mid-screen: the end of a post needs room below it to come up that far | The last lines stuck at the bottom in Focus mode |
| `focus-fade` | `#post-form[data-fade="paragraph"] .CodeMirror-fullscreen .CodeMirror-code > :not(.cm-para-now)`, and `[data-fade="sentence"] .cm-dim` - opacity 0.35 | Fade: the paragraph or sentence you're in at full strength in Focus mode. CodeMirror's lines aren't ours to put classes on in the HTML | Everything at full strength |
| `focus-toolbar-slide` | Focus mode: the text runs the full height (`.CodeMirror-fullscreen { top: 0 }`), with the bars and the toolbar lying over its top - `padding-top` leaves them the room, in the writing and both previews; the bars a layer up (37, 38) | The faded toolbar and bars left an empty band and covered the text; lying over it, they can slide away and the text never moves | The text starting under the bars, the band left empty |
| `focus-text-size` | `html[data-focus-mode] :is(.CodeMirror-fullscreen, .editor-preview-side) { font-size: calc(var(--editor-fs) * var(--focus-scale)) }` | Focus mode's A- and A+: the writing larger or smaller there, remembered in the browser - and the preview beside it, so the two stay the same size | Focus mode always at the post's own size |
| `focus-caret` | `#post-form[data-caret] .CodeMirror-fullscreen .CodeMirror-code { caret-color }`, and `.CodeMirror-cursor` 2px - `var(--color-primary)` | Coloured caret (Settings > Editor > Writing): the caret in the palette's colour in Focus mode - the browser's own with spell check on, CodeMirror's (thicker) with it off | The caret in the text colour |
| `focus-quiet` | `.EasyMDEContainer[data-typing]` - the toolbar and (with Only your text) both bars slide up and fade out whole, `pointer-events: none`; `.editor-focus-dot` shown at 0.6 meanwhile; reduced motion: no slide | While you type in Focus mode nothing covers the writing; the save dot stays in the corner, a session's line along the top | The bars staying while you type |
| `selection-column` | `.CodeMirror-lines > div { overflow-x: clip }` | CodeMirror draws a selection's whole lines out to the box's edge, past the writing's column | A selection running out past the text |
| `tooltip-delay` | `.tooltip:hover` (not keyboard focus) - `transition-delay: 400ms` on the tooltip and its arrow, on screens with a mouse | daisyUI's tooltips showed the moment the pointer touched an icon, so moving across a row of them flashed every name; 300-500ms is the usual wait. The keyboard still gets it at once | Tooltips showing instantly under the mouse |
| `component-contrast` | `.label`, `.fieldset-label`, `.stat-title`, `.stat-desc`, table headers -> `--tx-muted-60`; `.menu-title` -> `--tx-muted-40`; inactive tabs -> `--tx-muted-60`; `.badge-soft.badge-<colour>` -> `--tx-<colour>`; field placeholders -> `--tx-muted-60`; disabled buttons and fields -> `--tx-muted-40`; disabled toggles, checkboxes and radios at 60% opacity | daisyUI mixes these components' quieter text itself, past the per-theme readable colours (`contrast.css`): a soft Published badge read 1.9:1, menu headings 2.5:1, the dim theme's help lines 3.9:1 - axe-core flagged 36 pages. Same colours, moved only where a theme falls short of 4.5:1. Placeholders were 2.3:1 at worst (retro) and disabled buttons 1.3:1 | daisyUI's fainter labels, tabs, headings and soft badges |

**From before the list.** The rest of `input.css` was written before
it. Each rule has a comment saying why, in these groups: the header's
popover menus; frosted glass (blur, fills, dialogs and drawers); tabs
folding under More and a row's ⋯ menu; menus the browser draws (select
pickers); Tailwind Typography in the palette's colours; the post editor
(EasyMDE and CodeMirror - the toolbar, the bar over the text, focus mode,
the phone bar and its sheets, the writing's font and colours, the
preview); code highlighting in theme colours; the post extras (callouts,
task lists, diagrams, highlights and the rest); text size, smooth
scrolling and the page animations; the table of contents and reading
progress; Isso comments; and printing a post. A change to any of them
goes in the list above.

## Removed daisyUI rules

Some daisyUI rules are taken out of the stylesheet as the app serves it
(`themes.served_css()`, at `/static/css/output.css?v=<hash>`):
`output.css` is built as daisyUI makes it, then `themes.lean_css()` drops
the selectors that match `themes.REMOVED_RULES`. A rule left with no
selectors goes; one that also has others keeps them. Only a selector with
a `:has()` in it can go. Done there, not after `daisyft build`, so it's
the same in Docker, CI and on your computer.

**Why.** Each of these has a `:has()` that isn't on the element it styles
(`.toggle:has(:checked) > :nth-child(2)` styles the child, not the
toggle). With any one of them in the stylesheet, Chrome restyled all
4,500 elements of the editor page on every change - so every key typed
cost 63 ms on a fast desktop and 290 ms on a phone-speed CPU (measured
with `Emulation.setCPUThrottlingRate` 4). Each is for something
Soloblog doesn't use, so nothing on screen changes.

`tests/test_features.py` fails if any of them is in what's served, if
one is no longer in daisyUI's build (an update renamed it - find its new
name, or it would come back unnoticed), or if the rules we moved off
`:has()` come back.

- **Bringing one back:** delete its entry from `REMOVED_RULES` and its
  row here, restart the app, and check what its last column describes.
  Before using one of these daisyUI features, bring its rules back first.
- **Adding one:** only for a rule measured to slow the page, and only for
  a feature we don't use - a row here, an entry in `REMOVED_RULES`.

| Name | The rules (daisyUI 5) | What they did | Why it's safe without them |
|---|---|---|---|
| `toggle-wrapped` | `.toggle:has(...)` - `:checked > :nth-child(2)`, `:nth-child(3)`, `:focus-visible`, `> input:checked` and its `::before` | A toggle written as a `<label class="toggle">` around its checkbox, or with icons inside that swap when it's on | Every toggle here is the checkbox itself (`Input(type="checkbox", cls="toggle")`), styled by daisyUI's other toggle rules |
| `field-wrapped-disabled` | `.input:has(> input[disabled])`, the same for `.select` and `.textarea`, and their `::placeholder` | A disabled field inside a `<label class="input">` wrapper: the wrapper faded, not-allowed cursor | No disabled field sits in a wrapper; a plain disabled `.input` still fades |
| `filter` | `.filter:not(:has(...)) ...` - the filter component's two rules | daisyUI's filter: a row of radio buttons with a reset that hides the others once one is picked | We don't use the filter component |
| `theme-controller` | `:root:has(input.theme-controller[value=NAME]:checked)` in each of the 35 themes | A palette switched by ticking a checkbox with `theme-controller` | Palettes are switched by `data-theme` on `<html>`; each theme's `[data-theme=NAME]` rule stays, and your own colours are our own `[data-theme]` rules |

**Our own rules stay off `:has()` too**, for the same reason - write a
sibling rule (`peer-*`, `~`), the element's own state (`:only-child`), a
class set where the page is made, or an attribute set by a script. Moved
off it: the search box's clear button
(`peer-placeholder-shown:hidden`), Settings presets' "One of your pages"
(`data-shown-for`), a section's lone card (`[&_.grid>:only-child]`), the
phone bar's buttons (`.editor-phonebar-scroll ~ button`) and tooltips
while a menu is open (`html[data-popover-open]`). Then the rest:
Back to top above a sound or the save bar (`html[data-sound]`,
`html[data-unsaved]`), what follows a side panel beside the text
(`html[data-side-beside]`), Focus mode's bars while you type
(`#post-form[data-typing]`, set only when it changes) and in Focus mode
(`html[data-focus-mode]`). A `:has()` on the element being styled
(`.list-row:has(> .x)`) didn't slow the page. What's left is daisyUI's
own tooltip, tab and dialog rules, about 0.1 ms each.

## The admin's login

Everything under `/admin` is behind the login before a route runs
(`guards.admin_guard`, fast_app's `before=`): a page goes to the login, an
htmx swap navigates there, and a script's `fetch()` gets a 401 it can read.
So an admin route doesn't check for itself - put it under `/admin` and it's
protected (`test_every_admin_address_needs_the_admin` checks them all). The
one exception is `guards.ADMIN_OPEN`. A route elsewhere that's for the admin
only (a reply to a comment on the post page) calls `require_login` itself.

## Errors and logging

- **Log, don't print.** Each module has `log = logging.getLogger(__name__)`;
  `app.py` sets the format once, and `LOG_LEVEL` how much is kept. A
  problem someone may need to know about is `log.warning`; something that
  went fine but is worth a line (a migration, a restore) is `log.info`.
  `print` is only for command-line tools and the setup instructions shown
  when the server starts.
- **Catch what you expect.** Name the errors a call can raise -
  `images.IMAGE_ERRORS` for reading an image, `OSError` for a file.
- **At the edge, catch everything - and say so.** A call to another server
  (urllib, TLS, JSON from a stranger) can fail in more ways than can be
  listed, and a site run by someone who isn't a developer mustn't break
  over one. There `except Exception as e` is right, with a `log.warning`
  of what failed. A background thread's loop does the same with
  `log.exception`, so one bad job never stops it and its traceback is kept.
- **Never swallow silently.** An `except` that only passes or returns a
  default either expects that error by name, or logs it.

## Gotchas

- **FastHTML's static route catches common extensions first.**
  `fast_app()` registers a catch-all for `.xml`, `.txt`, `.webp` and more
  ahead of your routes. Any dynamic route ending in one of those
  (`/sitemap.xml`, `/uploads/{filename}`) is moved to the front of
  `app.router.routes` at the bottom of `soloblog/app.py`. Add new ones to
  `_dynamic_paths` there.
- **Inline `<script>`s run in `<head>`**, before `<body>` exists. Attach
  listeners to `document`, never `document.body`.
- **htmx-swapped fragments don't fire `DOMContentLoaded`.** Anything that
  needs to initialise swapped-in content also listens for
  `htmx:afterSwap` (see `PANEL_STATE_JS`).
- **Test fixed/floating elements after scrolling**, not only at the top
  of the page. Some positioning bugs only show up once the page scrolls.
- **The Tailwind binary isn't the same everywhere.** The Docker build
  pins it (`TAILWIND_EXTRA` in the Dockerfile, checked by its sha256), but
  `daisyft init --binaries --force` - locally and in CI's test job - gets
  the latest release. If production styling ever differs from local,
  compare daisyUI versions first.
- **Times are stored in UTC.** `scheduled_at` and every timestamp are
  naive UTC ISO strings, compared as strings in SQL. The site's
  timezone (Settings > Language and time) is applied only at the edges, in
  `tz.py`: converting what the admin types, and formatting dates.
- **`X-Forwarded-For`**: `ratelimit.client_ip()` trusts the last entry,
  and only from a proxy on a private network - which assumes exactly one
  reverse proxy in front of the app (`CLIENT_IP_HEADER` for a CDN).
- **JavaScript lives in Python strings.** In a normal `"""` string, `\n`
  and `\s` meant for JavaScript become a real line break or a warning:
  write `\\n` and `\\s`, or make the constant a raw string (`r"""`).
  `tests/test_scripts.py` runs every `*_JS` constant through
  `node --check`.
- **Never leave a `transform` on `#page-content`.** Any transform (even a
  finished animation's, held by `animation-fill-mode`) makes it the frame
  for every `position: fixed` element inside it - drawers, backdrops, the
  reading progress bar - so they sit in the column instead of on screen.
- **Editor shortcuts are written the way CodeMirror reads them**: dashes,
  and modifiers in its order - `Shift-Cmd-X`, `Cmd-Alt-H`. `Ctrl-Shift-X`
  or `Ctrl+Alt+1` never fire. `Cmd` becomes Ctrl off a Mac. Keep clear of
  keys a browser takes first (F9, F11, Ctrl+Shift+K, Ctrl+Shift+H); a test
  checks both.
- **An editor command is one entry in `editor_config.COMMANDS`** - its
  name, what it does, group, icon, shortcut, slash words and where it
  sits. The toolbar, its menus, the slash menu, the shortcuts, the help
  and Settings > Editor are all made from it; what it does goes in
  `ACTIONS` in `routes/editor.py`. A new icon name (from
  [lucide.dev](https://lucide.dev)) needs `python tools/editor_icons.py`.
  `tests/test_editor_commands.py` fails if any part is missing.
- **EasyMDE's stylesheet loads after ours** and colours its own parts
  (links, quotes, borders, toolbar buttons) with fixed values, so an
  override of the same selector needs `!important` - and a theme token,
  so it follows the palette. A file picker can only open from a click in
  Chrome, not a keyboard shortcut.

## Checking a change

What has to pass before a commit, and what a change needs besides code (a
test, a changelog line, the user guide, a commit message), is in
[CLAUDE.md](../CLAUDE.md) > Every change. This is how the checks work.

```bash
python -m pytest -q                   # the tests, in tests/ (with .venv active)
python -m ruff check .                # mistakes: likely bugs, security smells, needless complexity
python -m pytest -q journeys          # what people do, in a real browser
daisyft build                         # if you used new classes
python tools/phone_check.py           # every page on a phone
```

Tests run against a throwaway `DATA_DIR` (see `tests/conftest.py`), with
one admin account created through the real `/setup` flow. Background
work that would make tests depend on timing is either waited for
(`translate.wait()`, `fediverse.wait()`, `webmention.wait()`) or, for the
publishing ticker, turned off (`publishing.AUTOMATIC = False`) so tests
call `publishing.check()` themselves. Outside services are replaced with
fakes: see `tests/test_fediverse.py` for a signed "remote server".

CI runs the tests under `coverage` and prints the share of `soloblog/` they
run - a number to watch, not a gate (`python -m coverage run -m pytest -q`,
then `python -m coverage report` for each file). It then builds the Docker
image, boots it and checks `/healthz`, the homepage and the compiled CSS - on
a version tag, a pull request or by hand, not on every push
([MAINTAINING.md](MAINTAINING.md#releases)).

A lint rule that doesn't apply to one line is switched off there with
`# noqa: CODE - why`, never for the whole project unless `ruff.toml` says why.
The `S` (security) rules are worth a look each time: SQL put together from
text (S608) is fine only when every piece is a name written in the code and
every value is bound with `?`.

## Releasing

1. Both workflows, run by hand (Actions > Run workflow) on what's to be
   released, are green, and `python tools/phone_check.py` says "Nothing
   found".
2. Upgrade a copy of the previous release's data with the new image
   ([MAINTAINING.md](MAINTAINING.md#updates-that-never-break-a-site)).
3. Move `Unreleased` entries in `CHANGELOG.md` under the new version and
   date. Start each big entry with its name in bold
   (`- **Footnotes beside the text**: ...`) - those names are what the
   admin's What's new card lists. A release that fixes a security problem has a
   `### Security` part: Site health then tells everyone on an older
   version it needs attention, not just that a version is out. If the person running it has to do anything, the section starts
   with **Upgrading** - numbered steps in plain words.
4. Bump `VERSION` in `soloblog/config.py`, then run
   `python tools/platforms.py version` - it brings every app-store package
   in `deploy/platforms/` to the same version (a test fails until it has).
5. Commit on the version branch (`1.1`), merge it into `master` with a
   merge commit (a pull request, once public), then tag `master`:
   `git tag v1.1.0 && git push --tags`. A patch is tagged on
   `master` straight after its fix is merged.
6. The Docker workflow checks the tag against `VERSION` and the changelog
   (`tools/release_notes.py`), publishes `ghcr.io/<owner>/soloblog:<version>`
   and moves `:latest` to it, then makes the GitHub Release - that
   version's changelog section as its text - and deploys it to the demo.
   `:latest` only ever moves on a release tag. The admin's **What's new**
   card shows the same section's headlines after the update.
7. Start the next version: a branch `1.2` from `master`, and
   `master` merged into it after every patch
   ([MAINTAINING.md](MAINTAINING.md#branches-and-pull-requests)).
8. Once the image is published, send the app stores the new version:
   `python tools/platforms.py build dist/platforms --digest`, then each
   folder where [deploy/platforms/README.md](../deploy/platforms/README.md)
   says.
