"""Templates (FR-78), preferences (FR-71), My messages (FR-82, FR-108), and the officer outbox
(FR-105)."""

import pytest
from django.core import mail
from django.core.management import call_command
from django.test import Client

from apps.accounts.models import AccessLevel, NotificationPreference, User
from apps.comms.models import MessageTemplate, Outbox
from apps.comms.services import compose, render_message, seed_templates, send
from apps.ops.models import AuditLog, ClubSetting

pytestmark = pytest.mark.django_db


def _user(email="m@example.org", level=AccessLevel.MEMBER):
    u = User.objects.create_user(email, "pw-Testing-123", first_name="Mo", last_name="Member")
    u.access_level = level
    u.save()
    return u


def _on():
    ClubSetting.objects.update_or_create(key="defaults.email_delivery", defaults={"value": "on"})
    ClubSetting.objects.update_or_create(key="club.short_name", defaults={"value": "Test ARC"})


def test_render_falls_back_to_the_shipped_default_and_uses_club_context():
    ClubSetting.objects.update_or_create(key="club.short_name", defaults={"value": "Test ARC"})
    subject, body = render_message("account.admitted", {})
    assert subject == "Welcome to Test ARC" and "member of Test ARC" in body


def test_seed_creates_rows_and_keeps_interface_edits_unless_reset():
    c, u, k = seed_templates()
    assert c == MessageTemplate.objects.count() and u == k == 0
    row = MessageTemplate.objects.get(key="account.admitted")
    row.subject, row.edited = "Hello from us", True
    row.save()
    seed_templates()
    assert MessageTemplate.objects.get(key="account.admitted").subject == "Hello from us"
    assert render_message("account.admitted", {})[0] == "Hello from us"
    seed_templates(reset=True)
    assert MessageTemplate.objects.get(key="account.admitted").subject.startswith("Welcome to")
    call_command("club_import")  # the import seeds too
    assert MessageTemplate.objects.filter(key="invitation").exists()


def test_preference_off_keeps_the_copy_and_skips_the_email_but_mandatory_still_goes():
    _on()
    u = _user()
    NotificationPreference.objects.create(user=u, category="reminder", email=False)
    m = compose(u, "reminder", "Reminder", "<p>Slot tomorrow</p>")
    assert m.state == Outbox.State.SKIPPED and len(mail.outbox) == 0
    m2 = compose(u, "cancellation", "Cancelled", "<p>Sorry</p>")
    assert m2.state == Outbox.State.SENT and len(mail.outbox) == 1
    assert u.reminders_off


def test_send_to_bare_addresses_when_there_is_no_account_yet():
    _on()
    m = send(
        "invitation",
        None,
        "account",
        {"link": "https://x/i/1/", "expires": None, "category": "student"},
        to=["new@example.org"],
    )
    assert m.to_addresses == ["new@example.org"] and m.state == Outbox.State.SENT
    assert "invited to join" in mail.outbox[0].subject


def test_my_messages_lists_marks_read_and_the_badge_and_banner_follow():
    u = _user()
    compose(u, "warning", "Slot at risk", "<p>Needs a licensee</p>")
    compose(u, "reminder", "Your slot", "<p>Tomorrow</p>")
    c = Client()
    c.force_login(u)
    home = c.get("/").content.decode()
    assert (
        "2 unread" in home
        and "Slot at risk" in home
        and "Your slot" not in home.split("My next slots")[0].split("unread notice")[1]
    )
    body = c.get("/me/messages/").content.decode()
    assert "Slot at risk" in body and "Your slot" in body
    assert Outbox.objects.filter(user=u, read_at__isnull=True).count() == 0
    home = c.get("/").content.decode()
    assert "unread notice" not in home and 'class="badge"' not in home


def test_notification_form_writes_preferences_and_profile_shows_them():
    u = _user()
    c = Client()
    c.force_login(u)
    body = c.get("/me/").content.decode()
    assert (
        "Notifications" in body
        and 'name="email" value="reminder"' in body
        and "always sent" in body.lower()
    )
    r = c.post("/me/notifications/", {"email": ["warning", "digest"]})
    assert r.status_code == 302
    prefs = {p.category: p.email for p in u.notification_preferences.all()}
    assert prefs["reminder"] is False and prefs["warning"] is True and prefs["digest"] is True
    assert u.reminders_off


def test_outbox_is_officers_only_and_filters_by_state():
    _on()
    m = _user()
    compose(m, "reminder", "Sent one", "<p>x</p>")
    ClubSetting.objects.update_or_create(key="defaults.email_delivery", defaults={"value": "off"})
    compose(m, "reminder", "Kept one", "<p>y</p>")
    c = Client()
    c.force_login(m)
    assert c.get("/ops/outbox/").status_code == 404
    o = _user("o@example.org", AccessLevel.OFFICER)
    c.force_login(o)
    body = c.get("/ops/outbox/").content.decode()
    assert "Sent one" in body and "Kept one" in body and "Email delivery is <strong>off" in body
    body = c.get("/ops/outbox/?state=sent").content.decode()
    assert "Sent one" in body and "Kept one" not in body
    home = c.get("/").content.decode()
    assert "Email delivery is <strong>off</strong>" in home


def test_template_edit_page_is_sysadmin_only_sanitises_and_audits():
    s = _user("s@example.org", AccessLevel.SYSADMIN)
    o = _user("o@example.org", AccessLevel.OFFICER)
    c = Client()
    c.force_login(o)
    assert c.get("/ops/templates/").status_code == 404
    c.force_login(s)
    body = c.get("/ops/templates/").content.decode()
    assert "account.admitted" in body and "shipped default" in body
    r = c.post(
        "/ops/templates/account.admitted/",
        {
            "subject": "Hi {{ user.display_first }}",
            "body_html": "<p>Welcome</p><script>x()</script>",
        },
    )
    assert r.status_code == 302
    row = MessageTemplate.objects.get(key="account.admitted")
    assert row.edited and "script" not in row.body_html
    assert AuditLog.objects.filter(action="template.edited", subject_id=str(row.pk)).exists()
    m = _user("n@example.org")
    m.preferred_name = "Nell"
    m.save()
    assert send("account.admitted", m, "account").subject == "Hi Nell"
    body = c.get("/ops/templates/account.admitted/").content.decode()
    assert "edited here" not in body or "Restore the shipped default" in body
    r = c.post("/ops/templates/account.admitted/", {"reset": "1"})
    assert not MessageTemplate.objects.get(key="account.admitted").edited


def test_invitation_message_goes_to_the_address_and_marks_emailed_at():
    _on()
    from apps.accounts.services import create_invitation

    o = _user("o@example.org", AccessLevel.OFFICER)
    inv = create_invitation(o, "new@example.org", "student", base_url="https://ops.example")
    assert inv.emailed_at is not None
    msg = Outbox.objects.get(to_addresses=["new@example.org"])
    assert f"/me/invite/{inv.token}/" in msg.body_html and msg.user is None
    ClubSetting.objects.update_or_create(key="defaults.email_delivery", defaults={"value": "off"})
    inv2 = create_invitation(o, "other@example.org", "student", base_url="https://ops.example")
    assert inv2.emailed_at is None
    minor = create_invitation(
        o, "kid@example.org", "student", True, "parent@example.org", base_url="https://ops.example"
    )
    assert Outbox.objects.get(to_addresses=["parent@example.org"]) and minor.guardian_email
