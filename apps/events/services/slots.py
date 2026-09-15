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
    report = limit_report(event)
    return {
        "counts": counts,
        "scheduled_hours": round(hours, 1),
        "over_total_limit": report["over_total"],
        "limits": report,
    }


# ------------------------------------------------------ operating limits (FR-39, FR-48) ---


def _basis_zone(event):
    from .roster import UTC, display_zone

    limit = getattr(event, "limit", None)
    return display_zone(event) if (limit and limit.day_basis == "local") else UTC


def windows_from_daily(event, ranges: list[tuple[str, str]]) -> list[tuple]:
    """FR-48: the officer names the hours to operate on each day ("15:00-21:00", in the limit's
    day basis); the generator fills only those hours, clipped to the operating periods. Returns
    (start, end) instants."""
    from datetime import datetime, time

    zone = _basis_zone(event)
    out = []
    for p in event.periods.all():
        day = p.start.astimezone(zone).date()
        last = p.end.astimezone(zone).date()
        while day <= last:
            for a, b in ranges:
                ha, ma = (int(x) for x in a.split(":"))
                hb, mb = (int(x) for x in b.split(":"))
                ws = datetime.combine(day, time(ha, ma), tzinfo=zone)
                we = datetime.combine(day, time(hb, mb), tzinfo=zone)
                if we <= ws:
                    we += timedelta(days=1)
                start, end = max(ws, p.start), min(we, p.end)
                if start < end:
                    out.append((start, end))
            day += timedelta(days=1)
    return sorted(set(out))


def limit_report(event) -> dict:
    """FR-39, FR-62: operating hours per day against the per-day limit and in total against the
    total limit; the slots that push a day or the event over are named. Advisory only."""
    limit = getattr(event, "limit", None)
    zone = _basis_zone(event)
    per_day: dict[str, float] = {}
    over_ids: set[int] = set()
    total = 0.0
    day_max = float(limit.max_hours_per_day) if (limit and limit.max_hours_per_day) else None
    total_max = float(limit.max_total_hours) if (limit and limit.max_total_hours) else None
    for s in Slot.objects.filter(
        position__location__event=event, kind="operating", cancelled=False
    ).order_by("start", "position_id"):
        hours = (s.end - s.start).total_seconds() / 3600
        key = s.start.astimezone(zone).strftime("%Y-%m-%d")
        before_day = per_day.get(key, 0.0)
        per_day[key] = before_day + hours
        total += hours
        if (day_max is not None and per_day[key] > day_max + 1e-9) or (
            total_max is not None and total > total_max + 1e-9
        ):
            over_ids.add(s.pk)
    days = [
        {
            "day": k,
            "hours": round(v, 1),
            "limit": day_max,
            "over": day_max is not None and v > day_max + 1e-9,
        }
        for k, v in sorted(per_day.items())
    ]
    return {
        "days": days,
        "total": round(total, 1),
        "total_limit": total_max,
        "over_total": total_max is not None and total > total_max + 1e-9,
        "over_slot_ids": over_ids,
        "basis": "local" if zone.key != "UTC" else "UTC",
        "min_break": limit.min_break_minutes if limit else None,
    }
