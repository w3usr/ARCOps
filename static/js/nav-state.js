// Runs in <head>, before first paint: marks JavaScript as available (the stylesheet keys the
// drawer behaviour on html.js) and restores the remembered sidebar state, so the layout never
// flashes from full to rail. Presentation only; without it the page still works (TR-4).
(function () {
  var html = document.documentElement;
  html.classList.remove("no-js");
  html.classList.add("js");
  try {
    if (localStorage.getItem("arcops.nav") === "rail") html.setAttribute("data-nav", "rail");
  } catch (e) { /* storage unavailable: full sidebar */ }
})();
