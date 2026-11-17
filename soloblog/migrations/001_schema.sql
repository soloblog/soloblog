-- Soloblog's database: every table at once. Everything written before the
-- first public release (1.0.0-beta) is folded into this one file. Each change
-- from here on is its own numbered file after it (db.run_migrations), and
-- a file that has shipped is never edited.

CREATE TABLE admin (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
, totp_secret TEXT NOT NULL DEFAULT '', recovery_codes TEXT NOT NULL DEFAULT '[]', totp_last_step INTEGER NOT NULL DEFAULT 0);

CREATE TABLE posts (
    id INTEGER PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '',
    published INTEGER NOT NULL DEFAULT 0,
    pinned INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
, cover_image TEXT NOT NULL DEFAULT '', views INTEGER NOT NULL DEFAULT 0, scheduled_at TEXT NOT NULL DEFAULT '', preview_token TEXT NOT NULL DEFAULT '', series_name TEXT NOT NULL DEFAULT '', series_order INTEGER NOT NULL DEFAULT 0, likes INTEGER NOT NULL DEFAULT 0, parent_slug TEXT NOT NULL DEFAULT '', pin_location TEXT NOT NULL DEFAULT 'header', comments_enabled INTEGER NOT NULL DEFAULT 1, pin_order INTEGER NOT NULL DEFAULT 0, redirect_from TEXT NOT NULL DEFAULT '', link_url TEXT NOT NULL DEFAULT '', password TEXT NOT NULL DEFAULT '', noindex INTEGER NOT NULL DEFAULT 0, canonical_url TEXT NOT NULL DEFAULT '', toc_style TEXT NOT NULL DEFAULT '', heading_fold TEXT NOT NULL DEFAULT '', cover_width TEXT NOT NULL DEFAULT '', unlisted INTEGER NOT NULL DEFAULT 0, seo_title TEXT NOT NULL DEFAULT '', share_image TEXT NOT NULL DEFAULT '', hide_list_cover INTEGER NOT NULL DEFAULT 0, extras TEXT NOT NULL DEFAULT '');

CREATE INDEX idx_posts_pub ON posts(published, pinned, created_at);

CREATE TABLE comments (
    id INTEGER PRIMARY KEY,
    post_slug TEXT NOT NULL,
    author_name TEXT NOT NULL,
    body TEXT NOT NULL,
    approved INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
, trashed_at TEXT, parent_id INTEGER, email TEXT NOT NULL DEFAULT '', confirm_token TEXT, confirmed_at TEXT, is_author INTEGER NOT NULL DEFAULT 0, notify_replies INTEGER NOT NULL DEFAULT 0, notify_token TEXT, source TEXT NOT NULL DEFAULT '', source_url TEXT NOT NULL DEFAULT '', author_url TEXT NOT NULL DEFAULT '', author_photo TEXT NOT NULL DEFAULT '');

CREATE INDEX idx_comments_post ON comments(post_slug, approved);

CREATE TABLE rate_hits (
    id INTEGER PRIMARY KEY,
    identifier TEXT NOT NULL,
    bucket TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX idx_rate_hits ON rate_hits(identifier, bucket, created_at);

CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT ''
);

CREATE VIRTUAL TABLE posts_fts USING fts5(slug UNINDEXED, title, body, tags);

CREATE TABLE image_meta (
    filename TEXT PRIMARY KEY,
    alt_text TEXT NOT NULL DEFAULT '',
    caption TEXT NOT NULL DEFAULT ''
, credit_name TEXT NOT NULL DEFAULT '', credit_url TEXT NOT NULL DEFAULT '', credit_source TEXT NOT NULL DEFAULT '');

CREATE TABLE post_views_daily (
    slug TEXT NOT NULL,
    day TEXT NOT NULL,
    views INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (slug, day)
);

CREATE TABLE contact_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL,
    is_read INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE post_revisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    saved_at TEXT NOT NULL
);

CREATE INDEX idx_revisions_slug ON post_revisions(slug, saved_at);

CREATE TABLE passkeys (
    id TEXT PRIMARY KEY,               -- the credential ID, base64url
    public_key BLOB NOT NULL,
    sign_count INTEGER NOT NULL DEFAULT 0,
    name TEXT NOT NULL,
    transports TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    last_used_at TEXT NOT NULL DEFAULT ''
);

CREATE TABLE post_reactions (
    post_slug TEXT NOT NULL,
    reaction TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (post_slug, reaction)
);

CREATE TABLE post_links (
    from_slug TEXT NOT NULL,
    to_slug TEXT NOT NULL,
    PRIMARY KEY (from_slug, to_slug)
);

CREATE INDEX idx_post_links_to ON post_links(to_slug);

CREATE TABLE post_translations (
    slug TEXT NOT NULL,
    lang TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    html TEXT NOT NULL,
    translated_at TEXT NOT NULL,
    PRIMARY KEY (slug, lang)
);

