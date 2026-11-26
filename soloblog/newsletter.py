import json
import re
import secrets
import threading
import time
from datetime import timedelta
from soloblog.tz import utcnow

from fasthtml.common import A, Button, Div, Form, H1, H3, Input, Label, P, Span

from soloblog import captcha
from soloblog import config
from soloblog import i18n
from soloblog.db import get_db

# Readers subscribe by email (Settings > Visitors > Newsletter). Soloblog's
# own newsletter confirms each address first, then emails every new post
# through the site's email setup - the publishing queue sends it once, the
# same way it announces posts to the fediverse. Or the subscribe box signs
# readers up to Buttondown, Kit, Mailchimp or Substack instead.

EMAIL_RE = re.compile(r"^[^@\s<>\"]+@[^@\s<>\"]+\.[^@\s<>\"]+$")

# name: (label, what the id field is, its pattern, form address, email field's name)
SERVICES = {
    "buttondown": ("Buttondown", "Username", re.compile(r"^[\w-]{1,100}$"),
                   "https://buttondown.com/api/emails/embed-subscribe/{}", "email"),
    "kit": ("Kit (ConvertKit)", "Form ID", re.compile(r"^\d{1,20}$"),
            "https://app.kit.com/forms/{}/subscriptions", "email_address"),
    "mailchimp": ("Mailchimp", "Form action URL",
                  re.compile(r"^https://[\w.-]+\.list-manage\.com/subscribe/post\?[\w=&;%.-]+$"), "{}", "EMAIL"),
    "substack": ("Substack", "Publication", re.compile(r"^[a-z0-9-]{1,100}$"),
                 "https://{}.substack.com/api/v1/free?nojs=true", "email"),
}


def mode(s) -> str:
    """"builtin", one of SERVICES, or "" - off, including Soloblog's own
    when email isn't set up (the confirm emails couldn't go out)."""
    m = s.get("newsletter_mode") or ""
    if m == "builtin":
        return m if s.get("email_provider") in ("smtp", "api") else ""
    if m in SERVICES:
        return m if SERVICES[m][2].match(s.get(f"newsletter_{m}") or "") else ""
    return ""


def sending(s) -> bool:
    """New posts go out by themselves, each as it goes live - publishing.py's
    newsletter channel."""
    return mode(s) == "builtin" and s.get("newsletter_auto") == "1" and not digest(s)


def digest(s) -> str:
    """"week" or "month" when new posts go out together, in one email."""
    on = mode(s) == "builtin" and s.get("newsletter_auto") == "1"
    return s.get("newsletter_digest") if on and s.get("newsletter_digest") in ("week", "month") else ""


# ---- which posts have gone out: published_log's newsletter rows. A post
# kept out of the newsletter (Post settings) has SKIP for its version.

SKIP = "skip"


def _logged(slug):
    row = get_db().execute("SELECT content_hash FROM published_log WHERE slug=? AND channel='newsletter'",
                           (slug,)).fetchone()
    return row["content_hash"] if row else None


def skipped(slug) -> bool:
    return _logged(slug) == SKIP


def emailed(slug) -> bool:
    return _logged(slug) not in (None, SKIP)


def set_skipped(slug, skip: bool):
    """Post settings > Email it to subscribers - only before it's gone out."""
    db = get_db()
    if skip and not emailed(slug):
        db.execute("INSERT INTO published_log (slug, channel, content_hash, done_at) VALUES (?, 'newsletter', ?, ?) "
                   "ON CONFLICT(slug, channel) DO UPDATE SET content_hash=excluded.content_hash",
                   (slug, SKIP, utcnow().isoformat(timespec="seconds")))
    elif not skip:
        db.execute("DELETE FROM published_log WHERE slug=? AND channel='newsletter' AND content_hash=?", (slug, SKIP))
    db.commit()


def _period(now_local, how) -> str:
    return f"{now_local:%G-W%V}" if how == "week" else f"{now_local:%Y-%m}"


