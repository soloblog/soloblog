document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.prose pre').forEach(function (pre) {
    var btn = document.createElement('button');
    btn.textContent = _t('Copy');
    btn.className = 'btn btn-xs copy-btn';
    btn.onclick = function () {
      var code = pre.querySelector('code');
      navigator.clipboard.writeText(code ? code.innerText : pre.innerText);
      btn.textContent = _t('Copied!');
      setTimeout(function () { btn.textContent = _t('Copy'); }, 1500);
    };
    // beside the code, not in it: inside, it scrolled away with a long
    // line. The code's margins pass through the wrapper, so the button
    // sits in the code's corner
    var wrap = document.createElement('div');
    wrap.className = 'relative';
    pre.parentNode.insertBefore(wrap, pre);
    wrap.appendChild(pre);
    wrap.appendChild(btn);
  });
});
