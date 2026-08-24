((scope) => {
  "use strict";

  const DB_NAME = "mv-field-queue";
  const DB_VERSION = 3;
  const STORE = "requests";

  const requestPromise = (request) => new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });

  const transactionDone = (transaction) => new Promise((resolve, reject) => {
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error);
    transaction.onabort = () => reject(transaction.error || new Error("IndexedDB transaction aborted."));
  });

  const open = () => new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      let store;
      if (!db.objectStoreNames.contains(STORE)) {
        store = db.createObjectStore(STORE, { keyPath: "id" });
      } else {
        store = request.transaction.objectStore(STORE);
      }
      if (!store.indexNames.contains("by_user")) store.createIndex("by_user", "userId", { unique: false });
      if (!store.indexNames.contains("by_created")) store.createIndex("by_created", "createdAt", { unique: false });
      if (!store.indexNames.contains("by_status")) store.createIndex("by_status", "status", { unique: false });
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });

  const withStore = async (mode, callback) => {
    const db = await open();
    try {
      const transaction = db.transaction(STORE, mode);
      const store = transaction.objectStore(STORE);
      const value = await callback(store, transaction);
      await transactionDone(transaction);
      return value;
    } finally {
      db.close();
    }
  };

  const serializeFormData = (formData) => {
    const fields = [];
    for (const [name, value] of formData.entries()) {
      if (typeof value === "string") {
        fields.push({ name, kind: "text", value });
      } else {
        fields.push({
          name,
          kind: "blob",
          value,
          filename: value.name || `${name}.webp`,
          mime: value.type || "application/octet-stream",
        });
      }
    }
    return fields;
  };

  const deserializeFormData = (fields) => {
    const formData = new FormData();
    for (const field of fields || []) {
      if (field.kind === "blob") {
        formData.append(field.name, field.value, field.filename);
      } else {
        formData.append(field.name, field.value);
      }
    }
    return formData;
  };

  const clientIdFrom = (formData) => String(formData.get("client_submission_id") || crypto.randomUUID());

  const notify = (payload) => {
    try {
      const channel = new BroadcastChannel("mv-sync");
      channel.postMessage(payload);
      channel.close();
    } catch (_) {
      // BroadcastChannel is optional; pages also refresh on focus/online.
    }
  };

  const enqueue = async ({ id, userId, url, method = "POST", headers = {}, formData, entryType }) => {
    if (!userId) throw new Error("A signed-in user is required for offline queueing.");
    const record = {
      id: id || clientIdFrom(formData),
      userId: String(userId),
      url,
      method,
      headers: Object.fromEntries(new Headers(headers).entries()),
      fields: serializeFormData(formData),
      entryType: entryType || (url.includes("specials") ? "specials" : "attendance"),
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      retries: 0,
      status: "queued",
      lastError: null,
    };
    await withStore("readwrite", (store) => requestPromise(store.put(record)));
    notify({ type: "QUEUE_CHANGED", userId: String(userId) });
    return record;
  };

  const enqueueRequest = async (request, userId) => {
    const clone = request.clone();
    const formData = await clone.formData();
    return enqueue({
      id: clientIdFrom(formData),
      userId,
      url: new URL(request.url).pathname + new URL(request.url).search,
      method: request.method,
      headers: request.headers,
      formData,
    });
  };

  const list = async (userId) => {
    if (!userId) return [];
    const values = await withStore("readonly", (store) => requestPromise(store.index("by_user").getAll(String(userId))));
    return values.sort((a, b) => a.createdAt.localeCompare(b.createdAt));
  };

  const get = async (id) => withStore("readonly", (store) => requestPromise(store.get(id)));

  const update = async (record) => {
    record.updatedAt = new Date().toISOString();
    await withStore("readwrite", (store) => requestPromise(store.put(record)));
    notify({ type: "QUEUE_CHANGED", userId: record.userId });
    return record;
  };

  const remove = async (id) => {
    const record = await get(id);
    await withStore("readwrite", (store) => requestPromise(store.delete(id)));
    if (record) notify({ type: "QUEUE_CHANGED", userId: record.userId });
  };

  const count = async (userId) => (await list(userId)).length;

  const freshCsrf = async (fetchImpl) => {
    const response = await fetchImpl("/api/v1/auth/csrf", {
      credentials: "same-origin",
      cache: "no-store",
      headers: { "Accept": "application/json" },
    });
    if (!response.ok) throw new Error(`Could not refresh security token (${response.status}).`);
    const payload = await response.json();
    return payload.csrf_token;
  };

  const flush = async (userId, options = {}) => {
    const fetchImpl = options.fetchImpl || fetch.bind(scope);
    const records = (await list(userId)).filter((record) => ["queued", "retrying", "failed"].includes(record.status));
    if (!records.length) return { sent: 0, failed: 0, remaining: 0 };

    let token;
    try {
      token = await freshCsrf(fetchImpl);
    } catch (error) {
      return { sent: 0, failed: 0, remaining: records.length, error: error.message };
    }

    let sent = 0;
    let failed = 0;
    for (const record of records) {
      record.status = "retrying";
      record.retries += 1;
      record.lastError = null;
      await update(record);
      const headers = new Headers(record.headers || {});
      headers.delete("content-type");
      headers.set("X-CSRFToken", token);
      headers.set("Accept", "application/json");

      try {
        const response = await fetchImpl(record.url, {
          method: record.method,
          body: deserializeFormData(record.fields),
          headers,
          credentials: "same-origin",
        });
        if (response.ok) {
          await remove(record.id);
          sent += 1;
          continue;
        }

        let payload = {};
        try { payload = await response.json(); } catch (_) { /* no JSON */ }
        const message = payload.error || `Server rejected entry (${response.status}).`;
        if ([400, 403, 404, 409, 413, 422].includes(response.status)) {
          record.status = "failed";
          record.lastError = message;
          await update(record);
          failed += 1;
        } else if (response.status === 401) {
          record.status = "queued";
          record.lastError = "Sign in again to synchronize.";
          await update(record);
          break;
        } else {
          record.status = "queued";
          record.lastError = message;
          await update(record);
          break;
        }
      } catch (error) {
        record.status = "queued";
        record.lastError = error.message || "Network unavailable.";
        await update(record);
        break;
      }
    }

    const remaining = await count(userId);
    notify({ type: "FLUSH_COMPLETE", userId: String(userId), sent, failed, remaining });
    return { sent, failed, remaining };
  };

  scope.MVQueue = {
    enqueue,
    enqueueRequest,
    list,
    get,
    update,
    remove,
    count,
    flush,
    serializeFormData,
    deserializeFormData,
  };
})(globalThis);
