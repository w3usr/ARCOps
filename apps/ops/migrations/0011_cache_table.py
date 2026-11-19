"""The database cache's table (private tracker 354), made here so a deploy, a laptop and CI all
get it from `migrate`. `createcachetable` is idempotent and does nothing for a cache that is not
in the database, as under the test settings."""

from django.core.management import call_command
from django.db import migrations


def create(apps, schema_editor):
    call_command("createcachetable", database=schema_editor.connection.alias, verbosity=0)


class Migration(migrations.Migration):
    dependencies = [("ops", "0010_auditlog_append_only")]

    operations = [migrations.RunPython(create, migrations.RunPython.noop)]
