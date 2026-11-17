"""When a regular meeting or net meets (FR-45; private tracker 273, SK 2026-11-16).

A display-only event says when it meets in fields, not in free text: weekly, monthly on a weekday
("first Monday", "last Friday"), or monthly on a date, at a time in the event's own zone. The site
writes the line members read and works out the next date. `parse` reads the free text such events
held before, for the migration that carried them over.
"""

from __future__ import annotations

import calendar
import re
from datetime import date, datetime, time, timedelta

from django.utils import timezone

from apps.ops.when import twelve_hour

WEEKLY, MONTHLY_WEEKDAY, MONTHLY_DATE = "weekly", "monthly_weekday", "monthly_date"
PATTERNS = [
    (WEEKLY, "Every week"),
    (MONTHLY_WEEKDAY, "Every month, on a weekday"),
    (MONTHLY_DATE, "Every month, on a date"),
]
DAYS = list(calendar.day_name)  # Monday first, as date.weekday() counts
WEEKS = [(1, "First"), (2, "Second"), (3, "Third"), (4, "Fourth"), (-1, "Last")]


def _ordinal(n: int) -> str:
    return f"{n}{'th' if 11 <= n % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def _on(event, d: date) -> bool:
    if event.repeats == WEEKLY:
        return d.weekday() == event.repeat_weekday
    if event.repeats == MONTHLY_WEEKDAY:
        if d.weekday() != event.repeat_weekday:
            return False
        if event.repeat_week == -1:
            return d.month != (d + timedelta(days=7)).month
        return (d.day - 1) // 7 + 1 == event.repeat_week
    if event.repeats == MONTHLY_DATE:  # the 31st in a short month falls on its last day
        return d.day == min(event.repeat_day, calendar.monthrange(d.year, d.month)[1])
    return False


def next_meeting(event, now: datetime | None = None) -> datetime | None:
    """When it next meets, in the event's zone; None when it says no pattern."""
    from .roster import display_zone

    if not event.repeats or event.meets_at is None:
        return None
    zone = display_zone(event)
    now = (now or timezone.now()).astimezone(zone)
    for i in range(0, 63):  # every pattern recurs within two months
        d = now.date() + timedelta(days=i)
        at = datetime.combine(d, event.meets_at, tzinfo=zone)
        if _on(event, d) and at >= now:
            return at
    return None


def describe(event, now: datetime | None = None) -> str:
    """The line members read: "Tuesdays, 8:00 PM EST", "First Monday of the month, 7:00 PM EST",
    "The 15th of every month, 7:00–9:00 PM EDT". The zone is named as it reads at the next
    meeting, so it follows summer time. "" with no pattern."""
    nxt = next_meeting(event, now)
    if nxt is None:
        return ""
    if event.repeats == WEEKLY:
        when = f"{DAYS[event.repeat_weekday]}s"
    elif event.repeats == MONTHLY_WEEKDAY:
        week = dict(WEEKS)[event.repeat_week]
        when = f"{week} {DAYS[event.repeat_weekday]} of the month"
    else:
        when = f"The {_ordinal(event.repeat_day)} of every month"
    hours = twelve_hour(event.meets_at)
    if event.meets_until:
        end = twelve_hour(event.meets_until)
        same = hours[-2:] == end[-2:]  # 7:00–9:00 PM, but 11:00 AM–1:00 PM
        hours = f"{hours[:-3] if same else hours}–{end}"
    return f"{when}, {hours} {nxt.strftime('%Z')}"


_DAY = r"\b(mon|tues?|wed(?:nes)?|thu(?:rs)?|fri|sat(?:ur)?|sun)(?:day)?s?\b"
_WEEK = {"first": 1, "1st": 1, "second": 2, "2nd": 2, "third": 3, "3rd": 3, "fourth": 4, "4th": 4}
_WEEK |= {"last": -1}
_FILLER = r"\b(every|each|at|on|of|the|month|monthly|weekly|from|to|until|[ecmp][sd]t|et|ct|mt|pt|utc|z)\b"


def parse(text: str) -> tuple[dict, str]:
    """Fields read from free text such as "Tuesdays 20:00 ET", "First Monday 7pm" or "15th of
    the month 19:00", and the note to keep: "" when everything was read, else the whole text.
    ({}, text) when no pattern and time can be read; nothing is guessed."""
    s = " ".join(text.lower().split())
    day = re.search(_DAY, s)
    week = re.search(r"\b(first|second|third|fourth|last|1st|2nd|3rd|4th)\b", s)
    date_ = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)\b", s)
    at = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b|\b(\d{1,2}):(\d{2})\b", s)
    if not at:
        return {}, text
    if at.group(1):
        h, m = int(at.group(1)) % 12 + (12 if at.group(3) == "pm" else 0), int(at.group(2) or 0)
    else:
        h, m = int(at.group(4)), int(at.group(5))
    if h > 23 or m > 59:
        return {}, text
    fields = {"meets_at": time(h, m)}
    used = [at]
    if day:
        weekday = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"].index(day.group(1)[:3])
        fields["repeat_weekday"] = weekday
        used.append(day)
        if week:
            fields |= {"repeats": MONTHLY_WEEKDAY, "repeat_week": _WEEK[week.group(1)]}
            used.append(week)
        else:
            fields["repeats"] = WEEKLY
    elif date_ and 1 <= int(date_.group(1)) <= 31:
        fields |= {"repeats": MONTHLY_DATE, "repeat_day": int(date_.group(1))}
        used.append(date_)
    else:
        return {}, text
    rest = s
    for m_ in sorted(used, key=lambda x: -x.start()):
        rest = rest[: m_.start()] + " " + rest[m_.end() :]
    rest = re.sub(_FILLER, " ", rest)
    return fields, ("" if not re.sub(r"[\s,.:;–-]", "", rest) else text)
