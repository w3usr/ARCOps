"""Announcements (FR-75, FR-106, FR-69, FR-81) and contest fields (FR-37)."""

from datetime import timedelta

import pytest
from django.core import mail
from django.test import Client
from django.utils import timezone

from apps.accounts.models import AccessLevel, NotificationPreference, User
from apps.comms import announce
from apps.comms.models import Announcement, Outbox
from apps.events.models import (
    Captaincy,
    Event,
    Location,
    OperatingPeriod,
    Position,
    RoleCapacity,
    SignUp,
    Slot,
)
from apps.ops.models import AuditLog, ClubSetting

pytestmark = pytest.mark.django_db


def _user(email, level=AccessLevel.MEMBER, category="student", **kw):
    u = User.objects.create_user(email, "pw-Testing-123", **kw)
    u.access_level = level
    u.category = category
    u.save()
    return u


def _event(start, captain):
    e = Event.objects.create(title="Sprint", state=Event.State.PUBLISHED)
    OperatingPeriod.objects.create(event=e, start=start, end=start + timedelta(hours=2))
    loc = Location.objects.create(event=e, name="Station")
    pos = Position.objects.create(location=loc, name="Run")
    slots = [
        Slot.objects.create(
            position=pos, start=start + timedelta(hours=h), end=start + timedelta(hours=h + 1)
        )
        for h in range(2)
    ]
    for s in slots:
        for r in ("operator", "observer"):
            RoleCapacity.objects.create(slot=s, role=r, capacity=2)
    Captaincy.objects.create(event=e, user=captain)
    return e, slots


