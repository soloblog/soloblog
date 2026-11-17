// Mastodon has no one universal share-URL the way X/Facebook/LinkedIn/
// Bluesky each do - it's federated, so "share this" only means
// anything on the *visitor's own* instance, not the author's. Every
// real Mastodon instance documents the same /share?text= endpoint
// (the same one the official "Share on Mastodon" button pattern uses
// elsewhere on the web) - this just asks which instance, once, then
// sends them there. sessionStorage remembers the answer so a visitor
// sharing a second post this same session isn't asked again.
function shareToMastodon(url, title) {
  var instance = sessionStorage.getItem('soloblog-mastodon-instance');
  if (!instance) {
    instance = prompt('Which Mastodon instance are you on? (e.g. mastodon.social)');
    if (!instance) return;
    instance = instance.trim().replace(/^https?:\/\//, '').replace(/\/.*$/, '');
    sessionStorage.setItem('soloblog-mastodon-instance', instance);
  }
  var text = title + ' ' + url;
  window.open('https://' + instance + '/share?text=' + encodeURIComponent(text), '_blank', 'noopener');
}
