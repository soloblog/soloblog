"""Site health (Admin > Site health): whether anything about the site
needs the admin, before it becomes a problem - like WordPress's Site
Health. Each check is critical, recommended or good, says why it
matters in plain words, and where to fix it. The quick ones run when the
page opens; the ones that ask other servers are in remote_checks(),
run once a day in the background (health_remote.py)."""
import contextlib
import json
import logging
import os
import platform
import re
import shutil
import sqlite3
import sys
import time
from datetime import datetime, timedelta, UTC
from logging.handlers import RotatingFileHandler
from soloblog.tz import utcnow
from urllib.parse import urlparse

from soloblog import config
from soloblog import settings

CRITICAL, RECOMMENDED, GOOD = "critical", "recommended", "good"
ORDER = {CRITICAL: 0, RECOMMENDED: 1, GOOD: 2}
AREAS = {"updates": "Updates", "backups": "Backups", "security": "Security", "email": "Email",
         "domain": "Domain", "storage": "Storage", "visibility": "Visibility", "payments": "Payments",
         "background": "Background"}
DEFAULT_SECRET = config.DEFAULT_SECRET


def check(key, area, status, title, why, fix=None, href=None, action=None):
    """One result. fix/href - the button to where it's put right; action -
    a form post that does it here (Verify a backup)."""
    return {"key": key, "area": area, "status": status, "title": title, "why": why, "fix": fix, "href": href,
            "action": action}


def _ago(iso: str):
    """How long ago a stored (UTC) time was, as a timedelta - None if it
    isn't one."""
    try:
        return utcnow() - datetime.fromisoformat((iso or "")[:19])
    except ValueError:
        return None


def _days(delta) -> str:
    days = delta.days
    if days < 1:
        return "today"
    return "yesterday" if days == 1 else f"{days} days ago"


def is_local() -> bool:
    """Running on this computer, not on the internet - the checks for a
    real address (HTTPS, the certificate) don't apply."""
    host = urlparse(config.BASE_URL).hostname or ""
    return host in ("localhost", "127.0.0.1", "::1", "0.0.0.0") or host.endswith((".localhost", ".test", ".local"))  # noqa: S104 - a name to recognise, not an address to bind


# ---- the checks

def updates_check():
    from soloblog import updates
    if not config.UPDATE_CHECK:
        return check("updates", "updates", RECOMMENDED, "Checking for new versions is off",
                     "UPDATE_CHECK=0 is set, so you won't hear about new versions - including security fixes. "
                     "Check the releases yourself now and then.",
                     "See the releases", f"{config.PROJECT_URL}/releases")
    newer = updates.newer()
    if newer:
        version, url = newer
        if updates.is_security_release():
            return check("updates", "updates", CRITICAL, f"A security update is out: {version}",
                         "It fixes a problem that could put your site at risk. Update as soon as you can - "
                         "your posts and settings carry over.",
                         "How to update", "/admin/help?tab=deployment#update-to-a-new-version")
        return check("updates", "updates", RECOMMENDED, f"A new version is out: {version}",
                     f"You're on {config.VERSION}. Updating brings fixes and improvements; your posts and "
                     "settings carry over.", "How to update", "/admin/help?tab=deployment#update-to-a-new-version")
    return check("updates", "updates", GOOD, f"You're on Soloblog {config.VERSION}",
                 "Checked against the latest release once a day.")


def backup_check():
    from soloblog import storage
    bucket = storage.enabled()
    if bucket and storage.last_status()["error"]:
        return check("backup", "backups", CRITICAL, "The last automatic backup failed",
                     f"It said: {storage.last_status()['error']}. Until it works, a change could be lost.",
                     "Open Backup and import", "/admin/settings?tab=backup")
    times = [t for t in (settings.get("backup_last_at"), settings.get("last_backup_download")) if t]
    last = min((_ago(t) for t in times if _ago(t) is not None), default=None)
    where = "to your bucket, automatically" if bucket else "by download"
    # cloud storage connected, but nothing has reached it: say so, not "connect cloud storage"
    if bucket and not settings.get("backup_last_at") and (last is None or last > timedelta(days=7)):
        return check("backup", "backups", CRITICAL if last is None or last > timedelta(days=30) else RECOMMENDED,
                     "No backup has reached your bucket yet" if last is None else
                     f"The last backup was {_days(last)}",
                     "Cloud storage is connected, but no backup has been made there yet. Back up now to check "
                     "it works - after that, it's done for you a minute after every change.",
                     "Back up now", "/admin/settings?tab=backup")
    if last is None:
        return check("backup", "backups", CRITICAL, "There's no backup yet",
                     "If the server's disk failed, everything on it would be gone. Download a backup, or "
                     "connect cloud storage for automatic ones.",
                     "Back up now", "/admin/settings?tab=backup")
    if last > timedelta(days=30):
        return check("backup", "backups", CRITICAL, f"The last backup was {_days(last)}",
                     "A month of posts, comments and settings could be lost. Back up now - or connect cloud "
                     "storage, and it's done for you a minute after every change.",
                     "Back up now", "/admin/settings?tab=backup")
    if last > timedelta(days=7):
        return check("backup", "backups", RECOMMENDED, f"The last backup was {_days(last)}",
                     "Download a fresh one, or connect cloud storage for automatic backups.",
                     "Back up now", "/admin/settings?tab=backup")
    return check("backup", "backups", GOOD, f"Backed up {_days(last)}", f"The last backup was made {where}.")


