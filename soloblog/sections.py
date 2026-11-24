"""Sections: the parts of a page. A ## with a "Section: Pricing" line under
it shows its ### items as that kind of part, in any post or page.

REGISTRY holds everything about each kind in one place - the words people
write after "Section:", what it is, its icon, search words, the Key: lines
it takes (OPTIONS), its sample words and which function draws it. Insert,
the / menu, the editor's Help and highlighting, the lines left out of
excerpts and feeds, and the page itself all read it, so a new kind is one
entry here, its render function and its tests (docs/DEVELOPMENT.md >
Adding a section).

Every Key: line takes Default: "follow the site" (or the section's own
usual). It means exactly what a missing line means.
"""
import re

from soloblog import editor_icons

DEFAULT = "Default"
# the Key: lines every section takes, first in what Insert writes
SHARED = ("Width", "Style", "Heading", "Space", "Appear")
# a line inside an item that the editor colours like the section's own lines
ITEM_KEYS = ("Icon",)


def is_default(value) -> bool:
    return str(value).strip().lower() == DEFAULT.lower()


def _space_values():
    from soloblog.pages import SPACINGS
    words = {"small": ("Less room around it", "fold-vertical"), "medium": ("The usual room", "align-vertical-space-around"),
             "large": ("More room around it", "unfold-vertical")}
    return tuple((key, label, *words[key]) for key, label in SPACINGS.items())


def _appear_values():
    from soloblog.pages import SECTION_MOTIONS
    words = {"fade": ("Fades in", "blend"), "rise": ("Rises into place", "arrow-up-from-line"),
             "zoom": ("Grows into place", "zoom-in"), "slide": ("Slides in from the left", "arrow-right-from-line"),
             "slide-right": ("Slides in from the right", "arrow-left-from-line"),
             "alternate": ("Slides in from each side, in turn", "arrow-left-right"),
             "blur": ("Comes into focus", "focus"), "tilt": ("Tilts up into place", "rotate-3d"),
             "none": ("Is there from the start", "ban")}
    return tuple((key, label, *words[key]) for key, label in SECTION_MOTIONS.items())


def _show_as_values():
    from soloblog.pages import PORTFOLIO_STYLES
    icons = {"grid": "grid-2x2", "masonry": "layout-dashboard", "rows": "layout-grid",
             "screen": "maximize-2", "sideways": "panels-top-left"}
    return tuple((key, label.split(" — ")[0], label.split(" — ")[1].capitalize(), icons[key])
                 for key, label in PORTFOLIO_STYLES.items())


# The Key: lines. type: "choice" (values: (key, label, what it does, icon)),
# "number" (a whole number from limit, with suggestions), "tag" (any of
# the site's tags) or "series" (any of the site's series). aliases: other spellings the page still reads.
# default: what Default does, as the / menu says it.
OPTIONS = {
    "Width": {"about": "How wide it runs", "default": "Follow the site", "type": "choice",
              "values": (("column", "Column", "As wide as the text", "shrink"),
                         ("wide", "Wide", "Out to the side panels", "expand"),
                         ("full", "Full", "Edge to edge", "maximize-2")),
              "aliases": {}},
    "Style": {"about": "How it's set apart", "default": "No card or cover", "type": "choice",
              "values": (("card", "Card", "Set apart on a card", "rectangle-horizontal"),),
              "aliases": {}},
    "Heading": {"about": "Where its heading sits", "default": "Follow the site", "type": "choice",
                "values": (("left", "Left", "On the left, with the text", "align-left"),
                           ("centre", "Centred", "In the middle, with its first words", "align-center")),
                "aliases": {"center": "centre", "centered": "centre"}},
    "Space": {"about": "How much room is around it", "default": "Follow the page", "type": "choice",
              "values": _space_values, "aliases": {}},
    "Appear": {"about": "How it comes into view", "default": "Follow the page", "type": "choice",
               "values": _appear_values, "aliases": {}},
    "Show as": {"about": "How the images are arranged", "default": "Follow the site", "type": "choice",
                "values": _show_as_values, "aliases": {}},
    "Count": {"about": "How many posts", "default": "Three posts", "type": "number",
              "suggest": (3, 6, 9, 12), "limit": (1, 12), "unit": "posts"},
    "Tag": {"about": "Only posts with this tag", "default": "Any tag", "type": "tag"},
    "Series": {"about": "Which series", "default": "This page's own series", "type": "series"},
    "First paragraph": {"about": "How the opening paragraph looks", "default": "Big", "type": "choice",
                        "values": (("big", "Big", "Large, like a magazine's opening", "a-large-small"),
                                   ("normal", "Normal", "The same size as the rest", "pilcrow")),
                        "aliases": {}},
    "Pictures together": {"about": "How images written together are placed", "default": "Side by side",
                          "type": "choice",
                          "values": (("side", "Side by side", "In a row, the same height", "columns-2"),
                                     ("stack", "One under another", "Each one across the page",
                                      "rectangle-horizontal")),
                          "aliases": {}},
    "A line after a picture": {"about": "Where a short line straight after an image goes", "default": "Beside it",
                               "type": "choice",
                               "values": (("beside", "Beside it", "Next to the image, sides taking turns",
                                           "layout-panel-left"),
                                          ("under", "Under it", "Under the image, like the rest", "image-up")),
                               "aliases": {}},
}

