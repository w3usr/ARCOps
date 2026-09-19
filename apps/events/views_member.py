"""Member-facing additions: role change (FR-111), waitlist (FR-57), the calendar feed (FR-59);
and for captains and officers the roster CSV (FR-85) and the cross-event view (FR-68)."""

from __future__ import annotations

import csv
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.models import User
from apps.ops.audit import record
from apps.ops.config import setting

from .models import Event, RoleCapacity, SignUp, Slot, Waitlist
from .services import notify, waitlist
from .services.eligibility import can_sign_up
from .services.roster import UTC, display_zone
from .services.slots import health
from .services.viability import evaluate

FEED_SALT = "ical-feed"


# --------------------------------------------------------------- role change (FR-111) ---


def _status_if_role(slot: Slot, su: SignUp, new_role: str):
    """What the slot would read if `su` held `new_role` instead."""
    signups = list(slot.signups.select_related("user").all())
    for s in signups:
        if s.pk == su.pk:
            s.role = new_role
    return evaluate(slot, signups)


@login_required
@require_POST
def signup_change_role(request, signup_id):
    su = get_object_or_404(SignUp, pk=signup_id, user=request.user)
    slot, event = su.slot, su.slot.event
    if event.state != Event.State.PUBLISHED:
        messages.error(request, "The roster is locked; ask a captain to change your role.")
        return redirect("event_detail", pk=event.pk)
    new_role = request.POST.get("role", "")
    if new_role == su.role:
        return redirect("slot_detail", pk=event.pk, slot_id=slot.pk)
    cap = RoleCapacity.objects.filter(slot=slot, role=new_role).first()
    if not cap or slot.signups.filter(role=new_role).count() >= cap.capacity:
        messages.error(request, f"No {new_role} seat is open in this slot.")
        return redirect("slot_detail", pk=event.pk, slot_id=slot.pk)
    ok, reason = can_sign_up(request.user, slot, new_role)
    if not ok:
        messages.error(request, f"You cannot take that role: {reason}.")
        return redirect("slot_detail", pk=event.pk, slot_id=slot.pk)
    before = evaluate(slot)
    after = _status_if_role(slot, su, new_role)
    breaks = (
        before.status in ("viable", "at_risk")
        and after.status in ("not_viable", "at_risk")
        and after.status != before.status
    )
    if breaks and request.POST.get("confirmed") != "yes":
        return render(
            request,
            "events/confirm_role.html",
            {"signup": su, "new_role": new_role, "broken": after},
        )
    old = su.role
    su.role = new_role
    su.save(update_fields=["role"])
    record(request.user, "signup.role_changed", su, before={"role": old}, after={"role": new_role})
    cutoff = int(setting("defaults.cancellation_cutoff_hours", 24))
    if slot.start - timezone.now() <= timedelta(hours=cutoff):
        for c in notify.captains_of(event) or notify.officers():
            notify.send(
                "captain.role_changed",
                c,
                "moved",
                {
                    "person": request.user.short_name_lettered,
                    "old_role": old,
                    "new_role": new_role,
                    "event": event,
                    "when": notify.when_text(slot),
                    "position": slot.position.name,
                    "cutoff": cutoff,
                    "broken": after.label.lower() if breaks else "",
                    "link": notify.slot_link(slot),
                },
            )
    waitlist.on_place_opened(slot, old)
    messages.success(request, f"You are now {new_role} in this slot.")
    return redirect("slot_detail", pk=event.pk, slot_id=slot.pk)


# ------------------------------------------------------------------- waitlist (FR-57) ---


@login_required
@require_POST
def waitlist_join(request, slot_id):
    slot = get_object_or_404(Slot, pk=slot_id, cancelled=False)
    event = slot.event
    if event.state != Event.State.PUBLISHED or slot.closed:
        raise Http404
    role = request.POST.get("role", "")
    if not RoleCapacity.objects.filter(slot=slot, role=role).exists():
        messages.error(request, "That role is not in this slot.")
        return redirect("slot_detail", pk=event.pk, slot_id=slot.pk)
    ok, reason = can_sign_up(request.user, slot, role)
    if not ok:
        messages.error(request, f"You cannot wait for that role: {reason}.")
        return redirect("slot_detail", pk=event.pk, slot_id=slot.pk)
    if waitlist.seats_open(slot, role):
        messages.info(request, f"A {role} seat is open; sign up directly.")
        return redirect("slot_detail", pk=event.pk, slot_id=slot.pk)
    waitlist.join(request.user, slot, role)
    messages.success(
        request,
        f"You are on the waitlist for {role}. If a place opens you will be offered it by message.",
    )
    return redirect("slot_detail", pk=event.pk, slot_id=slot.pk)


