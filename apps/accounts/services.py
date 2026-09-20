"""Account operations shared by the templates and the API (TR-8)."""

from __future__ import annotations

import secrets
from datetime import timedelta

from django.utils import timezone

from apps.ops.audit import record
from apps.ops.config import setting
from apps.ops.groups import people_who_may

from .models import CallsignHistory, Invitation, User


def _supersede_open_invitations(
    actor: User, email: str, guardian_email: str, is_minor: bool
) -> int:
    """Withdraw any invitation to this person that is still open, and say how many.

    Nobody should hold two live links to the same account. Without this, pressing "Create
    invitation" twice left both working, so revoking one withdrew nothing, and the person was
    sent the invitation twice (the advisor found six of them on 2026-09-19). "Make a new link"
    has always replaced the old one; this is the same rule reached from the other button.
    """
    open_ones = Invitation.objects.filter(state=Invitation.State.CREATED)
    if email:
        open_ones = open_ones.filter(email=email.lower())
    elif is_minor and guardian_email:  # a minor with no address of their own (§2.4)
        open_ones = open_ones.filter(is_minor=True, guardian_email=guardian_email.lower())
    else:
        return 0
    count = 0
    for old in open_ones:
        revoke_invitation(actor, old)
        count += 1
    return count


def create_invitation(
    issuer: User,
    email: str,
    category: str,
    is_minor: bool = False,
    guardian_email: str = "",
    base_url: str = "",
) -> Invitation:
    """FR-2/FR-3: a single-use link the issuer can also hand over by other means (FR-104). The
    invitation message goes to the address (the guardian's for a minor) through the outbox
    (FR-76); `emailed_at` is set only if it was actually sent, so the issuer knows when delivery
    is theirs to do."""
    days = int(setting("defaults.invitation_expiry_days", 14))
    superseded = _supersede_open_invitations(issuer, email, guardian_email, is_minor)
    inv = Invitation.objects.create(
        email=email.lower(),
        category=category,
        is_minor=is_minor,
        guardian_email=guardian_email.lower(),
        issued_by=issuer,
        expires_at=timezone.now() + timedelta(days=days),
    )
    record(issuer, "invitation.created", inv, after={"email": inv.email, "category": category})
    inv.superseded = superseded  # for the page to say so; not a stored field
    from django.conf import settings as dj

    from apps.comms.services import send

    base_url = base_url or getattr(dj, "SITE_URL", "")
    to = [inv.guardian_email] if inv.is_minor and inv.guardian_email else [inv.email]
    msg = send(
        "invitation",
        None,
        "account",
        {
            "link": f"{base_url}/me/invite/{inv.token}/",
            "expires": inv.expires_at,
            "category": category,
        },
        to=to,
    )
    if msg.state == msg.State.SENT:
        inv.emailed_at = msg.sent_at
        inv.save(update_fields=["emailed_at"])
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


def set_access(actor: User, user: User, groups: list[str], reason: str = "") -> None:
    """Put an account in exactly these access groups, which is the whole of what it may do.

    This was `set_access_level`, a move up or down one ladder. The ladder is gone: a group is a
    named set of capabilities the club defines, and an account in no group can do nothing, which
    is what losing access means (the advisor's decision, 2026-09-17).
    """
    from apps.ops.groups import set_groups

    had_access = user.has_access
    set_groups(actor, user, groups)
    if user.has_access and (user.closure_requested_at or user.suspended_at):
        # An account somebody can use is not closed and not suspended, whichever way the access
        # was given back. Without this the two could disagree, and an account reading Closed
        # was in the announcement audience (found by the advisor, 2026-09-19).
        user.closure_requested_at = None
        user.closed_by = None
        user.suspended_at = None
        user.suspended_by = None
        user.suspended_reason = ""
        user.save(
            update_fields=[
                "closure_requested_at",
                "closed_by",
                "suspended_at",
                "suspended_by",
                "suspended_reason",
            ]
        )
    if reason:
        record(actor, "access.changed", user, after={"groups": sorted(groups), "reason": reason})
    if had_access and not user.has_access:
        from apps.events.services.notify import access_removed

        access_removed(actor, user)  # future sign-ups go, captains are told