# Style: Cover, offered only by the kinds made with cover=True
COVER = ("cover", "Cover", "Its words over its image, across the page", "image")


def _kind(key, names, about, icon, words, heading, body="", options=None, width="", draw=None, styles=(),
          own_heading=False, cover=False):
    """names: what may follow "Section:", the first is its label. options:
    {name: its own words for what it does here, "" for the option's own}
    after Width and Style. width: how wide it runs with no Width line. draw: the function in
    pages.py that draws it (_render_ and its key, unless named). styles: Style
    values only this kind has, (key, label, what it does, icon) like the shared
    ones. own_heading: it draws its own ##, so the page leaves it out. cover: it
    takes Style: Cover - a section where words over a picture means something."""
    return {"names": names, "label": names[0], "about": about, "icon": icon, "words": words,
            "heading": heading, "body": body, "options": options or {}, "width": width,
            "draw": f"_render_{key}" if draw is None else draw, "styles": styles, "own_heading": own_heading,
            "cover": cover}


# In the order Insert lists them
REGISTRY = {
    "picture_and_text": _kind("picture_and_text", ("Picture and text", "Picture"), "An image beside its words", "layout-panel-left",
                  ("image", "photo", "side"), "A heading",
                  "![An image](https://)\n\nA few words about it.", cover=True),
    "numbers": _kind("numbers", ("Numbers", "Stats"), "Big figures, like 10,000 customers", "trending-up",
                     ("stats", "figures"), "In numbers",
                     "### 10,000\nhappy customers\n\n### 4.9 ★\naverage rating"),
    "testimonials": _kind("testimonials", ("Testimonials",), "Kind words, with who said them",
                          "message-square-quote", ("reviews", "quotes"), "What people say",
                          "### Their name\n\nRole: What they do\n\n> What they said."),
    "logos": _kind("logos", ("Logos",), "A row of logos - as seen in, trusted by", "award",
                   ("brands", "press"), "As seen in", "![A name](https://)\n![Another](https://)"),
    "pricing": _kind("pricing", ("Pricing", "Plans"), "Plans as cards, one picked out", "badge-dollar-sign",
                     ("plans", "prices"), "Plans",
                     "### Basic\n\nPrice: US$10 a month\n\n- What's included\n\n[Choose Basic](https://)\n\n"
                     "### Pro\n\nPrice: US$20 a month\nBadge: Most popular\n\n- Everything in Basic\n- And more\n\n"
                     "[Choose Pro](https://)"),
    "products": _kind("products", ("Products", "Shop"), "Things for sale, each with a button", "shopping-bag",
                  ("shop", "sell"), "Shop",
                  "### A product\n\n![An image](https://)\n\nPrice: US$25\n\nWhat it is.\n\n[Buy](https://)"),
    "services": _kind("services", ("Services",), "What you offer, with a starting price", "briefcase",
                      ("offer", "hire"), "Services",
                      "### A service\n\nFrom: US$400\n\nWhat's included.\n\n[Get in touch](/contact)"),
    "team": _kind("team", ("Team", "People"), "The people, with a photo and a line", "users",
                  ("people", "staff"), "The team",
                  "### A name\n\n![Their photo](https://)\n\nRole: What they do\n\nA line about them."),
    "faq": _kind("faq", ("FAQ", "Questions"), "Questions that open to their answers", "message-circle-question",
                 ("questions", "answers"), "Questions",
                 "### A question?\nIts answer.\n\n### Another question?\nIts answer."),
    "gallery": _kind("gallery", ("Photo gallery",), "A section of images, with its own heading", "layout-grid",
                     ("gallery", "photos", "images", "pictures"), "Photos",
                     "```gallery\n/uploads/a-photo.webp\n/uploads/another.webp\n```"),
    "cta": _kind("cta", ("Call to action", "CTA"), "One line and a button, in a band", "megaphone",
                 ("button", "call to action"), "Ready to start?",
                 "One line about why.\n\n[Get started](https://)", cover=True),
    "features": _kind("features", ("Features",), "Short points with an icon, side by side", "sparkles",
                      ("benefits", "icons", "grid"), "Why it's good",
                      "### Real bread\n\nIcon: leaf\nA line about it.\n\n"
                      "### Ready by nine\n\nIcon: clock\nA line about it.\n\n"
                      "### Delivered by bike\n\nIcon: truck\nA line about it."),
    "columns": _kind("columns", ("Columns",), "Text in columns, side by side", "columns-3",
                     ("side by side", "two columns"), "Two sides",
                     "### The first\n\nSome words.\n\n### The second\n\nSome more."),
    "signup": _kind("signup", ("Sign-up", "Signup", "Newsletter"), "Your newsletter's sign-up box", "mail",
                    ("newsletter", "subscribe", "email"), "Get the next one",
                    "A line about what they'll get."),
    "contact": _kind("contact", ("Contact form", "Contact"), "Your contact form", "send",
                     ("form", "message"), "Get in touch", "A line about what to write about."),
    "latest": _kind("latest", ("Latest posts", "Posts"), "Your newest posts, as cards", "newspaper",
                    ("recent", "newest", "posts"), "Lately",
                    options={"Count": "", "Tag": ""}),
    "compare": _kind("compare", ("Compare", "Comparison"), "A table of options, with ticks", "table-properties",
                     ("comparison", "table", "versus"), "Which one?",
                     "| | Basic | Pro |\n|---|---|---|\n| Every post | ✓ | ✓ |\n| Members-only posts | ✗ | ✓ |"),
    "steps": _kind("steps", ("Steps", "How it works"), "Numbered steps - how it works", "footprints",
                   ("how it works", "process", "numbered"), "How it works",
                   "1. The first step.\n2. The next.\n3. The last."),
    "milestones": _kind("milestones", ("Milestones", "Timeline"), "Dated entries on a line", "milestone",
                      ("timeline", "history", "dates"), "So far",
                      "### 2024 · It began\n\nA line about it.\n\n### 2026 · Where it is now\n\nA line about it."),
    "events": _kind("events", ("Events", "Talks"), "Events to come, then past ones", "calendar-check",
                    ("talks", "dates", "calendar"), "Coming up",
                    "### A talk\n\nDate: 12 March 2027\nPlace: Where it is\n\n[Details](https://)"),
    "menu": _kind("menu", ("Menu",), "Dishes with prices, lined up", "soup", ("food", "dishes", "prices"),
                  "On the menu", "### Breakfast\n\n- Porridge - oats, honey · $7\n- Toast - sourdough · $5"),
    "portfolio": _kind("portfolio", ("Portfolio", "Projects"), "Images of your work, each leading to its page",
                      "folder-open", ("portfolio", "work"), "Recent work",
                      "### A project\n\n![An image](https://)\n\nWhat it is.\n\n[See the project](https://)",
                      options={"Show as": "", "Tag": "Adds every post with this tag"}),
    "reviews": _kind("reviews", ("Reviews", "Books"), "Books or films, with stars", "star",
                       ("books", "films", "rating"), "Read lately",
                       "### A book\n\nAuthor: Their name\nRating: 4/5\n\nA line about it."),
    "uses": _kind("uses", ("Uses",), "Things you use, and what for", "hammer", ("tools", "gear", "setup"),
                  "What I use", "### At the desk\n\n- **A thing** - what it's for\n- **Another** - what it's for"),
    "hours": _kind("hours", ("Opening hours", "Hours"), "When you're open, as a table", "clock-3",
                   ("opening", "open", "times"), "Opening hours",
                   "Monday: 9am – 5pm\nTuesday: 9am – 5pm\nSaturday: Closed"),
    "details": _kind("details", ("Contact details",), "Buttons to call, write or find you", "contact",
                     ("phone", "address", "email", "map"), "Find us",
                     "Phone: +1 555 0100\nEmail: hello@example.com\nAddress: 1 High Street"),
    "resume": _kind("resume", ("Resume", "CV"), "Jobs or schooling, each with its dates", "history",
                    ("cv", "experience", "education", "work history"), "Experience",
                    "### Designer, Acme · 2021 – 2024\n\nA line about what you did.\n\n"
                    "### Assistant, Studio North · 2018 – 2021\n\nA line about what you did.",
                    draw="_render_resume_part"),
    "skills": _kind("skills", ("Skills",), "Short items, as small badges", "wand-sparkles",
                    ("badges", "abilities", "tags"), "Skills", "- Baking\n- Photography\n- Public speaking\n- Spanish"),
    "profile": _kind("profile", ("Profile",), "A photo, a big line about you and your links", "user-round",
                     ("about me", "bio", "introduction", "homepage"), "Your name",
                     "![A photo of you](https://)\n\nOne line about who you are.\n\n"
                     "A couple of sentences about what you do.\n\n"
                     "[Writing](/blog) [About](/about) [Email me](mailto:hello@example.com)",
                     draw="_render_profile_part", own_heading=True),
    "bios": _kind("bios", ("Bios", "Media kit"), "Bios to copy, and photos to download", "pen-line",
                  ("press", "media kit", "about"), "For the press",
                  "### Short bio\n\nTwo sentences to paste into an introduction.\n\n"
                  "### Long bio\n\nA few sentences about who you are and what you do.\n\n"
                  "### Photos\n\n![A photo](https://)\n![Another photo](https://)"),
    "project_facts": _kind("project_facts", ("Project facts",), "Client, year, role - a strip of facts", "folder-kanban",
                           ("client", "year", "role", "details"), "At a glance",
                           "Client: Their name\nYear: 2026\nRole: What you did"),
    "photo_story": _kind("photo_story", ("Photo story",), "Images and words laid out like a magazine", "book-open",
                         ("magazine", "pictures", "story", "project"), "The story",
                         "A big opening paragraph that sets the scene.\n\n![An image](https://)\n\n"
                         "A short line that sits beside the image.\n\n> A line worth pulling out.\n\n"
                         "![An image](https://)\n![Another image](https://)",
                         options={"First paragraph": "", "Pictures together": "", "A line after a picture": ""},
                         width="wide"),
    "story": _kind("story", ("Story", "Scroll story"), "Images that change as the words scroll", "gallery-vertical-end",
                   ("scroll", "scrolling", "pictures", "steps", "fullscreen", "tour"), "Take a look around",
                   "### Start here\n\n![An image for this step](https://)\n\n"
                   "Readers see this image while they read these words.\n\n"
                   "### Then the next\n\n![An image for the next step](https://)\n\n"
                   "The image changes as they scroll to these words.\n\n"
                   "### And the last\n\n![An image for the last step](https://)\n\n"
                   "Add as many steps as you like - an image and a few words each.", width="full"),
    # wider than the column: a picture with words over it, and tiles
    "hero": _kind("hero", ("Hero",), "A big heading and a button over an image", "rectangle-horizontal",
                  ("banner", "big", "header", "cover"), "A big heading",
                  "![An image](https://)\n\nA line about it.\n\n[Find out more](https://)",
                  width="full", cover=True,
                  styles=(("window", "Window", "The image framed like a window, as a launch page opens",
                           "panels-top-left"),)),
    "bento": _kind("bento", ("Bento grid", "Bento"), "Tiles of different sizes, the first big", "grid-2x2",
                   ("tiles", "grid", "mosaic"), "What's inside",
                   "### The main thing\n\n![A picture](https://)\n\nA line about it.\n\n### Another\n\nA line.\n\n"
                   "### And another\n\nA line.\n\n### One more\n\nA line.\n\n### The last\n\nA line.",
                   width="wide"),
    "recipe_facts": _kind("recipe_facts", ("Recipe facts",), "Serves, prep and cook time, side by side", "clock",
                          ("serves", "prep", "cook", "time", "recipe"), "At a glance",
                          "Serves: 4\nPrep: 15 min\nCook: 30 min"),
    "ingredients": _kind("ingredients", ("Ingredients",), "A list readers can tick off", "list-todo",
                         ("recipe", "shopping", "list"), "Ingredients",
                         "- 400 g tomatoes\n- 1 onion\n- A pinch of salt"),
    "method": _kind("method", ("Method", "Instructions", "Directions"), "Numbered steps with big numbers",
                    "utensils", ("recipe", "steps", "cook"), "Method",
                    "1. Chop the onion.\n2. Cook it with the tomatoes.\n3. Season and serve."),
    "interview": _kind("interview", ("Interview",), "Questions and answers as a chat", "message-circle",
                       ("q&a", "chat", "conversation", "speaker"), "The conversation",
                       "**Sam:** What got you started?\n\n**Alex:** A broken bike and a free weekend.\n\n"
                       "**Sam:** What would you tell someone starting out?\n\n**Alex:** Start small.",
                       draw="_render_interview_part"),
    "contents": _kind("contents", ("Contents", "Parts"), "A series' parts, in order, each a link", "map",
                      ("series", "parts", "guide", "index"), "In this series", options={"Series": ""}),
    "previous_next": _kind("previous_next", ("Previous and next",), "The pages before and after this one, as images",
                           "refresh-cw", ("next", "previous", "more", "keep reading"), "Keep reading"),
}
# every name people may write after "Section:", lower case -> its kind
NAMES = {name.lower(): key for key, entry in REGISTRY.items() for name in entry["names"]}


