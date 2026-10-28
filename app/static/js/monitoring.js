(() => {
  "use strict";
  if (!window.MV) return;
  const statusHost = document.querySelector("#monitor-status-list");
  let map;

  const statusKind = (status) => {
    if (["Failure", "Postponed"].includes(status)) return "danger";
    if (["Early", "Pending"].includes(status)) return "warning";
    if (["Visited", "On-time"].includes(status)) return "success";
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
      </div>`).join("") : '<div class="empty-state"><p>No villages in scope.</p></div>';
    document.querySelector("#monitor-updated").textContent = `Updated ${new Intl.DateTimeFormat(undefined, { timeStyle: "short" }).format(new Date())}`;
  };

  const popup = (item) => `
    <div class="map-popup mv-compact-map-card">
      <div class="mv-map-card-heading"><strong>${window.MV.escapeHtml(item.name)}</strong><span class="badge ${statusKind(item.status)}">${window.MV.escapeHtml(item.status)}</span></div>
      <small>${window.MV.escapeHtml(item.cluster)} · DA ${window.MV.escapeHtml(item.da_name)}</small>
      ${item.photo_url ? `<img loading="lazy" src="${window.MV.escapeHtml(item.photo_url)}" alt="Recent field evidence">` : ""}
      <div class="mv-map-quick-info"><span>${Number(item.committee_count || 0)} committees</span><span>${window.MV.escapeHtml(item.last_visit_date || "No visit")}</span></div>
      <a href="/directory/village/${Number(item.id)}">Village details</a>
    </div>`;

  const hasCoordinates = (item) => {
    if (item.latitude === null || item.latitude === undefined || item.latitude === "" ||
        item.longitude === null || item.longitude === undefined || item.longitude === "") return false;
    const lat = Number(item.latitude);
    const lon = Number(item.longitude);
    return Number.isFinite(lat) && Number.isFinite(lon) &&
      Math.abs(lat) <= 90 && Math.abs(lon) <= 180 &&
      !(Math.abs(lat) < 0.000001 && Math.abs(lon) < 0.000001);
  };

  const renderMap = (items) => {
    const host = document.querySelector("#village-map");
    const fallback = document.querySelector("#map-no-coordinates");
    const located = items.filter(hasCoordinates);
    const missing = items.filter((item) => !hasCoordinates(item));
    const missingHost = document.querySelector("#monitor-unmapped");
    if (missingHost) {
      missingHost.classList.toggle("hidden", !missing.length);
      missingHost.innerHTML = missing.length ? `
        <strong>${missing.length.toLocaleString()} village${missing.length === 1 ? "" : "s"} without GPS</strong>
        <p>These villages have no valid field or master GPS yet. They remain visible in the list view.</p>
        <ul>${missing.slice(0, 6).map((item) => `<li><a href="/directory/village/${Number(item.id)}">${window.MV.escapeHtml(item.name)}</a></li>`).join("")}</ul>
        ${missing.length > 6 ? `<small>And ${missing.length - 6} more · <a href="/map?mode=list">See all villages</a></small>` : `<a href="/map?mode=list">See the full village list</a>`}
      ` : "";
    }
    if (!located.length || !window.L) {
      host.classList.add("hidden");
      fallback.classList.remove("hidden");
      fallback.textContent = !window.L ? "Map tiles are unavailable. Open the village list." : "No villages have valid GPS coordinates yet.";
      return;
    }
    host.classList.remove("hidden");
    fallback.classList.add("hidden");
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
      window.L.marker(position, { icon, title: item.name }).addTo(map).bindPopup(popup(item), { maxWidth: 270 });
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
