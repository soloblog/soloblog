"""Settings > Backup and import: download, restore and import, the cloud bucket's backups, and Site health's disk panel."""
import logging
import os
import re
import shutil

from fasthtml.common import *

from soloblog import config
from soloblog import settings
from soloblog import images
from soloblog import backup
from soloblog import posts
from soloblog import tz
from soloblog import storage
from datetime import datetime
from soloblog.tz import utcnow
from soloblog.render import format_date
from soloblog.ui import IconAction, STATUS_BESIDE, STATUS_ROW
from soloblog.ui import RowActions
from soloblog.ui import SCROLLS
from soloblog.ui import CHEVRON_DOWN_SVG, glass_fill
from soloblog.ui import (Layout, Alert, FIELD_GAP, FormField, ToggleField, SettingsPanel,
                SaveStatus,
                DOWNLOAD_SVG, UPLOAD_SVG, RESTORE_SVG, PageHeader, X_SVG, SYNC_SVG, TRASH_SVG)

from soloblog.routes.admin_settings import EnvStatusRow, S3_ENV_VARS, SettingsNav, _toast_redirect

log = logging.getLogger(__name__)

ar = APIRouter()


def _when(iso: str) -> str:
    """"Sep 24, 2026 14:05" in the site's timezone, from a UTC timestamp."""
    try:
        dt = datetime.fromisoformat(iso[:19])
    except ValueError:
        return iso
    local = tz.to_local(dt)
    return f"{format_date(iso)} {local.strftime('%H:%M')}"


def _button_row(*buttons, status=""):
    """Actions sit right, primary rightmost - same as every SaveBar - and
    with status (an id) their result left of them: a redirect to
    #that-id puts it there (showStatus), not in the page's header."""
    slot = Span(id=status, data_status_slot=True, role="status", cls=f"text-xs {STATUS_BESIDE}") \
        if status else None
    return Div(slot, *buttons, cls=f"{STATUS_ROW} mt-3")


def SyncMenu():
    """Sync images asks which way, for every image at once - a drop menu,
    each choice a line of its own."""
    item = "w-full text-start whitespace-nowrap"
    return Div(
        Button(SYNC_SVG, Span("Sync images", cls="ml-1"), Span(CHEVRON_DOWN_SVG, cls="opacity-60 [&>svg]:h-3 [&>svg]:w-3"),
               type="button", popovertarget="sync-menu", cls="btn btn-sm gap-1"),
        Div(Ul(Li(Button("This site to your bucket", type="submit", formaction="/admin/backup/sync?way=up",
                         cls=item)),
               Li(Button("Your bucket to this site", type="submit", formaction="/admin/backup/sync?way=down",
                         data_confirm="Replace this site's images with your bucket's copies? Images only on "
                                      "this site stay.", cls=item)),
               cls="menu menu-sm flex-nowrap w-max"),
            id="sync-menu", popover="auto",
            cls=f"dropdown-content {glass_fill(settings.get_all())} rounded-box z-20 mt-1 p-1 shadow "
                "border-[length:var(--border)] border-base-200"),
    )


# backups listed before the rest fold under "Older backups"
RECENT_SHOWN = 3


