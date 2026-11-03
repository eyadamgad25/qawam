// Offline support for the installed app. The page (HTML) is network-first so
// a new deploy shows at once; everything else (hashed bundles, pose model,
// WASM runtime) is cache-first. Install precaches the app shell and the pose
// files so the coach works offline right after the first visit.
// shortcut: one cache that only grows across deploys; bump CACHE to clear it.
const CACHE = 'qawam-v1';
const POSE_FILES = [
  'models/pose_landmarker_lite.task',
  'mediapipe/wasm/vision_wasm_internal.js',
  'mediapipe/wasm/vision_wasm_internal.wasm',
];

self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(precache());
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (new URL(request.url).origin !== self.location.origin) return;
  if (request.method === 'HEAD') {
    // videoPose.ts probes the local model with HEAD before choosing it over the CDN
    event.respondWith(headWithCacheFallback(request));
  } else if (request.method === 'GET') {
    event.respondWith(
      request.mode === 'navigate' ? networkFirst(request) : cacheFirst(request),
    );
  }
});

async function precache() {
  const cache = await caches.open(CACHE);
  const page = await fetch('./');
  await cache.put('./', page.clone());
  const html = await page.text();
  const bundles = [...html.matchAll(/(?:src|href)="([^"]*assets\/[^"]+)"/g)].map(
    (m) => m[1],
  );
  // a missing file must not block install; it is cached on first use instead
  await Promise.all(
    [...bundles, ...POSE_FILES].map((url) => cache.add(url).catch(() => undefined)),
  );
  // lazy chunks (the pose library) are named only inside the main bundle: import(`./x.js`)
  for (const bundle of bundles.filter((url) => url.endsWith('.js'))) {
    const code = await (await cache.match(bundle))?.text();
    const chunks = [...(code ?? '').matchAll(/import\(`\.\/([\w-]+\.js)`\)/g)];
    const urls = chunks.map(
      (m) => new URL(m[1], new URL(bundle, self.location.href)).href,
    );
    await Promise.all(
      [...new Set(urls)].map((url) => cache.add(url).catch(() => undefined)),
    );
  }
}

async function networkFirst(request) {
  const cache = await caches.open(CACHE);
  try {
    const response = await fetch(request);
    if (response.ok) await cache.put('./', response.clone());
    return response;
  } catch {
    return (await cache.match('./')) ?? Response.error();
  }
}

async function cacheFirst(request) {
  const cache = await caches.open(CACHE);
  const cached = await cache.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok) await cache.put(request, response.clone());
  return response;
}

async function headWithCacheFallback(request) {
  try {
    return await fetch(request);
  } catch {
    const cached = await caches.match(request.url);
    if (!cached) return Response.error();
    return new Response(null, { status: cached.status, headers: cached.headers });
  }
}
