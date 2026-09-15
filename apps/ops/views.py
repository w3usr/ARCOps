"""Health check (TR-33) and the dashboard."""

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from apps.comms.categories import BANNER
from apps.comms.models import Outbox
from apps.events.models import Event, SignUp
from apps.events.services.viability import checkin_window_open

from . import jobs
from .config import setting
from .models import JobRun


def healthz(request):
    """Database reachability, the last ULS sync, and outbox failures in the last day."""
    status = 200
    body = {"version": settings.APP_VERSION, "db": "ok"}
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
    except Exception as exc:  # noqa: BLE001
        body["db"] = f"error: {exc.__class__.__name__}"
        status = 503
    last = JobRun.objects.filter(name="uls:sync", outcome="ok").order_by("-finished").first()
    body["last_uls_sync"] = last.finished.isoformat() if last and last.finished else None
    since = timezone.now() - timezone.timedelta(hours=24)
    body["outbox_failed_24h"] = Outbox.objects.filter(state="failed", created__gte=since).count()
    body["email_delivery"] = setting("defaults.email_delivery", "off")
    body["jobs"] = {
        name: (run.finished.isoformat() if run and run.finished else None)
        for name, run in ((n, jobs.last_ok(n)) for n in jobs.JOBS)
    }
    body["stale_jobs"] = jobs.stale_jobs()
    return JsonResponse(body, status=status)


@login_required
def status(request):
    """FR-93: every registered job's last run and outcome, and mail health."""
    if not request.user.is_sysadmin:
        from django.http import Http404

        raise Http404
    since = timezone.now() - timezone.timedelta(hours=24)
    recent = Outbox.objects.filter(created__gte=since)
    last_sent = Outbox.objects.filter(state="sent").order_by("-sent_at").first()
    return render(
        request,
        "ops/status.html",
        {
            "rows": jobs.status_rows(),
            "mail": {
                "mode": str(setting("defaults.email_delivery", "off")).lower(),
                "sent_24h": recent.filter(state="sent").count(),
                "failed_24h": recent.filter(state="failed").count(),
                "not_sent_24h": recent.filter(state="not_sent").count(),
                "last_sent": last_sent.sent_at if last_sent else None,
            },
        },
    )


@login_required
def dashboard(request):
    now = timezone.now()
    my_signups = (
        SignUp.objects.filter(user=request.user, slot__end__gte=now, slot__cancelled=False)
        .select_related(
            "slot", "slot__position", "slot__position__location", "slot__position__location__event"
        )
        .order_by("slot__start")[:10]
    )
    checkin_ready = [
        s for s in my_signups if checkin_window_open(s.slot, now) and not s.checked_in_at
    ]
    upcoming_events = Event.objects.filter(state__in=["published", "locked"]).order_by("id")[:10]
    upcoming_events = [e for e in upcoming_events if e.ends_at() and e.ends_at() >= now]
    pending = []
    if request.user.is_officer:
        from apps.accounts.entry import pending_review

        pending = list(pending_review()[:20])
    # FR-108: unread messages that would otherwise have been a warning email.
    banner_messages = list(
        Outbox.objects.filter(user=request.user, read_at__isnull=True, category__in=BANNER)[:5]
    )
    return render(
        request,
        "ops/dashboard.html",
        {
            "my_signups": my_signups,
            "checkin_ready": checkin_ready,
            "upcoming_events": upcoming_events,
            "pending_review": pending,
            "banner_messages": banner_messages,
            "delivery_mode": str(setting("defaults.email_delivery", "off")).lower(),
        },
    )
