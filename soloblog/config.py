import mimetypes
import os
import secrets

# the types uploads are served with (FileResponse asks mimetypes) - a slim
# Linux image's own list lacks some, and they went out as
# application/octet-stream, which a browser told nosniff may refuse
for _type, _ext in (("image/webp", ".webp"), ("image/avif", ".avif"), ("image/svg+xml", ".svg"),
                    ("video/webm", ".webm"), ("video/mp4", ".mp4"), ("audio/mp4", ".m4a"),
                    ("audio/mpeg", ".mp3"), ("audio/ogg", ".ogg"), ("audio/wav", ".wav")):
    mimetypes.add_type(_type, _ext)

VERSION = "1.0.0-beta"

# the project's own home and where people can support it - linked from
# the optional "Powered by Soloblog" footer line and the admin
PROJECT_URL = "https://github.com/soloblog/soloblog"
WEBSITE_URL = "https://soloblog.zrplus.net"

# `or`, not getenv's default argument, throughout - an env file with a
# blank line like SESSION_SECRET= sets the variable to "", and "" must
# count as unset, not as the value to use

SITE_TITLE = os.getenv("SITE_TITLE") or "My Blog"
# a first-setup token you choose yourself (16 characters or more) - set
# with the host's other variables, so nobody has to find it in a log
SETUP_TOKEN = (os.getenv("SETUP_TOKEN") or "").strip()


def _default_base_url():
    # the public URL the host platform already tells us about, so a
    # one-click deploy gets working RSS/sitemap/canonical links with no
    # extra setup - only a fallback: it's the host's own address, not a
    # domain you've pointed at it
    if os.getenv("RENDER_EXTERNAL_URL"):
        return os.getenv("RENDER_EXTERNAL_URL")
    if os.getenv("RAILWAY_PUBLIC_DOMAIN"):
        return f"https://{os.getenv('RAILWAY_PUBLIC_DOMAIN')}"
    if os.getenv("FLY_APP_NAME"):
        return f"https://{os.getenv('FLY_APP_NAME')}.fly.dev"
    return ""


# BASE_URL set on the host wins; then the address first-time setup was
# reached at, kept in the site_url setting and changeable in Settings >
# Site; then the platform's own address (app.py, use_site_url)
BASE_URL_FIXED = bool(os.getenv("BASE_URL"))
PLATFORM_URL = _default_base_url().rstrip("/")
LOCAL_URL = "http://localhost:5001"
BASE_URL = (os.getenv("BASE_URL") or PLATFORM_URL or LOCAL_URL).rstrip("/")

DATA_DIR = os.getenv("DATA_DIR") or "data"
POSTS_DIR = os.path.join(DATA_DIR, "posts")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
DB_PATH = os.path.join(DATA_DIR, "blog.db")

DEFAULT_SECRET = "dev-secret-change-me-in-prod"  # noqa: S105 - the placeholder the app warns about
PLACEHOLDER_SECRETS = {DEFAULT_SECRET, "change-me-to-a-long-random-string", "change-me", "changeme", "secret",
                       "your-secret-here", "replace-me"}
SECRET_FILE = os.path.join(DATA_DIR, ".session_secret")


def _session_secret():
    """(secret, where it's from): SESSION_SECRET when it's set; else one
    made at random on the first start and kept in the data folder, so a
    one-click host needs no variable at all. The fixed default only if
    the folder can't be written."""
    env = (os.getenv("SESSION_SECRET") or "").strip()
    # a value from a template or a guide is public: anyone could sign a
    # login with it - so it's as if it weren't set (health.secret_check says so)
    if env and env.lower() not in PLACEHOLDER_SECRETS:
        return env, "env"

    def kept():
        try:
            with open(SECRET_FILE, encoding="utf-8") as f:
                value = f.read().strip()
            return value if len(value) >= 32 else ""
        except OSError:
            return ""
    if kept():
        return kept(), "file"
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        # written aside, then linked into place: two processes starting at
        # once (a reloader and its worker) end up with the same one
        temp = f"{SECRET_FILE}.{os.getpid()}"
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(secrets.token_urlsafe(48) + "\n")
        try:
            os.link(temp, SECRET_FILE)
        except FileExistsError:
            pass
        finally:
            os.remove(temp)
    except OSError:
        return DEFAULT_SECRET, "default"
    return (kept(), "file") if kept() else (DEFAULT_SECRET, "default")


SESSION_SECRET, SESSION_SECRET_FROM = _session_secret()

# how long a login lasts without being used (the cookie is renewed on use)
SESSION_DAYS = int(os.getenv("SESSION_DAYS") or 14)

# a header your proxy or CDN sets to the visitor's real address, e.g.
# CF-Connecting-IP behind Cloudflare, or X-Real-IP from nginx - used for
# rate limiting instead of the last X-Forwarded-For entry. Only set it
# if every request reaches Soloblog through that proxy.
CLIENT_IP_HEADER = (os.getenv("CLIENT_IP_HEADER") or "").strip().lower()
# who may say what a visitor's address is (X-Forwarded-For and the header
# above). Unset: any caller on a private network, which is right behind a
# proxy on the same machine or network. "none": nobody - for a site
# reached straight from the internet, where the header is whatever the
# visitor wrote. Or the proxy's own addresses or networks, comma-separated.
TRUSTED_PROXY = (os.getenv("TRUSTED_PROXY") or "").strip().lower()

