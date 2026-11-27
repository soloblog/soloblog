# Maintaining Soloblog

How the project is run: where feedback goes, how releases happen, and
what the software depends on. For how the code is organised, see
[DEVELOPMENT.md](DEVELOPMENT.md); for the reasons behind big choices,
[DECISIONS.md](DECISIONS.md).

**Contents:** [Where feedback goes](#where-feedback-goes) · [Triage](#triage) ·
[Security](#security) · [Branches and pull requests](#branches-and-pull-requests) · [Releases](#releases) · [Updates that never break a site](#updates-that-never-break-a-site) ·
[Dependencies and their risks](#dependencies-and-their-risks) · [The demo](#the-demo) · [The website](#the-website) ·
[Keeping the project going](#keeping-the-project-going)

## Where feedback goes

Everything lives on GitHub, so there's one place to look and one login:

| For | Where | Links |
|---|---|---|
| Something broken | **Issues**, "Bug report" form | `github.com/soloblog/soloblog/issues/new/choose` - also **Report a problem** in the admin |
| An idea or a wish | **Discussions > Ideas** | people upvote with 👍; a good one becomes an issue |
| A question | **Discussions > Q&A** | an answer that keeps coming up goes into the [FAQ](FAQ.md) |
| Showing a site | **Discussions > Show and tell** | |
| News | **Discussions > Announcements** | one per release |
| A security problem | **Security > Report a vulnerability** (private) | never an issue - see [SECURITY.md](../SECURITY.md) |
| What's coming | **Projects > Roadmap** board (until it exists: [ROADMAP.md](ROADMAP.md)) | columns: Ideas · Planned · In progress · Done |
| What shipped | [CHANGELOG.md](../CHANGELOG.md) and GitHub Releases | |

**The path of an idea:** a Discussion (Ideas) → if it fits
[the direction](DECISIONS.md), an issue with the `enhancement` label →
on the board under *Planned* with a target release → *In progress* when
work starts → *Done* and a changelog line when it ships. The Discussion
gets a reply with the outcome either way; a "no" says why and links the
decision.

**Keeping it small, and nobody left wondering** (DECISIONS: Community):

- **One place.** No chat server and no forum of our own:
  Discussions is the forum. An answer given twice goes into the
  [FAQ](FAQ.md).
- **Say what to expect.** [SUPPORT.md](../SUPPORT.md) - GitHub shows it
  when someone opens an issue - gives where to ask what, which versions
  get fixes, and how soon things are read.
- **No stale bot.** Only `needs info` issues close on their own, after
  30 days without a reply (Triage).
- **Saved replies** (GitHub > Settings > Saved replies) for the answers
  given most - a click each (listed under Repository settings).
- **If it ever gets too busy** - a flood after a launch, or spam - the
  repository's Settings > Moderation options > **Interaction limits**
  limits issues, comments and pull requests to past contributors (or
  collaborators only) for 24 hours up to 6 months. Use it, say why in a
  pinned Discussion, and lift it when things calm down.
- **Show it's alive where people look:** a post on the project website's
  blog for each release, copied as the Announcement. The website runs
  Soloblog, so the same post reaches its newsletter, RSS, fediverse
  followers and Bluesky and Mastodon with no extra work. In the admin,
  **What's new** after an update does the same for people who never
  visit GitHub.
- **Measure without telemetry:** stars, Docker image pulls and app-store
  listings. Nothing about anyone's site is ever reported to us - the
  update check asks GitHub, and sends nothing about the site.

### Repository settings

- **Discussions** categories: Q&A, Ideas (with voting), Show and tell,
  Announcements (maintainers post).
- **Projects > Roadmap**, a public board with columns Ideas · Planned ·
  In progress · Done. Issues labelled `enhancement` are added to it, and
  closed ones move to Done.
- **Labels:** `bug`, `enhancement`, `question`, `docs`,
  `good first issue`, `needs info`, `wontfix`, `security`,
  `dependencies`, alongside GitHub's own.
- **Security:** private vulnerability reporting, Dependabot alerts and
  security updates are on.
- **A branch ruleset** for `master` and the version branches (the
  pattern `[0-9]*.[0-9]*`): no deletions and no force pushes, for
  anyone, admins included. It requires no checks, since CI runs only on
  pull requests, tags and by hand: CI is the gate on a pull request, and
  the local checks (CLAUDE.md > Every change) are the gate before a
  maintainer's push.
- **Pull requests from first-time contributors** wait for approval before
  CI runs. The workflows use `pull_request`, never
  `pull_request_target`, so a fork's run never sees the repository's
  secrets - keep it that way.
- **Saved replies** for the common answers:
  - **Low-effort pull request:** "Thanks for this. It doesn't follow how
    the project works - CLAUDE.md and CONTRIBUTING.md - so I'm closing
    it. A smaller change that does is welcome."
  - **A feature during the beta:** "Thanks - while Soloblog is in beta,
    new features start as a Discussion under Ideas, so others can weigh
    in. Could you post it there?"
  - **Needs info:** "Thanks for the report. Could you add your version
    (bottom of any admin page), how you host Soloblog, and the steps
    that show the problem?"
  - **Duplicate:** "Thanks - this is the same as #N, so I'm closing this
    one. Follow that issue for updates."
- **After a release with known bugs:** a pinned issue "Known issues in
  X.Y.Z", with each confirmed bug added as it comes in, unpinned when the
  fix release is out.

## Triage

Triage is reading what's come in and deciding what happens to each thing.
On GitHub, **Issues** is the list of bugs and planned work; each issue
gets a label (what kind of thing it is) and, if it's going to be done, a
place on the roadmap board. Once a week:

- **New issues:** label them; ask for what's missing (`needs info`) - the
  bug form already asks for version, how it's hosted and steps. Close
  duplicates with a link. A `needs info` issue with no reply in 30 days
  can be closed.
- **Bugs first:** anything that loses data or breaks security goes into
  the next patch release. Others go on the board.
- **Ideas:** answer within a week or two, even if the answer is "later".
- **Dependabot:** review its pull requests (below).

## Security

Once the project is public, keeping people's sites safe comes before any
new feature.

- **Reports** come in privately through the repository's Security tab
  (see [SECURITY.md](../SECURITY.md)): acknowledge within 3 days, fix in a
  patch release, then publish the advisory with credit to the reporter.
- **Automatic checks** (`.github/workflows/security.yml`) on every release,
  every pull request and every Monday: `pip-audit` for known
  vulnerabilities in the pinned Python packages, and GitHub's CodeQL code
  scanning (once the repository is public - it's paid on a private one).
  Dependabot alerts cover the same advisories between runs.
- **A failing security check blocks the release.** Update the package in
  its own commit, run the tests, release a patch.
- **New code that takes input, stores files, sends requests or touches
  the login** gets a test for the abuse case too - a path with `..`, an
  address on the local network, a script in a field, a request from
  another site.

## Branches and pull requests

`master` is the latest release, and the next version is built on its
own branch, named after it:

```
master  ──●─────────────●──────●────   v1.0.0   v1.0.1   v1.1.0
           \           / fix   \
1.1         ●──●──●──●──●───────●──     (the next version)
              feat  feat
```

*Why:* people get Soloblog from `master` without a release in between -
the Render, DigitalOcean, Heroku and Railway buttons build its source,
and `:latest` is the image their servers pull. So `master` only ever
holds released code.

- **`master` = the latest release.** Protected (see Repository settings): never
  deleted or force pushed. It only changes when a
  version is released or a patch is made.
- **The next version's branch** - `1.1`, then `1.2` - is where features
  go. It's made from `master` the day the previous version comes out.
  Its image is `:edge`, to try it; the demo stays on releases.
- **Every change is a short-lived branch** off the version branch, named
  by kind: `feat/...`, `docs/...`, `chore/...` - a pull request into
  `1.1`, the template filled in and a changelog line under
  `[Unreleased]`. Tests, the smoke test and the security checks must
  pass. It's squash-merged (one commit per change, its message written as
  [CLAUDE.md](../CLAUDE.md#commit-messages) says) and the branch
  deleted. The maintainer has the last word on every merge.
- **A release:** the version branch is merged into `master` (a merge
  commit, so its history stays), `master` is tagged `v1.1.0`, and the
  next branch, `1.2`, starts from there
  ([DEVELOPMENT.md](DEVELOPMENT.md#releasing)).
- **A patch** (a bug in the released version): a `fix/...` branch off
  `master`, a pull request into `master`, tagged `v1.1.1` - then
  `master` is merged into the version branch, so the fix is in the next
  version too.
- **Security fixes** are patches made in the private fork GitHub creates
  for a security advisory, then the advisory is published (see
  [Security](#security)).
- **Dependabot** opens against `master`. A security update is a patch;
  anything else, change the pull request's base to the version branch.
- **Contributors** open pull requests against the version branch (the
  pull request template and CONTRIBUTING say which); one against
  `master` gets its base changed.
- **Only the latest release gets fixes** - no branches for older
  versions.
- **A tag publishes everything:** the Docker image (`:latest` and its
  version), a GitHub Release (made from the changelog) and the demo,
  redeployed by CI.
- **Milestones** (1.1, 1.2) on GitHub group the issues and pull requests
  planned for each version.
- **Migrations from then on** only ever add a new numbered file; a file
  that has shipped is never edited.

## Releases

- **Version numbers:** `MAJOR.MINOR.PATCH`. The first public release is
  `1.0.0-beta`; fixes before `1.0.0` are `1.0.0-beta.2`, `-beta.3`... A
  **patch** (1.0.1) is fixes only and safe to take without reading
  anything; a **minor** (1.1.0) adds features and may need a note in the
  changelog's "Upgrading" part; a **major** (2.0.0) only for a change
  that needs the person running the site to do something.
- **Cadence:** a minor release when there's something worth shipping - no
  dates are promised (DECISIONS: Community); a patch whenever a real bug
  is fixed, and a security fix within days.
- **Steps:** in [DEVELOPMENT.md](DEVELOPMENT.md#releasing). The tag makes
  the GitHub Release by itself, from the changelog (the in-app update
  check reads it). Then a post on the website's blog, and the same post
  in Discussions > Announcements.
- **Continuous integration** (tests on both Pythons, the journeys, the
  smoke test, the security checks) runs on a version tag, a pull request,
  or by hand from Actions > Run workflow - not on every push, while the
  repository is private and its Actions minutes are counted. So before
  each commit the same checks run locally (CLAUDE.md > Every change), and
  before tagging a release, run the workflow by hand on what's to be
  released. The security check still runs every Monday.
- **The ways in, from scratch:** before each minor release, deploy the
  release candidate the way a new owner would - the **Deploy to Render**
  button, Railway's steps and Docker Compose - on fresh accounts, then
  go through setup to a test email and a first post. The deploy buttons
  and templates aren't covered by CI, and a broken one is the first
  thing a new owner meets. Note what was checked in the release's pull
  request.
- **Supported:** the latest release gets fixes. Upgrading is always from
  any earlier release straight to the latest - migrations run in order.

## Updates that never break a site

The people running Soloblog aren't developers. Taking an update has to be
one click (or one command) and nothing else, every time.

- **Migrations only add.** A new column gets a default; nothing is renamed
  or dropped in place. A migration that has shipped is never edited.
- **Settings keep their names and meanings.** A setting that's no longer
  used is ignored, not an error; a renamed one is read from its old name
  too.
- **Before tagging a release,** upgrade a copy of the previous release's
  data: run the previous image with a volume, add a post, an image and a
  comment, then start the new image on the same volume and check they're
  all there, the admin opens and Settings saves.
- **If a release needs anything from the person running it** - a new
  environment variable, a changed port, a step on their host - the
  changelog section starts with **Upgrading**: numbered steps, in plain
  words, one per host where they differ. The GitHub Release repeats it,
  and the admin's update notice links to it.
- **A breaking change waits** for a release that can explain it, and gets
  a major version once past 1.0.

## Dependencies and their risks

Every Python package is pinned in `requirements.txt` - the ones
Soloblog uses, and below them every package those depend on - and the
front-end libraries are copies in `static/vendor/`, so nothing changes
until we change it. (Pinning only the direct ones isn't enough: a new
version of a package's own dependency can arrive unasked and break the
app.) When a
pin changes by hand, check the whole set still installs: a fresh
`pip install -r requirements-dev.txt` in a clean environment - the
app's pins have to suit the test tools too. **Dependabot** (`.github/dependabot.yml`) opens pull requests
once a month for Python packages, GitHub Actions and the Docker base
image; CI runs the full test suite and boots the image on each. Merge
when green, and check the app in a browser for anything touching FastHTML,
htmx or the editor. CI also runs every Monday on its own, so something
that breaks upstream (a download, a base image) shows up quickly.

| Dependency | What for | Risk | If it goes wrong |
|---|---|---|---|
| **FastHTML** (`python-fasthtml`) | routes, HTML components, sessions | **Medium.** Pre-1.0 and fast-moving (Answer.AI): minor versions can change behaviour. Actively developed. | Pinned; upgrade one version at a time with the tests. It's built on Starlette - if it were ever abandoned, the app could stay on the last version for a long time, or be ported to Starlette with `fastcore`'s HTML components (days, not months; routes and components are the only parts used). |
| **Starlette / uvicorn** | web server underneath | Low. Mature, widely used. | Come in through FastHTML. |
| **htmx 2** | page updates without reloads | Low. Stable, long-supported major version, vendored. | Stay on 2.x; htmx 4 would be a planned migration. |
| **daisyUI 5 / Tailwind 4** | styles and themes | Low. Very widely used. | - |
| **daisyft** | builds the CSS with the Tailwind + daisyUI program (tailwind-cli-extra) | **Highest.** A small 0.x project. | It only runs at build time. The Docker build pins the program's version (`TAILWIND_EXTRA` in the Dockerfile) and checks its sha256 - asking for the latest hit GitHub's rate limit once and failed a release build. To update: a newer tag from its releases page, and the linux-x64 and linux-arm64 digests GitHub shows there, in the Dockerfile; build locally or deploy the demo to check. Replacing daisyft with Tailwind's standalone CLI and daisyUI's plugin file is an afternoon's work. |
| **EasyMDE** | the markdown editor | Medium, long term: slow releases, built on CodeMirror 5 (legacy). | Vendored, so it keeps working. If it ever has to go, CodeMirror 6 or another markdown editor behind the same toolbar settings. |
| **pymdown-extensions** | emoji shortcodes (`:coffee:`) | Low. Mature and widely used (Material for MkDocs is built on it). Only its emoji extension is used. | Pinned; if it ever went away, the shortcodes would show as typed. |
| **Python-Markdown, nh3, Pillow, argon2, webauthn, PyYAML** | rendering, sanitising, images, passwords, passkeys, files | Low. Mature and maintained. | Security fixes arrive through Dependabot. |
| **KaTeX, Mermaid** (CDN) | maths and diagrams, only on posts that use them | Low. Pinned with integrity hashes. | Vendor them if the CDN ever becomes a problem. |
| **Python** | 3.14 in the Docker image; 3.12 the oldest supported from source | Low. | CI tests on both. Move the image up one version a year or so, after the tests pass on it in CI; raising the oldest supported one needs an **Upgrading** note for people running from source. |
| **GitHub Actions** | CI and publishing images | Low. | Dependabot keeps the action versions current (Node 20 is being retired). |

## The demo

A public demo with a working admin (demo mode, `DEMO_MODE=1`), built by
`tools/demo.py` and reset every few hours. See
[DEPLOYMENT.md](DEPLOYMENT.md#run-a-public-demo) for running it anywhere.

The README's screenshots in `docs/screenshots/` are the website's own, from
its landing page - six sample sites, each framed as a browser window
(`showcase/shoot.py` in the private `soloblog-website` repository). Re-take
them there when the look changes, and copy the new ones in.

**It runs on Fly.io, at https://demo.soloblog.zrplus.net, and updates itself
with every release.** CI's `demo` job builds each release from its source
on Fly (`deploy/fly-demo.toml`). It needs the app, its
`demo_data` volume, its `SESSION_SECRET`, and the repository's
`FLY_API_TOKEN` Actions secret (a deploy token for `soloblog-demo` only)
that the job uses. Every release tag redeploys it, and each one shows
under the repository's **Deployments** (the `demo` environment), linking
to the demo. If the token is ever replaced:
`fly tokens create deploy --app soloblog-demo | gh secret set FLY_API_TOKEN`
(without the secret, the job does nothing).

To redeploy by hand, from the repository's folder:
`fly deploy . --config deploy/fly-demo.toml --remote-only --ha=false`.

The demo sleeps when nobody's visiting and wakes on the next visit. A
feature that shows gets sample content in
`soloblog/demo.py`, so the next release's demo has it.

## The website

The project's own site, **https://soloblog.zrplus.net**, runs on
Soloblog itself and is the repository's homepage link on GitHub. Its
content is edited in its own admin like any Soloblog site, and it's
updated to each release by hand. Its hosting settings are kept outside
this repository.

## Keeping the project going

What someone - a new contributor, a future maintainer, an AI assistant -
needs to carry on, and where it is:

- **How to work on it:** [CLAUDE.md](../CLAUDE.md) (the rules for every change, which
  an AI assistant reads first) and [DEVELOPMENT.md](DEVELOPMENT.md).
- **Why it's the way it is:** [DECISIONS.md](DECISIONS.md) - add an entry
  for every decision that closes off another path.
- **What changed and when:** [CHANGELOG.md](../CHANGELOG.md) and the commit
  messages, which say *why*.
- **What's next:** the roadmap board and open issues.
- **That it still works:** the tests and journeys, run before every
  commit, and by CI on every release and pull request.

Nothing important should live only in someone's head, a chat, or one
person's machine. If a conversation settles something, it goes into one
of the files above.
