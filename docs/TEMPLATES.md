# Templates and sections

What each built-in template sets and what each section reads and draws. A
test (`tests/test_templates_doc.py`) checks that every template and every
section has an entry here, so a new one can't be added without it. How to
add one is in [DEVELOPMENT.md](DEVELOPMENT.md#adding-a-section).

A **template** is a starting copy: sections, sample words and Post settings.
A page keeps no tie to the template it started from. A **section** is one
part of a page, the same on every page: a `##` with a `Section:` line, its
`Key:` lines under it and its `###` items.

Every section takes `Width:`, `Style:`, `Heading:` (`Left` or `Centred`;
`Default` follows the site's **Section headings**), `Space:` (`Small`,
`Medium` or `Large`) and `Appear:` (how it comes into view). For `Space:` and
`Appear:`, `Default` follows the page's Post settings, then the site's.

Which setting wins: a section's own `Key:` line, then the page's Post
settings, then the site's settings, then Soloblog's default.

## Templates

Every template is a standard page with sections. "Show" lists what the
template changes of what the site shows around a post; the rest follows the
site. Every template has Contents off unless it says otherwise.

| Template | Sections | Post settings it sets |
|---|---|---|
| Recipe | Recipe facts, Ingredients, Method; a plain Notes heading | Contents off. Show: Print on. |
| Book or film reviews | Reviews | None. |
| FAQ | FAQ | None. |
| Resume / CV | Resume (Experience), Resume (Education), Skills | Contents off. Show: Print on; author and date, tags, listen, likes, share, series links, related posts and about the author off. Page title stays on the left; no Profile section, as the title is the name. |
| Milestones | Milestones | None. |
| Interview | Interview | Contents off. |
| Portfolio | Portfolio | Page width wide, Contents off. Show: author and date, tags, listen, likes, related posts, series links and side panels off. |
| Pricing | Pricing; a plain Good to know heading | As Portfolio. |
| Profile / home | Profile, Latest posts (Count 3) | Title hidden (the Profile's own heading is the name), Contents off. Show: author and date, tags, listen, likes, related posts, about the author, series links and side panels off. |
| Landing page | Hero (Style Window), Image and text twice, Numbers, Testimonials, Pricing, FAQ, Call to action | Title hidden, page width wide, section spacing large, Contents off. Show as Portfolio. |
| Services | Services (Width Column), Steps | Contents off. Show as Portfolio. |
| Testimonials | Testimonials (Width Column) | Contents off. Show as Portfolio. |
| Project | Project facts, Photo story, Previous and next | Page width wide, cover full screen, Contents off. |
| Talks and events | Events | None. |
| Small business | Contact details, Opening hours; a plain Finding us heading | Contents off. Search engines get the business from the two sections. |
| Menu | Menu (Width Column) | Contents off. Show as Portfolio. |
| Media kit / press | Bios; plain Past interviews and Get in touch headings | Contents off. |
| Coming soon | Sign-up | Title centred, Contents off. Show: nothing. |
| Team | Team | As Portfolio. |
| Shop | Products; a plain Shipping heading | As Portfolio. |
| Journal / weekly notes | None, plain headings | None. |
| How-to | Steps; plain What you'll need and If something goes wrong headings | Contents at the top. |
| Now page | None, plain headings | Remind me to update on, Contents off. Show: related posts and series links off. |
| Privacy policy | None, plain headings | None. Starts as a footer page. |
| Terms | None, plain headings | None. Starts as a footer page. |
| Wiki / notes | None, plain headings and `[[links]]` | In the wiki on. |
| Photo story | Photo story, Previous and next | Page width wide, cover full screen, Contents off. |
| Link post | None, a quote and plain words | None. Its words say where Link to is (Post settings > Page > More). |
| Docs / guide | Steps; plain Before you start, Check it worked and Next headings | Contents on the left. Show: series links on. |
| Uses | Uses | None. |
| Slides | None, slides cut by `---` lines | Show as slides on. |

Not in a template: Published, the date, the URL, Members only, Unlisted,
search engines, the menu, the footer and the series. A template never
changes the site's header or footer.

## Sections

Every section reads **Width** and **Style**, and writes both lines out with
`Default`.

- **Width**: Column, Wide or Full. Default is the section's own width: Column
  on a column page, Wide on a wide page; Hero and Story are Full, Photo
  story and Bento grid Wide. A section is wider than the column only on a page of writing.
- **Style**: Card sets the section apart on a card; Cover draws it as a Hero
  (its image across the page, its text over it) and only Hero, Call to
  action and Image and text take it - on any other section it is
  ignored. Default is no card or cover. Hero also takes Window.
- Every other `Key:` takes `Default` too: it means "follow the site", or the
  section's own usual choice, as the `/` menu says.

Search-engine data: Recipe (Ingredients or Method, with the first Recipe
facts), Person (Resume or Profile, once per page), LocalBusiness (Contact
details or Opening hours, once per page), FAQPage (FAQ), Event (Events) and
Review (Reviews).

| Section | Reads | Draws |
|---|---|---|
| Image and text | The first image and the text | The image beside its text, framed. |
| Numbers | Each `###` a figure, the line under it | Big figures in a row. |
| Testimonials | Each `###` a person, `Role:`, a quote | Quote cards with who said them. |
| Logos | The images, each optionally a link | A row of logos. |
| Pricing | Each `###` a plan; `Price:`, `Badge:`, a list, a link | Plan cards, the badged one picked out. |
| Products | Each `###` a product; image, `Price:`, `Badge:`, a link | Product cards with a buy button. |
| Services | Each `###` a service; `From:`, words, a link | Cards with a starting price and a button. |
| Team | Each `###` a person; image, `Role:`, words | Cards with a photo, role and line. |
| FAQ | Each `###` a question, the text under it its answer | Questions that open to their answers. |
| Photo gallery | A `gallery` block | The site's gallery styles. |
| Call to action | The words, and the last link or a Buttons line | One line and a button (or a main and a quieter one) on a card in the main colour. |
| Features | Each `###` a point; `Icon:`, words | Short points with an icon, side by side. |
| Columns | Each `###` a column | Text in columns, side by side. |
| Sign-up | The text | The newsletter sign-up box under the text. |
| Contact form | The text | The contact form under the text. |
| Latest posts | `Count:` (1 to 12, Default three), `Tag:` (Default any) | The newest posts as cards. |
| Compare | A table; checkmarks and crosses | A table of options with checkmarks. |
| Steps | The first numbered list | Numbered steps as cards. |
| Milestones | Each `###` a dated entry, its date before a `·` | Entries on a line. |
| Events | Each `###` an event; `Date:`, `Place:`, words, links | Events to come, then past ones by their date. |
| Menu | Each `###` a group, a list of `Dish - about · price` | Dishes with prices, lined up. |
| Portfolio | Each `###` a project; image, words, a link; `Show as:` (Grid, Masonry, Rows, Full screen, Sideways; Default follows the site), `Tag:` (adds every post with the tag) | Images of work, each leading to its page. |
| Reviews | Each `###` a title; `Author:`, `Rating:`, `Finished:`, words | Books or films with stars. |
| Uses | Each `###` a group, a list of `**item** - what for` | Things you use, and what for. |
| Opening hours | `Day: hours` lines | A table of hours. |
| Contact details | `Phone:`, `Email:`, `Address:` lines | Buttons to call, write and find you on a map. |
| Resume | Each `###` an entry, its dates after `·`, `\|` or `—` | Entries with their dates on the right. |
| Skills | A list of items of 40 characters or fewer | Small badges; a longer list stays a list. |
| Profile | The first image, the first paragraph that isn't only links, the rest, a paragraph or list of only links, and the `##` | A round photo, the `##` as the name big, the line, the bio and buttons (the first the main one), centred. The `##` is the page's name for the person. |
| Bios | Each `###` a bio; images in an item | A Copy button on each plain bio; images in a grid with Download links. |
| Project facts | Each `Key: value` line (Client, Year, Role...) | A strip of facts, two across on a phone. |
| Photo story | `First paragraph:` (Big or Normal), `Images:` (Side by side or Stacked), `Captions:` (Beside or Under) | A magazine arrangement: a lone image wide, images in a row side by side, a short line beside its image (sides taking turns), quotes as pull quotes, a big first paragraph, each `###` beside its words. |
| Story | Each `###` a step: its first image, its text and its last link; text before the first step | Steps whose text scrolls while the step's image is held: beside the words on a wide screen, filling the screen behind them on a phone, fading from one to the next. A step with no image keeps the one before it. A plain stack of images and words where scripts or motion are off. |
| Hero | A `Label:` line (Window only), the first image, a paragraph of links or a Buttons line (buttons), a short list (points), the `##` | A big heading, a line and a button over its image on a dark layer. Style Window: the label, a very big heading, the line, buttons, points and the image framed as a window. |
| Bento grid | Each `###` a tile, the first big | Tiles of different sizes. |
| Recipe facts | Each `Key: value` line (Serves, Servings, Yield or Makes; Prep; Cook or Bake; Total) | A strip of facts, side by side in a wide column and one under another in a narrow one. |
| Ingredients | The first list | Items to check off that cross out. |
| Method | The first numbered list | Steps with big numbers. |
| Interview | Paragraphs that start with a bold speaker (`**Sam:**`) | Chat bubbles: the first speaker plain on the left, the others in the main colour on the right. |
| Contents | `Series:` (Default is this page's own series) | A numbered list of the series' live parts, the current one marked; nothing for readers while it's empty, a note for the admin. |
| Previous and next | The page's first tag | Two large image cards: the pages before and after this one with the same first tag; nothing when there are none. |
