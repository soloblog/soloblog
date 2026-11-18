"""Soloblog is described in its official words everywhere
(docs/brand/README.md > The words; CLAUDE.md > One look, everywhere)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORES = "deploy/platforms/"


def _words():
    """{'Tagline': ..., 'One line': ..., 'Paragraph': ...} from the brand page's table."""
    text = (ROOT / "docs/brand/README.md").read_text(encoding="utf-8")
    return dict(re.findall(r"^\| \*\*(Tagline|One line|Paragraph)\*\* \| (.+?) \|", text, re.M))


def _flat(path):
    """A file's text on one line, without markdown links' addresses or escapes."""
    text = (ROOT / path).read_text(encoding="utf-8")
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return re.sub(r"\s+", " ", text.replace("\\n", " "))


def test_the_brand_page_has_all_three():
    words = _words()
    assert set(words) == {"Tagline", "One line", "Paragraph"}
    assert words["Paragraph"].startswith("Soloblog is " + words["One line"][0].lower() + words["One line"][1:])


def test_each_place_says_the_official_words():
    words = _words()
    places = {
        "Tagline": ["README.md", "tools/brand.py", STORES + "cloudron/CloudronManifest.json",
                    STORES + "umbrel/soloblog/umbrel-app.yml", STORES + "casaos/Soloblog/docker-compose.yml"],
        "One line": ["docs/FAQ.md", "app.json", "Dockerfile", ".github/workflows/docker.yml",
                     "deploy/caprover-one-click.yml", STORES + "coolify/soloblog.yaml",
                     STORES + "dokploy/soloblog/meta.json", STORES + "sealos/soloblog/index.yaml",
                     STORES + "truenas/soloblog/app.yaml", STORES + "zeabur/template.yaml"],
        "Paragraph": ["README.md", STORES + "cloudron/DESCRIPTION.md", STORES + "umbrel/soloblog/umbrel-app.yml",
                      STORES + "casaos/Soloblog/docker-compose.yml", STORES + "unraid/soloblog.xml",
                      STORES + "railway/TEMPLATE.md", STORES + "sealos/soloblog/README.md",
                      STORES + "truenas/soloblog/README.md", STORES + "zeabur/template.yaml",
                      STORES + "easypanel/soloblog/meta.yaml"],
    }
    missing = [f"{length}: {path}" for length, paths in places.items() for path in paths
               if words[length] not in _flat(path)]
    assert not missing, missing


def test_no_old_wording_is_left():
    old = re.compile(r"blog and personal website|personal website and blog|self-hosted (personal )?blog|"
                     r"yours forever|for one writer|that you run yourself|a joy to write", re.I)
    files = [p for p in ROOT.rglob("*") if p.is_file() and p.suffix in (".md", ".py", ".json", ".yml", ".yaml", ".xml")
             and not any(part in (".venv", ".git", "locales", "node_modules", "dist", "demo-data", "demo-live",
                                  "demo-cache", "data") for part in p.relative_to(ROOT).parts)
             and p.name not in ("CHANGELOG.md", "test_brand.py")]
    found = [str(p.relative_to(ROOT)) for p in files if old.search(p.read_text(encoding="utf-8", errors="ignore"))]
    assert not found, found
