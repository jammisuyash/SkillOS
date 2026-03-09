/**
 * SkillOS Service Worker v2
 * Full offline support, background sync, push notifications.
 */

const CACHE_NAME = "skillos-v2";
const STATIC_ASSETS = ["/", "/index.html", "/manifest.json"];

// Install
self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE_NAME).then(c => c.addAll(STATIC_ASSETS)));
  self.skipWaiting();
});

// Activate — clean old caches
self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then(names =>
      Promise.all(names.filter(n => n !== CACHE_NAME).map(n => caches.delete(n)))
    )
  );
  self.clients.claim();
});

// Fetch — network-first for API, cache-first for static
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);

  // API requests: network-first, no cache
  if (url.pathname.startsWith("/api/") || url.port === "8000") {
    e.respondWith(
      fetch(e.request).catch(() =>
        new Response(JSON.stringify({ error: "Offline — no network" }), {
          status: 503,
          headers: { "Content-Type": "application/json" },
        })
      )
    );
    return;
  }

  // Static + navigation: cache-first with network fallback
  e.respondWith(
    caches.match(e.request).then(cached => {
      if (cached) return cached;
      return fetch(e.request)
        .then(res => {
          if (res.ok && e.request.method === "GET") {
            const clone = res.clone();
            caches.open(CACHE_NAME).then(c => c.put(e.request, clone));
          }
          return res;
        })
        .catch(() => caches.match("/index.html")); // SPA fallback
    })
  );
});

// Push notifications
self.addEventListener("push", (e) => {
  const data = e.data?.json() || { title: "SkillOS", body: "You have a new notification" };
  e.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: "/icons/icon-192.png",
      badge: "/icons/icon-72.png",
      data: data.url || "/",
      vibrate: [100, 50, 100],
      actions: [{ action: "open", title: "Open SkillOS" }],
    })
  );
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  e.waitUntil(clients.openWindow(e.notification.data || "/"));
});