def digest_due(s, now_local) -> bool:
    """Mondays from 9 in the morning (a weekly one) or the 1st (a monthly
    one), in the site's time zone - once for each week or month."""
    how = digest(s)
    if not how or now_local.hour < 9 or (now_local.weekday() if how == "week" else now_local.day - 1):
        return False
    return s.get("newsletter_digest_last") != _period(now_local, how)


def waiting():
    """Live posts not emailed yet, nor kept out - oldest first."""
    from soloblog import posts
    rows = [r for r in posts.list_all_published() if not posts.is_page(r) and _logged(r["slug"]) is None]
    return sorted(rows, key=lambda r: r["created_at"])


def send_digest(s, now_local) -> int:
    """This week's or month's posts in one email to every subscriber - or
    nothing, when there were none. Returns how many emails went out."""
    from soloblog import publishing, settings
    rows = waiting()
    settings.set_many({"newsletter_digest_last": _period(now_local, digest(s))})
    if not rows:
        return 0
    db = get_db()
    now = utcnow().isoformat(timespec="seconds")
    for row in rows:
        db.execute("INSERT INTO published_log (slug, channel, content_hash, done_at) VALUES (?, 'newsletter', ?, ?) "
                   "ON CONFLICT(slug, channel) DO UPDATE SET content_hash=excluded.content_hash, done_at=excluded.done_at",
                   (row["slug"], publishing._hash(row), now))
    db.commit()
    return send_posts(rows, s)


# ---- subscribers

def subscribe(email: str):
    """A token to confirm with, or None if the address is already
    subscribed (nothing to send)."""
    email = email.strip()[:200]
    db = get_db()
    row = db.execute("SELECT * FROM subscribers WHERE email=?", (email,)).fetchone()
    now = utcnow().isoformat(timespec="seconds")
    if row and row["confirmed_at"] and not row["unsubscribed_at"]:
        return None
    token = secrets.token_urlsafe(24)
    if row:
        db.execute("UPDATE subscribers SET token=?, confirmed_at=NULL, unsubscribed_at=NULL, created_at=? WHERE id=?",
                   (token, now, row["id"]))
    else:
        db.execute("INSERT INTO subscribers (email, token, created_at) VALUES (?, ?, ?)", (email, token, now))
    db.commit()
    return token


def confirm(token: str) -> bool:
    db = get_db()
    row = db.execute("SELECT * FROM subscribers WHERE token=?", (token,)).fetchone()
    if not row or row["unsubscribed_at"]:
        return False
    if not row["confirmed_at"]:
        db.execute("UPDATE subscribers SET confirmed_at=? WHERE id=?",
                   (utcnow().isoformat(timespec="seconds"), row["id"]))
        db.commit()
    # with the members area on, a subscriber is a free member too
    from soloblog import members
    if members.enabled():
        members.add(row["email"])
    return True


def unsubscribe(token: str) -> bool:
    db = get_db()
    cur = db.execute("UPDATE subscribers SET unsubscribed_at=? WHERE token=? AND unsubscribed_at IS NULL",
                     (utcnow().isoformat(timespec="seconds"), token))
    db.commit()
    return cur.rowcount > 0 or bool(db.execute("SELECT 1 FROM subscribers WHERE token=?", (token,)).fetchone())


def subscribe_confirmed(email: str):
    """For a member, whose address the sign-in link has already proved -
    subscribed straight away, no second email to confirm."""
    db = get_db()
    now = utcnow().isoformat(timespec="seconds")
    row = db.execute("SELECT * FROM subscribers WHERE email=?", (email,)).fetchone()
    if row:
        db.execute("UPDATE subscribers SET confirmed_at=COALESCE(confirmed_at, ?), unsubscribed_at=NULL WHERE id=?",
                   (now, row["id"]))
    else:
        db.execute("INSERT INTO subscribers (email, token, created_at, confirmed_at) VALUES (?, ?, ?, ?)",
                   (email, secrets.token_urlsafe(24), now, now))
    db.commit()


def unsubscribe_email(email: str):
    db = get_db()
    db.execute("UPDATE subscribers SET unsubscribed_at=? WHERE email=? AND unsubscribed_at IS NULL",
               (utcnow().isoformat(timespec="seconds"), email))
    db.commit()


