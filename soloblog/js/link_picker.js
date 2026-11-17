function openLinkPicker(target) {
  // target is either the EasyMDE instance (the post editor's own
  // toolbar action, unchanged) or a plain input id string (any other
  // picker field, e.g. the Banner's Button link) - same target/EasyMDE split
  // MEDIA_PICKER_JS already uses for openMediaPicker, so a field just
  // says which one it is instead of two separate open functions.
  var dlg = document.getElementById('link-picker-dialog');
  if (!dlg) return;
  var field = typeof target === 'string' ? document.getElementById(target) : null;
  if (typeof target === 'string') {
    dlg.dataset.target = target;
    window._activeEasyMDE = null;
  } else if (target) {
    window._activeEasyMDE = target;
    dlg.dataset.target = '__easymde_body__';
  }
  // a page field (ui.PageField) offers just its pages, and takes a slug
  var kind = (field && field.dataset.pickerKind) || '';
  document.getElementById('link-picker-kind').value = kind;
  var search = document.getElementById('link-picker-search');
  search.setAttribute('hx-vals', JSON.stringify({exclude: (field && field.dataset.pickerExclude) || ''}));
  document.getElementById('link-picker-title').textContent = kind ? 'Choose a page' : 'Link to a post or page';
  search.value = '';
  htmx.trigger(search, 'search');
  showDialog(dlg);
}
// event delegation, not a per-row onclick with an interpolated title -
// a title containing a quote (an apostrophe is common in a real post
// title) would break out of an inline onclick string; data-title/
// data-url sidestep that entirely
document.addEventListener('click', function (e) {
  var row = e.target.closest('.link-picker-row');
  if (!row) return;
  var dlg = document.getElementById('link-picker-dialog');
  if (dlg) dlg.close();
  var target = dlg.dataset.target;
  if (target === '__easymde_body__' && window._activeEasyMDE) {
    var cm = window._activeEasyMDE.codemirror;
    var selected = cm.getSelection();
    cm.replaceSelection('[' + (selected || row.dataset.title) + '](' + row.dataset.url + ')');
    cm.focus();
  } else if (target) {
    var input = document.getElementById(target);
    if (input && input.dataset.pickerKind) {
      input.value = row.dataset.slug;
      document.getElementById(target + '-title').value = row.dataset.title;
      input.dispatchEvent(new Event('input', {bubbles: true}));
      input.dispatchEvent(new Event('change', {bubbles: true}));
    } else if (input) { input.value = row.dataset.url; input.dispatchEvent(new Event('input', {bubbles: true})); }
  }
});
// a picker's ✕ (PageField, ClearPickedButton): its field emptied, as if typed
function clearPageField(name) {
  var input = document.getElementById(name);
  input.value = '';
  var title = document.getElementById(name + '-title');
  if (title) title.value = '';
  input.dispatchEvent(new Event('input', {bubbles: true}));
  input.dispatchEvent(new Event('change', {bubbles: true}));
}
