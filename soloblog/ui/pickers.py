"""The media and link pickers."""
from fasthtml.common import *
from soloblog import gallery
from soloblog import i18n
from soloblog.actions import on, EL
from soloblog import images
from soloblog import posts
from soloblog import settings
from soloblog import stock
from soloblog.render import format_date
from soloblog.ui.icons import CHECK_SVG, LINK_SVG, PHOTO_SVG, SPEAKER_SVG, UPLOAD_SVG, X_SVG
from soloblog.ui.base import (
    MoreBelowSlot, RESULTS_CLS, RESULT_ABOUT, RESULT_EMPTY, RESULT_ROW, RESULT_TITLE, SCROLLS,
    SEARCH_DIALOG_ACTION, SEARCH_DIALOG_BOX, SearchBox, glass_fill,
)

# p-1 on the scrolling grid: overflow-y-auto clips sideways too (one axis
# not visible makes the other not visible), which cut off the hover ring
# of the thumbnails along its edges.
PICKER_GRID = "grid grid-cols-4 gap-2 max-h-80 overflow-y-auto p-1"
PICKER_THUMB = "w-full h-20 object-cover rounded-field cursor-pointer hover:ring-2 hover:ring-primary"


PICKER_PAGE = 60  # thumbnails in the image picker before "Show more"


def PickerGrid(tab, items, q="", offset=0, oob=False, unused=(), kind="image", skip=""):
    """One of the image picker's own-image tabs (Gallery, Unused): the
    first PICKER_PAGE thumbnails, and "Show more" for the next ones,
    which replaces itself (/admin/media/picker). Loaded when the picker
    opens and again as you search, never with the page - a library of
    thousands would make every editor page heavy."""
    from urllib.parse import quote
    page = items[offset:offset + PICKER_PAGE]
    more = len(items) - offset - len(page)
    # not lazy: Firefox (and Zen) never start a lazy image in a dialog, and
    # this is a page of PICKER_PAGE small copies, fetched as the picker opens
    # role and tabindex: a picture is picked from the keyboard too (MEDIA_PICKER_JS)
    thumbs = [Div(Img(src=images.thumb(u["url"]), data_url=u["url"], decoding="async", role="button", tabindex="0",
                      alt=u["filename"], cls=f"media-picker-row {PICKER_THUMB}") if kind == "image" else
                  # a sound: its name to pick by - there's nothing to see
                  Button(SPEAKER_SVG, Span(u["filename"], cls="text-xs break-all line-clamp-2"), type="button",
                         data_url=u["url"], cls=f"media-picker-row {PICKER_THUMB} btn h-20 flex-col gap-1 p-2"),
                  Span("Unused", cls="badge badge-xs badge-warning absolute bottom-1 left-1 pointer-events-none")
                  if tab == "gallery" and u["filename"] in unused else None,
                  cls="relative") for u in page]
    more_btn = Button(f"Show more ({more})", type="button", cls="btn btn-sm col-span-full",
                      hx_get=f"/admin/media/picker?tab={tab}&offset={offset + PICKER_PAGE}&q={quote(q)}&kind={kind}"
                             f"{'&skip=' + quote(skip) if skip else ''}",
                      hx_target="this", hx_swap="outerHTML") if more > 0 else None
    if offset:
        return (*thumbs, more_btn)
    what = "sounds" if kind == "audio" else "images"
    empty = ("Nothing matches" if q else {"gallery": f"No {what} yet", "unused": f"No unused {what}"}[tab])
    return Div(Div(*thumbs, more_btn, cls=PICKER_GRID) if page else P(empty, cls="text-sm text-base-content/60 py-6"),
               id=f"picker-{tab}", hx_swap_oob="true" if oob else None)


def _stock_tab(source, settings):
    label = stock.SOURCES[source]
    if not settings.get(stock.KEY_SETTINGS[source]):
        return P(f"Add {'an' if label[0] in 'AEIOU' else 'a'} {label} API key in ", A("Integrations", href="/admin/settings?tab=integrations", cls="link"),
                 " to search here.", cls="text-sm text-base-content/60 py-6")
    return Div(
        SearchBox("w-full mb-2", name="q", placeholder=f"Search {label}", aria_label=f"Search {label}",
                  autocomplete="off",
                  hx_get=f"/admin/media/stock/{source}", hx_trigger="input changed delay:500ms, search",
                  hx_target=f"#stock-results-{source}", hx_swap="innerHTML"),
        Div(id=f"stock-results-{source}"),
    )


