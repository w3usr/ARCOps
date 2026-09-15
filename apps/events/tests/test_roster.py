"""The rebuilt roster (2026-09-13, second design round): day groups in two zones, grid or list,
status phrased as a need, the slot page and fragment, captain edits on a slot, bulk actions."""

from datetime import UTC, datetime, timedelta

import pytest
from django.test import Client

from apps.accounts.models import AccessLevel, User
from apps.events.models import (
    Event,
    Location,
    OperatingPeriod,
    Position,
    RoleCapacity,
    SignUp,
    Slot,
)
from apps.events.services.roster import build, present
from apps.events.services.slots import generate_slots
from apps.ops.models import ClubSetting

pytestmark = pytest.mark.django_db


@pytest.fixture
def world():
    ClubSetting.objects.update_or_create(
        key="club.timezone", defaults={"value": "America/New_York"}
    )
    ClubSetting.objects.update_or_create(
        key="slot_roles",
        defaults={
            "value": [
                {"key": "operator", "label": "Operator", "on_air": True},
                {"key": "observer", "label": "Observer", "on_air": False},
            ]
        },
    )
    off = User.objects.create_user(
        "off@example.org",
        "pw-Testing-123",
        access_level=AccessLevel.OFFICER,
        first_name="Ann",
        last_name="Officer",
    )
    mem = User.objects.create_user(
        "mem@example.org",
        "pw-Testing-123",
        access_level=AccessLevel.MEMBER,
        first_name="Mo",
        last_name="Member",
        callsign="N0MEM",
    )
    ev = Event.objects.create(title="RTTY", state=Event.State.PUBLISHED, created_by=off)
    start = datetime(2026, 9, 26, 0, 0, tzinfo=UTC)  # Friday 20:00 EDT
    OperatingPeriod.objects.create(event=ev, start=start, end=start + timedelta(hours=4))
    loc = Location.objects.create(event=ev, name="Club station")
    run = Position.objects.create(location=loc, name="Run", order=1)
    mult = Position.objects.create(location=loc, name="Mult", order=2)
    for s in generate_slots(ev, [run, mult], minutes=60, setup_slots=1):
        RoleCapacity.objects.create(slot=s, role="operator", capacity=1)
        RoleCapacity.objects.create(slot=s, role="observer", capacity=2)
    return {"off": off, "mem": mem, "ev": ev, "run": run, "mult": mult}


def _as(u):
    c = Client()
    c.force_login(u)
    return c


def test_grid_layout_days_in_local_zone_with_utc_beneath(world):
    data = build(world["ev"], world["mem"], "local")
    assert data["layout"] == "grid" and len(data["positions"]) == 2
    assert data["lead_label"] == "EDT" and data["other_label"] == "UTC"
    # 00:00Z Saturday is Friday evening locally: the setup slot and the first hours share Friday.
    assert data["days"][0].heading == "Friday 25 September"
    row = data["days"][0].rows[1]
    assert row.lead_range == "20:00–21:00 EDT" and row.other_range == "Sat 00:00–01:00 UTC"
    assert len(row.cells) == 2 and all(row.cells)
    utc = build(world["ev"], world["mem"], "utc")
    assert utc["days"][0].heading == "Friday 25 September"  # 23:00Z setup slot
    assert utc["days"][1].heading == "Saturday 26 September"


def test_status_is_phrased_as_a_need_never_a_verdict(world):
    ev = world["ev"]
    body = _as(world["mem"]).get(f"/events/{ev.pk}/").content.decode()
    assert "Open" in body and "not viable" not in body.lower() and "Not viable" not in body
    assert "open slot" in body  # the member summary, not the health card
    assert "Schedule health" not in body
    body = _as(world["off"]).get(f"/events/{ev.pk}/").content.decode()
    assert "Schedule health" in body and "open</span>" in body


def test_zone_toggle_is_remembered(world):
    c = _as(world["mem"])
    ev = world["ev"]
    c.get(f"/events/{ev.pk}/tz/?tz=utc")
    body = c.get(f"/events/{ev.pk}/").content.decode()
    assert "Times in <strong>UTC</strong>" in body


def test_slot_page_and_fragment_and_signup_from_it(world):
    c = _as(world["mem"])
    ev = world["ev"]
    slot = Slot.objects.filter(position=world["run"], kind="operating").first()
    page = c.get(f"/events/{ev.pk}/slot/{slot.pk}/").content.decode()
    assert "Who is on it" in page and 'id="sidenav"' in page and "Sign up" in page
    frag = c.get(f"/events/{ev.pk}/slot/{slot.pk}/?partial=1").content.decode()
    assert "Who is on it" in frag and "<html" not in frag
    c.post(f"/events/slot/{slot.pk}/signup/", {"role": "observer", "note": "first time"})
    assert SignUp.objects.filter(slot=slot, user=world["mem"], role="observer").exists()
    body = c.get(f"/events/{ev.pk}/").content.decode()
    assert 'class="you"' in body


