"""The sample blog: Mira Castell's site, used by the live demo (DEMO_MODE)
and for the screenshots (tools/demo.py). Every
template, feature and a believable year of writing, with openly licensed
photos - CC0, public domain or CC BY, credited - downloaded once into a
cache and reused on every rebuild."""
from pathlib import Path
import logging
import io
import json
import os
import random
import re
import shutil
import threading
import time
import urllib.request
from datetime import timedelta
from soloblog.tz import utcnow

from soloblog import config
from soloblog import netguard

log = logging.getLogger(__name__)

UA = {"User-Agent": "SoloblogDemo/1.0 (https://github.com/soloblog/soloblog)"}

# key: (credit, licence, alt text) - download addresses and credit links are in demo_photos.json
PHOTOS = {
    "hero": ("Kylli Kittus", "Unsplash", "Forested hills and a bridge over still water"),
    "loaf": ("Debbie Widjaja", "Unsplash", "A round loaf of bread on a wooden board"),
    "loaf2": ("Jens Meyers", "Unsplash", "A loaf of bread cooling on a wire rack"),
    "starter": ("victoria.", "Unsplash", "A bowl of flour next to a wooden spoon"),
    "focaccia": ("Diego Arenas de Rodrigo", "Unsplash", "Focaccia with rosemary on a wooden board"),
    "crumb": ("Diego Arenas de Rodrigo", "Unsplash", "Freshly baked focaccia with herbs"),
    "bike_blue": ("Teo Zac", "Unsplash", "A bicycle leaning against a green wall"),
    "bike_red": ("Zhen Yao", "Unsplash", "A red bicycle with a wicker basket"),
    "bike_lamp": ("Indra Projects", "Unsplash", "The headlamp of an old bicycle, on its handlebars"),
    "workshop": ("Bohdan Kadun", "Unsplash", "A bicycle being looked over in a garage workshop"),
    "tools": ("Anton Savinov", "Unsplash", "Tools hanging on a workshop wall"),
    "forest_road": ("Leon Fellingham", "Unsplash", "A sunlit road under a tunnel of green trees"),
    "tug_fog": ("Vladislav Anchuk", "Unsplash", "A tugboat at the quay on a foggy day"),
    "old_lake": ("Shutter Speed", "Unsplash", "A pier on a misty lake"),
    "pier_fog": ("Aaron Burden", "Unsplash", "An empty wooden dock over calm water"),
    "heron": ("Enzo Gannerie", "Unsplash", "A white heron at the edge of a shallow river"),
    "heron2": ("Joshua J. Cotten", "Unsplash", "A grey heron in the water"),
    "fishing_boat": ("Zoltan Tasi", "Unsplash", "A small wooden boat on still water"),
    "bakery": ("Elisha Terada", "Unsplash", "A bakery full of fresh bread and pastries"),
    "kneading": ("Tatev Ayvazyan", "Unsplash", "Hands kneading dough next to a white bowl"),
    "dough": ("Nadya Spetnitskaya", "Unsplash", "Kneading dough beside a wooden rolling pin"),
    "city_bike": ("Gio L", "Unsplash", "A bright yellow bicycle with plants in its basket"),
    "fjord": ("Mark Twisselmann", "Unsplash", "A fjord between green mountains"),
    "fjord_farm": ("Ingrid Martinussen", "Unsplash", "Colourful wooden wharf houses along a river under a blue sky"),
    "oslo_sunset": ("Julian Zwengel", "Unsplash", "The sun setting over a harbour full of boats"),
    "yellow_boat": ("Georg Eiermann", "Unsplash", "A yellow boat out on the sea"),
    "desk": ("Clay Banks", "Unsplash", "A room with a desk and a bookshelf"),
    "platter": ("Nick", "Unsplash", "The inside of a hard disk drive"),
    "drive": ("Vincent Botta", "Unsplash", "A hard drive on a desk"),
    "notebook": ("Alex Padurariu", "Unsplash", "A croissant on an open book beside a mug"),
    "notebook_dark": ("Kelly Sikkema", "Unsplash", "A notepad, a pen, a camera and coffee on a wooden table"),
    "library": ("Drahomír Hugo Posteby-Mach", "Unsplash", "A library with tall windows, bookshelves and red chairs"),
    "books": ("Robert Anasch", "Unsplash", "Books in every colour"),
    "camera": ("Margo Evardson", "Unsplash", "A twin-lens camera on a dark, shiny surface"),
    "plant": ("Mahadi Mugdho", "Unsplash", "A spider plant with green and white striped leaves"),
    "coffee": ("Anna Wohnoutka", "Unsplash", "A cup of coffee and a pastry on a table"),
}


