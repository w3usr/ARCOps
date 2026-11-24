"""Bugs from a gap analysis: seats that open without a cancellation reach the waitlist, and a merge
keeps a live offer; Display only cannot change under an event's slots or once it is out of draft,
either way; no "Not checked in" notice for a canceled event; a merge keeps the later slot's own
rules and closed state, and removing a period clips the on-air hours. Written first."""

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


# -----------------------------------------------------------------------------------------------


def test_more_seats_offer_the_place_to_the_first_waiting(
    officer, django_capture_on_commit_callbacks
):
    now = timezone.now()
    holder, w = _user("h@example.org"), _user("w@example.org")
    ev, (slot, _) = _event(now + timedelta(days=2), captain=officer)
    SignUp.objects.create(slot=slot, user=holder, role="operator")
    entry = waitlist.join(w, slot, "operator")
    with django_capture_on_commit_callbacks(
        execute=True
    ):  # the offer goes once the seats are saved
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


# -----------------------------------------------------------------------------------------------


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
    r = _client(officer).post(
        f"/events/{ev.pk}/details/",
        _details(ev, display_only="on", repeats="weekly", repeat_weekday="1", meets_at="20:00"),
    )
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
    _client(officer).post(
        f"/events/{ev.pk}/details/",
        _details(ev, display_only="on", repeats="weekly", repeat_weekday="1", meets_at="20:00"),
    )
    ev.refresh_from_db()
    assert ev.display_only


# -----------------------------------------------------------------------------------------------


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


# -----------------------------------------------------------------------------------------------


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


def test_shortening_the_start_and_end_clips_the_on_air_hours(officer):
    """As A32 has it: the on-air hours stay inside the event's start and end."""
    start = timezone.now().replace(second=0, microsecond=0) + timedelta(days=30)
    ev, _ = _event(start, hours=8, captain=officer, state=Event.State.DRAFT)
    OnAirRange.objects.create(event=ev, start=start, end=start + timedelta(hours=1))
    OnAirRange.objects.create(
        event=ev, start=start + timedelta(hours=6), end=start + timedelta(hours=7)
    )
    Slot.objects.filter(position__location__event=ev).delete()
    end = start + timedelta(hours=2)
    _client(officer).post(
        f"/events/{ev.pk}/span/",
        {"start": f"{start:%Y-%m-%dT%H:%M}", "end": f"{end:%Y-%m-%dT%H:%M}"},
    )
    assert list(ev.on_air_ranges.values_list("start", flat=True)) == [start]


# -----------------------------------------------------------------------------------------------


def test_losing_access_leaves_every_waitlist_and_each_place_freed_is_offered(officer):
    """FR-118, FR-57: a deleted account leaves the waitlists, and an offer passes over anyone
    without access; a place freed by suspension is offered."""
    from apps.accounts.services import delete_account, suspend

    now = timezone.now()
    holder, gone, lost, nxt = (_user(f"{n}@example.org") for n in ("hold", "gone", "lost", "next"))
    ev, (slot, _) = _event(now + timedelta(days=2), captain=officer)
    SignUp.objects.create(slot=slot, user=holder, role="operator")  # the one Operator seat
    for u in (gone, lost, nxt):
        waitlist.join(u, slot, "operator")
    delete_account(officer, gone, "testing")
    assert Waitlist.objects.get(user=gone).state == Waitlist.State.WITHDRAWN
    lost.groups.clear()  # no access, though still pending: passed over
    suspend(officer, holder, "testing")
    assert not SignUp.objects.filter(slot=slot, user=holder).exists()
    assert Waitlist.objects.get(user=lost).state == Waitlist.State.PENDING
    assert Waitlist.objects.get(user=nxt).state == Waitlist.State.OFFERED


def test_one_place_per_person_in_a_slot_and_eligibility_again_at_acceptance(officer):
    """Holding the slot, a member cannot wait for another role in it; an offer to someone
    already in the slot or no longer eligible is not marked taken, and passes on; eligibility is
    asked again at acceptance."""
    from apps.events.models import EligibilityRule

    now = timezone.now()
    holder, mem, w, x = (_user(f"{n}@example.org") for n in ("h2", "m2", "w2", "x2"))
    ev, (slot, _) = _event(now + timedelta(days=2), captain=officer)
    SignUp.objects.create(slot=slot, user=holder, role="operator")
    SignUp.objects.create(slot=slot, user=mem, role="observer")
    _client(mem).post(f"/events/slot/{slot.pk}/waitlist/", {"role": "operator"})
    assert not Waitlist.objects.filter(user=mem).exists()
    early = Waitlist.objects.create(slot=slot, user=mem, role="operator")  # joined before this
    later = Waitlist.objects.create(slot=slot, user=w, role="operator")
    last = Waitlist.objects.create(slot=slot, user=x, role="operator")
    SignUp.objects.filter(user=holder).delete()
    waitlist.on_place_opened(slot, "operator")
    early.refresh_from_db()
    assert early.state == Waitlist.State.OFFERED and waitlist.accept(mem, early) is None
    assert SignUp.objects.get(slot=slot, user=mem).role == "observer"
    later.refresh_from_db()
    assert later.state == Waitlist.State.OFFERED  # passed on
    EligibilityRule.objects.create(event=ev, role="operator", categories=["faculty"])
    assert waitlist.accept(w, later) is None  # a student, no longer eligible
    last.refresh_from_db()
    assert last.state == Waitlist.State.OFFERED
