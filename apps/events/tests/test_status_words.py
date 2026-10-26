"""A slot's state reaches every reader in the roster's words, never as "not viable" (FR-62).

FR-62 replaced *not viable* and *at risk* on the roster on 2026-09-13 "so that a newcomer reads an
invitation, not a verdict". The pages that warn before a change, the messages, the captains'
digest and the export still printed the state's name. SK, 2026-10-26: the roster's words
everywhere, captains included; the names stay in the code and the requirements (FR-73).
"""

from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.comms.models import Outbox
from apps.events.models import SignUp
from apps.events.services import notify
from apps.events.services.viability import SlotStatus

from .test_notify import _event, _msgs, _user

pytestmark = pytest.mark.django_db

BROKEN = SlotStatus("not_viable", ["nobody with station access", "nobody with computer access"])
SAYS = "needs someone with station access and someone with computer access"


def test_a_state_reads_as_what_the_slot_needs():
    assert BROKEN.needs == SAYS
    assert BROKEN.word == "Needs someone with station access"
    thin = SlotStatus("at_risk", ["depends on Ben N0CAM alone"])
    assert thin.needs == "needs one more person alongside Ben N0CAM" and thin.word == "Covered"
    empty = SlotStatus("empty", ["no one signed up"])
    assert empty.needs == "has nobody in it" and empty.word == "Open"
    assert SlotStatus("viable").word == "Covered"


def _broken(monkeypatch):
    monkeypatch.setattr("apps.events.views.would_break", lambda slot, su: BROKEN)


def test_the_pages_that_warn_before_a_change_say_what_the_slot_needs(monkeypatch):
    now = timezone.now()
    cap = _user("cap@example.org", "officer", first_name="Cap", last_name="Tain")
    mem = _user("mem@example.org", first_name="Mo", last_name="Member")
    e, slots = _event(now + timedelta(days=3), captain=cap)
    su = SignUp.objects.create(slot=slots[0], user=mem, role="observer")
    _broken(monkeypatch)
    c = Client()
    c.force_login(mem)
    body = c.post(f"/events/signup/{su.pk}/cancel/").content.decode()
    assert f"without you the slot {SAYS}." in body and "not viable" not in body
    # said once, by the page: the flash that repeated it is gone
    assert body.count("Careful:") == 1
    token = notify.confirm_token(su)
    body = Client().get(f"/events/cannot/{token}/").content.decode()
    assert f"without you the slot {SAYS}." in body and "not viable" not in body
    c.force_login(cap)
    body = c.get(f"/events/signup/{su.pk}/remove/").content.decode()
    assert f"without them the slot {SAYS}." in body and "not viable" not in body


def test_the_captains_are_told_what_the_slot_needs():
    now = timezone.now()
    cap = _user("cap@example.org", "officer", first_name="Cap", last_name="Tain")
    mem = _user("mem@example.org", first_name="Mo", last_name="Member")
    e, slots = _event(now + timedelta(days=3), captain=cap)
    su = SignUp.objects.create(slot=slots[0], user=mem, role="observer")
    notify.member_cancelled(mem, su, BROKEN)
    body = _msgs(cap, "cancellation").get().body_html
    assert f"The slot now {SAYS}." in body and "not viable" not in body


def test_the_at_risk_message_and_digest_use_the_roster_words():
    now = timezone.now()
    cap = _user("cap@example.org", "officer", first_name="Cap", last_name="Tain")
    new = _user("new@example.org", first_name="Newt", last_name="Person")
    e, slots = _event(now + timedelta(hours=30), captain=cap)
    SignUp.objects.create(slot=slots[0], user=new, role="observer")
    notify.send_warnings(now)
    person = _msgs(new, "warning").get().body_html
    digest = _msgs(cap, "warning").get().body_html
    for body in (person, digest):
        assert "needs someone with" in body.lower()
        assert "Not viable" not in body and "At risk" not in body and "nobody with" not in body
    assert ", Run, needs someone with" in person


def test_the_export_gives_the_roster_word():
    now = timezone.now()
    cap = _user("cap@example.org", "officer", first_name="Cap", last_name="Tain")
    new = _user("new@example.org", first_name="Newt", last_name="Person")
    e, slots = _event(now + timedelta(days=3), captain=cap)
    SignUp.objects.create(slot=slots[0], user=new, role="observer")
    c = Client()
    c.force_login(cap)
    rows = c.get(f"/events/{e.pk}/roster.csv").content.decode().splitlines()
    status = [r.split(",")[7] for r in rows[1:]]
    assert status[0].startswith("Needs someone with") and "Open" in status
    assert not {"Not viable", "Empty", "Viable", "At risk"} & set(status)
    assert Outbox.objects.count() == 0  # an export sends nothing
