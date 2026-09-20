"""The second step at sign-in, offering the method the account actually holds.

The library's page leads with an authenticator code and demotes the security key to "Alternative
options", whatever the person enrolled: it builds the code form unconditionally and the layout is
fixed in the template. Somebody whose only factor is a key met a box they could not fill (the
advisor, 2026-09-20).

The view is the library's, with two facts added so the page can lead with what is there. The
code box also accepts a recovery code, which is what it is for an account with no authenticator
app, and the page says so.
"""

from __future__ import annotations

from allauth.mfa.base.views import AuthenticateView
from allauth.mfa.models import Authenticator


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
