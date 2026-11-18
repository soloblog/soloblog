// Galleries (gallery.py) and the lightbox (LightboxDialog, ui).

// slider and filmstrip arrows, and the slider's "2 / 5" counter. A
// filmstrip moves by most of its width, so the last image or two stay
// in view; an arrow hides at its own end, both when everything fits.
function slideGallery(btn, dir) {
  var track = btn.closest('.gallery-slider').querySelector('.carousel');
  var step = track.closest('.gallery-filmstrip') ? 0.8 : 1;
  track.scrollBy({ left: dir * track.clientWidth * step, behavior: 'smooth' });
}
function syncSlider(track) {
  var arrows = track.parentNode.querySelectorAll(':scope > button');
  if (arrows.length === 2) {
    arrows[0].classList.toggle('invisible', track.scrollLeft <= 1);
    arrows[1].classList.toggle('invisible', track.scrollLeft + track.clientWidth >= track.scrollWidth - 1);
  }
  var gallery = track.closest('.gallery');
  var count = gallery && gallery.querySelector('.slider-count');
  if (!count) return;
  var i = Math.round(track.scrollLeft / Math.max(track.clientWidth, 1));
  count.textContent = (i + 1) + ' / ' + track.children.length;
  // the caption under it, the slide's own
  var caption = gallery.querySelector('.slider-caption'), slide = track.children[i];
  if (caption && slide) caption.textContent = slide.getAttribute('data-title') || '';
  // the slides' names above it: the one in view picked
  var names = gallery.querySelector('[data-slider-names]');
  if (names) {
    names.querySelectorAll('button').forEach(function (b, n) {
      b.setAttribute('aria-pressed', n === i ? 'true' : 'false');
      b.classList.toggle('btn-soft', n === i);
      b.classList.toggle('btn-primary', n === i);
      b.classList.toggle('btn-ghost', n !== i);
    });
    // where they don't all fit (a phone), the picked one slides into view -
    // the row itself, not the page
    var picked = names.querySelectorAll('button')[i];
    if (picked && names.scrollWidth > names.clientWidth) {
      var box = names.getBoundingClientRect(), r = picked.getBoundingClientRect();
      names.scrollTo({ left: names.scrollLeft + r.left - box.left - (box.width - r.width) / 2, behavior: 'smooth' });
    }
  }
}
// a slide's name, picked: that slide
function showSlide(btn, i) {
  var track = btn.closest('.gallery').querySelector('.carousel');
  track.scrollTo({ left: i * track.clientWidth, behavior: 'smooth' });
}
// A slider that moves by itself ("```gallery slider auto"): a slide every
// 6 seconds, held while it's pointed at or focused and while the tab is
// hidden, and stopped for good once someone moves it or presses its pause
// button (WCAG 2.2.2). With Animations off or less motion asked for, it
// starts stopped - its button still plays it.
function _autoplay(slider) {
  var track = slider.querySelector('.carousel'), gallery = slider.closest('.gallery');
  var btn = gallery.querySelector('[data-slider-pause]');
  var stopped = !document.documentElement.hasAttribute('data-animate') ||
    (window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches);
  var held = false;
  function show() {
    btn.setAttribute('aria-label', _t(stopped ? 'Resume' : 'Pause'));
    btn.querySelector('[data-icon=pause]').classList.toggle('hidden', stopped);
    btn.querySelector('[data-icon=play]').classList.toggle('hidden', !stopped);
  }
  function stop() { stopped = true; show(); }
  show();
  setInterval(function () {
    if (stopped || held || document.hidden) return;
    var n = track.children.length, i = Math.round(track.scrollLeft / Math.max(track.clientWidth, 1));
    track.scrollTo({ left: ((i + 1) % n) * track.clientWidth, behavior: 'smooth' });
  }, 6000);
  slider.addEventListener('pointerenter', function () { held = true; });
  slider.addEventListener('pointerleave', function () { held = false; });
  slider.addEventListener('focusin', function () { held = true; });
  slider.addEventListener('focusout', function () { held = false; });
  slider.addEventListener('pointerdown', stop);
  var names = gallery.querySelector('[data-slider-names]');
  if (names) names.addEventListener('click', stop);
  btn.addEventListener('click', function () { stopped = !stopped; show(); });
}
window.addEventListener('load', function () {
  document.querySelectorAll('.gallery-slider[data-autoplay]').forEach(_autoplay);
});
// before any scrolling: the first arrow starts hidden, and a strip that
// fits hides both - once its images have their sizes
window.addEventListener('load', function () {
  document.querySelectorAll('.gallery-slider > .carousel').forEach(syncSlider);
});
window.addEventListener('resize', function () {
  document.querySelectorAll('.gallery-slider > .carousel').forEach(syncSlider);
});
// a strip's images load lazily, after the page's own load - until they
// do, it looks like everything fits and both arrows hide; check again
// as each one arrives
document.addEventListener('load', function (e) {
  var track = e.target.tagName === 'IMG' && e.target.closest('.gallery-slider > .carousel');
  if (track) syncSlider(track);
}, true);

