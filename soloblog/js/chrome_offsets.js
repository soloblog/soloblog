// how much of the screen a fixed header and a fixed footer cover, as
// --header-h and --footer-h on <html>: a jump to a heading lands below
// the header (scroll-padding, input.css), and a table of contents
// beside the post fits between the two (TableOfContents, ui)
function syncChromeOffsets() {
  var root = document.documentElement.style;
  var header = document.querySelector('[data-site-header]');
  var footer = document.querySelector('footer');
  var fixed = function (el) { return el && getComputedStyle(el).position === 'fixed'; };
  root.setProperty('--header-h', fixed(header) ? Math.ceil(header.getBoundingClientRect().bottom) + 'px' : '0px');
  // the page starts 3rem below a fixed header, however tall it is (a
  // stacked one has a second row), 2rem below the admin's thin bar -
  // Layout's padding is the guess before this runs
  var content = document.getElementById('page-content');
  var gap = header && header.hasAttribute('data-admin-bar') ? 32 : 48;
  if (content) content.style.paddingTop = fixed(header) ? Math.ceil(header.getBoundingClientRect().bottom) + gap + 'px' : '';
  root.setProperty('--footer-h', fixed(footer) ? Math.ceil(window.innerHeight - footer.getBoundingClientRect().top) + 'px' : '0px');
  flushEdges(content);
}
// Something edge to edge (data-flush: a full-width cover or banner, a
// landing page's bands) that opens the page meets the header, and one
// that closes it meets the footer - no strip of page between them. In
// the page's own positions, so a scrolled page doesn't throw it off; a
// fixed footer keeps the room it covers, so nothing ends up under it.
function flushEdges(content) {
  if (!content) return;
  var header = document.querySelector('[data-site-header]'), footer = document.querySelector('footer');
  var isFixed = function (el) { return el && getComputedStyle(el).position === 'fixed'; };
  var style = getComputedStyle(content), y = window.scrollY;
  var box = content.getBoundingClientRect();
  var padTop = parseFloat(style.paddingTop), padBottom = parseFloat(style.paddingBottom);
  var start = box.top + y + padTop, end = box.bottom + y - padBottom;
  // where the page can start: under a fixed header, or the page's own top -
  // and behind a floating one (inset from the top), as its pill floats over it
  var floating = isFixed(header) && header.getBoundingClientRect().top > 0;
  var floor = floating ? 0 : isFixed(header) ? header.getBoundingClientRect().bottom : box.top + y;
  var under = isFixed(footer) ? window.innerHeight - footer.getBoundingClientRect().top : 0;
  content.querySelectorAll('[data-flush]').forEach(function (el) {
    el.style.marginTop = el.style.marginBottom = '';
    el.style.removeProperty('--flush-top');
    var r = el.getBoundingClientRect(), m = getComputedStyle(el);
    if (Math.abs(r.top + y - parseFloat(m.marginTop) - start) < 2) {
      el.style.marginTop = -(start - floor) + 'px';
      // behind a floating header, what's written on it starts below the header
      if (floating) el.style.setProperty('--flush-top', Math.ceil(header.getBoundingClientRect().bottom) + 'px');
    }
    if (Math.abs(end - (r.bottom + y + parseFloat(m.marginBottom))) < 2) el.style.marginBottom = -(padBottom - under) + 'px';
  });
}
document.addEventListener('DOMContentLoaded', syncChromeOffsets);
window.addEventListener('resize', syncChromeOffsets);
// and whenever the header itself changes size - its logo or fonts
// arriving after the first measure, a phone turning - so what sits under
// it (the editor's toolbar) is exactly under it on every device
document.addEventListener('DOMContentLoaded', function () {
  var header = document.querySelector('[data-site-header]');
  if (header && window.ResizeObserver) new ResizeObserver(syncChromeOffsets).observe(header);
});
window.addEventListener('load', syncChromeOffsets);
// a live list swaps #page-content, padding and all
document.addEventListener('htmx:afterSettle', syncChromeOffsets);

