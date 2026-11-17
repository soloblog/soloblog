window.addEventListener('scroll', function () {
  var btn = document.getElementById('scroll-top-btn');
  if (!btn) return;
  // Post settings (routes/editor.py) slides over this corner: hidden for
  // as long as it's open, checked on every scroll - checking only when it
  // opened, the next scroll showed the button again
  var drawer = document.getElementById('post-settings-panel');
  var drawerOpen = drawer && !drawer.classList.contains('translate-x-full') && !drawer.hidden;
  var show = window.scrollY > 400 && !drawerOpen;
  btn.classList.toggle('opacity-0', !show);
  btn.classList.toggle('pointer-events-none', !show);
});
