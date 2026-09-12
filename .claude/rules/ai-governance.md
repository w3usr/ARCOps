# AI Governance and Policy Compliance

Binding on all AI-assisted work in W3USR club repositories.

Club work carries the University of Scranton's name. Careless AI use here risks the club's
standing with the University, with grant funders, and with the amateur radio community.
Treat what follows as hard constraints.

## Prerequisite: The Signed Agreement

Every club member signs the **HamSCI Project Research Group Generative AI Use Agreement**
before using a generative AI tool on a club project. The form lives in
`docs/ai_policy_agreement/` and is the condition of access to the tools.

A member who has not signed it does not run AI-assisted work on this project. Signed forms
go to a W3USR faculty advisor. If you are not sure whether yours is on file, ask before you
start.

## Applicable Policies (Always)

### 1. University of Scranton AI Policy (September 2025)
- Maintain transparency about AI use in all club outputs
- Human oversight and review of all AI-generated content is required before it is published,
  submitted, printed, or sent
- Do not use AI to misrepresent authorship or intellectual contribution
- Ethical use aligned with University academic integrity standards, and mission alignment
  with Jesuit values

Full policy: https://www.scranton.edu/Governance/artificial-intelligence-policy_september-2025.pdf

**Club work is not coursework.** If any part of a club project will also be submitted for
academic credit (an independent study, a capstone, a course project, a thesis), the
instructor's AI policy for that course governs that submission, and it may be stricter than
this file. Ask the instructor before reusing club work in a graded artifact. Resolve the
conflict in favor of the stricter rule.

### 2. HamSCI Generative AI Use Agreement (January 2026)
- Log the AI tool name, version, and date/time for every substantive session
- Verify all AI-generated output before incorporating it into a club artifact
- Do not submit confidential, ITAR/EAR-controlled, or proprietary material to AI tools

### 3. NASA Guidance on Generative AI in Funded Research
Applies to club work connected to HamSCI or to any other NASA-funded effort.
- Disclose AI-assisted content in deliverables to NASA-funded projects
- Maintain human authorship and accountability for scientific claims
- Do not submit ITAR/EAR-controlled, confidential, or unpublished mission data to AI tools
- Verify factual claims against authoritative sources before publication

### 4. NSF Guidance on Responsible Use of Generative AI in Funded Research
Applies to club work connected to an NSF-funded effort.
- Disclose AI use in NSF deliverables, proposals, and publications as required
- Maintain human authorship and intellectual responsibility for results
- Do not use AI to generate or substantially shape proposal review content unless explicitly
  authorized
- Do not submit confidential or unpublished data to AI tools

### 5. Grant Funders (ARDC and others)
{{If this project is supported by a grant, name the funder and the grant number here, and
record any AI-use terms the award carries. Amateur Radio Digital Communications (ARDC) is the
most common source for club equipment and project grants; university sources include
{{STUDENT GOVERNMENT / DEPARTMENT / OFFICE}}.

Whatever the source: acknowledge the funder by name and grant number in every deliverable,
report honestly on what was accomplished, and disclose AI-assisted content per the award's
terms. If the award says nothing about AI, disclose anyway.

If the project is unfunded, replace this section with: "This project has no external funder
beyond the standing institutional policies above."}}

### 6. Student Privacy (FERPA)
Never send student records to an AI tool or commit them to a repository: grades, evaluations,
advising notes, disciplinary matters, disability accommodations, or any roster that ties a
student ID to a name. A club membership list with names and callsigns is ordinary club
business; a list that pulls in student IDs, addresses, or class schedules is not.

### 7. Project-Specific Constraints
{{A project may carry obligations this file does not cover. Where it does, write them into
their own rule file under `.claude/rules/` and name it in the project's `CLAUDE.md`. Delete
this section if there are none.}}

## AI Usage Logging Requirements

**Every substantive AI session must be logged in `ai/ai_usage_log.md` before committing.**

"Substantive" means the AI produced or reshaped content that lands in the repository. Asking
Claude to explain what a git command does needs no entry. Having it draft a page of the club
website, write a logging script, or analyze propagation data does.

Each entry must include:

| Field | Requirement |
|---|---|
| **Date/Time** | From the system clock via `date`. Never estimated. |
| **Tool** | Name and exact version, e.g. "Claude (Anthropic), claude-opus-5" |
| **Session Purpose** | What the session set out to accomplish |
| **Sections/Files Affected** | The specific files or documents touched |
| **Nature of Contribution** | Draft, edit, analysis, code generation, research, scaffolding |
| **Human Review Status** | Reviewed and verified / Partially reviewed / Pending review |
| **Git Hash** | Added after committing |

Work done inside a submodule is logged in that submodule's own log where one exists.
The internal log is the source of truth for what AI did; any public disclosure summarizes it
truthfully.

## Disclosing AI Use in Club Outputs

The log is internal. Some outputs also need a visible disclosure:

| Output | Disclosure |
|---|---|
| Journal or conference paper, poster, or abstract | Name the tool and version and state what it did, in the methods or an equivalent section. AGU and most publishers require this. |
| Grant application or report to a funder | Per the funder's terms. Disclose even when the terms are silent. |
| Club website page, newsletter, or social post substantially drafted by AI | A short line is enough: "Drafted with AI assistance and reviewed by {{NAME, CALLSIGN}}." |
| Code released publicly | A note in the README that the repository contains AI-assisted work, with the log as the record. |
| Anything submitted for academic credit | Per that course's policy. See section 1. |

Keep disclosures short and accurate. Understating the scope of AI use is the failure to avoid.

## AI Is Not an Author

- AI tools cannot be listed as authors on a paper, poster, or report. They cannot take
  responsibility for the work or hold copyright.
- A human club member's name goes on every artifact, and that person is accountable for it.

## What AI Should Never Do Here

- Fabricate or hallucinate citations, references, data, quotations, or records of any kind
- Invent club history, member accomplishments, event attendance, or grant outcomes
- Present AI output as purely human work
- Receive student records, unpublished data, ITAR/EAR-controlled material, credentials, or
  proprietary information
- Skip the AI usage log before committing AI-assisted changes
- Force-push or hard-reset without explicit instruction from the project lead
