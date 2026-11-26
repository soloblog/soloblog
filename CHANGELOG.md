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
- A page in the menu or footer can go under one of Soloblog's own pages,
  like Home or Blog, as it can under a page of yours
- Search lists Soloblog's own pages in your menu, like Blog or Archive,
  when their name matches
- Restoring a locked backup asks for the passphrase it was made with,
  when it isn't the one set now
- A new server that can't open its newest backup asks to restore your
  site, instead of starting as an empty site
- A post on your site has a button back to Posts and pages, beside Edit
- Admin lists open the tab you were on last, with the filters and sort
  you chose, in this browser

### Changed

- Settings > Email asks for your password only once you change the
  admin email
- Settings > Address and search is now URL and SEO, and the admin and
  Help say URL wherever they said address
- The admin and Help say image wherever they said picture
- The admin and Help say text where they said words, and the editor's
  tooltips no longer describe Bold or Italic in other words
- Two-factor login is called two-factor authentication (2FA)
- A slider's Move by itself is called Autoplay
- Fold headings and Fold contents are called Collapsible headings and
  Collapsible contents, like the editor's Collapsible block
- The admin and Help say restore where they said bring back
- The admin and Help say select where they said tick
- Each kind of section, Key: line and value has one name: Picture and
  text is Image and text, Pictures together is Images, A line after a
  picture is Captions, and second names like Stats or Timeline are only
  search words in Insert
- The newsletter's sign-up box under each post is off until you switch
  it on; a site that already shows it keeps it
- The newsletter's "Show it on the homepage too" is "Show it on the blog
  roll too" - it shows with the list of your posts, wherever that is
- The Numbers section's figures grow with the space they have, up to a
  launch page's size, and the words under them are easier to read
- Insert's Call to action, Hero, Testimonials, Bento grid, Story,
  Services and Reviews start with every part they can show - a second
  button, a photo, a cover, a button on a tile or step, how it works
- A sample's buttons show as buttons before their URL is filled in, and
  its images as a dashed box for you, left out for readers
- What an action did shows right beside its button - Save, Discard,
  Security, your own palette, replies, the contact and comment forms

### Fixed

- Pictures in a wide or full section, a gallery and a full-screen cover
  are sharp - they loaded a copy sized for the column and looked soft
- A Story with pictures finishes loading - its pictures kept being
  picked again, so the page never settled
- The banner shows above the list of your posts at /blog when your
  homepage is a page, instead of nowhere
- The page that's your homepage is listed as a page in Posts and pages,
  and the list's count says how many posts and how many pages it has
- Bold, italic or a line through text isn't shown in the editor until
  its closing mark is typed, as the preview shows it
- A footnote's text no longer looks like a URL in the editor
- Back leaves a post after following its contents or heading links,
  instead of going back through each heading
- A Hero's heading has no copy-link button beside it, so it stays centred
  on a phone
- Typing in Chinese, Japanese or Korean, Enter confirms the word in the
  post title and the editor's searches
- Restoring a backup made with an older passphrase brings its images back
  too
- A damaged backup no longer stops a new server from starting
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
- Backup and import shows straight away; Cloud storage fills in once
  your bucket answers
- On the Pinned tab, what a row's button did shows beside its own group
- A folded Settings card's summary goes when it's opened

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