def option_names(key) -> tuple:
    """The Key: lines a kind takes, in the order Insert writes them: Width,
    Style, Heading, Space, Appear, then its own."""
    return (*SHARED, *REGISTRY[key]["options"])


def values(name, kind="") -> tuple:
    """A choice's values: (key, label, what it does, icon name). Style also
    has a kind's own after the shared ones - kind "" is the shared ones
    alone, None every kind's."""
    found = OPTIONS[name]["values"]
    found = found() if callable(found) else found
    if name != "Style" or kind == "":
        return found
    mine = [(k, entry) for k, entry in REGISTRY.items() if kind in (None, k)]
    return (*found, *([COVER] if any(entry["cover"] for _, entry in mine) else []),
            *(v for _, entry in mine for v in entry["styles"]))


def cover_labels() -> list:
    """The labels of the sections that take Style: Cover."""
    return [entry["label"] for entry in REGISTRY.values() if entry["cover"]]


def accepted(name, kind=None) -> set:
    """What a line may say after "Width:" - lower case, Default too. A
    number or a tag is checked another way (accepts). kind: whose own Style
    values count too - "" for none, None for every kind's."""
    option = OPTIONS[name]
    if option["type"] != "choice":
        return {DEFAULT.lower()}
    return {DEFAULT.lower(), *option["aliases"],
            *(w for key, label, *_ in values(name, kind) for w in (key, label.lower()))}


