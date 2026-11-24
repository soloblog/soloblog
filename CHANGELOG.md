# Changelog

All notable changes to Soloblog are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions
follow [Semantic Versioning](https://semver.org/). Until 1.0, minor
versions may include breaking changes; they'll always be listed here.

## [Unreleased]

### Added

- Sync images asks which way: this site to your bucket, or your bucket to
  this site - and copies only what's missing or different
- Restoring a bucket backup can bring back the bucket's images too

### Fixed

- A Buttons line in a Call to action or a Hero shows its buttons on the
  card, instead of repeating the last one
- Links, lists, quotes and paragraph spacing in a section's words look as
  they do in the rest of the post
- A section after ordinary writing sits as close as a heading does,
  instead of leaving a big gap above it
- The space under a section is the same for every kind of section
- On a page with writing of its own, two sections in a row are spaced
  like headings too
- Words under a Menu section's dishes show, instead of being left out
- Post settings say when Settings turns something off for that post or
  page, with a link to change it
- The post chosen as the homepage follows the contents' settings for
  pages, as the side panels already did
- Post settings list each choice once, instead of the site's twice
- A cloud storage endpoint works as the storage company shows it, without
  https://
- Backup and import says what's wrong with a cloud storage endpoint,
  instead of showing an error page
- Site health says when cloud storage is connected but has no backup
  yet, instead of asking to connect it and to check backups that don't
  exist
- A failed automatic backup stays in Site health after a restart, until
  one works
- When the bucket refuses, Backup and import says what's wrong and which
  setting to check, instead of the bucket's raw reply
- What Back up now, Sync images, Restore, Verify a backup, Check again
  and similar buttons did shows beside them, not at the top of the page
- Recent backups lists the newest three, with the rest under Older
  backups - every kept backup can be restored
- The restore screen and the message after a restore count "1 revision"
  and "110 revisions", not "revision(s)"
- Restore on a bucket backup brings the Restore card into view and says
  which backup it's from
- Backup and import and Site health say when images haven't reached your
  bucket
- On a tall window, the section after a Story follows at its usual gap,
  instead of after a screen of empty space
- The page chosen as the homepage stays out of the list of posts and the
  feeds by itself, and search finds it at the homepage's address

## [1.0.0-beta] - 2026-11-17

The first public release: a blog and personal website for one person,
run on your own server or hosting account. The
[user guide](docs/guide/README.md) covers everything in detail.

### Added

- Markdown editor with a matching preview, drafts, scheduling, private
  preview links and version history
- 31 templates and 41 kinds of section, from recipes and resumes to
  pricing, portfolios and slides
- 12 starting styles and 35 colour palettes with dark mode, or your own
  colours
- Media library with galleries, alt text, stock photos, audio and video
- Comments, a newsletter, a contact form, and free or paid members
  through Stripe
- RSS, the fediverse, webmentions and Bluesky sharing; visitor pages in
  23 languages
- Import from WordPress, Ghost, Medium, Substack or a folder of markdown
- An API, Micropub and an MCP server for apps and AI assistants
- Backups, passkeys, two-factor login and Site health
- A built-in guide, searchable from any admin page
- One-click hosting, your own server or a computer at home
