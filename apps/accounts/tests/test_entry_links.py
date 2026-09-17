"""Entry links (FR-119, FR-120), the Provisional level and its review (FR-121), the mentor-needs
page (FR-123). Test plan T23 to T25."""

from datetime import UTC, datetime, timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.accounts import entry
from apps.accounts.models import EntryLink, User
from apps.comms.models import Outbox
from apps.events.models import Event, Location, OperatingPeriod, Position, RoleCapacity
from apps.events.services.slots import generate_slots
from apps.ops.models import ClubSetting

pytestmark = pytest.mark.django_db

FORM = {
    "callsign": "",
    "first_name": "New",
    "middle_name": "",
    "last_name": "Person",
    "preferred_name": "",
    "cell_phone": "",
    "password1": "a-Long-Password-77!",
    "password2": "a-Long-Password-77!",
    "consent": "on",
}


@pytest.fixture
def world():
    ClubSetting.objects.update_or_create(
        key="trusted_email_domains", defaults={"value": ["uni.example"]}
    )
    ClubSetting.objects.update_or_create(
        key="club.timezone", defaults={"value": "America/New_York"}
    )
    ClubSetting.objects.update_or_create(
        key="member_categories",
        defaults={
            "value": [
                {"key": "student", "label": "Student", "email_domain": "uni.example"},
                {"key": "faculty", "label": "Faculty"},
                {"key": "community", "label": "Community Member"},
            ]
        },
    )
    ClubSetting.objects.update_or_create(
        key="slot_roles",
        defaults={
            "value": [
                {"key": "operator", "label": "Operator", "on_air": True},
                {"key": "mentor", "label": "Mentor", "on_air": True, "requires_license": True},
            ]
        },
    )
    off = User.objects.create_user(
        "off@uni.example",
        "pw-Testing-123",
        groups=["officer"],
        first_name="Ann",
        last_name="Officer",
    )
    ev = Event.objects.create(
        title="RTTY", state=Event.State.PUBLISHED, created_by=off, min_license_class="General"
    )
    start = datetime(2027, 9, 25, 0, 0, tzinfo=UTC)
    OperatingPeriod.objects.create(event=ev, start=start, end=start + timedelta(hours=3))
    loc = Location.objects.create(event=ev, name="Station, Room 596")
    pos = Position.objects.create(location=loc, name="Run")
    for s in generate_slots(ev, [pos], minutes=60):
        RoleCapacity.objects.create(slot=s, role="operator", capacity=2)
        RoleCapacity.objects.create(slot=s, role="mentor", capacity=1)
    return {"off": off, "ev": ev}


def _as(u, view="sysadmin"):
    c = Client()
    c.force_login(u)
    if u.is_superuser:
        session = c.session  # the level a sysadmin's session acts at
        session["acting_view"] = view
        session.save()
    return c


def _link(off, kind, **kw):
    return entry.create_link(
        off,
        label=kw.pop("label", "TEST 101"),
        kind=kind,
        expires_at=timezone.now() + timedelta(days=30),
        **kw,
    )


def test_officer_creates_links_and_the_page_lists_them(world):
    c = _as(world["off"])
    r = c.post(
        "/me/entry-links/",
        {
            "label": "PHYS 101 Fall",
            "kind": "class",
            "required_domain": "uni.example",
            "expires_at": "2030-01-01",
            "cap": "5",
            "landing_event": world["ev"].pk,
        },
    )
    link = EntryLink.objects.get(label="PHYS 101 Fall")
    body = r.content.decode()
    assert (
        f"/join/{link.token}/" in body and link.required_domain == "uni.example" and link.cap == 5
    )
    r = c.post(
        "/me/entry-links/",
        {"label": "No domain", "kind": "class", "required_domain": "", "expires_at": "2030-01-01"},
    )
    assert "needs a trusted domain" in r.content.decode()
    assert (
        _as(User.objects.create_user("m@x.example", "pw-Testing-123", groups=["member"]))
        .get("/me/entry-links/")
        .status_code
        == 404
    )


def test_class_link_admits_at_once_with_a_verification_deadline(world):
    link = _link(world["off"], "class", required_domain="uni.example", landing_event=world["ev"])
    c = Client()
    r = c.post(
        f"/join/{link.token}/form/", {**FORM, "email": "kid@home.example", "category": "student"}
    )
    assert (
        "is for uni.example addresses" in r.content.decode()
        and not User.objects.by_address("kid@home.example").exists()
    )
    r = c.post(
        f"/join/{link.token}/form/", {**FORM, "email": "kid@uni.example", "category": "student"}
    )
    assert r.status_code == 302 and r["Location"] == f"/events/{world['ev'].pk}/"
    u = User.objects.by_address("kid@uni.example").get()
    assert (
        u.in_group("member")
        and u.joined_via == link
        and u.addresses.get(address="kid@uni.example").kind == "institution"
    )
    assert u.verification_deadline and not u.has_confirmed_address
    assert Outbox.objects.filter(user=u, subject__startswith="Confirm your address").exists()
    # Signed in already; the roster works; the sign-in address is verified by the token.
    assert c.get(f"/events/{world['ev'].pk}/").status_code == 200
    token = entry.verification_token(u)
    assert c.get(f"/verify/{token}/").status_code == 200
    u.refresh_from_db()
    assert u.has_confirmed_address


