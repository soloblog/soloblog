"""Every page of the sample blog, as a visitor, a member and the admin -
every GET route, with real values for the ones that take one (each post,
page, tag, the editor for each post). Reports what fails (a 500, a page
that should be there and isn't) and what's slow. Markdown on stdout;
exits 1 if anything failed.

    python tools/crawl.py > crawl.md
"""
import atexit
import os
import re
import shutil
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="soloblog-crawl-")
# its throwaway site goes when it ends
atexit.register(shutil.rmtree, os.environ["DATA_DIR"], ignore_errors=True)
os.environ.setdefault("SESSION_SECRET", "crawl")
os.chdir(ROOT)
SLOW = 1.0  # seconds
# off on the sample blog, so missing on purpose: the fediverse, ads, and the
# newsletter page without email set up
OFF = ("/.well-known/nodeinfo", "/.well-known/webfinger", "/nodeinfo/", "/ap/", "/ads.txt", "/newsletter", "/webmention")


def main():
    from soloblog import demo
    demo.build(cache=os.path.join(ROOT, "demo-cache"))
    from soloblog.app import app
    from soloblog import members, posts
    from starlette.routing import Route
    from starlette.testclient import TestClient

    visitor = TestClient(app, follow_redirects=False, raise_server_exceptions=False)
    admin = TestClient(app, follow_redirects=False, raise_server_exceptions=False)
    assert admin.post("/login", data={"password": "demo"}).status_code == 303
    member = TestClient(app, follow_redirects=False, raise_server_exceptions=False)
    m = members.by_email("kai@example.com") or members.add("kai@example.com", "Kai")
    member.cookies.set(members.COOKIE, members.new_session(m["id"]))

    rows = posts.list_posts(include_drafts=True)
    values = {
        "slug": [r["slug"] for r in rows], "tag": sorted({t.strip() for r in rows for t in (r["tags"] or "").split(",")
                                                          if t.strip()})[:15],
        "series": sorted({posts.series_slug(r["series_name"]) for r in rows if r["series_name"]}),
    }
    paths = []
    for r in app.routes:
        if not isinstance(r, Route) or "GET" not in (r.methods or ()) or "{fname" in r.path:
            continue
        names = re.findall(r"{(\w+)(?::[^}]*)?}", r.path)
        if not names:
            paths.append(r.path)
        elif names == ["slug"] and r.path.startswith("/series/"):
            paths += [f"/series/{s}" for s in values["series"]]
        elif names == ["slug"]:
            paths += [re.sub(r"{slug(?::[^}]*)?}", s, r.path) for s in values["slug"]]
        elif names == ["tag"]:
            paths += [re.sub(r"{tag(?::[^}]*)?}", t, r.path) for t in values["tag"]]
    paths = sorted(set(paths))

    failures, slow, counts = [], [], {}
    from soloblog.db import get_db
    for who, client in (("visitor", visitor), ("member", member), ("admin", admin)):
        for path in paths:
            # the site's own rate limits are for people, not a crawl
            get_db().execute("DELETE FROM rate_hits")
            get_db().commit()
            start = time.perf_counter()
            r = client.get(path)
            took = time.perf_counter() - start
            counts[r.status_code] = counts.get(r.status_code, 0) + 1
            if r.status_code >= 500:
                failures.append((who, path, r.status_code, r.text[:200].replace("\n", " ")))
            elif who == "admin" and r.status_code == 404 and not path.startswith(("/api/", "/ghost/", *OFF)):
                failures.append((who, path, 404, "missing for the admin"))
            if took > SLOW:
                slow.append((who, path, took))

    print("# Crawl\n")
    print(f"{len(paths)} addresses, each as a visitor, a member and the admin - {len(paths) * 3} requests.\n")
    print("| Status | Requests |\n|---|---|")
    for status in sorted(counts):
        print(f"| {status} | {counts[status]} |")
    print(f"\n## Failures ({len(failures)})\n")
    for who, path, status, text in failures:
        print(f"- [ ] **{status}** as {who}: `{path}` - {text}")
    print(f"\n## Slower than {SLOW:.0f} s ({len(slow)})\n")
    for who, path, took in sorted(slow, key=lambda x: -x[2]):
        print(f"- [ ] {took:.2f} s as {who}: `{path}`")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
