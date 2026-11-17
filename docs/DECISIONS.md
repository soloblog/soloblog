# Decisions

The choices that shape Soloblog, with the reasons, so they aren't
re-argued or undone by accident. Newest at the end. Reversing one is fine -
add a new entry that says so and why.

**Format:** date · decision · why.

## Product

- **2026-08 · One person, one site.** Soloblog began as a multi-tenant
  service and was cut back to a self-hosted blog for one person. No
  sign-ups, tenants, billing or staff tools. *Why:* that much is more than
  one maintainer can run well, and personal sites are the gap worth
  filling.
- **2026-09-25 · No multi-author, no organisations.** Not now, not later.
  *Why:* the audience is individuals, often non-technical; teams add
  roles, permissions and workflows that make everything harder for them.
- **2026-09 · Not planned: paid memberships, Obsidian sync, a seller
  platform, "Pro" features.** *Why:* each pulls toward being a platform
  rather than a personal site.
- **2026-10-08 · Memberships are back on the table: a members area,
  before launch**, narrowing "not planned: paid
  memberships" above. Like Ghost's, but simpler; still one admin -
  members are readers, never writers. *Why:* people who run their site
  on Soloblog should be able to earn from it. Designed and decided on
  its own before it's built.
- **2026-10-09 · The members area, decided**:
  members are readers who sign in with a link or code emailed to them -
  no passwords - and never write; still one admin. One free tier and one
  paid tier (monthly and yearly, an optional free trial). Each post is
  for Everyone, Members or Paid members, with a free preview above a
  cut. Payments through Stripe - its own Checkout and Customer Portal,
  so card details never reach the site - set up from one restricted key,
  with Soloblog making the product, prices and webhook. Newsletter
  subscribers become free members. *Why:* the patterns readers already
  know from Ghost, Substack and Medium; the payment provider's hosted
  pages are the safe norm; one paid tier keeps it simple for a person
  running it alone - more can come once it's in use.
- **2026-09-27 · Team pages, a simple shop and members-only pages are on
  the roadmap**, narrowing "not planned" above. *Why:*
  a one-person business or club needs them, and each can stay within the
  rules: one admin edits everything, a shop links out to a payment
  service instead of running a cart, and members-only pages open with a
  password or a subscriber's emailed link, not reader accounts. (Members
  became readers who sign in by emailed link, 2026-10-09; team pages and
  the shop are now sections, 2026-11-04.)
- **2026-09-27 · Colour palettes, not themes.** People pick from 35 colour
  palettes (daisyUI calls them themes) on one design; visitors get a
  "Colours" menu. *Why:* "theme" promises a different design, which
  Soloblog doesn't have. The settings keep their names (`theme`,
  `theme_dark`), so no site has to change anything.
- **2026-09-27 · English is spelled the site's way** - American, British or
  Australian - on the site, in the admin and in Help. *Why:* a writer in
  Sydney shouldn't see "color", or one in Ohio "colour". The docs are
  written in British English and Help converts them for an American site.
- **2026-09-25 · MIT licence** (over AGPL). *Why:* the simplest licence for
  people to use, host and build on; a closed hosted fork is an accepted
  risk.
- **2026-09 · Good defaults over options.** New settings need a reason a
  real person would change them; everything works before anything is set.