def bucket_images_check():
    """Only with a bucket, and only when some image's copy to it failed -
    nothing else would say so, and it's never retried by itself."""
    from soloblog import storage
    missing = len(storage.unsynced()) if storage.enabled() else 0
    if not missing:
        return None
    return check("bucket-images", "backups", RECOMMENDED,
                 "1 image hasn't reached your bucket" if missing == 1 else f"{missing} images haven't reached your bucket",
                 "Copying it there failed, so if the server's disk failed it would be gone. Sync this site's images "
                 "to your bucket." if missing == 1 else "Copying them there failed, so if the server's disk failed "
                 "they'd be gone. Sync this site's images to your bucket.",
                 "Open Backup and import", "/admin/settings?tab=backup#cloud-status")


def verify_check():
    """Only with a bucket: a backup there can be opened and checked here.
    Without one, Restore does the same for a downloaded file."""
    from soloblog import storage
    if not storage.enabled() or not settings.get("backup_last_at"):
        # nothing in the bucket to check yet - the backup check says so
        return None
    verified = _ago(settings.get("backup_verified_at"))
    result = settings.get("backup_verified_result")
    if verified is not None and result and result != "ok":
        return check("verify", "backups", CRITICAL, "The last backup check found a problem",
                     f"It said: {result}. A backup that can't be restored isn't a backup - check Cloud storage "
                     "and run a new one.", action=("Verify again", "/admin/health/verify"))
    if verified is None or verified > timedelta(days=90):
        return check("verify", "backups", RECOMMENDED,
                     "Your backups haven't been checked" if verified is None else
                     f"Your backups were last checked {_days(verified)}",
                     "Verify opens the newest backup in your bucket and makes sure it would restore - "
                     "without restoring anything.", action=("Verify a backup", "/admin/health/verify"))
    return check("verify", "backups", GOOD, f"The newest backup was checked {_days(verified)}",
                 "It opened, and it would restore.", action=("Verify again", "/admin/health/verify"))


def https_check():
    if is_local():
        return None
    if config.BASE_URL.startswith("https://"):
        return check("https", "security", GOOD, "Your site uses HTTPS",
                     "Visits are encrypted, and browsers show it as secure.")
    return check("https", "security", CRITICAL, "Your site isn't using HTTPS",
                 "Logins and comments travel unencrypted, and browsers mark the site as not secure. Most hosts "
                 "turn HTTPS on for free; then set BASE_URL to the https:// URL.",
                 "How to set it up", "/admin/help?tab=deployment#put-https-in-front")


def secret_check():
    if (os.getenv("SESSION_SECRET") or "").strip().lower() in config.PLACEHOLDER_SECRETS:
        return check("secret", "security", RECOMMENDED, "SESSION_SECRET is a placeholder, so it isn't used",
                     "It's the example from a template, which anyone can read. Soloblog uses one of its own "
                     "instead - remove SESSION_SECRET on your host, or set it to 64 random characters.",
                     "How to set it", "/admin/help?tab=deployment#settings-on-the-host")
    if config.SESSION_SECRET != DEFAULT_SECRET:
        return check("secret", "security", GOOD, "Logins are signed with your own secret",
                     "SESSION_SECRET is set." if config.SESSION_SECRET_FROM == "env" else  # noqa: S105 - a source name, not a secret
                     "Made for you on the first start, and kept with your data.")
    return check("secret", "security", CRITICAL, "Logins are signed with the default secret",
                 "Anyone who knows the default could forge a login to your admin. Soloblog couldn't save a "
                 "secret of its own in the data folder - make it writable, or set SESSION_SECRET to 64 random "
                 "characters on your host, then restart.",
                 "How to set it", "/admin/help?tab=deployment#settings-on-the-host")


def login_check():
    from soloblog import passkeys, totp
    if totp.is_enabled() or passkeys.count():
        return check("login", "security", GOOD, "Your login is protected beyond the password",
                     "With a passkey or two-factor authentication (2FA).")
    return check("login", "security", RECOMMENDED, "Your login has only a password",
                 "Add a passkey - your fingerprint, face or device PIN - or two-factor authentication, so a leaked "
                 "password isn't enough to get in.", "Open Security", "/admin/settings?tab=security")


def recovery_check():
    from soloblog import auth
    if auth.has_recovery_key():
        return check("recovery", "security", GOOD, "You have a recovery key",
                     "It resets your password if you forget it.")
    return check("recovery", "security", RECOMMENDED, "There's no recovery key",
                 "Without one, a forgotten password means a server restart to get back in.",
                 "Make one", "/admin/settings?tab=security")


