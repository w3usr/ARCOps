"""
Entry links (FR-119, FR-120) and the Provisional review (FR-121).

An officer makes a link; a person who opens it completes the join form. Through a class link the
account is a Member at once and must verify its address within `defaults.entry_link_verification_days`
unless an officer waives it. Through a community link the account exists but is inactive until the
verification link is followed, then becomes Provisional and every officer is told.

Verification tokens are signed values (django.core.signing), so nothing is stored and a token
cannot be minted without the secret key.
"""

from __future__ import annotations

from datetime import timedelta

from django.core import signing
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from apps.comms.services import send
from apps.ops.audit import record
from apps.ops.config import setting

from .models import AccessLevel, EntryLink, User

VERIFY_SALT = "arcops.verify-email"
VERIFY_MAX_AGE = 30 * 24 * 3600  # a link in an old email still works for a month


def trusted_domains() -> list[str]:
    return [str(d).lower() for d in (setting("trusted_email_domains", []) or [])]


def verification_days() -> int:
    return int(setting("defaults.entry_link_verification_days", 7) or 7)


def create_link(
    actor: User,
    *,
    label: str,
    kind: str,
    required_domain: str = "",
    expires_at,
    cap=None,
    landing_event=None,
) -> EntryLink:
    link = EntryLink.objects.create(
        label=label.strip()[:80],
        kind=kind,
        required_domain=(required_domain or "").lower().strip()
        if kind == EntryLink.Kind.CLASS
        else "",
        expires_at=expires_at,
        cap=cap or None,
        landing_event=landing_event,
        created_by=actor,
    )
    record(actor, "entry_link.created", link, after={"label": link.label, "kind": kind})
    return link


def verification_token(user: User) -> str:
    return signing.dumps({"u": user.pk, "e": user.email}, salt=VERIFY_SALT)


def user_from_token(token: str) -> User | None:
    try:
        data = signing.loads(token, salt=VERIFY_SALT, max_age=VERIFY_MAX_AGE)
    except signing.BadSignature:
        return None
    user = User.objects.filter(pk=data.get("u"), email=data.get("e")).first()
    return user


def send_verification(user: User, base_url: str) -> None:
    url = base_url + reverse("verify_email", args=[verification_token(user)])
    key = "account.verify_member" if user.is_active else "account.verify_provisional"
    send(key, user, "account", {"link": url, "days": verification_days()})


def join_through_link(
    link: EntryLink, *, email: str, password: str, category: str, base_url: str, **profile
) -> User:
    """Creates the account for a person who completed the join form on an open link."""
    email = email.strip().lower()
    now = timezone.now()
    is_class = link.kind == EntryLink.Kind.CLASS
    with transaction.atomic():
        user = User.objects.create_user(
            email=email,
            password=password,
            category=category if is_class else "community",
            access_level=AccessLevel.MEMBER if is_class else AccessLevel.NONE,
            joined_via=link,
            verification_deadline=now + timedelta(days=verification_days()) if is_class else None,
            **profile,
        )
        if not is_class:
            user.is_active = False  # exists only once the address is confirmed
            user.save(update_fields=["is_active"])
        from .services import place_sign_in_email

        if place_sign_in_email(user):
            user.save(update_fields=["institution_email", "personal_email"])
    record(user, "account.joined_via_link", user, after={"link": link.pk, "kind": link.kind})
    send_verification(user, base_url)
    return user


def complete_verification(user: User, base_url: str) -> str:
    """Marks the address verified; a community account becomes Provisional and officers are told.
    Returns a short description of what happened for the page."""
    now = timezone.now()
    user.email_verified_at = now
    fields = ["email_verified_at"]
    became_provisional = False
    if (
        not user.is_active
        and user.access_level == AccessLevel.NONE
        and user.joined_via
        and user.joined_via.kind == EntryLink.Kind.COMMUNITY
    ):
        user.is_active = True
        user.access_level = AccessLevel.PROVISIONAL
        fields += ["is_active", "access_level"]
        became_provisional = True
    user.save(update_fields=fields)
    record(user, "email.verified", user)
    if became_provisional:
        notify_officers_of_provisional(user, base_url)
        return "provisional"
    return "verified"


def mark_verified(actor: User, user: User) -> None:
    """The officer's waiver (FR-120): counts as verification for the deadline and the badge."""
    if not user.email_verified_at:
        user.email_verified_at = timezone.now()
        user.save(update_fields=["email_verified_at"])
        record(actor, "email.verified_by_officer", user)


def notify_officers_of_provisional(user: User, base_url: str) -> None:
    url = base_url + reverse("member_detail", args=[user.pk])
    via = user.joined_via.label if user.joined_via else "a community link"
    for officer in User.objects.filter(
        access_level__in=[AccessLevel.OFFICER, AccessLevel.SYSADMIN], is_active=True
    ):
        send(
            "account.provisional_notice",
            officer,
            "account",
            {"person": user, "via": via, "link": url},
        )


def admit(actor: User, user: User) -> None:
    from .services import set_access_level

    set_access_level(actor, user, AccessLevel.MEMBER, "admitted after review")
    send("account.admitted", user, "account")


def decline(actor: User, user: User, reason: str) -> None:
    from .services import set_access_level

    set_access_level(actor, user, AccessLevel.NONE, f"declined: {reason}")
    send("account.declined", user, "account", {"reason": reason})


def pending_review():
    return (
        User.objects.filter(access_level=AccessLevel.PROVISIONAL, is_active=True)
        .select_related("joined_via")
        .order_by("date_joined")
    )
