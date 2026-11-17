// Yes sends the form with requestSubmit(), not submit(): submit() skips
// the 'submit' event, which SCROLL_RESTORE_JS needs to keep your place
var _confirmCallback = null;
// yesLabel - what the button that goes ahead says: the action's own name
// ("Move to trash", "Delete forever"), not a bare "Confirm"
// hx-confirm (a button that posts with htmx, not a form) asks in the same
// dialog as data-confirm, instead of the browser's own confirm()
document.addEventListener('htmx:confirm', function (e) {
  if (!e.detail.question) return;
  e.preventDefault();
  var el = e.detail.elt;
  confirmAction(e.detail.question, function () { e.detail.issueRequest(true); },
                el.getAttribute('aria-label') || el.textContent.trim());
});

// A form the browser won't send (a required field left empty, an email
// without an @): say so beside its buttons. A phone's browser shows its
// own bubble badly, or not at all, so a tap on Send just seemed to do
// nothing. An empty field is named - the browser's "Please fill out this
// field" doesn't say which one, away from its bubble; anything else is
// in the browser's own words and language.
function _fieldName(field) {
  var legend = field.closest('fieldset') && field.closest('fieldset').querySelector('legend');
  return field.getAttribute('aria-label') || (legend && legend.textContent.trim()) || '';
}
document.addEventListener('invalid', function (e) {
  var field = e.target, form = field.form;
  if (!form) return;
  // in Post settings while it's closed: open it, so the field can be shown
  if (field.closest('#post-settings-panel[inert]') && typeof togglePostSettings === 'function') togglePostSettings(true);
  // the first field wrong is the one the message is about
  if (form._invalidAt && Date.now() - form._invalidAt < 100) return;
  form._invalidAt = Date.now();
  // beside Save and Discard when the form has them (as syncSettingsDirty)
  var slot = form.querySelector('#save-status') || form.querySelector('[data-status-slot]');
  if (!slot) return;
  var name = field.validity.valueMissing && _fieldName(field);
  slot.textContent = name ? _t('{field} is required').replace('{field}', name)
                          : field.validationMessage.replace(/[.。]$/, '');
  slot.className = 'text-xs text-error';
}, true);

// onSave: a third button, the main one, for when there's something to
// save first (leaving with unsaved changes) - Yes then steps back to a
// soft red, so only one button is filled
var _saveCallback = null;
function confirmAction(message, onYes, yesLabel, onSave, saveLabel) {
  var dlg = document.getElementById('confirm-dialog');
  if (!dlg) { if (onYes) onYes(); return; }
  document.getElementById('confirm-message').textContent = message;
  document.getElementById('confirm-yes-label').textContent = yesLabel || _t('Confirm');
  var saveBtn = document.getElementById('confirm-save-btn');
  if (saveBtn) {
    saveBtn.hidden = !onSave;
    document.getElementById('confirm-save-label').textContent = saveLabel || _t('Save');
    document.getElementById('confirm-yes-btn').classList.toggle('btn-soft', !!onSave);
    saveBtn.parentNode.toggleAttribute('data-stack', !!onSave);
  }
  _confirmCallback = onYes;
  _saveCallback = onSave || null;
  dlg.showModal();
}
document.addEventListener('DOMContentLoaded', function () {
  var yesBtn = document.getElementById('confirm-yes-btn');
  if (!yesBtn) return;
  yesBtn.onclick = function () {
    document.getElementById('confirm-dialog').close();
    if (_confirmCallback) _confirmCallback();
    _confirmCallback = null;
  };
  var saveBtn = document.getElementById('confirm-save-btn');
  if (saveBtn) saveBtn.onclick = function () {
    document.getElementById('confirm-dialog').close();
    if (_saveCallback) _saveCallback();
    _saveCallback = null;
  };
});
