# W3USR Repository Onboarding

Welcome to the University of Scranton Amateur Radio Club's project repositories.

This page is for club members who are new to these repositories, whether or not you have used
git or AI tools before. It takes about fifteen minutes. Read it once; you will not need it
again.

---

## First: sign the AI use agreement

**You sign the Generative AI Use Agreement before you use Claude or any other generative AI
tool on a club project.** This is a prerequisite, not paperwork to catch up on later. Access
to these tools comes through the HamSCI project, and the signed agreement is the condition of
that access.

The form is in [`ai_policy_agreement/`](ai_policy_agreement/), as both PDF and Word:
**HamSCI Project Research Group, Generative AI Use Agreement**, updated 15 January 2026.

Read the form. In summary, you are certifying that:

- You have read and will comply with the **University of Scranton AI Policy**, including its
  requirements for ethical use, transparency, privacy protection, and mission alignment with
  Jesuit values.
- Per **NSF and NASA** requirements: you will disclose AI use including tool name, version,
  and date and time; you understand generative AI creates risks of fabrication, falsification,
  and plagiarism; **you are responsible for the accuracy and authenticity of all research
  content, including AI-generated material**; and you will not upload ITAR/EAR-restricted or
  other confidential or protected material to publicly accessible AI systems.
- You understand that **material you upload to these systems can potentially be exposed to
  the public.**
- You will follow **HamSCI group practice**: document and cite all AI use in NASA format,
  upload only data you have permission to upload, verify every output, and ask Dr. Frissell
  when you are uncertain.

Print it, sign it, date it, and return it to a W3USR faculty advisor.

The rest of this page assumes that is done.

---

## What you are looking at

This repository holds a club project: software, a document, station notes, website source, a
grant application, or some mix. Its `CLAUDE.md` file describes the specific project. Read that
next.

The repository also carries a set of rules in `.claude/rules/`. Claude Code reads those
automatically when you work here. You should read them too, because you are the one who is
responsible for the result.

| File | Read it when |
|---|---|
| `.claude/rules/ai-governance.md` | Before your first AI-assisted session. Always applies. |
| `.claude/rules/web-development.md` | Working on the website or any web page |
| `.claude/rules/latex-writing.md` | Writing a paper, poster, or report in LaTeX |
| `.claude/rules/python-code.md` | Writing Python |

Some projects add rule files of their own beyond the ones above. Where a project does, its
`CLAUDE.md` says so, and you read those too.

---

## The two things that matter most

### 1. Every substantive AI session gets logged before you commit

The club keeps `ai/ai_usage_log.md` as an honest record of what AI did on this project. This
is required by University of Scranton policy, by the HamSCI Generative AI Use Agreement, and
by the funders behind some of our work. It also protects you: a documented, reviewed AI
contribution is defensible, and an undocumented one is not.

You do not have to write the entry by hand. Run `/commit` in Claude Code and it will draft the
entry, show it to you for confirmation, append it, and then commit.

"Substantive" means AI produced or reshaped something that ends up in the repository. Asking
Claude what a git command does needs no entry.

### 2. Some things never get committed

Whatever the repository's visibility:

- Student records of any kind: grades, rosters tied to student IDs, advising notes, anything
  under FERPA
- Member home addresses, phone numbers, personal email addresses, dates of birth
- Credentials, **unless this project's `CLAUDE.md` says this private repository deliberately
  holds them.** Some club repositories do: an orchestrator repo needs the keys and host
  details that make a deploy work. That is decided in advance by the project lead and a
  faculty advisor and written down. It is never a call you make mid-task. A personal login,
  yours or anyone's university account, is never committed either way.
- Building access details, alarm codes, tower or rooftop access procedures
- Photographs of identifiable people without their permission
- Fabricated records of any kind

Callsigns and names are public in the FCC database and are fine to publish. Combining a
member's callsign with their address or daily schedule is not.

**If you commit a secret by accident, say so immediately.** Do not try to quietly fix it with
a force-push. The credential is already exposed and needs to be rotated, and someone needs to
know. Tell the project lead or the advisor the same day. Nobody is in trouble for reporting
it; the only real mistake is the silent one.

---

## Your first fifteen minutes

Sign and return the AI use agreement first, if you have not already. Then:

```bash
# 1. Clone the project (ask the project lead for the URL)
git clone <repo-url>
cd <repo-name>

# 2. If the project uses submodules, fetch them too
git submodule update --init --recursive

# 3. Read the project description and the rules
cat CLAUDE.md
ls .claude/rules/

# 4. Start Claude Code in the project directory
claude
```

Claude Code picks up `CLAUDE.md` and `.claude/rules/` automatically. You do not need to paste
them into a prompt.

---

## The working loop

1. **Pull before you start.** `git pull` and, if there are submodules,
   `git submodule update --recursive`. More than one member may be working in here.
2. **Do the work**, with or without AI help.
3. **Review what AI produced.** Actually read it. Run the code. Check the numbers against the
   source. Verify facts about the club with a human. You are putting your name on this.
4. **Run `/commit`.** It logs the AI session, then commits.
5. **Ask before pushing.** Confirm with the project lead until you have been told you do not
   need to.

---

## Working with AI honestly

The point of the log is not paperwork. It is that the club's credibility, with the University,
with funders like ARDC, and with the wider amateur community, depends on our outputs being
what we say they are.

A few habits that keep that true:

- **Verify before you publish.** AI will produce a confident, specific, wrong answer about
  regulations, about our club's history, and about what a paper said. Check it against the
  actual source: the issuing body for a rule, a club officer for club facts, the paper itself
  for what a paper said.
- **Say what AI did.** Understating it is the failure mode that damages people. Overstating it
  costs nothing.
- **Never let AI make something up to fill a gap.** An obvious `{{TBD}}` in a draft is a
  useful signal. An invented date on the club website is a problem someone discovers later, in
  public.
- **Club work is not coursework.** If any of this will also be submitted for a grade, that
  course's AI policy governs that submission and may be stricter. Ask the instructor first.

---

## Git commands you will actually use

```bash
git status                  # what have I changed?
git diff                    # show me the changes
git pull                    # get everyone else's work
git log --oneline -10       # recent history
git checkout -- <file>      # throw away my changes to one file
```

Things to ask before doing: `git push`, `git reset --hard`, `git push --force`, deleting a
branch, changing repository visibility. None of these are forbidden; they are just hard or
impossible to undo, so they get a second person.

If git has you stuck, ask Claude to explain what the error means before running anything it
suggests. Understanding beats copy-pasting, especially here.

---

## Who to ask

| Question | Ask |
|---|---|
| This repository, the code, the document | The project lead named in `CLAUDE.md` |
| Station access, club equipment, using the club callsign | The trustee or faculty advisor |
| "Are we allowed to do this?" | The trustee or faculty advisor, before you do it |
| AI policy, disclosure, whether something needs logging | The faculty advisor |
| The AI use agreement: getting a copy, returning a signed one | A W3USR faculty advisor |
| "I think I committed something I shouldn't have" | The project lead and the advisor, immediately |

Asking early is always cheaper than fixing later. Nobody expects you to know this already.

73, and welcome aboard.
