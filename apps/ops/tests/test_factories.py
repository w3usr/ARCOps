"""Each factory makes a saved row the application accepts (TR-35)."""

import pytest

from apps import factories as f
from apps.accounts.models import User

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "factory",
    [
        f.UserFactory,
        f.GuardianshipFactory,
        f.InvitationFactory,
        f.EntryLinkFactory,
        f.EventFactory,
        f.LocationFactory,
        f.PositionFactory,
        f.SlotFactory,
        f.RoleCapacityFactory,
        f.SignUpFactory,
        f.WaitlistFactory,
        f.CaptaincyFactory,
    ],
)
def test_each_factory_saves_a_row(factory):
    obj = factory()
    assert obj.pk and type(obj).objects.filter(pk=obj.pk).exists()


def test_a_member_from_the_factory_has_an_address_a_password_and_a_group():
    u = f.UserFactory()
    assert User.objects.by_address(u.email).get() == u
    assert u.groups.filter(name="member").exists()
    assert u.check_password(f.PASSWORD)


def test_a_sign_up_builds_its_event_and_names_only_what_the_test_sets():
    ada = f.UserFactory(first_name="Ada")
    su = f.SignUpFactory(user=ada, role="mentor")
    assert su.user == ada and su.role == "mentor"
    assert su.slot.position.location.event.title.startswith("Field Day")
