from fasthtml.common import *

from soloblog import comments
from soloblog import config
from soloblog import linkcheck
from soloblog import posts
from soloblog import settings
from soloblog.db import get_db
from soloblog.render import format_date
from soloblog.ui import Layout, PageHeader, ListToolbar, FilterSelect, IconAction, SYNC_SVG, DOWNLOAD_SVG, SCROLLS_X
from soloblog.routes.editor import _when

ar = APIRouter()



def StatTile(title, value, desc=None):
    return Div(
        Div(title, cls="stat-title"),
        Div(f"{value:,}", cls="stat-value text-2xl tabular-nums"),
        Div(desc, cls="stat-desc") if desc else None,
        cls="stat"
    )


def _short(day: str) -> str:
    """A day without its year, in the order the site writes dates:
    "Sep 24" or "24 Sep"."""
    from calendar import month_abbr
    month, number = month_abbr[int(day[5:7])], int(day[8:10])
    return f"{number} {month}" if format_date(day)[:1].isdigit() else f"{month} {number}"


def _bucket_label(b, unit, axis=False) -> str:
    """How one bar is named: a day, the week it starts, or a month."""
    if unit == "month":
        from calendar import month_abbr
        month = month_abbr[int(b["start"][5:7])]
        return month if axis else f"{month} {b['start'][:4]}"
    if unit == "week":
        return _short(b["start"]) if axis else f"Week of {_short(b['start'])}"
    return _short(b["start"]) if axis else format_date(b["start"])


def ViewsChart(series, range_key):
    """One series, so no legend - the heading names it. Bars stand on
    a shared baseline with 2px gaps and rounded tops; each whole column
    (not just its bar) is the hover target, so a zero bar still shows
    its tooltip. Only the peak and the two ends are labelled - the
    table underneath has every number. Longer ranges use weeks or
    months as bars, so there are never more than about 30."""
    label, _, unit = posts.VIEW_RANGES[range_key]
    peak = max((b["views"] for b in series), default=0)
    total = sum(b["views"] for b in series)
    bars = [
        Div(
            Div(cls="w-full bg-primary rounded-t-[4px]",
                style=f"height: {max(b['views'] / peak * 100, 2) if b['views'] and peak else 0:.1f}%"),
            data_tip=f"{_bucket_label(b, unit)}: {b['views']:,} view{'s' if b['views'] != 1 else ''}",
            role="img", aria_label=f"{_bucket_label(b, unit)}: {b['views']} views",
            cls="tooltip flex-1 h-full flex items-end hover:bg-base-200 rounded-t-[4px]"
        )
        for b in series
    ]
    per = {"day": "per day", "week": "per week", "month": "per month"}[unit]
    return Div(
        Div(
            Div(
                H2(f"Views, {label.lower()}", Span(f" · {per}", cls="font-normal text-base-content/50"),
                   cls="font-semibold text-sm"),
                Span(f"{total:,} total", cls="text-xs text-base-content/60"),
                cls="flex items-baseline justify-between gap-2"
            ),
            Div(
                Span(f"{peak:,}", cls="absolute -top-5 left-0 text-xs text-base-content/50 tabular-nums") if peak else None,
                Div(*bars, cls="flex items-end gap-[2px] h-32"),
                cls="relative mt-6 border-b-[length:var(--border)] border-base-300"
            ),
            Div(Span(_bucket_label(series[0], unit, axis=True)), Span(_bucket_label(series[-1], unit, axis=True)),
                cls="flex justify-between text-xs text-base-content/50 mt-1"),
            Details(
                Summary("Show as a table", cls="text-xs link link-hover w-fit py-1"),
                Table(
                    Thead(Tr(Th({"day": "Day", "week": "Week", "month": "Month"}[unit]), Th("Views", cls="text-right"))),
                    Tbody(*[Tr(Td(_bucket_label(b, unit)), Td(f"{b['views']:,}", cls="text-right tabular-nums"))
                            for b in reversed(series)]),
                    cls="table table-xs mt-2"
                ),
                cls="mt-3"
            ),
            cls="card-body p-4"
        ),
        cls="card card-border bg-base-100"
    )


