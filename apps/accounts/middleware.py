"""
Two small gates on every request:

* A session not remembered on this device ends after 12 hours without a request (TR-17).
* A temporary password (FR-7) works for exactly one sign-in, which must set a new password
  before anything else; the member is sent to the change-password page until they do.
* An account at access level "none" is signed out and shown a plain explanation (§2.1).
* A class-link account whose address is unverified past its deadline is signed out until it is
  verified or an officer waives it (FR-120).
* An account whose access level requires two-step verification (§2.6) is told for as long as the
  club's grace period lasts, and then sent to enroll before anything else.
"""

import time

from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils import timezone

ALLOWED_WHILE_TEMPORARY = (
    "/accounts/password/set/",  # the temporary password is spent at sign-in (signals.py)
    "/accounts/password/change/",
    "/accounts/logout/",
    "/static/",
    "/healthz",
)
IDLE = 12 * 3600  # TR-17: a session not remembered, after this long without a request
SEEN_EVERY = 300  # the last request is written at most this often, not on every page

# Everything the library's own pages need, so somebody being made to enroll can actually do it.
ALLOWED_WHILE_ENROLLING = ("/accounts/", "/me/two-step/", "/static/", "/healthz")


class AccountGateMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            if _idle_too_long(request.session):
                logout(request)
                messages.info(request, "You were signed out after 12 hours without activity.")
                return redirect("account_login")
            for signed_out, message in (
                (
                    not user.has_access,
                    "This account does not currently have access. Contact a club officer.",
                ),
                (
                    user.password_is_temporary
                    and user.temporary_password_expires
                    and user.temporary_password_expires < timezone.now(),
                    "That temporary password has expired. Ask a sysadmin for a new one.",
                ),
                (
                    user.verification_overdue
                    and not request.path.startswith(
                        ("/verify/", "/accounts/logout/", "/static/", "/healthz")
                    ),
                    "Please confirm your email address first: open the link in the message we "
                    "sent you, or ask a club officer to mark it verified.",
                ),
            ):
                if signed_out:
                    logout(request)
                    messages.error(request, message)
                    return redirect("account_login")
            gate = _two_factor_gate(request, user)
            if gate is not None:
                return gate
            if user.password_is_temporary and not request.path.startswith(ALLOWED_WHILE_TEMPORARY):
                messages.info(
                    request, "You signed in with a temporary password. Set your own to continue."
                )
                request.session["forced_password_change"] = True
                return redirect("/accounts/password/set/")
        return self.get_response(request)


def _two_factor_gate(request, user):
    """§2.6: a level the club requires it of is told first and made to enroll afterwards.

    The countdown starts the first time the requirement meets the account, which is here; the
    date is kept on the account so the same one is shown and enforced.
    """
    from . import mfa

    if not mfa.is_required(user) or mfa.has_factor(user):
        return None
    if not user.two_factor_enabled_at:
        user.two_factor_enabled_at = timezone.now()
        user.save(update_fields=["two_factor_enabled_at"])
    due = mfa.deadline(user)
    if due is None or timezone.now() < due or request.path.startswith(ALLOWED_WHILE_ENROLLING):
        return None
    messages.error(
        request,
        "Your access level requires two-step verification. Add an authenticator app or a "
        "passkey to carry on.",
    )
    return redirect("mfa_index")


def _idle_too_long(session) -> bool:
    """TR-17: "a 12-hour idle timeout otherwise". A session the person did
    not ask to remember ends with the browser, but on the server it lived the 14 days a
    remembered one has, which matters on the station PC. It now ends after 12 hours idle."""
    if not session.get_expire_at_browser_close():
        return False  # remembered on this device: its 14 days
    now, seen = time.time(), session.get("seen_at")
    if seen and now - seen > IDLE:
        return True
    if not seen or now - seen > SEEN_EVERY:
        session["seen_at"] = now
    return False
