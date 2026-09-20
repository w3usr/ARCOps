"""Seed the decision record from the state each agreement is in today.

`SignedAgreement` keeps only the latest decision, so this is all there is to recover: one row
per agreement that is no longer merely *signed*, from its own `state`, `approver`, `approved_at`
and `decision_reason`. The steps before it are gone, and the label says so rather than letting
the page imply the record reaches back further than it does.

From here the record is written as decisions happen, so it is complete from the day this runs.
"""

from django.db import migrations

# state on the agreement -> what that state records having been decided
FROM_STATE = {
    "approved": "approved",
    "declined": "declined",
    "revoked": "revoked",
    "expired": "expired",
}


def seed(apps, schema_editor):
    SignedAgreement = apps.get_model("credentials", "SignedAgreement")
    CredentialDecision = apps.get_model("credentials", "CredentialDecision")
    if CredentialDecision.objects.exists():
        return  # never seed twice over a record that is already being kept

    rows = []
    for a in SignedAgreement.objects.exclude(state="signed").select_related("approver"):
        action = FROM_STATE.get(a.state)
        if not action:
            continue
        who = str(a.approver) if a.approver else "system"
        rows.append(
            CredentialDecision(
                agreement=a,
                action=action,
                actor=a.approver,
                actor_label=f"{who} (from the record as it stood)",
                note=a.decision_reason or "",
                expires_on=a.expires_on,
            )
        )
    CredentialDecision.objects.bulk_create(rows)
    # `at` is auto_now_add, so every seeded row carries the moment of the migration rather than
    # a time nobody recorded. Move it to when the decision was actually made, where that is
    # known; the rest keep the migration's own timestamp, which is the honest answer.
    for row, a in zip(rows, [r.agreement for r in rows], strict=True):
        if a.approved_at and row.pk:
            CredentialDecision.objects.filter(pk=row.pk).update(at=a.approved_at)


def unseed(apps, schema_editor):
    CredentialDecision = apps.get_model("credentials", "CredentialDecision")
    CredentialDecision.objects.filter(actor_label__endswith="(from the record as it stood)").delete()


class Migration(migrations.Migration):
    dependencies = [("credentials", "0006_the_record_of_what_was_decided")]
    operations = [migrations.RunPython(seed, unseed)]