def revoke_invitation(actor: User, inv: Invitation) -> None:
    """FR-3: the issuer (or any officer) can withdraw an invitation that has not been used."""
    if inv.state == Invitation.State.CREATED:
        inv.state = Invitation.State.REVOKED
        inv.save(update_fields=["state"])
        record(actor, "invitation.revoked", inv)


def reissue_invitation(actor: User, inv: Invitation, base_url: str = "") -> Invitation:
    """FR-3: a fresh link for the same person; the old one stops working."""
    revoke_invitation(actor, inv)
    return create_invitation(
        actor, inv.email, inv.category, inv.is_minor, inv.guardian_email, base_url=base_url
    )


def returning_account(address: str):
    """The account this address already belongs to, if the person is coming back.

    A member who left is **archived, not deleted** (FR-125), so inviting them again should find
    the record they had rather than start an empty one. The advisor, 2026-09-19: "if an archived
    member decides to come back... it searches the closed and archived membership to bring that
    account back, rather than creating a completely new account."

    Returns (account, why-not): an account that may be brought back, or None and a sentence
    saying why this address cannot be invited. A **suspended** account is not a returning
    member: somebody took its access away on purpose, and a faculty advisor lifts that (FR-91).
    """
    held = User.objects.by_address((address or "").strip()).first()
    if held is None:
        return None, ""
    if held.deleted_at:
        return None, "That address belonged to an account that was deleted."
    if held.status == "suspended":
        return None, (
            f"{held.full_name}'s account is suspended, so it cannot be invited back. "
            "A faculty advisor lifts a suspension."
        )
    if held.has_access:
        return None, (
            f"{held.full_name} already has an account with that address. "
            "Invite a different address, or find them under Members."
        )
    return held, ""


def bring_back(actor, user: User, password: str = "", **profile) -> User:
    """Return a closed or archived member to the club, with everything they had.

    Their callsign, agreements, participation and addresses are all still there; what changed
    is that they are a member again. A password is set when the person themselves is at the
    form, because they have just proved they hold the address.
    """
    was = user.status
    if user.is_archived:
        restore_member(actor, user)
    for field, value in profile.items():
        if value:
            setattr(user, field, value)
    if password:
        user.set_password(password)
    user.is_active = True
    user.save()
    readmit(actor, user)
    record(actor, "member.returned", user, before={"status": was, "archived": bool(was)})
    return User.objects.get(pk=user.pk)


def admit_from_invitation(inv: Invitation, password: str, **profile) -> User:
    """FR-5: completing the form admits the person as a Member with the invitation's category.

    An address that already belongs to a closed or archived account brings that account back
    instead of starting a new one (FR-125, 2026-09-19).
    """
    address = profile.get("email", "") or inv.email
    returning, _ = returning_account(address)
    if returning is not None:
        profile.pop("email", None)
        user = bring_back(inv.issued_by or returning, returning, password, **profile)
        inv.state = Invitation.State.COMPLETED
        inv.completed_at = timezone.now()
        inv.accepted_by = user
        inv.save(update_fields=["state", "completed_at", "accepted_by"])
        record(user, "application.completed", user, after={"invitation": inv.pk, "returned": True})
        _completion_notices(inv, user)
        return user
    user = User.objects.create_user(
        email=profile.pop("email", "") or inv.email,  # a minor's may differ (§2.4)
        password=password,
        category=inv.category,
        groups=["member"],
        under_18=inv.is_minor,
        **profile,
    )
    inv.state = Invitation.State.COMPLETED
    inv.completed_at = timezone.now()
    inv.accepted_by = user
    inv.save(update_fields=["state", "completed_at", "accepted_by"])
    record(
        user, "application.completed", user, after={"invitation": inv.pk, "category": inv.category}
    )
    _completion_notices(inv, user)
    return user


