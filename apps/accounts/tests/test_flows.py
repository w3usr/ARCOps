"""Audit tests for the account surface: invitation-only, gates, and what pages show."""

import datetime as dt
import re

import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import Client
from django.utils import timezone

from apps.accounts.models import Invitation, User
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
        groups=["officer"],
        category="faculty",
    )


def test_login_page_has_no_signup_link_or_wording():
    body = Client().get("/accounts/login/").content.decode()
    assert "Sign in" in body
    assert "sign up" not in body.lower()
    assert "/accounts/signup/" not in body
    assert "Forgot your password?" in body


def test_signup_route_is_closed():
    r = Client().get("/accounts/signup/")
    assert r.status_code == 200 and b"by invitation" in r.content
    r = Client().post(
        "/accounts/signup/",
        {"email": "x@example.org", "password1": "abcdefghijk1", "password2": "abcdefghijk1"},
    )
    assert r.status_code in (200, 405) and User.objects.by_address("x@example.org").count() == 0


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
    u = User.objects.by_address("new@example.org").get()
    assert u.in_group("member") and u.category == "student" and u.callsign == "N0NEW"
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


def test_an_account_in_no_group_is_signed_out():
    u = User.objects.create_user(
        "none@example.org", "x", first_name="No", last_name="Access", groups=[]
    )
    c = Client()
    c.force_login(u)
    if u.is_superuser:
        session = c.session  # acting at the raised level
        session["acting_view"] = "sysadmin"
        session.save()
    r = c.get("/")
    assert r.status_code == 302 and "/accounts/login/" in r["Location"]
    assert c.get("/").status_code == 302  # still out


def test_temporary_password_forces_change_and_expires():
    o = officer()
    u = User.objects.create_user(
        "tmp@example.org", "x", first_name="T", last_name="P", groups=["member"]
    )
    issue_temporary_password(o, u)
    c = Client()
    c.force_login(u)
    if u.is_superuser:
        session = c.session  # acting at the raised level
        session["acting_view"] = "sysadmin"
        session.save()
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
        is_superuser=True,
    )
    c = Client()
    c.force_login(a)
    if a.is_superuser:
        session = c.session  # acting at the raised level
        session["acting_view"] = "sysadmin"
        session.save()
    assert c.get("/admin/accounts/user/add/").status_code == 200
    assert c.get("/admin/accounts/user/").status_code == 200
    assert c.get(f"/admin/accounts/user/{a.pk}/change/").status_code == 200