def CloudStoragePanel(now=False):
    """The bucket's state, its backups and what's done with them. Unless
    now, a line that fills itself in once the page is up
    (/admin/backup/cloud) - the bucket answers in a second or two, and the
    rest of the page shouldn't wait for it."""
    if storage.enabled() and not now:
        return SettingsPanel(
            "Cloud storage",
            Div(Span(cls="loading loading-spinner loading-xs"),
                Span("Checking your bucket…", cls="text-sm text-base-content/60"),
                hx_get="/admin/backup/cloud", hx_trigger="load", hx_swap="outerHTML",
                role="status", cls="flex items-center gap-2"),
            key="backup-cloud"
        )
    if not storage.enabled():
        return SettingsPanel(
            "Cloud storage",
            P(Span("Off", cls="badge badge-sm badge-ghost mr-2"),
              "Keep your images and backups in your own S3, Cloudflare R2 or Backblaze B2 bucket. Set these "
              "on your host:", cls=f"text-sm text-base-content/70 {FIELD_GAP}"),
            *[EnvStatusRow(name, help_text) for name, help_text in S3_ENV_VARS],
            key="backup-cloud"
        )
    problem = storage.check()
    missing = storage.unsynced()
    status = storage.last_status()
    try:
        backups = storage.list_backups() if not problem else []
    except storage.StorageError as e:
        problem, backups = str(e), []
    def backup_row(i, b, folded=False):
        # a row action, as on every admin list: an icon, its words in the ⋯ menu on a
        # phone - Restore still shows what's in it first, so nothing goes back by accident
        return Div(
            Div(P(_when(b["modified"]),
                  Span("Latest", cls="badge badge-xs badge-ghost ms-2") if i == 0 else None, cls="text-sm"),
                P(backup.size_label(b["size"]) + (" · encrypted" if b["key"].endswith(".enc") else ""),
                  cls="text-xs text-base-content/50")),
            RowActions(Form(Input(type="hidden", name="key", value=b["key"]),
                            # in the box that scrolls, beside the icon: above, its edges clipped it
                            IconAction(RESTORE_SVG, "Restore", tip="tooltip-left" if folded else ""),
                            action="/admin/backup/from-bucket", method="post", cls="contents"),
                       id=f"backup-acts-{i}"),
            cls="flex items-center justify-between py-2 border-b-[length:var(--border)] border-base-300 last:border-0"
        )

    # the newest few, which is what a restore is usually for; the rest folded,
    # in a box that scrolls - every one kept can be restored, none takes the page
    rows = [backup_row(i, b) for i, b in enumerate(backups[:RECENT_SHOWN])]
    older = [backup_row(i, b, folded=True) for i, b in enumerate(backups) if i >= RECENT_SHOWN]
    if older:
        rows.append(Details(Summary(f"Older backups ({len(older)})", cls="text-xs link link-hover w-fit py-2"),
                            # up and down only - a scrolling box scrolls sideways too, unless told
                            Div(*older, data_scroll_hint=True,
                                cls=f"max-h-72 overflow-y-auto overflow-x-hidden pe-1 {SCROLLS}")))
    if status["error"]:
        last = P(f"The last automatic backup failed: {status['error']}", cls="text-sm text-error")
    elif status["at"]:
        last = P(f"Last backup: {_when(status['at'])}.", cls="text-sm text-base-content/60")
    else:
        last = None
    return SettingsPanel(
        "Cloud storage",
        P(Span("On", cls="badge badge-sm badge-success mr-2") if not problem
          else Span("Error", cls="badge badge-sm badge-error mr-2"),
          f"Bucket “{config.S3_BUCKET}”. Your images are kept there"
          + (f", and what you choose below is backed up {_BACKED_UP.get(settings.get('backup_every'), _BACKED_UP['changes'])}."
             if config.S3_AUTO_BACKUP else "."),
          cls="text-sm text-base-content/70 mb-2"),
        P(problem, cls="text-sm text-error mb-2") if problem else None,
        last,

        Form(
            FormField(
                "How often",
                Div(
                    Select(*[Option(label, value=key, selected=key == (settings.get("backup_every") or "changes"))
                             for key, label in BACKUP_EVERY_LABELS],
                           name="backup_every", cls="select select-sm w-56"),
                    Span(id="every-status", role="status", cls="text-xs"),
                    cls="flex items-center gap-3"
                ),
                help="Less often, the backups you keep reach further back - but you can lose more if your server breaks."
            ),
            hx_post="/admin/backup/every", hx_trigger="change", hx_target="#every-status", hx_swap="outerHTML",
            cls="mt-2"
        ),
        Form(
            FormField(
                "Backups to keep",
                Div(
                    Select(*[Option(f"Newest {n}", value=str(n), selected=(n == storage.keep_count()))
                             for n in sorted(set(storage.BACKUP_KEEP_CHOICES) | {storage.keep_count()})],
                           name="backup_keep", cls="select select-sm w-36"),
                    Span(id="save-status", role="status", cls="text-xs"),
                    cls="flex items-center gap-3"
                ),
                help="Older ones are deleted as new ones are made."
            ),
            # a choice saves as it changes, as every setting's does
            hx_post="/admin/backup/keep", hx_trigger="change", hx_target="#save-status", hx_swap="outerHTML",
            cls="mt-2"
        ),
        Form(
            FormField(
                "What the backups include",
                Div(*[_category_checkbox(cat, checked=cat in storage.backup_categories())
                      for cat in storage.BACKUP_CATEGORIES], cls="flex flex-col gap-1"),
                help="Your images are kept in the bucket separately."
            ),
            Span(id="include-status", role="status", cls="text-xs block mt-1"),
            hx_post="/admin/backup/include", hx_trigger="change", hx_target="#include-status", hx_swap="outerHTML",
            cls="mt-2"
        ) if not problem else None,
        FormField("Recent backups", Div(*rows) if rows else
                  P("None yet.", cls="text-sm text-base-content/60"), cls="mt-2") if not problem else None,
        P(("1 image hasn't" if len(missing) == 1 else f"{len(missing)} images haven't")
          + " reached your bucket. Sync this site's images to it.", cls="text-sm text-warning mt-3")
        if missing and not problem else None,
        Form(
            _button_row(
                SyncMenu(),
                Button(UPLOAD_SVG, Span("Back up now", cls="ml-1"), type="submit", cls="btn btn-primary btn-sm",
                       formaction="/admin/backup/now"),
                status="cloud-status",
            ),
            method="post"
        ) if not problem else None,
        Details(Summary("Environment variables", cls="text-xs link link-hover w-fit py-1"),
                Div(*[EnvStatusRow(name, help_text) for name, help_text in S3_ENV_VARS], cls="mt-1"),
                cls="mt-3"),
        key="backup-cloud"
    )


