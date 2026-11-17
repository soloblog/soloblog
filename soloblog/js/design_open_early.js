// Settings with the Design preview open (design_preview.js): moving to
// another Design page reopens it - set before the page draws, or the
// admin's menu showed for a moment first
try {
  if (sessionStorage.getItem('design-open') && window.innerWidth >= 1024) {
    document.documentElement.setAttribute('data-design-open', '');
  }
} catch (e) {}
