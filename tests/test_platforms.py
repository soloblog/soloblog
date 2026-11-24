"""A one-click host (PikaPods, Cloudron, Elestio...) that sets no
variables and shows no log: Soloblog makes its own login secret, keeps
the setup token in a file, and takes its address from first-time setup.
Each run is its own process, since config is read once at import."""
import os
import stat
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST_VARS = ("BASE_URL", "SESSION_SECRET", "SETUP_TOKEN", "FLY_APP_NAME", "RENDER_EXTERNAL_URL",
             "RAILWAY_PUBLIC_DOMAIN", "DEMO_MODE", "ENV")

FIRST_START = r'''
import os, sys
sys.path.insert(0, os.getcwd())
from soloblog.app import app
from soloblog import auth, config, settings, health
from starlette.testclient import TestClient
assert config.SESSION_SECRET_FROM == "file" and len(config.SESSION_SECRET) >= 32, "secret made"
assert health.secret_check()["status"] == health.GOOD
token = open(auth.SETUP_TOKEN_FILE).read().split()[0]
assert token == auth.setup_token(), "token file"
# the browser stays on https behind the proxy, so the Secure cookie comes back
c = TestClient(app, base_url="https://testserver", follow_redirects=False)
# setup, as a browser behind the host's proxy sends it
r = c.post("/setup", data={"token": token, "password": "a good password", "confirm": "a good password"},
           headers={"Host": "pod-123.pikapod.net", "X-Forwarded-Proto": "https"})
assert r.status_code == 200, r.text[:300]
assert settings.get("site_url") == "https://pod-123.pikapod.net", settings.get("site_url")
assert config.BASE_URL == "https://pod-123.pikapod.net"
assert not os.path.exists(auth.SETUP_TOKEN_FILE), "token file gone"
assert "https://pod-123.pikapod.net/" in c.get("/rss").text, "feeds use it"
# changed in Settings > Site; nonsense refused
r = c.post("/admin/settings/url", data={"site_url": "javascript:alert(1)", "declared_fields": "site_url"},
           headers={"HX-Request": "true"})
assert "just https://" in r.text and settings.get("site_url") == "https://pod-123.pikapod.net"
c.post("/admin/settings/url", data={"site_url": "https://Blog.Example.org/", "declared_fields": "site_url"},
       headers={"HX-Request": "true"})
assert settings.get("site_url") == "https://blog.example.org" and config.BASE_URL == "https://blog.example.org"
print("SECRET=" + config.SESSION_SECRET)
'''

NEXT_START = r'''
import os, sys
sys.path.insert(0, os.getcwd())
from soloblog.app import app
from soloblog import auth, config
assert config.BASE_URL == "https://blog.example.org", config.BASE_URL
assert not os.path.exists(auth.SETUP_TOKEN_FILE)
print("SECRET=" + config.SESSION_SECRET)
'''

SPOOFED_SETUP = r'''
import os, sys
sys.path.insert(0, os.getcwd())
from soloblog.app import app
from soloblog import auth, config, settings
from starlette.testclient import TestClient
c = TestClient(app, follow_redirects=False)
c.post("/setup", data={"token": auth.setup_token(), "password": "a good password", "confirm": "a good password"},
       headers={"Host": "evil.example/path?x=1"})
assert settings.get("site_url") == "" and config.BASE_URL == config.LOCAL_URL, settings.get("site_url")
print("ok")
'''

HOST_SETS_THEM = r'''
import os, sys
sys.path.insert(0, os.getcwd())
from soloblog.app import app
from soloblog import config, settings
assert config.SESSION_SECRET_FROM == "env" and config.SESSION_SECRET == "x" * 64
assert not os.path.exists(config.SECRET_FILE)
settings.set_many({"site_url": "https://ignored.example"})
settings.use_site_url()
assert config.BASE_URL == "https://mine.example", config.BASE_URL
print("ok")
'''

