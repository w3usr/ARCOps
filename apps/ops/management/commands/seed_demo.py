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


def account(email: str, **fields):
    """The demo's accounts, found by address or created with it. An account is its key now, so
    there is no address field to get_or_create on."""
    found = User.objects.by_address(email).first()
    if found:
        return found, False
    return User.objects.create_user(email, None, **fields), True


class Command(BaseCommand):
    help = "Seed a development database with fictitious data."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true")

    def handle(self, *args, **opts):
        real = User.objects.exclude(addresses__address__endswith="@example.org").distinct()
        if real.exists() and not opts["force"]:
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
            # the faculty advisor: approves access agreements and reads the archive (FR-125)
            ("dee@example.org", "Dee", "Example", "", "", AccessLevel.ADVISOR, "faculty"),
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
            u, _ = account(
                email,
                first_name=first,
                last_name=last,
                callsign=call,
                access_level=level,
                category=cat,
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
        self._seed_later_phases(users, ev)
        self.stdout.write("demo seeded: sign in as ada@example.org / demo-password-please-change")

    def _seed_later_phases(self, users, ev):
        """The states phases 0 to 7 added, so every page has something to show and the
        accessibility check (tools/a11y) can reach it: a guardian and a minor with a responsible
        adult, a waitlist entry, an entry link, an announcement (so the outbox and My messages
        have rows), contest fields, and the message templates."""
        from apps.accounts.entry import create_link
        from apps.accounts.models import EntryLink, Guardianship
        from apps.comms.announce import send_announcement
        from apps.comms.services import seed_templates
        from apps.events.models import ResponsibleAdult, Waitlist

        seed_templates()
        pat, _ = account(
            "pat@example.org",
            first_name="Pat",
            last_name="Example",
            cell_phone="555-0100",
            category="community",
            access_level=AccessLevel.MEMBER,
        )
        kim, kim_new = account(
            "kim@example.org",
            first_name="Kim",
            last_name="Example",
            category="student",
            access_level=AccessLevel.MEMBER,
            under_18=True,
        )
        for u in (pat, kim):
            u.set_password("demo-password-please-change")
            u.save()
        Guardianship.objects.get_or_create(
            minor=kim, guardian=pat, defaults={"relationship": "parent"}
        )
        op_slots = list(
            ev.locations.first()
            .positions.first()
            .slots.filter(kind="operating", cancelled=False)
            .order_by("start")
        )
        if kim_new and len(op_slots) > 3:
            su = SignUp.objects.create(slot=op_slots[3], user=kim, role="observer")
            ResponsibleAdult.objects.create(
                signup=su, name="Pat Example", phone="555-0100", email="pat@example.org", member=pat
            )
            Waitlist.objects.get_or_create(slot=op_slots[0], user=users["Dee"], role="operator")
        # someone in the archive, so the page has a row to read (FR-125)
        gone, gone_new = account(
            "gus@example.org",
            first_name="Gus",
            last_name="Example",
            callsign="N0OLD",
            category="student",
            access_level=AccessLevel.MEMBER,
        )
        if gone_new:
            gone.set_password("demo-password-please-change")
            gone.save()
            from apps.accounts.services import archive_member

            archive_member(users["Ada"], gone, "graduated in May")

        if not EntryLink.objects.exists():
            create_link(
                users["Ada"],
                label="PHYS 101 demo section",
                kind=EntryLink.Kind.CLASS,
                required_domain="example.edu",
                expires_at=timezone.now() + timedelta(days=90),
                landing_event=ev,
            )
        if not ev.contest_fields:
            ev.contest_fields = {
                "mode": "SSB",
                "bands": "160-10m",
                "exchange": "RS + serial number",
            }
            ev.save(update_fields=["contest_fields"])
        from apps.comms.models import Announcement

        if not Announcement.objects.exists():
            send_announcement(
                users["Ben"],
                ev,
                {},
                "Demo: bring a headset",
                "<p>A fictitious announcement so the outbox and My messages have something to show.</p>",
            )
