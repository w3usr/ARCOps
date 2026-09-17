"""Events completeness: lock and complete (FR-44), role change (FR-111), limits and windows
(FR-39, FR-48, FR-62, FR-66), eligibility and openings (FR-53, FR-54, FR-80), CSV (FR-85),
filter and badges (FR-65), waitlist (FR-57), calendar feed (FR-59), cross-event view (FR-68),
display-only events (FR-45)."""

from datetime import timedelta

import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import Client
from django.utils import timezone

from apps.accounts.models import User
from apps.comms.models import Outbox
from apps.credentials.models import CredentialType, LicenseRecord
from apps.events.models import (
    Captaincy,
    EligibilityRule,
    Event,
    Location,
    Opening,
    OperatingLimit,
    OperatingPeriod,
    Position,
    RoleCapacity,
    SignUp,
    Slot,
    Waitlist,
)
from apps.events.services import lifecycle, waitlist
from apps.events.services.slots import generate_slots, limit_report, windows_from_daily
from apps.ops.models import ClubSetting

pytestmark = pytest.mark.django_db


def _user(email, level="member", **kw):
    u = User.objects.create_user(email, "pw-Testing-123", **kw)
    u.groups.set(Group.objects.filter(name=level))
    u.category = kw.get("category", "student")
    u.save()
    return u


def _licensed(u, cls="General"):
    LicenseRecord.objects.create(
        user=u,
        callsign=u.callsign or "N0TEST",
        operator_class=cls,
        status="active",
        expiry_date=timezone.now().date() + timedelta(days=900),
    )


def _station(u):
    from apps.credentials.models import SignedAgreement

    for key in ("station_access", "it_access"):
        ct, _ = CredentialType.objects.get_or_create(
            key=key, defaults={"label": key, "established_by": "agreement"}
        )
        SignedAgreement.objects.create(
            user=u,
            credential=ct,
            signer_name=u.full_name,
            state="approved",
            expires_on=timezone.now().date() + timedelta(days=400),
        )


def _event(start, hours=2, captain=None, state=Event.State.PUBLISHED):
    e = Event.objects.create(title="Sprint", state=state)
    OperatingPeriod.objects.create(event=e, start=start, end=start + timedelta(hours=hours))
    loc = Location.objects.create(event=e, name="Club station")
    pos = Position.objects.create(location=loc, name="Run")
    slots = []
    for h in range(hours):
        s = Slot.objects.create(
            position=pos, start=start + timedelta(hours=h), end=start + timedelta(hours=h + 1)
        )
        for role, n in (("operator", 1), ("mentor", 1), ("observer", 1)):
            RoleCapacity.objects.create(slot=s, role=role, capacity=n)
        slots.append(s)
    if captain:
        Captaincy.objects.create(event=e, user=captain)
    return e, slots


def test_lock_blocks_member_changes_and_complete_runs_automatically():
    now = timezone.now()
    cap = _user("cap@example.org", "officer")
    mem = _user("mem@example.org")
    e, slots = _event(now + timedelta(days=2), captain=cap)
    su = SignUp.objects.create(slot=slots[0], user=mem, role="observer")
    c = Client()
    c.force_login(cap)
    c.post(f"/events/{e.pk}/state/", {"what": "lock"})
    assert Event.objects.get(pk=e.pk).state == Event.State.LOCKED
    c.force_login(mem)
    body = c.get(f"/events/{e.pk}/").content.decode()
    assert "Locked" in body and "roster is frozen" in body
    r = c.post(f"/events/signup/{su.pk}/cancel/", {"confirmed": "yes"})
    assert r.status_code == 302 and SignUp.objects.filter(pk=su.pk).exists()
    r = c.post(f"/events/slot/{slots[1].pk}/signup/", {"role": "observer"})
    assert not SignUp.objects.filter(slot=slots[1], user=mem).exists()
    c.force_login(cap)
    c.post(f"/events/{e.pk}/state/", {"what": "unlock"})
    assert Event.objects.get(pk=e.pk).state == Event.State.PUBLISHED
    # automatic completion once the last slot has ended
    old, oslots = _event(now - timedelta(days=1), captain=cap)
    assert lifecycle.complete_ended(now) == 1
    assert Event.objects.get(pk=old.pk).state == Event.State.COMPLETED
    assert Event.objects.get(pk=e.pk).state == Event.State.PUBLISHED
    call_command("events_complete", "--now", now.isoformat())


def test_publish_with_announcement_reaches_members():
    now = timezone.now()
    cap = _user("cap@example.org", "officer")
    mem = _user("mem@example.org")
    e, _ = _event(now + timedelta(days=5), captain=cap, state=Event.State.DRAFT)
    c = Client()
    c.force_login(cap)
    c.post(f"/events/{e.pk}/publish/", {"announce": "yes"})
    assert Event.objects.get(pk=e.pk).state == Event.State.PUBLISHED
    assert Outbox.objects.filter(
        user=mem, category="announcement", subject__contains="Sprint"
    ).exists()