def StockResults(source, results):
    """What the stock tab's search swaps in. Picking one downloads it
    into the library first (MEDIA_PICKER_JS -> /admin/media/import) -
    data-full is the large version to import, src only the preview.
    The credit line is Pixabay's own API requirement ("show your users
    where the images are from"), and Pexels asks for the same."""
    if not results:
        return P("No results", cls="text-sm text-base-content/60 py-6")
    home = {"pixabay": "https://pixabay.com", "pexels": "https://www.pexels.com",
            "unsplash": "https://unsplash.com/?utm_source=soloblog&utm_medium=referral"}[source]
    return Div(
        Div(*[Img(src=r["thumb"], data_full=r["full"], data_alt=r["alt"],
                  alt=r["alt"] or f"{stock.SOURCES[source]} photo", decoding="async",
                  data_credit=r.get("credit", ""), data_credit_url=r.get("credit_url", ""), data_source=source,
                  data_download=r.get("download", ""), role="button", tabindex="0",
                  cls=f"stock-picker-row {PICKER_THUMB}") for r in results], cls=PICKER_GRID),
        P("Images from ", A(stock.SOURCES[source], href=home, target="_blank", rel="noopener", cls="link"),
          " - shown from Unsplash's own servers, as its terms require, so they aren't copied to your library."
          if source in stock.HOTLINKED else None,
          cls="text-xs text-base-content/50 mt-2"),
    )


def MediaPickerDialog(settings):
    """One shared <dialog> per page - MediaPickerButton just tells it
    which field to fill in, so several buttons on one page (cover
    image, avatar, favicon) can all reuse the same picker markup.

    Gallery/Unused split the same way as the Media page's own tabs (one
    usage_map() scan feeding both), and Pixabay/Pexels search stock
    photos with the keys from Settings > Integrations. Radio-input tabs, pure
    CSS - no JS to switch between them.

    Upload sits right of the title, like the Media page's own header,
    but uploads in the background (MEDIA_PICKER_JS) and uses the new
    image straight away - a form submit here would reload the page and
    lose unsaved edits in the post editor. #media-picker-status beside
    it is the dialog's one inline status line (uploads and stock
    imports), in place of a toast."""
    # the two grids of your own images come from /admin/media/picker when
    # it opens (openMediaPicker)
    loading = Span(cls="loading loading-spinner loading-sm text-base-content/40 m-6")
    tabs = [
        ("All media", Div(loading, id="picker-gallery")),
        ("Unused", Div(loading, id="picker-unused")),
        ("Pixabay", _stock_tab("pixabay", settings)),
        ("Pexels", _stock_tab("pexels", settings)),
        ("Unsplash", _stock_tab("unsplash", settings)),
    ]
    stock_tabs = {"Pixabay", "Pexels", "Unsplash"}
    return Dialog(
        Div(
            # the title and Upload, then the search on its own full row - as
            # the post picker has it; all three on one row folded the title
            # onto two lines on a phone
            Div(
                H3("Choose an image", id="media-picker-title", cls="font-semibold truncate min-w-0"),
                Div(
                    Span(id="media-picker-status", role="status", cls="text-xs"),
                    Label(UPLOAD_SVG, Span("Upload", cls="ml-1"),
                          Input(type="file", accept="image/*", id="media-picker-upload", cls="hidden",
                                **on("change", "uploadToPicker", EL)),
                          cls="btn btn-sm cursor-pointer"),
                    cls="flex items-center gap-3 shrink-0"
                ),
                cls="flex items-center justify-between gap-3 mb-3"
            ),
            # your own images, by name, alt text, caption, credit or the post they're in
            # what the field takes - set as the picker opens (openMediaPicker)
            Input(type="hidden", name="kind", value="image", id="media-picker-kind"),
            # an image that can't be picked: the one whose other version this is
            Input(type="hidden", name="skip", value="", id="media-picker-skip"),
            SearchBox("w-full mb-2", name="q", id="media-picker-search", placeholder="Search your media…",
                      aria_label="Search your media", autocomplete="off",
                      hx_get="/admin/media/picker", hx_trigger="input changed delay:250ms, search",
                      hx_include="#media-picker-kind, #media-picker-skip", hx_target="#picker-gallery", hx_swap="outerHTML"),
            Div(
                *[el for i, (label, content) in enumerate(tabs) for el in (
                    Input(type="radio", name="media_picker_tab", cls="tab", aria_label=label, checked=(i == 0),
                          data_images_only=True if label in stock_tabs else None),
                    # min-h - the dialog stays one height across tabs
                    # instead of resizing (and re-centering) on every switch
                    Div(content, cls="tab-content pt-3 sm:min-h-80"),
                )],
                role="tablist", data_scroll_hint=True,
                cls=f"tabs tabs-border tabs-sm min-h-0 overflow-y-auto {SCROLLS}"
            ),
            Div(
                # gallery mode only (the editor's Gallery button): pick
                # several images, choose a style, insert them as one block
                Div(
                    Select(Option("Site default style", value=""),
                           *[Option(label.split(" — ")[0], value=key) for key, label in gallery.STYLES.items()],
                           id="gallery-picker-style", aria_label="Gallery style", cls="select select-sm w-44"),
                    Span(id="gallery-picker-count", cls="text-xs text-base-content/60"),
                    cls="gallery-mode-only hidden flex items-center gap-2 mr-auto"
                ),
                Button(X_SVG, Span(i18n.t("Close"), cls="ml-1"), type="button", cls="btn btn-sm",
                       data_close_dialog="media-picker-dialog"),
                Button(CHECK_SVG, Span("Insert gallery", cls="ml-1"), type="button", id="gallery-insert-btn",
                       cls="gallery-mode-only hidden btn btn-primary btn-sm", disabled=True,
                       **on("click", "insertGallery")),
                cls=f"{SEARCH_DIALOG_ACTION} flex-wrap"),
            cls=f"{SEARCH_DIALOG_BOX} {glass_fill(settings)}"
        ),
        Form(Button(cls="cursor-default", aria_label=i18n.t("Close")), method="dialog", cls="modal-backdrop"),
        id="media-picker-dialog", aria_labelledby="media-picker-title", cls="modal modal-top sm:modal-middle"
    )


