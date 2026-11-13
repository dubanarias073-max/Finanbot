/* FinanBot - Service Worker (PWA)
 * Alcance: /legacy/pages/
 * - Páginas: red primero; si no hay conexión muestra offline.html
 * - Iconos/imágenes del logo: caché primero
 * - /api y cualquier petición no GET: nunca se cachean (datos financieros siempre frescos)
 */
const VERSION = 'finanbot-v1';
const PRECACHE = [
  '/legacy/pages/offline.html',
  '/legacy/pages/icons/icon-192.png',
  '/legacy/pages/icons/icon-512.png',
  '/images/logo.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(VERSION).then((c) => c.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;      // CDNs, fuentes, etc.: el navegador decide
  if (url.pathname.startsWith('/api')) return;           // API: siempre a la red

  if (req.mode === 'navigate') {
    event.respondWith(fetch(req).catch(() => caches.match('/legacy/pages/offline.html')));
    return;
  }

  if (url.pathname.startsWith('/legacy/pages/icons/') || url.pathname.startsWith('/images/')) {
    event.respondWith(
      caches.match(req).then((hit) => hit || fetch(req).then((res) => {
        const copy = res.clone();
        caches.open(VERSION).then((c) => c.put(req, copy));
        return res;
      }))
    );
  }
});
