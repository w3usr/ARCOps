---
paths:
  - "**/*.py"
  - "pyproject.toml"
  - "requirements.txt"
  - "requirements*.txt"
---

# Python Code Rules
*Delete this file if the project includes no Python.*

Common club uses: log parsing and ADIF handling, propagation and WSPR/PSKReporter analysis,
satellite pass prediction, rig or rotator control, dashboards, data plotting.

## Code Standards
- Follow the existing structure; introduce a new abstraction only with a reason you can state
- Keep `requirements.txt` or `pyproject.toml` current when adding a dependency
- Default to environment variables and a gitignored `.env` for credentials and API keys.
  Where a private repository deliberately holds deploy configuration, `CLAUDE.md` records
  that decision. A personal login is never committed, at any visibility.
- Write code a club member who joins next semester can read. Name things plainly, and comment
  the parts that are non-obvious rather than the parts that are obvious.

## Side Effects
- Default to dry-run. Make an action that reaches the outside world an explicit opt-in, never
  the default behavior of a script someone runs to see what it does.
- Guard destructive or irreversible actions (uploading data, posting to a service, writing
  over a record) behind a confirmation.
- Where a project's hardware or external systems impose constraints of their own, write them
  into a project rule file under `.claude/rules/` and follow it.

## Data Handling
- Copy a real data file before operating on it; never edit the original in place
- Keep test fixtures clearly named as fixtures so no one mistakes them for real records
- Bulk data stays out of git; fetch it from its archive or regenerate it from a committed
  script, and record where it came from

## Commit Workflow
- Code in a submodule: commit in the submodule first, then bump the pointer here, then push
  the submodule before the parent
- `[AI-assisted]` prefix on AI-assisted commits
- Reference the tracking issue (`refs #N`, or `closes #N` when finishing the work is yours to
  declare)
- Ask the project lead before pushing to any remote

## Open Source
- Keep commit history clean and suitable for public visibility from the first commit
- Document design decisions in comments or `docs/`, not only in commit messages
- Apply the project's license consistently, with a `LICENSE` at the repository root
