// A Design page's live preview (DesignPreview): Preview opens it full
// screen, the page's settings on the left and the site on the right
// (Ghost's design view) - or, where there's no room for both, the site
// in a new tab. The form as it stands is kept under a token
// (/admin/design/preview) and shown in the frame - after a pause in the
// changes, so typing doesn't reload it at every letter.
(function () {
  var pane = document.querySelector('[data-design-preview]');
  var form = document.querySelector('#settings-body form[data-declare-fields]');
  var frame = pane && pane.querySelector('[data-preview-frame]');
  var box = pane && pane.querySelector('[data-preview-box]');
  var pathPick = document.querySelector('[data-preview-path]');
  var root = document.documentElement;
  var device = 'desktop', token = '', timer = null;
  // a settings page shown inside a preview never draws one of its own -
  // that's how previews ended up nested in previews
  if (window.top !== window.self) { if (pane) pane.remove(); return; }
  if (!form || !frame) return;
  // a preset's Preview, clicked here, shows it in the frame - until a change
  var preset = '';
  function path() { return pathPick ? pathPick.value : '/'; }
  function address() {
    var extra = preset ? 'preset_preview=' + encodeURIComponent(preset) : token ? 'design_preview=' + token : '';
    return path() + (extra ? (path().indexOf('?') < 0 ? '?' : '&') + extra : '');
  }
  function shown() { return root.hasAttribute('data-design-open'); }
  function fit() {
    if (!shown()) return;
    // a computer's page fills the room beside the settings - scaled down
    // only where that's narrower than a laptop's 1280
    var room = box.clientWidth, width = device === 'phone' ? 390 : Math.max(1280, room);
    var scale = Math.min(1, room / width);
    frame.style.width = width + 'px';
    frame.style.height = (box.clientHeight / scale) + 'px';
    frame.style.transform = 'scale(' + scale + ')';
    frame.style.left = device === 'phone' ? Math.max(0, (room - width * scale) / 2) + 'px' : '0';
  }
  function load() { if (shown()) frame.src = address(); }
  function refresh() {
    var data = new FormData(form), names = {};
    [].forEach.call(form.elements, function (f) { if (f.name) names[f.name] = 1; });
    data.append('declared_fields', Object.keys(names).join(','));
    return fetch('/admin/design/preview', {method: 'POST', body: data})
      .then(function (r) { return r.json(); })
      .then(function (r) { token = r.token; load(); });
  }
  // room for the settings and a useful preview beside them
  function roomy() { return window.innerWidth >= 1024; }
  function open() {
    if (!roomy()) { refresh().then(function () { window.open(address(), '_blank'); }); return; }
    root.setAttribute('data-design-open', '');
    try { sessionStorage.setItem('design-open', '1'); } catch (e) {}
    fit();
    refresh();
  }
  function close() {
    root.removeAttribute('data-design-open');
    try { sessionStorage.removeItem('design-open'); } catch (e) {}
    frame.removeAttribute('src');
  }
  function later() { if (!shown()) return; preset = ''; clearTimeout(timer); timer = setTimeout(refresh, 600); }
  document.addEventListener('click', function (e) {
    var link = e.target.closest && e.target.closest('a[href^="/admin/presets/preview/"]');
    if (!link || !shown()) return;
    e.preventDefault();
    preset = link.getAttribute('href').split('/').pop();
    load();
  });
  form.addEventListener('input', later);
  form.addEventListener('change', later);
  if (pathPick) pathPick.addEventListener('change', load);
  document.querySelectorAll('[data-preview-show]').forEach(function (b) { b.addEventListener('click', open); });
  document.querySelectorAll('[data-preview-close]').forEach(function (b) { b.addEventListener('click', close); });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && shown() && !document.querySelector('dialog[open], :popover-open')) close();
  });
  document.querySelectorAll('[data-preview-device]').forEach(function (b) {
    b.addEventListener('click', function () {
      device = b.getAttribute('data-preview-device');
      document.querySelectorAll('[data-preview-device]').forEach(function (o) {
        o.setAttribute('aria-pressed', o === b ? 'true' : 'false');
      });
      fit();
    });
  });
  document.querySelectorAll('[data-preview-open]').forEach(function (b) {
    b.addEventListener('click', function () { window.open(address(), '_blank'); });
  });
  // links in the preview go where they lead on your site - but not into
  // the admin: back to the page being previewed
  frame.addEventListener('load', function () {
    try {
      if (/^[/](admin|login)/.test(frame.contentWindow.location.pathname)) frame.src = address();
    } catch (e) {}
  });
  window.addEventListener('resize', function () { if (shown() && !roomy()) close(); else fit(); });
  // a save that reloads the page (a new theme) comes back to the preview
  var again = null;
  try { again = sessionStorage.getItem('design-open'); } catch (e) {}
  if (again && roomy()) open();
})();
