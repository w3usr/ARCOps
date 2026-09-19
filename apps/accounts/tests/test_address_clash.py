"""An address that already belongs to somebody, met on the way in.

The advisor completed an invitation, created a second one to the same address, and tried it
three times on 2026-09-19. Each attempt answered Server Error (500) and left an account behind
with no address on it: three "Kay Craigie" rows, each in the member group, none able to sign in.
"""

from datetime import timedelta

import pytest
from django.core.management import call_command
from django.test import Client
from django.utils import timezone

from apps.accounts.addresses import AddressInUse
from apps.accounts.models import Invitation, User

pytestmark = pytest.mark.django_db
PASSWORD = "a-Long-Password-77!"


@pytest.fixture(autouse=True)
def club():
    call_command("club_import")


def _officer():
    return User.objects.create_user(
        "off@example.org", PASSWORD, groups=["officer"], first_name="Ann", last_name="Officer"
    )


def _invitation(issuer, email="taken@example.org"):
    return Invitation.objects.create(
        email=email,
        category="student",
        issued_by=issuer,
        expires_at=timezone.now() + timedelta(days=14),
    )


def _join(token, **over):
    data = {
        "first_name": "Kay",
        "middle_name": "",
        "last_name": "Craigie",
        "preferred_name": "",
        "callsign": "",
        "cell_phone": "",
        "password1": PASSWORD,
        "password2": PASSWORD,
        "consent": "on",
    }
    data.update(over)
    return Client().post(f"/me/invite/{token}/", data)


def test_a_refused_address_leaves_no_account_behind():
    """create_user is all or nothing. It used to save the account, then add the address, then
    raise, leaving a member with no way to sign in and no way to be told apart from a real one.
    """
    officer = _officer()
    User.objects.create_user(
        "taken@example.org", PASSWORD, groups=["member"], first_name="First", last_name="Holder"
    )
    before = User.objects.count()

    with pytest.raises(AddressInUse):
        User.objects.create_user(
            "taken@example.org", PASSWORD, groups=["member"], first_name="Second", last_name="Try"
        )

    assert User.objects.count() == before, "a refused address must not leave an account"
    assert not User.objects.filter(first_name="Second").exists()
    assert officer.pk  # the fixture is used; the officer is untouched


def test_the_join_form_says_so_instead_of_answering_500():
    officer = _officer()
    User.objects.create_user(
        "taken@example.org", PASSWORD, groups=["member"], first_name="First", last_name="Holder"
    )
    inv = _invitation(officer)
    before = User.objects.count()

    r = _join(inv.token)

    assert r.status_code == 200, "a taken address is a form error, not a server error"
    body = r.content.decode()
    assert "There is already an account for taken@example.org" in body
    assert "Sign in instead" in body
    assert User.objects.count() == before
    inv.refresh_from_db()
    assert inv.state == "created", "a refused attempt must not use the invitation up"


def test_three_refused_attempts_leave_three_nothings():
    """The shape of what actually happened: retrying made another account every time."""
    officer = _officer()
    User.objects.create_user(
        "taken@example.org", PASSWORD, groups=["member"], first_name="First", last_name="Holder"
    )
    inv = _invitation(officer)
    before = User.objects.count()
    for _ in range(3):
        assert _join(inv.token).status_code == 200
    assert User.objects.count() == before
    assert not User.objects.filter(addresses__isnull=True).exclude(under_18=True).exists()


def test_an_officer_cannot_invite_an_address_that_already_has_an_account():
    """Refused at the near end too, so nobody is sent a link that is certain to fail."""
    officer = _officer()
    User.objects.create_user(
        "taken@example.org", PASSWORD, groups=["member"], first_name="First", last_name="Holder"
    )
    c = Client()
    c.force_login(officer)
    r = c.post(
        "/me/invitations/", {"email": "taken@example.org", "category": "student"}, follow=True
    )
    body = r.content.decode()
    assert "First Holder already has an account with that address" in body
    assert not Invitation.objects.filter(email="taken@example.org").exists()


def test_a_free_address_is_still_invited_and_admitted():
    """The guard must not refuse the ordinary case."""
    officer = _officer()
    c = Client()
    c.force_login(officer)
    c.post("/me/invitations/", {"email": "new@example.org", "category": "student"})
    inv = Invitation.objects.get(email="new@example.org")
    assert _join(inv.token).status_code == 302  # signed in, on to the dashboard
    inv.refresh_from_db()
    assert inv.state == "completed"
    assert User.objects.by_address("new@example.org").get().addresses.count() == 1
