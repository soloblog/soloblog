import logging
import os
from urllib.parse import quote

from fasthtml.common import *

from soloblog import config
from soloblog import images
from soloblog import settings
from soloblog import posts
from soloblog import stock
from soloblog.actions import on, EL
from soloblog.ui import DRAWER_W, DRAWER_BACKDROP, DOCKED_FILL, SCROLLS, Tabs, TABS_CLS
from soloblog.ui import rows_per_page
from soloblog.ui import IconAction, SaveBar, MediaPickerDialog, MediaPickerButton
from soloblog.ui import (Layout, EmptyState, ListHeader, BulkButton, SearchField, FilterSelect, list_summary, RowCheck, TICK_ROW, TICK_ROW_CLS, FIELD_GAP, FormField, SettingsPanel, TRASH_SVG, RESTORE_SVG, UPLOAD_SVG,
                 COPY_SVG, EDIT_SVG, X_SVG, Pagination, PageHeader, ListToolbar, glass_fill,
                 StockResults, PickerGrid, ROTATE_LEFT_SVG, ROTATE_RIGHT_SVG, CROP_SVG)
from soloblog.guards import is_local_path, status_redirect, undo_url

log = logging.getLogger(__name__)

ar = APIRouter()

def _toast_redirect(message: str, kind: str = "success", return_to: str = "/admin/media", undo: str = ""):
    # return_to - lands back on whichever tab/page the admin acted from,
    # never another site (is_local_path)
    target = return_to if is_local_path(return_to) else "/admin/media"
    return status_redirect(target, message, kind, undo)


# Heroicons outline, for files with no picture of their own
_KIND_ICONS = {
    "document": "M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 "
                "3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 "
                "1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z",
    "audio": "m9 9 10.5-3m0 6.553v3.75a2.25 2.25 0 0 1-1.632 2.163l-1.32.377a1.803 1.803 0 1 1-.99-3.467l2.31-.66a2.25 "
             "2.25 0 0 0 1.632-2.163Zm0 0V2.25L9 5.25v10.303m0 0v3.75a2.25 2.25 0 0 1-1.632 2.163l-1.32.377a1.803 "
             "1.803 0 0 1-.99-3.467l2.31-.66A2.25 2.25 0 0 0 9 15.553Z",
}
KIND_NAMES = {"image": "Image", "audio": "Audio", "video": "Video", "document": "PDF"}


def file_type(filename: str) -> str:
    """What a person calls the file: "MP3", "PDF", "JPG"."""
    return filename.rsplit(".", 1)[-1].upper() if "." in filename else KIND_NAMES.get(images.kind_of(filename), "File")


def MediaPreview(item, cls, player=False, **attrs):
    """What a card shows: the image, a video's first frame, or an icon
    for audio and PDFs. attrs (the details drawer's trigger) go on it
    whatever the kind, so clicking any preview opens its details.
    player - the details drawer itself: audio and video play there."""
    kind = images.kind_of(item["filename"])
    if kind in ("audio", "video") and player:
        if kind == "audio":
            return Div(Audio(src=item["url"], preload="metadata", controls=True, cls="w-full"),
                       cls=f"{cls} flex items-center p-3 bg-base-200")
        return Video(src=item["url"], preload="metadata", controls=True, cls=f"{cls} bg-base-300")
    if kind == "video":
        return Video(src=item["url"], preload="metadata", muted=True, cls=f"{cls} bg-base-300",
                     aria_label=item["filename"], **attrs)
    if kind in _KIND_ICONS:
        icon = NotStr(f'<svg xmlns="http://www.w3.org/2000/svg" class="h-10 w-10 opacity-60" fill="none" '
                      f'viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5" aria-hidden="true">'
                      f'<path stroke-linecap="round" stroke-linejoin="round" d="{_KIND_ICONS[kind]}" /></svg>')
        return Div(icon, Span(file_type(item["filename"]), cls="text-xs font-medium"),
                   cls=f"{cls} flex flex-col items-center justify-center gap-1 bg-base-200", **attrs)
    # ?v= its time, so an edit (rotate, crop) shows here straight away
    src = images.thumb(item["url"])
    # the card names the file under it - the preview itself says nothing more
    return Img(src=f"{src}{'&' if '?' in src else '?'}v={item['mtime']}", loading="lazy", cls=cls,
               **{"alt": "", **attrs})


