"""Content-Security-Policy, with a fresh nonce on every page.

Every <script> this app writes carries nonce=NONCE - a random marker
made once per process, never sent to a browser as-is. On the way out,
ContentSecurityPolicy swaps it for a new random nonce and sends the
policy allowing exactly that nonce. Anything injected into a page can't
carry it (the marker never leaves the server), so it won't run. Nor
will inline event handlers (onclick=...) - there aren't any; see
actions.py.

'strict-dynamic' lets a trusted script load others (Google Analytics,
AdSense, Mermaid do), the approach Google's own CSP guidance uses.
There's no 'unsafe-inline' or https: fallback for browsers too old to
know nonces: every browser that runs this app's scripts knows them, and
any browser that knows them ignored the fallback anyway - it only
opened a door on the oldest ones.
"""
import re
import secrets

NONCE = "csp-" + secrets.token_hex(16)
_MARK = NONCE.encode()


def nonce_scripts(html: str) -> str:
    """Admin-written <head> code (Settings > Site): its <script> tags get
    the nonce, so it keeps working under the policy."""
    return re.sub(r"<script\b", f'<script nonce="{NONCE}"', html, flags=re.I)


def policy(nonce: str) -> str:
    return "; ".join([
        "default-src 'self'",
        f"script-src 'nonce-{nonce}' 'strict-dynamic'",
        # inline styles: htmx, CodeMirror, KaTeX and the custom CSS setting
        "style-src 'self' 'unsafe-inline' https:",
        # cover images, avatars and stock photos can live anywhere
        "img-src 'self' data: blob: https:",
        "media-src 'self' blob: https:",
        "font-src 'self' data: https:",
        "connect-src 'self' https:",
        # click-to-load embeds, maps, hosted forms, ads
        # https: for embeds; 'self' for a PDF from the media library
        "frame-src 'self' https:",
        "object-src 'none'",
        "base-uri 'self'",
        # the newsletter box can sign readers up on these (newsletter.py)
        "form-action 'self' https://buttondown.com https://app.kit.com https://*.list-manage.com "
        "https://*.substack.com",
        "frame-ancestors 'self'",
    ])


class ContentSecurityPolicy:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        start = None
        chunks = []

        async def buffer(message):
            nonlocal start
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                if not headers.get(b"content-type", b"").startswith(b"text/html"):
                    start = False
                    return await send(message)
                start = message
                return
            if start is False:
                return await send(message)
            chunks.append(message.get("body", b""))
            if message.get("more_body"):
                return
            nonce = secrets.token_urlsafe(16)
            body = b"".join(chunks).replace(_MARK, nonce.encode())
            headers = list(start.get("headers", []))
            # a HEAD response has no body to measure - its length stays
            # whatever the page would have been
            if scope["method"] != "HEAD":
                headers = [(k, v) for k, v in headers if k.lower() != b"content-length"]
                headers.append((b"content-length", str(len(body)).encode()))
            headers.append((b"content-security-policy", policy(nonce).encode()))
            await send({**start, "headers": headers})
            await send({"type": "http.response.body", "body": body})

        return await self.app(scope, receive, buffer)
