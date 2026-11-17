"""The README's "Light on resources" figures, measured on a running copy:
memory after a few pages, the time for a page one at a time, pages a second
and peak memory with 16 requests at once, and what a post and its styles and
scripts weigh. Run Soloblog in production mode on one core first, with the
sample blog and the Docker image's MALLOC_ARENA_MAX:

    python tools/demo.py /tmp/sample
    MALLOC_ARENA_MAX=2 ENV=production DATA_DIR=/tmp/sample SESSION_SECRET=x \\
        PORT=5020 taskset -c 0 python app.py
    taskset -c 1-7 python tools/measure.py <its pid>

Linux only (it reads the process's memory from /proc)."""
import http.client
import re
import statistics
import sys
import threading
import time
import urllib.request
from pathlib import Path

PORT = 5020


def main():
    pid = int(sys.argv[1])

    def rss():
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("VmRSS"):
                return int(line.split()[1]) / 1024

    def get(conn, url, headers=None):
        for _ in (0, 1):
            try:
                conn.request("GET", url, headers=headers or {})
                resp = conn.getresponse()
                return resp, resp.read()
            except (http.client.RemoteDisconnected, ConnectionResetError, BrokenPipeError):
                conn.close()
                conn.connect()

    home = urllib.request.urlopen(f"http://localhost:{PORT}/").read().decode()
    posts = list(dict.fromkeys(re.findall(r'href="(/post/[a-z0-9-]+)"', home)))[:8]
    urls = ["/", "/archive", "/tags"] + posts
    conn = http.client.HTTPConnection("localhost", PORT)
    for _ in range(3):
        for url in urls:
            get(conn, url)
    time.sleep(5)
    print(f"Memory after a few pages: {rss():.0f} MB")

    times = []
    for i in range(300):
        start = time.perf_counter()
        get(conn, urls[i % len(urls)])
        times.append((time.perf_counter() - start) * 1000)
    times.sort()
    print(f"One at a time: {statistics.median(times):.0f} ms typical, {times[int(len(times) * .95)]:.0f} ms at 95%")

    done, peak, stop, lock = [0], [0.0], time.time() + 30, threading.Lock()

    def worker(k):
        c, n = http.client.HTTPConnection("localhost", PORT), 0
        while time.time() < stop:
            get(c, urls[(k + n) % len(urls)])
            n += 1
        with lock:
            done[0] += n

    def sample():
        while time.time() < stop:
            peak[0] = max(peak[0], rss())
            time.sleep(0.25)
    threads = [threading.Thread(target=worker, args=(k,)) for k in range(16)] + [threading.Thread(target=sample)]
    began = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f"16 at once for 30 s: {done[0] / (time.time() - began):.0f} pages a second, {peak[0]:.0f} MB at peak")

    _, raw = get(conn, posts[0])
    _, sent = get(conn, posts[0], {"Accept-Encoding": "gzip"})
    print(f"A post's page: {len(raw) / 1024:.0f} KB, {len(sent) / 1024:.0f} KB compressed")
    for url in re.findall(r'(?:href|src)="(/(?:static/css|static/vendor/htmx|app\.js)[^"]*)"', home):
        resp, body = get(conn, url, {"Accept-Encoding": "gzip"})
        print(f"{url.split('?')[0]}: {len(body) / 1024:.0f} KB compressed, {resp.getheader('cache-control') or 'no cache header'}")


if __name__ == "__main__":
    main()
