"""Two-step verification: who is asked for a second factor, and when.

The sign-in library asks for one whenever an account holds **any** enrolled authenticator, which
counts a passkey as a second factor. Here a passkey is a way to sign in:

> I created a passkey, but did not enroll an authenticator app. So, I did not actually enable
> 2fa. — NAF, 2026-09-20

> We should make enabling 2fa explicit. I also want to make it optional right now. So, a user can
> enable or disable it. There should be a sysop option to make 2fa mandatory. — NAF, 2026-09-20

So the second step happens when the person asked for it, or when the club requires it of their
access group (§2.6, TR-16). The switch is on the account; the requirement is a club setting, a
list of group keys, shipped empty.

The library reads its login steps from the adapter (`get_login_stages`), which is where
`TwoFactorStage` replaces the shipped one.
"""

from __future__ import annotations

from datetime import timedelta

from allauth.mfa.stages import AuthenticateStage
from django.utils import timezone

from apps.ops.config import setting

SYSADMIN_KEY = "sysadmin"  # not a group; the account flag that holds every capability


def required_groups() -> set[str]:
    value = setting("security.two_factor_required_groups", []) or []
    return {str(key).strip() for key in value if str(key).strip()}


def grace_days() -> int:
    try:
        return max(0, int(setting("security.two_factor_grace_days", 14)))
    except (TypeError, ValueError):
        return 14


def is_required(user) -> bool:
    """Whether this account's level must use a second factor. A sysadmin counts when the club
    names the sysadmin key, because a sysadmin is a flag rather than a group."""
    wanted = required_groups()
    if not wanted:
        return False
    if user.is_superuser and SYSADMIN_KEY in wanted:
        return True
    return user.groups.filter(name__in=wanted).exists()


def has_factor(user) -> bool:
    """Whether anything could answer the second step: an authenticator app or a security key.
    Recovery codes are not one on their own; the library creates them beside a real factor."""
    from allauth.mfa.models import Authenticator

    return Authenticator.objects.filter(
        user=user, type__in=[Authenticator.Type.TOTP, Authenticator.Type.WEBAUTHN]
    ).exists()


def in_use(user) -> bool:
    """Whether the second step is actually asked of this account: they turned it on, or their
    level requires it and they have something to answer with."""
    if not user.is_authenticated:
        return False
    return (user.two_factor_enabled or is_required(user)) and has_factor(user)


def deadline(user):
    """When a required account that has not enrolled stops being let in. Counted from the date
    the club's requirement first met this account, which is when they last signed in without it;
    `two_factor_enabled_at` holds that mark, set the first time they are told."""
    if not is_required(user) or has_factor(user):
        return None
    start = user.two_factor_enabled_at or timezone.now()
    return start + timedelta(days=grace_days())


class TwoFactorStage(AuthenticateStage):
    """The library's second-factor step, asked for rather than inferred."""

    def _should_handle(self, request) -> bool:
        user = self.login.user
        if user is None or not (user.two_factor_enabled or is_required(user)):
            return False
        return super()._should_handle(request)
