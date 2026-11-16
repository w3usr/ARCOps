"""
`{% when start end event %}`: a time or span in UTC with the event's zone beneath (FR-36,
FR-38); UTC leads everywhere, as on the roster (functional addendum A12). One tag, so Home,
Events, My schedule, and the roster agree on how a time looks. NAF, 2026-09-14, on seeing a bare "Sat 26 Sep 2026 00:00":
"this needs time zone indicated. It should be in both utc and local".
"""

from __future__ import annotations

from datetime import datetime

from django import template
from django.utils.html import format_html

from apps.ops import when as when_

from ..services.roster import UTC, display_zone

register = template.Library()


@register.filter
def utc_time(t):
    """`Sat 21 Nov 2026 21:00 UTC` (#274)."""
    return when_.utc(t)


@register.filter
def utc_time_short(t):
    """`Sat 21 Nov 21:00 UTC`, for rows and lists where the event gives the year (#274)."""
    return when_.utc(t, year=False)


@register.filter
def plain_day(d):
    """`21 Nov 2026`: a plain date, or an instant's UTC date (#274)."""
    return when_.day(d)


@register.simple_tag
def utc_span(start, end, year=True):
    """`Sat 21 Nov 2026 21:00–23:00 UTC` (#274)."""
    return when_.utc_span(start, end, year) if start and end else ""


def _one(start: datetime, end: datetime | None, zone, with_year: bool) -> str:
    """UTC in the one form (apps/ops/when.py); the event's zone in the US convention beneath."""
    if zone == UTC:
        return when_.utc(start, with_year) if end is None else when_.utc_span(start, end, with_year)
    if end is None:
        return when_.local(start, zone, with_year)
    return when_.local_span(start, end, zone, with_year)


@register.simple_tag(takes_context=True)
def when(context, start, end=None, event=None, year=False):
    """Two lines: the lead zone in normal weight, the other zone beneath in muted small type."""
    if not start:
        return ""
    local = display_zone(event) if event is not None else UTC
    if local == UTC:
        return format_html('<span class="when1">{}</span>', _one(start, end, UTC, year))
    return format_html(
        '<span class="when1">{}</span><span class="when2 muted">{}</span>',
        _one(start, end, UTC, year),
        _one(start, end, local, year),
    )


@register.filter
def meets_line(event) -> str:
    """When a regular meeting or net meets, as members read it (private tracker 273)."""
    from ..services.meets import describe

    return describe(event)


@register.filter
def next_meets(event) -> str:
    """ "Tue 24 Nov, 8:00 PM EST": its next meeting, in its own zone; "" with no pattern."""
    from ..services.meets import _clock, next_meeting

    at = next_meeting(event)
    return f"{at:%a %-d %b}, {_clock(at.time())} {at:%Z}" if at else ""


@register.filter
def zone_name(event):
    """The event's own zone, `America/New_York`, for a time box's local clock (A35)."""
    return getattr(display_zone(event), "key", "UTC")
