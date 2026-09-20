"""Two-step verification is asked for, not inferred from a key.

NAF, 2026-09-20, after adding a passkey and being stopped at the next sign-in by a prompt for an
authenticator code he had never enrolled:

> I created a passkey, but did not enroll an authenticator app. So, I did not actually enable 2fa.

> We should make enabling 2fa explicit. I also want to make it optional right now. So, a user can
> enable or disable it. There should be a sysop option to make 2fa mandatory.

The sign-in library asks for a second factor whenever an account holds any enrolled
authenticator. Here the second step happens because the member turned it on, or because the club
requires it of their access group.
"""

import pytest
from allauth.mfa.models import Authenticator
from django.core.management import call_command
from django.test import Client

from apps.accounts.models import User
from apps.ops.config import set_setting
from apps.ops.models import AuditLog

pytestmark = pytest.mark.django_db
PASSWORD = "a-Long-Password-77!"


@pytest.fixture(autouse=True)
def club():
    call_command("club_import")


def _member(address="mem@example.org", groups=("member",), **extra):
    extra.setdefault("first_name", "Mem")
    extra.setdefault("last_name", "Ber")
    return User.objects.create_user(address, PASSWORD, groups=list(groups), **extra)


def _key(user):
    """A security key on the account, as the library records one."""
    return Authenticator.objects.create(
        user=user, type=Authenticator.Type.WEBAUTHN, data={"name": "Test key", "credential": {}}
    )


SECOND_STEP = "/accounts/2fa/authenticate/"


def _sign_in(address="mem@example.org"):
    """Sign in and stop at the first redirect. The page behind the second step is the library's
    own and parses the stored credential, which a test key cannot satisfy; where it sends you is
    what these tests are about."""
    client = Client()
    return client, client.post("/accounts/login/", {"login": address, "password": PASSWORD})


def test_a_key_on_its_own_does_not_ask_for_a_second_step():
    """The fault the advisor found: adding a key turned on something he never asked for."""
    _key(_member())
    client, response = _sign_in()
    assert response.status_code == 302 and SECOND_STEP not in response["Location"]
    assert client.session.get("_auth_user_id"), "signed in, with the password alone"


def test_turning_it_on_makes_sign_in_ask():
    member = _member()
    _key(member)
    client, _ = _sign_in()
    client.post("/me/two-step/", {"state": "on"})
    member.refresh_from_db()
    assert member.two_factor_enabled and member.two_factor_enabled_at
    assert AuditLog.objects.filter(action="two_factor.enabled").exists()

    client, response = _sign_in()
    assert response["Location"] == SECOND_STEP, "the second step, because it was asked for"
    assert not client.session.get("_auth_user_id"), "and not signed in until it is answered"


def test_turning_it_on_needs_something_to_answer_with():
    member = _member()
    client, _ = _sign_in()
    response = client.post("/me/two-step/", {"state": "on"}, follow=True)
    member.refresh_from_db()
    assert not member.two_factor_enabled
    assert b"Add an authenticator app or a security key first" in response.content
    assert response.request["PATH_INFO"] == "/accounts/2fa/", "and it takes you there"


def test_turning_it_off_leaves_the_keys_alone():
    member = _member()
    _key(member)
    member.two_factor_enabled = True
    member.save(update_fields=["two_factor_enabled"])
    client = Client()
    client.force_login(member)
    client.post("/me/two-step/", {"state": "off"})
    member.refresh_from_db()
    assert not member.two_factor_enabled
    assert Authenticator.objects.filter(user=member).count() == 1, "the key is still there"
    assert AuditLog.objects.filter(action="two_factor.disabled").exists()

    client, response = _sign_in()
    assert SECOND_STEP not in response["Location"], "nothing is asked for any more"


def test_a_club_can_require_it_of_an_access_group():
    """NAF, 2026-09-13 and again 2026-09-20: required for certain permission levels."""
    from apps.accounts import mfa

    officer = _member("off@example.org", groups=["officer"])
    member = _member()
    set_setting(None, "security.two_factor_required_groups", ["officer"])

    assert mfa.is_required(officer) and not mfa.is_required(member)

    client = Client()
    client.force_login(officer)
    response = client.post("/me/two-step/", {"state": "off"}, follow=True)
    officer.refresh_from_db()
    assert b"requires two-step verification" in response.content
    assert mfa.is_required(officer), "and it stays required"


