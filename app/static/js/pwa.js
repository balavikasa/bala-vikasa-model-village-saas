(() => {
  "use strict";

  if (!window.MV || !window.MVQueue || !window.MV.userId) return;
  const userId = String(window.MV.userId);
  const dialog = document.querySelector("#sync-dialog");
  const listHost = document.querySelector("#sync-queue-list");

  const postToWorker = async (message) => {
    const registration = await navigator.serviceWorker?.ready;
    const target = navigator.serviceWorker?.controller || registration?.active;
    target?.postMessage(message);
  };

  const setCounts = async () => {
    const count = await window.MVQueue.count(userId);
    document.querySelectorAll("[data-queue-count]").forEach((node) => {
      node.textContent = String(count);
      node.setAttribute("aria-label", `${count} queued entries`);
    });
    return count;
  };

  const renderQueue = async () => {
    if (!listHost) return;
    const records = await window.MVQueue.list(userId);
    if (!records.length) {
      listHost.innerHTML = '<div class="empty-state"><h3>Queue is clear</h3><p>All field entries are synchronized.</p></div>';
      return;
    }
    listHost.innerHTML = records.map((record) => `
      <article class="sync-item" data-status="${window.MV.escapeHtml(record.status)}">
        <div>
          <strong>${record.entryType === "specials" ? "Specials entry" : "Attendance entry"}</strong>
          <small>${window.MV.formatDate(record.createdAt, true)} · ${window.MV.escapeHtml(record.status)}</small>
          ${record.lastError ? `<small>${window.MV.escapeHtml(record.lastError)}</small>` : ""}
        </div>
        <div class="row-actions">
          ${record.status === "failed" ? `<button type="button" class="text-button" data-retry-id="${window.MV.escapeHtml(record.id)}">Retry</button>` : ""}
          <button type="button" class="text-button danger-text" data-remove-id="${window.MV.escapeHtml(record.id)}">Remove</button>
        </div>
      </article>`).join("");

    listHost.querySelectorAll("[data-retry-id]").forEach((button) => {
      button.addEventListener("click", async () => {
        const record = await window.MVQueue.get(button.dataset.retryId);
        if (!record) return;
        record.status = "queued";
        record.lastError = null;
        await window.MVQueue.update(record);
        await flushNow();
      });
    });
    listHost.querySelectorAll("[data-remove-id]").forEach((button) => {
      button.addEventListener("click", async () => {
        if (!window.confirm("Remove this unsynchronized entry from this device? This cannot be undone.")) return;
        await window.MVQueue.remove(button.dataset.removeId);
        await setCounts();
        await renderQueue();
      });
    });
  };

  const flushNow = async () => {
    if (!navigator.onLine) {
      window.MV.toast("Still offline. Entries remain safely queued.", "error");
      return;
    }
    document.querySelectorAll("[data-sync-now]").forEach((button) => { button.disabled = true; });
    try {
      await window.MV.refreshCsrf();
      const result = await window.MVQueue.flush(userId);
      await setCounts();
      await renderQueue();
      if (result.sent) window.MV.toast(`${result.sent} entr${result.sent === 1 ? "y" : "ies"} synchronized.`, "success");
      if (result.failed) window.MV.toast(`${result.failed} entr${result.failed === 1 ? "y needs" : "ies need"} review.`, "error");
      if (result.error) window.MV.toast(result.error, "error");
    } finally {
      document.querySelectorAll("[data-sync-now]").forEach((button) => { button.disabled = false; });
    }
  };

  document.querySelectorAll("[data-sync-trigger]").forEach((button) => {
    button.addEventListener("click", async () => {
      await renderQueue();
      dialog?.showModal();
    });
  });
  document.querySelectorAll("[data-close-sync]").forEach((button) => {
    button.addEventListener("click", () => dialog?.close());
  });
  document.querySelector("[data-sync-now]")?.addEventListener("click", flushNow);

  const channel = "BroadcastChannel" in window ? new BroadcastChannel("mv-sync") : null;
  channel?.addEventListener("message", async (event) => {
    if (String(event.data?.userId) !== userId) return;
    await setCounts();
    if (dialog?.open) await renderQueue();
  });

  window.addEventListener("online", async () => {
    await postToWorker({ type: "FLUSH_QUEUE", userId });
    await flushNow();
  });
  window.addEventListener("focus", setCounts);

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js", { scope: "/" })
      .then(async () => {
        await postToWorker({ type: "SET_USER", userId });
        if ("sync" in (await navigator.serviceWorker.ready)) {
          // Sync registration happens when an item is queued.
        }
      })
      .catch(() => window.MV.toast("Offline shell could not be enabled on this browser.", "error"));
  }

  window.addEventListener("mv:queued", async () => {
    await setCounts();
    try {
      const registration = await navigator.serviceWorker.ready;
      await registration.sync?.register("mv-entry-sync");
    } catch (_) {
      // Online and focus fallbacks cover browsers without Background Sync.
    }
  });

  setCounts();
})();