def _load_sources():
    """Download addresses and credit links, kept beside this file."""
    path = os.path.join(os.path.dirname(__file__), "demo_photos.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _wikimedia_sized(url, width=2560):
    """Wikimedia asks for its standard thumbnail sizes, not originals."""
    prefix = "https://upload.wikimedia.org/wikipedia/commons/"
    if not url.startswith(prefix):
        return url
    rest = url[len(prefix):].split("?", 1)[0]
    return f"{prefix}thumb/{rest}/{width}px-{rest.rsplit('/', 1)[1]}"


def _photo_bytes(key, url, cache):
    if os.environ.get("DEMO_OFFLINE"):
        # the tests: a plain image, nothing downloaded
        from PIL import Image
        out = io.BytesIO()
        Image.new("RGB", (640, 400), (90 + len(key) * 5, 120, 150)).save(out, "JPEG")
        return out.getvalue()
    # named by where it comes from too: a photo swapped for another is
    # fetched again, not the old one kept from a cache that outlives deploys
    import hashlib
    path = os.path.join(cache, f"{key}-{hashlib.sha1(url.encode(), usedforsecurity=False).hexdigest()[:10]}.jpg")
    if os.path.exists(path):
        return open(path, "rb").read()
    for old in os.listdir(cache) if os.path.isdir(cache) else ():
        if old == f"{key}.jpg" or (old.startswith(f"{key}-") and old.endswith(".jpg")):
            os.remove(os.path.join(cache, old))
    raw = netguard.open_url(urllib.request.Request(_wikimedia_sized(url), headers=UA), timeout=60).read()  # noqa: S310 - opened through netguard
    os.makedirs(cache, exist_ok=True)
    with open(path, "wb") as f:
        f.write(raw)
    time.sleep(0.5)
    return raw


def _add_photos(cache):
    """Every photo into the media library, named and credited. Returns
    {key: /uploads/url}."""
    from soloblog import images
    sources = _load_sources()
    urls = {}
    for key, (credit, _licence, alt) in PHOTOS.items():
        src = sources[key]
        try:
            raw = _photo_bytes(key, src["url"], cache)
        except Exception as e:
            log.warning("couldn't get the %s photo: %s", key, e)
            continue
        url = images.save_upload(raw, alt[:40])
        filename = url.rsplit("/", 1)[1]
        # from Unsplash: "Photo by Name on Unsplash", linked as its licence asks
        images.set_meta(filename, alt, "", credit, src.get("page") or "",
                        "unsplash" if src.get("source") == "unsplash" else "")
        urls[key] = url
    return urls


def _frame(f) -> dict:
    """A page's Post settings: those of the template it's made from (the
    same ones a person gets), then the page's own."""
    from soloblog import post_templates
    got = post_templates.settings_of(post_templates.get(f["template"])) if f.get("template") else {}
    got.pop("link_url", None)
    got.update({k: f[k] for k in ("title_style", "slides", "in_wiki", "remind_update", "sides") if k in f})
    return got


def _when(days_ago, hour=9):
    return (utcnow() - timedelta(days=days_ago)).replace(hour=hour, minute=random.randint(0, 59),  # noqa: S311 - sample numbers, not security
                                                                  second=0, microsecond=0).isoformat()


def _day(days_from_now):
    """"14 November 2026" - an event date that's always ahead of (or behind)
    the demo, whenever it's built."""
    d = utcnow() + timedelta(days=days_from_now)
    return f"{d.day} {d.strftime('%B %Y')}"


def _notes():
    """Mira's notes: a small wiki (In the wiki - off the blog roll),
    found from Notes in the menu (the wiki's own row) - /wiki, its front
    page, which starts with How these notes work."""
    note = dict(template="wiki", in_wiki=True)
    return [
        ("notes-start-here", "How these notes work", "notes",
         "A notebook that links to itself - start here.", """
These are my working notes: short pages, one idea each, that link to
each other. They're never finished. A blog post is something I've
thought about; a note is something I'm still thinking about.

## Where to start

- Bread: [[Hydration]] is the number everything else depends on, then
  [[Levain]], [[Bulk fermentation]] and [[Oven spring]].
- Bicycles: [[Reynolds 531]], the steel the Peugeot is made of, and
  [[Chain wear]], the cheapest thing to check.

Every note lists what it links to and what links back to it, at the
foot of the page. Follow those and you'll find the rest.
""", dict(note, days=2, views=880)),
        ("notes-hydration", "Hydration", "notes, bread",
         "Water over flour, as a percentage - the number every recipe argues about.", """
How much water a dough has, as a share of its flour: 700 g of water to
1 kg of flour is 70%.

- **Below 65%** - a stiff dough, easy to shape, a tight crumb. Sandwich
  bread.
- **70-75%** - where most of my loaves live. Open, but still manageable.
- **Over 80%** - glorious holes and a dough like a puddle. Only with
  strong flour and good [[Bulk fermentation]].

Whole grain flour drinks more, so the same loaf with half wholemeal
wants about 5% more water. The [[Levain]] counts too: it's half water.

An [[Autolyse]] makes a wet dough much easier to handle.
""", dict(note, days=3, views=1420)),
        ("notes-levain", "Levain", "notes, bread",
         "The bit of starter that goes into the dough.", """
A levain is a small batch of starter, fed the night before, that goes
into the dough. The starter itself (mine is in
[[My sourdough starter has outlived three houseplants and a toaster|this post]])
stays in the fridge.

It's ready when it has doubled and a spoonful floats in water. Too early
and the loaf is slow; too late and it's sour and slack.

It's half flour and half water, so it counts towards the [[Hydration]].
After it goes in comes [[Bulk fermentation]].
""", dict(note, days=9, views=760)),
        ("notes-bulk-fermentation", "Bulk fermentation", "notes, bread",
         "The long first rise, where the flavour comes from.", """
The first rise, all the dough in one bowl, from mixing the [[Levain]] in
until shaping. Four to six hours in a warm kitchen; longer in winter.

Done when the dough has grown by about half, is domed and wobbly, and
has bubbles at the sides. Watch the dough, not the clock.

Under-fermented dough gives a tight, gummy crumb and little
[[Oven spring]]; over-fermented spreads flat, and [[Scoring]] it won't
help.
""", dict(note, days=5, views=990)),
        ("notes-autolyse", "Autolyse", "notes, bread",
         "Flour and water, left alone for an hour.", """
Mixing just the flour and water and leaving them for 30-60 minutes
before the [[Levain]] and salt go in. The flour soaks up the water and
the gluten starts to form on its own, so there's less kneading.

Worth it at any [[Hydration]] over 70%.
""", dict(note, days=30, views=310)),
        ("notes-oven-spring", "Oven spring", "notes, bread",
         "Why a loaf rises in the oven, and why mine sometimes doesn't.", """
Oven spring is the last burst of rising a loaf does in the first ten
minutes of baking, before the crust sets and says no more.

## What helps

- **Steam.** A wet crust stretches; a dry one sets early and the loaf
  gives up. A tray of boiling water on the oven floor does it.
- **A hot start.** The stone, the tin, the oven - all properly hot, for
  longer than seems reasonable.
- **Good [[Bulk fermentation]].** Under-proved dough has nothing left to
  give.
- **[[Scoring]].** It tells the loaf where to open.

## What doesn't

Opening the oven door to look. I know. I do it every time.

## Related

The quickest loaf I make gets most of its rise from the yeast rather
than the oven - [[Emergency focaccia, for people who forgot to plan dinner|the emergency focaccia]]
forgives everything on this list.
""", dict(note, days=21, views=1310)),
        ("notes-scoring", "Scoring", "notes, bread",
         "The cut on top of a loaf, and why it isn't decoration.", """
A quick, shallow cut with a razor just before the loaf goes in. It's
where the loaf opens during [[Oven spring]] - without it, it bursts
wherever it likes.

- One long cut at a low angle gives the "ear", the crunchy ridge.
- A cross gives an even, round rise.
- Cut fast. Hesitating drags the dough.

Badly under-proved dough tears whatever you do - see
[[Bulk fermentation]].
""", dict(note, days=14, views=540)),
        ("notes-reynolds-531", "Reynolds 531", "notes, bikes",
         "The steel tubing the Peugeot is made of.", """
A steel tubing made in Birmingham from 1935, and the frame of most good
racing bikes for fifty years - the Peugeot's included (the story of
buying it is
[[I bought a 1983 racing bike from a man named Lars|here]]).

- Light for steel, and springy - it soaks up a rough road.
- It can be brazed, bent back and repaired, where aluminium can't.
- A sticker on the seat tube says which tubes are 531. Keep it.

It does rust from the inside, so a frame that's been stored damp wants
a look down the seat tube. The other thing to check first is
[[Chain wear]].
""", dict(note, days=40, views=670)),
        ("notes-chain-wear", "Chain wear", "notes, bikes",
         "Why a stretched chain is the most expensive cheap part.", """
A chain's pins wear, and it gets longer - "stretch", though nothing
actually stretches. A long chain grinds down the sprockets and
chainrings, which cost far more to replace.

Check it with a ruler: 12 links should measure 12 inches. At 12 1/16 it's
time for a new chain; at 12 1/8 the sprockets have probably gone too.

The Peugeot's was at 12 1/4. See [[Reynolds 531]] for what I found under
it, and [[Gear inches, and other numbers I now care about|my numbers page]]
for the rest.
""", dict(note, days=12, views=450)),
    ]


def _views(current=""):
    """The line on Mira's Work page, and on each copy of it, going to her
    projects in every arrangement - the one shown in bold."""
    from soloblog import pages
    names = [(key, label.split(" — ")[0]) for key, label in pages.PORTFOLIO_STYLES.items()]
    return "See it as: " + " · ".join(f"**{name}**" if key == current else f"[{name}](/post/projects-{key})"
                                      for key, name in names)


def posts_and_pages(p):
    """(slug, title, tags, summary, body, fields) - p maps photo keys to URLs."""
    img = lambda k, alt="": f"![{alt or PHOTOS[k][2]}]({p.get(k, '')})"  # noqa: E731
    gallery = lambda *ks, style="": "```gallery" + (f" {style}" if style else "") + "\n" + "\n".join(  # noqa: E731
        p[k] for k in ks if k in p) + "\n```"
    return [
        # ---- pages
        ("about", "About", "", "Who writes this, and why it's mostly about bread and bicycles.", f"""
Hi, I'm Mira. I design software for a living and, in my spare time, I
try to finish things. This site is where I write about the things I
finish, the things I don't, and the long, flour-dusted middle.

{img("camera", "Looking down into the viewfinder of my twin-lens camera")}

## What you'll find here

- **Bread** - mostly sourdough, occasionally a focaccia made in a panic.
- **Bicycles** - one in particular: a 1983 Peugeot I'm bringing back
  from the dead, one bolt at a time.
- **Fog** - I live by the harbour and photograph it far more than is
  reasonable.
- **Finishing things** - the small tricks that get a project from 90%
  to done.

## So far

Section: Numbers

### 12
years designing software

### 3
houseplants outlived by a sourdough starter

### 1983
the year my bicycle was built

## Say hello

Section: Contact form

I read everything, and I reply to most things before the bread comes
out of the oven.
""", dict(pinned=True, pin_location="header", cover="loaf2", days=400, comments=False)),
        ("cv", "CV", "", "Twelve years of designing software people actually use.", """
Product designer. I make complicated things feel obvious, and I'm
suspicious of any screen with more than one primary button.

## Experience

Section: Resume

### Lead product designer, Tidewater Studio · 2021 – now

Design lead for a booking app used by 400 small harbours. Cut the
check-in flow from nine screens to three; fishermen stopped phoning us.

### Product designer, Northlight · 2017 – 2021

Designed the offline mode for a field-survey app used in places with
more sheep than signal.

### Designer, Kaffe & Kode · 2014 – 2017

Everything from logos to login screens at a six-person agency.

## Education

Section: Resume

### BA Interaction Design, Harbourside School of Design · 2010 – 2014

## Skills

Section: Skills

- Product design
- Prototyping
- Research
- Figma
- HTML and CSS
- Norwegian (enthusiastic)
""", dict(pinned=True, pin_location="header", parent="projects", template="resume", days=398)),
        ("now", "Now", "", "What I'm up to this month.", """
What I'm focused on at the moment, in the spirit of
[nownownow.com](https://nownownow.com/about).

## Baking

A rye starter called Gunnar, who is younger and more energetic than my
wheat starter and knows it.

## Riding

The Peugeot is on the road. I'm working up to the 60 km coast loop
before the autumn storms arrive.

## Reading

*Four Thousand Weeks*, slowly, which I suspect is the point.

## Learning

Norwegian verbs. Specifically, why *å få* means six different things.
""", dict(pinned=True, pin_location="header", parent="about", template="now", remind_update=True, days=6)),
        ("projects", "Work", "", "Things I've made, mended or talked myself into.", f"""
Things I've made in the evenings, most of them on purpose - and one
or two for people who paid me in more than jam.

## Projects

Section: Portfolio

{_views()}

### The Peugeot

{img("bike_blue")}

A 1983 steel racing bike, restored over one long winter.

[Read the series](/series/the-peugeot)

### Corner Café

{img("coffee")}

A booking page that finally makes sense.

[See the project](/corner-cafe)

### Sunday Loaves

{img("loaf2")}

A tiny bread club: eight neighbours, one loaf each.

[How it started](/post/my-sourdough-starter-has-outlived-three-houseplants)

### Fog Almanac

{img("old_lake")}

Fifty foggy mornings on the harbour, as a photo zine.

[See some of it](/post/fog-ferries-and-one-extremely-patient-heron)

### Small Fixes

{img("tools")}

A zine about mending the things you own.

[Read it](/small-fixes)

### Verb Wheel

{img("notebook_dark")}

A paper wheel for Norwegian verb forms.

[The long story](/post/ten-years-of-learning-norwegian-badly)
""", dict(pinned=True, pin_location="header", template="landing", title_style="", days=120)),
        ("bread-classes", "Bread classes", "", "Small sourdough classes in my kitchen.", """
Small sourdough classes in my kitchen, four people at a time. Flour,
aprons and a jar of starter to take home are included.

## Classes

Section: Pricing

### Taster

Price: Free

- Watch a loaf being shaped and baked
- Questions answered, however basic
- A slice, still warm

[Join the list](/contact)

### Weekend class

Price: €45 per person
Badge: Most popular

- Two mornings: mix on Saturday, bake on Sunday
- Your own loaf to take home
- A jar of my starter, Gerald

[Book a place](/contact)

### Private lesson

Price: €90 for up to two

- Your kitchen or mine
- Rye, baguettes, or rescuing a flat loaf - your choice
- Follow-up questions by email

[Ask about dates](/contact)

## Good to know

Classes run from October to May. Cancel up to two days before for a
full refund.
""", dict(pinned=True, pin_location="header", parent="shop", template="landing", title_style="", days=40)),
        # ---- the page-style templates, in Mira's own life. The menu by what a
        # visitor's after (build): her work, her shop, the repair café, her
        # notes, about her, the tour and getting in touch - every other
        # page is under one of them
        ("in-short", "In short", "", "Mira in a minute.", f"""
## Mira

Section: Profile

{img("kneading", "My floury hands, which is how most people know me")}

I design calm software, and fix things at the repair café on Saturdays.

Twelve years of product design taught me most things are nearly done
for a very long time. This site is where I write about finishing them.

[Work with me](/work-with-me) · [Read the blog](/) · [Get new posts by email](/newsletter)

## Lately

Section: Latest posts
Count: 3
""", dict(pinned=True, pin_location="header", parent="about", template="profile", days=390)),
        ("work-with-me", "Work with me", "", "Design for small teams and one-person businesses.", """
I help small teams and one-person businesses make software that's calm to use.

## What I offer

Section: Services
Width: Column

### A design review

From: €600

Two days with your product, then a call and a written list of what to
change first - and what to leave alone.

[Ask about dates](/contact)

### A product, start to finish

From: €4,000

From the first sketch to the screens your developer builds from, over
four to six weeks.

[Tell me about it](/contact)

## How it works

Section: Steps

1. A free half-hour call about what you're making.
2. A short plan with a fixed price.
3. The work, shared as it goes - no big reveal at the end.
""", dict(pinned=True, pin_location="header", parent="projects", template="landing", title_style="", days=120)),
        ("kind-words", "Kind words", "", "What people say about working with me.", """
## What people say

Section: Testimonials
Width: Column

### Theo Marsh

Role: Founder, Tidewater Tickets

> Mira found the three screens our customers hated and fixed two of them
> in a week. The third was ours to fix, and she was right.

### Ana Okafor

Role: Owner, Corner Café

> Our booking page finally makes sense. So does the menu.

### Jules Brandt

Role: Product lead

> Calm, quick and allergic to unnecessary buttons.
""", dict(pinned=True, pin_location="header", parent="projects", template="landing", title_style="", days=110)),
        ("press-kit", "Press kit", "", "For journalists and podcast hosts.", f"""
Everything you need to write about me or have me on your show.

## For the press

Section: Bios

### Short bio

Mira Castell is a product designer and weekend baker who writes about
finishing things.

### Long bio

Mira Castell has designed software for twelve years, most recently for
small teams who'd rather ship one good thing than five rushed ones. On
Saturdays she helps run the Maple Street repair café, and she writes
about bread, bicycles and fog at this site.

### Photos

{img("kneading")}

{img("camera")}

## Past interviews

- [Making Podcast, episode 41](https://example.com/making-41) - on finishing things
- [The Harbour Gazette](https://example.com/gazette) - on the repair café
""", dict(pinned=True, pin_location="header", parent="projects", template="media-kit", days=100)),
        ("corner-cafe", "Corner Café", "projects, web", "A booking page that finally makes sense.", f"""
## At a glance

Section: Project facts

Client: Corner Café
Year: 2026
Role: Design, and a little code
Took: Six weekends

## The story

Section: Photo story

How a small café stopped answering the same three questions on the
phone, and got its Saturday mornings back.

### Challenge

Nobody could find the opening hours, the menu was a photo of a
chalkboard, and bookings came in by text message - at all hours, and
mostly to the owner's personal phone.

{img("bakery")}

The counter on a Saturday: the busiest hour, and the phone ringing under it.

### Approach

One page with the hours at the top, the menu as text, and a booking
form that asks only what the kitchen needs to know. We tested it with
regulars over coffee, which is the best kind of user research.

{img("notebook")}
{img("notebook_dark")}

> I used to spend my mornings on the phone. Now I spend them baking.
>
> — Ana, who owns the café

### Result

Phone calls down by half in the first month, bookings all in one
place, and the chalkboard retired with honours.

{img("desk")}

## More work

Section: Previous and next
""", dict(pinned=True, pin_location="header", parent="projects", template="project", days=90, sound="/uploads/cafe-ambience.mp3", cover="coffee")),
        ("small-fixes", "Small Fixes", "", "A zine about mending the things you own.", f"""
Thirty-two pages on fixing toasters, trousers and one very stubborn
lamp - from the repair café's first year.

[Order a copy](#copies)

- 32 hand-drawn pages
- Printed on recycled paper
- Posted anywhere

{img("notebook")}

## What's inside

Section: Image and text

{img("tools")}

Twelve repairs, step by step, drawn by hand. Each one took less than an
hour and saved something from the bin.

## Who it's for

Section: Image and text

{img("workshop")}

Anyone who has ever thrown out something with one broken part.

## The first year, in numbers

Section: Numbers

### 12
repairs, step by step

### 32
hand-drawn pages

### 200
copies, stapled by volunteers

## What readers say

Section: Testimonials

### Ingrid

Role: First-time fixer

> I fixed my kettle on a Sunday afternoon. I'd been about to throw it out.

### Tomas

Role: Volunteer, repair café

> The drawings are the best part - clear, and no jargon.

## As seen in

Section: Logos

![Harbour Makers](/uploads/logo-harbour-makers.png)
![Mend & Make Radio](/uploads/logo-mend-radio.png)
![Small Repairs Quarterly](/uploads/logo-small-repairs.png)
![The Library Workshop](/uploads/logo-library-workshop.png)

## Copies

Section: Pricing

### The zine

Price: US$12

- 32 pages, printed on recycled paper
- Posted anywhere

[Order the zine](/shop)

### The zine and a class

Price: US$40
Badge: Most popular

- The zine
- A Saturday repair class at the café

[Order with a class](/shop)

## Questions

Section: FAQ

### Do I need tools already?
A screwdriver and a needle get you through most of it.

### Is there a digital copy?
Not yet - it's made to be read with your hands busy.

## Fix something this weekend

Section: Call to action

Most repairs take less than an hour.

[Order a copy](#copies)
""", dict(pinned=True, pin_location="header", parent="shop", template="landing", title_style="", days=80)),
        ("shop", "Shop", "", "Prints, zines and a jar of starter.", f"""
A few things I've made. Each button goes straight to checkout.

## For sale

Section: Products

### Fog over the harbour

{img("fjord", "A print of a still fjord in fog")}

Price: €25

A3, on heavy matte paper.

[Buy it](https://example.com/buy/fog-print)

### Small Fixes zine

{img("notebook", "The Small Fixes zine")}

Price: €8

Thirty-two pages, hand-stapled.

[Buy it](https://example.com/buy/small-fixes)

### Starter, in a jar

Price: €5
Badge: Sold out

A spoonful of Gerald, my sourdough starter.

## Shipping

Anywhere, in a stiff envelope, within a week. Starter only in person.
""", dict(pinned=True, pin_location="header", template="landing", title_style="", days=70)),
        ("zine-club", "Zine club", "", "Coming in spring.", """
A zine club is on its way: one theme a month, everyone makes four
pages, and we staple them together.

## Hear first

Section: Sign-up

Leave your email and you'll hear when the first meet-up is.
""", dict(pinned=True, pin_location="header", parent="shop", template="coming-soon", days=10)),
        ("repair-cafe", "Repair café", "", "Bring your broken things.", """
A free repair café in the Maple Street Library: bring something broken
and we'll fix it together.

## Find us

Section: Contact details

Phone: 02 9000 0000
Email: fix@example.com
Address: Maple Street Library, Springfield

## Opening hours

Section: Opening hours

Saturday: 10am - 2pm
Sunday - Friday: Closed

## What we fix

Toasters, lamps, bicycles, zips, hems and the occasional radio. If it
plugs in, we'll test it before you take it home.

## What it costs

Nothing. There's a jar for the tea fund.

## So far

Section: Numbers
Style: Card

### 1,240
things fixed

### 9 in 10
leave working

### 2,000
cups of tea
""", dict(pinned=True, pin_location="header", template="business", days=200)),
        ("volunteers", "Volunteers", "", "The people who keep the café going.", f"""
The repair café runs on a dozen volunteers and a lot of tea.

## The volunteers

Section: Team

### Mira Castell

{img("kneading", "Mira")}

Role: Organiser, and the bake stall

Keeps the list of who fixes what, and the cinnamon buns.

### Theo Marsh

{img("tools", "Theo's tools")}

Role: Electrics

Has never met a lamp he couldn't rewire.

### Ana Okafor

{img("workshop", "The bike stand")}

Role: Bicycles

Can true a wheel faster than you can say "spoke key".

## Join us

Section: Call to action

Any skill is welcome - even just making the tea.

[Get in touch](/contact)
""", dict(pinned=True, pin_location="header", parent="repair-cafe", template="landing", title_style="", days=190)),
        ("bake-stall", "Bake stall menu", "", "What's on the Saturday stall.", """
Saturday mornings at the repair café, until it's gone. The price list
to print and pin up is below, too.

/uploads/bake-stall-price-list.pdf

## On the stall

Section: Menu
Width: Column

### Bread

- Country sourdough - Gerald's finest · €9
- Seeded rye - dark, dense and worth it · €10
- Focaccia - rosemary and sea salt · €7

### Sweet

- Cinnamon bun - still warm · €4
- Brown butter cookie · €3

### Drinks

- Coffee · €3.5
- Tea - whatever's in the tin · €2.5
""", dict(pinned=True, pin_location="header", parent="repair-cafe", template="landing", title_style="", days=60)),
        ("handbook", "Fixer's handbook", "", "How the repair café runs, for anyone who helps.", """
How a Saturday at the repair café runs, for anyone who fixes, makes the
tea or holds the torch. Read it once before your first morning.

## Before you come

Bring your own tools if you have them - mark them with tape and your
name. We have screwdrivers, a soldering iron and far too much glue.

### What to wear

Closed shoes, and nothing with long sleeves near the lathe.

## At the table

Each visitor sits with you while you work. Explain what you're doing -
half the point is that they can fix it themselves next time.

### Writing it down

Every repair gets a line in the log: what it was, what was wrong and
whether it worked. A "no" is useful too.

### When it can't be fixed

Say so kindly, and say why. Point them to a recycling bin for the parts.

## Safety

!!! warning "Anything with a plug"
    Only Theo or Ana open mains appliances. Everyone else: batteries
    and low voltage only.

Unplug before you open anything, and test it on the bench socket before
it goes home.

## After

Sweep the floor, put the tools back on the board where their outline is,
and take a bun - you've earned it.
""", dict(pinned=True, pin_location="header", parent="repair-cafe", template="docs", days=170)),
        ("talks", "Talks and workshops", "", "Where I'll be.", f"""
Talks and workshops on mending and on finishing things.

## On the calendar

Section: Events

### Mending as design practice

Date: {_day(21)}
Place: Maple Street Library

What fixing a toaster taught me about designing software.

### Fix your bike: a beginners' workshop

Date: {_day(48)}
Place: The repair café

Bring your bike and two hours. Tools and tea provided.

### Finishing things

Date: {_day(-60)}
Place: Small Design Meetup

[Slides](https://example.com/slides/finishing) · [Video](https://example.com/video/finishing)

### The repair café's first year

Date: {_day(-200)}
Place: Town Hall
""", dict(pinned=True, pin_location="header", parent="projects", days=180)),
        ("bookshelf", "Bookshelf", "", "What I've read lately, and what I thought.", f"""
Books I've finished recently, rated with the confidence of someone who
reads mostly on the ferry.

{img("books")}

## Read lately

Section: Reviews

### The Art of Fermentation

Author: Sandor Ellix Katz
Rating: 5/5
Finished: August 2026

The book that made me stop apologising for the jars on my windowsill.
Encyclopedic, warm and faintly alarming.

### Zen and the Art of Motorcycle Maintenance

Author: Robert M. Pirsig
Rating: 4/5
Finished: May 2026

I read it for the maintenance and stayed for the Quality. My bike is
not a motorcycle; the lessons transferred anyway.

### Shop Class as Soulcraft

Author: Matthew B. Crawford
Rating: 4/5
Finished: February 2026

An argument for working with your hands that I read, appropriately,
with oil under my fingernails.

### Four Thousand Weeks

Author: Oliver Burkeman
Rating: 5/5
Finished: Still reading

On finitude and time. I'm reading it one chapter a week, which feels
like either wisdom or procrastination.
""", dict(pinned=True, pin_location="header", parent="about", days=30)),
        ("uses", "Uses", "", "The tools I use for design, bread and bicycles.", f"""
The things I use every day, and a few I use too much.

{img("desk")}

## What I use

Section: Uses

### Desk

- **A 14-inch laptop** - old enough to have opinions, new enough to run Figma.
- **A mechanical keyboard** - loud, which my neighbour below has mentioned.
- **A paper notebook** - where every good idea starts and most bad ones end.

### Kitchen

- **A cast-iron pot** - bakes every loaf; weighs as much as a small dog.
- **A digital scale** - accurate to a gram, which bread demands.
- **A bench scraper** - the best five euros I've ever spent.

### Workshop

- **[Park Tool cone spanners](https://www.parktool.com)** - for wheels, and patience.
- **A very small wire brush** - see the Peugeot series.

### Software

- **[Soloblog](https://github.com/soloblog/soloblog)** - this site.
- **Figma** - for work.
- **A plain text file called `done.txt`** - the most motivating app I own.
""", dict(pinned=True, pin_location="header", parent="about", days=60)),
        ("contact", "Contact", "", "", "", dict(pinned=True, pin_location="header", template="link",
                                               link="/contact", days=399)),
        ("privacy", "Privacy", "", "What this site does and doesn't keep about you.", """
This site keeps as little about you as it can.

- **Visits** are counted without cookies and without storing who you are.
- **Comments** keep the name and email address you give; the address is
  never shown and only used to confirm your comment.
- **The newsletter** keeps your email address until you unsubscribe, which
  every email lets you do in one click.
- **Nothing** is sold, shared or handed to advertisers.

Questions? Use the [contact form](/contact).
""", dict(pinned=True, pin_location="footer", days=399)),
        ("terms", "Terms of sale", "", "For prints, zines and bread classes.", """
Last updated: 1 September 2026

For anything bought from the [shop](/shop) or booked as a
[bread class](/bread-classes).

## Orders

Prints and zines are posted within a week, anywhere. If one arrives
damaged, send a photo through the [contact form](/contact) and I'll
send another.

## Classes

Cancel up to two days before for a full refund. Later than that, the
place can go to a friend instead.

## Starter

Gerald is given in good faith. Results depend on your kitchen, your
flour and your patience.
""", dict(pinned=True, pin_location="footer", days=399)),

        # ---- posts
        ("my-sourdough-starter-has-outlived-three-houseplants",
         "My sourdough starter has outlived three houseplants and a toaster", "bread, kitchen",
         "Seven years, two cities, one jar. A love letter to the most demanding pet I've ever had.", f"""
My sourdough starter is seven years old. In that time I have killed
three houseplants, one toaster and a relationship with a man who
thought "feeding the starter" was a euphemism.

The starter, meanwhile, thrives on neglect and flour. There's a lesson
in there, and I'm choosing not to learn it.

{img("starter")}

## What a starter actually is

Flour and water, left alone long enough that wild yeast and bacteria
move in and start a small, sour civilisation[^1]. You feed it; it
rises; you bake with some and keep the rest. That's the whole trick.

!!! tip "The only rule that matters"
    Feed it the same weight of flour and water, and use it when it has
    doubled and smells like yoghurt that's been to university.

## Seven years of lessons

1. **It will survive a week in the fridge.** It will survive a month.
   It will survive you forgetting it exists.
2. **It won't survive a hot car.** Ask me how I know.
3. **Name it.** Mine is called Brenda. You're less likely to throw out
   something called Brenda.

## My weekly routine

- [x] Feed Brenda on Friday night
- [x] Mix the dough on Saturday morning
- [x] Shape it before lunch, into the fridge overnight
- [ ] Remember to buy more flour *before* running out

{img("plant", "The last surviving houseplant, keeping its distance")}

The houseplant above is the fourth. It sits well away from the jar, and
honestly, I think it knows.

[^1]: Microbiologists would describe this more precisely and with fewer
    jokes about civilisation.
""", dict(cover="loaf", days=210, views=1840, likes=64, sides="author=left,tags=right")),
        ("emergency-focaccia", "Emergency focaccia, for people who forgot to plan dinner", "bread, recipes, kitchen",
         "Four hours from nothing to golden, dimpled, olive-oily bread. No starter, no plan, no problem.", f"""
This is the bread I make when it's four o'clock, I have nothing for
dinner, and people are coming at eight. It's forgiving, it's fast, and
it looks like you tried much harder than you did.

## At a glance

Section: Recipe facts

Serves: 6
Prep: 20 min
Cook: 25 min

## Ingredients

Section: Ingredients

- 500 g strong white flour
- 400 g warm water
- 7 g instant yeast
- 10 g salt
- 80 ml good olive oil, plus more for the tin
- A handful of rosemary, flaky salt

## Method

Section: Method

1. Stir the flour, water, yeast and salt into a shaggy mess. Cover and
   leave for 30 minutes.
2. With wet hands, stretch and fold the dough four times over an hour.
3. Pour half the oil into a baking tin, tip in the dough and let it
   relax until it fills the corners, about 90 minutes.
4. Dimple it all over with oily fingers, press in the rosemary and
   scatter the salt.
5. Bake at 230°C for 20–25 minutes, until deep gold and crackling.

## Notes

{img("crumb")}

It keeps for a day, which is purely theoretical - it has never lasted
that long in my kitchen.
""", dict(cover="focaccia", template="recipe", days=150, views=2960, likes=121)),
        ("i-bought-a-1983-racing-bike-from-a-man-named-lars", "I bought a 1983 racing bike from a man named Lars",
         "bikes, projects", "It was rusty, it was beautiful, and Lars would only take cash.", f"""
The listing said "old bike, needs love". The photo showed a blue steel
frame leaning against a brick wall, and I was in love before I'd
finished reading.

Lars turned out to be seventy-eight and deeply suspicious of bank
transfers. He'd bought it new in 1983, ridden it to work for twenty
years, and then, in his words, "got a car and got fat".

{img("bike_blue")}

## What I got for my money

- A Reynolds 531 steel frame, straight and true
- Two wheels, one of which was round
- Brakes that suggested stopping rather than performing it
- A saddle with the texture and comfort of a paving stone

## Why bother?

Because a new bike is a purchase and an old one is a story. Also
because I'd spent the winter designing screens and I wanted to fix
something I could hold.

Lars shook my hand, told me to keep the chain oiled, and watched me
push it down the road like I was taking his dog.
""", dict(cover="bike_blue", series=("The Peugeot", 1), days=180, views=1320, likes=58)),
        ("rust-patience-and-a-very-small-wire-brush", "Rust, patience and a very small wire brush", "bikes, projects",
         "Three weekends, one very small brush and a lot of swearing in two languages.", f"""
Restoring a bike is mostly cleaning. Nobody tells you this. The
internet shows you the before and after; the during is a wire brush
the size of a toothbrush and a podcast about something else entirely.

{img("workshop")}

## The order I did things in

| Weekend | Job | Swearing |
|---|---|---|
| 1 | Stripped it down, bagged and labelled every bolt | Mild |
| 2 | Rust off the chrome, new cables and housing | Moderate |
| 3 | Wheels trued, bearings regreased, rebuilt | Norwegian |

## What I'd tell myself at the start

> Take a photo before you take anything apart. Then take another one,
> from the other side.

The bottom bracket fought me for an afternoon. I won, eventually, with
a borrowed tool and a length of scaffolding pole that I'm told is not
standard practice.

{gallery("tools", "bike_lamp", "workshop")}
""", dict(cover="workshop", series=("The Peugeot", 2), days=160, views=980, likes=41)),
        ("back-on-the-road-mostly", "Back on the road (mostly)", "bikes, projects, outdoors",
         "The Peugeot's first real ride, and the one part I haven't fixed yet.", f"""
It rides. It rides beautifully, in fact - light and quick and a little
twitchy, like a greyhound that's just seen a squirrel.

{img("forest_road")}

The first proper ride was 30 km along the coast road and back through
the forest. Nothing fell off. The shifting is crisp, the brakes stop
things, and the new saddle has settled from "paving stone" to "firm
handshake".

## What's still not right

The front wheel has a tiny wobble I can only see when I'm looking for
it, which is always. It's on the list. Everything is on the list.

{gallery("bike_red", "city_bike", "forest_road", style="filmstrip")}

I sent Lars a photo. He replied, in full: "Good. Oil the chain."
""", dict(cover="forest_road", series=("The Peugeot", 3), days=120, views=1105, likes=77)),
        ("fog-ferries-and-one-extremely-patient-heron", "Fog, ferries and one extremely patient heron",
         "projects, photography, harbour", "Fifty foggy mornings on the harbour, and the heron who was there for all of them.", f"""
## The fog

Section: Photo story

In October the fog comes in off the water and stays for breakfast. I
started taking a camera down to the harbour on those mornings, and
then I couldn't stop.

{img("tug_fog", "A tug pushes out into the grey")}

The ferries sound their horns every few minutes. You hear them long
before you see them, which gives the whole thing the feeling of a
ghost story told by a very polite ghost.

{img("heron")}

And then there's the heron. Same spot, most mornings, standing in the
shallows with the patience of someone waiting for a kettle. I've
photographed him more than any person I know.

{img("fishing_boat")}

{img("old_lake", "A photograph a century older than mine, with the same fog")}

This last one isn't mine. I found it in a museum's open collection -
the same fog, a hundred years earlier. Nothing about the harbour has
changed except the boats and the people complaining about the ferry
timetable.

## More work

Section: Previous and next
""", dict(cover="pier_fog", template="project", days=95, views=2210, likes=140)),
        ("everything-my-grandmother-knows-about-running-a-bakery",
         "Everything my grandmother knows about running a bakery", "bread, family",
         "She ran a bakery for thirty years. I asked her how. She mostly talked about ovens and gossip.", f"""
My grandmother ran a bakery in a small town for thirty years. She's 91,
sharp as a bread knife, and agreed to an interview on the condition
that I brought cake.

{img("bakery")}

## The conversation

Section: Interview

**Me:** What time did you start in the morning?

**Oma:** Half past three. The bread doesn't care that you're tired.

**Me:** Did you ever get used to it?

**Oma:** No. You just stop expecting to feel awake. That's different.

**Me:** What was the hardest part?

**Oma:** The oven. It had moods. On a cold day it sulked; on a hot day
it burnt everything on the left. I knew it better than I knew your
grandfather.

<!-- members only from here -->

{img("kneading")}

## The rest

Section: Interview

**Me:** And the best part?

**Oma:** The first customers. Always the same four people, and they
told me everything. I knew who was getting divorced before their
husbands did.

**Me:** Any advice for my sourdough?

**Oma:** Stop photographing it and eat it while it's warm.
""", dict(cover="kneading", template="interview", days=75, views=3410, likes=212, visibility="members")),
        ("questions-people-ask-when-i-say-i-dont-own-a-car",
         "Questions people ask when I say I don't own a car", "bikes, city",
         "Yes, it rains. No, I'm not training for anything. Answers to the usual questions.", f"""
I haven't owned a car in six years. It comes up at parties more than
you'd think, usually followed by one of these.

{img("city_bike")}

## Questions

Section: FAQ

### Don't you get wet?

Yes. Then I get dry. It's a cycle, much like the bicycle.

### What about the shopping?

A basket on the front and panniers on the back carry a week's food.
The big supermarket run is a lot of small ones, which also means
fresher bread.

### Isn't it dangerous?

Our town has decent bike lanes and I ride like everyone else on the
road is distracted, because they are.

### What do you do when you need a car?

Borrow one, rent one, or discover I didn't need one after all. That
last one happens more often than you'd expect.

### Are you training for something?

Only for being slightly less out of breath on the hill by the ferry.
""", dict(cover="city_bike", days=55, views=870, likes=33)),
        ("ten-years-of-learning-norwegian-badly", "Ten years of learning Norwegian, badly", "language, travel",
         "A decade of verbs, dialects and being answered in English. A timeline of small victories.", f"""
I've been learning Norwegian for ten years. My vocabulary is excellent;
my grammar is a rumour. Here's how it went.

{img("fjord")}

## Ten years

Section: Milestones

### 2016 · Moved to Bergen

Learned *takk*, *unnskyld* and the word for "rain" in nine variations,
all of which I needed in the first week.

### 2017 · First evening class

Sat next to a retired sea captain who had been attending the same
beginners' class for four years "for the company".

### 2019 · Ordered a whole meal in Norwegian

The waiter replied in English. I pretended not to understand and
carried on. We both won.

### 2021 · Understood a joke

On the radio, about the weather. I laughed a full two seconds after
everyone else in the café.

### 2023 · Dreamt in Norwegian

The dream was about verbs. I conjugated them wrong, even asleep.

### 2026 · Still learning

{img("fjord_farm")}

Now working on dialects, which is like learning the language again,
except everyone insists theirs is the correct one.
""", dict(cover="oslo_sunset", days=40, views=1560, likes=95)),
        ("how-i-back-up-40000-photos", "How I back up 40,000 photos without thinking about it",
         "tools, photography",
         "Three copies, two kinds of storage, one of them somewhere else. Set up once, then ignored forever.", f"""
Every photographer loses photos exactly once. After that, they back up.
This is my setup: three copies of everything, on two kinds of storage,
with one copy somewhere other than my flat.

{img("platter")}

## The rule

Three copies, two different kinds of storage, one of them off-site.
It's called the 3-2-1 rule, and it's ==boring, which is the point==.

| Copy | Where | How often |
|---|---|---|
| 1 | My laptop | Always - it's where I work |
| 2 | A portable drive | Every night, automatically |
| 3 | A cloud bucket | Every night, encrypted |

## The nightly copy

A scheduled job copies anything new to the portable drive:

=== "Mac and Linux"

    ```bash
    rsync -a --delete ~/Pictures/ /Volumes/Photos/
    ```

=== "Windows"

    ```powershell
    robocopy $HOME\\Pictures E:\\Photos /MIR
    ```

To check it ran, open the drive and press ++ctrl+f++ (++cmd+f++ on a Mac)
for today's photos.

## The off-site copy

The same folder goes, encrypted, to a cloud bucket:

```bash
rclone sync ~/Pictures remote:photos --transfers 8
```

!!! warning "Test your restore"
    A backup you've never restored from is a hope, not a backup. Once
    a quarter I restore a random folder and check it opens.

## What it costs

About the price of one coffee a month for the cloud storage, and one
evening to set up. The peace of mind is free.

{img("drive")}
""", dict(cover="platter", days=25, views=640, likes=28)),
        ("worth-reading-the-right-to-repair", "Worth reading: the right to repair", "projects, reading",
         "Why being allowed to fix your own things matters, from phones to tractors to old bicycles.", """
After a winter of rebuilding a bike from 1983 - every part of which can
still be taken apart, cleaned and replaced - I went looking for why so
few modern things can be. This is the best overview I've found: short,
well-sourced, and quietly infuriating.
""", dict(cover="tools", template="link", link="https://en.wikipedia.org/wiki/Right_to_repair", days=100, views=410,
         likes=19)),
        ("the-five-minute-rule-and-other-tricks-for-finishing-things",
         "The five-minute rule, and other tricks for finishing things", "habits, projects",
         "Most of my projects die at 90%. These five tricks drag them over the line.", f"""
I am an excellent starter of things. The finishing is where I come
unstuck. Over the years I've collected a few tricks that get projects
over the line, and I'm sharing them in the hope that writing them down
counts as finishing something.

{img("notebook")}

## 1. The five-minute rule

When I don't want to do something, I agree to do it for five minutes.
I almost always keep going. When I don't, I've still done five minutes.

<!-- members only from here -->

## 2. Keep a `done.txt`

A plain text file, one line per finished thing. On bad days I read it
back. It's the least glamorous and most motivating thing I own.

## 3. Decide what "done" means before you start

> A project without a finish line isn't a project. It's a hobby with
> guilt.

## 4. Finish ugly

The first version can be embarrassing. The second one never gets made
if the first one doesn't ship.

## 5. Tell one person

Not the internet - one person, who will ask how it's going. Mine is my
grandmother, who has no mercy.
""", dict(cover="notebook", days=12, views=1210, likes=88, visibility="paid")),
        ("fixing-things-notes-from-my-library-talk", "Fixing things: notes from my library talk", "projects, talks",
         "The slides from a twenty-minute talk at the library's repair café. Arrow keys to flip through.", """
# Fixing things

Notes from the repair café, Maple Street Library

---

## Why fix anything?

- It's cheaper
- It's kinder to the planet
- You get to feel like a wizard

---

## The three tools you need

1. A screwdriver set
2. A torch
3. The patience to read the manual

---

## The one habit

**Take a photo before you take it apart.**

---

## Thank you

Questions, broken toasters and cake welcome.
""", dict(cover="library", template="slides", slides=True, days=45, views=300, likes=17)),
        ("weeknotes-rye-rain-and-a-new-bell", "Weeknotes: rye, rain and a new bell", "weeknotes",
         "A wet week, a better loaf and the first ride in the dark.", """
A wet week, mostly spent indoors with the oven on.

## What happened

- Gunnar, the rye starter, finally made a loaf that rose
- Rode home from the café in the dark for the first time this autumn
- Twelve things fixed on Saturday, one radio from 1962

## What I learned

- Rye wants a warmer kitchen than wheat
- A bicycle bell sounds friendlier than you'd think in fog

## Next week

- [x] Order a new bell
- [ ] Test the [zine club](/zine-club) idea on three friends
- [ ] Bake for the Saturday stall
""", dict(cover="bike_red", days=2, views=120, likes=9)),
        ("a-small-victory-the-bread-knife-is-back", "A small victory: the bread knife is back", "kitchen",
         "It was missing for a month. The explanation is worse than you think.", """
The good bread knife went missing in August. I searched the kitchen,
the workshop and, in a low moment, the recycling.

It turned up yesterday, in the bike toolbox, where I had apparently
used it to scrape old grease off the Peugeot's chain rings.

It has been washed. Twice. We are not talking about it.
""", dict(cover="bakery", days=70, views=190, likes=24)),
        ("a-year-of-fog-five-ways", "A year of fog, five ways", "photography, fog",
         "Twelve months of the harbour in grey - and every way this site can lay out a gallery.", f"""
I take a photo of the harbour most mornings. Most of them are of fog. Here
is a year of it, laid out five different ways, because I couldn't choose.

## A grid

Even squares, for when every photo matters as much as the next.

{gallery("tug_fog", "pier_fog", "old_lake", "fishing_boat", "heron", "fjord", style="grid")}

## Masonry

Columns, each photo at its own height - the way a pinboard fills up.

{gallery("heron2", "fjord_farm", "yellow_boat", "tug_fog", "oslo_sunset", "pier_fog", style="masonry")}

## Justified

Rows of equal height, edge to edge, like a contact sheet.

{gallery("fjord", "fishing_boat", "old_lake", "heron", "yellow_boat", style="justified")}

## A slider

One at a time, with arrows - for a sequence that should be seen in order.

{gallery("tug_fog", "pier_fog", "fishing_boat", "oslo_sunset", style="slider")}

## A filmstrip

A row you scroll sideways, like holding the negatives up to the window.

{gallery("heron", "heron2", "fjord_farm", "fjord", "old_lake", style="filmstrip")}

Any photo opens bigger when you click it.
""", dict(cover="fjord", days=4, views=640, likes=51)),
        ("gear-inches-and-other-numbers", "Gear inches, and other numbers I now care about", "bikes, projects",
         "The maths of an old bicycle, a flowchart for whether a part is worth saving, and a lot of notes.", r"""
Restoring the Peugeot has turned me into someone with ==opinions about
numbers==. This is the page I keep open while I work.

!!! tip "If you're starting your own"
    Photograph everything before you take it apart. Then photograph it
    again, from the other side.

## Gear inches

The old way of saying how hard a gear is to push: the wheel's diameter,
times the chainring's teeth over the sprocket's.

$$\text{gear inches} = d_{\text{wheel}} \times \frac{T_{\text{chainring}}}{T_{\text{sprocket}}}$$

So the Peugeot's top gear, $27 \times \frac{52}{14}$, is about 100 inches -
far more than my knees agreed to in 1983 or now.

| Chainring | Sprocket | Gear inches | Feels like |
|---|---|---|---|
| 52 | 14 | 100 | A tailwind I don't have |
| 52 | 21 | 67 | Flat roads, good mood |
| 42 | 24 | 47 | The hill by the bakery |

## Is it worth saving?

```mermaid
flowchart LR
    A[A rusty part] --> B{Does it still move?}
    B -->|Yes| C[Clean it, grease it, keep it]
    B -->|No| D{Is it original?}
    D -->|Yes| E[Soak it overnight, try again]
    D -->|No| F[Replace it, keep the old one in a jar]
```

## Steel or aluminium

=== "Steel"
    Heavier, springier, and it can be bent back after a crash. The
    Peugeot is Reynolds 531 - see [[Reynolds 531]] in my notes.

=== "Aluminium"
    Lighter and stiffer, and it doesn't rust - but once it cracks, it's
    finished.

## Words I had to learn

Bottom bracket
:   The bearing the cranks turn in. Mine was full of something that was
    once grease.

Headset
:   The bearing the handlebars turn in. Also full of history.

!!! warning "Check the chain first"
    A stretched chain wears out everything it touches - see
    [[Chain wear]]. It's the cheapest part to replace and the most
    expensive to ignore.

## Still to do

- [x] New brake cables
- [x] True the wheels
- [ ] Find a period-correct bottle cage that doesn't cost more than the bike
- [ ] Pump the tyres to 90 PSI and stop checking them every morning
- [ ] Learn to fix a puncture without swearing[^1]

[^1]: Ambitious.

*[PSI]: Pounds per square inch - how hard the tyres are pumped
""", dict(cover="bike_lamp", days=8, views=720, likes=46)),
    ] + _notes()


COMMENTS = {
    "my-sourdough-starter-has-outlived-three-houseplants": [
        ("Tom B.", "My starter is called Kevin and he has also outlived my houseplants. Solidarity.", 200, None),
        ("Priya", "The toaster detail is doing a lot of work here and I'd like to know more.", 198, None),
        ("Mira", "The toaster knew what it did.", 197, "author"),
    ],
    "emergency-focaccia": [
        ("Jonas", "Made this tonight in exactly the panic you described. Guests asked for the recipe.", 140, None),
        ("Elin", "Does it work with half wholemeal flour?", 130, None),
        ("Mira", "It does - add a splash more water and give it an extra half hour to rise.", 129, "author"),
    ],
    "i-bought-a-1983-racing-bike-from-a-man-named-lars": [
        ("Henrik", "Reynolds 531! Lars had taste. Keep the original decals if you can.", 176, None),
    ],
    "fog-ferries-and-one-extremely-patient-heron": [
        ("Sam W.", "I would read an entire book about that heron.", 90, None),
        ("Aiko", "The museum photo at the end gave me chills. Same fog, a hundred years apart.", 88, None),
    ],
    "everything-my-grandmother-knows-about-running-a-bakery": [
        ("Liv", "\"I knew who was getting divorced before their husbands did\" - I love her.", 70, None),
        ("Marcus", "Please tell her the internet thinks she's wonderful.", 69, None),
        ("Mira", "I did. She said the internet should visit more often and bring cake.", 68, "author"),
    ],
    "the-five-minute-rule-and-other-tricks-for-finishing-things": [
        ("Nadia", "Started a done.txt after reading this. Line one: \"read a blog post\". It counts.", 10, None),
    ],
}


# the Every template page: template -> (Mira's page that shows it, its photo)
TEMPLATES = {
    "recipe": ("emergency-focaccia", "focaccia"),
    "interview": ("everything-my-grandmother-knows-about-running-a-bakery", "kneading"),
    "docs": ("handbook", "platter"),
    "wiki": ("", "old_lake"),
    "link": ("worth-reading-the-right-to-repair", "tools"),
    "slides": ("fixing-things-notes-from-my-library-talk", "library"),
    "now": ("now", "plant"),
    "resume": ("cv", "notebook_dark"),
    "profile": ("in-short", "camera"),
    "media-kit": ("press-kit", "yellow_boat"),
    "project": ("corner-cafe", "coffee"),
    "portfolio": ("projects", "bike_blue"),
    "services": ("work-with-me", "desk"),
    "pricing": ("bread-classes", "loaf2"),
    "testimonials": ("kind-words", "notebook"),
    "events": ("talks", "library"),
    "landing": ("small-fixes", "dough"),
    "business": ("repair-cafe", "workshop"),
    "coming-soon": ("zine-club", "fishing_boat"),
}
# how the Every template page groups them
TEMPLATE_GROUPS = (("Writing", ("recipe", "interview", "docs", "wiki", "link", "slides", "now")),
                   ("Personal", ("resume", "profile", "media-kit")),
                   ("Work", ("project", "portfolio", "services", "pricing", "testimonials", "events", "landing")),
                   ("Business", ("business", "coming-soon")))


def _templates_page(photos):
    """Every template, each as a card going to the page of Mira's that
    shows it, with the sections it starts with - a Portfolio section for
    each group."""
    from soloblog import post_templates, posts
    from soloblog.routes.editor import section_names
    groups = []
    for group, keys in TEMPLATE_GROUPS:
        cards = []
        for key in keys:
            slug, photo = TEMPLATES[key]
            row = posts.get_post(slug) if slug else None
            name, body = post_templates.BUILT_IN[key]
            names = section_names(body)
            about = f"Starts with {', '.join(names)}." if names else "Plain writing, with its settings."
            cards.append(f"### {name}\n\n![{PHOTOS[photo][2]}]({photos.get(photo, '')})\n\n{about}\n\n"
                         f"[See it]({posts.url_for(row) if row else '/wiki'})")
        groups.append(f"## {group}\n\nSection: Portfolio\nShow as: Grid\n\n" + "\n\n".join(cards))
    # the catalogue looks the same whichever style a visitor tries
    return (f"Soloblog comes with {len(post_templates.BUILT_IN)} templates - a page ready to fill in, made of "
            "sections and settings. Start a post from one, or apply one to a page you've begun. Here are some, "
            "each as Mira has used it.\n\n[See every section](/sections)\n\n" + "\n\n".join(groups))


# the Every style page: preset -> its photo
STYLE_PHOTOS = {"personal": "loaf", "notebook": "notebook", "magazine": "yellow_boat", "photo": "fjord",
                "portfolio": "bike_blue", "journal": "oslo_sunset", "freelancer": "desk", "business": "bakery",
                "docs": "platter", "wiki": "old_lake", "launch": "dough", "link-in-bio": "camera"}


def _styles_page(photos):
    """Every starting style, each tried on the whole site for this visitor
    only (/demo/style) - and the way back to Mira's own."""
    from soloblog import presets
    cards = [f"### {name}\n\n![{PHOTOS[STYLE_PHOTOS[key]][2]}]({photos.get(STYLE_PHOTOS[key], '')})\n\n"
             f"{about}\n\n[Try it](/demo/style/{key})" for key, (name, about, *_) in presets.PRESETS.items()]
    return (f"A starting style changes the whole site in one go - how posts are listed, the header, the "
            f"fonts and what each post shows. Here are all {len(presets.PRESETS)}. Try one: the site changes "
            "for you alone, and the note in the corner brings Mira's own look back.\n\n"
            "## Every style\n\nSection: Portfolio\nShow as: Grid\n\n"
            f"### Mira's own\n\n![{PHOTOS['fjord_farm'][2]}]({photos.get('fjord_farm', '')})\n\n"
            "Cards, a floating header, a banner across the screen and soft colours.\n\n"
            "[Go back to it](/demo/style)\n\n" + "\n\n".join(cards))


def _tour_page(photos):
    """What the site can do, as a landing page made of sections - the way
    in for someone seeing Soloblog for the first time."""
    from glob import glob
    from soloblog import post_templates, presets
    from soloblog.sections import REGISTRY
    p = lambda key: f"![{PHOTOS[key][2]}]({photos.get(key, '')})"  # noqa: E731
    languages = len(glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "locales", "*.json"))) + 1
    return f"""## Everything this site can do

Section: Hero
Style: Window

Label: The tour

{p("tug_fog")}

I wanted to see everything this site could do, so I tried all of it.
Every page here is real - open the admin and change any of it.

[Start with the templates](/templates)

## In numbers

Section: Numbers
Style: Card

### {len(post_templates.BUILT_IN)}
templates

### {len(presets.PRESETS)}
starting styles

### {len(REGISTRY)}
kinds of section

### {languages}
languages for visitors

## From a draft to a page

Section: Story

### Write it

{p("notebook_dark")}

Type in the editor like any notebook. Press / for plans, photos, a contact form and the rest.

### Start from a template

{p("desk")}

A recipe, a resume, a café menu - pick one, change the words and it's yours.

### Add the parts you need

{p("tools")}

Numbers, a team, opening hours, a story like this one - in any page, in any order.

## Where to look

Section: Features

### Every template

Icon: layout-template

A page made from each one, from a recipe to a café menu. [See them](/templates)

### Every style

Icon: palette

The whole site as a magazine, a portfolio or a wiki - just for you. [Try one](/styles)

### Every section

Icon: puzzle

Plans, numbers, a team, opening hours - in any page. [See them](/sections)

### A portfolio, five ways

Icon: image

My projects as a grid, rows, full screen and more. [See my work](/projects)

### Galleries

Icon: camera

A year of fog, in every gallery there is. [See the fog](/post/a-year-of-fog-five-ways)

### Notes that link

Icon: book-open

A small wiki of bread and bicycle notes. [Read the notes](/wiki)

### Members and paid posts

Icon: lock

Posts for members, and plans readers pay for. [See the plans](/membership)

### Email

Icon: mail

New posts by email, with a weekly round-up. [Sign up](/newsletter)

## Posts that do more

Section: Bento grid

### A recipe

{p("focaccia")}

With its servings, times and a print button.

[Emergency focaccia](/post/emergency-focaccia)

### An interview

Questions and answers, for members.

[Oma's bakery](/post/everything-my-grandmother-knows-about-running-a-bakery)

### Slides

A talk you flip through.

[Fixing things](/post/fixing-things-notes-from-my-library-talk)

### A timeline

Ten years, year by year.

[Learning Norwegian](/post/ten-years-of-learning-norwegian-badly)

### A series

Three posts, read in order.

[The Peugeot](/series/the-peugeot)

## How I set it up

Section: Steps

1. Picked a starting style, then my own colours.
2. Wrote posts the way I write anything.
3. Made pages from templates - a shop, a CV, a café.
4. Added sections where a page needed more.

## Your turn

Section: Call to action

The admin is open to everyone, and it all resets every few hours.

[Open the admin](/admin)
"""


