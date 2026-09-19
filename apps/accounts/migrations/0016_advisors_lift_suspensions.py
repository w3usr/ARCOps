"""Only a faculty advisor lets a suspended account back in.

The advisor, 2026-09-19: an officer may suspend, because something can happen at the station on
a Tuesday night, and lifting it needs somebody answerable for the station. The capability is new,
so it is written into the groups that should hold it here; the configuration import leaves an
existing group alone by design.
"""

from django.db import migrations

CAPABILITY = "lift_suspension"
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
    dependencies = [("accounts", "0015_suspension")]
    operations = [migrations.RunPython(grant, take_back)]
