// The insert list: every command with slash words (editor_config.COMMANDS),
// grouped, each with its icon, what it does and the markdown it writes
// (or its shortcut). Three ways in:
//   "/" at the start of a line, or after a space - typing narrows it,
//       arrows and Enter pick, Esc (or a space) closes it and leaves the
//       "/" as typed
//   ":" and two letters - emoji (render.emoji_list)
//   "[[" - the titles of your posts and pages (/admin/post-titles.json),
//       for a link by title; a space is part of what's typed
//   (all only with Settings > Editor > Slash menu on)
//   the toolbar's Insert button - the same list under it, with a search
// What you used last comes first, under "Recently used".
// The toolbar's Go to button (openSections) is the same kind of menu: the
// post's own sections, to jump to one.
function setupSlashMenu(mde, slashOn) {
  var cm = mde.codemirror, menu = null, listEl = null, search = null, start = null;
  var mode = null, active = 0, shown = [], anchor = null, lastQ = null;
  // Insert in a section: the rest and its lines under two tabs - Insert first
  var tabs = null, tab = 'rest';
  // Insert opened at one group (the Go to menu's "Insert a section…"),
  // until something's typed
  var onlyGroup = null;
  var ORDER = ['Headings', 'Blocks', 'Insert', 'Sections', 'Text', 'View', 'Help'];
  var COMMANDS = ((window.EDITOR_PREFS || {}).commands || []).filter(function (c) { return c.slash.length; });
  var HEADINGS = (window.EDITOR_PREFS || {}).headings || [];
  function groupOf(c) { return HEADINGS.indexOf(c.id) > -1 ? 'Headings' : c.group; }
  function item(c) {
    return { id: c.id, label: c.label, about: c.about, icon: c.icon,
             words: (c.label + ' ' + c.slash.join(' ') + ' ' + c.about).toLowerCase(),
             hint: c.md || (c.keys ? mde.keyText(c.keys) : ''), keys: !c.md && !!c.keys,
             run: function () { mde.runCommand(c.id); } };
  }
  // The block the cursor is in - a section (a ## with a Section: line
  // under it) or a ```gallery - and its options, first in the list: its
  // Width: and Style: lines, or the gallery's style, the one in use marked
  var OPTIONS = (window.EDITOR_PREFS || {}).options;
  function blockAt() {
    var at = cm.getCursor().line, n = cm.lineCount(), i, t;
    // a callout (!!! tip) or a fold (??? "A heading"): its first line, and
    // the indented lines under it
    for (i = at; i >= 0; i--) {
      t = cm.getLine(i);
      if (/^(!!!|\?\?\?\+?)[ \t]/.test(t)) return { kind: /^!!!/.test(t) ? 'callout' : 'fold', line: i };
      if (i !== at && t.trim() && !/^(\t| {4})/.test(t)) break;
    }
    for (i = at; i >= 0; i--) {
      t = cm.getLine(i);
      if (/^```gallery\b/.test(t)) {
        var end = i + 1;
        while (end < n && !/^```\s*$/.test(cm.getLine(end))) end++;
        if (at <= end) return { kind: 'gallery', line: i };
        break;
      }
      // another block's fence, or the heading the cursor's under
      if ((/^```/.test(t) && i !== at) || /^#{1,2}\s/.test(t)) break;
    }
    for (i = at; i >= 0; i--) {
      t = cm.getLine(i);
      if (!/^#{1,2}\s/.test(t)) continue;
      if (!/^##\s/.test(t)) return null;
      for (var k = i + 1; k < n && k < i + 4; k++) {
        var m = /^Section:[ \t]*(\S.*?)[ \t]*$/i.exec(cm.getLine(k));
        if (m) return { kind: 'section', line: k, name: m[1] };
        if (cm.getLine(k).trim()) break;
      }
      return null;
    }
    return null;
  }
  // a line as written: not the "/" and what's typed after it while the menu is open
  function lineText(i) {
    var t = cm.getLine(i);
    if (start && mode !== 'insert' && start.line === i) t = t.slice(0, start.ch) + t.slice(cm.getCursor().ch);
    return t;
  }
  // a section's own lines: Key: values under its Section: line, empty
  // lines between them allowed, up to the first line of writing
  function ownLines(from) {
    var out = [];
    for (var k = from + 1; k < cm.lineCount(); k++) {
      var t = lineText(k);
      if (!t.trim()) continue;
      if (!/^[A-Za-z][A-Za-z ]*:[ \t]*\S/.test(t) || /^#/.test(t)) break;
      out.push(k);
    }
    return out;
  }
  function lineValue(line) { return lineText(line).replace(/^[^:]*:\s*/, '').trim().toLowerCase(); }
  function keyLine(block, key) {
    var re = new RegExp('^' + key + ':', 'i'), lines = ownLines(block.line);
    for (var i = 0; i < lines.length; i++) {
      if (re.test(lineText(lines[i]))) return { line: lines[i], value: lineValue(lines[i]) };
    }
    return null;
  }
  // a line is always written - Default included, never a deleted line
  function setKey(block, key, value) {
    var found = keyLine(block, key), text = key + ': ' + value;
    if (found) cm.replaceRange(text, { line: found.line, ch: 0 }, { line: found.line, ch: cm.getLine(found.line).length });
    else cm.replaceRange('\n' + text, { line: block.line, ch: cm.getLine(block.line).length });
  }
  // the option the cursor's line is, if it's one of the section's lines
  function optionAtCursor(block) {
    var at = cm.getCursor().line;
    if (ownLines(block.line).indexOf(at) === -1) return '';
    var m = /^([A-Za-z][A-Za-z ]*?):/.exec(lineText(at));
    return m ? Object.keys(OPTIONS.options).filter(function (n) { return n.toLowerCase() === m[1].toLowerCase(); })[0] || '' : '';
  }
  function blockOptions() {
    var block = OPTIONS && blockAt();
    if (!block) return null;
    var out = [], current = function (on) { return on ? 'In use' : ''; };
    function option(label, about, icon, run, on, words) {
      out.push({ label: label, about: about, icon: icon, hint: current(on),
                 words: (label + ' ' + about + ' ' + (words || '')).toLowerCase(), run: run });
    }
    if (block.kind === 'gallery') {
      var fence = /^```gallery(?:[ \t]+([a-z]+))?(?:[ \t]+(auto))?/.exec(cm.getLine(block.line));
      var style = fence[1] || '', auto = !!fence[2];
      var write = function (st, au) {
        cm.replaceRange('```gallery' + (st ? ' ' + st : '') + (st === 'slider' && au ? ' auto' : ''),
                        { line: block.line, ch: 0 }, { line: block.line, ch: cm.getLine(block.line).length });
      };
      OPTIONS.gallery.forEach(function (o) {
        option(o[1], o[2], o[3], function () { write(o[0], auto); }, (style || OPTIONS.galleryDefault) === o[0],
               'gallery style');
      });
      if (style) option('Site default', 'The style set in Settings > Posts', OPTIONS.icons['default'],
                        function () { write('', false); }, false, 'gallery style');
      if (style === 'slider') option(auto ? 'Stop autoplay' : 'Autoplay', 'A slide every few seconds',
                                     OPTIONS.icons.auto, function () { write('slider', !auto); }, false, 'slider auto');
      return ['Gallery', out];
    }
    if (block.kind === 'callout' || block.kind === 'fold') {
      var first = cm.getLine(block.line), put = function (text) {
        cm.replaceRange(text, { line: block.line, ch: 0 }, { line: block.line, ch: first.length });
      };
      if (block.kind === 'fold') {
        var open = /^\?\?\?\+/.test(first);
        option('Starts closed', 'Readers open it', OPTIONS.icons.closed,
               function () { put(first.replace(/^\?\?\?\+?/, '???')); }, !open, 'collapsible fold open');
        option('Starts open', 'Readers can close it', OPTIONS.icons.open,
               function () { put(first.replace(/^\?\?\?\+?/, '???+')); }, open, 'collapsible fold open');
        return ['Collapsible', out];
      }
      var kind = (/^!!![ \t]+([a-z]+)/.exec(first) || [])[1] || 'note';
      OPTIONS.callout.forEach(function (o) {
        option(o[1], o[2], o[3], function () { put(first.replace(/^!!![ \t]+[a-z]*/, '!!! ' + o[0])); },
               kind === o[0], 'callout box');
      });
      return ['Callout', out];
    }
    // a section's Key: lines (sections.REGISTRY), each Default first, then
    // its values. Its own before Width: and Style:, and the one the
    // cursor's line is before the rest.
    var spec = OPTIONS.sections[OPTIONS.kinds[block.name.toLowerCase()]] || { label: block.name, options: OPTIONS.shared, about: {} };
    var names = spec.options.filter(function (n) { return OPTIONS.shared.indexOf(n) === -1; }).concat(
      spec.options.filter(function (n) { return OPTIONS.shared.indexOf(n) !== -1; }));
    var chosen = optionAtCursor(block);
    if (names.indexOf(chosen) > 0) names.unshift(names.splice(names.indexOf(chosen), 1)[0]);
    names.forEach(function (name) {
      var o = OPTIONS.options[name], found = keyLine(block, name), now = found ? found.value : '';
      var words = name + ' ' + o.about + ' ' + spec.label + ' section';
      var about = (spec.about && spec.about[name]) || o.about, write = function (v) { return function () { setKey(block, name, v); }; };
      var usual = name === 'Width' && spec.width ? o.values.filter(function (v) { return v[0] === spec.width; })[0] : null;
      option(name + ': ' + OPTIONS.defaultWord, usual ? 'Usually ' + usual[1] : o['default'], OPTIONS.icons['default'],
             write(OPTIONS.defaultWord), !now || now === OPTIONS.defaultWord.toLowerCase(), words);
      if (o.type === 'choice') {
        // a kind's own Style values come after the shared ones
        o.values.concat(name === 'Style' ? spec.styles || [] : []).forEach(function (v) {
          option(name + ': ' + v[1], v[2], v[3], write(v[1]), now === v[0] || now === v[1].toLowerCase() || o.aliases[now] === v[0], words);
        });
      } else if (o.type === 'number') {
        o.suggest.forEach(function (n) {
          option(name + ': ' + n, n + ' ' + o.unit, OPTIONS.icons.count, write(String(n)), now === String(n), words);
        });
      } else {
        // not a tag called Default: it can't be picked (reserved)
        var series = o.type === 'series';
        (series ? OPTIONS.series : OPTIONS.tags).filter(function (t) { return t.toLowerCase() !== OPTIONS.defaultWord.toLowerCase(); }).forEach(function (t) {
          option(name + ': ' + t, about, series ? OPTIONS.icons.series : OPTIONS.icons.tag, write(t), now.replace(/^#/, '') === t.toLowerCase(), words);
        });
      }
    });
    return [spec.label + ' section', out];
  }
  // for the phone's All sheet, which opens on them too (editor_init.js)
  mde.blockOptions = blockOptions;
  // A finger swiping up or down on a menu moves the menu's own list, never
  // the text behind it: a list that has more keeps the swipe (and
  // overscroll-contain stops it passing on at its end); on anything else
  // in the menu the swipe does nothing. Sideways swipes are left alone -
  // the tabs' row, the sheet's pages.
  mde.holdSwipes = function (el) {
    var from = null;
    el.addEventListener('touchstart', function (e) {
      from = e.touches.length === 1 ? { x: e.touches[0].clientX, y: e.touches[0].clientY } : null;
    }, { passive: true });
    el.addEventListener('touchmove', function (e) {
      if (!from || !e.cancelable) return;
      if (Math.abs(e.touches[0].clientX - from.x) > Math.abs(e.touches[0].clientY - from.y)) return;
      for (var n = e.target; n && n.nodeType === 1; n = n === el ? null : n.parentNode) {
        if (n.scrollHeight > n.clientHeight + 1 && /auto|scroll/.test(getComputedStyle(n).overflowY)) return;
      }
      e.preventDefault();
    }, { passive: false });
  };

  // A value the page can't use - Width: Tall, a kind of section Soloblog
  // doesn't know - underlined, with a line under it saying what it can be,
  // as a form says under a field. Checked a moment after typing stops.
  var flagged = [], checkLater = 0;
  function flag(line, from, to, words) {
    var note = document.createElement('div');
    note.className = 'text-xs text-error pb-1';
    note.textContent = words;
    flagged.push(cm.markText({ line: line, ch: from }, { line: line, ch: to }, { className: 'underline decoration-wavy decoration-error underline-offset-3' }));
    flagged.push(cm.addLineWidget(line, note));
  }
  function checkValues() {
    if (!OPTIONS) return;
    cm.operation(function () {
      flagged.forEach(function (f) { f.clear(); });
      flagged = [];
      var n = cm.lineCount(), fence = false;
      for (var i = 0; i < n; i++) {
        var t = cm.getLine(i), m;
        if (/^```/.test(t)) {
          // a gallery's style, on its first line
          m = !fence && /^```gallery[ \t]+([a-z]+)/i.exec(t);
          if (m && !OPTIONS.gallery.some(function (o) { return o[0] === m[1].toLowerCase(); })) {
            flag(i, t.indexOf(m[1], 10), t.indexOf(m[1], 10) + m[1].length, 'A gallery can be ' + OPTIONS.gallery.map(function (o) { return o[0]; }).join(', ').replace(/, ([^,]*)$/, ' or $1'));
          }
          fence = !fence;
          continue;
        }
        if (fence) continue;
        m = /^(Section:[ \t]*)(\S.*?)[ \t]*$/i.exec(t);
        if (!m) continue;
        if (!OPTIONS.kinds[m[2].toLowerCase()]) {
          flag(i, m[1].length, t.length, 'Soloblog doesn\'t know this kind of section - Insert > Sections lists them');
        }
        var kindSpec = OPTIONS.sections[OPTIONS.kinds[m[2].toLowerCase()]] || {};
        // its own lines, straight under it
        ownLines(i).forEach(function (k) {
          var kv = /^([A-Za-z][A-Za-z ]*?):[ \t]*(\S.*?)[ \t]*$/.exec(cm.getLine(k));
          var name = kv && Object.keys(OPTIONS.options).filter(function (n) { return n.toLowerCase() === kv[1].toLowerCase(); })[0];
          if (!name) return;
          var o = OPTIONS.options[name], value = kv[2].toLowerCase(), from = cm.getLine(k).indexOf(kv[2], kv[1].length + 1), bad = '';
          // a tag called Default can't be told from the word
          if (o.type === 'tag') bad = value === OPTIONS.defaultWord.toLowerCase() && OPTIONS.defaultTag ? OPTIONS.reserved : '';
          else if (o.type !== 'series' && value !== OPTIONS.defaultWord.toLowerCase()) {
            // a kind with Style values of its own has its own list and its own note
            var own = name === 'Style' && kindSpec.styleAccepts && kindSpec.styleAccepts.length;
            bad = (o.type === 'number' ? /^\d+$/.test(value) && +value >= o.limit[0] && +value <= o.limit[1]
                                       : (own ? kindSpec.styleAccepts : o.accepts).indexOf(value) !== -1) ? ''
                  : own ? kindSpec.styleNote : o.note;
          }
          if (bad) flag(k, from, from + kv[2].length, bad);
        });
      }
    });
  }
  if (OPTIONS) {
    cm.on('change', function () { clearTimeout(checkLater); checkLater = setTimeout(checkValues, 500); });
    checkValues();
  }
  var ITEMS = COMMANDS.map(item), BY_ID = {};
  ITEMS.forEach(function (it, i) { BY_ID[it.id] = it; it.group = groupOf(COMMANDS[i]); });
  // Go to a section: not a command, so nothing's inserted - the / menu
  // closes and the Go to list (openSections) opens where the cursor is.
  // Only here: Insert's list is for things to add.
  var GO_TO = (window.EDITOR_PREFS || {}).goTo;
  if (GO_TO) {
    var goTo = { id: 'goto', label: GO_TO.label, about: GO_TO.about, icon: GO_TO.icon, group: GO_TO.group,
                 words: (GO_TO.label + ' ' + GO_TO.slash.join(' ') + ' ' + GO_TO.about).toLowerCase(),
                 hint: '', keys: false, slashOnly: true,
                 run: function () { setTimeout(function () { mde.openSections(null); }); } };
    ITEMS.push(goTo);
    BY_ID[goTo.id] = goTo;
  }
  function offered(it) { return !(it.slashOnly && mode === 'insert'); }

  // the last three used, kept in this browser only
  function recent() {
    try { return JSON.parse(localStorage.getItem('editor-recent') || '[]').filter(function (id) { return BY_ID[id] && offered(BY_ID[id]); }); }
    catch (e) { return []; }
  }
  function remember(id) {
    try {
      var list = [id].concat(recent().filter(function (x) { return x !== id; })).slice(0, 3);
      localStorage.setItem('editor-recent', JSON.stringify(list));
    } catch (e) {}
  }

  // : and two letters suggests emoji - :smile: in a post shows as the
  // emoji itself
  // typing faster than the list loads mustn't close it for good
  var emoji = null, emojiLoading = false;
  function emojiItems(q) {
    if (!emoji) return [];
    var starts = [], has = [];
    emoji.forEach(function (e) {
      var i = e[0].indexOf(q);
      if (i === 0) starts.push(e); else if (i > 0) has.push(e);
    });
    return starts.concat(has).slice(0, 8).map(function (e) {
      return { label: e[1] + '  ' + e[0], run: function () { cm.replaceSelection(e[1]); } };
    });
  }

  // [[ suggests the titles of your other posts and pages, fetched the
  // first time they're wanted. Any case, any accents, the closest first.
  var titles = null, titlesLoading = false;
  function plain(t) { return t.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase(); }
  function titleItems(q) {
    if (!titles) return [];
    var needle = plain(q), hits = [];
    titles.forEach(function (t, i) {
      var at = t.plain.indexOf(needle);
      if (at < 0) return;
      // starts with it, then a word that does, then anywhere; the newest first within each
      hits.push({ t: t, rank: at === 0 ? 0 : t.plain.charAt(at - 1) === ' ' ? 1 : 2, i: i });
    });
    hits.sort(function (a, b) { return a.rank - b.rank || a.i - b.i; });
    return hits.slice(0, 8).map(function (h) {
      return { label: h.t.title, about: h.t.status, run: function () { wikiLink(h.t); } };
    });
  }
  // [[Title]] where the "[[" and what was typed after it were - the "]]"
  // already there is used, not doubled. A title the link can't hold
  // (brackets, a bar) is linked by its address.
  function wikiLink(t) {
    var cur = cm.getCursor(), end = { line: cur.line, ch: cur.ch + 2 };
    var safe = !/[\[\]|]/.test(t.title) && t.title.length <= 120;
    var text = '[[' + (safe ? t.title : t.slug) + ']]';
    cm.replaceRange(text, cur, cm.getRange(cur, end) === ']]' ? end : cur);
    cm.setCursor({ line: cur.line, ch: cur.ch + text.length });
  }

  var keys = {
    Up: function () { move(-1); }, Down: function () { move(1); },
    Enter: function () { choose(active); }, Tab: function () { choose(active); },
    Esc: function () { dismissed = start; close(); }
  }, keysOn = false, dismissed = null;
  // the arrows, Enter and Tab work the list only while it shows - until
  // : has two letters after it, they do what they always do
  function listKeys(on) {
    if (on && !keysOn) cm.addKeyMap(keys);
    if (!on && keysOn) cm.removeKeyMap(keys);
    keysOn = on;
  }
  function move(step) {
    if (!shown.length) return;
    active = (active + step + shown.length) % shown.length;
    mark();
  }
  function close() {
    var field = menu && listField();
    if (field) { field.removeAttribute('aria-activedescendant'); field.removeAttribute('aria-controls'); }
    if (menu && mode === 'sections' && anchor) anchor.setAttribute('aria-expanded', 'false');
    if (menu) menu.remove();
    listKeys(false);
    menu = null; listEl = null; search = null; start = null; mode = null; anchor = null; tabs = null; onlyGroup = null;
  }
  function typed() {
    var cur = cm.getCursor();
    if (!start || cur.line !== start.line || cur.ch <= start.ch) return null;
    return cm.getRange(start, cur);
  }

  // a heading, then its rows - daisyUI's menu-title
  function row(it, i) {
    var li = document.createElement('li');
    var a = document.createElement('a');
    // w-full: daisyUI's menu rows wrap, which sized a row to its words -
    // a long description pushed its shortcut out of the box
    a.className = 'flex items-center gap-3 w-full min-w-0';
    a.dataset.index = i;
    // an option of the list, which the text field names as its pick (mark)
    a.setAttribute('role', 'option');
    a.id = 'slash-option-' + i;
    li.setAttribute('role', 'presentation');
    if (it.icon) {
      var icon = document.createElement('span');
      icon.className = 'slash-icon';
      icon.innerHTML = it.icon;  // from editor_icons - never anything typed
      a.appendChild(icon);
    }
    var text = document.createElement('span');
    text.className = 'flex-1 min-w-0';
    var label = document.createElement('span');
    label.className = 'block truncate';
    label.textContent = it.label;
    text.appendChild(label);
    if (it.about) {
      var about = document.createElement('span');
      about.className = 'slash-about block truncate text-xs';
      about.textContent = it.about;
      text.appendChild(about);
    }
    a.appendChild(text);
    if (it.hint) {
      var hint = document.createElement('span');
      hint.className = 'slash-hint font-mono text-xs';
      if (it.keys) hint.setAttribute('data-keys', '');
      hint.textContent = it.hint;
      a.appendChild(hint);
    }
    // mousedown, not click - the editor would lose focus first
    a.addEventListener('mousedown', function (e) { e.preventDefault(); choose(i); });
    li.appendChild(a);
    return li;
  }
  function title(text) {
    var li = document.createElement('li');
    li.className = 'menu-title';
    li.setAttribute('role', 'presentation');
    li.textContent = text;
    return li;
  }
  function mark() {
    listEl.querySelectorAll('a').forEach(function (a) {
      var on = Number(a.dataset.index) === active;
      a.classList.toggle('menu-active', on);
      a.setAttribute('aria-selected', String(on));
    });
    var current = listEl.querySelector('a.menu-active');
    if (current) current.scrollIntoView({ block: 'nearest' });
    var field = listField();
    if (field && current) {
      field.setAttribute('aria-activedescendant', current.id);
      field.setAttribute('aria-controls', listEl.id);
    }
  }
  // the text field the list belongs to, for a screen reader: the editor's,
  // or the search box in Insert
  function listField() {
    if (mode === 'sections') return listEl;
    return mode === 'insert' && search ? search.querySelector('input') : cm.getInputField();
  }
  function fill(q) {
    listEl.innerHTML = '';
    shown = [];
    if (mode === 'wiki') {
      shown = titleItems(q);
      shown.forEach(function (it, i) { listEl.appendChild(row(it, i)); });
      return;
    }
    if (mode === 'emoji') {
      shown = q.length < 2 ? [] : emojiItems(q);
      shown.forEach(function (it, i) { listEl.appendChild(row(it, i)); });
      return;
    }
    var groups = [];
    // Insert at one group, until something's typed
    if (onlyGroup && !q) {
      listEl.appendChild(title(onlyGroup));
      ITEMS.filter(function (it) { return it.group === onlyGroup; }).forEach(function (it) {
        listEl.appendChild(row(it, shown.length));
        shown.push(it);
      });
      return;
    }
    var here = blockOptions();
    // a tab each until there's something typed - then everything that has it
    var only = tabs && !q ? tab : null;
    if (here && only !== 'rest') groups.push([here[0], here[1].filter(function (it) { return !q || it.words.indexOf(q) !== -1; })]);
    if (only === 'here') {
      groups.forEach(function (g) { g[1].forEach(function (it) { listEl.appendChild(row(it, shown.length)); shown.push(it); }); });
      return;
    }
    if (!q) groups.push(['Recently used', recent().map(function (id) { return BY_ID[id]; })]);
    ORDER.forEach(function (g) {
      groups.push([g, ITEMS.filter(function (it) {
        return it.group === g && offered(it) && (!q || it.words.indexOf(q) !== -1);
      })]);
    });
    groups.forEach(function (g) {
      if (!g[1].length) return;
      listEl.appendChild(title(g[0]));
      g[1].forEach(function (it) { listEl.appendChild(row(it, shown.length)); shown.push(it); });
    });
  }
  function place() {
    // from the phone bar: a sheet just above it, the width of the screen
    if (anchor && anchor.closest('.editor-phonebar')) {
      var barTop = anchor.getBoundingClientRect().top, vv = window.visualViewport;
      menu.style.left = '0.5rem';
      menu.style.width = 'calc(100vw - 1rem)';
      menu.style.top = 'auto';
      menu.style.bottom = (window.innerHeight - barTop + 4) + 'px';
      listEl.style.maxHeight = Math.max(160, barTop - (vv ? vv.offsetTop : 0) - 72) + 'px';
      return;
    }
    listEl.style.maxHeight = '';
    var width = menu.offsetWidth, height = menu.offsetHeight;
    var at = anchor ? anchor.getBoundingClientRect() : cm.cursorCoords(start, 'window');
    // inside the editor's edges (in focus mode, the screen's)
    var edge = mde.isFullscreenActive() ? { left: 8, right: window.innerWidth - 8 }
             : cm.getWrapperElement().closest('.EasyMDEContainer').getBoundingClientRect();
    var left = Math.min(at.left, edge.right - width);
    menu.style.left = Math.max(8, Math.max(edge.left, left)) + 'px';
    // as every menu does (placeMenu): below, or above where there's more
    // room - and no taller than that room, the list scrolling inside it.
    // The room is what's visible: not under a phone's keyboard.
    var vv = window.visualViewport, top = vv ? vv.offsetTop : 0, bottom = vv ? vv.offsetTop + vv.height : window.innerHeight;
    var roomBelow = bottom - at.bottom - 12, roomAbove = at.top - top - 12;
    var above = height > roomBelow && roomAbove > roomBelow, room = above ? roomAbove : roomBelow;
    if (height > room) {
      listEl.style.maxHeight = Math.max(96, room - (height - listEl.offsetHeight)) + 'px';
      height = menu.offsetHeight;
    }
    menu.style.top = (above ? at.top - 4 - height : at.bottom + 4) + 'px';
  }
  function draw() {
    var q = '';
    if (mode === 'sections') return;
    if (mode === 'insert') {
      q = search.querySelector('input').value.trim().toLowerCase();
    } else {
      q = typed();
      var trigger = mode === 'emoji' ? ':' : mode === 'wiki' ? '[[' : '/';
      if (q === null || q.indexOf(trigger) !== 0 || (mode === 'wiki' ? /[\]|]/.test(q) : /\s/.test(q)) ||
          (mode === 'emoji' && q.length > 1 && /:$/.test(q))) {
        close(); return;
      }
      q = q.slice(trigger.length);
      if (mode !== 'wiki') q = q.toLowerCase();
    }
    fill(q);
    // as the words change, the row whose name starts with them is picked -
    // /shortcuts is Keyboard shortcuts, not Help, which mentions them
    if (q !== lastQ) {
      lastQ = q;
      var best = -1;
      shown.forEach(function (it, i) {
        if (best < 0 && q && it.words && it.words.indexOf(q) === 0) best = i;
      });
      shown.forEach(function (it, i) {
        // not Go to a section: /section and Enter adds one, as it always did
        if (best < 0 && q && it.words && !it.slashOnly &&
            it.label.toLowerCase().split(' ').some(function (w) { return w.indexOf(q) === 0; })) best = i;
      });
      active = Math.max(best, 0);
    }
    if (mode !== 'insert' && !shown.length) {
      var waiting = mode === 'wiki' ? titlesLoading : mode === 'emoji' && !(q.length >= 2 && !emojiLoading);
      if (waiting) { menu.hidden = true; listKeys(false); } else close();
      return;
    }
    menu.hidden = false;
    if (mode !== 'insert') listKeys(true);
    active = Math.min(active, Math.max(shown.length - 1, 0));
    mark();
    place();
    if (window._scrollHint) _scrollHint(listEl);
  }
  function choose(i) {
    var it = shown[i];
    if (!it) return;
    if (mode === 'sections') { close(); it.run(); return; }
    var from = start, to = cm.getCursor(), wasTyped = mode !== 'insert';
    close();
    if (wasTyped) cm.replaceRange('', from, to);
    cm.focus();
    if (it.id) remember(it.id);
    cm.operation(it.run);
  }
  // a rounded box that clips, the list scrolling inside it - on the list
  // itself the scrollbar squared off the theme's corners. Frosted like
  // every other menu when Frosted glass is on.
  function build(kind) {
    close();
    mode = kind;
    active = 0;
    lastQ = null;
    menu = document.createElement('div');
    // the Go to menu is as wide as its longest row (a phone's is the screen's: place)
    menu.className = 'fixed z-50 overflow-hidden p-1 rounded-box border border-base-300 shadow-lg ' +
                     (kind === 'sections' ? 'w-max min-w-44 max-w-[min(28rem,calc(100vw-1rem))] ' : 'w-80 max-w-[calc(100vw-1rem)] ') +
                     (document.documentElement.hasAttribute('data-glass') ? 'glass-fill glass-blur' : 'bg-base-100');
    listEl = document.createElement('ul');
    listEl.setAttribute('role', 'listbox');
    listEl.id = 'slash-list';
    listEl.setAttribute('aria-label', kind === 'sections' ? 'Sections' : 'Insert');
    listEl.setAttribute('data-scroll-hint', '');
    listEl.className = 'menu menu-sm w-full max-h-80 overflow-y-auto overscroll-contain flex-nowrap [scrollbar-width:thin] ' +
                       'data-[more]:[mask-image:linear-gradient(to_bottom,black_calc(100%-2.5rem),transparent)]';
    menu.appendChild(listEl);
    mde.holdSwipes(menu);
    document.body.appendChild(menu);
  }
  function begin(ch, from) {
    var before = cm.getLine(from.line).slice(0, from.ch);
    if (ch === '[[') {
      if (!titles && !titlesLoading) {
        titlesLoading = true;
        var own = (cm.getWrapperElement().closest('form') || {}).dataset || {};
        fetch('/admin/post-titles.json?exclude=' + encodeURIComponent(own.ownSlug || ''))
          .then(function (r) { return r.json(); })
          .then(function (list) {
            titles = list.map(function (t) { return { title: t[0], slug: t[1], status: t[2], plain: plain(t[0]) }; });
            titlesLoading = false;
            if (menu && mode === 'wiki') draw();
          }, function () { titlesLoading = false; });
      }
      build('wiki');
      start = from;
      return;
    }
    if (before !== '' && !/\s$/.test(before)) return;
    if (ch === ':' && !emoji) {
      emoji = [];
      emojiLoading = true;
      fetch('/admin/emoji.json').then(function (r) { return r.json(); })
        .then(function (list) { emoji = list; emojiLoading = false; if (menu && mode === 'emoji') draw(); });
    }
    build(ch === ':' ? 'emoji' : 'slash');
    start = from;
  }
  // the toolbar's Emoji button opens the suggestions the same way
  cm.suggestFrom = function (ch, from) { if (!menu) begin(ch, from); if (menu) draw(); };
  // the Insert button: the list under it, with the search box
  // (ui.SearchBox, from the page's <template>) to narrow it
  mde.openInsert = function (button, group) {
    if (menu && mode === 'insert') { close(); return; }
    build('insert');
    onlyGroup = group || null;
    anchor = button && button.offsetParent ? button : null;
    if (!anchor) start = cm.getCursor();
    var tpl = document.getElementById('insert-search');
    search = tpl.content.firstElementChild.cloneNode(true);
    search.classList.add('mb-1');
    menu.insertBefore(search, listEl);
    var here = onlyGroup ? null : blockOptions();
    if (here) {
      tab = 'here';  // what the cursor is in comes first, Insert a tab away
      tabs = document.createElement('div');
      tabs.setAttribute('role', 'tablist');
      tabs.className = 'tabs tabs-border tabs-sm flex-nowrap mb-1';
      [['here', here[0]], ['rest', 'Insert']].forEach(function (t) {
        var b = document.createElement('button');
        b.type = 'button';
        b.setAttribute('role', 'tab');
        b.className = 'tab' + (t[0] === tab ? ' tab-active' : '');
        b.textContent = t[1];
        b.addEventListener('mousedown', function (e) {
          e.preventDefault();
          tab = t[0];
          tabs.querySelectorAll('.tab').forEach(function (x) { x.classList.toggle('tab-active', x === b); });
          active = 0;
          draw();
          listEl.scrollTop = 0;
        });
        tabs.appendChild(b);
      });
      menu.insertBefore(tabs, listEl);
    }
    var input = search.querySelector('input');
    input.addEventListener('input', function () { active = 0; draw(); });
    input.addEventListener('keydown', function (e) {
      // while a word is being composed (Chinese, Japanese, Korean), Enter,
      // the arrows and Esc belong to the input method
      if (e.isComposing || e.keyCode === 229) return;
      var k = { ArrowDown: 1, ArrowUp: -1 }[e.key];
      if (k) { e.preventDefault(); move(k); }
      else if (e.key === 'Enter') { e.preventDefault(); choose(active); }
      else if (e.key === 'Escape') { e.preventDefault(); close(); cm.focus(); }
    });
    draw();
    if (_keyboardToHand()) input.focus();
  };
  mde.insertOpen = function () { return !!menu && mode === 'insert'; };

  // The Go to button: one row per section of the post, in the order
  // written - its kind, and its heading's words beside it - the one the
  // cursor's in marked. Built each time it opens: the text has changed.
  // Choosing one takes the cursor to its heading (mde.goToLine). With
  // none, a line saying so and a way to add one.
  function sectionRow(it, i) {
    var li = document.createElement('li'), a = document.createElement('a');
    li.setAttribute('role', 'presentation');
    a.className = 'flex items-center gap-3 w-full min-w-0 whitespace-nowrap';
    a.dataset.index = i;
    a.setAttribute('role', 'option');
    a.id = 'slash-option-' + i;
    if (it.here) a.setAttribute('aria-current', 'true');
    if (it.icon) {
      var icon = document.createElement('span');
      icon.className = 'slash-icon';
      icon.innerHTML = it.icon;  // from editor_icons
      a.appendChild(icon);
    }
    var kind = document.createElement('span');
    kind.className = 'flex-none';
    kind.textContent = it.label;
    a.appendChild(kind);
    if (it.about) {
      var about = document.createElement('span');
      about.className = 'slash-about min-w-0 flex-1 truncate';
      about.textContent = it.about;
      a.appendChild(about);
    }
    if (it.here !== undefined) {
      var tick = document.createElement('span');
      tick.className = 'slash-icon ms-auto flex-none ' + (it.here ? '' : 'invisible');
      tick.innerHTML = (window.EDITOR_PREFS.icons || {}).check || '';
      tick.setAttribute('aria-hidden', 'true');
      a.appendChild(tick);
    }
    a.addEventListener('mousedown', function (e) { e.preventDefault(); choose(i); });
    li.appendChild(a);
    return li;
  }
  mde.openSections = function (button) {
    if (menu && mode === 'sections') { close(); return; }
    build('sections');
    anchor = button && button.offsetParent ? button : null;
    if (anchor) anchor.setAttribute('aria-expanded', 'true');
    else start = cm.getCursor();  // from the / menu: at the cursor
    var found = mde.sections ? mde.sections() : [], from = anchor;
    shown = [];
    if (found.length) {
      found.forEach(function (sec) {
        shown.push({ label: sec.kind, about: sec.heading, here: sec.here,
                     run: function () { mde.goToLine(sec.line); } });
      });
    } else {
      var none = document.createElement('li');
      none.className = 'px-3 py-2 text-sm slash-about';
      none.setAttribute('role', 'presentation');
      none.textContent = 'No sections yet';
      listEl.appendChild(none);
      var plus = (window.EDITOR_PREFS.commands || []).filter(function (c) { return c.id === 'insert'; })[0];
      shown.push({ label: 'Insert a section…', icon: plus ? plus.icon : '',
                   // after the press that chose it, or Insert's own outside-click closes it
                   run: function () { setTimeout(function () { mde.openInsert(from, 'Sections'); }); } });
    }
    shown.forEach(function (it, i) { listEl.appendChild(sectionRow(it, i)); });
    // the one the cursor's in is where the arrows start
    active = Math.max(0, shown.map(function (it) { return it.here; }).indexOf(true));
    mark();
    place();
    if (window._scrollHint) _scrollHint(listEl);
    // the arrows, Enter and Esc work the list - which has the focus, as a
    // menu does. On a phone it stays with the text: the keyboard stays up
    // and the list is for a finger.
    listEl.addEventListener('keydown', function (e) {
      var step = { ArrowDown: 1, ArrowUp: -1 }[e.key];
      if (step) { e.preventDefault(); move(step); }
      else if (e.key === 'Home' || e.key === 'End') { e.preventDefault(); active = e.key === 'Home' ? 0 : shown.length - 1; mark(); }
      else if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); choose(active); }
      else if (e.key === 'Escape') {
        e.preventDefault();
        e.stopPropagation();
        var back = anchor;
        close();
        if (back) back.focus(); else cm.focus();
      } else if (e.key === 'Tab') close();
    });
    if (anchor ? !anchor.closest('.editor-phonebar') : _keyboardToHand()) {
      listEl.tabIndex = -1;
      listEl.classList.add('focus:outline-hidden');
      listEl.focus({ preventScroll: true });
    }
  };
  mde.sectionsOpen = function () { return !!menu && mode === 'sections'; };
  // a click anywhere else closes it (the Insert button toggles it itself)
  document.addEventListener('mousedown', function (e) {
    if (menu && (mode === 'insert' || mode === 'sections') && !menu.contains(e.target) &&
        !(anchor && anchor.contains(e.target))) close();
  });
  // Typed on after a list closed with nothing found - letters deleted and
  // typed again - the list comes back once the words after the "/" or ":"
  // find something again. Not after Esc: that leaves it as typed.
  function reopen() {
    var cur = cm.getCursor(), before = cm.getLine(cur.line).slice(0, cur.ch);
    var w = /\[\[([^\[\]|]*)$/.exec(before);
    if (w) {
      // not inside a link that's already written: only at the end of what's typed
      if (/^[^\s\]]/.test(cm.getLine(cur.line).slice(cur.ch))) return;
      var at = { line: cur.line, ch: cur.ch - w[1].length - 2 };
      if (!(dismissed && dismissed.line === at.line && dismissed.ch === at.ch)) begin('[[', at);
      return;
    }
    var m = /(^|\s)([\/:])([^\s\/:]+)$/.exec(before);
    if (!m || m[3].length < (m[2] === ':' ? 2 : 1)) return;
    var from = { line: cur.line, ch: cur.ch - m[3].length - 1 };
    if (dismissed && dismissed.line === from.line && dismissed.ch === from.ch) return;
    begin(m[2], from);
  }
  if (slashOn) {
    cm.on('inputRead', function (_, change) {
      var ch = change.text.join('');
      if (!menu && ch === '[' && cm.getLine(change.from.line).slice(change.from.ch - 1, change.from.ch + 1) === '[[') {
        dismissed = null; begin('[[', { line: change.from.line, ch: change.from.ch - 1 });
      } else if (!menu && (ch === '/' || ch === ':')) { dismissed = null; begin(ch, change.from); }
      else if (!menu && change.origin === '+input') reopen();
      if (menu && mode !== 'insert') draw();
    });
  }
  cm.on('cursorActivity', function () { if (menu && mode !== 'insert' && mode !== 'sections') draw(); });
  cm.on('blur', function () { if (mode !== 'insert' && mode !== 'sections') close(); });
  // A menu stays with its button, or the / list with the cursor, as the
  // page scrolls - and goes once that's out of sight. Typing on a long
  // post's last line scrolls the page to keep the cursor clear of the
  // toolbar; closing on any scroll shut the / list as it opened.
  window.addEventListener('scroll', function () {
    if (!menu || !start && !anchor) return;
    var at = anchor ? anchor.getBoundingClientRect() : cm.cursorCoords(start, 'window');
    if (at.bottom < 0 || at.top > window.innerHeight) close(); else place();
  }, { passive: true });
}
