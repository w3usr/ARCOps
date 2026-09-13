import datetime as dt

import pytest

from apps.credentials.services import default_expiry

R = "next_september_1_skip_august"


@pytest.mark.parametrize(
    "approved, expected",
    [
        (dt.date(2026, 10, 15), dt.date(2027, 9, 1)),  # autumn -> next September
        (dt.date(2027, 3, 1), dt.date(2027, 9, 1)),  # spring -> that September
        (dt.date(2027, 7, 31), dt.date(2027, 9, 1)),  # July -> that September (a month left)
        (dt.date(2027, 8, 20), dt.date(2028, 9, 1)),  # August -> skip to the year after (NAF)
        (dt.date(2026, 9, 1), dt.date(2027, 9, 1)),  # on 1 September -> next year
    ],
)
def test_september_rule(approved, expected):
    assert default_expiry(approved, R) == expected


def test_one_year_rule_handles_leap_day():
    assert default_expiry(dt.date(2028, 2, 29), "one_year") == dt.date(2029, 2, 28)
