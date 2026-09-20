"""Confirming your password before adding two-factor or a passkey.

NAF, 2026-09-20: "Trying to add 2fa or a passkey doesn't accept my password." The library
reauthenticates by rebuilding credentials from its own username field and the primary row of
its address table; this installation keys accounts on a public identifier and mirrors its own
confirmed addresses into that table without a primary, so it had nothing to look the account
up by and called every correct password wrong.
"""

import time

import pytest
from allauth.account.internal.flows.login import AUTHENTICATION_METHODS_SESSION_KEY
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


def _sign_in_was_a_while_ago(client):
    """Age the session past the window in which the library takes the sign-in as recent enough:
    the state the advisor was in when he went to add a passkey."""
    session = client.session
    session[AUTHENTICATION_METHODS_SESSION_KEY] = [
        {"method": "password", "at": time.time() - 24 * 60 * 60}
    ]
    session.save()


def _signed_in():
    user = _member()
    client = Client()
    assert client.post("/accounts/login/", {"login": "kay@example.org", "password": PASSWORD})
    return user, client


def test_the_right_password_is_accepted():
    _, client = _signed_in()
    r = client.post(
        "/accounts/reauthenticate/",
        {"password": PASSWORD, "next": "/accounts/2fa/totp/activate/"},
    )
    assert r.status_code == 302, "the right password lets the person through"
    assert "/accounts/reauthenticate/" not in r["Location"]


def test_the_wrong_password_is_refused():
    _, client = _signed_in()
    r = client.post("/accounts/reauthenticate/", {"password": "not-the-password"})
    assert r.status_code == 200
    assert "Incorrect password" in r.content.decode()


def test_turning_on_two_factor_asks_once_and_then_proceeds():
    """The route the advisor walked: an hour after signing in, the activation page asks him to
    confirm his password, and afterwards it shows him the code to scan."""
    _, client = _signed_in()
    _sign_in_was_a_while_ago(client)
    r = client.get("/accounts/2fa/totp/activate/")
    assert r.status_code == 302
    assert "/accounts/reauthenticate/" in r["Location"]
    client.post("/accounts/reauthenticate/", {"password": PASSWORD})
    r = client.get("/accounts/2fa/totp/activate/")
    assert r.status_code == 200, "asked once, then the page itself"


def test_adding_a_passkey_asks_the_same_way():
    _, client = _signed_in()
    _sign_in_was_a_while_ago(client)
    r = client.get("/accounts/2fa/webauthn/add/")
    assert r.status_code == 302
    assert "/accounts/reauthenticate/" in r["Location"]
    client.post("/accounts/reauthenticate/", {"password": PASSWORD})
    r = client.get("/accounts/2fa/webauthn/add/")
    assert r.status_code == 200
