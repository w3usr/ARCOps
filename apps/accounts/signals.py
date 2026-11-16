"""Clear the temporary-password flag once the member sets their own (FR-7)."""

from allauth.account.signals import password_changed, password_reset
from django.dispatch import receiver

from apps.ops.audit import record


def _clear(user):
    if user.password_is_temporary:
        user.password_is_temporary = False
        user.temporary_password_expires = None
        user.save(update_fields=["password_is_temporary", "temporary_password_expires"])
        record(user, "password.temporary_replaced", user)


@receiver([password_changed, password_reset])
def on_password_set(sender, user, **kwargs):
    _clear(user)
