"""Credential rules: expiry (FR-25), who holds what (FR-26, FR-61), license refresh (TR-13)."""

from __future__ import annotations

import datetime as dt

from cryptography.fernet import Fernet
from django.conf import settings
from django.utils import timezone

from apps.ops.audit import record
from apps.ops.config import setting

from .models import (
    AgreementTemplate,
    CredentialDecision,
    LicenseRecord,
    SharedSecret,
    SignedAgreement,
    UlsLicense,
)


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


def log_decision(agreement, action: str, actor=None, note: str = "", expires_on=None):
    """Write one line of the record of what has been decided about somebody's access.

    Called from the five places a decision is made: approving, approving after a decline,
    declining, revoking, and the two ways an approval ends by itself. The actor is frozen into a
    label the way the audit log freezes it, so a decision outlives the account that made it and
    a job reads as "system" (FR-25, 2026-09-20).
    """
    from .models import CredentialDecision

    guardian = getattr(actor, "acting_guardian", None)
    label = f"{guardian} acting for {actor}" if guardian else (str(actor) if actor else "system")
    return CredentialDecision.objects.create(
        agreement=agreement,
        action=action,
        actor=(guardian or actor) if getattr(guardian or actor, "pk", None) else None,
        actor_label=label,
        note=note or "",
        expires_on=expires_on,
    )


