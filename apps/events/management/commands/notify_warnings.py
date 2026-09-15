"""notify:warnings (FR-73, FR-110, FR-113): every 15 minutes, at-risk warnings and no-show notices."""

from apps.events.services.notify import send_warnings
from apps.ops.jobs import ScheduledCommand


class Command(ScheduledCommand):
    help = "Warn captains and slot-mates about slots at risk; notice of confirmed no-shows (FR-73, FR-113)."
    job_name = "notify:warnings"

    def run_job(self, now, **options):
        return send_warnings(now)