def accepts(name, value, kind=None) -> bool:
    """Whether a value is one the page can use (a tag is any word). With no
    kind, one any kind can use."""
    value = str(value).strip().lower()
    option = OPTIONS[name]
    if is_default(value):
        return True
    if option["type"] == "number":
        return value.isdigit() and option["limit"][0] <= int(value) <= option["limit"][1]
    return bool(value) if option["type"] in ("tag", "series") else value in accepted(name, kind)


def pick(name, value, kind=None) -> str:
    """The key of the choice a line says ("Side by side" -> "side"), "" for
    Default, a missing line or anything the page can't use."""
    value = str(value).strip().lower()
    option = OPTIONS[name]
    value = option["aliases"].get(value, value)
    for key, label, *_ in values(name, kind):
        if value in (key, label.lower()):
            return key
    return ""


def note(name, kind="") -> str:
    """What the editor says under a value the page can't use (a tag is any
    word, so none)."""
    option = OPTIONS[name]
    if option["type"] in ("tag", "series"):
        return ""
    if option["type"] == "number":
        return f"{name} is a number from {option['limit'][0]} to {option['limit'][1]}, or {DEFAULT}"
    labels = [label for _, label, *_ in values(name, kind)] + [DEFAULT]
    return f"{name} can be {', '.join(labels[:-1])} or {labels[-1]}"