# as daisyUI's theme generator exports a theme
HARBOUR = """@plugin "daisyui/theme" {
  name: "harbour";
  default: false;
  prefersdark: false;
  color-scheme: "light";
  --color-base-100: oklch(98% 0.01 220);
  --color-base-200: oklch(95% 0.015 220);
  --color-base-300: oklch(90% 0.02 220);
  --color-base-content: oklch(28% 0.04 240);
  --color-primary: oklch(52% 0.11 230);
  --color-primary-content: oklch(98% 0.01 230);
  --color-secondary: oklch(68% 0.12 45);
  --color-secondary-content: oklch(22% 0.04 45);
  --color-accent: oklch(72% 0.1 175);
  --color-accent-content: oklch(22% 0.03 175);
  --color-neutral: oklch(35% 0.03 240);
  --color-neutral-content: oklch(96% 0.01 240);
  --color-info: oklch(70% 0.12 230);
  --color-info-content: oklch(20% 0.04 230);
  --color-success: oklch(70% 0.14 150);
  --color-success-content: oklch(20% 0.04 150);
  --color-warning: oklch(82% 0.14 80);
  --color-warning-content: oklch(25% 0.05 80);
  --color-error: oklch(64% 0.19 25);
  --color-error-content: oklch(98% 0.01 25);
  --radius-selector: 1rem;
  --radius-field: 0.5rem;
  --radius-box: 1rem;
  --size-selector: 0.25rem;
  --size-field: 0.25rem;
  --border: 1px;
  --depth: 1;
  --noise: 0;
}"""


