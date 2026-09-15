"""
Slot viability (FR-61 to FR-64), the control operator (FR-63), and the check-in window
(FR-113). Pure functions over a slot and its sign-ups, so the tests are table-driven.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from apps.credentials.services import class_rank, holds
from apps.ops.config import setting

ON_AIR_ROLES_DEFAULT = {"operator", "mentor"}


@dataclass
class SlotStatus:
    status: str  # empty | not_viable | viable | at_risk
    reasons: list[str] = field(default_factory=list)
    control_operator = None  # a User or None
    missing: list[str] = field(default_factory=list)
    below_preferred: str | None = None  # the best class present when under the event's preferred class

    @property
    def label(self) -> str:
        return {
            "empty": "Empty",
            "not_viable": "Not viable",
            "viable": "Viable",
            "at_risk": "At risk",
        }[self.status]


def on_air_roles() -> set[str]:
    roles = setting("slot_roles", []) or []
    s = {r["key"] for r in roles if r.get("on_air")}
    return s or ON_AIR_ROLES_DEFAULT


def rule_for(slot) -> list[dict]:
    """The location's rule, else the club default (FR-51, FR-61); non-operating kinds have
    their own (FR-47)."""
    if slot.kind != "operating":
        kinds = setting("non_operating_slot_kinds", []) or []
        for k in kinds:
            if k["key"] == slot.kind:
                return [{"credential": c} for c in k.get("viability", [])]
        return [{"credential": "station_access"}]
    loc_rule = slot.position.location.viability_rule
    if loc_rule:
        return loc_rule.get("require_all_of", loc_rule) if isinstance(loc_rule, dict) else loc_rule
    default = setting("viability_rule_default", {}) or {}
    return default.get(
        "require_all_of",
        [
            {"credential": "amateur_license", "min_class_from_event": True},
            {"credential": "station_access"},
            {"credential": "it_access"},
        ],
    )


def _satisfied(rule: list[dict], people, slot) -> tuple[bool, list[str]]:
    """Does this set of people satisfy every requirement? Returns (ok, missing labels)."""
    on = slot.start.date()
    missing = []
    for req in rule:
        key = req["credential"]
        # The event's class is *preferred* (FR-61, 2026-09-15): any class satisfies the requirement;
        # evaluate() adds a warning when nobody in the slot reaches the preferred class.
        if not any(holds(p, key, on, None) for p in people):
            missing.append(key.replace("_", " "))
    return (not missing, missing)


def below_preferred(event, people, on) -> str | None:
    """The best license class present when it is below the event's preferred class, else None."""
    from apps.credentials.services import class_rank

    pref = event.min_license_class
    if not pref:
        return None
    best, best_rank = None, -1
    for p in people:
        if holds(p, "amateur_license", on, None):
            cls = getattr(getattr(p, "license", None), "effective_class", None) or ""
            if class_rank(cls) > best_rank:
                best, best_rank = cls, class_rank(cls)
    if best is not None and best_rank < class_rank(pref):
        return best
    return None


def evaluate(slot, signups=None) -> SlotStatus:
    signups = list(signups if signups is not None else slot.signups.select_related("user").all())
    if not signups:
        return SlotStatus("empty", ["no one signed up"])
    on_air = [s for s in signups if s.role in on_air_roles()]
    people = [s.user for s in (on_air if slot.kind == "operating" else signups)]
    rule = rule_for(slot)
    ok, missing = _satisfied(rule, people, slot)
    reasons: list[str] = []
    for label in missing:
        reasons.append(f"nobody with {label}")

    # Minors need their designated responsible adult on the sign-up (FR-64).
    for s in signups:
        if s.user.under_18 and not s.responsible_adults.exists():
            ok = False
            reasons.append(f"{s.user.short_name} (under 18) has no responsible adult designated")

    if not ok:
        return SlotStatus("not_viable", reasons, missing=missing)

    # At risk: removing any one person breaks it (FR-62).
    low = below_preferred(slot.event, people, slot.start.date())
    for i in range(len(people)):
        others = people[:i] + people[i + 1 :]
        if not others or not _satisfied(rule, others, slot)[0]:
            status = SlotStatus("at_risk", [f"depends on {people[i].short_name} alone"])
            status.below_preferred = low
            status.control_operator = control_operator(slot, on_air)
            return status
    status = SlotStatus("viable", [f"below preferred class ({low})"] if low else [])
    if low:
        status.below_preferred = low
    status.control_operator = control_operator(slot, on_air)
    return status


def control_operator(slot, on_air_signups):
    """FR-63: the captain's choice, else the highest-class valid licensee in an on-air role."""
    if slot.kind != "operating":
        return None
    if slot.control_operator_id:
        return slot.control_operator
    on = slot.start.date()
    best, best_rank = None, -1
    for s in on_air_signups:
        lic = getattr(s.user, "license", None)
        if lic is None or not holds(s.user, "amateur_license", on):
            continue
        rank = class_rank(lic.effective_class)
        if rank > best_rank:
            best, best_rank = s.user, rank
    return best


def checkin_window_open(slot, now) -> bool:
    """FR-113: from N minutes before the start until the slot ends."""
    minutes = int(setting("defaults.checkin_opens_minutes_before", 30))
    return slot.start - timedelta(minutes=minutes) <= now <= slot.end


def would_break(slot, without_signup) -> SlotStatus | None:
    """FR-111/FR-56: what the slot would look like if this sign-up left; None if unchanged."""
    remaining = [s for s in slot.signups.select_related("user").all() if s.pk != without_signup.pk]
    before = evaluate(slot)
    after = evaluate(slot, remaining)
    if (
        before.status in ("viable", "at_risk")
        and after.status in ("not_viable", "empty", "at_risk")
        and after.status != before.status
    ):
        return after
    return None
