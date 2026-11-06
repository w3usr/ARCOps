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
      if (t.matches("[data-select-fold]")) {  // a folded run's own box: its hours, one tick (FR-55)
        form.querySelectorAll(`.r-row[data-fold="${t.dataset.selectFold}"] input[name="slots"]`).forEach((b) => { b.checked = t.checked; });
      }
      update();
    });
    update();
  }
})();

// Manage's forms open in a dialog (#168). Each button is a link to the form's own page; htmx
// fetches that page into the dialog instead, and the form posts back to it there. A save answers
// with HX-Redirect, so the tab reloads with its message; a refusal comes back inside the dialog.
// Focus goes to the problem, or else the first field, and back to the button on closing.
(() => {
  const dlg = document.getElementById("manage-dialog");
  if (!dlg || typeof dlg.showModal !== "function" || !window.htmx) return;
  const body = dlg.querySelector(".dialog-body");
  let opener = null;
  // After the settle, not the swap: htmx wires the new content's own triggers (the generator's
  // line) as it settles, so focus arrives when typing already does something.
  document.addEventListener("htmx:afterSettle", (ev) => {
    if (ev.detail.target !== body) return;
    const a = ev.detail.requestConfig.elt.closest("a[data-dialog]");
    if (a) opener = a;
    if (!dlg.open) dlg.showModal();
    const f = body.querySelector(".msg.error")
      || body.querySelector("[aria-invalid=true]")
      || body.querySelector("input:not([type=hidden]), select, textarea")
      || body.querySelector("h1");
    if (f) { if (f.matches(".msg, h1")) f.setAttribute("tabindex", "-1"); f.focus(); }
  });
  // A form htmx could not fetch opens as its own page, as it does without JavaScript.
  const fallBack = (ev) => { const a = ev.detail.elt.closest("a[data-dialog]"); if (a) window.location = a.href; };
  document.addEventListener("htmx:responseError", fallBack);
  document.addEventListener("htmx:sendError", fallBack);
  dlg.addEventListener("click", (ev) => { if (ev.target === dlg || ev.target.closest("[data-close]")) dlg.close(); });
  dlg.addEventListener("close", () => { body.innerHTML = ""; if (opener) opener.focus(); });
})();

// A step's own form saved in place (#177): htmx swaps the step and the bar, and focus would be
// left on a button that no longer exists. Note which section the form was in before the request;
// after the swap, focus the message if there is one, or else that section's heading.
(() => {
  let section = null;
  document.addEventListener("htmx:beforeRequest", (ev) => {
    const form = ev.detail.elt.closest && ev.detail.elt.closest("form[data-in-place]");
    if (form) section = form.closest("section")?.getAttribute("aria-labelledby") || "";
  });
  document.addEventListener("htmx:afterSettle", () => {
    if (section === null) return;
    const stage = document.getElementById("stage-body");
    const f = (stage && stage.querySelector(".messages")) || (section && document.getElementById(section))
      || (stage && stage.querySelector("h2"));
    section = null;
    if (f) { f.setAttribute("tabindex", "-1"); f.focus(); }
  });
})();

// A confirmation's button opens its dialog by itself (commandfor and command, in every browser
// since late 2025). This does the same for an older one; a current browser never runs it.
// Safari does not focus a button it clicks, so the browser has nothing to give focus back to
// when the dialog closes: remember the button, and return to it.
(() => {
  let opener = null;
  document.addEventListener("click", (ev) => {
    const b = ev.target.closest("button[commandfor][command=show-modal]");
    if (b) opener = b;
  });
  document.addEventListener("close", (ev) => {
    if (!opener || ev.target.id !== opener.getAttribute("commandfor") || !opener.isConnected) return;
    // Opened from a ⋮ menu (#228): the menu closed when the dialog opened, so go back to its button.
    const menu = opener.closest("[popover]");
    const back = menu && !menu.matches(":popover-open") ? document.querySelector(`[popovertarget="${menu.id}"]`) : opener;
    if (back) back.focus();
  }, true);  // a dialog's close event does not bubble; catch it on the way down
})();

// ⋮ menus (#228, technical addendum A10): the popover opens and closes itself, with Escape and a
// click outside. This moves focus to its first entry, and places it under its button where CSS
// anchor positioning has not (a browser before 2026, or one without the popover's implicit anchor).
(() => {
  document.addEventListener("toggle", (ev) => {
    const m = ev.target;
    if (!(m instanceof HTMLElement) || !m.classList.contains("menu")) return;
    const b = document.querySelector(`[popovertarget="${m.id}"]`);
    if (ev.newState === "closed") {
      // Safari does not focus a button it clicks, so it has nowhere to give focus back to and
      // drops it on <main>: when focus is in the menu, or nowhere a reader can Tab to (the body,
      // or a container focusable only by script), it goes back to the ⋮ button.
      const at = document.activeElement;
      const nowhere = !at || at === document.body || at.getAttribute("tabindex") === "-1";
      if (b && (nowhere || m.contains(at))) b.focus();
      return;
    }
    if (b) {
      m.style.cssText = "";
      const r = b.getBoundingClientRect(), mr = m.getBoundingClientRect();
      if (Math.abs(mr.top - r.bottom) > 12 && Math.abs(r.top - mr.bottom) > 12) {
        m.style.cssText = `position: fixed; inset: auto; margin: 0; top: ${r.bottom + 4}px; ` +
          `left: ${Math.max(8, Math.min(r.right - mr.width, innerWidth - mr.width - 8))}px`;
      }
    }
    const first = m.querySelector("a[href], button:not([disabled])");
    if (first) first.focus();
  }, true);  // toggle does not bubble either
})();
if (!("command" in HTMLButtonElement.prototype)) {
  document.addEventListener("click", (ev) => {
    const b = ev.target.closest("button[commandfor]");
    const d = b && document.getElementById(b.getAttribute("commandfor"));
    if (!d || typeof d.showModal !== "function") return;
    if (b.getAttribute("command") === "show-modal" && !d.open) d.showModal();
    else if (b.getAttribute("command") === "close") d.close();
  });
}

// A folded run of open hours opens in place (#161): its rows are on the page already, hidden.
// Without JavaScript the same link reloads the roster with the run open.
document.addEventListener("click", (ev) => {
  const link = ev.target.closest("[data-open-fold]");
  if (!link) return;
  ev.preventDefault();
  const id = link.dataset.openFold;
  const rows = document.querySelectorAll(`.r-row[data-fold="${id}"]`);
  rows.forEach((r) => { r.hidden = false; });
  document.getElementById(`fold-${id}`)?.remove();
  rows[0]?.querySelector(".slot-link")?.focus();
});

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