def test_overdue_verification_pauses_sign_in_until_an_officer_waives_it(world):
    link = _link(world["off"], "class", required_domain="uni.example")
    c = Client()
    c.post(
        f"/join/{link.token}/form/", {**FORM, "email": "late@uni.example", "category": "student"}
    )
    u = User.objects.by_address("late@uni.example").get()
    u.verification_deadline = timezone.now() - timedelta(hours=1)
    u.save()
    r = c.get("/events/")
    assert r.status_code == 302 and "/accounts/login/" in r["Location"]
    _as(world["off"]).post(f"/members/{u.pk}/", {"action": "mark_verified"})
    u.refresh_from_db()
    assert u.has_confirmed_address and not u.verification_overdue
    c2 = _as(u)
    assert c2.get("/events/").status_code == 200
    # and the whole-link waiver
    c.post(
        f"/join/{link.token}/form/", {**FORM, "email": "late2@uni.example", "category": "student"}
    )
    _as(world["off"]).post(f"/me/entry-links/{link.pk}/", {"action": "verify_all"})
    assert User.objects.by_address("late2@uni.example").get().has_confirmed_address


def test_closed_links_admit_nobody(world):
    link = _link(world["off"], "class", required_domain="uni.example", cap=1)
    c = Client()
    c.post(f"/join/{link.token}/form/", {**FORM, "email": "one@uni.example", "category": "student"})
    assert Client().get(f"/join/{link.token}/form/").status_code == 410  # cap reached
    link2 = _link(world["off"], "community", label="FRC")
    _as(world["off"]).post(f"/me/entry-links/{link2.pk}/", {"action": "pause"})
    assert "paused" in Client().get(f"/join/{link2.token}/").content.decode()
    _as(world["off"]).post(f"/me/entry-links/{link2.pk}/", {"action": "revoke"})
    assert Client().get(f"/mentors/{link2.token}/").status_code == 410


def test_community_link_makes_a_provisional_member_after_verification_and_officers_hear(world):
    link = _link(world["off"], "community", label="FRC 2026")
    c = Client()
    assert c.get(f"/join/{link.token}/")["Location"] == f"/mentors/{link.token}/"
    page = c.get(f"/mentors/{link.token}/").content.decode()
    assert "Mentors wanted" in page and "RTTY" in page and "mentor seat" in page
    assert "Room 596" not in page and "Ann" not in page  # no room, no names for outsiders
    r = c.post(f"/join/{link.token}/form/", {**FORM, "email": "ham@gmail.example"})
    assert "Check your email" in r.content.decode()
    u = User.objects.by_address("ham@gmail.example").get()
    assert not u.is_active and not u.has_access and u.category == "community"
    assert Client().login(email="ham@gmail.example", password=FORM["password1"]) is False
    r = c.get(f"/verify/{entry.verification_token(u)}/")
    assert "provisional" in r.content.decode().lower()
    u.refresh_from_db()
    assert u.is_active and u.in_group("provisional") and u.has_confirmed_address
    assert Outbox.objects.filter(
        user=world["off"], subject__startswith="New provisional member"
    ).exists()
    # Officer's Home lists them; the member page offers admit and decline.
    body = _as(world["off"]).get("/").content.decode()
    assert "waiting for review" in body and "New Person" in body


def test_provisional_sees_counts_not_names_and_no_directory_or_agreements(world):
    link = _link(world["off"], "community", label="FRC 2026")
    prov = User.objects.create_user(
        "p@gmail.example",
        "pw-Testing-123",
        groups=["provisional"],
        first_name="Pat",
        last_name="Prov",
        joined_via=link,
    )
    mem = User.objects.create_user(
        "s@uni.example",
        "pw-Testing-123",
        groups=["member"],
        first_name="Stu",
        last_name="Dent",
        callsign="N0STU",
    )
    from apps.events.models import SignUp, Slot

    slot = Slot.objects.filter(position__location__event=world["ev"]).first()
    SignUp.objects.create(slot=slot, user=mem, role="operator")
    c = _as(prov)
    body = c.get(f"/events/{world['ev'].pk}/").content.decode()
    assert "Stu" not in body and "N0STU" not in body and "1 U" in body
    assert (
        c.get("/members/").status_code == 404
        and c.get("/credentials/agreements/").status_code == 404
    )
    assert ">Members<" not in body and ">Agreements<" not in body
    # once admitted, names appear
    _as(world["off"]).post(f"/members/{prov.pk}/", {"action": "admit"})
    prov.refresh_from_db()
    assert prov.in_group("member")
    body = _as(prov).get(f"/events/{world['ev'].pk}/").content.decode()
    assert "Stu N0STU (U)" in body
    assert Outbox.objects.filter(user=prov, subject__startswith="Welcome").exists()


def test_decline_sets_no_access_with_a_reason(world):
    prov = User.objects.create_user(
        "q@gmail.example",
        "pw-Testing-123",
        groups=["provisional"],
        first_name="Q",
        last_name="R",
    )
    _as(world["off"]).post(
        f"/members/{prov.pk}/", {"action": "decline", "reason": "not this season"}
    )
    prov.refresh_from_db()
    assert not prov.has_access
    assert "not this season" in Outbox.objects.get(user=prov).body_html


def test_existing_address_gets_the_same_page_and_an_email(world):
    link = _link(world["off"], "class", required_domain="uni.example")
    r = Client().post(
        f"/join/{link.token}/form/", {**FORM, "email": "off@uni.example", "category": "student"}
    )
    assert "Check your email" in r.content.decode()
    assert Outbox.objects.filter(
        user=world["off"], body_html__contains="already has an account"
    ).exists()
