"""Templates (FR-78), preferences (FR-71), My messages (FR-82, FR-108), and the officer outbox
(FR-105)."""

import pytest
from django.contrib.auth.models import Group
from django.core import mail
from django.core.management import call_command
from django.test import Client

from apps.accounts.models import NotificationPreference, User
from apps.comms.models import MessageTemplate, Outbox
from apps.comms.services import compose, render_message, seed_templates, send
from apps.ops.models import AuditLog, ClubSetting

pytestmark = pytest.mark.django_db


def _user(email="m@example.org", level="member"):
    """A sysadmin is a superuser rather than a member of a group of that name."""
    u = User.objects.create_user(email, "pw-Testing-123", first_name="Mo", last_name="Member")
    if level == "sysadmin":
        u.is_superuser = True
    else:
        u.groups.set(Group.objects.filter(name=level))
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
    if u.is_superuser:
        session = c.session  # a sysadmin signs in acting lower
        session["acting_view"] = "sysadmin"
        session.save()
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
    if u.is_superuser:
        session = c.session  # a sysadmin signs in acting lower
        session["acting_view"] = "sysadmin"
        session.save()
    # the profile says what reaches you; the switches are on the edit page (NAF, 2026-09-19)
    body = c.get("/me/", follow=True).content.decode()
    assert "Notifications" in body and "always sent" in body.lower()
    assert 'name="email" value="reminder"' not in body
    edit = c.get("/me/edit/", follow=True).content.decode()
    assert 'name="email" value="reminder"' in edit and "always sent" in edit.lower()
    r = c.post("/me/notifications/", {"email": ["warning", "digest"]})
    assert r.status_code == 302
    prefs = {p.category: p.email for p in u.notification_preferences.all()}
    assert prefs["reminder"] is False and prefs["warning"] is True and prefs["digest"] is True
    assert u.reminders_off
    # and the profile reads back what was saved
    body = c.get("/me/", follow=True).content.decode()
    assert '<td data-label="Email">off</td>' in body and '<td data-label="Email">on</td>' in body


def test_outbox_is_officers_only_and_filters_by_state():
    _on()
    m = _user()
    compose(m, "reminder", "Sent one", "<p>x</p>")
    ClubSetting.objects.update_or_create(key="defaults.email_delivery", defaults={"value": "off"})
    compose(m, "reminder", "Kept one", "<p>y</p>")
    c = Client()
    c.force_login(m)
    if m.is_superuser:
        session = c.session  # a sysadmin signs in acting lower
        session["acting_view"] = "sysadmin"
        session.save()
    assert c.get("/ops/outbox/").status_code == 404
    o = _user("o@example.org", "officer")
    c.force_login(o)
    if o.is_superuser:
        session = c.session  # a sysadmin signs in acting lower
        session["acting_view"] = "sysadmin"
        session.save()
    body = c.get("/ops/outbox/").content.decode()
    assert "Sent one" in body and "Kept one" in body
    assert "<strong>Mail is not being sent.</strong>" in body
    body = c.get("/ops/outbox/?state=sent").content.decode()
    assert "Sent one" in body and "Kept one" not in body
    home = c.get("/").content.decode()
    assert "<strong>Mail is not being sent.</strong>" in home


def test_template_edit_page_is_sysadmin_only_sanitises_and_audits():
    s = _user("s@example.org", "sysadmin")
    o = _user("o@example.org", "officer")
    c = Client()
    c.force_login(o)
    if o.is_superuser:
        session = c.session  # a sysadmin signs in acting lower
        session["acting_view"] = "sysadmin"
        session.save()
    assert c.get("/ops/templates/").status_code == 404
    c.force_login(s)
    if s.is_superuser:
        session = c.session  # a sysadmin signs in acting lower
        session["acting_view"] = "sysadmin"
        session.save()
    body = c.get("/ops/templates/").content.decode()
    # named by what the message is, not by its key
    assert "Admitted as a member" in body and "as shipped" in body
    assert "account.admitted" in body  # the link still carries the key
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

    o = _user("o@example.org", "officer")
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


def test_delivered_html_carries_the_site_layout_and_styled_links(settings):
    """Every mail the site sends is framed alike (apps.comms.layout): a band with the club's
    short name, the body, the club's name and contact; plain anchors take the accent color."""
    from django.core import mail

    from apps.comms.services import compose, deliver
    from apps.ops.config import set_setting

    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    set_setting(None, "defaults.email_delivery", "on")
    set_setting(None, "club.short_name", "EXAMPLE")
    set_setting(None, "club.contact_email", "club@example.org")
    msg = compose(
        None,
        "account",
        "Hello",
        '<p>See <a href="https://x.example/p/">the page</a>.</p>',
        to=["m@example.org"],
    )
    deliver(msg)
    html = [c for c, t in mail.outbox[-1].alternatives if t == "text/html"][0]
    assert "EXAMPLE Operations</td>" in html and "club@example.org" in html
    assert '<a style="color:#' in html and 'href="https://x.example/p/"' in html
    assert "See" in mail.outbox[-1].body  # the text part is the bare body


