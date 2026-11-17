"""An admin list's parts: its header, toolbar, filters, bulk buttons and Save bar."""
from fasthtml.common import *
from soloblog.actions import on, EL
from soloblog import settings
from soloblog.ui.icons import (
    CHECK_SVG, CHEVRON_DOWN_SVG, DOWNLOAD_SVG, EDIT_SVG, FOCUS_SVG, PLUS_SVG, RESTORE_SVG, SEND_SVG, TRASH_SVG,
    X_SVG,
)
from soloblog.ui.base import CancelButton, IconAction, SCROLLS, SCROLLS_X, glass_fill


def EditPostLink(slug: str):
    """Sits right on the article, not buried in a separate management
    list - if you're an admin looking at your own post, editing it
    should be one click from there."""
    # icons, named by their tooltips, so they always fit beside the title -
    # a post's and a pinned page's alike
    return Div(IconAction(EDIT_SVG, "Edit", href=f"/admin/edit/{slug}", menu_label=False, size="sm",
                          tip="tooltip-bottom"),
               IconAction(FOCUS_SVG, "Edit in Focus", href=f"/admin/edit/{slug}?focus=1", menu_label=False,
                          size="sm", tip="tooltip-bottom"),
               cls="join shrink-0")


def PageNav(groups, current, base, id, name):
    """Where the admin menu isn't beside the page (a phone): the page you're
    on, its group first, and a menu of every page under their headings - one
    tap away. For a set of many pages (Settings' twenty, Help's sixteen),
    as a phone's own settings list them; a few choices keep their tabs.
    name: what the pages are, for a screen reader ("Settings pages")."""
    label = next((text for _, pages in groups for key, text in pages if key == current), "")
    group = next((g for g, pages in groups if current in dict(pages)), "")
    return Div(
        Button(Span(f"{name}, ", cls="sr-only"),
               Span(Span(f"{group} ›", cls="text-base-content/60"), " ", label, cls="truncate min-w-0"),
               type="button", popovertarget=id,
               cls="select select-sm w-full max-w-full min-w-0 text-left"),
        Ul(*[part for g, pages in groups for part in [Li(g, cls="menu-title")] + [
                Li(A(text, href=f"{base}?tab={key}", cls="menu-active" if key == current else None,
                     aria_current="page" if key == current else None)) for key, text in pages]],
           popover="auto", id=id,
           cls=f"dropdown-content menu menu-sm flex-nowrap rounded-box border border-base-300 bg-base-100 shadow-lg "
               f"w-max max-w-[calc(100vw-2rem)] max-h-[70vh] overflow-y-auto {SCROLLS}"),
        cls="mb-6 [html[data-admin-beside]_&]:hidden"
    )


def SaveStatus(message: str = "", kind: str = "success"):
    """What an htmx-submitted form's save-status span gets swapped to
    after a save - the confirmation itself, shown inline left of the
    form's own buttons (every Settings tab's SaveBar, the post editor's
    action row), never a toast. Its class is also what htmx:afterSwap
    (SAVE_STATUS_CLEAR_JS, app.py) checks to decide whether to
    rebaseline the post editor's own dirty-tracking."""
    # a change to the page's own frame (settings.FRAME) shows on a reload
    # (SAVE_STATUS_CLEAR_JS), with this message carried across it
    reload = "1" if kind == "success" and settings.frame_changed() else None
    return Span(message, id="save-status", role="status", data_reload=reload,
                cls=f"text-xs {'text-success' if kind == 'success' else 'text-error'}")


def PageHeader(title, action=None):
    """The admin pages' shared first row: the page title on the left,
    that page's one primary action (New post, Upload...) on the right -
    same position and spacing on every list page, so the eye always
    knows where to look for "the thing to do here".

    The data-status-slot span is where a list action's confirmation
    lands after its redirect ("Moved to trash", "Approved"...) - inline,
    left of the action button, instead of a toast (see showStatus,
    TOAST_JS in app.py)."""
    # the browser tab says which admin page this is ("Posts — My Blog")
    from soloblog import seo
    from soloblog import settings as _settings
    if not seo.current_title():
        seo._page_title.set(f"{title} — {_settings.get('site_title')}")
    return Div(
        # the title wraps; its buttons keep their size (they spilled off a
        # 320 px screen as 44 px buttons)
        H1(title, cls="text-xl sm:text-2xl font-bold min-w-0"),
        Div(Span(data_status_slot=True, role="status", cls="text-xs"), action, cls="flex items-center gap-3 shrink-0"),
        cls="flex justify-between items-center gap-3 mb-4"
    )


