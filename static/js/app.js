// Small enhancements only; every page works without JavaScript (TR-4).
// The CSP allows scripts from this origin and nothing inline, so everything lives here.

// Copy buttons (invitation link and text).
document.addEventListener("click", (ev) => {
  const btn = ev.target.closest("[data-copy]");
  if (!btn) return;
  const el = document.querySelector(btn.dataset.copy);
  if (!el) return;
  navigator.clipboard.writeText(el.value || el.textContent).then(() => {
    const said = document.getElementById("said"); // a changed label alone is not announced (341)
    if (said) {
      said.textContent = "";
      setTimeout(() => {
        said.textContent = "Copied";
      }, 50);
    }
    // A button that is a glyph keeps its glyph: swapping textContent would throw the icon away.
    if (btn.querySelector("svg")) {
      const label = btn.getAttribute("aria-label");
      btn.classList.add("copied");
      btn.setAttribute("aria-label", "Copied");
      setTimeout(() => {
        btn.classList.remove("copied");
        btn.setAttribute("aria-label", label);
      }, 1500);
    } else {
      const old = btn.textContent;
      btn.textContent = "Copied";
      setTimeout(() => (btn.textContent = old), 1500);
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
      toggle.setAttribute(
        "aria-label",
        rail ? "Expand the menu" : "Collapse the menu to icons",
      );
      if (label) label.textContent = rail ? "Expand" : "Collapse";
    };
    toggle.addEventListener("click", () => {
      const rail = html.getAttribute("data-nav") !== "rail";
      if (rail) html.setAttribute("data-nav", "rail");
      else html.removeAttribute("data-nav");
      try {
        localStorage.setItem("arcops.nav", rail ? "rail" : "full");
      } catch (e) {
        /* fine */
      }
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
    if (on) (close || nav.querySelector("a")).focus();
    else if (open) open.focus();
  };
  if (open) open.addEventListener("click", () => setOpen(true));
  if (close) close.addEventListener("click", () => setOpen(false));
  if (backdrop) backdrop.addEventListener("click", () => setOpen(false));
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && nav.classList.contains("open")) setOpen(false);
  });
})();

// Progressive disclosure: an element with data-reveal-when="#control" is shown only while that
// control is ticked (the guardian field on the invitation form), or, with data-reveal-value,
// while the control holds one of those space-separated values (the student fields on a member's
// page). A control that is itself hidden hides what it reveals, so they nest (when a net meets);
// all are synced in page order on any change. The server enforces the rule regardless.
(() => {
  const reveals = [...document.querySelectorAll("[data-reveal-when]")];
  const sync = () =>
    reveals.forEach((el) => {
      const ctl = document.querySelector(el.dataset.revealWhen);
      if (!ctl) return;
      const want = el.dataset.revealValue;
      const on =
        want === undefined ? ctl.checked : want.split(" ").includes(ctl.value);
      el.hidden = !on || !!ctl.closest("[hidden]");
    });
  if (reveals.length) {
    document.addEventListener("change", sync);
    sync();
  }
})();

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(() => {}); // served by Django, never cached (FR-96)
  // Signed out (base.html marks <main> "plain"): the offline copies of the member's own pages go.
  if (document.querySelector("main.plain")) {
    navigator.serviceWorker.ready.then(
      (r) => r.active && r.active.postMessage("signed-out"),
    );
  }
}

// The slot and Manage dialogs: a link htmx could not fetch opens as its own page, as it does
// without JavaScript; the backdrop or a [data-close] button closes the dialog, which empties it
// and gives focus back to what refocus() returns.
function wireDialog(dlg, opener, refocus) {
  const fallBack = (ev) => {
    const a = ev.detail.elt.closest(opener);
    if (a) window.location = a.href;
  };
  document.addEventListener("htmx:responseError", fallBack);
  document.addEventListener("htmx:sendError", fallBack);
  dlg.addEventListener("click", (ev) => {
    if (ev.target === dlg || ev.target.closest("[data-close]")) dlg.close();
  });
  dlg.addEventListener("close", () => {
    dlg.querySelector(".dialog-body").innerHTML = "";
    const a = refocus();
    if (a) a.focus();
  });
}

