"""Fixtures shared by the events tests."""

import pytest

from apps.accounts.models import User
from apps.ops.models import ClubSetting


@pytest.fixture
def officer():
    ClubSetting.objects.update_or_create(
        key="slot_roles",
        defaults={
            "value": [
                {"key": "operator", "label": "Operator", "on_air": True},
                {"key": "mentor", "label": "Mentor", "on_air": True},
            ]
        },
    )
    return User.objects.create_user(
        "off@example.org",
        "pw-Testing-123",
        groups=["officer"],
        first_name="Ann",
        last_name="O",
    )


@pytest.fixture
def member():
    return User.objects.create_user(
        "mem@example.org", "pw-Testing-123", groups=["member"], first_name="Mo", last_name="M"
    )
