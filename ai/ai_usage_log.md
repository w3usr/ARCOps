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
- **Git Hash**: 644db55

## [2026-09-12 23:04 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Turn the faculty advisor's dictated first-pass description of the
  application into the functional requirements document: 101 numbered requirements (FR-1 to
  FR-101) with v1 priorities, a permission matrix, a guardian model for minors, a credential
  mechanism generalising license, station access, and IT access, slot viability rules including
  a named control operator and a chaperone check, and 15 open questions for the advisor.
- **Sections/Files Affected**: `docs/REQUIREMENTS.md` (rewritten from the shell; all sections),
  `CLAUDE.md` (project overview and tree entry now say requirements are drafted, awaiting
  adoption)
- **Nature of Contribution**: Draft and analysis. The requirements' content is the advisor's
  dictation, quoted verbatim where it decides something; additions are marked "(added)" in the
  text and tabulated with reasons in section 9. Contest rules (PA QSO Party, School Club
  Roundup) and the contest calendar's field list were verified against their sources on
  2026-09-12; the Part 97 section numbers cited in FR-63 were not and are flagged for
  verification.
- **Human Review Status**: Pending review; the document's own status is "Draft; not adopted".
- **Git Hash**: 3a7ca46

## [2026-09-12 23:25 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Apply NAF's correction that members must be able to change their own
  callsign (vanity grant, new sequential call on upgrade). The first draft had made the
  callsign sysadmin-only alongside the FCC-sourced license fields.
- **Sections/Files Affected**: `docs/REQUIREMENTS.md`: FR-8 callsign row; FR-14 (lookup also
  fires on callsign entry or change); new FR-102 (change flow: immediate FCC lookup, name-
  mismatch flag, unverified state until ULS knows the call, callsign history, audit, override
  re-confirmation); permission matrix row; section 9 "Decisions taken after the first draft"
  with NAF's words verbatim.
- **Nature of Contribution**: Edit. The decision is NAF's; the change-flow detail in FR-102 is
  the assistant's and is marked as such.
- **Human Review Status**: Partially reviewed. NAF stated the decision and saw the summary of
  the applied changes; FR-102's full text is pending his read.
- **Git Hash**: baafc34

## [2026-09-13 02:58 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Record the outbound-mail decision in the requirements without host
  details, and adjust FR-81 to what v1 can deliver under it.
- **Sections/Files Affected**: `docs/REQUIREMENTS.md` §6 (outbound mail: decided, Postfix on
  the origin, application submits to localhost; reason and consequences), FR-81 (list mail
  carries unsubscribe link and List-Unsubscribe header; in-application bounce record demoted
  to Should for v1, bounces readable in the club mailbox)
- **Nature of Contribution**: Edit. The decision is the faculty advisor's.
- **Human Review Status**: Pending review
- **Git Hash**: b1acfe6

## [2026-09-13 03:05 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Apply NAF's direction that the system stay useful if email breaks: no
  action may require an email to be delivered, invitations show the issuer a link and text to
  send by hand, and the sign-in page carries a "Forgot username or password?" link. Also
  restate FR-7 (sysadmin temporary password) as explicitly one-time use with unused-expiry,
  per his second instruction.
- **Sections/Files Affected**: `docs/REQUIREMENTS.md`: new §3.8.1 "Email independence" with
  NAF's words verbatim and FR-103 to FR-108 (flow-by-flow email-free paths table; invitation
  link and text shown to issuer; email delivery on/off mode with an outbox; recipient export
  for announcements; forgot-username-or-password link with non-enumerating response and
  email-off fallback; in-application notifications); FR-7 sharpened; FR-82 promoted to Must;
  FR-72, FR-93, FR-3, §1.4, §2.6, §2.7 amended; §9 decision record.
- **Nature of Contribution**: Edit and draft. The principle and the two examples are NAF's;
  the table of email-free paths, the delivery-mode design (drop, never queue, while off),
  and the anti-enumeration behaviour of FR-107 are the assistant's and are marked as such.
- **Human Review Status**: Partially reviewed. NAF saw the summary of the applied changes;
  the full text of FR-103 to FR-108 is pending his read, and the drop-versus-queue choice in
  FR-105 was flagged for his decision.
- **Git Hash**: 6d9f1e2

## [2026-09-13 03:17 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Apply NAF's correction that sign-up openings are per role: mentor and
  observer roles open to anyone available at once; operator roles to students first and to
  everyone later, if at all.
- **Sections/Files Affected**: `docs/REQUIREMENTS.md`: §1.4 definition of done (the "students
  first, then everyone" sentence now distinguishes roles), FR-54 (opening schedule stated as
  belonging to a role, with NAF's case as the example), §9 decision record (his words
  verbatim). FR-53 unchanged; it already modelled eligibility per role.
- **Nature of Contribution**: Edit. The decision is NAF's.
- **Human Review Status**: Partially reviewed. NAF stated the rule and saw the summary of the
  applied wording.
- **Git Hash**: 4b542b1

## [2026-09-13 03:36 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Apply three of NAF's decisions to the requirements: (1) an explicit,
  recorded publish action for events and a rule that a published event can return to draft
  only before the first sign-up; (2) the minors model: responsible adults are designated per
  slot by the guardian and take no place in the slot, the roster shows them and the guardians
  with contact details behind the minor's name, more than one guardian may be linked, no
  dates of birth are stored, and conversion at 18 is manual by a faculty advisor; (3)
  University SSO is not pursued in this version, option left open.