def MediaCard(item, mode="gallery", return_to="/admin/media"):
    """One file in Media, the same card on every tab. mode: "gallery"
    (in use - Trash warns that posts lose it), "unused" (Trash asks, and
    says it can be restored) or "trash" (Restore, and Delete forever,
    which asks). Its picture, its name and Edit all open its details
    (MediaDetailsForm), where "Used in" is."""
    copy_btn = IconAction(COPY_SVG, "Copy URL", menu_label=False, **on("click", "copyLink", item["url"], EL))
    if mode == "trash":
        title = Span(item["filename"], cls="font-medium text-sm truncate block")
        actions = Div(
            copy_btn,
            Form(Input(type="hidden", name="filename", value=item["filename"]),
                 Input(type="hidden", name="return_to", value=return_to),
                 IconAction(RESTORE_SVG, "Restore", menu_label=False),
                 action="/admin/media/restore", method="post", cls="contents"),
            Form(Input(type="hidden", name="filename", value=item["filename"]),
                 Input(type="hidden", name="return_to", value=return_to),
                 IconAction(TRASH_SVG, "Delete forever", danger=True, menu_label=False,
                            confirm="Permanently delete this file? This can't be undone."),
                 action="/admin/media/delete-forever", method="post", cls="contents"),
            cls="join"
        )
        image = MediaPreview(item, "aspect-[4/3] w-full object-cover")
    else:
        delete_btn = IconAction(
            TRASH_SVG, "Trash", danger=True, menu_label=False,
            confirm="Move this file to trash? You can restore it from Trash." if mode == "unused" else
            "Move this file to trash? Posts using it will show it missing until you restore it.")
        # one shared trigger for the Details drawer - thumbnail, title,
        # and the Edit button all fire the identical htmx call, so all
        # three open the same fragment rather than three slightly
        # different ones to keep in sync.
        details_attrs = dict(hx_get=f"/admin/media/details/{item['filename']}",
                              hx_target="#media-details-content", hx_swap="innerHTML",
                              **on("click", "toggleMediaDetails", True))
        title = Span(item["filename"], cls="link link-hover font-medium text-sm truncate block cursor-pointer",
                     **details_attrs)
        edit_btn = IconAction(EDIT_SVG, "Edit", menu_label=False, type="button", **details_attrs)
        actions = Div(
            copy_btn,
            edit_btn,
            Form(
                Input(type="hidden", name="filename", value=item["filename"]),
                Input(type="hidden", name="return_to", value=return_to),
                delete_btn,
                action="/admin/media/trash", method="post",
                cls="contents"
            ),
            cls="join"
        )
        # cursor-pointer + the hover ring MediaPickerDialog's own
        # clickable rows already use is what tells you the thumbnail
        # itself is clickable too, since a plain image gives no such
        # hint otherwise.
        image = MediaPreview(item, "aspect-[4/3] w-full object-cover cursor-pointer hover:ring-2 hover:ring-primary",
                             **details_attrs)
    dims = item.get("dimensions")
    dims_text = f"{dims[0]}×{dims[1]} px" if dims else None
    meta_text = " · ".join(b for b in (dims_text, f"{item['size_kb']} KB") if b)
    meta_span = Div(Span(meta_text, cls="text-xs text-base-content/50"),
                    # the same pills as the lists of posts and comments
                    Span("Unused", cls="badge badge-xs badge-warning badge-soft whitespace-nowrap")
                    if mode == "unused" else None, cls="flex flex-wrap items-center gap-2")
    bottom = Div(title, meta_span, Div(actions, cls="flex justify-end mt-2"), cls="min-w-0")
    return Div(
        Figure(image, RowCheck("media-bulk", "filenames", item["filename"], item["filename"],
                               "absolute top-2 left-2 bg-base-100"), cls="relative"),
        Div(bottom, cls="card-body p-3"),
        cls=f"card card-border bg-base-100 {TICK_ROW_CLS}", **TICK_ROW
    )


def ImageEditPanel(item, status="", failed=False):
    """Rotate, crop to a shape, or go back to the original - each changes
    the file itself, so every post using it follows."""
    name = item["filename"]
    swap = dict(hx_target="#media-details-content", hx_swap="innerHTML")
    return SettingsPanel(
        "Rotate & crop",
        Div(
            Form(Input(type="hidden", name="action", value="left"),
                 Button(ROTATE_LEFT_SVG, Span("Rotate left", cls="ml-1"), type="submit", cls="btn btn-sm join-item"),
                 hx_post=f"/admin/media/edit/{name}", cls="contents", **swap),
            Form(Input(type="hidden", name="action", value="right"),
                 Button(ROTATE_RIGHT_SVG, Span("Rotate right", cls="ml-1"), type="submit", cls="btn btn-sm join-item"),
                 hx_post=f"/admin/media/edit/{name}", cls="contents", **swap),
            cls="join mb-3"
        ),
        Form(
            Input(type="hidden", name="action", value="crop"),
            Div(
                FormField("Crop to", Select(*[Option(label, value=k) for k, (label, _) in images.RATIOS.items()],
                                            name="ratio", cls="select select-sm w-full")),
                FormField("Keep", Select(*[Option(k.title(), value=k) for k in images.KEEP],
                                         name="keep", cls="select select-sm w-full")),
                cls="grid grid-cols-2 gap-2"
            ),
            Div(Span(status, cls=f"text-xs {'text-error' if failed else 'text-success'}"),
                Button(CROP_SVG, Span("Crop", cls="ml-1"), type="submit", cls="btn btn-sm ml-auto"),
                cls="flex items-center gap-2 mt-2"),
            hx_post=f"/admin/media/edit/{name}", **swap
        ),
        Div(
            P("Edited - posts using it show the change", cls="text-xs text-base-content/60"),
            Form(Input(type="hidden", name="action", value="restore"),
                 Button(RESTORE_SVG, Span("Restore original", cls="ml-1"), type="submit", cls="btn btn-sm whitespace-nowrap"),
                 hx_post=f"/admin/media/edit/{name}", **swap),
            cls="flex items-center justify-between gap-2 mt-3"
        ) if images.has_original(name) else None,
        key="media-edit"
    )


