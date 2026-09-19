"""
The controls that change the addresses on an account, shared by the member's own profile and an
officer's view of someone else.

Both pages post to their own URL and hand the request here, so an address behaves the same
whoever is looking at it. The rules live in `apps.accounts.addresses`; this module is the part
that reads a form and says what happened.
"""

from __future__ import annotations

from django.contrib import messages

from . import addresses
from .models import User

ACTIONS = (
    "address_add",
    "address_remove",
    "address_delivery",
    "address_confirm",
    "address_unconfirm",
    "address_send_link",
)


def may_edit(actor: User, subject: User) -> bool:
    """A member holds their own addresses; an officer can add one and confirm one, because
    somebody has to be able to help a member who has lost the mailbox they signed up with."""
    return actor.pk == subject.pk or actor.may("manage_member_addresses")


def may_correct(actor: User, subject: User) -> bool:
    """Whether this person may take an address, its confirmation, or its club mail off somebody
    else's account.

    An officer may not: the advisor, 2026-09-19, "They should not be able to stop an email
    address from signing them in, or turn off a users club email... Users can adjust email
    settings in their own accounts." An officer who needs to shut an account out suspends it,
    where the act is named, reasoned and lifted by somebody answerable for it (FR-91).
    """
    return actor.pk == subject.pk or actor.may("correct_member_addresses")


def handle(request, subject: User) -> bool:
    """Act on an address control. Returns whether this request was one, so the page can fall
    through to its own form when it was not."""
    action = request.POST.get("action", "")
    if action not in ACTIONS:
        return False
    actor = request.user
    if not may_edit(actor, subject):
        messages.error(request, "You cannot change the addresses on that account.")
        return True
    is_self = actor.pk == subject.pk
    who = "you" if is_self else subject.display_first
    address = request.POST.get("address", "").strip().lower()
    base_url = f"{request.scheme}://{request.get_host()}"

    if action == "address_add":
        if not address:
            messages.error(request, "Type the address you want to add.")
        elif address in {a.address for a in addresses.on_file(subject)}:
            messages.info(request, f"{address} is already on the account.")
        else:
            try:
                addresses.add(subject, address, actor=actor)
            except addresses.AddressInUse as exc:
                messages.error(request, str(exc))
            else:
                addresses.send_confirmation(subject, address, base_url)
                messages.success(
                    request,
                    f"{address} is on the account. A confirmation link is on its way to it; "
                    f"until {who} open{'' if is_self else 's'} that link it receives club mail "
                    "without signing anyone in.",
                )
        return True

    if action in ("address_remove", "address_delivery") and not may_correct(actor, subject):
        messages.error(
            request,
            "A member sets their own club mail and takes their own addresses off. To shut an "
            "account out, suspend it.",
        )
        return True

    if action == "address_remove":
        try:
            addresses.remove(subject, address, actor)
        except addresses.LastAddress as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, f"{address} is off the account.")
        return True

    if action == "address_delivery":
        row = subject.addresses.filter(address__iexact=address).first()
        if row is None:
            messages.error(request, "That address is not on the account.")
        elif row.delivery and len([a for a in addresses.on_file(subject) if a.delivery]) == 1:
            messages.error(
                request,
                "Club mail has to reach at least one address. Turn another one on first.",
            )
        else:
            row.delivery = not row.delivery
            row.save(update_fields=["delivery"])
            state = "goes to" if row.delivery else "no longer goes to"
            messages.success(request, f"Club mail {state} {address}.")
        return True

    if action == "address_confirm":
        if is_self:  # proving your own address means opening the link sent to it
            messages.error(request, "Open the link sent to that address to confirm it.")
            return True
        if address not in {a.address for a in addresses.on_file(subject)}:
            messages.error(request, "That address is not on the account.")
            return True
        try:
            addresses.mark_confirmed(subject, address, actor)
        except addresses.AddressInUse as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, f"{address} is confirmed; {who} can sign in with it.")
        return True

    if action == "address_unconfirm":
        if not may_correct(actor, subject) or is_self:
            messages.error(
                request,
                "Taking an address's confirmation away is a sysadmin's. To shut an account out, "
                "suspend it.",
            )
        elif len(addresses.confirmed(subject)) == 1 and address in addresses.confirmed(subject):
            messages.error(
                request,
                "That is the only confirmed address on the account, so it is the only way in.",
            )
        else:
            addresses.unconfirm(subject, address, actor)
            messages.success(request, f"{address} no longer signs this member in.")
        return True

    if action == "address_send_link":
        if address not in {a.address for a in addresses.on_file(subject)}:
            messages.error(request, "That address is not on the account.")
        elif address in addresses.confirmed(subject):
            messages.info(request, f"{address} is already confirmed.")
        else:
            addresses.send_confirmation(subject, address, base_url)
            messages.success(request, f"A confirmation link is on its way to {address}.")
        return True

    return True
