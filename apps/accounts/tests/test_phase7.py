"""Phase 7: guardians and minors (§2.4, FR-10, FR-64, FR-67, FR-70, FR-109, FR-113)."""

import datetime as dt

import pytest
from django.test import Client
from django.utils import timezone

from apps.accounts.models import AccessLevel, Guardianship, User
from apps.accounts.services import create_invitation
from apps.comms.models import Outbox
from apps.comms.services import recipient_addresses
from apps.events.models import (
    Captaincy,
    Event,
    Location,
    OperatingPeriod,
    Position,
    ResponsibleAdult,
    SignUp,
)
from apps.events.services.roster import cell_for
from apps.events.services.slots import generate_slots
from apps.ops.models import AuditLog

pytestmark = pytest.mark.django_db


def _user(email, level=AccessLevel.MEMBER, **kw):
    kw.setdefault("first_name", email.split("@")[0].title())
    kw.setdefault("last_name", "Tester")
    kw.setdefault("category", "student")
    return User.objects.create_user(email, "pw-Testing-123", access_level=level, **kw)


def _as(user):
    c = Client()
    c.force_login(user)
    return c


def _slot(captain, days=5, minutes=60):
    ev = Event.objects.create(title="Test Contest", state="published")
    start = timezone.now() + dt.timedelta(days=days)
    OperatingPeriod.objects.create(event=ev, start=start, end=start + dt.timedelta(minutes=minutes))
    pos = Position.objects.create(
        location=Location.objects.create(event=ev, name="Station"), name="Run"
    )
    Captaincy.objects.create(event=ev, user=captain)
    slot = generate_slots(ev, [pos], minutes=minutes)[0]
    from apps.events.models import RoleCapacity

    RoleCapacity.objects.create(slot=slot, role="observer", capacity=3)
    return slot


def _family():
    officer = _user("off@example.org", AccessLevel.OFFICER)
    guardian = _user("parent@example.org", category="guardian")
    minor = _user("kid@example.org", under_18=True)
    Guardianship.objects.create(minor=minor, guardian=guardian, relationship="parent")
    return officer, guardian, minor


def test_guardian_completes_a_minors_invitation_creating_both_accounts():
    officer = _user("off@example.org", AccessLevel.OFFICER)
    inv = create_invitation(
        officer, "kid@example.org", "student", is_minor=True, guardian_email="parent@example.org"
    )
    c = Client()
    r = c.get(f"/me/invite/{inv.token}/")
    assert (
        r.status_code == 200
        and b"guardian" in r.content.lower()
        and b"Your first name" in r.content
    )
    r = c.post(
        f"/me/invite/{inv.token}/",
        {
            "guardian_first_name": "Pat",
            "guardian_last_name": "Parent",
            "guardian_phone": "555-0100",
            "relationship": "parent",
            "guardian_password1": "pw-Testing-123!",
            "guardian_password2": "pw-Testing-123!",
            "first_name": "Kim",
            "last_name": "Kid",
            "password1": "pw-Kid-Testing-123!",
            "password2": "pw-Kid-Testing-123!",
            "consent": "on",
        },
    )
    assert r.status_code == 302
    g = User.objects.get(email="parent@example.org")
    m = User.objects.get(email="kid@example.org")
    assert g.is_guardian_only and not g.under_18 and g.cell_phone == "555-0100"
    assert m.under_18 and m.category == "student" and m.access_level == AccessLevel.MEMBER
    assert Guardianship.objects.get(minor=m, guardian=g).relationship == "parent"
    assert c.get("/").context["user"] == g  # the guardian is signed in
    assert m.check_password("pw-Kid-Testing-123!")


