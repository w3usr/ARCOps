"""jobs:stale: the watchdog (TR-11, FR-93). Lists every registered job whose last success is
older than its period plus grace. It records the list on its own JobRun and warns in the log;
the stale jobs' own healthchecks.io checks are late by then, which is where the alert comes
from. This command's check going late means the timers themselves have stopped."""

import logging

from apps.ops.jobs import ScheduledCommand, stale_jobs

log = logging.getLogger(__name__)


class Command(ScheduledCommand):
    help = "Report registered jobs that have not succeeded within their period plus grace."
    job_name = "jobs:stale"

    def run_job(self, now, **options):
        stale = [n for n in stale_jobs(now) if n != self.job_name]
        if stale:
            log.warning("stale jobs: %s", ", ".join(stale))
        return {"stale": stale}
