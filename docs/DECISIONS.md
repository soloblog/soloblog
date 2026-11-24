# Decisions

The principles that shape Soloblog, and what it deliberately doesn't do,
each with its reason. When the direction changes, this page changes in
the same commit. How each one is carried out is in
[CLAUDE.md](../CLAUDE.md) and [DEVELOPMENT.md](DEVELOPMENT.md).

## Product

- **One person, one site.** No multi-author, roles, teams or
  organisations. *Why:* the audience is individuals, often not
  technical; teams bring permissions and workflows that make everything
  harder for them.
- **Members read, never write.** Readers can sign in by an emailed link
  or code, with no password, to read members-only posts. One free tier
  and one paid tier, paid through Stripe's own checkout and portal.
  *Why:* a person running a site alone should be able to earn from it,
  and card details should never reach the site.
- **A personal site, not a platform.** No seller marketplace, plugin
  system or "Pro" edition. *Why:* each pulls toward running other
  people's businesses rather than one person's site.
- **Good defaults over options.** A setting needs a reason a real person
  would change it, and everything works before anything is set.
- **Colour palettes, not themes.** 35 palettes on one design, each with
  a dark mode. *Why:* "theme" promises a different design.
- **English spelled the site's way** - American, British or Australian -
  on the site, in the admin and in Help.
- **The admin is in English; what visitors see is in 23 languages.**
- **MIT licence.** *Why:* the simplest licence to use, host and build on.

## Content and data

- **Posts are markdown files on disk**, with SQLite as the index and
  everything else. *Why:* the writing stays readable and portable without
  the app - back it up, edit it anywhere, leave any time.
- **One SQLite file, one data folder, one instance.** *Why:* the cheapest
  hosting there is, and a backup is one zip. Scaling out isn't a goal.
- **An update never breaks a working site.** Migrations only add, and a
  shipped migration is never edited; settings keep their names and
  meanings.

## Pages

- **A page is made of sections, set by Post settings, started from a
  template.** A section looks the same on every page; a template is only
  a starting copy, with no tie kept to it. There are no page layouts.
  *Why:* one set of parts, learnt once, works everywhere.
- **The closest setting wins:** a section's own line, then the page's
  Post settings, then the site's settings, then the default.
- **No full-width reading column.** *Why:* lines that long are hard to
  read.

## Interface

- **daisyUI components and theme tokens, not custom colours or CSS.**
  *Why:* every palette has to work.
- **Feedback beside the action, not pop-up toasts.**
- **Trash and delete always ask first;** moving to trash also offers
  Undo. *Why:* a tap on the wrong row shouldn't remove anything.
- **One look everywhere:** a new pattern goes to every place it fits, on
  a phone and a wide screen alike.
- **Settings are pages under small headings,** searchable from any admin
  page. Switches save as they change; typed text waits for Save.
- **Words for people who aren't developers:** what something does for
  them, never how it works, in the standard terms they already know and
  search for - never a paraphrase of one.

## Technology

- **FastHTML and htmx, rendered on the server.** *Why:* one language, no
  build step for the app, fast pages and a small surface. The risks and
  the fallback are in [MAINTAINING.md](MAINTAINING.md).
- **Front-end libraries kept in the repository, not loaded from CDNs**
  (KaTeX and Mermaid excepted, pinned and loaded only when used).
  *Why:* nothing changes underneath a site, and it works offline.
- **Few dependencies.** Stripe, the MCP server and the DNS checks use
  plain HTTPS rather than a package each. *Why:* every package is one
  more thing to keep safe and up to date.
- **The docs are the admin's Help.** One source for GitHub and the app.

## Privacy and connections

- **No telemetry, not even an opt-in ping.** Nothing leaves a site unless
  its owner turns it on, and the user guide lists every outside
  connection. *Why:* a simple promise is one that can be kept.
- **Apps and AI assistants post by API key,** with drafts-only keys and
  one choice for who may publish. *Why:* what goes live stays the
  owner's decision.
- **Writing apps connect through a small Ghost-compatible API and
  Micropub.** *Why:* what the popular writing apps already speak, with
  the least to build and keep safe.

## Community

- **GitHub for everything:** Issues for bugs, Discussions for questions
  and ideas, the changelog for what shipped.
- **Support stays small:** no chat server, no stale bot, no promised
  release dates. *Why:* a project run by one person; a Discussion stays
  searchable where chat scrolls away.
- **A live demo with a working admin,** reset every few hours. *Why:*
  trying the editor is the best way to see the app.
- **Referral links in the hosting guide are allowed, and always
  disclosed** - one notice under the page's title covers every link on
  it. *Why:* they help fund the project; whether a company has one never
  decides what's listed, and one notice can't be forgotten the way a
  label on each link can.