def test_role_change_warns_when_it_breaks_the_slot_and_tells_captains_inside_cutoff():
    now = timezone.now()
    cap = _user("cap@example.org", "officer")
    mem = _user("mem@example.org", callsign="N0MEM")
    _licensed(mem)
    _station(mem)  # the slot is viable on mem alone
    e, slots = _event(now + timedelta(hours=5), captain=cap)
    su = SignUp.objects.create(slot=slots[0], user=mem, role="operator")
    c = Client()
    c.force_login(mem)
    body = c.get(f"/events/{e.pk}/slot/{slots[0].pk}/").content.decode()
    assert "Change role to" in body
    r = c.post(f"/events/signup/{su.pk}/role/", {"role": "observer"})
    assert r.status_code == 200 and b"Before you switch" in r.content  # the only licensee
    su.refresh_from_db()
    assert su.role == "operator"
    c.post(f"/events/signup/{su.pk}/role/", {"role": "observer", "confirmed": "yes"})
    su.refresh_from_db()
    assert su.role == "observer"
    m = Outbox.objects.get(user=cap, category="moved")
    assert "Role change inside the cutoff" in m.subject


def test_windows_and_limits_mark_over_limit_slots_and_show_on_health():
    now = timezone.now().replace(minute=0, second=0, microsecond=0)
    cap = _user("cap@example.org", "officer")
    e = Event.objects.create(title="SCR", state=Event.State.PUBLISHED)
    start = now + timedelta(days=3)
    OperatingPeriod.objects.create(
        event=e, start=start.replace(hour=13), end=start.replace(hour=13) + timedelta(days=2)
    )
    loc = Location.objects.create(event=e, name="Station")
    pos = Position.objects.create(location=loc, name="Run")
    Captaincy.objects.create(event=e, user=cap)
    OperatingLimit.objects.create(event=e, max_hours_per_day=6, day_basis="utc", max_total_hours=10)
    windows = windows_from_daily(e, [("15:00", "22:00")])  # 7 h a day
    assert len(windows) == 3 or len(windows) == 2
    slots = generate_slots(e, [pos], minutes=60, windows=windows)
    assert all(15 <= s.start.hour < 22 for s in slots)
    report = limit_report(e)
    assert report["days"][0]["hours"] == 7.0 and report["days"][0]["over"]
    assert report["over_total"] and len(report["over_slot_ids"]) >= 1
    c = Client()
    c.force_login(cap)
    body = c.get(f"/events/{e.pk}/").content.decode()
    assert "over limit" in body and "Per day:" in body and "Export CSV" in body
    # the manage page's generator accepts the windows text and the limits form saves
    r = c.post(
        f"/events/{e.pk}/limits/",
        {
            "max_hours_per_day": "6",
            "day_basis": "utc",
            "max_total_hours": "24",
            "min_break_minutes": "10",
        },
    )
    assert r.status_code == 302 and OperatingLimit.objects.get(event=e).max_total_hours == 24
    Slot.objects.filter(position=pos).delete()
    r = c.post(
        f"/events/{e.pk}/slots/generate/",
        {
            "minutes": 60,
            "setup_slots": 0,
            "breakdown_slots": 0,
            "windows": "15:00-18:00",
            "cap_operator": 1,
            "cap_mentor": 1,
            "cap_observer": 1,
        },
    )
    assert Slot.objects.filter(position=pos, kind="operating").count() in (6, 9)