- **2026-11-03 · The first public release is `1.0.0-beta`**, not 0.4.0
  (the earlier entries' "0.4.0" means this release). `1.0.0` follows once
  it has been used in public for a while without serious problems.
  *Why:* it's complete, and it already keeps 1.0's promise - an update
  never breaks a working site - so features from here are minor versions
  and only a change that needs the owner to act is a major one. "Beta"
  says it's new to the public.

## Content and data

- **Posts are markdown files with front matter**; SQLite is an index
  plus everything else. *Why:* your writing stays readable and portable
  without the app - back it up, edit it anywhere, leave any time.
- **One SQLite file and one data folder, one instance.** *Why:* the
  cheapest hosting there is, and backups are one zip. Scaling out isn't a
  goal.
- **2026-09-26 · Migrations folded into `001_schema.sql` before the first
  deployed release.** From then on each change is a new numbered file and
  shipped files are never edited.
- **2026-10-25 · A feature freeze until 0.4.0 ships.** Until the first
  public release: fixes, security, behavioural tests, better defaults
  (more off until turned on), and setup and email that work first time -
  no new features. *Why:* Soloblog's breadth is its biggest weakness -
  more than one maintainer and one non-technical owner can keep in good
  shape. Problems were hiding in corners and combinations that checks of
  the markup didn't reach.

## Interface

- **daisyUI components and theme tokens only**, no custom colours. *Why:*
  35 themes must all work; hand-picked colours break some of them.
- **Status beside the action, not toasts.** *Why:* feedback where you're
  looking.
- **2026-09-26 · Trash and delete always ask first, and trash still offers
  Undo** (this replaced "Undo instead of are-you-sure"). *Why:* a tap on the
  wrong row, especially on a phone, shouldn't be able to remove anything.
- **2026-09-26 · Row actions are icons with tooltips; a new UI pattern goes
  everywhere it fits.** *Why:* a mix of icons and words, or a pattern in
  one list and not the next, makes the admin feel unfinished.
- **2026-10-11 · Settings are pages under small headings** (Site, Design,
  You, Readers, Growth, Writing, Advanced), one page at a time with search
  over all of them, as Notion and Ghost do; names are the plain words
  people search for. Switches and choices save as they change; typing
  waits for Save. *Why:* one long page per area was too long to browse,
  and a Save for every switch lost changes.
- **2026-09-26 · Admin menu in the margin beside the content**, a drawer
  where there's no room. *Why:* a sidebar at the screen's edge sits far
  from the content on wide monitors.
- **2026-10-08 · The editor's toolbar is in fixed sections** - Text,
  Blocks, Insert, History, View, Help - shown as Icons or Classic menus,
  and the phone bar has the same sections. Buttons are ordered within a
  section, never across; there's no heading menu, and Insert is the one
  button always there. *Why:* the desktop, the phone and both styles then
  agree on where everything lives, and the dividers mean something.
  (Since then Layout and Sections have joined them, and a third style,
  Minimal, has no toolbar - `/` instead.)
- **2026-10-08 · The buttons you choose are what one tap reaches**, on a
  computer and on a phone; the rest of each section is a ▾ away. The
  phone's bar matches the toolbar unless set on its own (Settings >
  Editor > On a phone), and always has Undo, Redo and Help (replaced
  2026-10-19, below). *Why:*
  choosing buttons should pay off wherever you write, and a phone has
  no keyboard shortcuts to fall back on.
- **2026-10-08 · Posting from other apps and AI, by API key** (how it works:
  docs/API.md). A post sent from an app arrives as the app asks -
  published or a draft - with a switch to make every one a draft. An AI
  assistant (the MCP server) can publish only with a key that has the
  publish scope, and a setting keeps it to drafts. Micropub first, with
  "sign in with your site"; a WordPress- or Ghost-compatible layer for
  Ulysses and iA Writer on Android, chosen by what those apps really
  send. *Why:* the apps writers draft in decide; the app already knows
  whether the writer meant to publish, and anything that publishes for
  you is your choice, made once, in Settings. (The two switches became one
  choice, "Who may publish", 2026-10-20.)
- **2026-10-08 · A writing app for your computer is on the roadmap**
  (docs/ROADMAP.md > Soloblog on the desktop): Windows, macOS and
  Linux, built on the API, the one first-party client. It edits the
  site directly and keeps offline work only until it's sent - never a
  second copy to keep in step, so "Obsidian sync" above stays not
  planned. *Why:* writers want a window of their own that works without
  a browser tab or a connection, and the site stays the one source of
  truth.
