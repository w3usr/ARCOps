"""Creating and running an event from the manage page (§2.2, FR-42, FR-46, FR-47, FR-52)."""

from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.accounts.models import User
from apps.events.models import Captaincy, Event, OperatingPeriod, Slot
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


def test_only_an_officer_appoints_or_removes_captains(officer):
    """§2.2: a member made captain runs the event but cannot change who else does
    (found in acceptance test T11, 2026-10-14)."""
    c = _as(officer)
    ev = _build(c)
    mem, other = (
        User.objects.create_user(
            f"{n}@example.org", "pw-Testing-123", groups=["member"], first_name=n, last_name="M"
        )
        for n in ("Mo", "Cy")
    )
    c.post(f"/events/{ev.pk}/captains/add/", {"user": mem.pk})
    cm = _as(mem)
    body = cm.get(f"/events/{ev.pk}/manage/").content.decode()
    assert "Appoint captain" not in body and "An officer appoints and removes captains." in body
    assert cm.post(f"/events/{ev.pk}/captains/add/", {"user": other.pk}).status_code == 404
    assert cm.post(f"/events/{ev.pk}/captains/{officer.pk}/remove/").status_code == 404
    assert set(ev.captaincies.values_list("user", flat=True)) == {officer.pk, mem.pk}
    # Nor can they cancel the event: only an officer can (SK, 2026-10-15).
    assert "Cancel this event" not in body and "An officer can cancel this event." in body
    r = cm.post(f"/events/{ev.pk}/cancel/", {"confirm": "yes", "reason": "Rained out"})
    ev.refresh_from_db()
    assert r.status_code == 404 and ev.state == "draft"


def test_the_last_captain_cannot_be_removed(officer):
    c = _as(officer)
    ev = _build(c)
    c.post(f"/events/{ev.pk}/captains/{officer.pk}/remove/")
    assert ev.captaincies.filter(user=officer).exists()
    assert "Appoint captain" in c.get(f"/events/{ev.pk}/manage/").content.decode()


def test_the_event_form_says_preferred_license_class(officer):
    body = _as(officer).get("/events/new/").content.decode()
    assert "Preferred license class" in body and "Min license class" not in body


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
    )  # the canceled one is not copied
    assert c.post(f"/events/{copy.pk}/cancel/", {}).status_code == 302
    copy.refresh_from_db()
    assert copy.state == "draft"  # without the confirmation tick nothing happens
    c.post(f"/events/{copy.pk}/cancel/", {"confirm": "yes", "reason": " "})
    copy.refresh_from_db()
    assert copy.state == "draft"  # nor without a reason (the form's `required` can be stripped)
    c.post(f"/events/{copy.pk}/cancel/", {"confirm": "yes", "reason": "Rained out"})
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


def test_a_slot_is_added_by_hand_after_sign_ups_with_its_own_seats(officer):
    """FR-46: slots added by hand afterwards, people or no people; FR-49: their seats set as they
    are made. Beta users, 2026-10-26: "add a way to add more slots after generating"."""
    from apps.events.models import SignUp
    from apps.ops.models import AuditLog

    ClubSetting.objects.update_or_create(
        key="non_operating_slot_kinds",
        defaults={"value": [{"key": "training", "label": "Training"}]},
    )
    c = _as(officer)
    ev = _build(c)
    run = ev.locations.get().positions.get(name="Run")
    signed = Slot.objects.filter(position=run, kind="operating").first()
    SignUp.objects.create(slot=signed, user=officer, role="operator")
    before = Slot.objects.filter(position__location__event=ev).count()

    def add(start, minutes="60", kind="operating", **seats):
        form = {"position": run.pk, "start": start, "minutes": minutes, "kind": kind}
        form |= {"cap_operator": "1", "cap_mentor": "0"} | seats
        return c.post(f"/events/{ev.pk}/slots/add/", form)

    # Refused, and the reason is beside the field: a clash, and an operating slot outside every
    # operating period.
    assert "already has a slot from Sat 27 Jun 20:00" in add("2026-06-27T20:30").content.decode()
    assert "inside an operating period" in add("2026-06-29T10:00").content.decode()
    assert Slot.objects.filter(position__location__event=ev).count() == before

    # A training slot after the contest, with three operators' seats.
    r = add("2026-06-29T10:00", minutes="120", kind="training", cap_operator="3")
    assert r.status_code == 302 and r["Location"] == f"/events/{ev.pk}/manage/"
    slot = Slot.objects.get(position=run, kind="training")
    assert (slot.end - slot.start) == timedelta(hours=2)
    assert {c.role: c.capacity for c in slot.capacities.all()} == {"operator": 3}
    assert AuditLog.objects.get(action="slot.added").after["seats"] == {"operator": 3}
    assert Slot.objects.filter(position__location__event=ev).count() == before + 1
    assert signed.signups.count() == 1, "nothing else on the grid changes"

    # Re-timing an empty slot: cancel it, and its time is free to add again.
    empty = Slot.objects.get(position=run, start__hour=20, kind="operating")
    c.post(f"/events/slot/{empty.pk}/toggle/", {"what": "cancel"})
    assert add("2026-06-27T20:30", minutes="30").status_code == 302

    member = User.objects.create_user("mem@example.org", "pw-Testing-123", groups=["member"])
    assert _as(member).post(f"/events/{ev.pk}/slots/add/", {}).status_code == 404


def test_a_canceled_upcoming_event_is_tagged_in_the_house_spelling(officer):
    """Found in acceptance test T18 (2026-10-16): the Events list tagged an upcoming canceled
    event "Cancelled", from the state's label, beside a "Canceled." banner."""
    ev = Event.objects.create(title="Sprint", state=Event.State.CANCELLED, created_by=officer)
    start = timezone.now() + timedelta(days=10)
    OperatingPeriod.objects.create(event=ev, start=start, end=start + timedelta(hours=4))
    body = _as(officer).get("/events/").content.decode()
    assert '<span class="tag">Canceled</span>' in body and "Cancelled" not in body
