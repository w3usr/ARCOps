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


def test_the_librarys_own_pages_use_the_sites_controls():
    """NAF, 2026-09-20, of the recovery codes page: "Should Download Codes Generate New Codes be
    on 2 separate lines?" They were two bare links with a space between them, which reads as one
    phrase. Every control the library draws is now one of the site's buttons."""
    _, client = _signed_in()
    client.post("/accounts/reauthenticate/", {"password": PASSWORD})
    body = client.get("/accounts/2fa/recovery-codes/generate/").content.decode()
    assert 'class="button libctl' in body, "the library's controls carry the site's button"
    assert "Generate" in body


def test_confirm_access_offers_the_passkey_on_the_page_that_asks(monkeypatch):
    """NAF, 2026-09-20: "Why can't I just click Use passkey on the first page, and then it
    automatically uses the passkey without going through a separate screen?"

    It can. The page carries the library's own passkey form and challenge, so the button raises
    the browser prompt where the question was asked; the credential still posts to the library's
    endpoint, which verifies it.
    """
    from allauth.mfa.models import Authenticator
    from allauth.mfa.webauthn.internal import auth as webauthn_auth

    monkeypatch.setattr(webauthn_auth, "begin_authentication", lambda user: {"challenge": "x"})
    user, client = _signed_in()
    Authenticator.objects.create(
        user=user, type=Authenticator.Type.WEBAUTHN, data={"name": "Key", "credential": {}}
    )
    page = client.get("/accounts/reauthenticate/?next=/me/level/").content.decode()

    assert 'id="mfa_webauthn_reauthenticate"' in page, "the button is here"
    assert 'action="/accounts/2fa/webauthn/reauthenticate/"' in page, "and posts to the library"
    assert 'id="js_data"' in page and "id_credential" in page
    assert page.count("mfa/js/webauthn.js") == 1, "one include, or two prompts on one press"
    assert page.count('value="/me/level/"') == 2, "next rides in both forms, or it is lost"
    assert (
        "Alternative options" not in page or "webauthn" not in page.split("Alternative options")[1]
    )
    assert 'name="password"' in page, "and the password is still on the page"


def test_confirm_access_without_a_passkey_is_the_page_it_always_was():
    _, client = _signed_in()
    page = client.get("/accounts/reauthenticate/").content.decode()
    assert 'name="password"' in page and "mfa_webauthn_reauthenticate" not in page
    assert "webauthn.js" not in page, "nothing is loaded for a method this account does not have"


def test_the_club_s_own_word_reaches_the_librarys_pages():
    """The catalogue (locale/en/LC_MESSAGES/django.po): a passkey is a passkey wherever it is
    named, including on pages the library draws (NAF, 2026-09-20: "I do want our UI to always say
    Passkey instead of Security key")."""
    from django.utils.translation import gettext

    assert gettext("Security Keys") == "Passkeys"
    assert gettext("Use a security key") == "Use a passkey"
    assert gettext("Add Security Key") == "Add a passkey"


def test_confirm_access_offers_a_password_and_a_passkey_and_no_authenticator_code(monkeypatch):
    """One screen for confirming it is you, laid out like the sign-in page.

    > TOTP tokens/authenticator app is ONLY used for 2fa. So, it does not show up on any initial
    > screen. Passwords or passkeys are the first line of entry. I actually like how it looks on
    > the login screen. — NAF, 2026-09-20

    An authenticator code proves a second factor at sign-in; it is not a way of saying who you
    are, and offering it here put "Alternative options" under a page that already knows.
    """
    from allauth.mfa.models import Authenticator

    user = _member()
    c = Client()
    c.force_login(user)

    body = c.get("/accounts/reauthenticate/").content.decode()
    assert "Confirm" in body and 'type="password"' in body
    assert "authenticator" not in body.lower()
    assert "Use a passkey" not in body  # no passkey on this account, so no button

    Authenticator.objects.create(user=user, type=Authenticator.Type.TOTP, data={"secret": "x" * 32})
    body = c.get("/accounts/reauthenticate/").content.decode()
    assert "authenticator" not in body.lower(), "an enrolled app still does not appear here"

    monkeypatch.setattr(
        "apps.accounts.views_mfa.webauthn_auth.begin_authentication", lambda user: {"x": 1}
    )
    Authenticator.objects.create(
        user=user, type=Authenticator.Type.WEBAUTHN, data={"credential": {}}
    )
    body = c.get("/accounts/reauthenticate/").content.decode()
    assert "Use a passkey" in body
    assert body.index("Confirm") < body.index("Use a passkey"), "password first, as on sign-in"
    assert "authenticator" not in body.lower()
