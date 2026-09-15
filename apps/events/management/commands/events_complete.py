"""events:complete (FR-44): a published or locked event whose last slot has ended is completed."""

from apps.events.services.lifecycle import complete_ended
from apps.ops.jobs import ScheduledCommand


class Command(ScheduledCommand):
    help = "Mark events completed once their last slot has ended (FR-44)."
    job_name = "events:complete"

    def run_job(self, now, **options):
        return {"completed": complete_ended(now)}
