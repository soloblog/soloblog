"""Templates: a page ready to fill in - its sections, its words and its Post
settings. Built in below, and any post saved as a template (yours live in
the post_templates setting as JSON). A page keeps no tie to the template it
started from."""
import json
import secrets

from soloblog import sections, settings


def _s(kind, heading, body=None, given=None):
    """A section as the page has it: every Key: line written, Default unless
    `given` says what the template means."""
    return sections.markdown(kind, given, heading, body)


def _doc(*parts) -> str:
    return "\n\n".join(part.strip("\n") for part in parts) + "\n"


# key: (name, body) - a page's kind is in its sections and in SETTINGS below
BUILT_IN = {
    "recipe": ("Recipe", _doc(
        "A line or two about the dish - where it's from, why you make it.",
        _s("recipe_facts", "At a glance", "Serves: 4\nPrep: 15 min\nCook: 30 min"),
        _s("ingredients", "Ingredients", "- 2 of something\n- 1 cup of something else\n- A pinch of salt"),
        _s("method", "Method", "1. The first thing to do.\n2. What comes next.\n3. How to finish and serve it."),
        "## Notes\n\nWhat you'd change next time.")),
    "reviews": ("Book or film reviews", _doc(
        "What you've been reading or watching.",
        _s("reviews", "Read lately", """### The title

Author: Who wrote it
Rating: 4/5
Finished: March 2026

What you thought of it.

### Another title

Author: Who wrote it
Rating: 3/5
Finished: April 2026

What you thought of it."""))),
    "faq": ("FAQ", _doc(
        _s("faq", "Questions", """### The first question?

Its answer.

### The second question?

Its answer.

### The third question?

Its answer."""))),
    "resume": ("Resume / CV", _doc(
        "A line about who you are and what you do.",
        _s("resume", "Experience", """### Your role, Company · 2022 – now

What you did there, and what came of it.

### An earlier role, Company · 2019 – 2022

What you did there."""),
        _s("resume", "Education", "### Your degree, University · 2015 – 2019\n\nWhat you studied."),
        _s("skills", "Skills", "- A skill\n- Another skill\n- A tool you know well"))),
    "milestones": ("Milestones", _doc(
        _s("milestones", "So far", """### 2024 · Something that happened

What it was and why it mattered.

### 2022 · Something earlier

What it was.

### 2020 · Where it started

What it was."""))),
    "interview": ("Interview", _doc(
        "Who you talked to, and why.",
        _s("interview", "The conversation", """**You:** The first question?

**Guest:** Their answer.

**You:** The next question?

**Guest:** Their answer."""))),
    "portfolio": ("Portfolio", _doc(
        "A line about your work - what you make, and for whom.",
        _s("portfolio", "Work", """### A project

What it is, in a line. Put its picture above this line, and a link to its own page under it.

### Another project

What it is, in a line.

### A third project

What it is, in a line."""))),
    "pricing": ("Pricing", _doc(
        "A line on what you offer, and who it's for.",
        _s("pricing", "Plans", """### Starter

Price: Free

- What's included
- Something else that's included

[Get started](/contact)

### Standard

Price: US$12 a month
Badge: Most popular

- Everything in Starter
- What makes this one better

[Choose Standard](/contact)

### Premium

Price: US$39 a month

- Everything in Standard
- The extras

[Choose Premium](/contact)"""),
        "## Good to know\n\nAnything people ask before they choose - refunds, how to cancel.")),
    "profile": ("Profile / home", _doc(
        _s("profile", "Your name", """![A photo of you](/uploads/me.webp)

One line about you - what you do, and for whom.

A short bio: two or three sentences on where you've been and what you care about.

[Work with me](/contact) · [Read the blog](/blog) · [Get the newsletter](/newsletter)"""),
        _s("latest", "Latest posts", given={"Count": "3"}))),
    "landing": ("Landing page", _doc(
        _s("hero", "What it is, in a few words", """Label: New

![A picture of it](/uploads/picture.webp)

Why it's worth someone's time, in a sentence.

[Get it now](https://example.com)""", {"Style": "Window"}),
        _s("picture_and_text", "What you'll get", "![A picture of it](/uploads/picture.webp)\n\n"
                                      "The first thing it gives people, in plain words."),
        _s("picture_and_text", "Who it's for", "![Someone using it](/uploads/someone.webp)\n\n"
                                   "The people it helps most - and who it isn't for."),
        _s("numbers", "In numbers", "### 1,000+\npeople using it\n\n### 4.9 ★\ntheir average rating"),
        _s("testimonials", "What people say", "### Their name\n\nRole: What they do\n\n> What they said about it."),
        _s("pricing", "Plans", """### Basic

Price: US$10

- What's included

[Choose Basic](https://example.com)

### Pro

Price: US$20
Badge: Most popular

- Everything in Basic
- And more

[Choose Pro](https://example.com)"""),
        _s("faq", "Questions", "### A question people ask?\nIts answer, in a line or two."),
        _s("cta", "Ready when you are", "One line to close.\n\n[Get it now](https://example.com)"))),
    "services": ("Services", _doc(
        "A line on what you do, and who you do it for.",
        _s("services", "What I offer", """### Website in a week

From: US$1,200

A small site, designed and live in five working days.

[Ask about it](/contact)

### A day of design help

From: US$600

A day of whatever you need - a logo, a page, a second opinion.

[Book a day](/contact)""", {"Width": "Column"}),
        _s("steps", "How it works", """1. We talk for half an hour - free.
2. I send a plan and a price.
3. I do the work, and you see it as it goes."""))),
    "testimonials": ("Testimonials", _doc(
        "What people say about working with you.",
        _s("testimonials", "What people say", """### Sam Lee

Role: Owner, Corner Café

> Quick, kind, and the site paid for itself in a month.

### Priya Shah

Role: Author

> Exactly what I asked for, and two things I didn't know I needed.""", {"Width": "Column"}))),
    "project": ("Project", _doc(
        _s("project_facts", "At a glance", "Client: Who it was for\nYear: 2026\nRole: What you did"),
        _s("photo_story", "The story", """One or two lines on what the project was - shown large, at the top.

### Challenge

What wasn't working, and why it mattered.

![The before](/uploads/before.webp)

A short line about this picture sits beside it.

### Approach

What you tried, what you learned, and what you chose.

![A detail](/uploads/detail-1.webp)
![Another detail](/uploads/detail-2.webp)

> A line from the client, shown big.
>
> — Their name, their role

### Result

What changed - in numbers if you have them.

![The after](/uploads/after.webp)"""),
        _s("previous_next", "Keep reading"))),
    "events": ("Talks and events", _doc(
        "Where you'll be speaking, teaching or reading.",
        _s("events", "Talks and events", """### Talk title

Date: 12 March 2026
Place: A venue, a city

A line on what it's about.

[Slides](https://example.com) · [Video](https://example.com)

### Workshop title

Date: 4 June 2026
Place: Online

What people will make or learn."""))),
    "business": ("Small business", _doc(
        "A line about the place - what you make, sell or fix.",
        _s("details", "Get in touch", "Phone: 02 9000 0000\nEmail: hello@example.com\nAddress: 12 Maple Street, Springfield"),
        _s("hours", "Opening hours", """Monday: Closed
Tuesday - Friday: 9am - 5pm
Saturday: 9am - 1pm
Sunday: Closed"""),
        "## Finding us\n\nTwo doors down from the library. Parking out the back.")),
    "menu": ("Menu", _doc(
        "What's on, and when.",
        _s("menu", "On the menu", """### Breakfast

- Sourdough toast - butter and jam · $8
- Porridge - oats, apple, cinnamon · $11

### Lunch

- Soup of the day - with bread · $14
- Toastie - cheese, ham or both · $12

### Drinks

- Coffee · $4.5
- Tea · $4""", {"Width": "Column"}))),
    "media-kit": ("Media kit / press", _doc(
        "Everything a journalist or a podcast host needs, in one place.",
        _s("bios", "For the press", """### Short bio

[Your name] is a [what you do] based in [where].

### Long bio

A paragraph or two: where you started, what you do now, what you're known for.

### Photos

![A portrait](/uploads/portrait.webp)"""),
        "## Past interviews\n\n- [A podcast](https://example.com) - 2026\n- [A newspaper](https://example.com) - 2025",
        "## Get in touch\n\nhello@example.com")),
    "coming-soon": ("Coming soon", _doc(
        "Something new is on its way - a line on what it is, and when.",
        _s("signup", "Hear first", "Leave your email and you'll hear first."))),
    "team": ("Team", _doc(
        "The people behind it.",
        _s("team", "The team", """### Alex Rivera

![Alex](/uploads/alex.webp)

Role: Founder

What Alex does, in a sentence or two.

### Sam Lee

![Sam](/uploads/sam.webp)

Role: Workshop lead

What Sam does, in a sentence or two."""))),
    "shop": ("Shop", _doc(
        "A few things for sale. Each button goes straight to checkout.",
        _s("products", "For sale", """### A print

![The print](/uploads/print.webp)

Price: US$25

A3, on heavy matte paper.

[Buy it](https://buy.stripe.com/example)

### A zine

![The zine](/uploads/zine.webp)

Price: US$8
Badge: Sold out

Thirty-two pages, hand-stapled.

[Join the waitlist](/contact)"""),
        "## Shipping\n\nWorldwide, in a stiff envelope, within a week.")),
    "journal": ("Journal / weekly notes", """A line on how the week went.

## What happened

- Something that happened

## What I learned

- Something you learned

## Next week

- [ ] Something to do
- [ ] Something else to do
"""),
    "howto": ("How-to", _doc(
        "What this helps you do, and what you'll need before you start.",
        """## What you'll need

- A thing you'll need
- Another thing""",
        _s("steps", "Steps", """1. The first step.
2. The next step.
3. The last step, and how to tell it worked."""),
        """## If something goes wrong

The usual problem, and what fixes it.""")),
    "now": ("Now page", """What you're up to these days - a [now page](https://nownownow.com/about) \
says what you're focused on at the moment.

## Working on

What you're building.

## Reading

A book or two.

## Learning

Something new.
"""),
    "privacy": ("Privacy policy", """_A starting point: change it to match what your site uses, check it against \
the laws where you and your readers live, and delete this line._

Last updated: [the date]

This site is run by [your name]. This page says what it collects about you, why, and what you can do about it.

## What this site collects

- **Comments:** the name, email address and website you give. Your email address isn't shown.
- **Newsletter:** your email address, to send you new posts. Every email has a link to stop them.
- **Membership:** your email address and, if you pay, your payment - handled by Stripe. This site never sees \
your card number.
- **Contact form:** your name, email address and message.
- **Visits:** [the analytics service this site uses, or "nothing - this site doesn't track visitors"].

Remove the lines for anything your site doesn't use.

## Cookies

[Which ones, and what for - signing in as a member, remembering your colours, analytics.]

## Who else sees it

[The services that handle it - your host, your email service, Stripe, your analytics.] Nothing is sold.

## How long it's kept

[As long as you're a subscriber or member, or until you ask for it to be removed.]

## Your choices

You can ask to see, correct or delete what this site has about you: [your email address, or a link to the \
contact page]. Members can download their data, or delete their account, from their account page.

## Changes

When this page changes, the date at the top changes too.
"""),
    "terms": ("Terms", """_A starting point: change it to fit what you offer, check it against the laws \
where you live, and delete this line._

Last updated: [the date]

These terms cover using this site and, if you join, being a member.

## Comments

Your comments are yours, but posting one lets this site show it. Comments that are abusive, spam or against \
the law may be removed.

## What's here

The posts, pictures and other work on this site are [your name]'s unless it says otherwise. [How people may \
share it - for example, "Quote a few lines with a link back."]

## Membership

- **Free members** can read members-only posts.
- **Paid members** pay [monthly or yearly] through Stripe, until they cancel. Cancel any time under **Manage \
billing** on your account page; you keep access until the end of the time you've paid for.
- **Refunds:** [your refund policy].

Remove this part if your site has no members.

## No guarantees

The site is offered as it is. [Your name] isn't responsible for losses from using it, or from the sites it \
links to.

## Changes and questions

When these terms change, the date at the top changes too. Questions: [your email address, or a link to the \
contact page].
"""),
    "wiki": ("Wiki / notes", """A short note on one idea. Link related notes with [[Their title]] - a note
that doesn't exist yet shows red, ready to write.

## What it is

A few lines, in your own words.

## Why it matters

Where it comes up, and what it connects to.

## See also

- [[Another note]]
- [[A related idea]]
"""),
    "photo-story": ("Photo story", _doc(
        _s("photo_story", "The story", """A short introduction - where you were, and what you went looking for.

![What the first photo shows](/uploads/photo.webp)

A line or two about this moment.

![What the second photo shows](/uploads/photo.webp)

What happened next.

![What the third photo shows](/uploads/photo.webp)

How it ended, and what stayed with you."""),
        _s("previous_next", "Keep reading"))),
    "link": ("Link post", """Why this is worth reading, in a sentence or two. Put the page's address in
Post settings > Page > More > Link to - the title points there.

> A line from it that stayed with you.

What you'd add, or where you see it differently.
"""),
    "docs": ("Docs / guide", _doc(
        "What this part covers, and who it's for.",
        """## Before you start

- Something you'll need
- Something to have done first""",
        _s("steps", "Steps", """1. The first step.
2. The next step.
3. The last step."""),
        """## Check it worked

What you should see now.""",
        """## Next

What to read next - the following part of the series.""")),
    "uses": ("Uses", _doc(
        "The things I use, and what for.",
        _s("uses", "What I use", """### Desk

- **A laptop** - what it's for
- **A keyboard** - why this one

### Software

- [An app](https://example.com) - what you use it for
- **Another app** - what it's for

### Carry

- **A bag** - what's in it"""))),
    "slides": ("Slides", """## The talk's title

Your name · where and when

---

## The first point

- What to say
- Why it matters

---

## The second point

A picture, a quote or a few words.

---

## Thank you

Where people can find you.
"""),
}


