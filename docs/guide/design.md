# Designing the site

Change how your site looks to readers - its overall style, colours,
fonts, header, footer and homepage. Your writing isn't changed by any of
it.

These settings are on the **Design** pages in Settings: **Style**,
**Blog layout**, **Posts**, **Header and footer** and **Banner**.

**See each change before you save it:** on a Design page, select
**Preview mode**. Your site fills the screen, with the page's settings
down the left, and your site changes as you change each setting. Choose
whether to look at the homepage, a post or a page, and how it looks on a
**Computer** or a **Phone**. **Close** (or **Esc**) takes you back. On a
smaller screen, Preview mode opens your site in a tab of its own.

**Contents:** [Pick a starting style](#pick-a-starting-style) ·
[Choose colours](#choose-colours) ·
[Add custom colours](#add-custom-colours) ·
[Choose fonts and text size](#choose-fonts-and-text-size) ·
[Arrange the header and footer](#arrange-the-header-and-footer) ·
[Choose how posts are listed](#choose-how-posts-are-listed) ·
[Place the side panels](#place-the-side-panels) ·
[Add a homepage banner](#add-a-homepage-banner) ·
[Add a logo and icons](#add-a-logo-and-icons)

## Pick a starting style

A starting style, called a **settings preset**, changes your whole
site's look in one go - to a personal blog, a magazine, a portfolio or a
link-in-bio page, for example.

1. Open **Settings > Style**.
2. Under **Settings presets**, select **Preview** on a preset to see your
   own site in that style.
3. Select **Use this** on the one you want.

The preset sets how your posts are listed, what each post shows, the side
panels, the header and the fonts. Your colours and your writing stay as
they are.

**Didn't like it?** Select **Undo it**. Everything the preset changed
goes back to how it was.

**Want to keep your current look before trying others?** Select **Save
current look** on **Custom**. To come back to it later, select **Use
this** on **Custom**.

**Choosing Portfolio, Freelancer, Small business, Docs, Wiki, Launch or
Link in bio?** These are built around a page that becomes your homepage. Choose one of your own
pages, or let the preset make a new one for you to fill in.

**Want everything as it was when you installed Soloblog?** Select **Use
this** on **Default**. It asks first. Your posts, pictures and pages
stay.

See also: [How a starting style fits with the rest of a site](put-together.md#the-parts-from-biggest-to-smallest)

## Choose colours

Pick the colours your site is shown in. Each site has a light set of
colours and a dark set, called palettes.

1. Open **Settings > Style**, and go to **Colours**.
2. Choose one of the **Matching pairs** - a light and a dark palette that
   go together. Or choose a **Light palette** and a **Dark palette**
   yourself.
3. Under **Visitors see**, choose what each visitor gets: the palette
   that matches their device's light or dark setting, always light, or
   always dark.
4. Select **Save**.

There are 35 palettes to choose from. In each one, the text colours are
adjusted to be easy to read.

**Want readers to choose their own colours?** Switch on **Let readers
pick other colours**. A Colours menu appears in your site's header, and
what a reader picks changes the colours for them only.

**Want the page to show faintly through the header and menus?** Switch
on **Frosted glass**.

**A screenshot or diagram too bright on the dark palette?** Give it a dark
mode version in **Media** - see
[Organise media](run.md#organise-media).

See also: [Add custom colours](#add-custom-colours)

## Add custom colours

Use any colours you like, beyond the 35 palettes that come with
Soloblog. You make the palette on daisyUI's website, then paste it in.

It's more than colours: a palette made there also sets how round the
corners of buttons and boxes are, how thick their borders are, how big
fields and buttons are, how deep the shadows look, and a light grain
texture. All of these come with it.

1. Make a palette with [daisyUI's theme generator](https://daisyui.com/theme-generator/)
   and copy its CSS - the block of text it gives you.
2. Open **Settings > Style**. Under **Colours**, find **Custom
colours** and select **Add colours**.
3. Paste the CSS. A preview shows your colours as you paste.
4. Give the palette a name and select **Save**.

Your palette is now first in the **Light palette** or **Dark palette**
list, and in readers' Colours menu. Its text colours are adjusted just
enough to be easy to read.

**Want to change it?** Select **Change** to paste a new version, or to
rename it.

**Don't want it any more?** Select **Delete**. It asks first. If your
site was using that palette, it goes back to the default one.

You can keep up to 10 palettes of your own.

## Choose fonts and text size

Set the fonts, and how big the text is, across your site.

1. Open **Settings > Style**, and go to **Fonts and text size**.
2. Choose a **Text font** for your writing and a **Heading font** for
   titles and headings. Each font's name is shown in that font, so you
   can see what it looks like; type to find one.
3. Choose a **Text size**: **Small**, **Medium** or **Large**.

The fonts are ones already on readers' phones and computers, so your
pages don't have to download them and stay fast.

**What does Medium mean?** The size the reader's browser is set to. Anyone
who has made the text bigger in their browser still gets it bigger.

**Does the admin change too?** The text size does. The admin keeps its
own fonts.

## Arrange the header and footer

The header is the bar at the top of every page, with your site's name and
menu. The footer is the area at the bottom. You choose how each one looks
and behaves.

1. Open **Settings > Header and footer**.
2. Under **Header**, choose a **Header position** - whether it scrolls
   away with the page, stays at the top, or floats over the page - and a
   **Header layout**: the menu beside your site's name, behind a button,
   or on a row of its own.
3. Under **Footer**, choose a **Layout**. In **What to show**, tick what
   goes in it - your bio, social links, pages, the copyright line and the
   small print - and drag them into the order you want.

**Want a narrower column of text, easier to read?** Under **Width and
spacing**, set **Reading column** to **Narrow**.

**Want more or less room between a page's sections?** Under **Width and
spacing**, choose **Small**, **Medium** or **Large** for **Space between
sections**. It changes every page - a landing page's sections, the
sections in a post, a project's pictures, and the gap before comments.
For one page only, open its **Post settings > Page** and choose
**Space between sections** there. One section can say otherwise with its
own `Space:` line. On a wide screen **Small** is about half an inch,
**Medium** an inch and a half and **Large** three inches; a phone gets
less. The space is for one section to the next: a section that comes
straight after ordinary writing sits as close as a heading would, so
the reading flows on.

**Want sections to move as they come into view?** Under **Advanced** in
**Settings > Style > Motion**, choose how for **Sections appear** - Fade,
Rise, Zoom and more. It needs **Animations** on, and it never moves for
a reader whose device is set to reduce motion. A section's cards or
pictures come in one after another, a heading comes in with the section
under it, and the writing between sections moves the same way. For one
page only, choose
**Sections appear** in its **Post settings > Page**; one section can say
otherwise with its own `Appear:` line - see
[Width, style, heading, space and appear](sections-templates.md#width-style-heading-space-and-appear).

**Want every section's heading in the middle?** Under **Width and
spacing**, set **Section headings** to **Centred**. The heading and the
words under it move; the cards and pictures stay where they are. One
section can say otherwise with its own `Heading:` line - see
[Width, style, heading, space and appear](sections-templates.md#width-style-heading-space-and-appear).

**Too many links to fit in the header?** Set **Header width** to reach
out to the side panels. Links that still don't fit go under **More**.

**Want your own copyright line?** Type it in **Footer note**. Left empty,
it says "© your site's name".

**Want to change what's in the menu?** The menu is made of your pages -
see [Make a page for the menu or footer](pages.md#make-a-page-for-the-menu-or-footer).

## Choose how posts are listed

Choose how your homepage and tag pages show the list of your posts.

1. Open **Settings > Blog layout**.
2. Under **Posts are shown as**, choose **List**, **Cards**,
   **Magazine** (the newest post large, the rest as cards), **Minimal**
   (only dates and titles) or **Timeline**.
3. Under **Each post in the list shows**, tick what to show for each post
   - its cover image, date, reading time, summary and tags.
4. Choose how many **Posts per page**.

**Posts without a cover image leaving gaps among the cards?** With Cards
or Magazine, switch on **Placeholder for posts without a cover**. Those
posts get a tile in your site's colours instead.

**Want fewer, bigger cards?** Set **Cards in a row** to two, or one.

**Want your posts grouped by year?** Choose **Minimal**, then choose how
to **Group posts by**.

## Place the side panels

Side panels are small boxes beside or under your posts: your tags (the
tag cloud), links to past months (the archive), and a short About the
author box.

1. Open **Settings > Blog layout**, and go to **Side panels**.
2. For **Tag cloud**, **Archive links** and **About the author**, choose
   where each one goes: under the posts, on the left, on the right, or
   off.
3. Under **Shows on**, tick where each one appears: **The blog roll**
   (the list of your posts), **Posts** and **Pages**. **Shows on** is
   hidden while a panel is off, and clearing every tick turns it off.
4. Drag them into the order you want.

On a phone, on a wide page, on slides or on a page with a `Wide` or
`Full` section, the side panels move under the page, and the contents
move to the top.

**Want them without a box around them?** Switch on **Blend side panels
into the page**.

**Want one post without side panels?** In that post's **Post settings >
Page**, under **Show**, untick the side panels.

**Where does About the author get its words and photo?** From
**Settings > Profile and links**.

## Add a homepage banner

A banner is a big welcome at the top of your homepage - a heading, a line
under it, and a button if you want one.

1. Open **Settings > Banner**.
2. Switch on **Show a banner above your posts**.
3. Type a **Heading** and a **Subheading**.
4. For a button, type its **Button text**, and set where it goes in
   **Button link**. **Pick** lists your posts and built-in pages to
   choose from.
5. Choose a **Background image** and a **Width**.

**Don't want a button?** Leave **Button text** and **Button link** empty.

## Add a logo and icons

Put your logo beside your site's name, and your icon in browser tabs and
on phones' home screens.

1. Open **Settings > Header and footer**, and go to **Icons**.
2. Beside **Header icon**, select **Pick** and choose your logo.

Your logo is also used as the **Favicon** - the small icon in browser
tabs and bookmarks - and as the icon on phones, unless you pick others.

**For phones' home screens:** when someone adds your site to their
phone's home screen, it shows an icon and a name, like an app. To choose
them, open **On a phone's home screen**, under **Advanced** at the
bottom of the page. An **App icon** looks best square, 512 × 512 pixels
or larger. **App name** is the name under it.

**Want your own CSS or a web font?** Add it in **Settings >
Integrations**, under **Advanced**, in **Custom code**. It applies to
your public pages only, so a mistake can't lock you out of the admin.
