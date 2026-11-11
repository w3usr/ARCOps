"""Re-time, split or merge a slot that has people in it (FR-46, #156; SK, 2026-11-11).

Re-timed, the people stay, are told the old and the new time, and confirm again. Split, each
person is in both halves, since they signed up for the whole of it, and nobody is told. Merged,
which only back-to-back slots of one position can be, everyone from both is in the one slot.
None of it once a slot has started or has a check-in or a no-show, so attendance stays true.
"""

from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.comms.services import send
from apps.ops.audit import record

from ..models import Event, ResponsibleAdult, RoleCapacity, SignUp, Slot, Waitlist
from .notify import slot_link, when_text

SHORTEST = timedelta(minutes=15)  # as the generator's and Add a slot's
WAITING = (Waitlist.State.PENDING, Waitlist.State.OFFERED)


def frozen(slot: Slot, now=None) -> str:
    """Why this slot's time can no longer change, as a sentence; "" when it can."""
    now = now or timezone.now()
    if slot.event.state in (Event.State.COMPLETED, Event.State.CANCELLED):
        return "The event is over, so this slot keeps its time."
    if slot.start <= now:
        return "This slot has started, so it keeps its time."
    if (
        slot.signups.exclude(checked_in_at=None).exists()
        or slot.signups.filter(no_show=True).exists()
    ):
        return "Someone has been checked in to this slot, so it keeps its time."
    return ""


def misfit(slot: Slot, start, end) -> str:
    """Why `slot` cannot run from `start` to `end`; "" when it can. Add a slot's two rules: an
    operating slot sits inside an operating period (FR-38), and a position has one slot at a time."""
    if end - start < SHORTEST:
        return "A slot is at least 15 minutes long."
    if (
        slot.kind == "operating"
        and not slot.event.periods.filter(start__lte=start, end__gte=end).exists()
    ):
        return "An operating slot has to fit inside an operating period."
    clash = (
        Slot.objects.filter(position=slot.position, cancelled=False, start__lt=end, end__gt=start)
        .exclude(pk=slot.pk)
        .first()
    )
    if clash:
        return (
            f"{slot.position} already has a slot from {clash.start:%a %d %b %H:%M} to "
            f"{clash.end:%H:%M} UTC."
        )
    return ""


def _tell(actor, signups, slot, was: str) -> int:
    """Their slot's time changed: the confirmation and the reminder were for the old one, so
    both start again, and each person is told the old time and the new."""
    for su in signups:
        su.confirmed_at = su.reminder_sent_at = None
        su.save(update_fields=["confirmed_at", "reminder_sent_at"])
        send(
            "slot.changed",
            su.user,
            "cancellation",  # the category a slot's other changes arrive in
            {
                "actor": actor.full_name,
                "event": slot.event,
                "was": was,
                "when": when_text(slot),
                "position": slot.position.name,
                "link": slot_link(slot),
            },
        )
    return len(signups)


@transaction.atomic
def retime(actor, slot: Slot, start, end) -> int:
    """Move `slot`; the caller has checked frozen() and misfit(). Returns how many were told."""
    was, before = when_text(slot), (slot.start, slot.end)
    slot.start, slot.end = start, end
    slot.save(update_fields=["start", "end"])
    told = _tell(actor, list(slot.signups.select_related("user")), slot, was)
    record(
        actor,
        "slot.retimed",
        slot,
        before={"start": before[0].isoformat(), "end": before[1].isoformat()},
        after={"start": start.isoformat(), "end": end.isoformat(), "people told": told},
    )
    return told


@transaction.atomic
def split(actor, slot: Slot, at) -> Slot:
    """Cut `slot` at `at`: it keeps the first part, and a new slot takes the second with the same
    seats, sign-up rules, people and waitlist. Nobody's hours change, so nobody is told."""
    second = Slot.objects.create(
        position=slot.position,
        start=at,
        end=slot.end,
        kind=slot.kind,
        closed=slot.closed,
        control_operator=slot.control_operator,
    )
    RoleCapacity.objects.bulk_create(
        RoleCapacity(slot=second, role=c.role, capacity=c.capacity) for c in slot.capacities.all()
    )
    for rule in slot.eligibility_rules.all():
        rule.pk, rule.slot = None, second
        rule.save()
    for su in slot.signups.all():
        adults = list(su.responsible_adults.all())
        copy = SignUp.objects.create(
            slot=second,
            user=su.user,
            role=su.role,
            note=su.note,
            note_at=su.note_at,
            confirmed_at=su.confirmed_at,
            reminder_sent_at=su.reminder_sent_at,
        )
        ResponsibleAdult.objects.bulk_create(
            ResponsibleAdult(
                signup=copy, name=a.name, email=a.email, phone=a.phone, member=a.member
            )
            for a in adults
        )
    Waitlist.objects.bulk_create(
        Waitlist(slot=second, user=w.user, role=w.role)
        for w in slot.waitlist.filter(state__in=WAITING)
    )
    was_end, slot.end = slot.end, at
    slot.save(update_fields=["end"])
    record(
        actor,
        "slot.split",
        slot,
        before={"end": was_end.isoformat()},
        after={
            "end": at.isoformat(),
            "second slot": second.pk,
            "people in both": slot.signups.count(),
        },
    )
    return second


@transaction.atomic
def merge(actor, first: Slot, second: Slot) -> int:
    """`second` follows straight on from `first`: `first` grows to its end and takes its people.
    Someone in both becomes one sign-up, in the role they held first. Each role keeps the larger
    seat count, raised to hold everyone (addendum A3). People whose hours grew are told and confirm
    again; someone who held both keeps a confirmation only if they had confirmed both. `second`
    is canceled, as a slot taken off the roster is. Returns how many were told."""
    was = {s.pk: when_text(s) for s in (first, second)}
    mine = {su.user_id: su for su in first.signups.all()}
    theirs = list(second.signups.select_related("user"))
    in_both = {su.user_id for su in theirs} & set(mine)
    grew = [(su, was[first.pk]) for uid, su in mine.items() if uid not in in_both]
    for su in theirs:
        held = mine.get(su.user_id)
        if held:  # in both: the hours they hold are the same as before
            if held.confirmed_at and not su.confirmed_at:
                held.confirmed_at = None
                held.save(update_fields=["confirmed_at"])
            su.delete()
        else:
            su.slot = first
            su.save(update_fields=["slot"])
            grew.append((su, was[second.pk]))
    seats = {c.role: c.capacity for c in first.capacities.all()}
    for c in second.capacities.all():
        seats[c.role] = max(seats.get(c.role, 0), c.capacity)
    first.end = second.end
    first.save(update_fields=["end"])
    for role in set(seats) | set(first.signups.values_list("role", flat=True)):
        need = max(seats.get(role, 0), first.signups.filter(role=role).count())
        RoleCapacity.objects.update_or_create(slot=first, role=role, defaults={"capacity": need})
    here = set(first.signups.values_list("user_id", flat=True))
    for w in second.waitlist.filter(state__in=WAITING):
        if w.user_id not in here:
            Waitlist.objects.get_or_create(slot=first, user=w.user, role=w.role)
    second.waitlist.all().delete()
    second.cancelled = True
    second.save(update_fields=["cancelled"])
    told = sum(_tell(actor, [su], first, old) for su, old in grew)
    record(
        actor,
        "slot.merged",
        first,
        before={"end": second.start.isoformat(), "merged slot": second.pk},
        after={
            "end": first.end.isoformat(),
            "people": len(here),
            "people told": told,
            "in both": len(in_both),
        },
    )
    return told
