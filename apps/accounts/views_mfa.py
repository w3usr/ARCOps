"""The pages that ask "is this really you", offering the method the account actually holds.

The library's page leads with an authenticator code and demotes the security key to "Alternative
options", whatever the person enrolled: it builds the code form unconditionally and the layout is
fixed in the template. Somebody whose only factor is a key met a box they could not fill (the
advisor, 2026-09-20).

The view is the library's, with two facts added so the page can lead with what is there. The
code box also accepts a recovery code, which is what it is for an account with no authenticator
app, and the page says so.
"""

from __future__ import annotations

from allauth.account.adapter import get_adapter
from allauth.account.views import ReauthenticateView
from allauth.mfa.base.views import AuthenticateView
from allauth.mfa.models import Authenticator
from allauth.mfa.webauthn.forms import ReauthenticateWebAuthnForm
from allauth.mfa.webauthn.internal import auth as webauthn_auth


class SecondStepView(AuthenticateView):
    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        held = set(
            Authenticator.objects.filter(user=self.stage.login.user).values_list("type", flat=True)
        )
        context.update(
            {
                "has_totp": Authenticator.Type.TOTP in held,
                "has_key": Authenticator.Type.WEBAUTHN in held,
                "has_recovery_codes": Authenticator.Type.RECOVERY_CODES in held,
            }
        )
        return context


second_step = SecondStepView.as_view()


class ConfirmAccessView(ReauthenticateView):
    """Confirm Access, with the passkey on the page that asks rather than behind a link.

    The library gives each way of confirming its own view and links between them, so a member
    with a passkey met two Confirm Access pages in a row (the advisor, 2026-09-20: "Why can't I
    just click Use passkey on the first page?"). This is the library's own password view with
    the other half's form and challenge added, exactly as its sign-in second step already does
    for itself.

    Verification stays the library's: `begin_authentication` leaves the challenge in the session,
    so the credential posts to `mfa_reauthenticate_webauthn`, which checks it and resumes
    whatever was interrupted.
    """

    def _check_reauthentication_method_available(self, request):
        # The library sends you to the first advertised method when you are not on one. This
        # page offers every method the account has, so it is where somebody should be.
        if get_adapter().get_reauthentication_methods(request.user):
            return None
        return super()._check_reauthentication_method_available(request)

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        user = self.request.user
        has_key = Authenticator.objects.filter(user=user, type=Authenticator.Type.WEBAUTHN).exists()
        context["has_key"] = has_key
        if has_key:
            context["webauthn_form"] = ReauthenticateWebAuthnForm(user=user)
            context["js_data"] = {"request_options": webauthn_auth.begin_authentication(user)}
            # The button is on this page now, so the link to the page it used to live on is not
            # an alternative to anything.
            context["reauthentication_alternatives"] = [
                alt
                for alt in context.get("reauthentication_alternatives") or []
                if not alt.get("id", "").endswith("webauthn")
            ]
        return context


confirm_access = ConfirmAccessView.as_view()
