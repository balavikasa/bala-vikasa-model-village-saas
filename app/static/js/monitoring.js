(() => {
  "use strict";
  if (!window.MV) return;
  const statusHost = document.querySelector("#monitor-status-list");
  let map;

  const statusKind = (status) => {
    if (["Failure", "Postponed"].includes(status)) return "danger";
    if (["Early", "Pending"].includes(status)) return "warning";
    if (status === "On-time") return "success";
    return "";
  };

  const renderSummary = (data) => {
    Object.entries(data.counts || {}).forEach(([key, value]) => {
      document.querySelectorAll(`[data-monitor-kpi="${key}"]`).forEach((node) => {
        node.textContent = Number(value).toLocaleString();
      });
    });
    document.querySelectorAll("[data-monitor-status]").forEach((node) => {
      node.textContent = Number(data.status_breakdown?.[node.dataset.monitorStatus] || 0).toLocaleString();
    });
    const entries = Object.entries(data.status_breakdown || {});
    const max = Math.max(...entries.map(([, value]) => Number(value)), 1);
    statusHost.innerHTML = entries.length ? entries.map(([status, value]) => `
      <div class="status-row">
        <label>${window.MV.escapeHtml(status)}</label>
        <span class="status-track"><i class="status-fill" data-status="${window.MV.escapeHtml(status)}" style="width:${Math.max(4, Number(value) / max * 100)}%"></i></span>
        <strong>${Number(value).toLocaleString()}</strong>
      </div>`).join("") : '<div class="empty-state"><p>No action plans in this scope.</p></div>';
    document.querySelector("#monitor-updated").textContent = `Updated ${new Intl.DateTimeFormat(undefined, { timeStyle: "short" }).format(new Date())}`;
  };

  const popup = (item) => `
    <div class="map-popup">
      <span class="badge ${statusKind(item.status)}">${window.MV.escapeHtml(item.status)}</span>
      <h3>${window.MV.escapeHtml(item.name)}</h3>
      <p>${window.MV.escapeHtml(item.cluster)} · DA ${window.MV.escapeHtml(item.da_name)}</p>
      <p>${Number(item.committee_count).toLocaleString()} committees · Last visit ${window.MV.escapeHtml(item.last_visit_date ? window.MV.formatDate(item.last_visit_date) : "not recorded")}</p>
      ${item.photo_url ? `<img src="${window.MV.escapeHtml(item.photo_url)}" alt="Latest visit evidence for ${window.MV.escapeHtml(item.name)}" loading="lazy">` : ""}
    </div>`;

  const renderMap = (items) => {
    const host = document.querySelector("#village-map");
    const fallback = document.querySelector("#map-no-coordinates");
    const located = items.filter((item) => Number.isFinite(Number(item.latitude)) && Number.isFinite(Number(item.longitude)));
    if (!located.length || !window.L) {
      host.classList.add("hidden");
      fallback.classList.remove("hidden");
      return;
    }
    map = window.L.map(host, { zoomControl: true, scrollWheelZoom: false });
    window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map);
    const bounds = [];
    located.forEach((item) => {
      const kind = statusKind(item.status);
      const icon = window.L.divIcon({
        className: "",
        html: `<div class="mv-map-marker ${kind}"></div>`,
        iconSize: [24, 24],
        iconAnchor: [12, 12],
        popupAnchor: [0, -12],
      });
      const position = [Number(item.latitude), Number(item.longitude)];
      bounds.push(position);
      window.L.marker(position, { icon, title: item.name }).addTo(map).bindPopup(popup(item), { maxWidth: 280 });
    });
    map.fitBounds(bounds, { padding: [30, 30], maxZoom: 12 });
    window.setTimeout(() => map.invalidateSize(), 150);
  };

  (async () => {
    try {
      const [summaryResponse, mapResponse] = await Promise.all([
        window.MV.api("/api/v1/monitoring/summary"),
        window.MV.api("/api/v1/monitoring/map"),
      ]);
      if (!summaryResponse.ok || !mapResponse.ok) throw new Error("Monitoring data could not be loaded.");
      renderSummary(await summaryResponse.json());
      renderMap((await mapResponse.json()).items || []);
    } catch (error) {
      statusHost.innerHTML = `<div class="form-alert">${window.MV.escapeHtml(error.message)}</div>`;
      document.querySelector("#monitor-updated").textContent = "Unavailable";
    }
  })();

  window.addEventListener("resize", () => map?.invalidateSize());
})();
