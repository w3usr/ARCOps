"""
Identity becomes a key of its own, and the addresses become rows.

The account used to *be* its email address: that field was the primary identifier, so it had to
be unique and always present. Two fabrications came out of that. A minor with no mailbox was
given a made-up address derived from a guardian's, flagged as sign-in-only. A deleted account
had its address overwritten with `deleted-<id>@invalid.example` to keep the constraint happy.

Now `public_id` is what the account is, and `Address` rows are what the person holds: any kind,
each confirmed or not, each with its own delivery switch. Both fabrications go.

Moving the data:

* the old sign-in address becomes a confirmed row, because it demonstrably signed that person in
  before this migration and must keep doing so afterwards;
* the institution and personal addresses become rows of their kind, carrying their own delivery
  switch, confirmed where the sign-in library already held them confirmed;
* a minor's fabricated sign-in-only address becomes no row at all, which is the point;
* the delivery rule is preserved exactly: where both switches were off, mail went to the sign-in
  address, so that row is the one that carries delivery.
"""

from uuid import uuid4

import django.db.models.deletion
from django.db import migrations, models


def give_each_account_a_key(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    for user in User.objects.all().only("pk"):
        User.objects.filter(pk=user.pk).update(public_id=uuid4())


def addresses_into_rows(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Address = apps.get_model("accounts", "Address")
    EmailAddress = apps.get_model("account", "EmailAddress")
    already_confirmed = {
        (row.user_id, (row.email or "").lower())
        for row in EmailAddress.objects.filter(verified=True)
    }
    for user in User.objects.all():
        sign_in = (user.email or "").lower()
        institution = (user.institution_email or "").lower()
        personal = (user.personal_email or "").lower()
        rows: dict[str, dict] = {}

        if institution:
            rows[institution] = {
                "kind": "institution",
                "delivery": user.institution_email_delivery,
                "confirmed": (user.pk, institution) in already_confirmed,
            }
        if personal:
            rows.setdefault(personal, {})
            rows[personal].update(
                {
                    "kind": rows[personal].get("kind", "personal"),
                    "delivery": rows[personal].get("delivery", False)
                    or user.personal_email_delivery,
                    "confirmed": rows[personal].get("confirmed", False)
                    or (user.pk, personal) in already_confirmed,
                }
            )
        # The address they signed in with keeps working: it is confirmed by having been used.
        # A minor's fabricated address is dropped instead, which is what it was standing in for.
        if sign_in and not user.sign_in_only_address:
            row = rows.setdefault(sign_in, {"kind": "personal", "confirmed": False})
            row["confirmed"] = True
            # The old rule: with neither switch on, club mail went to the sign-in address alone.
            # It must still go there alone, whether or not that address also filled one of the
            # two slots. Found on the live data, where both switches were off and every row came
            # out with delivery off, which would have started sending to an address that had
            # been receiving nothing.
            nothing_switched_on = not (institution and user.institution_email_delivery) and not (
                personal and user.personal_email_delivery
            )
            if nothing_switched_on:
                for other in rows.values():
                    other["delivery"] = False
                row["delivery"] = True
            else:
                row.setdefault("delivery", False)

        for address, values in rows.items():
            Address.objects.create(
                user_id=user.pk,
                address=address,
                kind=values.get("kind", "personal"),
                confirmed=values.get("confirmed", False),
                delivery=values.get("delivery", True),
            )

        # The sign-in library reads its own table, and `apps.accounts.addresses.mirror` is what
        # keeps it in step. Nothing calls that during a migration, so the mirror is rebuilt here:
        # exactly the confirmed addresses, marked verified. Without this the two tables disagree
        # from the first request after the migration, and an address this migration did not
        # confirm would still be sitting in the library's table signing someone in.
        confirmed_here = {a for a, v in rows.items() if v.get("confirmed")}
        EmailAddress.objects.filter(user_id=user.pk).exclude(email__in=confirmed_here).delete()
        for address in confirmed_here:
            existing = EmailAddress.objects.filter(user_id=user.pk, email=address).first()
            if existing is None:
                EmailAddress.objects.create(
                    user_id=user.pk, email=address, verified=True, primary=False
                )
            elif not existing.verified:
                existing.verified = True
                existing.save(update_fields=["verified"])


def rows_back_into_fields(apps, schema_editor):
    """Enough to step back safely during a rehearsal."""
    User = apps.get_model("accounts", "User")
    Address = apps.get_model("accounts", "Address")
    for user in User.objects.all():
        rows = list(Address.objects.filter(user_id=user.pk))
        institution = next((r for r in rows if r.kind == "institution"), None)
        personal = next((r for r in rows if r.kind == "personal"), None)
        confirmed = next((r for r in rows if r.confirmed), None)
        user.institution_email = institution.address if institution else ""
        user.institution_email_delivery = institution.delivery if institution else True
        user.personal_email = personal.address if personal else ""
        user.personal_email_delivery = personal.delivery if personal else True
        user.email = (
            (confirmed or institution or personal).address
            if rows
            else f"no-address-{user.pk}@invalid.example"
        )
        user.save(
            update_fields=[
                "email",
                "institution_email",
                "institution_email_delivery",
                "personal_email",
                "personal_email_delivery",
            ]
        )


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0001_initial"),
        ("accounts", "0008_minor_sign_in_only_address"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="public_id",
            field=models.UUIDField(default=uuid4, editable=False, null=True),
        ),
        migrations.RunPython(give_each_account_a_key, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="user",
            name="public_id",
            field=models.UUIDField(default=uuid4, editable=False, unique=True),
        ),
        migrations.CreateModel(
            name="Address",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("address", models.EmailField(max_length=254)),
                (
                    "kind",
                    models.CharField(
                        choices=[("institution", "Institution"), ("personal", "Personal")],
                        default="personal",
                        max_length=12,
                    ),
                ),
                ("confirmed", models.BooleanField(default=False)),
                ("delivery", models.BooleanField(default=True)),
                ("created", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="addresses",
                        to="accounts.user",
                    ),
                ),
            ],
            options={"ordering": ["kind", "address"]},
        ),
        migrations.AddConstraint(
            model_name="address",
            constraint=models.UniqueConstraint(
                fields=("user", "address"), name="one_row_per_address"
            ),
        ),
        migrations.AddConstraint(
            model_name="address",
            constraint=models.UniqueConstraint(
                condition=models.Q(confirmed=True),
                fields=("address",),
                name="a_confirmed_address_belongs_to_one_account",
            ),
        ),
        # Stepping back re-adds these columns before the rows are written into them, so they are
        # made nullable here: reversing puts the column back as it is at this point (nullable),
        # `rows_back_into_fields` fills it, and reversing these three restores the definitions.
        migrations.AlterField(
            model_name="user", name="email", field=models.EmailField(max_length=254, null=True)
        ),
        migrations.AlterField(
            model_name="user",
            name="institution_email",
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
        migrations.AlterField(
            model_name="user",
            name="personal_email",
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
        migrations.RunPython(addresses_into_rows, rows_back_into_fields),
        migrations.RemoveField(model_name="user", name="email"),
        migrations.RemoveField(model_name="user", name="institution_email"),
        migrations.RemoveField(model_name="user", name="institution_email_delivery"),
        migrations.RemoveField(model_name="user", name="personal_email"),
        migrations.RemoveField(model_name="user", name="personal_email_delivery"),
        migrations.RemoveField(model_name="user", name="sign_in_only_address"),
        migrations.RemoveField(model_name="user", name="email_verified_at"),
    ]
