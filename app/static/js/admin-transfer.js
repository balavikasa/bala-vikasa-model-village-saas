(() => {
  "use strict";
  const root = document.querySelector("[data-master-transfer]");
  if (!root || !window.MV) return;
  const exportResource = document.getElementById("master-export-resource");
  const importResource = document.getElementById("master-import-resource");
  const exportLink = document.getElementById("master-export-link");
  const file = document.getElementById("master-import-file");
  const fileLabel = document.getElementById("master-file-label");
  const previewButton = document.getElementById("master-preview");
  const confirmButton = document.getElementById("master-confirm");
  const error = document.getElementById("master-transfer-error");
  const panel = document.getElementById("master-preview-panel");
  const list = document.getElementById("master-preview-list");
  const title = document.getElementById("master-preview-title");
  const esc = window.MV.escapeHtml;
  let token = null;
  let preview = null;

  const updateExport = () => {
    exportLink.href = `/admin/data-transfer/export.xlsx?resource=${encodeURIComponent(exportResource.value)}`;
  };
  exportResource.addEventListener("change", updateExport);
  updateExport();

  file.addEventListener("change", () => {
    token = null;
    preview = null;
    panel.classList.add("hidden");
    fileLabel.textContent = file.files[0]?.name || ".xlsx only · preview before save";
  });

  const setError = (message = "") => {
    error.textContent = message;
    error.classList.toggle("hidden", !message);
  };

  const render = () => {
    if (!preview) return;
    panel.classList.remove("hidden");
    title.textContent = `${preview.label} changes`;
    for (const [key, value] of Object.entries(preview.counts || {})) {
      document.querySelector(`[data-master-count="${key}"]`)?.replaceChildren(document.createTextNode(value));
    }
    const rows = preview.rows || [];
    list.innerHTML = `
      <div class="ledger-table-wrap desktop-ledger">
        <table class="ledger modern-ledger"><thead><tr><th>Excel row</th><th>ID</th><th>Record</th><th>Action</th><th>Issues</th></tr></thead>
        <tbody>${rows.map((row) => `<tr>
          <td>${row.excel_row}</td><td>${row.id || "New"}</td><td>${esc(row.name || "—")}</td>
          <td><span class="badge" data-status="${esc(row.action)}">${esc(row.action)}</span></td>
          <td>${row.errors?.length ? esc(row.errors.join(" · ")) : "—"}</td>
        </tr>`).join("")}</tbody></table>
      </div>
      <div class="mobile-ledger">${rows.map((row) => `<article class="ledger-card">
        <div class="ledger-card-top"><div><strong>${esc(row.name || "Record")}</strong><small>Excel row ${row.excel_row} · ${row.id ? `ID ${row.id}` : "New record"}</small></div><span class="badge" data-status="${esc(row.action)}">${esc(row.action)}</span></div>
        ${row.errors?.length ? `<div class="form-alert">${esc(row.errors.join(" · "))}</div>` : ""}
      </article>`).join("")}</div>`;
    confirmButton.disabled = Boolean(preview.has_errors) || !(Number(preview.counts?.New || 0) + Number(preview.counts?.Changed || 0) + Number(preview.counts?.Moved || 0));
  };

  previewButton.addEventListener("click", async () => {
    setError();
    if (!file.files[0]) return setError("Choose the exported .xlsx workbook first.");
    previewButton.disabled = true;
    token = null;
    const form = new FormData();
    form.append("resource", importResource.value);
    form.append("file", file.files[0]);
    try {
      const response = await window.MV.api("/api/v1/admin/data-transfer/preview", { method: "POST", body: form });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Could not validate workbook.");
      token = payload.token;
      preview = payload.preview;
      render();
      panel.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (e) {
      setError(e.message);
    } finally {
      previewButton.disabled = false;
    }
  });

  confirmButton.addEventListener("click", async () => {
    if (!token || !preview || preview.has_errors) return;
    if (!confirm(`Apply the previewed ${preview.label} changes? This is atomic and audit-logged.`)) return;
    confirmButton.disabled = true;
    try {
      const response = await window.MV.api("/api/v1/admin/data-transfer/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, resource: importResource.value }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Import could not be completed.");
      window.MV.toast(`Import complete · ${payload.created} new · ${payload.updated} updated · ${payload.moved} moved`, "success");
      token = null;
      preview = null;
      panel.classList.add("hidden");
      file.value = "";
      fileLabel.textContent = ".xlsx only · preview before save";
    } catch (e) {
      setError(e.message);
      confirmButton.disabled = false;
    }
  });
})();