"""
Retention (§4.3, TR-28): the daily `retention:apply` job. It anonymises and deletes on the
schedule the requirements set, logs what it did to the audit log by count, and never touches a
row belonging to an account under legal hold. Periods are configuration (`defaults.retention_*`)
with the requirements' proposed values as defaults.
"""

from __future__ import annotations

import datetime as dt

from django.utils import timezone

from .audit import record
from .config import setting


def _days(key: str, default_days: int) -> dt.timedelta:
    return dt.timedelta(days=int(setting(key, default_days)))


def apply(now=None) -> dict:
    from apps.accounts.models import AccessLevel, Guardianship, Invitation, User
    from apps.comms.models import Outbox
    from apps.credentials.models import SignedAgreement
    from apps.events.models import ResponsibleAdult

    now = now or timezone.now()
    today = now.date()
    counts = {}

    # Profiles at No access for the period: contact details go; name, callsign, and
    # participation history stay as club record. The audit row for the access change dates it.
    from .models import AuditLog

    cutoff = now - _days("defaults.retention_no_access_days", 730)
    n = 0
    for u in User.objects.filter(
        access_level=AccessLevel.NONE, legal_hold=False, deleted_at__isnull=True
    ).exclude(institution_email="", personal_email="", cell_phone=""):
        changed = (
            AuditLog.objects.filter(
                action="access_level.changed", subject_type="User", subject_id=str(u.pk)
            )
            .order_by("-at")
            .first()
        )
        since = changed.at if changed else u.date_joined
        if since <= cutoff:
            u.institution_email = u.personal_email = u.cell_phone = ""
            u.save(update_fields=["institution_email", "personal_email", "cell_phone"])
            n += 1
    counts["profiles_contact_removed"] = n

    # Guardian records: contact details go once the minor is converted or closed; the link stays.
    n = 0
    for g in Guardianship.objects.filter(active=False).select_related("guardian", "minor"):
        if g.guardian.legal_hold or g.minor.legal_hold:
            continue
        if g.relationship != "":
            g.relationship = ""
            g.save(update_fields=["relationship"])
            n += 1
    counts["guardian_links_trimmed"] = n

    # Responsible adults named for a slot: a year after the event.
    cutoff = now - _days("defaults.retention_responsible_adult_days", 365)
    qs = ResponsibleAdult.objects.filter(signup__slot__end__lt=cutoff).exclude(
        signup__user__legal_hold=True
    )
    counts["responsible_adults_deleted"] = qs.count()
    qs.delete()

    # Signed agreements and their PDFs: the configured years after expiry.
    cutoff_date = today - _days("defaults.retention_agreement_days", 3 * 365)
    n = 0
    for a in SignedAgreement.objects.filter(expires_on__lt=cutoff_date).exclude(
        user__legal_hold=True
    ):
        if a.pdf:
            a.pdf.delete(save=False)
        a.delete()
        n += 1
    counts["agreements_purged"] = n

    # Messages: bodies go after a year; the fact and recipient count stay.
    cutoff = now - _days("defaults.retention_message_days", 365)
    n = (
        Outbox.objects.filter(created__lt=cutoff)
        .exclude(body_html="")
        .exclude(user__legal_hold=True)
        .update(body_html="", body_text="")
    )
    counts["message_bodies_removed"] = n

    # Invitations never completed: 90 days after expiry.
    cutoff = now - _days("defaults.retention_invitation_days", 90)
    qs = Invitation.objects.exclude(state=Invitation.State.COMPLETED).filter(expires_at__lt=cutoff)
    counts["invitations_deleted"] = qs.count()
    qs.delete()

    if any(counts.values()):
        record(None, "retention.applied", after=counts)
    return counts
