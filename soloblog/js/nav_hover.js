// The header's menus that open as you point at them (data-hover-menu): a
// page with sub-pages (ui.PinnedNavItem), Colours and the admin's gear. A
// mouse resting on one opens its list, and leaving both closes it - a
// moment later, so the gap between them can be crossed. Its button still
// opens it by click, tap or keyboard; clicked while hover has it open, it
// stays open.
(function () {
  var hover = window.matchMedia('(hover: hover) and (pointer: fine)');
  var timers = new WeakMap();
  function parts(e) {
    var item = e.target.closest && e.target.closest('[data-hover-menu]');
    // under More a page's sub-pages show beneath it, with no list to open
    if (!item || item.closest('[data-nav-more-list]')) return null;
    var button = item.querySelector('[popovertarget]');
    var menu = button && document.getElementById(button.getAttribute('popovertarget'));
    return menu ? {item: item, menu: menu} : null;
  }
  document.addEventListener('mouseover', function (e) {
    if (!hover.matches) return;
    var p = parts(e);
    if (!p) return;
    clearTimeout(timers.get(p.menu));
    if (!p.menu.matches(':popover-open')) { p.menu.showPopover(); p.menu.setAttribute('data-hover-open', ''); }
  });
  document.addEventListener('mouseout', function (e) {
    if (!hover.matches) return;
    var p = parts(e);
    if (!p || (e.relatedTarget && p.item.contains(e.relatedTarget))) return;
    if (!p.menu.hasAttribute('data-hover-open')) return;
    timers.set(p.menu, setTimeout(function () {
      if (p.menu.matches(':popover-open')) p.menu.hidePopover();
    }, 250));
  });
  document.addEventListener('click', function (e) {
    var button = e.target.closest && e.target.closest('[data-hover-menu] [popovertarget]');
    if (!button) return;
    var menu = document.getElementById(button.getAttribute('popovertarget'));
    if (menu && menu.hasAttribute('data-hover-open') && menu.matches(':popover-open')) {
      e.preventDefault();
      clearTimeout(timers.get(menu));
    }
    if (menu) menu.removeAttribute('data-hover-open');
  }, true);
  document.addEventListener('toggle', function (e) {
    if (e.newState === 'closed' && e.target.removeAttribute) e.target.removeAttribute('data-hover-open');
  }, true);
})();