@login_required
@require_POST
def waitlist_withdraw(request, pk):
    entry = get_object_or_404(Waitlist, pk=pk, user=request.user)
    waitlist.withdraw(request.user, entry)
    messages.success(request, "Removed from the waitlist.")
    return redirect("slot_detail", pk=entry.slot.event.pk, slot_id=entry.slot.pk)


@login_required
def waitlist_accept(request, pk):
    entry = get_object_or_404(Waitlist, pk=pk, user=request.user)
    slot = entry.slot
    if request.method == "POST":
        su = waitlist.accept(request.user, entry)
        if su:
            messages.success(request, f"Signed up as {entry.role}. Thank you for waiting.")
        else:
            messages.error(request, "That offer has lapsed or the place is gone.")
        return redirect("slot_detail", pk=slot.event.pk, slot_id=slot.pk)
    return render(
        request,
        "events/waitlist_accept.html",
        {
            "entry": entry,
            "slot": slot,
            "open": waitlist.seats_open(slot, entry.role),
            "now": timezone.now(),
        },
    )


# ------------------------------------------------------------- calendar feed (FR-59) ---


def feed_token(user) -> str:
    """The member's own calendar address, which does not change when they look at it again.

    It was a signed string, and Django's signatures carry a timestamp, so the address on the
    page was different on every load: alarming to read, impossible to tell apart from a leak,
    and it left one live credential per page view. The key is on the account now, and replacing
    it is a deliberate act (FR-59).
    """
    if not user.calendar_key:
        from apps.accounts.models import new_calendar_key

        user.calendar_key = new_calendar_key()
        user.save(update_fields=["calendar_key"])
    return user.calendar_key


@login_required
@require_POST
def replace_feed(request):
    """Give this account a new calendar address, which stops the old one working.

    The other half of holding a key rather than a signature: an address that has been shared by
    accident can be replaced, and the calendars subscribed to the old one stop receiving.
    """
    from apps.accounts.models import new_calendar_key
    from apps.ops.audit import record

    request.user.calendar_key = new_calendar_key()
    request.user.save(update_fields=["calendar_key"])
    record(request.user, "calendar.address_replaced", request.user)
    messages.success(
        request,
        "Your calendar address is new. Subscribe your calendar to it again; anything subscribed "
        "to the old address stops receiving your slots.",
    )
    return redirect("my_schedule")