def BackupTab(inspect_result=None, source="", from_bucket=False, locked=None):
    """source: where a backup being restored came from, said above its ticks.
    locked: a locked backup waiting for its passphrase - {"error": ...}."""
    waiting = inspect_result is None and locked is None
    pending = backup.staged_restore() if waiting else None
    if waiting and not pending and backup.staged_locked():
        locked = {}
    restore_section = (
        _RestoreConfirmPanel(inspect_result, source, from_bucket) if inspect_result is not None
        else _RestoreLockedPanel(source, from_bucket, **locked) if locked is not None
        else _RestorePendingPanel(pending) if pending else _RestoreUploadPanel()
    )
    return Div(
        SettingsPanel(
            "Download",
            P("Posts come as markdown files, and the rest as a database file - both open in other apps.",
              cls="text-sm text-base-content/60 mb-3"),
            Form(
                Div(*[_category_checkbox(cat) for cat in backup.CATEGORIES], cls="flex flex-col gap-1"),
                _button_row(Button(DOWNLOAD_SVG, Span("Download", cls="ml-1"), type="submit",
                                   cls="btn btn-primary btn-sm"), status="download-status"),
                action="/admin/backup/download", method="get"
            ),
            key="backup-download"
        ),
        _arriving(SettingsPanel(
            "Restore",
            Div(restore_section, id="restore-section"),
            key="backup-restore"
        ), inspect_result is not None or bool(locked)),
        CloudStoragePanel(),
        ImportPanel(),
        P(A("See what's using the disk", href="/admin/health#disk", cls="link"),
          cls="text-xs text-base-content/60 px-1"),
        cls="flex flex-col gap-3"
    )


# Disk space: what each kind of file is, and where it's looked after
DISK_ABOUT = {
    "posts": ("Your writing, as files", "/admin/posts"),
    "posts_trash": ("Until you empty the trash", "/admin/posts?status=trash"),
    "images": ("Your media library", "/admin/media"),
    "images_trash": ("Until you empty the trash", "/admin/media?tab=trash"),
    "originals": ("So a crop or a turn can be undone", "/admin/media"),
    "sizes": ("Made as pages need them - safe to clear", None),
    "cards": ("Images shown when your posts are shared - safe to clear", None),
    "log": ("The last two weeks of problems - safe to clear", "/admin/health?tab=log"),
    "detail_log": ("Four weeks of everything your site did, to help find a problem - safe to clear",
                   "/admin/health?tab=log"),
    "database": ("Settings, comments, subscribers and the rest", None),
    "pending": ("Deleted a day after it's uploaded", None),
    "keys": ("Keeps your login safe. Made when your site first started - keep it", None),
    "demo": ("Only on the public demo: its marker, and the photos it's rebuilt from", None),
}


def _post_counts() -> str:
    """"Your writing, as files: 24 posts, 3 pages" - trashed ones aren't counted."""
    from soloblog.db import get_db
    from soloblog import posts
    rows = get_db().execute("SELECT * FROM posts").fetchall()
    pages = sum(1 for r in rows if posts.is_page(r))
    counts = [(len(rows) - pages, "post", "posts"), (pages, "page", "pages")]
    parts = [f"{n} {one if n == 1 else many}" for n, one, many in counts if n]
    return "Your writing, as files" + (": " + ", ".join(parts) if parts else "")


def _media_counts() -> str:
    """"Your media library: 36 images, 2 videos" - what's there, by kind."""
    from soloblog import images
    counts = {}
    try:
        for name in os.listdir(config.uploads_dir()):
            if os.path.isfile(os.path.join(config.uploads_dir(), name)):
                kind = images.kind_of(name)
                counts[kind] = counts.get(kind, 0) + 1
    except OSError:
        pass
    words = {"image": ("image", "images"), "video": ("video", "videos"), "audio": ("audio file", "audio files"),
             "document": ("PDF", "PDFs")}
    parts = [f"{counts[k]} {words[k][counts[k] != 1]}" for k in words if counts.get(k)]
    return "Your media library" + (": " + ", ".join(parts) if parts else "")


