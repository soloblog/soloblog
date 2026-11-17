# Reference

Every setting, every option of a post, and everything you can write in
a post, with a line or two on each - a page to look things up in. To get
something done step by step, the other pages of the guide say how; this
page is the detail behind them. Every kind of section and every template has
its own entry in [Sections and templates](sections-templates.md).

## How Settings work

**Settings**, in the admin menu, opens a list of pages, grouped under
small headings. These are the headings and the pages under each:

- **Site:** Name and homepage, Address and search, Language and time
- **Design:** Style, Blog layout, Posts, Header and footer, Banner
- **You:** Profile and links
- **Readers:** Comments and messages, Newsletter, Members
- **Growth:** Analytics and ads, Sharing
- **Writing:** Editor
- **Advanced:** Email, Integrations, Security, Backup and import

Switches and choices save the moment you change them. Once saved,
**Undo** shows beside "Saved" in case you change your mind. When you
type something, a **Save** button shows at the bottom of the screen,
with **Discard** beside it to throw away what you've typed.

Things you set up once - sending email, analytics, ads, paid members,
translation - are a single row showing their current state, such as
"Off" or "Test mode". **Edit** opens them, and their fields save
together, with **Save**. Settings you'll
rarely change are under **Advanced**, at the bottom of their page, each
also a row showing its current state, with **Edit** to open it
(**Show** for settings made on your host, which you can only look at).