def markdown(key, given=None, heading=None, body=None) -> str:
    """The markdown that adds a section: its heading, its Section: line,
    every Key: line it takes - Default unless `given` ({name: value}) says
    otherwise - and its sample words. A template gives its own heading and
    body."""
    entry, given = REGISTRY[key], given or {}
    for name, value in given.items():
        if name not in option_names(key) or not accepts(name, value, key):
            raise ValueError(f"{name}: {value} is not an option of {entry['label']}")
    heading = entry["heading"] if heading is None else heading
    body = entry["body"] if body is None else body.strip("\n")
    lines = [f"Section: {entry['label']}", *(f"{name}: {given.get(name, DEFAULT)}" for name in option_names(key))]
    return f"## {heading}\n\n" + "\n".join(lines) + (f"\n\n{body}" if body else "")


_OWN_LINE = re.compile(r"^([A-Za-z][A-Za-z ]{0,30}):[ \t]*(.*)$")


def write_out_options(text: str) -> str:
    """Markdown with every section's options written out under its Section:
    line, in order - what a line already says kept, the rest Default - as
    a section inserted today has them. For pages written before."""
    lines, out, i = text.split("\n"), [], 0
    while i < len(lines):
        out.append(lines[i])
        found = re.match(r"^Section:[ \t]*(.+?)\s*$", lines[i])
        kind = NAMES.get(found.group(1).strip().lower()) if found else None
        i += 1
        if not kind:
            continue
        names = {n.lower(): n for n in option_names(kind)}
        said = {}
        while i < len(lines) and (own := _OWN_LINE.match(lines[i])) and own.group(1).strip().lower() in names:
            said[names[own.group(1).strip().lower()]] = own.group(2).strip()
            i += 1
        out.extend(f"{n}: {said.get(n) or DEFAULT}" for n in option_names(kind))
    return "\n".join(out)


