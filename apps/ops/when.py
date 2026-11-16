"""How a date or time reads, everywhere (private tracker 274; NAF and SK, 2026-11-12 and 2026-11-16).

- **A UTC instant:** `Sat 21 Nov 2026 21:00 UTC`: weekday, day, month as a word, year, a 24-hour
  time, `UTC`. In tight places (roster rows, slot lists) the year drops out: `Sat 21 Nov 21:00 UTC`.
  A span within a day is `Sat 21 Nov 2026 21:00–23:00 UTC`; across days,
  `Sat 21 Nov 2026 21:00 – Mon 23 Nov 2026 02:59 UTC`.
- **A plain date** that is not an instant (a license's expiry, a join date): `21 Nov 2026`.
- **A local time** (the event's own zone, beside UTC) in the US convention the club reads:
  `Sat, Nov 21, 4:00 PM EST`.
- **Machine-readable output** (CSV, the calendar feed, `value=`) stays ISO 8601 and is not made
  here.

Every page, mail, the PDF and the outbox go through these, and `tools/check_interface.sh` refuses
a hand-written UTC format anywhere else.
"""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

UTC = ZoneInfo("UTC")


def _day(t: datetime, year: bool) -> str:
    return f"{t:%a %-d %b %Y}" if year else f"{t:%a %-d %b}"


def utc(t: datetime | None, year: bool = True) -> str:
    """`Sat 21 Nov 2026 21:00 UTC`; `Sat 21 Nov 21:00 UTC` without the year."""
    if t is None:
        return ""
    u = t.astimezone(UTC)
    return f"{_day(u, year)} {u:%H:%M} UTC"


def utc_span(start: datetime, end: datetime, year: bool = True) -> str:
    """`Sat 21 Nov 2026 21:00–23:00 UTC` within a day, else both ends in full."""
    s, e = start.astimezone(UTC), end.astimezone(UTC)
    if s.date() == e.date():
        return f"{_day(s, year)} {s:%H:%M}–{e:%H:%M} UTC"
    return f"{_day(s, year)} {s:%H:%M} – {_day(e, year)} {e:%H:%M} UTC"


def day(d: date | datetime | None) -> str:
    """`21 Nov 2026`: a plain date, or the UTC date of an instant."""
    if d is None:
        return ""
    if isinstance(d, datetime):
        d = d.astimezone(UTC).date()
    return f"{d.day} {d:%b %Y}"


def _clock(t: datetime) -> str:
    return f"{t.hour % 12 or 12}:{t:%M} {'AM' if t.hour < 12 else 'PM'}"


def local(t: datetime, zone, year: bool = False) -> str:
    """`Sat, Nov 21, 4:00 PM EST` in `zone` (`Sat, Nov 21, 2026, 4:00 PM EST` with the year)."""
    s = t.astimezone(zone)
    when = f"{s:%a, %b} {s.day}" + (f", {s.year}" if year else "")
    return f"{when}, {_clock(s)} {s:%Z}"


def local_span(start: datetime, end: datetime, zone, year: bool = False) -> str:
    """`Sat, Nov 21, 4:00–6:00 PM EST` within a day (one AM or PM where both share it), else
    `Sat, Nov 21, 4:00 PM – Mon, Nov 23, 9:59 PM EST`."""
    s, e = start.astimezone(zone), end.astimezone(zone)
    head = f"{s:%a, %b} {s.day}" + (f", {s.year}" if year else "")
    if s.date() == e.date():
        a, b = _clock(s), _clock(e)
        a = a[:-3] if a[-2:] == b[-2:] else a
        return f"{head}, {a}–{b} {s:%Z}"
    tail = f"{e:%a, %b} {e.day}" + (f", {e.year}" if year else "")
    return f"{head}, {_clock(s)} – {tail}, {_clock(e)} {e:%Z}"
