"""Hours for a course (FR-124): check-in credits the slot's full length unless a captain marked a
no-show; officers read and export the totals per entry-link label."""

from __future__ import annotations

from ..models import SignUp


def credited_hours(signup: SignUp) -> float:
    if not signup.checked_in_at or signup.no_show:
        return 0.0
    return round((signup.slot.end - signup.slot.start).total_seconds() / 3600, 2)


def course_report(label: str) -> dict:
    signups = (
        SignUp.objects.filter(user__joined_via__label=label, slot__cancelled=False)
        .select_related("user", "slot", "slot__position", "slot__position__location__event")
        .order_by("user__last_name", "user__first_name", "slot__start")
    )
    rows, totals = [], {}
    for su in signups:
        h = credited_hours(su)
        rows.append({"signup": su, "hours": h})
        totals[su.user] = totals.get(su.user, 0.0) + h
    return {"label": label, "rows": rows, "totals": sorted(totals.items(), key=lambda kv: (kv[0].last_name, kv[0].first_name))}
