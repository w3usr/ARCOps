"""
Scheduled jobs (TR-11, TR-33, FR-93).

A job is a management command that subclasses ScheduledCommand. Each run writes a JobRun row
(started, finished, outcome, detail) and, when a healthchecks.io ping key is configured, pings
the check for its slug: `.../<key>/<slug>?create=1` on success (the check is created on the
first ping) and `.../<key>/<slug>/fail` on failure. The systemd timers that fire the commands
live in the private deployment repository (`deploy/timers/`).

JOBS is the registry the stale-job watchdog and the status page read: every job the timers run
must be here with the period the timer uses and the grace it is allowed. A job not registered is
not watched.
"""

from __future__ import annotations

import logging
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import JobRun

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class JobSpec:
    name: str  # JobRun.name and the TR-11 label, e.g. "uls:sync"
    label: str
    period: timedelta  # how often the timer fires
    grace: timedelta  # how late a run may be before it counts as stale

    @property
    def slug(self) -> str:
        """The healthchecks.io check slug: ops-<name> with punctuation as hyphens."""
        return "ops-" + self.name.replace(":", "-").replace("_", "-")

    @property
    def command(self) -> str:
        return self.name.replace(":", "_")


JOBS: dict[str, JobSpec] = {
    spec.name: spec
    for spec in (
        JobSpec("selfcheck", "Self-check of /healthz", timedelta(minutes=5), timedelta(minutes=10)),
        JobSpec("jobs:stale", "Stale-job watchdog", timedelta(hours=1), timedelta(minutes=30)),
        JobSpec(
            "notify:reminders",
            "Slot reminders (FR-72)",
            timedelta(minutes=15),
            timedelta(minutes=30),
        ),
        JobSpec(
            "notify:warnings",
            "At-risk warnings and no-show notices (FR-73, FR-113)",
            timedelta(minutes=15),
            timedelta(minutes=30),
        ),
        JobSpec("digest:weekly", "Weekly digest (FR-79)", timedelta(days=7), timedelta(days=1)),
    )
}


def register(spec: JobSpec) -> None:
    """Later phases add their jobs here (reminders, warnings, uls:sync, ...)."""
    JOBS[spec.name] = spec


def ping(slug: str, ok: bool) -> bool:
    """Ping healthchecks.io for the slug. Returns False (and logs) when not configured or on
    any network error; a failed ping never fails the job."""
    key = getattr(settings, "HEALTHCHECKS_PING_KEY", "")
    if not key:
        return False
    base = getattr(settings, "HEALTHCHECKS_PING_URL", "https://hc-ping.com").rstrip("/")
    url = f"{base}/{key}/{slug}" + ("?create=1" if ok else "/fail?create=1")
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:  # noqa: S310 - fixed https host
            return 200 <= resp.status < 300
    except Exception as exc:  # noqa: BLE001
        log.warning("healthchecks ping failed for %s: %s", slug, exc)
        return False


def last_ok(name: str) -> JobRun | None:
    return JobRun.objects.filter(name=name, outcome="ok").order_by("-finished").first()


def last_run(name: str) -> JobRun | None:
    return JobRun.objects.filter(name=name).order_by("-started").first()


def is_stale(spec: JobSpec, now: datetime | None = None) -> bool:
    """A job is stale when its last successful run is older than period + grace, or it has
    never succeeded and the JobRun table has existed for longer than that (the first run of a
    fresh deployment gets the same grace as every later one)."""
    now = now or timezone.now()
    last = last_ok(spec.name)
    if last and last.finished:
        return now - last.finished > spec.period + spec.grace
    first_any = JobRun.objects.order_by("started").first()
    if first_any is None:
        return False
    return now - first_any.started > spec.period + spec.grace


def stale_jobs(now: datetime | None = None) -> list[str]:
    return [name for name, spec in JOBS.items() if is_stale(spec, now)]


def status_rows(now: datetime | None = None) -> list[dict]:
    """What the status page (FR-93) shows, one row per registered job."""
    now = now or timezone.now()
    rows = []
    for spec in JOBS.values():
        rows.append(
            {
                "spec": spec,
                "last": last_run(spec.name),
                "last_ok": last_ok(spec.name),
                "stale": is_stale(spec, now),
            }
        )
    return rows


class ScheduledCommand(BaseCommand):
    """Base class for every job. Subclasses set `job_name` (a key of JOBS) and implement
    `run_job(self, now, **options) -> dict`, returning the counts to store on the JobRun."""

    job_name = ""

    def add_arguments(self, parser):
        parser.add_argument(
            "--now",
            help="ISO 8601 instant to treat as now (tests and rehearsals); default: the clock",
        )

    @property
    def spec(self) -> JobSpec:
        try:
            return JOBS[self.job_name]
        except KeyError as exc:
            raise CommandError(
                f"job {self.job_name!r} is not registered in apps.ops.jobs.JOBS"
            ) from exc

    def handle(self, *args, **options):
        spec = self.spec
        now = timezone.now()
        raw_now = options.pop("now", None)
        if raw_now:
            parsed = parse_datetime(raw_now)
            if parsed is None:
                raise CommandError(f"--now {raw_now!r} is not an ISO 8601 instant")
            now = parsed if timezone.is_aware(parsed) else timezone.make_aware(parsed)
        run = JobRun.objects.create(name=spec.name)
        try:
            detail = self.run_job(now, **options) or {}
        except Exception as exc:  # noqa: BLE001 - recorded, pinged, then re-raised
            run.outcome, run.detail = "failed", {"error": f"{exc.__class__.__name__}: {exc}"[:500]}
            run.finished = timezone.now()
            run.save(update_fields=["outcome", "detail", "finished"])
            ping(spec.slug, ok=False)
            log.exception("job %s failed", spec.name)
            raise CommandError(f"{spec.name} failed: {exc}") from exc
        run.outcome, run.detail, run.finished = "ok", detail, timezone.now()
        run.save(update_fields=["outcome", "detail", "finished"])
        pinged = ping(spec.slug, ok=True)
        self.stdout.write(f"{spec.name}: ok {detail}{' (pinged)' if pinged else ''}")

    def run_job(self, now: datetime, **options) -> dict:  # pragma: no cover - abstract
        raise NotImplementedError
