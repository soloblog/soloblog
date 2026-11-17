// A fixed footer's real height, as the page's bottom padding - Layout's
// pb-36 (ui) is a guess, and a long bio or many links make it taller.
// It's set on the content div, where pb-36 is (on <main> it would add to
// it), plus 48px - the same gap as an inline footer's pb-12.
function syncFixedFooterClearance() {
  var footer = document.querySelector('footer');
  var content = document.querySelector('main > div');
  if (!footer || !content) return;
  // fixed only from sm up (SiteFooter) - on a phone it's in the flow
  content.style.paddingBottom = getComputedStyle(footer).position === 'fixed' ? (footer.offsetHeight + 48) + 'px' : '';
}
document.addEventListener('DOMContentLoaded', syncFixedFooterClearance);
window.addEventListener('resize', syncFixedFooterClearance);
