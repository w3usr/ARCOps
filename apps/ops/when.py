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

**For now, pages show the viewer's own time only, never UTC** (functional addendum A38; NAF and
SK, 2026-11-18): the browser names its zone in the `tz` cookie (static/js/app.js), the middleware
activates it (apps/ops/middleware.py), and `local()` and `local_span()` default to it. Mail, the
agreement PDF and machine output keep their own zones. Storage and logic stay UTC.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.utils import timezone

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


def twelve_hour(t) -> str:
    """`4:00 PM`: a datetime's or a time's clock, in the US convention the club reads."""
    return f"{t.hour % 12 or 12}:{t:%M} {'AM' if t.hour < 12 else 'PM'}"


def clock_span(start: datetime, end: datetime) -> str:
    """`5:00–7:00 PM`, the clocks alone in the viewer's zone, for a button that sits under the
    full time (private tracker 361)."""
    zone = timezone.get_current_timezone()
    a, b = twelve_hour(start.astimezone(zone)), twelve_hour(end.astimezone(zone))
    return f"{a[:-3] if a[-2:] == b[-2:] else a}–{b}"


def local(t: datetime, zone=None, year: bool = False) -> str:
    """`Sat, Nov 21, 4:00 PM EST` in `zone`, by default the viewer's (`Sat, Nov 21, 2026, 4:00
    PM EST` with the year)."""
    s = t.astimezone(zone or timezone.get_current_timezone())
    when = f"{s:%a, %b} {s.day}" + (f", {s.year}" if year else "")
    return f"{when}, {twelve_hour(s)} {s:%Z}"


def local_span(start: datetime, end: datetime, zone=None, year: bool = False) -> str:
    """`Sat, Nov 21, 4:00–6:00 PM EST` within a day (one AM or PM where both share it), else
    `Sat, Nov 21, 4:00 PM – Mon, Nov 23, 9:59 PM EST`. Where the clocks change between the two
    ends, each names its own zone (`Sun, Nov 1, 12:00 AM EDT – 6:00 AM EST`): one name for both
    put one end an hour off."""
    zone = zone or timezone.get_current_timezone()
    s, e = start.astimezone(zone), end.astimezone(zone)
    head = f"{s:%a, %b} {s.day}" + (f", {s.year}" if year else "")
    a, b = twelve_hour(s), twelve_hour(e)
    changed = s.tzname() != e.tzname()
    if s.date() == e.date():
        if changed:
            return f"{head}, {a} {s:%Z} – {b} {e:%Z}"
        a = a[:-3] if a[-2:] == b[-2:] else a
        return f"{head}, {a}–{b} {s:%Z}"
    tail = f"{e:%a, %b} {e.day}" + (f", {e.year}" if year else "")
    return f"{head}, {a}{f' {s:%Z}' if changed else ''} – {tail}, {b} {e:%Z}"


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


def in_zone(t: datetime, zone) -> datetime:
    """A box's date and time read on `zone`'s clock rather than UTC's (A35), as UTC. The hour the
    clocks go forward never happens there, and the hour they go back happens twice; either is
    refused rather than guessed, since a guess can put a slot an hour off."""
    wall = t.replace(tzinfo=None)
    first, second = wall.replace(tzinfo=zone, fold=0), wall.replace(tzinfo=zone, fold=1)
    if first.utcoffset() != second.utcoffset():
        at = f"{wall.hour % 12 or 12}:{wall:%M} {'AM' if wall.hour < 12 else 'PM'} on {wall.day} {wall:%b}"
        if first.astimezone(UTC).astimezone(zone).replace(tzinfo=None) != wall:
            raise Unreadable(
                f"{at} does not happen in your time zone: the clocks go "
                "forward that night. Choose a time outside that hour."
            )
        raise Unreadable(
            f"{at} happens twice in your time zone, as the clocks go back. "
            "Choose a time outside that hour."
        )
    return first.astimezone(UTC)


_OFFSET = re.compile(r"(?:Z|[+-]\d{2}:?\d{2})\s*$", re.I)


def has_offset(text: str) -> bool:
    """Whether a box's value came with its offset (or Z), as the page's script sends it."""
    return bool(_OFFSET.search((text or "").strip()))


def parse_box(text: str, zone=None) -> datetime | None:
    """A time box's value as UTC (A38). The page's script sends ISO 8601 with the browser's
    offset, `2026-11-21T16:00-05:00`; without the script the box holds the wall clock of the zone
    the page was drawn in, `zone` (by default the viewer's), read as `in_zone` reads it."""
    if has_offset(text):
        try:
            return datetime.fromisoformat(text.strip()).astimezone(UTC)
        except ValueError:
            raise Unreadable("That is not a date and time: pick one in the box.") from None
    t = parse_utc(text)
    return in_zone(t, zone or timezone.get_current_timezone()) if t else None


def typed(t: datetime | None) -> str:
    """What a box holds: `2026-11-21T16:00`, the viewer's wall clock, the value a datetime-local
    box takes (A35, A38)."""
    return t.astimezone(timezone.get_current_timezone()).strftime("%Y-%m-%dT%H:%M") if t else ""
