"""Take "(from the record as it stood)" out of the middle of somebody's name.

The seeded rows carried it inside `actor_label`, which is the column that answers "who decided
this". It is a fact about how the row was recorded rather than about who decided, so it moves to
a flag of its own and is said quietly beside the date instead (NAF, 2026-09-20: "We don't need
'(from the record as it stood)' in the 'By' column").
"""

from django.db import migrations

SUFFIX = " (from the record as it stood)"


def split_it_out(apps, schema_editor):
    CredentialDecision = apps.get_model("credentials", "CredentialDecision")
    for row in CredentialDecision.objects.filter(actor_label__endswith=SUFFIX):
        row.actor_label = row.actor_label[: -len(SUFFIX)]
        row.seeded = True
        row.save(update_fields=["actor_label", "seeded"])


def put_it_back(apps, schema_editor):
    CredentialDecision = apps.get_model("credentials", "CredentialDecision")
    for row in CredentialDecision.objects.filter(seeded=True):
        row.actor_label = f"{row.actor_label}{SUFFIX}"
        row.save(update_fields=["actor_label"])


class Migration(migrations.Migration):
    dependencies = [("credentials", "0009_a_decision_says_how_it_was_recorded")]
    operations = [migrations.RunPython(split_it_out, put_it_back)]
