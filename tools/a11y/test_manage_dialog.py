"""Manage's forms open in a dialog (#168), and work as pages without JavaScript.

Focus goes into the dialog on opening, to the problem when a form is refused, and back to the
button on closing; a save lands on the tab with its message. With JavaScript off the button is a
link to the form's page, which posts and comes back to the tab.
"""

import pytest
from playwright.sync_api import expect, sync_playwright
from test_axe import ACCOUNTS, sign_in  # the sweep lives beside this file

pytestmark = pytest.mark.django_db(transaction=True)


def _event():
    from apps.events.models import Event

    return Event.objects.order_by("pk").first()


def test_a_form_opens_in_the_dialog_keeps_focus_and_comes_back(live_server, engine):
    ev = _event()
    setup = f"{live_server.url}/events/{ev.pk}/manage/setup/"
    with sync_playwright() as p:
        browser = getattr(p, engine).launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        sign_in(page, live_server.url, ACCOUNTS["officer"])
        page.goto(setup)
        button = page.get_by_role("link", name="Add period")
        button.click()
        dialog = page.locator("#manage-dialog")
        expect(dialog).to_be_visible()
        expect(dialog.get_by_role("heading", name="Add an operating period")).to_be_visible()
        expect(dialog.get_by_label("Starts (UTC)")).to_be_focused()

        dialog.get_by_label("Starts (UTC)").fill("2030-07-01T18:00")
        dialog.get_by_label("Ends (UTC)").fill("2030-07-01T17:00")
        dialog.get_by_role("button", name="Add period").click()
        expect(dialog.locator(".msg.error")).to_contain_text("Problem:")
        expect(dialog.locator(".msg.error")).to_be_focused()
        expect(dialog.get_by_label("Starts (UTC)")).to_have_value("2030-07-01T18:00")
        assert page.url == setup

        page.keyboard.press("Escape")
        expect(dialog).to_be_hidden()
        expect(button).to_be_focused()

        button.click()
        dialog.get_by_label("Starts (UTC)").fill("2030-07-01T18:00")
        dialog.get_by_label("Ends (UTC)").fill("2030-07-01T20:00")
        dialog.get_by_role("button", name="Add period").click()
        page.wait_for_url(setup)
        expect(page.locator("#messages")).to_contain_text("Operating period added.")
        expect(page.locator("section[aria-labelledby=per]")).to_contain_text("01 Jul 2030 18:00")
        browser.close()


def test_the_generator_says_what_it_will_make_as_the_fields_change(live_server, engine):
    ev = _event()
    with sync_playwright() as p:
        browser = getattr(p, engine).launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        sign_in(page, live_server.url, ACCOUNTS["officer"])
        page.goto(f"{live_server.url}/events/{ev.pk}/manage/slots/")
        page.locator("section[aria-labelledby=gen] a[data-dialog]").first.click()
        dialog = page.locator("#manage-dialog")
        line = dialog.locator("#gen-preview")
        expect(line).not_to_be_empty()
        before = line.inner_text()
        assert before  # written by the server as the dialog opens
        expect(dialog.get_by_label("Slot length (minutes)")).to_be_focused()  # settled: wired
        dialog.get_by_label("Slot length (minutes)").fill("5")  # under the minimum: no line
        expect(line).to_have_text("")
        dialog.get_by_label("Slot length (minutes)").fill("60")
        expect(line).to_have_text(before)
        browser.close()


def test_without_javascript_the_button_is_the_forms_page(live_server, engine):
    ev = _event()
    setup = f"{live_server.url}/events/{ev.pk}/manage/setup/"
    with sync_playwright() as p:
        browser = getattr(p, engine).launch()
        ctx = browser.new_context(
            java_script_enabled=False, viewport={"width": 1280, "height": 900}
        )
        page = ctx.new_page()
        sign_in(page, live_server.url, ACCOUNTS["officer"])
        page.goto(setup)
        page.get_by_role("link", name="Add period").click()
        page.wait_for_url(f"{live_server.url}/events/{ev.pk}/periods/add/")
        page.get_by_label("Starts (UTC)").fill("2030-08-01T18:00")
        page.get_by_label("Ends (UTC)").fill("2030-08-01T20:00")
        page.get_by_role("button", name="Add period").click()
        page.wait_for_url(setup)
        expect(page.locator("#messages")).to_contain_text("Operating period added.")
        browser.close()
