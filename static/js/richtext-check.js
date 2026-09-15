// FR-115: the editor encourages structure. After each change, check the heading order in the
// editor's content and say so beneath it when a level is skipped (H1 to H3). Nothing is blocked.
(function () {
  function check(ed) {
    const body = ed.getBody();
    if (!body) return;
    const hs = body.querySelectorAll("h1,h2,h3,h4");
    let prev = 0, skipped = false;
    hs.forEach((h) => { const lvl = +h.tagName[1]; if (prev && lvl > prev + 1) skipped = true; prev = lvl; });
    const el = ed.getElement();
    let note = el.parentNode.querySelector(".heading-note");
    if (!note) { note = document.createElement("p"); note.className = "helptext heading-note"; el.parentNode.appendChild(note); }
    note.textContent = skipped ? "A heading level is skipped (for example Heading 1 straight to Heading 3). Screen readers follow the levels; keep them in order." : "";
  }
  function arm() {
    if (!window.tinymce) return;
    window.tinymce.on("AddEditor", (e) => {
      e.editor.on("init change keyup SetContent", () => check(e.editor));
    });
  }
  if (window.tinymce) arm(); else document.addEventListener("DOMContentLoaded", arm);
})();