def test_a_join_notice_names_the_person_the_way_the_club_does():
    """NAF, 2026-09-19: "Include the person's call sign in join emails", with the subject line
    naming the person and their callsign. An officer reading it should know who it is about."""
    from apps.accounts.services import create_invitation
    from apps.comms.models import Outbox

    officer = _user()
    inv = create_invitation(officer, "kay@example.org", "student", False, "")
    from apps.accounts.services import admit_from_invitation

    admit_from_invitation(
        inv, "a-Long-Password-77!", first_name="Kay", last_name="Craigie", callsign="N3KN"
    )
    subjects = [m.subject for m in Outbox.objects.all()]
    assert any("Kay Craigie N3KN joined" in s for s in subjects), subjects
    body = Outbox.objects.filter(subject__contains="joined").first().body_html
    assert "Kay Craigie N3KN completed the invitation" in body


def test_the_one_thing_a_message_asks_for_is_drawn_as_a_button():
    """NAF, 2026-09-20: "Can we make the Join and Confirm Email emails a bit more attractive
    like the Reset my password button/email?"

    The password reset built its button in code; the club's own messages hold their link in an
    editable template, where the sanitiser keeps only the href, so no marker would survive an
    edit. The shape of the message carries it instead: a paragraph holding nothing but one link
    is the call to action and is drawn as the filled block.
    """
    from apps.comms.layout import wrap
    from apps.ops.config import accent_color

    html = wrap('<p><a href="https://x.example/c/">Confirm this address</a></p>')
    assert f'bgcolor="{accent_color()}"' in html, "a filled block, as the reset mail has"
    assert ">Confirm this address</span>" in html

    inline = wrap('<p>Open this: <a href="https://x.example/c/">here</a> soon.</p>')
    assert "bgcolor" not in inline.split("</td></tr>", 1)[1], "a link in a sentence stays a link"

    single = wrap("<p><a href='https://x.example/c/'>Confirm</a></p>")
    assert ">Confirm</span>" in single, "a hand-typed single quote is still a call to action"

    two = wrap(
        '<p><a href="https://x.example/y/">Yes</a> · <a href="https://x.example/n/">No</a></p>'
    )
    assert "bgcolor" not in two.split("</td></tr>", 1)[1], "two choices stay two links"
    assert two.count('href="https://x.example/') == 2, "and both of them survive"


def test_the_invitation_asks_for_its_link_on_a_line_of_its_own():
    """So the reader's one action is the button, not a phrase in the middle of a sentence."""
    from apps.comms.defaults import DEFAULTS_BY_KEY
    from apps.comms.layout import wrap
    from apps.comms.services import render_message

    assert '<p><a href="{{ link }}">' in DEFAULTS_BY_KEY["invitation"]["body_html"]
    _, body = render_message("invitation", {"link": "https://x.example/i/abc", "expires": None})
    assert "Accept the invitation</span>" in wrap(body)


@pytest.mark.django_db
def test_the_in_application_copy_keeps_its_link_as_a_link():
    """The filled block belongs to the mail. On the site the message sits on a page that already
    styles a link, and a mail-shaped table in the middle of it would read as a foreign object."""
    from apps.accounts.models import User
    from apps.comms.services import compose

    user = User.objects.create_user(
        "mem@example.org", "pw-Testing-123", groups=["member"], first_name="M", last_name="Em"
    )
    compose(user, "account", "Hello", '<p><a href="https://x.example/c/">Confirm</a></p>')
    client = Client()
    client.force_login(user)
    body = client.get("/me/messages/").content.decode()
    assert 'href="https://x.example/c/"' in body and "bgcolor" not in body


@pytest.mark.django_db
def test_the_date_header_carries_the_clubs_own_zone(settings):
    """The advisor, 2026-09-20: the same message was stamped four hours apart in two of his
    mailboxes, one showing UTC and one showing local time.

    Django writes `-0000`, which RFC 5322 reads as "no information about the local time zone",
    and a client is then free to show what it likes. The club's own offset says when it sent.
    """
    from django.core import mail

    from apps.comms.services import compose
    from apps.ops.config import set_setting

    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    set_setting(None, "defaults.email_delivery", "on")
    set_setting(None, "club.timezone", "America/New_York")
    compose(None, "account", "When", "<p>now</p>", to=["m@example.org"])
    date = mail.outbox[-1].message()["Date"]
    assert date.endswith(("-0400", "-0500")), f"the club's own offset, not -0000: {date}"

    set_setting(None, "club.timezone", "nonsense/Zone")
    compose(None, "account", "When", "<p>now</p>", to=["m@example.org"])
    assert mail.outbox[-1].message()["Date"].endswith("+0000"), "a bad zone falls back to UTC"
