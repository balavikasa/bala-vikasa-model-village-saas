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
    const p = window.BVReporting ? window.BVReporting.params() : new URLSearchParams({ month: month.value });
    if(search.value.trim())p.set("q",search.value.trim());
    const selectedVillage = new URLSearchParams(location.search).get('village');
    if (selectedVillage) p.set('village', selectedVillage);
    if (type.value) p.set("type", type.value);
    if (status.value) p.set("status", status.value);
    return p;
  };

  const filtered = () => rows;

  const badge = (value) => `<span class="badge" data-status="${esc(value)}">${esc(value)}</span>`;

  const adminActions = (row, mobile = false) => {
    if (!isAdmin) return "";
    const editUrl = row.plan_id ? `/admin?resource=action-plans&edit=${encodeURIComponent(row.plan_id)}` : null;
    const edit = editUrl ? `<a class="button ghost compact-action" href="${editUrl}">Edit legacy plan</a>` : "";
    const deleteId = row.village_visit_id ? `data-village-delete="${Number(row.village_visit_id)}"` : `data-report-delete="${Number(row.plan_id)}"`;
    if (mobile) {
      return `<div class="report-row-admin-actions">
        ${edit}
        <button class="button danger" type="button" ${deleteId}>Delete</button>
      </div>`;
    }
    return `${edit}
      <button class="button danger compact-action" type="button" ${deleteId}>Delete</button>`;
  };

  const render = () => {
    const data = filtered();
    if (!data.length) {
      list.innerHTML = `<div class="empty-state"><strong>No reports match.</strong><span>Change the reporting period or filters.</span></div>`;
      return;
    }

    list.innerHTML = `
      <div class="ledger-table-wrap desktop-ledger">
        <table class="ledger modern-ledger">
          <thead><tr><th>Date</th><th>DA</th><th>Village</th><th>Coverage</th><th>Type</th><th>Status</th><th>Male</th><th>Female</th><th>Total</th><th>New members</th><th>Actions</th></tr></thead>
          <tbody>${data.map((row) => `<tr>
            <td>${esc(row.date || "\u2014")}</td>
            <td>${esc(row.da)}</td>
            <td>${esc(row.village)}</td>
            <td>${esc(row.committee)}<small>${esc(row.history_kind||"")}</small></td>
            <td>${esc(row.type)}</td>
            <td>${badge(row.status)}</td><td>${Number(row.male||0)}</td><td>${Number(row.female||0)}</td><td>${Number(row.people_attended||0)}</td><td>${Number(row.new_members||0)}</td>
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
        <p>Male ${Number(row.male||0)} + Female ${Number(row.female||0)} = <strong>${Number(row.people_attended||0)} attendances</strong> &middot; New members ${Number(row.new_members||0)}</p><small>${esc(row.history_kind||"")}</small><a class="button ghost wide" href="${esc(row.view_url)}">View</a>
        ${adminActions(row, true)}
      </article>`).join("")}</div>`;
  };

  const deleteReport = async (planId, villageVisit = false) => {
    if (!isAdmin || !planId) return;
    const confirmed = window.confirm(
      "Move this report to the Recycle Bin? Linked field submission data will also be soft-deleted and can be restored by an administrator."
    );
    if (!confirmed) return;

    try {
      const url = villageVisit ? `/api/v1/reports/village/${encodeURIComponent(planId)}` : `/api/v1/reports/plan/${encodeURIComponent(planId)}`;
      const response = await window.MV.api(url, {
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

  let loadId=0;
  const load = async () => {
    const id=++loadId, requestParams=params();
    exportLink.removeAttribute("href");exportLink.setAttribute("aria-disabled","true");
    try {
    list.innerHTML = `<div class="skeleton-card">Loading reports...</div>`;
    const response = await window.MV.api(`/api/v1/reports?${requestParams}`);
    const payload = await response.json();
    if(id!==loadId)return;
    if (!response.ok) {
      throw new Error(payload.error || "Could not load reports.");
    }
    rows = payload.items || [];
    label.textContent = payload.label;
    document.querySelectorAll("[data-report-metric]").forEach((node) => {
      const key = node.dataset.reportMetric;
      node.textContent = payload.summary?.[key] ?? 0;
    });
    exportLink.href = `/reports/export.xlsx?${requestParams}`;
    exportLink.setAttribute("aria-disabled","false");
    const url = new URL(window.location.href);
    ["q","type","status","period","date","month","year","from","to"].forEach(key=>url.searchParams.delete(key));
    requestParams.forEach((value,key)=>url.searchParams.set(key,value));
    history.replaceState({}, "", url);
    render();
    }catch(error){if(id!==loadId)return;rows=[];list.innerHTML=`<div class="form-alert">${esc(error.message||"Reports unavailable. Retry this selection.")}</div>`;document.querySelectorAll('[data-report-metric]').forEach(n=>n.textContent='—');}
  };

  list.addEventListener("click", (event) => {
    const button = event.target.closest("[data-report-delete]");
    if (button) return deleteReport(button.dataset.reportDelete);
    const villageButton = event.target.closest("[data-village-delete]");
    if (villageButton) return deleteReport(villageButton.dataset.villageDelete, true);
  });

  const step = (delta) => {
    const value = monthDate(month.value);
    value.setMonth(value.getMonth() + delta);
    month.value = monthValue(value);
    window.BVReporting?.set({period:"month",month:month.value});
  };

  document.querySelectorAll("[data-month-step]").forEach((button) =>
    button.addEventListener("click", () => step(Number(button.dataset.monthStep)))
  );
  document.querySelector("button[data-current-month]")?.addEventListener("click", () => {
    month.value = currentMonth;
    window.BVReporting.set({period:"this_month"});
  });
  month.addEventListener("change", ()=>window.BVReporting.set({period:"month",month:month.value}));
  type.addEventListener("change", load);
  status.addEventListener("change", load);
  let searchTimer;
  search.addEventListener("input", ()=>{++loadId;exportLink.removeAttribute("href");exportLink.setAttribute("aria-disabled","true");document.querySelectorAll("[data-report-metric]").forEach(n=>n.textContent="\u2014");clearTimeout(searchTimer);searchTimer=setTimeout(load,250);});
  document.addEventListener("bv:period-change",load);
  search.value=new URLSearchParams(location.search).get("q")||"";
  load();
})();
