"""openings:announce (FR-80, FR-57): announce role openings that have fired; lapse waitlist offers."""

from apps.events.services.lifecycle import announce_openings
from apps.events.services.waitlist import expire_offers
from apps.ops.jobs import ScheduledCommand


class Command(ScheduledCommand):
    help = (
        "Send opening announcements that are due and pass lapsed waitlist offers on (FR-80, FR-57)."
    )
    job_name = "openings:announce"

    def run_job(self, now, **options):
        return {"openings": announce_openings(now), "offers_lapsed": expire_offers(now)}
