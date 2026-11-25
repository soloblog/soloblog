# How a site is put together

A site's look is made of a few parts, from the whole site down to a
single Key: value in a post. This page explains what each part changes,
which one wins when two disagree, and how to write a Key: value. Every
section, template and Key: value is listed in
[Sections and templates](sections-templates.md).

**Contents:** [The parts, from biggest to smallest](#the-parts-from-biggest-to-smallest) ·
[Which setting wins](#which-setting-wins) ·
[Templates, sections and Post settings](#templates-sections-and-post-settings) ·
[Writing a Key: value](#writing-a-key-value) ·
[Every Key: value](#every-key-value)

## The parts, from biggest to smallest

| Part | What it changes | Where you choose it |
|---|---|---|
| **Starting style** (a settings preset) | Many settings at once: how posts are listed, the fonts, the header, the side panels and more - a personal blog, a magazine, a portfolio | **Settings > Style > Settings presets** |
| **Colours and fonts** | The site's palette and its type | **Settings > Style** |
| **Blog layout** | How the list of posts looks on the homepage and in tags and archives - cards, a list, a magazine | **Settings > Blog layout** |
| **Settings** | What every post starts with - its cover width, contents, gallery style and what it shows | **Settings > Posts** |
| **Post settings** | One post's or page's own choices - its title, width, cover, contents, what shows around it, and what kind of page it is | **Post settings** in the editor |
| **Section** | One part of a post or page - plans, kind words, a row of numbers, a recipe's ingredients | **Insert > Sections**, or `Section:` |
| **Block** | A small thing between paragraphs - buttons, a pull quote, a countdown | **Insert > Blocks** |
| **Key: value** | A detail of a section or one of its items - a price, a width, an arrangement | Typed on a line of its own, like `Price: €12` |

A **template** isn't one of these parts: it's a page to start from, with
its sections, words and Post settings already chosen. See
[Templates, sections and Post settings](#templates-sections-and-post-settings).

A starting style changes settings only. It never changes your colours
or your posts, so the sections and Key: values in them stay as you
wrote them.

## Which setting wins

When the same thing is set in more than one place, the one closest to
what it changes wins. From the closest:

1. **A section's own Key: line** - that section only. A `Width: Column`
   line keeps one section in the column.
2. **The page's Post settings** - the whole page. A **Page width** of
   **Wide** lets every section run wider.
3. **The site's settings** - every page. **Settings > Posts**,
   **Settings > Header and footer** and the others.
4. **Soloblog's own default**, for anything none of those say.

So set what most of your site should look like in **Settings**, and
change one page or one section where it needs to be different. For
example, if every cover on your site is full screen but one page's
**Cover image** says **Edge to edge**, that page's cover runs edge to
edge. **Portfolio pages** in Settings arranges every portfolio, but a
portfolio with `Show as: Rows` shows in rows. Likewise **Section
headings** in Settings centres every section's heading, but a section
with `Heading: Left` keeps its heading on the left. And a page whose
**Sections appear** says **Rise** rises its sections even if the site
fades them, until a section says `Appear: Zoom`.

`Default` - or no line at all - in a section means "follow what's below
it": the page's Post settings, then the site's. See
[Default](sections-templates.md#default). In Post settings, a coloured
line beside a setting marks what this page sets differently from the site,
and **Reset** - the ↺ arrow beside it - puts it back.

A template isn't one of these. Applying one writes its settings into the
page's Post settings, where they work like any you'd chosen yourself.

## Templates, sections and Post settings

Three things make up a page. A **template** is a page to start from, a
**section** is one part of it, and **Post settings** are its frame and
what kind of page it is.

| | What it is | Built-in | Custom |
|---|---|---|---|
| **Template** | A page to start from, with its sections, words and Post settings in place | 31 | Yes - save any page as one |
| **Section** | One part of a page, on any page, as many as you like | 41 kinds | No - change one with its Key: lines |
| **Post settings** | The page's frame and kind: its title, width, cover, contents, what shows around it | - | - |

A **template** is only where a page starts. Once it opens, it's an
ordinary page: change anything, and the template stays as it was. The page
keeps no tie to it. To make your own, save any page as a template - see
[Save a page as a template](writing.md#save-a-page-as-a-template). To add a
template to a page you've already written, see
[Apply a template to a page](writing.md#apply-a-template-to-a-page).

A **section** is one part of a page - your plans, a team, questions, a
recipe's ingredients, a gallery - in any post. A `##` heading with a
`Section:` line under it says what it is; without that line, a `##` is
ordinary writing. A page can have as many sections as you like, and each
looks the same on every page.

**Post settings** are the page's own choices: its title (left, centred or
hidden), its width (column or wide), cover image, contents, the space
between sections, the side panels and what shows around the text. A few
less common ones say what kind of page it is: **Show as slides**, **In the
wiki**, **Remind me to update** and **Link to**. Every one works on every
page, whatever template it started from - a template only fills them in.
See [Page](reference.md#page).

So a recipe isn't a separate kind of page. It's the **Recipe** template: a
page with **Recipe facts**, **Ingredients** and **Method** sections, and
**Print or save as PDF** switched on. Start from it, or add those sections
to any page.

**Built-in pages** - the archive, tags, search, the contact form, the
wiki's front page and the rest - are made for you. They have no template
to start from: turn one on in **Settings** where it needs it, and add it
to the menu or footer with **Add to menu**. See
[Built-in pages and feeds](reference.md#built-in-pages-and-feeds).

**Making a pricing page, an FAQ or a team page?** Start from its
template, in
[Start a post from a template](writing.md#start-a-post-from-a-template).
You get the page with its section written out, ready to fill in.

**Building a whole page out of sections?** Start from the **Landing
page** template. It opens with a Hero, sets the title to hidden and the
page width to wide, and gives sections room of their own - see
[Add sections](pages.md#add-sections).

## Writing a Key: value

A Key: value is a key (a name, like `Price`), a colon and a value, on a
line of its own - `Price: €12` or `Width: Wide`. It changes how
something shows, and readers never see it.

Where you write it decides what it changes:

- **Straight under a section's `Section:` line** - for the whole section,
  like `Width: Full` or `Count: 6`.
- **Under an item's heading** - for that one item, like a plan's
  `Price:` or a person's `Role:`.
- **In a section's words** - the facts a section is made of, like Recipe
  facts' `Serves:` or Project facts' `Client:`.

Every Key: value a section reads also takes `Default`, which is the same
as leaving the line out. A section you add from **Insert** comes with all
its lines written, each set to `Default`.

Write them straight under their heading, one after another with no
empty line between them. Start each key with a capital letter; the
value can be in capitals or not - `Width: Wide` and `Width: wide` do
the same.

**Spelt a section wrong?** A `Section:` with a kind Soloblog doesn't
know stays on the page as you wrote it, so you can spot it.

**Which widths are there?** A width is always `Column`, `Wide` or
`Full` - the same three as **Cover image** in Settings, where Full is
called **Edge to edge**. See [Width, style, heading, space and appear](sections-templates.md#width-style-heading-space-and-appear).

## Every Key: value

Every key, what it does and the values it takes are in the
[Key: value index](sections-templates.md#key-value-index), and each one
is explained in its section's own entry in
[Sections and templates](sections-templates.md).

**Not Key: values, but settings:** a post's cover width, contents,
collapsible headings and side panels are in its **Post settings**
([Page](reference.md#page)). The defaults for galleries, portfolios,
covers and contents are in **Settings > Posts**, and how sections come
into view is under **Settings > Style > Motion**.

See also: [Sections and templates](sections-templates.md) ·
[Start a post from a template](writing.md#start-a-post-from-a-template) ·
[Pick a starting style](design.md#pick-a-starting-style)
