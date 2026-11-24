from urllib.parse import quote

from fasthtml.common import *

from soloblog import comments
from soloblog import members
from soloblog import replymail
from soloblog import settings
from soloblog import posts
from soloblog.render import format_date, web_url
from soloblog.ui import ReplyBox, ReplyButton
from soloblog.ui import Tabs, TABS_CLS
from soloblog.ui import IconAction
from soloblog.ui import RowActions
from soloblog.ui import (ListHeader, BulkButton, FilterSelect, SearchField, OffNotice, list_summary, RowCheck, TICK_ROW, TICK_ROW_CLS, Layout, EmptyState, TRASH_SVG, RESTORE_SVG, CHECK_SVG, REPLY_SVG, Pagination, rows_per_page,
                PageHeader, ListToolbar, top_options)
from soloblog.guards import is_local_path, status_redirect, undo_url
from soloblog.routes.public import MAX_REPLY_DEPTH, REPLY_INDENT

ar = APIRouter()


def _toast_redirect(path: str, message: str, kind: str = "success", undo: str = ""):
    return status_redirect(path, message, kind, undo)


# same tab/pagination language as Posts (STATUS_TABS) and Media
# (MEDIA_TABS) - Pending/Approved mirror what a comment actually is at
# any moment (not yet public / already public), Trash the same
# recoverable-delete pattern both of those already have.
COMMENT_TABS = [("pending", "Pending"), ("approved", "Approved"), ("trash", "Trash"), ("mentions", "Mentions")]
COMMENTS_PER_PAGE = 15
COMMENT_SORTS = [("newest", "Newest"), ("oldest", "Oldest")]


def _post_title(slug: str) -> str:
    row = posts.get_post(slug)
    return row["title"] if row else slug


def MemberPill(c):
    """A signed-in member's comment says so - and whether they pay - in
    the same pills as Admin > Members."""
    member = members.get(c["member_id"]) if "member_id" in c.keys() and c["member_id"] else None
    if not member:
        return None
    paid = members.has_paid(member)
    return Span("Paid member" if paid else "Member",
                cls=f"badge badge-xs ml-2 whitespace-nowrap {'badge-primary' if paid else 'badge-primary badge-soft'}")


