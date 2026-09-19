"""
Access groups: a named set of capabilities, and who is in one.

A group is a Django group, so nothing new had to be built to hold one, and a sysadmin can make
another. The groups a fresh installation starts with come from the club's configuration
(`access_groups` in club.yaml); after that they are the club's to change, and an import leaves an
edited group alone unless it is asked to reset.

Reading this module: `sync` writes configuration into groups, `capabilities_of` and `set_groups`
are what the pages use, and `people_who_may` answers "who should be told about this", which used
to be a query against the access ladder.
"""

from __future__ import annotations

from django.contrib.auth.models import Group, Permission
from django.db.models import Q

from .capabilities import APP_LABEL, CODENAMES, LABELS


class GroupRefused(Exception):
    """A change that would leave the club unable to run itself."""


def capabilities_held(user) -> set[str]:
    """What this account may do **right now**, which is the level its session acts at.

    A sysadmin who has dropped to Faculty Advisor appoints what an advisor appoints; that is
    what acting at a level means (apps.accounts.acting).
    """
    acting = getattr(user, "acting_capabilities", None)
    if acting is not None:
        return set(acting)
    from apps.accounts.acting import full_capabilities

    return full_capabilities(user)


def assignable_groups(actor):
    """The groups this person may put an account into.

    The rule, the advisor's on 2026-09-19: *"Faculty advisors should be able to appoint
    officers, members, and below. Officers should be able to appoint members, and below."*
    Written against capabilities rather than a ladder, because a club may invent a group this
    application has never heard of: **a group is yours to grant when everything it grants is
    something you already hold, and it does not hold everything you do.** A proper subset, so
    nobody appoints their own peer, and nobody appoints above themselves.
    """
    mine = capabilities_held(actor)
    out = []
    for group in Group.objects.order_by("name"):
        granted = {p.codename for p in group.permissions.all()}
        if granted < mine:
            out.append(group)
    return out


def may_set_access(actor, subject) -> bool:
    """Whether this person may decide which groups that account is in.

    Two halves, and the second matters as much as the first: you may only change an account
    that is **below** you. Without it an officer could edit the advisor's account and drop
    them to Member, taking the club over by demotion rather than by promotion.
    """
    if not actor.may("assign_groups"):
        return False
    at_the_top = actor.is_superuser and getattr(actor, "acting_capabilities", None) is None
    if subject.is_superuser:
        return at_the_top  # a sysadmin's account is a sysadmin's to change
    if subject.pk == actor.pk:
        # Your own access is yours to change only when you hold everything anyway, so there is
        # nothing to gain by it.
        return at_the_top
    return capabilities_held(subject) < capabilities_held(actor)


def permission(codename: str) -> Permission:
    return Permission.objects.get(content_type__app_label=APP_LABEL, codename=codename)


def sync(configured: list[dict] | None, *, reset: bool = False) -> dict:
    """Create the configured groups and give them their capabilities.

    A group that already exists keeps the capabilities it has, because a sysadmin may have
    changed them deliberately; `reset` puts the configuration back.
    """
    counts = {"created": 0, "updated": 0, "kept": 0}
    for row in configured or []:
        key = str(row.get("key") or "").strip()
        if not key:
            continue
        group, created = Group.objects.get_or_create(name=key)
        if created or reset:
            wanted = [c for c in (row.get("capabilities") or []) if c in CODENAMES]
            group.permissions.set(
                Permission.objects.filter(content_type__app_label=APP_LABEL, codename__in=wanted)
            )
            counts["created" if created else "updated"] += 1
        else:
            counts["kept"] += 1
    return counts


def summary_of(
    group_name: str, configured: list[dict] | None = None, added: list[str] | None = None
) -> str:
    """One line saying what a level lets somebody do, in words.

    The page used to offer "Faculty advisor · 16 capabilities", which is a row count from a
    database table and tells a reader nothing. The club's configuration carries a sentence for
    each group it ships; a group invented in the interface gets one built from the capabilities
    it adds to the level below it.
    """
    for row in configured or []:
        if str(row.get("key")) == group_name and row.get("summary"):
            return str(row["summary"])
    things = [LABELS[c][0].lower() + LABELS[c][1:] for c in (added or []) if c in LABELS]
    if not things:
        return "Nothing beyond signing in and seeing your own account."
    if len(things) > 3:
        things = things[:3] + ["more besides"]
    if len(things) == 1:
        return things[0] + "."
    return ", ".join(things[:-1]) + ", and " + things[-1] + "."


def label_of(group: Group, configured: list[dict] | None = None) -> str:
    """The name a page shows. The configuration carries it; a group made in the interface is
    shown by its own name."""
    for row in configured or []:
        if str(row.get("key")) == group.name:
            return str(row.get("label") or group.name)
    return group.name.replace("_", " ").capitalize()


def capabilities_of(group: Group) -> list[tuple[str, str]]:
    """What a group lets its members do, in the order the capability list declares."""
    held = {p.codename for p in group.permissions.all()}
    return [(code, LABELS[code]) for code in CODENAMES if code in held]


def set_groups(actor, user, keys: list[str]) -> None:
    """Put an account in exactly these groups. The audit row names both sides, because this is
    the whole of what somebody may do."""
    from apps.ops.audit import record

    before = sorted(g.name for g in user.groups.all())
    user.groups.set(Group.objects.filter(name__in=keys))
    after = sorted(g.name for g in user.groups.all())
    if before != after:
        record(actor, "groups.changed", user, before={"groups": before}, after={"groups": after})


def people_who_may(codename: str):
    """Everyone who holds this capability: through a group, directly, or by being a superuser.

    Used where the application has to write to whoever is responsible for something, which is a
    question about capability rather than about rank.
    """
    from apps.accounts.models import User

    return (
        User.objects.filter(is_active=True)
        .filter(
            Q(is_superuser=True)
            | Q(
                groups__permissions__codename=codename,
                groups__permissions__content_type__app_label=APP_LABEL,
            )
            | Q(
                user_permissions__codename=codename,
                user_permissions__content_type__app_label=APP_LABEL,
            )
        )
        .distinct()
    )


def refuse_if_last(codename: str, *, leaving) -> None:
    """Keep at least one account able to do the thing that grants everything else. Without this
    a sysadmin can lock the club out of its own site in one edit."""
    remaining = people_who_may(codename).exclude(pk=getattr(leaving, "pk", None))
    if not remaining.exists():
        raise GroupRefused(
            f"somebody has to be able to {LABELS.get(codename, codename).lower()}; "
            "give it to another account first"
        )
