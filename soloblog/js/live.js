// Live admin lists (Layout(live=True), ui: Posts, Comments, Media,
// Messages). Their plain POST forms - approve, trash, restore, bulk
// actions, upload - and their tabs, filters and pagination fetch the
// next page and swap #page-content in place, instead of a full reload
// that starts back at the top. The server side doesn't change at all:
// the same POST-redirect-GET, the same ?toast= message, which shows in
// the page header's status slot here too. Without JavaScript, every one
// of these is still an ordinary form or link.
function _liveRoot() { return document.querySelector('#page-content[data-live]'); }
function _liveSwap(html) {
  // the search box being typed in keeps its focus and caret
  var box = document.activeElement;
  var keep = box && box.matches && box.matches('[data-live-search]') ?
    {el: box, start: box.selectionStart, end: box.selectionEnd} : null;
  htmx.swap('#page-content', html, {swapStyle: 'outerHTML', swapDelay: 0, settleDelay: 20},
            {select: '#page-content', selectOOB: '#admin-nav:innerHTML,#admin-nav-margin:innerHTML'});
  if (keep && keep.el.isConnected && document.activeElement !== keep.el) {
    keep.el.focus({preventScroll: true});
    try { keep.el.setSelectionRange(keep.start, keep.end); } catch (err) {}
  }
}
function _liveStatusFrom(url) {
  // the redirect's ?toast=&toast_type=&undo= - shown, then dropped from
  // the address bar so a reload doesn't show it again
  var params = url.searchParams, msg = params.get('toast');
  var type = params.get('toast_type') || 'success', undo = params.get('undo') || '';
  // the slot beside the action, which a fetched address no longer carries as its #
  window._statusAt = params.get('toast_at') || '';
  ['toast', 'toast_type', 'toast_at', 'undo', 'undo_sig'].forEach(function (k) { params.delete(k); });
  var qs = params.toString();
  history.replaceState(history.state, '', url.pathname + (qs ? '?' + qs : '') + (url.hash || location.hash));
  if (msg) showStatus(msg, type, undo);
}
function _liveFetch(url, init) {
  init = init || {};
  init.credentials = 'same-origin';
  // HX-Request: FastHTML answers with the page's body only, no <head>
  init.headers = {'HX-Request': 'true'};
  return fetch(url, init).then(function (r) {
    return r.text().then(function (html) { return {r: r, html: html}; });
  });
}
// GET: a tab, filter, page number or search on the same list. stale():
// true once a newer search has gone out, so an answer that comes back
// late doesn't put an older list back
function liveGo(url, push, stale) {
  if (!_liveRoot()) { location.href = url; return Promise.resolve(); }
  var target = new URL(url, location.href);
  return _liveFetch(target.href).then(function (res) {
    if (stale && stale()) return;
    // a search keeps its own box (hx-preserve marks it in what comes back)
    if (stale) res.html = res.html.replace('id="live-search"', 'id="live-search" hx-preserve="true"');
    var landed = new URL(res.r.url);
    if (!res.r.ok || landed.pathname !== location.pathname || res.html.indexOf('id="page-content"') === -1) {
      location.href = target.href;
      return;
    }
    _liveSwap(res.html);
    if (push !== false) history.pushState({live: 1}, '', landed.pathname + landed.search);
    // for what follows the address: the tab you're on (tab_memory.js)
    document.dispatchEvent(new Event('live:swapped'));
  }).catch(function () { location.href = target.href; });
}
document.addEventListener('click', function (e) {
  var a = e.target.closest && e.target.closest('a[href]');
  var root = _liveRoot();
  if (!a || !root || !root.contains(a) || e.defaultPrevented) return;
  if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
  if (a.target || a.hasAttribute('download') || a.closest('[data-no-live]')) return;
  var url = new URL(a.href, location.href);
  // only the same list with a different query - anything else is a
  // real page change, and a link that only changes #hash stays native
  if (url.origin !== location.origin || url.pathname !== location.pathname) return;
  if (url.search === location.search) return;
  e.preventDefault();
  liveGo(url.href);
  // pagination: the next page starts at the top of the list
  if (a.closest('.join')) window.scrollTo(0, 0);
});
window.addEventListener('popstate', function (e) {
  if (e.state && e.state.live && _liveRoot()) liveGo(location.href, false);
});
// the header's menu, when its links don't fit on one line (ui.Nav): the
// last ones go under More, one at a time, until the row fits; if even one
// link and More don't fit, the whole menu folds into the menu button, as
// on a phone - whatever the font, zoom or number of pages. It doesn't fit
// when its row runs over, or squeezes the site's title short. Only the
// row and the title are measured - an icon's hidden tooltip hangs past its
// own box and isn't a lack of room. Done in one go, so nothing flickers.
function fitNav() {
  document.querySelectorAll('[data-site-header]').forEach(function (header) {
    var menu = header.querySelector('[data-nav-menu]');
    if (!menu) return;
    header.removeAttribute('data-nav-folded');
    var more = menu.querySelector('[data-nav-more]');
    var list = more && more.querySelector('[data-nav-more-list]');
    // everything back on the row first
    if (list) {
      while (list.firstElementChild) menu.insertBefore(list.firstElementChild, more);
      more.hidden = true;
    }
    if (!menu.offsetParent) return;  // a phone's width: already folded
    var row = menu.closest('.navbar') || menu.parentElement;
    var title = header.querySelector('[data-site-title]');
    function over() {
      return row.scrollWidth > row.clientWidth + 1 || (title && title.offsetParent && title.scrollWidth > title.clientWidth + 1);
    }
    if (!over()) return;
    if (list) {
      more.hidden = false;
      var links = [].filter.call(menu.children, function (li) { return li !== more; });
      // Home stays on the row
      while (over() && links.length > 1) list.insertBefore(links.pop(), list.firstElementChild);
      if (!over()) return;
      while (list.firstElementChild) menu.insertBefore(list.firstElementChild, more);
      more.hidden = true;
    }
    header.setAttribute('data-nav-folded', '');
  });
}
window.addEventListener('resize', fitNav);
document.addEventListener('DOMContentLoaded', fitNav);
if (document.fonts) document.fonts.ready.then(fitNav);
// a field typed twice - an email address, a new password - names the one
// it repeats (data-must-match): until they match, the form won't send and
// says why beside its buttons (data-mismatch), as a wrong field does
function _checkMatch(field) {
  var other = field.form && field.form.elements[field.getAttribute('data-must-match')];
  if (!other) return;
  var a = other.value.trim(), b = field.value.trim();
  if (field.type === 'email') { a = a.toLowerCase(); b = b.toLowerCase(); }
  field.setCustomValidity(a === b ? '' : (field.getAttribute('data-mismatch') || "They don't match"));
}
// a field only needed to change a saved value - the password, to change
// the admin email - shows while that value differs from what's saved
// (data-shown-while-changed), and empties itself when it hides again
function _showWhileChanged(form) {
  form.querySelectorAll('[data-shown-while-changed]').forEach(function (box) {
    var f = form.elements[box.getAttribute('data-shown-while-changed')];
    if (!f) return;
    var was = f.defaultValue.trim().toLowerCase();
    box.hidden = !was || f.value.trim().toLowerCase() === was;
    if (box.hidden) box.querySelectorAll('input').forEach(function (i) { i.value = i.defaultValue = ''; });
  });
}
document.addEventListener('input', function (e) {
  var f = e.target;
  if (!f.form || !f.name) return;
  if (f.matches('[data-must-match]')) _checkMatch(f);
  f.form.querySelectorAll('[data-must-match="' + f.name + '"]').forEach(_checkMatch);
  if (f.form.querySelector('[data-shown-while-changed="' + f.name + '"]')) _showWhileChanged(f.form);
});
// Discard puts the address back; a save makes the new one the saved one
document.addEventListener('reset', function (e) {
  var form = e.target;
  setTimeout(function () { _showWhileChanged(form); });
});
document.addEventListener('htmx:afterSettle', function () {
  setTimeout(function () {
    document.querySelectorAll('form').forEach(function (form) {
      if (form.querySelector('[data-shown-while-changed]')) _showWhileChanged(form);
    });
  });
});
// SearchBox (ui): its clear button empties the box as if it had
// been typed away - the live list, the search box's results and the
// pickers all listen for input - and leaves the cursor in it
document.addEventListener('click', function (e) {
  var btn = e.target.closest && e.target.closest('[data-clear-search]');
  if (!btn) return;
  e.preventDefault();
  var box = btn.parentNode.querySelector('input');
  box.value = '';
  box.dispatchEvent(new Event('input', { bubbles: true }));
  box.dispatchEvent(new Event('search', { bubbles: true }));
  box.focus();
});
// A daisyUI tooltip is centred on its button, so on one at the very edge
// of the screen it was cut off (focus mode's close and Hide browser bars).
// There it turns to the side with room, and back once there's room again.
function _fitTooltip(e) {
  var el = e.target.closest && e.target.closest('.tooltip[data-tip]');
  if (!el) return;
  if (!el.dataset.tipDir) {
    el.dataset.tipDir = ['tooltip-bottom', 'tooltip-left', 'tooltip-right'].filter(function (c) {
      return el.classList.contains(c);
    })[0] || 'tooltip-top';
  }
  var dir = el.dataset.tipDir;
  if (dir !== 'tooltip-top' && dir !== 'tooltip-bottom') return;
  var ctx = _fitTooltip.ctx || (_fitTooltip.ctx = document.createElement('canvas').getContext('2d'));
  ctx.font = '0.875rem ' + getComputedStyle(document.body).fontFamily;
  var half = (Math.min(ctx.measureText(el.dataset.tip).width, 320) + 24) / 2;
  var r = el.getBoundingClientRect(), mid = r.left + r.width / 2;
  var want = mid - half < 4 ? 'tooltip-right' : mid + half > document.documentElement.clientWidth - 4 ? 'tooltip-left' : dir;
  el.classList.remove('tooltip-top', 'tooltip-bottom', 'tooltip-left', 'tooltip-right');
  el.classList.add(want);
}
document.addEventListener('mouseover', _fitTooltip);
document.addEventListener('focusin', _fitTooltip);
// a list that scrolls inside a box (ui.SCROLLS) fades at its foot while
// there's more below - a scrollbar Firefox hides until hovered says
// nothing. A list of results (data-scroll-more: search, the link picker)
// also has a "More below" button under it, which a fade alone is easy to
// miss - not a menu, where it would sit in the way. data-scroll-more="id"
// puts it there instead: a dialog's own row, beside Close. The button keeps its
// place at the end (invisible, not gone), so the list doesn't jump; it's
// only absent when nothing scrolls.
// what's in a box that fades changes size by itself - a section folding
// up, after its animation - so it's checked again whenever it does
var _hintWatch = window.ResizeObserver && new ResizeObserver(function (parts) {
  parts.forEach(function (p) {
    var box = p.target._hintBox || p.target;
    if (box.isConnected) _scrollHint(box);
  });
});
function _watchHint(el) {
  if (!_hintWatch) return;
  if (!el._hintWatched) { el._hintWatched = true; _hintWatch.observe(el); }
  [].forEach.call(el.children, function (c) {
    if (c._hintBox) return;
    c._hintBox = el;
    _hintWatch.observe(c);
  });
}
function _scrollHint(el) {
  _watchHint(el);
  // more to scroll to - not a sliver of padding under the last thing. Only
  // in a box that scrolls: the contents beside a post scroll, but on a
  // phone they sit in the page, where what's folded away isn't "more below"
  var scrolls = /auto|scroll/.test(getComputedStyle(el).overflowY);
  var more = scrolls && el.scrollHeight - el.scrollTop - el.clientHeight > 16;
  el.toggleAttribute('data-more', more);
  var chip = el._moreChip;
  if (!chip && more && el.hasAttribute('data-scroll-more')) {
    chip = document.createElement('button');
    chip.type = 'button';
    var slot = document.getElementById(el.getAttribute('data-scroll-more'));
    chip.className = 'btn btn-ghost btn-xs w-fit flex gap-1 text-base-content/70' + (slot ? '' : ' mx-auto mt-1');
    chip.innerHTML = '<span></span><svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" ' +
      'viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-hidden="true"><path stroke-linecap="round" ' +
      'stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5"/></svg>';
    chip.firstChild.textContent = _t('More below');
    chip.addEventListener('click', function () { el.scrollBy({ top: el.clientHeight * 0.8, behavior: 'smooth' }); });
    if (slot) slot.appendChild(chip); else el.insertAdjacentElement('afterend', chip);
    el._moreChip = chip;
  }
  if (chip) {
    chip.hidden = el.scrollHeight <= el.clientHeight + 4;
    chip.classList.toggle('invisible', !more);
  }
}
// The same classes as ui.SCROLLS, for the boxes a script makes.
var SCROLLS = '[scrollbar-width:thin] data-[more]:[mask-image:linear-gradient(to_bottom,black_calc(100%-2.5rem),transparent)]';
// A row you swipe along (ui.SCROLLS_X) fades at the side there's more on.
// The same classes as ui.SCROLLS_X, for the rows a script makes.
var SCROLLS_X = '[scrollbar-width:none] ' +
  'data-[right]:[mask-image:linear-gradient(to_right,black_calc(100%-1.5rem),transparent)] ' +
  'data-[left]:[mask-image:linear-gradient(to_left,black_calc(100%-1.5rem),transparent)] ' +
  'data-[left]:data-[right]:[mask-image:linear-gradient(to_right,transparent,black_1.5rem,black_calc(100%-1.5rem),transparent)]';
