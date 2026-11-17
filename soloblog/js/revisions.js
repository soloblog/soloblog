// History > Restore: puts an earlier version into the editor, unsaved -
// Save keeps it, Discard goes back to what's saved now
function restoreRevision(btn) {
  fetch('/admin/revisions/' + btn.dataset.revision)
    .then(function (r) { return r.ok ? r.json() : Promise.reject(); })
    .then(function (rev) {
      var title = document.querySelector('input[name=title]');
      if (title) { title.value = rev.title; title.dispatchEvent(new Event('input', { bubbles: true })); }
      if (window._activeEasyMDE) window._activeEasyMDE.value(rev.body);
      else document.getElementById('body-editor').value = rev.body;
      // a slide-over goes, to show the text; a card beside it stays
      if (typeof togglePostSettings === 'function' && !postSettingsDocked()) togglePostSettings(false);
      var status = document.getElementById('save-status');
      if (status) {
        status.textContent = 'Loaded the version from ' + btn.dataset.when + ' - Save to keep it';
        status.className = 'text-xs text-warning';
      }
    })
    .catch(function () { showStatus("Couldn't load that version", 'error'); });
}
