// A list whose rows open on a click anywhere (data-click-rows - the
// blog roll, search results, related posts), as the link picker's rows
// do: not only the title. A row is a list item, a card, or anything
// marked data-click-row (a post's picture card). A click on a link of its
// own (a tag) still goes there, and one that ends a text selection
// doesn't open anything. Ctrl, Cmd or the middle button opens it in a
// new tab, as on the title itself.
function _rowLink(e) {
  var list = e.target.closest && e.target.closest('[data-click-rows]');
  if (!list || e.defaultPrevented || e.target.closest('a, button, input, label')) return null;
  if (String(window.getSelection && window.getSelection()).trim()) return null;
  var row = e.target.closest('[data-click-row], li, .card');
  return row && list.contains(row) && row.querySelector('h2 a[href], h3 a[href], a[href]');
}
document.addEventListener('click', function (e) {
  if (e.button !== 0) return;
  var link = _rowLink(e);
  if (!link) return;
  if (e.metaKey || e.ctrlKey) window.open(link.href, '_blank');
  else location.href = link.href;
});
document.addEventListener('auxclick', function (e) {
  if (e.button !== 1) return;
  var link = _rowLink(e);
  if (link) window.open(link.href, '_blank');
});
