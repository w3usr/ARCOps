"""Event lifecycle (FR-44), opening announcements (FR-80), and the publish announcement."""

from __future__ import annotations

from datetime import datetime

from django.conf import settings as dj
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.comms.services import send
from apps.ops.audit import record
from apps.ops.templatetags.labels import role_label

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
        # The people with slots still to come are told their slots will not run; otherwise they
        # find out by turning up (#258; SK, 2026-11-12). Reminders stop with the state.
        by_user: dict[int, list] = {}
        for su in event.signups_ahead().select_related("user"):
            by_user.setdefault(su.user_id, []).append(su)
        for sus in by_user.values():
            send(
                "event.completed_early",
                sus[0].user,
                "cancellation",
                {"actor": actor.full_name, "event": event, "count": len(sus)},
            )
        record(actor, "event.completed", event, after={"people_told": len(by_user)})
        if by_user:
            n = len(by_user)
            return f"Marked completed. {n} {'person' if n == 1 else 'people'} with slots still to come {'was' if n == 1 else 'were'} told."
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
    from .notify import mail_when

    start, end = event.starts_at(), event.ends_at()
    when = mail_when(start, end, event, " to ") if start and end else ""
    link = _site() + reverse("event_detail", args=[event.pk])
    members = User.objects.filter(
        is_active=True,
        groups__permissions__codename="view_directory",
    )
    n = 0
    for u in members:
        # Its own category, so that turning off an officer's announcements does not silently
        # turn off the club's calendar as well (the unsubscribe page promised as much).
        send("event.published", u, "event_published", {"event": event, "when": when, "link": link})
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
        # Claimed before anyone is told, in one conditional update, so a second run at the same
        # moment (the timer and a manage.py call) finds it taken and sends nothing (#165).
        # ponytail: at most once; a run that dies mid-send leaves the rest untold, not told twice.
        if not Opening.objects.filter(pk=o.pk, announced_at__isnull=True).update(announced_at=now):
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
                "opening.announced",
                u,
                "opening",
                {"role": role_label(o.role), "event": o.event, "link": link},
            )
        n += 1
    return n