def is_subscribed(email: str) -> bool:
    return bool(get_db().execute("SELECT 1 FROM subscribers WHERE email=? AND confirmed_at IS NOT NULL "
                                 "AND unsubscribed_at IS NULL", (email,)).fetchone())


def remove(subscriber_id: int):
    get_db().execute("DELETE FROM subscribers WHERE id=?", (subscriber_id,))
    get_db().commit()


def import_csv(text: str) -> tuple:
    """Addresses from another service's export (Substack, Buttondown,
    Mailchimp, Kit...): the column called email, or else the first one
    with an @ in it. They signed up there, so they come in confirmed.
    Returns (added, skipped)."""
    import csv
    import io
    rows = list(csv.reader(io.StringIO(text.lstrip("\ufeff"))))
    if not rows:
        return 0, 0
    header = [h.strip().lower() for h in rows[0]]
    col = next((i for i, h in enumerate(header) if h in ("email", "email address", "e-mail")), None)
    body = rows[1:] if col is not None else rows
    if col is None:
        col = next((i for i, v in enumerate(rows[0]) if "@" in v), 0)
    db = get_db()
    now = utcnow().isoformat(timespec="seconds")
    added = skipped = 0
    for row in body:
        email = row[col].strip()[:200] if len(row) > col else ""
        if not EMAIL_RE.match(email) or db.execute("SELECT 1 FROM subscribers WHERE email=?", (email,)).fetchone():
            skipped += 1
            continue
        db.execute("INSERT INTO subscribers (email, token, created_at, confirmed_at) VALUES (?, ?, ?, ?)",
                   (email, secrets.token_urlsafe(24), now, now))
        added += 1
    db.commit()
    from soloblog import members
    if members.enabled():
        members.sync_subscribers()
    return added, skipped


def confirmed():
    return get_db().execute("SELECT * FROM subscribers WHERE confirmed_at IS NOT NULL AND unsubscribed_at IS NULL "
                            "ORDER BY confirmed_at DESC").fetchall()


def list_all():
    return get_db().execute("SELECT * FROM subscribers ORDER BY created_at DESC").fetchall()


def by_ids(ids) -> list:
    """The subscribers ticked in Admin > Newsletter, newest first."""
    ids = [int(i) for i in ids][:100_000]
    if not ids:
        return []
    marks = ",".join("?" * len(ids))
    return get_db().execute(f"SELECT * FROM subscribers WHERE id IN ({marks}) ORDER BY created_at DESC",  # noqa: S608 - fixed lists, ids bound
                            ids).fetchall()


STATES = {"confirmed": "confirmed_at IS NOT NULL AND unsubscribed_at IS NULL",
          "unconfirmed": "confirmed_at IS NULL AND unsubscribed_at IS NULL",
          "unsubscribed": "unsubscribed_at IS NOT NULL"}
SORTS = {"newest": "created_at DESC", "oldest": "created_at ASC", "email": "email"}


def list_page(page, per_page, q="", state="", sort="newest"):
    """One page of Admin > Subscribers, and how many match in all: a part
    of an email address, and confirmed, not yet or unsubscribed."""
    where = "email LIKE ?" + (f" AND {STATES[state]}" if state in STATES else "")
    like = f"%{q.strip()}%"
    db = get_db()
    total = db.execute(f"SELECT COUNT(*) FROM subscribers WHERE {where}", (like,)).fetchone()[0]  # noqa: S608 - fixed lists, ids bound
    rows = db.execute(f"SELECT * FROM subscribers WHERE {where} ORDER BY {SORTS.get(sort, SORTS['newest'])} "  # noqa: S608 - fixed lists, ids bound
                      "LIMIT ? OFFSET ?", (like, per_page, (page - 1) * per_page)).fetchall()
    return rows, total


def count() -> int:
    return get_db().execute("SELECT COUNT(*) FROM subscribers WHERE confirmed_at IS NOT NULL "
                            "AND unsubscribed_at IS NULL").fetchone()[0]


# ---- emails

def unsubscribe_url(token: str) -> str:
    return f"{config.BASE_URL}/newsletter/unsubscribe/{token}"


