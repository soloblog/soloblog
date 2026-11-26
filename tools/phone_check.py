"""Every page of the sample blog (soloblog/demo.py) on a phone, checked
for what's easy to miss by eye: a page that scrolls sideways, something
sticking out past the screen's edge, a row of tabs cut off, buttons too
small to tap, words squeezed a word a line by the buttons beside them, a
picture out of shape or without its width and height. Needs
Playwright, like the journeys:

    python tools/phone_check.py                   # 375 and 320 px wide
    python tools/phone_check.py --browser msedge  # an installed Edge
    python tools/phone_check.py --firefox         # Firefox instead of Chromium
    python tools/phone_check.py --axe             # and accessibility, by axe-core

--axe needs axe-core, outside the project's Python packages:
npm install --prefix .tools/node axe-core@4.14.0

Prints what it finds, page by page, and exits 1 if anything is wrong -
run it after any change to how pages look."""
from pathlib import Path
import argparse
import io
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PORT = 5098


def wait_up(url, server, seconds=180):
    end = time.time() + seconds
    while time.time() < end:
        # its own server stopped (the port was taken): never check whatever else answers there
        if server.poll() is not None:
            raise SystemExit(f"Soloblog didn't start - is something else using port {PORT}?")
        try:
            urllib.request.urlopen(url + "/healthz", timeout=3)  # noqa: S310 - the app on localhost
            return
        except Exception:
            time.sleep(1)
    raise SystemExit("Soloblog didn't start")

BASE = f"http://localhost:{PORT}"
WIDTHS = (375, 320)

PUBLIC = ["/", "/tags", "/archive", "/links", "/contact", "/search?q=bread", "/projects", "/bookshelf",
          "/post/my-sourdough-starter-has-outlived-three-houseplants", "/post/emergency-focaccia",
          "/post/fog-ferries-and-one-extremely-patient-heron",
          "/post/everything-my-grandmother-knows-about-running-a-bakery",
          "/post/ten-years-of-learning-norwegian-badly", "/post/how-i-back-up-40000-photos",
          "/post/back-on-the-road-mostly",
          # a page made from each kind of template
          "/sections", "/in-short", "/work-with-me", "/kind-words", "/press-kit", "/corner-cafe", "/small-fixes",
          "/shop", "/bake-stall", "/zine-club", "/repair-cafe", "/volunteers", "/talks", "/handbook", "/about",
          # the tour
          "/tour", "/templates", "/styles", "/post/projects-sideways", "/terms",
          # the members area
          "/post/the-five-minute-rule-and-other-tricks-for-finishing-things", "/join", "/signin", "/membership"]
ADMIN = ["/admin/posts", "/admin/posts?status=pinned", "/admin/posts?status=trash", "/admin/posts?status=tags",
         "/admin/posts?status=calendar", "/admin/new", "/admin/edit/emergency-focaccia", "/admin/media",
         "/admin/comments", "/admin/comments?tab=approved", "/admin/comments?tab=mentions", "/admin/messages",
         "/admin/newsletter", "/admin/members", "/admin/stats", "/admin/health", "/admin/health?tab=log", "/admin/health?tab=info"]



def _settings_pages():
    """Every settings page, as ui.SETTINGS_GROUPS lists them - read from
    the source, since importing the app here would read its config."""
    import re
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "soloblog", "ui", "admin.py"),
              encoding="utf-8") as f:
        block = f.read().split("SETTINGS_GROUPS = [", 1)[1].split("\n]\n", 1)[0]
    return re.findall(r'\("([a-z]+)", "[^"]+"\)', block)


SETTINGS = _settings_pages()
HELP = ["guide", "faq", "whatsnew", "deployment", "api", "sponsor"]

