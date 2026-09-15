"""Participation report (FR-86)."""

from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.accounts.models import AccessLevel, User
from apps.events.models import (
    Captaincy,
    Event,
    Location,
    OperatingPeriod,
    Position,
    RoleCapacity,
    SignUp,
    Slot,
)
from apps.events.services.participation import participation

pytestmark = pytest.mark.django_db


def test_participation_counts_hours_people_and_first_timers():
    cap = User.objects.create_user(
        "cap@example.org", "pw-Testing-123", first_name="Cap", last_name="T"
    )
    cap.access_level = AccessLevel.OFFICER
    cap.save()
    a = User.objects.create_user("a@example.org", "pw-Testing-123", first_name="A", last_name="One")
    b = User.objects.create_user("b@example.org", "pw-Testing-123", first_name="B", last_name="Two")
    for u in (a, b):
        u.access_level = AccessLevel.MEMBER
        u.save()
    start = timezone.now() - timedelta(days=2)
    e = Event.objects.create(title="Past Sprint", state=Event.State.COMPLETED)
    p1 = OperatingPeriod.objects.create(event=e, start=start, end=start + timedelta(hours=2))
    OperatingPeriod.objects.create(
        event=e, start=start + timedelta(hours=5), end=start + timedelta(hours=6)
    )
    loc = Location.objects.create(event=e, name="Station")
    pos = Position.objects.create(location=loc, name="Run")
    Captaincy.objects.create(event=e, user=cap)
    slots = [
        Slot.objects.create(
            position=pos, start=start + timedelta(hours=h), end=start + timedelta(hours=h + 1)
        )
        for h in (0, 1, 5)
    ]
    for s in slots:
        RoleCapacity.objects.create(slot=s, role="observer", capacity=2)
    SignUp.objects.create(slot=slots[0], user=a, role="observer", checked_in_at=start)
    SignUp.objects.create(slot=slots[0], user=b, role="observer")
    SignUp.objects.create(slot=slots[2], user=a, role="observer", checked_in_at=start, no_show=True)
    # an earlier event where b checked in, so b is not a first-timer even if b checks in here
    old = Event.objects.create(title="Old", state=Event.State.COMPLETED)
    oloc = Location.objects.create(event=old, name="S")
    opos = Position.objects.create(location=oloc, name="R")
    os_ = Slot.objects.create(
        position=opos,
        start=start - timedelta(days=30),
        end=start - timedelta(days=30) + timedelta(hours=1),
    )
    SignUp.objects.create(
        slot=os_, user=b, role="observer", checked_in_at=start - timedelta(days=30)
    )
    r = participation(e)
    t = r["total"]
    assert t["slots"] == 3 and t["hours_scheduled"] == 3.0 and t["hours_covered"] == 2.0
    assert (
        t["people_scheduled"] == 2 and t["people_checked_in"] == 1
    )  # a's second check-in is a no-show
    assert (
        t["first_timers"] == 1 and r["periods"][0]["period"] == p1 and r["periods"][0]["slots"] == 2
    )
    c = Client()
    c.force_login(cap)
    body = c.get(f"/events/{e.pk}/participation/").content.decode()
    assert "Participation: Past Sprint" in body and "first time" in body
    csv_body = c.get(f"/events/{e.pk}/participation/?format=csv").content.decode()
    assert "first_time_participants,1" in csv_body
    c.force_login(a)
    assert c.get(f"/events/{e.pk}/participation/").status_code == 404
