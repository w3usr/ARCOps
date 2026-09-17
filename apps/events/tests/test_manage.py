"""Creating and running an event from the manage page (§2.2, FR-42, FR-46, FR-47, FR-52)."""

import pytest
from django.test import Client

from apps.accounts.models import User
from apps.events.models import Captaincy, Event, Slot
from apps.ops.models import ClubSetting

pytestmark = pytest.mark.django_db


@pytest.fixture
def officer():
    ClubSetting.objects.update_or_create(
        key="slot_roles",
        defaults={
            "value": [
                {"key": "operator", "label": "Operator", "on_air": True},
                {"key": "mentor", "label": "Mentor", "on_air": True},
            ]
        },
    )
    return User.objects.create_user(
        "off@example.org",
        "pw-Testing-123",
        groups=["officer"],
        first_name="Ann",
        last_name="O",
    )


def _as(user, view="sysadmin"):
    c = Client()
    c.force_login(user)
    if user.is_superuser:
        session = c.session  # the level a sysadmin's session acts at
        session["acting_view"] = view
        session.save()
    return c


def _build(c):
    c.post(
        "/events/new/",
        {
            "title": "Field Day",
            "type": "contest",
            "description_html": "",
            "rules_url": "",
            "min_license_class": "",
            "kbyg_html": "",
            "start": "2026-06-27T18:00",
            "end": "2026-06-28T18:00",
        },
    )
    ev = Event.objects.get(title="Field Day")
    c.post(
        f"/events/{ev.pk}/locations/add/",
        {"name": "Club station", "position": "Run", "is_club_station": "on"},
    )
    loc = ev.locations.get()
    c.post(f"/events/{ev.pk}/locations/{loc.pk}/positions/add/", {"name": "Mult"})
    c.post(
        f"/events/{ev.pk}/slots/generate/",
        {
            "minutes": "60",
            "setup_slots": "1",
            "breakdown_slots": "1",
            "cap_operator": "2",
            "cap_mentor": "1",
        },
    )
    return ev


def test_officer_builds_an_event_end_to_end(officer):
    c = _as(officer)
    ev = _build(c)
    assert ev.state == "draft" and Captaincy.objects.filter(event=ev, user=officer).exists()
    slots = Slot.objects.filter(position__location__event=ev)
    assert slots.count() == 2 * (24 + 2)  # two positions, 24 operating hours, setup and breakdown
    assert slots.filter(kind="operating").first().capacities.count() == 2
    body = c.get(f"/events/{ev.pk}/").content.decode()
    assert "Manage</a>" in body and "48 operating hours" in body


def test_members_are_kept_out_and_captains_let_in(officer):
    c = _as(officer)
    ev = _build(c)
    mem = User.objects.create_user(
        "m@example.org",
        "pw-Testing-123",
        groups=["member"],
        first_name="Mo",
        last_name="M",
    )
    cm = _as(mem)
    assert cm.get(f"/events/{ev.pk}/manage/").status_code == 404
    assert cm.get("/events/new/").status_code == 404
    c.post(f"/events/{ev.pk}/captains/add/", {"user": mem.pk})
    assert cm.get(f"/events/{ev.pk}/manage/").status_code == 200
    c.post(f"/events/{ev.pk}/captains/{mem.pk}/remove/")
    assert cm.get(f"/events/{ev.pk}/manage/").status_code == 404


def test_slot_close_cancel_duplicate_and_cancel_event(officer):
    c = _as(officer)
    ev = _build(c)
    s = Slot.objects.filter(position__location__event=ev, kind="operating").first()
    c.post(f"/events/slot/{s.pk}/toggle/", {"what": "close"})
    s.refresh_from_db()
    assert s.closed
    c.post(f"/events/slot/{s.pk}/toggle/", {"what": "cancel"})
    s.refresh_from_db()
    assert s.cancelled
    c.post(f"/events/{ev.pk}/duplicate/")
    copy = Event.objects.get(title="Field Day (copy)")
    assert copy.state == "draft" and copy.duplicated_from == ev
    assert (
        Slot.objects.filter(position__location__event=copy).count() == 2 * 26 - 1
    )  # the cancelled one is not copied
    assert c.post(f"/events/{copy.pk}/cancel/", {}).status_code == 302
    copy.refresh_from_db()
    assert copy.state == "draft"  # without the confirmation tick nothing happens
    c.post(f"/events/{copy.pk}/cancel/", {"confirm": "yes"})
    copy.refresh_from_db()
    assert copy.state == "cancelled"


def test_grid_is_fixed_once_someone_has_signed_up(officer):
    from apps.events.models import SignUp

    c = _as(officer)
    ev = _build(c)
    s = Slot.objects.filter(position__location__event=ev, kind="operating").first()
    SignUp.objects.create(slot=s, user=officer, role="operator")
    before = Slot.objects.filter(position__location__event=ev).count()
    c.post(
        f"/events/{ev.pk}/slots/generate/",
        {
            "minutes": "30",
            "setup_slots": "0",
            "breakdown_slots": "0",
            "cap_operator": "1",
            "cap_mentor": "0",
        },
    )
    assert Slot.objects.filter(position__location__event=ev).count() == before
