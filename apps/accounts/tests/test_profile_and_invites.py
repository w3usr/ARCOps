"""Email delivery switches (FR-70), the guardian rule on invitations, and where a password
change lands (FR-7)."""

import pytest
from django.contrib.auth.models import Group
from django.test import Client

from apps.accounts.models import Invitation, User
from apps.comms.services import recipient_addresses

pytestmark = pytest.mark.django_db


def _officer():
    u = User.objects.create_user("o@example.org", "pw-Testing-123", first_name="Ann", last_name="O")
    u.groups.set(Group.objects.filter(name="officer"))
    u.save()
    return u


def test_club_mail_follows_the_delivery_switches_and_never_reaches_nobody():
    from apps.accounts import addresses

    u = _officer()
    addresses.add(u, "ann@uni.example", confirmed=True)
    addresses.add(u, "ann@home.example", delivery=False)
    u.addresses.filter(address="o@example.org").update(delivery=False)
    assert recipient_addresses(u) == ["ann@uni.example"]

    u.addresses.update(delivery=False)  # every switch off: everything receives, rather than nothing
    assert recipient_addresses(u) == ["ann@home.example", "ann@uni.example", "o@example.org"]

    u.addresses.update(delivery=True)
    assert recipient_addresses(u) == ["ann@home.example", "ann@uni.example", "o@example.org"]


def test_profile_shows_every_address_once_with_its_standing_and_a_way_to_add_one():
    from apps.accounts import addresses

    u = _officer()
    addresses.add(u, "ann@home.example")
    c = Client()
    c.force_login(u)
    body = c.get("/me/").content.decode()
    assert "Where we write, and how you sign in" in body
    assert body.count('value="address_delivery"') == 2  # one switch per address
    assert "Not confirmed: send the link" in body  # the badge is the button
    assert 'name="action" value="address_add"' in body
    # each address is written out once; the rest of its row is controls, not a second copy
    assert body.count('<span class="address">o@example.org</span>') == 1
    assert body.count('<span class="address">ann@home.example</span>') == 1


def test_a_minor_needs_a_guardian_and_an_adult_never_stores_one():
    c = Client()
    c.force_login(_officer())
    r = c.post(
        "/me/invitations/",
        {"email": "kid@example.org", "category": "student", "is_minor": "on", "guardian_email": ""},
    )
    assert r.status_code == 200 and "required for a minor" in r.content.decode()
    assert not Invitation.objects.filter(email="kid@example.org").exists()
    c.post(
        "/me/invitations/",
        {"email": "adult@example.org", "category": "student", "guardian_email": "x@example.org"},
    )
    assert Invitation.objects.get(email="adult@example.org").guardian_email == ""
    # The field is present in the HTML (works without JavaScript) but marked for disclosure.
    assert 'data-reveal-when="#id_is_minor"' in c.get("/me/invitations/").content.decode()


def test_forced_password_change_lands_on_home_and_a_voluntary_one_on_the_profile():
    u = _officer()
    u.password_is_temporary = True
    u.save()
    c = Client()
    c.force_login(u)
    assert c.get("/events/")["Location"] == "/accounts/password/change/"
    r = c.post(
        "/accounts/password/change/",
        {
            "oldpassword": "pw-Testing-123",
            "password1": "a-New-Long-Password-9",
            "password2": "a-New-Long-Password-9",
        },
    )
    assert r.status_code == 302 and r["Location"] == "/"
    assert "Welcome, Ann" in c.get("/").content.decode()
    r = c.post(
        "/accounts/password/change/",
        {
            "oldpassword": "a-New-Long-Password-9",
            "password1": "a-New-Long-Password-10",
            "password2": "a-New-Long-Password-10",
        },
    )
    assert r["Location"] == "/me/"