- **2026-10-19 · On a phone, Undo, Redo and Help are buttons like the
  rest**, not fixed at the end of the bar: in the row you swipe when
  they're among your buttons (Undo and Redo are, out of the box), and
  always in their sections, History and Help. *Why:* fixed, they took
  room from the buttons people chose, and Help is in the ⋯ beside Save
  already. (Help beside Save is no longer folded first, 2026-11-05, below.)
- **2026-09-22 · No full-width reading column** - Standard or Narrow only.
  *Why:* lines that long are hard to read.
- **2026-09-22 · Post settings slide over the text** at every screen size,
  instead of docking beside it. *Why:* docked, it squeezed the text or
  widened the page past the site's column. (Narrowed 2026-10-19, below.)
- **2026-10-19 · Post settings sits beside the editor where the screen has
  room for it** - a card in the right margin, as the admin menu is in the
  left, always there as that one is - and slides over the text everywhere
  else, and in Focus mode, changing between the two at once. *Why:* on a wide screen
  the slide-over covered the writing for no reason; in the margin it
  squeezes nothing and widens nothing, which is what the 2026-09-22
  decision was guarding against. A switch in Settings > Editor keeps it
  sliding over everywhere, for those who prefer that.
- **2026-09-23 · One Glass switch** for the header, footer, drawers, menus
  and dialogs, and glass is frosted, never clear. *Why:* nobody wants a
  glass header over a solid footer, and text over moving content was hard
  to read.
- **2026-09-23 · Menus are popovers**, placed by script beside their
  button. *Why:* nested in a glass header, a CSS dropdown never drew its
  blur; a popover also closes on a click outside or Esc.
- **2026-10-12 · One width for every admin page; the Design preview opens
  full screen** (Ghost's design view). *Why:* a wider page for the Design
  pages alone made them look like a different app.
- **2026-10-12 · A list that opens from a field is as wide as the field; a
  button's menu is as wide as its contents.** *Why:* the same as a
  browser's own dropdowns, so every one looks alike.
- **2026-10-20 · The admin is its own frame** (Ghost's, WordPress's): a
  thin bar of its own at every width (the site's name, search, colours)
  and no site header or footer; on a wide screen the menu is a rail on
  the left, the page starts beside it, and Post settings sits beside the
  text. One button opens the menu where the rail doesn't show - the
  sidebar button and the gear were two ways to one place, and the
  setting that chose between them went with them. *Why:* the site's
  header over the admin took room and looked like the site, not a place
  to work; a floating header and an edge-to-edge footer made it worse.
- **The admin is English; what visitors see is in 23 languages** (English and 22 translations).
- **2026-10-22 · Sections work in any post, and Insert always offers
  them; a layout's own pieces stay only with their layout.** A section
  (Pricing, Testimonials, Numbers...) is written as a Landing page always
  wrote one - a `##` with a `Section:` line - in every post; no second way
  to write it. In a layout whose `##`s are its items, a section shows
  after them. *Why:* one list that's the same everywhere can be learnt
  once, and a plan or a question means nothing outside its layout. One
  way of writing keeps the text readable and portable, and Landing pages
  unchanged. Not "components" (a developer's word) or "blocks" (Insert's
  Blocks are the small things inside text). (A layout's own pieces are
  replaced 2026-11-06, below: there are no layouts; the rest stands.)
- **2026-11-04 · A layout is the page; a section is a part of it.**
  Layouts stop guessing parts from what's written (the Landing page's
  picture bands and closing card, Small business's contact buttons and
  hours, Profile's latest posts, Coming soon's sign-up): each is a
  written-out section. Layouts that were only a list of one kind of item
  (Pricing, Team, FAQ...) become pages that start with that section. A
  section looks the same on every page, the Landing page's look, starting
  at column width in an ordinary post. This replaces "full-width bands
  stay on Landing pages only" (2026-10-22). *Why:* one way to build every
  part can be learnt once; what you write is what you get. (Replaced 2026-11-06,
  below, by Templates and sections, no layouts: a section is the only
  part of a page, and a template only where a page starts.)
- **2026-10-24 · Your own colours (Custom colours since 2026-11-05) are pasted from daisyUI's theme
  generator, and stored as checked values, not as the pasted CSS.** Up to
  10, beside the built-in palettes and in readers' Colours menu; each
  gets the built-in themes' readable-text treatment when it's saved.
  *Why:* the generator's own editor and preview are better than any we'd
  build, and a daisyUI theme is only its values, so a page can carry it
  without rebuilding the site's styles. Keeping only daisyUI's 28 values,
  each matched to a strict pattern, means nothing else in a paste - a
  `</style>`, a rule of its own, a URL - can reach a page.

- **2026-11-06 · Layouts and templates, one for one.** Every premade
  template gets a coded layout of its own and every layout one premade
  template - 32 of each, the 17 new layouts first simple, then designed
  as the Landing page was. A layout still styles the page and a section
  still looks the same everywhere. Custom templates keep a layout, coded
  or custom; custom layouts are a saved look on one coded layout,
  second-class by design, and only exist once someone makes one. New
  posts start from a template chosen once in Settings, with no picker
  each time. How it works: docs/DEVELOPMENT.md > Templates, sections and
  Post settings. *Why:* a template should
  feel like a page of its own, not a Standard or Landing page with words;
  people can't write code, so what they make is a look and a starting
  point, never a layout's special behaviour. (Replaced the same day,
  below, before any of it was built.)
