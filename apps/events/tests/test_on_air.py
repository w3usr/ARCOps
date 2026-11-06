"""On-air hours (#247, SK 2026-11-05; functional addendum A15): the operating periods are the
contest's span, and the club chooses the hours it means to be on the air inside them, as ranges
typed to the minute (#248, SK 2026-11-06; A16). The generator and the fill use those hours;
changing them never touches a slot."""

from datetime import UTC, datetime, timedelta

import pytest

from apps.events.models import Event, OnAirRange, OperatingPeriod, Slot
from apps.events.services.slots import (
    clip,
    merge,
    on_air,
    plan_slots,
    set_on_air,
)

from .test_manage import _as, _build

pytestmark = pytest.mark.django_db

H = timedelta(hours=1)
T = datetime(2026, 6, 27, 18, tzinfo=UTC)  # _build's period: Sat 18:00 to Sun 18:00


def _ev(c):
    ev = _build(c)
    return ev, list(ev.locations.get().positions.all())


def test_merge_and_clip():
    assert merge([(T, T + H), (T + H, T + 3 * H), (T + 5 * H, T + 6 * H)]) == [
        (T, T + 3 * H),
        (T + 5 * H, T + 6 * H),
    ]
    assert clip([(T - H, T + H)], [(T, T + 10 * H)]) == [(T, T + H)]
    assert clip([(T - 3 * H, T - H)], [(T, T + 10 * H)]) == []


def test_the_whole_event_until_the_club_chooses(officer):
    ev, _ = _ev(_as(officer))
    assert on_air(ev) == [(T, T + 24 * H)] and not OnAirRange.objects.filter(event=ev).exists()
    # choosing the whole of the periods is the same as choosing nothing, and is stored as nothing
    assert set_on_air(ev, [(T - H, T + 30 * H)]) == []
    assert not OnAirRange.objects.filter(event=ev).exists()


def test_the_generator_and_the_fill_use_the_on_air_hours(officer):
    c = _as(officer)
    ev, positions = _ev(c)
    Slot.objects.filter(position__location__event=ev).delete()
    set_on_air(ev, [(T, T + 6 * H), (T + 14 * H, T + 20 * H)])  # Sat 18-24, Sun 08-14
    planned = list(plan_slots(ev, positions[:1], 60, setup_slots=1, breakdown_slots=1))
    operating = [(a, b) for _, a, b, k in planned if k == "operating"]
    assert len(operating) == 12 and (T + 6 * H, T + 7 * H) not in operating
    setup = [a for _, a, _, k in planned if k == "setup"]
    breakdown = [b for _, _, b, k in planned if k == "breakdown"]
    assert setup == [T - H] and breakdown == [T + 21 * H]  # around the first and last on-air hour
    form = {
        "minutes": 60,
        "setup_slots": 0,
        "breakdown_slots": 0,
        "cap_operator": 1,
        "cap_mentor": 0,
    }
    page = c.get(f"/events/{ev.pk}/slots/generate/").content.decode()
    assert "in the on-air hours (2 stretches)" in page
    c.post(f"/events/{ev.pk}/slots/generate/", form)
    assert Slot.objects.filter(position__location__event=ev).count() == 2 * 12
    # widening the on-air hours never touches a slot; the fill adds only the new hours
    set_on_air(ev, [(T, T + 8 * H), (T + 14 * H, T + 20 * H)])
    assert Slot.objects.filter(position__location__event=ev).count() == 24
    c.post(f"/events/{ev.pk}/slots/generate/", form | {"mode": "fill"})
    assert Slot.objects.filter(position__location__event=ev).count() == 24 + 2 * 2


