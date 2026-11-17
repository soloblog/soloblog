// after a real successful save, "discard unsaved changes" (Cancel,
// below) has to mean "go back to what was just saved" - not "go back
// to whatever the page happened to show on its very first load", which
// is all form.reset() alone knows how to do (it only ever reverts to
// each field's original defaultValue/defaultChecked). This re-stamps
// those defaults to match what was just persisted, so a save/edit/
// cancel cycle repeated any number of times always lands on the right
// baseline. Skipped on a failed save (text-error) - nothing was
// actually persisted then, so the previous baseline is still correct.
function rebaselineForm(form) {
  [].forEach.call(form.elements, function (field) {
    if (field.type === 'checkbox' || field.type === 'radio') {
      field.defaultChecked = field.checked;
    } else if (field.tagName === 'SELECT') {
      [].forEach.call(field.options, function (o) { o.defaultSelected = o.selected; });
    } else if ('defaultValue' in field) {
      field.defaultValue = field.value;
    }
  });
}

// on document: these scripts run in <head>, before there's a body
// A save's answer replaces #save-status (outerHTML). Until htmx has
// settled the swap, the new one still wears the old one's classes (htmx
// carries them over, then settles to the new) - so this waits for
// afterSettle, then finds its form. Done: what's on screen is now saved.
document.addEventListener('htmx:afterSettle', function (e) {
  // or a form's own slot (data-status-slot), as Email > Admin email has
  var t = e.detail.target;
  if (!t || (t.id !== 'save-status' && !(t.hasAttribute && t.hasAttribute('data-status-slot')))) return;
  var el = document.getElementById(t.id);
  // data-saved: saved even though the message is an error (a test email that didn't go)
  var form = el && (el.classList.contains('text-success') || el.hasAttribute('data-saved')) && el.closest('form');
  if (!form) return;
  rebaselineForm(form);
  form.removeAttribute('data-dirty');
  // admin.js's - not on a visitor's page, where the contact form saves
  if (typeof syncUnsaved === 'function') syncUnsaved();
});

// the public comment form (routes/public.py) - the swap carries the
// confirmation text itself ("Posted for approval"), and this is what
// resets the form: there's no Cancel/discard concept here, and a fresh
// visitor's next comment shouldn't still have their last one sitting
// in the fields once "Posted for approval" shows up.
// afterSettle: until then htmx keeps the old status's classes on the new one
document.addEventListener('htmx:afterSettle', function (e) {
  var el = e.target;
  if (!el || el.id !== 'comment-status') return;
  // an error (the spam check, a mistyped email) keeps what they wrote
  var status = document.getElementById('comment-status');
  if (status && status.classList.contains('text-error')) return;
  var form = document.getElementById('comment-form');
  if (form) form.reset();
});

// Cancel (CancelButton, ui) - discards unsaved edits in place, the
// same way Save applies them in place: no navigation, no page reload,
// no scroll jump. form.reset() handles every plain field correctly on
// its own; two things here keep state outside the form fields
// themselves and need an explicit nudge back into sync after that:
// EasyMDE's rendered view of the post body (it mirrors the real
// textarea but doesn't listen for a native reset event), and the post
// editor's pin-location-dependent parent-page field (its visibility
// isn't itself a form field).
function discardForm(btn) {
  var form = btn.closest('form');
  if (!form) return;
  // the post's text changed since it was saved: asked first - it's writing
  var text = document.getElementById('body-editor');
  if (window._activeEasyMDE && text && form.contains(text) && window._activeEasyMDE.value() !== text.defaultValue &&
      !btn.hasAttribute('data-asked')) {
    confirmAction('Discard your changes? The post goes back to how it was last saved.', function () {
      btn.setAttribute('data-asked', '');
      try { discardForm(btn); } finally { btn.removeAttribute('data-asked'); }
    }, 'Discard');
    return;
  }
  form.reset();
  if (window._activeEasyMDE) {
    var el = document.getElementById('body-editor');
    // .value() drives CodeMirror's own setValue, which fires a
    // 'change' event just like a real edit would - the post editor's
    // dirty-tracking (EDITOR_INIT_JS) reacts to that before
    // _clearFormDirty below gets a chance to run, which is exactly why
    // that call comes after this, not before.
    if (el) window._activeEasyMDE.value(el.defaultValue);
  }
  var pinLocation = document.getElementById('pin_location');
  if (pinLocation && typeof updateParentField === 'function') updateParentField(pinLocation.value);
  if (typeof window._clearFormDirty === 'function') window._clearFormDirty();
  form.removeAttribute('data-dirty');
  if (typeof syncUnsaved === 'function') syncUnsaved();
  // replaces whatever "Unsaved changes" warning was showing (markDirty,
  // EDITOR_INIT_JS) - inline, in the same spot Save confirms in
  var status = document.getElementById('save-status');
  if (status) { status.textContent = 'Discarded'; status.className = 'text-xs text-base-content/60'; }
}
