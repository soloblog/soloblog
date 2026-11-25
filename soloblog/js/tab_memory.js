// An admin page's tabs (Media's Unused, Posts' Drafts...) and its list's
// filters and sort (Type: Pages, Tag, Sort: Oldest - ui.FilterSelect) are
// remembered in this browser: coming back to the page from the menu, or
// any address without them in it, opens it as you left it. A search
// isn't kept - it's a one-off question. An address that names a tab or
// a filter keeps it.
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
  // what a row of tabs or a filter's menu has chosen: the one setting its
  // links change, as its chosen link has it
  var CHOICES = [['[data-fit-tabs]', 'a.tab[href]', 'a.tab.tab-active, a.tab[aria-current="page"]'],
                 ['[popover][id^="filter-"]', 'a[href]', 'a[aria-current="true"]']];
  function remember() {
    var last = read(LAST), first = read(FIRST), plain = !location.search;
    CHOICES.forEach(function (c) { document.querySelectorAll(c[0]).forEach(function (row) {
      var links = [].slice.call(row.querySelectorAll(c[1])), values = {};
      var open = row.querySelector(c[2]);
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
    }); });
    try {
      localStorage.setItem(LAST, JSON.stringify(last));
      localStorage.setItem(FIRST, JSON.stringify(first));
    } catch (e) {}
  }
  document.addEventListener('DOMContentLoaded', remember);
  // a list's tabs open in place, without loading the page (live.js)
  document.addEventListener('live:swapped', remember);
})();
