"""Creating and running an event from the manage page (§2.2, FR-42, FR-46, FR-47, FR-52)."""

from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.accounts.models import User
from apps.events.models import Captaincy, Event, Slot
from apps.ops import when
from apps.ops.models import ClubSetting

pytestmark = pytest.mark.django_db


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
        },
    )
    ev = Event.objects.get(title="Field Day")
    ev.locations.all().delete()  # its club station by default (276): these tests add their own
    # The first period is added on Operating periods like any other.
    c.post(f"/events/{ev.pk}/span/", {"start": "2026-06-27T18:00", "end": "2026-06-28T18:00"})
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
    ev.refresh_from_db()  # the start and end were posted after it was read
    return ev


def test_officer_builds_an_event_end_to_end(officer):
    c = _as(officer)
    ev = _build(c)
    assert ev.state == "draft" and Captaincy.objects.filter(event=ev, user=officer).exists()
    slots = Slot.objects.filter(position__location__event=ev)
    assert slots.count() == 2 * (24 + 2)  # two positions, 24 operating hours, setup and breakdown
    assert slots.filter(kind="operating").first().capacities.count() == 2
    body = c.get(f"/events/{ev.pk}/").content.decode()
    assert (
        "Manage</a>" in body and "24 operating hours" in body
    )  # the station's: Run and Mult at once


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
    assert cm.get(f"/events/{ev.pk}/manage/details/").status_code == 404
    assert cm.get("/events/new/").status_code == 404
    c.post(f"/events/{ev.pk}/captains/add/", {"user": mem.pk})
    assert cm.get(f"/events/{ev.pk}/manage/details/").status_code == 200
    c.post(f"/events/{ev.pk}/captains/{mem.pk}/remove/")
    assert cm.get(f"/events/{ev.pk}/manage/details/").status_code == 404


def test_only_an_officer_appoints_or_removes_captains(officer):
    """§2.2: a member made captain runs the event but cannot change who else
    does."""
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
    body = cm.get(f"/events/{ev.pk}/manage/details/").content.decode()
    body += cm.get(f"/events/{ev.pk}/manage/publish/").content.decode()
    assert "Appoint captain" not in body and "An officer appoints and removes captains." in body
    assert cm.post(f"/events/{ev.pk}/captains/add/", {"user": other.pk}).status_code == 404
    assert cm.post(f"/events/{ev.pk}/captains/{officer.pk}/remove/").status_code == 404
    assert set(ev.captaincies.values_list("user", flat=True)) == {officer.pk, mem.pk}
    # Nor can they cancel the event: only an officer can.
    assert "Cancel this event" not in body and "An officer can cancel this event." in body
    r = cm.post(f"/events/{ev.pk}/cancel/", {"confirm": "yes", "reason": "Rained out"})
    ev.refresh_from_db()
    assert r.status_code == 404 and ev.state == "draft"


def test_the_last_captain_cannot_be_removed(officer):
    c = _as(officer)
    ev = _build(c)
    c.post(f"/events/{ev.pk}/captains/{officer.pk}/remove/")
    assert ev.captaincies.filter(user=officer).exists()
    assert "Appoint captain" in c.get(f"/events/{ev.pk}/manage/publish/").content.decode()


def test_the_event_form_says_preferred_license_class(officer):
    body = _as(officer).get("/events/new/").content.decode()
    assert "Preferred license class" in body and "Min license class" not in body


