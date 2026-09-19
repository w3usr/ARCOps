"""The members directory: one table for everyone, sortable, and narrowable.

NAF, 2026-09-19, asked for separate name columns, sorting on every column defaulting to last
name, a phone column of its own, filters on category, position and access, the access column
for officers only, no "joined via", and the same table for every access level with the
redaction unchanged.
"""

import re

import pytest
from django.core.management import call_command
from django.test import Client

from apps.accounts.models import User

pytestmark = pytest.mark.django_db
PASSWORD = "a-Long-Password-77!"


@pytest.fixture(autouse=True)
def club():
    call_command("club_import")


@pytest.fixture
def directory():
    officer = User.objects.create_user(
        "off@example.org",
        PASSWORD,
        groups=["officer"],
        first_name="Ann",
        last_name="Officer",
        category="faculty",
        club_position="president",
        cell_phone="5550001",
    )
    User.objects.create_user(
        "zeta@example.org",
        PASSWORD,
        groups=["member"],
        first_name="Zoe",
        last_name="Adams",
        preferred_name="Zed",
        callsign="W1ZZZ",
        category="student",
        cell_phone="5550002",
    )
    User.objects.create_user(
        "alpha@example.org",
        PASSWORD,
        groups=["member"],
        first_name="Al",
        last_name="Zephyr",
        category="community",
    )
    return officer


def _names(body: str) -> list[str]:
    """The Last column, in the order the table shows it."""
    rows = re.search(r"<tbody>(.*?)</tbody>", body, re.S).group(1)
    return re.findall(r'<td data-label="Last">([^<]*)</td>', rows)


def _as(user):
    c = Client()
    c.force_login(user)
    return c


def test_it_sorts_by_last_name_unasked(directory):
    body = _as(directory).get("/members/").content.decode()
    assert _names(body) == ["Adams", "Officer", "Zephyr"]


def test_every_column_sorts_and_turns_round(directory):
    c = _as(directory)
    for key in (
        "name",
        "first",
        "last",
        "preferred",
        "callsign",
        "category",
        "position",
        "access",
        "email",
        "phone",
    ):
        up = c.get(f"/members/?sort={key}&dir=asc")
        down = c.get(f"/members/?sort={key}&dir=desc")
        assert up.status_code == down.status_code == 200, key
        assert _names(up.content.decode()) == _names(down.content.decode())[::-1], key


def test_the_heading_says_which_way_it_is_sorted(directory):
    body = _as(directory).get("/members/?sort=first&dir=desc").content.decode()
    assert 'aria-sort="descending"' in body
    assert body.count('aria-sort="none"') >= 5, "the other columns say they are not sorted"


def test_a_nonsense_sort_falls_back_to_last_name(directory):
    body = _as(directory).get("/members/?sort=DROP+TABLE").content.decode()
    assert _names(body) == ["Adams", "Officer", "Zephyr"]


def test_filtering_by_category_position_and_access(directory):
    c = _as(directory)
    assert _names(c.get("/members/?category=student").content.decode()) == ["Adams"]
    assert _names(c.get("/members/?position=president").content.decode()) == ["Officer"]
    assert _names(c.get("/members/?access=officer").content.decode()) == ["Officer"]
    assert _names(c.get("/members/?access=member").content.decode()) == ["Adams", "Zephyr"]


def test_filters_and_sorting_survive_each_other(directory):
    body = _as(directory).get("/members/?access=member&sort=last&dir=desc").content.decode()
    assert _names(body) == ["Zephyr", "Adams"]


def test_a_member_gets_no_category_or_access_filter(directory):
    """They cannot see those columns, so they cannot narrow by them."""
    member = User.objects.by_address("zeta@example.org").get()
    body = _as(member).get("/members/").content.decode()
    assert 'name="position"' in body, "position is on the page for everyone"
    assert 'name="category"' not in body and 'name="access"' not in body
    # and asking for one anyway changes nothing
    rows = _as(member).get("/members/?category=student&access=sysadmin").content.decode()
    assert re.search(r"<tbody>(.*?)</tbody>", rows, re.S).group(1).count("<tr>") == 3


def test_joined_via_is_gone(directory):
    assert "Joined via" not in _as(directory).get("/members/").content.decode()


def test_phone_stands_on_its_own(directory):
    body = _as(directory).get("/members/").content.decode()
    assert '<td data-label="Phone">' in body and '<td data-label="Email">' in body
    assert "5550002" in body