// Settings > Style > Motion: an image shows daisyUI's shimmering
// skeleton until it has loaded (input.css fades the page itself in) - and
// the pictures a list brings in as it updates
function _skeletons() {
  if (!document.documentElement.hasAttribute('data-animate')) return;
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  document.querySelectorAll('#page-content img').forEach(function (img) {
    if (!img.complete) img.classList.add('skeleton');
  });
}
document.addEventListener('DOMContentLoaded', _skeletons);
document.addEventListener('htmx:afterSettle', _skeletons);
document.addEventListener('load', function (e) {
  if (e.target.tagName === 'IMG') e.target.classList.remove('skeleton');
}, true);
document.addEventListener('error', function (e) {
  if (e.target.tagName === 'IMG') e.target.classList.remove('skeleton');
}, true);

// panels beside the column (Beside, ui - the contents, a tag cloud,
// archive links) go in the margin only when it's wide enough for them
// (13rem + 1.5rem); otherwise they stay in the page
function placeSidePanels() {
  var rem = parseFloat(getComputedStyle(document.documentElement).fontSize);
  var page = document.getElementById('page-content');
  // the end of the page's content, not its padding - down to there, a
  // panel sat flush on the footer
  var pageEnd = page ? page.getBoundingClientRect().bottom - parseFloat(getComputedStyle(page).paddingBottom) : 0;
  document.querySelectorAll('[data-side-panel]').forEach(function (side) {
    side.parentElement.style.minHeight = '';
    var box = side.parentElement.getBoundingClientRect();
    var room = side.dataset.sidePanel === 'right' ? document.documentElement.clientWidth - box.right : box.left;
    // a panel can ask for more than the usual 15.5rem - 13 and the 2.5rem
    // gap (ui.Beside) - as the admin menu does
    side.toggleAttribute('data-beside', room >= (parseFloat(side.dataset.sideRoom) || 15.5) * rem + 8);
    // for what's styled by it elsewhere on the page - not body:has(), which
    // restyled the whole page on every change
    document.documentElement.toggleAttribute('data-side-beside', !!document.querySelector('[data-side-panel][data-beside]'));
    // beside a short column (a last page of a few posts), a taller panel
    // ran into the footer: the column grows to fit it, and its gap below
    // (from where it starts: the admin menu sits level with the page, below its top padding)
    var needed = side.hasAttribute('data-beside') ?
      parseFloat(getComputedStyle(side).paddingTop) + side.firstElementChild.scrollHeight + 1.5 * rem : 0;
    if (needed > box.height) {
      side.parentElement.style.minHeight = needed + 'px';
      pageEnd += needed - box.height;
      box = side.parentElement.getBoundingClientRect();
    }
    // beside, it follows the reader to the end of the page - comments
    // and all - not just the end of the text it starts beside: on a
    // short post it scrolled up under a fixed header
    var extra = page && side.hasAttribute('data-beside') ? pageEnd - box.bottom : 0;
    side.style.bottom = extra > 0 ? -extra + 'px' : '';
    // in the margin it scrolls and may fade at its foot; moved into the
    // page, it doesn't - a fade left from before stayed on the contents
    if (typeof _scrollHints === 'function') _scrollHints(side);
  });
  fitSidePanels();
  // the admin's rail (ui.AdminRail) shows: the drawer button and
  // Settings' own tabs aren't needed - its menu has them
  var admin = document.querySelector('[data-admin-rail]');
  document.documentElement.toggleAttribute('data-admin-beside', !!(admin && admin.offsetWidth));
  // a panel shown beside the column isn't shown again after the content
  document.querySelectorAll('[data-side-fallback]').forEach(function (copy) {
    var column = document.querySelector('[data-side-panel="' + copy.dataset.sideFallback + '"]');
    copy.hidden = !!(column && column.hasAttribute('data-beside'));
  });
}
// Beside, a panel follows the reader between the header and the end of the
// column (Beside, ui). Near the end of a short page there isn't a whole
// screen of room left: it was pushed up under the header, its foot flush on
// the footer (the admin menu with Settings open). It gets shorter instead,
// and its list scrolls inside.
function fitSidePanels() {
  var rem = parseFloat(getComputedStyle(document.documentElement).fontSize);
  var header = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--header-h')) || 0;
  document.querySelectorAll('[data-side-panel][data-beside]').forEach(function (side) {
    var inner = side.firstElementChild;
    inner.style.maxHeight = '';
    // one that starts just under where it would stop (the admin side panel,
    // level with the page) stops where it starts: it crept up a little on
    // the first scroll. One further down still follows the reader up.
    // down to the footer, or the window's foot, whichever comes first - not
    // just the end of its column: on a short page that left empty room
    // under it while its list was cut and faded
    var footer = document.querySelector('footer');
    var end = Math.min(footer ? footer.getBoundingClientRect().top - 1.5 * rem : Infinity,
                       window.innerHeight - 1.5 * rem);
    inner.style.top = '';
    var stopsAt = header + 1.5 * rem;
    var startsAt = side.parentElement.getBoundingClientRect().top + window.scrollY + parseFloat(getComputedStyle(side).paddingTop || 0);
    // ...unless that little room is what lets it fit whole (the end of a
    // short page); one that scrolls inside either way stays put
    var tall = inner.scrollHeight, fitsOnlyHigher = tall > end - startsAt + 16 && tall <= end - stopsAt + 16;
    if (startsAt > stopsAt && startsAt - stopsAt <= 3 * rem && !fitsOnlyHigher) inner.style.top = startsAt + 'px';
    var stuckAt = parseFloat(getComputedStyle(inner).top) || 0;
    var room = end - stuckAt;
    // a sliver short (the card's own padding and rounded foot) it keeps its
    // height, a little into its gap above the footer, rather than cut
    if (room < inner.offsetHeight - 16) inner.style.maxHeight = Math.max(6 * rem, room) + 'px';
    if (typeof _scrollHint === 'function') _scrollHint(inner);
    // and again whenever what's in it changes size - Settings folding away
    // ends after its animation, not when it starts
    if (window.ResizeObserver && !inner._sizeWatched) {
      inner._sizeWatched = true;
      new ResizeObserver(function () { fitSidePanels(); }).observe(inner.firstElementChild || inner);
    }
  });
}
var _fitPending = false;
window.addEventListener('scroll', function () {
  if (_fitPending) return;
  _fitPending = true;
  requestAnimationFrame(function () { _fitPending = false; fitSidePanels(); });
}, { passive: true });
window.addEventListener('resize', placeSidePanels);
document.addEventListener('DOMContentLoaded', placeSidePanels);
// images change the page's length as they load
window.addEventListener('load', placeSidePanels);
// a live list swaps the page without running its scripts - place again
document.addEventListener('htmx:afterSettle', placeSidePanels);
// and when a panel opens or closes a part of itself (the admin menu's
// Settings and Help): the page grows to fit it, so the footer moves down
// instead of covering the end of it
document.addEventListener('toggle', function (e) {
  if (e.target.closest && e.target.closest('[data-side-panel]')) placeSidePanels();
}, true);

