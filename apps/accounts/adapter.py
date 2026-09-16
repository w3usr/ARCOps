"""allauth adapter: invitation-only signup (FR-1) and the client IP behind a proxy."""

from email.utils import formataddr

from allauth.account.adapter import DefaultAccountAdapter
from django.contrib import messages
from django.urls import reverse

from apps.ops.config import setting


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

    # allauth sends its own mail (password reset, address confirmation) outside the club's
    # composer, so it took Django's default sender "webmaster@localhost" and a "[host] …"
    # subject. It now uses the club's sending address and display name (FR-69, FR-105), and the
    # subject stands on its own.

    def get_from_email(self) -> str:
        return formataddr(
            (
                setting("club.sending_display_name", "Club Operations"),
                setting("club.sending_address", "ops@example.org"),
            )
        )

    def format_email_subject(self, subject: str) -> str:
        return subject

    def render_mail(self, template_prefix, email, context, headers=None):
        context = {
            **context,
            "club_name": setting("club.name", "the club"),
            "club_short": setting("club.short_name", "the club"),
            "club_contact": setting("club.contact_email", ""),
        }
        return super().render_mail(template_prefix, email, context, headers)