// it shows, hides or changes width without a scroll (a bulk bar, a phone turned)
var _rowWatch = window.ResizeObserver && new ResizeObserver(function (rows) {
  rows.forEach(function (r) { _scrollHintX(r.target); });
});
function _scrollHintX(el) {
  el.toggleAttribute('data-left', el.scrollLeft > 4);
  el.toggleAttribute('data-right', el.scrollWidth - el.scrollLeft - el.clientWidth > 4);
  if (_rowWatch && !el._watched) { el._watched = true; _rowWatch.observe(el); }
}
function _scrollHints(root) {
  (root || document).querySelectorAll('[data-scroll-hint]').forEach(_scrollHint);
  (root || document).querySelectorAll('[data-scroll-x]').forEach(_scrollHintX);
}
document.addEventListener('scroll', function (e) {
  if (e.target.matches && e.target.matches('[data-scroll-hint]')) _scrollHint(e.target);
  if (e.target.matches && e.target.matches('[data-scroll-x]')) _scrollHintX(e.target);
}, true);
// a mouse wheel only goes up and down - over a row that goes sideways,
// it moves the row, until the row's end, then the page as usual
document.addEventListener('wheel', function (e) {
  var row = e.target.closest && e.target.closest('[data-scroll-x]');
  if (!row || row.tagName === 'INPUT' || e.ctrlKey || Math.abs(e.deltaX) >= Math.abs(e.deltaY)) return;
  var room = e.deltaY > 0 ? row.scrollWidth - row.clientWidth - row.scrollLeft : row.scrollLeft;
  if (room <= 1) return;
  e.preventDefault();
  row.scrollLeft += e.deltaY;
}, { passive: false });
document.addEventListener('toggle', function (e) { if (e.target.querySelectorAll) _scrollHints(e.target); }, true);
document.addEventListener('htmx:afterSettle', function () { _scrollHints(); });
document.addEventListener('DOMContentLoaded', function () { _scrollHints(); });
// SearchField (ui): the list narrows as you type - a moment after the
// last key. The box itself stays as it is through the swap (liveGo),
// so what's typed meanwhile isn't lost and nothing flashes, and only the
// newest search's answer is shown
var _liveSearchTimer = null, _liveSearchSeq = 0;
document.addEventListener('input', function (e) {
  var box = e.target;
  if (!box.matches || !box.matches('[data-live-search]') || !_liveRoot()) return;
  clearTimeout(_liveSearchTimer);
  _liveSearchTimer = setTimeout(function () {
    var form = box.form, url = new URL(form.action, location.href);
    url.search = new URLSearchParams(new FormData(form)).toString();
    if (url.search === location.search) return;
    var mine = ++_liveSearchSeq;
    liveGo(url.href, false, function () { return mine !== _liveSearchSeq; }).then(function () {
      if (mine === _liveSearchSeq) history.replaceState({live: 1}, '', url.pathname + url.search);
    });
  }, 300);
});
document.addEventListener('DOMContentLoaded', function () {
  if (_liveRoot()) history.replaceState({live: 1}, '', location.href);
});
// POST (and same-list GET search) forms. Registered before the scroll
// restore and busy-button listeners, which both skip a prevented submit.
document.addEventListener('submit', function (e) {
  var form = e.target, root = _liveRoot();
  if (e.defaultPrevented || !root || !root.contains(form)) return;
  if (form.matches('[hx-post],[hx-get],[hx-put],[hx-delete],[hx-patch]') || form.closest('[data-no-live]')) return;
  var method = (form.getAttribute('method') || 'get').toLowerCase();
  var submitter = e.submitter;
  // a file comes back (Export): the browser saves it, the page stays
  if (submitter && submitter.hasAttribute('data-download')) return;
  var action = new URL((submitter && submitter.getAttribute('formaction')) || form.getAttribute('action') || location.href,
                       location.href);
  if (action.origin !== location.origin || method === 'dialog') return;
  var data;
  try { data = new FormData(form, submitter || undefined); } catch (err) { data = new FormData(form); }
  if (method === 'get') {
    if (action.pathname !== location.pathname) return;
    e.preventDefault();
    action.search = new URLSearchParams(data).toString();
    liveGo(action.href);
    return;
  }
  if (method !== 'post') return;
  e.preventDefault();
  setBusy(submitter, true);
  _liveFetch(action.href, {method: 'POST', body: data}).then(function (res) {
    var landed = new URL(res.r.url);
    if (!res.r.ok) {
      setBusy(submitter, false);
      showStatus(res.r.status === 403 ? 'Your session has ended - reload the page' : 'Something went wrong - try again',
                 'error');
      return;
    }
    if (res.r.redirected && landed.pathname !== location.pathname) { location.href = res.r.url; return; }
    if (res.html.indexOf('id="page-content"') === -1) {
      location.href = res.r.redirected ? res.r.url : location.href;
      return;
    }
    _liveSwap(res.html);
    if (res.r.redirected) _liveStatusFrom(landed);
  }).catch(function () {
    setBusy(submitter, false);
    showStatus("Couldn't reach the server - try again", 'error');
  });
});
