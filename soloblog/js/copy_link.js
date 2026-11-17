function copyPreviewLink(url) {
  navigator.clipboard.writeText(url);
  var el = document.getElementById('preview-copied');
  if (el) { el.classList.remove('hidden'); setTimeout(function () { el.classList.add('hidden'); }, 2000); }
}