# pages people look for at the foot of a site - they start as footer pages
FOOTER_PAGES = {"privacy", "terms"}


def saved() -> list:
    """Your own templates: [{"id", "name", "tags", "body", ...}]."""
    try:
        return json.loads(settings.get("post_templates") or "[]")
    except ValueError:
        return []


# What a template can set of a page's frame and kind - never the site's. A
# value of "" or False is the default, and every template has every key.
NO_SETTINGS = {"title_style": "", "page_width": "", "cover_width": "", "toc_style": "", "heading_fold": "",
               "section_space": "", "section_motion": "", "sides": "", "extras": "", "slides": False, "in_wiki": False,
               "remind_update": False, "link_url": ""}

# what each built-in template sets, besides what the rest of NO_SETTINGS says
SETTINGS = {
    "recipe": {"toc_style": "off"},
    "resume": {"toc_style": "off"},
    "interview": {"toc_style": "off"},
    "portfolio": {"page_width": "wide", "toc_style": "off"},
    "pricing": {"page_width": "wide", "toc_style": "off"},
    "profile": {"title_style": "hidden", "toc_style": "off"},
    "landing": {"title_style": "hidden", "page_width": "wide", "toc_style": "off", "section_space": "large"},
    "services": {"toc_style": "off"},
    "testimonials": {"toc_style": "off"},
    "project": {"page_width": "wide", "cover_width": "screen", "toc_style": "off"},
    "business": {"toc_style": "off"},
    "menu": {"toc_style": "off"},
    "media-kit": {"toc_style": "off"},
    "coming-soon": {"title_style": "centre", "toc_style": "off"},
    "team": {"page_width": "wide", "toc_style": "off"},
    "shop": {"page_width": "wide", "toc_style": "off"},
    "howto": {"toc_style": "top"},
    "now": {"remind_update": True, "toc_style": "off"},
    "wiki": {"in_wiki": True},
    "photo-story": {"page_width": "wide", "cover_width": "screen", "toc_style": "off"},
    "docs": {"toc_style": "side"},
    "slides": {"slides": True},
}
# the title, byline, tags and the like-and-listen row of a page that opens with its own words
_OPENING = ("byline", "tags", "listen", "reactions")
# Show, as changes to what the site shows: (turned on, turned off), or "none"
SHOWS = {
    "recipe": (("print",), ()),
    "resume": (("print",), (*_OPENING, "share", "series", "related", "author")),
    "portfolio": ((), (*_OPENING, "related", "series", "sides")),
    "pricing": ((), (*_OPENING, "related", "series", "sides")),
    "profile": ((), (*_OPENING, "related", "author", "series", "sides")),
    "landing": ((), (*_OPENING, "related", "series", "sides")),
    "services": ((), (*_OPENING, "related", "series", "sides")),
    "testimonials": ((), (*_OPENING, "related", "series", "sides")),
    "menu": ((), (*_OPENING, "related", "series", "sides")),
    "team": ((), (*_OPENING, "related", "series", "sides")),
    "shop": ((), (*_OPENING, "related", "series", "sides")),
    "coming-soon": "none",
    "now": ((), ("related", "series")),
    "docs": (("series",), ()),
}


