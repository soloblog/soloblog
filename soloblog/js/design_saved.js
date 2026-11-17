document.body.addEventListener('design-saved', function () {
  localStorage.removeItem('admin-preview');
  try { sessionStorage.setItem('design-saved', String(window.scrollY)); } catch (e) {}
  window._leaving = true;
  location.reload();
});
window.addEventListener('load', function () {
  var y = null;
  try { y = sessionStorage.getItem('design-saved'); sessionStorage.removeItem('design-saved'); } catch (e) {}
  if (y === null) return;
  window.scrollTo(0, Number(y) || 0);
  var status = document.getElementById('save-status');
  if (status) { status.textContent = 'Saved'; status.className = 'text-xs text-success'; }
});
