"""A guardian on the same slot as their ward is the ward's responsible adult (FR-64 as amended by
addendum A40). The ordinary row is written for them, marked `automatic`, so
check-in, the roster and the slot dialog read it as any other; it goes when the guardian leaves."""

from __future__ import annotations

from django.db.models import Q

from apps.ops.audit import record

from ..models import ResponsibleAdult, SignUp


def name_guardians_on_slot(actor, su: SignUp) -> None:
    """After `su` joins its slot: whichever of a minor and their active adult guardian came
    second, the guardian is named for the minor's sign-up, unless already named."""
    from apps.accounts.models import Guardianship

    on_slot = {s.user_id: s for s in su.slot.signups.select_related("user")}
    pairs = Guardianship.objects.filter(
        Q(minor_id=su.user_id, guardian_id__in=on_slot)
        | Q(guardian_id=su.user_id, minor_id__in=on_slot),
        active=True,
        guardian__under_18=False,
    ).select_related("guardian")
    for g in pairs:
        ward = on_slot[g.minor_id]
        if not ward.user.under_18 or ward.responsible_adults.filter(member=g.guardian).exists():
            continue
        ResponsibleAdult.objects.create(
            signup=ward, name=g.guardian.full_name, member=g.guardian, automatic=True
        )
        record(
            actor,
            "responsible_adult.named",
            ward,
            after={
                "name": g.guardian.full_name,
                "member": g.guardian.pk,
                "via": "guardian on the slot",
            },
        )


def release_guardian(actor, su: SignUp) -> None:
    """Before `su` leaves its slot: the rows that named its holder only because they were on it."""
    for a in ResponsibleAdult.objects.filter(
        automatic=True, member_id=su.user_id, signup__slot_id=su.slot_id
    ).select_related("signup"):
        record(
            actor,
            "responsible_adult.removed",
            a.signup,
            before={"name": a.name, "via": "left the slot"},
        )
        a.delete()
