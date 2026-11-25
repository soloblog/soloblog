// A confirmation shows beside the action, not as a pop-up: in the page's
// [data-status-slot] -
// the admin page header's (PageHeader, ui), or on a post page the
// comment form's own status line. A page with neither falls back to a
// toast, so a message can never silently vanish.
//
// undo - a local "/path?field=value" to POST back to (status_redirect,
// guards.py): "Moved to trash" gets an Undo button right next to it
// instead of an are-you-sure dialog before it.
// a save that changed the page's frame (settings.FRAME - its palette,
// text size, the sidebar) reloads it, keeping its place and its message
document.addEventListener('htmx:afterSettle', function () {
  var status = document.querySelector('#save-status[data-reload]');
  if (!status) return;
  try { sessionStorage.setItem('soloblog-saved', status.textContent); } catch (e) {}
  // just saved, so nothing's lost: no "Leave page?" on the way
  window._leaving = true;
  location.reload();
});
document.addEventListener('DOMContentLoaded', function () {
  var saved = null;
  try { saved = sessionStorage.getItem('soloblog-saved'); sessionStorage.removeItem('soloblog-saved'); } catch (e) {}
  if (saved) showStatus(saved, 'success');
});
function showStatus(message, type, undo, waited) {
  // the slot beside the action, when the redirect named it (#its-id,
  // status_redirect's at=); otherwise the page's first - its header's.
  // A slot in a part that fills itself in after the page (Cloud storage)
  // is waited for, a few seconds at most
  var wanted = window._statusAt || (location.hash.length > 1 ? decodeURIComponent(location.hash.slice(1)) : '');
  if (wanted && !document.getElementById(wanted) && !waited && document.querySelector('[hx-trigger="load"]')) {
    var done = false;
    var later = function () {
      if (done || !document.getElementById(wanted)) return;
      done = true;
      document.removeEventListener('htmx:afterSettle', later);
      showStatus(message, type, undo, true);
    };
    document.addEventListener('htmx:afterSettle', later);
    setTimeout(function () {
      if (done) return;
      done = true;
      document.removeEventListener('htmx:afterSettle', later);
      showStatus(message, type, undo, true);
    }, 5000);
    return;
  }
  var named = wanted && document.getElementById(wanted);
  var near = named && (named.matches('[data-status-slot]') ? named : named.querySelector('[data-status-slot]'));
  var slot = near || document.querySelector('[data-status-slot]');
  // arrived after the page did, or named in the query (a page swapped in
  // place): the browser didn't scroll to it, so it's brought into view
  if (near && (waited || window._statusAt)) near.scrollIntoView({block: 'nearest'});
  window._statusAt = '';
  if (slot) {
    slot.textContent = message;
    paintStatus(slot, type === 'error' ? 'text-error' : 'text-success');
    if (_isUndoPath(undo)) slot.append(' ', _undoButton(undo));
    return;
  }
  showToast(message, type);
}
// a status's colour (text-success, text-error, text-warning, a muted
// text-base-content/60), changed alone: its place in its row - against
// the buttons (STATUS_BESIDE, ui) - is the page's, and stays
function paintStatus(el, colour) {
  [].slice.call(el.classList).forEach(function (c) {
    if (c === 'text-error' || c === 'text-success' || c === 'text-warning' || c.indexOf('text-base-content') === 0) el.classList.remove(c);
  });
  el.classList.add('text-xs');
  if (colour) el.classList.add(colour);
}
// the same rule as is_local_path (guards.py): "/x", never "//x" or "/\x"
function _isLocalPath(p) {
  return !!p && p.charAt(0) === '/' && p.charAt(1) !== '/' && p.charAt(1) !== String.fromCharCode(92);
}
// Undo only ever puts something back: a list's own /admin/.../restore.
// The server has already dropped any undo it didn't sign (app.SignedUndo)
function _isUndoPath(p) {
  return _isLocalPath(p) && /^\/admin\/[a-z]+\/restore$/.test(p.split('?')[0]);
}
function _undoButton(undo) {
  var btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'btn btn-xs btn-ghost ml-1';
  btn.textContent = 'Undo';
  btn.onclick = function () {
    var url = new URL(undo, location.href);
    var form = document.createElement('form');
    form.method = 'post';
    form.action = url.pathname;
    url.searchParams.forEach(function (value, name) {
      var input = document.createElement('input');
      input.type = 'hidden'; input.name = name; input.value = value;
      form.appendChild(input);
    });
    // inside a live list, so it swaps in place like any other action
    (document.getElementById('page-content') || document.body).appendChild(form);
    btn.disabled = true;
    form.requestSubmit();
  };
  return btn;
}
function showToast(message, type) {
  type = type || 'success';
  var container = document.getElementById('toast-container');
  if (!container) return;
  var el = document.createElement('div');
  // no shadow class: .alert has the theme's own. !py-1/!px-3/!text-xs
  // with ! - .alert's padding and size win over a plain utility.
  // The classes are spelled out in a table, not 'alert-' + type:
  // Tailwind only builds classes it can read whole in the source.
  var colorClass = {
    success: 'alert-success', error: 'alert-error',
    warning: 'alert-warning', info: 'alert-info'
  }[type] || 'alert-success';
  el.className = 'alert ' + colorClass + ' !py-1 !px-3 !text-xs';
  el.textContent = message;
  container.appendChild(el);
  setTimeout(function () {
    el.style.transition = 'opacity 0.3s';
    el.style.opacity = '0';
    setTimeout(function () { el.remove(); }, 300);
  }, 3000);
}
// a page redirects here with ?toast=message&toast_type=success/error -
// the one, standard way a list action confirms itself after its
// redirect (the param keeps its old name; it's shown inline now)
document.addEventListener('DOMContentLoaded', function () {
  var params = new URLSearchParams(location.search);
  var msg = params.get('toast');
  if (!msg) return;
  window._statusAt = params.get('toast_at') || '';
  showStatus(msg, params.get('toast_type') || 'success', params.get('undo'));
  params.delete('toast');
  params.delete('toast_type');
  params.delete('toast_at');
  params.delete('undo');
  params.delete('undo_sig');
  var qs = params.toString();
  var newUrl = location.pathname + (qs ? '?' + qs : '') + location.hash;
  history.replaceState(null, '', newUrl);
});
// one shared copy-URL helper for the Posts list and Media cards.
// Absolute URLs only (window.location.origin + path) - the whole point
// is pasting this somewhere else, where a bare "/post/slug" means
// nothing on its own. Success confirms on the button itself: its icon
// flips to a check for a moment.
// the admin's reply box under a comment (comments_routes.ReplyBox): the
// ⋯ menu the Reply came from closes, any other reply box closes (what's
// typed in it stays), and the cursor goes in
function openReply(id, btn) {
  var box = document.getElementById(id);
  if (!box) return;
  var menu = btn.closest('[popover]');
  if (menu && menu.matches(':popover-open')) menu.hidePopover();
  document.querySelectorAll('[data-reply-box]').forEach(function (b) { if (b !== box) b.hidden = true; });
  box.hidden = !box.hidden;
  if (!box.hidden) {
    var text = box.querySelector('textarea');
    if (text) text.focus();
  }
}
function closeReply(btn) {
  var box = btn.closest('[data-reply-box]');
  if (box) box.hidden = true;
}

function copyLink(path, btn) {
  var url = window.location.origin + path;
  navigator.clipboard.writeText(url).then(function () {
    if (!btn) return;
    if (!btn.dataset.icon) btn.dataset.icon = btn.innerHTML;
    btn.innerHTML = __CHECK_ICON__;
    btn.classList.add('text-success');
    clearTimeout(btn._copyTimer);
    btn._copyTimer = setTimeout(function () {
      btn.innerHTML = btn.dataset.icon;
      btn.classList.remove('text-success');
    }, 1500);
  }, function () {
    // the Clipboard API genuinely rejects this in real browsers too -
    // no HTTPS (a plain local network deploy), or a permission denial -
    // so this fails loud instead of leaving a click that did nothing
    showStatus("Couldn't copy link", 'error');
  });
}
