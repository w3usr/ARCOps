"""Who may open what: one table, every page, every kind of account.

This is the safety net under the permission work. It records what each kind of account can
reach today, so a change to how permission is decided has to keep the same answers or say why.
The failure mode being guarded against is silent: somebody sees a page they should not, and
nothing crashes to announce it.

`OK` means the page renders, `GONE` means the application refuses by pretending the page is not
there, and `AWAY` means it sends the visitor somewhere else (usually to sign in).
"""

import datetime as dt

import pytest
from django.core.management import call_command
from django.test import Client
from django.utils import timezone

from apps.accounts.models import User
from apps.credentials.models import AgreementTemplate, CredentialType
from apps.events.models import Event, Location, OperatingPeriod, Position
from apps.events.services.slots import generate_slots

pytestmark = pytest.mark.django_db

OK, GONE, AWAY, POST_ONLY, NO_CREDENTIAL = 200, 404, 302, 405, 403
# "sysadmin" is a sysadmin acting at the level they sign in at (the club's configured everyday
# view); "raised" is the same account after stepping up, which asks for the password.
ROLES = ("anonymous", "provisional", "member", "officer", "advisor", "sysadmin", "raised")


@pytest.fixture(autouse=True)
def club():
    call_command("club_import")


def _user(email, level, **kw):
    kw.setdefault("first_name", email.split("@")[0].title())
    kw.setdefault("last_name", "Tester")
    kw.setdefault("category", "student")
    return User.objects.create_user(
        email,
        "pw-Testing-123",
        groups=[] if level == "sysadmin" else [level],
        is_superuser=level == "sysadmin",
        **kw,
    )


@pytest.fixture
def world():
    people = {
        "provisional": _user("prov@example.org", "provisional"),
        "member": _user("mem@example.org", "member"),
        "officer": _user("off@example.org", "officer"),
        "advisor": _user("adv@example.org", "advisor", category="faculty"),
        "sysadmin": _user("sys@example.org", "sysadmin", category="faculty"),
    }
    people["sysadmin"].is_superuser = True
    people["sysadmin"].save()
    ev = Event.objects.create(title="Matrix Contest", state="published")
    start = timezone.now() + dt.timedelta(days=5)
    OperatingPeriod.objects.create(event=ev, start=start, end=start + dt.timedelta(hours=2))
    pos = Position.objects.create(
        location=Location.objects.create(event=ev, name="Station"), name="Run"
    )
    slot = generate_slots(ev, [pos], minutes=60)[0]
    credential, _ = CredentialType.objects.get_or_create(
        key="station_access", defaults={"label": "Station access", "established_by": "agreement"}
    )
    template = AgreementTemplate.objects.create(
        key="sa",
        credential=credential,
        title="Station access",
        version=1,
        html="<p>Agree</p>",
        audience=["student", "faculty"],
        content_hash="h1",
        effective_date="2026-01-01",
    )
    return {"people": people, "event": ev, "slot": slot, "template": template}


def _client(role, world):
    c = Client()
    if role == "anonymous":
        return c
    c.force_login(world["people"]["sysadmin" if role == "raised" else role])
    if role == "raised":
        session = c.session
        session["acting_view"] = "sysadmin"
        session.save()
    return c


