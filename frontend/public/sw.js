const CACHE_NAME = 'skillos-v3';

self.addEventListener('install', (e) => {
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.map(key => caches.delete(key)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  // Never intercept API calls or external resources
  if (url.hostname !== 'skill-os-omega.vercel.app') return;
  // Never intercept JS/CSS assets - always fetch fresh
  if (url.pathname.startsWith('/assets/')) return;
  // Pass through everything else
  return;
});
