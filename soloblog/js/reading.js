// Everything here only does something on a post page - each piece looks
// for its own element and quietly does nothing without it.

// reading progress (ReadingProgress, ui): how far through the article
// itself the reader is - not the whole page, whose comments and footer
// would otherwise make it stall short of full. Once a frame, and not
// rounded: whole percents moved in steps on a long post
var readingFrame = 0;
function syncReadingProgress() {
  if (readingFrame) return;
  readingFrame = requestAnimationFrame(function () {
    readingFrame = 0;
    var bar = document.getElementById('reading-progress');
    var article = document.querySelector('article');
    if (!bar || !article) return;
    // how far down the page, as Ghost's themes measure it - by the post
    // alone, a short one fit the screen and showed full before a word was read
    var total = document.documentElement.scrollHeight - window.innerHeight;
    bar.value = (total > 0 ? Math.min(Math.max(window.scrollY / total, 0), 1) : 1) * 100;
  });
}
document.addEventListener('DOMContentLoaded', syncReadingProgress);
// pictures arriving make the post longer
window.addEventListener('load', syncReadingProgress);
window.addEventListener('scroll', syncReadingProgress, { passive: true });
window.addEventListener('resize', syncReadingProgress);

// table of contents scrollspy: the heading currently at the top of the
// screen gets its TOC link highlighted
document.addEventListener('DOMContentLoaded', function () {
  var links = [].slice.call(document.querySelectorAll('[data-toc] a[href^="#"]'));
  if (!links.length || !('IntersectionObserver' in window)) return;
  var byId = {};
  links.forEach(function (a) { byId[decodeURIComponent(a.getAttribute('href').slice(1))] = a; });
  var headings = Object.keys(byId).map(function (id) { return document.getElementById(id); }).filter(Boolean);
  var visible = {};
  // a link just clicked stays marked until the jump has finished: a
  // heading near the end can't scroll up to the top
  var clicked = null, settle;
  // once a jump has stopped, the heading sits just under the header - on a
  // phone the page can move under a long smooth scroll (the address bar
  // hiding, a fold opening), and it stopped past the heading
  function landed() {
    var el = clicked;
    clicked = null;
    if (!el) return;
    var want = parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop) || 0;
    var off = el.getBoundingClientRect().top - want;
    if (Math.abs(off) > 4) window.scrollTo({ top: window.scrollY + off, behavior: 'instant' });
  }
  links.forEach(function (a) {
    a.addEventListener('click', function () {
      clicked = document.getElementById(decodeURIComponent(a.getAttribute('href').slice(1)));
      mark();
      clearTimeout(settle); settle = setTimeout(landed, 300);
    });
  });
  function mark() {
    var current = null;
    // the section being read is the last heading that has reached the top,
    // just under a fixed header (scroll-padding-top, input.css)
    var top = (parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop) || 0) + 8;
    headings.forEach(function (h) { if (h.getBoundingClientRect().top <= top) current = h; });
    if (!current) current = headings[0];
    if (clicked) current = clicked;
    links.forEach(function (a) { a.classList.remove('toc-active'); });
    if (current) byId[current.id].classList.add('toc-active');
    // "Follow the reader": only the section being read shows its ###s
    document.querySelectorAll('[data-toc="auto"] details').forEach(function (d) {
      d.open = !!current && d.contains(byId[current.id]);
    });
  }
  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) { visible[e.target.id] = e.isIntersecting; });
    mark();
  }, { rootMargin: '0px 0px -60% 0px' });
  headings.forEach(function (h) { observer.observe(h); });
  window.addEventListener('scroll', function () {
    if (clicked) { clearTimeout(settle); settle = setTimeout(landed, 150); return; }
    mark();
  }, { passive: true });
  mark();
});

// Listen (ListenButton, ui): the browser's own text-to-speech. The
// post is queued a paragraph at a time - Chrome silently stops a single
// long utterance after about 15 seconds, short ones don't hit that.
var _listen = { state: 'idle' };
function setListenState(state) {
  _listen.state = state;
  var btn = document.getElementById('listen-button');
  if (!btn) return;
  btn.querySelector('.listen-icon-play').classList.toggle('hidden', state === 'playing');
  btn.querySelector('.listen-icon-pause').classList.toggle('hidden', state !== 'playing');
  btn.querySelector('.listen-label').textContent =
    _t(state === 'playing' ? 'Pause' : state === 'paused' ? 'Resume' : 'Listen');
}
function toggleListen() {
  var synth = window.speechSynthesis;
  if (_listen.state === 'playing') { synth.pause(); setListenState('paused'); return; }
  if (_listen.state === 'paused') { synth.resume(); setListenState('playing'); return; }
  var prose = document.querySelector('article .prose');
  if (!prose) return;
  synth.cancel();
  var title = document.querySelector('article h1');
  var chunks = title ? [title.innerText] : [];
  prose.querySelectorAll('h2, h3, h4, p, li, blockquote, dt, dd').forEach(function (el) {
    if (el.closest('pre, .footnote') || el.querySelector('p, li')) return;
    var text = el.innerText.trim();
    if (text) chunks.push(text);
  });
  var lang = document.documentElement.lang || navigator.language;
  chunks.forEach(function (text, i) {
    var u = new SpeechSynthesisUtterance(text);
    u.lang = lang;
    if (i === chunks.length - 1) u.onend = function () { setListenState('idle'); };
    synth.speak(u);
  });
  setListenState('playing');
}
document.addEventListener('DOMContentLoaded', function () {
  var btn = document.getElementById('listen-button');
  if (btn && 'speechSynthesis' in window) btn.classList.remove('hidden');
});
// a click-to-load embed (render.py's _embed): only now does the iframe,
// and with it anything from YouTube/Vimeo/Spotify/Mastodon, load
function loadEmbed(btn) {
  var box = btn.closest('.embed');
  var frame = document.createElement('iframe');
  frame.src = box.dataset.embedSrc;
  frame.className = 'w-full h-full border-0';
  box.classList.remove('flex', 'flex-col', 'items-center', 'justify-center', 'gap-2', 'p-4', 'text-center');
  frame.allow = 'autoplay; encrypted-media; fullscreen; picture-in-picture';
  frame.allowFullscreen = true;
  frame.loading = 'lazy';
  box.replaceChildren(frame);
}
// leaving the page mid-sentence shouldn't keep talking
window.addEventListener('pagehide', function () {
  if ('speechSynthesis' in window) window.speechSynthesis.cancel();
});
