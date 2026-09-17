"""
A member's addresses, and which of them sign them in.

The account's sign-in address always signs them in: it is the account's identity. Any other
address on the account, the institution one or the personal one, signs them in once it is
verified, either by following a link sent to it or because an officer said so. Until then the
address still receives club mail, so nothing a member relies on waits for verification: no part
of this system may depend on mail arriving.

Verified addresses live in the sign-in library's own table, which is what it consults when
someone signs in or asks for a reset, and which holds a verified address to one account. A
verified address is never removed automatically, so correcting a sign-in address cannot take
away the way someone gets in.
"""

from __future__ import annotations

from allauth.account.models import EmailAddress
from django.core import signing
from django.db import IntegrityError, transaction
from django.urls import reverse

from apps.ops.audit import record

from .models import User

SALT = "arcops.verify-address"
MAX_AGE = 14 * 24 * 3600


class AddressInUse(Exception):
    """Another account has already proved this address."""


def on_file(user: User) -> list[str]:
    """Every address the account carries, the sign-in one first, without repeats."""
    out: list[str] = []
    for value in (user.email, user.institution_email, user.personal_email):
        value = (value or "").strip().lower()
        if value and value not in out:
            out.append(value)
    return out


def verified(user: User) -> set[str]:
    """The addresses that sign this member in: the sign-in address, and any proved one."""
    rows = EmailAddress.objects.filter(user=user, verified=True).values_list("email", flat=True)
    return {(user.email or "").lower()} | {e.lower() for e in rows}


def state(user: User) -> list[dict]:
    """Each address with its standing, for the profile and the member page."""
    proved = verified(user)
    delivery = {
        (user.institution_email or "").lower(): user.institution_email_delivery,
        (user.personal_email or "").lower(): user.personal_email_delivery,
    }
    out = []
    for address in on_file(user):
        is_sign_in = address == (user.email or "").lower()
        out.append(
            {
                "address": address,
                "is_sign_in": is_sign_in,
                "verified": address in proved,
                # the sign-in address always receives what the others decline
                "delivery": delivery.get(address, True) or is_sign_in,
            }
        )
    return out


def mark_verified(user: User, address: str, actor: User | None = None) -> None:
    """Say that this address belongs to this member: from their own confirmation link, or from
    an officer who knows it does. Refused when another account has already proved it."""
    address = address.strip().lower()
    if address not in on_file(user):
        raise AddressInUse("That address is not on this account.")
    taken = EmailAddress.objects.filter(email__iexact=address, verified=True).exclude(user=user)
    if taken.exists():
        raise AddressInUse("Another account has already confirmed that address.")
    try:
        with transaction.atomic():
            row, _ = EmailAddress.objects.get_or_create(
                user=user, email=address, defaults={"verified": True}
            )
            if not row.verified:
                row.verified = True
                row.save(update_fields=["verified"])
            if address == (user.email or "").lower() and not user.email_verified_at:
                from django.utils import timezone

                user.email_verified_at = timezone.now()
                user.save(update_fields=["email_verified_at"])
    except IntegrityError as exc:  # the library holds a verified address to one account
        raise AddressInUse("Another account has already confirmed that address.") from exc
    record(actor or user, "email.address_verified", user, after={"address": address})


def unverify(user: User, address: str, actor: User) -> None:
    """Take an address's standing away; the sign-in address keeps working regardless."""
    address = address.strip().lower()
    EmailAddress.objects.filter(user=user, email__iexact=address).delete()
    record(actor, "email.address_unverified", user, after={"address": address})


def token(user: User, address: str) -> str:
    return signing.dumps({"u": user.pk, "a": address.strip().lower()}, salt=SALT)


def from_token(value: str) -> tuple[User, str] | None:
    try:
        data = signing.loads(value, salt=SALT, max_age=MAX_AGE)
    except signing.BadSignature:
        return None
    user = User.objects.filter(pk=data.get("u")).first()
    address = (data.get("a") or "").lower()
    if not user or address not in on_file(user):
        return None
    return user, address


def send_confirmation(user: User, address: str, base_url: str = "") -> None:
    """A link to the address itself, which is the only thing that proves it."""
    from django.conf import settings as dj

    from apps.comms.services import send

    base_url = base_url or getattr(dj, "SITE_URL", "")
    link = base_url + reverse("verify_address", args=[token(user, address)])
    send(
        "account.verify_address",
        user,
        "account",
        {"link": link, "address": address},
        to=[address],  # to the address being proved, never to the others
    )


def sync(user: User, actor: User | None = None, base_url: str = "") -> list[str]:
    """Called after the addresses on an account change. A proved address that is no longer on
    the account loses its standing; a new one is sent a confirmation link. Returns the addresses
    a link went to."""
    current = set(on_file(user))
    for row in EmailAddress.objects.filter(user=user):
        if row.email.lower() not in current:
            row.delete()
    sent = []
    proved = verified(user)
    for address in current:
        if address not in proved:
            send_confirmation(user, address, base_url)
            sent.append(address)
    return sent