def MediaDetailsForm(item, used_in, status="", edit_status="", edit_failed=False):
    """The details drawer for one file: what it is, where it's used and
    its name - and for an image, rotate and crop, and the alt text,
    caption and credit posts show with it (images.meta_for_url). The
    heading comes along out of band. Opening and saving both return it,
    so a save refreshes it in place.

    Its panels' keys start "media-": a panel's open or closed state is
    remembered by key, shared with the editor's panels. status: "Saved",
    left of the Save button."""
    meta = images.get_meta(item["filename"])
    dims = item.get("dimensions")
    kind = images.kind_of(item["filename"])
    facts = [file_type(item["filename"])]
    if kind == "image" and dims:
        facts.append(f"{dims[0]}×{dims[1]} px")
    facts.append(f"{item['size_kb']} KB")
    used_in_text = ", ".join(f"“{u['title']}”" for u in used_in) if used_in else "Nothing yet"
    # the drawer's heading names what's open (MediaDetailsDrawer)
    title = H2(f"{KIND_NAMES.get(kind, 'File')} details", id="media-details-title", cls="font-semibold",
               hx_swap_oob="true")
    # the whole image, not cropped to fill: a wide logo showed a few letters
    preview = MediaPreview(item, "w-full h-40 object-contain bg-base-200 rounded-box", player=True)
    if kind == "document":
        preview = A(preview, href=item["url"], target="_blank", rel="noopener",
                    aria_label=f"Open {item['filename']}", cls="block hover:opacity-80")
    # what a post shows of the file: an image's alt text, caption and
    # credit - a player or a PDF shows none of them
    description = Form(
        SettingsPanel(
            "Description",
            FormField("Alt text", Input(name="alt_text", value=meta["alt_text"], cls="input input-sm w-full"),
                      help="Describes the image for people who can't see it. Empty if it's only decoration.",
                      cls=FIELD_GAP),
            FormField("Caption", Input(name="caption", value=meta["caption"], cls="input input-sm w-full"),
                      help="Shown under the image in posts.", cls=FIELD_GAP),
            FormField("Credit", Input(name="credit_name", value=meta["credit_name"], cls="input input-sm w-full"),
                      help="Who made the image. Shown with it as “Image by …”.", cls=FIELD_GAP),
            FormField("Credit link", Input(name="credit_url", type="url", value=meta["credit_url"],
                                           placeholder="https://", cls="input input-sm w-full"),
                      help="Their website. The name in the credit links to it.", cls=FIELD_GAP),
            FormField("Dark mode version",
                      Div(Input(name="dark_version", id="media-dark-version",
                                value=f"/uploads/{meta['dark_version']}" if meta["dark_version"] else "",
                                placeholder="/uploads/…", data_picker_skip=item["filename"],
                                cls="input input-sm join-item flex-1 min-w-0"),
                          MediaPickerButton("media-dark-version"), cls="join w-full"),
                      help="Another image, shown in place of this one while your site is dark.", cls=FIELD_GAP),
            FormField("Phone version",
                      Div(Input(name="phone_version", id="media-phone-version",
                                value=f"/uploads/{meta['phone_version']}" if meta["phone_version"] else "",
                                placeholder="/uploads/…", data_picker_skip=item["filename"],
                                cls="input input-sm join-item flex-1 min-w-0"),
                          MediaPickerButton("media-phone-version"), cls="join w-full"),
                      help="Another image, shown in place of this one on a phone."),
            key="media-fields"
        ),
        # Discard and Save only while something's changed, as in Settings
        # (data-declare-fields: syncSettingsDirty)
        Div(SaveBar(status=status), cls="mt-3"),
        hx_post=f"/admin/media/details/{item['filename']}", data_declare_fields=True,
        hx_target="#media-details-content", hx_swap="innerHTML"
    ) if kind == "image" else None
    return Div(
        Div(preview,
            A("Open the PDF", href=item["url"], target="_blank", rel="noopener", cls="link text-sm mt-1 inline-flex items-center pointer-coarse:min-h-11")
            if kind == "document" else None, cls="mb-3"),
        SettingsPanel(
            "Info",
            P(" · ".join(facts), cls="text-xs text-base-content/60 mb-1"),
            P(f"Used in: {used_in_text}", cls="text-xs text-base-content/60 mb-3"),
            Form(
                FormField("File name", Div(
                    Input(name="name", value=item["filename"].rsplit(".", 1)[0], required=True,
                          pattern="[A-Za-z0-9 _-]+", title="Letters, numbers, spaces and dashes",
                          cls="input input-sm join-item flex-1 min-w-0 font-mono"),
                    Button(EDIT_SVG, Span("Rename", cls="ml-1"), type="submit", cls="btn btn-sm join-item"),
                    cls="join w-full"),
                    help="Posts that use it keep working."),
                hx_post=f"/admin/media/rename/{item['filename']}", hx_target="#media-details-content",
                hx_swap="innerHTML"
            ),
            key="media-info"
        ),
        ImageEditPanel(item, edit_status, edit_failed) if kind == "image" and not item["filename"].lower().endswith((".gif", ".svg")) else None,
        description,
        cls="flex flex-col gap-3"
    ), title


