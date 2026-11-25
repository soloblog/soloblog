# Running the site

Keep your site safe, backed up and up to date, and keep it tidy as it
grows.

**Contents:** [Manage posts in bulk](#manage-posts-in-bulk) ·
[Organise media](#organise-media) ·
[Back up and restore](#back-up-and-restore) ·
[Move a blog to Soloblog](#move-a-blog-to-soloblog) ·
[Update Soloblog](#update-soloblog) ·
[Check Site health](#check-site-health) ·
[Set up email that arrives](#set-up-email-that-arrives) ·
[Keep the login safe](#keep-the-login-safe) ·
[Connect writing apps and AI assistants](#connect-writing-apps-and-ai-assistants)

## Manage posts in bulk

Publish, tag, export or trash many posts at once, instead of one by one.

1. Open **Posts and pages**.
2. Select the posts you want. On a wide screen, a post's checkbox shows
   when you point at its row. On a phone, press and hold a row to select
   it.
3. Choose what to do, in the line above the list: **Add tag** (type the
   tag first), **Publish**, **Move to drafts**, **Export** or **Move to
   trash**.

Only the actions that make sense for what you selected are shown -
**Publish** shows only when you've selected drafts, for example.

**Want every post, not just the ones on this page?** Select the checkbox above
the list, then select **Select all**. It picks every post that matches
your search and filters.

**Want only posts, or only pages?** Above the list, set **Type** to
**Posts** or **Pages**. **In a series** shows the posts that belong to
one. On a phone, select **Filter** beside the search box first. The tabs
above that show what state they're in: **Published**, **Scheduled**,
**Drafts** or **Trash**.

**Looking for the post you worked on last?** Set **Sort** to **Last
edited**. It puts the posts you saved most recently first. Views, likes
and comments don't count - only saving the post or changing its
settings. On a phone, select **Filter** beside the search box first.

**Looking for Duplicate or Copy link?** Each row shows **Edit** and
**View**. The rest are under the row's **⋯** button: **Edit in Focus**,
**Copy link**, **Duplicate** and **Trash**.

**Moved one to the trash by mistake?** Select **Undo** straight away, or
open the **Trash** tab later and restore it.

**Reading one of your posts on the site?** While you're logged in, three
buttons sit beside its title: **Posts and pages** brings you back to this
list, and **Edit** and **Edit in Focus** open the post.

**Back on the tab you left.** A page with tabs - **Posts and pages**,
**Media**, **Comments**, **Settings** and the others - opens the tab you
were on last, in this browser. A link to a particular tab still opens
that one.

**Want to see more rows at once, or fewer?** Below the list, beside the
page buttons, choose **10**, **20** or **50** next to **Per page**. It
appears once a list has more than 10 rows. Soloblog remembers your choice
for each list, in this browser.

**Other lists work the same way.** In **Media**, **Comments** (and its
**Mentions** tab), **Contact messages**, **Members** and **Newsletter**,
select the rows, then choose what to do with them. Each has its own **Per
page** choice too.

**Want to rename or merge a tag?** Select **Tags**, beside the page's
title (on a phone, under the **⋯** button there). Rename a tag to the
name of another tag to merge the two into one.

**Want to see your posts by date?** Select **Calendar**, in the same
place. It shows a month at a time, with each post on the day it was
published, and scheduled posts on the day they will be. **Pinned**,
beside it, shows your menu pages and the posts pinned to the homepage.

## Organise media

**Media** is your library of images, audio, video and PDFs. Find files,
describe them, and tidy up the ones you no longer need.

1. Open **Media** in the admin menu.
2. Search by a file's name, alt text or caption, or by the title of a
   post that uses it. Or choose a **Kind**: images, audio, video, PDFs, or
   **No alt text** for images that still need describing.
3. Select a file to see which posts use it. From there you can change
   its alt text, caption, credit, dark mode version, phone version or name,
   or rotate or crop it.

Every post that uses the file shows the change straight away, and links
to its old name keep working.

**Want to see only what your posts use?** The **In use** tab lists just
those files.

**Files that no post uses?** The **Unused** tab lists them. Select them and
select **Move to trash**.

**A screenshot or diagram that's too bright when your site is dark?**
Give it a dark version:

1. Upload the dark version to **Media**, like any image. Its file name
   doesn't matter.
2. Select the light one to open its details.
3. Under **Dark mode version**, select **Pick** and choose the dark one,
   then select **Save**.

Use the light one in your posts as usual. Each reader sees the version
that matches their light or dark setting - their device's, or the
palette they choose in the theme switcher - and it changes automatically if
they switch while reading, in galleries and the lightbox too. The dark
one counts as in use, so it never shows under **Unused**.

**A wide screenshot that's too small to read on a phone?** Give it a phone
version, such as a screenshot taken on a phone:

1. Upload the phone version to **Media**, like any image.
2. Select the wide one to open its details.
3. Under **Phone version**, select **Pick** and choose the phone one,
   then select **Save**.

Use the wide one in your posts as usual. On a phone, readers see the
phone version in its place, including in galleries, in the lightbox and
in each step of a Story. It changes automatically if they turn the phone
sideways, and a wide screen shows the usual one. The phone version counts
as in use, so it never shows under **Unused**.

**An image with both a dark and a phone version?** A wide screen shows
the dark one while the site is dark, and the usual one otherwise. A phone
shows the phone version, in light and dark alike - unless the phone
version has a dark one of its own. To give it one:

1. Upload the dark phone image to **Media**.
2. Select the phone image, the one you chose under **Phone version**, to
   open its details.
3. Under **Dark mode version**, select **Pick** and choose the dark phone
   image, then select **Save**.

A phone then shows the phone version in light and its dark one in dark,
and it changes automatically when the theme does. It counts as in use, so it
never shows under **Unused**.

**Images with names like IMG_4032?** Select them and choose **Name from alt
text** to give each one a name from its description.

**Trashed a file that a post still uses?** It asks you first. In the
**Trash** tab, **Restore** brings files back, and **Delete forever**
removes them for good.

## Back up and restore

A backup is a copy of everything on your site, in one file you keep.
If something goes wrong, you can restore it all.

1. Open **Settings > Backup and import**.
2. Under **Download**, select what to include. Everything is selected to
   start with.
3. Select **Download**.

You get a zip file named after your site and the date. Keep it somewhere
private: it includes your settings, and those include the keys to
services you've connected. Inside are the parts you selected:

| In the zip | What it is |
|---|---|
| `posts/` | Each post and page as a markdown file, which any text editor opens. Posts in the trash are in `posts/_trash/`. |
| `uploads/` | Your images and other files. `_trash/` holds the ones in the trash, `_sizes/` the smaller copies made for pages, and `_originals/` an image as it was before you edited it. |
| `blog.db` | Everything else - settings, comments, members, subscribers, stats - in one database file. |

**To restore from a backup:** on the same page, under **Restore**, select
**Upload** and choose the backup file. It shows what's inside, with a
count for each part. Choose what to restore, then select **Restore**.
It asks once more, then replaces what you selected - read what that means
below first.

**What does a restore replace?** Only the parts you select, and nothing
is renamed or kept twice:

- **Posts, pages and images** - each one in the backup replaces the one
  on your site with the same name. A post you've edited since the backup
  goes back to how it was then. A post or image you've added since isn't
  in the backup, so it stays as it is.
- **Settings, comments and messages, members, subscribers and followers,
  stats and reactions** - each part you select is replaced as a whole. A
  comment, a member or a subscriber that arrived after the backup is
  removed. A post's earlier versions go back to the backup's too.
- **Your password and passkeys** always stay as they are, so you can
  still log in.

It doesn't ask about each post or image, and it doesn't show which ones
will change - the checkboxes and the counts are what you choose by.

**Before you restore, keep a copy of today.** Select **Back up now**, or
**Download** a backup, first. If the restore gives back less than you
hoped, restoring that copy puts your site back as it was this minute.

**Want backups made for you?** Connect cloud storage - a bucket at
Amazon S3, Cloudflare R2 or Backblaze B2, which is online storage you
pay for by how much you keep. Backups are then made for you after you
change things, and a new server restores itself from the newest one.
Cloud storage is set up on your host, not in Settings - see
[Keep files in cloud storage](../DEPLOYMENT.md#keep-files-in-cloud-storage).
Locking it with a passphrase? Read
[the warning first](../DEPLOYMENT.md#lock-the-bucket-with-a-passphrase): without the
passphrase, nothing in the bucket can be opened.

Once it's connected, **Settings > Backup and import > Cloud storage**
says **On** and shows the last backup. Your images are copied to the
bucket as you add, change or delete them - not only when a backup is made.

- **Sync images** asks which way, for all your images at once. **This
  site to your bucket** copies each image the bucket doesn't have, or
  has a different copy of - press it once after you first connect
  storage, so the images you already had are there too. **Your bucket
  to this site** does the same the other way. An image that's the same
  on both sides is left alone, and nothing is deleted: an image on only
  one side stays where it is. You
  don't need it day to day - if an image ever fails to reach the bucket,
  this page and **Site health** say so.
- **Back up now** makes a backup straight away, instead of waiting for
  the next change. Press it after you first connect storage, to check
  the bucket works.
- **What the backups include** - select what goes into each backup. Your
  images aren't in backups; the bucket keeps them separately.

**To restore from your bucket:** under **Recent backups**, the newest
three are listed with their date and size, and **Older backups** opens
the rest. Select **Restore** (the ↺ icon; on a phone, under ⋯) beside
the one you want. The **Restore** card above fills in and comes into
view, saying which backup it's from. As with a file you upload, select
what to restore and select **Restore**. **Images** restores the
bucket's latest copy of each image, replacing your site's - the bucket
keeps one copy of each, not one per backup.

**A backup asks for a passphrase?** It's locked with a passphrase other
than the one on your host now - it was made before you changed
`BACKUP_PASSPHRASE`, or on another site. Type the passphrase it was made
with and select **Open**. It's used for this restore only, and your
host's setting stays as it is.

**Want to know a backup would work?** In **Site health**, select
**Verify a backup**. It opens the newest backup in your bucket and checks
it would restore, without restoring anything. Site health suggests it
again after three months.

**Want fewer backups?** In **Settings > Backup and import**, under
**Cloud storage**, set **How often**:

- **A minute after changes** - the safest, and where it starts.
- **Once a day, if anything changed** - at most one backup a day. Publish
  a post at 3 pm when the last backup was at 9 am, and it's backed up at
  9 am the next day, with anything else you change before then. A day
  with no changes makes no backup.
- **Once a week, if anything changed** - the same, a week apart.

When your site restarts - for an update, say - anything waiting is
backed up first. **Backups to keep** sets how many stay in your bucket;
older ones are deleted. That number, not how often, is what you pay to
store. Less often, the backups you keep reach further back, but more of
your latest work can be lost if your server breaks.

**Restoring an old backup?** Your images aren't in backups - the bucket
keeps one copy of each, the latest. An image you've deleted for good
since that backup won't come back, and an image you've rotated or
cropped since comes back the new way. See
[what's kept in the bucket](../DEPLOYMENT.md#whats-in-the-bucket).

**Just want a spreadsheet of your posts, members or subscribers?** In
**Posts and pages**, **Members** or **Newsletter**, select what you want
and choose **Export**. For the whole list, select the checkbox above it, then
**Select all**. **Stats** has its own **Export**.

## Move a blog to Soloblog

Bring your posts over from WordPress, Ghost, Medium, Substack, or a
folder of markdown files.

1. Export your blog from the old one:

   | From | Where to export it |
   |---|---|
   | WordPress | Tools > Export > All content (an `.xml` file) |
   | Ghost | Settings > Labs > Export your content (a `.json` file) |
   | Medium | Settings > Security and apps > Download your information (a `.zip` file) |
   | Substack | Settings > Exports > Create new export (a `.zip` file) |
   | Jekyll, Hugo, Obsidian, Eleventy… | Make a `.zip` of your markdown files, with their images |

2. Open **Settings > Backup and import**, and go to **Import from another
   blog**.
3. Select **Copy images into the media library**. Your images are then kept
   on your new site, so they still show after the old blog is gone.
4. Select **Upload** and choose the file. The import starts straight
   away.

Posts keep their dates, tags and summaries; drafts stay drafts and pages
stay pages. WordPress comments and Substack subscribers come across too.
A big blog can take a few minutes; the page shows how far it's got.

**Want to check each post before it's published?** Select **Import as
drafts** before you upload.

**Coming from Ghost?** Type your old blog's URL in **Old blog's
URL** before you upload, so its images can be copied. Some WordPress
exports need it too.

**Will old links still work?** Yes. Old URLs like
`/2020/05/my-post/` take people to the same post here.

## Update Soloblog

New versions of Soloblog bring fixes and new features. Updating keeps
your posts, images and settings as they are.

1. When a new version is out, the line at the bottom of every admin page
   says so. Select **How to update** there.
2. Download a backup first, in **Settings > Backup and import**, in case
   you need to go back.
3. Update the way you installed Soloblog - with your host's redeploy
   button, or with the commands in
   [Update to a new version](../DEPLOYMENT.md#update-to-a-new-version).

When it's done, the version number at the bottom of the admin is the
new one.

**Want to update with one click?** Set it up once in **Settings >
Integrations** - select **Edit** beside **Updates**. **How to update**
then becomes an **Update now** button. See
[Set up the Update now button](../DEPLOYMENT.md#set-up-the-update-now-button).

**Something wrong after updating?** Go back to the older version, and
restore the backup you made.

**What changed?** **Help > What's new** lists it.

## Check Site health

Site health checks whether anything about your site needs you, before it
becomes a problem.

1. Open **Site health** in the admin menu. A red dot beside it means
   something needs your attention.
2. Open a check to see what it found and why it matters.
3. Select the check's button to go where it's put right.

Each check either **needs attention**, is **recommended**, or has
**passed**. Together they look at updates, backups, security, email,
your domain, storage, search engines and scheduled posts. When something
needs attention, you also get an email - at most once a week for the same
problem.

**Something went wrong - an email that didn't send, a page that broke?**
The **Log** tab lists what went wrong in the last two weeks. **Details**
on each has the technical information for whoever fixes it.

**Asking someone for help?** In the **Info** tab, select **Copy for a bug
report**. It copies what they need to know about your site, without any
password, key or email address.

**How do I know if my site goes down?** A site can't tell you that itself
while it's down. Use a free uptime monitor like UptimeRobot, and point it
at your site's URL with `/healthz` on the end - for example
`https://example.com/healthz`. It emails you if your site stops
answering.

## Set up email that arrives

Your site sends email: password resets, comment confirmations, the
newsletter, and messages to you. Set it up so those emails reach
people's inboxes.

1. Open **Settings > Email**. Type your **Email address** twice, and select
   **Save**.
2. Select **Edit** beside **Sending email**. Under **Send email with**,
   choose **Resend** - an email service that works on every host.
3. Make a free account at resend.com and add your own domain there -
   Resend shows the records to add at your domain's registrar, and says
   when it's verified. Paste the **API key** Resend gives you.
4. Fill in the **From address**: any address at that domain, like
   `hello@yourdomain.com`. Choose one you read, as replies go there -
   Resend only sends. Emails show your site's name as the sender.
5. Select **Send a test email**, and check it arrives in your inbox.

If your host's setup already asked for your email settings - an SMTP
server or a Resend key, an address to send from and your email - those
show as **Set on your host**, and your email already works. Anything you
save here is used in their place. See
[Send email from your host](../DEPLOYMENT.md#send-email-from-your-host).

**Rather send from your Gmail or iCloud account?** Choose **An email
account you have (SMTP)**, then choose **Your email provider**. It tells
you where to make the app password that provider needs - a separate
password for your site, not the one you log in with.

**No domain of your own yet?** Resend needs one. Until you have it, use
**An email account you have (SMTP)** instead.

**The test didn't arrive?** It says why, and what to try. Some hosts
block sending email from an email account; Resend works on all of them.

**Emails reach you, but nobody else?** Your **From address** is probably
at resend.dev, which Resend keeps for trying it out: emails go only to
you. Add your domain in Resend and use an address there. Site health
warns about this too.

**Emails landing in spam?** Your domain needs three settings, called SPF,
DKIM and DMARC records, that prove the emails are really from you. Site
health checks them - see
[Why email lands in spam](how-it-works.md#why-email-lands-in-spam).

## Keep the login safe

Make sure nobody but you can log in to your site.

1. Open **Settings > Security**.
2. Under **Passkeys**, select **Add a passkey**, and confirm with your
   fingerprint, face or device PIN.
3. Under **Recovery key**, make sure you have one saved. If you've lost
   it, select **Make a new key**, and keep it in a password manager.

With a passkey, you log in with your fingerprint, face or PIN instead of
typing a password. A fake login page can't steal a passkey.

**Prefer a code from an app on your phone?** Under **Two-factor authentication**,
select **Turn on**, scan the QR code with an authenticator app, and keep
the ten recovery codes somewhere safe. Each time you log in, you then
type a code from the app too.

**Logging in on a shared computer?** Untick **Keep me signed in** on the
login page. You're then logged out when you close the browser, instead
of staying logged in for 14 days.

**Still logged in somewhere you shouldn't be?**
Under **Sessions**, select **Log out other devices**. Changing your
password does the same.

**Forgot your password?** On the login page, select **Forgot password?**
and use your recovery key to choose a new one.

**Moving your site to a new domain?** A passkey only works on the
domain where you added it, so add a new one on the new domain.

See also: [How your site is kept safe](how-it-works.md#how-your-site-is-kept-safe)

## Connect writing apps and AI assistants

Post from a writing app like iA Writer or Ulysses, or let an AI assistant
draft posts for you.

**A writing app that supports Micropub** (iA Writer, Quill, Micro.blog's
apps):

1. In the app, add an account, choose **Micropub**, and type your site's
   URL.
2. Your site asks whether to let the app in. Choose whether it can
   **Write drafts** or **Publish**, and select **Connect**.

**Ulysses, or iA Writer on a Mac, iPhone or iPad:** these apps publish to
Ghost, another blogging platform, and your site can act as one.

1. Open **Settings > Integrations**, and go to **API keys**. An API key
   is a password for an app. Give the key a **Name**, choose what it can
   do, set **For** to **Apps that publish to Ghost**, and select **Make a
   key**. Copy the key - it's only shown once.
2. In the app, add a **Ghost** account, with your site's URL and the
   key.

**An AI assistant** (Claude, ChatGPT, Cursor and others that support
MCP, a way for assistants to use other apps):

1. Make a key that can **Write drafts**, as above.
2. In the assistant, add your site as an MCP server at your site's
   URL with `/mcp` on the end - for example
   `https://example.com/mcp` - with the key as a header:
   `Authorization: Bearer sb_...`.

Then ask it things like "Draft a post from these notes" or "Which of my
images have no alt text?".

**Will it publish without me?** Not unless you let it. To start with, an
AI assistant's posts arrive as drafts for you to check and publish.
**Who may publish with a Publish key**, on the same page, decides this.

**Want to disconnect an app or assistant?** Select **Revoke** on its key.
It stops working at once.

See also: [The API](../API.md) · [Webhooks](../API.md#webhooks)
