from soloblog.tz import utcnow

from fasthtml.common import *

from soloblog import config
from soloblog import health
from soloblog import posts
from soloblog import settings
from soloblog.ui import Layout, PageHeader, Tabs, TABS_CLS, SettingsPanel, ToggleField, FIELD_GAP, SYNC_SVG, GoLink
from soloblog.ui import EmptyState, TRASH_SVG, DOWNLOAD_SVG
from soloblog import tz
from datetime import datetime

ar = APIRouter()


def _svg(d, cls):
    return NotStr(f'<svg xmlns="http://www.w3.org/2000/svg" class="{cls}" fill="none" viewBox="0 0 24 24" '
                  f'stroke="currentColor" stroke-width="2" aria-hidden="true"><path stroke-linecap="round" '
                  f'stroke-linejoin="round" d="{d}"/></svg>')


# heroicons: a circled !, a triangle !, a circled tick
_ICON = {
    health.CRITICAL: ("M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z", "text-error"),
    health.RECOMMENDED: ("M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 "
                         "1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v"
                         "-.008Z", "text-warning"),
    health.GOOD: ("M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z", "text-success"),
}
_SAYS = {health.CRITICAL: "Something needs your attention", health.RECOMMENDED: "A few things could be better",
         health.GOOD: "Your site is in good shape"}
_STATUS_WORD = {health.CRITICAL: "Needs attention", health.RECOMMENDED: "Recommended", health.GOOD: "Passed"}


def icon(status, size="h-5 w-5"):
    d, colour = _ICON[status]
    return Span(_svg(d, size), cls=f"{colour} shrink-0 flex")


def CheckRow(r):
    """One check: its icon, what it found and its area; opened, why it
    matters and the way to put it right."""
    action = r.get("action")
    return Details(
        Summary(
            icon(r["status"]),
            Span(r["title"], cls="flex-1 min-w-0 font-medium text-sm"),
            # what its action did (Verify a backup) - in the row, open or folded
            Span(id=f"status-{r['key']}", data_status_slot=True, role="status", cls="text-xs shrink-0 empty:hidden")
            if action else None,
            Span(health.AREAS[r["area"]], cls="badge badge-sm badge-ghost shrink-0 max-sm:hidden"),
            Span(_STATUS_WORD[r["status"]], cls="sr-only"),
            cls="collapse-title flex items-center gap-3 min-h-0 py-3 pe-10"
        ),
        Div(
            P(r["why"], cls="text-sm text-base-content/70"),
            # where it's put right is a link; something done here, a button -
            # both at the right, as a card's actions are
            Div(
                GoLink(r["fix"], r["href"]) if r.get("fix") and r.get("href") else None,
                Form(Button(SYNC_SVG, Span(action[0], cls="ml-1"), type="submit", cls="btn btn-sm"),
                     action=action[1], method="post") if action else None,
                cls="flex flex-wrap items-center justify-end gap-3 mt-3")
            if (r.get("fix") and r.get("href")) or action else None,
            cls="collapse-content"
        ),
        id=f"check-{r['key']}",
        cls="collapse collapse-arrow join-item border-[length:var(--border)] border-base-300 bg-base-100"
    )


def Group(title, rows, key):
    """Needs attention, Recommended or Passed: a card like Disk space's,
    open to start with and remembered folded if you fold it."""
    if not rows:
        return None
    return Div(SettingsPanel(f"{title} ({len(rows)})", Div(*[CheckRow(r) for r in rows],
                                                          cls="join join-vertical w-full"),
                             key=f"health-{key}"), cls="mb-3")


def Summary_(results, checked_at):
    status = health.overall(results)
    counts = {s: sum(1 for r in results if r["status"] == s) for s in _ICON}
    parts = [f"{counts[s]} {w}" for s, w in (
        (health.CRITICAL, "needs attention" if counts[health.CRITICAL] == 1 else "need attention"),
        (health.RECOMMENDED, "recommended"), (health.GOOD, "passed")) if counts[s]]
    return Div(
        icon(status, "h-10 w-10"),
        Div(H2(_SAYS[status], cls="text-lg font-semibold"),
            P(" · ".join(parts), cls="text-sm text-base-content/60"),
            P(f"Certificate, domain and email checked {checked_at}" if checked_at else
              "Certificate, domain and email not checked yet",
              cls="text-xs text-base-content/50 mt-1") if settings.get("health_remote") != "0" else None,
            # min-w-48: on a phone the button goes underneath rather than squeeze this
            cls="flex-1 min-w-48"),
        Span(id="check-again-status", data_status_slot=True, role="status", cls="text-xs empty:hidden")
        if settings.get("health_remote") != "0" else None,
        Form(Button(SYNC_SVG, Span("Check again", cls="ml-1"), type="submit", cls="btn btn-sm"),
             action="/admin/health/refresh", method="post", cls="shrink-0")
        if settings.get("health_remote") != "0" else None,
        cls="flex flex-wrap items-center gap-4 p-5 mb-6 rounded-box border-[length:var(--border)] border-base-300 "
            "bg-base-100"
    )


