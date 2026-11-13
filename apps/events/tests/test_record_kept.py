"""The record of an event that ran is kept (SK, 2026-11-12): a sign-up with attendance, or on a
slot that has ended, or on an event that is over, is not deleted by "I cannot make it" (#251);
a waitlist offer on a canceled slot or event cannot be taken (#252); an event that is over is not
canceled, and a canceled one is not canceled twice (#255). Tests written before the code."""

from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.comms.models import Outbox
from apps.events.models import Event, SignUp, Waitlist
from apps.events.services import waitlist
from apps.events.services.notify import confirm_token

from .test_phase2 import _event, _user

pytestmark = pytest.mark.django_db


def _client(user):
    c = Client()
    c.force_login(user)
    return c


# ----------------------------------------------------------------------------------- #251 ---


def test_a_checked_in_sign_up_on_a_completed_event_is_not_cancelled(officer):
    now = timezone.now()
    mem = _user("m1@example.org")
    ev, (slot, _) = _event(now - timedelta(hours=3), captain=officer)
    su = SignUp.objects.create(slot=slot, user=mem, role="operator", checked_in_at=slot.start)
    Event.objects.filter(pk=ev.pk).update(state=Event.State.COMPLETED)
    c = _client(mem)
    page = c.get(f"/events/{ev.pk}/slot/{slot.pk}/").content.decode()
    assert "I cannot make it" not in page
    r = c.post(f"/events/signup/{su.pk}/cancel/", {"confirmed": "yes"}, follow=True)
    assert SignUp.objects.filter(pk=su.pk).exists()
    assert "stays in the record" in r.content.decode()
    assert not Outbox.objects.filter(subject__startswith="Late cancellation").exists()


def test_a_sign_up_on_a_slot_that_has_ended_is_not_cancelled_by_the_member():
    now = timezone.now()
    mem = _user("m2@example.org")
    ev, (slot, _) = _event(now - timedelta(hours=3))
    su = SignUp.objects.create(slot=slot, user=mem, role="operator")
    _client(mem).post(f"/events/signup/{su.pk}/cancel/", {"confirmed": "yes"})
    assert SignUp.objects.filter(pk=su.pk).exists()


def test_a_checked_in_sign_up_on_a_future_slot_of_a_completed_event_is_kept():
    now = timezone.now()
    mem = _user("m3@example.org")
    ev, (slot, _) = _event(now + timedelta(days=1), state=Event.State.COMPLETED)
    su = SignUp.objects.create(slot=slot, user=mem, role="operator", checked_in_at=now)
    _client(mem).post(f"/events/signup/{su.pk}/cancel/", {"confirmed": "yes"})
    assert SignUp.objects.filter(pk=su.pk).exists()


def test_the_cannot_make_it_link_in_a_reminder_keeps_a_sign_up_on_a_completed_event():
    """A slot that has ended already makes the link invalid; an event completed early does not."""
    now = timezone.now()
    mem = _user("m4@example.org")
    ev, (slot, _) = _event(now + timedelta(days=1), state=Event.State.COMPLETED)
    su = SignUp.objects.create(slot=slot, user=mem, role="operator")
    r = Client().post(f"/events/cannot/{confirm_token(su)}/")
    assert SignUp.objects.filter(pk=su.pk).exists()
    assert "stays in the record" in r.content.decode()


def test_a_captain_cannot_remove_someone_whose_attendance_is_recorded(officer):
    now = timezone.now()
    mem = _user("m5@example.org")
    ev, (slot, _) = _event(now - timedelta(minutes=30), captain=officer)
    su = SignUp.objects.create(slot=slot, user=mem, role="operator", checked_in_at=slot.start)
    c = _client(officer)
    page = c.get(f"/events/{ev.pk}/slot/{slot.pk}/").content.decode()
    assert f"/events/signup/{su.pk}/remove/" not in page
    c.post(f"/events/signup/{su.pk}/cancel/", {"confirmed": "yes", "reason": "Left early"})
    assert SignUp.objects.filter(pk=su.pk).exists()


def test_a_member_still_leaves_a_future_slot_on_a_published_event():
    now = timezone.now()
    mem = _user("m6@example.org")
    ev, (slot, _) = _event(now + timedelta(days=2))
    su = SignUp.objects.create(slot=slot, user=mem, role="observer")
    _client(mem).post(f"/events/signup/{su.pk}/cancel/", {"confirmed": "yes"})
    assert not SignUp.objects.filter(pk=su.pk).exists()


# ----------------------------------------------------------------------------------- #252 ---


def _offered(officer):
    """A full operator seat with W waiting; the holder leaves, and W is offered the place."""
    now = timezone.now()
    holder, w = _user("h@example.org"), _user("w@example.org")
    ev, (slot, _) = _event(now + timedelta(days=2), captain=officer)
    su = SignUp.objects.create(slot=slot, user=holder, role="operator")
    entry = waitlist.join(w, slot, "operator")
    _client(holder).post(f"/events/signup/{su.pk}/cancel/", {"confirmed": "yes"})
    entry.refresh_from_db()
    assert entry.state == Waitlist.State.OFFERED
    return ev, slot, w, entry


