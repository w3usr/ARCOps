"""One start and end per event (FR-38 as functional addendum A32; private tracker 275).

Each event's periods become its start and end, from the first start to the last end. Where there
were gaps between them (a split contest), the on-air hours keep the gaps off the air: the club's
own stretches, or the old periods themselves where it had chosen none, clipped to the old periods,
so nothing that was off the air comes on. Then OperatingPeriod goes.

Reversing makes one period per event from its start and end; the gaps survive only as on-air
hours. The deploy's database snapshot is the way back for anything else.
"""

from django.db import migrations, models


def _merge(spans):
    out = []
    for a, b in sorted(spans):
        if a >= b:
            continue
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [tuple(x) for x in out]


def _clip(spans, bounds):
    return _merge(
        (max(a, c), min(b, d)) for a, b in spans for c, d in bounds if max(a, c) < min(b, d)
    )


def one_span(apps, schema_editor):
    Event = apps.get_model("events", "Event")
    OnAirRange = apps.get_model("events", "OnAirRange")
    for event in Event.objects.all():
        periods = _merge((p.start, p.end) for p in event.periods.all())
        if not periods:
            continue
        event.start, event.end = periods[0][0], periods[-1][1]
        event.save(update_fields=["start", "end"])
        own = [(r.start, r.end) for r in OnAirRange.objects.filter(event=event)]
        on_air = _clip(own or periods, periods)
        OnAirRange.objects.filter(event=event).delete()
        if on_air != [(event.start, event.end)]:  # the whole span is stored as nothing
            OnAirRange.objects.bulk_create(
                OnAirRange(event=event, start=a, end=b) for a, b in on_air
            )


def back_to_periods(apps, schema_editor):
    Event = apps.get_model("events", "Event")
    OperatingPeriod = apps.get_model("events", "OperatingPeriod")
    for event in Event.objects.exclude(start=None).exclude(end=None):
        OperatingPeriod.objects.create(event=event, start=event.start, end=event.end)


class Migration(migrations.Migration):
    dependencies = [("events", "0009_reminder_help_text")]

    operations = [
        migrations.AddField(
            model_name="event", name="start", field=models.DateTimeField(blank=True, null=True)
        ),
        migrations.AddField(
            model_name="event", name="end", field=models.DateTimeField(blank=True, null=True)
        ),
        migrations.RunPython(one_span, back_to_periods),
        migrations.DeleteModel(name="OperatingPeriod"),
    ]
