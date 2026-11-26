// SortableList (ui): a row is dragged by its handle (only the handle,
// so text in its fields can still be selected) or moved with its arrow
// buttons. The hidden order field is updated and told, so the
// unsaved-changes warning notices; Discard puts the rows back.
(function () {
  var dragged = null;
  function save(list) {
    var field = list.parentElement.querySelector('[data-sort-order]');
    field.value = [].map.call(list.children, function (li) { return li.dataset.key; }).join(',');
    field.dispatchEvent(new Event('input', { bubbles: true }));
  }
  document.addEventListener('mousedown', function (e) {
    var handle = e.target.closest && e.target.closest('[data-sort-handle]');
    if (handle) handle.closest('li').draggable = true;
  });
  document.addEventListener('dragstart', function (e) {
    var li = e.target.closest && e.target.closest('[data-sortable] > li');
    if (li && li.draggable) { dragged = li; e.dataTransfer.effectAllowed = 'move'; }
  });
  document.addEventListener('dragover', function (e) {
    if (!dragged) return;
    var li = e.target.closest && e.target.closest('[data-sortable] > li');
    if (!li || li.parentElement !== dragged.parentElement) return;
    e.preventDefault();
    if (li === dragged) return;
    var r = li.getBoundingClientRect();
    li.parentElement.insertBefore(dragged, e.clientY - r.top < r.height / 2 ? li : li.nextSibling);
  });
  // A finger: phones don't do HTML drag and drop, so a row follows the
  // pointer from its handle instead (touch-none on the handle keeps the
  // page from scrolling meanwhile)
  var held = null;
  document.addEventListener('pointerdown', function (e) {
    if (e.pointerType === 'mouse') return;
    var handle = e.target.closest && e.target.closest('[data-sortable] [data-sort-handle]');
    if (!handle) return;
    held = handle.closest('li');
    held.classList.add('opacity-60');
    try { handle.setPointerCapture(e.pointerId); } catch (err) {}
    e.preventDefault();
  });
  document.addEventListener('pointermove', function (e) {
    if (!held) return;
    var over = document.elementFromPoint(e.clientX, e.clientY);
    var li = over && over.closest('[data-sortable] > li');
    if (!li || li === held || li.parentElement !== held.parentElement) return;
    var r = li.getBoundingClientRect();
    li.parentElement.insertBefore(held, e.clientY - r.top < r.height / 2 ? li : li.nextSibling);
  });
  function letGo() {
    if (!held) return;
    held.classList.remove('opacity-60');
    save(held.parentElement);
    held = null;
  }
  document.addEventListener('pointerup', letGo);
  document.addEventListener('pointercancel', letGo);
  document.addEventListener('dragend', function () {
    if (!dragged) return;
    dragged.draggable = false;
    save(dragged.parentElement);
    dragged = null;
  });
  document.addEventListener('click', function (e) {
    var btn = e.target.closest && e.target.closest('[data-sort-move]');
    if (!btn) return;
    var li = btn.closest('li'), list = li.parentElement;
    if (btn.dataset.sortMove === 'up' && li.previousElementSibling) list.insertBefore(li, li.previousElementSibling);
    if (btn.dataset.sortMove === 'down' && li.nextElementSibling) list.insertBefore(li.nextElementSibling, li);
    save(list);
    btn.focus();
  });
  document.addEventListener('reset', function (e) {
    setTimeout(function () {
      e.target.querySelectorAll('[data-sortable]').forEach(function (list) {
        var field = list.parentElement.querySelector('[data-sort-order]');
        field.value.split(',').forEach(function (key) {
          var li = list.querySelector(':scope > li[data-key="' + key + '"]');
          if (li) list.appendChild(li);
        });
      });
    });
  }, true);
})();