def _extras(key) -> str:
    """A built-in template's Show, as a page stores it: the site's own
    choice with the template's changes, "" while that's the site's own."""
    from soloblog import pages
    change = SHOWS.get(key)
    if change == "none":
        return "none"
    if not change:
        return ""
    on, off = change
    return pages.extras_value((pages.default_extras(False) | set(on)) - set(off), key in FOOTER_PAGES)


def get(key: str):
    """{name, body, tags, summary, cover, pin, settings} for a built-in
    key or "mine-<id>". settings is every key of NO_SETTINGS."""
    if key in BUILT_IN:
        name, body = BUILT_IN[key]
        chosen = {**NO_SETTINGS, **SETTINGS.get(key, {}), "extras": _extras(key)}
        found = {"name": name, "tags": "", "body": body, "summary": "", "cover": "",
                 "pin": "footer" if key in FOOTER_PAGES else ""}
    else:
        saved_one = next((t for t in saved() if key == f"mine-{t['id']}"), None)
        if not saved_one:
            return None
        chosen = clean_settings(saved_one.get("settings"))
        found = {"name": saved_one["name"],
                 "tags": saved_one.get("tags", ""), "body": saved_one["body"], "summary": saved_one.get("summary", ""),
                 "cover": saved_one.get("cover", ""), "pin": ""}
    return {**found, "settings": chosen}


