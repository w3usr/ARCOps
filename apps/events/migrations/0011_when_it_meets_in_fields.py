"""When a regular meeting or net meets, in fields (FR-45; private tracker 273).

The free text "When it recurs, in words" becomes the note. Each event's text is read for a pattern
and a time ("Tuesdays 20:00 ET", "First Monday 7pm", "15th of the month 19:00"); what is read fills
the fields, and the text stays as the note unless every word of it was read. Nothing is guessed.
"""

from django.db import migrations, models


def read_the_text(apps, schema_editor):
    from apps.events.services.meets import parse

    Event = apps.get_model("events", "Event")
    for event in Event.objects.exclude(meeting_note=""):
        fields, note = parse(event.meeting_note)
        if fields:
            for k, v in fields.items():
                setattr(event, k, v)
            event.meeting_note = note
            event.save(update_fields=[*fields, "meeting_note"])


class Migration(migrations.Migration):
    dependencies = [("events", "0010_one_start_and_end_per_event")]

    operations = [
        migrations.RenameField("event", "recurrence_text", "meeting_note"),
        migrations.AlterField(
            "event", "meeting_note", models.CharField(blank=True, max_length=200)
        ),
        migrations.AddField("event", "repeats", models.CharField(blank=True, max_length=16)),
        migrations.AddField(
            "event", "repeat_weekday", models.PositiveSmallIntegerField(blank=True, null=True)
        ),
        migrations.AddField("event", "repeat_week", models.SmallIntegerField(blank=True, null=True)),
        migrations.AddField(
            "event", "repeat_day", models.PositiveSmallIntegerField(blank=True, null=True)
        ),
        migrations.AddField("event", "meets_at", models.TimeField(blank=True, null=True)),
        migrations.AddField("event", "meets_until", models.TimeField(blank=True, null=True)),
        migrations.RunPython(read_the_text, migrations.RunPython.noop),
    ]
