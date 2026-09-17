# ARCOps: Technical Requirements

**Status: the eight decisions in section 10 were taken by the faculty advisor on 2026-09-13,
three of them amending the draft (TR-13, TR-16, TR-33); formal adoption of the whole document
is pending his read.** Every requirement below states a decision with its reasoning, made
against the functional requirements in [`REQUIREMENTS.md`](REQUIREMENTS.md) (FR-1 to FR-118)
and the constraints of the club's server.

| | |
|---|---|
| **Document status** | Decisions taken 2026-09-13; first build deployed the same day on the advisor's instruction; adoption pending his read |
| **Last revised** | 2026-09-13 |
| **Owner** | Nathaniel A. Frissell, W2NAF (faculty advisor), pending a project lead |
| **Adopted by** | {{NAME, CALLSIGN}} on {{YYYY-MM-DD}} |

---

## 0. How to read this document

**IDs.** Technical requirements are `TR-n`, a separate permanent series from the functional
`FR-n`. Each states a decision, the reasoning, the alternatives considered in a clause, and the
functional requirements it serves. Retire by marking `[RETIRED YYYY-MM-DD]`; never reuse a number.

**The recommendation stance.** Where a choice exists, this document recommends one option and
names the runner-up briefly. It does not survey. The alternatives are listed so that a later
session can see they were weighed, and so that the advisor can pick one of them instead by
saying so.

**Verification.** Facts about software versions, licences, and the server were checked on
2026-09-13 and are tabulated in section 11 with their sources. Memory and throughput figures are
estimates from experience with the named components on comparable hosts and are marked as such;
the build measures them (TR-30).

---

## 1. What the stack must satisfy

Collected from the functional requirements and the server, so that every decision below can be
checked against a list.

| Constraint | Source | Consequence |
|---|---|---|
| 1 vCPU, 956 MB RAM, 496 MB swap, 20 GB free disk, one machine, no budget | the Nanode; NAF, 2026-09-13 | No container orchestrator, no JVM, no separate database server, no paid services. Everything that runs, runs on this box beside nginx and Postfix |
| Maintainable by undergraduates with turnover every few years | REQUIREMENTS §5.8 | Mainstream language and framework with long support windows, few moving parts, one way to do things, a local setup that takes an afternoon |
| GPL-3.0-or-later compatible | REQUIREMENTS §7 | Dependencies under MIT, BSD, Apache-2.0, LGPL, GPL-2.0-or-later, or GPL-3 |
| Documented API alongside the web interface, so a native app is an addition | FR-97 | One service layer, two thin clients (see TR-8 and the proposed amendment in section 10) |
| Installable PWA with web push | FR-96, FR-112 | Service worker, manifest, VAPID keys, a push library |
| Tagged, accessible PDFs of signed agreements | FR-23, FR-116 | An HTML-to-PDF renderer that emits PDF/UA |
| WYSIWYG editor that is itself accessible and GPL-compatible | FR-115, FR-116 | TinyMCE 8 (GPL-2+) or CKEditor 5 (GPL-2+); server-side sanitiser |
| WCAG 2.1 AA, verified in the build | FR-116, FR-117 | Server-rendered semantic HTML; axe-core in CI; a screen-reader gate before release |
| A secret encrypted at rest with a key outside the database | FR-32 | Symmetric encryption with a key in a root-only file on the server |
| Daily and hourly scheduled jobs whose health is visible | FR-14, FR-28, FR-72, FR-73, FR-93 | systemd timers and a job-run table; no queue broker |
| Outbound mail to localhost:25, no credential | REQUIREMENTS §6, decided | SMTP backend pointed at the loopback |
| FCC ULS license data, no more than a day stale | FR-14 | The FCC's own bulk files, imported daily into a local table that answers every lookup instantly (TR-13) |
| Every action works without email | FR-103 to FR-108 | No flow may be gated on a delivery callback |
| All times UTC in storage, dual display | REQUIREMENTS §5.9 | Timezone-aware datetimes; `zoneinfo` |
| Club-specific facts are configuration | REQUIREMENTS §1.5 | A settings model in the database seeded from a file; agreement texts loaded at deploy from the private repository |
| Nightly backup off the box, restore rehearsed, at no cost | REQUIREMENTS §4.4 | Encrypted dump pulled by a campus machine (TR-22) |

---

## 2. Architecture in one picture

