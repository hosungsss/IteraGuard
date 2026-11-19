/* Offline app shell. API calls are never cached. */
const CACHE = 'dmsg-v51-shell-a053ca035793f64d';
const SHELL = ['./', 'index.html', 'styles.css', 'app.js', 'engine-data.js', 'dmsg-engine.js', 'dmsg-nlp.js', 'linkguard-data.js', 'dmsg-linkguard.js', 'dmsg-apkscan.js', 'dmsg-domainintel.js', 'v50-contract-data.js', 'v50-contract.js', 'v51-profile-data.js', 'v51-semantic-data.js', 'v51-base-engine.js', 'v51-base-contract.js', 'v51-semantic.js', 'v51-evidence.js', 'v51-contract-data.js', 'v51-contract.js', 'build-info.js', 'nlp/dmsg-nlp-vocab.js', 'nlp/dmsg-nlp-heads.js', 'nlp/dmsg-nlp-weights.js', 'manifest.webmanifest',
  'icons/icon.svg', 'icons/icon-180.png', 'icons/icon-192.png', 'icons/icon-512.png', 'icons/icon-maskable-512.png'];
self.addEventListener('install', e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())); });
self.addEventListener('activate', e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener('fetch', e => {
  const u = new URL(e.request.url);
  if (e.request.method !== 'GET' || u.origin !== location.origin || u.pathname.startsWith('/api/')) return;
  e.respondWith(caches.match(e.request, { ignoreSearch: true }).then(hit => hit || fetch(e.request)));
});
