// The demo's note (ui.DemoBanner): its ✕ puts it away on this page - it's
// back on the next, so the password and the reset time are always at hand
function closeDemoNote() {
  document.documentElement.setAttribute('data-demo-note-closed', '');
}