```
                 Cloudflare (DNS, TLS at the edge, proxy)
                                |
   ---------------------------- the Nanode ------------------------------
   |  nginx :443  (TLS to Cloudflare, static files, security headers,   |
   |               rate limits, /healthz)                                |
   |     |  unix socket                                                   |
   |  gunicorn (2 workers) -> Django application                         |
   |     |         |                 |                                    |
   |  SQLite (WAL) | media/ (signed-agreement PDFs)                       |
   |               |                                                      |
   |  systemd timers -> `manage.py <job>` (ULS sync, reminders, warnings, |
   |                    expiry notices, digest, retention, backup)        |
   |               |                                                      |
   |  Postfix :25 (loopback only) + OpenDKIM  -> the internet             |
   |  /etc/ops.w3usr.org/env  (SECRET_KEY, field key, VAPID keys; root)   |
   -----------------------------------------------------------------------
                 |                                    ^
     web push to members' browsers          nightly encrypted backup,
     (VAPID, best effort)                   pulled by a campus machine
```

One process tree, one database file, one deploy script. The parts a student must understand to
fix the site at 2 a.m. are nginx, gunicorn, Django, SQLite, and systemd, and every one of them
has a decade of documentation.

---

## 3. Platform decisions

- **TR-1 Language and framework: Python 3.12+ and Django 5.2 LTS**, moving to 6.2 LTS when it
  ships (April 2027) and 5.2 nears its April 2028 end of support. *Why:* Django ships the
  parts this application is mostly made of (accounts, sessions, permissions, forms, admin, ORM,
  migrations, CSRF and security middleware, email, timezone handling), so students build the
  club's logic and not the plumbing; it is the most-taught Python web framework; the club's
  other software is Python; the server runs Python 3.14, which 5.2.8+ supports. *Considered:*
  Flask (fewer batteries; every one of those parts becomes a choice), FastAPI (excellent API,
  thin on the rest), Rails/Laravel (a second language for the club to know). Serves: §5.8, §7.
- **TR-2 Datastore: SQLite in WAL mode**, one file under `/srv/ops.w3usr.org/var/`, accessed
  only by the application. *Why:* the club has tens of members and a few hundred writes on a
  contest day; SQLite handles orders of magnitude more; it needs no server process, no memory
  of its own, no administration; a backup is one file; a rebuild is a copy. Django's ORM keeps
  the door to PostgreSQL open if the club ever outgrows it. *Considered:* PostgreSQL (the right
  answer at ten times the load, and 100–200 MB of the box's memory now). Serves: §5.2, §4.4.
- **TR-3 Application server: gunicorn**, two synchronous workers, a unix socket, behind the
  existing nginx, as a systemd service (`ops-web.service`). *Why:* the standard pairing; two
  workers fit the budget (TR-30) and are plenty for the club's concurrency. *Considered:*
  uvicorn/ASGI (no async need in v1; add if server-sent events are wanted later).
- **TR-4 Front end: server-rendered Django templates, progressively enhanced with htmx** and
  a small amount of plain JavaScript; **no single-page framework**. *Why:* server-rendered
  semantic HTML is the shortest path to WCAG AA and screen-reader correctness (FR-116); it
  needs no build toolchain, so a student edits a template and reloads; htmx gives the roster
  its in-place updates (a slot changing state, a sign-up landing) with a few attributes.
  *Considered:* React/Vue SPA (a second toolchain, a second language, and accessibility that
  must be re-earned component by component; the API still exists without it, see TR-8).
  Serves: FR-65, FR-116, §5.8.
- **TR-5 CSS: a small semantic base stylesheet plus project CSS**, with colour tokens and a
  dark mode; the base is Pico CSS (MIT) or equivalent classless framework. *Why:* accessible
  defaults for forms and tables out of the box; no utility-class build step. Colour-blind-safe
  palette and text-plus-icon status (FR-62) are project CSS.
- **TR-6 PWA: a web app manifest and a hand-written service worker** that caches the shell and
  the member's own schedule for offline reading (FR-96); no framework. Installable on Android,
  desktop, and iOS (home-screen install required on iOS for push).
- **TR-7 Web push: `pywebpush` with VAPID keys** generated once on the server and kept in the
  env file (TR-19); subscriptions stored per device (FR-112); delivery best effort, failures
  logged and never retried. Serves: FR-112, FR-114.
- **TR-8 API: Django Ninja**, generating OpenAPI, mounted at `/api/v1/`, using session
  authentication for the web and token authentication for a future native client. Both the
  templates and the API call **one service layer** (plain Python modules per domain: accounts,
  events, credentials, comms) so that the rules live once. *Why:* Ninja is small,
  type-annotated, and documents itself; the service layer is what makes "a native app is an
  addition" true without forcing the web UI to be an API client. *Considered:* Django REST
  Framework (heavier, more ceremony). Serves: FR-97, and see the amendment in section 10.
- **TR-9 Rich text: TinyMCE 8 under its GPL-2.0-or-later option** (`license_key: 'gpl'`),
  self-hosted from the repository's static files, configured to the FR-115 feature set (three
  heading levels, lists, links, emphasis, simple tables) with accessibility checking on; all
  saved HTML passed through **nh3** (an allow-list sanitiser) on save and again on render.
  *Why:* TinyMCE's accessibility work is mature and its GPL option is compatible with this
  repository's licence; nh3 is the maintained successor to bleach. *Considered:* CKEditor 5
  (also GPL-2+, equally capable; the choice between the two is taste, and either satisfies
  FR-115 and FR-116). Serves: FR-115, FR-116.
  *As built (2026-09-15):* `django-tinymce` 4.1.0, which bundles **TinyMCE 6.8.4 under the MIT
  licence** (no licence key), self-hosted from the package's static files; the FR-115 feature
  set as above; the premium accessibility checker is not available, so `static/js/richtext-check.js`
  warns beneath the editor when a heading level is skipped. The saved HTML goes through nh3.
