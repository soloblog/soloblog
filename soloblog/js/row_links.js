// A list whose rows open on a click anywhere (data-click-rows - the
// search page's results), as the link picker's rows do: not only the
// title. A click on a link of its own (a tag) still goes there, and one
// that ends a text selection doesn't open anything.
document.addEventListener('click', function (e) {
  var list = e.target.closest && e.target.closest('[data-click-rows]');
  if (!list || e.defaultPrevented || e.button !== 0 || e.target.closest('a, button, input, label')) return;
  if (String(window.getSelection && window.getSelection()).trim()) return;
  var row = e.target.closest('li, .card');
  var link = row && list.contains(row) && row.querySelector('h2 a[href], h3 a[href], a[href]');
  if (!link) return;
  if (e.metaKey || e.ctrlKey) window.open(link.href, '_blank');
  else location.href = link.href;
});
