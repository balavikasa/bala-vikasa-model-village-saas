(() => {
  "use strict";
  const host = document.getElementById("profile-map");
  if (!host || !window.L) return;
  const map = window.L.map(host);
  window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors',
  }).addTo(map);
  const bounds = [];
  const add = (lat, lng, label) => {
    const pos = [Number(lat), Number(lng)];
    if (!Number.isFinite(pos[0]) || !Number.isFinite(pos[1])) return;
    bounds.push(pos);
    window.L.marker(pos).addTo(map).bindPopup(window.MV.escapeHtml(label));
  };
  if (host.dataset.lat && host.dataset.lng) {
    add(host.dataset.lat, host.dataset.lng, host.dataset.label || "Village");
  } else if (host.dataset.villages) {
    try {
      JSON.parse(host.dataset.villages).forEach((v) => add(v.latitude, v.longitude, v.name));
    } catch (_) {}
  }
  if (bounds.length === 1) map.setView(bounds[0], 13);
  else if (bounds.length > 1) map.fitBounds(bounds, { padding: [24,24], maxZoom: 12 });
  else host.innerHTML = '<div class="empty-state">No coordinates recorded.</div>';
  setTimeout(() => map.invalidateSize(), 120);
})();