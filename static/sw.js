// Minimal service worker (FR-96): caches static files as they are fetched; pages stay
// network-first so schedules are never stale. Push handling (FR-112) is added when VAPID keys are
// configured.
const CACHE = "ops-shell-v7";
// Only hashed names (app.1ec310869fd1.css), which the servers' manifest storage gives every static
// file: their content never changes, so a cached copy is never stale. Unhashed names (a local
// DEBUG run) always go to the network.
// ponytail: a deploy's superseded files stay cached until CACHE is bumped; a few hundred KB each.
const HASHED = /\.[0-9a-f]{12}\.[a-z0-9]+$/;
// Pages kept for offline reading (FR-96): the member's own schedule and messages. Network first,
// so nothing is stale while online; the last good copy is served when the network is gone.
const OFFLINE_PAGES = ["/events/mine/", "/me/messages/"];
self.addEventListener("install", () => { self.skipWaiting(); });
self.addEventListener("activate", (e) => { e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k))))); });
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET") return;
  if (url.pathname.startsWith("/static/")) {
    if (!HASHED.test(url.pathname)) return;
    e.respondWith(caches.match(e.request).then((hit) => hit || fetch(e.request).then((res) => {
      if (res.ok) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(e.request, copy)); }
      return res;
    })));
    return;
  }
  if (OFFLINE_PAGES.includes(url.pathname) && e.request.mode === "navigate") {
    e.respondWith(
      fetch(e.request)
        // Clone now: once the page has read the body, a later clone throws and nothing is kept.
        .then((res) => { if (res.ok) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(e.request, copy)); } return res; })
        .catch(() => caches.match(e.request))
    );
  }
});
self.addEventListener("push", (e) => {
  // The title carries the club's short name (set server-side); the fallback is this origin, so a
  // member of two clubs running the software can tell the notifications apart.
  const data = e.data ? e.data.json() : {};
  const title = data.title || self.location.host;
  const opts = { body: data.body || "", data: { url: data.url || "/" }, tag: data.tag || undefined };
  if (data.icon) opts.icon = data.icon;
  e.waitUntil(self.registration.showNotification(title, opts));
});
self.addEventListener("notificationclick", (e) => { e.notification.close(); e.waitUntil(clients.openWindow((e.notification.data && e.notification.data.url) || "/")); });