- **2026-11-06 · Templates and sections, no layouts.** Every job a layout
  did moves elsewhere: its parts to sections (Recipe's ingredients,
  Resume's entries, Profile's photo and links...), its frame to Post
  settings (a Title and a Page width join cover, contents and Show), and
  what kind of page it is to four Post settings (Show as slides, In the
  wiki, Link to, Remind me to update). Each layout becomes a template of
  sections and settings. Custom templates are made of exactly what the
  premade ones are, and can be exported and imported as a file; a
  curated gallery may follow. Templates never change the header or
  footer. Built before 1.0.0-beta, and the three sites' posts fixed by
  hand - no conversion code and no old layouts kept, as there are no
  other sites. *Why:* two things to learn
  instead of three, one way to build every page, custom templates equal
  to ours, and less code to keep up - the end of what 2026-11-04 began.
  Once public, every layout written into a post would have had to work
  for good. Built 2026-11-07: 31 templates, 40 kinds of section and the
  Post settings, with no layout left in the code, the editor, the API or
  the docs.
- **2026-11-08 · A scroll story is a section of its own, Story.** Its
  `###` steps each have a picture and words: on a wide screen the words
  scroll beside the step's picture, held still; on a phone each picture
  fills the screen and fades into the next, the words over it. With
  reduce motion, Animations off or no script, the steps are a plain
  stack. *Why:* several pictures played as you scroll are a kind of part
  of their own - a key on Picture and text would have made one section
  two different things.
- **2026-11-08 · Section headings, left or centred.** A `Heading:` line on
  every section, and Settings > Header and footer > **Section headings**
  for the whole site; Centred centres the heading and its intro, never
  the items. *Why:* a page of sections often reads better with its
  headings in the middle, as a landing page's are - without it there was
  no way to do it.
- **2026-11-08 · Space and appearing at every level.** The room between
  sections and how they come into view can be set for the site, for a
  page (Post settings > Page > Space between sections, Sections appear)
  and for one section (`Space:`, `Appear:` lines). *Why:* both were
  site-wide or page-wide only, and the one that followed the old Landing
  layout - sections appearing - had stopped reaching any page. A section's
  own value is stamped on its wrapper, resolved on the server, so the
  stylesheet needs one rule per value, not one per level.
- **2026-11-08 · On a phone, Apply's "applied · Undo" floats as a bar at
  the bottom** - the one exception to feedback beside the action. *Why:*
  there's no room beside Save on a phone, and Undo must stay in reach.
