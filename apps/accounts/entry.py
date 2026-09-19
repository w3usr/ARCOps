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

from django.contrib.auth.models import Group
from django.core import signing
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from apps.comms.services import send
from apps.ops.audit import record
from apps.ops.config import setting
from apps.ops.groups import people_who_may

from .models import EntryLink, User

# An identifier rather than the product's name (see apps/accounts/addresses.py): changing it
# would invalidate every verification link already sent.
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


def user_from_token(token: str) -> tuple[User, str] | None:
    """The account the link was issued to and the address it was sent to. The link stops working
    when that address leaves the account, which is what stops an old link proving a new mailbox."""
    try:
        data = signing.loads(token, salt=VERIFY_SALT, max_age=VERIFY_MAX_AGE)
    except signing.BadSignature:
        return None
    user = User.objects.filter(pk=data.get("u")).first()
    address = (data.get("e") or "").lower()
    if not user or not user.addresses.filter(address__iexact=address).exists():
        return None
    return user, address


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
            groups=["member"] if is_class else [],
            joined_via=link,
            verification_deadline=now + timedelta(days=verification_days()) if is_class else None,
            confirmed=False,  # they typed it; the link they are sent proves it
            **profile,
        )
        if not is_class:
            user.is_active = False  # exists only once the address is confirmed
            user.save(update_fields=["is_active"])
    record(user, "account.joined_via_link", user, after={"link": link.pk, "kind": link.kind})
    send_verification(user, base_url)
    return user


def returned_through(link: EntryLink, user: User) -> None:
    """A member who left came back through this link.

    They come back as a member whatever kind of link it was: an officer admitted them once
    already, and the link is only the door they walked through (FR-125, 2026-09-19). Their old
    address is confirmed on the account, so there is nothing to verify either.
    """
    user.joined_via = link
    user.verification_deadline = None
    user.save(update_fields=["joined_via", "verification_deadline"])
    record(user, "account.returned_via_link", user, after={"link": link.pk, "kind": link.kind})


def complete_verification(user: User, base_url: str, address: str = "") -> str:
    """Marks the address verified; a community account becomes Provisional and officers are told.
    Returns a short description of what happened for the page."""
    from . import addresses as address_book

    rows = user.addresses.filter(address__iexact=address) if address else user.addresses.all()
    for row in rows:
        address_book.mark_confirmed(user, row.address)
    fields = []
    became_provisional = False
    if (
        not user.is_active
        and not user.has_access
        and user.joined_via
        and user.joined_via.kind == EntryLink.Kind.COMMUNITY
    ):
        user.is_active = True
        fields += ["is_active"]
        user.groups.set(Group.objects.filter(name="provisional"))
        became_provisional = True
    if fields:
        user.save(update_fields=fields)
    record(user, "email.verified", user)
    if became_provisional:
        notify_officers_of_provisional(user, base_url)
        return "provisional"
    return "verified"


def mark_verified(actor: User, user: User) -> None:
    """The officer's waiver (FR-120): counts as verification for the deadline and the badge."""
    from . import addresses as address_book

    for row in user.addresses.filter(confirmed=False):
        address_book.mark_confirmed(user, row.address, actor)
        record(actor, "email.verified_by_officer", user)


def notify_officers_of_provisional(user: User, base_url: str) -> None:
    url = base_url + reverse("member_detail", args=[user.pk])
    via = user.joined_via.label if user.joined_via else "a community link"
    for officer in people_who_may("view_member_records"):
        send(
            "account.provisional_notice",
            officer,
            "account",
            {"person": user, "via": via, "link": url},
        )


def admit(actor: User, user: User) -> None:
    from .services import set_access

    set_access(actor, user, ["member"], "admitted after review")
    send("account.admitted", user, "account")


def decline(actor: User, user: User, reason: str) -> None:
    from .services import set_access

    set_access(actor, user, [], f"declined: {reason}")
    send("account.declined", user, "account", {"reason": reason})


def pending_review():
    return (
        User.objects.filter(groups__name="provisional", is_active=True)
        .select_related("joined_via")
        .order_by("date_joined")
    )