def email_check():
    """Email, as one thing: your address (where resets and alerts go) and
    how the site sends it - both on the Email page."""
    from soloblog import mail
    sending, yours = mail.can_send(), settings.get("admin_email")
    if not sending and not yours:
        return check("email", "email", RECOMMENDED, "Email isn't set up",
                     "Add your address and choose how email is sent. Password resets, sign-in alerts, comment "
                     "confirmations and the newsletter all need it.", "Set it up", "/admin/settings?tab=email")
    if not sending:
        return check("email", "email", RECOMMENDED, "Email can't be sent yet",
                     "Your address is saved - choose how email is sent. Password resets, sign-in alerts, comment "
                     "confirmations and the newsletter all need it.", "Set it up", "/admin/settings?tab=email")
    if not yours:
        return check("email", "email", RECOMMENDED, "Your email address isn't set",
                     "Email can be sent, but password reset links and sign-in alerts have nowhere to go.",
                     "Add it", "/admin/settings?tab=email#admin_email")
    ok_at, error, failed_at = settings.get("mail_last_ok_at"), settings.get("mail_last_error"), \
        settings.get("mail_last_failed_at")
    if error and failed_at and failed_at >= (ok_at or ""):
        return check("email", "email", CRITICAL, "The last email didn't go out",
                     f"{mail.explain(error).rstrip('.')}. Then send yourself a test. (The server said: {error})",
                     "Open Email", "/admin/settings?tab=email")
    if mail.only_reaches_you():
        # worst while someone else depends on it: members signing in, or subscribers
        others = settings.get("members_enabled") == "1" or settings.get("newsletter_mode") == "builtin"
        return check("email", "email", CRITICAL if others else RECOMMENDED, "Email only reaches you",
                     "Your From address is at resend.dev, which Resend keeps for trying it out: emails go only to "
                     "you. Members' sign-in links, comment confirmations and the newsletter don't arrive. Add your "
                     "domain in Resend and send from an address there, or use an email account you have.",
                     "Open Email", "/admin/settings?tab=email")
    sent = _ago(ok_at)
    if sent is None:
        return check("email", "email", GOOD, "Email is set up",
                     "Nothing's been sent yet - send yourself a test to be sure it arrives.",
                     "Send a test", "/admin/settings?tab=email")
    return check("email", "email", GOOD, "Email is set up", f"The last one went out {_days(sent)}.")


def address_check(request_host: str):
    """The site's address (BASE_URL, or Settings > Site) is what links in
    emails, feeds and the fediverse use - it should be the one the site's
    reached at."""
    configured = urlparse(config.BASE_URL).hostname or ""
    if not request_host or request_host in ("localhost", "127.0.0.1", "testserver"):
        return None
    where = ("How to set it", "/admin/help?tab=deployment#settings-on-the-host") if config.BASE_URL_FIXED else \
        ("Change the URL", "/admin/settings?tab=url#site_url")
    if not config.BASE_URL_FIXED and config.BASE_URL == config.LOCAL_URL:
        return check("address", "domain", RECOMMENDED, "The site URL isn't set",
                     f"Links in emails, feeds and shares say localhost. Set it to the URL readers use - "
                     f"probably https://{request_host}.", "Set the URL", where[1])
    if is_local():
        return None
    name = "BASE_URL" if config.BASE_URL_FIXED else "The site URL"
    if request_host.lower() == configured.lower():
        return check("address", "domain", GOOD, f"{name} matches the URL you're using, {configured}",
                     "Links in emails, feeds and shares point to the right place.")
    return check("address", "domain", RECOMMENDED, f"{name} doesn't match the URL you're using",
                 f"It's set to {configured}, but you're on {request_host}. Links in emails, feeds and shares "
                 "would point to the wrong place" + (" - set BASE_URL on your host to the URL readers use."
                                                      if config.BASE_URL_FIXED else "."), *where)


def disk_check():
    try:
        usage = shutil.disk_usage(config.data_dir())
    except OSError:
        return None
    from soloblog.backup import size_label
    free_share = usage.free / usage.total if usage.total else 1
    free = size_label(usage.free)
    if free_share < 0.05 or usage.free < 200 * 1024 * 1024:
        return check("disk", "storage", CRITICAL, f"The disk is almost full - {free} free",
                     "New images, backups and even saving posts can fail. Clear what's listed under Disk space "
                     "below, or give the server more room.", "See what's using it", "#disk")
    if free_share < 0.15:
        return check("disk", "storage", RECOMMENDED, f"The disk is getting full - {free} free",
                     "Clear what's listed under Disk space below before it runs out.", "See what's using it",
                     "#disk")
    return check("disk", "storage", GOOD, f"{free} free on the disk", "Plenty of room.")


def data_kept() -> bool:
    """False when the data folder is in the container's own files, not on
    a disk or volume - a redeploy or restart starts it empty. A server's
    own disk (no container) always keeps it."""
    if host_kind() == "other" or is_local() or config.DEMO_MODE:
        return True
    path = os.path.realpath(config.data_dir())
    while path != os.path.dirname(path):
        if os.path.ismount(path):
            return True
        path = os.path.dirname(path)
    return False