- **2026-11-07 · Which setting wins: the closest to the part.** A
  section's own Key: line, then the page's Post settings, then the site's
  settings, then Soloblog's default. `Default` - or no line - means
  "follow the one below", and a page's Post setting that differs from the
  site's carries a **Custom** tag with **Reset** beside it.
  *Why:* one rule for every setting, the one people already know from
  styles and from settings editors, and a page that has changed something
  says so without anyone having to compare.
- **2026-11-09 · Every switch and choice with a default shows the bar and
  a Reset icon while it differs - in Post settings and on the settings
  pages - and no "On/Off by default" label.** Reset is an icon (↺) on the
  setting's own line, its tooltip "Reset to default (On)", as VS Code marks
  a modified setting. On the settings pages the default is the starting
  style chosen last over Soloblog's own (`presets.baseline()`), so a style
  just picked marks nothing; Reset puts its value back and saves.
  Choices' lists keep their **Default** mark; what's typed isn't marked.
  *Why:* the labels sat on every switch (about 120 across the settings
  pages) whether it mattered or not, and a changed switch took three lines
  in Post settings; one look for one meaning, everywhere. Compared with
  Soloblog's defaults alone, a starting style would have lit up dozens of
  settings it changed on purpose.
- **2026-11-09 · A changed Post setting shows a thin bar and Reset, not a
  Custom tag.** The bar on the setting's left edge (the "modified" signal
  editors use) and the Reset button say it differs from the site; the
  panel heading says "Page · 2 changed". *Why:* Reset already says it's
  changed, and the word cost space in a 320 px panel, squeezing labels and
  switches.
- **2026-11-07 · Apply a template adds the whole template and replaces the
  page's Post settings.** Its sections go at the end of the page, even one
  the page already has, and never touch what's written; its settings
  replace the page's own; its summary, tags and cover fill only what's
  empty; **Undo** puts it all back, and nothing is saved until Save. The
  second of two applied wins. *Why:* it replaces switching a page's
  layout, and one rule is easier to remember than merging settings
  one by one - the bar and Reset show what changed.
- **2026-11-07 · One setting for what new posts start from.** **New posts
  start from** - Blank, a custom template or a built-in one - is chosen
  once in Settings > Editor and applies to every new post and page, with no
  picker each time; **Template** under the title still starts one from
  another. *Why:* most people write the same kind of page again and again,
  and a choice at the start of every post is a cost.
- **2026-11-05 · One picker for a new post's layout and template.** The
  Layout label above the post opens it; on a new post it has a Templates
  tab (Recent, Custom, Built-in), each card with its layout's picture, and
  the Start from box is gone. *Why:* two pickers for one choice, one above
  the other, and a template is mostly a layout with words in it. (Replaced
  2026-11-06, below: with no layouts, the picker is for templates only.)
- **2026-11-05 · A block's own options come first in Insert and `/`.** With
  the cursor in a section, a gallery, a callout or a fold, its lines -
  Width:, Style:, Show as:, Count:, Tag:, a gallery's style - are offered
  first, the one in use marked, and a value the page can't use is
  underlined with what it can be. *Why:* people shouldn't have to read Help
  or remember the words to change how something looks.
- **2026-11-05 · On a phone, Settings and Help stay beside Save**; Discard
  and View fold into ⋯ first. *Why:* they're reached for more.
- **2026-11-05 · Professional wording, as the big product companies write
  it.** "Custom", never "Yours"; no "your" in Help's headings or the
  admin's panel names (Site address, Custom colours, Admin email). *Why:*
  the owner's direction - chatty words read as unfinished.

## Technology

