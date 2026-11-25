"""
How a time reads on a page. **For now, the viewer's own time only, never UTC** (functional
addendum A38, superseding A12's UTC first for pages): the filters keep
their old names so the change is easy to undo, and each prints a `<time>` whose `datetime` is
ISO 8601 in UTC. The viewer's zone comes from the `tz` cookie (apps/ops/middleware.py).
`utc_record` keeps UTC for the signed agreement's PDF, a record that must read the same for
everyone.
"""

from __future__ import annotations

from datetime import datetime

from django import template
from django.utils.html import format_html

from apps.ops import when as when_

register = template.Library()


def _mark(t: datetime, text: str):
    return format_html('<time datetime="{}">{}</time>', t.astimezone(when_.UTC).isoformat(), text)


def _at(t, year: bool):
    got = when_._instant(t) if t not in (None, "") else None
    if not isinstance(got, datetime):
        return when_.day(t)  # a date with no time, or nothing
    got = got if got.tzinfo else got.replace(tzinfo=when_.UTC)
    return _mark(got, when_.local(got, year=year))


@register.filter
def utc_time(t):
    """`Sat, Nov 21, 2026, 4:00 PM EST` in the viewer's zone (A38)."""
    return _at(t, year=True)


@register.filter
def utc_time_short(t):
    """`Sat, Nov 21, 4:00 PM EST`, for rows and lists where the event gives the year (A38)."""
    return _at(t, year=False)


@register.filter
def utc_record(t):
    """`Sat 21 Nov 2026 21:00 UTC`, for the agreement PDF only."""
    return when_.utc(t)


@register.filter
def plain_day(d):
    """`21 Nov 2026`: a plain date, or an instant's UTC date."""
    return when_.day(d)


@register.simple_tag
def utc_span(start, end, year=True):
    """`Sat, Nov 21, 2026, 4:00–6:00 PM EST` in the viewer's zone (A38)."""
    return _mark(start, when_.local_span(start, end, year=year)) if start and end else ""


@register.simple_tag
def when(start, end=None, event=None, year=False):
    """A time or span in the viewer's zone, one line (A38). `event` is no longer read: the
    viewer's zone, not the event's, is the one shown."""
    if not start:
        return ""
    text = when_.local(start, year=year) if end is None else when_.local_span(start, end, year=year)
    return format_html('<span class="when1">{}</span>', _mark(start, text))


@register.filter
def checkin_label(signup) -> str:
    """`Check in`, or `Check in, 5:00–7:00 PM (2 slots)` when one tap checks in a run (A42)."""
    run = signup.checkin_run()
    if len(run) == 1:
        return "Check in"
    return f"Check in, {when_.clock_span(signup.slot.start, run[-1].slot.end)} ({len(run)} slots)"


@register.filter
def meets_line(event) -> str:
    """When a regular meeting or net meets, as members read it."""
    from ..services.meets import describe

    return describe(event)


@register.filter
def next_meets(event) -> str:
    """ "Tue, Nov 24, 8:00 PM EST": its next meeting, in its own zone, as every local time
    reads (apps/ops/when.py); "" with no pattern."""
    from ..services.meets import next_meeting

    at = next_meeting(event)
    return when_.local(at, at.tzinfo) if at else ""
