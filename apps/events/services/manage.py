"""Event management helpers used by the manage page: duplication (FR-42) and slot generation
with role capacities (FR-46, FR-49)."""

from __future__ import annotations

from ..models import Captaincy, Event, Location, OperatingPeriod, Position, RoleCapacity, Slot
from .slots import generate_slots


def duplicate_event(source: Event, actor) -> Event:
    """FR-42: the copy carries every field, the operating periods, the locations and positions,
    and the slot structure with its capacities; no sign-ups, no captains but the person copying,
    and it starts as a draft under a marked title."""
    copy = Event.objects.create(
        type=source.type,
        title=f"{source.title} (copy)",
        description_html=source.description_html,
        state=Event.State.DRAFT,
        display_timezone=source.display_timezone,
        min_license_class=source.min_license_class,
        rules_url=source.rules_url,
        contest_fields=source.contest_fields,
        calendar_ref=source.calendar_ref,
        kbyg_html=source.kbyg_html,
        duplicated_from=source,
        created_by=actor,
    )
    for p in source.periods.all():
        OperatingPeriod.objects.create(event=copy, start=p.start, end=p.end)
    if hasattr(source, "limit"):
        lim = source.limit
        lim.pk = None
        lim.event = copy
        lim.save()
    for loc in source.locations.all():
        positions = list(loc.positions.all())
        loc.pk = None
        loc.event = copy
        loc.save()
        for pos in positions:
            slots = list(pos.slots.filter(cancelled=False).prefetch_related("capacities"))
            pos.pk = None
            pos.location = loc
            pos.save()
            for s in slots:
                caps = list(s.capacities.all())
                s.pk = None
                s.position = pos
                s.control_operator = None
                s.save()
                for c in caps:
                    RoleCapacity.objects.create(slot=s, role=c.role, capacity=c.capacity)
    Captaincy.objects.get_or_create(event=copy, user=actor)
    return copy


def generate_with_capacities(
    event: Event,
    positions,
    minutes: int,
    setup_slots: int,
    breakdown_slots: int,
    capacities: dict[str, int],
    windows=None,
) -> list[Slot]:
    """Slots for the positions given, then a capacity row per role with a non-zero count."""
    created = generate_slots(
        event,
        positions,
        minutes=minutes,
        setup_slots=setup_slots,
        breakdown_slots=breakdown_slots,
        windows=windows,
    )
    rows = [
        RoleCapacity(slot=s, role=role, capacity=n)
        for s in created
        for role, n in capacities.items()
        if n > 0
    ]
    RoleCapacity.objects.bulk_create(rows)
    return created


def has_signups(event: Event) -> bool:
    return Slot.objects.filter(position__location__event=event, signups__isnull=False).exists()


__all__ = ["duplicate_event", "generate_with_capacities", "has_signups", "Location", "Position"]
