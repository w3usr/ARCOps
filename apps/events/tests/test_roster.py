"""The rebuilt roster (2026-09-13, second design round): day groups in two zones, grid or list,
status phrased as a need, the slot page and fragment, captain edits on a slot, bulk actions."""

from datetime import UTC, datetime, timedelta

import pytest
from django.test import Client

from apps.accounts.models import User
from apps.credentials.models import LicenseRecord
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
        groups=["officer"],
        first_name="Ann",
        last_name="Officer",
    )
    mem = User.objects.create_user(
        "mem@example.org",
        "pw-Testing-123",
        groups=["member"],
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


def _as(u, view="sysadmin"):
    c = Client()
    c.force_login(u)
    if u.is_superuser:
        session = c.session  # the level a sysadmin's session acts at
        session["acting_view"] = view
        session.save()
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


def test_the_zone_label_follows_the_event_not_today(world):
    """A 4 November event read on 15 October is headed EST, as its rows are (found in
    acceptance test T12, 2026-10-14)."""
    ev = world["ev"]
    start = datetime(2026, 11, 4, 18, 0, tzinfo=UTC)
    ev.periods.update(start=start, end=start + timedelta(hours=4))
    data = build(ev, world["mem"], "local", now=datetime(2026, 10, 15, 12, 0, tzinfo=UTC))
    assert data["lead_label"] == "EST" and data["other_label"] == "UTC"
    assert data["span"]["lead"].endswith("EST")


def test_a_utc_event_shows_each_time_once(world):
    """A contest shown in UTC repeated every time beneath itself, and offered "Lead with UTC"
    (found on the contact sheet, 2026-10-23)."""
    ev = world["ev"]
    ev.display_timezone = "UTC"
    ev.save()
    for lead in ("local", "utc"):
        data = build(ev, world["mem"], lead)
        row = data["days"][1].rows[0]  # Friday holds only the 23:00Z setup slot
        assert row.lead_range == "00:00–01:00 UTC" and row.other_range == ""
        assert data["span"]["lead"].endswith("UTC") and data["span"]["other"] == ""
        assert data["lead_label"] == "UTC" and data["other_label"] == ""
    body = _as(world["mem"]).get(f"/events/{ev.pk}/").content.decode()
    assert "Times in <strong>UTC</strong>." in body and "Lead with" not in body


def test_status_is_phrased_as_a_need_never_a_verdict(world):
    ev = world["ev"]
    body = _as(world["mem"]).get(f"/events/{ev.pk}/").content.decode()
    assert "Open" in body and "not viable" not in body.lower() and "Not viable" not in body
    assert "open slot" in body  # the member summary, not the captain's card
    assert ">Coverage<" not in body
    body = _as(world["off"]).get(f"/events/{ev.pk}/").content.decode()
    # NAF, 2026-09-20: ""Upcoming health" sounds too medical." The card is headed with the word
    # the roster already uses for a slot that has enough people: Covered.
    assert ">Coverage<" in body and "open</span>" in body


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
    frag = c.get(f"/events/{ev.pk}/slot/{slot.pk}/", HTTP_HX_REQUEST="true").content.decode()
    assert "Who is on it" in frag and "<html" not in frag
    c.post(f"/events/slot/{slot.pk}/signup/", {"role": "observer", "note": "first time"})
    assert SignUp.objects.filter(slot=slot, user=world["mem"], role="observer").exists()
    body = c.get(f"/events/{ev.pk}/").content.decode()
    assert 'class="you"' in body


def test_the_roster_dialog_answers_htmx_with_the_slot_and_its_cell(world):
    """#139: an action in the roster's dialog comes back to the slot there, with the slot's roster
    cell out of band, instead of leaving the roster for the slot's own page. One URL answers both
    ways, so the answer varies on the header."""
    c = _as(world["mem"])
    ev = world["ev"]
    slot = Slot.objects.filter(position=world["run"], kind="operating").first()
    url = f"/events/{ev.pk}/slot/{slot.pk}/"
    page = c.get(url)
    assert "HX-Request" in page["Vary"] and "hx-boost" not in page.content.decode()
    r = c.get(url, HTTP_HX_REQUEST="true")
    frag = r.content.decode()
    assert "HX-Request" in r["Vary"] and "<html" not in frag
    assert f'id="slot-{slot.pk}" hx-swap-oob="true"' in frag and 'hx-boost="true"' in frag

    r = c.post(f"/events/slot/{slot.pk}/signup/", {"role": "observer"}, HTTP_HX_REQUEST="true")
    assert r.status_code == 302 and r["Location"] == url  # without htmx, the roster
    frag = c.get(url, HTTP_HX_REQUEST="true").content.decode()
    assert "Done:</span> Signed up as Observer" in frag and "You hold this slot" in frag
    assert 'class="you"' in frag  # the cell sent back for the roster behind the dialog

    # Anywhere else a redirect leads, htmx loads the whole page instead of filling the dialog.
    r = Client().get(url, HTTP_HX_REQUEST="true")
    assert r.status_code == 200 and r["HX-Redirect"].startswith("/accounts/login/")


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
    assert slot.control_operator is None  # in the slot, but unlicensed (FR-63; SK, 2026-10-15)
    LicenseRecord.objects.create(
        user=mem,
        callsign="N0MEM",
        operator_class="General",
        status="active",
        expiry_date=datetime(2030, 1, 1).date(),
    )
    c.post(f"/events/{ev.pk}/slot/{slot.pk}/control-operator/", {"user": mem.pk})
    slot.refresh_from_db()
    assert slot.control_operator == mem
    assert (
        _as(mem).post(f"/events/{ev.pk}/slot/{slot.pk}/seats/", {"cap_operator": "9"}).status_code
        == 404
    )


def test_seats_below_the_people_holding_a_role_are_refused(world):
    """Found in acceptance test T16 (2026-10-16): Observer 0 with an observer in the slot was
    saved as "Seats updated." and left them in a role with no seats. SK, 2026-10-16: refuse."""
    c = _as(world["off"])
    ev, mem = world["ev"], world["mem"]
    slot = Slot.objects.filter(position=world["mult"], kind="operating").first()
    SignUp.objects.create(slot=slot, user=mem, role="observer")
    r = c.post(
        f"/events/{ev.pk}/slot/{slot.pk}/seats/",
        {"cap_operator": "3", "cap_observer": "0"},
        follow=True,
    )
    assert {c_.role: c_.capacity for c_ in slot.capacities.all()} == {"operator": 1, "observer": 2}
    body = r.content.decode()
    assert "Seats updated." not in body and "1 person holds Observer" in body


def test_sign_someone_up_needs_a_live_slot_and_a_published_or_locked_event(world):
    """Found in acceptance test T16 (2026-10-16): a crafted request put a member into a canceled
    slot and mailed them. SK, 2026-10-16: no captain sign-ups while the event is a draft."""
    c = _as(world["off"])
    ev, mem = world["ev"], world["mem"]
    slot = Slot.objects.filter(position=world["mult"], kind="operating").first()
    page, assign = f"/events/{ev.pk}/slot/{slot.pk}/", f"/events/{ev.pk}/slot/{slot.pk}/assign/"
    for state in (Event.State.DRAFT, Event.State.CANCELLED, Event.State.COMPLETED):
        Event.objects.filter(pk=ev.pk).update(state=state)
        c.post(assign, {"user": mem.pk, "role": "observer"})
        assert not SignUp.objects.filter(slot=slot).exists(), state
    Event.objects.filter(pk=ev.pk).update(state=Event.State.DRAFT)
    assert "Sign someone up" not in c.get(page).content.decode()
    Event.objects.filter(pk=ev.pk).update(state=Event.State.LOCKED)  # when captains place people
    assert "Sign someone up" in c.get(page).content.decode()
    c.post(assign, {"user": mem.pk, "role": "observer"})
    assert SignUp.objects.filter(slot=slot, user=mem).exists()
    SignUp.objects.filter(slot=slot).delete()
    Slot.objects.filter(pk=slot.pk).update(cancelled=True)
    assert c.post(assign, {"user": mem.pk, "role": "observer"}).status_code == 404
    assert not SignUp.objects.filter(slot=slot).exists()


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
    assert "Signed up as Operator for 2 slots." in body and "closed" in body  # role_label
    co = _as(world["off"])
    co.post(f"/events/{ev.pk}/bulk/", {"action": "close", "slots": [s.pk for s in run_slots]})
    assert Slot.objects.filter(pk__in=[s.pk for s in run_slots], closed=True).count() == len(
        run_slots
    )
    # Canceling cannot be undone, so it asks first and says what is about to go.
    r = co.post(f"/events/{ev.pk}/bulk/", {"action": "cancel", "slots": [s.pk for s in run_slots]})
    assert r.status_code == 200 and b"cannot be brought back" in r.content
    # and names the slots it leaves alone, not only how many (acceptance test T14, 2026-10-14):
    # 00:00Z and 02:00Z hold sign-ups, and neither is among the slots that go
    kept = r.content.decode().split("left alone:")[1].split("Remove the people first")[0]
    assert "Sat 26 Sep 00:00Z" in kept and "Sat 26 Sep 02:00Z" in kept
    assert Slot.objects.filter(pk__in=[s.pk for s in run_slots], cancelled=False).count() == 4
    co.post(
        f"/events/{ev.pk}/bulk/",
        {"action": "cancel", "confirmed": "yes", "slots": [s.pk for s in run_slots]},
    )
    # the two with sign-ups stay
    assert Slot.objects.filter(pk__in=[s.pk for s in run_slots], cancelled=False).count() == 2
    assert (
        c.post(
            f"/events/{ev.pk}/bulk/", {"action": "close", "slots": [run_slots[0].pk]}
        ).status_code
        == 404
    )


def test_a_locked_roster_offers_members_nothing_to_tick(world):
    """A locked roster kept its tick-boxes for members, with nothing behind them, and a forced
    bulk sign-up there was told it opens when published (T37 step 1, 2026-10-19)."""
    ev = world["ev"]
    Event.objects.filter(pk=ev.pk).update(state=Event.State.LOCKED)
    body = _as(world["mem"]).get(f"/events/{ev.pk}/").content.decode()
    assert 'name="slots"' not in body and "data-select-day" not in body
    assert 'id="bulk-bar"' not in body
    body = _as(world["off"]).get(f"/events/{ev.pk}/").content.decode()
    assert 'name="slots"' in body and 'id="bulk-bar"' in body  # Close and Cancel still apply
    slot = Slot.objects.filter(position=world["run"], kind="operating").first()
    r = _as(world["mem"]).post(
        f"/events/{ev.pk}/bulk/",
        {"action": "signup", "role": "operator", "slots": [slot.pk]},
        follow=True,
    )
    body = r.content.decode()
    assert "The roster is locked." in body and "when the event is published" not in body


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


def test_the_captains_red_within_48_hours_says_so_in_words(world):
    """A captain's red for a slot that still needs someone within 48 hours read, by the key, as
    "over limit", and only its color set it apart from the amber Needs (T15, 2026-10-19)."""

    class St:
        status, reasons = "not_viable", ["nobody with station access", "nobody with a license"]

    class Sl:
        closed = False
        start = datetime(2026, 1, 2, tzinfo=UTC)

    now = datetime(2026, 1, 1, tzinfo=UTC)
    args = (Sl(), St(), [object()], [])
    p = present(*args, published=True, is_captain=True, now=now)
    assert p.tone == "bad" and p.word == "Needs someone with station access"
    assert p.detail == "within 48 hours; someone with a license"
    p = present(*args, published=True, is_captain=False, now=now)
    assert p.tone == "warn" and "48 hours" not in p.detail

    ev = world["ev"]
    entry = "within 48 hours: it starts soon and still needs someone"
    assert entry in _as(world["off"]).get(f"/events/{ev.pk}/").content.decode()
    assert entry not in _as(world["mem"]).get(f"/events/{ev.pk}/").content.decode()


def test_events_list_and_home_show_both_zones(world, monkeypatch):
    """Issue #23 on the private tracker: no bare times anywhere a member reads a schedule."""
    # Home lists only events that have not ended, so read it from a week before this one.
    # Temporary fix: the test passes only on the assumption that the day it runs is
    # 2026-09-19. To be revised if a different approach is requested (for example, event
    # dates relative to today).
    monkeypatch.setattr(
        "django.utils.timezone.now", lambda: datetime(2026, 9, 19, 12, 0, tzinfo=UTC)
    )
    c = _as(world["mem"])
    body = c.get("/events/").content.decode()
    # The operating period runs 00:00Z to 04:00Z on Saturday 26th: Friday evening locally.
    assert "Fri 25 Sep 2026 20:00 – Sat 26 Sep 2026 00:00 EDT" in body
    assert "Sat 26 Sep 2026 00:00–04:00 UTC" in body
    assert "00:00</td>" not in body and "Z<" not in body
    c.get(f"/events/{world['ev'].pk}/tz/?tz=utc")
    body = c.get("/").content.decode()
    assert 'class="when1">Sat 26 Sep 2026 00:00–04:00 UTC' in body


@pytest.mark.django_db
def test_the_calendar_address_is_the_same_every_time_you_look():
    """NAF, 2026-09-19: "Is this calendar address supposed to change every time I reload the
    page? It does, but I feel like it shouldn't."

    It should not: a subscription address that changes on every page load is impossible to tell
    apart from one that has leaked, and it left a live credential behind on every view.
    """
    from django.core import signing
    from django.test import Client

    from apps.accounts.models import User
    from apps.events.views_member import FEED_SALT, feed_token

    member = User.objects.create_user(
        "sked@example.org", "pw-Testing-123", groups=["member"], first_name="Sam", last_name="Key"
    )
    c = Client()
    c.force_login(member)
    first = c.get("/events/mine/").content.decode()
    second = c.get("/events/mine/").content.decode()
    key = feed_token(member)
    assert key in first and key in second, "the same address, twice"
    assert len(key) >= 40, "and long enough to be a secret in a URL"

    assert Client().get(f"/events/feed/{key}.ics").status_code == 200
    assert Client().get("/events/feed/not-a-key.ics").status_code == 404

    # an address handed out before the key existed keeps working
    old = signing.dumps({"u": member.pk}, salt=FEED_SALT)
    assert Client().get(f"/events/feed/{old}.ics").status_code == 200


@pytest.mark.django_db
def test_a_member_can_replace_a_calendar_address_that_has_leaked():
    """The other half of holding a key rather than a signature: it can be revoked."""
    from django.test import Client

    from apps.accounts.models import User
    from apps.events.views_member import feed_token
    from apps.ops.models import AuditLog

    member = User.objects.create_user(
        "leak@example.org", "pw-Testing-123", groups=["member"], first_name="Lee", last_name="Key"
    )
    old = feed_token(member)
    assert Client().get(f"/events/feed/{old}.ics").status_code == 200

    c = Client()
    c.force_login(member)
    assert "Replace this address" in c.get("/events/mine/").content.decode()
    r = c.post("/events/feed/replace/", follow=True)
    assert r.status_code == 200 and b"Your calendar address is new" in r.content

    member.refresh_from_db()
    new = member.calendar_key
    assert new != old
    assert Client().get(f"/events/feed/{old}.ics").status_code == 404, "the old one stops working"
    assert Client().get(f"/events/feed/{new}.ics").status_code == 200
    assert AuditLog.objects.filter(action="calendar.address_replaced").exists()


# Home opens on what you do next (#162). The clock is a week before the event, as above.
def _home(world, monkeypatch, who):
    monkeypatch.setattr(
        "django.utils.timezone.now", lambda: datetime(2026, 9, 19, 12, 0, tzinfo=UTC)
    )
    return _as(world[who])


def test_home_offers_the_next_events_open_hours_to_somebody_signed_up_for_nothing(
    world, monkeypatch
):
    body = _home(world, monkeypatch, "mem").get("/").content.decode()
    assert "<h1>Pick your hours</h1>" in body
    open_slots = Slot.objects.filter(position__location__event=world["ev"]).count()
    assert f"{open_slots} open slots" in body  # every slot, setup too, as the roster counts
    assert "Hello," not in body


def test_home_leads_with_your_next_slot_and_the_one_thing_to_do_about_it(world, monkeypatch):
    c = _home(world, monkeypatch, "mem")
    first, later = Slot.objects.filter(position=world["run"], kind="operating").order_by("start")[
        :2
    ]
    mine = SignUp.objects.create(slot=first, user=world["mem"], role="operator")
    SignUp.objects.create(slot=later, user=world["mem"], role="operator")
    body = c.get("/").content.decode()
    assert "<h1>Your next slot</h1>" in body
    assert "In 6\xa0days" in body and "Club station · Run · as Operator" in body
    assert "Confirm you will be there" in body and "Your other slots" in body
    c.post(f"/events/signup/{mine.pk}/confirm/")
    body = c.get("/").content.decode()
    assert "Confirm you will be there" not in body and '<span class="tag">confirmed</span>' in body


def test_home_shows_a_captain_the_gaps_in_the_next_event_they_run(world, monkeypatch):
    body = _home(world, monkeypatch, "off").get("/").content.decode()
    assert "Gaps in RTTY" in body
    open_slots = Slot.objects.filter(position__location__event=world["ev"]).count()
    assert f"{open_slots} open slots" in body and f"{open_slots} open</span>" in body  # one count
    assert "Gaps in" not in _home(world, monkeypatch, "mem").get("/").content.decode()
