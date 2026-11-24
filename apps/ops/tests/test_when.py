"""One form for every date and time (apps/ops/when.py)."""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from apps.ops import when

A = datetime(2026, 11, 21, 21, 0, tzinfo=UTC)
NY = ZoneInfo("America/New_York")


def test_utc_reads_one_way_and_drops_the_year_only_when_asked():
    assert when.utc(A) == "Sat 21 Nov 2026 21:00 UTC"
    assert when.utc(A, year=False) == "Sat 21 Nov 21:00 UTC"
    assert when.utc(A.astimezone(NY)) == "Sat 21 Nov 2026 21:00 UTC"  # always said in UTC
    assert when.utc(None) == ""


def test_a_span_within_a_day_and_across_days():
    assert when.utc_span(A, A.replace(hour=23)) == "Sat 21 Nov 2026 21:00–23:00 UTC"
    later = datetime(2026, 11, 23, 2, 59, tzinfo=UTC)
    assert when.utc_span(A, later) == "Sat 21 Nov 2026 21:00 – Mon 23 Nov 2026 02:59 UTC"


def test_a_plain_date_and_a_local_time():
    assert when.day(date(2026, 11, 7)) == "7 Nov 2026"
    assert when.day(datetime(2026, 11, 8, 2, 0, tzinfo=UTC)) == "8 Nov 2026"
    assert when.local(A, NY) == "Sat, Nov 21, 4:00 PM EST"
    assert when.local_span(A, A.replace(hour=23), NY) == "Sat, Nov 21, 4:00–6:00 PM EST"
    noon = datetime(2026, 11, 21, 16, 0, tzinfo=UTC)  # 11:00 AM to 1:00 PM: both halves named
    assert when.local_span(noon, noon.replace(hour=18), NY) == "Sat, Nov 21, 11:00 AM–1:00 PM EST"


def test_a_local_span_across_the_clock_change_names_each_ends_zone():
    """The clocks go back at 06:00 UTC on 1 Nov 2026: 6:00 AM that morning is EST, not EDT."""
    night = datetime(2026, 11, 1, 4, 0, tzinfo=UTC)
    assert (
        when.local_span(night, night.replace(hour=11), NY)
        == "Sun, Nov 1, 12:00 AM EDT – 6:00 AM EST"
    )
    weekend = datetime(2026, 10, 31, 22, 0, tzinfo=UTC)
    assert (
        when.local_span(weekend, datetime(2026, 11, 2, 0, 59, tzinfo=UTC), NY)
        == "Sat, Oct 31, 6:00 PM EDT – Sun, Nov 1, 7:59 PM EST"
    )


def test_a_utc_box_takes_the_date_and_a_24_hour_time_however_the_browser_is_set():
    from apps.ops.when import Unreadable, parse_utc, typed

    for text in (
        "2026-11-21 21:00",
        "2026-11-21 2100",
        "2026-11-21T21:00",
        " 2026-11-21 21:00 UTC ",
    ):
        assert parse_utc(text) == A, text
    assert typed(A) == "2026-11-21T21:00" and parse_utc("") is None  # a datetime-local value (A35)
    for text, said in (
        ("11/21/2026 09:00 PM", "Write it as 2026-11-21 21:00"),
        ("2026-11-21", "Write it as"),
        ("2026-11-21 24:00", "hours run 00 to 23"),
        ("2026-02-30 10:00", "check the month and the day"),
    ):
        try:
            parse_utc(text)
            raise AssertionError(f"{text!r} was taken")
        except Unreadable as exc:
            assert said in str(exc), text


def test_a_date_stored_as_text_reads_the_same_and_nothing_else_fails():
    """The agreement PDF reads dates back from a decision record, as ISO text."""
    assert when.day("2027-09-01") == "1 Sep 2027"
    assert when.utc("2026-11-21T21:00:00+00:00") == "Sat 21 Nov 2026 21:00 UTC"
    assert when.day("not a date") == "not a date" and when.utc("") == ""


def test_a_time_box_reads_the_offset_the_browser_sends_or_the_viewers_clock():
    """A38: the page's script sends ISO 8601 with the browser's offset, which wins; without the
    script the box is the wall clock of the zone the page was drawn in, the viewer's."""
    from zoneinfo import ZoneInfo

    from django import forms
    from django.utils import timezone

    from apps.ops.forms import utc_field
    from apps.ops.when import typed

    class F(forms.Form):
        start = utc_field("Starts")

    with timezone.override(ZoneInfo("America/New_York")):
        for sent in (
            "2026-11-21T16:00",
            "2026-11-21T16:00-05:00",
            "2026-11-21T13:00:00-08:00",
            "2026-11-21T21:00Z",
        ):
            f = F({"start": sent})
            assert (
                f.is_valid() and f.cleaned_data["start"].isoformat() == "2026-11-21T21:00:00+00:00"
            )
            assert typed(f.cleaned_data["start"]) == "2026-11-21T16:00"  # shown on EST's clock
        assert "data-instant" in str(f["start"]) and "UTC" not in str(f["start"])
        f = F({"start": "2026-11-01T01:30"})
        assert not f.is_valid() and "happens twice in your time zone" in str(f.errors)
        assert not F({"start": "2026-11-21T16:00+99:00"}).is_valid()
        # sent back after an error elsewhere on the form: the box shows the wall clock again
        assert 'value="2026-11-21T16:00"' in str(F({"start": "2026-11-21T13:00-08:00"})["start"])


def test_a_local_time_the_clocks_skip_or_repeat_is_refused_not_guessed():
    """A35: 2:30 AM on the night the clocks go forward never happens in New York, and 1:30 AM on
    the night they go back happens twice; a guess would put a slot an hour off."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    import pytest

    from apps.ops.when import UTC, Unreadable, in_zone, typed

    ny = ZoneInfo("America/New_York")
    assert typed(in_zone(datetime(2026, 11, 21, 16, 0, tzinfo=UTC), ny)) == "2026-11-21T21:00"
    with pytest.raises(Unreadable, match="2:30 AM on 8 Mar does not happen"):
        in_zone(datetime(2026, 3, 8, 2, 30, tzinfo=UTC), ny)
    with pytest.raises(Unreadable, match="1:30 AM on 1 Nov happens twice"):
        in_zone(datetime(2026, 11, 1, 1, 30, tzinfo=UTC), ny)
