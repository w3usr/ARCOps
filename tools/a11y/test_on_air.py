"""On-air hours (#247; ranges only since #248, SK 2026-11-06): a range typed to the minute and
added by keyboard, saved in place, then removed; and the same without JavaScript."""

from datetime import timedelta

import pytest
from playwright.sync_api import expect, sync_playwright
from test_axe import ACCOUNTS, sign_in  # the sweep lives beside this file

pytestmark = pytest.mark.django_db(transaction=True)


def _event(live_server):
    """The Slots step's address, and a two-hour range inside the event's first period."""
    from apps.events.models import Event

    ev = Event.objects.filter(periods__isnull=False).order_by("pk").first()
    start = ev.periods.order_by("start").first().start + timedelta(hours=1)
    rng = (f"{start:%Y-%m-%dT%H:%M}", f"{start + timedelta(hours=2):%Y-%m-%dT%H:%M}")
    return f"{live_server.url}/events/{ev.pk}/manage/slots/", rng


def _fill(page, rng):
    form = page.locator("form", has=page.get_by_role("button", name="Add range"))
    form.get_by_label("Starts (UTC)").fill(rng[0])
    form.get_by_label("Ends (UTC)").fill(rng[1])
    return form


def test_a_range_by_keyboard_saves_in_place_and_is_removed(live_server, engine):
    url, rng = _event(live_server)
    with sync_playwright() as p:
        browser = getattr(p, engine).launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        sign_in(page, live_server.url, ACCOUNTS["officer"])
        page.goto(url)
        air = page.locator("section[aria-labelledby=air]")
        expect(air).to_contain_text("On the air for the whole event")
        expect(air.locator("table, input[name=hour]")).to_have_count(0)  # no grid (#248)
        form = _fill(page, rng)
        before = page.evaluate("history.length")
        form.get_by_role("button", name="Add range").focus()
        page.keyboard.press("Enter")
        expect(page.locator("#messages")).to_contain_text("On-air hours saved: 2 hours in 1 stretch.")
        expect(page.locator("#messages")).to_be_focused()
        expect(air).to_contain_text("On the air 2 of")
        assert page.url == url and page.evaluate("history.length") == before
        # Remove, in place too: the whole event again
        air.get_by_role("button", name="Remove").click()
        expect(page.locator("#messages")).to_contain_text("whole event")
        expect(air).to_contain_text("On the air for the whole event")
        browser.close()


def test_without_javascript_a_range_is_a_plain_post(live_server, engine):
    url, rng = _event(live_server)
    with sync_playwright() as p:
        browser = getattr(p, engine).launch()
        ctx = browser.new_context(java_script_enabled=False, viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        sign_in(page, live_server.url, ACCOUNTS["officer"])
        page.goto(url)
        _fill(page, rng).get_by_role("button", name="Add range").click()
        page.wait_for_url(url)
        expect(page.locator("#messages")).to_contain_text("On-air hours saved: 2 hours in 1 stretch.")
        browser.close()
