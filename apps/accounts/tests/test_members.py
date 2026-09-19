"""The member directory and management pages (FR-6, FR-7, FR-13, §2.1 to §2.3) and the
placement of the sign-in address on acceptance."""

import re

import pytest
from django.contrib.auth.models import Group
from django.test import Client

from apps.accounts.models import Invitation, User
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
        return User.objects.create_user(
            email,
            "pw-Testing-123",
            groups=[] if lvl == "sysadmin" else [lvl],
            is_superuser=lvl == "sysadmin",
            **kw,
        )

    return {
        "sys": mk("root@uni.example", "sysadmin", first_name="Sys", last_name="Admin"),
        "off": mk("off@uni.example", "officer", first_name="Ann", last_name="Officer"),
        "mem": mk(
            "mem@home.example",
            "member",
            first_name="Mo",
            last_name="Member",
            callsign="N0MEM",
            category="student",
        ),
    }


def _as(user, view="sysadmin"):
    c = Client()
    c.force_login(user)
    if user.is_superuser:
        session = c.session  # the level a sysadmin's session acts at
        session["acting_view"] = view
        session.save()
    return c


def test_members_see_short_names_and_officers_see_everything(people):
    """Everyone gets the same table; a member gets fewer columns in it (NAF, 2026-09-19).

    What a member may see is unchanged from when this was a list of cards: a first name and a
    last initial, or a callsign, and no addresses (FR-67).
    """
    body = _as(people["mem"]).get("/members/").content.decode()
    rows = re.search(r"<tbody>(.*?)</tbody>", body, re.S).group(1)
    assert "<table" in body, "a member reads the same shape of page as an officer"
    assert "Ann O." in rows and "Officer" not in rows, "a last name is an initial to a member"
    assert "@" not in rows  # no addresses for members (FR-67)
    for withheld in ("Category", "Access", "Email", "Phone", "First", "Last", "Preferred"):
        assert f'data-label="{withheld}"' not in rows, f"{withheld} is an officer's column"

    from apps.accounts import addresses

    addresses.add(people["mem"], "mo@uni.example", confirmed=True)
    body = _as(people["off"]).get("/members/").content.decode()
    assert "Mo Member" in body
    # every address an officer may write to, not one of them chosen for them
    assert "mem@home.example" in body and "mo@uni.example" in body
    assert _as(people["mem"]).get(f"/members/{people['off'].pk}/").status_code == 404


def test_a_sysadmin_sets_what_another_account_may_do(people):
    c, mem = _as(people["sys"]), people["mem"]
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
            "groups": [Group.objects.get(name="officer").pk],
            "under_18": "",
        },
    )
    mem.refresh_from_db()
    assert (mem.in_group("officer"), mem.club_position, mem.callsign) == (
        True,
        "president",
        "N0MEM",
    )
    assert mem.may("manage_events") and not mem.may("approve_agreements")


def test_nobody_takes_away_their_own_ability_to_decide_who_may_do_what(people):
    """A sysadmin keeps every capability whatever group they are in, so their own edit is
    harmless. Anyone else the club has trusted with it can lock everyone out in one save."""
    from django.contrib.auth.models import Permission

    from apps.ops.capabilities import APP_LABEL

    trusted = Group.objects.create(name="trusted")
    trusted.permissions.set(
        Permission.objects.filter(
            content_type__app_label=APP_LABEL,
            codename__in=["assign_groups", "view_member_records", "edit_member_privileges"],
        )
    )
    keeper = User.objects.create_user(
        "keeper@example.org",
        "pw-Testing-123",
        first_name="Kee",
        last_name="Per",
        groups=["trusted"],
    )
    fields = {
        "action": "save",
        "first_name": "Kee",
        "middle_name": "",
        "last_name": "Per",
        "callsign": "",
        "category": "",
        "club_position": "",
        "under_18": "",
    }
    c = _as(keeper)
    r = c.post(
        f"/members/{keeper.pk}/",
        {**fields, "groups": [Group.objects.get(name="member").pk]},
    )
    keeper.refresh_from_db()
    assert keeper.in_group("trusted") and b"your own ability" in r.content

    # a sysadmin may do it to them, because a sysadmin still holds it
    c = _as(people["sys"])
    c.post(
        f"/members/{keeper.pk}/",
        {**fields, "groups": [Group.objects.get(name="member").pk]},
    )
    keeper.refresh_from_db()
    assert not keeper.in_group("trusted")


