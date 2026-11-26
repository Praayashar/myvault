/* MyVault service worker.
   Purpose is modest and deliberate: make the app installable on Android and
   survive a flaky connection. It does NOT try to run the app offline - this
   is financial data and showing a stale balance would be worse than showing
   nothing. Pages always go to the network first. */

const CACHE = 'myvault-v2';

// Only the shell assets. No pages, no API responses.
const SHELL = [
  '/static/css/style.css',
  '/static/js/main.js',
  '/static/manifest.json',
  '/static/img/icon-192.png',
  '/static/img/icon-512.png',
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE)
      .then(c => c.addAll(SHELL))
      .then(() => self.skipWaiting())
      .catch(() => self.skipWaiting())   // a missing asset must not block install
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys.filter(k => k !== CACHE).map(k => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const req = event.request;

  // Never touch anything that changes data or carries a session decision.
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith('/cron/')) return;
  if (url.pathname.startsWith('/vault/passwords/get/')) return;  // never cache a password

  // Static assets: serve from cache, refresh in the background.
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(req).then(hit => {
        const network = fetch(req).then(res => {
          if (res && res.status === 200) {
            const copy = res.clone();
            caches.open(CACHE).then(c => c.put(req, copy));
          }
          return res;
        }).catch(() => hit);
        return hit || network;
      })
    );
    return;
  }

  // Pages: network only. Financial data must never be served stale.
  // If the network fails, let the browser show its own offline page.
});