def ListToolbar(filters=(), actions=None, filtered=False):
    """The admin list pages' shared row between the tabs and the list:
    filters/sort on the left (what you're looking at), bulk actions on
    the right (what you can do to all of it). One row, not one each -
    returns None when a tab has neither.

    On a phone, two or more filters wait behind one Filter button beside
    the search, so the list starts on the first screen; filtered: one of
    them is set, and they show."""
    filters = [f for f in filters if f is not None]
    if not filters and actions is None:
        return None
    search = [f for f in filters if getattr(f, "tag", "") == "form"]
    rest = [f for f in filters if getattr(f, "tag", "") != "form"]
    if search and len(rest) > 1:
        # a tick box before its button and the filters: open or shut with
        # no script (not daisyUI's own tick-box button - ticked, that one
        # is primary - and not :has() on the row, which restyles the page)
        filters = search + [
            Input(type="checkbox", id="filter-toggle", checked=filtered, data_filter_toggle=True,
                  cls="peer sr-only"),
            Label("Filter", fr="filter-toggle",
                  cls="btn btn-sm sm:hidden peer-checked:bg-base-300 peer-focus-visible:outline-2 "
                      "peer-focus-visible:outline-offset-2"),
            Div(*rest, cls="contents max-sm:hidden max-sm:peer-checked:flex "
                           "max-sm:flex-wrap max-sm:items-center max-sm:gap-2 max-sm:w-full")]
    return Div(
        Div(*filters, cls="flex flex-wrap items-center gap-2"),
        Div(actions, cls="ml-auto") if actions is not None else None,
        cls="flex flex-wrap items-center justify-between gap-2 mb-3"
    )


def FilterSelect(label, name, options, selected, go):
    """A filter or sort, named in the box itself ("Tag", "Sort") so it
    reads as what it is, not just as its current value. options: (value,
    label). A daisyUI drop-down of links, not a <select>: Firefox and
    Safari draw a select's list themselves, unstyled and unthemed. Each
    choice is a link (go + its value), so a live list swaps in place."""
    from urllib.parse import quote
    current = next((text for value, text in options if value == selected), options[0][1] if options else "")
    menu_id = f"filter-{name}"
    return Div(
        Button(Span(label, Span(":", cls="sr-only"), cls="text-base-content/60"), " ", Span(current, cls="truncate"),
               Span(CHEVRON_DOWN_SVG, cls="opacity-60 [&>svg]:h-3 [&>svg]:w-3"),
               type="button", popovertarget=menu_id,
               # a long choice (a post's title) mustn't stretch the whole toolbar
               cls="btn btn-sm font-normal gap-2 max-w-full sm:max-w-72"),
        # a rounded box that clips, the list scrolling inside it (as the
        # theme menu does) - so a long list keeps its corners
        Div(Ul(*[Li(A(text, href=go + quote(value, safe=""), aria_current="true" if value == selected else None,
                      cls="menu-active" if value == selected else None)) for value, text in options],
               data_scroll_hint=True, cls=f"menu menu-sm flex-nowrap w-max max-h-72 overflow-y-auto {SCROLLS}"),
            id=menu_id, popover="auto",
            cls=f"dropdown-content {glass_fill(settings.get_all())} rounded-box overflow-hidden z-20 mt-1 p-1 shadow "
                "border-[length:var(--border)] border-base-200"),
    )


def list_summary(n: int, noun: str, q: str = "", *filters) -> str:
    """"12 posts", or "3 posts matching “coffee” · tagged garden"."""
    text = f"{n} {noun}{'' if n == 1 else 's'}"
    parts = ([f"matching “{q}”"] if q else []) + [f for f in filters if f]
    return text + (" " + " · ".join(parts) if parts else "")


