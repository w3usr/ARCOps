import datetime as dt

import pytest
from django.utils import timezone

from apps.events.models import Event, Location, OperatingPeriod, Position
from apps.events.services.slots import generate_slots

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
