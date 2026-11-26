# Getting started

This page takes you from a fresh install to a site that's yours, with
your first post on it. Soloblog is a free, open source blog and website
for one person, so there's one account to log in with: yours.

**Contents:** [Set up the site](#set-up-the-site) ·
[Write and publish the first post](#write-and-publish-the-first-post) ·
[Get around the admin](#get-around-the-admin) ·
[Make it yours in 10 minutes](#make-it-yours-in-10-minutes)

## Set up the site

Create your account, give your site a name and a look, then work through
a short list that makes it safe and ready to share.

1. In your browser, go to your site's URL with `/setup` on the end -
   for example `https://example.com/setup`.
2. Enter the **Setup token**. This is a one-time code that proves you're
   the person who installed Soloblog. The page tells you where to find
   it: it's either the `SETUP_TOKEN` you chose when you installed
   Soloblog, or it's in your server's log, on the lines marked `[setup]`.
3. Choose a password of at least 8 characters, type it again, and select
   **Create admin account**.
4. Your **recovery key** is shown next. Save it with **Copy** or
   **Download**, and keep it somewhere safe - a password manager, or
   printed and put away. It's shown only this once. Then select **I've
   saved it**.
5. Four short screens follow: **Your site** (its name, a tagline, its
   language and time zone), **About you**, **Look** (your icon or logo,
   and your colours) and **Style**. Fill in what you want on each and
   select **Continue**. A screen you leave as it is changes nothing, and
   **Back** returns to the screen before.

Your site is ready. The last screen lists six jobs worth doing before
you share it:

- **Set up email**, so password resets, sign-in alerts and new comments
  reach you.
- **Protect your login** with a passkey.
- **Plan your backups**: download one, or connect cloud storage.
- **Describe your site** in a sentence, for search results and link
  previews.
- **Use a custom domain**, a domain like yourname.com.
- **Write your first post**.

Select one to open the **Settings** page where it's done. Each is checked
off automatically once it is - there's nothing to mark.

The same list stays in **Getting started**, at the bottom of the admin
menu, and opens from any page. The number beside it shows how far you've
got. **Remind me later** closes the list and keeps it in the menu;
**Don't show again** takes it out of the menu.

**Closed the browser before the last screen?** Open **Getting started**
and select **Finish setting up your site's name, about you and look**.

**Want to go through the setup screens again?** Open **Settings > Name
and homepage**, then **Identity**, and select **Run setup again**.
Nothing changes until you change it, and everything the screens ask is
in **Settings** too.

**Chose Don't show again?** Open **Settings > Name and homepage**, then
**Identity**, and select **Open Getting started**. The button is there
while a job on the list is left to do.

**What's the recovery key for?** If you forget your password, the
recovery key lets you choose a new one. You don't need email or access
to your server.

**What does Set up email need?** It opens **Settings > Email**, which
asks for two things. The first is your own email address, so your site
can send you password resets and news about comments. The second is a
way to send those emails: a key from Resend, an email service with a
free plan, or an email account you already have, like Gmail. **Send a
test email** checks it works. The steps are in
[Set up email that arrives](run.md#set-up-email-that-arrives).

**Don't use an address at resend.dev.** Resend keeps those for trying it
out: your test arrives, but emails to anyone else - members' sign-in
links, comment confirmations, the newsletter - don't.

**Seeing a warning that your site isn't on lasting storage?** Fix it
before you write anything. Without lasting storage, your posts are lost
the next time your site is updated. The warning says how to fix it on
your host. See also
[Open setup the first time](../DEPLOYMENT.md#open-setup-the-first-time).

**Moving a site you already have?** On the setup page, select **Moving
your site? Restore a backup** instead of creating an account - see
[Move to a new server or domain](../DEPLOYMENT.md#move-to-a-new-server-or-domain).

**Lost the setup token?** See
[I lost the setup token](../FAQ.md#i-lost-the-setup-token-or-forgot-my-password).

## Write and publish the first post

Put your first post on your blog for readers to see.

1. Select **New post**, the button at the top of the admin menu.
2. Type a title where it says **Title**, then write your post below it.
3. Select **Settings** - the gear icon beside **Save** - and switch
   **Published** on.
4. Select **Save**.

Your post is now on your blog. To see it as readers do, select **View** -
the eye icon beside **Save**.

**What's the draft called "Welcome to your new site"?** A short note
that comes with every new site: where things are, and a pointer to
**Getting started**. It's a draft, so only you can see it, and it doesn't
count as your first post. You'll find it in **Posts and pages**. Read it,
then move it to the trash.

**Want your writing to look a certain way?** The toolbar above the text
has headings, lists, links and images. **Insert**, at the right of the
toolbar, has everything else - tables, videos, buttons and more. See
[Writing posts](writing.md) for all of it.

## Get around the admin

The admin is where you run your site. Here's where things are, and what
works the same on every page.

The **admin menu** runs down the left. At the top is your site's name -
select it to open your site - and **New post**. Below them, every part of
the admin, under three small headings:

| Heading | Item | What's there |
|---|---|---|
| Content | Posts and pages | Everything you've written. Edit, publish, pin, tag or trash it, or see it on a calendar |
| | Media | Your images, audio, video and PDFs |
| Audience | Comments | Comments waiting for your approval, approved ones, and mentions from other sites |
| | Contact messages | What visitors sent through your contact form. Shows once the form is on |
| | Members | Your members, free and paid. Shows once members are on |
| | Newsletter | Your subscribers. Shows once the newsletter is on |
| | Stats | Views, your top posts and where readers came from |
| Manage | Site health | Anything that needs you: updates, backups, security, email |
| | Settings | Everything about your site, one page at a time |
| | Help | This guide, common questions, hosting and more |

At the bottom of the menu are **Getting started** (until you choose **Don't show again**
it), **View your site** and **Log out**.

**Comments** and **Contact messages** show a number when something new is
waiting for you.

**On a phone,** the admin menu is hidden to save room. The bar along the
top has the menu button on the left, which opens it. On the right are
search, **Colours**, and a gear icon with a short list of admin pages.

**On your site and want to get back to the admin?** Select the gear icon
in your site's header and choose where to go. Only you see the gear icon, while
you're logged in.

**What works the same everywhere:**

- **The result shows beside the button you pressed** - "Saved", or what
  went wrong and what to do. Nothing pops up in a corner.
- **Switches and choices save the moment you change them.** **Undo**
  shows beside "Saved" in case you change your mind. When you type
  something, a **Save** button shows at the bottom of the screen.
- **Trash and delete ask first.** After something moves to the trash,
  **Undo** brings it straight back.
- **The buttons on each row are small icons.** Point at one to see its
  name. On a phone, they're in the row's **⋯** menu, with their names.
- **Search**, at the top of every page, finds any admin page, setting or
  Help page as you type.
  Select the empty box to see your last five searches - pick one to run
  it again, or **Clear recent searches**. They stay in this browser only.

**Want to work on many posts at once - filters, selecting rows, Select
all?** See [Manage posts in bulk](run.md#manage-posts-in-bulk).

## Make it yours in 10 minutes

Give your site your colours, your face and an About page.

1. **Colours:** open **Settings > Style**. Under **Colours**, pick a
   palette - a set of colours that go together.
2. **A starting style:** on the same page, choose one of the **Settings
   presets**. Each one sets the blog layout, what each post shows and
   the fonts in one go, and keeps the colours you picked.
3. **Your logo:** open **Settings > Header and footer**. Under **Icons**,
   select **Pick** beside **Header icon** and choose your logo. It's also
   used for the icon in browser tabs and on phones, unless you pick
   others.
4. **About you:** open **Settings > Profile and links**. Add your photo
   as your **Avatar**, a line or two about you under **Bio**, and your
   **Social links**.
5. **An About page:** select **New post** and write about yourself. Open
   **Settings** (the gear icon), and under **Publishing**, set **Where it
   appears** to **In the menu**. Switch **Published** on and select
   **Save**. Your About page now has a link in your site's menu.

Select **View your site**, at the bottom of the admin menu, to see the
result.

**Want your own colours, not a ready-made palette?** See
[Add custom colours](design.md#add-custom-colours).

**Want a different homepage - a page of your own instead of your latest
posts?** See [Choose the homepage](pages.md#choose-the-homepage).

See also: [Designing the site](design.md) ·
[Make a page for the menu or footer](pages.md#make-a-page-for-the-menu-or-footer)