# a worded button has its icon (docs/DEVELOPMENT.md > Buttons)
_BULK_ICONS = {"trash": TRASH_SVG, "delete": TRASH_SVG, "restore": RESTORE_SVG, "rename": EDIT_SVG,
               "tag": PLUS_SVG, "publish": SEND_SVG, "draft": EDIT_SVG, "export": DOWNLOAD_SVG,
               "remove": TRASH_SVG}


def BulkButton(label, key, danger=False, confirm="", confirm_all="", for_states=None, needs=None, download=False):
    """One of ListHeader's actions - submits its form with action=key.
    confirm: asked first, for what can't be undone; confirm_all: the same
    when every page is selected, {n} the count. for_states: shown only
    while a ticked row's data-state is one of these (Publish for drafts);
    needs: the name of a field it's greyed out without (Add tag);
    download: it sends back a file (Export), so the browser takes it -
    not the in-place update the list's other actions get (live.js)."""
    # moving to trash asks first too, like every trash button
    if key == "trash" and not confirm:
        confirm = "Move the selected items to trash? You can restore them from Trash."
        confirm_all = confirm_all or "Move all {n} to trash? You can restore them from Trash."
    return Button(_BULK_ICONS.get(key, CHECK_SVG), Span(label, cls="ml-1"), type="submit", name="action", value=key,
                  data_confirm=confirm or None,
                  data_confirm_all=confirm_all or None,
                  data_bulk_for=",".join(for_states) if for_states else None, data_needs=needs,
                  data_download=download or None,
                  cls=f"btn btn-sm{' text-error' if danger else ''}")


def ListHeader(summary, clear=None, form_id=None, action="", buttons=(), extra=(), return_to="", total=None,
               scope=None):
    """The line between a list's filters and the list itself. At rest it
    says how many there are - or what the filters left, with Clear to
    show everything again. Tick rows (or Select all, which lines up with
    the rows' own boxes) and it turns into "3 selected" with what can be
    done to them, and Cancel (BULK_JS, app.py). Rows join the form with
    RowCheck (form=), since each row has its own forms and forms can't
    nest. Without form_id it's just the summary.

    total: how many the filters match on every page. With the whole page
    ticked and more beyond it, "Select all N" sends all_matching=1 and
    scope (the filters, as fields) for the action to rebuild that set."""
    idle = Div(Span(summary, cls="text-sm text-base-content/70"),
               A("Clear", href=clear, cls="link link-hover text-sm ms-2") if clear else None,
               data_bulk_idle=True, cls="flex-1 min-w-0")
    if not form_id:
        return Div(idle, cls="flex items-center gap-3 px-4 min-h-10 mb-1")
    return Form(
        # Enter in a field here (a tag name) mustn't press the first action
        Button(type="submit", disabled=True, hidden=True, aria_hidden="true", tabindex="-1"),
        Span(Input(type="checkbox", aria_label="Select all", data_select_all=True,
                   cls="checkbox checkbox-sm", **on("change", "selectAllRows", EL)),
             data_tip="Select all", cls="tooltip tooltip-right inline-flex"),
        idle,
        Div(Div(Span(data_bulk_count=True, cls="text-sm font-medium whitespace-nowrap"),
                Button(type="button", data_bulk_all=True, hidden=True,
                       cls="link link-hover text-xs text-left whitespace-nowrap")
                if total else None,
                cls="flex flex-col items-start shrink-0 gap-x-2"),
            # one row at every width - wrapped or stacked, the first tick
            # made the bar taller and pushed the list down. What doesn't
            # fit goes under More (fitBulk, actions.js), as a row of tabs does;
            # on the narrowest phone what's left swipes. ms-auto, not
            # justify-end, so a row too wide still starts in reach
            Div(*extra, *buttons, data_scroll_x=True,
                cls="flex-1 min-w-0 flex flex-nowrap items-center gap-2 overflow-x-auto [&>*]:shrink-0 "
                    f"[&>:first-child]:ms-auto {SCROLLS_X}"),
            Button("More", CHEVRON_DOWN_SVG, type="button", popovertarget=f"{form_id}-more", hidden=True,
                   data_bulk_more=True, cls="btn btn-sm gap-1 shrink-0"),
            Ul(id=f"{form_id}-more", popover="auto",
               cls=f"menu menu-sm dropdown-content dropdown-end w-max {glass_fill(settings.get_all())} rounded-box z-20 "
                   "p-2 shadow border-[length:var(--border)] border-base-200"),
            # beside the row, not in it, so it's never swiped out of reach
            Span(Button(X_SVG, type="button", aria_label="Cancel", data_bulk_cancel=True,
                        cls="btn btn-sm btn-ghost btn-square"),
                 data_tip="Cancel", cls="tooltip tooltip-left shrink-0"),
            data_bulk_busy=True, hidden=True,
            cls="flex-1 min-w-0 flex items-center gap-2"),
        Input(type="hidden", name="return_to", value=return_to),
        Input(type="hidden", name="all_matching", value="", data_bulk_all_field=True) if total else None,
        *[Input(type="hidden", name=k, value=v) for k, v in (scope or {}).items()],
        id=form_id, action=action, method="post", data_bulk=True, data_bulk_total=total,
        # as tall as its buttons from the start - they're 44px on a touch screen
        cls="flex items-center gap-3 px-4 min-h-10 pointer-coarse:min-h-11 mb-1"
    )