# what to do about it on each host, in its own words
KEEP_IT = {
    "Railway": "In Railway, add a volume to this service, mounted at {dir}.",
    "Render": "In Render, add a disk to this service, mounted at {dir} - disks need a paid instance.",
    "Fly.io": "Create a volume (fly volumes create blog_data) and mount it at {dir} in fly.toml.",
    "Heroku": "Heroku can't keep files: move to a host with a disk, or connect cloud storage for backups.",
    "Koyeb": "In Koyeb, add a volume to this service, mounted at {dir}.",
}


def keep_it() -> str:
    return KEEP_IT.get(host_kind(), "Give the container a volume mounted at {dir}.").format(dir=config.data_dir())


def storage_check():
    if data_kept():
        return None
    from soloblog import storage
    fix = keep_it()
    if storage.enabled() and config.S3_RESTORE_ON_BOOT:
        return check("kept", "storage", RECOMMENDED, "Your site is put back from your bucket on each start",
                     "It isn't on lasting storage, so each update starts empty and brings back the last backup - "
                     f"a change from the last minute could be lost. {fix}")
    return check("kept", "storage", CRITICAL, "Your posts will be lost on the next update",
                 f"They're kept inside the app, not on lasting storage, so an update or restart starts empty. "
                 f"Download a backup now, then: {fix}", "Back up now", "/admin/settings?tab=backup")


DB_CHECK_EVERY = timedelta(days=7)


def integrity() -> str:
    """SQLite's quick_check, on a connection of its own, opened for it and
    closed after. Not the app's: those stay open for the life of their
    thread, and the search index (FTS5) keeps a copy of its structure per
    connection - checked on one that another connection has since written
    through, it reported a "checksum mismatch" that wasn't there."""
    conn = None
    try:
        conn = sqlite3.connect(config.db_path(), timeout=10)
        return conn.execute("PRAGMA quick_check").fetchone()[0]
    except sqlite3.Error as e:
        return str(e)
    finally:
        if conn:
            conn.close()


def database_check():
    """SQLite's own quick_check, at most once a week - it reads every page,
    so it's not for every visit."""
    last = _ago(settings.get("db_check_at"))
    if last is None or last > DB_CHECK_EVERY:
        result = integrity()
        settings.set_many({"db_check_at": utcnow().isoformat(), "db_check_result": result})
    result = settings.get("db_check_result")
    if result == "ok":
        return check("database", "storage", GOOD, "The database checks out",
                     "SQLite's own integrity check passed. It runs once a week.")
    return check("database", "storage", CRITICAL, "The database reports a problem",
                 f"Its integrity check said: {result[:200]}. Download a backup now, then restore it to a fresh "
                 "site if things go wrong.", "Open Backup and import", "/admin/settings?tab=backup")


def visibility_checks():
    out = []
    if settings.get("search_noindex") == "1":
        out.append(check("noindex", "visibility", RECOMMENDED, "Your site is hidden from search engines",
                         "Fine while it's private or unfinished - easy to forget once it's ready.",
                         "Open Search engines", "/admin/settings?tab=url"))
    else:
        out.append(check("noindex", "visibility", GOOD, "Search engines can find your site",
                         "It has a sitemap and isn't asking to be hidden."))
    if (settings.get("site_title") or "").strip() in ("", "My Blog"):
        out.append(check("title", "visibility", RECOMMENDED, "Your site still has the default title",
                         "It's what shows in browser tabs, search results and shares.",
                         "Change it", "/admin/settings?tab=name"))
    return out


def scheduler_check():
    """The background check that publishes scheduled posts and sends what
    goes with them - a stopped one means nothing scheduled goes out."""
    from soloblog import publishing
    if not publishing.AUTOMATIC or publishing.last_run() is None:
        return None
    idle = utcnow().timestamp() - publishing.last_run()
    if idle > publishing.INTERVAL * 10:
        return check("scheduler", "background", CRITICAL, "Scheduled posts aren't being published",
                     f"The check that publishes them last ran {int(idle // 60)} minutes ago. Restart the "
                     "server; if it happens again, report it.", "Report a problem",
                     f"{config.PROJECT_URL}/issues/new/choose")
    return check("scheduler", "background", GOOD, "Scheduled posts go out on time",
                 "The check that publishes them runs every minute.")


# ---- One running copy: the data folder is this process's alone
# Scheduled posts, the fediverse queues, mirrors and backups run in
# threads of the one process that serves the site. A second copy on the
# same folder (two containers, or a server started with several workers)
# runs them twice, or each half the time - so each copy claims the folder
# with a lock, and one that can't get it says so in Site health.
SHARED_KEY = "second_copy_seen_at"
CLAIM_TRIES, CLAIM_WAIT = 24, 5  # two minutes: the old copy may still be stopping during an update
_claim = None  # the open lock file, held for the life of the process


def lock_path() -> str:
    return os.path.join(config.data_dir(), ".running")


def claim_data() -> bool:
    """Take the data folder's lock. True when this process holds it."""
    global _claim
    if _claim is not None:
        return True
    try:
        import fcntl
    except ImportError:  # Windows: run for development only, one copy
        return True
    f = open(lock_path(), "a")  # noqa: SIM115 - held open for as long as this copy runs
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close()
        return False
    _claim = f
    return True