def send_confirm(email: str, token: str, s):
    from soloblog import i18n, mail
    site = s["site_title"]
    with i18n.in_site_language():
        subject = i18n.t("Confirm your subscription to {site}", site=site)
        thanks = i18n.t("Thanks for subscribing to {site}.", site=site)
        confirm = i18n.t("Confirm your email address to start getting new posts:")
        ignore = i18n.t("If you didn't subscribe, you can ignore this email. Nothing more will be sent.")
    body = f"{thanks}\n\n{confirm}\n{config.BASE_URL}/newsletter/confirm/{token}\n\n{ignore}\n"
    mail.send_email(email, subject, body)


def _post_parts(row, s, can_read=True):
    """(markdown text, whether it's the whole post) of what a post's email says."""
    from soloblog import i18n
    from soloblog import posts
    from soloblog.render import excerpt, render_post, without_section_lines_text
    body = posts.load_post_body(row["slug"]) if can_read else posts.public_part(posts.load_post_body(row["slug"]),
                                                                                 row["visibility"])
    if posts.is_protected(row):
        text = row["summary"]
    elif s.get("newsletter_full") == "1":
        text = without_section_lines_text(body).strip()
    else:
        text = row["summary"] or excerpt(render_post(body)[0])
    if not can_read:
        with i18n.in_site_language():
            text = (f"{text}\n\n" if text else "") + (i18n.t("This post is for paid members.")
                                                        if posts.clean_visibility(row["visibility"]) == "paid"
                                                        else i18n.t("This post is for members."))
    return text


def _footer(s, token):
    from soloblog import i18n
    with i18n.in_site_language():
        return (i18n.t("You're getting this because you subscribed to {site}.", site=s["site_title"]),
                i18n.t("Unsubscribe:"), unsubscribe_url(token))


def post_email(row, s, token: str, can_read: bool = True) -> str:
    """can_read - whether this subscriber may read all of a members post;
    if not, they get its free preview and a line to read it on the site."""
    from soloblog import i18n
    from soloblog import posts
    url = config.BASE_URL + posts.url_for(row)
    text = _post_parts(row, s, can_read)
    with i18n.in_site_language():
        read = i18n.t("Read it on {site}:", site=s["site_title"])
    why, stop, link = _footer(s, token)
    return f"{row['title']}\n\n{text}\n\n{read}\n{url}\n\n--\n{why}\n{stop} {link}\n"


def post_email_html(row, s, token: str, can_read: bool = True) -> str:
    """The same email, designed: the post as it reads on the site, plainly
    styled so it looks right in any email app."""
    from html import escape
    from soloblog import i18n
    from soloblog import posts
    from soloblog.render import render_post
    url = config.BASE_URL + posts.url_for(row)
    with i18n.in_site_language():
        read = i18n.t("Read it on {site}", site=s["site_title"])
    inner = (f'<h1 style="{_H1}"><a href="{escape(url)}" style="color:inherit;text-decoration:none">'
             f'{escape(row["title"])}</a></h1>'
             + _for_email(render_post(_post_parts(row, s, can_read))[0])
             + f'<p style="margin:28px 0 0"><a href="{escape(url)}" style="{_BUTTON}">{escape(read)}</a></p>')
    return _email_page(s, inner, token)


def digest_email(rows, s, token: str) -> tuple:
    """(subject, text, html) for a week's or a month's posts in one email:
    each one's title, summary and link."""
    from html import escape
    from soloblog import i18n
    from soloblog import posts
    from soloblog.render import excerpt, render_post
    site = s["site_title"]
    with i18n.in_site_language():
        subject = (i18n.t("This week on {site}", site=site) if digest(s) == "week"
                   else i18n.t("This month on {site}", site=site))
        read = i18n.t("Read it")
    items = [(r["title"], r["summary"] or excerpt(render_post(posts.load_post_body(r["slug"]))[0]),
              config.BASE_URL + posts.url_for(r)) for r in rows]
    why, stop, link = _footer(s, token)
    text = f"{subject}\n\n" + "\n\n".join(f"{t}\n{summary}\n{url}" for t, summary, url in items) + \
        f"\n\n--\n{why}\n{stop} {link}\n"
    inner = f'<h1 style="{_H1}">{escape(subject)}</h1>' + "".join(
        f'<div style="margin:0 0 24px;padding:0 0 24px;border-bottom:1px solid #e4e4e7">'
        f'<h2 style="font-size:19px;line-height:1.3;margin:0 0 6px"><a href="{escape(url)}" '
        f'style="color:#18181b;text-decoration:none">{escape(t)}</a></h2>'
        f'<p style="margin:0 0 8px;color:#52525b">{escape(summary)}</p>'
        f'<a href="{escape(url)}" style="color:#18181b;font-weight:600">{escape(read)} →</a></div>'
        for t, summary, url in items)
    return subject, text, _email_page(s, inner, token)


