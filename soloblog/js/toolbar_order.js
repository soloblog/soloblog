// Settings > Editor > Toolbar order: the ticked buttons, a list per
// section, in the same shape as SortableList (ui) - so SORTABLE_JS
// (app.py) handles dragging, the arrow buttons, and keeps each button in
// its own section. Each list has an order field of its own, unnamed; the
// sections joined, in order, are the one field that's saved. A newly
// ticked button joins the end of its section, an unticked one leaves.
document.addEventListener('DOMContentLoaded', function () {
  var container = document.getElementById('toolbar-order-list');
  if (!container) return;
  var field = document.getElementById('editor-toolbar-input');
  var labels = JSON.parse(container.dataset.labels);
  // the toolbar's own icons (editor_icons), so a row looks like its button
  var icons = JSON.parse(container.dataset.icons);
  var groups = JSON.parse(container.dataset.groups), sections = JSON.parse(container.dataset.sections);
  var always = container.dataset.always;

  function isChecked(key) {
    if (key === always) return true;
    var cb = document.querySelector('#toolbar-options input[name="tb_' + key + '"]');
    return !!(cb && cb.checked);
  }

  function row(key) {
    var li = document.createElement('li');
    li.dataset.key = key;
    li.className = 'flex items-center gap-2 p-2 rounded-box bg-base-100 border border-base-300';
    li.innerHTML =
      '<span data-sort-handle aria-hidden="true" data-tip="Drag to reorder" ' +
      'class="tooltip cursor-move opacity-40 select-none text-xs px-2 py-1.5 -my-1 touch-none max-[359px]:hidden">\u22ee\u22ee</span>' +
      '<span class="flex text-base-content/70">' + (icons[key] || '') + '</span>' +
      '<span class="text-sm flex-1 min-w-0"></span>' +
      (key === always ? '<span class="text-xs text-base-content/40">always on</span>' : '') +
      // Move up and down, as SortableList's (ui.SortMoves) - behind ⋯ on a phone
      container.dataset.moves.replace(/__ID__/g, 'toolbar-order-' + key);
    li.querySelector('.flex-1').textContent = labels[key] || key;
    return li;
  }

  // the order, each section's buttons together - as editor_config.pinned_from_setting
  function bySection(order) {
    return sections.reduce(function (all, name) {
      return all.concat(order.filter(function (key) { return groups[key] === name; }));
    }, []);
  }
  function save(order) {
    if (field.value === order.join(',')) return;
    field.value = order.join(',');
    field.dispatchEvent(new Event('input', { bubbles: true }));
  }
  function render(order) {
    order = order.filter(isChecked);
    if (order.indexOf(always) === -1) order.push(always);
    document.querySelectorAll('#toolbar-options input[type=checkbox]').forEach(function (cb) {
      var key = cb.name.slice(3);
      if (cb.checked && order.indexOf(key) === -1) order.push(key);
    });
    order = bySection(order);
    container.innerHTML = '';
    sections.forEach(function (name) {
      var keys = order.filter(function (key) { return groups[key] === name; });
      if (!keys.length) return;
      var part = document.createElement('div');
      var title = document.createElement('div');
      title.className = 'text-xs font-semibold text-base-content/60 mb-1';
      title.textContent = name;
      var list = document.createElement('ul');
      list.className = 'flex flex-col gap-1';
      list.setAttribute('data-sortable', '');
      keys.forEach(function (key) { list.appendChild(row(key)); });
      var own = document.createElement('input');
      own.type = 'hidden';
      own.setAttribute('data-sort-order', '');
      own.value = keys.join(',');
      // a move within this section: the sections joined again
      own.addEventListener('input', function (e) {
        e.stopPropagation();
        save([].map.call(container.querySelectorAll('li[data-key]'), function (li) { return li.dataset.key; }));
      });
      part.appendChild(title); part.appendChild(list); part.appendChild(own);
      container.appendChild(part);
    });
    save(order);
  }
  function current() { return field.value.split(',').filter(Boolean); }

  document.querySelectorAll('#toolbar-options input[type=checkbox]').forEach(function (cb) {
    cb.addEventListener('change', function () { render(current()); });
  });
  var resetBtn = document.getElementById('toolbar-reset-btn');
  if (resetBtn) {
    resetBtn.addEventListener('click', function () {
      document.querySelectorAll('#toolbar-options input').forEach(function (i) { i.checked = i.dataset.default === '1'; });
      render(container.dataset.defaultOrder.split(',').filter(Boolean));
    });
  }
  // Discard: the form puts the field back, the rows follow
  field.form.addEventListener('reset', function () { setTimeout(function () { render(current()); }); });

  render(current());
});