def claim_or_report():
    """Claim the folder, waiting a while for a copy that's stopping - and
    if another copy keeps it, say so."""
    for _ in range(CLAIM_TRIES):
        if claim_data():
            if settings.get(SHARED_KEY):
                settings.set_many({SHARED_KEY: ""})
            return
        time.sleep(CLAIM_WAIT)
    logging.getLogger(__name__).warning(
        "Another copy of Soloblog is running on the same data folder (%s) - run only one", config.data_dir())
    settings.set_many({SHARED_KEY: utcnow().isoformat(timespec="seconds")})


def watch_for_second_copy():
    """At start: claim_or_report, in the background - the site is served
    meanwhile."""
    import threading
    threading.Thread(target=claim_or_report, name="one-copy", daemon=True).start()


def copies_check():
    """Two copies sharing the data folder - only shown when there are."""
    if not settings.get(SHARED_KEY):
        return None
    return check("copies", "background", CRITICAL, "Two copies of Soloblog share this site's data",
                 "Scheduled posts, emails and backups can go out twice or not at all. Run one copy: "
                 "one container, or one server process started with python app.py.",
                 "Read the hosting guide", "/admin/help?tab=deployment#what-it-needs")


def payments_check():
    """Paid members: whether readers can pay - and if one couldn't, why."""
    from soloblog import members
    from soloblog import stripe_members as pay
    s = settings.get_all()
    if not members.enabled(s) or not s.get("stripe_key"):
        return None
    where = ("Open Members", "/admin/settings?tab=members")
    error, failed_at = s.get("stripe_last_error"), s.get("stripe_last_failed_at")
    if error and failed_at and failed_at >= (s.get("stripe_last_ok_at") or ""):
        return check("payments", "payments", CRITICAL, "A reader couldn't pay",
                     f"Stripe said: {error}. Check the Stripe key and its permissions, then try paying with a "
                     "test card.", *where)
    if not pay.ready(s):
        return check("payments", "payments", RECOMMENDED, "Paid members aren't finished",
                     "Readers can't pay yet - add a price and save, at the site's own https:// URL, so "
                     "Stripe can tell it about payments.", *where)
    if pay.test_mode():
        return check("payments", "payments", RECOMMENDED, "Payments are in test mode",
                     "Nobody is really charged. When it works the way you want, use a live key.", *where)
    return check("payments", "payments", GOOD, "Readers can pay",
                 "Through Stripe, which tells the site about each payment.")


def run(request_host: str = "") -> list:
    """Every check, the stored results of the remote ones with them -
    most serious first, then by area."""
    from soloblog import health_remote
    results = [updates_check(), backup_check(), bucket_images_check(), verify_check(), https_check(), secret_check(), login_check(),
               recovery_check(), email_check(), address_check(request_host), storage_check(), disk_check(),
               database_check(), *visibility_checks(), payments_check(), scheduler_check(), copies_check(),
               *health_remote.stored()]
    results = [r for r in results if r]
    area_order = list(AREAS)
    return sorted(results, key=lambda r: (ORDER[r["status"]], area_order.index(r["area"])))


def overall(results) -> str:
    statuses = {r["status"] for r in results}
    return CRITICAL if CRITICAL in statuses else RECOMMENDED if RECOMMENDED in statuses else GOOD


def info() -> list:
    """(section, [(label, value)]) for the Info tab and a bug report - no
    secrets, ever: only whether one is set."""
    from soloblog import mail, storage
    from soloblog.db import get_db
    db = get_db()
    count = lambda q: db.execute(q).fetchone()[0]  # noqa: E731
    try:
        db_size = os.path.getsize(config.db_path())
    except OSError:
        db_size = 0
    from soloblog.backup import size_label
    s = settings.get_all()
    return [
        ("Soloblog", [("Version", config.VERSION), ("Mode", "production" if config.IS_PROD else "development"),
                      # how the address is set, never the address - a bug report is pasted in public
                      ("URL", ("https" if config.BASE_URL.startswith("https://") else "http") + ", " +
                       ("set on the host" if config.BASE_URL_FIXED else
                        "from Settings" if settings.get("site_url") else
                        "the host's own" if config.PLATFORM_URL else "not set")),
                      ("Demo", "yes" if config.DEMO_MODE else "no")]),
        ("Server", [("Python", sys.version.split()[0]), ("SQLite", sqlite3.sqlite_version),
                    ("System", f"{platform.system()} {platform.release()}"), ("Machine", platform.machine())]),
        ("Content", [("Posts and pages", f"{count('SELECT COUNT(*) FROM posts'):,}"),  # noqa: S608 - fixed query
                     ("Comments", f"{count('SELECT COUNT(*) FROM comments'):,}"),  # noqa: S608 - fixed query
                     ("Database", size_label(db_size))]),
        ("Settings", [("Language", s.get("site_language") or "en"), ("Palette", f"{s['theme']} / {s['theme_dark']}"),
                      ("Comments", (s.get("comments_system") or "Soloblog's own")
                       if s.get("comments_enabled") == "1" else "off"),
                      ("Email", {"smtp": "SMTP", "api": "Resend"}.get(s.get("email_provider"), "off")
                       if mail.can_send() else "off"),
                      ("Newsletter", s.get("newsletter_mode") or "off"),
                      ("Cloud storage", "on" if storage.enabled() else "off"),
                      ("Update hook", "set" if s.get("update_hook_url") else "not set"),
                      ("Remote checks", "on" if s.get("health_remote") != "0" else "off")]),
        ("Features in use", features()),
    ]


