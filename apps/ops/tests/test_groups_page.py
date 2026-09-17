"""The page where a club decides what its groups may do.

The advisor, 2026-09-17: "define configurable access groups (member, officer, faculty advisor,
etc)... This would allow sysadmins to define new access levels on their own."
"""

import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import Client

from apps.accounts.models import User
from apps.ops.models import AuditLog

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def club():
    call_command("club_import")


def _user(email, groups=(), **kw):
    kw.setdefault("first_name", email.split("@")[0].title())
    kw.setdefault("last_name", "Tester")
    return User.objects.create_user(email, "pw-Testing-123", groups=list(groups), **kw)


def _as(user, view="sysadmin"):
    c = Client()
    c.force_login(user)
    if user.is_superuser:
        session = c.session  # the level a sysadmin's session acts at
        session["acting_view"] = view
        session.save()
    return c


def test_only_an_account_that_may_manage_groups_opens_the_page():
    sysadmin = _user("sys@example.org", is_superuser=True)
    officer = _user("off@example.org", ["officer"])
    assert _as(sysadmin).get("/ops/groups/").status_code == 200
    assert _as(officer).get("/ops/groups/").status_code == 404


def test_a_sysadmin_changes_what_a_group_may_do():
    sysadmin = _user("sys@example.org", is_superuser=True)
    officer = _user("off@example.org", ["officer"])
    assert not officer.may("view_archive")

    group = Group.objects.get(name="officer")
    held = [p.codename for p in group.permissions.all()]
    c = _as(sysadmin)
    c.post(
        "/ops/groups/",
        {
            "action": "save",
            "groups_in_form": [group.pk],
            f"caps_{group.pk}": [*held, "view_archive"],
        },
    )

    officer = User.objects.get(pk=officer.pk)  # permissions are cached on the instance
    assert officer.may("view_archive")
    assert _as(officer).get("/members/archive/").status_code == 200
    assert AuditLog.objects.filter(action="group.capabilities_changed").exists()


def test_a_club_invents_a_group_of_its_own():
    sysadmin = _user("sys@example.org", is_superuser=True)
    c = _as(sysadmin)
    c.post("/ops/groups/", {"action": "new", "name": "Station Manager"})
    made = Group.objects.get(name="station_manager")

    c.post(
        "/ops/groups/",
        {
            "action": "save",
            "groups_in_form": [made.pk],
            f"caps_{made.pk}": ["manage_events", "view_reports"],
        },
    )
    keeper = _user("keep@example.org", ["station_manager"])
    assert keeper.may("manage_events") and not keeper.may("approve_agreements")
    assert AuditLog.objects.filter(action="group.created").exists()


def test_a_group_with_members_is_not_deleted_and_an_empty_one_is():
    sysadmin = _user("sys@example.org", is_superuser=True)
    _user("off@example.org", ["officer"])
    c = _as(sysadmin)
    officers = Group.objects.get(name="officer")
    r = c.post("/ops/groups/", {"action": "delete", "group": officers.pk}, follow=True)
    assert b"still has members" in r.content and Group.objects.filter(pk=officers.pk).exists()

    spare = Group.objects.create(name="spare")
    c.post("/ops/groups/", {"action": "delete", "group": spare.pk})
    assert not Group.objects.filter(name="spare").exists()


def test_nobody_can_save_away_the_last_account_that_decides_who_may_do_what():
    """The one edit that cannot be undone from inside the application."""
    sysadmin = _user("sys@example.org", is_superuser=True)
    advisor_group = Group.objects.get(name="advisor")
    c = _as(sysadmin)
    # stripping every group changes nothing about a sysadmin, who is not in one
    c.post(
        "/ops/groups/",
        {"action": "save", "groups_in_form": [advisor_group.pk]},
    )
    sysadmin = User.objects.get(pk=sysadmin.pk)
    assert sysadmin.may("assign_groups") and sysadmin.may("manage_groups")
    assert not Group.objects.get(name="advisor").permissions.exists()