def MediaPickerButton(target_input_id: str, label: str = "Pick", icon=None):
    # join-item - always paired with its target input inside a join
    # wrapper (see every call site: header icon/favicon/hero image/
    # author avatar/cover image), never used on its own, so it carries
    # the class itself rather than each caller repeating it. The picker
    # shows what the field takes - its data-picker-kind (audio), or images.
    return (Button(icon or PHOTO_SVG, Span(label, cls="ml-1"), type="button", cls="btn btn-sm join-item",
                   **on("click", "openMediaPicker", target_input_id)),
            ClearPickedButton(target_input_id))


def ClearPickedButton(target_input_id: str):
    """Empties a picker's field - every Pick has one beside it (PageField too)."""
    return Button(X_SVG, type="button", aria_label="Clear", data_tip="Clear",
                  cls="btn btn-sm btn-square join-item tooltip", **on("click", "clearPageField", target_input_id))


def LinkPickerDialog():
    """Browse your own posts/pages and click one to fill in a link -
    no copying a slug or typing /post/whatever by hand. One shared
    <dialog> per page, same as MediaPickerDialog: openLinkPicker(id)
    just tells it which field to fill in, or - from inside the post
    editor's toolbar - hands it the EasyMDE instance directly to
    insert markdown instead. The list (LinkPickerResults) comes from
    /admin/link-picker when it opens and as you type."""
    body = Div(
        # what the field takes - a link, or one of your pages (PageField);
        # set as the picker opens (openLinkPicker)
        Input(type="hidden", name="kind", value="", id="link-picker-kind"),
        SearchBox("w-full", name="q", id="link-picker-search", placeholder="Search by title…",
                  aria_label="Search by title", autocomplete="off",
                  hx_get="/admin/link-picker", hx_trigger="input changed delay:200ms, search",
                  hx_include="#link-picker-kind", hx_target="#link-picker-results"),
        Div(id="link-picker-results", data_scroll_hint=True, data_scroll_more="link-picker-more",
            cls=f"mt-1 {RESULTS_CLS}"),
        cls="flex flex-col min-h-0"
    )
    return Dialog(
        Div(
            H3("Link to a post or page", id="link-picker-title", cls="font-semibold mb-3"),
            body,
            Div(MoreBelowSlot("link-picker-more"),
                Button(X_SVG, Span(i18n.t("Close"), cls="ml-1"), type="button", cls="btn btn-sm",
                       data_close_dialog="link-picker-dialog"),
                cls=SEARCH_DIALOG_ACTION),
            cls=f"{SEARCH_DIALOG_BOX} max-w-lg {glass_fill(settings.get_all())}"
        ),
        Form(Button(cls="cursor-default", aria_label=i18n.t("Close")), method="dialog", cls="modal-backdrop"),
        id="link-picker-dialog", aria_labelledby="link-picker-title", cls="modal modal-top sm:modal-middle"
    )


