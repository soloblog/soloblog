"""Site health's alerts: a dot on Site health in the admin menu while
something needs attention, and an email when something becomes critical
- once a week at most for the same problem, to the admin's own address,
only with email set up (Site health > How it checks)."""
import json
from datetime import timedelta
from soloblog.tz import utcnow

from soloblog import config
from soloblog import health
from soloblog import settings

AGAIN_AFTER = timedelta(days=7)


def note(results):
    """Keeps how many checks need attention, for the menu's dot - so the
    menu needn't run them on every page."""
    count = sum(1 for r in results if r["status"] == health.CRITICAL)
    if settings.get("health_critical") != str(count):
        settings.set_many({"health_critical": str(count)})


def needs_attention() -> int:
    try:
        return int(settings.get("health_critical") or 0)
    except ValueError:
        return 0


def _alerted() -> dict:
    try:
        data = json.loads(settings.get("health_alerted") or "{}")
        return data if isinstance(data, dict) else {}
    except ValueError:
        return {}


def check_and_send(results=None):
    """Runs the checks (or takes their results), keeps the count, and emails
    about any critical one not emailed about in the last week. Returns
    the checks it emailed about."""
    from soloblog import mail
    results = health.run() if results is None else results
    note(results)
    critical = {r["key"]: r for r in results if r["status"] == health.CRITICAL}
    alerted = {k: v for k, v in _alerted().items() if k in critical}  # one that's put right can alert again
    to = settings.get("admin_email")
    due = [r for k, r in critical.items()
           if health._ago(alerted.get(k)) is None or health._ago(alerted.get(k)) > AGAIN_AFTER]
    if not due or settings.get("health_alerts") == "0" or not to or not mail.can_send():
        if alerted != _alerted():
            settings.set_many({"health_alerted": json.dumps(alerted)})
        return []
    site = settings.get("site_title") or "your site"
    one = len(due) == 1
    lines = [f"Site health found a problem on {site} that needs your attention:" if one else
             f"Site health found {len(due)} problems on {site} that need your attention:", ""]
    for r in due:
        lines += [f"- {r['title']}", f"  {r['why']}", ""]
    lines += ["See how to fix it:" if one else "See how to fix each one:", f"{config.BASE_URL}/admin/health", "",
              "You get this at most once a week for the same problem. To stop these emails, open "
              "Site health > How it checks.", ""]
    subject = f"{site}: {due[0]['title']}" if len(due) == 1 else f"{site}: {len(due)} things need attention"
    if mail.send_email(to, subject, "\n".join(lines)):
        now = utcnow().isoformat()
        alerted.update({r["key"]: now for r in due})
    settings.set_many({"health_alerted": json.dumps(alerted)})
    return due
