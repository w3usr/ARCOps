// Minimal service worker (FR-96): caches the shell; pages stay network-first so schedules are
// never stale. Push handling (FR-112) is added when VAPID keys are configured.
const CACHE = "ops-shell-v3";
const SHELL = ["/static/css/app.css", "/static/js/app.js"];
// Pages kept for offline reading (FR-96): the member's own schedule and messages. Network first,
// so nothing is stale while online; the last good copy is served when the network is gone.
const OFFLINE_PAGES = ["/events/mine/", "/me/messages/"];
self.addEventListener("install", (e) => { e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL))); self.skipWaiting(); });
self.addEventListener("activate", (e) => { e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k))))); });
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET") return;
  if (url.pathname.startsWith("/static/")) {
    e.respondWith(caches.match(e.request).then((hit) => hit || fetch(e.request)));
    return;
  }
  if (OFFLINE_PAGES.includes(url.pathname) && e.request.mode === "navigate") {
    e.respondWith(
      fetch(e.request)
        .then((res) => { if (res.ok) caches.open(CACHE).then((c) => c.put(e.request, res.clone())); return res; })
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
