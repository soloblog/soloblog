import logging
from soloblog.tz import utcnow
import urllib.parse
import urllib.request
import json

from soloblog import netguard

log = logging.getLogger(__name__)


def notify_new_comment(webhook_url: str, title: str, author_name: str, body: str):
    """The chat version of the comment email: who, on which post (by its
    title, as the email says it), the start of what they wrote, and where
    to approve it."""
    from soloblog import config
    notify(webhook_url, f"{author_name} commented on “{title}”: {body[:200]}\n"
                        f"Approve or trash it: {config.BASE_URL}/admin/comments")


def comment_waiting(post_slug: str, author_name: str, body: str):
    """A new comment is waiting for approval: the webhook, and an email
    to the admin if they asked for one (Settings > Integrations >
    Notifications) - sent in the background, so a slow mail server
    never holds up the reader's request."""
    import threading
    from soloblog import config
    from soloblog import mail
    from soloblog import settings
    from soloblog import posts
    s = settings.get_all()
    post = posts.get_post(post_slug)
    title = post["title"] if post else post_slug
    notify_new_comment(s.get("comment_webhook_url"), title, author_name, body)
    from soloblog import webhooks
    webhooks.send("comment.created", webhooks.comment_data(post_slug, author_name, body))
    if s.get("notify_comments") == "1" and s.get("admin_email"):
        text = (f"{author_name} commented on “{title}”:\n\n{body[:2000]}\n\n"
                f"It's waiting for you. Approve or trash it:\n{config.BASE_URL}/admin/comments\n\n"
                f"The post:\n{config.BASE_URL}{posts.url_for_slug(post_slug)}\n")
        threading.Thread(target=mail.send_email, daemon=True,
                         args=(s["admin_email"], f"{author_name[:60]} commented on “{title[:80]}”", text)).start()


def sign_in(request):
    """A sign-in from a browser this site hasn't seen before: an email to
    the admin, so a sign-in that wasn't them doesn't go unnoticed - when
    email is set up and the alert is on (Settings > Email > Admin email).
    Sent in the background."""
    import threading
    from soloblog import config, mail, ratelimit, settings, tz
    s = settings.get_all()
    if s.get("signin_alerts") == "0" or not s.get("admin_email") or not mail.can_send():
        return
    when = tz.to_local(utcnow()).strftime("%d %b %Y, %H:%M")
    browser = (request.headers.get("user-agent") or "an unknown browser")[:160]
    text = (f"Someone signed in to {s.get('site_title')} from a browser it hasn't seen before.\n\n"
            f"When: {when} ({s.get('timezone') or 'UTC'})\n"
            f"IP address: {ratelimit.client_ip(request)}\n"
            f"Browser: {browser}\n\n"
            "If this was you, there's nothing to do.\n\n"
            "If it wasn't, change your password and log out every other device:\n"
            f"{config.BASE_URL}/admin/settings?tab=security\n")
    threading.Thread(target=mail.send_email, daemon=True,
                     args=(s["admin_email"], f"New sign-in to {s.get('site_title')}", text)).start()


def guessing(minutes: int):
    """Many wrong passwords from all over at once (auth_routes.SITE_WRONG):
    one email to the admin, under the same switch as the sign-in alert."""
    import threading
    from soloblog import config, mail, settings
    s = settings.get_all()
    if s.get("signin_alerts") == "0" or not s.get("admin_email") or not mail.can_send():
        return
    text = (f"Someone is trying many passwords on {s.get('site_title')} - more wrong ones in {minutes} minutes "
            "than a person would type.\n\n"
            "Until it stops, the password works only in a browser that has logged in before. On a new "
            "device, use a passkey or your recovery key, or wait.\n\n"
            "A long password that you use nowhere else can't be guessed this way. To protect your login "
            "beyond the password, add a passkey or two-factor authentication (2FA):\n"
            f"{config.BASE_URL}/admin/settings?tab=security\n")
    threading.Thread(target=mail.send_email, daemon=True,
                     args=(s["admin_email"], f"Someone is guessing the password for {s.get('site_title')}",
                           text)).start()


def notify(webhook_url: str, text: str):
    """One line to the Slack or Discord webhook (a new comment, a contact
    form message). Never raises: a broken webhook mustn't stop a comment
    or a message from saving."""
    if not webhook_url:
        return
    host = (urllib.parse.urlsplit(webhook_url).hostname or "").lower()
    # Slack reads "text"; Discord refuses a message without "content"
    # ("Cannot send an empty message")
    field = "content" if host.endswith(("discord.com", "discordapp.com")) else "text"
    req = urllib.request.Request(webhook_url, data=json.dumps({field: text}).encode(), method="POST",  # noqa: S310 - opened through netguard
                                 # named: Discord's firewall turns away Python's default name (error 1010)
                                 headers={"Content-Type": "application/json", "User-Agent": "Soloblog"})
    try:
        # the webhook URL is the admin's, but never a private address
        netguard.open_url(req, timeout=5)
    except Exception as e:
        # the host, not the address: a webhook's path is its password
        log.warning("the chat webhook at %s failed: %s", host, e)
