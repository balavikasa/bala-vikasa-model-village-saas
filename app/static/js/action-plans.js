(() => {
  "use strict";

  const root = document.querySelector(".planning-page");
  if (!root) return;

  const monthInput = document.getElementById("planning-month");
  const label = document.getElementById("month-label");
  const list = document.getElementById("plan-list");
  const search = document.getElementById("plan-search");
  const statusFilter = document.getElementById("plan-status-filter");
  const transferLink = document.querySelector("[data-transfer-link]");
  const canManage = root.dataset.canManage === "1";
  const dialog = document.getElementById("plan-edit-dialog");
  const form = document.getElementById("plan-edit-form");
  let rows = [];

  const monthDate = (value) => new Date(`${value}-01T00:00:00`);
  const monthValue = (date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
  const currentMonth = root.dataset.currentMonth || monthInput.value;
  const esc = window.MV.escapeHtml;

  const serverEpoch = Date.parse(root.dataset.serverNow || new Date().toISOString());
  const pageLoadedAt = Date.now();
  const appTimeZone = root.dataset.appTimezone || "Asia/Kolkata";
  const updateToday = () => {
    const node = document.querySelector("[data-today-stamp]");
    if (!node) return;
    const now = new Date(serverEpoch + (Date.now() - pageLoadedAt));
    node.innerHTML = `<strong>${new Intl.DateTimeFormat(undefined, { weekday: "long", timeZone: appTimeZone }).format(now)}</strong><span>${new Intl.DateTimeFormat(undefined, { dateStyle: "long", timeZone: appTimeZone }).format(now)}</span><small>${new Intl.DateTimeFormat(undefined, { timeStyle: "short", timeZone: appTimeZone }).format(now)}</small>`;
  };
  updateToday();
  window.setInterval(updateToday, 60000);

  const badge = (status) => `<span class="badge" data-status="${esc(status)}">${esc(status)}</span>`;

  const renderMetrics = (summary) => {
    Object.entries(summary || {}).forEach(([key, value]) => {
      document.querySelector(`[data-metric="${key}"]`)?.replaceChildren(document.createTextNode(value));
    });
  };

  const filtered = () => {
    const q = (search?.value || "").trim().toLowerCase();
    const status = statusFilter?.value || "";
    return rows.filter((row) => {
      const hay = `${row.da_name} ${row.village_name} ${row.committee_name} ${row.plan_type || ""}`.toLowerCase();
      return (!q || hay.includes(q)) && (!status || row.status === status);
    });
  };

  const render = () => {
    const data = filtered();
    if (!data.length) {
      list.innerHTML = `<div class="empty-state"><strong>No action plans match.</strong><span>Change the filters or planning month.</span></div>`;
      return;
    }
    list.innerHTML = `
      <div class="ledger-table-wrap desktop-ledger">
        <table class="ledger modern-ledger">
          <thead><tr><th>DA</th><th>Village</th><th>Committee</th><th>Type</th><th>Assigned</th><th>Status</th>${canManage ? "<th></th>" : ""}</tr></thead>
          <tbody>${data.map((row) => `<tr>
            <td>${esc(row.da_name)}</td><td>${esc(row.village_name)}</td><td>${esc(row.committee_name)}</td>
            <td>${esc(row.plan_type || "Draft")}</td><td>${esc(row.assigned_date || "—")}</td><td>${badge(row.status)}</td>
            ${canManage ? `<td>${row.locked ? '<span class="mono muted">Locked</span>' : `<button class="text-button" type="button" data-edit-plan="${row.plan_id || ""}" data-committee-id="${row.committee_id}">Edit</button>`}</td>` : ""}
          </tr>`).join("")}</tbody>
        </table>
      </div>
      <div class="mobile-ledger">${data.map((row) => `<article class="ledger-card">
        <div class="ledger-card-top"><div><strong>${esc(row.committee_name)}</strong><small>${esc(row.village_name)} · ${esc(row.da_name)}</small></div>${badge(row.status)}</div>
        <div class="ledger-card-meta"><span>${esc(row.plan_type || "Draft")}</span><span>${esc(row.assigned_date || "Not assigned")}</span></div>
        ${canManage ? (row.locked ? '<span class="mono muted">Immutable history</span>' : `<button class="button ghost wide" type="button" data-edit-plan="${row.plan_id || ""}" data-committee-id="${row.committee_id}">Edit plan</button>`) : ""}
      </article>`).join("")}</div>`;
  };

  const load = async () => {
    list.innerHTML = `<div class="skeleton-card">Loading action plans…</div>`;
    const response = await window.MV.api(`/api/v1/planning/month?month=${encodeURIComponent(monthInput.value)}`);
    const payload = await response.json();
    if (!response.ok) {
      list.innerHTML = `<div class="form-alert">${esc(payload.error || "Could not load action plans.")}</div>`;
      return;
    }
    rows = payload.rows || [];
    label.textContent = payload.label;
    renderMetrics(payload.summary);
    if (transferLink) transferLink.href = `/action-plans/transfer?month=${encodeURIComponent(monthInput.value)}`;
    const url = new URL(window.location.href);
    url.searchParams.set("month", monthInput.value);
    history.replaceState({}, "", url);
    render();
  };

  const stepMonth = (delta) => {
    const d = monthDate(monthInput.value);
    d.setMonth(d.getMonth() + delta);
    monthInput.value = monthValue(d);
    load();
  };
  document.querySelectorAll("[data-month-step]").forEach((button) => button.addEventListener("click", () => stepMonth(Number(button.dataset.monthStep))));
  document.querySelector("[data-current-month]")?.addEventListener("click", () => {
    monthInput.value = currentMonth;
    load();
  });
  monthInput.addEventListener("change", load);
  search?.addEventListener("input", render);
  statusFilter?.addEventListener("change", render);

  const rowByPlan = (planId, committeeId) => rows.find((r) => (planId && String(r.plan_id) === String(planId)) || (!planId && String(r.committee_id) === String(committeeId)));

  list.addEventListener("click", (event) => {
    const button = event.target.closest("[data-edit-plan]");
    if (!button || !canManage || !dialog) return;
    const row = rowByPlan(button.dataset.editPlan, button.dataset.committeeId);
    if (!row) return;
    document.getElementById("plan-edit-id").value = row.plan_id || "";
    form.dataset.committeeId = row.committee_id;
    document.getElementById("plan-edit-title").textContent = `${row.village_name} · ${row.committee_name}`;
    document.getElementById("plan-edit-type").value = row.plan_type || "";
    document.getElementById("plan-edit-date").value = row.assigned_date || "";
    document.getElementById("plan-edit-notes").value = row.notes || "";
    document.getElementById("plan-edit-error").classList.add("hidden");
    dialog.showModal();
  });
  document.querySelectorAll("[data-close-plan]").forEach((button) => button.addEventListener("click", () => dialog?.close()));

  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const error = document.getElementById("plan-edit-error");
    error.classList.add("hidden");
    const planId = document.getElementById("plan-edit-id").value;
    const payload = {
      month: monthInput.value,
      committee_id: Number(form.dataset.committeeId),
      plan_type: document.getElementById("plan-edit-type").value,
      assigned_date: document.getElementById("plan-edit-date").value,
      notes: document.getElementById("plan-edit-notes").value,
    };
    const url = planId ? `/api/v1/planning/plans/${planId}` : "/api/v1/planning/plans";
    const response = await window.MV.api(url, {
      method: planId ? "PATCH" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) {
      error.textContent = result.error || "Could not save the plan.";
      error.classList.remove("hidden");
      return;
    }
    dialog.close();
    window.MV.toast("Action plan saved", "success");
    load();
  });

  document.getElementById("prepare-next-month")?.addEventListener("click", async (event) => {
    const button = event.currentTarget;
    if (!confirm(`Prepare the month after ${label.textContent}? Dates are intentionally not copied.`)) return;
    button.disabled = true;
    try {
      const response = await window.MV.api("/api/v1/planning/prepare-next-month", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ month: monthInput.value }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Could not prepare next month.");
      window.MV.toast(`Prepared ${result.created} plans for ${result.target_month}`, "success");
      monthInput.value = result.target_month;
      load();
    } catch (error) {
      window.MV.toast(error.message, "error");
    } finally {
      button.disabled = false;
    }
  });

  load();
})();