# a designed email's look: no theme colours (an email app shows them its
# own way), the same in light and dark email apps
_H1 = "font-size:26px;line-height:1.25;margin:0 0 20px;color:#18181b"
_BUTTON = ("display:inline-block;background:#18181b;color:#ffffff;text-decoration:none;padding:10px 18px;"
           "border-radius:6px;font-weight:600")


def _email_page(s, inner, token):
    from html import escape
    why, stop, link = _footer(s, token)
    return (f'<!doctype html><html><body style="margin:0;padding:24px 12px;background:#f4f4f5">'
            f'<div style="max-width:600px;margin:0 auto;background:#ffffff;border-radius:8px;padding:32px 28px;'
            f'font:16px/1.6 -apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,Helvetica,Arial,sans-serif;'
            f'color:#27272a">'
            f'<p style="margin:0 0 24px;font-size:14px;font-weight:600;color:#71717a">'
            f'<a href="{escape(config.BASE_URL)}" style="color:inherit;text-decoration:none">'
            f'{escape(s["site_title"])}</a></p>{inner}</div>'
            f'<p style="max-width:600px;margin:16px auto 0;font:12px/1.5 sans-serif;color:#71717a;text-align:center">'
            f'{escape(why)} <a href="{escape(link)}" style="color:#71717a">{escape(stop.rstrip(":"))}</a></p>'
            f'</body></html>')


def _for_email(html):
    """A post's html as an email app can show it: addresses in full, no
    scripts, buttons or the site's classes, pictures no wider than the email."""
    html = re.sub(r"<(script|style|iframe|video|audio|button|svg|form|noscript)\b.*?</\1>", "", html, flags=re.S | re.I)
    html = re.sub(r'\s(?:class|srcset|sizes|loading|decoding|data-[\w-]+|on\w+)="[^"]*"', "", html)
    html = re.sub(r'\s(src|href)="/(?!/)', lambda m: f' {m.group(1)}="{config.BASE_URL}/', html)
    html = re.sub(r"<img\b", '<img style="max-width:100%;height:auto;border-radius:6px"', html)
    return html


def _deliver(subs, email_for, pause=0.5) -> tuple:
    """email_for(sub) -> (subject, text, html), sent to each of subs, until
    the email service says its daily or monthly limit is reached. Returns
    how many went out, and who's left."""
    from soloblog import mail
    sent = 0
    for i, sub in enumerate(subs):
        link = unsubscribe_url(sub["token"])
        subject, text, html = email_for(sub)
        if mail.send_email(sub["email"], subject, text, html=html,
                           headers={"List-Unsubscribe": f"<{link}>",
                                    "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"}):
            sent += 1
        elif mail.over_limit():
            return sent, list(subs[i:])
        time.sleep(pause)
    return sent, []


def send_posts(rows, s) -> int:
    """A digest - these posts in one email - to every confirmed subscriber."""
    subs = confirmed()
    sent, rest = _deliver(subs, lambda sub: digest_email(rows, s, sub["token"]))
    if rest:
        _hold([r["slug"] for r in rows], rest, len(subs), sent)
    return sent


def send_test(row, s, to: str) -> bool:
    """A post's email to the site's owner first, to see how it looks -
    "test" in its token, so its unsubscribe link does nothing."""
    from soloblog import mail
    return mail.send_email(to, row["title"], post_email(row, s, "test"), html=post_email_html(row, s, "test"))


