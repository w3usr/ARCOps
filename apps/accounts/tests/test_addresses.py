"""A member's addresses: which of them sign them in, and how one is proved.

The advisor, 2026-09-17: either address should sign you in. The rule built from that
conversation is that the sign-in address always does, and any other address on the account does
once it is confirmed, by the member following a link sent to it or by an officer saying so.
"""

import pytest
from allauth.account.models import EmailAddress
from django.core import mail
from django.test import Client

from apps.accounts import addresses
from apps.accounts.models import AccessLevel, User
from apps.ops.models import AuditLog

pytestmark = pytest.mark.django_db
PASSWORD = "pw-Testing-123"


def _member(email="mem@example.edu", **kw):
    kw.setdefault("first_name", "Mem")
    kw.setdefault("last_name", "Ber")
    u = User.objects.create_user(email, PASSWORD, **kw)
    u.access_level = AccessLevel.MEMBER
    u.save()
    return u


def test_the_sign_in_address_always_signs_you_in_and_a_confirmed_one_too():
    u = _member(personal_email="mem.home@example.org")
    c = Client()
    assert c.login(email="mem@example.edu", password=PASSWORD)
    c.logout()
    assert not c.login(email="mem.home@example.org", password=PASSWORD)  # not confirmed yet

    addresses.mark_verified(u, "mem.home@example.org")
    assert c.login(email="mem.home@example.org", password=PASSWORD)
    assert c.login(email="MEM.HOME@example.org", password=PASSWORD)  # case is not a barrier


def test_a_member_confirms_an_address_from_the_link_sent_to_it(settings):
    from apps.ops.config import set_setting

    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    set_setting(None, "defaults.email_delivery", "on")
    u = _member()
    c = Client()
    c.force_login(u)
    r = c.post(
        "/me/",
        {
            "first_name": "Mem",
            "last_name": "Ber",
            "preferred_name": "",
            "callsign": "",
            "cell_phone": "",
            "institution_email": "mem@example.edu",
            "personal_email": "mem.home@example.org",
            "institution_email_delivery": "on",
            "personal_email_delivery": "on",
        },
        follow=True,
    )
    assert r.status_code == 200
    u.refresh_from_db()
    assert u.personal_email == "mem.home@example.org"
    sent = [m for m in mail.outbox if m.to == ["mem.home@example.org"]]
    assert sent, "a confirmation link goes to the address itself"
    assert "/verify-address/" in sent[-1].body  # the text part carries a link that survives copying
    html = [c for c, t in sent[-1].alternatives if t == "text/html"][0]
    link = html[html.index("http") : html.index('">Confirm this address')]
    assert addresses.verified(u) == {"mem@example.edu"}

    r = Client().get(link)
    assert r.status_code == 200 and b"Address confirmed" in r.content
    assert "mem.home@example.org" in addresses.verified(u)
    assert AuditLog.objects.filter(action="email.address_verified").exists()


def test_an_officer_can_confirm_an_address_without_any_mail():
    """Nothing here may depend on mail arriving, so the officer's word is enough."""
    off = _member("off@example.edu", access_level=AccessLevel.OFFICER)
    off.access_level = AccessLevel.OFFICER
    off.save()
    m = _member(personal_email="mem.home@example.org")
    c = Client()
    c.force_login(off)
    r = c.post(
        f"/members/{m.pk}/",
        {"action": "verify_address", "address": "mem.home@example.org"},
        follow=True,
    )
    assert r.status_code == 200 and b"is confirmed" in r.content
    assert "mem.home@example.org" in addresses.verified(m)
    assert Client().login(email="mem.home@example.org", password=PASSWORD)


def test_an_address_confirmed_on_one_account_cannot_be_claimed_by_another():
    a = _member("a@example.edu", personal_email="shared@example.org")
    b = _member("b@example.edu", personal_email="shared@example.org")
    addresses.mark_verified(a, "shared@example.org")
    with pytest.raises(addresses.AddressInUse):
        addresses.mark_verified(b, "shared@example.org")
    assert "shared@example.org" not in addresses.verified(b)


def test_changing_the_sign_in_address_does_not_take_away_the_old_way_in(settings):
    """A typo in the sign-in address must not lock anyone out: what they have confirmed keeps
    working, and the one-time password an officer issues needs no mail at all."""
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    sysadmin = _member("sys@example.edu")
    sysadmin.access_level = AccessLevel.SYSADMIN
    sysadmin.save()
    m = _member(personal_email="mem.home@example.org")
    addresses.mark_verified(m, "mem.home@example.org")

    c = Client()
    c.force_login(sysadmin)
    c.post(
        f"/members/{m.pk}/",
        {
            "action": "save",
            "first_name": "Mem",
            "last_name": "Ber",
            "category": "",
            "access_level": AccessLevel.MEMBER,
            "email": "typo@example.edu",
            "personal_email": "mem.home@example.org",
        },
    )
    m.refresh_from_db()
    assert m.email == "typo@example.edu"
    assert Client().login(email="mem.home@example.org", password=PASSWORD)


def test_an_address_taken_off_the_account_stops_signing_you_in():
    m = _member(personal_email="mem.home@example.org")
    addresses.mark_verified(m, "mem.home@example.org")
    m.personal_email = ""
    m.save()
    addresses.sync(m)
    assert "mem.home@example.org" not in addresses.verified(m)
    assert not EmailAddress.objects.filter(user=m, email="mem.home@example.org").exists()
