# ops.w3usr.org: Requirements

**Status: SHELL DOCUMENT. Nothing here is decided.**

This file is a skeleton created to be filled in during a dedicated requirements session. Every
`{{TBD}}` marks a decision that has not been made. Headings and prompting questions were
drafted with AI assistance; the answers are the club's to write.

Do not build against this document until its status line says the requirements are adopted,
with a date and the name of the person who adopted them.

| | |
|---|---|
| **Document status** | Shell; not adopted |
| **Last revised** | 2026-09-12 |
| **Owner** | {{PROJECT LEAD, CALLSIGN}} |
| **Adopted by** | {{NAME, CALLSIGN}} on {{YYYY-MM-DD}} |

---

## 1. Purpose and scope

The repository description reads: *"Web App to Support Radio Club Contests and Operations."*
That is the only fixed statement of purpose so far. Everything below expands on it.

**1.1 Problem statement.** {{TBD: What does the club do today, by hand or on paper, that this
application replaces? Name the specific pain, not the feature.}}

**1.2 In scope.** {{TBD}}

**1.3 Explicitly out of scope.** {{TBD: Naming what this is not keeps the build finite. A
candidate for this list is anything the club already has a good tool for.}}

**1.4 Definition of done for v1.** {{TBD: One paragraph describing the first release that is
worth putting in front of the club.}}

---

## 2. Users and roles

Who uses this, and what may each of them do? A first cut at the roles the application will
likely need to distinguish, to be confirmed or replaced:

| Role | Who they are | What they can do |
|---|---|---|
| Visitor | Not logged in, general public | {{TBD}} |
| Club member | A W3USR member | {{TBD}} |
| Operator | A member running a station during an event | {{TBD}} |
| Event lead | Runs a contest or operating event | {{TBD}} |
| Administrator | Trustee, advisor, or officer | {{TBD}} |

**2.1 Authentication.** {{TBD: How do members sign in? University SSO, a club-managed account,
GitHub, or something else? This decision has the longest reach of any in this document, because
it constrains hosting, privacy obligations, and how much account plumbing the club maintains.}}

**2.2 Licensing and callsign verification.** {{TBD: Does the application need to know whether a
user holds a license, and of what class? If so, is that self-reported or checked against FCC
ULS?}}

---

## 3. Functional requirements

Each requirement gets an ID (`FR-1`, `FR-2`, ...) so that later sessions, issues, and commits
can cite it. Numbering is permanent: retire a requirement by marking it retired, never by
reusing its number.

### 3.1 Contest and operating events

- **FR-1** {{TBD}}
- {{TBD: Candidate areas to consider, none of them decided: scheduling operators into time
  slots; showing who is on which band and mode right now; tracking a score as an event runs;
  recording which stations and antennas are in use; a post-event summary.}}

### 3.2 Logging

- **FR-n** {{TBD}}
- {{TBD: Open questions. Does this application log QSOs itself, or does it read logs produced
  by software the club already runs? If it ingests, what formats: ADIF, Cabrillo, N1MM+
  broadcast? Is there a single club log or one per operator per event? What is the
  relationship to LoTW, eQSL, QRZ, and Club Log?}}

### 3.3 Station and equipment

- **FR-n** {{TBD}}
- {{TBD: An equipment inventory, antenna configurations, band availability, and known faults
  are candidates. Note that station access procedures are private club information and must
  not be published.}}

### 3.4 Public-facing content

- **FR-n** {{TBD}}
- {{TBD: The club's public web presence is the University page at
  www.scranton.edu/academics/cas/physics-engineering/w3usr/, and w3usr.org redirects
  there. Decide what, if anything, ops.w3usr.org shows to a visitor who is not logged in, and
  how that avoids duplicating the University page.}}

### 3.5 Integrations

- {{TBD: Candidates to accept or reject, with the cost of each: FCC ULS callsign lookup, QRZ
  XML, Club Log, LoTW, HamSCI data products, WSPRNet, PSKReporter, solar and space-weather
  indices, a calendar feed.}}

