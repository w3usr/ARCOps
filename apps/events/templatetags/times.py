"""
`{% when start end event %}`: a time or span in the event's zone with UTC alongside (FR-36),
the lead zone following the member's roster preference. One tag, so Home, Events, My Sked, and
the roster agree on how a time looks. NAF, 2026-09-14, on seeing a bare "Sat 26 Sep 2026 00:00":
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
    request = context.get("request")
    lead = request.session.get("roster_tz", "local") if request and hasattr(request, "session") else "local"
    local = display_zone(event) if event is not None else UTC
    if local == UTC:
        return format_html('<span class="when1">{}</span>', _one(start, end, UTC, year))
    lead_zone, other = (UTC, local) if lead == "utc" else (local, UTC)
    return format_html(
        '<span class="when1">{}</span><span class="when2 muted">{}</span>',
        _one(start, end, lead_zone, year),
        _one(start, end, other, year),
    )