def DiskPanel():
    """Everything Soloblog keeps on its disk, by kind (backup.disk_usage) -
    so nothing sits there unseen - and what can be cleared."""
    usage = backup.disk_usage()
    actions = {
        "sizes": Form(IconAction(TRASH_SVG, "Clear", danger=True,
                                 confirm="Clear the smaller copies of your images? They're made again as "
                                         "pages need them."),
                      action="/admin/disk/clear-sizes", method="post", cls="contents"),
        "cards": Form(IconAction(TRASH_SVG, "Clear", danger=True,
                                 confirm="Clear the share cards? They're made again when a link is shared."),
                      action="/admin/disk/clear-cards", method="post", cls="contents"),
        "detail_log": Form(IconAction(TRASH_SVG, "Clear", danger=True,
                                      confirm="Clear the detailed log? It starts again from now."),
                           action="/admin/disk/clear-detail-log", method="post", cls="contents"),
        "log": Form(IconAction(TRASH_SVG, "Clear", danger=True,
                               confirm="Clear the problems log? New problems are kept again as they happen."),
                    action="/admin/disk/clear-log", method="post", cls="contents"),
        "pending": Form(IconAction(TRASH_SVG, "Discard", danger=True,
                                   confirm="Discard this uploaded backup? Nothing is restored, and the file on "
                                           "your computer isn't touched."),
                        action="/admin/backup/discard", method="post", cls="contents"),
    }

    def row(key, label, size, about=None, href=None):
        name = A(label, href=href, cls="link link-hover inline-flex items-center pointer-coarse:min-h-11") if href else Span(label)
        act = actions.get(key)
        return Tr(
            Td(Div(name, cls="font-medium"), Div(about, cls="text-xs text-base-content/60") if about else None),
            Td(backup.size_label(size), cls="text-right tabular-nums whitespace-nowrap"),
            Td(RowActions(act, id=f"disk-acts-{key}") if act else None, cls="w-0"),
        )

    about = {**DISK_ABOUT, "images": (_media_counts(), "/admin/media"), "posts": (_post_counts(), "/admin/posts")}
    rows = [row(key, label, size, *about.get(key, (None, None))) for key, label, size in usage["parts"]]
    if usage["other"]:
        rows.append(row("other", "Other files", sum(usage["other"].values()),
                        ", ".join(sorted(usage["other"])) + " - not Soloblog's own"))
    disk = usage["disk"]
    return SettingsPanel(
        "Disk space",
        P("Everything your site keeps on its server.", cls="text-sm text-base-content/60 mb-2"),
        Div(Table(Tbody(*rows),
                  Tfoot(Tr(Td("Total"), Td(backup.size_label(usage["total"]), cls="text-right tabular-nums"),
                           Td())),
                  cls="table table-sm"),
            cls="overflow-x-auto"),
        Div(P(f"{backup.size_label(disk[1])} free of {backup.size_label(disk[0])} on this disk",
              cls="text-xs text-base-content/50") if disk else None,
            # what clearing did, here beside the rows (a redirect to #disk)
            Span(data_status_slot=True, role="status", cls="text-xs ms-auto"),
            cls="flex flex-wrap items-center gap-2 mt-2"),
        key="backup-disk"
    )


def ImportStatus():
    """The import's progress line - polls itself while one is running."""
    from soloblog import importers
    st = importers.status()
    if st["running"]:
        return Div(Span(cls="loading loading-spinner loading-xs"), Span(st["message"], cls="text-sm"),
                   hx_get="/admin/import/status", hx_trigger="every 2s", hx_swap="outerHTML",
                   cls="flex items-center gap-2 mb-2", id="import-progress")
    if st["message"]:
        return Alert(st["message"], "error" if st["error"] else "success")
    return None


def ImportPanel():
    return SettingsPanel(
        "Import from another blog",
        P("Moving from WordPress, Ghost, Medium, Substack or a static site? Upload its export: your posts come "
          "across with their dates, tags and pages, and WordPress comments and Substack subscribers too.",
          cls=f"text-sm text-base-content/60 {FIELD_GAP}"),
        Ul(Li(Strong("WordPress: "), "Tools > Export > All content (.xml)"),
           Li(Strong("Ghost: "), "Settings > Labs > Export your content (.json)"),
           Li(Strong("Medium: "), "Settings > Security and apps > Download your information (.zip)"),
           Li(Strong("Substack: "), "Settings > Exports > Create new export (.zip)"),
           Li(Strong("Jekyll, Hugo, Obsidian, Eleventy…: "), "a .zip of your markdown files, with their images"),
           cls=f"text-xs text-base-content/60 list-disc pl-5 {FIELD_GAP}"),
        Div(ImportStatus(), id="import-status"),
        Form(
            ToggleField("Copy images into the media library", "copy_images", checked=True,
                        help="So they keep working when the old blog is gone.", cls=FIELD_GAP),
            ToggleField("Import as drafts", "as_drafts", checked=False,
                        help="Look each post over before it goes live.", cls=FIELD_GAP),
            FormField("Old blog's URL", Input(name="old_url", type="url", placeholder="https://blog.example.com",
                                                   cls="input input-sm w-full"),
                      help="Helps bring images across from Ghost and some WordPress sites."),
            _button_row(Label(UPLOAD_SVG, Span("Upload", cls="ml-1"),
                              Input(type="file", name="export", accept=".xml,.json,.zip", required=True,
                                    cls="hidden", data_autosubmit=True),
                              cls="btn btn-sm cursor-pointer")),
            hx_post="/admin/import", hx_encoding="multipart/form-data", hx_target="#import-status",
            hx_swap="innerHTML show:none focus-scroll:false"
        ),
        key="backup-import"
    )


