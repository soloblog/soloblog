(function () {
  var sel = document.querySelector('select[name=timezone]');
  var zone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  if (sel && sel.value === 'UTC' && zone && sel.querySelector('option[value="' + zone + '"]')) sel.value = zone;
  var spelling = document.querySelector('select[name=english_spelling]'), lang = navigator.language || '';
  if (spelling && spelling.value === 'us' && /^en-/i.test(lang) && !/^en-US/i.test(lang))
    spelling.value = /^en-AU/i.test(lang) ? 'au' : 'gb';
})();
