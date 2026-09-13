"""Who may sign up for a role in a slot, and when (FR-53, FR-54)."""

from __future__ import annotations

from django.utils import timezone

from apps.credentials.services import class_rank, holds

from ..models import EligibilityRule, Opening


def can_sign_up(user, slot, role: str, now=None) -> tuple[bool, str]:
    """Returns (allowed, reason). Captains and officers are not exempt: the rules describe who
    the slot is for, and a captain who wants to override does so through the roster tools."""
    now = now or timezone.now()
    event = slot.event
    if user.under_18:
        return False, "a guardian signs up on a minor's behalf"

    # Openings: if any opening exists for this role, one of them must have passed for this
    # person's category (an opening with no categories is for everyone).
    openings = list(Opening.objects.filter(event=event, role=role))
    if openings:
        open_for_me = [
            o
            for o in openings
            if o.opens_at <= now and (not o.categories or user.category in o.categories)
        ]
        if not open_for_me:
            upcoming = sorted(
                (o for o in openings if not o.categories or user.category in o.categories),
                key=lambda o: o.opens_at,
            )
            if upcoming:
                return False, f"{role} opens to you on {upcoming[0].opens_at:%d %b %Y %H:%M}Z"
            return False, f"{role} is not open to your membership category"

    # Eligibility: the slot's own rule wins over the event's default for the role.
    rule = (
        EligibilityRule.objects.filter(slot=slot, role=role).first()
        or EligibilityRule.objects.filter(event=event, slot__isnull=True, role=role).first()
    )
    if rule:
        if rule.categories and user.category not in rule.categories:
            return False, f"{role} is limited to: {', '.join(rule.categories)}"
        if rule.min_license_class and (
            not holds(user, "amateur_license", slot.start.date())
            or class_rank(getattr(getattr(user, "license", None), "effective_class", None))
            < class_rank(rule.min_license_class)
        ):
            return False, f"{role} needs a {rule.min_license_class} or higher license"
        for key in rule.required_credentials or []:
            if not holds(user, key, slot.start.date()):
                return False, f"{role} needs {key.replace('_', ' ')}"
    return True, ""