def clean_settings(raw) -> dict:
    """Every setting in NO_SETTINGS, each cleaned as a post's own is -
    whatever was typed, edited by hand or imported."""
    from soloblog import pages, posts
    raw = raw if isinstance(raw, dict) else {}
    return {"title_style": posts.clean_title_style(raw.get("title_style")),
            "page_width": posts.clean_page_width(raw.get("page_width")),
            "cover_width": posts.clean_choice(raw.get("cover_width"), "COVER_STYLES"),
            "toc_style": posts.clean_choice(raw.get("toc_style"), "TOC_STYLES"),
            "heading_fold": posts.clean_choice(raw.get("heading_fold"), "FOLD_STYLES"),
            "section_space": posts.clean_choice(raw.get("section_space"), "SPACINGS"),
            "section_motion": posts.clean_choice(raw.get("section_motion"), "SECTION_MOTIONS"),
            "sides": posts.clean_sides(raw.get("sides")), "extras": pages.clean_extras(raw.get("extras")),
            "slides": bool(posts.clean_flag(raw.get("slides"))), "in_wiki": bool(posts.clean_flag(raw.get("in_wiki"))),
            "remind_update": bool(posts.clean_flag(raw.get("remind_update"))),
            "link_url": posts.clean_link(raw.get("link_url"))}


