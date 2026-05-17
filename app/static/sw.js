const IMAGE_CACHE = 'roachflix-images-v2';
const STATIC_CACHE = 'roachflix-static-v2';

self.addEventListener('install', e => {
  e.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(k => k !== IMAGE_CACHE && k !== STATIC_CACHE).map(k => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  // Cache-first for TMDB poster/backdrop images
  if (url.hostname === 'image.tmdb.org') {
    e.respondWith(
      caches.open(IMAGE_CACHE).then(cache =>
        cache.match(e.request).then(cached => {
          if (cached) return cached;
          return fetch(e.request).then(res => {
            cache.put(e.request, res.clone());
            return res;
          });
        })
      )
    );
    return;
  }

  // Cache-first for versioned static assets (CSS, JS, icons)
  if (url.origin === self.location.origin && url.pathname.startsWith('/static/')) {
    e.respondWith(
      caches.open(STATIC_CACHE).then(cache =>
        cache.match(e.request).then(cached => {
          if (cached) return cached;
          return fetch(e.request).then(res => {
            cache.put(e.request, res.clone());
            return res;
          });
        })
      )
    );
    return;
  }

  // Network-only for all HTML pages — always fresh from server
  // (no caching; stale watchlist data is worse than no offline support)
});
