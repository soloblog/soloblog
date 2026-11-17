import logging
import json
import re
import threading
import time
import urllib.request

from soloblog import config

log = logging.getLogger(__name__)

# "0.3.0 is out" beside the version in Settings: GitHub's latest release,
# looked up in the background at most once a day, and only when the admin
# opens Settings. UPDATE_CHECK=0 turns it off - nothing is ever sent but
# the request itself.

DAY = 24 * 3600
_state = {"latest": None, "url": "", "notes": "", "checked": 0.0, "running": False}
_lock = threading.Lock()


def _key(version: str):
    """"v0.10.0-beta" -> (0, 10, 0, 0, 1): a pre-release sorts before its
    release, and "-beta" (the first) before "-beta.2"."""
    m = re.match(r"v?(\d+)\.(\d+)\.(\d+)(-[^\s.]+(?:\.(\d+))?)?$", version.strip())
    if not m:
        return None
    pre = (0, int(m.group(5) or 1)) if m.group(4) else (1, 0)
    return int(m.group(1)), int(m.group(2)), int(m.group(3)), *pre


def _fetch():
    try:
        repo = config.PROJECT_URL.split("github.com/", 1)[1]
        req = urllib.request.Request(f"https://api.github.com/repos/{repo}/releases/latest",
                                     headers={"Accept": "application/vnd.github+json", "User-Agent": "Soloblog"})
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310 - the fixed GitHub releases address; netguard is not used (test_netguard allows it)
            data = json.loads(resp.read())
        _state.update(latest=data.get("tag_name") or None, url=data.get("html_url") or "", notes=data.get("body") or "")
    except Exception as e:
        log.warning("couldn't check for a new version: %s", e)
    finally:
        _state["running"] = False


def trigger(s) -> bool:
    """Update now: asks whatever runs Soloblog to pull the new version and
    restart it - Watchtower's /v1/update, or a host's deploy hook - with
    the update hook from Settings > Integrations. In the background, because
    the restart may well take this process down mid-request. False if
    there's no hook set."""
    url = (s.get("update_hook_url") or "").strip()
    if not url.startswith(("http://", "https://")):
        return False

    def call():
        headers = {"User-Agent": "Soloblog"}
        if s.get("update_hook_token"):
            headers["Authorization"] = f"Bearer {s['update_hook_token']}"
        # not netguard: Watchtower is usually on the private Docker
        # network, and only the admin can set this address
        req = urllib.request.Request(url, data=b"", method="POST", headers=headers)  # noqa: S310 - the admin's own update hook, often on the private network
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:  # noqa: S310 - the admin's own update hook, often on the private network
                log.info("update hook answered %s", resp.status)
        except Exception as e:
            log.warning("update hook: %s", e)

    threading.Thread(target=call, daemon=True).start()
    return True


def is_security_release() -> bool:
    """Whether the latest release fixes a security problem - its notes (the
    changelog's section) have a Security part (docs/DEVELOPMENT.md >
    Releasing)."""
    return bool(re.search(r"^(?:#+\s*|\*\*)Security\b", _state["notes"] or "", re.M))


def newer():
    """(version, release page) when a newer release is out, else None.
    Starts a check in the background when the last one is a day old."""
    if not config.UPDATE_CHECK:
        return None
    with _lock:
        if not _state["running"] and time.time() - _state["checked"] > DAY:
            _state.update(running=True, checked=time.time())
            threading.Thread(target=_fetch, daemon=True).start()
    latest, current = _key(_state["latest"] or ""), _key(config.VERSION)
    if latest and current and latest > current:
        return _state["latest"].lstrip("v"), _state["url"]
    return None
