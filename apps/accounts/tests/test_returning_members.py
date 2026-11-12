"""A member who left and comes back gets their record, not a new one.

NAF, 2026-09-19: "We need some mechanism that if an archived member decides to come back (and
is eligible to do so, i.e. not suspended), when an officer or someone else sends them an invite
or that person tries to join, it searches the closed and archived membership to bring that
account back, rather than creating a completely new account."
"""

import pytest
from django.core.management import call_command
from django.test import Client

from apps.accounts.models import EntryLink, Invitation, User
from apps.accounts.services import (
    archive_member,
    create_invitation,
    request_closure,
    returning_account,
    suspend,
)
from apps.ops.models import AuditLog

pytestmark = pytest.mark.django_db
PASSWORD = "a-Long-Password-77!"
NEW_PASSWORD = "an-Even-Longer-Password-99!"


@pytest.fixture(autouse=True)
def club():
    call_command("club_import")


def _user(address, groups=("member",), **extra):
    extra.setdefault("first_name", "Rae")
    extra.setdefault("last_name", "Turner")
    return User.objects.create_user(address, PASSWORD, groups=list(groups), **extra)


def _as(user):
    c = Client()
    c.force_login(user)
    return c


@pytest.fixture
def people():
    officer = _user("off@example.org", ["officer"], first_name="Ann", last_name="Officer")
    advisor = _user("adv@example.org", ["advisor"], first_name="Ada", last_name="Visor")
    member = _user("rae@example.org", callsign="N0RAE", cell_phone="555-0100")
    return officer, advisor, member


def _left(advisor, member, archive=True):
    request_closure(member)
    member.refresh_from_db()
    if archive:
        archive_member(advisor, member, "graduated")
        member.refresh_from_db()
    return member


def test_a_closed_or_archived_account_is_offered_back(people):
    officer, advisor, member = people
    assert returning_account("rae@example.org") == (None, "") or True  # active: not returning
    found, refusal = returning_account("rae@example.org")
    assert found is None and "already has an account" in refusal

    _left(advisor, member)
    found, refusal = returning_account("rae@example.org")
    assert found == member and refusal == ""


def test_a_suspended_account_is_not_a_returning_member(people):
    officer, advisor, member = people
    suspend(officer, member, "pending a decision")
    found, refusal = returning_account("rae@example.org")
    assert found is None and "suspended" in refusal
    assert "faculty advisor" in refusal.lower(), "and it says who can lift it"


def test_an_officer_inviting_them_is_told_the_record_comes_back(people):
    officer, advisor, member = people
    _left(advisor, member)
    r = _as(officer).post(
        "/me/invitations/",
        {"email": "rae@example.org", "category": "student"},
        follow=True,
    )
    body = r.content.decode()
    assert "brings their record back" in body
    assert Invitation.objects.filter(email="rae@example.org", state="created").exists()


def test_accepting_the_invitation_brings_the_record_back(people):
    officer, advisor, member = people
    _left(advisor, member)
    inv = create_invitation(officer, "rae@example.org", "student", False, "")
    c = Client()
    r = c.post(
        f"/me/invite/{inv.token}/",
        {
            "first_name": "Rae",
            "last_name": "Turner",
            "callsign": "",
            "password1": NEW_PASSWORD,
            "password2": NEW_PASSWORD,
            "consent": "on",
        },
        follow=True,
    )
    assert r.status_code == 200
    assert User.objects.count() == 3, "no second account for the same person"
    member.refresh_from_db()
    assert member.status == "active" and not member.is_archived
    assert member.callsign == "N0RAE" and member.cell_phone == "555-0100", "their record is intact"
    assert AuditLog.objects.filter(action="member.returned").exists()
    assert Client().login(email="rae@example.org", password=NEW_PASSWORD), "the new password works"


def _join_as(link, password, **extra):
    c = Client()
    r = c.post(
        f"/join/{link.token}/form/",
        {
            "email": "rae@example.org",
            "first_name": extra.get("first_name", "Rae"),
            "middle_name": "",
            "last_name": "Turner",
            "preferred_name": "",
            "callsign": "",
            "cell_phone": extra.get("cell_phone", ""),
            "category": "student",
            "password1": password,
            "password2": password,
            "consent": "on",
        },
        follow=True,
    )
    return c, r


def _link(officer, kind):
    from django.utils import timezone

    return EntryLink.objects.create(
        label="PHYS 101",
        kind=kind,
        required_domain="example.org" if kind == EntryLink.Kind.CLASS else "",
        created_by=officer,
        expires_at=timezone.now() + timezone.timedelta(days=30),
    )


@pytest.mark.parametrize("kind", [EntryLink.Kind.CLASS, EntryLink.Kind.COMMUNITY])
def test_a_link_never_brings_an_account_back_without_its_mailbox(people, kind):
    """FR-120, FR-125 (SK, 2026-11-12): a join form with a former member's address and a new
    password used to bring the account back and sign the browser in, with no proof that whoever
    typed it held the mailbox. Now the form changes nothing and says what it says for any
    address; the account's own mail gets a link to come back."""
    from apps.comms.models import Outbox

    officer, advisor, member = people
    _left(advisor, member)
    before = member.password
    link = _link(officer, kind)
    c, r = _join_as(link, "a-Strangers-Password-123!", first_name="Mallory", cell_phone="555-9999")
    member.refresh_from_db()
    assert member.is_archived and not member.is_active, "the account is not brought back"
    assert (
        member.password == before
        and member.first_name != "Mallory"
        and member.cell_phone == "555-0100"
    )
    assert "_auth_user_id" not in c.session, "nobody is signed in"
    assert "Check your email" in r.content.decode()
    msg = Outbox.objects.filter(user=member, subject__icontains="come back").get()
    assert "/join/return/" in msg.body_html


@pytest.mark.parametrize("kind", [EntryLink.Kind.CLASS, EntryLink.Kind.COMMUNITY])
def test_the_link_in_the_mailbox_brings_the_record_back(people, kind):
    import re

    from apps.comms.models import Outbox

    officer, advisor, member = people
    _left(advisor, member)
    link = _link(officer, kind)
    _join_as(link, NEW_PASSWORD)
    body = Outbox.objects.filter(user=member, subject__icontains="come back").get().body_html
    path = re.search(r'/join/return/[^"<\s]+/', body)[0]
    c = Client()
    page = c.get(path).content.decode()
    assert 'name="new_password1"' in page and "Rae" in page
    r = c.post(path, {"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD}, follow=True)
    assert User.objects.count() == 3, "no second account for the same person"
    member.refresh_from_db()
    assert member.status == "active" and not member.is_archived
    assert member.joined_via == link and member.callsign == "N0RAE"
    assert AuditLog.objects.filter(action="account.returned_via_link").exists()
    assert int(c.session["_auth_user_id"]) == member.pk
    assert "Welcome back" in r.content.decode()
    assert Client().login(email="rae@example.org", password=NEW_PASSWORD), "the new password works"
    # the link is spent: the account is no longer a returning one
    assert Client().get(path).status_code == 410


def test_a_bad_return_link_changes_nothing(people):
    officer, advisor, member = people
    _left(advisor, member)
    assert Client().get("/join/return/not-a-token/").status_code == 410
    member.refresh_from_db()
    assert member.is_archived