def _ics_dt(dt) -> str:
    return dt.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def _ics_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def ical_feed(request, token):
    """A per-member signed URL; works without signing in so a phone calendar can subscribe."""
    user = User.objects.filter(calendar_key=token, is_active=True).first()
    if user is None:
        # The addresses handed out before the key existed were signed strings; they keep working,
        # so a calendar somebody subscribed last week does not quietly stop (2026-09-19).
        try:
            data = signing.loads(token, salt=FEED_SALT)
        except signing.BadSignature as exc:
            raise Http404 from exc
        user = get_object_or_404(User, pk=data.get("u"), is_active=True)
    club = setting("club.short_name", "Club")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//ARCOps//EN",
        f"X-WR-CALNAME:{_ics_escape(club)} slots",
        "CALSCALE:GREGORIAN",
    ]
    signups = SignUp.objects.filter(user=user, slot__cancelled=False).select_related(
        "slot__position__location__event"
    )
    site = request.build_absolute_uri("/").rstrip("/")
    for su in signups:
        slot, event = su.slot, su.slot.event
        if event.state == Event.State.CANCELLED:
            continue
        lines += [
            "BEGIN:VEVENT",
            # The UID identifies this entry to every calendar that has already subscribed; it is not
            # the product's name and does not follow its spelling.
            f"UID:signup-{su.pk}@arcops",
            f"DTSTAMP:{_ics_dt(su.created)}",
            f"DTSTART:{_ics_dt(slot.start)}",
            f"DTEND:{_ics_dt(slot.end)}",
            f"SUMMARY:{_ics_escape(f'{event.title}: {slot.position.name} as {su.role}')}",
            f"LOCATION:{_ics_escape(slot.position.location.name)}",
            f"URL:{site}/events/{event.pk}/slot/{slot.pk}/",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    body = "\r\n".join(lines) + "\r\n"
    resp = HttpResponse(body, content_type="text/calendar; charset=utf-8")
    resp["Content-Disposition"] = 'inline; filename="slots.ics"'
    return resp


# ------------------------------------------------------------------ roster CSV (FR-85) ---


@login_required
def roster_csv(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if not request.user.can_captain(event):
        raise Http404
    zone = display_zone(event)
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="roster-{event.pk}.csv"'
    w = csv.writer(resp)
    w.writerow(
        [
            "start_utc",
            "end_utc",
            "start_local",
            "end_local",
            "location",
            "position",
            "kind",
            "status",
            "name",
            "callsign",
            "class",
            "role",
            "state",
            "note",
        ]
    )
    slots = (
        Slot.objects.filter(position__location__event=event, cancelled=False)
        .select_related("position__location")
        .prefetch_related("signups__user", "signups__user__license", "signups__responsible_adults")
        .order_by("start", "position__location__order", "position__order")
    )
    for s in slots:
        signups = list(s.signups.all())
        status = evaluate(s, signups)
        base = [
            _ics_dt(s.start),
            _ics_dt(s.end),
            s.start.astimezone(zone).strftime("%Y-%m-%d %H:%M"),
            s.end.astimezone(zone).strftime("%Y-%m-%d %H:%M"),
            s.position.location.name,
            s.position.name,
            s.kind,
            status.label,
        ]
        if not signups:
            w.writerow(base + ["", "", "", "", "", ""])
        for su in signups:
            state = (
                "checked in"
                if su.checked_in_at
                else ("confirmed" if su.confirmed_at else "signed up")
            )
            w.writerow(
                base
                + [
                    su.user.full_name,
                    su.user.callsign,
                    su.user.license_letter,
                    su.role,
                    state,
                    su.note,
                ]
            )
    return resp


# -------------------------------------------------------------- cross-event view (FR-68) ---


@login_required
def health_overview(request):
    if not request.user.may("manage_events"):
        raise Http404
    now = timezone.now()
    weeks = int(request.GET.get("weeks") or setting("defaults.health_overview_weeks", 6))
    until = now + timedelta(weeks=weeks)
    rows = []
    for e in Event.objects.filter(
        state__in=[Event.State.PUBLISHED, Event.State.LOCKED], display_only=False
    ).prefetch_related("periods"):
        start, end = e.starts_at(), e.ends_at()
        if not start or start > until or (end and end < now):
            continue
        h = health(e)
        unconfirmed = SignUp.objects.filter(
            slot__position__location__event=e,
            slot__start__lte=now + timedelta(hours=48),
            slot__start__gte=now,
            confirmed_at__isnull=True,
            checked_in_at__isnull=True,
        ).count()
        rows.append(
            {"event": e, "start": start, "end": end, "health": h, "unconfirmed_48h": unconfirmed}
        )
    rows.sort(key=lambda r: r["start"])
    return render(request, "events/health_overview.html", {"rows": rows, "weeks": weeks})


@login_required
def participation_report(request, pk):
    """FR-86: hours scheduled, covered, and viable; people scheduled and checked in; first-timers."""
    from .services.participation import participation

    event = get_object_or_404(Event, pk=pk)
    if not request.user.can_captain(event):
        raise Http404
    report = participation(event)
    if request.GET.get("format") == "csv":
        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = f'attachment; filename="participation-{event.pk}.csv"'
        w = csv.writer(resp)
        w.writerow(
            [
                "period_start_utc",
                "period_end_utc",
                "slots",
                "hours_scheduled",
                "hours_covered",
                "hours_viable",
                "people_scheduled",
                "people_checked_in",
            ]
        )
        for r in report["periods"]:
            w.writerow(
                [
                    r["period"].start.isoformat(),
                    r["period"].end.isoformat(),
                    r["slots"],
                    r["hours_scheduled"],
                    r["hours_covered"],
                    r["hours_viable"],
                    r["people_scheduled"],
                    r["people_checked_in"],
                ]
            )
        t = report["total"]
        w.writerow(
            [
                "total",
                "",
                t["slots"],
                t["hours_scheduled"],
                t["hours_covered"],
                t["hours_viable"],
                t["people_scheduled"],
                t["people_checked_in"],
            ]
        )
        w.writerow(["first_time_participants", t["first_timers"]])
        return resp
    return render(request, "events/participation.html", {"report": report, "event": event})
