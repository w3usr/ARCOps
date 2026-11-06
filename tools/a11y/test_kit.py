"""The redesign's kit on its own page (#231): the ⋮ menu (#228) by mouse and keyboard, and a data
table's one link per row (#230), in each engine."""

from playwright.sync_api import expect, sync_playwright
from test_axe import ACCOUNTS, audit, sign_in  # the sweep lives beside this file


def _kit(p, engine, live_server):
    browser = getattr(p, engine).launch()
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    sign_in(page, live_server.url, ACCOUNTS["sysadmin"], raise_level=True)
    page.goto(f"{live_server.url}/ops/components/")
    return browser, page


def test_the_menu_by_mouse_and_keyboard(live_server, engine):
    with sync_playwright() as p:
        browser, page = _kit(p, engine, live_server)
        more = page.get_by_role("button", name="More actions for Mult")
        menu = page.locator("#k-menu")
        # By mouse: open, focus on the first entry, against its button, clean while open
        more.click()
        expect(menu).to_be_visible()
        expect(menu.get_by_role("link", name="Rename")).to_be_focused()
        b, m = more.bounding_box(), menu.bounding_box()
        below = abs(m["y"] - (b["y"] + b["height"])) < 16
        above = abs(b["y"] - (m["y"] + m["height"])) < 16  # flipped, with no room under it
        assert below or above, (b, m)
        assert audit(page) == []
        # Escape closes it and gives focus back to its button
        page.keyboard.press("Escape")
        expect(menu).to_be_hidden()
        expect(more).to_be_focused()
        # By keyboard: Enter opens it on its first entry (Tab then walks it, the browser's own way;
        # WebKit, as Safari, passes links by unless asked to); a click outside closes it
        page.keyboard.press("Enter")
        expect(menu).to_be_visible()
        expect(menu.get_by_role("link", name="Rename")).to_be_focused()
        page.mouse.click(5, 5)
        expect(menu).to_be_hidden()
        # A destructive entry opens its confirmation; closing it comes back to the ⋮ button
        more.click()
        menu.get_by_role("button", name="Remove").click()
        dialog = page.locator("#k-confirm")
        expect(dialog).to_be_visible()
        expect(menu).to_be_hidden()
        dialog.get_by_role("button", name="Keep Mult").click()
        expect(dialog).to_be_hidden()
        expect(more).to_be_focused()
        browser.close()


ONE_LINK = """() => [...document.querySelectorAll('table.data tbody tr')]
  .filter(tr => tr.querySelectorAll('td:not(.row-actions) a').length > 1)
  .map(tr => tr.textContent.trim().replace(/\\s+/g, ' '))"""


def test_a_data_table_has_one_link_per_row(live_server, engine):
    with sync_playwright() as p:
        browser, page = _kit(p, engine, live_server)
        assert page.locator("table.data tbody tr").count() >= 2
        assert page.evaluate(ONE_LINK) == []
        browser.close()
