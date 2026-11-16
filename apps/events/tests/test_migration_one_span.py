"""The migration to one start and end per event (A32, private tracker 275): a split contest's
periods become one span, and its break stays off the air."""

from datetime import UTC, datetime, timedelta

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

pytestmark = pytest.mark.django_db(transaction=True)
BEFORE, AFTER = (
    [("events", "0009_reminder_help_text")],
    [("events", "0010_one_start_and_end_per_event")],
)
T, H = datetime(2027, 3, 13, 16, 0, tzinfo=UTC), timedelta(hours=1)


def test_periods_become_one_span_and_the_breaks_stay_off_the_air():
    ex = MigrationExecutor(connection)
    ex.migrate(BEFORE)
    old = ex.loader.project_state(BEFORE).apps
    Event, Period, OnAir = (
        old.get_model("events", n) for n in ("Event", "OperatingPeriod", "OnAirRange")
    )
    split = Event.objects.create(title="Split")  # 16-04 and 13-22 next day, nothing chosen
    Period.objects.create(event=split, start=T, end=T + 12 * H)
    Period.objects.create(event=split, start=T + 21 * H, end=T + 30 * H)
    chose = Event.objects.create(title="Chose")  # its own hours, one running into the gap
    Period.objects.create(event=chose, start=T, end=T + 4 * H)
    Period.objects.create(event=chose, start=T + 6 * H, end=T + 8 * H)
    OnAir.objects.create(event=chose, start=T + 2 * H, end=T + 7 * H)
    touching = Event.objects.create(title="Touching")  # one ends as the next starts: no break
    Period.objects.create(event=touching, start=T, end=T + 2 * H)
    Period.objects.create(event=touching, start=T + 2 * H, end=T + 5 * H)
    Event.objects.create(title="Net")  # no period

    ex = MigrationExecutor(connection)
    ex.migrate(AFTER)
    new = ex.loader.project_state(AFTER).apps
    Event, OnAir = new.get_model("events", "Event"), new.get_model("events", "OnAirRange")

    def got(title):
        e = Event.objects.get(title=title)
        return (e.start, e.end), [
            (r.start, r.end) for r in OnAir.objects.filter(event=e).order_by("start")
        ]

    assert got("Split") == ((T, T + 30 * H), [(T, T + 12 * H), (T + 21 * H, T + 30 * H)])
    assert got("Chose") == ((T, T + 8 * H), [(T + 2 * H, T + 4 * H), (T + 6 * H, T + 7 * H)])
    assert got("Touching") == ((T, T + 5 * H), [])  # the whole span is stored as nothing
    assert got("Net") == ((None, None), [])


def test_the_old_free_text_is_read_into_fields_and_kept_as_the_note_where_it_cannot_be():
    """Private tracker 273: migration 0011 reads "When it recurs, in words"."""
    from datetime import time

    to, at = (
        [("events", "0010_one_start_and_end_per_event")],
        [("events", "0011_when_it_meets_in_fields")],
    )
    ex = MigrationExecutor(connection)
    ex.migrate(to)
    Event = ex.loader.project_state(to).apps.get_model("events", "Event")
    Event.objects.create(title="Read", display_only=True, recurrence_text="Tuesdays 20:00 ET")
    Event.objects.create(title="Kept", display_only=True, recurrence_text="when the band is open")
    ex = MigrationExecutor(connection)
    ex.migrate(at)
    Event = ex.loader.project_state(at).apps.get_model("events", "Event")
    read, kept = Event.objects.get(title="Read"), Event.objects.get(title="Kept")
    assert (read.repeats, read.repeat_weekday, read.meets_at, read.meeting_note) == (
        "weekly",
        1,
        time(20),
        "",
    )
    assert (kept.repeats, kept.meeting_note) == ("", "when the band is open")
