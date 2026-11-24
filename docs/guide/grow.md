# Growing an audience

Hear from your readers, keep them coming back, and help new readers find
you.

**Contents:** [Moderate comments](#moderate-comments) ·
[Use another comment system](#use-another-comment-system) ·
[Add a contact form](#add-a-contact-form) ·
[Send a newsletter](#send-a-newsletter) ·
[Move subscribers over](#move-subscribers-over) ·
[Let readers become members](#let-readers-become-members) ·
[Let readers pay](#let-readers-pay) ·
[Share new posts to Bluesky and Mastodon](#share-new-posts-to-bluesky-and-mastodon) ·
[Join the fediverse](#join-the-fediverse) ·
[Show up in search engines](#show-up-in-search-engines) ·
[Read the stats](#read-the-stats) ·
[Translate posts](#translate-posts)

## Moderate comments

New comments wait for you to approve them before anyone else sees them.
You choose which ones show under your posts, and reply to them.

1. Open **Comments** in the admin menu. New comments wait in the
   **Pending** tab, and a number beside **Comments** says how many.
2. On each comment, select **Approve** to show it, **Trash** to remove
   it, or **Reply** to answer it.

Approved comments show under the post. Your replies show straight away,
marked **Author** so readers know they're from you.

**Lots waiting?** Tick several comments and approve or trash them
together. To pick every comment in the tab, tick the box above the list,
then select **Select all**.

**Want an email when a comment arrives?** Switch on **Email me about new
comments**, under **Notifications** in **Settings > Comments and
messages**.

**Getting spam?** In **Settings > Comments and messages**, add words, email addresses
or websites to **Blocked words**, one on each line. Comments and
messages containing any of them go straight to the trash. For more
protection, go to **Settings > Security** and select **Edit** beside
**Spam protection**: it adds a check to the comment and contact forms,
newsletter sign-ups and member sign-in that stops automated spam.

**Want no comments on one post?** In that post's **Post settings >
Publishing**, switch off **Allow comments on this post**.

**What's in the Mentions tab?** Replies and mentions from other sites
and the fediverse - see [Join the fediverse](#join-the-fediverse).

## Use another comment system

Instead of Soloblog's own comments, you can use Giscus, Bluesky, Isso or
Remark42 - comment services that keep the comments somewhere else.

1. Open **Settings > Comments and messages**.
2. Under **Comments use**, choose the system.
3. Fill in what it asks for, and select **Save**.

| System | Where the comments are kept | What you fill in |
|---|---|---|
| Giscus | In GitHub Discussions - readers sign in with GitHub to comment | The repository, category and their IDs, from giscus.app |
| Bluesky | As replies to your Bluesky post that links to the blog post | Your Bluesky handle |
| Isso | On your own Isso server | Its URL |
| Remark42 | On your own Remark42 server | Its URL and site ID |

Readers select **Load comments** under a post to show them.

**Want the comments to show without a click?** Switch on **Load comments
without a click**.

**Switching back to Soloblog's own?** The comments people made in
Soloblog before you switched come back with it.

## Add a contact form

Let visitors send you a message from your site, without seeing your
email address.

1. Open **Settings > Comments and messages**.
2. Under **Contact form**, switch on **Turn on the contact form**.
3. If you like, type an **Intro** - a line shown above the form.

The form is now at `/contact` on your site. Messages arrive in **Contact
messages** in the admin menu, with a number beside it for the ones you
haven't read. A new message shows in bold, with a **New** badge. On each
message, **Reply** opens your email app to answer it, and **Mark as
read** takes it off the count - **Mark as unread** puts it back.

**Deleted a message by mistake?** **Move to trash** shows **Undo** straight
away, or open the **Trash** tab and select **Restore**. Messages stay in
the trash until you delete them there, or select **Empty trash**.

**Want your messages in a spreadsheet?** Tick them, then select
**Export** to download them as a CSV file.

**Getting spam through the form?** Add a check in **Settings >
Security** - see [Moderate comments](#moderate-comments).

**Want the form in your menu?** Choose **Contact** under **Add to menu** in **Posts and pages > Pinned** - see
[Add a link or a built-in page to the menu](pages.md#add-a-link-or-a-built-in-page-to-the-menu).

**Want messages by email too?** Type your address in **Also email
messages to**, under **Notifications**. Replying to the email answers the
visitor.

**Want to hear about new comments and messages in Slack or Discord?**
Paste a webhook URL - a link Slack or Discord makes for posting into
one of your channels - in **Send new comments and messages to**, under
**Notifications**.

**Already have a form on Tally, Typeform or Google Forms?** Under
**Which form**, choose **One you made elsewhere** and paste its share
link.

## Send a newsletter

Email your new posts to readers who sign up for them.

1. Set up email first, in **Settings > Email** - that's how the
   newsletter is sent.
2. Open **Settings > Newsletter**. Under **Readers subscribe with**,
   choose **Soloblog's own**.
3. Switch on **Email new posts to subscribers**.
4. Under **How often**, choose **Each post, as it's published**, or one
   email a week or a month with all the posts from that time.
5. Choose whether to **Send the whole post**, or only its summary and a
   link to read the rest.

A sign-up box now shows under each post, and on its own page at
`/newsletter`. New subscribers confirm their address before they get
anything else. Each email shows the post the way it looks on your site,
with a plain-text copy for email apps that want one, and a link to
unsubscribe.

**Which posts are sent?** Each new post, once. Edits to a post, pages and
unlisted posts aren't sent. A weekly email goes out on Monday morning
and a monthly one on the 1st, in your site's time zone. If there were no
new posts, nothing is sent.

**Want to leave one post out?** In the editor, open **Post settings >
Publishing** and switch off **Email it to subscribers** before it goes
out.

**Want to see an email before your subscribers do?** Open **Newsletter**
in the admin menu, choose a post, then select **Send me a test**. It goes
to the email address in **Settings > Email**.

**Want to send a post yourself?** Open **Newsletter** in the admin menu,
choose a **Post to send**, then select **Send to** your subscribers.

**More subscribers than your email service sends in a day?** Resend's
free plan, for example, sends 100 emails a day. When the limit is
reached, Soloblog stops and sends the rest by itself the next day. Until
then, the post's settings and **Newsletter** show how many it has reached.

**Members on too?** The sign-up box becomes a way to join: readers who
type their email become members and get your new posts, unless they
untick **Email me new posts**.

**Already use Buttondown, Kit, Mailchimp or Substack?** Choose it under
**Readers subscribe with**. The same sign-up box sends readers to that
service, and that service sends the emails.

**Emails landing in spam?** See
[Why email lands in spam](how-it-works.md#why-email-lands-in-spam).

## Move subscribers over

Bring your email list with you from Substack, Buttondown, Mailchimp, Kit
or another service.

1. On the other service, export your subscribers as a CSV file - a
   spreadsheet file most services offer as a download.
2. Open **Newsletter** in the admin menu and select **Import**.
3. Choose the file.

Your subscribers are added, already confirmed, and the line beside
**Import** says how many.

**Using members?** You can import members too, in **Members** - from
another Soloblog site, from Ghost, or from any list with an email column.

**Want a copy of your list?** Tick the box above the list, then select
**Select all** and choose **Export**. Or tick only the subscribers you
want.

## Let readers become members

Members are readers who join your site with their email address. You can
keep some posts for members only.

1. Set up email first, in **Settings > Email** - members sign in with a
   link or code sent by email.
2. Open **Settings > Members** and switch on **Let readers become
   members**.
3. In a post's **Post settings > Publishing**, set **Who can read it** to
   **Members**.
4. Select **Save**.

Readers join at `/join` on your site, or from the post itself, with
their email address. To sign in, they get a link or a code by email, so
they don't need a password. Someone who asks to sign in with an address
that isn't a member's gets an email saying so, with a link to join.

**Signing in on a shared computer?** Members can untick **Keep me signed
in** on the sign-in page. They're then signed out when they close the
browser; otherwise they stay signed in for 180 days.

Anyone who isn't a member sees the start of a members post, then a box
inviting them to join or sign in.

**Want to choose where the preview stops?** In the post, insert
**Members only from here** at that point - from **Insert**, or by typing
`/members`.

**Who are my members?** **Members** in the admin menu lists them all,
with how many you have, how many joined this month, and how many pay.

**Want to welcome new members?** Write a few lines in **Welcome email**,
in **Settings > Members**. Each new member gets it by email.

**Want only members to comment?** Set **Who can comment**, in **Settings >
Members**.

## Let readers pay

Members can pay for a plan to read posts you keep for paid members. You
take payments through Stripe, a payment service, and the money goes to
your Stripe account.

1. In your Stripe dashboard, open **Developers > API keys** and select
   **Create restricted key**. Give it **Write** access for Products,
   Prices, Customers, Checkout Sessions, Customer portal, Subscriptions
   and Webhook Endpoints, and **None** for everything else. Start in
   Stripe's test mode, which makes a key beginning `rk_test_`: no real
   money moves while you try it out.
2. Open **Settings > Members**, select **Edit** beside **Paid members**,
   and paste the key as the **Stripe key**.
3. Choose the **Currency**, a price for **A month**, **A year** or both,
   and a **Free trial** if you want one. Select **Save**.
4. Try it out: join your site as a reader, open a post for paid members,
   and pay with Stripe's test card - `4242 4242 4242 4242`, any date in
   the future and any three numbers for the security code.
5. When you're ready to take real payments, paste a live key (one
   beginning `rk_live_`) in the same place, and save again.

Paid members can now read posts with **Who can read it** set to **Paid
members**. The **Paid members** row in Settings shows **Test
mode** or **Live**, so you always know which one is on.

**How do members cancel or change their card?** On your site, under
**Your account**, with **Manage billing**. A cancelled plan keeps working
until the end of the time they've paid for.

**Want to give someone paid access for free?** Find them in **Members**
and select **Give paid access**.

**Changing a price?** The new price is for new members. People already
paying keep their price.

**A member's card payment failed?** Stripe tries again for a while.
Meanwhile the member shows as **Past due**. If the payment never goes
through, they become a free member.

Payments need your site at its own `https://` URL.

## Share new posts to Bluesky and Mastodon

Have each new post shared on your own Bluesky and Mastodon accounts,
automatically, as it's published.

1. Open **Settings > Sharing**.
2. For Bluesky, select **Edit** beside **Share on Bluesky**. Switch on
   **Post to Bluesky**, and enter your **Bluesky handle** and an **App
   password**. An app password is a separate password you make in
   Bluesky's **Privacy and security** settings - not the one you log in
   with.
3. For Mastodon, select **Edit** beside **Share on Mastodon**. Switch on
   **Post to Mastodon**, and enter your **Server** (like
   `https://mastodon.social`) and an **Access token**. To get the token,
   make an application in your Mastodon account's **Development**
   settings, with only `write:statuses` ticked, and copy its access
   token.
4. Select **Save**.

On Bluesky, each new post shows as a link card with its cover image. On
Mastodon, it shows its title, summary and link.

**Want readers to share your posts too?** Each post has share buttons for
the platforms in your social links, plus email and copy link.

## Join the fediverse

The fediverse is a network of social sites - Mastodon, Pixelfed, Misskey,
Threads and others - where people follow each other across sites. Your
site can join it, so people there can follow it like any other
account.

1. Open **Settings > Sharing**, and go to **Fediverse**.
2. Switch on **Let people follow this blog**.
3. Choose a **Username**, and select **Save**.

Your blog is now an account people can follow, with a handle like
`@blog@yourblog.com`. **Copy handle** copies it, to share. Your new posts
appear in your followers' timelines. Their replies arrive in **Comments**
for you to approve, and your replies go back to them.

**Choose the username carefully** - if you change it later, you lose
your followers.

**Have your own Mastodon account?** Add it to your **Social links**, in
**Settings > Profile and links**. Your blog then verifies that the
account is yours, and Mastodon shows a green check beside the link.

**Want to hear when other blogs link to you?** In **Settings > Sharing**,
open **Webmentions** under **Advanced** and switch on **Accept
webmentions**. Their likes, reposts and replies then show under your
posts. With **Approve replies and mentions first** on, they wait in the
**Mentions** tab of **Comments** for you to approve.

Both need your site at a public `https://` URL.

## Show up in search engines

Search engines like Google and Bing find your site by themselves.
Soloblog gives them everything they need - titles, descriptions, share
previews and a sitemap, a list of all your pages - with nothing for you
to set up.

To see how your site does in search, and what people search for to find
it, add it to Google Search Console or Bing Webmaster Tools:

1. In Search Console or Webmaster Tools, add your site and choose to
   verify it with an HTML tag. Copy the code inside the tag.
2. In Soloblog, open **Settings > URL and SEO**. Under **Advanced**,
   open **Verify with Google and Bing**.
3. Paste Google's code into **Google Search Console**, or Bing's into
   **Bing Webmaster Tools**, and select **Save**.
4. Back in Search Console or Webmaster Tools, select **Verify**.

**Is a post's title too long for search results?** Give it a shorter
**Title for search engines**, in its **Post settings > Search engines**.

**Not ready to be found?** Switch on **Hide this site from search
engines**, in **Settings > URL and SEO**. A single post can be hidden
in its own **Post settings > Search engines**.

**Moved from another blog?** Old URLs like `/2020/05/my-post/`
take people to the same post here, so old links and search results keep
working.

## Read the stats

See how many people read your posts, and how they found them.

1. Open **Stats** in the admin menu.
2. Choose a **Range**: the last 7 days, 30 days, 90 days or 12 months.

Stats shows your views, your top posts, and **Top sources** - the sites
and apps that sent readers to you. Nothing is kept about the readers
themselves, and your own visits aren't counted.

**Worried about broken links in your posts?** Select **Check links** in
**Stats**. It lists any links that no longer work.

**Prefer Plausible, Cloudflare or Google Analytics?** Set one up in
**Settings > Analytics and ads** - select **Edit** beside **Analytics**.

## Translate posts

Offer your posts in other languages. Soloblog has them translated for
you by a translation service you choose, and each translation gets a page
of its own.

1. Make an account with a translation service - DeepL, Google Cloud
   Translation or LibreTranslate - and get its API key, a code that lets
   your site use it. Each service has its own prices.
2. Open **Settings > Language and time**. Select **Edit** beside
   **Translation**.
3. Choose your **Translation service** and paste its **API key**.
4. Under **Offer posts in**, tick the languages to translate into.
5. Select **Save**.

Each new post now gets a translated page for each language, like
`/es/post/your-post`, and the original post shows links to them, like
"Also in: Español · Français".

**What about posts you wrote before?** Select **Translate every post
now**.

**Does it cost anything?** Each translation counts towards what your
translation service charges for, so more languages mean more use. Check
the service's prices.

**Writing in a language other than English?** Choose it in **Posts are
written in**, in **Settings > Language and time**. Everything readers
see around your posts - dates, buttons, "Comments" - follows it.