def CommentRow(c, status, depth=0, post=""):
    # title line - the post this comment is on, same treatment Posts'
    # own row gives its title (link, text-sm) - no "on " prefix, this
    # reads as a title now, not a sentence fragment
    # the post's title, not its slug - "Don't panic" reads, "don-t-panic" doesn't
    title_link = A(_post_title(c["post_slug"]), href=f"/post/{c['post_slug']}#comments", cls="link text-sm")

    if status == "approved" and c["trashed_at"]:
        # a placeholder for a trashed comment kept only because it
        # still has surviving replies nested under it (see
        # list_approved_with_deleted_parents, comments.py) - same
        # rendering the live page gives it, so an admin sees the exact
        # same thing a visitor would. Managing it (Restore, or
        # permanently deleting it) happens in the Trash tab, where
        # every trashed comment - placeholder-worthy or not - already
        # lives, not duplicated here.
        return Li(
            Div(
                title_link,
                Div(f"Deleted {format_date(c['trashed_at'])}", cls="text-xs text-base-content/50 mt-0.5"),
                P(Em("This comment was deleted."), cls="my-2 text-base-content/50"),
                cls="list-col-grow"
            ),
            cls=f"list-row {REPLY_INDENT[depth]}".strip()
        )

    # who and when, on one line: the name at full weight, the rest muted.
    # "Author" comes from is_author - visitors reply too. The reply arrow:
    # from depth in a thread (a reply whose parent is gone has none); in
    # Pending, a flat list, from parent_id.
    is_reply = depth > 0 if status != "pending" else bool(c["parent_id"])
    date_label = f"Deleted {format_date(c['trashed_at'])}" if status == "trash" else format_date(c["created_at"])
    meta = Div(
        Span(REPLY_SVG, cls="inline-flex opacity-40 mr-1 align-middle") if is_reply else None,
        Strong(c["author_name"], cls="whitespace-nowrap"),
        Span("Author", cls="badge badge-outline badge-xs ml-2") if c["is_author"] else None,
        MemberPill(c),
        A(f"<{c['email']}>", href=f"mailto:{c['email']}",
          cls="text-xs text-base-content/50 link link-hover block sm:inline sm:ml-1 break-all") if c["email"] else None,
        Span(f" · {date_label}", cls="text-xs text-base-content/50"),
        cls="mt-0.5"
    )
    # Pending is a flat list, so a reply there quotes what it answers
    # ("Re: ..."). The parent can be in any state - in the trash it's
    # said so; deleted for good, there's nothing to quote.
    reply_context = None
    if status == "pending" and c["parent_id"]:
        parent = comments.get(c["parent_id"])
        if parent:
            snippet = parent["body"][:80] + ("…" if len(parent["body"]) > 80 else "")
            note = " (comment since deleted)" if parent["trashed_at"] else ""
            reply_context = Div(
                "Replying to ", Strong(parent["author_name"]), note, f': "{snippet}"',
                cls="text-xs text-base-content/50 italic mt-0.5"
            )
        else:
            reply_context = Div(
                "Replying to a comment that's no longer available",
                cls="text-xs text-base-content/50 italic mt-0.5"
            )
    # comment body on its own line - the third stacked element, same
    # slot TagList fills on a Posts row
    body = P(c["body"], cls="my-2")

    reply_box = None
    if status == "trash":
        actions = RowActions(
            Form(
                Input(type="hidden", name="comment_id", value=c["id"]),
                IconAction(RESTORE_SVG, "Restore"),
                action="/admin/comments/restore", method="post", cls="contents"
            ),
            Form(
                Input(type="hidden", name="comment_id", value=c["id"]),
                IconAction(TRASH_SVG, "Delete forever", danger=True,
                           confirm="Permanently delete this comment? This can't be undone."),
                action="/admin/comments/delete-forever", method="post", cls="contents"
            ),
            id=f"comment-acts-{c['id']}"
        )
    else:
        # every action here is a join-item now - Pending and Approved
        # each always render at least two buttons grouped together, so
        # there's no longer a "standing alone" case that skips it
        delete_form = Form(
            Input(type="hidden", name="comment_id", value=c["id"]),
            # tab and post: after a delete, back to the same tab and filter
            Input(type="hidden", name="tab", value=status),
            Input(type="hidden", name="post", value=post),
            IconAction(TRASH_SVG, "Trash", danger=True,
                       confirm="Move this comment to trash? You can restore it from Trash."),
            action="/admin/comments/delete", method="post", cls="contents"
        )
        if status == "pending":
            actions = RowActions(
                Form(Input(type="hidden", name="comment_id", value=c["id"]),
                     # bare, not btn-primary - primary is reserved for a
                     # page's one most important action, and this repeats
                     # once per pending comment, so a colored version
                     # would multiply across the queue instead of
                     # standing out once
                     IconAction(CHECK_SVG, "Approve"),
                     action="/admin/comments/approve", method="post", cls="contents"),
                delete_form,
                id=f"comment-acts-{c['id']}"
            )
        else:
            # Reply, composed right here in a box under the comment
            # (ReplyBox) instead of linking off to the post page. Gated
            # on depth < MAX_REPLY_DEPTH, the cap the live page enforces
            # too - past that depth, only Trash is offered.
            can_reply = depth < MAX_REPLY_DEPTH
            actions = RowActions(ReplyButton(c["id"]) if can_reply else None, delete_form,
                                 id=f"comment-acts-{c['id']}")
            reply_box = ReplyBox(f"/post/{c['post_slug']}/reply", c["id"],
                                 redirect_to="/admin/comments?tab=approved") if can_reply else None

    # same right-alignment shape as Posts'/Media's own rows: the
    # growable content column (title, then meta, then body - stacked,
    # no card, no divider between them) and the actions column are
    # siblings in one flex row (justify-between pushes actions to the
    # row's right edge), not actions stacked underneath the content.
    return Li(
        Div(
            RowCheck("comments-bulk", "ids", c["id"], f"comment by {c['author_name']}", "mt-0.5"),
            Div(title_link, meta, reply_context, body, reply_box, cls="flex-1 min-w-0"),
            actions,
            cls="list-col-grow flex justify-between items-start gap-3"
        ),
        # REPLY_INDENT[depth] - the exact same per-depth indent the
        # live post page uses (routes/public.py's own literal-class-
        # list, imported rather than duplicated, not an f-string - same
        # Tailwind-scanner reason noted there), so a reply thread reads
        # the same way in both places
        cls=f"list-row {REPLY_INDENT[depth]} {TICK_ROW_CLS}", **TICK_ROW
    )