def settings_of(template) -> dict:
    """A template's settings - all of NO_SETTINGS, cleaned."""
    return clean_settings(template.get("settings"))


def clean_start(key) -> str:
    """A template's key, or "" (Blank) when it isn't one - a stale or typed-in value."""
    return key if isinstance(key, str) and get(key) else ""


def start_key() -> str:
    """The template a new post starts from (Settings > Editor > New posts
    start from) - Blank when it's gone, as a deleted custom one is."""
    return clean_start(settings.get("new_post_start"))


RECENT = 3


def listed() -> list:
    """(key, name, group) for every template: your custom ones,
    then the built-in ones Soloblog comes with."""
    mine = [(f"mine-{t['id']}", t["name"], "Custom") for t in saved()]
    return mine + [(k, v[0], "Built-in") for k, v in BUILT_IN.items()]


def choices() -> list:
    """(key, name, group) for the template picker: the last few you
    started from, then the rest as listed."""
    every = listed()
    keys = recent()
    first = [(k, name, "Recent") for key in keys for k, name, _ in every if k == key]
    return first + [c for c in every if c[0] not in keys]


def recent() -> list:
    """The keys of the templates last started from, newest first - those that are still there."""
    keys = [k for k in (settings.get("template_recent") or "").split(",") if k]
    return [k for k in keys if get(k)][:RECENT]


def used(key: str):
    """A new post started from this one: it's first under Recent."""
    if get(key):
        settings.set_many({"template_recent": ",".join([key] + [k for k in recent() if k != key][:RECENT - 1])})


def save(name: str, tags: str, body: str, summary: str = "", cover: str = "", page: dict = None) -> str:
    """Adds one of yours - a template with the same name is replaced. page:
    its Post settings (NO_SETTINGS), cleaned here."""
    name = " ".join(name.split())[:80]
    items = [t for t in saved() if t["name"].lower() != name.lower()]
    items.insert(0, {"id": secrets.token_hex(4), "name": name,
                     "tags": tags.strip()[:300], "body": body[:100_000], "summary": summary.strip()[:500],
                     "cover": cover.strip()[:500], "settings": clean_settings(page)})
    settings.set_many({"post_templates": json.dumps(items)})
    return items[0]["id"]


def delete(template_id: str):
    settings.set_many({"post_templates": json.dumps([t for t in saved() if t["id"] != template_id])})
