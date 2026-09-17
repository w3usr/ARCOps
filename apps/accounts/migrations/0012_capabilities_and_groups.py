"""
The access ladder becomes groups of capabilities.

The advisor, 2026-09-17: "I am thinking the correct way to do this is actually have access be
item-by-item, and then define configurable access groups (member, officer, faculty advisor,
etc). Systemic is superuser."

Each of the five levels becomes the group of the same name, holding the capabilities that level
used to imply, and every account joins the group its level named. A sysadmin becomes a Django
superuser, which is what holds every capability without naming any of them. `access_level` stays
for now and is dropped once nothing reads it.

The groups are the club's afterwards: a sysadmin edits them, and may make others. What this
migration writes is a starting point that matches the behaviour of the day it ran.
"""

from django.db import migrations

# level -> the capabilities that level implied, from the requirements' table of who may do what
GROUPS = {
    "provisional": [],
    "member": ["view_directory"],
    "officer": [
        "view_directory",
        "view_member_records",
        "view_participant_contacts",
        "invite_members",
        "set_club_position",
        "manage_member_addresses",
        "create_events",
        "manage_events",
        "manage_signups",
        "send_announcements",
        "view_outbox",
        "view_reports",
    ],
    "advisor": [
        "view_directory",
        "view_member_records",
        "view_participant_contacts",
        "invite_members",
        "set_club_position",
        "manage_member_addresses",
        "create_events",
        "manage_events",
        "manage_signups",
        "send_announcements",
        "view_outbox",
        "view_reports",
        "approve_agreements",
        "convert_minor_accounts",
        "archive_members",
        "view_archive",
    ],
}


GROUPS["sysadmin"] = "everything"  # filled in below, from the capability list itself


def ladder_into_groups(apps, schema_editor):
    from apps.ops.capabilities import CODENAMES, ensure_permissions

    # The permission rows are written by a signal that fires after every migration has run, from
    # a frozen copy of the model's Meta. This migration needs them now, and needs the list as it
    # stands rather than as it stood when an earlier migration was written.
    ensure_permissions(apps.get_model("auth", "Permission"), apps.get_model("contenttypes", "ContentType"))
    GROUPS["sysadmin"] = list(CODENAMES)

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    User = apps.get_model("accounts", "User")

    for name, codenames in GROUPS.items():
        group, _ = Group.objects.get_or_create(name=name)
        group.permissions.set(
            Permission.objects.filter(content_type__app_label="ops", codename__in=codenames)
        )

    groups = {g.name: g for g in Group.objects.filter(name__in=GROUPS)}
    for user in User.objects.all():
        if user.access_level == "sysadmin":
            # the group holds every capability, and the superuser flag opens the Django admin
            user.is_superuser = True
            user.save(update_fields=["is_superuser"])
            user.groups.add(groups["sysadmin"])
        elif user.access_level in groups:
            user.groups.add(groups[user.access_level])
        # "none" joins nothing, which is what having no access now means


def groups_back_into_the_ladder(apps, schema_editor):
    """Enough to step back safely: the level each account's group names."""
    User = apps.get_model("accounts", "User")
    for user in User.objects.all():
        names = {g.name for g in user.groups.all()}
        for level in ("advisor", "officer", "member", "provisional"):
            if level in names:
                user.access_level = level
                break
        else:
            user.access_level = "sysadmin" if user.is_superuser else "none"
        user.save(update_fields=["access_level"])


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0011_archive_former_members"),
        ("ops", "0002_capabilities"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [migrations.RunPython(ladder_into_groups, groups_back_into_the_ladder)]
