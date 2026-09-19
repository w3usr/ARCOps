"""Officers and advisors may appoint, within the bound the code enforces.

The advisor, 2026-09-19: *"Faculty advisors should be able to appoint officers, members, and
below. Officers should be able to appoint members, and below."* The capability itself is old;
what is new is that `apps.ops.groups` bounds it, so holding it lets you grant only a group whose
capabilities you already hold, on an account below you.

It is a data migration rather than a line in the club's configuration because the configuration
import deliberately leaves an existing group alone (a sysadmin may have changed it on purpose),
and this is a decision about what the application means by "officer" rather than a preference.
A club that disagrees unticks it on the Access groups page afterwards.
"""

from django.db import migrations

GROUPS = ("officer", "advisor")
CAPABILITY = "assign_groups"


def grant(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    perm = Permission.objects.filter(content_type__app_label="ops", codename=CAPABILITY).first()
    if perm is None:
        return
    for group in Group.objects.filter(name__in=GROUPS):
        group.permissions.add(perm)


def take_back(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    perm = Permission.objects.filter(content_type__app_label="ops", codename=CAPABILITY).first()
    if perm is None:
        return
    for group in Group.objects.filter(name__in=GROUPS):
        group.permissions.remove(perm)


class Migration(migrations.Migration):
    dependencies = [("accounts", "0013_access_becomes_groups")]
    operations = [migrations.RunPython(grant, take_back)]