def _about(n: int) -> str:
    """A count as a rough range - enough to know a site's size, not to
    tell one site from another."""
    for top, label in ((0, "none"), (9, "1-9"), (49, "10-49"), (199, "50-199"), (999, "200-999")):
        if n <= top:
            return label
    return "1,000+"


def host_kind() -> str:
    """Where it runs, from what the host itself sets - no lookup. An app
    store's package of Soloblog (deploy/platforms) names its platform in
    HOSTED_ON, where the platform itself sets nothing to tell by."""
    env = os.environ
    named = (env.get("HOSTED_ON") or "").strip()
    if named:
        return named[:40]
    for name, label in (("FLY_APP_NAME", "Fly.io"), ("RENDER", "Render"), ("RAILWAY_ENVIRONMENT", "Railway"),
                        ("KOYEB_APP_NAME", "Koyeb"), ("DYNO", "Heroku"), ("KUBERNETES_SERVICE_HOST", "Kubernetes")):
        if env.get(name):
            return label
    return "Docker" if os.path.exists("/.dockerenv") else "other"


def features() -> list:
    """Which features this site uses - on or off, a service's name, rough
    counts - for a bug report, so whoever reads it knows what's in play.
    Nothing that names the site or its readers: no titles, addresses or
    text. Only ever shared by the admin copying it."""
    from soloblog import members, post_templates, posts, sections, stripe_members
    from soloblog.db import get_db
    db = get_db()
    one = lambda q, *a: db.execute(q, a).fetchone()[0]  # noqa: E731
    s = settings.get_all()
    on = lambda key: "on" if s.get(key) == "1" else "off"  # noqa: E731
    if not members.enabled(s):
        membership = "off"
    elif stripe_members.ready(s):
        membership = "free and paid (" + ("test mode" if "_test_" in s.get("stripe_key", "") else "live") + ")"
    else:
        membership = "free"
    used = {}
    for row in db.execute("SELECT slug FROM posts"):
        for name in re.findall(r"(?mi)^Section:[ \t]*(\S[^\n]*?)[ \t]*$", posts.load_post_body(row["slug"])):
            kind = sections.NAMES.get(name.lower())
            if kind:
                used[kind] = used.get(kind, 0) + 1
    in_use = ", ".join(f"{sections.REGISTRY[k]['label']} ({_about(n)})"
                       for k, n in sorted(used.items(), key=lambda item: (-item[1], item[0])))
    return [
        ("Host", host_kind()),
        ("Homepage", "a page" if s.get("home_page") else "the blog"),
        ("Members", membership),
        ("Member count", _about(one("SELECT COUNT(*) FROM members"))),
        ("Newsletter subscribers", _about(one("SELECT COUNT(*) FROM subscribers WHERE confirmed_at IS NOT NULL"))),
        ("Posts for members", _about(one("SELECT COUNT(*) FROM posts WHERE visibility != 'public'"))),
        ("Scheduled posts", _about(one("SELECT COUNT(*) FROM posts WHERE scheduled_at != ''"))),
        ("Series", "used" if one("SELECT COUNT(*) FROM posts WHERE series_name != ''") else "not used"),
        ("Sections in use", in_use or "none"),
        ("Custom templates", _about(len(post_templates.saved()))),
        ("Fediverse", on("activitypub_enabled")),
        ("Webmentions", f"receive {on('webmention_receive')}, send {on('webmention_send')}"),
        ("Sharing", ", ".join(n for n, k in (("Bluesky", "crosspost_bluesky"), ("Mastodon", "crosspost_mastodon"))
                              if s.get(k) == "1") or "off"),
        ("Translations", s.get("translate_provider") or "off"),
        ("Contact form", (s.get("contact_service") or "Soloblog's own") if s.get("contact_enabled") == "1" else "off"),
        ("Spam check", s.get("captcha_provider") or "off"),
        ("Analytics", s.get("analytics_provider") or "off"),
        ("Ads", "on" if s.get("adsense_client") else "off"),
        ("Custom code", "set" if s.get("custom_css") or s.get("custom_head") else "none"),
        ("Two-factor authentication", "on" if one("SELECT COUNT(*) FROM admin WHERE totp_secret != ''") else "off"),
        ("Passkeys", _about(one("SELECT COUNT(*) FROM passkeys"))),
    ]


