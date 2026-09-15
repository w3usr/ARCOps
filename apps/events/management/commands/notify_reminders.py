"""notify:reminders (FR-72): every 15 minutes, the reminder for each sign-up entering its window."""

from apps.events.services.notify import send_reminders
from apps.ops.jobs import ScheduledCommand


class Command(ScheduledCommand):
    help = "Send slot reminders that have come due (FR-72)."
    job_name = "notify:reminders"

    def run_job(self, now, **options):
        return send_reminders(now)
