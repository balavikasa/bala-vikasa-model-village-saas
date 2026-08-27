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

  const monthValue = (date) =>
    `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;

  const showError = (message) => {
    if (!error) return;

    error.textContent = message || "Something went wrong.";
    error.classList.remove("hidden");

    error.scrollIntoView({
      behavior: "smooth",
      block: "center",
    });
  };

  const clearError = () => {
    if (!error) return;

    error.textContent = "";
    error.classList.add("hidden");
  };

  const readJson = async (response) => {
    try {
      return await response.json();
    } catch (_) {
      return {};
    }
  };

  const clearPreview = () => {
    token = null;

    preview?.classList.add("hidden");

    if (rowsHost) {
      rowsHost.innerHTML = "";
    }

    clearError();

    if (confirmButton) {
      confirmButton.disabled = true;
    }
  };

  if (!new URLSearchParams(window.location.search).has("month")) {
    month.value = monthValue(new Date());
  }

  const syncLinks = () => {
    exportLink.href =
      `/action-plans/export.xlsx?month=${encodeURIComponent(month.value)}`;

    const url = new URL(window.location.href);

    url.searchParams.set(
      "month",
      month.value
    );

    history.replaceState(
      {},
      "",
      url
    );
  };

  month.addEventListener("change", () => {
    syncLinks();
    clearPreview();
  });

  syncLinks();

  file?.addEventListener("change", () => {
    fileName.textContent =
      file.files?.[0]?.name || "No file selected";

    clearPreview();
  });

  document
    .getElementById("clear-preview")
    ?.addEventListener(
      "click",
      clearPreview
    );

  const actionBadge = (value) =>
    `<span class="badge import-${value.toLowerCase()}">${esc(value)}</span>`;

  validate?.addEventListener(
    "click",
    async () => {
      const selected =
        file.files?.[0];

      if (!selected) {
        window.MV.toast(
          "Choose the edited action-plan workbook.",
          "error"
        );

        return;
      }

      clearError();
      clearPreview();

      validate.disabled = true;

      try {
        const data =
          new FormData();

        data.append(
          "month",
          month.value
        );

        data.append(
          "file",
          selected,
          selected.name
        );

        const response =
          await window.MV.api(
            "/api/v1/planning/import/preview",
            {
              method: "POST",
              body: data,
            }
          );

        const payload =
          await readJson(response);

        if (!response.ok) {
          throw new Error(
            payload.error ||
            `Could not validate workbook. Server returned ${response.status}.`
          );
        }

        if (!payload.token) {
          throw new Error(
            "The server validated the workbook but did not return an import token."
          );
        }

        if (!payload.preview) {
          throw new Error(
            "The server did not return an import preview."
          );
        }

        token =
          payload.token;

        const p =
          payload.preview;

        const previewTitle =
          document.getElementById(
            "preview-title"
          );

        if (previewTitle) {
          previewTitle.textContent =
            `${p.month_label} changes`;
        }

        Object
          .entries(
            p.counts || {}
          )
          .forEach(
            ([key, value]) => {
              const node =
                document.querySelector(
                  `[data-preview="${key}"]`
                );

              if (node) {
                node.textContent =
                  value;
              }
            }
          );

        const rows =
          Array.isArray(p.rows)
            ? p.rows
            : [];

        rowsHost.innerHTML = `
          <div class="ledger-table-wrap desktop-ledger">
            <table class="ledger modern-ledger">
              <thead>
                <tr>
                  <th>Row</th>
                  <th>DA</th>
                  <th>Village</th>
                  <th>Committee</th>
                  <th>Type</th>
                  <th>Date</th>
                  <th>Result</th>
                </tr>
              </thead>
              <tbody>
                ${rows
                  .map(
                    (r) => `
                      <tr>
                        <td>${Number(r.excel_row || 0)}</td>

                        <td>${esc(r.da_name || "")}</td>

                        <td>${esc(r.village_name || "")}</td>

                        <td>${esc(r.committee_name || "")}</td>

                        <td>${esc(r.plan_type || "Draft")}</td>

                        <td>${esc(r.assigned_date || "—")}</td>

                        <td>
                          ${actionBadge(r.action)}

                          ${
                            r.errors?.length
                              ? `
                                <small class="row-error">
                                  ${esc(r.errors.join(" "))}
                                </small>
                              `
                              : ""
                          }
                        </td>
                      </tr>
                    `
                  )
                  .join("")}
              </tbody>
            </table>
          </div>

          <div class="mobile-ledger">
            ${rows
              .map(
                (r) => `
                  <article class="ledger-card">
                    <div class="ledger-card-top">
                      <div>
                        <strong>
                          ${esc(
                            r.committee_name ||
                            `Excel row ${r.excel_row}`
                          )}
                        </strong>

                        <small>
                          ${esc(r.village_name || "")}
                          ·
                          ${esc(r.da_name || "")}
                        </small>
                      </div>

                      ${actionBadge(r.action)}
                    </div>

                    <div class="ledger-card-meta">
                      <span>
                        ${esc(r.plan_type || "Draft")}
                      </span>

                      <span>
                        ${esc(r.assigned_date || "—")}
                      </span>
                    </div>

                    ${
                      r.errors?.length
                        ? `
                          <p class="row-error">
                            ${esc(r.errors.join(" "))}
                          </p>
                        `
                        : ""
                    }
                  </article>
                `
              )
              .join("")}
          </div>
        `;

        confirmButton.disabled =
          Boolean(p.has_errors);

        const previewNote =
          document.getElementById(
            "preview-note"
          );

        if (previewNote) {
          previewNote.textContent =
            p.has_errors
              ? (
                "Fix the workbook errors and validate again. " +
                "Nothing has been saved."
              )
              : (
                "Validation passed. Confirm to save all " +
                "New/Changed rows in one transaction."
              );
        }

        preview.classList.remove(
          "hidden"
        );

        preview.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });

      } catch (ex) {
        showError(
          ex?.message ||
          "Could not validate workbook."
        );

        preview?.classList.remove(
          "hidden"
        );

      } finally {
        validate.disabled =
          false;
      }
    }
  );

  confirmButton?.addEventListener(
    "click",
    async () => {
      clearError();

      if (!token) {
        showError(
          "Import preview token is missing. " +
          "Validate the workbook again."
        );

        return;
      }

      confirmButton.disabled =
        true;

      const originalText =
        confirmButton.textContent;

      confirmButton.textContent =
        "Importing…";

      try {
        const response =
          await window.MV.api(
            "/api/v1/planning/import/confirm",
            {
              method: "POST",

              headers: {
                "Content-Type":
                  "application/json",
              },

              body: JSON.stringify({
                token,
                month: month.value,
              }),
            }
          );

        const payload =
          await readJson(response);

        if (!response.ok) {
          throw new Error(
            payload.error ||
            `Import failed with server status ${response.status}.`
          );
        }

        const created =
          Number(
            payload.created || 0
          );

        const updated =
          Number(
            payload.updated || 0
          );

        window.MV.toast(
          (
            `Import complete: ${created} new, ` +
            `${updated} changed`
          ),
          "success"
        );

        token =
          null;

        window.location.href =
          (
            "/action-plans?month=" +
            encodeURIComponent(
              month.value
            )
          );

      } catch (ex) {
        showError(
          ex?.message ||
          "Import failed. No rows were saved."
        );

        confirmButton.disabled =
          false;

        confirmButton.textContent =
          originalText;
      }
    }
  );
})();