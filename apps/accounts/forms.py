"""Forms handed to the sign-in library (ACCOUNT_FORMS)."""

from __future__ import annotations

from allauth.account import forms as allauth_forms
from allauth.account.forms import default_token_generator  # the library's email-aware one
from allauth.account.internal import flows
from django.db.models import Q

from .models import User


class ResetPasswordForm(allauth_forms.ResetPasswordForm):
    """A reset may be asked for with any address that signs the member in: their sign-in
    address, or one they have confirmed. The mail goes to the address typed. An unknown address
    gets no mail at all (the library's default sends an "unknown account" mail pointing at a
    signup page this site does not have); the page says the same thing either way. A minor's
    generated sign-in-only address is not an address anyone reads."""

    def clean_email(self) -> str:
        email = self.cleaned_data["email"].lower().strip()
        qs = User.objects.filter(is_active=True, sign_in_only_address=False).exclude(
            access_level="none"
        )
        # The same addresses that sign a member in: their sign-in address, and any they have
        # confirmed. An address merely typed into a profile does not move anyone's password.
        self.users = list(
            qs.filter(
                Q(email__iexact=email)
                | Q(emailaddress__email__iexact=email, emailaddress__verified=True)
            ).distinct()
        )
        return email

    def save(self, request, **kwargs) -> str:
        email = self.cleaned_data["email"]
        if self.users:
            # The key view checks the link with the library's email-aware generator; the mail
            # must be made with the same one, or every link reads "Bad Token" (found live,
            # 2026-09-16, after this form first shipped with Django's generator here).
            token_generator = kwargs.get("token_generator", default_token_generator)
            flows.password_reset.request_password_reset(request, email, self.users, token_generator)
        return email
