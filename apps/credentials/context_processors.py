"""What the sidebar needs from credentials: the approvals badge, and the way to the password.

The advisor, 2026-09-20: "Can the Approvals navigation item also get a badge indicating the
number of things that need approval?" It is the same badge the unread count uses, so the two
read alike; it is counted only for somebody who may approve, so nobody else pays for the query.
"""

from django.utils import timezone

from .models import SignedAgreement
from .services import holds


def approvals_waiting(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated or not user.may("approve_agreements"):
        return {}
    # The same filter the page applies, or the badge promises work the queue does not show. An
    # account ended any of the four ways -- closed, suspended, archived, deleted -- keeps its
    # signatures on the record, but they are nobody's to approve (2026-09-23).
    from apps.accounts.models import User

    return {
        "approvals_waiting": SignedAgreement.objects.filter(
            state=SignedAgreement.State.SIGNED, user__in=User.objects.with_access()
        ).count()
    }


def computer_password_entry(request):
    """Whether this account may read the station computer password, so the sidebar can offer it.

    The page had no entry of its own: a member reached it from the rotation notice and nowhere
    else, so anybody who deleted that message was left with a URL to guess (NAF, 2026-09-20:
    "what is the UI route for a person who has been granted access to view the station password
    … I want that to be straightforward and simple"). It is offered to whoever holds the
    credential today, which is the same test the page itself applies (FR-33).
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated or user.under_18:
        return {}
    return {"may_see_computer_password": holds(user, "it_access", timezone.now().date())}