def MediaDetailsDrawer():
    """The shared drawer shell - one per page, its #media-details-content
    filled in by htmx per-card (see MediaCard's title/thumbnail/Edit
    button, all three the same trigger). Same slide-over pattern as
    the post editor's settings panel
    (routes/editor.py), independent copy rather than a shared component:
    different trigger id (toggleMediaDetails vs togglePostSettings),
    different content shape, and pulling it into a shared helper would
    mean threading both through one generic API for two call sites."""
    drawer_fill = glass_fill(settings)
    return (
        Div(id="media-details-backdrop", cls=DRAWER_BACKDROP,
            **on("click", "toggleMediaDetails", False)),
        Div(Div(
            Div(
                H2("Details", id="media-details-title", cls="font-semibold"),
                Button(X_SVG, type="button", cls="btn btn-sm btn-ghost btn-square",
                       aria_label="Close details", **on("click", "toggleMediaDetails", False)),
                cls="flex items-center justify-between mb-3"
            ),
            Div(P("Pick a file to see its details.", cls="text-sm text-base-content/50"),
                id="media-details-content"),
            # the fade is a mask: on the panel itself it would fade its fill too
            data_scroll_hint=True, cls=f"h-full overflow-y-auto overscroll-contain p-3 {SCROLLS}"),
            id="media-details-panel", aria_label="File details", inert=True, data_own_scroll=True,
            cls=f"fixed inset-y-0 right-0 z-40 {DRAWER_W} translate-x-full {drawer_fill} "
                f"shadow-xl transition-transform duration-200 {DOCKED_FILL}"
        )
    )


MEDIA_TABS = [("all", "All"), ("used", "In use"), ("unused", "Unused"), ("trash", "Trash")]
MEDIA_PER_PAGE = 20
# two to a row on a phone, like a phone's own photos - one filled the screen
MEDIA_GRID = "grid grid-cols-2 sm:grid-cols-3 gap-3 sm:gap-4"
# "Largest"/"smallest" instead of Posts' "Most viewed" - an image has
# no view count of its own, but file size is the equivalent "which one
# is worth a second look" signal here
MEDIA_SORT_OPTIONS = [("newest", "Newest"), ("oldest", "Oldest"),
                      ("largest", "Largest file"), ("smallest", "Smallest file")]


MEDIA_KINDS = ("image", "audio", "video", "document", "noalt")


def _filtered_media(q, kind, usage):
    """(every upload, the unused ones, the trash) the search and the kind
    filter leave - for the page, and for its bulk bar's Select all, so
    both mean the same files."""
    all_items = images.list_uploads()
    if kind == "noalt":
        has_alt = images.alt_texts()
        all_items = [i for i in all_items if i["kind"] == "image" and i["filename"] not in has_alt]
    elif kind:
        all_items = [i for i in all_items if i["kind"] == kind]
    if q:
        text = images.search_text(all_items, usage)
        all_items = [i for i in all_items if images.matches(text[i["filename"]], q)]
    orphans = [i for i in all_items if i["filename"] not in usage]
    trash_items = images.list_trash()
    if q:
        trash_items = [t for t in trash_items if images.matches(t["filename"].lower(), q)]
    return all_items, orphans, trash_items


def _media_tab_files(tab, q, kind, post):
    """Every filename on a tab of Media, its filters as on the page."""
    usage = images.usage_map()
    q, kind = q.strip()[:100], kind if kind in MEDIA_KINDS else ""
    all_items, orphans, trash_items = _filtered_media(q, kind, usage)
    if tab == "trash":
        return [t["filename"] for t in trash_items]
    if tab == "unused":
        return [o["filename"] for o in orphans]
    if tab == "used":
        all_items = [i for i in all_items if i["filename"] in usage]
    if post:
        all_items = [i for i in all_items if any(u["slug"] == post for u in usage.get(i["filename"], []))]
    return [i["filename"] for i in all_items]


