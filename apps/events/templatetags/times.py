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

from ..services.roster import UTC, display_zone, zone_label

register = template.Library()


def _one(start: datetime, end: datetime | None, zone, with_year: bool) -> str:
    s = start.astimezone(zone)
    day = "%a %-d %b %Y" if with_year else "%a %-d %b"
    if end is None:
        return f"{s:{day} %H:%M} {zone_label(start, zone)}"
    e = end.astimezone(zone)
    if s.date() == e.date():
        return f"{s:{day} %H:%M}–{e:%H:%M} {zone_label(start, zone)}"
    return f"{s:{day} %H:%M} – {e:{day} %H:%M} {zone_label(start, zone)}"


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
