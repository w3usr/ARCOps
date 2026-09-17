"""Acting at a lower level than you hold.

The advisor, 2026-09-17: "I don't always like being logged in with the superuser view, even
though my account has superuser capabilities... By default, it is set to the highest level below
superuser. To get superuser, the user has to explicitly change the view and re-authenticate."
"""

import pytest
from django.core.management import call_command
from django.test import Client

from apps.accounts.models import User
from apps.ops.models import AuditLog

pytestmark = pytest.mark.django_db
PASSWORD = "pw-Testing-123"


@pytest.fixture(autouse=True)
def club():
    call_command("club_import")


def _sysadmin():
    return User.objects.create_user(
        "sys@example.org", PASSWORD, first_name="Sys", last_name="Admin", is_superuser=True
    )


def _signed_in(user):
    c = Client()
    c.force_login(user)
    return c


def test_a_sysadmin_signs_in_acting_at_the_clubs_everyday_level():
    c = _signed_in(_sysadmin())
    c.get("/")  # the level is settled on the first request
    assert c.session["acting_view"] == "advisor"
    # the everyday level cannot reach the club's configuration
    assert c.get("/ops/settings/").status_code == 404
    assert c.get("/ops/groups/").status_code == 404
    # and everything the club's work needs is there
    assert c.get("/members/").status_code == 200
    assert c.get("/credentials/approvals/").status_code == 200


def test_raising_the_level_asks_for_the_password_and_is_recorded():
    c = _signed_in(_sysadmin())
    c.get("/")

    r = c.post("/me/level/", {"view": "sysadmin", "password": "not-the-password"}, follow=True)
    assert b"password is not right" in r.content
    assert c.session["acting_view"] == "advisor"
    assert c.get("/ops/settings/").status_code == 404
    assert AuditLog.objects.filter(action="view.raise_refused").exists()

    c.post("/me/level/", {"view": "sysadmin", "password": PASSWORD}, follow=True)
    assert c.session["acting_view"] == "sysadmin"
    assert c.get("/ops/settings/").status_code == 200
    assert AuditLog.objects.filter(action="view.raised").exists()


def test_dropping_the_level_needs_no_password_and_takes_the_capability_away():
    c = _signed_in(_sysadmin())
    c.post("/me/level/", {"view": "sysadmin", "password": PASSWORD})
    assert c.get("/ops/settings/").status_code == 200

    c.post("/me/level/", {"view": "member"})  # nothing is asked for on the way down
    assert c.session["acting_view"] == "member"
    assert c.get("/ops/settings/").status_code == 404
    assert c.get("/members/").status_code == 200  # a member sees the directory
    assert c.get("/members/archive/").status_code == 404  # and not the archive
    assert AuditLog.objects.filter(action="view.lowered").exists()


def test_the_lower_level_refuses_the_action_rather_than_hiding_the_button():
    """The whole point. A view that only hid controls would be trusted, and would be wrong."""
    member = User.objects.create_user(
        "mem@example.org", PASSWORD, first_name="Mem", last_name="Ber", groups=["member"]
    )
    c = _signed_in(_sysadmin())
    c.post("/me/level/", {"view": "member"})
    assert c.get(f"/members/{member.pk}/").status_code == 404
    assert c.post(f"/members/{member.pk}/", {"action": "archive"}).status_code == 404
    member.refresh_from_db()
    assert not member.is_archived


def test_nobody_may_act_above_themselves():
    officer = User.objects.create_user(
        "off@example.org", PASSWORD, first_name="Off", last_name="Icer", groups=["officer"]
    )
    c = _signed_in(officer)
    r = c.post("/me/level/", {"view": "advisor", "password": PASSWORD}, follow=True)
    assert b"not a level your account can act at" in r.content
    assert c.get("/credentials/approvals/").status_code == 404

    # an officer may still drop to a member's view, which is below them
    c.post("/me/level/", {"view": "member"})
    assert c.session["acting_view"] == "member"
    assert c.get("/me/invitations/").status_code == 404


def test_the_page_offers_only_the_levels_the_account_holds():
    c = _signed_in(_sysadmin())
    body = c.get("/me/level/").content.decode()
    for label in ("Provisional", "Member", "Club officer", "Faculty advisor", "Sysadmin"):
        assert label in body, label
    assert "asks for your password" in body

    officer = User.objects.create_user(
        "off@example.org", PASSWORD, first_name="Off", last_name="Icer", groups=["officer"]
    )
    body = _signed_in(officer).get("/me/level/").content.decode()
    assert "Club officer" in body and "Faculty advisor" not in body and "Sysadmin" not in body


def test_the_sidebar_names_the_level_on_every_page():
    c = _signed_in(_sysadmin())
    body = c.get("/").content.decode()
    assert "Faculty advisor" in body and "/me/level/" in body
