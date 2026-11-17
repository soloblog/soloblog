// Settings pages (SettingsForm, data-autosave): a switch, a choice or a
// picker saves the moment it changes - just that setting, posted to the
// page's own save - with Undo beside "Saved". What's typed waits for
// Save. A group inside [data-autosave-off] (a service and its key, a
// palette pair) is saved together, with Save.
function _autosaves(f) {
  if (!f.name || f.disabled || f.closest('[data-autosave-off]')) return false;
  return f.type === 'checkbox' || f.type === 'radio' || f.tagName === 'SELECT' ||
         f.hasAttribute('data-autosave');
}
function _fieldsNamed(form, name) {
  return [].filter.call(form.elements, function (x) { return x.name === name; });
}
function _snapshot(fields) {
  return fields.map(function (x) {
    return {el: x, checked: x.defaultChecked, value: x.defaultValue,
            selected: x.tagName === 'SELECT' ? [].map.call(x.options, function (o) { return o.defaultSelected; }) : null};
  });
}
// what a snapshot holds, to compare two
function _snapKey(snapshot) {
  return JSON.stringify(snapshot.map(function (b) { return [b.checked, b.value, b.selected]; }));
}
function _restore(snapshot) {
  snapshot.forEach(function (b) {
    if (b.el.type === 'checkbox' || b.el.type === 'radio') b.el.checked = b.checked;
    else if (b.selected) [].forEach.call(b.el.options, function (o, i) { o.selected = b.selected[i]; });
    else b.el.value = b.value;
  });
}
// "Saved" goes beside what changed - in its panel's heading, on the
// right - not in the Save bar at the page's foot
function _autosaveSlot(form, name) {
  var field = _fieldsNamed(form, name)[0], panel = field && field.closest('details[data-panel]');
  var summary = panel && panel.querySelector('summary');
  if (!summary) return form.querySelector('#save-status');
  var slot = summary.querySelector('[data-autosave-status]');
  if (!slot) {
    slot = document.createElement('span');
    slot.setAttribute('data-autosave-status', '');
    slot.setAttribute('aria-live', 'polite');
    summary.classList.add('flex', 'items-center', 'gap-3');
    summary.appendChild(slot);
  }
  return slot;
}
function autosaveField(form, name, undoing) {
  var fields = _fieldsNamed(form, name), before = _snapshot(fields);
  // how it was when the page opened - put back there, there's nothing to undo
  form._opened = form._opened || {};
  if (!(name in form._opened)) form._opened[name] = _snapKey(before);
  var data = new FormData();
  new FormData(form).getAll(name).forEach(function (v) { data.append(name, v); });
  data.append('declared_fields', name);
  var status = _autosaveSlot(form, name);
  fetch(form.getAttribute('hx-post'), {method: 'POST', body: data, headers: {'HX-Request': 'true'}})
    .then(function (r) { return r.text(); })
    .then(function (html) {
      var box = document.createElement('div');
      box.innerHTML = html;
      var answer = box.firstElementChild;
      var ok = answer && answer.classList.contains('text-success');
      if (ok) {
        fields.forEach(function (x) {
          if (x.type === 'checkbox' || x.type === 'radio') x.defaultChecked = x.checked;
          else if (x.tagName === 'SELECT') [].forEach.call(x.options, function (o) { o.defaultSelected = o.selected; });
          else x.defaultValue = x.value;
        });
      }
      // the page's frame changed (a new header): reload to show it - unless
      // there's typing still to save, which a reload would lose
      if (answer && answer.hasAttribute('data-reload') && !document.querySelector('form[data-declare-fields][data-dirty]')) {
        try { sessionStorage.setItem('soloblog-saved', answer.textContent); } catch (e) {}
        window._leaving = true;
        location.reload();
        return;
      }
      if (status) {
        status.className = (answer ? answer.className : 'text-xs text-error') + ' ms-auto me-6 font-normal';
        status.textContent = answer ? answer.textContent : 'Not saved - try again';
        var back = _snapKey(_snapshot(fields)) === form._opened[name];
        if (ok && !undoing && !back) {
          var undo = document.createElement('button');
          undo.type = 'button';
          undo.className = 'link ml-2';
          undo.textContent = _t('Undo');
          undo.addEventListener('click', function (e) {
            // in a panel's heading: undo, don't fold the panel
            e.preventDefault();
            e.stopPropagation();
            _restore(before);
            autosaveField(form, name, true);
          });
          status.appendChild(undo);
        }
        var shown = status.textContent;
        clearTimeout(status._fade);
        status._fade = setTimeout(function () { if (status.textContent === shown) status.textContent = ''; }, 8000);
      }
      syncSettingsDirty(form);
      _syncShownFor(form);
      // Undo puts a value back without a change event
      if (typeof updateCustomTags === 'function') updateCustomTags(form);
    })
    .catch(function () {
      if (status) { status.className = 'text-xs text-error self-center'; status.textContent = 'Not saved - check your connection'; }
    });
}
document.addEventListener('change', function (e) {
  var f = e.target, form = f.form;
  if (!form || !form.hasAttribute('data-autosave') || !_autosaves(f)) return;
  autosaveField(form, f.name);
});
