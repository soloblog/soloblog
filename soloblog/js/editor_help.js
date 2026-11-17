// The Help panel (EditorHelpPanel): a drawer from the right, like Post
// settings. section: where to open it (start, shortcuts...).
var MAC = /Mac|iPhone|iPad/.test(navigator.platform || '');
function toggleEditorHelp(open, section) {
  var panel = document.getElementById('editor-help-panel');
  if (!panel) return;
  if (open === undefined) open = panel.classList.contains('translate-x-full');
  var scroll = document.getElementById('editor-help-scroll');
  if (open) scroll.classList.remove('hidden');
  // hidden once it has slid away - laid out off screen, it slows down typing
  else setTimeout(function () { if (panel.classList.contains('translate-x-full')) scroll.classList.add('hidden'); }, 250);
  if (!open) panelClosed(panel);
  var wasOpen = !panel.hasAttribute('inert');
  panel.classList.toggle('translate-x-full', !open);
  panel.toggleAttribute('inert', !open);
  document.getElementById('editor-help-backdrop').classList.toggle('hidden', !open);
  if (open) {
    if (!wasOpen) _panelFrom.set(panel, document.activeElement);
    // not on a touch screen: the keyboard would cover the panel
    if (_keyboardToHand()) panel.querySelector('input[type=search]').focus({ preventScroll: true });
    else if (document.activeElement) document.activeElement.blur();  // the keyboard would cover it
    _loadEditorHelp().then(function () {
      var to = section && panel.querySelector('[data-help-section="' + section + '"]');
      scroll.scrollTop = to ? to.offsetTop - _helpHead() : 0;
    });
  }
}
function openEditorHelp(section) { toggleEditorHelp(true, section); }
// its parts come the first time it opens - half the editor's page otherwise
var _helpLoading = null;
function _loadEditorHelp() {
  if (!_helpLoading) {
    var parts = document.getElementById('editor-help-parts');
    _helpLoading = fetch('/admin/editor/help')
      .then(function (r) { return r.ok ? r.text() : Promise.reject(); })
      .then(function (html) {
        parts.innerHTML = html;
        if (MAC) parts.querySelectorAll('kbd[data-mac]').forEach(function (k) { k.textContent = k.dataset.mac; });
        // a search typed while they came
        var box = document.querySelector('#editor-help-panel input[type=search]');
        if (box && box.value) box.dispatchEvent(new Event('input', { bubbles: true }));
      })
      .catch(function () { _helpLoading = null; });
  }
  return _helpLoading;
}
// the height of its title, search and jump row, which stay over what scrolls
function _helpHead() {
  var head = document.getElementById('editor-help-head');
  return (head ? head.offsetHeight : 0) + 4;
}
document.addEventListener('DOMContentLoaded', function () {
  var panel = document.getElementById('editor-help-panel');
  if (!panel) return;
  // search: every entry whose words have it, and the sections that still
  // have one
  var box = panel.querySelector('input[type=search]'), empty = document.getElementById('editor-help-empty');
  var count = document.getElementById('editor-help-count'), guide = document.getElementById('editor-help-guide');
  box.addEventListener('input', function () {
    // every word somewhere in the entry, as Settings' and Help's own search
    var q = box.value.trim(), words = q.toLowerCase().split(/\s+/).filter(Boolean), any = false, n = 0;
    var has = function (text) { return words.every(function (w) { return (text || '').indexOf(w) !== -1; }); };
    panel.querySelectorAll('[data-help-section]').forEach(function (s) {
      var shown = 0, all = has(s.dataset.words);
      s.querySelectorAll('[data-help-entry]').forEach(function (e) {
        var hit = !words.length || all || has(e.dataset.words);
        e.hidden = !hit;
        // a folded row (a section) opens when the search finds it
        if (e.tagName === 'DETAILS') e.open = !!words.length && hit && !all;
        if (hit) shown++;
      });
      s.hidden = words.length && !shown;
      if (!s.hidden) { any = true; n += shown; }
    });
    empty.hidden = any;
    // it's filtering, and says so - with the way back
    count.hidden = !words.length || !any;
    count.querySelector('span').textContent = n === 1 ? 'Showing 1 match' : 'Showing ' + n + ' matches';
    guide.href = '/admin/help' + (q ? '?q=' + encodeURIComponent(q) : '');
    document.getElementById('editor-help-guide-search').href = guide.href;
  });
  count.querySelector('button').addEventListener('click', function () {
    box.value = '';
    box.dispatchEvent(new Event('input', {bubbles: true}));
    box.focus();
  });
  // Insert: the example into the post, on a line of its own
  panel.addEventListener('click', function (e) {
    // a part of the panel to jump to
    var jump = e.target.closest('[data-help-jump]');
    if (jump) {
      var to = panel.querySelector('[data-help-section="' + jump.dataset.helpJump + '"]');
      // a part that isn't showing (hidden by a search) has nowhere to go
      if (to && to.offsetParent) document.getElementById('editor-help-scroll').scrollTo({ top: to.offsetTop - _helpHead(), behavior: 'smooth' });
      return;
    }
    var b = e.target.closest('[data-help-insert]');
    if (!b || !window._activeEasyMDE) return;
    toggleEditorHelp(false);
    window._activeEasyMDE.insertBlock(b.closest('[data-help-example], [data-help-entry]').querySelector('code').textContent);
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !panel.classList.contains('translate-x-full') &&
        !document.querySelector('dialog[open], :popover-open')) {
      e.preventDefault();
      e.stopPropagation();
      toggleEditorHelp(false);
    }
  }, true);
});
