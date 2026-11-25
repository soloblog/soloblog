document.addEventListener('DOMContentLoaded', function () {
  var el = document.getElementById('body-editor');
  if (!el) return;
  // The toolbar's buttons and their order come from Settings > Editor
  // (EDITOR_PREFS.pinned, editor_config.prefs_script). EasyMDE's own are
  // just their name; ours need a full definition.
  // EasyMDE has no checklist button of its own - this adds (or takes
  // away) "- [ ] " at the start of each selected line: the toolbar
  // button, the slash menu and Shift+Ctrl+L
  function toggleChecklist(editor) {
    var cm = editor.codemirror, from = cm.getCursor('from').line, to = cm.getCursor('to').line;
    for (var n = from; n <= to; n++) {
      var line = cm.getLine(n), m = line.match(/^(\s*)[-*] \[[ xX]\] /);
      if (m) cm.replaceRange(m[1], { line: n, ch: 0 }, { line: n, ch: m[0].length });
      else cm.replaceRange('- [ ] ', { line: n, ch: line.match(/^\s*/)[0].length });
    }
    cm.focus();
  }
  // wraps the selection (or a placeholder, selected so typing replaces it)
  function wrap(before, after, placeholder) {
    return function (editor) {
      var cm = editor.codemirror, text = cm.getSelection() || placeholder;
      cm.replaceSelection(before + text + after);
      if (!cm.getSelection() && text === placeholder) {
        var end = cm.getCursor();
        cm.setSelection({ line: end.line, ch: end.ch - after.length - text.length },
                        { line: end.line, ch: end.ch - after.length });
      }
      cm.focus();
    };
  }
  // a block of its own, on a new line after the current one
  function block(text) {
    return function (editor) {
      var cm = editor.codemirror, line = cm.getCursor().line, current = cm.getLine(line);
      cm.replaceRange((current.trim() ? '\n\n' : '') + text, { line: line, ch: current.length });
      cm.focus();
    };
  }
  function footnote(editor) {
    var cm = editor.codemirror;
    var n = (cm.getValue().match(/\[\^\d+\]:/g) || []).length + 1;
    cm.replaceSelection('[^' + n + ']');
    var end = cm.lastLine();
    cm.replaceRange('\n\n[^' + n + ']: ', { line: end, ch: cm.getLine(end).length });
    cm.setCursor({ line: cm.lastLine(), ch: String(n).length + 5 });
    cm.focus();
  }
  // a colon, then the emoji suggestions the slash menu shows (SLASH_MENU_JS)
  function emoji(editor) {
    var cm = editor.codemirror, pos = cm.getCursor();
    var before = cm.getLine(pos.line).slice(0, pos.ch);
    if (before && !/\s$/.test(before)) { cm.replaceSelection(' '); pos = cm.getCursor(); }
    cm.replaceSelection(':');
    if (cm.suggestFrom) cm.suggestFrom(':', pos);
    cm.focus();
  }
  // the current lines as a paragraph (0) or a heading of that level - the
  // same level again turns it back into a paragraph. The post's title is
  // its h1, so the levels here start at 2.
  function setHeading(level) {
    return function (editor) {
      var cm = editor.codemirror, from = cm.getCursor('from').line, to = cm.getCursor('to').line;
      for (var n = from; n <= to; n++) {
        var line = cm.getLine(n), m = line.match(/^(\s*)(#{1,6})\s+/);
        var now = m ? m[2].length : 0, body = m ? line.slice(m[0].length) : line.replace(/^\s*/, '');
        var next = now === level ? 0 : level;
        cm.replaceRange((next ? new Array(next + 1).join('#') + ' ' : '') + body,
                        { line: n, ch: 0 }, { line: n, ch: line.length });
      }
      cm.focus();
    };
  }
  // the selected lines inside a fenced block, or out of one - EasyMDE's own
  // made inline `code` of a phrase within a line
  function codeBlock(editor) {
    var cm = editor.codemirror, from = cm.getCursor('from').line, to = cm.getCursor('to').line;
    if (/^```/.test(cm.getLine(from - 1) || '') && /^```\s*$/.test(cm.getLine(to + 1) || '')) {
      cm.replaceRange('', { line: to, ch: cm.getLine(to).length }, { line: to + 1, ch: cm.getLine(to + 1).length });
      cm.replaceRange('', { line: from - 1, ch: 0 }, { line: from, ch: 0 });
    } else if (from === to && !cm.getLine(from).trim()) {
      cm.replaceRange('```\n\n```', { line: from, ch: 0 }, { line: from, ch: cm.getLine(from).length });
      cm.setCursor({ line: from + 1, ch: 0 });
    } else {
      cm.replaceRange('\n```', { line: to, ch: cm.getLine(to).length });
      cm.replaceRange('```\n', { line: from, ch: 0 });
    }
    cm.focus();
  }
  // asks for images and uploads them where the cursor is - EasyMDE's own
  // needs its button on the toolbar itself, so from the ⋯ menu it did nothing
  function uploadImage(editor) {
    var input = document.createElement('input');
    input.type = 'file';
    input.multiple = true;
    input.accept = editor.options.imageAccept || 'image/*';
    input.hidden = true;
    input.addEventListener('change', function () {
      editor.uploadImagesUsingCustomFunction(editor.options.imageUploadFunction, input.files);
      input.remove();
    });
    document.body.appendChild(input);
    input.click();
  }
  // a shortcut as people write it: "Shift-Cmd-X" is Ctrl+Shift+X, or
  // Cmd+Shift+X on a Mac (editor_config.key_text says the same)
  var MAC = /Mac|iPhone|iPad/.test(navigator.platform || '');
  function keyText(k) {
    var parts = k.replace(/Cmd/g, MAC ? 'Cmd' : 'Ctrl').split('-');
    if (parts.length > 2 && parts[0] === 'Shift') { parts[0] = parts[1]; parts[1] = 'Shift'; }
    return parts.join('+');
  }
  function picker(target) {
    return function (editor) { window._activeEasyMDE = editor; openMediaPicker(target); };
  }
  function callout(kind) { return block('!!! ' + kind + ' "A title"\n    What it says, indented.'); }
  // What each command does. Its name, icon, shortcut and where it sits
  // are in editor_config.COMMANDS (EDITOR_PREFS.commands), for every part
  // of the editor at once.
  var ACTIONS = {
    'bold': EasyMDE.toggleBold, 'italic': EasyMDE.toggleItalic, 'strikethrough': EasyMDE.toggleStrikethrough,
    'inline-code': wrap('`', '`', 'code'), 'highlight': wrap('==', '==', 'highlighted'),
    'superscript': wrap('^', '^', '2'), 'subscript': wrap('~', '~', '2'), 'keys': wrap('++', '++', 'ctrl+c'),
    'emoji': emoji, 'clean-block': EasyMDE.cleanBlock,
    'paragraph': setHeading(0), 'heading': setHeading(2), 'subheading': setHeading(3), 'small-heading': setHeading(4),
    'quote': EasyMDE.toggleBlockquote, 'unordered-list': EasyMDE.toggleUnorderedList,
    'ordered-list': EasyMDE.toggleOrderedList, 'check-list': toggleChecklist, 'code': codeBlock,
    'callout': callout('note'), 'callout-tip': callout('tip'), 'callout-warning': callout('warning'),
    'callout-danger': callout('danger'),
    'tabs': block('=== "First"\n\n    In the first tab.\n\n=== "Second"\n\n    In the second tab.'),
    'definition': block('Term\n: What it means'), 'footnote': footnote,
    'abbreviation': block('*[HTML]: HyperText Markup Language'),
    'insert': function (editor) { editor.openInsert(document.querySelector('.editor-toolbar button.insert')); },
    'link': EasyMDE.drawLink, 'link-picker': function (editor) { openLinkPicker(editor); },
    'wiki-link': wrap('[[', ']]', 'Another post'), 'library': picker('__easymde_body__'),
    // no shortcut: Chrome only opens a file picker for a click - and the
    // library (Ctrl+Alt+I) has an Upload button of its own
    'upload-image': uploadImage, 'image': EasyMDE.drawImage, 'gallery': picker('__gallery__'),
    'table': EasyMDE.drawTable, 'horizontal-rule': EasyMDE.drawHorizontalRule, 'embed': block('https://'),
    'members-cut': block('<!-- members only from here -->'),
    'math': wrap('$', '$', 'E = mc^2'), 'diagram': block('```mermaid\ngraph LR; Idea --> Post\n```'),
    'undo': EasyMDE.undo, 'redo': EasyMDE.redo,
    'preview': EasyMDE.togglePreview, 'side-by-side': EasyMDE.toggleSideBySide, 'fullscreen': EasyMDE.toggleFullScreen,
    // the Help panel (EditorHelpPanel), from the top or at its shortcuts
    'guide': function () { toggleEditorHelp(); }, 'shortcuts': function () { openEditorHelp('shortcuts'); }
  };
  var PREFS = window.EDITOR_PREFS || { pinned: [], order: [], commands: [], menus: {} }, COMMANDS = {};
  PREFS.commands.forEach(function (c) {
    COMMANDS[c.id] = c;
    // a section (editor_config): each adds its markdown
    if (c.snippet) ACTIONS[c.id] = block(c.snippet);
  });
  // these still work while the preview shows (EasyMDE greys out the rest)
  var ALWAYS = ['preview', 'side-by-side', 'fullscreen', 'undo', 'redo', 'guide', 'shortcuts'];
  // a command as EasyMDE's toolbar wants it: its name, what it does, its
  // icon, and "Bold (Ctrl+B)" - daisyTooltips splits that in two
  function button(id) {
    var c = COMMANDS[id] || { label: id };
    // Insert says its name: it opens a list, not one thing
    var icon = id === 'insert' ? c.icon + '<span class="toolbar-word">' + c.label + '</span>' : c.icon;
    return { name: id, action: ACTIONS[id], icon: icon, className: ALWAYS.indexOf(id) > -1 ? 'no-disable' : undefined,
             title: c.label + (c.keys ? ' (' + keyText(c.keys) + ')' : '') };
  }
  // Go to, beside Insert at the toolbar's right end in every style: the
  // post's own sections, to jump to one (slash_menu.js, openSections).
  // Not one of the buttons you choose - it can't be taken off - and, like
  // Insert, it says its name. Off while the preview shows: the cursor it
  // moves is in the text.
  function goToButton() {
    var m = PREFS.menus.goto;
    return { name: 'goto', icon: m.icon + '<span class="toolbar-word">' + m.label + '</span>' + PREFS.icons['chevron-down'],
             action: function (editor) { editor.openSections(document.querySelector('.editor-toolbar button.goto')); },
             title: PREFS.goTo.label };
  }
  function buildToolbar() {
    var item = button;
    // Minimal: no toolbar at all (input.css hides it) - the slash menu,
    // the bar over the text and the keyboard do the rest
    if (PREFS.rows === 'none') return [item('insert'), goToButton()];
    // Classic menus: Text ▾ Blocks ▾ Insert ▾ History ▾ View ▾ Help ▾,
    // each every command in its section, a divider between them as
    // between the Icons toolbar's sections
    if (PREFS.rows === 'menus') {
      var menus = [];
      (PREFS.sections || []).forEach(function (section, i) {
        if (i) menus.push('|');
        menus.push({ name: 'section-' + section.name.toLowerCase(), title: section.name,
                     attributes: { 'data-section': section.name },
                     icon: '<span class="toolbar-word">' + section.name + '</span>' + PREFS.icons['chevron-down'],
                     children: section.ids.map(button) });
      });
      menus.push('|', goToButton());
      return menus;
    }
    // Go to and Insert aren't in a section's row: they're at the toolbar's right end
    var keys = PREFS.pinned.filter(function (id) { return id !== 'insert'; }), groups = PREFS.groups || {},
        inSection = {};
    (PREFS.sections || []).forEach(function (section) { inSection[section.name] = section.ids; });
    // the rest of a section - what you didn't choose - under a ▾ at its end
    var rest = function (group) {
      return (inSection[group] || []).filter(function (id) { return keys.indexOf(id) === -1; });
    };
    var restMenu = function (group) {
      var ids = rest(group);
      return ids.length ? { name: 'rest-' + group.toLowerCase(), title: 'More in ' + group,
                            attributes: { 'data-rest': group }, icon: PREFS.icons['chevron-down'],
                            children: ids.map(button) } : null;
    };
    // a divider between sections (editor_config keeps each one's together)
    var bar = [];
    keys.forEach(function (key, i) {
      if (i && groups[key] !== groups[keys[i - 1]]) {
        var more = restMenu(groups[keys[i - 1]]);
        if (more) bar.push(more);
        bar.push('|');
      }
      bar.push(item(key));
    });
    var last = keys.length && restMenu(groups[keys[keys.length - 1]]);
    if (last) bar.push(last);
    if (keys.length) bar.push('|');
    bar.push(goToButton(), item('insert'));
    // ⋯ has a copy of each button and of each section's rest, shown only
    // for what doesn't fit the row (fitToolbar) - and isn't there at all
    // when everything does
    var restIds = [];
    keys.forEach(function (key, i) {
      if (i === keys.length - 1 || groups[key] !== groups[keys[i + 1]]) restIds = restIds.concat(rest(groups[key]));
    });
    var copies = keys.concat(restIds).map(function (key) {
      var copy = button(key);
      copy.name = key + '-more';
      return copy;
    });
    if (copies.length) bar.push({ name: 'more', icon: PREFS.menus.more.icon, title: PREFS.menus.more.label, children: copies });
    return bar;
  }

  // EasyMDE names its buttons with title= - the browser's own tooltip.
  // Swapped for daisyUI's, like every other button in the admin: "Bold ·
  // Ctrl+B" there, and the menus show the name and the shortcut apart.
  function daisyTooltips(toolbar) {
    toolbar.querySelectorAll('[title]').forEach(function (b) {
      var m = b.title.match(/^(.*?) \((.+)\)$/);
      b.dataset.name = m ? m[1] : b.title;
      if (m) b.dataset.key = m[2];
      var tip = b.dataset.name + (m ? ' · ' + b.dataset.key : '');
      b.setAttribute('aria-label', tip);
      b.removeAttribute('title');
      // Go to says its name, and what it's for
      if (b.classList.contains('goto')) { b.dataset.tip = PREFS.goTo.label; b.classList.add('tooltip', 'tooltip-bottom'); return; }
      if (b.querySelector('.toolbar-word')) return;  // its name is on it
      b.dataset.tip = tip;
      b.classList.add('tooltip', b.closest('.easymde-dropdown-content') ? 'tooltip-right' : 'tooltip-bottom');
    });
  }
  // a menu's buttons with their names beside them, and their shortcuts -
  // the name is right there, so no tooltip on top of it
  function nameButton(b) {
    var name = document.createElement('span');
    name.textContent = b.dataset.name || b.getAttribute('aria-label') || '';
    b.appendChild(name);
    if (b.dataset.key) {
      var key = document.createElement('kbd');
      key.className = 'menu-key kbd kbd-xs';
      key.textContent = b.dataset.key;
      b.appendChild(key);
    }
    b.classList.remove('tooltip', 'tooltip-right', 'tooltip-bottom');
    b.removeAttribute('data-tip');
  }
  // On a phone the toolbar scrolls sideways and cuts off whatever hangs
  // below it, so its ⋯ menu is fixed to the screen
  // (input.css) - opened here, under the button that was tapped
  function placeMenus(toolbar) {
    function place(e) {
      var dropdown = e.target.closest && e.target.closest('.easymde-dropdown');
      if (!dropdown) return;
      // a wider screen: the menu hangs under its button, moved back in
      // if it would run past either edge of the screen
      if (!matchMedia('(width < 40rem)').matches) {
        var panel = dropdown.querySelector('.easymde-dropdown-content');
        if (!panel || dropdown.contains(e.relatedTarget)) return;
        panel.style.translate = '';
        var box = panel.getBoundingClientRect(), shift = 0;
        if (box.right > innerWidth - 8) shift = innerWidth - 8 - box.right;
        if (box.left + shift < 8) shift = 8 - box.left;
        if (shift) panel.style.translate = Math.round(shift) + 'px 0';
        return;
      }
      var menu = dropdown.querySelector('.easymde-dropdown-content'), at = dropdown.getBoundingClientRect();
      menu.style.top = (at.bottom + 4) + 'px';
      menu.style.maxHeight = (innerHeight - at.bottom - 16) + 'px';
      // More spans the screen; a narrower menu lines up with its button
      if (!menu.classList.contains('more-grouped'))
        menu.style.left = Math.max(12, Math.min(at.left, innerWidth - menu.offsetWidth - 12)) + 'px';
    }
    toolbar.addEventListener('focusin', place);
    toolbar.addEventListener('pointerdown', place);
    // A menu is open while its button has focus, so clicking the button
    // again only kept it open. Now it closes, like any other menu: the
    // mousedown takes the focus away, and the click that follows is
    // swallowed - EasyMDE's own onclick focuses the button (for iOS,
    // where a tap doesn't) and would open it straight back up.
    var closing = null;
    toolbar.addEventListener('mousedown', function (e) {
      var dropdown = e.target.closest && e.target.closest('.easymde-dropdown');
      closing = null;
      if (!dropdown || e.target.closest('.easymde-dropdown-content')) return;
      if (dropdown.contains(document.activeElement)) {
        e.preventDefault();
        closing = dropdown;
        document.activeElement.blur();
      }
    });
    toolbar.addEventListener('click', function (e) {
      if (closing && closing.contains(e.target) && !e.target.closest('.easymde-dropdown-content')) e.stopPropagation();
      closing = null;
    }, true);
  }
  // ⋯ and the classic menus: each button with its name and shortcut
  function nameMenus(toolbar) {
    toolbar.querySelectorAll('.easymde-dropdown > .easymde-dropdown-content').forEach(function (menu) {
      [].forEach.call(menu.children, function (b) { if (!b.querySelector('.toolbar-word')) nameButton(b); });
      menu.classList.add('levels');
      // a menu is open while it has focus: once an item's chosen, it
      // closes - Preview and the like don't move the focus on by
      // themselves. Capturing: EasyMDE stops each item's click.
      menu.addEventListener('click', function () {
        setTimeout(function () {
          if (menu.parentNode.contains(document.activeElement)) document.activeElement.blur();
        });
      }, true);
    });
  }
  // The status line: "342 words · 2 min read · Saved 3 min ago".
  // Reading time at 200 words a minute, as the post's own
  // (render.reading_time); the words are runs of letters and numbers, so
  // markdown's marks don't count.
  var statusEls = {}, lastSaved = null, saveFailed = false, focusWords = null, sessionTick = null;
  function ago(time) {
    var min = Math.floor((Date.now() - time) / 60000);
    if (min < 1) return 'just now';
    if (min < 60) return min + ' min ago';
    var hours = Math.floor(min / 60);
    return hours === 1 ? 'an hour ago' : hours + ' hours ago';
  }
  function updateStatus() {
    // form: not yet while the editor's still being set up (its mode, below, redraws it)
    if (!mde || !statusEls.words || !form) return;
    var n = (mde.value().match(/[\p{L}\p{N}]+(?:['’-][\p{L}\p{N}]+)*/gu) || []).length;
    // Settings > Editor > Writing progress: the words written today - the
    // count now, less the post's at midnight (posts.words_at_day_start) -
    // and a ring filling towards the post's word goal, as you type it in
    // empty: the default (Settings > Editor); 0: none
    var goalField = form.elements.word_goal, goal = !goalField ? 0 : goalField.value.trim() === ''
      ? parseInt(goalField.dataset.default, 10) || 0 : parseInt(goalField.value, 10) || 0;
    // reached: the ring full and the count in the palette's success colour,
    // counting on ("Goal reached" in words is a writing session's)
    var reached = goal && n >= goal;
    statusEls.words.textContent = goal && !reached ? n.toLocaleString() + ' of ' + goal.toLocaleString() + ' words'
      : n === 1 ? '1 word' : n.toLocaleString() + ' words';
    statusEls.words.classList.toggle('text-success', !!reached);
    statusEls.read.textContent = Math.max(1, Math.ceil(n / 200)) + ' min read';
    var today = form.dataset.dayWords === undefined ? 0 : n - parseInt(form.dataset.dayWords, 10);
    statusEls.today.textContent = today > 0 ? '+' + today.toLocaleString() + ' today' : '';
    statusEls.today.hidden = today <= 0;
    var ring = statusEls.ring;
    if (goal && !ring) {
      ring = statusEls.ring = document.createElement('div');
      ring.className = 'radial-progress mr-1.5 align-[-0.15em] [--size:0.875rem] [--thickness:2px]';
      ring.setAttribute('role', 'progressbar');
      statusEls.words.parentNode.insertBefore(ring, statusEls.words);
    }
    if (ring) {
      var done = Math.min(100, Math.round(n / (goal || 1) * 100));
      ring.hidden = !goal;
      ring.style.setProperty('--value', done);
      ring.setAttribute('aria-valuenow', done);
      ring.setAttribute('aria-label', done + '% of your word goal');
      ring.classList.toggle('text-success', done >= 100);
      ring.classList.toggle('text-primary', done < 100);
    }
    statusEls.saved.textContent = saveFailed ? "Couldn't save" : dirty ? 'Unsaved changes'
      : lastSaved ? 'Saved ' + ago(lastSaved) : form.dataset.draftKey === 'new' ? 'Not saved yet' : 'Saved';
    statusEls.saved.classList.toggle('text-warning', dirty || saveFailed);
    // Post settings' own Save, at its foot, while there's something to save
    form.toggleAttribute('data-unsaved', dirty || saveFailed);
    // just the words where Focus's bar is short of room (fitFocusBar)
    if (focusWords) focusWords.textContent = focusWords.hasAttribute('data-short') ? statusEls.words.textContent
      : statusEls.words.textContent + ' · ' + statusEls.read.textContent + (today > 0 ? ' · ' + statusEls.today.textContent : '');
    if (sessionTick) sessionTick(n);
  }
  var mde = new EasyMDE({
    element: el,
    autoDownloadFontAwesome: false,  // the icons are Lucide's (editor_icons)
    // EasyMDE's own spell checker is English-only and heavy; the
    // browser's own checks in the writer's language, and only works
    // with contenteditable input (Settings > Editor > Check spelling)
    spellChecker: false,
    nativeSpellcheck: (window.EDITOR_PREFS || {}).spellcheck !== false,
    inputStyle: (window.EDITOR_PREFS || {}).spellcheck !== false ? "contenteditable" : "textarea",
    // the status line: words, reading time and whether it's saved
    // (updateStatus, below) - what a writer checks, not lines and the
    // cursor's column. EasyMDE's own "autosave" option is deliberately
    // not used: it would keep a second copy of the draft in its own
    // localStorage format, separate from the draft recovery below
    status: ['words', 'read', 'today', 'saved'].map(function (name) {
      return { className: 'status-' + name, defaultValue: function (el) { statusEls[name] = el; },
               onUpdate: function () { updateStatus(); } };
    }),
    uploadImage: true,
    imageUploadFunction: function (file, onSuccess, onError) {
      var data = new FormData();
      data.append('image', file);
      fetch('/admin/upload-image', { method: 'POST', body: data })
        .then(function (r) { return r.json(); })
        .then(function (r) { r.url ? onSuccess(r.url) : onError(r.error || 'upload failed'); })
        .catch(function () { onError('upload failed'); });
    },
    // the preview pane renders real HTML, but Tailwind's base reset
    // strips all default heading/list/quote styling from it - without
    // this it looked like "preview does nothing" when it was actually
    // rendering correctly, just with an h1 that's the same size as
    // body text. Same prose classes the published post body already
    // uses (routes/public.py), so the preview now looks like the
    // actual post instead of like unstyled text - at its size too
    // (pages._prose: 16px, 18px from 48rem, as the writing is)
    previewClass: ["editor-preview", "prose", "md:prose-lg", "max-w-none", "prose-li:my-1", "[&_:not(pre)>code]:wrap-anywhere",
      // the writing's own 36em column, at its size (--editor-fs), centred; Wide fills the box (#post-form is the group)
      "[&>*]:max-w-[calc(36*var(--editor-fs,1rem))]", "[&>*]:mx-auto", "group-data-[editor-width=wide]/pf:[&>*]:max-w-none"],
    // the preview is the published post's own rendering (/admin/preview),
    // not EasyMDE's - galleries, embeds, callouts, math and credits look
    // exactly as they will. Asked for a moment after typing stops.
    previewRender: function (plainText, preview) {
      clearTimeout(window._previewTimer);
      window._previewTimer = setTimeout(function () {
        var data = new FormData();
        data.append('body', plainText);
        fetch('/admin/preview', { method: 'POST', body: data })
          .then(function (r) { return r.ok ? r.text() : Promise.reject(); })
          .then(function (html) {
            preview.innerHTML = html;
            // the title at the top, as the post shows it - it's not in the text
            var title = document.createElement('h1');
            title.dataset.previewTitle = '';
            title.className = 'not-prose text-2xl sm:text-3xl font-bold leading-tight mb-4';
            var field = document.querySelector('#post-form input[name=title]');
            title.textContent = field ? field.value : '';
            title.hidden = !title.textContent.trim();
            preview.prepend(title);
            if (window.mermaid) drawMermaid(preview.querySelectorAll('pre.mermaid'));
            if (window.renderMathInElement) renderMathInElement(preview, { delimiters: [
              { left: '\[', right: '\]', display: true }, { left: '\(', right: '\)', display: false }],
              throwOnError: false });
          })
          .catch(function () {});
      }, 300);
      return preview.innerHTML || '<p class="text-base-content/50">Rendering preview…</p>';
    },
    // the same "-" the slash menu and the help use
    unorderedListStyle: '-',
    // Tab and Shift+Tab move the line four spaces in and out (EasyMDE's
    // own keys), as wide as markdown counts a tab: shown two wide, people
    // pressed it twice and got a code block
    tabSize: 4,
    indentWithTabs: false,
    placeholder: (window.EDITOR_PREFS || {}).placeholder || '',
    // EasyMDE binds none of its own: every shortcut is the command list's,
    // bound below. null switches an EasyMDE default off.
    shortcuts: { toggleBold: null, toggleItalic: null, drawLink: null, toggleBlockquote: null,
                 toggleStrikethrough: null, cleanBlock: null, toggleUnorderedList: null, toggleOrderedList: null,
                 togglePreview: null, toggleFullScreen: null, toggleSideBySide: null, toggleCodeBlock: null,
                 drawImage: null, toggleHeadingSmaller: null, toggleHeadingBigger: null,
                 toggleHeading1: null, toggleHeading2: null, toggleHeading3: null,
                 toggleHeading4: null, toggleHeading5: null, toggleHeading6: null },
    // Minimal: no formatting buttons, but preview, full screen and help (buildToolbar)
    toolbar: buildToolbar()
  });
  window._activeEasyMDE = mde;
  if (mde.gui.toolbar) {
    daisyTooltips(mde.gui.toolbar); nameMenus(mde.gui.toolbar);
    placeMenus(mde.gui.toolbar);
  }
  // every command's shortcut, as Ctrl and as Cmd - CodeMirror tells them
  // apart. The keys are written in CodeMirror's order (Shift, then
  // Cmd, then Alt), or they never fire. Undo and Redo are CodeMirror's
  // own; Help's the page answers anywhere (below).
  var keymap = {};
  PREFS.commands.forEach(function (c) {
    if (!c.keys || c.builtin || !ACTIONS[c.id]) return;
    var run = function () { ACTIONS[c.id](mde); };
    keymap[c.keys] = run;
    keymap[c.keys.replace('Cmd', 'Ctrl')] = run;
  });
  mde.codemirror.addKeyMap(keymap);
  // Tab indents, so on its own it would trap the keyboard in the text:
  // Esc, then Tab (or Shift+Tab) moves on, as in other code editors. The
  // title is the top of the text on screen, so it comes first going in and
  // last coming out, though it sits inside the text's own box.
  var tabLeaves = false, wrapEl = mde.codemirror.getWrapperElement();
  var beside = function (forward) {
    var all = [].filter.call(document.querySelectorAll(
      'a[href], button:not([disabled]), input:not([disabled]):not([type=hidden]), select:not([disabled]), ' +
      'textarea:not([disabled]), summary, [tabindex]:not([tabindex="-1"])'), function (el) {
      return el.tabIndex >= 0 && el.getClientRects().length && !el.closest('[inert], [hidden], dialog:not([open])') &&
             !wrapEl.contains(el);
    });
    var after = all.filter(function (el) { return !!(wrapEl.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING); });
    return forward ? after[0] : all[all.length - after.length - 1];
  };
  mde.tabBeside = beside;
  wrapEl.addEventListener('keydown', function (e) {
    if (e.key === 'Tab' && tabLeaves && !e.ctrlKey && !e.metaKey && !e.altKey) {
      e.stopPropagation();
      var to = e.shiftKey ? mde.titleInput || beside(false) : beside(true);
      if (to) { e.preventDefault(); to.focus(); }
    }
    tabLeaves = e.key === 'Escape' || (e.key === 'Shift' && tabLeaves);
  }, true);
  // Tab from the bar lands on the text's box, which holds the title
  // (only for Tab itself - a click or a button that moves the cursor here is its own)
  var tabbed = false;
  document.addEventListener('keydown', function (e) { tabbed = e.key === 'Tab'; }, true);
  document.addEventListener('mousedown', function () { tabbed = false; }, true);
  wrapEl.addEventListener('focusin', function (e) {
    var title = mde.titleInput, from = e.relatedTarget;
    if (!tabbed || !title || !from || wrapEl.contains(from)) return;
    tabbed = false;
    var forward = !!(from.compareDocumentPosition(wrapEl) & Node.DOCUMENT_POSITION_FOLLOWING);
    if (forward && e.target !== title) title.focus();
    else if (!forward && e.target === title) mde.codemirror.focus();
  });
  // CodeMirror's markdown takes any [words] for a link's text, so a
  // placeholder like [TOTAL] looked like a link and lit the Link button.
  // Only words with somewhere to go are: [text](address), [text][ref], a
  // reference's [ref]: address, a [[wiki link]], an image or a [^footnote].
  (function () {
    var cm = mde.codemirror, CM = cm.constructor, base = cm.getMode();
    if (!CM || !CM.defineMode || !base || !base.token) return;
    function goesSomewhere(line, at) {
      var open = line.charAt(at) === '[' ? at : line.lastIndexOf('[', at);
      var close = line.indexOf(']', Math.max(at, open));
      if (open < 0 || close < 0) return true;
      var before = line.charAt(open - 1), after = line.charAt(close + 1);
      return (after === '(' || after === '[' || after === ':') || before === '[' || before === '!' ||
        line.charAt(open + 1) === '[' || line.charAt(open + 1) === '^';
    }
    // what isn't plain writing stands out (input.css, editor-blocks): a
    // section's Section: line, its settings (the names the registry gives:
    // sections.OPTIONS) and the blocks written as a line (Buttons:, Pull
    // quote:, Countdown:, a fold, a gallery). A setting left at Default is
    // faded, the ones changed at full strength.
    var KEYS = ((PREFS.options || {}).lineKeys || []).map(function (k) { return k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }).join('|');
    var SECTION = /^Section:[ \t]*\S/i, SETTING = new RegExp('^(' + KEYS + '):[ \\t]*\\S', 'i'),
        UNCHANGED = /^[^:]*:[ \t]*default[ \t]*$/i,
        BLOCK = /^((Buttons|Pull quote|Countdown):[ \t]*\S|(\?\?\?\+?|!!!)[ \t]|```gallery\b)/i;
    function lineKind(line) {
      return SECTION.test(line) ? 'line-sb-section' :
        KEYS && SETTING.test(line) ? 'line-sb-setting' + (UNCHANGED.test(line) ? ' line-sb-default' : '') :
        BLOCK.test(line) ? 'line-sb-block' : '';
    }
    // **, *, _ and ~~ that are never closed are only characters (the
    // preview shows them as typed), but CodeMirror styles everything
    // after an opening one as bold, italic or struck through to the end of
    // the paragraph. Styled only where its closing mark follows, on this
    // line or a later one in the same paragraph.
    function closes(stream, from, mark) {
      if (stream.string.indexOf(mark, from) >= 0) return true;
      for (var n = 1; n <= 40; n++) {
        var next = stream.lookAhead(n);
        if (next == null || !/\S/.test(next) || /^\s*([-+*]|\d+[.)]|#{1,6})\s/.test(next)) return false;
        if (next.indexOf(mark) >= 0) return true;
      }
      return false;
    }
    var MARKS = [['strong', function (s) { return s.strong ? s.strong + s.strong : ''; }],
                 ['em', function (s) { return s.em || ''; }],
                 ['strikethrough', function (s) { return s.strikethrough ? '~~' : ''; }]];
    function unclosed(stream, before, state, style) {
      MARKS.forEach(function (m) {
        var name = m[0], was = m[1](before), now = m[1](state), mark = was || now;
        if (!mark || !style || style.indexOf(name) < 0) return;
        // an opening mark looks for its partner after itself; text inside,
        // or the closing mark, from where it starts
        if (closes(stream, was ? stream.start : stream.pos, mark)) return;
        style = style.replace(new RegExp('(^|\\s)(formatting-)?' + name + '(?=\\s|$)', 'g'), ' ');
        // the mark itself then reads as the characters it is
        if (!/formatting-/.test(style)) style = style.replace(/(^|\s)formatting(?=\s|$)/g, ' ');
        style = style.replace(/\s+/g, ' ').trim() || null;
      });
      return style;
    }
    var mode = {};
    for (var key in base) mode[key] = base[key];
    mode.token = function (stream, state) {
      var kind = stream.sol() ? lineKind(stream.string) : '';
      // the markdown's own state, under the overlay EasyMDE adds
      var md = state.base || state;
      var before = { strong: md.strong, em: md.em, strikethrough: md.strikethrough };
      var style = unclosed(stream, before, md, base.token(stream, state));
      // a footnote's text ([^1]: The note.) reads like a link reference's
      // address to CodeMirror, which styled its first word as one
      if (style && /(^|\s)url(\s|$)/.test(style) && /^\s*\[\^[^\]]+\]:/.test(stream.string)) {
        style = style.replace(/(^|\s)(string|url)(?=\s|$)/g, ' ').trim() || null;
      }
      if (style && /(^|\s)link(\s|$)/.test(style) && !goesSomewhere(stream.string, stream.start)) {
        style = style.replace(/(^|\s)(formatting-)?link(?=\s|$)/g, ' ').trim() || null;
      }
      return kind ? ((style || '') + ' ' + kind).trim() : style;
    };
    CM.defineMode('soloblog-markdown', function () { return mode; });
    cm.setOption('mode', 'soloblog-markdown');
  })();
  // the slash menu runs commands by name
  mde.runCommand = function (id) { if (ACTIONS[id]) ACTIONS[id](mde); };
  mde.keyText = keyText;
  // the Help panel's Insert: an example on a line of its own
  mde.insertBlock = function (text) { block(text)(mde); };
  setupSlashMenu(mde, PREFS.slash);
  // Chrome only checks text you've touched, so a post's whole text put in
  // at once (a draft brought back, a template, a revision) showed no
  // underlines until opened again. Then, and only then, it's asked to check
  // all of it again: turning spell check off and on does that. Never on a
  // pause or a scroll - the underlines flickered, and on a phone it dropped
  // a selection - and not while a word is still being composed (a phone
  // keyboard's suggestions), something is selected or a finger is down.
  if (PREFS.spellcheck !== false) {
    var recheckAt = 0, composing = false, touching = 0, cmSpell = mde.codemirror;
    var busy = function () {
      return composing || touching > 0 || cmSpell.somethingSelected() || !window.getSelection().isCollapsed;
    };
    var recheck = function () {
      clearTimeout(recheckAt);
      recheckAt = setTimeout(function () {
        var field = cmSpell.getInputField();
        if (!field || field.getAttribute('spellcheck') !== 'true') return;
        if (busy()) { recheck(); return; }
        field.setAttribute('spellcheck', 'false');
        requestAnimationFrame(function () { field.setAttribute('spellcheck', 'true'); });
      }, 600);
    };
    cmSpell.on('changes', function (_, changes) {
      if (changes.some(function (c) { return c.origin === 'setValue'; })) recheck();
    });
    var spellField = cmSpell.getInputField(), spellWrap = cmSpell.getWrapperElement();
    spellField.addEventListener('compositionstart', function () { composing = true; });
    spellField.addEventListener('compositionend', function () { composing = false; });
    spellWrap.addEventListener('touchstart', function (e) { touching = e.touches.length; }, { passive: true });
    ['touchend', 'touchcancel'].forEach(function (name) {
      spellWrap.addEventListener(name, function (e) { touching = e.touches.length; }, { passive: true });
    });
  }
  // A right-click puts the cursor where it was made, unless that's inside
  // what's selected. Firefox leaves the cursor where it was, and the editor
  // only reads what the browser changed near the cursor - so a spelling
  // correction picked on another line was put back as it was.
  mde.codemirror.getWrapperElement().addEventListener('contextmenu', function (e) {
    var cmAt = mde.codemirror, at = cmAt.coordsChar({left: e.clientX, top: e.clientY}, 'window');
    var before = function (a, b) { return a.line < b.line || (a.line === b.line && a.ch < b.ch); };
    var inside = cmAt.listSelections().some(function (r) {
      return !before(at, r.from()) && !before(r.to(), at);
    });
    if (!inside) cmAt.setCursor(at);
  }, true);

  // lets you drag the editor taller for a longer writing session (CSS
  // resize handle on the actual scroll area, see input.css) - a manual
  // resize doesn't tell CodeMirror its own measurements changed, so
  // without this, line wrapping and the cursor position can drift out
  // of sync with where the text actually sits after you drag it
  if (window.ResizeObserver) {
    new ResizeObserver(function () { mde.codemirror.refresh(); })
      .observe(mde.codemirror.getScrollerElement());
  }
  // Preview, outside Focus: as tall as what it shows, as Write is as tall
  // as its text - it scrolled inside Write's height. Write gets its own
  // height back.
  (function () {
    var wrap = mde.codemirror.getWrapperElement(), watched = null;
    var fit = function () {
      var pv = wrap.querySelector(':scope > .editor-preview');
      // Focus sizes the box itself, and Write's height waits for the way out
      if (mde.isFullscreenActive()) { if (pv) pv.style.overflowY = ''; return; }
      var on = pv && pv.classList.contains('editor-preview-active');
      if (!on) {
        if (pv) pv.style.overflowY = '';
        if (wrap.dataset.writeHeight !== undefined) { wrap.style.height = wrap.dataset.writeHeight; delete wrap.dataset.writeHeight; }
        return;
      }
      if (wrap.dataset.writeHeight === undefined) wrap.dataset.writeHeight = wrap.style.height;
      // the box's own borders too, and again if a phone's rounding left it
      // short: a pixel or two short was a tiny scrollbar of its own, which
      // caught the first swipe instead of the page
      var borders = wrap.offsetHeight - wrap.clientHeight;
      pv.style.overflowY = '';
      wrap.style.height = Math.max(pv.scrollHeight + borders, wrap.querySelector('.CodeMirror-scroll').offsetHeight) + 'px';
      if (pv.scrollHeight > pv.clientHeight) wrap.style.height = wrap.offsetHeight + pv.scrollHeight - pv.clientHeight + 'px';
      pv.style.overflowY = 'hidden';
    };
    var watch = function () {
      var pv = wrap.querySelector(':scope > .editor-preview');
      if (!pv || pv === watched) return;
      watched = pv;
      // turned on or off, filled in, and pictures arriving
      new MutationObserver(fit).observe(pv, { attributes: true, attributeFilter: ['class'], childList: true, subtree: true });
      pv.addEventListener('load', fit, true);
    };
    // and in or out of Focus, where it scrolls again
    new MutationObserver(function () { watch(); fit(); }).observe(wrap, { childList: true, attributes: true, attributeFilter: ['class'] });
    watch();
    // the words re-wrap when the fonts arrive or the phone turns
    if (document.fonts) document.fonts.ready.then(fit);
    var fitWidth = window.innerWidth;
    window.addEventListener('resize', function () { if (window.innerWidth !== fitWidth) { fitWidth = window.innerWidth; fit(); } });
  })();
  // on a touch screen the browser's own corner is too small to hold:
  // a grip a thumb can drag, in the same corner
  (function () {
    var wrap = mde.codemirror.getWrapperElement(), grip = document.createElement('div');
    grip.className = 'hidden pointer-coarse:flex absolute bottom-0 right-0 z-10 size-11 items-end justify-end p-1.5 ' +
                     'touch-none cursor-ns-resize text-base-content/40 [.CodeMirror-fullscreen_&]:hidden';
    grip.setAttribute('aria-hidden', 'true');
    grip.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" class="size-4" viewBox="0 0 16 16" fill="none" ' +
                     'stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M15 6 6 15M15 11l-4 4"/></svg>';
    var from = null;
    grip.addEventListener('pointerdown', function (e) {
      from = { y: e.clientY, h: wrap.offsetHeight };
      grip.setPointerCapture(e.pointerId);
      e.preventDefault();
    });
    grip.addEventListener('pointermove', function (e) {
      if (from) wrap.style.height = Math.max(300, from.h + e.clientY - from.y) + 'px';
    });
    grip.addEventListener('pointerup', function () { from = null; mde.codemirror.refresh(); });
    grip.addEventListener('pointercancel', function () { from = null; });
    wrap.appendChild(grip);
    // and the browser's own corner gone from under it (important: input.css's is)
    wrap.classList.add('pointer-coarse:resize-none!');
  })();

  // save-state feedback: dirty flag flips the moment anything changes,
  // clears on submit, and warns before a navigate-away loses work.
  // status is re-queried each time, not cached - an htmx save swaps
  // #save-status's whole element (outerHTML) for the server's own
  // "Saved." response, so a cached reference would go stale the
  // moment the very first save completes.
  var form = document.getElementById('post-form');
  var dirty = false;
  function markDirty() {
    dirty = true;
    saveFailed = false;
    var status = document.getElementById('save-status');
    if (status) { status.textContent = 'Unsaved'; paintStatus(status, 'text-warning'); }
    updateStatus();
  }
  mde.codemirror.on('change', markDirty);
  // Undo and Redo greyed out while there's nothing to undo or redo -
  // wherever they are: the toolbar, its menus and ⋯, a phone's bar
  function syncHistory() {
    var size = mde.codemirror.historySize();
    [['undo', size.undo], ['redo', size.redo]].forEach(function (pair) {
      var id = pair[0];
      document.querySelectorAll('.editor-toolbar button.' + id + ', .editor-toolbar button.' + id + '-more, ' +
                                '.editor-phonebar [data-id="' + id + '"], .editor-sheet [data-id="' + id + '"]')
        .forEach(function (b) {
          b.disabled = !pair[1];
          // important: the toolbar's buttons start from all: unset (input.css)
          b.classList.add('disabled:opacity-40!', 'disabled:pointer-events-none!');
        });
    });
  }
  mde.codemirror.on('changes', syncHistory);
  setTimeout(syncHistory);  // once the phone's bar is made, below
  // what the cursor is in, lit up wherever its button is. EasyMDE's own
  // goes by its names: "heading" is any heading, so Heading lit for a
  // subheading too, and a checklist lit the bullet list
  function syncFormatting() {
    var cm = mde.codemirror, s = mde.getState();
    var check = /^\s*[-*+]\s+\[[ xX]\]/.test(cm.getLine(cm.getCursor().line));
    var on = { heading: s['heading-2'], subheading: s['heading-3'], 'small-heading': s['heading-4'],
               bold: s.bold, italic: s.italic, strikethrough: s.strikethrough, code: s.code, quote: s.quote,
               link: s.link, 'ordered-list': s['ordered-list'], 'unordered-list': s['unordered-list'] && !check,
               'check-list': check };
    Object.keys(on).forEach(function (id) {
      document.querySelectorAll('.editor-toolbar button.' + id + ', .editor-toolbar button.' + id + '-more, ' +
                                '.editor-phonebar [data-id="' + id + '"]')
        .forEach(function (b) { b.classList.toggle('active', !!on[id]); });
    });
  }
  mde.codemirror.on('cursorActivity', syncFormatting);
  // the post's state beside its heading, as Post settings change it -
  // before it's saved (routes/editor.py STATE_LOOK, the lists' pills)
  var stateEl = document.getElementById('post-state');
  if (stateEl) {
    var LOOK = { Published: 'badge-success', Draft: 'badge-warning', Scheduled: 'badge-info', Unlisted: 'badge-neutral' };
    var loadedAt = Date.now(), siteNow = Date.parse(stateEl.dataset.now + 'Z');
    var syncState = function () {
      var f = form.elements, when = f.scheduled_at && f.scheduled_at.value;
      var state = !(f.published && f.published.checked) ? 'Draft'
        : when && Date.parse(when + 'Z') > siteNow + Date.now() - loadedAt ? 'Scheduled'
        : f.unlisted && f.unlisted.checked ? 'Unlisted' : 'Published';
      stateEl.textContent = state;
      Object.keys(LOOK).forEach(function (k) { stateEl.classList.toggle(LOOK[k], k === state); });
    };
    form.addEventListener('change', syncState);
    form.addEventListener('input', syncState);
    form.addEventListener('reset', function () { setTimeout(syncState); });  // Discard
  }
  // The post's sections, in the order they're written: the kind (its
  // "Section:" line), the words of the "##" heading above it, and the line
  // that heading's on - the Go to menu lists them (slash_menu.js), and
  // marks the one the cursor's in
  mde.sections = function () {
    var cm = mde.codemirror, n = cm.lineCount(), fence = false, heads = [], found = [], last = -1;
    for (var i = 0; i < n; i++) {
      var t = cm.getLine(i), m;
      if (/^```/.test(t)) { fence = !fence; continue; }
      if (fence) continue;
      if (/^#{1,2}[ \t]/.test(t)) { heads.push(i); last = i; continue; }
      m = /^Section:[ \t]*(\S.*?)[ \t]*$/i.exec(t);
      if (!m) continue;
      // the heading straight above it, empty lines between allowed
      var above = last > -1 && /^##[ \t]/.test(cm.getLine(last));
      for (var k = last + 1; above && k < i; k++) if (cm.getLine(k).trim()) above = false;
      found.push({ kind: m[1], heading: above ? cm.getLine(last).replace(/^##[ \t]+|[ \t]+#*[ \t]*$/g, '') : '',
                   line: above ? last : i });
    }
    // it runs to the next heading of its own level or above
    var at = cm.getCursor().line;
    found.forEach(function (sec) {
      var next = heads.filter(function (h) { return h > sec.line; })[0];
      sec.here = at >= sec.line && (next === undefined || at < next);
    });
    return found;
  };
  // the cursor to the start of a line, which comes up near the top of the
  // text (Preview goes back to Write first)
  var flashed;
  mde.goToLine = function (line) {
    var cm = mde.codemirror;
    if (mde.isPreviewActive()) EasyMDE.togglePreview(mde);
    cm.focus();
    cm.setCursor({ line: line, ch: 0 });
    var at = cm.charCoords({ line: line, ch: 0 }, 'local');
    cm.scrollTo(null, Math.max(0, at.top - 24));
    // Focus and side by side: the text is a box of its own, with the bars
    // over its top - the heading comes up just under them, or, with
    // Typewriter scrolling, in the middle where that keeps the line
    var bars = mde.gui.toolbar;
    if (bars && bars.classList.contains('fullscreen')) {
      var scroller = cm.getScrollerElement();
      if (PREFS.typewriter && mde.isFullscreenActive() && innerWidth >= 640) {
        cm.scrollTo(null, Math.max(0, (at.top + at.bottom) / 2 - scroller.clientHeight / 2));
      } else {
        cm.scrollTo(null, Math.max(0, cm.getScrollInfo().top + cm.charCoords({ line: line, ch: 0 }, 'window').top -
                                      bars.getBoundingClientRect().bottom - 24));
      }
    }
    // the page too, where the text isn't in a box of its own - to the same
    // place under the bars each time: left where it was when the heading
    // was anywhere in view, a section near the bottom of the window stayed
    // there, its own lines out of sight below
    // And again once the lines there are drawn: until then the editor
    // only guesses how tall the text above is, and the further down the
    // section, the further out the guess - the last one landed worst.
    var bar = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--header-h')) || 0;
    var land = function (again) {
      var by = cm.charCoords({ line: line, ch: 0 }, 'window').top - bar - 120;
      if (Math.abs(by) > 1) scrollBy({ top: by, behavior: 'instant' });
      if (again) requestAnimationFrame(function () { land(again - 1); });
    };
    land(3);
    // a short flash on the line - none with Reduce motion
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    if (flashed) { clearTimeout(flashed.timer); cm.removeLineClass(flashed.handle, 'background', 'bg-primary/25'); }
    var handle = cm.addLineClass(line, 'background', 'bg-primary/25');
    flashed = { handle: handle, timer: setTimeout(function () {
      cm.removeLineClass(handle, 'background', 'bg-primary/25');
      flashed = null;
    }, 1200) };
  };
  // "Post:" or "Page:" before its name, and the pills under it - the
  // template a new post starts from, pinned and who can read it
  // (EditorPills, routes/editor.py); the row's gone when there are none
  var pillsEl = document.getElementById('post-pills');
  if (pillsEl) {
    var pill = function (text, cls) {
      var p = document.createElement('span');
      p.className = 'badge badge-sm ' + (cls || 'badge-outline') + ' whitespace-nowrap';
      p.textContent = text;
      return p;
    };
    var syncPills = function () {
      var f = form.elements, where = f.pin_location ? f.pin_location.value : '';
      var access = f.visibility ? f.visibility.value : 'public';
      var kind = document.querySelector('[data-post-kind]');
      // the homepage stays a page, in the menu or not
      if (kind) kind.textContent = (kind.hasAttribute('data-home') || where === 'header' || where === 'footer' ? 'Page' : 'Post') + ':';
      var out = [];
      var start = pillsEl.querySelector('[data-template-name]');
      if (start) out.push(start.closest('.tooltip'));
      if (where === 'top') out.push(pill('Pinned'));
      if (access === 'paid') out.push(pill('Paid members', 'badge-primary'));
      else if (access === 'members') out.push(pill('Members', 'badge-primary badge-soft'));
      if (f.post_password && f.post_password.value) out.push(pill('Password'));
      pillsEl.replaceChildren.apply(pillsEl, out);
      pillsEl.hidden = !out.length;
    };
    syncPills();
    // Unlisted on a page in the menu or footer: a line under the switch
    // says it's still there for anyone (UNLISTED_NOTE, routes/editor.py)
    var note = document.getElementById('unlisted-note');
    var syncUnlisted = function () {
      if (!note || !form.elements.unlisted) return;
      var where = form.elements.pin_location ? form.elements.pin_location.value : '';
      var pinned = !form.elements.pinned || form.elements.pinned.checked;
      var shown = form.elements.unlisted.checked && pinned && (where === 'header' || where === 'footer');
      note.hidden = !shown;
      if (shown) note.textContent = note.textContent.replace(/the (menu|footer)/, 'the ' + (where === 'footer' ? 'footer' : 'menu'));
    };
    form.addEventListener('change', syncUnlisted);
    form.addEventListener('change', syncPills);
    form.addEventListener('reset', function () { setTimeout(syncPills); });
  }
  // only the post's own fields - not a search that isn't part of it (form="no-form")
  form.addEventListener('input', function (e) { if (e.target.form === form) markDirty(); });
  form.addEventListener('submit', function () { dirty = false; });
  // EasyMDE keeps what's typed in its own buffer, not the #body-editor
  // textarea the form sends - so it's copied in just before the request
  // is built (htmx:configRequest)
  form.addEventListener('htmx:configRequest', function (e) {
    // saves only - a GET from inside the form (History > Compare) would
    // carry the whole post in its address
    if (e.detail.verb !== 'get') e.detail.parameters.body = mde.value();
  });
  // discardForm() (app.py) calls this after a Cancel - resyncing
  // EasyMDE's value programmatically fires the same 'change' event a
  // real edit would, which would otherwise re-flip dirty back to true
  // and stomp "Discarded" with "Unsaved changes" moments later.
  window._clearFormDirty = function () { dirty = false; clearDraft(); updateStatus(); };
  // a save's answer replaces #save-status: green is saved, red isn't -
  // read once htmx has settled it (until then it wears the old classes)
  document.addEventListener('htmx:afterSettle', function (e) {
    var s = document.getElementById('save-status');
    if (!e.detail.target || e.detail.target.id !== 'save-status' || !s || !s.textContent) return;
    if (s.classList.contains('text-success') && !dirty) { lastSaved = Date.now(); saveFailed = false; }
    // not saved, so still unsaved: leaving asks again (submit cleared it)
    else if (s.classList.contains('text-error')) { saveFailed = true; dirty = true; }
    updateStatus();
  });
  setInterval(updateStatus, 30000);
  updateStatus();

  // autosave: while the form is dirty, a snapshot of every field is kept
  // in this browser's localStorage a moment after each change (never on
  // the server - a post's file is what visitors read, and a half-typed
  // edit silently going live is worse than losing it). Reopening the
  // page offers to restore it; a real Save or Cancel throws it away.
  // Every storage call is wrapped, since localStorage can throw (private
  // windows, blocked site data) and the editor must work without it.
  var prefs = window.EDITOR_PREFS || {};
  // keyed by the post's row id, not its slug - a rename keeps the id,
  // so the draft still finds its post
  var draftKey = 'soloblog-draft:' + (form.dataset.draftKey || 'new');
  var autosaveTimer = null;

  function snapshot() {
    var data = {};
    [].forEach.call(form.elements, function (f) {
      if (!f.name || f.name === 'body' || f.disabled) return;
      data[f.name] = (f.type === 'checkbox' || f.type === 'radio') ? f.checked : f.value;
    });
    data.body = mde.value();
    return data;
  }
  function clearDraft() {
    clearTimeout(autosaveTimer);
    try { localStorage.removeItem(draftKey); } catch (err) {}
  }
  function saveDraft() {
    if (!dirty) return;
    var data = snapshot();
    if (draftKey.slice(-4) === ':new' && !data.title && !data.body) { clearDraft(); return; }
    try {
      localStorage.setItem(draftKey, JSON.stringify({ saved: Date.now(), data: data }));
    } catch (err) { return; }
    var status = document.getElementById('save-status');
    // an Undo beside it (Apply a template) stays until the next edit
    if (status && dirty && !status.querySelector('button')) status.textContent = 'Unsaved';
  }
  function scheduleAutosave() {
    if (!prefs.autosave) return;
    clearTimeout(autosaveTimer);
    autosaveTimer = setTimeout(saveDraft, 1500);
  }
  mde.codemirror.on('change', scheduleAutosave);
  form.addEventListener('input', scheduleAutosave);
  // a Save the server accepted makes the draft redundant. afterRequest
  // on the form, not afterSwap on the status span: a brand-new post's
  // first save answers with an HX-Redirect and never swaps anything, so
  // the swap-based signal would leave its draft behind to be offered
  // back on the next New post page. The HTTP status, not htmx's own
  // detail.successful flag: htmx leaves that undefined on exactly that
  // HX-Redirect response.
  form.addEventListener('htmx:afterRequest', function (e) {
    var status = e.detail.xhr ? e.detail.xhr.status : 0;
    if (e.target === form && status >= 200 && status < 300) clearDraft();
  });

  function restoreDraft(data) {
    Object.keys(data).forEach(function (name) {
      if (name === 'body') { mde.value(data.body); return; }
      var field = form.elements[name];
      if (!field || !field.tagName) return;
      if (field.type === 'checkbox' || field.type === 'radio') field.checked = !!data[name]; else field.value = data[name];
    });
    var pin = document.getElementById('pin_location');
    if (pin && typeof updateParentField === 'function') updateParentField(pin.value);
  }
  if (prefs.autosave) {
    var stored = null;
    try { stored = JSON.parse(localStorage.getItem(draftKey) || 'null'); } catch (err) {}
    if (stored && stored.data && JSON.stringify(stored.data) !== JSON.stringify(snapshot())) {
      var banner = document.createElement('div');
      banner.setAttribute('role', 'alert');
      // stacked on a phone - side by side, the message was squeezed to a word a line
      banner.className = 'alert alert-warning alert-vertical sm:alert-horizontal mb-4 text-sm';
      var msg = document.createElement('span');
      msg.textContent = 'You have unsaved changes from ' + new Date(stored.saved).toLocaleString() + '.';
      var actions = document.createElement('div');
      actions.className = 'flex gap-2';
      var restore = document.createElement('button');
      restore.type = 'button'; restore.className = 'btn btn-sm'; restore.textContent = 'Restore them';
      restore.onclick = function () { restoreDraft(stored.data); banner.remove(); };
      var discard = document.createElement('button');
      discard.type = 'button'; discard.className = 'btn btn-sm btn-ghost'; discard.textContent = 'Discard';
      discard.onclick = function () { clearDraft(); banner.remove(); };
      actions.appendChild(restore); actions.appendChild(discard);
      banner.appendChild(msg); banner.appendChild(actions);
      form.parentNode.insertBefore(banner, form);
    }
  }
  // for the site's own leave-without-saving dialog (unsavedChanges, app.py)
  window.editorDirty = function () { return dirty; };
  window.addEventListener('beforeunload', function (e) {
    if (!dirty || window._leaving) return;
    e.preventDefault();
    e.returnValue = '';
  });

  // Ctrl+S saves - anywhere on the page, not just in the text (the
  // browser would save the web page); Ctrl+/ opens the help; Esc leaves
  // preview, as it already leaves full screen
  document.addEventListener('keydown', function (e) {
    var mod = (e.ctrlKey || e.metaKey) && !e.altKey;
    if (mod && !e.shiftKey && (e.key === 's' || e.key === 'S')) {
      e.preventDefault();
      form.requestSubmit();
    } else if (mod && e.key === '/') {
      e.preventDefault();
      toggleEditorHelp();
    } else if (e.key === 'Escape' && !document.querySelector('dialog[open]') && mde.isPreviewActive()) {
      EasyMDE.togglePreview(mde);
      mde.codemirror.focus();
    }
  }, true);

  // The bar over the text (PostForm, #editor-bar): the save state as a
  // dot, its words the dot's tooltip (and beside it when something went
  // wrong, input.css). It sticks under the header, the toolbar under it.
  var toolbar = mde.gui.toolbar, bar = document.getElementById('editor-bar');
  // Go to and Insert at the toolbar's right end, their divider and a
  // space setting them apart (important: the toolbar's parts start from all: unset)
  var goToBtn = toolbar ? toolbar.querySelector(':scope > button.goto') : null;
  var insertBtn = toolbar && PREFS.rows === 'one' ? toolbar.querySelector(':scope > button.insert') : null;
  var insertGap = goToBtn && goToBtn.previousElementSibling;
  if (insertGap) insertGap.classList.add('ms-auto!');
  if (goToBtn) {
    goToBtn.setAttribute('aria-haspopup', 'listbox');
    goToBtn.setAttribute('aria-expanded', 'false');
  }
  if (bar) {
    var dot = bar.querySelector('[data-save-dot]'), slot = bar.querySelector('[data-save-slot]');
    var syncDot = function () {
      var s = document.getElementById('save-status'), text = s ? s.textContent.trim() : '', kind = '';
      // whole class names - Tailwind only builds what it can read
      if (s && s.classList.contains('text-error')) kind = 'status-error';
      else if (s && s.classList.contains('text-warning')) kind = 'status-warning';
      else if (s && s.classList.contains('text-success')) kind = 'status-success';
      if (!text) {
        text = form.dataset.draftKey === 'new' ? 'Not saved yet' : 'Saved';
        kind = form.dataset.draftKey === 'new' ? '' : 'status-success';
      }
      dot.className = 'status status-md ' + kind;
      dot.parentNode.dataset.tip = text;
      dot.setAttribute('aria-label', text);
    };
    syncDot();
    // #save-status is swapped whole by each save, so its box is watched
    new MutationObserver(syncDot).observe(slot, { childList: true, subtree: true, characterData: true,
                                                   attributes: true, attributeFilter: ['class'] });
  }
  // how tall the bar and toolbar are, for what sticks under them and for
  // focus mode (a hidden toolbar - a phone, Minimal - is 0)
  if (window.ResizeObserver) {
    if (bar) new ResizeObserver(function () { form.style.setProperty('--editor-bar-h', bar.offsetHeight + 'px'); }).observe(bar);
    if (toolbar) {
      new ResizeObserver(function () {
        form.style.setProperty('--editor-toolbar-h', toolbar.offsetHeight + 'px');
        fitToolbar();
      }).observe(toolbar);
    }
  }
  // Stuck under the header, the bar takes the page's background (and a
  // line under it when there's no toolbar there), the toolbar square
  // corners - round ones showed the text through them
  var markStuck = function () {
    [bar, toolbar].forEach(function (el) {
      if (!el) return;
      var top = parseFloat(getComputedStyle(el).top);
      el.toggleAttribute('data-stuck', getComputedStyle(el).position === 'sticky' && !isNaN(top) &&
                                       window.scrollY > 0 && el.getBoundingClientRect().top <= top + 1);
    });
    if (bar) bar.toggleAttribute('data-lone', !toolbar || !toolbar.offsetHeight);
  };
  window.addEventListener('scroll', markStuck, { passive: true });
  markStuck();
  // One row: the buttons that don't fit fold into ⋯, which is only there
  // when some don't - as Google Docs does - whatever the width
  function fitToolbar() {
    var more = toolbar && [].filter.call(toolbar.children, function (el) { return el.classList.contains('more'); })[0];
    if (!more || !toolbar.offsetWidth) return;
    var menu = more.querySelector('.easymde-dropdown-content');
    var items = [].filter.call(toolbar.children, function (el) { return el !== more; });
    items.forEach(function (el) { el.hidden = false; });
    [].forEach.call(menu.children, function (b) { b.hidden = true; });
    more.hidden = true;
    var edge = function () {
      return toolbar.getBoundingClientRect().right - parseFloat(getComputedStyle(toolbar).paddingRight) + 0.5;
    };
    if (!items.length || items[items.length - 1].getBoundingClientRect().right <= edge()) return;
    more.hidden = false;
    var showCopy = function (name) {
      var copy = menu.querySelector('.' + name + '-more');
      if (copy) copy.hidden = false;
    };
    for (var i = items.length - 1; i > 0 && more.getBoundingClientRect().right > edge(); i--) {
      if (items[i] === insertBtn || items[i] === goToBtn || items[i] === insertGap) continue;  // always there
      items[i].hidden = true;
      if (items[i].tagName !== 'BUTTON') continue;
      // a section's ▾ that doesn't fit: what was in it goes under ⋯
      if (items[i].hasAttribute('data-rest')) {
        [].forEach.call(items[i].querySelector('.easymde-dropdown-content').children,
                        function (b) { showCopy(b.classList[0]); });
      } else showCopy(items[i].classList[0]);
    }
    // no two dividers together - Insert's is the one kept - and none
    // left hanging at the end
    var lastSep = null;
    items.forEach(function (el) {
      if (el.hidden) return;
      if (el.classList.contains('separator')) { if (lastSep) lastSep.hidden = true; lastSep = el; } else lastSep = null;
    });
    for (i = items.length - 1; i >= 0; i--) {
      if (items[i].hidden) continue;
      if (items[i].classList.contains('separator')) items[i].hidden = true; else break;
    }
  }
  fitToolbar();
  window.addEventListener('load', fitToolbar);
  if (document.fonts) document.fonts.ready.then(fitToolbar);

  // Focus mode - EasyMDE's full screen with a bar of its own: a way out,
  // the post's title, its words, and the browser's own full screen. The
  // formatting toolbar fades while you type (Save stays) and comes back
  // when the mouse moves or text is selected, as in iA Writer.
  if (toolbar) {
    var box = toolbar.parentNode, icons = PREFS.icons || {};
    // Focus mode's "typing": on the box and on the form (input.css hides
    // the bars by it), set only when it changes - a :has() reading it off
    // the box restyled the whole page on every key
    var postForm = document.getElementById('post-form');
    var setTyping = function (on) {
      if (box.hasAttribute('data-typing') === on) return;
      box.toggleAttribute('data-typing', on);
      if (postForm) postForm.toggleAttribute('data-typing', on);
      if (showBars) showBars.hidden = !on;
    };
    // On a phone there's no mouse to bring the bars back once they've gone
    // quiet: a small arrow at the top says they can come back, and does it.
    // The text keeps its focus as it is, so the keyboard doesn't open.
    var showBars = document.createElement('button');
    showBars.type = 'button';
    showBars.hidden = true;
    showBars.className = 'btn btn-ghost btn-circle btn-sm sm:hidden fixed top-[max(0.5rem,env(safe-area-inset-top))] ' +
                         'left-1/2 -translate-x-1/2 z-[39] tooltip tooltip-bottom';
    showBars.dataset.tip = 'Show the toolbar';
    showBars.setAttribute('aria-label', 'Show the toolbar');
    showBars.innerHTML = icons['chevron-down'];
    showBars.addEventListener('pointerdown', function (e) { e.preventDefault(); });
    showBars.addEventListener('click', function () { setTyping(false); });
    box.appendChild(showBars);
    var iconButton = function (icon, tip, run) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'btn btn-sm btn-ghost btn-square tooltip tooltip-bottom';
      // its words, shown once it's folded into ⋯ (fitFocusBar)
      b.innerHTML = icon + '<span class="hidden [[data-row-menu]_&]:inline ml-1">' + tip.split(' · ')[0] + '</span>';
      b.dataset.tip = tip;
      b.setAttribute('aria-label', tip);
      b.addEventListener('click', run);
      return b;
    };
    var focusBar = document.createElement('div');
    focusBar.className = 'editor-focusbar';
    var leave = iconButton(icons.x, 'Leave Focus · Esc', function () {
      if (mde.isFullscreenActive()) EasyMDE.toggleFullScreen(mde);
    });
    var focusTitle = document.createElement('span');
    focusTitle.className = 'editor-focus-title truncate';
    focusWords = document.createElement('span');
    focusWords.className = 'editor-focus-words';
    var browserBars = iconButton(icons.expand, 'Fullscreen', function () {
      if (document.fullscreenElement) document.exitFullscreen();
      else document.documentElement.requestFullscreen().catch(function () {});
    });
    browserBars.hidden = !document.fullscreenEnabled;
    document.addEventListener('fullscreenchange', function () {
      var on = !!document.fullscreenElement, tip = on ? 'Exit fullscreen' : 'Fullscreen';
      browserBars.innerHTML = on ? icons.shrink : icons.expand;
      browserBars.dataset.tip = tip;
      browserBars.setAttribute('aria-label', tip);
    });
    // the counts and a session's progress, centred on the bar - wherever
    // they're shown (not on a phone: input.css)
    var focusMiddle = document.createElement('div');
    focusMiddle.className = 'flex items-center gap-3 sm:absolute sm:left-1/2 sm:-translate-x-1/2 ' +
                            'data-[flow]:static data-[flow]:translate-x-0';
    focusMiddle.appendChild(focusWords);
    var focusTools = document.createElement('div'), toolFolds = null;
    focusTools.className = 'contents';
    focusBar.append(leave, focusTitle, focusMiddle, focusTools);
    focusTools.appendChild(browserBars);
    // Focus is one bar at every width - its own and the one over the text
    // (mergeBars). Where it's short of room, in this order: the counts leave
    // the very middle; on a phone full screen, then A- and A+, then the timer
    // fold into ⋯; the views become their icons; the counts become just the
    // words; and only then do the counts go
    // The post's buttons beside Save, as many as fit - the rest in ⋯, which
    // only shows then
    var actRow = document.querySelector('[data-actions-row]'), actMenu = document.getElementById('editor-actions');
    var actMore = document.querySelector('[data-actions-more]');
    var actOrder = actRow ? [].slice.call(actRow.children) : [];
    var syncMore = function () { if (actMore && actMenu) actMore.hidden = !actMenu.children.length; };
    var unfoldActions = function () {
      actOrder.forEach(function (el) { actRow.appendChild(el); });
      syncMore();
    };
    // Discard and View go into ⋯ first (data-fold-first) - Settings and
    // Help are reached for more - then the rest, the last ones first; in
    // ⋯ they keep the bar's order
    var foldOrder = actOrder.filter(function (el) { return !el.hasAttribute('data-fold-first'); })
      .concat(actOrder.filter(function (el) { return el.hasAttribute('data-fold-first'); }));
    var foldOneAction = function () {
      for (var i = foldOrder.length - 1; i >= 0; i--) {
        if (foldOrder[i].parentNode === actRow && !foldOrder[i].hidden) {
          actMenu.appendChild(foldOrder[i]);
          actOrder.forEach(function (el) { if (el.parentNode === actMenu) actMenu.appendChild(el); });
          syncMore();
          return true;
        }
      }
      return false;
    };
    var fitEditorBar = function () {
      if (!actRow || !actMenu || !bar || merged) return;
      unfoldActions();
      while (bar.scrollWidth > bar.clientWidth + 1 && foldOneAction()) { /* the next one */ }
    };
    // only when it's narrower or wider: a phone's keyboard makes the window
    // shorter, and a refit moved the timer in ⋯, closing it as you typed
    var onWidth = function (fit) {
      var w = window.innerWidth;
      window.addEventListener('resize', function () { if (window.innerWidth !== w) { w = window.innerWidth; fit(); } });
    };
    onWidth(fitEditorBar);
    setTimeout(fitEditorBar);
    var phoneWidth = matchMedia('(width < 40rem)');
    var fitFocusBar = function () {
      if (!toolFolds) return;
      var tabsBox = focusBar.querySelector('.editor-tabs') || document.querySelector('.editor-tabs');
      toolFolds.slice().reverse().forEach(function (group) { group.forEach(function (el) { focusTools.appendChild(el); }); });
      if (tabsBox) tabsBox.removeAttribute('data-icons');
      focusWords.removeAttribute('data-short');
      focusMiddle.removeAttribute('data-flow');
      focusMiddle.hidden = false;
      updateStatus();
      if (actRow) unfoldActions();
      if (!merged) { fitEditorBar(); return; }
      var menu = document.getElementById('editor-actions');
      var tight = function () {
        if (focusBar.scrollWidth > focusBar.clientWidth + 1) return true;
        var m = focusMiddle.getBoundingClientRect();
        if (focusMiddle.hidden || !m.width) return false;
        return [].slice.call(focusBar.children).concat([].slice.call(focusTools.children)).some(function (el) {
          if (el === focusMiddle || el === focusTitle || el === focusTools) return false;
          var r = el.getBoundingClientRect();
          return r.width && r.left < m.right + 8 && r.right > m.left - 8;
        });
      };
      var steps = [function () { focusMiddle.setAttribute('data-flow', ''); }];
      if (phoneWidth.matches && menu) {
        toolFolds.forEach(function (group) {
          steps.push(function () { group.forEach(function (el) { menu.appendChild(el); }); });
        });
      }
      // then the post's buttons, one at a time, the last first
      if (phoneWidth.matches && actRow) actOrder.forEach(function () { steps.push(foldOneAction); });
      steps.push(function () { if (tabsBox) tabsBox.setAttribute('data-icons', ''); });
      steps.push(function () { focusWords.setAttribute('data-short', ''); updateStatus(); });
      steps.push(function () { focusMiddle.hidden = true; });
      for (var i = 0; i < steps.length && tight(); i++) steps[i]();
      syncMore();
    };
    box.insertBefore(focusBar, toolbar);
    // while the bars are away (While you type > Only your words), the save
    // state stays as a dot in the corner - the bar's own dot, mirrored
    var focusDot = document.createElement('span');
    focusDot.className = 'editor-focus-dot fixed top-3 right-3 z-[39]';
    focusDot.setAttribute('aria-hidden', 'true');
    box.appendChild(focusDot);
    var barDot = bar && bar.querySelector('[data-save-dot]');
    if (barDot) {
      var mirrorDot = function () { focusDot.className = barDot.className + ' editor-focus-dot fixed top-3 right-3 z-[39]'; };
      new MutationObserver(mirrorDot).observe(barDot, { attributes: true, attributeFilter: ['class'] });
      mirrorDot();
    }
    // Focus mode's bars > One bar (Settings > Editor > Writing), where it's
    // wide enough: the bar over the text joins Focus mode's own - the
    // views by the way out; the save dot, the post's buttons and Save at
    // its end - and goes back on the way out (focus-one-bar)
    var views = document.getElementById('editor-views'), merged = false;
    var mergeBars = function () {
      var want = PREFS.focusBars === 'one' && mde.isFullscreenActive() && !!bar;
      if (want === merged) return fitFocusBar();
      merged = want;
      var from = want ? bar : focusBar, to = want ? focusBar : bar;
      var tabsEl = (want ? views : focusBar).querySelector('.editor-tabs');
      // the ⋯ whole - its button and its menu (RowActions) - not the menu
      // alone: the button left behind sat by the views once the bars parted
      var actions = document.getElementById('editor-actions');
      var moving = [from.querySelector('.editor-status'), actions && actions.parentElement,
                    from.querySelector(':scope > button[type=submit]')];
      // the views on the left, by the way out - the space between pushes the rest right
      if (tabsEl) { if (want) focusTitle.before(tabsEl); else views.appendChild(tabsEl); }
      moving.forEach(function (el) { if (el) to.appendChild(el); });
      document.documentElement.toggleAttribute('data-focus-one-bar', want);
      fitFocusBar();
    };
    onWidth(mergeBars);
    // the title: a heading at the top of the writing you type into - the
    // post's own title field, the two kept in step - not again in the bar
    // (focusTitle stays there, empty, to keep its buttons at the right)
    var titleField = form.querySelector('input[name=title]'), heading = null, headingAt = null;
    var cmFocus = mde.codemirror;
    if (titleField) {
      heading = document.createElement('input');
      heading.type = 'text';
      heading.placeholder = 'Title';
      heading.setAttribute('aria-label', 'Title');
      heading.className = 'w-full pointer-coarse:min-h-11 bg-transparent border-0 outline-none p-0 ps-0.75 mb-4 text-2xl sm:text-3xl font-bold ' +
                          'leading-tight placeholder:text-base-content/50 ' + SCROLLS_X;
      // a title longer than the line fades at the side it goes on (live.js)
      heading.setAttribute('data-scroll-x', '');
      var titleEdges = function () { if (typeof _scrollHintX === 'function') _scrollHintX(heading); };
      ['input', 'keyup', 'click', 'focus', 'select'].forEach(function (ev) { heading.addEventListener(ev, titleEdges); });
      // leaving it puts the start of the title back in view
      heading.addEventListener('blur', function () { setTimeout(titleEdges); });
      // the heading sits inside the writing's editable area: its typing and
      // composing events stay with it, or the writing reads them too and
      // fast typing dropped characters
      ['keypress', 'beforeinput', 'input', 'compositionstart', 'compositionupdate', 'compositionend', 'paste', 'cut', 'copy']
        .forEach(function (ev) { heading.addEventListener(ev, function (e) { e.stopPropagation(); }); });
      heading.addEventListener('input', function () {
        titleField.value = heading.value;
        titleField.dispatchEvent(new Event('input', { bubbles: true }));
      });
      mde.titleInput = heading;
      // Enter: on to the writing, as in a title anywhere else; so is Tab,
      // and Shift+Tab goes back to the bar (the box's own order would put it
      // in the writing first)
      heading.addEventListener('keydown', function (e) {
        // Enter confirms a word being composed (Chinese, Japanese, Korean)
        if (e.isComposing || e.keyCode === 229) return;
        if (e.key === 'Tab' && e.shiftKey && !e.ctrlKey && !e.metaKey && !e.altKey) {
          var back = mde.tabBeside(false);
          if (back) { e.preventDefault(); back.focus(); }
          return;
        }
        if (e.key !== 'Enter' && e.key !== 'ArrowDown' && !(e.key === 'Tab' && !e.shiftKey)) return;
        e.preventDefault();
        cmFocus.focus();
        cmFocus.setCursor({ line: 0, ch: 0 });
      });
      titleField.addEventListener('input', function (e) {
        // not while it's the same: setting the value cancels a word being
        // composed and moves the caret, and fast typing lost characters
        if (e.target !== heading && heading.value !== titleField.value) heading.value = titleField.value;
        document.querySelectorAll('[data-preview-title]').forEach(function (h) {
          h.textContent = titleField.value;
          h.hidden = !titleField.value.trim();
        });
      });
      // at full strength while you type in it - the fade (input.css,
      // focus-fade) follows the writing's cursor, which is elsewhere
      var fade = '';
      heading.addEventListener('focus', function () { fade = form.dataset.fade || ''; delete form.dataset.fade; });
      heading.addEventListener('blur', function () { if (fade) form.dataset.fade = fade; });
    }
    // above the first line - put back there if that line goes (all of it deleted)
    var placeHeading = function () {
      if (!heading) return;
      if (headingAt && headingAt.line && cmFocus.getLineNumber(headingAt.line) === 0) return;
      if (headingAt) headingAt.clear();
      heading.value = titleField.value;
      headingAt = cmFocus.addLineWidget(0, heading, { above: true });
      // an empty post's grey hint goes under it, not over it
      var wrap = cmFocus.getWrapperElement();
      wrap.classList.add('[&_.CodeMirror-placeholder]:top-(--title-h)!');  // moved down, not pushing the heading
      wrap.style.setProperty('--title-h', (heading.offsetHeight + parseFloat(getComputedStyle(heading).marginBottom)) + 'px');
    };
    cmFocus.on('changes', placeHeading);
    placeHeading();  // in Write and in Focus alike - there's no other title box
    if (heading) requestAnimationFrame(function () { if (typeof _scrollHintX === 'function') _scrollHintX(heading); });
    var showTitle = placeHeading;
    // however it's entered or left - the button, the keys, Esc
    new MutationObserver(function () {
      document.documentElement.toggleAttribute('data-focus-mode', toolbar.classList.contains('fullscreen'));
      mergeBars();
      line.hidden = !toolbar.classList.contains('fullscreen');
      if (toolbar.classList.contains('fullscreen')) { showTitle(); updateStatus(); return; }
      setTyping(false);
      if (document.fullscreenElement) document.exitFullscreen();
    }).observe(toolbar, { attributes: true, attributeFilter: ['class'] });
    // Focus mode, as iA Writer has it (Settings > Editor > Writing):
    // typewriter scrolling keeps the line you're on in the middle of the
    // screen (not on a phone, where the keyboard has the bottom half), and
    // the paragraph you're in - the lines between blank ones - stays at
    // full strength while the rest fades (input.css, focus-fade)
    var lit = [], focusText = mde.codemirror, small = matchMedia('(width < 40rem)');
    var paragraph = function () {
      var line = focusText.getCursor().line, first = line, last = line;
      if (focusText.getLine(line).trim()) {
        while (first > 0 && focusText.getLine(first - 1).trim()) first--;
        while (last < focusText.lastLine() && focusText.getLine(last + 1).trim()) last++;
      }
      return [first, last];
    };
    // the sentence you're in, within its paragraph: from just after the
    // last . ! ? (and any closing quote or bracket) before the cursor, to
    // just after the next one
    var sentence = function (p) {
      var from = { line: p[0], ch: 0 }, to = { line: p[1], ch: focusText.getLine(p[1]).length };
      var text = focusText.getRange(from, to), base = focusText.indexFromPos(from);
      var at = focusText.indexFromPos(focusText.getCursor()) - base, start = 0, end = text.length, m;
      var stop = /[.!?…]+["'”’)\]]*(\s+|$)/g;
      while ((m = stop.exec(text))) {
        if (m.index + m[0].length <= at) start = m.index + m[0].length;
        else { end = m.index + m[0].length; break; }
      }
      return [focusText.posFromIndex(base + start), focusText.posFromIndex(base + end)];
    };
    var dims = [];
    var lightParagraph = function () {
      focusText.operation(function () {
        lit.forEach(function (handle) { focusText.removeLineClass(handle, 'wrap', 'cm-para-now'); });
        dims.forEach(function (mark) { mark.clear(); });
        lit = [];
        dims = [];
        if (PREFS.fade === 'off' || !mde.isFullscreenActive()) return;
        var p = paragraph();
        if (PREFS.fade === 'sentence') {
          // everything but the sentence steps back - marks, since part of a
          // line can't be lit (focus-fade)
          var s = sentence(p), last = focusText.lastLine();
          dims.push(focusText.markText({ line: 0, ch: 0 }, s[0], { className: 'cm-dim' }));
          dims.push(focusText.markText(s[1], { line: last, ch: focusText.getLine(last).length }, { className: 'cm-dim' }));
          return;
        }
        for (var n = p[0]; n <= p[1]; n++) lit.push(focusText.addLineClass(n, 'wrap', 'cm-para-now'));
      });
    };
    // the page glides to the new line, rather than jumping a line at a time
    var glide = 0, still = matchMedia('(prefers-reduced-motion: reduce)');
    var centre = function () {
      if (!PREFS.typewriter || !mde.isFullscreenActive() || small.matches) return;
      var at = focusText.cursorCoords(null, 'local'), scroller = focusText.getScrollerElement();
      var to = Math.max(0, (at.top + at.bottom) / 2 - scroller.clientHeight / 2), from = scroller.scrollTop;
      cancelAnimationFrame(glide);
      if (still.matches || Math.abs(to - from) < 2 || Math.abs(to - from) > scroller.clientHeight) {
        focusText.scrollTo(null, to);
        return;
      }
      var start = performance.now();
      var step = function (now) {
        var t = Math.min(1, (now - start) / 180);
        focusText.scrollTo(null, from + (to - from) * (1 - Math.pow(1 - t, 3)));  // eases out
        if (t < 1) glide = requestAnimationFrame(step);
      };
      glide = requestAnimationFrame(step);
    };
    // only the keyboard's moves recentre: a click or a drag with the mouse
    // leaves the text where it is - recentring under the pointer as it
    // moved made selecting with a mouse almost impossible - and so does a
    // selection, until you're typing again
    var byMouse = false;
    focusText.on('mousedown', function () { byMouse = true; });
    focusText.on('touchstart', function () { byMouse = true; });
    focusText.on('keydown', function () { byMouse = false; });
    focusText.on('cursorActivity', function () {
      lightParagraph();
      if (!byMouse && !focusText.somethingSelected()) centre();
    });
    new MutationObserver(function () {
      lightParagraph();
      setTimeout(centre, 50);  // once the text has its full-screen size
      // a slower blink in Focus mode (and a softer caret - focus-caret)
      focusText.setOption('cursorBlinkRate', mde.isFullscreenActive() ? 800 : 530);
    }).observe(toolbar, { attributes: true, attributeFilter: ['class'] });
    // Text size, in Focus mode only: A- and A+ in its bar step the writing
    // down or up, remembered in this browser (focus-text-size)
    var SIZES = [0.9, 1, 1.1, 1.25, 1.4, 1.6], sizeAt = 1;
    try { sizeAt = Math.max(0, Math.min(SIZES.length - 1, parseInt(localStorage.getItem('focus-text-size'), 10))); }
    catch (err) {}
    if (isNaN(sizeAt)) sizeAt = 1;
    var smaller, larger, sizeReset;
    var setSize = function (at) {
      sizeAt = Math.max(0, Math.min(SIZES.length - 1, at));
      form.style.setProperty('--focus-scale', SIZES[sizeAt]);
      smaller.disabled = sizeAt === 0;
      larger.disabled = sizeAt === SIZES.length - 1;
      sizeReset.hidden = SIZES[sizeAt] === 1;
      sizeReset.textContent = Math.round(SIZES[sizeAt] * 100) + '%';
      try { localStorage.setItem('focus-text-size', sizeAt); } catch (err) {}
      focusText.refresh();
      centre();
    };
    smaller = iconButton(icons['a-arrow-down'], 'Smaller text', function () { setSize(sizeAt - 1); });
    larger = iconButton(icons['a-arrow-up'], 'Larger text', function () { setSize(sizeAt + 1); });
    // the size it's at, between the two - a click puts it back to the post's own
    sizeReset = document.createElement('button');
    sizeReset.type = 'button';
    sizeReset.className = 'btn btn-sm btn-ghost px-1 tabular-nums tooltip tooltip-bottom';
    sizeReset.dataset.tip = 'Reset text size';
    sizeReset.setAttribute('aria-label', 'Reset text size');
    sizeReset.addEventListener('click', function () { setSize(SIZES.indexOf(1)); });

    // Writing sessions: from Focus mode's bar, a stretch of time or a
    // number of words. A hair-thin line along the top of the bar fills as
    // you go, the bar says what's left, and it ends with "Session done".
    // Kept for this tab (sessionStorage), so a reload carries on.
    var SESSIONS = [['time', 25, '25 minutes'], ['time', 50, '50 minutes'], ['words', 500, '500 words'],
                    ['words', 1000, '1,000 words']];
    var session = null, sessionKey = 'focus-session:' + (form.dataset.draftKey || 'new'), wordsNow = 0;
    try { session = JSON.parse(sessionStorage.getItem(sessionKey) || 'null'); } catch (err) {}
    var line = document.createElement('div');
    line.className = 'editor-session-line fixed left-0 top-0 z-[39] h-0.5 bg-primary transition-[width] duration-700 ease-out';
    line.setAttribute('aria-hidden', 'true');
    line.hidden = true;
    var keep = function () {
      try {
        if (session) sessionStorage.setItem(sessionKey, JSON.stringify(session));
        else sessionStorage.removeItem(sessionKey);
      } catch (err) {}
    };
    var sessionText = document.createElement('span');
    sessionText.className = 'editor-focus-words';
    sessionTick = function (n) {
      if (typeof n === 'number') wordsNow = n;
      if (!session) {
        line.style.width = '0';
        line.classList.remove('bg-base-content/30', 'bg-success');
        line.classList.add('bg-primary');
        sessionText.textContent = '';
        sessionText.classList.remove('text-success');
        return;
      }
      var added = Math.max(0, wordsNow - session.startWords), part;
      // reached: a quiet moment that stays - the line full in the palette's
      // success colour, and the words still counting - until you end it
      // or start another
      if (session.done) {
        line.style.width = '100%';
        line.classList.remove('bg-primary', 'bg-base-content/30');
        line.classList.add('bg-success');
        sessionText.textContent = 'Goal reached · ' + (session.kind === 'time'
          ? session.target + ' min · +' + added.toLocaleString() + (added === 1 ? ' word' : ' words')
          : added.toLocaleString() + (added === 1 ? ' word' : ' words'));
        sessionText.classList.add('text-success');
        return;
      }
      sessionText.classList.remove('text-success');
      if (session.kind === 'time') {
        // the time it's been running - a pause (since pausedAt, and the
        // ones before, pausedFor) doesn't count
        var ran = (session.pausedAt || Date.now()) - session.started - (session.pausedFor || 0);
        var left = session.target * 60000 - ran;
        part = 1 - left / (session.target * 60000);
        sessionText.textContent = (session.pausedAt ? 'Paused · ' : '') + Math.max(1, Math.ceil(left / 60000)) +
                                  ' min left';
      } else {
        part = added / session.target;
        sessionText.textContent = added.toLocaleString() + ' of ' + session.target.toLocaleString() + ' words';
      }
      // time: an even glide second to second; words: a quick ease as you type
      var timed = session.kind === 'time';
      line.classList.toggle('duration-1000', timed);
      line.classList.toggle('ease-linear', timed);
      line.classList.toggle('duration-700', !timed);
      line.classList.toggle('ease-out', !timed);
      line.style.width = Math.min(100, part * 100) + '%';
      // paused, the line stops in a quiet grey; the palette's colour again on Resume
      line.classList.toggle('bg-primary', !session.pausedAt);
      line.classList.toggle('bg-base-content/30', !!session.pausedAt);
      if (part >= 1) {
        session.done = true;
        keep();
        drawMenu();
        sessionTick();
        // a brief glow as it's reached - none for anyone who asked for less motion
        line.classList.add('motion-safe:shadow-[0_0_12px_var(--color-success)]');
        setTimeout(function () { line.classList.remove('motion-safe:shadow-[0_0_12px_var(--color-success)]'); }, 1500);
      }
    };
    // the list of sessions, and under it - not in it, where daisyUI's menu
    // styles every child as an item - the row for a custom one
    var panel = document.createElement('div');
    panel.className = 'dropdown-content z-10 mt-2 w-60 rounded-box border border-base-300 p-1 shadow-lg ' +
                      (document.documentElement.hasAttribute('data-glass') ? 'glass-fill glass-blur' : 'bg-base-100');
    var menu = document.createElement('ul');
    menu.className = 'menu menu-sm w-full p-0';
    panel.appendChild(menu);
    var item = function (label, run) {
      var li = document.createElement('li'), a = document.createElement('button');
      a.type = 'button';
      a.textContent = label;
      a.addEventListener('click', function () { run(); });
      li.appendChild(a);
      menu.appendChild(li);
      return li;
    };
    var named = function (kind, n) { return n.toLocaleString() + (kind === 'time' ? ' minutes' : ' words'); };
    var begin = function (kind, target) {
      session = { kind: kind, target: target, started: Date.now(), startWords: wordsNow };
      keep();
      sessionTick();
      drawMenu();
      fitFocusBar();
      if (panel.contains(document.activeElement)) document.activeElement.blur();
    };
    // the last custom one is offered again, in this browser
    var custom = null;
    try { custom = JSON.parse(localStorage.getItem('focus-session-custom') || 'null'); } catch (err) {}
    var customForm = function () {
      var wrap = document.createElement('div');
      wrap.className = 'editor-session-custom grid grid-cols-[4rem_1fr_auto] items-center gap-1 px-1 pt-1 pb-0.5 ' +
                       'border-t border-base-300 mt-1';
      // a plain field - a number one's spinner arrows crowded the digits
      var count = document.createElement('input');
      count.type = 'text';
      count.inputMode = 'numeric';
      count.maxLength = 6;
      count.value = custom ? custom.target : 30;
      count.setAttribute('aria-label', 'How many');
      count.className = 'input input-sm w-full text-right tabular-nums';
      var kind = document.createElement('select');
      kind.setAttribute('aria-label', 'Minutes or words');
      kind.className = 'select select-sm w-full';
      [['time', 'minutes'], ['words', 'words']].forEach(function (k) {
        var o = document.createElement('option');
        o.value = k[0];
        o.textContent = k[1];
        o.selected = custom ? custom.kind === k[0] : k[0] === 'time';
        kind.appendChild(o);
      });
      var go = document.createElement('button');
      go.type = 'button';
      go.className = 'btn btn-sm btn-primary';
      go.textContent = 'Start';
      var start = function () {
        var n = Math.min(100000, parseInt(count.value, 10) || 0);
        if (n < 1) { count.focus(); return; }
        custom = { kind: kind.value, target: n };
        try { localStorage.setItem('focus-session-custom', JSON.stringify(custom)); } catch (err) {}
        begin(custom.kind, custom.target);
      };
      go.addEventListener('click', start);
      count.addEventListener('keydown', function (e) { if (e.key === 'Enter' && !e.isComposing && e.keyCode !== 229) { e.preventDefault(); start(); } });
      wrap.append(count, kind, go);
      return wrap;
    };
    var drawMenu = function () {
      menu.replaceChildren();
      panel.querySelectorAll('.editor-session-custom').forEach(function (row) { row.remove(); });
      if (session && session.kind === 'time' && !session.done) {
        item(session.pausedAt ? 'Resume' : 'Pause', function () {
          if (session.pausedAt) {
            session.pausedFor = (session.pausedFor || 0) + Date.now() - session.pausedAt;
            session.pausedAt = 0;
          } else session.pausedAt = Date.now();
          keep();
          sessionTick();
          drawMenu();
        });
      }
      if (session) item('End session', function () { session = null; keep(); sessionTick(); drawMenu(); });
      SESSIONS.forEach(function (spec) { item(spec[2], function () { begin(spec[0], spec[1]); }); });
      if (custom && !SESSIONS.some(function (spec) { return spec[0] === custom.kind && spec[1] === custom.target; })) {
        item(named(custom.kind, custom.target), function () { begin(custom.kind, custom.target); });
      }
      // your own length, always there: a step to open it closed the menu
      panel.appendChild(customForm());
    };
    var sessionButton = iconButton(icons.timer, 'Writing session', function () {});
    var sessionMenu = document.createElement('div');
    sessionMenu.className = 'dropdown dropdown-end';
    sessionMenu.append(sessionButton, panel);
    drawMenu();
    focusMiddle.appendChild(sessionText);
    // Focus's tools, together - so they can fold into ⋯ and come back in order
    focusTools.append(sessionMenu, smaller, sizeReset, larger, browserBars);
    toolFolds = [[browserBars], [smaller, sizeReset, larger], [sessionMenu]];
    box.appendChild(line);
    // a timed session's line moves every second, gliding at an even pace
    // from one to the next - it jumped every 15 seconds before
    setInterval(function () { if (session && session.kind === 'time' && !session.pausedAt) sessionTick(); }, 1000);
    setSize(sizeAt);
    updateStatus();  // the words now, for a session carried over a reload

    // "Edit in Focus mode" (the posts lists, a post's own page): straight
    // in - and the address tidied, so a reload doesn't go in again
    if (new URLSearchParams(location.search).get('focus') === '1') {
      EasyMDE.toggleFullScreen(mde);
      mde.codemirror.focus();
      history.replaceState(null, '', location.pathname);
    }

    // the toolbar slides away while you type - and only if wanted
    // (Settings > Editor > Writing). Typing is the text changing as it's
    // typed: a phone's keyboard doesn't say which keys it presses.
    if (PREFS.focusToolbar !== 'none') {
      var MOUSE = matchMedia('(hover: hover)').matches, CHROME = '.editor-focusbar, .editor-bar, .editor-toolbar';
      // how far down the bars reach while shown - the mouse within it brings them back
      var reach = 0;
      var quiet = function () {
        if (!box.hasAttribute('data-typing')) {
          reach = 0;
          document.querySelectorAll(CHROME).forEach(function (el) {
            if (el.offsetParent) reach = Math.max(reach, el.getBoundingClientRect().bottom);
          });
        }
        setTyping(true);
      };
      mde.codemirror.on('change', function (cm, change) {
        if (mde.isFullscreenActive() && /^\+(input|delete)/.test(change.origin || '')) quiet();
      });
      // a selection made with the mouse brings them back, for formatting it;
      // one made with Shift and the arrows is still typing
      var byPointer = false;
      mde.codemirror.getWrapperElement().addEventListener('pointerdown', function () { byPointer = true; });
      mde.codemirror.on('keydown', function () { byPointer = false; });
      mde.codemirror.on('cursorActivity', function (cm) {
        if (cm.somethingSelected() && byPointer) setTyping(false);
      });
      if (MOUSE) {
        // reading the preview there's no typing to send them away: a second
        // with the mouse still does - unless it's over a bar or one of their
        // menus is open
        var idle = 0, pointerAt = null;
        var restIdle = function () {
          clearTimeout(idle);
          if (!mde.isFullscreenActive() || !mde.isPreviewActive()) return;
          idle = setTimeout(function () {
            var busy = (pointerAt && pointerAt.closest && pointerAt.closest(CHROME)) ||
                       (document.activeElement && document.activeElement.closest(CHROME));
            if (!busy && mde.isFullscreenActive() && mde.isPreviewActive()) quiet();
          }, 1000);
        };
        // back only when the mouse comes near them - moving it over the
        // writing leaves them away
        document.addEventListener('mousemove', function (e) {
          pointerAt = e.target;
          if (Math.abs(e.movementX) + Math.abs(e.movementY) <= 3) return;
          if (box.hasAttribute('data-typing') && e.clientY > (reach || 120) + 24) return;
          setTyping(false);
          restIdle();
        });
        // the preview opened from the keyboard (Ctrl+Alt+P) starts the wait too
        document.addEventListener('keyup', restIdle);
      } else {
        // a phone: back when you scroll up, as a browser's own bars come back
        var lastTop = 0;
        mde.codemirror.on('scroll', function (cm) {
          var top = cm.getScrollInfo().top;
          if (top < lastTop - 40) setTyping(false);
          if (top < lastTop - 40 || top > lastTop) lastTop = top;
        });
      }
    }
  }

  // On a phone the toolbar gives way to a bar of its own, above the
  // keyboard, with buttons a thumb can hit (44px) - Settings > Editor > On
  // a phone (editor_config.phone_bar): a button per section, each opening
  // its commands as a grid just above the bar; or the Icons toolbar's own
  // buttons in a row, with All for the rest; or no bar. Undo, Redo and
  // Help are buttons like the rest - in the row when they're yours, and
  // in History and Help. Write / Preview tabs sit over the text. It shows
  // while you're writing - there's nothing to format otherwise.
  if (toolbar) {
    var PHONE = matchMedia('(width < 40rem)'), vv = window.visualViewport, cm = mde.codemirror;
    var phoneBar = document.createElement('div');
    phoneBar.className = 'editor-phonebar';
    phoneBar.setAttribute('role', 'toolbar');
    phoneBar.setAttribute('aria-label', 'Formatting');
    phoneBar.hidden = true;
    var sheet = null;
    var closeSheet = function () {
      if (!sheet) return;
      sheet.remove();
      sheet = null;
      phoneBar.querySelectorAll('[aria-expanded]').forEach(function (b) { b.setAttribute('aria-expanded', 'false'); });
    };
    // pointerdown, not click: the text keeps its focus, so the keyboard stays up
    var keepFocus = function (el) { el.addEventListener('pointerdown', function (e) { e.preventDefault(); }); };
    var placeSheet = function () {
      if (!sheet) return;
      var top = phoneBar.getBoundingClientRect().top;
      sheet.style.bottom = (window.innerHeight - top + 4) + 'px';
      sheet.style.maxHeight = Math.max(160, top - (vv ? vv.offsetTop : 0) - 16) + 'px';
    };
    // sections, buttons or none (editor_config.phone_bar)
    var MODE = PREFS.phone || 'sections', SECTIONS = {};
    (PREFS.sections || []).forEach(function (section) { SECTIONS[section.name] = section; });
    // a phone's screen is too narrow for side by side
    var PHONE_SKIP = ['side-by-side'];
    // undo and redo again and again, without the sheet closing each time
    var STAYS_OPEN = ['undo', 'redo'];
    var run = function (id, from) {
      if (id === 'insert') { closeSheet(); mde.openInsert(from); return; }  // the list, over the bar
      if (STAYS_OPEN.indexOf(id) === -1) closeSheet();
      ACTIONS[id](mde);
      showBar();
    };
    // the section or gallery the cursor is in: its options, a tab of
    // their own first in All, the one in use picked (slash_menu.js)
    var BLOCK = '@block', here = null;
    var blockGrid = function () {
      var tiles = document.createElement('div');
      tiles.className = 'grid grid-cols-4 gap-1';
      (here ? here[1] : []).forEach(function (it) {
        var b = document.createElement('button');
        b.type = 'button';
        b.className = 'editor-tile flex flex-col items-center justify-start gap-1 min-h-16 px-1 pt-2.5 pb-1.5 rounded-field [&_.editor-icon]:size-5.5! ' +
                      'text-xs text-center leading-tight hover:bg-base-200 active:bg-base-300' +
                      (it.hint ? ' bg-base-200 font-semibold' : '');
        if (it.hint) b.setAttribute('aria-pressed', 'true');
        b.innerHTML = it.icon;  // from editor_icons - never anything typed
        var label = document.createElement('span');
        label.textContent = it.label;
        b.appendChild(label);
        keepFocus(b);
        b.addEventListener('click', function () { closeSheet(); mde.codemirror.operation(it.run); showBar(); });
        tiles.appendChild(b);
      });
      return tiles;
    };
    // a section's commands as a grid of tiles, each an icon and its name
    var grid = function (name) {
      if (name === BLOCK) return blockGrid();
      var tiles = document.createElement('div');
      tiles.className = 'grid grid-cols-4 gap-1';
      SECTIONS[name].ids.forEach(function (id) {
        if (PHONE_SKIP.indexOf(id) > -1 || !ACTIONS[id]) return;
        var c = COMMANDS[id], b = document.createElement('button');
        b.type = 'button';
        b.dataset.id = id;
        b.className = 'editor-tile flex flex-col items-center justify-start gap-1 min-h-16 px-1 pt-2.5 pb-1.5 rounded-field [&_.editor-icon]:size-5.5! ' +
                      'text-xs text-center leading-tight hover:bg-base-200 active:bg-base-300';
        b.innerHTML = c.icon;  // from editor_icons - never anything typed
        var label = document.createElement('span');
        label.textContent = c.label;
        b.appendChild(label);
        keepFocus(b);
        b.addEventListener('click', function () { run(id, b); });
        tiles.appendChild(b);
      });
      return tiles;
    };
    var newSheet = function (button, label) {
      var same = sheet && sheet.dataset.from === button.dataset.id;
      closeSheet();
      if (same) return null;
      if (mde.insertOpen()) mde.openInsert();  // one menu at a time
      if (mde.sectionsOpen()) mde.openSections();
      sheet = document.createElement('div');
      sheet.dataset.from = button.dataset.id;
      sheet.setAttribute('role', 'menu');
      sheet.setAttribute('aria-label', label);
      sheet.className = 'editor-sheet overscroll-contain rounded-box border border-base-300 shadow-lg p-1 ' +
                        (document.documentElement.hasAttribute('data-glass') ? 'glass-fill glass-blur' : 'bg-base-100');
      button.setAttribute('aria-expanded', 'true');
      return sheet;
    };
    var show = function () {
      mde.holdSwipes(sheet);
      document.body.appendChild(sheet); placeSheet(); syncHistory(); _scrollHints(sheet);
    };
    // a section: its name, then its grid
    var titleOf = function (name) {
      return name === BLOCK ? here[0] : name;
    };
    var openSection = function (button, name) {
      if (!newSheet(button, name)) return;
      var title = document.createElement('div');
      title.className = 'px-3 pt-2 pb-1 text-xs font-semibold text-base-content/60';
      title.textContent = titleOf(name);
      sheet.appendChild(title);
      sheet.appendChild(grid(name));
      show();
    };
    // All, after your own buttons: every section, a tab each
    var openAll = function (button) {
      if (!newSheet(button, 'All')) return;
      var tabs = document.createElement('div'), body = document.createElement('div');
      tabs.className = 'tabs tabs-border tabs-sm flex-nowrap overflow-x-auto shrink-0 mb-1 ' + SCROLLS_X;
      tabs.dataset.scrollX = '';
      tabs.setAttribute('role', 'tablist');
      // it opens on the tab used last on this device, else where a + leads:
      // Insert - the other sections a swipe away
      var names = Object.keys(SECTIONS), last = null;
      try { last = localStorage.getItem('editor-sheet-tab'); } catch (e) {}
      var first = names.indexOf(last) !== -1 ? names.indexOf(last) : Math.max(0, names.indexOf('Insert'));
      // in a section or a gallery, it opens on that block's options
      here = mde.blockOptions ? mde.blockOptions() : null;
      if (here && here[1].length) { names.unshift(BLOCK); first = 0; }
      // a tab's grid slides in from its side as the one before slides out,
      // and a swipe drags the grid with the finger first - as tabbed sheets
      // do in other apps. Asked for less motion: it just changes.
      var at = first, sliding = false, still = matchMedia('(prefers-reduced-motion: reduce)');
      var EASE = 'transform 0.25s cubic-bezier(0.2, 0, 0, 1)';
      body.className = 'relative overflow-hidden touch-pan-y';
      var peek = null;  // the next tab's grid, beside the one being dragged
      var go = function (i, dir) {
        if (i < 0 || i >= names.length || sliding) return false;
        var old = body.firstElementChild, next = peek && peek.dataset.at === String(i) ? peek : grid(names[i]);
        if (peek && peek !== next) peek.remove();
        peek = null;
        at = i;
        try { if (names[i] !== BLOCK) localStorage.setItem('editor-sheet-tab', names[i]); } catch (e) {}
        [].forEach.call(tabs.children, function (t, n) { t.classList.toggle('tab-active', n === i); });
        tabs.children[i].scrollIntoView({ block: 'nearest', inline: 'nearest' });
        if (!dir || still.matches || !old) { body.replaceChildren(next); syncHistory(); return true; }
        sliding = true;
        if (!next.parentNode) {
          next.style.cssText = 'position: absolute; inset: 0 0 auto 0; transform: translateX(' + (dir * 100) + '%)';
          body.appendChild(next);
        }
        // the sheet's height goes from this tab's to the next's as they slide
        body.style.height = old.offsetHeight + 'px';
        next.getBoundingClientRect();  // placed beside, then both move
        old.style.transition = next.style.transition = EASE;
        body.style.transition = 'height 0.25s cubic-bezier(0.2, 0, 0, 1)';
        old.style.transform = 'translateX(' + (-dir * 100) + '%)';
        next.style.transform = 'translateX(0)';
        body.style.height = next.offsetHeight + 'px';
        setTimeout(function () {
          old.remove();
          next.style.cssText = '';
          body.style.height = body.style.transition = '';
          sliding = false;
          syncHistory();
        }, 260);
        return true;
      };
      names.forEach(function (name, i) {
        var tab = document.createElement('button');
        tab.type = 'button';
        tab.className = 'tab shrink-0' + (i === first ? ' tab-active' : '');
        tab.setAttribute('role', 'tab');
        tab.textContent = titleOf(name);
        keepFocus(tab);
        tab.addEventListener('click', function () { if (i !== at) go(i, i > at ? 1 : -1); });
        tabs.appendChild(tab);
      });
      body.appendChild(grid(names[first]));
      var from = null, dragging = false;
      body.addEventListener('touchstart', function (e) {
        from = e.touches.length === 1 && !sliding ? { x: e.touches[0].clientX, y: e.touches[0].clientY } : null;
        dragging = false;
      }, { passive: true });
      body.addEventListener('touchmove', function (e) {
        if (!from || still.matches) return;
        var dx = e.touches[0].clientX - from.x, dy = e.touches[0].clientY - from.y;
        if (!dragging && Math.abs(dx) > 8 && Math.abs(dx) > Math.abs(dy)) dragging = true;
        if (!dragging) return;
        // past the first or last tab it gives, but only a little
        var end = (dx > 0 && at === 0) || (dx < 0 && at === names.length - 1), dir = dx < 0 ? 1 : -1;
        var move = end ? dx / 4 : dx;
        body.firstElementChild.style.transition = '';
        body.firstElementChild.style.transform = 'translateX(' + move + 'px)';
        // the tab it's going to comes in beside it
        if (peek && peek.dataset.at !== String(at + dir)) { peek.remove(); peek = null; }
        if (!peek && !end) {
          peek = grid(names[at + dir]);
          peek.dataset.at = String(at + dir);
          peek.style.cssText = 'position: absolute; inset: 0 0 auto 0';
          body.appendChild(peek);
        }
        if (peek) peek.style.transform = 'translateX(calc(' + (dir * 100) + '% + ' + move + 'px))';
      }, { passive: true });
      body.addEventListener('touchend', function (e) {
        if (!from) return;
        var dx = e.changedTouches[0].clientX - from.x, dy = e.changedTouches[0].clientY - from.y;
        from = null;
        var swiped = Math.abs(dx) >= 48 && Math.abs(dx) >= Math.abs(dy) * 1.5 && go(at + (dx < 0 ? 1 : -1), dx < 0 ? 1 : -1);
        var g = body.firstElementChild;
        if (!swiped && dragging && g) {  // not far enough: back where it was, the next tab back out
          g.style.transition = EASE;
          g.style.transform = 'translateX(0)';
          if (peek) {
            var gone = peek, side = gone.style.transform.indexOf('(calc(-') > -1 ? -100 : 100;
            gone.style.transition = EASE;
            gone.style.transform = 'translateX(' + side + '%)';
            setTimeout(function () { gone.remove(); }, 260);
            peek = null;
          }
        }
        dragging = false;
      }, { passive: true });
      // the tabs stay put; a long tab (Sections) scrolls under them, fading
      // at the bottom while there's more
      var scroller = document.createElement('div');
      scroller.className = 'flex-1 min-h-0 overflow-y-auto overscroll-contain ' + SCROLLS;
      scroller.dataset.scrollHint = '';
      scroller.appendChild(body);
      sheet.classList.add('flex', 'flex-col');
      sheet.appendChild(tabs);
      sheet.appendChild(scroller);
      show();
    };
    var barButton = function (parent, id, icon, label, tap, expands) {
      var b = document.createElement('button');
      b.type = 'button';
      b.dataset.id = id;
      // the row's buttons and the + after it keep their 44px (! over the bar's flex: 1);
      // a bar of sections spreads its buttons across the width
      if (parent !== phoneBar || id === 'all' || id === 'sections-jump') b.className = 'flex-none! w-11!';
      b.innerHTML = icon;  // from editor_icons
      b.setAttribute('aria-label', label);
      if (expands) b.setAttribute('aria-expanded', 'false');
      keepFocus(b);
      b.addEventListener('click', function () { tap(b); });
      parent.appendChild(b);
      return b;
    };
    var divider = function (parent) {
      var line = document.createElement('span');
      line.className = 'editor-phonebar-sep flex-none self-center w-px h-6 mx-0.5 bg-base-300';
      line.setAttribute('aria-hidden', 'true');
      parent.appendChild(line);
    };
    if (MODE === 'sections') {
      (PREFS.phoneSections || []).forEach(function (name) {
        barButton(phoneBar, name, SECTIONS[name].icon, name, function (b) { openSection(b, name); }, true);
      });
    } else if (MODE === 'buttons') {
      // your buttons, in their sections - the row swipes if they don't fit
      var row = document.createElement('div');
      row.className = 'editor-phonebar-scroll flex flex-1 min-w-0 overflow-x-auto ' + SCROLLS_X;  // it fades where there's more (live.js)
      row.dataset.scrollX = '';
      // Insert isn't among them: the + at the bar's end is (below)
      var mine = PREFS.pinned.filter(function (id) { return PHONE_SKIP.indexOf(id) === -1 && id !== 'insert'; });
      mine.forEach(function (id, i) {
        if (i && PREFS.groups[id] !== PREFS.groups[mine[i - 1]]) divider(row);
        barButton(row, id, COMMANDS[id].icon, COMMANDS[id].label, function (b) { run(id, b); });
      });
      phoneBar.appendChild(row);
      _scrollHintX(row);  // watched from now on, as it shows and hides
    }
    // Sections: the post's own sections, to jump to one - its list opens as
    // Insert's does, over the bar. Just its icon, with its name for a screen reader.
    var jumpButton = function () {
      var m = PREFS.menus.goto;
      var b = barButton(phoneBar, 'sections-jump', m.icon, PREFS.goTo.label, function (b) {
        closeSheet();
        mde.openSections(b);
      }, true);
      b.setAttribute('aria-haspopup', 'listbox');
    };
    if (MODE === 'buttons') {
      divider(phoneBar);
      jumpButton();
      // a phone's one +: every section's commands, a tab each - Insert's among them
      barButton(phoneBar, 'all', COMMANDS.insert.icon, 'All', openAll, true);
    } else if (MODE === 'sections') {
      jumpButton();
    }
    document.body.appendChild(phoneBar);
    // above the keyboard: the visual viewport is what's left of the screen
    // In the browser's own full screen, Chrome lays the keyboard over the
    // page without making room for it (interactive-widget doesn't apply
    // there): the bar sat a whole bar's height under it. There, its
    // keyboard API says how tall the keyboard is - the bar goes just above
    // it, and the text stops above the bar. Elsewhere the page makes room.
    var vk = navigator.virtualKeyboard;
    var overKeyboard = function () { return !!(vk && vk.overlaysContent); };
    var lastKb = 0;
    var placeBar = function () {
      var wrap = cm.getWrapperElement();
      if (overKeyboard()) {
        // from the keyboard's top edge: its height left out Android's own
        // strip below it (the ⌄ and the home line), and the bar sat under it
        var rect = vk.boundingRect, kb = rect.height ? Math.max(rect.height, window.innerHeight - rect.top) : 0;
        phoneBar.style.top = '';
        phoneBar.style.bottom = kb + 'px';
        wrap.style.bottom = kb ? (kb + phoneBar.offsetHeight) + 'px' : '';
        // the line you're on, still in view - as the keyboard comes up, not
        // each time the bar is placed: scrolling away went back to the cursor
        if (kb && kb !== lastKb && cm.hasFocus()) cm.scrollIntoView(null, 56);
        lastKb = kb;
      } else if (vv) {
        // from the top of what you can see, not the window's foot: in
        // Firefox's full screen (no keyboard API) the window reached past
        // what's shown, and the bar sat that much under the keyboard
        phoneBar.style.bottom = 'auto';
        phoneBar.style.top = Math.max(0, vv.offsetTop + vv.height - phoneBar.offsetHeight) + 'px';
        wrap.style.bottom = '';
      } else {
        phoneBar.style.top = '';
        phoneBar.style.bottom = '0px';
        wrap.style.bottom = '';
      }
      placeSheet();
    };
    if (vk) {
      document.addEventListener('fullscreenchange', function () {
        vk.overlaysContent = !!document.fullscreenElement;
        placeBar();
      });
      vk.addEventListener('geometrychange', placeBar);
    }
    var showBar = function () {
      var drawer = document.querySelector('#editor-help-panel:not(.translate-x-full), #post-settings-panel:not(.translate-x-full)');
      var on = MODE !== 'none' && PHONE.matches && !drawer && !mde.isPreviewActive() &&
               (cm.hasFocus() || !!sheet || mde.insertOpen() || mde.sectionsOpen());
      phoneBar.hidden = !on;
      document.documentElement.toggleAttribute('data-writing', on);
      if (on) placeBar();
      else closeSheet();
    };
    cm.on('focus', showBar);
    cm.on('blur', function () { setTimeout(showBar, 200); });
    // a closed keyboard comes back with a tap on the text. Closed with its
    // own button, the text keeps its focus, and a tap on what already has
    // it opens nothing (the title, the browser's own field, does) - so away
    // and back in the tap, for the browser a fresh one. The window shrinks
    // with the keyboard (interactive-widget): smaller than it's been, it's up.
    // Only a tap does it: a finger that scrolled the text also ends on it,
    // and brought the keyboard up and the page back to the cursor.
    var viewHeight = function () { return vv ? vv.height : window.innerHeight; };
    var tallest = viewHeight();
    window.addEventListener('resize', function () { tallest = Math.max(tallest, viewHeight()); });
    matchMedia('(orientation: portrait)').addEventListener('change', function () { tallest = 0; });
    // The keyboard closed with its own button leaves the text focused, and
    // anything that then touches the text - a scroll redrawing the cursor,
    // a line coming into view - brings the keyboard back. So a closed
    // keyboard takes the focus off the text and the title: it opens when
    // one is tapped.
    var keyboardUp = false;
    var keyboardMoved = function () {
      var up = overKeyboard() ? vk.boundingRect.height > 0 : viewHeight() < tallest - 120;
      var was = keyboardUp;
      keyboardUp = up;
      if (!was || up || !PHONE.matches) return;
      var at = document.activeElement;
      if (at && cm.getWrapperElement().contains(at)) at.blur();
    };
    var tapFrom = null;
    var scrolledTo = function () { return cm.getScrollInfo().top + window.scrollY; };
    cm.getWrapperElement().addEventListener('touchstart', function (e) {
      tapFrom = e.touches.length === 1 ? { x: e.touches[0].clientX, y: e.touches[0].clientY, at: scrolledTo(), when: Date.now() } : null;
    }, { passive: true });
    cm.getWrapperElement().addEventListener('touchend', function (e) {
      tallest = Math.max(tallest, viewHeight());
      var from = tapFrom, to = e.changedTouches[0];
      tapFrom = null;
      if (!from || Math.abs(to.clientX - from.x) > 10 || Math.abs(to.clientY - from.y) > 10 || scrolledTo() !== from.at) return;
      // a long press selects a word: away and back would drop the selection
      // and its handles
      if (Date.now() - from.when >= 400 || cm.somethingSelected() || !window.getSelection().isCollapsed) return;
      if (!PHONE.matches || !cm.hasFocus() || viewHeight() < tallest - 120) return;
      var input = cm.getInputField();
      input.blur();
      // where the tap was stays where it is - the browser would bring the
      // field back into view from where the cursor was before the tap
      input.focus({ preventScroll: true });
    }, { passive: true });
    document.addEventListener('pointerdown', function (e) {
      if (sheet && !sheet.contains(e.target) && !phoneBar.contains(e.target)) closeSheet();
      setTimeout(showBar, 250);
    });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && sheet) closeSheet(); });
    if (vv) { vv.addEventListener('resize', placeBar); vv.addEventListener('scroll', placeBar); vv.addEventListener('resize', keyboardMoved); }
    window.addEventListener('resize', keyboardMoved);
    if (vk) vk.addEventListener('geometrychange', keyboardMoved);
    PHONE.addEventListener('change', showBar);
    // Help and Post settings, however they're opened
    ['editor-help-panel', 'post-settings-panel'].forEach(function (id) {
      var panel = document.getElementById(id);
      if (panel) new MutationObserver(showBar).observe(panel, { attributes: true, attributeFilter: ['class'] });
    });
    // the caret stays clear of the bar as you type down the page
    cm.setOption('cursorScrollMargin', 56);

    // Write / Preview and Focus mode at the start of the bar over the
    // text, all alike (Side by side joins them in focus mode, where
    // there's room for it - input.css)
    var tabs = document.createElement('div');
    tabs.className = 'editor-tabs group/tabs tabs tabs-border flex-nowrap';
    tabs.setAttribute('role', 'tablist');
    // the view: Write, Preview or Side by side - Focus is on or off beside it
    var mode = function () { return mde.isSideBySideActive() ? 'side' : mde.isPreviewActive() ? 'preview' : 'write'; };
    [['write', 'Write'], ['preview', 'Preview'], ['side', 'Side by side'], ['focus', 'Focus']].forEach(function (spec) {
      var tab = document.createElement('button');
      tab.type = 'button';
      tab.className = 'tab';
      tab.dataset.mode = spec[0];
      // a phone shows their icons, leaving room for the post's buttons beside Save
      var icon = { write: 'pencil', preview: 'eye', side: 'columns-2', focus: 'maximize-2' }[spec[0]];
      if (icon) {
        tab.innerHTML = '<span class="sm:hidden group-data-[icons]/tabs:inline" aria-hidden="true">' +
                        PREFS.icons[icon] + '</span>' +
                        '<span class="max-sm:sr-only group-data-[icons]/tabs:sr-only">' + spec[1] + '</span>';
      } else tab.textContent = spec[1];
      if (spec[0] === 'focus') {
        // a switch, not a view: on or off, filled while it's on (syncTabs)
        tab.setAttribute('aria-pressed', 'false');
        tab.addEventListener('click', function () { EasyMDE.toggleFullScreen(mde); cm.focus(); });
      } else {
        tab.setAttribute('role', 'tab');
        tab.addEventListener('click', function () {
          if (spec[0] !== 'side' && mde.isSideBySideActive()) EasyMDE.toggleSideBySide(mde);
          if (spec[0] === 'side' && !mde.isSideBySideActive()) {
            if (mde.isPreviewActive()) EasyMDE.togglePreview(mde);
            EasyMDE.toggleSideBySide(mde);
          }
          if (spec[0] !== 'side' && mde.isPreviewActive() !== (spec[0] === 'preview')) EasyMDE.togglePreview(mde);
          if (spec[0] !== 'preview') cm.focus();
          showBar();
        });
      }
      tabs.appendChild(tab);
    });
    var syncTabs = function () {
      var now = mode();
      [].forEach.call(tabs.children, function (tab) {
        if (tab.dataset.mode === 'focus') {
          var on = mde.isFullscreenActive();
          tab.classList.toggle('bg-base-300', on);
          tab.classList.toggle('rounded-field', on);
          tab.setAttribute('aria-pressed', String(on));
          return;
        }
        tab.classList.toggle('tab-active', tab.dataset.mode === now);
        tab.setAttribute('aria-selected', String(tab.dataset.mode === now));
      });
    };
    var viewsSlot = document.getElementById('editor-views');
    if (viewsSlot) viewsSlot.appendChild(tabs); else box.insertBefore(tabs, box.firstChild);
    syncTabs();
    // however the view changes (the tabs, Esc, a shortcut, the ⋯ menu)
    new MutationObserver(syncTabs).observe(box, { attributes: true, subtree: true, attributeFilter: ['class'] });
  }
});
