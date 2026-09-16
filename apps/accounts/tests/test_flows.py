"""Audit tests for the account surface: invitation-only, gates, and what pages show."""

import datetime as dt
import re

import pytest
from django.core.management import call_command
from django.test import Client
from django.utils import timezone

from apps.accounts.models import AccessLevel, Invitation, User
from apps.accounts.services import create_invitation, issue_temporary_password

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def club():
    call_command("club_import")


def officer():
    return User.objects.create_user(
        "off@example.org",
        "x",
        first_name="Off",
        last_name="Icer",
        access_level=AccessLevel.OFFICER,
        category="faculty",
    )


def test_login_page_has_no_signup_link_or_wording():
    body = Client().get("/accounts/login/").content.decode()
    assert "Sign in" in body
    assert "sign up" not in body.lower()
    assert "/accounts/signup/" not in body
    assert "Forgot your username or password?" in body


def test_signup_route_is_closed():
    r = Client().get("/accounts/signup/")
    assert r.status_code == 200 and b"by invitation" in r.content
    r = Client().post(
        "/accounts/signup/",
        {"email": "x@example.org", "password1": "abcdefghijk1", "password2": "abcdefghijk1"},
    )
    assert r.status_code in (200, 405) and User.objects.filter(email="x@example.org").count() == 0


def test_admin_login_goes_through_allauth():
    r = Client().get("/admin/login/")
    assert r.status_code == 302 and r["Location"].startswith("/accounts/login/")


def test_api_docs_require_login():
    r = Client().get("/api/v1/docs")
    assert r.status_code == 302 and "/accounts/login/" in r["Location"]


def test_password_reset_page_explains_when_email_off():
    body = Client().get("/accounts/password/reset/").content.decode()
    assert (
        "club officer" in body and "<form" not in body.split("<h1")[1].split("Back to sign in")[0]
    )


def test_invitation_accept_admits_member_at_once():
    inv = create_invitation(officer(), "new@example.org", "student")
    c = Client()
    r = c.get(f"/me/invite/{inv.token}/")
    assert r.status_code == 200
    r = c.post(
        f"/me/invite/{inv.token}/",
        {
            "callsign": "n0new",
            "first_name": "New",
            "last_name": "Member",
            "password1": "a-long-password-123",
            "password2": "a-long-password-123",
            "consent": "on",
        },
    )
    assert r.status_code == 302 and r["Location"] == "/"
    u = User.objects.get(email="new@example.org")
    assert (
        u.access_level == AccessLevel.MEMBER and u.category == "student" and u.callsign == "N0NEW"
    )
    assert u.license.status == "unverified"  # not in the local ULS table yet
    inv.refresh_from_db()
    assert inv.state == Invitation.State.COMPLETED and inv.accepted_by == u
    # single use
    assert c.get(f"/me/invite/{inv.token}/").status_code == 410


def test_minor_invitation_is_addressed_to_the_guardian():
    inv = create_invitation(
        officer(), "kid@example.org", "student", is_minor=True, guardian_email="parent@example.org"
    )
    body = Client().get(f"/me/invite/{inv.token}/").content.decode()
    assert "under 18" in body and "parent@example.org" in body and "Your first name" in body


def test_no_access_level_is_signed_out():
    u = User.objects.create_user(
        "none@example.org", "x", first_name="No", last_name="Access", access_level=AccessLevel.NONE
    )
    c = Client()
    c.force_login(u)
    r = c.get("/")
    assert r.status_code == 302 and "/accounts/login/" in r["Location"]
    assert c.get("/").status_code == 302  # still out


def test_temporary_password_forces_change_and_expires():
    o = officer()
    u = User.objects.create_user(
        "tmp@example.org", "x", first_name="T", last_name="P", access_level=AccessLevel.MEMBER
    )
    issue_temporary_password(o, u)
    c = Client()
    c.force_login(u)
    r = c.get("/events/")
    assert r.status_code == 302 and r["Location"].startswith("/accounts/password/change/")
    assert c.get("/accounts/password/change/").status_code == 200
    u.temporary_password_expires = timezone.now() - dt.timedelta(hours=1)
    u.save()
    r = c.get("/events/")
    assert r.status_code == 302 and "/accounts/login/" in r["Location"]


def test_admin_add_user_page_renders_with_custom_forms():
    a = User.objects.create_user(
        "adm@example.org",
        "x",
        first_name="A",
        last_name="D",
        access_level=AccessLevel.SYSADMIN,
        is_superuser=True,
    )
    c = Client()
    c.force_login(a)
    assert c.get("/admin/accounts/user/add/").status_code == 200
    assert c.get("/admin/accounts/user/").status_code == 200
    assert c.get(f"/admin/accounts/user/{a.pk}/change/").status_code == 200


