"""Signing in says nothing; the page already does.

NAF, 2026-09-19, on "Done: Successfully signed in as Kay Craigie (N3KN).": "We don't need a
notification saying you successfully signed in."
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


def _member():
    return User.objects.create_user(
        "kay@example.org",
        PASSWORD,
        groups=["member"],
        first_name="Kay",
        last_name="Craigie",
        callsign="N3KN",
    )


def test_signing_in_adds_no_message():
    _member()
    r = Client().post(
        "/accounts/login/", {"login": "kay@example.org", "password": PASSWORD}, follow=True
    )
    body = r.content.decode()
    assert r.status_code == 200
    assert "Hello, Kay N3KN" in body, "the page says who you are, callsign and all (FR-67)"
    assert "Successfully signed in" not in body
    assert 'class="messages"' not in body, "no message bar at all on a plain sign-in"


def test_signing_out_still_says_so():
    """The sign-in page is also where an expired session lands you; the two differ."""
    c = Client()
    c.force_login(_member())
    body = c.post("/accounts/logout/", follow=True).content.decode()
    assert "signed out" in body.lower()
