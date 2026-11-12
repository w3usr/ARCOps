"""Bugs from the 2026-11-12 gap analysis, fixed at SK's word ("let's work thru bugs"): seats that
open without a cancellation reach the waitlist, and a merge keeps a live offer (#253); Display
only cannot change under an event's slots or once it is out of draft (#254, SK: "Refuse both
ways"); no "Not checked in" notice for a canceled event (#256); a merge keeps the later slot's own
rules and closed state, and removing a period clips the on-air hours (#260). Written first."""

from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.comms.models import Outbox
from apps.events.models import EligibilityRule, Event, OnAirRange, SignUp, Slot, Waitlist
from apps.events.services import reshape, waitlist
from apps.events.services.notify import notify_no_shows

from .test_phase2 import _event, _user

pytestmark = pytest.mark.django_db


def _client(user):
    c = Client()
    c.force_login(user)
    return c


# ----------------------------------------------------------------------------------- #253 ---


def test_more_seats_offer_the_place_to_the_first_waiting(officer):
    now = timezone.now()
    holder, w = _user("h@example.org"), _user("w@example.org")
    ev, (slot, _) = _event(now + timedelta(days=2), captain=officer)
    SignUp.objects.create(slot=slot, user=holder, role="operator")
    entry = waitlist.join(w, slot, "operator")
    _client(officer).post(
        f"/events/{ev.pk}/slot/{slot.pk}/seats/", {"cap_operator": "3", "cap_mentor": "1"}
    )
    entry.refresh_from_db()
    assert entry.state == Waitlist.State.OFFERED
    assert Outbox.objects.filter(user=w, subject__contains="place opened").exists()


def test_a_merge_offers_a_seat_it_opens_to_the_waiting(officer):
    now = timezone.now()
    a_holder, b_holder, w = (_user(f"{n}@example.org") for n in ("ah", "bh", "bw"))
    ev, (first, second) = _event(now + timedelta(days=2), captain=officer)
    first.capacities.filter(role="operator").update(capacity=3)
    SignUp.objects.create(slot=first, user=a_holder, role="operator")
    SignUp.objects.create(slot=second, user=b_holder, role="operator")  # B's one seat is full
    waitlist.join(w, second, "operator")
    reshape.merge(officer, first, second)
    entry = Waitlist.objects.get(user=w)
    assert entry.slot_id == first.pk and entry.state == Waitlist.State.OFFERED


def test_a_merge_keeps_an_offer_and_its_link(officer):
    now = timezone.now()
    holder, w = _user("oh@example.org"), _user("ow@example.org")
    ev, (first, second) = _event(now + timedelta(days=2), captain=officer)
    su = SignUp.objects.create(slot=second, user=holder, role="operator")
    entry = waitlist.join(w, second, "operator")
    _client(holder).post(f"/events/signup/{su.pk}/cancel/", {"confirmed": "yes"})
    entry.refresh_from_db()
    assert entry.state == Waitlist.State.OFFERED
    reshape.merge(officer, first, second)
    entry.refresh_from_db()  # the same row: the link in the offer still opens it
    assert entry.slot_id == first.pk and entry.state == Waitlist.State.OFFERED
    assert _client(w).get(f"/events/waitlist/{entry.pk}/accept/").status_code == 200
    assert waitlist.accept(w, entry) is not None


# ----------------------------------------------------------------------------------- #254 ---


def _details(ev, **change):
    data = {
        "title": ev.title,
        "type": "contest",
        "min_license_class": "",
        "display_timezone": "UTC",
    }
    data.update(change)
    return data


def test_an_event_with_slots_cannot_become_display_only(officer):
    ev, _ = _event(timezone.now() + timedelta(days=2), captain=officer)
    r = _client(officer).post(f"/events/{ev.pk}/details/", _details(ev, display_only="on"))
    ev.refresh_from_db()
    assert not ev.display_only
    assert "cannot become display only" in r.content.decode()


def test_a_published_display_only_event_cannot_take_a_roster(officer):
    ev = Event.objects.create(title="Net", state=Event.State.PUBLISHED, display_only=True)
    from apps.events.models import Captaincy

    Captaincy.objects.create(event=ev, user=officer)
    r = _client(officer).post(f"/events/{ev.pk}/details/", _details(ev))  # box unticked
    ev.refresh_from_db()
    assert ev.display_only
    assert "back to draft first" in r.content.decode()


def test_a_draft_may_still_change_display_only(officer):
    ev = Event.objects.create(title="Meeting", state=Event.State.DRAFT)
    from apps.events.models import Captaincy

    Captaincy.objects.create(event=ev, user=officer)
    _client(officer).post(f"/events/{ev.pk}/details/", _details(ev, display_only="on"))
    ev.refresh_from_db()
    assert ev.display_only


# ----------------------------------------------------------------------------------- #256 ---


def test_no_not_checked_in_notice_for_a_canceled_event(officer):
    now = timezone.now()
    mem = _user("ns@example.org")
    ev, (slot, _) = _event(now - timedelta(minutes=20), captain=officer)
    SignUp.objects.create(
        slot=slot, user=mem, role="operator", confirmed_at=now - timedelta(days=1)
    )
    Event.objects.filter(pk=ev.pk).update(state=Event.State.CANCELLED)
    assert notify_no_shows(now) == 0
    assert not Outbox.objects.filter(subject__startswith="Not checked in").exists()


# ----------------------------------------------------------------------------------- #260 ---


def test_a_merge_keeps_the_later_slots_own_rule_and_closed_state(officer):
    ev, (first, second) = _event(timezone.now() + timedelta(days=2), captain=officer)
    EligibilityRule.objects.create(event=ev, slot=second, role="observer", minors_allowed=False)
    Slot.objects.filter(pk=second.pk).update(closed=True)
    second.refresh_from_db()
    reshape.merge(officer, first, second)
    first.refresh_from_db()
    assert first.closed
    assert EligibilityRule.objects.filter(
        slot=first, role="observer", minors_allowed=False
    ).exists()


def test_removing_a_period_clips_the_on_air_hours(officer):
    from apps.events.models import OperatingPeriod

    start = timezone.now().replace(microsecond=0) + timedelta(days=30)
    ev, _ = _event(start, hours=2, captain=officer, state=Event.State.DRAFT)
    later = OperatingPeriod.objects.create(
        event=ev, start=start + timedelta(hours=5), end=start + timedelta(hours=8)
    )
    OnAirRange.objects.create(event=ev, start=start, end=start + timedelta(hours=1))
    OnAirRange.objects.create(
        event=ev, start=start + timedelta(hours=6), end=start + timedelta(hours=7)
    )
    _client(officer).post(f"/events/{ev.pk}/periods/{later.pk}/delete/")
    assert not OperatingPeriod.objects.filter(pk=later.pk).exists()
    assert list(ev.on_air_ranges.values_list("start", flat=True)) == [start]