// The lightbox shows one set at a time: a gallery's images, or - when
// single images are allowed - every other image in the post, in order.
var _lb = { items: [], index: 0, zoomed: false };
function _lbItems(trigger) {
  var group = trigger.dataset.lightbox;
  if (group) {
    return [].map.call(document.querySelectorAll('[data-lightbox="' + group + '"]'), function (a) {
      // the image's own src - its dark mode version while the page is dark,
      // its phone version on a phone
      var img = a.querySelector('img');
      return { src: (img && img.getAttribute('src')) || a.getAttribute('href'), alt: (img || {}).alt || '',
               caption: a.dataset.caption || '', el: a };
    });
  }
  // only the ones showing: a story has each picture twice, one for a
  // phone and one held beside the words, and hides whichever doesn't fit -
  // its step's copy in a box for screen readers alone (1px, clipped), which
  // the picture inside still has a size in. And each picture once.
  var seen = {};
  var shown = [].filter.call(document.querySelectorAll('.lightbox-single'), function (img) {
    if (img !== trigger && (!img.getClientRects().length || _lbClipped(img))) return false;
    if (seen[img.src] && img !== trigger) return false;
    seen[img.src] = true;
    return true;
  });
  return shown.map(function (img) {
    var fig = img.closest('figure');
    var cap = fig && fig.querySelector('figcaption');
    // src, not currentSrc - the page may be showing a smaller srcset copy
    return { src: img.src, alt: img.alt, caption: cap ? cap.innerHTML : '', el: img };
  });
}
function _lbClipped(img) {
  for (var e = img.parentElement; e && e !== document.body; e = e.parentElement) {
    var r = e.getBoundingClientRect();
    if (r.width <= 1 || r.height <= 1) return true;
  }
  return false;
}
// The picture opens once it has loaded, so the box opens at its size with
// only the dialog's own animation. Moving to another one, the old picture
// fades into the new while the box grows or shrinks to it - the ones
// either side are loaded ahead, so there's rarely a wait. A slow picture
// shows a spinner instead of an empty box
var _lbTurn = 0;
function _lbMotion() {
  return document.documentElement.hasAttribute('data-animate') &&
    !(window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches);
}
function _lbLoaded(src) {
  var pre = new Image();
  pre.src = src;
  return pre.decode ? pre.decode().catch(function () {}) : Promise.resolve();
}
function _lbAhead() {
  var n = _lb.items.length;
  if (n < 2) return;
  _lbLoaded(_lb.items[(_lb.index + 1) % n].src);
  _lbLoaded(_lb.items[(_lb.index - 1 + n) % n].src);
}
function _lbSpinner(turn) {
  var spin = document.getElementById('lightbox-loading');
  var late = setTimeout(function () { if (turn === _lbTurn) spin.classList.remove('hidden'); }, 200);
  return function () { clearTimeout(late); spin.classList.add('hidden'); };
}
function _lbFill(item) {
  var img = document.getElementById('lightbox-img');
  img.alt = item.alt;
  // our own markup (render.py/gallery.py build it escaped) - it can
  // carry the photographer's credit link, so it's html, not text
  document.getElementById('lightbox-caption').innerHTML = item.caption;
  var many = _lb.items.length > 1;
  document.getElementById('lightbox-count').textContent = many ? (_lb.index + 1) + ' / ' + _lb.items.length : '';
  document.getElementById('lightbox-nav').classList.toggle('hidden', !many);
}
function _lbReset() {
  var img = document.getElementById('lightbox-img');
  var box = img.closest('.modal-box');
  img.getAnimations().forEach(function (a) { a.cancel(); });
  box.getAnimations().forEach(function (a) { a.cancel(); });
  box.querySelectorAll('[data-lightbox-ghost]').forEach(function (g) { g.remove(); });
  box.style.width = box.style.height = img.style.opacity = '';
  _lbZoom(false);
}
// the new picture in place of what's showing: the box from its old size to
// the new one, the old picture (a copy laid over it) fading as the new comes in
function _lbSwap(item, turn) {
  var img = document.getElementById('lightbox-img');
  var box = img.closest('.modal-box');
  var motion = _lbMotion(), before = box.getBoundingClientRect(), ghost = null;
  if (motion) {
    box.style.width = before.width + 'px';
    box.style.height = before.height + 'px';
    if (img.getAttribute('src')) {
      ghost = img.cloneNode();
      ghost.removeAttribute('id');
      ghost.setAttribute('data-lightbox-ghost', '');
      ghost.className = 'absolute inset-0 w-full h-full object-contain pointer-events-none';
      img.parentNode.appendChild(ghost);
    }
    img.style.opacity = '0';
  }
  img.src = item.src;
  _lbFill(item);
  return (img.decode ? img.decode().catch(function () {}) : Promise.resolve()).then(function () {
    if (turn !== _lbTurn || !motion) return;
    box.style.width = box.style.height = '';
    var after = box.getBoundingClientRect();
    img.style.opacity = '';
    var ease = { duration: 250, easing: 'ease-out' };
    box.animate([{ width: before.width + 'px', height: before.height + 'px' },
                 { width: after.width + 'px', height: after.height + 'px' }], ease);
    img.animate([{ opacity: 0 }, { opacity: 1 }], ease);
    if (ghost) ghost.animate([{ opacity: 1 }, { opacity: 0 }], ease).finished.then(function () { ghost.remove(); });
  });
}
function openLightbox(trigger) {
  _lb.items = _lbItems(trigger);
  _lb.index = Math.max(0, _lb.items.findIndex(function (i) { return i.el === trigger; }));
  var item = _lb.items[_lb.index], turn = ++_lbTurn;
  var dialog = document.getElementById('lightbox'), img = document.getElementById('lightbox-img');
  _lbReset();
  // never the last picture shown, even for a moment
  img.removeAttribute('src');
  var done = _lbSpinner(turn);
  // a slow picture: open now, with the spinner, and grow to it when it's there
  var late = setTimeout(function () { if (turn === _lbTurn && !dialog.open) dialog.showModal(); }, 300);
  _lbLoaded(item.src).then(function () {
    if (turn !== _lbTurn) return;
    clearTimeout(late);
    done();
    if (dialog.open) { _lbSwap(item, turn); } else {
      img.src = item.src;
      _lbFill(item);
      (img.decode ? img.decode().catch(function () {}) : Promise.resolve()).then(function () {
        if (turn === _lbTurn && !dialog.open) dialog.showModal();
      });
    }
    _lbAhead();
  });
}
function stepLightbox(dir) {
  if (_lb.items.length < 2) return;
  _lb.index = (_lb.index + dir + _lb.items.length) % _lb.items.length;
  var item = _lb.items[_lb.index], turn = ++_lbTurn;
  _lbReset();
  var done = _lbSpinner(turn);
  _lbLoaded(item.src).then(function () {
    if (turn !== _lbTurn) return;
    done();
    _lbSwap(item, turn);
    _lbAhead();
  });
}
// click to zoom in where you clicked; move the pointer (or drag a
// finger) to look around; click again to zoom back out
function _lbZoom(on, x, y) {
  var img = document.getElementById('lightbox-img');
  var stage = document.getElementById('lightbox-stage');
  _lb.zoomed = on;
  if (on && x !== undefined) _lbPan(x, y);
  img.style.transform = on ? 'scale(2.5)' : '';
  stage.classList.toggle('cursor-zoom-in', !on);
  stage.classList.toggle('cursor-zoom-out', on);
}
function _lbPan(x, y) {
  var img = document.getElementById('lightbox-img');
  var r = img.getBoundingClientRect();
  var px = Math.min(Math.max((x - r.left) / r.width, 0), 1) * 100;
  var py = Math.min(Math.max((y - r.top) / r.height, 0), 1) * 100;
  img.style.transformOrigin = px + '% ' + py + '%';
}
document.addEventListener('DOMContentLoaded', function () {
  var box = document.getElementById('lightbox');
  if (!box) return;
  if (box.dataset.single === '1') {
    // the writing's pictures, and a section's or a landing page's own
    // (a band's, a tile's) - not one behind a hero's words, a link's or a
    // gallery's, which opens its own set
    document.querySelectorAll('article [data-post-body] img, article figure img').forEach(function (img) {
      if (img.closest('a, .gallery') || img.classList.contains('absolute')) return;
      // a hand, as any link has: the zoom cursor is the lightbox's own
      img.classList.add('lightbox-single', 'cursor-pointer');
    });
  }
  var stage = document.getElementById('lightbox-stage');
  var start = null, moved = false;
  stage.addEventListener('pointerdown', function (e) { start = { x: e.clientX, y: e.clientY }; moved = false; });
  stage.addEventListener('pointermove', function (e) {
    if (_lb.zoomed) _lbPan(e.clientX, e.clientY);
    if (start && Math.abs(e.clientX - start.x) > 10) moved = true;
  });
  stage.addEventListener('pointerup', function (e) {
    var dx = start ? e.clientX - start.x : 0;
    start = null;
    // a sideways swipe moves between images; a tap zooms
    if (!_lb.zoomed && moved && Math.abs(dx) > 50) { stepLightbox(dx < 0 ? 1 : -1); return; }
    if (!moved || _lb.zoomed) _lbZoom(!_lb.zoomed, e.clientX, e.clientY);
  });
  box.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowLeft') stepLightbox(-1);
    if (e.key === 'ArrowRight') stepLightbox(1);
  });
  box.addEventListener('close', function () { _lbZoom(false); });
});
document.addEventListener('click', function (e) {
  var trigger = e.target.closest('[data-lightbox], .lightbox-single');
  if (!trigger || !document.getElementById('lightbox')) return;
  e.preventDefault();
  openLightbox(trigger);
});
