// A page's small motions (pages.py): a framed picture tilts a
// little toward the pointer (data-tilt) - the opening one with a sheen
// where the light would catch it - and a big number counts up as it
// comes into view (data-count-up). Only with Animations on, never when
// the device asks for less motion, and the tilt only with a mouse.
(function () {
  function still() {
    return !document.documentElement.hasAttribute('data-animate') ||
      (window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches);
  }

  document.addEventListener('pointermove', function (e) {
    if (e.pointerType !== 'mouse' || still()) return;
    var box = e.target.closest && e.target.closest('[data-tilt]');
    if (!box) return;
    var r = box.getBoundingClientRect();
    var x = (e.clientX - r.left) / r.width - 0.5, y = (e.clientY - r.top) / r.height - 0.5;
    // where the light catches it (pages._SHEEN)
    box.style.setProperty('--sheen-x', ((x + 0.5) * 100).toFixed(1) + '%');
    box.style.setProperty('--sheen-y', ((y + 0.5) * 100).toFixed(1) + '%');
    box.style.transition = 'transform 0.12s ease-out';
    box.style.transform = 'perspective(1200px) rotateX(' + (-y * 5).toFixed(2) + 'deg) rotateY(' +
      (x * 6).toFixed(2) + 'deg) translateY(-4px) scale(1.01)';
  });
  document.addEventListener('pointerout', function (e) {
    var box = e.target.closest && e.target.closest('[data-tilt]');
    if (!box || box.contains(e.relatedTarget)) return;
    box.style.transition = 'transform 0.4s ease-out';
    box.style.transform = '';
  });

  // "1,000+", "4.9 ★", "28" - the number counts up, what's around it stays
  function countUp(el) {
    var m = el.textContent.match(/^(\D*)([\d,]*\.?\d+)(.*)$/s);
    if (!m) return;
    var target = parseFloat(m[2].replace(/,/g, '')), places = (m[2].split('.')[1] || '').length;
    var commas = m[2].indexOf(',') >= 0, start = null, original = el.textContent;
    function show(v) {
      var t = v.toFixed(places);
      if (commas) t = Number(t).toLocaleString('en', { minimumFractionDigits: places });
      el.textContent = m[1] + t + m[3];
    }
    function step(now) {
      if (start === null) start = now;
      var p = Math.min((now - start) / 1200, 1);
      show(target * (1 - Math.pow(1 - p, 3)));
      if (p < 1) requestAnimationFrame(step); else el.textContent = original;
    }
    show(0);
    requestAnimationFrame(step);
  }
  function watch() {
    var numbers = document.querySelectorAll('[data-count-up]');
    if (!numbers.length || still() || !window.IntersectionObserver) return;
    var seen = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        seen.unobserve(en.target);
        countUp(en.target);
      });
    }, { threshold: 0.6 });
    numbers.forEach(function (n) { seen.observe(n); });
  }
  // What comes into view on a page with sections, beyond what pages.py
  // marked: a section whose items sit in a grid (cards, people, prices)
  // gives its place to them, so they arrive one after another as a wall of
  // pictures does - unless it's one card (Style: Card), which is one thing.
  // And the plain writing around the sections, block by block
  function pieces() {
    var bodies = [];
    [].forEach.call(document.querySelectorAll('[data-section]'), function (sec) {
      var body = sec.closest('.prose');
      if (body && bodies.indexOf(body) < 0) bodies.push(body);
      var first = sec.firstElementChild;
      if (!sec.classList.contains('reveal-item') || !first || first.classList.contains('card')) return;
      var grid = [].filter.call(sec.querySelectorAll('.grid'), function (g) {
        return g.children.length > 1 && !g.closest('form');
      })[0];
      if (!grid) return;
      sec.classList.remove('reveal-item');
      for (var el = grid; el !== sec; el = el.parentElement) {
        [].forEach.call(el.parentElement.children, function (beside) {
          if (beside !== el) beside.classList.add('reveal-item');
        });
      }
      [].forEach.call(grid.children, function (item) { item.classList.add('reveal-item'); });
    });
    function writing(el) {
      [].forEach.call(el.children, function (c) {
        // not what floats over the page (a heading's Copy link button)
        if (c.matches('.reveal-item, [data-section], script, style') || getComputedStyle(c).position === 'absolute') return;
        if (c.querySelector('.reveal-item, [data-section]')) writing(c);
        else c.classList.add('reveal-item');
      });
    }
    bodies.forEach(writing);
  }
  // a page's sections come into view as they scroll in, once each
  // (input.css [section-reveal] - the how is the site's, the page's or the section's own)
  function reveal() {
    if (still() || !window.IntersectionObserver) return;
    pieces();
    var items = [].slice.call(document.querySelectorAll('.reveal-item'));
    if (!items.length) return;
    document.documentElement.classList.add('js-reveal');
    // a section and the heading above it are one movement, whichever is seen first
    var mates = new Map();
    items.forEach(function (n, i) {
      var next = items[i + 1];
      if (n.tagName !== 'H2' || !next || !next.hasAttribute('data-section')) return;
      mates.set(n, next);
      mates.set(next, n);
    });
    function show(n, wait) {
      if (n.hasAttribute('data-revealed')) return;
      seen.unobserve(n);
      if (wait) n.style.animationDelay = wait + 'ms';
      n.setAttribute('data-revealed', '');
    }
    var seen = new IntersectionObserver(function (entries) {
      // those arriving together follow one another, a moment apart
      var place = 0;
      entries.forEach(function (en) {
        if (!en.isIntersecting || en.target.hasAttribute('data-revealed')) return;
        var wait = Math.min(place++, 6) * 90, mate = mates.get(en.target);
        show(en.target, wait);
        if (mate) show(mate, wait);
      });
    }, { rootMargin: '0px 0px -12% 0px' });
    items.forEach(function (n) {
      // "None" has nothing to wait for
      if (getComputedStyle(n).getPropertyValue('--reveal').trim() === 'none') n.setAttribute('data-revealed', '');
      else seen.observe(n);
    });
  }
  // On a wide screen the story's heading is held with the picture right under it, at the gap
  // every section's heading has above its content, and they let go together (pages._STORY_HEAD,
  // _STORY_BODY). The page's own gap is measured with the heading in its place in the page.
  // On a tall window the pair is held in the middle of the space under the header, level with
  // the words beside it, not pinned to its top with the space left empty below: --story-shift
  // moves both down by the same, worked out from the tallest picture at the width it shows,
  // and --story-head-x centres the heading across the story.
  // --story-top is where the picture is held, and data-held on the wrapper switches on the
  // classes that use them
  function live(story, on) {
    var wrap = story.closest('[data-story-wrap]');
    [story, wrap].forEach(function (el) { if (el) el.toggleAttribute('data-live', on); });
  }
  function stick(story) {
    var wrap = story.closest('[data-story-wrap]'), head = wrap && wrap.querySelector('[data-story-head]');
    var body = story.closest('[data-section]'), area = story.querySelector('[data-story-held] > div');
    if (!head || !body) return;
    var pictures = [].slice.call(story.querySelectorAll('[data-story-picture] img'));
    function tallest(width) {
      // a picture not loaded yet goes by the size its tag gives; one with neither, unknown
      var most = 0;
      for (var i = 0; i < pictures.length; i++) {
        var img = pictures[i];
        var w = img.naturalWidth || +img.getAttribute('width'), h = img.naturalHeight || +img.getAttribute('height');
        if (!w || !h) return Infinity;
        most = Math.max(most, width * h / w);
      }
      return most;
    }
    function set() {
      wrap.removeAttribute('data-held');
      if (getComputedStyle(head).position !== 'sticky') {
        ['--story-top', '--story-gap', '--story-shift', '--story-head-x', '--story-first-h', '--story-last-h'].forEach(function (v) { wrap.style.removeProperty(v); });
        return;
      }
      var was = head.style.position;
      head.style.position = 'static';
      wrap.style.removeProperty('--story-head-x');
      var gap = Math.max(0, body.getBoundingClientRect().top - head.getBoundingClientRect().bottom);
      var high = head.offsetHeight;
      head.style.width = 'fit-content';
      var at = head.getBoundingClientRect();
      head.style.removeProperty('width');
      head.style.position = was;
      // centred across the whole story, words and picture, as the page's own headings are
      // across their column: the heading is only as wide as its words (_STORY_HEAD), and moved
      // in from its own edge to the story's middle
      var grid = area && area.closest('[data-story-held]').parentNode, x = 0;
      if (grid) {
        var box = grid.getBoundingClientRect(), middle = (box.left + box.right) / 2;
        x = (getComputedStyle(head).direction === 'rtl' ? at.right - middle : middle - at.left) - at.width / 2;
      }
      wrap.style.setProperty('--story-head-x', Math.max(0, Math.round(x)) + 'px');
      var root = getComputedStyle(document.documentElement);
      var room = window.innerHeight - (parseFloat(root.getPropertyValue('--header-h')) || 0) -
        (parseFloat(root.getPropertyValue('--footer-h')) || 0);
      // the 3rem kept under the picture (pages._SCROLL_FRAME), shared above and below
      var under = 3 * (parseFloat(root.fontSize) || 16);
      var most = room - high - gap - under;
      var picture = Math.min(most, area ? tallest(area.clientWidth) : Infinity);
      var shift = Math.max(0, Math.round((most - picture) / 2));
      // the first and last steps are as tall as puts their words level with the picture's
      // middle when the story is caught and when it lets go (pages._SCROLL_STEP)
      var top = (parseFloat(root.getPropertyValue('--header-h')) || 0) + shift + high + gap;
      var foot = window.innerHeight - (parseFloat(root.getPropertyValue('--footer-h')) || 0);
      if (picture < Infinity) {
        wrap.style.setProperty('--story-first-h', Math.round(picture) + 'px');
        wrap.style.setProperty('--story-last-h', Math.round(2 * (foot - top - picture / 2)) + 'px');
      }
      wrap.style.setProperty('--story-gap', gap + 'px');
      wrap.style.setProperty('--story-shift', shift + 'px');
      wrap.style.setProperty('--story-top', 'calc(var(--header-h, 0px) + ' + (shift + high + gap) + 'px)');
      wrap.setAttribute('data-held', '');
    }
    set();
    window.addEventListener('resize', function () { requestAnimationFrame(set); });
    pictures.forEach(function (img) { img.addEventListener('load', set); });
    if (window.ResizeObserver) new ResizeObserver(set).observe(head);
  }
  // A Story (pages._render_story): the step crossing the middle of the
  // window is the one being read - its picture is shown, and the others
  // fade away. Watched by the browser (IntersectionObserver), never by a
  // scroll listener. Marked live only where that works and motion is
  // allowed; otherwise the story stays a plain stack of pictures and words.
  function stories() {
    var all = [].slice.call(document.querySelectorAll('[data-story]'));
    if (!all.length || still() || !window.IntersectionObserver) return;
    function pick(story, n) {
      var step = story.querySelector('[data-story-step="' + n + '"]');
      var pic = step ? step.getAttribute('data-story-pic') : '';
      story.querySelectorAll('[data-story-step], [data-story-mark], [data-story-picture]').forEach(function (el) {
        var mine = el.hasAttribute('data-story-picture') ? el.getAttribute('data-story-picture') === pic :
          (el.getAttribute('data-story-step') || el.getAttribute('data-story-mark')) === n;
        if (el.hasAttribute('data-active') !== mine) el.toggleAttribute('data-active', mine);
      });
      level(story);
    }
    // beside the picture on a wide screen, the step markers are level with its middle - each
    // picture its own height, so they move with the one shown
    function level(story) {
      var held = story.querySelector('[data-story-held]'), mark = story.querySelector('[data-story-mark]');
      var img = story.querySelector('[data-story-picture][data-active] img');
      if (!held || !mark) return;
      var marks = mark.parentNode;
      if (!img || getComputedStyle(held).display !== 'flex') { marks.style.removeProperty('margin-top'); return; }
      marks.style.marginTop = Math.max(0, Math.round((img.offsetHeight - marks.offsetHeight) / 2)) + 'px';
    }
    // a thin band across the middle: one step at a time, at any window height
    var watch = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) pick(e.target.closest('[data-story]'), e.target.getAttribute('data-story-step'));
      });
    }, { rootMargin: '-50% 0px -49% 0px' });
    // the page settles on a step as it scrolls near one (input.css, story-scroll) - only while a
    // story fills the window, top to bottom. Left on for the whole page, a phone pulled the page
    // back to the last step from the section after it, and caught it again on the way back up
    var across = new Map(), printing = false;
    function snap() {
      var inside = !printing && all.some(function (story) {
        var edges = across.get(story);
        return edges && edges.top && edges.bottom;
      });
      document.documentElement.toggleAttribute('data-story-snap', inside);
    }
    function edge(name, margin) {
      return new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          var edges = across.get(e.target) || {};
          edges[name] = e.isIntersecting;
          across.set(e.target, edges);
        });
        snap();
      }, { rootMargin: margin });
    }
    // the window's top line, and its bottom one: a story across both has nothing else showing
    var topLine = edge('top', '0px 0px -100% 0px'), bottomLine = edge('bottom', '-100% 0px 0px 0px');
    all.forEach(function (story) {
      pick(story, '0');
      live(story, true);
      topLine.observe(story);
      bottomLine.observe(story);
      story.querySelectorAll('[data-story-step]').forEach(function (step) { watch.observe(step); });
      // on a phone a landscape picture fills the area (its sides cropped); a portrait or square one
      // shows whole. Read from the file itself, so a phone version swapped in is judged on its own.
      // A cropped one shows wider than the screen, so its sizes say how wide
      // (beside the words, on a wide screen, the held layer is a row: nothing is cropped there)
      var held = story.querySelector('[data-story-held]');
      story.querySelectorAll('[data-story-picture] img').forEach(function (img) {
        var frame = img.closest('[data-story-picture]'), sizes = img.getAttribute('sizes');
        function fit() {
          if (!img.naturalWidth) return;
          var cover = img.naturalWidth > img.naturalHeight && !(held && getComputedStyle(held).display === 'flex');
          if (cover) frame.setAttribute('data-fit', 'cover'); else frame.removeAttribute('data-fit');
          if (!cover) img.setAttribute('sizes', sizes);
          else img.setAttribute('sizes', Math.ceil(frame.clientHeight * img.naturalWidth / img.naturalHeight) + 'px');
        }
        img.addEventListener('load', function () { fit(); level(story); });
        window.addEventListener('resize', function () { requestAnimationFrame(function () { fit(); level(story); }); });
        fit();
      });
      stick(story);
      // a step's own picture is moved out of sight (kept for a screen reader): its credit link too
      story.querySelectorAll('[data-story-real] a').forEach(function (a) { a.tabIndex = -1; });
    });
    // printed, a story is the plain stack - white words on paper would vanish
    window.addEventListener('beforeprint', function () {
      all.forEach(function (story) { live(story, false); });
      printing = true;
      snap();
    });
    window.addEventListener('afterprint', function () {
      all.forEach(function (story) { live(story, true); });
      printing = false;
      snap();
    });
  }
  // a row of logos with more than fit (pages._logos): one line drifting
  // slowly sideways, without end, paused under the pointer or keyboard -
  // two copies side by side, so the second takes the first's place. Left
  // wrapping onto more lines when there's room, or with less motion
  function drift() {
    if (still() || !Element.prototype.animate) return;
    document.querySelectorAll('[data-drift]').forEach(function (row) {
      var gap = parseFloat(getComputedStyle(row).columnGap) || 0;
      row.style.flexWrap = 'nowrap';
      var wide = row.scrollWidth > row.clientWidth;
      if (!wide) { row.style.flexWrap = ''; return; }
      var half = document.createElement('div');
      half.style.cssText = 'display:flex;align-items:center;flex-shrink:0;gap:' + gap + 'px;padding-right:' + gap + 'px';
      while (row.firstChild) half.appendChild(row.firstChild);
      var copy = half.cloneNode(true);
      copy.setAttribute('aria-hidden', 'true');
      copy.querySelectorAll('a').forEach(function (a) { a.tabIndex = -1; });
      var track = document.createElement('div');
      track.style.cssText = 'display:flex;width:max-content';
      track.appendChild(half);
      track.appendChild(copy);
      row.appendChild(track);
      row.style.justifyContent = 'flex-start';
      row.style.overflow = 'hidden';
      row.style.maskImage = row.style.webkitMaskImage =
        'linear-gradient(to right,transparent,black 3rem,black calc(100% - 3rem),transparent)';
      // about 30 px a second, however many there are
      var run = track.animate([{ transform: 'translateX(0)' }, { transform: 'translateX(-50%)' }],
                              { duration: half.offsetWidth / 30 * 1000, iterations: Infinity });
      ['pointerenter', 'focusin'].forEach(function (e) { row.addEventListener(e, function () { run.pause(); }); });
      ['pointerleave', 'focusout'].forEach(function (e) { row.addEventListener(e, function () { run.play(); }); });
    });
  }
  function start() { watch(); reveal(); stories(); drift(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
