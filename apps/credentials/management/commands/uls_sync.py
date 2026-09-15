"""uls:sync (FR-14, TR-13): the FCC ULS bulk import into the local license table."""

from apps.credentials.uls import run
from apps.ops.jobs import ScheduledCommand


class Command(ScheduledCommand):
    help = "Import the FCC ULS amateur file (weekly complete or daily transactions) into the local table."
    job_name = "uls:sync"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument("--full", action="store_true", help="fetch the complete weekly file")
        parser.add_argument("--file", help="import this local archive instead of downloading")

    def run_job(self, now, **options):
        return run(now, full=True if options.get("full") else None, file=options.get("file"))
