"""A member named as a minor's responsible adult kept a copy of their email and phone on the row,
which the guardian's page and the slot's other members read (FR-67). The row keeps
the link; the copy goes, and the member's own account still holds both."""

from django.db import migrations


def drop_the_copies(apps, schema_editor):
    ResponsibleAdult = apps.get_model("events", "ResponsibleAdult")
    ResponsibleAdult.objects.exclude(member=None).update(email="", phone="")


class Migration(migrations.Migration):
    dependencies = [("events", "0011_when_it_meets_in_fields")]

    operations = [migrations.RunPython(drop_the_copies, migrations.RunPython.noop)]
