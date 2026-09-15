"""allauth adapter: invitation-only signup (FR-1) and the client IP behind a proxy."""

from allauth.account.adapter import DefaultAccountAdapter
from django.contrib import messages
from django.urls import reverse


class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request) -> bool:
        # Registration happens through an invitation link (apps.accounts.views.accept_invitation),
        # never through allauth's public signup page.
        return False

    def get_password_change_redirect_url(self, request) -> str:
        """After a forced change (a temporary password, FR-7) the member lands on the home page
        with a welcome; allauth's default left them on the form they had just submitted, which
        read as if nothing had happened. A change made from the profile returns to the profile."""
        if request.session.pop("forced_password_change", False):
            messages.success(
                request, f"Your password is set. Welcome, {request.user.display_first}."
            )
            return reverse("dashboard")
        return reverse("profile")

    def get_client_ip(self, request) -> str:
        """allauth's rate limiter (TR-18) keys on the client IP and refuses the request when it
        cannot find one. gunicorn listens on a unix socket, so REMOTE_ADDR is empty; nginx passes
        the visitor's address, already restored from Cloudflare's header by the real-IP snippet,
        in X-Real-IP. Only nginx can reach the socket, so the header is trustworthy here."""
        for key in ("HTTP_X_REAL_IP", "HTTP_X_FORWARDED_FOR", "REMOTE_ADDR"):
            value = request.META.get(key, "")
            if value:
                return value.split(",")[0].strip()
        return "0.0.0.0"  # noqa: S104 - a sentinel for "unknown", never a bind address
