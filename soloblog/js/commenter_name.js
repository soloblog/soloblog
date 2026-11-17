// remembers a visitor's own name across comments/replies on any post
// - every Name field that opts in carries .remember-name-field (the
// main comment form, and each visitor's ReplyBox, routes/public.py).
// Only the name, not the email - that wasn't asked for, and a stored
// email would be a much bigger thing to get wrong (this is
// localStorage, per-browser, never sent anywhere - but still).
document.addEventListener('DOMContentLoaded', function () {
  var saved = localStorage.getItem('soloblog-commenter-name');
  if (!saved) return;
  document.querySelectorAll('.remember-name-field').forEach(function (el) {
    if (!el.value) el.value = saved;
  });
});
document.addEventListener('submit', function (e) {
  var nameField = e.target.querySelector && e.target.querySelector('.remember-name-field');
  if (nameField && nameField.value.trim()) {
    localStorage.setItem('soloblog-commenter-name', nameField.value.trim());
  }
});