def test_duplicate_moves_everything_to_the_new_start(officer):
    """FR-42: the officer supplies the new start and the copy shifts with it: start and end, on-air
    hours, slots and openings by the same amount; it carries the eligibility rules, event-wide
    and per slot, and every field."""
    from datetime import timedelta

    from apps.events.models import EligibilityRule, OnAirRange, Opening

    c = _as(officer)
    ev = _build(c)
    ev.reminder_hours_before = 6
    ev.save()
    p = ev  # its start and end (A32)
    OnAirRange.objects.create(event=ev, start=p.start, end=p.start + timedelta(hours=6))
    Opening.objects.create(
        event=ev,
        role="operator",
        opens_at=p.start - timedelta(days=7),
        announce=True,
        announced_at=p.start - timedelta(days=7),
    )
    first = Slot.objects.filter(position__location__event=ev).order_by("start", "pk").first()
    EligibilityRule.objects.create(event=ev, role="operator", min_license_class="general")
    EligibilityRule.objects.create(event=ev, slot=first, role="observer", minors_allowed=False)
    week = timedelta(days=7)
    new_start = p.start + week
    r = c.post(f"/events/{ev.pk}/duplicate/", {"start": f"{new_start:%Y-%m-%dT%H:%M}"})
    copy = Event.objects.get(duplicated_from=ev)
    assert r["Location"] == f"/events/{copy.pk}/manage/span/"
    cp = copy
    assert (cp.start, cp.end) == (p.start + week, p.end + week)
    assert [(a.start, a.end) for a in copy.on_air_ranges.all()] == [
        (p.start + week, p.start + week + timedelta(hours=6))
    ]
    old = sorted(Slot.objects.filter(position__location__event=ev).values_list("start", "end"))
    new = sorted(Slot.objects.filter(position__location__event=copy).values_list("start", "end"))
    assert new == [(a + week, b + week) for a, b in old]
    o = copy.openings.get()
    assert (
        o.opens_at == p.start - timedelta(days=7) + week and o.announce and o.announced_at is None
    )
    assert copy.eligibility_rules.get(slot__isnull=True).min_license_class == "general"
    moved = copy.eligibility_rules.get(slot__isnull=False)
    assert moved.slot.position.location.event == copy and moved.slot.start == first.start + week
    assert not moved.minors_allowed and copy.reminder_hours_before == 6


def test_duplicate_asks_when_the_copy_starts(officer):
    """FR-42: one dialog on the page, opened from the event's menu and from the Publish step,
    with this event's start offered as the copy's."""
    c = _as(officer)
    ev = _build(c)
    body = c.get(f"/events/{ev.pk}/manage/publish/").content.decode()
    start = ev.start
    assert body.count('commandfor="dup-dlg" command="show-modal"') == 2
    assert (
        f'name="start" type="datetime-local" autocomplete="off" value="{start:%Y-%m-%dT%H:%M}" data-instant'
        in body
    )


def test_duplicate_refuses_a_start_it_cannot_read(officer):
    c = _as(officer)
    ev = _build(c)
    r = c.post(f"/events/{ev.pk}/duplicate/", {"start": "next spring"}, follow=True)
    assert not Event.objects.filter(duplicated_from=ev).exists()
    assert "Nothing was copied" in r.content.decode()


def test_slot_close_cancel_duplicate_and_cancel_event(officer):
    c = _as(officer)
    ev = _build(c)
    s = Slot.objects.filter(position__location__event=ev, kind="operating").first()
    c.post(f"/events/slot/{s.pk}/toggle/", {"what": "close"})
    s.refresh_from_db()
    assert s.closed
    c.post(f"/events/slot/{s.pk}/toggle/", {"what": "cancel", "confirmed": "yes"})
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
    are made. Beta users: "add a way to add more slots after generating"."""
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

    # Refused, and the reason is beside the field: a clash, and an operating slot outside the
    # on-air hours (A32).
    assert (
        "already has a slot at Sat, Jun 27, 2026, 8:00–9:00 PM UTC"
        in add("2026-06-27T20:30").content.decode()
    )
    assert "inside the on-air hours" in add("2026-06-29T10:00").content.decode()
    assert Slot.objects.filter(position__location__event=ev).count() == before

    # A training slot after the contest, with three operators' seats.
    r = add("2026-06-29T10:00", minutes="120", kind="training", cap_operator="3")
    assert r.status_code == 302 and r["Location"] == f"/events/{ev.pk}/manage/slots/"
    slot = Slot.objects.get(position=run, kind="training")
    assert (slot.end - slot.start) == timedelta(hours=2)
    assert {c.role: c.capacity for c in slot.capacities.all()} == {"operator": 3}
    assert AuditLog.objects.get(action="slot.added").after["seats"] == {"operator": 3}
    assert Slot.objects.filter(position__location__event=ev).count() == before + 1
    assert signed.signups.count() == 1, "nothing else on the grid changes"

    # Re-timing an empty slot: cancel it, and its time is free to add again.
    empty = Slot.objects.get(position=run, start__hour=20, kind="operating")
    c.post(f"/events/slot/{empty.pk}/toggle/", {"what": "cancel", "confirmed": "yes"})
    assert add("2026-06-27T20:30", minutes="30").status_code == 302

    member = User.objects.create_user("mem@example.org", "pw-Testing-123", groups=["member"])
    assert _as(member).post(f"/events/{ev.pk}/slots/add/", {}).status_code == 404


def test_a_canceled_upcoming_event_is_tagged_in_the_house_spelling(officer):
    """Found in acceptance testing: the Events list tagged an upcoming canceled
    event "Cancelled", from the state's label, beside a "Canceled." banner."""
    ev = Event.objects.create(title="Sprint", state=Event.State.CANCELLED, created_by=officer)
    start = timezone.now() + timedelta(days=10)
    ev.start, ev.end = start, start + timedelta(hours=4)
    ev.save(update_fields=["start", "end"])
    body = _as(officer).get("/events/").content.decode()
    # a badge in the canceled tone; the word is what the house spells
    assert '<span class="tag bad">Canceled</span>' in body and "Cancelled" not in body


