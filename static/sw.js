// Minimal service worker (FR-96): caches the shell; pages stay network-first so schedules are
// never stale. Push handling (FR-112) is added when VAPID keys are configured.
const CACHE = "ops-shell-v1";
const SHELL = ["/static/css/app.css", "/static/js/app.js", "/static/manifest.webmanifest"];
self.addEventListener("install", (e) => { e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL))); self.skipWaiting(); });
self.addEventListener("activate", (e) => { e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k))))); });
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || !url.pathname.startsWith("/static/")) return;
  e.respondWith(caches.match(e.request).then((hit) => hit || fetch(e.request)));
});
self.addEventListener("push", (e) => {
  const data = e.data ? e.data.json() : { title: "Club Ops", body: "" };
  e.waitUntil(self.registration.showNotification(data.title || "Club Ops", { body: data.body || "", data: { url: data.url || "/" } }));
});
self.addEventListener("notificationclick", (e) => { e.notification.close(); e.waitUntil(clients.openWindow((e.notification.data && e.notification.data.url) || "/")); });
