// "Working..." states: the button that started a request swaps its icon
// for a daisyUI spinner and can't be pressed again until the answer
// arrives - no silent waits, no double submits. One place, every button.
function setBusy(btn, busy) {
  if (!btn || btn.hasAttribute('data-no-busy')) return;
  if (busy) {
    if (btn.dataset.busy) return;
    btn.dataset.busy = '1';
    // a disabled button drops the keyboard's place - it's given back below
    btn._keyHad = document.activeElement === btn;
    btn.disabled = true;
    var spin = document.createElement('span');
    spin.className = 'loading loading-spinner loading-xs busy-spinner';
    var icon = btn.querySelector('svg');
    if (icon) { icon.classList.add('hidden', 'busy-hidden'); icon.after(spin); } else btn.prepend(spin);
  } else {
    if (!btn.dataset.busy) return;
    delete btn.dataset.busy;
    btn.disabled = false;
    if (btn._keyHad && (!document.activeElement || document.activeElement === document.body)) btn.focus({ preventScroll: true });
    btn._keyHad = false;
    btn.querySelectorAll('.busy-spinner').forEach(function (s) { s.remove(); });
    btn.querySelectorAll('.busy-hidden').forEach(function (i) { i.classList.remove('hidden', 'busy-hidden'); });
  }
}
function _requestButton(detail) {
  var elt = detail.elt;
  if (elt && elt.matches && elt.matches('button, .btn')) return elt;
  var ev = detail.requestConfig && detail.requestConfig.triggeringEvent;
  return ev && ev.submitter ? ev.submitter : null;
}
document.addEventListener('htmx:beforeRequest', function (e) {
  var btn = _requestButton(e.detail);
  if (btn) { e.detail.elt._busyButton = btn; setBusy(btn, true); }
});
document.addEventListener('htmx:afterRequest', function (e) {
  setBusy(e.detail.elt && e.detail.elt._busyButton, false);
});
// plain (non-htmx) POST forms: the page is about to navigate. Disabled a
// tick later, so the button's own name/value still goes with the form.
document.addEventListener('submit', function (e) {
  var form = e.target;
  if (e.defaultPrevented || !e.submitter || (form.method || '').toLowerCase() !== 'post') return;
  // a download leaves the page where it is, so nothing would clear it
  if (e.submitter.hasAttribute('data-download')) return;
  if (form.matches('[hx-post],[hx-get],[hx-put],[hx-delete],[hx-patch]')) return;
  setTimeout(function () { setBusy(e.submitter, true); }, 0);
});
// back button onto a page from the cache - nothing is in flight any more
window.addEventListener('pageshow', function (e) {
  if (e.persisted) document.querySelectorAll('[data-busy]').forEach(function (b) { setBusy(b, false); });
});