def test_eligibility_editor_and_openings_with_announcement():
    now = timezone.now()
    cap = _user("cap@example.org", "officer")
    stu = _user("stu@example.org", category="student")
    com = _user("com@example.org", category="community", callsign="N0COM")
    _licensed(com, "Technician")
    e, slots = _event(now + timedelta(days=4), captain=cap)
    c = Client()
    c.force_login(cap)
    body = c.get(f"/events/{e.pk}/manage/").content.decode()
    assert "Who may sign up" in body and "Openings" in body and "Operating limits" in body
    c.post(
        f"/events/{e.pk}/eligibility/",
        {
            "cat_operator": ["student"],
            "class_mentor": "General",
            "minors_operator": "on",
            "minors_mentor": "on",
            "minors_observer": "on",
        },
    )
    assert EligibilityRule.objects.filter(event=e, slot__isnull=True).count() == 2
    from apps.events.services.eligibility import can_sign_up

    assert can_sign_up(stu, slots[0], "operator")[0]
    ok, reason = can_sign_up(com, slots[0], "operator")
    assert not ok and "limited to" in reason
    ok, reason = can_sign_up(com, slots[0], "mentor")
    assert not ok and "General" in reason
    # slot-level override lets the community member operate this slot only
    c.post(
        f"/events/{e.pk}/slot/{slots[0].pk}/eligibility/",
        {"role": "operator", "minors_operator": "on"},
    )
    assert (
        can_sign_up(com, slots[0], "operator")[0] and not can_sign_up(com, slots[1], "operator")[0]
    )
    # openings: observer opens to everyone in an hour, announced
    opens = (now + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")
    c.post(
        f"/events/{e.pk}/openings/add/", {"role": "observer", "opens_at": opens, "announce": "on"}
    )
    o = Opening.objects.get(event=e, role="observer")
    ok, reason = can_sign_up(stu, slots[0], "observer")
    assert not ok and "opens to you" in reason
    assert lifecycle.announce_openings(now) == 0
    assert lifecycle.announce_openings(now + timedelta(hours=2)) == 1
    assert Outbox.objects.filter(user=stu, category="opening").exists()
    o.refresh_from_db()
    assert o.announced_at is not None
    call_command("openings_announce", "--now", now.isoformat())


def test_waitlist_offer_accept_and_lapse():
    now = timezone.now()
    cap = _user("cap@example.org", "officer")
    a = _user("a@example.org")
    b = _user("b@example.org")
    d = _user("d@example.org")
    ClubSetting.objects.update_or_create(key="defaults.waitlist_offer_hours", defaults={"value": 2})
    e, slots = _event(now + timedelta(days=3), captain=cap)
    su = SignUp.objects.create(slot=slots[0], user=a, role="observer")  # observer seat now full
    c = Client()
    c.force_login(b)
    body = c.get(f"/events/{e.pk}/slot/{slots[0].pk}/").content.decode()
    assert "Join the waitlist" in body
    c.post(f"/events/slot/{slots[0].pk}/waitlist/", {"role": "observer"})
    c.force_login(d)
    c.post(f"/events/slot/{slots[0].pk}/waitlist/", {"role": "observer"})
    assert Waitlist.objects.filter(slot=slots[0], state="pending").count() == 2
    c.force_login(a)
    c.post(f"/events/signup/{su.pk}/cancel/", {"confirmed": "yes"})
    first = Waitlist.objects.get(user=b)
    assert (
        first.state == "offered"
        and Outbox.objects.filter(user=b, subject__contains="place opened").exists()
    )
    assert waitlist.expire_offers(now + timedelta(hours=1)) == 0
    assert waitlist.expire_offers(now + timedelta(hours=3)) == 1  # b lapsed, d offered
    assert Waitlist.objects.get(user=d).state == "offered"
    c.force_login(d)
    r = c.post(f"/events/waitlist/{Waitlist.objects.get(user=d).pk}/accept/")
    assert (
        r.status_code == 302
        and SignUp.objects.filter(slot=slots[0], user=d, role="observer").exists()
    )


def test_csv_filter_badges_feed_and_overview():
    now = timezone.now()
    cap = _user("cap@example.org", "officer")
    mem = _user("mem@example.org", first_name="Mo", last_name="Member", callsign="N0MEM")
    _licensed(mem)
    CredentialType.objects.get_or_create(
        key="station_access", defaults={"label": "Station", "established_by": "agreement"}
    )
    e, slots = _event(now + timedelta(days=3), captain=cap)
    SignUp.objects.create(slot=slots[0], user=mem, role="observer")  # unlicensed role: needs
    c = Client()
    c.force_login(cap)
    csv_body = c.get(f"/events/{e.pk}/roster.csv").content.decode()
    assert "Mo Member" in csv_body and "N0MEM" in csv_body and csv_body.count("\n") >= 3
    full = c.get(f"/events/{e.pk}/").content.decode()
    problems = c.get(f"/events/{e.pk}/?filter=problems").content.decode()
    assert "Show every slot" in problems and problems.count('class="r-cell') < full.count(
        'class="r-cell'
    )
    c.force_login(mem)
    assert c.get(f"/events/{e.pk}/roster.csv").status_code == 404
    sked = c.get("/events/mine/").content.decode()
    assert "/events/feed/" in sked
    import re

    url = re.search(r'id="feed-url">(.*?)<', sked).group(1)
    path = url[url.index("/events/feed/") :]
    ics = Client().get(path)
    assert ics.status_code == 200 and b"BEGIN:VEVENT" in ics.content and b"Sprint" in ics.content
    assert Client().get("/events/feed/tampered.ics").status_code == 404
    c.force_login(cap)
    body = c.get("/events/health/").content.decode()
    assert "Sprint" in body and "Upcoming events, at a glance" in body
    c.force_login(mem)
    assert c.get("/events/health/").status_code == 404


def test_display_only_event_has_no_roster_and_lists_as_regular():
    cap = _user("cap@example.org", "officer")
    e = Event.objects.create(
        title="Tuesday Net",
        state=Event.State.PUBLISHED,
        display_only=True,
        recurrence_text="Tuesdays 20:00 ET",
    )
    c = Client()
    c.force_login(cap)
    body = c.get("/events/").content.decode()
    assert "Regular meetings and nets" in body and "Tuesdays 20:00 ET" in body
    body = c.get(f"/events/{e.pk}/").content.decode()
    assert "no roster, no sign-up" in body and "No slots yet" not in body
    r = c.post(
        "/events/new/",
        {
            "title": "Monthly meeting",
            "type": "other",
            "display_only": "on",
            "recurrence_text": "First Monday 19:00",
            "description_html": "",
            "rules_url": "",
            "min_license_class": "",
            "kbyg_html": "",
            "start": "",
            "end": "",
        },
    )
    assert (
        r.status_code == 302
        and Event.objects.filter(title="Monthly meeting", display_only=True).exists()
    )
