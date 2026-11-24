// Menus are popovers, not daisyUI's :focus-within dropdowns: nested in a
// glass header, a dropdown's blur never showed, and a popover sits above
// everything, closing on a click outside or Esc for free. A popover
// doesn't place itself, so placeMenu (below) puts each by its button.
// A Combobox (ui): type to narrow its list, click to choose
function filterCombo(input) {
  var box = input.closest('[data-combo]'), q = input.value.trim().toLowerCase();
  box.querySelectorAll('[data-combo-item]').forEach(function (li) {
    li.hidden = q && li.getAttribute('data-combo-item').indexOf(q) < 0;
  });
  box.querySelectorAll('[data-combo-group]').forEach(function (title) {
    var next = title.nextElementSibling, any = false;
    while (next && !next.hasAttribute('data-combo-group')) { if (!next.hidden) any = true; next = next.nextElementSibling; }
    title.hidden = !any;
  });
  _scrollHints(box);
  // shorter now: back beside its box
  if (box.matches(':popover-open')) placeMenu(box);
}
document.addEventListener('click', function (e) {
  var pick = e.target.closest('[data-combo] [data-value]');
  if (!pick) return;
  var box = pick.closest('[data-combo]'), name = box.getAttribute('data-combo');
  var input = document.getElementById(name);
  input.value = pick.getAttribute('data-value');
  var label = document.getElementById(name + '-label');
  if ('value' in label && label.tagName === 'INPUT') label.value = pick.getAttribute('data-label');
  else label.textContent = pick.getAttribute('data-label');
  label.style.cssText = pick.style.cssText;
  box.querySelectorAll('[data-value]').forEach(function (b) {
    b.classList.toggle('menu-active', b === pick);
    b.setAttribute('aria-selected', b === pick ? 'true' : 'false');
  });
  input.dispatchEvent(new Event('input', {bubbles: true}));
  input.dispatchEvent(new Event('change', {bubbles: true}));
  box.hidePopover();
});
// Enter chooses the first match - never the form's Save
document.addEventListener('keydown', function (e) {
  if (e.key !== 'Enter' || e.isComposing || e.keyCode === 229 || !e.target.closest) return;
  var box = e.target.closest('[data-combo]');
  if (!box || e.target.tagName !== 'INPUT') return;
  e.preventDefault();
  // the first match showing - in a list, or in the template picker
  var first = Array.prototype.find.call(box.querySelectorAll('[data-combo-item]'), function (li) {
    return !li.hidden && li.getClientRects().length;
  });
  var choice = first && first.querySelector('[data-value], a[href], [data-combo-pick]');
  if (choice) choice.click();
});
document.addEventListener('toggle', function (e) {
  var el = e.target;
  if (e.newState !== 'open' || !(el.matches && el.matches('[data-combo]'))) return;
  // the search ready to type in, and the chosen one in view
  var search = el.querySelector('input[type=search], input');
  if (search) { search.value = ''; filterCombo(search); if (_keyboardToHand()) search.focus(); }
  var chosen = el.querySelector('.menu-active');
  if (chosen) chosen.scrollIntoView({block: 'center'});
}, true);
// Choosing something in a row's ⋯ menu closes it, as any menu does - once
// the click has done its work (a form sent, Discard, a drawer opened). A
// menu inside it (Pinned's Move) stays open until its own choice.
document.addEventListener('click', function (e) {
  var item = e.target.closest && e.target.closest('[popover]:is([data-row-menu], [data-more-menu]) :is(button, a)');
  if (!item || (item.closest('.dropdown') && !item.closest('.dropdown-content'))) return;
  // a wide screen's own ⋯ (data-more-menu) and the phone's menu around it
  var menus = [item.closest('[popover][data-more-menu]'), item.closest('[popover][data-row-menu]')];
  setTimeout(function () {
    menus.forEach(function (menu) { if (menu && menu.matches(':popover-open')) menu.hidePopover(); });
  });
});
// Placed under its button - or above, where there's more room there - and
// never taller than the window has room for (it scrolls inside instead).
// It stays with its button as the page scrolls, and closes once you've
// scrolled the button out of sight, as a browser's own list does.
// The room is what you can see: on a phone, above the keyboard.
function _placedMenu(el) {
  return el.matches && (el.matches('[popover]:is([data-row-menu], [data-more-menu])') || el.matches('[popover].dropdown-content'));
}
function _seen() {
  var vv = window.visualViewport;
  return vv ? {top: vv.offsetTop, bottom: vv.offsetTop + vv.height} : {top: 0, bottom: window.innerHeight};
}
// a scroll you made - a finger, the wheel, the keys - not the page
// jumping as a phone's keyboard opens
var _scrolledAt = 0;
['touchmove', 'wheel', 'keydown'].forEach(function (type) {
  document.addEventListener(type, function (e) {
    if (type !== 'keydown' || /^(Page|Arrow(Up|Down)$|Home$|End$| $)/.test(e.key)) _scrolledAt = Date.now();
  }, {capture: true, passive: true});
});
function placeMenu(el) {
  var trigger = document.querySelector('[popovertarget="' + el.id + '"]');
  if (!trigger) return;
  // a header page's arrow opens its list under the page's name, not under itself
  var anchor = trigger.closest('[data-nav-parent]') || trigger;
  var seen = _seen(), r = anchor.getBoundingClientRect();
  if (r.bottom < seen.top || r.top > seen.bottom) {
    if (Date.now() - _scrolledAt < 800) { el.hidePopover(); return; }
    // the keyboard pushed it out of sight: bring it back, the list with it
    trigger.scrollIntoView({block: 'nearest'});
    seen = _seen();
    r = anchor.getBoundingClientRect();
  }
  el.style.maxHeight = '';
  // a field's list (it opens from a box like a select) is at least as wide
  // as the box, as a browser's own is; a button's menu is as wide as it needs
  if (trigger.classList.contains('select')) el.style.minWidth = r.width + 'px';
  // a row's menu ends under its button, at the row's end. A button's menu near the window's edge
  // (the header's, More) does too - but with room beside it, it opens the way the page reads,
  // from its button's start, as menus do everywhere else
  el.style.maxWidth = '';
  var atEnd = el.matches('[data-row-menu], [data-more-menu]') ||
    (el.classList.contains('dropdown-end') && r.left + el.offsetWidth + 8 > window.innerWidth);
  // one that ends under its button never runs off the screen's other side
  if (atEnd) el.style.maxWidth = (r.right - 8) + 'px';
  var height = el.offsetHeight, roomBelow = seen.bottom - r.bottom - 12, roomAbove = r.top - seen.top - 12;
  var above = height > roomBelow && roomAbove > roomBelow;
  var room = above ? roomAbove : roomBelow;
  // a list with a search shrinks its list (Combobox), the search staying in view
  if (height > room) { el.style.maxHeight = Math.max(120, room) + 'px'; el.style.overflowY = 'auto'; height = el.offsetHeight; }
  el.style.top = (above ? r.top - 4 - height : r.bottom + 4) + 'px';
  if (atEnd) {
    el.style.right = (window.innerWidth - r.right) + 'px';
    el.style.left = 'auto';
  } else {
    el.style.left = Math.max(8, Math.min(r.left, window.innerWidth - el.offsetWidth - 8)) + 'px';
    el.style.right = 'auto';
  }
}
document.addEventListener('toggle', function (e) {
  if (e.newState === 'open' && _placedMenu(e.target)) placeMenu(e.target);
  // a page's sub-pages opening inside it (the phone's menu, More): its
  // height again, so a list grown past the screen's foot scrolls
  var menu = e.target.matches && e.target.matches('details') && e.target.closest(':popover-open');
  if (menu && _placedMenu(menu)) placeMenu(menu);
}, true);
function _replaceMenus() {
  document.querySelectorAll(':popover-open').forEach(function (el) { if (_placedMenu(el)) placeMenu(el); });
}
// the page scrolling, or a panel the button is in (capture: scroll doesn't bubble) - not the menu's own list
document.addEventListener('scroll', function (e) {
  if (e.target.closest && e.target.closest(':popover-open')) return;
  _replaceMenus();
}, {capture: true, passive: true});
// a phone's keyboard opening or closing: placed again in what's left, and
// a field in the menu (a search, the timer's own length) back in view
var _keyboardMoved = function () {
  _replaceMenus();
  var field = document.activeElement;
  if (field && field.closest && field.closest(':popover-open') && field.matches('input, select, textarea')) {
    field.scrollIntoView({block: 'nearest'});
  }
};
window.addEventListener('resize', _keyboardMoved);
if (window.visualViewport) {
  window.visualViewport.addEventListener('resize', _keyboardMoved);
  window.visualViewport.addEventListener('scroll', _replaceMenus);
}
// any menu open anywhere: the tooltips go quiet (input.css). An attribute
// set here, not a :has() in the stylesheet, which restyled the whole page
// on every change. A swap can take an open menu away without a toggle.
function _syncPopoverOpen() {
  document.documentElement.toggleAttribute('data-popover-open', !!document.querySelector('[popover]:popover-open'));
}
document.addEventListener('toggle', function (e) {
  if (e.target.hasAttribute && e.target.hasAttribute('popover')) _syncPopoverOpen();
}, true);
document.addEventListener('htmx:afterSwap', _syncPopoverOpen);