def approve(
    actor, agreement: SignedAgreement, expires_on: dt.date | None = None
) -> SignedAgreement:
    after_decline = agreement.state == SignedAgreement.State.DECLINED
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
    log_decision(
        agreement,
        CredentialDecision.Action.APPROVED_AFTER_DECLINE
        if after_decline
        else CredentialDecision.Action.APPROVED,
        actor,
        expires_on=agreement.expires_on,
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
    try:
        store_agreement_pdf(agreement)  # FR-23: the approval block joins the record
    except Exception:  # noqa: BLE001
        import logging

        logging.getLogger(__name__).exception("agreement PDF not re-rendered for %s", agreement.pk)
    return agreement


def approvers():
    """Everyone who may approve access to the station: faculty advisors and sysadmins (§2.1)."""
    from apps.ops.groups import people_who_may

    return list(people_who_may("approve_agreements"))


def expire_due() -> int:
    """`agreements:expiry` (TR-11): move past-due approvals to expired (FR-28)."""
    today = timezone.now().date()
    due = list(
        SignedAgreement.objects.filter(
            state=SignedAgreement.State.APPROVED, expires_on__lt=today
        ).select_related("credential", "user")
    )
    n = SignedAgreement.objects.filter(pk__in=[a.pk for a in due]).update(
        state=SignedAgreement.State.EXPIRED
    )
    if n:
        record(None, "agreements.expired", after={"count": n})
        # The audit log counts them; the approver's own record names each one (FR-25).
        for agreement in due:
            log_decision(
                agreement,
                CredentialDecision.Action.EXPIRED,
                None,
                note=f"reached its expiry date, {agreement.expires_on:%d %B %Y}",
            )
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
        lic.licensee_type = row.applicant_type
        lic.status = row.status or "active"
        lic.grant_date = row.grant_date
        lic.expiry_date = row.expiry_date
        lic.frn = row.frn
        lic.source = "fcc_uls_local"
        if lic.expiry_notice_for and lic.expiry_notice_for != row.expiry_date:
            lic.expiry_notice_stage, lic.expiry_notice_for = 0, None  # renewed: notices start over
        if user.name_from_uls and not user.pending_uls_name and (row.first_name or row.last_name):
            # FR-8, FR-14: with a callsign the name is the ULS name, refreshed by the sync
            changed = []
            if row.first_name and user.first_name != row.first_name:
                user.first_name = row.first_name
                changed.append("first_name")
            if row.last_name and user.last_name != row.last_name:
                user.last_name = row.last_name
                changed.append("last_name")
            if user.middle_name != row.middle_initial:
                user.middle_name = row.middle_initial  # FR-4: the middle initial the FCC holds
                changed.append("middle_name")
            if changed:
                user.save(update_fields=changed)
    else:
        # Nothing on this record describes the callsign the member now holds, so none of it may
        # stay: a member who moved from a Technician callsign to one the FCC has no record of
        # kept the class, the licensee name and the expiry of the callsign they left (the
        # collaborator on T10, 2026-09-20: "Switching from KC3ABC to WC1XYZ keeps the name and
        # Technician category of KC3ABC"). An override is a sysadmin's deliberate act and is
        # left alone (FR-15).
        lic.licensee_name = ""
        lic.operator_class = ""
        lic.licensee_type = ""
        lic.grant_date = None
        lic.expiry_date = None
        lic.frn = ""
        lic.expiry_notice_stage, lic.expiry_notice_for = 0, None
        lic.status = "unverified"  # until the next import finds it
        lic.source = "fcc_uls_local"
    lic.retrieved_at = timezone.now()
    lic.save()
    return lic


def names_match(first_a: str, last_a: str, first_b: str, last_b: str) -> bool:
    """FR-16: the same person beyond a middle name or initial. First names match on their
    first token so 'Nathaniel A' and 'Nathaniel' agree; last names match whole."""
    fa = (first_a or "").strip().lower().split()
    fb = (first_b or "").strip().lower().split()
    return (
        bool(fa and fb)
        and fa[0] == fb[0]
        and (last_a or "").strip().lower() == (last_b or "").strip().lower()
    )


def apply_override(actor, lic: LicenseRecord, data: dict) -> LicenseRecord:
    """FR-15, FR-20: a sysadmin's override of class, status, expiry, name, or country, with a
    reason; shown as such wherever the value appears and never replaced by the sync."""
    before = {
        k: str(getattr(lic, k) or "")
        for k in (
            "override_class",
            "override_status",
            "override_expiry",
            "override_name",
            "override_country",
        )
    }
    for k in before:
        setattr(lic, k, data.get(k) or ("" if k != "override_expiry" else None))
    lic.override_reason = data.get("override_reason", "")
    lic.override_by = actor if lic.has_override else None
    lic.save()
    record(
        actor,
        "license.override",
        lic,
        before=before,
        after={k: str(getattr(lic, k) or "") for k in before} | {"reason": lic.override_reason},
    )
    return lic


def lift_override(actor, lic: LicenseRecord) -> LicenseRecord:
    return apply_override(actor, lic, {})


def expiry_notices(now=None) -> dict:
    """FR-17: one notice at 90 days, one at 30, one on expiry, per license per expiry date.
    Overrides count: the effective expiry is what the member is told."""
    from apps.comms.services import send

    now = now or timezone.now()
    today = now.date()
    sent = {"90": 0, "30": 0, "expired": 0}
    for lic in LicenseRecord.objects.select_related("user").exclude(status="unverified"):
        expiry = lic.effective_expiry
        if not expiry or not lic.user.is_active or not lic.user.has_access:
            continue
        reset = lic.expiry_notice_for != expiry
        if reset:
            lic.expiry_notice_stage, lic.expiry_notice_for = 0, expiry
        days = (expiry - today).days
        stage = 1 if days < 0 else 30 if days <= 30 else 90 if days <= 90 else 0
        already = (
            stage == lic.expiry_notice_stage
            or (stage == 90 and lic.expiry_notice_stage in (30, 1))
            or (stage == 30 and lic.expiry_notice_stage == 1)
        )
        if stage == 0 or already:
            if reset:
                lic.save(update_fields=["expiry_notice_stage", "expiry_notice_for"])
            continue
        key = "license.expired" if stage == 1 else "license.expiring"
        send(
            key,
            lic.user,
            "license_expiry",
            {
                "callsign": lic.callsign,
                "expiry": expiry,
                "days": max(days, 0),
                "license_class": lic.effective_class,
            },
        )
        lic.expiry_notice_stage = stage
        lic.save(update_fields=["expiry_notice_stage", "expiry_notice_for"])
        sent["expired" if stage == 1 else str(stage)] += 1
    return sent


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


# ------------------------------------------------- agreements: expiry, revocation (FR-28, FR-29) ---


def agreement_expiry_run(now=None) -> dict:
    """FR-28: expire what is due; one notice per member covering every agreement expiring on
    the same date at 30 days and on the day; one summary to the approvers at each; FR-30: an
    approval of a superseded version past its re-sign date expires."""
    from django.conf import settings as dj
    from django.urls import reverse

    from apps.comms.services import send

    now = now or timezone.now()
    today = now.date()
    site = getattr(dj, "SITE_URL", "") or ""
    notice_days = int(setting("defaults.agreement_expiry_notice_days", 30))

    # FR-30: superseded versions with a re-sign date that has passed
    superseded = 0
    for a in SignedAgreement.objects.filter(
        state=SignedAgreement.State.APPROVED, template__is_current=False
    ).select_related("template"):
        newer = AgreementTemplate.objects.filter(key=a.template.key, is_current=True).first()
        if newer and newer.resign_by and newer.resign_by <= today:
            a.state = SignedAgreement.State.EXPIRED
            a.decision_reason = (
                f"superseded by version {newer.version}; re-sign was due {newer.resign_by}"
            )
            a.save(update_fields=["state", "decision_reason"])
            # This path wrote nothing anywhere until now: not the audit log, not the record the
            # approver reads. An approval that ended is a decision like any other (2026-09-20).
            log_decision(a, CredentialDecision.Action.SUPERSEDED, None, note=a.decision_reason)
            superseded += 1
    expired_now = expire_due()

    def bundle(qs):
        by_user: dict = {}
        for a in qs.select_related("user", "template"):
            by_user.setdefault(a.user, []).append(a)
        return by_user

    sent30 = sent0 = 0
    link = site + reverse("agreements")
    # 30-day notices: approved, expiring within the window, not yet noticed
    soon = SignedAgreement.objects.filter(
        state=SignedAgreement.State.APPROVED,
        expires_on__gte=today,
        expires_on__lte=today + dt.timedelta(days=notice_days),
        notice_30_sent_on__isnull=True,
    )
    due_summary = []
    for user, items in bundle(soon).items():
        if not user.is_active or not user.has_access:
            continue
        expires = min(a.expires_on for a in items)
        send(
            "agreement.expiring",
            user,
            "agreement",
            {
                "expires": expires,
                "titles": [a.template.title if a.template else a.credential.label for a in items],
                "link": link,
            },
        )
        SignedAgreement.objects.filter(pk__in=[a.pk for a in items]).update(notice_30_sent_on=today)
        due_summary.append(
            f"{user.full_name}{' ' + user.callsign if user.callsign else ''}: {expires:%d %b}"
        )
        sent30 += 1
    # day-of notices: expired today (state now expired, expires_on == yesterday or today)
    just = SignedAgreement.objects.filter(
        state=SignedAgreement.State.EXPIRED,
        expires_on__gte=today - dt.timedelta(days=1),
        expires_on__lte=today,
        notice_expiry_sent_on__isnull=True,
    )
    expired_summary = []
    for user, items in bundle(just).items():
        if not user.is_active or not user.has_access:
            continue
        send(
            "agreement.expired_notice",
            user,
            "agreement",
            {
                "expires": max(a.expires_on for a in items),
                "titles": [a.template.title if a.template else a.credential.label for a in items],
                "link": link,
            },
        )
        SignedAgreement.objects.filter(pk__in=[a.pk for a in items]).update(
            notice_expiry_sent_on=today
        )
        expired_summary.append(f"{user.full_name}{' ' + user.callsign if user.callsign else ''}")
        sent0 += 1
    summaries = 0
    approvals_link = site + reverse("approvals")
    for rows, expired in ((due_summary, False), (expired_summary, True)):
        if not rows:
            continue
        for ap in approvers():
            send(
                "agreement.expiry_summary",
                ap,
                "agreement",
                {
                    "count": len(rows),
                    "expired": expired,
                    "expires": today + dt.timedelta(days=notice_days),
                    "members": rows,
                    "link": approvals_link,
                },
            )
            summaries += 1
    return {
        "expired": expired_now,
        "superseded": superseded,
        "notices_30": sent30,
        "notices_expiry": sent0,
        "summaries": summaries,
    }


def revoke(actor, agreement: SignedAgreement, reason: str) -> SignedAgreement:
    """FR-29: an approver withdraws an approval; the member is told; the slots that depended on
    it read *Needs* on the next roster view and the warnings job picks them up."""
    from django.conf import settings as dj
    from django.urls import reverse

    from apps.comms.services import send

    agreement.state = SignedAgreement.State.REVOKED
    agreement.decision_reason = reason
    agreement.revoked_at = timezone.now()
    agreement.save(update_fields=["state", "decision_reason", "revoked_at"])
    record(actor, "agreement.revoked", agreement, after={"reason": reason})
    log_decision(agreement, CredentialDecision.Action.REVOKED, actor, note=reason)
    send(
        "agreement.revoked",
        agreement.user,
        "agreement",
        {
            "title": agreement.template.title if agreement.template else agreement.credential.label,
            "approver": actor.full_name,
            "reason": reason,
            "link": (getattr(dj, "SITE_URL", "") or "") + reverse("agreements"),
        },
    )
    return agreement


# ------------------------------------------------------- shared password rotation (FR-34) ---


def rotate_shared_secret(actor, plaintext: str, effective_date: dt.date) -> dict:
    """FR-32, FR-34: set the password and tell every member with current computer access; tell
    the sysadmin which former viewers no longer hold access, since cutting them off is the point."""
    from django.conf import settings as dj
    from django.urls import reverse

    from apps.accounts.models import User
    from apps.comms.services import send
    from apps.ops.models import AuditLog

    today = timezone.now().date()
    previous_viewers = set(
        AuditLog.objects.filter(action="shared_secret.viewed")
        .exclude(actor__isnull=True)
        .values_list("actor_id", flat=True)
    )
    set_shared_secret(actor, plaintext, effective_date)
    link = (getattr(dj, "SITE_URL", "") or "") + reverse("computer_password")
    current = [u for u in User.objects.with_access() if holds(u, "it_access", today)]
    for u in current:
        send("password.rotated", u, "security", {"effective": effective_date, "link": link})
    former = [
        u.full_name + (f" {u.callsign}" if u.callsign else "")
        for u in User.objects.filter(pk__in=previous_viewers)
        if not holds(u, "it_access", today)
    ]
    send(
        "password.rotation_summary",
        actor,
        "security",
        {
            "effective": effective_date,
            "notified": len(current),
            "cut_off": len(former),
            "former": former,
        },
    )
    return {"notified": len(current), "former": former}


# ------------------------------------------------------------- signed agreement PDF (FR-23) ---


def render_agreement_pdf(agreement: SignedAgreement) -> bytes:
    """FR-23, TR-10: the text as signed plus the signature block, as a tagged PDF (PDF/UA-1).
    WeasyPrint is imported here so the web worker pays for it only when a PDF is made."""
    import weasyprint
    from django.template.loader import render_to_string

    html = render_to_string(
        "credentials/agreement_pdf.html",
        {
            "a": agreement,
            "template": agreement.template,
            "club_name": setting("club.name", "the club"),
            "club_short": setting("club.short_name", "the club"),
            # The document carries its own standing and how it got there (NAF, 2026-09-20).
            "decisions": list(agreement.decisions.order_by("at", "pk")),
            "built_at": timezone.now(),
            # The watermark's colour, as six hex digits: the template writes it into an SVG
            # background, where a "#" would have to be escaped anyway.
            "watermark_color": {
                "approved": "1b6e3a",
                "revoked": "9b1c1c",
                "declined": "8a5a00",
                "expired": "8a5a00",
            }.get(agreement.state, "555555"),
        },
    )
    return weasyprint.HTML(string=html, base_url="/").write_pdf(
        pdf_variant="pdf/ua-1", pdf_tags=True
    )


def store_agreement_pdf(agreement: SignedAgreement) -> None:
    """Render and attach the PDF; re-rendered on approval so the approval block is in it."""
    from django.core.files.base import ContentFile

    data = render_agreement_pdf(agreement)
    name = (
        f"agreement-{agreement.pk}-v{agreement.template.version if agreement.template else 0}.pdf"
    )
    if agreement.pdf:
        agreement.pdf.delete(save=False)
    agreement.pdf.save(name, ContentFile(data), save=False)
    agreement.pdf_built_at = timezone.now()
    agreement.save(update_fields=["pdf", "pdf_built_at"])
