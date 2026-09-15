"""FR-57: waitlists. A member joins the list for a full role; when a place opens, the first
pending entry is offered it by message and has a window to accept before it passes on."""

from __future__ import annotations

from datetime import datetime, timedelta

from django.conf import settings as dj
from django.urls import reverse
from django.utils import timezone

from apps.comms.services import send
from apps.ops.audit import record
from apps.ops.config import setting

from ..models import RoleCapacity, SignUp, Slot, Waitlist


def offer_hours() -> int:
    return int(setting("defaults.waitlist_offer_hours", 12))


def seats_open(slot: Slot, role: str) -> bool:
    cap = RoleCapacity.objects.filter(slot=slot, role=role).first()
    return bool(cap) and slot.signups.filter(role=role).count() < cap.capacity


def join(user, slot: Slot, role: str) -> Waitlist:
    entry, _ = Waitlist.objects.get_or_create(
        slot=slot, user=user, role=role, defaults={"state": Waitlist.State.PENDING}
    )
    if entry.state in (Waitlist.State.WITHDRAWN, Waitlist.State.EXPIRED):
        entry.state = Waitlist.State.PENDING
        entry.save(update_fields=["state"])
    record(user, "waitlist.joined", entry, after={"role": role})
    return entry


def withdraw(user, entry: Waitlist) -> None:
    entry.state = Waitlist.State.WITHDRAWN
    entry.save(update_fields=["state"])
    record(user, "waitlist.withdrawn", entry)


def offer_next(slot: Slot, role: str, now: datetime | None = None) -> Waitlist | None:
    """Called when a place in `role` opens. Offers it to the first pending entry."""
    now = now or timezone.now()
    if not seats_open(slot, role):
        return None
    if Waitlist.objects.filter(slot=slot, role=role, state=Waitlist.State.OFFERED).exists():
        return None  # an offer is already out; the expiry pass moves it on
    entry = Waitlist.objects.filter(slot=slot, role=role, state=Waitlist.State.PENDING).first()
    if entry is None:
        return None
    entry.state = Waitlist.State.OFFERED
    entry.offered_at = now
    entry.offer_expires_at = now + timedelta(hours=offer_hours())
    entry.save(update_fields=["state", "offered_at", "offer_expires_at"])
    from .notify import when_text

    site = getattr(dj, "SITE_URL", "") or ""
    send(
        "waitlist.offer",
        entry.user,
        "moved",
        {
            "event": slot.event,
            "when": when_text(slot),
            "position": slot.position.name,
            "role": role,
            "expires": entry.offer_expires_at,
            "link": site + reverse("waitlist_accept", args=[entry.pk]),
        },
    )
    return entry


def accept(user, entry: Waitlist) -> SignUp | None:
    if entry.user_id != user.pk or entry.state != Waitlist.State.OFFERED:
        return None
    if entry.offer_expires_at and entry.offer_expires_at < timezone.now():
        return None
    if not seats_open(entry.slot, entry.role):
        return None
    su, _ = SignUp.objects.get_or_create(
        slot=entry.slot, user=user, defaults={"role": entry.role, "note": ""}
    )
    entry.state = Waitlist.State.ACCEPTED
    entry.save(update_fields=["state"])
    record(user, "signup.created", su, after={"role": entry.role, "waitlist": entry.pk})
    return su


def expire_offers(now: datetime | None = None) -> int:
    """Offers past their window lapse and the place is offered to the next in line."""
    now = now or timezone.now()
    lapsed = list(
        Waitlist.objects.filter(
            state=Waitlist.State.OFFERED, offer_expires_at__lt=now
        ).select_related("slot")
    )
    for e in lapsed:
        e.state = Waitlist.State.EXPIRED
        e.save(update_fields=["state"])
        offer_next(e.slot, e.role, now)
    return len(lapsed)


def on_place_opened(slot: Slot, role: str) -> None:
    """Hook for the cancel and remove paths."""
    try:
        offer_next(slot, role)
    except Exception:  # noqa: BLE001 - a waitlist hiccup must not break a cancellation
        import logging

        logging.getLogger(__name__).exception("waitlist offer failed")
