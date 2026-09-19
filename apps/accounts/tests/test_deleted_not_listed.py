"""A deleted account keeps its row, and keeps out of the lists of people.

NAF, 2026-09-19, having deleted a test account: "now I see a remnant Deleted member." The row
survives on purpose, so a past roster still adds up, but the directory is who the club has now.
"""

from datetime import UTC, datetime, timedelta

import pytest
from django.core.management import call_command
from django.test import Client

from apps.accounts.models import User
from apps.accounts.services import archive_member, delete_account
from apps.events.models import Event, Location, OperatingPeriod, Position, SignUp
from apps.events.services.slots import generate_slots

pytestmark = pytest.mark.django_db
PASSWORD = "a-Long-Password-77!"


@pytest.fixture(autouse=True)
def club():
    call_command("club_import")


def _sysadmin():
    return User.objects.create_user(
        "sys@example.org", PASSWORD, first_name="Sys", last_name="Admin", is_superuser=True
    )


def _as(user, view="sysadmin"):
    c = Client()
    c.force_login(user)
    if user.is_superuser:
        s = c.session
        s["acting_view"] = view
        s.save()
    return c


def test_a_deleted_account_leaves_the_directory():
    sysadmin = _sysadmin()
    gone = User.objects.create_user(
        "gone@example.org", PASSWORD, groups=["member"], first_name="Kay", last_name="Craigie"
    )
    c = _as(sysadmin)
    assert "Craigie" in c.get("/members/").content.decode()

    delete_account(sysadmin, gone, "testing")

    body = c.get("/members/").content.decode()
    assert "Deleted member" not in body, "the directory is who the club has now"
    assert "Craigie" not in body  # a surname, not a first name: "Ann" hides inside "Announcements"
    gone.refresh_from_db()
    assert gone.deleted_at is not None, "the row stays; only the listing changes"


def test_an_archived_account_is_out_of_the_directory_too():
    """The rule that was already right, kept honest beside the new one."""
    sysadmin = _sysadmin()
    left = User.objects.create_user(
        "left@example.org", PASSWORD, groups=["member"], first_name="Ann", last_name="Former"
    )
    archive_member(sysadmin, left, "graduated")
    assert "Former" not in _as(sysadmin).get("/members/").content.decode()


def test_a_deleted_member_still_holds_their_place_on_a_past_roster():
    """Why the row is kept at all: the counts must not change under the club's feet."""
    sysadmin = _sysadmin()
    gone = User.objects.create_user(
        "gone2@example.org", PASSWORD, groups=["member"], first_name="Kay", last_name="Craigie"
    )
    event = Event.objects.create(
        title="Past contest", state=Event.State.COMPLETED, created_by=sysadmin
    )
    start = datetime(2026, 1, 3, 0, 0, tzinfo=UTC)
    OperatingPeriod.objects.create(event=event, start=start, end=start + timedelta(hours=2))
    loc = Location.objects.create(event=event, name="Club station")
    pos = Position.objects.create(location=loc, name="Run", order=1)
    slot = generate_slots(event, [pos], minutes=60)[0]
    SignUp.objects.create(slot=slot, user=gone, role="operator")

    delete_account(sysadmin, gone, "testing")

    assert SignUp.objects.filter(slot=slot).count() == 1, "the past sign-up survives"
    gone.refresh_from_db()
    assert gone.full_name == "Deleted member"


def test_a_deleted_account_cannot_be_named_as_a_responsible_adult():
    sysadmin = _sysadmin()
    gone = User.objects.create_user(
        "adult@example.org", PASSWORD, groups=["member"], first_name="Kay", last_name="Craigie"
    )
    delete_account(sysadmin, gone, "testing")
    assert gone not in User.objects.with_access().filter(under_18=False)
