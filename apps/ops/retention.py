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
    from apps.accounts.models import Guardianship, Invitation
    from apps.comms.models import Outbox
    from apps.events.models import ResponsibleAdult

    now = now or timezone.now()
    counts = {}

    # A former member's record is kept whole, and read in the archive (FR-125). It used to be
    # stripped of its contact details two years after the account lost access. The advisor,
    # 2026-09-17: "I don't really like the automatic deletion. Instead, can we have a method to
    # archive members?" So nothing here touches a member's profile any more.

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

    # Signed agreements and their PDFs are kept indefinitely, on the same decision: who was
    # cleared for the station, and when, is the club's answer to the University years later.

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
