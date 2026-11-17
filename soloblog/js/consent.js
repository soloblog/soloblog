// Cookie consent (ads.py): remembered per browser. Until the visitor
// says yes, the gated scripts (Google Analytics, custom code marked as
// tracking) stay inside their <template> and never run.
function _consent() {
  try { return localStorage.getItem('soloblog-consent'); } catch (e) { return null; }
}
function _runConsentScripts() {
  var tpl = document.getElementById('consent-scripts');
  if (!tpl || tpl.dataset.done) return;
  tpl.dataset.done = '1';
  // a script copied in runs; anything else (a <meta>, a <link>) is cloned
  [].forEach.call(tpl.content.childNodes, function (old) {
    if (old.nodeType !== 1) return;
    if (old.tagName !== 'SCRIPT') { document.head.appendChild(old.cloneNode(true)); return; }
    var s = document.createElement('script');
    [].forEach.call(old.attributes, function (a) { s.setAttribute(a.name, a.value); });
    s.text = old.text;
    document.head.appendChild(s);
  });
}
function setConsent(choice) {
  try { localStorage.setItem('soloblog-consent', choice); } catch (e) {}
  var banner = document.getElementById('consent-banner');
  if (banner) banner.classList.add('hidden');
  if (choice === 'granted') _runConsentScripts();
  // a "no" after an earlier "yes" can't unload a running script - a
  // reload starts the page clean without it
  else if (document.getElementById('consent-scripts') && document.getElementById('consent-scripts').dataset.done) location.reload();
}
function openConsent() {
  var banner = document.getElementById('consent-banner');
  if (banner) banner.classList.remove('hidden');
}
document.addEventListener('DOMContentLoaded', function () {
  if (!document.getElementById('consent-banner')) return;
  var choice = _consent();
  if (choice === 'granted') _runConsentScripts();
  else if (choice !== 'denied') openConsent();
});
