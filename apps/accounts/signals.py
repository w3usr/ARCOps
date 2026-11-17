"""A temporary password (FR-7): spent at the sign-in that uses it, and the flag cleared once the
member sets their own."""

from allauth.account.signals import password_changed, password_reset, password_set
from django.contrib.auth import HASH_SESSION_KEY
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from apps.ops.audit import record


def _clear(user):
    if user.password_is_temporary:
        user.password_is_temporary = False
        user.temporary_password_expires = None
        user.save(update_fields=["password_is_temporary", "temporary_password_expires"])
        record(user, "password.temporary_replaced", user)


@receiver([password_changed, password_reset, password_set])
def on_password_set(sender, user, **kwargs):
    _clear(user)


@receiver(user_logged_in)
def spend_a_temporary_password(sender, request, user, **kwargs):
    """FR-7: "it works for exactly one sign-in" (private tracker 287). Used once, it signs nobody
    in again: this session stays, and can only set the member's own password (the middleware
    sends it there); anyone who saw the password and tries it afterwards is refused."""
    if user.password_is_temporary and user.has_usable_password():
        user.set_unusable_password()
        user.save(update_fields=["password"])
        request.session[HASH_SESSION_KEY] = user.get_session_auth_hash()  # this sign-in stays
        record(user, "password.temporary_spent", user)
