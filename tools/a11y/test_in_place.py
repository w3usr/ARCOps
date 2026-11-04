"""A step's own forms save in place (#177): the step and the bar swap, focus lands on the message,
the address and the history stay as they were, and a dialog still opens after the swap."""

import pytest
from playwright.sync_api import expect, sync_playwright
from test_axe import ACCOUNTS, sign_in  # the sweep lives beside this file

pytestmark = pytest.mark.django_db(transaction=True)


def test_removing_a_position_happens_in_place(live_server, engine):
    from apps.events.models import Event, Position

    ev = Event.objects.order_by("pk").first()
    loc = ev.locations.order_by("order").first()
    spare = Position.objects.create(location=loc, name="Spare", order=99)
    url = f"{live_server.url}/events/{ev.pk}/manage/locations/"
    with sync_playwright() as p:
        browser = getattr(p, engine).launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        sign_in(page, live_server.url, ACCOUNTS["officer"])
        page.goto(url)
        before = page.evaluate("history.length")
        rows = page.locator("section[aria-labelledby=loc] ul.list li")
        count = rows.count()
        page.evaluate("window.__kept = true")  # gone if the page reloads
        rows.filter(has_text="Spare").get_by_role("button", name="Remove").click()
        expect(rows).to_have_count(count - 1)
        expect(page.locator("#messages")).to_contain_text("Position removed")
        expect(page.locator("#messages")).to_be_focused()
        assert page.evaluate("window.__kept === true")
        assert page.url == url and page.evaluate("history.length") == before
        page.get_by_role("link", name="Add position").first.click()
        dialog = page.locator("#manage-dialog")
        expect(dialog).to_be_visible()
        expect(dialog.get_by_role("heading", name="Add a position", exact=False)).to_be_visible()
        browser.close()
    assert not Position.objects.filter(pk=spare.pk).exists()


def test_without_javascript_a_remove_posts_and_comes_back(live_server, engine):
    from apps.events.models import Event, Position

    ev = Event.objects.order_by("pk").first()
    loc = ev.locations.order_by("order").first()
    Position.objects.create(location=loc, name="Spare", order=99)
    url = f"{live_server.url}/events/{ev.pk}/manage/locations/"
    with sync_playwright() as p:
        browser = getattr(p, engine).launch()
        ctx = browser.new_context(
            java_script_enabled=False, viewport={"width": 1280, "height": 900}
        )
        page = ctx.new_page()
        sign_in(page, live_server.url, ACCOUNTS["officer"])
        page.goto(url)
        page.locator("section[aria-labelledby=loc] ul.list li", has_text="Spare").get_by_role(
            "button", name="Remove"
        ).click()
        page.wait_for_url(url)
        expect(page.locator("#messages")).to_contain_text("Position removed")
        browser.close()
