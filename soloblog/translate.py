import logging
import hashlib
import json
import queue
import re
import threading
import urllib.request
from soloblog.tz import utcnow

import nh3

from soloblog import netguard
from soloblog import settings
from soloblog.db import get_db

log = logging.getLogger(__name__)

# Built-in translation (Settings > Site > Languages). Each post is
# translated once per language by the chosen service, kept in
# post_translations, and served at a real URL: /es/post/<slug>. A
# translation is made in the background - when a live post is saved,
# or the first time someone asks for it - and made again whenever the
# post's words change (source_hash).

LANGUAGES = {
    "ar": "العربية", "cs": "Čeština", "da": "Dansk", "de": "Deutsch", "el": "Ελληνικά", "en": "English",
    "es": "Español", "fi": "Suomi", "fr": "Français", "hi": "हिन्दी", "id": "Bahasa Indonesia", "it": "Italiano",
    "ja": "日本語", "ko": "한국어", "nb": "Norsk", "nl": "Nederlands", "pl": "Polski", "pt": "Português",
    "ru": "Русский", "sv": "Svenska", "tr": "Türkçe", "uk": "Українська", "zh": "中文",
}
RTL = {"ar"}
PROVIDERS = {"": "Off", "deepl": "DeepL", "google": "Google Cloud Translation", "libretranslate": "LibreTranslate"}
# DeepL wants a regional variant for these two as a target
_DEEPL_TARGET = {"en": "EN-US", "pt": "PT-PT"}
CHUNK = 20000


class TranslateError(RuntimeError):
    pass


def site_language(s=None) -> str:
    s = s or settings.get_all()
    return s.get("site_language") if s.get("site_language") in LANGUAGES else "en"


def enabled(s=None) -> bool:
    s = s or settings.get_all()
    return bool(s.get("translate_provider") in PROVIDERS and s.get("translate_provider") and targets(s))


def targets(s=None) -> list:
    """The languages posts are offered in, besides the site's own."""
    s = s or settings.get_all()
    own = site_language(s)
    return [c for c in (s.get("translate_languages") or "").split(",") if c in LANGUAGES and c != own]


def source_hash(row, body_md: str) -> str:
    return hashlib.sha256(f"{row['title']}\n{row['summary']}\n{body_md}".encode()).hexdigest()[:16]


def get(slug: str, lang: str):
    return get_db().execute("SELECT * FROM post_translations WHERE slug=? AND lang=?", (slug, lang)).fetchone()


def available(slug: str) -> list:
    return [r["lang"] for r in get_db().execute("SELECT lang FROM post_translations WHERE slug=? ORDER BY lang",
                                                (slug,))]


def count() -> int:
    return get_db().execute("SELECT COUNT(*) FROM post_translations").fetchone()[0]


def clear():
    get_db().execute("DELETE FROM post_translations")
    get_db().commit()


# ---- the services

def _post_json(url, data, headers=None, private_ok=False):
    req = urllib.request.Request(url, data=json.dumps(data).encode(), method="POST",  # noqa: S310 - opened through netguard
                                 headers={"Content-Type": "application/json", "User-Agent": "Soloblog", **(headers or {})})
    try:
        # a self-hosted LibreTranslate is often on the same private
        # network - the admin's own address, so it's allowed there
        with netguard.open_url(req, timeout=60, private_ok=private_ok) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        detail = e.read()[:300].decode("utf-8", "replace")
        raise TranslateError(f"{e.code}: {detail}") from e
    except Exception as e:
        raise TranslateError(str(e)) from e


def translate_texts(texts: list, target: str, source: str, html: bool, s=None) -> list:
    s = s or settings.get_all()
    provider, key = s.get("translate_provider"), s.get("translate_api_key", "")
    if not texts:
        return []
    if provider == "deepl":
        host = "api-free.deepl.com" if key.endswith(":fx") else "api.deepl.com"
        data = {"text": texts, "target_lang": _DEEPL_TARGET.get(target, target.upper()),
                "source_lang": source.upper()}
        if html:
            data["tag_handling"] = "html"
        out = _post_json(f"https://{host}/v2/translate", data, {"Authorization": f"DeepL-Auth-Key {key}"})
        return [t["text"] for t in out["translations"]]
    if provider == "google":
        out = _post_json(f"https://translation.googleapis.com/language/translate/v2?key={key}",
                         {"q": texts, "target": target, "source": source, "format": "html" if html else "text"})
        return [t["translatedText"] for t in out["data"]["translations"]]
    if provider == "libretranslate":
        base = (s.get("translate_url") or "https://libretranslate.com").rstrip("/")
        data = {"q": texts, "source": source, "target": target, "format": "html" if html else "text"}
        if key:
            data["api_key"] = key
        out = _post_json(f"{base}/translate", data, private_ok=True)
        result = out["translatedText"]
        return result if isinstance(result, list) else [result]
    raise TranslateError("no translation service chosen")


