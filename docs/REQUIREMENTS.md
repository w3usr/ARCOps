# ops.w3usr.org: Requirements

**Status: DRAFT FUNCTIONAL REQUIREMENTS, awaiting review and adoption.**

This document turns the faculty advisor's first-pass description of the application (dictated
2026-09-12) into numbered functional requirements. Section 3 is the substance. Sections 4 to 6
hold what is known about data, non-functional constraints, and technology, and are deliberately
thin: the advisor's direction was *"We are going to focus on functional requirements first. Once
we get that figured out, we can move onto technical requirements."*

Every requirement below is a **proposal** until the status table says otherwise. Where the
drafting session filled a gap in the dictation or resolved a problem it found, the requirement
says so and section 9 records the reasoning, so that a reviewer can tell the advisor's
instructions from the assistant's inferences.

Do not build against this document until its status line says the requirements are adopted,
with a date and the name of the person who adopted them.

| | |
|---|---|
| **Document status** | Draft; not adopted |
| **Last revised** | 2026-09-12 |
| **Owner** | Nathaniel A. Frissell, W2NAF (faculty advisor), pending a project lead |
| **Adopted by** | {{NAME, CALLSIGN}} on {{YYYY-MM-DD}} |

---

## 0. How to read this document

**Requirement IDs.** Each functional requirement has a permanent ID, `FR-n`. Issues, commits,
and later sessions cite the ID. Retire a requirement by marking it `[RETIRED YYYY-MM-DD]` with a
pointer to what replaced it; never reuse a number.

**Priority.** Each requirement carries one of three tags for the first release:

| Tag | Meaning |
|---|---|
| **Must** | v1 is not usable by the club without it |
| **Should** | Expected in v1; may slip to v1.1 if it threatens the schedule |
| **Could** | Wanted, and designed for now so it stays cheap later; built when there is time |

Items marked **Later** are recorded so the design leaves room for them, and are out of scope for
v1 unless the priority is changed here.

**Source.** Requirements taken directly from the dictation carry no marker. Requirements the
drafting session added carry **(added)** and a one-line reason; the fuller reasoning is in
section 9. Where the dictation was ambiguous and the draft picked a reading, the requirement
says **(interpretation)** and section 8 lists the question.

**Terms.** *Event*: anything the club schedules people for (a contest, JOTA, a special-event
station, a work party). *Operating period*: a contiguous span of time within an event during
which the station may be on the air. *Slot*: a bookable interval within an event. *Sign-up*: one
person in one slot in one role. *Credential*: a verified fact about a person that a slot may
require (a license of a given class, current station access, a current IT agreement).

---

## 1. Purpose and scope

### 1.1 Problem statement

W3USR runs contests and operating events with volunteer operators drawn from students,
faculty, staff, and community members. Today the club coordinates them by hand: who covers
which hours, whether each hour has someone legally able to operate and someone physically able
to open the station, who has signed which access agreement, and who needs to be told what. The
same by-hand process handles station swipe-card access, the shared computer account, and the
paper agreements behind both. The application replaces that coordination with one system of
record.

The advisor's framing, verbatim:

> This is going to be a webapp to support and manage amateur radio operations at the W3USR
> University of Scranton amateur radio club. While this website is going to be specifically for
> W3USR, it should be sufficiently modular and adaptable so that any club could make use of it.
> Also, while it will primarily support contesting operations, it might also be used to support
> other events, such as JOTA, CQ Santa, etc.

### 1.2 In scope for v1

1. **Events and scheduling**: create events (imported from a contest calendar or by hand),
   generate bookable time slots that respect each contest's operating rules, and let members
   sign up.
2. **People**: an invitation-only user database with the profile fields the club needs, four
   access levels, per-event captains, and guardian-managed accounts for minors.
3. **Credentials and access**: FCC license class and expiration kept current automatically;
   digital signing, advisor approval, and expiry of the station and computer access agreements;
   controlled display of the shared computer account password.
4. **Schedule health**: for every slot, whether the people signed up satisfy the legal and
   physical requirements to operate, surfaced on a roster page and pushed out as warnings.
5. **Communications**: transactional email from `ops@w3usr.org` (invitations, reminders,
   warnings, announcements), with guardians copied on everything sent to a minor.
6. **Reports**: who currently holds station access and computer access; per-event rosters.

### 1.3 Out of scope for v1 (proposed; the advisor's call per section 8, Q1)

The requirements skeleton that preceded this draft listed several candidate areas. None were
mentioned in the dictation. The draft proposes deferring them so that v1 is finite:

- **QSO logging and scoring.** The club runs N1MM Logger+ and the station log lives on the
  station computers (the Computer Account Usage Agreement names both). Reproducing or ingesting
  that is a separate project. See section 3.11.
- **Equipment and antenna inventory, band plans, fault tracking.** Section 3.11.
- **Public-facing content.** The University page at `scranton.edu/w3usr` is the club's public
  face and `w3usr.org` redirects there. `ops.w3usr.org` shows a visitor a sign-in page and
  nothing that names a member (FR-98).
- **Native mobile apps.** The v1 web application must work well on phone browsers and be
  installable as a progressive web app; a native app is a later path (section 5.4).
- **SMS and push notifications.** Designed for (FR-83), built later.
- **Membership dues, finances, meeting minutes, inventory of club property.**

### 1.4 Definition of done for v1 (proposed)

An officer imports the next School Club Roundup and the next Pennsylvania QSO Party from the
contest calendar, accepts the offered slot schedule (which respects each contest's operating
periods and hour limits), names a captain for each, and opens sign-ups: mentor and observer
roles to anyone available at once, operator roles to students first and to everyone later.
Members sign up from their phones. Every member who will open the station has
signed the current station access agreement in the application and the advisor has approved it
there. The roster page shows, for every slot, whether it can legally and physically run, and
the captains and the people signed up have received a warning for any slot that cannot. Every
person signed up received a reminder 24 hours before their slot and confirmed by clicking a
link. The advisor can print a roster of who currently holds station and computer access.
Every step of this also works with outbound email switched off: the officer hands the
invitation links over by other means, and members see their reminders and warnings in the
application (FR-103).

### 1.5 Portability principle

Anything that is a fact about W3USR is configuration, never code: the club name and callsign,
the sending and reply-to addresses, the list of member categories, the list of club positions,
the license class ladder, the agreement texts, and the credential types. A second club adopts
the application by editing configuration and supplying its own agreement texts. Requirements
below that exist mainly to keep this true are marked **(portability)**.

---

## 2. Users, roles, and permissions

### 2.1 Access levels

The dictation names four levels. They are mutually exclusive and every account holds exactly one.

| Level | Who | Summary of powers |
|---|---|---|
| **Sysadmin** | The people who run the application | Everything, including manual account creation and editing, password resets, privilege fields, configuration, and overrides of automated data |
| **Club officer** | Elected officers and the faculty advisors | Send invitations; create, edit, and captain events; send announcements; view reports; approve applications. Cannot edit another account's privilege fields or reset passwords |
| **Member** | An admitted member in good standing | Edit own non-privilege profile fields; view schedules and rosters; sign up for slots; sign agreements; view the computer password when eligible |
| **No access** | Account exists; sign-in refused | Nothing. Used for graduated, lapsed, or suspended members, and for accounts whose application is pending |

Verbatim:

> Members should be able to update their personal details, but not things that grant privileges
> (like Faculty / Staff / Student / Community Member - that should be set in initial iniviation,
> or license class, which should be from FCC lookup or sysadmin override, or station/IT access
> approval, or club position)

### 2.2 Event captain (a per-event grant)

Any member may be made a captain of a specific event by an officer or sysadmin. Within that
event, and only there, a captain has officer-equivalent powers: edit the event and its slots,
adjust capacities and eligibility, move or remove sign-ups, send messages to the event's
participants, and see participants' contact details. Captains receive every notification the
event generates. An event has one or more captains.

### 2.3 Club positions and derived capabilities

Club position (Faculty Advisor, Associate Faculty Advisor, President, Vice President, Secretary,
Treasurer, Trustee, and so on) is a profile field set by a sysadmin or officer, from a
configurable list **(portability)**. It is displayed, and two capabilities derive from it:

- **Agreement approver.** Approving a signed access agreement is reserved to positions the
  configuration marks as approvers; for W3USR, the faculty advisors. This is deliberately
  narrower than "officer".