# A row with a RowCheck: pointing at it shows the box, and on a phone
# pressing and holding it ticks it (actions.js) - so a long press doesn't
# also select its words or open the link's menu
TICK_ROW = {"data_tick_row": True}
TICK_ROW_CLS = "pointer-coarse:select-none pointer-coarse:[-webkit-touch-callout:none]"


def RowCheck(form_id, name, value, label, cls="", state=None):
    """A row's tick for ListHeader's form. state - what the row is
    (published, draft...), for actions that only fit some (BulkButton).
    Out of sight, its space kept so nothing moves, until its row
    (TICK_ROW) is pointed at, it has the keyboard, or anything in the list
    is ticked (data-ticking, syncBulk) - as Linear's and Google Photos' do.
    On a touch screen it can't be tapped by accident while it's unseen."""
    return Input(type="checkbox", name=name, value=value, form=form_id, aria_label=f"Select {label}",
                 data_state=state,
                 cls=("checkbox checkbox-sm shrink-0 opacity-0 transition-opacity checked:opacity-100 "
                      "focus-visible:opacity-100 data-[ticking]:opacity-100 "
                      "[@media(hover:hover)]:[[data-tick-row]:hover_&]:opacity-100 "
                      f"pointer-coarse:not-data-[ticking]:pointer-events-none {cls}").strip())


def SaveBar(save_label: str = "Save", status: str = ""):
    """Status span on the left, Discard then Save on the right - same
    shape as the post editor's own action row (status text at the
    start of the row, the button cluster pushed to the end via
    ml-auto, Save right-most since it's the primary action). Pair
    with hx_post/hx_target="#save-status"/hx_swap on the <Form> itself;
    the route returns SaveStatus(message) instead of redirecting or
    toasting - Cancel needs no such wiring, it never leaves the client
    (see CancelButton)."""
    # Switches and choices save as they change (AUTOSAVE_JS); the buttons
    # are for what's typed, so they show - and the bar stays in view at
    # the screen's foot - only while there's something unsaved
    return Div(
        Span(status, id="save-status", role="status",
             cls=f"text-xs {'text-success' if status else 'text-base-content/50'} self-center"),
        Div(
            CancelButton(),
            Button(CHECK_SVG, Span(save_label, cls="ml-1"), type="submit", cls="btn btn-primary btn-sm"),
            cls="hidden in-data-dirty:flex items-center gap-2 ml-auto"
        ),
        cls="flex items-center gap-2 min-h-8 in-data-dirty:sticky in-data-dirty:bottom-0 in-data-dirty:z-20 "
            "in-data-dirty:bg-base-200 in-data-dirty:py-2"
    )
