# Troubleshooting

Something not working as you expect? Find it below. If it isn't here,
the end of the page says where to ask.

## I lost the setup token

The setup token is the one-time code you need to create your account.
The setup page tells you where your host shows it. Or restart your site
from your host's dashboard: a new token appears in the server's log, on
the lines marked `[setup]`, until your account exists.

## Setup says my posts would be lost on the next update

Your host isn't keeping your site's files between updates. Add lasting
storage, mounted at `/data`: a volume on Railway, Fly or Koyeb, or a disk
on Render's paid plans. Then redeploy. The warning goes away once the
storage is there. Your host's section of
[Hosting and deploying](../DEPLOYMENT.md) has the steps.

## I forgot my password

On the login page, select **Forgot password?** and enter your **recovery
key** to choose a new password.

**Lost the recovery key too?** If email is set up and your address is
saved in **Settings > Email**, the same page emails you a link to reset
it instead.

**No email either?** On your host, add a setting called `RESET_PASSWORD`
with the value `1`, and restart your site. A one-time link to reset your
password appears in the server's log. Remove the setting afterwards.

## I'm locked out by two-factor

When you turned on two-factor login, you were given ten recovery codes.
Type one of them where it asks for the 6-digit code. Each code works
once.

## "Unsaved changes" won't go away

Something you typed on that page hasn't been saved. Select **Save** to
keep it, or **Discard** to throw it away.

## A post I scheduled didn't go live

Open the post's **Post settings > Publishing**. Check that **Published**
is on, and that **Publish at** is the time you meant, in your site's
time zone. The time zone is in **Settings > Language and time**. Choosing
a time switches **Published** on for you.

## An edited image still looks the same

Browsers keep a copy of images for up to an hour, to load pages faster.
Reload the page while holding **Shift** (or press **Ctrl+F5**) to see
the change straight away. Your readers will see it within the hour.

## Links in feeds or the sitemap say "localhost"

Your site doesn't know its public address yet. Type it in **Settings >
Address and search**, under **Site address**.

## Emails aren't arriving

Open **Settings > Email** and select **Send a test email** - if it can't
send, it says why and what to try. If test emails arrive but land in
spam, send from an address at your own domain, and add your email
provider's SPF and DKIM records to your domain. See
[Why email lands in spam](how-it-works.md#why-email-lands-in-spam).

## Fediverse follows don't arrive

Two things need to be right. The site address, in **Settings > Search
engines**, must be its public `https://` address. And if your site runs
behind a reverse proxy (like Caddy or nginx, which add HTTPS), it must
pass the original `Host` header through - see
[Put HTTPS in front](../DEPLOYMENT.md#put-https-in-front).

## Images disappeared after a redeploy

Your host isn't keeping your site's files between deploys. Add lasting
storage mounted at `/data`, or connect cloud storage, so a fresh server
restores itself from your newest backup. See
[Keep files in cloud storage](../DEPLOYMENT.md#keep-files-in-cloud-storage).

## Your site shows "Bring your site back"

A new server, or a restart on a host without a disk, brings your site
back from the newest backup in your storage bucket. When it can't, it
shows this page instead of starting as an empty site, and makes no
backups until you choose what to do - so your real backups are never
replaced by empty ones.

1. Find your setup token: the `SETUP_TOKEN` setting on your host, or
   the server's log on the lines marked `[setup]`.
2. Type it in **Setup token**.
3. If the page asks for a **Passphrase**, type the passphrase the
   backup was made with - the `BACKUP_PASSPHRASE` your host had before
   you changed or removed it.
4. Select **Restore**.

Your whole site comes back, and you log in with its password as before.
A new backup is made straight away with the passphrase your host has
now, so the next restart opens it by itself.

**The page says the bucket didn't answer?** Check the `S3_` settings on
your host - the endpoint, the bucket name and both keys - then select
**Try again**.

**The newest backup couldn't be opened?** Choose an earlier one under
**Backup**.

**Lost the passphrase?** Nothing can open those backups. Select **Start
a new site instead** to set up a new site. The old backups stay in your
bucket, but new backups replace the oldest ones, as they always do -
copy any you want to keep from your storage company's dashboard first.

**Expected your site, but it started empty with no message?** Check
`S3_PREFIX` on your host: a different folder name means Soloblog looks
in an empty folder, and the backups in the old one aren't touched.

## A translation isn't showing

New translations can take a minute. If one still isn't there, open
**Settings > Language and time** and select **Edit** beside
**Translation**. It shows any problem, like a wrong key or a translation
service account that's used up its credit.

## An embed shows only a link

Only links from the services listed in
[Embed from other sites](writing.md#embed-from-other-sites) become
players or cards, and only when the link is on a line by itself.

## My page isn't at the short address I expected

Pages in your menu or footer usually get a short address, like `/about`.
If the one you wanted is already used by Soloblog itself (like `/search`
or `/tags`), your page stays at `/post/…` instead -
**Post settings > Details** says so. Change its **URL** there to
something else to give it a short address.

## Still stuck?

At the bottom of every admin page:
- **Ideas and questions** opens the project's discussion forum, where
  you can ask.
- **Report a problem** opens a form to report a bug.

Before you report one, open **Site health**, go to the **Info** tab, and
select **Copy for a bug report**. Paste what it copies into your report.
