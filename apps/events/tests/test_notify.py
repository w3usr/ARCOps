"""Reminders (FR-72, FR-100), warnings and notes (FR-73, FR-110), no-shows (FR-113),
cancellation and move notices (FR-56, FR-58, FR-74, FR-91), and the digest (FR-79)."""

from datetime import timedelta

import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import Client
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.services import set_access
from apps.comms.models import Outbox
from apps.events.models import (
    Captaincy,
    Event,
    Location,
    OperatingPeriod,
    Position,
    RoleCapacity,
    SignUp,
    Slot,
    SlotWarning,
)
from apps.events.services import notify
from apps.ops.models import ClubSetting

pytestmark = pytest.mark.django_db


def _user(email, level="member", **kw):
    u = User.objects.create_user(email, "pw-Testing-123", **kw)
    u.groups.set(Group.objects.filter(name=level))
    u.save()
    return u


def _event(start, hours=2, captain=None, title="Test Contest"):
    e = Event.objects.create(
        title=title, state=Event.State.PUBLISHED, kbyg_html="<p>Bring a headset.</p>"
    )
    OperatingPeriod.objects.create(event=e, start=start, end=start + timedelta(hours=hours))
    loc = Location.objects.create(event=e, name="Club station")
    pos = Position.objects.create(location=loc, name="Run")
    slots = []
    for h in range(hours):
        s = Slot.objects.create(
            position=pos, start=start + timedelta(hours=h), end=start + timedelta(hours=h + 1)
        )
        for role, n in (("operator", 2), ("mentor", 1), ("observer", 2)):
            RoleCapacity.objects.create(slot=s, role=role, capacity=n)
        slots.append(s)
    if captain:
        Captaincy.objects.create(event=e, user=captain)
    return e, slots


def _msgs(user, category=None):
    qs = Outbox.objects.filter(user=user)
    return qs.filter(category=category) if category else qs


def test_reminder_goes_once_inside_the_window_with_the_right_content_and_a_working_token():
    now = timezone.now()
    cap = _user(
        "cap@example.org",
        "officer",
        first_name="Cap",
        last_name="Tain",
        cell_phone="555-0100",
    )
    mem = _user("mem@example.org", first_name="Mo", last_name="Member", callsign="N0MEM")
    other = _user("oth@example.org", first_name="Ann", last_name="Other")
    e, slots = _event(now + timedelta(hours=25, minutes=30), captain=cap)
    su = SignUp.objects.create(slot=slots[0], user=mem, role="operator")
    SignUp.objects.create(slot=slots[0], user=other, role="observer")
    assert notify.send_reminders(now) == {"sent": 0}  # 25.5 h out: not yet
    later = now + timedelta(hours=2)
    assert notify.send_reminders(later)["sent"] == 2
    assert notify.send_reminders(later + timedelta(minutes=15))["sent"] == 0  # once only
    m = _msgs(mem, "reminder").get()
    body = m.body_html
    assert (
        "operator" in body
        and "Bring a headset" in body
        and "Cap Tain" in body
        and "555-0100" in body
    )
    assert "Ann" in body and "Confirm you will be there" in body and "I cannot make it" in body
    su.refresh_from_db()
    assert su.reminder_sent_at is not None and su.confirmed_at is None
    import re

    link = re.search(r'href="([^"]*?/events/confirm/[^"]+)"', body).group(1)
    path = link[link.index("/events/") :]
    c = Client()  # signed out
    r = c.get(path)
    assert r.status_code == 200 and b"Confirmed, thank you" in r.content
    su.refresh_from_db()
    assert su.confirmed_at is not None
    r = c.get(path)
    assert b"Already confirmed" in r.content
    r = c.get(path[:-3] + "xyz/")
    assert r.status_code == 410 and b"no longer valid" in r.content


