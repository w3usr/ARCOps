"""On-air hours (#247): the hour grid by mouse (drag to paint, None for a day), saved in place,
and the same without JavaScript, where the day buttons stay hidden and each box is a checkbox."""

import pytest
from playwright.sync_api import expect, sync_playwright
from test_axe import ACCOUNTS, sign_in  # the sweep lives beside this file

pytestmark = pytest.mark.django_db(transaction=True)


def _url(live_server):
    from apps.events.models import Event

    return f"{live_server.url}/events/{Event.objects.order_by('pk').first().pk}/manage/slots/"


def test_drag_to_paint_and_none_for_a_day_then_save_in_place(live_server, engine):
    url = _url(live_server)
    with sync_playwright() as p:
        browser = getattr(p, engine).launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        sign_in(page, live_server.url, ACCOUNTS["officer"])
        page.goto(url)
        boxes = page.locator(".onair tbody tr").nth(1).locator("input[name=hour]")
        expect(boxes.first).to_be_checked()  # the whole event to start with
        # Drag from the first box of the second day across three more: all unticked, as the first.
        first, fourth = boxes.nth(0).bounding_box(), boxes.nth(3).bounding_box()
        page.mouse.move(first["x"] + 5, first["y"] + 5)
        page.mouse.down()
        for i in (1, 2, 3):
            b = boxes.nth(i).bounding_box()
            page.mouse.move(b["x"] + 5, b["y"] + 5)
        page.mouse.up()
        assert fourth and [boxes.nth(i).is_checked() for i in range(5)] == [False] * 4 + [True]
        # None for the first day
        row = page.locator(".onair tbody tr").first
        row.get_by_role("button", name="None").click()
        assert row.locator("input[name=hour]:checked").count() == 0
        before = page.evaluate("history.length")
        page.get_by_role("button", name="Save on-air hours").click()
        expect(page.locator("#messages")).to_contain_text("On-air hours saved")
        expect(page.locator("#messages")).to_be_focused()
        expect(page.locator("section[aria-labelledby=air]")).to_contain_text("On the air")
        assert page.url == url and page.evaluate("history.length") == before
        # the day buttons still work after the swap
        page.locator(".onair tbody tr").first.get_by_role("button", name="All").click()
        assert (
            page.locator(".onair tbody tr").first.locator("input[name=hour]:not(:checked)").count()
            == 0
        )
        browser.close()


def test_without_javascript_each_box_is_a_checkbox(live_server, engine):
    url = _url(live_server)
    with sync_playwright() as p:
        browser = getattr(p, engine).launch()
        ctx = browser.new_context(
            java_script_enabled=False, viewport={"width": 1280, "height": 900}
        )
        page = ctx.new_page()
        sign_in(page, live_server.url, ACCOUNTS["officer"])
        page.goto(url)
        expect(page.locator("[data-day-tools]").first).to_be_hidden()
        page.locator(".onair input[name=hour]").first.uncheck()
        page.get_by_role("button", name="Save on-air hours").click()
        page.wait_for_url(url)
        expect(page.locator("#messages")).to_contain_text("On-air hours saved")
        browser.close()
