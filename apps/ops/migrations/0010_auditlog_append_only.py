"""TR-21: the audit log is append-only in the database itself, not only in the admin.

The model has said so since it was written, but no migration ever made the triggers, so an
UPDATE or DELETE went through (T22, 2026-10-21). One change stays allowed: clearing `actor_id`,
which is what deleting an account in the Django admin does to its rows (on_delete=SET_NULL);
`actor_label` keeps who it was.
"""

from django.db import migrations

STOP = "SELECT RAISE(ABORT, 'The audit log is append-only (TR-21).');"

CREATE = [
    f"CREATE TRIGGER ops_auditlog_no_delete BEFORE DELETE ON ops_auditlog BEGIN {STOP} END;",
    "CREATE TRIGGER ops_auditlog_no_update BEFORE UPDATE OF "
    '"id", "at", "actor_label", "action", "subject_type", "subject_id", "before", "after" '
    f"ON ops_auditlog BEGIN {STOP} END;",
    "CREATE TRIGGER ops_auditlog_actor_only_cleared BEFORE UPDATE OF actor_id ON ops_auditlog "
    f"WHEN NEW.actor_id IS NOT NULL BEGIN {STOP} END;",
]
DROP = [
    f"DROP TRIGGER IF EXISTS {name};"
    for name in (
        "ops_auditlog_no_delete",
        "ops_auditlog_no_update",
        "ops_auditlog_actor_only_cleared",
    )
]


def create(apps, schema_editor):
    if schema_editor.connection.vendor == "sqlite":  # TR-2: the application runs on SQLite
        for sql in CREATE:
            schema_editor.execute(sql)


def drop(apps, schema_editor):
    if schema_editor.connection.vendor == "sqlite":
        for sql in DROP:
            schema_editor.execute(sql)


class Migration(migrations.Migration):
    dependencies = [("ops", "0009_permission_levels")]

    operations = [migrations.RunPython(create, drop)]
