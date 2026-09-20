"""Announcements (FR-75, FR-106, FR-69, FR-81) and contest fields (FR-37)."""

from datetime import timedelta

import pytest
from django.contrib.auth.models import Group
from django.core import mail
from django.test import Client
from django.utils import timezone

from apps.accounts.models import NotificationPreference, User
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


def _user(email, level="member", category="student", **kw):
    u = User.objects.create_user(email, "pw-Testing-123", **kw)
    u.groups.set(Group.objects.filter(name=level))
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
    cap = _user("cap@example.org", "officer", first_name="Cap", last_name="Tain")
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
    assert "2 people" in body and "Send to 2" in body
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
    # The stored copy carries the message and who sent it to whom; the unsubscribe line belongs
    # to the mail, where it can be acted on without signing in (2026-09-20).
    assert "Sent by Cap Tain" in msgs.first().body_html
    assert "<p>Please bring a headset.</p>" in msgs.first().body_html
    assert "unsubscribe" not in msgs.first().body_html
    sent = mail.outbox[-1]
    html = [c for c, t in sent.alternatives if t == "text/html"][0]
    assert "/unsubscribe/" in html and "your notification settings" in html
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
    cap = _user("cap@example.org", "officer")
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
    off = _user("off@example.org", "officer")
    m = _user("m@example.org", first_name="Mo", last_name="M")
    token = announce.unsubscribe_token(m)
    cl = Client()
    r = cl.get(f"/unsubscribe/{token}/")
    assert r.status_code == 200 and b"Stop these emails" in r.content
    assert b"general announcements from officers" in r.content, "it names what it stops"
    assert b"Mo" not in r.content, "but not whose account it is: the link travels (2026-09-20)"
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
    cap = _user("cap@example.org", "officer", first_name="Cap", last_name="T")
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


@pytest.mark.django_db
def test_every_message_carries_one_shared_link_to_the_member_s_own_settings(settings):
    """NAF, 2026-09-20: "For all emails, there should be a link to set user email and notification
    preferences... one link that works for every account, so you don't need to send individual
    links in the footers of the email."
    """
    from django.core import mail

    from apps.comms.services import compose

    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    ClubSetting.objects.update_or_create(key="defaults.email_delivery", defaults={"value": "on"})
    one = _user("one@example.org", first_name="One", last_name="Member")
    two = _user("two@example.org", first_name="Two", last_name="Member")

    compose(one, "reminder", "Your slot", "<p>Tomorrow.</p>")
    compose(two, "reminder", "Your slot", "<p>Tomorrow.</p>")
    first, second = (
        [c for c, t in m.alternatives if t == "text/html"][0] for m in mail.outbox[-2:]
    )
    assert "/me/edit/#notifications" in first, "the shared settings link"
    assert first.count("/me/edit/#notifications") == second.count("/me/edit/#notifications")
    assert "/unsubscribe/" not in first, "a reminder is not something to unsubscribe from"
    assert "notification settings" in mail.outbox[-1].body, "and the text part carries it too"


@pytest.mark.django_db
def test_bulk_mail_carries_an_unsubscribe_and_the_club_s_address(settings):
    """The digest and the openings blast are list mail by any receiver's definition; until
    2026-09-20 neither carried an unsubscribe of any kind."""
    from django.core import mail

    from apps.comms.services import compose

    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    ClubSetting.objects.update_or_create(key="defaults.email_delivery", defaults={"value": "on"})
    ClubSetting.objects.update_or_create(
        key="club.postal_address", defaults={"value": "Club Station, 1 Example Way, Town ST 00000"}
    )
    m = _user("bulk@example.org", first_name="Bee", last_name="Ulk")

    for category in ("digest", "opening", "event_published", "announcement"):
        compose(m, category, "Something", "<p>x</p>")
        sent = mail.outbox[-1]
        html = [c for c, t in sent.alternatives if t == "text/html"][0]
        assert "/unsubscribe/" in html, category
        assert "1 Example Way" in html, f"the club's address on {category}"
        assert sent.extra_headers["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
        assert "/unsubscribe/" in sent.extra_headers["List-Unsubscribe"]

    compose(m, "cancellation", "Off", "<p>x</p>")
    sent = mail.outbox[-1]
    html = [c for c, t in sent.alternatives if t == "text/html"][0]
    assert "/unsubscribe/" not in html and "List-Unsubscribe" not in sent.extra_headers
    assert "1 Example Way" not in html, "the address rides with bulk mail, not with every notice"


@pytest.mark.django_db
def test_the_address_line_is_absent_when_the_club_has_not_set_one(settings):
    from django.core import mail

    from apps.comms.services import compose

    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    ClubSetting.objects.update_or_create(key="defaults.email_delivery", defaults={"value": "on"})
    m = _user("noaddr@example.org", first_name="No", last_name="Addr")
    compose(m, "digest", "Weekly", "<p>x</p>")
    html = [c for c, t in mail.outbox[-1].alternatives if t == "text/html"][0]
    assert "/unsubscribe/" in html, "the unsubscribe does not depend on the address"
    assert "None" not in html.split("</table>")[-2], "and no placeholder stands in for it"


@pytest.mark.django_db
def test_unsubscribing_from_one_kind_of_bulk_mail_leaves_the_others_alone():
    """The token names the category, so "stop these" means the kind in front of the reader."""
    from apps.comms.services import compose

    ClubSetting.objects.update_or_create(key="defaults.email_delivery", defaults={"value": "on"})
    m = _user("pick@example.org", first_name="Pick", last_name="Y")
    token = announce.unsubscribe_token(m, "digest")
    r = Client().post(f"/unsubscribe/{token}/", {"List-Unsubscribe": "One-Click"})
    assert r.status_code == 200 and r.content == b"unsubscribed"

    assert compose(m, "digest", "Weekly", "<p>x</p>").state == Outbox.State.SKIPPED
    assert compose(m, "announcement", "Hello", "<p>x</p>").state == Outbox.State.SENT
    assert compose(m, "event_published", "New", "<p>x</p>").state == Outbox.State.SENT


@pytest.mark.django_db
def test_a_token_from_before_the_category_was_named_still_means_announcements():
    """An old link in an old message keeps working, and keeps meaning what it meant."""
    from django.core import signing

    m = _user("old@example.org", first_name="Old", last_name="Link")
    token = signing.dumps({"u": m.pk}, salt=announce.UNSUB_SALT)
    user, category = announce.user_from_unsubscribe_token(token)
    assert user == m and category == "announcement"