def _completion_notices(inv: Invitation, user: User) -> None:
    """FR-5, FR-76: the inviter and the officers are told who joined, with callsign and ULS name,
    so a wrong person or a mistyped callsign is caught after the fact; the member gets a welcome."""
    from django.conf import settings as dj
    from django.urls import reverse

    from apps.comms.services import send

    site = getattr(dj, "SITE_URL", "") or ""
    link = site + reverse("member_detail", args=[user.pk])
    lic = getattr(user, "license", None)
    uls_name = getattr(lic, "uls_name", "") if lic else ""
    recipients = {u.pk: u for u in people_who_may("invite_members")}
    if inv.issued_by and inv.issued_by.is_active:
        recipients[inv.issued_by.pk] = inv.issued_by
    for r in recipients.values():
        send(
            "account.completed",
            r,
            "account",
            {
                "person": user,
                "uls_name": uls_name or "",
                "invited_email": inv.email,
                "category": inv.category,
                "link": link,
            },
        )
    send("account.welcome", user, "account")


def apply_callsign(user: User, new_callsign: str, previous: str = "") -> dict:
    """FR-102, FR-16: set a callsign, look it up, and decide what happens to the name.

    Returns {"state": "matched" | "pending" | "unverified" | "none"}. With a ULS row whose name
    agrees with the name on file (or a member whose name already comes from ULS), the ULS name is
    applied and marked as such. With a row whose name differs beyond a middle name, nothing is
    replaced: the ULS name is held in `pending_uls_name` for the member to confirm or refuse.
    """
    from apps.credentials.models import UlsLicense
    from apps.credentials.services import names_match, refresh_license_from_local_table

    new_callsign = (new_callsign or "").upper().strip()
    if previous and previous != new_callsign:
        CallsignHistory.objects.create(user=user, callsign=previous)
        record(
            user,
            "callsign.changed",
            user,
            before={"callsign": previous},
            after={"callsign": new_callsign},
        )
    user.callsign = new_callsign
    user.pending_uls_name = {}
    if not new_callsign:
        user.name_from_uls = False
        user.save(update_fields=["callsign", "pending_uls_name", "name_from_uls"])
        return {"state": "none"}
    row = UlsLicense.objects.filter(callsign=new_callsign).first()
    if row is None:
        # The name on file came from the FCC's record for the callsign they just left, so it is
        # no longer the FCC's record for anything this account holds. The name itself stays,
        # because wiping somebody's name is not ours to do; what goes is the claim that the FCC
        # wrote it, which is what makes it read-only and what the page says about it (FR-4,
        # FR-8).
        user.name_from_uls = False
        user.save(update_fields=["callsign", "pending_uls_name", "name_from_uls"])
        refresh_license_from_local_table(user)
        return {"state": "unverified"}
    # FR-16: a differing ULS name is confirmed by the member even when the name on file came
    # from ULS for an earlier callsign; only a member with no name at all takes it unasked.
    if not (user.first_name or user.last_name) or names_match(
        user.first_name, user.last_name, row.first_name, row.last_name
    ):
        if row.first_name:
            user.first_name = row.first_name
        if row.last_name:
            user.last_name = row.last_name
        user.middle_name = row.middle_initial  # FR-4: the licensee's first, middle, and last
        user.name_from_uls = True
        user.save(
            update_fields=[
                "callsign",
                "pending_uls_name",
                "first_name",
                "middle_name",
                "last_name",
                "name_from_uls",
            ]
        )
        refresh_license_from_local_table(user)
        return {"state": "matched"}
    user.pending_uls_name = {
        "first": row.first_name,
        "middle": row.middle_initial,
        "last": row.last_name,
        "callsign": new_callsign,
        "previous": previous,
    }
    user.save(update_fields=["callsign", "pending_uls_name"])
    refresh_license_from_local_table(user)
    return {"state": "pending", "uls_name": f"{row.first_name} {row.last_name}".strip()}


