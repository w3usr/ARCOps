"""A roster row is as tall as its content: the time on one line, in the browser's own zone.

Found on the contact sheet at 1280 px (2026-10-23): rows about 75 px tall for one line of
content, and "16:00–17:00 UTC" wrapping in the time column. Measured in a real browser, because
the wrap is a layout question. Since functional addendum A38 (2026-11-18) the page shows the
browser's zone only, never UTC: the browser names it in a cookie and the server draws in it.
"""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest
from playwright.sync_api import sync_playwright
from test_axe import ACCOUNTS, sign_in  # the sweep lives beside this file


@pytest.mark.parametrize(
    ("zone", "labels"),
    [("America/Los_Angeles", ("PDT", "PST")), ("Asia/Kolkata", ("IST",))],  # :30 offset too
)
def test_the_time_sits_on_one_line_in_the_browsers_zone(live_server, engine, zone, labels):
    from apps.events.models import Event

    ev = Event.objects.filter(start__isnull=False).first()
    with sync_playwright() as p:
        browser = getattr(p, engine).launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900}, timezone_id=zone)
        sign_in(page, live_server.url, ACCOUNTS["member"])
        page.goto(f"{live_server.url}/")  # a page's script names the browser's zone in a cookie
        page.wait_for_function("document.cookie.split('; ').some(c => c.startsWith('tz='))")
        page.goto(f"{live_server.url}/events/{ev.pk}/")
        drawn_in = page.get_attribute("html", "data-tz")
        rows = page.eval_on_selector_all(
            ".r-row:not([hidden]):not(.r-fold)",
            """rows => rows.map(r => {
                const lead = r.querySelector('.r-time .lead');
                const line = parseFloat(getComputedStyle(lead).lineHeight);
                return {lead: lead.getBoundingClientRect().height, line};
            })""",
        )
        head = page.text_content(".r-head .r-time") if page.query_selector(".r-head") else ""
        zones = page.locator(".r-zone").count()
        roster = page.text_content("main")
        browser.close()

    now = datetime.now(UTC)  # a browser may name a zone by its alias (Asia/Calcutta)
    assert (
        now.astimezone(ZoneInfo(drawn_in)).utcoffset() == now.astimezone(ZoneInfo(zone)).utcoffset()
    ), f"the page is drawn in the browser's zone: {drawn_in}"
    assert rows, "the roster has rows"
    assert all(r["lead"] <= r["line"] * 1.5 for r in rows), "the time is one line"
    assert zones == 0 and "UTC" not in roster, "one zone, never UTC"
    assert head in labels or not head, f"the column names the zone: {head!r}"


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
