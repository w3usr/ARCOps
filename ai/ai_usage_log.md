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

## [2026-09-16 22:06 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: The advisor's reset link from the new form read "Bad Token" on his phone.
  Cause, from the access log and the library's code: the form shipped an hour earlier fell back
  to Django's token generator when making the link, while the library checks links with its
  own email-aware one, so every fresh link failed. The form now uses the library's generator,
  and the test follows the link through to setting a password, which it had not.
- **Sections/Files Affected**: apps/accounts/forms.py, apps/accounts/tests/test_flows.py.
- **Nature of Contribution**: Bug fix and test.
- **Human Review Status**: Pending the advisor's retry. 165 tests pass.
- **Git Hash**: d4b32fe

## [2026-09-17 01:58 UTC]
- **Tool**: Claude (Anthropic), claude-fable-5-1
- **Session Purpose**: "Sysadmins should be able to edit all fields" (the advisor, 2026-09-17,
  on a member's page). The sysadmin's Manage form now carries the preferred name, the sign-in
  address (kept unique), the institution and personal addresses with their delivery switches,
  the mobile number, and the student fields, alongside the privilege fields; officers still
  edit the club position only; every change is audited as before. Test added.
- **Sections/Files Affected**: apps/accounts/views_members.py (MemberForm),
  apps/accounts/tests/test_members.py.
- **Nature of Contribution**: Code generation and a test.
- **Human Review Status**: Pending review; T7 step 4 of the private test plan is the check.
  166 tests pass.
- **Git Hash**: 372aacc

## [2026-09-17 02:10 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: "We should not have FR- and TR-references in the UI" (the advisor,
  2026-09-17, seeing "Delete this account (FR-118)" and two others on a member's page). Every
  requirement identifier was removed from the text a browser renders and from the labels, help
  text, and messages a form shows; they stay in code comments, docstrings, and template
  comments. A new check, tools/check_no_requirement_ids.sh, fails a build that puts one back;
  it strips template comments and Python comments before looking, skips migrations, and was
  proved able to fail by planting one. CI runs it beside the club-neutrality check, and
  docs/ONBOARDING.md explains both.
- **Sections/Files Affected**: 18 templates, apps/events/models.py (help text) with migration
  events 0005, apps/events/views_manage.py, apps/accounts/views.py, apps/accounts/views_members.py,
  tools/check_no_requirement_ids.sh (new), .github/workflows/ci.yml, docs/ONBOARDING.md.
- **Nature of Contribution**: Edit and a check.
- **Human Review Status**: Pending review; the member page and the settings page are where the
  advisor saw them. 166 tests pass; ruff, both checks clean.
- **Git Hash**: 98d90c9

## [2026-09-17 02:26 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The advisor asked for a clear dividing line in the sidebar between the
  officer's tools and the sysadmin's, and for "Admin" to read "Django Admin". The sidebar is
  now three lists: the member's pages, then **Officer tools** (Invite, Approvals,
  Announcements, Outbox), then **Sysadmin tools** (Status, Templates, Settings, Django Admin).
  Each later group sits under a rule with a small label, which also names the list for a screen
  reader; collapsed to the rail the rules stay and the words go, as the other labels do. Django
  Admin takes its own icon, so it no longer repeats Settings'.
- **Sections/Files Affected**: templates/base.html, static/css/app.css.
- **Nature of Contribution**: Edit.
- **Human Review Status**: Pending review. 166 tests pass; the accessibility check passes for
  the member, officer, and sysadmin views; both project checks clean.
- **Git Hash**: 515be43

## [2026-09-17 02:42 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Four findings from the advisor on a member's page (2026-09-17). (1) His
  own licence read "none on file" though his callsign is in the FCC table: the nightly sync
  refreshed licence records but never created one, so an account whose callsign was set outside
  the profile form (the first sysadmin, an import) never got a licence; the sync is now driven
  by the member's callsign. (2) On his own page the licence override was hidden by the
  not-yourself check that guards deletion and access removal; it is now available to a sysadmin
  on any page, and, at his suggestion, a **Look this callsign up in the FCC table** button beside
  the licence lets any officer re-read the table for one member, audited. (3) Student level and
  graduation now appear only while the category is Student, and are cleared on save otherwise.
  (4) Guardian is no longer a membership category: guardianship is a relationship, any adult
  account can hold it, and a parent who joins only to manage a minor is a community member.
- **Sections/Files Affected**: apps/credentials/uls.py (refresh_members), apps/accounts/
  views_members.py, apps/accounts/views.py, apps/accounts/models.py, apps/events/services/
  eligibility.py, apps/events/views_adults.py, apps/ops/management/commands/seed_demo.py,
  templates/accounts/member_detail.html, static/js/app.js, config/club.example.yaml, tests in
  apps/credentials/tests/test_uls.py, apps/accounts/tests/{test_members,test_phase7}.py.
- **Nature of Contribution**: Bug fix, code generation, tests.
- **Human Review Status**: Pending the advisor's look; his own page is the check. 169 tests pass;
  ruff and both project checks clean.
- **Git Hash**: 749889e

## [2026-09-17 03:04 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: On the advisor's instruction after we talked it through: either address
  on an account signs a member in. REQUIREMENTS §2.6 already asked for this ("either on file")
  and only one address had ever worked, so this is a defect closed rather than a feature added;
  the condition we agreed, that an address must be confirmed before it carries the weight of a
  credential, is recorded as a clarification with its reasoning. Built: apps/accounts/
  addresses.py holds the rule (the sign-in address always works; another works once confirmed,
  by the member's link or an officer's word, the same waiver as a class link, so nothing waits
  on mail); confirmed addresses live in the sign-in library's own table, which is what it
  consults and which holds a confirmed address to one account; a confirmed address is never
  removed automatically, so a mistyped sign-in address cannot lock anyone out; password reset
  now accepts exactly the addresses that sign a member in; the profile and the member page show
  each address with its standing and the controls to confirm, resend, or withdraw it. Also
  stopped the plain-text part of every message wrapping a long URL mid-link.
- **Sections/Files Affected**: apps/accounts/addresses.py (new), apps/accounts/{views,
  views_members,forms,urls}.py, apps/comms/{services,defaults}.py, config/urls.py,
  templates/accounts/{verify_address (new),profile,member_detail}.html,
  docs/REQUIREMENTS.md (§2.6 and the decision record), tests
  apps/accounts/tests/{test_addresses (new),test_flows}.py.
- **Nature of Contribution**: Code generation, tests, requirement clarification.
- **Human Review Status**: Pending the advisor's check with his two addresses. 175 tests pass;
  ruff and both project checks clean.
- **Git Hash**: c0dcc34

## [2026-09-17 03:30 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: On the advisor's instruction after the evaluation: one account form for
  both pages, with the fields derived from one permission table rather than a form per page.
  apps/accounts/account.py holds editable_fields (the requirements' editability rules in one
  place), AccountForm, and save_account, the one save path; templates/accounts/_account_form.html
  and _addresses.html are shared by the profile and the member page. Three faults the split had
  hidden are closed: a callsign typed on the member page skipped the FCC lookup, the licence
  record, the name check, and the history; the same field carried two labels; and a member with
  no callsign could not edit their own name although FR-8 says they may. The member page is one
  column now, matching the profile, at the advisor's preference.
- **Sections/Files Affected**: apps/accounts/account.py (new), apps/accounts/{views,
  views_members}.py, templates/accounts/{_account_form,_addresses}.html (new),
  templates/accounts/{profile,member_detail}.html, tests
  apps/accounts/tests/test_account_form.py (new).
- **Nature of Contribution**: Refactor, bug fixes, tests.
- **Human Review Status**: Pending the advisor's look at both pages. 181 tests pass; the
  accessibility check passes for the member, officer, and sysadmin views; ruff and both project
  checks clean.
- **Git Hash**: 8f14c3c

