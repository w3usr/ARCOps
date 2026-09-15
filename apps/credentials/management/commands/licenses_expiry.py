"""licenses:expiry (FR-17): notices at 90 and 30 days before a license expires, and when it has."""

from apps.credentials.services import expiry_notices
from apps.ops.jobs import ScheduledCommand


class Command(ScheduledCommand):
    help = "Send license expiry notices due today (FR-17)."
    job_name = "licenses:expiry"

    def run_job(self, now, **options):
        return expiry_notices(now)
