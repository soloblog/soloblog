# Common questions

Short answers to what people ask most, each with a link to more in the
[user guide](guide/getting-started.md) or the [deployment guide](DEPLOYMENT.md).

**Contents:** [About Soloblog](#about-soloblog) · [Getting it running](#getting-it-running) ·
[Writing and posts](#writing-and-posts) · [Readers](#readers) ·
[Search engines and sharing](#search-engines-and-sharing) · [Keeping it safe](#keeping-it-safe)

## About Soloblog

### What is Soloblog?

A free, open source blog and website for one person, run on your own
server or hosting account. You write in your web browser, and your posts
are saved as files you own. It comes with what a personal site needs -
pages, a menu, comments, a newsletter, members, feeds, search, stats -
without plugins.

### Is it free?

Yes. Soloblog is open source, under the MIT licence. What you pay for is
where it runs - a small server or a hosting service, usually a few
dollars a month - and a domain name if you want one. See
[Choose where to run it](DEPLOYMENT.md#choose-where-to-run-it).

### What if Soloblog stops being developed?

Your site keeps running, as it is, for as long as your host runs it -
it doesn't depend on any server of ours. Your posts are ordinary files
you can take anywhere, a backup is one download, and anyone can carry the
code on. [SUPPORT.md](../SUPPORT.md) says what to expect meanwhile.

### Can several people write on the same blog?

No - on purpose. Soloblog has one author: you. Readers can become
members, free or paid, to read posts that are for them, but they never
write. It stays simple because it's one person's site.

### Do I need to know how to code?

Not to write and run your site: everything is in the admin, the part of
your site only you can open, in plain words. Getting it online the first
time is the technical part, and a hosting service with a one-click button
does most of it for you in a few minutes. See [Put it on a hosting service](DEPLOYMENT.md#put-it-on-a-hosting-service).

### Can I add a feature of my own?

Yes. Soloblog is open source, so you can change your own copy - and an
AI coding agent, like Claude Code, Codex or Cursor, can do it for you
while you describe what you want in plain words: a reading list page, a
box beside your posts, a new kind of section. The steps, from making your
copy to putting it on your blog, are in
[Change a site with an AI agent](DEVELOPMENT.md#change-a-site-with-an-ai-agent).

### Does it work on my phone?

Yes - your site, and the admin where you write and run it. On a phone,
the editor has a bar of buttons above the keyboard, and everything else
is a step away, under **+**.

## Getting it running

### What's the easiest way to put it online?

A hosting service with a one-click button - Render, Railway, Fly.io and
others, listed in
[Put it on a hosting service](DEPLOYMENT.md#put-it-on-a-hosting-service).
Pick a plan with lasting storage (a disk that's kept between updates), or
your posts are lost when the site updates. Or connect
[cloud storage](DEPLOYMENT.md#keep-files-in-cloud-storage), which
keeps a copy for you.

### Can I use my own domain?

Yes. Point your domain at your host - each host explains how in its own
settings - then open setup at your domain. Already set up at another
URL? Change your site's URL in **Settings > URL and SEO**, to
something like `https://example.com`. See
[Use a custom domain](DEPLOYMENT.md#use-a-custom-domain).

### How do I update to a new version?

The bottom of every admin page tells you when one is out, with **How to
update**. Usually it's your host's redeploy button. Set up the **Update
now** button once, and it's one click from then on. Your posts and settings stay as they are. See
[Update Soloblog](guide/run.md#update-soloblog).

### I lost the setup token or forgot my password

**The setup token** (the one-time code to create your account): the
setup page says where your host shows it - on Render, it's in the
service's **Environment**. Elsewhere, restart your site and find a new
one in the server's log. Or, on your host, set
`SETUP_TOKEN` to a code you choose and restart
([Open setup the first time](DEPLOYMENT.md#open-setup-the-first-time)).

**Your password:** select **Forgot password?** on the login page and use
your **recovery key**. No key? It can email you a link instead, if email
is set up - or see
[Troubleshooting](guide/troubleshooting.md#i-forgot-my-password).

### My site isn't sending email

Open **Settings > Email** and select **Send a test email** - if it can't
go, it says why and what to try. Most often it's one of these:

- **Gmail, iCloud or Yahoo:** use an *app password* - a separate
  password you make in your account's security settings - not the
  password you sign in with.
- **Outlook.com or Microsoft 365:** they no longer let other apps send
  with a password. Use Resend instead.
- **Your host blocks sending from an email account** (Render's free plan,
  Railway's Hobby plan and some others): use Resend, an email service
  that works on every host.
- **Emails reach you, but nobody else:** your From address is at
  resend.dev, which Resend keeps for trying it out. Add your own domain
  in Resend and send from an address there.

[Set up email that arrives](guide/run.md#set-up-email-that-arrives) has the rest.

### Can someone use my site to send email as me?

No. Your site sends only from the From address you set, and only to you
or to someone who typed their own address - to confirm a comment, a
sign-up or a sign-in - a few times an hour at most. Resend sends only
from a domain verified in your own account, so no one can send as your
domain without your API key; in Resend you can make a key that sends
only from that one domain.

## Writing and posts

### Where are my posts kept?

As ordinary text files, in markdown - one per post, readable in any text
editor - with a database file beside them for everything else, like
comments and settings. See [Where posts are kept](guide/how-it-works.md#where-posts-are-kept).

### How do I move my site to a new host?

With cloud storage connected, start Soloblog on the new host with the
same `S3_` settings: it restores itself from the newest backup in your
bucket, images and login included. Without it, download a backup with
everything selected, and on the new site's setup page select **Moving
your site? Restore a backup**. Both are in
[Move to a new server or domain](DEPLOYMENT.md#move-to-a-new-server-or-domain).

### Can I move my blog from WordPress, Ghost, Medium or Substack?

Yes: **Settings > Backup and import > Import from another blog** brings in
your posts, pages, tags and images, and old URLs keep working. See
[Move a blog to Soloblog](guide/run.md#move-a-blog-to-soloblog).

### What's the difference between a post and a page?

A page is a post you put in your site's menu or footer - About, Contact,
Privacy. It has a short URL like `/about`, and stays out of the list
of your posts. See [Make a page for the menu or footer](guide/pages.md#make-a-page-for-the-menu-or-footer).

### What's the difference between a template, a section and Post settings?

A **template** is a page you start from, with its sections, sample words
and settings already in place. A **section** is a part of a page with its
own heading - plans, kind words, a row of numbers, a recipe's ingredients -
and any page can have as many as it likes. **Post settings** are the
page's own choices: its title, width, cover, contents and what shows
around it. See
[Templates, sections and Post settings](guide/put-together.md#templates-sections-and-post-settings).

### How do I make a page look like a recipe, a resume or a landing page?

Start it from the template for that kind of page: select **New post**,
then **Template** under the title, and choose it. You get the page with
its sections and settings in place, ready to fill in. See
[Make a recipe, resume or other kind of page](guide/pages.md#make-a-recipe-resume-or-other-kind-of-page).

### Can I make new posts start from a template?

Yes. In **Settings > Editor**, under **Templates**, choose one beside
**New posts start from**. **New post** then opens from it, with no list to
choose from. See
[Choose what new posts start from](guide/writing.md#choose-what-new-posts-start-from).

### How do I add a template to a page I've already written?

Open the page's **Post settings**, then **Template**, and select **Apply a
template**. Its sections are added at the end of the page and its settings
replace the page's own, and **Undo** puts it all back. See
[Apply a template to a page](guide/writing.md#apply-a-template-to-a-page).

### Why is there a line beside a setting?

A thin coloured line down the left of a setting means it's set differently
from its default, with a small **Reset** button (the ↺ arrow) beside it.
In a page's Post settings, the default is your site's setting - say, a page
with its contents off where the site shows them. On the Settings pages, it's
what your starting style sets, or Soloblog's own for anything a style
doesn't change, so a style you've just picked shows no lines. Select
**Reset** to put the setting back; in Post settings it follows any later
change to the site, too. See
[Which setting wins](guide/put-together.md#which-setting-wins).

### Can I show my photos, designs or artwork as a portfolio?

Yes. A **Portfolio** section shows your work images first - as tiles,
in rows edge to edge, or a screen each - and each project can be a page
of its own, started from the **Project** template and laid out like a
magazine. Either works as a post or a page. See
[Show work as a portfolio](guide/pages.md#show-work-as-a-portfolio).

### Do I need a privacy policy or terms?

If your site collects email addresses - comments, the newsletter,
members, the contact form - a privacy policy is good practice, and the
law in many places. Start a new post from the **Privacy policy** or
**Terms** template: each starts as a footer page with the parts to fill
in, in brackets. They're outlines, not legal advice.

### Can I use my own colours?

Yes: make a palette in [daisyUI's theme generator](https://daisyui.com/theme-generator/),
copy its CSS, and paste it in **Settings > Style**, under **Colours > Custom colours**. It's then a palette like the others, for your site
and in readers' Colours menu. It brings its corner rounding, borders and
shadows with it, too.
See [Add custom colours](guide/design.md#add-custom-colours).

### Can an image look different when the site is dark?

Yes. Upload a dark version of it, then choose that under **Dark mode
version** in the light one's details, in **Media**. Readers see the one
that matches their light or dark setting, and it switches when they do.
See [Organise media](guide/run.md#organise-media).

### Can an image look different on a phone?

Yes. Upload the phone version of it, such as a screenshot taken on a
phone, then choose that under **Phone version** in the wide one's
details, in **Media**. A phone shows it in place of the usual image.
To give the phone image a dark version too, open the phone image's
own details and choose one under **Dark mode version**: a phone shows it
while the site is dark. See [Organise media](guide/run.md#organise-media).

### Can I schedule posts, or keep them private?

Yes: pick a publish time, make a post unlisted (only people with the
link find it), give it a password, or make it for members. See
[Schedule a post](guide/writing.md#schedule-a-post) and
[Post settings](guide/reference.md#post-settings).

### Is there a distraction-free way to write?

Yes: **Focus**, above the editor's toolbar (or press **Ctrl+Shift+F**),
or **Edit in Focus** on a post's row in **Posts and pages**.
Your writing fills the screen, and once you start typing, everything
else slides out of the way. See [Write in Focus](guide/writing.md#write-in-focus).

### Can I undo a change to a post?

Yes: each post keeps its last 50 saved versions, in **Post settings >
History**. You can see what each one changed, and bring any of them
back. See
[Restore an earlier version](guide/writing.md#restore-an-earlier-version).

## Readers

### Can some posts be for members only?

Yes - switch on **Let readers become members** in **Settings > Members**,
then choose **Who can read it** in a post's settings: everyone, members
or paid members. Readers join with their email address, and sign in with
a link or code sent by email - no passwords. See
[Let readers become members](guide/grow.md#let-readers-become-members).

### Can readers pay to be members?

Yes, through Stripe, a payment service: a monthly or yearly price, with a free trial if you
like. The money goes to your Stripe account - Soloblog takes nothing. See
[Let readers pay](guide/grow.md#let-readers-pay).

### How do readers follow my blog?

In a feed reader app (your site has feeds built in), by email if you
turn the newsletter on, and from Mastodon and the rest of the fediverse
if you turn that on. See
[Send a newsletter](guide/grow.md#send-a-newsletter) and
[Join the fediverse](guide/grow.md#join-the-fediverse).

### Can readers comment without an account?

Yes: they give a name and an email address, confirm it with a link sent
by email, and you approve each comment before it shows. Or use Giscus, Bluesky or another comment system. See
[Moderate comments](guide/grow.md#moderate-comments) and
[Use another comment system](guide/grow.md#use-another-comment-system).

### Do I need a cookie banner?

Usually not: the cookies Soloblog uses by itself are the kind the law
doesn't ask about - logins, and members signing in. If you add Google
Analytics, ads or tracking code, your site asks visitors for you, and
**Settings > Analytics and ads**, under **Cookie consent**, says what
it's asking about. See
[Cookies and consent](guide/how-it-works.md#cookies-and-consent).

### Does Soloblog track how I use it?

No. It never sends usage statistics or counts of installs anywhere. See
[What Soloblog sends](guide/how-it-works.md#what-soloblog-sends-and-never-collects).

## Search engines and sharing

### Will search engines find my blog?

Yes, with nothing to set up. Add your site to Google Search Console and
Bing Webmaster Tools to see how it's doing in search - their
verification codes go in **Settings > URL and SEO**, under
**Advanced**. See
[Show up in search engines](guide/grow.md#show-up-in-search-engines).

### Can a post have a different title in search results?

Yes: **Post settings > Search engines** has a title for search results
and an image for shares.

### Can I hide a post, or the whole site, from search engines?

Yes: **Post settings > Search engines** for one post, or **Settings >
URL and SEO** for everything.

## Keeping it safe

### How does Soloblog look after my site and my readers?

Much of it is built in, with nothing to set up:

- **Your login.** After a few wrong passwords, Soloblog makes whoever's
  trying wait before they can try again. If wrong passwords pour in from
  many places at once, only a browser that has logged in before can use
  the password until it stops, and your site emails you. A passkey or
  two-factor authentication
  adds a second step - see [Keep the login safe](guide/run.md#keep-the-login-safe).
- **Your readers.** Members sign in with a link or a code sent to their
  email, so they have no password to forget. Their details stay on your
  site, and Soloblog never sends them to us - see
  [What Soloblog sends and never collects](guide/how-it-works.md#what-soloblog-sends-and-never-collects).
- **Updates.** A new version keeps your posts, images and settings as
  they are. **Site health** tells you when one is out, and says so
  clearly when it's one to install soon.
- **A watchful eye.** **Site health** checks your backups, email and
  storage, and emails you if something needs your attention - see
  [Check Site health](guide/run.md#check-site-health).

The code is open for anyone to read, and every version is checked
against [well-known standards](STANDARDS.md) before it's released. The
whole image is in
[How your site is kept safe](guide/how-it-works.md#how-your-site-is-kept-safe).
Found a problem? [Tell us about it privately](../SECURITY.md).

### How do I back up?

In **Settings > Backup and import**, **Download** gives you one file
with everything in it. To restore, upload that file on the same page.
With cloud storage connected, backups are made for you. See
[Back up and restore](guide/run.md#back-up-and-restore).

### How do I keep my account safe?

Use a long password, and add a passkey (log in with your fingerprint or
face) or two-factor authentication (a code from an app on your phone), in
**Settings > Security**. See [Keep the login safe](guide/run.md#keep-the-login-safe).

### Something's wrong - where do I ask?

Check [Troubleshooting](guide/troubleshooting.md) first. Then select
**Report a problem**, at the bottom of any admin page, to report a bug.

### I have an idea, or a question this page doesn't answer

**Ideas and questions**, at the bottom of any admin page, opens the
project's discussion forum: ask there, or suggest something - others can
upvote ideas, and popular ones go on the roadmap.
