const CACHE_NAME = 'tdm-pwa-v0.0.70';
const ASSETS_TO_CACHE = [
  './',
  './index.html',
  './manifest.json',
  './icons/icon-192.png',
  './icons/icon-512.png'
];

self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE).catch(() => {});
    })
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  // Ignorar peticiones no HTTP/HTTPS (extensiones de chrome, data:, blob:, etc.)
  if (!event.request.url.startsWith('http://') && !event.request.url.startsWith('https://')) {
    return;
  }

  // Solo interceptar peticiones GET
  if (event.request.method !== 'GET') {
    return;
  }

  const url = new URL(event.request.url);

  // Ignorar peticiones dinámicas de API, WebSockets y streaming (incluso bajo sub-rutas /aabbcc/api/...)
  if (url.pathname.includes('/api/') || url.pathname.includes('/ws/') || url.pathname.includes('/websockify')) {
    return;
  }

  // Estrategia Network-First para asegurar siempre la versión más reciente
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (response && response.status === 200 && event.request.method === 'GET') {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone).catch(() => {});
          }).catch(() => {});
        }
        return response;
      })
      .catch(() => {
        return caches.match(event.request);
      })
  );
});
