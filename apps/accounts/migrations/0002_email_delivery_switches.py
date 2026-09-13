# Two delivery switches of equal standing replace the "primary only / both addresses"
# preference (FR-70; NAF, 2026-09-13: "Neither should be considered primary"). Members who had
# chosen "both" keep both addresses on; members on "primary only" received mail at their sign-in
# address alone, which is what both switches off still gives them (services.recipient_addresses
# falls back to the sign-in address).

from django.db import migrations, models


def carry_preference_forward(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(email_preference="both").update(
        institution_email_delivery=True, personal_email_delivery=True
    )
    User.objects.exclude(email_preference="both").update(
        institution_email_delivery=False, personal_email_delivery=False
    )


def carry_preference_back(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(institution_email_delivery=True, personal_email_delivery=True).update(
        email_preference="both"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="institution_email_delivery",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="user",
            name="personal_email_delivery",
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(carry_preference_forward, carry_preference_back),
        migrations.RemoveField(
            model_name="user",
            name="email_preference",
        ),
    ]
