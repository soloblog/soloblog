# Vendored front-end files

Served from here instead of a CDN, so every page runs exactly this code: no
third-party host in the loop, nothing that can change underneath the site,
and nothing to fetch on a self-hosted box without internet access.

| File | Version | Licence | Source |
|---|---|---|---|
| `htmx-2.0.7.min.js` | 2.0.7 | 0BSD | npm `htmx.org` |
| `easymde-2.20.0/` | 2.20.0 | MIT | npm `easymde` |
| `theme-change-2.5.0.js` | 2.5.0 | MIT | npm `theme-change` |

To update one: download the new version from npm, replace the file, put the
new version in its name, and update the references in `app.py`,
`routes/editor.py`, `routes/admin_settings.py` and `routes/welcome.py`.

The editor's icons are Lucide's (ISC), copied into `soloblog/editor_icons.py`
as SVG markup by `tools/editor_icons.py`, with the licence at its top.

KaTeX and Mermaid stay on jsdelivr - they're large, opt-in, and only load on
posts that use them - pinned to exact versions with `integrity` hashes
(`ui`, `PostScripts`).
