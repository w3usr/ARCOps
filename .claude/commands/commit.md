# /commit: AI-Assisted Commit Workflow (W3USR)

Run this any time you finish a substantive AI-assisted work session in a W3USR project.

It logs the AI session first, then commits, in that order. The order is the point: the log is
the club's record of what AI did, and a commit without one is a gap in that record.

Handles flat repos, single-submodule repos (e.g. Overleaf only), and multi-submodule repos.
Submodules are auto-detected from `git submodule status`.

## Steps

### 1. Get the current timestamp
```bash
date
```
Use this exact output. Never estimate the date or time.

### 2. Identify all changes
```bash
git status
git submodule foreach 'git status'
git diff --stat
git submodule foreach 'git diff --stat'
```
No output from `git submodule foreach` means the repo has no submodules; proceed without them.

### 3. Check what is about to be staged
Before drafting anything, look at the changed files for material that must never be committed
(see `CLAUDE.md` and `.claude/rules/ai-governance.md`):

- credentials, API keys, or `.env` files with real values, unless `CLAUDE.md` records a
  deliberate decision that this private repository holds deploy configuration
- a personal login or personal API key, which is never committed at any visibility
- student records, rosters tied to student IDs, member addresses or phone numbers
- building access details, alarm codes, tower or rooftop access procedures
- photographs of identifiable people without permission

If any appear, stop and raise it with the user before committing.

### 4. Ask the user for the session purpose
Draft a one- or two-sentence purpose for the log. Show it to the user and ask them to confirm
or correct it.

### 5. Draft the AI usage log entry
Use the **actual running model ID** in the Tool field (e.g. `claude-opus-5`), never a
placeholder.

```
## [YYYY-MM-DD HH:MM TZ]
- **Tool**: Claude (Anthropic), <actual-model-id>
- **Session Purpose**: [user's description]
- **Sections/Files Affected**: [changed files and sections]
- **Nature of Contribution**: [Draft / Edit / Analysis / Code generation / Research / etc.]
- **Human Review Status**: [Reviewed and verified / Partially reviewed / Pending review]
- **Git Hash**: [filled in after committing]
```

Set **Human Review Status** honestly. "Pending review" is a legitimate and useful value, and
it is far better than claiming a review that did not happen.

Present the draft. Wait for confirmation or corrections.

### 6. Append the entry to `ai/ai_usage_log.md`

### 7. Commit in submodules FIRST (if any have changes)
```bash
git -C <submodule-path> add <files>
git -C <submodule-path> commit -m "[AI-assisted] <description>"
```
Skip this step when there are no submodules or none have changes.

### 8. Commit in the main repo
Stage `ai/ai_usage_log.md`, any updated submodule pointers, and the other changed files:
```bash
git add ai/ai_usage_log.md <other-files-and-submodule-pointers>
git commit -m "[AI-assisted] <description>"
```

### 9. Fill in the git hash(es)
```bash
git log --oneline -1
```
Update the entry's **Git Hash** field with the main-repo hash and any submodule hashes
(e.g. `main=abc1234, overleaf=def5678`).

If that needs a follow-up commit, use a plain message without the `[AI-assisted]` prefix, such
as `Update AI usage log with git hashes`.

### 10. Ask before pushing
Never push without explicit instruction from the user.

When pushing a repo with submodules, **push the submodule before the parent**. A parent that
reaches GitHub ahead of its submodule looks correct on the machine that pushed it and breaks
for everyone who clones. Verify first:
```bash
git -C <submodule-path> branch -r --contains HEAD   # empty output = local only; push it first
```

## Notes

- The `[AI-assisted]` prefix goes on commits whose content was produced or substantially
  shaped with AI. A purely human edit (the user fixes a typo, rewords a sentence) does not
  carry it.
- Submodules get their own `[AI-assisted]` commits where their content is AI-assisted,
  separately from the parent's pointer-bump commit.
- Use `git add <specific-files>` rather than `git add -A` or `git add .`, so build output,
  credentials, and large binaries are not staged by accident.
- Reference a tracking issue where one exists (`refs #N`, or `closes #N` when declaring the
  work finished is yours to declare).
