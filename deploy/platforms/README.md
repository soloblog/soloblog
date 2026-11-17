# App-store packages

Soloblog's packages for the stores and panels people install apps from.
Each folder here is laid out the way that store's own repository wants
it. They all run the same image, `ghcr.io/soloblog/soloblog`, with its data
folder on lasting storage, and set `HOSTED_ON` so first-time setup can say
where that platform shows the setup token (`TOKEN_IN_LOG` in
`soloblog/routes/auth_routes.py`; a test keeps the two in step).

Every store pulls the public image, so a package can only be submitted
once a release's image is published.

## Each release

1. After changing `config.VERSION`, run `python tools/platforms.py version`
   - it sets every package's version and image tag (a test fails until it
   has run).
2. Once the release's image is published, run
   `python tools/platforms.py build dist/platforms --digest`. It copies each
   package into `dist/platforms/<store>/`, adds the icon and screenshot each
   store asks for, and pins the image's digest where the store requires it.
3. Send each store its folder, as below. After the first time, a new
   version is a pull request to the same place.

## The stores

| Store | What goes where | First time |
|---|---|---|
| Railway | `railway/TEMPLATE.md` - typed into Railway's template editor | Publish from the project's Railway account |
| Zeabur | `zeabur/template.yaml` | `npx zeabur@latest template create -f template.yaml`, from the project's Zeabur account |
| Sealos | `sealos/soloblog/` → `template/soloblog/` in labring-actions/templates | Pull request, after deploying it on Sealos |
| Coolify | `coolify/templates/compose/soloblog.yaml` and `coolify/svgs/soloblog.svg` → the same paths in coollabsio/coolify | Pull request to its `next` branch |
| CapRover | `caprover/public/v4/` → the same paths in caprover/one-click-apps | Pull request |
| Dokploy | `dokploy/soloblog/` → `blueprints/soloblog/` in Dokploy/templates | Pull request - its preview deploys it |
| Easypanel | `easypanel/soloblog/` → `templates/soloblog/` in easypanel-io/templates | Pull request, after `npm run build` there |
| Umbrel | `umbrel/soloblog/` → `soloblog/` in getumbrel/umbrel-apps | `npm run lint:apps -- soloblog --check-images` there, then a pull request with screenshots and the logo in its description |
| CasaOS / ZimaOS | `casaos/Soloblog/` → `Apps/Soloblog/` in IceWhaleTech/CasaOS-AppStore | `./scripts/build_dist.sh` there, then a pull request |
| Unraid | `unraid/soloblog.xml`, served from this repository at `TemplateURL` | Submit the repository to Community Applications, with a support thread on the Unraid forum |
| TrueNAS SCALE | `truenas/soloblog/` → `ix-dev/community/soloblog/` in truenas/apps | Its `copy-lib` and `ci.py` there (they add the library and its hash), then a pull request with the icon and screenshots |
| Cloudron | `cloudron/` | `cloudron build` and `cloudron install` on a Cloudron, then publish to its App Store |

## How each was checked

Every package was run against a locally built image (`docker compose` for
the compose-based ones, the Cloudron image read-only with only its data
folder writable, the Unraid template's settings as `docker run`, the
TrueNAS image as its non-root user) - setup opened, a post kept across a
restart. What can only be checked on the platform itself - its own
interface and linters - is in the first-time column above.