def info_text(host: str = "") -> str:
    """The Info tab as plain text, to paste into a bug report - with the
    recent problems from the log, cleaned (problems_report)."""
    lines = []
    for section, rows in info():
        lines.append(f"## {section}")
        lines += [f"- {label}: {value}" for label, value in rows]
        lines.append("")
    recent = problems_report(host)
    if recent:
        lines += ["## Recent problems", recent, ""]
    return "\n".join(lines).strip()


# Site health > Log: the problems Soloblog logs - warnings and errors, not
# routine events - kept on the data disk for two weeks, in at most two files
# of 256 KB, so it can never fill a disk. Not in backups (backup.py copies
# posts, media and the database by name).
LOG_DIR = os.path.join(config.data_dir(), "logs")
LOG_PATH = os.path.join(LOG_DIR, "problems.log")
LOG_DAYS = 14


class _LogLine(logging.Formatter):
    """One JSON line per problem: when (UTC), how bad, where, what, and the
    traceback when there was one."""
    def format(self, record):
        return json.dumps({
            "at": datetime.fromtimestamp(record.created, UTC).replace(tzinfo=None).isoformat(timespec="seconds"),
            "level": record.levelname, "where": record.name, "message": record.getMessage(),
            "detail": self.formatException(record.exc_info) if record.exc_info else "",
        })


class _LogFile(RotatingFileHandler):
    # the folder is made when there's first something to write - not on
    # start, when the demo checks its data folder is empty
    def _open(self):
        os.makedirs(LOG_DIR, exist_ok=True)
        return super()._open()


def log_handler() -> logging.Handler:
    """Where Soloblog's warnings and errors are kept (app.py adds it)."""
    handler = _LogFile(LOG_PATH, maxBytes=256 * 1024, backupCount=1, encoding="utf-8", delay=True)
    handler.setLevel(logging.WARNING)
    handler.setFormatter(_LogLine())
    return handler


# The detailed log, beside it: everything Soloblog notes - its routine
# steps, each page and admin action, and the problems in full - for four
# weeks, downloaded from Site health > Log for working out what happened.
# One file a day; older than DETAIL_DAYS goes, and the oldest days go
# first past DETAIL_MAX, so a busy site can't fill a disk. Never visitors'
# addresses or browsers, nor anything after a ? (reset and preview links).
DETAIL_DIR = os.path.join(LOG_DIR, "detail")
DETAIL_DAYS = 28
DETAIL_MAX = 20 * 1024 * 1024


class _DetailFile(logging.Handler):
    def __init__(self):
        super().__init__(logging.INFO)
        self.setFormatter(logging.Formatter("%(asctime)s UTC  %(levelname)-7s %(name)s  %(message)s",
                                            "%Y-%m-%d %H:%M:%S"))
        self.formatter.converter = time.gmtime
        self._day = None

    def emit(self, record):
        try:
            if _detail_off():
                return
            day = time.strftime("%Y-%m-%d", time.gmtime(record.created))
            # every time, not once a day: Clear or a restore may have taken it
            os.makedirs(DETAIL_DIR, exist_ok=True)
            if day != self._day:
                self._day = day
                prune_detail()
            with open(os.path.join(DETAIL_DIR, f"{day}.log"), "a", encoding="utf-8") as f:
                f.write(self.format(record) + "\n")
        except Exception:
            self.handleError(record)


def _detail_off() -> bool:
    try:
        return settings.get("detail_log") == "0"
    except (sqlite3.Error, OSError):  # before the database is ready (the first migration): on
        return False


def detail_handler() -> logging.Handler:
    """Where everything Soloblog notes is kept, for the download (app.py adds it)."""
    return _DetailFile()


def _detail_files() -> list[str]:
    try:
        return sorted(os.path.join(DETAIL_DIR, n) for n in os.listdir(DETAIL_DIR) if n.endswith(".log"))
    except OSError:
        return []


def prune_detail():
    """Days older than DETAIL_DAYS go, then the oldest while it's past DETAIL_MAX."""
    oldest = (utcnow() - timedelta(days=DETAIL_DAYS)).strftime("%Y-%m-%d")
    files = _detail_files()
    for path in [f for f in files if os.path.basename(f)[:10] < oldest]:
        with contextlib.suppress(OSError):
            os.remove(path)
    files = _detail_files()
    total = sum(os.path.getsize(f) for f in files if os.path.exists(f))
    while files[:-1] and total > DETAIL_MAX:
        path = files.pop(0)
        try:
            total -= os.path.getsize(path)
            os.remove(path)
        except OSError:
            pass


def detail_text(host: str = "") -> str:
    """The detailed log as one file, oldest first, with a word on what it is."""
    days = _detail_files()
    if not days:
        return ""
    head = [f"Soloblog {config.VERSION} - detailed log for {host or config.BASE_URL}",
            f"The last {DETAIL_DAYS} days as recorded, oldest first, times in UTC.",
            "It holds personal details - email addresses, the pages people visited, what was written.",
            "Keep it to yourself or someone helping you; to share in public, use Copy for a bug report.", ""]
    body = []
    for path in days:
        try:
            with open(path, encoding="utf-8") as f:
                body.append(f.read())
        except OSError:
            continue
    return "\n".join(head) + "\n" + "".join(body)


def has_detail() -> bool:
    return bool(_detail_files())