- **TR-10 PDF: WeasyPrint** rendering the signed agreement from an HTML template with
  `pdf_variant='pdf/ua-1'` and `pdf_tags=True`, so the document is tagged (FR-116). WeasyPrint
  states that conformance is the author's to verify, so the template is checked once with a
  PDF/UA validator by hand and re-checked when it changes. *Why:* the agreement is already HTML
  (FR-21), so one template serves the screen and the PDF. *Considered:* ReportLab (a second
  layout language). Serves: FR-23, FR-116.
- **TR-11 Scheduled jobs: systemd timers running Django management commands**, one per job,
  each writing a row to a `job_runs` table (started, finished, outcome, counts) that the FR-93
  status page reads and that a `jobs:stale` check alerts on. Jobs: `uls:sync` (daily),
  `notify:reminders` and `notify:warnings` (every 15 minutes), `agreements:expiry` (daily),
  `digest:weekly`, `retention:apply` (daily), `backup:nightly`. *Why:* no broker, no worker
  process, no memory; visible in `systemctl list-timers` and in `deploy/run-remote.sh status`.
  *Considered:* Celery + Redis (a second and third process on a 1 GB box), django-q2/huey
  (workable, but a worker process for a handful of daily jobs). Serves: FR-14, FR-72, FR-73,
  FR-28, FR-79, FR-93, §4.3.
- **TR-12 Email: Django's SMTP backend to `localhost:25`**, no authentication, no TLS on the
  loopback; messages built as multipart (HTML plus a generated text alternative via
  `html2text`); `List-Unsubscribe` and `List-Unsubscribe-Post` headers on list mail (FR-81);
  `Reply-To` per FR-69. An outbox table records every message and its state (FR-105). Serves:
  §6 of REQUIREMENTS (decided), FR-69 to FR-82, FR-105.