# the largest audio or video file the media library takes, in MB
# the public demo (soloblog/demo.py): the sample blog, rebuilt on every
# start, reset every few hours, with anything that could harm the next
# visitor switched off
DEMO_MODE = os.getenv("DEMO_MODE") == "1"
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD") or "demo"
DEMO_RESET_HOURS = float(os.getenv("DEMO_RESET_HOURS") or 3)

MAX_MEDIA_MB = int(os.getenv("MAX_MEDIA_MB") or (5 if DEMO_MODE else 100))

ENV = os.getenv("ENV") or "development"
# for developers and the journeys (journeys/): email written to files in
# this folder instead of sent - set only by whoever starts the server
MAIL_OUTBOX = (os.getenv("MAIL_OUTBOX") or "").strip()
# Email and the admin's address from the host, for a one-click deploy that
# asks for them. Settings > Email wins once it's filled in there
# (settings._from_host). SMTP first - any email provider; Resend's API
# for a host that blocks SMTP's ports.
SMTP_HOST = (os.getenv("SMTP_HOST") or "").strip()
SMTP_PORT = (os.getenv("SMTP_PORT") or "").strip()
SMTP_USER = (os.getenv("SMTP_USER") or "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD") or ""
SMTP_FROM = (os.getenv("SMTP_FROM") or "").strip()
RESEND_API_KEY = (os.getenv("RESEND_API_KEY") or "").strip()
RESEND_FROM = (os.getenv("RESEND_FROM") or "").strip()
ADMIN_EMAIL = (os.getenv("ADMIN_EMAIL") or "").strip()
# A site at an https address is a live site, whatever ENV says: someone who
# starts it with a plain "python app.py" behind HTTPS still gets a Secure
# login cookie, HSTS and no auto-reload.
IS_PROD = ENV == "production" or BASE_URL.startswith("https://")

# Optional S3-compatible bucket (Amazon S3, Cloudflare R2, Backblaze B2,
# MinIO...) for images and automatic backups - see storage.py and
# docs/DEPLOYMENT.md. Unset S3_BUCKET and none of it runs.
S3_BUCKET = os.getenv("S3_BUCKET") or ""
S3_ENDPOINT = (os.getenv("S3_ENDPOINT") or "").rstrip("/")   # blank = Amazon S3 for S3_REGION
S3_REGION = os.getenv("S3_REGION") or "auto"                  # R2 uses "auto"; S3/B2 need the real one
S3_ACCESS_KEY_ID = os.getenv("S3_ACCESS_KEY_ID") or ""
S3_SECRET_ACCESS_KEY = os.getenv("S3_SECRET_ACCESS_KEY") or ""
S3_PREFIX = os.getenv("S3_PREFIX") or ""                      # a folder inside the bucket, if it's shared
S3_AUTO_BACKUP = (os.getenv("S3_AUTO_BACKUP") or "1") != "0"
S3_RESTORE_ON_BOOT = (os.getenv("S3_RESTORE_ON_BOOT") or "1") != "0"
S3_BACKUP_KEEP = int(os.getenv("S3_BACKUP_KEEP") or 30)       # newest N backups kept, older ones deleted
# UPDATE_CHECK=0: don't ask GitHub whether a newer release is out (updates.py)
UPDATE_CHECK = (os.getenv("UPDATE_CHECK") or "1") != "0"
# how much goes in the server's log: WARNING for problems only, DEBUG for everything
LOG_LEVEL = (os.getenv("LOG_LEVEL") or "INFO").upper()
# RESET_PASSWORD=1: the server prints a one-time password reset link to
# its log on start (remove it again afterwards)
RESET_PASSWORD = (os.getenv("RESET_PASSWORD") or "") == "1"
# set, and bucket backups are encrypted with it (storage.seal) - they
# hold the password hash, two-factor secret and API keys
BACKUP_PASSPHRASE = os.getenv("BACKUP_PASSPHRASE") or ""
S3_BACKUP_DELAY = 60        # seconds of quiet after a change before backing up
S3_BACKUP_MAX_WAIT = 600    # ...but never longer than this after the first change



# The public demo (DEMO_MODE): a visitor who changes anything gets their
# own copy of the site (demo.Sandbox), and while a request of theirs runs
# these point into it - what one visitor writes, no one else sees.
# Nothing sets it outside the demo, and they're the folders above. Every
# read of the data folder goes through them, not the names above.
import contextvars as _contextvars  # noqa: E402

VISITOR_DIR = _contextvars.ContextVar("visitor_dir", default=None)


def data_dir() -> str:
    return VISITOR_DIR.get() or DATA_DIR


def posts_dir() -> str:
    visitor = VISITOR_DIR.get()
    return os.path.join(visitor, "posts") if visitor else POSTS_DIR


def uploads_dir() -> str:
    visitor = VISITOR_DIR.get()
    return os.path.join(visitor, "uploads") if visitor else UPLOADS_DIR


def db_path() -> str:
    visitor = VISITOR_DIR.get()
    return os.path.join(visitor, "blog.db") if visitor else DB_PATH
