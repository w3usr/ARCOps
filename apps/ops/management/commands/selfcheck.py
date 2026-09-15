"""selfcheck: the five-minute self-check (TR-33). Runs the /healthz logic in-process and fails
if the database is unreachable, so the healthchecks.io check for it goes late when the
application or its database is down."""

from django.test import RequestFactory

from apps.ops.jobs import ScheduledCommand
from apps.ops.views import healthz


class Command(ScheduledCommand):
    help = "Run the /healthz check in-process and record the result (TR-33)."
    job_name = "selfcheck"

    def run_job(self, now, **options):
        response = healthz(RequestFactory().get("/healthz"))
        if response.status_code != 200:
            raise RuntimeError(
                f"/healthz returned {response.status_code}: {response.content[:200]!r}"
            )
        import json

        body = json.loads(response.content)
        return {"db": body.get("db"), "outbox_failed_24h": body.get("outbox_failed_24h")}
