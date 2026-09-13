"""The member directory and management pages (FR-6, FR-7, FR-13, §2.1 to §2.3) and the
placement of the sign-in address on acceptance."""

import re

import pytest
from django.test import Client

from apps.accounts.models import AccessLevel, Invitation, User
from apps.ops.models import ClubSetting

pytestmark = pytest.mark.django_db


@pytest.fixture
def people():
    ClubSetting.objects.update_or_create(
        key="member_categories",
        defaults={"value": [{"key": "student", "label": "Student", "email_domain": "uni.example"}]},
    )
    ClubSetting.objects.update_or_create(
        key="club_positions", defaults={"value": [{"key": "president", "label": "President"}]}
    )
    mk = lambda email, lvl, **kw: User.objects.create_user(email, "pw-Testing-123", access_level=lvl, **kw)  # noqa: E731
    return {
        "sys": mk("root@uni.example", AccessLevel.SYSADMIN, first_name="Sys", last_name="Admin"),
        "off": mk("off@uni.example", AccessLevel.OFFICER, first_name="Ann", last_name="Officer"),
        "mem": mk("mem@home.example", AccessLevel.MEMBER, first_name="Mo", last_name="Member", callsign="N0MEM", category="student"),
    }


def _as(user):
    c = Client()
    c.force_login(user)
    return c


def test_members_see_short_names_and_officers_see_everything(people):
    body = _as(people["mem"]).get("/members/").content.decode()
    directory = re.search(r'<ul class="directory">(.*?)</ul>', body, re.S).group(1)
    assert "Mo N0MEM" in directory and "Ann O." in directory
    assert "@" not in directory  # no addresses for members (FR-67)
    body = _as(people["off"]).get("/members/").content.decode()
    assert "Mo Member" in body and "mem@home.example" in body
    assert _as(people["mem"]).get(f"/members/{people['off'].pk}/").status_code == 404


def test_sysadmin_edits_privilege_fields_and_cannot_demote_self(people):
    c, mem, sys_ = _as(people["sys"]), people["mem"], people["sys"]
    c.post(
        f"/members/{mem.pk}/",
        {"action": "save", "first_name": "Mo", "middle_name": "", "last_name": "Member", "callsign": "n0mem",
         "category": "student", "club_position": "president", "access_level": "officer", "under_18": ""},
    )
    mem.refresh_from_db()
    assert (mem.access_level, mem.club_position, mem.callsign) == ("officer", "president", "N0MEM")
    r = c.post(
        f"/members/{sys_.pk}/",
        {"action": "save", "first_name": "Sys", "middle_name": "", "last_name": "Admin", "callsign": "",
         "category": "", "club_position": "", "access_level": "member", "under_18": ""},
    )
    sys_.refresh_from_db()
    assert sys_.access_level == "sysadmin" and "your own sysadmin" in r.content.decode()


def test_officer_sets_club_position_only(people):
    c, mem = _as(people["off"]), people["mem"]
    body = c.get(f"/members/{mem.pk}/").content.decode()
    assert 'name="club_position"' in body and 'name="access_level"' not in body
    assert "temporary password" not in body.lower()
    c.post(f"/members/{mem.pk}/", {"action": "save", "club_position": "president"})
    mem.refresh_from_db()
    assert mem.club_position == "president"
    # A forged privilege change is ignored: the field is not on an officer's form.
    c.post(f"/members/{mem.pk}/", {"action": "save", "club_position": "", "access_level": "sysadmin"})
    mem.refresh_from_db()
    assert mem.access_level == "member"
    assert c.post(f"/members/{mem.pk}/", {"action": "temporary_password"}).status_code == 404


def test_temporary_password_shown_once_and_access_removed_and_restored(people):
    c, mem = _as(people["sys"]), people["mem"]
    body = c.post(f"/members/{mem.pk}/", {"action": "temporary_password"}).content.decode()
    shown = re.search(r'<code id="tpv">([^<]+)</code>', body).group(1)
    mem.refresh_from_db()
    assert mem.password_is_temporary and mem.check_password(shown)
    assert shown not in c.get(f"/members/{mem.pk}/").content.decode()
    c.post(f"/members/{mem.pk}/", {"action": "close", "reason": "graduated"})
    mem.refresh_from_db()
    assert mem.access_level == "none"
    c.post(f"/members/{mem.pk}/", {"action": "reopen"})
    mem.refresh_from_db()
    assert mem.access_level == "member"


def test_invitation_reissue_and_acceptance_places_the_sign_in_address(people):
    c = _as(people["off"])
    c.post("/me/invitations/", {"email": "new@uni.example", "category": "student"})
    inv = Invitation.objects.get(email="new@uni.example")
    body = c.post(f"/me/invitations/{inv.pk}/", {"action": "reissue"}).content.decode()
    inv.refresh_from_db()
    assert inv.state == "revoked" and "/me/invite/" in body
    new = Invitation.objects.get(email="new@uni.example", state="created")
    Client().post(
        f"/me/invite/{new.token}/",
        {"first_name": "New", "middle_name": "", "last_name": "Person", "preferred_name": "", "callsign": "",
         "cell_phone": "", "password1": "a-Long-Password-77!", "password2": "a-Long-Password-77!", "consent": "on"},
    )
    u = User.objects.get(email="new@uni.example")
    assert u.institution_email == "new@uni.example" and u.personal_email == ""
    # A personal-domain sign-in address lands in the personal slot.
    c.post("/me/invitations/", {"email": "other@home.example", "category": "student"})
    inv2 = Invitation.objects.get(email="other@home.example")
    Client().post(
        f"/me/invite/{inv2.token}/",
        {"first_name": "O", "middle_name": "", "last_name": "P", "preferred_name": "", "callsign": "",
         "cell_phone": "", "password1": "a-Long-Password-77!", "password2": "a-Long-Password-77!", "consent": "on"},
    )
    u2 = User.objects.get(email="other@home.example")
    assert u2.personal_email == "other@home.example" and u2.institution_email == ""
