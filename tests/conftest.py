import atexit
import os
import shutil
import sys
import tempfile

import pytest

# config.py reads its env vars once, at import - so the data dir has to
# point somewhere disposable before the app is imported at all
_DATA = tempfile.mkdtemp(prefix="soloblog-test-")


def _remove_data():
    """Gone when the run ends: every run left one behind, and a day's runs
    filled /tmp. A background write can still land as it goes ("not
    empty"), so it tries a few times."""
    import time
    for _ in range(5):
        shutil.rmtree(_DATA, ignore_errors=True)
        if not os.path.exists(_DATA):
            return
        time.sleep(0.2)


atexit.register(_remove_data)
os.environ["DATA_DIR"] = _DATA
os.environ["SESSION_SECRET"] = "test-secret"
os.environ["UPDATE_CHECK"] = "0"  # no calls to GitHub from the tests
os.environ.pop("ENV", None)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from soloblog import app as app_module  # noqa: E402
from soloblog import publishing  # noqa: E402

publishing.AUTOMATIC = False  # tests call publishing.check() when they mean to
from soloblog import health_remote  # noqa: E402
health_remote.AUTOMATIC = False  # nothing in the background may ask the internet
from soloblog import auth  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

PASSWORD = "correct horse battery"


@pytest.fixture(scope="session")
def app():
    return app_module.app


@pytest.fixture(scope="session", autouse=True)
def admin_account(app):
    """One admin for the whole run, created through the real /setup flow."""
    c = TestClient(app, follow_redirects=False)
    r = c.post("/setup", data={"token": auth.setup_token(), "password": PASSWORD, "confirm": PASSWORD})
    # the recovery key first, shown the once, then on to the welcome
    assert r.status_code == 200 and "Save your recovery key" in r.text and 'href="/admin/welcome"' in r.text, r.text
    return True


@pytest.fixture
def client(app):
    """A visitor - not logged in."""
    return TestClient(app, follow_redirects=False)


@pytest.fixture(scope="session")
def admin(app, admin_account):
    # session-scoped - /login is rate limited per IP, and every test
    # client shares the same one
    c = TestClient(app, follow_redirects=False)
    r = c.post("/login", data={"password": PASSWORD})
    assert r.status_code == 303, r.text
    return c


def editor_script(admin, html):
    """The editor's scripts, as the page loads them (/admin/editor.js) -
    a file the browser keeps, not inline in the page."""
    import re
    src = re.search(r'<script src="(/admin/editor\.js\?v=\w+)"', html).group(1)
    return admin.get(src).text


def save_post(admin, **fields):
    """Creates/updates a post through the editor's own save route and
    returns its slug."""
    data = {"title": "Untitled", "body": "Hello.", "published": "1", "comments_enabled": "1", **fields}
    r = admin.post("/admin/save", data=data, headers={"hx-request": "true"})
    assert r.status_code == 200, r.text
    return r.headers.get("hx-redirect", "").rsplit("/", 1)[-1] or fields.get("slug")


@pytest.fixture
def real_pictures():
    """Ask for this when a test is about a picture that isn't on disk."""


@pytest.fixture(autouse=True)
def sample_pictures_exist(request, monkeypatch):
    """Tests draw posts with pictures like /uploads/a.webp and never make the
    files; a page leaves out a picture that isn't on disk, so unless a test
    asks for real_pictures, every picture counts as there."""
    from soloblog import images
    if "real_pictures" not in request.fixturenames:
        monkeypatch.setattr(images, "is_missing", lambda src: False)


@pytest.fixture(autouse=True)
def fresh_rate_limits():
    """Every test starts with a clean login/comment budget - otherwise the
    order tests run in decides which one hits a limit."""
    from soloblog.db import get_db
    get_db().execute("DELETE FROM rate_hits")
    get_db().commit()