def test_cannot_make_it_token_cancels_and_tells_the_captains_late():
    now = timezone.now()
    cap = _user("cap@example.org", "officer", first_name="Cap", last_name="Tain")
    mem = _user("mem@example.org", first_name="Mo", last_name="Member")
    e, slots = _event(now + timedelta(hours=5), captain=cap)
    su = SignUp.objects.create(slot=slots[0], user=mem, role="operator")
    token = notify.confirm_token(su)
    c = Client()
    r = c.get(f"/events/cannot/{token}/")
    assert r.status_code == 200 and b"Cannot make it" in r.content
    r = c.post(f"/events/cannot/{token}/")
    assert r.status_code == 200 and b"Sign-up canceled" in r.content
    assert not SignUp.objects.filter(pk=su.pk).exists()
    m = _msgs(cap, "cancellation").get()
    assert "Late cancellation" in m.subject and "Mo" in m.subject


def test_member_cancel_outside_cutoff_is_not_late_and_captain_removal_tells_the_member():
    now = timezone.now()
    cap = _user("cap@example.org", "officer", first_name="Cap", last_name="Tain")
    mem = _user("mem@example.org", first_name="Mo", last_name="Member")
    e, slots = _event(now + timedelta(days=3), captain=cap)
    su = SignUp.objects.create(slot=slots[0], user=mem, role="observer")
    c = Client()
    c.force_login(mem)
    c.post(f"/events/signup/{su.pk}/cancel/", {"confirmed": "yes"})
    m = _msgs(cap, "cancellation").get()
    assert m.subject.startswith("Cancellation:") and "Late" not in m.subject
    su2 = SignUp.objects.create(slot=slots[1], user=mem, role="observer")
    c.force_login(cap)
    c.post(f"/events/signup/{su2.pk}/cancel/", {"confirmed": "yes", "reason": "double booked"})
    m = _msgs(mem, "moved").get()
    assert "removed" in m.subject and "double booked" in m.body_html


def test_captain_assign_tells_the_member_and_slot_and_event_cancel_tell_everyone():
    now = timezone.now()
    cap = _user("cap@example.org", "officer", first_name="Cap", last_name="Tain")
    mem = _user("mem@example.org", first_name="Mo", last_name="Member")
    e, slots = _event(now + timedelta(days=3), captain=cap)
    c = Client()
    c.force_login(cap)
    c.post(f"/events/{e.pk}/slot/{slots[0].pk}/assign/", {"user": mem.pk, "role": "observer"})
    assert "signed up" in _msgs(mem, "moved").get().subject
    # slot cancel with a person: refused without confirmation, done with it
    c.post(f"/events/slot/{slots[0].pk}/toggle/", {"what": "cancel"})
    assert Slot.objects.get(pk=slots[0].pk).cancelled is False
    c.post(
        f"/events/slot/{slots[0].pk}/toggle/",
        {"what": "cancel", "confirmed": "yes", "reason": "storm"},
    )
    s0 = Slot.objects.get(pk=slots[0].pk)
    assert s0.cancelled and not s0.signups.exists()
    m = _msgs(mem, "cancellation").get()
    assert "Slot canceled" in m.subject and "storm" in m.body_html
    SignUp.objects.create(slot=slots[1], user=mem, role="observer")
    c.post(f"/events/{e.pk}/cancel/", {"confirm": "yes", "reason": "no operators"})
    assert Event.objects.get(pk=e.pk).state == Event.State.CANCELLED
    assert any(
        "Event canceled" in x.subject and "no operators" in x.body_html
        for x in _msgs(mem, "cancellation")
    )