def _post_for(row, s):
    from soloblog import members, posts
    gated = posts.is_gated(row)

    def email_for(sub):
        # a members post: the whole of it to those who can read it
        can_read = not gated or members.can_read(row, members.by_email(sub["email"]))
        return (row["title"], post_email(row, s, sub["token"], can_read),
                post_email_html(row, s, sub["token"], can_read))
    return email_for


def send_post(row, s=None, to=None) -> int:
    """Emails a post to every confirmed subscriber (or just `to`, a
    list of rows). Returns how many went out. Paced a little, so an
    email API's per-second limit isn't hit; whoever the email service's
    daily limit keeps it from is held for later (send_held)."""
    from soloblog import settings
    s = s or settings.get_all()
    subs = to if to is not None else confirmed()
    sent, rest = _deliver(subs, _post_for(row, s), 0.5 if to is None else 0)
    if rest and to is None:
        _hold([row["slug"]], rest, len(subs), sent)
    return sent


# ---- held back by the email service's daily or monthly limit: who a
# newsletter hasn't reached yet, sent once the limit resets. Resend's
# resets at midnight UTC, so that's when the next try is.

_held_lock = threading.Lock()


def held() -> list:
    from soloblog import settings
    try:
        entries = json.loads(settings.get("newsletter_held") or "[]")
    except ValueError:
        return []
    return [e for e in entries if isinstance(e, dict) and e.get("slugs") and e.get("ids")] \
        if isinstance(entries, list) else []


def _keep_held(entries):
    from soloblog import settings
    settings.set_many({"newsletter_held": json.dumps(entries) if entries else ""})


def _next_try() -> str:
    return (utcnow() + timedelta(days=1)).replace(hour=0, minute=5, second=0, microsecond=0) \
        .isoformat(timespec="seconds")


def _hold(slugs, rest, total, sent):
    with _held_lock:
        entries = held()
        after = _next_try()
        for e in entries:  # the limit holds everything else back too
            e["after"] = after
        entries.append({"slugs": slugs, "ids": [sub["id"] for sub in rest], "total": total, "sent": sent,
                        "after": after})
        _keep_held(entries)


def held_for(slug):
    """What's still to go for a post, or None."""
    return next((e for e in held() if slug in e["slugs"]), None)


def held_note(e) -> str:
    from datetime import datetime
    from soloblog.tz import to_local
    after, today = to_local(datetime.fromisoformat(e["after"])), to_local(utcnow())
    when = "later today" if after.date() == today.date() else "tomorrow"
    return (f"Sent to {e.get('sent', 0)} of {e.get('total', 0)} subscribers - your email service's limit was "
            f"reached, so the rest go out {when}")


def send_held(s) -> int:
    """The rest of each held newsletter, once the limit has reset - to
    those still subscribed, of posts still live. Returns how many went out."""
    from soloblog import posts
    now = utcnow().isoformat(timespec="seconds")
    sent = 0
    with _held_lock:
        entries = held()
        if not entries or entries[0].get("after", "") > now:
            return 0
        while entries:
            e = entries[0]
            rows = [r for r in (posts.get_post(slug) for slug in e["slugs"]) if r and posts.is_live(r)]
            subs = [sub for sub in by_ids(e["ids"]) if sub["confirmed_at"] and not sub["unsubscribed_at"]]
            if rows and subs:
                email_for = _post_for(rows[0], s) if len(e["slugs"]) == 1 else \
                    (lambda sub, rows=rows: digest_email(rows, s, sub["token"]))
                n, rest = _deliver(subs, email_for)
                sent += n
                if rest:
                    e.update(ids=[sub["id"] for sub in rest], sent=e.get("sent", 0) + n)
                    for other in entries:
                        other["after"] = _next_try()
                    break
            entries.pop(0)
        _keep_held(entries)
    return sent


# ---- the subscribe box

