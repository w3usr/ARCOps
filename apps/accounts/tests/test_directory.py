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
        club_positions=["president"],
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
    return re.findall(r'<td data-label="Last"><a [^>]*>([^<]*)</a>', rows)


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


def test_an_officer_sees_the_redacted_name_beside_the_real_one(directory):
    """So an officer can see what the club sees, without signing in as somebody else.

    NAF, 2026-09-19: "make sure the name column the officers sees is the same one the members
    see... so the officers can quickly see what is on public view."
    """
    body = _as(directory).get("/members/").content.decode()
    head = re.search(r"<thead>(.*?)</thead>", body, re.S).group(1)
    assert ">Name<" in head and ">First<" in head and ">Last<" in head

    rows = re.search(r"<tbody>(.*?)</tbody>", body, re.S).group(1)
    zoe = [r for r in rows.split("<tr>") if "Adams" in r][0]
    # Zoe Adams prefers "Zed": the public name is the preferred one and an initial
    assert "Zed A." in zoe, "the name column is the redacted form, not the full name"


def test_a_member_gets_that_column_and_no_other_name(directory):
    member = User.objects.by_address("zeta@example.org").get()
    head = re.search(
        r"<thead>(.*?)</thead>",
        _as(member).get("/members/").content.decode(),
        re.S,
    ).group(1)
    assert ">Name<" in head, "the redacted name is the only name a member has"
    assert ">First<" not in head and ">Last<" not in head


def test_both_halves_of_the_name_open_the_member(directory):
    rows = re.search(
        r"<tbody>(.*?)</tbody>", _as(directory).get("/members/").content.decode(), re.S
    ).group(1)
    zoe = User.objects.by_address("zeta@example.org").get()
    link = f'/members/{zoe.pk}/"'
    first_row = [r for r in rows.split("<tr>") if "Adams" in r][0]
    assert first_row.count(link) == 2, "the first name and the last name each link to the page"


def test_a_members_sort_falls_back_to_a_column_they_have(directory):
    """ "last" is not theirs to sort by, so asking for it lands on the name they do see."""
    member = User.objects.by_address("zeta@example.org").get()
    body = _as(member).get("/members/?sort=last").content.decode()
    assert 'aria-sort="ascending"' in body
    head = re.search(r"<thead>(.*?)</thead>", body, re.S).group(1)
    sorted_col = re.search(r'aria-sort="ascending"[^>]*><a[^>]*>([A-Za-z]+)', head).group(1)
    assert sorted_col == "Name"


def test_joined_via_is_gone(directory):
    assert "Joined via" not in _as(directory).get("/members/").content.decode()


def test_phone_stands_on_its_own(directory):
    body = _as(directory).get("/members/").content.decode()
    assert '<td data-label="Phone">' in body and '<td data-label="Email">' in body
    assert "5550002" in body


def _licensed(directory):
    """Give the three people classes spread across the ladder."""
    from apps.credentials.models import LicenseRecord

    for address, callsign, cls in (
        ("off@example.org", "W1OFF", "Extra"),
        ("zeta@example.org", "W1ZZZ", "Technician"),
    ):
        u = User.objects.by_address(address).get()
        u.callsign = callsign
        u.save(update_fields=["callsign"])
        LicenseRecord.objects.create(user=u, callsign=callsign, operator_class=cls, status="active")
    return directory


def test_the_class_is_its_own_column_and_members_see_it(directory):
    _licensed(directory)
    for who in (directory, User.objects.by_address("zeta@example.org").get()):
        body = _as(who).get("/members/").content.decode()
        head = re.search(r"<thead>(.*?)</thead>", body, re.S).group(1)
        assert ">Class<" in head, "the class is on the page for everyone"
        assert '<td data-label="Class">' in body
    # the letter, not the word: the club reads N/T/G/A/E on every roster, and the column is
    # narrow enough to matter (NAF, 2026-09-19)
    body = _as(directory).get("/members/").content.decode()
    rows = re.search(r"<tbody>(.*?)</tbody>", body, re.S).group(1)
    assert '<td data-label="Class">T</td>' in rows and '<td data-label="Class">E</td>' in rows
    assert "Technician</td>" not in rows, "the word belongs in the filter, not the cell"


def test_the_class_sorts_up_the_ladder_not_down_the_alphabet(directory):
    """Novice before Extra, because that is what a class means.

    Sorted as words, Advanced would come before Technician and the column would be nonsense.
    """
    _licensed(directory)
    body = _as(directory).get("/members/?sort=class&dir=asc").content.decode()
    # Technician (Zoe Adams) is below Extra (Ann Officer); Al Zephyr holds no license and is last
    assert _names(body) == ["Adams", "Officer", "Zephyr"]
    assert _names(_as(directory).get("/members/?sort=class&dir=desc").content.decode()) == [
        "Zephyr",
        "Officer",
        "Adams",
    ]


