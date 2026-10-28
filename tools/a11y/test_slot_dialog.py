"""Signing up from the roster's slot dialog keeps you on the roster (#139).

Every form in the dialog used to post and redirect to the slot's own page, scrolled to the top,
away from the roster being worked through. Now the answer comes back into the dialog, the cell
behind it changes, and focus goes to the message saying what happened, then back to the slot's
link when the dialog closes.
"""

import pytest
from playwright.sync_api import expect, sync_playwright
from test_axe import ACCOUNTS, sign_in  # the sweep lives beside this file

pytestmark = pytest.mark.django_db(transaction=True)


def _open_slot_for(email):
    """A slot of the first event with a seat this member may take, and that role."""
    from apps.accounts.models import User
    from apps.events.models import Event, Slot
    from apps.events.services.eligibility import can_sign_up

    member = User.objects.by_address(email).get()
    ev = Event.objects.order_by("pk").first()
    for slot in Slot.objects.filter(position__location__event=ev, kind="operating").order_by(
        "start"
    ):
        if slot.signups.filter(user=member).exists():
            continue
        for cap in slot.capacities.all():
            if slot.signups.filter(role=cap.role).count() < cap.capacity:
                if can_sign_up(member, slot, cap.role)[0]:
                    return ev, slot
    raise AssertionError("the demo has no slot this member may sign up for")


def test_signing_up_in_the_dialog_stays_on_the_roster(live_server, engine):
    ev, slot = _open_slot_for(ACCOUNTS["member"])
    roster = f"{live_server.url}/events/{ev.pk}/"
    with sync_playwright() as p:
        browser = getattr(p, engine).launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        sign_in(page, live_server.url, ACCOUNTS["member"])
        page.goto(roster)
        page.click(f'a[data-slot="{slot.pk}"]')
        dialog = page.locator("#slot-dialog")
        expect(dialog).to_be_visible()
        dialog.get_by_role("button", name="Sign up").click()

        expect(dialog.locator(".messages")).to_contain_text("Signed up")
        expect(dialog.locator(".messages")).to_be_focused()
        expect(dialog).to_contain_text("You hold this slot")
        assert page.url == roster
        expect(page.locator(f"#slot-{slot.pk} .you")).to_be_visible()

        page.keyboard.press("Escape")
        expect(dialog).to_be_hidden()
        expect(page.locator(f'a[data-slot="{slot.pk}"]')).to_be_focused()
        browser.close()
