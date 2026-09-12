# W3USR AI Project Template

A starter scaffold for AI-assisted projects of the **University of Scranton Amateur Radio
Club (W3USR)**.

The template does two things:

1. Keeps club work compliant with University of Scranton, HamSCI, NASA, NSF, and grant-funder
   policies on generative AI, through a mandatory session log and a `/commit` workflow that
   enforces it.
2. Gives new club members a fifteen-minute on-ramp in [`docs/ONBOARDING.md`](docs/ONBOARDING.md),
   starting with the Generative AI Use Agreement they sign before using AI tools, so they can
   contribute without having used git or Claude Code before.

The same scaffold supports:

- **Software projects**: log tools, propagation analysis, satellite tracking, dashboards, rig control
- **Web projects**: the club website, event pages, outreach material
- **Writing projects**: papers, posters, grant applications, reports, newsletters, typically
  with an `overleaf/` submodule
- **Station and hardware projects**: antenna builds, station documentation, equipment records
- **Mixed projects**: any combination

## Use as a GitHub Template

```bash
gh repo create w3usr/my-new-project --template w3usr/ai_project_template --clone
```

Add `--public` or `--private` to that command deliberately; see step 2 below. You can also
click **Use this template** on the GitHub repository page.

## After Instantiation

1. **Replace placeholders.** Search the repo for `{{` and replace every `{{PLACEHOLDER}}` in
   `CLAUDE.md`, `.claude/rules/ai-governance.md`, and `ai/ai_usage_log.md`:
   ```bash
   grep -rn '{{' . --exclude-dir=.git
   ```
   Common ones: `{{PROJECT_NAME}}`, `{{PROJECT_TITLE}}`, `{{REPO_NAME}}`, `{{PROJECT_PERIOD}}`,
   the project lead, the advisor, the trustee, and `{{FUNDER}}`.

   Then clear `ai/ai_usage_log.md` of every entry below its append marker. Those entries
   belong to the template repository, and the new project's log starts empty.

2. **Decide the repository's visibility and record it.** `CLAUDE.md` has a section for this
   with criteria and a place for the decision, the date, and the reason. This template sets no
   default, because the answer changes what may be committed. Decide it before the first
   commit rather than after.

3. **Prune the rule files that do not apply.**
   ```bash
   rm .claude/rules/web-development.md   # no web work
   rm .claude/rules/latex-writing.md     # no LaTeX
   rm .claude/rules/python-code.md       # no Python
   ```
   `ai-governance.md` stays in every club project.

   Projects with needs of their own add their own rule file. A station or on-air project,
   for instance, is the right place to write down its operating constraints, because those
   constraints depend on the project.

4. **Replace the `LICENSE`.** The template itself is CC BY 4.0; an instantiated project
   picks its own. Software the club wants others to reuse: MIT or BSD-3-Clause.
   Documentation and outreach material: CC BY 4.0. Ask the advisor if the work is
   grant-funded, since some awards carry licensing terms.

5. **Add the project's own top-level folders**, e.g. `src/`, `web/`, `station/`, `outreach/`,
   `hardware/`, `logs/`, `manuscript/`.

6. **Add submodules if needed.**
   ```bash
   git submodule add https://git.overleaf.com/<id> overleaf
   git submodule add git@github.com:w3usr/<repo>.git <path>
   ```

7. **Point new members at [`docs/ONBOARDING.md`](docs/ONBOARDING.md)** before their first
   commit.

## What This Template Provides

| Path | Purpose |
|---|---|
| `CLAUDE.md` | Project instructions Claude Code reads automatically, with placeholders, the visibility decision, and the never-commit list |
| `docs/ONBOARDING.md` | Student-facing on-ramp: the signing gate, the things that matter, a first-fifteen-minutes checklist, the working loop, and who to ask |
| `docs/ai_policy_agreement/` | The HamSCI Generative AI Use Agreement, signed before a member uses AI tools on a club project |
| `.claude/rules/ai-governance.md` | Scranton, HamSCI, NASA, NSF, and grant-funder AI policy; logging requirements; disclosure table; FERPA |
| `.claude/rules/web-development.md` | Content accuracy, University identity, accessibility, secrets, workflow |
| `.claude/rules/latex-writing.md` | Citation integrity, crediting students and funders, figures, build hygiene |
| `.claude/rules/python-code.md` | Code standards, data handling, commit workflow |
| `.claude/commands/commit.md` | The `/commit` slash command: logs the AI session, commits submodules first, then the main repo |
| `ai/ai_usage_log.md` | Append-only log of every substantive AI-assisted session |
| `.gitignore` | Build artifacts, secrets, and bulk data for Python, LaTeX, and web projects |
| `LICENSE`, `NOTICE` | CC BY 4.0, covering the scaffold itself. Replace both with the project's own license. |

## The Non-Negotiable

Every project from this template inherits one rule that does not bend:

**Every substantive AI session is logged before the work is committed.** Run `/commit`.

Everything else in here exists to make that easy to follow.

## Maintaining This Template

Improvements go back into `w3usr/ai_project_template` so the next project starts from them.
A change that turns out to matter for one project usually matters for all of them: a rule that
was ambiguous, a placeholder nobody knew how to fill, a step in onboarding that lost someone.

73 de W3USR