- **FastHTML + htmx, server-rendered.** *Why:* one language, no build
  step for the app, fast pages, small surface. Risks and the fallback are
  in [MAINTAINING.md](MAINTAINING.md#dependencies-and-their-risks).
- **Front-end libraries vendored, not from CDNs** (except KaTeX and
  Mermaid, pinned with SRI and only loaded when used). *Why:* nothing can
  change underneath a site, and it works offline.
- **2026-09-26 · Code in one `soloblog/` package**, `app.py` at the top only
  starts it.
- **2026-09-26 · Docs in `docs/` are also the admin's Help.** *Why:* one
  source, never out of step.
- **2026-10-09 · Numbered migrations from now on**, starting with
  `002_members.sql`, instead of folding everything into `001_schema.sql`.
  *Why:* the project's own website already runs on a real database, and
  a folded change would never reach it. Each file only adds; one that's
  shipped is never edited.
- **2026-10-12 · Folded into one `001_schema.sql` again for 0.4.0**, the
  first public release. *Why:* a new install starts from one file. The
  sites already running had applied all of 002-008, so nothing reaches
  them twice or not at all; the next file is `009`, never a name they
  already have.
- **2026-10-20 · 009-012 folded into `001_schema.sql` too**, still before the
  first public release. The two that only added columns are its last
  lines; the two that carried old settings over (the phone bar, who may
  publish) had nothing to carry on a new site. *Why:* the sites running -
  the demo, the website, zrplus.net - had applied them all; the next file
  is `013`.
- **2026-10-09 · Stripe through plain HTTPS, no Stripe package.** Its API
  is form posts and JSON, and webhook signatures are an HMAC - the same
  way Soloblog already talks to Resend and DeepL. *Why:* no new
  dependency to keep up to date for a handful of calls.
- **2026-10-09 · Site health looks up DNS over HTTPS** (Cloudflare, then
  Google), for the sending domain's SPF, DKIM and DMARC records. *Why:*
  no new package; it only sends a public domain name. Remote checks can
  be turned off.

- **2026-11-05 · Links to headings are written GitHub's way**
  (`#project--photo-story` for "Project / photo story"), and Help reads
  them as its own. A test checks every link and heading in the
  repository's text files. *Why:* the same docs are read on GitHub and in
  Help, and each gave a heading with a slash a different id.

## Community

- **2026-09-26 · GitHub for everything:** Issues for bugs and accepted
  work, Discussions for questions and ideas, a Projects board as the
  public roadmap, the changelog for what shipped. *Why:* one place, one
  login, and ideas turn into issues in a click.
- **2026-09-26 · A live demo with a working admin**, reset every few hours
  (demo mode). *Why:* trying the editor is the most convincing way to
  show the app.
- **2026-09-26 · Referral links in the deployment guide are allowed, and
  always marked as referral links.** *Why:* they help fund the project;
  disclosure keeps readers' trust and is what the law asks.
- **2026-10-12 · Post by email removed, before launch.** Few people blog
  by email now; it kept a mailbox password on the site and read a
  mailbox every five minutes - security surface and support questions
  for little use. Writing apps (Micropub, the API) and the phone admin
  cover writing away from a computer. Its settings, password included,
  are deleted (migration 008). The entry below is how it worked.
- **2026-10-09 · Post by email reads a mailbox over IMAP.** Any
  provider, any host - a home server behind a router too - and Python's
  own imaplib, no new dependency; the way WordPress does it. Only mail
  from the admin's addresses that the receiving provider says passed
  DMARC (its own, top Authentication-Results header) counts; everything
  becomes a draft. *Why:* a provider's inbound webhook would be instant,
  but needs another account and a site the provider can reach, and each
  provider's format is different.
- **2026-10-09 · Ghost's Admin API, not WordPress's, for Ulysses and iA
  Writer.** Both publish to Ghost on Apple devices with one key; Ghost's
  API is documented and small, WordPress's application-password flow
  sends the password back in an address. Only the endpoints these apps
  use, and Soloblog's own name everywhere a person sees. The signed key's
  secret is derived from SESSION_SECRET, not stored. *Why:* the two apps
  people asked about, with the least to build and keep safe.
- **2026-10-09 · The MCP server is Soloblog's own, and assistants write
  drafts.** No MCP package: the part that's needed - JSON-RPC over one
  HTTP endpoint, a handful of tools - is small, and one less dependency
  is one less thing to keep safe. "AI assistants can only write drafts"
  starts on, whatever an assistant's key; the author turns it off
  (replaced by "Who may publish", 2026-10-20). *Why:*
  the author's voice and what goes live stay theirs, and an assistant
  that misunderstands can't change what readers see.
- **2026-10-20 · One choice for who may publish, for every way in.**
  "Posts from apps arrive as drafts" covered only Micropub, despite its
  name, and "AI assistants can only write drafts" looked like its twin;
  nothing on a key said either applied. Now "Who may publish with a
  Publish key": No one, Apps not AI assistants (the default, as before),
  or Apps and AI assistants - for the API, writing apps, Ghost apps and
  AI assistants alike. Held back, a new post asked to go live arrives as
  a draft; changing a live post is refused, saying why. Sites carry over
  what they chose. *Why:* one rule the author can read, and a key's row
  says what it can really do.
- **2026-10-09 · "Sign in with your site" is built in, and makes an
  ordinary key.** Soloblog is its own IndieAuth server (the site is the
  identity - there's one admin), PKCE S256 required, codes once and for
  ten minutes, sent back only to the app's own site or an address it
  lists. You choose the scope on the Connect page; the key it makes is
  listed and revoked like any other. *Why:* no second kind of credential
  to secure, and nothing for a non-technical writer to copy and paste.
- **2026-10-09 · API keys: three scopes, a header only, kept as SHA-256.**
  Read, Write drafts and Publish, each allowing what the one before does;
  a drafts key can't change a live post. A key travels only in the
  Authorization header - never the address, never the login cookie, so
  CSRF can't reach the API. Kept as a plain SHA-256: keys are 256 random
  bits, so slow password hashing buys nothing, and they don't depend on
  SESSION_SECRET. Every save goes through posts.write, the editor's own.
  The panel was in Settings > Security, beside passkeys and sessions: keys
  are access to the site. It's now in Settings > Integrations, with
  webhooks and the other outside connections. *Why:* the smallest set of choices that keeps
  "give each app only what it needs" true, and one save path means one
  set of rules to test.
- **2026-10-09 · Still no telemetry - not even an opt-in ping.** What the
  project knows of how Soloblog is used comes from what people choose to
  share: Copy for a bug report lists the features in use (rough counts,
  nothing that names a site), plus GitHub's stars and image downloads,
  issues and Discussions, and platform partners' numbers. The user guide
  lists every outside connection the app makes. *Why:* a promise of
  "nothing leaves your site unless you turn it on" is simple to keep and
  easy to believe; an install counter needs a server to run and secure,
  and a privacy policy, for numbers that wouldn't change what gets built.
- **2026-10-08 · Support stays small and on GitHub: no chat server, no
  forum of our own, no stale bot, no promised release dates, no
  telemetry.** Discussions is the forum; [SUPPORT.md](../SUPPORT.md) says
  what to expect; each release gets a post on the project's own website.
  *Why:* one maintainer. Chat sets an expectation of always being there
  and its answers scroll away, where a Discussion stays searchable and
  becomes a FAQ entry; a bot closing issues makes people feel dismissed;
  a promised date is one more thing to miss. Nobody should feel
  abandoned, so what we promise instead is answers within a week, and
  sites that keep working whatever happens to the project. Usage is
  measured by stars and image pulls, never by anything reported from
  people's sites.
- **2026-11-05 · The project's addresses are the soloblog organisation's**
  (`github.com/soloblog/soloblog`, `ghcr.io/soloblog/soloblog`, Sponsors
  under the organisation), everywhere they're written, ahead of the public
  repository. *Why:* never a personal account in public, and nothing to
  change on release day.
