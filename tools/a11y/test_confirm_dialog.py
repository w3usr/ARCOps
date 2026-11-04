"""A destructive act confirms in a dialog over the page (docs/INTERFACE.md, Destructive actions).

The button opens it with invoker commands (commandfor), and app.js does the same for a browser
that predates them. Focus goes into the dialog, Escape closes it and focus comes back to the
button, the dialog passes axe, and the form inside posts the ordinary way.
"""

import pytest
from playwright.sync_api import expect, sync_playwright
from test_axe import ACCOUNTS, audit, describe, sign_in  # the sweep lives beside this file

pytestmark = pytest.mark.django_db(transaction=True)


def test_the_danger_zone_confirms_in_a_dialog(live_server, engine):
    from apps.events.models import Event

    ev = Event.objects.order_by("pk").first()
    status = f"{live_server.url}/events/{ev.pk}/manage/status/"
    with sync_playwright() as p:
        browser = getattr(p, engine).launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        sign_in(page, live_server.url, ACCOUNTS["officer"])
        page.goto(status)
        button = page.get_by_role("button", name="Cancel event")
        dialog = page.get_by_role("dialog", name="Cancel this event?")
        expect(dialog).to_be_hidden()

        button.click()
        expect(dialog).to_be_visible()
        expect(dialog.get_by_label("Reason")).to_be_focused()
        found = audit(page)
        assert not found, describe(status, 1280, found)
        page.keyboard.press("Escape")
        expect(dialog).to_be_hidden()
        expect(button).to_be_focused()

        button.click()
        dialog.get_by_role("button", name="Keep the event").click()
        expect(dialog).to_be_hidden()

        button.click()
        dialog.get_by_label("Reason").fill("Station closed for the storm")
        dialog.get_by_label("I understand this cannot be undone").check()
        dialog.get_by_role("button", name="Cancel the event").click()
        expect(page.locator("#messages")).to_contain_text("cancel", ignore_case=True)
        browser.close()
    ev.refresh_from_db()
    assert ev.state == "cancelled"


def test_an_older_browser_opens_it_from_app_js(live_server, engine):
    """The fallback runs where the browser reports no invoker commands. A browser cannot be
    made to drop its own handling, so this proves the script switches on and does no harm beside
    it (opening an open dialog would throw); CI's older engines are not on offer to test it alone."""
    with sync_playwright() as p:
        browser = getattr(p, engine).launch()
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        ctx.add_init_script("delete HTMLButtonElement.prototype.command;")
        page = ctx.new_page()
        sign_in(page, live_server.url, ACCOUNTS["member"])
        page.goto(f"{live_server.url}/events/mine/")
        assert page.evaluate("!('command' in HTMLButtonElement.prototype)")
        dialog = page.get_by_role("dialog", name="Replace your calendar address?")
        page.get_by_role("button", name="Replace this address").click()
        expect(dialog).to_be_visible()
        dialog.get_by_role("button", name="Keep this address").click()
        expect(dialog).to_be_hidden()
        browser.close()
