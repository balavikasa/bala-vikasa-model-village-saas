(() => {
  "use strict";
  const root = document.querySelector(".transfer-page");
  if (!root) return;
  const month = document.getElementById("transfer-month");
  const exportLink = document.getElementById("export-workbook");
  const file = document.getElementById("import-file");
  const fileName = document.getElementById("import-file-name");
  const validate = document.getElementById("validate-import");
  const preview = document.getElementById("import-preview");
  const rowsHost = document.getElementById("preview-rows");
  const confirmButton = document.getElementById("confirm-import");
  const error = document.getElementById("import-error");
  let token = null;

  const esc = window.MV.escapeHtml;
  const monthValue = (date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
  if (!new URLSearchParams(window.location.search).has("month")) {
    month.value = monthValue(new Date());
  }
  const syncLinks = () => {
    exportLink.href = `/action-plans/export.xlsx?month=${encodeURIComponent(month.value)}`;
    const u = new URL(window.location.href); u.searchParams.set("month", month.value); history.replaceState({}, "", u);
  };
  month.addEventListener("change", () => { syncLinks(); clearPreview(); });
  syncLinks();

  file?.addEventListener("change", () => {
    fileName.textContent = file.files?.[0]?.name || "No file selected";
    clearPreview();
  });

  const clearPreview = () => {
    token = null;
    preview?.classList.add("hidden");
    if (rowsHost) rowsHost.innerHTML = "";
    if (error) { error.classList.add("hidden"); error.textContent = ""; }
  };
  document.getElementById("clear-preview")?.addEventListener("click", clearPreview);

  const actionBadge = (value) => `<span class="badge import-${value.toLowerCase()}">${esc(value)}</span>`;

  validate?.addEventListener("click", async () => {
    const selected = file.files?.[0];
    if (!selected) return window.MV.toast("Choose the edited action-plan workbook.", "error");
    validate.disabled = true;
    error?.classList.add("hidden");
    try {
      const data = new FormData();
      data.append("month", month.value);
      data.append("file", selected, selected.name);
      const response = await window.MV.api("/api/v1/planning/import/preview", { method: "POST", body: data });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Could not validate workbook.");
      token = payload.token;
      const p = payload.preview;
      document.getElementById("preview-title").textContent = `${p.month_label} changes`;
      Object.entries(p.counts).forEach(([key, value]) => {
        const node = document.querySelector(`[data-preview="${key}"]`);
        if (node) node.textContent = value;
      });
      rowsHost.innerHTML = `
        <div class="ledger-table-wrap desktop-ledger"><table class="ledger modern-ledger">
          <thead><tr><th>Row</th><th>DA</th><th>Village</th><th>Committee</th><th>Type</th><th>Date</th><th>Result</th></tr></thead>
          <tbody>${p.rows.map((r) => `<tr><td>${r.excel_row}</td><td>${esc(r.da_name)}</td><td>${esc(r.village_name)}</td><td>${esc(r.committee_name)}</td><td>${esc(r.plan_type || "Draft")}</td><td>${esc(r.assigned_date || "—")}</td><td>${actionBadge(r.action)}${r.errors?.length ? `<small class="row-error">${esc(r.errors.join(" "))}</small>` : ""}</td></tr>`).join("")}</tbody>
        </table></div>
        <div class="mobile-ledger">${p.rows.map((r) => `<article class="ledger-card"><div class="ledger-card-top"><div><strong>${esc(r.committee_name || `Excel row ${r.excel_row}`)}</strong><small>${esc(r.village_name)} · ${esc(r.da_name)}</small></div>${actionBadge(r.action)}</div><div class="ledger-card-meta"><span>${esc(r.plan_type || "Draft")}</span><span>${esc(r.assigned_date || "—")}</span></div>${r.errors?.length ? `<p class="row-error">${esc(r.errors.join(" "))}</p>` : ""}</article>`).join("")}</div>`;
      confirmButton.disabled = p.has_errors;
      document.getElementById("preview-note").textContent = p.has_errors ? "Fix the workbook errors and validate again. Nothing has been saved." : "Validation passed. Confirm to save all New/Changed rows in one transaction.";
      preview.classList.remove("hidden");
      preview.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (ex) {
      error.textContent = ex.message;
      error.classList.remove("hidden");
      preview.classList.remove("hidden");
    } finally {
      validate.disabled = false;
    }
  });

  confirmButton?.addEventListener("click", async () => {
    if (!token) return;
    confirmButton.disabled = true;
    try {
      const response = await window.MV.api("/api/v1/planning/import/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, month: month.value }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Import failed.");
      window.MV.toast(`Import complete: ${payload.created} new, ${payload.updated} changed`, "success");
      window.location.href = `/action-plans?month=${encodeURIComponent(month.value)}`;
    } catch (ex) {
      error.textContent = ex.message;
      error.classList.remove("hidden");
      confirmButton.disabled = false;
    }
  });
})();