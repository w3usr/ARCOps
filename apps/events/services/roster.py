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

from apps.credentials.services import holds
from apps.ops.config import setting

from ..models import Event, Position, SignUp, Slot
from .slots import limit_report
from .viability import evaluate, may_control, needs_from_reasons

GRID_MAX_POSITIONS = 4
UTC = ZoneInfo("UTC")


def display_zone(event: Event) -> ZoneInfo:
    name = event.display_timezone or setting("club.timezone", "UTC") or "UTC"
    try:
        return ZoneInfo(name)
    except Exception:  # noqa: BLE001 - a misconfigured zone name must not take the page down
        return UTC


def zone_label(dt: datetime, zone: ZoneInfo) -> str:
    """'EDT', 'UTC': what the reader recognizes, not the IANA name."""
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


def present(
    slot: Slot,
    status,
    signups: list[SignUp],
    open_roles: list[str],
    *,
    published: bool,
    is_captain: bool,
    now: datetime,
    locked: bool = False,
) -> Presentation:
    if slot.closed:
        return Presentation("closed", "Closed")
    if not signups:
        if locked:
            return Presentation("not_open", "Locked", "ask a captain")
        if not published:
            return Presentation("not_open", "Opens when published")
        return Presentation("open", "Open")  # the action is in the link's accessible name (#170)
    needs = needs_from_reasons(status.reasons)
    if status.status == "not_viable":
        soon = slot.start - now <= timedelta(hours=48)
        word = "Needs " + (needs[0] if needs else "more")
        if is_captain and soon:  # the captain's red says why in words, not color alone
            return Presentation("problem", word, "; ".join(["within 48 hours", *needs[1:]]))
        return Presentation("needs", word, "; ".join(needs[1:]))
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
    over_limit: bool = False  # FR-39, FR-62: pushes a day or the event past an operating limit
    # FR-65: signup pk -> compact credential badges, each a mark and its word: [("S", "station access")]
    badges: dict = field(default_factory=dict)
    co_choices: list = field(default_factory=list)  # FR-63: who a captain may name; captains only

    @property
    def class_counts(self) -> str:
        """FR-121: what a Provisional member sees of a slot's people, e.g. '1 G, 2 U'.

        C, R, and M are a club, a RACES station, and a military recreation station: the FCC
        gives none of them an operator class, so they sit below the ladder and above the
        people holding no license at all.
        """
        order = "EAGTNCRMU"
        counts: dict[str, int] = {}
        for su in self.signups:
            letter = su.user.license_letter
            counts[letter] = counts.get(letter, 0) + 1
        return ", ".join(f"{counts[k]} {k}" for k in order if k in counts)


@dataclass
class Fold:
    """A run of rows with every slot in them open, read as one row (#161): "06:00–14:00, 8 open
    hours", which opens in place to the hours themselves. Its rows stay on the page, hidden."""

    id: str
    lead_range: str
    other_range: str
    hours: float
    slots: int
    open: bool = False  # shown expanded: `?open=<id>`, or `?open=all`
    lead_hours: str = ""  # as Row's
    other_hours: str = ""


@dataclass
class Row:
    start: datetime
    end: datetime
    lead_range: str
    other_range: str
    kind: str
    cells: list[Cell | None] = field(default_factory=list)  # one per position in grid layout
    fold: Fold | None = None  # the run this row is folded into, if any
    fold_head: bool = False  # the run's first row, where its one line is drawn
    # The grid's own strings: the zone is named once, in the column's header, so a row names it
    # only where it differs from the header's, after a change of clocks (#161, section 5.9).
    lead_hours: str = ""
    other_hours: str = ""
    anchor: str = ""  # the first row at its start: where the coverage strip links to


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


# How a cell's state is counted in the event's coverage: the words on the roster, in four piles.
BUCKET = {
    "open": "open",
    "not_open": "open",
    "covered": "covered",
    "thin": "covered",
    "low": "covered",
    "full": "covered",
    "needs": "needs",
    "problem": "needs",
    "closed": "closed",
}