- **TR-13 FCC license data: the FCC's ULS bulk files, imported into a local table.** The
  application keeps its own table of every US amateur license (callsign, licensee name, operator
  class, status, grant and expiry dates, FRN) built from the FCC's weekly complete Amateur file
  (`l_amat.zip`, 198 MB compressed, produced Sundays) and kept current by the daily transaction
  files (`l_am_<day>.zip`, tens of kilobytes), both streamed from the pipe-delimited `HD`, `AM`,
  and `EN` records without ever holding the file in memory. `uls:sync` (TR-11) applies the daily
  file each night and the full file each week. Every lookup the application makes, at
  registration (FR-4), on a callsign change (FR-102), and in the nightly credential refresh
  (FR-14), is a local query and therefore instant and free of any third party; a callsign not
  yet in the table is *unverified* until the next import, which is what FR-4 and FR-102 already
  say. Disk: roughly 150–250 MB for the table and the current archive (estimate). CPU: a few
  minutes a week on one core. *Why (the advisor's decision, 2026-09-13):* no dependence on a
  donation-run hobby service for a credential that gates who may operate. *Considered:*
  callook.info (JSON, no key, maintained by W1JDD; the draft's proposal; kept in mind as an
  optional on-demand check if a grant hours old ever needs confirming before the nightly import),
  QRZ XML (subscription), HamQTH. The record layout is confirmed against the FCC's public access
  file definitions by the developer who implements it. Serves: FR-4, FR-14, FR-16, FR-102.

- **TR-14 Time: timezone-aware UTC everywhere in storage and logic** (`USE_TZ = True`),
  `zoneinfo` for display in the event's zone; slot boundaries are stored instants and never
  shift at a daylight-saving change. Serves: §5.9.

---

## 4. Security decisions

- **TR-15 Authentication: `django-allauth` (MIT) for accounts and sign-in, with Argon2 password
  hashing**; email address as the login identifier; Django's password validators plus a
  breached-password check against the Have I Been Pwned range API (k-anonymity: five characters
  of the hash leave the server, the password never does); one-time temporary passwords (FR-7)
  and single-use signed tokens (FR-100) built on Django's signing with expiry. *Why allauth:* it
  carries the whole account surface (sign-in, reset, email management) and the MFA module TR-16
  needs, maintained and current (65.19, September 2026). Serves: §2.6, FR-7, FR-99, FR-100,
  FR-107.
- **TR-16 Second factor and passkeys: both built in v1, optional by default, requirable per
  access group.** allauth's MFA module provides TOTP (any authenticator app), WebAuthn
  **passkeys** as a second factor, **passwordless sign-in by passkey**, and recovery codes. A
  member enrols either or both from the profile page. A sysadmin setting (FR-89) marks, per
  access group, whether a second factor is **required**; the
  shipped default requires none, and a level switched to required gives its holders a grace
  period with a banner before sign-in is blocked. A passkey-only account has no password to
  forget; FR-107's reset path still works for accounts that have one.

  > Implement totp and passkey now, but make optional. Add the ability to turn on required for
  > certain permission levels. Also allow for password less login using passkeys.
  > — NAF, 2026-09-13

  *Considered:* `django-otp` alone (TOTP only; the draft's proposal), hand-rolled WebAuthn on
  `py_webauthn` (more code for the club to own). Serves: §2.6, §5.7.

- **TR-17 Sessions and re-authentication**: server-side sessions in the database; 14-day
  "remember this device" and a 12-hour idle timeout otherwise; viewing the computer password
  requires the member's password again within the last five minutes (FR-33). Cookies `Secure`,
  `HttpOnly`, `SameSite=Lax`.
- **TR-18 Rate limiting: nginx `limit_req` on the sign-in, reset, and invitation endpoints**,
  plus application-level lockout after repeated failures with a notice to the account owner
  (FR-99). *Why:* nginx stops the flood before Python sees it; the application handles the
  per-account rule.
- **TR-19 Secrets: one root-owned environment file on the server**, `/etc/ops.w3usr.org/env`,
  mode 0600, holding `SECRET_KEY`, the field-encryption key (TR-20), and the VAPID key pair;
  generated by the private repository's bootstrap on first run, never committed to either
  repository, recorded in the private repository's credential inventory, and rotated on
  turnover per that inventory's rules. The application refuses to start without it. *Why:* the
  same pattern the DKIM key already uses; a secret generated in place has no history to leak.
- **TR-20 Encryption at rest for the computer password: Fernet (AES-128-CBC with HMAC) from
  the `cryptography` package**, key from TR-19, ciphertext in the database. Backups therefore
  carry the ciphertext and not the key. Every decryption (a view under FR-33) writes an audit
  row. Serves: FR-32, FR-33, §5.7.
- **TR-21 Audit log: an append-only table** enforced by SQLite triggers that raise on `UPDATE`
  and `DELETE`, written through one service function so no code path forgets it; entries carry
  actor, subject, action, timestamp, and before/after JSON (FR-92). Retained indefinitely
  (§4.3). *Why:* an audit log the application can edit is a diary.
- **TR-22 Backups: nightly, encrypted, pulled off the box at no cost** (adopted 2026-09-13; the
  campus machine is the one that already pulls the club's other site's backups, on a parallel
  path and the same retention ladder, per the advisor). `backup:nightly` runs
  `sqlite3 .backup` for a consistent copy, tars it with `media/` (the signed PDFs), encrypts
  with `age` to a public key whose private half the advisor holds offline, and leaves the file
  in `/srv/ops.w3usr.org/backup/` with seven days retained. A cron job on a campus machine the
  advisor controls (the Linode cannot reach campus hosts by name, but campus can reach the
  Linode) pulls the newest file nightly over SSH with a read-only key and keeps 90 days. A
  restore is rehearsed onto a scratch checkout before the first live event and each summer,
  and the date recorded in the private repository's notes. The pull is least-privilege: a
  dedicated backup user on the server whose only permitted command is a read-only `rrsync` of
  the backup directory, authorised for the campus machine's key. Archives carry a SHA-256
  sidecar so the puller can verify what arrived without holding the decryption key. Retention
  on the campus side follows the advisor's grandfather-father-son ladder: everything for 7
  days, four days a month for a month, two a month for a year, one a month for three years,
  1 January forever. *Considered:* a private GitHub
  repository as the destination (also free; encrypted files of a few megabytes; acceptable
  if no campus machine is available); Linode's backup service and object storage (paid).
  Serves: §4.4.
- **TR-23 Transport and headers**: TLS terminates at Cloudflare and again at nginx (already
  in place); HSTS, CSP, and the other headers already in the nginx snippet, with the CSP
  tightened to the application's actual script and style sources (TinyMCE self-hosted, no
  third-party scripts); the origin's ports 80 and 443 restricted to Cloudflare's published
  ranges once the application is live, since `mail.w3usr.org` now publishes the origin
  address (adopted 2026-09-13). The monthly job that already fetches Cloudflare's ranges for
  nginx's real-IP list feeds the firewall rules too, so the two never disagree. Serves: §5.7.
- **TR-24 Dependencies**: pinned in `requirements.txt` from a `requirements.in`; Dependabot
  enabled on the public repository; a published advisory in a dependency is a task, and the
  monthly `deploy` picks up patch releases. Serves: §5.7, `.claude/rules/web-development.md`.
- **TR-25 Uploads**: the application accepts no file uploads in v1 (agreement PDFs are
  generated, not uploaded), which removes a class of risk; if images in rich text are ever
  wanted (FR-115 leaves them out) they arrive with their own requirement.

---

## 5. Data decisions

- **TR-26 Schema**: one Django app per domain, each owning its tables. Sketch, with the FRs
  they serve:

  | App | Tables (principal columns) | FRs |
  |---|---|---|
  | `accounts` | `User` (ULS and preferred names, phone, category, position, under-18 flag, student level, graduation term), `Address` (one row per address, its kind, confirmation, delivery switch), `Guardianship` (guardian ↔ minor, history), `Invitation` (token, category, state, issuer), `CallsignHistory`, `NotificationPreference`, `PushSubscription` | FR-1 to FR-13, FR-71, FR-102, FR-109, FR-112 |
  | `credentials` | `CredentialType` (config), `LicenseRecord` (class, status, dates, source, retrieved, override), `AgreementTemplate` (type, audience, version, HTML, hash), `SignedAgreement` (signer, version hash, signature block, PDF path, state, expiry, approver), `SharedSecret` (the computer password, Fernet ciphertext, effective date) | FR-14 to FR-35 |
  | `events` | `Event` (type, title, description, display zone, state, contest fields, calendar ref), `OperatingPeriod`, `OperatingLimit`, `Location`, `Position`, `Slot` (kind, times, closed/cancelled), `RoleCapacity`, `EligibilityRule`, `Opening`, `SignUp` (person, role, note, confirmed, checked-in, control-operator flag), `ResponsibleAdult` (per minor sign-up), `WaitlistEntry`, `Captaincy` | FR-36 to FR-68, FR-110, FR-111, FR-113 |
  | `comms` | `MessageTemplate`, `Outbox` (recipient, channel, category, body, state, sent/failed), `Announcement` (sender, audience definition, recipients) | FR-69 to FR-82, FR-105, FR-106 |
  | `ops` | `ClubSetting` (key/value config), `AuditLog`, `JobRun` | FR-89 to FR-94, §1.5 |

  Every table has `created`/`updated` timestamps; personal fields are marked in the model so
  the retention and deletion jobs (FR-11, FR-118, §4.3) find them without a hand-kept list.
- **TR-27 Migrations**: Django migrations, committed, run by `deploy.sh` before the service
  restarts; a migration that drops or rewrites personal data is reviewed by a second person.
- **TR-42 Permissions**: capabilities are Django permissions on a table-less model in the `ops`
  app, declared in one list (`apps/ops/capabilities.py`); an access group is a Django group; a
  sysadmin is a superuser. `club_import` writes any new capability and seeds the configured
  groups, and the deploy runs it. Nothing in the application tests a rank: every decision asks
  whether an account holds a named capability (§2.1). A permission matrix test
  (`apps/accounts/tests/test_permission_matrix.py`) asserts what every kind of account gets from
  every page, because the failure mode is silent.
- **TR-28 Retention**: `retention:apply` (TR-11) implements §4.3 exactly: it deletes on schedule
  what is not a member's own record, logs what it did to the audit log by count, and never
  touches a row under a legal hold flag (added for the case where a record must be kept). A
  member's own record is never on that list: former members are archived and kept (FR-125).
- **TR-29 Sizing**: with 100 members, 30 events a year, and 2,000 sign-ups, the database is
  under 50 MB and the PDFs under 200 MB after five years (estimate). A daily backup is a few
  megabytes encrypted. Disk is not a constraint for a decade.

---

## 6. Operations decisions

- **TR-30 Memory budget** (estimates, to be measured in the first week and recorded):

  | Component | Resident memory, estimate |
  |---|---|
  | nginx | ~10 MB |
  | gunicorn, 2 Django workers | ~150–200 MB |
  | Postfix + OpenDKIM | ~30 MB |
  | SQLite | inside the workers |
  | A scheduled job while running | ~60–100 MB, transient |
  | WeasyPrint rendering one PDF | ~100–150 MB, transient |
  | OS, journald, sshd, unattended-upgrades | ~150 MB |

  Total steady state around 350–400 MB of 956 MB, with the 496 MB swap as headroom for a PDF
  render coinciding with a job. Two workers is the ceiling; the build does not add a third
  without measuring. If the budget is ever wrong, the fix is the next Linode size, not a
  redesign.
- **TR-31 Deployment**: the private repository's `deploy.sh` grows five steps after the
  fast-forward: create or update the virtual environment, `pip install -r requirements.txt`,
  `manage.py migrate`, `manage.py collectstatic`, `systemctl restart ops-web`, then `/healthz`
  is checked before the script reports success; a failed health check prints the last 50 log
  lines. Bootstrap gains the `ops-web.service` unit, the timers, the env file (TR-19), the
  `backup/` directory, and the `age` and `sqlite3` packages. Serves: the private repository's
  "server is configured only from this repository" rule.
- **TR-32 Configuration**: everything club-specific is a `ClubSetting` row (§1.5), seeded by
  `manage.py club_import` from a configuration directory (TR-40) and edited in the sysadmin
  interface afterwards (FR-89); interface edits win over the file unless the import is run with
  `--reset`, so officers work in the interface and the file stays the seed and the record.
- **TR-33 Logging and health**: application logs to journald through gunicorn (structured
  one-line JSON per request and per job); no personal data in log lines beyond the user id;
  `/healthz` returns the database's reachability, the last `uls:sync` time, and the outbox
  failure count, and is what `deploy/run-remote.sh status` reads. **External monitoring is
  healthchecks.io** (the advisor's decision; the club's advisor already uses it for hamsci.org):
  every scheduled job (TR-11) pings its own check on success, so a job that stops running raises
  an alert when its ping is late; a five-minute self-check timer fetches `/healthz` locally and
  pings only on a healthy answer, so a down site or a failing database also goes quiet and
  alerts. Alerts go to the club address. The free plan's 20 checks cover the seven jobs, the
  self-check, and the backup pull with room to spare. Ping URLs are treated as secrets and live
  in the env file (TR-19); the account is recorded in the private repository's credential
  inventory. *Considered:* a polling uptime monitor (the draft's proposal; healthchecks.io's
  ping model catches the silent job failure a poller cannot).

  > Use healthchecks.io. I already use it for hamsci.org — NAF, 2026-09-13

- **TR-40 Generic defaults: the public repository ships a fully working club.** `config/`
  holds `club.example.yaml` (every configuration key with neutral values), `assets/` (a
  text-free placeholder logo usable as favicon and icon), and `agreements/` (example station-
  access and computer-use templates, clearly marked as illustrations for the adopting club's
  advisor to replace; the application shows a banner while a template key ends in
  `.example`). A fresh checkout with `seed_demo` therefore runs, signs, approves, schedules,
  and reminds as "Example Amateur Radio Club" with nothing edited. **The code never names a
  club**: CI greps `apps/`, `templates/`, and `static/` for the string `w3usr` and fails on a
  hit (TR-38). Another club adopts the application by editing `club.yaml` and replacing the
  two directories, or by supplying an overlay (TR-41). *Why (the advisor's direction,
  2026-09-13):* the open-source release must work for another club at once, with the W3USR
  assets kept separate but deployable. Serves: §1.5, §7, FR-12, FR-18, FR-21, FR-89.
- **TR-41 Club overlay: W3USR's assets are tracked privately and laid over the defaults at
  deploy.** The application reads an **overlay directory** (`CLUB_OVERLAY_DIR`, on the server
  `/srv/ops.w3usr.org/club/`) with the same layout as `config/` (`club.yaml`, `static/club/…`,
  `agreements/…`) before the shipped defaults, for every club-specific thing: configuration,
  logo and icons, QSL card, agreement texts, message-template overrides. `club_import` loads
  the overlay's `club.yaml` and agreement files, versioning each agreement by content hash
  (FR-21, FR-30); `collectstatic` places `static/club/` ahead of the defaults. Removing the
  overlay yields the generic club, which is how the public repository is tested. The W3USR
  overlay is held in the club's private orchestration repository with a **manifest** that
  traces every asset to its master (the club's image library, the paper agreements), records
  the derivation command, the approval for public use, and the date regenerated; the deploy
  copies the overlay to the server and runs the import on every `deploy`. An asset not in the
  manifest is not deployed. Serves: §1.5, §7, TR-32.
- **TR-34 Environments**: `prod` on the Nanode and `dev` on a student's laptop, the only
  difference being the env file and the email backend (console in dev). No staging server; the
  club has one box. A `manage.py seed_demo` command fills a dev database with fictitious
  members, a past and a future event, and every credential state, so a new developer sees the
  application working within the afternoon §5.8 asks for.

---

## 7. Quality decisions

- **TR-35 Tests: pytest with pytest-django**, factories for the models, coverage measured and
  reported; the service layer (TR-8) at or above 80 % line coverage, the viability rule
  (FR-61 to FR-64) and the date and expiry arithmetic (FR-25, FR-38, FR-39) covered by
  table-driven cases including the PA QSO Party split, School Club Roundup limits, the
  August-approval expiry rule, and the daylight-saving weekend.
- **TR-36 Accessibility in CI: Playwright (Python) driving a headless browser with axe-core
  injected**, run against the seeded dev database on every pull request over the pages FR-117
  names; any violation at the "serious" or "critical" level fails the build. The manual
  screen-reader walk (FR-117) is recorded in a checklist file per release. No Node toolchain is
  needed at runtime; Playwright's Python package brings its own browser.
- **TR-37 Static analysis: `ruff` (lint and format) and `djlint` for templates**, run by
  pre-commit locally and by CI. Type hints on the service layer, checked with `mypy` in
  non-strict mode.
- **TR-38 CI: GitHub Actions on the public repository** (free for public repositories): lint,
  tests, accessibility checks, a `pip-audit` dependency scan, and the club-neutrality grep
  (TR-40) on every push and pull request. CI never deploys; deployment stays a human action from the private repository.
- **TR-39 Definition of done for a change**: tests pass, accessibility checks pass, the
  requirement ID it implements is in the commit message, and if the change sends a message it
  has a row in the FR-103 table.

---

## 8. Repository layout (public application repository)

```
arcops/
|-- manage.py
|-- config/                 <- Django settings (base, dev, prod), urls, wsgi
|   |-- club.example.yaml   <- generic configuration seed (TR-40); club.yaml in a fork, or an overlay (TR-41)
|   |-- assets/             <- neutral placeholder logo and icons
|   `-- agreements/         <- example agreement templates, marked for replacement
|-- apps/
|   |-- accounts/  credentials/  events/  comms/  ops/      <- TR-26; each: models, services, api, views, templates, tests
|-- templates/              <- base layout, components (roster table, slot card, status badge)
|-- static/                 <- project CSS and JS, service worker, manifest, TinyMCE (vendored)
|-- prototypes/             <- proofs that predate the stack; deleted as their lessons land in apps/
|-- requirements.in / requirements.txt
|-- pyproject.toml          <- ruff, mypy, pytest configuration
|-- .github/workflows/ci.yml
|-- docs/                   <- REQUIREMENTS.md, TECHNICAL_REQUIREMENTS.md, ONBOARDING.md, ADRs
`-- web/                    <- retired once the application serves the root
```

Architecture decision records (`docs/adr/NNNN-title.md`) capture any later deviation from this
document, with the TR it supersedes.

---

## 9. Development environment

```bash
git clone https://github.com/w3usr/arcops.git && cd arcops
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp config/env.example .env            # dev secrets, gitignored
python manage.py migrate && python manage.py seed_demo
python manage.py runserver            # http://localhost:8000, sign in as the seeded sysadmin
```

Six commands, standard Python, no Node, no Docker. Email goes to the console; push is disabled
in dev unless a VAPID pair is generated with `manage.py vapid_keys`. This block becomes the
"run it locally" section of `ONBOARDING.md` when adopted.

---

## 10. Decisions taken by the advisor, 2026-09-13

Asked one at a time in session and answered as recorded here; three answers amended the draft.

| # | Question | Decision | Applied at |
|---|---|---|---|
| 1 | Django 5.2 LTS, SQLite (WAL), gunicorn behind nginx? | Agree | TR-1, TR-2, TR-3 |
| 2 | Server-rendered templates with htmx, no SPA; FR-97 amended to one service layer with two thin clients? | Agree | TR-4, TR-8; FR-97 |
| 3 | TinyMCE 8 or CKEditor 5? | TinyMCE 8 | TR-9 |
| 4 | callook.info with FCC bulk files as fallback, or bulk files primary? | **FCC bulk files as primary** | TR-13 (rewritten) |
| 5 | Backup destination? | The campus machine that already pulls the club's other site's backups, on a parallel path with the same retention ladder | TR-22 |
| 6 | Second factor required for officers as well as sysadmins? | **TOTP and passkeys both built now, optional by default; a per-level "required" setting; passwordless sign-in by passkey** | TR-15, TR-16 (rewritten); REQUIREMENTS §2.6 |
| 7 | External uptime monitor? | **healthchecks.io**, which the advisor already uses for hamsci.org | TR-33 (rewritten) |
| 8 | Restrict origin ports 80/443 to Cloudflare's ranges at go-live? | Agree | TR-23 |

**Added 2026-09-13, on the advisor's direction:** TR-40 (generic defaults so the release works
for any club) and TR-41 (the W3USR overlay, tracked privately and deployed).

**Open after these decisions:** the healthchecks.io
project and check names (private repository's credential inventory); formal adoption of this
document and of `REQUIREMENTS.md` once the advisor has read them through.

---

## 11. What was verified, and when

| Fact | Source | Date |
|---|---|---|
| Server: Python 3.14.4, 956 MB RAM, 496 MB swap, 20 GB free, 1 vCPU; `age` 1.2.1, `sqlite3` 3.46, `python3-cryptography` 46 packaged | the Linode, over SSH | 2026-09-13 |
| Django 5.2 is the LTS, extended support to April 2028; Python 3.14 supported from 5.2.8 | djangoproject.com download page and 5.2 install FAQ | 2026-09-13 |
| WeasyPrint 70.0: `pdf_variant` accepts `pdf/ua-1` and `pdf/ua-2`; `pdf_tags` tags for accessibility; conformance is the author's to verify | WeasyPrint API reference | 2026-09-13 |
| TinyMCE 8 is GPL-2.0-or-later with `license_key: 'gpl'` required in configuration | tiny.cloud licence-key documentation | 2026-09-13 |
| CKEditor 5 is GPL-2.0-or-later with a commercial alternative | ckeditor5 `LICENSE.md` | 2026-09-13 |
| callook.info returns `status`, `type`, `current.callsign`, `current.operClass`, `previous`, `trustee`, `name`, `address`, `location`, `otherInfo.grantDate`, `otherInfo.expiryDate`, `otherInfo.lastActionDate`, `otherInfo.frn`, `otherInfo.ulsUrl` as JSON at `/{CALLSIGN}/json`; maintained by W1JDD; no published terms or rate limit | callook.info, API page and a live lookup | 2026-09-13 |
| `pywebpush` 2.5.0, `nh3` 0.3.7, `django-otp` 1.7.3, `weasyprint` 70.0, `gunicorn` 26.2.0, `django-ninja` 1.7.0 exist on PyPI | `pip index versions` | 2026-09-13 |
| `django-allauth` 65.19.3 (2026-09-11): MFA module supports TOTP, WebAuthn credentials, and login by passkey; WebAuthn is off by default and must be enabled; install as `django-allauth[mfa]` | docs.allauth.org, MFA introduction | 2026-09-13 |
| `webauthn` 3.0.0 and `fido2` 2.2.1 exist on PyPI (the primitives allauth builds on) | `pip index versions` | 2026-09-13 |
| healthchecks.io: ping-based (jobs ping, it alerts when a ping is late); free plan monitors 20 jobs with 100 log entries per job | healthchecks.io/pricing | 2026-09-13 |
| The Linode cannot resolve or reach campus hosts by name; campus can reach the Linode | connection test from the server; the 2026-09-12 infrastructure note | 2026-09-13 |
| FCC ULS bulk files exist at `data.fcc.gov/download/pub/uls/complete/l_amat.zip` (197,744,902 bytes, last modified Sun 6 Sep 2026) and `.../daily/l_am_<day>.zip` (57,889 bytes for Saturday) | HTTP HEAD requests | 2026-09-13 |

The FCC's documentation page refused the fetch, so the files themselves were checked; their
internal record format (pipe-delimited `HD`, `AM`, `EN`) is from experience with the ULS public
access files and is confirmed by the first developer who implements the fallback (TR-13).
Memory figures in TR-30 are estimates.

---

<sub>Drafted by Claude (Anthropic), `claude-fable-5-1`, under W2NAF's direction, against the
functional requirements and the server as found on 2026-09-13. Every decision is a proposal
until adopted; the decisions are the club's.<br>Co-Authored-By: Claude Fable 5.1
&lt;noreply@anthropic.com&gt;</sub>
