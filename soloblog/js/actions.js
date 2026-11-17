// Every event handler on the site, delegated from the document instead
// of inline onclick= attributes - the Content-Security-Policy (csp.py)
// forbids inline script, handlers included. Server side, actions.py
// writes these attributes:
//   data-onclick / data-onchange / data-oninput / data-onload / data-onscroll="fn"
//     calls window.fn(...data-args), where "$el" is the element and
//     "$value" its value
//   data-confirm="question"   ask first, then submit the button's form
//   data-autosubmit           submit the form when the field changes
//   data-live-go / data-go="url prefix"   go to prefix + the new value
//                             (in place / full page load)
//   data-open-dialog / data-close-dialog="id"
//   data-close-details        close the <details> the button is in
//   data-copy="text" [data-copied="label"]
//   data-prevent-default
//   data-shown-for="name=value"   shown only while the form's field
//                             `name` (a radio group or select) is value;
//                             a switch (checkbox) is its value while on,
//                             empty while off - "name=1";
//                             "name!=value" while it's anything else;
//                             "name=a|b" while it's either;
//                             "a=x;b=y" while either rule holds
//   data-declare-fields       (a form) also sends declared_fields, the
//                             names of its fields - settings.set_declared
// the site's language for the few words scripts write themselves
// (i18n.py puts them on <html data-i18n="{...}">)
function _t(text) {
  if (!window._i18n) {
    try { window._i18n = JSON.parse(document.documentElement.getAttribute('data-i18n') || '{}'); }
    catch (e) { window._i18n = {}; }
  }
  return window._i18n[text] || text;
}
function _actionArgs(el) {
  var raw = el.getAttribute('data-args');
  return (raw ? JSON.parse(raw) : []).map(function (a) {
    return a === '$el' ? el : a === '$value' ? el.value : a;
  });
}
function _runAction(el, attr) {
  var fn = window[el.getAttribute(attr)];
  if (typeof fn === 'function') fn.apply(el, _actionArgs(el));
}
// A search box takes the cursor by itself only where there's a keyboard to
// hand. On a touch screen the list shows first - the keyboard would cover
// it - and a tap on the box brings the keyboard.
function _keyboardToHand() { return matchMedia('(hover: hover)').matches; }
// A slide-over (Post settings, Help, Media's details) opened: the keyboard
// goes into it, at its close button, and back to what opened it when it
// closes (before it goes inert, which drops the focus)
var _panelFrom = new WeakMap();
function panelOpened(panel) {
  _panelFrom.set(panel, document.activeElement);
  var close = panel.querySelector('[aria-label^="Close"]:not([hidden])');
  if (close && _keyboardToHand()) close.focus({ preventScroll: true });
}
function panelClosed(panel) {
  var from = _panelFrom.get(panel);
  if (panel.hasAttribute('inert') || !panel.contains(document.activeElement)) return;
  if (from && from.isConnected && from !== document.body) from.focus({ preventScroll: true });
}
// a dialog, opened: on a touch screen the dialog itself has the focus, not
// the search box in it - moved before anything's drawn, so no keyboard comes up
function showDialog(d) {
  d.showModal();
  if (_keyboardToHand()) return;
  d.tabIndex = -1;
  d.focus({ preventScroll: true });
}
document.addEventListener('click', function (e) {
  var t = e.target;
  if (!t.closest) return;
  var el;
  if ((el = t.closest('[data-prevent-default]'))) e.preventDefault();
  if ((el = t.closest('[data-onclick]'))) _runAction(el, 'data-onclick');
  if ((el = t.closest('[data-confirm]'))) {
    e.preventDefault();
    // its own copy: el is reused below, so by the time Yes is clicked it
    // points at something else, or nothing
    // its form - the one it names with form= (a row inside another form), or the one it's in
    var asker = el, form = el.form || el.closest('form');
    confirmAction(asker.getAttribute('data-confirm'), function () { if (form) form.requestSubmit(asker.type === 'submit' ? asker : undefined); },
                  asker.getAttribute('aria-label') || asker.textContent.trim());
  }
  if ((el = t.closest('[data-open-dialog]'))) {
    var d = document.getElementById(el.getAttribute('data-open-dialog'));
    // opened from a drawer (the admin menu on a phone): the drawer goes -
    // closing the dialog left it open, and it looked as if nothing closed
    var drawer = el.closest('.drawer-side');
    var toggle = drawer && drawer.parentElement.querySelector(':scope > .drawer-toggle');
    if (d && toggle) toggle.checked = false;
    if (d) showDialog(d);
  }
  if ((el = t.closest('[data-close-dialog]'))) {
    var c = document.getElementById(el.getAttribute('data-close-dialog'));
    if (c) c.close();
  }
  if ((el = t.closest('[data-close-details]'))) {
    var det = el.closest('details');
    if (det) det.removeAttribute('open');
  }
  if ((el = t.closest('[data-copy]'))) {
    navigator.clipboard.writeText(el.getAttribute('data-copy'));
    if (el.hasAttribute('data-copied')) {
      // "Copied" for a moment, in a button that keeps its width - a
      // shorter label moved it, and whatever sat beside it
      if (el._label === undefined) el._label = el.innerHTML;
      el.style.minWidth = el.offsetWidth + 'px';
      el.textContent = el.getAttribute('data-copied');
      clearTimeout(el._copiedTimer);
      el._copiedTimer = setTimeout(function () { el.innerHTML = el._label; el.style.minWidth = ''; }, 2000);
    }
  }
});
document.addEventListener('change', function (e) {
  var el = e.target;
  if (!el.matches) return;
  if (el.matches('[data-onchange]')) _runAction(el, 'data-onchange');
  if (el.matches('[data-autosubmit]') && el.form) el.form.requestSubmit();
  if (el.matches('[data-live-go]')) liveGo(el.getAttribute('data-live-go') + encodeURIComponent(el.value));
  if (el.matches('[data-go]')) location.href = el.getAttribute('data-go') + encodeURIComponent(el.value);
  if (el.form) _syncShownFor(el.form);
});
function _syncShownFor(form) {
  form.querySelectorAll('[data-shown-for]').forEach(function (el) {
    var known = false, shown = el.getAttribute('data-shown-for').split(';').some(function (rule) {
      var negate = rule.indexOf('!=') > -1, parts = rule.split(negate ? '!=' : '=');
      var field = form.elements[parts[0]];
      if (!field) return false;
      known = true;
      var value = field.type === 'checkbox' && !field.checked ? '' : field.value;
      var match = parts[1].split('|').indexOf(value) > -1;
      return negate ? !match : match;
    });
    if (known) el.hidden = !shown;
  });
}
document.addEventListener('input', function (e) {
  if (e.target.matches && e.target.matches('[data-oninput]')) _runAction(e.target, 'data-oninput');
});
// load and scroll don't bubble, but a capturing listener still sees
// them - how a CDN script (Mermaid, KaTeX) runs its setup once it has
// loaded, and how a slider keeps its counter in step
document.addEventListener('load', function (e) {
  var t = e.target;
  if (t && t.getAttribute && t.getAttribute('data-onload')) _runAction(t, 'data-onload');
}, true);
document.addEventListener('scroll', function (e) {
  var t = e.target;
  if (t && t.getAttribute && t.getAttribute('data-onscroll')) _runAction(t, 'data-onscroll');
}, true);
// a disabled field isn't sent, so it isn't declared either - it's left
// as it was rather than read as empty
// a button inside that sends its form along (hx-include="closest form",
// as Send a test email does) declares it the same way
document.addEventListener('htmx:configRequest', function (e) {
  var form = e.detail.elt;
  if (form.getAttribute && form.getAttribute('hx-include') === 'closest form') form = form.closest('form');
  if (!form || !form.matches || !form.matches('form[data-declare-fields]')) return;
  var names = [];
  [].forEach.call(form.elements, function (f) {
    if (f.name && !f.disabled && names.indexOf(f.name) < 0) names.push(f.name);
  });
  e.detail.parameters.declared_fields = names.join(',');
});
// ListHeader (ui): ticking rows swaps the list's summary for
// "3 selected" and what can be done to them; none ticked, it's back.
// Only what fits the ticked rows shows (data-bulk-for: their data-state),
// a button that needs a field stays greyed out without it
// (data-bulk-needs), and with the whole page ticked and more beyond it,
// "Select all N" takes every page the filters match (all_matching).
function syncBulk(form, typing) {
  var boxes = [].slice.call(document.querySelectorAll('input[type=checkbox][form="' + form.id + '"]'));
  var ticked = boxes.filter(function (b) { return b.checked; });
  var n = ticked.length, total = parseInt(form.getAttribute('data-bulk-total') || '0', 10);
  // one ticked, and every row's box shows (RowCheck)
  boxes.forEach(function (b) { b.toggleAttribute('data-ticking', n > 0); });
  var allField = form.querySelector('[data-bulk-all-field]');
  // a row unticked: it's this page's ticks again, not every page
  if (allField && n < boxes.length) allField.value = '';
  var every = !!(allField && allField.value === '1');
  var all = form.querySelector('[data-select-all]');
  if (all) { all.checked = n > 0 && n === boxes.length; all.indeterminate = n > 0 && n < boxes.length; }
  var idle = form.querySelector('[data-bulk-idle]'), busy = form.querySelector('[data-bulk-busy]');
  if (idle) idle.hidden = n > 0;
  if (busy) busy.hidden = n === 0;
  var count = form.querySelector('[data-bulk-count]');
  if (count) count.textContent = every ? 'All ' + total + ' selected' : n + ' selected';
  var more = form.querySelector('[data-bulk-all]');
  if (more) {
    more.hidden = !(n > 0 && n === boxes.length && total > boxes.length);
    more.textContent = every ? 'Just this page' : 'Select all ' + total;
  }
  var states = ticked.map(function (b) { return b.getAttribute('data-state'); });
  form.querySelectorAll('[data-bulk-for]').forEach(function (btn) {
    // every page: rows not on this one count too - the server skips what doesn't fit
    var fits = btn.getAttribute('data-bulk-for').split(',');
    btn.hidden = !every && !states.some(function (st) { return fits.indexOf(st) !== -1; });
  });
  form.querySelectorAll('[data-confirm-all]').forEach(function (btn) {
    if (btn._confirmOne === undefined) btn._confirmOne = btn.getAttribute('data-confirm');
    btn.setAttribute('data-confirm', every ? btn.getAttribute('data-confirm-all').replace('{n}', total)
                                           : btn._confirmOne);
  });
  // typing changes no widths, and moving the field would take its cursor
  if (!typing) fitBulk(form);
}
// The bulk bar keeps to one line, so a tick never pushes the list down:
// the actions that don't fit go under More, from the last one, as a row
// of tabs does (fitTabs, chrome_offsets.js). Each item presses the real
// button, so asking first and Undo work as they are. Its own class, not
// hidden= - syncBulk hides Publish that way for rows it doesn't fit. A
// field and its button (Tag, Add tag) go last, together, and as they are:
// the menu is in the form, so they still send with it.
function fitBulk(form) {
  var busy = form.querySelector('[data-bulk-busy]'), more = form.querySelector('[data-bulk-more]');
  var menu = more && document.getElementById(more.getAttribute('popovertarget'));
  if (!busy || !menu) return;
  var row = busy.querySelector('[data-scroll-x]');
  if (!row._kids) row._kids = [].slice.call(row.children);
  var actions = row._kids.filter(function (k) { return k.matches('button[name=action]:not([data-needs])'); });
  var fields = row._kids.filter(function (k) { return actions.indexOf(k) === -1; });
  // back from the menu, ahead of the actions - only if they went
  if (fields.length && fields[0].parentNode !== row) row.prepend.apply(row, fields);
  actions.forEach(function (b) { b.classList.remove('hidden'); });
  more.hidden = true;
  menu.replaceChildren();
  var over = function () { return row.scrollWidth > row.clientWidth + 1; };
  if (busy.hidden || !over()) return;
  more.hidden = false;
  var moved = [];
  for (var i = actions.length - 1; i >= 0 && over(); i--) {
    if (actions[i].hidden) continue;
    actions[i].classList.add('hidden');
    moved.unshift(actions[i]);
  }
  if (over() && fields.length) {
    var li = document.createElement('li'), box = document.createElement('div');
    box.className = 'flex flex-row flex-wrap items-center gap-2 p-1 hover:bg-transparent';
    box.append.apply(box, fields);
    li.appendChild(box);
    menu.appendChild(li);
    // with the field gone there may be room again
    while (moved.length) {
      moved[0].classList.remove('hidden');
      if (over()) { moved[0].classList.add('hidden'); break; }
      moved.shift();
    }
  }
  if (!moved.length && !menu.children.length) { more.hidden = true; return; }
  moved.forEach(function (real) {
    var li = document.createElement('li'), item = document.createElement('button');
    item.type = 'button';
    item.innerHTML = real.innerHTML;
    if (real.classList.contains('text-error')) item.classList.add('text-error');
    item.addEventListener('click', function () { menu.hidePopover(); real.click(); });
    li.appendChild(item);
    menu.appendChild(li);
  });
}
window.addEventListener('resize', function () { document.querySelectorAll('form[data-bulk]').forEach(fitBulk); });
// On a touch screen a row's box is out of sight until something's
// ticked: pressing and holding a row (ui.TICK_ROW) ticks it, as in Gmail
// and Google Photos - without the tap the finger's lifting makes, and
// without the browser's own menu for the link under it
var _hold = null, _held = false, _liftedAt = 0;
document.addEventListener('touchstart', function (e) {
  _held = false;
  var row = e.touches.length === 1 && e.target.closest && e.target.closest('[data-tick-row]');
  var box = row && row.querySelector('input[type=checkbox][form]');
  if (!box || e.target.closest('input, textarea, select, button, [popover]')) return;
  var t = e.touches[0];
  _hold = {x: t.clientX, y: t.clientY, timer: setTimeout(function () {
    _hold = null;
    if (navigator.vibrate) navigator.vibrate(10);
    box.click();
    _held = true;
  }, 500)};
}, {passive: true});
function _letGo() { if (_hold) { clearTimeout(_hold.timer); _hold = null; } }
document.addEventListener('touchmove', function (e) {
  var t = e.touches[0];
  if (_hold && Math.abs(t.clientX - _hold.x) + Math.abs(t.clientY - _hold.y) > 10) _letGo();
}, {passive: true});
document.addEventListener('touchend', function (e) {
  _letGo();
  if (!_held) return;
  _held = false;
  _liftedAt = Date.now();
  e.preventDefault();
}, {passive: false});
document.addEventListener('touchcancel', _letGo);
// the browser's own menu while the finger's down, and a click some send
// on lifting it anyway
document.addEventListener('contextmenu', function (e) {
  if ((_hold || _held) && e.target.closest && e.target.closest('[data-tick-row]')) e.preventDefault();
}, true);
document.addEventListener('click', function (e) {
  if (Date.now() - _liftedAt > 350 || !(e.target.closest && e.target.closest('[data-tick-row]'))) return;
  _liftedAt = 0;
  e.preventDefault();
  e.stopPropagation();
}, true);
// a button that needs a field (data-needs="name") is greyed out while it's
// empty - Add tag without a tag, Save a template without a name
function syncNeeds(form) {
  form.querySelectorAll('[data-needs]').forEach(function (btn) {
    var field = form.elements[btn.getAttribute('data-needs')];
    btn.disabled = !(field && field.value.trim());
  });
}
// a field that takes another's text (data-follows="title") until it's
// typed in itself - the template's name follows the post's title
document.addEventListener('input', function (e) {
  var t = e.target, form = t.form;
  if (!form) return;
  if (t.hasAttribute && t.hasAttribute('data-follows')) t._own = true;
  if (t.name) form.querySelectorAll('[data-follows="' + t.name + '"]').forEach(function (f) {
    if (!f._own) f.value = t.value;
  });
  syncNeeds(form);
});
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('form').forEach(function (f) { if (f.querySelector('[data-needs]')) syncNeeds(f); });
});
// a group that only means something while a box is ticked
// (data-off-unless="name=value": Post settings' own side panel places,
// while Show has Side panels) - greyed out and out of reach otherwise,
// with its note saying why; still sent, so nothing chosen is lost
function syncOffUnless(group) {
  var rule = group.getAttribute('data-off-unless').split('='), form = group.closest('form');
  var box = form && form.querySelector('input[type=checkbox][name="' + rule[0] + '"][value="' + rule[1] + '"]');
  var on = !box || box.checked;
  [].forEach.call(group.children, function (child) {
    if (child.hasAttribute('data-off-note')) { child.hidden = on; return; }
    child.inert = !on;
    child.classList.toggle('opacity-50', !on);
  });
}
document.addEventListener('change', function (e) {
  if (e.target.type === 'checkbox' && e.target.form)
    e.target.form.querySelectorAll('[data-off-unless]').forEach(syncOffUnless);
});
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('[data-off-unless]').forEach(syncOffUnless);
});
// a browser that brings back ticks on Back: the bar matches them
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('form[data-bulk]').forEach(syncBulk);
});
function selectAllRows(box) {
  document.querySelectorAll('input[type=checkbox][form="' + box.form.id + '"]').forEach(function (c) {
    c.checked = box.checked;
  });
  if (box.form.hasAttribute('data-bulk')) syncBulk(box.form);
}
document.addEventListener('change', function (e) {
  var t = e.target;
  if (t.type === 'checkbox' && t.form && t.form.hasAttribute('data-bulk') && !t.hasAttribute('data-select-all')) {
    syncBulk(t.form);
  }
});
// typing in the bar's own field (Add tag's) - not a tick: a checkbox
// sends input before change, and syncing then would undo Select all
document.addEventListener('input', function (e) {
  var form = e.target.form;
  if (e.target.type !== 'checkbox' && form && form.hasAttribute && form.hasAttribute('data-bulk')) syncBulk(form, true);
});
document.addEventListener('click', function (e) {
  var more = e.target.closest && e.target.closest('[data-bulk-all]');
  if (more) {
    var field = more.form.querySelector('[data-bulk-all-field]');
    field.value = field.value === '1' ? '' : '1';
    syncBulk(more.form);
    return;
  }
  var cancel = e.target.closest && e.target.closest('[data-bulk-cancel]');
  if (!cancel) return;
  var form = cancel.form;
  document.querySelectorAll('input[type=checkbox][form="' + form.id + '"]').forEach(function (c) { c.checked = false; });
  syncBulk(form);
});
function scrollToTop() { window.scrollTo({top: 0, behavior: 'smooth'}); }
function printPage() { window.print(); }
// Mermaid's own setup once its CDN script loads. run: draw the post's
// diagrams now (a post page); the editor preview draws its own later.
function initMermaid(run) {
  if (run) drawMermaid(document.querySelectorAll('pre.mermaid'));
  // a palette change redraws the diagrams in the new one
  new MutationObserver(function () { drawMermaid(document.querySelectorAll('pre.mermaid')); })
    .observe(document.documentElement, {attributes: true, attributeFilter: ['data-theme']});
}
// Draws diagrams for the page's palette. Mermaid swaps a diagram's text
// for SVG, so the text is kept in data-src to draw again from.
function drawMermaid(nodes) {
  var root = document.documentElement;
  // printing flips the page light for a moment - its diagrams stay as they were
  if (root.hasAttribute('data-print-from')) return;
  var dark = getComputedStyle(root).colorScheme === 'dark';
  mermaid.initialize({startOnLoad: false, theme: dark ? 'dark' : 'neutral'});
  var todo = [];
  nodes.forEach(function (p) {
    if (p.dataset.src === undefined) p.dataset.src = p.textContent;
    else if (p.hasAttribute('data-processed')) {
      if (p.hasAttribute('data-drawn-dark') === dark) return;
      p.textContent = p.dataset.src;
      p.removeAttribute('data-processed');
    }
    todo.push(p);
  });
  // drawn for a dark page: printing flips them light (input.css, @media print)
  todo.forEach(function (p) { p.toggleAttribute('data-drawn-dark', dark); });
  if (todo.length) mermaid.run({nodes: todo});
}
// Printing from a dark theme: paper is white, so the page prints in a
// light one, then goes back
window.addEventListener('beforeprint', function () {
  var root = document.documentElement;
  if (getComputedStyle(root).colorScheme !== 'dark') return;
  root.setAttribute('data-print-from', root.getAttribute('data-theme') || '');
  root.setAttribute('data-theme', 'light');
});
window.addEventListener('afterprint', function () {
  var root = document.documentElement;
  if (!root.hasAttribute('data-print-from')) return;
  root.setAttribute('data-theme', root.getAttribute('data-print-from'));
  root.removeAttribute('data-print-from');
});
function renderPostMath() {
  renderMathInElement(document.querySelector('.prose'), {delimiters: [
    {left: '\\[', right: '\\]', display: true},
    {left: '\\(', right: '\\)', display: false}], throwOnError: false});
}
