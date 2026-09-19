# ARCOps, Amateur Radio Club Operations (repository `w3usr/ARCOps`)

A project of the **University of Scranton Amateur Radio Club (W3USR)**.

New to this club's repositories? Read [`docs/ONBOARDING.md`](docs/ONBOARDING.md) first.

## Project Overview

**ARCOps** (Amateur Radio Club Operations) is operations software for amateur radio clubs (see `docs/NAME.md`). The name is spelled out wherever it is first met: the advisor's rule for every acronym. W3USR's
installation is served at `ops.w3usr.org`. The club runs contests and operating events and currently coordinates them by hand; this
application is intended to carry that work. **Functional requirements are drafted and awaiting
adoption**: [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) holds numbered requirements (FR-1
onward), all open questions answered, adoption pending. The technology stack is proposed in
[`docs/TECHNICAL_REQUIREMENTS.md`](docs/TECHNICAL_REQUIREMENTS.md) (TR-1 onward) and awaits
the advisor's decisions in its section 10; do not scaffold it before those are recorded.

**Project type**: Software build (web application)
**Project lead**: {{TBD: NAME, CALLSIGN}}
**Faculty advisor**: Nathaniel A. Frissell, W2NAF
**Club license trustee**: {{TBD: NAME, CALLSIGN}}
**Other contributors**: {{TBD}}
**Funder**: {{TBD: unfunded / club-internal unless an award is named here}}
**Project period**: 2026-09-12 to {{TBD}}

## Project Goal

Give W3USR one place to plan an operating event, see who is on the air, and keep the club's
operational record. "Done" for v1 is defined in `docs/REQUIREMENTS.md` §1.4, which is
currently `{{TBD}}`.

## Repository Visibility

**This repository is: PUBLIC**, decided by Nathaniel A. Frissell (W2NAF) on 2026-09-12.
**Reason**: The application is released as free software under GPL-3.0-or-later so that other
clubs can reuse it, and so that students can point at their work.

Because this repository is public, the rules below are absolute.

**Never commit, at any visibility:**
- Student records, grades, rosters tied to student IDs, or anything else covered by FERPA
- Member home addresses, phone numbers, personal email addresses, or dates of birth
- **Personal credentials**: anyone's university login, personal account password, or personal
  API key
- Photographs of identifiable people without their permission

**Never commit here, because this repository is public:**
- Credentials, keys, tokens, or access information of any kind
- Server host names, IP addresses, file paths on the server, or deploy configuration
- Building access details, alarm codes, or rooftop and tower access procedures

**Where deploy configuration lives instead.** The club's private orchestration repository,
`w3usr/w3usr.org-PRIVATE`, owns server provisioning, DNS, TLS, and any credential the deploy
needs. It carries this repository as a submodule. Nothing in that direction ever flows back
into this one. If a task here seems to need a host name or a key, it belongs in the private
repo; say so rather than inventing a workaround.

Callsigns and names are public information in the FCC ULS database, so publishing a callsign
is fine. Aggregating a member's callsign with their address, schedule, or dorm is not.

## Repository Structure

```
ARCOps/
|-- CLAUDE.md
|-- README.md
|-- LICENSE                       <- GNU GPL v3
|-- NOTICE                        <- copyright, trademark, and attribution
|-- .gitignore
|-- .claude/
|   |-- settings.json
|   |-- commands/commit.md        <- /commit workflow
|   `-- rules/
|       |-- ai-governance.md          <- always applies
|       |-- web-development.md
|       `-- python-code.md
|-- ai/
|   `-- ai_usage_log.md           <- mandatory AI session log
|-- config/                       <- generic club defaults: club.example.yaml, assets/, agreements/ (TR-40)
|-- docs/
|   |-- NAME.md                   <- why it is called ARCOps; the attribution rule
|   |-- REQUIREMENTS.md           <- functional requirements (draft, FR-numbered)
|   |-- TECHNICAL_REQUIREMENTS.md <- proposed stack and technical decisions (draft, TR-numbered)
|   |-- INTERFACE.md              <- how a page reads: words, controls, destructive actions
|   |-- ONBOARDING.md             <- read this first
|   `-- ai_policy_agreement/      <- sign before using AI tools
`-- web/                          <- served at ops.w3usr.org; currently a holding page
```

The application was scaffolded on 2026-09-13 on the advisor's instruction ("build and deploy the
best you can"), against the decided stack in `docs/TECHNICAL_REQUIREMENTS.md`. Layout: `config/`
(settings, urls, generic club defaults), `apps/{ops,accounts,credentials,events,comms}/` each with
models, services, views, and tests, `templates/`, `static/`.

**Before committing, run `tools/check.sh`**: lint, format, the three repository guards, the
migration check, the 244 application tests and the accessibility sweep. It is everything CI runs
and takes about two minutes, because both suites fan out across cores (`pytest-xdist`) and run at
the same time as each other. `tools/check.sh quick` skips the browser and takes about twenty
seconds. While iterating on one page, `pytest tools/a11y -k sysadmin` checks a single role in
about ninety seconds instead of all eight.

Anything that changes a page follows [`docs/INTERFACE.md`](docs/INTERFACE.md): plain nouns for
headings, nothing from inside the program on a page, one solid button per form, the three tiers
of destructive action, and American English throughout.

## Deployment

The server serves `web/` from a checkout of this repository's `main` branch. A push to `main`
goes live only when someone runs the deployment from the private orchestration repo, so
**`main` should always be in a state that is safe to serve**.

`python-code.md` applies: Python is the proposed language (TR-1). Delete it only if the
advisor's decision lands elsewhere.

## AI Governance

All AI-assisted work on this project must comply with `.claude/rules/ai-governance.md`.

**Before any of it: sign the Generative AI Use Agreement in `docs/ai_policy_agreement/`.**
Members who have not signed it do not run AI-assisted work on this project.

One thing is non-negotiable: **every substantive AI session is logged in
`ai/ai_usage_log.md` before the work is committed.** Use the `/commit` command, which does the
logging and committing in the right order.

Because this repository is public, its AI usage log is public too. Write entries that are
accurate and that you are content to have read by the University, by a funder, and by the
wider amateur radio community.

## Getting Help

- Club questions, station access, on-air activity: {{TBD: ADVISOR OR TRUSTEE, CALLSIGN, CONTACT}}
- This repository: {{TBD: PROJECT LEAD, CALLSIGN}}
- Club meeting time and place: {{TBD}}
- General club contact: w3usr@scranton.edu
