"""
The roster as the reader sees it (design run of 2026-09-13, second round).

Everything the template needs is assembled here: slots grouped under day headings in the
leading zone, each with its hours in that zone and in the other; a grid (time down, one column
per position) when the event has up to four positions, a list otherwise; and a status phrased
as what the slot needs from the reader, never as a verdict on it. FR-36 makes the event's zone
(falling back to the club's) the display zone, so it leads and UTC follows unless the viewer
swaps them.

The viability engine (viability.evaluate) is unchanged; this module only re-words its result.
Red is reserved for a captain looking at a slot that has people in it, still cannot operate,
and starts within two days.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.utils import timezone

from apps.ops.config import setting

from ..models import Event, Position, SignUp, Slot
from .viability import evaluate

GRID_MAX_POSITIONS = 4
UTC = ZoneInfo("UTC")


def display_zone(event: Event) -> ZoneInfo:
    name = event.display_timezone or setting("club.timezone", "UTC") or "UTC"
    try:
        return ZoneInfo(name)
    except Exception:  # noqa: BLE001 - a misconfigured zone name must not take the page down
        return UTC


def zone_label(dt: datetime, zone: ZoneInfo) -> str:
    """'EDT', 'UTC': what the reader recognises, not the IANA name."""
    return dt.astimezone(zone).strftime("%Z") or str(zone)


@dataclass
class Presentation:
    key: str  # open | needs | covered | thin | full | closed | not_open | problem
    word: str
    detail: str = ""

    @property
    def tone(self) -> str:  # low: covered, but below the event's preferred class (FR-61)
        return {
            "open": "open",
            "needs": "warn",
            "covered": "ok",
            "thin": "ok",
            "low": "warn",
            "full": "muted",
            "closed": "muted",
            "not_open": "muted",
            "problem": "bad",
        }[self.key]


def _needs_from_reasons(reasons: list[str]) -> list[str]:
    out = []
    for r in reasons:
        if r.startswith("nobody with "):
            out.append("someone with " + r[len("nobody with ") :])
        elif r.endswith("has no responsible adult designated"):
            out.append("a responsible adult for " + r.split(" (under 18)")[0])
        elif r.startswith("depends on ") and r.endswith(" alone"):
            out.append("one more person alongside " + r[len("depends on ") : -len(" alone")])
        elif r != "no one signed up":
            out.append(r)
    return out


def present(
    slot: Slot,
    status,
    signups: list[SignUp],
    open_roles: list[str],
    *,
    published: bool,
    is_captain: bool,
    now: datetime,
) -> Presentation:
    if slot.closed:
        return Presentation("closed", "Closed")
    if not signups:
        if not published:
            return Presentation("not_open", "Opens when published")
        return Presentation("open", "Open", "sign up")
    needs = _needs_from_reasons(status.reasons)
    if status.status == "not_viable":
        soon = slot.start - now <= timedelta(hours=48)
        key = "problem" if (is_captain and soon) else "needs"
        return Presentation(key, "Needs " + (needs[0] if needs else "more"), "; ".join(needs[1:]))
    low = getattr(status, "below_preferred", None)
    if low:  # FR-61: viable, with the warning; it may also depend on one person
        detail = f"below preferred class ({low})"
        if status.status == "at_risk" and needs:
            detail += "; " + needs[0]
        return Presentation("low", "Covered", detail)
    if status.status == "at_risk":
        return Presentation("thin", "Covered", needs[0] if needs else "")
    if open_roles and published:
        return Presentation("covered", "Covered", "room for more")
    if not open_roles and published:
        return Presentation("full", "Full")
    return Presentation("covered", "Covered")


@dataclass
class Cell:
    slot: Slot
    signups: list[SignUp]
    open_roles: list[str]
    mine: SignUp | None
    status: object
    shown: Presentation
    control_operator: object = None

    @property
    def class_counts(self) -> str:
        """FR-121: what a Provisional member sees of a slot's people, e.g. '1 G, 2 U'."""
        order = "EAGTNU"
        counts: dict[str, int] = {}
        for su in self.signups:
            letter = su.user.license_letter
            counts[letter] = counts.get(letter, 0) + 1
        return ", ".join(f"{counts[k]} {k}" for k in order if k in counts)


@dataclass
class Row:
    start: datetime
    end: datetime
    lead_range: str
    other_range: str
    kind: str
    cells: list[Cell | None] = field(default_factory=list)  # one per position in grid layout


@dataclass
class Day:
    key: str
    heading: str
    rows: list[Row] = field(default_factory=list)


def _hours(start: datetime, end: datetime, zone: ZoneInfo, with_day: bool) -> str:
    s, e = start.astimezone(zone), end.astimezone(zone)
    text = f"{s:%H:%M}–{e:%H:%M}"
    if with_day:
        text = f"{s:%a} {text}"
    return f"{text} {zone_label(start, zone)}"


