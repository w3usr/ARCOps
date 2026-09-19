"""Correcting somebody else's addresses is a sysadmin's.

The advisor, 2026-09-19: "They should not be able to stop an email address from signing them in,
or turn off a users club email... Users can adjust email settings in their own accounts." An
officer can still add an address and confirm one, which is what a member who has lost a mailbox
needs; taking one away, or its confirmation, or its club mail, is nobody else's business. An
officer who needs to shut an account out suspends it (FR-91).
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
