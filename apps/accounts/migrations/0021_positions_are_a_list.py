"""A member holds any number of club positions, not one.

The field was a single key, so a person who is both the faculty advisor and the club's license
trustee could be recorded as only one of them, and a club with a board of several members had
nowhere to put them. It becomes a list of keys, and the old value becomes a list of one.
"""

from django.db import migrations, models


def to_list(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    for pk, held in User.objects.exclude(club_position="").values_list("pk", "club_position"):
        User.objects.filter(pk=pk).update(club_positions=[held])


def to_one(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    for pk, held in User.objects.exclude(club_positions=[]).values_list("pk", "club_positions"):
        User.objects.filter(pk=pk).update(club_position=held[0] if held else "")


class Migration(migrations.Migration):
    dependencies = [("accounts", "0020_calendar_key")]

    operations = [
        migrations.AddField(
            model_name="user",
            name="club_positions",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.RunPython(to_list, to_one),
        migrations.RemoveField(model_name="user", name="club_position"),
    ]
