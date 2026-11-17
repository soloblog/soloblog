(function () {
  // An image with a dark mode or phone version (data-dark-src and
  // data-phone-src, images.with_other_versions) shows it while the page is
  // dark or on a phone - swapped as each image is parsed, and again when
  // the theme or the screen's width changes (the switcher, a phone turned
  // over). On a phone the phone version wins - its own dark mode version
  // (data-phone-dark-src) while the page is dark, if it has one. Runs
  // early, after the theme script when there is one, which sets data-scheme.
  var root = document.documentElement;
  var narrow = window.matchMedia && matchMedia('(max-width: 767px)');
  var OTHER = 'img[data-dark-src], img[data-phone-src]';
  function swap(img) {
    if (!img.hasAttribute('data-light-src')) {
      img.setAttribute('data-light-src', img.getAttribute('src') || '');
      img.setAttribute('data-light-srcset', img.getAttribute('srcset') || '');
    }
    var side = 'light', dark = root.getAttribute('data-scheme') === 'dark';
    if (narrow && narrow.matches && img.hasAttribute('data-phone-src')) {
      side = dark && img.hasAttribute('data-phone-dark-src') ? 'phone-dark' : 'phone';
    } else if (dark && img.hasAttribute('data-dark-src')) side = 'dark';
    var src = img.getAttribute('data-' + side + '-src'), set = img.getAttribute('data-' + side + '-srcset');
    if (img.getAttribute('src') === src) return;
    if (set) img.setAttribute('srcset', set); else img.removeAttribute('srcset');
    img.setAttribute('src', src);
  }
  function swapAll() { document.querySelectorAll(OTHER).forEach(swap); }
  new MutationObserver(function (changes) {
    changes.forEach(function (c) {
      c.addedNodes.forEach(function (n) {
        if (n.nodeType !== 1) return;
        if (n.matches(OTHER)) swap(n);
        else if (n.querySelector) n.querySelectorAll(OTHER).forEach(swap);
      });
    });
  }).observe(root, {childList: true, subtree: true});
  new MutationObserver(swapAll).observe(root, {attributes: true, attributeFilter: ['data-scheme']});
  if (narrow) narrow.addEventListener('change', swapAll);
  document.addEventListener('DOMContentLoaded', swapAll);
})();