def OptionsPanel(s):
    return SettingsPanel(
        "How it checks",
        Form(
            ToggleField("Check certificate, domain and email", "health_remote",
                        checked=s.get("health_remote") != "0",
                        help="Once a day, from services on the internet. Only domain names are sent.",
                        cls=FIELD_GAP),
            ToggleField("Keep a detailed log", "detail_log", checked=s.get("detail_log") != "0",
                        help="Four weeks of everything your site does, kept on your server, to download from Log "
                             "when something needs working out.", cls=FIELD_GAP),
            ToggleField("Email me when something needs attention", "health_alerts",
                        checked=s.get("health_alerts") != "0",
                        help=Span("To ", A("your email", href="/admin/settings?tab=email#admin_email", cls="link"),
                                  ", once a week at most for the same problem. Needs email set up.")),
            Span(id="health-options-status", data_status_slot=True, role="status", cls="text-xs"),
            hx_post="/admin/health/options", hx_trigger="change", hx_target="#health-options-status",
            hx_swap="outerHTML", data_declare_fields=True
        ),
        key="health-options"
    )


def InfoTab(host=""):
    recent = health.problems_report(host)
    return Div(
        Div(P("What's running, which features are on and the latest problems, for a bug report - copied for you "
              "to paste, never sent. No passwords, keys, text or names.",
              cls="text-sm text-base-content/60"),
            Div(Button("Copy for a bug report", type="button", cls="btn btn-sm",
                       data_copy=health.info_text(host), data_copied="Copied"),
                A("Report a problem", href=f"{config.PROJECT_URL}/issues/new/choose", target="_blank",
                  rel="noopener", cls="btn btn-sm btn-ghost"), cls="flex flex-wrap gap-2"),
            cls="flex flex-wrap items-center justify-between gap-3 mb-4"),
        *[SettingsPanel(section, Table(Tbody(*[Tr(Th(label, cls="font-normal text-base-content/60 w-40"),
                                                  Td(value, cls="break-all")) for label, value in rows]),
                                       cls="table table-sm"), key=f"health-info-{section.lower()}")
          for section, rows in health.info()],
        # exactly what's copied of the log, so nothing goes unseen
        SettingsPanel("Recent problems",
                      P("From the last week, without email addresses, links, IP addresses, keys or file names.",
                        cls="text-xs text-base-content/60 mb-2"),
                      Pre(recent, cls="text-xs whitespace-pre-wrap break-words bg-base-200 rounded-box p-3"),
                      key="health-info-problems") if recent else None,
        cls="flex flex-col gap-3"
    )


def LogTab():
    """The problems from the last two weeks, newest first - the same one
    over and over shown once, with how many times."""
    entries = health.grouped_problems()[:200]
    clear = Form(Input(type="hidden", name="back", value="log"),
                 Button(TRASH_SVG, Span("Clear", cls="ml-1"), type="button", cls="btn btn-sm btn-ghost",
                        data_confirm="Clear the problems log? New problems are kept again as they happen."),
                 action="/admin/disk/clear-log", method="post") if entries else None

    def row(e):
        error = e["level"] in ("ERROR", "CRITICAL")
        return Li(
            Div(Span("Error" if error else "Warning",
                     cls=f"badge badge-xs badge-soft {'badge-error' if error else 'badge-warning'}"),
                Span(health.log_where(e["where"]), cls="font-medium text-sm"),
                Span(f"{e['times']} times" if e["times"] > 1 else "", cls="text-xs text-base-content/60"),
                Span(f"{(when := tz.to_local(datetime.fromisoformat(e['at']))).day} {when:%b, %H:%M}",
                     cls="text-xs text-base-content/60 ms-auto whitespace-nowrap"),
                cls="flex flex-wrap items-center gap-2"),
            P(e["message"], cls="text-sm break-words mt-1"),
            Details(Summary("Details", cls="text-xs link link-hover w-fit"),
                    Pre(e["detail"], cls="text-xs whitespace-pre-wrap break-words bg-base-200 rounded-box p-2 mt-1"),
                    cls="mt-1") if e.get("detail") else None,
            cls="py-3 border-b border-base-300 last:border-0")

    # the detailed log: everything, four weeks, for working out what happened
    # - its own button, apart from Copy for a bug report, saying what's in it
    warning = ("The log has the last four weeks in full - email addresses, the pages people visited and what was "
               "written. Keep it to yourself or someone helping you; to share in public, use Copy for a bug report "
               "(Info).")
    download = Form(Button(DOWNLOAD_SVG, Span("Download detailed log", cls="ml-1"), type="button",
                           cls="btn btn-sm", data_confirm="Download the detailed log? " + warning),
                    action="/admin/health/log/download", method="get") if health.has_detail() else None
    return Div(
        Div(P("Problems from the last two weeks, newest first - where to look when something didn't work.",
              cls="text-sm text-base-content/60"),
            Div(Span(id="log-status", data_status_slot=True, role="status", cls="text-xs empty:hidden"),
                download, clear, cls="flex flex-wrap items-center gap-2"),
            cls="flex flex-wrap items-center justify-between gap-3 mb-2"),
        P(warning, cls="text-xs text-base-content/60 mb-3") if download else
        P("The detailed log is off - turn it on in Status > How it checks." if settings.get("detail_log") == "0"
          else "", cls="text-xs text-base-content/60 mb-3 empty:hidden"),
        SettingsPanel("Log", Ul(*[row(e) for e in entries], cls="flex flex-col"), key="health-log") if entries
        else EmptyState("Nothing's gone wrong lately.", "✓"),
    )