def search_words(key) -> tuple:
    """What the / menu finds a kind by, besides its label."""
    entry = REGISTRY[key]
    return tuple(dict.fromkeys(("section", *(n.lower() for n in entry["names"]), *entry["words"])))


def section_kind(body):
    """(kind, body without its "Section:" line) when a ## section says what
    kind it is ("Section: Pricing") - None for a plain ## or a misspelt
    kind, which stays text (and its line in view)."""
    from soloblog.pages import facts, text_of
    pairs, rest = facts(body.strip())
    if not pairs or pairs[0][0].lower() != "section":
        return None
    kind = NAMES.get(text_of(pairs[0][1]).strip().lower())
    if not kind:
        return None
    # lines written straight under it ("Count: 3") are the section's own
    others = "<br>\n".join(f"{k}: {v}" for k, v in pairs[1:])
    return kind, (f"<p>{others}</p>\n" if others else "") + rest


def take_line(html, key):
    """(its value, lower case - "" for Default - and the html without the
    line) for a "Key: value" line among a section's first lines, the key
    in lower case; ("", html) if none."""
    from soloblog.pages import facts, text_of
    pairs, rest = facts(html)
    found = next((text_of(v).strip().lower() for k, v in pairs if k.lower() == key), "")
    if not found:
        return "", html
    others = "<br>\n".join(f"{k}: {v}" for k, v in pairs if k.lower() != key)
    return ("" if is_default(found) else found), (f"<p>{others}</p>\n" if others else "") + rest


