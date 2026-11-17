import json
import os
import re
from contextlib import contextmanager
from contextvars import ContextVar

# The words visitors see - "Comments", "Share", "2 min read", dates - in
# the site's language (Settings > Site > Languages), from locales/<code>.json:
# {"English text": "translation", ...}. Anything a file leaves out stays
# in English, so a language can be added or finished one line at a time.
# The admin stays in English.

_here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locales")
_current = ContextVar("lang", default="en")
_english = ContextVar("english", default="us")
_locales = {}

# An English site's spelling (Settings > Site > Languages): the words
# visitors see, dates, <html lang>, and the admin's own wording.
# locales/english/<code>.json holds what differs from the text in the
# code; Australian spelling is British, with its own <html lang>.
ENGLISH = {"us": "American - color, center", "gb": "British - colour, centre",
           "au": "Australian - colour, centre"}
ENGLISH_LANG = {"us": "en-US", "gb": "en-GB", "au": "en-AU"}


def _load(lang: str) -> dict:
    if lang not in _locales:
        try:
            with open(os.path.join(_here, f"{lang}.json"), encoding="utf-8") as f:
                _locales[lang] = json.load(f)
        except (OSError, ValueError):
            _locales[lang] = {}
    return _locales[lang]


def use(lang: str, english: str = "us"):
    """The language for the rest of this request, and an English one's
    spelling."""
    _current.set(lang or "en")
    _english.set(english if english in ENGLISH else "us")


@contextmanager
def in_site_language():
    """For an email to a visitor: the site's language, whatever page or
    background job is sending it - the admin's pages are English."""
    from soloblog import settings, translate
    lang, english = _current.set(translate.site_language()), _english.set(
        settings.get("english_spelling") if settings.get("english_spelling") in ENGLISH else "us")
    try:
        yield
    finally:
        _current.reset(lang)
        _english.reset(english)


def _table() -> dict:
    """The current language's words - for English, only what its spelling
    changes."""
    if _current.get() != "en":
        return _load(_current.get())
    variant = "gb" if _english.get() == "au" else _english.get()
    return _load(os.path.join("english", variant))


def british() -> bool:
    return _english.get() in ("gb", "au")


# (British, American) - the words Soloblog's own wording uses that are
# spelled differently. Only its wording goes through spell(); a writer's
# posts never do.
SPELLINGS = [("colour", "color"), ("centred", "centered"), ("centre", "center"), ("grey", "gray"),
             ("favourite", "favorite"), ("licence", "license"), ("catalogue", "catalog"),
             ("organise", "organize"), ("behaviour", "behavior"), ("cancelled", "canceled"),
             ("customise", "customize"), ("analyse", "analyze")]


def spell(text):
    """text in the English spelling of this request - both ways, so the
    code's wording can be written either way. Anything but a string, or
    a site in another language, passes through."""
    if not isinstance(text, str) or _current.get() != "en":
        return text
    pairs = {us: gb for gb, us in SPELLINGS} if british() else {gb: us for gb, us in SPELLINGS}

    def swap(m):
        word = pairs[m.group(1).lower()]
        return (word.capitalize() if m.group(1)[0].isupper() else word) + (m.group(2) or "")
    return re.sub(r"\b(" + "|".join(pairs) + r")(s|d|ed|ing|ful|less|r|rs)?\b", swap, text, flags=re.I)


def lang() -> str:
    return _current.get()


def t(text: str, **values) -> str:
    """text in the current language. {name} placeholders are filled in
    after translating, so a language can put them in its own order."""
    out = _table().get(text, text)
    return out.format(**values) if values else out


def _form(n: int) -> str:
    """Which plural form a number takes - "one", "few" or "many". Most
    languages only have one and many; these have a third."""
    code = _current.get()
    if code in ("ja", "zh", "ko", "id", "tr"):
        return "many"
    if code == "fr":
        return "one" if n in (0, 1) else "many"
    if code in ("ru", "uk"):
        if n % 10 == 1 and n % 100 != 11:
            return "one"
        return "few" if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else "many"
    if code == "pl":
        if n == 1:
            return "one"
        return "few" if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else "many"
    if code == "cs":
        return "one" if n == 1 else "few" if 2 <= n <= 4 else "many"
    if code == "ar":
        return "one" if n == 1 else "few" if 2 <= n % 100 <= 10 else "many"
    return "one" if n == 1 else "many"


def plural(n: int, one: str, many: str) -> str:
    """"1 minute ago" / "5 minutes ago" - each form translated whole. A
    language with a third form keeps it under "<many>|few"."""
    form = _form(n)
    if form == "one":
        return t(one, n=n)
    if form == "few":
        few = _table().get(many + "|few")
        if few:
            return few.format(n=n)
    return t(many, n=n)


def months(full: bool = False) -> list:
    """Month names, January first - short ones for dates, full ones for
    the archive's headings."""
    if full:
        return _table().get("_months_full") or [
            "January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
            "November", "December"]
    return _table().get("_months") or ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug",
                                                     "Sep", "Oct", "Nov", "Dec"]


SCRIPT_WORDS = ("Copy", "Copied!", "Listen", "Pause", "Resume", "{field} is required", "More below")


def script_words() -> dict:
    """The words app.js writes itself, in the current language."""
    return {w: t(w) for w in SCRIPT_WORDS}


def date_format() -> str:
    """How a date is written: {month} {day}, {year} in English."""
    return _table().get("_date") or "{month} {day}, {year}"
