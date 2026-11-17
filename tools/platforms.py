"""The app-store packages in deploy/platforms, ready for each store.

    python tools/platforms.py version          # every package to config.VERSION
    python tools/platforms.py build OUT        # each store's folder, with its pictures
    python tools/platforms.py build OUT --digest   # ... and the image pinned by digest

`version` rewrites each package's version and image tag - run it after
changing config.VERSION (a test fails until it's run). `build` copies
the packages into OUT, one folder per store, laid out as that store's
repository wants it, with the icon and screenshot each one asks for. With
--digest it looks up the published image's digest (docker buildx
imagetools) and pins it where a store requires that (Umbrel, TrueNAS) - so
it only works once the release's image is public. deploy/platforms/README.md
says where each folder goes.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from soloblog import config  # noqa: E402

PLATFORMS = ROOT / "deploy" / "platforms"
BRAND = ROOT / "docs" / "brand"
SCREENSHOT = ROOT / "docs" / "screenshots" / "hero.webp"
IMAGE = "ghcr.io/soloblog/soloblog"
TAG = re.compile(r"(ghcr\.io/soloblog/soloblog:)([0-9][\w.-]*?)(@sha256:[0-9a-f]{64})?(?=[\s\"'`]|$)", re.M)

# each file's version fields, beyond the image tag: (file, pattern, replacement)
VERSION_FIELDS = [
    ("umbrel/soloblog/umbrel-app.yml", r'^version: ".*"$', 'version: "{v}"'),
    ("casaos/Soloblog/docker-compose.yml", r'^  version: ".*"$', '  version: "{v}"'),
    ("dokploy/soloblog/meta.json", r'^  "version": ".*",$', '  "version": "{v}",'),
    ("cloudron/CloudronManifest.json", r'^  "upstreamVersion": ".*",$', '  "upstreamVersion": "{v}",'),
    ("cloudron/CloudronManifest.json", r'^  "version": ".*",$', '  "version": "{v}",'),
    ("truenas/soloblog/app.yaml", r"^app_version: .*$", "app_version: {v}"),
    ("truenas/soloblog/ix_values.yaml", r'^(    repository: ghcr\.io/soloblog/soloblog\n    tag: )".*"$',
     r'\g<1>"{v}"'),
    ("../caprover-one-click.yml", r"^      defaultValue: .*$", "      defaultValue: {v}"),
]


def package_files():
    return [p for p in PLATFORMS.rglob("*") if p.is_file()] + [ROOT / "deploy" / "caprover-one-click.yml"]


def set_version(version: str) -> list:
    changed = []
    for path in package_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        new = TAG.sub(lambda m: m.group(1) + version, text)
        for rel, pattern, repl in VERSION_FIELDS:
            if (PLATFORMS / rel).resolve() == path.resolve():
                new = re.sub(pattern, repl.replace("{v}", version), new, flags=re.M)
        if new != text:
            path.write_text(new, encoding="utf-8")
            changed.append(path.relative_to(ROOT))
    # Cloudron shows a line for each version it updates to
    log = PLATFORMS / "cloudron" / "CHANGELOG"
    text = log.read_text(encoding="utf-8")
    if f"[{version}]" not in text:
        entry = f"[{version}]\n* Soloblog {version}: https://github.com/soloblog/soloblog/releases/tag/v{version}\n\n"
        log.write_text(entry + text, encoding="utf-8")
        changed.append(log.relative_to(ROOT))
    return changed


def digest(version: str) -> str:
    docker = shutil.which("docker") or sys.exit("docker isn't installed - it reads the image's digest")
    ref = f"{IMAGE}:{version}"
    run = lambda *args: subprocess.run([docker, *args], capture_output=True, text=True, check=True).stdout  # noqa: E731
    try:
        manifest = json.loads(run("buildx", "imagetools", "inspect", ref, "--format", "{{json .Manifest}}"))
    except subprocess.CalledProcessError:
        # no buildx plugin: the index from the registry, and its digest
        # from a pull (an image's RepoDigests name the index, not one arch)
        manifest = json.loads(run("manifest", "inspect", ref))
        run("pull", "-q", ref)
        digests = run("image", "inspect", ref, "--format", "{{json .RepoDigests}}")
        manifest["digest"] = next(d.split("@")[1] for d in json.loads(digests) if d.startswith(IMAGE + "@"))
    platforms = {f"{m['platform']['os']}/{m['platform']['architecture']}" for m in manifest.get("manifests", [])
                 if m.get("platform")}
    if not {"linux/amd64", "linux/arm64"} <= platforms:
        raise SystemExit(f"{IMAGE}:{version} isn't built for both linux/amd64 and linux/arm64: {platforms}")
    return manifest["digest"]


def _picture(src: Path, dest: Path, size=None, fmt=None):
    from PIL import Image
    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        if size:
            im = im.copy()
            im.thumbnail(size)
        im.save(dest, fmt or dest.suffix.lstrip(".").upper().replace("JPG", "JPEG"))


def build(out: Path, pin: bool):
    version = config.VERSION
    sha = digest(version) if pin else None
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(PLATFORMS, out)
    (out / "README.md").unlink()
    icon_png, icon_svg = BRAND / "soloblog-icon-512.png", BRAND / "soloblog-icon.svg"

    # where each store wants its pictures
    shutil.copy(icon_svg, out / "dokploy" / "soloblog" / "soloblog.svg")
    (out / "easypanel" / "soloblog" / "assets").mkdir(parents=True, exist_ok=True)
    shutil.copy(icon_svg, out / "easypanel" / "soloblog" / "assets" / "logo.svg")
    _picture(SCREENSHOT, out / "easypanel" / "soloblog" / "assets" / "screenshot.png")
    (out / "coolify" / "svgs").mkdir(parents=True, exist_ok=True)
    shutil.copy(icon_svg, out / "coolify" / "svgs" / "soloblog.svg")
    (out / "coolify" / "templates" / "compose").mkdir(parents=True, exist_ok=True)
    shutil.move(out / "coolify" / "soloblog.yaml", out / "coolify" / "templates" / "compose" / "soloblog.yaml")
    _picture(icon_png, out / "sealos" / "soloblog" / "logo.png")
    _picture(SCREENSHOT, out / "sealos" / "soloblog" / "website-screenshot.webp")
    _picture(icon_png, out / "casaos" / "Soloblog" / "icon.png")
    _picture(SCREENSHOT, out / "casaos" / "Soloblog" / "thumbnail.png", size=(1280, 720))
    _picture(SCREENSHOT, out / "casaos" / "Soloblog" / "screenshot-1.png")
    _picture(icon_png, out / "cloudron" / "logo.png", size=(256, 256))
    caprover = out / "caprover" / "public" / "v4"
    (caprover / "apps").mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "deploy" / "caprover-one-click.yml", caprover / "apps" / "soloblog.yml")
    _picture(icon_png, caprover / "logos" / "soloblog.png")

    if sha:
        for rel in ("umbrel/soloblog/docker-compose.yml",):
            path = out / rel
            path.write_text(TAG.sub(lambda m: f"{m.group(1)}{version}@{sha}", path.read_text(encoding="utf-8")),
                            encoding="utf-8")
        values = out / "truenas" / "soloblog" / "ix_values.yaml"
        values.write_text(values.read_text(encoding="utf-8").replace(f'tag: "{version}"', f'tag: "{version}@{sha}"'),
                          encoding="utf-8")
    print(f"Built {version} into {out}" + (f", pinned to {sha}" if sha else " (no digest - add --digest on release day)"))


def main(argv):
    if argv[:1] == ["version"]:
        changed = set_version(config.VERSION)
        print("\n".join(map(str, changed)) or f"Every package already says {config.VERSION}")
    elif argv[:1] == ["build"] and len(argv) >= 2:
        build(Path(argv[1]).resolve(), "--digest" in argv)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
