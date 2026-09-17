"""A member's addresses: which of them sign them in, how one is proved, and what keeps an
account reachable.

The advisor, 2026-09-17: "Either one can sign-in, so there should not be a separate 'sign-in'
email. The user should not be allowed to delete their last email. They can change an email to a
different verified email. To keep accounts 'unique', they should each be given a unique key/id."
So an account is its `public_id`; every confirmed address signs its owner in; an unconfirmed one
receives club mail and signs nobody in; and the last address stays.
"""

import pytest
from allauth.account.models import EmailAddress
from django.core import mail
from django.test import Client

from apps.accounts import addresses
from apps.accounts.models import User
from apps.ops.models import AuditLog

pytestmark = pytest.mark.django_db
PASSWORD = "pw-Testing-123"


def _member(email="mem@example.edu", **kw):
    kw.setdefault("first_name", "Mem")
    kw.setdefault("last_name", "Ber")
    kw.setdefault("groups", ["member"])
    return User.objects.create_user(email, PASSWORD, **kw)


def test_every_confirmed_address_signs_you_in_and_an_unconfirmed_one_does_not():
    u = _member()
    addresses.add(u, "mem.home@example.org")
    c = Client()
    assert c.login(email="mem@example.edu", password=PASSWORD)
    c.logout()
    assert not c.login(email="mem.home@example.org", password=PASSWORD)

    addresses.mark_confirmed(u, "mem.home@example.org")
    assert c.login(email="mem.home@example.org", password=PASSWORD)
    assert c.login(email="MEM.HOME@example.org", password=PASSWORD)  # case is not a barrier


def test_the_account_is_its_key_so_its_addresses_can_all_change():
    """Nothing identifies the account but `public_id`, which is why a member may replace the
    address they joined with and still be the same person to every record."""
    u = _member()
    key = u.public_id
    addresses.add(u, "mem.new@example.edu", confirmed=True)
    addresses.remove(u, "mem@example.edu", actor=u)
    u.refresh_from_db()
    assert u.public_id == key and u.email == "mem.new@example.edu"
    assert Client().login(email="mem.new@example.edu", password=PASSWORD)


def test_a_member_adds_an_address_and_confirms_it_from_the_link_sent_to_it(settings):
    from apps.ops.config import set_setting

    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    set_setting(None, "defaults.email_delivery", "on")
    u = _member()
    c = Client()
    c.force_login(u)
    r = c.post("/me/", {"action": "address_add", "address": "mem.home@example.org"}, follow=True)
    assert r.status_code == 200
    assert {a.address for a in addresses.on_file(u)} == {
        "mem@example.edu",
        "mem.home@example.org",
    }
    sent = [m for m in mail.outbox if m.to == ["mem.home@example.org"]]
    assert sent, "a confirmation link goes to the address itself"
    assert "/verify-address/" in sent[-1].body  # the text part carries a link that survives copying
    html = [c for c, t in sent[-1].alternatives if t == "text/html"][0]
    link = html[html.index("http") : html.index('">Confirm this address')]
    assert addresses.confirmed(u) == {"mem@example.edu"}

    r = Client().get(link)
    assert r.status_code == 200 and b"Address confirmed" in r.content
    assert "mem.home@example.org" in addresses.confirmed(u)
    assert AuditLog.objects.filter(action="address.confirmed").exists()


def test_an_officer_can_confirm_an_address_without_any_mail():
    """Nothing here may depend on mail arriving, so the officer's word is enough."""
    off = _member("off@example.edu", groups=["officer"])
    m = _member()
    addresses.add(m, "mem.home@example.org")
    c = Client()
    c.force_login(off)
    r = c.post(
        f"/members/{m.pk}/",
        {"action": "address_confirm", "address": "mem.home@example.org"},
        follow=True,
    )
    assert r.status_code == 200 and b"is confirmed" in r.content
    assert "mem.home@example.org" in addresses.confirmed(m)
    assert Client().login(email="mem.home@example.org", password=PASSWORD)


def test_an_address_confirmed_on_one_account_cannot_be_claimed_by_another():
    a = _member("a@example.edu")
    b = _member("b@example.edu")
    addresses.add(a, "shared@example.org")
    addresses.add(b, "shared@example.org")
    addresses.mark_confirmed(a, "shared@example.org")
    with pytest.raises(addresses.AddressInUse):
        addresses.mark_confirmed(b, "shared@example.org")
    assert "shared@example.org" not in addresses.confirmed(b)


def test_an_account_keeps_its_last_address():
    """An account with no address has nothing to reach its owner by and no way back in but the
    one-time password an officer issues."""
    m = _member()
    with pytest.raises(addresses.LastAddress):
        addresses.remove(m, "mem@example.edu", actor=m)
    c = Client()
    c.force_login(m)
    r = c.post("/me/", {"action": "address_remove", "address": "mem@example.edu"}, follow=True)
    assert b"keeps at least one address" in r.content
    assert addresses.on_file(m)


def test_an_address_taken_off_the_account_stops_signing_you_in():
    m = _member()
    addresses.add(m, "mem.home@example.org", confirmed=True)
    addresses.remove(m, "mem.home@example.org", actor=m)
    assert "mem.home@example.org" not in addresses.confirmed(m)
    assert not EmailAddress.objects.filter(user=m, email="mem.home@example.org").exists()
    assert not Client().login(email="mem.home@example.org", password=PASSWORD)


def test_club_mail_follows_the_delivery_switch_and_one_address_always_receives():
    from apps.comms.services import recipient_addresses

    m = _member()
    addresses.add(m, "mem.home@example.org", confirmed=True)
    c = Client()
    c.force_login(m)
    c.post("/me/", {"action": "address_delivery", "address": "mem@example.edu"})
    assert recipient_addresses(m) == ["mem.home@example.org"]

    r = c.post(
        "/me/", {"action": "address_delivery", "address": "mem.home@example.org"}, follow=True
    )
    assert b"at least one address" in r.content
    assert recipient_addresses(m) == ["mem.home@example.org"]


def test_only_a_sysadmin_takes_a_confirmation_away_and_never_the_last_one():
    sysadmin = _member("sys@example.edu", is_superuser=True)
    m = _member()
    addresses.add(m, "mem.home@example.org", confirmed=True)
    c = Client()
    c.force_login(sysadmin)
    c.post(f"/members/{m.pk}/", {"action": "address_unconfirm", "address": "mem.home@example.org"})
    assert addresses.confirmed(m) == {"mem@example.edu"}
    r = c.post(
        f"/members/{m.pk}/",
        {"action": "address_unconfirm", "address": "mem@example.edu"},
        follow=True,
    )
    assert b"only way in" in r.content and addresses.confirmed(m) == {"mem@example.edu"}