def _sections_page(photos):
    """Every kind of section once, in an ordinary post - the way any post
    or page can use them (Insert > Sections)."""
    p = lambda key: f"![{PHOTOS[key][2]}]({photos.get(key, '')})"  # noqa: E731
    return f"""Any post or page can have sections - plans, kind words, a row of
numbers - between its paragraphs. Each one is a heading with a line under
it saying what kind it is. Here's every kind, once.

## Hero

Section: Hero

A big heading, a line and a button over a photo.

{p("tools")}

The repair café is back on Saturday, with more benches than ever.

[Come along](/repair-cafe)

## Bento grid

Section: Bento grid

Tiles of different sizes in one grid, the first one big.

### Bicycles, mostly

{p("bike_blue")}

Brakes, gears and the odd frame that needs a weld - the bike bench is always busy.

### Lamps

Rewired, not replaced.

### Toasters

Most of them, anyway.

### Clothes

Buttons, zips and hems.

### Radios

The ones with valves too.

## Story

Section: Story

Pictures that change as you scroll the words - on a phone, each one fills the screen.

### Bring it in

{p("bike_blue")}

A bicycle with a stiff gear, a lamp that flickers, a toaster that just clicks.

### We look it over

{p("workshop")}

Someone with the right tool, and the patience to show you what's wrong.

### Take it home

{p("city_bike")}

Working again, and you know why.

## Features

Section: Features

Short items, each with an icon (an `Icon: leaf` line), a title and a line.

### Tools on the table

Icon: puzzle

Bring the thing; we bring the screwdrivers.

### Tea and cake

Icon: coffee

Fixing goes better with a slice.

### Less thrown away

Icon: leaf

Nine in ten things leave working.

## Columns

Section: Columns

Plain columns of words, side by side.

### What people bring

Lamps, toasters, bicycles, a radio from 1962.

### What they take home

The same things, working - and how to fix them next time.

## A cover

Section: Image and text
Style: Cover

{p("forest_road")}

A Hero, a Call to action or a Picture and text can be a cover with a
`Style: Cover` line - its words over its picture, across the page.

## Picture and text

Section: Image and text

A picture beside its words.

{p("workshop")}

Once a month the church hall fills with toasters, bicycles and one very
old sewing machine. Bring what's broken; leave with it working, or knowing why.

## Numbers

Section: Numbers
Style: Card

Big figures, and what each one counts. They count up as they appear - and
this one's on a card (a `Style: Card` line).

### 214
things mended

### 31
volunteers

### 9
toasters beyond help

## Testimonials

Section: Testimonials

Kind words, with who said them - a `Role:` line under each name.

### Theo Marsh

Role: Brought a lamp

> I came for the lamp. I stayed for the soldering.

### Ana Okafor

Role: Owner, Corner Café

> The coffee machine works and I understand why it didn't.

### Jules Brandt

Role: Regular

> My radio plays again, and I watched every step.

## Logos

Section: Logos

A row of logos - who you've worked with, or where you've been.

![Harbour Makers](/uploads/logo-harbour-makers.png)
![Mend & Make Radio](/uploads/logo-mend-radio.png)
![Small Repairs Quarterly](/uploads/logo-small-repairs.png)
![The Library Workshop](/uploads/logo-library-workshop.png)

## Pricing

Section: Pricing

Plans side by side, with what each one includes - `Price:` and `Badge:` lines.

### A morning

Price: €45 once

- Three hours, one loaf to take home

[Book a morning](/contact)

### Four Saturdays

Price: €150 the lot
Badge: Most popular

- Starter, shaping, scoring and baking
- Your own starter to keep

[Book the course](/contact)

## Products

Section: Products

Things for sale, each with a `Price:` line and a button.

### A sourdough tin

{p("loaf2")}

Price: €18

The one I use, seasoned and ready.

[Buy it](/contact)

### A bench scraper

{p("dough")}

Price: €6

The best six euros in the kitchen.

[Buy it](/contact)

### A jar of starter

{p("starter")}

Price: €5
Badge: Sold out

A spoonful of Gerald.

## Services

Section: Services

What you offer, with a price to start from - a `From:` line.

### A design check-up

From: €400

An afternoon with your app, and a page of what to change first.

[Get in touch](/contact)

### A product, start to finish

From: €4,000

From the first sketch to the screens your developer builds from.

[Tell me about it](/contact)

## Team

Section: Team

The people behind it, each with a `Role:` line.

### Mira Castell

{p("camera")}

Role: Baker and fixer

Brings the tea and the screwdrivers.

### Theo Marsh

{p("tools")}

Role: Electrics

Has never met a lamp he couldn't rewire.

### Ana Okafor

{p("workshop")}

Role: Bicycles

Can true a wheel faster than you can say "spoke key".

## FAQ

Section: FAQ

Questions that open to their answers.

### Does it cost anything?
No - bring something to fix, and maybe a cake.

### What can't you fix?
Anything with a gas pipe, and most printers.

## Photos

Section: Photo gallery

Pictures with their captions - here, a slider that moves along by itself
(` ```gallery slider auto `).

```gallery slider auto
{photos.get("tools", "")} | The tool wall, after a busy Saturday
{photos.get("bike_blue", "")} | A bike that came in with no brakes
{photos.get("kneading", "")} | Bread for the volunteers' lunch
```

## Compare

Section: Compare

A table that compares options, with ticks and crosses.

| | Saturday | Wednesday evening |
|---|---|---|
| Bicycles | ✓ | ✗ |
| Electricals | ✓ | ✓ |
| Sewing | ✗ | ✓ |

## Steps

Section: Steps

Numbered steps, each on a card.

1. Tell us what's wrong.
2. We open it up together.
3. You take it home - working, or knowing why not.

## Milestones

Section: Milestones

Moments on a timeline.

### 2016 · The first one

Four people, two toasters, one kettle.

### 2026 · This year

Thirty-one volunteers and a waiting list for bicycles.

## Events

Section: Events

Dates coming up - `Date:` and `Place:` lines. Past ones fold away.

### Fixing lamps, a workshop

Date: {(utcnow() + timedelta(days=20)).date().isoformat()}
Place: St Olav's church hall

[Sign up](/contact)

### Bike brakes in an evening

Date: {(utcnow() + timedelta(days=41)).date().isoformat()}
Place: The repair café

## Menu

Section: Menu

Dishes and their prices.

### On the table

- Tea - any kind you like · free
- Cake - whatever someone baked · €2

## Portfolio

Section: Portfolio

Pictures of your work, each leading to its page. Or a `Tag: work` line for
everything with that tag, and `Show as: Rows` for another arrangement.

### A lamp from a bicycle

{p("bike_lamp")}

Its dynamo, its bulb and a wooden stand.

[See how](/repair-cafe)

### Corner Café

{p("coffee")}

A booking page that finally makes sense.

[See the project](/corner-cafe)

### Small Fixes

{p("notebook")}

A zine about mending the things you own.

[Read it](/small-fixes)

## Reviews

Section: Reviews

Books or things you've rated - `Author:` and `Rating:` lines.

### The Repair Manifesto

Author: Platform21
Rating: 5/5

Short, and it says it all.

### Shop Class as Soulcraft

Author: Matthew B. Crawford
Rating: 4/5

Read with oil under my fingernails.

## Uses

Section: Uses

The things you use, in groups.

### Tools

- **A soldering iron** - for lamps and radios
- **Tyre levers** - for everything with wheels

### Tea

- **A very big teapot** - twelve cups, all at once

## Opening hours

Section: Opening hours

One line for each day, with its hours.

Saturday: 10am – 2pm
Wednesday: 6pm – 9pm

## Contact details

Section: Contact details

Email: repair@example.com
Address: St Olav's church hall, Harbour Street

## Latest posts

Section: Latest posts

Count: 3

Your newest posts - a `Count:` line for how many, and `Tag:` for one tag's.

## Sign-up

Section: Sign-up

A box to get new posts by email.

One email a month, the week before.

## Contact form

Section: Contact form

A form for sending you a message.

Not sure we can fix it? Ask first.

## Call to action

Section: Call to action

### Bring something broken and a friend

A heading, a line and a button, on a card in your main colour.

[Get directions](/contact)

## Recipe facts

Section: Recipe facts

Serves, prep and cook time, side by side.

Serves: 8
Prep: 20 min
Cook: 45 min

## Ingredients

Section: Ingredients

A list readers can tick off as they shop.

- 200 g flour
- 150 g sugar
- 3 ripe bananas

## Method

Section: Method

Numbered steps with big numbers.

1. Mash the bananas and stir in the sugar.
2. Fold in the flour.
3. Bake for 45 minutes, and share it at the café.

## Interview

Section: Interview

**Sam:** What do people bring most often?

**Priya:** Toasters. Always toasters.

**Sam:** And do they get fixed?

**Priya:** Nearly all of them.

## Blocks for any text

Not sections, but in Insert too: small blocks between your paragraphs.

Pull quote: Most things that break can be fixed by someone with a little time.

Buttons: [See past ones](/repair-cafe) [Volunteer](/volunteers)

Countdown: {(utcnow() + timedelta(days=12)).date().isoformat()}

??? "What should I bring?"
    The broken thing, any parts that came off it, and its charger if it has one.
"""


ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_assets")


