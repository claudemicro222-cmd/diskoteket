// Offline-läget: appen och den senast visade samlingen sparas i webbläsaren.
// Nätet först (så att allt alltid är färskt), sparad kopia om servern inte svarar.
// Omslagen sparas efterhand som de visas.
const SHELL = "diskoteket-shell-v41";
const DATA = "diskoteket-data";
const COVERS = "diskoteket-covers";
const SHELL_FILES = ["/", "/static/app.js", "/static/style.css", "/static/icon.svg", "/manifest.webmanifest"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(SHELL).then((c) => c.addAll(SHELL_FILES)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(
    keys.filter((k) => k.startsWith("diskoteket-shell-") && k !== SHELL).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

async function networkFirst(req, cacheName) {
  const cache = await caches.open(cacheName);
  try {
    const res = await fetch(req);
    if (res.ok) cache.put(req, res.clone());
    return res;
  } catch (err) {
    const hit = await cache.match(req, { ignoreVary: true });
    if (hit) {
      const headers = new Headers(hit.headers);
      headers.set("X-Diskoteket-Offline", "1"); // appen visar "Offline – sparad kopia"
      return new Response(hit.body, { status: hit.status, headers });
    }
    throw err;
  }
}

async function coverFirst(req) {
  const cache = await caches.open(COVERS);
  const hit = await cache.match(req);
  if (hit) return hit;
  const res = await fetch(req);
  if (res.ok) cache.put(req, res.clone());
  return res;
}

// Bara läsning sparas. Det som visas i listorna och detaljvyerna fungerar offline.
const CACHED_API = /^\/api\/(items|libraries|facets|status|stats|collections|tags|locations)(\/|\?|$)/;

self.addEventListener("fetch", (e) => {
  const req = e.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== location.origin) return;
  if (url.pathname.startsWith("/poster/")) return e.respondWith(coverFirst(req));
  if (url.pathname === "/" || url.pathname.startsWith("/static/") || url.pathname === "/manifest.webmanifest") {
    return e.respondWith(networkFirst(req, SHELL));
  }
  if (CACHED_API.test(url.pathname)) return e.respondWith(networkFirst(req, DATA));
});
