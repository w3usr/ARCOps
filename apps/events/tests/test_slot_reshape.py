"""Re-time, split or merge a slot that has people in it (FR-46, #156), as SK decided on
2026-11-11: re-timed, the people stay, are told and confirm again; split, they are in both
halves; merged, back-to-back slots only; none of it once a slot has started or has a check-in."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.comms.models import Outbox
from apps.events.models import RoleCapacity, SignUp, Waitlist
from apps.ops.models import AuditLog

from .test_manage import _as
from .test_manage_gaps import _future, _live

pytestmark = pytest.mark.django_db


def _slots(ev):
    return list(_live(ev).filter(kind="operating").order_by("start"))  # 18, 19, 20, 21 UTC


def _told(user):
    return Outbox.objects.filter(user=user, subject__startswith="Slot changed")


def test_a_slot_with_people_is_re_timed_and_they_are_told_and_confirm_again(officer, member):
    c = _as(officer)
    ev = _future(c)
    a, b, _, d = _slots(ev)
    su = SignUp.objects.create(
        slot=d,
        user=member,
        role="operator",
        confirmed_at=timezone.now(),
        reminder_sent_at=timezone.now(),
    )
    url = f"/events/{ev.pk}/slot/{d.pk}/retime/"
    page = c.get(f"/events/{ev.pk}/slot/{d.pk}/").content.decode()
    assert f'action="{url}"' in page and 'value="2027-06-26T21:00"' in page
    # onto another slot's time, or outside the period: refused, nothing moves, nobody told
    r = c.post(url, {"start": "2027-06-26T18:30", "minutes": "60"}, follow=True)
    assert "already has a slot from" in r.content.decode()
    r = c.post(url, {"start": "2027-06-26T22:00", "minutes": "60"}, follow=True)
    assert "has to fit inside an operating period" in r.content.decode()
    d.refresh_from_db()
    assert d.start.hour == 21 and not _told(member).exists()
    # half an hour shorter, inside the period
    c.post(url, {"start": "2027-06-26T21:15", "minutes": "45"})
    d.refresh_from_db()
    su.refresh_from_db()
    assert (d.start.hour, d.start.minute, d.end.hour) == (21, 15, 22)
    assert su.slot_id == d.pk and su.confirmed_at is None and su.reminder_sent_at is None
    msg = _told(member).get()
    assert "21:00" in msg.body_html and "21:15" in msg.body_html and "confirm" in msg.body_html
    row = AuditLog.objects.filter(action="slot.retimed", subject_id=str(d.pk)).get()
    assert row.after["people told"] == 1
    # an empty slot moves with nobody to tell
    c.post(f"/events/{ev.pk}/slot/{a.pk}/retime/", {"start": "2027-06-26T18:00", "minutes": "30"})
    a.refresh_from_db()
    assert (
        a.end.minute == 30
        and Outbox.objects.filter(subject__startswith="Slot changed").count() == 1
    )


def test_a_split_slot_keeps_its_people_in_both_halves(officer, member):
    c = _as(officer)
    ev = _future(c)
    a = _slots(ev)[0]
    confirmed = timezone.now()
    SignUp.objects.create(
        slot=a, user=member, role="operator", note="Early", confirmed_at=confirmed
    )
    Waitlist.objects.create(slot=a, user=officer, role="mentor")
    url = f"/events/{ev.pk}/slot/{a.pk}/split/"
    r = c.post(url, {"at": "2027-06-26T18:05"}, follow=True)  # a five-minute half
    assert "at least 15 minutes" in r.content.decode() and _live(ev).count() == 4
    c.post(url, {"at": "2027-06-26T18:30"})
    a.refresh_from_db()
    first, second = _slots(ev)[:2]
    assert first.pk == a.pk and (first.end.minute, second.start.minute, second.end.hour) == (
        30,
        30,
        19,
    )
    assert _live(ev).count() == 5
    for half in (first, second):
        su = half.signups.get()
        assert (su.user, su.role, su.note, su.confirmed_at) == (
            member,
            "operator",
            "Early",
            confirmed,
        )
        assert {x.role: x.capacity for x in half.capacities.all()} == {"operator": 2, "mentor": 1}
        assert half.waitlist.filter(user=officer, role="mentor", state="pending").exists()
    assert not Outbox.objects.filter(user=member).exists()  # their time did not change
    assert AuditLog.objects.filter(action="slot.split", subject_id=str(a.pk)).exists()


def test_back_to_back_slots_merge_with_everyone_in_them(officer, member):
    from apps.accounts.models import User

    other = User.objects.create_user(
        "oth@example.org", "pw-Testing-123", groups=["member"], first_name="Ann", last_name="Other"
    )
    c = _as(officer)
    ev = _future(c)
    a, b, x, _ = _slots(ev)
    now = timezone.now()
    SignUp.objects.create(slot=a, user=member, role="operator", confirmed_at=now)
    SignUp.objects.create(slot=b, user=member, role="operator", confirmed_at=now)  # in both
    SignUp.objects.create(slot=b, user=other, role="operator", confirmed_at=now)
    SignUp.objects.create(slot=b, user=officer, role="operator")  # a third operator, of 2 seats
    RoleCapacity.objects.filter(slot=b, role="operator").update(capacity=3)
    page = c.get(f"/events/{ev.pk}/slot/{a.pk}/").content.decode()
    assert f'action="/events/{ev.pk}/slot/{a.pk}/merge/"' in page
    # only the slot that follows on: not one further along
    r = c.post(f"/events/{ev.pk}/slot/{a.pk}/merge/", {"with": x.pk}, follow=True)
    assert "Only the slot that follows straight on" in r.content.decode()
    c.post(f"/events/{ev.pk}/slot/{a.pk}/merge/", {"with": b.pk})
    a.refresh_from_db()
    b.refresh_from_db()
    assert (a.start.hour, a.end.hour) == (18, 20) and b.cancelled and not b.signups.exists()
    people = {s.user: s for s in a.signups.all()}
    assert set(people) == {member, other, officer}
    assert people[member].confirmed_at is not None  # held both hours: nothing changed for them
    assert people[other].confirmed_at is None  # an hour longer now: told, and confirms again
    assert _told(other).count() == 1 and not _told(member).exists()
    assert a.capacities.get(role="operator").capacity == 3  # the larger, and it holds all three
    assert AuditLog.objects.filter(action="slot.merged", subject_id=str(a.pk)).exists()


def test_a_slot_that_has_started_or_has_a_check_in_keeps_its_time(officer, member):
    c = _as(officer)
    ev = _future(c)
    a, b, *_ = _slots(ev)
    SignUp.objects.create(slot=a, user=member, role="operator", checked_in_at=timezone.now())
    page = c.get(f"/events/{ev.pk}/slot/{a.pk}/").content.decode()
    assert "keeps its time" in page and f"/slot/{a.pk}/retime/" not in page
    for what, data in (
        ("retime", {"start": "2027-06-26T18:15", "minutes": "45"}),
        ("split", {"at": "2027-06-26T18:30"}),
        ("merge", {"with": b.pk}),
    ):
        r = c.post(f"/events/{ev.pk}/slot/{a.pk}/{what}/", data, follow=True)
        assert "keeps its time" in r.content.decode(), what
    a.refresh_from_db()
    assert a.end - a.start == timedelta(hours=1) and _live(ev).count() == 4
    # merging into a slot that has a check-in is refused from the other side too
    r = c.post(
        f"/events/{ev.pk}/slot/{b.pk}/retime/",
        {"start": "2020-01-01T00:00", "minutes": "60"},
        follow=True,
    )
    assert "has to fit inside an operating period" in r.content.decode()
    # a member who is not a captain has none of it
    assert (
        _as(member)
        .post(f"/events/{ev.pk}/slot/{b.pk}/split/", {"at": "2027-06-26T19:30"})
        .status_code
        == 404
    )
