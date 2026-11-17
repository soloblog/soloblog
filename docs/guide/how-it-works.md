# Privacy and how it works

This page explains a few things behind the scenes: how your site is kept
safe, what it sends to other services, what it stores on visitors'
devices, why email sometimes lands in spam, and where your writing is
kept. There's nothing you need to do here - read it when you want to
know.

**Contents:** [How your site is kept safe](#how-your-site-is-kept-safe) ·
[What Soloblog sends and never collects](#what-soloblog-sends-and-never-collects) ·
[Cookies and consent](#cookies-and-consent) ·
[Why email lands in spam](#why-email-lands-in-spam) ·
[Where posts are kept](#where-posts-are-kept)

## How your site is kept safe

Soloblog is built so that a site run by one person, with no developer
to call, stays safe by default. Most of what follows needs nothing from
you, and each part links to where you can do more.

**Your login.** Only you can reach the admin: every page under it asks
you to log in first. Your password is stored scrambled, so even someone
holding a copy of your data can't read it back, and it needs at least 8
characters - a long one you use nowhere else is best. After five wrong
passwords in 15 minutes from one place, Soloblog makes whoever's trying
wait. If wrong passwords pour in from many places at once, only a
browser you've logged in with before can use the password until it
stops. With email set up, you get an email about that, and one
whenever a browser your site hasn't seen before logs in, so you know
straight away if it wasn't you. It's the switch **Email me when a new
device signs in**, on to start with. A passkey (your fingerprint, face or device
PIN) or two-factor login (a code from an app on your phone) adds a second
step, and a recovery key lets you back in if you forget your password.
You stay logged in for 14 days on each browser, or until you close it if
you untick **Keep me signed in**, and **Log out other devices** ends the
rest. **Site health** tells you when you have only a password, or no
recovery key. See [Keep the login safe](run.md#keep-the-login-safe).

**Your visitors.** Visitors can read your site, comment, send you a
message and sign up, and that's all: they can't log in to the admin,
change your site or upload a file. A comment is plain text - anything typed as
HTML shows as typed, with no pictures or links, so a comment can't
run anything on your page. New comments wait for your approval, and when
email is set up the commenter confirms their address first. Forms
are guarded against spam with a hidden field that bots fill in and
people don't, a limit on how many one address can send an hour, your
list of **Blocked words**, and, if you add it, an extra check
(Cloudflare Turnstile or hCaptcha). See
[Moderate comments](grow.md#moderate-comments). Your site also refuses
anything that changes it unless it comes from a page on your own
address, so another website can't trick your browser into posting for
you while you're logged in.

**Files.** Pictures you upload are re-saved by Soloblog in a web
format, which drops any location or camera details stored inside them,
and a file that isn't a picture it knows is refused. Audio, video and PDF files are accepted
only when their contents match what they say they are.

**What your site sends out.** When Soloblog contacts an address for
you (to check a link, import a blog or call a webhook), it must be a public
one on the internet, never a machine inside your own network. The exceptions are
a translation server or a storage bucket that you typed in yourself.
What your site does send, and to whom, is listed in
[What Soloblog sends and never collects](#what-soloblog-sends-and-never-collects).

**Your data.** Your writing, uploads and database stay in your site's
data folder on your own host. Nothing about your site or readers is
sent to the people who make Soloblog, and nothing tracks visitors unless
you add it - see [Cookies and consent](#cookies-and-consent). A backup is
one file you download, or made for you in cloud storage you rent; with
`BACKUP_PASSPHRASE` set on your host, what's in the bucket is locked, so
even the storage company can't open it. See
[Back up and restore](run.md#back-up-and-restore). Keep backups private:
they include your settings and the keys to services you've connected.
**Site health** keeps watch: it checks that your site uses HTTPS, that
logins are signed with a secret of your own, and that your backups are
recent and would restore, and it emails you when something needs you.
See [Check Site health](run.md#check-site-health). On an HTTPS site,
browsers are also told to keep using HTTPS, and other websites can't
show your pages inside theirs.

**Updates.** A security problem comes before any new feature, and the
people who make Soloblog check for known weaknesses in the parts it's
built from before each release and every week. Only the latest version
gets fixes, so keep up. An update keeps your posts, images and settings
as they are; the database upgrades itself. **Site health** tells you
when one is out. See [Update Soloblog](run.md#update-soloblog).

**Found a problem?** Please don't post it publicly. Report it privately
through the **Security** tab of the Soloblog repository on GitHub, with
what you found and how to repeat it. You get a reply within 3 days, and
the fix goes out in the next update, with credit to you if you'd like it.
The full policy is in [SECURITY.md](../../SECURITY.md), and the outside
standards Soloblog is held to are in [STANDARDS.md](../STANDARDS.md).

## What Soloblog sends and never collects

Soloblog never reports how you use it. It doesn't send usage data or
count installs - not to the people who make Soloblog, and not to anyone
else. Nobody but you knows your site exists.

Your site only connects to other services for the features you turn on:

| When | Where it connects | What's sent |
|---|---|---|
| Once a day, to see if there's a new version of Soloblog | GitHub | An ordinary request for the latest version - nothing about your site |
| Site health's daily checks | GitHub, your own address, rdap.org, and Cloudflare's or Google's DNS | Only public names: your domain, to check its security certificate, when it needs renewing, and its email records |
| Emails your site sends - sign-ins, the newsletter, alerts | Your own email provider | The emails themselves |
| Paid members | Stripe | Checkout and billing, between your reader and Stripe |
| Sharing, the fediverse, webmentions | Bluesky, Mastodon, your followers' servers, and the sites you link to | The posts you publish |
| Translations, stock photos, cloud backups | The service you set up | What that feature needs - text to translate, a photo search, your backup |
| Comments, spam checks, analytics, embeds from other services | The service you chose | Loaded by your visitors' browsers, under that service's terms |

**Don't want Site health asking other servers?** Open **Site health**,
and under **How it checks**, switch off **Check certificate, domain
and email**. The daily check for a new version stops when your host sets
`UPDATE_CHECK=0` - a setting on your host, not in Soloblog.

**A bug report is yours to share.** In **Site health**, the **Info** tab
has **Copy for a bug report**. It copies a summary to your clipboard and
sends nothing anywhere. The summary has your Soloblog version, rough
counts, which features are on, and the last week's problems with
personal details taken out. It never includes your writing, names, email
addresses or your site's address. You can read all of it before you copy
it.

**Your own stats keep nothing about your readers** - no IP addresses, no
browser details, and nothing that follows a person from one visit to the
next.

## Cookies and consent

In the EU and the UK, a website has to ask visitors before it stores
anything on their device that isn't needed for what they came to do -
analytics cookies, ads and trackers, for example. Anything that is
needed doesn't need asking.

Everything Soloblog stores by itself is the kind that's needed, so your
site doesn't need a cookie banner:

| What's stored | Why it's allowed without asking |
|---|---|
| Your admin login, and a note that tells a new browser from one you've used before | You asked to log in |
| A member's sign-in | They asked to sign in |
| A reader's choice of colours, their name in the comment form, and their answer to the cookie banner | They chose it, on your site |

Some things you add to your site do need asking. Soloblog handles them:

- **Google Analytics** waits until a visitor accepts the cookie banner.
  You set up the banner in **Settings > Analytics and ads**, under
  **Cookie consent**. Cloudflare Web Analytics and Plausible don't use
  cookies, so they never need it.
- **Code you paste** in **Settings > Integrations > Custom code** runs
  as it is. If it tracks visitors, switch on **This code sets cookies or
  tracks visitors**, and it waits for the banner too.
- **Comments from other services, and embedded videos,** only load when
  a reader chooses to show them.
- **AdSense** needs Google's own consent message for visitors in the EU,
  UK and Switzerland. You turn it on in your AdSense account, under
  **Privacy & messaging**.
- **Paid members** pay on Stripe's own pages, under Stripe's terms.

The cookie banner only appears when something on your site needs it, and
**Settings > Analytics and ads** tells you what that is.

A privacy page is good to have either way, saying what you collect and
why. The **Privacy policy** template starts one for you, with the parts
about Soloblog already outlined - fill in the parts in brackets. It's an
outline to start from, not legal advice.

## Why email lands in spam

Anyone can type any address as the sender of an email, so inboxes don't
trust an email just because of the address it says it's from. They trust
it when the domain it's sent from vouches for it. Without that,
newsletters, comment confirmations and password resets land in spam, or
don't arrive at all.

A domain vouches for its emails with three records. You add them where
your domain's settings (its DNS) are managed - usually the company you
bought the domain from, or Cloudflare:

- **SPF** - a TXT record that lists who may send email for your domain.
  Your email provider gives you the exact text. A domain can only have
  one.
- **DKIM** - a key your email provider signs each email with. It's added
  as a TXT or CNAME record, which your provider's setup page gives you.
  Resend's is at `resend._domainkey`.
- **DMARC** - a TXT record at `_dmarc` that says what to do with email
  that fails the other two checks. Gmail and Yahoo expect one from
  anyone sending a newsletter. The simplest is `v=DMARC1; p=none`.

Site health checks all three, and tells you which one is missing.

This is also why sending from a Gmail or iCloud address through Resend
doesn't work well: you can't add records to gmail.com, because you don't
own it. Send from an address at your own domain instead. See
[Set up email that arrives](run.md#set-up-email-that-arrives).

## Where posts are kept

Each post is an ordinary text file, in markdown, in your site's data
folder. Any text editor can open it, so your writing is never locked
inside Soloblog.

The data folder holds three things:

- **`posts`** - one markdown file for each post and page.
- **`uploads`** - your images and files, and the originals of any you've
  rotated or cropped.
- **`blog.db`** - one database file for everything else: settings,
  comments, members, subscribers and stats. A free app called
  [DB Browser for SQLite](https://sqlitebrowser.org) can open it.

A backup is these same three things, in a zip file.

The data folder has to be on lasting storage - a disk or volume your
host keeps between updates. If it isn't, the next update starts your
site empty, and Site health warns you before that happens. The hosting
guide says how to set this up for each host: see
[Open setup the first time](../DEPLOYMENT.md#open-setup-the-first-time).

If you edit a post's file directly on your server, Soloblog reads the
change the next time it starts.

See also: [Back up and restore](run.md#back-up-and-restore)
