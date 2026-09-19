"""A profile is read, and edited on a page of its own.

NAF, 2026-09-19: "When you click on someone's name, it should take the person to a read-only
view of their profile page. If they have the permission to edit a profile (such as a member
looking at their own page, an officer, or a sysadmin), there should be a button to 'Edit
Profile'. This will allow for potential public views of profiles, as well as make it more
difficult to accidentally change information."
"""

import pytest
from django.core.management import call_command
from django.test import Client

from apps.accounts.models import User

pytestmark = pytest.mark.django_db
PASSWORD = "a-Long-Password-77!"


@pytest.fixture(autouse=True)
def club():
    call_command("club_import")


def _user(address, groups, **extra):
    extra.setdefault("first_name", "Pat")
    extra.setdefault("last_name", "Person")
    return User.objects.create_user(address, PASSWORD, groups=groups, **extra)


def _as(user):
    c = Client()
    c.force_login(user)
    return c


@pytest.fixture
def pair():
    officer = _user("off@example.org", ["officer"], first_name="Ann", last_name="Officer")
    member = _user(
        "mem@example.org", ["member"], first_name="Mo", last_name="Member", callsign="N0MEM"
    )
    return officer, member


def test_a_members_page_holds_nothing_that_changes_anything(pair):
    officer, member = pair
    body = _as(officer).get(f"/members/{member.pk}/").content.decode()
    assert "N0MEM" in body and "Mo Member" in body
    page = body.split("<main", 1)[1]  # the sidebar keeps its sign-out form
    assert "<form" not in page, "a page opened to read cannot change what it shows"
    assert "csrfmiddlewaretoken" not in page


def test_the_edit_button_is_there_for_whoever_may_edit(pair):
    officer, member = pair
    body = _as(officer).get(f"/members/{member.pk}/").content.decode()
    assert f'href="/members/{member.pk}/edit/"' in body and "Edit profile" in body
    assert (
        'name="club_position"' in _as(officer).get(f"/members/{member.pk}/edit/").content.decode()
    )


def test_your_own_page_is_a_member_page(pair):
    """NAF, 2026-09-19: "These should be the same thing. i.e. /me/ should redirect to
    /members/1/ [...] That way there is a more unified codebase and interface." """
    _, member = pair
    c = _as(member)
    r = c.get("/me/")
    assert r.status_code == 302 and r["Location"] == f"/members/{member.pk}/"
    assert c.get("/me/edit/")["Location"] == f"/members/{member.pk}/edit/"


def test_your_own_profile_reads_and_the_edit_page_holds_the_form(pair):
    _, member = pair
    c = _as(member)
    body = c.get("/me/", follow=True).content.decode()
    assert "Edit profile and preferences" in body
    assert f'href="/members/{member.pk}/edit/"' in body
    # nothing on it changes anything, preferences included (NAF, 2026-09-19)
    assert "<form" not in body.split("<main", 1)[1]
    assert "N0MEM" in body, "the account is shown, whether or not it is being edited"
    assert 'name="callsign"' not in body
    assert "Notifications" in body and 'name="email" value="reminder"' not in body
    edit = c.get("/me/edit/", follow=True).content.decode()
    assert 'name="callsign"' in edit and 'name="preferred_name"' in edit
    assert 'name="email" value="reminder"' in edit  # your preferences, on the same edit page
    assert "Close my account" in edit


def test_editing_your_profile_lands_back_on_it(pair):
    _, member = pair
    c = _as(member)
    r = c.post(
        f"/members/{member.pk}/edit/",
        {"action": "save", "first_name": "Mo", "last_name": "Member", "preferred_name": "Moe"},
    )
    assert r.status_code == 302 and r["Location"] == f"/members/{member.pk}/"
    assert User.objects.get(pk=member.pk).preferred_name == "Moe"


def test_your_name_in_the_corner_opens_your_profile(pair):
    _, member = pair
    body = _as(member).get("/events/").content.decode()
    foot = body.split('class="sidenav-foot"')[1]
    assert 'href="/me/"' in foot and "N0MEM" in foot


def test_a_member_under_18_has_no_edit_page(pair):
    officer, _ = pair
    minor = _user("kid@example.org", ["member"], first_name="Kim", last_name="Young", under_18=True)
    c = _as(minor)
    assert c.get("/me/", follow=True).status_code == 200
    assert c.get("/me/edit/", follow=True).status_code == 404
    body = c.get("/me/", follow=True).content.decode()
    assert "Edit profile" not in body
    assert "Your guardian makes changes to this account" in body


def test_a_member_cannot_reach_anybody_elses_page(pair):
    officer, member = pair
    c = _as(member)
    assert c.get(f"/members/{officer.pk}/").status_code == 404
    assert c.get(f"/members/{officer.pk}/edit/").status_code == 404
    assert c.get(f"/members/{member.pk}/").status_code == 200, "their own is always theirs"
