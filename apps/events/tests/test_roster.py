"""The rebuilt roster: day groups in two zones, grid or list,
status phrased as a need, the slot page and fragment, captain edits on a slot, bulk actions."""

import re
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.test import Client
from django.utils import timezone

from apps.accounts.models import User
from apps.credentials.models import LicenseRecord
from apps.events import views_slots
from apps.events.models import (
    Event,
    Location,
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
    ev.start, ev.end = start, start + timedelta(hours=4)
    ev.save(update_fields=["start", "end"])
    loc = Location.objects.create(event=ev, name="Club station")
    run = Position.objects.create(location=loc, name="Run", order=1)
    mult = Position.objects.create(location=loc, name="Mult", order=2)
    for s in generate_slots(ev, [run, mult], minutes=60, setup_slots=1):
        RoleCapacity.objects.create(slot=s, role="operator", capacity=1)
        RoleCapacity.objects.create(slot=s, role="observer", capacity=2)
    # What the middleware does for a page with no `tz` cookie, for build() called directly (A38).
    with timezone.override(ZoneInfo("America/New_York")):
        yield {"off": off, "mem": mem, "ev": ev, "run": run, "mult": mult}


def _as(u, view="sysadmin"):
    c = Client()
    c.force_login(u)
    if u.is_superuser:
        session = c.session  # the level a sysadmin's session acts at
        session["acting_view"] = view
        session.save()
    return c


def test_grid_layout_days_in_the_viewers_zone(world):
    """Functional addendum A38: one zone, the viewer's own; no UTC on the page."""
    data = build(world["ev"], world["mem"])
    assert data["layout"] == "grid" and len(data["positions"]) == 2
    assert data["lead_label"] == "EDT" and data["other_label"] == ""
    assert [d.heading for d in data["days"]] == ["Friday, September 25"]  # 23:00Z to 04:00Z
    row = data["days"][0].rows[1]  # 00:00Z Saturday is Friday evening in New York
    assert row.lead_range == "8:00–9:00 PM EDT" and row.other_range == ""
    assert len(row.cells) == 2 and all(row.cells)


def test_the_zone_label_follows_the_event_not_today(world):
    """A 4 November event read on 15 October is headed EST, as its rows are."""
    ev = world["ev"]
    start = datetime(2026, 11, 4, 18, 0, tzinfo=UTC)
    Event.objects.filter(pk=ev.pk).update(start=start, end=start + timedelta(hours=4))
    ev.refresh_from_db()
    data = build(ev, world["mem"], now=datetime(2026, 10, 15, 12, 0, tzinfo=UTC))
    assert data["lead_label"] == "EST" and data["other_label"] == ""
    assert data["span"]["lead"].endswith("EST") and data["span"]["other"] == ""


def test_an_event_in_utc_still_reads_in_the_viewers_zone(world):
    """A contest whose own zone is UTC: the page shows the viewer's time, not UTC (A38)."""
    ev = world["ev"]
    ev.display_timezone = "UTC"
    ev.save()
    assert _rows(build(ev, world["mem"]))[1].lead_range == "8:00–9:00 PM EDT"
    body = _as(world["mem"]).get(f"/events/{ev.pk}/").content.decode()
    assert "Times in <strong>EDT</strong>." in body and "UTC" not in body


def test_an_open_cell_reads_its_state_and_its_link_names_the_action(world):
    """Twenty cells read "Open · sign up" on a small event. The cell says Open; the
    action and the slot are in the link's accessible name, for a screen reader (FR-62, FR-95)."""
    body = _as(world["mem"]).get(f"/events/{world['ev'].pk}/").content.decode()
    assert "<small>sign up</small>" not in body
    assert 'aria-label="Open: sign up for Run, Fri, Sep 25, 8:00 PM EDT"' in body
    assert 'aria-label="Open: sign up for Mult, Fri, Sep 25, 7:00 PM EDT"' in body  # setup


def test_know_before_you_go_shows_only_the_sections_written(world):
    """An event never edited keeps the outline's six empty headings, which the event page
    printed under the roster. It drops them as the reminder does."""
    from apps.events.views_manage import KBYG_OUTLINE

    ev, c = world["ev"], _as(world["mem"])
    ev.kbyg_html = KBYG_OUTLINE
    ev.save()
    body = c.get(f"/events/{ev.pk}/").content.decode()
    assert "Know before you go" not in body and "Getting into the station" not in body
    ev.kbyg_html = KBYG_OUTLINE.replace(
        "<h2>What to bring</h2><p></p>", "<h2>What to bring</h2><p>A headset.</p>"
    )
    ev.save()
    body = c.get(f"/events/{ev.pk}/").content.decode()
    assert "Know before you go" in body and "What to bring" in body and "A headset." in body
    assert "Getting into the station" not in body and "Who to contact" not in body


def test_status_is_phrased_as_a_need_never_a_verdict(world):
    ev = world["ev"]
    body = _as(world["mem"]).get(f"/events/{ev.pk}/").content.decode()
    assert "Open" in body and "not viable" not in body.lower() and "Not viable" not in body
    assert "open slot" in body  # the member summary, not the captain's card
    assert ">Coverage<" not in body
    body = _as(world["off"]).get(f"/events/{ev.pk}/").content.decode()
    # The card is headed with the word the roster already uses for a slot that has enough
    # people: Covered, rather than a clinical "health".
    assert ">Coverage<" in body and "open</span>" in body


def test_one_time_column_in_the_viewers_zone_from_the_browsers_cookie(world):
    """A38: the zone is named once, in the header; the browser's `tz` cookie picks it, the club's
    zone stands in before it has, and a name the server does not know is ignored."""
    ev = world["ev"]
    body = _as(world["mem"]).get(f"/events/{ev.pk}/").content.decode()
    assert "Times in <strong>EDT</strong>." in body and 'data-tz="America/New_York"' in body
    assert '<div class="r-time" role="columnheader">EDT</div>' in body and "r-zone" not in body
    row = build(ev, world["mem"])["days"][0].rows[1]  # 00:00Z Saturday, the first operating hour
    assert (row.lead_hours, row.other_hours) == ("8:00–9:00 PM", "")
    c = _as(world["mem"])
    c.cookies["tz"] = "America/Los_Angeles"
    body = c.get(f"/events/{ev.pk}/").content.decode()
    assert "Times in <strong>PDT</strong>." in body and ">5:00–6:00 PM<" in body
    c.cookies["tz"] = (
        "Asia/Calcutta"  # Chromium's name for it; recent Ubuntu keeps it only in tzdata
    )
    assert "Times in <strong>IST</strong>." in c.get(f"/events/{ev.pk}/").content.decode()
    c.cookies["tz"] = "Not/AZone"
    assert "Times in <strong>EDT</strong>." in c.get(f"/events/{ev.pk}/").content.decode()
    assert _as(world["mem"]).get(f"/events/{ev.pk}/tz/?tz=local").status_code == 404


def test_a_row_names_its_zone_where_the_clocks_have_changed(world):
    """Section 5.9: an event can straddle the end of daylight saving time. The header names the
    zone the event starts in, and a row after the change says it is in EST."""
    ev = world["ev"]
    start = datetime(2026, 11, 1, 3, 0, tzinfo=UTC)  # 23:00 EDT; clocks go back at 06:00Z
    Event.objects.filter(pk=ev.pk).update(start=start, end=start + timedelta(hours=6))
    ev.refresh_from_db()
    Slot.objects.filter(position__location__event=ev).delete()
    generate_slots(ev, [world["run"]], minutes=60)
    data = build(ev, world["mem"])
    rows = [r for d in data["days"] for r in d.rows]
    assert data["lead_label"] == "EDT"
    assert rows[0].lead_hours == "11:00 PM–midnight" and rows[-1].lead_hours.endswith(" EST")


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
    """An action in the roster's dialog comes back to the slot there, with the slot's roster
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
    assert slot.control_operator is None  # in the slot, but unlicensed (FR-63)
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
    """Observer 0 with an observer in the slot was saved as "Seats updated." and left them in
    a role with no seats; it is refused."""
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
    """A crafted request put a member into a canceled slot and mailed them. No captain sign-ups
    while the event is a draft."""
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
    # and names the slots it leaves alone, not only how many:
    # 00:00Z and 02:00Z hold sign-ups, and neither is among the slots that go
    kept = r.content.decode().split("left alone:")[1].split("Remove the people first")[0]
    assert "Fri, Sep 25, 8:00 PM EDT" in kept and "Fri, Sep 25, 10:00 PM EDT" in kept
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
    bulk sign-up there was told it opens when published."""
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


def test_the_captains_red_within_48_hours_says_so_in_words(world):
    """A captain's red for a slot that still needs someone within 48 hours read, by the key, as
    "over limit", and only its color set it apart from the amber Needs."""

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


def test_events_list_and_home_show_the_viewers_zone_only(world, monkeypatch):
    """No bare times anywhere a member reads a schedule."""
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
    assert "Fri, Sep 25, 2026, 8:00 PM – Sat, Sep 26, 2026, 12:00 AM EDT" in body  # local: en-US
    assert "UTC" not in body and "00:00</td>" not in body and "Z<" not in body
    body = c.get("/").content.decode()  # the viewer's zone only (functional addendum A38)
    assert '<time datetime="2026-09-26T00:00:00+00:00">Fri, Sep 25, 2026, 8:00 PM – ' in body
    assert "UTC" not in body


@pytest.mark.django_db
def test_the_calendar_address_is_the_same_every_time_you_look():
    """A subscription address that changes on every page load is impossible to tell
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


# Home opens on what you do next. The clock is a week before the event, as above.
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
    assert world["ev"].title in body and ">Open the roster</a>" in body
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
    assert "In 6\xa0days" in body and "Run at Club station, as Operator" in body
    assert "Confirm you will be there" in body and "Your other slots" in body
    # The most important action first (FR-116): Confirm before the roster.
    assert body.index("Confirm you will be there") < body.index(">Open the roster</a>")
    sked = c.get("/events/mine/").content.decode()
    row = sked[sked.index("<tbody>") :]
    assert row.index(">Confirm</button>") < row.index(f'href="/events/{world["ev"].pk}/"')
    c.post(f"/events/signup/{mine.pk}/confirm/")
    body = c.get("/").content.decode()
    assert "Confirm you will be there" not in body and '<span class="tag">confirmed</span>' in body


def test_home_shows_a_captain_the_gaps_in_the_next_event_they_run(world, monkeypatch):
    body = _home(world, monkeypatch, "off").get("/").content.decode()
    assert "Gaps in RTTY" in body
    open_slots = Slot.objects.filter(position__location__event=world["ev"]).count()
    assert f"{open_slots} open slots" in body and f"{open_slots} open</span>" in body  # one count
    assert "Gaps in" not in _home(world, monkeypatch, "mem").get("/").content.decode()


# Folded runs of open hours.
def _rows(data):
    return [r for d in data["days"] for r in d.rows]


def test_a_run_of_open_hours_folds_into_one_line_and_setup_stays_itself(world):
    rows = _rows(build(world["ev"], world["mem"]))
    operating = [r for r in rows if r.kind == "operating"]
    fold = operating[0].fold
    assert fold and operating[0].fold_head and all(r.fold is fold for r in operating)
    assert (fold.hours, fold.slots, fold.open) == (4, 8, False)  # two positions, four hours
    assert all(r.fold is None for r in rows if r.kind != "operating")  # one setup row stays


@pytest.mark.parametrize(
    "hours, minutes, positions, folds",
    [
        (1, 20, 2, False),  # three 20-minute rows are one hour, not three
        (2, 30, 2, False),  # four 30-minute rows are two hours
        (4, 120, 2, True),  # two 2-hour rows are four hours
        (4, 60, 5, True),  # five positions: the list layout, a row per slot
    ],
)
def test_open_time_folds_by_three_clock_hours_not_by_rows(world, hours, minutes, positions, folds):
    """A13: three or more consecutive hours in which every slot is open read as one row."""
    ev = Event.objects.create(title="Fold", state=Event.State.PUBLISHED, created_by=world["off"])
    ev.start = datetime(2026, 9, 26, 0, 0, tzinfo=UTC)
    ev.end = ev.start + timedelta(hours=hours)
    ev.save(update_fields=["start", "end"])
    loc = Location.objects.create(event=ev, name="Station")
    made = [Position.objects.create(location=loc, name=f"P{i}", order=i) for i in range(positions)]
    for slot in generate_slots(ev, made, minutes=minutes):
        RoleCapacity.objects.create(slot=slot, role="operator", capacity=1)
    rows = _rows(build(ev, world["mem"]))
    assert len(rows) == hours * 60 // minutes * (1 if positions <= 4 else positions)
    assert all(r.fold for r in rows) if folds else not any(r.fold for r in rows)


def test_anybody_in_a_slot_breaks_the_run_and_short_runs_do_not_fold(world):
    second = Slot.objects.filter(position=world["mult"], kind="operating").order_by("start")[1]
    SignUp.objects.create(slot=second, user=world["mem"], role="operator")
    assert all(r.fold is None for r in _rows(build(world["ev"], world["mem"])))


def test_a_fold_opens_by_its_id_or_all_of_them(world):
    fold = _rows(build(world["ev"], world["mem"]))[1].fold
    assert _rows(build(world["ev"], world["mem"], open_fold=fold.id))[1].fold.open
    assert _rows(build(world["ev"], world["mem"], open_fold="all"))[1].fold.open


def test_the_roster_page_hides_a_folded_run_and_opens_it_without_javascript(world):
    c = _as(world["mem"])
    body = c.get(f"/events/{world['ev'].pk}/").content.decode()
    fold = re.search(r'id="fold-(\d+)"', body)
    assert fold and "4 open hours" in body and "8 slots" in body
    assert body.count(f'data-fold="{fold[1]}" hidden') == 4
    opened = c.get(f"/events/{world['ev'].pk}/?open={fold[1]}").content.decode()
    assert (
        "r-fold" not in opened
        and " hidden" not in opened.split('class="roster')[1].split("</form>")[0]
    )


def test_a_run_that_ends_at_midnight_ends_at_midnight(world):
    fold = _rows(build(world["ev"], world["mem"]))[1].fold
    assert fold.lead_range == "8:00 PM–midnight EDT"  # 00:00Z to 04:00Z; 04:00Z is midnight EDT
    assert fold.other_range == ""


# The coverage strip.
def test_the_strip_marks_every_span_by_its_most_urgent_state_and_links_to_it(world):
    first = Slot.objects.filter(position=world["run"], kind="operating").order_by("start").first()
    SignUp.objects.create(slot=first, user=world["mem"], role="observer")  # in it, still needs
    data = build(world["ev"], world["mem"])
    marks = [m for d in data["strip"] for m in d["marks"]]
    assert len(marks) == 5  # the setup hour and four operating hours, across both positions
    assert [m["mark"] for m in marks[1:3]] == ["!", ""]  # needs outranks Mult's open seat
    assert marks[1]["href"] == f"#r-{first.start:%Y%m%d%H%M}" and marks[1]["time"] == "8:00–9:00 PM"
    folded = marks[2]["href"]  # 01:00 onward is a run of three open hours, folded
    assert folded.startswith("?open=") and folded.endswith(f"#r-{first.end:%Y%m%d%H%M}")
    filtered = build(world["ev"], world["mem"], filter="problems")
    assert sum(len(d["marks"]) for d in filtered["strip"]) == 5  # the whole event, still


def test_the_strip_is_for_the_eye_and_the_key_reads_its_marks(world):
    body = _as(world["mem"]).get(f"/events/{world['ev'].pk}/").content.decode()
    strip = re.split(
        r'</div>\s*<div class="legend',
        body.split('<div class="strip" aria-hidden="true">', 1)[1],
        maxsplit=1,
    )[0]
    assert strip.count('tabindex="-1"') == strip.count("<a ") == 5
    assert (
        '<span class="sm sm-open" aria-hidden="true"></span> <span class="what">'
        '<span class="tag open">Open</span>' in body
    )


def test_the_key_opens_from_a_button_beside_problems_only(world):
    """The Key is a native popover behind a ? button named Key, beside
    Problems only; no script of ours. The list inside is still named Key."""
    body = _as(world["mem"]).get(f"/events/{world['ev'].pk}/").content.decode()
    zones = body.split('<p class="zones muted">', 1)[1].split("</p>", 1)[0]
    assert "Problems only" in zones
    # the ? an icon-only button named Key, still beside Problems only
    assert re.search(
        r'<button type="button" class="[^"]*keybtn" popovertarget="roster-key-pop" aria-label="Key">',
        zones,
    )
    assert '<div class="legend muted" id="roster-key-pop" popover>' in body
    assert '<ul aria-labelledby="roster-key">' in body and 'id="roster-key">Key</span>' in body


def test_a_canceled_events_slots_leave_home_and_my_sked(world, monkeypatch):
    c = _home(world, monkeypatch, "mem")
    slot = Slot.objects.filter(position=world["run"], kind="operating").first()
    SignUp.objects.create(slot=slot, user=world["mem"], role="operator")
    assert "<h1>Your next slot</h1>" in c.get("/").content.decode()
    Event.objects.filter(pk=world["ev"].pk).update(state=Event.State.CANCELLED)
    assert "<h1>Your next slot</h1>" not in c.get("/").content.decode()
    assert "Run at Club station" not in c.get("/events/mine/").content.decode()


def test_inside_its_window_check_in_is_the_first_thing_on_home_to_take_the_focus(
    world, monkeypatch
):
    # FR-116: the check-in button, inside its window, is first in the tab order.
    slot = Slot.objects.filter(position=world["run"], kind="operating").order_by("start").first()
    SignUp.objects.create(slot=slot, user=world["mem"], role="operator")
    monkeypatch.setattr("django.utils.timezone.now", lambda: slot.start - timedelta(minutes=10))
    body = _as(world["mem"]).get("/").content.decode()
    main = body[body.index("<main") :]
    main = main[main.index("</h1>") :]
    assert (
        re.search(r"<(a href|button|input(?! type=\"hidden\")|select|textarea)", main).group(0)
        == "<button"
    )
    assert main.index(">Check in</button>") < main.index(">Open the roster</a>")


def test_mail_leads_with_utc_and_gives_the_events_zone_beside_it(world):
    # A12, extended to mail.
    from apps.events.services.notify import mail_when, when_text

    slot = Slot.objects.filter(position=world["run"], kind="operating").order_by("start").first()
    text = when_text(slot)
    assert re.fullmatch(
        r"\w{3} \d+ \w{3} \d{4} \d\d:\d\d–\d\d:\d\d UTC \(.+ [AP]M E[SD]T\)", text
    ), text
    ev = world["ev"]
    span = mail_when(ev.start, ev.end, ev, " to ")
    assert span.index("UTC") < span.index("(") and " – " in span  # across days


def test_sign_someone_up_finds_by_any_part_of_a_name_or_call_and_leaves_out_who_is_in(
    world, monkeypatch
):
    """Typed, not a drop-down of the membership; the role first, and nobody already in the
    slot."""
    c = _as(world["off"])
    ev, mem = world["ev"], world["mem"]
    slot = Slot.objects.filter(position=world["mult"], kind="operating").first()
    page = f"/events/{ev.pk}/slot/{slot.pk}/"
    choice = f'name="user" value="{mem.pk}"'
    assert choice not in c.get(page).content.decode()  # nothing typed, nobody listed
    for q in ("n0m", "MEMB", "mo mem"):
        assert choice in c.get(page, {"q": q, "role": "observer"}).content.decode(), q
    assert "Nobody here matches" in c.get(page, {"q": "zzz", "role": "observer"}).content.decode()
    # Find with script off posts, and comes back to the slot with what was typed and the role
    r = c.post(f"{page}assign/", {"find": "1", "q": "n0m", "role": "observer", "manage": "1"})
    assert r.status_code == 302 and r.url == f"{page}?q=n0m&role=observer&manage=1"
    assert not SignUp.objects.filter(slot=slot).exists()
    # the role's own rule decides who is offered: one that refuses Operator leaves Mo out of it
    monkeypatch.setattr(
        views_slots, "can_sign_up", lambda m, s, role, **kw: (role != "operator", "no license")
    )
    assert choice not in c.get(page, {"q": "n0m", "role": "operator"}).content.decode()
    assert choice in c.get(page, {"q": "n0m", "role": "observer"}).content.decode()
    SignUp.objects.create(slot=slot, user=mem, role="observer")
    assert choice not in c.get(page, {"q": "n0m", "role": "observer"}).content.decode()


def test_appoint_a_captain_finds_by_name_and_leaves_out_the_captains(world):
    c = _as(world["off"])
    ev, mem = world["ev"], world["mem"]
    page = f"/events/{ev.pk}/captains/add/"
    assert f'value="{mem.pk}"' in c.get(page, {"q": "mo"}).content.decode()
    r = c.post(page, {"find": "1", "q": "member"})
    assert r.status_code == 200 and f'value="{mem.pk}"' in r.content.decode()
    assert not ev.captaincies.filter(user=mem).exists()
    c.post(page, {"user": mem.pk})
    assert ev.captaincies.filter(user=mem).exists()
    assert f'value="{mem.pk}"' not in c.get(page, {"q": "mo"}).content.decode()


def test_members_sort_without_regard_to_case(world):
    """A name stored in capitals no longer comes first."""
    User.objects.create_user("z@example.org", "pw-Testing-123", first_name="Al", last_name="ABEL")
    User.objects.create_user("a@example.org", "pw-Testing-123", first_name="Bo", last_name="aaron")
    assert [
        u.last_name
        for u in User.objects.filter(last_name__iexact="abel")
        | User.objects.filter(last_name="aaron")
    ] == ["aaron", "ABEL"]


def test_manage_this_slot_is_folded_until_used_and_open_after(world):
    """The captain's box is a closed disclosure named Manage this slot, and comes back open after an
    action taken from inside it."""
    c = _as(world["off"])
    ev = world["ev"]
    slot = Slot.objects.filter(position=world["mult"], kind="operating").first()
    page = f"/events/{ev.pk}/slot/{slot.pk}/"
    body = c.get(page).content.decode()
    assert '<details class="card manage-slot">' in body and "Manage this slot" in body
    assert ">Captain<" not in body
    r = c.post(f"{page}seats/", {"cap_operator": "2", "cap_observer": "2", "manage": "1"})
    assert r.url == f"{page}?manage=1"
    assert '<details class="card manage-slot" open>' in c.get(r.url).content.decode()
    assert _as(world["mem"]).get(page).content.decode().count("Manage this slot") == 0


def test_change_seats_on_ticked_slots_reviews_first_and_refuses_per_slot(world):
    """Set, add or remove N seats per role: after sign-ups, nothing changes until the review is
    confirmed; a slot whose people would outnumber its seats is left alone and named; every other
    slot changes."""
    c = _as(world["off"])
    ev, mem = world["ev"], world["mem"]
    a, b = Slot.objects.filter(position=world["mult"], kind="operating").order_by("start")[:2]
    SignUp.objects.create(slot=a, user=mem, role="observer")
    url = f"/events/{ev.pk}/bulk/"
    ticked = {"action": "seats", "slots": [a.pk, b.pk]}
    seats = lambda s: {x.role: x.capacity for x in s.capacities.all()}  # noqa: E731
    assert "Leave as is" in c.post(url, ticked).content.decode()
    change = {
        **ticked,
        "op_operator": "add",
        "n_operator": "1",
        "op_observer": "set",
        "n_observer": "0",
    }
    body = c.post(url, {**change, "step": "review"}).content.decode()
    assert "Change seats on 1 slot" in body and "Careful:" in body and "Mult" in body
    assert seats(a) == seats(b) == {"operator": 1, "observer": 2}  # the review changes nothing
    r = c.post(url, {**change, "step": "apply"}, follow=True)
    assert "Seats changed on 1 slot." in r.content.decode()
    assert seats(a) == {"operator": 1, "observer": 2}  # MEM holds Observer here: left alone
    assert seats(b) == {"operator": 2}  # +1 Operator, Observer set to 0
    assert SignUp.objects.filter(slot=a, user=mem).exists()
    assert _as(mem).post(url, {**change, "step": "apply"}).status_code == 404


def test_change_seats_is_every_slot_or_none(world, monkeypatch):
    """A change that fails part way leaves no slot changed, so trying
    it again adds one seat, not two, where it had got to."""
    c = _as(world["off"])
    ev = world["ev"]
    a, b = Slot.objects.filter(position=world["mult"], kind="operating").order_by("start")[:2]
    seats = lambda s: {x.role: x.capacity for x in s.capacities.all()}  # noqa: E731
    before = seats(a), seats(b)
    real, calls = views_slots.set_seats, []

    def fails_on_the_second(user, slot, new):
        calls.append(slot.pk)
        real(user, slot, new)
        if len(calls) == 2:
            raise RuntimeError("database is locked")

    monkeypatch.setattr(views_slots, "set_seats", fails_on_the_second)
    change = {"action": "seats", "slots": [a.pk, b.pk], "op_operator": "add", "n_operator": "1"}
    with pytest.raises(RuntimeError):
        c.post(f"/events/{ev.pk}/bulk/", {**change, "step": "apply"})
    assert (seats(a), seats(b)) == before


def test_a_roster_mark_and_the_license_letter_say_what_they_mean_on_hover(world):
    """Each mark carries its words as a tooltip, the letter after a name its
    class in full, and the Key explains the letter."""
    ev, mem = world["ev"], world["mem"]
    slot = Slot.objects.filter(position=world["mult"], kind="operating").first()
    SignUp.objects.create(slot=slot, user=mem, role="observer", confirmed_at=slot.start)
    body = _as(world["off"]).get(f"/events/{ev.pk}/").content.decode()
    assert f'data-tip="{mem.license_letter_says}">{mem.license_letter}</span>' in body
    assert 'data-tip="Confirmed"' in body and "after a name, the license class" in body
    assert mem.license_letter_says == "No license on file"


def test_small_accessibility_gaps_are_closed(world):
    """FR-116 (WCAG 4.1.3, 1.3.1, 1.4.1): the bulk bar's count and Copied are
    spoken; Announce's Category is a group with a legend; the two urgent marks differ in shape."""
    from apps.events.services.roster import STRIP_MARKS

    page = _as(world["off"]).get(f"/events/{world['ev'].pk}/").content.decode()
    assert '<span class="count" aria-live="polite"><strong data-count>' in page
    assert 'id="said" class="sr-only" aria-live="polite"' in page
    announce = _as(world["off"]).get(f"/events/{world['ev'].pk}/announce/").content.decode()
    assert '<fieldset class="field checkset"><legend>Category</legend>' in announce
    assert STRIP_MARKS["problem"] != STRIP_MARKS["needs"]