def _add_files():
    """The media library's sound and PDF: Corner Café's background sound
    (demo_assets/README.md for where it's from) and the bake stall's price
    list, written here rather than kept as a file."""
    os.makedirs(config.uploads_dir(), exist_ok=True)
    shutil.copyfile(os.path.join(ASSETS, "cafe-ambience.mp3"), os.path.join(config.uploads_dir(), "cafe-ambience.mp3"))
    with open(os.path.join(config.uploads_dir(), "bake-stall-price-list.pdf"), "wb") as f:
        f.write(_price_list_pdf())
    for slug, name in LOGOS.items():
        _wordmark(name, os.path.join(config.uploads_dir(), f"logo-{slug}.png"))


# Small Fixes' "As seen in" - made-up local groups, not real ones
LOGOS = {"harbour-makers": "Harbour Makers", "mend-radio": "Mend & Make Radio",
         "small-repairs": "Small Repairs Quarterly", "library-workshop": "The Library Workshop"}


def _wordmark(name, path):
    """A plain grey wordmark on a clear background - it reads in light
    and dark."""
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.load_default(size=44)
    box = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), name, font=font)
    img = Image.new("RGBA", (box[2] - box[0] + 24, box[3] - box[1] + 24), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((12 - box[0], 12 - box[1]), name, font=font, fill=(128, 128, 128, 255))
    img.save(path)


def _price_list_pdf() -> bytes:
    """A one-page PDF of the bake stall's prices - plain PDF, by hand."""
    lines = [(28, "Bake stall"), (13, "Saturday mornings at the repair cafe, until it's gone."), (13, ""),
             (16, "Bread"), (12, "Country sourdough - Gerald's finest    9.00"),
             (12, "Seeded rye - dark, dense and worth it    10.00"), (12, "Focaccia - rosemary and sea salt    7.00"),
             (13, ""), (16, "Sweet"), (12, "Cinnamon bun - still warm    4.00"), (12, "Brown butter cookie    3.00"),
             (13, ""), (16, "Drinks"), (12, "Coffee    3.50"), (12, "Tea - whatever's in the tin    2.50"),
             (13, ""), (10, "Prices in euros. Cash or card. Bring a bag, or borrow one of ours.")]
    text, y = [], 780
    for size, line in lines:
        safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        text.append(f"BT /F1 {size} Tf 72 {y} Td ({safe}) Tj ET")
        y -= size + 10
    stream = "\n".join(text).encode("latin-1")
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
               b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> "
               b"/Contents 4 0 R >>",
               b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offsets = bytearray(b"%PDF-1.4\n"), []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def build(password: str = "demo", cache: str = None):  # noqa: S107 - the demo's own sample password
    """Fills an empty data folder with the sample blog. The admin's
    password is `password`."""
    from soloblog import auth, posts, sections, settings
    from soloblog.db import get_db, run_migrations
    random.seed(7)
    run_migrations()
    cache = cache or os.environ.get("DEMO_CACHE") or os.path.join(config.data_dir(), "demo-cache")
    photos = _add_photos(cache)
    if not auth.admin_exists():
        auth.create_admin(password)
    s = {
        "setup_done": "1", "whatsnew_seen": config.VERSION, "site_title": "Mira Castell",
        "tagline": "Bread, bicycles and the slow art of finishing things.",
        "meta_description": "Mira Castell writes about sourdough, restoring an old racing bike, foggy harbours "
                            "and the small tricks that get projects finished.",
        "author_name": "Mira Castell",
        "author_bio": "Product designer, weekend baker and slow cyclist. Writing about the things I finish, "
                      "and the long, flour-dusted middle.",
        "author_avatar_url": photos.get("city_bike", ""),
        # made-up addresses - a real handle could be a real person's
        "social_mastodon": "https://example.com/mastodon", "social_instagram": "https://example.com/instagram",
        "social_github": "https://example.com/github", "social_bluesky": "https://example.com/bluesky",
        "banner_enabled": "1", "banner_heading": "Hi, I'm Mira.",
        "banner_subheading": "I bake bread, fix old bicycles and photograph the fog. This is where I write it all down.",
        "banner_button_text": "Take the tour", "banner_button_url": "/tour",
        # calm and muted, as the rest of Mira's photos are: misty hills over
        # still water, its grey sky dark enough behind the floating header to
        # read as the photo it is (a pale glare looked like a strip of page)
        "banner_image_url": photos.get("hero", ""),
        "share_image_url": photos.get("hero", ""),
        # Mira's own look: cheerful - Mint, soft pastels and round corners by
        # day and green at night (the Mint pair, themes.THEME_PAIRS), rounded
        # headings over a clean sans, a floating glass header over a bright
        # edge-to-edge banner, her posts as cards, side panels blended into
        # the page, and the tag cloud under the posts
        "theme": "cupcake", "theme_dark": "forest", "theme_mode": "auto", "visitor_theme_switching": "1",
        "font_headings": "rounded", "font_body": "system", "english_spelling": "gb",
        "section_motion": "rise",
        "header_style": "floating", "header_width": "wide", "banner_width": "full", "roll_style": "cards",
        "side_plain": "1",
        "side_tags": "under", "side_tags_where": "roll", "side_archive": "off",
        "side_author": "right", "side_author_where": "posts", "cover_width": "screen",
        "gallery_style": "masonry", "markdown_mermaid": "1", "markdown_math": "1",
        "post_shows": "breadcrumbs,progress,byline,tags,listen,reactions,share,print,support,series,related,"
                      "author,newsletter,sides",
        "reactions_style": "emoji", "contact_enabled": "1",
        "contact_intro": "Questions, bread tips and bicycle parts welcome.",
        "newsletter_mode": "builtin", "newsletter_title": "Get new posts by email",
        "newsletter_intro": "One email when I write something new. No spam, no bread puns (some bread puns).",
        "links_enabled": "1", "toc_style": "side", "relative_dates": "0",
        # the wiki is in the menu as Notes, after the repair café's page
        "nav_wiki_on": "1", "nav_wiki_order": "4", "nav_wiki_label": "Notes",
        "footer_note": "© 2026 Mira Castell · Baked fresh daily",
        # a short footer: her links, Privacy and the small print - her bio
        # is beside every post already, and Notes and the menu have the rest
        "footer_show_bio": "0", "footer_show_browse": "0",
        "footer_layout": "split", "footer_order": "socials,note,|,links,small",
        # members, and paid plans that look set up - paying itself is off in the demo (BLOCKED)
        "members_enabled": "1",
        "members_intro": "Members read the whole of Oma's interview, and every members post. It's free.",
        "stripe_key": "rk_test_demo", "members_currency": "usd", "members_price_month": "4",
        "members_price_year": "40", "members_trial_days": "7", "stripe_product_id": "prod_demo",
        "stripe_price_month": "price_demo_month", "stripe_price_year": "price_demo_year",
        "stripe_webhook_id": "we_demo", "stripe_webhook_secret": "whsec_demo",
    }
    settings.set_many(s)
    # a palette of Mira's own, made in daisyUI's theme generator (Settings >
    # Style > Colours > Custom colours) - in the pickers and the readers' menu
    from soloblog import themes
    themes.save_own(themes.parse_theme(HARBOUR)[0], "Harbour")
    _add_files()
    author = s["author_name"]
    db = get_db()
    for slug, title, tags, summary, body, f in posts_and_pages(photos):
        # every section's options written out, as Insert writes them
        body = sections.write_out_options(body)
        series = f.get("series") or ("", 0)
        posts.save_post(slug, title, author, body.strip(), tags, summary, True, bool(f.get("pinned")),
                        photos.get(f.get("cover", ""), ""), series_name=series[0], series_order=series[1],
                        parent_slug=f.get("parent", ""), pin_location=f.get("pin_location", "header"),
                        created_at=_when(f.get("days", 30)), link_url=f.get("link", ""),
                        visibility=f.get("visibility", "public"), sound=f.get("sound", ""),
                        unlisted=bool(f.get("unlisted")), comments_enabled=f.get("comments", True),
                        **_frame(f))
        # never edited since, as far as readers can tell - no "Updated" beside every date
        db.execute("UPDATE posts SET views=?, likes=?, updated_at=created_at WHERE slug=?",
                   (f.get("views", 180 if f.get("pinned") else 0), f.get("likes", 0), slug))
        if f.get("views"):
            # the last month of visits, for Stats
            for day in range(30):
                n = max(0, int(f["views"] / 120 * random.uniform(0.3, 1.8)))  # noqa: S311 - sample numbers, not security
                date = (utcnow() - timedelta(days=day)).date().isoformat()
                db.execute("INSERT OR REPLACE INTO post_views_daily (slug, day, views) VALUES (?, ?, ?)",
                           (slug, date, n))
            for reaction in ("heart", "clap", "laugh", "wow", "think"):
                if random.random() < 0.8:  # noqa: S311 - sample numbers, not security
                    db.execute("INSERT OR REPLACE INTO post_reactions (post_slug, reaction, count) VALUES (?, ?, ?)",
                               (slug, reaction, random.randint(2, max(3, f.get("likes", 10) // 3))))  # noqa: S311 - sample numbers, not security
    # Mira's projects in each arrangement, for the Portfolio card - her own
    # page follows the style a visitor tries
    from soloblog import pages
    projects = posts.load_post_body("projects")
    for key, label in pages.PORTFOLIO_STYLES.items():
        name = label.split(" — ")[0]
        # its own Show as line, among the rest in their order
        body = sections.write_out_options(re.sub(r"^Show as: .*$", f"Show as: {name}", projects, count=1, flags=re.M)
                                          .replace(_views(), _views(key)))
        posts.save_post(f"projects-{key}", f"Work - {name}", author, body, "",
                        "Mira's projects, arranged another way.", True, False, "", parent_slug="projects",
                        created_at=_when(120), unlisted=True,
                        **_frame(dict(template="landing", title_style="")))
    # the tour, and what it leads to
    for slug, title, body, summary, kw in (
            ("tour", "Tour", _tour_page(photos), "Everything this site can do, and where to see it.",
             _frame(dict(template="landing"))),
            ("templates", "Every template", _templates_page(photos),
             "Every template Soloblog has, and where to see it here.",
             dict(parent_slug="tour", **_frame(dict(template="landing", title_style="")))),
            ("styles", "Every style", _styles_page(photos), "Every starting style, to try on the whole site.",
             dict(parent_slug="tour", **_frame(dict(template="landing", title_style="")))),
            ("sections", "Every section", _sections_page(photos), "Every kind of section, in an ordinary page.",
             dict(parent_slug="tour"))):
        posts.save_post(slug, title, author, sections.write_out_options(body), "", summary, True, True, "",
                        pin_location="header", created_at=_when(398), comments_enabled=False, **kw)
        db.execute("UPDATE posts SET updated_at=created_at WHERE slug=?", (slug,))
    # the menu by what a visitor's after: her work, her shop, the repair
    # café, her notes, about her, the tour and getting in touch - and the
    # pages under each in the order they're read. Her notes are the wiki's own row (4)
    for number, slug in zip((1, 2, 3, 5, 6, 7), ("projects", "shop", "repair-cafe", "about", "tour", "contact")):
        db.execute("UPDATE posts SET pin_order=? WHERE slug=?", (number, slug))
    for group in (("corner-cafe", "work-with-me", "cv", "kind-words", "talks", "press-kit"),
                  ("small-fixes", "bread-classes", "zine-club"), ("volunteers", "bake-stall", "handbook"),
                  ("in-short", "now", "bookshelf", "uses"), ("templates", "styles", "sections")):
        for i, slug in enumerate(group):
            db.execute("UPDATE posts SET pin_order=? WHERE slug=?", (i + 1, slug))
    for day in range(30):
        date = (utcnow() - timedelta(days=day)).date().isoformat()
        for source, share in (("google.com", 60), ("mastodon.social", 25), ("news.ycombinator.com", 12),
                              ("duckduckgo.com", 18), ("bsky.app", 9)):
            db.execute("INSERT OR REPLACE INTO sources_daily (day, source, views) VALUES (?, ?, ?)",
                       (date, source, int(share * random.uniform(0.4, 1.6))))  # noqa: S311 - sample numbers, not security
    parent = None
    for slug, rows in COMMENTS.items():
        for name, body, days_ago, kind in rows:
            if kind == "author":
                db.execute("INSERT INTO comments (post_slug, author_name, body, approved, parent_id, is_author, "
                           "created_at) VALUES (?, ?, ?, 1, ?, 1, ?)", (slug, name, body, parent, _when(days_ago, 20)))
            else:
                cur = db.execute("INSERT INTO comments (post_slug, author_name, email, body, approved, confirmed_at, "
                                 "created_at) VALUES (?, ?, ?, ?, 1, ?, ?)",
                                 (slug, name, f"{name.split()[0].lower()}@example.com", body, _when(days_ago),
                                  _when(days_ago)))
                parent = cur.lastrowid
    # one waiting for approval, so the admin has something to do
    db.execute("INSERT INTO comments (post_slug, author_name, email, body, approved, confirmed_at, created_at) "
               "VALUES (?, ?, ?, ?, 0, ?, ?)", ("a-small-victory-the-bread-knife-is-back", "Oma", "oma@example.com",
                                              "I told you to label the knives.", _when(1), _when(1)))
    for i, email in enumerate(("tom@example.com", "priya@example.com", "jonas@example.com", "elin@example.com",
                               "henrik@example.com", "aiko@example.com", "liv@example.com")):
        db.execute("INSERT OR IGNORE INTO subscribers (email, token, created_at, confirmed_at) VALUES (?, ?, ?, ?)",
                   (email, f"demo-{i}", _when(200 - i * 25), _when(200 - i * 25)))
    db.commit()
    from soloblog import members
    members.sync_subscribers()
    # (email, name, status, days ago, plan) - plan: (interval, amount in pence, Stripe's status)
    for email, name, status, days, plan in (
            ("oma@example.com", "Oma", "comped", 300, None),
            ("lars@example.com", "Lars", "paid", 140, ("year", 4000, "active")),
            ("noor@example.com", "Noor", "paid", 60, ("month", 400, "active")),
            ("ben@example.com", "Ben", "paid", 33, ("month", 400, "past_due")),
            ("sofia@example.com", "Sofia", "paid", 4, ("month", 400, "trialing")),
            ("kai@example.com", "Kai", "free", 9, None)):
        m = members.add(email, name, status)
        db.execute("UPDATE members SET created_at=?, last_seen_at=? WHERE id=?", (_when(days), _when(1), m["id"]))
        if plan:
            interval, amount, state = plan
            ends = utcnow() + timedelta(days=3 if state == "trialing" else 21)
            members.update(m["id"], stripe_customer_id=f"cus_demo{m['id']}", stripe_subscription_id=f"sub_demo{m['id']}",
                           subscription_status=state, plan_interval=interval, plan_amount=amount,
                           plan_currency="usd", current_period_end=ends.isoformat(timespec="seconds"))
    db.commit()
    # the smaller copies pages ask for, made now - not by the first visitor,
    # whose page would ask for dozens at once
    from soloblog import images
    for item in images.list_uploads():
        if item["kind"] == "image":
            for width in images.SIZES:
                images.sized(item["filename"], width)
    log.info("built the sample blog: %s photos", len(photos))


# ---- demo mode (config.DEMO_MODE): the public demo

MARKER = ".soloblog-demo"
# kept from what a form sends - each could put someone else's scripts or
# settings in front of the next visitor
LOCKED_SETTINGS = {"custom_head", "custom_css", "analytics_provider", "analytics_id", "adsense_client",
                   "adsense_slot_post", "adsense_slot_roll", "comments_system", "activitypub_enabled",
                   "webmention_send", "crosspost_bluesky", "crosspost_mastodon", "search_noindex",
                   "newsletter_auto", "update_hook_url", "update_hook_token", "contact_email", "custom_head_consent",
                   "stripe_key", "members_currency", "members_price_month", "members_price_year",
                   "members_trial_days", "members_tax"}
# and every setting that's a secret, a server or an address the server
# itself calls - by its name, so a new one is locked without being listed
# here. Images and links stay: they only change what a browser loads.
_SERVER_SIDE = re.compile(r"(secret|password|token|_key$|_api_key|webhook|^smtp_|^translate_|_host$|^site_url$"
                          r"|^isso_url$|^remark42_url$|^activitypub_|^stripe_|^captcha_|^email_api)")


def _locked_by_name():
    from soloblog import settings
    return {k for k in settings.DEFAULTS if _SERVER_SIDE.search(k)}
# refused outright: the login itself, secrets, anything that reaches out
# to other servers, restores and imports
BLOCKED = ("/admin/2fa/", "/admin/passkeys/", "/admin/recovery-key", "/admin/email/test",
           "/admin/settings/password", "/admin/sessions/",
           "/forgot-password", "/reset-password", "/admin/settings/email", "/admin/settings/integrations",
           "/admin/backup/", "/admin/import",
           "/admin/media/import", "/admin/newsletter/send", "/admin/newsletter/import", "/admin/translate/",
           "/admin/update", "/admin/stats/links", "/admin/disk/", "/admin/health/verify",
           "/admin/health/refresh", "/admin/health/options", "/membership", "/account/billing",
           "/stripe/webhook", "/admin/members/import", "/join", "/signin",
           "/admin/apikeys/", "/indieauth/", "/admin/webhooks/")
BLOCKED_MESSAGE = "Not in the demo"
_booted = time.time()


def _build_id() -> str:
    """The schema and the sample blog this app would build."""
    import glob
    import hashlib
    h = hashlib.sha256()
    here = os.path.dirname(os.path.abspath(__file__))
    for path in sorted(glob.glob(os.path.join(here, "migrations", "*.sql"))) + [os.path.abspath(__file__)]:
        with open(path, "rb") as f:
            h.update(f.read())
    return h.hexdigest()[:12]


def boot():
    """On start: wipe the data folder (but not the photo cache) and build
    the sample blog again - unless the copy there is younger than
    DEMO_RESET_HOURS, as it is when a host that stops idle machines wakes
    it for a visitor (then it's ready in a second, not ten). Exits when
    the copy is due a fresh one, so the host starts it again. Refuses a
    data folder that holds anything but the demo - demo mode switched on
    by mistake mustn't wipe a blog."""
    global _booted
    data = config.data_dir()
    os.makedirs(data, exist_ok=True)
    cache = os.environ.get("DEMO_CACHE") or os.path.join(data, "demo-cache")
    # lost+found: a fresh disk's own (a Fly.io volume has one) - not a blog;
    # nor the secret the app writes there first when the host sets none
    keep = {MARKER, os.path.basename(cache), "lost+found", os.path.basename(config.SECRET_FILE)}
    entries = [e for e in os.listdir(data) if e not in keep]
    if entries and not os.path.exists(os.path.join(data, MARKER)):
        raise RuntimeError(f"DEMO_MODE is on, but {data} holds a blog that isn't the demo. Demo mode wipes its "
                           "data folder on every start, so it won't touch this one: turn DEMO_MODE off, or "
                           "point DATA_DIR at an empty folder.")
    marker = os.path.join(data, MARKER)
    # a copy made by an older build is rebuilt - its database may miss a
    # column, and its sample posts the latest changes
    fresh = entries and os.path.exists(marker) and _build_id() in Path(marker).read_text(encoding="utf-8") and \
        time.time() - os.path.getmtime(marker) < config.DEMO_RESET_HOURS * 3600
    if not fresh:
        for entry in entries:
            path = os.path.join(data, entry)
            shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
        with open(marker, "w", encoding="utf-8") as f:
            f.write("The Soloblog demo: this folder is wiped and rebuilt every few hours.\n"
                    f"build {_build_id()}\n")
        build(config.DEMO_PASSWORD, cache)
    # the visitors' own copies (Sandbox) go with every start - which
    # visitor had which isn't kept
    shutil.rmtree(os.path.join(data, VISITORS), ignore_errors=True)
    # the copy's age, not this start's, decides when it's reset
    _booted = os.path.getmtime(marker)

    def reset_later():
        time.sleep(max(0, _booted + config.DEMO_RESET_HOURS * 3600 - time.time()))
        log.info("time for a fresh copy - exiting so the host restarts it")
        os._exit(3)
    threading.Thread(target=reset_later, daemon=True).start()


def minutes_left() -> int:
    return max(0, int((_booted + config.DEMO_RESET_HOURS * 3600 - time.time()) // 60))


def blocked(path: str) -> bool:
    return any(path == b or path.startswith(b) for b in BLOCKED)


class DemoGuard:
    """Refuses the BLOCKED requests with a message where the result
    would have shown: the status beside the buttons (htmx), or the page
    it came from."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["method"] == "POST" and blocked(scope["path"]):
            from urllib.parse import urlsplit
            from starlette.responses import HTMLResponse
            from soloblog.guards import status_redirect
            headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
            if headers.get("hx-request"):
                response = HTMLResponse(f'<span id="save-status" class="text-xs text-error">{BLOCKED_MESSAGE}</span>')
            else:
                # the page it came from, tab and all (Settings > Backup is
                # ?tab=backup) - its path alone landed somewhere else
                came = urlsplit(headers.get("referer") or "/admin")
                kept = "&".join(q for q in came.query.split("&") if q and not q.startswith(("toast", "undo")))
                back = (came.path or "/admin") + (f"?{kept}" if kept else "")
                response = status_redirect(back, BLOCKED_MESSAGE, "error")
            return await response(scope, receive, send)
        return await self.app(scope, receive, send)


# Everything a visitor changes - a post, a page, a photo, a comment, a
# setting - goes into their own copy of the site, made the first time
# they change anything (or open the admin) and kept until the demo
# resets. Nothing one visitor writes reaches anyone else, so there's
# nothing to deface. The copy is picked by a cookie of its own, outside
# the session, so every part of a request - the middleware too - sees it.
VISITORS = "visitors"
VISITOR_COOKIE = "soloblog_demo"
MAX_VISITORS = 30          # copies kept; the longest unused goes first
MAX_NEW_PER_MINUTE = 20    # copies made - a script can't keep the disk busy
_ID = re.compile(r"^[0-9a-f]{32}$")
_copies = {}               # visitor id -> their copy's folder
_made = []                 # when copies were made, in the last minute
_copy_lock = threading.Lock()


def _cookie(scope):
    for k, v in scope.get("headers", []):
        if k == b"cookie":
            for part in v.decode("latin-1").split(";"):
                name, _, value = part.strip().partition("=")
                if name == VISITOR_COOKIE and _ID.match(value):
                    return value
    return None


def _wants_copy(scope) -> bool:
    """A change, or the admin with a session to sign in with - a
    crawler asking for /admin gets no copy."""
    if scope["method"] not in ("GET", "HEAD", "OPTIONS"):
        return True
    has_session = any(k == b"cookie" and b"blog_session=" in v for k, v in scope.get("headers", []))
    return scope["path"].startswith("/admin") and has_session


def _new_copy(visitor):
    """The site as it is now - its database, posts and uploads (not their
    smaller copies, made again when asked for) - into a folder of the
    visitor's own. A fresh name each time: a connection still open to an
    old copy is never mistaken for the new one."""
    import secrets
    import sqlite3
    from soloblog import db
    with _copy_lock:
        now = time.time()
        _made[:] = [t for t in _made if now - t < 60]
        if len(_made) >= MAX_NEW_PER_MINUTE:
            return None
        _made.append(now)
        root = os.path.join(config.data_dir(), VISITORS)
        dest = os.path.join(root, f"{visitor}-{secrets.token_hex(4)}")
        os.makedirs(dest)
        target = sqlite3.connect(os.path.join(dest, "blog.db"))
        db.get_db().backup(target)
        target.close()
        for sub in ("posts", "uploads"):
            if os.path.isdir(os.path.join(config.data_dir(), sub)):
                shutil.copytree(os.path.join(config.data_dir(), sub), os.path.join(dest, sub),
                                ignore=shutil.ignore_patterns("_sizes"))
        _copies[visitor] = dest
        # the longest unused go (their mtime is touched as they're used)
        while len(_copies) > MAX_VISITORS:
            oldest = min(_copies, key=lambda v: os.path.getmtime(_copies[v]))
            gone = _copies.pop(oldest)
            db.forget_visitor(os.path.join(gone, "blog.db"))
            shutil.rmtree(gone, ignore_errors=True)
        return dest


def _touch(path):
    try:
        if time.time() - os.path.getmtime(path) > 60:
            os.utime(path)
    except OSError:
        pass


class Sandbox:
    """Runs each request of a visitor who has their own copy of the site
    against it (config.VISITOR_DIR), making the copy on their first
    change."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        visitor = _cookie(scope)
        path = _copies.get(visitor) if visitor else None
        new = None
        if path is None and _wants_copy(scope):
            import anyio
            import secrets
            visitor = visitor or secrets.token_hex(16)
            path = await anyio.to_thread.run_sync(_new_copy, visitor)
            if path is None:
                from starlette.responses import PlainTextResponse
                return await PlainTextResponse("The demo is busy - try again in a minute", status_code=503,
                                               headers={"Retry-After": "60"})(scope, receive, send)
            new = visitor
        if path is None:
            return await self.app(scope, receive, send)
        _touch(path)

        async def send_with_cookie(message):
            if new and message["type"] == "http.response.start":
                secure = "; Secure" if config.BASE_URL.startswith("https") else ""
                cookie = (f"{VISITOR_COOKIE}={new}; Path=/; HttpOnly; SameSite=Lax; "
                          f"Max-Age={int(config.DEMO_RESET_HOURS * 3600)}{secure}")
                message = {**message, "headers": list(message.get("headers", [])) +
                           [(b"set-cookie", cookie.encode("latin-1"))]}
            await send(message)
        token = config.VISITOR_DIR.set(path)
        try:
            await self.app(scope, receive, send_with_cookie)
        finally:
            config.VISITOR_DIR.reset(token)