def section_width(html):
    """A section's "Width:" - Column, Wide or Full, the names the cover and
    the header use ("" for Default)."""
    width, html = take_line(html, "width")
    return OPTIONS["Width"]["aliases"].get(width, width), html


# What an excerpt, a feed and an email leave out: a paragraph of only a
# section's own lines (Section:, then its Key: lines), each with a value
# the page knows - any other line is someone's words.
LINE_KEYS = ("Section", *OPTIONS)
LINE_KEYS_RE = "|".join(re.escape(k) for k in LINE_KEYS)


SECTION_PARAGRAPH = re.compile(r"<p>\s*(Section:.*?)</p>\s*", re.I | re.S)


def split_own(inner_html: str):
    """(the section's own lines, the other lines) of a paragraph that starts
    with a "Section:" line for a kind the page knows - its Width: and the
    like, and lines of its items (Project facts' Client: and Year:) written
    straight under it. ([], []) for any other paragraph."""
    lines = [line for line in re.split(r"<br\s*/?>|\n", inner_html) if line.strip()]
    first = lines[0].partition(":") if lines else ("", "", "")
    if first[0].strip().lower() != "section" or first[2].strip().lower() not in NAMES:
        return [], []
    taken = [n.lower() for n in option_names(NAMES[first[2].strip().lower()])]
    own, rest = [], []
    for line in lines:
        key, _, value = line.partition(":")
        name = next((n for n in OPTIONS if n.lower() == key.strip().lower()), None)
        mine = key.strip().lower() == "section" or (name and name.lower() in taken
                                                           and accepts(name, value, NAMES[first[2].strip().lower()]))
        (own if mine else rest).append(line)
    return own, rest


def only_own_lines(lines: str) -> bool:
    """Every line a section's own. A count or a tag is only one beside a
    Section: line - on its own it's more likely someone's words."""
    found = [line.partition(":") for line in re.split(r"<br\s*/?>|\n", lines) if line.strip()]
    has_section = any(key.strip().lower() == "section" for key, *_ in found)
    for key, _, value in found:
        key, value = key.strip().lower(), value.strip()
        if key == "section":
            ok = value.lower() in NAMES
        else:
            name = next((n for n in OPTIONS if n.lower() == key), None)
            ok = bool(name) and accepts(name, value) and (OPTIONS[name]["type"] == "choice" or has_section
                                                          or is_default(value))
        if not ok:
            return False
    return True


def editor_data() -> dict:
    """The registry for the editor's scripts (slash_menu.js, the mode in
    editor_init.js): every kind by its names, every option with its values
    and what Default does. Built only from the lists above."""
    icon = editor_icons.svg
    options = {}
    for name, option in OPTIONS.items():
        spec = {"about": option["about"], "default": option["default"], "type": option["type"],
                "accepts": sorted(accepted(name, "")), "note": note(name)}
        if option["type"] == "choice":
            spec["values"] = [[key, label, about, icon(svg)] for key, label, about, svg in values(name, "")]
            spec["aliases"] = option["aliases"]
        if option["type"] == "number":
            spec["suggest"] = list(option["suggest"])
            spec["limit"] = list(option["limit"])
            spec["unit"] = option["unit"]
        options[name] = spec
    kinds = {key: {"label": entry["label"], "options": list(option_names(key)),
                   "about": {name: words for name, words in entry["options"].items() if words},
                   "width": entry["width"],
                   # the Style values beyond the shared ones (Cover, its own), and what it says under one it can't use
                   "styles": [[k, label, about, icon(svg)] for k, label, about, svg in values("Style", key)
                              if (k, label, about, svg) not in OPTIONS["Style"]["values"]],
                   "styleNote": note("Style", key), "styleAccepts": sorted(accepted("Style", key))}
             for key, entry in REGISTRY.items()}
    return {"kinds": NAMES, "sections": kinds, "options": options, "shared": list(SHARED),
            "lineKeys": [*OPTIONS, *ITEM_KEYS], "defaultWord": DEFAULT, "reserved": f"{DEFAULT} is a reserved word"}
