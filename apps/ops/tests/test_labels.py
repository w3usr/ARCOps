"""Stored keys reach a page as the words the club chose for them."""

from datetime import timedelta

import pytest
from django.core.management import call_command

from apps.ops.templatetags.labels import (
    category_label,
    duration,
    kind_label,
    role_label,
    role_labels,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def club():
    call_command("club_import")


def test_a_key_reaches_the_page_as_its_configured_label():
    assert role_label("operator") == "Operator"
    assert category_label("student") == "Student"
    assert kind_label("operating") == "Operating"
    assert kind_label("setup") == "Setup"


def test_a_key_the_club_has_removed_still_reads_as_words():
    assert role_label("net_control") == "Net control"
    assert category_label("") == ""


def test_a_list_of_roles_reads_as_a_sentence():
    assert role_labels(["operator"]) == "Operator"
    assert role_labels(["operator", "mentor"]) == "Operator and Mentor"
    assert role_labels(["operator", "mentor", "observer"]) == "Operator, Mentor, and Observer"
    assert role_labels([]) == ""


def test_a_period_is_words_rather_than_a_python_repr():
    assert duration(timedelta(minutes=15)) == "15 minutes"
    assert duration(timedelta(hours=1)) == "1 hour"
    assert duration(timedelta(days=1)) == "1 day"
    assert duration(timedelta(seconds=90)) == "1 minute"
    assert duration(timedelta(0)) == "never"
