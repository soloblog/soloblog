# Sections and templates

Every kind of section and every built-in template, with how to write each
one and the Key: lines it reads - a page to look things up in. To see how
sections, templates and Post settings fit together first, read
[How a site is put together](put-together.md). To do it step by step:
[Add sections](pages.md#add-sections) and
[Start a post from a template](writing.md#start-a-post-from-a-template).

**Contents:** [Sections](#sections) · [Default](#default) ·
[Width, style, heading, space and appear](#width-style-heading-space-and-appear) · [Templates](#templates) ·
[Key: value index](#key-value-index)

## Sections

A section is one part of a page with its own heading - plans, kind
words, a row of numbers, a recipe's ingredients - in any post or page,
between its paragraphs. Add one from **Insert > Sections**, or type `/`
and its name (`/pricing`, `/team`); it arrives ready to fill in, with a
line for every option it has - see [Default](#default).

Each section is a `##` heading with a `Section:` line under it saying
what kind it is. Its items are `###` headings. It runs until the next
`##` - to carry on with ordinary writing after it, start a new heading:

```markdown
## What people say

Section: Testimonials

### Sam Lee

Role: Designer

> Best desk I've owned.

## Back to the post

Ordinary writing again.
```

**Where it shows:** right where you wrote it, in the reading column or
wider - see [Width, style, heading, space and appear](#width-style-heading-space-and-appear). Its cards fit the column:
three across where there's room, two in a narrower one, one on a phone.
A page can have as many sections as you like, in any order, and the same
kind more than once. A section looks the same on every page.

**What readers see elsewhere:** the `Section:` line never shows - not on
the page, in its description, the feed or the newsletter - and a
translation keeps it as it is. A kind Soloblog doesn't know stays on the
page as you wrote it, so you can spot it.

**Another name for the same kind:** most kinds can be written under a
second name too, shown as "Also written" in each entry - `Section: Stats`
is the same as `Section: Numbers`. Capitals don't matter.

The kinds of section, in the order **Insert** lists them, each headed
with the line you write:

### Section: Picture and text

An image beside its words, the image on one side and the words on the
other, and the words under it on a phone. Under the heading: an image
and a few lines. Without an image it's just the words. Also written
`Section: Picture`.

`Style: Cover` puts the words over the image, across the whole page,
as a [Hero](#section-hero) does.

### Section: Numbers

Big figures in a row, two to a row on a phone; they count up as they
appear. Each item is `### 10,000`, with the words under it saying what
it counts. Also written `Section: Stats`.

### Section: Testimonials

Quote cards. Each item: `### Their name`, `Role: …` (or `Who:`,
`Company:`), their words (as a quote or not) and a photo if you have one.

### Section: Logos

A row of logos - as seen in, trusted by. Under the heading: the logo
images, each a link if you make it one. More than fit in a row drift
slowly sideways.

### Section: Pricing

Plan cards, one picked out. Each item: `### Plan`, `Price: …`,
`Badge: Most popular` on the one to point out, what's included, and a
link for its button. Any other key shows as a detail. Also written
`Section: Plans`.

### Section: Products

Things for sale. Each item: `### Product`, an image, `Price: …`
(`Badge: Sold out` if it is), a line and a link to buy it - from Stripe,
Gumroad, Lemon Squeezy or PayPal. There's no cart: each button goes to
its own checkout. Also written `Section: Shop`.

### Section: Services

What you offer. Each item: `### Service`, `From: US$400` (or `Price:`,
`Starts at:`), what's included and a link. Any other key shows as a
detail.

### Section: Team

People. Each item: `### Name`, a photo, `Role: …` (or `Job:`,
`Position:`) and a line about them. Also written `Section: People`.

### Section: FAQ

Questions that open to their answers. Each item: `### A question?`, then
the answer. Search engines can show them in their results. Also written
`Section: Questions`.

### Section: Photo gallery

Your photos, with their captions. Under the heading: a gallery block, in
any [gallery style](reference.md#galleries).

### Section: Call to action

One line and a button, on a card in your main colour. Under the heading:
a line, and a link for the button. For two buttons, write a
[Buttons](reference.md#callouts-tabs-and-other-blocks) line instead, like
`Buttons: [Get started](/start) [Try the demo](/demo)` - the first is
the main button, the second a quieter one beside it. To give the card a
big heading of its own, start it with one: `### Bring a friend`. Also
written `Section: CTA`.

`Style: Cover` makes it a [Hero](#section-hero): a big heading and a button
over an image, across the page.

### Section: Features

Short points side by side, each with an icon. Each item: `### Real bread`,
then `Icon: leaf` and a line or two - or an emoji first in the heading
(`### 🍞 Real bread`). The icons, by name: pen-line, palette,
layout-template, mail, users, smartphone, shield-check, database-backup,
key-round, chart-column, refresh-cw, luggage, bot, globe, lock, zap,
heart, rocket, sparkles, check, clock, star, message-circle, bell,
search, book-open, image, camera, music, coffee, gift, map-pin, calendar,
credit-card, download, cloud, code, server, wand-sparkles, leaf, puzzle,
life-buoy, languages, rss, feather, eye-off, hand-heart, house, store,
truck.

### Section: Columns

Text in columns, side by side. Each item: `### A heading` and its words.

### Section: Sign-up

Your newsletter's sign-up box, with a line about what they'll get. It
shows while the newsletter is on; with it off, readers see only the
line. Also written `Section: Signup` and `Section: Newsletter`.

### Section: Contact form

Your contact form, with a line about what to write about. It shows while
the contact form is on; with it off, readers see only the line. Also
written `Section: Contact`.

### Section: Latest posts

Your newest posts, as cards. `Count: 3` for how many (up to 12; three
with `Default` or no line) and `Tag: baking` for only that tag's posts, on
the lines straight under `Section:`. Also written `Section: Posts`.

### Section: Compare

A table of options. Write a table; ✓ or yes and ✗ or no in its cells
show as ticks and crosses. Also written `Section: Comparison`.

### Section: Steps

Numbered steps as cards - how it works, how to order. Write a numbered
list. A step that starts in **bold** gets that as its title, and a link
at its end becomes its button. Also written `Section: How it works`.

### Section: Milestones

Dated entries on a line - a history, a year in review. Each item:
`### 2024 · What happened`, its date first, and a line about it. Also
written `Section: Timeline`.

### Section: Events

Talks, workshops and readings. Each item: `### A talk`,
`Date: 12 March 2027` (or `When:`), `Place: …` (or `Where:`, `Venue:`)
and links to the slides or video. Events to come are listed first,
soonest first; past ones fold away by themselves. Search engines
understand each one as an event. Also written `Section: Talks`.

### Section: Menu

Dishes with prices, in two columns with the prices lined up. Each item:
`### A course`, then `- A dish - what's in it · €12`, in a list or a
line each.

### Section: Portfolio

Images of your work, each leading to its page. Each item:
`### A project`, an image, a line or two and a link - the image and
title lead there. A link to another site opens in a new tab, and the
title ends in ↗ so readers know it leaves your site. The link's own
words, like `[Visit](https://…)`, show only in **Full screen**, as a
button under each piece. A piece without an image is a quiet tile of its own
words. Also written `Section: Projects`. On the lines straight under
`Section:`:

- `Tag: work` adds every post and page with that tag, by its cover,
  title and summary. To let each of those pages lead on to the next one,
  give it a [Previous and next](#section-previous-and-next) section.
- `Show as:` picks the arrangement: `Grid` (even tiles, a title under
  each), `Masonry` (each image at its own shape, nothing cut off),
  `Rows` (edge to edge, each row the same height), `Full screen` (one
  piece at a time, as you scroll) or `Sideways` (a row of tall images
  you swipe along). With `Default` or no line, **Portfolio pages** in
  **Settings > Posts > Images** decides.

### Section: Reviews

Books or films, with stars. Each item: `### A book`, a cover if you
like, `Rating:` (`4/5`, `4`, `★★★★` and `4.5 out of 5` all work),
`Author:`, `Finished:` and your notes. Search engines understand each one
as a review. Also written `Section: Books`.

### Section: Uses

Things you use, and what for. Each item: `### A group` (Desk, Software),
then `- **A thing** - what it's for`, or `- [A thing](https://…) - what
it's for`.

### Section: Opening hours

When you're open, as a table: a line for each day, like
`Monday: 9am – 5pm` (two or more). A day you're shut is `Saturday:
Closed`. Search engines understand the page as a business with these
hours. Also written `Section: Hours`.

### Section: Contact details

Buttons to call, write or find you on a map: `Phone: …`, `Email: …` and
`Address: …` lines. Search engines understand the page as a local
business, with this phone, email and address - and the hours, if the
page has an [Opening hours](#section-opening-hours) section.

### Section: Resume

Jobs or schooling, each with its dates. Each item: `### Designer, Acme ·
2021 – 2024` - the title, then the dates after a `·`, a `|` or a `—` -
and a line about what you did under it. The dates sit on the right of
each entry. For a whole CV, write one section for each part (`##
Experience`, `## Education`), and a [Skills](#section-skills) section.
Search engines understand the page as a person's. Also written
`Section: CV`.

### Section: Skills

Short items as small badges. Under the heading: a list, each item 40
characters or fewer. A list with a longer item stays an ordinary list.

### Section: Profile

A personal introduction, centred. Under the heading, in any order: a
photo, one line about who you are (shown big), a couple of sentences of
bio, and a line of links, which become buttons - the first is the main
one. The `##` heading is your name, shown big under the photo. Search
engines understand the page as one about a person. Use one for the page.
To show your newest writing under it, add a
[Latest posts](#section-latest-posts) section.

### Section: Bios

Bios to copy, and photos to download - for journalists and podcast
hosts. Each item: `### Short bio`, `### Long bio` and their words; each
plain bio gets a **Copy** button. An item that holds images shows them
in a grid, each with a **Download** link. Also written
`Section: Media kit`.

### Section: Project facts

A strip of facts about one project. Under the heading, a line for each:
`Client: …`, `Year: …`, `Role: …` - any keys you like. Two across on a
phone.

### Section: Photo story

Images and words laid out like a magazine, wide. Write the story under
the heading and put the images between the paragraphs; the section
places them:

- The first paragraph is shown large.
- An image on its own runs wide. Images one after another sit side by
  side at the same height.
- A short paragraph straight after an image sits beside it, the
  images taking turns on each side.
- A quote (`>`) is shown large; a last line starting with `—` is who said
  it.
- Each `###` heading sits beside its words.

Three Key: lines turn those arrangements off, on the lines straight
under `Section:`:

- `First paragraph:` `Big` or `Normal` (the same size as the rest).
- `Pictures together:` `Side by side` or `One under another`.
- `A line after a picture:` `Beside it` or `Under it`.

Each also takes `Default`, which is the first one in each list.

### Section: Story

Images that change as the words scroll - a way to walk readers through
a tour, a process or a project, one step at a time. Under the heading,
write each step as `### A heading`, with one image and a few lines of
words under it; a link on its own line becomes the step's button. Words
before the first step show above the story. Also written
`Section: Scroll story`.

- **On a wide screen**, the words scroll in a column on the left while
  the image for the step being read stays in view on the right, whole
  and in its own shape. The image changes as the next step comes up,
  and on a computer with a mouse it tilts a little toward the pointer.
  The story's heading stays at the top while the story plays, then
  scrolls away with its end.
- **On a phone or a tablet**, each image sits just below the site's
  header, with rounded corners, and fades into the next one as you
  scroll. An image shows whole from its top, unless it's landscape: then
  it fills the area and its sides are cropped. The top stays clear and the bottom
  fades into the page's own colour, where the words sit in the text
  colour of the look you chose.
- **The words** of each step fade in as they come up, stay clear while
  you read them and fade out as they scroll away. On a touch screen,
  while the story fills it, the page comes to rest on a step as you
  scroll near one;
  the sections above and below it scroll as usual.
- **Small marks beside the image** show how many steps there are and
  which one you're on. On a phone they sit over the image's edge.
- **A step without an image** keeps the image of the step before it.
- **Where there's no motion** - **Animations** switched off in
  **Settings > Style > Motion**, or a reader's device set to reduce motion, or
  their browser not running scripts - nothing is held or fades. Each
  step shows its image and its words, one after another.

A story is as wide as the screen, so write its images to fill one: tall
ones read best on a phone. For a screenshot, give the image a phone
version so a phone shows a phone-shaped one. `Width: Wide` or `Column`
keeps it narrower.

### Section: Hero

A big heading, a line and a button over an image, across the whole
screen. Under the heading: an image, a line and a link for the button,
or a Buttons line for two - the `##` heading is the big heading. A Call to action or a Image and
text with `Style: Cover` is shown the same way.

`Style: Window` is the opening of a launch or product page: the image
is framed like an app window, with a soft glow, under a very big heading.
It also reads:

- `Label:` - a few words in a small tag above the heading, like
  `Label: Free and open source`. Write it on the first line of the
  section's words, under its `Style:` line.
- Two links on one line, like `[Try it](/demo) · [Learn more](/about)`,
  are a main button and a quieter one.
- A short bulleted list under the buttons shows as small ticked points
  in a row.

### Section: Bento grid

Tiles of different sizes, the first one big. Each item: `### A tile`, a
image if you like, a line and a link. It runs wide. Also written
`Section: Bento`.

### Section: Recipe facts

A strip of times and servings at the top of a recipe, side by side where
there's room and one under another in a narrow column. Under the
heading, a line for each: `Serves:` (or `Servings:`, `Yield:`, `Makes:`),
`Prep:` (or `Prep time:`), `Cook:` (or `Cook time:`, `Bake:`) and
`Total:` (or `Total time:`). Any other key shows beside them.

### Section: Ingredients

A list readers can tick off - each item crosses out when ticked. Under
the heading: a list. Words before or after the list stay as they are.

### Section: Method

The steps of a recipe, each with a big number. Under the heading: a
numbered list. Also written `Section: Instructions` and
`Section: Directions`.

Search engines understand a page with an Ingredients or a Method section
as a recipe. They read the first Ingredients, the first Method and the
first Recipe facts on the page. To give readers a **Print** button at the
top, tick **Print or save as PDF** under **Show** in
[Post settings](reference.md#page), as the Recipe template does.

### Section: Interview

Questions and answers as a chat. Start each paragraph with the speaker's
name in bold: `**Sam:** What got you started?`. The first speaker is on
the left in a plain bubble; everyone else is on the right in your main
colour. A paragraph that doesn't start with a bold name is shown between
the bubbles as ordinary words.

### Section: Contents

The parts of a [series](pages.md#start-a-series), in order, as a numbered
list where each is a link and the page being read is marked. It follows
the series: a part added or moved shows at once. `Series:` on the line
straight under `Section:` says which series; with `Default` or no line,
it's the page's own series - the one set in **Post settings > Series**.

While the series has no published parts, readers see nothing, not even
the heading. You see a note saying why, which only you can see - there's
no series on the page, or a series by that name doesn't exist, or none of
its parts is published yet. Also written `Section: Parts`.

### Section: Previous and next

Two large image cards leading to the pages before and after this one -
the others with the same first tag. It uses the page's first tag, so it
shows nothing for a page with no tag, or the only page with it. Readers
see nothing, not even the heading, when there's nothing to show.

## Default

Every `Key:` line a section reads takes `Default`: *follow the site*, or
what the section usually does. It means the same as having no line at
all. It follows later changes to the site, so `Show as: Default` on a
Portfolio changes when you change **Portfolio pages** in **Settings >
Posts**. You never have to type it.

**Every option is written out.** A section you add from **Insert**, with
`/`, with **+** on a phone, from **Apply a template** or in a new post
from a template comes with a line for every option it has, each set to
`Default`:

```markdown
## Latest
Section: Latest posts
Width: Default
Style: Default
Heading: Default
Space: Default
Appear: Default
Count: Default
Tag: Default
```

In the editor, a line set to `Default` is faded, and a line you've
changed is at full strength - so you can see at a glance what a section
does its own way. To change one, put your cursor in the section and open
**Insert**, type `/`, or on a phone select **+**: its options are first in
the list, with `Default` first in each and the one in use marked. Or
type the value yourself. A value that isn't one it can take is
underlined in red, with a line saying what it can be.

**Removing a line** means the same as `Default`. Choosing `Default` from
the menu writes the line again; it doesn't delete it.

**Keeping a tag called Default?** `Tag: Default` can't pick it - `Default`
is a reserved word. If your site has a tag by that name, the editor
underlines `Tag: Default` and says "Default is a reserved word"; rename
the tag to use it in a section.

## Width, style, heading, space and appear

Five Key: lines every section reads change how it's shown:

| Line | Where it goes | Values |
|---|---|---|
| `Width:` | Under a section's `Section:` line | `Column`, `Wide`, `Full` |
| `Style:` | Under a section's `Section:` line | `Card` on any section - `Cover` on a [Hero](#section-hero), [Call to action](#section-call-to-action) or [Picture and text](#section-picture-and-text), and `Window` on a Hero |
| `Heading:` | Under a section's `Section:` line | `Left`, `Centred` |
| `Space:` | Under a section's `Section:` line | `Small`, `Medium`, `Large` |
| `Appear:` | Under a section's `Section:` line | `Fade`, `Rise`, `Zoom`, `Slide left`, `Slide right`, `Slide both ways`, `Focus`, `Tilt`, `None` |

Some sections read more lines of their own, written the same way:
`Count:` and `Tag:` on [Latest posts](#section-latest-posts), `Show as:`
and `Tag:` on a [Portfolio](#section-portfolio), `Series:` on
[Contents](#section-contents), and three on a
[Photo story](#section-photo-story). A gallery's style goes after
`` ```gallery `` on its first line: `grid`, `masonry`, `justified`,
`slider` (add `auto` to move by itself) or `filmstrip` - see
[Galleries](reference.md#galleries).

**`Width: Column`, `Wide` or `Full`** - as wide as the text, out to the
side panels, or edge to edge.

- With `Default` or no line, a section is as wide as the page: the
  column, or wide on a page whose **Page width** is **Wide**. A
  [Hero](#section-hero) and a [Story](#section-story) are `Full`, and a
  [Photo story](#section-photo-story) and a
  [Bento grid](#section-bento-grid) are `Wide`. `Width: Column` keeps
  any of them in the column.
- A page with a `Wide` or `Full` section has nothing beside the post:
  the contents go to the top of the post, and the side panels (tags,
  archive, author) go under it, so the section has the room.

**`Style: Card` or `Cover`** - `Card` sets any section apart on a card of
its own. `Cover` puts its words over its image, across the page - the
same as a [Hero](#section-hero) - and only a Hero, a
[Call to action](#section-call-to-action) and
[Picture and text](#section-picture-and-text) can have it. On any other
section the `Style: Cover` line does nothing, and the editor underlines it.

**`Heading: Left` or `Centred`** - where the section's heading sits, and
the words under it before its first item. `Centred` puts both in the
middle. Its cards, steps, photos and other items stay as they are.

- With `Default` or no line, a section follows **Section headings** in
  **Settings > Header and footer**, which is **On the left** to start
  with. Set it to **Centred** and every section's heading is centred,
  except where a section says `Heading: Left`.
- A [Hero](#section-hero) and a [Profile](#section-profile) draw their
  own heading, so `Heading:` changes nothing there.

**`Space: Small`, `Medium` or `Large`** - how much room is above
the section. `Small` and `Large` give it less or more room than
`Medium`, which is the usual.

- With `Default` or no line, a section follows its page's **Space between
  sections** in **Post settings > Page**, and if the page doesn't choose,
  the site's, in **Settings > Header and footer**.
- It sets the room around that section, the room above its heading and
  the gaps inside it.
- On a page with writing of its own (a plain `##` heading anywhere), a
  section with no `Space:` line sits as close as a heading would, even
  right after another section, and so does the writing after it. The
  room between sections is for a page made of them, like a landing page.
  An opening paragraph before the first section doesn't count.

**`Appear:`** - how the section comes into view as the reader scrolls to
it, played once. `Fade`, `Rise`, `Zoom`, `Slide left`,
`Slide right`, `Slide both ways`, `Focus` and `Tilt` each move it
differently, and `None` doesn't move it at all.

- With `Default` or no line, a section follows its page's **Sections
  appear** in **Post settings > Page**, and if the page doesn't choose,
  the site's, in **Settings > Style > Motion**.
- A section's own heading stays still while its words and items come in -
  unless it draws its own heading, as a [Hero](#section-hero) does. A
  [Portfolio](#section-portfolio) brings its images in one by one.
- Where there's no motion - **Animations** switched off, or a reader's
  device set to reduce motion - nothing moves, whatever a section says.

When the same thing is set in more than one place, the closest to the
part wins: a section's own line, then the page's Post settings, then the
site's settings. See
[Which setting wins](put-together.md#which-setting-wins).

## Templates

A template is a page to start from, with its sections, sample words and
Post settings already in place. Start a post from one, or add one to a page
you've already written - see
[Start a post from a template](writing.md#start-a-post-from-a-template)
and [Apply a template to a page](writing.md#apply-a-template-to-a-page).
Once the page opens it's an ordinary page: change anything, and the
template stays as it was. A page keeps no tie to the template it started
from.

A template sets only what belongs to the page: its sections and words, its
Post settings, and a starting summary, tags and cover image. It never
changes the site's header, footer, menu, colours or fonts, and it never sets
whether the page is published, its date, its URL, who can read it,
whether it's hidden from search engines, or its series.

In the table below, **Contents off** means **Contents** in Post settings is
set to **Off**, and **bare** means that under **Show**, author and date,
tags, Listen button, likes, related posts, series links and side panels
are off. Anything a template doesn't mention follows the site.

The templates Soloblog comes with, under **Built-in**:

| Template | Sections | Post settings it sets |
|---|---|---|
| Recipe | Recipe facts, Ingredients, Method, and a plain Notes heading | Contents off. Print or save as PDF on. |
| Book or film reviews | Reviews | None. |
| FAQ | FAQ | None. |
| Resume / CV | Resume (Experience), Resume (Education), Skills | Contents off. Print or save as PDF on; author and date, tags, Listen button, likes, share buttons, series links, related posts and About the author off. The page title stays on the left, as it's the name. |
| Milestones | Milestones | None. |
| Interview | Interview | Contents off. |
| Portfolio | Portfolio | Page width wide, Contents off, bare. |
| Pricing | Pricing, and a plain Good to know heading | Page width wide, Contents off, bare. |
| Profile / home | Profile, Latest posts (Count 3) | Title hidden, as the Profile's heading is the name. Contents off, bare, and About the author off. |
| Landing page | Hero (Style Window), Picture and text twice, Numbers, Testimonials, Pricing, FAQ, Call to action | Title hidden, page width wide, space between sections large, Contents off, bare. |
| Services | Services (Width Column), Steps | Contents off, bare. |
| Testimonials | Testimonials (Width Column) | Contents off, bare. |
| Project | Project facts, Photo story, Previous and next | Page width wide, cover image full screen, Contents off. |
| Talks and events | Events | None. |
| Small business | Contact details, Opening hours, and a plain Finding us heading | Contents off. |
| Menu | Menu (Width Column) | Contents off, bare. |
| Media kit / press | Bios, and plain Past interviews and Get in touch headings | Contents off. |
| Coming soon | Sign-up | Title centred, Contents off. Nothing shown around the page. |
| Team | Team | Page width wide, Contents off, bare. |
| Shop | Products, and a plain Shipping heading | Page width wide, Contents off, bare. |
| Journal / weekly notes | None, plain headings | None. |
| How-to | Steps; plain What you'll need and If something goes wrong headings | Contents at the top. |
| Now page | None, plain headings | Remind me to update on, Contents off. Related posts and series links off. |
| Privacy policy | None, plain headings | None. Starts as a footer page. |
| Terms | None, plain headings | None. Starts as a footer page. |
| Wiki / notes | None, plain headings and `[[links]]` | In the wiki on. |
| Photo story | Photo story, Previous and next | Page width wide, cover image full screen, Contents off. |
| Link post | None, a quote and plain words | None. Its words say where **Link to** is. |
| Docs / guide | Steps; plain Before you start, Check it worked and Next headings | Contents on the left. Series links on. |
| Uses | Uses | None. |
| Slides | None, slides cut by `---` lines | Show as slides on. |

**Privacy policy** and **Terms** start in the footer. **How-to** starts
with its contents at the top.

### Custom templates

Any post can be saved as your own template - see
[Save a page as a template](writing.md#save-a-page-as-a-template). It's
listed under **Custom** when you start a post or apply a template, with
a **Custom** label, and in **Settings > Editor > Templates**, where you
can start a post from it or remove it.

A custom template keeps the page's words, with the sections as written,
its Post settings (every one a template can set, listed above) and its
tags, summary and cover image. It's made of exactly what the built-in
ones are.

## Key: value index

Every key, A to Z. Write it as the key, a colon and a value on a line of
its own - see [Writing a Key: value](put-together.md#writing-a-key-value).

| Key | Where | Its values | See |
|---|---|---|---|
| `A line after a picture:` | Photo story | `Beside it` or `Under it` - or `Default` | [Photo story](#section-photo-story) |
| `Address:` - also `Where:`, `Location:`, `Find us:` | Contact details | The address - a button to find it on a map | [Contact details](#section-contact-details) |
| `Appear:` | Any section | `Fade`, `Rise`, `Zoom`, `Slide left`, `Slide right`, `Slide both ways`, `Focus`, `Tilt` or `None` - or `Default` | [Width, style, heading, space and appear](#width-style-heading-space-and-appear) |
| `Author:` | Reviews | Who wrote it | [Reviews](#section-reviews) |
| `Badge:` | Pricing, Products | Any label - `Most popular`, `Sold out` | [Pricing](#section-pricing) |
| `Buttons:` | Anywhere in your writing | One or two links | [Callouts, tabs and other blocks](reference.md#callouts-tabs-and-other-blocks) |
| `Cook:` - also `Cook time:`, `Bake:` | Recipe facts | A time - `30 min` | [Recipe facts](#section-recipe-facts) |
| `Count:` | Latest posts | A number, up to 12 - or `Default` | [Latest posts](#section-latest-posts) |
| `Countdown:` | Anywhere in your writing | A date - `12 March 2027` | [Callouts, tabs and other blocks](reference.md#callouts-tabs-and-other-blocks) |
| `Date:` - also `When:` | Events | A date - `12 March 2027` | [Events](#section-events) |
| `Email:` | Contact details | An email address - a button to write | [Contact details](#section-contact-details) |
| `Finished:` | Reviews | When you finished it | [Reviews](#section-reviews) |
| `First paragraph:` | Photo story | `Big` or `Normal` - or `Default` | [Photo story](#section-photo-story) |
| `From:` - also `Starts at:`, `Price:` | Services | The price it starts at | [Services](#section-services) |
| `Heading:` | Any section | `Left` or `Centred` - or `Default` | [Width, style, heading, space and appear](#width-style-heading-space-and-appear) |
| `Icon:` | Features | An icon's name - `leaf` | [Features](#section-features) |
| `Label:` | Hero | A few words above the heading, with `Style: Window` | [Hero](#section-hero) |
| `Monday:` (any day) | Opening hours | That day's hours - `9am – 5pm`, `Closed` | [Opening hours](#section-opening-hours) |
| `Phone:` | Contact details | A phone number - a button to call | [Contact details](#section-contact-details) |
| `Pictures together:` | Photo story | `Side by side` or `One under another` - or `Default` | [Photo story](#section-photo-story) |
| `Place:` - also `Where:`, `Venue:`, `Location:` | Events | Where it is | [Events](#section-events) |
| `Prep:` - also `Prep time:` | Recipe facts | A time - `15 min` | [Recipe facts](#section-recipe-facts) |
| `Price:` | Pricing, Products | The price, and what it's per - `€45 per person` | [Pricing](#section-pricing) |
| `Pull quote:` | Anywhere in your writing | A sentence to show big | [Quotes](reference.md#quotes) |
| `Rating:` | Reviews | `4/5`, `4`, `★★★★` or `4.5 out of 5` | [Reviews](#section-reviews) |
| `Role:` - also `Who:`, `Company:` (testimonials), `Job:`, `Position:` (team) | Team, Testimonials | Who they are | [Team](#section-team) |
| `Section:` | Any `##` | A kind of section - `Pricing`, `Team`… | [Sections](#sections) |
| `Serves:` - also `Servings:`, `Yield:`, `Makes:` | Recipe facts | How many it serves | [Recipe facts](#section-recipe-facts) |
| `Series:` | Contents | A series' name - or `Default` for the page's own | [Contents](#section-contents) |
| `Show as:` | Portfolio | `Grid`, `Masonry`, `Rows`, `Full screen` or `Sideways` - or `Default` | [Portfolio](#section-portfolio) |
| `Space:` | Any section | `Small`, `Medium` or `Large` - or `Default` | [Width, style, heading, space and appear](#width-style-heading-space-and-appear) |
| `Style:` | Any section | `Card` - or `Cover` on a Hero, Call to action or Picture and text, and `Window` on a Hero - or `Default` | [Width, style, heading, space and appear](#width-style-heading-space-and-appear) |
| `Tag:` | Portfolio, Latest posts | A tag's name - `work` - or `Default` | [Portfolio](#section-portfolio) |
| `Total:` - also `Total time:` | Recipe facts | A time - `45 min` | [Recipe facts](#section-recipe-facts) |
| `Width:` | Any section | `Column`, `Wide` or `Full` - or `Default` | [Width, style, heading, space and appear](#width-style-heading-space-and-appear) |
| Any other key | Project facts and Recipe facts; a detail on a plan, product, service, team member, event or book | Anything - `Client: Corner Café`, `Duration: 2 hours` | [Project facts](#section-project-facts) |
