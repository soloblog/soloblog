(function () {
  // a returning visitor's own theme choice (from the switcher in the
  // nav) beats the site's default; otherwise a device in dark mode gets
  // the site's dark theme, if it has one (data-dark-theme), and follows
  // the device if it switches. Applied before the stylesheet loads, so
  // there's no flash of the other theme first.
  var root = document.documentElement;
  function chosen() { try { return localStorage.getItem('theme'); } catch (e) { return null; } }
  var dark = root.getAttribute('data-dark-theme'), light = root.getAttribute('data-theme');
  var query = window.matchMedia && matchMedia('(prefers-color-scheme: dark)');
  // the site's own: its light theme, or its dark one when the device is dark
  window.siteTheme = function () { return dark && query && query.matches ? dark : light; };
  function follow() {
    if (chosen()) return;
    root.setAttribute('data-theme', window.siteTheme());
    // known before the stylesheet is: the dark theme is dark
    if (dark) root.setAttribute('data-scheme', root.getAttribute('data-theme') === dark ? 'dark' : 'light');
  }
  if (chosen()) root.setAttribute('data-theme', chosen()); else follow();
  if (dark && query) query.addEventListener('change', follow);

  // a theme chosen in the switcher could be either: once the stylesheet
  // has it, the page itself says
  function measure() {
    var scheme = getComputedStyle(root).colorScheme === 'dark' ? 'dark' : 'light';
    if (root.getAttribute('data-scheme') !== scheme) root.setAttribute('data-scheme', scheme);
  }
  new MutationObserver(function () { requestAnimationFrame(measure); })
    .observe(root, {attributes: true, attributeFilter: ['data-theme']});
  document.addEventListener('DOMContentLoaded', measure);
})();
