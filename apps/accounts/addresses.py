"""
The addresses on an account, and what each of them does.

A person may hold more than one address. Any address they have confirmed signs them in; an
address they have not confirmed still receives club mail, so nothing a member relies on waits
for delivery. No address is the account's identity: that is `User.public_id`, which never
changes and is never shown.

Confirmed addresses are mirrored into the sign-in library's own table, which is what it
consults when someone signs in or asks for a reset, and whose constraint holds an address to one
account. The mirror runs one way, from here.
"""

from __future__ import annotations

from allauth.account.models import EmailAddress
from django.core import signing
from django.db import IntegrityError, transaction
from django.urls import reverse

from apps.ops.audit import record
from apps.ops.config import institution_email_domain

from .models import Address, User

# Lower case on purpose: a salt is an identifier, not the product's name. Changing it would
# invalidate every confirmation link already in somebody's mailbox.
SALT = "arcops.verify-address"
MAX_AGE = 14 * 24 * 3600


class AddressInUse(Exception):
    """Another account has already confirmed this address."""


class LastAddress(Exception):
    """An account keeps at least one address."""


def kind_for(address: str) -> str:
    """An address at the club's institution domain is the institution one; anything else is
    personal. The club's domain is configuration, so another club's rule follows its own."""
    domain = (institution_email_domain() or "").lower()
    if domain and address.lower().endswith("@" + domain):
        return Address.Kind.INSTITUTION
    return Address.Kind.PERSONAL


def on_file(user: User) -> list[Address]:
    return list(user.addresses.all())


def confirmed(user: User) -> set[str]:
    """The addresses this person has proved."""
    return {a.address.lower() for a in user.addresses.filter(confirmed=True)}


def sign_in_addresses(user: User) -> set[str]:
    """The addresses that sign this person in: the ones they have proved, and, while a class
    link's confirmation window is still open, the address they joined with. Past that deadline
    the account is signed out until something confirms it, which is FR-120's whole point."""
    from django.utils import timezone

    within_window = bool(user.verification_deadline and user.verification_deadline > timezone.now())
    return {a.address.lower() for a in user.addresses.all() if a.confirmed or within_window}


def for_delivery(user: User) -> list[str]:
    """Where club mail goes. With no switch on, every address receives, because an unreachable
    member is worse than an extra copy."""
    rows = on_file(user)
    wanted = [a.address for a in rows if a.delivery]
    return wanted or [a.address for a in rows]


def display(user: User) -> str:
    """The one address to show where a page or an export has room for one: a confirmed address
    that receives mail, else any confirmed one, else any at all."""
    rows = on_file(user)
    for test in (lambda a: a.confirmed and a.delivery, lambda a: a.confirmed, lambda a: True):
        for row in rows:
            if test(row):
                return row.address
    return ""


def add(
    user: User,
    address: str,
    *,
    kind: str | None = None,
    confirmed: bool = False,
    delivery: bool = True,
    actor: User | None = None,
) -> Address:
    """Put an address on an account. Confirming it here is for the paths that already prove it:
    an invitation opened from that mailbox, an entry link, an officer who knows."""
    address = (address or "").strip().lower()
    if not address:
        raise ValueError("an address is required")
    if confirmed:
        _refuse_if_taken(user, address)
    row, created = Address.objects.get_or_create(
        user=user,
        address=address,
        defaults={"kind": kind or kind_for(address), "confirmed": confirmed, "delivery": delivery},
    )
    if not created:
        row.kind = kind or row.kind
        row.delivery = delivery
        if confirmed and not row.confirmed:
            row.confirmed = True
        row.save(update_fields=["kind", "delivery", "confirmed"])
    mirror(user)
    if created and actor:
        record(actor, "address.added", user, after={"address": address})
    return row


def remove(user: User, address: str, actor: User) -> None:
    """Take an address off an account. The last one stays: an account with no address has no way
    back in but the one-time password, and nothing to reach its owner by."""
    address = (address or "").strip().lower()
    rows = on_file(user)
    if len([a for a in rows if a.address.lower() != address]) == 0:
        raise LastAddress("An account keeps at least one address.")
    Address.objects.filter(user=user, address__iexact=address).delete()
    mirror(user)
    record(actor, "address.removed", user, after={"address": address})


def mark_confirmed(user: User, address: str, actor: User | None = None) -> None:
    """Say the address belongs to this person: from their own link, or from an officer who
    knows it does, which is what keeps signing in from depending on mail arriving."""
    address = (address or "").strip().lower()
    row = Address.objects.filter(user=user, address__iexact=address).first()
    if row is None:
        raise ValueError("That address is not on this account.")
    _refuse_if_taken(user, address)
    if not row.confirmed:
        row.confirmed = True
        row.save(update_fields=["confirmed"])
    mirror(user)
    record(actor or user, "address.confirmed", user, after={"address": address})


def unconfirm(user: User, address: str, actor: User) -> None:
    """Take an address's standing away; it keeps receiving mail and stops signing anyone in."""
    address = (address or "").strip().lower()
    Address.objects.filter(user=user, address__iexact=address).update(confirmed=False)
    mirror(user)
    record(actor, "address.unconfirmed", user, after={"address": address})


def _refuse_if_taken(user: User, address: str) -> None:
    taken = Address.objects.filter(address__iexact=address, confirmed=True).exclude(user=user)
    if taken.exists():
        raise AddressInUse("Another account has already confirmed that address.")


def mirror(user: User) -> None:
    """Keep the sign-in library's table in step with the confirmed rows here."""
    want = sign_in_addresses(user)
    try:
        with transaction.atomic():
            EmailAddress.objects.filter(user=user).exclude(email__in=want).delete()
            for address in want:
                EmailAddress.objects.get_or_create(
                    user=user, email=address, defaults={"verified": True}
                )
                EmailAddress.objects.filter(user=user, email=address, verified=False).update(
                    verified=True
                )
    except IntegrityError as exc:  # the library holds a confirmed address to one account
        raise AddressInUse("Another account has already confirmed that address.") from exc


def token(user: User, address: str) -> str:
    return signing.dumps({"u": user.pk, "a": address.strip().lower()}, salt=SALT)


def from_token(value: str) -> tuple[User, str] | None:
    try:
        data = signing.loads(value, salt=SALT, max_age=MAX_AGE)
    except signing.BadSignature:
        return None
    user = User.objects.filter(pk=data.get("u")).first()
    address = (data.get("a") or "").lower()
    if not user or not Address.objects.filter(user=user, address__iexact=address).exists():
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


def state(user: User) -> list[dict]:
    """Each address with its standing, for the profile and the member page."""
    rows = on_file(user)
    return [
        {
            "address": a.address,
            "kind": a.get_kind_display(),
            "confirmed": a.confirmed,
            "delivery": a.delivery,
            "can_remove": len(rows) > 1,
        }
        for a in rows
    ]