def test_every_page_has_one_h1_and_labelled_inputs():
    a = User.objects.create_user(
        "a11y@example.org",
        "x",
        first_name="A",
        last_name="Y",
        is_superuser=True,
        category="faculty",
    )
    c = Client()
    c.force_login(a)
    if a.is_superuser:
        session = c.session  # acting at the raised level
        session["acting_view"] = "sysadmin"
        session.save()
    pages = [
        "/",
        "/events/",
        "/events/mine/",
        f"/members/{a.pk}/",  # your own profile, which /me/ forwards to
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
        groups=["member"],
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
    u.groups.set(Group.objects.filter(name="member"))
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


def test_password_reset_follows_the_addresses_that_sign_you_in(settings):
    """A confirmed address resets the account; one merely typed into a profile does not, and a
    stranger's address gets no mail at all. The page reads the same in every case."""
    from django.core import mail

    from apps.accounts import addresses

    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    u = User.objects.create_user("who@example.edu", "pw-Testing-123", first_name="W", last_name="H")
    addresses.add(u, "who.home@example.org")
    u.groups.set(Group.objects.filter(name="member"))
    u.save()
    c = Client()

    r = c.post("/accounts/password/reset/", {"email": "who.home@example.org"}, follow=True)
    assert b"Check your email" in r.content  # the same page either way
    assert len(mail.outbox) == 0  # not confirmed: it does not move a password

    addresses.mark_confirmed(u, "who.home@example.org")
    r = c.post("/accounts/password/reset/", {"email": "Who.Home@example.org"}, follow=True)
    assert b"Check your email" in r.content
    assert len(mail.outbox) == 1 and mail.outbox[0].to == ["who.home@example.org"]
    link = re.search(r"https?://\S+/accounts/password/reset/key/\S+/", mail.outbox[0].body).group(0)
    path = link[link.index("/accounts/") :]
    r = c.get(path, follow=True)
    assert r.status_code == 200 and b"Bad Token" not in r.content and b"password1" in r.content
    form_url = r.redirect_chain[-1][0]
    r = c.post(form_url, {"password1": "a-New-Password-123!", "password2": "a-New-Password-123!"})
    assert r.status_code == 302
    u.refresh_from_db()
    assert u.check_password("a-New-Password-123!")

    r = c.post("/accounts/password/reset/", {"email": "nobody@example.org"}, follow=True)
    assert b"Check your email" in r.content
    assert len(mail.outbox) == 1  # nothing sent to a stranger


def test_a_password_keeps_the_spaces_it_was_typed_with():
    """A password is a secret, not a name, so nothing trims it.

    Reported 2026-09-20: "passwords exactly 12 characters long are not working, like
    'testme123456'. They are being required to be 13 characters or longer, even though it says
    the minimum is 12." Django's CharField strips by default, so a trailing space made twelve
    characters into eleven, refused with Django's own "at least 12 characters", and the value
    that reached set_password was not the one typed.
    """
    typed = "testme12345 "  # twelve characters, the last one a space
    assert len(typed) == 12
    off = officer()
    inv = create_invitation(off, "spaces@example.org", "student")
    c = Client()
    # The page says the rule before it refuses anything.
    assert "12 characters" in c.get(f"/me/invite/{inv.token}/").content.decode()
    r = c.post(
        f"/me/invite/{inv.token}/",
        {
            "first_name": "Spa",
            "last_name": "Ces",
            "callsign": "",
            "password1": typed,
            "password2": typed,
            "consent": "on",
        },
    )
    assert r.status_code == 302, "twelve characters refused"
    u = User.objects.by_address("spaces@example.org").get()
    assert u.check_password(typed)  # stored as typed, spaces and all
    assert not u.check_password(typed.strip())  # and not as something else

    # Eleven characters is still eleven, and the refusal names the rule.
    inv2 = create_invitation(off, "short@example.org", "student")
    c2 = Client()
    r = c2.post(
        f"/me/invite/{inv2.token}/",
        {
            "first_name": "Sh",
            "last_name": "Ort",
            "callsign": "",
            "password1": "elevenchar ",
            "password2": "elevenchar ",
            "consent": "on",
        },
    )
    assert r.status_code == 200 and "at least 12 characters" in r.content.decode()
    assert not User.objects.by_address("short@example.org").exists()


def test_an_open_invitation_keeps_its_link_on_the_list():
    """The link was shown once, on the card, and nowhere else.

    An officer who closed that card could only get another by pressing **Make a new link**,
    which withdrew the invitation already sent and emailed a second one. The advisor accepted
    the proposal to show it on every open row (issue #4, 2026-09-20).
    """
    off = officer()
    inv = create_invitation(off, "keeps@example.org", "student")
    c = Client()
    c.force_login(off)
    body = c.get("/me/invitations/").content.decode()
    # The control is a glyph beside the link, so its name is for a screen reader (2026-09-20).
    assert f"/me/invite/{inv.token}/" in body and "Copy the link for" in body

    # A revoked one has no live link to show.
    c.post(f"/me/invitations/{inv.pk}/", {"action": "revoke"})
    body = c.get("/me/invitations/").content.decode()
    assert f"/me/invite/{inv.token}/" not in body


def test_a_name_that_does_not_match_the_fcc_says_what_to_do_and_links_there():
    """A warning that sends somebody somewhere carries the way there.

    The advisor, 2026-09-20: the wording should be better, "and if you are going to tell someone
    to go somewhere to do something, provide them a link right in the warning."
    """
    from apps.credentials.models import UlsLicense

    UlsLicense.objects.create(
        callsign="N0DIF",
        operator_class="Extra",
        status="active",
        licensee_name="Other, Someone",
        first_name="Someone",
        last_name="Other",
    )
    inv = create_invitation(officer(), "mismatch@example.org", "student")
    c = Client()
    r = c.post(
        f"/me/invite/{inv.token}/",
        {
            "first_name": "Not",
            "last_name": "Thesame",
            "callsign": "n0dif",
            "password1": "a-long-password-123",
            "password2": "a-long-password-123",
            "consent": "on",
        },
        follow=True,
    )
    body = r.content.decode()
    assert "not the name you gave" in body
    assert "counts for nothing" in body, "it says what the callsign does until answered"
    assert 'href="/me/"' in body or "Answer it on your profile" in body
    # The question follows them until it is answered, rather than waiting on the profile page:
    # a callsign that counts for nothing is too consequential to hide there (2026-09-20).
    for page in ("/", "/events/", "/me/"):
        assert "Is this you?" in c.get(page, follow=True).content.decode(), page
    c.post("/me/uls-name/", {"decision": "yes"})
    assert "Is this you?" not in c.get("/", follow=True).content.decode()


def test_no_password_field_anywhere_trims_what_was_typed():
    """The invariant behind the twelve-character report, held across the whole codebase.

    A plain CharField strips by default, which is right for a name and wrong for a secret: a
    password typed with a trailing space was shortened before it was validated, refused as too
    short, and stored as something other than what was typed. Every password field in the
    project is either built by `password_field` or says `strip=False` itself, so writing one the
    ordinary way cannot bring it back (2026-09-20).

    Read from the source rather than by importing every module: importing the world to make an
    assertion leaves the world imported, and other tests have to live in it.
    """
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parents[3] / "apps"
    offenders = []
    for path in sorted(root.rglob("*.py")):
        if "migrations" in path.parts or "tests" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        # Each field's source, from "CharField(" to the matching close, near a PasswordInput.
        for m in re.finditer(r"forms\.CharField\((?:[^()]|\([^()]*\))*\)", text, re.S):
            body = m.group(0)
            if "PasswordInput" in body and "strip=False" not in body:
                line = text[: m.start()].count("\n") + 1
                offenders.append(f"{path.relative_to(root.parent)}:{line}")
    assert not offenders, (
        "these password fields trim what is typed into them; build them with "
        f"apps.accounts.forms.password_field: {', '.join(offenders)}"
    )


def test_the_emailed_invitation_link_proves_the_mailbox_and_the_copied_one_does_not():
    """The link on the page can be copied and passed on; the one in the mail cannot.

    > Maybe put an extra token on the invitation that actually gets sent, as opposed to the
    > invitation link that someone can copy and paste. — NAF, 2026-09-20
    """
    from apps.accounts import addresses

    off = officer()
    fields = {
        "first_name": "Mail",
        "last_name": "Box",
        "callsign": "",
        "password1": "a-long-password-123",
        "password2": "a-long-password-123",
        "consent": "on",
    }

    copied = create_invitation(off, "copied@example.org", "student")
    Client().post(f"/me/invite/{copied.token}/", fields)
    u = User.objects.by_address("copied@example.org").get()
    row = u.addresses.get(address="copied@example.org")
    assert row.confirmed, "it still signs them in: nothing waits on mail (FR-103)"
    assert row.proof == "vouched", "but nobody has shown they read that mailbox"

    emailed = create_invitation(off, "emailed@example.org", "student")
    Client().post(f"/me/invite/{emailed.token}/?m={emailed.mail_token}", fields)
    row = (
        User.objects.by_address("emailed@example.org")
        .get()
        .addresses.get(address="emailed@example.org")
    )
    assert row.confirmed and row.proof == "mailbox"

    # A guessed or stale second token is no proof at all.
    guessed = create_invitation(off, "guessed@example.org", "student")
    Client().post(f"/me/invite/{guessed.token}/?m=not-the-token", fields)
    row = (
        User.objects.by_address("guessed@example.org")
        .get()
        .addresses.get(address="guessed@example.org")
    )
    assert row.proof == "vouched"
    assert addresses.confirmed(User.objects.by_address("guessed@example.org").get())
