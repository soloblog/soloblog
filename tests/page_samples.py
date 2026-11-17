# One realistic page per kind of page - used by test_pages.py, and handy for
# seeing each in a browser (seed a dev server with them).

SAMPLES = {
    "resume": ("Alex Rivera", "Product designer who writes code.", """
I design and build small, careful software.

## Experience

Section: Resume

### Senior designer, Acme · 2021 – Present
Led the redesign of the checkout, lifting conversion by 12%.

### Designer, Globex · 2017 – 2021
Built the design system used across four products.

## Education

Section: Resume

### BA Design, Riverside University · 2013 – 2017

## Skills

Section: Skills

- Figma
- HTML & CSS
- Python
- User research
"""),
    "milestones": ("How the shop grew", "", """
From a spare room to a real shop.

## 2019 · The first sale
A friend bought a mug. It counted.

## 2021 · Moved into a studio
Finally, room for a kiln.

## 2024 · Opened the shop
Doors open six days a week.
"""),
    "wiki": ("Sourdough starter", "", """
A starter is flour and water, fed daily. See [[Baking bread]] for how it's used,
and [[Hydration|what hydration means]]. `[[not a link]]` stays as code.
"""),
    "faq": ("Questions people ask", "", """
Answers to what comes up most.

## Do you ship abroad?
Yes - everywhere except Antarctica.

## How long does delivery take?
Three to five working days.
"""),
    "portfolio": ("Things I've made", "", """
A few projects I'm proud of.

## Tide tables
![Tide chart](/uploads/tide.webp)

A tiny app for local tide times.

[Visit the site](https://example.com/tides)

## Soloblog theme
A theme for this very blog.

[See the code](https://example.com/theme)
"""),
    "now": ("Now", "", """
- Reading *The Dispossessed*
- Learning to throw pots
"""),
    "link": ("On small websites", "", """
A lovely essay on why small sites matter.
"""),
    "interview": ("A chat with Sam", "", """
Sam runs a tiny bakery.

## The conversation

Section: Interview

**Me:** How did it start?

**Sam:** With one oven and a lot of optimism.

**Me:** Any advice?

**Sam:** Start before you're ready.
"""),
    "docs": ("Getting started", "", """
Everything you need to set up.

## Install

Run the installer.

## Configure

Set your name.

### Advanced

Only if you need it.
"""),
    "recipe": ("Tomato soup", "A quick weeknight soup.", """
The easiest soup there is.

## At a glance

Section: Recipe facts

Serves: 4
Prep: 10 min
Cook: 1 h 20 min

## Ingredients

Section: Ingredients

- 1 kg tomatoes
- 1 onion
- Salt

## Method

Section: Method

1. Roast the tomatoes.
2. Blend everything.
3. Season and serve.
"""),
    "reviews": ("Books of 2026", "", """
What I read this year.

## The Dispossessed
Author: Ursula K. Le Guin
Rating: 5/5
Finished: March 2026

A quiet, brilliant book about freedom.

## Project Hail Mary
Author: Andy Weir
Rating: ★★★★

Fun from start to finish.
"""),
    "uses": ("Uses", "", """
The things I use every day.

## Desk

- **Keyboard** - a small mechanical one
- [Monitor](https://example.com/monitor) - 27 inches

## Software

- **Editor** - for everything
"""),
    "slides": ("My talk", "", """
# Hello

A talk about small software.

---

## Why small?

Because it's finishable.

---

## Thanks!
"""),
    "pricing": ("Plans", "What it costs.", """
Pick what suits you. Stop any time.

## Free

Price: US$0
Billed: never

- The whole app
- Community help

[Start free](/contact)

## Pro

Price: US$12 a month
Badge: Most popular

- Everything in Free
- Help by email

[Choose Pro](https://example.com/pro)

## Good to know

Prices include tax.
"""),
    "profile": ("Mira Castell", "Designer and weekend baker.", """
## Mira Castell

Section: Profile

![Mira at the bench](/uploads/mira.webp)

I design calm software, and fix things at the repair café on Saturdays.

Before that I spent ten years in agencies, which is where I learned to finish things.

[Work with me](/contact) · [The blog](/blog)

## Latest posts

Section: Latest posts
Count: 3
"""),
    "landing": ("Small Fixes", "A zine about mending.", """
## A zine about mending

Section: Hero
Style: Window

Label: New

![The app](/uploads/app.webp)

Thirty-two pages on fixing the things you already own.

[Order a copy](https://example.com/zine)

## What's inside

Section: Picture and text

![The cover](/uploads/zine.webp)

Toasters, trousers and a very stubborn lamp.

## Who it's for

Section: Picture and text

![A reader mending](/uploads/mending.webp)

Anyone who has ever thrown out something with one broken part.

## Get yours

Section: Call to action

Printed in small batches.

[Order a copy](https://example.com/zine)
"""),
    "services": ("Work with me", "What I do.", """
Small sites for small businesses.

## Website in a week

From: US$1,200

Designed and live in five days.

[Ask about it](/contact)

## Design day

From: US$600

A day of whatever you need.

## How it works

1. A free call.
2. A plan and a price.
3. The work.
"""),
    "testimonials": ("Kind words", "What people say.", """
## Sam Lee

Role: Owner, Corner Café

> Quick, kind, and worth every cent.

## Priya Shah

![Priya](/uploads/priya.webp)

Role: Author

> Exactly what I asked for.
"""),
    "project": ("Corner Café", "A new site for a café.", """
## At a glance

Section: Project facts

Client: Corner Café
Year: 2026
Role: Design and build

## The story

Section: Photo story

A new site for a café.

### Challenge

Nobody could find the opening hours.

### Result

Bookings up by a third.
"""),
    "events": ("Talks", "Where I'll be.", """
## Mending as design practice

Date: 12 March 2099
Place: Maple Street Library

[Slides](https://example.com/slides)

## Repair café open day

Date: 4 June 2020
Place: Town Hall
"""),
    "business": ("Maple Repair Café", "Bring your broken things.", """
We fix toasters, trousers and everything between.

## Get in touch

Section: Contact details

Phone: 02 9000 0000
Email: hello@example.com
Address: 12 Maple Street, Springfield

## Opening hours

Section: Opening hours

Monday: Closed
Saturday: 10am - 2pm

## Finding us

Two doors down from the library.
"""),
    "menu": ("Weekend menu", "What's baking.", """
## Bread

- Sourdough - a country loaf · $9
- Rye - dark and seeded · $10

## Drinks

Coffee · $4.5
Tea · $4
"""),
    "media-kit": ("Press", "For journalists.", """
## For the press

Section: Bios

### Short bio

Mira Castell is a designer based in Springfield.

### Photos

![Portrait of Mira](/uploads/portrait.webp)

## Past interviews

- [Making Podcast](https://example.com/podcast)
"""),
    "coming-soon": ("Something new", "On its way.", """
A shop for prints and zines, opening in spring.

## Hear first

Section: Sign-up
"""),
    "team": ("The café crew", "Who's who.", """
The people who keep the repair café going.

## Alex Rivera

![Alex](/uploads/alex.webp)

Role: Founder

Started it with a borrowed soldering iron.

## Sam Lee

Role: Textiles

Can fix any zip.

## Volunteer with us

Saturdays, any skill welcome.
"""),
    "shop": ("Shop", "Prints and zines.", """
A few things for sale.

## Harbour print

![The print](/uploads/print.webp)

Price: US$25

A3, matte.

[Buy it](https://buy.stripe.com/test_harbour)

## Small Fixes zine

Price: US$8
Badge: Sold out

Thirty-two pages.

## Shipping

Worldwide, within a week.
"""),
}


