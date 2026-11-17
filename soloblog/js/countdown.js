// Countdown: blocks (render._countdown): days to go, counted again on the
// visitor's own day - the page may have been made days ago. Once, when it
// loads: a count, not a ticking clock.
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('[data-countdown]').forEach(function (el) {
    var parts = el.dataset.countdown.split('-');
    var day = new Date(+parts[0], +parts[1] - 1, +parts[2]), now = new Date();
    var today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    var left = Math.round((day - today) / 86400000);
    var out = el.querySelector('[data-countdown-left]');
    if (!out) return;
    out.textContent = left === 0 ? el.dataset.today : left === 1 ? el.dataset.one
                    : left > 1 ? el.dataset.many.replace('{n}', left) : '';
  });
});
