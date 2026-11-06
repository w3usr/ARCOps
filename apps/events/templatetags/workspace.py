"""The event as a workspace (#232, SK 2026-11-06, D8): one header for the event page, every Manage
step and Who took part. The title with its state badge, a line of facts, a captain's actions at
the right (Announce, and a ⋮ menu of what the event's state allows), and the three as tabs."""

from django import template
from django.utils import timezone

register = template.Library()


@register.inclusion_tag("events/_event_header.html", takes_context=True)
def event_header(context, event, tab: str, prefix: str = ""):
    """`tab` is roster, manage or people; `prefix` goes before the title for a screen reader and
    the scenario scripts ("Manage", "Who took part"), and is not shown."""
    from ..models import Slot

    user = context["request"].user
    captain = user.is_authenticated and user.can_captain(event)
    periods = list(event.periods.order_by("start"))
    start, end = (periods[0].start, periods[-1].end) if periods else (None, None)
    now = timezone.now()
    locations = list(event.locations.all())
    slots = (
        Slot.objects.filter(position__location__event=event, cancelled=False).count()
        if captain
        else 0
    )
    return {
        "event": event,
        "tab": tab,
        "prefix": prefix,
        "captain": captain,
        "start": start,
        "end": end,
        "upcoming": bool(start and now < start),
        "running": bool(start and start <= now < end),
        "place": locations[0].name if len(locations) == 1 else "",
        "places": len(locations),
        "slots": slots,
        "captains": event.captaincies.count() if captain else 0,
        "request": context["request"],
        "csrf_token": context.get("csrf_token"),
    }
