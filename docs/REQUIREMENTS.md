# ARCOps: Requirements

*ARCOps is the product; `ops.w3usr.org` is W3USR's installation of it. See `NAME.md`.*

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
| **Document status** | Draft; all section 8 questions answered 2026-09-13; the build began the same day on the advisor's instruction; formal adoption pending his read |
| **Last revised** | 2026-09-13 |
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

### 1.3 Out of scope for v1 (adopted by the advisor 2026-09-13, Q1)

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
- **SMS notifications.** Designed for (FR-83), built later. Browser notifications are in v1
  (FR-112).
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

The dictation names four levels; a fifth, **Provisional**, was added on 2026-09-15 (FR-121). They
are mutually exclusive and every account holds exactly one.

| Level | Who | Summary of powers |
|---|---|---|
| **Sysadmin** | The people who run the application | Everything, including manual account creation and editing, password resets, privilege fields, configuration, and overrides of automated data |
| **Club officer** | Elected officers and the faculty advisors | Send invitations; create, edit, and captain events; send announcements; view reports; approve applications. Cannot edit another account's privilege fields or reset passwords |
| **Member** | An admitted member in good standing | Edit own non-privilege profile fields; view schedules and rosters; sign up for slots; sign agreements; view the computer password when eligible |
| **Provisional** | Someone who joined through a community entry link (FR-119) and has not yet been reviewed by an officer | Sign in; see events; sign up for slots the role rules allow (Mentor, given a license); on a roster see their own name and the count of people by license class, nothing more. No directory, no other names or contact details, no agreements. Becomes Member on an officer's review (FR-121) |
| **No access** | Account exists; sign-in refused | Nothing. Used for graduated, lapsed, or suspended members, for declined Provisional accounts, and for class-link accounts whose address went unverified (FR-120) |

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
  them: completes the application, edits the profile, signs up for slots, and
  receives every message. A minor may have **more than one guardian account** linked; every
  linked guardian can act and every one receives every message. A guardian need not be a
  member; if the guardian is also a member, one account holds both.
