"""The count of signatures waiting on an approver, for the sidebar badge.

The advisor, 2026-09-20: "Can the Approvals navigation item also get a badge indicating the
number of things that need approval?" It is the same badge the unread count uses, so the two
read alike; it is counted only for somebody who may approve, so nobody else pays for the query.
"""

from .models import SignedAgreement


def approvals_waiting(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated or not user.may("approve_agreements"):
        return {}
    return {
        "approvals_waiting": SignedAgreement.objects.filter(
            state=SignedAgreement.State.SIGNED
        ).count()
    }
