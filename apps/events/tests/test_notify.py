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
        "Operator" in body
        and "Bring a headset" in body
        and "Cap Tain" in body
        and "555-0100" in body
    )
    assert "Ann" in body and "Confirm you will be there" in body and "I cannot make it" in body
    # A role reaches the reader as the club's label, not its stored key (T31, 2026-10-20)
    assert "as <strong>Operator</strong>" in body
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


def test_reminder_escapes_contest_fields_and_names_only_advisors():
    """A captain's contest details reach every participant's mail, so they are escaped; and a
    sysadmin is not named as a faculty advisor for being a superuser (T31, T42, 2026-10-20)."""
    now = timezone.now()
    _user("adv@example.org", "advisor", first_name="Dee", last_name="Visor")
    User.objects.create_superuser(
        "root@example.org", "pw-Testing-123", first_name="Ada", last_name="Root"
    )
    mem = _user("mem@example.org", first_name="Mo", last_name="Member")
    e, slots = _event(now + timedelta(hours=23))
    e.contest_fields = {"exchange": '<a href="https://evil.example">RST</a>', "mode": "<b>CW</b>"}
    e.save()
    SignUp.objects.create(slot=slots[0], user=mem, role="operator")
    notify.send_reminders(now)
    body = _msgs(mem, "reminder").get().body_html
    assert '<a href="https://evil.example">' not in body and "<b>CW</b>" not in body
    assert "&lt;b&gt;CW&lt;/b&gt;" in body
    assert "Dee Visor" in body and "Ada Root" not in body


def test_cannot_make_it_token_cancels_and_tells_the_captains_late(monkeypatch):
    now = timezone.now()
    cap = _user("cap@example.org", "officer", first_name="Cap", last_name="Tain")
    mem = _user("mem@example.org", first_name="Mo", last_name="Member")
    e, slots = _event(now + timedelta(hours=5), captain=cap)
    su = SignUp.objects.create(slot=slots[0], user=mem, role="operator")
    token = notify.confirm_token(su)
    c = Client()
    # Signed out, the warning and the order are the signed-in page's: Careful, then the safe
    # option first (T31 step 3, 2026-10-20).
    from types import SimpleNamespace

    with monkeypatch.context() as m:
        broken = SimpleNamespace(label="Not viable", reasons=["nobody with station access"])
        m.setattr("apps.events.views.would_break", lambda slot, su: broken)
        body = c.get(f"/events/cannot/{token}/").content.decode()
    assert '<p class="msg warning"><span class="lvl">Careful:</span> without you' in body
    assert 'class="banner"' not in body and 'class="danger"' in body
    assert body.index("Keep it") < body.index("Cancel my sign-up")
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
    assert "canceled their Observer sign-up" in m.body_html
    su2 = SignUp.objects.create(slot=slots[1], user=mem, role="observer")
    c.force_login(cap)
    # FR-58: a removal with no reason is refused by the server, not only by the form's
    # `required` (found in acceptance test T14 on 2026-10-14, with the attribute stripped)
    r = c.post(f"/events/signup/{su2.pk}/cancel/", {"confirmed": "yes", "reason": "  "})
    assert r.url == f"/events/signup/{su2.pk}/remove/" and SignUp.objects.filter(pk=su2.pk).exists()
    assert not _msgs(mem, "moved").exists()
    c.post(f"/events/signup/{su2.pk}/cancel/", {"confirmed": "yes", "reason": "double booked"})
    m = _msgs(mem, "moved").get()
    assert (
        "removed" in m.subject and "double booked" in m.body_html and "as Observer" in m.body_html
    )


def test_captain_assign_tells_the_member_and_slot_and_event_cancel_tell_everyone():
    now = timezone.now()
    cap = _user("cap@example.org", "officer", first_name="Cap", last_name="Tain")
    mem = _user("mem@example.org", first_name="Mo", last_name="Member")
    e, slots = _event(now + timedelta(days=3), captain=cap)
    c = Client()
    c.force_login(cap)
    c.post(f"/events/{e.pk}/slot/{slots[0].pk}/assign/", {"user": mem.pk, "role": "observer"})
    assigned = _msgs(mem, "moved").get()
    assert "signed up" in assigned.subject and "as Observer" in assigned.body_html
    # slot cancel with a person: refused without confirmation, done with it
    c.post(f"/events/slot/{slots[0].pk}/toggle/", {"what": "cancel"})
    assert Slot.objects.get(pk=slots[0].pk).cancelled is False
    c.post(f"/events/slot/{slots[0].pk}/toggle/", {"what": "cancel", "confirmed": "yes"})
    assert Slot.objects.get(pk=slots[0].pk).cancelled is False  # nor without a reason
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


def test_the_captains_get_notes_given_inside_the_48_hours_before_the_slot():
    """FR-110: the 48 hours count back from the slot's start, not from the job's run."""
    now = timezone.now()
    cap = _user("cap@example.org", "officer", first_name="Cap", last_name="Tain")
    early = _user("early@example.org", first_name="Early", last_name="Bird")
    late = _user("late@example.org", first_name="Late", last_name="Comer")
    e, slots = _event(now + timedelta(hours=30), captain=cap)
    for who, note, before in ((early, "an old note", 70), (late, "a fresh note", 40)):
        su = SignUp.objects.create(slot=slots[0], user=who, role="observer", note=note)
        SignUp.objects.filter(pk=su.pk).update(created=slots[0].start - timedelta(hours=before))
    notify.send_warnings(now)
    body = _msgs(cap, "warning").get().body_html
    assert "a fresh note" in body and "an old note" not in body


