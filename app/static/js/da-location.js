(() => {
  'use strict';
  if (document.body.dataset.role !== 'da') return;
  // Browser and phone OS control the actual permission. An app cannot toggle
  // device Location Services or bypass a denial. Auto-request when permitted.
  let last = null, running = false, lastRequestAt = 0;
  const dialog = document.getElementById('da-location-dialog');
  const help = document.getElementById('da-location-help');
  const showHelp = (message) => {
    if (help) help.textContent = message;
    if (dialog && !dialog.open) dialog.showModal();
  };
  const hideHelp = () => { if (dialog?.open) dialog.close(); };
  const send = (point) => {
    last = point;
    window.dispatchEvent(new CustomEvent('mv:location', { detail: point }));
  };
  const capture = async (force = false) => {
    if (running) return;
    if (!force && Date.now() - lastRequestAt < 12000) return;
    if (!window.isSecureContext || !navigator.geolocation) {
      showHelp('Location requires HTTPS and a browser with GPS support.');
      send({ message: 'GPS unavailable. Open with HTTPS and enable location access.' });
      return;
    }
    lastRequestAt = Date.now();
    running = true;
    navigator.geolocation.getCurrentPosition(
      (position) => {
        running = false;
        const { latitude, longitude, accuracy } = position.coords;
        if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return;
        hideHelp();
        send({ latitude, longitude, accuracy, capturedAt: Date.now() });
      },
      (err) => {
        running = false;
        const denied = err?.code === 1;
        const message = denied
          ? 'Enable location permission for this site in browser/app settings. Also turn on Location Services in your phone settings, then return to the app.'
          : 'Turn on device Location Services, move to a place with a clear signal, and tap Try again. A GPS fix may take longer while offline.';
        send({ message });
        showHelp(message);
      },
      // Reuse a recent high-quality fix for speed; form requires a newer fix.
      { enableHighAccuracy: true, maximumAge: 15000, timeout: 12000 }
    );
  };
  window.MVLocation = { capture, get last() { return last; } };
  document.querySelectorAll('[data-location-retry]').forEach(btn => btn.addEventListener('click', () => capture(true)));
  document.querySelectorAll('[data-location-dismiss]').forEach(btn => btn.addEventListener('click', hideHelp));
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden && (!last?.capturedAt || Date.now() - last.capturedAt > 60000)) capture(true);
  });
  navigator.permissions?.query({ name: 'geolocation' }).then(permission => {
    permission.onchange = () => { if (permission.state === 'granted') capture(true); else if (permission.state === 'denied') showHelp('Allow location in site settings, then return to the app.'); };
    if (permission.state === 'granted' || permission.state === 'prompt') capture();
    else showHelp('Location is disabled for this site. Enable it in browser permissions and phone settings.');
  }).catch(() => capture());
})();
