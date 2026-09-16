"""Forms handed to the sign-in library (ACCOUNT_FORMS)."""

from __future__ import annotations

from allauth.account import forms as allauth_forms
from allauth.account.internal import flows
from django.contrib.auth.tokens import default_token_generator
from django.db.models import Q

from .models import User


class ResetPasswordForm(allauth_forms.ResetPasswordForm):
    """FR-107: a reset may be asked for with any address on the account, the sign-in address,
    the institution one, or the personal one, and the mail goes to the address typed. An
    unknown address gets no mail at all (the library's default sends an "unknown account" mail
    pointing at a signup page this site does not have); the page says the same thing either
    way. A minor's generated sign-in-only address is not an address anyone reads."""

    def clean_email(self) -> str:
        email = self.cleaned_data["email"].lower().strip()
        self.users = list(
            User.objects.filter(is_active=True, sign_in_only_address=False)
            .exclude(access_level="none")
            .filter(
                Q(email__iexact=email)
                | Q(institution_email__iexact=email)
                | Q(personal_email__iexact=email)
            )
        )
        return email

    def save(self, request, **kwargs) -> str:
        email = self.cleaned_data["email"]
        if self.users:
            token_generator = kwargs.get("token_generator", default_token_generator)
            flows.password_reset.request_password_reset(request, email, self.users, token_generator)
        return email
