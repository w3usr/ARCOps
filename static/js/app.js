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

// Progressive disclosure: an element with data-reveal-when="#control" is shown only while that
// control is ticked (the guardian field on the invitation form), or, with data-reveal-value,
// while the control holds that value (the student fields on a member's page). The server
// enforces the underlying rule regardless.
document.querySelectorAll("[data-reveal-when]").forEach((el) => {
  const ctl = document.querySelector(el.dataset.revealWhen);
  if (!ctl) return;
  const want = el.dataset.revealValue;
  const sync = () => { el.hidden = want === undefined ? !ctl.checked : ctl.value !== want; };
  ctl.addEventListener("change", sync);
  sync();
});

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(() => {});  // served by Django, never cached (FR-96)
}

// Roster: a slot opens in a dialog (the same page, fetched as a fragment); the checkboxes drive
// a bulk bar; a day heading's box selects its whole day. Without JavaScript the slot link is a
// page and the bar is simply always shown.
(() => {
  const dlg = document.getElementById("slot-dialog");
  if (dlg && typeof dlg.showModal === "function" && window.fetch) {
    const body = dlg.querySelector(".dialog-body");
    let opener = null;
    document.addEventListener("click", async (ev) => {
      const a = ev.target.closest("a[data-slot]");
      if (!a) return;
      ev.preventDefault();
      opener = a;
      try {
        const res = await fetch(a.href + (a.href.includes("?") ? "&" : "?") + "partial=1", { credentials: "same-origin" });
        if (!res.ok) { window.location = a.href; return; }
        body.innerHTML = await res.text();
        dlg.showModal();
        const h = body.querySelector("h1"); if (h) { h.setAttribute("tabindex", "-1"); h.focus(); }
      } catch (e) { window.location = a.href; }
    });
    dlg.addEventListener("click", (ev) => { if (ev.target === dlg || ev.target.closest("[data-close]")) dlg.close(); });
    dlg.addEventListener("close", () => { body.innerHTML = ""; if (opener) opener.focus(); });
  }

  const bar = document.getElementById("bulk-bar");
  const form = document.getElementById("roster-form");
  if (bar && form) {
    const boxes = () => form.querySelectorAll('input[name="slots"]');
    const update = () => {
      const n = [...boxes()].filter((b) => b.checked).length;
      bar.classList.toggle("active", n > 0);
      const c = bar.querySelector("[data-count]"); if (c) c.textContent = String(n);
    };
    form.addEventListener("change", (ev) => {
      const t = ev.target;
      if (t.matches("[data-select-day]")) {
        form.querySelectorAll(`input[name="slots"][data-day="${t.dataset.selectDay}"]`).forEach((b) => { b.checked = t.checked; });
      }
      update();
    });
    update();
  }
})();

// Flash messages: a live region that is already on the page when it loads announces nothing,
// so move focus to it once. The list is tabindex="-1", so it never enters the tab order.
(() => {
  const list = document.getElementById("messages");
  if (list) list.focus({ preventScroll: true });
})();

// Slot eligibility override: the role select renames the fields that go with it. This was an
// inline onchange, which the CSP (script-src 'self') blocks, so every override was written
// against the first role whatever the captain picked.
document.addEventListener("change", (ev) => {
  const sel = ev.target.closest("[data-role-select]");
  if (!sel || !sel.form) return;
  sel.form.querySelectorAll("[data-role-field]").forEach((el) => {
    el.name = el.dataset.roleField + "_" + sel.value;
  });
});