// Roster: a slot opens in a dialog; the checkboxes drive a bulk bar; a day heading's box selects
// its whole day. Without JavaScript the slot link is a page and the bar is simply always shown.
(() => {
  const dlg = document.getElementById("slot-dialog");
  if (dlg && typeof dlg.showModal === "function" && window.htmx) {
    // htmx fills the dialog, from a slot link and again after each action in it. Focus
    // goes to what just happened, or else to the slot's heading.
    const body = dlg.querySelector(".dialog-body");
    let openerSlot = null;
    document.addEventListener("htmx:afterSwap", (ev) => {
      if (ev.detail.target !== body) return;
      const a = ev.detail.requestConfig.elt.closest("a[data-slot]"); // detail.elt is the target here
      if (a) openerSlot = a.dataset.slot;
      // The answer carries the slot's roster cell, so the link just pressed has been replaced. Focus
      // its replacement before opening: the dialog hands focus back to it when it closes.
      if (!dlg.open) {
        const back =
          openerSlot && document.querySelector(`a[data-slot="${openerSlot}"]`);
        if (back) back.focus();
        dlg.showModal();
      }
      const f = body.querySelector(".messages") || body.querySelector("h1");
      if (f) {
        f.setAttribute("tabindex", "-1");
        f.focus();
      }
    });
    // Back to the slot's link, found afresh, when an action in the dialog replaced its cell.
    wireDialog(
      dlg,
      "a[data-slot]",
      () =>
        openerSlot && document.querySelector(`a[data-slot="${openerSlot}"]`),
    );
  }

  const bar = document.getElementById("bulk-bar");
  const form = document.getElementById("roster-form");
  if (bar && form) {
    const boxes = () => form.querySelectorAll('input[name="slots"]');
    const update = () => {
      const n = [...boxes()].filter((b) => b.checked).length;
      bar.classList.toggle("active", n > 0);
      const c = bar.querySelector("[data-count]");
      if (c) c.textContent = String(n);
    };
    form.addEventListener("change", (ev) => {
      const t = ev.target;
      if (t.matches("[data-select-all]")) {
        // every slot, for a captain's bulk change (282)
        form
          .querySelectorAll('input[name="slots"], [data-select-day]')
          .forEach((b) => {
            b.checked = t.checked;
          });
      }
      if (t.matches("[data-select-day]")) {
        form
          .querySelectorAll(
            `input[name="slots"][data-day="${t.dataset.selectDay}"]`,
          )
          .forEach((b) => {
            b.checked = t.checked;
          });
      }
      if (t.matches("[data-select-fold]")) {
        // a folded run's own box: its hours, one tick (FR-55)
        form
          .querySelectorAll(
            `.r-row[data-fold="${t.dataset.selectFold}"] input[name="slots"]`,
          )
          .forEach((b) => {
            b.checked = t.checked;
          });
      }
      update();
    });
    update();
  }
})();

// Manage's forms open in a dialog. Each button is a link to the form's own page; htmx
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
    const f =
      body.querySelector(".msg.error") ||
      body.querySelector("[aria-invalid=true]") ||
      body.querySelector("input:not([type=hidden]), select, textarea") ||
      body.querySelector("h1");
    if (f) {
      if (f.matches(".msg, h1")) f.setAttribute("tabindex", "-1");
      f.focus();
    }
  });
  wireDialog(dlg, "a[data-dialog]", () => opener);
})();

