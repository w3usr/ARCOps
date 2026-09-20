"""What a faculty advisor may set on an account.

The advisor, 2026-09-20: *"Faculty Advisors need to be able to set Category, Club Position, and
Access"*, with the ladder reaching their own level. So the advisor group gains two capabilities:

* `edit_member_privileges`, which is the category, the names, and the student fields;
* `appoint_peers`, which lets the access list include a group as capable as their own, so an
  advisor can make a second advisor.

Sysadmin is untouched. It is a checkbox rather than a group, and it stays a sysadmin's to tick.
A club that disagrees unticks either capability on the Access groups page.
"""

from django.db import migrations

CAPABILITIES = ("edit_member_privileges", "appoint_peers")
GROUPS = ("advisor",)
LABELS = {
    "edit_member_privileges": "Edit another member's category, names, and student details",
    "appoint_peers": "Appoint somebody to your own level, not only below it",
}


def _permissions(apps):
    """The rows, creating any the capability list has gained since the last deploy: `migrate`
    runs before `club_import`, so a brand-new capability has no row yet when this runs."""
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    content_type, _ = ContentType.objects.get_or_create(app_label="ops", model="capability")
    rows = []
    for codename in CAPABILITIES:
        row, _ = Permission.objects.get_or_create(
            content_type=content_type, codename=codename, defaults={"name": LABELS[codename]}
        )
        rows.append(row)
    return rows


def grant(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    rows = _permissions(apps)
    for group in Group.objects.filter(name__in=GROUPS):
        group.permissions.add(*rows)


def take_back(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    rows = _permissions(apps)
    for group in Group.objects.filter(name__in=GROUPS):
        group.permissions.remove(*rows)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0021_positions_are_a_list"),
        ("ops", "0007_the_position_field_is_a_list"),
    ]
    operations = [migrations.RunPython(grant, take_back)]
