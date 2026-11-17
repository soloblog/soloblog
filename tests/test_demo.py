"""The sample blog (soloblog/demo.py) builds, and every post in it renders."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_demo_builds_into_its_own_folder(tmp_path):
    env = {**os.environ, "DEMO_OFFLINE": "1"}
    env.pop("DATA_DIR", None)
    r = subprocess.run([sys.executable, "tools/demo.py", str(tmp_path / "data"), "--cache", str(tmp_path / "cache")],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stderr[-2000:]
    assert "36 photos" in r.stdout
    files = os.listdir(tmp_path / "data" / "posts")
    assert "emergency-focaccia.md" in files and len(files) >= 20
    # a second build into the same folder is refused, not merged
    again = subprocess.run([sys.executable, "tools/demo.py", str(tmp_path / "data")], cwd=ROOT, env=env,
                           capture_output=True, text=True, timeout=60)
    assert again.returncode != 0


def test_demo_posts_are_complete():
    from soloblog import demo, post_templates
    from soloblog.render import render_post
    photos = {k: f"/uploads/{k}.webp" for k in demo.PHOTOS}
    items = demo.posts_and_pages(photos)
    slugs = [i[0] for i in items]
    assert len(slugs) == len(set(slugs))
    for slug, title, _tags, _summary, body, f in items:
        assert title and (body.strip() or f.get("template") == "link"), slug
        assert not f.get("template") or post_templates.get(f["template"]), slug
        assert "layout" not in f, slug
        assert "lorem" not in body.lower()
        if body.strip():
            assert render_post(body)[0], slug
        # every photo it uses is one we have
        assert "/uploads/.webp" not in body and "](/uploads/)" not in body, slug
    assert set(demo.PHOTOS) == set(demo._load_sources())
