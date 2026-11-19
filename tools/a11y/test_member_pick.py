"""Sign someone up finds the member as the captain types (private tracker 281).

The slot dialog's picker asks for the slot's own page with what was typed and keeps only the
matches (templates/_member_pick.html), so this checks the as-you-type path through htmx, in the
dialog, then that the person chosen is signed up.
"""

import pytest
from playwright.sync_api import expect, sync_playwright
from test_axe import ACCOUNTS, sign_in  # the sweep lives beside this file

pytestmark = pytest.mark.django_db(transaction=True)


def test_typing_part_of_a_name_offers_them_and_signs_them_up(live_server, engine):
    from apps.accounts.models import User
    from apps.events.models import Event, Slot

    member = User.objects.by_address(ACCOUNTS["member"]).get()
    ev = Event.objects.filter(state=Event.State.PUBLISHED).order_by("pk").first()
    slot = next(
        s
        for s in Slot.objects.filter(position__location__event=ev, kind="operating")
        if not s.signups.filter(user=member).exists()
        and any(s.signups.filter(role=c.role).count() < c.capacity for c in s.capacities.all())
    )
    with sync_playwright() as p:
        browser = getattr(p, engine).launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        sign_in(page, live_server.url, ACCOUNTS["officer"])
        page.goto(f"{live_server.url}/events/{ev.pk}/")
        page.click(f'a[data-slot="{slot.pk}"]')
        dialog = page.locator("#slot-dialog")
        manage = dialog.locator("summary", has_text="Manage this slot")
        manage.wait_for(state="attached")  # the dialog's content is in...
        # ...and wired: htmx adds the box's hx-get listener at settle, after the swap; typed
        # before it, the search is never sent (private tracker 355, which failed under -n auto).
        dialog.locator(".htmx-added, .htmx-settling").first.wait_for(state="detached")
        expect(
            dialog.get_by_label("Member", exact=True)
        ).to_be_hidden()  # folded until opened (280)
        manage.focus()
        page.keyboard.press("Enter")  # by keyboard, as a captain without a mouse would
        box = dialog.get_by_label("Member", exact=True)
        box.press_sequentially(member.last_name[:3].lower())
        choice = dialog.get_by_role("radio", name=member.full_name, exact=False)
        expect(choice).to_be_visible()
        choice.check()
        dialog.get_by_role("button", name="Add").click()
        expect(dialog.locator(".messages")).to_contain_text("signed up as")
        expect(dialog.locator("details.manage-slot")).to_have_attribute(
            "open", ""
        )  # still open after
        browser.close()
