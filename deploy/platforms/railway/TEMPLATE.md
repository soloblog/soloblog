# Railway template

Railway's templates are made in its template editor, not from a file. This
is everything to put in it, signed in to the project's Railway account.

## The template

- **Name:** Soloblog
- **Description:** A blog and personal website for one person, that you run
  yourself
- **Category:** Blogs
- **Icon:** `docs/brand/soloblog-icon-512.png`

## The service

One service, named `soloblog`.

- **Source:** Docker image `ghcr.io/soloblog/soloblog:latest`
- **Volume:** mounted at `/data`
- **Public networking:** HTTP on port `8080`, with a Railway domain
- **Healthcheck path:** `/healthz`
- **Restart policy:** On failure
- **Replicas:** 1 - it keeps its data in one folder

Variables (Railway detects itself through `RAILWAY_ENVIRONMENT`, and setup
reads the address from `RAILWAY_PUBLIC_DOMAIN`):

| Name | Value |
|---|---|
| `SETUP_TOKEN` | `${{secret(32)}}` |
| `ENV` | `production` |
| `DATA_DIR` | `/data` |

Setup tells the owner to copy `SETUP_TOKEN` from the service's Variables,
so nobody has to search the logs.

## Overview (the template page)

```markdown
# Deploy and Host Soloblog on Railway

Soloblog is a free, open source blog and personal website for one person.
Write in a calm editor, choose from 35 colour palettes, and build pages out of
sections - a homepage, a portfolio, a book's landing page. Readers can
comment, subscribe by email or follow from Mastodon, and members-only posts
can be free or paid.

## About Hosting Soloblog

Soloblog is one container with one folder of data: posts as markdown files,
a SQLite database, pictures and settings, all on the volume at `/data`.
There's no database server to run, and backups to a zip or an
S3-compatible bucket are built in.

## Common Use Cases

- A personal blog or newsletter
- A personal website, portfolio or a book's landing page
- Members-only posts, free or paid through Stripe

## Dependencies for Soloblog Hosting

- A volume at `/data`, which this template adds

### Deployment Dependencies

- [User guide](https://github.com/soloblog/soloblog/blob/master/docs/guide/README.md)
- [Hosting guide](https://github.com/soloblog/soloblog/blob/master/docs/DEPLOYMENT.md#railway)

### Implementation Details

After it deploys, open the Railway domain. First-time setup asks for a
setup token: open the service's Variables in Railway and copy
`SETUP_TOKEN`. Then choose your password and keep the recovery key it
gives you. To send email on Railway's Hobby plan, use Resend - Railway
allows SMTP only on Pro and up.

## Why Deploy Soloblog on Railway?

Railway runs the container and the volume for you, with HTTPS and your own
domain, so you can have a blog running in a few minutes without managing a
server.
```

## After publishing

Point the Railway section of docs/DEPLOYMENT.md at the template (making the
account stays its first step), and add a Railway button to the README.
