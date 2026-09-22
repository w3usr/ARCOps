"""One signature awaiting approval per member per agreement.

Signing was a single unguarded POST, so a double-click made a second row: the same act
recorded twice. The approver saw two cards and got two messages; the member saw one, their
page keeping only the latest signature per agreement.

The constraint cannot go on while such a pair is in the table, so the duplicates are collapsed
first. The earliest of each pair is kept — it is the one the member's click actually made, and
the later rows are the echo. Nothing is lost by dropping them: the audit log holds an
`agreement.signed` row for every submission, so the record of what arrived, and when, stands
whatever this leaves in the table.

Only rows still awaiting approval are touched. A duplicate that somebody has already decided
is a decision in the record, and is left exactly where it is.
"""

from django.db import migrations, models


def collapse_duplicate_pending_signatures(apps, schema_editor):
    SignedAgreement = apps.get_model("credentials", "SignedAgreement")
    seen: dict[tuple[int, int], int] = {}
    redundant: list[int] = []
    for pk, user_id, template_id in (
        SignedAgreement.objects.filter(state="signed", template__isnull=False)
        .order_by("signed_at", "pk")
        .values_list("pk", "user_id", "template_id")
    ):
        key = (user_id, template_id)
        if key in seen:
            redundant.append(pk)
        else:
            seen[key] = pk
    if redundant:
        SignedAgreement.objects.filter(pk__in=redundant).delete()


def noop(apps, schema_editor):
    """Nothing to undo: the rows were duplicates, and putting them back would restore the bug."""


class Migration(migrations.Migration):
    dependencies = [("credentials", "0012_the_reversal_has_a_plainer_name")]

    operations = [
        migrations.RunPython(collapse_duplicate_pending_signatures, noop),
        migrations.AddConstraint(
            model_name="signedagreement",
            constraint=models.UniqueConstraint(
                condition=models.Q(("state", "signed")),
                fields=("user", "template"),
                name="one_pending_signature_per_agreement",
            ),
        ),
    ]
