"""A card ends with its padding, not its padding plus the last paragraph's margin.

Found on the contact sheet (2026-10-23): on your profile the Email card had visibly more space
under its last line than the License card. Measured in a real browser, because the space is a
margin and the markup does not show it.
"""

import pytest
from playwright.sync_api import sync_playwright
from test_axe import ACCOUNTS, sign_in  # the sweep lives beside this file

# The space under the lowest thing drawn in each card, less its padding: its text and controls,
# the leaves, so a list item's own padding counts as space too. What is inside a closed
# <details> is not drawn, apart from its summary.
EXTRA = """() => [...document.querySelectorAll('.card')].filter(c => c.offsetParent).map(c => {
    const cs = getComputedStyle(c);
    let bottom = c.getBoundingClientRect().top + parseFloat(cs.paddingTop);
    for (const el of c.querySelectorAll('*')) {
        if (el.children.length && !el.matches('select, button, summary')) continue;
        const closed = el.parentElement.closest('details:not([open])');
        if (closed && closed !== c && !el.closest('summary')) continue;
        const r = el.getBoundingClientRect();
        if (r.height) bottom = Math.max(bottom, r.bottom);
    }
    const inner = c.getBoundingClientRect().bottom - parseFloat(cs.borderBottomWidth) - bottom;
    return {card: (c.querySelector('h2, h3') || c).textContent.trim().slice(0, 40),
            extra: Math.round(inner - parseFloat(cs.paddingBottom))};
})"""


@pytest.mark.parametrize("url", ["/me/", "/me/edit/"])
def test_a_card_ends_with_its_padding(live_server, engine, url):
    with sync_playwright() as p:
        browser = getattr(p, engine).launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        sign_in(page, live_server.url, ACCOUNTS["member"])
        page.goto(f"{live_server.url}{url}")  # /me/ forwards to the member's own page
        cards = page.evaluate(EXTRA)
        browser.close()

    assert cards, "the page has cards"
    # An inline leaf (a <strong> in a line) sits a few pixels inside its line's height; a margin
    # or a list item's padding is 12 px or more.
    uneven = [c for c in cards if c["extra"] > 4]
    assert not uneven, f"space under the last line beyond the padding: {uneven}"
