// The spam check (captcha.py). Turnstile and hCaptcha share the same
// render/reset calls; whichever loaded calls captchaReady.
function _captchaApi() { return window.turnstile || window.hcaptcha; }
function renderCaptchas(root) {
  var api = _captchaApi();
  if (!api) return;
  (root || document).querySelectorAll('[data-captcha]:not([data-widget])').forEach(function (el) {
    // a reply form waits until its popover opens - one widget per
    // comment on the page would be a lot of iframes
    if (el.closest('details:not([open])')) return;
    el.setAttribute('data-widget', api.render(el, {sitekey: el.getAttribute('data-captcha')}));
  });
}
function captchaReady() { renderCaptchas(); }
document.addEventListener('toggle', function (e) {
  if (e.target.open) renderCaptchas(e.target);
}, true);
// the token goes out as captcha_token - capturing, so it's in place
// before htmx (or the browser) reads the form
document.addEventListener('submit', function (e) {
  var form = e.target;
  if (!form.querySelector || !form.querySelector('[data-captcha]')) return;
  var answer = form.querySelector('[name="cf-turnstile-response"], [name="h-captcha-response"]');
  var field = form.querySelector('input[name="captcha_token"]');
  if (!field) {
    field = document.createElement('input');
    field.type = 'hidden'; field.name = 'captcha_token';
    form.appendChild(field);
  }
  field.value = answer ? answer.value : '';
}, true);
// a token works once - a fresh check for the next message
document.addEventListener('htmx:afterRequest', function (e) {
  var box = e.target.querySelector && e.target.querySelector('[data-widget]');
  var api = _captchaApi();
  if (box && api) api.reset(box.getAttribute('data-widget'));
});
