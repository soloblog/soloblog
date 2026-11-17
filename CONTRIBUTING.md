# Contributing

Thanks for your interest in Soloblog.

## Questions, ideas and bugs

- **A question:** ask in [Discussions > Q&A](https://github.com/soloblog/soloblog/discussions/categories/q-a)
  (and check the [FAQ](docs/FAQ.md) first).
- **An idea:** post it in [Discussions > Ideas](https://github.com/soloblog/soloblog/discussions/categories/ideas),
  where others can upvote it. Good ones become issues and go on the
  [roadmap](docs/ROADMAP.md).
- **A bug:** open an [issue](https://github.com/soloblog/soloblog/issues/new/choose)
  with the bug form - it asks for what's needed to reproduce it.
- **A security problem:** privately, as [SECURITY.md](SECURITY.md) says.

How ideas travel from a Discussion to a release is in
[docs/MAINTAINING.md](docs/MAINTAINING.md).

Soloblog is deliberately small and for one person's site - see
[docs/DECISIONS.md](docs/DECISIONS.md). Before starting a big feature,
open a Discussion to talk it through, so your work doesn't end up outside
the project's scope.

## Pull requests

**While Soloblog is in beta**, bug fixes, translations and docs are
welcome as pull requests. New features start as a Discussion under Ideas
first - pull requests that add a feature without one aren't merged
during the beta.

Using an AI assistant is fine - the project is built with one - but read
what it wrote, follow the steps below and be ready to explain the
change. Pull requests that don't are closed.

1. Read [CLAUDE.md](CLAUDE.md) - the working rules, for people and AI
   assistants alike - and [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for
   setup, the project layout, and the UI conventions new code follows.
   [docs/STANDARDS.md](docs/STANDARDS.md) lists the outside standards a
   change meets - OWASP, WCAG and the rest - and how each is checked.
2. Keep each pull request to one change, and open it against the next
   version's branch (`1.1`, say - the highest-numbered one), not `master`:
   `master` is the latest release. A fix for a bug in the release itself
   can go to `master`.
3. Write each commit message as [CLAUDE.md](CLAUDE.md#commit-messages)
   says: what changed and why, in plain words, with no personal details.
4. Before submitting, run `python -m pytest` and `python -m ruff check .`,
   and check your change in a browser, including dark and light themes
   and a phone-width window if it touches the UI.
5. Add a line under `Unreleased` in [CHANGELOG.md](CHANGELOG.md) for
   anything a user would notice, and describe new features in
   [the user guide](docs/guide/README.md).

By contributing, you agree your work is licensed under the project's
[MIT License](LICENSE).
