"""Every route, sent what a bot or an attacker might send - an empty or
folder-like name, a number too big for the database, odd characters,
nonsense in every query and form field - as a visitor and as the admin.
Nothing may answer with a server error. It runs on a throwaway data
folder of its own, since the admin's forms are sent nonsense too.

    python tools/fuzz_routes.py        # prints anything that broke

tests/test_hardening.py runs it."""
import atexit
import itertools
import logging
import os
import re
import shutil
import sys
import tempfile

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="soloblog-fuzz-")
# its throwaway site goes when it ends
atexit.register(shutil.rmtree, os.environ["DATA_DIR"], ignore_errors=True)
os.environ.setdefault("SESSION_SECRET", "fuzz")
os.environ["UPDATE_CHECK"] = "0"
os.environ.pop("ENV", None)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.disable(logging.CRITICAL)

from starlette.routing import Mount, Route  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

from soloblog import app as app_module, auth, health_remote, publishing  # noqa: E402

publishing.AUTOMATIC = False
health_remote.AUTOMATIC = False

# in an address: empty, a folder of the uploads', climbing out, too big a
# number, and characters a name never has
VALUES = ["", "_trash", "..", "%2e%2e", "99999999999999999999", "-1", "😀", "%00", "x" * 300, "x.png"]
QUERY = ("?page=abc&per=zz&per_page=-1&w=abc&q=%00&tab=..&status=zz&sort=zz&range=zz&step=zz&kind=zz&tag=%00"
         "&n=-5&id=abc&slug=..&offset=-1&limit=abc&lang=zz&back=//evil.example&next=//evil.example&template=..%2Fx")
FORM = {k: "😀\x00" for k in ("title", "body", "slug", "id", "ids", "q", "email", "name", "url", "page", "w",
                              "tab", "action", "value", "key", "token", "password", "declared_fields",
                              "new_post_start", "dark_version", "phone_version", "site", "where", "label", "direction")}
# a JSON body that isn't one, or isn't an object - sent once per route
JSON_BODIES = ["{not json", "[1, 2]", '"words"', "\xff"]
# what would end the run itself
SKIP = ("/logout",)


def routes(app):
    found = []

    def walk(rs, prefix=""):
        for r in rs:
            if isinstance(r, Mount):
                walk(r.routes or [], prefix + r.path)
            elif isinstance(r, Route):
                found.append((prefix + r.path, sorted(set(r.methods or ["GET"]) - {"HEAD"})))
    walk(app.routes)
    return found


def run() -> list:
    app = app_module.app
    visitor = TestClient(app, follow_redirects=False, raise_server_exceptions=False)
    admin = TestClient(app, follow_redirects=False, raise_server_exceptions=False)
    password = "correct horse battery"
    admin.post("/setup", data={"token": auth.setup_token(), "password": password, "confirm": password})
    admin.post("/login", data={"password": password})
    admin.post("/admin/save", data={"title": "Hello", "body": "Hi.", "published": "1"}, headers={"hx-request": "true"})
    broken = set()

    def send(client, who, method, url, data=None, json_body=None):
        headers = {"hx-request": "true"} if method != "GET" else {}
        if json_body is not None:
            headers["content-type"] = "application/json"
        try:
            r = client.request(method, url, data=data, content=json_body, headers=headers or None)
            if r.status_code >= 500:
                broken.add(f"{who} {method} {url[:100]} -> {r.status_code}")
        except Exception as e:  # noqa: BLE001 - anything at all is a finding
            broken.add(f"{who} {method} {url[:100]} -> {type(e).__name__}: {e}"[:200])

    for path, methods in routes(app):
        params = re.findall(r"{(\w+)(?::\w+)?}", path)
        combos = [dict.fromkeys(params, v) for v in VALUES] if params else [{}]
        if len(params) == 2:
            combos += [dict(zip(params, v)) for v in itertools.product(VALUES[:3], repeat=2)]
        for n, combo in enumerate(combos):
            url = re.sub(r"{(\w+)(?::\w+)?}", lambda m, combo=combo: combo[m.group(1)], path)
            if url.startswith(SKIP):
                continue
            for client, who in ((visitor, "visitor"), (admin, "admin")):
                for method in methods:
                    if method == "GET":
                        send(client, who, "GET", url)
                        send(client, who, "GET", url + QUERY)
                    else:
                        send(client, who, method, url, {})
                        send(client, who, method, url, FORM)
                        for body in JSON_BODIES if n == 0 else ():
                            send(client, who, method, url, json_body=body.encode("latin-1"))
    return sorted(broken)


if __name__ == "__main__":
    found = run()
    print("\n".join(found) or "Nothing found")
    sys.exit(1 if found else 0)
