"""A guardian signed up for the same slot as their ward is the ward's responsible adult (addendum
A40)."""

from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.accounts.models import Guardianship
from apps.events.models import ResponsibleAdult, SignUp
from apps.events.services import reshape
from apps.events.services.viability import evaluate
from apps.ops.models import AuditLog

from .test_phase2 import _event, _licensed, _user

pytestmark = pytest.mark.django_db


@pytest.fixture
def family():
    parent = _user("parent@example.org", first_name="Pat", last_name="Parent", callsign="N0PAT")
    _licensed(parent)
    kid = _user("kid@example.org", first_name="Kit", last_name="Parent", under_18=True)
    Guardianship.objects.create(minor=kid, guardian=parent)
    _, slots = _event(timezone.now() + timedelta(days=2))
    return parent, kid, slots


def _client(user):
    c = Client()
    c.force_login(user)
    return c


def _adults(su):
    return list(su.responsible_adults.values_list("name", "automatic"))


def test_a_guardian_signing_up_beside_their_ward_is_named(family):
    parent, kid, slots = family
    ward = SignUp.objects.create(slot=slots[0], user=kid, role="observer")
    assert evaluate(slots[0]).status == "not_viable"
    _client(parent).post(f"/events/slot/{slots[0].pk}/signup/", {"role": "mentor"})
    assert SignUp.objects.filter(slot=slots[0], user=parent).exists()
    assert _adults(ward) == [("Pat Parent", True)]
    assert AuditLog.objects.filter(action="responsible_adult.named").exists()
    assert not any("responsible adult" in r for r in evaluate(slots[0]).reasons)


def test_a_ward_signing_up_beside_their_guardian_is_covered_once(family):
    parent, kid, slots = family
    SignUp.objects.create(slot=slots[0], user=parent, role="mentor")
    ward = SignUp.objects.create(slot=slots[0], user=kid, role="observer")
    from apps.events.services.adults import name_guardians_on_slot

    name_guardians_on_slot(kid, ward)
    name_guardians_on_slot(kid, ward)  # twice: still one row
    assert _adults(ward) == [("Pat Parent", True)]


def test_a_guardian_on_another_slot_or_a_stranger_is_not_named(family):
    parent, kid, slots = family
    stranger = _user("adult@example.org", first_name="Sam")
    ward = SignUp.objects.create(slot=slots[0], user=kid, role="observer")
    _client(parent).post(f"/events/slot/{slots[1].pk}/signup/", {"role": "mentor"})
    _client(stranger).post(f"/events/slot/{slots[0].pk}/signup/", {"role": "mentor"})
    assert _adults(ward) == []


def test_the_guardian_cancelling_warns_first_and_takes_the_designation_with_them(family):
    parent, kid, slots = family
    ward = SignUp.objects.create(slot=slots[0], user=kid, role="observer")
    c = _client(parent)
    c.post(f"/events/slot/{slots[0].pk}/signup/", {"role": "mentor"})
    mine = SignUp.objects.get(slot=slots[0], user=parent)
    # Without the guardian, the ward is uncovered again, which is what would_break warns of.
    assert any(
        "responsible adult" in r
        for r in evaluate(slots[0], [s for s in slots[0].signups.all() if s != mine]).reasons
    )
    c.post(f"/events/signup/{mine.pk}/cancel/", {"confirmed": "yes"})
    assert not SignUp.objects.filter(pk=mine.pk).exists()
    assert _adults(ward) == []
    assert AuditLog.objects.filter(action="responsible_adult.removed").exists()


def test_a_hand_named_adult_stays_when_the_guardian_leaves(family):
    parent, kid, slots = family
    ward = SignUp.objects.create(slot=slots[0], user=kid, role="observer")
    ResponsibleAdult.objects.create(signup=ward, name="Aunt May", phone="555")
    c = _client(parent)
    c.post(f"/events/slot/{slots[0].pk}/signup/", {"role": "mentor"})
    mine = SignUp.objects.get(slot=slots[0], user=parent)
    c.post(f"/events/signup/{mine.pk}/cancel/", {"confirmed": "yes"})
    assert _adults(ward) == [("Aunt May", False)]


def test_a_merge_that_brings_the_pair_together_names_the_guardian(family):
    parent, kid, slots = family
    officer = _user("off@example.org", "officer")
    ward = SignUp.objects.create(slot=slots[0], user=kid, role="observer")
    SignUp.objects.create(slot=slots[1], user=parent, role="mentor")
    reshape.merge(officer, slots[0], slots[1])
    assert _adults(ward) == [("Pat Parent", True)]
    later = reshape.split(officer, slots[0], slots[0].start + timedelta(minutes=30))
    assert _adults(later.signups.get(user=kid)) == [("Pat Parent", True)]  # split keeps the mark


def test_the_migration_names_pairs_already_on_a_slot_ahead(family):
    import importlib

    from django.apps import apps

    step = importlib.import_module(
        "apps.events.migrations.0013_a_guardian_on_the_slot_is_the_adult"
    ).name_pairs_already_signed_up
    parent, kid, slots = family
    ward = SignUp.objects.create(slot=slots[0], user=kid, role="observer")
    SignUp.objects.create(slot=slots[0], user=parent, role="mentor")
    alone = SignUp.objects.create(slot=slots[1], user=kid, role="observer")
    step(apps, None)
    step(apps, None)  # run twice: still one row
    assert _adults(ward) == [("Pat Parent", True)]
    assert _adults(alone) == []
