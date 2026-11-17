// a <details class="collapse" data-panel="..."> remembers its own
// open/closed state per browser (localStorage) and wins over whatever
// the server rendered by default the next time it shows up - "pinning"
// a section open (or closed) once means it stays that way from then
// on, wherever that panel renders (the post editor's own settings
// drawer, Media's own details drawer, ...). Runs on every full page
// load AND every htmx swap (htmx:afterSwap) - a swapped-in fragment
// never fires DOMContentLoaded again, and Media's own drawer content
// is exactly that: fetched and swapped in per-image, not loaded fresh.
// A post's or guide's contents on a phone start folded - open, the whole
// list was a screenful before the first line - and remember their own
// state apart from a wide screen's, where they sit beside the page.
function restorePanelStates(root) {
  var phone = window.matchMedia('(width < 40rem)').matches;
  (root || document).querySelectorAll('details[data-panel]').forEach(function (d) {
    var folded = phone && d.dataset.panel === 'toc';
    var key = 'soloblog-panel-open:' + d.dataset.panel + (folded ? ':phone' : '');
    var stored = null;
    try { stored = localStorage.getItem(key); } catch (err) {}
    if (stored !== null) d.open = stored === '1';
    else if (folded) d.open = false;
    if (d.dataset.panelBound) return;
    d.dataset.panelBound = '1';
    d.addEventListener('toggle', function () {
      try { localStorage.setItem(key, d.open ? '1' : '0'); } catch (err) {}
    });
  });
}
document.addEventListener('DOMContentLoaded', function () { restorePanelStates(document); });
// on document: these scripts run in <head>, before there's a body
document.addEventListener('htmx:afterSwap', function (e) { restorePanelStates(e.target); });

// A folding section (daisyUI's collapse on a <details> - Settings'
// panels, a post's folding headings, the contents) opens and closes
// smoothly: a browser only snaps a <details> open or shut, and daisyUI
// animates only its checkbox kind. Height and a fade over 0.3s, like the
// drawers; not with Animations off or the reader's "reduce motion". The
// <details> still opens and closes itself, so its toggle event - and the
// remembered state above - work as before.
function _foldMotion() {
  return document.documentElement.hasAttribute('data-animate') &&
         !matchMedia('(prefers-reduced-motion: reduce)').matches;
}
document.addEventListener('click', function (e) {
  if (e.defaultPrevented || !_foldMotion() || !e.target.closest) return;
  var summary = e.target.closest('summary');
  var d = summary && summary.parentElement;
  if (!d || d.tagName !== 'DETAILS' || !d.classList.contains('collapse') || d.firstElementChild !== summary) return;
  // a link or button inside the title (a heading's copy-link) does its own thing
  var inner = e.target.closest('a, button, input, select, textarea');
  if (inner && summary.contains(inner)) return;
  e.preventDefault();
  var opening = !d.open || d.hasAttribute('data-closing');
  var from = d.getBoundingClientRect().height;
  if (d._fold) d._fold.cancel();
  if (d._fade) d._fade.cancel();
  d.removeAttribute('data-closing');
  // data-folding pauses daisyUI's own 0.2s one (input.css) - it would
  // fight this, throw off the heights measured here, and Firefox skips it
  var content = summary.nextElementSibling;
  d.setAttribute('data-folding', '');
  d.open = false;
  var shut = d.getBoundingClientRect().height;
  d.open = true;
  var to = opening ? d.getBoundingClientRect().height : shut;
  if (!opening) d.setAttribute('data-closing', '');
  var timing = {duration: 300, easing: 'ease-out', fill: 'forwards'};
  d.style.overflow = 'hidden';
  var fold = d._fold = d.animate({height: [from + 'px', to + 'px']}, timing);
  if (content) d._fade = content.animate({opacity: opening ? [0, 1] : [1, 0]}, timing);
  fold.onfinish = function () {
    if (!opening) { d.removeAttribute('data-closing'); d.open = false; }
    d.style.overflow = '';
    fold.cancel();
    if (d._fade) d._fade.cancel();
    d._fold = d._fade = null;
    // the browser takes in "shut" now, while daisyUI's transitions are
    // still off - otherwise it sees that and them back on together, and
    // its 0.2s delay showed the content again for a moment (Firefox)
    d.getBoundingClientRect();
    requestAnimationFrame(function () { if (!d._fold) d.removeAttribute('data-folding'); });
  };
});
