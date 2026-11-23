"""A guardian signed up for the same slot as their ward is the ward's responsible adult (addendum
A40; private tracker 358). The row is marked `automatic` and goes when the guardian leaves. Pairs
already on a slot that has not ended are named here, as a new sign-up would name them."""

from django.db import migrations, models
from django.utils import timezone


def name_pairs_already_signed_up(apps, schema_editor):
    Guardianship = apps.get_model("accounts", "Guardianship")
    SignUp = apps.get_model("events", "SignUp")
    ResponsibleAdult = apps.get_model("events", "ResponsibleAdult")
    for g in Guardianship.objects.filter(
        active=True, guardian__under_18=False, minor__under_18=True
    ).select_related("guardian"):
        for ward in SignUp.objects.filter(
            user_id=g.minor_id,
            slot__end__gt=timezone.now(),
            slot__cancelled=False,
            slot__signups__user_id=g.guardian_id,
        ):
            u = g.guardian
            if not ResponsibleAdult.objects.filter(signup=ward, member_id=g.guardian_id).exists():
                ResponsibleAdult.objects.create(
                    signup=ward,
                    name=" ".join(  # User.full_name, which a migration's model lacks
                        p for p in (u.first_name, u.middle_name, u.last_name) if p
                    ),
                    member_id=g.guardian_id,
                    automatic=True,
                )


class Migration(migrations.Migration):
    dependencies = [
        ("events", "0012_a_named_member_is_a_link_not_a_copy"),
        ("accounts", "0027_user_ordering_ignores_case"),
    ]

    operations = [
        migrations.AddField(
            model_name="responsibleadult",
            name="automatic",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(name_pairs_already_signed_up, migrations.RunPython.noop),
    ]
