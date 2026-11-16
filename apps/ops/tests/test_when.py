"""One form for every date and time (private tracker 274; apps/ops/when.py)."""

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