def SourcesCard(since_day, range_label, range_key="30d"):
    """Where readers came from over the range - sites by name, each with
    a bar sized against the biggest."""
    from soloblog import sources
    rows = sources.top(since_day)
    top = max((n for _, n in rows), default=0)
    body = Table(
        Thead(Tr(Th("Source"), Th(range_label.replace("Last ", "").capitalize(), cls="text-right"))),
        Tbody(*[Tr(
            Td(Div(Div(cls="absolute inset-y-0 left-0 bg-primary/10 rounded-field", style=f"width:{n / top * 100:.1f}%"),
                   Span(src, cls="relative"), cls="relative px-2 py-0.5")),
            Td(f"{n:,}", cls="text-right tabular-nums")) for src, n in rows]),
        cls="table table-sm"
    ) if rows else P("None yet. Visits from other sites, search engines and social media show here, by name - "
                     "never the page they came from or who they are.", cls="text-sm text-base-content/60")
    export = IconAction(DOWNLOAD_SVG, "Export sources", href=f"/admin/stats/export?kind=sources&range={range_key}",
                        menu_label=False, tip="tooltip-left") if rows else None
    return Div(Div(Div(H2("Top sources", cls="font-semibold text-sm"), export,
                       cls="flex items-center justify-between gap-2 mb-2"),
                   Div(body, cls="overflow-x-auto"), cls="card-body p-4"), cls="card card-border bg-base-100")


def TopPosts(recent, range_label):
    rows = get_db().execute(
        "SELECT slug, title, views, likes FROM posts WHERE published=1 ORDER BY views DESC LIMIT 50"
    ).fetchall()
    rows = sorted(rows, key=lambda r: (recent.get(r["slug"], 0), r["views"]), reverse=True)[:10]
    if not rows:
        return None
    # likes, or the emoji reactions' total when those are on instead
    emoji = settings.get("reactions_style") == "emoji"
    reacted = dict(get_db().execute("SELECT post_slug, SUM(count) FROM post_reactions GROUP BY post_slug").fetchall()) \
        if emoji else {}
    return Div(
        Div(
            H2("Top posts", cls="font-semibold text-sm mb-2"),
            Div(Table(
                Thead(Tr(Th("Post"), Th(range_label.replace("Last ", "").capitalize(), cls="text-right"), Th("All time", cls="text-right"),
                         Th("Reactions" if emoji else "Likes", cls="text-right"), Th("Comments", cls="text-right"))),
                Tbody(*[Tr(
                    # a title keeps room to be read on a phone; the numbers swipe along
                    Td(A(r["title"], href=f"/post/{r['slug']}", cls="link link-hover"), cls="min-w-36"),
                    Td(f"{recent.get(r['slug'], 0):,}", cls="text-right tabular-nums"),
                    Td(f"{r['views']:,}", cls="text-right tabular-nums"),
                    Td(f"{(reacted.get(r['slug'], 0) if emoji else r['likes']):,}", cls="text-right tabular-nums"),
                    Td(f"{comments.count_by_status('approved', r['slug']):,}", cls="text-right tabular-nums"),
                ) for r in rows]),
                cls="table table-sm"
            ), data_scroll_x=True, cls=f"overflow-x-auto {SCROLLS_X}"),
            cls="card-body p-4"
        ),
        cls="card card-border bg-base-100"
    )


def LinksCard():
    """Broken links, from the last check. While a check runs, this card
    reloads itself every two seconds until it's done."""
    st = linkcheck.state()
    if st["running"]:
        body = P(Span(cls="loading loading-spinner loading-xs mr-2"), "Checking every link in your posts...",
                 cls="text-sm text-base-content/70 flex items-center")
        poll = dict(hx_get="/admin/stats/links", hx_trigger="every 2s", hx_swap="outerHTML")
    elif not st["checked_at"]:
        body = P("Finds links in your posts that go nowhere - deleted posts, missing images, and outside "
                 "pages that have moved or vanished.", cls="text-sm text-base-content/70")
        poll = {}
    else:
        summary = (f"All {st['total']} links work." if not st["broken"]
                   else f"{len(st['broken'])} of {st['total']} links are broken.")
        rows = [Tr(
            Td(*[A(title, href=f"/admin/edit/{slug}", cls="link link-hover block") for slug, title in b["posts"][:3]],
               Span(f"and {len(b['posts']) - 3} more", cls="text-xs text-base-content/50")
               if len(b["posts"]) > 3 else None, cls="min-w-36"),
            Td(A(b["url"], href=b["url"], target="_blank", rel="noopener", cls="link link-hover break-all text-xs")),
            Td(b["reason"], cls="text-error text-xs whitespace-nowrap"),
        ) for b in st["broken"]]
        body = Div(
            P(summary, " ", Span(f"Checked {_when(st['checked_at'])}.", cls="text-base-content/50"),
              cls="text-sm " + ("text-success" if not st["broken"] else "text-base-content/70")),
            Div(Table(Thead(Tr(Th("Post"), Th("Link"), Th("Problem"))), Tbody(*rows), cls="table table-sm mt-2"),
                data_scroll_x=True, cls=f"overflow-x-auto {SCROLLS_X}") if rows else None,
        )
        poll = {}
    return Div(
        Div(
            Div(
                H2("Links", cls="font-semibold text-sm"),
                Form(Button(SYNC_SVG, Span("Check links", cls="ml-1"), type="submit", cls="btn btn-sm",
                            disabled=st["running"]),
                     hx_post="/admin/stats/links", hx_target="#links-card", hx_swap="outerHTML"),
                cls="flex items-center justify-between gap-2 mb-2"
            ),
            body,
            cls="card-body p-4"
        ),
        id="links-card", cls="card card-border bg-base-100", **poll
    )