@ar.get("/admin/health")
def health_page(session, request, tab: str = "status"):
    from soloblog import health_remote
    from soloblog.routes.backup_routes import DiskPanel
    tab = tab if tab in ("info", "log") else "status"
    tabs = Tabs(*[A(label, href=f"/admin/health?tab={key}",
                    cls=f"tab tab-sm whitespace-nowrap shrink-0 {'tab-active font-semibold' if key == tab else ''}")
                  for key, label in (("status", "Status"), ("log", "Log"), ("info", "Info"))],
                id="health-tabs", cls=f"{TABS_CLS} mb-4")
    if tab == "info":
        body = InfoTab(request.url.hostname or "")
    elif tab == "log":
        body = LogTab()
    else:
        results = health.run(request.url.hostname or "")
        from soloblog import health_alerts
        health_alerts.note(results)
        by = lambda st: [r for r in results if r["status"] == st]  # noqa: E731
        body = Div(
            Summary_(results, health_remote.checked_label()),
            Group("Needs attention", by(health.CRITICAL), "critical"),
            Group("Recommended", by(health.RECOMMENDED), "recommended"),
            Group("Passed", by(health.GOOD), "passed"),
            Div(DiskPanel(), id="disk", cls="mb-3 scroll-mt-24"),
            OptionsPanel(settings.get_all()),
        )
    return Layout(PageHeader("Site health"), tabs, body,
                  settings=settings.get_all(), logged_in=True, pinned_tree=posts.list_pinned_tree(), admin_page=True)


@ar.post("/admin/health/options")
def health_options(session, request, health_remote: bool = False, health_alerts: bool = False,
                   detail_log: bool = False, declared_fields: str = None):
    settings.set_declared(declared_fields, {"health_remote": "1" if health_remote else "0",
                                            "health_alerts": "1" if health_alerts else "0",
                                            "detail_log": "1" if detail_log else "0"})
    return Span("Saved", id="health-options-status", data_status_slot=True, role="status", cls="text-xs text-success")


@ar.get("/admin/health/log/download")
def download_detail_log(session, request):
    """Site health > Log's Download: the detailed log as one text file. Not
    on the public demo - it would show other visitors' doings."""
    from starlette.responses import Response
    from soloblog.routes.admin_settings import _toast_redirect
    if config.DEMO_MODE:
        from soloblog.demo import BLOCKED_MESSAGE
        return _toast_redirect("/admin/health?tab=log#log-status", BLOCKED_MESSAGE, "error")
    host = request.url.hostname or ""
    text = health.detail_text(host)
    if not text:
        return _toast_redirect("/admin/health?tab=log#log-status", "Nothing's been recorded yet", "error")
    name = f"soloblog-log-{host or 'site'}-{utcnow():%Y-%m-%d}.txt"
    return Response(text, media_type="text/plain; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{name}"', "Cache-Control": "no-store"})


@ar.post("/admin/health/verify")
def health_verify(session):
    """Opens the newest backup in the bucket and checks it would restore -
    restoring nothing."""
    from soloblog import backup, storage
    from soloblog.routes.admin_settings import _toast_redirect
    result = "ok"
    try:
        newest = storage.list_backups()[:1]
        data = storage.get_backup(newest[0]["key"]) if newest else None
        if data is None:
            result = "there's no backup in the bucket yet"
        else:
            import io
            import zipfile
            if not zipfile.is_zipfile(io.BytesIO(data)):
                raise ValueError("it isn't a zip file")
            found = backup.inspect_zip(data)
            # unticked on purpose (Cloud storage) isn't a problem
            if "settings" in storage.backup_categories() and not found["settings"]["present"]:
                result = "it has no settings - your site's settings wouldn't come back"
    except storage.StorageError as e:
        result = f"couldn't read it from the bucket: {e}"
    except Exception as e:  # a damaged zip, a wrong passphrase
        result = f"it couldn't be opened: {e}"
    settings.set_many({"backup_verified_at": utcnow().isoformat(), "backup_verified_result": result})
    if result == "ok":
        return _toast_redirect("/admin/health#status-verify", "The newest backup opened, and it would restore")
    return _toast_redirect("/admin/health#status-verify", "The backup check found a problem", "error")


@ar.post("/admin/health/refresh")
def health_refresh(session, request):
    """Check again: the remote checks, now - at most once a minute."""
    from soloblog import health_remote, ratelimit
    from soloblog.routes.admin_settings import _toast_redirect
    if not ratelimit.hit("site", "health-refresh", limit=1, window_minutes=1):
        return _toast_redirect("/admin/health#check-again-status", "Checked a moment ago - try again in a minute", "error")
    health_remote.refresh()
    return _toast_redirect("/admin/health#check-again-status", "Checked again")
