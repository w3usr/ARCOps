// Browser notifications (FR-112). On a device that has not been asked, ask once after the first
// signed-in page settles; on grant, subscribe with the club's VAPID key and post the subscription.
// The profile page's button re-asks on a device where the person declined or wants to opt in later.
(function () {
  const me = document.currentScript;
  if (!me || !("serviceWorker" in navigator) || !("PushManager" in window) || !("Notification" in window)) return;
  const vapid = me.dataset.vapid, subscribeUrl = me.dataset.subscribe, csrf = me.dataset.csrf;
  const enabled = me.dataset.enabled === "1";
  const ASKED = "ops-push-asked";
  const status = document.getElementById("push-status");
  const button = document.getElementById("push-enable-here");

  function b64ToBytes(s) {
    const pad = "=".repeat((4 - (s.length % 4)) % 4);
    const raw = atob((s + pad).replace(/-/g, "+").replace(/_/g, "/"));
    return Uint8Array.from(raw, (c) => c.charCodeAt(0));
  }
  function say(text) { if (status) status.textContent = text; }

  async function subscribe() {
    const reg = await navigator.serviceWorker.ready;
    let sub = await reg.pushManager.getSubscription();
    if (!sub) sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64ToBytes(vapid) });
    const r = await fetch(subscribeUrl, { method: "POST", headers: { "Content-Type": "application/json", "X-CSRFToken": csrf }, body: JSON.stringify(sub.toJSON()) });
    if (!r.ok) throw new Error("subscribe failed: " + r.status);
    say("This device gets browser notifications.");
  }

  async function ask() {
    localStorage.setItem(ASKED, "1");
    const perm = await Notification.requestPermission();
    if (perm === "granted") { await subscribe(); }
    else { say("Blocked by this browser. Allow notifications for this site in the browser's site settings, then use the button."); if (button) button.hidden = false; }
  }

  (async () => {
    if (!enabled) { say("Off by your setting above."); return; }
    const isIOS = /iP(hone|ad|od)/.test(navigator.userAgent);
    const standalone = window.matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
    if (isIOS && !standalone) { say("On iPhone and iPad, add this site to the home screen first; notifications work from the installed app."); return; }
    if (Notification.permission === "granted") { try { await subscribe(); } catch (e) { say("Could not register this device: " + e.message); } return; }
    if (Notification.permission === "denied") { say("Blocked by this browser. Allow notifications for this site in the browser's site settings."); return; }
    if (!localStorage.getItem(ASKED)) { try { await ask(); } catch (e) { say("Could not register this device: " + e.message); } }
    else { say("Not yet allowed on this device."); if (button) button.hidden = false; }
  })();
  if (button) button.addEventListener("click", () => ask().catch((e) => say("Could not register this device: " + e.message)));
})();
