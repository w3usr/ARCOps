"""Correcting somebody else's addresses is a sysadmin's.

An officer cannot stop an address signing a member in, or turn off their club mail; a member adjusts
their own mail settings. An officer can still add an address and confirm one, which is what a member
who has lost a mailbox needs; taking one away, or its confirmation, or its club mail, is nobody
else's business. An officer who needs to shut an account out suspends it (FR-91).
"""

from django.db import migrations

CAPABILITY = "correct_member_addresses"


def write_it(apps, schema_editor):
    from apps.ops.capabilities import ensure_permissions

    ensure_permissions(
        apps.get_model("auth", "Permission"), apps.get_model("contenttypes", "ContentType")
    )


class Migration(migrations.Migration):
    dependencies = [("accounts", "0017_position_is_the_advisors")]
    operations = [migrations.RunPython(write_it, migrations.RunPython.noop)]