# Fly, Render, Railway: the host's own address was taken as set on the
# host - Settings was locked and setup didn't keep your own domain
ON_FLY = r'''
import os, sys
sys.path.insert(0, os.getcwd())
from soloblog.app import app
from soloblog import auth, config, settings, health
from starlette.testclient import TestClient
assert config.BASE_URL == "https://myblog.fly.dev" and not config.BASE_URL_FIXED, config.BASE_URL
# https, as on Fly: the login cookie is Secure there
c = TestClient(app, base_url="https://testserver", follow_redirects=False)
c.post("/setup", data={"token": auth.setup_token(), "password": "a good password", "confirm": "a good password"},
       headers={"Host": "blog.example.org", "X-Forwarded-Proto": "https"})
assert settings.get("site_url") == "https://blog.example.org" and config.BASE_URL == "https://blog.example.org"
page = c.get("/admin/settings?tab=url").text
field = page[page.index('name="site_url"') - 200:page.index('name="site_url"') + 300]
assert "disabled" not in field and 'placeholder="https://myblog.fly.dev"' in field, field
# on the other address: Site health opens the field
check = health.address_check("myblog.fly.dev")
assert check["status"] == health.RECOMMENDED and "/admin/settings?tab=url#site_url" in str(check), check
# emptied: the host's own again
c.post("/admin/settings/url", data={"site_url": "", "declared_fields": "site_url"}, headers={"HX-Request": "true"})
assert config.BASE_URL == "https://myblog.fly.dev", config.BASE_URL
c.post("/admin/settings/url", data={"site_url": "https://blog.example.org", "declared_fields": "site_url"},
       headers={"HX-Request": "true"})
print("ok")
'''

ON_FLY_AGAIN = r'''
import os, sys
sys.path.insert(0, os.getcwd())
from soloblog.app import app
from soloblog import config
assert config.BASE_URL == "https://blog.example.org", config.BASE_URL
print("ok")
'''


def _run(script, data, **extra):
    env = {k: v for k, v in os.environ.items() if k not in HOST_VARS}
    env.update({"DATA_DIR": str(data), "UPDATE_CHECK": "0", **extra})
    r = subprocess.run([sys.executable, "-c", script], cwd=ROOT, env=env, capture_output=True, text=True,
                       timeout=120)
    assert r.returncode == 0, (r.stdout + r.stderr)[-3000:]
    return r.stdout


def test_a_host_with_no_variables(tmp_path):
    data = tmp_path / "data"
    first = _run(FIRST_START, data)
    secret_file = data / ".session_secret"
    assert stat.S_IMODE(secret_file.stat().st_mode) == 0o600
    # the same secret after a restart - nobody is signed out
    assert first.split("SECRET=")[1].strip() == _run(NEXT_START, data).split("SECRET=")[1].strip()


def test_setup_takes_only_a_real_address(tmp_path):
    assert "ok" in _run(SPOOFED_SETUP, tmp_path / "data")


def test_what_the_host_sets_wins(tmp_path):
    assert "ok" in _run(HOST_SETS_THEM, tmp_path / "data", SESSION_SECRET="x" * 64, BASE_URL="https://mine.example")


def test_on_fly_your_own_domain_comes_from_setup_and_settings(tmp_path):
    data = tmp_path / "data"
    assert "ok" in _run(ON_FLY, data, FLY_APP_NAME="myblog")
    # kept after a restart, over the host's own address
    assert "ok" in _run(ON_FLY_AGAIN, data, FLY_APP_NAME="myblog")


def test_an_https_address_is_a_live_site_without_being_told():
    """Started with a plain "python app.py" and an https address, and no
    ENV: the login cookie is still Secure and HSTS is sent."""
    code = r'''
import os, sys
sys.path.insert(0, os.getcwd())
from soloblog.app import app
from soloblog import auth, config
from starlette.testclient import TestClient
assert config.IS_PROD == (os.environ["WANT"] == "live"), config.IS_PROD
c = TestClient(app, base_url=config.BASE_URL, follow_redirects=False)
r = c.post("/setup", data={"token": auth.setup_token(), "password": "a good password",
                           "confirm": "a good password"}, headers={"Origin": config.BASE_URL})
cookie = r.headers.get("set-cookie", "")
assert "blog_session" in cookie, r.status_code
assert ("secure" in cookie.lower()) == (os.environ["WANT"] == "live"), cookie
assert ("strict-transport-security" in r.headers) == (os.environ["WANT"] == "live")
print("OK")
'''
    import tempfile
    for base, env, want in (("https://blog.example.org", None, "live"), ("http://localhost:5001", None, "dev"),
                            ("https://blog.example.org", "development", "live")):
        with tempfile.TemporaryDirectory() as data:
            e = {k: v for k, v in os.environ.items() if k not in HOST_VARS}
            e.update(DATA_DIR=data, BASE_URL=base, SESSION_SECRET="s" * 40, WANT=want)
            if env:
                e["ENV"] = env
            out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=e, capture_output=True, text=True, timeout=120)
            assert "OK" in out.stdout, (base, env, out.stdout[-300:], out.stderr[-600:])


