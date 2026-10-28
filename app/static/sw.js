/* global MVQueue */
"use strict";
importScripts("/static/js/idb-queue.js");

const VERSION = "2026.27.31-reference-layout";
// Explicit DA location permission and Camera / Photo Album / Files choices
const STATIC_CACHE = `mv-static-${VERSION}`;
const DATA_PREFIX = "mv-data-";
let activeUser = null;

const networkFirstStatic = async (request) => {
  try {
    const response = await fetch(request);

    if (response.ok) {
      const cache = await caches.open(STATIC_CACHE);
      await cache.put(request, response.clone());
    }

    return response;
  } catch (error) {
    const cached = await caches.match(request);

    if (cached) {
      return cached;
    }

    throw error;
  }
};

const STATIC_ASSETS = [
  "/static/css/reference-ui.css?v=2026.27.31",
  "/static/js/reference-ui.js?v=2026.27.31",
  "/static/js/overview.js?v=2026.27.31",
  "/static/js/visit-analytics.js?v=2026.27.31",
  "/static/js/village-attendance.js?v=2026.27.31",
  "/static/js/admin.js?v=2026.27.31",
  "/static/reference/brand-lockup.png",
  "/static/reference/sidebar-village.png",
  "/static/reference/hero-village.png",
  "/static/reference/hero-dashboard.png",
  "/offline",
  "/manifest.json",
  "/static/css/app.css",
  "/static/css/village-renewal.css",
  "/static/brand/bala-vikasa-official.png",
  "/static/brand/bala-vikasa-symbol.png",
  "/static/brand/village-landscape.svg",
  "/static/css/da-field.css",
  "/static/css/attendance-theme.css",
  "/static/css/workflow-review.css",
  "/static/js/app.js",
  "/static/js/village-renewal.js",
  "/static/js/idb-queue.js",
  "/static/js/pwa.js",
  "/static/js/village-attendance.js",
  "/static/js/da-location.js",
  "/static/js/overview.js",
  "/static/js/visit-analytics.js",
  "/static/js/directory.js",
  "/static/js/monitoring.js",
  "/static/js/map.js",
  "/static/js/profile.js",
  "/static/js/action-plans.js",
  "/static/js/action-plan-transfer.js",
  "/static/js/reports.js",
  "/static/js/report-detail.js",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/icons/icon-maskable-192.png",
  "/static/icons/icon-maskable-512.png",
  "/static/icons/apple-touch-icon.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => cache.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys
        .filter((key) => key.startsWith("mv-static-") && key !== STATIC_CACHE)
        .map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

const dataCacheName = () => activeUser ? `${DATA_PREFIX}${activeUser}` : null;

const cacheFirst = async (request) => {
  const cached = await caches.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok) {
    const cache = await caches.open(STATIC_CACHE);
    cache.put(request, response.clone());
  }
  return response;
};

const networkFirstData = async (request) => {
  const name = dataCacheName();
  try {
    const response = await fetch(request);
    if (response.ok && name) {
      const cache = await caches.open(name);
      await cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    if (name) {
      const cached = await caches.match(request, { cacheName: name });
      if (cached) return cached;
    }
    throw error;
  }
};

const networkFirstNavigation = async (request) => {
  const name = dataCacheName();
  try {
    const response = await fetch(request);
    const url = new URL(request.url);
    if (response.ok && name && response.type === "basic" && url.pathname !== "/login") {
      const cache = await caches.open(name);
      await cache.put(request, response.clone());
    }
    return response;
  } catch (_) {
    if (name) {
      const cached = await caches.match(request, { cacheName: name });
      if (cached) return cached;
    }
    return (await caches.match("/offline")) || new Response("Offline", { status: 503 });
  }
};

const isEntryPost = (request) => {
  if (request.method !== "POST") return false;
  const path = new URL(request.url).pathname;
  return path === "/api/v1/attendance/village";
};

const entryNetworkFirst = async (request) => {
  try {
    return await fetch(request.clone());
  } catch (_) {
    if (!activeUser) {
      return new Response(JSON.stringify({ error: "No signed-in profile is available for offline queueing." }), {
        status: 503,
        headers: { "Content-Type": "application/json" },
      });
    }
    const record = await MVQueue.enqueueRequest(request, activeUser);
    try {
      const registration = await self.registration;
      await registration.sync?.register("mv-entry-sync");
    } catch (_) {
      // Browser may not implement Background Sync.
    }
    return new Response(JSON.stringify({
      queued: true,
      client_submission_id: record.id,
      message: "Saved to the offline queue.",
    }), {
      status: 202,
      headers: { "Content-Type": "application/json" },
    });
  }
};

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (isEntryPost(request)) {
    event.respondWith(entryNetworkFirst(request));
    return;
  }
  if (request.method !== "GET") return;

  if (request.mode === "navigate") {
    event.respondWith(networkFirstNavigation(request));
    return;
  }
  if (url.pathname.startsWith("/static/")) {
    event.respondWith(networkFirstStatic(request));
    return;
  }

  if (url.pathname === "/manifest.json") {
    event.respondWith(cacheFirst(request));
    return;
  }
  if (url.pathname.startsWith("/api/v1/")) {
    event.respondWith(networkFirstData(request));
  }
});

self.addEventListener("sync", (event) => {
  if (event.tag === "mv-entry-sync" && activeUser) {
    event.waitUntil(MVQueue.flush(activeUser, { fetchImpl: fetch.bind(self) }));
  }
});

self.addEventListener("message", (event) => {
  const message = event.data || {};
  if (message.type === "SET_USER" && message.userId) {
    activeUser = String(message.userId);
  } else if (message.type === "CLEAR_USER") {
    const userId = String(message.userId || activeUser || "");
    activeUser = null;
    if (userId) event.waitUntil?.(caches.delete(`${DATA_PREFIX}${userId}`));
  } else if (message.type === "FLUSH_QUEUE" && message.userId) {
    activeUser = String(message.userId);
    event.waitUntil?.(MVQueue.flush(activeUser, { fetchImpl: fetch.bind(self) }));
  } else if (message.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});
