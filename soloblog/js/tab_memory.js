// An admin page's tabs (Media's Unused, Posts' Drafts, a Settings page...)
// are remembered in this browser: coming back to the page from the menu,
// or any address without a tab in it, opens the tab you were on. An
// address that names a tab keeps it.
(function () {
  var path = location.pathname;
  if (path.indexOf('/admin') !== 0) return;
  function read(key) {
    try { return JSON.parse(localStorage.getItem(key) || '{}') || {}; } catch (e) { return {}; }
  }
  var LAST = 'soloblog-tabs:' + path, FIRST = 'soloblog-tabs-default:' + path;
  // before the page draws (this runs in <head>), so the other tab never shows
  if (!location.search) {
    var last = read(LAST), first = read(FIRST), query = [];
    Object.keys(last).forEach(function (k) {
      if (last[k] !== first[k]) query.push(encodeURIComponent(k) + '=' + encodeURIComponent(last[k]));
    });
    if (query.length) { location.replace(path + '?' + query.join('&') + location.hash); return; }
  }
  // the tab a row of tabs has open: the one setting its links change
  function remember() {
    var last = read(LAST), first = read(FIRST), plain = !location.search;
    document.querySelectorAll('[data-fit-tabs]').forEach(function (row) {
      var links = [].slice.call(row.querySelectorAll('a.tab[href]')), values = {};
      var open = row.querySelector('a.tab.tab-active, a.tab[aria-current="page"]');
      if (!open || links.length < 2) return;
      links.forEach(function (a) {
        new URL(a.href, location.href).searchParams.forEach(function (v, k) { (values[k] = values[k] || {})[v] = 1; });
      });
      var url = new URL(open.href, location.href);
      Object.keys(values).forEach(function (k) {
        if (Object.keys(values[k]).length < 2 || !url.searchParams.has(k)) return;
        last[k] = url.searchParams.get(k);
        if (plain) first[k] = last[k];
      });
    });
    try {
      localStorage.setItem(LAST, JSON.stringify(last));
      localStorage.setItem(FIRST, JSON.stringify(first));
    } catch (e) {}
  }
  document.addEventListener('DOMContentLoaded', remember);
  // a list's tabs open in place, without loading the page (live.js)
  document.addEventListener('live:swapped', remember);
})();
