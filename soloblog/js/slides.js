// Show as slides (pages.py): a scroll-snap carousel, moved by the
// arrow buttons, the keyboard, or a swipe; the counter follows along.
function _slideTrack(el) { return el.closest('.slides').querySelector('.slides-track'); }
function moveSlide(el, step) {
  var track = _slideTrack(el);
  var i = Math.round(track.scrollLeft / Math.max(track.clientWidth, 1)) + step;
  i = Math.max(0, Math.min(i, track.children.length - 1));
  track.scrollTo({ left: i * track.clientWidth, behavior: 'smooth' });
}
function syncSlides(track) {
  var count = track.closest('.slides').querySelector('.slides-count');
  var i = Math.round(track.scrollLeft / Math.max(track.clientWidth, 1));
  count.textContent = (i + 1) + ' / ' + track.children.length;
}
function fullscreenSlides(btn) {
  var box = btn.closest('.slides');
  if (document.fullscreenElement) { document.exitFullscreen(); return; }
  if (box.requestFullscreen) box.requestFullscreen().then(function () { _slideTrack(btn).focus(); });
}
// A deck fills the screen, with no header: Esc goes back to the site - but
// in the browser's full screen it leaves full screen, as everywhere
document.addEventListener('keydown', function (e) {
  var exit = document.querySelector('[data-slides-exit]');
  if (e.key === 'Escape' && exit && !document.fullscreenElement && !e.defaultPrevented
      && !document.querySelector('dialog[open]')) {
    location.href = exit.href;
    return;
  }
  var track = document.querySelector('.slides-track');
  if (!track || e.target.closest('input, textarea, select, [contenteditable]')) return;
  var step = { ArrowRight: 1, PageDown: 1, ' ': 1, ArrowLeft: -1, PageUp: -1 }[e.key];
  var focused = document.fullscreenElement || track.contains(document.activeElement) || document.activeElement === track;
  if (!step || (!focused && e.key === ' ')) return;
  if (e.key === ' ' || e.key.indexOf('Page') === 0 || focused) e.preventDefault();
  moveSlide(track, step);
});
