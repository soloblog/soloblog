// A drawer or sidebar opening closes every menu left open under it - the
// admin sidebar (its checkbox), and any slide-over (media details, post
// settings, the editor's help), which open by losing translate-x-full -
// however it was opened: a click, a key, a shortcut
function closeMenus() {
  document.querySelectorAll(':popover-open').forEach(function (m) { try { m.hidePopover(); } catch (e) {} });
  var inMenu = document.activeElement && document.activeElement.closest &&
    document.activeElement.closest('.dropdown, .easymde-dropdown');
  if (inMenu) document.activeElement.blur();
}
document.addEventListener('change', function (e) {
  if (e.target.classList && e.target.classList.contains('drawer-toggle') && e.target.checked) closeMenus();
});
new MutationObserver(function (changes) {
  changes.forEach(function (c) {
    if (c.oldValue && c.oldValue.indexOf('translate-x-full') >= 0 && !c.target.classList.contains('translate-x-full')) {
      closeMenus();
    }
  });
}).observe(document.documentElement, {subtree: true, attributes: true, attributeFilter: ['class'], attributeOldValue: true});
// Media's details drawer: one shared slide-over, its content loaded per
// image by htmx (MediaCard, routes/media.py)
function toggleMediaDetails(open) {
  var panel = document.getElementById('media-details-panel');
  var backdrop = document.getElementById('media-details-backdrop');
  if (!panel) return;
  panel.toggleAttribute('data-open', !!open);
  if (panel.hasAttribute('data-docked')) { _showDocked(panel); return; }
  var wasOpen = !panel.hasAttribute('inert');
  if (!open) panelClosed(panel);
  panel.classList.toggle('translate-x-full', !open);
  panel.toggleAttribute('inert', !open);
  backdrop.classList.toggle('hidden', !open);
  if (open && !wasOpen) panelOpened(panel);
}
// Escape closes what's on top: a dialog or menu over the drawer first (as design_preview's)
document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape' && !document.querySelector('dialog[open], :popover-open')) toggleMediaDetails(false);
});
// Media's details: on a wide screen beside the page's column once a file
// is picked, as Post settings is (placePostSettings, the same rule) -
// nothing there until then; a sidebar over the page everywhere else
function _showDocked(panel) {
  var open = panel.hasAttribute('data-open');
  panel.hidden = !open;
  panel.toggleAttribute('inert', !open);
  // Main makes room for it, as for Post settings (ui.Layout)
  document.documentElement.toggleAttribute('data-settings-docked', open);
  window.dispatchEvent(new Event('resize'));
}
// A side panel docked beside the page (Post settings, Media's details):
// straight after the page's column, which starts beside the admin's rail -
// past the column the admin is the panels' colour already (ui.Layout), so
// it's one with what's beyond it
function _dockBeside(panel, dock) {
  var column = document.getElementById('page-content');
  panel.style.left = dock && column ? Math.round(column.parentElement.getBoundingClientRect().right) + 'px' : '';
}
function placeMediaDetails() {
  var panel = document.getElementById('media-details-panel');
  if (!panel) return;
  var rem = parseFloat(getComputedStyle(document.documentElement).fontSize);
  var rail = document.querySelector('[data-admin-rail]');
  var left = rail && rail.offsetWidth ? rail.offsetWidth : 0;
  var dock = left > 0 && window.innerWidth - left - 22.5 * rem >= 50 * rem;
  if (dock !== panel.hasAttribute('data-docked')) {
    panel.style.transition = 'none';
    panel.toggleAttribute('data-docked', dock);
    // a line on its right, as Post settings has (_DOCKED_CLS, pin_location.js)
    ['z-30', 'top-12', 'border-r-[length:var(--border)]', 'border-base-300'].forEach(function (c) {
      panel.classList.toggle(c, dock);
    });
    ['shadow-xl', 'transition-transform', 'duration-200', 'z-40'].forEach(function (c) { panel.classList.toggle(c, !dock); });
    document.getElementById('media-details-backdrop').classList.add('hidden');
    if (dock) {
      panel.classList.remove('translate-x-full');
      _showDocked(panel);
    } else {
      panel.hidden = false;
      document.documentElement.removeAttribute('data-settings-docked');
      // a sidebar again: closed, until a file is picked
      panel.removeAttribute('data-open');
      panel.classList.add('translate-x-full');
      panel.setAttribute('inert', '');
      window.dispatchEvent(new Event('resize'));
    }
    panel.getBoundingClientRect();
    panel.style.transition = '';
  }
  _dockBeside(panel, dock);
}
document.addEventListener('DOMContentLoaded', placeMediaDetails);
window.addEventListener('resize', placeMediaDetails);
// a live list swaps the page, the panel with it
document.addEventListener('htmx:afterSettle', placeMediaDetails);
// the contact form empties itself once a message has gone
document.addEventListener('htmx:afterSettle', function (e) {
  var status = document.getElementById('contact-status');
  if (e.target.id === 'contact-status' && status && status.classList.contains('text-success')) {
    var form = document.getElementById('contact-form');
    if (form) form.reset();
  }
});
// the height you can see - less while a phone's keyboard is open, which
// 100dvh doesn't follow. SEARCH_DIALOG_BOX (ui) fits it, so a picker's
// Close stays above the keyboard instead of below the fold.
(function () {
  var vv = window.visualViewport;
  if (!vv) return;
  var seen = function () { document.documentElement.style.setProperty('--seen-h', vv.height + 'px'); };
  vv.addEventListener('resize', seen);
  seen();
})();
// the admin drawer's open and close buttons: real buttons, for the keyboard
// and screen readers, flipping daisyUI's hidden checkbox (data-toggles)
document.addEventListener('click', function (e) {
  var btn = e.target.closest && e.target.closest('button[data-toggles]');
  var box = btn && document.getElementById(btn.getAttribute('data-toggles'));
  if (!box) return;
  box.checked = !box.checked;
  box.dispatchEvent(new Event('change', {bubbles: true}));
});
// A page shown in a Design page's live preview (or a preset's) keeps
// showing it as you click around in the frame: a link to another page of
// the site carries the preview along, instead of showing the saved site
(function () {
  if (window.top === window.self) return;
  var params = new URLSearchParams(location.search), keep = null;
  ['design_preview', 'preset_preview'].forEach(function (k) { if (params.get(k)) keep = [k, params.get(k)]; });
  if (!keep) return;
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[href]');
    if (!a || a.target === '_blank' || a.origin !== location.origin || a.getAttribute('href').charAt(0) === '#') return;
    var url = new URL(a.href);
    if (url.pathname.indexOf('/admin') === 0) return;
    url.searchParams.set(keep[0], keep[1]);
    a.href = url.pathname + url.search + url.hash;
  }, true);
})();
// The wheel over a side panel (data-own-scroll: Post settings, Help,
// the admin menu, Media's details) scrolls the panel, or nothing - not
// the page behind it, which moved under a panel with nothing to scroll
document.addEventListener('wheel', function (e) {
  var panel = e.target.closest && e.target.closest('[data-own-scroll]');
  if (!panel || e.ctrlKey || Math.abs(e.deltaX) > Math.abs(e.deltaY)) return;
  for (var el = e.target; el && el !== panel.parentElement; el = el.parentElement) {
    var s = getComputedStyle(el), scrolls = /(auto|scroll)/.test(s.overflowY) && el.scrollHeight > el.clientHeight + 1;
    if (scrolls && (e.deltaY < 0 ? el.scrollTop > 0 : el.scrollTop + el.clientHeight < el.scrollHeight - 1)) return;
  }
  e.preventDefault();
}, {passive: false});

// /...#getting-started (Open Getting started, after it was dismissed): its
// box open on arrival
document.addEventListener('DOMContentLoaded', function () {
  var box = location.hash === '#getting-started' && document.getElementById('getting-started');
  if (box && box.showModal) box.showModal();
});