// Settings forms (data-declare-fields): "Unsaved changes" beside Save
// as soon as anything differs from what's saved - gone again if it's
// put back - and a warning before leaving the page with it unsaved,
// like the post editor. A save re-baselines (rebaselineForm, above).
function settingsFormDirty(form) {
  var autosave = form.hasAttribute('data-autosave');
  return [].some.call(form.elements, function (f) {
    if (!f.name || f.disabled) return false;
    // it saves as it changes (AUTOSAVE_JS) - never left unsaved
    if (autosave && _autosaves(f)) return false;
    if (f.type === 'checkbox' || f.type === 'radio') return f.checked !== f.defaultChecked;
    if (f.tagName === 'SELECT') return [].some.call(f.options, function (o) { return o.selected !== o.defaultSelected; });
    return f.type !== 'hidden' && 'defaultValue' in f && f.value !== f.defaultValue;
  });
}
// anything unsaved on the page: floating buttons move up over the save bar
// (ScrollToTopButton) - an attribute here, not body:has([data-dirty]),
// which restyled the whole page on every change
function syncUnsaved() {
  document.documentElement.toggleAttribute('data-unsaved', !!document.querySelector('form[data-dirty]'));
}
function syncSettingsDirty(form) {
  var dirty = settingsFormDirty(form);
  form.toggleAttribute('data-dirty', dirty);
  syncUnsaved();
  // the Save bar's own line, where Save and Discard are - not a status of
  // an action inside the form (Send a test email), which comes first
  var status = form.querySelector('#save-status') || form.querySelector('[data-status-slot]');
  if (!status) return;
  if (dirty) {
    status.textContent = 'Unsaved changes';
    paintStatus(status, 'text-warning');
  } else if (status.textContent === 'Unsaved changes') {
    status.textContent = '';
  }
}
['input', 'change'].forEach(function (type) {
  document.addEventListener(type, function (e) {
    var form = e.target.form;
    if (form && form.hasAttribute('data-declare-fields')) syncSettingsDirty(form);
  });
});
// Leaving with unsaved changes (a settings form, or the editor's
// window.editorDirty). A link inside the site asks in the app's own
// dialog; closing the tab or going to
// another site gets the browser's warning - which no page can style or
// word, on purpose.
function unsavedChanges() {
  return !!document.querySelector('form[data-declare-fields][data-dirty]') ||
         (typeof window.editorDirty === 'function' && window.editorDirty());
}
document.addEventListener('click', function (e) {
  var a = e.target.closest && e.target.closest('a[href]');
  if (!a || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || a.target === '_blank') return;
  var url = new URL(a.href, location.href);
  // another site, a download, or a jump within this page: not ours to ask about
  if (url.origin !== location.origin || a.hasAttribute('download') ||
      (url.pathname === location.pathname && url.search === location.search)) return;
  if (!unsavedChanges()) return;
  e.preventDefault();
  e.stopPropagation();
  confirmAction(_t('Save changes before you leave?'), function () {
    window._leaving = true;
    location.href = a.href;
  }, _t('Discard'), function () { saveThenLeave(a.href); }, _t('Save'));
}, true);
// Save (and leave): the form saves the way its own Save button does, and
// only a save the server accepted goes on - a red "couldn't save" (a
// taken URL, a missing field) stays here with it, nothing lost. A green
// status or a redirect (a new post's first save) is accepted; the page
// isn't updated with it, since it's being left.
function saveThenLeave(href) {
  var form = (typeof window.editorDirty === 'function' && window.editorDirty() && document.getElementById('post-form')) ||
             document.querySelector('form[data-declare-fields][data-dirty]');
  if (!form) { window._leaving = true; location.href = href; return; }
  if (!form.checkValidity()) { form.requestSubmit(); return; }  // says which field, beside Save
  var done = function () {
    form.removeEventListener('htmx:beforeOnLoad', onLoad);
    form.removeEventListener('htmx:sendError', done);
  };
  var onLoad = function (e) {
    if (e.detail.elt !== form) return;
    done();
    var xhr = e.detail.xhr, ok = xhr.status >= 200 && xhr.status < 300 && xhr.responseText.indexOf('text-error') === -1;
    if (!ok) return;
    e.preventDefault();
    window._leaving = true;
    location.href = href;
  };
  form.addEventListener('htmx:beforeOnLoad', onLoad);
  form.addEventListener('htmx:sendError', done);  // offline: nothing to wait for, and the next Save mustn't leave
  form.requestSubmit();
}
window.addEventListener('beforeunload', function (e) {
  if (window._leaving) return;
  if (document.querySelector('form[data-declare-fields][data-dirty]')) { e.preventDefault(); e.returnValue = ''; }
});