def _RestoreUploadPanel():
    # same pattern as Media's own Upload button - a styled label hiding
    # the real file input, submitting itself the moment a file's picked
    # rather than needing a second, separate "Inspect" click.
    return Div(
        P("Upload a backup to see what's in it, then choose what to restore.",
          cls="text-sm text-base-content/60"),
        Form(
            _button_row(Label(UPLOAD_SVG, Span("Upload", cls="ml-1"),
                              Input(type="file", name="backup_zip", accept=".zip,.enc", required=True, cls="hidden",
                                    data_autosubmit=True),
                              cls="btn btn-sm cursor-pointer"), status="restore-status"),
            action="/admin/backup/inspect", method="post", enctype="multipart/form-data"
        ),
    )


def _arriving(panel, now):
    """The next step, brought into view and marked as a search result is
    (data-arrive, index_search.js) - Restore on a bucket backup fills a
    card further up the page."""
    if now:
        panel.attrs["data-arrive"] = "1"
    return panel


def backup_when(key: str) -> str:
    """"19 Nov 2026 16:27", from a backup's name in the bucket - blank if
    it has no date in it."""
    m = re.search(r"soloblog-(\d{8})-(\d{6})", key)
    if not m:
        return ""
    d, t = m.groups()
    return _when(f'{d[:4]}-{d[4:6]}-{d[6:]}T{t[:2]}:{t[2:4]}:{t[4:]}+00:00')


def _backup_source(key: str) -> str:
    """"your backup of 19 Nov 2026 16:27"."""
    when = backup_when(key)
    return f"your backup of {when}" if when else "your backup"


def _RestoreConfirmPanel(result, source="", from_bucket=False):
    present = [cat for cat in backup.CATEGORIES if result[cat]["present"]]
    if not present:
        return Div(
            P("That file doesn't look like a Soloblog backup - nothing recognizable was found inside.",
              cls="text-sm text-error"),
            _button_row(A(RESTORE_SVG, Span("Try another file", cls="ml-1"), href="/admin/settings?tab=backup",
                          cls="btn btn-sm"))
        )

    def note(cat):
        info = result[cat]
        if cat in ("posts", "images"):
            bits = [str(info["count"])] + ([f"{info['trashed']} in the trash"] if info.get("trashed") else [])
        else:
            bits = []
        bits += [backup.counted(table, n) for table, n in info.get("rows", {}).items() if table in backup.COUNTED]
        return ", ".join(bits) if bits else None

    return Div(
        P(f"From {source}.", cls="text-sm font-medium mb-1") if source else None,
        P("Each one you select replaces what you have now with the backup's. Your password and passkeys stay "
          "as they are.",
          cls="text-sm text-base-content/60 mb-3"),
        Form(
            Div(*[_category_checkbox(cat, note=note(cat)) for cat in present],
                # a bucket backup has no images - they're in the bucket, the latest copy of each
                Label(Input(type="checkbox", name="images_from_bucket", value="1", checked=True,
                            cls="checkbox checkbox-sm"),
                      Span("Images (the latest copy of each, from your bucket)"),
                      cls="label cursor-pointer gap-2 justify-start items-start text-sm whitespace-normal")
                if from_bucket else None,
                cls="flex flex-col gap-1"),
            _button_row(
                _DiscardButton(),
                Button(RESTORE_SVG, Span("Restore", cls="ml-1"), type="button", cls="btn btn-primary btn-sm",
                       data_confirm="Restore the selected items? This will overwrite any matching data you have now."),
            ),
            action="/admin/backup/restore-confirm", method="post"
        ),
    )


PASSPHRASE_MAX = 1000


def _RestoreLockedPanel(source="", from_bucket=False, error=""):
    """A backup locked with a passphrase the host's BACKUP_PASSPHRASE
    doesn't open - one made before it changed, or on another site. The
    passphrase typed here opens it for this restore and isn't kept."""
    return Div(
        P(f"From {source}.", cls="text-sm font-medium mb-1") if source else None,
        P("This backup is locked with a passphrase. Type the one it was made with.",
          cls="text-sm text-base-content/60 mb-3"),
        Form(
            FormField("Passphrase", Input(type="password", name="passphrase", required=True, autofocus=True,
                                          autocomplete="off", maxlength=str(PASSPHRASE_MAX),
                                          cls="input input-sm w-full" + (" input-error" if error else ""))),
            P(error, cls="text-xs text-error mt-1", role="alert") if error else None,
            Input(type="hidden", name="source", value=source),
            Input(type="hidden", name="from_bucket", value="1" if from_bucket else ""),
            _button_row(
                # its own form: Enter in the field sends a form's first button
                _DiscardButton(form="discard-locked"),
                Button(RESTORE_SVG, Span("Open", cls="ml-1"), type="submit", cls="btn btn-primary btn-sm"),
            ),
            action="/admin/backup/unlock", method="post"
        ),
        Form(id="discard-locked", action="/admin/backup/discard", method="post"),
    )