# in the page: what's wrong with it, as short lines
CHECK_JS = r"""
() => {
  const width = document.documentElement.clientWidth, found = [];
  const describe = el => el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') +
    (typeof el.className === 'string' && el.className ? '.' + el.className.trim().split(/\s+/).slice(0, 3).join('.') : '') +
    (el.textContent.trim() ? ' "' + el.textContent.trim().replace(/\s+/g, ' ').slice(0, 30) + '"' : '');
  // sr-only things (Skip to content) are 1px until focused - not shown
  const shown = el => el.checkVisibility({visibilityProperty: true, opacityProperty: true}) &&
    el.getBoundingClientRect().width > 1;
  // inside something meant to scroll sideways (a tab row, a table, the toolbar)
  const scrolls = el => {
    for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
      const x = getComputedStyle(p).overflowX;
      if (x === 'auto' || x === 'scroll') return true;
    }
    return false;
  };
  if (document.documentElement.scrollWidth > width + 1)
    found.push(`the page scrolls sideways (${document.documentElement.scrollWidth}px wide)`);
  const out = [...document.body.querySelectorAll('*')].filter(el => {
    // a row of logos that drifts sideways is clipped by its box on purpose
    if (!shown(el) || scrolls(el) || el.closest('[popover]:not(:popover-open), dialog:not([open]), .drawer-side, [data-drift]'))
      return false;
    const r = el.getBoundingClientRect();
    // a closed drawer waits wholly off the screen; CodeMirror's scroller
    // hides its scrollbars past the edge on purpose
    if (r.left >= width - 1 || r.right <= 1 || el.matches('.CodeMirror-scroll')) return false;
    return r.right > width + 2 || r.left < -2;
  });
  // the outermost only - its children stick out with it
  out.filter(el => !out.includes(el.parentElement))
     .filter(el => !/w-screen/.test(el.className))  // the hero and cover breakouts, on purpose
     .slice(0, 5).forEach(el => found.push('sticks out: ' + describe(el)));
  // a slider or filmstrip that doesn't fit shows the arrow onwards
  document.querySelectorAll('.gallery-slider > .carousel').forEach(track => {
    const next = track.parentNode.querySelector(':scope > button:last-of-type');
    if (track.scrollWidth > track.clientWidth + 1 && (!next || next.classList.contains('invisible')))
      found.push('gallery arrows missing: ' + describe(track.closest('.gallery')));
  });
  // a badge (a tag) whose words spill out of it
  document.querySelectorAll('.badge').forEach(b => {
    if (shown(b) && b.scrollWidth > b.clientWidth + 1) found.push('badge overflows: ' + describe(b));
  });
  // a row of tabs must show them all - under More if need be (ui.Tabs);
  // a tab cut off at the edge is easy to miss
  document.querySelectorAll('.tabs').forEach(row => {
    if (shown(row) && row.scrollWidth > row.clientWidth + 1) found.push('tabs cut off: ' + describe(row));
  });
  // a picture squeezed out of its shape, or one of ours a visitor's page
  // gives no width and height (the page jumps as it loads)
  document.querySelectorAll('img').forEach(img => {
    const r = img.getBoundingClientRect();
    if (shown(img) && img.naturalWidth && r.width > 8 && r.height > 8 && getComputedStyle(img).objectFit === 'fill' &&
        Math.abs((r.width / r.height) / (img.naturalWidth / img.naturalHeight) - 1) > 0.04)
      found.push(`picture out of shape (${Math.round(r.width)}x${Math.round(r.height)}): ` + describe(img));
    if (!location.pathname.startsWith('/admin') && /^\/uploads\/[^/]+$/.test(new URL(img.src, location).pathname) &&
        img.naturalWidth && !(img.hasAttribute('width') && img.hasAttribute('height')))
      found.push('picture without width and height: ' + describe(img));
  });
  // a target a finger can hit: on a touch screen 44 by 44 px (the usual touch target; WCAG
  // 2.5.5) - a pill's with its reach - and 24 for a checkbox, radio or switch
  // (touch-size, input.css);
  // with a mouse WCAG 2.2's minimum, 24 (links inside text are exempt) - less
  // half a pixel, as a section still sliding in measures 43.9
  const touch = matchMedia('(pointer: coarse)').matches, big = touch ? 44 : 24, choice = touch ? 24 : 16;
  document.querySelectorAll('.btn, button, select, input:not([type=hidden]), textarea, summary, .tab, ' +
                            '.menu li > a, a.badge, button.badge').forEach(el => {
    if (!shown(el) || el.disabled || el.closest('.drawer-side, [popover]:not(:popover-open)')) return;
    // a field's own parts (a search's clear button sits inside its field)
    if (el.closest('.input, .select') && el.closest('.input, .select') !== el) return;
    const r = el.getBoundingClientRect();
    // a pill's tap area reaches past its edges (touch-size, input.css): what
    // a finger can hit is its height and that reach together
    const after = el.matches('.badge') ? getComputedStyle(el, '::after') : null;
    const reach = after && after.content !== 'none' && after.position === 'absolute'
                ? -(parseFloat(after.top) || 0) - (parseFloat(after.bottom) || 0) : 0;
    const small = el.type === 'checkbox' || el.type === 'radio' ? Math.min(r.width, r.height) < choice
                : el.matches('.badge') ? r.height + reach < (touch ? 44 : 16) - .5 : (r.height < big - .5 || r.width < big - .5);
    if (small) found.push(`too small to tap (${Math.round(r.width)}x${Math.round(r.height)}): ` + describe(el));
  });
  // words squeezed by buttons beside them: a short run of text (a date, a
  // name) broken a word or two a line, as History's dates were by Compare
  // and Restore - its own text, not a heading, at least 3 lines of under
  // 10 characters, beside a button in its row
  const lineCount = el => { const r = document.createRange(); r.selectNodeContents(el);
    const lh = parseFloat(getComputedStyle(el).lineHeight) || parseFloat(getComputedStyle(el).fontSize) * 1.4;
    let n = 0, last = -1e9;
    for (const t of [...r.getClientRects()].filter(x => x.width > 1).map(x => x.top).sort((a, b) => a - b))
      if (t - last > lh * 0.6) { n++; last = t; }
    return n; };
  document.querySelectorAll('.btn, button').forEach(btn => {
    const row = btn.closest('.flex, .grid');
    if (!row || !shown(btn) || btn.closest('[popover]:not(:popover-open)')) return;
    [...row.querySelectorAll('p, span, div, a, label')].filter(el => shown(el) && !el.closest('.btn, button') &&
        [...el.children].every(c => ['inline', 'contents', 'none'].includes(getComputedStyle(c).display))).forEach(el => {
      const text = (el.innerText || '').trim().replace(/\s+/g, ' ');
      if (text.length < 12 || parseFloat(getComputedStyle(el).fontSize) >= 20) return;
      const n = lineCount(el);
      if (n >= 3 && text.length / n < 10) found.push('squeezed by buttons: ' + describe(el));
    });
  });
  return [...new Set(found)];
}
"""