def decide_uls_name(user: User, accept: bool) -> str:
    """FR-16: the member confirms the ULS name is theirs (it replaces the name on file) or says
    it is not (the callsign is rejected and the previous one restored). Audited either way."""
    from apps.credentials.services import refresh_license_from_local_table

    pending = user.pending_uls_name or {}
    if not pending:
        return "nothing pending"
    if accept:
        before = {"first_name": user.first_name, "last_name": user.last_name}
        user.first_name = pending.get("first") or user.first_name
        user.middle_name = pending.get("middle", user.middle_name)
        user.last_name = pending.get("last") or user.last_name
        user.name_from_uls = True
        user.pending_uls_name = {}
        user.save(
            update_fields=[
                "first_name",
                "middle_name",
                "last_name",
                "name_from_uls",
                "pending_uls_name",
            ]
        )
        record(
            user,
            "name.replaced_from_uls",
            user,
            before=before,
            after={
                "first_name": user.first_name,
                "last_name": user.last_name,
                "callsign": pending.get("callsign"),
            },
        )
        refresh_license_from_local_table(user)
        return "name replaced"
    rejected = user.callsign
    user.callsign = pending.get("previous") or ""
    user.pending_uls_name = {}
    user.save(update_fields=["callsign", "pending_uls_name"])
    CallsignHistory.objects.filter(user=user, callsign=user.callsign).delete()
    record(
        user,
        "callsign.rejected",
        user,
        before={"callsign": rejected},
        after={"callsign": user.callsign, "reason": "ULS name is not the member's"},
    )
    refresh_license_from_local_table(user)
    return "callsign rejected"


# ---------------------------------------- the archive of former members (FR-125, §4.3) ---


class ArchiveRefused(Exception):
    """Some accounts cannot leave active service while something still depends on them."""


def archive_member(actor: User, user: User, reason: str = "") -> None:
    """Put a former member into the archive: their record is kept whole and indefinitely, and it
    is read by a faculty advisor or a sysadmin.

    This is what the club does instead of deleting people. The advisor, 2026-09-17: "I don't
    really like the automatic deletion. Instead, can we have a method to archive members? Only
    faculty advisors and above can view the archive." Nothing is erased here: the name, callsign,
    addresses, participation, and signed agreements all stay. What changes is that the account
    stops signing in, leaves the directory and every audience, and is read in one place.
    """
    if user.is_archived:
        return
    if user.wards.filter(active=True).exists():
        raise ArchiveRefused(
            "a guardian is archived once every linked minor has been converted, re-linked, or archived"
        )
    # An archived account is never one somebody can still use, so archiving one that still has
    # access closes it in the same act (the advisor, 2026-09-19: "Faculty Advisors and above
    # should be able to Close and archive accounts without suspending").
    if user.has_access:
        close_account(actor, user, reason or "archived")
        user.refresh_from_db()
    if not _someone_else_can_administer(user):
        raise ArchiveRefused("the last account that can run the site cannot be archived")
    user.archived_at = timezone.now()
    user.archived_reason = (reason or "").strip()[:200]
    # The password stops working too. No access already refuses every page, but an account
    # nobody is a member of should not authenticate at all.
    user.is_active = False
    user.save(update_fields=["archived_at", "archived_reason", "is_active"])
    record(actor, "member.archived", user, after={"reason": user.archived_reason})


