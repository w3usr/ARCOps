"""Audit tests for the event surface: eligibility, openings, roster visibility, publish."""

import datetime as dt

import pytest
from django.core.management import call_command
from django.test import Client
from django.utils import timezone

from apps.accounts.models import AccessLevel, User
from apps.events.models import (
    Captaincy,
    Event,
    Location,
    Opening,
    OperatingPeriod,
    Position,
    RoleCapacity,
    SignUp,
)
from apps.events.services.eligibility import can_sign_up
from apps.events.services.slots import generate_slots

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def club():
    call_command("club_import")


def user(name, **kw):
    kw.setdefault("access_level", AccessLevel.MEMBER)
    kw.setdefault("category", "student")
    return User.objects.create_user(
        f"{name}@example.org", "x", first_name=name, last_name="Tester", **kw
    )


def event_with_slot(state="published"):
    ev = Event.objects.create(title="Test Contest", state=state, min_license_class="General")
    start = timezone.now() + dt.timedelta(days=5)
    OperatingPeriod.objects.create(event=ev, start=start, end=start + dt.timedelta(hours=2))
    pos = Position.objects.create(
        location=Location.objects.create(event=ev, name="Station"), name="Run"
    )
    slot = generate_slots(ev, [pos], minutes=60)[0]
    for role, cap in (("operator", 1), ("mentor", 1), ("observer", 2)):
        RoleCapacity.objects.create(slot=slot, role=role, capacity=cap)
    return ev, slot


def test_opening_gates_by_category_and_time():
    ev, slot = event_with_slot()
    later = timezone.now() + dt.timedelta(days=1)
    Opening.objects.create(
        event=ev,
        role="operator",
        opens_at=timezone.now() - dt.timedelta(days=1),
        categories=["student"],
    )
    Opening.objects.create(event=ev, role="operator", opens_at=later, categories=[])
    ok, _ = can_sign_up(user("stu"), slot, "operator")
    assert ok
    ok, reason = can_sign_up(user("com", category="community"), slot, "operator")
    assert not ok and "opens to you on" in reason
    # No openings are defined for mentor, so the openings gate passes; the club's role default
    # (FR-122, 2026-09-15) then asks for a license, which this person lacks.
    ok, reason = can_sign_up(user("com2", category="community"), slot, "mentor")
    assert not ok and "license" in reason


def test_signup_view_enforces_capacity_and_eligibility():
    ev, slot = event_with_slot()
    a, b = user("a"), user("b")
    c = Client()
    c.force_login(a)
    r = c.post(f"/events/slot/{slot.pk}/signup/", {"role": "operator", "note": "running late"})
    assert (
        r.status_code == 302
        and SignUp.objects.filter(slot=slot, user=a, role="operator", note="running late").exists()
    )
    c2 = Client()
    c2.force_login(b)
    c2.post(f"/events/slot/{slot.pk}/signup/", {"role": "operator"})
    assert not SignUp.objects.filter(slot=slot, user=b).exists()  # capacity 1
    minor = user("kid", under_18=True)
    c3 = Client()
    c3.force_login(minor)
    c3.post(f"/events/slot/{slot.pk}/signup/", {"role": "observer"})
    assert not SignUp.objects.filter(user=minor).exists()


def test_roster_shows_short_names_to_members_and_full_names_to_captains():
    ev, slot = event_with_slot()
    op = user("Bartholomew", callsign="N0BAR")
    SignUp.objects.create(slot=slot, user=op, role="operator", note="secret note")
    member = Client()
    member.force_login(user("viewer"))
    body = member.get(f"/events/{ev.pk}/").content.decode()
    assert (
        "Bartholomew N0BAR" in body
        and "Bartholomew Tester" not in body
        and "secret note" not in body
    )
    cap = user("cap")
    Captaincy.objects.create(event=ev, user=cap)
    captain = Client()
    captain.force_login(cap)
    body = captain.get(f"/events/{ev.pk}/").content.decode()
    assert "Bartholomew Tester" in body and "secret note" in body


def test_draft_hidden_from_members_visible_to_captain_and_publish_rule():
    ev, slot = event_with_slot(state="draft")
    m = Client()
    m.force_login(user("m"))
    assert m.get(f"/events/{ev.pk}/").status_code == 404
    cap = user("cap")
    Captaincy.objects.create(event=ev, user=cap)
    c = Client()
    c.force_login(cap)
    assert c.get(f"/events/{ev.pk}/").status_code == 200
    c.post(f"/events/{ev.pk}/publish/")
    ev.refresh_from_db()
    assert ev.state == "published" and ev.published_by == cap
    SignUp.objects.create(slot=slot, user=user("x"), role="observer")
    c.post(f"/events/{ev.pk}/publish/")  # cannot unpublish with sign-ups
    ev.refresh_from_db()
    assert ev.state == "published"


def test_api_events_requires_login_and_lists_published():
    ev, _ = event_with_slot()
    assert Client().get("/api/v1/events").status_code in (401, 403)
    c = Client()
    c.force_login(user("api"))
    data = c.get("/api/v1/events").json()
    assert [e["title"] for e in data] == ["Test Contest"]
