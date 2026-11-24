"""Event management helpers used by the manage page: duplication (FR-42) and slot generation
with role capacities (FR-46, FR-49)."""

from __future__ import annotations

from datetime import timedelta

from ..models import (
    Captaincy,
    Event,
    OnAirRange,
    Opening,
    RoleCapacity,
    Slot,
)
from .slots import generate_slots


def duplicate_event(source: Event, actor, shift: timedelta = timedelta(0)) -> Event:
    """FR-42: the copy carries every field, the start and end, the on-air hours, the
    locations and positions, the slot structure with its capacities, the eligibility rules and
    the openings; no sign-ups, no captains but the person copying, and it starts as a draft under
    a marked title. Every date moves by `shift`, the officer's new start less the old one, so the
    copy keeps its shape on the new dates."""
    copy = Event.objects.create(
        type=source.type,
        title=f"{source.title} (copy)",
        description_html=source.description_html,
        state=Event.State.DRAFT,
        display_timezone=source.display_timezone,
        start=source.start + shift if source.start else None,
        end=source.end + shift if source.end else None,
        min_license_class=source.min_license_class,
        rules_url=source.rules_url,
        contest_fields=source.contest_fields,
        calendar_ref=source.calendar_ref,
        kbyg_html=source.kbyg_html,
        reminder_hours_before=source.reminder_hours_before,
        checkin_opens_minutes_before=source.checkin_opens_minutes_before,
        display_only=source.display_only,
        repeats=source.repeats,
        repeat_weekday=source.repeat_weekday,
        repeat_week=source.repeat_week,
        repeat_day=source.repeat_day,
        meets_at=source.meets_at,
        meets_until=source.meets_until,
        meeting_note=source.meeting_note,
        duplicated_from=source,
        created_by=actor,
    )
    for r in source.on_air_ranges.all():  # the club's on-air hours go with the span
        OnAirRange.objects.create(event=copy, start=r.start + shift, end=r.end + shift)
    for o in source.openings.all():  # announced again on the new dates, so not yet announced
        Opening.objects.create(
            event=copy,
            role=o.role,
            opens_at=o.opens_at + shift,
            categories=o.categories,
            announce=o.announce,
        )
    new_slot = {}  # old slot pk -> its copy, for the rules that name a slot
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
                old = s.pk
                s.pk = None
                s.position = pos
                s.control_operator = None
                s.start += shift
                s.end += shift
                s.save()
                new_slot[old] = s
                for c in caps:
                    RoleCapacity.objects.create(slot=s, role=c.role, capacity=c.capacity)
    for rule in source.eligibility_rules.all():
        if rule.slot_id and rule.slot_id not in new_slot:
            continue  # a canceled slot is not copied, and nor is its rule
        rule.pk = None
        rule.event = copy
        rule.slot = new_slot.get(rule.slot_id)
        rule.save()
    Captaincy.objects.get_or_create(event=copy, user=actor)
    return copy


def generate_with_capacities(
    event: Event,
    positions,
    minutes: int,
    setup_slots: int,
    breakdown_slots: int,
    capacities: dict[str, int],
    fill: bool = False,
    setup_minutes: int | None = None,
    breakdown_minutes: int | None = None,
) -> list[Slot]:
    """Slots for the positions given, then a capacity row per role with a non-zero count. With
    `fill`, only the empty hours get slots and setup and breakdown are not made."""
    created = generate_slots(
        event,
        positions,
        minutes=minutes,
        setup_slots=setup_slots,
        breakdown_slots=breakdown_slots,
        setup_minutes=setup_minutes,
        breakdown_minutes=breakdown_minutes,
        fill=fill,
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
