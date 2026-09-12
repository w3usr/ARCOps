# {{PROJECT_NAME}}

A project of the **University of Scranton Amateur Radio Club (W3USR)**.

New to this club's repositories? Read [`docs/ONBOARDING.md`](docs/ONBOARDING.md) first.

## Project Overview
{{ONE-PARAGRAPH DESCRIPTION: what is being built or written, who it serves, and why the club is doing it.}}

**Project type**: {{Station documentation / Club website / Outreach or demo material / Event or contest operation / Software build / Hardware or antenna build / Grant application / Newsletter, poster, or presentation / Other}}
**Project lead**: {{NAME, CALLSIGN}}
**Faculty advisor**: {{NAME, CALLSIGN}}
**Club license trustee**: {{NAME, CALLSIGN}}
**Other contributors**: {{NAMES AND CALLSIGNS}}
**Funder**: {{FUNDER, or "Unfunded / club-internal"}}
**Project period**: {{START to END}}

## Project Goal
{{1 to 3 sentences. What does "done" look like?}}

## Repository Visibility

**This repository is: {{PUBLIC | PRIVATE}}**, decided by {{NAME}} on {{YYYY-MM-DD}}.
**Reason**: {{REASON}}

This template sets no default. Decide deliberately at instantiation and record the decision
above, because the answer changes what may be committed.

| Choose **public** when | Choose **private** when |
|---|---|
| The work is meant to be shared: club website source, station how-to guides, outreach material, open-source tools | The repo holds unpublished research data, an in-progress grant application, or draft material the club is not ready to stand behind |
| Other clubs or HamSCI could reuse it | It must hold the keys, tokens, or host details a deploy or development setup needs |
| It is a build log or design the club wants to publish | Member contact information beyond a callsign is unavoidable in the work |

**Never commit, at any visibility:**
- Student records, grades, rosters tied to student IDs, or anything else covered by FERPA
- Member home addresses, phone numbers, personal email addresses, or dates of birth
- **Personal credentials**: anyone's university login, personal account password, or personal
  API key. A person's credential is theirs, and it opens doors well beyond this project.
- Photographs of identifiable people without their permission

**Never commit to a public repository:**
- Credentials, keys, tokens, or access information of any kind
- Building access details, alarm codes, or rooftop and tower access procedures

**A private repository may hold the access information a project needs to deploy and
develop**, where that has been carefully and deliberately decided. Deploy keys, service
tokens, host names and paths, and a `.env` for a staging environment are legitimate contents
of a private orchestrator repository, and pretending otherwise pushes them somewhere worse.

Carefully and deliberately means:

- **The project lead and a W3USR faculty advisor decide together, in advance.** A member does
  not add a credential on their own judgement mid-task.
- **The credential belongs to the project.** A deploy key or service account scoped to one
  target, never a person's own login.
- **Scope it to what the deploy needs** and no further. A key that can push to one host beats
  one that can administer the account.
- **Record what is in there**, in the repository, so the next person can find every credential
  when it is time to rotate them.
- **Rotate on turnover.** Members graduate. Rotate when someone with access leaves the
  project, and on any suspicion of exposure.
- **The repository stays private until you rotate.** Git history keeps a committed secret
  after the file is deleted, so this repository cannot simply be flipped to public later:
  rotate everything first, then flip.

Callsigns and names are public information in the FCC ULS database, so publishing a callsign
is fine. Aggregating a member's callsign with their address, schedule, or dorm is not.

## Repository Structure

This project starts from the W3USR `ai_project_template` scaffold. Add or remove top-level
directories to match the project. The scaffold expects:

```
{{REPO_NAME}}/
|-- CLAUDE.md
|-- README.md
|-- LICENSE                       <- replace with the project's own; see README
|-- NOTICE                        <- copyright and attribution
|-- .gitignore
|-- .gitmodules                   <- present only if you add submodules
|-- .claude/
|   |-- settings.json
|   |-- commands/commit.md        <- /commit workflow
|   `-- rules/
|       |-- ai-governance.md          <- always applies
|       |-- web-development.md        <- delete if no web work
|       |-- latex-writing.md          <- delete if no LaTeX
|       `-- python-code.md            <- delete if no Python
|-- ai/
|   `-- ai_usage_log.md           <- mandatory AI session log
|-- docs/
|   |-- ONBOARDING.md             <- read this first
|   `-- ai_policy_agreement/      <- sign before using AI tools
`-- {{PROJECT-SPECIFIC FOLDERS}}  <- e.g. src/, station/, web/, outreach/, logs/, hardware/
```

## Submodules (optional)

If the project includes a submodule (an Overleaf document, the club website repo, a separate
code repo):

1. Make changes and commit **inside** the submodule first.
2. Then commit the updated submodule pointer in this repo.
3. Push the submodule **before** pushing this repo. A parent pushed ahead of its submodule
   works on your laptop and breaks for everyone who clones it.
4. Use the `[AI-assisted]` prefix on commits whose content was produced with AI assistance.
5. Ask the project lead before pushing to any remote.

The `/commit` workflow auto-detects submodules via `git submodule status`.

## AI Governance

All AI-assisted work on this project must comply with `.claude/rules/ai-governance.md`.

**Before any of it: sign the Generative AI Use Agreement in `docs/ai_policy_agreement/`.**
Members who have not signed it do not run AI-assisted work on this project.

One thing is non-negotiable: **every substantive AI session is logged in
`ai/ai_usage_log.md` before the work is committed.** Use the `/commit` command, which does the
logging and committing in the right order.

{{If this project has constraints of its own that AI work must respect, write them into a
rule file under `.claude/rules/` and name it here.}}

## Getting Help

- Club questions, station access, on-air activity: {{ADVISOR OR TRUSTEE NAME, CALLSIGN, CONTACT}}
- This repository: {{PROJECT LEAD NAME, CALLSIGN}}
- Club meeting time and place: {{WHEN AND WHERE}}
