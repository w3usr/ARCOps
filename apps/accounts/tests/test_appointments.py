"""Who may appoint whom.

NAF, 2026-09-19: "Faculty advisors should be able to appoint officers, members, and below.
Officers should be able to appoint members, and below."

Written against capabilities rather than a ladder, so a club that invents a group gets the same
rule: a group is yours to grant when everything it grants is something you already hold and it
does not hold everything you do, and an account is yours to change when it is below you.
"""

import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import Client

from apps.accounts.models import User
from apps.ops.groups import assignable_groups, may_set_access

pytestmark = pytest.mark.django_db
PASSWORD = "a-Long-Password-77!"


@pytest.fixture(autouse=True)
def club():
    call_command("club_import")


def _user(address, groups=(), **extra):  # noqa: D103
    extra.setdefault("first_name", address.split("@")[0].title())
    extra.setdefault("last_name", "Tester")
    return User.objects.create_user(address, PASSWORD, groups=list(groups), **extra)


def _as(user):
    c = Client()
    c.force_login(user)
    return c


@pytest.fixture
def club_people():
    return {
        "advisor": _user("adv@example.org", ["advisor"]),
        "officer": _user("off@example.org", ["officer"]),
        "member": _user("mem@example.org", ["member"]),
        "closed": _user("gone@example.org", []),
    }


def _names(groups):
    return sorted(g.name for g in groups)


def test_each_level_appoints_the_levels_below_it(club_people):
    assert _names(assignable_groups(club_people["advisor"])) == ["member", "officer", "provisional"]
    assert _names(assignable_groups(club_people["officer"])) == ["member", "provisional"]
    # a member holds no say in it at all, whatever the arithmetic of subsets says
    assert not may_set_access(club_people["member"], club_people["closed"])


def test_nobody_appoints_a_peer_or_anybody_above_them(club_people):
    advisor, officer = club_people["advisor"], club_people["officer"]
    other_advisor = _user("adv2@example.org", ["advisor"])
    assert "advisor" not in _names(assignable_groups(advisor)), "not even another advisor"
    assert not may_set_access(advisor, other_advisor), "a peer is not below you"
    assert not may_set_access(officer, advisor), "and nobody edits the account above them"
    assert may_set_access(advisor, officer) and may_set_access(officer, club_people["member"])


def test_an_officer_restores_an_account_that_was_closed(club_people):
    """The case the rule was asked for: a member closed their own account and wants back in."""
    from apps.accounts.services import request_closure

    member = club_people["member"]
    request_closure(member)
    member.refresh_from_db()
    assert not member.has_access and member.closure_requested_at

    c = _as(club_people["officer"])
    body = c.get(f"/members/{member.pk}/").content.decode()
    assert "Closed at their own request on" in body, "which of the two am I undoing?"
    r = c.post(f"/members/{member.pk}/edit/", {"action": "reopen"}, follow=True)
    assert r.status_code == 200
    member.refresh_from_db()
    assert member.has_access and member.in_group("member")
    assert member.closure_requested_at is None, "no longer a member who asked to leave"


def test_a_suspended_account_says_who_suspended_it_and_why(club_people):
    officer, member = club_people["officer"], club_people["member"]
    _as(officer).post(
        f"/members/{member.pk}/edit/", {"action": "close", "reason": "pending a decision"}
    )
    member.refresh_from_db()
    assert not member.has_access
    body = _as(officer).get(f"/members/{member.pk}/").content.decode()
    assert "Suspended by" in body and "pending a decision" in body
    assert ">Suspended<" in _as(club_people["advisor"]).get("/members/").content.decode()


def test_an_officer_is_offered_only_the_groups_they_may_grant(club_people):
    officer, member = club_people["officer"], club_people["member"]
    body = _as(officer).get(f"/members/{member.pk}/edit/").content.decode()
    assert 'name="groups"' in body
    assert "Club Officer" not in body, "an officer does not make another officer"
    assert 'name="is_superuser"' not in body


def test_a_forged_appointment_is_refused(club_people):
    """The page offers what it should; the server is what makes it true."""
    officer, member = club_people["officer"], club_people["member"]
    r = _as(officer).post(
        f"/members/{member.pk}/edit/",
        {
            "action": "save",
            "first_name": member.first_name,
            "last_name": member.last_name,
            "groups": [Group.objects.get(name="officer").pk],
        },
    )
    member.refresh_from_db()
    assert r.status_code == 200, "the form comes back with the error rather than saving"
    assert not member.in_group("officer") and member.in_group("member")


def test_an_officer_cannot_touch_the_advisors_account(club_people):
    officer, advisor = club_people["officer"], club_people["advisor"]
    body = _as(officer).get(f"/members/{advisor.pk}/edit/").content.decode()
    assert 'name="groups"' not in body and "Danger zone" not in body
    _as(officer).post(f"/members/{advisor.pk}/edit/", {"action": "close", "reason": "taking over"})
    advisor.refresh_from_db()
    assert advisor.has_access, "no coup by demotion"


