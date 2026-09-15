# Scheduled jobs

How the application's periodic work runs (TR-11, TR-33, FR-93).

## The shape

A job is a Django management command that subclasses `apps.ops.jobs.ScheduledCommand` and
implements `run_job(self, now, **options) -> dict`. The base class does the rest:

- writes a `JobRun` row (started, finished, `ok` or `failed`, the dict you return as `detail`);
- pings the job's healthchecks.io check when `HEALTHCHECKS_PING_KEY` is set: `<slug>?create=1` on
  success, `<slug>/fail` on failure. The check is created by the first ping; the deployment's
  owner sets its period and grace in the healthchecks.io dashboard once;
- accepts `--now <ISO 8601>` so a job can be rehearsed against another instant in tests and in
  acceptance scenarios (T30, T31);
- re-raises a failure as `CommandError` after recording it, so the systemd unit fails too.

Every job is registered in `apps.ops.jobs.JOBS` with its period and grace. The registry is what
the stale-job watchdog (`jobs_stale`) and the status page (`/ops/status/`, sysadmins) read; a job
not registered is not watched.

| Job (`JobRun.name`) | Command | Timer | Does |
|---|---|---|---|
| `selfcheck` | `manage.py selfcheck` | every 5 min | runs `/healthz` in-process; fails if the database is unreachable |
| `jobs:stale` | `manage.py jobs_stale` | hourly | lists registered jobs whose last success is older than period + grace |
| `notify:reminders` | `manage.py notify_reminders` | every 15 min | the FR-72 reminder for each sign-up entering its event's window, once per sign-up |
| `notify:warnings` | `manage.py notify_warnings` | every 15 min | FR-73 at-risk warnings to the people in a slot and a digest to the captains, one per state per 12 h; FR-113 no-show notices |
| `digest:weekly` | `manage.py digest_weekly` | weekly | the FR-79 digest to every member |
| `uls:sync` | `manage.py uls_sync [--full] [--file X.zip]` | daily | the FCC ULS import (FR-14, TR-13): the complete weekly file on Mondays or when the table is empty, else yesterday's daily transaction file; then every member's license record is refreshed |
| `licenses:expiry` | `manage.py licenses_expiry` | daily | notices at 90 and 30 days before a license expires and when it has (FR-17) |
| `agreements:expiry` | `manage.py agreements_expiry` | daily | expires due approvals; one notice per member covering every agreement expiring on a date at 30 days and on the day; one summary to the approvers at each; expires approvals of a superseded version past its re-sign date (FR-28, FR-30) |
| `events:complete` | `manage.py events_complete` | hourly | a published or locked event whose last slot has ended becomes *completed* (FR-44) |
| `openings:announce` | `manage.py openings_announce` | every 15 min | announces role openings that have fired (FR-80); passes lapsed waitlist offers to the next in line (FR-57) |
| `retention:apply` | `manage.py retention_apply` | daily | the retention schedule of REQUIREMENTS §4.3 (TR-28): contact details of long-closed accounts, responsible-adult records, expired agreements and their PDFs, message bodies, lapsed invitations; skips accounts under legal hold; periods are `defaults.retention_*` |

A later phase adds `retention:apply`.

## Running one by hand

```bash
manage.py selfcheck
manage.py jobs_stale --now 2026-10-10T16:00:00+00:00
```

On the server the deployment's `run-remote.sh` has a `job` action for this.

## The timers

The systemd units are not in this repository. The deployment repository holds a templated
service unit (`ops-job@.service`, one instance per job) and a manifest of job name to
`OnCalendar` expression; its installer writes one timer per manifest line. Adding a job means:
the command and its `JobSpec` here; a manifest line there; a row in the healthchecks.io project.

## Health

`/healthz` reports `jobs` (last success per registered job) and `stale_jobs`. The five-minute
self-check is the heartbeat: if its check goes late, the timers or the application are down.