def Box(s, page=False):
    """Under posts, on the homepage and at /newsletter - or nothing when
    the newsletter's off. page: /newsletter itself, its heading the page's
    and the card the same as Join's and Sign in's. With members on, a
    visitor joins here - members and subscribers one list."""
    from soloblog import members
    m = mode(s)
    member = members.current() if members.enabled(s) else None
    if members.enabled(s) and not member:
        return _card(*_join(s, m), page)
    if not m or (member and m == "builtin" and is_subscribed(member["email"])):
        return None
    title = s.get("newsletter_title") or i18n.t("Get new posts by email")
    intro = s.get("newsletter_intro") or i18n.t("No spam - just the next post, when it's out. Unsubscribe any time.")
    if m == "builtin":
        form = Form(
            Div(Input(name="email", type="email", required=True, placeholder="you@example.com", autocomplete="email",
                      aria_label=i18n.t("Email address"), cls="input input-sm join-item flex-1 min-w-0"),
                Button(i18n.t("Subscribe"), type="submit", cls="btn btn-primary btn-sm join-item"), cls="join w-full"),
            # honeypot, like the comment form's
            Input(name="website", cls="hidden", tabindex="-1", autocomplete="off"),
            captcha.Widget(s, cls="mt-2"),
            Span(id="newsletter-status", data_status_slot=True, role="status", cls="text-xs text-base-content/60 mt-2 block"),
            hx_post="/newsletter/subscribe", hx_target="#newsletter-status",
            hx_swap="outerHTML show:none focus-scroll:false"
        )
    else:
        label, _, _, action, field = SERVICES[m]
        form = Form(
            Div(Input(name=field, type="email", required=True, placeholder="you@example.com", autocomplete="email",
                      aria_label=i18n.t("Email address"), cls="input input-sm join-item flex-1 min-w-0"),
                Button(i18n.t("Subscribe"), type="submit", cls="btn btn-primary btn-sm join-item"), cls="join w-full"),
            P(i18n.t("Opens {service} to finish.", service=label), cls="text-xs text-base-content/50 mt-2"),
            action=action.format(s[f"newsletter_{m}"]), method="post", target="_blank"
        )
    return _card(title, intro, form, page)


def _join(s, m):
    """(title, intro, form) for the box with members on: an email, joining
    - and, with Soloblog's own newsletter, new posts by email too."""
    letter = m == "builtin"
    if letter:
        title = s.get("newsletter_title") or i18n.t("Get new posts by email")
        intro = s.get("newsletter_intro") or i18n.t("No spam - just the next post, when it's out. Unsubscribe any time.")
    else:
        title = i18n.t("Become a member")
        intro = s.get("members_intro") or i18n.t("Members can read every members-only post. Joining is free.")
    form = Form(
        Div(Input(name="email", type="email", required=True, placeholder="you@example.com", autocomplete="email",
                  aria_label=i18n.t("Email address"), cls="input input-sm join-item flex-1 min-w-0"),
            Button(i18n.t("Subscribe") if letter else i18n.t("Join"), type="submit",
                   cls="btn btn-primary btn-sm join-item"), cls="join w-full"),
        Label(Input(type="checkbox", name="newsletter", value="1", checked=True, cls="checkbox checkbox-xs"),
              Span(i18n.t("Email me new posts"), cls="text-xs"),
              cls="flex items-center gap-2 mt-2 cursor-pointer") if letter else None,
        Input(name="website", cls="hidden", tabindex="-1", autocomplete="off"),
        captcha.Widget(s, cls="mt-2"),
        P(i18n.t("You'll be a member too, so you can read members-only posts."),
          cls="text-xs text-base-content/60 mt-2") if letter else None,
        P(i18n.t("Already a member?"), " ", A(i18n.t("Sign in"), href="/signin", cls="link"),
          cls="text-xs text-base-content/60 mt-1"),
        action="/join", method="post"
    )
    return title, intro, form


def _card(title, intro, form, page):
    if page:
        return Div(Div(H1(title, cls="text-xl font-bold"), P(intro, cls="text-sm text-base-content/70"), form,
                       cls="card-body p-6 gap-3"),
                   cls="card card-border bg-base-100 max-w-md mx-auto", id="newsletter")
    return Div(Div(
        H3(title, cls="text-base font-semibold text-accent mb-1"),
        P(intro, cls="text-sm text-base-content/70 mb-3"),
        form,
        cls="card-body p-5"
    ), cls="card card-border bg-base-100", id="newsletter")