def MentionRow(m):
    """One webmention (webmention.py) - who, what kind, from where."""
    from urllib.parse import urlsplit
    kind = {"reply": "replied", "like": "liked", "repost": "reposted", "bookmark": "bookmarked"}.get(m["kind"],
                                                                                                 "mentioned")
    hidden = Input(type="hidden", name="mention_id", value=m["id"])
    actions = RowActions(
        Form(hidden, IconAction(CHECK_SVG, "Approve"),
             action="/admin/mentions/approve", method="post", cls="contents") if not m["approved"] else None,
        Form(hidden, IconAction(TRASH_SVG, "Delete", danger=True,
                                confirm="Delete this mention? This can't be undone."),
             action="/admin/mentions/delete", method="post", cls="contents"),
        id=f"mention-acts-{m['id']}")
    return Li(
        RowCheck("mentions-bulk", "ids", m["id"], f"mention from {m['author_name']}", "mt-0.5",
                 state="approved" if m["approved"] else "waiting"),
        Div(
            Div(A(m["author_name"], href=web_url(m["author_url"]) or web_url(m["source"]), target="_blank", rel="noopener",
                  cls="font-medium link link-hover"),
                Span(f" {kind} ", cls="text-base-content/60"),
                A(_post_title(m["post_slug"]), href=f"/post/{m['post_slug']}#mentions", cls="link link-hover"),
                cls="text-sm"),
            Div(A(urlsplit(m["source"]).hostname or m["source"], href=m["source"], target="_blank", rel="noopener",
                  cls="link link-hover"), " · ", m["received_at"][:10],
                Span("Waiting", cls="badge badge-xs badge-warning ml-2") if not m["approved"] else None,
                cls="text-xs text-base-content/50"),
            P(m["content"], cls="text-sm my-1") if m["content"] else None,
            cls="list-col-grow min-w-0"),
        actions, cls=f"list-row {TICK_ROW_CLS}", **TICK_ROW)


MENTION_STATES = [("", "All"), ("pending", "Waiting for approval"), ("approved", "Showing on posts")]


