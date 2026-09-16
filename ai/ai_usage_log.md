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

## [2026-09-13 04:18 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Apply three of NAF's decisions on agreement states: (1) drop the
  *active* state; agreements are signed, approved, declined, expired, or revoked; (2) the
  slot-viability check uses *approved*; (3) a Community Member agreement can be approved only
  when a @scranton.edu address is on file, since the University issues one only after HR's
  process, and the approver may add the address at approval.
- **Sections/Files Affected**: `docs/REQUIREMENTS.md`: FR-26 (rewritten), FR-27 (checklist
  replaced by the scranton.edu precondition), FR-61 (approved agreements), and the removal of
  "active"/"activated" from FR-29, FR-31, FR-33, FR-34, FR-76, FR-84, FR-92, and the FR-103
  table; §9 table row for the withdrawn active state struck; §9 decision record with NAF's
  three statements verbatim.
- **Nature of Contribution**: Edit. The decisions are NAF's. The assistant's additions: the
  note that an expired approval is *expired* so "approved" already means current; the choice
  that an approver-entered scranton.edu address is vouched for and not mail-verified, flagged
  to NAF.
- **Human Review Status**: Partially reviewed. NAF read FR-26 and FR-27 closely enough to
  correct each; the propagated wording elsewhere is pending his read.
- **Git Hash**: 3e3f20a

## [2026-09-13 04:27 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Make the *locked* event state explicitly optional in FR-44, per NAF, and
  define how *completed* is reached.
- **Sections/Files Affected**: `docs/REQUIREMENTS.md`: FR-44 (locking optional; published may
  go straight to completed; completed set by a captain or officer, or automatically after the
  last slot ends); §9 decision record with NAF's words verbatim.
- **Nature of Contribution**: Edit. The decision is NAF's; the automatic completion after the
  last slot is the assistant's addition, marked as such.
- **Human Review Status**: Partially reviewed. NAF stated the rule and saw the applied wording
  summarised.
- **Git Hash**: 0d53c02

## [2026-09-13 04:30 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Generalise FR-47 from setup and breakdown slots to a configurable list
  of non-operating slot kinds (training, equipment pre-check, post-event analysis, and
  others), per NAF.
- **Sections/Files Affected**: `docs/REQUIREMENTS.md`: FR-47 (kinds configurable; placeable
  before, after, or between operating periods; generator still offers setup and breakdown by
  default; each kind has its own viability rule); §9 decision record with NAF's words verbatim.
- **Nature of Contribution**: Edit. The generalisation is NAF's; the per-kind viability rule
  and the placement in gaps between periods are the assistant's additions.
- **Human Review Status**: Partially reviewed. NAF stated the rule and saw the applied wording
  summarised.
- **Git Hash**: 83fec12

## [2026-09-13 04:37 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Apply two of NAF's decisions: (1) events support multiple positions and
  multiple locations (Q12 resolved), with a viability rule per location; (2) sign-ups carry a
  member's note to the captains.
- **Sections/Files Affected**: `docs/REQUIREMENTS.md`: FR-51 (Should to Must; location →
  position → slot model; per-location viability; residence-address visibility), FR-36, FR-61,
  FR-65, FR-72, FR-77 (propagation); new FR-110 (sign-up note to captains); Q12 struck as
  resolved; §9 table row and decision record with NAF's words verbatim.
- **Nature of Contribution**: Edit and draft. The decisions are NAF's. The assistant's
  additions: the per-location viability rule, without which a field site could never be
  viable; the private-residence address rule; the roster marker for notes and their inclusion
  in the captains' at-risk digest when added inside 48 hours.
- **Human Review Status**: Partially reviewed. NAF stated both rules and saw the applied text
  summarised; the full wording of FR-51 and FR-110 is pending his read.
- **Git Hash**: d20d6aa

## [2026-09-13 04:41 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Apply NAF's decision that a member may change role within a slot
  (operator, mentor, observer) when eligible, and his follow-up that a change which would
  break the slot's viability warns the member beforehand so they can decide to stay.
- **Sections/Files Affected**: `docs/REQUIREMENTS.md`: new FR-111 (role change; eligibility
  and capacity checks; cutoff behaviour; no-gap guarantee; pre-change viability warning with
  confirm-or-stay; captain notified if they proceed), the same warning extended to
  cancellation (FR-56); §9 decision record with NAF's two statements verbatim.
- **Nature of Contribution**: Edit and draft. The decisions are NAF's. The assistant's
  additions: the cutoff behaviour and the no-gap guarantee; the extension of the pre-change
  warning to cancellation, which follows from NAF's answer.
- **Human Review Status**: Partially reviewed. NAF stated the rule, answered the assistant's
  question on the viability case, and saw the applied text summarised.
- **Git Hash**: fbc9be9

## [2026-09-13 04:54 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Apply three of NAF's decisions on notifications and attendance:
  (1) browser notifications mirroring email, on by default per device, subject to the
  browser's own permission; (2) notification preferences on the profile page by category
  and channel, with a named set that always goes out, cancellations first among them;
  (3) one-tap check-in on arrival, available from 30 minutes before a slot.
- **Sections/Files Affected**: `docs/REQUIREMENTS.md`: FR-71 (rewritten as preferences with
  a mandatory set), new FR-112 (browser notifications), FR-83 (narrowed to SMS), new FR-113
  (check-in) and FR-114 (check-in nudge, Could), FR-86 (actual attendance), FR-8 row, §1.3,
  FR-103 table; §9 decision record with NAF's five statements verbatim.
- **Nature of Contribution**: Edit and draft. The decisions are NAF's. The assistant's
  additions: the mandatory categories beyond cancellations (moves by others, account security,
  agreement decisions and expiry); the *reminders off* roster state; the iOS home-screen
  constraint on push; the roster's checked-in state, late-arrival notice to captains, the
  minor's check-in recording the responsible adult present, and the feed into the
  participation report.
- **Human Review Status**: Partially reviewed. NAF corrected the push default and added the
  ease requirement for check-in; the remaining text is summarised to him and pending his read.
- **Git Hash**: d4274e9

## [2026-09-13 05:00 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Apply NAF's direction that the know-before-you-go text and other long
  texts are HTML edited in a WYSIWYG editor, with good heading structure encouraged.
- **Sections/Files Affected**: `docs/REQUIREMENTS.md`: new FR-115 (rich text: the fields it
  covers, the editor's feature set, structure encouragement, heading-level offset for one H1
  per page, sanitisation, HTML email with plain-text alternative); FR-77 (seeded heading
  outline); §9 decision record with NAF's words verbatim.
- **Nature of Contribution**: Edit and draft. The decision is NAF's. The assistant's additions:
  the sanitisation rule, the heading-level offset, the plain-text alternative for email, and
  the seeded outline.
- **Human Review Status**: Partially reviewed. NAF stated the rule and saw the applied text
  summarised.
- **Git Hash**: 26fb55f

## [2026-09-13 05:03 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Apply NAF's requirement that the system be accessible, especially to
  visually impaired people using screen readers, by promoting §5.3 from a one-line statement
  to numbered, testable requirements.