def test_an_offer_on_a_canceled_slot_cannot_be_taken(officer):
    ev, slot, w, entry = _offered(officer)
    _client(officer).post(f"/events/slot/{slot.pk}/toggle/", {"what": "cancel"})
    slot.refresh_from_db()
    assert slot.cancelled
    c = _client(w)
    page = c.get(f"/events/waitlist/{entry.pk}/accept/").content.decode()
    assert "Take the place" not in page
    r = c.post(f"/events/waitlist/{entry.pk}/accept/")
    assert not SignUp.objects.filter(slot=slot, user=w).exists()
    assert (
        r.status_code in (200, 302)
        and c.get(r.url if r.status_code == 302 else "/").status_code != 404
    )


def test_an_offer_on_a_canceled_event_cannot_be_taken(officer):
    ev, slot, w, entry = _offered(officer)
    Event.objects.filter(pk=ev.pk).update(state=Event.State.CANCELLED)
    assert waitlist.accept(w, entry) is None
    assert not SignUp.objects.filter(slot=slot, user=w).exists()


def test_a_canceled_slot_offers_its_place_to_nobody(officer):
    now = timezone.now()
    holder, w = _user("h2@example.org"), _user("w2@example.org")
    ev, (slot, _) = _event(now + timedelta(days=2), captain=officer)
    SignUp.objects.create(slot=slot, user=holder, role="operator")
    entry = waitlist.join(w, slot, "operator")
    SignUp.objects.filter(slot=slot).delete()
    slot.cancelled = True
    slot.save(update_fields=["cancelled"])
    assert waitlist.offer_next(slot, "operator") is None
    entry.refresh_from_db()
    assert entry.state == Waitlist.State.PENDING


# ----------------------------------------------------------------------------------- #255 ---


def test_a_completed_event_is_not_canceled(officer):
    ev, _ = _event(timezone.now() - timedelta(days=1), captain=officer, state=Event.State.COMPLETED)
    c = _client(officer)
    page = c.get(f"/events/{ev.pk}/manage/publish/").content.decode()
    assert "Cancel this event" not in page
    c.post(f"/events/{ev.pk}/cancel/", {"confirm": "yes", "reason": "Mistake"})
    ev.refresh_from_db()
    assert ev.state == Event.State.COMPLETED


def test_a_canceled_event_is_not_canceled_twice(officer):
    now = timezone.now()
    mem = _user("m7@example.org")
    ev, (slot, _) = _event(now + timedelta(days=2), captain=officer)
    SignUp.objects.create(slot=slot, user=mem, role="operator")
    c = _client(officer)
    c.post(f"/events/{ev.pk}/cancel/", {"confirm": "yes", "reason": "Storm"})
    c.post(f"/events/{ev.pk}/cancel/", {"confirm": "yes", "reason": "Storm"})
    ev.refresh_from_db()
    assert ev.state == Event.State.CANCELLED
    assert Outbox.objects.filter(user=mem, subject__startswith="Event canceled").count() == 1


# --------------------------------------------------------- compliance review, 2026-11-12 ---


def test_a_slot_under_way_with_attendance_is_not_canceled(officer):
    """Canceling deleted every sign-up in the slot, attendance included; hours and participation
    skip a canceled slot as well."""
    now = timezone.now()
    ev, (slot, _) = _event(now - timedelta(minutes=30), captain=officer)
    here = SignUp.objects.create(
        slot=slot, user=_user("c1@example.org"), role="operator", checked_in_at=now
    )
    SignUp.objects.create(slot=slot, user=_user("c2@example.org"), role="mentor")
    c = _client(officer)
    assert "Cancel this slot" not in c.get(f"/events/{ev.pk}/slot/{slot.pk}/").content.decode()
    r = c.post(
        f"/events/slot/{slot.pk}/toggle/",
        {"what": "cancel", "confirmed": "yes", "reason": "Storm"},
        follow=True,
    )
    slot.refresh_from_db()
    assert not slot.cancelled
    assert (
        SignUp.objects.filter(slot=slot).count() == 2 and SignUp.objects.filter(pk=here.pk).exists()
    )
    assert "stays in the record" in r.content.decode()
    assert not Outbox.objects.filter(subject__icontains="cancel").exists()


def test_removing_access_keeps_a_sign_up_with_attendance(officer):
    """FR-91 withdraws future sign-ups; one checked in to a slot under way is attendance."""
    from apps.events.services.notify import access_removed

    now = timezone.now()
    mem = _user("c3@example.org")
    ev, (on_now, later) = _event(now - timedelta(minutes=30), captain=officer)
    kept = SignUp.objects.create(slot=on_now, user=mem, role="operator", checked_in_at=now)
    gone = SignUp.objects.create(slot=later, user=mem, role="operator")
    assert access_removed(officer, mem) == 1
    assert SignUp.objects.filter(pk=kept.pk).exists()
    assert not SignUp.objects.filter(pk=gone.pk).exists()