// A step's own form saved in place: htmx swaps the step and the bar, and focus would be
// left on a button that no longer exists. Note which section the form was in before the request;
// after the swap, focus the message if there is one, or else that section's heading.
(() => {
  let section = null;
  document.addEventListener("htmx:beforeRequest", (ev) => {
    const form =
      ev.detail.elt.closest && ev.detail.elt.closest("form[data-in-place]");
    if (form)
      section = form.closest("section")?.getAttribute("aria-labelledby") || "";
  });
  document.addEventListener("htmx:afterSettle", () => {
    if (section === null) return;
    const stage = document.getElementById("stage-body");
    const f =
      (stage && stage.querySelector(".messages")) ||
      (section && document.getElementById(section)) ||
      (stage && stage.querySelector("h2"));
    section = null;
    if (f) {
      f.setAttribute("tabindex", "-1");
      f.focus();
    }
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
  document.addEventListener(
    "close",
    (ev) => {
      if (
        !opener ||
        ev.target.id !== opener.getAttribute("commandfor") ||
        !opener.isConnected
      )
        return;
      // Opened from a ⋮ menu: the menu closed when the dialog opened, so go back to its button.
      const menu = opener.closest("[popover]");
      const back =
        menu && !menu.matches(":popover-open")
          ? document.querySelector(`[popovertarget="${menu.id}"]`)
          : opener;
      if (back) back.focus();
    },
    true,
  ); // a dialog's close event does not bubble; catch it on the way down
})();

// ⋮ menus (technical addendum A10): the popover opens and closes itself, with Escape and a
// click outside. This moves focus to its first entry, and places it under its button where CSS
// anchor positioning has not (a browser before 2026, or one without the popover's implicit anchor).
(() => {
  document.addEventListener(
    "toggle",
    (ev) => {
      const m = ev.target;
      if (!(m instanceof HTMLElement) || !m.classList.contains("menu")) return;
      const b = document.querySelector(`[popovertarget="${m.id}"]`);
      if (ev.newState === "closed") {
        // Safari does not focus a button it clicks, so it has nowhere to give focus back to and
        // drops it on <main>: when focus is in the menu, or nowhere a reader can Tab to (the body,
        // or a container focusable only by script), it goes back to the ⋮ button.
        const at = document.activeElement;
        const nowhere =
          !at || at === document.body || at.getAttribute("tabindex") === "-1";
        if (b && (nowhere || m.contains(at))) b.focus();
        return;
      }
      if (b) {
        m.style.cssText = "";
        const r = b.getBoundingClientRect(),
          mr = m.getBoundingClientRect();
        if (
          Math.abs(mr.top - r.bottom) > 12 &&
          Math.abs(r.top - mr.bottom) > 12
        ) {
          m.style.cssText =
            `position: fixed; inset: auto; margin: 0; top: ${r.bottom + 4}px; ` +
            `left: ${Math.max(8, Math.min(r.right - mr.width, innerWidth - mr.width - 8))}px`;
        }
      }
      const first = m.querySelector("a[href], button:not([disabled])");
      if (first) first.focus();
    },
    true,
  ); // toggle does not bubble either
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

// A folded run of open hours opens in place: its rows are on the page already, hidden.
// Without JavaScript the same link reloads the roster with the run open.
document.addEventListener("click", (ev) => {
  const link = ev.target.closest("[data-open-fold]");
  if (!link) return;
  ev.preventDefault();
  const id = link.dataset.openFold;
  const rows = document.querySelectorAll(`.r-row[data-fold="${id}"]`);
  rows.forEach((r) => {
    r.hidden = false;
  });
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
  // ...and starts from the rule the event applies to that role, carried on its choice.
  const rule = JSON.parse(sel.selectedOptions[0]?.dataset.rule || "null");
  if (!rule) return;
  sel.form.querySelectorAll("[data-role-field]").forEach((el) => {
    const f = el.dataset.roleField;
    if (f === "class") el.value = rule.class || "";
    else if (f === "minors") el.checked = !!rule.minors_allowed;
    else if (f === "cat")
      el.checked = (rule.categories || []).includes(el.value);
    else if (f === "cred")
      el.checked = (rule.credentials || []).includes(el.value);
  });
});

// A field showing a default: its tag ("Club default", "Same as a
// slot") goes once the value differs from it. A field that follows another (a setup slot's
// length follows the slot length) copies it until it is typed in, and then says so to the
// server through its *_edited box, so an untouched one keeps following there too.
document.addEventListener("input", (ev) => {
  const el = ev.target;
  if (!(el instanceof HTMLInputElement) || !el.form) return;
  const tag = (f) => f.form.querySelector(`[data-default-tag-for="${f.id}"]`);
  if (el.dataset.follows !== undefined) {
    el.dataset.edited = "1";
    const flag = el.form.elements[el.name + "_edited"];
    if (flag) flag.value = "1";
  }
  if (el.dataset.default !== undefined) {
    const t = tag(el);
    if (t) t.hidden = el.value !== el.dataset.default;
  }
  el.form.querySelectorAll(`[data-follows="${el.name}"]`).forEach((f) => {
    if (f.dataset.edited) return;
    f.value = el.value;
    f.dataset.default = el.value;
    const t = tag(f);
    if (t) t.hidden = false;
  });
});

// The viewer's own time zone (functional addendum A38): pages show local
// time only. The browser names its zone in the `tz` cookie and the server draws every page in it
// (apps/ops/middleware.py); the page says which zone it was drawn in on <html data-tz>. A time
// box holds that zone's wall clock and is sent as ISO 8601 with the offset, so the server stores
// UTC without guessing. A time the clocks skip or repeat is refused before sending, as the
// server refuses it without JavaScript (apps/ops/when.py in_zone).
(() => {
  let browser = "";
  try {
    browser = Intl.DateTimeFormat().resolvedOptions().timeZone || "";
  } catch {
    /* no Intl */
  }
  if (
    /^[A-Za-z0-9_+\-/]{1,64}$/.test(browser) &&
    !document.cookie.split("; ").includes(`tz=${browser}`)
  ) {
    document.cookie = `tz=${browser}; path=/; max-age=31536000; SameSite=Lax${location.protocol === "https:" ? "; Secure" : ""}`;
  }
  const zone = document.documentElement.dataset.tz || browser || "UTC";
  const pad = (n) => String(n).padStart(2, "0");
  const asUtc = (v) =>
    Date.UTC(
      +v.slice(0, 4),
      +v.slice(5, 7) - 1,
      +v.slice(8, 10),
      +v.slice(11, 13),
      +v.slice(14, 16),
    );
  const wall = (ms) => {
    // the wall clock in `zone` at instant `ms`, as a box value
    const p = Object.fromEntries(
      new Intl.DateTimeFormat("en-US", {
        timeZone: zone,
        hourCycle: "h23",
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      })
        .formatToParts(new Date(ms))
        .map((x) => [x.type, x.value]),
    );
    return `${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}`;
  };
  // The instants whose wall clock reads v: none in the hour the clocks go forward, two in the
  // hour they go back.
  const instants = (v) => {
    const guess = asUtc(v),
      day = 864e5,
      off = (ms) => asUtc(wall(ms)) - ms;
    return [
      ...new Set([off(guess - day), off(guess + day)].map((o) => guess - o)),
    ].filter((t) => wall(t) === v);
  };
  const withOffset = (v, ms) => {
    // 2026-11-21T16:00-05:00
    const m = Math.round((asUtc(v) - ms) / 6e4),
      a = Math.abs(m);
    return `${v}:00${m < 0 ? "-" : "+"}${pad(Math.floor(a / 60))}:${pad(a % 60)}`;
  };
  const valid = (v) => /^\d{4}-\d\d-\d\dT\d\d:\d\d$/.test(v);
  const check = (box) => {
    // the refusal, said under the box and held as the box's validity
    const v = box.value.slice(0, 16);
    const n = valid(v) ? instants(v).length : 1;
    const why =
      n === 1
        ? ""
        : n
          ? "This time happens twice here, as the clocks go back. Choose a time outside that hour."
          : "This time does not happen here: the clocks go forward that night. Choose a time outside that hour.";
    let line = document.getElementById(`${box.id}-dst`);
    if (why && !line && box.id) {
      line = Object.assign(document.createElement("span"), {
        className: "helptext",
        id: `${box.id}-dst`,
      });
      box.after(line);
      box.setAttribute(
        "aria-describedby",
        [box.getAttribute("aria-describedby"), line.id]
          .filter(Boolean)
          .join(" "),
      );
    }
    if (line) line.textContent = why;
    box.setCustomValidity(why);
  };
  const BOX = 'input[type="datetime-local"][data-instant]';
  document.addEventListener("input", (ev) => {
    if (ev.target.matches?.(BOX)) check(ev.target);
  });
  // Capture, so the offset is in place before htmx or the browser reads the form.
  document.addEventListener(
    "submit",
    (ev) => {
      ev.target.querySelectorAll(BOX).forEach((box) => {
        const name = box.dataset.name || box.name;
        if (!name) return;
        box.dataset.name = name;
        ev.target
          .querySelector(`input[type="hidden"][data-for="${box.id}"]`)
          ?.remove();
        const v = box.value.slice(0, 16),
          found = valid(v) ? instants(v) : [];
        if (found.length !== 1) {
          box.name = name;
          return;
        } // empty or refused: sent as typed
        box.removeAttribute("name");
        box.after(
          Object.assign(document.createElement("input"), {
            type: "hidden",
            name,
            value: withOffset(v, found[0]),
          }),
        );
        box.nextElementSibling.dataset.for = box.id;
      });
    },
    true,
  );
})();

// A "select every" box outside the roster: ticks the boxes of its form, which may sit elsewhere
// on the page and join the form by `form=` (Approvals, FR-28).
document.addEventListener("change", (ev) => {
  const all = ev.target;
  if (!all.matches("[data-check-all]") || !all.form) return;
  [...all.form.elements]
    .filter((b) => b.name === all.dataset.checkAll)
    .forEach((b) => {
      b.checked = all.checked;
    });
});