def restore_member(actor: User, user: User) -> None:
    """Take a record out of the archive, and **leave its status alone**.

    Archiving and closing are two dimensions now (the advisor, 2026-09-19): the archive is
    where a record is put away, and the status is where the person stands with the club. So an
    account comes out of the archive exactly as it went in, Closed or Suspended, and somebody
    gives it access back as a separate, deliberate act. Nothing was lost while it was away.
    """
    if not user.is_archived:
        return
    before = {"archived_at": user.archived_at.isoformat(), "reason": user.archived_reason}
    user.archived_at = None
    user.archived_reason = ""
    user.is_active = True
    user.save(update_fields=["archived_at", "archived_reason", "is_active"])
    record(actor, "member.restored", user, before=before, after={"status": user.status})


def close_account(actor: User, user: User, reason: str = "") -> None:
    """Close somebody's account for them: they have left, without anybody being suspended.

    The advisor, 2026-09-19: "Faculty Advisors and above should be able to Close and archive
    accounts without suspending." A closure is a departure, a suspension is a decision about
    somebody's conduct, and the two should not have to be confused to file a graduating member.
    """
    user.closure_requested_at = timezone.now()
    user.closed_by = actor if actor.pk != user.pk else None
    user.suspended_at = None
    user.suspended_by = None
    user.suspended_reason = ""
    user.save(
        update_fields=[
            "closure_requested_at",
            "closed_by",
            "suspended_at",
            "suspended_by",
            "suspended_reason",
        ]
    )
    set_access(actor, user, [], reason or "closed")


def suspend(actor: User, user: User, reason: str) -> None:
    """Take an account's access away, with a reason (FR-91).

    An officer may do this to an account below them, because something can happen at the station
    on a Tuesday night; only a faculty advisor lifts it (§2.3, the advisor's rule of
    2026-09-19). The reason is kept on the account, not only in the audit log, because the
    person deciding whether to let them back in needs to read it.
    """
    user.suspended_at = timezone.now()
    user.suspended_by = actor if actor.pk != user.pk else None
    user.suspended_reason = (reason or "").strip()[:200]
    user.closure_requested_at = None  # a suspension supersedes a closure
    user.closed_by = None
    user.save(
        update_fields=[
            "suspended_at",
            "suspended_by",
            "suspended_reason",
            "closure_requested_at",
            "closed_by",
        ]
    )
    set_access(actor, user, [], reason or "suspended")


def readmit(actor: User, user: User, groups: list[str] | None = None) -> None:
    """Give a closed or suspended account access again, as a member.

    Whoever held an officer's place before comes back a member and is re-appointed by somebody
    who may appoint one (§2.3): coming back is not the moment to hand privileges out.
    """
    was = user.status
    user.suspended_at = None
    user.suspended_by = None
    user.suspended_reason = ""
    user.closure_requested_at = None
    user.closed_by = None
    user.save(
        update_fields=[
            "suspended_at",
            "suspended_by",
            "suspended_reason",
            "closure_requested_at",
            "closed_by",
        ]
    )
    set_access(actor, user, groups or ["member"], "readmitted")
    record(actor, "member.readmitted", user, before={"status": was})


def _someone_else_can_administer(user: User) -> bool:
    """Whether anybody but this account can still run the site.

    Two things have to survive, and they stopped being the same thing on 2026-09-19, when
    officers and advisors gained a **bounded** form of "decide which groups an account is in"
    (§2.3): it appoints members and officers, and it cannot make a sysadmin, reach the club's
    settings, or open the Django admin. So the last sysadmin is still the last sysadmin even in
    a club full of officers who can appoint.
    """
    from apps.ops.groups import people_who_may

    others = User.objects.filter(is_active=True).exclude(pk=user.pk)
    if user.is_superuser and not others.filter(is_superuser=True).exists():
        return False
    return people_who_may("assign_groups").exclude(pk=user.pk).exists()


def archived_members():
    """Everyone in the archive, most recently archived first."""
    return User.objects.filter(archived_at__isnull=False).order_by("-archived_at")


# ------------------------------------------------------ closure and deletion (FR-11, FR-118) ---


