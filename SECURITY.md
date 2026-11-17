# Security policy

For what this means for the owner of a site, in plain words, see
[How your site is kept safe](docs/guide/how-it-works.md#how-your-site-is-kept-safe).

## Reporting a vulnerability

Please **don't open a public issue** for security problems. Report them
privately through GitHub instead: go to the repository's **Security**
tab and choose **Report a vulnerability**.

Include what you found, how to reproduce it, and what an attacker could
do with it. You'll get a reply within 3 days. The fix ships in a patch
release, then the advisory is published - with credit to you, if you'd
like.

## Supported versions

Soloblog is in beta. Only the latest release gets security fixes.

## Running Soloblog safely

- Set a long, random `SESSION_SECRET`. Settings > Integrations warns you if
  it's still the development default.
- Serve it over HTTPS (see [DEPLOYMENT.md](docs/DEPLOYMENT.md#put-https-in-front)).
- Turn on two-factor login or add a passkey (Settings > Security).
- Keep backup zips and your storage bucket private: they contain your
  settings, including any SMTP password, API keys and the fediverse
  signing key.
- Behind a CDN, set `CLIENT_IP_HEADER` only if your server accepts traffic
  from that CDN alone; otherwise the header can be faked.

## What's in place

- Every release, pull request and Monday: known vulnerabilities in the
  pinned dependencies are checked (`pip-audit`), and once the repository
  is public, GitHub's code scanning (CodeQL) looks for injection, unsafe
  redirects and the like. A failing check blocks a release.

- Passwords hashed with Argon2id; 5 login attempts per 15 minutes; TOTP
  two-factor with recovery codes; passkeys (WebAuthn).
- Sessions last 14 days unused and can be revoked from Settings > Security.
- Every state-changing request must come from the site's own origin (CSRF).
  The exceptions never act on the login cookie: `/ap/inbox`, `/webmention`
  and `/stripe/webhook` (each checked its own way), and the API, Micropub,
  MCP and Ghost endpoints, which take only a key.
- Anyone not logged in may send at most 16 MB in one request.
- Rate limits count the visitor's own address; `X-Forwarded-For` is only
  believed from a proxy on a private network.
- A password reset link sent by email keeps two-factor login on.
- Posts, comments, translations and imported content are sanitised with
  an allowlist (nh3).
- Only `static/` is served as files; uploads are served by name only.
- Outbound requests the site makes (link checker, webhooks, imports,
  webmentions, fediverse deliveries) go to public addresses only.
- ActivityPub inbox deliveries must carry a valid HTTP signature covering
  where they were sent and when, from an actor on the server it claims.
- Uploaded images: known formats only, re-encoded (no EXIF or location
  kept), and counted in pixels before they're decoded.
- Members-only text never reaches feeds, search, lists, the fediverse or
  emails to people who can't read it.
- Security headers on every response; third-party scripts are vendored or
  pinned with SRI hashes.