// A row of tabs (ui.Tabs) that doesn't fit keeps the tabs that do - the
// current one always - and lists the rest under More at its end
function fitTabs() {
  document.querySelectorAll('[data-fit-tabs]').forEach(function (row) {
    var more = row.querySelector('[data-tabs-more]');
    var menu = more && document.getElementById(more.getAttribute('popovertarget'));
    // a row being swapped out (Help's search) can lose its menu mid-way
    if (!menu) return;
    var tabs = [].slice.call(row.querySelectorAll(':scope > .tab:not([data-tabs-more])'));
    tabs.forEach(function (t) { t.hidden = false; });
    more.hidden = true;
    menu.replaceChildren();
    if (!row.clientWidth || row.scrollWidth <= row.clientWidth + 1) return;
    more.hidden = false;
    var moved = [];
    for (var i = tabs.length - 1; i >= 0 && row.scrollWidth > row.clientWidth + 1; i--) {
      if (tabs[i].classList.contains('tab-active')) continue;
      tabs[i].hidden = true;
      moved.unshift(tabs[i]);
    }
    moved.forEach(function (t) {
      var li = document.createElement('li'), link = document.createElement('a');
      link.href = t.getAttribute('href');
      link.textContent = t.textContent;
      li.appendChild(link);
      menu.appendChild(li);
    });
  });
}
window.addEventListener('resize', fitTabs);
document.addEventListener('DOMContentLoaded', fitTabs);
document.addEventListener('htmx:afterSettle', fitTabs);