def test_a_home_server_over_plain_http_can_log_in(tmp_path):
    """The image runs as a live site (ENV=production), but a home server is
    opened at http://umbrel.local or an address on the network: a Secure
    cookie there is never sent back, and its owner could set up but never
    log in. Secure on an HTTPS visit, as a proxy reports it - and a visitor
    can't take it off anyone else's: an address of https keeps it."""
    code = r'''
import os, sys
sys.path.insert(0, os.getcwd())
from soloblog.app import app
from soloblog import auth
from starlette.testclient import TestClient
home = TestClient(app, base_url="http://192.168.1.20:8484", follow_redirects=False)
r = home.post("/setup", data={"token": auth.setup_token(), "password": "a good password",
                              "confirm": "a good password"}, headers={"Origin": "http://192.168.1.20:8484"})
cookie = r.headers.get("set-cookie", "")
assert "blog_session" in cookie and "secure" not in cookie.lower(), cookie
assert home.get("/admin/posts").status_code == 200
r = home.post("/login", data={"password": "a good password"}, headers={"Origin": "http://192.168.1.20:8484"})
assert r.status_code == 303 and "secure" not in r.headers.get("set-cookie", "").lower()
assert home.get("/admin/posts").status_code == 200
# behind an HTTPS proxy (Fly, Railway, a tunnel): Secure
proxied = TestClient(app, base_url="http://blog.example.org", follow_redirects=False)
r = proxied.post("/login", data={"password": "a good password"},
                 headers={"Origin": "https://blog.example.org", "X-Forwarded-Proto": "https"})
assert r.status_code == 303 and "secure" in r.headers.get("set-cookie", "").lower(), r.headers
print("OK")
'''
    e = {k: v for k, v in os.environ.items() if k not in HOST_VARS}
    e.update(DATA_DIR=str(tmp_path), ENV="production", SESSION_SECRET="s" * 40, UPDATE_CHECK="0")
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=e, capture_output=True, text=True, timeout=120)
    assert "OK" in out.stdout, (out.stdout[-300:], out.stderr[-1500:])


def test_the_image_says_what_it_is():
    """Registries, Watchtower and one-click hosts read the image's labels.
    The release build names them again (docker/metadata-action would take
    the repository's own description and licence otherwise), as labels and
    as the index's annotations - all three must say the same."""
    import re
    from pathlib import Path

    from soloblog import config
    read = lambda *parts: Path(ROOT, *parts).read_text(encoding="utf-8")  # noqa: E731
    docker = read("Dockerfile")
    block = re.search(r"^LABEL (.*?)\n\n", docker, re.S | re.M).group(1)
    labels = dict(re.findall(r'(org\.opencontainers\.image\.\w+)="([^"]*)"', block))
    for key in ("title", "description", "licenses", "vendor", "url", "source", "documentation"):
        assert labels.get(f"org.opencontainers.image.{key}"), key
    assert labels["org.opencontainers.image.source"] == config.PROJECT_URL
    assert labels["org.opencontainers.image.documentation"].startswith(config.PROJECT_URL + "/")
    assert labels["org.opencontainers.image.licenses"] == "MIT"
    assert "MIT" in read("LICENSE")

    workflow = read(".github", "workflows", "docker.yml")
    for part in ("labels", "annotations"):
        given = re.search(rf"^ {{10}}{part}: \|\n((?: {{12}}.*\n)+)", workflow, re.M).group(1)
        named = dict(line.strip().split("=", 1) for line in given.splitlines())
        # source and url come from the repository the build runs in
        expected = {k: v for k, v in labels.items() if not k.endswith((".url", ".source"))}
        assert named == expected, part
    assert "annotations: ${{ steps.meta.outputs.annotations }}" in workflow
    assert "DOCKER_METADATA_ANNOTATIONS_LEVELS: manifest,index" in workflow


