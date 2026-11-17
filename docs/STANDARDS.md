# Standards

What Soloblog conforms to, and how each is checked. The project's own
rules come first - [CLAUDE.md](../CLAUDE.md) (how every change is made),
[DEVELOPMENT.md](DEVELOPMENT.md) (conventions) and
[DECISIONS.md](DECISIONS.md) (why things are as they are). This page is
the outside standards behind them. Where one is only aimed for, it says so.

A change is done when it meets the ones that apply to it.

## Code

| Standard | What it means here | Checked by |
|---|---|---|
| [PEP 8](https://peps.python.org/pep-0008/) | Python style; comments only for a non-obvious why | `ruff check .` in CI |
| [Semantic Versioning](https://semver.org) | A patch for fixes, a minor for features, a major only when people must do something | `tools/release_notes.py` matches tag, VERSION and changelog |
| [Keep a Changelog](https://keepachangelog.com) | Every change a user would notice, under `[Unreleased]` | Review |
| [The Twelve-Factor App](https://12factor.net) | Settings from the environment, one image, data in one folder | [DEPLOYMENT.md](DEPLOYMENT.md) |
| [Docker best practices](https://docs.docker.com/build/building/best-practices/) | A small base image, pinned versions, run as a non-root user | CI builds and boots the image |
| Tests | New behaviour and every fixed bug get a test - for abuse, not only the happy path | `pytest` in CI |
| Journeys | What people do, in a real browser against a real server | `pytest journeys` in CI |

## Security

Security comes before features ([CLAUDE.md](../CLAUDE.md)).

| Standard | What it means here | Checked by |
|---|---|---|
| [OWASP Top 10](https://owasp.org/Top10/) | Injection, broken access, weak sessions and the rest, kept out | Tests for each abuse case |
| Robustness | Nothing a bot or attacker sends - an empty or folder-like name, a number too big for the database, odd characters - gets a server error | `tools/fuzz_routes.py`, run by the tests: every route, as a visitor and as the admin |
| [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/) level 1 | The checklist to grow into - *aimed for*: a full pass before the first public release | To do |
| [OWASP Cheat Sheets](https://cheatsheetseries.owasp.org) | Passwords (Argon2), sessions, file uploads, outbound requests (`netguard`, public addresses only), HTML sanitising (nh3) | Tests |
| [Content-Security-Policy](https://developer.mozilla.org/docs/Web/HTTP/CSP) | No inline handlers; a nonce on every script | `csp.py`; tests |
| Supply chain | Pinned dependencies; an advisory jumps the queue | `pip-audit` in CI, Dependabot monthly |
| Reporting | How to report a problem, and what happens then | [SECURITY.md](../SECURITY.md) |

## Accessibility

| Standard | What it means here | Checked by |
|---|---|---|
| [WCAG 2.2](https://www.w3.org/TR/WCAG22/) level AA | Text at 4.5:1 in every theme, your own too; keyboard use; labels; targets at least 24px | `tools/theme_contrast.py`; tests; `tools/phone_check.py --axe` |
| [WCAG 2.5.5](https://www.w3.org/WAI/WCAG22/Understanding/target-size-enhanced) (AAA), [Apple's HIG](https://developer.apple.com/design/human-interface-guidelines/accessibility), [Material](https://m3.material.io/foundations/designing/structure) | On a touch screen, 44px targets and 16px field text (the `touch-size` rule) | `tools/phone_check.py` |
| Motion | Animations off with Settings' switch or the reader's "reduce motion"; nothing ticks or moves on its own (WCAG 2.2.2) | Review |

## Interface

| Standard | What it means here | Checked by |
|---|---|---|
| [daisyUI](https://daisyui.com) and [Tailwind](https://tailwindcss.com) | Their components, sizes and theme colours - custom CSS only with a written reason ([DEVELOPMENT.md > Custom CSS](DEVELOPMENT.md#custom-css)) | Review; tests |
| [Nielsen Norman Group's heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/) | Plain words, consistency, recognition over recall, errors that say how to fix them | Review |
| Words | Written for someone who isn't a developer ([DEVELOPMENT.md > Writing and settings](DEVELOPMENT.md#writing-and-settings)) | Review |
| One look | A new pattern goes everywhere it fits, phone and desktop | `tools/phone_check.py`: sideways scrolling, things sticking out, small targets, squeezed words, script errors |

Before UI work, look up current practice (Apple's HIG, Material, WCAG,
NN/g) and follow it within daisyUI's own components.

## The web platform

| Standard | What it means here | Checked by |
|---|---|---|
| [HTML Living Standard](https://html.spec.whatwg.org) / [MDN](https://developer.mozilla.org) | Real headings, `<details>`, popovers, forms - the platform's own parts first | Review |
| [Core Web Vitals](https://web.dev/articles/vitals) | Fast first paint, no layout shift, quick to respond; lazy images, no web fonts to download | *Aimed for*: a Lighthouse run on the demo before each release |
| Internationalisation | Every word a visitor reads in all 23 languages; dates and directions (right to left) by language | Tests |

## Privacy and the law

| Standard | What it means here | Checked by |
|---|---|---|
| [GDPR](https://gdpr.eu) and ePrivacy | Nothing that tracks visitors before their yes (the consent banner); members can download and delete their data; a Privacy policy template | Tests |
| Payments | Stripe holds the cards - Soloblog never sees a card number, so little of PCI DSS applies | Review |
| Outside connections | Every one the app makes is listed in the user guide; nothing is sent home | [DECISIONS.md](DECISIONS.md) (no telemetry) |

## Open source

| Standard | What it means here |
|---|---|
| [MIT licence](../LICENSE) | ZRPlus Studio as the author, everywhere |
| [Code of conduct](../CODE_OF_CONDUCT.md), [contributing](../CONTRIBUTING.md), [support](../SUPPORT.md) | How people take part, and what to expect |
| [Open Source Guides](https://opensource.guide) | Maintaining with care: answers within a week, sites that keep working whatever happens |
| [OpenSSF Scorecard](https://securityscorecards.dev) | *Aimed for* once the repository is public |

## Still to do

1. A full ASVS level 1 pass, before 1.0.0-beta.
2. `tools/phone_check.py --axe` required for every change that's seen, not only run now and then.
3. A Lighthouse run on the demo before each release, against Core Web Vitals.
4. OpenSSF Scorecard once the repository is public.
