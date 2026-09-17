"""Event lifecycle (FR-44), opening announcements (FR-80), and the publish announcement."""

from __future__ import annotations

from datetime import datetime

from django.conf import settings as dj
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.comms.services import send
from apps.ops.audit import record

from ..models import Event, Opening, Slot


def _site() -> str:
    return getattr(dj, "SITE_URL", "") or ""


def set_state(actor, event: Event, what: str) -> str:
    """lock | unlock | complete. Returns a message for the page; raises ValueError if the move
    is not allowed from the current state."""
    st = Event.State
    if what == "lock" and event.state == st.PUBLISHED:
        event.state = st.LOCKED
        event.save(update_fields=["state"])
        record(actor, "event.locked", event)
        return "Locked. Members can see the roster; changes to sign-ups now go through you."
    if what == "unlock" and event.state == st.LOCKED:
        event.state = st.PUBLISHED
        event.save(update_fields=["state"])
        record(actor, "event.unlocked", event)
        return "Unlocked. Members can change their sign-ups again."
    if what == "complete" and event.state in (st.PUBLISHED, st.LOCKED):
        event.state = st.COMPLETED
        event.completed_at = timezone.now()
        event.save(update_fields=["state", "completed_at"])
        record(actor, "event.completed", event)
        return "Marked completed."
    raise ValueError(f"cannot {what} an event that is {event.get_state_display().lower()}")


def complete_ended(now: datetime | None = None) -> int:
    """FR-44: automatic completion once the last slot has ended."""
    now = now or timezone.now()
    n = 0
    for e in Event.objects.filter(
        state__in=[Event.State.PUBLISHED, Event.State.LOCKED], display_only=False
    ):
        last = (
            Slot.objects.filter(position__location__event=e, cancelled=False)
            .order_by("-end")
            .first()
        )
        end = last.end if last else e.ends_at()
        if end and end < now:
            e.state = Event.State.COMPLETED
            e.completed_at = now
            e.save(update_fields=["state", "completed_at"])
            record(None, "event.completed", e, after={"automatic": True})
            n += 1
    return n


def announce_published(actor, event: Event) -> int:
    """FR-44: the optional announcement when an event becomes visible."""
    from .notify import when_text  # noqa: F401  (kept for parity; span text built below)
    from .roster import display_zone, zone_label

    start, end = event.starts_at(), event.ends_at()
    when = ""
    if start and end:
        z = display_zone(event)
        when = f"{start.astimezone(z):%a %-d %b %H:%M} to {end.astimezone(z):%a %-d %b %H:%M} {zone_label(start, z)}"
    link = _site() + reverse("event_detail", args=[event.pk])
    members = User.objects.filter(
        is_active=True,
        groups__permissions__codename="view_directory",
    )
    n = 0
    for u in members:
        send("event.published", u, "announcement", {"event": event, "when": when, "link": link})
        n += 1
    record(actor, "event.announced", event, after={"recipients": n})
    return n


def announce_openings(now: datetime | None = None) -> int:
    """FR-80: when an opening with `announce` fires, tell the newly eligible audience once."""
    now = now or timezone.now()
    n = 0
    due = Opening.objects.filter(
        announce=True, announced_at__isnull=True, opens_at__lte=now
    ).select_related("event")
    for o in due:
        if o.event.state not in (Event.State.PUBLISHED, Event.State.LOCKED):
            continue
        audience = User.objects.filter(
            is_active=True,
            groups__permissions__codename="view_directory",
        )
        if o.categories:
            audience = audience.filter(category__in=o.categories)
        link = _site() + reverse("event_detail", args=[o.event.pk])
        for u in audience:
            send(
                "opening.announced", u, "opening", {"role": o.role, "event": o.event, "link": link}
            )
        o.announced_at = now
        o.save(update_fields=["announced_at"])
        n += 1
    return n
