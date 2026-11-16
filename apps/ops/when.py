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

import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

UTC = ZoneInfo("UTC")


def _day(t: datetime, year: bool) -> str:
    return f"{t:%a %-d %b %Y}" if year else f"{t:%a %-d %b}"


def utc(t: datetime | str | None, year: bool = True) -> str:
    """`Sat 21 Nov 2026 21:00 UTC`; `Sat 21 Nov 21:00 UTC` without the year."""
    if t in (None, ""):
        return ""
    got = _instant(t)
    if not isinstance(got, datetime):
        return day(t)  # a date with no time, or not a date at all
    u = (got if got.tzinfo else got.replace(tzinfo=UTC)).astimezone(UTC)
    return f"{_day(u, year)} {u:%H:%M} UTC"


def utc_span(start: datetime, end: datetime, year: bool = True) -> str:
    """`Sat 21 Nov 2026 21:00–23:00 UTC` within a day, else both ends in full."""
    s, e = start.astimezone(UTC), end.astimezone(UTC)
    if s.date() == e.date():
        return f"{_day(s, year)} {s:%H:%M}–{e:%H:%M} UTC"
    return f"{_day(s, year)} {s:%H:%M} – {_day(e, year)} {e:%H:%M} UTC"


def _instant(t):
    """A datetime or date as given; an ISO 8601 string, as a decision record stores one, read
    into one (the agreement PDF reads them back); None for anything else."""
    if isinstance(t, (date, datetime)):
        return t
    try:
        return datetime.fromisoformat(t) if "T" in t or " " in t.strip() else date.fromisoformat(t)
    except (TypeError, ValueError):
        return None


def day(d: date | datetime | str | None) -> str:
    """`21 Nov 2026`: a plain date, or the UTC date of an instant."""
    if d in (None, ""):
        return ""
    got = _instant(d)
    if got is None:
        return str(d)  # not a date at all: shown as it is, never a page that fails
    d = got
    if isinstance(d, datetime) and d.tzinfo is None:
        d = d.replace(tzinfo=UTC)
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


# ---------------------------------------------------------------- typed in UTC ---

# The browser's own date and time box (A35, SK 2026-11-16, reversing A34's plain box): it sends
# ISO's "2026-11-21T21:00" whatever it shows. A link or script may still send "2026-11-21 21:00"
# or "2026-11-21 2100" (as contest rules write it), so those are taken too.
_TYPED = re.compile(
    r"^\s*(\d{4})-(\d{2})-(\d{2})(?:[ T]+(?:(\d{1,2}):(\d{2})|(\d{2})(\d{2})))?\s*(?:UTC|Z)?\s*$",
    re.I,
)


class Unreadable(ValueError):
    """What was typed is not a date and time; the message says how to write one."""


def parse_utc(text: str, need_time: bool = True) -> datetime | None:
    """A UTC instant from what was typed, None for nothing typed; Unreadable otherwise."""
    if not (text or "").strip():
        return None
    m = _TYPED.match(text)
    if not m or (need_time and m.group(4) is None and m.group(6) is None):
        raise Unreadable("Write it as 2026-11-21 21:00: the date, then a 24-hour time.")
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    h, mi = (int(m.group(4) or m.group(6) or 0), int(m.group(5) or m.group(7) or 0))
    if h > 23 or mi > 59:
        raise Unreadable("That is not a time: hours run 00 to 23, minutes 00 to 59.")
    try:
        return datetime(y, mo, d, h, mi, tzinfo=UTC)
    except ValueError:
        raise Unreadable("That is not a date: check the month and the day.") from None


def typed(t: datetime | None) -> str:
    """What a UTC box holds: `2026-11-21T21:00`, the value a datetime-local box takes (A35)."""
    return t.astimezone(UTC).strftime("%Y-%m-%dT%H:%M") if t else ""
