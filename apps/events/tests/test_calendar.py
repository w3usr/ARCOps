from apps.events.services.calendar import parse_date_line


def test_paqp_two_segments():
    r = parse_date_line("1600Z, Oct 10 to 0400Z, Oct 11 and 1300Z-2200Z, Oct 11, 2026")
    assert r.parsed, r.error
    assert [(s.start.isoformat(), s.end.isoformat()) for s in r.segments] == [
        ("2026-10-10T16:00:00+00:00", "2026-10-11T04:00:00+00:00"),
        ("2026-10-11T13:00:00+00:00", "2026-10-11T22:00:00+00:00"),
    ]


def test_2400z_is_next_day():
    r = parse_date_line("0000Z, Sep 26 to 2400Z, Sep 27, 2026")
    assert r.segments[0].end.isoformat() == "2026-09-28T00:00:00+00:00"


def test_year_rollover_and_qualifier():
    r = parse_date_line("CW: 160,80m: 2100Z, Dec 31 to 2100Z, Jan 1, 2027")
    assert r.parsed and r.qualifier == "CW: 160,80m"
    assert r.segments[0].start.year == 2026 and r.segments[0].end.year == 2027


def test_unparseable_reports():
    r = parse_date_line("sometime in October, 2026")
    assert not r.parsed and "unrecognised" in r.error
