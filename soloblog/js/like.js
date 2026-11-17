function syncLikeButton(slug) {
  var btn = document.getElementById('like-button');
  if (!btn) return;
  var liked = !!localStorage.getItem('liked:' + slug);
  btn.querySelector('.heart-outline').classList.toggle('hidden', liked);
  btn.querySelector('.heart-filled').classList.toggle('hidden', !liked);
}
function toggleLike(slug) {
  var btn = document.getElementById('like-button');
  var key = 'liked:' + slug;
  if (localStorage.getItem(key)) return;  // one like per browser
  fetch('/post/' + slug + '/like', { method: 'POST' })
    .then(function (r) { return r.json(); })
    .then(function (r) {
      if (r.likes === undefined) return;
      document.getElementById('like-count').textContent = r.likes;
      localStorage.setItem(key, '1');
      syncLikeButton(slug);
      btn.classList.add('like-pop');
      setTimeout(function () { btn.classList.remove('like-pop'); }, 300);
    });
}
document.addEventListener('DOMContentLoaded', function () {
  var btn = document.getElementById('like-button');
  if (!btn) return;
  // the slug toggleLike is called with (data-args, actions.py)
  var slug = JSON.parse(btn.getAttribute('data-args'))[0];
  syncLikeButton(slug);
});

// emoji reactions (ReactionBar, ui): pressed state per browser, the
// counts from the server - which also enforces the real limits
function _reactedKey(slug, key) { return 'reacted:' + slug + ':' + key; }
document.addEventListener('DOMContentLoaded', function () {
  var bar = document.getElementById('reactions');
  if (!bar) return;
  bar.querySelectorAll('button.reaction').forEach(function (b) {
    var seen = null;
    try { seen = localStorage.getItem(_reactedKey(bar.dataset.slug, b.dataset.reaction)); } catch (e) {}
    if (seen) b.setAttribute('aria-pressed', 'true');
  });
});
document.addEventListener('click', function (e) {
  var b = e.target.closest && e.target.closest('#reactions button.reaction');
  if (!b || b.getAttribute('aria-pressed') === 'true' || b.dataset.busy) return;
  var bar = document.getElementById('reactions');
  var slug = bar.dataset.slug, key = b.dataset.reaction;
  b.dataset.busy = '1';
  var data = new FormData();
  data.append('reaction', key);
  fetch('/post/' + encodeURIComponent(slug) + '/react', { method: 'POST', body: data })
    .then(function (r) { return r.json(); })
    .then(function (r) {
      if (!r.counts) return;
      bar.querySelectorAll('button.reaction').forEach(function (x) {
        x.querySelector('.reaction-count').textContent = r.counts[x.dataset.reaction] || 0;
      });
      b.setAttribute('aria-pressed', 'true');
      try { localStorage.setItem(_reactedKey(slug, key), '1'); } catch (err) {}
      b.classList.add('like-pop');
      setTimeout(function () { b.classList.remove('like-pop'); }, 300);
    })
    .finally(function () { delete b.dataset.busy; });
});
