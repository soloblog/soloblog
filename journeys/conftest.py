"""Journeys: what people do with Soloblog, done in a real browser against a
real server - set it up, write and publish, read and comment, change the
look, use it on a phone. Not the markup (tests/ checks that): what happens
when someone clicks. Run them with

    python -m pytest journeys

on a fresh, empty site each time - its email written to an outbox folder
(MAIL_OUTBOX) for a journey to read, as a person reads their inbox. Any
script error on any page fails the journey it happened in."""
import email
import email.policy
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASSWORD = "journey-password-1"
TOKEN = "journey-setup-token"
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", os.path.join(ROOT, ".venv", "ms-playwright"))

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def pytest_collection_modifyitems(items):
    """The first-run journey goes first: its setup screens are only a
    first run's until the site has been set up, and the other journeys
    set it up."""
    items.sort(key=lambda item: os.path.basename(str(item.fspath)) != "test_first_run.py")


def start_server():
    """A Soloblog server on an empty disk of its own: (the process,
    {"base", "data", "outbox"}). The site fixture's - and a new host's,
    for moving a site to it."""
    data = tempfile.mkdtemp(prefix="journey-")
    outbox = os.path.join(data, "outbox")
    port = _free_port()
    base = f"http://127.0.0.1:{port}"
    env = {**os.environ, "DATA_DIR": data, "PORT": str(port), "BASE_URL": base, "ENV": "production",
           "SETUP_TOKEN": TOKEN, "MAIL_OUTBOX": outbox, "PYTHONUNBUFFERED": "1"}
    log = open(os.path.join(data, "server.log"), "w")  # noqa: SIM115 - the server writes to it until it stops
    server = subprocess.Popen([sys.executable, "app.py"], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    for _ in range(150):
        try:
            urllib.request.urlopen(base + "/healthz", timeout=1)  # noqa: S310 - the app on localhost
            break
        except Exception:
            time.sleep(0.2)
    else:
        server.terminate()
        pytest.fail("the server didn't start - see " + log.name)
    return server, {"base": base, "data": data, "outbox": outbox}


@pytest.fixture(scope="session")
def site(request):
    """A fresh site on its own port: {"base", "data", "outbox"} - set up
    by the first-run journey (setup_done), as its owner would."""
    if sync_playwright is None:
        pytest.skip("needs Playwright (requirements-dev.txt)")
    server, found = start_server()
    yield found
    server.terminate()
    server.wait(timeout=10)
    data = found["data"]
    # kept when a journey failed, for its server.log; otherwise gone
    if not request.session.testsfailed:
        shutil.rmtree(data, ignore_errors=True)


@pytest.fixture(scope="session")
def _playwright():
    if sync_playwright is None:
        pytest.skip("needs Playwright (requirements-dev.txt)")
    with sync_playwright() as p:
        yield p


def _launch(kind):
    try:
        return kind.launch()
    except Exception as e:
        pytest.skip(f"no browser for Playwright: {e}")


@pytest.fixture(scope="session")
def browser(_playwright):
    b = _launch(_playwright.chromium)
    yield b
    b.close()


@pytest.fixture(scope="session")
def firefox(_playwright):
    """For what only Firefox does differently."""
    b = _launch(_playwright.firefox)
    yield b
    b.close()


class Window:
    """One browser window: a page, the script errors it met, and helpers."""

    def __init__(self, browser, base, width=1280, height=900, phone=False, state=None):
        extra = {"is_mobile": True, "has_touch": True} if phone else {}
        self.context = browser.new_context(viewport={"width": width, "height": height}, base_url=base,
                                           storage_state=state, **extra)
        self.page = self.context.new_page()
        self.errors = []
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))

    def go(self, path):
        response = self.page.goto(path)
        self.page.wait_for_load_state("networkidle")
        assert response.status < 500, f"{path}: {response.status}"
        return response

    def close(self):
        self.context.close()
        assert not self.errors, f"script errors: {self.errors}"


@pytest.fixture
def window(browser, site):
    """A visitor's window, on a wide screen."""
    w = Window(browser, site["base"])
    yield w
    w.close()


@pytest.fixture
def phone(browser, site):
    """A visitor's window, on a phone - a finger, not a mouse."""
    w = Window(browser, site["base"], 375, 812, phone=True)
    yield w
    w.close()


def sign_in(w):
    w.go("/login")
    w.page.fill("input[name=password]", PASSWORD)
    w.page.get_by_role("button", name="Log in").click()
    w.page.wait_for_load_state("networkidle")
    assert "/login" not in w.page.url, "couldn't sign in"


@pytest.fixture
def owner(browser, site, set_up):
    """The site's owner, signed in, on a wide screen."""
    w = Window(browser, site["base"])
    sign_in(w)
    yield w
    w.close()


@pytest.fixture
def owner_firefox(firefox, site, set_up):
    w = Window(firefox, site["base"])
    sign_in(w)
    yield w
    w.close()


@pytest.fixture
def owner_phone(browser, site, set_up):
    w = Window(browser, site["base"], 375, 812, phone=True)
    sign_in(w)
    yield w
    w.close()


@pytest.fixture(scope="session")
def set_up(browser, site):
    """The first run, through the setup page, once: a password from the
    setup token, as a new owner does it."""
    w = Window(browser, site["base"])
    w.go("/setup")
    if w.page.locator("input[name=token]").count():
        w.page.fill("input[name=token]", TOKEN)
        w.page.fill("input[name=password]", PASSWORD)
        w.page.fill("input[name=confirm]", PASSWORD)
        w.page.get_by_role("button", name="Create admin account").click()
        w.page.wait_for_load_state("networkidle")
    w.close()
    return True


def outbox(site):
    """Every email the site has sent, oldest first: [(to, subject, body)]."""
    if not os.path.isdir(site["outbox"]):
        return []
    out = []
    for name in sorted(os.listdir(site["outbox"])):
        with open(os.path.join(site["outbox"], name), "rb") as f:
            msg = email.message_from_bytes(f.read(), policy=email.policy.default)
        # the plain text - a newsletter email has a designed copy beside it
        out.append((msg["To"], msg["Subject"], msg.get_body(("plain",)).get_content()))
    return out


# ---- writing, as the owner does it in the editor

def write(w, title, text):
    w.page.locator("[placeholder=Title], .editor-title, input.text-2xl").first.fill(title)
    w.page.locator(".CodeMirror").first.click()
    w.page.keyboard.press("Control+End")
    w.page.keyboard.type(text)


def save(w):
    # the Save in view: Post settings' own while it's open over the editor
    panel = w.page.locator("#post-settings-panel:not([inert]) button[type=submit]:visible")
    (panel.first if panel.count() else w.page.locator("#editor-bar button[type=submit]").first).click()
    w.page.wait_for_load_state("networkidle")
    w.page.wait_for_timeout(500)


def publish(w, title, text):
    """A new post, written and published: its address."""
    w.go("/admin/new")
    write(w, title, text)
    w.page.evaluate("() => togglePostSettings(true)")
    w.page.locator("#post-settings-panel input[name=published]").check()
    save(w)
    slug = w.page.url.rstrip("/").rsplit("/", 1)[-1]
    return f"/post/{slug}"
