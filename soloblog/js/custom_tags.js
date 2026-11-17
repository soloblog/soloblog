// What's set differently from its default (ui.CHANGED_BAR): a bar beside it
// and Reset, an icon, while it differs - before anything is saved.
// Post settings: a setting that follows the site carries the site's value in
// data-site-value - a choice is changed while it's set and isn't that value,
// a tick or switch while it isn't what the site does ("1" or "0"); Reset
// empties a choice, so it follows the site again. Each panel's heading
// counts them.
// Settings pages (SettingsForm): data-default-value, the starting style's
// value or Soloblog's - changed while it isn't that; Reset puts it back and
// it saves, like any change there.
function _isChanged(el) {
  if (el.hasAttribute('data-default-value')) {
    var d = el.getAttribute('data-default-value');
    if (el.type === 'checkbox') return el.checked !== (d === '1');
    if (el.type === 'radio') return el.checked && el.value !== d;
    return el.value !== d;
  }
  var site = el.getAttribute('data-site-value');
  return el.type === 'checkbox' ? el.checked !== (site === '1') : el.value !== '' && el.value !== site;
}
var _DEFAULTED = '[data-site-value], [data-default-value]';
function updateCustomTags(form) {
  form = form || document.getElementById('post-form');
  if (!form) return;
  form.querySelectorAll('[data-custom-field]').forEach(function (field) {
    var changed = [].some.call(field.querySelectorAll(_DEFAULTED), _isChanged);
    field.toggleAttribute('data-changed', changed);
    field.querySelectorAll('[data-custom-reset]').forEach(function (button) {
      button.classList.toggle('hidden', !changed);
    });
  });
  // a tick's own Default tag: the site shows it, and this page does too
  form.querySelectorAll('[data-default-field]').forEach(function (tick) {
    var box = tick.querySelector('[data-site-value]');
    var tag = tick.querySelector('[data-default-tag]');
    if (box && tag) tag.classList.toggle('hidden', _isChanged(box) || box.getAttribute('data-site-value') !== '1');
  });
  form.querySelectorAll('[data-custom-count]').forEach(function (count) {
    var panel = count.closest('details');
    var n = panel ? panel.querySelectorAll('[data-custom-field][data-changed]').length : 0;
    count.textContent = n ? ' · ' + n + ' changed' : '';
  });
}
// Reset: what differs in its field goes back to its default, and tells the
// form like any change - a list of ticks or a set of radios once, so it
// saves once
function customReset(button) {
  var field = button.closest('[data-custom-field]');
  if (!field) return;
  var moved = [];
  field.querySelectorAll(_DEFAULTED).forEach(function (el) {
    if (el.hasAttribute('data-default-value')) {
      var d = el.getAttribute('data-default-value');
      if (el.type === 'radio') {
        if (el.checked !== (el.value === d)) { el.checked = el.value === d; if (el.checked) moved.push(el); }
      } else if (el.type === 'checkbox') {
        if (el.checked !== (d === '1')) { el.checked = d === '1'; moved.push(el); }
      } else if (el.value !== d) { el.value = d; moved.push(el); }
      return;
    }
    if (!_isChanged(el)) return;
    if (el.type === 'checkbox') el.checked = el.getAttribute('data-site-value') === '1';
    else el.value = '';
    el.dispatchEvent(new Event('input', {bubbles: true}));
    el.dispatchEvent(new Event('change', {bubbles: true}));
  });
  var last = moved[moved.length - 1];
  if (last) {
    last.dispatchEvent(new Event('input', {bubbles: true}));
    last.dispatchEvent(new Event('change', {bubbles: true}));
  }
}
document.addEventListener('change', function (e) {
  var el = e.target;
  if (el.form && el.matches && el.matches(_DEFAULTED)) updateCustomTags(el.form);
});
// Discard puts the form back without a change event
document.addEventListener('reset', function (e) { setTimeout(function () { updateCustomTags(e.target); }); });
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('form').forEach(function (form) {
    if (form.querySelector('[data-custom-field]')) updateCustomTags(form);
  });
});
