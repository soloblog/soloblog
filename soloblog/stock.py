import logging
import json
import urllib.parse
import urllib.request

from soloblog import netguard
from soloblog import settings

log = logging.getLogger(__name__)

# Stock photo search for the image picker. Two providers, same shape
# back from search() so the picker renders them identically. Picking a
# result downloads it into our own uploads (images.save_upload) rather
# than hotlinking - Pixabay's own API terms say its image URLs expire
# after 24h and must be downloaded, and it keeps every image on the
# site served the same way regardless of where it came from.

SOURCES = {"pixabay": "Pixabay", "pexels": "Pexels", "unsplash": "Unsplash"}
KEY_SETTINGS = {"pixabay": "pixabay_api_key", "pexels": "pexels_api_key", "unsplash": "unsplash_access_key"}

# Unsplash is the exception to "download it": its API terms require
# the image to be shown from Unsplash's own servers (hotlinked), the
# photographer and Unsplash credited with links, and its download
# endpoint called when a photo is used. So a pick from Unsplash keeps
# its images.unsplash.com URL, its credit is saved against that URL
# (images.set_meta), and track_download() pings Unsplash.
HOTLINKED = {"unsplash"}
UNSPLASH_IMAGES = "https://images.unsplash.com/"
UTM = "utm_source=soloblog&utm_medium=referral"

# the only hosts download() will fetch from. The import route takes a
# URL from the browser, so without this it could be pointed at any
# internal address the server can reach.
ALLOWED_HOSTS = {"pixabay.com", "cdn.pixabay.com", "images.pexels.com"}

MAX_BYTES = 15 * 1024 * 1024
UA = {"User-Agent": "Soloblog/1.0"}


def api_key(source: str) -> str:
    return settings.get(KEY_SETTINGS[source]) or ""


def search(source: str, query: str) -> list:
    """[{"thumb", "full", "alt", "credit", "credit_url"}] - thumb for the
    grid, full for import, credit/credit_url for the photographer both
    sites ask to be named.
    Raises on a network/API failure; the caller shows the error."""
    key = api_key(source)
    if source == "pixabay":
        url = "https://pixabay.com/api/?" + urllib.parse.urlencode({
            "key": key, "q": query, "image_type": "photo", "per_page": 24, "safesearch": "true",
        })
        data = _get_json(url, UA)
        return [{"thumb": h["webformatURL"], "full": h["largeImageURL"], "alt": h.get("tags", ""),
                 "credit": h.get("user", ""), "credit_url": h.get("pageURL", "")}
                for h in data.get("hits", [])]
    if source == "unsplash":
        url = "https://api.unsplash.com/search/photos?" + urllib.parse.urlencode({
            "query": query, "per_page": 24, "content_filter": "high",
        })
        data = _get_json(url, {**UA, "Authorization": f"Client-ID {key}", "Accept-Version": "v1"})
        return [{"thumb": p["urls"]["small"], "full": p["urls"]["regular"],
                 "alt": p.get("alt_description") or p.get("description") or "",
                 "credit": p["user"]["name"], "credit_url": f"{p['user']['links']['html']}?{UTM}",
                 "download": p["links"]["download_location"]}
                for p in data.get("results", [])]
    url = "https://api.pexels.com/v1/search?" + urllib.parse.urlencode({"query": query, "per_page": 24})
    data = _get_json(url, {**UA, "Authorization": key})
    return [{"thumb": p["src"]["medium"], "full": p["src"]["large2x"], "alt": p.get("alt", ""),
             "credit": p.get("photographer", ""), "credit_url": p.get("photographer_url", "")}
            for p in data.get("photos", [])]


def _get_json(url, headers):
    req = urllib.request.Request(url, headers=headers)  # noqa: S310 - opened through netguard
    with netguard.open_url(req, timeout=10) as resp:
        return json.loads(resp.read())


def download(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)  # noqa: S310 - opened through netguard
    try:
        with netguard.open_url(req, timeout=20, hosts=ALLOWED_HOSTS) as resp:
            data = resp.read(MAX_BYTES + 1)
    except netguard.Blocked as e:
        raise ValueError("not a stock photo URL") from e
    if len(data) > MAX_BYTES:
        raise ValueError("image too large")
    return data


def is_unsplash_image(url: str) -> bool:
    parts = urllib.parse.urlparse(url or "")
    return parts.scheme == "https" and parts.hostname == "images.unsplash.com"


def track_download(download_location: str):
    """Unsplash's required "this photo was used" ping - in the background,
    and never allowed to get in the way of the pick itself."""
    import threading
    parts = urllib.parse.urlparse(download_location or "")
    if parts.scheme != "https" or parts.hostname != "api.unsplash.com":
        return

    def ping():
        try:
            _get_json(download_location, {**UA, "Authorization": f"Client-ID {api_key('unsplash')}",
                                          "Accept-Version": "v1"})
        except Exception as e:
            log.warning("Unsplash download ping failed: %s", e)
    threading.Thread(target=ping, daemon=True).start()