def build(event: Event, viewer, lead: str = "local", now: datetime | None = None) -> dict:
    now = now or timezone.now()
    local = display_zone(event)
    lead_zone, other_zone = (local, UTC) if lead == "local" or local == UTC else (UTC, local)
    if lead == "utc":
        lead_zone, other_zone = UTC, local
    is_captain = viewer.can_captain(event)
    published = event.state == Event.State.PUBLISHED

    positions = list(
        Position.objects.filter(location__event=event)
        .select_related("location")
        .order_by("location__order", "order")
    )
    slots = list(
        Slot.objects.filter(position__location__event=event, cancelled=False)
        .select_related("position", "position__location", "control_operator")
        .prefetch_related(
            "signups__user", "signups__user__license", "signups__responsible_adults", "capacities"
        )
        .order_by("start", "position__location__order", "position__order")
    )
    mine = {su.slot_id: su for su in SignUp.objects.filter(user=viewer, slot__in=slots)}

    cells: dict[int, Cell] = {}
    counts = {"total": 0, "open": 0, "covered": 0, "needs": 0, "closed": 0}
    for s in slots:
        st = evaluate(s)
        signups = list(s.signups.all())
        caps = {c.role: c.capacity for c in s.capacities.all()}
        taken: dict[str, int] = {}
        for su in signups:
            taken[su.role] = taken.get(su.role, 0) + 1
        open_roles = [r for r, c in caps.items() if taken.get(r, 0) < c]
        shown = present(
            s, st, signups, open_roles, published=published, is_captain=is_captain, now=now
        )
        cells[s.pk] = Cell(
            s, signups, open_roles, mine.get(s.pk), st, shown, getattr(st, "control_operator", None)
        )
        counts["total"] += 1
        bucket = {
            "open": "open",
            "not_open": "open",
            "covered": "covered",
            "thin": "covered",
            "low": "covered",
            "full": "covered",
            "needs": "needs",
            "problem": "needs",
            "closed": "closed",
        }[shown.key]
        counts[bucket] += 1

    layout = "grid" if 1 <= len(positions) <= GRID_MAX_POSITIONS else "list"
    pos_index = {p.pk: i for i, p in enumerate(positions)}

    days: dict[str, Day] = {}
    rows_by_span: dict[tuple, Row] = {}
    for s in slots:
        lead_start = s.start.astimezone(lead_zone)
        day_key = lead_start.strftime("%Y-%m-%d")
        day = days.setdefault(day_key, Day(day_key, lead_start.strftime("%A %-d %B")))
        span = (s.start, s.end, s.kind) if layout == "grid" else (s.start, s.end, s.kind, s.pk)
        row = rows_by_span.get(span)
        if row is None:
            row = Row(
                s.start,
                s.end,
                _hours(s.start, s.end, lead_zone, with_day=False),
                _hours(s.start, s.end, other_zone, with_day=True),
                s.kind,
                cells=[None] * len(positions) if layout == "grid" else [],
            )
            rows_by_span[span] = row
            day.rows.append(row)
        if layout == "grid":
            row.cells[pos_index[s.position_id]] = cells[s.pk]
        else:
            row.cells.append(cells[s.pk])

    single_location = len({p.location_id for p in positions}) == 1
    starts, ends = event.starts_at(), event.ends_at()
    return {
        "names_visible": viewer.is_member,  # FR-121: Provisional members see counts, not names
        "layout": layout,
        "positions": positions,
        "single_location": positions[0].location if positions and single_location else None,
        "days": list(days.values()),
        "counts": counts,
        "lead": "utc" if lead_zone == UTC else "local",
        "lead_label": zone_label(now, lead_zone),
        "other_label": zone_label(now, other_zone),
        "span": {
            "lead": f"{starts.astimezone(lead_zone):%a %-d %b %H:%M} – {ends.astimezone(lead_zone):%a %-d %b %H:%M} {zone_label(starts, lead_zone)}"
            if starts and ends
            else "",
            "other": f"{starts.astimezone(other_zone):%a %-d %b %H:%M} – {ends.astimezone(other_zone):%a %-d %b %H:%M} {zone_label(starts, other_zone)}"
            if starts and ends
            else "",
        },
        "roles": setting("slot_roles", []) or [],
        "is_captain": is_captain,
        "published": published,
    }


def cell_for(slot: Slot, viewer, lead: str = "local") -> tuple[Cell, dict]:
    """One slot's cell plus the zone strings the slot page shows; built through `build` so the
    wording is identical to the roster's."""
    data = build(slot.event, viewer, lead)
    for day in data["days"]:
        for row in day.rows:
            for c in row.cells:
                if c and c.slot.pk == slot.pk:
                    return c, {**data, "row": row}
    raise ValueError("slot is not on the roster")