def mentions_page(q="", state="", sort="newest", page=1):
    from soloblog import webmention
    state = state if state in dict(MENTION_STATES) else ""
    per = rows_per_page(COMMENTS_PER_PAGE)
    rows = webmention.list_all(state, page, per, q, sort)
    matched = webmention.count(state, q)
    total_pages = max(1, -(-matched // per))
    tabs = Tabs(*[A(label, href=f"/admin/comments?tab={key}",
                   cls=f"tab tab-sm {'tab-active font-semibold' if key == 'mentions' else ''}")
                 for key, label in COMMENT_TABS], id="comment-tabs", cls=f"{TABS_CLS} mb-4")
    intro = None if webmention.receiving() else OffNotice(
        "Webmentions are off, so other sites' links to yours don't show here", "/admin/settings?tab=sharing")
    base = "/admin/comments?tab=mentions"
    toolbar = ListToolbar([
        SearchField(q, "Search mentions…", "/admin/comments",
                    {k: v for k, v in (("tab", "mentions"), ("state", state), ("sort", sort)) if v}),
        FilterSelect("Status", "state", MENTION_STATES, state, f"{base}&q={quote(q)}&sort={sort}&state="),
        FilterSelect("Sort", "sort", COMMENT_SORTS, sort, f"{base}&q={quote(q)}&state={state}&sort=")],
        filtered=bool(state or sort != "newest"))
    label = dict(MENTION_STATES)[state].lower() if state else ""
    return Layout(
        PageHeader("Comments"), tabs, intro, toolbar,
        ListHeader(list_summary(matched, "mention", q, label), clear=base if q or state else None,
                   form_id="mentions-bulk" if rows else None, action="/admin/mentions/bulk",
                   return_to=f"{base}&q={quote(q)}&state={state}&sort={sort}&page={page}", total=matched,
                   scope={"in_state": state, "in_q": q},
                   buttons=[BulkButton("Approve", "approve", for_states=("waiting",)),
                            BulkButton("Delete", "delete", danger=True,
                                       confirm="Delete the selected mentions? This can't be undone.",
                                       confirm_all="Delete all {n} mentions? This can't be undone.")]),
        Ul(*[MentionRow(m) for m in rows], cls="list") if rows else EmptyState(
            f"Nothing matches “{q}”." if q else "None of these yet." if state else "No mentions yet.", "🔗"),
        Pagination(min(page, total_pages), total_pages, f"{base}&q={quote(q)}&state={state}&sort={sort}",
                   labels=("« Prev", "Next »"), per_page=per, total=matched),
        settings=settings.get_all(), logged_in=True, pinned_tree=posts.list_pinned_tree(), admin_page=True,
        live=True
    )


@ar.post("/admin/mentions/bulk")
def bulk_mentions(session, action: str = "", ids: list[int] = None, return_to: str = "/admin/comments?tab=mentions",
                  all_matching: str = "", in_state: str = "", in_q: str = ""):
    from soloblog import webmention
    target = return_to if is_local_path(return_to) else "/admin/comments?tab=mentions"
    if all_matching == "1":
        # every page the search and Status match, rebuilt here
        state = in_state if in_state in dict(MENTION_STATES) else ""
        rows = webmention.list_all(state, 1, 10 ** 6, in_q)
        ids = [m["id"] for m in rows if action != "approve" or not m["approved"]]
    else:
        ids = [i for i in (ids or []) if i]
    do = {"approve": webmention.approve, "delete": webmention.delete}.get(action)
    if not ids or not do:
        return _toast_redirect(target, "Select some mentions first", "error")
    for mention_id in ids:
        do(mention_id)
    n = f"{len(ids)} mention{'s' if len(ids) != 1 else ''}"
    return _toast_redirect(target, f"Approved {n}" if action == "approve" else f"Deleted {n}")


@ar.post("/admin/mentions/approve")
def approve_mention(session, mention_id: int):
    from soloblog import webmention
    webmention.approve(mention_id)
    return _toast_redirect("/admin/comments?tab=mentions", "Approved")


@ar.post("/admin/mentions/delete")
def delete_mention(session, mention_id: int):
    from soloblog import webmention
    webmention.delete(mention_id)
    return _toast_redirect("/admin/comments?tab=mentions", "Deleted")


@ar.get("/admin/comments")
def comment_queue(session, tab: str = "pending", post: str = "", page: int = 1, q: str = "", sort: str = "newest",
                  state: str = ""):
    if tab not in dict(COMMENT_TABS):
        tab = "pending"
    sort = sort if sort in dict(COMMENT_SORTS) else "newest"
    q = q.strip()
    page = max(1, page)
    if tab == "mentions":
        return mentions_page(q, state, sort, page)

    pagination = None
    bulk_actions = None
    per = rows_per_page(COMMENTS_PER_PAGE)
    if tab == "trash":
        # trash isn't filtered by post - it's small and short-lived by
        # nature (things pass through on their way to either Restore or
        # Empty trash), same as Posts'/Media's own trash tabs, neither
        # of which offer a filter there either
        trash_items = comments.list_by_status("trash", page=page, per_page=per, q=q, sort=sort)
        total_trash = comments.count_by_status("trash")
        matched = comments.count_by_status("trash", q=q)
        total_pages = max(1, -(-matched // per))
        pagination = Pagination(page, total_pages, f"/admin/comments?tab=trash&q={quote(q)}&sort={sort}",
                                labels=("« Prev", "Next »"), per_page=per, total=matched)
        bulk_actions = Form(
            Button(TRASH_SVG, Span("Empty trash", cls="ml-1"), type="button", cls="btn btn-sm text-error",
                   data_confirm="Permanently delete everything in trash? This can't be undone."),
            action="/admin/comments/empty-trash", method="post"
        ) if total_trash else None
        body = (Ul(*[CommentRow(c, "trash") for c in trash_items], cls="list") if trash_items
                else EmptyState(f"Nothing matches “{q}”." if q else "Trash is empty.", "🗑️"))
    elif tab == "approved" and q:
        # a search finds comments, not threads: each match on its own
        rows = comments.list_by_status("approved", post, page, per, q=q, sort=sort)
        matched = comments.count_by_status("approved", post, q=q)
        total_pages = max(1, -(-matched // per))
        pagination = Pagination(page, total_pages, f"/admin/comments?tab=approved&post={quote(post)}&q={quote(q)}"
                                f"&sort={sort}", labels=("« Prev", "Next »"), per_page=per, total=matched)
        body = (Ul(*[CommentRow(c, "approved", post=post) for c in rows], cls="list") if rows
                else EmptyState(f"Nothing matches “{q}”.", "💬"))
    elif tab == "approved":
        # In threads, paged by top-level comment, so a reply is always on
        # its parent's page. The threads are built as on the post page
        # (build_thread_tree), with "deleted" placeholders for parents in
        # the trash (list_approved_with_deleted_parents).
        all_approved = comments.list_approved_with_deleted_parents(post)
        top_level_all, children_by_parent = comments.build_thread_tree(all_approved)
        # newest top-level comment first, matching Pending's/Trash's
        # own ordering - build_thread_tree's underlying order is
        # chronological (right for reading a thread top-to-bottom, on
        # the live page), so only the top-level ordering gets flipped
        # here; each thread's own replies stay chronological under it
        top_level_all.sort(key=lambda c: c["created_at"], reverse=sort != "oldest")

        total_top = len(top_level_all)
        total_pages = max(1, -(-total_top // per))
        base_path = f"/admin/comments?tab=approved&post={quote(post)}&sort={sort}"
        pagination = Pagination(page, total_pages, base_path, labels=("« Prev", "Next »"), per_page=per,
                                total=total_top)
        page_slice = top_level_all[(page - 1) * per: page * per]

        items = []

        def add_thread(cm, depth):
            items.append(CommentRow(cm, "approved", depth=depth, post=post))
            for child in children_by_parent.get(cm["id"], []):
                add_thread(child, depth + 1)

        for cm in page_slice:
            add_thread(cm, 0)

        body = Ul(*items, cls="list") if items else EmptyState("No approved comments yet.", "💬")
    else:
        rows = comments.list_by_status("pending", post, page, per, q=q, sort=sort)
        total = comments.count_by_status("pending", post, q=q)
        total_pages = max(1, -(-total // per))
        base_path = f"/admin/comments?tab=pending&post={quote(post)}&q={quote(q)}&sort={sort}"
        pagination = Pagination(page, total_pages, base_path, labels=("« Prev", "Next »"), per_page=per, total=total)
        body = (Ul(*[CommentRow(c, "pending", post=post) for c in rows], cls="list") if rows
                else EmptyState(f"Nothing matches “{q}”." if q else "Nothing waiting on you.", "✅"))

    tabs = Tabs(
        *[A(label, href=f"/admin/comments?tab={key}&post={quote(post)}",
            cls=f"tab tab-sm {'tab-active font-semibold' if key == tab else ''}")
          for key, label in COMMENT_TABS],
        id="comment-tabs", cls=f"{TABS_CLS} mb-4"
    )

    # filters live in their own row below the tabs, same split Posts
    # uses (the tabs pick which subset, this refines within it) - not
    # offered on Trash, matching the note above. Scoped to the active
    # tab - a post whose only comments are pending shouldn't be a
    # filter option while looking at Approved, where it'd just lead to
    # "No approved comments yet" with no explanation why it was there.
    # the 30 most recently commented on, when there are more
    commented_slugs = comments.list_commented_slugs(tab)
    post_filter = FilterSelect("Post", "post", [("", "All")] + top_options(
                                   [(slug, _post_title(slug)) for slug in commented_slugs], post),
                               post, f"/admin/comments?tab={tab}&q={quote(q)}&sort={sort}&post=") \
        if tab != "trash" and commented_slugs else None
    search_box = SearchField(q, "Search comments…", "/admin/comments",
                             {k: v for k, v in (("tab", tab), ("post", post), ("sort", sort)) if v})
    sort_picker = FilterSelect("Sort", "sort", COMMENT_SORTS, sort,
                               f"/admin/comments?tab={tab}&post={quote(post)}&q={quote(q)}&sort=")

    count = comments.count_by_status(tab, "" if tab == "trash" else post, q=q)
    buttons = {"pending": [BulkButton("Approve", "approve"), BulkButton("Move to trash", "trash", danger=True)],
               "approved": [BulkButton("Move to trash", "trash", danger=True)],
               "trash": [BulkButton("Restore", "restore"),
                         BulkButton("Delete forever", "delete", danger=True,
                                    confirm="Permanently delete the selected comments? This can't be undone.",
                                    confirm_all="Permanently delete all {n} comments in the trash? This can't be "
                                                "undone.")]}[tab]
    header = ListHeader(
        list_summary(count, "comment", q, f"on “{_post_title(post)}”" if post else ""),
        clear=f"/admin/comments?tab={tab}" if post or q else None,
        form_id="comments-bulk" if getattr(body, "tag", "") == "ul" else None, action="/admin/comments/bulk",
        return_to=f"/admin/comments?tab={tab}&post={quote(post)}&q={quote(q)}&sort={sort}&page={page}",
        total=count, scope={"in_tab": tab, "in_post": "" if tab == "trash" else post, "in_q": q},
        buttons=buttons
    )

    return Layout(
        PageHeader("Comments"),
        tabs,
        ListToolbar([search_box, post_filter, sort_picker], bulk_actions, filtered=bool(post or sort != "newest")),
        header,
        body,
        pagination,
        settings=settings.get_all(), logged_in=True, pinned_tree=posts.list_pinned_tree(), admin_page=True, live=True
    )


@ar.post("/admin/comments/approve")
def approve(session, comment_id: int):
    comments.approve(comment_id)
    replymail.send_for([comment_id])
    return _toast_redirect("/admin/comments", "Approved")


# what each tab's bulk bar offers - "all" is only ever done within one tab
TAB_ACTIONS = {"pending": ("approve", "trash"), "approved": ("trash",), "trash": ("restore", "delete")}


@ar.post("/admin/comments/bulk")
def bulk(session, action: str = "", ids: list[int] = None, return_to: str = "/admin/comments",
         all_matching: str = "", in_tab: str = "", in_post: str = "", in_q: str = ""):
    target = return_to if is_local_path(return_to) else "/admin/comments"
    if all_matching == "1":
        if action not in TAB_ACTIONS.get(in_tab, ()):
            return _toast_redirect(target, "Select some comments and choose what to do", "error")
        ids = [c["id"] for c in comments.list_by_status(in_tab, "" if in_tab == "trash" else in_post, 1, 10 ** 6,
                                                         q=in_q)]
    else:
        ids = [i for i in (ids or []) if i]
    do = {"approve": comments.approve, "trash": comments.move_to_trash, "restore": comments.restore_from_trash,
          "delete": comments.delete_permanently}.get(action)
    if not ids or not do:
        return _toast_redirect(target, "Select some comments and choose what to do", "error")
    for comment_id in ids:
        do(comment_id)
    if action == "approve":
        replymail.send_for(ids)
    n = f"{len(ids)} comment{'s' if len(ids) != 1 else ''}"
    said = {"approve": f"Approved {n}", "trash": f"Moved {n} to trash", "restore": f"Restored {n}",
            "delete": f"Permanently deleted {n}"}[action]
    return _toast_redirect(target, said)


@ar.post("/admin/comments/delete")
def delete(session, comment_id: int, slug: str = None, tab: str = "", post: str = ""):
    comments.move_to_trash(comment_id)
    # back where it was deleted from: the post page (slug), or the tab
    # and filter of the comments list (CommentRow's hidden tab and post)
    if slug:
        target = f"/post/{slug}#comments"
    elif tab:
        target = f"/admin/comments?tab={tab}&post={quote(post)}"
    else:
        target = "/admin/comments"
    return _toast_redirect(target, "Moved to trash",
                           undo=undo_url("/admin/comments/restore", comment_id=comment_id, return_to=target))


@ar.post("/admin/comments/restore")
def restore(session, comment_id: int, return_to: str = ""):
    comments.restore_from_trash(comment_id)
    # return_to - an Undo lands back where the comment was trashed from
    target = return_to if is_local_path(return_to) else "/admin/comments?tab=trash"
    return _toast_redirect(target, "Restored")


@ar.post("/admin/comments/empty-trash")
def empty_trash(session):
    count = comments.empty_trash()
    return _toast_redirect("/admin/comments?tab=trash", f"Permanently deleted {count} comment(s)")


@ar.post("/admin/comments/delete-forever")
def delete_forever(session, comment_id: int):
    comments.delete_permanently(comment_id)
    return _toast_redirect("/admin/comments?tab=trash", "Permanently deleted")