def clear_detail():
    for path in _detail_files():
        with contextlib.suppress(OSError):
            os.remove(path)


def problems(days: int = LOG_DAYS) -> list[dict]:
    """The logged problems from the last `days`, newest first."""
    since = (utcnow() - timedelta(days=days)).isoformat(timespec="seconds")
    found = []
    for path in (LOG_PATH + ".1", LOG_PATH):
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                    except ValueError:
                        continue
                    if isinstance(entry, dict) and entry.get("at", "") >= since:
                        found.append(entry)
        except OSError:
            continue
    # the files are in the order things happened: reversed, the newest of
    # the same second comes first too
    return sorted(reversed(found), key=lambda e: e["at"], reverse=True)


def clear_log():
    for path in (LOG_PATH + ".1", LOG_PATH):
        # emptied, not removed - the handler may have it open
        with contextlib.suppress(OSError), open(path, "w"):
            pass


# a logger's name (its module) as the part of the site it's about
_WHERE = {"app": "The site", "db": "Database", "mail": "Email", "storage": "Cloud storage", "backup": "Backups",
          "fediverse": "Fediverse", "webmention": "Webmentions", "publishing": "Publishing",
          "health_remote": "Site health", "health_alerts": "Site health", "translate": "Translation",
          "importers": "Import", "images": "Media", "appicon": "App icon", "passkeys": "Passkeys",
          "captcha": "Spam check", "crosspost": "Sharing", "notify": "Notifications",
          "updates": "Updates", "stock": "Stock photos",
          "formservices": "Contact form", "demo": "The demo", "posts": "Posts"}


def log_where(name: str) -> str:
    part = name.rsplit(".", 1)[-1]
    return _WHERE.get(part, part.replace("_routes", "").replace("_", " ").capitalize())


# what could say whose site it is, taken out before a problem is copied
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
_LINK = re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s'\"<>)]+", re.I)
# IPv4, and IPv6 with three colons or "::" - a time like 09:00:12 has two
_ADDRESS = re.compile(r"\b\d{1,3}(\.\d{1,3}){3}\b|\b(?:[0-9a-f]{1,4}:){3,7}[0-9a-f]{1,4}\b|(?<![\w:])(?:[0-9a-f]{1,4}:)*[0-9a-f]{0,4}::[0-9a-f:]*",
                      re.I)
# a key or token: long, with letters and digits - a long name in the code has no digits
_TOKEN = re.compile(r"\b(?=[A-Za-z0-9_-]*\d)(?=[A-Za-z0-9_-]*[A-Za-z])[A-Za-z0-9_-]{24,}\b")
_FILE = re.compile(r"[\w.-]+\.(?:jpe?g|png|gif|webp|svg|avif|heic|pdf|mp3|m4a|ogg|wav|flac|mp4|webm|mov|md|zip)\b", re.I)
# a page's address names a post, a tag or a file: the kind stays, the name goes
_SITE_PATH = re.compile(r"(/(?:post|tag|uploads|wiki|admin/edit|[a-z]{2}/post)/)[^\s'\"]+")
_FRAME = re.compile(r'File "[^"]*?(soloblog/[^"]+)", line (\d+), in (\w+)')


def clean_for_report(text: str, host: str = "") -> str:
    """text without email addresses, links, IP addresses, keys and tokens,
    file names, the data folder's path or the site's own address."""
    if host:
        text = re.sub(re.escape(host), "[your site]", text, flags=re.I)
    text = _EMAIL.sub("[email]", text)
    text = _LINK.sub("[link]", text)
    text = text.replace(os.path.abspath(config.data_dir()), "[data folder]")
    text = _SITE_PATH.sub(r"\1[name]", text)
    text = _FILE.sub("[file]", text)
    text = _TOKEN.sub("[key]", text)
    return _ADDRESS.sub("[address]", text)


def grouped_problems(days: int = LOG_DAYS) -> list[dict]:
    """problems(), the same one over and over shown once: its newest time,
    and how many times ("times")."""
    first = {}
    for e in problems(days):
        key = (e["where"], e["message"])
        if key in first:
            first[key]["times"] += 1
        else:
            first[key] = {**e, "times": 1}
    return list(first.values())


def problems_report(host: str = "", limit: int = 20, days: int = 7) -> str:
    """The last few problems, cleaned, for a bug report: when, where and
    what, the error's last line, and where in Soloblog's own code it was."""
    out = []
    for e in grouped_problems(days)[:limit]:
        times = f" ({e['times']} times)" if e["times"] > 1 else ""
        out.append(f"- {e['at'].replace('T', ' ')} UTC · {log_where(e['where'])} · {e['level'].lower()}: "
                   f"{clean_for_report(e['message'], host)}{times}")
        if e.get("detail"):
            frames = [f"{path}:{line} {fn}" for path, line, fn in _FRAME.findall(e["detail"])][-3:]
            last = e["detail"].strip().splitlines()[-1]
            out.append(f"  {clean_for_report(last, host)}" + (f" ({' < '.join(reversed(frames))})" if frames else ""))
    return "\n".join(out)
