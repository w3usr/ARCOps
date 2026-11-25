"""Model factories for tests (TR-35): each builds a saved row with what the model needs, so a
test names only what it is about. `SignUpFactory()` makes the member, the event, its location,
position and slot along the way; `SignUpFactory(user=ada, role="mentor")` fixes the two that
matter. Accounts are made through `User.objects.create_user`, as the application makes them, so
each has its address and its access group."""

from datetime import timedelta

import factory
from django.utils import timezone

from apps.accounts.models import EntryLink, Guardianship, Invitation, User
from apps.events.models import (
    Captaincy,
    Event,
    Location,
    Position,
    RoleCapacity,
    SignUp,
    Slot,
    Waitlist,
)

PASSWORD = "pw-Testing-123"  # noqa: S105  (a test password, the one the tests already use)


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    first_name = factory.Sequence(lambda n: f"Quinn{n}")
    last_name = "Vale"
    email = factory.Sequence(lambda n: f"member{n}@example.org")
    groups = ("member",)

    @classmethod
    def _create(cls, model_class, *args, email="", groups=(), **kwargs):
        return model_class.objects.create_user(email, PASSWORD, groups=list(groups), **kwargs)


class GuardianshipFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Guardianship

    minor = factory.SubFactory(UserFactory, under_18=True)
    guardian = factory.SubFactory(UserFactory)


class InvitationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Invitation

    email = factory.Sequence(lambda n: f"invited{n}@example.org")
    category = "student"
    issued_by = factory.SubFactory(UserFactory, groups=("officer",))
    expires_at = factory.LazyFunction(lambda: timezone.now() + timedelta(days=14))


class EntryLinkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EntryLink

    label = factory.Sequence(lambda n: f"PHYS {100 + n}")
    kind = EntryLink.Kind.COMMUNITY
    expires_at = factory.LazyFunction(lambda: timezone.now() + timedelta(days=30))
    created_by = factory.SubFactory(UserFactory, groups=("officer",))


class EventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Event

    title = factory.Sequence(lambda n: f"Field Day {2026 + n}")


class LocationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Location

    event = factory.SubFactory(EventFactory)
    name = "Club station"


class PositionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Position

    location = factory.SubFactory(LocationFactory)


class SlotFactory(factory.django.DjangoModelFactory):
    """An hour on the air, starting tomorrow at this time, so it is open to sign up for."""

    class Meta:
        model = Slot

    position = factory.SubFactory(PositionFactory)
    start = factory.LazyFunction(
        lambda: (timezone.now() + timedelta(days=1)).replace(minute=0, second=0, microsecond=0)
    )
    end = factory.LazyAttribute(lambda s: s.start + timedelta(hours=1))


class RoleCapacityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RoleCapacity

    slot = factory.SubFactory(SlotFactory)
    role = "operator"


class SignUpFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SignUp

    slot = factory.SubFactory(SlotFactory)
    user = factory.SubFactory(UserFactory)
    role = "operator"


class WaitlistFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Waitlist

    slot = factory.SubFactory(SlotFactory)
    user = factory.SubFactory(UserFactory)
    role = "operator"


class CaptaincyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Captaincy

    event = factory.SubFactory(EventFactory)
    user = factory.SubFactory(UserFactory)