def test_filtering_by_class_including_nobody_licensed(directory):
    _licensed(directory)
    c = _as(directory)
    assert _names(c.get("/members/?license=Extra").content.decode()) == ["Officer"]
    assert _names(c.get("/members/?license=Technician").content.decode()) == ["Adams"]
    assert _names(c.get("/members/?license=none").content.decode()) == ["Zephyr"]


def test_a_member_may_filter_by_class_too(directory):
    _licensed(directory)
    member = User.objects.by_address("zeta@example.org").get()
    body = _as(member).get("/members/").content.decode()
    assert 'name="license"' in body
    rows = _as(member).get("/members/?license=Extra").content.decode()
    assert re.search(r"<tbody>(.*?)</tbody>", rows, re.S).group(1).count("<tr>") == 1


def test_the_directory_takes_the_whole_window(directory):
    """72rem is a measure for reading prose, not for a table this wide."""
    body = _as(directory).get("/members/").content.decode()
    assert 'class="content wide"' in body


def test_a_phone_number_is_shown_the_way_its_country_writes_it(directory):
    u = User.objects.by_address("zeta@example.org").get()
    u.cell_phone = "9737874506"
    u.save(update_fields=["cell_phone"])
    body = _as(directory).get("/members/").content.decode()
    assert "(973) 787-4506" in body, "formatted for display"
    assert 'href="tel:9737874506"' in body, "dialed as stored"
    u.refresh_from_db()
    assert u.cell_phone == "9737874506", "what they typed is what is stored"


def _station(directory, callsign="W2FSR", licensee_type="B"):
    """W2FSR on the live site: a club callsign, matched at the FCC, with no operator class.

    The FCC issues a class to a person only, so a station's record is a callsign, a status, and
    the applicant type that says what kind of licensee holds it. NAF, 2026-09-19: "It's not
    technically true... that is a Club call sign."
    """
    from apps.credentials.models import LicenseRecord

    u = User.objects.by_address("alpha@example.org").get()
    u.callsign = callsign
    u.save(update_fields=["callsign"])
    LicenseRecord.objects.filter(user=u).delete()
    LicenseRecord.objects.create(
        user=u, callsign=callsign, operator_class="", licensee_type=licensee_type, status="active"
    )
    return User.objects.get(pk=u.pk)


def _club_station(directory):
    return _station(directory)


def test_a_club_callsign_reads_c_and_an_unlicensed_account_reads_u(directory):
    club = _club_station(directory)
    assert club.license_letter == "C"
    assert User.objects.by_address("zeta@example.org").get().license_letter == "U"
    rows = re.search(
        r"<tbody>(.*?)</tbody>", _as(directory).get("/members/").content.decode(), re.S
    ).group(1)
    assert '<td data-label="Class">C</td>' in rows
    assert '<td data-label="Class">U</td>' in rows


def test_a_callsign_the_fcc_has_no_record_of_is_not_a_club(directory):
    """Blank class is also what "never checked" looks like, so C needs a matched record."""
    from apps.credentials.models import LicenseRecord

    u = User.objects.by_address("zeta@example.org").get()
    u.callsign = "W1ZZZ"
    u.save(update_fields=["callsign"])
    lic = LicenseRecord.objects.create(user=u, callsign="W1ZZZ", status="unverified")
    assert User.objects.get(pk=u.pk).license_letter == "U"
    lic.status = "not_found"
    lic.save(update_fields=["status"])
    assert User.objects.get(pk=u.pk).license_letter == "U"


def test_club_stations_filter_and_sort_apart_from_the_unlicensed(directory):
    _licensed(directory)
    _club_station(directory)
    c = _as(directory)
    body = c.get("/members/").content.decode()
    assert ">Club station<" not in body, "no entry of its own in the class filter (2026-09-20)"
    assert _names(c.get("/members/?license=club").content.decode()) == ["Zephyr"]
    assert _names(c.get("/members/?license=none").content.decode()) == [], "a club holds a license"
    # Technician, Extra, then the club station, which sits below the ladder it is not on
    assert _names(c.get("/members/?sort=class&dir=asc").content.decode()) == [
        "Adams",
        "Officer",
        "Zephyr",
    ]


def test_the_three_stations_the_fcc_gives_no_class_get_their_own_letters(directory):
    """C a club, R a RACES station, M a military recreation station (NAF, 2026-09-19).

    The FCC issues an operator class to a person, so these three hold a callsign with the class
    field empty; the applicant type on the record (EN24 in its file) is what tells them apart.
    """
    for licensee_type, letter in (("B", "C"), ("R", "R"), ("M", "M")):
        assert _station(directory, licensee_type=licensee_type).license_letter == letter
    # a matched record whose applicant type the import has not reached yet: still a station,
    # and a club is what nearly all of them are
    assert _station(directory, licensee_type="").license_letter == "C"


