(() => {
  "use strict";
  const root = document.querySelector(".reports-page");
  if (!root) return;

  const month = document.getElementById("report-month");
  const type = document.getElementById("report-type");
  const status = document.getElementById("report-status");
  const search = document.getElementById("report-search");
  const list = document.getElementById("report-list");
  const label = document.getElementById("report-month-label");
  const exportLink = document.getElementById("report-export");
  const isAdmin = window.MV?.role === "admin";
  let rows = [];
  const esc = window.MV.escapeHtml;

  const monthDate = (value) => new Date(`${value}-01T00:00:00`);
  const monthValue = (value) => `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}`;
  const currentMonth = root.dataset.currentMonth || month.value;

  const params = () => {
    const p = new URLSearchParams({ month: month.value });
    if (type.value) p.set("type", type.value);
    if (status.value) p.set("status", status.value);
    return p;
  };

  const filtered = () => {
    const q = search.value.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((row) =>
      `${row.da} ${row.village} ${row.committee} ${row.type} ${row.status}`.toLowerCase().includes(q)
    );
  };

  const badge = (value) => `<span class="badge" data-status="${esc(value)}">${esc(value)}</span>`;

  const adminActions = (row, mobile = false) => {
    if (!isAdmin) return "";
    const editUrl = `/admin?resource=action-plans&edit=${encodeURIComponent(row.plan_id)}`;
    if (mobile) {
      return `<div class="report-row-admin-actions">
        <a class="button ghost" href="${editUrl}">Edit</a>
        <button class="button danger" type="button" data-report-delete="${esc(row.plan_id)}">Delete</button>
      </div>`;
    }
    return `<a class="button ghost compact-action" href="${editUrl}">Edit</a>
      <button class="button danger compact-action" type="button" data-report-delete="${esc(row.plan_id)}">Delete</button>`;
  };

  const render = () => {
    const data = filtered();
    if (!data.length) {
      list.innerHTML = `<div class="empty-state"><strong>No reports match.</strong><span>Change month or filters.</span></div>`;
      return;
    }

    list.innerHTML = `
      <div class="ledger-table-wrap desktop-ledger">
        <table class="ledger modern-ledger">
          <thead><tr><th>Date</th><th>DA</th><th>Village</th><th>Committee</th><th>Type</th><th>Status</th><th>Actions</th></tr></thead>
          <tbody>${data.map((row) => `<tr>
            <td>${esc(row.date || "\u2014")}</td>
            <td>${esc(row.da)}</td>
            <td>${esc(row.village)}</td>
            <td>${esc(row.committee)}</td>
            <td>${esc(row.type)}</td>
            <td>${badge(row.status)}</td>
            <td><div class="row-actions">
              <a class="button ghost compact-action" href="${esc(row.view_url)}">View</a>
              ${adminActions(row)}
            </div></td>
          </tr>`).join("")}</tbody>
        </table>
      </div>
      <div class="mobile-ledger">${data.map((row) => `<article class="ledger-card report-card">
        <div class="ledger-card-top"><div><strong>${esc(row.committee)}</strong><small>${esc(row.village)} \u00b7 ${esc(row.da)}</small></div>${badge(row.status)}</div>
        <div class="ledger-card-meta"><span>${esc(row.type)}</span><span>${esc(row.date || "\u2014")}</span></div>
        <a class="button ghost wide" href="${esc(row.view_url)}">View</a>
        ${adminActions(row, true)}
      </article>`).join("")}</div>`;
  };

  const deleteReport = async (planId) => {
    if (!isAdmin || !planId) return;
    const confirmed = window.confirm(
      "Move this report to the Recycle Bin? Linked field submission data will also be soft-deleted and can be restored by an administrator."
    );
    if (!confirmed) return;

    try {
      const response = await window.MV.api(`/api/v1/reports/plan/${encodeURIComponent(planId)}`, {
        method: "DELETE",
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.error || "Could not delete report.");
      window.MV.toast?.(payload.message || "Report moved to Recycle Bin.", "success");
      await load();
    } catch (error) {
      window.MV.toast?.(error.message, "error");
    }
  };

  const load = async () => {
    list.innerHTML = `<div class="skeleton-card">Loading reports...</div>`;
    const response = await window.MV.api(`/api/v1/reports?${params()}`);
    const payload = await response.json();
    if (!response.ok) {
      list.innerHTML = `<div class="form-alert">${esc(payload.error || "Could not load reports.")}</div>`;
      return;
    }
    rows = payload.items || [];
    label.textContent = payload.label;
    document.querySelectorAll("[data-report-metric]").forEach((node) => {
      const key = node.dataset.reportMetric;
      node.textContent = payload.summary?.[key] ?? 0;
    });
    exportLink.href = `/reports/export.xlsx?${params()}`;
    const url = new URL(window.location.href);
    url.searchParams.set("month", month.value);
    history.replaceState({}, "", url);
    render();
  };

  list.addEventListener("click", (event) => {
    const button = event.target.closest("[data-report-delete]");
    if (button) deleteReport(button.dataset.reportDelete);
  });

  const step = (delta) => {
    const value = monthDate(month.value);
    value.setMonth(value.getMonth() + delta);
    month.value = monthValue(value);
    load();
  };

  document.querySelectorAll("[data-month-step]").forEach((button) =>
    button.addEventListener("click", () => step(Number(button.dataset.monthStep)))
  );
  document.querySelector("[data-current-month]")?.addEventListener("click", () => {
    month.value = currentMonth;
    load();
  });
  month.addEventListener("change", load);
  type.addEventListener("change", load);
  status.addEventListener("change", load);
  search.addEventListener("input", render);
  load();
})();