# Samples that are one section: each as the page its template now makes - its
# items under one Section line.
# key: (section heading, kind, its ##s that stay plain writing)
AS_SECTION = {
    "milestones": ("So far", "Milestones", ()), "faq": ("Questions", "FAQ", ()),
    "portfolio": ("Work", "Portfolio", ()), "reviews": ("Read lately", "Reviews", ()),
    "uses": ("What I use", "Uses", ()), "events": ("Talks", "Events", ()),
    "pricing": ("Plans", "Pricing", ("Good to know",)),
    "services": ("What I offer", "Services", ("How it works",)),
    "testimonials": ("What people say", "Testimonials", ()), "menu": ("On the menu", "Menu", ()),
    "team": ("The team", "Team", ("Volunteer with us",)),
    "shop": ("For sale", "Products", ("Shipping",)),
}


def _as_section(key, body):
    import re
    heading, kind, plain = AS_SECTION[key]
    parts = re.split(r"(?m)^(?=## )", body)
    items, after = [], []
    for part in parts[1:]:
        title = part.split("\n", 1)[0][3:].strip()
        if title == "How it works":
            after.append("## How it works\n\nSection: Steps\n\n" + part.split("\n", 1)[1].lstrip("\n"))
        elif title in plain:
            after.append(part)
        else:
            items.append("#" + part)
    return parts[0] + f"## {heading}\n\nSection: {kind}\n\n" + "".join(items) + "".join(after)


for _key in AS_SECTION:
    _title, _summary, _body = SAMPLES[_key]
    SAMPLES[_key] = (_title, _summary, _as_section(_key, _body))