def coverage(event: Event, now: datetime | None = None) -> dict:
    """The roster's Coverage counts without the roster: how many slots are open, covered, need
    someone, or closed, worded as a member reads the roster. Home shows it for the next event a
    captain runs (#162)."""
    now = now or timezone.now()
    published = event.state == Event.State.PUBLISHED
    locked = event.state == Event.State.LOCKED
    counts = {"total": 0, "open": 0, "covered": 0, "needs": 0, "closed": 0}
    slots = Slot.objects.filter(position__location__event=event, cancelled=False).prefetch_related(
        "signups__user", "capacities"
    )
    for s in slots:
        signups = list(s.signups.all())
        taken: dict[str, int] = {}
        for su in signups:
            taken[su.role] = taken.get(su.role, 0) + 1
        open_roles = [c.role for c in s.capacities.all() if taken.get(c.role, 0) < c.capacity]
        shown = present(
            s,
            evaluate(s),
            signups,
            open_roles,
            published=published,
            is_captain=False,
            now=now,
            locked=locked,
        )
        counts["total"] += 1
        counts[BUCKET[shown.key]] += 1
    return counts


def _run_hours(start: datetime, end: datetime, zone: ZoneInfo, with_day: bool) -> str:
    """A run's hours, where a run that ends at midnight ends at 24:00: "04:00–00:00" reads as
    if it went backwards, and a whole free day as "00:00–00:00" reads as no time at all."""
    text = _hours(start, end, zone, with_day)
    local = end.astimezone(zone)
    if (local.hour, local.minute) != (0, 0):
        return text
    head, tail = text.rsplit("–", 1)  # tail is "00:00" and the zone's label
    return f"{head}–24:00{tail[5:]}"


def _unlabelled(text: str, label: str) -> str:
    """The range without its zone, where the zone is the one the column's header names."""
    return text[: -len(label) - 1] if label and text.endswith(f" {label}") else text


# The coverage strip (#161): a mark per time span, its state as a symbol as well as a color (FR-62),
# most urgent first when positions differ.
STRIP_MARKS = {
    "problem": "!",
    "needs": "!",
    "open": "",
    "covered": "✓",
    "closed": "–",
    "none": "",  # on the air, no slot yet: a dashed box (#247)
    "off": "",  # off the air: a hatched cell with no box
}  # open: an empty box
STRIP_ORDER = list(STRIP_MARKS)


def _gaps(event, slots) -> list[tuple]:
    """(start, end, state) for each hour of the periods that no slot touches: "off" outside the
    club's on-air hours, "none" on the air with no slot yet (#247). Without them a strip could
    not tell an hour the club means to skip from one nobody has made a slot for."""
    from .slots import HOUR, hour_grid

    taken = [(s.start, s.end) for s in slots]
    out = []
    for row in hour_grid(event):
        for box in row["boxes"]:
            if not box:
                continue
            a, b = box["at"], box["at"] + HOUR
            if not any(s < b and e > a for s, e in taken):
                out.append((a, b, "none" if box["on"] else "off"))
    return out


def _strip(slots, cells, by_start, zone, label, filtered: bool, event=None) -> list[dict]:
    """The whole event, a line a day: one mark per time span, linking to its row, or to the row's
    fold, or past the Problems only filter to the full roster. An hour with no slot is a mark
    that links nowhere: off the air, or on the air with no slot yet (#247)."""
    spans: dict[tuple, str] = {}
    for s in slots:
        key = cells[s.pk].shown.key
        state = "problem" if key == "problem" else BUCKET[key]
        span = (s.start, s.end)
        if span not in spans or STRIP_ORDER.index(state) < STRIP_ORDER.index(spans[span]):
            spans[span] = state
    gaps = {(a, b): state for a, b, state in _gaps(event, slots)} if event is not None else {}
    days: dict[str, dict] = {}
    for (start, end), state in sorted({**spans, **gaps}.items()):
        local = start.astimezone(zone)
        day = days.setdefault(local.strftime("%Y-%m-%d"), {"label": f"{local:%a %-d}", "marks": []})
        row, anchor = by_start.get(start), f"r-{start:%Y%m%d%H%M}"
        if (start, end) in gaps:
            href = ""  # no row to go to
        elif row is None or filtered:
            href = f"?#{anchor}"
        elif row.fold and not row.fold.open:
            href = f"?open={row.fold.id}#{anchor}"
        else:
            href = f"#{anchor}"
        day["marks"].append(
            {
                "state": state,
                "mark": STRIP_MARKS[state],
                "href": href,
                "time": _unlabelled(_hours(start, end, zone, with_day=False), label),
            }
        )
    return list(days.values())


