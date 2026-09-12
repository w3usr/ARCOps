---
paths:
  - "**/*.tex"
  - "**/*.bib"
  - "**/*.cls"
  - "**/*.sty"
---

# LaTeX Writing Rules
*Delete this file if the project includes no LaTeX.*

Applies to LaTeX source anywhere in the project, typically under `manuscript/`, `poster/`,
`report/`, `proposal/`, or an `overleaf/` submodule. Common club uses: a conference poster,
a HamSCI or ARRL paper, a grant application, a technical report on a station build.

## Document Setup
- Name the document type up front (poster, paper, report, proposal) and record the template or
  style guide it follows in the project's `CLAUDE.md`
- Record the main `.tex` filename and the bibliography path in `CLAUDE.md`
- Keep figures in a `figs/` subdirectory beside the main `.tex`, or wherever the template requires

## Content Rules
- **Never fabricate or hallucinate citations.** Every reference is verified against the actual
  paper before it is cited. Citing a paper you have not opened is how a club embarrasses itself
  in front of the people who wrote it.
- The reference list contains only works cited in the text
- Describe accomplishments that happened, in the terms they actually happened in
- **Credit students, club members, and volunteers by name and callsign**, accurately, in the
  author list or acknowledgments. Undercrediting a student contributor is a real harm.
- Acknowledge funders by name and grant number, exactly as the award requires
- Verify every number in the prose against the data or script that produced it

## Figures
- Every figure is reproducible from a committed script or a recorded procedure
- Captions are self-contained: a reader skimming the figures understands each one
- Color-blind-safe palettes; no rainbow or jet; color is never the only discriminator
- Legends stay off the data

## Workflow
- If the document lives in a submodule, commit there first, then bump the pointer here
- Using Overleaf, pull before editing to avoid conflicts
- Do not commit build artifacts (`.aux`, `.log`, `.bbl`, `.bcf`, `.blg`, `.out`, `.toc`,
  `.fls`, `.fdb_latexmk`); they are gitignored
- Verify a clean rebuild with zero undefined references and zero undefined citations before
  committing significant changes
