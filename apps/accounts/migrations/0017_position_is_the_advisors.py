"""Setting a club position is the faculty advisor's.

Only faculty advisors and above set the club position. An officer still appoints members
(§2.3); who holds which office is the advisor's to record.
A club that disagrees ticks it back on the Access groups page.
"""

from django.db import migrations

CAPABILITY = "set_club_position"
GROUPS = ("officer",)


def take_back(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    perm = Permission.objects.filter(content_type__app_label="ops", codename=CAPABILITY).first()
    if perm is None:
        return
    for group in Group.objects.filter(name__in=GROUPS):
        group.permissions.remove(perm)


def grant(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    perm = Permission.objects.filter(content_type__app_label="ops", codename=CAPABILITY).first()
    if perm is None:
        return
    for group in Group.objects.filter(name__in=GROUPS):
        group.permissions.add(perm)


class Migration(migrations.Migration):
    dependencies = [("accounts", "0016_advisors_lift_suspensions")]
    operations = [migrations.RunPython(take_back, grant)]
