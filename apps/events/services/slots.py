"""Slot generation (FR-46 to FR-48) and event health (FR-66)."""

from __future__ import annotations

from datetime import timedelta

from django.template.defaultfilters import pluralize

from ..models import OnAirRange, Slot
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
    (start, end) datetimes to fill; otherwise the event's on-air hours (#247), which are the whole
    periods unless the club has chosen otherwise.
    Setup slots go before the first period and breakdown slots after the last (FR-47)."""
    return [
        Slot.objects.create(position=pos, start=a, end=b, kind=kind)
        for pos, a, b, kind in plan_slots(
            event, positions, minutes, setup_slots, breakdown_slots, windows
        )
    ]


def plan_slots(
    event, positions, minutes=60, setup_slots=0, breakdown_slots=0, windows=None, fill=False
):
    """(position, start, end, kind) for each slot the generator would make, without making any:
    what generating and filling create, and what the preview counts (#168), from one place.
    With `fill`, only the hours no slot covers, and no setup or breakdown (#153)."""
    step = timedelta(minutes=minutes)
    spans = windows or on_air(event)
    for pos in positions:
        for start, end in empty_hours(pos, spans) if fill else spans:
            for a, b in _cut(start, end, step):
                yield pos, a, b, "operating"
        if fill or not spans:
            continue
        first, last = min(s for s, _ in spans), max(e for _, e in spans)
        for i in range(setup_slots):
            yield pos, first - step * (i + 1), first - step * i, "setup"
        for i in range(breakdown_slots):
            yield pos, last + step * i, last + step * (i + 1), "breakdown"


def describe(
    event, positions, minutes=60, setup_slots=0, breakdown_slots=0, windows=None, fill=False
) -> str:
    """The line the generator shows before anything is made (#168): how many slots, per position
    and across positions; or, filling, how many go into the empty hours. ponytail: per position
    as the first position has it, which is every position's count when generating."""
    planned = list(
        plan_slots(event, positions, minutes, setup_slots, breakdown_slots, windows, fill)
    )
    n = len(planned)
    if fill:
        if not n:
            return "Every hour already has a slot; nothing would be added."
        return f"Adds {n} slot{pluralize(n)} to the empty hours."
    positions = list(positions)
    each = sum(1 for p, *_ in planned if p == positions[0]) if positions else 0
    kinds = [
        f"a {kind}" if count == 1 else f"{count} {kind}"
        for kind, count in (("setup", setup_slots), ("breakdown", breakdown_slots))
        if count
    ]
    many = pluralize(max(setup_slots, breakdown_slots))
    tail = f", including {' and '.join(kinds)} slot{many} each" if kinds else ""
    return (
        f"{n} slot{pluralize(n)}: {each} per position × {len(positions)} "
        f"position{pluralize(len(positions))}{tail}."
    )


def _cut(start, end, step):
    """Consecutive (start, end) pieces of `step`, the last one short if it does not divide."""
    t = start
    while t < end:
        yield t, min(t + step, end)
        t = min(t + step, end)


SHORTEST = timedelta(minutes=15)  # the generator form's minimum slot length


def empty_hours(position, spans) -> list[tuple]:
    """The parts of `spans` that no slot of `position` covers. A canceled slot still covers its
    time: a cancellation is a decision a bulk fill should not undo (SK, 2026-11-03). Pieces
    shorter than SHORTEST are left out, so a grid of other lengths does not leave slivers."""
    taken = sorted(position.slots.values_list("start", "end"))
    out = []
    for start, end in spans:
        t = start
        for a, b in taken:
            if b <= t or a >= end:
                continue
            if a - t >= SHORTEST:
                out.append((t, a))
            t = max(t, b)
        if end - t >= SHORTEST:
            out.append((t, end))
    return out


def fill_empty_hours(event, positions, minutes: int = 60, windows=None) -> list[Slot]:
    """#153 (FR-46, FR-48): operating slots for the on-air hours (or `windows`) that
    have no slot yet, position by position. Every existing slot, its seats and its sign-ups stay
    as they are, so this runs after people have signed up: a range or a period added later, or a
    new position, gets its slots. Setup and breakdown are left to Add a slot (SK, 2026-11-03)."""
    return [
        Slot.objects.create(position=pos, start=a, end=b, kind=kind)
        for pos, a, b, kind in plan_slots(event, positions, minutes, windows=windows, fill=True)
    ]


# ------------------------------------------------------------- on-air hours (#247, A15) ---

HOUR = timedelta(hours=1)


def merge(spans) -> list[tuple]:
    """Sorted, with overlapping and touching spans joined."""
    out: list[list] = []
    for a, b in sorted(spans):
        if a >= b:
            continue
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [tuple(x) for x in out]


def clip(spans, bounds) -> list[tuple]:
    """The parts of `spans` inside `bounds`, merged."""
    return merge(
        (max(a, c), min(b, d)) for a, b in spans for c, d in bounds if max(a, c) < min(b, d)
    )


def periods_of(event) -> list[tuple]:
    return merge((p.start, p.end) for p in event.periods.all())


def chosen(event) -> list[tuple]:
    """The club's own stretches, clipped to the periods; [] when it has chosen none."""
    return clip([(r.start, r.end) for r in event.on_air_ranges.all()], periods_of(event))


def on_air(event) -> list[tuple]:
    """When the club means to be on the air: its chosen stretches, or the whole of the periods
    (the contest's span) when it has chosen none."""
    return chosen(event) or periods_of(event)


def set_on_air(event, spans) -> list[tuple]:
    """Store `spans` as the event's on-air hours, clipped and merged. Stretches that come to the
    whole of the periods are stored as nothing, which means the same and follows the periods if
    they change. Slots are never touched."""
    periods = periods_of(event)
    spans = clip(spans, periods)
    OnAirRange.objects.filter(event=event).delete()
    if spans and spans != periods:
        OnAirRange.objects.bulk_create(OnAirRange(event=event, start=a, end=b) for a, b in spans)
    return spans if spans != periods else []


def hour_grid(event) -> list[dict]:
    """The on-air hours as a grid: a row per UTC day the periods touch, a box per hour of it.
    A box is None where the hour is outside every period; otherwise its instant and whether it
    is on the air: "all", "part" (a stretch typed to the minute starts or ends inside it) or ""."""
    from datetime import UTC, datetime, time

    periods, live = periods_of(event), on_air(event)
    if not periods:
        return []
    day, last = periods[0][0].astimezone(UTC).date(), periods[-1][1].astimezone(UTC).date()
    rows = []
    while day <= last:
        boxes = []
        for h in range(24):
            t = datetime.combine(day, time(h), tzinfo=UTC)
            inside = clip([(t, t + HOUR)], periods)
            if not inside:
                boxes.append(None)
                continue
            have = sum(((b - a) for a, b in clip(inside, live)), timedelta())
            want = sum(((b - a) for a, b in inside), timedelta())
            boxes.append({"at": t, "on": "all" if have == want else ("part" if have else "")})
        if any(boxes):
            rows.append({"day": day, "boxes": boxes})
        day += timedelta(days=1)
    return rows


def from_ticks(event, ticked: set) -> list[tuple]:
    """The on-air hours the grid was saved with: each ticked hour box, inside the periods. A box
    that was partly on the air and stays ticked keeps the part it had, so saving the grid never
    widens a stretch someone typed to the minute."""
    periods, live, out = periods_of(event), on_air(event), []
    for row in hour_grid(event):
        for box in row["boxes"]:
            if not box or box["at"] not in ticked:
                continue
            inside = clip([(box["at"], box["at"] + HOUR)], periods)
            out += clip(inside, live) if box["on"] == "part" else inside
    return merge(out)


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
