"""allauth adapter: the system is invitation-only (FR-1), so open signup is closed."""

from allauth.account.adapter import DefaultAccountAdapter


class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request) -> bool:
        # Registration happens through an invitation link (apps.accounts.views.accept_invitation),
        # never through allauth's public signup page.
        return False
