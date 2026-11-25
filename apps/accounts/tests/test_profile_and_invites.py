"""Email delivery switches (FR-70), the guardian rule on invitations, and where a password
change lands (FR-7)."""

import pytest
from django.contrib.auth.models import Group
from django.test import Client

from apps.accounts.models import Invitation, User
from apps.comms.services import recipient_addresses

pytestmark = pytest.mark.django_db


def _officer():
    u = User.objects.create_user("o@example.org", "pw-Testing-123", first_name="Ann", last_name="O")
    u.groups.set(Group.objects.filter(name="officer"))
    u.save()
    return u


def test_club_mail_follows_the_delivery_switches_and_never_reaches_nobody():
    from apps.accounts import addresses

    u = _officer()
    addresses.add(u, "ann@uni.example", confirmed=True)
    addresses.add(u, "ann@home.example", delivery=False)
    u.addresses.filter(address="o@example.org").update(delivery=False)
    assert recipient_addresses(u) == ["ann@uni.example"]

    u.addresses.update(delivery=False)  # every switch off: everything receives, rather than nothing
    assert recipient_addresses(u) == ["ann@home.example", "ann@uni.example", "o@example.org"]

    u.addresses.update(delivery=True)
    assert recipient_addresses(u) == ["ann@home.example", "ann@uni.example", "o@example.org"]


def test_profile_shows_every_address_once_with_its_standing_and_a_way_to_add_one():
    from apps.accounts import addresses

    u = _officer()
    addresses.add(u, "ann@home.example")
    c = Client()
    c.force_login(u)
    body = c.get("/me/", follow=True).content.decode()
    assert ">Email</h2>" in body  # a plain noun, not a sentence
    # the profile reads; nothing on it changes anything
    assert "address_delivery" not in body and "address_add" not in body
    assert "Not confirmed, so it cannot sign you in yet" in body
    edit = c.get("/me/edit/", follow=True).content.decode()
    assert edit.count('value="address_delivery"') == 2  # one switch per address
    # what each address does, said in words rather than in a row of badges
    assert "Send the confirmation link" in edit
    assert "Turn club mail off" in edit
    assert 'name="action" value="address_add"' in edit
    # each address is written out once at the head of its block, on both pages
    for page in (body, edit):
        assert page.count('<p class="address">o@example.org ') == 1
        assert page.count('<p class="address">ann@home.example ') == 1


def test_a_minor_needs_a_guardian_and_an_adult_never_stores_one():
    c = Client()
    c.force_login(_officer())
    r = c.post(
        "/me/invitations/",
        {"email": "kid@example.org", "category": "student", "is_minor": "on", "guardian_email": ""},
    )
    assert r.status_code == 200 and "required for a minor" in r.content.decode()
    assert not Invitation.objects.filter(email="kid@example.org").exists()
    c.post(
        "/me/invitations/",
        {"email": "adult@example.org", "category": "student", "guardian_email": "x@example.org"},
    )
    assert Invitation.objects.get(email="adult@example.org").guardian_email == ""
    # The field is present in the HTML (works without JavaScript) but marked for disclosure.
    assert 'data-reveal-when="#id_is_minor"' in c.get("/me/invitations/").content.decode()


def test_forced_password_change_lands_on_home_and_a_voluntary_one_on_the_profile():
    u = _officer()
    u.password_is_temporary = True
    u.save()
    c = Client()
    c.force_login(u)
    assert c.get("/events/")["Location"] == "/accounts/password/set/"
    r = c.post(  # the temporary password was spent at sign-in, so no old one is asked (287)
        "/accounts/password/set/",
        {"password1": "a-New-Long-Password-9", "password2": "a-New-Long-Password-9"},
    )
    assert r.status_code == 302 and r["Location"] == "/"
    assert "Welcome, Ann" in c.get("/").content.decode()
    r = c.post(
        "/accounts/password/change/",
        {
            "oldpassword": "a-New-Long-Password-9",
            "password1": "a-New-Long-Password-10",
            "password2": "a-New-Long-Password-10",
        },
    )
    assert r["Location"] == "/me/"


def test_a_new_invitation_shows_its_link_and_a_ready_text_each_with_a_copy_button():
    """FR-104: the officer can pass the invitation on themselves, by link or by text."""
    c = Client()
    c.force_login(_officer())
    body = c.post(
        "/me/invitations/", {"email": "new@example.org", "category": "student"}
    ).content.decode()
    inv = Invitation.objects.get(email="new@example.org")
    link = f"/me/invite/{inv.token}/"
    assert 'id="lnk" readonly value="' in body and link in body
    text = body[body.index('id="txt"') : body.index("</textarea>", body.index('id="txt"'))]
    assert link in text
    assert 'data-copy="#lnk"' in body and 'data-copy="#txt"' in body


def test_the_push_test_button_says_why_nothing_was_sent_or_how_many_devices_got_it(monkeypatch):
    """FR-112: a test notification, sent now, so a member can see whether they arrive."""
    from apps import factories as f
    from apps.accounts.models import PushSubscription
    from apps.comms import push

    u = f.UserFactory()
    c = Client()
    c.force_login(u)

    def said():
        r = c.post("/me/push/test/", follow=True)
        return [str(m) for m in r.context["messages"]]

    monkeypatch.setattr(push, "configured", lambda: False)
    assert said() == ["Browser notifications are not set up on this site yet."]
    monkeypatch.setattr(push, "configured", lambda: True)
    u.push_enabled = False
    u.save(update_fields=["push_enabled"])
    assert "are off for this account" in said()[0]
    u.push_enabled = True
    u.save(update_fields=["push_enabled"])
    assert "No device has allowed notifications yet" in said()[0]
    PushSubscription.objects.create(user=u, endpoint="https://push.example/1", p256dh="k", auth="a")
    sent = []
    monkeypatch.setattr(push, "send_push", lambda user, title, url: sent.append(title) or 1)
    assert said()[0].startswith("Sent to 1 device.") and sent == ["Test notification"]
