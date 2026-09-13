"""Account operations shared by the templates and the API (TR-8)."""

from __future__ import annotations

import secrets
from datetime import timedelta

from django.utils import timezone

from apps.ops.audit import record
from apps.ops.config import institution_email_domain, setting

from .models import AccessLevel, Invitation, User


def create_invitation(
    issuer: User, email: str, category: str, is_minor: bool = False, guardian_email: str = ""
) -> Invitation:
    """FR-2/FR-3: a single-use link the issuer can also hand over by other means (FR-104)."""
    days = int(setting("defaults.invitation_expiry_days", 14))
    inv = Invitation.objects.create(
        email=email.lower(),
        category=category,
        is_minor=is_minor,
        guardian_email=guardian_email.lower(),
        issued_by=issuer,
        expires_at=timezone.now() + timedelta(days=days),
    )
    record(issuer, "invitation.created", inv, after={"email": inv.email, "category": category})
    return inv


def invitation_text(inv: Invitation, base_url: str) -> str:
    """The ready-to-send text the issuer can copy (FR-104)."""
    club = setting("club.name", "the club")
    contact = setting("club.contact_email", "")
    link = f"{base_url}/me/invite/{inv.token}/"
    return (
        f"You are invited to join {club}'s operations site.\n\n"
        f"Open this link to create your account: {link}\n"
        f"The link works once and expires on {inv.expires_at:%d %B %Y}.\n\n"
        f"Questions: {contact}"
    )


def issue_temporary_password(actor: User, user: User) -> str:
    """FR-7: one-time, expiring, shown once, never emailed."""
    hours = int(setting("defaults.temporary_password_expiry_hours", 72))
    password = secrets.token_urlsafe(12)
    user.set_password(password)
    user.password_is_temporary = True
    user.temporary_password_expires = timezone.now() + timedelta(hours=hours)
    user.save(update_fields=["password", "password_is_temporary", "temporary_password_expires"])
    record(actor, "password.temporary_issued", user)
    return password


def set_access_level(actor: User, user: User, level: str, reason: str = "") -> None:
    before = user.access_level
    user.access_level = level
    user.save(update_fields=["access_level"])
    record(
        actor,
        "access_level.changed",
        user,
        before={"level": before},
        after={"level": level, "reason": reason},
    )


def place_sign_in_email(user: User) -> bool:
    """The sign-in address is also a contact address. It goes into the institution slot when its
    domain is the one the club configures for its institution, otherwise into the personal slot,
    and only when that slot is empty. Returns True if a field was set (the caller saves).
    NAF, 2026-09-13: "The sign-in email never got populated into one of the email address
    locations." """
    if not user.email:
        return False
    domain = user.email.rsplit("@", 1)[-1].lower()
    inst = institution_email_domain().lower()
    if inst and domain == inst:
        if not user.institution_email:
            user.institution_email = user.email
            return True
        return False
    if not user.personal_email:
        user.personal_email = user.email
        return True
    return False


def revoke_invitation(actor: User, inv: Invitation) -> None:
    """FR-3: the issuer (or any officer) can withdraw an invitation that has not been used."""
    if inv.state == Invitation.State.CREATED:
        inv.state = Invitation.State.REVOKED
        inv.save(update_fields=["state"])
        record(actor, "invitation.revoked", inv)


def reissue_invitation(actor: User, inv: Invitation) -> Invitation:
    """FR-3: a fresh link for the same person; the old one stops working."""
    revoke_invitation(actor, inv)
    return create_invitation(actor, inv.email, inv.category, inv.is_minor, inv.guardian_email)


def admit_from_invitation(inv: Invitation, password: str, **profile) -> User:
    """FR-5: completing the form admits the person as a Member with the invitation's category."""
    user = User.objects.create_user(
        email=inv.email,
        password=password,
        category=inv.category,
        access_level=AccessLevel.MEMBER,
        under_18=inv.is_minor,
        **profile,
    )
    if place_sign_in_email(user):
        user.save(update_fields=["institution_email", "personal_email"])
    inv.state = Invitation.State.COMPLETED
    inv.completed_at = timezone.now()
    inv.accepted_by = user
    inv.save(update_fields=["state", "completed_at", "accepted_by"])
    record(
        user, "application.completed", user, after={"invitation": inv.pk, "category": inv.category}
    )
    return user