def test_the_events_list_works_out_coverage_only_for_live_events(officer, monkeypatch):
    """On dev, hundreds of canceled test events each had their coverage worked out slot by
    slot on every visit to the Events list. Only a published or locked event has any."""
    from apps.events.services import roster

    asked = []
    real = roster.coverage
    monkeypatch.setattr(
        roster, "coverage", lambda e, now=None: asked.append(e.title) or real(e, now)
    )
    start = timezone.now() + timedelta(days=10)
    for title, state in (
        ("Gone", Event.State.CANCELLED),
        ("Plan", Event.State.DRAFT),
        ("On", Event.State.PUBLISHED),
    ):
        ev = Event.objects.create(title=title, state=state, created_by=officer)
        ev.start, ev.end = start, start + timedelta(hours=4)
        ev.save(update_fields=["start", "end"])
    assert _as(officer).get("/events/").status_code == 200
    assert asked == ["On"]


def _fill(c, ev, **extra):
    return c.post(
        f"/events/{ev.pk}/slots/generate/",
        {
            "minutes": "60",
            "setup_slots": "1",
            "breakdown_slots": "1",
            "cap_operator": "2",
            "cap_mentor": "0",
            "mode": "fill",
            **extra,
        },
        follow=True,
    )


def test_after_sign_ups_a_longer_event_gets_slots_and_nothing_else_moves(officer):
    """The generator adds to the empty hours without replacing the grid."""
    from apps.events.models import SignUp
    from apps.ops.models import AuditLog

    c = _as(officer)
    ev = _build(c)
    s = Slot.objects.filter(position__location__event=ev, kind="operating").first()
    su = SignUp.objects.create(slot=s, user=officer, role="operator")
    before = set(Slot.objects.filter(position__location__event=ev).values_list("pk", "start"))
    page = c.get(f"/events/{ev.pk}/manage/slots/").content.decode()
    assert "Add slots to the empty hours" in page and "Regenerate slots" not in page

    # four hours more on the end (A32: one start and end, made longer); the breakdown slot already
    # holds the first, so three are filled
    start = ev.end + timedelta(hours=1)
    ev.end = start + timedelta(hours=3)
    ev.save(update_fields=["end"])
    body = " ".join(_fill(c, ev).content.decode().split())
    after = Slot.objects.filter(position__location__event=ev)
    assert set(after.values_list("pk", "start")) >= before and after.count() == len(before) + 6
    new = after.filter(start__gte=start)
    assert {x.kind for x in new} == {"operating"} and all(
        x.capacities.get().capacity == 2 for x in new
    )
    assert SignUp.objects.filter(pk=su.pk).exists()
    assert "Added 6 slots to the empty hours across 2 positions." in body
    assert AuditLog.objects.filter(action="slots.generated", after__mode="fill").exists()

    body = " ".join(_fill(c, ev).content.decode().split())
    assert "Every hour you asked for already has a slot; nothing added." in body
    assert after.count() == len(before) + 6


