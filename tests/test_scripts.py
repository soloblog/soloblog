import shutil
import subprocess

import pytest


def _inline_scripts():
    """Every *_JS string constant the app ships, across the modules
    that hold them."""
    import importlib
    out = {}
    for name in ("app", "ads", "routes.editor", "routes.admin_settings", "routes.public", "routes.media"):
        mod = importlib.import_module(f"soloblog.{name}")
        for attr, value in vars(mod).items():
            if attr.endswith("_JS") and isinstance(value, str) and value.strip():
                out[f"{name}.{attr}"] = value
    return out


@pytest.mark.skipif(not shutil.which("node"), reason="needs node for a JS syntax check")
def test_inline_scripts_are_valid_javascript(tmp_path):
    # JS lives in Python strings here, where a "\n" meant for JavaScript
    # silently becomes a real line break - this catches that class of bug
    scripts = _inline_scripts()
    assert len(scripts) > 15
    for name, js in scripts.items():
        f = tmp_path / f"{name}.js"
        f.write_text(js, encoding="utf-8")
        r = subprocess.run(["node", "--check", str(f)], capture_output=True, text=True)
        assert r.returncode == 0, f"{name}: {r.stderr[:400]}"


def test_no_invalid_escapes_in_the_source():
    # a "\s" meant for JavaScript, written in a plain Python string, only
    # warns - and turns into an error in a later Python
    import pathlib
    import warnings
    root = pathlib.Path(__file__).resolve().parent.parent
    for path in [*(root / "soloblog").rglob("*.py"), *(root / "tools").glob("*.py")]:
        with warnings.catch_warnings():
            warnings.simplefilter("error", SyntaxWarning)
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
