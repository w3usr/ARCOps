"""retention:apply (§4.3, TR-28): the daily retention pass."""

from apps.ops.jobs import ScheduledCommand
from apps.ops.retention import apply


class Command(ScheduledCommand):
    help = "Apply the retention schedule of REQUIREMENTS §4.3 (TR-28)."
    job_name = "retention:apply"

    def run_job(self, now, **options):
        return apply(now)