def test_every_page_has_one_h1_and_labelled_inputs():
    a = User.objects.create_user(
        "a11y@example.org",
        "x",
        first_name="A",
        last_name="Y",
        access_level=AccessLevel.SYSADMIN,
        is_superuser=True,
        category="faculty",
    )
    c = Client()
    c.force_login(a)
    pages = [
        "/",
        "/events/",
        "/events/mine/",
        "/me/",
        "/me/invitations/",
        "/credentials/agreements/",
        "/credentials/approvals/",
        "/credentials/computer-password/",
    ]
    for p in pages + ["/accounts/login/", "/accounts/password/reset/", "/accounts/signup/"]:
        body = (c if p in pages else Client()).get(p).content.decode()
        assert len(re.findall(r"<h1[\s>]", body)) == 1, f"{p}: expected one h1"
        # every visible text/email/password input has an id referenced by a label or an aria-label
        for m in re.finditer(r"<input[^>]*type=\"(?:text|email|password|number|tel)\"[^>]*>", body):
            tag = m.group(0)
            idm = re.search(r'id="([^"]+)"', tag)
            assert idm, f"{p}: input without id: {tag}"
            assert f'for="{idm.group(1)}"' in body or "aria-label" in tag, (
                f"{p}: unlabelled input {idm.group(1)}"
            )


def test_real_login_post_works_behind_a_proxy_with_empty_remote_addr():
    """Production runs gunicorn on a unix socket: REMOTE_ADDR is empty and the visitor's address
    arrives in X-Real-IP from nginx. allauth's rate limiter must still find an IP (it raised
    PermissionDenied on the first live sign-in attempt, 2026-09-13)."""
    User.objects.create_user(
        "real@example.org",
        "a-long-password-123",
        first_name="R",
        last_name="L",
        access_level=AccessLevel.MEMBER,
    )
    c = Client()
    page = c.get("/accounts/login/", REMOTE_ADDR="", HTTP_X_REAL_IP="203.0.113.5")
    token = c.cookies["csrftoken"].value
    r = c.post(
        "/accounts/login/",
        {
            "csrfmiddlewaretoken": token,
            "login": "real@example.org",
            "password": "a-long-password-123",
        },
        REMOTE_ADDR="",
        HTTP_X_REAL_IP="203.0.113.5",
        HTTP_REFERER="http://testserver/accounts/login/",
    )
    assert r.status_code == 302, r.status_code
    assert c.get("/", REMOTE_ADDR="", HTTP_X_REAL_IP="203.0.113.5").status_code == 200
    assert page.status_code == 200


def test_password_reset_mail_comes_from_the_club_with_its_own_subject(settings):
    """allauth's own mail used Django's default sender and a "[host] …" subject (seen live on
    2026-09-16); it now carries the club's sender and wording."""
    from django.core import mail

    from apps.ops.config import set_setting

    set_setting(None, "club.sending_address", "ops@example.org")
    set_setting(None, "club.sending_display_name", "Example Operations")
    set_setting(None, "club.short_name", "EXAMPLE")
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    u = User.objects.create_user("who@example.org", "pw-Testing-123", first_name="W", last_name="H")
    u.access_level = AccessLevel.MEMBER
    u.save()
    Client().post("/accounts/password/reset/", {"email": "who@example.org"})
    assert len(mail.outbox) == 1
    m = mail.outbox[0]
    assert m.from_email == "Example Operations <ops@example.org>"
    assert m.subject == "Reset your EXAMPLE password"
    assert (
        "webmaster" not in m.body
        and "Hello from" not in m.body
        and "/accounts/password/reset/key/" in m.body
    )
    # HTML part: the link on readable text (a mail scanner rewrites only the href), drawn as a
    # table button inside the site's one mail layout, which Outlook renders faithfully
    html = [c for c, t in m.alternatives if t == "text/html"][0]
    assert "Reset my password</span></font></a>" in html and "/accounts/password/reset/key/" in html
    assert "EXAMPLE Operations</td>" in html and 'bgcolor="#' in html and "<table" in html


def test_password_changed_page_offers_sign_in(client):
    r = client.get("/accounts/password/reset/key/done/")
    assert (
        r.status_code == 200
        and b"Password changed" in r.content
        and b'href="/accounts/login/"' in r.content
    )
