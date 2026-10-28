(() => {
  "use strict";
  if (!window.MV) return;

  const renderStatus = (values) => {
    const host = document.querySelector("#status-breakdown");
    if (!host) return;
    const entries = Object.entries(values || {});
    if (!entries.length) {
      host.innerHTML = '<div class="empty-state"><p>No village attendance yet.</p></div>';
      return;
    }
    const max = Math.max(...entries.map(([, value]) => Number(value)), 1);
    const order = ["Done", "Not done"];
    entries.sort((a, b) => {
      const ai = order.indexOf(a[0]), bi = order.indexOf(b[0]);
      return (ai < 0 ? 99 : ai) - (bi < 0 ? 99 : bi);
    });
    host.innerHTML = entries.map(([status, value]) => `
      <div class="status-row">
        <label>${window.MV.escapeHtml(status)}</label>
        <span class="status-track"><i class="status-fill" data-status="${window.MV.escapeHtml(status)}" style="width:${Math.max(0, Number(value) / max * 100)}%"></i></span>
        <strong>${Number(value).toLocaleString()}</strong>
      </div>`).join("");
  };

  (async () => {
    try {
      const response = await window.MV.api("/api/v1/monitoring/summary");
      if (!response.ok) throw new Error("Summary unavailable");
      const data = await response.json();
      const counts = data.counts || {};
      const values = {
        villages: counts.villages || 0,
        committees: counts.committees || 0,
        villages_done: counts.villages_done || 0,
        villages_pending: counts.villages_pending || 0,
        people_attended: counts.people_attended || 0,
        new_members: counts.new_members || 0,
      };
      Object.entries(values).forEach(([key, value]) => {
        const node = document.querySelector(`[data-kpi="${key}"]`);
        if (node) node.textContent = Number(value).toLocaleString();
      });
      renderStatus(data.status_breakdown);
    } catch (_) {
      document.querySelectorAll("[data-kpi]").forEach((node) => { node.textContent = "—"; });
      renderStatus({});
    }
  })();
})();