- **Sections/Files Affected**: `docs/REQUIREMENTS.md`: FR-44 (publish/unpublish); §2.4,
  permission matrix, FR-8 rows, FR-64 (rewritten), FR-67 (minor detail panel), new FR-109
  (manual conversion), §4.1, §4.2, §4.3, Q7 and Q14 wording; §2.6 and Q9 (SSO); §9 table row
  and decision record with NAF's words verbatim.
- **Nature of Contribution**: Edit and draft. The decisions are NAF's, quoted in place. The
  assistant's choices: responsible-adult records may belong to non-members and are retained
  one year after the event; the minor detail panel is visible to captains, officers, and
  sysadmins, matching FR-67's existing contact-detail rule (flagged to NAF as widenable).
- **Human Review Status**: Partially reviewed. NAF stated the rules and saw the summary of
  the applied text; the full wording of FR-64, FR-67, and FR-109 is pending his read.
- **Git Hash**: 1d9ab7e

## [2026-09-13 03:40 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Apply two of NAF's decisions: (1) on rosters, members see only a
  short name (first name and callsign, or first name and last initial), with full names and
  contact details reserved to captains, officers, and sysadmins; (2) Student profiles carry
  anticipated graduation (semester: Spring, Summer, or Fall, Spring default; plus year) and
  student level (undergraduate or graduate).
- **Sections/Files Affected**: `docs/REQUIREMENTS.md`: FR-67 (short name defined, applied by
  reference to FR-63, FR-72, FR-13), FR-65 and FR-72 wording; FR-8 (two Student-only fields),
  FR-87 (fields on the member roster plus a past-graduation filter); §9 decision record with
  NAF's words verbatim, including the semester refinement.
- **Nature of Contribution**: Edit. The decisions are NAF's. The assistant's additions: the
  short-name rule extended beyond the roster to every place a member sees another member; the
  graduation fields made member-editable since they grant no privilege; the past-graduation
  filter on FR-87 as the retention hook.
- **Human Review Status**: Partially reviewed. NAF stated the rules and saw the summaries of
  the applied text.
- **Git Hash**: 0b858f9

## [2026-09-13 03:55 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Apply NAF's direction that registration is callsign-first: an immediate
  FCC ULS lookup fills the name and license fields, the ULS name is read-only to the member
  while the preferred name is theirs, and an applicant with no callsign enters a name by hand.
  Then, on the name-mismatch check (FR-16): the member confirms the ULS name replacing their
  entered name themselves, with no sysadmin involved.
- **Sections/Files Affected**: `docs/REQUIREMENTS.md`: §2.7 step 3, FR-4 (rewritten), FR-8
  name rows, FR-15 (ULS name override added), FR-16 (repurposed to the add-or-change-callsign
  case; member self-confirmation; no sysadmin), FR-102 wording; §9 decision record with NAF's
  three statements verbatim.
- **Nature of Contribution**: Edit and draft. The decisions are NAF's. The assistant's
  additions: the unverified state when the lookup fails or the call is too new for ULS data;
  the reviewing officer catching a wrong-person callsign via the ULS name; the "beyond a middle
  name or initial" threshold in FR-16. The assistant proposed a sysadmin second look on FR-16
  and NAF removed it.
- **Human Review Status**: Partially reviewed. NAF read the FR-16 text closely enough to
  correct it twice; FR-4's full text is pending his read.
- **Git Hash**: a977acc

## [2026-09-13 04:01 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Apply NAF's correction that the background check behind the Community
  Member agreement is administered by University HR and its type is not known to the club, so
  the requirements must not name a specific check.
- **Sections/Files Affected**: `docs/REQUIREMENTS.md`: §3.3 (source-documents paragraph), FR-27
  (checklist now records HR's confirmation only, never the kind or result of the check), §9
  decision record with NAF's words verbatim.
- **Nature of Contribution**: Edit. The specific name had been quoted from clause 1 of the
  2024-08-19 agreement text; the assistant pointed this out (H4) and noted it as a candidate
  correction for the agreement's next revision. The agreement document itself was not changed.
- **Human Review Status**: Partially reviewed. NAF stated the correction and saw the applied
  wording summarised.
- **Git Hash**: 00867e5

## [2026-09-13 04:11 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Apply four of NAF's decisions on access agreements: (1) the system does
  not store R numbers (FR-24 confirmed; Q5 resolved); (2) approvals expire by default on the
  next 1 September, with August approvals carried to the September after, so the club renews
  together and no one gets a term of weeks; (3) 30-day notices ask members to sign in and
  re-sign every agreement in one visit; (4) station and IT agreements are signed in a single
  workflow, and minors do not sign them, nor guardians on their behalf.
- **Sections/Files Affected**: `docs/REQUIREMENTS.md`: FR-24 and Q5; FR-25 (default expiry
  rule with worked examples); FR-28 (single notice per member, summary to approvers, bulk
  re-sign queue); FR-22 (rewritten: one workflow, per-document records, minors excluded, with
  the consequences for FR-61 and FR-33 stated); FR-10, §2.4, and the permission matrix
  (guardians sign only for themselves); §9 decision record with NAF's five statements verbatim.
- **Nature of Contribution**: Edit. The decisions are NAF's. The assistant's additions: the
  worked examples in FR-25; the single summary to approvers and the bulk queue in FR-28, which
  follow from a shared expiry date; the stated consequence that a minor never holds station or
  IT access.
- **Human Review Status**: Partially reviewed. NAF read and corrected the expiry rule once;
  the rest was stated by him and summarised back.
- **Git Hash**: 29ee97c