def _package(*parts):
    from pathlib import Path
    return Path(ROOT, "deploy", "platforms", *parts)


def test_every_app_store_package_runs_the_same_soloblog(tmp_path):
    """The packages in deploy/platforms all run this release's image, on
    port 8080, with the data folder on lasting storage - and say nothing
    about the project's money (they go to other people's repositories)."""
    import json
    import re
    import shutil
    import tomllib
    import xml.etree.ElementTree as ET

    import yaml

    from soloblog import config
    files = [p for p in _package().rglob("*") if p.is_file() and p.name != ".gitkeep"]
    assert len(files) > 25
    for path in files:
        text = path.read_text(encoding="utf-8")
        # parse what can be parsed (Sealos's has ${{ }} placeholders, TrueNAS's is Jinja)
        if path.suffix == ".json":
            json.loads(text)
        elif path.suffix == ".toml":
            tomllib.loads(text)
        elif path.suffix == ".xml":
            ET.fromstring(text)
        elif path.suffix in (".yml", ".yaml") and "templates" not in path.parts:
            list(yaml.safe_load_all(text))
        for tag in re.findall(r"ghcr\.io/soloblog/soloblog:([\w.$-]+)", text):
            assert tag in (config.VERSION, "latest"), (path.name, tag)
        assert not re.search(r"(?i)kickback|referral|commission|affiliate|claude", text), path

    # the tool sets every version: run on a copy, it changes nothing
    import importlib.util
    spec = importlib.util.spec_from_file_location("platforms_tool", os.path.join(ROOT, "tools", "platforms.py"))
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    shutil.copytree(os.path.join(ROOT, "deploy"), tmp_path / "deploy")
    tool.ROOT, tool.PLATFORMS = tmp_path, tmp_path / "deploy" / "platforms"
    assert tool.set_version(config.VERSION) == [], "run: python tools/platforms.py version"
    changed = tool.set_version("9.9.9")
    assert len(changed) >= 14
    copied = [p for p in (tmp_path / "deploy").rglob("*") if p.is_file()]
    assert not any(config.VERSION in p.read_text(encoding="utf-8") for p in copied
                   if p.name != "CHANGELOG"), "a version the tool doesn't reach"

    # compose-style packages: the image's port and a volume at /data
    for rel in (("coolify", "soloblog.yaml"), ("dokploy", "soloblog", "docker-compose.yml"),
                ("casaos", "Soloblog", "docker-compose.yml"), ("umbrel", "soloblog", "docker-compose.yml")):
        compose = yaml.safe_load(_package(*rel).read_text(encoding="utf-8"))
        web = next(s for name, s in compose["services"].items() if name != "app_proxy")
        mounts = [m if isinstance(m, str) else f"{m['source']}:{m['target']}" for m in web["volumes"]]
        assert any(m.endswith(":/data") for m in mounts), rel

    # Umbrel: no logs to read, so the token is the password umbrelOS shows
    app = yaml.safe_load(_package("umbrel", "soloblog", "umbrel-app.yml").read_text(encoding="utf-8"))
    compose = yaml.safe_load(_package("umbrel", "soloblog", "docker-compose.yml").read_text(encoding="utf-8"))
    assert app["deterministicPassword"] is True and compose["services"]["web"]["environment"]["SETUP_TOKEN"] == "${APP_PASSWORD}"
    assert compose["services"]["app_proxy"]["environment"]["APP_HOST"] == f"{app['id']}_web_1"
    assert compose["services"]["app_proxy"]["environment"]["APP_PORT"] == 8080
    assert _package("umbrel", "soloblog", "data", "soloblog", ".gitkeep").exists()

    # Cloudron: the only writable folder is /app/data
    docker = _package("cloudron", "Dockerfile").read_text(encoding="utf-8")
    assert "DATA_DIR=/app/data" in docker
    assert json.loads(_package("cloudron", "CloudronManifest.json").read_text())["httpPort"] == 8080
    assert os.access(_package("cloudron", "start.sh"), os.X_OK)
