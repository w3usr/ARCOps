"""A profile is read, and edited on a page of its own.

A name opens a read-only view of the profile. Whoever may edit it (the member on their own page,
an officer, a sysadmin) gets an Edit profile button. A read-only page can later be shown
publicly, and is hard to change by accident.
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


def _user(address, groups, **extra):
    extra.setdefault("first_name", "Pat")
    extra.setdefault("last_name", "Person")
    return User.objects.create_user(address, PASSWORD, groups=groups, **extra)


def _as(user):
    c = Client()
    c.force_login(user)
    return c


@pytest.fixture
def pair():
    officer = _user("off@example.org", ["officer"], first_name="Ann", last_name="Officer")
    member = _user(
        "mem@example.org", ["member"], first_name="Mo", last_name="Member", callsign="N0MEM"
    )
    return officer, member


def test_a_members_page_holds_nothing_that_changes_anything(pair):
    officer, member = pair
    body = _as(officer).get(f"/members/{member.pk}/").content.decode()
    assert "N0MEM" in body and "Mo Member" in body
    page = body.split("<main", 1)[1]  # the sidebar keeps its sign-out form
    assert "<form" not in page, "a page opened to read cannot change what it shows"
    assert "csrfmiddlewaretoken" not in page


def test_the_edit_button_is_there_for_whoever_may_edit(pair):
    officer, member = pair
    body = _as(officer).get(f"/members/{member.pk}/").content.decode()
    assert f'href="/members/{member.pk}/edit/"' in body and "Edit profile" in body
    assert 'name="groups"' in _as(officer).get(f"/members/{member.pk}/edit/").content.decode()


def test_your_own_page_is_a_member_page(pair):
    """Your profile and your member page are one page: /me/ redirects to /members/<pk>/."""
    _, member = pair
    c = _as(member)
    r = c.get("/me/")
    assert r.status_code == 302 and r["Location"] == f"/members/{member.pk}/"
    assert c.get("/me/edit/")["Location"] == f"/members/{member.pk}/edit/"


def test_your_own_profile_reads_and_the_edit_page_holds_the_form(pair):
    _, member = pair
    c = _as(member)
    body = c.get("/me/", follow=True).content.decode()
    assert "Edit profile and preferences" in body
    assert f'href="/members/{member.pk}/edit/"' in body
    # nothing on it changes anything, preferences included
    assert "<form" not in body.split("<main", 1)[1]
    assert "N0MEM" in body, "the account is shown, whether or not it is being edited"
    assert 'name="callsign"' not in body
    assert "Notifications" in body and 'name="email" value="reminder"' not in body
    edit = c.get("/me/edit/", follow=True).content.decode()
    assert 'name="callsign"' in edit and 'name="preferred_name"' in edit
    assert 'name="email" value="reminder"' in edit  # your preferences, on the same edit page
    assert "Close my account" in edit


def test_editing_your_profile_lands_back_on_it(pair):
    _, member = pair
    c = _as(member)
    r = c.post(
        f"/members/{member.pk}/edit/",
        {"action": "save", "first_name": "Mo", "last_name": "Member", "preferred_name": "Moe"},
    )
    assert r.status_code == 302 and r["Location"] == f"/members/{member.pk}/"
    assert User.objects.get(pk=member.pk).preferred_name == "Moe"


def test_your_name_in_the_corner_opens_your_profile(pair):
    _, member = pair
    body = _as(member).get("/events/").content.decode()
    foot = body.split('class="sidenav-foot"')[1]
    assert 'href="/me/"' in foot and "N0MEM" in foot


def test_a_member_under_18_has_no_edit_page(pair):
    officer, _ = pair
    minor = _user("kid@example.org", ["member"], first_name="Kim", last_name="Young", under_18=True)
    c = _as(minor)
    assert c.get("/me/", follow=True).status_code == 200
    assert c.get("/me/edit/", follow=True).status_code == 404
    body = c.get("/me/", follow=True).content.decode()
    assert "Edit profile" not in body
    assert "Your guardian makes changes to this account" in body


def test_a_member_cannot_reach_anybody_elses_page(pair):
    officer, member = pair
    c = _as(member)
    assert c.get(f"/members/{officer.pk}/").status_code == 404
    assert c.get(f"/members/{officer.pk}/edit/").status_code == 404
    assert c.get(f"/members/{member.pk}/").status_code == 200, "their own is always theirs"


def test_a_name_from_the_fcc_says_so_where_the_fields_would_be(pair):
    """Where the first, middle and last name cannot be edited, the page says why.

    With a callsign the name is the FCC's (FR-8), and the page never said so: the partial
    looked for a `subject` variable that neither page passed.
    """
    from apps.credentials.models import LicenseRecord

    _, member = pair
    member.name_from_uls = True
    member.save(update_fields=["name_from_uls"])
    LicenseRecord.objects.create(
        user=member, callsign="N0MEM", operator_class="Extra", status="active"
    )
    body = _as(member).get("/me/edit/", follow=True).content.decode()
    assert 'name="first_name"' not in body, "the FCC's name is not typed here (FR-8)"
    assert "The name above is the FCC's record for" in body and "N0MEM" in body
    assert "Preferred name" in body, "and it says what to set instead"
    # and the name itself is printed above the note, in the three fields it is stored in
    assert ">First name</dt>" in body and ">Last name</dt>" in body


def test_your_own_fields_are_headed_details(pair):
    _, member = pair
    body = _as(member).get("/me/edit/", follow=True).content.decode()
    assert ">Details</h2>" in body
    assert "Club position" not in body, "your own fields are not somebody else's to assign"


def test_the_profile_counts_down_a_license_and_an_agreement_inside_their_notice_windows(pair):
    """FR-103: the license notice is a banner on the profile, the agreement notice a countdown."""
    import datetime as dt

    from django.utils import timezone

    from apps.credentials.models import (
        AgreementTemplate,
        CredentialType,
        LicenseRecord,
        SignedAgreement,
    )

    officer, member = pair
    today = timezone.now().date()
    lic = LicenseRecord.objects.create(
        user=member,
        callsign="N0MEM",
        operator_class="G",
        status="active",
        expiry_date=today + dt.timedelta(days=20),
    )
    cred, _ = CredentialType.objects.get_or_create(
        key="station_access", defaults={"label": "Station access", "established_by": "agreement"}
    )
    t = AgreementTemplate.objects.create(
        key="sa",
        credential=cred,
        title="Station Agreement",
        audience=["student"],
        version=1,
        content_hash="h1",
        html="<p>Rules.</p>",
        effective_date="2026-01-01",
        is_current=True,
    )
    a = SignedAgreement.objects.create(
        user=member,
        template=t,
        credential=cred,
        signer_name="Mo Member",
        content_hash="h1",
        state="approved",
        expires_on=today + dt.timedelta(days=1),
        approved_at=timezone.now(),
    )
    own = _as(member).get(f"/members/{member.pk}/").content.decode()
    assert "your license expires in 20 days; renew with the FCC." in own
    assert "Expires in 1 day</strong>; <a" in own and "re-sign on Agreements" in own
    theirs = _as(officer).get(f"/members/{member.pk}/").content.decode()
    assert "their license expires in 20 days." in theirs and "re-sign on" not in theirs

    # Outside the windows the page keeps to the dates alone.
    lic.expiry_date = today + dt.timedelta(days=91)
    lic.save()
    a.expires_on = today + dt.timedelta(days=31)
    a.save()
    own = _as(member).get(f"/members/{member.pk}/").content.decode()
    assert "license expires in" not in own and "Expires in" not in own


def test_an_unread_license_notice_earns_the_home_banner(pair):
    from apps.comms.services import compose

    _, member = pair
    compose(member, "license_expiry", "Your license expires soon", "<p>Renew.</p>")
    home = _as(member).get("/").content.decode()
    assert "1 unread message" in home.split("My next slots")[0]
