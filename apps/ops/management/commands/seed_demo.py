"""
seed_demo: fill a development database with fictitious members and events (TR-34).

Everything created here is invented: the people do not exist, the callsigns are from the
N0CALL family, and the events are next month. Refuses to run against a database that already
has real-looking data unless --force is given.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.accounts.models import AccessLevel, User
from apps.credentials.models import CredentialType, LicenseRecord, SignedAgreement
from apps.events.models import (
    Captaincy,
    Event,
    Location,
    OperatingPeriod,
    Position,
    RoleCapacity,
    SignUp,
)
from apps.events.services.slots import generate_slots


class Command(BaseCommand):
    help = "Seed a development database with fictitious data."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true")

    def handle(self, *args, **opts):
        if (
            User.objects.filter(email__endswith="@example.org").count() == 0
            and User.objects.count() > 1
            and not opts["force"]
        ):
            raise CommandError("database has non-demo users; pass --force to seed anyway")

        people = [
            (
                "ada@example.org",
                "Ada",
                "Example",
                "N0CAL",
                "Extra",
                AccessLevel.SYSADMIN,
                "faculty",
            ),
            (
                "ben@example.org",
                "Ben",
                "Example",
                "N0CAM",
                "General",
                AccessLevel.OFFICER,
                "student",
            ),
            (
                "cy@example.org",
                "Cy",
                "Example",
                "N0CAN",
                "Technician",
                AccessLevel.MEMBER,
                "student",
            ),
            ("dee@example.org", "Dee", "Example", "", "", AccessLevel.MEMBER, "faculty"),
            (
                "eli@example.org",
                "Eli",
                "Example",
                "N0CAP",
                "General",
                AccessLevel.MEMBER,
                "community",
            ),
        ]
        users = {}
        for email, first, last, call, cls, level, cat in people:
            u, _ = User.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "callsign": call,
                    "access_level": level,
                    "category": cat,
                },
            )
            u.set_password("demo-password-please-change")
            u.save()
            users[first] = u
            if call:
                LicenseRecord.objects.update_or_create(
                    user=u,
                    defaults={
                        "callsign": call,
                        "licensee_name": f"{first.upper()} {last.upper()}",
                        "operator_class": cls,
                        "status": "active",
                        "expiry_date": timezone.now().date() + timedelta(days=900),
                        "source": "demo",
                        "retrieved_at": timezone.now(),
                    },
                )
        station = CredentialType.objects.filter(key="station_access").first()
        it = CredentialType.objects.filter(key="it_access").first()
        for first in ("Ada", "Ben", "Dee", "Eli"):
            for ct in (station, it):
                if ct:
                    SignedAgreement.objects.get_or_create(
                        user=users[first],
                        template=None,
                        credential=ct,
                        defaults={
                            "signer_name": users[first].full_name,
                            "state": "approved",
                            "expires_on": timezone.now().date() + timedelta(days=200),
                            "approver": users["Ada"],
                            "approved_at": timezone.now(),
                        },
                    )

        start = (timezone.now() + timedelta(days=21)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        ev, created = Event.objects.get_or_create(
            title="Demo Worldwide DX Contest, SSB",
            defaults={
                "type": "contest",
                "state": "published",
                "description_html": "<p>A fictitious weekend contest used to demonstrate the schedule.</p>",
                "min_license_class": "General",
                "kbyg_html": "<h2>Getting in</h2><p>Demo text.</p>",
                "created_by": users["Ada"],
            },
        )
        if created:
            OperatingPeriod.objects.create(event=ev, start=start, end=start + timedelta(hours=48))
            loc = Location.objects.create(event=ev, name="Club station", is_club_station=True)
            pos = Position.objects.create(location=loc, name="Run", order=1)
            Captaincy.objects.create(event=ev, user=users["Ben"])
            slots = generate_slots(ev, [pos], minutes=60, setup_slots=1, breakdown_slots=1)
            for s in slots:
                for role, cap in (("operator", 2), ("mentor", 1), ("observer", 2)):
                    RoleCapacity.objects.create(slot=s, role=role, capacity=cap)
            op_slots = [s for s in slots if s.kind == "operating"]
            SignUp.objects.create(slot=op_slots[0], user=users["Ben"], role="operator")
            SignUp.objects.create(
                slot=op_slots[0], user=users["Cy"], role="operator", note="Running 10 minutes late"
            )
            SignUp.objects.create(
                slot=op_slots[1], user=users["Cy"], role="operator"
            )  # not viable: Tech only, no access
            SignUp.objects.create(slot=op_slots[2], user=users["Eli"], role="operator")
            SignUp.objects.create(
                slot=op_slots[2], user=users["Ben"], role="mentor"
            )  # two full holders: viable
            SignUp.objects.create(slot=op_slots[2], user=users["Dee"], role="observer")
        self.stdout.write("demo seeded: sign in as ada@example.org / demo-password-please-change")
