"""Health check (TR-33) and the dashboard."""

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from apps.comms.models import Outbox
from apps.events.models import Event, SignUp
from apps.events.services.viability import checkin_window_open

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
    return JsonResponse(body, status=status)


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
    return render(
        request,
        "ops/dashboard.html",
        {
            "my_signups": my_signups,
            "checkin_ready": checkin_ready,
            "upcoming_events": upcoming_events,
        },
    )
