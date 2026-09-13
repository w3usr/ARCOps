"""
Contest-calendar date lines (FR-38, FR-40), ported from the club's prototype.

Grammar as observed on the WA7BNM Contest Calendar: an optional qualifier ending in a colon,
then segments joined by " and ", each "HHMMZ, Mon D to HHMMZ, Mon D" or "HHMMZ-HHMMZ, Mon D",
with one ", YYYY" at the end for the whole line. 2400Z is the next day's 00:00. The year
belongs to the last date; earlier dates later in the calendar are the previous year.

Parsing only. Retrieval of pages waits on the calendar owner's authorisation (FR-40).
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import asdict, dataclass, field

MONTHS = {
    m: i
    for i, m in enumerate(
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1
    )
}
_SEG_RANGE = re.compile(
    r"^(?P<t1>\d{4})Z,\s*(?P<m1>[A-Z][a-z]{2})\s+(?P<d1>\d{1,2})\s+to\s+(?P<t2>\d{4})Z,\s*(?P<m2>[A-Z][a-z]{2})\s+(?P<d2>\d{1,2})$"
)
_SEG_SAMEDAY = re.compile(
    r"^(?P<t1>\d{4})Z-(?P<t2>\d{4})Z,\s*(?P<m1>[A-Z][a-z]{2})\s+(?P<d1>\d{1,2})$"
)
_YEAR_TAIL = re.compile(r",\s*(?P<year>\d{4})\s*$")


@dataclass
class Segment:
    start: dt.datetime
    end: dt.datetime


@dataclass
class DateLine:
    raw: str
    qualifier: str | None = None
    year: int | None = None
    segments: list[Segment] = field(default_factory=list)
    parsed: bool = False
    error: str | None = None

    def as_dict(self) -> dict:
        d = asdict(self)
        d["segments"] = [
            {"start": s.start.isoformat(), "end": s.end.isoformat()} for s in self.segments
        ]
        return d


def _stamp(year: int, mon: str, day: int, hhmm: str) -> dt.datetime:
    h, m = int(hhmm[:2]), int(hhmm[2:])
    base = dt.datetime(year, MONTHS[mon], day, tzinfo=dt.UTC)
    if h == 24:
        base += dt.timedelta(days=1)
        h = 0
    return base.replace(hour=h, minute=m)


def parse_date_line(text: str) -> DateLine:
    row = DateLine(raw=text.strip())
    s = row.raw
    m = _YEAR_TAIL.search(s)
    if not m:
        row.error = "no trailing year"
        return row
    row.year = int(m.group("year"))
    s = s[: m.start()].strip()
    first = re.search(r"\d{4}Z", s)
    if first and first.start() > 0:
        row.qualifier = s[: first.start()].strip().rstrip(":").strip() or None
        s = s[first.start() :]
    points: list[tuple[str, int, str]] = []
    shapes: list[tuple[int, int]] = []
    for part in [p.strip() for p in re.split(r"\s+and\s+", s)]:
        mr, ms = _SEG_RANGE.match(part), _SEG_SAMEDAY.match(part)
        if mr:
            points += [(mr["m1"], int(mr["d1"]), mr["t1"]), (mr["m2"], int(mr["d2"]), mr["t2"])]
        elif ms:
            points += [(ms["m1"], int(ms["d1"]), ms["t1"]), (ms["m1"], int(ms["d1"]), ms["t2"])]
        else:
            row.error = f"unrecognised segment: {part!r}"
            return row
        shapes.append((len(points) - 2, len(points) - 1))
    if any(mon not in MONTHS for mon, _, _ in points):
        row.error = "unknown month"
        return row
    years = [row.year] * len(points)
    for i in range(len(points) - 2, -1, -1):
        cur = (MONTHS[points[i][0]], points[i][1])
        nxt = (MONTHS[points[i + 1][0]], points[i + 1][1])
        years[i] = years[i + 1] - 1 if cur > nxt else years[i + 1]
    try:
        for a, b in shapes:
            row.segments.append(Segment(_stamp(years[a], *points[a]), _stamp(years[b], *points[b])))
    except ValueError as exc:
        row.error = f"invalid date: {exc}"
        row.segments = []
        return row
    row.parsed = True
    return row