- **Default reply-to.** Announcement replies route to the sender, the event's captains, and the
  club address (`w3usr@scranton.edu`), per the dictation.

### 2.4 Guardians and minors (added; the dictation states the rules, the account model is the draft's)

A member under 18 cannot manage their own account. The dictation:

> If someone is under 18, they are not able to manage their own account. They must have a
> designated parent/guardian manage it for them. We also need to keep track of the
> parent/guardian phone numbers and emails. A parent or guardian must be CC'd on every
> communication to a minor. The minor does not have to provide an email or phone number of
> their own; only the parent/guardian is required. A responsible adult authorized by the
> parent/guardian is required to chaperone minors at all W3USR events.

The draft models this as follows:

- A **guardian** is an account that is linked to one or more minor member accounts and acts for
  them: completes the application, edits the profile, signs agreements, signs up for slots, and
  receives every message. A guardian need not be a member; if the guardian is also a member,
  one account holds both.
- The minor's own account has access level **No access** until the club decides otherwise, so
  the minor never signs in. (Whether a minor may sign in at all, read-only, is Q6.)
- The guardian record holds the guardian's name, relationship, email(s), and phone. The minor's
  own email and phone are optional.
- The guardian designates **authorized chaperones**: adult members who may supervise the minor
  at events. The schedule-health check (FR-64) uses this list.
- On the member's 18th birthday, the system notifies the guardian and a sysadmin, and a
  sysadmin converts the account to self-managed. Nothing changes automatically.

### 2.5 Permission matrix

`✓` may do; `E` may do within events they captain; `own` on their own record only; `·` may not.

| Action | Sysadmin | Officer | Captain | Member | Guardian (for linked minor) |
|---|---|---|---|---|---|
| Send invitation | ✓ | ✓ | · | · | · |
| Approve application, set member category | ✓ | ✓ | · | · | · |
| Create or edit account manually | ✓ | · | · | · | · |
| Reset another user's password | ✓ | · | · | · | · |
| Change access level or club position | ✓ | · | · | · | · |
| Override license class or expiration | ✓ | · | · | · | · |
| Edit own name, callsign, emails, phone, preferences | ✓ | ✓ | ✓ | own | for minor |
| Sign an access agreement | ✓ | ✓ | ✓ | own | for minor |
| Approve an access agreement | approver position only | | | | |
| Set or rotate the computer password | ✓ | · | · | · | · |
| View the computer password | with current IT agreement | | | | · |
| Create event, import from calendar | ✓ | ✓ | · | · | · |
| Name event captains | ✓ | ✓ | · | · | · |
| Edit event, slots, capacities, eligibility | ✓ | ✓ | E | · | · |
| Move or remove another person's sign-up | ✓ | ✓ | E | · | · |
| Sign up for a slot, cancel own sign-up | ✓ | ✓ | ✓ | ✓ | for minor |
| View roster (names, callsigns, roles, health) | ✓ | ✓ | ✓ | ✓ | ✓ |
| View participants' phone and email | ✓ | ✓ | E | · | · |
| Send announcement to event participants | ✓ | ✓ | E | · | · |
| Send announcement to all members | ✓ | ✓ | · | · | · |
| View access rosters and reports | ✓ | ✓ | · | · | · |
| View audit log | ✓ | · | · | · | · |
| Edit club configuration | ✓ | · | · | · | · |

### 2.6 Authentication

**Decided by the dictation: club-managed accounts, invitation only.** Community members have no
University login, so University SSO cannot be the only door, and the dictation describes
passwords and sysadmin resets directly. Specifics:

- Sign-in by email address (either on file) and password.
- Password strength enforced; breached-password check **Should**.
- Self-service reset from a "Forgot username or password?" link on the sign-in page (FR-107),
  which needs working email. The sysadmin temporary-password path (FR-7) is the fallback and
  never depends on email.
- Second factor (TOTP or passkey) **Should** for sysadmins and officers, **Could** for members.
  The application displays a shared password to eligible members (FR-33), which raises the value
  of any compromised account.
- Sessions expire; "remember this device" is allowed on members' own devices.
- University SSO as an *additional* sign-in method for `@scranton.edu` accounts: **Later**, Q9.

### 2.7 Invitations and applications

Verbatim:

> Users will only be able to access the system by an invitation generated by a sysadmin or club
> officer. The sysadmin or club officer will be able to enter a person's email address into the
> system. An invitation email will be sent where a person can then fill out an application.
> Sysadmins can also create and edit user accounts manually, including resetting passwords by
> generating a temporary password that needs to be reset on next user login. Club officers can
> only send invitations.

