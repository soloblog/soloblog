# Working on Soloblog

The rules for anyone changing this codebase - people and AI assistants
alike. An assistant reads this file before anything else; one that looks
for `AGENTS.md` is pointed here.

**Each rule is written once.** This file says what must be true of every
change. How to do it - the helpers to use, the layout, the gotchas - is in
[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md), and a rule there is only
explained, never restated differently. When a rule changes, change it
here, and its how-to in the same commit.

**Before a first change,** read this file, then
[Picking up where the last session left off](#picking-up-where-the-last-session-left-off).
Before UI work, docs/DEVELOPMENT.md > UI conventions; before writing
words a user sees, > Writing and settings.

## What Soloblog is (and isn't)

A self-hosted blog and personal website for **one person**. FastHTML +
htmx, daisyUI 5 / Tailwind 4 (built with daisyft, no Node), SQLite, and
markdown files on disk as the source of truth for posts.

It is not for teams or organisations: no multi-author or roles. Readers
can become **members** (free or paid) who sign in by email to read
members-only posts - but they never write, and there's still one admin.
Judge every feature against "does this help
one non-technical person run their own site?" and prefer good defaults
over options. The reasons behind this and other big choices are in
[docs/DECISIONS.md](docs/DECISIONS.md) - read it before proposing
something that changes direction.

## Where things are

| | |
|---|---|
| `soloblog/` | The app: one package. `app.py` puts it together; `routes/` has one router per admin area. |
| `app.py` (top level) | Only starts the server (`python app.py`). |
| `docs/` | The user guide, FAQ, deployment, development and sponsor pages. **The same files are the admin's Help** (`HELP_PAGES` in `routes/help_routes.py`) - one source for GitHub and the app. |
| `docs/DEVELOPMENT.md` | Project layout, UI conventions, gotchas. Read before UI work. |
| `docs/MAINTAINING.md` | Releases, triage, dependencies and their risks. |
| `docs/DECISIONS.md` | Product and technical decisions, with the reasons. |
| `docs/STANDARDS.md` | The outside standards we conform to (OWASP, WCAG, PEP 8...) and how each is checked. |
| `docs/ROADMAP.md` | What's agreed and not built yet, nearest first. |
| `CHANGELOG.md` | Every user-visible change, under `[Unreleased]` until a release. |
| `tools/demo.py` | Builds the sample blog used for screenshots and the live demo. |
| `deploy/platforms/` | The app-store packages (Umbrel, Unraid, Coolify...), sent to each store by `tools/platforms.py`. |
| `docs/brand/` | The logo (the S and dot, #605DFF), made by `tools/brand.py`. |
| `tools/phone_check.py` | Every page on a phone, checked for layout problems, script errors and confirm buttons that don't send. |
| `tools/fuzz_routes.py` | Every route sent what a bot or attacker might - none may crash. Part of the tests. |
| `tests/` | pytest, about two minutes. |
| `journeys/` | What people do, in a real browser against a real server - set up, write, comment, members, the look, backup, a phone. About three and a half minutes. |

## Python

Everything runs from the project's own `.venv` (Windows:
`.venv\Scripts\python.exe`), never the system Python. A new package is
installed there and pinned in `requirements.txt` (the app) or
`requirements-dev.txt` (tests and the browser tools). Setup is in
docs/DEVELOPMENT.md > Local setup.

## Every change

1. **Tests:** `python -m pytest -q` and `python -m ruff check .` must
   pass. Add a test for new behaviour and for every bug fixed. For a
   change to anything people do, also `python -m pytest -q journeys` -
   and a journey for a path that hasn't one yet. CI runs them all, but
   only on a version tag, a pull request or by hand - so they run here
   before every commit.
2. **Look at it:** anything visible gets checked in a browser - light and
   dark theme, a phone (375px and 320px) and a wide screen. Then run
   `python tools/phone_check.py`: every page on a phone, checked for
   sideways scrolling, things sticking out, buttons too small to tap,
   words squeezed by the buttons beside them and script errors; on admin
   pages it also presses every button that asks first and checks Yes
   sends it. It must say "Nothing found". On a phone, use what people
   already know from other apps: a row's buttons behind a ⋯ menu, tabs
   that don't fit under More (`ui.Tabs`), a toolbar you swipe along, a
   box that opens where you tapped.
3. **Changelog:** a line under `[Unreleased]` for anything a user would
   notice, in plain words, in the group it belongs to - `### Added`,
   `### Changed`, `### Fixed`, `### Removed` or `### Security`. One short
   line per change, no detail - the user guide has that.
4. **Docs:** a feature isn't done until the user guide (`docs/guide/`)
   describes it (and the FAQ, if people will ask). Hosting changes go in
   `docs/DEPLOYMENT.md`. A doc says each thing in one place and links to
   it from the others.
5. **Commits:** one change per commit, written as
   [Commit messages](#commit-messages) says, as
   `ZRPlus Studio <hello.soloblog@zrplus.net>` - never a personal
   address. Until the repository is public, commit to `master`. From then
   on `master` is the latest release: features go on a branch into the
   next version's branch (`1.1`), fixes to the release into `master`,
   each by pull request (docs/MAINTAINING.md > Branches and pull
   requests). Version numbers and branches are the maintainer's call.

## Commit messages

The history is public and people read it to learn why the code is the
way it is. Write each message for a stranger reading it in a year.

- **Subject:** one line, about 70 characters at most, saying what
  changed in plain words, as a statement of what's now true or what was
  done - "A drop menu is as wide as its longest item", "Fix the comment
  count on a trashed post". Sentence case, no full stop, no prefix or
  emoji.
- **Body** (after a blank line, when the subject isn't enough): what was
  wrong or missing, and why this is the fix - the reason someone would
  need before changing it again. Wrapped at 72 characters. What was
  checked, when it isn't obvious.
- **One change.** If the message needs "and", it's probably two commits.
- **Never in a message:** a person's name or email address, a path on
  someone's computer, a key or password, anything about money, hosting
  plans or partners, or a customer's site.
- **Nothing about how the work was done:** no mention of a chat, a
  session, a prompt, an instruction given to an assistant ("as asked",
  "per the review"), or which tool wrote it. Say what the code does and
  why. An AI assistant's commit ends with its `Co-Authored-By:` line and
  says nothing else about itself.
- **Read the tests' result before committing** - never a command that
  commits whatever the result was.

## Security and updates come first

The project has plenty of features. Once it's public, keeping people's
sites safe and their updates painless matters more than anything new.

- **Security before features.** A security report or a vulnerable
  dependency jumps the queue (see SECURITY.md and docs/MAINTAINING.md).
  New code that takes input, stores files, sends requests or changes the
  login gets a test for the abuse case, not just the happy path.
- **An update must never break a working site.** People run this without
  a developer. Migrations only add (new columns get defaults); settings
  keep their names and meanings; a removed setting is ignored, not an
  error. If a release needs anything from the user, the CHANGELOG gets an
  **Upgrading** section in plain steps, and so do the release notes.
- **Versions** (semver; `1.0.0-beta`, then `-beta.2`... until `1.0.0`)
  are the maintainer's call: a patch for fixes, a minor for features, a
  major only for a change that needs the user to do something.
- **No new features until 1.0.0-beta is out** - fixes, tests, defaults
  and docs only (docs/ROADMAP.md > Before 1.0.0-beta).

## No personal details

The project's name for its author is **ZRPlus Studio**, everywhere - code,
docs, commits, licences, the demo. Never the maintainer's personal name
or email address.

## Business notes stay out of this repository

Pricing, income, hosting plans and partner talks aren't written here -
not in docs, code comments or commit messages. The repository's whole
history goes public, deleted files included. The maintainer keeps them
privately, in the private `soloblog-website` repository (checked out
beside this one), which also holds the project website's settings
(docs/MAINTAINING.md > The website). Read it for context if asked; never
copy from it into this repository.

## The demo and screenshots

The sample blog (`soloblog/demo.py`) shows off every feature. A new
feature that shows gets sample content there, and the screenshots
(`tools/screenshots.py` in the private `soloblog-website` repository) are
retaken when the look changes. The live demo
only changes when it's redeployed (docs/MAINTAINING.md).

## One look, everywhere

Consistency matters more than any single screen. When a new UI pattern
comes in, it goes everywhere it fits - every list, every page, phone and
desktop - in the same change, not just where it was first asked for.

- **Row and card actions** (every admin list, media cards, tags,
  subscribers, passkeys) are icons made with `ui.IconAction`: a daisyUI
  tooltip names each one on a wide screen, and on a phone they sit in the
  row's ⋯ menu (`ui.RowActions`) with their words. Never a mix of icons
  and words in one group. Buttons that belong together sit in one `join`.
- **Toolbar and page buttons** (Save, New post, bulk actions) keep their
  words.
- **Every admin page is one column wide** - the column the editor writes
  in, beside the menu. Lists and forms share it; a list doesn't widen to
  fill a big screen.
- **A drop menu is as wide as its longest item** - no fixed width, no
  empty space beside the words. When it's too tall, it scrolls up and
  down (docs/DEVELOPMENT.md > UI conventions).
- **Every search field is `ui.SearchBox`** - the magnifier and its own clear
  button, the same in every browser. A list that scrolls inside a box
  (results, menus) uses `ui.SCROLLS` and `data-scroll-hint`: a thin
  scrollbar and a fade at its foot while there's more below.
- **Tooltips are daisyUI's** (`tooltip` + `data-tip`), never the browser's
  `title=`. (`title` on a text field is the browser's hint for its
  pattern, and stays.)
- **Trash and delete always ask first**, everywhere - a row, a bulk
  action, a card, the post page. Moving to trash still shows Undo after.
- **Words** follow docs/DEVELOPMENT.md > Writing and settings, and for AI
  assistants that have it, the ui-copywriting skill -
  load it before writing any text a user sees; where the two differ, this
  project's rules win: written for someone who isn't a developer - what
  a setting does for them, never how it works, no reassurance about the
  machinery, one help line at most; short, plain, the wording the app
  already has for the same action; no full stop on a status message or a
  tooltip. Long choices are pickers, set-once groups are summaries that
  open, a page fits in about three screens.
- **The user guide** is written by task, one group per file in
  `docs/guide/`, every page in the shape docs/DEVELOPMENT.md > The user
  guide sets out (`docs/guide/writing.md` is the model) - read it before
  writing or changing a guide page, and check each step against the code.

## Rules that aren't obvious from the code

- **A page is made of sections, set by Post settings, started from a
  template.** A section is one part of a page: a `##` with a `Section:`
  line, its items `###`, on any page, looking the same everywhere, changed
  only by its `Width:`/`Style:` lines and the page's section spacing. Post
  settings are the page's frame and kind (Title, Page width, Show as slides,
  In the wiki...) and every one works on every page; a section's own line
  beats the page's setting, then the site's, then Soloblog's default. A
  template is only a starting copy of sections, words and settings - a page
  keeps no tie to it. Nothing guesses parts from what's written (a plain
  `##` is plain writing), and there are no page layouts: a new kind of part
  is a new section, a new kind of page is a Post setting, the places that
  check it and a template that switches it on (docs/DEVELOPMENT.md >
  Templates, sections and Post settings).

- **Migrations:** `001_schema.sql` is the whole schema as of 1.0.0-beta
  (002-008 were folded into it on 2026-10-12, 009-012 on 2026-10-20,
  013-016 on 2026-11-08, 017-018 on 2026-11-11). Each change after that goes in a new
  numbered file, starting at `019_...sql` - sites from before the folds
  have 002-018 recorded, so those names must never come back - and one
  that has shipped is never edited: a site that already ran it would
  never get the change.
- **CSS:** Tailwind only builds classes it can see in the source, spelled
  out whole. After using a new class, rebuild: `daisyft build` (see
  DEVELOPMENT.md). `static/css/output.css` isn't committed.
- **Styling:** use daisyUI components and theme tokens, not hand-picked
  colours or custom CSS - everything has to work in all 35 themes. A
  custom override needs a real reason, written in a comment, and the
  maintainer's OK first - then a row in docs/DEVELOPMENT.md > Custom CSS
  and its `[custom-css: name]` tag in input.css, so it can be reverted.
  `primary` is for the one most important action on a page. The
  contrast of text colours per theme is generated
  (`tools/theme_contrast.py`) and tested.
- **Feedback beside the action:** no pop-up toasts. A save's result shows
  in the status slot left of the buttons; lists update in place with
  Undo. Trash and delete ask first (above). One agreed exception
  (2026-11-08): on a phone, where there's no room beside Save, Apply a
  template's "applied · Undo" floats as a bar at the bottom of the screen.
- **Scripts** live in `soloblog/js/`, one file each, read by a `FOO_JS`
  constant. The Content-Security-Policy blocks inline handlers - use
  `actions.on()` and `data-*` attributes, and a nonce on every Script.
- **i18n:** every word a visitor sees goes through `i18n.t()` and must be
  in all 22 translation files in `soloblog/locales/` - English, the 23rd
  language, is the source (a test checks). The admin is
  English.
- **Comments in code:** only for a non-obvious why - a workaround, a
  constraint, a surprise. Plain and short, the way a person writes them.
- **Structure:** extend the existing modules before adding new ones; no
  abstractions for one caller.
- **Admin routes** live under `/admin`, where `guards.admin_guard` requires
  the login before they run - never a page for the admin anywhere else.
- **Outbound requests** go through `netguard` (public addresses only;
  `private_ok` for a server the admin named as their own), except the
  admin's own update hook. A test fails on `urlopen` anywhere else.
- **Names from outside** - a file name in an address or a form - pass
  `images.plain_name` (a folder like `_trash`, or an empty name, never
  counts) and are looked up with `os.path.isfile`, never `exists`. Any
  new route is covered by `tools/fuzz_routes.py`: nothing anyone sends
  may give a server error.

## Decisions are the maintainer's

Ask before: removing a feature, changing a default people rely on,
adding a dependency, anything that costs money or goes public (releases,
the demo, repository settings), and any design choice that's genuinely
open. Offer a recommendation with the question.

## Picking up where the last session left off

1. Read `[Unreleased]` in CHANGELOG.md and `git log --oneline -20`.
2. Read docs/ROADMAP.md for what's next, and check open issues (links in
   docs/MAINTAINING.md).
3. Run the tests before changing anything, so you know what was already
   broken.
