"""When a regular meeting or net meets, in fields (FR-45; private tracker 273, SK 2026-11-16)."""

from datetime import UTC, datetime, time

import pytest

from apps.events.models import Event
from apps.events.services.meets import describe, next_meeting, parse

from .test_manage import _as

pytestmark = pytest.mark.django_db
NOW = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)  # a Monday


def _net(**kw):
    kw.setdefault("display_timezone", "America/New_York")
    return Event(title="Net", display_only=True, **kw)


def test_each_pattern_reads_as_a_line_in_the_events_own_zone():
    weekly = _net(repeats="weekly", repeat_weekday=1, meets_at=time(20, 0))
    assert describe(weekly, NOW) == "Tuesdays, 8:00 PM EST"
    first = _net(repeats="monthly_weekday", repeat_weekday=0, repeat_week=1, meets_at=time(19, 0))
    assert describe(first, NOW) == "First Monday of the month, 7:00 PM EST"
    last = _net(repeats="monthly_weekday", repeat_weekday=4, repeat_week=-1, meets_at=time(11, 0))
    last.meets_until = time(13, 0)
    assert describe(last, NOW) == "Last Friday of the month, 11:00 AM–1:00 PM EST"
    dated = _net(repeats="monthly_date", repeat_day=15, meets_at=time(19, 0), meets_until=time(21))
    assert describe(dated, NOW) == "The 15th of every month, 7:00–9:00 PM EST"
    london = _net(repeats="weekly", repeat_weekday=2, meets_at=time(19, 30))
    london.display_timezone = "Europe/London"
    assert describe(london, NOW) == "Wednesdays, 7:30 PM GMT"
    assert describe(_net(), NOW) == ""


def test_the_next_meeting():
    weekly = _net(repeats="weekly", repeat_weekday=1, meets_at=time(20, 0))
    assert next_meeting(weekly, NOW).isoformat() == "2026-11-17T20:00:00-05:00"
    last = _net(repeats="monthly_weekday", repeat_weekday=4, repeat_week=-1, meets_at=time(19))
    assert next_meeting(last, NOW).date().isoformat() == "2026-11-27"
    thirty_first = _net(repeats="monthly_date", repeat_day=31, meets_at=time(19))
    assert next_meeting(thirty_first, NOW).date().isoformat() == "2026-11-30"  # its last day


def test_old_free_text_is_read_where_it_can_be_and_kept_where_it_cannot():
    assert parse("Tuesdays 20:00 ET") == (
        {"meets_at": time(20), "repeat_weekday": 1, "repeats": "weekly"},
        "",
    )
    fields, note = parse("First Monday 7pm")
    assert fields == {
        "meets_at": time(19),
        "repeat_weekday": 0,
        "repeats": "monthly_weekday",
        "repeat_week": 1,
    }
    assert note == ""
    assert parse("15th of the month 19:00")[0]["repeat_day"] == 15
    fields, note = parse("Thursdays 8pm on 146.52, not during finals week")
    assert (
        fields["repeats"] == "weekly" and note == "Thursdays 8pm on 146.52, not during finals week"
    )
    assert parse("every other week-ish") == ({}, "every other week-ish")
    assert parse("Common-interest net, Tuesdays 8pm")[0]["repeat_weekday"] == 1  # not "comMON"
    assert parse("Tuesdays") == ({}, "Tuesdays")  # no time: nothing is guessed


def test_a_display_only_event_must_say_when_it_meets_and_others_keep_nothing(officer):
    c = _as(officer)
    base = {"title": "Net", "type": "net", "display_only": "on"}
    body = c.post("/events/new/", base).content.decode()
    assert "Choose how often it meets." in body and "Give the time it starts." in body
    body = c.post(
        "/events/new/", base | {"repeats": "monthly_weekday", "meets_at": "20:00"}
    ).content.decode()
    assert "Choose the day of the week." in body and "Choose which week of the month." in body
    c.post(
        "/events/new/",
        base
        | {
            "repeats": "monthly_date",
            "repeat_day": "15",
            "meets_at": "19:00",
            "meeting_note": "on 146.52",
        },
    )
    e = Event.objects.get(title="Net")
    assert (e.repeats, e.repeat_day, e.meets_at, e.meeting_note) == (
        "monthly_date",
        15,
        time(19),
        "on 146.52",
    )
    page = c.get(f"/events/{e.pk}/").content.decode()
    assert "The 15th of every month, 7:00 PM" in page and "Next: " in page and "on 146.52" in page
    c.post(
        "/events/new/",
        {"title": "Sprint", "type": "contest", "repeats": "weekly", "meets_at": "20:00"},
    )
    s = Event.objects.get(title="Sprint")
    assert (s.repeats, s.meets_at) == ("", None)


def test_the_fields_appear_only_for_a_display_only_event_and_only_as_the_pattern_needs(officer):
    body = _as(officer).get("/events/new/").content.decode()
    assert 'data-reveal-when="#id_display_only"' in body
    assert 'data-reveal-when="#id_repeats" data-reveal-value="weekly monthly_weekday"' in body
    assert 'data-reveal-when="#id_repeats" data-reveal-value="monthly_date"' in body