CREATE TABLE ap_followers (
    actor TEXT PRIMARY KEY,
    inbox TEXT NOT NULL,
    shared_inbox TEXT NOT NULL DEFAULT '',
    handle TEXT NOT NULL DEFAULT '',
    followed_at TEXT NOT NULL
);

CREATE TABLE ap_actors (
    id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    fetched_at TEXT NOT NULL
);

CREATE TABLE ap_interactions (
    activity_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,          -- "like" or "boost"
    actor TEXT NOT NULL,
    post_slug TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX idx_ap_interactions_post ON ap_interactions(post_slug);

CREATE TABLE published_log (
    slug TEXT NOT NULL,
    channel TEXT NOT NULL,       -- "activitypub" or "webmention"
    content_hash TEXT NOT NULL,
    done_at TEXT NOT NULL, remote_id TEXT,
    PRIMARY KEY (slug, channel)
);

CREATE TABLE webmentions (
    id INTEGER PRIMARY KEY,
    post_slug TEXT NOT NULL,
    source TEXT NOT NULL,
    target TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'mention',   -- reply, like, repost, bookmark, mention
    author_name TEXT NOT NULL DEFAULT '',
    author_url TEXT NOT NULL DEFAULT '',
    author_photo TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL DEFAULT '',
    published TEXT NOT NULL DEFAULT '',
    approved INTEGER NOT NULL DEFAULT 0,
    received_at TEXT NOT NULL,
    UNIQUE (source, target)
);

CREATE INDEX idx_webmentions_post ON webmentions(post_slug, approved);

CREATE TABLE webmentions_sent (
    slug TEXT NOT NULL,
    target TEXT NOT NULL,
    status TEXT NOT NULL,
    sent_at TEXT NOT NULL,
    PRIMARY KEY (slug, target)
);

CREATE TABLE subscribers (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    token TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    confirmed_at TEXT,
    unsubscribed_at TEXT
);

CREATE TABLE sources_daily (
    day TEXT NOT NULL,
    source TEXT NOT NULL,
    views INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (day, source)
);

-- The members area (members.py): readers who sign in by email to read
-- members-only posts - free, or paid through Stripe. Only adds: every
-- site that already exists keeps working, with no members until it
-- turns them on.

-- who can read a post: public | members | paid (also "visibility:" in
-- the post's own file, the source of truth)
ALTER TABLE posts ADD COLUMN visibility TEXT NOT NULL DEFAULT 'public';

CREATE TABLE members (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    name TEXT NOT NULL DEFAULT '',
    -- free | paid | comped (paid access given by the admin)
    status TEXT NOT NULL DEFAULT 'free',
    created_at TEXT NOT NULL,
    last_seen_at TEXT,
    note TEXT NOT NULL DEFAULT '',
    -- paid, through Stripe
    stripe_customer_id TEXT NOT NULL DEFAULT '',
    stripe_subscription_id TEXT NOT NULL DEFAULT '',
    -- Stripe's own subscription status: trialing, active, past_due,
    -- canceled, unpaid, incomplete
    subscription_status TEXT NOT NULL DEFAULT '',
    plan_interval TEXT NOT NULL DEFAULT '',      -- month | year
    plan_amount INTEGER NOT NULL DEFAULT 0,       -- in the currency's smallest unit
    plan_currency TEXT NOT NULL DEFAULT '',
    current_period_end TEXT,
    cancel_at_period_end INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_members_customer ON members(stripe_customer_id);

-- a sign-in or sign-up in progress: the emailed link and the 6-digit code
-- beside it, both kept only as hashes, good for 15 minutes and once
CREATE TABLE member_tokens (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL COLLATE NOCASE,
    token_hash TEXT NOT NULL UNIQUE,
    code_hash TEXT NOT NULL,
    purpose TEXT NOT NULL DEFAULT 'signin',       -- signin | signup
    name TEXT NOT NULL DEFAULT '',
    newsletter INTEGER NOT NULL DEFAULT 0,
    next TEXT NOT NULL DEFAULT '',                -- where to go after
    attempts INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used_at TEXT
);
CREATE INDEX idx_member_tokens_email ON member_tokens(email);

-- a signed-in browser: the cookie's value kept only as a hash
CREATE TABLE member_sessions (
    id TEXT PRIMARY KEY,
    member_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE INDEX idx_member_sessions_member ON member_sessions(member_id);

-- each Stripe event handled once, however often it's sent
CREATE TABLE stripe_events (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    received_at TEXT NOT NULL
);

-- a comment from a signed-in member (members-only comments)
ALTER TABLE comments ADD COLUMN member_id INTEGER;

-- API keys (apikeys.py): what an app, a script or an AI assistant uses to
-- read and write the site for its one admin. Only adds - a site that
-- already exists has no keys until its admin makes one.

CREATE TABLE api_keys (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    -- read | draft | publish, each allowing what the one before does
    scope TEXT NOT NULL DEFAULT 'read',
    -- the key itself is shown once and never kept: its SHA-256 is
    key_hash TEXT NOT NULL UNIQUE,
    -- its first characters, so the admin can tell keys apart
    prefix TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_used_at TEXT,
    revoked_at TEXT
);

-- "Sign in with your site" (IndieAuth, routes/micropub.py): an app asks,
-- the admin approves, and the app gets an API key. Only adds.

-- the app a key was made for, when it was made by signing in - "" for a
-- key made by hand in Settings > Security
ALTER TABLE api_keys ADD COLUMN client_id TEXT NOT NULL DEFAULT '';

-- an approval waiting for the app to fetch its key: once, within minutes
CREATE TABLE indieauth_codes (
    id INTEGER PRIMARY KEY,
    code_hash TEXT NOT NULL UNIQUE,
    client_id TEXT NOT NULL,
    client_name TEXT NOT NULL DEFAULT '',
    redirect_uri TEXT NOT NULL,
    -- PKCE: the app proves it's the one that asked (S256 only)
    code_challenge TEXT NOT NULL,
    -- what the admin allowed: read | draft | publish (apikeys.SCOPES)
    scope TEXT NOT NULL,
    -- what the app asked for, as it asked (create update media...)
    requested TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used_at TEXT
);

-- A second kind of API key (apikeys.py), for apps that publish to Ghost -
-- Ulysses and iA Writer: an "id:secret" that the app signs each request
-- with, rather than sends. Only adds; existing keys stay "bearer".

-- bearer (sb_..., sent as it is) | signed (id:secret, a signed token)
ALTER TABLE api_keys ADD COLUMN kind TEXT NOT NULL DEFAULT 'bearer';
-- a signed key's public id - what the app names it by in each token
ALTER TABLE api_keys ADD COLUMN key_id TEXT NOT NULL DEFAULT '';
CREATE INDEX idx_api_keys_key_id ON api_keys (key_id);

-- Webhooks (webhooks.py): addresses the site tells when something
-- happens - a post goes live, a comment arrives - each message signed.
-- Only adds.

CREATE TABLE webhooks (
    id INTEGER PRIMARY KEY,
    url TEXT NOT NULL,
    -- comma list: post.published, comment.created
    events TEXT NOT NULL,
    created_at TEXT NOT NULL,
    -- the last delivery: when, its HTTP status (0: it couldn't connect), why it failed
    last_at TEXT,
    last_status INTEGER,
    last_error TEXT NOT NULL DEFAULT ''
);

-- a post's or page's background sound (Post settings > Page): one of
-- the media library's audio files, looping, played only when a visitor
-- presses its button
ALTER TABLE posts ADD COLUMN sound TEXT NOT NULL DEFAULT '';

-- a post's own places for the side panels (Post settings > Page): the
-- tag cloud, archive links and About the author, each off, under the post,
-- or beside it on the left or right - "tags=left,author=off", only those it
-- changes; "" follows Settings
ALTER TABLE posts ADD COLUMN sides TEXT NOT NULL DEFAULT '';

-- what last used a key - the API, a writing app (Micropub), an AI
-- assistant (MCP) or a Ghost app - so an unexpected use stands out
ALTER TABLE api_keys ADD COLUMN last_used_via TEXT NOT NULL DEFAULT '';

-- an image's dark mode version: another upload shown in its place while
-- the site is dark (Media > an image's details)
ALTER TABLE image_meta ADD COLUMN dark_version TEXT NOT NULL DEFAULT '';

-- contact messages go to a Trash first, as comments do
ALTER TABLE contact_messages ADD COLUMN trashed_at TEXT;

-- a page's own space between its sections (pages.SPACINGS); '' follows the site's
ALTER TABLE posts ADD COLUMN section_space TEXT NOT NULL DEFAULT '';

-- a page's title: '' left, 'centre' or 'hidden' (still there for screen readers)
ALTER TABLE posts ADD COLUMN title_style TEXT NOT NULL DEFAULT '';

-- a page's width: '' follows the site's column, 'wide' lets sections and pictures run wider
ALTER TABLE posts ADD COLUMN page_width TEXT NOT NULL DEFAULT '';

-- the page's --- lines make a slide deck
ALTER TABLE posts ADD COLUMN slides INTEGER NOT NULL DEFAULT 0;

-- a note in the wiki (/wiki)
ALTER TABLE posts ADD COLUMN in_wiki INTEGER NOT NULL DEFAULT 0;

-- shows when the page was last updated, and reminds the admin to update it
ALTER TABLE posts ADD COLUMN remind_update INTEGER NOT NULL DEFAULT 0;

-- an image's phone version: another upload shown in its place on a phone
-- (Media > an image's details)
ALTER TABLE image_meta ADD COLUMN phone_version TEXT NOT NULL DEFAULT '';
-- how a page's sections come into view (pages.SECTION_MOTIONS); '' follows the site's
ALTER TABLE posts ADD COLUMN section_motion TEXT NOT NULL DEFAULT '';
