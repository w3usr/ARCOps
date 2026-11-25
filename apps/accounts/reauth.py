"""Confirming it is you, once per act that needs it.

Two things on this site are guarded by Confirm Access: raising a session to Sysadmin, and
reading the station computer password. Both are "every time" rather than "once in a while", so
nobody acts as sysadmin by accident.

The sign-in library's own test, `did_recently_reauthenticate`, is true for five minutes after a
reauthentication and stays true however many guarded things are done in that window. So two
conditions are added here. The latest proof must itself be a **reauthentication** — signing in
is not one, so arriving from the sign-in page never counts, even inside an earlier one's five
minutes — and it is **spent** by the act it was given for, so the next act asks again.

Nothing about how somebody proves it belongs here: the library owns that, and Confirm Access
offers a password or a passkey (§2.6).
"""

from __future__ import annotations

from allauth.account.authentication import get_authentication_records
from allauth.account.internal.flows.reauthentication import did_recently_reauthenticate

SPENT = "account.confirmation_spent_at"


def _latest(request):
    """The most recent authentication record, which is what the library's own test reads."""
    records = get_authentication_records(request, request.user)
    return records[-1] if records else None


def is_confirmed(request) -> bool:
    """Whether this session holds a fresh confirmation that has not been used yet."""
    record = _latest(request)
    if not record or not record.get("reauthenticated"):
        return False
    if record.get("at") == request.session.get(SPENT):
        return False
    return did_recently_reauthenticate(request)


def spend(request) -> None:
    """Use up the confirmation, so the next guarded act asks for its own."""
    record = _latest(request)
    if record:
        request.session[SPENT] = record.get("at")