A switch or choice you've set differently from its default has a thin
coloured line down its left edge, with **Reset** - the ↺ arrow - beside
it. The default is what your starting style sets (see
[Settings presets](#settings-presets)), or Soloblog's own for anything a
style doesn't change, so a style you've just picked shows no lines. Point
to **Reset** to see the default; selecting it puts the setting back and
saves it. In a choice's list, the default is marked **Default**.

On the Design pages - Style, Blog layout, Posts, Header and footer, and
Banner - **Preview mode** fills the screen with your site, the page's
settings down the left, and shows each change as you make it, before
it's saved. Choose to look at the homepage, a post or a page, on a
**Computer** or a **Phone**. **Open** shows it in a browser tab of its
own, and **Close** (or **Esc**) goes back. On a smaller screen, Preview
mode opens your site in a tab.

**Help**, at the top of each settings page, opens the part of this
page about it.

The choice each setting starts with on a new Soloblog site is tagged
**Default**, and each switch says whether it starts **On by default** or
**Off by default**.

## Name and homepage

### Identity

- **Site title** - Your site's name. It shows in your header, in browser tabs, in search results and when your site is shared.
- **Tagline** - A short line under your site's name on the homepage.

### Homepage

- **Your homepage shows** - What people see first when they visit: your latest posts; your wiki's front page; or one of your pages - **Pick** one that's in your menu or footer, or an unlisted post to keep it out of the menu. With a page or the wiki as your homepage, your posts move to `/blog`, and a Blog link is added to the menu.
- **It also shows** - When a page is your homepage: tick what else it shows - the title (with the date and cover), reactions, share buttons, related posts, About the author, the newsletter sign-up, comments.

## Address and search

### Site address

- **Address** - Your site's web address, like `https://example.com`. It starts as the address you first set up Soloblog at. Change it when you move to a new domain. If the field can't be changed, your host sets the address (as `BASE_URL`): change it there instead.

### Search engines

- **Description** - Shown under your site's name in search results. Empty: your tagline.
- **Hide this site from search engines** (on/off) - For a private or unfinished site.

Search engines find your site by themselves. They get everything they need with nothing for you to set up: a sitemap (a list of all your pages, at `/sitemap.xml`), titles and descriptions, share previews, and recipes, FAQs and reviews in the formats search engines show specially. Drafts, unlisted and password-protected posts are never offered to them.

### Verify with Google and Bing

Under **Advanced**. Only needed if you use Google Search Console or Bing Webmaster Tools to see how your site does in search, and they ask you to prove the site is yours. See [Show up in search engines](grow.md#show-up-in-search-engines).

- **Google Search Console** - The code from Search Console's HTML tag - only the code, not the whole tag.
- **Bing Webmaster Tools** - The msvalidate.01 code.

### Redirects

Under **Advanced**.

- **Send old addresses somewhere new** - So links to pages that have moved keep working. One on each line: the old address, a space, and the new one - a page here or another site. End the old one with `*` for everything under it (`/2019/* /archive`). Renamed and imported posts need nothing here: their old addresses already work.

## Language and time

### Time zone

- **Time zone** - Used for your posts' dates, and for when scheduled posts are published. Type a city or region to find yours.

### Languages

- **Posts are written in** - The language you write in. Soloblog's own words on your site follow it - dates, buttons, "Comments". It doesn't translate your posts.
- **Spelling** - For a site in English: how dates and Soloblog's own words are spelled. American (color, Sep 15, 2026), or British or Australian (colour, 15 Sep 2026). Your writing is never changed.

### Translation

Your posts, translated for you into other languages by a service you choose. A row showing whether it's on; **Edit** opens it. Steps: [Translate posts](grow.md#translate-posts).

- **Translation service** - Who does the translating: DeepL, Google Cloud Translation or LibreTranslate. You need an account with them; each has its own prices.
- **API key** - The key the service gives you, so your site can use it: DeepL's from deepl.com/pro-api, Google's from Google Cloud, under Cloud Translation. LibreTranslate: only if your server asks for one.
- **LibreTranslate server** - Your own LibreTranslate server's address, if you run one. Empty: libretranslate.com, which needs a key.
- **Offer posts in** - The languages to translate into. Each post gets a page in each one, like `/es/post/your-post`. Every language is another translation of every post, so check the service's prices.
- **Translate every post now** - Translates the posts you wrote before turning it on. New posts are translated by themselves.

## Style

### Settings presets

A preset changes your whole site's look in one go. There are **Custom**, **Default** and twelve starting styles - Personal blog, Writer's notebook, Magazine, Photo journal, Portfolio, Journal, Freelancer, Small business, Docs, Wiki, Launch and Link in bio - each with **Preview** and **Use this**. The ones built around a page (Portfolio, Freelancer, Small business, Docs, Wiki, Launch, Link in bio) make that page for you, or use **One of your pages**. Each preset says how many settings it would change on your site as it is now - open it for the list, like "Posts are shown as: Cards → Minimal" - or, for the one in use, every setting it sets. **Undo it** puts back what the last one changed, and the line beside it lists what that was.

**Custom**, the first of them, keeps one look of your own: **Save current look** saves every look setting as it is now - colours, fonts, layout, header, footer - to come back to after trying others, with **Use this** like the rest. Saving again replaces it, and asks first.

**Default**, beside it, puts every look setting back to how Soloblog comes, the colours too. It asks before it does, and **Undo it** brings yours back. Your words, pictures and pages stay - the banner's text and picture, your icons and footer note, which page is your homepage.

A preset can change: how posts are shown in the blog roll (and what each one shows, cards in a row, grouping, the placeholder), the reading column, the fonts and text size, the header's position, layout and width, the side panels (where each goes, where it shows and their order), the table of contents, folding sections, the cover image's width, the gallery style, how portfolios are arranged, animations and what each post shows. A preset that makes a page of its own (a landing page, docs, a wiki) offers it as your homepage, or one of your pages; the others leave your homepage as it is. Never your colours, your writing or anything else.

### Colours

- **Matching pairs** - A light palette and a dark one that go together, set in one go.
- **Light palette** and **Dark palette** - The set of colours your site uses in light mode, and in dark mode. There are 21 light palettes and 14 dark ones, with your own first. Select one to see it.
- **Visitors see** - The palette that matches each visitor's device (the dark one when their device is set to dark mode); always the light one; or always the dark one.
- **Let readers pick other colours** (on/off) - Adds a Colours menu to your header, where readers choose colours for themselves only. **Default**, in that menu, takes them back to yours.
- **Frosted glass** (on/off) - The header, menus and popups let the page show through, blurred.

The colours save together, with **Save**.

#### Custom colours

Palettes you make yourself, on daisyUI's website, and paste in - see [Add custom colours](design.md#add-custom-colours). Besides colours, each sets the corner rounding, border width, sizes, shadow depth and grain texture it was made with.

- **Add colours** - Paste the CSS from [daisyUI's theme generator](https://daisyui.com/theme-generator/), and give it a name. A preview shows it as you paste. It's added first to **Light palette** or **Dark palette**, and to readers' Colours menu. Share images and comments use it too.
- **Change** - Paste a new version, or rename it.
- **Delete** - Asks first. If your site was using it, it goes back to the default palette.

Up to 10. Like the palettes that come with Soloblog, their text colours are adjusted just enough to be easy to read.

### Fonts and text size

- **Text font** and **Heading font** - The font for your writing, and the one for titles and headings: Default, or one of fifteen - serif, sans-serif and others. Each name is shown in its own font; type to find one. They're fonts already on readers' devices, so your pages stay fast. The admin keeps its own fonts.
- **Text size** - Small, Medium or Large, for your whole site and the admin. Medium is the size the reader's browser is set to.

### Motion

Under **Advanced**. Readers who've set their device to reduce motion never see animations, whatever you choose here.

- **Animations** (on/off) - Pages fade in, menus and panels slide, sections fold smoothly. Off, nothing moves - not the editor's sheets or drawers either.
- **Sections appear** - How each section comes into view as it scrolls in: Fade, Rise, Zoom, Slide left, Slide right, Slide both ways, Focus, Tilt, or None. Fade to start with. Only while Animations are on. Each post or page can choose its own, and a section's own `Appear:` line wins.
- **Smooth scrolling** (on/off) - Selecting a link to a heading glides down to it, instead of jumping.

## Blog layout

### Blog layout

- **Posts are shown as** - How your homepage and tag pages list your posts: List (text first); Cards (a grid with pictures); Magazine (the newest large, the rest in cards); Minimal (just dates and titles); Timeline (along a line).
- **Timeline line** - With Timeline: on the left, centred, or on the right.
- **Each post in the list shows** - Cover, date, reading time, summary and tags. A post can keep its own cover out of lists (**Post settings > Details**).
- **Group posts by** - With Minimal: none, year or month.
- **Cover position** - With List: the picture right or left of the text.
- **Placeholder for posts without a cover** - With Cards and Magazine: posts without a cover image get a tile in your colours, so the cards line up.
- **Cards in a row** - With Cards: three, two, or one. With one, each post is shown large, with its words over its picture, like Magazine shows the newest post.
- **Posts per page** - 6, 9, 12, 18, 24 or 48.

### Side panels

- **Tag cloud** - Under the posts, on the left, on the right, or off. Your most used tags.
- **Archive links** - The same choices. The last 12 months.
- **About the author** - The same choices. Your photo, name, bio and links (**Settings > Profile and links**). Where it shows, it takes the place of About the author under each post.
- **Shows on** (for each) - The blog roll, posts, pages. Each post or page can leave them out. Clearing every tick turns the panel off.
- **Blend side panels into the page** (on/off) - No box around the panels beside the page.

## Posts

### Each post shows

- **Around the text** - Tick what shows on each post, around your writing: breadcrumbs, the reading progress bar, author and date, tags, Listen (reads the post aloud), likes, share buttons, Print or save as PDF, support links, series links, related posts, About the author, the newsletter sign-up and the side panels. Each post or page can choose its own (**Post settings > Page > Show**). Comments have their own switch, under Comments.

### Breadcrumbs

- **Above each post** - Breadcrumbs are a line of links above a post showing where it sits on your site, like Home › Travel › This post. Choose: Home › series or first tag › post; Home › first tag › post; Home › post; or off.

### Reading

- **Use relative dates** (on/off) - "2 days ago" instead of "30 Aug 2026".
- **Show when a post was updated** (on/off) - "Updated …" beside the date, once a post is edited on a later day.
- **Show a "back to top" button** (on/off)
- **Open links to other sites in a new tab** (on/off) - Links in posts and pages to other sites. Links to your own site stay in the same tab.
- **Footnotes beside the text** (on/off) - In the margin on a wide screen, at the end on a phone.
- **Reader reactions** - A heart Like button, a row of emoji, or neither.
- **Emoji offered** - Which emoji the row has.

### Contents and sections

- **Table of contents** - At the top, on the left, on the right, or off. For posts with three or more headings. Each post can choose its own.
- **Shows on** - Posts, pages, or both. Each post or page can still choose its own contents in its settings.
- **Fold contents** - Follow the reader, foldable, or always open.
- **Number the contents** (on/off) - 1, 2, 2.1 - handy for guides.
- **A copy-link button beside each heading** (on/off) - To share a section.
- **Fold headings** - Off, foldable and open, or foldable and folded. Readers fold the writing under a heading by selecting it. Only plain writing folds: a section (a `##` with a `Section:` line) never does, whatever its width.

### Images

- **Cover image** - Full screen (the whole window, with the title over the bottom of it and an arrow down to the words), Edge to edge, Wide (out to the side panels) or as wide as the text. Full screen to start with. Each post can choose its own. A cover's caption, from **Media**, shows under it - or, on a full-screen cover, in its bottom corner.
- **Default gallery style** - Grid, Masonry, Justified, Slider or Filmstrip. Each gallery can choose its own.
- **Portfolio pages** - How a Portfolio section shows your work: Grid (even tiles, a title under each), Masonry (each picture at its own shape, nothing cut off), Rows (edge to edge, each row the same height), Full screen (one piece at a time, as you scroll) or Sideways (a row of tall pictures you swipe along). Each portfolio can choose its own with a `Show as:` line.
- **Open any image bigger with a click** (on/off) - Readers select an image in a post to see it full size. Images in a gallery always open this way.

### Milestones sections

Under **Advanced**. For Milestones sections, which show events along a line.

- **Line in Milestones sections** - Where the line runs: on the left, centred, or on the right.

## Header and footer

### Width and spacing

- **Reading column** - How wide the column of text is: Standard, or Narrow, which is easier on the eyes for long reading.
- **Space between sections** - Small, Medium or Large: the room between a page's sections, the sections in a post, a project's pictures, and before comments and related posts. Medium to start with. Each post or page can choose its own, and a section's own `Space:` line wins.
- **Section headings** - On the left or Centred: where every section's heading, and the words under it, sit. On the left to start with. A section's own `Heading:` line wins.

### Header

- **Header position** - The header is the bar at the top of every page, with your site's name and menu. It can scroll away with the page, stay at the top, or float over the page as a bar with a gap around it.
- **Header layout** - The title on the left with the menu beside it; centred with the menu behind a button; or centred with the menu on its own row. On a phone, the menu is always behind a button.
- **Header width** - As wide as the text, or out to the side panels, with room for more links. Links that don't fit go under **More**.

### Footer

- **Show the footer** (on/off)
- **Footer position** - The footer is the area at the bottom of every page. It can scroll with the page, stay at the bottom of the screen, or float. On a phone, it's at the end of the page.
- **Layout** - One column, centred or left-aligned; split left and right; or columns, where each footer page with pages under it is a column with its title on top, as product sites have.
- **What to show** - Your bio, social links, pages, the copyright line and the small print, each on or off. Drag to reorder; with the split layout, what's above **Right side** goes on the left.
- **Footer note** - The copyright line. Empty: "© your site's name".

### Icons

Add one and it's used for the others too, until you pick them separately.

- **Header icon** - Beside your site's name in the header - your logo, say.
- **Favicon** - The small icon in browser tabs and bookmarks.

### On a phone's home screen

Under **Advanced**. Phones let people add a website to their home screen, where it shows an icon and a name, like an app.

- **App icon** - Square, 512 × 512 or larger. Empty: your favicon.
- **App name** - Under the icon. Empty: your site's title.

## Banner

### Content

- **Show a banner above your posts** (on/off) - A big welcome at the top of your homepage.
- **Heading** and **Subheading**

### Button

- **Button text** and **Button link** - Leave both empty for no button. **Pick** lists your posts and the built-in pages.

### Background

- **Background image** - Behind the banner's words.
- **Width** - As wide as the posts, Wide (out to the side panels) or Edge to edge.

## Profile and links

### Bio

- **Author name** - The byline on your posts.
- **Avatar** - Your photo, beside your name under posts and in the footer.
- **Bio** - A line or two about you, under each post.

### Social links

- **Social links** - Links to your accounts on X, Facebook, Mastodon, Bluesky, Threads, LinkedIn, GitHub, Instagram, YouTube and your website. Drag to reorder - share buttons follow the same order.
- **More links** - Any other links, one on each line: `Name|https://address`. Add `|icon` to choose one: link, globe, mail, heart, star, bookmark.

### Support

Links where readers can pay to support your writing, shown as buttons.

- **Add a support link** - Ko-fi, Buy Me a Coffee, GitHub Sponsors, Patreon, Liberapay or PayPal: choose one and add your page on it. The ones you've added are listed above it.
- **Message** - A line above the buttons.
- **Show under each post** (on/off) - Each post or page can choose its own.

### Links page

- **Turn on the links page** (on/off) - Your photo, bio and a stack of links, at `/links` - the link to put in a social profile.
- **Links** - One on each line: `Name|https://address`.
- **Also show** - Your social links, support links and newest posts.

## Comments and messages

### Comments

- **Allow comments** (on/off) - Readers can comment under your posts. Each post can turn them off for itself, too.
- The settings below appear once **Allow comments** is on.
- **Comments use** - Which comment system: Soloblog's own (you approve each comment in **Comments**); Giscus (comments kept in GitHub Discussions); Bluesky (the replies to your Bluesky post about the blog post); or Isso or Remark42 (on your own server). Each one asks for its details, from its own dashboard; they save together, with **Save**. See [Use another comment system](grow.md#use-another-comment-system).
- **Let commenters get replies by email** (on/off) - Adds "Email me when someone replies" to the comment form. Needs email set up.
- **Load comments without a click** (on/off) - With another comment system. Off, readers select **Load comments** to show them, so nothing loads from that service until they do.

### Contact form

- **Turn on the contact form** (on/off) - A page at `/contact` where visitors can send you a message.
- The settings below appear once **Turn on the contact form** is on.
- **Intro** - A line above the form.
- **Which form** - Soloblog's own (messages arrive in Contact messages), or one you made elsewhere - Tally, Typeform, Google Forms, Jotform, Microsoft Forms, Airtable.
- **Also send to a form service** and **Form ID** - To keep a copy of each message with a form service as well: Formspree, Getform, Basin or Formcarry (the ID in the form's address), or FormSubmit (your email address).
- **Form link** - For a form made elsewhere: its share link.

### Blocked words

Shown while comments or the contact form is on.

- **Blocked words** - One word, phrase, email address or website address on each line. Comments and messages with any of them go straight to the trash.

### Notifications

Shown while comments or the contact form is on.

- **Email me about new comments** (on/off) - When one is waiting for your approval. With Soloblog's own comments. Needs email set up.
- **Also email messages to** - Your address, to get each message by email as well. Replying to the email answers the visitor. With Soloblog's own contact form. Needs email set up.
- **Send new comments and messages to** - To get a message in Slack or Discord when a comment or contact message arrives. Paste a webhook address - a link Slack or Discord makes for posting into one of your channels.

Spam protection is in [Security](#spam-protection).

## Newsletter

- **Readers subscribe with** - Nothing; Soloblog's own (your new posts, emailed to subscribers - needs email set up); or Buttondown, Kit, Mailchimp or Substack, where your account on that service sends the emails.
- **Email new posts to subscribers** (on/off) - Off, you send the ones you choose, from Newsletter.
- **How often** - Each post, as it's published; or once a week (Monday morning) or once a month (the 1st), with that time's posts in one email. A week or month with no new posts sends nothing.
- **Send the whole post** (on/off) - Off, the email has the post's summary and a link to read the rest.
- **Username** (Buttondown), **Form ID** (Kit), **Form action URL** (Mailchimp) or **Publication** (Substack) - With another service: where to send people who sign up. Each service shows it in its own settings.
- **Heading** and **Intro** - What the sign-up box says.
- **Show the sign-up box under each post** (on/off)
- **Show it on the homepage too** (on/off) - Readers can always sign up at `/newsletter`.

## Members

- **Let readers become members** (on/off) - Readers join with their email address, and sign in with a link or code sent by email - no passwords. Each post can then be for everyone, members or paid members.
- The settings below appear once **Let readers become members** is on.
- **Show Sign in in the header** (on/off) - A **Sign in** link in your header, for members. Off, they sign in from a members post or at `/join`.
- **Who can comment** - Everyone, members or paid members.
- **On the join page** - A line on the page where readers join.
- **Welcome email** - Sent when someone joins. Empty: none.
- **Paid members** - A row showing whether payments are set up, in test mode or live; **Edit** opens it: your Stripe key, the currency, a monthly and a yearly price (leave one empty if you don't offer it), a free trial, and Stripe Tax. See [Paid members](grow.md#let-readers-pay).

## Analytics and ads

### Analytics

Analytics count visits to your site, on another service, beside your own **Stats**. A row showing its current state; **Edit** opens it.

- **Provider** - None; Cloudflare Web Analytics (free, no cookies); Plausible (privacy-friendly, paid); Google Analytics.
- **Site ID** - Plausible: your site's domain. Google: the ID starting with G-. Cloudflare: the token in its snippet. Your own visits aren't counted.

### Cookie consent

- **Ask visitors before anything that tracks them** (on/off) - A small Accept / Decline banner, shown only when something on your site tracks visitors - the line under the switch says what. See [Cookies and consent](how-it-works.md#cookies-and-consent).
- **Message** - What the banner says.
- **Privacy page** - Your privacy page, linked from the banner.

### Ads

Show Google AdSense ads on your site. A row showing its current state; **Edit** opens it.

- **AdSense publisher ID** - From your AdSense account, under Account information. AdSense chooses where the ads go. You won't see them while you're logged in.
- **After each post** and **Below the blog roll** - Places of your own for an ad, as well as the ones AdSense chooses: paste the ID of a display ad unit you made in AdSense.
- **Show ads on pages too** (on/off) - About, Privacy and the other pages in your menu and footer.

For visitors in the EU, UK and Switzerland, Google needs its own consent message before it shows them ads - turn it on in your AdSense account, under Privacy & messaging.

## Sharing

### Sharing

- **Share image** - The picture shown when someone shares a link to your site, for pages without a cover image of their own. About 1200 × 630 pixels works best. Without one, a post without a cover shares a card with its title.

### Share on Bluesky

A row showing its current state; **Edit** opens it. Each new post is shared from your Bluesky account as it's published, with a link back.

- **Post to Bluesky** (on/off), with your **Bluesky handle** and an **App password** - a separate password you make in Bluesky's Privacy and security settings, not the one you log in with.

### Share on Mastodon

A row showing its current state; **Edit** opens it. Each new post is shared from your Mastodon account as it's published, with a link back.

- **Post to Mastodon** (on/off), with your **Server** (like `https://mastodon.social`) and an **Access token** - make an application in your Mastodon account's Development settings, with only `write:statuses` ticked, and copy its token.

### Fediverse

The fediverse is a network of social sites - Mastodon, Threads and others - where people follow each other across sites. Your blog can be an account there. See [Join the fediverse](grow.md#join-the-fediverse).

- **Let people follow this blog** (on/off) - Needs your site at a public `https://` address.
- The settings below appear once **Let people follow this blog** is on.
- **Username** - Letters, numbers and _. Changing it later loses your followers.

### Webmentions

Under **Advanced**. Webmentions are how blogs tell each other they've linked to, liked or replied to a post.

- **Accept webmentions** (on/off) - When other blogs link to, like or reply to your posts, it shows under them.
- **Approve replies and mentions first** (on/off) - They wait in the **Mentions** tab of **Comments** for you to approve. Likes and reposts show straight away.
- **Tell sites when I link to them** (on/off) - When you link to a blog that accepts webmentions, it's told about your post.

## Editor

### Writing

- **Keep unsaved writing** (on/off) - If the page closes before you save, you can get your writing back.
- **Post settings beside the editor** (on/off) - On a wide screen, Post settings stays open beside your writing. Off, the Settings button opens it over the text.
- **Slash menu** (on/off) - Type / at the start of a line to insert headings, images and more.
- **Check spelling** (on/off) - Your browser underlines misspelled words.
- **Writing width** - Comfortable (a column that's easy to read back), or Wide (the text fills the box).
- **Writing progress** (on/off) - Words written today, and a word goal for each post.
- **Default word goal** - A length every new post and page aims for. Each can have its own in Post settings, or none. Empty: none.
- **Markdown marks** - The symbols that format your writing, like `#` and `**`: Dimmed, so your words stand out; or Full, the same colour as your words.

### Focus

Focus fills the screen with your writing and nothing else. See [Write in Focus](writing.md#write-in-focus).

- **Typewriter scrolling** (on/off) - The line you're writing stays in the middle of the screen.
- **While you type** - Hide everything but your words, or keep the toolbar. Moving the mouse to the top, or scrolling up on a phone, brings everything back.
- **Fade** - What fades so you can concentrate: all but the paragraph you're in, all but the sentence, or nothing.

### Markdown

Footnotes, checklists, callouts, galleries and embedded videos always work. These two are extra:

- **Diagrams** (on/off) - Flowcharts and timelines, written as text in ```` ```mermaid ```` blocks.
- **Math** (on/off) - Formulas written between `$` signs.

### Toolbar buttons

- **Toolbar** - The bar of buttons above your writing: Icons (a row of the buttons you choose), Menus (like a word processor), or None (use the slash menu and keyboard shortcuts instead).
- **On a phone** - The bar above a phone's keyboard: your buttons; sections, each opening a grid of buttons; or none.
- **Buttons** - Tick which show, by group. The ones you leave off are still in the slash menu.

### Toolbar order

The order of the buttons on the toolbar. Drag them into order, or use the arrows. **Reset to default** brings back the standard set.

### Templates

- **New posts start from** - The template every new post opens from: **Blank** (an empty post), one of yours, or one that comes with Soloblog. Type to find one. See [Choose what new posts start from](writing.md#choose-what-new-posts-start-from).
- **Custom templates** - Pages you've saved as templates, each with **Remove**, and a button to start a new post from it. See [Save a page as a template](writing.md#save-a-page-as-a-template).

## Email

Everything about email is on this page: where it comes to you, and how
your site sends it. Site health checks both.

### Admin email

- **Email address** and **Type it again** - Where your site sends you password resets, sign-in alerts and news about comments. Never shown on your site. Saved with the page's **Save**, once both match.
- **Password** - Your admin password, needed only when you change the address. The old address gets an email saying it was changed.
- **Email me when a new device signs in** (on/off, on to start with) - An email the first time someone logs in to your admin from a new browser. If it wasn't you, change your password and log out other devices. The same switch sends you an email when someone is trying many passwords on your site.

### Sending email

A row showing its current state, such as "Resend" or "SMTP · smtp.gmail.com"; **Edit** opens it.

- **Send email with** - How your site sends email - sign-ins, comment confirmations, the newsletter and messages to you: Resend (an email service, recommended because it works on every host); an email account you have (SMTP, the way email apps send); or nothing. With nothing, comments skip the confirmation email.
- **Resend:** make a free account at resend.com, add your own domain there, then paste the **API key** it gives you and a **From address** at the domain you verified, like `hello@yourdomain.com`. Not an address at resend.dev: those reach only you. Emails show your site's name as the sender.
- **Your email account (SMTP):** pick **Your email provider** - Gmail, iCloud Mail, Yahoo Mail, Fastmail or Proton Mail - and give your **Email address** and **Password**; it says where to make the app password that provider needs. Outlook and Microsoft 365 no longer let a site send with a password: use Resend. For any other provider, pick **Another provider** and fill in its **Server**, **Port** and **Username**.
- **Send a test email** - Saves what's on screen, then sends an email to your own address, so you can check it arrives.
  If it can't go, it says why and what to try - Site health says the same
  when a real email doesn't go out. The usual ones: Gmail, iCloud and
  Yahoo need an **app password** - a separate password for your site, not
  the one you log in with; and some hosts (Render's free plan, Railway's
  Hobby plan) block sending from an email account - Resend works on every
  host.

These save together, with **Save**.

## Integrations

### API keys

An API key is a password for an app, a script or an AI assistant, letting it work on your site. See [Apps, scripts and AI assistants](run.md#connect-writing-apps-and-ai-assistants) and [The API](../API.md).

- **Who may publish with a Publish key** - **No one** (everything arrives as a draft), **Apps, not AI assistants** (to start with) or **Apps and AI assistants**. It covers every way in: the API, writing apps, Ghost apps and AI assistants. Whatever's held back arrives as a draft for you to publish, and a Publish key's row says when it is.
- **Name**, **What it can do** (Read, Write drafts, Publish) and **For** (most apps, or apps that publish to Ghost) - **Make a key** shows the key once, to copy. **Revoke** stops it working at once.
- Each key says when it was last used, to the minute, and by what - the API, a writing app, an AI assistant or a Ghost app - so a use you don't expect stands out.

### Webhooks

A webhook tells another service, like Zapier or your own script, when a post goes live or a comment arrives. See [Webhooks](../API.md#webhooks).

- **Address** and **Tell it when** - The address to tell, and what about. **Add** saves it; **Send a test** checks it's listening; **Remove** stops it.

### Stock photos

Search free photos from Pixabay, Pexels and Unsplash in the image picker. A row showing which are set up; **Edit** opens it. Each service gives you a free key when you sign up.

- **Pixabay API key** - From pixabay.com/api/docs
- **Pexels API key** - From pexels.com/api
- **Unsplash access key** - From unsplash.com/developers

### Updates

Gives you an **Update now** button when a new version of Soloblog is out. A row showing whether it's set up; **Edit** opens it.

- **Update hook** - A link your host gives you that redeploys your site (its deploy hook), or Watchtower's address if you run Soloblog with Docker Compose. See [Set up the Update now button](../DEPLOYMENT.md#set-up-the-update-now-button).
- **Token** - Watchtower's `WATCHTOWER_HTTP_API_TOKEN`. Empty for a deploy hook.

### Custom code

Under **Advanced**. For people who write code: your own code and styles, added to every public page of your site. It never applies to the admin, so a mistake can't lock you out.

- **In <head>** - Code added to the top of every page, like a script a service asks you to paste. Only paste code you trust.
- **This code sets cookies or tracks visitors** (on/off) - Then it waits until a visitor accepts the cookie banner, as Google Analytics does.
- **Custom CSS** - Your own styles. Your palette's colours are `var(--color-primary)` and the like.

### Environment

Under **Advanced**. Some settings are set on your host, not in Soloblog - `SESSION_SECRET`, `BASE_URL`, `SITE_TITLE`, `DATA_DIR`, `ENV` and others. This shows which of them your host sets. [Settings on the host](../DEPLOYMENT.md#settings-on-the-host) lists them all.

## Security

### Two-factor login

A second step when you log in: after your password, a 6-digit code from an authenticator app on your phone (1Password, Google Authenticator, Aegis…). **Turn on** shows a QR code to scan with the app, and ten recovery codes to keep in case you lose your phone.

### Passkeys

Log in with your fingerprint, face or device PIN instead of a password. A fake login page can't steal a passkey, and it skips the two-factor code.

- **Add a passkey** - Confirm with your fingerprint, face or device PIN. Add one on each device you log in from.
- **Name** - So you can tell your passkeys apart. Each one can be removed.

### Recovery key

Lets you choose a new password if you forget yours - select **Forgot password?** on the login page. **Make a new key** replaces it, and the old one stops working. A key is shown only once, so keep it in a password manager, or printed.

### Sessions

With **Keep me signed in** ticked on the login page, you stay logged in for 14 days on each browser; unticked, until you close the browser. **Log out other devices** logs you out everywhere except the browser you're using now. Changing your password logs out the others.

### Password

- **Current password**, then the **New password** (8 characters or more), typed twice.

### Spam protection

A row showing its current state; **Edit** opens it.

- **Extra check** - A check on comments, the contact form, newsletter sign-ups and members signing in that stops automated spam: None, Cloudflare Turnstile (free, and usually invisible to readers) or hCaptcha (free).
- **Site key** and **Secret key** - From the service's dashboard, once you add your site.

## Backup and import

### Download

A backup: a zip file of what you tick - posts and pages, images, settings, comments and messages, members, subscribers and followers, and stats and reactions.

### Restore

**Upload** a backup to see what's in it, then tick what to bring back and select **Restore**. Each part you tick replaces what your site has now. Your password and passkeys stay as they are.

### Cloud storage

Keep your images and backups in online storage of your own - an Amazon S3, Cloudflare R2 or Backblaze B2 bucket - so backups are made for you. It's set up with the `S3_` settings on your host, not here: see [Keep files in cloud storage](../DEPLOYMENT.md#keep-files-in-cloud-storage). Once connected, it shows the last backup and the backups to restore from, and you choose **How often** backups are made (a minute after changes, or once a day or a week if anything changed), how many to keep and what they include. With `BACKUP_PASSPHRASE` set on your host, backups and images in the bucket are encrypted.

### Import from another blog

Moving from WordPress, Ghost, Medium, Substack or a static site? Upload its export: your posts come across with their dates, tags and pages, and WordPress comments and Substack subscribers too.

- **Copy images into the media library** (on/off) - Copies the old blog's images to your site, so they keep working when the old blog is gone.
- **Import as drafts** (on/off) - Each post arrives as a draft, so you can look it over before you publish it.
- **Old blog's address** - Helps bring images across from Ghost and some WordPress sites.

## Post settings

Post settings are the options for one post or page. In the editor, they
open from **Settings**, the gear icon beside **Save**. On a wide screen,
they stay open beside your writing, the way the admin menu sits on the
left (**Settings > Editor** can turn that off). On a smaller screen, and
in Focus, **Settings** opens them over the text.

What you change there is saved with the post. When the panel covers the
editor, its bottom says when something is unsaved, with a **Save** of its
own. Beside the editor, use the editor's own **Save**.

### Publishing

- **Published** (on/off) - Off, it's a draft only you see.
- **Publish at** - It goes live then, in your site's time zone. Clear it
  to publish straight away.
- **Where it appears** - In the blog roll (a normal post); in the
  **menu** or the **footer** (a page, like About or Privacy); or **pinned
  to the top of the blog roll**. See
  [Make a page for the menu or footer](pages.md#make-a-page-for-the-menu-or-footer).
- **Parent page** - For a page in the menu or the footer: put it under another one
  (About > FAQ). In the menu it's a dropdown; in a footer laid out in columns, the
  page and those under it are a column.
- **Email it to subscribers** (on/off, with the newsletter sending new posts) - Switch off before it goes out to leave this post out of the newsletter.
- **Unlisted** (on/off) - Published, but only people with the link find it: it's left out
  of the blog roll, tags, search, feeds and search engines, and isn't sent
  to subscribers or followers. A page in the menu or footer stays there for
  anyone to open - a line under the switch says so.
- **Allow comments on this post** (on/off) - While comments are on for
  the site (**Settings > Comments and messages**).
- **Who can read it** (with members on) - Everyone, members or paid
  members. Others see the start, and are asked to join.
- **Password** - A password-protected post: readers see the title and
  summary, and a box for the password; the right one opens the post. Its text stays out of feeds,
  search and the newsletter. The password is kept as you typed it, so you
  can look it up to share it again - don't use one you use anywhere else.
- **Preview link** (drafts and scheduled posts, once saved) - At the top
  of Post settings: a private address to send someone, so they can read
  the post before it's published, without logging in. **Copy** copies it.

### Details

- **URL** - The post's address: a short one like `/about` for a page in
  the menu or footer, `/post/…` for the rest. Change it and the old
  address still takes people to the new one.
- **Cover image** - At the top of the post, on cards, and when the post is
  shared.
- **Hide the cover in post lists** (on/off) - Keeps the cover off the
  homepage, tag pages and search. It still shows on the post.
- **Summary** - A line about the post, in lists, search results and
  shares. Without one, the start of the post is used.
- **Tags** - Separated by commas. Select one of your tags above the field
  to add it.
- **Word goal** - Only you see it: a ring beside the word count fills as
  you write. Left empty, the post uses your default (**Settings > Editor >
  Default word goal**); type 0 for no goal on this one.

### Page

The heading counts what this page changes from the site: **Page · 2
changed**. Each setting that follows a site setting (Contents, Fold
sections, Cover image, Space between sections, Sections appear, the side panels, Page
width and a tick under Show; **Allow comments on this post** and **Email
it to subscribers** under Publishing; **Hide the cover in post lists** and
**Word goal** under Details; **Hide this post from search engines** under
Search engines) gets a thin coloured line down its left edge, and a
**Reset** button - the ↺ arrow on its name's line, just before a switch -
while this page sets it differently, and every panel's heading counts its
own. Point to **Reset** to see what the default is. It puts the setting
back to following the site - it empties the setting, so it keeps following
later changes. Choosing what the site already has isn't a
change, but it no longer follows the site.

- **Title** - Left, centred, or hidden (screen readers still read it).
  Hide it when a Hero section opens the page with its own heading.
- **Page width** - The site's column, or wide: sections and pictures may
  run wider. A section's own `Width:` line still wins - see
  [Which setting wins](put-together.md#which-setting-wins).
- **Contents** - This post's table of contents: the site's default, at the
  top, beside the post (left or right), or off.
- **Fold headings** - Whether the writing under this post's headings
  folds: the site's default, off, foldable and open, or foldable and
  folded. A section never folds.
- **Cover image** - The site's default, as wide as the text, out to the
  side panels, edge to edge, or full screen with the title over it.
- **Space between sections** - The site's default, or Small, Medium or
  Large for this post or page alone. A section's own `Space:` line still
  wins.
- **Sections appear** - The site's default, or how this post or page's
  sections come into view as they scroll in: Fade, Rise, Zoom, Slide left,
  Slide right, Slide both ways, Focus, Tilt, or None. A section's own `Appear:` line still wins.
  Nothing moves while Animations are off.
- **Tag cloud**, **Archive links** and **About the author** - Where each
  side panel goes on this post: the site's default, under the post, on
  the left, on the right, or off - even a panel that Settings hides on
  posts. Left and right need room: on a phone, on a wide page or on slides,
  they go under the post. They're greyed out while **Side panels** isn't ticked
  under Show.
- **Background sound** - One of your audio files, looping on this post or
  page - for a band, a project or a talk. **Pick** shows your audio, and
  uploads a new file too. Visitors get a play button in the corner, under
  Back to top; it never starts by itself.
- **Show** - What appears around the text. Tick any of: breadcrumbs, the
  reading progress bar, author and date, tags, Listen, likes, share
  buttons, Print or save as PDF, support links, the series' other parts,
  related posts, About the author, the newsletter sign-up and the side
  panels.

  A post starts with what **Settings > Posts > Each post shows** ticks; a
  page in the menu or footer starts with only its title and content.
  Comments have their own switch, **Allow comments**.
- **More** - Folded, and open by itself while the page uses one of these.
  They work on any post or page:
  - **Show as slides** (on/off) - Each part between `---` lines is a slide.
  - **In the wiki** (on/off) - Listed on the wiki's front page, not in the blog.
  - **Remind me to update** (on/off) - Shows when it was last updated, and
    reminds you after three months.
  - **Link to** - The page this post is about. For another website, the title links there, with a button under the words. For one of your own pages, visitors go straight to it.

### Template

- **Apply a template** - Opens the list of templates. The one you choose
  is added to the end of the page and its settings replace the page's -
  see [Apply a template to a page](writing.md#apply-a-template-to-a-page).
- **Save as a template** - Give it a name and select **Save**: the post's
  words, its Post settings, tags, summary and cover are kept, to start new
  posts from and to apply to other pages - see
  [Save a page as a template](writing.md#save-a-page-as-a-template).
  **Settings > Editor > Templates** lists yours.

### Search engines

- **Hide this post from search engines** (on/off) - It stays on your site.
- **Title for search engines** - Shown in search results and shares
  instead of the title. About 60 characters shows in full.
- **Share image** - Shown when the post is shared, instead of its cover.
- **Original URL** - Only if it was published somewhere else first.

### Series

- **Name** and **Order** - Posts with the same series name are read in
  order: each shows "Part 2 of 4" with links to the others, and
  `/series/<name>` lists them all. A **Contents** section lists them on a
  page - see [Contents](sections-templates.md#section-contents).

### History

The post as it is now, then its last 50 saved versions, each with when
and how many words. **Compare** shows what a version changed - red taken
out, green added. **Restore** puts one in the editor; nothing changes
until you save.

## Galleries

The Gallery button (or the slash menu) lets you pick several images and a
style, and inserts a block like this:

````markdown
```gallery masonry
/uploads/one.webp
/uploads/two.webp | An optional caption
```
````

A picture's caption - this one, or the one saved with it in **Media** -
shows over the bottom of it when you point at it (always on a phone), and in the
lightbox.

| Style | Looks like |
|---|---|
| `grid` | even squares |
| `masonry` | columns, each image at its own height |
| `justified` | rows of equal height, edge to edge |
| `slider` | one image at a time, with arrows, and its caption and count under it - and when every image has a caption, their names in a row above it, to pick one. Write `slider auto` to have it move along by itself, a slide every few seconds: it stops when a reader moves it, and has a pause button |
| `filmstrip` | a row that scrolls sideways, with arrows |

Leave the style out to use the default from **Settings > Posts >
Images**. To change a gallery's style without typing, put your cursor in
it and open **Insert** or type `/`: the styles are first, the one in use
marked. Every gallery image opens in a full-size viewer with arrows,
swiping and zoom (and, with **Open any image bigger with a click**,
so does every other image in a post).

## Markdown and extras

Posts are written in markdown - plain text with a few marks for
formatting. Each post is kept as an ordinary text file, so your writing
is never locked in.

You don't have to remember the marks. A name in bold in the **What**
column below is a command in the editor - on the toolbar, in **Insert**,
or in the slash menu you open by typing `/` at the start of a line - and
choosing it writes the marks for you.

Two things to know as you type:

- **Some marks need an empty line above them** when they come after a
  paragraph - a table or a divider. Without it, they join the
  paragraph as plain text. Each row below says where one is needed.
- **An indent is four spaces, or one press of Tab,** at the start of
  the line.

### Paragraphs and headings

| What | You type | You get |
|---|---|---|
| **Paragraph** | Your words, with an empty line between one paragraph and the next | Plain text. Lines with no empty line between them join into one paragraph. On a heading, **Paragraph** turns it back into plain text. |
| Line break | Two spaces at the end of a line | A new line in the same paragraph |
| **Heading** | `##`, a space, then the heading, at the start of a line | A heading that starts a new section of the post |
| **Subheading** | `###`, a space, then the subheading | A smaller heading, for a part of a section |
| **Small heading** | `####`, a space, then the heading | A heading for a few lines. It isn't in the table of contents. |
| **Clear formatting** | Nothing - put your cursor on the line and choose it | The heading, list or quote taken off that line, leaving plain text |

Your post's title is its biggest heading, so headings in the writing
start at `##`. Headings (`##` and `###`) build the post's table of
contents, get a copy-link button, and can fold (see
[Contents and sections](#contents-and-sections)).

### Text styles

| What | You type | You get |
|---|---|---|
| **Bold** | `**words**` | Words in bold, to stand out |
| **Italic** | `*words*` | Slanted words, for emphasis |
| **Strikethrough** | `~~words~~` | Words crossed out |
| **Inline code** | `` `words` `` | Words in a fixed-width font, for a bit of code or a file name in a sentence |
| **Highlight** | `==words==` | Words marked in your palette's colour |
| **Superscript** | `x^2^` | Raised text: x² |
| **Subscript** | `H~2~O` | Lowered text: H₂O |
| **Keyboard keys** | `++ctrl+c++` | Keys drawn as keys, like Ctrl+C |
| **Emoji** | `:coffee:`, `:tada:`, `:man:` | The emoji itself: ☕ 🎉 👨. Type `:` and two letters of its name for suggestions. The names are GitHub's. |
| Symbols | `(c)`, `(tm)`, `-->`, `1/2`, `1st` | ©, ™, →, ½, and 1st with a raised "st" |
| A mark as it is | `\` before the mark, like `\*` | The mark itself, without its formatting |

### Links

| What | You type | You get |
|---|---|---|
| **Link** | `[words](https://example.com)` | The words, linking to that address |
| **Link to a post or page** | Nothing - choose it, then pick a post or page from the list | A link to one of your own posts or pages, with its title as the words |
| **Link by title** | `[[Another post]]`, or `[[its-url|some text]]` for other words. Type `[[` and a few letters of the title for suggestions. | A link to another of your posts, by its title or its address. Until that post exists, the link shows red for you and as plain text for visitors. |
| Web address | `<https://example.com>` | The address itself, as a link. An address without `<` and `>` around it stays plain text. |

### Lists

A list can start on the line right under a paragraph. After the list,
leave an empty line before the next paragraph - otherwise the paragraph
joins the last item.

| What | You type | You get |
|---|---|---|
| **Bulleted list** | `-` and a space at the start of each line | Points in no particular order |
| **Numbered list** | `1.` and a space at the start of each line | Steps, numbered in order. The numbers are counted for you, so `1.` on every line works too. |
| **Checklist** | `- [ ]` and a space for something to do; `- [x]` or `- [X]` for something done | Each item with a box beside it, empty or ticked. Readers can't tick the boxes. Nothing else makes a box - not `[ x]`, and not `[x]` without a space after it. |
| A list inside a list | The inner list's lines indented by four spaces, or one press of Tab | A list under one of the points |

### Quotes

| What | You type | You get |
|---|---|---|
| **Quote** | `>` and a space at the start of each line | Someone else's words, set apart from yours. A line with only `>` starts a new paragraph inside the quote. |
| **Pull quote** | `Pull quote: A line worth repeating.` on a line of its own, with an empty line above and below | A sentence from the post shown big, with a line beside it |

### Code

| What | You type | You get |
|---|---|---|
| **Code block** | ` ``` ` on a line above the code and again on a line below it | Lines of code kept exactly as typed, in a fixed-width font, with a **Copy** button. Add the language after the first marks - ` ```python ` - to colour the code to match your palette. |
| Indented code | Every line indented by four spaces, or one press of Tab, with an empty line above | The same as a code block, without the colours |
| **Diagram** | A code block that starts ` ```mermaid ` | A flowchart, sequence diagram or timeline, drawn from the text. Switch on **Diagrams** in **Settings > Editor > Markdown** first; while it's off, the text shows as code. |

### Tables and dividers

| What | You type | You get |
|---|---|---|
| **Table** | A row of headings, a row of dashes, then a row for each line, with upright lines between the cells - like the example below. An empty line above it. | Rows and columns. A wide table scrolls sideways on a narrow screen instead of spilling out. |
| **Divider** | `---` on a line of its own, with an empty line above | A line across the post. Without the empty line, the line above turns into a heading. |

```markdown
| Name | Role  |
|------|-------|
| Ann  | Owner |
```

### Pictures

| What | You type | You get |
|---|---|---|
| **Image from your library** | Nothing - choose it, then pick a picture you've uploaded, or upload one | The picture. On a line of its own, its caption and credit from **Media** show under it. |
| **Upload image** | Nothing - choose it, then pick a picture on your device. Or paste or drop one into your writing. | The picture, added to **Media** and to the post |
| **Image by URL** | `![Text](address)`, with the picture's web address | A picture from another site |
| Picture description | The Text in `![Text](address)` | A description of the picture. Screen readers read it aloud, search engines use it, and it shows if the picture can't load. Left empty, a picture from your library uses its **Alt text** from **Media**. |
| **Gallery** | Nothing - choose it, then pick the pictures | Several pictures together, as a grid, a slider and more - see [Galleries](#galleries) |

### Callouts, tabs and other blocks

The text inside a callout, a tab or a collapsible is indented by four
spaces, or one press of Tab. "A line of its own" means an empty line
above and below it.

| What | You type | You get |
|---|---|---|
| **Callout**, **Tip**, **Warning**, **Danger** | `!!! note`, then its text on the lines under it, indented | A note in a box that stands out. Write `tip`, `warning` or `danger` in place of `note` for the others, and add a title in quotes: `!!! tip "Pro tip"`. |
| **Tabs** | `=== "First"`, then its text indented, and the same again for each tab | The same content, one tab each, that readers switch between - steps for Windows and for Mac, say |
| **Collapsible** | `??? "A heading"`, then its text indented | A heading that opens to its text. `???+` starts it open. |
| **Buttons** | `Buttons: [Join](/join) [Read more](/about)` on a line of its own | One or two buttons in the text. The first stands out. |
| **Countdown** | `Countdown: 12 March 2027` on a line of its own | Days to go until that date, and the date. Once it's passed, only the date. `2027-03-12` and `March 12, 2027` work too. |
| **Members only from here** | `<!-- members only from here -->` on a line of its own | On a post for members, where the free part ends: everyone reads up to here, members read on. See [Let readers become members](grow.md#let-readers-become-members). |

Example callout:

```markdown
!!! warning "Before you start"
    Back up your data first.
```

### Notes, terms and abbreviations

| What | You type | You get |
|---|---|---|
| **Footnote** | `A claim.[^1]` in your text, and `[^1]: The source.` on a line of its own | A small number in the text, linking to the note at the end of the post - or beside the text, with **Footnotes beside the text** in **Settings > Posts > Reading**. The editor's **Footnote** numbers it and adds the note line for you. |
| **Definition** | `Term` on one line, then `: What it means` on the next | The term, with its meaning under it |
| **Abbreviation** | `*[HTML]: HyperText Markup Language` on a line of its own | Pointing at "HTML" anywhere in the post shows what it stands for |

### Videos, maps and math

| What | You type | You get |
|---|---|---|
| **Video or embed** | The link to a video, social media post, map or form, alone on a line of its own | The video, post, map or form, shown in the post. It loads only when a reader selects it. See [Embed from other sites](writing.md#embed-from-other-sites). |
| Your own audio, video or PDF | Its address from **Media**, alone on a line of its own | A player, or the PDF shown in the post - see [Add video, audio and PDFs](writing.md#add-video-audio-and-pdfs) |
| **Math** | `$E = mc^2$` in a sentence, or `$$` on lines of their own above and below a formula | The formula, set as in a textbook. No space just inside the `$` signs - that's how "$5 and $10" stays money. Switch on **Math** in **Settings > Editor > Markdown** first. |

The parts of a page - a `##` heading with a `Section:` line under it -
each have an entry in [Sections and templates](sections-templates.md#sections).

## Image details

Select an image in **Media** to open its details.

- **Rotate left** and **Rotate right** - Turn the image a quarter at a time.
- **Crop to** and **Keep** - Crop it to a shape - Wide 16:9, Photo 3:2, 4:3, Square or Portrait 4:5 - keeping its centre, top, bottom, left or right, then select **Crop**. **Restore original** undoes any rotating or cropping.
- **Alt text** - Describes the image for people who can't see it. Leave it empty if it's only decoration.
- **Caption** - Shown under the image in posts.
- **Credit** and **Credit link** - Who made the image - a photographer, an illustrator, you - shown with it as "Image by …", and their website for the name to link to. A stock photo you add from the picker is credited by itself, as "Photo by … on Pexels".
- **Dark mode version** - Another image shown in its place while a reader's site is dark: **Pick** one you've uploaded - any image but this one. It switches with each reader's light or dark setting - see [Organise media](run.md#organise-media).
- **Phone version** - Another image shown in its place on a phone: **Pick** one you've uploaded - any image but this one. A wide screen shows the usual image. The phone picture can have a Dark mode version of its own - see [Organise media](run.md#organise-media).
- **File name** - Rename the file. Posts that use it get the new name, and links to the old one keep working. Audio, video and PDFs have this too; the rest of this list is for images.

Every post that uses the image shows a change straight away.

## Built-in pages and feeds

Soloblog makes these pages for you. There's nothing to write and no
template to start from: turn one on in **Settings** where it needs
it, and put it in the menu or footer with **Add to menu**
([Add a link or a built-in page to the menu](pages.md#add-a-link-or-a-built-in-page-to-the-menu)).

| Address | What's there |
|---|---|
| `/archive` | Every post, by month |
| `/tags`, `/tag/<name>` | Every tag, and each tag's posts (with its own feed) |
| `/series/<name>` | A series in reading order |
| `/search` | Search, also from the magnifier in the header |
| `/wiki` | The wiki's front page: notes to start from, the latest edited, the most read, the topics, and every note A to Z |
| `/links` | A link-in-bio page (**Settings > Profile and links > Links page**) |
| `/contact` | The contact form (**Settings > Comments and messages**) |
| `/newsletter` | The newsletter sign-up (when it's on) |
| `/blog` | Your posts, when a page or the wiki is your homepage |
| `/join` | Where readers become members, with your line from **On the join page** (when members are on, **Settings > Members**) |
| `/signin` | Where members sign in, with a link or code sent by email |
| `/membership` | Where readers become paid members, with your prices (once **Paid members** is set up) |
| `/account` | A member's own page: their name, getting new posts by email, **Manage billing** for a paid plan, **Download my data**, **Sign out** and **Delete my account** |

**Breadcrumbs** show above posts (Home › Series › Post). Choose what sits
in the middle in **Settings > Posts > Breadcrumbs**.


**Feeds** let readers follow your new posts in a feed reader app, like
Feedly or NetNewsWire: RSS at `/rss`, Atom at `/atom.xml`, JSON Feed at `/feed.json`,
and one per tag at `/tag/<name>/rss`.

### Addresses Soloblog uses

A page in the menu or footer gets a short address from its name, like
`/about`. These names are Soloblog's own, so a page with one of them
stays at `/post/` and its name instead:

- **Pages and sign-in:** `account`, `archive`, `blog`, `card`, `comment`,
  `comments`, `contact`, `demo`, `forgot-password`, `join`, `links`,
  `login`, `logout`, `membership`, `newsletter`, `post`,
  `reset-password`, `search`, `series`, `setup`, `signin`, `signout`,
  `tag`, `tags`, `wiki`
- **Feeds, files and connections:** `.well-known`, `admin`, `admin.js`,
  `ads.txt`, `ap`, `api`, `app.js`, `atom.xml`, `card.png`, `favicon.ico`,
  `feed.json`, `ghost`, `healthz`, `indieauth`, `manifest.webmanifest`,
  `mcp`, `micropub`, `nodeinfo`, `robots.txt`, `rss`, `sitemap.xml`,
  `static`, `stripe`, `uploads`, `webmention`

## Keyboard shortcuts

In the editor. On a Mac, use Cmd instead of Ctrl. The editor's **Help**
(Ctrl+/) has the same list, and each toolbar button shows its own when you
point at it.

| Action | Keys |
|---|---|
| Save | Ctrl+S |
| Bold / Italic / Strikethrough | Ctrl+B / Ctrl+I / Ctrl+Shift+X |
| Highlight / Inline code / Clear formatting | Ctrl+Alt+H / Ctrl+E / Ctrl+\ |
| Paragraph / Heading / Subheading / Small heading | Ctrl+Alt+0 / 2 / 3 / 4 |
| Bulleted / numbered list / checklist | Ctrl+Shift+8 / 7 / 9 |
| Quote / Code block | Ctrl+' / Ctrl+Alt+C |
| Link / Link to a post or page | Ctrl+K / Ctrl+Alt+K |
| Image from your library / Gallery | Ctrl+Alt+I / Ctrl+Alt+G |
| Preview / Focus | Ctrl+Alt+P / Ctrl+Shift+F, and Esc to leave either |
| Help | Ctrl+/ |
| Move out of the text | Esc, then Tab (Shift+Tab to go back) - on its own, Tab indents the line |
| Undo / Redo | Ctrl+Z / Ctrl+Y (Shift+Cmd+Z on a Mac) |
| Slash menu | `/` at the start of a line, then ↑ ↓, Enter or Esc |
| Emoji | `:` and two letters of its name, then ↑ ↓, Enter or Esc |
| Link by title | `[[` and a few letters of the title, then ↑ ↓, Enter or Esc |

Elsewhere:

- **Esc** closes the post settings panel, the media details panel and any
  dialog.
- In a slide deck, ← and → (or Page Up/Down) move between slides.
- In the image viewer, ← and → move between images, and Esc closes it.
- **Tab** from the top of any page reaches a "Skip to content" link first.