# Fewer rows than this read faster as themselves than as "3 open hours".
FOLD_MIN_ROWS = 3


def _fold_runs(day: Day, lead_zone: ZoneInfo, other_zone: ZoneInfo | None, open_fold: str):
    """Folds every run of at least FOLD_MIN_ROWS rows in which each slot is open (nobody in it,
    not over a limit). A run breaks at an occupied or closed slot, a change of kind (setup,
    operating), a gap in time, and the day's end. Whole rows only, so a grid's columns stay
    aligned (FR-51, FR-65)."""
    run: list[Row] = []

    def close():
        if len(run) >= FOLD_MIN_ROWS:
            first, last = run[0], run[-1]
            fold = Fold(
                id=f"{first.start:%Y%m%d%H%M}",
                lead_range=_run_hours(first.start, last.end, lead_zone, with_day=False),
                other_range=_run_hours(first.start, last.end, other_zone, with_day=True)
                if other_zone
                else "",
                hours=round((last.end - first.start).total_seconds() / 3600, 2),
                slots=sum(1 for r in run for c in r.cells if c),
            )
            fold.open = open_fold in ("all", fold.id)
            first.fold_head = True
            for r in run:
                r.fold = fold
        run.clear()

    for row in day.rows:
        foldable = any(row.cells) and all(
            c is None or (c.shown.key == "open" and not c.over_limit) for c in row.cells
        )
        if not foldable:
            close()
            continue
        if run and (row.kind != run[-1].kind or row.start != run[-1].end):
            close()
        run.append(row)
    close()


