function openMediaPicker(targetInputId) {
  var dlg = document.getElementById('media-picker-dialog');
  if (!dlg) return;
  dlg.dataset.target = targetInputId;
  // the editor's Gallery button: clicks select several images instead
  // of using one straight away
  var galleryMode = targetInputId === '__gallery__';
  dlg.dataset.mode = galleryMode ? 'gallery' : '';
  window._gallerySel = [];
  dlg.querySelectorAll('.media-picker-row, .stock-picker-row').forEach(function (i) {
    i.classList.remove('ring-2', 'ring-primary', 'ring-offset-2');
    i.removeAttribute('aria-pressed');
    delete i.dataset.added;
  });
  dlg.querySelectorAll('.gallery-mode-only').forEach(function (el) { el.classList.toggle('hidden', !galleryMode); });
  // what the field takes: a sound field (data-picker-kind="audio") shows
  // your audio and uploads audio; anything else, images and stock photos
  var field = document.getElementById(targetInputId);
  var kind = field && field.dataset.pickerKind === 'audio' ? 'audio' : 'image';
  document.getElementById('media-picker-kind').value = kind;
  document.getElementById('media-picker-skip').value = (field && field.dataset.pickerSkip) || '';
  document.getElementById('media-picker-upload').accept = kind === 'audio' ? 'audio/*' : 'image/*';
  dlg.querySelectorAll('[data-images-only]').forEach(function (tab) { tab.hidden = kind !== 'image'; });
  var first = dlg.querySelector('input[name="media_picker_tab"]');
  if (first) first.checked = true;
  document.getElementById('media-picker-title').textContent = galleryMode ? 'Choose images for a gallery' :
    kind === 'audio' ? 'Choose a sound' : 'Choose an image';
  _syncGalleryCount();
  pickerStatus('', '');
  // your images, fresh each time (a new upload shows up) - the search
  // box's own request fills both grids
  htmx.trigger(document.getElementById('media-picker-search'), 'search');
  showDialog(dlg);
}
function _syncGalleryCount() {
  var n = (window._gallerySel || []).length;
  var count = document.getElementById('gallery-picker-count');
  if (count) count.textContent = n ? n + ' selected' : 'Click images to add them';
  var btn = document.getElementById('gallery-insert-btn');
  if (btn) btn.disabled = n === 0;
}
function _toggleGalleryPick(url, el) {
  var sel = window._gallerySel;
  var i = sel.indexOf(url);
  if (i === -1) sel.push(url); else sel.splice(i, 1);
  if (el) _ring(el, i === -1);
  _syncGalleryCount();
}
function _ring(el, on) {
  ['ring-2', 'ring-primary', 'ring-offset-2'].forEach(function (c) { el.classList.toggle(c, on); });
  el.setAttribute('aria-pressed', on ? 'true' : 'false');
}
// a search or "Show more" draws the grid again: what's chosen for the gallery stays marked
document.addEventListener('htmx:afterSettle', function () {
  var dlg = document.getElementById('media-picker-dialog');
  if (!dlg || dlg.dataset.mode !== 'gallery') return;
  var sel = window._gallerySel || [];
  dlg.querySelectorAll('.media-picker-row').forEach(function (row) {
    if (sel.indexOf(row.dataset.url) !== -1) _ring(row, true);
  });
});
function insertGallery() {
  var dlg = document.getElementById('media-picker-dialog');
  var sel = window._gallerySel || [];
  if (!sel.length || !window._activeEasyMDE) return;
  var style = document.getElementById('gallery-picker-style').value;
  var cm = window._activeEasyMDE.codemirror;
  // a fenced block needs its own lines
  var before = cm.getCursor().ch > 0 ? '\n\n' : '';
  cm.replaceSelection(before + '```gallery' + (style ? ' ' + style : '') + '\n' + sel.join('\n') + '\n```\n');
  cm.focus();
  dlg.close();
}
// the dialog's one inline status line (#media-picker-status, beside
// Upload) - uploads and stock imports both report here, no toast
function pickerStatus(text, cls) {
  var s = document.getElementById('media-picker-status');
  if (s) { s.textContent = text; s.className = 'text-xs ' + cls; }
}
// event delegation, not a per-thumbnail onclick="pickMedia('...')" with
// the url interpolated straight into a JS string literal - a filename
// (and so the /uploads/ url built from it) can contain an apostrophe,
// which would break out of that inline string; data-url on the
// thumbnail itself sidesteps it, same fix as LINK_PICKER_JS's
function applyPickedMedia(url, el) {
  var dlg = document.getElementById('media-picker-dialog');
  if (dlg.dataset.mode === 'gallery') { _toggleGalleryPick(url, el); return; }
  var target = dlg.dataset.target;
  if (target === '__easymde_body__' && window._activeEasyMDE) {
    var cm = window._activeEasyMDE.codemirror;
    cm.replaceSelection('![](' + url + ')');
    cm.focus();
  } else {
    var input = document.getElementById(target);
    if (input) { input.value = url; input.dispatchEvent(new Event('input', {bubbles: true})); }
  }
  dlg.close();
}
document.addEventListener('click', function (e) {
  var img = e.target.closest('.media-picker-row');
  if (img) applyPickedMedia(img.dataset.url, img);
});
// a picture is picked from the keyboard as a button is: Enter or Space
document.addEventListener('keydown', function (e) {
  if (e.key !== 'Enter' && e.key !== ' ') return;
  var img = e.target.closest && e.target.closest('img.media-picker-row, img.stock-picker-row');
  if (!img) return;
  e.preventDefault();
  img.click();
});
// a stock result isn't in the library yet - import it first (server
// downloads it into uploads, routes/media.py), then fill in the new
// /uploads/ url like any other pick.
document.addEventListener('click', function (e) {
  var img = e.target.closest('.stock-picker-row');
  if (!img || img.dataset.busy) return;
  // for a gallery, a second press takes it out again - not a second copy into the library
  if (img.dataset.added) { applyPickedMedia(img.dataset.added, img); return; }
  img.dataset.busy = '1';
  img.classList.add('opacity-50');
  pickerStatus('Adding to your library…', 'text-base-content/60');
  var data = new FormData();
  data.append('url', img.dataset.full);
  data.append('alt', img.dataset.alt || '');
  data.append('credit', img.dataset.credit || '');
  data.append('credit_url', img.dataset.creditUrl || '');
  data.append('source', img.dataset.source || '');
  data.append('download', img.dataset.download || '');
  fetch('/admin/media/import', { method: 'POST', body: data })
    .then(function (r) { return r.ok ? r.json() : Promise.reject(); })
    .then(function (r) {
      pickerStatus('', '');
      if (document.getElementById('media-picker-dialog').dataset.mode === 'gallery') img.dataset.added = r.url;
      applyPickedMedia(r.url, img);
    })
    .catch(function () { pickerStatus("Couldn't add that image", 'text-error'); })
    .finally(function () { delete img.dataset.busy; img.classList.remove('opacity-50'); });
});
// Upload inside the picker - the same /admin/upload-image endpoint the
// editor's own paste/drop upload uses (JSON back, no page reload), and
// the new image is used straight away, like picking it
function uploadToPicker(input) {
  var file = input.files[0];
  if (!file) return;
  pickerStatus('Uploading…', 'text-base-content/60');
  var data = new FormData();
  var kind = document.getElementById('media-picker-kind').value;
  data.append('image', file);
  data.append('kind', kind);
  fetch('/admin/upload-image', { method: 'POST', body: data })
    .then(function (r) { return r.ok ? r.json() : Promise.reject(); })
    .then(function (r) {
      pickerStatus('', '');
      applyPickedMedia(r.url);
      // for a gallery the picker stays open: the new one shows in the grid, chosen
      if (document.getElementById('media-picker-dialog').dataset.mode === 'gallery') {
        htmx.trigger(document.getElementById('media-picker-search'), 'search');
      }
    })
    .catch(function () {
      pickerStatus(kind === 'audio' ? 'Upload failed - an audio file (MP3, M4A, OGG, WAV or FLAC) only' :
                   'Upload failed - images up to 8MB only', 'text-error');
    })
    .finally(function () { input.value = ''; });
}
