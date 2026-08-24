(() => {
  "use strict";

  const root = document.querySelector(".report-detail-page");
  const host = document.getElementById("report-map");
  const deleteButton = document.querySelector("[data-report-delete-plan]");

  const deleteReport = async () => {
    if (!deleteButton || window.MV?.role !== "admin") return;
    const planId = deleteButton.dataset.reportDeletePlan;
    if (!planId) return;

    const confirmed = window.confirm(
      "Move this report to the Recycle Bin? Any submitted Attendance/Specials entry linked to this plan will also be soft-deleted and can be restored by an administrator."
    );
    if (!confirmed) return;

    deleteButton.disabled = true;
    deleteButton.textContent = "Deleting...";

    try {
      const response = await window.MV.api(`/api/v1/reports/plan/${encodeURIComponent(planId)}`, {
        method: "DELETE",
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.error || "Could not delete report.");

      window.MV.toast?.(payload.message || "Report moved to Recycle Bin.", "success");
      const month = root?.dataset.month;
      window.location.href = month ? `/reports?month=${encodeURIComponent(month)}` : "/reports";
    } catch (error) {
      window.MV.toast?.(error.message, "error");
      deleteButton.disabled = false;
      deleteButton.textContent = "Delete report";
    }
  };

  deleteButton?.addEventListener("click", deleteReport);

  if (!root || !host) return;

  const lat = Number(root.dataset.lat);
  const lng = Number(root.dataset.lng);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;

  let map = null;
  let resizeObserver = null;

  const refreshMap = () => {
    if (!map) return;
    window.requestAnimationFrame(() => {
      map.invalidateSize({ pan: false, animate: false });
      map.setView([lat, lng], map.getZoom(), { animate: false });
    });
  };

  const initializeMap = (attempt = 0) => {
    if (map || host.dataset.mapReady === "1") return;

    if (!window.L) {
      if (attempt < 40) {
        window.setTimeout(() => initializeMap(attempt + 1), 100);
      }
      return;
    }

    host.dataset.mapReady = "1";

    map = L.map(host, {
      scrollWheelZoom: false,
      zoomControl: true,
      preferCanvas: true,
    }).setView([lat, lng], 15);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      updateWhenIdle: false,
      keepBuffer: 4,
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);

    L.marker([lat, lng]).addTo(map);

    [0, 80, 220, 500, 1000].forEach((delay) => window.setTimeout(refreshMap, delay));

    if ("ResizeObserver" in window) {
      resizeObserver = new ResizeObserver(refreshMap);
      resizeObserver.observe(host);
    }

    window.addEventListener("resize", refreshMap, { passive: true });
    window.addEventListener(
      "orientationchange",
      () => window.setTimeout(refreshMap, 180),
      { passive: true },
    );
    window.addEventListener("load", refreshMap, { once: true });
    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) window.setTimeout(refreshMap, 80);
    });
  };

  initializeMap();

  window.addEventListener(
    "beforeunload",
    () => {
      resizeObserver?.disconnect();
      if (map) {
        window.removeEventListener("resize", refreshMap);
        map.remove();
        map = null;
      }
    },
    { once: true },
  );
})();
