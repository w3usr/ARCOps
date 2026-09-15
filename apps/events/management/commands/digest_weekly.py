"""digest:weekly (FR-79): what is coming up, what still needs people, and your own slots."""

from apps.events.services.notify import send_digest
from apps.ops.jobs import ScheduledCommand


class Command(ScheduledCommand):
    help = "Send the weekly digest to every member (FR-79)."
    job_name = "digest:weekly"

    def run_job(self, now, **options):
        return send_digest(now)
