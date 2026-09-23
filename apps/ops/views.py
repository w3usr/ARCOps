"""Health check (TR-33) and the dashboard."""

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
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
    if not request.user.may("view_job_status"):
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
    if request.user.may("view_member_records"):
        from apps.accounts.entry import pending_review

        pending = list(pending_review()[:20])
    # FR-108: unread messages that would otherwise have been a warning email. What the banner
    # needs from them is whether there are any and what they are about — not the messages
    # themselves. It used to show the first five and count that slice, so a reader with eight
    # unread was told there were five, and the sentence then listed every subject in a row
    # (the advisor, 2026-09-22: "'5 unread notices' is the wrong number … should just correctly
    # summarize the number of messages/approvals that need review, and should not list all of
    # them in a single sentence"). It reports the counts the sidebar badges carry instead, so
    # the reader is never given a third number to reconcile.
    unread_notices = Outbox.objects.filter(
        user=request.user, read_at__isnull=True, category__in=BANNER
    )
    notice_categories = set(unread_notices.values_list("category", flat=True).distinct())
    # A notice that something needs doing should offer the page where it is done, rather than
    # the list of notices (NAF, 2026-09-20: "It would be better to link to me to the Approvals
    # page than to the Messages page"). Only where every unread notice points the same way; a
    # mixed handful goes to Messages, which is the one place that holds them all.
    banner_action = None
    if request.user.may("approve_agreements") and notice_categories == {"agreement"}:
        from apps.credentials.models import SignedAgreement

        if SignedAgreement.objects.filter(state=SignedAgreement.State.SIGNED).exists():
            banner_action = {"url": reverse("approvals"), "label": "Go to Approvals"}
    return render(
        request,
        "ops/dashboard.html",
        {
            "my_signups": my_signups,
            "checkin_ready": checkin_ready,
            "upcoming_events": upcoming_events,
            "pending_review": pending,
            "has_notices": bool(notice_categories),
            "banner_action": banner_action,
            "delivery_mode": str(setting("defaults.email_delivery", "off")).lower(),
        },
    )


def _png_size(url: str) -> str:
    """ "WIDTHxHEIGHT" from a PNG's header, or "" when it cannot be read.

    The header is the first 24 bytes: an 8-byte signature, the IHDR length and name, then the
    width and height as big-endian 32-bit integers. Reading them beats trusting a file name.
    """
    import struct
    from pathlib import Path

    from django.conf import settings as dj
    from django.contrib.staticfiles import finders

    name = url.split("/static/", 1)[-1] if "/static/" in url else ""
    path = finders.find(name) if name else None
    if path is None:
        candidate = Path(str(getattr(dj, "STATIC_ROOT", "") or "")) / name
        path = str(candidate) if name and candidate.exists() else None
    if path is None and url.startswith("/") and getattr(dj, "MEDIA_ROOT", ""):
        candidate = Path(dj.MEDIA_ROOT) / url.split("/media/", 1)[-1]
        path = str(candidate) if candidate.exists() else None
    if path is None:
        return ""
    try:
        with open(path, "rb") as fh:
            head = fh.read(24)
        if head[:8] != b"\x89PNG\r\n\x1a\n":
            return ""
        width, height = struct.unpack(">II", head[16:24])
    except (OSError, struct.error):
        return ""
    return f"{width}x{height}"


def _icon_entry(url: str, purpose: str) -> dict:
    entry = {"src": url, "purpose": purpose}
    if ".svg" in url:
        entry["sizes"], entry["type"] = "any", "image/svg+xml"
    else:
        # The real pixel size, read from the file. A browser decides whether a site can be
        # installed, and which icon to use, from the sizes a manifest declares; "any" means
        # "scalable", which a PNG is not, so the club's 512px logo was being passed over.
        entry["sizes"] = _png_size(url) or "192x192"
        entry["type"] = "image/png"
    return entry


def manifest(request):
    """The web app manifest (FR-96), rendered from the club's configuration so an installed
    copy and its notification prompts carry this installation's name, never the product's. A
    member of two clubs running the software sees two names."""
    from .config import branding

    b = branding()
    short = setting("club.short_name", "Club")
    host = request.get_host()
    icons = []
    seen: set[str] = set()
    for key in ("apple_touch_icon", "logo"):
        url = b.get(key)  # already a URL: static (hashed) or an uploaded file (FR-89)
        if not url or url in seen:
            continue  # the shipped configuration points both at one file; say it once
        seen.add(url)
        icons.append(_icon_entry(url, "any"))
    # A phone that installs the site puts the icon under its own mask. An icon that does not
    # say it can be masked is treated as artwork of unknown shape: the launcher shrinks it and
    # sets it on a white tile, which is where the margin around the club's logo came from (the
    # advisor, 2026-09-20). A maskable icon is drawn to the edge, so the club supplies one with
    # its mark inside the safe area and the rest filled.
    masked = b.get("maskable_icon")
    if masked:
        icons.append(_icon_entry(masked, "maskable"))
    body = {
        "name": f"{short} Operations ({host})",
        "short_name": short[:12],
        "description": f"{setting('club.name', short)}: events, rosters, and sign-ups",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": b.get("accent") or "#1f3a5f",
        "icons": icons,
    }
    return JsonResponse(body, content_type="application/manifest+json")


def service_worker(request):
    """FR-96: the service worker, served at the site root so its scope is the whole site and
    with no-cache headers so a new version reaches browsers on their next visit. Under /static/
    it sat behind a 30-day immutable cache (found 2026-09-15: the live copy was two versions
    old), and a service worker's URL must not change, so it cannot carry a content hash."""
    from django.contrib.staticfiles import finders
    from django.http import Http404, HttpResponse

    path = finders.find("sw.js")
    if not path:
        raise Http404
    with open(path, encoding="utf-8") as fh:
        body = fh.read()
    resp = HttpResponse(body, content_type="application/javascript; charset=utf-8")
    resp["Cache-Control"] = "no-cache, max-age=0, must-revalidate"
    resp["Service-Worker-Allowed"] = "/"
    return resp


def branding_file(request, name):
    """An image uploaded from Settings (FR-89): served from MEDIA_ROOT/branding/ with a day's
    cache; the URL carries the file's mtime so a replacement is fetched at once."""
    import mimetypes
    from pathlib import Path

    from django.conf import settings as dj
    from django.http import FileResponse, Http404

    safe = Path(name).name
    path = dj.MEDIA_ROOT / "branding" / safe
    if safe != name or not path.is_file():
        raise Http404
    ctype = mimetypes.guess_type(safe)[0] or "application/octet-stream"
    resp = FileResponse(path.open("rb"), content_type=ctype)
    resp["Cache-Control"] = "public, max-age=86400"
    return resp
