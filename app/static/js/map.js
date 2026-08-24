(() => {
  "use strict";
  const mapHost = document.getElementById("role-village-map");
  if (!mapHost || !window.MV) return;

  const mapPanel = document.querySelector("[data-map-panel]");
  const listPanel = document.querySelector("[data-list-panel]");
  const listHost = document.getElementById("map-list-items");
  const search = document.getElementById("map-search");
  const empty = document.getElementById("role-map-empty");
  let rows = [];
  let map = null;
  const esc = window.MV.escapeHtml;

  const kind = (status) => {
    if (["Failure", "Postponed"].includes(status)) return "danger";
    if (["Early", "Due today"].includes(status)) return "warning";
    if (status === "On-time") return "success";
    return "neutral";
  };

  const popup = (item) => `
    <div class="map-popup">
      <strong>${esc(item.name)}</strong>
      <small>${esc(item.cluster)} · ${esc(item.da_name)}</small>
      <span class="badge" data-status="${esc(item.status)}">${esc(item.status)}</span>
      <dl>
        <div><dt>Committees</dt><dd>${Number(item.committee_count || 0)}</dd></div>
        <div><dt>Last visit</dt><dd>${esc(item.last_visit_date || "No visit")}</dd></div>
      </dl>
      ${item.photo_url ? `<img src="${esc(item.photo_url)}" alt="Latest field evidence">` : ""}
      <a class="button ghost wide" href="/directory/village/${Number(item.id)}">View village</a>
    </div>`;

  const renderMap = () => {
    if (!window.L) return;
    const located = rows.filter((r) => Number.isFinite(Number(r.latitude)) && Number.isFinite(Number(r.longitude)));
    empty.classList.toggle("hidden", located.length > 0);
    mapHost.classList.toggle("hidden", located.length === 0);
    if (!located.length) return;
    map?.remove();
    map = window.L.map(mapHost, { zoomControl: true });
    window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map);
    const bounds = [];
    located.forEach((item) => {
      const position = [Number(item.latitude), Number(item.longitude)];
      bounds.push(position);
      const icon = window.L.divIcon({
        className: "",
        html: `<div class="mv-map-marker ${kind(item.status)}"></div>`,
        iconSize: [24,24],
        iconAnchor: [12,12],
      });
      window.L.marker(position, { icon, title: item.name }).addTo(map).bindPopup(popup(item), { maxWidth: 290 });
    });
    map.fitBounds(bounds, { padding: [26,26], maxZoom: 12 });
    setTimeout(() => map.invalidateSize(), 120);
  };

  const renderList = () => {
    const q = (search?.value || "").trim().toLowerCase();
    const visible = rows.filter((item) => !q || `${item.name} ${item.da_name} ${item.cluster}`.toLowerCase().includes(q));
    listHost.innerHTML = visible.length ? visible.map((item) => `
      <article class="ledger-card">
        <div class="ledger-card-top"><div><strong>${esc(item.name)}</strong><small>${esc(item.da_name)} · ${esc(item.cluster)}</small></div><span class="badge" data-status="${esc(item.status)}">${esc(item.status)}</span></div>
        <div class="ledger-card-meta"><span>${Number(item.committee_count || 0)} committees</span><span>${esc(item.last_visit_date || "No visit")}</span></div>
        <a class="button ghost wide" href="/directory/village/${Number(item.id)}">View</a>
      </article>`).join("") : `<div class="empty-state"><strong>No matching villages.</strong></div>`;
  };

  document.querySelectorAll("[data-map-mode]").forEach((button) => button.addEventListener("click", () => {
    const list = button.dataset.mapMode === "list";
    document.querySelectorAll("[data-map-mode]").forEach((b) => {
      b.classList.toggle("is-active", b === button);
      b.setAttribute("aria-pressed", String(b === button));
    });
    mapPanel.classList.toggle("hidden", list);
    listPanel.classList.toggle("hidden", !list);
    if (list) renderList(); else setTimeout(() => map?.invalidateSize(), 100);
  }));
  search?.addEventListener("input", renderList);

  (async () => {
    try {
      const response = await window.MV.api("/api/v1/monitoring/map");
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Could not load the village map.");
      rows = payload.items || [];
      renderMap();
      renderList();
    } catch (error) {
      mapHost.innerHTML = `<div class="form-alert">${esc(error.message)}</div>`;
    }
  })();
})();