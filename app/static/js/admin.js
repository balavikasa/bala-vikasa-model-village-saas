(() => {
  "use strict";

  const root = document.querySelector("[data-admin-root]");
  if (!root || !window.MV) return;

  const deepLink = new URLSearchParams(window.location.search);

  const state = {
    resources: {},
    resource: "",
    page: 1,
    perPage: deepLink.get("edit") ? 500 : 25,
    total: 0,
    records: [],
    editing: null,
    relationships: new Map(),
    auditRows: [],
  };

  const $ = (selector, scope = document) => scope.querySelector(selector);
  const $$ = (selector, scope = document) => [...scope.querySelectorAll(selector)];
  const status = $("#admin-status");
  const resourceSelect = $("#admin-resource");
  const searchInput = $("#admin-search");
  const table = $("#admin-table");
  const empty = $("#admin-empty");
  const dialog = $("#admin-dialog");
  const form = $("#admin-form");
  const fieldsHost = $("#admin-fields");
  const formError = $("#admin-form-error");
  const moveAckRow = $("#move-ack-row");
  const moveAck = $("#move-ack");

  const escapeHtml = (value) => String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

  const labelize = (name) => name
    .replace(/_id$/, "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (m) => m.toUpperCase());

  const setStatus = (message, kind = "") => {
    status.textContent = message;
    status.dataset.kind = kind;
  };

  const showError = (message) => {
    formError.textContent = message;
    formError.classList.remove("hidden");
  };

  const clearError = () => {
    formError.textContent = "";
    formError.classList.add("hidden");
  };

  const api = async (url, options = {}) => {
    const response = await window.MV.api(url, options);
    if (!response.ok) {
      let payload = {};
      try { payload = await response.json(); } catch (_) { /* no JSON */ }
      const error = new Error(payload.error || payload.message || `Request failed (${response.status})`);
      error.status = response.status;
      error.payload = payload;
      throw error;
    }
    if (response.status === 204) return null;
    return response.json();
  };

  const resourceMeta = () => state.resources[state.resource] || {};
  const fieldMeta = () => resourceMeta().fields || [];

  const displayValue = (record, key) => {
    const value = record[key];
    if (typeof value === "boolean") return value ? "Yes" : "No";
    if (Array.isArray(value)) return value.join(", ");
    if (value && typeof value === "object") return JSON.stringify(value);
    if (value === null || value === undefined || value === "") return "—";
    if (key.endsWith("_at") || key.endsWith("_date") || key === "assigned_date" || key === "visit_date") {
      const date = new Date(value);
      if (!Number.isNaN(date.valueOf())) {
        return key.endsWith("_at")
          ? new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date)
          : new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(date);
      }
    }
    return String(value);
  };

  const preferredColumns = (records) => {
    const meta = resourceMeta();
    const configured = meta.columns || [];
    if (configured.length) return configured;
    const keys = records.length ? Object.keys(records[0]) : fieldMeta().map((f) => f.name);
    const first = ["id", "name", "full_name", "title", "email", "mobile", "role", "cluster", "village_name",
      "committee_name", "assigned_date", "visit_date", "status", "is_enabled", "created_at"];
    return [...new Set([...first.filter((key) => keys.includes(key)), ...keys])]
      .filter((key) => !["password_hash", "snapshot_json", "before_json", "after_json", "photo_path"].includes(key))
      .slice(0, 8);
  };

  const renderTable = () => {
    const columns = preferredColumns(state.records);
    table.tHead.innerHTML = `<tr>${columns.map((key) => `<th>${escapeHtml(labelize(key))}</th>`).join("")}<th>Actions</th></tr>`;
    table.tBodies[0].innerHTML = state.records.map((record) => {
      const inactive = record.is_enabled === false ? " is-muted" : "";
      return `<tr class="${inactive}" data-id="${escapeHtml(record.id)}">
        ${columns.map((key) => `<td data-label="${escapeHtml(labelize(key))}">${escapeHtml(displayValue(record, key))}</td>`).join("")}
        <td data-label="Actions">
          <div class="row-actions">
            <button class="text-button" type="button" data-edit="${escapeHtml(record.id)}">Edit</button>
            ${Object.hasOwn(record, "is_enabled") ? `<button class="text-button" type="button" data-toggle="${escapeHtml(record.id)}">${record.is_enabled ? "Disable" : "Enable"}</button>` : ""}
            ${Object.hasOwn(record, "is_deleted") && !record.is_deleted ? `<button class="text-button danger-text" type="button" data-delete="${escapeHtml(record.id)}">Delete</button>` : ""}
          </div>
        </td>
      </tr>`;
    }).join("");

    empty.classList.toggle("hidden", state.records.length !== 0);
    table.closest(".table-shell").classList.toggle("hidden", state.records.length === 0);
    $("#admin-page-label").textContent = `Page ${state.page} · ${state.total} record${state.total === 1 ? "" : "s"}`;
    $("#admin-prev").disabled = state.page <= 1;
    $("#admin-next").disabled = state.page * state.perPage >= state.total;

    $$("[data-edit]", table).forEach((button) => button.addEventListener("click", () => openEditor(button.dataset.edit)));
    $$("[data-toggle]", table).forEach((button) => button.addEventListener("click", () => toggleRecord(button.dataset.toggle)));
    $$("[data-delete]", table).forEach((button) => button.addEventListener("click", () => deleteRecord(button.dataset.delete)));
  };

  const loadResources = async () => {
    setStatus("Loading resources…");
    const payload = await api("/api/v1/admin/resources");
    const resources = payload.resources || payload;
    state.resources = Array.isArray(resources)
      ? Object.fromEntries(resources.map((item) => [item.slug || item.name, item]))
      : resources;
    const entries = Object.entries(state.resources);
    resourceSelect.innerHTML = entries.map(([slug, meta]) =>
      `<option value="${escapeHtml(slug)}">${escapeHtml(meta.label || labelize(slug))}</option>`).join("");
    const requestedResource = deepLink.get("resource");
    if (requestedResource && state.resources[requestedResource]) {
      resourceSelect.value = requestedResource;
    }
    state.resource = resourceSelect.value || entries[0]?.[0] || "";
    setStatus("Ready");
  };

  const loadRecords = async () => {
    if (!state.resource) return;
    setStatus("Loading…");
    const params = new URLSearchParams({
      page: String(state.page),
      per_page: String(state.perPage),
    });
    const q = searchInput.value.trim();
    if (q) params.set("q", q);
    try {
      const payload = await api(`/api/v1/admin/${encodeURIComponent(state.resource)}?${params}`);
      state.records = payload.items || payload.records || [];
      state.total = payload.total ?? state.records.length;
      renderTable();
      setStatus("Up to date", "success");
    } catch (error) {
      state.records = [];
      state.total = 0;
      renderTable();
      setStatus(error.message, "error");
    }
  };

  const relatedResourceFor = (field) => field.related_resource || field.relationship || ({
    pm_id: "pms",
    pc_id: "pcs",
    da_id: "das",
    village_id: "villages",
    committee_id: "committees",
    action_plan_id: "action-plans",
    user_id: "users",
  })[field.name];

  const optionLabel = (item) => item.label || item.name || item.full_name || item.title ||
    item.village_name || item.committee_name || item.email || `#${item.id}`;

  const relationshipOptions = async (field) => {
    const resource = relatedResourceFor(field);
    if (!resource) return [];
    if (state.relationships.has(resource)) return state.relationships.get(resource);
    try {
      const payload = await api(`/api/v1/admin/${encodeURIComponent(resource)}?per_page=500`);
      const values = payload.items || payload.records || [];
      state.relationships.set(resource, values);
      return values;
    } catch (_) {
      return [];
    }
  };

  const createInput = async (field, value) => {
    const wrapper = document.createElement(field.type === "boolean" ? "label" : "div");
    wrapper.className = field.type === "boolean" ? "check-row" : "field";
    const id = `admin-field-${field.name}`;

    if (field.type === "boolean") {
      wrapper.innerHTML = `<input id="${escapeHtml(id)}" name="${escapeHtml(field.name)}" type="checkbox" ${value !== false ? "checked" : ""}>
        <span>${escapeHtml(field.label || labelize(field.name))}</span>`;
      return wrapper;
    }

    const label = document.createElement("label");
    label.setAttribute("for", id);
    label.textContent = field.label || labelize(field.name);
    wrapper.append(label);

    let input;
    if (field.choices || field.enum) {
      input = document.createElement("select");
      const choices = field.choices || field.enum;
      if (!field.required) input.append(new Option("— Select —", ""));
      for (const choice of choices) {
        const optionValue = typeof choice === "object" ? choice.value : choice;
        const optionText = typeof choice === "object" ? (choice.label || choice.value) : choice;
        input.append(new Option(optionText, optionValue));
      }
    } else if (field.type === "relationship" || field.name.endsWith("_id")) {
      input = document.createElement("select");
      if (!field.required) input.append(new Option("— None —", ""));
      const options = await relationshipOptions(field);
      for (const item of options) input.append(new Option(optionLabel(item), item.id));
    } else if (field.type === "textarea" || field.type === "json") {
      input = document.createElement("textarea");
      input.rows = field.type === "json" ? 6 : 3;
    } else {
      input = document.createElement("input");
      input.type = ({
        integer: "number",
        number: "number",
        date: "date",
        datetime: "datetime-local",
        email: "email",
        tel: "tel",
        password: "password",
      })[field.type] || "text";
      if (field.type === "integer") input.step = "1";
      if (field.type === "number") input.step = field.step || "any";
    }

    input.id = id;
    input.name = field.name;
    if (field.required || (field.name === "password" && !state.editing)) input.required = true;
    if (field.readonly && state.editing) input.disabled = true;
    if (field.min !== undefined) input.min = field.min;
    if (field.max !== undefined) input.max = field.max;
    if (field.placeholder) input.placeholder = field.placeholder;
    if (value !== undefined && value !== null) {
      if (field.type === "json" && typeof value !== "string") input.value = JSON.stringify(value, null, 2);
      else if (field.type === "datetime") input.value = String(value).slice(0, 16);
      else input.value = value;
    }
    wrapper.append(input);
    return wrapper;
  };

  const openEditor = async (id = null) => {
    clearError();
    moveAck.checked = false;
    moveAckRow.classList.add("hidden");
    state.editing = id ? state.records.find((item) => String(item.id) === String(id)) : null;
    $("#admin-dialog-eyebrow").textContent = resourceMeta().label || labelize(state.resource);
    $("#admin-dialog-title").textContent = state.editing ? "Edit record" : "Add record";
    fieldsHost.replaceChildren();

    const fields = fieldMeta().filter((field) => !field.hidden);
    for (const field of fields) {
      const value = state.editing?.[field.name];
      fieldsHost.append(await createInput(field, value));
    }

    const parentFields = new Set(["pc_id", "da_id", "village_id", "committee_id"]);
    for (const select of $$("select", fieldsHost)) {
      if (state.editing && parentFields.has(select.name)) {
        select.addEventListener("change", () => {
          if (String(select.value) !== String(state.editing[select.name] ?? "")) {
            moveAckRow.classList.remove("hidden");
          } else {
            moveAckRow.classList.add("hidden");
            moveAck.checked = false;
          }
        });
      }
    }

    dialog.showModal();
    const first = $("input:not([type=hidden]), select, textarea", fieldsHost);
    first?.focus();
  };

  const formPayload = () => {
    const payload = {};
    for (const field of fieldMeta()) {
      const input = fieldsHost.elements?.[field.name] || fieldsHost.querySelector(`[name="${CSS.escape(field.name)}"]`);
      if (!input || input.disabled) continue;
      if (field.type === "boolean") {
        payload[field.name] = input.checked;
      } else if (field.type === "integer") {
        payload[field.name] = input.value === "" ? null : Number.parseInt(input.value, 10);
      } else if (field.type === "number") {
        payload[field.name] = input.value === "" ? null : Number.parseFloat(input.value);
      } else if (field.type === "json") {
        try {
          payload[field.name] = input.value.trim() ? JSON.parse(input.value) : null;
        } catch (_) {
          input.setCustomValidity("Enter valid JSON.");
          input.reportValidity();
          throw new Error(`${field.label || labelize(field.name)} must be valid JSON.`);
        }
      } else {
        payload[field.name] = input.value === "" ? null : input.value;
      }
    }
    if (moveAckRow.classList.contains("hidden") === false) payload.acknowledge_move = moveAck.checked;
    return payload;
  };

  const saveRecord = async () => {
    clearError();
    if (!form.checkValidity()) {
      form.reportValidity();
      return;
    }
    let payload;
    try { payload = formPayload(); } catch (error) { showError(error.message); return; }
    setStatus("Saving…");
    $("#admin-save").disabled = true;
    try {
      const url = state.editing
        ? `/api/v1/admin/${encodeURIComponent(state.resource)}/${encodeURIComponent(state.editing.id)}`
        : `/api/v1/admin/${encodeURIComponent(state.resource)}`;
      await api(url, {
        method: state.editing ? "PATCH" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      dialog.close();
      state.relationships.clear();
      await loadRecords();
      setStatus("Saved", "success");
      window.MV.toast?.("Record saved", "success");
    } catch (error) {
      showError(error.message);
      setStatus("Save failed", "error");
    } finally {
      $("#admin-save").disabled = false;
    }
  };

  const confirm = (title, message, actionLabel = "Confirm") => new Promise((resolve) => {
    const confirmDialog = $("#confirm-dialog");
    $("#confirm-title").textContent = title;
    $("#confirm-message").textContent = message;
    $("#confirm-action").textContent = actionLabel;
    const handler = () => {
      confirmDialog.removeEventListener("close", handler);
      resolve(confirmDialog.returnValue === "confirm");
    };
    confirmDialog.addEventListener("close", handler);
    confirmDialog.showModal();
  });

  const toggleRecord = async (id) => {
    const record = state.records.find((item) => String(item.id) === String(id));
    if (!record) return;
    const next = !record.is_enabled;
    if (!(await confirm(`${next ? "Enable" : "Disable"} record?`,
      `${next ? "Enable" : "Disable"} ${optionLabel(record)}?`, next ? "Enable" : "Disable"))) return;
    try {
      await api(`/api/v1/admin/${encodeURIComponent(state.resource)}/${encodeURIComponent(id)}/toggle`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_enabled: next }),
      });
      state.relationships.clear();
      await loadRecords();
    } catch (error) {
      setStatus(error.message, "error");
      window.MV.toast?.(error.message, "error");
    }
  };

  const deleteRecord = async (id) => {
    const record = state.records.find((item) => String(item.id) === String(id));
    if (!record) return;
    if (!(await confirm("Move to recycle bin?",
      `${optionLabel(record)} will be retained for ten days and can be restored during that period.`, "Move to bin"))) return;
    try {
      await api(`/api/v1/admin/${encodeURIComponent(state.resource)}/${encodeURIComponent(id)}`, { method: "DELETE" });
      state.relationships.clear();
      await loadRecords();
      window.MV.toast?.("Moved to recycle bin", "success");
    } catch (error) {
      setStatus(error.message, "error");
      window.MV.toast?.(error.message, "error");
    }
  };

  const loadRecycle = async () => {
    const host = $("#recycle-list");
    const emptyState = $("#recycle-empty");
    host.innerHTML = `<div class="skeleton-card"></div><div class="skeleton-card"></div>`;
    try {
      const payload = await api("/api/v1/admin/recycle-bin/items?per_page=200");
      const items = payload.items || [];
      host.innerHTML = items.map((item) => {
        const expires = item.purge_after || item.expires_at;
        return `<article class="admin-card">
          <div>
            <span class="badge clay">${escapeHtml(labelize(item.entity_type || item.resource || "record"))}</span>
            <h3>${escapeHtml(item.display_name || item.entity_label || `Record #${item.entity_id}`)}</h3>
            <p>Deleted ${escapeHtml(displayValue(item, "deleted_at"))}</p>
            <p class="muted">Purge due ${escapeHtml(displayValue({ expires }, "expires"))}</p>
          </div>
          <button class="button primary" type="button" data-restore="${escapeHtml(item.id)}">Restore</button>
        </article>`;
      }).join("");
      emptyState.classList.toggle("hidden", items.length !== 0);
      $$("[data-restore]", host).forEach((button) => button.addEventListener("click", async () => {
        if (!(await confirm("Restore record?", "The record and its previous enabled state will be restored.", "Restore"))) return;
        try {
          await api(`/api/v1/admin/recycle-bin/${encodeURIComponent(button.dataset.restore)}/restore`, { method: "POST" });
          state.relationships.clear();
          await loadRecycle();
        } catch (error) {
          window.MV.toast?.(error.message, "error");
        }
      }));
    } catch (error) {
      host.innerHTML = `<div class="form-alert">${escapeHtml(error.message)}</div>`;
    }
  };

  const auditText = (event) => `${event.actor_name || ""} ${event.actor_user_id || ""} ${event.action || ""} ${event.entity_type || ""} ${event.entity_id || ""}`.toLowerCase();

  const renderAudit = () => {
    const query = $("#audit-search").value.trim().toLowerCase();
    const items = query ? state.auditRows.filter((event) => auditText(event).includes(query)) : state.auditRows;
    const tbody = $("#audit-table").tBodies[0];
    tbody.innerHTML = items.map((event) => {
      const before = event.before_json || event.before || null;
      const after = event.after_json || event.after || null;
      const summary = event.change_summary || (before || after ? `${before ? "Before" : ""}${before && after ? " → " : ""}${after ? "After" : ""}` : "—");
      return `<tr>
        <td data-label="When">${escapeHtml(displayValue(event, "created_at"))}</td>
        <td data-label="Actor">${escapeHtml(event.actor_name || (event.actor_user_id ? `User #${event.actor_user_id}` : "System"))}</td>
        <td data-label="Action"><span class="badge">${escapeHtml(event.action || "—")}</span></td>
        <td data-label="Entity">${escapeHtml(labelize(event.entity_type || "—"))}</td>
        <td data-label="Record">${escapeHtml(event.entity_id ?? "—")}</td>
        <td data-label="Changes"><details><summary>${escapeHtml(summary)}</summary><pre>${escapeHtml(JSON.stringify({ before, after }, null, 2))}</pre></details></td>
      </tr>`;
    }).join("");
    $("#audit-empty").classList.toggle("hidden", items.length !== 0);
    $("#audit-table").closest(".table-shell").classList.toggle("hidden", items.length === 0);
  };

  const loadAudit = async () => {
    try {
      const payload = await api("/api/v1/admin/audit-logs/items?per_page=250");
      state.auditRows = payload.items || [];
      renderAudit();
    } catch (error) {
      state.auditRows = [];
      renderAudit();
      window.MV.toast?.(error.message, "error");
    }
  };

  const activateTab = (name) => {
    $$("[data-admin-tab]").forEach((button) => {
      const active = button.dataset.adminTab === name;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    $$("[data-admin-panel]").forEach((panel) => panel.classList.toggle("hidden", panel.dataset.adminPanel !== name));
    if (name === "recycle") loadRecycle();
    if (name === "audit") loadAudit();
  };

  resourceSelect.addEventListener("change", () => {
    state.resource = resourceSelect.value;
    state.page = 1;
    state.relationships.clear();
    loadRecords();
  });
  let searchTimer;
  searchInput.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => { state.page = 1; loadRecords(); }, 250);
  });
  $("#admin-refresh").addEventListener("click", loadRecords);
  $("#admin-add").addEventListener("click", () => openEditor());
  $("#admin-prev").addEventListener("click", () => { if (state.page > 1) { state.page -= 1; loadRecords(); } });
  $("#admin-next").addEventListener("click", () => { if (state.page * state.perPage < state.total) { state.page += 1; loadRecords(); } });
  $("#recycle-refresh").addEventListener("click", loadRecycle);
  $("#audit-refresh").addEventListener("click", loadAudit);
  $("#audit-search").addEventListener("input", renderAudit);
  $$("[data-admin-tab]").forEach((button) => button.addEventListener("click", () => activateTab(button.dataset.adminTab)));

  form.addEventListener("submit", (event) => {
    if (event.submitter?.value === "default") {
      event.preventDefault();
      saveRecord();
    }
  });

  (async () => {
    try {
      await loadResources();

      const requestedTab = deepLink.get("tab");
      if (requestedTab === "recycle" || requestedTab === "audit") {
        activateTab(requestedTab);
        return;
      }

      activateTab("records");
      await loadRecords();

      const requestedEdit = deepLink.get("edit");
      if (requestedEdit) {
        const exists = state.records.some((item) => String(item.id) === String(requestedEdit));
        if (exists) {
          await openEditor(requestedEdit);
        } else {
          window.MV.toast?.("The requested record was not found in the active resource.", "error");
        }
      }
    } catch (error) {
      setStatus(error.message, "error");
      window.MV.toast?.(error.message, "error");
    }
  })();
})();
