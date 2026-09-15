"""The mentor-needs page (FR-123): upcoming events with open Mentor seats, no person named."""

from __future__ import annotations

from django.utils import timezone

from apps.ops.config import setting

from ..models import Event, Slot
from .roster import display_zone, zone_label


def mentor_role_key() -> str:
    for r in setting("slot_roles", []) or []:
        if r.get("requires_license"):
            return r["key"]
    return "mentor"


def mentor_needs(*, viewer_is_member: bool) -> list[dict]:
    now = timezone.now()
    role = mentor_role_key()
    out = []
    for ev in Event.objects.filter(state=Event.State.PUBLISHED).order_by("id"):
        if not ev.ends_at() or ev.ends_at() < now:
            continue
        zone = display_zone(ev)
        slots = (
            Slot.objects.filter(position__location__event=ev, cancelled=False, closed=False, kind="operating", end__gte=now)
            .prefetch_related("signups", "capacities")
            .order_by("start")
        )
        rows = []
        open_total = 0
        for s in slots:
            cap = next((c.capacity for c in s.capacities.all() if c.role == role), 0)
            taken = sum(1 for su in s.signups.all() if su.role == role)
            open_seats = max(0, cap - taken)
            if open_seats:
                open_total += open_seats
                rows.append({
                    "slot": s,
                    "open": open_seats,
                    "lead": f"{s.start.astimezone(zone):%a %-d %b %H:%M}–{s.end.astimezone(zone):%H:%M} {zone_label(s.start, zone)}",
                    "utc": f"{s.start:%a %H:%M}–{s.end:%H:%M} UTC",
                })
        if not rows:
            continue
        loc = ev.locations.order_by("order").first()
        out.append({
            "event": ev,
            "open_total": open_total,
            "rows": rows,
            "where": (loc.name if loc else "") if viewer_is_member else f"the {setting('club.short_name', 'club')} station",
            "preferred_class": ev.min_license_class,
            "span": f"{ev.starts_at().astimezone(zone):%a %-d %b %H:%M} – {ev.ends_at().astimezone(zone):%a %-d %b %H:%M} {zone_label(ev.starts_at(), zone)}",
            "span_utc": f"{ev.starts_at():%a %-d %b %H:%M} – {ev.ends_at():%a %-d %b %H:%M} UTC",
        })
    return out
