"""agreements:expiry (FR-28, FR-30): expire what is due, send the 30-day and day-of notices, and
the approvers' summaries."""

from apps.credentials.services import agreement_expiry_run
from apps.ops.jobs import ScheduledCommand


class Command(ScheduledCommand):
    help = "Expire due agreement approvals and send the expiry notices and summaries (FR-28)."
    job_name = "agreements:expiry"

    def run_job(self, now, **options):
        return agreement_expiry_run(now)
