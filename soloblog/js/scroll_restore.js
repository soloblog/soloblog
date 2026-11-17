// A plain <form method="post"> action (bulk approve/delete/restore,
// reordering pinned pages or social links, etc) still does a real
// POST-redirect-GET round trip - the fresh page that lands always
// starts scrolled to the top, which reads as "the page jumped" for an
// action that conceptually didn't go anywhere (you clicked one small
// button in a long list). htmx-driven forms (every Save button)
// already avoid this entirely - they swap one small target in place,
// no navigation at all - so this only needs to step in for the
// plain ones. Scoped to submit, not every click/link - genuine
// navigation (switching tabs, Prev/Next pagination, clicking a post)
// takes you to different content, where landing at the top is
// correct, not a bug.
document.addEventListener('submit', function (e) {
  var form = e.target;
  // a live list's form (LIVE_JS) swaps in place - nothing to restore
  if (e.defaultPrevented) return;
  if (form.matches('[hx-post],[hx-get],[hx-put],[hx-delete],[hx-patch]')) return;
  try { sessionStorage.setItem('soloblog-scroll-y', window.scrollY); } catch (err) {}
});
document.addEventListener('DOMContentLoaded', function () {
  var y = sessionStorage.getItem('soloblog-scroll-y');
  if (y === null) return;
  sessionStorage.removeItem('soloblog-scroll-y');
  window.scrollTo(0, parseInt(y, 10) || 0);
});
// The admin's menu keeps its place from page to page: Settings > Posts,
// far down it, mustn't send it back to the top. Arriving another way (a
// search, a link), the page's own entry is scrolled into view instead.
function _navBox(nav) {
  var inside = nav.querySelector('[data-scroll-hint]');
  if (inside && /auto|scroll/.test(getComputedStyle(inside).overflowY)) return inside;
  for (var e = nav; e && e !== document.body; e = e.parentElement) {
    if (/auto|scroll/.test(getComputedStyle(e).overflowY)) return e;
  }
  return null;
}
document.addEventListener('click', function (e) {
  var link = e.target.closest && e.target.closest('[data-admin-nav] a[href]');
  var box = link && _navBox(link.closest('[data-admin-nav]'));
  if (box) try { sessionStorage.setItem('soloblog-nav-y', box.scrollTop); } catch (err) {}
});
document.addEventListener('DOMContentLoaded', function () {
  var y = null;
  try { y = sessionStorage.getItem('soloblog-nav-y'); sessionStorage.removeItem('soloblog-nav-y'); } catch (err) {}
  document.querySelectorAll('[data-admin-nav]').forEach(function (nav) {
    var box = _navBox(nav);
    if (!box || box.scrollHeight <= box.clientHeight) return;
    if (y !== null) { box.scrollTop = parseInt(y, 10) || 0; return; }
    var here = nav.querySelector('a[aria-current="page"], a.menu-active');
    if (here) {
      var r = here.getBoundingClientRect(), b = box.getBoundingClientRect();
      if (r.top < b.top || r.bottom > b.bottom) box.scrollTop += r.top - b.top - b.height / 3;
    }
  });
});
