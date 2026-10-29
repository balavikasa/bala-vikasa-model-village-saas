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
  let loadError = "";
  let loading = true;
  const esc = window.MV.escapeHtml;

  const kind = (status) => {
    if (["Failure", "Postponed"].includes(status)) return "danger";
    if (["Early", "Due today"].includes(status)) return "warning";
    if (["Visited", "On-time"].includes(status)) return "success";
    return "neutral";
  };

  const finiteCoordinate = (value) => {
    if (value === null || value === undefined || value === "") return false;
    return Number.isFinite(Number(value));
  };

  const hasCoordinates = (item) => {
    if (!finiteCoordinate(item.latitude) || !finiteCoordinate(item.longitude)) {
      return false;
    }
    const lat = Number(item.latitude);
    const lon = Number(item.longitude);
    if (lat < -90 || lat > 90 || lon < -180 || lon > 180) return false;
    return !(Math.abs(lat) < 0.000001 && Math.abs(lon) < 0.000001);
  };

  const locationLabel = (item) => {
    if (item.location_source === "field-evidence") return "Field GPS";
    if (item.location_source === "village-master") return "Village master";
    return "Location unavailable";
  };

  const popup = (item) => `
    <div class="map-popup mv-compact-map-card">
      <div class="mv-map-card-heading"><strong>${esc(item.name)}</strong><span class="badge" data-status="${esc(item.status)}">${esc(item.status)}</span></div>
      <small>${esc(item.cluster)} · ${esc(item.da_name)}</small>
      ${item.photo_url ? `<img loading="lazy" src="${esc(item.photo_url)}" alt="Village field visit evidence">` : ""}
      <div class="mv-map-quick-info"><span>${Number(item.committee_count || 0)} committees</span><span>${esc(item.last_visit_date || "No visit")}</span></div>
      ${item.outside_assignment ? '<div class="mv-map-source">Other village · visited by you</div>' : ''}
      <div class="mv-map-source">${esc(locationLabel(item))}</div>
      <a href="/directory/village/${Number(item.id)}">Village details</a>
    </div>`;

  const renderMap = () => {
    const located = rows.filter(hasCoordinates);

    if (map) {
      map.remove();
      map = null;
    }

    empty.classList.toggle("hidden", located.length > 0);
    mapHost.classList.toggle("hidden", located.length === 0);

    if (!located.length) return;

    if (!window.L) {
      if (window.BVUI) window.BVUI.map(mapHost, located);
      else mapHost.innerHTML = '<div class="form-alert" role="status">Map display unavailable. Use List to view your villages.</div>';
      return;
    }
    map = window.L.map(mapHost, { zoomControl: true });
    window.L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      referrerPolicy: "strict-origin-when-cross-origin",
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);

    const bounds = [];
    located.forEach((item) => {
      const position = [Number(item.latitude), Number(item.longitude)];
      bounds.push(position);
      const icon = window.L.divIcon({
        className: "",
        html: `<div class="mv-map-marker ${kind(item.status)}"></div>`,
        iconSize: [24, 24],
        iconAnchor: [12, 12],
      });
      window.L.marker(position, { icon, title: item.name })
        .addTo(map)
        .bindPopup(popup(item), { maxWidth: 270 });
    });

    if (bounds.length === 1) {
      map.setView(bounds[0], 13);
    } else {
      map.fitBounds(bounds, { padding: [26, 26], maxZoom: 13 });
    }

    requestAnimationFrame(() => map?.invalidateSize());
    setTimeout(() => map?.invalidateSize(), 160);
  };

  const renderList = () => {
    const summary = document.getElementById("map-list-summary");
    if (loading) {
      listHost.innerHTML = '<div class="empty-state" role="status">Loading villages...</div>';
      return;
    }
    if (loadError) {
      if (summary) summary.textContent = "";
      listHost.innerHTML = `<div class="form-alert" role="alert">${esc(loadError)} <button type="button" class="button ghost" data-map-retry>Try again</button></div>`;
      listHost.querySelector('[data-map-retry]')?.addEventListener('click', loadData);
      return;
    }
    const q = (search?.value || "").trim().toLowerCase();
    const visible = rows.filter(
      (item) => !q
        || `${item.name} ${item.da_name} ${item.cluster}`.toLowerCase().includes(q)
    );

    if (summary) summary.textContent = `${visible.length} ${visible.length === 1 ? "village" : "villages"}`;
    listHost.innerHTML = visible.length
      ? visible.map((item) => `
        <article class="ledger-card">
          <div class="ledger-card-top">
            <div>
              <strong>${esc(item.name)}</strong>
              <small>${esc(item.da_name)} · ${esc(item.cluster)}</small>
            </div>
            <span class="badge" data-status="${esc(item.status)}">${esc(item.status)}</span>
          </div>
          <div class="ledger-card-meta">
            <span>${Number(item.committee_count || 0)} committees</span>
            <span>${esc(item.last_visit_date || "No attendance recorded")}</span>
            <span>${hasCoordinates(item) ? esc(locationLabel(item)) : "GPS unavailable"}</span>
            ${item.outside_assignment ? '<span>Other village · visited by you</span>' : ''}
          </div>
          <a class="button ghost wide" href="${item.outside_assignment && item.report_url ? esc(item.report_url) : `/directory/village/${Number(item.id)}`}">View</a>
        </article>`)
        .join("")
      : `<div class="empty-state"><strong>No matching villages.</strong></div>`;
  };

  document.querySelectorAll("[data-map-mode]").forEach((button) => {
    button.addEventListener("click", () => {
      const list = button.dataset.mapMode === "list";
      document.querySelectorAll("[data-map-mode]").forEach((candidate) => {
        candidate.classList.toggle("is-active", candidate === button);
        candidate.setAttribute("aria-pressed", String(candidate === button));
      });
      mapPanel.classList.toggle("hidden", list);
      listPanel.classList.toggle("hidden", !list);
      if (list) {
        renderList();
      } else {
        if (!loading && !loadError && !map) renderMap();
        setTimeout(() => map?.invalidateSize(), 100);
      }
    });
  });

  search?.addEventListener("input", renderList);

  if (new URLSearchParams(window.location.search).get("mode") === "list") {
    document.querySelector('[data-map-mode="list"]')?.click();
  }

  let fetchId=0;
  async function loadData() {
    const id=++fetchId;
    loading = true; loadError = ""; renderList();
    try {
      const response = await window.MV.api("/api/v1/monitoring/map?"+window.BVReporting.params(Object.fromEntries([...new URLSearchParams(location.search)].filter(([k])=>["village","cluster","pc","da","submitted_da","committee","status"].includes(k)))));
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error || "Could not load the village map.");
      }
      if(id!==fetchId)return;
      if(map){map.remove();map=null;}
      rows = payload.items || [];
      loading = false;
      const requestedVillage = new URLSearchParams(location.search).get('village');
      if (requestedVillage) rows = rows.filter(row => String(row.id) === requestedVillage);
      renderMap();
      renderList();
    } catch (error) {
      loading = false; loadError = error.message || "Could not load villages.";
      mapHost.classList.remove("hidden"); empty.classList.add("hidden");
      mapHost.innerHTML = `<div class="form-alert" role="alert">${esc(loadError)} <button type="button" class="button ghost" data-map-retry>Try again</button></div>`;
      mapHost.querySelector('[data-map-retry]')?.addEventListener('click', loadData);
      renderList();
    }
  }
  document.addEventListener("bv:period-change",loadData);
  loadData();
})();
