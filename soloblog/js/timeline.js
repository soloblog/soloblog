// A timeline with its line down the middle (ui.timeline_cls, data-stagger):
// each entry is a row of its own, so beside every card the other side stood
// empty for that card's whole height. Each row is drawn up into the room
// beside the one before, from that one's dot down - never onto what's
// already on its own side, so the order still reads down the line.
// One-sided (a narrow screen), there's nothing to draw up.
(function () {
  var GAP = 24, DOTS = 48;
  function settle(list) {
    var rows = [].slice.call(list.children);
    rows.forEach(function (li) {
      li.style.marginTop = '';
      var hr = li.lastElementChild;
      if (hr && hr.tagName === 'HR') { hr.style.height = ''; hr.style.alignSelf = ''; }
    });
    if (rows.length < 2 || !window.matchMedia || !matchMedia('(min-width: 768px)').matches) return;
    var top = list.getBoundingClientRect().top;
    var read = rows.map(function (li) {
      var r = li.getBoundingClientRect(), dot = li.querySelector(':scope > .timeline-middle');
      var d = dot ? dot.getBoundingClientRect() : r;
      return {
        top: r.top - top, dot: d.top + d.height / 2 - r.top,
        parts: [].filter.call(li.children, function (c) {
          return /\btimeline-(start|end)\b/.test(c.className) && c.offsetParent;
        }).map(function (c) {
          var b = c.getBoundingClientRect();
          return { side: /\btimeline-start\b/.test(c.className) ? 'start' : 'end', top: b.top - r.top, bottom: b.bottom - r.top };
        })
      };
    });
    var free = {}, lastDot = 0, up = 0;
    read.forEach(function (row, i) {
      var natural = row.top - up, at = natural;
      if (i) {
        // it starts level with the last one's dot: cards of a height step down the line half a card at a time
        at = Math.max(lastDot, lastDot + DOTS - row.dot);
        row.parts.forEach(function (p) { if (p.side in free) at = Math.max(at, free[p.side] - p.top); });
        at = Math.min(at, natural);
        rows[i].style.marginTop = (at - natural) + 'px';
        up += natural - at;
      }
      row.parts.forEach(function (p) { free[p.side] = at + p.bottom + GAP; });
      lastDot = at + row.dot;
    });
    // the line stops at the last dot: an earlier, taller row's own piece of it ran on past
    var end = rows[rows.length - 1].querySelector(':scope > .timeline-middle');
    if (!end) return;
    var e = end.getBoundingClientRect(), stop = e.top + e.height / 2;
    rows.slice(0, -1).forEach(function (li) {
      var hr = li.lastElementChild;
      if (!hr || hr.tagName !== 'HR') return;
      var h = hr.getBoundingClientRect();
      if (h.bottom <= stop) return;
      hr.style.alignSelf = 'start';
      hr.style.height = Math.max(0, stop - h.top) + 'px';
    });
  }
  function all() { [].forEach.call(document.querySelectorAll('[data-stagger]'), settle); }
  function start() {
    all();
    // again when the width changes (its own height changes as it settles, and doesn't count)
    if (window.ResizeObserver) {
      [].forEach.call(document.querySelectorAll('[data-stagger]'), function (list) {
        var wide = list.clientWidth;
        new ResizeObserver(function () {
          if (list.clientWidth === wide) return;
          wide = list.clientWidth;
          settle(list);
        }).observe(list);
      });
    }
    window.addEventListener('load', all);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(all);
    document.addEventListener('htmx:afterSettle', all);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
