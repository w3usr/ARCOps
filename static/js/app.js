// Small enhancements only; every page works without JavaScript (TR-4).
// The CSP allows scripts from this origin and nothing inline, so everything lives here.

// Copy buttons (invitation link and text).
document.addEventListener("click", (ev) => {
  const btn = ev.target.closest("[data-copy]");
  if (!btn) return;
  const el = document.querySelector(btn.dataset.copy);
  if (!el) return;
  navigator.clipboard.writeText(el.value || el.textContent).then(() => {
    const old = btn.textContent; btn.textContent = "Copied"; setTimeout(() => (btn.textContent = old), 1500);
  });
});

// Sidebar: collapse to an icon rail on wide screens (remembered), drawer on narrow ones.
(() => {
  const html = document.documentElement;
  const nav = document.getElementById("sidenav");
  if (!nav) return;

  const toggle = document.getElementById("nav-toggle");
  if (toggle) {
    const label = toggle.querySelector("span");
    const reflect = () => {
      const rail = html.getAttribute("data-nav") === "rail";
      toggle.setAttribute("aria-pressed", String(rail));
      toggle.setAttribute("aria-label", rail ? "Expand the menu" : "Collapse the menu to icons");
      if (label) label.textContent = rail ? "Expand" : "Collapse";
    };
    toggle.addEventListener("click", () => {
      const rail = html.getAttribute("data-nav") !== "rail";
      if (rail) html.setAttribute("data-nav", "rail"); else html.removeAttribute("data-nav");
      try { localStorage.setItem("arcops.nav", rail ? "rail" : "full"); } catch (e) { /* fine */ }
      reflect();
    });
    reflect();
  }

  const open = document.getElementById("menu-open");
  const close = document.getElementById("menu-close");
  const backdrop = document.getElementById("backdrop");
  const setOpen = (on) => {
    nav.classList.toggle("open", on);
    if (backdrop) backdrop.hidden = !on;
    document.body.classList.toggle("drawer-open", on);
    if (open) open.setAttribute("aria-expanded", String(on));
    if (on) (close || nav.querySelector("a")).focus(); else if (open) open.focus();
  };
  if (open) open.addEventListener("click", () => setOpen(true));
  if (close) close.addEventListener("click", () => setOpen(false));
  if (backdrop) backdrop.addEventListener("click", () => setOpen(false));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && nav.classList.contains("open")) setOpen(false); });
})();

// Progressive disclosure: an element with data-reveal-when="#checkbox" is shown only while
// that checkbox is ticked (the guardian field on the invitation form). The server enforces
// the underlying rule regardless.
document.querySelectorAll("[data-reveal-when]").forEach((el) => {
  const ctl = document.querySelector(el.dataset.revealWhen);
  if (!ctl) return;
  const sync = () => { el.hidden = !ctl.checked; };
  ctl.addEventListener("change", sync);
  sync();
});

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/static/sw.js").catch(() => {});
}
