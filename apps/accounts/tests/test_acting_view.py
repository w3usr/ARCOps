"""Acting at a lower level than you hold.

The advisor, 2026-09-17: "I don't always like being logged in with the superuser view, even
though my account has superuser capabilities... By default, it is set to the highest level below
superuser. To get superuser, the user has to explicitly change the view and re-authenticate."
"""

import time

import pytest
from allauth.account.internal.flows.login import AUTHENTICATION_METHODS_SESSION_KEY
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


def _just_confirmed(client):
    """Stamp the session the way **Confirm Access** does: a record marked `reauthenticated`.

    force_login leaves no record at all, and signing in leaves one without that mark, which is
    the difference that matters now: a raise wants a confirmation of its own, not merely a
    recent sign-in (apps.accounts.reauth).
    """
    session = client.session
    session[AUTHENTICATION_METHODS_SESSION_KEY] = [
        {"method": "password", "at": time.time(), "reauthenticated": True}
    ]
    session.save()
    return client


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


def test_raising_the_level_asks_you_to_confirm_and_is_recorded():
    """NAF, 2026-09-20: "I should be able to use a passkey in addition to a password here." The
    page no longer holds a password field of its own; it hands the person to the sign-in
    library's Confirm Access, which offers whatever the account carries.
    """
    user = _sysadmin()
    c = _signed_in(user)
    c.get("/")

    r = c.post("/me/level/", {"view": "sysadmin"})
    assert r.status_code == 302 and r["Location"].startswith("/accounts/reauthenticate/")
    assert "next=%2Fme%2Flevel%2F" in r["Location"], "and it comes back here"
    assert c.session["acting_view"] == "advisor", "nothing has changed yet"

    # walking away without confirming leaves the level alone, and says so
    r = c.get("/me/level/", follow=True)
    assert b"not confirmed" in r.content
    assert c.session["acting_view"] == "advisor"
    assert c.get("/ops/settings/").status_code == 404
    assert AuditLog.objects.filter(action="view.raise_refused").exists()

    # and with the password accepted on that page, the level rises
    c.post("/me/level/", {"view": "sysadmin"})
    c.post("/accounts/reauthenticate/", {"password": PASSWORD})
    c.get("/me/level/")
    assert c.session["acting_view"] == "sysadmin"
    assert c.get("/ops/settings/").status_code == 200
    assert AuditLog.objects.filter(action="view.raised").exists()


def test_every_raise_is_confirmed_on_its_own():
    """A confirmation is spent by the raise it was given for.

    > Let's also make elevate to sysadmin an every time operation. We don't want people
    > accidentally logging in as sysadmin. — NAF, 2026-09-20

    It used to hold for five minutes, so a second raise in that window went through unasked.
    """
    c = _just_confirmed(_signed_in(_sysadmin()))
    c.get("/")
    r = c.post("/me/level/", {"view": "sysadmin"})
    assert r.status_code == 302 and "/accounts/reauthenticate/" not in r["Location"]
    assert c.session["acting_view"] == "sysadmin"

    # Down, then up again a moment later: the same confirmation does not serve twice.
    c.post("/me/level/", {"view": "member"})
    r = c.post("/me/level/", {"view": "sysadmin"})
    assert "/accounts/reauthenticate/" in r["Location"]
    assert c.session["acting_view"] == "member"

    # A fresh confirmation raises it again.
    _just_confirmed(c)
    r = c.post("/me/level/", {"view": "sysadmin"})
    assert "/accounts/reauthenticate/" not in r["Location"]
    assert c.session["acting_view"] == "sysadmin"


def test_signing_in_is_not_a_confirmation():
    """A record left by signing in carries no `reauthenticated` mark, so it does not raise."""
    c = _signed_in(_sysadmin())
    session = c.session
    session[AUTHENTICATION_METHODS_SESSION_KEY] = [{"method": "password", "at": time.time()}]
    session.save()
    c.get("/")
    r = c.post("/me/level/", {"view": "sysadmin"})
    assert "/accounts/reauthenticate/" in r["Location"]
    assert c.session["acting_view"] == "advisor"


def test_dropping_the_level_is_never_asked_about_and_takes_the_capability_away():
    c = _just_confirmed(_signed_in(_sysadmin()))
    c.get("/")
    c.post("/me/level/", {"view": "sysadmin"})
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
    assert c.get(f"/members/{member.pk}/edit/").status_code == 404
    assert c.post(f"/members/{member.pk}/edit/", {"action": "archive"}).status_code == 404
    member.refresh_from_db()
    assert not member.is_archived