def test_a_required_account_is_told_before_it_is_stopped():
    """The grace period: told for a fortnight, then made to set it up."""
    import datetime as dt

    from django.utils import timezone

    from apps.accounts import mfa

    officer = _member("off@example.org", groups=["officer"])
    set_setting(None, "security.two_factor_required_groups", ["officer"])
    set_setting(None, "security.two_factor_grace_days", 14)

    officer.two_factor_enabled_at = timezone.now()
    officer.save(update_fields=["two_factor_enabled_at"])
    when = mfa.deadline(officer)
    assert when and when - timezone.now() > dt.timedelta(days=13)

    body = Client()
    body.force_login(officer)
    page = body.get(f"/members/{officer.pk}/").content.decode()
    assert "required for your access level" in page
    assert when.strftime("%B") in page, "the date it stops being optional"

    _key(officer)
    assert mfa.deadline(officer) is None, "enrolled, so there is nothing to count down to"


def test_the_sysadmin_flag_counts_where_the_club_names_it():
    from apps.accounts import mfa

    sysadmin = _member("sys@example.org", groups=[], is_superuser=True)
    set_setting(None, "security.two_factor_required_groups", ["sysadmin"])
    assert mfa.is_required(sysadmin)
    set_setting(None, "security.two_factor_required_groups", ["advisor"])
    assert not mfa.is_required(sysadmin)


def _totp(user):
    return Authenticator.objects.create(
        user=user, type=Authenticator.Type.TOTP, data={"secret": "not-a-real-secret"}
    )


def test_the_second_step_asks_for_the_code_when_that_is_what_is_enrolled():
    member = _member()
    _totp(member)
    member.two_factor_enabled = True
    member.save(update_fields=["two_factor_enabled"])
    client, response = _sign_in()
    page = client.get(response["Location"]).content.decode()
    assert "code from your authenticator app" in page
    assert "Use a security key" not in page, "nothing is offered that this account cannot do"


def test_the_second_step_leads_with_the_key_when_that_is_what_is_enrolled(monkeypatch):
    """The advisor's case: a key and no authenticator app. The library's own page led with a code
    box he could not fill; this one leads with the key and offers the recovery codes second.
    """
    from allauth.mfa.webauthn.internal import auth as webauthn_auth

    monkeypatch.setattr(webauthn_auth, "begin_authentication", lambda user: {})
    member = _member()
    _key(member)
    Authenticator.objects.create(
        user=member, type=Authenticator.Type.RECOVERY_CODES, data={"migrated_codes": []}
    )
    member.two_factor_enabled = True
    member.save(update_fields=["two_factor_enabled"])

    client, response = _sign_in()
    page = client.get(response["Location"]).content.decode()
    assert page.index("Use a security key") < page.index("recovery code"), "the key comes first"
    assert "code from your authenticator app" not in page


def test_a_required_account_is_sent_to_enroll_once_the_grace_period_lapses():
    import datetime as dt

    from django.utils import timezone

    officer = _member("off@example.org", groups=["officer"])
    set_setting(None, "security.two_factor_required_groups", ["officer"])
    set_setting(None, "security.two_factor_grace_days", 14)

    client = Client()
    client.force_login(officer)
    assert client.get("/").status_code == 200, "told, not stopped, on the first day"
    officer.refresh_from_db()
    assert officer.two_factor_enabled_at, "the countdown starts when the account is first told"

    officer.two_factor_enabled_at = timezone.now() - dt.timedelta(days=15)
    officer.save(update_fields=["two_factor_enabled_at"])
    response = client.get("/", follow=True)
    assert response.request["PATH_INFO"] == "/accounts/2fa/", "sent to enroll"
    assert b"requires two-step verification" in response.content
    assert client.get("/accounts/2fa/totp/activate/").status_code in (200, 302), (
        "and the pages that let them enroll still open"
    )

    _key(officer)
    assert client.get("/").status_code == 200, "enrolled, so the club has what it asked for"