def build(
    event: Event,
    viewer,
    lead: str = "utc",
    now: datetime | None = None,
    filter: str = "",
    open_fold: str = "",
) -> dict:
    now = now or timezone.now()
    local = display_zone(event)
    lead_zone, other_zone = (local, UTC) if lead == "local" or local == UTC else (UTC, local)
    if lead == "utc":
        lead_zone, other_zone = UTC, local
    starts, ends = event.starts_at(), event.ends_at()
    lead_label = zone_label(starts or now, lead_zone)
    # One of the two zones is UTC, so equal labels mean every time would print twice: a contest
    # shown in UTC leaves the second zone's strings empty, and the templates skip them.
    one_zone = lead_label == zone_label(starts or now, other_zone)
    is_captain = viewer.can_captain(event)
    published = event.state == Event.State.PUBLISHED
    locked = event.state == Event.State.LOCKED
    report = limit_report(event)

    positions = list(
        Position.objects.filter(location__event=event)
        .select_related("location")
        .order_by("location__order", "order")
    )
    slots = list(
        Slot.objects.filter(position__location__event=event, cancelled=False)
        .select_related("position", "position__location", "control_operator")
        .prefetch_related(
            "signups__user",
            "signups__user__license",
            "signups__user__notification_preferences",
            "signups__responsible_adults",
            "capacities",
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
            s,
            st,
            signups,
            open_roles,
            published=published,
            is_captain=is_captain,
            now=now,
            locked=locked,
        )
        on = s.start.date()
        badges = {}
        for su in signups:
            b = []
            if holds(su.user, "station_access", on):
                b.append(("S", "station access"))
            if holds(su.user, "it_access", on):
                b.append(("I", "computer access"))
            badges[su.pk] = b
        cells[s.pk] = Cell(
            s,
            signups,
            open_roles,
            mine.get(s.pk),
            st,
            shown,
            getattr(st, "control_operator", None),
            over_limit=s.pk in report["over_slot_ids"],
            badges=badges,
            co_choices=[su for su in signups if may_control(s, su)]
            if is_captain and s.kind == "operating"
            else [],
        )
        counts["total"] += 1
        counts[BUCKET[shown.key]] += 1

    layout = "grid" if 1 <= len(positions) <= GRID_MAX_POSITIONS else "list"
    pos_index = {p.pk: i for i, p in enumerate(positions)}
    every = list(slots)  # the coverage strip shows the whole event, whatever the filter
    # FR-65: what needs attention, which Problems only shows and its switch counts (#235)
    keep = {pk for pk, c in cells.items() if c.shown.key in ("needs", "problem") or c.over_limit}
    counts["attention"] = len(keep)
    if filter == "problems":
        slots = [s for s in slots if s.pk in keep]

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
                "" if one_zone else _hours(s.start, s.end, other_zone, with_day=True),
                s.kind,
                cells=[None] * len(positions) if layout == "grid" else [],
            )
            rows_by_span[span] = row
            day.rows.append(row)
        if layout == "grid":
            row.cells[pos_index[s.position_id]] = cells[s.pk]
        else:
            row.cells.append(cells[s.pk])

    other_label = "" if one_zone else zone_label(starts or now, other_zone)
    for day in days.values():
        _fold_runs(day, lead_zone, None if one_zone else other_zone, open_fold)
        for row in day.rows:
            for item in (row, row.fold) if row.fold_head else (row,):
                item.lead_hours = _unlabelled(item.lead_range, lead_label)
                item.other_hours = _unlabelled(item.other_range, other_label)
    by_start: dict[datetime, Row] = {}
    for day in days.values():
        for row in day.rows:
            if row.start not in by_start:
                by_start[row.start] = row
                row.anchor = f"r-{row.start:%Y%m%d%H%M}"
    strip = _strip(
        every, cells, by_start, lead_zone, lead_label, filtered=filter == "problems", event=event
    )
    gap_states = {m["state"] for d in strip for m in d["marks"]} & {"none", "off"}

    single_location = len({p.location_id for p in positions}) == 1
    roles = setting("slot_roles", []) or []
    return {
        "names_visible": viewer.is_member,  # FR-121: Provisional members see counts, not names
        "locked": locked,
        "bookable": published,
        "filter": filter,
        "limits": report,
        "layout": layout,
        "positions": positions,
        "single_location": positions[0].location if positions and single_location else None,
        "days": list(days.values()),
        "counts": counts,
        "lead": "utc" if lead_zone == UTC else "local",
        # The event's zone at its start, not today's (FR-36): a November event read in October
        # is EST, as its rows are. ponytail: one label for the event; one that crosses a
        # change of clocks shows the zone it starts in, and each row still names its own.
        "lead_label": lead_label,
        "other_label": "" if one_zone else zone_label(starts or now, other_zone),
        # The time, the second zone where there is one, and a column per position in a grid.
        "columns": 1 + (0 if one_zone else 1) + (len(positions) if layout == "grid" else 1),
        "strip": strip,
        "strip_gaps": gap_states,  # which of the two no-slot marks the Key explains
        "span": {
            "lead": f"{starts.astimezone(lead_zone):%a %-d %b %H:%M} – {ends.astimezone(lead_zone):%a %-d %b %H:%M} {zone_label(starts, lead_zone)}"
            if starts and ends
            else "",
            "other": f"{starts.astimezone(other_zone):%a %-d %b %H:%M} – {ends.astimezone(other_zone):%a %-d %b %H:%M} {zone_label(starts, other_zone)}"
            if starts and ends and not one_zone
            else "",
        },
        "roles": roles,
        # Tick-boxes only where the bulk bar offers something: a member's sign-up while the
        # event is published, a captain's close, reopen and cancel in any state.
        "selectable": is_captain or (published and bool(roles)),
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
                    return c, {**data, "row": row, "day": day}
    raise ValueError("slot is not on the roster")
