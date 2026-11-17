// Passkeys (passkeys.py): the browser half of the two WebAuthn
// ceremonies. The server sends options with binary fields as base64url;
// navigator.credentials wants ArrayBuffers, and the answer goes back as
// base64url again.
function _b64uToBuf(s) {
  s = s.replace(/-/g, '+').replace(/_/g, '/');
  while (s.length % 4) s += '=';
  return Uint8Array.from(atob(s), function (c) { return c.charCodeAt(0); }).buffer;
}
function _bufToB64u(buf) {
  var bin = '';
  new Uint8Array(buf).forEach(function (b) { bin += String.fromCharCode(b); });
  return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
function _passkeyStatus(id, text) {
  var el = document.getElementById(id);
  if (el) { el.textContent = text; el.className = 'text-xs text-error'; }
}
function passkeysSupported() { return !!(window.PublicKeyCredential && navigator.credentials); }
async function addPasskey() {
  if (!passkeysSupported()) return _passkeyStatus('passkey-status', "This browser can't make passkeys");
  try {
    var opts = await (await fetch('/admin/passkeys/options', { method: 'POST' })).json();
    opts.challenge = _b64uToBuf(opts.challenge);
    opts.user.id = _b64uToBuf(opts.user.id);
    (opts.excludeCredentials || []).forEach(function (c) { c.id = _b64uToBuf(c.id); });
    var cred = await navigator.credentials.create({ publicKey: opts });
    var body = {
      name: document.getElementById('passkey-name').value,
      credential: {
        id: cred.id, rawId: _bufToB64u(cred.rawId), type: cred.type,
        response: {
          clientDataJSON: _bufToB64u(cred.response.clientDataJSON),
          attestationObject: _bufToB64u(cred.response.attestationObject),
          transports: cred.response.getTransports ? cred.response.getTransports() : []
        }
      }
    };
    var r = await (await fetch('/admin/passkeys/register', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
    })).json();
    if (r.error) return _passkeyStatus('passkey-status', r.error);
    location.href = '/admin/settings?tab=security&toast=' + encodeURIComponent('Passkey added');
  } catch (e) {
    // the person closed the prompt, or the device said no
    _passkeyStatus('passkey-status', e.name === 'InvalidStateError'
      ? 'This device already has a passkey here' : 'No passkey was added');
  }
}
async function loginWithPasskey() {
  if (!passkeysSupported()) return _passkeyStatus('passkey-login-status', "This browser can't use passkeys");
  try {
    var opts = await (await fetch('/login/passkey/options', { method: 'POST' })).json();
    opts.challenge = _b64uToBuf(opts.challenge);
    (opts.allowCredentials || []).forEach(function (c) { c.id = _b64uToBuf(c.id); });
    var cred = await navigator.credentials.get({ publicKey: opts });
    var body = {
      id: cred.id, rawId: _bufToB64u(cred.rawId), type: cred.type,
      response: {
        clientDataJSON: _bufToB64u(cred.response.clientDataJSON),
        authenticatorData: _bufToB64u(cred.response.authenticatorData),
        signature: _bufToB64u(cred.response.signature),
        userHandle: cred.response.userHandle ? _bufToB64u(cred.response.userHandle) : null
      }
    };
    var keep = document.getElementById('keep-signed-in');
    var r = await (await fetch('/login/passkey/verify' + (!keep || keep.checked ? '?keep=1' : ''), {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
    })).json();
    if (r.error) return _passkeyStatus('passkey-login-status', r.error);
    location.href = r.redirect || '/';
  } catch (e) {
    _passkeyStatus('passkey-login-status', 'No passkey was used');
  }
}