def _pages(world):
    """Every page worth gating, with what each kind of account should get."""
    ev, slot = world["event"].pk, world["slot"].pk
    mem = world["people"]["member"].pk
    officer_pk = world["people"]["officer"].pk
    tpl = world["template"].pk
    everyone_in = dict.fromkeys(ROLES[1:], OK)
    officer_up = {
        "provisional": GONE,
        "member": GONE,
        "officer": OK,
        "advisor": OK,
        "sysadmin": OK,
        "raised": OK,
    }
    advisor_up = {
        "provisional": GONE,
        "member": GONE,
        "officer": GONE,
        "advisor": OK,
        "sysadmin": OK,
        "raised": OK,
    }
    # A sysadmin signs in acting at the everyday level, so these are refused until they step up.
    sysadmin_only = {
        "provisional": GONE,
        "member": GONE,
        "officer": GONE,
        "advisor": GONE,
        "sysadmin": GONE,
        "raised": OK,
    }
    return [
        # the pages anyone signed in may see
        ("dashboard", "/", {"anonymous": AWAY, **everyone_in}),
        ("event list", "/events/", {"anonymous": AWAY, **everyone_in}),
        ("my schedule", "/events/mine/", {"anonymous": AWAY, **everyone_in}),
        ("event detail", f"/events/{ev}/", {"anonymous": AWAY, **everyone_in}),
        ("slot detail", f"/events/{ev}/slot/{slot}/", {"anonymous": AWAY, **everyone_in}),
        # /me/ forwards everyone signed in to their own member page, which is the profile
        ("profile", "/me/", dict.fromkeys(("anonymous", *ROLES[1:]), AWAY)),
        ("messages", "/me/messages/", {"anonymous": AWAY, **everyone_in}),
        ("privacy", "/privacy/", dict.fromkeys(("anonymous", *ROLES[1:]), OK)),
        # a provisional member sees no directory and no agreements (FR-121)
        (
            "member directory",
            "/members/",
            {
                "anonymous": AWAY,
                "provisional": GONE,
                "member": OK,
                "officer": OK,
                "advisor": OK,
                "sysadmin": OK,
                "raised": OK,
            },
        ),
        (
            "agreements",
            "/credentials/agreements/",
            {
                "anonymous": AWAY,
                "provisional": GONE,
                "member": OK,
                "officer": OK,
                "advisor": OK,
                "sysadmin": OK,
                "raised": OK,
            },
        ),
        # signing is a POST, so a GET is refused the same way for everyone who is signed in
        (
            "sign an agreement",
            f"/credentials/agreements/{tpl}/sign/",
            {"anonymous": AWAY, **dict.fromkeys(ROLES[1:], POST_ONLY)},
        ),
        # the computer password is gated by holding a current agreement, never by role: nobody
        # who has signed nothing may see it, whatever else they are allowed to do
        (
            "computer password",
            "/credentials/computer-password/",
            {"anonymous": AWAY, **dict.fromkeys(ROLES[1:], NO_CREDENTIAL)},
        ),
        # officer tools
        # Somebody else's page is an officer's to read. Your own is always yours, whoever you
        # are, because /me/ is now that page (NAF, 2026-09-19).
        ("member page", f"/members/{officer_pk}/", {"anonymous": AWAY, **officer_up}),
        ("own page", f"/members/{mem}/", {"anonymous": AWAY, **officer_up, "member": OK}),
        ("invitations", "/me/invitations/", {"anonymous": AWAY, **officer_up}),
        ("entry links", "/me/entry-links/", {"anonymous": AWAY, **officer_up}),
        ("announcements", "/announcements/", {"anonymous": AWAY, **officer_up}),
        ("announce to all", "/announce/", {"anonymous": AWAY, **officer_up}),
        ("outbox", "/ops/outbox/", {"anonymous": AWAY, **officer_up}),
        ("new event", "/events/new/", {"anonymous": AWAY, **officer_up}),
        ("manage event", f"/events/{ev}/manage/", {"anonymous": AWAY, **officer_up}),
        ("event health", "/events/health/", {"anonymous": AWAY, **officer_up}),
        ("participation", f"/events/{ev}/participation/", {"anonymous": AWAY, **officer_up}),
        ("member roster", "/members/roster/", {"anonymous": AWAY, **officer_up}),
        ("hours by course", "/members/hours/", {"anonymous": AWAY, **officer_up}),
        ("access rosters", "/credentials/access-rosters/", {"anonymous": AWAY, **officer_up}),
        # advisor tools
        ("approvals", "/credentials/approvals/", {"anonymous": AWAY, **advisor_up}),
        ("archive", "/members/archive/", {"anonymous": AWAY, **advisor_up}),
        # sysadmin tools
        ("job status", "/ops/status/", {"anonymous": AWAY, **sysadmin_only}),
        ("club settings", "/ops/settings/", {"anonymous": AWAY, **sysadmin_only}),
        ("message templates", "/ops/templates/", {"anonymous": AWAY, **sysadmin_only}),
        (
            "rotate the computer password",
            "/credentials/computer-password/manage/",
            {"anonymous": AWAY, **sysadmin_only},
        ),
    ]


@pytest.mark.parametrize("role", ROLES)
def test_every_page_answers_each_kind_of_account_the_same_way(role, world):
    wrong = []
    for label, url, expected in _pages(world):
        got = _client(role, world).get(url).status_code
        want = expected[role]
        if got != want:
            wrong.append(f"{label} ({url}): {role} got {got}, expected {want}")
    assert not wrong, "\n".join(wrong)


def test_an_account_with_no_access_and_an_archived_one_reach_nothing(world):
    """Two ways of being outside the club, and neither is a role."""
    closed = _user("closed@example.org", "none")
    archived = _user("gone@example.org", "member")
    from apps.accounts.services import archive_member

    archive_member(world["people"]["advisor"], archived, "graduated")
    for person in (closed, archived):
        c = Client()
        c.force_login(person)
        for url in ("/", "/events/", "/me/", "/members/"):
            assert c.get(url).status_code == AWAY, f"{person.email} reached {url}"