def test_officer_sets_club_position_only(people):
    c, mem = _as(people["off"]), people["mem"]
    body = c.get(f"/members/{mem.pk}/").content.decode()
    assert 'name="club_position"' in body and 'name="groups"' not in body
    assert "temporary password" not in body.lower()
    c.post(f"/members/{mem.pk}/", {"action": "save", "club_position": "president"})
    mem.refresh_from_db()
    assert mem.club_position == "president"
    # A forged privilege change is ignored: the field is not on an officer's form.
    c.post(
        f"/members/{mem.pk}/",
        {"action": "save", "club_position": "", "groups": [Group.objects.get(name="member").pk]},
    )
    mem.refresh_from_db()
    assert mem.in_group("member")
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
    assert not mem.has_access
    c.post(f"/members/{mem.pk}/", {"action": "reopen"})
    mem.refresh_from_db()
    assert mem.in_group("member")


def test_a_second_invitation_withdraws_the_first(people):
    """Nobody holds two live links to the same account.

    The advisor pressed Create invitation three more times while testing on 2026-09-19 and
    ended with four working links and six invitation emails in one inbox; revoking any one of
    them withdrew nothing.
    """
    c = _as(people["off"])
    for _ in range(3):
        c.post("/me/invitations/", {"email": "new@uni.example", "category": "student"})

    live = Invitation.objects.filter(email="new@uni.example", state="created")
    assert live.count() == 1, "only the newest invitation may still work"
    assert Invitation.objects.filter(email="new@uni.example", state="revoked").count() == 2

    # the two that were replaced are refused, and the survivor opens the form
    for dead in Invitation.objects.filter(email="new@uni.example", state="revoked"):
        assert Client().get(f"/me/invite/{dead.token}/").status_code == 410
    assert Client().get(f"/me/invite/{live.get().token}/").status_code == 200


def test_the_page_says_when_it_withdrew_an_earlier_invitation(people):
    c = _as(people["off"])
    c.post("/me/invitations/", {"email": "twice@uni.example", "category": "student"})
    body = c.post(
        "/me/invitations/", {"email": "twice@uni.example", "category": "student"}, follow=True
    ).content.decode()
    assert "1 earlier invitation to that address was withdrawn" in body


def test_an_invitation_to_somebody_else_is_left_alone(people):
    """Superseding matches on the address, not on the act of inviting."""
    c = _as(people["off"])
    c.post("/me/invitations/", {"email": "first@uni.example", "category": "student"})
    c.post("/me/invitations/", {"email": "second@uni.example", "category": "student"})
    assert Invitation.objects.filter(state="created").count() == 2


def test_a_minor_without_an_address_is_matched_by_their_guardian(people):
    """A minor may hold no address of their own, so the guardian's is what identifies them."""
    c = _as(people["off"])
    for _ in range(2):
        c.post(
            "/me/invitations/",
            {
                "email": "",
                "category": "student",
                "is_minor": "on",
                "guardian_email": "parent@uni.example",
            },
        )
    assert (
        Invitation.objects.filter(guardian_email="parent@uni.example", state="created").count() == 1
    )
    assert (
        Invitation.objects.filter(guardian_email="parent@uni.example", state="revoked").count() == 1
    )


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
    for label in ("Mobile number", "Graduation year", "Category", "Access"):
        assert label in body
    assert "Sign-in email" not in body  # every confirmed address signs in; none of them is special
    data = {
        "action": "save",
        "first_name": m.first_name,
        "last_name": m.last_name,
        "category": m.category,
        "groups": [g.pk for g in m.groups.all()],
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
            "groups": [g.pk for g in m.groups.all()],
            "email": m.email,
            "student_level": "undergraduate",
            "graduation_year": "2028",
        },
    )
    m.refresh_from_db()
    assert m.category == "faculty" and m.student_level == "" and m.graduation_year is None