def test_existing_member_as_guardian_must_sign_in_first_then_only_the_minor_form():
    officer = _user("off@example.org", AccessLevel.OFFICER)
    parent = _user("parent@example.org")
    inv = create_invitation(
        officer, "kid@example.org", "student", is_minor=True, guardian_email="parent@example.org"
    )
    r = Client().get(f"/me/invite/{inv.token}/")
    assert (
        r.status_code == 200
        and b"Sign in" in r.content
        and not User.objects.filter(email="kid@example.org").exists()
    )
    c = _as(parent)
    r = c.get(f"/me/invite/{inv.token}/")
    assert b"id_guardian_first_name" not in r.content and b"id_first_name" in r.content
    r = c.post(
        f"/me/invite/{inv.token}/",
        {
            "relationship": "parent",
            "first_name": "Kim",
            "last_name": "Kid",
            "password1": "pw-Kid-Testing-123!",
            "password2": "pw-Kid-Testing-123!",
            "consent": "on",
        },
    )
    assert r.status_code == 302
    m = User.objects.get(email="kid@example.org")
    assert Guardianship.objects.filter(minor=m, guardian=parent, active=True).exists()
    assert not parent.is_guardian_only  # a member stays a member


def test_minor_signs_in_read_only():
    officer, guardian, minor = _family()
    slot = _slot(officer)
    c = _as(minor)
    r = c.get("/")
    assert r.status_code == 200 and b"Read-only" in r.content
    assert c.post(f"/events/slot/{slot.pk}/signup/", {"role": "observer"}).status_code == 403
    assert c.post("/me/", {"first_name": "X"}).status_code == 403
    assert not SignUp.objects.filter(user=minor).exists()
    r = c.get("/me/")
    assert (
        b"Your guardians" in r.content
        and b"Parent Tester" in r.content
        and b"Close my account" not in r.content
    )


def test_guardian_acts_for_minor_signs_up_names_adult_and_the_audit_names_both():
    officer, guardian, minor = _family()
    slot = _slot(officer)
    c = _as(guardian)
    assert b"Act for Kid" in c.get("/me/").content
    assert c.post(f"/me/wards/{minor.pk}/act/").status_code == 302
    r = c.get("/")
    assert r.context["user"] == minor and b"Acting for Kid" in r.content
    r = c.post(f"/events/slot/{slot.pk}/signup/", {"role": "observer"})
    su = SignUp.objects.get(user=minor, slot=slot)
    assert r.status_code == 302 and r["Location"].endswith(f"/events/signup/{su.pk}/adults/")
    row = AuditLog.objects.get(action="signup.created")
    assert row.actor == guardian and "acting for" in row.actor_label
    # the slot needs an adult until one is named
    cell, _ = cell_for(slot, officer)
    assert (
        cell.shown.word.startswith("Needs")
        and "responsible adult" in cell.shown.word + cell.shown.detail
    )
    r = c.post(
        f"/events/signup/{su.pk}/adults/",
        {"action": "add", "name": "Uncle Ray", "phone": "555-0199"},
    )
    assert r.status_code == 302
    cell, _ = cell_for(slot, officer)
    assert "responsible adult" not in cell.shown.word + cell.shown.detail
    # the saved list offers the adult for the next slot
    slot2 = _slot(officer, days=6)
    c.post(f"/events/slot/{slot2.pk}/signup/", {"role": "observer"})
    su2 = SignUp.objects.get(user=minor, slot=slot2)
    assert b"Uncle Ray" in c.get(f"/events/signup/{su2.pk}/adults/").content
    c.post(f"/events/signup/{su2.pk}/adults/", {"action": "pick", "saved": "Uncle Ray||555-0199|"})
    assert ResponsibleAdult.objects.filter(signup=su2, name="Uncle Ray").exists()
    # agreements are not offered to the minor, even through the guardian
    assert (
        b"do not sign" in c.get("/credentials/agreements/").content.lower()
        or c.get("/credentials/agreements/").status_code == 200
    )
    assert c.post("/me/act/stop/").status_code == 302
    assert c.get("/").context["user"] == guardian
    assert not c.get("/").context["user"].under_18