// a matching pair of themes (Settings > Appearance, the welcome): picks
// the light one - previewing it, as its own swatch does - and the dark one
function choosePair(light, dark) {
  var l = document.querySelector('input[name=theme][value="' + light + '"]');
  var d = document.querySelector('input[name=theme_dark][value="' + dark + '"]');
  if (l) l.closest('label').click();
  if (d) { d.checked = true; d.dispatchEvent(new Event('change', { bubbles: true })); }
}

// the visitor's theme menu (VisitorThemeSwitcher, ui): Default forgets
// their pick, so the site's own shows again - following their device when
// the site does (siteTheme, VISITOR_THEME_INIT_JS)
function resetTheme() {
  try { localStorage.removeItem('theme'); } catch (e) {}
  if (window.siteTheme) document.documentElement.setAttribute('data-theme', window.siteTheme());
  markThemeDefault();
}
function markThemeDefault() {
  var none = true;
  try { none = !localStorage.getItem('theme'); } catch (e) {}
  document.querySelectorAll('[data-theme-default]').forEach(function (a) { a.classList.toggle('menu-active', none); });
  if (none) document.querySelectorAll('[data-set-theme].menu-active').forEach(function (a) { a.classList.remove('menu-active'); });
}
document.addEventListener('DOMContentLoaded', markThemeDefault);
document.addEventListener('click', function (e) {
  if (e.target.closest && e.target.closest('[data-set-theme]')) setTimeout(markThemeDefault, 0);
});

// a page with a background sound: Back to top sits above its button
function _markSound() { document.documentElement.toggleAttribute('data-sound', !!document.getElementById('sound-float')); }
document.addEventListener('DOMContentLoaded', _markSound);
document.addEventListener('htmx:afterSettle', _markSound);
// a page's background sound (SoundButton, ui): play and stop, looping
function toggleSound(btn) {
  var audio = document.getElementById('background-sound');
  if (!audio) return;
  var on = audio.paused;
  if (on) audio.play().catch(function () {}); else audio.pause();
  btn.setAttribute('aria-pressed', on ? 'true' : 'false');
  var label = on ? btn.dataset.stop : btn.dataset.play;
  btn.setAttribute('aria-label', label);
  btn.setAttribute('data-tip', label);
  btn.querySelector('[data-sound-off]').classList.toggle('hidden', on);
  btn.querySelector('[data-sound-on]').classList.toggle('hidden', !on);
}

function copyHeadingLink(btn) {
  // a folding section's button sits beside its heading, not in it
  var id = btn.dataset.target || (btn.closest('[id]') || {}).id;
  if (id) copyLink(window.location.pathname + '#' + id, btn);
}

// a heading inside a folded section (pages.fold_sections): open the
// way to it before the jump, from a link or from the address itself
function openFoldsTo(id) {
  var el = id && document.getElementById(id);
  var opened = false;
  for (var d = el && el.closest('details'); d; d = d.parentElement && d.parentElement.closest('details')) {
    if (!d.open) { d.open = true; opened = true; }
  }
  return opened ? el : null;
}
document.addEventListener('click', function (e) {
  var a = e.target.closest && e.target.closest('a[href^="#"]');
  if (a) openFoldsTo(decodeURIComponent(a.getAttribute('href').slice(1)));
});
document.addEventListener('DOMContentLoaded', function () {
  var el = openFoldsTo(decodeURIComponent(location.hash.slice(1)));
  if (el) el.scrollIntoView();
});