def _DiscardButton(form=None):
    # deletes the uploaded copy waiting on the server - it used to just go
    # back, and leave a whole site's backup on the disk
    return Button(X_SVG, Span("Discard", cls="ml-1"), type="submit", formaction="/admin/backup/discard",
                  formmethod="post", formnovalidate=True, form=form, cls="btn btn-sm",
                  data_confirm="Discard this uploaded backup? Nothing is restored, and the file on your "
                               "computer isn't touched.")


def _RestorePendingPanel(pending):
    """An upload that was looked at but never restored or discarded -
    shown, so it can't sit on the server unseen."""
    return Div(
        P(f"A backup you uploaded on {format_date(pending['when'])} ({backup.size_label(pending['size'])}) "
          "hasn't been restored yet.",
          cls="text-sm text-base-content/60"),
        Form(
            _button_row(
                _DiscardButton(),
                Button(RESTORE_SVG, Span("Continue", cls="ml-1"), type="submit", cls="btn btn-primary btn-sm"),
            ),
            action="/admin/backup/pending", method="post"
        ),
    )


@ar.get("/admin/backup/download")
def download_backup(session, request):
    include = {cat for cat in backup.CATEGORIES if request.query_params.get(cat)}
    if not include:
        return _toast_redirect("/admin/settings?tab=backup#download-status", "Select at least one thing to back up", "error")
    data = backup.build_backup_zip(include)
    settings.set_many({"last_backup_download": utcnow().isoformat()})
    return Response(
        content=data, media_type="application/zip",
        headers={"Content-Disposition": backup.download_header(backup.backup_filename())}
    )


@ar.post("/admin/import")
async def start_import(session, request):
    from soloblog import importers
    form = await request.form()
    file = form.get("export")
    if not file or not getattr(file, "filename", ""):
        return Alert("Choose an export file first.", "error")
    data = await file.read(importers.MAX_IMPORT_BYTES + 1)
    if len(data) > importers.MAX_IMPORT_BYTES:
        return Alert("That file is over 50 MB - export without media, or in parts.", "error")
    try:
        source, items = importers.read(file.filename, data, str(form.get("old_url") or ""))
    except importers.ImportError_ as e:
        return Alert(str(e), "error")
    if not items:
        return Alert(f"That {source} export has no posts in it.", "info")
    if not importers.start(items, source, as_drafts=form.get("as_drafts") == "1",
                           copy_images=form.get("copy_images") == "1"):
        return Alert("An import is already running - wait for it to finish.", "info")
    return ImportStatus()


@ar.get("/admin/import/status")
def import_status(session):
    return ImportStatus() or ""


@ar.post("/admin/backup/inspect")
async def inspect_backup(session, request):
    """Step 1 of restoring: stage the upload and look inside it, so
    the confirm step (below) can offer checkboxes only for what this
    specific file actually has - a fixed restore list would either
    lie about categories the file doesn't contain or silently do
    nothing for them."""
    form = await request.form()
    file = form.get("backup_zip")
    if not file:
        return RedirectResponse("/admin/settings?tab=backup", status_code=303)
    data = await file.read()
    return _open_backup(data, f"the file “{getattr(file, 'filename', '') or 'you uploaded'}”")


def _backup_page(**tab):
    return Layout(
        PageHeader("Settings: Backup and import"),
        SettingsNav("backup"),
        BackupTab(**tab),
        settings=settings.get_all(), logged_in=True, pinned_tree=posts.list_pinned_tree(), admin_page=True
    )


def _open_backup(data, source, from_bucket=False, passphrase=""):
    """Stage a backup and show what's in it - or, when it's locked and
    the passphrase (the host's, unless one was typed) doesn't open it,
    keep it locked and ask for the one it was made with."""
    backup.discard_staged()
    os.makedirs(config.data_dir(), exist_ok=True)
    if storage.is_locked(data):
        try:
            data = storage.open_backup(data, passphrase)
        except storage.StorageError:
            with open(backup.STAGED_LOCKED_PATH, "wb") as f:
                f.write(data)
            return _backup_page(source=source, from_bucket=from_bucket,
                                locked={"error": "Wrong passphrase, try again" if passphrase else ""})
    result = backup.inspect_zip(data)
    # kept for the next step only if there's something in it to restore
    if any(info["present"] for info in result.values()):
        with open(backup.STAGED_RESTORE_PATH, "wb") as f:
            f.write(data)
        backup.typed_passphrase(passphrase)
    return _backup_page(inspect_result=result, source=source, from_bucket=from_bucket)


