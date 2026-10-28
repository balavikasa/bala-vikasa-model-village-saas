(() => {
  "use strict";
  if (!window.MV) return;
  const root = document.getElementById("visit-analytics");
  if (!root) return;
  const h = window.MV.escapeHtml;
  function barRows(data, emptyText) {
    const rows = Object.entries(data || {}).filter(([, v]) => Number.isFinite(Number(v)));
    if (!rows.length || rows.every(([, value]) => Number(value) <= 0)) {
      return `<p class="analytics-empty">${h(emptyText)}</p>`;
    }
    const max = Math.max(1, ...rows.map(([, v]) => Number(v)));
    return `<div class="analytics-bars">${rows.map(([k, v]) => {
      const number = Math.max(0, Number(v) || 0);
      const width = Math.min(100, 100 * number / max);
      return `<div class="analytics-bar-row"><div><span>${h(k)}</span><strong>${number.toLocaleString()}</strong></div><span class="analytics-bar-track"><i style="width:${width}%"></i></span></div>`;
    }).join("")}</div>`;
  }
  (async () => {
    try {
      const res = await window.MV.api("/api/v1/monitoring/series");
      if (!res.ok) throw new Error("Analytics could not be loaded. Please refresh or contact the program administrator.");
      const data = await res.json();
      Object.entries(data.counts || {}).forEach(([key, value]) => {
        const node = root.querySelector(`[data-analytics-kpi="${key}"]`);
        if (node) node.textContent = Number(value || 0).toLocaleString();
      });
      const charts = {
        completion: [data.status_breakdown, "No villages in scope"],
        gender: [data.gender_distribution, "No attendance submitted this month"],
        clusters: [data.cluster_breakdown, "No assigned villages in scope"],
        committees: [data.committee_aggregates, "No committee attendance submitted"],
      };
      Object.entries(charts).forEach(([key, [values, fallback]]) => {
        const node = document.getElementById(`analytics-${key}`);
        if (node) node.innerHTML = barRows(values, fallback);
      });
    } catch (error) {
      const notice = document.getElementById("analytics-alert");
      notice.textContent = error.message;
      notice.classList.remove("hidden");
    }
  })();
})();
