"""The command that makes the first account, run at the server console before anyone can sign in."""

import pytest
from django.core.management import call_command
from django.test import Client

from apps.accounts.models import AccessLevel, User

pytestmark = pytest.mark.django_db


def _run(**kw):
    call_command(
        "bootstrap_sysadmin",
        **{"email": "first@example.org", "first": "First", "last": "Sysadmin", **kw},
    )
    return User.objects.by_address("first@example.org").get()


def test_the_first_sysadmin_can_sign_in_with_the_address_it_was_given(capsys):
    user = _run()
    password = capsys.readouterr().out.rsplit(": ", 1)[-1].strip()
    assert user.access_level == AccessLevel.SYSADMIN and user.is_superuser
    row = user.addresses.get(address="first@example.org")
    assert row.confirmed, "whoever runs this at the console vouches for the address"
    c = Client()
    assert c.login(email="first@example.org", password=password)
    # and it lands on the forced password change, because the password is temporary (FR-7)
    assert c.get("/events/")["Location"].startswith("/accounts/password/change/")


def test_running_it_again_promotes_the_same_account_rather_than_making_a_second():
    first = _run()
    again = _run(first="Other", last="Name")
    assert again.pk == first.pk and User.objects.count() == 1
    assert again.first_name == "First", "an existing account keeps its own details"
