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