def test_a_sysadmin_is_made_by_a_sysadmin(club_people):
    advisor = club_people["advisor"]
    sysadmin = _user("sys@example.org", [])
    sysadmin.is_superuser = True
    sysadmin.save(update_fields=["is_superuser"])
    assert not may_set_access(advisor, sysadmin)
    body = _as(advisor).get(f"/members/{sysadmin.pk}/edit/").content.decode()
    assert 'name="groups"' not in body and 'name="is_superuser"' not in body

    c = _as(sysadmin)
    session = c.session  # acting at the raised level
    session["acting_view"] = "sysadmin"
    session.save()
    body = c.get(f"/members/{advisor.pk}/edit/").content.decode()
    assert 'name="is_superuser"' in body, "a sysadmin is made by a sysadmin"
    assert "Advisor" in body, "and a sysadmin may appoint an advisor"


def test_the_four_statuses_and_the_archive_flag_beside_them(club_people):
    """NAF, 2026-09-19: Provisional, Active, Closed and Suspended are where somebody stands with
    the club; archiving is a flag beside that, and the record keeps the status it went in with.
    """
    from apps.accounts.services import archive_member, readmit, request_closure, suspend

    advisor, officer, member = (club_people[k] for k in ("advisor", "officer", "member"))
    assert member.status == "active" and member.status_label == "Active"
    provisional = _user("prov@example.org", ["provisional"])
    assert provisional.status == "provisional"

    request_closure(member)
    member.refresh_from_db()
    assert member.status == "closed" and not member.has_access

    archive_member(advisor, member, "graduated")
    member.refresh_from_db()
    assert member.status == "closed" and member.is_archived
    assert member.status_label == "Closed", "the archive is a flag beside the status"

    other = _user("two@example.org", ["member"])
    suspend(officer, other, "pending a decision")
    other.refresh_from_db()
    assert other.status == "suspended" and other.suspended_by == officer
    assert other.suspended_reason == "pending a decision"

    readmit(advisor, other)
    other.refresh_from_db()
    assert other.status == "active" and other.suspended_at is None


def test_an_officer_suspends_but_only_an_advisor_lifts_it(club_people):
    """ "Officer can suspend but only advisor can lift" — NAF, 2026-09-19."""
    officer, member = club_people["officer"], club_people["member"]
    _as(officer).post(f"/members/{member.pk}/edit/", {"action": "close", "reason": "pending"})
    member.refresh_from_db()
    assert member.status == "suspended"

    body = _as(officer).get(f"/members/{member.pk}/edit/").content.decode()
    assert "A suspension is lifted by a faculty advisor" in body
    _as(officer).post(f"/members/{member.pk}/edit/", {"action": "reopen"})
    member.refresh_from_db()
    assert member.status == "suspended", "an officer cannot lift what an officer imposed"

    _as(club_people["advisor"]).post(f"/members/{member.pk}/edit/", {"action": "reopen"})
    member.refresh_from_db()
    assert member.status == "active" and member.in_group("member")


def test_an_officer_lets_a_closed_account_back_in(club_people):
    from apps.accounts.services import request_closure

    officer, member = club_people["officer"], club_people["member"]
    request_closure(member)
    _as(officer).post(f"/members/{member.pk}/edit/", {"action": "reopen"})
    member.refresh_from_db()
    assert member.status == "active"


def test_the_status_column_is_an_officers_and_sorts_down_the_list(club_people):
    from apps.accounts.services import request_closure, suspend

    advisor, officer, member = (club_people[k] for k in ("advisor", "officer", "member"))
    request_closure(member)
    suspended = _user("sus@example.org", ["member"], last_name="Suspended")
    suspend(officer, suspended, "pending")

    body = _as(officer).get("/members/").content.decode()
    assert ">Status<" in body and ">Closed<" in body and ">Suspended<" in body
    assert 'name="status"' in body, "and it narrows by it"

    # a member sees neither the column nor the filter
    plain = _user("plain@example.org", ["member"])
    body = _as(plain).get("/members/").content.decode()
    assert ">Status<" not in body and 'name="status"' not in body

    names = _as(advisor).get("/members/?sort=status&dir=asc").content.decode()
    order = [n for n in ("Active", "Closed", "Suspended") if n in names]
    assert order == ["Active", "Closed", "Suspended"]


def test_access_is_one_choice_from_a_list(club_people):
    """NAF, 2026-09-19: "Access should be a drop-down. You should only be able to pick one." """
    advisor, member = club_people["advisor"], club_people["member"]
    body = _as(advisor).get(f"/members/{member.pk}/edit/").content.decode()
    assert '<select name="groups"' in body and 'type="checkbox" name="groups"' not in body
    assert ">No access</option>" in body, "and no access is one of the answers"

    _as(advisor).post(
        f"/members/{member.pk}/edit/",
        {
            "action": "save",
            "first_name": member.first_name,
            "last_name": member.last_name,
            "groups": Group.objects.get(name="officer").pk,
        },
    )
    member.refresh_from_db()
    assert [g.name for g in member.groups.all()] == ["officer"], "one level, not two"


def test_the_card_over_somebody_elses_fields_is_called_manage(club_people):
    advisor, member = club_people["advisor"], club_people["member"]
    assert ">Manage</h2>" in _as(advisor).get(f"/members/{member.pk}/edit/").content.decode()
    assert ">Details</h2>" in _as(advisor).get("/me/edit/", follow=True).content.decode()
