// Settings > Appearance > Reading > Footnotes beside the text:
// on a wide screen each footnote sits in the margin beside the line that
// refers to it, as long reads set them - in a margin no side panel is
// using (placeSidePanels), the right one first. With no room, a reference
// folded away, or for print, they stay at the foot as they were.
(function () {
  var ROOM = 14.5;  // rem: a 12rem note and the gap before it, as a side panel
  function place() {
    if (!document.documentElement.hasAttribute('data-sidenotes')) return;
    var rem = parseFloat(getComputedStyle(document.documentElement).fontSize);
    var width = document.documentElement.clientWidth;
    var taken = function (side) { return !!document.querySelector('[data-side-panel="' + side + '"][data-beside]'); };
    document.querySelectorAll('.prose').forEach(function (prose) {
      var foot = [].filter.call(prose.children, function (el) { return el.classList.contains('footnote'); })[0];
      if (!foot) return;
      prose.querySelectorAll('.sidenote').forEach(function (note) { note.remove(); });
      foot.hidden = false;
      var box = prose.getBoundingClientRect();
      var side = !taken('right') && width - box.right >= ROOM * rem ? 'right'
               : !taken('left') && box.left >= ROOM * rem ? 'left' : null;
      if (!side || matchMedia('print').matches) return;
      prose.classList.add('relative');
      var below = -Infinity, placed = 0;
      prose.querySelectorAll('a.footnote-ref').forEach(function (ref) {
        var item = document.getElementById(decodeURIComponent(ref.hash.slice(1)));
        // its section folded away - a daisyUI collapse keeps a closed
        // <details> laid out for its animation, and only hides it
        var shown = !ref.closest('details:not([open])') &&
                    (ref.checkVisibility ? ref.checkVisibility({ visibilityProperty: true }) : !!ref.offsetParent);
        if (!item || !foot.contains(item) || !shown) return;
        var note = document.createElement('aside');
        note.className = 'sidenote not-prose absolute w-48 text-xs leading-snug text-base-content/70 ' +
                         '[&_p]:inline [&_a]:link print:hidden transition-colors';
        note.setAttribute('role', 'note');
        note.dataset.for = item.id;
        var number = document.createElement('span');
        number.className = 'font-semibold text-base-content mr-1';
        number.textContent = ref.textContent;
        note.appendChild(number);
        [].forEach.call(item.childNodes, function (child) { note.appendChild(child.cloneNode(true)); });
        note.querySelectorAll('.footnote-backref').forEach(function (back) { back.remove(); });
        prose.appendChild(note);
        // level with its line, or just under the note before it
        var top = Math.max(ref.getBoundingClientRect().top - box.top - 2, below + 8);
        note.style.top = top + 'px';
        note.style[side === 'right' ? 'left' : 'right'] = 'calc(100% + 2rem)';
        below = top + note.offsetHeight;
        placed++;
      });
      // every one beside its line: the list at the foot isn't needed -
      // except on paper, where the margin notes aren't printed
      if (placed && placed === foot.querySelectorAll('li[id]').length) {
        foot.hidden = true;
        foot.classList.add('print:block');
      }
    });
  }
  // many at once (a resize, images loading) make one placing
  var timer = null;
  function later() {
    clearTimeout(timer);
    timer = setTimeout(place, 50);
  }
  document.addEventListener('DOMContentLoaded', function () {
    place();
    // images and fonts change where each line is; a section folds
    document.querySelectorAll('.prose').forEach(function (prose) {
      if (window.ResizeObserver) new ResizeObserver(later).observe(prose);
    });
  });
  window.addEventListener('load', later);
  window.addEventListener('resize', later);
  document.addEventListener('toggle', later, true);
  // a reference beside its note: no jump to the foot, the note lights up
  document.addEventListener('click', function (e) {
    var ref = e.target.closest && e.target.closest('a.footnote-ref');
    var note = ref && document.querySelector('.sidenote[data-for="' + CSS.escape(decodeURIComponent(ref.hash.slice(1))) + '"]');
    if (!note) return;
    e.preventDefault();
    note.classList.add('text-base-content');
    setTimeout(function () { note.classList.remove('text-base-content'); }, 1200);
  });
})();