- The minor's own account **can sign in, read-only** (NAF, Q6): the minor sees their own
  schedule, the rosters of events they are in (short names, FR-67), and the messages sent to
  them, and can change their own password. They cannot sign up, cancel, change role, check in,
  sign anything, or edit the profile; those are the guardian's. The guardian sets the minor's
  initial password and can reset it (as FR-7, from the guardian's account). Read-only is a
  restriction that follows from the under-18 flag, and no fifth access level is introduced.
- The guardian record holds the guardian's name, relationship, email(s), and phone. The minor's
  own email and phone are optional.
- When a guardian signs the minor up for a slot, the guardian designates the **responsible
  adult(s)** who will accompany the minor for that slot (FR-64). A responsible adult takes no
  place in the slot and need not be a member; the guardian may name themselves. The system
  keeps the adults a guardian has named before, so a repeat designation is a pick from a list.
  This is how the University's policy on minors in campus programs is met: the advisor's
  statement (Q14) is that the policy is satisfied so long as a guardian-approved responsible
  adult chaperones the minor at all times, and that is the rule the application enforces. The
  responsible adult is expected for the whole slot, and the minor's check-in records who is
  present (FR-113).
- **No date of birth is stored.** Under-18 is a flag set at invitation. When the member turns
  18, they or the guardian tell a faculty advisor, who converts the account by hand (FR-109).
  Nothing changes automatically, because the system has no date to change it on.

### 2.5 Permission matrix

`✓` may do; `E` may do within events they captain; `own` on their own record only; `·` may not.

| Action | Sysadmin | Officer | Captain | Member | Guardian (for linked minor) |
|---|---|---|---|---|---|
| Send invitation | ✓ | ✓ | · | · | · |
| Set member category (on the invitation) | ✓ | ✓ | · | · | · |
| Create or edit account manually | ✓ | · | · | · | · |
| Reset another user's password | ✓ | · | · | · | · |
| Change access level or club position | ✓ | · | · | · | · |
| Delete a user account (FR-118) | ✓ | · | · | · | · |
| Override license class or expiration | ✓ | · | · | · | · |
| Edit own name, callsign, emails, phone, preferences | ✓ | ✓ | ✓ | own | for minor |
| Sign an access agreement | ✓ | ✓ | ✓ | own | own only, never for the minor (FR-22) |
| Approve an access agreement | approver position only | | | | |
| Convert a minor's account to an adult's (FR-109) | approver position only | | | | |
| Designate responsible adults for a minor's slot | ✓ | ✓ | E | · | for minor |
| View a minor's responsible adults and guardians, with contact details | ✓ | ✓ | E | · | for minor |
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

- Sign-in by email address (either on file) and password. The account's sign-in address always
  works; another address on the account works once it is **confirmed**, either by the member
  following a link sent to that address or by an officer saying it is theirs (the same waiver as
  FR-120). Until then the address still receives club mail, so nothing waits on delivery
  (FR-103). A confirmed address belongs to one account, and is never taken away automatically,
  so correcting a sign-in address cannot lock anyone out; the temporary password (FR-7) remains
  the path that needs no mail at all. *(Clarified 2026-09-17 after the advisor asked why one of
  his addresses would not sign him in: "either on file" had never been built, and confirmation
  is the condition the assistant proposed and he accepted for the addresses that are not the
  account's identity.)*
- Password strength enforced; breached-password check **Should**.
- Self-service reset from a "Forgot username or password?" link on the sign-in page (FR-107),
  which needs working email. The sysadmin temporary-password path (FR-7) is the fallback and
  never depends on email.
- Second factor: **TOTP and passkeys are both built in v1 (Must)**, optional for every member by
  default, with a sysadmin setting that makes a second factor required for a given access level
  (sysadmin, officer, member); a passkey can also sign a member in with no password at all
  (NAF, 2026-09-13; TR-16). The application displays a shared password to eligible members
  (FR-33), which raises the value of any compromised account.
- Sessions expire; "remember this device" is allowed on members' own devices.
- University SSO as an *additional* sign-in method for `@scranton.edu` accounts: **not pursued
  in this version**, by NAF's decision of 2026-09-13; the option stays open for a future
  version. Nothing in the account model may assume its absence is permanent: a user record
  can later carry a University identity beside its password.

### 2.7 Invitations, entry links, and applications

Verbatim (2026-09-12; the first sentence was superseded on 2026-09-15 by entry links, FR-119, on the
advisor's direction quoted there):

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
3. The invitee completes the application, callsign first: the system looks the callsign up in
   FCC ULS at once and fills in the name and license fields (FR-4); an invitee with no callsign
   enters their name by hand. Then the remaining profile fields of FR-8, a password, and consent
   to the privacy notice (FR-101).
4. Completing the application admits the person: the account becomes a **Member** with the
   category the invitation carried, at once, with no review step (NAF, Q3). The inviter and the
   officers are told who joined, with the callsign and ULS name, and an officer or sysadmin can
   set the account to No access if something is wrong (FR-91).
5. On completion, the system sends a welcome message; the FCC lookup already ran during the
   application (FR-4).

**Entry links (added 2026-09-15).** Two use cases drove them, verbatim:

> Use case 1: A professor requires students to spend a certain number of hours working at W3USR
> as a course requirement. The professor sends everyone in the class a link that students can
> then see what the availability is for signing up. Students can sign up for (or request)
> Operator slots even though they are not licensed or have access. The mentor slots will have
> the people that carry the slot viability requirements. I don't want these students to be in
> "Observer" slots because I want them to actively participate, rather than sit in the
> background.

> Use case 2: We want to recruit members of the Frankford Radio Club (FRC), Murgas Amateur Radio
> Club, or local amateur community to help serve as mentors. I want to send an email blast out
> to these organization email lists. Someone who receives this email can easily see what is
> requested and offer to volunteer as a mentor. I want people to get enough information to know
> that they want to volunteer and sign up for a slot without me having to vet each application.
> At the same time, I want to maintain information security enough so that people that have
> not been vetted by club officials don't get all of the student names and other sensitive
> information.

Flow: an officer creates a link (FR-119) and sends it themselves. A person who opens it completes
the same join form as an invitee (step 3 above). Through a *class* link they are a Member at once
and must verify their address within seven days unless an officer waives it (FR-120). Through a
*community* link they become Provisional once the address is verified, officers are told, and an
officer admits or declines them (FR-121). Every account records the link it joined through.

---

## 3. Functional requirements

### 3.1 Accounts and profiles

- **FR-1 [Must]** Access is by an invitation from a sysadmin or officer (FR-2), or by an **entry
  link** an officer created (FR-119). There is no public registration form; the sign-in page
  offers no way to create an account. *(Rewritten 2026-09-15; the original read "Access is by
  invitation only.")*
- **FR-2 [Must]** Sysadmins and officers can issue an invitation to an email address, choosing
  the member category the invitee will hold and whether the invitee is a minor.
- **FR-3 [Must]** An invitation is a single-use link that expires; the issuer can resend it or
  revoke it, and always sees the link itself and a text to send by hand (FR-104). The system
  shows the issuer the state of each invitation (created, emailed or not, opened, completed,
  expired, revoked). **(added)**: the dictation does not mention expiry; an unexpiring invite in
  a mailbox is a standing door.
- **FR-4 [Must]** The application opens by asking for a callsign. On entry, the system looks it
  up in FCC ULS immediately (FR-14) and fills in the licensee's first, middle, and last name,
  license class, expiration, and status; the applicant confirms it is them and continues. The
  ULS name is shown as read-only. An applicant with no callsign chooses "I do not have a
  callsign" and enters their name by hand. If the lookup fails or the callsign is not yet in
  the ULS data (a fresh grant), the applicant may enter their name by hand and the license
  record is held as *unverified* until the daily sync finds it. The application then collects
  the remaining FR-8 fields, a password, and consent to the privacy notice. The inviter is told
  who completed the invitation, with the callsign and ULS name beside the invitation's email
  address (FR-5), which is where a callsign entered by the wrong person is noticed.

  > I think the registration path should be for the person to enter their call sign first, and
  > have it do an immediate automated lookup and fill in the name and license info. A person
  > cannot edit their ULS name, but they can edit their preferred name. There needs to be an
  > option for someone with no callsign to just enter a name. — NAF, 2026-09-13

- **FR-5 [Must]** Completing an invitation's application admits the applicant as a Member with the
  category set on the invitation; there is no review queue (for entry links see FR-120). The inviter and the officers receive a notice
  naming who joined, with callsign and ULS name, so a wrong person or a mistyped callsign is
  caught by a human after the fact and answered with No access (FR-91) if need be.

  > completing the form admits — NAF, 2026-09-13, Q3
- **FR-6 [Must]** Sysadmins can create and edit any account manually, including every privilege
  field.
- **FR-7 [Must]** Sysadmins can reset any account's password to a generated temporary,
  one-time password. It works for exactly one sign-in, which must set a new password before
  anything else; it expires unused after a configurable period (default 72 hours); and it is
  shown once to the sysadmin, who passes it to the member by whatever means they choose. The
  system never emails it. This is the password-reset path that does not depend on email
  (FR-103).
- **FR-119 [Must] Entry links.** An officer or sysadmin creates a multi-use link with: a **label**
  (a course or an organisation), recorded on every account that joins through it; a **kind**,
  *class* or *community*; for a class link a **required email domain**, chosen from the club's
  trusted domains (configuration, `trusted_email_domains`; W3USR: `scranton.edu`); an **expiry
  date**, required; an optional **cap** on the number of accounts; an optional **landing page**
  (an event, the events list, or the mentor-needs page, FR-123). The creator and any officer can
  pause, resume, revoke, extend, and see who joined through it. A link that is paused, revoked,
  past its expiry, or at its cap admits nobody and says so plainly.

  > a time-limited invitation link for community clubs similar to classes could be useful. This
  > would allow me to track which link a person joined on (e.g., are they FRC or Murgas club?)
  > and prevent links leaking onto the internet becoming permanent entry ways. — NAF, 2026-09-15

- **FR-120 [Must] Joining through an entry link.** The person completes the join form (callsign
  first, FR-4; consent, FR-101). Through a **class** link: the address must be at the link's
  domain; the account is a **Member** at once, category Student unless the person chooses Faculty
  or Staff (an officer can correct it); a verification email goes out, and if its link is not
  followed within seven days the account is set to No access until it is, or until an officer or
  sysadmin **marks the address verified**, for one account or for every account from one link.
  Through a **community** link: the account is created only when the verification link is
  followed, as **Provisional** (FR-121). Responses to the form never reveal whether an address is
  already known (FR-107).

  > allow for an officer/sysadmin override if necessary. I don't want people to get frustrated if
  > our email system goes pear-shaped. — NAF, 2026-09-15

- **FR-121 [Must] Provisional review.** A Provisional account (§2.1) is shown to every officer on
  Home until one acts, and officers are emailed when it appears. An officer admits the person as
  a **Member** or declines with a reason; declined accounts are set to No access and the person
  is told. Provisional members cannot open the agreements pages or sign an agreement; station and
  IT access remain behind the agreements once they are Members. On a roster a Provisional member
  sees their own name and, for each slot, the count of people by license class.

  > provisional members should only see their names, and counts of people by license class (i.e.
  > 2 U, 1 T, 3 G, 1 E). True provisional members will quickly be promoted to regular member and
  > be able to see more information. — NAF, 2026-09-15

  > Only members or higher can view and sign access agreements. — NAF, 2026-09-15

- **FR-123 [Must] Mentor-needs page.** A page reachable without signing in, from a community
  entry link: the upcoming events that want mentors, when (event zone and UTC), open Mentor
  seats per slot, what a mentor does, and what is required (a license at the event's preferred
  class; the club's agreements once admitted). It is labelled with the club's name, shows no
  person's name or contact detail and no room number until the viewer is a Member, and has one
  action: the join form of the link that led there.

- **FR-8 [Must]** The profile holds the following fields. Editability follows section 2.5.

  | Field | Required | Editable by member | Notes |
  |---|---|---|---|
  | First name | yes | only if no callsign | With a callsign, this is the ULS licensee name, filled by lookup (FR-4), refreshed by sync and on callsign change (FR-102), and read-only to the member; a sysadmin can override it with a reason (FR-15). Without a callsign, entered and edited by the member |
  | Middle name | no | only if no callsign | As first name |
  | Last name | yes | only if no callsign | As first name |
  | Preferred name | no | yes | Always the member's to set. Used in the short name (FR-67) and in salutations where set; people are addressed by the name they use |
  | Callsign | no | yes | Uppercase, validated as a plausible callsign. A change triggers FR-102 |
  | License class | no | no | From FCC lookup (FR-14) or sysadmin override |
  | License expiration | no | no | From FCC lookup or sysadmin override |
  | License status | no | no | **(added)** Active / expired / cancelled / not found, from FCC lookup; the health check needs status, not only class |
  | Scranton email | one of the two | yes | Validated as `@scranton.edu` |
  | Personal email | one of the two | yes | |
  | Email delivery preference | yes | yes | Scranton, personal, or both |
  | Notification preferences | yes | yes | Per category and channel (FR-71); browser notification subscriptions per device (FR-112) |
  | Cell phone | no for adults; no for minors | yes | Guardian phone is required for a minor instead |
  | Under 18 | yes | no | A flag set at invitation; drives the guardian rules. No date of birth is stored (NAF, 2026-09-13); conversion at 18 is by hand (FR-109) |
  | Member category | yes | no | Faculty / Staff / Student / Community Member; set at invitation, changed by officer or sysadmin |
  | Anticipated graduation | for Students | yes | Semester (Spring, Summer, or Fall; Spring is the default) and four-digit year. Students only; blank for other categories. NAF, 2026-09-13 |
  | Student level | for Students | yes | Undergraduate or graduate. Students only. NAF, 2026-09-13 |
  | Club position | no | no | From the configured list; set by sysadmin |
  | Access level | yes | no | Section 2.1; set by sysadmin |
  | Guardian(s) | required if under 18; more than one allowed | guardian edits own | Section 2.4 |
  | Responsible adults previously named | for minors | guardian | Section 2.4; picked from when signing up for a slot (FR-64) |

- **FR-9 [Must]** Members can edit their own non-privilege fields. Privilege fields (category,
  license data, access approvals, club position, access level) are read-only to the member and
  show where the value came from and when.
- **FR-10 [Must]** A guardian account can do everything on behalf of a linked minor that the
  minor could do if self-managed, except sign access agreements (FR-22). The minor's own
  account signs in read-only (section 2.4).

  > Yes, read only — NAF, 2026-09-13, Q6
- **FR-11 [Should]** A member can ask for their account to be closed. Closure sets No access and
  starts the retention clock (section 4.3); it does not delete signed agreements before their
  retention period ends.
- **FR-12 [Should] (portability)** Member categories and club positions are configurable lists.
  W3USR ships with the values in FR-8.
- **FR-13 [Must]** A member directory, visible to members, showing each member's short name
  (FR-67), callsign, category, and club position, searchable by name and callsign. No contact
  details; officers and sysadmins reach those through the member roster (FR-87).

  > Yes, I want this. — NAF, 2026-09-13, Q10

### 3.2 Licenses and credentials

Verbatim:

> License Class and Expiration Date (Do by FCC lookup at time of account creation; cronjob to
> batch-check this information on a daily basis. Allow for sysadmin overrides.)

- **FR-14 [Must]** When an account with a callsign is admitted, when a callsign is entered or
  changed (FR-102), and daily thereafter for every account with a callsign, the system
  retrieves license class, expiration date, status, and the licensee name from FCC ULS data
  and records the result with its source and retrieval time. The mechanism is decided
  (TR-13, 2026-09-13): the FCC's own bulk ULS files imported daily into a local table, so every
  lookup is local and instant; the requirement is that the data are FCC data and are no more
  than a day stale.
- **FR-15 [Must]** A sysadmin can override class, expiration, status, or the ULS name (where
  ULS is out of date or wrong), with a required reason.
  An override is shown as such wherever the value appears and is never silently replaced by the
  next sync. A sysadmin can lift the override.
- **FR-16 [Should]** When a callsign is added to an account that already has a name (a member
  without a callsign gets licensed, or a callsign change under FR-102), and the ULS name differs
  from the name on file beyond a middle name or initial, the system shows the member both names
  and asks them to confirm that the ULS name is theirs; on confirmation it replaces the name on
  file. If the member says it is not theirs, the callsign is rejected as mistyped or someone
  else's. No sysadmin is involved; the replacement is written to the audit log (FR-92) like any
  other name change, and that is the whole record.

  > FR-16: The user can also approve the ULS name to replace their input name.
  > — NAF, 2026-09-13

  > We want to keep the sysadmin out of this if we can. — NAF, 2026-09-13

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
  license fields and the ULS name update from the result, a name mismatch goes through the
  member's confirmation per FR-16 before the name is replaced, and a
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
requires a University Non-Employee Affiliate Application, which carries a background check
administered by University Human Resources; the club does not run or see the check. (The
2024-08-19 agreement text names a specific check; the advisor does not vouch for that detail,
and the next revision of the agreement should say only what HR actually does.)

- **FR-21 [Must]** The system stores agreement **templates**, each with a type (station access
  or IT access for W3USR), an audience rule (which member categories see it: the Student
  station agreement to Students; the Community Member agreement to Community Members; and,
  for Faculty and Staff, the Community Member agreement's text with its affiliate-application
  clause removed, kept as its own template so the signed record shows exactly what was signed;
  NAF, Q4), the full text, a version identifier, and an effective date. Publishing a
  new version never alters or deletes an earlier one, because signed records point at the
  version signed.
- **FR-22 [Must]** A member signs their access agreements in **one workflow**: the system
  presents every agreement applicable to them (the station access agreement for their category
  and the IT access agreement) in one sitting, and each is read and signed in turn. Each
  agreement remains its own record with its own approval and expiry (FR-25, FR-26), so the
  workflow is a single visit, and the records stay per document. A signature consists of: the
  signer's typed full name, an explicit affirmation checkbox, the timestamp, the signer's account
  identity, the IP address, and the agreement version's content hash. **Minors do not sign
  access agreements, and guardians do not sign them on a minor's behalf.** A minor therefore
  never holds station access or IT access, and is never the person satisfying those parts of a
  slot's viability rule (FR-61) or eligible to view the computer password (FR-33). A guardian
  who holds their own member account signs the agreements for themselves, as any member does.

  > Yes, everyone should sign station access and IT agreements as a single workflow. Minors
  > should not sign these, and their guardians should not sign them for minors. Instead,
  > guardians who have their own accounts may sign them for themselves. — NAF, 2026-09-13
- **FR-23 [Must]** The system renders each signed agreement to a PDF that reproduces the text as
  signed plus the signature block, stores it immutably, and lets the signer and approvers
  download it.
- **FR-24 [Must] (added; confirmed by NAF 2026-09-13)** The digital agreement does **not**
  collect or store the University R number. The paper forms do, and the swipe-card request to
  University facilities needs it, but this repository's rules forbid storing rosters tied to
  student IDs. The advisor obtains the R number from University systems at the moment of
  requesting access, outside this application.
- **FR-25 [Must]** A signed agreement enters an approval queue visible to approver positions
  (section 2.3). The approver can approve, setting an expiration date, or decline with a reason
  that is sent to the signer. The default expiration is **the next 1 September**, except that
  an approval dated in August is set to the 1 September of the following year, so no one signs
  in August and expires within weeks. Examples: approved 15 October 2026 or 1 March 2027,
  expires 1 September 2027; approved 20 August 2027, expires 1 September 2028. Configurable per
  agreement type. The shared date means the whole club renews together at the start of each
  academic year. Approval is itself recorded with the approver's identity and timestamp.

  > Let's change it from a default of 1 year to a default of expires Sept 1 of the following
  > year. This will help use to renew everyone at the same time. — NAF, 2026-09-13

  > Anything signed in August should be set for Sept 1 of the next year. I don't want someone
  > signing something in August and only having it be good for less than 30 days.
  > — NAF, 2026-09-13
- **FR-26 [Must]** A signed agreement has the states *signed* (awaiting review), *approved*,
  *declined*, *expired*, and *revoked*. **The viability check (FR-61) uses *approved*.** An
  approval that has reached its expiry date is *expired*, so "approved" already means current;
  the same test serves the reports (FR-31, FR-84) and the computer-password view (FR-33). The system does not track
  whether the University has physically enabled a swipe card; that step is the advisor's, and
  the approval is taken as the record that it was requested.

  > FR-26: Let's not keep track of active, just signed, approved, expired, revoked, declined.
  > It's going to be too much trouble to correctly keep track of active here.
  > — NAF, 2026-09-13

  > The viability check of FR-26 should therefore use "approved" — NAF, 2026-09-13
- **FR-27 [Must]** The Community Member agreement cannot be approved unless the member has a
  `@scranton.edu` email address on file. The University issues that address when the
  Non-Employee Affiliate Application, including HR's background check, has gone through, so
  its existence is the evidence that HR is done, and the system needs no separate checklist
  and records nothing about the check itself. If no `@scranton.edu` address is on file when
  the approver reaches the agreement, the approval form lets the approver enter one there, and
  it is saved to the member's profile as their Scranton email (FR-8) as part of the approval.
  The address is not verified by sending mail to it; the approver is vouching for it.

  > We will know the HR's confirmation is active once the community member gets a
  > scranton.edu email address. So, require a scranton.edu address for community member
  > agreement approval. If one is not already on file, let the approver add one at the time of
  > approval. — NAF, 2026-09-13

  > This requires a background check that HR takes care of. I do not know exactly what
  > background check is run, so you do not need to specify PA State Criminal Background Check.
  > — NAF, 2026-09-13
- **FR-28 [Must]** Approvals expire on their date. Thirty days before, the member (and guardian)
  receives one notice covering every agreement of theirs that is about to expire, encouraging
  them to sign in and re-sign all of their agreements in one visit, with a link to the page
  where they do it; a second notice goes on the expiry date itself. Because the default expiry
  puts the whole club on the same date, the approvers receive a single summary listing everyone
  due, at 30 days and again at expiry, and the re-sign queue is built to be worked through in
  bulk. An expired credential no longer satisfies slot viability.

  > The system should automatically notify people 30 days before their IT and Station Access
  > agreements expire. They should be encouraged to log into the system and re-sign all of the
  > agreements. — NAF, 2026-09-13
- **FR-29 [Should]** An approver can revoke an approval at any time with a reason. The
  system notifies the member and flags every future slot whose viability depended on it.
- **FR-30 [Should]** When a new agreement version is published, the publisher chooses whether
  existing approvals remain valid until their own expiry or all signers must re-sign by a date.
- **FR-31 [Must]** Reports (section 3.9) list who currently holds station access and IT
  access (approved and unexpired), with expiry dates, and who is approaching expiry.
- **FR-32 [Must]** A sysadmin can set the shared W3USR computer account password and its
  effective date. The system stores it encrypted at rest and shows it in the interface only.
  It is **never** included in an email or other message: the agreement the viewer signed says
  "I will not share the password with others or write the password down on paper," and mail is
  both.
- **FR-33 [Must]** A member whose IT-access agreement is approved and unexpired can view the current
  password after re-entering their own password. Each view is written to the audit log (FR-92)
  with the viewer and time.
- **FR-34 [Should]** On rotation, the system notifies every member with current IT access that
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
  club's, `America/New_York`), one or more locations and positions (FR-51), one or more
  captains, an optional link to rules, a **preferred license class** (the class the captain
  wants the control operator to hold; below it a slot is viable with a warning, FR-61; the Mentor
  role's default requirement, FR-122), and the contest fields of FR-37 where relevant. *(Until
  2026-09-15 this was a minimum class that made lower-class slots not viable.)*
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
  pages are copyrighted. The advisor is writing to WA7BNM (Q11); meanwhile a lightweight
  prototype of the retrieval and parsing may be built ahead of the stack decision, tested
  against the club's 2026–27 events (CQ WW RTTY, CQ WW SSB, ARRL DX SSB, November
  Sweepstakes, CQ WPX RTTY and SSB, ARRL Rookie Roundup), so that FR-37's field list and
  FR-38's period parsing are grounded in real pages before anything is built on them.

  > I will write to him, but you can still prototype a lightweight mechanism of retrieving
  > contest details now. — NAF, 2026-09-13, Q11
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
  **Locking is optional.** A captain locks an event when they want the roster frozen (the
  night before a contest, say, so that a late cancellation goes through them); an event that
  is never locked goes from *published* to *completed* directly. *Completed* is set by a
  captain or officer, or automatically once the last slot has ended, whichever comes first.
  Publishing is an explicit action by an officer or captain, recorded with who and when, and
  offers an announcement to members at that moment (the FR-80 opening announcements cover each
  role's opening, and this one covers the event becoming visible). Visibility and sign-up are
  separate switches: a published event may have every role still closed, so members can see
  what is coming before anything opens. A published event can return to *draft* only while
  no one has signed up; once anyone has, the only way off the schedule is *cancelled*, so no
  member's commitment disappears without notice.
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
- **FR-47 [Must]** An event can carry **non-operating slots** alongside its operating ones:
  setup, breakdown, training, equipment pre-check, post-event analysis, and whatever else the
  club needs, from a configurable list of kinds **(portability)**. They can sit before the
  first operating period, after the last, or in a gap between periods (a training session in
  the overnight break of a two-period contest, for example). The generator offers setup before
  and breakdown after by default, of chosen length and count; a captain adds the others by
  hand. Non-operating slots do not count toward FR-39 operating-time limits, and each kind has
  its own viability rule (FR-61): the default requires one person with station access and
  nothing else, a kind that meets away from the station can require nothing at all, and the
  rule is editable per kind.

  > For FR-47, setup and breakdown are only two types of pre- or post- event slots. There
  > might also be training, equipment pre-checks, post-event analysis, etc.
  > — NAF, 2026-09-13
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
- **FR-51 [Must]** An event has one or more **locations**, and each location has one or more
  **positions**; every slot belongs to a position. A location is a place (the club station, a
  field site, a scout camp for JOTA, a member's home station in a distributed multi-operator
  entry) with its own name, directions, and know-before-you-go text (FR-77). A position is an
  operating station at that location (*Run*, *Multiplier*, *Satellite*, *VHF*). The default
  event has one location, the club station, with one position, and a captain adds more.
  Because the credentials a slot needs depend on where it is, **each location carries its own
  viability rule** (FR-61): the club station requires station access and IT access; a field
  site or a member's home requires neither, and may require something of its own (a key
  holder, a site lead) expressed as a credential type (FR-18). The roster (FR-65) groups by
  location and shows positions as parallel columns; reminders (FR-72) name the slot's location.
  A location that is a private residence shows its address only to people signed up there and
  to captains, officers, and sysadmins, per section 4.2.

  > Q12: Yes, we should support multiple positions and even locations. — NAF, 2026-09-13
- **FR-52 [Should]** A captain can mark a slot as *closed* (not bookable, shown greyed) and as
  *cancelled* (removed from the schedule with notice to anyone signed up).

### 3.6 Eligibility and sign-ups

Verbatim:

> We should be able to designate when categories of people can sign up for certain slots. For
> instance, we might initially open Operator slots to students, while mentor slots might be
> open to all members with a certain minimum license class.

- **FR-53 [Must]** Each role in each slot has an **eligibility rule**, defaulted at event level
  and overridable per slot, composed of: allowed member categories; a license class requirement
  (or none); required credentials (from FR-18, any combination); whether minors may sign up; and
  an **opening schedule** (FR-54). A member sees only the roles they are eligible for, with the
  reason shown for roles they are not.
- **FR-122 [Must] Role defaults.** Club configuration carries a default eligibility per role, used
  wherever an event has set none: for W3USR, **Mentor** requires a valid amateur license of any
  class (the event's preferred class is advisory and produces the FR-61 warning, so that a
  Technician may still mentor); **Operator** and **Observer** require nothing, so an unlicensed student may take
  Operator and operate under the mentor as control operator (FR-63, §97.115(b)). Station and IT
  access are viability requirements on the slot (FR-61), carried by whoever in it holds them,
  never a condition of any role.

  > only ham radio license should be required for mentor. Operator, mentor, or observer could carry
  > station and IT access. — NAF, 2026-09-15
- **FR-54 [Must]** The opening schedule belongs to a role, so each role in an event opens on
  its own terms: for example, mentor and observer roles open to every member as soon as the
  event is published, while operator roles open to Students first and to everyone on a later
  date the captain sets (or never, if the captain prefers to hand out the remaining operator
  slots by hand). The schedule is a list of (date-time, audience) pairs per role. The system
  sends the announcement of each opening (FR-80) automatically if the captain enables it.
- **FR-55 [Must]** An eligible member signs up for a slot in a role in one action, and can
  select a run of consecutive slots at once. A guardian does the same for a minor.
- **FR-111 [Must]** A member holding a slot can change their role in it (operator to mentor,
  mentor to observer, and back) at any time before the cancellation cutoff (FR-56), provided
  they are eligible for the new role (FR-53) and it has capacity (FR-49); inside the cutoff,
  the change goes through with the captains notified, as a late cancellation does. The change
  is one action, with no gap in which the member holds no place; the roster and the slot's
  viability and control-operator designation (FR-61, FR-63) update at once. **Before the
  change is made**, the system evaluates what it would do to the slot and, if the slot would
  become *not viable* or *at risk* (FR-62), tells the member so in plain terms ("you are the
  only licensed operator in this slot; if you switch to observer it cannot run") and asks them
  to confirm or stay. The same warning applies to cancelling a sign-up (FR-56). If they go
  ahead, a captain is told. Captains can change a member's role on their behalf (FR-58). A
  guardian does the same for a minor.

  > People should be able to change from operator to mentor to observer, if they are eligible
  > to do so. — NAF, 2026-09-13

  > If this happens, you could warn the user before they make that switch. Then they might
  > decide to stay as an operator. — NAF, 2026-09-13

- **FR-113 [Must]** **Check-in.** A member checks in when they arrive for a slot, from "my
  schedule" (FR-59) on their phone or any signed-in browser, from 30 minutes before the slot
  starts (configurable per event) until it ends. **Checking in must be very easy**: when a
  member is inside the window for a slot they hold, the first thing they see on signing in, and
  the top of "my schedule", is a single large **Check in** button for that slot; one tap, no
  further page, no confirmation dialog. The same button appears on the browser notification
  (FR-114) where the platform allows an action there. A check-in records the time. The roster shows
  a sign-up's state as *signed up*, *confirmed* (FR-72), or *checked in*, so during the event
  the roster is also the attendance board. Captains can check a member in on their behalf; for
  a minor, a guardian or a captain checks them in, and the check-in records which designated
  responsible adult (FR-64) is present. If a slot has started and a confirmed person has not
  checked in within 15 minutes (configurable), the captains get one notice naming them. Check-in
  times feed the participation report (FR-86), which then distinguishes scheduled from actual
  attendance. There is no check-out; the slot's end is taken as the departure unless the member
  cancels the rest of a run of slots.

  > Members should check in when they arrive at their time slot. They can check-in up to
  > 30 minutes early. — NAF, 2026-09-13

  > The checkin mechanism must be very easy to do. — NAF, 2026-09-13
- **FR-124 [Should] Hours for a course.** Check-in time is recorded (FR-113). A member who
  checked in is credited with the slot's full length by default; a captain can mark a **no-show**,
  which removes the credit. Officers can view and export, per entry-link label (the course, FR-119),
  each member's slots, check-in times, and credited hours, for the instructor who set the
  requirement.

  > let's just record event check-in time and report that to the professor. By default, student
  > will be given full credit for the slot. — NAF, 2026-09-15

- **FR-114 [Could]** A browser notification (FR-112) 30 minutes before each slot the member
  holds, opening the check-in.
- **FR-110 [Must]** A sign-up carries an optional free-text **note to the captains** ("I will
  be running 10 minutes late", "I need to leave 15 minutes early", "first time on CW"),
  entered at sign-up and editable by the member afterwards. Notes are visible to the event's
  captains, officers, and sysadmins, on the roster beside the sign-up and in the slot's
  detail; other members do not see them. A slot with a note shows a marker on the roster so
  captains notice without opening each one, and a note added or changed inside the 48 hours
  before the slot is included in the captains' at-risk digest (FR-73) so a late arrival is
  known before it happens.

  > People should be able to add notes visible to team captains when they sign up for slots,
  > so they can say things like "I will be running 10 minutes late" or "I need to leave 15
  > minutes early", etc. — NAF, 2026-09-13
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

- **FR-61 [Must]** A slot is **viable** when, among the people signed up in it, the event's
  viability rule is satisfied. W3USR's default rule: at least one person in an on-air role holds a
  valid amateur license of **any class**; at least one person holds an *approved* station access
  agreement; at least one person holds an *approved* IT access agreement (FR-26). One person may
  satisfy all three, or three people one each. When no licensee in the slot meets the event's
  **preferred** class (FR-36) the slot is viable **with a warning** that names the class present
  (*Covered · below preferred class (T)*). *(Amended 2026-09-15; the class had been a minimum.)*

  > I think a slot that has any license class is viable. But, those below the preferred class
  > would carry a warning. — NAF, 2026-09-15 The rule is expressed over credential types (FR-18), is set per location (FR-51)
  with the club station's rule as the default, and is editable per event
  **(portability)**.
- **FR-62 [Must]** Each slot displays one of: *Open* (no one signed up; the word invites), *Needs
  …* (people signed up but the rule fails, naming the missing credential as what the slot needs),
  *Covered*, *Covered · below preferred class (X)* (FR-61), and *Covered* with a note when it
  depends on one person (if they cancel, it fails). *(Reworded 2026-09-13 from empty / not viable
  / viable / at risk so that a newcomer reads an invitation, not a verdict.)* A slot also shows
  *over limit* when it would push the event past an FR-39 operating-time limit. Status is
  conveyed by icon and text as well as colour, in a colour-blind-safe palette.
- **FR-63 [Must] (added; FCC Part 97)** For each viable slot, the roster names the **control
  operator**: the licensed person whose license class governs what the station may do during
  that slot. Part 97 requires a control operator for every transmission and limits the station
  to the control operator's privileges (§97.7, §97.105(b)); unlicensed participants may speak
  under the control operator's supervision as third parties (§97.115(b)(1)). (Citations
  verified against the current CFR text on 2026-09-13.) The default is the
  highest-class licensee signed up in an on-air role; a captain can change it; the person
  named is told in their reminder. This makes the dictation's "minimum license class" concrete:
  it is the class the control operator needs for the bands and modes the event uses.
- **FR-64 [Must]** When a guardian signs a minor up for a slot, they designate one or more
  **responsible adults** who will accompany the minor for that slot: name, email, and phone,
  picked from adults the guardian has named before or entered fresh; a member can be picked by
  name. A responsible adult occupies no place in the slot and is not counted toward its
  capacity or its viability rule. A minor's sign-up with no responsible adult designated makes
  the slot *not viable*, and the status text names the minor. Captains can edit the
  designation on the guardian's behalf.

  > I don't think the responsible adult accompanying the minor needs to take up a "slot".
  > Instead, […] the guardian should be able to designate responsible adult(s) that will be
  > accompanying the minor for each slot. — NAF, 2026-09-13

- **FR-109 [Must]** Converting a minor's account to an adult's is a manual action by a faculty
  advisor (an approver position, section 2.3), taken when the member or a guardian reports that
  the member has turned 18. It clears the under-18 flag, ends the guardian links (kept in
  history), makes the account self-managed, and issues a one-time temporary password (FR-7) or
  a reset link so the member sets their own credentials. Guardians are notified. Audited.

  > We are not storing any DOBs in this system. So, when the minor turns 18, they need to talk
  > to a faculty advisor who can then manually convert the minor account into an adult
  > account. — NAF, 2026-09-13
- **FR-65 [Must]** The **roster page** for an event shows every slot in time order, grouped by
  day and, where an event has more than one location, by location, with position columns
  (FR-51), each person's name (in the form FR-67
  allows the viewer to see), role, and compact credential badges (license class, station
  access, IT access, control operator), the slot's status, and a filter for "problems only".
  Times show in UTC and the event's display zone. The page works at phone width and has a
  print layout.
- **FR-66 [Must]** An **event health summary** at the top of the roster and on the event list:
  slots total, viable, at risk, not viable, empty; hours scheduled against each FR-39 limit;
  and the number of unconfirmed sign-ups in the next 48 hours.
- **FR-67 [Must]** On rosters, members see each person's **short name**: first name (the
  preferred name where one is set) and callsign, or first name and last initial for a person
  with no callsign; then the **license class in parentheses** (N, T, G, A, E; U for none):
  `Nathaniel W2NAF (E)`, `Nathaniel F. (U)`; and their role. Captains and officers see the full
  name with the same suffix. A Provisional member (FR-121) sees no names but their own, and a
  count by class per slot.

  > just do Nathaniel W2NAF (E) — NAF, 2026-09-15; earlier the same day: "This will let us quickly
  > assess what the license class of the slot is. I think it could also provide incentive for
  > people to upgrade to see their designation increase."
 Full names, phone numbers, and email addresses are visible
  to captains of that event, officers, and sysadmins only. The short name is the form used
  wherever a member sees another member: the roster, the control operator's name (FR-63),
  the list of slot-mates in a reminder (FR-72), and any directory (FR-13). For a
  minor on the roster, those same people can open the minor's name to see the responsible
  adult(s) designated for that slot with their email and phone, and the minor's guardian(s)
  with name and contact details. Members signed up in the same slot as the minor see the
  responsible adults' names and phone numbers too, so the people on site know who is
  accompanying the minor; guardian details stay with captains, officers, and sysadmins
  (NAF, Q17).

  > On Rosters, only event captains, officers, and above can see full names and contact
  > details. Members can only see First Name and Call Sign (Or last initial if no call sign).
  > — NAF, 2026-09-13

  > On the roster, we should be able to click the minors name and see who is accompanying,
  > along with their email and telephone number. That display should also show the guardians
  > name and contact info. — NAF, 2026-09-13

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
  | Application completed | Welcome to the member; notice to inviter and officers | The member is simply in; officers see new members on the member roster (FR-87) |
  | Forgotten password | Reset link (FR-107) | Sysadmin issues a temporary password in the interface (FR-7) |
  | Slot reminder and confirmation | Reminder with confirm link (FR-72) | "My schedule" shows the slot, its details, and confirm / cannot-make-it buttons (FR-59) |
  | At-risk warning | Warning (FR-73) | Roster status and health summary (FR-62, FR-66); in-application notifications (FR-108) |
  | Announcement | Bulk message (FR-75) | Visible in each recipient's "my messages" (FR-82); officer can export the recipients and body to send from their own mail client (FR-106) |
  | Agreement submitted, approved, declined, expiring | Notices (FR-76) | Approver queue and the member's agreements page show the state; expiry countdown on the profile |
  | Computer password rotated | Notice (FR-34) | Banner for eligible members on sign-in |
  | License expiring | Notice (FR-17) | Banner on the member's profile |
  | Cancellation of a slot, event, or sign-up | Notice (FR-74) | "My schedule" and the roster reflect it immediately; notification (FR-108) |
  | Check-in (FR-113) | none; it is an in-application action | "My schedule", or a captain on the member's behalf |

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
- **FR-71 [Must]** **Notification preferences** live on the member's profile page: one row per
  message category, with a switch for email and, where enabled (FR-112), for browser
  notifications. The in-application copy (FR-82) is always kept. Categories a member controls:
  automated slot reminders (FR-72); at-risk warnings for slots they hold (FR-73); role-opening
  announcements (FR-80); general announcements (FR-75); the weekly digest (FR-79); license
  expiry notices (FR-17). Categories that **go out no matter what**, because they change
  something the member is relying on or protect their account: cancellation of a slot, event,
  or sign-up they hold (FR-74); a sign-up moved, removed, or re-timed by someone else (FR-58);
  account security messages (password reset, temporary password, sign-in lockout); and
  agreement decisions and expiry (FR-25, FR-28), since losing access silently is worse than an
  unwanted message. For a minor, the guardian sets the preferences and the mandatory messages
  always reach every guardian (FR-70). A member who turns reminders off is shown on the roster
  as *reminders off*, distinct from *unconfirmed*, so captains read the confirmation column
  correctly; they can still confirm from "my schedule" (FR-59).

  > Members should be able to control on their profile page what notifications they get,
  > particularly automated reminders. Some emails, such as cancellations, should go out no
  > matter what. — NAF, 2026-09-13
- **FR-72 [Must]** **Reminder**: 24 hours before each slot (configurable per event), each
  person signed up receives a message with the slot time in UTC and local, the location and
  position, their role, the
  control operator's name, the other people in the slot (short names, FR-67), the
  know-before-you-go text, the
  captains' names and contact details with the faculty advisor's as a second line after them
  (NAF, Q15), and a one-click **confirm** link that works without
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
  completed (to inviter and officers), welcome, password reset, agreement submitted (to approvers), agreement
  approved, declined, expiring, expired, revoked (to signer), computer password
  rotated (FR-34), license expiring (FR-17).
- **FR-77 [Must]** Each event has a **know-before-you-go** text, edited by captains, included
  in every reminder: where the station is and how to get in, parking, what to bring, the
  exchange, the logging setup, the rules link. Where an event has more than one location, each
  location has its own section (how to get in differs by place) and the reminder includes the
  one for the recipient's slot. A duplicated event carries it forward, so it becomes a living
  document per contest. It is rich text (FR-115), and a new event's text starts from a
  template with the headings already in place (Getting in, Parking, What to bring, Exchange,
  Logging, Who to contact), so the structure is there before the first word is written.
- **FR-115 [Must]** **Rich text.** Every long text a person authors in the application is HTML,
  edited in a WYSIWYG editor: the know-before-you-go text and its per-location sections
  (FR-77), event descriptions (FR-36), location directions (FR-51), announcement bodies (FR-75),
  message templates (FR-78), agreement templates (FR-21), and the privacy notice (FR-101). The
  editor offers headings at three levels, paragraphs, bold and italic, bulleted and numbered
  lists, links, and simple tables, and it **encourages structure**: headings are prominent in
  the toolbar, the templates that seed new texts carry a heading outline, and the editor warns
  when heading levels are skipped. Because each text is rendered inside a page that already has
  its own title, the editor's first heading level renders as the page's next level down, so the
  rendered page keeps one H1 and an unbroken heading order (WCAG, section 5.3). Saved HTML is
  sanitised on the way in and on the way out to the allowed elements only: no scripts, frames,
  forms, or inline styles. When a rich text goes out by email it is sent as HTML with a
  generated plain-text alternative, so it reads in any client and passes spam filters that
  penalise HTML-only mail.

  > This and other text should be HTML rich text editable with a WYSIWYG editor. Good
  > structure using appropriate H1, H2, H3, headers, etc should be encouraged.
  > — NAF, 2026-09-13, on FR-77
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
- **FR-83 [Later]** SMS notifications. The notification layer is designed so that a channel is
  an implementation of one interface and a member preference; v1 implements email and browser
  notifications (FR-112). SMS waits on a budget for per-message cost.
- **FR-112 [Should]** **Browser notifications.** The application's browser-notification
  (web push) setting is **on by default**. A browser will only deliver notifications once the
  person has granted permission on that device, so at first sign-in on each device the site
  asks for it; granting activates the subscription, declining leaves the setting shown as
  *blocked by this browser* with how to allow it. One subscription per device, each revocable
  from the profile page, where the member can also turn the setting off entirely. When on,
  every message the member would receive by email under their preferences (FR-71) is also
  delivered as a browser notification, with the mandatory categories included, and tapping it
  opens the relevant page. Browser notifications never carry the computer password or
  contact details. Push works from the ordinary browser on desktop and Android; on iOS it works
  only when the application has been installed to the home screen as a PWA (FR-96), and the
  profile page says so. Delivery is best effort: a failed push is not retried and never blocks
  the email or the in-application copy.

  > Can we also have this site show notifications through the browser? So if an email
  > notification goes out, a browser notification is also enabled? This should be an optional
  > setting. — NAF, 2026-09-13

  > Make on by default — NAF, 2026-09-13

### 3.9 Reports and exports

- **FR-84 [Must]** **Access rosters**: who currently holds station access and IT
  access, with category, approval date, approver, expiry, and days remaining; sortable and
  filterable by expiring-within-N-days. Officers and sysadmins; downloadable as CSV.
- **FR-85 [Must]** **Event roster export**: the FR-65 roster as CSV and as a printable page.
- **FR-86 [Should]** **Participation report** per event and per period: hours scheduled, hours
  covered, hours viable, people scheduled and people who checked in (FR-113), first-time
  participants. This is what the
  club reports to the University and puts in a grant application, so it should be right.
- **FR-87 [Should]** **Member roster** for officers: name, callsign, category, position,
  student level and anticipated graduation (semester and year), license class and expiry,
  access credentials and their expiry, access level, last sign-in. A filter for Students
  whose anticipated graduation semester has passed gives officers the list, three times a
  year, of accounts to review for category change or No access (section 4.3).
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
- **FR-118 [Must]** A sysadmin can **delete a user account**, with a required reason and a
  confirmation that names what will happen, since the action is irreversible. Deletion is
  distinct from setting No access (FR-91), which keeps everything, and from member-requested
  closure (FR-11), which starts the retention clock. On deletion the system: cancels the
  person's future sign-ups and tells the captains of those events (FR-74); removes name,
  callsign, emails, phone, preferences, browser-notification subscriptions, guardian links, and
  responsible-adult designations; and replaces the person on past rosters and in participation
  history with an anonymous marker ("deleted member"), so counts and hours stay right while
  nothing identifies them. Signed agreements and their PDFs are kept for the retention period
  in section 4.3 and then purged automatically; the audit log (FR-92) keeps its entries, with
  the deleted account's identifier and the deletion itself recorded. A sysadmin cannot delete
  the last remaining sysadmin account. Deleting a minor's account also deletes the
  responsible-adult records attached to their sign-ups; a guardian account is deleted only
  after every linked minor has been converted (FR-109), re-linked to another guardian, or
  deleted.

  > There needs to be a mechanism for a sysadmin to delete a user account. — NAF, 2026-09-13
- **FR-92 [Must]** An **audit log**, append-only and readable by sysadmins, records: access
  level and club position changes, category changes, license overrides, agreement approvals,
  revocations and declines, computer password sets and every view, invitations
  issued, applications completed, accounts set to No access, announcements sent, sign-ups moved or removed by
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

Entities implied by section 3: club configuration; users (with guardian links and the
responsible adults a guardian has named); invitations; applications; credentials (license records with sync history and
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
  visible on the same terms as adult contact data and no wider. Responsible adults named for a
  slot (FR-64) may be people with no account; their name, email, and phone are held only for
  the slots they were named for and are visible on the same terms.
- No date of birth is stored for anyone. Under-18 is a flag (section 2.4).
- The IP address recorded with a signature (FR-22) exists to make the signature evidentially
  useful and is shown only on the rendered agreement.

### 4.3 Retention (proposed; the advisor's call, Q8)

| Data | Retain | Then |
|---|---|---|
| Profile of a member set to No access | 2 years from the change | Delete contact details and phone; keep name, callsign, and participation history as club record, or delete entirely on request |
| Guardian records | Until the minor's account is converted (FR-109) or closed | Delete contact details; keep the link in history |
| Responsible adults named for a slot | 1 year after the event | Delete |
| Signed agreements and approval history | 3 years after expiry (proposed default, configurable). The University's own period for the paper equivalents is not known to the advisor (Q8); if one is found, it replaces this | Delete |
| Audit log | Indefinitely | Nothing; it is small and it is the record |
| Messages sent | 1 year | Delete bodies; keep the fact and recipient count |
| Invitations never completed | 90 days after expiry | Delete |

### 4.4 Storage, backup, and recovery

Storage: SQLite in WAL mode, proposed 2026-09-13 (TR-2 in `TECHNICAL_REQUIREMENTS.md`), with
the schema sketched per domain in TR-26. Backup: a nightly copy of the datastore and the
signed-agreement PDFs to a location other than the server, encrypted, with a restore rehearsed
and dated before the first live event; the proposed mechanism is TR-22, an `age`-encrypted
nightly archive pulled off the box by a campus machine, at no cost.

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

**5.3 Accessibility.**

> The system must be accessible, especially for visually impaired people who use screen
> readers. — NAF, 2026-09-13

- **FR-116 [Must]** The application meets **WCAG 2.1 AA**, and is built and tested for screen
  reader users as a primary audience. Concretely:
  - Semantic HTML throughout: landmarks, one H1 per page and an unbroken heading order
    (FR-115), real buttons and links, every form field labelled, every image with meaningful
    alternative text or marked decorative.
  - The roster (FR-65) is a real table with row and column headers, so a screen reader announces
    the slot, position, and person for each cell; slot status (FR-62) has a text name read out
    alongside its icon and colour; a change of status while the page is open is announced
    through a live region.
  - Everything works by keyboard alone, with a visible focus indicator, and the most important
    action on each page (the check-in button when inside its window, FR-113; the confirm action
    on a reminder) is first in the tab order.
  - The WYSIWYG editor (FR-115) is itself operable by keyboard and screen reader, which
    constrains the choice of editor component in section 6.
  - Rendered agreement PDFs (FR-23) are tagged, so the document a member signed is readable to
    them afterwards.
  - Email and browser notifications (FR-69, FR-112) use plain, well-structured HTML with a
    plain-text alternative.
  - Colour is never the only carrier of information (FR-62), and text contrast meets AA.
- **FR-117 [Must]** Accessibility is verified: automated checks (an axe-core class
  of tool) run on every page in the build pipeline and a failure blocks the deploy; and before
  each release the core member flows (sign in, find an event, sign up, confirm, check in, read
  the roster, sign an agreement, view the computer password) are walked with a screen reader
  (NVDA or VoiceOver) by a person, and the result recorded. v1 is not released until that walk
  passes. If a club member who uses a screen reader is willing, their testing is sought and
  weighted above the automated results.

See also `.claude/rules/web-development.md`.

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
  to the same API the web front end shares its logic with. **Design consequence for section
  6**: the server exposes its functionality through a documented API from the start, and both
  the web interface and the API are thin clients of one service layer, so that a second client
  is an addition. (Amended 2026-09-13 with the advisor's agreement, TR-4 and TR-8; the first
  draft had made the web interface a client of the API, which would have forced a single-page
  front end.)

**5.5 Visitors.**

- **FR-98 [Must]** A visitor who is not signed in sees a sign-in page with the club's name and
  a link to the University club page, and nothing else. No event details, no names, no rosters
  (NAF, Q13).

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

**Decided 2026-09-13; formal adoption pending the advisor's read.** The technical requirements are a separate document,
[`TECHNICAL_REQUIREMENTS.md`](TECHNICAL_REQUIREMENTS.md) (TR-1 to TR-39), with the reasoning
for each choice; the advisor took its eight decisions on 2026-09-13 (its section 10). The headline proposals,
for the reader who needs only the shape:

- **Language and framework**: Python 3.12+ and Django 5.2 LTS (TR-1); decided 2026-09-13
- **Datastore**: SQLite in WAL mode, one file, nightly encrypted backup pulled off the box by
  a campus machine (TR-2, TR-22); decided 2026-09-13
- **Front end**: server-rendered Django templates with htmx, a small semantic CSS base, a
  hand-written service worker for the PWA, TinyMCE under GPL for rich text (TR-4 to TR-9);
  decided 2026-09-13
- **Outbound mail**: **decided 2026-09-13 by the faculty advisor**: a Postfix instance on the
  origin server, listening on the loopback interface only, DKIM-signing and delivering
  directly. The application sends over plain SMTP to `localhost` with no credential. Reason:
  the club has no budget for a transactional provider. Consequences: the SMTP endpoint is a
  configuration value, so a provider can be substituted by changing the server's relay with
  no application change; and in v1 bounces arrive in the club mailbox via the domain's inbound
  routing, so FR-81's in-application bounce record waits on an inbound hook.
- **Scheduler**: systemd timers running management commands, with a job-run table and
  healthchecks.io pings (TR-11, TR-33); decided 2026-09-13
- **FCC ULS access**: the FCC's bulk ULS files imported daily into a local table (TR-13);
  decided 2026-09-13
- **Build and deploy**: gunicorn as a systemd service behind the existing nginx; the private
  repository's `deploy.sh` runs migrations and restarts it (TR-3, TR-31); decided 2026-09-13
- **Testing**: pytest, Playwright with axe-core for accessibility, ruff, GitHub Actions on the
  public repository (TR-35 to TR-38); decided 2026-09-13

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

**All nineteen questions were answered by the advisor on 2026-09-13**, on an answer sheet kept in
the private repository (`prompts/20260913_open_questions_answers.md`), and the answers are applied
in the requirements above, quoted where they decide something. The list stays here as the record.
New questions are appended with the next number; a resolved question is never renumbered.

| # | Question | Decision (2026-09-13) | Applied at |
|---|---|---|---|
| 1 | v1 scope: adopt section 1.3's deferrals? | Agree | §1.3 |
| 2 | Accept the Must/Should/Could tags as drafted? | Agree | throughout |
| 3 | Is an application reviewed before access is granted? | "completing the form admits" | §2.7, FR-4, FR-5 |
| 4 | Which station agreement do Faculty and Staff sign? | The Community Member text with the affiliate clause removed | FR-21 |
| 5 | Store R numbers? | No; FR-24 stands | FR-24 |
| 6 | Can a minor sign in? | "Yes, read only" | §2.4, FR-10 |
| 7 | Date of birth or a flag? | Flag only; conversion at 18 is manual | §2.4, FR-109 |
| 8 | Retention table; University period for agreements? | Agree; University period unknown, 3 years after expiry proposed | §4.3 |
| 9 | University SSO? | Not at this time; option open | §2.6 |
| 10 | Member directory? | "Yes, I want this." | FR-13 (Must) |
| 11 | Contest calendar import: permission, feed, or both? | Advisor writes to WA7BNM; prototype retrieval now against the 2026–27 events | FR-40 |
| 12 | Multiple positions? | Yes, and locations | FR-51 |
| 13 | Anything for visitors? | Nothing | FR-98 |
| 14 | University policy on minors on campus? | Exists; satisfied by a guardian-approved responsible adult chaperoning at all times | §2.4, FR-64 |
| 15 | Name the advisor in reminders as a fallback? | Yes | FR-72 |
| 16 | Messages composed while email is off: drop or queue? | Accept as drafted (drop) | FR-105 |
| 17 | Who sees a minor's responsible adults? | Widen to slot-mates (names and phones); guardians stay with captains | FR-67 |
| 18 | Mail-confirm an approver-entered `@scranton.edu` address? | Accept as drafted (no) | FR-27 |
| 19 | `Reply-To` exposing captains' addresses? | Accept as drafted | FR-69 |

**Follow-ups that are not questions for the advisor:**

- Q8: find out whether the University sets a retention period for signed access agreements; until
  then the default is 3 years after expiry.
- Q11: the letter to WA7BNM (advisor); the retrieval prototype (assistant), in the application
  repository, ahead of the stack decision and without committing to one.
- ~~FR-63: the Part 97 section numbers cited (§97.7, §97.105, §97.115) are from memory and must be
  checked against eCFR before adoption.~~ **Verified 2026-09-13** against 47 CFR as published
  (Cornell LII mirror of eCFR; eCFR itself refused automated access): §97.7 "Control operator
  required"; §97.105(b) "A station may only be operated in the manner and to the extent
  permitted by the privileges authorized for the class of operator license held by the control
  operator"; §97.115(b)(1) third-party participation where "the control operator is present at
  the control point and is continuously monitoring and supervising". All three cited correctly.

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
| ~~Approved versus active station access (FR-26)~~ | Withdrawn 2026-09-13 at NAF's direction: tracking whether the University has enabled the card is more bookkeeping than it is worth. *Approved and unexpired* is the tested fact. |
| Control operator named per slot (FR-63) | Part 97 makes one licensed person responsible for every transmission and limits the station to that person's privileges. "At least one licensed person" is necessary but does not say who, and "minimum license class" is a statement about the control operator. |
| Responsible-adult designation in slot viability (FR-64) | The dictation states the chaperone rule as a policy; requiring a designation at sign-up is how the roster enforces it. First drafted as "a chaperone must hold a place in the slot"; NAF corrected this on 2026-09-13 to a designation that takes no place. |
| No R number (FR-24) | The paper forms collect it; the repository's rules forbid storing student IDs. The two conflicted and one had to yield. |
| Password never emailed (FR-32) | The agreement being signed forbids writing the password down or sharing it. Emailing it does both. |
| Invitation expiry and application review (FR-3, FR-5) | Standard hygiene for an invitation-only system; the dictation is silent. |
| Self-service password reset (section 2.6) | Removes routine work from the sysadmin; the sysadmin path the dictation asked for remains. |
| Confirming an address before it signs a member in (section 2.6, 2026-09-17) | The dictation asks for sign-in by either address on file. Anyone can type any address into a profile, so an address only carries the weight of a credential once the member has followed a link sent to it or an officer has vouched for it; an officer's waiver keeps it independent of mail delivery. |
| Audit log (FR-92) | The system approves access to a room and displays a shared password; who did what and when has to be recoverable. |
| Waitlist (FR-57), calendar feed (FR-59), digest (FR-79), messages page (FR-82) | Cheap once the core exists; each closes a way a slot goes uncovered or a message goes unread. |
| Positions and locations (FR-51) | Proposed as Should pending Q12; NAF confirmed both positions and locations on 2026-09-13, and FR-51 became Must with a per-location viability rule. |
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
- 2026-09-13, NAF, asked whether events can be drafted hidden from members and published
  later; FR-44 already provided the lifecycle. On his *"do it"*, FR-44 gained an explicit,
  recorded publish action with an optional announcement, and the rule that unpublishing is
  allowed only before the first sign-up.
- 2026-09-13, NAF, on minors (quoted at FR-64, FR-67, FR-109): responsible adults are
  designated per slot by the guardian and take no place in the slot; the roster exposes them
  and the guardians, with contact details, behind the minor's name; more than one guardian may
  be linked; no dates of birth are stored, so conversion at 18 is manual by a faculty advisor.
  Replaced the first draft's "authorized chaperones must sign up for the slot" and its
  automatic 18th-birthday handling. Resolves Q7.
- 2026-09-13, NAF (quoted at FR-67): members see first name and callsign (or last initial)
  on rosters; full names and contact details are for captains, officers, and sysadmins. The
  first draft had shown full names to all members. Applied to FR-65, FR-67, and by reference
  to FR-63, FR-72, and FR-13.
- 2026-09-13, NAF: *"For students, I also want to keep track of anticipated graduation year,
  and undergrad or grad student."* Then: *"It should be graduation semester and year, really.
  Summer, Fall, or Spring. Spring is the default."* Two Student-only fields added to FR-8,
  member-editable since neither grants a privilege; both shown on the officers' member roster
  (FR-87), with a past-graduation filter added there as the natural use.
- 2026-09-13, NAF (quoted at FR-4): registration is callsign-first with an immediate ULS
  lookup filling name and license; the ULS name is read-only to the member, the preferred
  name is theirs; a no-callsign path enters a name by hand. Applied to §2.7, FR-4, FR-8's name
  rows, FR-15 (name override), FR-16 (repurposed to the add-or-change-callsign case), FR-102.
  Then, on FR-16: the member confirms the ULS name themselves, with no sysadmin flag; the
  audit log is the record. The assistant had proposed a sysadmin second look and NAF removed it.
- 2026-09-13, NAF (quoted at FR-27): the background check is HR's and its type is not known to
  the club. §3.3 and FR-27 no longer name a specific check; they record only HR's confirmation.
  The specific name had been taken from clause 1 of the 2024-08-19 agreement, which is noted
  as a candidate correction for the agreement's next revision.
- 2026-09-13, NAF: *"It is fine that the digital system does not store R numbers."* FR-24
  confirmed as written. Resolves Q5.
- 2026-09-13, NAF (quoted at FR-25 and FR-28): agreement approvals default to expiring on the
  next 1 September, with August approvals carried to the September after, so the club renews
  together and nobody gets a term of weeks; the two agreements are signed in one workflow, and
  minors do not sign them (nor guardians for them), so a minor never holds station or IT
  access; 30-day notices ask
  members to re-sign every agreement in one visit. The assistant added the single summary to
  approvers and the bulk re-sign queue, since a shared date means everyone comes due at once.
- 2026-09-13, NAF: *"We will not be pursuing University SSO at this time. We leave the option
  open for a future version."* Section 2.6 updated. Resolves Q9.

- 2026-09-13, NAF (quoted at FR-26): no *active* state; agreements are signed, approved,
  declined, expired, or revoked, and "holds access" means approved and unexpired. Applied to
  FR-26, FR-27, FR-29, FR-31, FR-33, FR-34, FR-61, FR-76, FR-84, FR-92, and the FR-103 table;
  the section 9 row proposing the state is struck.
- 2026-09-13, NAF: *"For FR-44, is the locked step optional? I think it should be optional."*
  The text had not said; it now does. The automatic completion after the last slot is the
  assistant's addition so that events do not linger as published.
- 2026-09-13, NAF, technical decisions (asked one at a time in session; recorded in
  `TECHNICAL_REQUIREMENTS.md` §10): Django/SQLite/gunicorn; server-rendered with htmx, with
  FR-97 amended; TinyMCE; **FCC bulk files as the primary license source** (the draft had
  proposed callook.info); campus-machine backup pull; *"Implement totp and passkey now, but make
  optional. Add the ability to turn on required for certain permission levels. Also allow for
  password less login using passkeys."* (§2.6 rewritten to Must); *"Use healthchecks.io. I
  already use it for hamsci.org"*; origin ports restricted to Cloudflare at go-live.
- 2026-09-13, NAF, answer sheet (`prompts/20260913_open_questions_answers.md`, private
  repository): all nineteen section 8 questions answered. The five that changed the draft:
  Q3 (no application review; completing the form admits, with the inviter told who joined),
  Q6 (minors sign in read-only), Q10 (member directory wanted, FR-13 to Must), Q14 (the
  University's minors policy is met by the responsible-adult rule), Q17 (slot-mates see a
  minor's responsible adults). Q4, Q8, Q11, Q15 accepted the recommendation with a refinement;
  the rest accepted it as drafted. Section 8 is now a table of decisions.
- 2026-09-13, NAF (quoted at FR-118): sysadmins can delete accounts. New FR-118; the
  anonymise-and-retain behaviour (history kept without identity, agreements purged at the end
  of retention, audit log intact), the last-sysadmin guard, and the guardian ordering rule are
  the assistant's.
- 2026-09-13, NAF (quoted at §5.3): the system must be accessible, especially to screen reader
  users. §5.3 promoted from a paragraph to FR-116 (specific commitments) and FR-117
  (verification as a release gate); the itemised commitments are the assistant's reading of
  what that requires of this particular application.
- 2026-09-15, NAF (two use cases quoted at §2.7; decisions quoted at FR-119 to FR-124, FR-61,
  FR-67): entry links replace "invitation only" (FR-1 rewritten); a Provisional access level;
  Mentor needs a license only, station and IT access sit with anyone in the slot; the event's
  minimum class becomes a preferred class with a warning below it; license letters after names;
  check-in credits the slot for a course report. The link mechanism (label, domain, expiry, cap,
  pause), the seven-day verification with an officer's waiver, the identical-response rule on
  the form, and the mentor-needs page's contents are the assistant's; the "Provisional" name and
  every visibility rule are NAF's. Plan: private repository, `notes/2026-09-15_entry-links-plan.md`.
- 2026-09-13, NAF (quoted at FR-115): long texts are HTML edited in a WYSIWYG editor with
  good heading structure encouraged. New FR-115 listing the fields; the sanitisation rule, the
  heading-level offset that keeps one H1 per page, the plain-text alternative for email, and
  the seeded heading outline in FR-77 are the assistant's.
- 2026-09-13, NAF (quoted at FR-113): members check in on arrival, up to 30 minutes early.
  New FR-113; the roster's checked-in state, the late-arrival notice to captains, the minor's
  check-in recording the responsible adult present, and the feed into the participation report
  are the assistant's; FR-114 (a check-in nudge) is a Could. NAF added that check-in must be
  very easy: one tap from the sign-in landing or the top of "my schedule".
- 2026-09-13, NAF (quoted at FR-112 and FR-71): browser notifications as an optional per-device
  setting mirroring email, on by default (the browser's own permission prompt still governs
  each device); notification preferences on the profile page, with cancellations
  always sent. FR-71 rewritten as a category-by-channel preference model with a named
  mandatory set; new FR-112; FR-83 narrowed to SMS. The assistant's additions: the mandatory
  set beyond cancellations (moves by others, account security, agreement decisions and
  expiry), the *reminders off* roster state, and the iOS home-screen constraint.
- 2026-09-13, NAF (quoted at FR-111): a member may change role within a slot when eligible.
  New FR-111; the cutoff behaviour and the no-gap guarantee are the assistant's. On the
  assistant's question of what to do when a role change breaks viability, NAF chose to warn
  the member before the change and let them decide; applied to FR-111 and, by the same logic,
  to cancellation (FR-56).
- 2026-09-13, NAF (quoted at FR-110): sign-ups carry a note to the captains. New FR-110; the
  roster marker and the inclusion of late notes in the captains' digest are the assistant's.
- 2026-09-13, NAF (quoted at FR-51): multiple positions and multiple locations are supported.
  FR-51 to Must, modelling location → position → slot; viability rule per location (FR-61);
  roster grouped by location (FR-65); location in reminders (FR-72); know-before-you-go per
  location (FR-77); FR-36 updated. Resolves Q12.
- 2026-09-13, NAF (quoted at FR-47): setup and breakdown are two kinds of non-operating slot
  among several. FR-47 generalised to a configurable list of kinds, placeable before, after,
  or between operating periods, each with its own viability rule.
- 2026-09-13, NAF (quoted at FR-27): a Community Member agreement needs a `@scranton.edu`
  address on file to be approved, since the University issues one only after HR's process;
  the approver may add the address at approval. Replaces the two-item checklist.

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
