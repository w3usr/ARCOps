"""Slot generation (FR-46 to FR-48) and event health (FR-66)."""

from __future__ import annotations

from datetime import timedelta

from ..models import Slot
from .viability import evaluate


def generate_slots(
    event,
    positions,
    minutes: int = 60,
    setup_slots: int = 0,
    breakdown_slots: int = 0,
    windows=None,
):
    """Fill each operating period with slots of `minutes`, aligned to the period start, with a
    final short slot if the period length is not a multiple. `windows`, when given, is a list of
    (start, end) datetimes to fill instead of the whole periods (FR-48, for hour-limited events).
    Setup slots go before the first period and breakdown slots after the last (FR-47)."""
    step = timedelta(minutes=minutes)
    spans = windows or [(p.start, p.end) for p in event.periods.all()]
    created: list[Slot] = []
    for pos in positions:
        for start, end in spans:
            t = start
            while t < end:
                nxt = min(t + step, end)
                created.append(
                    Slot.objects.create(position=pos, start=t, end=nxt, kind="operating")
                )
                t = nxt
        first = min(s for s, _ in spans) if spans else None
        last = max(e for _, e in spans) if spans else None
        for i in range(setup_slots):
            created.append(
                Slot.objects.create(
                    position=pos, start=first - step * (i + 1), end=first - step * i, kind="setup"
                )
            )
        for i in range(breakdown_slots):
            created.append(
                Slot.objects.create(
                    position=pos, start=last + step * i, end=last + step * (i + 1), kind="breakdown"
                )
            )
    return created


def scheduled_hours(event) -> float:
    total = timedelta()
    for s in Slot.objects.filter(
        position__location__event=event, kind="operating", cancelled=False
    ):
        total += s.end - s.start
    return total.total_seconds() / 3600


def health(event) -> dict:
    """FR-66: counts by status, hours against limits."""
    counts = {"total": 0, "empty": 0, "not_viable": 0, "viable": 0, "at_risk": 0}
    for slot in Slot.objects.filter(
        position__location__event=event, cancelled=False
    ).prefetch_related("signups__user"):
        counts["total"] += 1
        counts[evaluate(slot).status] += 1
    hours = scheduled_hours(event)
    limit = getattr(event, "limit", None)
    over = bool(limit and limit.max_total_hours and hours > float(limit.max_total_hours))
    return {"counts": counts, "scheduled_hours": round(hours, 1), "over_total_limit": over}