Flow as drafted (the review step and expiry are the draft's additions; see FR-3 to FR-7):

1. Officer or sysadmin enters an email address and selects the member category the person will
   hold (Faculty / Staff / Student / Community Member), since the dictation says category is
   "set in initial invitation". For an applicant under 18, the inviter marks the invitation as
   a minor's and enters the guardian's email instead.
2. The system creates a single-use invitation link that expires (default 14 days), shows it to
   the inviter with a ready-to-send text (FR-104), and emails it if email delivery is on. The
   inviter can resend or revoke it.
3. The invitee completes the application: the profile fields of FR-8, a password, and consent
   to the privacy notice (FR-101).
4. The application lands in a review queue. An officer or sysadmin admits the applicant, which
   sets the access level to Member, or declines with a reason. Until then the account is
   **No access**. (The dictation does not say whether an application is reviewed before access
   is granted; the draft assumes yes, Q3.)
5. On admission, the system performs the FCC lookup (FR-14) and sends a welcome message.

---

## 3. Functional requirements

### 3.1 Accounts and profiles

- **FR-1 [Must]** Access is by invitation only. There is no public registration form.
- **FR-2 [Must]** Sysadmins and officers can issue an invitation to an email address, choosing
  the member category the invitee will hold and whether the invitee is a minor.
- **FR-3 [Must]** An invitation is a single-use link that expires; the issuer can resend it or
  revoke it, and always sees the link itself and a text to send by hand (FR-104). The system
  shows the issuer the state of each invitation (created, emailed or not, opened, completed,
  expired, revoked). **(added)**: the dictation does not mention expiry; an unexpiring invite in
  a mailbox is a standing door.
- **FR-4 [Must]** The invitee completes an application that collects the FR-8 fields, sets a
  password, and records consent to the privacy notice.
- **FR-5 [Must] (interpretation)** Completed applications enter a review queue. An officer or
  sysadmin admits or declines each one. Until admitted, the account has access level No access.
- **FR-6 [Must]** Sysadmins can create and edit any account manually, including every privilege
  field.
- **FR-7 [Must]** Sysadmins can reset any account's password to a generated temporary,
  one-time password. It works for exactly one sign-in, which must set a new password before
  anything else; it expires unused after a configurable period (default 72 hours); and it is
  shown once to the sysadmin, who passes it to the member by whatever means they choose. The
  system never emails it. This is the password-reset path that does not depend on email
  (FR-103).
- **FR-8 [Must]** The profile holds the following fields. Editability follows section 2.5.

  | Field | Required | Editable by member | Notes |
  |---|---|---|---|
  | First name | yes | yes | |
  | Middle name | no | yes | |
  | Last name | yes | yes | |
  | Preferred name | no | yes | **(added)** Shown on rosters where set; people are addressed by the name they use |
  | Callsign | no | yes | Uppercase, validated as a plausible callsign. A change triggers FR-102 |
  | License class | no | no | From FCC lookup (FR-14) or sysadmin override |
  | License expiration | no | no | From FCC lookup or sysadmin override |
  | License status | no | no | **(added)** Active / expired / cancelled / not found, from FCC lookup; the health check needs status, not only class |
  | Scranton email | one of the two | yes | Validated as `@scranton.edu` |
  | Personal email | one of the two | yes | |
  | Email delivery preference | yes | yes | Scranton, personal, or both |
  | Cell phone | no for adults; no for minors | yes | Guardian phone is required for a minor instead |
  | Under 18 | yes | no | Set at invitation; drives the guardian rules. **(added)** Store date of birth only if the club wants automatic 18th-birthday handling (Q7); otherwise a boolean set by the inviter |
  | Member category | yes | no | Faculty / Staff / Student / Community Member; set at invitation, changed by officer or sysadmin |
  | Club position | no | no | From the configured list; set by sysadmin |
  | Access level | yes | no | Section 2.1; set by sysadmin |
  | Guardian(s) | required if under 18 | guardian edits own | Section 2.4 |
  | Authorized chaperones | for minors | guardian | Section 2.4 |

- **FR-9 [Must]** Members can edit their own non-privilege fields. Privilege fields (category,
  license data, access approvals, club position, access level) are read-only to the member and
  show where the value came from and when.
- **FR-10 [Must]** A guardian account can do everything on behalf of a linked minor that the
  minor could do if self-managed, and the minor's account cannot sign in.
- **FR-11 [Should]** A member can ask for their account to be closed. Closure sets No access and
  starts the retention clock (section 4.3); it does not delete signed agreements before their
  retention period ends.
- **FR-12 [Should] (portability)** Member categories and club positions are configurable lists.
  W3USR ships with the values in FR-8.
- **FR-13 [Could]** A member directory, visible to members, showing name, callsign, category,
  and club position only. No contact details. (Whether the club wants this at all is Q10.)

### 3.2 Licenses and credentials

Verbatim:

> License Class and Expiration Date (Do by FCC lookup at time of account creation; cronjob to
> batch-check this information on a daily basis. Allow for sysadmin overrides.)

- **FR-14 [Must]** When an account with a callsign is admitted, when a callsign is entered or
  changed (FR-102), and daily thereafter for every account with a callsign, the system
  retrieves license class, expiration date, status, and the licensee name from FCC ULS data
  and records the result with its source and retrieval time. The mechanism (direct ULS
  download, a public ULS mirror API, or another source) is a technical decision for section 6;
  the requirement is that the data are FCC data and are no more than a day stale.
- **FR-15 [Must]** A sysadmin can override class, expiration, or status, with a required reason.
  An override is shown as such wherever the value appears and is never silently replaced by the
  next sync. A sysadmin can lift the override.
- **FR-16 [Should]** If the licensee name returned by ULS does not match the profile name, flag
  it for a sysadmin. **(added)**: catches typos in callsigns and a callsign entered by the wrong
  person.
- **FR-17 [Should]** Notify a member (and guardian) when their license is within 90 and 30 days
  of expiration, and when it has expired. **(added)**: cheap once FR-14 exists, and a lapsed
  license silently breaks slot viability.
- **FR-18 [Must] (added; portability)** Credentials are a general mechanism. A credential type
  has a name, a way of being established (external lookup, signed agreement plus approval, or
  sysadmin assertion), and an optional expiry. W3USR ships with three: *amateur license* (FCC
  lookup, class-graded), *station access* (agreement plus approval, FR-25), and *IT access*
  (agreement plus approval, FR-25). Slot eligibility (FR-53) and slot viability (FR-61) are
  expressed in terms of credential types, so another club can add its own (a tower-climbing
  sign-off, a club-specific safety briefing) without code changes.
- **FR-19 [Must] (portability)** The license class ladder is configuration. W3USR ships with
  the US ladder: Novice < Technician < General < Advanced < Extra. "Minimum class" comparisons
  use this order.
- **FR-20 [Should]** A non-US license (a Canadian community member, for example) is recorded by
  sysadmin override with the issuing country and an equivalent class for comparison purposes.
- **FR-102 [Must]** A member can change their own callsign, since a vanity grant or a new
  sequential call on upgrade replaces it. The change runs the FCC lookup immediately; the
  license fields update from the result, a licensee-name mismatch is flagged per FR-16, and a
  callsign that ULS does not know is held as *unverified* until the daily sync finds it. The
  previous callsign is kept in the account's callsign history with the change date, so past
  rosters and participation reports still read correctly, and the change is written to the
  audit log. A sysadmin override on the license fields (FR-15) survives a callsign change only
  if the sysadmin re-confirms it.

### 3.3 Access agreements and the shared computer password

Verbatim:

> This website is also the system where club members can apply for station swipe card access and
> station computer password access. We need a way of presenting and having members digitally
> sign access agreements, and then have those access agreements be reviewed and approved by a
> faculty advisor. […] Note that there are separate station access agreements for students vs
> community members. Everyone signs the same IT access agreement. Agreement approval should have
> the ability to have an expiration date, typically a year. Those who have approved and current IT
> access agreements should have a way to view the current w3usr computer account password, which
> is rotated on a yearly basis. We should also have the ability to generate reports/rosters of who
> has current station and computer access.

The source agreements are the three documents in the private repository's
`docs/w3usr_access_agreements/`: the Computer Account Usage Agreement (2024-02-10), the
Community Member Station Access Agreement (2024-08-19), and the Student Station Access
Agreement (2025-09-08). The paper forms collect printed name, R number, email, phone, signature
and date, and the faculty advisor's signature and date. The Community Member agreement also
requires a University Non-Employee Affiliate Application with a Pennsylvania State Criminal
Background Check.

- **FR-21 [Must]** The system stores agreement **templates**, each with a type (station access
  or IT access for W3USR), an audience rule (which member categories see it: the student
  station agreement to Students, the community one to Community Members and, pending Q4,
  Faculty and Staff), the full text, a version identifier, and an effective date. Publishing a
  new version never alters or deletes an earlier one, because signed records point at the
  version signed.
- **FR-22 [Must]** A member (or guardian, for a minor) can read the agreement applicable to them
  and sign it digitally. A signature consists of: the signer's typed full name, an explicit
  affirmation checkbox, the timestamp, the signer's account identity, the IP address, and the
  agreement version's content hash. For a minor, the guardian signs and the record says so.
- **FR-23 [Must]** The system renders each signed agreement to a PDF that reproduces the text as
  signed plus the signature block, stores it immutably, and lets the signer and approvers
  download it.
- **FR-24 [Must] (added; resolves a conflict with the repository's privacy rules)** The digital
  agreement does **not** collect or store the University R number. The paper forms do, and the
  swipe-card request to University facilities presumably needs it, but this repository's rules
  forbid storing rosters tied to student IDs. The advisor obtains the R number from University
  systems at the moment of requesting access, outside this application. If that is unworkable,
  Q5 records the alternative.
- **FR-25 [Must]** A signed agreement enters an approval queue visible to approver positions
  (section 2.3). The approver can approve, setting an expiration date (default: one year from
  approval, configurable per agreement type), or decline with a reason that is sent to the
  signer. Approval is itself recorded with the approver's identity and timestamp.
- **FR-26 [Must] (added)** Approval and physical access are two facts. A station-access record
  has the states *signed*, *approved*, *active*, *expired*, *revoked*, *declined*. *Active*
  means the University has actually enabled the swipe card, and is set by an approver with the
  date. The viability check (FR-61) uses *active*, since an approved agreement does not open the
  door.
- **FR-27 [Must]** For the Community Member agreement, the record carries a checklist the
  approver ticks: Non-Employee Affiliate Application submitted, background check cleared. The
  agreement cannot move to *active* until both are ticked.
- **FR-28 [Must]** Approvals expire on their date. The member (and guardian) and the approvers
  are notified 30 days before and on expiry, and the member is prompted to re-sign the current
  version. An expired credential no longer satisfies slot viability.
- **FR-29 [Should]** An approver can revoke an active approval at any time with a reason. The
  system notifies the member and flags every future slot whose viability depended on it.
- **FR-30 [Should]** When a new agreement version is published, the publisher chooses whether
  existing approvals remain valid until their own expiry or all signers must re-sign by a date.
- **FR-31 [Must]** Reports (section 3.9) list who currently holds active station access and
  active IT access, with expiry dates, and who is approaching expiry.
- **FR-32 [Must]** A sysadmin can set the shared W3USR computer account password and its
  effective date. The system stores it encrypted at rest and shows it in the interface only.
  It is **never** included in an email or other message: the agreement the viewer signed says
  "I will not share the password with others or write the password down on paper," and mail is
  both.
- **FR-33 [Must]** A member whose IT-access credential is *active* can view the current
  password after re-entering their own password. Each view is written to the audit log (FR-92)
  with the viewer and time.
- **FR-34 [Should]** On rotation, the system notifies every member with active IT access that
  a new password is in effect and that they must view it in the application. When the previous
  password's holders include people whose IT access has since expired, the rotation notice to
  the sysadmin lists them, since the point of rotating is to cut those people off.
- **FR-35 [Could]** The Computer Account Usage Agreement references a University-approved
  software list "on the back of this agreement". The template supports an appendix, kept
  current by a sysadmin, and the rendered PDF includes it.

### 3.4 Events

Verbatim:

> So, one thing it should be able to do is allow for the scheduling of events, including
> contests. It should have the ability to allow a club officer or site administrator to import
> contest information from https://www.contestcalendar.com/, or to create their own custom event
> or contest. The table of data https://www.contestcalendar.com/ provides for each contest is a
> good starting point for what each event in our database should have. Events should be able to
> be duplicated so that an existing or past event can be used as a template.

- **FR-36 [Must]** Officers and sysadmins can create an event by hand or by import. An event
  has a type (contest, special event, outreach, work party, other; configurable), a title, a
  description, one or more **operating periods** (FR-38), a time zone for display (default the
  club's, `America/New_York`), a location, one or more captains, an optional link to rules, and
  the contest fields of FR-37 where relevant.
- **FR-37 [Should]** Contest events carry the fields the WA7BNM Contest Calendar publishes for
  each contest, verified against the site on 2026-09-12: status, geographic focus,
  participation, awards, mode, bands, classes, max power, exchange, work stations, QSO points,
  multipliers, score calculation, log submission (email, upload URL, postal address), log
  deadline, rules URL, Cabrillo name and aliases, and the calendar's own reference number. All
  are free text except the reference number and the URLs. They inform the know-before-you-go
  text (FR-77) and are otherwise for people to read.
- **FR-38 [Must]** An event has one or more operating periods, each a UTC start and end.
  Contests with an overnight break (the Pennsylvania QSO Party runs 1600Z to 0400Z Saturday
  into Sunday and again 1300Z to 2200Z Sunday) are two periods. Slots are generated within
  periods (FR-46). All times are stored in UTC and displayed in UTC and in the event's display
  zone side by side.
- **FR-39 [Must]** An event can carry **operating-time limits**: a maximum number of on-air
  hours per calendar day (UTC or local, selectable), a maximum total for the event, and a
  minimum break length that counts as off time. School Club Roundup needs all three: the ARRL
  rules say a station "may operate no more than 6 hours out of 24 and may not count more than
  a total of 24 hours of the 107 hour event," and "clearly marked breaks of at least 10 minutes
  may be taken and are not counted towards total operating time." The schedule-health check
  (FR-62) reports when the scheduled slots exceed a limit. Limits are advisory: the system warns
  and never refuses, because the club may schedule setup or listening time that does not count.
- **FR-40 [Must]** **Import from the WA7BNM Contest Calendar.** An officer pastes the URL or
  reference number of a `contestdetails.php?ref=NNN` page. The system retrieves the page,
  populates FR-37, and proposes operating periods from the listed dates, including the
  `A and B` form the calendar uses for split contests (`1600Z, Oct 10 to 0400Z, Oct 11, 2026
  and 1300Z-2200Z, Oct 11, 2026`). The officer reviews and corrects every field before saving;
  the import is a starting point, never authoritative. The record keeps the source URL and
  retrieval time. **Constraint**: retrieval is user-initiated, one page per import, and cached;
  the calendar publishes an iCalendar feed as its machine-readable surface and its detail
  pages are copyrighted. Q11 asks whether to seek WA7BNM's permission or to prefer the feed.
- **FR-41 [Should]** Import can also read the calendar's iCalendar feed to offer a pick-list of
  upcoming contests, so the officer does not have to find the reference number by hand.
- **FR-42 [Must]** Any event can be **duplicated**. The copy carries every field and the slot
  structure (roles, capacities, eligibility rules, know-before-you-go text) and none of the
  sign-ups; the officer supplies new dates and the slots shift with them. The copy records
  which event it came from.
- **FR-43 [Should]** For an imported contest, "create next year's" is a one-step duplication
  that re-reads the calendar for the next listed date.
- **FR-44 [Must]** An event has a lifecycle: *draft* (visible to officers and captains only),
  *published* (visible to members; sign-ups open per FR-54), *locked* (visible; no member
  changes to sign-ups), *completed*, *cancelled*. Cancelling notifies everyone signed up.
- **FR-45 [Should]** Events can be marked as recurring for display purposes (the club's weekly
  net, monthly meeting) without slots; these appear on the calendar and have no roster.

### 3.5 Time slots

Verbatim:

> Events should have the ability to have time slots that people can sign up for. When an event is
> first created, such as from a contest on https://www.contestcalendar.com/, the app should offer
> to automatically create timeslots that match the contest requirements. For instance, if the
> contest starts at 1800 UTC Friday night and goes until 2200 UTC Sunday night, the app should
> offer to automatically create 1 hour time slots throughout the whole weekend from 1800 UTC
> Friday night and goes until 2200 UTC Sunday night. There should also be the option of having
> pre- and post- event time slots to allow for setup and breakdown. Some contests and events do
> not let you operate through the night... I think the PA QSO party is an example of this. Or,
> they may restrict how many hours the station can be active each day throughout the event...
> School Club Roundup is an example of this. We need to account for this somehow.

- **FR-46 [Must]** On creating an event with operating periods, the system offers to generate
  slots: a slot length (default 60 minutes; 30, 90, 120 selectable), aligned to each period's
  start, filling each period, with a final short slot if the period length is not a multiple.
  The officer can accept, edit, or skip the offer. Slots can be added, removed, split, merged,
  and re-timed by hand afterwards.
- **FR-47 [Must]** The generator can add **setup** slots before the first period and
  **breakdown** slots after the last, of chosen length and count, marked as non-operating.
  Non-operating slots do not count toward FR-39 limits and have their own viability rule (they
  need someone who can open the station and nothing else).
- **FR-48 [Must]** For events with a per-day operating limit (FR-39), the generator asks the
  officer which hours on each day the club intends to operate (School Club Roundup runs
  Monday 1300Z to Friday 2359Z; the club will pick perhaps 1500Z to 2100Z each weekday) and
  generates slots only in those windows. The club chooses the hours; the system checks them.
- **FR-49 [Must]** Each slot has capacity per **role**. The roles are *operator*, *mentor*, and
  *observer*, each with a maximum count (0 to disable the role for that slot). Event-level
  defaults apply to generated slots and can be overridden slot by slot.

  > For each time slot that people can sign up for, they can sign up as an operator, mentor, or
  > observer. We should be able to limit the number of available operator, mentor, or observer
  > slots on an event-by-event and even slot-by-slot basis.

- **FR-50 [Should] (portability)** The role list is configuration; W3USR ships with the three
  above. Roles carry a flag for whether they count as "on the air" for the viability rule.
- **FR-51 [Should] (added)** A slot can belong to a **position** (a named operating station,
  such as *Run* and *Multiplier*). An event has one position by default. Multi-transmitter
  contests, or an event that puts a satellite station and an HF station on the air at once,
  add positions, and the roster shows them as parallel columns. This costs little if designed
  in and is expensive to retrofit; the advisor confirms whether W3USR needs it (Q12).
- **FR-52 [Should]** A captain can mark a slot as *closed* (not bookable, shown greyed) and as
  *cancelled* (removed from the schedule with notice to anyone signed up).

### 3.6 Eligibility and sign-ups

Verbatim:

> We should be able to designate when categories of people can sign up for certain slots. For
> instance, we might initially open Operator slots to students, while mentor slots might be
> open to all members with a certain minimum license class.

- **FR-53 [Must]** Each role in each slot has an **eligibility rule**, defaulted at event level
  and overridable per slot, composed of: allowed member categories; minimum license class (or
  none); required credentials (from FR-18, any combination); whether minors may sign up; and
  an **opening schedule** (FR-54). A member sees only the roles they are eligible for, with the
  reason shown for roles they are not.
- **FR-54 [Must]** The opening schedule belongs to a role, so each role in an event opens on
  its own terms: for example, mentor and observer roles open to every member as soon as the
  event is published, while operator roles open to Students first and to everyone on a later
  date the captain sets (or never, if the captain prefers to hand out the remaining operator
  slots by hand). The schedule is a list of (date-time, audience) pairs per role. The system
  sends the announcement of each opening (FR-80) automatically if the captain enables it.
- **FR-55 [Must]** An eligible member signs up for a slot in a role in one action, and can
  select a run of consecutive slots at once. A guardian does the same for a minor.
- **FR-56 [Must]** A member can cancel their own sign-up up to a configurable cutoff before the
  slot (default 24 hours). Inside the cutoff, cancellation still works but is flagged *late*
  and the captains are notified immediately. Cancellation always tells the captains.
- **FR-57 [Should]** When a role in a slot is full, an eligible member can join a **waitlist**.
  If a place opens, the first waitlisted person is offered it by message and has a configurable
  window to accept before it passes to the next.
- **FR-58 [Must]** Captains, officers, and sysadmins can add, move, or remove any sign-up, with
  a notice to the person affected.
- **FR-59 [Should]** A member sees "my schedule": every slot they hold across all events, with
  an iCalendar feed URL they can subscribe to from a phone or desktop calendar **(added)**: the
  cheapest possible reminder channel, and it works offline.
- **FR-60 [Could]** A member can record a **preference** without committing to a slot ("I could do any
  two hours Saturday afternoon"), which captains see as they fill gaps. Deferred unless captains
  ask for it.

### 3.7 Roster and schedule health

Verbatim:

> When we look at the roster page for an event, we should quickly be able to see who is signed
> up for when, and where there are missing slots. In order for a time slot to run, it must have
> at least one person with a valid ham radio license, one person with swipe card access to the
> station, and one person with a currently approved IT agreement. This can be held by one person,
> or it can be two separate people (i.e. one license amateur working with a faculty member who is
> unlicensed but has swipe card access.) On an event by event basis, we shoud be able to specify
> the minimum license class required.

- **FR-61 [Must]** A slot is **viable** when, among the people signed up in on-air roles, the
  event's viability rule is satisfied. W3USR's default rule: at least one person holds an
  active amateur license of at least the event's minimum class; at least one person holds
  active station access; at least one person holds active IT access. One person may satisfy
  all three. The rule is expressed over credential types (FR-18) and is editable per event
  **(portability)**.
- **FR-62 [Must]** Each slot displays one of: *empty* (no one signed up), *not viable* (people
  signed up but the rule fails, with the specific missing credential named), *viable*, and
  *at risk* (viable only because of one person; if they cancel, it fails). A slot also shows
  *over limit* when it would push the event past an FR-39 operating-time limit. Status is
  conveyed by icon and text as well as colour, in a colour-blind-safe palette.
- **FR-63 [Must] (added; FCC Part 97)** For each viable slot, the roster names the **control
  operator**: the licensed person whose license class governs what the station may do during
  that slot. Part 97 requires a control operator for every transmission and limits the station
  to the control operator's privileges (§97.7, §97.105); unlicensed participants may speak
  under the control operator's supervision as third parties (§97.115). The default is the
  highest-class licensee signed up in an on-air role; a captain can change it; the person
  named is told in their reminder. This makes the dictation's "minimum license class" concrete:
  it is the class the control operator needs for the bands and modes the event uses.
- **FR-64 [Must] (added; from the chaperone rule in section 2.4)** If a minor is signed up in a
  slot, the slot is *not viable* unless one of the minor's authorized chaperones is also signed
  up in that slot, in any role. The missing-credential text says whose chaperone is absent.
- **FR-65 [Must]** The **roster page** for an event shows every slot in time order, grouped by
  day, with position columns where FR-51 applies, each person's name, callsign, role, and
  compact credential badges (license class, station access, IT access, control operator), the
  slot's status, and a filter for "problems only". Times show in UTC and the event's display
  zone. The page works at phone width and has a print layout.
- **FR-66 [Must]** An **event health summary** at the top of the roster and on the event list:
  slots total, viable, at risk, not viable, empty; hours scheduled against each FR-39 limit;
  and the number of unconfirmed sign-ups in the next 48 hours.
- **FR-67 [Must]** Members see names, callsigns, and roles on the roster. Phone numbers and
  email addresses are visible to captains of that event, officers, and sysadmins only.
- **FR-68 [Should]** A cross-event view for officers: every event in the next N weeks with its
  health summary, so that a quiet Tuesday-evening problem is seen on Tuesday.

### 3.8 Communications

Verbatim:

> People who sign up for slots should get reminder emails 24 hours before their slot takes place
> and ask them to confirm. The reminder email should provide all of the important
> know-before-you-go information, as well as who to contact (the event captains(s)) in the event
> of an issue. Event captains and people who sign up for slots should receive a warning email and
> notification in the event their time slot is in danger of being cancelled because we do not
> have the correct combination of licensed people and people with station access.

> There should be a way for event captains, club officers, and sysadmins to quickly evaluate the
> schedule health of an event, as well as contact all (or a subset of) people signed up for the
> event. Announcement emails can come from ops@w3usr.org. Replies can go to the event captains,
> person sending the message, and w3usr@scranton.edu.

> The server must be able to send email notifications from ops@w3usr.org. Possibly also text
> messages and push notifications. Push notifications definintely when we develop a mobile app.

#### 3.8.1 Email independence

Added 2026-09-13 at the advisor's direction, after the decision to self-host outbound mail
made it likely that reliable delivery would take time to establish:

> Let's add to the requirements some route that the system is still useful even if email
> breaks. I can see getting the outbound email going could possibly take some time if I have
> to deal with waiting for domains to get white listed or otherwise figuring out how to make
> sure things don't show up as spam.
>
> So, no action should absolutely require email. For instance, For the invite process, the
> system can show the officer creating the invite an invite link and text that could be
> manually mailed to a person.
>
> Also, there should be a "forgot username or password" link on the front page. That will of
> course require email to work.

- **FR-103 [Must]** No action in the system requires an email to be delivered. Every flow that
  sends a message also has a path inside the application that reaches the same end, and a new
  feature that sends a message adds its own row to this table before it ships.

  | Flow | The message | The email-free path |
  |---|---|---|
  | Invitation | Invitation link | Issuer sees the link and a ready-to-send text (FR-104) |
  | Application admitted or declined | Notice | Status shown on the applicant's next sign-in attempt; issuer can tell them |
  | Forgotten password | Reset link (FR-107) | Sysadmin issues a temporary password in the interface (FR-7) |
  | Slot reminder and confirmation | Reminder with confirm link (FR-72) | "My schedule" shows the slot, its details, and confirm / cannot-make-it buttons (FR-59) |
  | At-risk warning | Warning (FR-73) | Roster status and health summary (FR-62, FR-66); in-application notifications (FR-108) |
  | Announcement | Bulk message (FR-75) | Visible in each recipient's "my messages" (FR-82); officer can export the recipients and body to send from their own mail client (FR-106) |
  | Agreement submitted, approved, declined, activated, expiring | Notices (FR-76) | Approver queue and the member's agreements page show the state; expiry countdown on the profile |
  | Computer password rotated | Notice (FR-34) | Banner for eligible members on sign-in |
  | License expiring | Notice (FR-17) | Banner on the member's profile |
  | Cancellation of a slot, event, or sign-up | Notice (FR-74) | "My schedule" and the roster reflect it immediately; notification (FR-108) |

- **FR-104 [Must]** When an invitation is created, the issuer is shown the invitation link and
  a ready-to-send text (who is inviting, to what, the link, its expiry, and the club contact),
  each with a copy button, so the issuer can deliver it by their own email, a message, or in
  person. The link is the same single-use, expiring token whether the system or the issuer
  delivers it. The invitation record shows whether the system's own email went out, so the
  issuer knows when delivery is theirs to do.
- **FR-105 [Must]** A sysadmin setting, **email delivery: on / off**, audited. When off, the
  application composes and records every message exactly as it otherwise would, marks it
  *not sent (email off)*, and shows it in the recipient's "my messages" and in an officer-visible
  outbox. Nothing is held for later sending: a reminder delivered a day late is worse than
  none, and the in-application copy is already there. When on, each message's state (sent,
  failed) is recorded and failures appear in the outbox. The current mode is visible to
  officers on the dashboard, so they know when delivery is theirs to do.
- **FR-106 [Must]** When composing an announcement, an officer or captain can, before sending or
  without sending it, copy the resolved recipient list as a comma-separated address list
  (for the BCC field of their own mail client) and the message body. The announcement is still
  recorded per FR-75, marked *sent outside the system*. This shows addresses to people who may
  already see them (section 2.5) and to no one else.
- **FR-107 [Must]** The sign-in page carries a **"Forgot username or password?"** link. The
  member enters one identifier they know: either email address on file, or their callsign. If it
  matches an account, reset instructions go to every email address on that account (the
  guardian's, for a minor). The page's response is the same whether or not a match exists, so
  the form cannot be used to discover who has an account. This path needs working email; when
  email delivery is off (FR-105), the link leads to a page saying that resets are done by a club
  officer, with the club contact, and the sysadmin uses FR-7.
- **FR-108 [Should]** In-application notifications: an unread-messages indicator and a dashboard
  banner for anything that would otherwise be a warning email (a slot at risk, an agreement
  expiring, a rotated computer password). The in-application half of FR-73 and FR-76.

#### 3.8.2 Sending

- **FR-69 [Must]** All system mail is sent from `ops@w3usr.org` (configurable, **portability**)
  with a display name naming the club. Transactional mail (invitations, resets, reminders,
  warnings) has `Reply-To` set to the club address; announcements have `Reply-To` set to the
  sender, the event's captains, and the club address.
- **FR-70 [Must]** Every message to a member is delivered to the address(es) their preference
  selects. Every message to a minor is delivered to the guardian's address(es), with the
  minor's own address included only if one is on file. There is no path by which a minor is
  messaged without the guardian.
- **FR-71 [Must]** Members can opt out of announcements and of the digest (FR-79). Members
  cannot opt out of messages about slots they hold (reminders, warnings, cancellations) or
  about their own account and credentials, since those messages exist to protect the club and
  the member.
- **FR-72 [Must]** **Reminder**: 24 hours before each slot (configurable per event), each
  person signed up receives a message with the slot time in UTC and local, their role, the
  control operator's name, the other people in the slot, the know-before-you-go text, the
  captains' names and contact details, and a one-click **confirm** link that works without
  signing in (a signed, single-use token) plus a **cannot make it** link that opens the
  cancellation flow. The same confirm and cannot-make-it actions are on the member's "my
  schedule" page (FR-59), so confirming never depends on the message arriving. Confirmation
  state shows on the roster.
- **FR-73 [Must]** **At-risk warning**: when a slot inside a configurable horizon (default
  72 hours) is *not viable*, *at risk*, or has an unconfirmed sign-up within 24 hours, the
  captains receive a warning, and the people signed up receive a message saying what is
  missing and asking them to help fill it. Warnings for one slot are rate-limited (at most one
  per state change per 12 hours) so a problem generates one clear signal.
- **FR-74 [Must]** **Cancellation notices**: when a slot, an event, or a sign-up is cancelled
  by someone other than the member, everyone affected is told, with the reason if one was given.
- **FR-75 [Must]** **Announcements**: captains (for their events), officers, and sysadmins can
  compose a message to a chosen audience: everyone signed up for an event, a subset filtered by
  day, role, slot status, confirmation state, or member category, or all members. The sender
  sees the recipient count before sending. Every announcement is recorded (sender, audience
  definition, resolved recipient list, body, time) and is visible to officers afterwards.
- **FR-76 [Must]** Account and credential messages: invitation, application received,
  admitted or declined, welcome, password reset, agreement submitted (to approvers), agreement
  approved, declined, activated, expiring, expired, revoked (to signer), computer password
  rotated (FR-34), license expiring (FR-17).
- **FR-77 [Must]** Each event has a **know-before-you-go** text, edited by captains, included
  in every reminder: where the station is and how to get in, parking, what to bring, the
  exchange, the logging setup, the rules link. A duplicated event carries it forward, so it
  becomes a living document per contest.
- **FR-78 [Must]** All messages are rendered from templates that a sysadmin can edit in the
  interface, with the variables each template may use documented beside it **(portability)**.
- **FR-79 [Should]** A weekly digest to members: upcoming events, slots still needing people,
  and the member's own commitments. Opt-out per FR-71.
- **FR-80 [Should]** When an opening in a slot's schedule (FR-54) fires, an announcement to
  the newly eligible audience, if the captain enabled it.
- **FR-81 [Must]** Outbound mail carries proper authentication for the sending domain so it is
  delivered to the inbox; the private orchestration repository owns the DNS records this
  requires. Announcements to a list carry a working unsubscribe link and a `List-Unsubscribe`
  header, which large receivers expect from any sender of list mail and which FR-71 already
  provides for. **[Should]** The application records delivery failures (bounces) against the
  address and shows them to officers, since an unread reminder is the same as no reminder; in
  v1 bounces are readable in the club mailbox (section 6).
- **FR-82 [Must]** Every message the system sends, or would have sent, to a person is visible
  to that person in the application ("my messages"), so a lost or undelivered email is
  recoverable and a guardian can see what a minor was sent. (Promoted from Should on
  2026-09-13; it is the in-application half of FR-103.)
- **FR-83 [Later]** SMS and push notifications. The notification layer is designed so that a
  channel is an implementation of one interface and a member preference; v1 implements email
  only. Web push from an installed progressive web app (section 5.4) is the likely first
  additional channel, ahead of SMS, because it has no per-message cost.

### 3.9 Reports and exports

- **FR-84 [Must]** **Access rosters**: who currently holds active station access and active IT
  access, with category, approval date, approver, expiry, and days remaining; sortable and
  filterable by expiring-within-N-days. Officers and sysadmins; downloadable as CSV.
- **FR-85 [Must]** **Event roster export**: the FR-65 roster as CSV and as a printable page.
- **FR-86 [Should]** **Participation report** per event and per period: hours scheduled, hours
  covered, hours viable, people who participated, first-time participants. This is what the
  club reports to the University and puts in a grant application, so it should be right.
- **FR-87 [Should]** **Member roster** for officers: name, callsign, category, position,
  license class and expiry, access credentials and their expiry, access level, last sign-in.
  Contact details are a separate, deliberately clicked export.
- **FR-88 [Could]** Per-member participation history, visible to the member.

### 3.10 Administration and audit

- **FR-89 [Must]** Sysadmins edit club configuration in the interface: club identity, sending
  and reply-to addresses, member categories, club positions and which are approvers, roles,
  credential types, license ladder, default slot length, default cutoffs and horizons, message
  templates **(portability)**.
- **FR-90 [Must]** Sysadmins manage agreement templates (FR-21) and the computer password
  (FR-32).
- **FR-91 [Must]** Sysadmins can set an account's access level to No access with a reason, and
  restore it. Doing so removes the person from future slots and notifies the captains of those
  events.
- **FR-92 [Must]** An **audit log**, append-only and readable by sysadmins, records: access
  level and club position changes, category changes, license overrides, agreement approvals,
  activations, revocations and declines, computer password sets and every view, invitations
  issued, applications admitted or declined, announcements sent, sign-ups moved or removed by
  someone other than the member, configuration changes, and sign-ins by sysadmins. Each entry
  carries actor, subject, action, timestamp, and the before and after values where they exist.
- **FR-93 [Should]** Scheduled jobs (FCC sync, reminders, warnings, expiry notices, digest)
  report their last run and outcome on a status page for sysadmins, and a job that has not run
  on schedule raises an alert. A reminder system that silently stops is worse than none. The
  same page shows email delivery health: the delivery mode (FR-105), messages sent and failed
  in the last 24 hours, and the last successful delivery time.
- **FR-94 [Must]** Sysadmins can impersonate a member's *view* (read-only) to reproduce what
  the member reports seeing. Impersonation is audited and never permits actions.

### 3.11 Deferred candidates (from the requirements skeleton; not in v1 unless promoted)

Recorded so a later session does not re-derive them.

- **Logging.** Does the application log QSOs itself, or ingest logs (ADIF, Cabrillo, N1MM+
  UDP broadcast) from the station computers? A live "who is on the air now and what is the
  score" panel during a contest would be a natural extension of the roster page. Relationship
  to LoTW, Club Log, QRZ.
- **Station and equipment.** Inventory, antenna and band availability, known faults, a
  "report a problem" form that the agreements already require members to use ("I will
  immediately report any issues regarding station equipment to the W3USR faculty advisor").
  The report form is the cheapest and most useful piece and could be promoted to v1.1.
- **Integrations.** QRZ XML, HamQTH, space-weather indices, PSKReporter, HamSCI products. None
  is needed for the v1 purpose.
- **Public content.** Anything a visitor sees beyond a sign-in page (FR-98).

---

## 4. Data

### 4.1 What the application stores

Entities implied by section 3: club configuration; users (with guardian links and chaperone
authorizations); invitations; applications; credentials (license records with sync history and
overrides; agreement templates and versions; signed agreements with rendered PDFs; approvals
with state history); the computer password (encrypted) and its rotation history; events;
operating periods; operating-time limits; positions; slots; role capacities and eligibility
rules; opening schedules; sign-ups with confirmation state; waitlist entries; messages sent
(with recipient resolution and delivery state); message templates; announcements; audit log;
scheduled-job status.

### 4.2 Personal data and minimisation

The application will hold information about identifiable students and about minors. The
following are binding:

- Callsigns and names are public in the FCC ULS database and may be shown to signed-in members.
  **A roster that joins a callsign to a time and a place is exactly the aggregation the club's
  rules forbid publishing**, so rosters are never visible without sign-in (FR-98) and never
  exported to anywhere public.
- Student records covered by FERPA never enter this system: no grades, no R numbers (FR-24), no
  class schedules, no advising or disciplinary information.
- The only personal data collected are the FR-8 fields, each of which a named requirement uses.
  Adding a field requires naming the requirement that needs it.
- Phone numbers and email addresses are shown to captains, officers, and sysadmins only
  (FR-67), and are exported only by a deliberate action that is audited (FR-87).
- Data about minors and their guardians are the most sensitive the system holds. They are
  visible on the same terms as adult contact data and no wider.
- The IP address recorded with a signature (FR-22) exists to make the signature evidentially
  useful and is shown only on the rendered agreement.

### 4.3 Retention (proposed; the advisor's call, Q8)

| Data | Retain | Then |
|---|---|---|
| Profile of a member set to No access | 2 years from the change | Delete contact details and phone; keep name, callsign, and participation history as club record, or delete entirely on request |
| Guardian records | Until the minor's account is converted or closed | Delete |
| Signed agreements and approval history | Per the University's record-retention requirement for the paper equivalents, once established | Archive outside the application or delete |
| Audit log | Indefinitely | Nothing; it is small and it is the record |
| Messages sent | 1 year | Delete bodies; keep the fact and recipient count |
| Invitations never completed | 90 days after expiry | Delete |

### 4.4 Storage, backup, and recovery

Technical decisions for the next phase. The requirement they must meet: a nightly backup of
the datastore and the signed-agreement PDFs to a location other than the server, encrypted,
with a restore rehearsed and dated before the first live event. The club runs a 1 GB Nanode;
pick accordingly.

---

## 5. Non-functional requirements

**5.1 Hosting.** Deployed to `ops.w3usr.org`, a Linode Nanode (1 vCPU, 1 GB RAM, 25 GB disk,
US-Newark), fronted by Cloudflare. Provisioning and deployment are orchestrated from the club's
private `w3usr.org-PRIVATE` repository, which also owns the DNS records that outbound mail
requires (FR-81).

**5.2 Resource budget.** 1 GB of RAM is the binding constraint on the stack choice. The
application also needs a scheduler for daily and hourly jobs (FR-14, FR-72, FR-73, FR-28) and
an outbound mail path; both must fit in the same box or be delegated to a service the club can
afford.

**5.3 Accessibility.** WCAG 2.1 AA. Slot status is never conveyed by colour alone (FR-62). The
roster and sign-up flows work by keyboard and with a screen reader. See
`.claude/rules/web-development.md`.

**5.4 Responsive design and the mobile path.** Verbatim:

> The web app must display and work well on desktop and mobile browsers. We should have a path
> for making a W3USR Ops mobile app for Android and iOS, too.

- **FR-95 [Must]** Every member-facing page (sign-in, my schedule, event list, roster, sign-up,
  agreements, computer password, messages) is designed for phone width first and works
  without horizontal scrolling. Officer and sysadmin pages work on a phone and are laid out
  for a desktop.
- **FR-96 [Should]** The application is an installable **progressive web app**: a manifest,
  an icon, and a service worker that caches the shell and the member's own schedule for
  offline reading. This gives a home-screen icon on Android and iOS today, and is the
  prerequisite for web push (FR-83), with no app-store dependency.
- **FR-97 [Later]** A native app, if the club still wants one after the PWA is in use, talks
  to the same API the web front end uses. **Design consequence for section 6**: the server
  exposes its functionality through a documented API from the start, and the web interface is
  a client of it, so that a second client is an addition.

**5.5 Visitors.**

- **FR-98 [Must]** A visitor who is not signed in sees a sign-in page with the club's name and
  a link to the University club page, and nothing else. No event details, no names, no rosters.
  Whether to show a bare list of upcoming event names and dates to visitors is Q13.

**5.6 Availability.** The application is a coordination tool. If it is down during a contest,
the contest continues from the last printed or emailed roster; FR-72's reminders and FR-59's
calendar feed exist partly for this reason. Target: available whenever anyone would reasonably
look at it, restored within a working day from backup after a total loss. No offline path
beyond the calendar feed and the cached PWA schedule is required.

**5.7 Security.** Threat model at minimum: an attacker with a member's password (motivates
FR-33's re-authentication and section 2.6's second factor for privileged accounts); an attacker
reading the database backup (motivates encryption of the computer password and of backups);
a member trying to see other members' contact details (motivates FR-67); phishing that imitates
the club's mail (motivates FR-81 and a consistent, plain message design). All input validated
and escaped; dependencies kept current; no secrets in this public repository.

**FR-99 [Must]** Rate-limit sign-in and password-reset attempts; lock an account after repeated
failures and tell the owner.

**FR-100 [Must]** Signed single-use tokens (confirm links, reset links, invitations) expire and
are bound to one action; a used or expired token shows a clear message and a route to sign in.

**FR-101 [Must]** A privacy notice, presented at application and reachable from every page,
states what is collected, who sees it, how long it is kept (section 4.3), and how to ask for
closure (FR-11). The advisor approves its text.

**5.8 Continuity.** Club members graduate. The stack must be one an undergraduate who has never
seen the code can run locally in an afternoon from the onboarding document, and every
club-specific fact must be in configuration (section 1.5) so that a new officer can change an
address or an agreement text without a developer.

**5.9 Time.** All times are stored in UTC. Displays show UTC and the event's zone together
wherever a time is shown, because amateur radio runs on UTC and people live in local time, and
because the autumn contest season straddles the end of daylight saving time (the ARRL November
Sweepstakes weekends can include the change). Slot boundaries never move when the clocks do.

---

## 6. Technology

**Undecided, deliberately.** The stack follows from sections 3 through 5 and gets chosen in the
technical-requirements phase. Record the decision here with its reasoning when it is made.

- **Language and framework**: {{TBD}}
- **Datastore**: {{TBD}}
- **Front end**: {{TBD}}
- **Outbound mail**: **decided 2026-09-13 by the faculty advisor**: a Postfix instance on the
  origin server, listening on the loopback interface only, DKIM-signing and delivering
  directly. The application sends over plain SMTP to `localhost` with no credential. Reason:
  the club has no budget for a transactional provider. Consequences: the SMTP endpoint is a
  configuration value, so a provider can be substituted by changing the server's relay with
  no application change; and in v1 bounces arrive in the club mailbox via the domain's inbound
  routing, so FR-81's in-application bounce record waits on an inbound hook.
- **Scheduler**: {{TBD}}
- **FCC ULS access**: {{TBD: direct ULS data download, a public mirror API, or other; see FR-14}}
- **Build and deploy**: {{TBD}}
- **Testing**: {{TBD}}

Constraints any candidate stack must satisfy, now including those the functional requirements
impose:

- Runs within a 1 GB Nanode alongside nginx, with the scheduler and mail path accounted for.
- Maintainable by undergraduate club members with turnover every few years.
- GPL-3.0 compatible.
- Exposes a documented API that the web interface consumes (FR-97).
- Installable as a PWA (FR-96).
- Renders PDFs (FR-23).
- Encrypts a secret at rest with a key held outside the database (FR-32).

---

## 7. Licensing and governance

- This repository is licensed **GPL-3.0-or-later**. Dependencies must be compatible with it.
- AI-assisted work here follows `.claude/rules/ai-governance.md`: every substantive session is
  logged in `ai/ai_usage_log.md` before the work is committed.
- The University of Scranton's name, seal, and logos are the University's marks. The W3USR club
  logo in `web/assets/` comes from the club's own asset library. Using a University mark needs
  the advisor's sign-off. The paper agreements carry the University seal; the rendered digital
  agreements (FR-23) may only do so with that sign-off.
- The agreement texts are the club's and the University's documents. They are configuration
  data (FR-21), and the W3USR texts are **not** committed to this public repository; a second
  club supplies its own.

---

## 8. Open questions for the advisor

Each has the draft's recommendation, so that a one-word answer suffices where the
recommendation is acceptable.

1. **v1 scope.** Adopt section 1.3's deferrals (no logging, equipment, or public content in v1)?
   *Recommend yes.* The dictation describes a complete, coherent v1 without them.
2. **Priorities.** Accept the Must / Should / Could tags as drafted, or re-tag? The Musts are
   the dictation's content plus the minimum the draft found necessary to make it safe (expiry,
   review, audit, control operator, chaperone check, R-number exclusion).
3. **Application review.** Is an application reviewed by an officer before access is granted
   (FR-5), or does completing the form admit the person? *Recommend review.* The inviter knows
   the person; the review is one click, and it is where the category is confirmed.
4. **Which station agreement do Faculty and Staff sign?** The paper forms exist for Students and
   for Community Members only. *Recommend: Faculty and Staff sign the Community Member
   agreement's text with the affiliate-application clause removed*, or a third template. The
   application supports any answer (FR-21).
5. **R numbers.** Confirm FR-24: the digital agreement does not collect the R number, and the
   advisor obtains it from University systems when submitting the swipe-card request. If the
   University's process requires it on the signed form itself, the alternative is to collect it
   into the rendered PDF only and never into a queryable field; that is still a stored student
   ID and would need the repository's privacy rules amended.
6. **Can a minor sign in at all?** *Recommend no in v1* (section 2.4). A read-only view for the
   minor is possible later.
7. **Date of birth or a boolean?** Automatic handling of the 18th birthday (section 2.4) needs
   the date. *Recommend the boolean plus an optional "turns 18 on" date entered by the inviter*,
   which drives the notification without storing a full birth date for adults.
8. **Retention.** Accept section 4.3, and does the University specify a retention period for
   signed access agreements?
9. **University SSO** as an extra sign-in path for `@scranton.edu` users: worth asking IT now,
   or leave for later? *Recommend later*; the club-managed path is required regardless.
10. **Member directory** (FR-13): wanted, or is the roster enough?
11. **Contest calendar import.** Seek WA7BNM's permission for page retrieval, rely on the
    iCalendar feed plus manual entry of the detail fields, or both? *Recommend writing to
    WA7BNM*; the use is modest and the courtesy is cheap, and the answer settles FR-40.
12. **Positions** (FR-51): does W3USR run more than one station at once in any event it
    schedules? If never, drop FR-51 to Could.
13. **Visitors** (FR-98): show a bare list of upcoming event names and dates without sign-in,
    or nothing?
14. **Minors on campus.** Does the University have a policy governing minors participating in
    campus programs (background checks or training for chaperones, sign-in requirements)? If so,
    it constrains who may be an authorized chaperone (section 2.4) and may add a credential type
    (FR-18). The draft does not know and has not assumed.
15. **Contact for issues.** The reminder names the captains (FR-72). Should it also name the
    faculty advisor as a fallback, given the agreements route equipment problems to the advisor?

---

## 9. Source and decision record

**Source.** The dictation is `prompts/20260912_create_ops_site_requirements.md` in the private
`w3usr.org-PRIVATE` repository, written by N. A. Frissell on 2026-09-12. Its substantive
paragraphs are quoted verbatim in the sections they drive. This draft was prepared the same day
by the assistant from that file, the three agreement documents, the WA7BNM Contest Calendar
(field list and the split-period notation, read 2026-09-12), the ARRL School Club Roundup rules
page (read 2026-09-12), and the Pennsylvania QSO Party 2026 rules (`paqso.org`, §2.a, read
2026-09-12).

**Where the draft went beyond the dictation, and why.** Each is a proposal for the advisor to
accept, amend, or strike.

| Addition | Why |
|---|---|
| Credentials as a general mechanism (FR-18) with the viability rule expressed over them (FR-61) | The dictation's three requirements (license, swipe access, IT agreement) are three instances of one pattern. Naming the pattern is what makes the application usable by another club, which the dictation asks for. |
| Approved versus active station access (FR-26) | An approved agreement does not open the door; the University does. The viability check has to test the fact that matters. |
| Control operator named per slot (FR-63) | Part 97 makes one licensed person responsible for every transmission and limits the station to that person's privileges. "At least one licensed person" is necessary but does not say who, and "minimum license class" is a statement about the control operator. |
| Chaperone check in slot viability (FR-64) | The dictation states the chaperone rule as a policy; making it a viability condition is how the roster enforces it. |
| No R number (FR-24) | The paper forms collect it; the repository's rules forbid storing student IDs. The two conflicted and one had to yield. |
| Password never emailed (FR-32) | The agreement being signed forbids writing the password down or sharing it. Emailing it does both. |
| Invitation expiry and application review (FR-3, FR-5) | Standard hygiene for an invitation-only system; the dictation is silent. |
| Self-service password reset (section 2.6) | Removes routine work from the sysadmin; the sysadmin path the dictation asked for remains. |
| Audit log (FR-92) | The system approves access to a room and displays a shared password; who did what and when has to be recoverable. |
| Waitlist (FR-57), calendar feed (FR-59), digest (FR-79), messages page (FR-82) | Cheap once the core exists; each closes a way a slot goes uncovered or a message goes unread. |
| Positions (FR-51) | Cheap to design in, expensive to retrofit; flagged as Should pending Q12. |
| PWA and an API-first server (FR-96, FR-97) | The dictation asks for a path to native apps; this is the path that costs least and keeps the option open. |
| Operating-time limits are advisory, never enforced (FR-39) | The club may schedule non-counting time (setup, listening). A system that refuses to schedule is wrong more often than one that warns. |

**Decisions taken after the first draft.**

- 2026-09-12, NAF: *"members should be able to change their call sign. this might happen if
  they get a vanity call or request a new sequential call on upgrade"*. Applied as FR-102 and
  the callsign row of FR-8; the first draft had made the callsign sysadmin-only alongside the
  license fields, which remain so because they come from the FCC.
- 2026-09-13, NAF: the system must stay useful if email breaks (quoted in full in section
  3.8.1). Applied as FR-103 to FR-108, with FR-82 promoted to Must, in-application confirmation
  added to FR-72, mail health added to FR-93, and the invitation flow in section 2.7 and FR-3
  showing the link to the issuer.
- 2026-09-13, NAF: *"Sysadmins should be able to reset passwords for accounts and set a
  temporary, one-time use password. This would enable password reset without email."* Already
  FR-7 from the dictation; its text now says one-time use and unused-expiry explicitly.
- 2026-09-13, NAF, on the definition of done's "opens sign-ups to students first and then to
  everyone": *"I may offer operator sign-ups to students first, but anyone available can sign
  up for a mentor slot or observer slot. Later, I may allow anyone to sign up for an open
  operator slot."* Openings are per role (FR-53, FR-54 already modelled them so); §1.4 and
  the FR-54 example now say it the same way.

**Where the draft chose a reading of the dictation.** "Club officers can only send invitations"
was read as *relative to sysadmins' account powers*: officers cannot create or edit accounts
or reset passwords, and they can still do the event, announcement, and reporting work the rest
of the dictation gives them. If the advisor meant officers to have no account powers beyond
inviting, section 2.5's officer column changes and nothing else does.

---

<sub>Drafted by Claude (Anthropic), `claude-fable-5-1`, under W2NAF's direction, from his dictated
requirements of 2026-09-12 and the sources named in section 9. Every requirement is a proposal
until adopted; the decisions are the club's.<br>Co-Authored-By: Claude Fable 5.1
&lt;noreply@anthropic.com&gt;</sub>