def test_a_member_edits_their_note_to_the_captains_after_signing_up():
    """FR-110: a note is "entered at sign-up and editable by the member afterwards"; saving it
    keeps when, for the digest, and the audit log keeps what it said before."""
    from django.urls import reverse

    from apps.ops.models import AuditLog

    now = timezone.now()
    mem = _user("mem@example.org", first_name="Mo", last_name="Member")
    other = _user("other@example.org", first_name="Ot", last_name="Her")
    e, slots = _event(now + timedelta(days=5))
    su = SignUp.objects.create(slot=slots[0], user=mem, role="observer", note="first CW contest")
    c = Client()
    c.force_login(mem)
    page = c.get(f"/events/{e.pk}/slot/{slots[0].pk}/").content.decode()
    assert 'value="first CW contest"' in page and ">Save note<" in page
    url = reverse("signup_note", args=[su.pk])
    r = c.post(url, {"note": "running 10 minutes late"}, follow=True)
    su.refresh_from_db()
    assert su.note == "running 10 minutes late" and su.note_at is not None
    assert "Saved. The captains see your note." in r.content.decode()
    row = AuditLog.objects.get(action="signup.note_changed")
    assert row.before == {"note": "first CW contest"} and row.after == {
        "note": "running 10 minutes late"
    }
    other_c = Client()
    other_c.force_login(other)
    assert other_c.post(url, {"note": "not mine"}).status_code == 404
    Event.objects.filter(pk=e.pk).update(state=Event.State.LOCKED)  # FR-44: no member changes
    c.post(url, {"note": "changed while locked"})
    su.refresh_from_db()
    assert su.note == "running 10 minutes late"


def test_a_note_changed_inside_the_48_hours_reaches_the_captains():
    """FR-110: a note added or changed inside the 48 hours before the slot rides along, even on
    a sign-up made earlier."""
    now = timezone.now()
    cap = _user("cap@example.org", "officer", first_name="Cap", last_name="Tain")
    mem = _user("mem@example.org", first_name="Mo", last_name="Member")
    e, slots = _event(now + timedelta(hours=30), captain=cap)
    su = SignUp.objects.create(slot=slots[0], user=mem, role="observer", note="an old note")
    SignUp.objects.filter(pk=su.pk).update(created=slots[0].start - timedelta(hours=70))
    c = Client()
    c.force_login(mem)
    c.post(f"/events/signup/{su.pk}/note/", {"note": "now running late"})
    notify.send_warnings(now)
    assert "now running late" in _msgs(cap, "warning").get().body_html


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
    assert ">Check in<" in body
    r = c.post(f"/events/signup/{su.pk}/checkin/")
    su.refresh_from_db()
    assert su.checked_in_at is not None and su.checked_in_by == cap
    # Back to the slot for the next person, not the captain's own My Sked
    assert r["Location"] == f"/events/{e.pk}/slot/{slots[0].pk}/"


def test_digest_lists_events_open_slots_and_own_commitments():
    now = timezone.now()
    mem = _user("mem@example.org", first_name="Mo", last_name="Member")
    e, slots = _event(now + timedelta(days=3), title="Fall Sprint")
    SignUp.objects.create(slot=slots[0], user=mem, role="observer")
    r = notify.send_digest(now)
    assert r["members"] == 1 and r["events"] == 1
    m = _msgs(mem, "digest").get()
    assert "Fall Sprint" in m.body_html and "1 open" in m.body_html and "as Observer" in m.body_html
    ClubSetting.objects.update_or_create(key="club.short_name", defaults={"value": "Test ARC"})
    call_command("digest_weekly", "--now", now.isoformat())


def test_keep_it_from_the_reminder_says_nothing_changed_without_a_sign_in():
    """Signed out, Keep it on Cannot make it? led to My schedule, which asks for a sign-in, so a
    member who only wanted their slot was never told that nothing changed."""
    now = timezone.now()
    mem = _user("mem@example.org", first_name="Mo", last_name="Member")
    e, slots = _event(now + timedelta(hours=20))
    su = SignUp.objects.create(slot=slots[0], user=mem, role="operator")
    token = notify.confirm_token(su)
    c = Client()
    page = c.get(f"/events/cannot/{token}/").content.decode()
    assert 'href="?kept=1">Keep it</a>' in page
    r = c.get(f"/events/cannot/{token}/?kept=1")
    body = r.content.decode()
    assert (
        r.status_code == 200
        and "Nothing changed" in body
        and "Sign in" not in body.split("<main")[1][:600]
    )
    assert "you are still down as <strong>Operator</strong>" in body and "Open my schedule" in body
    su.refresh_from_db()
    assert su.confirmed_at is None, "keeping a slot is not confirming attendance"