def test_saving_the_on_air_hours_from_the_slots_step(officer):
    c = _as(officer)
    ev, _ = _ev(c)
    url, step = f"/events/{ev.pk}/on-air/", f"/events/{ev.pk}/manage/slots/"
    body = c.get(step).content.decode()
    assert "On the air for the whole event: 24 hours." in body
    assert 'name="hour"' not in body and 'name="daily"' not in body  # no grid, no daily (#248)
    # the first range replaces the whole event; the next is added to it
    r = c.post(url, {"what": "range", "start": "2026-06-27T18:00", "end": "2026-06-27T21:00"})
    assert r.status_code == 302 and r["Location"] == step
    assert on_air(ev) == [(T, T + 3 * H)]
    c.post(url, {"what": "range", "start": "2026-06-28T04:00", "end": "2026-06-28T06:00"})
    assert on_air(ev) == [(T, T + 3 * H), (T + 10 * H, T + 12 * H)]
    body = c.get(step).content.decode()
    assert (
        "On the air 5 of 24 hours:" in body and "Sat 27 Jun 18:00 to Sat 27 Jun 21:00 UTC" in body
    )
    assert "slots fall outside the on-air hours" in body  # _build generated the whole event
    # one that touches a stretch joins it; one past the periods is cut to them
    c.post(url, {"what": "range", "start": "2026-06-27T21:00", "end": "2026-06-27T21:30"})
    assert on_air(ev)[0] == (T, T + 3 * H + timedelta(minutes=30))
    c.post(url, {"what": "range", "start": "2026-06-28T16:30", "end": "2026-06-28T20:00"})
    assert on_air(ev)[-1] == (T + 22 * H + timedelta(minutes=30), T + 24 * H)
    r = c.post(url, {"what": "range", "start": "2026-07-01T10:00", "end": "2026-07-01T12:00"})
    assert "That range falls outside every operating period." in r.content.decode()
    # one stretch removed, then the whole event again
    c.post(url, {"what": "remove", "i": "0"})
    assert on_air(ev)[0][0] == T + 10 * H
    c.post(url, {"what": "whole"})
    assert on_air(ev) == [(T, T + 24 * H)]
    # the grid's ticked hours and the same hours every day are gone (#248)
    assert c.post(url, {"what": "hours", "hour": [T.isoformat()]}).status_code == 404
    assert c.post(url, {"what": "daily", "daily": "20:00-22:00"}).status_code == 404


def test_duplicate_copies_the_on_air_hours(officer):
    c = _as(officer)
    ev, _ = _ev(c)
    set_on_air(ev, [(T, T + 6 * H)])
    c.post(f"/events/{ev.pk}/duplicate/")
    copy = Event.objects.exclude(pk=ev.pk).get()
    assert on_air(copy) == [(T, T + 6 * H)] and OperatingPeriod.objects.filter(event=copy).exists()


def test_a_member_who_is_not_a_captain_may_not_set_them(officer):
    from apps.accounts.models import User

    c = _as(officer)
    ev, _ = _ev(c)
    member = User.objects.create_user(
        "m@example.org", "pw-Testing-123", groups=["member"], first_name="M", last_name="M"
    )
    r = _as(member).post(f"/events/{ev.pk}/on-air/", {"what": "whole"})
    assert r.status_code == 404


def test_the_strip_tells_off_the_air_from_no_slot_yet(officer):
    """#247: an hour of the periods with no slot is marked, off the air or on the air with no
    slot yet, by shape as well as tone; the Key explains only the marks that are there."""
    import re

    c = _as(officer)
    ev, _ = _ev(c)
    page = c.get(f"/events/{ev.pk}/").content.decode()
    assert "sm-none" not in page and "sm-off" not in page  # every hour has its slot
    Slot.objects.filter(
        position__location__event=ev, start__gte=T + 6 * H, end__lte=T + 9 * H
    ).delete()
    set_on_air(ev, [(T, T + 7 * H), (T + 9 * H, T + 24 * H)])  # Sunday 01:00-03:00 off the air
    page = c.get(f"/events/{ev.pk}/").content.decode()
    strip = page.split('<div class="strip"', 1)[1].split("</div>\n", 1)[0]
    marks = re.findall(r'class="sm sm-(\w+)"', strip)
    assert marks.count("off") == 2 and marks.count("none") == 1  # Sunday 00:00 on the air, no slot
    assert '<span class="sm sm-off"></span>' in strip  # not a link
    key = page.split('id="roster-key-pop"', 1)[1].split("</ul>", 1)[0]
    assert "off the air: outside the club's on-air hours" in key
    assert "on the air, but no slot has been made for the hour yet" in key
