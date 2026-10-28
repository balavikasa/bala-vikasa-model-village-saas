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
      const values = counts;
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
  (async () => {
    const recentNode = document.getElementById('renewal-recent-visits');
    const pendingNode = document.getElementById('renewal-pending-villages');
    if (!recentNode || !pendingNode) return;
    try {
      const response = await window.MV.api('/api/v1/monitoring/recent');
      if (!response.ok) throw new Error('Recent visits unavailable.');
      const data = await response.json();
      const esc = window.MV.escapeHtml;
      recentNode.innerHTML = data.recent.length ? data.recent.map((visit) => `
        <a class="renewal-activity-row" href="${visit.report_url}">
          <span class="renewal-row-icon">✓</span>
          <span><strong>${esc(visit.village)}</strong><small>${esc(visit.date)} · ${Number(visit.people).toLocaleString()} people${visit.outside_assignment ? ' · Other village' : ''}</small></span>
          <b aria-hidden="true">›</b>
        </a>`).join('') : '<p class="analytics-empty">No attendance submissions yet.</p>';
      pendingNode.innerHTML = data.pending.length ? data.pending.map((village) => `
        <a class="renewal-activity-row" href="${village.url}">
          <span class="renewal-row-icon pending">⌂</span><span><strong>${esc(village.name)}</strong><small>Not visited this month</small></span>
          <b aria-hidden="true">›</b>
        </a>`).join('') : '<p class="analytics-empty">All assigned villages have a recorded visit this month.</p>';
      if (data.pending_total > data.pending.length) pendingNode.insertAdjacentHTML('beforeend',
        `<p class="muted">${Number(data.pending_total-data.pending.length).toLocaleString()} more pending villages. View My Villages for the full list.</p>`);
    } catch(error) {
      recentNode.textContent = error.message;
      pendingNode.textContent = 'Village coverage list is unavailable.';
    }
  })();
})();
