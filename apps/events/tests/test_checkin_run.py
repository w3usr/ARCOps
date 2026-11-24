"""A42: one tap checks a member in for the whole run of back-to-back slots."""

from datetime import timedelta

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.utils import timezone

from apps.accounts.models import Guardianship
from apps.events.models import ResponsibleAdult, SignUp, Slot
from apps.events.services import notify
from apps.events.tests.test_notify import _event, _user
from apps.ops.models import AuditLog

pytestmark = pytest.mark.django_db


def _as(user):
    c = Client()
    c.force_login(user)
    return c


def _signed(user, slots, **kw):
    return [SignUp.objects.create(slot=s, user=user, role="operator", **kw) for s in slots]


def test_one_post_checks_in_a_back_to_back_run_and_the_button_says_so():
    now = timezone.now()
    mem = _user("mem@example.org", first_name="Mo", last_name="Member")
    _, slots = _event(now + timedelta(minutes=10), hours=2)
    first, second = _signed(mem, slots, confirmed_at=now)
    c = _as(mem)
    page = c.get("/events/mine/").content.decode()
    assert "(2 slots)</button>" in page
    assert page.count("<h2>Check in:") == 1  # the later slot is not offered a tap of its own
    home = c.get("/").content.decode()
    assert "(2 slots)</button>" in home and "You can also check in now" not in home
    r = c.post(f"/events/signup/{first.pk}/checkin/", follow=True)
    assert "Checked in for 2 slots" in r.content.decode()
    for su in (first, second):
        su.refresh_from_db()
        assert su.checked_in_at and su.checked_in_by == mem
    assert AuditLog.objects.get(action="signup.checked_in").after == {"run": [first.pk, second.pk]}
    assert notify.notify_no_shows(slots[1].start + timedelta(minutes=20)) == 0


def test_a_gap_or_a_canceled_slot_ends_the_run():
    now = timezone.now()
    mem = _user("mem@example.org")
    _, slots = _event(now + timedelta(minutes=10), hours=4)
    a, b, c_, d = _signed(mem, slots)
    Slot.objects.filter(pk=slots[1].pk).update(cancelled=True)
    _as(mem).post(f"/events/signup/{a.pk}/checkin/")
    checked = set(SignUp.objects.exclude(checked_in_at=None).values_list("pk", flat=True))
    assert checked == {a.pk}
    b.delete()
    c_.delete()  # slot 3 does not follow slot 1 either
    assert a.checkin_run() == [a]


def test_an_adjacent_slot_in_another_event_is_not_in_the_run():
    now = timezone.now()
    mem = _user("mem@example.org")
    _, (one,) = _event(now + timedelta(minutes=10), hours=1)
    _, (other,) = _event(one.end, hours=1, title="Next Contest")
    here, there = _signed(mem, [one, other])
    assert here.checkin_run() == [here]
    _as(mem).post(f"/events/signup/{here.pk}/checkin/")
    there.refresh_from_db()
    assert there.checked_in_at is None


def test_a_captain_checks_in_the_run_and_a_member_may_still_leave_a_later_slot():
    now = timezone.now()
    cap = _user("cap@example.org", "officer")
    mem = _user("mem@example.org", first_name="Mo", last_name="Member")
    e, slots = _event(now - timedelta(minutes=10), hours=2, captain=cap)
    first, second = _signed(mem, slots)
    c = _as(cap)
    assert "(2 slots)</button>" in c.get(f"/events/{e.pk}/slot/{slots[0].pk}/").content.decode()
    c.post(f"/events/signup/{first.pk}/checkin/")
    second.refresh_from_db()
    assert second.checked_in_by == cap and not second.kept
    first.refresh_from_db()
    assert first.kept  # the slot under way keeps its attendance
    _as(mem).post(f"/events/signup/{second.pk}/cancel/", {"confirmed": "yes"})
    assert not SignUp.objects.filter(pk=second.pk).exists()


def test_a_minors_run_records_the_adult_only_where_they_are_designated():
    now = timezone.now()
    cap = _user("cap@example.org", "officer")
    guardian = _user("parent@example.org", category="community")
    kid = _user("kid@example.org", under_18=True, first_name="Kit", last_name="Young")
    Guardianship.objects.create(minor=kid, guardian=guardian, relationship="parent")
    kid.groups.set(Group.objects.filter(name="member"))
    _, slots = _event(now - timedelta(minutes=10), hours=3, captain=cap)
    runs = [SignUp.objects.create(slot=s, user=kid, role="observer") for s in slots]
    ray = [ResponsibleAdult.objects.create(signup=su, name="Uncle Ray") for su in runs[:2]]
    ResponsibleAdult.objects.create(signup=runs[2], name="Aunt May")
    c = _as(cap)
    r = c.post(f"/events/signup/{runs[0].pk}/checkin/", {"adult": [str(ray[0].pk)]}, follow=True)
    assert "Checked in for 2 slots" in r.content.decode()
    assert "check in for it on its own" in r.content.decode()
    for su in runs:
        su.refresh_from_db()
    assert [bool(su.checked_in_at) for su in runs] == [True, True, False]
    assert all(ResponsibleAdult.objects.get(pk=a.pk).present_at for a in ray)
    assert ResponsibleAdult.objects.get(name="Aunt May").present_at is None
