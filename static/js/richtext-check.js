// FR-115: the editor encourages structure. After each change, check the heading order in the
// editor's content and say so beneath it when a level is skipped (H1 to H3). Nothing is blocked.
(function () {
  function check(ed) {
    const body = ed.getBody();
    if (!body) return;
    const hs = body.querySelectorAll("h1,h2,h3,h4");
    let prev = 0,
      skipped = false;
    hs.forEach((h) => {
      const lvl = +h.tagName[1];
      if (prev && lvl > prev + 1) skipped = true;
      prev = lvl;
    });
    const el = ed.getElement();
    let note = el.parentNode.querySelector(".heading-note");
    if (!note) {
      // Made when the editor starts, empty, so a screen reader hears it when it is filled.
      note = document.createElement("p");
      note.className = "helptext heading-note";
      note.setAttribute("role", "status");
      el.parentNode.appendChild(note);
    }
    note.textContent = skipped
      ? "A heading level is skipped (for example Heading 1 straight to Heading 3). Screen readers follow the levels; keep them in order."
      : "";
  }
  // FR-116: the editing area is named by the field's own label, not the library's "Rich Text
  // Area", so two editors on one page are told apart.
  function name(ed) {
    const label = document.querySelector(`label[for="${ed.id}"]`);
    if (label && ed.iframeElement)
      ed.iframeElement.title = label.textContent.trim();
  }
  function watch(ed) {
    ed.on("init", () => name(ed));
    ed.on("init change keyup SetContent", () => check(ed));
    if (ed.initialized) {
      name(ed);
      check(ed);
    }
  }
  function arm() {
    if (!window.tinymce) return;
    // django-tinymce starts the editors before this script runs, so the ones already on the page
    // are taken up here; AddEditor catches any added later.
    window.tinymce.get().forEach(watch);
    window.tinymce.on("AddEditor", (e) => watch(e.editor));
  }
  if (window.tinymce) arm();
  else document.addEventListener("DOMContentLoaded", arm);
})();