@ar.get("/admin/media")
def media_library(session, tab: str = "all", sort: str = "newest", post: str = "", page: int = 1,
                  q: str = "", kind: str = ""):
    if tab not in dict(MEDIA_TABS):
        tab = "all"
    if sort not in dict(MEDIA_SORT_OPTIONS):
        sort = "newest"
    page = max(1, page)

    # one scan for both the orphan check and each gallery card's own
    # "Used in" line, instead of calling list_orphans() (which would
    # scan again internally) and separately re-deriving usage here
    usage = images.usage_map()
    q = q.strip()[:100]
    kind = kind if kind in MEDIA_KINDS else ""
    all_items, orphans, trash_items = _filtered_media(q, kind, usage)
    orphan_filenames = {o["filename"] for o in orphans}
    # what each tab's links keep: the search and the kind filter
    keep = f"&q={quote(q)}&kind={kind}"

    pagination = None
    sort_picker = None
    bulk_actions = None
    per = rows_per_page(MEDIA_PER_PAGE)
    if tab in ("all", "used"):
        # ?post= (a link to one post's images) still narrows the gallery;
        # there's no picker for it - the search box finds images by post
        post_title = next((u["title"] for entries in usage.values() for u in entries if u["slug"] == post),
                          "") if post else ""
        # everything, in use or not - an Unused pill on the ones no post uses
        gallery_items = list(all_items) if tab == "all" else [i for i in all_items if i["filename"] in usage]
        if post:
            gallery_items = [i for i in gallery_items
                              if any(u["slug"] == post for u in usage.get(i["filename"], []))]
        if sort == "oldest":
            gallery_items = sorted(gallery_items, key=lambda i: i["modified"])
        elif sort == "largest":
            gallery_items = sorted(gallery_items, key=lambda i: i["size_kb"], reverse=True)
        elif sort == "smallest":
            gallery_items = sorted(gallery_items, key=lambda i: i["size_kb"])
        # "newest" needs no re-sort - list_uploads() already returns that order

        total_pages = max(1, -(-len(gallery_items) // per))
        page_items = shown = gallery_items[(page - 1) * per: page * per]
        base_path = f"/admin/media?tab={tab}&sort={sort}&post={quote(post)}{keep}"
        return_to = f"{base_path}&page={page}"
        if page_items:
            body = Div(*[MediaCard(i, mode="unused" if i["filename"] in orphan_filenames else "gallery",
                                   return_to=return_to)
                         for i in page_items], cls=MEDIA_GRID)
        elif tab == "used" and not (q or kind):
            body = EmptyState("No posts use your media yet.", "🖼️")
        elif all_items or q or kind:
            # library isn't empty, this filter just matched nothing
            body = EmptyState(f"Nothing matches “{q}”." if q else "Nothing matches this filter.", "🔍")
        else:
            body = EmptyState("Nothing uploaded yet. Use Upload to add photos, audio, video or PDFs.", "🖼️")
        pagination = Pagination(page, total_pages, base_path, labels=("« Prev", "Next »"), per_page=per,
                                total=len(gallery_items))

        total_count = len(gallery_items)
        sort_picker = FilterSelect("Sort", "sort", MEDIA_SORT_OPTIONS, sort,
                                   f"/admin/media?tab={tab}&post={quote(post)}{keep}&sort=")
    elif tab == "unused":
        total_pages = max(1, -(-len(orphans) // per))
        page_orphans = shown = orphans[(page - 1) * per: page * per]
        total_count = len(orphans)
        pagination = Pagination(page, total_pages, f"/admin/media?tab=unused{keep}", labels=("« Prev", "Next »"),
                                per_page=per, total=total_count)
        return_to = f"/admin/media?tab=unused{keep}&page={page}"
        body = (Div(*[MediaCard(o, mode="unused", return_to=return_to) for o in page_orphans],
                    cls=MEDIA_GRID)
                if page_orphans else EmptyState("Nothing unused.", "🧹"))
    else:
        total_pages = max(1, -(-len(trash_items) // per))
        page_trash = shown = trash_items[(page - 1) * per: page * per]
        total_count = len(trash_items)
        pagination = Pagination(page, total_pages, f"/admin/media?tab=trash{keep}", labels=("« Prev", "Next »"),
                                per_page=per, total=total_count)
        return_to = f"/admin/media?tab=trash{keep}&page={page}"
        bulk_actions = Form(
            Input(type="hidden", name="return_to", value="/admin/media?tab=trash"),
            Button(TRASH_SVG, Span("Empty trash", cls="ml-1"), type="button", cls="btn btn-sm text-error",
                   data_confirm="Permanently delete everything in trash? This can't be undone."),
            action="/admin/media/empty-trash", method="post"
        ) if trash_items else None
        # same card grid as Gallery/Unused, not a plain text list -
        # each card's own real thumbnail comes from the login-gated
        # /admin/media/trash-file/{filename} route above, since a
        # trashed file isn't reachable at the public /uploads/ url
        body = (Div(*[MediaCard(t, mode="trash", return_to=return_to) for t in page_trash],
                    cls=MEDIA_GRID)
                if page_trash else EmptyState("Trash is empty.", "🗑️"))

    kinds = [("", "All"), ("image", "Images"), ("audio", "Audio"), ("video", "Video"), ("document", "PDFs"),
             ("noalt", "No alt text")]
    filtered = q or kind or (tab == "all" and post)
    header = ListHeader(
        list_summary(total_count, "file", q, dict(kinds)[kind].lower() if kind else "",
                     f"in “{post_title}”" if tab == "all" and post else ""),
        clear=f"/admin/media?tab={tab}&sort={sort}" if filtered else None,
        form_id="media-bulk" if shown else None, action="/admin/media/bulk", return_to=return_to,
        total=total_count, scope={"in_tab": tab, "in_q": q, "in_kind": kind, "in_post": post if tab == "all" else ""},
        buttons=[BulkButton("Restore", "restore"),
                 BulkButton("Delete forever", "delete", danger=True,
                            confirm="Permanently delete the selected files? This can't be undone.",
                            confirm_all="Permanently delete all {n} files in the trash? This can't be undone.")]
        if tab == "trash" else [BulkButton("Name from alt text", "rename"),
                                BulkButton("Move to trash", "trash", danger=True)]
    )
    search_box = SearchField(q, "Search media…", "/admin/media", {"tab": tab, "sort": sort, "post": post, "kind": kind})
    kind_filter = FilterSelect("Kind", "kind", kinds, kind,
                               f"/admin/media?tab={tab}&sort={sort}&post={quote(post)}&q={quote(q)}&kind=") \
        if tab != "trash" else None

    tabs = Tabs(
        *[A(label, href=f"/admin/media?tab={key}{keep}",
            cls=f"tab tab-sm {'tab-active font-semibold' if key == tab else ''}")
          for key, label in MEDIA_TABS],
        id="media-tabs", cls=f"{TABS_CLS} mb-4"
    )
    # Upload is a button, not an inline file input: choosing files
    # submits the form straight away (multiple=True, so a whole batch
    # goes up in one go) - same "one primary action button in the title
    # row" look as Posts' New post
    upload = Form(
        Label(UPLOAD_SVG, Span("Upload", cls="ml-1"),
              Input(type="file", name="image", accept="image/*,audio/*,video/*,application/pdf,.pdf", required=True, multiple=True,
                    cls="hidden",
                    data_autosubmit=True),
              cls="btn btn-primary btn-sm cursor-pointer"),
        action="/admin/media/upload", method="post", enctype="multipart/form-data"
    )

    return Layout(
        PageHeader("Media", upload),
        tabs,
        ListToolbar([search_box, kind_filter, sort_picker], bulk_actions, filtered=bool(kind or sort != "newest")),
        header,
        body,
        pagination,
        *MediaDetailsDrawer(),
        MediaPickerDialog(settings.get_all()),
        settings=settings.get_all(), logged_in=True, pinned_tree=posts.list_pinned_tree(), admin_page=True, live=True
    )


@ar.post("/admin/media/upload")
async def upload(session, request):
    form = await request.form()
    # multiple=True on the file input means the browser can attach more
    # than one file under the same "image" field name - form.getlist()
    # is what actually gets all of them; form.get() only ever hands
    # back the first, which is exactly why this used to silently drop
    # every file past the first one whenever more than one was picked.
    files = form.getlist("image")
    count = 0
    for file in files:
        data = await file.read()
        name = getattr(file, "filename", "") or ""
        try:
            if images.kind_of(name) != "image":
                images.save_media(data, name)
            elif data and len(data) <= 8 * 1024 * 1024:
                images.save_upload(data, name)
            else:
                continue
            count += 1
        except Exception as e:
            log.warning("%s: %s", name, e)
    if count == 0:
        return _toast_redirect(f"Nothing uploaded - images up to 8 MB, audio, video and PDFs up to "
                               f"{config.MAX_MEDIA_MB} MB", "error")
    # tab=unused, not the default Gallery - a freshly uploaded image
    # isn't attached to anything yet, so it always lands in Unused
    # first. Redirecting to Gallery (where it doesn't show up) read as
    # "did my upload even work" - landing where the file actually is
    # fixes that without needing to explain the distinction in a toast.
    return _toast_redirect("Uploaded" if count == 1 else f"Uploaded {count} files",
                            return_to="/admin/media?tab=unused")


@ar.get("/admin/media/trash-file/{filename}")
def trash_file(session, filename: str):
    # login-gated, unlike the public /uploads/{filename} route
    # (routes/public.py) - a trashed image is deliberately unservable
    # there (moved out of UPLOADS_DIR's own root specifically to stop
    # being publicly reachable), this exists only to render a real
    # thumbnail on the admin's own trash card, not to make trashed
    # images embeddable again
    if not images.plain_name(filename):
        return Response("Not found", status_code=404)
    path = os.path.join(config.uploads_dir(), "_trash", filename)
    if not os.path.isfile(path):
        return Response("Not found", status_code=404)
    return FileResponse(path)


def _find_upload(filename: str):
    return next((i for i in images.list_uploads() if i["filename"] == filename), None)


@ar.get("/admin/media/details/{filename}")
def media_details(session, filename: str):
    item = _find_upload(filename)
    if not item:
        return Response("Not found", status_code=404)
    return MediaDetailsForm(item, images.usage_map().get(filename))


@ar.post("/admin/media/details/{filename}")
def save_media_details(session, filename: str, alt_text: str = "", caption: str = "", credit_name: str = "",
                       credit_url: str = "", dark_version: str = "", phone_version: str = ""):
    item = _find_upload(filename)
    if not item:
        return Response("Not found", status_code=404)
    images.set_meta(filename, alt_text, caption, credit_name=credit_name, credit_url=credit_url,
                    dark_version=dark_version, phone_version=phone_version)
    return MediaDetailsForm(item, images.usage_map().get(filename), status="Saved")


# settings that hold an upload's address - a rename updates them too
IMAGE_SETTINGS = ("author_avatar_url", "favicon_url", "header_icon_url", "banner_image_url", "app_icon_url",
                  "share_image_url")


def _rename_everywhere(filename, name):
    """Renames an upload and points every post and image setting at the
    new name. Returns (new name or None, how many posts changed)."""
    new = images.rename_upload(filename, name)
    if not new:
        return None, 0
    old_url, new_url = f"/uploads/{filename}", f"/uploads/{new}"
    changed = posts.replace_upload_url(old_url, new_url)
    s = settings.get_all()
    settings.set_many({k: new_url for k in IMAGE_SETTINGS if s.get(k) == old_url})
    return new, changed


def _readable_name(filename, usage):
    """A name for an older upload: its alt text, or the post it's in."""
    alt = images.get_meta(filename)["alt_text"]
    if alt:
        return " ".join(alt.split()[:6])
    posts_in = [u["title"] for u in usage.get(filename, []) if u["slug"]]
    return posts_in[0] if posts_in else ""


@ar.post("/admin/media/rename/{filename}")
def rename_media(session, filename: str, name: str = ""):
    new, changed = _rename_everywhere(filename, name)
    item = _find_upload(new or filename)
    if not item:
        return Response("Not found", status_code=404)
    if not new:
        return MediaDetailsForm(item, images.usage_map().get(filename),
                                status="Not renamed - give it a new name of letters and numbers")
    return MediaDetailsForm(item, images.usage_map().get(new),
                            status=f"Renamed{f' - {changed} post' + ('s' if changed != 1 else '') + ' updated' if changed else ''}")


@ar.post("/admin/media/edit/{filename}")
def edit_media(session, filename: str, action: str = "", ratio: str = "", keep: str = "center"):
    if action == "restore":
        done = images.restore_original(filename)
    else:
        done = images.edit_image(filename, action, ratio, keep)
    item = _find_upload(filename)
    if not item:
        return Response("Not found", status_code=404)
    status = {"left": "Rotated", "right": "Rotated", "crop": "Cropped", "restore": "Restored"}.get(action, "")
    return MediaDetailsForm(item, images.usage_map().get(filename),
                            edit_status=status if done else "Couldn't edit this image", edit_failed=not done)


@ar.get("/admin/media/picker")
def media_picker(session, q: str = "", tab: str = "", offset: int = 0, kind: str = "image", skip: str = ""):
    """The media picker's Gallery and Unused grids (ui.PickerGrid): both
    at once when it opens or its search changes, or the next few of one
    for its "Show more". kind - what the field takes: images, or audio
    for a sound field."""
    kind = "audio" if kind == "audio" else "image"
    usage = images.usage_map()
    # video and PDFs stay in Media - no field takes them
    # skip: the image whose other version is being picked - never itself
    uploads = [u for u in images.list_uploads() if u["kind"] == kind and u["filename"] != skip]
    if q.strip():
        text = images.search_text(uploads, usage)
        uploads = [u for u in uploads if images.matches(text[u["filename"]], q)]
    # All media is everything, as in Media - the unused ones marked
    unused = {u["filename"] for u in uploads if u["filename"] not in usage}
    grids = {"gallery": uploads, "unused": [u for u in uploads if u["filename"] in unused]}
    if tab in grids and offset > 0:
        return PickerGrid(tab, grids[tab], q, offset, unused=unused, kind=kind, skip=skip)
    return (PickerGrid("gallery", grids["gallery"], q, unused=unused, kind=kind, skip=skip),
            PickerGrid("unused", grids["unused"], q, oob=True, unused=unused, kind=kind, skip=skip))


@ar.get("/admin/media/stock/{source}")
def stock_search(session, request, source: str, q: str = ""):
    if source not in stock.SOURCES:
        return Response("Not found", status_code=404)
    q = q.strip()
    if not q:
        return ""
    try:
        results = stock.search(source, q)
    except Exception as e:
        log.warning("%s search failed: %s", source, e)
        return P("Search failed - check the API key in Integrations", cls="text-sm text-error py-6")
    return StockResults(source, results)


@ar.post("/admin/media/import")
def import_stock(session, url: str = "", alt: str = "", credit: str = "", credit_url: str = "", source: str = "",
                 download: str = ""):
    # called with fetch() from MEDIA_PICKER_JS, answers in JSON: the new
    # /uploads/ url on success, which the picker then fills in exactly
    # like a pick from the library. stock.download() only fetches from
    # the stock sites' own image hosts - see ALLOWED_HOSTS there.
    if source in stock.HOTLINKED:
        # Unsplash: used from its own servers, credited, and counted
        if not stock.is_unsplash_image(url):
            return JSONResponse({"error": "not an Unsplash image"}, status_code=400)
        images.set_meta(url, alt[:200], "", credit_name=credit[:200], credit_url=credit_url[:500],
                        credit_source="unsplash")
        stock.track_download(download)
        return JSONResponse({"url": url})
    try:
        new_url = images.save_upload(stock.download(url), alt or f"{source} photo")
    except Exception as e:
        log.warning("import failed: %s", e)
        return JSONResponse({"error": "import failed"}, status_code=400)
    # the photographer's name comes along too - Pixabay and Pexels both
    # ask for credit, and this is the moment we still know it
    images.set_meta(new_url.rsplit("/", 1)[1], alt[:200], "", credit_name=credit[:200],
                    credit_url=credit_url[:500], credit_source=source if source in images.CREDIT_SOURCES else "")
    return JSONResponse({"url": new_url})


@ar.post("/admin/media/delete")
def delete(session, filename: str, return_to: str = "/admin/media"):
    # older pages' permanent Delete - the library's own buttons all
    # move to trash now, so this does too
    return trash_one(session, filename, return_to)


@ar.post("/admin/media/trash")
def trash_one(session, filename: str, return_to: str = "/admin/media"):
    images.move_to_trash(filename)
    target = return_to if is_local_path(return_to) else "/admin/media"
    return _toast_redirect("Moved to trash", return_to=target,
                           undo=undo_url("/admin/media/restore", filename=filename, return_to=target))


@ar.post("/admin/media/bulk")
def bulk(session, action: str = "", filenames: list[str] = None, return_to: str = "/admin/media",
         all_matching: str = "", in_tab: str = "", in_q: str = "", in_kind: str = "", in_post: str = ""):
    target = return_to if is_local_path(return_to) else "/admin/media"
    if all_matching == "1":
        # within the tab it came from: trash's actions on the trash, the
        # others' on files in use or not - never across
        allowed = ("restore", "delete") if in_tab == "trash" else ("rename", "trash")
        if in_tab not in dict(MEDIA_TABS) or action not in allowed:
            return _toast_redirect("Select some files and choose what to do", "error", return_to=target)
        names = _media_tab_files(in_tab, in_q, in_kind, in_post)
    else:
        names = [f for f in (filenames or []) if f]
    if action == "rename" and names:
        # older uploads with random names: named after their alt text,
        # or the post they're in
        usage = images.usage_map()
        done = sum(1 for name in names if (readable := _readable_name(name, usage))
                   and _rename_everywhere(name, readable)[0])
        skipped = len(names) - done
        said = f"Renamed {done} image{'s' if done != 1 else ''}" + (
            f" - {skipped} kept {'their names' if skipped != 1 else 'its name'} (no alt text or post to name "
            f"{'them' if skipped != 1 else 'it'} after, or already named that)" if skipped else "")
        return _toast_redirect(said, "error" if not done else "success", return_to=target)
    do = {"trash": images.move_to_trash, "restore": images.restore_from_trash,
          "delete": images.delete_forever}.get(action)
    if not names or not do:
        return _toast_redirect("Select some files and choose what to do", "error", return_to=target)
    for name in names:
        do(name)
    said = {"trash": "Moved {n} to trash", "restore": "Restored {n}", "delete": "Permanently deleted {n}"}[action]
    return _toast_redirect(said.format(n=f"{len(names)} file{'s' if len(names) != 1 else ''}"), return_to=target)


@ar.post("/admin/media/restore")
def restore(session, filename: str, return_to: str = "/admin/media"):
    images.restore_from_trash(filename)
    return _toast_redirect("Restored", return_to=return_to)


@ar.post("/admin/media/delete-forever")
def delete_forever(session, filename: str, return_to: str = "/admin/media"):
    images.delete_forever(filename)
    return _toast_redirect("Permanently deleted", return_to=return_to)


@ar.post("/admin/media/empty-trash")
def empty_trash(session, return_to: str = "/admin/media"):
    count = images.empty_trash()
    return _toast_redirect(f"Permanently deleted {count} file(s)", return_to=return_to)
