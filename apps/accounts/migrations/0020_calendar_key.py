"""A stable address for the calendar feed (FR-59).

It was a signed string, and Django's signatures carry a timestamp, so the address shown on My
Schedule was different on every page load. A key on the account is what a calendar feed wants:
the same address every time, and one credential to replace if it ever leaks.

Three steps, because the column is unique and the rows already exist: add it empty, fill it with
a fresh key each, then make it unique.
"""

from django.db import migrations, models

from apps.accounts.models import new_calendar_key


def fill(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    for user in User.objects.filter(calendar_key=""):
        user.calendar_key = new_calendar_key()
        user.save(update_fields=["calendar_key"])


class Migration(migrations.Migration):
    dependencies = [("accounts", "0019_closed_by")]

    operations = [
        migrations.AddField(
            model_name="user",
            name="calendar_key",
            field=models.CharField(default="", max_length=64),
        ),
        migrations.RunPython(fill, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="user",
            name="calendar_key",
            field=models.CharField(default=new_calendar_key, max_length=64, unique=True),
        ),
    ]