## [2026-09-17 03:48 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Three things the advisor found on the rebuilt member page. A multi-line
  {# #} renders as text in Django, so the two partials' opening comments were showing on the
  page; they are {% comment %} blocks now and a test reads both pages for a leak. The read-only
  card repeated what the form already offered as inputs: readonly_rows is now the complement of
  editable_fields, so a field is an input where the viewer may change it and a line of text
  where they may not, never both, with a skip for a field the page shows elsewhere (the name in
  the heading). The unconfirmed address badge is now the button that sends the link, and each
  address carries its delivery state, so the addresses appear in one place on both pages.
- **Sections/Files Affected**: apps/accounts/account.py (readonly_rows), apps/accounts/
  addresses.py (delivery in the list), apps/accounts/{views,views_members}.py,
  templates/accounts/{_account_readonly.html (new),_account_form,_addresses,profile,
  member_detail}.html, static/css/app.css, apps/accounts/tests/test_account_form.py.
- **Nature of Contribution**: Bug fix and interface work.
- **Human Review Status**: Pending the advisor's look. 183 tests pass; the accessibility check
  passes for the member, officer, and sysadmin views; ruff and both project checks clean.
- **Git Hash**: 505ec70

## [2026-09-17 05:05 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The advisor's decision that an account should not have a "sign-in" email
  at all, implemented. Identity is now `public_id`, a UUID that never changes and is never
  typed; every address a person holds is an `Address` row with its kind, whether it is
  confirmed, and its own delivery switch. Any confirmed address signs its owner in; an
  unconfirmed one still receives club mail; an account keeps at least one address, except a
  minor, who may hold none because their guardians are written to and act for them. The two
  fabricated addresses the old schema needed (a minor's `guardian+name@`, a deleted account's
  `deleted-<id>@invalid.example`) are gone. One address-control handler serves both the member's
  own profile and an officer's view of them. Migration 0009 was written by hand, rehearsed
  forward and in reverse against a database built on the old schema, and made reversible.
- **Sections/Files Affected**: apps/accounts/{models,addresses,account,entry,forms,services,
  admin,urls,views,views_entry,views_members}.py, apps/accounts/views_addresses.py (new),
  apps/accounts/migrations/0009_identity_is_a_key_addresses_are_rows.py (new), apps/comms/
  {services,defaults}.py, apps/credentials/{views,views_reports}.py, apps/ops/retention.py,
  apps/ops/management/commands/{seed_demo,bootstrap_sysadmin}.py, config/settings/base.py,
  templates/accounts/{_addresses,_account_form,profile,member_detail,members,verify_address}.html,
  templates/credentials/approvals.html, static/css/app.css, docs/REQUIREMENTS.md (§2.6, FR-107),
  tools/a11y/test_axe.py, and the account tests including a new apps/ops/tests/
  test_bootstrap_sysadmin.py.
- **Nature of Contribution**: Design, code generation, data migration, and test rewriting under
  the advisor's decision, quoted in docs/REQUIREMENTS.md §2.6 and the session note.
- **Human Review Status**: Pending the advisor's look. 188 tests pass; the accessibility check
  passes for every role at phone and desktop width; ruff, the club-neutrality guard and the
  requirement-id guard are clean; `makemigrations --check` reports no changes.
- **Git Hash**: 05c2b86

## [2026-09-17 10:35 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: A sweep for anything left assuming one address per account, after the
  identity refactor. The directory now lists every address an officer may write to, in one
  query; the member roster export prefetches them too. The three pages that named a single
  address hold for an account with none: a minor's temporary-password page says there is
  nothing to sign in with yet, the guardian's invitation page says the same, and the signed
  agreement's PDF names the account's address only when there is one.
- **Sections/Files Affected**: apps/accounts/views_members.py, apps/credentials/
  views_reports.py, templates/accounts/{members,ward_password,accept_invitation_guardian}.html,
  templates/credentials/agreement_pdf.html, apps/accounts/tests/test_members.py.
- **Nature of Contribution**: Code and template edits with a test.
- **Human Review Status**: Pending the advisor's look. 188 tests pass; ruff and both project
  checks clean.
- **Git Hash**: 64ac45c

## [2026-09-17 11:05 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The identity migration rehearsed against a copy of the server's database
  (the advisor's permission, 2026-09-17), which found two defects invented data could not. The
  delivery rule was lost when the sign-in address also filled one of the two contact slots: with
  both switches off, every row came out with delivery off, and the application then writes to
  every address, so an address that had been receiving nothing would have started receiving club
  mail. And the sign-in library's own table was left holding the pre-migration rows, because
  nothing calls the mirror during a migration. Both fixed; the migration now rebuilds that table
  to hold exactly the confirmed addresses.
- **Sections/Files Affected**: apps/accounts/migrations/0009_identity_is_a_key_addresses_are_rows.py.
- **Nature of Contribution**: Defect analysis and code.
- **Human Review Status**: Pending the advisor's look. Rehearsed forward, back, and forward again
  against the copy: both real accounts keep their addresses, the delivery rule is preserved, and
  the mirror matches. 188 tests pass; `makemigrations --check` reports no changes.
- **Git Hash**: a68ad02

## [2026-09-17 11:20 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The Faculty advisor access level the advisor asked for (issue 87 of the
  private repository), between Club officer and Sysadmin. Approving a signed access agreement,
  and converting a minor's account at 18, move from a flag on the club position to this level:
  an elected officer cannot approve access to the station, whatever post they hold. The ladder
  now has a rank, so "this level and above" is one comparison rather than a list of levels that
  a new level silently escapes. Approvals moved out of the officer group in the sidebar into an
  advisor group of its own.
- **Sections/Files Affected**: apps/accounts/models.py (AccessLevel, ACCESS_RANK, at_least,
  levels_at_least, is_advisor), apps/accounts/migrations/0010_faculty_advisor_access_level.py,
  apps/credentials/{views,services}.py, apps/{comms/announce,events/services/lifecycle,
  events/services/notify,accounts/entry,accounts/services}.py, templates/base.html,
  config/club.example.yaml, docs/REQUIREMENTS.md (§2.1, §2.3, the capability table),
  apps/accounts/tests/test_access_levels.py (new), the credentials tests.
- **Nature of Contribution**: Design and code generation from the advisor's issue.
- **Human Review Status**: Pending the advisor's look. 192 tests pass; ruff and both project
  checks clean; `makemigrations --check` reports no changes.
- **Git Hash**: 3ba45ec

## [2026-09-17 11:35 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The archive of former members, replacing the automatic deletion the
  advisor said he did not want. A faculty advisor or a sysadmin archives someone who has left,
  with a reason; the record is kept whole and indefinitely, the account stops authenticating and
  leaves the directory and every audience, and the archive page is readable only at advisor level
  and above, with each opening written to the audit log. An advisor restores someone, and there
  is nothing to restore but the access, because nothing ages out while they are in it. The
  retention job no longer strips a former member's contact details or purges expired agreements;
  what still runs is what is not a member's own record. The privacy notice, which promised those
  deletions to members, says what happens now.
- **Sections/Files Affected**: apps/accounts/{models,services,views_members,admin}.py,
  apps/accounts/migrations/0011_archive_former_members.py, apps/ops/retention.py,
  apps/ops/views_settings.py, apps/ops/templatetags/nav.py, apps/ops/management/commands/
  seed_demo.py, config/{urls.py,club.example.yaml}, templates/accounts/{archive.html (new),
  member_detail.html}, templates/base.html, docs/{REQUIREMENTS.md (FR-125, §4.3),
  TECHNICAL_REQUIREMENTS.md (TR-28), JOBS.md}, tools/a11y/test_axe.py,
  apps/accounts/tests/{test_archive.py (new), test_phase6.py}.
- **Nature of Contribution**: Design and code generation from the advisor's decision, with the
  privacy consequences named rather than assumed.
- **Human Review Status**: Pending the advisor's look. 202 tests pass; ruff and both project
  checks clean.
- **Git Hash**: 5738c6a

## [2026-09-17 11:50 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The advisor asked whether capabilities should stop deriving from the club
  position entirely. Reading the tree for the answer found two rules still on the old flag: the
  "who to call" line on a slot reminder, which had gone empty when the flag left the
  configuration an hour earlier and would have sent every reminder without the advisor's contact
  details, and the access-rosters page, which offered a Revoke control to anyone holding any
  position while the action behind it required an approver. Both follow the access level now,
  and a test reads the tree for the shape of either mistake returning.
- **Sections/Files Affected**: apps/events/services/notify.py (advisors),
  templates/credentials/access_rosters.html, apps/accounts/tests/test_access_levels.py.
- **Nature of Contribution**: Defect analysis and code.
- **Human Review Status**: Pending the advisor's look. 204 tests pass; ruff clean.
- **Git Hash**: d94fe2a

## [2026-09-17 12:45 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The rest of the permission model the advisor asked for. A page where a
  sysadmin decides what each group may do, adds a group the application has never heard of, and
  removes an empty one, refusing the one edit that cannot be undone from inside: leaving nobody
  able to decide who may do what. The requirements' access section was rewritten around
  capabilities and groups rather than a ladder, with the advisor's words quoted, and a technical
  requirement records how it is built.
- **Sections/Files Affected**: apps/ops/views_groups.py (new), templates/ops/groups.html (new),
  apps/ops/urls.py, templates/base.html, static/css/app.css, apps/ops/tests/test_groups_page.py
  (new), tools/a11y/test_axe.py, docs/REQUIREMENTS.md (§2.1, §2.3, the capability table, the
  decision record), docs/TECHNICAL_REQUIREMENTS.md (TR-42).
- **Nature of Contribution**: Design and code generation from the advisor's decision.
- **Human Review Status**: Pending the advisor's look. 218 tests pass, including the permission
  matrix unchanged from before the refactor; ruff and both project checks clean.
- **Git Hash**: 3cf2b6c

## [2026-09-17 13:50 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Two decisions of the advisor's. First, sysadmin and superuser are one
  thing, so the Sysadmin group is gone and the account flag is what a sysadmin is, set from the
  member's own page beside the groups. Second, a session acts at a level rather than always at
  the top: a sysadmin signs in acting as Faculty advisor, the name in the sidebar shows the level
  and leads to the page that changes it, raising asks for the password and lowering does not, and
  no level is offered that the account does not already hold. The lowered level is real, because
  `User.has_perm` answers from it: a request it does not allow is refused rather than hidden.
- **Sections/Files Affected**: apps/accounts/acting.py (new), apps/accounts/views_acting.py
  (new), templates/accounts/acting_view.html (new), apps/accounts/{models,account}.py,
  apps/accounts/urls.py, config/settings/base.py, templates/base.html, static/css/app.css,
  config/club.example.yaml, apps/accounts/migrations/0012 (no sysadmin group),
  apps/ops/management/commands/bootstrap_sysadmin.py, apps/accounts/tests/test_acting_view.py
  (new), the permission matrix (a sysadmin at the everyday level and the same account raised),
  many test factories, docs/REQUIREMENTS.md §2.1, docs/TECHNICAL_REQUIREMENTS.md (TR-43).
- **Nature of Contribution**: Design and code generation from the advisor's decisions, with the
  security claim stated honestly in the module and the requirements (a seatbelt, not a lock).
- **Human Review Status**: Pending the advisor's look. 226 tests pass; ruff and both project
  checks clean; `makemigrations --check` reports no changes.
- **Git Hash**: 7adef4d

## [2026-09-17 16:45 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The requirements reconciled against the code after the day's three
  changes. Four reviewers read the acceptance plan and both requirement documents against the
  tree and reported 41 discrepancies; the requirements' side is applied here. What changed:
  deletion and closure no longer speak of a retention clock, signed agreements are kept
  indefinitely, the field table carries one Addresses row instead of two email fields and a
  delivery preference, the audit log's list names the actions the code writes, approving an
  agreement and converting a minor follow capabilities rather than a club position, the sign-in
  identifier is the account's key, the data-model row names what the model holds, and the
  uploads requirement admits the branding image the settings page has accepted since Phase 6.
- **Sections/Files Affected**: docs/REQUIREMENTS.md (FR-8's field table, FR-11, FR-25, FR-70,
  FR-89, FR-92, FR-94, FR-107, FR-109, FR-118, the §2.5 matrix, Q8),
  docs/TECHNICAL_REQUIREMENTS.md (TR-15, TR-25, TR-26).
- **Nature of Contribution**: Review by four subagents, applied and checked by the assistant.
- **Human Review Status**: Pending the advisor's look. 228 tests pass.
- **Git Hash**: 08ad3f0

## [2026-09-17 21:07 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The interface, reviewed and rebuilt. The advisor read the live site and
  found three faults in as many minutes: a level offered as "Faculty Advisor · 16 capabilities",
  a heading reading "Where we write, and how you sign in" where "Email" would do, and a run of
  badges, buttons, and links after each address ending in a filled red pill. His instruction was
  to survey every page, find the best practice for this kind of application, propose one solution,
  and apply it everywhere. Four reviewers read all 73 templates, the stylesheet, and the
  JavaScript against the code behind them and returned 159 findings. Applied here: the dozen that
  were not cosmetic (pressing Recount discarded the announcement body; a bad value in Settings
  discarded everything typed; Enter in the decline-reason field approved an agreement and granted
  station access; a captain's remove bypassed the viability check and sent an empty reason; the
  slot role override was an inline handler the content security policy blocks; any banner pushed
  the page into the sidebar column; danger buttons were 2.0:1 in dark mode and the focus ring
  2.0:1 in light; flash messages were never announced; bulk cancel and regenerate were
  unconfirmed; two pages disagreed about "open" slots), then the house rules in docs/INTERFACE.md,
  the design system they need, and a vocabulary pass so no stored key, dotted setting, or Python
  repr reaches a page. Also, on the advisor's instruction mid-session, American English throughout.
- **Sections/Files Affected**: docs/INTERFACE.md (new); tools/check_interface.sh (new, wired into
  CI); tools/a11y/test_contact_sheet.py (new); apps/ops/templatetags/labels.py (new);
  apps/ops/tests/test_interface.py and test_labels.py (new); static/css/app.css; static/js/app.js;
  templates/base.html and 30 further templates, the member page and profile rebuilt as separate
  cards with a danger zone last; apps/comms/views_announce.py, apps/ops/views_settings.py,
  apps/events/views.py, views_slots.py, views_manage.py; apps/comms/defaults.py and categories.py;
  apps/credentials/models.py; apps/events/services/viability.py; config/club.example.yaml.
- **Nature of Contribution**: Review by four subagents; design, code, and tests by the assistant
  under the advisor's four instructions and four design decisions.
- **Human Review Status**: Pending the advisor's look at the contact sheet. 241 tests pass, ruff
  clean, the axe sweep passes for all eight roles at 1280px and 390px, and the three repository
  guards pass.
- **Git Hash**: 9d15363

## [2026-09-17 23:18 UTC]
- **Session Purpose**: The rest of the interface review applied: the polish findings left over
  from the first pass. The event manage page gains a strip at the top saying which of the four
  setup steps are done and which to do next, because the page is a dozen cards with nothing on it
  that says what order they go in. The announce page is rebuilt as "Who gets it" and "What it
  says", with the count of recipients and the control that counts again beside each other. Every
  empty state now names what belongs there and how it gets there, rather than saying "None yet."
  Row-level actions read as words ("Remove them", "Check in") instead of lowercase fragments. The
  two "before you cancel" pages put the safe option first, after the VA design system, and stop
  using "cancel" to mean two things on one page. The sign-in page stops offering to recover a
  username, since an account has none. One fault found by the new guard was already live: a
  {# #} comment on the approvals page ran over two lines, and Django's is a single line, so the
  comment was rendering onto the page as text. The guard now refuses that, and was checked
  against a file that should fail.
- **Tool**: Claude (Anthropic), claude-opus-5
- **Sections/Files Affected**: apps/events/views_manage.py (setup_steps); templates/events/
  manage.html, confirm_cancel.html, confirm_role.html, list.html, my_schedule.html, _slot_body.html,
  adults.html, participation.html, health_overview.html; templates/comms/announce.html,
  my_messages.html, announcements.html; templates/credentials/agreements.html, approvals.html,
  access_rosters.html, password_denied.html; templates/accounts/invitations.html, entry_links.html,
  members.html, roster.html, member_detail.html, profile.html, hours.html, join.html,
  ward_password.html; templates/account/login.html, password_reset.html; templates/ops/
  settings.html, outbox.html, groups.html; static/css/app.css; tools/check_interface.sh;
  apps/comms/defaults.py.
- **Nature of Contribution**: Design and code by the assistant, from the review the four subagents
  returned earlier in the day.
- **Human Review Status**: Pending the advisor's look. 241 tests pass, ruff clean, the axe sweep
  passes for all eight roles at 1280px and 390px, and the four repository guards pass.
- **Git Hash**: f79ccee

## [2026-09-18 00:49 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The requirements reconciled with the interface work of 2026-09-17. Six
  requirements said something the code no longer does: FR-107 quoted the sign-in link as "Forgot
  your username or password?", which is gone because an account has no username; FR-58 now
  records that removing somebody else's sign-up is confirmed on its own page and requires a
  reason; FR-89 that a settings submission with a bad value saves nothing and returns what was
  typed; FR-95 that a stacked table cell carries its column heading, and why a scrolling wide
  table was rejected; FR-62 that the rule against color carrying meaning alone reaches the four
  feedback levels and destructive links. TR-44 is new: the interface standard in docs/INTERFACE.md
  with tools/check_interface.sh enforcing the greppable half in CI. The interface guard itself
  gained a fix: it exempted a whole line that mentioned an identifier, so
  `{% if e.state == 'cancelled' %}<span class="tag">Cancelled</span>` hid visible British text
  behind a state key. It now blanks the identifier and checks what is left, which caught that tag.
- **Sections/Files Affected**: docs/REQUIREMENTS.md (FR-58, FR-62, FR-89, FR-95, FR-107);
  docs/TECHNICAL_REQUIREMENTS.md (TR-44 added, TR-38 amended); tools/check_interface.sh;
  templates/events/list.html.
- **Nature of Contribution**: Analysis and edit by the assistant.
- **Human Review Status**: Pending the advisor's look. 241 tests pass and the four guards pass.
- **Git Hash**: 7bb5e83

## [2026-09-19 13:47 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Two things. First, the privacy notice is now linked from the box that
  consents to it, on all three ways into the club. The advisor, looking at the invitation page
  during T3: "We need to link to the privacy notice if we are going to ask people to agree to
  it." The invitation path linked it nowhere, the guardian path linked it only in a trailing
  sentence, and the entry-link path had gained a link the day before. The link now sits inside
  the consent label itself and opens in a new tab, so reading it does not cost a half-filled
  form. Second, the test cycle: it ran about thirteen minutes, which was discouraging changes.
  Measurement showed one accessibility role taking 96s wall for 31s of CPU, so two thirds of it
  was waiting on a browser, and the machine has 64 cores running one. With pytest-xdist the
  application tests go 82s to 15s and the accessibility sweep 11 minutes to 98s; tools/check.sh
  runs the whole gate, both suites at once, in 1m48s.
- **Sections/Files Affected**: apps/accounts/consent.py (new), apps/accounts/tests/test_consent.py
  (new), apps/accounts/views.py, apps/accounts/views_entry.py, templates/accounts/
  accept_invitation.html, accept_invitation_guardian.html, join.html; tools/check.sh (new),
  requirements-dev.txt, .github/workflows/ci.yml, CLAUDE.md, docs/INTERFACE.md.
- **Nature of Contribution**: Code, tests, and measurement by the assistant.
- **Human Review Status**: Pending the advisor's look. 244 tests pass, the accessibility sweep
  passes for all eight roles, and the four guards pass.
- **Git Hash**: a7ebb50 (consent), d93f2e3 (test speed)

## [2026-09-19 14:06 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The retention section cut from the generic privacy notice this repository
  ships. The advisor removed it from the club's own notice first, on the grounds that a retention
  policy should not be published before it is vetted; the same holds with more force for the
  default a different club would publish under its own name without reading it. The notice's other
  sections do not refer to it, so nothing was left dangling.
- **Sections/Files Affected**: config/club.example.yaml (privacy_notice_html).
- **Nature of Contribution**: Edit by the assistant, at the advisor's instruction.
- **Human Review Status**: Reviewed by the advisor, who asked for it.
- **Git Hash**: b475868

## [2026-09-19 14:25 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: One live invitation link per person. The advisor, testing T3, found six
  rows for one address and asked what was going on. The audit log separated two things: two of
  them were "Make a new link" working exactly as designed, revoking and replacing in the same
  instant, and three more were plain presses of Create invitation, eleven seconds apart, each
  making another independently valid link. Four links worked at once, revoking any one withdrew
  nothing, and six invitation emails reached the mailbox. Creating an invitation now withdraws
  any earlier one still open to the same address, matched by the guardian's address for a minor
  who has none of their own, and the page says how many it withdrew.
- **Sections/Files Affected**: apps/accounts/services.py (_supersede_open_invitations,
  create_invitation), apps/accounts/views.py, templates/accounts/invitations.html,
  apps/accounts/tests/test_members.py (four tests added), docs/REQUIREMENTS.md (FR-3).
- **Nature of Contribution**: Diagnosis from the live audit log, code, and tests by the assistant.
- **Human Review Status**: Pending the advisor's retest of T3. 248 tests pass, the accessibility
  sweep passes, and the four guards pass.
- **Git Hash**: 05cc0c3

## [2026-09-19 15:20 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: A Server Error (500) the advisor hit while testing T3, and the data damage
  behind it. He completed an invitation, made a second one to the same address, and tried it three
  times; each attempt answered 500 and left an account behind. The log named the cause:
  AddressInUse raised out of create_user, uncaught. Three faults, one root: create_user saved the
  account and then added the address, with nothing holding the two together, so a refused address
  left a member with no address, in a group, in the directory, unable to sign in. Fixed by making
  account creation atomic, which closes it for every path in, not only invitations; by catching
  the refusal in the invitation and guardian views and putting it on the form with a route
  forward; and by refusing at the Invite page to issue an invitation to an address that already
  has an account, so nobody is sent a link certain to fail. The three orphan rows on the live
  server were removed, each with an audit row saying what it was.
- **Sections/Files Affected**: apps/accounts/models.py (create_user), apps/accounts/views.py
  (InviteForm.clean, accept_invitation, _accept_as_guardian),
  apps/accounts/tests/test_address_clash.py (new, five tests), docs/TEST_PLAN.md (T3 step 8).
- **Nature of Contribution**: Diagnosis from the production traceback, code, and tests by the
  assistant; the orphan removal was checked against each row before it ran.
- **Human Review Status**: Pending the advisor's retest of T3. 253 tests pass, the accessibility
  sweep passes, and the four guards pass. The new tests were checked against the unfixed code:
  three of the five fail without it.
- **Git Hash**: 86bc92a

## [2026-09-19 15:29 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The sign-in confirmation removed. The advisor, on "Done: Successfully
  signed in as Kay Craigie (N3KN).": "We don't need a notification saying you successfully signed
  in." The page it sits above is headed "Hello, Kay" and names the account in the sidebar, so the
  message repeated what the reader could see. Suppressed by overriding allauth's logged_in
  template with an empty one, which allauth reads as "say nothing". Signing out keeps its
  message, because the page it lands on is also the page an expired session lands on and the two
  are worth telling apart. The principle is now in docs/INTERFACE.md, since this is the second
  time a message has been noise: confirm an action when its result is not visible, stay quiet
  when it is.
- **Sections/Files Affected**: templates/account/messages/logged_in.txt (new, deliberately
  empty), apps/accounts/tests/test_signin_messages.py (new), docs/INTERFACE.md.
- **Nature of Contribution**: Edit and tests by the assistant, at the advisor's instruction.
- **Human Review Status**: Pending the advisor's look. 255 tests pass, the sweep passes, the four
  guards pass.
- **Git Hash**: 1f9a447

## [2026-09-19 15:40 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: A deleted account was still listed among the members. The advisor deleted a
  test account and found "a remnant Deleted member" in the directory, with no address and no
  access. The row itself is right: FR-118 keeps it so a past roster still adds up. What was wrong
  is that the directory filtered out archived accounts and not deleted ones, and the same slip
  sat in the responsible-adult picker, which listed every adult row rather than the accounts that
  can be used. Both now exclude them; archiving and deleting both clear is_active, so
  with_access() was already right everywhere else it was used.
- **Sections/Files Affected**: apps/accounts/views_members.py, apps/events/views_adults.py,
  apps/accounts/tests/test_deleted_not_listed.py (new, four tests).
- **Nature of Contribution**: Diagnosis, code, and tests by the assistant.
- **Human Review Status**: Pending the advisor's look. 259 tests pass, the sweep passes, the four
  guards pass. The new test was checked against the unfixed code and fails without it.
- **Git Hash**: 423d1c3

## [2026-09-19 15:48 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: What a deleted account's retained row may hold. Reviewing the row left by
  FR-118, two fields were doing no work: push_enabled, a notification switch on an account that
  cannot sign in and whose subscriptions the deletion already removes, and last_login. The
  advisor kept the second: "last_login may still be good for audit or investigation purposes."
  So deletion now clears push_enabled, and a comment records why last_login stays, so that a
  later tidying pass does not remove the one fact kept on purpose. The single existing row on
  the live server was corrected the same way, with an audit entry.
- **Sections/Files Affected**: apps/accounts/services.py (delete_account),
  apps/accounts/tests/test_deleted_not_listed.py.
- **Nature of Contribution**: Code and test by the assistant, at the advisor's decision.
- **Human Review Status**: Reviewed by the advisor, who made the call on each field. 260 tests
  pass and the guards pass.
- **Git Hash**: cb553a8

## [2026-09-19 16:03 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The members directory rebuilt to the advisor's specification: first, last
  and preferred name in their own columns, every column sortable and defaulting to last name,
  phone in its own column beside email, filters on category, position and access, the access
  column for officers and above only, "joined via" dropped, and the same table for every access
  level rather than a table for officers and a list of cards for members. The redaction is
  unchanged: a member still sees a first name and a last initial and no addresses, and the
  columns they may not see are absent rather than empty, so nothing on the page hints at what is
  being withheld. Sorting reads the value shown rather than the key stored behind it, which is
  why it happens in Python: three of the columns show a label the database does not hold. Every
  sort ends in the same tiebreaker, so reversing a column reverses the page exactly.
- **Sections/Files Affected**: apps/accounts/views_members.py (DIRECTORY_COLUMNS, _sort_keys,
  members), templates/accounts/members.html, static/css/app.css,
  apps/accounts/tests/test_directory.py (new, nine tests), apps/accounts/tests/test_members.py.
- **Nature of Contribution**: Design and code by the assistant, to the advisor's specification.
- **Human Review Status**: Pending the advisor's look. 269 tests pass, the accessibility sweep
  passes for all eight roles at both widths, and the four guards pass.
- **Git Hash**: dde98a8

## [2026-09-19 16:38 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Four more changes to the members directory, at the advisor's direction. The
  name column is back for officers, showing the same redacted name a member sees rather than the
  full one: "so the officers can quickly see what is on public view", without signing in as
  somebody else. The license class is its own column, on the page for everyone, and it sorts up
  the ladder rather than down the alphabet, because sorted as words Advanced would file above
  Technician. It can be filtered, including for members holding no license at all. And phone
  numbers are written the way their own country writes them, through Google's libphonenumber
  (the `phonenumbers` package) rather than a regular expression of our own: the club is at a US
  university but its community members are not all in it, and a home-made formatter would put
  brackets round a London number. What a member typed is stored untouched; a number the library
  cannot make sense of is shown exactly as typed, because somebody has to dial it. The region a
  bare number is read in is a club setting, so another club is not assumed to be in the US.
- **Sections/Files Affected**: requirements.txt (phonenumbers), apps/ops/templatetags/labels.py
  (phone), apps/accounts/models.py (license_class), apps/accounts/views_members.py,
  apps/ops/views_settings.py, config/club.example.yaml, templates/accounts/members.html and five
  other templates showing a number, apps/accounts/tests/test_directory.py.
- **Nature of Contribution**: Design and code by the assistant, to the advisor's specification.
- **Human Review Status**: Pending the advisor's look. 278 tests pass, the accessibility sweep
  passes, and the four guards pass.
- **Git Hash**: 68e6c7c

## [2026-09-19 16:52 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Three layout corrections to the members directory, from the advisor
  reading it on a wide screen. The page was capped at 72rem, which is a measure for reading
  prose, so a table eleven columns wide scrolled sideways inside a half-empty window; a page
  whose point is a wide table now takes the window it is given, through a block in the base
  template rather than a rule aimed at one page. Phone numbers no longer wrap, because a number
  broken across two lines reads as two numbers and it is the column somebody copies by eye to
  dial; the same holds for a callsign. And the license class shows its letter rather than its
  word, which is what the club already reads on every roster and saves the column most of its
  width. The filter keeps the full words, where there is room for them.
- **Sections/Files Affected**: templates/base.html (a main_class block), static/css/app.css,
  templates/accounts/members.html, apps/accounts/tests/test_directory.py.
- **Nature of Contribution**: Code and tests by the assistant, at the advisor's direction.
- **Human Review Status**: Pending the advisor's look. 279 tests pass, the accessibility sweep
  passes at both widths, and the four guards pass.
- **Git Hash**: c7b019a

## [2026-09-19 17:07 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Two things the advisor asked for while testing the members directory. A
  club callsign was reading **U** in the Class column, which is not true: the FCC issues no
  operator class to a club, because a club is not a person, so a club's record carries a
  callsign and a status and an empty class field. That empty field is also what "never checked"
  looks like, so the letter is now C only where the FCC has a matched record and no class, and
  U everywhere else. C sorts below the ladder and above the unlicensed, has its own entry in
  the class filter, and is counted on the rosters a Provisional member sees. RACES and
  military-recreation licenses carry no operator class either and will read C as well; all
  three are a station rather than a person, which is what the letter says.

  Second, a profile page now **reads**. Clicking a name opens the record with no control on it
  that changes anything, and an **Edit profile** button appears for a reader entitled to change
  something; every form that was on that page moved to an edit page of its own. The same split
  applies to a member's own profile, and a member under 18 has no edit page, because their
  guardian edits the account while acting for them. The advisor's reason, 2026-09-19: it "will
  allow for potential public views of profiles, as well as make it more difficult to
  accidentally change information". The name and callsign in the corner of the sidebar now open
  the profile, with the acting level beside it as its own link.
- **Sections/Files Affected**: apps/accounts/models.py (license_letter), apps/accounts/account.py
  (profile_rows, may_manage), apps/accounts/views.py (profile, profile_edit),
  apps/accounts/views_members.py (member_detail read-only, member_edit), apps/accounts/urls.py,
  config/urls.py, apps/events/services/roster.py, templates/accounts/{member_detail,member_edit,
  profile,profile_edit}.html, templates/base.html, static/css/app.css, docs/INTERFACE.md,
  docs/REQUIREMENTS.md (FR-6, FR-67), tools/a11y/test_axe.py, and the tests across
  apps/accounts and apps/credentials.
- **Nature of Contribution**: Code, tests, and documentation by the assistant, at the advisor's
  direction.
- **Human Review Status**: Pending the advisor's look. 289 tests pass, the accessibility sweep
  passes for all eight roles at both widths, and the four guards pass.
- **Git Hash**: 6ac4f41

## [2026-09-19 17:22 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Give a RACES station R and a military recreation station M, keeping C for
  a club, at the advisor's instruction. The FCC issues an operator class to a person only, so
  all three hold a callsign with the class field empty and nothing else in the record tells them
  apart; the applicant type (EN24 in the FCC's entity file) does, and it was not being imported.
  The import now carries it into the local table and into each member's license record, the
  letter follows from it, and a matched record whose applicant type is still blank reads C,
  which is what nearly every one of them is and what every row holds until the next import.
  The three sort below the license ladder in that order and each has its own entry in the
  directory's class filter; the rosters a Provisional member sees count them separately. Where
  a page has room for words rather than a letter it now says "club station", "RACES station",
  or "military recreation station" in place of the empty class.
- **Sections/Files Affected**: apps/credentials/{models,uls,services}.py and migration 0004,
  apps/accounts/models.py (license_letter), apps/accounts/views_members.py (rank and filters),
  apps/events/services/roster.py, templates/accounts/{member_detail,member_edit,profile}.html,
  docs/REQUIREMENTS.md (FR-14, FR-67), and the tests in apps/accounts and apps/credentials.
- **Nature of Contribution**: Code, tests, and documentation by the assistant, at the advisor's
  direction. The applicant type codes were read from the FCC's own ULS code definitions.
- **Human Review Status**: Pending the advisor's look. 292 tests pass, the accessibility sweep
  passes for all eight roles at both widths, and the four guards pass.
- **Git Hash**: ca060f4

## [2026-09-19 17:45 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Finish the read-only profile. The notification switches, the browser-
  notification controls, and the close-my-account form were still on the profile page, which the
  advisor caught on the live site: "I'm seeing editable options even on the read-only profile.
  Those should only show up when you press Edit profile." All three moved to the edit page, and
  the button says what it opens. The profile now shows what reaches you as plain text, read from
  the same place the switches are built from, so the two cannot drift. The password and
  two-step-verification links stay on the profile: they lead somewhere rather than change
  anything, and a member under 18, who has no edit page, reaches their password through them.
- **Sections/Files Affected**: apps/accounts/views.py (a shared `_preferences`, and the
  preference forms now return to the edit page), apps/accounts/views_push.py,
  templates/accounts/profile.html, templates/accounts/profile_edit.html, and the tests in
  apps/accounts and apps/comms.
- **Nature of Contribution**: Code and tests by the assistant, at the advisor's direction.
- **Human Review Status**: Pending the advisor's look. 292 tests pass, the accessibility sweep
  passes for all eight roles at both widths, and the four guards pass.
- **Git Hash**: 10c2edd

## [2026-09-19 18:13 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: One profile page instead of two, at the advisor's instruction: "These
  should be the same thing. i.e. [/me/] should redirect to [/members/1/] ... That way there is a
  more unified codebase and interface." `/me/` and `/me/edit/` are now redirects to your own
  member page and its edit page, which keeps every existing link, menu entry, and bookmark
  working. A member may always read and edit their own record whatever else they may see, and
  the sections that are yours alone (the FCC name question, the members you act for, what
  reaches you, your password, closing your account) appear on that page only when it is your
  own. Two templates were deleted rather than kept in step by hand. Saving the account form now
  returns to the page that reads, which is what the interface rules already said.
- **Sections/Files Affected**: apps/accounts/views.py (profile and profile_edit are redirects),
  apps/accounts/views_members.py (self-access, preferences, the minor guard),
  templates/accounts/member_detail.html and member_edit.html, templates/base.html (which menu
  entry is current), templates/accounts/profile.html and profile_edit.html deleted, and the
  tests across apps/accounts, apps/comms, apps/credentials, apps/ops and tools/a11y.
- **Nature of Contribution**: Code, tests, and documentation by the assistant, at the advisor's
  direction.
- **Human Review Status**: Pending the advisor's look. 293 tests pass, the accessibility sweep
  passes for all eight roles at both widths, and the four guards pass.
- **Git Hash**: 12f894f

## [2026-09-19 18:36 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The requirements side of the day's reconciliation. FR-6 now describes a
  page that reads with the editing behind a button, and a member's own profile being that same
  page; FR-13 describes the rebuilt directory; FR-14 adds the FCC applicant type; FR-67 gives a
  club, a RACES station and a military recreation station their letters; FR-71 says where the
  notification switches live; FR-118 records why a deleted account keeps an emptied row. The
  advisor's words are quoted with their date in each case.
- **Sections/Files Affected**: docs/REQUIREMENTS.md (FR-6, FR-13, FR-14, FR-67, FR-71, FR-118).
- **Nature of Contribution**: Documentation by the assistant, at the advisor's direction.
- **Human Review Status**: Pending the advisor's look.
- **Git Hash**: e6f8886

## [2026-09-19 18:53 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Three faults the advisor found while testing a member's edit page. The
  page never said why the name fields are absent: the partial looked for a `subject` variable
  that neither including page passed, so the one sentence explaining that the name is the FCC's
  has never reached anybody; it now reads the form's own instance and names the callsign, the
  name on file, and what to set instead. The card over a member's own fields was headed "Club
  position", which is what an officer may set on somebody else; on your own account it is
  "Details". And the import dropped the middle initial (EN10 in the FCC's entity record),
  although FR-4 asks for the licensee's first, middle, and last name, so KC2NMC's MARY L WEST
  reached the account as "Mary West"; it is carried through the staging table, the local table,
  the callsign lookup, the member's confirmation, and the nightly refresh.
- **Sections/Files Affected**: templates/accounts/_account_form.html,
  apps/accounts/views_members.py, apps/accounts/services.py, apps/credentials/{models,uls,
  services}.py and migration 0005, and the tests in apps/accounts and apps/credentials.
- **Nature of Contribution**: Code and tests by the assistant, at the advisor's direction.
- **Human Review Status**: Pending the advisor's look. 295 tests pass, the accessibility sweep
  and the four guards pass.
- **Git Hash**: 7e779cb

## [2026-09-19 19:22 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Four changes the advisor asked for while testing. The name is printed in
  the three fields it is stored in, read-only where a callsign makes it the FCC's, with the
  explanation and the sysadmin-override note beside it rather than at the foot of the form; the
  License card names the licensee as the FCC holds it; both pages head themselves with the name
  the person is called by, the preferred name where there is one; and the edit page has one
  Details card holding what cannot be changed as text and what can as fields, instead of two
  cards with the same heading. Then two rules narrowed: forcing a callsign lookup is a
  sysadmin's, because the nightly import refreshes every licensed member anyway and the page now
  says so; and only a sysadmin has acting levels at all, the page answering 404 to everybody
  else, because an officer rehearsing as a member is a way to lose an afternoon.
- **Sections/Files Affected**: apps/accounts/{account,acting,views_acting,views_members}.py,
  apps/credentials/models.py, templates/accounts/{_account_form,member_detail,member_edit}.html,
  docs/REQUIREMENTS.md (FR-8, FR-14), docs/TECHNICAL_REQUIREMENTS.md (TR-43), tools/a11y, and
  the tests across apps/accounts.
- **Nature of Contribution**: Code, tests, and documentation by the assistant, at the advisor's
  direction.
- **Human Review Status**: Pending the advisor's look. 298 tests pass, the accessibility sweep
  passes for all eight roles at both widths, and the four guards pass.
- **Git Hash**: 3bb9b67

## [2026-09-19 19:51 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Who may appoint whom, to the advisor's rule of 2026-09-19: "Faculty
  advisors should be able to appoint officers, members, and below. Officers should be able to
  appoint members, and below." Written against capabilities rather than a ladder, so a club that
  invents a group gets the same rule: a group is yours to grant when everything it grants is
  something you already hold and it does not hold everything you do, and an account is yours to
  change when what it holds is a proper subset of what you hold. The second half is what stops
  an officer editing the advisor's account and dropping them to Member. The bounded capability
  reaches the existing groups through a data migration, because the configuration import leaves
  an existing group alone by design. An account with no access now says why: closed at its own
  request with the date, or removed by a named person with their reason, so whoever restores it
  knows which of the two they are undoing; restoring clears a closure request. The last account
  that can run the site is protected by the sysadmin flag rather than by the capability, which
  officers now hold.
- **Sections/Files Affected**: apps/ops/groups.py (assignable_groups, may_set_access),
  apps/accounts/{account,services,views_members}.py, migration 0014,
  templates/accounts/{member_detail,member_edit}.html, config/club.example.yaml,
  docs/REQUIREMENTS.md (FR-91), and the tests across apps/accounts.
- **Nature of Contribution**: Code, tests, and documentation by the assistant, at the advisor's
  direction.
- **Human Review Status**: Pending the advisor's look. 306 tests pass, the accessibility sweep
  and the four guards pass.
- **Git Hash**: 3ceea88

## [2026-09-19 20:25 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Where an account stands with the club, as the advisor settled it on
  2026-09-19. Four statuses on one axis, Provisional, Active, Closed and Suspended, all of them
  on the members list, because an account somebody could still use should never be off it.
  Archiving is a flag beside the status rather than a value of it: the record keeps the status
  it went in with, and taking it out of the archive and letting the person back in are two acts.
  Closed and Suspended part company: a member who asked to leave is readmitted by an officer, a
  member somebody suspended by a faculty advisor, through a new capability. Suspension is a fact
  on the account now, with who did it and why, so the person deciding can read it. The archive
  page is folded into the members list as a filter, its URL forwarding, its audit row kept. The
  list gained a Status column for officers and above, sortable down the list rather than down
  the alphabet, with archived shown to whoever may read the archive and deleted to a sysadmin.
  The sidebar tells everybody the level they hold; only a sysadmin's is a link.
- **Sections/Files Affected**: apps/accounts/{models,services,acting,views_members}.py and
  migrations 0015 and 0016, apps/ops/{capabilities,groups}.py and migration 0005,
  templates/accounts/{members,member_detail,member_edit}.html, templates/base.html,
  templates/accounts/archive.html deleted, config/club.example.yaml, seed_demo, tools/a11y, and
  the tests across apps/accounts and apps/ops.
- **Nature of Contribution**: Code and tests by the assistant, at the advisor's direction.
- **Human Review Status**: Pending the advisor's look. 307 tests pass, the accessibility sweep
  and the four guards pass.
- **Git Hash**: 70a2cd5

## [2026-09-19 20:28 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The requirements and the technical requirements catch up with the status
  work: FR-13a describes the four statuses and the archive flag beside them, FR-11 says an
  officer may readmit somebody who asked to leave, FR-91 says an officer suspends and a faculty
  advisor lifts, FR-125 says an account is closed or suspended before it is archived and that
  taking a record out of the archive leaves its status alone, and TR-43 records that the sidebar
  names everybody's level while only a sysadmin's is a link.
- **Sections/Files Affected**: docs/REQUIREMENTS.md (FR-11, FR-13a, FR-91, FR-125),
  docs/TECHNICAL_REQUIREMENTS.md (TR-43).
- **Nature of Contribution**: Documentation by the assistant, at the advisor's direction.
- **Human Review Status**: Pending the advisor's look.
- **Git Hash**: f923885

## [2026-09-19 20:42 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Filters that take more than one answer, and the archive as a flag of its
  own. Each drop-down is now a disclosure holding a checkbox per value: no script, no
  ctrl-clicking, it opens from the keyboard, the summary says what is ticked, and it submits the
  same name twice, so every link anybody already has still means what it meant. Officers and
  above start with every status ticked but Deleted, which is a sysadmin's and stays unticked so
  that ordinary work is not cluttered with it. The archive stopped being a status: it is a
  column and a filter beside the status, ticked to "not archived" to begin with, and shown only
  to a reader who may read an archived record at all. The guard that forbids a capability
  deriving from a club position learned that narrowing a list by position is not that.
- **Sections/Files Affected**: apps/accounts/views_members.py, apps/accounts/models.py
  (status_label), templates/accounts/_filter.html (new) and members.html, static/css/app.css,
  templates/base.html, templates/accounts/member_edit.html, tools/a11y, and the tests across
  apps/accounts.
- **Nature of Contribution**: Code and tests by the assistant, at the advisor's direction.
- **Human Review Status**: Pending the advisor's look. 314 tests pass, the accessibility sweep
  and the four guards pass.
- **Git Hash**: 0c55a5f

## [2026-09-19 20:54 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Two narrowings from the advisor's testing. Access is one choice from a
  drop-down rather than a set of tick boxes, so an account holds one level or none, with "No
  access" among the answers; the field still offers only what this person may grant. And setting
  a club position became the faculty advisor's: an officer says who is a member, while who holds
  which office is the advisor's to record. The card over somebody else's fields is called
  Manage, since "Club position" no longer describes what is in it.
- **Sections/Files Affected**: apps/accounts/account.py, apps/accounts/views_members.py,
  migration 0017, config/club.example.yaml, docs/REQUIREMENTS.md (§2.3, FR-91), and the tests
  across apps/accounts.
- **Nature of Contribution**: Code, tests, and documentation by the assistant, at the advisor's
  direction.
- **Human Review Status**: Pending the advisor's look. 316 tests pass, the accessibility sweep
  and the four guards pass.
- **Git Hash**: e5e8d84

## [2026-09-19 21:14 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Four more narrowings and two pieces of polish from the advisor's testing.
  An officer may promote but never demote: the Access list only goes up for somebody who cannot
  lift a suspension, and "No access" is not among their answers, because shutting an account out
  is the suspension, where the act carries a reason and somebody answerable for lifting it.
  Taking an address away, its confirmation, or its club mail is nobody else's business: a new
  capability covers those three, an officer keeps adding an address and confirming one, and a
  member sets their own club mail. The dashboard stopped saying that mail is being sent, which
  is the ordinary state and whose outbox is in the menu, and the events link moved under
  Upcoming events where it belongs. The filter panels became an exclusive set, so opening one
  closes the last rather than overlapping it, and their checkboxes sit beside their words.
- **Sections/Files Affected**: apps/ops/{capabilities,groups}.py, apps/accounts/account.py,
  apps/accounts/views_addresses.py, migrations accounts/0018 and ops/0006,
  templates/accounts/{_addresses,_filter}.html, templates/ops/dashboard.html,
  static/css/app.css, config/club.example.yaml, and the tests across apps/accounts.
- **Nature of Contribution**: Code and tests by the assistant, at the advisor's direction.
- **Human Review Status**: Pending the advisor's look. 317 tests pass, the accessibility sweep
  and the four guards pass.
- **Git Hash**: e5135df

## [2026-09-19 21:32 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Two things from the advisor's testing. A member who left and comes back
  gets their own record instead of a second account: an address that belongs to a closed or
  archived account is recognised when an officer sends an invitation and when the person joins
  through an entry link, and completing either brings the record back with its callsign,
  agreements and history. A suspended account is not a returning member, and the refusal says
  that a faculty advisor lifts a suspension. And a page the session may not open is now the
  club's own page rather than the server's bare Not Found: it says the level you are acting at
  and offers Home and the level page, which is what happens when somebody drops a level while
  standing on a sysadmin page. The menu entry reads Archived members.
- **Sections/Files Affected**: apps/accounts/{services,entry,views,views_entry}.py,
  templates/{404,403}.html (new), templates/base.html, and the tests in apps/accounts and
  apps/ops.
- **Nature of Contribution**: Code and tests by the assistant, at the advisor's direction.
- **Human Review Status**: Pending the advisor's look. 324 tests pass, the accessibility sweep
  and the four guards pass.
- **Git Hash**: 1db41d4

## [2026-09-19 21:56 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The greeting now names the member as the club does, callsign and all. The
  filter panels' checkboxes were being stretched across their rows by the rule that makes the
  search box grow, which left every label ragged down the right edge; the rule is scoped to the
  search input, and a browser test measures the rows rather than trusting the markup. The
  Archived column is gone, since the archive is a menu entry and a filter. A faculty advisor can
  now close an account outright, and archiving one that is still open closes it in the same act,
  so filing a member who has left takes one action and no suspension; the card holding those is
  called Leaving the club and appears only when there is something in it. Deletion was already a
  sysadmin's alone.
- **Sections/Files Affected**: templates/ops/dashboard.html, static/css/app.css,
  apps/accounts/{models,services,views_members}.py and migration 0019,
  templates/accounts/{members,member_edit}.html, tools/a11y/test_filter_layout.py (new), and
  the tests in apps/accounts.
- **Nature of Contribution**: Code and tests by the assistant, at the advisor's direction.
- **Human Review Status**: Pending the advisor's look. 325 tests pass, the accessibility sweep
  and the four guards pass.
- **Git Hash**: b58fd2a

## [2026-09-19 22:11 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Four from the advisor's testing. A join notice names the person as the
  club does, callsign in the subject line. A button on the profile's edit page sends a test
  notification to every device that has allowed one, and says what happened, because browser
  notifications depend on a permission, a service worker and a push service that may be asleep,
  and the only honest way to know they work is to send one. Announcements reach active members
  only. And the fault behind that last one: an account closed and then given a level again read
  Closed while being perfectly usable, because the status flags and the group list could
  disagree; granting access now clears them.
- **Sections/Files Affected**: apps/comms/defaults.py, apps/comms/announce.py,
  apps/accounts/{services,views_push,urls}.py, templates/accounts/member_edit.html,
  templates/comms/announce.html, and the tests in apps/accounts and apps/comms.
- **Nature of Contribution**: Code and tests by the assistant, at the advisor's direction.
- **Human Review Status**: Pending the advisor's look. 328 tests pass, the accessibility sweep
  and the four guards pass.
- **Git Hash**: 72d50d6

## [2026-09-19 22:17 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The requirements catch up with a long testing round: FR-126 (an officer
  adds and confirms an address, and correcting one is a sysadmin's) and FR-13a (four statuses,
  the archive as a flag, filters that take a set) are new; FR-3 gains the member who comes back
  to their own record, FR-11 and FR-125 the closing and archiving rules, FR-75 the active-members
  audience, FR-112 the test notification, FR-14 the middle initial, FR-91 the promote-only rule.
  INTERFACE.md gains what a refusal looks like and what a filter is. Three amendments made
  earlier today had been lost by a script that raised on its last anchor and wrote nothing, so
  they were rewritten.
- **Sections/Files Affected**: docs/REQUIREMENTS.md (FR-3, FR-11, FR-13a, FR-14, FR-75, FR-91,
  FR-112, FR-125, FR-126), docs/INTERFACE.md.
- **Nature of Contribution**: Documentation by the assistant, at the advisor's direction.
- **Human Review Status**: Pending the advisor's look.
- **Git Hash**: 228518c

## [2026-09-19 22:29 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The product is **ARCOps** everywhere it is read, including its own
  repository: `w3usr/arcops` is renamed `w3usr/ARCOps` (GitHub redirects the old name, so every
  clone and link keeps working), and the links, the clone line, the tree diagrams and the
  product URL follow it. Three lowercase uses stay and now say why: two signing salts and a
  calendar UID, which are identifiers rather than the product's name, and changing them would
  invalidate every outstanding verification link and every calendar entry already subscribed.
- **Sections/Files Affected**: apps/ops/branding.py, README.md, CLAUDE.md, docs/NAME.md,
  docs/TECHNICAL_REQUIREMENTS.md, and comments in apps/accounts/{addresses,entry}.py and
  apps/events/views_member.py.
- **Nature of Contribution**: Edit by the assistant, at the advisor's direction.
- **Human Review Status**: Pending the advisor's look. 328 tests pass, the accessibility sweep
  and the four guards pass.
- **Git Hash**: 49d2fe6

## [2026-09-19 22:54 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The weekly FCC import was failing with "database is locked" thirty-three
  minutes in, and the full traceback named the cause: the winners are written while the staging
  table is still being read, and SQLite refuses a write on a connection whose own read cursor is
  open, this database opening its transactions in IMMEDIATE mode. No other process was involved,
  which is why the busy timeout never helped. The walk now reads a slice at a time by key, so no
  cursor is open when a batch is written; a test walks more rows than one slice and more than
  one write batch. And the roster is one page, as the advisor decided: the Archived column
  returns for whoever may read an archived record, an officer gets neither it nor the filter,
  the second menu entry is gone, and the filter reads "Archived".
- **Sections/Files Affected**: apps/credentials/uls.py, apps/accounts/views_members.py,
  templates/accounts/members.html, templates/base.html, and the tests in apps/accounts and
  apps/credentials.
- **Nature of Contribution**: Code and tests by the assistant, at the advisor's direction.
- **Human Review Status**: Pending the advisor's look. 329 tests pass, the accessibility sweep
  and the four guards pass.
- **Git Hash**: 73133fa

## [2026-09-19 23:13 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The documents follow the last three changes: FR-13a and FR-125 describe
  one roster with the Archived column for whoever may read an archived record and no second menu
  entry; TR-13 records that the staging table is walked a slice at a time and why, which is the
  fault that had been failing the weekly import; and docs/NAME.md records the repository's
  rename to ARCOps together with the three identifiers that keep the lower-case spelling.
- **Sections/Files Affected**: docs/REQUIREMENTS.md (FR-13a), docs/TECHNICAL_REQUIREMENTS.md
  (TR-13), docs/NAME.md.
- **Nature of Contribution**: Documentation by the assistant, at the advisor's direction.
- **Human Review Status**: Pending the advisor's look.
- **Git Hash**: f8a9c13

## [2026-09-19 23:22 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The calendar feed's address changed on every page load, which the advisor
  noticed on his phone. It was a signed string, and Django's signatures carry a timestamp, so
  every view produced a different address and left another live credential behind; a member
  could not tell a new address from a leaked one, and there was nothing to revoke. The address
  is now a key on the account, generated once, the same every time it is read, and the
  signed addresses handed out before today keep working so nobody's subscription stops.
- **Sections/Files Affected**: apps/accounts/models.py and migration 0020,
  apps/events/views_member.py, apps/events/tests/test_roster.py.
- **Nature of Contribution**: Code and tests by the assistant, at the advisor's direction.
- **Human Review Status**: Pending the advisor's look. 330 tests pass, the accessibility sweep
  and the four guards pass.
- **Git Hash**: da4a8e3

## [2026-09-19 23:30 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The other half of a calendar address that is a key rather than a
  signature: a member can replace one that has been shared by accident, behind a disclosure that
  says what it costs, and the old address stops working at once. Audited.
- **Sections/Files Affected**: apps/events/{views_member,urls}.py,
  templates/events/my_schedule.html, apps/events/tests/test_roster.py.
- **Nature of Contribution**: Code and tests by the assistant, at the advisor's direction.
- **Human Review Status**: Pending the advisor's look. 331 tests pass, the accessibility sweep
  and the four guards pass.
- **Git Hash**: d84cefd

## [2026-09-19 23:36 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The manifest declares each icon at its real pixel size, read from the
  PNG's own header rather than trusted from a file name, and says it once where the shipped
  configuration points twice at the same file. A browser decides whether a site can be installed,
  and which icon to put on a home screen, from those declarations, and the club's 512px seal was
  being passed over because it was declared "any", which means scalable and is not true of a PNG.
  Also in this entry: the weekly FCC import completed for the first time since the applicant type
  was added, 1,602,418 callsigns written, with the self-lock fixed.
- **Sections/Files Affected**: apps/ops/views.py, apps/ops/tests/test_health_and_import.py.
- **Nature of Contribution**: Code and tests by the assistant, at the advisor's direction.
- **Human Review Status**: Pending the advisor's look. 332 tests pass, the accessibility sweep
  and the four guards pass.
- **Git Hash**: e179ba6

## [2026-09-19 23:45 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The footer's last line was under the phone's navigation bar in the
  installed app and fine in the browser. An installed app has no browser chrome, so the system's
  own bars sit over the page, and a page shorter than the screen puts its footer exactly where
  the navigation bar is. The page now says it is drawn edge to edge and pays for every edge that
  meets a system bar: the footer, the top bar, and the drawer's foot. In a browser those insets
  are zero and nothing moves.
- **Sections/Files Affected**: templates/base.html (viewport-fit), static/css/app.css.
- **Nature of Contribution**: Code by the assistant, at the advisor's direction.
- **Human Review Status**: Pending the advisor's look on a phone. 332 tests pass, the
  accessibility sweep at both widths and the four guards pass.
- **Git Hash**: 26bc37e

## [2026-09-19 23:50 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The documents follow the evening's last batch: FR-59 records that the
  calendar address is a key on the account, shown unchanged and replaceable, with the older
  signed addresses still accepted; FR-96 records the manifest's real icon sizes and the edge-to-
  edge layout that pays for the system's bars; INTERFACE.md says the same for any page.
- **Sections/Files Affected**: docs/REQUIREMENTS.md (FR-59, FR-96), docs/INTERFACE.md.
- **Nature of Contribution**: Documentation by the assistant, at the advisor's direction.
- **Human Review Status**: Pending the advisor's look.
- **Git Hash**: 9353502

## [2026-09-19 23:55 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The footer was still cut off in the installed app after the safe-area
  padding, because the phone reports no inset: its navigation bar is beside the window rather
  than over it, so `env(safe-area-inset-bottom)` is zero and the padding added nothing. What was
  wrong is the unit: `100dvh` in an installed app on Android can be the whole screen, including
  the strip the navigation bar occupies, so the page was pinned to a height that is not visible.
  The layout uses `100svh`, the small viewport, which can only ever be smaller than what is
  shown. The safe-area padding stays, because it is what an iPhone's home indicator needs, and
  the service worker's cache name is bumped so an installed copy takes the new stylesheet.
- **Sections/Files Affected**: static/css/app.css, static/sw.js.
- **Nature of Contribution**: Code by the assistant, at the advisor's direction.
- **Human Review Status**: Pending the advisor's look on the phone. 332 tests pass, the
  accessibility sweep and the four guards pass.
- **Git Hash**: 73bba40

## [2026-09-20 00:00 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The authoring club's name in the footer's credit line is a link to its own
  page. It is the software's attribution rather than the installation's, so the address lives
  beside the product's other constants and points at the club that wrote the software wherever
  a copy is run.
- **Sections/Files Affected**: apps/ops/branding.py, templates/base.html,
  apps/ops/tests/test_interface.py.
- **Nature of Contribution**: Code and a test by the assistant, at the advisor's direction.
- **Human Review Status**: Pending the advisor's look. 333 tests pass, the accessibility sweep
  and the four guards pass.
- **Git Hash**: 43911b3

## [2026-09-20 00:12 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Two faults the advisor met in acceptance testing. First, confirming a
  password before adding two-factor or a passkey refused the correct password: the sign-in
  library rebuilds the credentials from its own username field and the primary row of its
  address table, and this installation has neither, so it had nothing to look the account up
  by. The adapter now hands it the account's own key. Second, the installed app's home-screen
  icon sat small on a white tile, because the manifest declared no icon a phone may crop to its
  own shape; it now offers one, and the club's configuration supplies it.
- **Sections/Files Affected**: apps/accounts/adapter.py, apps/accounts/tests/test_reauthenticate.py,
  apps/ops/views.py, apps/ops/config.py, apps/ops/views_settings.py, config/club.example.yaml,
  config/assets/club-logo-maskable.svg, apps/ops/tests/test_health_and_import.py.
- **Nature of Contribution**: Diagnosis, code, a placeholder icon, and tests by the assistant,
  from the advisor's two reports.
- **Human Review Status**: Pending the advisor's look on his own phone. 338 tests pass, with
  the accessibility sweep and the four guards.
- **Git Hash**: 3784623

## [2026-09-20 00:34 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: `/reconcile` after the evening's fixes, and three more faults the advisor
  found while it ran. The documents follow the re-authentication fix, the viewport unit, the
  maskable icon and the footer credit. Then: the sign-in library's own pages now use the site's
  buttons, because two of its controls in a row read as one underlined phrase; the class filter
  drops the three station types, since a member account belongs to a person; and the status
  panel starts with nothing ticked, like every other panel.
- **Sections/Files Affected**: docs/REQUIREMENTS.md (FR-13, FR-96), docs/TECHNICAL_REQUIREMENTS.md
  (TR-17), docs/INTERFACE.md, docs/NAME.md, templates/allauth/elements/button.html (new),
  static/css/app.css, apps/accounts/views_members.py, apps/accounts/tests/test_directory.py,
  apps/accounts/tests/test_reauthenticate.py.
- **Nature of Contribution**: Documentation, code and tests by the assistant, from the advisor's
  reports; decisions his.
- **Human Review Status**: Pending the advisor's look. 339 tests pass, with the accessibility
  sweep and the four guards.
- **Git Hash**: de77810

## [2026-09-20 00:41 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Take this installation's server paths out of the public technical
  requirements, on the advisor's instruction. The environment file, the database directory, the
  backup directory and the club overlay were each named by their full path on the club's own
  server; each now describes what it is and leaves its location to whoever runs the
  installation.
- **Sections/Files Affected**: docs/TECHNICAL_REQUIREMENTS.md (the deployment diagram, TR-2,
  TR-19, the backup entry, TR-41).
- **Nature of Contribution**: Edit by the assistant.
- **Human Review Status**: Pending the advisor's look; the repository guards and 339 tests pass.
- **Git Hash**: 45763c8

## [2026-09-20 00:52 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The invite page told officers that a member under 18 with no address of
  their own "signs in with an address made from the guardian's". Nothing has done that since the
  account stopped being its own address; the advisor caught the sentence. The help text now says
  what happens: with an address of their own a minor signs in read-only, and with none they do
  not sign in and the guardian acts for them.
- **Sections/Files Affected**: apps/accounts/views.py (InviteForm help text),
  apps/accounts/tests/test_phase7.py.
- **Nature of Contribution**: Edit and a test by the assistant, from the advisor's reading.
- **Human Review Status**: Pending the advisor's look. 340 tests, the accessibility sweep and
  the four guards pass.
- **Git Hash**: ca4420a

## [2026-09-20 01:15 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Give every message the call-to-action button the password reset already
  had. The mail layout now draws a paragraph holding nothing but one link as a filled block in
  the club's color, which reads the shape of the message rather than a marker the template
  editor's sanitiser would strip. The templates whose link sat mid-sentence were rewritten to
  put it on a line of its own; the two that offer a choice, and the two that list links inside
  list items, keep theirs as links.
- **Sections/Files Affected**: apps/comms/layout.py, apps/comms/defaults.py (ten templates),
  apps/comms/tests/test_messages.py, apps/accounts/tests/test_addresses.py,
  docs/REQUIREMENTS.md (FR-78).
- **Nature of Contribution**: Code, template wording and tests by the assistant, from the
  advisor's request.
- **Human Review Status**: Rendered and checked by eye against the advisor's own screenshots;
  340 tests, the accessibility sweep and the four guards pass.
- **Git Hash**: 450ae4f

## [2026-09-20 01:25 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: `/reconcile`. Two documents had over-generalised yesterday's filter rule:
  four of the five panels start empty, but the Archive panel opens with "Not archived" ticked
  and should, because the unnarrowed roster does leave the archive out. FR-13 and INTERFACE.md
  now name that exception and give the test behind it. FR-78 gained a line saying the mail's
  call-to-action block belongs to the mail, with a test that the copy read in the application
  keeps its link as a link.
- **Sections/Files Affected**: docs/REQUIREMENTS.md (FR-13, FR-78), docs/INTERFACE.md,
  apps/comms/tests/test_messages.py.
- **Nature of Contribution**: Reconciliation and writing by the assistant.
- **Human Review Status**: Pending the advisor's look. 341 tests, the accessibility sweep and
  the four guards pass.
- **Git Hash**: 329ed13

## [2026-09-20 01:33 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Say in §2.3 that an account carries one club position, which is the fact
  behind the advisor holding two offices and the list being able to show only one. The
  installation's own list is configuration and lives in the private repository.
- **Sections/Files Affected**: docs/REQUIREMENTS.md (§2.3).
- **Nature of Contribution**: Edit by the assistant, from the advisor's report.
- **Human Review Status**: Pending the advisor's look; the guards and tests pass.
- **Git Hash**: 19d284b

## [2026-09-20 01:55 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: A member's club position becomes a set of positions. Neither side was
  meant to be exclusive: one person is both the faculty advisor and the club's license trustee,
  and a club with a board elects several members to the same seat. The field, the edit form, the
  directory column, its filter and its sort, the profile page, the roster, the CSV export and the
  audit of what an officer may set all follow, and the permission matrix in the requirements was
  corrected where it still showed officers setting a position.
- **Sections/Files Affected**: apps/accounts/models.py,
  apps/accounts/migrations/0021_positions_are_a_list.py, apps/ops/migrations/0007_…,
  apps/accounts/account.py, apps/accounts/views_members.py, apps/accounts/services.py,
  apps/accounts/admin.py, apps/ops/capabilities.py, apps/ops/templatetags/labels.py,
  apps/credentials/views_reports.py, templates/accounts/members.html,
  templates/accounts/roster.html, docs/REQUIREMENTS.md (§2.3, §2.5, the profile-field table),
  and the tests.
- **Nature of Contribution**: Design change, code, migration and tests by the assistant, from
  the advisor's instruction.
- **Human Review Status**: Pending the advisor's look. 345 tests, the accessibility sweep and
  the four guards pass.
- **Git Hash**: eff7079

## [2026-09-20 02:10 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: `/reconcile`. The pages say Coverage where they said "health", which the
  advisor found too medical; the word matches Covered, which is what a slot with enough people
  already reads. The sweep after the positions change also removed the singular position filter
  that had no callers, renamed the CSV column and the table heading to the plural, and told the
  Settings help that a member may hold several offices.
- **Sections/Files Affected**: templates/events/{detail,list,health_overview}.html,
  apps/ops/views_settings.py, apps/ops/templatetags/labels.py, apps/credentials/views_reports.py,
  apps/accounts/views_members.py, templates/accounts/{members,roster}.html,
  docs/REQUIREMENTS.md (FR-66, §3.7), apps/events/tests/test_roster.py.
- **Nature of Contribution**: Vocabulary change and tidying by the assistant, from the advisor's
  question.
- **Human Review Status**: Pending the advisor's look. 345 tests, the accessibility sweep and the
  four guards pass.
- **Git Hash**: 5d5c6ca

## [2026-09-20 02:35 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: What a faculty advisor may set on an account: the category, names and
  student fields; the club positions, including on their own account; and access up to their own
  level, which is a new capability ("appoint a peer") rather than a ladder written into the code.
  Sysadmin stays a sysadmin's to tick. The advisor chose where the ladder stops when asked.
- **Sections/Files Affected**: apps/ops/capabilities.py, apps/ops/groups.py,
  apps/accounts/account.py, config/club.example.yaml,
  apps/accounts/migrations/0022_advisors_set_category_and_appoint_peers.py,
  apps/ops/migrations/0008_advisors_appoint_peers.py, docs/REQUIREMENTS.md (§2.3, §2.5, FR-91),
  and the appointment, form and member tests.
- **Nature of Contribution**: Permission design, code, migration and tests by the assistant, from
  the advisor's instruction and his answer on where the ladder stops.
- **Human Review Status**: Pending the advisor's look. 347 tests, the accessibility sweep and the
  four guards pass.
- **Git Hash**: da7e8b9

## [2026-09-20 02:50 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The offices a member holds are listed one per line, in the table and on
  the profile page, the way the addresses beside them are. The filter hands the cell a list and
  the cell decides the layout.
- **Sections/Files Affected**: apps/ops/templatetags/labels.py, apps/accounts/account.py,
  templates/accounts/{members,roster,member_detail,_account_readonly}.html,
  apps/accounts/tests/test_directory.py.
- **Nature of Contribution**: Interface change by the assistant, from the advisor's request.
- **Human Review Status**: Pending the advisor's look. 347 tests, the accessibility sweep and the
  four guards pass.
- **Git Hash**: 7c7a4c9

## [2026-09-20 02:50 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Three from the advisor's testing. Closing an account moves into the Danger
  zone beside suspending and deleting, and the card it used to live in is gone; archiving is
  offered only once an account is closed or suspended, since it is the second step; and raising
  the level a session acts at now goes through the sign-in library's Confirm Access, which takes
  a passkey as readily as a password, so the page carries no password field of its own.
- **Sections/Files Affected**: templates/accounts/member_edit.html,
  templates/accounts/acting_view.html, apps/accounts/views_members.py,
  apps/accounts/views_acting.py, docs/REQUIREMENTS.md (§2.1, FR-125),
  docs/TECHNICAL_REQUIREMENTS.md (TR-17), docs/INTERFACE.md, tools/a11y/test_axe.py, and the
  archive and acting-view tests.
- **Nature of Contribution**: Code, interface change and tests by the assistant, from three of
  the advisor's reports.
- **Human Review Status**: Pending the advisor's look. 349 tests, the accessibility sweep and the
  four guards pass.
- **Git Hash**: 3e64ff9

## [2026-09-20 03:05 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Access is no longer something the drop-down can take away. "No access" is
  gone from the menu at every level, because closing and suspending both carry a reason and a
  name, and on an account that is already shut out the menu is not rendered at all: the way back
  is the control that says so.
- **Sections/Files Affected**: apps/accounts/account.py, docs/REQUIREMENTS.md (FR-91),
  apps/accounts/tests/test_appointments.py.
- **Nature of Contribution**: Code and tests by the assistant, from the advisor's two decisions.
- **Human Review Status**: Pending the advisor's look. 350 tests, the accessibility sweep and the
  four guards pass.
- **Git Hash**: dbe3779

## [2026-09-20 03:20 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Three small corrections from the advisor's reading of the member page: the
  Under 18 box is gone, because the flag is set on the invitation and cleared by the conversion
  at 18 and that door only opens one way; the retention hold says what it does in fewer words;
  and a pending request to raise a level now expires, so confirming access for something else
  cannot raise one later.
- **Sections/Files Affected**: apps/accounts/account.py, apps/accounts/views_acting.py,
  docs/REQUIREMENTS.md (FR-109), docs/INTERFACE.md, and the form and acting-view tests.
- **Nature of Contribution**: Code, wording and tests by the assistant, from the advisor's
  requests.
- **Human Review Status**: Pending the advisor's look. 351 tests, the accessibility sweep and the
  four guards pass.
- **Git Hash**: 9a4df91

## [2026-09-20 03:55 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Two-step verification becomes something a member asks for. The sign-in
  library treats any enrolled key as a second factor, so adding a passkey turned it on by
  accident; the login stage is replaced through the adapter so the second step happens when the
  member turned it on or the club requires it of their access group. With it: a switch on the
  member's own page, two settings (which groups, and how many days of grace), a gate that tells
  somebody required for a fortnight and then sends them to enroll, and a second-step page that
  leads with the method the account actually holds.
- **Sections/Files Affected**: apps/accounts/mfa.py (new), apps/accounts/views_mfa.py (new),
  templates/mfa/authenticate.html (new), apps/accounts/adapter.py, apps/accounts/models.py,
  apps/accounts/migrations/0023_two_step_verification_is_asked_for.py, apps/accounts/views.py,
  apps/accounts/urls.py, apps/accounts/views_members.py, apps/accounts/middleware.py,
  apps/ops/views_settings.py, config/club.example.yaml, config/urls.py,
  templates/accounts/{member_detail,member_edit}.html, docs/REQUIREMENTS.md (§2.6),
  docs/TECHNICAL_REQUIREMENTS.md (TR-16), apps/accounts/tests/test_two_factor.py (new).
- **Nature of Contribution**: Design, code, migration and tests by the assistant, from the
  advisor's report and his two decisions on where a passkey belongs and who can be required.
- **Human Review Status**: Pending the advisor's look. 361 tests, the accessibility sweep and the
  four guards pass.
- **Git Hash**: 6adca39

## [2026-09-20 04:05 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The club overlay is laid over the shipped defaults rather than replacing
  them. Found on deploying the two-step verification settings: the rows were never created,
  because an installation with its own club.yaml never sees a key the application has added.
- **Sections/Files Affected**: apps/ops/config.py, apps/ops/tests/test_health_and_import.py,
  docs/TECHNICAL_REQUIREMENTS.md (TR-41).
- **Nature of Contribution**: Defect found on the server and fixed by the assistant, with a test.
- **Human Review Status**: Pending the advisor's look. 362 tests, the accessibility sweep and the
  four guards pass.
- **Git Hash**: ba8ac19

## [2026-09-20 04:15 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Every message now carries a Date header in the club's own time zone. The
  library's default writes `-0000`, which RFC 5322 defines as "no information about the local
  time zone", so a client may show the time in whatever zone it likes; the advisor saw the same
  message stamped four hours apart in two of his mailboxes.
- **Sections/Files Affected**: apps/comms/services.py, apps/comms/tests/test_messages.py,
  docs/REQUIREMENTS.md (FR-127, new).
- **Nature of Contribution**: Diagnosis against RFC 5322, code and a test by the assistant.
- **Human Review Status**: Pending the advisor's look. 364 tests, the accessibility sweep and the
  four guards pass.
- **Git Hash**: 6a2343a

## [2026-09-20 04:45 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: What the application grants an account is a **permission level** on every
  page that shows it, because "Access" already means the station and computer access a member
  signs for, and both words were on the members page at once. The code keeps `groups`.
- **Sections/Files Affected**: templates/accounts/{members,roster}.html, templates/ops/groups.html,
  templates/base.html, apps/accounts/{account,views_members,admin}.py, apps/ops/capabilities.py,
  apps/ops/views_settings.py, apps/ops/migrations/0009_permission_levels.py,
  docs/REQUIREMENTS.md (§2.1), docs/INTERFACE.md, and the member and form tests.
- **Nature of Contribution**: Vocabulary change by the assistant, from the advisor's question.
- **Human Review Status**: Pending the advisor's look. 364 tests, the accessibility sweep and the
  four guards pass.
- **Git Hash**: 503aa3e

## [2026-09-20 11:20 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: `/reconcile` after the rename: the requirements say permission level where
  a page does, the permission matrix row follows the capability's new label, TR-42 records that a
  level is a Django group, and the groups module says which word belongs where.
- **Sections/Files Affected**: docs/REQUIREMENTS.md (FR-13, §2.5), docs/TECHNICAL_REQUIREMENTS.md
  (TR-42), apps/ops/groups.py (docstring).
- **Nature of Contribution**: Reconciliation and writing by the assistant.
- **Human Review Status**: Pending the advisor's look. 364 tests, the accessibility sweep and the
  four guards pass.
- **Git Hash**: 010b70a

## [2026-09-20 11:30 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The members page's permission-level filter still summarised itself as
  "Any access": the panel's label and the word its summary uses are two separate strings, and
  yesterday's rename reached only the first.
- **Sections/Files Affected**: apps/accounts/views_members.py,
  apps/accounts/tests/test_directory.py.
- **Nature of Contribution**: Fix and test by the assistant, from the advisor spotting it.
- **Human Review Status**: Pending the advisor's look. 365 tests, the accessibility sweep and the
  four guards pass.
- **Git Hash**: 1fe70cf

## [2026-09-20 11:40 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The word for a WebAuthn credential is **passkey** on every page the club
  owns: the Confirm Access alternatives, the page that asks for one, our second-step page, and
  the profile's own sentences. The library's enrollment pages still say "security key" and are
  left for the advisor to decide about.
- **Sections/Files Affected**: apps/accounts/adapter.py (get_reauthentication_methods),
  templates/mfa/webauthn/reauthenticate.html (new override), templates/mfa/authenticate.html,
  templates/accounts/{member_detail,member_edit}.html, apps/accounts/{views,middleware,mfa}.py,
  apps/accounts/tests/test_two_factor.py.
- **Nature of Contribution**: Wording change by the assistant, from the advisor's request.
- **Human Review Status**: Pending the advisor's look. 365 tests, the accessibility sweep and the
  four guards pass.
- **Git Hash**: 0b41e60

## [2026-09-20 15:25 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The forked library template goes away. The club's word for a WebAuthn
  credential is passkey and every page written here says so; the sign-in library's own pages keep
  the library's words, because rewording them means forking markup or carrying a translation
  catalog, and both are a thing to maintain until the library catches up.
- **Sections/Files Affected**: templates/mfa/webauthn/reauthenticate.html (removed),
  apps/accounts/adapter.py, docs/INTERFACE.md.
- **Nature of Contribution**: Edit by the assistant, from the advisor's decision.
- **Human Review Status**: The advisor's call, recorded verbatim in INTERFACE.md.
- **Git Hash**: 8e4e104

## [2026-09-20 15:45 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Two links under every message. One shared address leads any member to
  their own notification switches; bulk mail additionally carries a signed unsubscribe for that
  recipient and that category, the RFC 8058 headers, and the club's postal address. The weekly
  digest and the openings blast had no unsubscribe of any kind, and new-event notices borrowed
  the announcement switch.
- **Sections/Files Affected**: apps/comms/{categories,services,layout,announce,views_announce}.py,
  apps/events/services/lifecycle.py, apps/accounts/views.py, apps/ops/views_settings.py,
  config/club.example.yaml, templates/comms/unsubscribe.html, docs/REQUIREMENTS.md (FR-71, FR-81,
  FR-89), apps/comms/tests/{test_announce,test_messages}.py, apps/events/tests/test_phase2.py.
- **Nature of Contribution**: Design against the FTC's guide and RFC 8058, code and tests by the
  assistant, from the advisor's instruction and his collaborator's point.
- **Human Review Status**: Pending the advisor's look; the club's postal address is his to
  confirm before it goes out. 370 tests, the accessibility sweep and the four guards pass.
- **Git Hash**: 8c0ce87

## [2026-09-20 16:25 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The surname gets a column of its own at every level, in full for an
  officer and as the initial for a member, and the directory opens sorted on it. A member had
  nothing to sort a roster by but the first name.
- **Sections/Files Affected**: apps/accounts/views_members.py, templates/accounts/members.html,
  docs/REQUIREMENTS.md (FR-13), apps/accounts/tests/{test_directory,test_members}.py.
- **Nature of Contribution**: Code, tests and documentation by the assistant, from the advisor's
  observation while walking T7.
- **Human Review Status**: Pending the advisor's look; he is the assignee of the scenario.
  371 tests, the accessibility sweep and the four guards pass.
- **Git Hash**: f7587e9

## [2026-09-20 16:40 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The Name column drops the surname's initial, now that the surname has a
  column of its own; it holds the name the club calls the person and nothing else.
- **Sections/Files Affected**: templates/accounts/members.html, docs/REQUIREMENTS.md (FR-13),
  apps/accounts/tests/{test_directory,test_members}.py.
- **Nature of Contribution**: Edit by the assistant, from the advisor's observation.
- **Human Review Status**: Pending the advisor's look. 371 tests, the accessibility sweep and the
  four guards pass.
- **Git Hash**: 72780b1

## [2026-09-20 16:50 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: A sysadmin was missing from the member-level directory. The list asked
  which accounts hold "see the member directory" through a group, and a sysadmin holds every
  capability through the account flag instead, so the club's own sysadmins were absent from its
  roster.
- **Sections/Files Affected**: apps/accounts/views_members.py, docs/REQUIREMENTS.md (FR-13),
  apps/accounts/tests/test_directory.py.
- **Nature of Contribution**: Defect found by the advisor while walking T7, fixed with a test.
- **Human Review Status**: Pending the advisor's look. 372 tests, the accessibility sweep and the
  four guards pass.
- **Git Hash**: f191a89

## [2026-09-20 17:10 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Confirm Access becomes one page: the library's password view with the
  passkey form and its challenge added, so the button is where the question is asked instead of
  behind a link to a second page of the same name. And a message catalogue gives the club's word
  for a WebAuthn credential to the library's own pages and mail, so the interface says passkey
  everywhere; it compiles with polib, because neither this machine nor the server has gettext.
- **Sections/Files Affected**: apps/accounts/views_mfa.py, templates/account/reauthenticate.html
  (new), config/urls.py, apps/accounts/adapter.py, locale/en/LC_MESSAGES/django.po (new),
  apps/ops/management/commands/compile_locale.py (new), config/settings/base.py, requirements.txt,
  tools/check.sh, .gitignore, docs/REQUIREMENTS.md (§2.1), docs/TECHNICAL_REQUIREMENTS.md (TR-17,
  TR-45 new), docs/INTERFACE.md, apps/accounts/tests/test_reauthenticate.py.
- **Nature of Contribution**: Design against the library's own extension points, code and tests
  by the assistant, from the advisor's two instructions.
- **Human Review Status**: Pending the advisor's look; the passkey prompt itself is his to try,
  since WebAuthn cannot be exercised from a test. 375 tests, the accessibility sweep and the four
  guards pass.
- **Git Hash**: b201e90

## [2026-09-20 17:47 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: A defect found while walking acceptance scenario T10: moving to a callsign
  the FCC has no record of left the previous callsign's class, licensee name and expiry on the
  license record, so the directory went on showing the old class letter.
- **Sections/Files Affected**: apps/credentials/services.py
  (`refresh_license_from_local_table`), apps/accounts/services.py (`apply_callsign`),
  apps/credentials/tests/test_uls.py (one new regression test, one existing test updated).
- **Nature of Contribution**: Diagnosis and fix by the assistant, from a club member's written
  report of what he saw.
- **Human Review Status**: Reviewed here; awaiting the reporter's re-test. Lint, the four
  guards, 376 tests and the accessibility sweep pass.
- **Git Hash**: b3969a2

## [2026-09-20 18:33 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The station computer password gains a way in. The page that sets it was a
  sysadmin's alone and reachable only by typing the address; the faculty advisor now holds the
  capability and Advisor tools carries the link.
- **Sections/Files Affected**: templates/base.html, apps/ops/templatetags/nav.py (a key icon),
  config/club.example.yaml, apps/accounts/migrations/0024_advisors_rotate_the_computer_password.py
  (new), apps/accounts/tests/test_permission_matrix.py, apps/credentials/tests/test_phase4.py.
- **Nature of Contribution**: Code generation and tests by the assistant, from the advisor's
  instruction.
- **Human Review Status**: Pending the advisor's look. Lint, the four guards, 378 tests and the
  accessibility sweep pass.
- **Git Hash**: f2f48fa

## [2026-09-20 18:52 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The approvals page as the advisor asked for it: a badge on the sidebar
  entry with the number waiting, Approve and Decline on one row, a link to the signed PDF, and a
  way back from a decline made by mistake.
- **Sections/Files Affected**: apps/credentials/context_processors.py (new),
  config/settings/base.py, templates/base.html, templates/credentials/approvals.html,
  apps/credentials/views.py, static/css/app.css, apps/credentials/tests/test_phase4.py.
- **Nature of Contribution**: Code generation and tests by the assistant, from four instructions.
- **Human Review Status**: Pending the advisor's look. Lint, the four guards, 380 tests and the
  accessibility sweep pass.
- **Git Hash**: a70b6aa

## [2026-09-20 19:08 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Three faults found by acceptance testing: a password was silently trimmed
  before it was validated, so twelve characters were refused as eleven; the page that shows the
  station computer password had no way in but the rotation notice; and an invitation's link was
  shown once and nowhere else.
- **Sections/Files Affected**: apps/accounts/forms.py (`password_field`), apps/accounts/views.py,
  apps/accounts/views_entry.py, apps/credentials/context_processors.py, config/settings/base.py,
  templates/base.html, templates/credentials/agreements.html, templates/credentials/password.html,
  templates/accounts/invitations.html, static/css/app.css, and tests in
  apps/accounts/tests/test_flows.py and apps/credentials/tests/test_phase4.py.
- **Nature of Contribution**: Diagnosis, code generation and tests by the assistant, from three
  club members' written reports and the advisor's instructions.
- **Human Review Status**: Pending the testers' re-walk. Lint, the four guards, 383 tests and the
  accessibility sweep pass.
- **Git Hash**: 1b551a1

## [2026-09-20 19:39 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: One Confirm Access for every guarded act: the authenticator code taken off
  it, the page laid out like the sign-in screen, the station password moved behind it, and a
  confirmation spent by the act it was given for so a raise to Sysadmin and a view of the shared
  password each ask again. Separately, the invitation link copies from a glyph and its page takes
  the window.
- **Sections/Files Affected**: apps/accounts/reauth.py (new), apps/accounts/adapter.py,
  apps/accounts/views_acting.py, apps/credentials/views.py, templates/account/reauthenticate.html,
  templates/credentials/password.html, templates/accounts/invitations.html, static/css/app.css,
  static/js/app.js, and tests in apps/accounts/ and apps/credentials/.
- **Nature of Contribution**: Design against the library's own hooks, code and tests by the
  assistant, from the advisor's instructions.
- **Human Review Status**: Pending the advisor's look; the passkey prompt is his to try. Lint,
  the four guards, 386 tests and the accessibility sweep pass.
- **Git Hash**: d1e04da, 4273a05

## [2026-09-20 19:50 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Reconciliation: the requirements catch up with the evening's work — the
  advisor rotating the computer password, the member's route to it, the approvals page and its
  undo, a password that keeps its spaces, an invitation link that stays reachable, and Confirm
  Access as one screen asked for every time.
- **Sections/Files Affected**: docs/REQUIREMENTS.md (§2.1 table, §2.6, FR-3, FR-25, FR-32,
  FR-33), docs/TECHNICAL_REQUIREMENTS.md (TR-17).
- **Nature of Contribution**: Document edits by the assistant, from the code as built and the
  advisor's instructions quoted in place.
- **Human Review Status**: Pending the advisor's look.
- **Git Hash**: 175052c

## [2026-09-20 20:00 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The access rosters sort and narrow the way the members directory does:
  every column sortable, four filter panels and a search box in the same words, the name split
  into First, Last and Callsign, the credential linked to the signed PDF, and a download that
  follows the filters.
- **Sections/Files Affected**: apps/ops/tables.py (new, the shared sort/filter helpers),
  apps/credentials/views_reports.py (`access_rosters`),
  templates/credentials/access_rosters.html, apps/credentials/tests/test_phase4.py.
- **Nature of Contribution**: Code generation and tests by the assistant, from the advisor's
  five points on issue #92.
- **Human Review Status**: Pending the advisor's look. Lint, the four guards, 386 tests and the
  accessibility sweep pass.
- **Git Hash**: ea138d6

## [2026-09-20 20:12 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: A regression from this evening's Confirm Access work: taking the passkey
  out of the adapter's list of reauthentication methods also took it out of the library's own
  check, so the credential came back to a view that redirected instead of verifying it.
- **Sections/Files Affected**: apps/accounts/adapter.py (`get_reauthentication_methods`),
  apps/accounts/tests/test_reauthenticate.py (one new regression test).
- **Nature of Contribution**: Diagnosis and fix by the assistant, from the advisor's report on
  issue #9; the test was checked against the broken version before being kept.
- **Human Review Status**: Pending the advisor's re-test; WebAuthn itself cannot be exercised
  from a test. Lint, the four guards, 387 tests and the accessibility sweep pass.
- **Git Hash**: 6fb9192

## [2026-09-20 20:23 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The record of what has been decided about access (FR-128), on the
  approvals page: a table of its own that keeps every decision rather than the latest, with
  search, two filters, sorting, pagination and CSV. Plus three more on the access rosters:
  contact columns, the Days column removed, and a Status panel that opens on Active.
- **Sections/Files Affected**: apps/credentials/models.py (`CredentialDecision`), migrations
  0006 and 0007 (the model and its backfill), apps/credentials/services.py (`log_decision`,
  approve, revoke, expire_due, the supersede path), apps/credentials/views.py (the log, its
  CSV), apps/credentials/views_reports.py and templates/credentials/access_rosters.html,
  templates/credentials/approvals.html, docs/REQUIREMENTS.md (FR-128), tests.
- **Nature of Contribution**: Code generation, a data migration and tests by the assistant, from
  the advisor's instructions on issues #92 and the approved plan.
- **Human Review Status**: Pending the advisor's look. Lint, the four guards, 389 tests and the
  accessibility sweep pass.
- **Git Hash**: 2f5dff2

## [2026-09-20 20:28 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The seeded decision rows named "User object (1)": a migration's historical
  model has no custom `__str__`. The seed is corrected and the rows it already wrote repaired.
- **Sections/Files Affected**: apps/credentials/migrations/0007_seed_the_record_from_what_stands.py,
  apps/credentials/migrations/0008_the_seeded_rows_name_a_person.py (new).
- **Nature of Contribution**: Fix by the assistant, found by reading the live database back after
  the deploy.
- **Human Review Status**: Reviewed here; the repair is verified on the server after deploying.
- **Git Hash**: 93fc712

## [2026-09-20 20:54 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Four notes from the advisor walking the approvals page: the seeded note
  out of the By column, the queue as a list rather than a card each, the signed PDF carrying its
  own standing and the record of decisions on it, and an unread notice offering the page where
  the work is done.
- **Sections/Files Affected**: apps/credentials/models.py (`seeded`, `pdf_built_at`), migrations
  0009 and 0010, apps/credentials/services.py (the PDF context and its build stamp),
  apps/credentials/views_reports.py (rebuild a stale PDF), apps/ops/views.py and
  templates/ops/dashboard.html (the banner's action), templates/credentials/agreement_pdf.html,
  templates/credentials/approvals.html, static/css/app.css, tools/check_interface.sh, tests.
- **Nature of Contribution**: Design and code by the assistant, from the advisor's four points.
- **Human Review Status**: Pending the advisor's look; one question is his to answer. Lint, the
  four guards, 389 tests and the accessibility sweep pass.
- **Git Hash**: 2323185

## [2026-09-20 21:02 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The rotation page and its notice name the page a member reads the password
  on, and stop promising a password prompt that now takes a passkey too.
- **Sections/Files Affected**: templates/credentials/password_manage.html,
  apps/comms/defaults.py (`password.rotated`).
- **Nature of Contribution**: Wording fix by the assistant, from the advisor's note on issue #76.
- **Human Review Status**: Pending the advisor's look.
- **Git Hash**: 9bdff55

## [2026-09-20 21:10 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The document's status marking became a page-margin band: a rotated
  watermark, and an SVG background carrying one, both laid the word into the text layer glyph by
  glyph and threaded it through the record of decisions.
- **Sections/Files Affected**: templates/credentials/agreement_pdf.html,
  apps/credentials/services.py (the band's colour).
- **Nature of Contribution**: Fix by the assistant, found by rendering a real document and
  reading its text back with pdftotext.
- **Human Review Status**: Reviewed here; verified by extraction, one page, no scattered glyphs.
- **Git Hash**: 56c0dc5

## [2026-09-20 21:36 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Station and computer access now require an institution address from
  anyone; reversing a decline says why and is done from its own row in the log; the watermark is
  back as glyph outlines with the club's seal behind it; the roster's phone numbers are
  formatted; and the FCC name-mismatch warning says what happens and links where to answer it.
- **Sections/Files Affected**: apps/credentials/views.py (the institution rule, the reversal
  reason, the log's reversible flag), apps/credentials/services.py (approve's note, the
  watermark builder), templates/credentials/approvals.html and access_rosters.html and
  agreement_pdf.html, apps/accounts/views.py and views_members.py and
  templates/accounts/member_detail.html (the warning), static/css/app.css, config/club.example.yaml,
  club.yaml in the private repo, tests.
- **Nature of Contribution**: Code generation and tests by the assistant, from the advisor's
  points on issues #8, #92 and #93.
- **Human Review Status**: Pending the advisor's look. Lint, the four guards, 391 tests and the
  accessibility sweep pass; the PDF was rendered and its text extracted to check the watermark
  stays out of the text layer.
- **Git Hash**: ce3ac29

## [2026-09-20 21:47 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Four on the signed document: every stored PDF rebuilds when the rendering
  changes rather than only when a decision does, an agreement awaiting approval carries no
  watermark, the watermark is larger, the download is named after who signed what and when, and
  "Approve after all" becomes "Reverse this decision".
- **Sections/Files Affected**: apps/credentials/models.py (`pdf_render_version`, the action's
  label), migrations 0011 and 0012, apps/credentials/services.py (`PDF_RENDER_VERSION`,
  `agreement_pdf_name`, the watermark's size), apps/credentials/views_reports.py,
  apps/credentials/views.py, templates/credentials/approvals.html and agreement_pdf.html, tests.
- **Nature of Contribution**: Code generation and tests by the assistant, from the advisor's
  three notes on issue #8.
- **Human Review Status**: Pending the advisor's look. Lint, the four guards, 392 tests and the
  accessibility sweep pass; a document was rendered and its text extracted again.
- **Git Hash**: ddc3c67

## [2026-09-20 21:57 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The unanswered FCC-name question follows the member on every page until
  they answer it, rather than sitting on a profile they may never open.
- **Sections/Files Affected**: templates/base.html, templates/accounts/member_detail.html
  (its duplicate removed), apps/accounts/tests/test_flows.py.
- **Nature of Contribution**: Change by the assistant, from the advisor's point on issue #93.
- **Human Review Status**: Pending the advisor's look. Lint, the four guards, 392 tests and the
  accessibility sweep pass.
- **Git Hash**: dcc9430

## [2026-09-20 22:05 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The callsign question made quiet and short, with the way to a preferred
  name in it; and an invariant that no password field in the project trims what is typed.
- **Sections/Files Affected**: templates/base.html, static/css/app.css,
  apps/accounts/tests/test_flows.py.
- **Nature of Contribution**: Wording, styling and a test by the assistant, from the advisor's
  points on issue #93; the test was checked against a deliberately broken form first.
- **Human Review Status**: Pending the advisor's look. Lint, the four guards, 393 tests and the
  accessibility sweep pass.
- **Git Hash**: 132b4fb

## [2026-09-20 22:14 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The signed PDF is named in the advisor's own shape, and the seeded note
  stops being printed in the decision tables.
- **Sections/Files Affected**: apps/credentials/services.py (`agreement_pdf_name`),
  templates/credentials/approvals.html, templates/credentials/agreement_pdf.html, tests.
- **Nature of Contribution**: Change by the assistant, from the advisor's two notes on issue #8.
- **Human Review Status**: Pending the advisor's look. Lint, the four guards, 393 tests and the
  accessibility sweep pass.
- **Git Hash**: 3046deb

## [2026-09-20 22:20 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The callsign question goes back to the warning colour and becomes a strip
  rather than a block: the first attempt fixed the wrong half of the advisor's note.
- **Sections/Files Affected**: templates/base.html, static/css/app.css.
- **Nature of Contribution**: Styling and wording by the assistant, from the advisor's note on
  issue #93.
- **Human Review Status**: Pending the advisor's look. Lint, the four guards, 393 tests and the
  accessibility sweep pass.
- **Git Hash**: 25461c9

## [2026-09-20 22:26 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The callsign question moves out of the banner rail and into the content as
  a message strip, the shape and place the advisor pointed at.
- **Sections/Files Affected**: templates/base.html, static/css/app.css.
- **Nature of Contribution**: Styling by the assistant, from the advisor's note on issue #93.
- **Human Review Status**: Pending the advisor's look. Lint, the four guards, 393 tests and the
  accessibility sweep pass.
- **Git Hash**: 8d504fc

## [2026-09-20 22:38 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: An access agreement is approved only against a **confirmed** institution
  address, and approving is no longer a place where an address gets confirmed. Reported by the
  advisor, who approved an agreement using an address already confirmed to another member.
- **Sections/Files Affected**: apps/credentials/views.py (`_institution_address`, the gate, the
  queue and reversal contexts), templates/credentials/approvals.html, tests.
- **Nature of Contribution**: Diagnosis and fix by the assistant, from the advisor's report and
  his decision on the rule.
- **Human Review Status**: Pending the advisor's look. Lint, the four guards, 395 tests and the
  accessibility sweep pass.
- **Git Hash**: 07e8310

## [2026-09-20 22:58 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: An address now records **how** it came to be trusted. The emailed
  invitation carries a second token the copied link does not, so arriving by it proves the
  mailbox; access agreements are approved only against an address proved that way or confirmed
  by hand.
- **Sections/Files Affected**: apps/accounts/models.py (`Address.Proof`, `Address.proof`,
  `Invitation.mail_token`), migrations 0025 and 0026, apps/accounts/addresses.py,
  apps/accounts/services.py, apps/accounts/views.py, apps/accounts/entry.py,
  apps/credentials/views.py, templates/accounts/_addresses.html,
  templates/credentials/approvals.html, tests.
- **Nature of Contribution**: Design and code by the assistant, from the advisor's instruction.
- **Human Review Status**: Pending the advisor's look. Lint, the four guards, 397 tests and the
  accessibility sweep pass.
- **Git Hash**: 9ff3d3d

## [2026-09-20 23:25 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: The requirements record how an address is proved, what an access approval
  now asks for, and the advisor's decision that addresses confirmed before tonight stay unproven.
- **Sections/Files Affected**: docs/REQUIREMENTS.md (§2.6, FR-27).
- **Nature of Contribution**: Document edits by the assistant, from the advisor's instruction and
  the code as built.
- **Human Review Status**: Pending the advisor's look.
- **Git Hash**: 8aea8ab

## [2026-09-20 23:55 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5
- **Session Purpose**: Reconciliation: the requirements catch up with an evening of acceptance
  testing — the rosters' sorting and columns, the document's standing and watermark, the
  reversal's required reason, the callsign question that follows a member, and why the passkey
  must stay in the library's own list.
- **Sections/Files Affected**: docs/REQUIREMENTS.md (FR-16, FR-23, FR-25, FR-84),
  docs/TECHNICAL_REQUIREMENTS.md (TR-10, TR-17).
- **Nature of Contribution**: Document edits by the assistant, from the code as built and the
  advisor's instructions quoted in place.
- **Human Review Status**: Pending the advisor's look.
- **Git Hash**: a476878

## [2026-09-22 18:34 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5[1m]
- **Session Purpose**: Fix the duplicate agreement signature the advisor found walking T8: one
  click on Sign it could be recorded twice, putting a second card in the approvals queue and
  sending the approver a second notification for the same agreement.
- **Sections/Files Affected**: apps/credentials/views.py (`sign`), apps/credentials/models.py
  (`SignedAgreement.Meta`), apps/credentials/migrations/0013_one_signature_awaiting_approval.py
  (new; collapses duplicates already stored, then adds the constraint),
  apps/credentials/tests/test_phase4.py (two tests).
- **Nature of Contribution**: Diagnosis from the advisor's screenshot and report, then code
  generation and tests by the assistant.
- **Human Review Status**: Pending the advisor's look. Verified by the assistant: the new test
  fails on the unfixed code and passes on the fix; the migration was run forward against a
  scratch database seeded with three duplicate pending rows and a decided one, keeping the
  earliest and leaving the decision untouched; `tools/check.sh quick` all clear, 395 tests.
- **Git Hash**: 8b93d1d

## [2026-09-23 02:23 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5[1m]
- **Session Purpose**: Four defects the advisor found walking T8, and one terminology decision
  taken with him: the Home banner counted a truncated slice and recited every subject; the
  institution address was asked for at approval rather than before signing; the approval
  refusal was reworded; the standing "Is this you?" question was duplicated by a flash message
  on the way in; and the account page had five names, now one.
- **Sections/Files Affected**: apps/ops/views.py and templates/ops/dashboard.html (the banner);
  apps/credentials/views.py, templates/credentials/agreements.html and approvals.html (the
  address before signing, and the refusal wording); apps/accounts/views.py and templates/base.html
  (the question said once, reworded); apps/comms/defaults.py, templates/accounts/member_edit.html
  (terminology and the addresses anchor); docs/REQUIREMENTS.md (FR-22, FR-27, FR-108);
  docs/INTERFACE.md (one name for the account page); tests in three apps.
- **Nature of Contribution**: Diagnosis from the advisor's screenshots, code generation, and
  document edits by the assistant. The banner wording was settled with him over two drafts and
  the terminology decision is his, taken against a survey of what the site already said.
- **Human Review Status**: Pending the advisor's look. Verified by the assistant: `tools/check.sh`
  passes in full — lint, format, the three repository guards, the migration check, 397 tests and
  the accessibility sweep across all eight roles.
- **Git Hash**: 399d1e4

## [2026-09-23 11:46 UTC]
- **Tool**: Claude (Anthropic), claude-opus-5[1m]
- **Session Purpose**: Two agreements were found awaiting approval on the live site for an
  account that had been ended after signing: the approver could neither approve them (the FR-27
  address check refused) nor clear them. The queue and its badge now hold only signatures
  somebody could act on, and approving one from a held URL is refused.
- **Sections/Files Affected**: apps/credentials/views.py (the queue, and the refusal in
  `decide`), apps/credentials/context_processors.py (the badge, so it agrees with the queue),
  apps/credentials/tests/test_phase4.py (two tests), docs/REQUIREMENTS.md (FR-22).
- **Nature of Contribution**: Diagnosis from a live read-only query, then code generation, tests
  and document edits by the assistant. The advisor corrected the first attempt: it keyed on
  `is_active`, which catches archiving and deletion but not closing or suspending, and the
  correction is his ("there is closing, suspending, archiving, and deleting. Of those, deleting
  is not reversable"), quoted in FR-22.
- **Human Review Status**: Pending the advisor's look. Verified by the assistant: the first test
  was confirmed to fail on the unfixed code; the second walks all four endings; `tools/check.sh`
  passes in full — lint, format, the three guards, the migration check, 399 tests and the
  accessibility sweep across all eight roles.
- **Git Hash**: ebeb5e8
