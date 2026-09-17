"""Forms handed to the sign-in library (ACCOUNT_FORMS)."""

from __future__ import annotations

from allauth.account import forms as allauth_forms
from allauth.account.forms import default_token_generator  # the library's email-aware one
from allauth.account.internal import flows

from .addresses import sign_in_addresses
from .models import User


class ResetPasswordForm(allauth_forms.ResetPasswordForm):
    """A reset may be asked for with any address that signs the member in. The mail goes to the
    address typed. An unknown address gets no mail at all (the library's default sends an
    "unknown account" mail pointing at a signup page this site does not have); the page says the
    same thing either way."""

    def clean_email(self) -> str:
        email = self.cleaned_data["email"].lower().strip()
        # The same addresses that sign a member in, so the two doors match: an address merely
        # typed into a profile moves nobody's password.
        self.users = [
            u
            for u in User.objects.by_address(email)
            .filter(is_active=True)
            .exclude(access_level="none")
            if email in sign_in_addresses(u)
        ]
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
