"""Credential rules: expiry (FR-25), who holds what (FR-26, FR-61), license refresh (TR-13)."""

from __future__ import annotations

import datetime as dt

from cryptography.fernet import Fernet
from django.conf import settings
from django.utils import timezone

from apps.ops.audit import record
from apps.ops.config import setting

from .models import LicenseRecord, SharedSecret, SignedAgreement, UlsLicense


def default_expiry(approved_on: dt.date, rule: str) -> dt.date:
    """FR-25. `next_september_1_skip_august`: the next 1 September, except that an approval in
    August runs to the 1 September of the following year. `one_year`: a year from approval."""
    if rule == "next_september_1_skip_august":
        year = approved_on.year
        if approved_on.month >= 8:  # September onward -> next year's; August -> also next year's
            year += 1
        return dt.date(year, 9, 1)
    return (
        dt.date(approved_on.year + 1, approved_on.month, approved_on.day)
        if not (approved_on.month == 2 and approved_on.day == 29)
        else dt.date(approved_on.year + 1, 2, 28)
    )


def ladder() -> list[str]:
    return list(setting("license_ladder", ["Novice", "Technician", "General", "Advanced", "Extra"]))


def class_rank(cls: str | None) -> int:
    lad = ladder()
    return lad.index(cls) if cls in lad else -1


def has_valid_license(user, on: dt.date, min_class: str | None = None) -> bool:
    lic = getattr(user, "license", None) or LicenseRecord.objects.filter(user=user).first()
    if not lic or lic.effective_status != "active":
        return False
    if lic.effective_expiry and lic.effective_expiry < on:
        return False
    if min_class and class_rank(lic.effective_class) < class_rank(min_class):
        return False
    return True


def holds_agreement(user, credential_key: str, on: dt.date) -> bool:
    """Approved and unexpired is the tested fact (FR-26)."""
    return (
        SignedAgreement.objects.filter(
            user=user, credential__key=credential_key, state=SignedAgreement.State.APPROVED
        )
        .filter(models_q_unexpired(on))
        .exists()
    )


def models_q_unexpired(on: dt.date):
    from django.db.models import Q

    return Q(expires_on__isnull=True) | Q(expires_on__gte=on)


def holds(user, credential_key: str, on: dt.date, min_class: str | None = None) -> bool:
    if credential_key == "amateur_license":
        return has_valid_license(user, on, min_class)
    return holds_agreement(user, credential_key, on)


def approve(
    actor, agreement: SignedAgreement, expires_on: dt.date | None = None
) -> SignedAgreement:
    rule = agreement.credential.default_expiry
    agreement.expires_on = expires_on or default_expiry(timezone.now().date(), rule)
    agreement.state = SignedAgreement.State.APPROVED
    agreement.approver = actor
    agreement.approved_at = timezone.now()
    agreement.save()
    record(
        actor,
        "agreement.approved",
        agreement,
        after={"expires_on": agreement.expires_on.isoformat()},
    )
    from apps.comms.services import send

    send(
        "agreement.approved",
        agreement.user,
        "agreement",
        {
            "title": agreement.template.title,
            "approver": actor.full_name if actor else "an approver",
            "expires": agreement.expires_on,
        },
    )
    return agreement


def approvers():
    """Sysadmins and members in an approver position (§2.3)."""
    from apps.accounts.models import AccessLevel, User
    from apps.ops.config import setting

    keys = {p["key"] for p in (setting("club_positions", []) or []) if p.get("approver")}
    qs = User.objects.filter(is_active=True).exclude(access_level=AccessLevel.NONE)
    from django.db.models import Q

    return list(qs.filter(Q(access_level=AccessLevel.SYSADMIN) | Q(club_position__in=keys)))


def expire_due() -> int:
    """`agreements:expiry` (TR-11): move past-due approvals to expired (FR-28)."""
    today = timezone.now().date()
    due = SignedAgreement.objects.filter(state=SignedAgreement.State.APPROVED, expires_on__lt=today)
    n = due.update(state=SignedAgreement.State.EXPIRED)
    if n:
        record(None, "agreements.expired", after={"count": n})
    return n


def refresh_license_from_local_table(user) -> LicenseRecord:
    """FR-4/FR-14/FR-102: look the member's callsign up in the local ULS table (TR-13)."""
    lic, _ = LicenseRecord.objects.get_or_create(user=user, defaults={"callsign": user.callsign})
    lic.callsign = user.callsign
    row = (
        UlsLicense.objects.filter(callsign=user.callsign.upper()).first() if user.callsign else None
    )
    if row:
        lic.licensee_name = row.licensee_name
        lic.operator_class = row.operator_class
        lic.status = row.status or "active"
        lic.grant_date = row.grant_date
        lic.expiry_date = row.expiry_date
        lic.frn = row.frn
        lic.source = "fcc_uls_local"
    else:
        lic.status = "unverified"  # until the next import finds it
        lic.source = "fcc_uls_local"
    lic.retrieved_at = timezone.now()
    lic.save()
    return lic


# ------------------------------------------------------------ shared secret ---
def _fernet() -> Fernet:
    key = settings.FIELD_ENCRYPTION_KEY
    if not key:
        raise RuntimeError("FIELD_ENCRYPTION_KEY is not set (TR-20)")
    return Fernet(key.encode() if isinstance(key, str) else key)


def set_shared_secret(
    actor, plaintext: str, effective_date: dt.date, name: str = "computer_account"
) -> None:
    obj, _ = SharedSecret.objects.get_or_create(
        name=name, defaults={"ciphertext": b"", "effective_date": effective_date}
    )
    obj.ciphertext = _fernet().encrypt(plaintext.encode("utf-8"))
    obj.effective_date = effective_date
    obj.set_by = actor
    obj.save()
    record(actor, "shared_secret.set", obj, after={"effective_date": effective_date.isoformat()})


def reveal_shared_secret(actor, name: str = "computer_account") -> str | None:
    """FR-33: every reveal is audited."""
    obj = SharedSecret.objects.filter(name=name).first()
    if not obj:
        return None
    record(actor, "shared_secret.viewed", obj)
    return _fernet().decrypt(bytes(obj.ciphertext)).decode("utf-8")
