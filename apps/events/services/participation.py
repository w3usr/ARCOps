"""Participation report (FR-86): what the club reports to the University and puts in a grant
application, so it should be right. Per event and per operating period: hours scheduled,
covered, and viable; people scheduled and checked in; first-time participants."""

from __future__ import annotations

from ..models import Event, SignUp, Slot
from .viability import evaluate


def _hours(slots) -> float:
    return round(sum((s.end - s.start).total_seconds() for s in slots) / 3600, 1)


def participation(event: Event) -> dict:
    slots = list(
        Slot.objects.filter(position__location__event=event, cancelled=False, kind="operating")
        .prefetch_related("signups__user", "signups__user__license", "signups__responsible_adults")
        .order_by("start")
    )
    periods = list(event.periods.order_by("start"))
    people = {}
    first_timers = set()
    for s in slots:
        for su in s.signups.all():
            people.setdefault(su.user_id, {"user": su.user, "scheduled": 0, "checked_in": 0})
            people[su.user_id]["scheduled"] += 1
            if su.checked_in_at and not su.no_show:
                people[su.user_id]["checked_in"] += 1
    # first-timers: checked in here and never checked in to an earlier event
    for pk, p in people.items():
        if p["checked_in"]:
            earlier = (
                SignUp.objects.filter(
                    user_id=pk,
                    checked_in_at__isnull=False,
                    no_show=False,
                    slot__start__lt=slots[0].start if slots else None,
                )
                .exclude(slot__position__location__event=event)
                .exists()
            )
            if not earlier:
                first_timers.add(pk)

    def block(sub):
        covered = [s for s in sub if s.signups.exists()]
        viable = [
            s for s in sub if evaluate(s, list(s.signups.all())).status in ("viable", "at_risk")
        ]
        checked = {
            su.user_id for s in sub for su in s.signups.all() if su.checked_in_at and not su.no_show
        }
        scheduled = {su.user_id for s in sub for su in s.signups.all()}
        return {
            "slots": len(sub),
            "hours_scheduled": _hours(sub),
            "hours_covered": _hours(covered),
            "hours_viable": _hours(viable),
            "people_scheduled": len(scheduled),
            "people_checked_in": len(checked),
        }

    rows = []
    for p in periods:
        sub = [s for s in slots if p.start <= s.start < p.end]
        rows.append({"period": p, **block(sub)})
    total = block(slots)
    total["first_timers"] = len(first_timers)
    return {
        "event": event,
        "periods": rows,
        "total": total,
        "people": sorted(
            people.values(), key=lambda x: (x["user"].last_name, x["user"].first_name)
        ),
        "first_timer_ids": first_timers,
    }