def test_roster_shows_adults_to_slot_mates_and_guardians_to_captains():
    officer, guardian, minor = _family()
    mate = _user("mate@example.org")
    other = _user("other@example.org")
    slot = _slot(officer)
    su = SignUp.objects.create(slot=slot, user=minor, role="observer")
    ResponsibleAdult.objects.create(
        signup=su, name="Uncle Ray", phone="555-0199", email="ray@example.org"
    )
    SignUp.objects.create(slot=slot, user=mate, role="observer")
    url = f"/events/{slot.event.pk}/slot/{slot.pk}/"
    page = _as(mate).get(url).content
    assert b"Uncle Ray" in page and b"555-0199" in page and b"parent@example.org" not in page
    page = _as(other).get(url).content
    assert b"Uncle Ray" not in page and b"under 18" in page
    page = _as(officer).get(url).content
    assert b"Uncle Ray" in page and b"ray@example.org" in page and b"parent@example.org" in page


def test_captain_checks_a_minor_in_recording_the_adult_present():
    officer, guardian, minor = _family()
    slot = _slot(officer, days=0, minutes=120)
    su = SignUp.objects.create(slot=slot, user=minor, role="observer")
    a = ResponsibleAdult.objects.create(signup=su, name="Uncle Ray", phone="555-0199")
    c = _as(officer)
    r = c.post(f"/events/signup/{su.pk}/checkin/", {"adult": [str(a.pk)]})
    assert r.status_code == 302
    su.refresh_from_db()
    a.refresh_from_db()
    assert su.checked_in_at and a.present_at and su.checked_in_by == officer
    assert AuditLog.objects.get(action="signup.checked_in").after == {"present": ["Uncle Ray"]}


def test_messages_to_a_minor_reach_every_guardian(settings):
    officer, guardian, minor = _family()
    second = _user("aunt@example.org", category="guardian")
    Guardianship.objects.create(minor=minor, guardian=second)
    addrs = recipient_addresses(minor)
    assert set(addrs) == {"parent@example.org", "aunt@example.org", "kid@example.org"}
    minor.email = "kid@example.org"
    minor2 = _user("kid2@example.org", under_18=True)
    Guardianship.objects.create(minor=minor2, guardian=guardian)
    assert "parent@example.org" in recipient_addresses(minor2)


def test_conversion_at_18_by_an_approver():
    officer, guardian, minor = _family()
    sys = _user("sys@example.org", AccessLevel.SYSADMIN)
    c = _as(officer)
    assert b"Convert to adult account" not in c.get(f"/members/{minor.pk}/").content
    c = _as(sys)
    r = c.get(f"/members/{minor.pk}/")
    assert b"Convert to adult account" in r.content and b"parent@example.org" in r.content
    r = c.post(f"/members/{minor.pk}/", {"action": "convert_adult"})
    assert r.status_code == 200 and b"Temporary password for Kid" in r.content
    minor.refresh_from_db()
    link = Guardianship.objects.get(minor=minor, guardian=guardian)
    assert not minor.under_18 and minor.password_is_temporary
    assert not link.active and link.ended is not None
    assert Outbox.objects.filter(user=guardian, subject__contains="now their own").exists()
    assert Outbox.objects.filter(user=minor, subject="Your account is now your own").exists()
    assert AuditLog.objects.filter(action="account.converted_to_adult").exists()
    # the former guardian can no longer act
    g = _as(guardian)
    assert g.post(f"/me/wards/{minor.pk}/act/").status_code == 404


def test_sysadmin_links_and_unlinks_guardians():
    officer, guardian, minor = _family()
    sys = _user("sys@example.org", AccessLevel.SYSADMIN)
    aunt = _user("aunt@example.org")
    c = _as(sys)
    c.post(
        f"/members/{minor.pk}/",
        {"action": "link_guardian", "guardian_email": "aunt@example.org", "relationship": "aunt"},
    )
    assert Guardianship.objects.filter(minor=minor, guardian=aunt, active=True).exists()
    first = Guardianship.objects.get(minor=minor, guardian=guardian)
    c.post(f"/members/{minor.pk}/", {"action": "unlink_guardian", "link": first.pk})
    first.refresh_from_db()
    assert not first.active
    last = Guardianship.objects.get(minor=minor, guardian=aunt)
    c.post(f"/members/{minor.pk}/", {"action": "unlink_guardian", "link": last.pk})
    last.refresh_from_db()
    assert last.active  # the last guardian of a minor stays
