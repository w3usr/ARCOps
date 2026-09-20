"""Rewrite the seeded labels that came out as "User object (1)".

A migration's historical model has no custom `__str__`, so the seeding in 0007 wrote Django's
default into a column a person reads. 0007 is corrected for any installation built from scratch;
this repairs the rows it has already written, on the one installation that ran it.
"""

from django.db import migrations

SEEDED = " (from the record as it stood)"


def label_for(user) -> str:
    if user is None:
        return "system"
    name = " ".join(part for part in (user.first_name, user.last_name) if part).strip()
    name = name or user.preferred_name or f"account {user.pk}"
    return f"{name} ({user.callsign})" if user.callsign else name


def rename(apps, schema_editor):
    CredentialDecision = apps.get_model("credentials", "CredentialDecision")
    for row in CredentialDecision.objects.filter(
        actor_label__startswith="User object ("
    ).select_related("actor"):
        row.actor_label = label_for(row.actor) + SEEDED
        row.save(update_fields=["actor_label"])


def nothing(apps, schema_editor):
    """The old labels named nobody; there is nothing worth putting back."""


class Migration(migrations.Migration):
    dependencies = [("credentials", "0007_seed_the_record_from_what_stands")]
    operations = [migrations.RunPython(rename, nothing)]