def test_nobody_may_act_above_themselves():
    c = _signed_in(_sysadmin())
    c.post("/me/level/", {"view": "member"})  # a sysadmin drops to a member's view
    r = c.post("/me/level/", {"view": "nonesuch"}, follow=True)
    assert b"not a level your account can act at" in r.content
    assert c.session["acting_view"] == "member"
    assert c.get("/me/invitations/").status_code == 404


def test_only_a_sysadmin_has_levels_at_all():
    """NAF, 2026-09-19: "Only people with sysadmin privileges should be able to change their
    access view, even to something lower."

    An officer rehearsing as a member is a way to lose an afternoon wondering why the
    application has stopped working. The feature is there so somebody holding everything can
    put the dangerous half of it away.
    """
    officer = User.objects.create_user(
        "off@example.org", PASSWORD, first_name="Off", last_name="Icer", groups=["officer"]
    )
    c = _signed_in(officer)
    assert c.get("/me/level/").status_code == 404
    assert c.post("/me/level/", {"view": "member"}).status_code == 404
    assert "acting_view" not in c.session
    body = c.get("/").content.decode()
    assert "/me/level/" not in body, "and no way to reach it from the sidebar"
    assert c.get("/me/invitations/").status_code == 200, "an officer is simply an officer"


def test_the_page_offers_only_the_levels_the_account_holds():
    c = _signed_in(_sysadmin())
    body = c.get("/me/level/").content.decode()
    for label in ("Provisional", "Member", "Club officer", "Faculty advisor", "Sysadmin"):
        assert label in body, label
    assert "asks you to confirm" in body

    # and a sysadmin is offered every level, because a sysadmin holds everything


def test_the_sidebar_names_the_level_on_every_page():
    c = _signed_in(_sysadmin())
    body = c.get("/").content.decode()
    assert "Faculty advisor" in body and "/me/level/" in body


def test_the_django_admin_says_what_to_do_instead_of_looping():
    """The admin follows the level. Left alone it sent an unraised sysadmin to its own sign-in,
    which sent them back, which sent them to the admin again."""
    c = _signed_in(_sysadmin())
    r = c.get("/admin/", follow=True)
    assert r.status_code == 200
    assert r.redirect_chain[0][0].startswith("/me/level/?next=/admin/")
    assert b"opens at the Sysadmin level" in r.content

    _just_confirmed(c).post("/me/level/", {"view": "sysadmin"})
    assert c.get("/admin/").status_code == 200


def test_converting_a_minor_follows_its_own_capability():
    """It was gated on approving agreements, so a club that ticked "Convert a member's account
    to an adult's at 18" for a group got nothing."""
    from django.contrib.auth.models import Group, Permission

    from apps.accounts.models import Guardianship
    from apps.ops.capabilities import APP_LABEL

    converters = Group.objects.create(name="converters")
    converters.permissions.set(
        Permission.objects.filter(
            content_type__app_label=APP_LABEL,
            codename__in=["convert_minor_accounts", "view_member_records"],
        )
    )
    keeper = User.objects.create_user(
        "keep@example.org", PASSWORD, first_name="Kee", last_name="Per", groups=["converters"]
    )
    guardian = User.objects.create_user(
        "guard@example.org", PASSWORD, first_name="Gua", last_name="Rd", groups=["member"]
    )
    minor = User.objects.create_user(
        "kid@example.org",
        PASSWORD,
        first_name="Kid",
        last_name="Doe",
        under_18=True,
        groups=["member"],
    )
    Guardianship.objects.create(minor=minor, guardian=guardian)

    c = _signed_in(keeper)
    assert b"Convert to adult account" in c.get(f"/members/{minor.pk}/edit/").content
    c.post(f"/members/{minor.pk}/edit/", {"action": "convert_adult"})
    minor.refresh_from_db()
    assert not minor.under_18


def test_a_forgotten_request_to_raise_the_level_does_not_fire_later():
    """Asking for Sysadmin and wandering off leaves nothing armed: confirming access for
    something else half an hour later, then coming back to this page, raises nothing.
    """
    c = _signed_in(_sysadmin())
    c.get("/")
    c.post("/me/level/", {"view": "sysadmin"})  # arms the request, then the person leaves

    session = c.session
    pending = session["acting_view_pending"]
    pending["at"] = time.time() - 3600
    session["acting_view_pending"] = pending
    session[AUTHENTICATION_METHODS_SESSION_KEY] = [{"method": "password", "at": time.time()}]
    session.save()

    c.get("/me/level/")
    assert c.session["acting_view"] == "advisor", "the old request went stale"
    assert "acting_view_pending" not in c.session, "and is gone"