def builtin_pages(s):
    """The pages Soloblog makes itself, that are there right now - the
    link picker lists them, so nobody has to know /newsletter by heart.
    The same list the menu and footer offer (posts.SITE_PAGES)."""
    return [(page[1], page[0], page[2]) for key, page in posts.SITE_PAGES.items() if not posts.site_note(s, key)]


def _picker_group(title):
    return P(title, cls="text-xs font-semibold text-base-content/60 px-3 pt-3 pb-1 first:pt-1")


def _picker_row(title, url, about, slug=None):
    # a button, so the keyboard reaches it too (LINK_PICKER_JS fills the link)
    return Button(
        Span(title, cls=RESULT_TITLE),
        Span(about, cls=RESULT_ABOUT),
        type="button", data_title=title, data_url=url, data_slug=slug, cls=f"link-picker-row {RESULT_ROW}"
    )


def PageField(name, slug, kind, placeholder="None", exclude="", id=None):
    """One of your pages, chosen with the link picker (kind: "home" - a
    page or unlisted post for the homepage; "page" - a page in the menu
    or footer) instead of a long dropdown of them. The slug is what's
    sent; its title is what you see. id - where several on a page share
    a name."""
    row = posts.get_post(slug) if slug else None
    id = id or name
    return Div(
        Input(type="hidden", name=name, id=id, value=slug or "", data_picker_kind=kind,
              data_picker_exclude=exclude or None, data_autosave=True),
        Input(id=f"{id}-title", value=row["title"] if row else "", placeholder=placeholder, readonly=True,
              aria_label=placeholder, cls="input input-sm flex-1 min-w-0 join-item cursor-pointer",
              **on("click", "openLinkPicker", id)),
        Button(LINK_SVG, Span("Pick", cls="ml-1"), type="button", cls="btn btn-sm join-item",
               **on("click", "openLinkPicker", id)),
        Button(X_SVG, type="button", aria_label="Clear", data_tip="Clear",
               cls="btn btn-sm btn-square join-item tooltip", **on("click", "clearPageField", id)),
        cls="join w-full"
    )


def LinkPickerResults(rows, total, q="", kind=""):
    """The newest posts and pages whose title matches - drafts and
    scheduled ones too (post_status() labels them), since it's you
    picking your own work. Same title/date look as the site search.
    The built-in pages (builtin_pages) that match come first - a short
    list, and the one people can't guess the address of."""
    needle = q.strip().lower()
    if kind:
        # one of your pages (PageField) - just them, by title
        if not rows:
            return P("Nothing matches" if needle else "No pages yet", cls=RESULT_EMPTY)
        return (*[_picker_row(p["title"], posts.url_for(p), posts.url_for(p) + (
                    f" · {posts.post_status(p)}" if posts.post_status(p) not in ("Published", "Pinned") else ""),
                              slug=p["slug"]) for p in rows],
                P(f"{len(rows)} of {total} - type to find others", cls="text-xs text-base-content/50 pt-2")
                if total > len(rows) else None)
    builtins = [p for p in builtin_pages(settings.get_all()) if needle in p[0].lower() or needle in p[1]]
    if not rows and not builtins:
        return P("Nothing matches", cls=RESULT_EMPTY)
    relative = settings.get("relative_dates") == "1"
    return (
        # the count at the top, as the site's search has
        P(f"Results: {len(builtins) + total}", cls="text-xs text-base-content/50 px-1 pb-1") if needle else None,
        _picker_group("Built-in pages") if builtins else None,
        *[_picker_row(*p) for p in builtins],
        _picker_group("Posts and pages") if rows else None,
        *[_picker_row(
            p["title"],
            posts.url_for(p),
            format_date(p["created_at"], relative) +
            (f" · {posts.post_status(p)}" if posts.post_status(p) != "Published" else "")
        ) for p in rows],
        P(f"The newest {len(rows)} of {total} - type to find others", cls="text-xs text-base-content/50 pt-2")
        if total > len(rows) else None,
    )


def LinkPickerButton(target_input_id: str, label: str = "Pick"):
    # same join-item reasoning as MediaPickerButton - always paired
    # with its target input inside a join wrapper.
    return (Button(LINK_SVG, Span(label, cls="ml-1"), type="button", cls="btn btn-sm join-item",
                   **on("click", "openLinkPicker", target_input_id)),
            ClearPickedButton(target_input_id))