def test_captain_edits_seats_control_operator_and_assigns(world):
    c = _as(world["off"])
    ev, mem = world["ev"], world["mem"]
    slot = Slot.objects.filter(position=world["mult"], kind="operating").first()
    c.post(f"/events/{ev.pk}/slot/{slot.pk}/seats/", {"cap_operator": "2", "cap_observer": "0"})
    assert {c_.role: c_.capacity for c_ in slot.capacities.all()} == {"operator": 2}
    c.post(f"/events/{ev.pk}/slot/{slot.pk}/assign/", {"user": mem.pk, "role": "operator"})
    assert SignUp.objects.filter(slot=slot, user=mem, role="operator").exists()
    c.post(f"/events/{ev.pk}/slot/{slot.pk}/control-operator/", {"user": world["off"].pk})
    slot.refresh_from_db()
    assert slot.control_operator is None  # the officer is not in the slot
    c.post(f"/events/{ev.pk}/slot/{slot.pk}/control-operator/", {"user": mem.pk})
    slot.refresh_from_db()
    assert slot.control_operator == mem
    assert (
        _as(mem).post(f"/events/{ev.pk}/slot/{slot.pk}/seats/", {"cap_operator": "9"}).status_code
        == 404
    )


def test_bulk_signup_reports_per_slot_and_captain_bulk_close(world):
    c = _as(world["mem"])
    ev = world["ev"]
    run_slots = list(Slot.objects.filter(position=world["run"], kind="operating").order_by("start"))
    run_slots[1].closed = True
    run_slots[1].save()
    r = c.post(
        f"/events/{ev.pk}/bulk/",
        {
            "action": "signup",
            "role": "operator",
            "note": "",
            "slots": [s.pk for s in run_slots[:3]],
        },
        follow=True,
    )
    body = r.content.decode()
    assert SignUp.objects.filter(user=world["mem"], slot__in=run_slots[:3]).count() == 2
    assert "2 slots" in body and "closed" in body
    co = _as(world["off"])
    co.post(f"/events/{ev.pk}/bulk/", {"action": "close", "slots": [s.pk for s in run_slots]})
    assert Slot.objects.filter(pk__in=[s.pk for s in run_slots], closed=True).count() == len(
        run_slots
    )
    co.post(f"/events/{ev.pk}/bulk/", {"action": "cancel", "slots": [s.pk for s in run_slots]})
    # the two with sign-ups stay
    assert Slot.objects.filter(pk__in=[s.pk for s in run_slots], cancelled=False).count() == 2
    assert (
        c.post(
            f"/events/{ev.pk}/bulk/", {"action": "close", "slots": [run_slots[0].pk]}
        ).status_code
        == 404
    )


def test_present_wording():
    class St:
        def __init__(self, status, reasons):
            self.status, self.reasons = status, reasons

    class Sl:
        closed = False
        start = datetime(2030, 1, 1, tzinfo=UTC)

    now = datetime(2026, 1, 1, tzinfo=UTC)
    assert (
        present(
            Sl(),
            St("empty", ["no one signed up"]),
            [],
            ["operator"],
            published=True,
            is_captain=False,
            now=now,
        ).word
        == "Open"
    )
    assert (
        present(Sl(), St("empty", []), [], [], published=False, is_captain=False, now=now).word
        == "Opens when published"
    )
    p = present(
        Sl(),
        St("not_viable", ["nobody with station access (General or higher)"]),
        [object()],
        [],
        published=True,
        is_captain=False,
        now=now,
    )
    assert p.word == "Needs someone with station access (General or higher)" and p.tone == "warn"
    p = present(
        Sl(),
        St("at_risk", ["depends on Mo N0MEM alone"]),
        [object()],
        [],
        published=True,
        is_captain=False,
        now=now,
    )
    assert p.word == "Covered" and "one more person alongside Mo N0MEM" in p.detail


def test_events_list_and_home_show_both_zones(world):
    """Issue #23 on the private tracker: no bare times anywhere a member reads a schedule."""
    c = _as(world["mem"])
    body = c.get("/events/").content.decode()
    # The operating period runs 00:00Z to 04:00Z on Saturday 26th: Friday evening locally.
    assert "Fri 25 Sep 2026 20:00 – Sat 26 Sep 2026 00:00 EDT" in body
    assert "Sat 26 Sep 2026 00:00–04:00 UTC" in body
    assert "00:00</td>" not in body and "Z<" not in body
    c.get(f"/events/{world['ev'].pk}/tz/?tz=utc")
    body = c.get("/").content.decode()
    assert 'class="when1">Sat 26 Sep 2026 00:00–04:00 UTC' in body