def test_each_station_letter_filters_and_sorts_on_its_own(directory):
    _licensed(directory)
    _station(directory, licensee_type="R")
    c = _as(directory)
    body = c.get("/members/").content.decode()
    for word in ("Club station", "RACES station", "Military recreation"):
        assert f">{word}<" not in body, "the filter list holds people, not stations (2026-09-20)"
    assert _names(c.get("/members/?license=races").content.decode()) == ["Zephyr"]
    assert _names(c.get("/members/?license=club").content.decode()) == []
    # Technician, Extra, then the RACES station, which sits below the ladder it is not on
    assert _names(c.get("/members/?sort=class&dir=asc").content.decode()) == [
        "Adams",
        "Officer",
        "Zephyr",
    ]


def test_a_filter_takes_more_than_one_answer(directory):
    """NAF, 2026-09-19: "Is it possible to have checkboxes in the drop-down so you can select
    more than one to filter on?" A disclosure of checkboxes, so no JavaScript and no ctrl-click.
    """
    _licensed(directory)
    c = _as(directory)
    body = c.get("/members/").content.decode()
    assert '<details class="filter" name="members-filter"' in body, "one panel open at a time"
    assert 'type="checkbox"' in body
    assert 'name="license" value="Extra"' in body
    # two classes at once, which a drop-down holding one answer cannot do
    assert _names(c.get("/members/?license=Extra&license=Technician").content.decode()) == [
        "Adams",
        "Officer",
    ]
    # and an old single-value link still means what it meant
    assert _names(c.get("/members/?license=Extra").content.decode()) == ["Officer"]


def test_the_panel_says_what_is_ticked(directory):
    body = _as(directory).get("/members/?category=student&category=faculty").content.decode()
    assert "2 categorys" not in body, "a count of two reads worse than the two names"
    assert "Student, Faculty" in body or "Faculty, Student" in body


def test_the_status_panel_starts_empty_like_every_other_panel(directory):
    """NAF, 2026-09-20: "I think the convention we are using is that the filter is turned off if
    everything is unchecked. The status filter seems to be the opposite right now. Fix it."

    The list is unchanged: every live account, with a deleted row left out until it is asked
    for. What changed is that the page no longer draws four ticks under "Any status".
    """
    body = _as(directory).get("/members/").content.decode()
    for key in ("active", "closed", "suspended", "provisional", "deleted"):
        assert f'name="status" value="{key}" checked' not in body, key
    assert "Any status" in body, "the summary says the filter is off"
    assert 'name="archived"' not in body, "and an officer has no archive filter at all"

    # the archive is a flag with a filter of its own, for whoever may read one
    advisor = User.objects.create_user(
        "adv@example.org", PASSWORD, groups=["advisor"], first_name="Ada", last_name="Visor"
    )
    body = _as(advisor).get("/members/").content.decode()
    assert 'name="archived" value="no" checked' in body
    assert 'name="archived" value="yes" checked' not in body
    # One roster: an advisor may ask for the archived rows beside the live ones, so a column
    # tells them apart (NAF, 2026-09-19). An officer gets neither the column nor the filter.
    assert "sort=archived" in body


def test_a_member_holds_any_number_of_positions_and_a_position_any_number_of_members(directory):
    """NAF, 2026-09-20: "I am both Faculty Advisor and Club License Trustee. I should be able to
    be marked and listed as both. Some clubs may have a Board of Trustees, where multiple members
    hold the position of Board Member."

    Both halves: one account carrying two offices, and one office carried by two accounts.
    """
    from apps.ops.config import set_setting

    set_setting(
        None,
        "club_positions",
        [
            {"key": "faculty_advisor", "label": "Faculty Advisor"},
            {"key": "trustee", "label": "Club License Trustee"},
            {"key": "board_member", "label": "Board Member"},
        ],
    )
    both = User.objects.get(last_name="Adams")
    both.club_positions = ["trustee", "faculty_advisor"]
    both.save(update_fields=["club_positions"])
    for last in ("Zephyr", "Officer"):
        u = User.objects.get(last_name=last)
        u.club_positions = ["board_member"]
        u.save(update_fields=["club_positions"])

    body = _as(directory).get("/members/").content.decode()
    assert "Faculty Advisor, Club License Trustee" in body, (
        "both offices, in the order the club lists them rather than the order they were ticked"
    )

    c = _as(directory)
    assert _names(c.get("/members/?position=trustee").content.decode()) == ["Adams"]
    assert _names(c.get("/members/?position=board_member").content.decode()) == [
        "Officer",
        "Zephyr",
    ], "a position several people hold lists all of them"
    assert _names(c.get("/members/?position=trustee&position=board_member").content.decode()) == [
        "Adams",
        "Officer",
        "Zephyr",
    ], "ticking two positions asks for either"


def test_the_profile_page_reads_every_office_a_member_holds(directory):
    from apps.ops.config import set_setting

    set_setting(
        None,
        "club_positions",
        [
            {"key": "faculty_advisor", "label": "Faculty Advisor"},
            {"key": "trustee", "label": "Club License Trustee"},
        ],
    )
    member = User.objects.get(last_name="Adams")
    member.club_positions = ["faculty_advisor", "trustee"]
    member.save(update_fields=["club_positions"])
    body = _as(directory).get(f"/members/{member.pk}/").content.decode()
    assert "Faculty Advisor, Club License Trustee" in body
