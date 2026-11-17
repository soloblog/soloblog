// Every daisyUI <select> opens the same list as a Combobox (ui) - a
// browser draws its own list for a plain select, so one dropdown looked
// nothing like the next. The select stays, hidden, and holds the value:
// forms, Save, autosave and what shows for each choice read it as before.
// A select can keep the browser's own with data-native.
var _styledSelects = 0;
function styleSelect(sel) {
  if (sel.hasAttribute('data-styled') || sel.multiple || sel.size > 1 || sel.hasAttribute('data-native')) return;
  sel.setAttribute('data-styled', '');
  var id = 'select-list-' + (++_styledSelects);
  var button = document.createElement('button');
  button.type = 'button';
  button.className = sel.className + ' text-left font-normal min-w-0';
  button.setAttribute('popovertarget', id);
  button.setAttribute('aria-haspopup', 'listbox');
  // its name, then the choice that shows - a screen reader says both, and
  // what it says starts with what's on the button
  var named = sel.getAttribute('aria-label') || (sel.labels && sel.labels[0] && sel.labels[0].textContent.trim());
  var shown = document.createElement('span');
  shown.className = 'truncate min-w-0';
  if (named) {
    var said = document.createElement('span');
    said.className = 'sr-only';
    said.textContent = named + ', ';
    button.appendChild(said);
  }
  button.appendChild(shown);
  var list = document.createElement('ul');
  list.id = id;
  list.setAttribute('popover', 'auto');
  list.setAttribute('role', 'listbox');
  var glass = document.documentElement.hasAttribute('data-glass') ? 'glass-fill glass-blur' : 'bg-base-100';
  list.className = 'dropdown-content menu menu-sm flex-nowrap rounded-box border border-base-300 shadow-lg p-2 ' +
    'max-h-72 overflow-y-auto max-w-[calc(100vw-2rem)] ' + glass;
  function sync() {
    var o = sel.options[sel.selectedIndex];
    shown.textContent = o ? o.textContent : '';
    button.disabled = sel.disabled;
  }
  function item(o) {
    var li = document.createElement('li'), b = document.createElement('button');
    b.type = 'button';
    b.textContent = o.textContent;
    // the choice a new site starts with (ui.DEFAULT_TAG)
    if (o.hasAttribute('data-default')) {
      var tag = document.createElement('span');
      tag.className = 'badge badge-ghost badge-xs shrink-0 ms-auto';
      tag.textContent = 'Default';
      b.appendChild(tag);
    }
    b.setAttribute('role', 'option');
    b.setAttribute('aria-selected', o.selected ? 'true' : 'false');
    if (o.selected) b.className = 'menu-active';
    if (o.disabled) { b.disabled = true; li.className = 'menu-disabled'; }
    b.addEventListener('click', function () {
      sel.value = o.value;
      sel.dispatchEvent(new Event('input', {bubbles: true}));
      sel.dispatchEvent(new Event('change', {bubbles: true}));
      list.hidePopover();
      button.focus();
    });
    li.appendChild(b);
    return li;
  }
  function build() {
    list.textContent = '';
    [].forEach.call(sel.children, function (node) {
      if (node.tagName === 'OPTGROUP') {
        var title = document.createElement('li');
        title.className = 'menu-title';
        title.textContent = node.label;
        list.appendChild(title);
        [].forEach.call(node.children, function (o) { list.appendChild(item(o)); });
      } else if (node.tagName === 'OPTION') list.appendChild(item(node));
    });
  }
  list.addEventListener('toggle', function (e) {
    if (e.newState !== 'open') return;
    var chosen = list.querySelector('.menu-active') || list.querySelector('button:not([disabled])');
    if (chosen) { chosen.scrollIntoView({block: 'nearest'}); chosen.focus(); }
  });
  button.addEventListener('click', build, true);
  // up and down move through the choices, as in the browser's own list
  list.addEventListener('keydown', function (e) {
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
    var all = [].slice.call(list.querySelectorAll('button:not([disabled])'));
    var at = all.indexOf(document.activeElement);
    var next = all[Math.min(all.length - 1, Math.max(0, at + (e.key === 'ArrowDown' ? 1 : -1)))];
    if (next) { e.preventDefault(); next.focus(); }
  });
  sel.addEventListener('change', sync);
  // Discard puts the form back without a change event
  if (sel.form) sel.form.addEventListener('reset', function () { setTimeout(sync, 0); });
  sel.hidden = true;
  sel.after(button, list);
  sync();
}
function styleSelects(root) {
  (root || document).querySelectorAll('select.select').forEach(styleSelect);
}
document.addEventListener('DOMContentLoaded', function () { styleSelects(); });
document.addEventListener('htmx:afterSettle', function (e) { styleSelects(e.target); });