def test_access_removed_withdraws_future_signups_and_tells_the_captains():
    now = timezone.now()
    cap = _user("cap@example.org", "officer", first_name="Cap", last_name="Tain")
    sysadmin = _user("s@example.org", "sysadmin")
    mem = _user("mem@example.org", first_name="Mo", last_name="Member")
    e, slots = _event(now + timedelta(days=2), captain=cap)
    SignUp.objects.create(slot=slots[0], user=mem, role="observer")
    SignUp.objects.create(slot=slots[1], user=mem, role="observer")
    set_access(sysadmin, mem, [], "graduated")
    assert not SignUp.objects.filter(user=mem).exists()
    m = _msgs(cap, "moved").get()
    assert "lost access" in m.subject and "2 sign-up" in m.subject


def test_warnings_go_to_people_and_captains_once_per_state_and_carry_late_notes():
    now = timezone.now()
    cap = _user("cap@example.org", "officer", first_name="Cap", last_name="Tain")
    new = _user("new@example.org", first_name="Newt", last_name="Person")
    e, slots = _event(now + timedelta(hours=30), captain=cap)
    SignUp.objects.create(slot=slots[0], user=new, role="observer", note="running 10 minutes late")
    r = notify.send_warnings(now)
    assert r["slots_warned"] == 1 and r["captains_told"] == 1
    assert "needs help" in _msgs(new, "warning").get().subject
    capmsg = _msgs(cap, "warning").get()
    assert "1 slot(s) at risk" in capmsg.subject and "running 10 minutes late" in capmsg.body_html
    assert notify.send_warnings(now + timedelta(hours=1))["slots_warned"] == 0  # rate limit
    assert (
        notify.send_warnings(now + timedelta(hours=13))["slots_warned"] == 1
    )  # same state, 12 h later
    assert SlotWarning.objects.filter(slot=slots[0]).count() == 2
    # a slot inside 24 h with an unconfirmed sign-up is flagged even when viable
    call_command("notify_warnings", "--now", now.isoformat())


def test_no_show_notice_goes_once_to_captains():
    now = timezone.now()
    cap = _user("cap@example.org", "officer", first_name="Cap", last_name="Tain")
    mem = _user("mem@example.org", first_name="Mo", last_name="Member")
    e, slots = _event(now - timedelta(minutes=20), captain=cap)
    su = SignUp.objects.create(
        slot=slots[0], user=mem, role="observer", confirmed_at=now - timedelta(days=1)
    )
    assert notify.notify_no_shows(now) == 1
    assert notify.notify_no_shows(now + timedelta(minutes=5)) == 0
    m = _msgs(cap, "warning").get()
    assert "Not checked in" in m.subject and "Mo" in m.subject
    su.refresh_from_db()
    assert su.no_show_notified_at is not None


def test_captain_can_check_a_member_in_from_the_slot_page():
    now = timezone.now()
    cap = _user("cap@example.org", "officer", first_name="Cap", last_name="Tain")
    mem = _user("mem@example.org", first_name="Mo", last_name="Member")
    e, slots = _event(now - timedelta(minutes=10), captain=cap)
    su = SignUp.objects.create(slot=slots[0], user=mem, role="observer")
    c = Client()
    c.force_login(cap)
    body = c.get(f"/events/{e.pk}/slot/{slots[0].pk}/").content.decode()
    assert ">check in<" in body
    c.post(f"/events/signup/{su.pk}/checkin/")
    su.refresh_from_db()
    assert su.checked_in_at is not None and su.checked_in_by == cap


def test_digest_lists_events_open_slots_and_own_commitments():
    now = timezone.now()
    mem = _user("mem@example.org", first_name="Mo", last_name="Member")
    e, slots = _event(now + timedelta(days=3), title="Fall Sprint")
    SignUp.objects.create(slot=slots[0], user=mem, role="observer")
    r = notify.send_digest(now)
    assert r["members"] == 1 and r["events"] == 1
    m = _msgs(mem, "digest").get()
    assert "Fall Sprint" in m.body_html and "1 open" in m.body_html and "as observer" in m.body_html
    ClubSetting.objects.update_or_create(key="club.short_name", defaults={"value": "Test ARC"})
    call_command("digest_weekly", "--now", now.isoformat())
