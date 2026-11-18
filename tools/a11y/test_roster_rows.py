"""A roster row is as tall as its content: the time on one line, and a UTC event's time once.

Found on the contact sheet at 1280 px (2026-10-23): rows about 75 px tall for one line of
content, "16:00–17:00 UTC" wrapping in the time column, and a UTC event repeating every time
beneath itself. Measured in a real browser, because the wrap is a layout question.
"""

import pytest
from playwright.sync_api import sync_playwright
from test_axe import ACCOUNTS, sign_in  # the sweep lives beside this file


@pytest.mark.parametrize("zone", ["UTC", "America/New_York"])
def test_the_time_sits_on_one_line_and_utc_shows_once(live_server, engine, zone):
    from apps.events.models import Event

    ev = Event.objects.filter(start__isnull=False).first()
    Event.objects.filter(pk=ev.pk).update(display_timezone=zone)
    with sync_playwright() as p:
        browser = getattr(p, engine).launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        sign_in(page, live_server.url, ACCOUNTS["member"])
        page.goto(f"{live_server.url}/events/{ev.pk}/")
        # UTC leads, and the event's zone is a column of its own (#161, functional addendum A12).
        rows = page.eval_on_selector_all(
            ".r-row:not([hidden]):not(.r-fold)",
            """rows => rows.map(r => {
                const lead = r.querySelector('.r-time .lead');
                const other = r.querySelector('.r-zone');
                const line = parseFloat(getComputedStyle(lead).lineHeight);
                return {lead: lead.getBoundingClientRect().height, line,
                        other: other ? other.textContent.trim() : ''};
            })""",
        )
        heads = [
            page.text_content(f".r-head {c}") if page.query_selector(f".r-head {c}") else ""
            for c in (".r-time", ".r-zone")
        ]
        when = page.text_content("p.when")
        browser.close()

    assert rows, "the roster has rows"
    assert all(r["lead"] <= r["line"] * 1.5 for r in rows), "the lead time is one line"
    if zone == "UTC":
        assert all(r["other"] == "" for r in rows), "a UTC event shows each time once"
        assert when.count("UTC") == 1, f"and its span once: {when!r}"
    else:
        assert heads[0] == "UTC" and heads[1] in ("EDT", "EST"), (
            f"UTC leads, the zone beside: {heads}"
        )
        assert all(r["other"] for r in rows), "every row also shows the event's zone"


def test_at_phone_width_each_cell_names_its_position_and_the_header_stays(live_server, engine):
    """Private tracker 337 (FR-95, FR-116): stacked at 390 px, a two-position roster's cells each
    say which position they are, and the column headers are still there for a screen reader."""
    from apps.events.models import Event, Position
    from apps.events.services.slots import generate_slots

    ev = Event.objects.filter(start__isnull=False).first()
    first = Position.objects.filter(location__event=ev).first()
    second = Position.objects.create(location=first.location, name="Second op", order=2)
    generate_slots(ev, [second], minutes=60)
    with sync_playwright() as p:
        browser = getattr(p, engine).launch()
        page = browser.new_page(viewport={"width": 390, "height": 900})
        sign_in(page, live_server.url, ACCOUNTS["member"])
        page.goto(f"{live_server.url}/events/{ev.pk}/")
        cells = page.eval_on_selector_all(
            ".roster.grid .r-row:not([hidden]):not(.r-fold) .r-cell",
            "cs => cs.filter(c => c.offsetParent).map(c => c.innerText)",
        )
        headers = page.get_by_role("columnheader", name="Second op").count()
        browser.close()

    assert cells, "the roster is a grid with cells"
    assert all(first.name in c or "Second op" in c for c in cells), (
        f"each names its position: {cells[:4]}"
    )
    assert headers == 1, "the column header is still in the accessibility tree"
