// Service Worker para Termux Display Manager (TDM) PWA
const CACHE_NAME = 'tdm-pwa-v0.0.85';
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
  const req = event.request;
  if (!req || !req.url) return;

  // 1. Filtrar explícitamente cualquier esquema no HTTP/HTTPS (extensiones de Chrome, data:, blob:, moz-extension:, etc.)
  if (!req.url.startsWith('http://') && !req.url.startsWith('https://')) {
    return;
  }

  // 2. Solo interceptar peticiones GET
  if (req.method !== 'GET') {
    return;
  }

  let url;
  try {
    url = new URL(req.url);
  } catch (e) {
    return;
  }

  if (url.protocol !== 'http:' && url.protocol !== 'https:') {
    return;
  }

  // 3. Ignorar llamadas de telemetría dinámica de la API, WebSockets y streaming
  if (url.pathname.includes('/api/') || url.pathname.includes('/ws/') || url.pathname.includes('/websockify')) {
    return;
  }

  // 4. Estrategia Network-First con protección absoluta de caché
  event.respondWith(
    fetch(req)
      .then((response) => {
        if (response && response.status === 200 && (response.type === 'basic' || response.type === 'cors')) {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            try {
              if (req.url.startsWith('http://') || req.url.startsWith('https://')) {
                cache.put(req, responseClone).catch(() => {});
              }
            } catch (err) {}
          }).catch(() => {});
        }
        return response;
      })
      .catch(() => {
        return caches.match(req);
      })
  );
});
