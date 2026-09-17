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

    def mk(email, lvl, **kw):
        return User.objects.create_user(email, "pw-Testing-123", access_level=lvl, **kw)

    return {
        "sys": mk("root@uni.example", AccessLevel.SYSADMIN, first_name="Sys", last_name="Admin"),
        "off": mk("off@uni.example", AccessLevel.OFFICER, first_name="Ann", last_name="Officer"),
        "mem": mk(
            "mem@home.example",
            AccessLevel.MEMBER,
            first_name="Mo",
            last_name="Member",
            callsign="N0MEM",
            category="student",
        ),
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
    from apps.accounts import addresses

    addresses.add(people["mem"], "mo@uni.example", confirmed=True)
    body = _as(people["off"]).get("/members/").content.decode()
    assert "Mo Member" in body
    # every address an officer may write to, not one of them chosen for them
    assert "mem@home.example" in body and "mo@uni.example" in body
    assert _as(people["mem"]).get(f"/members/{people['off'].pk}/").status_code == 404


def test_sysadmin_edits_privilege_fields_and_cannot_demote_self(people):
    c, mem, sys_ = _as(people["sys"]), people["mem"], people["sys"]
    c.post(
        f"/members/{mem.pk}/",
        {
            "action": "save",
            "first_name": "Mo",
            "middle_name": "",
            "last_name": "Member",
            "callsign": "n0mem",
            "category": "student",
            "club_position": "president",
            "access_level": "officer",
            "under_18": "",
        },
    )
    mem.refresh_from_db()
    assert (mem.access_level, mem.club_position, mem.callsign) == ("officer", "president", "N0MEM")
    r = c.post(
        f"/members/{sys_.pk}/",
        {
            "action": "save",
            "first_name": "Sys",
            "middle_name": "",
            "last_name": "Admin",
            "callsign": "",
            "category": "",
            "club_position": "",
            "access_level": "member",
            "under_18": "",
        },
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
    c.post(
        f"/members/{mem.pk}/", {"action": "save", "club_position": "", "access_level": "sysadmin"}
    )
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
        {
            "first_name": "New",
            "middle_name": "",
            "last_name": "Person",
            "preferred_name": "",
            "callsign": "",
            "cell_phone": "",
            "password1": "a-Long-Password-77!",
            "password2": "a-Long-Password-77!",
            "consent": "on",
        },
    )
    u = User.objects.by_address("new@uni.example").get()
    row = u.addresses.get(address="new@uni.example")
    assert row.kind == "institution" and row.confirmed and u.addresses.count() == 1
    # An address outside the institution's domain is a personal one.
    c.post("/me/invitations/", {"email": "other@home.example", "category": "student"})
    inv2 = Invitation.objects.get(email="other@home.example")
    Client().post(
        f"/me/invite/{inv2.token}/",
        {
            "first_name": "O",
            "middle_name": "",
            "last_name": "P",
            "preferred_name": "",
            "callsign": "",
            "cell_phone": "",
            "password1": "a-Long-Password-77!",
            "password2": "a-Long-Password-77!",
            "consent": "on",
        },
    )
    u2 = User.objects.by_address("other@home.example").get()
    assert u2.addresses.get(address="other@home.example").kind == "personal"


def test_sysadmin_edits_every_field_and_the_change_is_audited(people):
    """The advisor, 2026-09-17: sysadmins edit every field. Addresses have their own controls, so
    the form holds the rest of the account."""
    from apps.ops.models import AuditLog

    s, m = people["sys"], people["mem"]
    c = _as(s)
    body = c.get(f"/members/{m.pk}/").content.decode()
    for label in ("Mobile number", "Graduation year", "Category", "Access level"):
        assert label in body
    assert "Sign-in email" not in body  # every confirmed address signs in; none of them is special
    data = {
        "action": "save",
        "first_name": m.first_name,
        "last_name": m.last_name,
        "category": m.category,
        "access_level": m.access_level,
        "cell_phone": "555-0199",
        "student_level": "undergraduate",
        "graduation_year": "2028",
    }
    r = c.post(f"/members/{m.pk}/", data)
    assert r.status_code in (200, 302)
    m.refresh_from_db()
    assert m.cell_phone == "555-0199" and m.graduation_year == 2028
    row = AuditLog.objects.filter(action="member.edited").latest("at")
    assert "cell_phone" in row.after

    # and the addresses are changed from the same page, through their own controls
    c.post(f"/members/{m.pk}/", {"action": "address_add", "address": "Moved@example.org"})
    assert m.addresses.filter(address="moved@example.org").exists()
    r = c.post(
        f"/members/{m.pk}/",
        {"action": "address_confirm", "address": s.email},
        follow=True,
    )
    assert b"not on the account" in r.content  # a sysadmin cannot hand over someone else's


def test_officer_looks_a_callsign_up_in_the_fcc_table(people):
    """The advisor asked for this rather than an override: a button that re-reads the local FCC
    table for a member's callsign, for officers as well as sysadmins."""
    from apps.credentials.models import LicenseRecord, UlsLicense
    from apps.ops.models import AuditLog

    m = people["mem"]
    m.callsign = "N0LOOK"
    m.save()
    UlsLicense.objects.create(
        callsign="N0LOOK",
        first_name="Mo",
        last_name="Member",
        operator_class="General",
        status="active",
    )
    c = _as(people["off"])
    assert b"Look this callsign up in the FCC table" in c.get(f"/members/{m.pk}/").content
    r = c.post(f"/members/{m.pk}/", {"action": "license_lookup"}, follow=True)
    assert r.status_code == 200 and b"N0LOOK: General, active" in r.content
    assert LicenseRecord.objects.get(user=m).operator_class == "General"
    assert AuditLog.objects.filter(action="license.looked_up").exists()
    # a callsign the table does not know says so rather than inventing a class
    m.callsign = "N0NONE"
    m.save()
    r = c.post(f"/members/{m.pk}/", {"action": "license_lookup"}, follow=True)
    assert b"not in the local FCC table" in r.content


def test_student_fields_are_cleared_when_the_category_is_not_student(people):
    """They are hidden on the page while the category is anything else; the server makes it true."""
    from apps.ops.models import ClubSetting

    ClubSetting.objects.update_or_create(
        key="member_categories",
        defaults={
            "value": [
                {"key": "student", "label": "Student"},
                {"key": "faculty", "label": "Faculty"},
            ]
        },
    )
    s, m = people["sys"], people["mem"]
    m.category, m.student_level, m.graduation_year = "student", "undergraduate", 2028
    m.save()
    c = _as(s)
    body = c.get(f"/members/{m.pk}/").content.decode()
    assert 'data-reveal-when="#id_category" data-reveal-value="student"' in body
    c.post(
        f"/members/{m.pk}/",
        {
            "action": "save",
            "first_name": m.first_name,
            "last_name": m.last_name,
            "category": "faculty",
            "access_level": m.access_level,
            "email": m.email,
            "student_level": "undergraduate",
            "graduation_year": "2028",
        },
    )
    m.refresh_from_db()
    assert m.category == "faculty" and m.student_level == "" and m.graduation_year is None