def _chunks(html: str) -> list:
    """The post's html in pieces a service takes in one go, split only
    before a heading or paragraph so no tag is cut in half."""
    blocks = re.split(r"(?=<(?:h[1-6]|p|ul|ol|pre|figure|blockquote|table|div)\b)", html)
    chunks, current = [], ""
    for b in blocks:
        if current and len(current) + len(b) > CHUNK:
            chunks.append(current)
            current = ""
        current += b
    return [c for c in chunks + [current] if c.strip()]


def _hold_section_lines(html: str):
    """A section's "Section: Pricing" line names what it is - translated
    ("Sección: Precios") the page wouldn't know it; so with its Width,
    Style and other Key: lines. Held out, by the ## heading they follow:
    (the html without them, {nth heading: lines})."""
    from soloblog import sections
    from soloblog.render import _SECTION_LINES
    held = {}

    def hold(m):
        if not sections.only_own_lines(m.group(1)):
            return m.group(0)
        held[html[:m.start()].count("</h2>")] = m.group(0)
        return ""

    def hold_own(m):
        own, rest = sections.split_own(m.group(1))
        if not own:
            return m.group(0)
        # the lines of its items (Project facts' Client:) are words to translate
        held[m.string[:m.start()].count("</h2>")] = f"<p>{'<br>'.join(own)}</p>\n"
        return f"<p>{'<br>'.join(rest)}</p>\n" if rest else ""
    return sections.SECTION_PARAGRAPH.sub(hold_own, _SECTION_LINES.sub(hold, html)), held


def _restore_section_lines(html: str, held: dict) -> str:
    """Each held line back after its heading - a translation keeps them."""
    for n in sorted(held, reverse=True):
        ends = [m.end() for m in re.finditer(r"</h2>", html)]
        if 0 < n <= len(ends):
            html = html[:ends[n - 1]] + held[n] + html[ends[n - 1]:]
    return html


def translate_post(slug: str, lang: str, s=None):
    """Makes (or remakes) one post's translation. Raises TranslateError."""
    from soloblog import posts
    from soloblog.render import ALLOWED_ATTRS, ALLOWED_TAGS, render_post
    s = s or settings.get_all()
    row = posts.get_post(slug)
    # a protected post's text never goes to a translation service
    if not row or posts.is_protected(row):
        return None
    body = posts.load_post_body(slug)
    html, _ = render_post(body)
    source = site_language(s)
    title, summary = translate_texts([row["title"], row["summary"] or " "], lang, source, html=False, s=s)
    html, held = _hold_section_lines(html)
    pieces = translate_texts(_chunks(html), lang, source, html=True, s=s)
    # the service's html is someone else's - sanitised like any post
    translated = _restore_section_lines(nh3.clean("".join(pieces), tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS),
                                        held)
    db = get_db()
    db.execute("INSERT INTO post_translations (slug, lang, source_hash, title, summary, html, translated_at) "
               "VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(slug, lang) DO UPDATE SET source_hash=excluded.source_hash, "
               "title=excluded.title, summary=excluded.summary, html=excluded.html, translated_at=excluded.translated_at",
               (slug, lang, source_hash(row, body), title, summary.strip(), translated,
                utcnow().isoformat(timespec="seconds")))
    db.commit()
    return get(slug, lang)


def is_stale(slug: str, lang: str) -> bool:
    from soloblog import posts
    row, t = posts.get_post(slug), get(slug, lang)
    return bool(row and (not t or t["source_hash"] != source_hash(row, posts.load_post_body(slug))))


# ---- in the background, one at a time

_queue = queue.Queue()
_queued = set()
_worker = None
_lock = threading.Lock()
_last_error = {"message": "", "at": ""}


def last_error() -> dict:
    return dict(_last_error)


def _work():
    while True:
        slug, lang = _queue.get()
        try:
            if is_stale(slug, lang):
                translate_post(slug, lang)
        except Exception as e:
            _last_error.update(message=f"{slug} ({lang}): {e}"[:300], at=utcnow().isoformat(timespec="seconds"))
            log.warning("%s -> %s failed: %s", slug, lang, e)
        finally:
            with _lock:
                _queued.discard((slug, lang))
            _queue.task_done()


def queue_post(slug: str, langs=None):
    """Translates slug into langs (every offered language by default),
    in the background, skipping any that are already up to date."""
    global _worker
    s = settings.get_all()
    if not enabled(s):
        return
    with _lock:
        if _worker is None:
            _worker = threading.Thread(target=_work, name="translate", daemon=True)
            _worker.start()
        for lang in langs or targets(s):
            if (slug, lang) not in _queued:
                _queued.add((slug, lang))
                _queue.put((slug, lang))


def pending() -> int:
    with _lock:
        return len(_queued)


def wait():
    _queue.join()