def test_before_sign_ups_both_fill_and_regenerate_are_offered(officer):
    c = _as(officer)
    ev = _build(c)
    page = c.get(f"/events/{ev.pk}/manage/slots/").content.decode()
    assert "Add slots to the empty hours" in page and "Regenerate slots" in page


def _operating(ev):
    return Slot.objects.filter(position__location__event=ev, kind="operating", cancelled=False)


def test_regenerate_counts_only_the_slots_on_the_roster(officer):
    """A canceled slot is not on the roster, so Replace the whole grid? does not count it, though
    Regenerate clears it too."""
    c = _as(officer)
    ev = _build(c)
    _operating(ev).filter(pk=_operating(ev).first().pk).update(cancelled=True)
    body = c.post(
        f"/events/{ev.pk}/slots/generate/",
        {
            "minutes": "60",
            "setup_slots": "1",
            "breakdown_slots": "1",
            "cap_operator": "2",
            "cap_mentor": "0",
            "mode": "replace",
        },
    ).content.decode()
    assert "the 51 slots on the roster now" in body  # 52 made, 1 canceled


# Publishing waits for the required steps: an event with only a title had gone on every member's
# calendar, announceable to all.
def _bare(c, **extra):
    c.post(
        "/events/new/",
        {
            "title": "Bare",
            "type": "contest",
            "description_html": "",
            "rules_url": "",
            "min_license_class": "",
            **extra,
        },
    )
    ev = Event.objects.get(title="Bare")
    ev.locations.all().delete()  # bare: not even the default club station (276)
    return ev


def test_publishing_is_refused_until_the_required_steps_are_done(officer):
    c = _as(officer)
    ev = _bare(c)
    r = c.post(f"/events/{ev.pk}/publish/", {"from": "manage", "announce": "yes"}, follow=True)
    ev.refresh_from_db()
    assert ev.state == "draft"
    assert (
        "Not published: Event start and end, Locations and Slots are not done yet."
        in r.content.decode()
    )


def _publish_controls(page: str) -> bool:
    """Whether a page offers the Publish form: its button or its Announce box."""
    return ">Publish</button>" in page or 'name="announce"' in page


def test_a_line_stands_in_place_of_publish_while_steps_are_missing(officer):
    """In place of a greyed Publish button, a line says what is missing: a greyed button
    explains nothing on a phone."""
    c = _as(officer)
    ev = _bare(c)
    body = c.get(f"/events/{ev.pk}/manage/publish/").content.decode()
    assert (
        "Not ready to publish: Event start and end, Locations and Slots are not done yet." in body
    )
    assert not _publish_controls(body)
    banner = c.get(f"/events/{ev.pk}/").content.decode()  # the Draft banner's too
    assert "Not ready to publish:" in banner and not _publish_controls(banner)
    built = _build(c)  # every required step done, moved to the future (its June has passed)
    soon = timezone.now() + timedelta(days=30)
    Event.objects.filter(pk=built.pk).update(start=soon, end=soon + timedelta(days=1))
    body = c.get(f"/events/{built.pk}/manage/publish/").content.decode()
    assert '<button type="submit">Publish</button>' in body and "pub-missing" not in body


def test_a_display_only_event_publishes_with_nothing_set_up(officer):
    c = _as(officer)
    ev = _bare(c, display_only="on", repeats="weekly", repeat_weekday="1", meets_at="20:00")
    c.post(f"/events/{ev.pk}/publish/", {"from": "manage"})
    ev.refresh_from_db()
    assert ev.state == "published"


