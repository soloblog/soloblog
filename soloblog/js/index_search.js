// IndexSearch (ui): the box over Settings and Help. As you type, the
// page's own content steps aside for a list of what matches - every
// section, not just the open one - with a bar that says it's a search
// and a Clear search button that brings the page back as it was. The
// index (the page's /search-index) is fetched the first time it's
// needed. A result opens its place with what you looked for marked.
function _fold(text) {
  return (text || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
}
function _escape(text) {
  return String(text).replace(/[&<>"]/g, function (c) { return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]; });
}
function _markWords(text, words) {
  var safe = _escape(text);
  var parts = words.filter(function (w) { return w.length >= 2; })
    .map(function (w) { return w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); });
  if (!parts.length) return safe;
  // the whole word it's in: a search for "page" looks for "pag" (so it
  // finds "pages" too), and marked only those three letters. All the words
  // in one pass - one at a time, a later one matched inside an earlier mark
  var re = new RegExp('([\\p{L}\\p{N}]*(?:' + parts.join('|') + ')[\\p{L}\\p{N}]*)', 'giu');
  safe = safe.replace(re, '<mark class="bg-warning/40 text-inherit rounded-sm">$1</mark>');
  // a word inside an entity or a tag it made isn't a match
  return safe.replace(/&(\w*)<mark[^>]*>(\w*)<\/mark>(\w*;)/g, '&$1$2$3');
}
function _snippet(text, words) {
  var folded = _fold(text), at = -1;
  words.forEach(function (w) { var i = folded.indexOf(w); if (i !== -1 && (at === -1 || i < at)) at = i; });
  if (at === -1) return text.length > 160 ? text.slice(0, 160) + '…' : text;
  var start = Math.max(0, at - 60), end = Math.min(text.length, at + 100);
  // whole words at both ends
  if (start) start = text.indexOf(' ', start) + 1 || start;
  if (end < text.length) end = text.lastIndexOf(' ', end) > at ? text.lastIndexOf(' ', end) : end;
  return (start ? '…' : '') + text.slice(start, end) + (end < text.length ? '…' : '');
}
// the little words of a question don't have to be in an answer, and a word
// matches its other endings: "how do I move to a new host" looks for
// "mov", "new" and "host" - so "Moving to a new server" is found
var _LITTLE = {a: 1, an: 1, the: 1, to: 1, my: 1, of: 1, for: 1, in: 1, on: 1, how: 1, do: 1, i: 1, from: 1,
               and: 1, or: 1, is: 1, can: 1, with: 1, your: 1, it: 1, me: 1};
function _searchWords(q) {
  return _fold(q).split(/\s+/).filter(function (w) { return w && !_LITTLE[w]; }).map(function (w) {
    var stem = w.replace(/(ing|ed|es|s)$/, '').replace(/e$/, '');
    return stem.length >= 3 ? stem : w;
  });
}
function _indexSearch(box) {
  _recentShow(box);
  var body = document.getElementById(box.dataset.indexBody);
  var out = document.getElementById(box.dataset.indexBody + '-results');
  var q = box.value.trim(), words = _searchWords(q);
  // only little words ("how do I"): look for them as they are
  if (q && !words.length) words = _fold(q).split(/\s+/).filter(Boolean);
  // the top bar's box leaves the address alone: ?q= is the page's own (Posts' search)
  if (!box.hasAttribute('data-index-no-url')) {
    var url = new URL(location.href);
    if (q) url.searchParams.set('q', q); else url.searchParams.delete('q');
    history.replaceState(history.state, '', url.pathname + url.search + location.hash);
  }
  var heading = document.querySelector('#page-content h1');
  if (heading && box.dataset.indexTitle) {
    if (heading.dataset.title === undefined) heading.dataset.title = heading.textContent;
    heading.textContent = words.length ? box.dataset.indexTitle : heading.dataset.title;
  }
  if (!words.length) { out.hidden = true; out.innerHTML = ''; body.hidden = false; return; }
  if (!box._index) {
    box._index = fetch(box.dataset.indexSearch, {credentials: 'same-origin'}).then(function (r) { return r.json(); })
      .then(function (list) {
        list.forEach(function (e) { e._hay = _fold([e.title, e.sub, e.text, e.words, e.group].join(' ')); e._title = _fold(e.title); });
        return list;
      });
  }
  box._index.then(function (list) {
    if (box.value.trim() !== q) return;
    var hits = list.filter(function (e) { return words.every(function (w) { return e._hay.indexOf(w) !== -1; }); });
    // a panel (no sub) that's only there for a setting of its own already listed: once is enough
    var seen = {};
    hits.forEach(function (e) { if (e.sub) seen[e.group + '|' + e.sub] = 1; });
    hits = hits.filter(function (e) {
      return e.sub || e.text || !seen[e.group + '|' + e.title] || words.every(function (w) { return e._title.indexOf(w) !== -1; });
    });
    // a heading that has every word is the answer, on top - and what's
    // under it that only matches by its name is folded into it ("Security":
    // the Security section once, not each of its parts)
    var whole = function (e) { return words.every(function (w) { return e._title.indexOf(w) !== -1; }); };
    var named = {};
    hits.forEach(function (e) { if (whole(e)) named[e.group + '|' + e.title] = 1; });
    hits = hits.filter(function (e) {
      // under a heading that matched, or on a page that did (Settings: "Email")
      var under = (e.sub && named[e.group + '|' + e.sub]) || (e.title !== e.group && named[e.group + '|' + e.group]);
      if (!under || whole(e)) return true;
      var own = _fold([e.title, e.sub && !named[e.group + '|' + e.sub] ? e.sub : '', e.text, e.words].join(' '));
      return words.every(function (w) { return own.indexOf(w) !== -1; });
    });
    hits.forEach(function (e) {
      e._score = (e._title === _fold(q) ? 20 : whole(e) ? 10 : 0) +
        words.reduce(function (n, w) { return n + (e._title.indexOf(w) !== -1 ? 3 : 0) + (_fold(e.sub).indexOf(w) !== -1 ? 1 : 0); }, 0);
    });
    var groups = [], byGroup = {};
    hits.forEach(function (e) {
      if (!byGroup[e.group]) { byGroup[e.group] = []; groups.push(e.group); }
      byGroup[e.group].push(e);
    });
    // the area with the best match first - a heading that has the words
    // beats a passage that only mentions them
    // the top bar's search (ui.AdminSearch): an admin page, then a setting,
    // before Help's page about it, when they're the same good match
    // (data-index-first: the groups' beginnings, in that order, "|" apart)
    var first = (box.dataset.indexFirst || '').split('|').filter(Boolean);
    var best = function (g) {
      var at = first.findIndex(function (f) { return g.indexOf(f) === 0; });
      return Math.max.apply(null, byGroup[g].map(function (e) { return e._score; })) +
        (at === -1 ? 0 : 2 * (first.length - at));
    };
    groups = groups.map(function (g, i) { return [g, i]; })
      .sort(function (a, b) { return best(b[0]) - best(a[0]) || a[1] - b[1]; }).map(function (p) { return p[0]; });
    var later = box.dataset.indexLast;
    if (later && byGroup[later]) groups = groups.filter(function (g) { return g !== later; }).concat([later]);
    var noun = box.dataset.indexNoun, nouns = box.dataset.indexNouns;
    var html = '<div class="flex flex-wrap items-center justify-between gap-2 rounded-box border-[length:var(--border)] ' +
      'border-base-300 bg-base-200 px-4 py-2 mb-4"><p class="text-sm" role="status">' +
      (hits.length ? hits.length + ' ' + (hits.length === 1 ? noun : nouns) + ' found for ' : 'Nothing found for ') +
      '<strong>“' + _escape(q) + '”</strong>' + (hits.length ? '' : ' - try another word') + '</p>' +
      '<button type="button" class="btn btn-sm" data-index-clear>Clear search</button></div>';
    groups.forEach(function (g) {
      var rows = byGroup[g].sort(function (a, b) { return b._score - a._score; }).slice(0, 30);
      html += '<h2 class="text-sm font-semibold mb-2 mt-4">' + _escape(g) + '</h2><ul class="list bg-base-100 rounded-box ' +
        'border-[length:var(--border)] border-base-300">';
      rows.forEach(function (e) {
        var href = e.href, hash = '';
        if (href.indexOf('#') !== -1) { hash = href.slice(href.indexOf('#')); href = href.slice(0, href.indexOf('#')); }
        href += (href.indexOf('?') === -1 ? '?' : '&') + 'find=' + encodeURIComponent(q) + hash;
        html += '<li><a href="' + _escape(href) + '" class="block px-4 py-2.5 hover:bg-base-200 rounded-box">' +
          '<span class="block text-sm font-medium">' + _markWords(e.title, words) + '</span>' +
          (e.sub ? '<span class="block text-xs text-base-content/60">' + _markWords(e.sub, words) + '</span>' : '') +
          (e.text ? '<span class="block text-xs text-base-content/70 mt-0.5">' + _markWords(_snippet(e.text, words), words) + '</span>' : '') +
          '</a></li>';
      });
      html += '</ul>';
    });
    out.innerHTML = html;
    out.hidden = false;
    body.hidden = true;
  });
}
// Recent searches: the box, focused and empty, lists the last few
// searches made in it (Enter, or a result opened), newest first. Kept in
// this browser only, one list per box (data-recent-searches names it).
// The box is the combobox, focus stays in it, and the list is its listbox.
var _RECENT_MAX = 5;
function _recentList(box) {
  try {
    var list = JSON.parse(localStorage.getItem('soloblog-recent-' + box.dataset.recentSearches));
    return Array.isArray(list) ? list.filter(function (q) { return typeof q === 'string' && q; }).slice(0, _RECENT_MAX) : [];
  } catch (err) { return []; }
}
function _recentSave(box, list) {
  try {
    if (list.length) localStorage.setItem('soloblog-recent-' + box.dataset.recentSearches, JSON.stringify(list));
    else localStorage.removeItem('soloblog-recent-' + box.dataset.recentSearches);
  } catch (err) { /* storage blocked: the list lasts until the page changes */ }
}
function _recentRemember(box) {
  var q = box.value.trim().slice(0, 100);
  if (!q || !box.dataset.recentSearches) return;
  var list = _recentList(box).filter(function (r) { return r.toLowerCase() !== q.toLowerCase(); });
  list.unshift(q);
  _recentSave(box, list.slice(0, _RECENT_MAX));
}
function _recentPanel(box) {
  var id = 'recent-' + box.dataset.recentSearches;
  var panel = document.getElementById(id);
  if (panel) return panel;
  panel = document.createElement('div');
  panel.id = id;
  panel.hidden = true;
  panel.setAttribute('data-recent-for', box.id);
  panel.className = 'absolute left-0 top-full mt-1 z-40 w-max min-w-full max-w-[calc(100vw-1rem)] max-lg:inset-x-2 max-lg:w-auto max-lg:min-w-0 max-lg:max-w-none p-1 rounded-box ' +
    'border border-base-300 shadow-lg ' + (document.documentElement.hasAttribute('data-glass') ? 'glass-fill glass-blur' : 'bg-base-100');
  box.closest('[data-admin-search-row]').appendChild(panel);
  box.setAttribute('role', 'combobox');
  box.setAttribute('aria-haspopup', 'listbox');
  box.setAttribute('aria-controls', id + '-list');
  box.setAttribute('aria-expanded', 'false');
  box.setAttribute('aria-autocomplete', 'none');
  // focus stays in the box: a press on the list doesn't take it
  panel.addEventListener('mousedown', function (e) { e.preventDefault(); });
  return panel;
}
function _recentHide(box) {
  var panel = document.getElementById('recent-' + box.dataset.recentSearches);
  if (panel) panel.hidden = true;
  box.setAttribute('aria-expanded', 'false');
  box.removeAttribute('aria-activedescendant');
}
function _recentOpen(box) {
  var panel = document.getElementById('recent-' + box.dataset.recentSearches);
  return !!panel && !panel.hidden;
}
// shown when the box is focused and empty and there's something to show
function _recentShow(box) {
  if (!box.dataset.recentSearches) return;
  var list = _recentList(box);
  if (document.activeElement !== box || box.value.trim() || !list.length) { _recentHide(box); return; }
  var panel = _recentPanel(box), id = panel.id;
  var row = 'pointer-coarse:min-h-11 cursor-pointer';
  panel.innerHTML = '<p id="' + id + '-title" class="px-3 pt-2 pb-1 text-xs font-semibold text-base-content/60">Recent searches</p>' +
    '<ul role="listbox" id="' + id + '-list" aria-labelledby="' + id + '-title" data-scroll-hint ' +
    'class="menu menu-sm w-full max-h-80 overflow-y-auto flex-nowrap p-0 ' + SCROLLS + '">' +
    list.map(function (q, i) {
      return '<li role="option" id="' + id + '-' + i + '" data-recent-query="' + _escape(q) + '"><span class="' + row + '">' + _escape(q) + '</span></li>';
    }).join('') +
    '<li role="option" id="' + id + '-clear" data-recent-clear class="border-t border-base-300 mt-1 pt-1"><span class="' + row + ' text-base-content/70">Clear recent searches</span></li></ul>';
  panel.hidden = false;
  box.setAttribute('aria-expanded', 'true');
  box.removeAttribute('aria-activedescendant');
  _scrollHint(panel.querySelector('ul'));
}
function _recentMove(box, step) {
  var items = Array.prototype.slice.call(document.getElementById('recent-' + box.dataset.recentSearches).querySelectorAll('[role=option]'));
  var at = items.findIndex(function (li) { return li.id === box.getAttribute('aria-activedescendant'); });
  at = at === -1 ? (step > 0 ? 0 : items.length - 1) : (at + step + items.length) % items.length;
  items.forEach(function (li, i) { li.classList.toggle('menu-active', i === at); li.setAttribute('aria-selected', i === at ? 'true' : 'false'); });
  box.setAttribute('aria-activedescendant', items[at].id);
  items[at].scrollIntoView({block: 'nearest'});
}
function _recentChoose(box, li) {
  if (li.hasAttribute('data-recent-clear')) {
    _recentSave(box, []);
    _recentHide(box);
    return;
  }
  box.value = li.dataset.recentQuery;
  _recentRemember(box);
  _recentHide(box);
  _indexSearch(box);
}
document.addEventListener('focusin', function (e) {
  if (e.target.matches && e.target.matches('[data-recent-searches]')) _recentShow(e.target);
});
document.addEventListener('click', function (e) {
  var box = e.target.matches && e.target.matches('[data-recent-searches]') && e.target;
  if (box && !_recentOpen(box)) _recentShow(box);
  var li = e.target.closest && e.target.closest('[data-recent-for] [role=option]');
  if (li) _recentChoose(document.getElementById(li.closest('[data-recent-for]').dataset.recentFor), li);
});
document.addEventListener('focusout', function (e) {
  if (e.target.matches && e.target.matches('[data-recent-searches]')) _recentHide(e.target);
});
// Esc closes the list first (before the phone's row, which it would close too)
document.addEventListener('keydown', function (e) {
  var box = e.target.matches && e.target.matches('[data-recent-searches]') && e.target;
  if (!box) return;
  // Safari sends the Enter that ends a composed word with isComposing
  // false, but key code 229
  if (e.key === 'Enter' && !e.isComposing && e.keyCode !== 229) {
    var active = _recentOpen(box) && document.getElementById(box.getAttribute('aria-activedescendant') || '');
    if (active) { e.preventDefault(); _recentChoose(box, active); } else _recentRemember(box);
  } else if (e.key === 'Escape' && _recentOpen(box)) {
    e.preventDefault();
    e.stopImmediatePropagation();
    _recentHide(box);
  } else if ((e.key === 'ArrowDown' || e.key === 'ArrowUp') && !box.value.trim()) {
    e.preventDefault();
    if (!_recentOpen(box)) _recentShow(box);
    if (_recentOpen(box)) _recentMove(box, e.key === 'ArrowDown' ? 1 : -1);
  }
});
// a result opened is a search made (before the click goes on to clear the box)
document.addEventListener('click', function (e) {
  var link = e.target.closest && e.target.closest('[id$="-results"] a[href]');
  var out = link && link.closest('[id$="-results"]');
  var box = out && document.querySelector('[data-index-body="' + out.id.slice(0, -'-results'.length) + '"]');
  if (box) _recentRemember(box);
}, true);

document.addEventListener('input', function (e) {
  if (e.target.matches && e.target.matches('[data-index-search]')) _indexSearch(e.target);
});
document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape' && e.target.matches && e.target.matches('[data-index-search]') && e.target.value) {
    e.target.value = '';
    _indexSearch(e.target);
  }
});
document.addEventListener('click', function (e) {
  var b = e.target.closest && e.target.closest('[data-index-clear]');
  if (!b) return;
  // the box these results are from - a page can have two (Settings' own, the top bar's)
  var out = b.closest('[id$="-results"]');
  var box = document.querySelector('[data-index-body="' + out.id.slice(0, -'-results'.length) + '"]');
  box.value = '';
  _indexSearch(box);
  if (_keyboardToHand()) box.focus();
});
document.addEventListener('DOMContentLoaded', function () {
  // a search in the address of Settings or Help (an old link, a bookmark):
  // the top bar's box comes back with it - elsewhere ?q= is the page's own
  var bar = document.getElementById('admin-search'), asked = new URLSearchParams(location.search).get('q');
  if (bar && asked && /^\/admin\/(settings|help)$/.test(location.pathname)) bar.value = asked.slice(0, 100);
  document.querySelectorAll('[data-index-search]').forEach(function (box) {
    if (box.value.trim()) _indexSearch(box);
  });
  _arrive();
});
// A result's place, from the address: opened and marked with what was
// looked for. Also what a result does on the page it's already on.
function _arrive() {
  var params = new URLSearchParams(location.search), find = params.get('find');
  // a page's next step, marked by the page itself (data-arrive): brought into view the same way
  var next = document.querySelector('[data-arrive]');
  // ?panel= alone opens it too: a link to one setting
  if (!find && !params.get('panel') && !next) return;
  var target = null;
  if (next) {
    if (next.tagName === 'DETAILS') next.open = true;
    target = next;
    params.delete('find');
  } else if (params.get('panel')) {
    var panel = document.querySelector('details[data-panel="' + CSS.escape(params.get('panel')) + '"]');
    if (panel) {
      panel.open = true;
      target = panel;
      var name = params.get('setting');
      if (name) panel.querySelectorAll('fieldset').forEach(function (f) {
        var label = f.querySelector('legend, span.font-medium');
        if (!target.matches('fieldset') && label && label.textContent.trim() === name) target = f;
      });
    }
  } else if (location.hash) {
    target = document.getElementById(decodeURIComponent(location.hash.slice(1)));
  }
  if (!target) return;
  for (var p = target.parentElement; p; p = p.parentElement) if (p.tagName === 'DETAILS') p.open = true;
  // a help section: the words looked for, marked in it
  if (!params.get('panel') && !next) {
    var words = _fold(find).split(/\s+/).filter(function (w) { return w.length > 1; });
    var scope = target.closest('details') || target.parentElement;
    var walker = document.createTreeWalker(scope, NodeFilter.SHOW_TEXT), nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(function (n) {
      if (!n.nodeValue.trim() || n.parentElement.closest('script,style,mark,svg')) return;
      var html = _markWords(n.nodeValue, words);
      if (html === _escape(n.nodeValue)) return;
      var span = document.createElement('span');
      span.innerHTML = html;
      n.replaceWith(span);
    });
  }
  // marked with a soft wash of the palette's primary colour, a little past
  // its edges, that fades away - a ring set off from it looked like a frame
  // around a heading, and left its rounded corners behind
  var WASH = ['bg-primary/15', 'shadow-[0_0_0_0.5rem_color-mix(in_oklab,var(--color-primary)_15%,transparent)]'];
  var FADE = ['rounded-field', 'transition-[background-color,box-shadow]', 'duration-1000', 'ease-out'];
  setTimeout(function () {
    target.scrollIntoView({block: 'center', behavior: 'instant'});
    target.classList.add.apply(target.classList, FADE.concat(WASH));
    setTimeout(function () {
      target.classList.remove.apply(target.classList, WASH);
      // once it's faded, nothing of it stays
      setTimeout(function () { target.classList.remove.apply(target.classList, FADE); }, 1100);
    }, 1800);
  }, 50);
}
// a result on the page that's open already (only its place or the words
// differ) loads nothing, so it's gone to from here: the results close,
// and the place opens as it does on arrival. Enter on a result is a click.
document.addEventListener('click', function (e) {
  var link = e.target.closest && e.target.closest('[id$="-results"] a[href]');
  var out = link && link.closest('[id$="-results"]');
  var box = out && document.querySelector('[data-index-body="' + out.id.slice(0, -'-results'.length) + '"]');
  if (!box || e.defaultPrevented || e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
  var to = new URL(link.href, location.href);
  if (to.origin !== location.origin || to.pathname !== location.pathname) return;
  var same = function (u) {
    var q = new URLSearchParams(u.search);
    q.delete('find'); q.delete('q');
    return q.toString();
  };
  if (same(to) !== same(location)) return;
  e.preventDefault();
  box.value = '';
  _indexSearch(box);
  var url = new URL(location.href);
  url.searchParams.set('find', new URLSearchParams(to.search).get('find'));
  history.replaceState(history.state, '', url.pathname + url.search + to.hash);
  _arrive();
});

// the admin's top bar on a phone: the magnifier opens the search as a row
// under the bar, and closes it, cleared
function toggleAdminSearch() {
  var open = !document.documentElement.hasAttribute('data-admin-search');
  document.documentElement.toggleAttribute('data-admin-search', open);
  var box = document.getElementById('admin-search');
  if (open) { box.focus(); return; }
  if (box.value) { box.value = ''; _indexSearch(box); }
}
// Esc closes it too, back to the magnifier - unless a dialog or menu
// is open over it, which Esc closes first
document.addEventListener('keydown', function (e) {
  if (e.key !== 'Escape' || !document.documentElement.hasAttribute('data-admin-search')) return;
  if (document.querySelector('dialog[open], :popover-open')) return;
  toggleAdminSearch();
  var magnifier = document.querySelector('[data-admin-bar] [aria-label="Search settings and help"]');
  if (magnifier) magnifier.focus();
});
// a tap anywhere else closes it while it's empty - with a search in it,
// the results are the page, and a tap there is reading them
document.addEventListener('click', function (e) {
  if (!document.documentElement.hasAttribute('data-admin-search')) return;
  if (!e.target.closest || e.target.closest('[data-admin-search-row], [aria-label="Search settings and help"]')) return;
  if (document.getElementById('admin-search').value.trim()) return;
  toggleAdminSearch();
});
