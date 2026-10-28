// Small enhancements only; every page works without JavaScript (TR-4).
// The CSP allows scripts from this origin and nothing inline, so everything lives here.

// Copy buttons (invitation link and text).
document.addEventListener("click", (ev) => {
  const btn = ev.target.closest("[data-copy]");
  if (!btn) return;
  const el = document.querySelector(btn.dataset.copy);
  if (!el) return;
  navigator.clipboard.writeText(el.value || el.textContent).then(() => {
    // A button that is a glyph keeps its glyph: swapping textContent would throw the icon away.
    if (btn.querySelector("svg")) {
      const label = btn.getAttribute("aria-label");
      btn.classList.add("copied");
      btn.setAttribute("aria-label", "Copied");
      setTimeout(() => { btn.classList.remove("copied"); btn.setAttribute("aria-label", label); }, 1500);
    } else {
      const old = btn.textContent; btn.textContent = "Copied"; setTimeout(() => (btn.textContent = old), 1500);
    }
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

// Roster: a slot opens in a dialog; the checkboxes drive a bulk bar; a day heading's box selects
// its whole day. Without JavaScript the slot link is a page and the bar is simply always shown.
(() => {
  const dlg = document.getElementById("slot-dialog");
  if (dlg && typeof dlg.showModal === "function" && window.htmx) {
    // htmx fills the dialog, from a slot link and again after each action in it (#139). Focus
    // goes to what just happened, or else to the slot's heading.
    const body = dlg.querySelector(".dialog-body");
    let openerSlot = null;
    document.addEventListener("htmx:afterSwap", (ev) => {
      if (ev.detail.target !== body) return;
      const a = ev.detail.requestConfig.elt.closest("a[data-slot]");  // detail.elt is the target here
      if (a) openerSlot = a.dataset.slot;
      // The answer carries the slot's roster cell, so the link just pressed has been replaced. Focus
      // its replacement before opening: the dialog hands focus back to it when it closes.
      if (!dlg.open) {
        const back = openerSlot && document.querySelector(`a[data-slot="${openerSlot}"]`);
        if (back) back.focus();
        dlg.showModal();
      }
      const f = body.querySelector(".messages") || body.querySelector("h1");
      if (f) { f.setAttribute("tabindex", "-1"); f.focus(); }
    });
    // A slot htmx could not fetch opens as its own page, as it does without JavaScript.
    const fallBack = (ev) => { const a = ev.detail.elt.closest("a[data-slot]"); if (a) window.location = a.href; };
    document.addEventListener("htmx:responseError", fallBack);
    document.addEventListener("htmx:sendError", fallBack);
    dlg.addEventListener("click", (ev) => { if (ev.target === dlg || ev.target.closest("[data-close]")) dlg.close(); });
    // Back to the slot's link, found afresh, when an action in the dialog replaced its cell.
    dlg.addEventListener("close", () => {
      body.innerHTML = "";
      const a = openerSlot && document.querySelector(`a[data-slot="${openerSlot}"]`);
      if (a) a.focus();
    });
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
