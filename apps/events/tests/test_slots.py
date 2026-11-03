import datetime as dt

import pytest
from django.utils import timezone

from apps.events.models import Event, Location, OperatingPeriod, Position, Slot
from apps.events.services.slots import fill_empty_hours, generate_slots

pytestmark = pytest.mark.django_db


def make(periods):
    ev = Event.objects.create(title="T")
    for s, e in periods:
        OperatingPeriod.objects.create(event=ev, start=s, end=e)
    loc = Location.objects.create(event=ev, name="L")
    return ev, Position.objects.create(location=loc, name="P")


def test_two_period_contest_generates_only_inside_periods():
    t0 = timezone.make_aware(dt.datetime(2026, 10, 10, 16, 0), dt.UTC)
    ev, pos = make(
        [
            (t0, t0 + dt.timedelta(hours=12)),
            (t0 + dt.timedelta(hours=21), t0 + dt.timedelta(hours=30)),
        ]
    )
    slots = generate_slots(ev, [pos], minutes=60)
    assert len(slots) == 21  # 12 + 9, none in the overnight gap
    assert all(s.kind == "operating" for s in slots)


def test_short_final_slot_and_setup_breakdown():
    t0 = timezone.make_aware(dt.datetime(2026, 9, 26, 0, 0), dt.UTC)
    ev, pos = make([(t0, t0 + dt.timedelta(minutes=150))])
    slots = generate_slots(ev, [pos], minutes=60, setup_slots=1, breakdown_slots=2)
    op = [s for s in slots if s.kind == "operating"]
    assert [int((s.end - s.start).total_seconds() // 60) for s in op] == [60, 60, 30]
    assert (
        sum(1 for s in slots if s.kind == "setup") == 1
        and sum(1 for s in slots if s.kind == "breakdown") == 2
    )
    assert min(s.start for s in slots) == t0 - dt.timedelta(hours=1)


def test_windows_for_hour_limited_event():
    t0 = timezone.make_aware(dt.datetime(2026, 10, 19, 13, 0), dt.UTC)
    ev, pos = make([(t0, t0 + dt.timedelta(days=4, hours=11))])  # SCR Monday 1300Z to Friday 2359Z
    windows = [
        (t0 + dt.timedelta(days=d, hours=2), t0 + dt.timedelta(days=d, hours=8)) for d in range(5)
    ]  # 1500-2100Z daily
    slots = generate_slots(ev, [pos], minutes=60, windows=windows)
    assert len(slots) == 30


# -------------------------------------------- adding to the empty hours (#153, FR-46, FR-48) ---

T0 = timezone.make_aware(dt.datetime(2026, 10, 19, 15, 0), dt.UTC)
H = dt.timedelta(hours=1)


def _hours(slots):
    return sorted((s.start, s.end) for s in slots)


def test_a_period_added_later_is_filled_and_the_grid_is_kept():
    ev, pos = make([(T0, T0 + 6 * H)])
    grid = generate_slots(ev, [pos], minutes=60)
    OperatingPeriod.objects.create(event=ev, start=T0 + 24 * H, end=T0 + 28 * H)
    added = fill_empty_hours(ev, [pos], minutes=60)
    assert _hours(added) == [(T0 + (24 + i) * H, T0 + (25 + i) * H) for i in range(4)]
    assert set(Slot.objects.filter(position=pos).values_list("pk", flat=True)) >= {
        s.pk for s in grid
    }


def test_a_range_added_later_fills_only_its_uncovered_hours():
    ev, pos = make([(T0 - 2 * H, T0 + 6 * H)])
    generate_slots(ev, [pos], minutes=60, windows=[(T0, T0 + 6 * H)])  # 15:00-21:00
    added = fill_empty_hours(ev, [pos], minutes=60, windows=[(T0 - 2 * H, T0 + H)])  # 13:00-16:00
    assert _hours(added) == [(T0 - 2 * H, T0 - H), (T0 - H, T0)]


def test_filling_twice_adds_nothing_the_second_time():
    ev, pos = make([(T0, T0 + 6 * H)])
    assert len(fill_empty_hours(ev, [pos], minutes=60)) == 6
    assert fill_empty_hours(ev, [pos], minutes=60) == []


def test_a_new_position_gets_the_whole_grid_and_the_old_one_nothing():
    ev, pos = make([(T0, T0 + 3 * H)])
    generate_slots(ev, [pos], minutes=60)
    mult = Position.objects.create(location=pos.location, name="Mult")
    added = fill_empty_hours(ev, [pos, mult], minutes=60)
    assert len(added) == 3 and {s.position_id for s in added} == {mult.pk}


def test_a_canceled_slot_keeps_its_hour_empty():
    """SK, 2026-11-03: a cancellation is a decision; the fill does not undo it."""
    ev, pos = make([(T0, T0 + 3 * H)])
    first = generate_slots(ev, [pos], minutes=60)[0]
    Slot.objects.filter(pk=first.pk).update(cancelled=True)
    assert fill_empty_hours(ev, [pos], minutes=60) == []


def test_gaps_are_cut_from_their_own_start_and_slivers_are_skipped():
    ev, pos = make([(T0, T0 + 4 * H)])
    Slot.objects.create(position=pos, start=T0 + dt.timedelta(minutes=10), end=T0 + 2 * H)
    Slot.objects.create(position=pos, start=T0 + 3 * H, end=T0 + 4 * H)
    added = fill_empty_hours(ev, [pos], minutes=60)
    # 15:00-15:10 is under the 15-minute minimum and stays empty; 17:00-18:00 is filled
    assert _hours(added) == [(T0 + 2 * H, T0 + 3 * H)]
    assert all(s.kind == "operating" for s in added)


# ------------------------------------------- what the generator will make, said first (#168) ---


def test_the_preview_says_what_generating_will_make():
    from apps.events.services.slots import describe

    ev, pos = make([(T0, T0 + 5 * H)])
    mult = Position.objects.create(location=pos.location, name="Mult")
    said = describe(ev, [pos, mult], minutes=60, setup_slots=1, breakdown_slots=1)
    assert said == (
        "14 slots: 7 per position × 2 positions, including a setup and a breakdown slot each."
    )
    assert describe(ev, [pos], minutes=60) == "5 slots: 5 per position × 1 position."
    assert Slot.objects.count() == 0  # it only counts


def test_the_preview_says_what_filling_will_add_and_matches_the_fill():
    from apps.events.services.slots import describe

    ev, pos = make([(T0, T0 + 6 * H)])
    generate_slots(ev, [pos], minutes=60, windows=[(T0 + 2 * H, T0 + 6 * H)])
    said = describe(ev, [pos], minutes=60, fill=True)
    assert said == "Adds 2 slots to the empty hours."
    assert len(fill_empty_hours(ev, [pos], minutes=60)) == 2
    assert describe(ev, [pos], minutes=60, fill=True) == (
        "Every hour already has a slot; nothing would be added."
    )