# every button that asks first: its box opens, and Yes sends it. Nothing
# really goes - the forms and htmx are stopped just before sending
CONFIRMS_JS = r"""
async () => {
  const found = [], sent = [], wait = () => new Promise(r => setTimeout(r, 30));
  const describe = el => el.tagName.toLowerCase() + ' "' +
    (el.getAttribute('aria-label') || el.textContent.trim().replace(/\s+/g, ' ')).slice(0, 30) + '"';
  HTMLFormElement.prototype.requestSubmit = function () { sent.push(this); };
  HTMLFormElement.prototype.submit = function () { sent.push(this); };
  document.addEventListener('htmx:beforeRequest', e => { sent.push(e.detail.elt); e.preventDefault(); }, true);
  const dlg = document.getElementById('confirm-dialog'), yes = document.getElementById('confirm-yes-btn');
  for (const el of document.querySelectorAll('[data-confirm], [hx-confirm]')) {
    if (el.disabled) continue;
    sent.length = 0;
    if (el.tagName === 'FORM') el.dispatchEvent(new Event('submit', {bubbles: true, cancelable: true}));
    else el.click();
    await wait();
    if (!dlg || !dlg.open) { found.push("doesn't ask first: " + describe(el)); continue; }
    yes.click();
    await wait();
    if (dlg.open) dlg.close();
    if (!sent.length) found.push("Yes doesn't send: " + describe(el));
  }
  return found;
}
"""