---

## 4. Data

**4.1 What the application stores.** {{TBD: Enumerate it. This list is what a privacy review
and a backup plan are both written against.}}

**4.2 Personal data.** The application will hold information about identifiable students. That
makes the following binding rather than optional:

- Callsigns and names are public in the FCC ULS database and may be shown. Aggregating a
  member's callsign with their address, schedule, or residence is not acceptable.
- Student records covered by FERPA (grades, student ID numbers, rosters tied to student IDs,
  advising or disciplinary information) must never enter this system.
- {{TBD: What is the minimum personal data the application actually needs? Default to
  collecting nothing that a named requirement does not force.}}
- {{TBD: Retention. When does a graduated member's data get deleted or anonymized?}}

**4.3 Storage.** {{TBD: Flat files, SQLite, or PostgreSQL, and why. The club runs a 1 GB
Nanode; pick accordingly.}}

**4.4 Backup and recovery.** {{TBD: What is backed up, how often, to where, and who has
verified a restore? A backup nobody has restored from is a hypothesis.}}

---

## 5. Non-functional requirements

**5.1 Hosting.** Deployed to `ops.w3usr.org`, a Linode Nanode (1 vCPU, 1 GB RAM, 25 GB disk,
US-Newark), fronted by Cloudflare. Provisioning and deployment are orchestrated from the club's
private `w3usr.org-PRIVATE` repository.

**5.2 Resource budget.** 1 GB of RAM is the binding constraint on the stack choice. A design
that assumes a container orchestrator, a JVM, or several database servers does not fit.

**5.3 Accessibility.** WCAG 2.1 AA. This is a university club's public face, so accessibility is
a requirement and not a polish step. See `.claude/rules/web-development.md`.

**5.4 Availability.** {{TBD: What happens if the site is down during a contest? If the answer is
"the contest stops," the design needs an offline path.}}

**5.5 Security.** {{TBD: Threat model. At minimum: no secrets in this public repository, all
visitor input validated and escaped, dependencies kept current.}}

**5.6 Continuity.** Club members graduate. {{TBD: What must be true for a student who has never
seen this code to run it, deploy it, and fix it? That answer belongs in the onboarding
document, and it constrains how exotic the stack may be.}}

---

## 6. Technology

**Undecided, deliberately.** The stack follows from sections 3 through 5 and gets chosen once
those are filled in. Record the decision here with its reasoning when it is made.

- **Language and framework**: {{TBD}}
- **Datastore**: {{TBD}}
- **Front end**: {{TBD}}
- **Build and deploy**: {{TBD}}
- **Testing**: {{TBD}}

Constraints already known, which any candidate stack must satisfy:

- Runs within a 1 GB Nanode alongside nginx.
- Maintainable by undergraduate club members with turnover every few years.
- GPL-3.0 compatible.

---

## 7. Licensing and governance

- This repository is licensed **GPL-3.0-or-later**. Dependencies must be compatible with it.
- AI-assisted work here follows `.claude/rules/ai-governance.md`: every substantive session is
  logged in `ai/ai_usage_log.md` before the work is committed.
- The University of Scranton's name, seal, and logos are the University's marks. The W3USR club
  logo in `web/assets/` comes from the club's own asset library. Using a University mark needs
  the advisor's sign-off.

---

## 8. Open questions for the requirements session

Carried forward so the session has an agenda:

1. Authentication: University SSO, club-managed accounts, or a third party? (§2.1)
2. Does this application log QSOs, or consume logs from existing software? (§3.2)
3. What is the single most valuable thing it could do in v1? (§1.4)
4. What is the relationship between ops.w3usr.org and the University club page? (§3.4)
5. Who maintains this after the current students graduate? (§5.6)
6. {{TBD: add to this list as questions surface.}}

---

<sub>Skeleton drafted by Claude (Anthropic), `claude-opus-5`, under W2NAF's direction. It
contains no decided requirements; every substantive answer is the club's to supply. Scientific
and engineering decisions are the authors'.</sub>
