# AI Usage Log: ops.w3usr.org

A project of the University of Scranton Amateur Radio Club (W3USR).

This log records every substantive AI-assisted session for the W3USR operations and contest
support web application.

Required by the University of Scranton AI Policy, the HamSCI Generative AI Use Agreement,
NASA and NSF guidance on generative AI in funded research, and the expectations of any funder
named in `CLAUDE.md`. See `.claude/rules/ai-governance.md`.

**This repository is public, so this log is public.** Write entries that are accurate and
that you are content to have read by the University, by a funder, and by the wider amateur
radio community. Understating the scope of AI use is the failure to avoid.

---

## Entry format

```
## [YYYY-MM-DD HH:MM TZ]
- **Tool**: Claude (Anthropic), <exact-model-id>
- **Session Purpose**: What this session set out to do
- **Sections/Files Affected**: The specific files or documents touched
- **Nature of Contribution**: Draft / Edit / Analysis / Code generation / Research / Scaffolding
- **Human Review Status**: Reviewed and verified / Partially reviewed / Pending review
- **Git Hash**: Filled in after committing
```

Date and time come from the system clock via `date`, never from an estimate. The Tool field
carries the actual running model ID.

---

<!-- Append new entries below this line, newest at the bottom. -->

## [2026-09-12 15:24 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Convert the fresh `ai_project_template` instantiation into the
  ops.w3usr.org project: relicense to GPL-3.0, write a requirements skeleton for a later
  requirements session, and stand up a holding page so the domain serves something while the
  application is designed.
- **Sections/Files Affected**: `LICENSE` (replaced with GNU GPL v3); `NOTICE` (rewritten:
  GPL notice, club-seal and University trademark statement, template attribution);
  `README.md` and `CLAUDE.md` (rewritten for this project; visibility recorded as public with
  the reason, and the never-commit list tightened because the repository is public);
  `docs/REQUIREMENTS.md` (new, a skeleton with no decided requirements);
  `web/index.html`, `web/favicon.ico`, `web/assets/` (new holding page and images derived
  from the club logo); `ai/ai_usage_log.md` (reset; template entries removed);
  `.claude/rules/ai-governance.md` (funder section resolved, project-specific section written
  for a public repository); `.claude/rules/latex-writing.md` (deleted; no LaTeX here).
- **Nature of Contribution**: Scaffolding, draft, and code generation. The GPL-3.0 text was
  retrieved from the GitHub licenses API rather than reproduced from memory. Holding-page
  colors were sampled from the club logo file. Text contrast was computed against the WCAG
  2.1 formula, which caught a focus-ring that failed SC 1.4.11; it was changed.
- **Human Review Status**: Partially reviewed. The scaffolding, license, and holding page were
  directed by W2NAF and are his to confirm. `docs/REQUIREMENTS.md` is explicitly **not**
  reviewed or adopted: it is a skeleton of headings and open questions, it contains no decided
  requirements, and it is to be revised in a dedicated session. Placeholders marked `{{TBD}}`
  in `CLAUDE.md` (project lead, trustee, meeting time, project period) await club input.
- **Git Hash**: 58c1332

## [2026-09-12 15:47 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Make the club-page link on the holding page use the same URL form as
  the Cloudflare redirect target, so a visitor and a redirected visitor land in the same
  place.
- **Sections/Files Affected**: `web/index.html` (one href)
- **Nature of Contribution**: Edit
- **Human Review Status**: Pending review. The URL `https://scranton.edu/w3usr` is taken from
  the w3usr GitHub organisation profile and could NOT be verified: scranton.edu refuses
  connections from the machines available to this session. W2NAF is to confirm it in a
  browser, and if it redirects, the landing URL should replace it here and in the redirect
  rule.
- **Git Hash**: ab23403

## [2026-09-12 15:52 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Correct the University club page URL. The previous value was a guess
  taken from the w3usr GitHub organisation profile and was wrong; W2NAF supplied the real one.
- **Sections/Files Affected**: `web/index.html` (the club page button),
  `docs/REQUIREMENTS.md` §3.4 and §8 (references to the club's public web presence)
- **Nature of Contribution**: Edit
- **Human Review Status**: Reviewed and verified. The URL
  `https://www.scranton.edu/academics/cas/physics-engineering/w3usr/index.shtml` was supplied
  by W2NAF from his browser on 2026-09-12. It remains unverifiable from this network, because
  scranton.edu refuses connections from the machines available to this session.
- **Git Hash**: f3e3e59

## [2026-09-12 15:58 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Point the club page link at the University's vanity URL,
  `https://scranton.edu/w3usr`, rather than the department page it resolves to. The
  University maintains the vanity mapping, so it survives a site reorganisation that would
  break a deep path.
- **Sections/Files Affected**: `web/index.html` (the club page button),
  `docs/REQUIREMENTS.md` §3.4
- **Nature of Contribution**: Edit
- **Human Review Status**: Reviewed and verified. W2NAF confirmed on 2026-09-12 that
  `scranton.edu/w3usr` redirects to
  `https://www.scranton.edu/academics/cas/physics-engineering/w3usr/index.shtml`. Neither URL
  is reachable from this network, so his browser is the source.
- **Git Hash**: [filled in after committing]
