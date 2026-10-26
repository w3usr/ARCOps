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

    ev = Event.objects.filter(periods__isnull=False).distinct().first()
    Event.objects.filter(pk=ev.pk).update(display_timezone=zone)
    with sync_playwright() as p:
        browser = getattr(p, engine).launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        sign_in(page, live_server.url, ACCOUNTS["member"])
        page.goto(f"{live_server.url}/events/{ev.pk}/")
        rows = page.eval_on_selector_all(
            ".r-row .r-time",
            """cells => cells.map(c => {
                const lead = c.querySelector('.lead');
                const other = c.querySelector('.other');
                const line = parseFloat(getComputedStyle(lead).lineHeight);
                return {lead: lead.getBoundingClientRect().height, line,
                        other: other ? other.textContent.trim() : ''};
            })""",
        )
        when = page.text_content("p.when")
        browser.close()

    assert rows, "the roster has rows"
    assert all(r["lead"] <= r["line"] * 1.5 for r in rows), "the lead time is one line"
    if zone == "UTC":
        assert all(r["other"] == "" for r in rows), "a UTC event shows each time once"
        assert when.count("UTC") == 1, f"and its span once: {when!r}"
    else:
        assert all(r["other"].endswith("UTC") for r in rows), "a local event still shows UTC"
