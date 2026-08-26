(() => {
  "use strict";

  const csrfMeta = document.querySelector('meta[name="csrf-token"]');
  const userId = document.body.dataset.userId || null;
  const role = document.body.dataset.role || null;

  const csrf = () => csrfMeta?.content || "";

  const api = async (url, options = {}) => {
    const config = { credentials: "same-origin", ...options };
    const method = (config.method || "GET").toUpperCase();
    const headers = new Headers(config.headers || {});
    if (!["GET", "HEAD", "OPTIONS"].includes(method) && !headers.has("X-CSRFToken")) {
      headers.set("X-CSRFToken", csrf());
    }
    headers.set("Accept", "application/json");
    config.headers = headers;
    return fetch(url, config);
  };

  const refreshCsrf = async () => {
    if (!csrfMeta) return "";
    try {
      const response = await fetch("/api/v1/auth/csrf", { credentials: "same-origin", cache: "no-store" });
      if (!response.ok) return csrf();
      const payload = await response.json();
      if (payload.csrf_token) csrfMeta.content = payload.csrf_token;
    } catch (_) {
      // Existing token remains valid for offline work and will be refreshed on sync.
    }
    return csrf();
  };

  const toast = (message, kind = "") => {
    const host = document.querySelector(".toast-region");
    if (!host) return;
    const node = document.createElement("div");
    node.className = `toast ${kind}`.trim();
    node.setAttribute("role", kind === "error" ? "alert" : "status");
    const span = document.createElement("span");
    span.textContent = message;
    const close = document.createElement("button");
    close.type = "button";
    close.className = "icon-button";
    close.setAttribute("aria-label", "Dismiss");
    close.textContent = "×";
    close.addEventListener("click", () => node.remove());
    node.append(span, close);
    host.append(node);
    window.setTimeout(() => node.remove(), 6000);
  };

  const escapeHtml = (value) => String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

  const formatDate = (value, withTime = false) => {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.valueOf())) return String(value);
    return new Intl.DateTimeFormat(undefined, withTime
      ? { dateStyle: "medium", timeStyle: "short" }
      : { dateStyle: "medium" }).format(date);
  };

  const setNetworkState = () => {
    const online = navigator.onLine;
    document.body.classList.toggle("is-offline", !online);
    document.querySelectorAll("[data-network-label]").forEach((node) => {
      node.textContent = online ? "Online" : "Offline";
    });
    window.dispatchEvent(new CustomEvent("mv:network", { detail: { online } }));
  };

  window.addEventListener("online", () => {
    setNetworkState();
    refreshCsrf();
  });
  window.addEventListener("offline", setNetworkState);
  setNetworkState();

  // Desktop sidebar is intentionally fixed-width now. Remove the old
  // persisted collapse state so users are never left in the legacy mode.
  localStorage.removeItem("mv-rail-collapsed");
  document.body.classList.remove("rail-collapsed");

  document.querySelectorAll("[data-toggle-password]").forEach((button) => {
    button.addEventListener("click", () => {
      const input = button.closest(".password-field")?.querySelector("input");
      if (!input) return;
      const visible = input.type === "text";
      input.type = visible ? "password" : "text";
      button.textContent = visible ? "Show" : "Hide";
    });
  });

  let installPrompt = null;
  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    installPrompt = event;
    document.querySelectorAll("[data-install-app]").forEach((node) => node.classList.remove("hidden"));
  });
  document.querySelectorAll("[data-install-app]").forEach((button) => {
    button.addEventListener("click", async () => {
      if (!installPrompt) return;
      installPrompt.prompt();
      await installPrompt.userChoice;
      installPrompt = null;
      button.classList.add("hidden");
    });
  });
  window.addEventListener("appinstalled", () => {
    installPrompt = null;
    document.querySelectorAll("[data-install-app]").forEach((node) => node.classList.add("hidden"));
    toast("Model Village installed", "success");
  });

  document.querySelectorAll('form[action$="/logout"]').forEach((form) => {
    form.addEventListener("submit", () => {
      navigator.serviceWorker?.controller?.postMessage({ type: "CLEAR_USER", userId });
    });
  });

  // Role-aware navigation hotfix v2026.27.5
  const mobileMenu = document.querySelector("#mobile-menu");
  const mobileMenuTriggers = document.querySelectorAll("[data-mobile-menu-open]");
  const setMenuExpanded = (expanded) => {
    mobileMenuTriggers.forEach((button) => button.setAttribute("aria-expanded", expanded ? "true" : "false"));
  };
  mobileMenuTriggers.forEach((button) => {
    button.addEventListener("click", () => {
      if (!mobileMenu) return;
      if (!mobileMenu.open) mobileMenu.showModal();
      setMenuExpanded(true);
    });
  });
  document.querySelector("[data-mobile-menu-close]")?.addEventListener("click", () => {
    mobileMenu?.close();
    setMenuExpanded(false);
  });
  document.querySelectorAll("[data-mobile-menu-link]").forEach((link) => {
    link.addEventListener("click", () => {
      if (mobileMenu?.open) mobileMenu.close();
      setMenuExpanded(false);
    });
  });
  mobileMenu?.addEventListener("cancel", () => setMenuExpanded(false));
  mobileMenu?.addEventListener("click", (event) => {
    if (event.target === mobileMenu) {
      mobileMenu.close();
      setMenuExpanded(false);
    }
  });
  window.matchMedia("(min-width: 760px)").addEventListener?.("change", (event) => {
    if (event.matches && mobileMenu?.open) {
      mobileMenu.close();
      setMenuExpanded(false);
    }
  });

  window.MV = {
    api,
    csrf,
    refreshCsrf,
    toast,
    escapeHtml,
    formatDate,
    userId,
    role,
  };

  if (userId && navigator.onLine) refreshCsrf();
})();