def test_an_event_with_no_slots_never_says_every_slot_is_spoken_for(officer):
    """One published before the gate above may have none at all."""
    c = _as(officer)
    ev = _bare(c)
    Event.objects.filter(pk=ev.pk).update(state="published")
    m = User.objects.create_user(
        "m@example.org", "pw-Testing-123", groups=["member"], first_name="M", last_name="M"
    )
    body = _as(m, view="member").get(f"/events/{ev.pk}/").content.decode()  # as a member reads it
    assert "No slots yet." in body and "Every slot is spoken for" not in body


# Dates in the past: a period that has already ended is allowed, with a warning
# that names it, since a wrong year is the likely cause; an event whose every period has ended is
# not published, so nobody is told about an event that is over.
def test_a_start_and_end_that_has_ended_is_saved_with_a_warning(officer):
    c = _as(officer)
    ev = _bare(c)
    start = (timezone.now() - timedelta(days=30)).replace(minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=4)
    r = c.post(
        f"/events/{ev.pk}/span/",
        {"start": f"{start:%Y-%m-%dT%H:%M}", "end": f"{end:%Y-%m-%dT%H:%M}"},
        follow=True,
    )
    ev.refresh_from_db()
    assert ev.end == end
    assert f"This event ended on {when.local(end, year=True)}, before now. Check the year." in (
        r.content.decode()
    )


def test_an_event_that_has_ended_is_not_published(officer):
    c = _as(officer)
    ev = _build(c)  # its start and end are in June 2026
    Event.objects.filter(pk=ev.pk).update(
        start=timezone.now() - timedelta(days=30), end=timezone.now() - timedelta(days=29)
    )
    ev.refresh_from_db()
    end = ev.end
    said = f"it ended on {when.local(end, year=True)}."
    body = c.get(f"/events/{ev.pk}/manage/publish/").content.decode()
    assert f"Not ready to publish: {said}" in body and not _publish_controls(body)
    r = c.post(f"/events/{ev.pk}/publish/", {"from": "manage", "announce": "yes"}, follow=True)
    ev.refresh_from_db()
    assert ev.state == "draft" and f"Not published: {said}" in r.content.decode()


def test_a_completed_event_is_under_past_even_before_its_dates_end(officer):
    """FR-44: completed by a captain, or once its last slot has ended, whichever comes first; a
    member then finds it under Past, not Upcoming."""
    c = _as(officer)
    ev = _build(c)
    soon = timezone.now() + timedelta(days=3)
    Event.objects.filter(pk=ev.pk).update(start=soon, end=soon + timedelta(days=1))
    c.post(f"/events/{ev.pk}/publish/", {"from": "manage"})
    c.post(f"/events/{ev.pk}/state/", {"what": "complete"})
    ev.refresh_from_db()
    assert ev.state == "completed"
    m = User.objects.create_user(
        "m@example.org", "pw-Testing-123", groups=["member"], first_name="M", last_name="M"
    )
    page = _as(m, view="member").get("/events/").content.decode()
    past = page.split('aria-labelledby="p"', 1)[1] if 'aria-labelledby="p"' in page else ""
    assert "Field Day" in past


def test_a_new_event_starts_at_the_club_station_and_a_net_has_no_location(officer):
    """FR-51: the club station, named and described from Settings, with one position; a
    display-only event gets none."""
    for key, value in {
        "club.station_location_name": "The shack",
        "club.station_address": "Room 596",
        "club.station_directions_html": "<p>Fifth floor.</p>",
    }.items():
        ClubSetting.objects.update_or_create(key=key, defaults={"value": value})
    c = _as(officer)
    c.post("/events/new/", {"title": "Sprint", "type": "contest"})
    loc = Event.objects.get(title="Sprint").locations.get()
    assert (loc.name, loc.address, loc.directions_html, loc.is_club_station) == (
        "The shack",
        "Room 596",
        "<p>Fifth floor.</p>",
        True,
    )
    assert [p.name for p in loc.positions.all()] == ["Station"]
    c.post(
        "/events/new/",
        {
            "title": "Net",
            "type": "net",
            "display_only": "on",
            "repeats": "weekly",
            "repeat_weekday": "1",
            "meets_at": "20:00",
        },
    )
    assert not Event.objects.get(title="Net").locations.exists()
