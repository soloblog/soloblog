// Another comment system in place of Soloblog's own (extcomments.py).
// Nothing loads from it until loadComments runs: on a click, or when
// the box nears the screen if the admin chose that.
function _commentsDark() { return getComputedStyle(document.documentElement).colorScheme === 'dark'; }
function _extScript(src, attrs) {
  var s = document.createElement('script');
  s.src = src; s.async = true;
  Object.keys(attrs || {}).forEach(function (k) { s.setAttribute(k, attrs[k]); });
  return s;
}
function _giscusTheme(d) {
  var name = document.documentElement.getAttribute('data-theme') || d.theme;
  return d.themeUrl ? d.themeUrl + '?t=' + encodeURIComponent(name) : (_commentsDark() ? 'dark' : 'light');
}
var _EXT_COMMENTS = {
  giscus: function (box, d) {
    box.appendChild(_extScript('https://giscus.app/client.js', {
      'data-repo': d.repo, 'data-repo-id': d.repoId, 'data-category': d.category,
      'data-category-id': d.categoryId, 'data-mapping': 'pathname', 'data-reactions-enabled': '1',
      'data-input-position': 'top', 'data-theme': _giscusTheme(d), 'data-lang': d.lang,
      'data-loading': 'lazy', 'crossorigin': 'anonymous'}));
  },
  isso: function (box, d) {
    var t = document.createElement('section');
    t.id = 'isso-thread';
    t.setAttribute('data-isso-id', d.path);
    t.setAttribute('data-title', d.title);
    box.appendChild(t);
    box.appendChild(_extScript(d.host + '/js/embed.min.js', {'data-isso': d.host + '/', 'data-isso-lang': d.lang,
      'data-isso-vote': 'true', 'data-isso-reply-notifications': 'true'}));
  },
  remark42: function (box, d) {
    var el = document.createElement('div');
    el.id = 'remark42';
    box.appendChild(el);
    window.remark_config = {host: d.host, site_id: d.site, url: d.url, page_title: d.title, locale: d.lang,
      theme: _commentsDark() ? 'dark' : 'light', components: ['embed'], no_footer: true};
    var s = _extScript(d.host + '/web/embed.mjs');
    s.type = 'module';
    box.appendChild(s);
  },
};
function loadComments(el) {
  var box = el.closest('[data-ext-comments]');
  if (!box || box.dataset.loaded) return;
  box.dataset.loaded = '1';
  box.className = 'w-full';
  box.replaceChildren();
  _EXT_COMMENTS[box.dataset.extComments](box, box.dataset);
}
document.addEventListener('DOMContentLoaded', function () {
  var boxes = document.querySelectorAll('[data-ext-comments][data-autoload]');
  if (!boxes.length || !('IntersectionObserver' in window)) return;
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) { if (e.isIntersecting) { io.unobserve(e.target); loadComments(e.target); } });
  }, {rootMargin: '400px'});
  boxes.forEach(function (b) { io.observe(b); });
});
// the reader switched theme: tell whichever system is loaded
new MutationObserver(function () {
  var box = document.querySelector('[data-ext-comments][data-loaded]');
  if (!box) return;
  var dark = _commentsDark(), kind = box.dataset.extComments;
  if (kind === 'giscus') {
    var frame = box.querySelector('iframe.giscus-frame');
    if (frame) frame.contentWindow.postMessage({giscus: {setConfig: {theme: _giscusTheme(box.dataset)}}}, 'https://giscus.app');
  } else if (kind === 'remark42' && window.REMARK42) {
    window.REMARK42.changeTheme(dark ? 'dark' : 'light');
  }
}).observe(document.documentElement, {attributes: true, attributeFilter: ['data-theme']});
