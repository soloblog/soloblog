// Post settings: a full-height rail beside the text where the screen has
// room for it, always there, as the admin's rail is on the left (ui.AdminRail);
// a sidebar, opened over the text with Settings, everywhere else and in
// Focus mode. open: true, false, or 'button' (the Settings button). Between
// the two it changes at once. As a rail it's under a sidebar's backdrop
// (z-[39]), dimmed with the page; as a sidebar it's over it
// a line on its right, where it meets the room past it - the page's
// column has the one on its left (ui.Layout)
var _DOCKED_CLS = ['z-30', 'top-12', 'border-r-[length:var(--border)]', 'border-base-300'];
var _SLIDING_CLS = ['shadow-xl', 'transition-transform', 'duration-200', 'z-40'];
function postSettingsDocked() {
  var panel = document.getElementById('post-settings-panel');
  return !!(panel && panel.hasAttribute('data-docked'));
}
function togglePostSettings(open) {
  var panel = document.getElementById('post-settings-panel');
  var backdrop = document.getElementById('post-settings-backdrop');
  if (!panel) return;
  // beside the editor it's always there - nothing to open or close
  if (panel.hasAttribute('data-docked')) return;
  if (open === 'button') open = true;
  var wasOpen = !panel.hasAttribute('inert');
  if (!open) panelClosed(panel);
  panel.classList.toggle('translate-x-full', !open);
  // closed, it's off-screen: out of reach of Tab and screen readers too
  panel.toggleAttribute('inert', !open);
  backdrop.classList.toggle('hidden', !open);
  if (open && !wasOpen) panelOpened(panel);
  // on a touch screen the keyboard would cover it
  if (open && !matchMedia('(hover: hover)').matches && document.activeElement) document.activeElement.blur();
  // the back-to-top button checks the drawer on every scroll
  // (SCROLL_TOP_JS, app.py) - a scroll event makes it look now
  window.dispatchEvent(new Event('scroll'));
}
// docked or not, and where: on load, as the window changes, as the page
// scrolls (it stays under the header) and in and out of Focus mode
function placePostSettings() {
  var panel = document.getElementById('post-settings-panel'), form = document.getElementById('post-form');
  if (!panel || !form) return;
  var rem = parseFloat(getComputedStyle(document.documentElement).fontSize);
  // a full-height rail on the right of the admin's frame (ui.AdminRail on
  // the left), where the editor still has its own width between the two
  var rail = document.querySelector('[data-admin-rail]');
  var left = rail && rail.offsetWidth ? rail.offsetWidth : 0;
  // Settings > Editor can keep it a sidebar whatever the room
  var allowed = !window.EDITOR_PREFS || window.EDITOR_PREFS.settingsBeside !== false;
  var dock = allowed && left > 0 && !document.documentElement.hasAttribute('data-focus-mode') &&
             window.innerWidth - left - 22.5 * rem >= 50 * rem;
  if (dock !== panel.hasAttribute('data-docked')) {
    // at once, not sliding away - as the admin side panel goes
    panel.style.transition = 'none';
    panel.toggleAttribute('data-docked', dock);
    document.documentElement.toggleAttribute('data-settings-docked', dock);
    _DOCKED_CLS.forEach(function (c) { panel.classList.toggle(c, dock); });
    _SLIDING_CLS.forEach(function (c) { panel.classList.toggle(c, !dock); });
    document.getElementById('post-settings-backdrop').classList.add('hidden');
    if (dock) {
      panel.classList.remove('translate-x-full');
      panel.removeAttribute('inert');
    } else {
      panel.classList.add('translate-x-full');
      panel.setAttribute('inert', '');
    }
    // its ✕ and the Settings button are the sidebar's: as a rail it's
    // always there, nothing to open or close
    panel.querySelectorAll('[aria-label="Close settings"]').forEach(function (b) { b.hidden = dock; });
    document.querySelectorAll('[data-actions-row] [aria-label="Settings"], #editor-actions [aria-label="Settings"]')
      .forEach(function (b) { b.hidden = dock; });
    panel.getBoundingClientRect();  // the change drawn with no transition, then transitions back for the sidebar
    panel.style.transition = '';
    // the page makes room for it (Layout's main), and side panels and the
    // toolbar measure again
    window.dispatchEvent(new Event('resize'));
  }
  // straight after the page's column, not at the screen's far edge, a long
  // way from the text (page_helpers.js)
  _dockBeside(panel, dock);
  if (dock && typeof _scrollHint === 'function') _scrollHint(document.getElementById('post-settings') || panel);
}
document.addEventListener('DOMContentLoaded', placePostSettings);
window.addEventListener('resize', placePostSettings);
new MutationObserver(placePostSettings).observe(document.documentElement, { attributes: true,
                                                                            attributeFilter: ['data-focus-mode'] });
// Esc closes a slide-over; a card beside the editor stays
document.addEventListener('keydown', function (e) {
  // what's on top first: closing Compare's dialog closed the panel under it too
  if (e.key === 'Escape' && !postSettingsDocked() && !document.querySelector('dialog[open], :popover-open'))
    togglePostSettings(false);
});

// a time to publish means it's meant to be published - without this, a
// post given a date but left unpublished just stayed a draft
function scheduleChanged(input) {
  var published = input.form.querySelector('input[name="published"]');
  if (input.value && published && !published.checked) {
    published.checked = true;
    published.dispatchEvent(new Event('change', { bubbles: true }));
  }
}

function updateParentField(location) {
  var field = document.getElementById('parent-page-field');
  if (!field) return;
  // the header's menu and the footer each have their own pages to go under
  field.classList.toggle('hidden', location !== 'header' && location !== 'footer');
  ['header', 'footer'].forEach(function (where) {
    var select = document.getElementById('parent-slug-' + where);
    if (!select) return;
    select.disabled = location !== where;
    select.classList.toggle('hidden', location !== where);
  });
}

function addTag(tag) {
  var input = document.getElementById('tags-input');
  var parts = input.value.split(',').map(function (s) { return s.trim(); }).filter(Boolean);
  if (parts.indexOf(tag) === -1) { parts.push(tag); }
  input.value = parts.join(', ');
  input.focus();
}