- **Sections/Files Affected**: `docs/REQUIREMENTS.md`: §5.3 (NAF's words verbatim), new FR-116
  (WCAG 2.1 AA with screen-reader-specific commitments: semantic structure, the roster as a
  real table with a live region, keyboard order, an accessible editor, tagged PDFs, plain HTML
  mail) and FR-117 (automated checks in the build pipeline and a screen-reader walk of the core
  flows as a release gate); §9 decision record.
- **Nature of Contribution**: Edit and draft. The requirement is NAF's; the itemised
  commitments and the release gate are the assistant's reading of what it demands of this
  application.
- **Human Review Status**: Partially reviewed. NAF stated the requirement and saw the applied
  text summarised.
- **Git Hash**: e3da986

## [2026-09-13 05:07 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Apply NAF's requirement that a sysadmin can delete a user account.
- **Sections/Files Affected**: `docs/REQUIREMENTS.md`: new FR-118 (deletion distinct from No
  access and from member-requested closure; future sign-ups cancelled with captains told;
  personal data removed; past rosters and participation anonymised; agreements kept for the
  retention period then purged; audit log intact; last-sysadmin guard; guardian ordering
  rule); permission matrix row; §9 decision record with NAF's words verbatim.
- **Nature of Contribution**: Edit and draft. The requirement is NAF's; the anonymise-and-
  retain behaviour and the two guards are the assistant's.
- **Human Review Status**: Partially reviewed. NAF stated the requirement and saw the applied
  text summarised.
- **Git Hash**: a9801df

## [2026-09-13 05:10 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Review section 8 (open questions) against the day's decisions: record
  the four resolved (Q5, Q7, Q9, Q12), reword Q2 and Q6 to the current state, and add Q16 to
  Q19 from choices the assistant made while applying decisions and flagged at the time.
- **Sections/Files Affected**: `docs/REQUIREMENTS.md` §8 (header, Q2, Q6, new Q16–Q19).
- **Nature of Contribution**: Edit. The new questions and their recommendations are the
  assistant's; the decisions they ask for are NAF's to make.
- **Human Review Status**: Pending review; NAF requested the review and has answered the
  questions on the answer sheet in the private repository, to be applied next.
- **Git Hash**: e459084

## [2026-09-13 05:28 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Apply NAF's answers to all nineteen section 8 questions, from the answer
  sheet in the private repository, and turn section 8 into a table of decisions.
- **Sections/Files Affected**: `docs/REQUIREMENTS.md`: status table; §1.3 (adopted); §2.4 and
  FR-10 (minors sign in read-only); §2.7, FR-4, FR-5, permission matrix, FR-76, FR-92, FR-103
  table (no application review; completing the form admits); FR-13 (Could to Must, directory);
  FR-21 (Faculty/Staff template); FR-40 (WA7BNM letter and retrieval prototype authorised);
  FR-67 (slot-mates see a minor's responsible adults); FR-72 (advisor named after captains);
  FR-98 (visitors: nothing); §2.4 (University minors policy met by the responsible-adult rule);
  §4.3 (3 years after expiry for agreements, pending the University's period); §8 rewritten as
  a decisions table with follow-ups; §9 record.
- **Nature of Contribution**: Edit. Every decision is NAF's, quoted where it changed the draft.
  The assistant's additions: the notice to inviter and officers that replaces the review step;
  the read-only scope for minors and the guardian setting the minor's password; the 3-year
  agreement retention default; the test set for the retrieval prototype drawn from the FRC
  proposal's Appendix B.
- **Human Review Status**: Partially reviewed. NAF wrote the answers; the applied wording is
  summarised to him and pending his read.
- **Git Hash**: af21c70

## [2026-09-13 12:00 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Draft the technical requirements (TR-1 to TR-39) against the functional
  requirements and the server as found; put the eight open technical choices to NAF one at a
  time and apply his answers; verify the Part 97 citations in FR-63.
- **Sections/Files Affected**: `docs/TECHNICAL_REQUIREMENTS.md` (new: constraints, architecture,
  platform, security, data, operations, quality, layout, dev environment, decisions table,
  verification table); `docs/REQUIREMENTS.md` (§6 decided stack, §4.4 storage and backup, §2.6
  second factor to Must, FR-14 mechanism, FR-97 amended, FR-63 citations verified, §8 follow-ups,
  §9 record); `README.md` and `CLAUDE.md` (status and tree).
- **Nature of Contribution**: Draft, analysis, and edit. The recommendations are the assistant's;
  the eight decisions are NAF's, three of which amended the draft (FCC bulk files as the primary
  license source; TOTP and passkeys both built, optional by default, requirable per level, with
  passwordless passkey sign-in; healthchecks.io). Versions, licences, PyPI availability, FCC file
  sizes, server facts, and the CFR text were verified on 2026-09-13 and are tabulated in §11 and
  at FR-63. Memory figures in TR-30 are estimates and marked so.
- **Human Review Status**: Partially reviewed. NAF answered each decision; the document's full
  text is pending his read, and both documents say adoption is pending.
- **Git Hash**: d4b5616

## [2026-09-13 12:24 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Make the open-source release work for any club out of the box, per NAF:
  generic, swappable club defaults in the public repository, and an overlay mechanism by which
  a club's own assets replace them at deploy.
- **Sections/Files Affected**: `config/` (new: `README.md`, `club.example.yaml` with every
  configuration key and neutral values, `assets/club-logo.svg` placeholder mark,
  `agreements/*.example.html` marked as illustrations to replace); `docs/TECHNICAL_REQUIREMENTS.md`
  (new TR-40 generic defaults and CI club-neutrality grep, TR-41 overlay; TR-32, TR-38, layout,
  §10 updated); `README.md` and `CLAUDE.md` trees.
- **Nature of Contribution**: Draft and code generation. The principle is NAF's, quoted in TR-40;
  the overlay mechanism, the example agreement texts (written as illustrations, not reviewed by
  any institution, and so labelled), the placeholder SVG, and the CI grep are the assistant's.
- **Human Review Status**: Pending review.
- **Git Hash**: 6ca9cd3

## [2026-09-13 12:47 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: First build of the application on the decided stack, done autonomously
  while NAF was away on his instruction ("make a plan to build and deploy the best you can
  with what we have without me there"). Scaffold Django per TR-1 to TR-8; models for accounts,
  credentials, events, comms, ops; services for viability (FR-61 to FR-64), slot generation
  (FR-46 to FR-48), expiry (FR-25), calendar date lines (FR-38); club_import, seed_demo,
  bootstrap_sysadmin; server-rendered templates with a roster, check-in, agreements signing and
  approval, invitations with copyable link and text (FR-104), computer-password view (FR-33);
  allauth with TOTP and passkeys optional; PWA manifest and service worker; tests; CI.
- **Sections/Files Affected**: `manage.py`, `config/` (settings base/dev/test/prod, urls, wsgi,
  env.example), `apps/ops`, `apps/accounts`, `apps/credentials`, `apps/events`, `apps/comms`
  (models, migrations, services, views, urls, admin, management commands, tests), `templates/`,
  `static/`, `requirements*.txt`, `pyproject.toml`, `.github/workflows/ci.yml`,
  `tools/check_club_neutral.sh`, `.gitignore`, `README.md`, `CLAUDE.md`.
- **Nature of Contribution**: Code generation and draft, unreviewed by a human at commit time.
  26 tests pass locally (Python 3.13, Django 5.2.17); ruff clean under the policy in
  pyproject.toml (E501, DJ008, DJ012 ignored for now); every page answers 200 to a signed-in
  demo sysadmin and the anonymous paths behave; the club-neutrality grep passes. Not yet built:
  the ULS bulk import job, notifications and reminders jobs, WeasyPrint PDFs, TinyMCE, the
  member directory, reports, waitlists, guardian sign-up flows, the API beyond two endpoints.
- **Human Review Status**: Pending review. NAF was not present; he reviews and tests after.
- **Git Hash**: bcd8f5c

## [2026-09-13 13:01 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Review and audit of the first build at NAF's request, with fixes: no
  sign-up option anywhere (his correction: "the front page should not even show an option to
  create an account"); allauth pages re-laid over the application's own layout with the
  passkey script blocks kept; admin sign-in routed through allauth so second-factor rules
  apply; API docs behind login; a gated email backend so nothing can send while delivery is
  off; the account gate middleware moved after the messages middleware (it posted messages
  before that middleware ran) and made to expire temporary passwords; admin forms bound to the
  custom user model (the stock ones point at Django's); eligibility and openings enforced on
  sign-up (FR-53, FR-54); minors' invitations held for the guardian flow; a rich-text filter
  that sanitises and shifts heading levels so pages keep one H1 (FR-115, FR-116); demo seed
  refuses to run beside real accounts.
- **Sections/Files Affected**: templates/account/{login,password_reset,signup_closed}.html,
  templates/allauth/layouts/base.html, templates/base.html, templates/accounts/invitation_minor.html,
  templates/credentials/agreements.html, templates/events/detail.html; apps/comms/backends.py,
  apps/events/services/eligibility.py, apps/ops/templatetags/richtext.py (new); config/settings/base.py,
  config/urls.py, apps/ops/{api,context_processors}.py, apps/accounts/{middleware,admin,views}.py,
  apps/events/views.py, apps/ops/management/commands/seed_demo.py; 18 new tests (44 total).
- **Nature of Contribution**: Code generation and analysis. Every fix is pinned by a test.
- **Human Review Status**: Pending review.
- **Git Hash**: 7569b81

## [2026-09-13 13:04 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Fix the first live sign-in failure found by an end-to-end probe through
  Cloudflare: allauth's rate limiter could not determine the client IP behind the unix socket
  and refused every login POST with 403. The adapter now reads nginx's X-Real-IP. Also silence
  Django's two deployment checks that nginx satisfies, with the reason recorded.
- **Sections/Files Affected**: apps/accounts/adapter.py, apps/accounts/tests/test_flows.py (a test
  that reproduces the empty REMOTE_ADDR), config/settings/prod.py.
- **Nature of Contribution**: Code generation; diagnosed from the server's journal.
- **Human Review Status**: Pending review.
- **Git Hash**: 7d92c0a

## [2026-09-13 14:19 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Name the product ARCOps at NAF's decision, after a namespace check he
  asked for (ClubOps rejected as a live commercial product in the same category; ARCOps has one
  sound-alike, arcOS, and no ham-radio product of its name). Rename the repository to
  w3usr/arcops; add the footer attribution "Powered by ARCOps, free software from W3USR" on
  every installation; name the schedule feature "Sked".
- **Sections/Files Affected**: docs/NAME.md (new: decision, verbatim reasoning, collision table,
  rules), apps/ops/branding.py (new: the one file allowed to name W3USR), apps/ops/context_processors.py,
  config/settings/base.py (product context processor; TOTP issuer), templates/base.html and
  templates/allauth/layouts/base.html (footer, titles, "My Sked"), static/manifest.webmanifest,
  tools/check_club_neutral.sh (branding.py exempted, with the reason), README.md, CLAUDE.md,
  docs/REQUIREMENTS.md and docs/TECHNICAL_REQUIREMENTS.md (titles, clone URL, tree root).
  GitHub repository renamed from ops.w3usr.org to arcops (redirect confirmed).
- **Nature of Contribution**: Research (the collision check), draft, and edit. The name and the
  Sked/hostname reasoning are NAF's, quoted in NAME.md; the attribution mechanism is the assistant's.
- **Human Review Status**: Partially reviewed. NAF chose the name and the rules in conversation;
  the text of NAME.md is pending his read.
- **Git Hash**: 1bae1e1

## [2026-09-13 15:34 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Design run after the advisor's first look at the deployed application:
  a sidebar shell (collapsible rail, drawer on small screens), a split sign-in page with the
  club's mark, a footer in the club's colour, the club colour taken from configuration with an
  AA contrast check; and four fixes he asked for while testing (password-change landing page,
  guardian field shown only for a minor, two email addresses of equal standing with delivery
  switches, page titles).
- **Sections/Files Affected**: templates/base.html, templates/allauth/layouts/base.html,
  templates/account/login.html, templates/accounts/{invitations,profile}.html, all page titles;
  static/css/app.css (rewritten), static/js/app.js, static/js/nav-state.js (new);
  apps/ops/templatetags/nav.py (new), apps/ops/config.py (accent_colour, contrast check,
  institution_email_domain), apps/ops/context_processors.py; apps/accounts/{models,admin,
  views,adapter,middleware}.py and migration 0002_email_delivery_switches;
  apps/comms/services.py (recipient_addresses); config/club.example.yaml; tests
  apps/ops/tests/test_shell.py and apps/accounts/tests/test_profile_and_invites.py (new).
- **Nature of Contribution**: Design (options put to the advisor, his choices recorded in the
  private repository's notes/2026-09-13_design.md), code generation, tests. The colour was
  sampled from the club's own artwork.
- **Human Review Status**: Pending review. The advisor chose the layout, colour, and sign-in
  design from mock-ups; he has not yet seen the rendered result.
- **Git Hash**: 337b960

## [2026-09-13 16:07 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Management audit and the pages it called for, so no officer or sysadmin
  needs the Django admin: a member directory and per-member management page (privilege fields,
  club position, one-time temporary password, access removal and restoration), invitation revoke
  and reissue, event creation and a manage page (details, operating periods, locations and
  positions, captains, slot generation with per-role seats, duplicate, cancel), captain controls
  on the roster (close, reopen, cancel a slot, remove a sign-up), and the sign-in address placed
  into a contact slot on acceptance with a backfill for existing accounts.
- **Sections/Files Affected**: apps/accounts/{views_members.py (new), views.py, services.py,
  urls.py}, migration 0003_place_sign_in_email, apps/events/{views_manage.py (new),
  services/manage.py (new), urls.py}, apps/ops/templatetags/{nav.py, dicts.py (new)},
  config/urls.py, templates/base.html, templates/accounts/{members,member_detail,invitations}.html,
  templates/events/{form,manage,list,detail}.html, static/css/app.css, tests
  apps/accounts/tests/test_members.py and apps/events/tests/test_manage.py (new).
- **Nature of Contribution**: Analysis (the audit, recorded in the private repository's
  notes/2026-09-13_management-audit.md), code generation, tests.
- **Human Review Status**: Pending review.
- **Git Hash**: 4b19387

## [2026-09-13 16:41 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Roster rebuilt to the advisor's direction and the recommendations he
  accepted: day-grouped rows with local and UTC times, a grid with one column per position,
  status phrased as what a slot needs, a slot page that also opens as a dialog with every edit
  a captain makes (seats, control operator, sign-up on behalf, close, cancel, remove), and bulk
  actions from checkboxes (multi-slot sign-up with per-slot answers; captain close, reopen,
  cancel). Event dates and a draft banner on the event page; member summary in place of the
  health card; print stylesheet.
- **Sections/Files Affected**: apps/events/services/roster.py (new), apps/events/views_slots.py
  (new), apps/events/views.py (event_detail), apps/events/urls.py, templates/events/detail.html
  (rewritten), templates/events/slot.html and _slot_body.html (new), static/css/app.css,
  static/js/app.js, tests apps/events/tests/test_roster.py (new) and test_manage.py.
- **Nature of Contribution**: Design (recommendations put to the advisor first, recorded in the
  private repository's notes/2026-09-13_design.md), code generation, tests.
- **Human Review Status**: Pending review; the advisor chose the direction, has not yet seen the
  rendered result.
- **Git Hash**: 682f094

## [2026-09-14 18:47 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: First finding of the acceptance walk-through (private tracker #23): times
  on Events, Home, and My Sked were UTC-only with no zone, and the Events table lost its headings
  on a phone. One `{% when %}` tag now renders every span in the event's zone with UTC beneath,
  following the member's roster preference; the Events list is cards.
- **Sections/Files Affected**: apps/events/templatetags/times.py (new), templates/events/
  {list,my_schedule}.html, templates/ops/dashboard.html, static/css/app.css, test in
  apps/events/tests/test_roster.py.
- **Nature of Contribution**: Code generation, test. The finding is the advisor's.
- **Human Review Status**: Pending review; the advisor verifies on the live site.
- **Git Hash**: c052d39

## [2026-09-15 15:41 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Requirement text for entry links and the Provisional access level, from the
  advisor's two use cases and the decisions he made in discussion on 2026-09-15: FR-1 rewritten;
  FR-119 to FR-124 added; §2.1, §2.7, FR-5, FR-36, FR-53, FR-61, FR-62, FR-67 amended; change log.
  No code.
- **Sections/Files Affected**: docs/REQUIREMENTS.md.
- **Nature of Contribution**: Draft, with the advisor's words quoted at each decision.
- **Human Review Status**: Pending review; the advisor asked for the text before the code.
- **Git Hash**: 767da16

## [2026-09-15 15:56 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Build the entry-links plan the advisor approved: class and community
  links with expiry, cap, pause, revoke, and who-joined; the join flow with the seven-day
  verification and the officer's waiver; the Provisional access level with its review (Home card,
  member page, officer email) and its restricted roster view; role defaults from configuration
  (Mentor needs a license); the event's class as a preferred class with a warning below it;
  license letters after names; check-in hours per course with CSV; the public mentor-needs page.
- **Sections/Files Affected**: apps/accounts/{entry.py, views_entry.py (new), models.py,
  views_members.py, middleware.py, urls.py}, migration 0004_entry_links; apps/events/{models.py,
  urls.py, views_slots.py, services/{roster,viability,eligibility}.py, services/{mentors,hours}.py
  (new)}, migration 0002_entry_links; apps/credentials/views.py (guards); apps/ops/views.py;
  config/urls.py, config/club.example.yaml; templates/accounts/{entry_links, join, join_closed,
  join_sent, verify_result, mentors, hours}.html (new) and {members, member_detail, invitations,
  invitation_minor}.html, templates/events/{detail,_slot_body}.html, templates/ops/dashboard.html,
  templates/base.html; docs/REQUIREMENTS.md (FR-122 wording); tests: apps/accounts/tests/
  test_entry_links.py, apps/events/tests/test_preferred_and_hours.py (new), test_flows.py and
  test_viability.py amended for FR-61 and FR-122.
- **Nature of Contribution**: Code generation and tests against the requirement text the advisor
  read; the FR-122 wording change (Mentor: any license class) is the assistant's reconciliation
  of two of his decisions, recorded in the private plan note.
- **Human Review Status**: Pending review; scenarios T23 to T27 of the test plan are his check.
- **Git Hash**: a26a26e

## [2026-09-15 16:41 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: One label fix found by the requirements coverage audit run in the private
  repository: the event page still printed "minimum class" for a field that became the
  *preferred* class on 2026-09-15 (FR-36, FR-61), so a tester following the acceptance plan would
  have seen the stale word and passed it.
- **Sections/Files Affected**: templates/events/detail.html (one string).
- **Nature of Contribution**: Edit.
- **Human Review Status**: Pending review; T12 step 1 of the private test plan is the check.
- **Git Hash**: 9766b46

## [2026-09-15 18:00 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Make CI green before the build resumes: the last three commits failed the
  `ruff format --check` step on 23 files formatted before the check existed. `ruff format .`
  applied; one lambda whose `noqa` comment the formatter moved off its line rewritten as a def.
- **Sections/Files Affected**: 23 files under apps/ (formatting only; no logic change) and
  apps/accounts/tests/test_members.py (helper `mk` as a def).
- **Nature of Contribution**: Edit (mechanical formatting; one three-line rewrite).
- **Human Review Status**: Reviewed by the tools: ruff check and format clean, 83 tests pass.
- **Git Hash**: 7bd2c07

## [2026-09-15 18:31 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Phase 0 of the implementation plan kept in the private repository
  (foundations every notice depends on): the scheduled-job runner with healthchecks.io pings and
  the stale-job watchdog (TR-11, TR-33); message templates editable by a sysadmin and seeded by
  the import (FR-78); notification preferences honoured by the outbox, mandatory categories, the
  roster's "reminders off" marker (FR-71); the My messages page with unread badge and Home
  banner (FR-82, FR-108); the officer outbox, the delivery mode on Home, and audited setting
  changes (FR-105); the sysadmin status page (FR-93). Also found and fixed along the way: the
  invitation email was never composed (emailed_at was never set); it now goes through the
  template system to the invitee, or the guardian for a minor.
- **Sections/Files Affected**: apps/ops/jobs.py (new), apps/ops/management/commands/{selfcheck,
  jobs_stale}.py (new), apps/ops/{views,urls,admin,config}.py, apps/ops/templatetags/{nav,
  richtext}.py; apps/comms/{categories,defaults,context_processors,views}.py (new),
  apps/comms/{services,models}.py, migration 0002; apps/accounts/{views,urls,models,services,
  entry,views_entry}.py; apps/events/services/roster.py; templates/base.html, ops/{dashboard,
  outbox,status,templates,template_edit}.html, comms/my_messages.html, accounts/profile.html,
  events/detail.html; static/css/app.css; config/settings/{base,dev,prod}.py; docs/JOBS.md (new),
  README.md; tests apps/comms/tests/test_messages.py and apps/ops/tests/test_jobs.py (new).
- **Nature of Contribution**: Code generation and tests against the requirement text and the
  technical decisions; the template wording is the first draft for the sysadmin to edit.
- **Human Review Status**: Pending review; scenarios T29 and T30 of the private test plan are
  the check. 98 tests pass; ruff clean.
- **Git Hash**: f7825bf

## [2026-09-15 18:52 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Phase 1 of the implementation plan kept in the private repository (the
  notices): the 24-hour reminder with a one-click confirm link that works signed out and a
  cannot-make-it link into the cancellation flow (FR-72, FR-100); at-risk warnings to the people
  in a slot and a digest to the captains, one per state per 12 hours, carrying late sign-up notes
  (FR-73, FR-110); no-show notices and captain check-in on a member's behalf (FR-113);
  cancellation, removal, and assignment notices, late-cancellation flag, event and slot
  cancellation with a reason, access removal withdrawing future sign-ups (FR-56, FR-58, FR-74,
  FR-91); application-completed, welcome, and agreement submitted / approved / declined notices
  (FR-5, FR-76); browser push with per-device subscriptions and a member switch (FR-112); the
  weekly digest (FR-79). Sixteen new message templates; three new scheduled jobs registered.
- **Sections/Files Affected**: apps/events/services/notify.py (new), apps/events/management/
  commands/{notify_reminders,notify_warnings,digest_weekly}.py (new), apps/events/{models,views,
  urls,views_manage,views_slots}.py, migration events 0005; apps/comms/{defaults,push}.py,
  apps/comms/services.py; apps/accounts/{models,services,views,views_push,urls}.py, migration
  accounts 0005; apps/credentials/{services,views}.py; apps/ops/{jobs,context_processors}.py;
  templates/events/{token_confirmed,token_cannot,token_cancelled,token_invalid}.html (new),
  templates/events/{_slot_body,manage}.html, templates/accounts/profile.html, templates/base.html;
  static/js/push.js (new); config/settings/base.py; docs/JOBS.md; tests apps/events/tests/
  test_notify.py, apps/comms/tests/test_push.py, apps/credentials/tests/test_notices.py (new).
- **Nature of Contribution**: Code generation and tests against the requirement text; the
  template wording is a first draft the sysadmin edits on the Templates page.
- **Human Review Status**: Pending review; scenarios T31 to T34 of the private test plan are
  the check. 112 tests pass; ruff clean.
- **Git Hash**: e5c36d6

## [2026-09-15 20:25 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Phase 2 of the implementation plan kept in the private repository (events
  completeness): lock, unlock, and complete, with automatic completion once the last slot has
  ended and an optional announcement at publish (FR-44); role change within a held slot with the
  viability warning and a captains' notice inside the cutoff (FR-111); operating limits and
  per-day windows on the manage page, "over limit" on the roster and per-day hours on the health
  card (FR-39, FR-48, FR-62, FR-66); an eligibility editor per role with a per-slot override, and
  openings per role with an announcement when they fire (FR-53, FR-54, FR-80); roster CSV
  (FR-85); a problems-only filter and credential badges (FR-65); a waitlist with offers that
  lapse to the next in line (FR-57); a signed per-member calendar feed (FR-59); an officers'
  cross-event health view (FR-68); display-only recurring events (FR-45). Two new jobs.
- **Sections/Files Affected**: apps/events/{models,views,views_manage,views_slots,urls}.py,
  apps/events/views_rules.py (new), apps/events/views_member.py (new), apps/events/services/
  {slots,roster,manage}.py, apps/events/services/{lifecycle,waitlist}.py (new), apps/events/
  management/commands/{events_complete,openings_announce}.py (new), migration events 0004;
  apps/comms/defaults.py (four templates); apps/ops/jobs.py; templates/events/{manage,detail,
  _slot_body,list,my_schedule}.html, templates/events/{confirm_role,waitlist_accept,
  health_overview}.html (new); docs/JOBS.md; tests apps/events/tests/test_phase2.py (new).
- **Nature of Contribution**: Code generation and tests against the requirement text.
- **Human Review Status**: Pending review; scenarios T35 to T37 of the private test plan are
  the check. 120 tests pass; ruff and the neutrality check clean.
- **Git Hash**: 3e1d693

## [2026-09-15 20:48 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Phase 3 of the implementation plan kept in the private repository (the FCC
  ULS sync): the `uls_sync` job streaming the FCC's weekly complete Amateur file or the daily
  transaction file to disk, staging HD, AM, and EN records in a scratch table, keeping the active
  or latest record per callsign, and refreshing every member's license record and ULS-sourced
  name (FR-14, TR-13); name confirmation when a callsign is added or changed and the ULS name
  differs beyond a middle name, with the callsign rejected on refusal (FR-16, FR-102); license
  expiry notices at 90 and 30 days and on expiry, once each, reset on renewal (FR-17); a sysadmin
  license override on the member page with class, status, expiry, name, issuing country, and a
  required reason, shown as an override and untouched by the sync (FR-15, FR-20).
- **Sections/Files Affected**: apps/credentials/uls.py (new), apps/credentials/management/
  commands/{uls_sync,licenses_expiry}.py (new), apps/credentials/{models,services}.py, migration
  credentials 0002; apps/accounts/{models,services,views,views_entry,views_members,urls}.py,
  migration accounts 0006; apps/comms/defaults.py (two templates); apps/ops/jobs.py;
  templates/accounts/{profile,member_detail}.html; docs/JOBS.md; tests
  apps/credentials/tests/test_uls.py (new, with a synthetic ULS archive).
- **Nature of Contribution**: Code generation and tests against the requirement text and the
  FCC's public-access field definitions (HD, AM, EN record layouts).
- **Human Review Status**: Pending review; scenario T38 of the private test plan is the check,
  and the first full import on the server is the memory measurement NAF asked for (D6). 125 tests
  pass; ruff and the neutrality check clean.
- **Git Hash**: a227acb

## [2026-09-15 21:50 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Fix found by the advisor on first use of browser notifications: the
  permission prompt and notifications named the product ("ARCOps" in the static manifest, "Club
  Ops" as the service worker's fallback) instead of the installation. A member of two clubs
  running the software would not be able to tell them apart. The manifest is now rendered from
  the club's configuration with the host in its name, every push title is prefixed with the
  club's short name, and the worker falls back to the origin.
- **Sections/Files Affected**: apps/ops/views.py (manifest view), config/urls.py,
  templates/base.html, static/sw.js (cache v2, origin fallback, icon and tag), apps/comms/push.py,
  static/manifest.webmanifest (deleted); tests apps/ops/tests/test_health_and_import.py and
  apps/comms/tests/test_push.py.
- **Nature of Contribution**: Code generation and tests; the finding is the advisor's.
- **Human Review Status**: Pending review; T34 step 1 of the private test plan is the check.
- **Git Hash**: e4388a0

## [2026-09-15 22:03 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Phase 4 of the implementation plan kept in the private repository
  (credentials and reports): a sysadmin page to set or rotate the shared computer password, with
  the rotation notice to current holders and a summary naming former viewers without access
  (FR-32, FR-34, FR-90); the daily agreement-expiry job with one bundled notice per member at 30
  days and on the day, approver summaries, and expiry of approvals on a superseded version past
  its re-sign date, set by a `--resign-by` option on the import (FR-28, FR-30); approvers revoke
  an approval with a reason and the member is told (FR-29); every signed agreement is rendered by
  WeasyPrint to a tagged PDF (PDF/UA-1) at signing and again at approval, downloadable by the
  signer and the approvers (FR-23); the access rosters report with an expiring-within filter and
  CSV (FR-31, FR-84); the participation report per event and period with first-time participants
  (FR-86); the officers' member roster with the past-graduation filter and a separate, audited
  contact export (FR-87); the agreements page offers re-signing when an approval is about to
  expire and says when a newer version must be re-signed.
- **Sections/Files Affected**: apps/credentials/{models,services,views,urls}.py,
  apps/credentials/views_reports.py (new), apps/credentials/management/commands/
  agreements_expiry.py (new), migration credentials 0003; apps/events/services/participation.py
  (new), apps/events/{views_member,urls}.py; apps/accounts/views_members.py; apps/comms/
  defaults.py (six templates); apps/ops/jobs.py; apps/ops/management/commands/club_import.py;
  config/urls.py; templates/credentials/{agreement_pdf,password_manage,access_rosters}.html
  (new), templates/credentials/{agreements,approvals,password}.html, templates/events/
  participation.html (new), templates/events/detail.html, templates/accounts/roster.html (new),
  templates/accounts/{members,member_detail}.html; requirements.{in,txt} (WeasyPrint and its
  dependencies); docs/JOBS.md; tests apps/credentials/tests/test_phase4.py and
  apps/events/tests/test_participation.py (new).
- **Nature of Contribution**: Code generation and tests against the requirement text and TR-10.
- **Human Review Status**: Pending review; scenarios T39 to T41 of the private test plan are
  the check. 134 tests pass; ruff and the neutrality check clean.
- **Git Hash**: d6ba7f0

## [2026-09-15 22:19 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Phase 5 of the implementation plan kept in the private repository
  (announcements and contest fields): captains announce to an event's participants filtered by
  day, role, slot status, confirmation state, or category, officers to every member, with the
  recipient count before sending; every announcement recorded with its audience and resolved
  recipients and listed for officers (FR-75); each copy carries Reply-To to the sender, the
  captains, and the club address (FR-69), an unsubscribe footer, and the List-Unsubscribe and
  List-Unsubscribe-Post headers with a one-click endpoint that turns off the announcement
  category only (FR-81); "copy for my own mail client" records the announcement as sent outside
  and shows the BCC list and body (FR-106); the WA7BNM contest field set entered by hand on
  Manage, shown on the event page, with the exchange and logging lines added to every reminder
  (FR-37). The calendar import itself stays out (D1).
- **Sections/Files Affected**: apps/comms/announce.py (new), apps/comms/views_announce.py (new),
  apps/comms/{models,services}.py, migration comms 0003; apps/events/contest_fields.py (new),
  apps/events/{views,views_rules,views_manage,urls}.py, apps/events/services/notify.py;
  apps/ops/urls.py; templates/comms/{announce,announce_outside,announcements,unsubscribe}.html
  (new), templates/events/{manage,detail}.html, templates/base.html; tests
  apps/comms/tests/test_announce.py (new).
- **Nature of Contribution**: Code generation and tests against the requirement text.
- **Human Review Status**: Pending review; scenario T42 of the private test plan is the check.
  138 tests pass; ruff and the neutrality check clean.
- **Git Hash**: 5e6100d

## [2026-09-15 22:35 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Phase 6 of the implementation plan (administration, governance, rich
  text): a sysadmin can view the application as a member, read-only and audited (FR-94); club
  settings are edited on one grouped page with every change audited (FR-89); a member can close
  their own account and a sysadmin can delete one, with future sign-ups withdrawn, identifying
  fields removed, past rosters keeping their shape, and signed agreements kept for retention
  (FR-11, FR-118); a daily retention job applies §4.3 with a legal-hold flag (TR-28); a privacy
  notice page linked from every footer, editable in Settings, with a generic default in the
  shipped configuration (FR-101); the TinyMCE editor on event description and know-before-you-go,
  announcements, message templates, and the privacy notice, with a heading-order warning
  (FR-115); a seeded know-before-you-go outline on every new event (FR-77).
- **Sections/Files Affected**: apps/accounts/impersonate.py (new), apps/accounts/{models,
  services,views,views_members,urls}.py, migration accounts 0007; apps/ops/{retention,
  views_settings}.py (new), apps/ops/management/commands/retention_apply.py (new),
  apps/ops/{jobs,urls}.py; apps/comms/{defaults,views,views_announce}.py;
  apps/events/views_manage.py; config/{urls}.py, config/settings/base.py,
  config/club.example.yaml; templates/ops/{settings,privacy,_editor}.html (new),
  templates/{base,accounts/profile,accounts/member_detail,events/form,events/manage,
  comms/announce,ops/template_edit}.html; static/js/richtext-check.js (new);
  requirements.in/.txt (django-tinymce 4.1.0); docs/JOBS.md, docs/TECHNICAL_REQUIREMENTS.md
  (TR-9 as built); tests apps/accounts/tests/test_phase6.py and
  apps/ops/tests/test_settings_and_privacy.py (new).
- **Nature of Contribution**: Code generation and tests against the requirement text.
- **Human Review Status**: Pending review; scenarios T43 to T45 of the private test plan are the
  check, and the privacy notice text awaits the advisor's edit (D4). 147 tests pass; ruff, the
  formatter, and the neutrality check clean.
- **Git Hash**: a590ae8

## [2026-09-15 22:41 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Phase 6 follow-up: the legal-hold flag (TR-28) had no control in the
  interface; it now sits on the sysadmin's member form, audited with the other privilege fields.
- **Sections/Files Affected**: apps/accounts/views_members.py.
- **Nature of Contribution**: Code generation.
- **Human Review Status**: Pending review; T44 step 5 of the private test plan is the check.
  147 tests pass; ruff and the neutrality check clean.
- **Git Hash**: d6884fe

## [2026-09-15 23:04 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Phase 7 of the implementation plan (guardians and minors, REQUIREMENTS
  §2.4): a guardian completes a minor's invitation, creating or linking their own account and
  the minor's read-only one (FR-10); a guardian acts for a linked minor from their own account,
  with every action rendered as the minor and audited in the guardian's name; a minor's own
  sign-in refuses every state change except their password; responsible adults are named per
  slot from a fresh entry, the guardian's saved list, or a member by name, shown to slot-mates
  and in full to captains, and recorded as present at check-in (FR-64, FR-67, FR-113); every
  message to a minor reaches every active guardian (FR-70, verified by test); an approver
  converts the account at 18 with a one-time password and notices to the guardians (FR-109);
  sysadmins link and unlink guardians on the member page.
- **Sections/Files Affected**: apps/accounts/guardian.py (new: middleware, context, act-for
  views, ward password, link/unlink/convert services), apps/accounts/{views,views_members,
  models,urls}.py, apps/accounts/tests/{test_phase7 (new),test_flows}.py; apps/events/
  views_adults.py (new), apps/events/{views,views_slots,urls}.py, apps/events/services/
  eligibility.py; apps/ops/audit.py (guardian attribution); apps/comms/defaults.py (two
  templates); config/settings/base.py, config/club.example.yaml (guardian category);
  templates/accounts/{accept_invitation_guardian,invitation_guardian_signin,ward_password}.html
  (new), templates/accounts/{profile,member_detail}.html, templates/events/{adults (new),
  my_schedule,_slot_body}.html, templates/{base,ops/dashboard}.html.
- **Nature of Contribution**: Code generation and tests against the requirement text.
- **Human Review Status**: Pending review; scenarios T46 to T48 of the private test plan are the
  check. 156 tests pass; ruff, the formatter, and the neutrality check clean.
- **Git Hash**: dbd43e6

## [2026-09-15 23:18 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Phase 7 follow-up, on the advisor's decision ("I'll take the
  recommendation"): a minor need not have an email address (§2.4). The invitee's address is
  optional on the invite form when the invitee is under 18, optional again on the guardian's
  acceptance form, and with none the minor signs in with a plus-address made from the guardian's
  (`parent+kim@…`), flagged sign-in-only so it is never messaged; the guardian sets the minor's
  real address later from Profile; the guardian's own address is refused as the minor's.
- **Sections/Files Affected**: apps/accounts/{models,views,services,guardian,urls}.py, migration
  accounts 0008; apps/comms/services.py (recipient_addresses); templates/accounts/{profile,
  invitations,member_detail}.html; tests apps/accounts/tests/test_phase7.py.
- **Nature of Contribution**: Code generation and tests.
- **Human Review Status**: Pending review; T5 step 1 and T46 step 1 of the private test plan are
  the check. 157 tests pass; ruff, the formatter, and the neutrality check clean.
- **Git Hash**: 5f28b8a

## [2026-09-15 23:50 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Phase 8 of the implementation plan, the verification gate (FR-117,
  FR-116, FR-95, FR-96): an accessibility check in CI (Playwright driving headless Chromium with
  axe-core injected, over every page of the seeded demo as each kind of account, at desktop and
  phone width; a serious or critical violation or a page that scrolls sideways fails the build;
  a self-test proves the check can fail); the fixes it found (the roster's day-heading rows had
  no cell, the editor's status bar carried ARIA axe rejects, long tokens overflowed a phone);
  seed_demo extended with the states of phases 5 to 7; the service worker keeps My schedule and
  My messages for offline reading; the screen-reader walk checklist; onboarding names the jobs
  and the check; NOTICE lists axe-core and TinyMCE.
- **Sections/Files Affected**: tools/a11y/{test_axe.py,conftest.py,axe.min.js,AXE_LICENSE}
  (new; axe-core 4.10.3 vendored under MPL-2.0), .github/workflows/ci.yml (accessibility job),
  requirements-dev.txt (playwright), apps/ops/management/commands/seed_demo.py,
  templates/events/detail.html, config/settings/base.py (editor statusbar), static/css/app.css,
  static/sw.js (cache v3, offline pages), docs/ACCESSIBILITY_WALK.md (new), docs/ONBOARDING.md,
  NOTICE.
- **Nature of Contribution**: Code generation, test harness, documentation.
- **Human Review Status**: Pending review; T49 of the private test plan is the check, and the
  screen-reader walk (T49 step 2) is a person's to do. Locally: 7 accessibility tests pass in
  3 min 49 s; 157 unit tests pass; ruff and the neutrality check clean.
- **Git Hash**: bec7bf3

## [2026-09-15 23:57 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Phase 8 follow-up: the service worker is now served at the site root by
  a Django view with no-cache headers and registered there. Found while verifying the Phase 8
  deploy: the live copy under /static/ was two versions old, held by the 30-day immutable cache
  that is right for hashed static names and wrong for a file whose URL cannot change.
- **Sections/Files Affected**: apps/ops/views.py (service_worker), config/urls.py,
  static/js/app.js, apps/ops/tests/test_health_and_import.py.
- **Nature of Contribution**: Code generation and a test.
- **Human Review Status**: Pending review; T49 step 3 of the private test plan is the check.
  158 tests pass; ruff and the neutrality check clean.
- **Git Hash**: f5b8568

## [2026-09-16 13:33 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Two interface rules from the advisor's review of the Settings page
  (2026-09-16): time zone fields are always a drop-down (he had typed a zone name with a typo;
  a saved typo would put every roster on UTC), and resource paths need a file picker. Built:
  club.timezone and the event's display zone as selects over the IANA list with server-side
  validation; the accent colour as a colour picker; each branding image with a preview, a file
  chooser (PNG/JPEG/SVG/WebP/ICO, 2 MB), and a remove tick, stored under MEDIA_ROOT/branding/
  and served by a small view; branding settings now resolve to URLs for both the overlay's
  static files and uploads, used by the shell, the sign-in layout, and the web manifest.
- **Sections/Files Affected**: apps/ops/{config,views,views_settings}.py, config/urls.py,
  apps/events/views_manage.py (display_timezone field), templates/ops/settings.html,
  templates/base.html, templates/allauth/layouts/base.html, static/css/app.css, tests
  apps/ops/tests/test_settings_and_privacy.py.
- **Nature of Contribution**: Code generation and tests.
- **Human Review Status**: Pending review; T43 step 1 of the private test plan is the check.
  161 tests pass; the accessibility check passes for the sysadmin and officer pages; ruff and
  the neutrality check clean.
- **Git Hash**: 1ef7ce4

## [2026-09-16 13:34 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Two of the advisor's instructions of 2026-09-16. (1) "I want ARCOps to
  be clearly defined upfront as 'Amateur Radio Club Operations'": the README title and first
  sentence, CLAUDE.md, docs/NAME.md, the footer's "Powered by" line, and the repository
  description now spell the name out where it is first met. (2) The screen-reader walk is
  deferred to the club's second or third phase, in his words, recorded at the top of
  docs/ACCESSIBILITY_WALK.md; the automated check is unchanged.
- **Sections/Files Affected**: README.md, CLAUDE.md, docs/NAME.md, docs/ACCESSIBILITY_WALK.md,
  apps/ops/branding.py (PRODUCT_LONG_NAME), templates/base.html.
- **Nature of Contribution**: Edit.
- **Human Review Status**: Pending review (the wording is the advisor's to confirm).
- **Git Hash**: 1bc9dcf

## [2026-09-16 13:43 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: CI's accessibility job failed on f4a0f5e with two slot pages answering
  500: an IndexError deep in Django's session lookup, from SQLite's shared in-memory test
  database misreading rows under the live server's concurrent requests. The check's database
  now lives in a temporary file with a 60 s lock timeout. Locally the full check passes again
  (7 tests, 3 min 54 s); the application is unchanged.
- **Sections/Files Affected**: tools/a11y/conftest.py.
- **Nature of Contribution**: Test-harness fix.
- **Human Review Status**: Pending review; CI on this commit is the check.
- **Git Hash**: 9a17184

## [2026-09-16 14:29 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Defects found by the 2026-09-16 reconciliation of the private test plan
  against this code (four parallel read-only reviews of T1 to T49): the invite form dropped the
  invitee-address help text; the entry-link card hard-coded "7 days" instead of the configured
  verification window; no 429 page existed for allauth's rate limit; the slot generator ignored
  defaults.slot_length_minutes; the view-as button appeared on another sysadmin's page though the
  POST was refused; My Sked still offered "Cannot make it" on a locked roster; two settings the
  code reads (waitlist_offer_hours, health_overview_weeks) were absent from the shipped
  configuration.
- **Sections/Files Affected**: templates/accounts/{invitations,entry_links,member_detail}.html,
  templates/events/my_schedule.html, templates/429.html (new), apps/accounts/views_entry.py,
  apps/events/views_manage.py, config/club.example.yaml.
- **Nature of Contribution**: Code fixes from a review.
- **Human Review Status**: Pending review; the corrected test plan (private, T3, T5, T21, T23,
  T37, T43) is the check. 161 tests pass; ruff and the neutrality check clean.
- **Git Hash**: c3ab667

## [2026-09-16 20:07 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: The advisor received a live password-reset mail from
  "webmaster@localhost" headed "[ops.w3usr.org] Password Reset Email": allauth sends its own mail
  outside the club's composer, so it took Django's default sender and allauth's default
  wording. The adapter now gives every allauth mail the club's sending address and display name
  (FR-69) and an unprefixed subject, and the reset mail has the club's own text, signed off with
  the club's name and contact address.
- **Sections/Files Affected**: apps/accounts/adapter.py (get_from_email, format_email_subject,
  render_mail), templates/account/email/{base_message,password_reset_key_subject,
  password_reset_key_message}.txt (new), apps/accounts/tests/test_flows.py.
- **Nature of Contribution**: Code fix and a test.
- **Human Review Status**: Pending review; T21 step 5 of the private test plan is the check.
  162 tests pass; ruff and the neutrality check clean.
- **Git Hash**: 35550b6

## [2026-09-16 20:45 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: On the advisor's request, allauth's password-reset mail now has an HTML
  part with the link on readable text ("Reset my password"), so a mail scanner that rewrites URLs
  (Microsoft Safe Links) changes only the target and the words a person reads stay clean; the
  plain-text part remains as the alternative. Test extended.
- **Sections/Files Affected**: templates/account/email/{base_message,password_reset_key_message}.html
  (new), apps/accounts/tests/test_flows.py.
- **Nature of Contribution**: Templates and a test.
- **Human Review Status**: Pending review; T21 step 5 is the check. 162 tests pass.
- **Git Hash**: b33dde0

## [2026-09-16 20:56 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: The advisor asked whether other mail needed the same treatment as the
  reset mail. Every one of the club's own message templates carried its URL as the link's own
  text (or bare), so a mail scanner that rewrites URLs replaced the words a person reads. The 23
  templates with a URL now put it behind a short labelled link ("Accept the invitation", "Open
  the slot", "Take it", "View the password", …); the reminder's two links already had labels.
  The plain-text alternative still carries the URL. club_import refreshes unedited template
  rows on deploy.
- **Sections/Files Affected**: apps/comms/defaults.py (23 templates).
- **Nature of Contribution**: Edit.
- **Human Review Status**: Pending review; T3, T19, T31, T42 of the private test plan show the
  mails. 162 tests pass.
- **Git Hash**: e41fe2a

## [2026-09-16 21:14 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: The advisor found the HTML reset mail ugly in Outlook, whose renderer
  ignores the CSS that drew the button. One mail layout for everything the site sends
  (apps/comms/layout.py): a table frame with a band in the club's accent colour naming the
  club, the body at a readable measure, the club's name and contact beneath; a table-drawn
  button for a message's one call to action; plain links coloured inline. deliver() wraps the
  club's messages in it; the sign-in library's mail is wrapped by the adapter; the reset mail
  uses the button. Tests for both paths.
- **Sections/Files Affected**: apps/comms/layout.py (new), apps/comms/services.py (deliver),
  apps/accounts/adapter.py (render_mail), templates/account/email/{base_message,
  password_reset_key_message}.html, apps/comms/tests/test_messages.py,
  apps/accounts/tests/test_flows.py.
- **Nature of Contribution**: Code generation and tests.
- **Human Review Status**: Pending the advisor's look at the next mail in Outlook. 163 tests
  pass; ruff and the neutrality check clean.
- **Git Hash**: 828563a

## [2026-09-16 21:27 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Two things from the advisor's reset walk-through: the "password changed"
  page had no way back to sign-in (it now says so and offers a Sign in button), and Outlook
  recoloured the mail button's text with its own link colour (an inner span and font tag now
  hold the white). Tests for both.
- **Sections/Files Affected**: templates/account/password_reset_from_key_done.html (new),
  apps/comms/layout.py (button), static/css/app.css (.button.wide),
  apps/accounts/tests/test_flows.py.
- **Nature of Contribution**: Code fix and tests.
- **Human Review Status**: Pending the advisor's next look. 164 tests pass.
- **Git Hash**: ae28158

## [2026-09-16 21:40 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: Two of the advisor's findings on the reset flow (FR-107). An unknown
  address received the library's "Unknown Account" mail, pointing at a signup page this site
  does not have: strangers now get no mail at all, and the page after the form reads the same
  for everyone, in his words: "If we have an account with that address on file, a message with
  a reset link is on its way." A personal address on file did not work for a reset because the
  library matched only the sign-in address: a reset may now be asked for with the sign-in,
  institution, or personal address, and the mail goes to the address typed; a minor's generated
  sign-in-only address is excluded.
- **Sections/Files Affected**: apps/accounts/forms.py (new ResetPasswordForm), config/settings/
  base.py (ACCOUNT_FORMS), templates/account/password_reset_done.html (new),
  apps/accounts/tests/test_flows.py.
- **Nature of Contribution**: Code fix and a test.
- **Human Review Status**: Pending the advisor's retry with his personal address. 165 tests pass.
- **Git Hash**: 1ecf1fb