@ar.get("/admin/stats/links")
def links_card(session):
    return LinksCard()


@ar.post("/admin/stats/links")
def start_link_check(session, request):
    linkcheck.start()
    return LinksCard()


@ar.get("/admin/stats/export")
def export_stats(session, range: str = "30d", kind: str = "views"):
    """Views per post per day - or, kind=sources, per source per day - over
    the range the page shows, for a spreadsheet."""
    from soloblog.backup import csv_download
    range_key = range if range in posts.VIEW_RANGES else "30d"
    start = posts.views_by_period(range_key)[0]["start"]
    if kind == "sources":
        rows = get_db().execute("SELECT day, source, views FROM sources_daily WHERE day >= ? ORDER BY day, views DESC",
                                (start,)).fetchall()
        return csv_download(f"sources-{range_key}.csv", ["date", "source", "views"], rows)
    rows = get_db().execute(
        "SELECT v.day, COALESCE(p.title, v.slug), v.slug, v.views FROM post_views_daily v "
        "LEFT JOIN posts p ON p.slug = v.slug WHERE v.day >= ? ORDER BY v.day, v.views DESC", (start,)).fetchall()
    return csv_download(f"views-{range_key}.csv", ["date", "title", "address", "views"],
                        [(day, title, config.BASE_URL + posts.url_for_slug(slug), n) for day, title, slug, n in rows])


@ar.get("/admin/stats")
def stats_page(session, range: str = "30d"):
    range_key = range if range in posts.VIEW_RANGES else "30d"
    range_label = posts.VIEW_RANGES[range_key][0]
    series = posts.views_by_period(range_key)
    recent = posts.views_since(series[0]["start"])
    totals = get_db().execute("SELECT COALESCE(SUM(views), 0) AS views, COALESCE(SUM(likes), 0) AS likes "
                              "FROM posts").fetchone()
    pending = comments.count_pending()
    return Layout(
        PageHeader("Stats", A(DOWNLOAD_SVG, Span("Export", cls="ml-1 hidden sm:inline"),
                              href=f"/admin/stats/export?range={range_key}", aria_label="Export views", data_tip="Export",
                              cls="btn btn-sm tooltip tooltip-bottom sm:before:hidden sm:after:hidden")),
        # the same filter row and select as the Posts and Comments pages
        ListToolbar([FilterSelect("Range", "range", [(key, label) for key, (label, _, _) in posts.VIEW_RANGES.items()],
                                  range_key, "/admin/stats?range=")]),
        Div(
            StatTile("Views", sum(b["views"] for b in series), range_label.lower()),
            StatTile("All-time views", totals["views"]),
            StatTile("Reactions", get_db().execute("SELECT COALESCE(SUM(count), 0) FROM post_reactions").fetchone()[0])
            if settings.get("reactions_style") == "emoji" else StatTile("Likes", totals["likes"]),
            StatTile("Comments", comments.count_by_status("approved"),
                     f"{pending} waiting for approval" if pending else None),
            # two by two on a phone, without the dividers - they'd run
            # down the card's edge on the second row
            cls="stats max-sm:grid-cols-2 max-sm:grid-flow-row max-sm:[&>.stat]:border-0 w-full bg-base-100 "
                "border-[length:var(--border)] border-base-300 mb-3"
        ),
        Div(ViewsChart(series, range_key), TopPosts(recent, range_label), SourcesCard(series[0]["start"], range_label, range_key),
            LinksCard(), cls="flex flex-col gap-3"),
        P("Your own visits while logged in aren't counted. Views are counted per day from the version that "
          "added this page; anything earlier only shows in all-time views.", cls="text-xs text-base-content/50 mt-3"),
        settings=settings.get_all(), logged_in=True, pinned_tree=posts.list_pinned_tree(), admin_page=True
    )