def test_audience_filters_count_and_send_with_reply_to_and_unsubscribe():
    ClubSetting.objects.update_or_create(key="defaults.email_delivery", defaults={"value": "on"})
    ClubSetting.objects.update_or_create(
        key="club.contact_email", defaults={"value": "club@example.org"}
    )
    cap = _user("cap@example.org", AccessLevel.OFFICER, first_name="Cap", last_name="Tain")
    a = _user("a@example.org", first_name="A", last_name="One")
    b = _user("b@example.org", category="community", first_name="B", last_name="Two")
    c = _user("c@example.org", first_name="C", last_name="Three")
    e, slots = _event(timezone.now() + timedelta(days=2), cap)
    SignUp.objects.create(slot=slots[0], user=a, role="operator", confirmed_at=timezone.now())
    SignUp.objects.create(slot=slots[0], user=b, role="observer")
    SignUp.objects.create(slot=slots[1], user=c, role="observer")
    assert len(announce.resolve_audience(e, {})) == 3
    assert [u.pk for u in announce.resolve_audience(e, {"role": "operator"})] == [a.pk]
    assert {u.pk for u in announce.resolve_audience(e, {"confirmation": "unconfirmed"})} == {
        b.pk,
        c.pk,
    }
    assert [u.pk for u in announce.resolve_audience(e, {"categories": ["community"]})] == [b.pk]
    assert len(announce.resolve_audience(None, {})) == 4  # every member, officers included
    cl = Client()
    cl.force_login(cap)
    body = cl.get(f"/events/{e.pk}/announce/?role=observer").content.decode()
    assert "2 recipients" in body and "Send to 2" in body
    r = cl.post(
        f"/events/{e.pk}/announce/",
        {
            "subject": "Bring headsets",
            "body_html": "Please bring a headset.\n\nThanks.",
            "role": "observer",
            "action": "send",
        },
    )
    assert r.status_code == 302
    ann = Announcement.objects.get()
    assert (
        ann.recipient_count == 2
        and ann.audience == {"role": "observer"}
        and [x[1] for x in ann.recipients]
    )
    msgs = Outbox.objects.filter(announcement=ann)
    assert msgs.count() == 2 and all(
        m.reply_to == ["cap@example.org", "club@example.org"] for m in msgs
    )
    assert (
        "unsubscribe" in msgs.first().body_html
        and "<p>Please bring a headset.</p>" in msgs.first().body_html
    )
    sent = mail.outbox[-1]
    assert sent.reply_to == ["cap@example.org", "club@example.org"]
    assert (
        "List-Unsubscribe" in sent.extra_headers
        and sent.extra_headers["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
    )
    assert "/unsubscribe/" in sent.extra_headers["List-Unsubscribe"]
    # history page for officers; a member cannot announce
    assert "Bring headsets" in cl.get("/announcements/").content.decode()
    cl.force_login(a)
    assert (
        cl.get(f"/events/{e.pk}/announce/").status_code == 404
        and cl.get("/announce/").status_code == 404
    )


def test_outside_copy_records_without_sending_and_lists_bcc_addresses():
    cap = _user("cap@example.org", AccessLevel.OFFICER)
    a = _user("a@example.org", first_name="A", last_name="One")
    e, slots = _event(timezone.now() + timedelta(days=2), cap)
    SignUp.objects.create(slot=slots[0], user=a, role="operator")
    cl = Client()
    cl.force_login(cap)
    r = cl.post(
        f"/events/{e.pk}/announce/", {"subject": "Hi", "body_html": "<p>x</p>", "action": "outside"}
    )
    assert r.status_code == 200 and b"a@example.org" in r.content and b"BCC" in r.content
    ann = Announcement.objects.get()
    assert (
        ann.sent_outside
        and ann.recipient_count == 1
        and Outbox.objects.filter(announcement=ann).count() == 0
    )
    assert AuditLog.objects.filter(action="announcement.recorded_outside").exists()


def test_unsubscribe_link_and_one_click_turn_off_announcements_only():
    ClubSetting.objects.update_or_create(key="defaults.email_delivery", defaults={"value": "on"})
    off = _user("off@example.org", AccessLevel.OFFICER)
    m = _user("m@example.org", first_name="Mo", last_name="M")
    token = announce.unsubscribe_token(m)
    cl = Client()
    r = cl.get(f"/unsubscribe/{token}/")
    assert r.status_code == 200 and b"Stop announcement emails" in r.content
    r = cl.post(f"/unsubscribe/{token}/", {"List-Unsubscribe": "One-Click"})
    assert r.status_code == 200 and r.content == b"unsubscribed"
    assert NotificationPreference.objects.get(user=m, category="announcement").email is False
    announce.send_announcement(off, None, {}, "All hands", "<p>x</p>")
    assert Outbox.objects.get(user=m, category="announcement").state == Outbox.State.SKIPPED
    from apps.comms.services import compose

    assert (
        compose(m, "cancellation", "Cancelled", "<p>x</p>").state == Outbox.State.SENT
    )  # unaffected
    assert cl.get("/unsubscribe/not-a-token/").status_code == 410


def test_contest_fields_saved_shown_and_in_the_reminder():
    cap = _user("cap@example.org", AccessLevel.OFFICER, first_name="Cap", last_name="T")
    mem = _user("m@example.org", first_name="Mo", last_name="M")
    e, slots = _event(timezone.now() + timedelta(hours=20), cap)
    cl = Client()
    cl.force_login(cap)
    r = cl.post(
        f"/events/{e.pk}/contest/",
        {
            "exchange": "RST and serial",
            "mode": "CW",
            "bands": "80-10m",
            "log_deadline": "7 days",
            "cabrillo_name": "TEST-SPRINT",
            "log_upload_url": "https://example.org/upload",
            "calendar_ref": "123",
        },
    )
    assert r.status_code == 302
    e.refresh_from_db()
    assert (
        e.contest_fields["exchange"] == "RST and serial"
        and e.calendar_ref == 123
        and "status" not in e.contest_fields
    )
    body = cl.get(f"/events/{e.pk}/").content.decode()
    assert (
        "Contest details" in body
        and "RST and serial" in body
        and 'href="https://example.org/upload"' in body
    )
    body = cl.get(f"/events/{e.pk}/manage/").content.decode()
    assert 'value="RST and serial"' in body
    from apps.events.services.notify import send_one_reminder

    su = SignUp.objects.create(slot=slots[0], user=mem, role="operator")
    send_one_reminder(su)
    rem = Outbox.objects.get(user=mem, category="reminder")
    assert (
        "Exchange:" in rem.body_html
        and "RST and serial" in rem.body_html
        and "TEST-SPRINT" in rem.body_html
    )
