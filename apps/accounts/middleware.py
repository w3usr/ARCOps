"""
Two small gates on every request:

* A temporary password (FR-7) works for exactly one sign-in, which must set a new password
  before anything else; the member is sent to the change-password page until they do.
* An account at access level "none" is signed out and shown a plain explanation (§2.1).
* A class-link account whose address is unverified past its deadline is signed out until it is
  verified or an officer waives it (FR-120).
"""

from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone

from .models import AccessLevel

ALLOWED_WHILE_TEMPORARY = (
    "/accounts/password/change/",
    "/accounts/logout/",
    "/static/",
    "/healthz",
)


class AccountGateMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            if user.access_level == AccessLevel.NONE and not user.is_superuser:
                logout(request)
                messages.error(
                    request, "This account does not currently have access. Contact a club officer."
                )
                return redirect(reverse("account_login"))
            if (
                user.password_is_temporary
                and user.temporary_password_expires
                and user.temporary_password_expires < timezone.now()
            ):
                logout(request)
                messages.error(
                    request, "That temporary password has expired. Ask a sysadmin for a new one."
                )
                return redirect(reverse("account_login"))
            if user.verification_overdue and not request.path.startswith(("/verify/", "/accounts/logout/", "/static/", "/healthz")):
                logout(request)
                messages.error(
                    request,
                    "Please confirm your email address first: open the link in the message we sent "
                    "you, or ask a club officer to mark it verified.",
                )
                return redirect(reverse("account_login"))
            if user.password_is_temporary and not request.path.startswith(ALLOWED_WHILE_TEMPORARY):
                messages.info(
                    request, "You signed in with a temporary password. Set your own to continue."
                )
                request.session["forced_password_change"] = True
                return redirect("/accounts/password/change/")
        return self.get_response(request)
