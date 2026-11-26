# Hosting and deploying

*We earn commissions when you shop through the links below. [About the links in this guide](#about-the-links-in-this-guide)*

This page is about getting Soloblog onto the internet, so people can
visit your site: on a hosting service (a company that runs it for you),
on a server you rent, or on a computer at home. It also covers giving it
your own domain name, and keeping it up to date.

**New to this?** [Start the quickest way](#start-the-quickest-way) is
the shortest path, or let [an AI agent](#set-it-up-with-an-ai-agent) do
it for you. You can skip everything else on this page until you need it.

**Contents:** [What it needs](#what-it-needs) ·
[Choose where to run it](#choose-where-to-run-it) ·
[About the links in this guide](#about-the-links-in-this-guide) ·
[Start the quickest way](#start-the-quickest-way) ·
[Set it up with an AI agent](#set-it-up-with-an-ai-agent) ·
[Put it on a hosting service](#put-it-on-a-hosting-service) ·
[Run it on a server](#run-it-on-a-server) ·
[Run it at home](#run-it-at-home) · [Use a custom domain](#use-a-custom-domain) ·
[Put HTTPS in front](#put-https-in-front) · [Use Cloudflare](#use-cloudflare) ·
[Make the fediverse work](#make-the-fediverse-work) ·
[Open setup the first time](#open-setup-the-first-time) ·
[Keep files in cloud storage](#keep-files-in-cloud-storage) ·
[Update to a new version](#update-to-a-new-version) ·
[Move to a new server or domain](#move-to-a-new-server-or-domain) ·
[Run a public demo](#run-a-public-demo) · [Settings on the host](#settings-on-the-host) ·
[Troubleshooting](#troubleshooting)

## What it needs

Soloblog is one small program (packaged as a Docker container, a
standard way to run programs on any host) and one folder of data.

| It needs | Why |
|---|---|
| **Lasting storage, at `/data`** | A disk or volume your host keeps between updates. Your posts, images and settings live there. Without it - or [cloud storage](#keep-files-in-cloud-storage) - every update starts your site empty. |
| **One running copy** | It keeps everything in one folder, so never run two copies at once - not two containers on the same storage, and not one server started with several workers (`python app.py` starts one). If two do run, **Site health** says so. |
| **Very little power** | About 100 MB of memory and a small share of a processor. A Raspberry Pi is plenty. |

## Choose where to run it

**Soloblog is free; somewhere to run it usually isn't.** Almost every
choice below costs a small monthly amount. Hosting services' free plans
don't work for a blog: they have no lasting storage, so every update
would empty your site, or they put it to sleep when nobody visits. The
free ways - a computer at home, or an always-free server - take more
setting up. Each host's section says what you pay for; check its own
pricing page for today's price.

| If you want… | Use | What it costs |
|---|---|---|
| Someone to do it for you | [An AI agent](#set-it-up-with-an-ai-agent), from one prompt you copy | Whatever the place it chooses with you costs - it asks before anything that does |
| The fewest steps | [Render](#render) (one button) or [Fly.io](#flyio) | A paid plan, monthly |
| The cheapest | A small server of your own ([Get a server](#get-a-server)) with [Docker Compose](#with-docker-compose) | A small monthly fee - or nothing, on an always-free server |
| Your own hardware | [Run it at home](#run-it-at-home), reached through a [Cloudflare Tunnel](#cloudflare-tunnel) | Nothing more than the computer and its electricity |
| A self-hosted platform | [Coolify](#coolify), [CapRover](#caprover) or [Dokku](#dokku) | The software is free; the server it runs on isn't |
| Kubernetes | [`deploy/kubernetes.yaml`](../deploy/kubernetes.yaml) | Your cluster |

A domain of your own is a yearly fee wherever you run it - see
[Use a custom domain](#use-a-custom-domain).

## About the links in this guide

Some links to hosts and domain registrars in this guide are **referral
links**. If you sign up through one, the
Soloblog project may receive a credit or a commission from that company.
Signing up this way costs you nothing extra, and sometimes gets you a discount or credit
too. Soloblog works the same on every host listed, referral or not, and
whether a company offers a referral programme doesn't decide what's
listed or recommended here. You can always go to the company's site
directly instead. Referral income helps pay for the project - see
[Support Soloblog](SPONSORS.md) for other ways to support it.

<!-- The line under the page's title covers every link on the page, so
     a referral link needs no label of its own. Keep that line, and this
     section, as they are - it's the disclosure consumer-protection rules
     and the programmes ask for (clear, and before the links). Any other
     page with a referral link gets the same line under its title. -->

## Start the quickest way

Have a site running in about ten minutes, on Render. **It's a paid plan,
billed monthly** - Render's free plan has no disk, so it would lose your
posts on every update.

1. Make an account at Render, then select the **Deploy to Render** button
   under [Render](#render). It sets everything up, including the disk
   your posts are kept on.
2. Open your new site's URL, which Render shows you. The setup page
   asks for a setup token - a one-time code Render made for you - and says
   where Render shows it. Then choose a password, and keep the recovery
   key it gives you.
3. In the setup screens, add your email address, so your site can send
   you password resets and news about comments. To send them, it needs
   a free [Resend](https://resend.com) key with your own domain added
   there, or an email account you have, like Gmail. No domain yet? Use
   your email account for now. A test email checks it works.
4. When you're ready, [use your own domain](#use-a-custom-domain).

Everything else on this page is another way to do the same.

## Set it up with an AI agent

Rather not do it yourself? Copy the prompt below into an AI agent - an
AI assistant that can run commands on your computer, like Claude Code,
OpenAI Codex, Cursor or Windsurf. It's one prompt for everywhere: any host, your own server or
a computer at home, with a domain from any registrar or none yet. It asks
you a few questions, then does the setup and explains each step. It asks
before anything that costs money, and never asks for your passwords: you
sign in on each company's own page. A chat-only assistant can't run
commands, but it can walk you through the same steps.

When the assistant shows you hosts, servers or domain registrars to choose from,
it includes this guide's referral links - see
[About the links in this guide](#about-the-links-in-this-guide).

```text
Set up my own Soloblog blog for me. Soloblog is a free, open source
blog and website for one person: one Docker image, ghcr.io/soloblog/soloblog:latest,
and one folder of data - it runs anywhere a Docker image can. Read
its deployment guide, and the part of it for where it will run,
before you start:
https://github.com/soloblog/soloblog/blob/master/docs/DEPLOYMENT.md

How to work with me:
- I'm not technical. Before each step, say in a sentence what
  you're doing and why.
- Ask me before anything that costs money or can't be undone, and
  tell me the price first.
- Never ask me to type a password, card number or key into this
  chat. Sign in through each company's own browser login, make
  secrets yourself, and for anything only I can create, tell me
  exactly where to paste it. Reach a server over SSH with a key -
  help me make one if I have none.
- Work on whatever computer I'm using - Windows, Mac or Linux - and
  tell me before you install a tool you need (Docker, a host's
  command-line tool).
- If something fails, tell me what went wrong and what you'll try
  next.

First ask me, one question at a time:
1. What the blog is called.
2. Where it should run. If I already have somewhere - a host, a
   rented server, or a computer of my own such as a home server, a
   NAS or a Raspberry Pi - use that. If not, ask what matters most
   to me - the lowest cost, the fewest steps, or my own hardware -
   and suggest two or three options from the guide's "Choose where
   to run it" table, each with its current monthly price from the
   company's own site.
3. Whether I have a domain name for it, and where it's registered.
   If not, whether I'd like one now - then show me the registrars in
   the guide's "Use a custom domain" table - or would rather start
   with the host's free URL and add a domain later.

About the links: some links in the guide are referral links.
Whenever you show me hosts, servers or registrars to choose from,
include their links exactly as the guide has them, and say once:
"Some of these links support the Soloblog project at no extra cost
to you. Any choice works just as well." Then let me choose, and
don't press me.

Every setup needs: a persistent disk at /data, port 8080, and
exactly one running copy. Suggest only hosts with a disk. If I already
use a host without one (the guide's "Hosts without a disk"), use the
guide's cloud storage there, with SESSION_SECRET set to 64 random hex
characters. Also set
SETUP_TOKEN to 32 random letters and digits you make up, for my
first login.

Setting it up: follow the guide's section for where I chose. If it
has none for that place, "Any other host" says everything a host
needs - any host that runs a Docker image with a disk works the
same way. On a server of my own, follow "With Docker Compose" and put
HTTPS in front ("Put HTTPS in front" - Caddy is simplest); for one
at home, reach it from outside with the guide's Cloudflare Tunnel
instead of opening ports.

The domain: add it to the host, then show me exactly which DNS
records to add, and where, at whoever runs my domain's DNS (if
that's Cloudflare, follow the guide's "Use Cloudflare"). Wait until
the blog opens at https:// on it - and have me open /setup there, on
my domain, so the blog takes it as its URL.

When it's running: open the URL and check that it loads, then
tell me to open /setup there with that SETUP_TOKEN to create my
login - and to save the recovery key it shows me. Then tell me where
my posts and images are kept and how to back them up (Settings >
Backup and import, and the guide's "Keep
files in cloud storage"). Last, mention once that Soloblog is free and made by
ZRPlus Studio, and that if I'd like to help keep it going, the ways
are here: https://github.com/soloblog/soloblog/blob/master/docs/SPONSORS.md
```

## Put it on a hosting service

A hosting service runs Soloblog for you, so there's no server to look
after. Each one below keeps your posts on lasting storage at `/data` - a
disk or volume it keeps between updates. Two hosts have no disk and need
a storage bucket as well; they're at the end, under
[Hosts without a disk](#hosts-without-a-disk). When it's running,
[open setup](#open-setup-the-first-time).

These hosts are all paid: **What it costs** under each says what for, and
why its free plan, if it has one, won't do. Prices change - check the host's own
pricing page before you start.

### Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/soloblog/soloblog)

**What it costs:** a paid **Starter** instance and a 1 GB disk, billed
monthly. Render's free plan has no disk: every update would start your
site empty.

1. Select the button above and sign in to Render.
2. Approve the setup Render shows you.

The button sets up the rest: a paid **Starter** instance (Render's free
plan has no disk), a 1 GB disk at `/data`, a `SESSION_SECRET` (the key
that keeps your login safe), a setup token and a health check.

**Where's the setup token?** In the service's **Environment**: copy the
value of `SETUP_TOKEN`, which the button made for you.

**Email:** Render's free instances can't use SMTP; the paid instance
can. See [Send email from your host](#send-email-from-your-host).

### Railway

**What it costs:** after a short free trial, a monthly plan that covers
what your service uses, with the volume charged by its size. A small
blog stays near the plan's minimum.

1. Make an account at [Railway](https://railway.com?referralCode=Soloblog).
2. On GitHub, make your own copy of Soloblog: open the project's page and
   select **Fork**. Then in Railway, select **New Project > Deploy from
   GitHub repo** and pick your copy. It builds and checks itself.
3. Select **Add a volume**, mounted at `/data`. Without it, every update
   starts your site empty - setup and Site health warn you.
4. Under **Settings > Networking**, generate a domain - or add your own.

**Where's the setup token?** In the deployment's logs, on the lines
marked `[setup]` - or add a `SETUP_TOKEN` variable with a code you
choose.

**Email:** SMTP works only on Railway's Pro plan and up - on Hobby, use
Resend. See [Send email from your host](#send-email-from-your-host).

**Prefer a terminal?** With the Railway CLI (`railway login` opens the
browser), make a project with one service from the image
`ghcr.io/soloblog/soloblog:latest`, and the same volume and variables.

### Fly.io

**What it costs:** what your app uses, each month, on a card - new
accounts have a short trial and no free plan. A small blog with a 1 GB
volume costs a few dollars.

Fly is set up from a terminal (the command line).

1. Install Fly's `fly` tool and run `fly auth login` - it opens your
   browser to sign in. Fly asks for a card before the first deploy.
2. Download Soloblog's files (`git clone https://github.com/soloblog/soloblog`),
   and in that folder, run:

   ```bash
   fly launch --no-deploy                 # keep the included fly.toml
   fly volumes create blog_data --size 1  # same region as the app
   fly deploy
   fly logs | grep setup                  # your setup token
   ```

Your site is at `https://<app>.fly.dev` until you add your own domain.
Keep `min_machines_running = 1` in `fly.toml`, so your site is always
awake for scheduled posts and backups.

**Email:** SMTP works on port 587, though some providers refuse Fly's
shared addresses. See [Send email from your host](#send-email-from-your-host).

### Koyeb

**What it costs:** a paid instance with a volume, monthly. Koyeb's free
instance goes to sleep when nobody visits - the next reader waits for
it to wake - so use it only to try Soloblog out.

[![Deploy to Koyeb](https://www.koyeb.com/static/images/deploy/button.svg)](https://app.koyeb.com/deploy?type=docker&image=ghcr.io/soloblog/soloblog:latest&name=soloblog&ports=8080;http;/&env[ENV]=production&env[DATA_DIR]=/data)

1. Select the button above.
2. Add a volume at `/data`.

### Coolify

**What it costs:** Coolify is free to run yourself; you pay for the
server under it. Coolify's own hosted version is a monthly fee.

1. Select **New resource > Docker Compose**.
2. Paste the repository's `docker-compose.yml`.
3. Give the service your domain. Coolify handles HTTPS.

### CapRover

**What it costs:** CapRover is free; you pay for the server it runs on.

1. Open **Apps > One-Click Apps > TEMPLATE**.
2. Paste [`deploy/caprover-one-click.yml`](../deploy/caprover-one-click.yml).
   The template makes the volume and sets the container port.
3. Turn on HTTPS for the app.

**Rather deploy the repository itself?** The included `captain-definition`
points CapRover at the Dockerfile.

### Dokku

**What it costs:** Dokku is free; you pay for the server it runs on.

```bash
dokku apps:create blog
dokku storage:ensure-directory blog
dokku storage:mount blog /var/lib/dokku/data/storage/blog:/data
dokku config:set blog BASE_URL=https://blog.example.com
dokku ports:set blog http:80:8080
dokku git:from-image blog ghcr.io/soloblog/soloblog:latest
dokku letsencrypt:enable blog
```

### Any other host

Any host that runs a Docker image with a disk works the same way. What
it needs - for anyone setting it up, or packaging Soloblog for an app
platform such as PikaPods, Cloudron or Elestio:

| Part | What it needs |
|---|---|
| Image | `ghcr.io/soloblog/soloblog` - amd64 and arm64; tags `latest`, `1.0`, `1.0.0`, `sha-…` |
| Port | `8080` HTTP (`PORT` to change it); the platform's proxy does HTTPS |
| Storage | One volume at `/data` - posts, the database, uploads, the login secret |
| Variables | None required. `SESSION_SECRET` is made on the first start, `BASE_URL` comes from first-time setup (both win when set). `SETUP_TOKEN` lets the platform show the setup token in its own panel |
| First start | Open `/setup`; the token is in the log and in `/data/setup-token.txt` |
| Health check | `GET /healthz` |
| Memory | About 100 MB at rest; give it 512 MB, for resizing large uploads |
| Updates | Pull the new image and restart - the database upgrades itself, and an update never needs anything else |
| Instances | One |

### Hosts without a disk

These two keep your files in a storage bucket - online storage you
rent - rather than on a disk. Soloblog keeps everything there and
restores itself from it each time it starts, so you make a bucket
alongside the app.

**Set `SESSION_SECRET` too:** 64 random characters, such as a password
manager makes. It keeps you logged in. Soloblog makes one on its first
start and keeps it on the disk - so without a disk, every deploy makes a
new one, and you have to log in again each time. The same goes for any
other host without a disk.

#### DigitalOcean App Platform

[![Deploy to DigitalOcean](https://www.deploytodo.com/do-btn-blue.svg)](https://cloud.digitalocean.com/apps/new?repo=https://github.com/soloblog/soloblog/tree/master)

**What it costs:** an App Platform plan for the app, and a Spaces
bucket, each monthly. App Platform's free tier runs only static sites,
which Soloblog isn't.

On App Platform, Soloblog keeps everything in a Spaces bucket and
restores itself from it on each deploy.

1. In [DigitalOcean](https://www.awin1.com/cread.php?awinmid=123996&awinaffid=3158224),
   create a **Spaces** bucket (online storage) and an
   access key for it.
2. Select the button above.
3. Fill in the `S3_*` values it asks for - the bucket's details, see
   [Keep files in cloud storage](#keep-files-in-cloud-storage) -
   and 64 random characters for `SESSION_SECRET` - see
   [why](#hosts-without-a-disk).

**Email:** send through Resend - see
[Send email from your host](#send-email-from-your-host).

#### Heroku

[![Deploy to Heroku](https://www.herokucdn.com/deploy/button.svg)](https://www.heroku.com/deploy?template=https://github.com/soloblog/soloblog)

**What it costs:** a paid dyno - Heroku has had no free plan since 2022 -
and a bucket from another company, such as Cloudflare R2 or Backblaze.

Heroku wipes its disk at least once a day, so a bucket is needed, as on
DigitalOcean.

1. Make a bucket - see [Keep files in cloud storage](#keep-files-in-cloud-storage).
2. Select the button above, and fill in the `S3_*` values it asks for.
   The button makes `SESSION_SECRET` for you.

## Run it on a server

The cheapest way, and the most yours: a small server you rent online
(often called a VPS), running Docker. You'll type a few commands, over a
terminal connection to the server.

### Get a server

**What it costs:** a small monthly fee for the smallest plan, which runs
Soloblog comfortably - 1 CPU and 1 GB of memory is plenty. Google Cloud
and Oracle Cloud have always-free servers, with limits that can change.
Everything else here - Docker, Soloblog, the HTTPS proxy - is free. Choose one near your readers, with Ubuntu or
Debian, then follow [With Docker Compose](#with-docker-compose).

| Provider | Worth knowing |
|---|---|
| [Hetzner](https://www.hetzner.com/cloud) | Very good value; data centres in Germany, Finland, the US and Singapore. |
| [DigitalOcean](https://www.awin1.com/cread.php?awinmid=123996&awinaffid=3158224) | Simple dashboard and excellent tutorials; Droplets in many regions. Email goes through [Resend](#send-email-from-your-host). |
| [Vultr](https://www.vultr.com/?ref=9936472-9J) | Many locations worldwide, hourly billing. |
| [Linode (Akamai)](https://www.linode.com) | Long-running, straightforward pricing, good support. |
| [Hostinger VPS](https://www.hostinger.com/vps-hosting) | Budget plans with a friendly panel; also sells domains. |
| [OVHcloud](https://www.ovhcloud.com/en/vps/) | Low-cost VPS, strong in Europe and Canada. |
| [Contabo](https://contabo.com) | A lot of memory and disk for the price. |
| [Amazon Lightsail](https://aws.amazon.com/lightsail/) | AWS with a fixed monthly price; handy if you already use AWS. |
| [Google Cloud](https://cloud.google.com/free) | A small always-free VM in some US regions. |
| [Oracle Cloud](https://www.oracle.com/cloud/free/) | An always-free ARM server, generous but sometimes out of capacity. |

### With Docker Compose

On your server, or any computer with Docker:

1. Fetch the two files and fill in your URL:

   ```bash
   curl -O https://raw.githubusercontent.com/soloblog/soloblog/master/docker-compose.yml
   curl -o .env https://raw.githubusercontent.com/soloblog/soloblog/master/.env.example
   # edit .env: BASE_URL, your site's URL
   ```

2. Start it, and find your setup token:

   ```bash
   docker compose up -d
   docker compose logs soloblog | grep setup
   ```

3. [Put HTTPS in front](#put-https-in-front) before you share the URL.

Your data is in the `soloblog-data` volume. To keep it in a folder
instead, use `- ./data:/data` in `docker-compose.yml`.

**Want a copy of the whole folder?** With the site running:

```bash
docker run --rm -v soloblog-data:/data -v "$PWD":/backup alpine \
  tar czf /backup/soloblog-$(date +%F).tgz -C /data .
```

Keep it private: it holds your readers' email addresses and your keys.

### With Docker alone

```bash
docker volume create soloblog-data
docker run -d --name soloblog --restart unless-stopped \
  -p 8080:8080 -v soloblog-data:/data \
  -e BASE_URL=https://blog.example.com \
  ghcr.io/soloblog/soloblog:latest
```

Images are published for `linux/amd64` and `linux/arm64`:

| Tag | Tracks |
|---|---|
| `:latest` | the newest release - it only moves when a version comes out |
| `:1.0.0-beta` | one release, never changes |
| `:edge` | the next version, still being built - to try it, not for a real blog |
| `:sha-<commit>` | one exact build |

**Keeping a site on one version?** Run a version's tag (`:1.0.0-beta`)
instead of `:latest`. With Watchtower, also give the Soloblog container
the label `com.centurylinklabs.watchtower.enable=false`.

**Building it yourself?** `docker build -t soloblog .` The image's labels
(`org.opencontainers.image.*`) say what it is, for registries and tools
like Watchtower.

### Without Docker

With Python 3.12 or newer:

```bash
sudo useradd --system --home /opt/soloblog soloblog
sudo git clone https://github.com/soloblog/soloblog /opt/soloblog && cd /opt/soloblog
sudo python3 -m venv .venv && sudo .venv/bin/pip install -r requirements.txt
sudo .venv/bin/daisyft init --defaults --binaries --force && sudo .venv/bin/daisyft build   # the CSS; no Node.js
sudo mkdir -p /var/lib/soloblog && sudo chown soloblog /var/lib/soloblog
echo "BASE_URL=https://blog.example.com" | sudo tee /etc/soloblog.env
sudo cp deploy/soloblog.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now soloblog
journalctl -u soloblog | grep setup
```

### On Kubernetes

[`deploy/kubernetes.yaml`](../deploy/kubernetes.yaml) has one replica
with the `Recreate` strategy, a persistent volume, a Service and an
Ingress.

## Run it at home

Run Soloblog on a home server, a NAS or a Raspberry Pi. **It costs
nothing** beyond the computer and its electricity - and a Cloudflare
Tunnel to reach it is free.

- **Unraid, TrueNAS SCALE, CasaOS, Synology Container Manager, QNAP:** add
  a container from `ghcr.io/soloblog/soloblog:latest`, map a folder to
  `/data`, and publish port `8080`.
- **Portainer:** open **Stacks > Add stack**, paste `docker-compose.yml`,
  and add the variables.
- **Raspberry Pi:** the arm64 image runs on a Pi 3, 4 or 5 with a 64-bit
  system. Use [Docker Compose](#with-docker-compose).

**Want people outside your home to reach it?** Use a
[Cloudflare Tunnel](#cloudflare-tunnel) or Tailscale Funnel. Both connect
your site to the internet safely, without changing your router's
settings.

## Use a custom domain

Give your site a domain of its own, like `yourname.com`. Move hosts
whenever you like, and every link still works.

**What it costs:** a yearly fee to the registrar. Many charge little for
the first year and more after - check the renewal price, not only the
first.

1. Buy a domain at any registrar - these are well liked for fair prices
   and free privacy protection:

   | Registrar | Worth knowing |
   |---|---|
   | [Cloudflare Registrar](https://www.cloudflare.com/products/registrar/) | Sells at cost with no markup. Needs Cloudflare as your DNS, which pairs well with [Cloudflare](#use-cloudflare). |
   | [Porkbun](https://porkbun.com) | Low prices, free WHOIS privacy and SSL, a clear dashboard. |
   | [Namecheap](https://www.namecheap.com) | Long-running, easy DNS settings, frequent first-year discounts. |
   | [Spaceship](https://www.spaceship.com) | Low prices and a modern dashboard, from Namecheap's founders. |
   | [GoDaddy](https://www.godaddy.com) | The biggest registrar; cheap first years, higher renewals - check the renewal price. |
   | [Squarespace Domains](https://domains.squarespace.com) | Where Google Domains moved; simple, privacy included. |
   | [Hostinger](https://www.hostinger.com/domain-name-search) | Budget domains, often bundled with its hosting. |
   | [IONOS](https://www.ionos.com/domains) | Cheap first years in Europe and the US. |
   | [Dynadot](https://www.dynadot.com) | Plain pricing and a wide choice of endings. |
   | [Gandi](https://www.gandi.net) | Long-standing European registrar, privacy by default. |
   | [Name.com](https://www.name.com) | Straightforward, with good DNS tools. |

2. Add the domain to your host, in its settings. Most hosts then show you
   the exact DNS record to add - a line that points your domain at the
   host.
3. Where your domain's settings are managed (usually the registrar, or
   Cloudflare), add that record: a CNAME record for a name like
   `blog.example.com`, or an A record for `example.com` itself.
4. Wait until your site opens at `https://` on the domain - it can take
   from a few minutes to a few hours. Then open setup there, so the site
   takes the domain as its URL.

**Already set up at another URL?** Change it in **Settings > URL and
SEO** - or `BASE_URL`, if you set that on your host.

**Using passkeys?** A passkey works only on the domain it was added on.
Add yours on the domain you'll keep.

## Put HTTPS in front

HTTPS is the secure `https://` connection browsers expect - without it,
they warn visitors, and logins aren't safe. Hosting services do this for
you. On your own server, a program called a reverse proxy sits in front
of Soloblog and adds HTTPS. Ready-made settings for the common ones are
in [`deploy/`](../deploy):

| Proxy | File | Notes |
|---|---|---|
| Caddy | [`Caddyfile`](../deploy/Caddyfile) | Gets certificates by itself. The simplest choice. |
| nginx | [`nginx.conf`](../deploy/nginx.conf) | Use certbot for certificates. |
| Apache | [`apache.conf`](../deploy/apache.conf) | Needs mod_proxy, mod_headers and mod_ssl. |
| Traefik | [`traefik-compose.yml`](../deploy/traefik-compose.yml) | Traefik and Soloblog in one Compose file. |
| Nginx Proxy Manager | none | Add a proxy host for `soloblog:8080`, request a certificate, and allow large uploads in Advanced (`client_max_body_size 110m;`). |

Whichever you use:

- **Keep the original `Host` header.** Fediverse servers sign it, and
  Soloblog checks requests against it. Caddy and Traefik do this by
  themselves; nginx needs `proxy_set_header Host $host;` and Apache
  `ProxyPreserveHost On`.
- **Pass `X-Forwarded-Proto` through,** so Soloblog knows the page came
  over HTTPS - passkeys need it.
- **Allow uploads of about 110 MB** if you upload audio or video.
- **Visitors' IP addresses:** Soloblog reads them from the last
  `X-Forwarded-For` entry, which is right for one proxy - and only when
  the proxy reaches Soloblog from a private IP address (the same machine,
  Docker's network, a host's internal network); from anywhere else the
  header is ignored, since a visitor could write it. With more than one
  proxy (a CDN in front of yours), or one that connects from a public
  IP address, set `CLIENT_IP_HEADER`.
  With no proxy at all in front, set `TRUSTED_PROXY=none`
  ([Settings on the host](#settings-on-the-host)).
- **Open setup at the `https://` URL,** so the site takes it as its
  own - or set `BASE_URL`.

## Use Cloudflare

### As the DNS and CDN

With the orange cloud (proxied) on for your blog's DNS record:

- **SSL/TLS mode: Full (strict)** once your server has a real certificate
  (Caddy, certbot), or **Full** with a self-signed one. Never Flexible:
  logins would travel unencrypted between Cloudflare and your server.
- **Set `CLIENT_IP_HEADER=CF-Connecting-IP`,** so login limits count
  visitors, not Cloudflare. Only if your server accepts traffic from
  Cloudflare alone - otherwise the header can be faked.
- **Caching:** Soloblog already tells Cloudflare to keep `/static/`,
  `/uploads/` and `/app.js`. Don't add a "cache everything" rule: pages
  differ for you when you're logged in, and the admin must never be
  cached. If you add cache rules, bypass the cache for `/admin*`,
  `/login*`, `/ap/*`, `/.well-known/*` and `/webmention`.
- **Turn off Rocket Loader** (**Speed > Optimization**) - it can break the
  editor. Auto Minify isn't needed.
- **Bot Fight Mode** can block fediverse servers sending to `/ap/inbox`.
  If follows don't arrive, add a WAF skip rule for `/ap/inbox` and
  `/.well-known/*`.

### Cloudflare Tunnel

Make a site running at home reachable from the internet, without
changing your router's settings or opening ports on it.

1. In Cloudflare, create a tunnel under **Zero Trust > Networks >
   Tunnels**.
2. Put its token in `.env` as `TUNNEL_TOKEN`.
3. Start [`deploy/cloudflare-tunnel-compose.yml`](../deploy/cloudflare-tunnel-compose.yml),
   which runs Soloblog and `cloudflared` together.
4. Point a public hostname at `http://soloblog:8080`.

### Other Cloudflare pieces

- **R2** for [cloud storage](#keep-files-in-cloud-storage): no fees
  for downloads.
- **Web Analytics:** privacy-friendly, set in **Settings > Analytics and
  ads**.
- **Pages and Workers can't host Soloblog** - it needs a server that
  keeps running, and a disk.

## Make the fediverse work

Let people on Mastodon and the rest of the fediverse follow your blog -
switched on in **Settings > Sharing > Fediverse**. Your host needs:

- your site's URL (**Settings > URL and SEO**, or `BASE_URL`) set
  to your public `https://` URL, on the domain you'll keep - your
  followers are tied to it;
- the original `Host` header passed through your proxy;
- `/.well-known/webfinger`, `/ap/*` and `/webmention` open to other
  servers - check any bot protection on your CDN or firewall.

**Does it work?** From a Mastodon account, search for `@blog@your.domain`
and follow it.

## Open setup the first time

The first time Soloblog starts, there's no account yet. Open `/setup` on
your site, enter the **setup token**, and choose your password.

**Where's the token?**

- **One you choose:** set the `SETUP_TOKEN` variable to 16 characters or
  more, with your host's other variables. Nothing to look up.
- **Or the one in the log:** without `SETUP_TOKEN`, Soloblog writes a new
  token to its log each time it starts - look for the line with
  `[setup]`. It's also in `setup-token.txt` in the data folder, for a
  host where you can reach the files but not the log.

Either stops working once your account exists. Setup then shows your
**recovery key**, once: it resets your password if you forget it. Keep
it in a password manager, or print it.

Without `BASE_URL`, setup keeps the URL you opened it at as your
site's URL - change it later in **Settings > URL and SEO**.

Then the guide takes over: [Getting started](guide/getting-started.md).

## Keep files in cloud storage

A bucket is online storage you rent by how much you keep in it. With
one connected, Soloblog keeps a copy of everything there - your images,
and backups made for you - so you never lose your site, even on a host
with no lasting storage. Amazon S3, Cloudflare R2, Backblaze B2, MinIO,
Wasabi and others that work like S3 all do.

**What it costs:** storage is charged by how much you keep, and a blog's
is small. Most of it is your images - each kept once - while backups are
small, because they leave the images out. Visitors never download from
the bucket: your server shows them your images, and fetches one from
the bucket only when its own copy is missing. Cloudflare R2 and Backblaze
B2 have free allowances a blog often fits in; check each one's terms.

With it on:

- **Your images** are kept in the bucket as they change.
- **It all happens in the background:** saving a post or uploading an
  image never waits for the bucket, and a slow or unreachable bucket
  doesn't slow your site - it catches up later.
- **Backups are made for you** about a minute after you change something,
  or once a day or once a week if you'd rather. The newest 30 are kept.
  Change both in **Settings > Backup and import > Cloud storage** - see
  [Back up and restore](guide/run.md#back-up-and-restore).
- **An empty disk restores itself** from the newest backup when Soloblog
  starts - your login, settings and images too - so hosts without a disk
  work. On one, set `SESSION_SECRET` too, or every deploy logs you out -
  see [Hosts without a disk](#hosts-without-a-disk). A change in the last minute before a crash can be lost; a normal
  restart saves it first.
- **Settings > Backup and import > Cloud storage** shows the last backup,
  lists recent ones to restore, and has **Back up now** and **Sync
  images**.

To set it up:

1. At the storage company, make a private bucket, and an access key for
   that bucket only. On Backblaze, also open the bucket's **Lifecycle
   Settings** and choose **Keep only the last version of the file** -
   otherwise it keeps every earlier copy of each image and backup, and
   you pay to store them all.
2. Set these on your host, where its settings or environment variables
   are. **All five are needed:**

   | Variable | What to put |
   |---|---|
   | `S3_BUCKET` | Your bucket's name, exactly as your storage company shows it - capital letters too. For a bucket called `My-Blog-Backups`, that's `My-Blog-Backups`. |
   | `S3_ENDPOINT` | Your bucket's S3 endpoint URL, copied from your storage company - it's different for each account and region, so don't copy the examples. Backblaze shows it as **Endpoint** on the bucket's page, like `s3.us-west-004.backblazeb2.com` (with or without `https://`). Cloudflare R2 shows it on the bucket's settings, like `https://<account-id>.r2.cloudflarestorage.com`. DigitalOcean Spaces: the region's address, like `https://nyc3.digitaloceanspaces.com` - not the bucket's own, which starts with its name. Amazon S3: leave it out. |
   | `S3_REGION` | The bucket's region. Backblaze: the middle of its endpoint - `us-west-004` in the example above. Cloudflare R2: `auto`. DigitalOcean Spaces: the region in its endpoint, like `nyc3`. Amazon S3: the region you chose, like `eu-west-1`. |
   | `S3_ACCESS_KEY_ID` | The ID of an access key for this bucket. Backblaze calls it **keyID**; DigitalOcean, the **Access Key**. |
   | `S3_SECRET_ACCESS_KEY` | That key's secret. Backblaze calls it **applicationKey**, and shows it only once, when the key is made - copy it then. |

   **These are optional** - leave them out for what each one does by
   itself:

   | Variable | What it does | Left out |
   |---|---|---|
   | `S3_PREFIX` | A folder inside the bucket for this site's files, like `my-blog`. Needed only if the bucket holds anything else, or two sites share it. | Files go at the top of the bucket |
   | `S3_BACKUP_KEEP` | How many backups to keep to start with. Change it later in **Settings > Backup and import**. | `30` |
   | `S3_AUTO_BACKUP` | `0` turns off automatic backups. Images are still copied. | Automatic backups on |
   | `S3_RESTORE_ON_BOOT` | `0` stops a site that starts on an empty disk from restoring itself from the bucket. | Restoring on |
   | `BACKUP_PASSPHRASE` | Locks every backup and image in the bucket. [Read this first](#lock-the-bucket-with-a-passphrase). | Not locked |

3. Restart Soloblog. **Settings > Backup and import > Cloud storage**
   shows which are set.

**Keep the bucket private** - backups hold your whole site, keys
included. It never needs to be public.

### Lock the bucket with a passphrase

> **Save the passphrase in a password manager before you set it.** Once
> it's set, the images and backups in your bucket are replaced by locked
> copies. Without the passphrase they can't be opened - not by you,
> Soloblog or your storage company - and a new server can't get your site
> back from the bucket.

Set `BACKUP_PASSPHRASE`, and backups and images are encrypted, so
someone who gets into the bucket - or the storage company itself -
still can't open them. Images already there are encrypted the next time
Soloblog starts. Restoring needs the same passphrase. Change or remove
it later and your images are copied again the new way when Soloblog
restarts - but older backups still need the passphrase they were made
with, and restoring one asks for it. On a host without a disk, the
restart after a change can't open the newest backup, so the site asks
for the old passphrase before anything else - see
[Your site shows "Restore your site"](guide/troubleshooting.md#your-site-shows-restore-your-site).

### What's in the bucket

| | What's kept | Encrypted |
|---|---|---|
| Your images | One copy of each, the latest. A trashed image moves to a trash folder, and is deleted when you empty the trash | With `BACKUP_PASSPHRASE` |
| Backups | Your posts, settings and the rest you choose - not images | With `BACKUP_PASSPHRASE` |

In the bucket, inside the folder `S3_PREFIX` names (or at the top, without one):

| Folder | What's in it |
|---|---|
| `uploads/` | Your images, each under its own name |
| `uploads/_trash/` | Images in the trash |
| `backups/` | One file per backup, named by date and time: `soloblog-20261119-154700.zip`, or `.zip.enc` when it's encrypted. Each is the same zip as a download, without `uploads/` - see [Back up and restore](guide/run.md#back-up-and-restore) for what's inside |

Two sites can share one bucket with a different `S3_PREFIX` each. Each
only reads, backs up to and clears its own folder.

**Who can see your images there?** Without `BACKUP_PASSPHRASE`, anyone
with the bucket's access key, and the storage company. Published images
are on your site for anyone anyway - this matters for images in drafts
and members-only posts. Set the passphrase to lock them, keep the bucket
private, and keep its key only on your host.

**Images have no history.** Rotating or cropping an image replaces its
copy, and an image deleted for good is gone - so restoring an old backup
restores its posts, but not an image deleted since. Want older
versions kept? Some storage companies can keep them for you: Amazon S3
calls it versioning, and Backblaze B2 keeps old versions unless you tell
it not to. Each old version is stored, and charged, as well.

## Update to a new version

When a new version is out, the admin says so. Your posts, images and
settings stay as they are, and the database upgrades itself.

1. While Soloblog is in beta, download a backup first in **Settings >
   Backup and import**.
2. Update the way you installed it:

   | Installed with | Update by |
   |---|---|
   | Docker Compose | `docker compose pull && docker compose up -d` in its folder |
   | Docker alone | `docker pull ghcr.io/soloblog/soloblog`, then remove and re-run the container with the same `/data` volume |
   | A hosting service (Render, Railway, Fly.io, Koyeb, DigitalOcean and more) | Redeploy the service - most have a "Deploy latest" button, or redeploy on each new release |
   | Coolify, CapRover, Dokku | Redeploy the app from its dashboard |
   | Unraid, TrueNAS, Synology, CasaOS, Portainer | "Update" or "Pull and redeploy" on the container |
   | Without Docker (systemd) | `git pull`, `pip install -r requirements.txt`, `daisyft build` (the new version's styles), then restart the service |

3. Check the version number at the bottom of any admin page - it's the
   new one.

**Going back?** Restore the backup from step 1 into the older version.

**Don't want Soloblog to check for new versions?** Set `UPDATE_CHECK=0`.

### Set up the Update now button

Set up an **update hook** once, and the admin offers **Update now**:
Soloblog asks whatever runs it to fetch the new version and restart.

**With Docker Compose, using Watchtower.** [Watchtower](https://github.com/nicholas-fedor/watchtower)
(the maintained fork) updates containers when asked:

1. In `docker-compose.yml`, uncomment the `watchtower` service. The
   `com.centurylinklabs.watchtower.enable` label on Soloblog, and
   `WATCHTOWER_LABEL_ENABLE`, keep it to this one container.
2. In `.env`, set `WATCHTOWER_HTTP_API_TOKEN` to a long random string
   (`openssl rand -hex 32`).
3. Run `docker compose up -d`.
4. In **Settings > Integrations**, select **Edit** beside **Updates**.
   Set **Update hook** to
   `http://watchtower:8080/v1/update` and **Token** to the same string.

Watchtower can reach the Docker socket, so don't publish its port - the
setup above keeps it on the private network between the two containers.

**On a hosting service with deploy hooks.** Render (**Settings > Deploy
Hook**), Coolify (the app's Webhooks), CapRover (**App Configs >
Deployment**) and others give each app a secret URL that starts a
new deploy.

1. In **Settings > Integrations**, select **Edit** beside **Updates**,
   and paste that URL into **Update hook**.
2. Leave **Token** empty - or put the host's API token there, if its hook
   wants one as a Bearer token.
3. Make sure the app deploys from `:latest` (or the branch), so it picks
   up the new version.

## Move to a new server or domain

Move your site to another host, a new server, or your own domain. How
you do it depends on whether your site keeps its files in
[cloud storage](#keep-files-in-cloud-storage).

**With cloud storage**, the new site restores itself:

1. On the old site, open **Settings > Backup and import > Cloud
   storage** and select **Back up now**, so the newest backup has
   everything.
2. Start Soloblog on the new host with the same `S3_` settings, and the
   same `BACKUP_PASSPHRASE` if you lock your backups with one.
3. Open the new site. When it starts on an empty disk, it restores
   itself from the newest backup in your bucket - posts, settings,
   comments, members and your login - and brings your images back from
   the bucket. Log in with your usual password.
4. Stop the old site, so the two don't both make backups in the same
   bucket.

If it can't restore itself, opening the new site shows **Restore your
site** instead of setting up a new one. Each asks for the setup token,
which is in your host's log on the lines marked `[setup]`, or the
`SETUP_TOKEN` you chose:

- **Locked with another passphrase** - the backup was made with a
  different `BACKUP_PASSPHRASE`. Type the one it was made with.
- **The bucket didn't answer** - check the `S3_` settings on your host,
  then select **Try again**.
- **The newest backup couldn't be opened** - choose an earlier one from
  the list.

**Start a new site instead** sets up an empty site. Your bucket's backups
stay there, but each new backup replaces the oldest, as usual. To always
start empty, set `S3_RESTORE_ON_BOOT` to `0` on the new host.

**With a downloaded backup:**

1. On the old site, open **Settings > Backup and import** and select
   **Download** with everything selected.
2. Start Soloblog on the new server and open `/setup` there. Select
   **Moving your site? Restore a backup**.
3. Enter the **Setup token**, choose the backup under **Backup**, and
   type its **Passphrase** if it's locked with one. Select **Restore**.
4. Everything in the backup comes back - posts, images, settings and
   your login. Log in with your old password.

**Copying the whole `/data` folder instead?** Start the new server with
it, and skip setup.

**Domain changing too?** Change the URL in **Settings > URL and SEO**
(or `BASE_URL`, if you set it on your host).

**Using passkeys?** They belong to the domain they were added on. Log in
with your password and add them again on the new one.

**Followers in the fediverse?** They stay with the old domain. Tell them
your new handle.

## Run a public demo

Run Soloblog as a public demo: a sample blog (Mira Castell's - every
layout, pages, comments, stats) that anyone can browse and log into,
with a password shown on the page. It's what the project's own demo
runs.

```bash
docker run -d --name soloblog-demo --restart unless-stopped -p 8080:8080 \
  -e DEMO_MODE=1 -e SESSION_SECRET="$(openssl rand -hex 32)" \
  -e BASE_URL=https://demo.example.com \
  -v soloblog-demo:/data ghcr.io/soloblog/soloblog:latest
```

| Variable | Default | What it does |
|---|---|---|
| `DEMO_MODE` | off | `1` turns the demo on. |
| `DEMO_PASSWORD` | `demo` | The admin password, shown on the site. |
| `DEMO_RESET_HOURS` | `3` | How often it starts afresh. |
| `DEMO_CACHE` | `demo-cache` in `/data` | Where the sample photos are kept between resets. |

**How it behaves:**

- **On every start** it empties the data folder (except the photo cache)
  and builds the sample blog again. The first start downloads its 36
  photos - openly licensed, credited - which takes a minute.
- **It resets** by stopping after `DEMO_RESET_HOURS`, so the host must
  start it again: `--restart unless-stopped` with Docker; Render, Railway
  and Fly.io do it by themselves.
- **A note** floats in a corner of every page: it's a demo, the password,
  and when it next starts afresh, with a ✕ that puts it away on that
  page. Search engines are asked not to list it.
- **Each visitor's changes are theirs alone.** The first time someone
  changes anything, or opens the admin, they get a copy of the sample
  site of their own (about 7 MB), and everything they write, upload or
  set goes into it: no one else sees it, so there's nothing to deface.
  Up to 30 copies are kept, the longest unused removed first, and all of
  them go at the reset.
- **Switched off**, since they'd reach past the visitor's copy: changing
  the password, two-factor and passkeys, **Settings > Integrations**,
  backups, restores and imports, sending the newsletter, translation, the
  broken-link checker and **Update now**. Custom code, analytics, ads,
  outside comment systems and fediverse or webmention sending are kept
  out of saved settings. Uploads are capped at 5 MB.
- **It won't touch a real blog.** Demo mode only ever empties a data
  folder it made itself: pointed at one with a blog in it, it stops with
  an error instead.

**Trying it on your own computer, without Docker?** Run
`python tools/demo.py demo-data`, then `DATA_DIR=demo-data python app.py` -
a copy that doesn't reset, with the password `demo`.

## Settings on the host

Almost all of Soloblog's settings are in the admin. These few are set
on your host instead, as environment variables - named settings you add
in your host's dashboard, or in the `.env` file with Docker Compose.
None of these settings is required. In the admin, **Settings >
Integrations**, under **Advanced**, shows which are set.

| Variable | Default | What it's for |
|---|---|---|
| `SESSION_SECRET` | made on the first start, kept in `/data/.session_secret` | Signs logins. Set your own (`python3 -c "import secrets; print(secrets.token_hex(32))"`) if you like - it wins. |
| `SETUP_TOKEN` | none | A first-login token you choose, 16 characters or more, instead of the one in the log. Only used until your account exists. |
| `BASE_URL` | the URL first-time setup was opened at; before that, the host's own on Render, Railway and Fly | Your public URL, e.g. `https://blog.example.com`, used in feeds, the sitemap, links in emails and the fediverse. Without it, change the address in **Settings > Address and search**; set here, it wins and Settings can't change it. |
| `DATA_DIR` | `/data` in the image | Where data is stored. |
| `PORT` | `8080` in the image | The port to listen on. Hosts that set `PORT` themselves are respected. |
| `HOSTED_ON` | set by Soloblog's app-store packages (Umbrel, Unraid, Coolify...) | The platform's name, so first-time setup can say where it shows the setup token. Leave it out anywhere else. |
| `SITE_TITLE` | `My Blog` | The first title only; change it later in **Settings > Name and homepage**. |
| `SESSION_DAYS` | `14` | How long a login lasts unused. |
| `UPDATE_CHECK` | `1` | `0` stops Soloblog asking GitHub, once a day, whether a newer release is out. |
| `LOG_LEVEL` | `INFO` | How much goes in the server's log: `WARNING` for problems only, `DEBUG` for everything. Site health's detailed log keeps its own, whatever this says. |
| `RESET_PASSWORD` | unset | `1` writes a one-time password reset link to the log on start. Remove it again afterwards. |
| `MAX_MEDIA_MB` | `100` | The largest audio or video upload. |
| `CLIENT_IP_HEADER` | none | A header your proxy sets to the visitor's IP address, e.g. `CF-Connecting-IP` behind [Cloudflare](#use-cloudflare). |
| `TRUSTED_PROXY` | none | Whose word counts for a visitor's IP address (`X-Forwarded-For` and `CLIENT_IP_HEADER`). Unset, any caller on a private network is believed - right when a proxy on the same machine or network is in front. With no proxy in front (the container's port open to the internet), set `none`, or a visitor can dodge the login limit by sending the header themselves. Or list your proxy's addresses or networks, with commas: `10.0.0.2, 172.18.0.0/16`. |
| `SMTP_HOST` | none | Your email provider's SMTP server, e.g. `smtp.fastmail.com`: your site sends its email through it until you set up email in **Settings > Email**, where what you save wins. |
| `SMTP_PORT` | `587` | The server's port: `587`, or `465`. |
| `SMTP_USER` | none | The username for the server - usually your email address. |
| `SMTP_PASSWORD` | none | The password for the server. Most providers want an app password: a separate password for your site, made in your account's security settings. Never shown in the admin. |
| `SMTP_FROM` | none | The address your email comes from, e.g. `hello@example.com`. |
| `RESEND_API_KEY` | none | A [Resend](https://resend.com) API key, for a host that blocks SMTP. On its own, your site sends through Resend; with `SMTP_HOST` set too, Resend takes over whenever SMTP fails. Never shown in the admin. |
| `RESEND_FROM` | none | The address Resend sends from, at a domain you verified there, e.g. `hello@example.com`. Needed with `RESEND_API_KEY`. |
| `ADMIN_EMAIL` | none | Your email address, for password resets and sign-in alerts, until you set one in **Settings > Email**. |
| `S3_*` | none | [Cloud storage](#keep-files-in-cloud-storage) for images and automatic backups. |
| `ENV` | `production` in the image | `development` turns on auto-reload, for working on the code. A site whose `BASE_URL` starts with `https://` always runs as `production`. |

## Send email from your host

Your site sends email - password resets, sign-in alerts, comment
confirmations, the newsletter. You can set it up in **Settings > Email**
after setup, or with settings on your host, so it works from the first
start. There are two ways:

- **Resend** - an email service that sends over HTTPS, so it works on
  every host, even one that blocks email ports. It needs a domain of
  your own. Set `RESEND_API_KEY` and `RESEND_FROM`. The admin recommends
  it for that reason.
- **SMTP** - the standard way email apps send. It works with an email
  account you already have (Gmail, iCloud, Fastmail, Yahoo, Proton -
  with an app password) or a sending service (Brevo, Mailgun, Postmark,
  Amazon SES, or Resend's own SMTP), so nothing ties you to one company.
  Set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` and
  `SMTP_FROM`.

Both are in [Settings on the host](#settings-on-the-host). Set both, and
Resend takes over whenever SMTP fails.

**Hosts and SMTP:** many hosts close SMTP's ports (25, 465 and 587) to
stop spam, and email sent that way never leaves. Where each one stands:

| Host | SMTP |
|---|---|
| Render | Blocked on free instances since September 2025. Soloblog needs a paid instance anyway, which can use SMTP; if email doesn't arrive, use Resend. |
| Railway | Only on the Pro plan and up. On Hobby or a trial, use Resend. |
| Fly.io | Works on port 587. Some email providers refuse email from Fly's shared addresses; a sending service, or Resend, avoids that. |
| DigitalOcean (App Platform and Droplets) | Closed by default, to keep spam off its network. Use Resend, or ask DigitalOcean's support to open it for your account. |
| Your own server elsewhere | Usually works on 587 or 465; port 25 is often blocked, and Soloblog doesn't use it. |

**Check it works:** in **Settings > Email**, select **Send a test email**.
If it doesn't arrive, it says why. Values set on your host show there as
**Set on your host**.

## Troubleshooting

| Problem | Fix |
|---|---|
| Can't find the setup token | It's in the logs until your account exists, and restarting writes a new one. Or set `SETUP_TOKEN` to one you choose (16 characters or more) and restart. |
| Posts disappear after a redeploy | No lasting storage at `/data`: add a disk or volume there, or connect [cloud storage](#keep-files-in-cloud-storage). |
| "Cross-site request refused" when saving | Your proxy changes the `Host` header, or your site's URL doesn't match the one you're using. |
| Links in feeds say localhost | Set your URL in **Settings > URL and SEO**. |
| Uploads fail for large files | Raise your proxy's upload limit - see [Put HTTPS in front](#put-https-in-front). |
| Everyone shares one login limit (people get "too many tries" they didn't make) | Several proxies in a row: set `CLIENT_IP_HEADER`. (On Fly.io, the visitor's address comes from Fly's own `Fly-Client-IP` by itself.) |
| Fediverse follows don't arrive | The site URL isn't public `https://`, the `Host` header is rewritten, or a firewall blocks `/ap/inbox`. |
| A passkey doesn't work after moving | Passkeys belong to the domain they were added on. Log in with your password and add it again. |

More, about using the site itself: [Troubleshooting](guide/troubleshooting.md).