@ar.post("/admin/backup/unlock")
def unlock_backup(session, passphrase: str = "", source: str = "", from_bucket: str = ""):
    data = backup.staged_locked()
    if data is None:
        return _toast_redirect("/admin/settings?tab=backup#restore-status", "That upload expired, try again", "error")
    source = source[:200]
    if not passphrase or len(passphrase) > PASSPHRASE_MAX:
        return _backup_page(source=source, from_bucket=bool(from_bucket),
                            locked={"error": "Wrong passphrase, try again" if passphrase else "Type the passphrase"})
    return _open_backup(data, source, bool(from_bucket), passphrase)


def _bucket_problem(what, e):
    """What went wrong, in words - the bucket's own reply (a status code,
    its XML) goes to the problems log (Site health > Log), not the page."""
    log.warning("%s: %s", what, e)
    if "BACKUP_PASSPHRASE" in str(e) or "encrypted" in str(e):
        return f"{what} - {e}"
    return f"{what} - the storage bucket didn't answer. Site health's Log has the details"


@ar.post("/admin/backup/now")
def backup_to_bucket(session):
    try:
        storage.backup_now()
    except storage.StorageError as e:
        return _toast_redirect("/admin/settings?tab=backup#cloud-status", _bucket_problem("The backup didn't reach your bucket", e),
                               "error")
    return _toast_redirect("/admin/settings?tab=backup#cloud-status", "Backed up")


_BACKED_UP = {"changes": "as you change it", "day": "once a day", "week": "once a week"}
BACKUP_EVERY_LABELS = [("changes", "A minute after changes"), ("day", "Once a day, if anything changed"),
                       ("week", "Once a week, if anything changed")]


@ar.post("/admin/backup/every")
def save_backup_every(session, backup_every: str = ""):
    if backup_every not in storage.BACKUP_EVERY:
        return Span("Choose one of these", id="every-status", role="status", cls="text-xs text-error")
    settings.set_many({"backup_every": backup_every})
    storage.reschedule()
    return Span("Saved", id="every-status", role="status", cls="text-xs text-success")


@ar.post("/admin/backup/keep")
def save_backup_keep(session, request, backup_keep: int = 30):
    settings.set_many({"backup_keep": str(max(1, min(backup_keep, 1000)))})
    return SaveStatus("Saved - applies from the next backup")


@ar.post("/admin/backup/include")
async def save_backup_include(session, request):
    form = await request.form()
    chosen = [cat for cat in storage.BACKUP_CATEGORIES if form.get(cat)]
    if not chosen:
        return Span("Choose at least one", id="include-status", role="status", cls="text-xs text-error")
    # all ticked is kept as blank, so a category added later is in by default
    settings.set_many({"backup_include": "" if len(chosen) == len(storage.BACKUP_CATEGORIES) else ",".join(chosen)})
    return Span("Saved - applies from the next backup", id="include-status", role="status", cls="text-xs text-success")


def _images(n: int) -> str:
    return f"{n} image{'' if n == 1 else 's'}"


def _synced(copied: int, same: int, direction: str) -> str:
    """What Sync images did, and what it found already the same."""
    if copied:
        return f"Copied {_images(copied)} {direction} your bucket" + (
            f" - {same} {'was' if same == 1 else 'were'} the same already" if same else "")
    if same:
        return f"Nothing to copy - {_images(same)} already the same on both sides"
    return "No images to copy"


@ar.get("/admin/backup/cloud")
def cloud_storage_part(session):
    """What fills the Cloud storage card in, once the page is up."""
    return Div(*CloudStoragePanel(now=True).children[1].children)


@ar.post("/admin/backup/sync")
def sync_bucket_images(session, way: str = "up"):
    way = way if way in ("up", "down") else "up"
    try:
        storage.reseal_images()
        counts = storage.sync_uploads(way)
    except storage.StorageError as e:
        return _toast_redirect("/admin/settings?tab=backup#cloud-status", _bucket_problem("The images didn't sync", e),
                               "error")
    copied = counts["uploaded"] if way == "up" else counts["downloaded"]
    message = _synced(copied, counts["same"], "to" if way == "up" else "from")
    return _toast_redirect("/admin/settings?tab=backup#cloud-status", message)


