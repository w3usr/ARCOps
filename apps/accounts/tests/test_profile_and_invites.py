"""Email delivery switches (FR-70), the guardian rule on invitations, and where a password
change lands (FR-7)."""

import pytest
from django.test import Client

from apps.accounts.models import AccessLevel, Invitation, User
from apps.comms.services import recipient_addresses

pytestmark = pytest.mark.django_db


def _officer():
    u = User.objects.create_user("o@example.org", "pw-Testing-123", first_name="Ann", last_name="O")
    u.access_level = AccessLevel.OFFICER
    u.save()
    return u


def test_recipients_are_the_switched_on_addresses_else_the_sign_in_address():
    u = _officer()
    u.institution_email = "ann@uni.example"
    u.personal_email = "ann@home.example"
    u.institution_email_delivery = True
    u.personal_email_delivery = False
    u.save()
    assert recipient_addresses(u) == ["ann@uni.example"]
    u.institution_email_delivery = False
    u.save()
    assert recipient_addresses(u) == ["o@example.org"]
    u.institution_email_delivery = u.personal_email_delivery = True
    u.save()
    assert recipient_addresses(u) == ["ann@home.example", "ann@uni.example"]


def test_profile_shows_two_addresses_of_equal_standing_with_a_switch_each():
    c = Client()
    c.force_login(_officer())
    body = c.get("/me/").content.decode()
    assert "Email addresses" in body
    assert body.count("Send club email here") == 2
    assert "Primary" not in body


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
        {"oldpassword": "pw-Testing-123", "password1": "a-New-Long-Password-9", "password2": "a-New-Long-Password-9"},
    )
    assert r.status_code == 302 and r["Location"] == "/"
    assert "Welcome, Ann" in c.get("/").content.decode()
    r = c.post(
        "/accounts/password/change/",
        {"oldpassword": "a-New-Long-Password-9", "password1": "a-New-Long-Password-10", "password2": "a-New-Long-Password-10"},
    )
    assert r["Location"] == "/me/"