def request_closure(user: User) -> None:
    """FR-11: the member asks for their account to be closed. No access at once; the retention
    record is kept as the club's own, and an advisor archives it when they get to it."""
    user.closure_requested_at = timezone.now()
    user.save(update_fields=["closure_requested_at"])
    set_access(user, user, [], "closure requested by the member")
    from apps.comms.services import send

    for s in User.objects.filter(is_superuser=True, is_active=True):
        send("account.closure_requested", s, "account", {"person": user})


class DeletionRefused(Exception):
    pass


def deletion_effects(user: User) -> dict:
    """What deleting this account will do, for the confirmation page (FR-118)."""
    from apps.credentials.models import SignedAgreement
    from apps.events.models import SignUp

    now = timezone.now()
    return {
        "future_signups": SignUp.objects.filter(
            user=user, slot__end__gte=now, slot__cancelled=False
        ).count(),
        "past_signups": SignUp.objects.filter(user=user, slot__end__lt=now).count(),
        "agreements": SignedAgreement.objects.filter(user=user).count(),
        "wards": user.wards.filter(active=True).count() if hasattr(user, "wards") else 0,
        "is_last_sysadmin": not _someone_else_can_administer(user),
    }


def delete_account(actor: User, user: User, reason: str) -> dict:
    """FR-118: irreversible. Future sign-ups are canceled and their captains told; every
    identifying field is removed and the row stays as "deleted member" so past rosters and
    participation counts keep their shape; signed agreements and their PDFs stay for the §4.3
    period and the retention job purges them; the audit log keeps its entries and records this."""
    from apps.accounts.models import NotificationPreference, PushSubscription
    from apps.events.models import ResponsibleAdult
    from apps.events.services.notify import access_removed

    effects = deletion_effects(user)
    if effects["is_last_sysadmin"]:
        raise DeletionRefused("the last remaining sysadmin account cannot be deleted")
    if effects["wards"]:
        raise DeletionRefused(
            "a guardian is deleted only after every linked minor has been converted, re-linked, or deleted"
        )
    withdrawn = access_removed(actor, user)  # future sign-ups go, captains told
    ResponsibleAdult.objects.filter(signup__user=user).delete()
    ResponsibleAdult.objects.filter(member=user).update(member=None)
    PushSubscription.objects.filter(user=user).delete()
    NotificationPreference.objects.filter(user=user).delete()
    user.guardianships.all().delete()
    if hasattr(user, "wards"):
        user.wards.all().delete()
    CallsignHistory.objects.filter(user=user).delete()
    before = {
        "addresses": [a.address for a in user.addresses.all()],
        "callsign": user.callsign,
        "name": user.full_name,
    }
    user.first_name, user.middle_name, user.last_name, user.preferred_name = (
        "Deleted",
        "",
        "member",
        "",
    )
    # An account is its key, so nothing has to stand in for the address. The sign-in library's
    # copies go with the rows, or a deleted account would still answer to its old address.
    from .addresses import mirror

    user.addresses.all().delete()
    mirror(user)
    user.cell_phone = user.callsign = ""
    user.name_from_uls = False
    user.pending_uls_name = {}
    user.club_positions = []
    # The subscriptions are already gone above; the switch that governed them is a preference
    # of the person's, and means nothing on an account that cannot sign in.
    user.push_enabled = False
    user.groups.clear()
    user.is_active = False
    # `last_login` stays. It is the one fact about the person kept on purpose: the advisor,
    # 2026-09-19, "last_login may still be good for audit or investigation purposes." Without
    # it there is no way to answer when a deleted account was last used.
    user.deleted_at = timezone.now()
    user.set_unusable_password()
    user.save()
    if hasattr(user, "license"):
        user.license.delete()
    record(
        actor,
        "account.deleted",
        user,
        before=before,
        after={
            "reason": reason,
            "signups_withdrawn": withdrawn,
            "agreements_kept": effects["agreements"],
        },
    )
    return {"withdrawn": withdrawn, **effects}
