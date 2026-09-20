"""The station computer password is the faculty advisor's to rotate.

The page that sets it was a sysadmin's alone and had no way in but a typed address, so nobody
who did not already know the URL could rotate it at all.

    There needs to be a UI entry point for the faculty advisor and above to rotate this.
    — NAF, 2026-09-20

The advisor answers to the University for station access, which is the same standing that makes
them the approver of the agreement the password goes with, so the capability moves to them and
Advisor tools carries the link. Granted here rather than left to the configuration, because the
import leaves an existing group's capabilities alone by design: a club may have changed them.
"""

from django.db import migrations

CAPABILITY = "rotate_shared_secret"
GROUPS = ("advisor",)


def grant(apps, schema_editor):
    from apps.ops.capabilities import ensure_permissions

    ensure_permissions(
        apps.get_model("auth", "Permission"), apps.get_model("contenttypes", "ContentType")
    )
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
    dependencies = [("accounts", "0023_two_step_verification_is_asked_for")]
    operations = [migrations.RunPython(grant, take_back)]