def main():
    # page text can hold anything; a Windows console can't print it all
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--browser", default="", help="a browser channel, like msedge or chrome")
    parser.add_argument("--firefox", action="store_true", help="Firefox instead of Chromium")
    parser.add_argument("--axe", nargs="?", const=os.path.join(ROOT, ".tools", "node", "node_modules", "axe-core",
                                                              "axe.min.js"), help="check accessibility with axe-core too")
    parser.add_argument("--cache", default=os.path.join(ROOT, "demo-cache"), help="the sample photos' cache")
    args = parser.parse_args()
    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", PORT)) == 0:
            raise SystemExit(f"Port {PORT} is in use - stop what's running there first, or it would be checked instead")

    work = tempfile.mkdtemp(prefix="soloblog-phone-")
    data = os.path.join(work, "data")
    env = {**os.environ, "SESSION_SECRET": "phone-check", "UPDATE_CHECK": "0"}
    env.pop("DATA_DIR", None)
    subprocess.run([sys.executable, "tools/demo.py", data, "--password", "phone-check", "--cache", args.cache],
                   cwd=ROOT, env=env, check=True)
    server = subprocess.Popen([sys.executable, "app.py"], cwd=ROOT,
                              env={**env, "DATA_DIR": data, "PORT": str(PORT), "ENV": "production",
                                   "BASE_URL": BASE})
    problems = 0
    axe = Path(args.axe).read_text(encoding="utf-8") if args.axe else None
    rules = {}  # axe's rule -> (how bad, what it means, {path: an example})
    try:
        wait_up(BASE, server)
        with sync_playwright() as p:
            browser = p.firefox.launch() if args.firefox else p.chromium.launch(channel=args.browser or None)
            # Firefox has no phone mode in Playwright - a phone-sized window is what's checked there
            phone = {} if args.firefox else {"is_mobile": True, "has_touch": True}
            login = browser.new_context()
            r = login.request.post(f"{BASE}/login", form={"password": "phone-check"}, headers={"Origin": BASE},
                                   max_redirects=0)
            assert r.status in (302, 303), r.status
            pages = [(path, False) for path in PUBLIC] + [(path, True) for path in ADMIN] + \
                [(f"/admin/settings?tab={t}", True) for t in SETTINGS] + \
                [(f"/admin/help?tab={t}", True) for t in HELP]
            for width in WIDTHS:
                viewport = {"width": width, "height": 800}
                visitor = browser.new_context(viewport=viewport, **phone)
                admin = browser.new_context(viewport=viewport, storage_state=login.storage_state(), **phone)
                for path, as_admin in pages:
                    page = (admin if as_admin else visitor).new_page()
                    errors = []
                    page.on("pageerror", lambda e, errors=errors: errors.append(f"script error: {e}"))
                    page.goto(BASE + path, wait_until="networkidle")
                    # galleries' images load lazily - bring them in first
                    page.evaluate("document.querySelectorAll('.gallery').forEach(g => g.scrollIntoView())")
                    page.wait_for_timeout(600)
                    page.evaluate("window.scrollTo(0, 0)")
                    page.wait_for_timeout(200)
                    found = page.evaluate(CHECK_JS)
                    # the buttons work the same at any width - once is enough
                    if as_admin and width == WIDTHS[0]:
                        found += page.evaluate(CONFIRMS_JS)
                    found += list(dict.fromkeys(errors))
                    if axe and width == WIDTHS[0]:
                        page.add_script_tag(content=axe)
                        for v in page.evaluate("async () => (await axe.run(document, {resultTypes: ['violations']}))"
                                               ".violations.map(v => [v.id, v.impact, v.help, v.nodes.length, "
                                               "v.nodes[0].target.join(' ')])"):
                            rule = rules.setdefault(v[0], (v[1], v[2], {}))
                            rule[2][path] = f"{v[3]}x, e.g. {v[4][:80]}"
                    page.close()
                    if found:
                        problems += len(found)
                        print(f"\n{width}px  {path}")
                        for line in found:
                            print("   ", line)
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=20)
        shutil.rmtree(work, ignore_errors=True)
    if rules:
        print("\n## Accessibility (axe-core)")
        order = {"critical": 0, "serious": 1, "moderate": 2, "minor": 3}
        for rule, (impact, text, where) in sorted(rules.items(), key=lambda r: (order.get(r[1][0], 4), r[0])):
            problems += len(where)
            print(f"\n{impact}  {rule} - {text} ({len(where)} pages)")
            for path, example in list(where.items())[:8]:
                print(f"    {path}  {example}")
    print(f"\n{problems} problem(s)" if problems else "\nNothing found")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
