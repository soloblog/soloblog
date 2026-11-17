// Post settings > Template > Apply a template (TemplateDialog, routes/editor.py).
// The chosen template's words go at the end of the text and its settings
// take the place of the page's - in the editor only, nothing is saved until
// Save, so Discard takes it back too. The status beside Save says what
// changed and has an Undo, until the next edit.
var _APPLY_SETTINGS = ['title_style', 'page_width', 'cover_width', 'toc_style', 'heading_fold', 'section_space',
  'section_motion', 'slides', 'in_wiki', 'remind_update', 'link_url'];
var _APPLY_SIDES = ['tags', 'archive', 'author'];
// a template fills these only where the page has nothing of its own
var _APPLY_FILLS = [['tags', 'tags'], ['summary', 'summary'], ['cover', 'cover_image']];
// on a phone there's no room beside Save for words and an Undo: a bar over the screen's foot, as a snackbar is
var _APPLY_SNACK = 'flex items-center min-w-0 max-sm:fixed max-sm:inset-x-3 max-sm:bottom-20 max-sm:z-50 max-sm:flex max-sm:items-center ' +
  'max-sm:justify-between max-sm:gap-2 max-sm:rounded-field max-sm:border max-sm:border-base-300 max-sm:bg-base-100 ' +
  'max-sm:px-3 max-sm:py-2 max-sm:text-sm max-sm:whitespace-normal max-sm:shadow-lg';
function _applyStatus(text, cls) {
  var s = document.getElementById('save-status');
  if (!s) return null;
  s.textContent = text;
  s.className = 'text-xs ' + (cls || '');
  return s;
}
// sets a field to a template's value and says whether that changed it
function _applySet(field, value) {
  var before = field.type === 'checkbox' ? {checked: field.checked} : {value: field.value};
  if (field.type === 'checkbox') field.checked = !!value;
  else {
    value = value == null ? '' : String(value);
    // a choice this page doesn't offer means following the site
    if (field.tagName === 'SELECT' && ![].some.call(field.options, function (o) { return o.value === value; })) value = '';
    field.value = value;
  }
  var changed = field.type === 'checkbox' ? field.checked !== before.checked : field.value !== before.value;
  return changed ? {field: field, before: before} : null;
}
function _applyTell(field) {
  field.dispatchEvent(new Event('input', {bubbles: true}));
  field.dispatchEvent(new Event('change', {bubbles: true}));
}
function _applyUndo(mde, text, changes) {
  mde.value(text);
  changes.forEach(function (c) {
    if ('checked' in c.before) c.field.checked = c.before.checked;
    else c.field.value = c.before.value;
    _applyTell(c.field);
  });
}
// Show's ticks from a template's extras: "" follows the site (what each tick's site value says),
// "none" is no ticks, else the list. Returns the ticks that changed.
function _applyShow(form, extras) {
  var chosen = extras && extras !== 'none' ? extras.split(',') : [], changes = [];
  [].forEach.call(form.querySelectorAll('input[name="extras"]'), function (box) {
    var on = !extras ? box.dataset.siteValue === '1' : chosen.indexOf(box.value) >= 0;
    var change = _applySet(box, on);
    if (change) changes.push(change);
  });
  return changes;
}
function applyTemplate(key) {
  var form = document.getElementById('post-form'), mde = window._activeEasyMDE;
  var dialog = document.getElementById('template-dialog');
  if (dialog) dialog.close();
  if (!form || !mde) return;
  fetch('/admin/template/' + encodeURIComponent(key), {headers: {Accept: 'application/json'}, credentials: 'same-origin'})
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (t) { _applyIn(form, mde, t); },
          function () { _applyStatus("Couldn't apply the template", 'text-error'); });
}
function _applyIn(form, mde, t) {
  var text = mde.value(), kept = text.replace(/\s+$/, ''), body = (t.body || '').replace(/\s+$/, '');
  var changes = [], settings = 0;
  mde.value(kept ? kept + '\n\n' + body + '\n' : body + '\n');
  if (kept) {
    // the new part's first line, in view
    mde.codemirror.scrollIntoView({line: kept.split('\n').length + 1, ch: 0}, 120);
  }
  _APPLY_SETTINGS.forEach(function (name) {
    var field = form.elements[name], change = field && name in (t.settings || {}) ? _applySet(field, t.settings[name]) : null;
    if (change) { changes.push(change); settings++; }
  });
  // the side panels' places, written "tags=left,author=off"
  var places = {};
  String((t.settings || {}).sides || '').split(',').forEach(function (part) {
    var pair = part.split('=');
    if (pair.length === 2) places[pair[0]] = pair[1];
  });
  _APPLY_SIDES.forEach(function (name) {
    var field = form.elements['sides_' + name], change = field && t.settings ? _applySet(field, places[name] || '') : null;
    if (change) { changes.push(change); settings++; }
  });
  // Show counts as one setting, however many of its ticks changed
  var show = t.settings && 'extras' in t.settings ? _applyShow(form, t.settings.extras) : [];
  if (show.length) { changes.push.apply(changes, show); settings++; }
  _APPLY_FILLS.forEach(function (pair) {
    var field = form.elements[pair[1]];
    if (field && !field.value.trim() && t[pair[0]]) {
      var change = _applySet(field, t[pair[0]]);
      if (change) changes.push(change);
    }
  });
  changes.forEach(function (c) { _applyTell(c.field); });
  // the group of less common settings opens when the page has one set
  var more = document.getElementById('page-more');
  if (more && ['slides', 'in_wiki', 'remind_update', 'link_url'].some(function (n) {
    var f = form.elements[n]; return f && (f.type === 'checkbox' ? f.checked : f.value.trim());
  })) more.open = true;
  // a slide-over would cover the status beside Save; beside the text it stays
  if (typeof togglePostSettings === 'function') togglePostSettings(false);
  // after the changes above, which each say "Unsaved changes" here
  var status = _applyStatus('', _APPLY_SNACK);
  if (!status) return;
  // beside Save the words shorten before the Undo does; on a phone they wrap
  var words = document.createElement('span');
  words.className = 'truncate max-sm:overflow-visible max-sm:whitespace-normal';
  words.textContent = t.name + ' applied' + (settings ? ' · ' + settings + (settings === 1 ? ' setting' : ' settings') + ' changed' : '');
  status.append(words);
  var undo = document.createElement('button');
  undo.type = 'button';
  undo.className = 'btn btn-xs btn-ghost ml-1 shrink-0';
  undo.textContent = 'Undo';
  undo.onclick = function () { _applyUndo(mde, text, changes); };
  status.append(undo);
}
