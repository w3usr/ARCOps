"""allauth adapter: invitation-only signup (FR-1) and the client IP behind a proxy."""

from email.utils import formataddr

from allauth.account.adapter import DefaultAccountAdapter
from allauth.core import context
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

    def reauthenticate(self, user, password: str) -> bool:
        """Confirm the person at the keyboard knows this account's password, before they add a
        passkey or turn on two-factor.

        The library rebuilds the credentials from what it expects an account to have: its own
        username field, and the primary row in its address table. This installation has neither.
        The account's key is its public identifier, and sign-in addresses are our own rows
        mirrored into the library's table with no primary among them, so the library handed
        Django a password and nothing to look the account up by. Every correct password came
        back "Incorrect password." (the advisor, 2026-09-20). The account's own key is the
        credential Django's model backend understands.
        """
        credentials = {"username": str(user.get_username()), "password": password}
        reauth_user = self.authenticate(context.request, **credentials)
        return reauth_user is not None and reauth_user.pk == user.pk

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
        """The club's names for the templates, a table-drawn button for the reset link, and the
        site's one mail layout around the HTML part (apps.comms.layout), as every other message
        gets in deliver()."""
        from apps.comms.layout import button, wrap

        context = {
            **context,
            "club_name": setting("club.name", "the club"),
            "club_short": setting("club.short_name", "the club"),
            "club_contact": setting("club.contact_email", ""),
        }
        if context.get("password_reset_url"):
            context["reset_button"] = button(context["password_reset_url"], "Reset my password")
        msg = super().render_mail(template_prefix, email, context, headers)
        alts = getattr(msg, "alternatives", None) or []
        for i, alt in enumerate(alts):
            content, mimetype = (alt.content, alt.mimetype) if hasattr(alt, "content") else alt
            if mimetype == "text/html":
                alts[i] = (
                    type(alt)(wrap(content), mimetype)
                    if hasattr(alt, "content")
                    else (wrap(content), mimetype)
                )
        return msg