@ar.post("/admin/backup/from-bucket")
def restore_from_bucket(session, key: str = ""):
    """A bucket backup goes through the same look-first restore as an
    uploaded file: staged, inspected, then the usual confirm step."""
    if not key.startswith(storage.BACKUP_PREFIX) or ".." in key:
        return RedirectResponse("/admin/settings?tab=backup", status_code=303)
    try:
        data = storage.get_backup(key, raw=True)
    except storage.StorageError as e:
        return _toast_redirect("/admin/settings?tab=backup#cloud-status", _bucket_problem("Couldn't restore that backup", e),
                               "error")
    if data is None:
        return _toast_redirect("/admin/settings?tab=backup#cloud-status", "Couldn't fetch that backup", "error")
    return _open_backup(data, _backup_source(key), from_bucket=True)


@ar.post("/admin/backup/pending")
def restore_pending(session):
    """Back to choosing what to restore from the upload that's waiting."""
    if not backup.staged_restore():
        return _toast_redirect("/admin/settings?tab=backup#restore-status", "That upload expired, try again", "error")
    with open(backup.STAGED_RESTORE_PATH, "rb") as f:
        result = backup.inspect_zip(f.read())
    return _backup_page(inspect_result=result, source="the backup you uploaded")


@ar.post("/admin/disk/clear-detail-log")
def disk_clear_detail_log(session):
    from soloblog import health
    health.clear_detail()
    return _toast_redirect("/admin/health#disk", "Cleared")


@ar.post("/admin/disk/clear-log")
def disk_clear_log(session, back: str = ""):
    from soloblog import health
    health.clear_log()
    # back to the log when it was cleared from there
    return _toast_redirect("/admin/health?tab=log#log-status" if back == "log" else "/admin/health#disk", "Cleared")


@ar.post("/admin/disk/clear-sizes")
def disk_clear_sizes(session):
    images.clear_sizes()
    return _toast_redirect("/admin/health#disk", "Cleared")


@ar.post("/admin/disk/clear-cards")
def disk_clear_cards(session):
    from soloblog import cards
    shutil.rmtree(cards.cards_dir(), ignore_errors=True)
    return _toast_redirect("/admin/health#disk", "Cleared")


@ar.post("/admin/backup/discard")
def restore_discard(session):
    backup.discard_staged()
    return _toast_redirect("/admin/settings?tab=backup#restore-status", "Discarded")


@ar.post("/admin/backup/restore-confirm")
async def restore_confirm(session, request):
    form = await request.form()
    include = {cat for cat in backup.CATEGORIES if form.get(cat)}
    if not backup.staged_restore():
        return _toast_redirect("/admin/settings?tab=backup#restore-status", "That upload expired, try again", "error")
    with open(backup.STAGED_RESTORE_PATH, "rb") as f:
        data = f.read()
    older = backup.typed_passphrase()
    backup.discard_staged()
    counts = backup.import_backup_zip(data, include=include)
    problem = ""
    if form.get("images_from_bucket") and storage.enabled():
        # a bucket backup's images: the bucket's latest copy of each, replacing these
        try:
            counts["images"] = storage.sync_uploads("down", older)["downloaded"]
        except storage.StorageError as e:
            problem = ". " + _bucket_problem("The images didn't come back from your bucket", e)
    elif storage.enabled() and (counts.get("images") or counts.get("trashed_images")):
        # restored images belong in the bucket too - in the background,
        # a large backup shouldn't hold this response up
        import threading
        threading.Thread(target=lambda: storage._mirror(storage.sync_uploads, "up"), daemon=True).start()
    # restored settings may say the images are locked another way
    storage._mirror(storage.reseal_images)
    # only the categories that actually had something restored - an
    # older backup with no trashed posts/images shouldn't read as
    # "0 trashed posts, 0 images" clutter
    labels = {"posts": ("post", "posts"), "trashed_posts": ("trashed post", "trashed posts"),
              "images": ("image", "images"), "trashed_images": ("trashed image", "trashed images"),
              "settings": ("setting", "settings"), "comments": ("comment", "comments"),
              "contact_messages": ("message", "messages"), "members": ("member", "members"),
              "subscribers": ("subscriber", "subscribers"), "ap_followers": ("follower", "followers")}
    parts = [f"{counts[key]} {one if counts[key] == 1 else many}" for key, (one, many) in labels.items()
             if counts.get(key)]
    message = (f"Restored {', '.join(parts)}" if parts else "Nothing restored") + problem
    return _toast_redirect("/admin/settings?tab=backup#restore-status", message, "error" if problem else "success")


def _category_checkbox(cat, checked=True, note=None):
    return Label(
        Input(type="checkbox", name=cat, value="1", checked=checked, cls="checkbox checkbox-sm"),
        Span(backup.CATEGORY_LABELS[cat] + (f" ({note})" if note else "")),
        # daisyUI's label doesn't wrap - a long one ran off a phone's edge
        cls="label cursor-pointer gap-2 justify-start items-start text-sm whitespace-normal"
    )
