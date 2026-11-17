import logging
import threading

from soloblog import comments
from soloblog import config
from soloblog import i18n
from soloblog import mail
from soloblog import posts
from soloblog import settings

log = logging.getLogger(__name__)

# "Someone replied to your comment" emails. A commenter opts in with a
# checkbox on the comment form (only offered when an email provider is
# set up); an email goes out when the author replies to them, or when
# a visitor's reply to them is approved. Sent on a background thread -
# a slow mail server never holds up the page.


def offered() -> bool:
    return settings.get("reply_emails") == "1" and settings.get("email_provider") in ("smtp", "api")


def _message(reply, parent):
    post = posts.get_post(parent["post_slug"])
    title = post["title"] if post else parent["post_slug"]
    url = f"{config.BASE_URL}/post/{parent['post_slug']}#comment-{reply['id']}"
    body = reply["body"] if len(reply["body"]) <= 600 else reply["body"][:600] + "…"
    stop = f"{config.BASE_URL}/comment/unsubscribe/{parent['notify_token']}"
    name = reply["author_name"]
    with i18n.in_site_language():
        subject = i18n.t("{name} replied to your comment on “{title}”", name=name, title=title)
        replied = i18n.t("{name} replied to your comment on “{title}”:", name=name, title=title)
        read = i18n.t("Read it and reply:")
        why = i18n.t("You're getting this because you asked to hear about replies.")
        stop_label = i18n.t("Stop these emails:")
    return subject, f"{replied}\n\n{body}\n\n{read}\n{url}\n\n--\n{why}\n{stop_label} {stop}\n"


def _send_all(jobs):
    # one that fails mustn't drop the ones after it; the error's own words can hold an address
    for job in jobs:
        try:
            mail.send_email(*job)
        except Exception as e:
            log.warning("a reply email couldn't be sent (%s)", type(e).__name__)


def send_for(reply_ids):
    """Queues a reply email for each of reply_ids whose parent's writer
    wants one."""
    if not offered():
        return
    jobs = []
    for reply_id in reply_ids:
        parent = comments.reply_recipient(reply_id)
        if parent:
            subject, body = _message(comments.get(reply_id), parent)
            jobs.append((parent["email"], subject, body))
    if jobs:
        threading.Thread(target=_send_all, args=(jobs,), daemon=True).start()
