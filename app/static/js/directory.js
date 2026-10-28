(() => {
  "use strict";
  if (!window.MV) return;
  const grid = document.querySelector("#directory-grid");
  const empty = document.querySelector("#directory-empty");
  const search = document.querySelector("#directory-search");
  let data = { villages: [], das: [], pcs: [], pms: [] };
  let tab = "villages";
  const esc = window.MV.escapeHtml;
  const text = (item) => Object.values(item).filter((value) => typeof value === "string").join(" ").toLowerCase();

  const card = (href, body) => `<a class="directory-card directory-link-card" href="${href}">${body}<span class="directory-open">View →</span></a>`;

  const render = () => {
    const query = search.value.trim().toLowerCase();
    const items = (data[tab] || []).filter((item) => !query || text(item).includes(query));
    if (tab === "villages") {
      grid.innerHTML = items.map((item) => card(item.profile_url || `/directory/village/${item.id}`, `
        <header><span class="badge">${esc(item.cluster)}</span><span class="mono">${esc(item.code || `#${item.id}`)}</span></header>
        <h2>${esc(item.name)}</h2>
        <p class="muted">${esc(item.gp_name || "Gram Panchayat not recorded")}</p>
        <div class="directory-meta">
          <span><small>Development agent</small><strong>${esc(item.da_name)}</strong></span>
          <span><small>Project coordinator</small><strong>${esc(item.pc_name)}</strong></span>
          <span><small>District</small><strong>${esc(item.district || "—")}</strong></span>
          <span><small>Mandal</small><strong>${esc(item.mandal || "—")}</strong></span>
        </div>`)).join("");
    } else if (tab === "das") {
      grid.innerHTML = items.map((item) => card(`/directory/da/${item.id}`, `
        <header><span class="badge">${esc(item.cluster)}</span><span class="mono">DA-${item.id}</span></header>
        <h2>${esc(item.name)}</h2>
        <p class="muted">Reports to ${esc(item.pc_name)}</p>
        <div class="directory-meta"><span><small>Assigned villages</small><strong>${Number(item.village_count).toLocaleString()}</strong></span><span><small>Cluster</small><strong>${esc(item.cluster)}</strong></span></div>`)).join("");
    } else if (tab === "pcs") {
      grid.innerHTML = items.map((item) => card(item.profile_url || `/directory/pc/${item.id}`, `
        <header><span class="badge">${esc(item.cluster)}</span><span class="mono">PC-${item.id}</span></header>
        <h2>${esc(item.name)}</h2>
        <p class="muted">Project Coordinator</p>
        <div class="directory-meta"><span><small>Development agents</small><strong>${Number(item.da_count || 0)}</strong></span><span><small>Villages</small><strong>${Number(item.village_count || 0)}</strong></span></div>`)).join("");
    } else {
      grid.innerHTML = items.map((item) => card(item.profile_url || `/directory/pm/${item.id}`, `
        <header><span class="badge">ALL CLUSTERS</span><span class="mono">PM-${item.id}</span></header>
        <h2>${esc(item.name)}</h2>
        <p class="muted">Program Manager · read-only monitoring</p>
        <div class="directory-meta"><span><small>Email</small><strong>${esc(item.email || "—")}</strong></span><span><small>Mobile</small><strong>${esc(item.mobile || "—")}</strong></span></div>`)).join("");
    }
    empty.classList.toggle("hidden", items.length !== 0);
    grid.classList.toggle("hidden", items.length === 0);
  };

  document.querySelectorAll("[data-directory-tab]").forEach((button) => {
    button.addEventListener("click", () => {
      tab = button.dataset.directoryTab;
      document.querySelectorAll("[data-directory-tab]").forEach((item) => {
        const active = item === button;
        item.classList.toggle("is-active", active);
        item.setAttribute("aria-pressed", String(active));
      });
      render();
    });
  });
  search.addEventListener("input", render);

  (async () => {
    try {
      const response = await window.MV.api("/api/v1/directory");
      if (!response.ok) throw new Error("Could not load directory.");
      data = await response.json();
      document.querySelectorAll("[data-directory-tab]").forEach((button) => {
        if (!(data[button.dataset.directoryTab] || []).length && button.dataset.directoryTab !== "villages") {
          button.classList.add("hidden");
        }
      });
      render();
    } catch (error) {
      grid.innerHTML = `<div class="form-alert">${esc(error.message)}</div>`;
    }
  })();
})();